"""Owner decision 171: the RANKVIS, CATCHALL and EMPTYENT registrations are well formed.

Model-free and data-free: every declaration is parsed by the effect-floor gate's own parser and floor
arithmetic, every Stage-3 label by the registry's own validator, and the two offline rules' pure
functions are exercised on synthetic values. No sealed byte, gold label or model output is read.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label

REPO = Path(__file__).resolve().parents[2]
READINESS = REPO / "docs/readiness"


def _load(relpath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


GATE = _load("scripts/checks/stage3_effect_floor_check.py", "_consume_gate")
CATCHALL = _load("scripts/analysis/catchall_offline_read.py", "_consume_catchall")
EMPTYENT = _load("scripts/analysis/empty_entity_offline_read.py", "_consume_emptyent")

PACKAGES = {
    "SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1": "2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1",
    "SAEA-SLURP-STAGE3-CATCHALL-OFFLINE-V1": "2026-09-27-slurp-stage3-catchall-offline-v1",
    "SAEA-SLURP-STAGE3-EMPTY-ENTITY-OFFLINE-V1": "2026-09-27-slurp-stage3-empty-entity-offline-v1",
}


def _facts(package: str) -> dict:
    return json.loads((READINESS / package / "registered-facts-v1.json").read_text(encoding="utf-8"))


def _fence(package: str) -> dict:
    text = (READINESS / f"{package}-preregistration.md").read_text(encoding="utf-8")
    block = re.search(r"```json\n(.*?)\n```", text, re.S).group(1)
    return json.loads(block)["stage3_measurement"]


@pytest.mark.parametrize("run_id, package", sorted(PACKAGES.items()))
def test_declaration_parses_and_clears_its_own_floor(run_id, package):
    block = _facts(package)["stage3_measurement"][run_id]
    parsed = GATE._parse_declaration(block, "registered-facts", None)
    assert parsed.problems == []
    floor, _lines = GATE.floor_for(block["measurement_design"], block["rows"])
    if floor is None:
        assert block["claims_benefit"] is False
    else:
        assert block["expected_effect_pp"] >= round(floor, 2) - 1e-9
    if block["rows"] < GATE.MIN_BENEFIT_ROWS:
        assert block["claims_benefit"] is False
    fence = _fence(package)[run_id]
    for key in ("measurement_design", "expected_effect_pp", "rows", "claims_benefit"):
        assert fence[key] == block[key]


@pytest.mark.parametrize("package", sorted(PACKAGES.values()))
def test_label_resolves_in_the_registry(package):
    record, operators = validate_stage3_algorithm_label(_facts(package)["stage3_algorithm"], cell=package)
    assert record.id == "none" and operators == ()


@pytest.mark.parametrize("rows", [1000, 1080])
def test_offline_floor_is_the_gate_arithmetic(rows):
    gate_floor, _ = GATE.floor_for("offline-sealed-pool", rows)
    assert math.isclose(CATCHALL.offline_floor_pp(rows), gate_floor, rel_tol=1e-12)


def test_catch_all_mark_is_strict_and_the_edit_keeps_entities():
    key = CATCHALL.CATCH_ALL_KEY
    assert CATCHALL.marks_catch_all({key: 0.4, "intent-boundary:news_query": 0.3})
    assert not CATCHALL.marks_catch_all({key: 0.3, "intent-boundary:news_query": 0.3})
    assert not CATCHALL.marks_catch_all({"intent-boundary:news_query": 0.3})
    text = json.dumps({"scenario": "news", "action": "query", "entities": [{"type": "t", "filler": "f"}]}, sort_keys=True)
    edited, status = CATCHALL.edit(text)
    assert status == "edited"
    payload = json.loads(edited)
    assert (payload["scenario"], payload["action"]) == ("general", "quirky")
    assert payload["entities"] == [{"type": "t", "filler": "f"}]
    empty = json.dumps({"scenario": "", "action": "", "entities": []}, sort_keys=True)
    assert CATCHALL.edit(empty) == (empty, "malformed")


def test_emptiness_states():
    assert EMPTYENT.sample_state(json.dumps({"scenario": "", "action": "", "entities": []})) == "malformed"
    assert EMPTYENT.sample_state(json.dumps({"scenario": "a", "action": "b", "entities": []})) == "empty"
    assert EMPTYENT.sample_state(json.dumps({"scenario": "a", "action": "b", "entities": [{"type": "x", "filler": "y"}]})) == "entities"
    assert EMPTYENT.half_width({"lo": -0.5, "hi": 0.7}) == pytest.approx(0.6)
