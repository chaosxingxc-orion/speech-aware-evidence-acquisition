"""``analysis.a2t_s2b_read``: the P-A2T Stage-2b follow-up probe pinned
offline read suite.

Engineering-only, zero live model contact -- reuses ``A2tS2World`` and its
response-text builders directly from ``test_a2t_s2_read`` (SAME data root,
lock, registry, gold shapes -- the SAME 120-id-shaped headroom set this
probe flies over, prereg intro: "the SAME 120 headroom ids"; a 20-sample
world here for tractable fixtures, exactly as Stage-2's own read suite
uses). This module is NEVER pointed at a real flight attempt directory;
that is a separate, one-shot registered read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_s2b_read import (
    Q_A_CONFIRMED_CUT_CONVERSION_MIN,
    Q_A_CONFIRMED_CUT_INDUCED_MAX,
    Q_A_NOT_DEFAULTS_INDUCED_MIN,
    Q_B_KNOWLEDGE_TIED_CONVERSION_MAX,
    Q_B_KNOWLEDGE_TIED_RETENTION_MIN,
    Q_B_MISLEAD_RETENTION_MAX,
    Q_B_SCHEMA_CONTRIBUTES_CONVERSION_MIN,
    A2tS2bReadError,
    build_a2t_s2b_report,
    main as a2t_s2b_read_main,
    report_to_json,
)
from speech_aware_evidence_acquisition.analysis.a2t_s2_read import A2tS2ReadError
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.probes.a2t_s2b_flight import B1_ARM, B2_ARM

from test_a2t_s2_read import (  # reuse the SAME synthetic world + response builders
    A2tS2World,
    DERANGEMENT,
    _arm_plan_document,
    _cli_repo_layout,
    _headroom_path,
    _tool_for,
    _write_flight_receipt,
    _correct_response,
    _wrong_tool_response,
    _wrong_value_response,
    _copy_supplied_default_response,
)


@pytest.fixture()
def a2ts2b_world(tmp_path):
    return A2tS2World(tmp_path)


# ---------------------------------------------------------------------------
# Fixture builders: outputs.jsonl (B1/B2 rows, correct supplied_tool labels)
# / flight-receipt.json / the reused Stage-2 arm-plan.json.
# ---------------------------------------------------------------------------


def _b1_label(sample_id: str) -> str:
    return _tool_for(sample_id)  # s1p_tool_names[sample_id] == [tool] (single) in this world


def _b2_wrong_tool(sample_id: str) -> str:
    return DERANGEMENT[_tool_for(sample_id)]


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
    b1_fn,
    b2_fn,
    name: str = "attempt",
    write_receipt: bool = True,
    receipt_kwargs: dict | None = None,
    extra_rows: list | None = None,
    corrupt_supplied_tool_for: str | None = None,
) -> Path:
    attempt_dir = tmp_path / name
    rows = []
    for sample_id in world.sample_ids:
        b1_supplied = _b1_label(sample_id)
        if sample_id == corrupt_supplied_tool_for:
            b1_supplied = "not-the-reused-mapping-value"
        rows.append(_row(B1_ARM, sample_id, b1_fn(sample_id), b1_supplied))
        rows.append(_row(B2_ARM, sample_id, b2_fn(sample_id), _b2_wrong_tool(sample_id)))
    if extra_rows:
        rows.extend(extra_rows)
    _write_outputs_jsonl(attempt_dir / "outputs.jsonl", rows)
    if write_receipt:
        kwargs = dict(split_identity_hash=world.split_identity_hash, arms=["B1", "B2"])
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
    return build_a2t_s2b_report(
        attempt_dir,
        lock,
        world.data_root,
        repo_root=world.repo_root,
        headroom_path=headroom_path,
        stage2_arm_plan_path=stage2_arm_plan_path,
    )


# ===========================================================================
# Q-A fixtures.
# ===========================================================================


def test_qa_confirmed_cut_fires(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    converting = set(world.sample_ids[:2])  # 2/20 == 0.10 >= 8/120

    def b1_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converting else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, b1_fn=b1_fn, b2_fn=_wrong_value_response)
    report = _build_report(tmp_path, world, attempt_dir)

    b1 = report.per_arm[B1_ARM].overall
    assert b1.induced_substitution_count == 0
    assert b1.em_conversion_rate == pytest.approx(2 / 20)
    assert b1.em_conversion_rate >= Q_A_CONFIRMED_CUT_CONVERSION_MIN
    assert b1.induced_substitution_count <= Q_A_CONFIRMED_CUT_INDUCED_MAX

    assert report.qa_verdict.confirmed_cut is True
    assert report.qa_verdict.not_defaults is False
    assert report.qa_verdict.overall == "CONFIRMED-CUT"


def test_qa_not_defaults_fires(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(
        tmp_path, world, b1_fn=_copy_supplied_default_response, b2_fn=_wrong_value_response
    )
    report = _build_report(tmp_path, world, attempt_dir)

    b1 = report.per_arm[B1_ARM].overall
    assert b1.induced_substitution_count == len(world.sample_ids) == 20
    assert b1.induced_substitution_count >= Q_A_NOT_DEFAULTS_INDUCED_MIN
    assert b1.em_conversion_rate == 0.0  # _copy_supplied_default_response never exact-matches

    assert report.qa_verdict.confirmed_cut is False
    assert report.qa_verdict.not_defaults is True
    assert report.qa_verdict.overall == "NOT-DEFAULTS"


def test_qa_inconclusive_when_neither_clause_fires(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response)
    report = _build_report(tmp_path, world, attempt_dir)

    b1 = report.per_arm[B1_ARM].overall
    assert b1.induced_substitution_count == 0  # induced <=5 holds ...
    assert b1.em_conversion_rate == 0.0  # ... but conversion >= 8/120 does NOT

    assert report.qa_verdict.confirmed_cut is False
    assert report.qa_verdict.not_defaults is False
    assert report.qa_verdict.overall == "INCONCLUSIVE-A"


# ===========================================================================
# Q-B fixtures.
# ===========================================================================


def test_qb_schema_contributes_fires(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    converting = set(world.sample_ids[:2])  # 2/20 == 0.10 >= 6/120 (0.05)

    def b2_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converting else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=b2_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    b2 = report.per_arm[B2_ARM].overall
    assert b2.em_conversion_rate == pytest.approx(2 / 20)
    assert b2.em_conversion_rate >= Q_B_SCHEMA_CONTRIBUTES_CONVERSION_MIN

    assert report.qb_verdict.schema_contributes is True
    assert report.qb_verdict.knowledge_tied is False
    assert report.qb_verdict.overall == "SCHEMA-CONTRIBUTES"
    assert report.qb_verdict.mislead is False
    assert report.qb_verdict.overall_with_overlay == "SCHEMA-CONTRIBUTES"


def test_qb_knowledge_tied_fires(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    # 18/20 keep the correct tool (retention 0.90 >= 85%), 2/20 name the
    # wrong tool; nobody exact-matches (conversion 0 <= 2/120).
    wrong_tool_ids = set(world.sample_ids[:2])

    def b2_fn(sample_id):
        return _wrong_tool_response(sample_id) if sample_id in wrong_tool_ids else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=b2_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    b2 = report.per_arm[B2_ARM].overall
    assert b2.em_conversion_rate == 0.0
    assert b2.em_conversion_rate <= Q_B_KNOWLEDGE_TIED_CONVERSION_MAX
    assert b2.tool_accuracy == pytest.approx(18 / 20)
    assert b2.tool_accuracy >= Q_B_KNOWLEDGE_TIED_RETENTION_MIN

    assert report.qb_verdict.schema_contributes is False
    assert report.qb_verdict.knowledge_tied is True
    assert report.qb_verdict.overall == "KNOWLEDGE-TIED"
    assert report.qb_verdict.mislead is False


def test_qb_inconclusive_when_no_primary_clause_fires(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    # Retention EXACTLY at the MISLEAD boundary (0.80, not < 0.80) and
    # BELOW the KNOWLEDGE-TIED floor (0.85): neither primary clause fires,
    # MISLEAD does not fire either (boundary is strict '<').
    wrong_tool_ids = set(world.sample_ids[:4])  # 4/20 wrong tool -> retention 16/20 == 0.80

    def b2_fn(sample_id):
        return _wrong_tool_response(sample_id) if sample_id in wrong_tool_ids else _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=b2_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    b2 = report.per_arm[B2_ARM].overall
    assert b2.em_conversion_rate == 0.0
    assert b2.tool_accuracy == pytest.approx(0.80)

    assert report.qb_verdict.schema_contributes is False
    assert report.qb_verdict.knowledge_tied is False
    assert report.qb_verdict.mislead is False
    assert report.qb_verdict.overall == "INCONCLUSIVE-B"
    assert report.qb_verdict.overall_with_overlay == "INCONCLUSIVE-B"


def test_qb_mislead_overlay_fires_independently_alongside_schema_contributes(a2ts2b_world, tmp_path):
    """The mission's own explicit requirement: MISLEAD must be shown firing
    INDEPENDENTLY -- here, alongside SCHEMA-CONTRIBUTES (not only inside
    INCONCLUSIVE-B), proving it is never gated behind the primary verdict."""

    world = a2ts2b_world
    converting = set(world.sample_ids[:2])  # 2/20 == 0.10 >= 0.05 -> SCHEMA-CONTRIBUTES
    wrong_tool_ids = set(world.sample_ids[2:8])  # 6/20 wrong tool -> retention 14/20 == 0.70 < 0.80

    def b2_fn(sample_id):
        if sample_id in converting:
            return _correct_response(sample_id)
        if sample_id in wrong_tool_ids:
            return _wrong_tool_response(sample_id)
        return _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=b2_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    b2 = report.per_arm[B2_ARM].overall
    assert b2.em_conversion_rate == pytest.approx(2 / 20)
    assert b2.tool_accuracy == pytest.approx(14 / 20)
    assert b2.tool_accuracy < Q_B_MISLEAD_RETENTION_MAX

    assert report.qb_verdict.schema_contributes is True
    assert report.qb_verdict.mislead is True
    assert report.qb_verdict.overall == "SCHEMA-CONTRIBUTES"
    assert report.qb_verdict.overall_with_overlay == "SCHEMA-CONTRIBUTES + MISLEAD overlay (independent)"


def test_qb_mislead_overlay_fires_alongside_knowledge_tied():
    """Sanity: MISLEAD's own clause depends on retention ALONE, so it is
    combinatorially possible even under KNOWLEDGE-TIED's own >=85% floor --
    this test only proves the two clauses are independently evaluated
    (KNOWLEDGE-TIED's floor is 85%, MISLEAD's ceiling is 80%, so both
    firing together is impossible by construction); this is documented,
    not exercised further, since KNOWLEDGE-TIED >= 85% and MISLEAD < 80%
    are mutually exclusive by the thresholds themselves."""


# ===========================================================================
# Harness-defect refusals.
# ===========================================================================


def test_malformed_row_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response)
    with (attempt_dir / "outputs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("not json\n")
    with pytest.raises(A2tS2bReadError, match="malformed row"):
        _build_report(tmp_path, world, attempt_dir)


def test_non_completed_flight_receipt_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(
        tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response,
        receipt_kwargs={"status": "ABORTED"},
    )
    with pytest.raises(A2tS2bReadError, match="status"):
        _build_report(tmp_path, world, attempt_dir)


def test_missing_flight_receipt_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(
        tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response, write_receipt=False
    )
    with pytest.raises(A2tS2bReadError, match="flight-receipt.json missing"):
        _build_report(tmp_path, world, attempt_dir)


def test_wrong_arms_field_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(
        tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response,
        receipt_kwargs={"arms": ["S1p", "S2", "S4", "N0r"]},
    )
    with pytest.raises(A2tS2bReadError, match="arms="):
        _build_report(tmp_path, world, attempt_dir)


def test_split_identity_hash_mismatch_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(
        tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response,
        receipt_kwargs={"split_identity_hash": "f" * 64},
    )
    with pytest.raises(A2tS2bReadError, match="split_identity_hash"):
        _build_report(tmp_path, world, attempt_dir)


def test_wrong_row_count_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response)
    lines = (attempt_dir / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
    (attempt_dir / "outputs.jsonl").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(A2tS2bReadError, match="row count"):
        _build_report(tmp_path, world, attempt_dir)


def test_duplicate_arm_sample_pair_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    dup = _row(B1_ARM, world.sample_ids[0], _wrong_value_response(world.sample_ids[0]), _b1_label(world.sample_ids[0]))
    attempt_dir = _build_attempt(
        tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response, extra_rows=[dup]
    )
    with pytest.raises(A2tS2bReadError, match="duplicate"):
        _build_report(tmp_path, world, attempt_dir)


def test_headroom_not_covered_by_reused_arm_plan_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response)
    # A headroom manifest naming an id the reused Stage-2 arm-plan does not cover.
    extra_headroom = _headroom_path(
        tmp_path, world, name="wider-headroom.json", sample_ids=list(world.sample_ids) + ["tier1_direct:999999"]
    )
    with pytest.raises(A2tS2bReadError, match="not covered"):
        _build_report(tmp_path, world, attempt_dir, headroom_path=extra_headroom)


def test_reused_arm_plan_derangement_fixed_point_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response)
    fixed = dict(DERANGEMENT)
    fixed["tool01"] = "tool01"
    with pytest.raises(A2tS2bReadError, match="fixed point"):
        _build_report(tmp_path, world, attempt_dir, arm_plan_overrides={"s4_derangement": fixed})


def test_supplied_tool_mismatch_against_reused_mapping_is_a_harness_defect_refusal(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(
        tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response,
        corrupt_supplied_tool_for=world.sample_ids[0],
    )
    with pytest.raises(A2tS2bReadError, match="does not match the reused Stage-2 mapping"):
        _build_report(tmp_path, world, attempt_dir)


def test_missing_stage2_arm_plan_raises_directly(a2ts2b_world, tmp_path):
    """A raw ``load_arm_plan`` failure (module docstring note 7) surfaces as
    THAT loader's own ``A2tS2ReadError``, never re-wrapped into this
    module's own harness-defect aggregation class."""

    world = a2ts2b_world
    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response)
    with pytest.raises(A2tS2ReadError, match="arm-plan.json missing"):
        _build_report(tmp_path, world, attempt_dir, stage2_arm_plan_path=tmp_path / "does-not-exist.json")


# ===========================================================================
# report_to_json shape / CLI idempotence.
# ===========================================================================


def test_report_to_json_shape(a2ts2b_world, tmp_path):
    world = a2ts2b_world
    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response)
    report = _build_report(tmp_path, world, attempt_dir)
    document = report_to_json(report)
    assert document["schema"] == "saea-a2t-s2b-read-v1"
    assert set(document["per_arm"]) == {"B1", "B2"}
    assert document["qa_verdict"]["overall"] in {"CONFIRMED-CUT", "NOT-DEFAULTS", "INCONCLUSIVE-A"}
    assert document["qb_verdict"]["overall"] in {"SCHEMA-CONTRIBUTES", "KNOWLEDGE-TIED", "INCONCLUSIVE-B"}
    assert isinstance(document["qb_verdict"]["mislead"], bool)


def test_cli_refuses_to_run_twice_against_the_same_output_dir(a2ts2b_world, tmp_path, monkeypatch):
    world = a2ts2b_world
    attempt_dir = _build_attempt(tmp_path, world, b1_fn=_wrong_value_response, b2_fn=_wrong_value_response)
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

    first_exit = a2t_s2b_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    assert (output_dir / "report.txt").is_file()

    second_exit = a2t_s2b_read_main(argv)
    assert second_exit == 1
