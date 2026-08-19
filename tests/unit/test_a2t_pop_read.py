"""``analysis.a2t_pop_read``: the P-A2T whole-population regression-arm
(R0/R1) pinned offline read suite
(docs/readiness/2026-08-19-a2t-pop-preregistration-REGISTERED.md).

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory built on top of a small,
self-contained ``A2tPopWorld`` (4 samples across two tiers, 2 distinct
tools, each with an ``argument_defaults`` literal so the full-registry
induced-substitution yardstick can be exercised directly). This module is
NEVER pointed at the real flight attempt directory
(``$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-pop-194/``); that is a separate,
one-shot registered read.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_pop_read import (
    REGRESSION_COSTLY_DELTA_MIN,
    REGRESSION_SAFE_CI_UPPER_MAX,
    REGRESSION_SAFE_DELTA_MAX,
    RUN_ID,
    A2tPopReadError,
    build_a2t_pop_report,
    compute_delta_reg_bootstrap,
    compute_reachability_statement,
    evaluate_pop_verdict,
    full_registry_supplied_values,
    main as a2t_pop_read_main,
    report_to_json,
    score_row,
)
from speech_aware_evidence_acquisition.analysis.a2t_s2_read import OutputRow
from speech_aware_evidence_acquisition.analysis.bootstrap import BootstrapResult
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import A2T_POP_ARMS, R0_ARM, R1_ARM
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall

# ---------------------------------------------------------------------------
# Lightweight, world-free tests: full_registry_supplied_values / score_row /
# compute_delta_reg_bootstrap / evaluate_pop_verdict / reachability.
# ---------------------------------------------------------------------------


def test_full_registry_supplied_values_reads_every_tool_default():
    rows = [
        {"tool_name": "t1", "argument_defaults": "x='dflt1'"},
        {"tool_name": "t2", "argument_defaults": "y='dflt2'"},
    ]
    values, warnings = full_registry_supplied_values(rows)
    from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import _canonical_value

    assert values == {"x": {_canonical_value("dflt1")}, "y": {_canonical_value("dflt2")}}
    assert warnings == ()


def test_full_registry_supplied_values_collects_non_fatal_parse_warnings():
    rows = [{"tool_name": "t1", "argument_defaults": "@@@ not valid python syntax"}]
    values, warnings = full_registry_supplied_values(rows)
    assert values == {}
    assert len(warnings) == 1
    assert "t1" in warnings[0]


def _mk_row(arm: str, sample_id: str, predicted_name: str, arguments: dict | None = None) -> OutputRow:
    return OutputRow(
        arm=arm,
        sample_id=sample_id,
        supplied_tool=None,
        response=json.dumps([{"name": predicted_name, "arguments": arguments or {}}]),
        timing={"started_at": "2026-08-19T00:00:00+00:00", "latency_seconds": 0.1},
    )


_EXPECTED = {
    "s1": (ToolCall(name="t", arguments={}),),
    "s2": (ToolCall(name="t", arguments={}),),
    "s3": (ToolCall(name="t", arguments={}),),
}


def test_score_row_computes_exact_match_and_empty_call():
    correct = score_row(_mk_row("R0", "s1", "t"), expected_by_id=_EXPECTED, supplied_values={})
    assert correct.item.exact_match == 1.0
    assert not correct.empty_tool_call

    empty = score_row(
        OutputRow(arm="R0", sample_id="s2", supplied_tool=None, response="[]", timing={}),
        expected_by_id=_EXPECTED,
        supplied_values={},
    )
    assert empty.item.exact_match == 0.0
    assert empty.empty_tool_call
    assert empty.parsed


def test_score_row_counts_induced_substitution_against_the_yardstick():
    from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import _canonical_value

    row = _mk_row("R1", "s1", "t", {"z": "registry_default"})
    expected = {"s1": (ToolCall(name="t", arguments={"z": "gold_value"}),)}
    supplied = {"z": {_canonical_value("registry_default")}}
    scored = score_row(row, expected_by_id=expected, supplied_values=supplied)
    assert scored.induced_substitutions == 1


def test_compute_delta_reg_bootstrap_point_estimate_matches_the_raw_delta():
    r0_scores = [
        score_row(_mk_row("R0", sid, "t"), expected_by_id=_EXPECTED, supplied_values={})
        for sid in ("s1", "s2", "s3")
    ]
    r1_scores = [
        score_row(_mk_row("R1", "s1", "t"), expected_by_id=_EXPECTED, supplied_values={}),
        score_row(_mk_row("R1", "s2", "wrong"), expected_by_id=_EXPECTED, supplied_values={}),
        score_row(_mk_row("R1", "s3", "wrong"), expected_by_id=_EXPECTED, supplied_values={}),
    ]
    result = compute_delta_reg_bootstrap(r0_scores, r1_scores, n_replicates=200, seed=1)
    assert result.point_estimate == 2.0  # reg(R1)=2 - reg(R0)=0


def test_compute_delta_reg_bootstrap_is_deterministic():
    r0_scores = [score_row(_mk_row("R0", "s1", "t"), expected_by_id=_EXPECTED, supplied_values={})]
    r1_scores = [score_row(_mk_row("R1", "s1", "wrong"), expected_by_id=_EXPECTED, supplied_values={})]
    first = compute_delta_reg_bootstrap(r0_scores, r1_scores, n_replicates=100, seed=7)
    second = compute_delta_reg_bootstrap(r0_scores, r1_scores, n_replicates=100, seed=7)
    assert first.replicates == second.replicates


def test_compute_delta_reg_bootstrap_rejects_disjoint_arms():
    r0_scores = [score_row(_mk_row("R0", "s1", "t"), expected_by_id=_EXPECTED, supplied_values={})]
    r1_scores = [score_row(_mk_row("R1", "s2", "t"), expected_by_id=_EXPECTED, supplied_values={})]
    with pytest.raises(A2tPopReadError, match="zero paired samples"):
        compute_delta_reg_bootstrap(r0_scores, r1_scores)


def _bootstrap(*, ci_low: float, ci_high: float) -> BootstrapResult:
    return BootstrapResult(
        point_estimate=0.0, replicates=(), sigma_hat=1.0, ci_low=ci_low, ci_high=ci_high,
        ci_level=0.90, n_replicates=10_000, seed=20260807,
    )


def test_evaluate_pop_verdict_regression_safe():
    bootstrap = _bootstrap(ci_low=-1.0, ci_high=REGRESSION_SAFE_CI_UPPER_MAX)
    verdict = evaluate_pop_verdict(reg_r0=1, reg_r1=1 + REGRESSION_SAFE_DELTA_MAX, bootstrap=bootstrap)
    assert verdict.delta_reg == REGRESSION_SAFE_DELTA_MAX
    assert verdict.overall == "REGRESSION-SAFE"


def test_evaluate_pop_verdict_regression_safe_requires_ci_upper_bound_too():
    """Δreg alone within the delta floor is not enough -- the CI upper bound
    must ALSO clear the ceiling (prereg: "Δreg <= 2 AND CI upper <= 5")."""

    bootstrap = _bootstrap(ci_low=-1.0, ci_high=REGRESSION_SAFE_CI_UPPER_MAX + 1.0)
    verdict = evaluate_pop_verdict(reg_r0=0, reg_r1=REGRESSION_SAFE_DELTA_MAX, bootstrap=bootstrap)
    assert verdict.overall != "REGRESSION-SAFE"


def test_evaluate_pop_verdict_regression_costly():
    bootstrap = _bootstrap(ci_low=1.0, ci_high=10.0)
    verdict = evaluate_pop_verdict(reg_r0=0, reg_r1=REGRESSION_COSTLY_DELTA_MIN, bootstrap=bootstrap)
    assert verdict.delta_reg == REGRESSION_COSTLY_DELTA_MIN
    assert verdict.overall == "REGRESSION-COSTLY"


def test_evaluate_pop_verdict_inconclusive_pop():
    """Between the two floors (Δreg=3,4,5 with a CI upper bound that clears
    the safe ceiling) fires neither branch."""

    bootstrap = _bootstrap(ci_low=1.0, ci_high=REGRESSION_SAFE_CI_UPPER_MAX + 1.0)
    verdict = evaluate_pop_verdict(reg_r0=0, reg_r1=3, bootstrap=bootstrap)
    assert verdict.overall == "INCONCLUSIVE-POP"


def test_compute_reachability_statement_reports_r0_regression_count():
    from speech_aware_evidence_acquisition.analysis.a2t_pop_read import ArmAggregate

    agg = ArmAggregate(
        arm=R0_ARM, n_samples=97, tool_accuracy=1.0, regression_count=3, regression_rate=3 / 97,
        slot_f1=1.0, empty_call_rate=0.0, parse_failure_rate=0.0, induced_substitution_count=0,
    )
    statement = compute_reachability_statement(agg)
    assert statement.r0_regression_count == 3
    assert statement.n_samples == 97
    assert "3/97" in statement.detail
    assert "FIRST empirical measurement" in statement.detail


# ---------------------------------------------------------------------------
# A2tPopWorld: 4 samples, 2 tiers (3 + 1), 2 distinct tools, each carrying a
# distinct argument_defaults literal.
# ---------------------------------------------------------------------------

TIER_A = "tier1_direct"  # 3 samples
TIER_B = "tier2_parametric"  # 1 sample
TOOLS = ["tool01", "tool02"]


def _sample_ids() -> list[str]:
    return [f"{TIER_A}:{i:06d}" for i in range(1, 4)] + [f"{TIER_B}:{i:06d}" for i in range(1, 2)]


def _tool_for(sample_id: str) -> str:
    index = int(sample_id.split(":")[1])
    return TOOLS[(index - 1) % len(TOOLS)]


def _gold_value(sample_id: str) -> str:
    return f"gold_{sample_id.replace(':', '_')}"


def _default_value(tool_name: str) -> str:
    return f"default_{tool_name}"


class A2tPopWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "a2tpop-data"
        self.repo_root = tmp_path / "a2tpop-repo"
        self.lock_path = tmp_path / "a2tpop-lock.json"
        self.carrier_dir = self.data_root / "datasets" / "audio2tool"
        self.public = self.carrier_dir / "public"
        self.receipt_path = self.repo_root / "docs" / "receipts" / "probe-samples" / "r1-a2t-pop-test.json"
        self.sample_ids = _sample_ids()
        self._materialize()
        self._write_lock()

    def _materialize(self) -> None:
        entries_by_tier: dict[str, list[dict]] = {TIER_A: [], TIER_B: []}
        for sample_id in self.sample_ids:
            tier, id_str = sample_id.split(":")
            item_id = int(id_str)
            tool = _tool_for(sample_id)
            entries_by_tier[tier].append(
                {
                    "id": item_id,
                    "tier": tier,
                    "query_idx": item_id,
                    "query": f"do something with {tool}",
                    "domain": "test",
                    "category": "test",
                    "tool_id": TOOLS.index(tool) + 1,
                    "tool_name": tool,
                    "expected_tool_call": f"{tool}(x='{_gold_value(sample_id)}')",
                    "extracted_params": {},
                    "additional_tool_calls": None,
                    "path": f"{tier}_audios/query_{item_id:05d}/turn.wav",
                    "duration": 0.5,
                }
            )
        for tier, entries in entries_by_tier.items():
            manifest = self.public / f"{tier}_data" / f"{tier}.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps(entries), encoding="utf-8")

        self.carrier_dir.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "tool_id", "domain", "category", "tool_name", "signature", "description",
            "argument_defaults", "argument_constraints",
        ]
        with (self.carrier_dir / "tools_registry.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for tool in TOOLS:
                writer.writerow(
                    {
                        "tool_id": str(TOOLS.index(tool) + 1),
                        "domain": "test",
                        "category": "test",
                        "tool_name": tool,
                        "signature": f"{tool}(x: String)",
                        "description": f"{tool} description",
                        "argument_defaults": f"x='{_default_value(tool)}'",
                        "argument_constraints": "",
                    }
                )

        from speech_aware_evidence_acquisition.reproduction.sampling import (
            split_identity_hash as compute_hash,
        )

        items = []
        for sample_id in self.sample_ids:
            tier, id_str = sample_id.split(":")
            items.append({"id": int(id_str), "key": f"audio2tool:{sample_id}", "query_idx": int(id_str), "tier": tier})
        payload = {
            "probe": "R1-a2t-pop-test",
            "carrier": "audio2tool",
            "seed": 1,
            "design": "synthetic a2t_pop_read test receipt",
            "pool_size": len(items),
            "strata_counts": {},
            "items": items,
            "split_identity_hash": compute_hash([item["key"] for item in items]),
            "split_role": "discovery",
        }
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _write_lock(self) -> None:
        document = {
            "asset_catalog": [
                {
                    "name": "audio2tool",
                    "kind": "dataset",
                    "local_subdir": "datasets/audio2tool",
                    "license": "cc-by-nc-4.0",
                    "lifecycle": "STAGE2_CANDIDATE",
                    "profiles": ["speech-aware-secondary"],
                }
            ],
            "models": [],
        }
        self.lock_path.write_text(json.dumps(document), encoding="utf-8")

    @property
    def split_identity_hash(self) -> str:
        return json.loads(self.receipt_path.read_text(encoding="utf-8"))["split_identity_hash"]


@pytest.fixture()
def a2tpop_world(tmp_path):
    return A2tPopWorld(tmp_path)


# ---------------------------------------------------------------------------
# Response-text builders.
# ---------------------------------------------------------------------------


def _correct_response(sample_id: str) -> str:
    tool = _tool_for(sample_id)
    return json.dumps([{"name": tool, "arguments": {"x": _gold_value(sample_id)}}])


def _wrong_value_response(sample_id: str) -> str:
    """Correct tool, a value that is neither gold nor the registry default
    -- tool_accuracy=1, exact_match=0 (a regression), induced=0."""

    tool = _tool_for(sample_id)
    return json.dumps([{"name": tool, "arguments": {"x": "totally_unrelated_value"}}])


def _copy_default_response(sample_id: str) -> str:
    """Correct tool, the value == the FULL REGISTRY's own default for this
    tool -- tool_accuracy=1, exact_match=0 (a regression), induced=1."""

    tool = _tool_for(sample_id)
    return json.dumps([{"name": tool, "arguments": {"x": _default_value(tool)}}])


_EMPTY_RESPONSE = "[]"


# ---------------------------------------------------------------------------
# Fixture builders: outputs.jsonl / flight-receipt.json.
# ---------------------------------------------------------------------------


def _row(arm: str, sample_id: str, response: str) -> dict:
    return {
        "arm": arm,
        "sample_id": sample_id,
        "supplied_tool": "unused",
        "response": response,
        "timing": {"started_at": "2026-08-19T00:00:00+00:00", "latency_seconds": 0.1},
    }


def _write_outputs_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write((json.dumps(row) if isinstance(row, dict) else row) + "\n")


def _write_flight_receipt(
    path: Path, *, split_identity_hash: str, status: str = "COMPLETED", arms: list | None = None,
    request_failures: list | None = None,
) -> None:
    document = {
        "status": status,
        "error": None,
        "arms": arms if arms is not None else list(A2T_POP_ARMS),
        "split_identity_hash": split_identity_hash,
        "request_failures": request_failures if request_failures is not None else [],
    }
    path.write_text(json.dumps(document), encoding="utf-8")


def _build_attempt(
    tmp_path: Path, world: A2tPopWorld, *, r0_fn, r1_fn, name: str = "attempt",
    write_receipt: bool = True, receipt_kwargs: dict | None = None, extra_rows: list | None = None,
    r0_ids: list[str] | None = None, r1_ids: list[str] | None = None,
) -> Path:
    attempt_dir = tmp_path / name
    r0_ids = list(world.sample_ids) if r0_ids is None else r0_ids
    r1_ids = list(world.sample_ids) if r1_ids is None else r1_ids
    rows = [_row(R0_ARM, sid, r0_fn(sid)) for sid in r0_ids]
    rows += [_row(R1_ARM, sid, r1_fn(sid)) for sid in r1_ids]
    if extra_rows:
        rows.extend(extra_rows)
    _write_outputs_jsonl(attempt_dir / "outputs.jsonl", rows)
    if write_receipt:
        kwargs = dict(split_identity_hash=world.split_identity_hash)
        kwargs.update(receipt_kwargs or {})
        _write_flight_receipt(attempt_dir / "flight-receipt.json", **kwargs)
    return attempt_dir


def _build_report(tmp_path, world, attempt_dir, **kwargs):
    lock = load_lock(world.lock_path)
    kwargs.setdefault("expected_n", len(world.sample_ids))
    return build_a2t_pop_report(attempt_dir, lock, world.data_root, repo_root=world.repo_root, **kwargs)


# ---------------------------------------------------------------------------
# Happy-path build_a2t_pop_report + verdict wiring.
# ---------------------------------------------------------------------------


def test_build_report_happy_path_regression_safe(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response)
    report = _build_report(tmp_path, world, attempt_dir)

    assert report.per_arm[R0_ARM].overall.regression_count == 0
    assert report.per_arm[R1_ARM].overall.regression_count == 0
    assert report.verdict.delta_reg == 0
    assert report.verdict.overall == "REGRESSION-SAFE"
    assert report.reachability.r0_regression_count == 0


def test_build_report_induced_substitution_counted_against_full_registry(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(tmp_path, world, r0_fn=_correct_response, r1_fn=_copy_default_response)
    report = _build_report(tmp_path, world, attempt_dir)

    assert report.per_arm[R1_ARM].overall.regression_count == len(world.sample_ids)
    assert report.per_arm[R1_ARM].overall.induced_substitution_count == len(world.sample_ids)
    # R1's own prompt STRIPS defaults (values-stripped self-supplied row) --
    # the yardstick still catches the model reproducing a value it was never
    # literally shown (module docstring: "a STRONGER, not weaker, guardrail").


def test_build_report_wrong_value_is_a_regression_without_induced_substitution(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(tmp_path, world, r0_fn=_correct_response, r1_fn=_wrong_value_response)
    report = _build_report(tmp_path, world, attempt_dir)

    assert report.per_arm[R1_ARM].overall.regression_count == len(world.sample_ids)
    assert report.per_arm[R1_ARM].overall.induced_substitution_count == 0


def test_build_report_empty_call_is_a_regression_and_counted_empty(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=lambda sid: _EMPTY_RESPONSE
    )
    report = _build_report(tmp_path, world, attempt_dir)

    r1 = report.per_arm[R1_ARM].overall
    assert r1.regression_count == len(world.sample_ids)
    assert r1.empty_call_rate == 1.0
    assert r1.tool_accuracy == 0.0


def test_build_report_per_tier_breakdown_covers_both_tiers(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response)
    report = _build_report(tmp_path, world, attempt_dir)
    assert set(report.per_arm[R0_ARM].by_tier) == {TIER_A, TIER_B}
    assert report.per_arm[R0_ARM].by_tier[TIER_A].n_samples == 3
    assert report.per_arm[R0_ARM].by_tier[TIER_B].n_samples == 1


def test_report_to_json_shape(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response)
    report = _build_report(tmp_path, world, attempt_dir)
    document = report_to_json(report)
    assert document["schema"] == "saea-a2t-pop-read-v1"
    assert document["run_id"] == RUN_ID
    assert set(document["per_arm"]) == set(A2T_POP_ARMS)
    assert document["verdict"]["overall"] == "REGRESSION-SAFE"
    assert "bootstrap" in document["verdict"]
    assert "detail" in document["reachability"]


# ---------------------------------------------------------------------------
# Harness-defect checks (fail-closed refusal, never a soft flag).
# ---------------------------------------------------------------------------


def test_build_report_rejects_malformed_row(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response)
    with (attempt_dir / "outputs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("not json at all\n")
    with pytest.raises(A2tPopReadError, match="malformed"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_non_completed_status(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response,
        receipt_kwargs={"status": "FAILED"},
    )
    with pytest.raises(A2tPopReadError, match="COMPLETED"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_non_empty_request_failures(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response,
        receipt_kwargs={"request_failures": [{"sample_id": "x"}]},
    )
    with pytest.raises(A2tPopReadError, match="request_failures"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_unexpected_arms_field(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response,
        receipt_kwargs={"arms": ["R0"]},
    )
    with pytest.raises(A2tPopReadError, match="arms"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_split_identity_hash_mismatch(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response,
        receipt_kwargs={"split_identity_hash": "deadbeef" * 8},
    )
    with pytest.raises(A2tPopReadError, match="split_identity_hash mismatch"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_unknown_arm_row(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response,
        extra_rows=[_row("R2", world.sample_ids[0], _correct_response(world.sample_ids[0]))],
    )
    with pytest.raises(A2tPopReadError, match="unknown arm"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_duplicate_arm_sample_pair(a2tpop_world, tmp_path):
    world = a2tpop_world
    dup_row = _row(R0_ARM, world.sample_ids[0], _correct_response(world.sample_ids[0]))
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response, extra_rows=[dup_row]
    )
    with pytest.raises(A2tPopReadError, match="duplicate row"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_wrong_row_count_per_arm(a2tpop_world, tmp_path):
    world = a2tpop_world
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response,
        r0_ids=world.sample_ids[:-1],  # one short
    )
    with pytest.raises(A2tPopReadError, match="97/97 fail-closed check"):
        _build_report(tmp_path, world, attempt_dir)


def test_build_report_rejects_r0_r1_id_set_mismatch(a2tpop_world, tmp_path):
    world = a2tpop_world
    swapped_ids = world.sample_ids[:-1] + ["tier1_direct:999999"]
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response, r1_ids=swapped_ids,
    )
    with pytest.raises(A2tPopReadError, match="PAIRED population"):
        _build_report(
            tmp_path, world, attempt_dir,
        )


# ---------------------------------------------------------------------------
# CLI: end-to-end + one-shot idempotence guard.
# ---------------------------------------------------------------------------


def _cli_repo_layout(tmp_path: Path, world: A2tPopWorld) -> Path:
    repo_root = tmp_path / "umbrella" / "studies" / "study"
    receipts_dir = repo_root / "docs" / "receipts" / "probe-samples"
    receipts_dir.mkdir(parents=True)
    (receipts_dir / world.receipt_path.name).write_text(
        world.receipt_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_cli_refuses_to_run_twice_against_the_same_output_dir(a2tpop_world, tmp_path, monkeypatch):
    world = a2tpop_world
    attempt_dir = _build_attempt(tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response)
    repo_root = _cli_repo_layout(tmp_path, world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [
        str(attempt_dir), "--output-dir", str(output_dir), "--repo-root", str(repo_root),
        "--expected-n", str(len(world.sample_ids)),
    ]

    first_exit = a2t_pop_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    assert (output_dir / "report.txt").is_file()

    second_exit = a2t_pop_read_main(argv)
    assert second_exit == 1


def test_cli_refuses_on_harness_defect(a2tpop_world, tmp_path, monkeypatch):
    world = a2tpop_world
    attempt_dir = _build_attempt(
        tmp_path, world, r0_fn=_correct_response, r1_fn=_correct_response,
        receipt_kwargs={"status": "FAILED"},
    )
    repo_root = _cli_repo_layout(tmp_path, world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    exit_code = a2t_pop_read_main(
        [
            str(attempt_dir), "--output-dir", str(output_dir), "--repo-root", str(repo_root),
            "--expected-n", str(len(world.sample_ids)),
        ]
    )
    assert exit_code == 1
    assert not (output_dir / "verdict.json").exists()
