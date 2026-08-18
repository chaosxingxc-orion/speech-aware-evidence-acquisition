"""``analysis.a2t_s2c_read``: the P-A2T Stage-2c form-robustness probe
pinned offline read suite.

Engineering-only, zero live model contact -- reuses ``A2tS2World`` and its
response-text builders directly from ``test_a2t_s2_read`` (SAME data root,
lock, registry, gold shapes -- the SAME 120-id-shaped headroom set this
probe flies over; a 20-sample world here for tractable fixtures, exactly as
Stage-2/2b's own read suites use, mirrors ``test_a2t_s2b_read``'s own
precedent). This module is NEVER pointed at a real flight attempt
directory; that is a separate, one-shot registered read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_s2c_read import (
    DEPLOY_CONVERSION_MIN,
    DEPLOY_INDUCED_MAX,
    DEPLOY_INDUCED_REOPENED_MIN,
    FRAGILE_CONVERSION_MAX,
    FRAGILE_INDUCED_MIN,
    ROBUST_CONVERSION_MIN,
    ROBUST_INDUCED_MAX,
    A2tS2cReadError,
    build_a2t_s2c_report,
    main as a2t_s2c_read_main,
    report_to_json,
)
from speech_aware_evidence_acquisition.analysis.a2t_s2_read import A2tS2ReadError
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.probes.a2t_s2c_flight import C1_ARM, C2_ARM, C3_ARM

from test_a2t_s2_read import (  # reuse the SAME synthetic world + response builders
    A2tS2World,
    _arm_plan_document,
    _cli_repo_layout,
    _headroom_path,
    _tool_for,
    _write_flight_receipt,
    _correct_response,
    _wrong_value_response,
    _copy_supplied_default_response,
)


@pytest.fixture()
def a2ts2c_world(tmp_path):
    return A2tS2World(tmp_path)


# ---------------------------------------------------------------------------
# Fixture builders: outputs.jsonl (C1/C2/C3 rows, all sharing the SAME
# s1p-derived supplied_tool label) / flight-receipt.json / the reused
# Stage-2 arm-plan.
# ---------------------------------------------------------------------------


def _c_label(sample_id: str) -> str:
    return _tool_for(sample_id)  # s1p_tool_names[sample_id] == [tool] (single) in this world


def _row(arm: str, sample_id: str, response: str, supplied_tool: str) -> dict:
    return {
        "arm": arm,
        "sample_id": sample_id,
        "supplied_tool": supplied_tool,
        "response": response,
        "timing": {"started_at": "2026-08-18T00:00:00+00:00", "latency_seconds": 0.1},
    }


def _write_outputs_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _write_stage2_arm_plan(path: Path, world: A2tS2World, **overrides) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_arm_plan_document(world, **overrides)), encoding="utf-8")
    return path


def _build_attempt(
    tmp_path: Path,
    world: A2tS2World,
    *,
    c1_fn,
    c2_fn,
    c3_fn,
    name: str = "attempt",
    write_receipt: bool = True,
    receipt_kwargs: dict | None = None,
    extra_rows: list | None = None,
    corrupt_supplied_tool_for: str | None = None,
) -> Path:
    attempt_dir = tmp_path / name
    rows = []
    for sample_id in world.sample_ids:
        label = _c_label(sample_id)
        if sample_id == corrupt_supplied_tool_for:
            label = "not-the-reused-mapping-value"
        rows.append(_row(C1_ARM, sample_id, c1_fn(sample_id), label))
        rows.append(_row(C2_ARM, sample_id, c2_fn(sample_id), label))
        rows.append(_row(C3_ARM, sample_id, c3_fn(sample_id), label))
    if extra_rows:
        rows.extend(extra_rows)
    _write_outputs_jsonl(attempt_dir / "outputs.jsonl", rows)
    if write_receipt:
        kwargs = dict(split_identity_hash=world.split_identity_hash, arms=["C1", "C2", "C3"])
        kwargs.update(receipt_kwargs or {})
        _write_flight_receipt(attempt_dir / "flight-receipt.json", **kwargs)
    return attempt_dir


def _build_report(
    tmp_path,
    world,
    attempt_dir,
    *,
    headroom_path: Path | None = None,
    stage2_arm_plan_path: Path | None = None,
    arm_plan_overrides: dict | None = None,
):
    lock = load_lock(world.lock_path)
    headroom_path = headroom_path or _headroom_path(tmp_path, world)
    stage2_arm_plan_path = stage2_arm_plan_path or _write_stage2_arm_plan(
        tmp_path / "stage2-arm-plan.json", world, **(arm_plan_overrides or {})
    )
    return build_a2t_s2c_report(
        attempt_dir,
        lock,
        world.data_root,
        repo_root=world.repo_root,
        headroom_path=headroom_path,
        stage2_arm_plan_path=stage2_arm_plan_path,
    )


# ===========================================================================
# Form-robustness verdict fixtures.
# ===========================================================================


def test_robust_fires(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    converting = set(world.sample_ids[:2])  # 2/20 == 0.10 >= 6/120 (0.05)

    def c1_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converting else _wrong_value_response(sample_id)

    def c2_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converting else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, c1_fn=c1_fn, c2_fn=c2_fn, c3_fn=_wrong_value_response)
    report = _build_report(tmp_path, world, attempt_dir)

    c1 = report.per_arm[C1_ARM].overall
    c2 = report.per_arm[C2_ARM].overall
    assert c1.em_conversion_rate == pytest.approx(2 / 20)
    assert c1.em_conversion_rate >= ROBUST_CONVERSION_MIN
    assert c1.induced_substitution_count == 0 <= ROBUST_INDUCED_MAX
    assert c2.em_conversion_rate == pytest.approx(2 / 20)
    assert c2.induced_substitution_count == 0 <= ROBUST_INDUCED_MAX

    verdict = report.form_robustness_verdict
    assert verdict.robust is True
    assert verdict.fragile is False
    assert verdict.overall == "ROBUST"


def test_form_fragile_fires_via_low_conversion(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    # C1 never converts (0/20 <= 3/120); C2 converts comfortably (>= 6/120)
    # and induces nothing -- isolates the LOW-CONVERSION disjunct.
    converting_c2 = set(world.sample_ids[:2])

    def c2_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converting_c2 else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=c2_fn, c3_fn=_wrong_value_response
    )
    report = _build_report(tmp_path, world, attempt_dir)

    c1 = report.per_arm[C1_ARM].overall
    assert c1.em_conversion_rate == 0.0
    assert c1.em_conversion_rate <= FRAGILE_CONVERSION_MAX
    assert c1.induced_substitution_count == 0  # NOT via induced

    verdict = report.form_robustness_verdict
    assert verdict.robust is False
    assert verdict.fragile is True
    assert verdict.overall == "FORM-FRAGILE"
    fragile_by_clause = {c.clause_text: c.verdict for c in verdict.fragile_clauses}
    assert fragile_by_clause["C1 conversion <= 3/120 (<= noise)"] == "met"
    assert fragile_by_clause["C1 induced-substitutions >= 20"] == "not_met"


def test_form_fragile_fires_via_high_induced(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    # C1 copies the supplied default on every sample -- induced == 20 ==
    # len(world.sample_ids), isolating the HIGH-INDUCED disjunct's own
    # mechanism (mirrors test_a2t_s2b_read.test_qa_not_defaults_fires).
    attempt_dir = _build_attempt(
        tmp_path,
        world,
        c1_fn=_copy_supplied_default_response,
        c2_fn=_wrong_value_response,
        c3_fn=_wrong_value_response,
    )
    report = _build_report(tmp_path, world, attempt_dir)

    c1 = report.per_arm[C1_ARM].overall
    assert c1.induced_substitution_count == len(world.sample_ids) == 20
    assert c1.induced_substitution_count >= FRAGILE_INDUCED_MIN
    assert c1.em_conversion_rate == 0.0  # _copy_supplied_default_response never exact-matches

    verdict = report.form_robustness_verdict
    assert verdict.robust is False
    assert verdict.fragile is True
    assert verdict.overall == "FORM-FRAGILE"
    fragile_by_clause = {c.clause_text: c.verdict for c in verdict.fragile_clauses}
    assert fragile_by_clause["C1 induced-substitutions >= 20"] == "met"


def test_inconclusive_c_when_neither_branch_fires(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    ids = world.sample_ids
    converting = {ids[0]}  # 1/20 == 0.05 -- exactly clears ROBUST's conversion floor
    copy_default_ids = set(ids[1:11])  # 10 more inducing samples: 5 < 10 < 20

    def c1_fn(sample_id):
        if sample_id in converting:
            return _correct_response(sample_id)
        if sample_id in copy_default_ids:
            return _copy_supplied_default_response(sample_id)
        return _wrong_value_response(sample_id)

    def c2_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converting else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, c1_fn=c1_fn, c2_fn=c2_fn, c3_fn=_wrong_value_response)
    report = _build_report(tmp_path, world, attempt_dir)

    c1 = report.per_arm[C1_ARM].overall
    c2 = report.per_arm[C2_ARM].overall
    assert c1.em_conversion_rate == pytest.approx(1 / 20)
    assert c1.em_conversion_rate >= ROBUST_CONVERSION_MIN
    assert c1.induced_substitution_count == 10
    assert not (c1.induced_substitution_count <= ROBUST_INDUCED_MAX)  # fails ROBUST
    assert not (c1.induced_substitution_count >= FRAGILE_INDUCED_MIN)  # fails FRAGILE too
    assert c2.em_conversion_rate == pytest.approx(1 / 20)
    assert c2.induced_substitution_count == 0

    verdict = report.form_robustness_verdict
    assert verdict.robust is False
    assert verdict.fragile is False
    assert verdict.overall == "INCONCLUSIVE-C"


# ===========================================================================
# DEPLOY-AUGMENT overlay fixtures (independent of the primary verdict).
# ===========================================================================


def test_deploy_augment_deployable_fires(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    converting = set(world.sample_ids[:2])  # 2/20 == 0.10 >= 6/120

    def c3_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converting else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=c3_fn
    )
    report = _build_report(tmp_path, world, attempt_dir)

    c3 = report.per_arm[C3_ARM].overall
    assert c3.em_conversion_rate == pytest.approx(2 / 20)
    assert c3.em_conversion_rate >= DEPLOY_CONVERSION_MIN
    assert c3.induced_substitution_count == 0 <= DEPLOY_INDUCED_MAX

    verdict = report.deploy_augment_verdict
    assert verdict.deployable is True
    assert verdict.channel_reopened is False
    assert verdict.overall == "DEPLOYABLE"


def test_deploy_augment_channel_reopened_fires(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path,
        world,
        c1_fn=_wrong_value_response,
        c2_fn=_wrong_value_response,
        c3_fn=_copy_supplied_default_response,
    )
    report = _build_report(tmp_path, world, attempt_dir)

    c3 = report.per_arm[C3_ARM].overall
    assert c3.induced_substitution_count == len(world.sample_ids) == 20
    assert c3.induced_substitution_count >= DEPLOY_INDUCED_REOPENED_MIN

    verdict = report.deploy_augment_verdict
    assert verdict.deployable is False
    assert verdict.channel_reopened is True
    assert verdict.overall == "CHANNEL-REOPENED"


def test_deploy_augment_no_flag_when_neither_fires(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response
    )
    report = _build_report(tmp_path, world, attempt_dir)

    c3 = report.per_arm[C3_ARM].overall
    assert c3.em_conversion_rate == 0.0
    assert c3.induced_substitution_count == 0

    verdict = report.deploy_augment_verdict
    assert verdict.deployable is False
    assert verdict.channel_reopened is False
    assert verdict.overall == "no flag"


def test_deploy_augment_fires_independently_of_the_primary_verdict(a2ts2c_world, tmp_path):
    """The mission's own explicit requirement: DEPLOY-AUGMENT must be shown
    firing regardless of C1/C2's own verdict -- here C1/C2 are ROBUST while
    C3 is CHANNEL-REOPENED, proving the two are never coupled."""

    world = a2ts2c_world
    converting = set(world.sample_ids[:2])

    def robust_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converting else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=robust_fn, c2_fn=robust_fn, c3_fn=_copy_supplied_default_response
    )
    report = _build_report(tmp_path, world, attempt_dir)

    assert report.form_robustness_verdict.overall == "ROBUST"
    assert report.deploy_augment_verdict.overall == "CHANNEL-REOPENED"


# ===========================================================================
# Harness-defect refusals.
# ===========================================================================


def test_malformed_row_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response
    )
    with (attempt_dir / "outputs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("not json\n")
    with pytest.raises(A2tS2cReadError, match="malformed row"):
        _build_report(tmp_path, world, attempt_dir)


def test_non_completed_flight_receipt_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response,
        receipt_kwargs={"status": "ABORTED"},
    )
    with pytest.raises(A2tS2cReadError, match="status"):
        _build_report(tmp_path, world, attempt_dir)


def test_missing_flight_receipt_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response,
        write_receipt=False,
    )
    with pytest.raises(A2tS2cReadError, match="flight-receipt.json missing"):
        _build_report(tmp_path, world, attempt_dir)


def test_wrong_arms_field_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response,
        receipt_kwargs={"arms": ["S1p", "S2", "S4", "N0r"]},
    )
    with pytest.raises(A2tS2cReadError, match="arms="):
        _build_report(tmp_path, world, attempt_dir)


def test_split_identity_hash_mismatch_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response,
        receipt_kwargs={"split_identity_hash": "f" * 64},
    )
    with pytest.raises(A2tS2cReadError, match="split_identity_hash"):
        _build_report(tmp_path, world, attempt_dir)


def test_wrong_row_count_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response
    )
    lines = (attempt_dir / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
    (attempt_dir / "outputs.jsonl").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(A2tS2cReadError, match="row count"):
        _build_report(tmp_path, world, attempt_dir)


def test_duplicate_arm_sample_pair_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    dup = _row(C1_ARM, world.sample_ids[0], _wrong_value_response(world.sample_ids[0]), _c_label(world.sample_ids[0]))
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response,
        extra_rows=[dup],
    )
    with pytest.raises(A2tS2cReadError, match="duplicate"):
        _build_report(tmp_path, world, attempt_dir)


def test_headroom_not_covered_by_reused_arm_plan_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response
    )
    extra_headroom = _headroom_path(
        tmp_path, world, name="wider-headroom.json", sample_ids=list(world.sample_ids) + ["tier1_direct:999999"]
    )
    with pytest.raises(A2tS2cReadError, match="not covered"):
        _build_report(tmp_path, world, attempt_dir, headroom_path=extra_headroom)


def test_supplied_tool_mismatch_against_reused_mapping_is_a_harness_defect_refusal(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response,
        corrupt_supplied_tool_for=world.sample_ids[0],
    )
    with pytest.raises(A2tS2cReadError, match="does not match the reused Stage-2 mapping"):
        _build_report(tmp_path, world, attempt_dir)


def test_missing_stage2_arm_plan_raises_directly(a2ts2c_world, tmp_path):
    """A raw ``load_arm_plan`` failure (module docstring note 8) surfaces as
    THAT loader's own ``A2tS2ReadError``, never re-wrapped into this
    module's own harness-defect aggregation class."""

    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response
    )
    with pytest.raises(A2tS2ReadError, match="arm-plan.json missing"):
        _build_report(tmp_path, world, attempt_dir, stage2_arm_plan_path=tmp_path / "does-not-exist.json")


# ===========================================================================
# report_to_json shape / CLI idempotence.
# ===========================================================================


def test_report_to_json_shape(a2ts2c_world, tmp_path):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response
    )
    report = _build_report(tmp_path, world, attempt_dir)
    document = report_to_json(report)
    assert document["schema"] == "saea-a2t-s2c-read-v1"
    assert set(document["per_arm"]) == {"C1", "C2", "C3"}
    assert document["form_robustness_verdict"]["overall"] in {"ROBUST", "FORM-FRAGILE", "INCONCLUSIVE-C"}
    assert document["deploy_augment_verdict"]["overall"] in {"DEPLOYABLE", "CHANNEL-REOPENED", "no flag"}
    assert isinstance(document["deploy_augment_verdict"]["channel_reopened"], bool)


def test_cli_refuses_to_run_twice_against_the_same_output_dir(a2ts2c_world, tmp_path, monkeypatch):
    world = a2ts2c_world
    attempt_dir = _build_attempt(
        tmp_path, world, c1_fn=_wrong_value_response, c2_fn=_wrong_value_response, c3_fn=_wrong_value_response
    )
    headroom_path = _headroom_path(tmp_path, world)
    stage2_arm_plan_path = _write_stage2_arm_plan(tmp_path / "stage2-arm-plan.json", world)
    repo_root = _cli_repo_layout(tmp_path, world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [
        str(attempt_dir),
        "--output-dir",
        str(output_dir),
        "--headroom-manifest",
        str(headroom_path),
        "--stage2-arm-plan",
        str(stage2_arm_plan_path),
        "--repo-root",
        str(repo_root),
    ]

    first_exit = a2t_s2c_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    assert (output_dir / "report.txt").is_file()

    second_exit = a2t_s2c_read_main(argv)
    assert second_exit == 1
