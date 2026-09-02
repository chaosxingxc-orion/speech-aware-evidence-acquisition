"""Ground-qualification profile for receipt-bound Audio2Tool preprocessing."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_packet_token_gate import (
    summarize_packet_tokens,
)


REPO = Path(__file__).resolve().parents[2]


def test_ground_qualification_identity_mode_is_exactly_receipt_bound() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/a2t_g1_preprocess.py"),
            "--ground-qual",
            "--emit-identity",
        ],
        cwd=REPO,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(REPO / "src"),
        },
        check=False,
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    identity = json.loads(completed.stdout)
    assert identity == {
        **identity,
        "run_id": "SAEA-SN-A2T-GROUND-QUAL-104-PREPROCESS",
        "split_identity_hash": (
            "fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b"
        ),
        "subset_receipt_sha256": (
            "eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16"
        ),
        "count": 104,
        "audio_seconds_total": 543.107,
        "plan_calls": 120,
        "plan_audio_seconds": 650,
        "prompt_fit_speech_token_ceiling": 455,
    }
    assert identity["promotion_receipt"].endswith(
        "A2T-GROUND-QUAL-104-promotion.json"
    )
    assert identity["fragments"] == {
        "baseline": "speech-native-preprocess",
        "dataset": "audio2tool-ground-qual-104",
        "experiment": "a2t-ground-qual-preprocess",
        "model": "q4km-preprocess-featcache-cpu-sidecar-a2t",
    }
    assert identity["config_hash"] == (
        "3845d4a8a601e3279a4656ccd0e1c9c92feed33236801758df528e43a7862ae4"
    )


def test_ground_qualification_preregistration_freezes_no_truncation_gate() -> None:
    preregistration = (
        REPO
        / "docs/readiness"
        / "2026-09-02-a2t-executable-ground-qualification-104-v1-preprocess-preregistration.md"
    ).read_text(encoding="utf-8")
    assert "maximum is at most 455 speech tokens" in preregistration
    assert "No packet is truncated, resampled, split, or selected by token count" in preregistration
    assert "Network jitter" in preregistration
    assert "outside this engineering gate" in preregistration


def test_packet_token_summary_uses_complete_packets_and_nearest_rank_percentiles() -> None:
    summary = summarize_packet_tokens(
        {"tier/003": 456, "tier/001": 10, "tier/002": 20, "tier/004": 40},
        ceiling=455,
    )
    assert summary == {
        "ceiling": 455,
        "within_ceiling": False,
        "distribution": {
            "count": 4,
            "max": 456,
            "mean": 131.5,
            "median": 30.0,
            "min": 10,
            "p90": 456,
            "p95": 456,
            "sum": 526,
        },
        "packets": [
            {"packet_id": "tier/001", "n_tokens": 10},
            {"packet_id": "tier/002", "n_tokens": 20},
            {"packet_id": "tier/003", "n_tokens": 456},
            {"packet_id": "tier/004", "n_tokens": 40},
        ],
    }


@pytest.mark.parametrize(
    "packet_tokens,ceiling",
    [({}, 455), ({"a": 0}, 455), ({"a": True}, 455), ({"a": 1}, 0)],
)
def test_packet_token_summary_refuses_incomplete_or_invalid_counts(
    packet_tokens: dict[str, int], ceiling: int
) -> None:
    with pytest.raises(ValueError):
        summarize_packet_tokens(packet_tokens, ceiling=ceiling)
