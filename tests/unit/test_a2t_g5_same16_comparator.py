"""Tests for the no-contact G5 same-roster comparator."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


REPO = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g5-same16-comparator/compare_g1_m0.py"
)


def _module():
    spec = importlib.util.spec_from_file_location("g5_same16_comparator", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_score_row_reads_standard_text_field_and_retains_micro_counts() -> None:
    module = _module()
    score = module.score_row(
        {"text": '[{"name":"setLevel","arguments":{"level":6}}]'},
        (ToolCall("setLevel", {"level": 6}),),
    )

    assert score == {
        "exact": 1,
        "tool": 1,
        "slot_f1": 1.0,
        "slot_true_positives": 1,
        "slot_expected_total": 1,
        "slot_predicted_total": 1,
        "parsed": 1,
        "predicted_calls": 1,
    }
    assert module.score_row(
        {"final_response_text": '[{"name":"setLevel","arguments":{"level":6}}]'},
        (ToolCall("setLevel", {"level": 6}),),
    ) == score


def test_micro_view_aggregates_slot_counts_not_per_row_f1_means() -> None:
    module = _module()
    rows = [
        {
            "exact": 1,
            "tool": 1,
            "parsed": 1,
            "slot_true_positives": 1,
            "slot_expected_total": 1,
            "slot_predicted_total": 1,
        },
        {
            "exact": 0,
            "tool": 0,
            "parsed": 1,
            "slot_true_positives": 0,
            "slot_expected_total": 1,
            "slot_predicted_total": 3,
        },
    ]

    assert module.aggregate_view(rows) == {
        "samples": 2,
        "exact_count": 1,
        "exact_match": 0.5,
        "tool_count": 1,
        "tool_accuracy": 0.5,
        "parse_count": 2,
        "parse_failures": 0,
        "slot_true_positives": 1,
        "slot_expected_total": 2,
        "slot_predicted_total": 4,
        "slot_precision": 0.25,
        "slot_recall": 0.5,
        "slot_f1": 1 / 3,
    }
