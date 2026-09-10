import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = ROOT / "configs" / "experiment"
OWNER_CONTROL = "OWNER-FEATURE-SERVING-007"
ALLOWED_MODES = {
    "raw-audio-precomputed-cache-cpu-projector",
    "formal-window-packets-decoder-only",
}


def _load(name: str) -> dict[str, object]:
    return json.loads((EXPERIMENTS / name).read_text(encoding="utf-8"))


def _assert_held_cells(parent: dict[str, object], successor: dict[str, object]) -> None:
    parent_cells = parent["cells"]
    successor_cells = successor["cells"]
    assert isinstance(parent_cells, list) and isinstance(successor_cells, list)
    assert len(successor_cells) == len(parent_cells)
    for old, new in zip(parent_cells, successor_cells, strict=True):
        assert isinstance(old, dict) and isinstance(new, dict)
        for key, value in old.items():
            if key != "model_fragment":
                assert new[key] == value
        assert new["model_fragment"] is None
        assert new["superseded_model_fragment"] == old["model_fragment"]
        assert new["model_binding"] == {
            "status": "PENDING_ROOT_SELECTION",
            "owner_control": OWNER_CONTROL,
            "replacement_model_fragment": None,
            "fresh_cache_manifest": None,
            "promotion_receipt": None,
            "request_fit_receipt": None,
            "runtime_identity_qualified": False,
            "contact_authorized": False,
            "allowed_modes": [
                "raw-audio-precomputed-cache-cpu-projector",
                "formal-window-packets-decoder-only",
            ],
            "selected_mode": None,
            "gpu_mmproj_allowed": False,
        }


def _assert_gate(successor: dict[str, object]) -> None:
    gate = successor["feature_serving_gate"]
    assert isinstance(gate, dict)
    assert gate["status"] == "BLOCKED"
    assert gate["owner_control"] == OWNER_CONTROL
    assert gate["contact_authorized"] is False
    replacement = gate["replacement_mode"]
    assert isinstance(replacement, dict)
    assert replacement["status"] == "PENDING_ROOT_SELECTION"
    assert replacement["selected_mode"] is None
    modes = replacement["allowed_modes"]
    assert isinstance(modes, list)
    assert {mode["mode"] for mode in modes} == ALLOWED_MODES
    joined = json.dumps(gate)
    assert "historical feature cache is not an input" in joined
    assert "GPU-mmproj model fragment is not an executable fallback" in joined


def test_dr_shared_v2_preserves_accepted_two_generation_scope() -> None:
    parent = _load("e21-dr-shared-two-generation-v1.json")
    successor = _load("e21-dr-shared-two-generation-v2.json")
    for key, value in parent.items():
        if key not in {
            "experiment_id",
            "date",
            "migration_status",
            "shared_protocol",
            "model_geometry",
            "cells",
        }:
            assert successor[key] == value
    for key, value in parent["shared_protocol"].items():
        assert successor["shared_protocol"][key] == value
    assert parent["family_execution_plan"]["generation_groups"] == 2
    assert successor["family_execution_plan"]["generation_groups"] == 2
    assert parent["family_execution_plan"]["planned_model_calls"] == 3500
    assert successor["family_execution_plan"]["planned_model_calls"] == 3500
    assert len(parent["delivery_derivatives"]) == 4
    assert successor["delivery_derivatives"] == parent["delivery_derivatives"]
    assert {
        cell["baseline_fragment"] for cell in successor["cells"]
    } == {
        "e21-dr1c-draft-refresh-constrained-ojw",
        "e21-dr1s-self-draft-twin-ojw",
    }
    assert {cell["policy"] for cell in successor["cells"]} == {
        "obs-repair-loop-ojw"
    }
    _assert_held_cells(parent, successor)
    _assert_gate(successor)


def test_loop_v2_is_held_and_preserves_scientific_plan() -> None:
    parent = _load("e21-loop-shared-two-plan-v1.json")
    successor = _load("e21-loop-shared-two-plan-v2.json")
    for key in (
        "execution_profile",
        "purpose",
        "policy_binding",
        "population",
        "predecessor",
        "comparators",
        "execution_plan",
        "family_execution_plan",
        "fit_execution_plan",
        "gain_definition",
        "decision",
        "preserve_wire_responses",
    ):
        assert successor[key] == parent[key]
    for key, value in parent["shared_protocol"].items():
        assert successor["shared_protocol"][key] == value
    old_pin = parent["source_pins"]["model_fragment"]
    assert successor["source_pins"]["superseded_model_fragment"] == old_pin
    assert successor["source_pins"]["replacement_model_fragment"]["repo_relpath"] is None
    _assert_held_cells(parent, successor)
    _assert_gate(successor)