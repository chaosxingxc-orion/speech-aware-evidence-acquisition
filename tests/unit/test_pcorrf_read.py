"""``analysis.pcorrf_read``: the P-CORR-F pinned offline read suite (Q-1/Q-2
bootstrap-evaluated verdicts, the mandatory dual measurement, the
reachability statement, and guardrails).

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory or a synthetic gold/response
fixture. This module is NEVER pointed at the real consumed P-SLU attempt
directory or a real P-CORR-F flight attempt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.pcorrf_read import (
    CITED_A3_SLU_F1,
    CROSS_SESSION_DRIFT_BOUND,
    Q1_INERT_BAND,
    Q1_MIN_DELTA,
    Q2_EFFICIENT_MIN_DELTA,
    Q2_INSUFFICIENT_MAX_DELTA,
    EntryCountDistribution,
    PCorrFOutputRow,
    PCorrFReadError,
    build_pcorrf_report,
    compute_contamination,
    compute_q1_bootstrap,
    compute_q2_bootstrap,
    compute_reachability_statement,
    compute_recovery,
    evaluate_q1,
    evaluate_q2,
    load_attempt_rows,
    report_to_json,
)
from speech_aware_evidence_acquisition.analysis.bootstrap import BootstrapResult
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pcorrf_flight import (
    CONSUMED_PSLU_ATTEMPT_ID,
    CONSUMED_PSLU_RUN_EXPERIMENT_ID,
    W1_ARM,
    W2_ARM,
    W3_ARM,
    W4_ARM,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity, SluScore


# ---------------------------------------------------------------------------
# Synthetic SLURP gold world -- 3 devel samples, mirroring analysis.
# ptrap_read's own fixture (101 iot TWO gold entities, 900/901 email).
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
        "sentence": "show me promotions",
        "sentence_annotation": "show me [email_folder : promotions]",
        "intent": "email_query",
        "scenario": "email",
        "action": "query",
        "tokens": _tokens("show", "me", "promotions"),
        "entities": [{"span": [2], "type": "email_folder"}],
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


def _a0_row(world: SlurpReadWorld, sample, response_text: str) -> dict:
    return {
        "arm": "A0",
        "sample_id": sample.sample_id,
        "silence_swapped": False,
        "phase1_scenario_parsed": None,
        "messages": list(world.adapter.assemble_prompt(sample, None)),
        "response_text": response_text,
        "metrics": dict(world.adapter.score(sample, response_text)),
        "consumption": {"records": []},
    }


def _corrf_row(world: SlurpReadWorld, sample, arm: str, response_text: str, corrective_entries: tuple[dict, ...]) -> dict:
    return {
        "arm": arm,
        "sample_id": sample.sample_id,
        "messages": list(world.adapter.assemble_prompt(sample, None)),
        "response_text": response_text,
        "metrics": dict(world.adapter.score(sample, response_text)),
        "consumption": {"records": []},
        "k": len(corrective_entries),
        "corrective_entries": list(corrective_entries),
    }


def _write_attempt_dir(path: Path, rows: list[dict], *, status: str = "COMPLETED", error=None) -> Path:
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


# ---------------------------------------------------------------------------
# 1. Loading.
# ---------------------------------------------------------------------------


def test_load_attempt_rows_parses_the_flight_write_shape(tmp_path):
    rows = [
        {
            "arm": "W1", "sample_id": "s1", "messages": [], "response_text": "{}",
            "metrics": {}, "consumption": {"records": []}, "k": 1,
            "corrective_entries": [{"type": "date", "filler": "monday", "origin_sample_id": "s1"}],
        }
    ]
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)
    parsed = load_attempt_rows(attempt_dir)
    assert len(parsed) == 1
    assert parsed[0].arm == "W1"
    assert parsed[0].k == 1
    assert parsed[0].corrective_entries[0]["filler"] == "monday"


def test_load_attempt_rows_refuses_missing_attempt_dir(tmp_path):
    with pytest.raises(PCorrFReadError, match="no outputs.jsonl"):
        load_attempt_rows(tmp_path / "does-not-exist")


def test_load_attempt_rows_refuses_zero_rows(tmp_path):
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    (attempt_dir / "outputs.jsonl").write_text("\n", encoding="utf-8")
    with pytest.raises(PCorrFReadError, match="zero rows"):
        load_attempt_rows(attempt_dir)


# ---------------------------------------------------------------------------
# 2. Dual measurement -- compute_recovery / compute_contamination.
# ---------------------------------------------------------------------------


def test_compute_recovery_counts_gold_slots_newly_matched():
    gold = (SlotEntity("time", "six"), SlotEntity("house_place", "kitchen"))
    a0_predicted = (SlotEntity("time", "six"),)  # A0 recovered ONLY "six"
    arm_predicted = (SlotEntity("time", "six"), SlotEntity("house_place", "kitchen"))  # this arm ALSO gets kitchen
    count, newly = compute_recovery(arm_predicted, a0_predicted, gold)
    assert count == 1
    assert newly == (SlotEntity("house_place", "kitchen"),)


def test_compute_recovery_zero_when_arm_matches_no_more_than_a0():
    gold = (SlotEntity("time", "six"),)
    a0_predicted = (SlotEntity("time", "six"),)
    arm_predicted = (SlotEntity("time", "six"),)
    count, newly = compute_recovery(arm_predicted, a0_predicted, gold)
    assert count == 0
    assert newly == ()


def test_compute_recovery_never_double_counts_a_duplicate_gold_type():
    gold = (SlotEntity("person", "bob"), SlotEntity("person", "bob"))
    a0_predicted = ()
    arm_predicted = (SlotEntity("person", "bob"), SlotEntity("person", "bob"))
    count, _newly = compute_recovery(arm_predicted, a0_predicted, gold)
    assert count == 2  # both gold copies matched, exactly the greedy exact-match convention


def test_compute_contamination_counts_captured_non_gold_entries():
    predicted = (SlotEntity("date", "wednesday"), SlotEntity("time", "six"))
    corrective_entries = (
        {"type": "date", "filler": "wednesday", "origin_sample_id": "s1"},
        {"type": "house_place", "filler": "kitchen", "origin_sample_id": "s1"},  # not captured (not predicted)
    )
    gold_values = frozenset({"six"})  # "wednesday" is NOT a gold value of this sample
    count, non_gold = compute_contamination(predicted, corrective_entries, gold_values)
    assert count == 1
    assert non_gold[0]["filler"] == "wednesday"


def test_compute_contamination_excludes_a_captured_entry_that_equals_gold():
    predicted = (SlotEntity("house_place", "kitchen"),)
    corrective_entries = ({"type": "house_place", "filler": "kitchen", "origin_sample_id": "s1"},)
    gold_values = frozenset({"kitchen"})  # this entry equals gold -- never contamination
    count, non_gold = compute_contamination(predicted, corrective_entries, gold_values)
    assert count == 0
    assert non_gold == ()


def test_compute_contamination_zero_when_no_corrective_entries():
    predicted = (SlotEntity("date", "wednesday"),)
    count, non_gold = compute_contamination(predicted, (), frozenset())
    assert count == 0
    assert non_gold == ()


# ---------------------------------------------------------------------------
# 3. Reachability statement.
# ---------------------------------------------------------------------------


def _out_row(arm: str, sample_id: str, k: int, entries: tuple[dict, ...] = ()) -> PCorrFOutputRow:
    return PCorrFOutputRow(
        arm=arm, sample_id=sample_id, messages=(), response_text="{}", metrics={}, consumption={},
        k=k, corrective_entries=entries or tuple({"type": "x", "filler": f"v{i}"} for i in range(k)),
    )


class _FakeGoldRecord:
    def __init__(self, entities):
        self.entities = entities


def test_compute_reachability_statement_counts_max_attainable_recovery():
    rows_by_arm = {
        "W1": (_out_row("W1", "s1", 1, ({"type": "house_place", "filler": "kitchen"},)),),
        "W2": (_out_row("W2", "s1", 0),),
        "W3": (_out_row("W3", "s1", 1, ({"type": "house_place", "filler": "kitchen"},)),),
        "W4": (_out_row("W4", "s1", 2, ({"type": "house_place", "filler": "kitchen"}, {"type": "date", "filler": "monday"})),),
    }
    gold_by_sample_id = {"s1": _FakeGoldRecord((SlotEntity("house_place", "kitchen"), SlotEntity("time", "six")))}
    statement = compute_reachability_statement(rows_by_arm, gold_by_sample_id)
    assert statement.total_gold_slots == 2
    assert statement.max_attainable_recovery_by_arm["W1"] == 1
    assert statement.max_attainable_recovery_by_arm["W2"] == 0
    assert statement.max_attainable_recovery_by_arm["W3"] == 1
    assert statement.max_attainable_recovery_by_arm["W4"] == 1  # "monday" doesn't reach the OTHER gold slot


def test_compute_reachability_statement_l1_k_zero_from_w1_distribution():
    rows_by_arm = {"W1": (_out_row("W1", "s1", 0), _out_row("W1", "s2", 2))}
    statement = compute_reachability_statement(rows_by_arm, {})
    assert statement.l1_k_zero_samples == 1


# ---------------------------------------------------------------------------
# 4. Q-1 / Q-2 bootstrap-based verdicts.
# ---------------------------------------------------------------------------


def _score(tp: float, fp: float, fn: float) -> SluScore:
    return SluScore(
        scenario_action_exact=0.0, scenario_exact=0.0, action_exact=0.0,
        slot_f1_exact_tp=tp, slot_f1_exact_fp=fp, slot_f1_exact_fn=fn,
        slu_f1_word_tp=tp, slu_f1_word_fp=fp, slu_f1_word_fn=fn,
        slu_f1_char_tp=tp, slu_f1_char_fp=fp, slu_f1_char_fn=fn,
    )


def test_compute_q1_bootstrap_point_estimate_is_the_f1_difference():
    w1 = {"s1": _score(2, 0, 0), "s2": _score(2, 0, 0)}  # perfect F1 = 1.0
    w2 = {"s1": _score(0, 0, 2), "s2": _score(0, 0, 2)}  # zero recall -> F1 = 0.0
    result = compute_q1_bootstrap(w1_scores_by_sample=w1, w2_scores_by_sample=w2, common_denominator=["s1", "s2"], n_replicates=200)
    assert result.point_estimate == pytest.approx(1.0)


def test_evaluate_q1_corrective_percept_when_delta_and_ci_clear_the_floor():
    bootstrap = BootstrapResult(point_estimate=0.10, replicates=(0.10,) * 100, sigma_hat=0.001, ci_low=0.05, ci_high=0.15, ci_level=0.90, n_replicates=100, seed=1)
    verdict = evaluate_q1(0.10, bootstrap)
    assert verdict.overall == "CORRECTIVE-PERCEPT"


def test_evaluate_q1_corrective_inert_when_the_entire_ci_is_within_the_band():
    bootstrap = BootstrapResult(point_estimate=0.01, replicates=(0.01,) * 100, sigma_hat=0.005, ci_low=-0.02, ci_high=0.02, ci_level=0.90, n_replicates=100, seed=1)
    verdict = evaluate_q1(0.01, bootstrap)
    assert verdict.overall == "CORRECTIVE-INERT"


def test_evaluate_q1_inconclusive_when_neither_clause_fires():
    bootstrap = BootstrapResult(point_estimate=0.10, replicates=(0.10,) * 100, sigma_hat=0.20, ci_low=-0.05, ci_high=0.25, ci_level=0.90, n_replicates=100, seed=1)
    verdict = evaluate_q1(0.10, bootstrap)
    assert verdict.overall == "INCONCLUSIVE-CORR"  # point clears the floor but CI crosses 0


def test_q1_constants_match_the_registration():
    assert Q1_MIN_DELTA == 0.03
    assert Q1_INERT_BAND == 0.03


def test_compute_q2_bootstrap_point_estimate_is_delta_vs_cited_a3():
    w3 = {"s1": _score(2, 0, 0), "s2": _score(2, 0, 0)}  # F1 = 1.0
    result = compute_q2_bootstrap(w3_scores_by_sample=w3, common_denominator=["s1", "s2"], n_replicates=200)
    assert result.point_estimate == pytest.approx(1.0 - CITED_A3_SLU_F1)


def test_evaluate_q2_dose_efficient_point_only_never_ci_gated():
    """module docstring: Q-2's own verdict is gated on the POINT value
    ONLY -- an ENTIRE-CI-crossing-zero shape still fires DOSE-EFFICIENT as
    long as the point clears the floor."""

    bootstrap = BootstrapResult(point_estimate=-0.01, replicates=(-0.01,) * 100, sigma_hat=0.20, ci_low=-0.40, ci_high=0.30, ci_level=0.90, n_replicates=100, seed=1)
    dist = EntryCountDistribution(n_samples=60, mean=1.02, max=4, min=0, k_zero_count=20)
    verdict = evaluate_q2(-0.01, bootstrap, dist)
    assert verdict.overall == "DOSE-EFFICIENT"


def test_evaluate_q2_dose_insufficient():
    bootstrap = BootstrapResult(point_estimate=-0.20, replicates=(-0.20,) * 100, sigma_hat=0.01, ci_low=-0.22, ci_high=-0.18, ci_level=0.90, n_replicates=100, seed=1)
    dist = EntryCountDistribution(n_samples=60, mean=1.02, max=4, min=0, k_zero_count=20)
    verdict = evaluate_q2(-0.20, bootstrap, dist)
    assert verdict.overall == "DOSE-INSUFFICIENT"


def test_evaluate_q2_inconclusive_between_the_bounds():
    bootstrap = BootstrapResult(point_estimate=-0.06, replicates=(-0.06,) * 100, sigma_hat=0.01, ci_low=-0.08, ci_high=-0.04, ci_level=0.90, n_replicates=100, seed=1)
    dist = EntryCountDistribution(n_samples=60, mean=1.02, max=4, min=0, k_zero_count=20)
    verdict = evaluate_q2(-0.06, bootstrap, dist)
    assert verdict.overall == "INCONCLUSIVE-DOSE"


def test_q2_constants_and_cited_a3_match_the_registration():
    assert Q2_EFFICIENT_MIN_DELTA == -0.03
    assert Q2_INSUFFICIENT_MAX_DELTA == -0.10
    assert CITED_A3_SLU_F1 == pytest.approx(0.5961280580450439)
    assert CROSS_SESSION_DRIFT_BOUND == pytest.approx(0.013)


# ---------------------------------------------------------------------------
# 5. Full read-suite integration (build_pcorrf_report / report_to_json).
# ---------------------------------------------------------------------------


def _build_report(world: SlurpReadWorld, tmp_path: Path):
    s101, s900, s901 = world.sid[101], world.sid[900], world.sid[901]

    # Consumed P-SLU A0 baseline: recovers "six" for 101, nothing else.
    a0_rows = [
        _a0_row(world, s101, _resp("iot", "hue_lighton", [("time", "six")])),
        _a0_row(world, s900, _resp("email", "query", [])),
        _a0_row(world, s901, _resp("email", "query", [])),
    ]
    pslu_attempt_dir = tmp_path / "pslu-attempt"
    _write_attempt_dir(pslu_attempt_dir, a0_rows)

    kitchen_entry = {"type": "house_place", "filler": "kitchen", "origin_sample_id": s101.sample_id}
    promotions_entry = {"type": "email_folder", "filler": "promotions", "origin_sample_id": s901.sample_id}
    wednesday_entry = {"type": "date", "filler": "wednesday", "origin_sample_id": s900.sample_id}

    corrf_rows = [
        # W1: recovers kitchen (101) and promotions (901); contaminates on 900.
        _corrf_row(world, s101, W1_ARM, _resp("iot", "hue_lighton", [("time", "six"), ("house_place", "kitchen")]), (kitchen_entry,)),
        _corrf_row(world, s900, W1_ARM, _resp("email", "query", [("date", "wednesday")]), (wednesday_entry,)),
        _corrf_row(world, s901, W1_ARM, _resp("email", "query", [("email_folder", "promotions")]), (promotions_entry,)),
        # W2: cross-sample control -- never recovers, never captures (irrelevant entries supplied).
        _corrf_row(world, s101, W2_ARM, _resp("iot", "hue_lighton", [("time", "six")]), (wednesday_entry,)),
        _corrf_row(world, s900, W2_ARM, _resp("email", "query", []), (kitchen_entry,)),
        _corrf_row(world, s901, W2_ARM, _resp("email", "query", []), (kitchen_entry,)),
        # W3: dose-only (L1 alone) -- recovers the same slots as W1 for 101/901, K=0 for 900.
        _corrf_row(world, s101, W3_ARM, _resp("iot", "hue_lighton", [("house_place", "kitchen")]), (kitchen_entry,)),
        _corrf_row(world, s900, W3_ARM, _resp("email", "query", []), ()),
        _corrf_row(world, s901, W3_ARM, _resp("email", "query", [("email_folder", "promotions")]), (promotions_entry,)),
        # W4: descriptive widened -- same as W1 for this fixture.
        _corrf_row(world, s101, W4_ARM, _resp("iot", "hue_lighton", [("time", "six"), ("house_place", "kitchen")]), (kitchen_entry,)),
        _corrf_row(world, s900, W4_ARM, _resp("email", "query", [("date", "wednesday")]), (wednesday_entry,)),
        _corrf_row(world, s901, W4_ARM, _resp("email", "query", [("email_folder", "promotions")]), (promotions_entry,)),
    ]
    attempt_dir = _write_attempt_dir(tmp_path / "corrf-attempt", corrf_rows)
    manifest_path, roster_table_path = _manifest_and_roster_paths(world, tmp_path)
    report = build_pcorrf_report(
        attempt_dir, world.lock, world.data_root,
        sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
        pslu_attempt_dir=pslu_attempt_dir,
    )
    return report, attempt_dir


def test_build_pcorrf_report_dual_measurement(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    assert report.flight_status == "COMPLETED"
    assert not report.harness_defect_reasons
    assert report.dual_measurement["W1"].recovery_total == 2  # kitchen + promotions, both newly recovered
    assert report.dual_measurement["W1"].contamination_total == 1  # "wednesday" on the no-gold sample
    assert report.dual_measurement["W2"].recovery_total == 0
    assert report.dual_measurement["W2"].contamination_total == 0


def test_build_pcorrf_report_q1_verdict_is_computed(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    # W1 strictly dominates W2 in this fixture -- delta1 must be positive.
    assert report.q1.delta1 > 0
    assert report.q1.overall in ("CORRECTIVE-PERCEPT", "INCONCLUSIVE-CORR")  # never INERT given the positive gap


def test_build_pcorrf_report_q2_verdict_is_computed(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    assert report.q2.overall in ("DOSE-EFFICIENT", "DOSE-INSUFFICIENT", "INCONCLUSIVE-DOSE")
    assert report.q2.w3_entries_distribution.k_zero_count == 1  # sample 900 supplied K=0 on W3


def test_build_pcorrf_report_w4_is_descriptive_only(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    assert report.w4_slu_f1 >= 0.0
    assert report.w4_entries_distribution.n_samples == 3


def test_build_pcorrf_report_reachability_statement(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    assert report.reachability.total_gold_slots == 3  # 101 has 2, 901 has 1, 900 has 0
    assert report.reachability.max_attainable_recovery_by_arm["W1"] == 2


def test_build_pcorrf_report_guardrails_present_for_every_arm(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    for arm in ("W1", "W2", "W3", "W4"):
        assert report.guardrails[arm].n_samples == 3
        assert 0.0 <= report.guardrails[arm].slu_f1 <= 1.0
        assert report.guardrails[arm].scenario_breakdown  # iot + email at least


def test_build_pcorrf_report_json_round_trips(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    document = report_to_json(report)
    assert document["schema"] == "saea-pcorrf-read-v1"
    assert document["runtime_prohibited"] is True
    assert document["q1"]["overall"] == report.q1.overall
    assert document["q2"]["overall"] == report.q2.overall
    assert document["dual_measurement"]["W1"]["recovery_total"] == 2
    assert "reachability" in document
    assert "guardrails" in document


def test_build_pcorrf_report_refuses_a_missing_attempt_dir(read_world, tmp_path):
    world = read_world
    manifest_path, roster_table_path = _manifest_and_roster_paths(world, tmp_path)
    pslu_attempt_dir = tmp_path / "pslu-attempt"
    _write_attempt_dir(pslu_attempt_dir, [_a0_row(world, world.sid[900], _resp("email", "query", []))])
    with pytest.raises(PCorrFReadError, match="no outputs.jsonl"):
        build_pcorrf_report(
            tmp_path / "does-not-exist", world.lock, world.data_root,
            sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
            pslu_attempt_dir=pslu_attempt_dir,
        )


def test_consumed_pslu_source_constants():
    assert CONSUMED_PSLU_RUN_EXPERIMENT_ID == "SAEA-PROBE-pslu-n60"
    assert CONSUMED_PSLU_ATTEMPT_ID == "attempt-20260818T010218Z-4c97cb"
