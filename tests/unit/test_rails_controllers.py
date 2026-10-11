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
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import AGENT_CONTROLLERS
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.knowledge import (
    AgentStateArtifact,
    FusionDecision,
    QueryState,
    RankedFacet,
    RankResult,
)
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
    # 2026-09-26: four programs were shipped and registered while this table was not
    # extended, so the registry/table equality test failed at 41 vs 37. The shapes below are
    # read from the shipped configs, not chosen: a stale oracle is a defect in the oracle.
    # All four are single-visit artifact programs -- they ask the frozen core for one
    # analysis or one selection, not for a task answer -- which is why none of them carries
    # the four-node native-role-episode shape.
    "phase-knowledge-value-edit-v1": (
        ("direct",), 1, "always-run-full-program"
    ),
    "phase-slurp-verify-select-v1": (
        ("choose",), 2, "always-run-full-program"
    ),
    "phase-system-batch-operations-v1": (
        ("direct",), 1, "always-run-full-program"
    ),
    "phase-system-group-operations-v1": (
        ("direct",), 1, "always-run-full-program"
    ),
    "phase-audio2tool-native-candidate-recovery-tools-v1": (
        ("perception", "reviewer", "planner", "solver"), 14, "native-role-episode"
    ),
    "phase-audio2tool-native-candidates-review-revise-v1": (
        ("perception", "reviewer", "planner", "solver"), 11, "native-role-episode"
    ),
    "phase-audio2tool-native-candidates-review-revise-json-v1": (
        ("perception", "reviewer", "planner", "solver"), 11, "native-role-episode"
    ),
    "phase-native-candidates-review-revise-v1": (
        ("perception", "reviewer", "planner", "solver"), 11, "native-role-episode"
    ),
    # Cell B7r, 2026-09-17: the review-revise program with the Reviewer
    # phase declaring the registered findings output contract. Same four
    # phases, same ceiling 11; only the Reviewer's response_format_id moves.
    "phase-native-candidates-review-revise-findings-v1": (
        ("perception", "reviewer", "planner", "solver"), 11, "native-role-episode"
    ),
    # Gap G1 plumbing, 2026-09-26 (rails.solver_citation): the same four
    # phases and ceiling 11; only the Solver's response_format_id moves, to
    # the registered cited-answer contract.
    "phase-native-candidates-review-revise-cited-v1": (
        ("perception", "reviewer", "planner", "solver"), 11, "native-role-episode"
    ),
    # E1, 2026-09-16 (M0): the same four phases with the review loop off, so
    # Reviewer and Planner never get a node -- ceiling drops from 11 to 2.
    # Slot-review contract program, 2026-10-02 (docs/readiness/2026-10-02-slot-review-contract-
    # correction-v1): shipped and registered without extending this table. Shape read from
    # configs/policy/phase-native-slot-review-contract-v1.json -- the four-role episode with the
    # Reviewer on the registered slot-review handoff contract, ceiling 13.
    "phase-native-slot-review-contract-v1": (
        ("perception", "reviewer", "planner", "solver"), 13, "native-role-episode"
    ),
    "phase-native-candidates-solve-v1": (
        ("perception", "reviewer", "planner", "solver"), 2, "native-role-episode"
    ),
    # E2b, 2026-09-16 (M2 on the review-off base): the review-off program with
    # a grouped Solver visit, so the ceiling is 1 + 1*(0 + 0 + 1*5) = 6.
    # Cell P1, 2026-09-22 (decision 85 on the R-PRIM base, decision 97): the
    # review-revise program with the Reviewer at ONE visit per round, so the
    # ceiling is 1 + (1+1)*(1 + 1 + 1) = 7.
    "phase-native-candidates-review1-revise-v1": (
        ("perception", "reviewer", "planner", "solver"), 7, "native-role-episode"
    ),
    "phase-native-candidates-solve-samples5-v1": (
        ("perception", "reviewer", "planner", "solver"), 6, "native-role-episode"
    ),
    # Cell B2 on the sealed anchor, 2026-09-17 (M2 on the review-loop-ON base):
    # the review-revise program with a grouped Solver visit, so the ceiling is
    # 1 + (1+1)*(1*5 + 3 + 1) = 19.
    "phase-native-candidates-review-revise-samples5-v1": (
        ("perception", "reviewer", "planner", "solver"), 19, "native-role-episode"
    ),
    # Cell ROLL-AA, 2026-09-24 (board route F2, the Stage-3 within-flight A/A
    # null): the same review-revise program with a grouped Solver visit at
    # samples 2 instead of 5, so the ceiling is 1 + (1+1)*(1*2 + 3 + 1) = 13.
    # It shares that 13 with the clean1 program above by arithmetic, not by
    # meaning -- clean1 reaches it through a cleaning boundary -- which is
    # exactly why each carries its own program id.
    "phase-native-candidates-review-revise-samples2-v1": (
        ("perception", "reviewer", "planner", "solver"), 13, "native-role-episode"
    ),
    # Item E42, 2026-09-25 (board route F12, Stage-3 family VAR-2: per-row
    # CONSTRUCTION-VARIANT interleaving inside ONE campaign): the same
    # review-revise program with the Solver visit fanned out to FOUR declared
    # supply-variant arms instead of one, so the ceiling is
    # 1 + (1+1)*(1*1*4 + 3 + 1) = 17. rails.native_episode_config multiplies
    # the Solver's own contribution by its registered arm count exactly as it
    # multiplies it by samples.
    "phase-native-candidates-review-revise-variants4-v1": (
        ("perception", "reviewer", "planner", "solver"), 17, "native-role-episode"
    ),
    # Owner decision 172, 2026-09-27 (merge set B, docs/superpowers/specs/
    # 2026-09-27-same-flight-supply-variant-instrument-design.md): the cited
    # review-revise program (anchor 11) with the Solver visit fanned out to
    # TWO declared supply-variant arms under arm_visits "first" -- only the
    # first visit fans out, so the ceiling is the anchor's 11 + (K - 1) = 12,
    # not the "every" product 1 + (1+1)*(1*1*2+3+1) = 13.
    "phase-native-candidates-review-revise-cited-variants2first-v1": (
        ("perception", "reviewer", "planner", "solver"), 12, "native-role-episode"
    ),
    # Owner decision 172, 2026-09-27: the same shape with a THIRD arm
    # (K = 3), so the ceiling is 11 + (3 - 1) = 13.
    "phase-native-candidates-review-revise-cited-variants3first-v1": (
        ("perception", "reviewer", "planner", "solver"), 13, "native-role-episode"
    ),
    # Coordinator amendment, 2026-09-28 (docs/superpowers/specs/2026-09-27-
    # same-flight-supply-variant-instrument-design.md, "Coordinator amendment
    # (2026-09-28)"): the UNCITED twin of
    # "phase-native-candidates-review-revise-cited-variants2first-v1" above --
    # the uncited review-revise program (anchor 11) with the Solver visit
    # fanned out to TWO declared supply-variant arms under arm_visits
    # "first", so the ceiling is the anchor's 11 + (K - 1) = 12.
    "phase-native-candidates-review-revise-variants2first-v1": (
        ("perception", "reviewer", "planner", "solver"), 12, "native-role-episode"
    ),
    # Coordinator amendment, 2026-09-28: the same shape with a THIRD arm
    # (K = 3), so the ceiling is 11 + (3 - 1) = 13.
    "phase-native-candidates-review-revise-variants3first-v1": (
        ("perception", "reviewer", "planner", "solver"), 13, "native-role-episode"
    ),
    # Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    # specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    # design.md section 5, item 8): the review-revise program (anchor 11)
    # with the Perception visit fanned out to K = 3 declared branches, level 1
    # (note only): the ceiling is the anchor's 11 + (K - 1) = 13.
    "phase-native-candidates-review-revise-pbranch3-l1-v1": (
        ("perception", "reviewer", "planner", "solver"), 13, "native-role-episode"
    ),
    # Same-flight instrument, PHASE 2: the same shape at level 2 (note + one
    # Solver contact per non-A branch) instead of level 1: the ceiling is the
    # anchor's 11 + 2 (K - 1) = 15.
    "phase-native-candidates-review-revise-pbranch3-l2-v1": (
        ("perception", "reviewer", "planner", "solver"), 15, "native-role-episode"
    ),
    # Item E4 (2026-09-28, owner decision 185, "core-native targeted re-
    # listen"; design docs/superpowers/specs/2026-09-28-e4-core-native-
    # targeted-relisten-design.md section 6, section 8 rulings): the
    # review-revise program (anchor 11) with a post-accept
    # native_episode.relisten block armed (max_slots_per_row 3, two
    # contacts per triggered entity): the ceiling is the anchor's
    # 11 + 2 * 3 = 17. Uncited: no baseline or experiment fragment names it
    # yet.
    "phase-native-candidates-review-revise-relisten-v1": (
        ("perception", "reviewer", "planner", "solver"), 17, "native-role-episode"
    ),
    # Cell B7b on the sealed anchor, 2026-09-17 (M5 / NCP level L2): the
    # review-revise program with ONE declared cleaning boundary, so the
    # ceiling is 1 + (1+1)*(1 + 3 + 1 + 1) = 13.
    "phase-native-candidates-review-revise-clean1-v1": (
        ("perception", "reviewer", "planner", "solver"), 13, "native-role-episode"
    ),
    # E32, 2026-09-21: the review-revise program plus the fifth, optional
    # Acquisition phase E18 built. Same ceiling 11 as the four-phase program
    # -- the registered zero-contact acquisition kinds add nothing to it --
    # by construction, not by coincidence (rails.controllers._PROGRAM_CONFIG_
    # FILENAMES comment beside the registration).
    "phase-native-candidates-review-revise-acquire-v1": (
        ("perception", "reviewer", "planner", "solver", "acquisition"),
        11,
        "native-role-episode",
    ),
    # Item E35, 2026-09-21 (owner decision 89): a CARRIER-NEUTRAL twin of the
    # program above -- same five phases, same ceiling 11, same stop rule --
    # with the Perception phase's response_format_id null instead of SLURP's
    # "slurp-intent-hypotheses-v1", so the Earnings21+ConEC carrier can fly
    # the same six-node native episode through the same shared harness.
    "phase-native-review-revise-acquire-v1": (
        ("perception", "reviewer", "planner", "solver", "acquisition"),
        11,
        "native-role-episode",
    ),
    "phase-native-candidates-review-refresh-v1": (
        ("perception", "reviewer", "planner", "solver"), 12, "native-role-episode"
    ),
    "phase-native-review-revise-v1": (("perception", "reviewer", "planner", "solver"), 11, "native-role-episode"),
    "phase-native-review-revise-json-v1": (("perception", "reviewer", "planner", "solver"), 11, "native-role-episode"),
    "phase-intent-hypotheses-only-v1": (
        ("hypotheses",),
        1,
        "always-run-full-program",
    ),
    "native-answer-or-tool-v1": (("decision-1", "decision-2", "final"), 3, "native-answer-or-tool"),
    "native-answer-or-one-tool-v1": (("decision-1", "final"), 2, "native-answer-or-tool"),
    "phase-task-tools-then-solve-v1": (("plan", "solve"), 2, "always-run-full-program"),
    "phase-task-tools-solve-revise-v1": (
        ("plan", "solve", "revise"),
        3,
        "always-run-full-program",
    ),
    "phase-direct-only-v1": (("direct",), 1, "always-run-full-program"),
    # Stage-3 S3-4 (2026-09-22): one phase, one contact, the same shape as
    # phase-direct-only-v1; bound to the construction-advantage-text arm and
    # the stage3-advantage-statement-v1 response format instead.
    "phase-stage3-advantage-v1": (("advantage",), 1, "always-run-full-program"),
    # Stage-3 S3-4s (owner decision 106, 2026-09-23): the SYSTEM-level
    # advantage program -- the same one-phase shape, binding the
    # stage3-advantage-statement-v2 response format (one to three
    # NODE/DELTA-KIND/TARGET/STATEMENT blocks) instead of v1's single
    # three-line statement. A program and its fragment must agree on a
    # phase output contract, so the v2 contract needs its own program.
    "phase-stage3-advantage-v2": (("advantage",), 1, "always-run-full-program"),
    # Stage-3 layer A, the GEPA arm: one phase ("gepa"), one contact, the same
    # one-phase shape the two advantage programs have. It differs in exactly
    # one field, the stage3-gepa-proposal-v1 response format (one to FIVE
    # blocks, all addressed to the group's single node), and it is the id
    # core.flight.runtime._default_construction_material dispatches the GEPA
    # material on, because both construction-visible cells fly the SAME arm.
    "phase-stage3-gepa-v1": (("gepa",), 1, "always-run-full-program"),
    # Decision 263-A (2026-10-11), E-T1: the typed proposer and the ACE reflector,
    # each ONE text-only phase and ONE contact, differing from the GEPA shape in
    # exactly the response format (saea-tfrl-typed-candidate-v1 and
    # saea-ace-delta-items-v1).
    "phase-tfrl-typed-proposer-v1": (("propose",), 1, "always-run-full-program"),
    "phase-tfrl-ace-reflector-v1": (("reflect",), 1, "always-run-full-program"),
    "phase-training-feedback-proposal-v1": (
        ("proposal",),
        1,
        "always-run-full-program",
    ),
    "phase-direct-then-slots-v1": (("direct", "slots"), 2, "always-run-full-program"),
    "phase-direct-then-slots-supplied-v1": (("direct", "slots"), 2, "always-run-full-program"),
    "phase-direct-evidence-alpha-blend-v1": (
        ("direct", "evidence"),
        2,
        "stop-policy-optional-early-exit",
    ),
    "phase-select-then-fill-v1": (("select", "fill"), 2, "always-run-full-program"),
    "phase-draft-revise-v1": (("draft", "revise"), 2, "always-run-full-program"),
    "phase-slots-given-intent-v1": (("slots",), 1, "always-run-full-program"),
    # KU-S3, 2026-09-07: the same one-contact slot program with its single
    # phase declaring knowledge "supplied". Two program ids rather than a flag
    # on one, because a phase's knowledge value rides the config hash.
    "phase-slots-given-intent-supplied-v1": (("slots",), 1, "always-run-full-program"),
    # KU-S4N, 2026-09-09: phase-direct-only-v1's single direct-decode phase
    # with knowledge "supplied", for the same reason the slots pair exists --
    # the phase's knowledge value rides the config hash, so the unsupplied
    # direct program and the narrowing cell must not resolve to one object.
    "phase-direct-only-supplied-v1": (("direct",), 1, "always-run-full-program"),
    # WAVE R7, 2026-09-08: the fold of the retired
    # rails.a2t_hard_validity.HardValidityRepairController -- draft, then the
    # repair contact only when the draft is hard-invalid, so the early exit is
    # the stop_policy seam rather than a loop_step branch inside a controller.
    "phase-reviewed-repair-v1": (("draft", "revise"), 2, "stop-policy-optional-early-exit"),
    "phase-hard-validity-repair-v1": (
        ("draft", "repair"),
        2,
        "stop-policy-optional-early-exit",
    ),
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


def _phase_supply(
    ctx: AgentRuntimeContext,
    *,
    value_ids: tuple[str, ...] = ("v-1",),
    facet_ids: tuple[str, ...] = ("f-1",),
    retain_prior: bool = False,
    knowledge_ok: bool = False,
) -> rc.PhaseSupply:
    """One structurally valid PhaseSupply bound to ``ctx``'s own state.

    ``knowledge_ok`` is only a documentation flag for the caller: a program
    phase declaring ``knowledge != "supplied"`` is refused by the controller
    itself, which is what the refusal test asserts.
    """

    _ = knowledge_ok
    rank_result = RankResult(
        snapshot_sha256=ctx.knowledge_snapshot_sha256,
        query_state_sha256=ctx.query_state.content_hash(),
        ranking_policy_id="fake-rank-v1",
        candidates=tuple(
            RankedFacet(facet_id=facet_id, score=1.0 - index / 10.0)
            for index, facet_id in enumerate(facet_ids)
        ),
    ).validate()
    fusion_decision = FusionDecision(
        snapshot_sha256=ctx.knowledge_snapshot_sha256,
        query_state_sha256=ctx.query_state.content_hash(),
        rank_result_sha256=rank_result.content_hash(),
        fusion_policy_id="fake-fuse-v1",
        supporting_facet_ids=facet_ids,
        selected_value_ids=value_ids,
    ).validate()
    return rc.PhaseSupply(
        rank_result=rank_result,
        fusion_decision=fusion_decision,
        retain_prior=retain_prior,
    ).validate()


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


def test_json_planner_program_changes_only_planner_response_format():
    historical = rc.load_phase_program(
        rc.DEFAULT_PROGRAM_CONFIG_DIR
        / "phase-audio2tool-native-candidates-review-revise-v1.json"
    )
    structured = rc.load_phase_program(
        rc.DEFAULT_PROGRAM_CONFIG_DIR
        / "phase-audio2tool-native-candidates-review-revise-json-v1.json"
    )

    assert structured.max_contacts == historical.max_contacts
    assert structured.stop_rule == historical.stop_rule
    assert len(structured.phases) == len(historical.phases)
    for structured_phase, historical_phase in zip(
        structured.phases, historical.phases, strict=True
    ):
        assert structured_phase.name == historical_phase.name
        assert structured_phase.purpose == historical_phase.purpose
        assert structured_phase.knowledge == historical_phase.knowledge
        assert structured_phase.barrier == historical_phase.barrier
        expected_format = (
            "saea-native-planner-action-v1"
            if structured_phase.name == "planner"
            else historical_phase.response_format_id
        )
        assert structured_phase.response_format_id == expected_format


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

    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: _phase_supply(ctx),
        stop_policy=stop_policy,
    )
    contact0, advance0, contact1, advance1 = _run_two_phase_trajectory(controller)

    assert stop_calls == [("direct",)]
    # E6: the supplied phase's transition is an ACQUIRE carrying the
    # decision, and the supplied values travel the successor QueryState --
    # never the instruction.
    assert advance0.transition.action_kind == "acquire"
    assert advance0.transition.new_value_ids == ("v-1",)
    assert advance0.rank_result is not None
    assert advance0.fusion_decision is not None
    assert advance0.next_query_state.retrieved_value_ids == ("v-1",)
    assert contact1.instruction == "Do evidence for s1"
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
    program = rc.default_phase_program("phase-draft-revise-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: "not a PhaseSupply",
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    with pytest.raises(rc.RailsControllersError, match="must return a PhaseSupply"):
        controller.advance(ctx0, contact0, "draft answer")


def test_supply_for_phase_returning_a_bare_supply_packet_is_refused_loudly():
    """E6: the fold-a-packet-into-the-instruction path is GONE, and the old
    return shape fails closed instead of silently reaching the wire."""

    program = rc.default_phase_program("phase-draft-revise-v1")
    packet = SupplyPacket(
        form=SupplyForm.TEXT,
        dose=SupplyDose(n_items=1, token_count=1),
        prompt_block="fused evidence text",
        assembly_template_id="t1",
        items=(SupplyItem(item_id="i1", text="fused evidence text"),),
    )
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: packet,
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    with pytest.raises(rc.RailsControllersError, match="bare SupplyPacket"):
        controller.advance(ctx0, contact0, "draft answer")


def test_supplied_phase_instruction_is_byte_identical_to_the_unsupplied_one():
    """The property the containment rule and every paired contrast depend
    on: turning supply ON changes the successor QueryState and NOTHING about
    the control-turn bytes."""

    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")

    def build(supply_for_phase):
        controller = rc.EvidenceAgentController(
            program=program,
            material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
            supply_for_phase=supply_for_phase,
        )
        return _run_two_phase_trajectory(controller)

    plain0, plain_adv0, plain1, _ = build(None)
    supplied0, supplied_adv0, supplied1, _ = build(lambda name, ctx: _phase_supply(ctx))

    assert supplied0.instruction == plain0.instruction
    assert supplied1.instruction == plain1.instruction
    assert supplied1.instruction.encode("utf-8") == plain1.instruction.encode("utf-8")
    assert plain_adv0.transition.action_kind == "organize"
    assert plain_adv0.transition.new_value_ids == ()
    assert supplied_adv0.transition.action_kind == "acquire"
    assert supplied_adv0.transition.new_value_ids == ("v-1",)


def test_phase_supply_on_a_phase_that_does_not_declare_supplied_knowledge_is_refused():
    program = rc.default_phase_program("phase-draft-revise-v1")
    assert program.phase("revise").knowledge == "none"
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: _phase_supply(ctx),
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    with pytest.raises(rc.RailsControllersError, match="declares knowledge="):
        controller.advance(ctx0, contact0, "draft answer")


def test_phase_supply_retain_prior_stops_on_the_completed_phase_answer():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: _phase_supply(ctx, retain_prior=True),
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    advance0 = controller.advance(ctx0, contact0, "direct wins uniquely")

    assert advance0.transition.action_kind == "stop"
    assert advance0.next_contact is None
    assert advance0.final_response_contact_id == contact0.contact_id


def test_phase_supply_retain_prior_is_refused_on_an_always_run_full_program():
    # No shipped program pairs "always-run-full-program" with a "supplied"
    # phase, so this refusal needs a synthetic one.
    program = rc.PhaseProgram(
        program_id="synthetic-always-run-supplied-v1",
        phases=(
            rc.PhaseSpec(
                name="draft",
                purpose="draft",
                knowledge="none",
                response_format_id=None,
                barrier=False,
            ),
            rc.PhaseSpec(
                name="revise",
                purpose="revise",
                knowledge="supplied",
                response_format_id=None,
                barrier=False,
            ),
        ),
        max_contacts=2,
        stop_rule="always-run-full-program",
    ).validate()
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: _phase_supply(
            ctx, retain_prior=True, knowledge_ok=True
        ),
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    with pytest.raises(rc.RailsControllersError, match="always-run-full-program"):
        controller.advance(ctx0, contact0, "draft answer")


def test_phase_supply_refuses_values_already_visible_in_the_trajectory():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: _phase_supply(ctx),
    )
    qs0 = _query_state().__class__(
        query_id="run:s1:step0",
        query_sample_id="s1",
        speech_packet_id="speech/s1",
        speech_packet_sha256=_SHA_A,
        use_split_identity_hash=_SHA_A,
        loop_step=0,
        retrieved_value_ids=("v-1",),
    ).validate()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    with pytest.raises(rc.RailsControllersError, match="already visible"):
        controller.advance(ctx0, contact0, "direct answer")


def test_facet_only_phase_supply_exposes_every_newly_supporting_facet():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda name, ctx: _phase_supply(ctx, value_ids=()),
    )
    _, advance0, _, _ = _run_two_phase_trajectory(controller)
    assert advance0.transition.action_kind == "acquire"
    assert advance0.transition.new_value_ids == ()
    assert advance0.transition.new_facet_ids == ("f-1",)
    assert advance0.next_query_state.visible_facet_ids == ("f-1",)


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
    if rc.default_phase_program(program_id).stop_rule == "native-answer-or-tool":
        with pytest.raises(rc.RailsControllersError, match="native.*dispatcher"):
            factory("s1")
        return
    controller = factory("s1")
    context = _context(_query_state())
    if rc.default_phase_program(program_id).stop_rule == "native-role-episode":
        with pytest.raises(rc.RailsControllersError, match="OpenJiuwen episode binding"):
            controller.initial_contact(context)
        return
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


def test_three_phase_program_preserves_knowledge_through_treatment_observation():
    program = rc.default_phase_program("phase-task-tools-solve-revise-v1")
    calls = []
    selected = ("value-2", "value-1")

    def tool_state(phase, staged, *, cited=()):
        return AgentStateArtifact(
            state_id=f"tool-result:{phase}:{staged.sample_id}",
            state_kind="tool-result",
            content=f"synthetic {phase} tool result",
            source_query_state_sha256=staged.query_state.content_hash(),
            source_response_sha256=staged.prior_response_sha256s[-1],
            producer_policy_id=program.program_id,
            cited_value_ids=cited,
        ).validate()

    def tools_for_phase(phase, next_phase, staged):
        calls.append((phase, next_phase))
        if phase == "plan":
            return rc.PhaseToolStep(
                supply=_phase_supply(staged, value_ids=selected),
                state=tool_state(phase, staged, cited=selected),
            ).validate()
        assert phase == "solve"
        return rc.PhaseToolStep(
            supply=None,
            state=tool_state(phase, staged),
        ).validate()

    tools_for_phase.is_action_phase = lambda phase: phase in {"plan", "solve"}
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        tools_for_phase=tools_for_phase,
    )
    context0 = replace(_context(_query_state()), catalog_value_ids=selected)
    plan_contact = controller.initial_contact(context0)
    after_plan = controller.advance(context0, plan_contact, "compact frame")
    assert after_plan.next_contact.contact_id == "c-solve-s1"
    assert after_plan.next_query_state.retrieved_value_ids == selected

    plan_sha = hashlib.sha256(b"compact frame").hexdigest()
    context1 = replace(
        context0,
        query_state=after_plan.next_query_state,
        agent_states=after_plan.new_agent_states,
        prior_response_sha256s=(plan_sha,),
        contact_index=1,
    )
    after_solve = controller.advance(context1, after_plan.next_contact, "solver draft")
    assert after_solve.next_contact.contact_id == "c-revise-s1"
    assert after_solve.next_query_state.retrieved_value_ids == selected
    assert after_solve.new_agent_states[-1].state_kind == "tool-result"
    assert after_solve.rank_result is None
    assert after_solve.fusion_decision is None

    solve_sha = hashlib.sha256(b"solver draft").hexdigest()
    context2 = replace(
        context1,
        query_state=after_solve.next_query_state,
        agent_states=context1.agent_states + after_solve.new_agent_states,
        prior_response_sha256s=(plan_sha, solve_sha),
        contact_index=2,
    )
    final = controller.advance(context2, after_solve.next_contact, "revised answer")
    assert final.next_contact is None
    assert final.final_response_contact_id == "c-revise-s1"
    assert calls == [("plan", "solve"), ("solve", "revise")]


class _NativeToolSteps:
    native_enabled = True

    def __init__(self):
        self.calls = []

    def is_action_phase(self, phase):
        return phase != "final"

    def is_native_phase(self, phase):
        return phase != "final"

    def __call__(self, phase, next_phase, context):
        self.calls.append((phase, next_phase, context))
        response = context.core_completions[0]
        state = AgentStateArtifact(
            state_id=f"native-observation:{phase}:{context.sample_id}",
            state_kind="tool-result",
            content="A source-bound tool observation.",
            source_query_state_sha256=context.query_state.content_hash(),
            source_response_sha256=response.response_text_sha256,
            producer_policy_id="native-test-tool-v1",
            cited_value_ids=(),
        ).validate()
        return rc.PhaseToolStep(state=state, supply=None)


def _native_response_context(context, contact, text, *, tool_calls=None):
    from speech_aware_evidence_acquisition.rails.core_client import CoreCompletion

    reply = CoreCompletion(
        text=text, request_id=f"request:{contact.contact_id}",
        sample_id=context.sample_id, agent_contact_id=contact.contact_id,
        request_sha256="c" * 64, response_sha256="d" * 64,
        response_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        tool_calls_json=json.dumps(tool_calls).encode(),
    )
    return replace(context, core_completions=(reply,))


def _native_controller(tools=None, *, program_id="native-answer-or-tool-v1", **kwargs):
    return rc.EvidenceAgentController(
        program=rc.default_phase_program(program_id),
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        tools_for_phase=tools or _NativeToolSteps(), **kwargs,
    )


@pytest.mark.parametrize("program_id", ["native-answer-or-tool-v1", "native-answer-or-one-tool-v1"])
def test_native_answer_stops_first_contact_without_tool_or_successor(program_id):
    tools = _NativeToolSteps()
    controller = _native_controller(tools, program_id=program_id)
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    assert contact.decoding_params == {
        "tool_choice": "auto", "parallel_tool_calls": False,
    }
    response_context = _native_response_context(context, contact, "Final task answer.")
    advance = controller.advance(response_context, contact, "Final task answer.")
    assert advance.next_contact is None
    assert advance.final_response_contact_id == contact.contact_id
    assert advance.transition.action_kind == "stop"
    assert tools.calls == []


@pytest.mark.parametrize("program_id,steps", [("native-answer-or-tool-v1", 2), ("native-answer-or-one-tool-v1", 1)])
def test_native_tool_observations_reach_bounded_successors_and_final_none(program_id, steps):
    tools = _NativeToolSteps()
    controller = _native_controller(tools, program_id=program_id)
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    for index in range(steps):
        text = f"native-call-{index}"
        response_context = _native_response_context(
            context, contact, text, tool_calls=[{
                "id": f"call-{index}", "type": "function",
                "function": {"name": "observe_speech", "arguments": "{}"},
            }],
        )
        advance = controller.advance(response_context, contact, text)
        assert advance.next_contact is not None
        assert len(tools.calls) == index + 1
        assert tools.calls[-1][2].core_completions == response_context.core_completions
        assert any(s.state_kind == "tool-result" for s in advance.new_agent_states)
        context = replace(
            context, query_state=advance.next_query_state,
            agent_states=context.agent_states + advance.new_agent_states,
            prior_response_sha256s=context.prior_response_sha256s
            + (hashlib.sha256(text.encode()).hexdigest(),),
            contact_index=index + 1,
        )
        contact = advance.next_contact
    assert contact.decoding_params == {
        "tool_choice": "none", "parallel_tool_calls": False,
    }
    response_context = _native_response_context(context, contact, "Corrected task answer.")
    advance = controller.advance(response_context, contact, "Corrected task answer.")
    assert advance.next_contact is None
    assert len(tools.calls) == steps
    assert advance.final_response_contact_id == contact.contact_id


@pytest.mark.parametrize("mismatch", ["missing", "sample", "contact", "text", "query"])
def test_native_completion_must_match_current_contact_before_sealing(mismatch):
    controller = _native_controller()
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    context = _native_response_context(context, contact, "Answer.")
    if mismatch == "missing":
        context = replace(context, core_completions=())
    elif mismatch == "query":
        context = replace(context, query_state=replace(context.query_state, loop_step=1))
    else:
        reply = context.core_completions[0]
        changes = {
            "sample": {"sample_id": "other"},
            "contact": {"agent_contact_id": "other"},
            "text": {"text": "Other answer."},
        }
        context = replace(context, core_completions=(replace(reply, **changes[mismatch]),))
    with pytest.raises(rc.RailsControllersError, match="native.*(completion|binding)"):
        controller.advance(context, contact, "Answer.")
    assert controller.sealed_states == {}


def test_native_tool_request_after_final_bound_never_executes():
    tools = _NativeToolSteps()
    program = replace(
        rc.default_phase_program("native-answer-or-tool-v1"),
        phases=(rc.default_phase_program("native-answer-or-tool-v1").phases[-1],),
        max_contacts=1,
    )
    controller = rc.EvidenceAgentController(
        program=program, material_for_phase=lambda n, c: _material(n, c.sample_id),
        tools_for_phase=tools,
    )
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    context = _native_response_context(context, contact, "Call.", tool_calls=[{}])
    with pytest.raises(rc.RailsControllersError, match="final.*native tool"):
        controller.advance(context, contact, "Call.")
    assert tools.calls == []


def test_native_program_requires_dispatcher_and_owns_stop_decision():
    program = rc.default_phase_program("native-answer-or-tool-v1")
    with pytest.raises(rc.RailsControllersError, match="native.*dispatcher"):
        rc.EvidenceAgentController(
            program=program, material_for_phase=lambda n, c: _material(n, c.sample_id),
        )
    with pytest.raises(rc.RailsControllersError, match="native.*stop"):
        _native_controller(stop_policy=lambda *_: True)


@pytest.mark.parametrize(
    "text",
    [
        "<tool_call>{\"name\":\"observe_speech\"}</tool_call>",
        "  \n<tool_call>\n{\"name\":\"observe_speech\"}",
        "```json\n<tool_call>\n{\"name\":\"observe_speech\"",
        "```\n<tool_call",
    ],
)
def test_native_first_phase_rejects_textual_tool_call_frames(text):
    tools = _NativeToolSteps()
    controller = _native_controller(tools)
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    response_context = _native_response_context(
        context, contact, text, tool_calls=[]
    )

    with pytest.raises(rc.RailsControllersError, match="textual native tool"):
        controller.advance(response_context, contact, text)

    assert tools.calls == []
    assert controller.sealed_states == {}


@pytest.mark.parametrize(
    "text",
    [
        "<tool_call>{}",
        " \t```json\n<tool_call>{}",
        "\n```\n  <tool_call",
    ],
)
def test_native_final_phase_rejects_textual_tool_call_frames(text):
    tools = _NativeToolSteps()
    program = replace(
        rc.default_phase_program("native-answer-or-tool-v1"),
        phases=(rc.default_phase_program("native-answer-or-tool-v1").phases[-1],),
        max_contacts=1,
    )
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, context: _material(name, context.sample_id),
        tools_for_phase=tools,
    )
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    response_context = _native_response_context(context, contact, text)

    with pytest.raises(rc.RailsControllersError, match="textual native tool"):
        controller.advance(response_context, contact, text)

    assert tools.calls == []
    assert controller.sealed_states == {}


def test_native_final_answer_allows_tool_call_text_as_quoted_json_value():
    controller = _native_controller()
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    text = '{"answer":"The literal marker <tool_call> is part of the task value."}'
    response_context = _native_response_context(context, contact, text)

    advance = controller.advance(response_context, contact, text)

    assert advance.final_response_contact_id == contact.contact_id
    assert controller.sealed_states["decision-1"].content == text


def test_legacy_controller_preserves_textual_tool_call_answer_behavior():
    program = rc.default_phase_program("phase-direct-only-v1")
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, context: _material(name, context.sample_id),
    )
    context = _context(_query_state())
    contact = controller.initial_contact(context)
    text = "<tool_call>{\"legacy\":true}</tool_call>"

    advance = controller.advance(context, contact, text)

    assert advance.final_response_contact_id == contact.contact_id
    assert controller.sealed_states["direct"].content == text


def test_shared_phase_response_sealer_preserves_view_raw_hash_namespace_and_citations():
    raw = '{"scenario":"weather","action":"query"}'
    viewed = '{"status":"valid"}'

    artifact = rc.seal_phase_response_state(
        phase_name="draft",
        sample_id="s1",
        state_content=viewed,
        raw_response_text=raw,
        source_query_state_sha256=_SHA_A,
        producer_policy_id="phase-reviewed-repair-v1",
        state_namespace="window-2",
        cited_value_ids=("value-1", "value-2"),
    )

    assert artifact == AgentStateArtifact(
        state_id="window-2:draft:s1",
        state_kind="phase:draft",
        content=viewed,
        source_query_state_sha256=_SHA_A,
        source_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        producer_policy_id="phase-reviewed-repair-v1",
        cited_value_ids=("value-1", "value-2"),
    ).validate()
    assert artifact.source_response_sha256 != hashlib.sha256(viewed.encode()).hexdigest()
