from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-03-a2t-construction-task-information-audit"
    / "run_audit.py"
)


def _load_runner():
    spec = importlib.util.spec_from_file_location("a2t_task_information_runner", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dialogue_translation_is_ascii_content_preserving_and_audited() -> None:
    runner = _load_runner()

    translated, counts = runner._translate_dialogue_text(
        "Wait\u2026 set it to 20\u00b0\u2014the low\u2011power mode\u201d"
    )

    assert translated == 'Wait... set it to 20 degrees -- the low-power mode"'
    assert translated.isascii()
    assert counts == {
        "U+00B0": 1,
        "U+2011": 1,
        "U+2014": 1,
        "U+201D": 1,
        "U+2026": 1,
    }


def test_dialogue_translation_refuses_unregistered_non_ascii_content() -> None:
    runner = _load_runner()

    with pytest.raises(RuntimeError, match="unregistered non-ASCII"):
        runner._translate_dialogue_text("unsupported \u03bb")


def test_metric_projection_retains_positive_score_and_fallback_diagnostics() -> None:
    runner = _load_runner()
    metrics = {
        "5": {
            "sample_count": 10,
            "requested_k": 5,
            "effective_k": 5,
            "required_item_recall": 0.8,
            "full_set_coverage": 0.7,
            "precision": 0.2,
            "mean_distractor_burden": 4.0,
            "positive_score_required_item_recall": 0.75,
            "positive_score_full_set_coverage": 0.65,
            "mean_zero_score_fallback_count": 0.3,
            "maximum_decision_space_reduction_bits": 4.9,
        }
    }

    assert runner._project_metrics(metrics) == metrics


def test_public_registry_keys_use_only_public_semantic_metadata() -> None:
    runner = _load_runner()

    keys = runner._public_registry_retrieval_keys(
        (
            {
                "tool_name": "setZoneTemperature",
                "domain": "smart_car",
                "category": "climate_environment",
                "description": "Sets the target temperature for a cabin zone.",
                "signature": "setZoneTemperature(zone: Zone, temperature: Float)",
                "argument_defaults": "zone='Driver', temperature=20.0",
            },
        )
    )

    assert keys == {
        "setZoneTemperature": (
            "Tool set zone temperature. Domain smart car. Category climate "
            "environment. Sets the target temperature for a cabin zone."
        )
    }
    assert "Driver" not in keys["setZoneTemperature"]
    assert keys["setZoneTemperature"].isascii()
