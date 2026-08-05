"""Scorer adapters over the frozen stack; transition accounting from hit masks."""

import json

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.bundle import VerifiedBundle
from speech_aware_evidence_acquisition.core.scorers import (
    ScoringPhaseError,
    score_bundle,
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


def test_text_containing_unicode_line_separator_round_trips(tmp_path, synthetic_world):
    """json.dumps(ensure_ascii=False) (the driver's own write style) leaves
    U+2028/U+2029 raw inside string values; the reader must split records on
    "\\n" only, not str.splitlines(), or a hit response text containing one of
    these characters cuts a single valid JSONL row in two."""

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    row = {
        "sample_id": "4000001", "carrier_lock_key": "earnings21-original",
        "arm": "bare-core", "request_id": "req-0001",
        "text": "hello world",
        "request_sha256": "0" * 64, "response_sha256": "0" * 64,
    }
    path = tmp_path / "u2028.outputs.jsonl"
    path.write_text(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = SCORERS.resolve("asr-wer")(path, lock, synthetic_world.data_root)
    assert scores["aggregate"] == {"mean_wer": 0.0, "samples": 1}


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


# ---------------------------------------------------------------------------
# score_bundle: R0 repair T6 (I7) manifest-entry scoring seam. "Refuse to
# score an unverified bundle" is enforced structurally -- only a genuine
# core.bundle.VerifiedBundle is accepted, never a bare path or dict.
# ---------------------------------------------------------------------------


def _outputs_path(tmp_path, synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    return _write_outputs(
        tmp_path,
        [{"sample_id": "4000001", "carrier_lock_key": "earnings21-original",
          "arm": "bare-core", "request_id": "req-0001", "text": "hello world",
          "request_sha256": "0" * 64, "response_sha256": "0" * 64,
          "response_text_sha256": "0" * 64}],
    )


@pytest.mark.parametrize("not_a_bundle", ["some/path.jsonl", {"outputs_path": "x"}, None, 7])
def test_score_bundle_refuses_anything_but_a_verified_bundle(tmp_path, synthetic_world, not_a_bundle):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="VerifiedBundle"):
        score_bundle(not_a_bundle, lock, synthetic_world.data_root)


def test_score_bundle_runs_configured_scorers_over_a_genuine_bundle(tmp_path, synthetic_world):
    outputs = _outputs_path(tmp_path, synthetic_world)
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["asr-wer"]},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )
    results = score_bundle(bundle, lock, synthetic_world.data_root)
    assert results == {"asr-wer": SCORERS.resolve("asr-wer")(outputs, lock, synthetic_world.data_root)}


def test_score_bundle_refuses_when_no_scorers_are_configured(tmp_path, synthetic_world):
    outputs = _outputs_path(tmp_path, synthetic_world)
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": []},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )
    with pytest.raises(ScoringPhaseError, match="no configured scorers"):
        score_bundle(bundle, lock, synthetic_world.data_root)


def test_score_bundle_refuses_when_outputs_path_is_missing(tmp_path, synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["asr-wer"]},
        outputs_path=None,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset(),
        attempt_state="ABORTED",
    )
    with pytest.raises(ScoringPhaseError, match="no outputs artifact"):
        score_bundle(bundle, lock, synthetic_world.data_root)
