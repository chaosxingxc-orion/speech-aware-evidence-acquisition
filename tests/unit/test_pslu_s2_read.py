"""``analysis.pslu_s2_read``: the P-SLU Stage-2 follow-up pinned offline read
suite (SAEA-PROBE-pslu-s2-183). Engineering-only, zero live model contact --
every fixture here is a hand-authored synthetic attempt directory. This
module is NEVER pointed at a real flight attempt directory.
"""

from __future__ import annotations

import itertools
import json
import string
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.pslu_s2_read import (
    A0_CITED_SLU_F1,
    A2_CITED_GAIN,
    A3_CITED_SLU_F1,
    A4_CITED_GAIN,
    Q_A_FORMAT_EVERYTHING_GAP_MAX,
    Q_A_FORMAT_FLOOR_GAIN_MIN,
    Q_A_KNOWLEDGE_BEYOND_GAP_MIN,
    Q_B_GAIN_FAILS_MAX,
    Q_B_GAIN_WORKS_MIN,
    Q_B_NON_FALLBACK_FAILS_MAX,
    Q_B_NON_FALLBACK_WORKS_MIN,
    MappingSummary,
    PsluS2ReadError,
    build_pslu_s2_report,
    evaluate_qa,
    evaluate_qb,
)
from speech_aware_evidence_acquisition.analysis.pslu_s2_read import main as pslu_s2_read_main
from speech_aware_evidence_acquisition.analysis.pslu_read import ArmAggregate
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters, pslu_supply_packet
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_filler import (
    f1_filler_supply_packet,
    generate_f1_filler_roster,
    load_filler_lexicon,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import (
    canonical_scenario_labels,
    closed_set_phase1_supply_packet,
    map_predicted_scenario_to_canonical,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SluScore, parse_slu_response

ARMS = ("F1", "A1r-phase1", "A1r")
SLURP_IDS = (101, 900, 901)


def _synthetic_lexicon(n: int) -> list[str]:
    letters = string.ascii_lowercase
    combos = itertools.islice(("".join(p) for p in itertools.product(letters, repeat=3)), n)
    return list(combos)


def _write_flac(path: Path, *, sample_rate_hz: int = 16000, seconds: float = 0.2) -> None:
    import numpy as np
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate_hz * seconds)
    sf.write(str(path), np.zeros(frames, dtype="float32"), sample_rate_hz, format="FLAC")


def _tokens(*surfaces: str) -> list[dict]:
    return [{"surface": s, "id": i, "lemma": s, "pos": "NN"} for i, s in enumerate(surfaces)]


# Same 3-devel-sample synthetic world as tests/unit/test_pslu_read.py's own
# PsluWorld -- 101 has scenario "iot" with one gold entity house_place=kitchen;
# 900/901 are "email"-scenario, no gold entities.
DEVEL_RECORDS = [
    {
        "slurp_id": 101,
        "sentence": "turn on the kitchen lights",
        "sentence_annotation": "turn on the [house_place : kitchen] lights",
        "intent": "iot_hue_lighton",
        "scenario": "iot",
        "action": "hue_lighton",
        "tokens": _tokens("turn", "on", "the", "kitchen", "lights"),
        "entities": [{"span": [3], "type": "house_place"}],
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

ROSTER_DOC = {
    "probe": "P-SLU",
    "legality_tier": "legal",
    "train_synthetic_refused": {"train_jsonl_overlap_with_devel": 0},
    "arms": {
        "A1_scenario_roster": {
            "rosters": {
                "iot": [["house_place", "bedroom"], ["house_place", "office"]],
                "email": [["email_folder", "inbox"]],
            }
        },
        "A2_global_type_vocabulary": {"types": ["house_place", "email_folder"]},
        "A3_full_ontology_dose_capped": {"roster": [["house_place", "bedroom"], ["email_folder", "inbox"]]},
        "A4_deranged": {"mapping": {"iot": "email", "email": "iot"}},
    },
}


class PsluS2World:
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
        self.sid = {slurp_id: self._find(samples, slurp_id) for slurp_id in SLURP_IDS}

        self.roster_table_path = tmp_path / "rosters.json"
        self.roster_table_path.write_text(json.dumps(ROSTER_DOC), encoding="utf-8")
        self.rosters = load_pslu_rosters(self.roster_table_path)
        self.canonical_labels = canonical_scenario_labels(self.rosters)

        self.filler_lexicon_path = tmp_path / "filler-lexicon.json"
        self.filler_lexicon_path.write_text(
            json.dumps(
                {
                    "lexicon_version": "pslu-s2-filler-lexicon-v1",
                    "probe": "P-SLU-S2",
                    "slurp_derived": False,
                    "words": _synthetic_lexicon(200),
                }
            ),
            encoding="utf-8",
        )
        self.f1_entries = generate_f1_filler_roster(load_filler_lexicon(self.filler_lexicon_path))
        self.f1_packet = f1_filler_supply_packet(self.f1_entries)

        self.sample_manifest_path = tmp_path / "manifest.json"
        manifest_doc = {
            "probe": "P-SLU",
            "seed": 20260807,
            "split_identity_hash": "a" * 64,
            "items": [{"sample_id": self.sid[slurp_id].sample_id} for slurp_id in SLURP_IDS],
        }
        self.sample_manifest_path.write_text(json.dumps(manifest_doc), encoding="utf-8")

    @staticmethod
    def _find(samples: dict, slurp_id: int):
        needle = f":{slurp_id:06d}:"
        for sample_id, sample in samples.items():
            if needle in sample_id:
                return sample
        raise KeyError(slurp_id)


@pytest.fixture()
def pslu_s2_world(tmp_path):
    return PsluS2World(tmp_path)


def _resp(scenario: str, action: str, entities: list[tuple[str, str]]) -> str:
    return json.dumps(
        {"scenario": scenario, "action": action, "entities": [{"type": t, "filler": f} for t, f in entities]}
    )


NEUTRAL = _resp("email", "query", [])
NEUTRAL_CHANGED = _resp("alarm", "set", [])


def _row(world: PsluS2World, sample, arm: str, response_text: str, *, canonical_label=None, silence_swapped=False) -> dict:
    if arm == "F1":
        supply = world.f1_packet
    elif arm == "A1r-phase1":
        supply = closed_set_phase1_supply_packet(world.canonical_labels)
    elif arm == "A1r":
        supply = pslu_supply_packet("A1p", scenario=canonical_label, rosters=world.rosters)
    else:
        raise ValueError(arm)

    messages = list(world.adapter.assemble_prompt(sample, supply))
    if silence_swapped:
        relpath = f"derived/silence/{sample.sample_id.replace(':', '_')}.flac"
        user_message = messages[1]
        new_content = []
        for part in user_message["content"]:
            if isinstance(part, dict) and part.get("type") == "input_audio":
                new_content.append({**part, "media_relpath": relpath})
            else:
                new_content.append(dict(part))
        messages[1] = {"role": "user", "content": new_content}

    metrics = dict(world.adapter.score(sample, response_text))
    consumption = world.adapter.extract_consumption(sample, supply, response_text).as_json()

    closed_set_mapping = None
    if arm == "A1r-phase1":
        predicted, _action, _entities, parsed = parse_slu_response(response_text)
        mapping = map_predicted_scenario_to_canonical(predicted if parsed else None, world.canonical_labels)
        closed_set_mapping = mapping.as_json()

    return {
        "arm": arm,
        "sample_id": sample.sample_id,
        "silence_swapped": silence_swapped,
        "messages": messages,
        "response_text": response_text,
        "metrics": metrics,
        "consumption": consumption,
        "closed_set_mapping": closed_set_mapping,
    }


def _build_sample_rows(world, sample, *, f1_response, phase1_response, phase2_response, silence_response=None):
    rows = [_row(world, sample, "F1", f1_response)]
    phase1_row = _row(world, sample, "A1r-phase1", phase1_response)
    rows.append(phase1_row)
    canonical_label = phase1_row["closed_set_mapping"]["canonical_label"]
    rows.append(_row(world, sample, "A1r", phase2_response, canonical_label=canonical_label))
    if silence_response is not None:
        rows.append(
            _row(world, sample, "A1r", silence_response, canonical_label=canonical_label, silence_swapped=True)
        )
    return rows


def _write_attempt_dir(path: Path, rows: list[dict], *, status="COMPLETED", error=None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (path / "flight-receipt.json").write_text(json.dumps({"status": status, "error": error}), encoding="utf-8")
    return path


def _build_report(world: PsluS2World, tmp_path: Path, rows):
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)
    return build_pslu_s2_report(
        attempt_dir,
        world.lock,
        world.data_root,
        sample_manifest_path=world.sample_manifest_path,
        roster_table_path=world.roster_table_path,
        filler_lexicon_path=world.filler_lexicon_path,
    )


def _all_sample_rows(world, *, phase1_response, silence_unchanged=True):
    """Rows for all 3 samples -- F1 misses, A1'r phase 1 answers
    ``phase1_response`` for every sample, phase 2 answers correctly on
    sample 101 (exercises a non-trivial roster) and NEUTRAL elsewhere.
    Silence-swap variants for all 3 samples (satisfies the fixed
    EXPECTED_SILENCE_SWAP_COUNT == 3 harness check on every fixture)."""

    f1_miss = _resp("x", "y", [])
    correct_101 = _resp("iot", "hue_lighton", [("house_place", "kitchen")])
    rows: list[dict] = []
    for slurp_id, phase2_response in ((101, correct_101), (900, NEUTRAL), (901, NEUTRAL)):
        sample = world.sid[slurp_id]
        silence_response = phase2_response if silence_unchanged else NEUTRAL_CHANGED
        rows.extend(
            _build_sample_rows(
                world, sample,
                f1_response=f1_miss, phase1_response=phase1_response, phase2_response=phase2_response,
                silence_response=silence_response,
            )
        )
    return rows


# ---------------------------------------------------------------------------
# VOID fixtures.
# ---------------------------------------------------------------------------


def test_lands_void_by_silence_swap_unanimous_unchanged(pslu_s2_world, tmp_path):
    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("iot", "x", []), silence_unchanged=True)
    report = _build_report(pslu_s2_world, tmp_path, rows)

    assert report.recheck_mismatches == ()
    assert report.harness_defect_reasons == ()
    assert all(c.unchanged for c in report.silence_comparisons)
    assert report.void_verdict.voided is True
    assert report.overall_qa == "VOID"
    assert report.overall_qb == "VOID"
    silence_clause = next(c for c in report.void_verdict.clauses if "silence-swap" in c.clause_text)
    assert silence_clause.verdict == "met"


def test_not_voided_when_silence_swap_flips(pslu_s2_world, tmp_path):
    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("iot", "x", []), silence_unchanged=False)
    report = _build_report(pslu_s2_world, tmp_path, rows)

    assert report.harness_defect_reasons == ()
    assert not any(c.unchanged for c in report.silence_comparisons)
    assert report.void_verdict.voided is False
    assert report.overall_qa == report.qa_verdict.overall
    assert report.overall_qb == report.qb_verdict.overall


def test_lands_void_via_recheck_mismatch(pslu_s2_world, tmp_path):
    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("iot", "x", []), silence_unchanged=False)
    target = next(r for r in rows if r["arm"] == "F1" and not r["silence_swapped"] and r["sample_id"] == pslu_s2_world.sid[101].sample_id)
    target["metrics"] = dict(target["metrics"])
    target["metrics"]["slot_f1_exact_tp"] = 999.0

    report = _build_report(pslu_s2_world, tmp_path, rows)

    assert len(report.recheck_mismatches) == 1
    assert report.recheck_mismatches[0].field == "slot_f1_exact_tp"
    assert report.void_verdict.voided is True
    recheck_clause = next(c for c in report.void_verdict.clauses if "recheck" in c.clause_text)
    assert recheck_clause.verdict == "met"


def test_lands_void_via_harness_defect_missing_arm_row(pslu_s2_world, tmp_path):
    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("iot", "x", []), silence_unchanged=False)
    sample_101_id = pslu_s2_world.sid[101].sample_id
    rows = [r for r in rows if not (r["arm"] == "A1r" and r["sample_id"] == sample_101_id and not r["silence_swapped"])]

    report = _build_report(pslu_s2_world, tmp_path, rows)

    assert report.void_verdict.voided is True
    harness_clause = next(c for c in report.void_verdict.clauses if c.clause_text == "harness defect")
    assert harness_clause.verdict == "met"
    assert any("A1r" in reason and "missing" in reason for reason in report.harness_defect_reasons)


def test_lands_void_via_roster_mismatch(pslu_s2_world, tmp_path):
    """A row whose own written prompt text disagrees with what the frozen
    reconstruction (F1's fixed filler packet / pslu_supply_packet) would
    produce -- module docstring note 6."""

    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("iot", "x", []), silence_unchanged=False)
    target = next(r for r in rows if r["arm"] == "F1" and not r["silence_swapped"] and r["sample_id"] == pslu_s2_world.sid[900].sample_id)
    tampered = [dict(part) for part in target["messages"][1]["content"]]
    tampered[0] = {"type": "text", "text": "TAMPERED ROSTER TEXT"}
    target["messages"] = [target["messages"][0], {"role": "user", "content": tampered}]

    report = _build_report(pslu_s2_world, tmp_path, rows)

    assert report.void_verdict.voided is True
    assert any("does not match the reconstructed" in reason for reason in report.harness_defect_reasons)


# ---------------------------------------------------------------------------
# End-to-end wiring (not voided): report.qa_verdict/qb_verdict/mapping_summary
# reflect the actual rows.
# ---------------------------------------------------------------------------


def test_end_to_end_wiring_matches_direct_evaluator_calls(pslu_s2_world, tmp_path):
    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("iot", "x", []), silence_unchanged=False)
    report = _build_report(pslu_s2_world, tmp_path, rows)

    assert report.void_verdict.voided is False
    assert report.qa_verdict == evaluate_qa(report.aggregates["F1"])
    assert report.qb_verdict == evaluate_qb(report.aggregates["A1r"], report.mapping_summary)
    # F1 missed everything (predicted no entities anywhere) -> SLU-F1 == 0.0
    # -> gap to A3_CITED is huge -> KNOWLEDGE-BEYOND-FORMAT fires.
    assert report.aggregates["F1"].slu_f1_f1 == pytest.approx(0.0)
    assert "KNOWLEDGE-BEYOND-FORMAT" in report.overall_qa
    # non_fallback_count == 3 (every phase-1 call mapped to "iot" exactly) --
    # far below the 50/60 WORKS floor and below the 30/60 FAILS ceiling.
    assert report.mapping_summary.non_fallback_count == 3
    assert report.overall_qb == "SELF-SCOPING-FAILS"


def test_mapping_summary_counts_fallback_when_phase1_is_unmapped(pslu_s2_world, tmp_path):
    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("Completely unrelated nonsense", "x", []), silence_unchanged=False)
    report = _build_report(pslu_s2_world, tmp_path, rows)
    assert report.mapping_summary.non_fallback_count == 0
    assert report.mapping_summary.fallback_count == 3
    assert report.mapping_summary.outcome_counts == {"unmapped": 3}


def test_supplied_item_audit_reports_f1_fixed_dose_and_a1r_variable_dose(pslu_s2_world, tmp_path):
    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("iot", "x", []), silence_unchanged=False)
    report = _build_report(pslu_s2_world, tmp_path, rows)
    f1_stats = report.supplied_item_stats["F1"]
    assert f1_stats.n_calls == 3
    assert f1_stats.minimum == f1_stats.maximum == len(pslu_s2_world.f1_entries)
    a1r_stats = report.supplied_item_stats["A1r"]
    assert a1r_stats.n_calls == 3


# ---------------------------------------------------------------------------
# evaluate_qa -- the four Q-A verdicts, directly (module docstring note 1).
# ---------------------------------------------------------------------------


def _agg(slu_f1_f1: float, *, arm: str = "F1") -> ArmAggregate:
    zero_score = SluScore(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    return ArmAggregate(
        arm=arm, n_samples=60, aggregate_score=zero_score,
        slu_f1_precision=slu_f1_f1, slu_f1_recall=slu_f1_f1, slu_f1_f1=slu_f1_f1,
        slot_f1_exact_precision=0.0, slot_f1_exact_recall=0.0, slot_f1_exact_f1=0.0,
        slot_f1_exact_tp_sum=0.0, intent_accuracy=0.0, copy_rate=0.0, copy_records=0,
        copy_records_total=0, induced_substitution_count=0,
    )


def test_evaluate_qa_cited_constants_match_the_registration():
    assert A0_CITED_SLU_F1 == 0.1741
    assert A3_CITED_SLU_F1 == 0.5961
    assert A4_CITED_GAIN == 0.1346
    assert A2_CITED_GAIN == 0.2946
    assert Q_A_FORMAT_FLOOR_GAIN_MIN == pytest.approx(0.1046)
    assert Q_A_KNOWLEDGE_BEYOND_GAP_MIN == 0.10
    assert Q_A_FORMAT_EVERYTHING_GAP_MAX == 0.03


def test_evaluate_qa_format_floor_confirmed_alone():
    verdict = evaluate_qa(_agg(0.53))
    assert verdict.format_floor_confirmed.verdict == "met"
    assert verdict.knowledge_beyond_format.verdict == "not_met"
    assert verdict.format_is_everything.verdict == "not_met"
    assert verdict.overall == "FORMAT-FLOOR-CONFIRMED"


def test_evaluate_qa_knowledge_beyond_format_alone():
    verdict = evaluate_qa(_agg(0.20))
    assert verdict.format_floor_confirmed.verdict == "not_met"
    assert verdict.knowledge_beyond_format.verdict == "met"
    assert verdict.format_is_everything.verdict == "not_met"
    assert verdict.overall == "KNOWLEDGE-BEYOND-FORMAT"


def test_evaluate_qa_format_is_everything_co_fires_with_format_floor():
    verdict = evaluate_qa(_agg(0.60))
    assert verdict.format_floor_confirmed.verdict == "met"
    assert verdict.knowledge_beyond_format.verdict == "not_met"
    assert verdict.format_is_everything.verdict == "met"
    assert verdict.overall == "FORMAT-FLOOR-CONFIRMED + FORMAT-IS-EVERYTHING"


def test_evaluate_qa_inconclusive_via_override_thresholds():
    """Module docstring note 1: with the LITERAL CITED thresholds,
    INCONCLUSIVE-QA is mathematically unreachable for ANY F1 value --
    verified here via deliberately unreachable OVERRIDE thresholds, exactly
    the override mechanism note 1 documents existing for this purpose."""

    verdict = evaluate_qa(
        _agg(0.45),
        format_floor_gain_min=10.0,
        knowledge_beyond_gap_min=10.0,
        format_everything_gap_max=-10.0,
    )
    assert verdict.format_floor_confirmed.verdict == "not_met"
    assert verdict.knowledge_beyond_format.verdict == "not_met"
    assert verdict.format_is_everything.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-QA"


def test_evaluate_qa_inconclusive_is_unreachable_at_the_default_thresholds():
    """The property note 1 documents, checked densely over F1 in [0, 1]."""

    for i in range(0, 101):
        f1 = i / 100.0
        verdict = evaluate_qa(_agg(f1))
        assert verdict.overall != "INCONCLUSIVE-QA", f"F1={f1} unexpectedly produced INCONCLUSIVE-QA"


# ---------------------------------------------------------------------------
# evaluate_qb -- the three Q-B verdicts, directly.
# ---------------------------------------------------------------------------


def _mapping(non_fallback_count: int, n_calls: int = 60) -> MappingSummary:
    return MappingSummary(
        n_calls=n_calls, non_fallback_count=non_fallback_count, fallback_count=n_calls - non_fallback_count,
        outcome_counts={}, phase1_scenario_accuracy=0.0,
    )


def test_evaluate_qb_cited_constants_match_the_registration():
    assert Q_B_NON_FALLBACK_WORKS_MIN == 50
    assert Q_B_NON_FALLBACK_FAILS_MAX == 30
    assert Q_B_GAIN_WORKS_MIN == pytest.approx(0.2646)
    assert Q_B_GAIN_FAILS_MAX == pytest.approx(0.1946)


def test_evaluate_qb_self_scoping_works():
    verdict = evaluate_qb(_agg(0.45, arm="A1r"), _mapping(55))
    assert verdict.self_scoping_works.verdict == "met"
    assert verdict.self_scoping_fails.verdict == "not_met"
    assert verdict.overall == "SELF-SCOPING-WORKS"


def test_evaluate_qb_self_scoping_fails_via_low_non_fallback():
    verdict = evaluate_qb(_agg(0.50, arm="A1r"), _mapping(20))
    assert verdict.self_scoping_fails.verdict == "met"
    assert verdict.self_scoping_works.verdict == "not_met"
    assert verdict.overall == "SELF-SCOPING-FAILS"


def test_evaluate_qb_self_scoping_fails_via_low_gain():
    verdict = evaluate_qb(_agg(0.30, arm="A1r"), _mapping(40))
    assert verdict.self_scoping_fails.verdict == "met"
    assert verdict.self_scoping_works.verdict == "not_met"
    assert verdict.overall == "SELF-SCOPING-FAILS"


def test_evaluate_qb_inconclusive():
    verdict = evaluate_qb(_agg(0.40, arm="A1r"), _mapping(40))
    assert verdict.self_scoping_works.verdict == "not_met"
    assert verdict.self_scoping_fails.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-QB"


def test_evaluate_qb_works_and_fails_never_co_fire_densely():
    for non_fallback in range(0, 61, 5):
        for i in range(0, 101, 5):
            gain_target_f1 = A0_CITED_SLU_F1 + (i / 100.0)
            verdict = evaluate_qb(_agg(gain_target_f1, arm="A1r"), _mapping(non_fallback))
            assert not (verdict.self_scoping_works.verdict == "met" and verdict.self_scoping_fails.verdict == "met")


# ---------------------------------------------------------------------------
# Loading-layer errors + CLI idempotence guard.
# ---------------------------------------------------------------------------


def test_load_attempt_rows_refuses_missing_outputs_jsonl(pslu_s2_world, tmp_path):
    empty_dir = tmp_path / "attempt-empty"
    empty_dir.mkdir()
    with pytest.raises(PsluS2ReadError, match="no outputs.jsonl"):
        build_pslu_s2_report(
            empty_dir, pslu_s2_world.lock, pslu_s2_world.data_root,
            sample_manifest_path=pslu_s2_world.sample_manifest_path,
            roster_table_path=pslu_s2_world.roster_table_path,
            filler_lexicon_path=pslu_s2_world.filler_lexicon_path,
        )


def _cli_repo_layout(tmp_path: Path, world: PsluS2World) -> Path:
    repo_root = tmp_path / "umbrella" / "studies" / "study"
    repo_root.mkdir(parents=True)
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_cli_refuses_to_run_twice_against_the_same_output_dir(pslu_s2_world, tmp_path, monkeypatch, capsys):
    rows = _all_sample_rows(pslu_s2_world, phase1_response=_resp("iot", "x", []), silence_unchanged=False)
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)

    repo_root = _cli_repo_layout(tmp_path, pslu_s2_world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(pslu_s2_world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [
        str(attempt_dir),
        "--output-dir", str(output_dir),
        "--repo-root", str(repo_root),
        "--sample-manifest", str(pslu_s2_world.sample_manifest_path),
        "--roster-table", str(pslu_s2_world.roster_table_path),
        "--filler-lexicon", str(pslu_s2_world.filler_lexicon_path),
    ]

    first_exit = pslu_s2_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    first_bytes = verdict_path.read_bytes()

    second_exit = pslu_s2_read_main(argv)
    assert second_exit == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    assert "already exists" in captured.err
    assert verdict_path.read_bytes() == first_bytes
