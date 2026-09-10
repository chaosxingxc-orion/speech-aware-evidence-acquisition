"""One-contact aligned SLURP official and normalized scoring views."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.data.slurp import SlurpRecord
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe
from speech_aware_evidence_acquisition.reproduction import slurp_slot_normalizer as ssn
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    OfficialSluResult,
    score_slurp_outputs_official_aligned,
    score_slurp_outputs_slu_normalized,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SLURP_LABEL_PROJECTION_V2_ID,
    SlotEntity,
)
from speech_aware_evidence_acquisition.reproduction.slurp_slot_normalizer import (
    SLURP_SLOT_NORMALIZER_ID,
    SLURP_SLU_NORMALIZED_SCORER_ID,
    build_slot_normalizer_inventory,
)


@dataclass(frozen=True)
class _IntentProfile:
    n: int


@dataclass(frozen=True)
class _Ontology:
    actions_by_scenario: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class _Schema:
    intents: Mapping[str, _IntentProfile]


@dataclass(frozen=True)
class _TrainingRow:
    entities: tuple[SlotEntity, ...]


def _official_result() -> OfficialSluResult:
    raw = {
        key: {
            "official_label": key,
            "precision": 1.0,
            "recall": 1.0,
            "f_measure": 1.0,
            "tp": 1.0,
            "fp": 0.0,
            "fn": 0.0,
        }
        for key in (
            "scenario",
            "action",
            "intent",
            "entities",
            "entities_distance_word",
            "entities_distance_char",
            "slu_f1",
        )
    }
    return OfficialSluResult(
        scenario_accuracy=1.0,
        action_accuracy=1.0,
        intent_accuracy=1.0,
        slu_f1=1.0,
        span_f1=1.0,
        raw=raw,
        stdout="synthetic official output",
        command=("python", "evaluate.py"),
    )


@pytest.fixture()
def aligned_wiring(monkeypatch, tmp_path):
    sample_id = "slurp:devel:000001:rec-a"
    gold = SlurpRecord(
        sample_id=sample_id,
        utterance_id="000001",
        split="devel",
        media_relpath="synthetic.flac",
        audio_seconds=1.0,
        scenario="recommendation",
        action="locations",
        intent="recommendation_locations",
        entities=(SlotEntity("place_name", "berlin"),),
    )
    inventory = build_slot_normalizer_inventory(
        [_TrainingRow((SlotEntity("place_name", "berlin"),))]
    )
    monkeypatch.setattr(
        soe,
        "load_slurp_split",
        lambda lock, root, split_id, *, allow_heldout=False, allow_synthetic=False: [gold],
    )
    monkeypatch.setattr(
        soe,
        "load_slurp_ontology",
        lambda lock, root: _Ontology(
            {"recommendation": ("locations",), "alarm": ("query",)}
        ),
    )
    monkeypatch.setattr(
        soe,
        "load_slurp_intent_slot_schema",
        lambda lock, root: _Schema(
            {
                "recommendation_locations": _IntentProfile(2),
                "alarm_query": _IntentProfile(1),
            }
        ),
    )
    monkeypatch.setattr(ssn, "load_slot_normalizer_inventory", lambda lock, root: inventory)
    monkeypatch.setattr(soe, "official_evaluator_root", lambda root: Path("synthetic"))
    official_calls: list[dict[str, object]] = []

    def fake_official(gold_path, pred_path, *, evaluator_root, python_executable=None, average="micro"):
        predictions = [
            json.loads(line)
            for line in Path(pred_path).read_text(encoding="utf-8").split("\n")
            if line
        ]
        official_calls.append(predictions[0])
        return _official_result()

    monkeypatch.setattr(soe, "run_official_evaluate", fake_official)
    outputs = tmp_path / "synthetic.outputs.jsonl"
    outputs.write_text(
        json.dumps(
            {
                "sample_id": sample_id,
                "text": json.dumps(
                    {
                        "scenario": "locations",
                        "action": "query",
                        "entities": [{"type": "place_name", "filler": "berlin"}],
                    }
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return outputs, official_calls, tmp_path


def test_aligned_scorer_is_registered_and_invokes_official_once(aligned_wiring):
    outputs, official_calls, root = aligned_wiring

    scorer = SCORERS.resolve("slurp-slu-official-aligned-v1")
    result = scorer(outputs, {}, root)

    assert scorer is score_slurp_outputs_official_aligned
    assert len(official_calls) == 1
    assert (official_calls[0]["scenario"], official_calls[0]["action"]) == (
        "recommendation",
        "locations",
    )
    assert result["aggregate"]["aligned_views"]["official_evaluate_invocations"] == 1
    assert result["views"]["normalized"]["provenance"][
        "official_evaluate_invocations"
    ] == 0


def test_primary_projected_labels_and_normalized_raw_labels_stay_distinct(aligned_wiring):
    outputs, _official_calls, root = aligned_wiring

    result = score_slurp_outputs_official_aligned(outputs, {}, root)

    primary = result["per_sample"][0]
    normalized = result["views"]["normalized"]["per_sample"][0]
    assert primary["scenario_action_exact"] == 1.0
    assert primary["projected_to"] == "recommendation_locations"
    assert normalized["scenario_action_exact"] == 0.0
    assert normalized["sample_id"] == primary["sample_id"]
    assert "normalized" not in primary
    aligned = result["aggregate"]["aligned_views"]
    assert aligned["primary"]["projection_id"] == SLURP_LABEL_PROJECTION_V2_ID
    assert aligned["normalized"]["prediction_labels"] == "raw-unprojected"
    assert aligned["normalized"]["normalizer_id"] == SLURP_SLOT_NORMALIZER_ID


def test_normalized_view_matches_legacy_normalized_computation(aligned_wiring):
    outputs, _official_calls, root = aligned_wiring

    aligned = score_slurp_outputs_official_aligned(outputs, {}, root)
    legacy = score_slurp_outputs_slu_normalized(outputs, {}, root)
    view = aligned["views"]["normalized"]

    assert view["aggregate"] == legacy["aggregate"]["normalized"]
    assert view["aggregate_per_rule"] == legacy["aggregate"][
        "normalized_per_rule"
    ]
    assert view["per_sample"] == [
        {"sample_id": row["sample_id"], **row["normalized"]}
        for row in legacy["per_sample"]
    ]


def test_legacy_normalized_output_shape_and_identity_remain_compatible(aligned_wiring):
    outputs, official_calls, root = aligned_wiring

    legacy = score_slurp_outputs_slu_normalized(outputs, {}, root)

    assert len(official_calls) == 1
    assert (official_calls[0]["scenario"], official_calls[0]["action"]) == (
        "locations",
        "query",
    )
    assert "views" not in legacy
    assert legacy["aggregate"]["normalized"]["scorer_id"] == (
        SLURP_SLU_NORMALIZED_SCORER_ID
    )
    assert legacy["aggregate"]["normalized"]["normalizer_id"] == (
        SLURP_SLOT_NORMALIZER_ID
    )
    assert legacy["per_sample"][0]["normalized"]["scenario_action_exact"] == 0.0


def test_legacy_per_rule_opt_out_remains_compatible(aligned_wiring):
    outputs, _official_calls, root = aligned_wiring

    legacy = score_slurp_outputs_slu_normalized(outputs, {}, root, per_rule=False)

    assert "normalized" in legacy["aggregate"]
    assert "normalized_per_rule" not in legacy["aggregate"]
