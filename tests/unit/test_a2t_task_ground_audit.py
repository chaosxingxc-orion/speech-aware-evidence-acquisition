"""Qualification rules for the Audio2Tool task-wide knowledge ground."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import a2t_task_ground_audit as audit


def _metrics(
    *,
    exact: int,
    tool: int,
    parse_failures: int,
    slot_f1: float,
    n: int = 104,
) -> audit.GroundMetrics:
    return audit.GroundMetrics(
        n_samples=n,
        exact_count=exact,
        tool_correct_count=tool,
        parse_failures=parse_failures,
        slot_micro_f1=slot_f1,
    )


def test_ground_floor_requires_all_quality_channels() -> None:
    result = audit.qualify_ground(
        _metrics(exact=94, tool=99, parse_failures=1, slot_f1=0.90)
    )

    assert result.gates == {
        "exact_at_least_90_percent": True,
        "tool_at_least_95_percent": True,
        "slot_f1_at_least_90_percent": True,
        "parse_rate_at_least_99_percent": True,
    }
    assert result.minimum_ground_passed is True
    assert result.target_95_exact_passed is False


def test_ground_target_requires_99_exact_rows_at_n104() -> None:
    result = audit.qualify_ground(
        _metrics(exact=99, tool=103, parse_failures=0, slot_f1=0.96)
    )

    assert result.minimum_ground_passed is True
    assert result.target_95_exact_passed is True
    assert result.rates["exact_match"] == pytest.approx(99 / 104)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("exact_count", 105),
        ("tool_correct_count", -1),
        ("parse_failures", 105),
        ("slot_micro_f1", 1.01),
    ),
)
def test_ground_metrics_refuse_invalid_counts_and_rates(field: str, value: object) -> None:
    values: dict[str, object] = {
        "n_samples": 104,
        "exact_count": 94,
        "tool_correct_count": 99,
        "parse_failures": 1,
        "slot_micro_f1": 0.90,
    }
    values[field] = value

    with pytest.raises(ValueError):
        audit.GroundMetrics(**values)


def test_landed_surface_diagnosis_forbids_candidate_optimization() -> None:
    result = audit.diagnose_landed_surface(
        full_registry_tool_accuracy=217 / 400,
        full_registry_exact_match=97 / 400,
        top5_gold_tool_coverage=71 / 104,
        matched_exact_match=40 / 104,
        postcontact_oracle_exact_match=46 / 104,
        highlighted_correct_row_conversion=16 / 120,
        highlighted_correct_row_retention=112 / 120,
        highlighted_default_substitutions=34,
    )

    assert result == {
        "full_registry_is_not_a_qualified_ground": True,
        "top5_surface_cannot_reach_the_ground_floor": True,
        "perfect_m0_matched_arbitration_cannot_reach_the_ground_floor": True,
        "correct_tool_row_does_not_supply_execution_knowledge": True,
        "literal_defaults_are_a_copy_hazard": True,
        "knowledge_expansion_required_before_candidate_optimization": True,
    }


def test_committed_task_ground_audit_preserves_the_sealed_decision() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    result_path = (
        repository_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-02-a2t-task-ground-audit-v1"
        / "task-ground-audit-result.json"
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["execution_profile"] == "model-free-check"
    assert set(result["contacts"].values()) == {0}
    assert result["offline_guard"]["outbound_connection_attempts"] == 0
    assert result["knowledge_inventory"] == {
        "argument_keys": 85,
        "argument_pattern_families": 354,
        "argument_pattern_family_coverage": 1.0,
        "construction_tools": 151,
        "lexical_gold_tool_recall": {
            "at_128": 0.985,
            "at_16": 0.8975,
            "at_32": 0.94,
            "at_5": 0.7925,
        },
        "registry_tools": 152,
        "tool_coverage": 1.0,
    }
    assert all(result["diagnosis"].values())
    assert result["landed_surfaces"]["perfect_m0_matched_arbitration"] == {
        "exact_count": 46,
        "exact_match": pytest.approx(46 / 104),
    }
    assert result["engineering_scope"] == {
        "complete_manifest_outer_parallel_scoring": True,
        "network_jitter_testing": False,
    }
