"""The ``key-source:k6p`` consumption-module component (2026-09-30): ``column`` only, compiling
to a Perception B branch's ``key_source`` axis. Model-free."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "scripts" / "analysis") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts" / "analysis"))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.supply_variants import parse_perception_branches  # noqa: E402

PSV1 = "configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1.json"
KEY_SOURCE = {
    "store_id": "intent-boundaries",
    "facet_source": {
        "kind": "sealed-vectors", "relpath": "prepared/SAEA-SLURP-CENTRED-CENTROID-KEY-V1/key-v1.jsonl",
        "sha256": "a" * 64, "tool_contact_ledger_row": "SAEA-SLURP-CENTRED-CENTROID-KEY-BUILD-V1",
        "embedded_signal": "text: centred centroid key",
    },
    "query_source": None,
    "agreement_source": None,
}


def _key_source_block(state: str = "column") -> dict:
    block = proof.psv_column_block(PSV1)
    for entry in block["components"]:
        if entry["component_id"] == cm.TOP2_CONTRAST:
            entry.clear()
            entry.update({"component_id": cm.TOP2_CONTRAST, "state": "off"})
        if entry["component_id"] == cm.KEY_SOURCE_K6P:
            entry.update({"state": state, "admitted_by": "registry row (test)", "record": PSV1,
                          "params": {"key_source": copy.deepcopy(KEY_SOURCE), "max_supplied_items": 10}})
    block["columns"] = [{"column_id": "b-k6p", "toggle": cm.KEY_SOURCE_K6P, "to": "on", "level": 2}]
    return block


def test_the_component_is_in_the_closed_inventory_as_a_column_only():
    spec = {s.component_id: s for s in cm.COMPONENT_CATALOGUE}[cm.KEY_SOURCE_K6P]
    assert cm.KEY_SOURCE_K6P == "key-source:k6p"
    assert spec.states == frozenset({cm.STATE_COLUMN})
    assert spec.params == frozenset({"key_source", "max_supplied_items"})
    assert cm.PERCEPTION_AXIS_COMPONENTS[cm.KEY_SOURCE_K6P] == ("key_source",)


def test_a_key_source_column_compiles_to_a_b_branch_carrying_exactly_the_pins():
    composed = cm.compile_module(_key_source_block(), carrier_module_hooks())
    block = composed.values()["native_episode"]["roles"]["perception"]["branches"]
    assert [row["branch_id"] for row in block["branches"]] == ["b-k6p", "t-twin", "a-agree"]
    b = block["branches"][0]
    assert b == {"branch_id": "b-k6p", "max_supplied_items": 10, "key_source": KEY_SOURCE}
    group = parse_perception_branches(block, first_phase_id="perception",
                                      declared_stores=("intent-boundaries",))
    assert group.branch("b-k6p").key_source.facet_source["sha256"] == "a" * 64
    assert group.delivering_branch.key_source is None and group.twin_branch.key_source is None


def test_on_is_refused_for_the_key_source_component():
    with pytest.raises(cm.ConsumptionModuleConfigError, match="cannot be 'on'"):
        cm.parse_consumption_module_block(_key_source_block(state="on"))
