"""C4a: PhaseProgram/PhaseSpec config loading and strict refusal, and the
generic EvidenceAgentController state machine across the registered
phase programs (direct-only, direct-evidence-alpha-blend, select-then-fill,
draft-revise, slots-given-intent). No model, GPU, or network contact -- every test drives the
controller directly with a synthetic AgentRuntimeContext, exactly the
"isinstance-free structural check" the mission brief asks for.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import AGENT_CONTROLLERS
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.runner import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentRuntimeContext,
)
from speech_aware_evidence_acquisition.rails.supply import (
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64

_EXPECTED_PROGRAM_SHAPES = {
    "phase-direct-only-v1": (("direct",), 1, "always-run-full-program"),
    "phase-direct-evidence-alpha-blend-v1": (
        ("direct", "evidence"),
        2,
        "stop-policy-optional-early-exit",
    ),
    "phase-select-then-fill-v1": (("select", "fill"), 2, "always-run-full-program"),
    "phase-draft-revise-v1": (("draft", "revise"), 2, "always-run-full-program"),
    "phase-slots-given-intent-v1": (("slots",), 1, "always-run-full-program"),
}


def _query_state(*, sample_id: str = "s1", loop_step: int = 0, agent_state_ids=()) -> QueryState:
    return QueryState(
        query_id=f"run:{sample_id}:step{loop_step}",
        query_sample_id=sample_id,
        speech_packet_id=f"speech/{sample_id}",
        speech_packet_sha256=_SHA_A,
        use_split_identity_hash=_SHA_A,
        loop_step=loop_step,
        agent_state_ids=agent_state_ids,
    ).validate()


def _context(query_state: QueryState, *, contact_index: int = 0, agent_states=()) -> AgentRuntimeContext:
    return AgentRuntimeContext(
        sample_id=query_state.query_sample_id,
        knowledge_snapshot_sha256=_SHA_B,
        catalog_facet_ids=(),
        catalog_value_ids=(),
        query_state=query_state,
        task_contract="fake task contract",
        agent_states=agent_states,
        prior_response_sha256s=(),
        contact_index=contact_index,
    )


def _material(phase_name: str, sample_id: str, *, response_format=None) -> PhaseMaterial:
    return PhaseMaterial(
        instruction=f"Do {phase_name} for {sample_id}",
        response_format=response_format,
        contact_id=f"c-{phase_name}-{sample_id}",
        purpose=phase_name,
    )


# ---------------------------------------------------------------------------
# PhaseSpec / PhaseProgram loading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("program_id, shape", sorted(_EXPECTED_PROGRAM_SHAPES.items()))
def test_load_phase_program_loads_the_shipped_configs(program_id, shape):
    expected_names, expected_max_contacts, expected_stop_rule = shape
    path = rc.DEFAULT_PROGRAM_CONFIG_DIR / f"{program_id}.json"
    program = rc.load_phase_program(path)
    assert program.program_id == program_id
    assert program.phase_names() == expected_names
    assert program.max_contacts == expected_max_contacts
    assert program.stop_rule == expected_stop_rule
    for phase in program.phases:
        phase.validate()


def test_registered_program_ids_match_the_shipped_configs():
    assert set(rc.registered_program_ids()) == set(_EXPECTED_PROGRAM_SHAPES)


def test_registered_program_ids_are_present_in_agent_controllers_registry():
    names = set(AGENT_CONTROLLERS.names())
    for program_id in rc.registered_program_ids():
        assert program_id in names


def test_register_phase_programs_v1_is_idempotent():
    before = set(AGENT_CONTROLLERS.names())
    rc.register_phase_programs_v1()
    rc.register_phase_programs_v1()
    assert set(AGENT_CONTROLLERS.names()) == before


def _write_program(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "program.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _valid_document(**overrides) -> dict:
    document = {
        "schema": rc.PHASE_PROGRAM_SCHEMA,
        "program_id": "test-program-v1",
        "phases": [
            {
                "name": "only",
                "purpose": "only-purpose",
                "knowledge": "none",
                "response_format_id": None,
                "barrier": False,
            }
        ],
        "max_contacts": 1,
        "stop_rule": "always-run-full-program",
    }
    document.update(overrides)
    return document


def test_load_phase_program_refuses_missing_file(tmp_path: Path):
    with pytest.raises(rc.RailsControllersError, match="not found"):
        rc.load_phase_program(tmp_path / "missing.json")


def test_load_phase_program_refuses_invalid_json(tmp_path: Path):
    path = tmp_path / "program.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(rc.RailsControllersError, match="not valid JSON"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_non_object_document(tmp_path: Path):
    path = tmp_path / "program.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(rc.RailsControllersError, match="must be a JSON object"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_unknown_top_level_key(tmp_path: Path):
    path = _write_program(tmp_path, _valid_document(extra_field="nope"))
    with pytest.raises(rc.RailsControllersError, match="unknown keys"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_missing_top_level_key(tmp_path: Path):
    document = _valid_document()
    del document["stop_rule"]
    path = _write_program(tmp_path, document)
    with pytest.raises(rc.RailsControllersError, match="missing keys"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_wrong_schema(tmp_path: Path):
    path = _write_program(tmp_path, _valid_document(schema="wrong-schema"))
    with pytest.raises(rc.RailsControllersError, match="schema must be"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_empty_phases(tmp_path: Path):
    path = _write_program(tmp_path, _valid_document(phases=[]))
    with pytest.raises(rc.RailsControllersError, match="non-empty array"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_non_object_phase_entry(tmp_path: Path):
    path = _write_program(tmp_path, _valid_document(phases=["not-an-object"]))
    with pytest.raises(rc.RailsControllersError, match="non-object phase entry"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_unknown_phase_key(tmp_path: Path):
    document = _valid_document()
    document["phases"][0]["extra"] = "nope"
    path = _write_program(tmp_path, document)
    with pytest.raises(rc.RailsControllersError, match="unknown keys"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_missing_phase_key(tmp_path: Path):
    document = _valid_document()
    del document["phases"][0]["barrier"]
    path = _write_program(tmp_path, document)
    with pytest.raises(rc.RailsControllersError, match="missing keys"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_duplicate_phase_names(tmp_path: Path):
    document = _valid_document()
    document["phases"].append(dict(document["phases"][0]))
    document["max_contacts"] = 2
    path = _write_program(tmp_path, document)
    with pytest.raises(rc.RailsControllersError, match="unique phase names"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_max_contacts_below_phase_count(tmp_path: Path):
    document = _valid_document()
    document["phases"].append(
        {
            "name": "second",
            "purpose": "second-purpose",
            "knowledge": "none",
            "response_format_id": None,
            "barrier": False,
        }
    )
    document["max_contacts"] = 1
    path = _write_program(tmp_path, document)
    with pytest.raises(rc.RailsControllersError, match="max_contacts"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_unknown_stop_rule(tmp_path: Path):
    path = _write_program(tmp_path, _valid_document(stop_rule="whenever"))
    with pytest.raises(rc.RailsControllersError, match="stop_rule"):
        rc.load_phase_program(path)


def test_load_phase_program_refuses_unknown_knowledge_kind(tmp_path: Path):
    document = _valid_document()
    document["phases"][0]["knowledge"] = "bogus"
    path = _write_program(tmp_path, document)
    with pytest.raises(rc.RailsControllersError, match="knowledge"):
        rc.load_phase_program(path)


def test_phase_program_solo_reduces_to_one_phase_and_max_contacts_one():
    program = rc.default_phase_program("phase-draft-revise-v1")
    solo = program.solo("revise")
    assert solo.phase_names() == ("revise",)
    assert solo.max_contacts == 1
    assert solo.stop_rule == "always-run-full-program"


def test_phase_program_solo_refuses_unknown_phase_name():
    program = rc.default_phase_program("phase-draft-revise-v1")
    with pytest.raises(rc.RailsControllersError, match="no phase named"):
        program.solo("nonexistent")


def test_phase_program_validate_refuses_max_contacts_bool():
    program = rc.default_phase_program("phase-direct-only-v1")
    bad = rc.PhaseProgram(
        program_id=program.program_id,
        phases=program.phases,
        max_contacts=True,
        stop_rule=program.stop_rule,
    )
    with pytest.raises(rc.RailsControllersError, match="max_contacts"):
        bad.validate()


# ---------------------------------------------------------------------------
# EvidenceAgentController: the direct-only (single phase) program
# ---------------------------------------------------------------------------


def test_direct_only_controller_runs_one_contact_then_stops():
    program = rc.default_phase_program("phase-direct-only-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)

    contact = controller.initial_contact(ctx0)
    assert isinstance(contact, AgentContactPlan)
    assert contact.contact_id == "c-direct-s1"
    assert contact.purpose == "direct-decode"

    advance = controller.advance(ctx0, contact, "the direct answer")
    assert isinstance(advance, AgentLoopAdvance)
    assert advance.transition.action_kind == "stop"
    assert advance.next_contact is None
    assert advance.next_query_state is None
    assert advance.final_response_contact_id == "c-direct-s1"
    assert controller.sealed_states["direct"].content == "the direct answer"
    assert (
        controller.sealed_states["direct"].source_response_sha256
        == hashlib.sha256(b"the direct answer").hexdigest()
    )
    assert controller.sealed_states["direct"].source_query_state_sha256 == qs0.content_hash()


def test_evidence_agent_controller_rejects_reentrant_initial_contact():
    program = rc.default_phase_program("phase-direct-only-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
    )
    ctx0 = _context(_query_state())
    controller.initial_contact(ctx0)
    with pytest.raises(rc.RailsControllersError, match="out of sequence"):
        controller.initial_contact(ctx0)


def test_evidence_agent_controller_rejects_non_string_response():
    program = rc.default_phase_program("phase-direct-only-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
    )
    ctx0 = _context(_query_state())
    contact = controller.initial_contact(ctx0)
    with pytest.raises(rc.RailsControllersError, match="one string response"):
        controller.advance(ctx0, contact, 12345)  # type: ignore[arg-type]


def test_evidence_agent_controller_rejects_out_of_sequence_contact():
    program = rc.default_phase_program("phase-direct-only-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
    )
    ctx0 = _context(_query_state())
    controller.initial_contact(ctx0)
    forged_contact = AgentContactPlan(
        contact_id="not-the-pending-contact",
        query_state_sha256=ctx0.query_state.content_hash(),
        purpose="direct-decode",
        instruction="forged",
        key_representation_id="k",
        matcher_policy_id="m",
        decoding_params={},
    )
    with pytest.raises(rc.RailsControllersError, match="out-of-sequence contact"):
        controller.advance(ctx0, forged_contact, "response")


def test_evidence_agent_controller_rejects_material_for_phase_returning_wrong_type():
    program = rc.default_phase_program("phase-direct-only-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: "not a PhaseMaterial",
    )
    with pytest.raises(rc.RailsControllersError, match="must return a PhaseMaterial"):
        controller.initial_contact(_context(_query_state()))


def test_evidence_agent_controller_rejects_uncallable_constructor_args():
    program = rc.default_phase_program("phase-direct-only-v1")
    with pytest.raises(rc.RailsControllersError, match="material_for_phase"):
        rc.EvidenceAgentController(program=program, material_for_phase="nope")  # type: ignore[arg-type]
    with pytest.raises(rc.RailsControllersError, match="supply_for_phase"):
        rc.EvidenceAgentController(
            program=program,
            material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
            supply_for_phase="nope",  # type: ignore[arg-type]
        )
    with pytest.raises(rc.RailsControllersError, match="stop_policy"):
        rc.EvidenceAgentController(
            program=program,
            material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
            stop_policy="nope",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# EvidenceAgentController: two-phase programs (direct-evidence-alpha-blend,
# select-then-fill run as a full non-solo trajectory, draft-revise)
# ---------------------------------------------------------------------------


def _run_two_phase_trajectory(controller, *, sample_id="s1"):
    """Drive a two-phase controller to its stop and return
    (contact0, advance0, contact1, advance1)."""

    qs0 = _query_state(sample_id=sample_id)
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    advance0 = controller.advance(ctx0, contact0, "response-for-phase-0")
    assert advance0.next_contact is not None
    contact1 = advance0.next_contact
    ctx1 = _context(
        advance0.next_query_state,
        contact_index=1,
        agent_states=advance0.new_agent_states,
    )
    advance1 = controller.advance(ctx1, contact1, "response-for-phase-1")
    return contact0, advance0, contact1, advance1


def test_draft_revise_runs_two_contacts_and_phase_two_material_sees_sealed_draft():
    program = rc.default_phase_program("phase-draft-revise-v1")
    observed_predecessor_content: list[str | None] = []

    controller_ref: dict[str, rc.EvidenceAgentController] = {}

    def material_for_phase(name, ctx):
        controller = controller_ref["controller"]
        sealed_draft = controller.sealed_states.get("draft")
        observed_predecessor_content.append(sealed_draft.content if sealed_draft else None)
        instruction = f"Do {name} for {ctx.sample_id}"
        if sealed_draft is not None:
            instruction = f"{instruction}\n\nSealed draft:\n{sealed_draft.content}"
        return PhaseMaterial(
            instruction=instruction,
            response_format=None,
            contact_id=f"c-{name}-{ctx.sample_id}",
            purpose=name,
        )

    controller = rc.EvidenceAgentController(program=program, material_for_phase=material_for_phase)
    controller_ref["controller"] = controller

    contact0, advance0, contact1, advance1 = _run_two_phase_trajectory(controller)

    assert observed_predecessor_content == [None, "response-for-phase-0"]
    assert "Sealed draft:\nresponse-for-phase-0" in contact1.instruction
    assert advance0.transition.action_kind == "organize"
    assert advance0.transition.new_agent_state_ids == ("draft:s1",)
    assert advance1.transition.action_kind == "stop"
    assert advance1.final_response_contact_id == contact1.contact_id
    assert set(controller.sealed_states) == {"draft", "revise"}


def test_direct_evidence_alpha_blend_stop_policy_skips_the_evidence_contact():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        stop_policy=lambda ctx, completed: True,
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    advance0 = controller.advance(ctx0, contact0, "direct wins uniquely")

    assert advance0.transition.action_kind == "stop"
    assert advance0.next_contact is None
    assert advance0.final_response_contact_id == contact0.contact_id
    assert set(controller.sealed_states) == {"direct"}


def test_direct_evidence_alpha_blend_stop_policy_false_continues_to_evidence():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    stop_calls: list[tuple[str, ...]] = []

    def stop_policy(ctx, completed):
        stop_calls.append(completed)
        return False

    def supply_for_phase(name, ctx):
        if name != "evidence":
            return None
        return SupplyPacket(
            form=SupplyForm.TEXT,
            dose=SupplyDose(n_items=1, token_count=1),
            prompt_block="fused evidence text",
            assembly_template_id="t1",
            items=(SupplyItem(item_id="i1", text="fused evidence text"),),
        )

    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=supply_for_phase,
        stop_policy=stop_policy,
    )
    contact0, advance0, contact1, advance1 = _run_two_phase_trajectory(controller)

    assert stop_calls == [("direct",)]
    assert advance0.transition.action_kind == "organize"
    assert "fused evidence text" in contact1.instruction
    assert advance1.transition.action_kind == "stop"
    assert advance1.final_response_contact_id == contact1.contact_id


def test_direct_evidence_alpha_blend_default_stop_rule_ignores_none_stop_policy():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        # stop_policy omitted: stop_rule is stop-policy-optional-early-exit,
        # but with no policy injected the program must run to completion.
    )
    _contact0, advance0, _contact1, advance1 = _run_two_phase_trajectory(controller)
    assert advance0.transition.action_kind == "organize"
    assert advance1.transition.action_kind == "stop"


def test_select_then_fill_controller_walks_both_phases_when_run_as_one_trajectory():
    """The controller itself is agnostic to PhaseSpec.barrier -- the barrier
    is realized entirely at the phase_runner level (module docstring). Run
    directly against the FULL (non-solo) program to prove the controller
    would happily run it as one continuous two-contact trajectory too."""

    program = rc.default_phase_program("phase-select-then-fill-v1")
    assert program.phase("select").barrier is True
    assert program.phase("fill").barrier is False

    def material_for_phase(name, ctx):
        response_format = {"type": "object"} if name == "select" else {"type": "array"}
        return _material(name, ctx.sample_id, response_format=response_format)

    controller = rc.EvidenceAgentController(program=program, material_for_phase=material_for_phase)
    _contact0, advance0, _contact1, advance1 = _run_two_phase_trajectory(controller)
    assert advance0.transition.action_kind == "organize"
    assert advance1.transition.action_kind == "stop"
    assert set(controller.sealed_states) == {"select", "fill"}


def test_evidence_agent_controller_response_format_mismatch_missing_is_refused():
    program = rc.default_phase_program("phase-select-then-fill-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        # "select" declares response_format_id but this material omits it.
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
    )
    with pytest.raises(rc.RailsControllersError, match="response_format"):
        controller.initial_contact(_context(_query_state()))


def test_evidence_agent_controller_response_format_mismatch_unexpected_is_refused():
    program = rc.default_phase_program("phase-direct-only-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        # "direct" declares no response_format_id but this material supplies one.
        material_for_phase=lambda name, ctx: _material(
            name, ctx.sample_id, response_format={"type": "object"}
        ),
    )
    with pytest.raises(rc.RailsControllersError, match="response_format"):
        controller.initial_contact(_context(_query_state()))


def test_evidence_agent_controller_rejects_bad_supply_for_phase_return_type():
    program = rc.default_phase_program("phase-direct-only-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: "not a SupplyPacket",
    )
    with pytest.raises(rc.RailsControllersError, match="SupplyPacket"):
        controller.initial_contact(_context(_query_state()))


# ---------------------------------------------------------------------------
# Structural AgentController-protocol check (isinstance-free, per the brief)
# ---------------------------------------------------------------------------


def test_evidence_agent_controller_satisfies_agent_controller_protocol_structurally():
    program = rc.default_phase_program("phase-draft-revise-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
    )
    assert callable(getattr(controller, "initial_contact", None))
    assert callable(getattr(controller, "advance", None))

    context = _context(_query_state())
    contact = controller.initial_contact(context)
    assert isinstance(contact, AgentContactPlan)

    advance = controller.advance(context, contact, "draft text")
    assert isinstance(advance, AgentLoopAdvance)
    assert advance.next_contact is not None
    assert isinstance(advance.next_contact, AgentContactPlan)


# ---------------------------------------------------------------------------
# The registered default factories (snapshot-free, always-safe)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("program_id", sorted(_EXPECTED_PROGRAM_SHAPES))
def test_default_controller_factory_runs_to_completion_for_every_registered_program(program_id):
    factory = AGENT_CONTROLLERS.resolve(program_id)
    controller = factory("s1")
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    assert isinstance(contact, AgentContactPlan)
    advance = controller.advance(context, contact, "a generic response")
    assert isinstance(advance, AgentLoopAdvance)
    # Walk any remaining phases to their eventual stop.
    while advance.transition.action_kind != "stop":
        next_context = _context(
            advance.next_query_state,
            contact_index=context.contact_index + 1,
            agent_states=advance.new_agent_states,
        )
        advance = controller.advance(next_context, advance.next_contact, "another response")
        context = next_context
    assert advance.final_response_contact_id is not None
