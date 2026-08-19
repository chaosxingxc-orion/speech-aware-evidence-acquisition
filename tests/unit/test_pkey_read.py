"""``analysis.pkey_read``: the P-KEY pinned offline read suite.

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory. This module is never pointed at
a real flight attempt directory; that is a separate, one-shot registered
read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.pkey_read import (
    KEY_ONLY_MAX_ABS,
    SPEECH_TERM_PRESENT_MIN,
    TEXT_DOMINANT_MAX,
    PKeyOutputRow,
    PKeyReadError,
    build_pkey_report,
    compute_converted_set,
    compute_t0_wer,
    evaluate_interaction,
    find_gold_leak_violations,
    find_transcript_reuse_mismatches,
    load_attempt_rows,
    load_gold_sentence_by_sample_id,
    load_pphon_classes,
    main as pkey_read_main,
    perception_gap,
)
from speech_aware_evidence_acquisition.analysis.pslu_read import ArmAggregate
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.consumption import ConsumptionTrace
from speech_aware_evidence_acquisition.rails.probes.pkey_flight import (
    AUD_NOSUP_ARM,
    AUD_SUP_ARM,
    T0_ARM,
    TXT_NOSUP_ARM,
    TXT_SUP_ARM,
    assemble_t0_messages,
    assemble_txt_messages,
    build_transcript_record,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters, pslu_supply_packet
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SluScore

SLURP_IDS = (101, 900, 901)


# ---------------------------------------------------------------------------
# evaluate_interaction -- the four verdicts, directly (no world needed).
# ---------------------------------------------------------------------------


def _agg(slu_f1_f1: float, *, arm: str = "AUD-NOSUP") -> ArmAggregate:
    zero_score = SluScore(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    return ArmAggregate(
        arm=arm, n_samples=60, aggregate_score=zero_score,
        slu_f1_precision=slu_f1_f1, slu_f1_recall=slu_f1_f1, slu_f1_f1=slu_f1_f1,
        slot_f1_exact_precision=0.0, slot_f1_exact_recall=0.0, slot_f1_exact_f1=0.0,
        slot_f1_exact_tp_sum=0.0, intent_accuracy=0.0, copy_rate=0.0, copy_records=0,
        copy_records_total=0, induced_substitution_count=0,
    )


def _aggregates(aud_nosup: float, aud_sup: float, txt_nosup: float, txt_sup: float) -> dict[str, ArmAggregate]:
    return {
        AUD_NOSUP_ARM: _agg(aud_nosup, arm=AUD_NOSUP_ARM),
        AUD_SUP_ARM: _agg(aud_sup, arm=AUD_SUP_ARM),
        TXT_NOSUP_ARM: _agg(txt_nosup, arm=TXT_NOSUP_ARM),
        TXT_SUP_ARM: _agg(txt_sup, arm=TXT_SUP_ARM),
    }


def test_interaction_thresholds_match_the_registration():
    assert SPEECH_TERM_PRESENT_MIN == 0.06
    assert KEY_ONLY_MAX_ABS == 0.03
    assert TEXT_DOMINANT_MAX == -0.06


def test_evaluate_interaction_speech_term_present():
    # Delta_AUD=+0.50, Delta_TXT=0.00 -> I=+0.50 >= +0.06.
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.70, txt_nosup=0.50, txt_sup=0.50))
    assert verdict.interaction == pytest.approx(0.50)
    assert verdict.speech_term_present.verdict == "met"
    assert verdict.key_only.verdict == "not_met"
    assert verdict.text_dominant.verdict == "not_met"
    assert verdict.overall == "SPEECH-TERM-PRESENT"


def test_evaluate_interaction_key_only():
    # Delta_AUD=Delta_TXT=+0.30 -> I=0.00, |I|<=0.03.
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.50, txt_nosup=0.10, txt_sup=0.40))
    assert verdict.interaction == pytest.approx(0.0)
    assert verdict.key_only.verdict == "met"
    assert verdict.speech_term_present.verdict == "not_met"
    assert verdict.text_dominant.verdict == "not_met"
    assert verdict.overall == "KEY-ONLY"


def test_evaluate_interaction_key_only_at_the_boundary():
    # I == +0.03 exactly -> still KEY-ONLY (non-strict <=). Values chosen to
    # land on the boundary WITHOUT floating-point subtraction error (e.g.
    # 0.33 - 0.30 computes to 0.030000000000000027, not 0.03).
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.0, aud_sup=0.03, txt_nosup=0.0, txt_sup=0.0))
    assert verdict.interaction == pytest.approx(0.03)
    assert verdict.key_only.verdict == "met"
    assert verdict.overall == "KEY-ONLY"


def test_evaluate_interaction_text_dominant():
    # Delta_AUD=0.00, Delta_TXT=+0.50 -> I=-0.50 <= -0.06.
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.40, aud_sup=0.40, txt_nosup=0.10, txt_sup=0.60))
    assert verdict.interaction == pytest.approx(-0.50)
    assert verdict.text_dominant.verdict == "met"
    assert verdict.speech_term_present.verdict == "not_met"
    assert verdict.key_only.verdict == "not_met"
    assert verdict.overall == "TEXT-DOMINANT"


def test_evaluate_interaction_inconclusive_key():
    # I=+0.045 -- strictly between the KEY-ONLY ceiling (0.03) and the
    # SPEECH-TERM-PRESENT floor (0.06).
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.0, aud_sup=0.045, txt_nosup=0.0, txt_sup=0.0))
    assert verdict.interaction == pytest.approx(0.045)
    assert verdict.speech_term_present.verdict == "not_met"
    assert verdict.key_only.verdict == "not_met"
    assert verdict.text_dominant.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-KEY"


def test_evaluate_interaction_verdicts_are_mutually_exclusive_densely():
    for i in range(-100, 101):
        i_value = i / 100.0
        verdict = evaluate_interaction(_aggregates(aud_nosup=0.0, aud_sup=i_value, txt_nosup=0.0, txt_sup=0.0))
        fired = [
            c.verdict == "met"
            for c in (verdict.speech_term_present, verdict.key_only, verdict.text_dominant)
        ]
        assert sum(fired) <= 1, f"I={i_value} fired more than one clause"


# ---------------------------------------------------------------------------
# perception_gap.
# ---------------------------------------------------------------------------


def test_perception_gap_is_txt_nosup_minus_aud_nosup():
    aggregates = _aggregates(aud_nosup=0.30, aud_sup=0.90, txt_nosup=0.55, txt_sup=0.60)
    assert perception_gap(aggregates) == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# compute_t0_wer -- direct, no world.
# ---------------------------------------------------------------------------


def _t0_row(sample_id: str, response_text: str) -> PKeyOutputRow:
    return PKeyOutputRow(
        arm=T0_ARM, sample_id=sample_id, silence_swapped=False, transcript_sha256_used=None,
        messages=(), response_text=response_text, metrics={}, consumption={},
    )


def test_compute_t0_wer_exact_match_is_zero_and_a_divergent_one_is_positive():
    rows = [_t0_row("s1", "check my email"), _t0_row("s2", "turn on the kitchen light")]
    gold = {"s1": "check my email", "s2": "turn on the kitchen lights"}
    result = compute_t0_wer(rows, gold)
    assert result.per_sample["s1"] == pytest.approx(0.0)
    assert result.per_sample["s2"] > 0.0
    assert result.macro_wer == pytest.approx((result.per_sample["s1"] + result.per_sample["s2"]) / 2.0)


def test_compute_t0_wer_skips_samples_with_no_gold_and_handles_empty_input():
    assert compute_t0_wer([], {}).macro_wer == 0.0
    rows = [_t0_row("no-gold", "x")]
    result = compute_t0_wer(rows, {})
    assert result.per_sample == {}
    assert result.macro_wer == 0.0


# ---------------------------------------------------------------------------
# load_pphon_classes -- soft, read-only, tolerate-absence.
# ---------------------------------------------------------------------------


def test_load_pphon_classes_none_path_is_empty():
    assert load_pphon_classes(None) == {}


def test_load_pphon_classes_missing_file_is_empty(tmp_path):
    assert load_pphon_classes(tmp_path / "does-not-exist.json") == {}


def test_load_pphon_classes_malformed_json_is_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_pphon_classes(path) == {}


def test_load_pphon_classes_samples_shape(tmp_path):
    path = tmp_path / "pphon-verdict.json"
    path.write_text(json.dumps({"samples": {"sid-1": {"class": "NEAR-MISS"}, "sid-2": "FAR-MISS"}}), encoding="utf-8")
    assert load_pphon_classes(path) == {"sid-1": "NEAR-MISS", "sid-2": "FAR-MISS"}


def test_load_pphon_classes_flat_shape(tmp_path):
    path = tmp_path / "pphon-verdict-flat.json"
    path.write_text(json.dumps({"sid-1": "NEAR-MISS"}), encoding="utf-8")
    assert load_pphon_classes(path) == {"sid-1": "NEAR-MISS"}


# ---------------------------------------------------------------------------
# compute_converted_set -- direct, using RowAnalysis-shaped fixtures.
# ---------------------------------------------------------------------------


def _analysis(sample_id: str, *, fully_correct: bool):
    from speech_aware_evidence_acquisition.analysis.pslu_read import RowAnalysis

    row = _t0_row(sample_id, "{}")
    score = (
        SluScore(1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if fully_correct
        else SluScore(0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0)
    )
    return RowAnalysis(
        row=row, predicted_scenario=None, predicted_action=None, predicted_entities=(),
        parsed=True, recomputed_score=score, recheck_mismatches=(), roster_reconciliation=None,
        induced_substitutions=0,
    )


def test_compute_converted_set_aud_only_perception_repair_set():
    result = compute_converted_set(
        aud_nosup_analyses=[_analysis("s1", fully_correct=False)],
        aud_sup_analyses=[_analysis("s1", fully_correct=True)],
        txt_nosup_analyses=[_analysis("s1", fully_correct=False)],
        txt_sup_analyses=[_analysis("s1", fully_correct=False)],
    )
    assert result.aud_converted == ("s1",)
    assert result.txt_converted == ()
    assert result.aud_only == ("s1",)
    assert result.pphon_class_by_sample == {}


def test_compute_converted_set_soft_pphon_cross_reference():
    result = compute_converted_set(
        aud_nosup_analyses=[_analysis("s1", fully_correct=False)],
        aud_sup_analyses=[_analysis("s1", fully_correct=True)],
        txt_nosup_analyses=[_analysis("s1", fully_correct=False)],
        txt_sup_analyses=[_analysis("s1", fully_correct=False)],
        pphon_classes={"s1": "NEAR-MISS", "unrelated": "FAR-MISS"},
    )
    assert result.aud_only == ("s1",)
    assert result.pphon_class_by_sample == {"s1": "NEAR-MISS"}


def test_compute_converted_set_both_converted_is_excluded_from_aud_only():
    result = compute_converted_set(
        aud_nosup_analyses=[_analysis("s1", fully_correct=False)],
        aud_sup_analyses=[_analysis("s1", fully_correct=True)],
        txt_nosup_analyses=[_analysis("s1", fully_correct=False)],
        txt_sup_analyses=[_analysis("s1", fully_correct=True)],
    )
    assert result.aud_converted == ("s1",)
    assert result.txt_converted == ("s1",)
    assert result.aud_only == ()


# ---------------------------------------------------------------------------
# Synthetic SLURP world (mirrors tests/unit/test_pslu_read.py's own
# PsluWorld): 101 (scenario "iot", one gold entity house_place=kitchen)
# plus two neutral no-entity samples (900/901, scenario "email").
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
        "A1_scenario_roster": {"rosters": {"iot": [["house_place", "kitchen"]], "email": [["email_folder", "inbox"]]}},
        "A2_global_type_vocabulary": {"types": ["house_place", "email_folder"]},
        "A3_full_ontology_dose_capped": {"roster": [["house_place", "kitchen"], ["email_folder", "inbox"]]},
        "A4_deranged": {"mapping": {"iot": "email", "email": "iot"}},
    },
}


class PKeyWorld:
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
        self.a3_supply = pslu_supply_packet("A3", scenario=None, rosters=self.rosters)

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
def pkey_world(tmp_path):
    return PKeyWorld(tmp_path)


def _resp(scenario: str, action: str, entities: list[tuple[str, str]]) -> str:
    return json.dumps(
        {"scenario": scenario, "action": action, "entities": [{"type": t, "filler": f} for t, f in entities]}
    )


NEUTRAL = _resp("email", "query", [])
IOT_WRONG = _resp("iot", "hue_lighton", [])
IOT_RIGHT = _resp("iot", "hue_lighton", [("house_place", "kitchen")])

T0_RESPONSES = {101: "turn on the kitchen light", 900: "check my email", 901: "any new email"}


def _row(world: PKeyWorld, sample, arm: str, response_text: str, *, transcript_registry, silence_swapped=False) -> dict:
    if arm == T0_ARM:
        messages = list(assemble_t0_messages(sample))
        metrics: dict = {}
        consumption = world.adapter.extract_consumption(sample, None, response_text).as_json()
        transcript_sha256_used = None
    elif arm in (AUD_NOSUP_ARM, AUD_SUP_ARM):
        supply = None if arm == AUD_NOSUP_ARM else world.a3_supply
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
        transcript_sha256_used = None
    else:  # TXT_NOSUP_ARM / TXT_SUP_ARM
        supply = None if arm == TXT_NOSUP_ARM else world.a3_supply
        messages = list(assemble_txt_messages(sample, supply, transcript_registry))
        metrics = dict(world.adapter.score(sample, response_text))
        consumption = world.adapter.extract_consumption(sample, supply, response_text).as_json()
        transcript_sha256_used = transcript_registry[sample.sample_id].sha256
    return {
        "arm": arm,
        "sample_id": sample.sample_id,
        "silence_swapped": silence_swapped,
        "transcript_sha256_used": transcript_sha256_used,
        "messages": messages,
        "response_text": response_text,
        "metrics": metrics,
        "consumption": consumption,
    }


def _build_rows(
    world: PKeyWorld,
    *,
    aud_nosup: dict[int, str],
    aud_sup: dict[int, str],
    txt_nosup: dict[int, str],
    txt_sup: dict[int, str],
    silence_sample_ids: tuple[int, ...] = SLURP_IDS,
    silence_responses: dict[int, str] | None = None,
) -> list[dict]:
    transcript_registry = {
        world.sid[slurp_id].sample_id: build_transcript_record(world.sid[slurp_id].sample_id, T0_RESPONSES[slurp_id])
        for slurp_id in SLURP_IDS
    }
    rows: list[dict] = []
    for slurp_id in SLURP_IDS:
        sample = world.sid[slurp_id]
        rows.append(_row(world, sample, T0_ARM, T0_RESPONSES[slurp_id], transcript_registry=transcript_registry))
    for slurp_id in SLURP_IDS:
        rows.append(_row(world, world.sid[slurp_id], AUD_NOSUP_ARM, aud_nosup[slurp_id], transcript_registry=transcript_registry))
    for slurp_id in SLURP_IDS:
        rows.append(_row(world, world.sid[slurp_id], AUD_SUP_ARM, aud_sup[slurp_id], transcript_registry=transcript_registry))
    for slurp_id in SLURP_IDS:
        rows.append(_row(world, world.sid[slurp_id], TXT_NOSUP_ARM, txt_nosup[slurp_id], transcript_registry=transcript_registry))
    for slurp_id in SLURP_IDS:
        rows.append(_row(world, world.sid[slurp_id], TXT_SUP_ARM, txt_sup[slurp_id], transcript_registry=transcript_registry))
    silence_responses = silence_responses or {slurp_id: aud_sup[slurp_id] for slurp_id in silence_sample_ids}
    for slurp_id in silence_sample_ids:
        rows.append(
            _row(
                world, world.sid[slurp_id], AUD_SUP_ARM, silence_responses[slurp_id],
                transcript_registry=transcript_registry, silence_swapped=True,
            )
        )
    return rows


def _write_attempt_dir(path: Path, rows: list[dict], *, status="COMPLETED", error=None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (path / "flight-receipt.json").write_text(json.dumps({"status": status, "error": error}), encoding="utf-8")
    return path


def _build_report(world: PKeyWorld, tmp_path: Path, rows: list[dict], **kwargs):
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)
    return build_pkey_report(
        attempt_dir, world.lock, world.data_root,
        sample_manifest_path=world.sample_manifest_path, roster_table_path=world.roster_table_path,
        **kwargs,
    )


def _clean_rows(world: PKeyWorld) -> list[dict]:
    return _build_rows(
        world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
    )


# ---------------------------------------------------------------------------
# load_gold_sentence_by_sample_id.
# ---------------------------------------------------------------------------


def test_load_gold_sentence_by_sample_id(pkey_world):
    sample_ids = [pkey_world.sid[slurp_id].sample_id for slurp_id in SLURP_IDS]
    sentences = load_gold_sentence_by_sample_id(pkey_world.lock, pkey_world.data_root, sample_ids)
    assert sentences[pkey_world.sid[101].sample_id] == "turn on the kitchen lights"
    assert sentences[pkey_world.sid[900].sample_id] == "check my email"


# ---------------------------------------------------------------------------
# build_pkey_report -- happy path.
# ---------------------------------------------------------------------------


def test_happy_path_key_only_and_zero_defects(pkey_world, tmp_path):
    # Deliberately NOT _clean_rows()'s own default silence_responses (which
    # equal the real AUD-SUP responses on every sample -- unanimous
    # unchanged, see test_silence_swap_unanimous_unchanged_voids_the_read):
    # sample 101 flips under silence here, so the silence-swap VOID clause
    # stays not_met and this fixture can assert a clean, non-VOID read.
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        silence_responses={101: NEUTRAL, 900: NEUTRAL, 901: NEUTRAL},
    )
    report = _build_report(pkey_world, tmp_path, rows)

    assert report.recheck_mismatches == ()
    assert report.harness_defect_reasons == ()
    assert report.gold_leak_violations == ()
    assert report.transcript_mismatches == ()
    assert report.void_verdict.voided is False

    assert report.aggregates[AUD_NOSUP_ARM].slu_f1_f1 == pytest.approx(0.0)
    assert report.aggregates[AUD_SUP_ARM].slu_f1_f1 == pytest.approx(1.0)
    assert report.aggregates[TXT_NOSUP_ARM].slu_f1_f1 == pytest.approx(0.0)
    assert report.aggregates[TXT_SUP_ARM].slu_f1_f1 == pytest.approx(1.0)
    assert report.interaction.delta_aud == pytest.approx(1.0)
    assert report.interaction.delta_txt == pytest.approx(1.0)
    assert report.interaction.interaction == pytest.approx(0.0)
    assert report.interaction.overall == "KEY-ONLY"
    assert report.overall == "KEY-ONLY"

    assert report.perception_gap == pytest.approx(0.0)
    assert report.t0_wer.per_sample[pkey_world.sid[900].sample_id] == pytest.approx(0.0)
    assert report.t0_wer.per_sample[pkey_world.sid[101].sample_id] > 0.0

    # Both AUD-SUP and TXT-SUP convert sample 101 -> aud_only is empty.
    assert report.converted_set.aud_only == ()


# ---------------------------------------------------------------------------
# converted-set difference (perception-repair set) over the full report.
# ---------------------------------------------------------------------------


def test_converted_set_difference_via_full_report(pkey_world, tmp_path):
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},  # TXT never converts 101
    )
    pphon_path = tmp_path / "pphon-verdict.json"
    pphon_path.write_text(
        json.dumps({"samples": {pkey_world.sid[101].sample_id: {"class": "NEAR-MISS"}}}), encoding="utf-8"
    )
    report = _build_report(pkey_world, tmp_path, rows, pphon_verdict_path=pphon_path)

    assert report.converted_set.aud_converted == (pkey_world.sid[101].sample_id,)
    assert report.converted_set.txt_converted == ()
    assert report.converted_set.aud_only == (pkey_world.sid[101].sample_id,)
    assert report.converted_set.pphon_class_by_sample == {pkey_world.sid[101].sample_id: "NEAR-MISS"}


def test_converted_set_difference_without_pphon_output_tolerates_absence(pkey_world, tmp_path):
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
    )
    report = _build_report(pkey_world, tmp_path, rows)  # no pphon_verdict_path
    assert report.converted_set.aud_only == (pkey_world.sid[101].sample_id,)
    assert report.converted_set.pphon_class_by_sample == {}


# ---------------------------------------------------------------------------
# Legality: gold text must never appear inside any prompt.
# ---------------------------------------------------------------------------


def test_find_gold_leak_violations_clean_fixture_has_none(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)
    parsed_rows = load_attempt_rows(attempt_dir)
    gold = load_gold_sentence_by_sample_id(
        pkey_world.lock, pkey_world.data_root, [pkey_world.sid[i].sample_id for i in SLURP_IDS]
    )
    assert find_gold_leak_violations(parsed_rows, gold) == ()


def test_gold_leak_fixture_voids_the_read(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)
    leaked_sample_id = pkey_world.sid[101].sample_id
    for row in rows:
        if row["arm"] == AUD_SUP_ARM and row["sample_id"] == leaked_sample_id and not row["silence_swapped"]:
            # Appended AFTER the roster+audio content parts, to isolate the
            # gold-leak clause from the (unrelated) roster-shape harness-
            # defect check -- content_text_parts still finds texts[0] ==
            # the real roster block, so only the leak clause fires here.
            row["messages"][1]["content"].append({"type": "text", "text": "turn on the kitchen lights"})
    report = _build_report(pkey_world, tmp_path, rows)

    assert len(report.gold_leak_violations) >= 1
    assert any(v.sample_id == leaked_sample_id for v in report.gold_leak_violations)
    assert report.void_verdict.voided is True
    assert report.overall == "VOID"
    leak_clause = next(c for c in report.void_verdict.clauses if c.clause_text == "gold sentence text found inside a prompt")
    assert leak_clause.verdict == "met"


# ---------------------------------------------------------------------------
# Transcript-reuse byte-identity fixture.
# ---------------------------------------------------------------------------


def test_transcript_mismatch_fixture_voids_the_read(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)
    corrupted_sample_id = pkey_world.sid[101].sample_id
    for row in rows:
        if row["arm"] == TXT_NOSUP_ARM and row["sample_id"] == corrupted_sample_id:
            row["messages"][1]["content"][-1]["text"] = "The user said: a completely different transcript"
    report = _build_report(pkey_world, tmp_path, rows)

    assert len(report.transcript_mismatches) >= 1
    assert any(m.sample_id == corrupted_sample_id for m in report.transcript_mismatches)
    assert report.void_verdict.voided is True
    assert report.overall == "VOID"
    transcript_clause = next(
        c for c in report.void_verdict.clauses
        if c.clause_text == "a TXT-* row's transcript disagrees with its own T0 output (byte-identity)"
    )
    assert transcript_clause.verdict == "met"


def test_find_transcript_reuse_mismatches_direct():
    t0_rows = [_t0_row("s1", "hello world")]
    good_row = PKeyOutputRow(
        arm=TXT_NOSUP_ARM, sample_id="s1", silence_swapped=False, transcript_sha256_used=None,
        messages=({"role": "system", "content": "x"}, {"role": "user", "content": [{"type": "text", "text": "The user said: hello world"}]}),
        response_text="{}", metrics={}, consumption={},
    )
    bad_row = PKeyOutputRow(
        arm=TXT_SUP_ARM, sample_id="s1", silence_swapped=False, transcript_sha256_used=None,
        messages=({"role": "system", "content": "x"}, {"role": "user", "content": [{"type": "text", "text": "The user said: goodbye world"}]}),
        response_text="{}", metrics={}, consumption={},
    )
    mismatches = find_transcript_reuse_mismatches(t0_rows, [good_row, bad_row])
    assert len(mismatches) == 1
    assert mismatches[0].arm == TXT_SUP_ARM


# ---------------------------------------------------------------------------
# Silence-swap unanimity VOID bar.
# ---------------------------------------------------------------------------


def test_silence_swap_unanimous_unchanged_voids_the_read(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)  # silence_responses defaults to aud_sup (unchanged)
    report = _build_report(pkey_world, tmp_path, rows)
    assert all(c.unchanged for c in report.silence_comparisons)
    assert report.void_verdict.voided is True
    silence_clause = next(c for c in report.void_verdict.clauses if c.clause_text == "silence-swap answers persist unchanged")
    assert silence_clause.verdict == "met"


def test_silence_swap_not_unanimous_does_not_void_via_that_clause(pkey_world, tmp_path):
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        silence_responses={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},  # 101 flips under silence
    )
    report = _build_report(pkey_world, tmp_path, rows)
    assert not all(c.unchanged for c in report.silence_comparisons)
    silence_clause = next(c for c in report.void_verdict.clauses if c.clause_text == "silence-swap answers persist unchanged")
    assert silence_clause.verdict == "not_met"
    assert report.void_verdict.voided is False


# ---------------------------------------------------------------------------
# Loading-layer errors.
# ---------------------------------------------------------------------------


def test_build_pkey_report_raises_on_missing_outputs_jsonl(tmp_path):
    (tmp_path / "attempt").mkdir()
    with pytest.raises(PKeyReadError, match="no outputs.jsonl"):
        load_attempt_rows(tmp_path / "attempt")


# ---------------------------------------------------------------------------
# CLI: idempotence guard (refuses to run twice against the same output dir).
# ---------------------------------------------------------------------------


def _cli_repo_layout(tmp_path: Path, world: PKeyWorld) -> Path:
    repo_root = tmp_path / "umbrella" / "studies" / "study"
    repo_root.mkdir(parents=True)
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_cli_refuses_to_run_twice_against_the_same_output_dir(pkey_world, tmp_path, monkeypatch, capsys):
    rows = _clean_rows(pkey_world)
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)

    repo_root = _cli_repo_layout(tmp_path, pkey_world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(pkey_world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [
        str(attempt_dir),
        "--output-dir", str(output_dir),
        "--repo-root", str(repo_root),
        "--sample-manifest", str(pkey_world.sample_manifest_path),
        "--roster-table", str(pkey_world.roster_table_path),
    ]

    first_exit = pkey_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    first_bytes = verdict_path.read_bytes()

    second_exit = pkey_read_main(argv)
    assert second_exit == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    assert "already exists" in captured.err
    assert verdict_path.read_bytes() == first_bytes  # untouched by the refused second run
