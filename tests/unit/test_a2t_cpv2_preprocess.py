"""Profile selection for receipt-bound Audio2Tool preprocessing."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]


def test_cpv2_identity_mode_selects_only_the_new_receipt() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/a2t_g1_preprocess.py"),
            "--cpv2",
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
    assert identity["run_id"] == "SAEA-SN-A2T-CPV2-PREPROCESS"
    assert identity["split_identity_hash"] == (
        "401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1"
    )
    assert identity["subset_receipt_sha256"] == (
        "8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783"
    )
    assert identity["audio_seconds_total"] == 536.05
    assert identity["promotion_receipt"].endswith(
        "A2T-CPV2-104-promotion.json"
    )


def test_cpv2_prompt_fit_inherits_text_bytes_and_prices_new_packet_maximum() -> None:
    path = (
        REPO
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-contract-preserving-cascade-104-v2"
        / "prompt-fit-cpv2.json"
    )
    receipt = json.loads(path.read_text(encoding="utf-8"))
    source = REPO / receipt["inherited_text_envelope_receipt"]
    assert receipt["inherited_text_envelope_receipt_sha256"] == hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    assert receipt["speech_feature_tokens_distribution"] == {
        "count": 104,
        "max": 455,
        "median": 65,
        "min": 26,
        "p90": 130,
        "sum": 7735,
    }
    assert receipt["maximum_prompt_tokens_with_measured_speech"] == 19504
    assert receipt["required_context_per_slot"] == 20528
    assert receipt["context_margin_tokens"] == 12240
    assert receipt["maximum_prompt_fits_one_slot"] is True
    assert receipt["model_contact"] is False
    assert receipt["tokenizer_contact"] is False
