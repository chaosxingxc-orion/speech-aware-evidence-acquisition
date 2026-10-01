"""Protect the one-time control-format correction without relaxing the parser."""
import json
from pathlib import Path

from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    _planner_action, PLANNER_ACTION_ILLEGAL,
)

ROOT = Path(__file__).resolve().parents[2]


def test_successor_changes_only_planner_contract_and_administrative_fit_pin():
    old = json.loads((ROOT / "configs/baseline/slurp-native-stage3-system-text-smoke-4-v1.json").read_text())
    new = json.loads((ROOT / "configs/baseline/slurp-native-stage3-system-text-smoke-4-recovery1-v1.json").read_text())
    for role in ("solver", "reviewer", "planner"):
        before = (ROOT / "configs" / old["phase_material"][role]["instruction_template"]).read_text()
        after = (ROOT / "configs" / new["phase_material"][role]["instruction_template"]).read_text()
        if role == "planner":
            assert after.startswith(before.rstrip())
            assert "exactly one bare token: ACCEPT or REVISE" in after
            assert "After receiving a tool result" in after
        else:
            assert before == after
        new["phase_material"][role]["instruction_template"] = old["phase_material"][role]["instruction_template"]
    for component in new["native_episode"]["consumption_module"]["components"]:
        previous = next(c for c in old["native_episode"]["consumption_module"]["components"]
                        if c["component_id"] == component["component_id"])
        for role in ("solver", "reviewer", "planner"):
            key = role + "_template"
            if key in component.get("params", {}):
                component["params"][key] = previous["params"][key]
    for key in ("prepared_phase_supply", "native_contact_fit", "what_this_is"):
        new.pop(key, None)
        old.pop(key, None)
    assert new == old


def test_exact_text_contract_does_not_accept_json_control():
    for action in ("ACCEPT", "REVISE"):
        assert _planner_action(action, output_format="exact-text", legal={"ACCEPT", "REVISE"}) == (action, None, None)
        assert _planner_action(json.dumps({"action": action}), output_format="exact-text",
                               legal={"ACCEPT", "REVISE"})[0] == PLANNER_ACTION_ILLEGAL
