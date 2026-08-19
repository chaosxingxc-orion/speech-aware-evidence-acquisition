"""``analysis.ptrap_read``: the P-TRAP pinned offline read suite (the
A0-value harvester, the capture detector, the CI-gated verdict evaluator,
and the mandatory reachability statement).

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory or a synthetic gold/response
fixture. This module is NEVER pointed at the real consumed P-SLU attempt
directory or a real P-TRAP flight attempt; those are separate, one-shot
registered reads (module docstring of ``analysis.ptrap_read`` itself).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.ptrap_read import (
    ACOUSTIC_MEDIATED_MIN_RAW_DIFF,
    CONSUMED_PSLU_ARM,
    PTrapReadError,
    PTrapSampleRow,
    build_ptrap_report,
    compute_capture_bootstrap,
    compute_reachability_statement,
    evaluate_point,
    evaluate_ptrap_ci_gated,
    harvest_a0_wrong_values,
    main as ptrap_read_main,
    report_to_json,
    response_captures_trap,
)
from speech_aware_evidence_acquisition.analysis.bootstrap import BootstrapResult
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.ptrap_flight import V1_ARM, V2_ARM
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

ARMS = ("A0",)


# ---------------------------------------------------------------------------
# Synthetic SLURP gold world -- 3 devel samples: 101 (scenario "iot", TWO
# gold entities, for the cross-slot zero-overlap harvester test), 900/901
# (scenario "email", no gold entities -- every A0 prediction there is
# automatically "wrong").
# ---------------------------------------------------------------------------


def _write_flac(path: Path, *, sample_rate_hz: int = 16000, seconds: float = 0.2) -> None:
    import numpy as np
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate_hz * seconds)
    sf.write(str(path), np.zeros(frames, dtype="float32"), sample_rate_hz, format="FLAC")


def _tokens(*surfaces: str) -> list[dict]:
    return [{"surface": s, "id": i, "lemma": s, "pos": "NN"} for i, s in enumerate(surfaces)]


DEVEL_RECORDS = [
    {
        "slurp_id": 101,
        "sentence": "wake me at six near the kitchen",
        "sentence_annotation": "wake me at [time : six] near the [house_place : kitchen]",
        "intent": "alarm_set",
        "scenario": "iot",
        "action": "hue_lighton",
        "tokens": _tokens("wake", "me", "at", "six", "near", "the", "kitchen"),
        "entities": [{"span": [3], "type": "time"}, {"span": [6], "type": "house_place"}],
        "recordings": [{"file": "audio-101.flac", "wer": 0.0, "ent_wer": 0.0, "status": "correct"}],
    },
    {
        "slurp_id": 900,
        "sentence": "check my email",
        "sentence_annotation": "check my email",
        "intent": "email_query",
        "scenario": "email",
        "action": "query",
        "tokens": _tokens("check", "my", "email"),
        "entities": [],
        "recordings": [{"file": "audio-900.flac", "wer": 0.0, "ent_wer": None, "status": "correct"}],
    },
    {
        "slurp_id": 901,
        "sentence": "any new email",
        "sentence_annotation": "any new email",
        "intent": "email_query",
        "scenario": "email",
        "action": "query",
        "tokens": _tokens("any", "new", "email"),
        "entities": [],
        "recordings": [{"file": "audio-901.flac", "wer": 0.0, "ent_wer": None, "status": "correct"}],
    },
]


class SlurpReadWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "data"
        self.lock_path = tmp_path / "lock.json"
        audio_root = self.data_root / "datasets" / "slurp"
        metadata_dir = audio_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        (metadata_dir / "devel.jsonl").write_text(
            "\n".join(json.dumps(r) for r in DEVEL_RECORDS) + "\n", encoding="utf-8"
        )
        real_dir = audio_root / "slurp_real"
        for record in DEVEL_RECORDS:
            for recording in record["recordings"]:
                _write_flac(real_dir / recording["file"])
        lock_doc = {
            "datasets": [
                {
                    "name": "slurp",
                    "kind": "dataset",
                    "local_subdir": "repos/slurp/scripts/audio",
                    "license": "mixed: textual part CC BY 4.0, audio part CC BY-NC 4.0",
                    "annotations": {"governed_copy": "datasets/slurp/metadata"},
                }
            ]
        }
        self.lock_path.write_text(json.dumps(lock_doc), encoding="utf-8")
        self.lock = load_lock(self.lock_path)
        self.adapter = SlurpAdapter(self.lock, self.data_root)
        samples = {s.sample_id: s for s in self.adapter.load_split("devel")}
        self.sid = {record["slurp_id"]: self._find(samples, record["slurp_id"]) for record in DEVEL_RECORDS}

    @staticmethod
    def _find(samples: dict, slurp_id: int):
        needle = f":{slurp_id:06d}:"
        for sample_id, sample in samples.items():
            if needle in sample_id:
                return sample
        raise KeyError(slurp_id)


@pytest.fixture()
def read_world(tmp_path):
    return SlurpReadWorld(tmp_path)


def _resp(scenario: str | None, action: str | None, entities: list[tuple[str, str]]) -> str:
    return json.dumps(
        {"scenario": scenario, "action": action, "entities": [{"type": t, "filler": f} for t, f in entities]}
    )


def _pslu_a0_row(world: SlurpReadWorld, sample, response_text: str, *, silence_swapped: bool = False, arm: str = "A0") -> dict:
    metrics = dict(world.adapter.score(sample, response_text))
    return {
        "arm": arm,
        "sample_id": sample.sample_id,
        "silence_swapped": silence_swapped,
        "phase1_scenario_parsed": None,
        "messages": list(world.adapter.assemble_prompt(sample, None)),
        "response_text": response_text,
        "metrics": metrics,
        "consumption": {"records": []},
    }


def _write_attempt_dir(path: Path, rows: list[dict], *, status: str = "COMPLETED", error=None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (path / "flight-receipt.json").write_text(json.dumps({"status": status, "error": error}), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. THE A0-VALUE HARVESTER.
# ---------------------------------------------------------------------------


def test_harvest_a0_wrong_values_basic_and_dedupes_and_caps_nothing(read_world, tmp_path):
    """Sample 101's A0 response emits its OWN correct time=six plus SIX
    distinct wrong entities (one repeated once, for the dedupe check) --
    the harvester returns ALL of them uncapped (K-capping is
    rails.probes.ptrap_flight.build_trap_sets's own job, downstream)."""

    world = read_world
    s101 = world.sid[101]
    response_101 = _resp(
        "iot", "hue_lighton",
        [
            ("time", "six"),  # matches gold -- never "wrong"
            ("date", "tuesday"),
            ("date", "tuesday"),  # duplicate -- must be deduped
            ("person", "bob"),
            ("person", "alice"),
            ("business_name", "acme"),
            ("place_name", "paris"),
            ("currency_name", "dollar"),
        ],
    )
    rows = [_pslu_a0_row(world, s101, response_101)]
    for slurp_id, response in ((900, _resp("email", "query", [])), (901, _resp("email", "query", [("email_folder", "promotions")]))):
        rows.append(_pslu_a0_row(world, world.sid[slurp_id], response))
    attempt_dir = _write_attempt_dir(tmp_path / "pslu-attempt", rows)

    gold_by_sample_id = {sample.sample_id: sample for sample in world.sid.values()}
    yielded = harvest_a0_wrong_values(attempt_dir, gold_by_sample_id)

    wrong_101 = yielded.wrong_values_by_sample[s101.sample_id]
    assert [w.filler for w in wrong_101] == ["tuesday", "bob", "alice", "acme", "paris", "dollar"]
    assert yielded.per_sample_wrong_value_counts[s101.sample_id] == 6

    assert world.sid[900].sample_id in yielded.samples_with_zero_wrong_values
    assert world.sid[901].sample_id not in yielded.samples_with_zero_wrong_values
    assert yielded.per_sample_wrong_value_counts[world.sid[901].sample_id] == 1
    assert yielded.total_wrong_value_count == 6 + 0 + 1


def test_harvest_a0_wrong_values_ignores_silence_swapped_rows(read_world, tmp_path):
    world = read_world
    s900 = world.sid[900]
    real_row = _pslu_a0_row(world, s900, _resp("email", "query", []))
    silence_row = _pslu_a0_row(world, s900, _resp("email", "query", [("email_folder", "spam")]), silence_swapped=True)
    attempt_dir = _write_attempt_dir(tmp_path / "pslu-attempt", [real_row, silence_row])

    gold_by_sample_id = {sample.sample_id: sample for sample in world.sid.values()}
    yielded = harvest_a0_wrong_values(attempt_dir, gold_by_sample_id)
    assert s900.sample_id in yielded.samples_with_zero_wrong_values  # the silence row's own "spam" is IGNORED


def test_harvest_a0_wrong_values_ignores_non_a0_arms(read_world, tmp_path):
    world = read_world
    s900 = world.sid[900]
    a0_row = _pslu_a0_row(world, s900, _resp("email", "query", []))
    other_row = _pslu_a0_row(world, s900, _resp("email", "query", [("email_folder", "spam")]), arm="A3")
    attempt_dir = _write_attempt_dir(tmp_path / "pslu-attempt", [a0_row, other_row])

    gold_by_sample_id = {sample.sample_id: sample for sample in world.sid.values()}
    yielded = harvest_a0_wrong_values(attempt_dir, gold_by_sample_id)
    assert s900.sample_id in yielded.samples_with_zero_wrong_values


def test_harvest_a0_wrong_values_refuses_when_no_a0_rows(read_world, tmp_path):
    world = read_world
    s900 = world.sid[900]
    other_row = _pslu_a0_row(world, s900, _resp("email", "query", []), arm="A3")
    attempt_dir = _write_attempt_dir(tmp_path / "pslu-attempt", [other_row])

    gold_by_sample_id = {sample.sample_id: sample for sample in world.sid.values()}
    with pytest.raises(PTrapReadError, match="zero non-silence-swapped"):
        harvest_a0_wrong_values(attempt_dir, gold_by_sample_id)


def test_consumed_pslu_arm_is_a0():
    assert CONSUMED_PSLU_ARM == "A0"


# ---------------------------------------------------------------------------
# 2. Capture detector -- normalization cases.
# ---------------------------------------------------------------------------


def test_response_captures_trap_true_on_exact_match():
    predicted = (SlotEntity(type="date", filler="tuesday"),)
    traps = ({"filler": "tuesday"},)
    assert response_captures_trap(predicted, traps) is True


def test_response_captures_trap_false_when_no_trap_entries():
    predicted = (SlotEntity(type="date", filler="tuesday"),)
    assert response_captures_trap(predicted, ()) is False


def test_response_captures_trap_ignores_entity_type_only_value_matters():
    predicted = (SlotEntity(type="person", filler="tuesday"),)  # WRONG type vs the trap's own "date"
    traps = ({"type": "date", "filler": "tuesday"},)
    assert response_captures_trap(predicted, traps) is True


def test_response_captures_trap_normalizes_case_and_punctuation():
    predicted = (SlotEntity(type="business_name", filler="Acme, Inc."),)
    traps = ({"filler": "acme inc"},)
    assert response_captures_trap(predicted, traps) is True


def test_response_captures_trap_normalizes_whitespace():
    predicted = (SlotEntity(type="place_name", filler="new   york"),)
    traps = ({"filler": "new york"},)
    assert response_captures_trap(predicted, traps) is True


def test_response_captures_trap_false_on_a_genuine_mismatch():
    predicted = (SlotEntity(type="date", filler="wednesday"),)
    traps = ({"filler": "tuesday"},)
    assert response_captures_trap(predicted, traps) is False


def test_response_captures_trap_true_when_any_of_several_predicted_entities_matches():
    predicted = (SlotEntity(type="time", filler="six"), SlotEntity(type="date", filler="tuesday"))
    traps = ({"filler": "monday"}, {"filler": "tuesday"})
    assert response_captures_trap(predicted, traps) is True


# ---------------------------------------------------------------------------
# 3. Reachability arithmetic.
# ---------------------------------------------------------------------------


def _sample_row(sample_id: str, *, v1_k: int, v1_captured: bool = False, v2_captured: bool = False, v2_k: int | None = None) -> PTrapSampleRow:
    return PTrapSampleRow(
        sample_id=sample_id,
        v1_k=v1_k,
        v2_k=v2_k if v2_k is not None else v1_k,
        v1_captured=v1_captured,
        v2_captured=v2_captured,
        v1_parsed=True,
        v2_parsed=True,
        v1_induced_substitutions=0,
        v2_induced_substitutions=0,
    )


def test_reachability_statement_reachable_when_n_usable_at_least_six():
    per_sample = [_sample_row(f"s{i}", v1_k=1) for i in range(6)] + [_sample_row("s6", v1_k=0)]
    statement = compute_reachability_statement(per_sample, n_samples=7)
    assert statement.n_usable == 6
    assert statement.max_attainable_raw_diff == 6
    assert statement.max_attainable_rate_diff == 1.0
    assert statement.acoustic_mediated_reachable is True


def test_reachability_statement_unreachable_when_n_usable_below_six():
    per_sample = [_sample_row(f"s{i}", v1_k=1) for i in range(5)]
    statement = compute_reachability_statement(per_sample, n_samples=5)
    assert statement.n_usable == 5
    assert statement.max_attainable_raw_diff == 5
    assert statement.acoustic_mediated_reachable is False


def test_reachability_statement_zero_usable_is_unreachable():
    per_sample = [_sample_row("s0", v1_k=0), _sample_row("s1", v1_k=0)]
    statement = compute_reachability_statement(per_sample, n_samples=2)
    assert statement.n_usable == 0
    assert statement.max_attainable_rate_diff == 0.0
    assert statement.max_attainable_raw_diff == 0
    assert statement.acoustic_mediated_reachable is False


# ---------------------------------------------------------------------------
# 4. K=0 exclusion accounting (evaluate_point + the common-denominator rule).
# ---------------------------------------------------------------------------


def test_k_zero_samples_are_excluded_from_the_common_denominator_by_construction():
    """PTrapSampleRow.usable is exactly the V1-K>=1 rule; a caller building
    the common denominator (as analysis.ptrap_read.build_ptrap_report does)
    filters on it directly."""

    rows = [
        _sample_row("usable-1", v1_k=2, v1_captured=True),
        _sample_row("usable-2", v1_k=1, v1_captured=False),
        _sample_row("excluded-1", v1_k=0),
        _sample_row("excluded-2", v1_k=0),
    ]
    denominator = [row for row in rows if row.usable]
    assert {row.sample_id for row in denominator} == {"usable-1", "usable-2"}
    assert len(denominator) == 2


# ---------------------------------------------------------------------------
# 5. evaluate_point -- the registered point thresholds.
# ---------------------------------------------------------------------------


def test_evaluate_point_acoustic_mediated_point_clause_needs_both_rate_and_raw_floor():
    met = evaluate_point(rate_diff=0.10, raw_diff=6)
    assert met.acoustic_mediated_point.verdict == "met"

    rate_only = evaluate_point(rate_diff=0.50, raw_diff=3)  # big rate, small n -- raw floor not met
    assert rate_only.acoustic_mediated_point.verdict == "not_met"

    raw_only = evaluate_point(rate_diff=0.05, raw_diff=10)  # rate floor not met
    assert raw_only.acoustic_mediated_point.verdict == "not_met"


def test_evaluate_point_key_only_matching_point_clause():
    assert evaluate_point(rate_diff=0.03, raw_diff=1).key_only_matching_point.verdict == "met"
    assert evaluate_point(rate_diff=-0.03, raw_diff=-1).key_only_matching_point.verdict == "met"
    assert evaluate_point(rate_diff=0.031, raw_diff=1).key_only_matching_point.verdict == "not_met"


# ---------------------------------------------------------------------------
# 6. The bootstrap + the CI-gated verdict evaluator -- ALL branches.
# ---------------------------------------------------------------------------


def _bootstrap(*, point_estimate: float, ci_low: float, ci_high: float) -> BootstrapResult:
    return BootstrapResult(
        point_estimate=point_estimate,
        replicates=(point_estimate,) * 100,
        sigma_hat=(ci_high - ci_low) / 4.0,
        ci_low=ci_low,
        ci_high=ci_high,
        ci_level=0.90,
        n_replicates=100,
        seed=20260807,
    )


def _reachability(*, n_usable: int) -> "object":
    from speech_aware_evidence_acquisition.analysis.ptrap_read import ReachabilityStatement

    reachable = n_usable >= ACOUSTIC_MEDIATED_MIN_RAW_DIFF
    return ReachabilityStatement(
        n_samples=60,
        n_usable=n_usable,
        max_attainable_rate_diff=1.0 if n_usable else 0.0,
        max_attainable_raw_diff=n_usable,
        acoustic_mediated_reachable=reachable,
        detail="synthetic fixture",
    )


def test_ci_gated_acoustic_mediated_fires_when_point_and_ci_both_qualify():
    point = evaluate_point(rate_diff=0.20, raw_diff=10)
    bootstrap = _bootstrap(point_estimate=0.20, ci_low=0.02, ci_high=0.38)
    reachability = _reachability(n_usable=20)
    verdict = evaluate_ptrap_ci_gated(point, bootstrap, reachability)
    assert verdict.acoustic_mediated.verdict == "met"
    assert verdict.overall == "ACOUSTIC-MEDIATED"


def test_ci_gated_acoustic_mediated_not_met_when_ci_crosses_zero():
    """Point thresholds are met, but the bootstrap CI still contains (or is
    entirely below) zero -- the 2026-08-19 amendment's own ci_low>0
    requirement blocks the affirmative verdict."""

    point = evaluate_point(rate_diff=0.15, raw_diff=6)
    bootstrap = _bootstrap(point_estimate=0.15, ci_low=-0.01, ci_high=0.31)
    reachability = _reachability(n_usable=10)
    verdict = evaluate_ptrap_ci_gated(point, bootstrap, reachability)
    assert verdict.acoustic_mediated.verdict == "not_met"
    assert verdict.overall != "ACOUSTIC-MEDIATED"


def test_ci_gated_key_only_matching_fires_when_point_ci_and_reachability_all_qualify():
    point = evaluate_point(rate_diff=0.01, raw_diff=0)
    bootstrap = _bootstrap(point_estimate=0.01, ci_low=-0.02, ci_high=0.025)
    reachability = _reachability(n_usable=20)  # reachable: n_usable >= 6
    verdict = evaluate_ptrap_ci_gated(point, bootstrap, reachability)
    assert verdict.key_only_matching.verdict == "met"
    assert verdict.overall == "KEY-ONLY-MATCHING"


def test_ci_gated_key_only_matching_blocked_by_a_ci_crossing_the_band_yields_inconclusive():
    """Explicit CI-crossing case: the point estimate sits inside the
    +/-0.03 band, but the CI itself is NOT entirely inside it -- MUST fall
    to INCONCLUSIVE-TRAP, never an affirmative KEY-ONLY-MATCHING."""

    point = evaluate_point(rate_diff=0.02, raw_diff=1)
    bootstrap = _bootstrap(point_estimate=0.02, ci_low=-0.05, ci_high=0.09)  # crosses the band
    reachability = _reachability(n_usable=20)
    verdict = evaluate_ptrap_ci_gated(point, bootstrap, reachability)
    assert verdict.key_only_matching.verdict == "not_met"
    assert verdict.acoustic_mediated.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-TRAP"


def test_ci_gated_key_only_matching_blocked_by_unreachability_yields_inconclusive():
    """Mirrors the P-KEY 2026-08-19 amendment item 2 gate: an equivalence
    verdict may not fire as an affirmative negative under an unreachable
    alternative."""

    point = evaluate_point(rate_diff=0.0, raw_diff=0)
    bootstrap = _bootstrap(point_estimate=0.0, ci_low=-0.01, ci_high=0.01)
    reachability = _reachability(n_usable=3)  # UNREACHABLE: n_usable < 6
    verdict = evaluate_ptrap_ci_gated(point, bootstrap, reachability)
    assert verdict.key_only_matching.verdict == "not_met"
    assert "UNREACHABLE" in verdict.key_only_matching.detail
    assert verdict.overall == "INCONCLUSIVE-TRAP"


def test_ci_gated_inconclusive_when_neither_branch_qualifies():
    point = evaluate_point(rate_diff=0.06, raw_diff=4)  # between the two bands entirely
    bootstrap = _bootstrap(point_estimate=0.06, ci_low=0.01, ci_high=0.11)
    reachability = _reachability(n_usable=20)
    verdict = evaluate_ptrap_ci_gated(point, bootstrap, reachability)
    assert verdict.acoustic_mediated.verdict == "not_met"
    assert verdict.key_only_matching.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-TRAP"


def test_compute_capture_bootstrap_refuses_an_empty_common_denominator():
    with pytest.raises(PTrapReadError, match="empty common denominator"):
        compute_capture_bootstrap(v1_captured_by_sample={}, v2_captured_by_sample={}, common_denominator=())


def test_compute_capture_bootstrap_is_paired_and_deterministic():
    v1 = {"s1": True, "s2": False, "s3": True}
    v2 = {"s1": False, "s2": False, "s3": False}
    first = compute_capture_bootstrap(v1_captured_by_sample=v1, v2_captured_by_sample=v2, common_denominator=["s1", "s2", "s3"], n_replicates=500)
    second = compute_capture_bootstrap(v1_captured_by_sample=v1, v2_captured_by_sample=v2, common_denominator=["s1", "s2", "s3"], n_replicates=500)
    assert first.replicates == second.replicates
    assert first.point_estimate == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# 7. Full read-suite integration (build_ptrap_report / report_to_json /
#    the idempotence guard) over a hand-authored synthetic attempt dir.
# ---------------------------------------------------------------------------


def _ptrap_row(world: SlurpReadWorld, sample, arm: str, response_text: str, trap_entries: tuple[dict, ...]) -> dict:
    metrics = dict(world.adapter.score(sample, response_text))
    return {
        "arm": arm,
        "sample_id": sample.sample_id,
        "messages": list(world.adapter.assemble_prompt(sample, None)),
        "response_text": response_text,
        "metrics": metrics,
        "consumption": {"records": []},
        "k": len(trap_entries),
        "trap_entries": list(trap_entries),
    }


def _write_ptrap_attempt_dir(path: Path, rows: list[dict], *, status: str = "COMPLETED", error=None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (path / "flight-receipt.json").write_text(json.dumps({"status": status, "error": error}), encoding="utf-8")
    return path


def _manifest_and_roster_paths(world: SlurpReadWorld, tmp_path: Path) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    roster_doc = {
        "probe": "P-SLU",
        "legality_tier": "legal",
        "train_synthetic_refused": {"train_jsonl_overlap_with_devel": 0},
        "arms": {
            "A1_scenario_roster": {"rosters": {"iot": [["house_place", "bedroom"]], "email": [["email_folder", "inbox"]]}},
            "A2_global_type_vocabulary": {"types": ["house_place", "email_folder"]},
            "A3_full_ontology_dose_capped": {"roster": [["house_place", "bedroom"], ["email_folder", "inbox"]]},
            "A4_deranged": {"mapping": {"iot": "email", "email": "iot"}},
        },
    }
    roster_table_path = tmp_path / "rosters.json"
    roster_table_path.write_text(json.dumps(roster_doc), encoding="utf-8")

    manifest_doc = {
        "probe": "P-SLU",
        "seed": 20260807,
        "split_identity_hash": "a" * 64,
        "items": [{"sample_id": world.sid[slurp_id].sample_id} for slurp_id in (101, 900, 901)],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_doc), encoding="utf-8")
    return manifest_path, roster_table_path


def _build_report(world: SlurpReadWorld, tmp_path: Path):
    s101, s900, s901 = world.sid[101], world.sid[900], world.sid[901]
    trap_101_v1 = ({"type": "date", "filler": "tuesday", "origin_sample_id": s101.sample_id},)
    trap_101_v2 = ({"type": "date", "filler": "friday", "origin_sample_id": s900.sample_id},)
    trap_901_v1 = ({"type": "email_folder", "filler": "promotions", "origin_sample_id": s901.sample_id},)
    trap_901_v2 = ({"type": "email_folder", "filler": "spam", "origin_sample_id": s900.sample_id},)

    rows = [
        # 101: V1 captures its own trap ("tuesday"); V2 does not ("friday" absent).
        _ptrap_row(world, s101, V1_ARM, _resp("iot", "hue_lighton", [("time", "six"), ("date", "tuesday")]), trap_101_v1),
        _ptrap_row(world, s101, V2_ARM, _resp("iot", "hue_lighton", [("time", "six")]), trap_101_v2),
        # 900: K=0 on both arms -- EXCLUDED from the common denominator.
        _ptrap_row(world, s900, V1_ARM, _resp("email", "query", []), ()),
        _ptrap_row(world, s900, V2_ARM, _resp("email", "query", []), ()),
        # 901: V1 captures its own trap ("promotions"); V2 does not ("spam" absent).
        _ptrap_row(world, s901, V1_ARM, _resp("email", "query", [("email_folder", "promotions")]), trap_901_v1),
        _ptrap_row(world, s901, V2_ARM, _resp("email", "query", []), trap_901_v2),
    ]
    attempt_dir = _write_ptrap_attempt_dir(tmp_path / "ptrap-attempt", rows)
    manifest_path, roster_table_path = _manifest_and_roster_paths(world, tmp_path)
    report = build_ptrap_report(
        attempt_dir, world.lock, world.data_root,
        sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
    )
    return report, attempt_dir


def test_build_ptrap_report_capture_and_k_zero_exclusion_accounting(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    assert report.flight_status == "COMPLETED"
    assert not report.harness_defect_reasons
    assert report.n_usable == 2  # 101 and 901 -- 900 excluded (K=0 on V1)
    assert report.n_excluded == 1
    assert report.excluded_sample_ids == (read_world.sid[900].sample_id,)
    assert report.v1_capture_count == 2
    assert report.v2_capture_count == 0
    assert report.v1_capture_rate == pytest.approx(1.0)
    assert report.v2_capture_rate == pytest.approx(0.0)
    assert report.ci_verdict.point.raw_diff == 2
    # raw_diff (2) is well under the registered floor (6) -- INCONCLUSIVE-TRAP
    # is the only mechanically-correct outcome for this tiny fixture.
    assert report.ci_verdict.overall == "INCONCLUSIVE-TRAP"
    assert report.ci_verdict.reachability.acoustic_mediated_reachable is False


def test_build_ptrap_report_json_round_trips(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    document = report_to_json(report)
    assert document["schema"] == "saea-ptrap-read-v1"
    assert document["n_usable"] == 2
    assert document["capture"]["v1_capture_count"] == 2
    assert document["verdict"]["overall"] == "INCONCLUSIVE-TRAP"
    assert len(document["per_sample"]) == 3


def test_build_ptrap_report_flags_a_gold_zero_overlap_violation_as_a_harness_defect(read_world, tmp_path):
    """Read-side re-derivation (defense in depth): even though
    rails.probes.ptrap_flight.validate_ptrap_flight_summary refuses this
    shape at WRITE time, the read suite independently re-checks it too."""

    world = read_world
    s101 = world.sid[101]
    leaking_trap = ({"type": "date", "filler": "six", "origin_sample_id": s101.sample_id},)  # "six" is s101's own gold
    rows = [
        _ptrap_row(world, s101, V1_ARM, _resp("iot", "hue_lighton", []), leaking_trap),
        _ptrap_row(world, s101, V2_ARM, _resp("iot", "hue_lighton", []), ()),
        _ptrap_row(world, world.sid[900], V1_ARM, _resp("email", "query", []), ()),
        _ptrap_row(world, world.sid[900], V2_ARM, _resp("email", "query", []), ()),
        _ptrap_row(world, world.sid[901], V1_ARM, _resp("email", "query", []), ()),
        _ptrap_row(world, world.sid[901], V2_ARM, _resp("email", "query", []), ()),
    ]
    attempt_dir = _write_ptrap_attempt_dir(tmp_path / "ptrap-attempt", rows)
    manifest_path, roster_table_path = _manifest_and_roster_paths(world, tmp_path)
    report = build_ptrap_report(
        attempt_dir, world.lock, world.data_root,
        sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
    )
    assert any("zero-overlap" in reason for reason in report.harness_defect_reasons)


def test_build_ptrap_report_refuses_a_missing_attempt_dir(read_world, tmp_path):
    world = read_world
    manifest_path, roster_table_path = _manifest_and_roster_paths(world, tmp_path)
    with pytest.raises(PTrapReadError, match="no outputs.jsonl"):
        build_ptrap_report(
            tmp_path / "does-not-exist", world.lock, world.data_root,
            sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
        )


# ---------------------------------------------------------------------------
# 8. Idempotence guard (the CLI's own one-shot read discipline).
# ---------------------------------------------------------------------------


def _cli_repo_layout(tmp_path: Path, world: SlurpReadWorld) -> Path:
    """Mirrors tests/unit/test_pslu_read.py's own ``_cli_repo_layout``: a
    minimal umbrella/study directory shape so ``main()``'s own
    ``umbrella_lock_path(repo_root)`` resolves to a real (copied) lock
    file, without needing the REAL umbrella checkout."""

    repo_root = tmp_path / "umbrella" / "studies" / "study"
    repo_root.mkdir(parents=True)
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_main_refuses_to_run_twice_against_the_same_output_dir(read_world, tmp_path, monkeypatch, capsys):
    world = read_world
    _, attempt_dir = _build_report(world, tmp_path)
    manifest_path, roster_table_path = _manifest_and_roster_paths(world, tmp_path / "cfg")

    repo_root = _cli_repo_layout(tmp_path, world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(world.data_root))
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    argv = [
        str(attempt_dir),
        "--output-dir", str(output_dir),
        "--repo-root", str(repo_root),
        "--sample-manifest", str(manifest_path),
        "--roster-table", str(roster_table_path),
    ]

    first_exit = ptrap_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    first_bytes = verdict_path.read_bytes()

    second_exit = ptrap_read_main(argv)
    assert second_exit == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    assert "already exists" in captured.err
    assert verdict_path.read_bytes() == first_bytes  # untouched by the refused second run
