"""E18: the Acquisition node -- ``acquire(action -> typed evidence)``.

Owner decisions 43 and 44 of 2026-09-19: every carrier instantiates all six
nodes of the agent base, and Acquisition is a component of everyday inference
(SUPPLY governs the TIMING of evidence), so it is built now rather than left
as the base-lock draft's one MISSING primitive.

What this module proves, all of it through the REAL parser, the REAL
OpenJiuwen role graph, the REAL ``rails.runner`` and the shared fake
transport. No model, no tokenizer, no encoder, no server; nothing under
``SPEECHRL_DATA_DIR`` is read or written.

1. the loader: the null arm (the key absent), the two armed forms, and the
   fail-closed refusals;
2. E15 is unchanged on an unarmed episode -- an ``ACQUIRE`` token still names
   no registered action and still seals the row -- and that episode's request
   bytes are byte-identical to the pre-E18 tree's, pinned by digest;
3. an armed episode where the Planner routes ``ACQUIRE``: the node runs kind
   (a), the Solver revision's request gains the ``acquired-evidence`` block
   and NOTHING else moves;
4. kind (b) spends exactly one contact, at the acquisition seat, inside the
   declared ceiling;
5. an ACQUIRE past the declared allowance reaches the graph's own
   ``_Exhausted`` refusal rather than acquiring off the books.

Design: ``docs/superpowers/specs/2026-09-19-e18-acquisition-node-design.md``.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import ACQUISITION_POLICIES
from speech_aware_evidence_acquisition.rails import acquisition as acq
from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import (
    ACQUIRED_EVIDENCE_BOUNDARY,
    ACQUIRED_EVIDENCE_BOUNDARY_ID,
    ACQUIRED_EVIDENCE_RENDERER,
    ACQUIRED_EVIDENCE_TEMPLATE,
    SEMANTIC_CLASSES,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    ACQUISITION_STAGE,
)

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The four phases every pre-E18 episode has, plus the acquisition seat.
PHASES = ("perception", "solver", "reviewer", "planner")
ACQUISITION_PHASE = "acquisition"
PROGRAM_ID = "native-role-runner-proof-v1"


# ---------------------------------------------------------------------------
# 1. The loader.
# ---------------------------------------------------------------------------


def _loader_program(*, ceiling, phases=PHASES):
    return PhaseProgram(
        program_id="phase-native-role-test",
        phases=tuple(
            PhaseSpec(name, name, "none", None, False) for name in phases
        ),
        max_contacts=ceiling,
        stop_rule="native-role-episode",
    ).validate()


def _loader_values(*, max_revisions=0):
    return {"native_episode": {
        "schema": "saea-native-episode-config-v1",
        "episode_id": "native-role-test",
        "max_revisions": max_revisions,
        "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
        "roles": {
            name: {"phase_id": name, "max_iterations": 1} for name in PHASES
        },
    }}


def _armed_values(*, kind="knowledge-requery", policy=None, iterations=0,
                  budget=None, kinds=None, max_revisions=1):
    values = _loader_values(max_revisions=max_revisions)
    values["native_episode"]["roles"][ACQUISITION_PHASE] = {
        "phase_id": ACQUISITION_PHASE,
        "max_iterations": iterations,
        "kinds": [kind] if kinds is None else kinds,
    }
    values["native_episode"]["acquisition"] = {
        "policy": policy or acq.KNOWLEDGE_REQUERY_POLICY_ID,
        "budget": budget or {"max_acquisitions_per_row": 1, "contact_budget": 0},
    }
    return values


def test_the_null_arm_is_the_absent_key_and_composes_the_pre_e18_episode():
    parsed = load_native_episode_config(_loader_values(), _loader_program(ceiling=4))

    assert parsed.acquisition_enabled is False
    assert parsed.acquisition_role is None
    assert parsed.acquisition_policy_id is None
    assert parsed.acquisition_budget is None
    assert parsed.max_acquisitions_per_row == 0
    assert parsed.acquisition_contact_budget == 0
    # The ceiling is exactly the pre-E18 formula: Perception once plus one
    # round of Solver + Reviewer + Planner.
    assert parsed.max_contacts == 4


def test_the_model_free_arm_adds_a_node_and_no_contact_to_the_ceiling():
    parsed = load_native_episode_config(
        _armed_values(),
        _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
    )

    assert parsed.acquisition_enabled is True
    assert parsed.acquisition_policy_id == acq.KNOWLEDGE_REQUERY_POLICY_ID
    assert parsed.acquisition_role.phase_id == ACQUISITION_PHASE
    assert parsed.acquisition_role.max_iterations == 0
    assert parsed.acquisition_role.acquisition_kinds == ("knowledge-requery",)
    assert parsed.acquisition_budget == {
        "max_acquisitions_per_row": 1, "contact_budget": 0,
    }
    # 1 Perception + 2 rounds x 3 roles + 1 acquisition x 0 contacts.
    assert parsed.max_contacts == 7


def test_the_contact_spending_arm_adds_exactly_its_own_contacts():
    parsed = load_native_episode_config(
        _armed_values(
            kind="speech-reobserve",
            policy=acq.SPEECH_REOBSERVE_POLICY_ID,
            iterations=1,
            budget={"max_acquisitions_per_row": 1, "contact_budget": 1},
        ),
        _loader_program(ceiling=8, phases=(*PHASES, ACQUISITION_PHASE)),
    )

    assert parsed.max_contacts == 8
    assert parsed.acquisition_contact_budget == 1
    # And the ceiling is CHECKED, not advisory.
    with pytest.raises(ValueError, match="ceiling"):
        load_native_episode_config(
            _armed_values(
                kind="speech-reobserve",
                policy=acq.SPEECH_REOBSERVE_POLICY_ID,
                iterations=1,
                budget={"max_acquisitions_per_row": 1, "contact_budget": 1},
            ),
            _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda v: v["native_episode"].pop("acquisition"), "one module"),
        (
            lambda v: v["native_episode"]["roles"].pop(ACQUISITION_PHASE),
            "one module",
        ),
        (
            lambda v: v["native_episode"]["roles"][ACQUISITION_PHASE].update(
                kinds=["telepathy"]
            ),
            "unknown acquisition kinds",
        ),
        (
            lambda v: v["native_episode"]["acquisition"].update(
                policy="saea-acquire-nothing-v9"
            ),
            "acquisition.policy is invalid",
        ),
        (
            lambda v: v["native_episode"]["roles"][ACQUISITION_PHASE].update(
                kinds=["speech-reobserve"]
            ),
            "roles.acquisition.kinds does not admit",
        ),
        (
            lambda v: v["native_episode"]["acquisition"]["budget"].update(
                max_acquisitions_per_row=4
            ),
            "bounded by\nmax_revisions|bounded by max_revisions",
        ),
        (
            lambda v: v["native_episode"]["acquisition"]["budget"].update(
                contact_budget=2
            ),
            "contact_budget must equal",
        ),
        (
            lambda v: v["native_episode"]["roles"][ACQUISITION_PHASE].update(
                max_iterations=1
            ),
            "max_iterations must equal",
        ),
        (
            lambda v: v["native_episode"]["roles"][ACQUISITION_PHASE].update(
                tool_names=["analyze"]
            ),
            "exactly phase_id, max_iterations",
        ),
    ],
)
def test_the_loader_fails_closed_on_every_half_armed_shape(mutate, match):
    values = _armed_values()
    mutate(values)
    with pytest.raises(ValueError, match=match):
        load_native_episode_config(
            values,
            _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
        )


def test_the_acquisition_seat_may_not_carry_analytical_tools():
    values = _armed_values()
    values["phase_tools"] = {
        ACQUISITION_PHASE: {
            "mode": "native-tools",
            "source_authority_role": ACQUISITION_PHASE,
            "allowed_tools": ["analyze"],
        }
    }
    with pytest.raises(ValueError, match="may not expose analytical tools"):
        load_native_episode_config(
            values,
            _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
        )


def test_acquisition_and_candidate_refresh_are_not_composed_silently():
    values = _armed_values()
    values["native_episode"]["candidate_refresh"] = {
        "action": "REFRESH", "max_refreshes": 1,
    }
    with pytest.raises(ValueError, match="declare one of them"):
        load_native_episode_config(
            values,
            _loader_program(ceiling=8, phases=(*PHASES, ACQUISITION_PHASE)),
        )


# ---------------------------------------------------------------------------
# 2. The primitive: one record shape, three kinds, the closed boundary.
# ---------------------------------------------------------------------------


def test_the_three_kinds_are_registered_with_their_own_cost():
    assert ACQUISITION_POLICIES.names() == [
        acq.KNOWLEDGE_REQUERY_POLICY_ID,
        acq.SPEECH_REOBSERVE_POLICY_ID,
        acq.TOOL_ACQUIRE_POLICY_ID,
    ]
    costs = {
        policy.kind: (policy.contacts_per_acquisition, policy.cost_unit)
        for policy in (
            acq.resolve_acquisition_policy(name)
            for name in ACQUISITION_POLICIES.names()
        )
    }
    assert costs == {
        "knowledge-requery": (0, "supply-calls"),
        "speech-reobserve": (1, "model-contacts"),
        "tool-acquire": (0, "registry-lookups"),
    }


def test_the_new_boundary_is_declared_beside_the_twelve():
    assert "acquired-evidence" in SEMANTIC_CLASSES
    assert ACQUIRED_EVIDENCE_BOUNDARY == ("solver", "acquired-evidence")
    assert ACQUIRED_EVIDENCE_BOUNDARY_ID == "B-ACQ-SOL"
    template = acq.acquired_evidence_template(REPO_ROOT)
    assert template.renderer == ACQUIRED_EVIDENCE_RENDERER
    assert template.template_id == ACQUIRED_EVIDENCE_TEMPLATE


def test_the_block_renders_items_and_its_own_closed_empty_phrase():
    template = acq.acquired_evidence_template(REPO_ROOT)
    rendered = acq.render_evidence_block(
        template,
        kind="knowledge-requery",
        policy_id=acq.KNOWLEDGE_REQUERY_POLICY_ID,
        items=(acq.AcquiredItem("kb:v1", "intent-boundaries", "alarm_set"),),
    )
    assert rendered.startswith("ACQUIRED EVIDENCE (1 item(s)")
    assert "[kb:v1 from intent-boundaries] alarm_set" in rendered

    empty = acq.render_evidence_block(
        template,
        kind="knowledge-requery",
        policy_id=acq.KNOWLEDGE_REQUERY_POLICY_ID,
        items=(),
    )
    assert "nothing new was acquired for this row" in empty


def test_the_tool_kind_is_registered_and_fails_closed_unarmed():
    request = acq.AcquisitionRequest(
        policy_id=acq.TOOL_ACQUIRE_POLICY_ID,
        kind="tool-acquire",
        sample_id="s1",
        visit_index=0,
        revision_count=0,
        planner_route_index=0,
        planner_action="ACQUIRE",
        state_filters=(),
        supplied_value_ids=(),
        budget=acq.AcquisitionBudget(1, 0),
        contacts_used=0,
    )
    policy = acq.resolve_acquisition_policy(acq.TOOL_ACQUIRE_POLICY_ID)
    template = acq.acquired_evidence_template(REPO_ROOT)
    with pytest.raises(acq.AcquisitionError, match="not armed on this"):
        _run(policy(request, template=template))


def test_the_state_restriction_is_bounded_and_deterministic():
    state = {
        "review": "The time slot is missing a filler; the place_name looks wrong.",
        "plan": "ACQUIRE",
    }
    first = acq.derive_state_filters(state)
    assert first == acq.derive_state_filters(state)
    assert len(first) <= acq.MAX_STATE_FILTERS
    assert "time" in first and "place_name" in first
    # Digits, punctuation and casing never survive into a restriction token.
    assert all(token.islower() and token.replace("_", "").isalpha() for token in first)


def _run(awaitable):
    import asyncio

    return asyncio.run(_await(awaitable))


async def _await(awaitable):
    return await awaitable


# ---------------------------------------------------------------------------
# 3-5. The live graph.
# ---------------------------------------------------------------------------


def _episode_program(*, max_contacts, with_acquisition):
    names = (*PHASES, ACQUISITION_PHASE) if with_acquisition else PHASES
    return PhaseProgram(
        program_id=PROGRAM_ID,
        phases=tuple(
            PhaseSpec(
                name=phase,
                purpose=f"Run the {phase} role.",
                knowledge="none",
                response_format_id=None,
                barrier=False,
            )
            for phase in names
        ),
        max_contacts=max_contacts,
        stop_rule="native-role-episode",
    ).validate()


def _episode_config(*, max_revisions, max_contacts, kind, iterations, contact_budget):
    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": PROGRAM_ID,
            "max_revisions": max_revisions,
            "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
            "roles": {
                name: {"phase_id": name, "max_iterations": 1} for name in PHASES
            },
        }
    }
    if kind is not None:
        values["native_episode"]["roles"][ACQUISITION_PHASE] = {
            "phase_id": ACQUISITION_PHASE,
            "max_iterations": iterations,
            "kinds": [kind],
        }
        values["native_episode"]["acquisition"] = {
            "policy": (
                acq.KNOWLEDGE_REQUERY_POLICY_ID
                if kind == "knowledge-requery"
                else acq.SPEECH_REOBSERVE_POLICY_ID
            ),
            "budget": {
                "max_acquisitions_per_row": 1, "contact_budget": contact_budget,
            },
        }
    program = _episode_program(
        max_contacts=max_contacts, with_acquisition=kind is not None,
    )
    return load_native_episode_config(values, program), program


def _armed_harness(
    tmp_path,
    *,
    planner_actions,
    kind="knowledge-requery",
    iterations=0,
    contact_budget=0,
    max_contacts=7,
    max_revisions=1,
    requery_items=(("kb:value-7", "intent-boundaries", "alarm_set: set an alarm"),),
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=max_revisions,
        max_contacts=max_contacts,
        planner_actions=planner_actions,
        exhaustion_policy="deliver-latest-solver",
    )
    config, program = _episode_config(
        max_revisions=max_revisions,
        max_contacts=max_contacts,
        kind=kind,
        iterations=iterations,
        contact_budget=contact_budget,
    )
    harness.config = config
    harness.program = program
    harness.repo_root = REPO_ROOT
    calls = []

    def requery(*, phase_id, filters, exclude_value_ids, scope, context):
        calls.append({
            "phase_id": phase_id,
            "filters": tuple(filters),
            "excluded": frozenset(exclude_value_ids),
            "scope": dict(scope),
        })
        return [
            acq.AcquiredItem(value_id, source_id, content)
            for value_id, source_id, content in requery_items
        ]

    harness.acquisition_requery = requery
    harness.requery_calls = calls
    return harness


#: The rendered marker of one agent state produced by the acquisition seat.
ACQUISITION_STATE_MARKER = f"kind=phase:{ACQUISITION_PHASE}]"


def _acquisition_parts(rendered):
    """Every rendered text part carrying an ``acquired-evidence`` state."""

    return [
        part for part in rendered["messages"][-1]["content"]
        if part.get("type") == "text"
        and ACQUISITION_STATE_MARKER in part.get("text", "")
    ]


def _state_content(part):
    """The state's own content, without the renderer's fixed state prefix."""

    return part["text"].split("] ", 1)[1]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_unarmed_acquire_is_still_the_e15_retained_row(tmp_path):
    """E15 is untouched: with no acquisition node an ``ACQUIRE`` token names
    no registered action, so the row is SEALED through the E8c path -- draft
    delivered unchanged, no further role contacted, revision unspent."""

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=7,
        planner_actions=("ACQUIRE",),
    )
    try:
        summary = harness.run()
    finally:
        harness.close()

    [result] = summary.results
    assert result.final_response_text == "solver-answer:s1:visit:1"
    receipt = result.native_episode_receipt
    assert "acquisition" not in receipt
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception", "solver", "review", "planner",
    ]
    route = receipt["planner_routes"][0]
    assert route["action"] == "ACQUIRE"
    assert route["legal"] is False
    assert receipt["planner_action_illegal"] == {
        "schema": "saea-native-planner-action-illegal-v1",
        "count": 1,
        "action_sha256": [hashlib.sha256(b"ACQUIRE").hexdigest()],
    }


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_unarmed_episode_renders_the_pre_e18_request_bytes(tmp_path):
    """The OFF arm's falsifier, pinned by digest exactly as E17 pins its own.

    These four digests are the rendered requests of a four-contact unarmed
    row on this fixture. E18 touches the request path in three places (the
    Planner's advertised action set, the node-context phase map and the
    settle's added states); every one of them is reached only by an ARMED
    episode, and these digests are what makes that a checked statement rather
    than a claim.
    """

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    try:
        harness.run()
    finally:
        harness.close()

    digests = {
        phase: hashlib.sha256(
            json.dumps(
                harness.prepared[("s1", phase, 1, 1)]["rendered"], sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        for phase in PHASES
    }
    assert digests == ANCHOR_REQUEST_DIGESTS


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_armed_acquire_runs_the_node_and_supplies_the_solver(tmp_path):
    harness = _armed_harness(tmp_path, planner_actions=("ACQUIRE", "ACCEPT"))
    try:
        summary = harness.run()
    finally:
        harness.close()

    [result] = summary.results
    assert result.final_response_text == "solver-answer:s1:visit:2"
    receipt = result.native_episode_receipt
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception", "solver", "review", "planner",
        ACQUISITION_STAGE,
        "solver", "review", "planner",
    ]
    assert receipt["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": "ACQUIRE"},
        {"role_visit_index": 7, "revision_count": 1, "action": "ACCEPT"},
    ]
    # ACQUIRE is a LEGAL route on an armed episode, so it no longer counts
    # as an illegal Planner output -- the one E15 disposition E18 changes.
    assert "planner_action_illegal" not in receipt
    assert all(route.get("legal") is not False for route in receipt["planner_routes"])

    # The node's own visit carries the acquisition receipt and -- being a
    # model-free kind -- no execution receipt at all.
    visit = receipt["role_visits"][4]
    assert visit["role_id"] == ACQUISITION_PHASE
    assert "execution_receipt" not in visit
    record = visit["acquisition_receipt"]
    assert record["kind"] == "knowledge-requery"
    assert record["policy_id"] == acq.KNOWLEDGE_REQUERY_POLICY_ID
    assert record["contacts_used"] == 0
    assert record["cost_unit"] == "supply-calls"
    assert record["provenance_ids"] == ["kb:value-7"]
    assert record["planner_action"] == "ACQUIRE"
    assert len(record["inputs_sha256"]) == 64
    assert len(record["evidence_sha256"]) == 64

    block = receipt["acquisition"]
    assert block["node_phase_id"] == ACQUISITION_PHASE
    assert block["kind"] == "knowledge-requery"
    assert block["contacts_used"] == 0
    assert block["budget"] == {"max_acquisitions_per_row": 1, "contact_budget": 0}
    assert block["acquisitions"] == [record]

    # The row spent exactly the four-role contacts: an acquisition of this
    # kind costs none.
    assert len(result.contacts) == 7

    # The Solver's revision saw the typed block, and the block's digest is
    # the one the receipt bound.
    rendered = harness.prepared[("s1", "solver", 2, 1)]["rendered"]
    [part] = _acquisition_parts(rendered)
    content = _state_content(part)
    assert content.startswith("ACQUIRED EVIDENCE (1 item(s)")
    assert "[kb:value-7 from intent-boundaries] alarm_set: set an alarm" in content
    assert hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest() == record["evidence_sha256"]

    # The re-query was asked for the SOLVER's phase, restricted by state and
    # handed the dedupe set -- never a free-text query of its own.
    [call] = harness.requery_calls
    assert call["phase_id"] == "solver"
    assert call["scope"] == {
        "phase_id": ACQUISITION_PHASE, "kinds": ["knowledge-requery"],
    }
    assert "review" in call["filters"] or call["filters"]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_acquired_block_is_the_only_byte_the_acquisition_moves(tmp_path):
    """The one-factor falsifier: two ACQUIRE rows whose acquisitions differ
    only in what they brought back render second-Solver requests that differ
    in exactly one agent state -- the ``acquired-evidence`` block."""

    full = _armed_harness(
        tmp_path / "full", planner_actions=("ACQUIRE", "ACCEPT"),
    )
    try:
        full.run()
    finally:
        full.close()
    empty = _armed_harness(
        tmp_path / "empty", planner_actions=("ACQUIRE", "ACCEPT"), requery_items=(),
    )
    try:
        empty.run()
    finally:
        empty.close()

    full_request = copy.deepcopy(full.prepared[("s1", "solver", 2, 1)]["rendered"])
    empty_request = copy.deepcopy(empty.prepared[("s1", "solver", 2, 1)]["rendered"])
    assert full_request != empty_request

    [full_part] = _acquisition_parts(full_request)
    [empty_part] = _acquisition_parts(empty_request)
    assert "kb:value-7" in _state_content(full_part)
    assert "nothing new was acquired for this row" in _state_content(empty_part)

    # Everything that is not that one block's content is byte-identical:
    # same system message, same speech part, same evidence blocks, same other
    # agent states with the same ids, same role query and limits, same
    # decoding params and the same slot.
    for request in (full_request, empty_request):
        for part in _acquisition_parts(request):
            prefix = part["text"].split("] ", 1)[0]
            part["text"] = f"{prefix}] <acquired-evidence block>"
    assert full_request == empty_request


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_reobservation_acquisition_costs_exactly_one_perception_contact(tmp_path):
    harness = _armed_harness(
        tmp_path,
        planner_actions=("ACQUIRE", "ACCEPT"),
        kind="speech-reobserve",
        iterations=1,
        contact_budget=1,
        max_contacts=8,
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    [result] = summary.results
    receipt = result.native_episode_receipt
    visit = receipt["role_visits"][4]
    record = visit["acquisition_receipt"]
    assert record["kind"] == "speech-reobserve"
    assert record["contacts_used"] == 1
    assert record["cost_unit"] == "model-contacts"
    assert receipt["acquisition"]["contacts_used"] == 1

    # ONE extra contact, at the acquisition seat, inside the declared
    # ceiling -- the eighth of an eight-contact row.
    assert len(result.contacts) == 8
    assert close_summary["request_count"] == 8
    assert ("s1", ACQUISITION_PHASE, 1, 1) in harness.prepared
    # Its own contact is bound to the visit, through the same normalisation
    # every role visit's receipt takes.
    final = visit["execution_receipt"]["final_contact"]
    assert final == harness.traced_contact(final["agent_contact_id"])

    # The state the next Solver reads is the TYPED block, not the
    # re-observation's raw text -- and the block quotes the observation the
    # contact actually returned.
    rendered = harness.prepared[("s1", "solver", 2, 1)]["rendered"]
    [part] = _acquisition_parts(rendered)
    content = _state_content(part)
    assert content.startswith("ACQUIRED EVIDENCE (1 item(s)")
    assert "acquisition-analysis:s1:visit:1" in content
    assert hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest() == record["evidence_sha256"]
    # Its provenance is that contact, not a value id.
    assert record["provenance_ids"] == [final["agent_contact_id"]]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_acquire_past_the_declared_allowance_is_refused_by_the_graph(tmp_path):
    """Defence in depth: the advertised action set stops offering ACQUIRE the
    moment the allowance is spent, so reaching the second ACQUIRE means a
    Planner emitted a token past its own budget -- and the graph refuses it
    rather than acquiring off the books."""

    harness = _armed_harness(
        tmp_path,
        planner_actions=("ACQUIRE", "ACQUIRE"),
        max_revisions=2,
        max_contacts=10,
    )
    try:
        with pytest.raises(Exception, match="acquisition budget is exhausted"):
            harness.run()
    finally:
        harness.close()


#: The pinned rendered-request digests of a four-contact unarmed row on the
#: ``_ActualEpisodeHarness`` fixture. Captured at E18 with zero model
#: contacts; any change to them is a change to the OFF arm's request bytes.
ANCHOR_REQUEST_DIGESTS = {
    "perception": "96edc0bed1ab183fe7604f29e10cd93482bcdb89b52cf0bd10ff368351322d7d",
    "solver": "46d3cd75ece3271d4d7003be56425f8a4fe064e05fad4e8827ac08fcea55cfd2",
    "reviewer": "9d78ad22810ff8c8cf5a0e1865b1ee791cda8e46a17a7a8748c044b31bc1fad8",
    "planner": "55886d6df29defe1d64f5038351f6b2bc0bc62bb677c547ad240901291782949",
}
