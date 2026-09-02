"""Model-free paired headroom audit for post-contact arbitration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import a2t_postcontact_headroom as audit


def _row(
    sample_id: str,
    *,
    m0: int,
    matched: int,
    m0_text: str | None = None,
    matched_text: str | None = None,
    m0_parsed: bool = True,
    matched_parsed: bool = True,
) -> audit.PairedExactRecord:
    return audit.PairedExactRecord(
        sample_id=sample_id,
        m0_exact=m0,
        matched_exact=matched,
        m0_text=m0_text if m0_text is not None else f"m0-{sample_id}",
        matched_text=(
            matched_text if matched_text is not None else f"matched-{sample_id}"
        ),
        m0_parsed=m0_parsed,
        matched_parsed=matched_parsed,
    )


def test_headroom_partition_and_oracle_identities() -> None:
    rows = (
        _row("save", m0=0, matched=1, m0_parsed=False, matched_parsed=True),
        _row("harm", m0=1, matched=0, m0_parsed=True, matched_parsed=False),
        _row("both", m0=1, matched=1, m0_text="same", matched_text="same"),
        _row("neither", m0=0, matched=0, m0_parsed=False, matched_parsed=False),
    )

    result = audit.analyse(rows)

    assert result.paired_counts == {
        "save": 1,
        "harm": 1,
        "both_correct": 1,
        "both_wrong": 1,
    }
    assert result.parse_counts == {
        "parse_rescue": 1,
        "parse_loss": 1,
        "both_parse": 1,
        "neither_parse": 1,
    }
    assert result.changed_count == 3
    assert result.unchanged_count == 1
    assert result.m0_exact_count == 2
    assert result.matched_exact_count == 2
    assert result.oracle_exact_count == 3
    assert result.oracle_minus_matched == result.paired_counts["harm"] == 1


def test_headroom_gate_requires_saves_harms_and_static_gain() -> None:
    rows = tuple(
        [_row(f"save-{index}", m0=0, matched=1) for index in range(4)]
        + [_row(f"harm-{index}", m0=1, matched=0) for index in range(2)]
        + [_row("both", m0=1, matched=1)]
    )
    result = audit.analyse(rows)
    assert result.always_matched_net == 2
    assert result.oracle_minus_m0 == 4
    assert result.oracle_minus_matched == 2
    assert result.gates == {
        "minimum_saves": True,
        "minimum_harms": True,
        "always_matched_net": True,
        "oracle_net_over_m0": True,
        "oracle_net_over_matched": True,
    }
    assert result.postcontact_headroom_present is True


def test_headroom_rejects_duplicate_and_nonbinary_records() -> None:
    duplicate = _row("same", m0=0, matched=1)
    with pytest.raises(audit.PostContactHeadroomError, match="duplicate"):
        audit.analyse((duplicate, duplicate))
    with pytest.raises(ValueError, match="binary"):
        audit.PairedExactRecord(
            sample_id="bad",
            m0_exact=2,
            matched_exact=0,
            m0_text="a",
            matched_text="b",
            m0_parsed=True,
            matched_parsed=True,
        )


def test_committed_headroom_result_preserves_the_sealed_decision() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    result_path = (
        repository_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-postcontact-headroom-v1"
        / "headroom-result.json"
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["execution_profile"] == "model-free-check"
    assert result["offline_guard"]["outbound_connection_attempts"] == 0
    assert set(result["contacts"].values()) == {0}
    assert result["audit"] == {
        "always_matched_net": 8,
        "changed_count": 70,
        "gates": {
            "always_matched_net": True,
            "minimum_harms": True,
            "minimum_saves": True,
            "oracle_net_over_m0": True,
            "oracle_net_over_matched": True,
        },
        "m0_exact_count": 32,
        "matched_exact_count": 40,
        "n_samples": 104,
        "oracle_exact_count": 46,
        "oracle_minus_m0": 14,
        "oracle_minus_matched": 6,
        "paired_counts": {
            "both_correct": 26,
            "both_wrong": 58,
            "harm": 6,
            "save": 14,
        },
        "parse_counts": {
            "both_parse": 98,
            "neither_parse": 0,
            "parse_loss": 0,
            "parse_rescue": 6,
        },
        "postcontact_headroom_present": True,
        "unchanged_count": 34,
    }
