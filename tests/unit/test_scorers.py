"""Scorer adapters over the frozen stack; transition accounting from hit masks."""

import json

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.scorers import (
    ScoringPhaseError,
    transition_report,
)
from speech_aware_evidence_acquisition.data.lock import load_lock


def _write_outputs(tmp_path, rows):
    path = tmp_path / "x.outputs.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return path


def test_asr_wer_scores_against_references(synthetic_world, tmp_path):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "4000001", "carrier_lock_key": "earnings21-original",
          "arm": "bare-core", "request_id": "req-0001", "text": "hello world",
          "request_sha256": "0" * 64, "response_sha256": "0" * 64}],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = SCORERS.resolve("asr-wer")(outputs, lock, synthetic_world.data_root)
    assert scores["aggregate"] == {"mean_wer": 0.0, "samples": 1}
    assert scores["per_sample"][0]["ref_hit_mask"] == [True, True]


def test_empty_outputs_fail_closed(tmp_path, synthetic_world):
    path = tmp_path / "empty.outputs.jsonl"
    path.write_text("", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="empty"):
        SCORERS.resolve("asr-wer")(path, lock, synthetic_world.data_root)


def test_transition_report_counts_mask_flips():
    baseline = {"per_sample": [{"sample_id": "a", "ref_hit_mask": [True, False, True]}]}
    treatment = {"per_sample": [{"sample_id": "a", "ref_hit_mask": [True, True, False]}]}
    report = transition_report(baseline, treatment)
    assert report == {
        "correct_to_correct": 1,
        "correct_to_wrong": 1,
        "wrong_to_correct": 1,
        "wrong_to_wrong": 0,
    }


def test_transition_report_fails_closed_on_mismatch():
    with pytest.raises(ScoringPhaseError, match="differ"):
        transition_report(
            {"per_sample": [{"sample_id": "a", "ref_hit_mask": [True]}]},
            {"per_sample": [{"sample_id": "b", "ref_hit_mask": [True]}]},
        )
