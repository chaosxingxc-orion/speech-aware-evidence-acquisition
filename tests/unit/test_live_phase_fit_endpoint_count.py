"""Registered roster shape determines the exact tokenizer fit cap offline."""
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_fit import (
    complete_phase_endpoint_count,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("experiment", "rows", "required"),
    [
        ("slurp-native-stage3-verify-1-smoke-4-v1", 4, 13),
        ("slurp-native-stage3-verify-1-v1", 625, 1876),
    ],
)
def test_verify1_registered_roster_and_phase_shape(experiment, rows, required):
    config = json.loads(
        (ROOT / "configs" / "experiment" / f"{experiment}.json").read_text()
    )
    policy = json.loads(
        (ROOT / "configs" / "policy" / "phase-slurp-verify-select-v1.json").read_text()
    )
    assert len(config["populations"]) == 1
    assert len(config["populations"][0]["ids"]) == rows
    assert len(policy["phases"]) == 1
    assert complete_phase_endpoint_count(len(policy["phases"]), rows) == required


@pytest.mark.parametrize("phase_count,row_count", [(0, 4), (1, 0), (True, 4), (1, False)])
def test_endpoint_count_refuses_invalid_shapes(phase_count, row_count):
    with pytest.raises(PreparationError, match="positive phase and row counts"):
        complete_phase_endpoint_count(phase_count, row_count)
