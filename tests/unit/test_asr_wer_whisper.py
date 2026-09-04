"""asr-wer-whisper scorer: corpus WER arithmetic, divergence from the frozen
asr-wer scorer, registration, and fail-closed behavior -- mirrors
tests/unit/test_scorers.py's synthetic earnings21 root/lock fixture usage.
"""

import json

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.scorers import (
    ScoringPhaseError,
    score_asr_outputs_whisper,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (
    WHISPER_NORMALIZER_NAME,
    WHISPER_WER_SCORER_VERSION,
)


def _write_outputs(tmp_path, rows):
    path = tmp_path / "x.outputs.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return path


def _row(sample_id: str, text: str) -> dict:
    return {
        "sample_id": sample_id,
        "carrier_lock_key": "earnings21-original",
        "arm": "bare-core",
        "request_id": f"req-{sample_id}",
        "text": text,
        "request_sha256": "0" * 64,
        "response_sha256": "0" * 64,
    }


def test_registration_resolves_the_same_function():
    assert SCORERS.resolve("asr-wer-whisper") is score_asr_outputs_whisper


def test_corpus_wer_arithmetic(synthetic_world, tmp_path):
    nlp1 = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp1.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    nlp2 = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000002.nlp"
    nlp2.write_text("token|tags\ngood|\nmorning|\n", encoding="utf-8")
    outputs = _write_outputs(
        tmp_path,
        [
            _row("4000001", "hello there"),  # 1 substitution / 2 ref words
            _row("4000002", "good morning"),  # exact match / 2 ref words
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_asr_outputs_whisper(outputs, lock, synthetic_world.data_root)

    per_sample = {entry["sample_id"]: entry for entry in scores["per_sample"]}
    assert per_sample["4000001"]["substitutions"] == 1
    assert per_sample["4000001"]["deletions"] == 0
    assert per_sample["4000001"]["insertions"] == 0
    assert per_sample["4000001"]["hits"] == 1
    assert per_sample["4000001"]["wer"] == pytest.approx(0.5)
    assert per_sample["4000001"]["normalizer"] == WHISPER_NORMALIZER_NAME
    assert per_sample["4000002"]["wer"] == pytest.approx(0.0)
    assert per_sample["4000002"]["hits"] == 2

    aggregate = scores["aggregate"]
    assert aggregate["substitutions"] == 1
    assert aggregate["deletions"] == 0
    assert aggregate["insertions"] == 0
    assert aggregate["reference_words"] == 4
    assert aggregate["samples"] == 2
    # corpus (micro) WER: sum(errors) / sum(reference words), NOT a mean of
    # per-sample WER values (score_asr_outputs's own "asr-wer" convention).
    assert aggregate["corpus_wer"] == pytest.approx(1 / 4)
    assert aggregate["scorer_version"] == WHISPER_WER_SCORER_VERSION
    assert aggregate["normalizer"] == WHISPER_NORMALIZER_NAME


def test_asr_wer_and_asr_wer_whisper_differ_on_number_form(synthetic_world, tmp_path):
    """"twenty" (reference) vs "20" (hypothesis): the frozen saea-scoring-v1
    normalizer never expands/contracts numbers, so these are a substitution;
    the Whisper normalizer maps both to "20", so they align as a hit."""

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\ntwenty|\n", encoding="utf-8")
    outputs = _write_outputs(tmp_path, [_row("4000001", "20")])
    lock = load_lock(synthetic_world.lock_path)

    frozen = SCORERS.resolve("asr-wer")(outputs, lock, synthetic_world.data_root)
    whisper = SCORERS.resolve("asr-wer-whisper")(outputs, lock, synthetic_world.data_root)

    assert frozen["per_sample"][0]["wer"] == pytest.approx(1.0)
    assert frozen["per_sample"][0]["substitutions"] == 1
    assert frozen["aggregate"]["mean_wer"] == pytest.approx(1.0)

    assert whisper["per_sample"][0]["wer"] == pytest.approx(0.0)
    assert whisper["per_sample"][0]["hits"] == 1
    assert whisper["per_sample"][0]["substitutions"] == 0
    assert whisper["aggregate"]["corpus_wer"] == pytest.approx(0.0)


def test_empty_outputs_fail_closed(tmp_path, synthetic_world):
    path = tmp_path / "empty.outputs.jsonl"
    path.write_text("", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="empty"):
        score_asr_outputs_whisper(path, lock, synthetic_world.data_root)


def test_malformed_line_fails_closed(tmp_path, synthetic_world):
    path = tmp_path / "malformed.outputs.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="malformed"):
        score_asr_outputs_whisper(path, lock, synthetic_world.data_root)


def test_repo_root_keyword_is_accepted_and_does_not_change_the_result(synthetic_world, tmp_path):
    """``repo_root`` is keyword-only with a default -- score_bundle's own
    uniform ``scorer(outputs_path, lock, root)`` call must keep working
    unchanged, and an explicit override must not raise or change anything
    (this scorer's reference resolution only ever reads ``root``)."""

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    outputs = _write_outputs(tmp_path, [_row("4000001", "hello world")])
    lock = load_lock(synthetic_world.lock_path)

    default_call = score_asr_outputs_whisper(outputs, lock, synthetic_world.data_root)
    explicit_call = score_asr_outputs_whisper(
        outputs, lock, synthetic_world.data_root, repo_root=tmp_path
    )
    assert default_call == explicit_call
