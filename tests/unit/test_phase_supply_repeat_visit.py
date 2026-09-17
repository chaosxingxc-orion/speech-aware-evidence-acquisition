"""E3c: a RE-ENTERED phase acquires only what its trajectory does not hold.

Cell B1 (SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2) aborted on
2026-09-17 at the first row whose Planner routed REVISE: the second Solver
visit re-ran the prepared phase supply, the decision selected the same twenty
``train-exemplars`` values, and ``EvidenceAgentController._acquired_ids``
refused them as "already visible in this trajectory". The four-row smoke never
saw it because all four rows routed ACCEPT.

``rails.controllers.restrict_repeat_visit_supply`` is the fix: on a repeat
visit of one phase the decision is restricted to the values and facets the
trajectory does not already hold (what ``rails.kb_policy``'s own fuser does
against ``QueryState.retrieved_value_ids`` before it ever builds a decision),
and a revisit that acquires nothing emits no acquire transition at all -- the
supplied values still reach the request because every post-Perception request
renders from the ACCUMULATED ``QueryState``.

Everything here is model-free: the episodes run the real OpenJiuwen role graph
and the real runner through the shared fake transport, and the supply callable
is a synthetic stand-in for a prepared ``rails.phase_supply`` binding (same
decision on every call, rebound to the caller's current ``QueryState``).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.controllers import (
    PhaseProgram,
    PhaseSpec,
    restrict_repeat_visit_supply,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    FusionDecision,
    KeyFacet,
    KnowledgeSnapshot,
    RankedFacet,
    RankResult,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeRunBinding,
)
from speech_aware_evidence_acquisition.rails.runner import run_speech_native_agent_loop
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import PHASES, _ActualEpisodeHarness
from test_rails_runner import _controller_registry

_SHA_B = "b" * 64
#: Mirrors cell B1's ``train-exemplars`` store: k = 20, twenty in and twenty
#: out on every row.
EXEMPLAR_COUNT = 20
EXEMPLAR_VALUE_IDS = tuple(
    f"train-exemplars::value:exemplar-{index:02d}" for index in range(EXEMPLAR_COUNT)
)
EXEMPLAR_FACET_IDS = ("facet:content:a", "facet:content:b")

# ---------------------------------------------------------------------------
# Byte-identity pins.
#
# Captured from the PRE-CHANGE tree (master 93bbb3ad, before
# restrict_repeat_visit_supply existed) with the production render path
# (``LlamaServerTransport.render_request``, exactly the bytes
# ``_ActualEpisodeHarness.request_gate`` admits) and the production transition
# objects (``AgentStepTransition.content_hash``). They are what "no request
# byte of any first visit may change" means as a test: if any of these move,
# the change stopped being a repeat-visit-only change.
# ---------------------------------------------------------------------------

#: Supplied-Solver episode, Planner ACCEPT -- every phase visited exactly once.
SUPPLIED_FIRST_VISIT_REQUEST_SHA256 = {
    "perception/1": "a097af24516175ad10fd5b5845cdb64dc052ef1a00d8feb5826a7bc62e02e279",
    "solver/1": "febb3f0fc9a0ccc803fb14305ead0eea7e3d23f27f6af965cdc78a01745fa6a5",
    "reviewer/1": "d8bd43280a157615346e5bf49f73e9ec2b0424ee30d816514f25b1a83ef11cd4",
    "planner/1": "a0f7f955551b26210840541e70a77f8930a7514009663be1e696e99dedbcf822",
}
SUPPLIED_FIRST_VISIT_TRANSITION_SHA256 = (
    "aebea8bc07cb6ea6bc0c2f9d6b0b864edefd3f20c546ee9d05b0f6f5a4019346",
    "16177d906287bb37935f2dd09ae42c9f15c81b010e85486d402c41c4459947ee",
    "11598f8f9ff554fc2264172cb49e7074851e45c555de209752e4f48d5584d7ef",
    "2f622f0f0126dfe8ef577f5eed9aa1dfc24e52567247103fe7827527fb6019f8",
    "97513b221182e822b5cb7a1a9acbee7ecd1ce11e50f16862a3046df8005b26b6",
)

#: The anchor shape: no phase supply at all, Planner REVISE then ACCEPT.
ANCHOR_REQUEST_SHA256 = {
    "perception/1": "a097af24516175ad10fd5b5845cdb64dc052ef1a00d8feb5826a7bc62e02e279",
    "solver/1": "8db2283fde1d99722c0d3ed52d2d3c3348d09b2d183238013e0d04ac9fb1fd35",
    "reviewer/1": "f5afebe7fae388ff8469afc4bc7ce21d3329db78732c122fc4da978d4777fc54",
    "planner/1": "7bdab312803b2fdf0a350b6ef03a78073c049c8c982de04fff59b93a860d900b",
    "solver/2": "712e443b4b094b82b867a51e82551f86dd4bcd392f57916627a6a372728682cf",
    "reviewer/2": "e5818e4fc0b182d2d7ae61414d6387f8a2d38ee0d5215198c53a11822312485a",
    "planner/2": "25b63ade66b6c2b700f1f2cb5b7316a7df904642b0e2e5da435e73569f9346a3",
}
ANCHOR_TRANSITION_SHA256 = (
    "95fd2ffeee410f56174294f7c8916edcaf11668803092b8db22eefecacfc1c0a",
    "fc354a63073bc6f93056ce1c1741c580b86d446098d7162278bc58330a3bff97",
    "799520151683ed26eedf1d9f93713c70859cc627e18f393c44c485c9b8c5f74d",
    "30b006de1204168e84a23b19b4611858b2bd3dfed869e4e7aa1191ca2cb103ff",
    "e7e3a32b7a69888108e60899efac79d17fd94d060a5d9c20430791d9259c5c90",
    "22b6da076dd6084dc3b55332bac0ccf6cebbf31d244f8b3a5de6e17836f354aa",
    "f7b619f73dc016abcf06ee29f5e499c308edd25b90b45a6c04e690407f2092e8",
    "99ae905dd5ecb1caf7db0561aa08ee8985288581a015570b08b3721482884206",
)


def _exemplar_snapshot() -> KnowledgeSnapshot:
    """A TRAIN snapshot carrying twenty exemplar values over two facets."""

    return KnowledgeSnapshot(
        snapshot_id="fake-train-exemplars-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:t1",),
        builder_policy_id="coverage-builder-v1",
        facets=tuple(
            KeyFacet(
                facet_id=facet_id,
                dimension="content",
                representation_kind="text",
                representation=f"Exemplar content group {facet_id}.",
                source_sample_ids=("train:t1",),
            )
            for facet_id in EXEMPLAR_FACET_IDS
        ),
        values=tuple(
            ValueBundle(
                value_id=value_id,
                content=f"exemplar utterance {index:02d} | alarm_set | type=filler",
                associated_facet_ids=(EXEMPLAR_FACET_IDS[index % 2],),
                source_sample_ids=("train:t1",),
                provenance_refs=("train:t1",),
            )
            for index, value_id in enumerate(EXEMPLAR_VALUE_IDS)
        ),
    ).validate()


def _prepared_supply(snapshot: KnowledgeSnapshot, *, phase: str = "solver"):
    """A stand-in for a prepared ``rails.phase_supply`` binding.

    Like the real one it is a pure function of (phase, sample): the SAME
    twenty values come back on every call, re-bound to the caller's current
    ``QueryState`` (``rails.phase_supply.build_supply_for_phase`` builds a
    fresh provider and a fresh decision per call, so its hashes always name
    the state of the contact that just completed).
    """

    snapshot_sha256 = snapshot.content_hash()
    calls: list[tuple[str, int]] = []

    def supply_for_phase(phase_name, context):
        if phase_name != phase:
            return None
        calls.append((phase_name, context.query_state.loop_step))
        rank_result = RankResult(
            snapshot_sha256=snapshot_sha256,
            query_state_sha256=context.query_state.content_hash(),
            ranking_policy_id="saea-rank-wcos-prior-agree-v1",
            candidates=tuple(
                RankedFacet(facet_id=facet_id, score=1.0 - index / 10.0)
                for index, facet_id in enumerate(EXEMPLAR_FACET_IDS)
            ),
        ).validate()
        fusion_decision = FusionDecision(
            snapshot_sha256=snapshot_sha256,
            query_state_sha256=context.query_state.content_hash(),
            rank_result_sha256=rank_result.content_hash(),
            fusion_policy_id="saea-fuse-supplyfilter-v1",
            supporting_facet_ids=EXEMPLAR_FACET_IDS,
            selected_value_ids=EXEMPLAR_VALUE_IDS,
        ).validate()
        return rc.PhaseSupply(
            rank_result=rank_result,
            fusion_decision=fusion_decision,
            action_target_ref="kb-facet-v1:saea-rank-wcos-prior-agree-v1:k=20",
        ).validate()

    supply_for_phase.calls = calls
    return supply_for_phase


def _supplied_program(*, max_contacts: int, supplied_phase: str = "solver") -> PhaseProgram:
    """``test_native_episode_runner._program`` with one supplied phase.

    The program id is unchanged so the harness's own controller registry and
    contact identities stay exactly what every other episode proof uses.
    """

    return PhaseProgram(
        program_id="native-role-runner-proof-v1",
        phases=tuple(
            PhaseSpec(
                name=phase,
                purpose=f"Run the {phase} role.",
                knowledge="supplied" if phase == supplied_phase else "none",
                response_format_id=None,
                barrier=False,
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
        stop_rule="native-role-episode",
    ).validate()


def _run_episode(tmp_path, *, planner_actions, supply=None, snapshot=None):
    """One real native episode; returns (harness, summary).

    Identical to ``_ActualEpisodeHarness.run`` except that the binding may
    carry a ``supply_for_phase`` -- the seam cell B1 uses.
    """

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=7,
        planner_actions=planner_actions,
    )
    if snapshot is None:
        snapshot = _exemplar_snapshot()
    if supply is not None:
        harness.program = _supplied_program(max_contacts=7)
    binding = NativeEpisodeRunBinding(
        config=harness.config,
        program=harness.program,
        material_for_phase=harness.material_for_phase,
        render_request=harness.transport.render_request,
        request_gate=harness.request_gate,
        tools_for_phase=harness.tools_for_phase,
        supply_for_phase=supply,
    )
    try:
        summary = run_speech_native_agent_loop(
            data_root=harness.world.data_root,
            plan=harness.plan,
            adapter=harness.adapter,
            core_client=harness.client,
            split_id="all",
            knowledge_snapshot=snapshot,
            speech_packet_bindings=harness.speech_bindings,
            controller_policy_id=harness.program.program_id,
            controller_registry=_controller_registry(
                harness.program.program_id, lambda _sample_id: object()
            ),
            max_contacts=harness.config.max_contacts,
            slot_count=1,
            queue_depth=1,
            trace_sink=harness.trace,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params={"temperature": 0, "max_tokens": 64},
            native_episode_binding=binding,
        )
    finally:
        harness.close()
    return harness, summary


def _request_digests(harness):
    """sha256 of the canonical bytes of every request the gate admitted."""

    return {
        f"{phase}/{visit}": hashlib.sha256(
            json.dumps(
                prepared["rendered"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        for (_sample, phase, visit, _turn), prepared in harness.prepared.items()
    }


def _transition_digests(summary):
    return tuple(
        transition.content_hash() for transition in summary.results[0].transitions
    )


def _rendered_texts(harness, key):
    """Every text part of one admitted request, in wire order.

    The transport flattens the runner's typed knowledge blocks into
    ``"[evidence <value_id>] <content>"`` (and a key block into its own text
    part), so this is exactly where a duplicated or a newly promoted block
    would show.
    """

    content = harness.prepared[key]["rendered"]["messages"][1]["content"]
    return [
        part["text"]
        for part in content
        if isinstance(part, dict) and part.get("type") == "text"
    ]


def _expected_value_texts(snapshot):
    return [f"[evidence {value.value_id}] {value.content}" for value in snapshot.values]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_revise_route_re_enters_the_supplied_solver_without_reacquiring(tmp_path):
    """(a) The B1 abort, fixed, through the real role graph.

    The Planner routes REVISE, the Solver is entered a second time, the
    prepared supply offers the SAME twenty values -- and the trajectory
    completes: the revisit emits no acquire transition, the twenty values
    still reach the second Solver request exactly once each through the
    accumulated ``QueryState``, and no facet is promoted into a key block
    that the first visit never carried.
    """

    snapshot = _exemplar_snapshot()
    supply = _prepared_supply(snapshot)
    harness, summary = _run_episode(
        tmp_path, planner_actions=("REVISE", "ACCEPT"), supply=supply, snapshot=snapshot,
    )
    result = summary.results[0]

    # The episode ran to an explicitly accepted second Solver answer.
    assert result.final_response_text == "solver-answer:s1:visit:2"
    assert [visit["stage"] for visit in result.native_episode_receipt["role_visits"]] == [
        "perception", "solver", "review", "planner", "solver", "review", "planner",
    ]
    assert [
        route["action"] for route in result.native_episode_receipt["planner_routes"]
    ] == ["REVISE", "ACCEPT"]

    # The supply was consulted on BOTH Solver entries; only the first acquired.
    assert [phase for phase, _loop_step in supply.calls] == ["solver", "solver"]
    acquires = [
        transition
        for transition in result.transitions
        if transition.action_kind == "acquire"
    ]
    assert len(acquires) == 1
    assert acquires[0].new_value_ids == EXEMPLAR_VALUE_IDS
    assert acquires[0].new_facet_ids == ()
    # Perception acquires once; the Planner wave that routes back into the
    # Solver is an ordinary organize step, not a second acquire.
    kinds = [transition.action_kind for transition in result.transitions]
    assert kinds[0] == "acquire"
    assert kinds[-1] == "stop"
    assert set(kinds[1:-1]) == {"organize"}
    assert all(
        transition.new_value_ids == () for transition in result.transitions[1:]
    )
    assert result.final_query_state.retrieved_value_ids == EXEMPLAR_VALUE_IDS

    # The twenty values reach the SECOND Solver request exactly once each,
    # in the same order and with no key block the first visit never carried.
    expected = _expected_value_texts(snapshot)
    assert len(expected) == EXEMPLAR_COUNT
    first_texts = _rendered_texts(harness, ("s1", "solver", 1, 1))
    second_texts = _rendered_texts(harness, ("s1", "solver", 2, 1))
    assert [text for text in first_texts if text.startswith("[evidence ")] == expected
    assert [text for text in second_texts if text.startswith("[evidence ")] == expected
    assert not [text for text in second_texts if text.startswith("[key ")]
    assert not [text for text in first_texts if text.startswith("[key ")]
    for facet in snapshot.facets:
        assert facet.representation not in "\n".join(second_texts)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_first_visit_supplied_request_bytes_and_transitions_are_unchanged(tmp_path):
    """(b) Nothing a FIRST visit sends or seals moved.

    The supplied-Solver episode whose Planner ACCEPTs visits every phase
    exactly once, so it is the whole first-visit surface of cell B1's shape.
    Its request bytes and its transition identities are pinned to digests
    captured from the pre-change tree.
    """

    snapshot = _exemplar_snapshot()
    harness, summary = _run_episode(
        tmp_path,
        planner_actions=("ACCEPT",),
        supply=_prepared_supply(snapshot),
        snapshot=snapshot,
    )
    assert _request_digests(harness) == SUPPLIED_FIRST_VISIT_REQUEST_SHA256
    assert _transition_digests(summary) == SUPPLIED_FIRST_VISIT_TRANSITION_SHA256


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_anchor_without_phase_supply_renders_identically(tmp_path):
    """(c) The anchor configuration -- no phase supply anywhere -- is untouched.

    Same REVISE-then-ACCEPT route as the failing cell, but with no supply
    binding: every request byte and every transition identity is pinned to
    the pre-change tree, so the fix cannot have moved the base the whole
    program compares against.
    """

    harness, summary = _run_episode(
        tmp_path, planner_actions=("REVISE", "ACCEPT"), supply=None,
    )
    assert _request_digests(harness) == ANCHOR_REQUEST_SHA256
    assert _transition_digests(summary) == ANCHOR_TRANSITION_SHA256


def test_first_visit_of_another_phase_still_refuses_an_already_visible_value():
    """(d) The guard keeps its original purpose.

    A fuser that fails to exclude ``QueryState.retrieved_value_ids`` on a
    genuinely new acquisition -- a phase this trajectory has never answered
    -- is still refused by name, because ``restrict_repeat_visit_supply``
    returns such a decision unchanged.
    """

    from test_rails_controllers import _context, _material, _phase_supply, _query_state

    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    assert program.phases[1].name == "evidence"
    seeded = _context(
        replace(_query_state(sample_id="s1"), retrieved_value_ids=("v-1",)).validate()
    )
    seeded = replace(seeded, catalog_value_ids=("v-1", "v-2"), catalog_facet_ids=("f-1",))
    # The destination phase has never answered in this trajectory, so the
    # decision reaches _acquired_ids exactly as it did before E3c.
    assert not rc._phase_already_visited(seeded, "evidence")
    supply = _phase_supply(seeded, value_ids=("v-1", "v-2"))
    assert restrict_repeat_visit_supply(supply, seeded, phase_name="evidence") is supply

    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
        supply_for_phase=lambda _phase, ctx: _phase_supply(ctx, value_ids=("v-1", "v-2")),
    )
    contact = controller.initial_contact(seeded)
    with pytest.raises(
        rc.RailsControllersError, match="already visible in this trajectory"
    ):
        controller.advance(seeded, contact, "A direct answer.")
