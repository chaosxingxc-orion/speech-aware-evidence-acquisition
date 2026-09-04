"""core.scorers registration for the SLURP official-evaluator identity-check
scorer (consolidation slice C3a). Mirrors ``test_scorers.py``'s own
``test_cost_scorer_is_registered`` convention -- a name-presence assertion,
never an exhaustive ``SCORERS.names()`` equality (other scorers register
concurrently in this same module)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.data.slurp import SlurpRecord
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    OfficialSluResult,
    score_slurp_outputs_official,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity


def test_slurp_slu_and_slurp_slu_official_are_both_registered():
    names = SCORERS.names()
    assert "slurp-slu" in names
    assert "slurp-slu-official" in names


def test_slurp_slu_and_slurp_slu_official_resolve_the_same_function():
    resolved_primary = SCORERS.resolve("slurp-slu")
    resolved_explicit = SCORERS.resolve("slurp-slu-official")
    assert resolved_primary is resolved_explicit
    assert resolved_primary is score_slurp_outputs_official


def _gold(sample_id: str, scenario: str, action: str, entities) -> SlurpRecord:
    return SlurpRecord(
        sample_id=sample_id,
        utterance_id=sample_id.split(":")[2],
        split="devel",
        media_relpath=f"slurp_real/{sample_id}.flac",
        audio_seconds=1.5,
        scenario=scenario,
        action=action,
        intent=f"{scenario}_{action}",
        entities=entities,
    )


def _official_result(slu_f1: float, span_f1: float) -> OfficialSluResult:
    raw = {
        key: {
            "official_label": key,
            "precision": 0.0,
            "recall": 0.0,
            "f_measure": 0.0,
            "tp": 0.0,
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
        slu_f1=slu_f1,
        span_f1=span_f1,
        raw=raw,
        stdout="fake",
        command=("python", "evaluate.py"),
    )


def test_scorers_resolve_slurp_slu_runs_through_the_uniform_three_positional_signature(
    tmp_path, monkeypatch
):
    """Proves the registry entry is callable exactly like every other scorer
    -- ``SCORERS.resolve(name)(outputs_path, lock, root)`` -- with no extra
    positional argument, matching ``core.scorers.score_bundle``'s own call
    convention."""

    record = _gold(
        "slurp:devel:000001:rec-a", "alarm", "set", (SlotEntity("time", "seven am"),)
    )
    monkeypatch.setattr(
        soe,
        "load_slurp_split",
        lambda lock, root, split_id, *, allow_heldout=False, allow_synthetic=False: [record],
    )
    monkeypatch.setattr(soe, "official_evaluator_root", lambda root: Path("unused"))
    monkeypatch.setattr(
        soe,
        "run_official_evaluate",
        lambda gold_path, pred_path, *, evaluator_root, python_executable=None, average="micro": (
            _official_result(slu_f1=1.0, span_f1=1.0)
        ),
    )

    outputs = tmp_path / "x.outputs.jsonl"
    row = {
        "sample_id": record.sample_id,
        "text": json.dumps(
            {
                "scenario": record.scenario,
                "action": record.action,
                "entities": [{"type": e.type, "filler": e.filler} for e in record.entities],
            }
        ),
    }
    outputs.write_text(json.dumps(row) + "\n", encoding="utf-8")

    scorer_fn = SCORERS.resolve("slurp-slu")
    result = scorer_fn(outputs, {}, tmp_path)

    assert result["aggregate"]["identity_check"]["passed"] is True
    assert result["aggregate"]["port_micro"]["slu_f1"] == pytest.approx(1.0)
    assert len(result["per_sample"]) == 1
