"""Item E35 (owner decision 89, 2026-09-21): a carrier-neutral twin of
``phase-native-candidates-review-revise-acquire-v1`` (item E32) -- the SAME
five phases (perception, reviewer, planner, solver, acquisition), the SAME
contact ceiling (11) and the SAME stop rule (``native-role-episode``), but
with the Perception phase's ``response_format_id`` null instead of SLURP's
``slurp-intent-hypotheses-v1``. This is what lets the Earnings21+ConEC
carrier fly the same six-node native episode SLURP flies, through the same
shared harness (``rails.controllers.EvidenceAgentController``,
``core.flight.FlightRuntime``) -- one program id per perception-format
binding, never a carrier flag on one program object (the same "the phase's
declared shape rides the config hash" discipline every other program-id
pair in this module already follows).

Model-free: loads committed JSON through ``rails.controllers.
default_phase_program``. No model, tokenizer, encoder, scorer, server or
network contact.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.controllers import (
    default_phase_program,
    register_phase_programs_v1,
    registered_program_ids,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = REPO_ROOT / "configs" / "policy"

SLURP_PROGRAM_ID = "phase-native-candidates-review-revise-acquire-v1"
NEUTRAL_PROGRAM_ID = "phase-native-review-revise-acquire-v1"


def test_both_program_ids_are_registered():
    register_phase_programs_v1()
    assert SLURP_PROGRAM_ID in registered_program_ids()
    assert NEUTRAL_PROGRAM_ID in registered_program_ids()


def test_the_neutral_program_loads_with_five_phases_and_ceiling_eleven():
    program = default_phase_program(NEUTRAL_PROGRAM_ID)
    assert [phase.name for phase in program.phases] == [
        "perception",
        "reviewer",
        "planner",
        "solver",
        "acquisition",
    ]
    assert program.max_contacts == 11
    assert program.stop_rule == "native-role-episode"


def test_the_neutral_program_declares_no_perception_response_format():
    program = default_phase_program(NEUTRAL_PROGRAM_ID)
    perception = next(phase for phase in program.phases if phase.name == "perception")
    assert perception.response_format_id is None


def test_the_slurp_program_is_byte_unchanged_by_this_item():
    program = default_phase_program(SLURP_PROGRAM_ID)
    assert [phase.name for phase in program.phases] == [
        "perception",
        "reviewer",
        "planner",
        "solver",
        "acquisition",
    ]
    assert program.max_contacts == 11
    assert program.stop_rule == "native-role-episode"
    perception = next(phase for phase in program.phases if phase.name == "perception")
    assert perception.response_format_id == "slurp-intent-hypotheses-v1"

    document = json.loads(
        (POLICY_DIR / f"{SLURP_PROGRAM_ID}.json").read_text(encoding="utf-8")
    )
    assert document == {
        "schema": "saea-phase-program-v1",
        "program_id": SLURP_PROGRAM_ID,
        "phases": [
            {
                "name": "perception",
                "purpose": "form-candidates",
                "knowledge": "supplied",
                "response_format_id": "slurp-intent-hypotheses-v1",
                "barrier": False,
            },
            {
                "name": "reviewer",
                "purpose": "review-evidence",
                "knowledge": "supplied",
                "response_format_id": None,
                "barrier": False,
            },
            {
                "name": "planner",
                "purpose": "choose-next-action",
                "knowledge": "supplied",
                "response_format_id": None,
                "barrier": False,
            },
            {
                "name": "solver",
                "purpose": "answer",
                "knowledge": "supplied",
                "response_format_id": None,
                "barrier": False,
            },
            {
                "name": "acquisition",
                "purpose": "acquire-evidence",
                "knowledge": "none",
                "response_format_id": None,
                "barrier": False,
            },
        ],
        "max_contacts": 11,
        "stop_rule": "native-role-episode",
    }


def test_the_two_programs_differ_only_in_perception_response_format():
    slurp_doc = json.loads((POLICY_DIR / f"{SLURP_PROGRAM_ID}.json").read_text(encoding="utf-8"))
    neutral_doc = json.loads((POLICY_DIR / f"{NEUTRAL_PROGRAM_ID}.json").read_text(encoding="utf-8"))

    assert slurp_doc["schema"] == neutral_doc["schema"]
    assert slurp_doc["max_contacts"] == neutral_doc["max_contacts"]
    assert slurp_doc["stop_rule"] == neutral_doc["stop_rule"]
    assert neutral_doc["program_id"] == NEUTRAL_PROGRAM_ID

    for slurp_phase, neutral_phase in zip(slurp_doc["phases"], neutral_doc["phases"]):
        assert slurp_phase["name"] == neutral_phase["name"]
        assert slurp_phase["purpose"] == neutral_phase["purpose"]
        assert slurp_phase["knowledge"] == neutral_phase["knowledge"]
        assert slurp_phase["barrier"] == neutral_phase["barrier"]
        if slurp_phase["name"] == "perception":
            assert slurp_phase["response_format_id"] == "slurp-intent-hypotheses-v1"
            assert neutral_phase["response_format_id"] is None
        else:
            assert slurp_phase["response_format_id"] == neutral_phase["response_format_id"]
