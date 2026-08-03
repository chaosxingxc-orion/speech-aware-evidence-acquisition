"""Contract 5: exposure-claim schema validates; the model entry gate refuses without receipts."""

import json
from pathlib import Path

import pytest

from audio_aware_evidence_acquisition.contracts import (
    ExposureSchemaError,
    FrozenCoreGate,
    GateClosed,
    validate_exposure_claim,
)


REPO_ROOT = Path(__file__).resolve().parents[2]

VALID_CLAIM = {
    "scope": "earnings21-original dev slice, D0 acquisition only",
    "date": "2026-08-03",
    "counts": {"model_calls": 0, "audio_seconds": 0},
    "inherited": "W1 probe campaigns on other carriers; zero model exposure on the three carriers",
}


def test_valid_exposure_claim_passes():
    validate_exposure_claim(VALID_CLAIM)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda claim: claim.pop("scope"),
        lambda claim: claim.pop("inherited"),
        lambda claim: claim.update(date="03/08/2026"),
        lambda claim: claim.update(counts={}),
        lambda claim: claim.update(counts={"model_calls": -1}),
        lambda claim: claim.update(extra_field=1),
    ],
)
def test_malformed_exposure_claims_fail(mutation):
    claim = {key: (dict(value) if isinstance(value, dict) else value) for key, value in VALID_CLAIM.items()}
    mutation(claim)
    with pytest.raises(ExposureSchemaError):
        validate_exposure_claim(claim)


def test_exposure_ledger_file_exists_with_required_columns():
    ledger = (REPO_ROOT / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    for column in ("date", "run/experiment id", "model/tool", "calls", "audio seconds"):
        assert column in ledger


def test_gate_refuses_when_receipts_are_missing(tmp_path):
    gate = FrozenCoreGate(tmp_path / "e0.json", tmp_path / "runtime.json")
    with pytest.raises(GateClosed):
        gate.assert_model_touch_allowed()


def test_gate_refuses_partial_e0_closure(tmp_path):
    e0 = tmp_path / "e0.json"
    runtime = tmp_path / "runtime.json"
    e0.write_text(
        json.dumps(
            {
                "d1_identity": "CLOSED",
                "d2_leakage": "CLOSED",
                "d3_scoring": "OPEN",
                "d4_trace": "CLOSED",
            }
        ),
        encoding="utf-8",
    )
    runtime.write_text("{}", encoding="utf-8")
    with pytest.raises(GateClosed, match="d3_scoring"):
        FrozenCoreGate(e0, runtime).assert_model_touch_allowed()


def test_gate_refuses_invalid_runtime_receipt_then_opens_on_valid_one(tmp_path):
    e0 = tmp_path / "e0.json"
    runtime = tmp_path / "runtime.json"
    e0.write_text(
        json.dumps({key: "CLOSED" for key in FrozenCoreGate.E0_DELIVERABLES}),
        encoding="utf-8",
    )
    runtime.write_text(json.dumps({"llama_cpp_build_commit": "xyz"}), encoding="utf-8")
    with pytest.raises(GateClosed):
        FrozenCoreGate(e0, runtime).assert_model_touch_allowed()

    runtime.write_text(
        json.dumps(
            {
                "llama_cpp_build_commit": "a" * 40,
                "gguf_files": [
                    {"path": "models/q8_0.gguf", "sha256": "b" * 64},
                    {"path": "models/mmproj-bf16.gguf", "sha256": "c" * 64},
                ],
            }
        ),
        encoding="utf-8",
    )
    FrozenCoreGate(e0, runtime).assert_model_touch_allowed()
