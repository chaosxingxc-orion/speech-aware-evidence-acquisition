"""Scoring-side reference reading (never imported by runtime-phase modules)."""

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.references import (
    ReferenceError,
    reference_tokens,
)


def test_reads_tokens_from_nlp_header(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|speaker|tags\nhello|A|\nworld|A|\n", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    tokens = reference_tokens(
        lock, synthetic_world.data_root, "earnings21-original", "4000001"
    )
    assert tokens == ["hello", "world"]


def test_missing_token_column_fails_closed(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("word|speaker\nhello|A\n", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="token"):
        reference_tokens(
            lock, synthetic_world.data_root, "earnings21-original", "4000001"
        )


def test_unknown_carrier_fails_closed(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ReferenceError, match="carrier"):
        reference_tokens(lock, synthetic_world.data_root, "conec", "4000001")
