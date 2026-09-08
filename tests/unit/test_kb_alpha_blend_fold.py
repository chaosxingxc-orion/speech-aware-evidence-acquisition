"""WAVE R7: the ``saea-kb-alpha-blend-v1`` fold onto the shared base.

``rails.kb_policy.KbAlphaBlendController`` kept its whole acquire decision
inside its own ``_advance_after_direct``, which is why five SLURP experiment
configs could not reach it from ``rails.controllers.EvidenceAgentController``.
This wave split the decision out into one module-level body,
``compute_alpha_blend_decision``, and expressed it as the two seams the base
already exposes:

* ``stop_policy`` -- the retain-primary shortcut (all four of its cases);
* ``supply_for_phase`` -- the acquire, returning the same
  ``RankResult``/``FusionDecision`` pair.

**Structural equivalence.** The controller and the fold call THE SAME function.
There is one decision body, so the two cannot drift; these tests prove the
seams route it correctly and that the branch taken matches, case by case.

**One declared behavioural delta.** The base seals the direct answer as an
``AgentStateArtifact`` and carries it on the successor ``QueryState``, so the
evidence contact sees it as an agent-state turn; the retired controller sealed
nothing and the evidence contact saw only the retrieved values. That is the
standardization -- every other phase program in this repository traces its own
intermediate answers -- and it is asserted here rather than left to be
discovered by whoever flips the first cell.

Model-free: no contact, no GPU, no data root.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails import kb_policy
from speech_aware_evidence_acquisition.rails.controllers import (
    EvidenceAgentController,
    RailsControllersError,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext

# The red/green fixture world this fold is exercised on is the one
# ``test_kb_policy_v1`` already uses for the retired controller, imported
# rather than copied so the two shapes are compared on identical inputs.
from test_kb_policy_v1 import (  # noqa: E402  (pytest puts tests/unit on sys.path)
    _DIRECT_TEXT,
    _RED_GREEN_FACET_VECTORS,
    _RED_GREEN_QUERY_VECTOR,
    _red_green_controller_snapshot,
)

_SHA = "a" * 64

RANK_WEIGHTS = kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0)
FUSE_KNOBS = kb_policy.FuseKnobs(tau=0.5, m=10, c=1, top_l=2)


def _factories(*, alpha: float, query_vectors_by_sample=None):
    """The legacy controller factory and the folded one, same knobs."""

    snapshot = _red_green_controller_snapshot()
    if query_vectors_by_sample is None:
        query_vectors_by_sample = {"s1": _RED_GREEN_QUERY_VECTOR}
    kwargs = dict(
        snapshot=snapshot,
        query_vectors_by_sample=query_vectors_by_sample,
        facet_vectors=lambda facet_id: _RED_GREEN_FACET_VECTORS.get(facet_id, {}),
        rank_weights=RANK_WEIGHTS,
        fuse_knobs=FUSE_KNOBS,
        alpha=alpha,
        top_k_per_dimension=10,
    )
    return (
        snapshot,
        kb_policy.make_kb_alpha_blend_controller_factory(**kwargs),
        kb_policy.make_kb_alpha_blend_phase_controller_factory(**kwargs),
    )


def _context(snapshot, *, sample_id: str = "s1") -> AgentRuntimeContext:
    state = QueryState(
        query_id=f"run:{sample_id}:step0",
        query_sample_id=sample_id,
        speech_packet_id=f"speech/{sample_id}",
        speech_packet_sha256=_SHA,
        use_split_identity_hash=_SHA,
        loop_step=0,
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256=snapshot.content_hash(),
        catalog_facet_ids=tuple(facet.facet_id for facet in snapshot.facets),
        catalog_value_ids=tuple(value.value_id for value in snapshot.values),
        query_state=state,
        task_contract="Answer as compact JSON.",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )


def _first_wave(factory, snapshot, response: str):
    """Dispatch the direct contact, feed it ``response``, return the advance."""

    controller = factory("s1")
    context = _context(snapshot)
    contact = controller.initial_contact(context)
    return controller, contact, controller.advance(context, contact, response)


# ---------------------------------------------------------------------------
# 1. One decision body, four retain cases and the acquire case
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alpha, query_vectors, expect_retain, expect_reason",
    [
        (0.0, None, True, "direct-label-uniquely-wins-the-blend"),
        (0.5, None, False, ""),
        (1.0, None, False, ""),
        (1.0, {}, True, "no-fused-values"),
    ],
)
def test_the_two_shapes_take_the_same_branch(
    alpha, query_vectors, expect_retain, expect_reason
):
    snapshot, legacy_factory, fold_factory = _factories(
        alpha=alpha, query_vectors_by_sample=query_vectors
    )

    _legacy, legacy_contact, legacy_advance = _first_wave(
        legacy_factory, snapshot, _DIRECT_TEXT
    )
    _folded, fold_contact, fold_advance = _first_wave(
        fold_factory, snapshot, _DIRECT_TEXT
    )

    # Same branch.
    assert (legacy_advance.next_contact is None) is expect_retain
    assert (fold_advance.next_contact is None) is expect_retain
    assert legacy_advance.transition.action_kind == fold_advance.transition.action_kind

    # Same CONTROL turn on the contact that was dispatched.
    assert fold_contact.contact_id == legacy_contact.contact_id
    assert fold_contact.instruction == legacy_contact.instruction

    if not expect_retain:
        # Same retrieval decision, byte for byte on the ids that ride it.
        assert (
            fold_advance.fusion_decision.selected_value_ids
            == legacy_advance.fusion_decision.selected_value_ids
        )
        assert (
            fold_advance.rank_result.content_hash()
            == legacy_advance.rank_result.content_hash()
        )
        assert fold_advance.next_contact.contact_id == (
            legacy_advance.next_contact.contact_id
        )
        assert fold_advance.next_contact.instruction == (
            legacy_advance.next_contact.instruction
        )
        assert fold_advance.transition.new_value_ids == (
            legacy_advance.transition.new_value_ids
        )
    else:
        decision = kb_policy.compute_alpha_blend_decision(
            response_text=_DIRECT_TEXT,
            snapshot=snapshot,
            snapshot_sha256=snapshot.content_hash(),
            query_state=_context(snapshot).query_state,
            query_vectors=(
                {"s1": _RED_GREEN_QUERY_VECTOR}
                if query_vectors is None
                else query_vectors
            ).get("s1", {}),
            facet_vectors=lambda facet_id: _RED_GREEN_FACET_VECTORS.get(facet_id, {}),
            normalizer=kb_policy.default_label_normalizer,
            ranker=kb_policy.rank_wcos_prior_agree_factory(RANK_WEIGHTS),
            fuser=kb_policy.fuse_supplyfilter_factory(FUSE_KNOBS),
            alpha=alpha,
            top_k_per_dimension=10,
            label_targets=kb_policy._label_identities(snapshot),
            values_by_id={value.value_id: value for value in snapshot.values},
        )
        assert decision.retain_direct is True
        assert decision.retain_reason == expect_reason


def test_a_snapshotless_decision_retains_without_touching_recall():
    decision = kb_policy.compute_alpha_blend_decision(
        response_text=_DIRECT_TEXT,
        snapshot=None,
        snapshot_sha256="c" * 64,
        query_state=_context(_red_green_controller_snapshot()).query_state,
        query_vectors={},
        facet_vectors=lambda facet_id: {},
        normalizer=kb_policy.default_label_normalizer,
        ranker=lambda **kwargs: pytest.fail("the ranker must not run"),
        fuser=lambda **kwargs: pytest.fail("the fuser must not run"),
        alpha=0.5,
        top_k_per_dimension=1,
        label_targets={},
        values_by_id={},
    )
    assert decision.retain_direct is True
    assert decision.retain_reason == "no-snapshot-or-no-label-targets"
    assert decision.rank_result is None


# ---------------------------------------------------------------------------
# 2. The fold is the base, and it carries the cell's own identity
# ---------------------------------------------------------------------------


def test_the_fold_builds_the_shared_base_on_the_registered_program():
    snapshot, _legacy, fold_factory = _factories(alpha=0.5)
    controller = fold_factory("s1")
    assert isinstance(controller, EvidenceAgentController)
    assert controller.program.program_id == kb_policy.ALPHA_BLEND_PROGRAM_ID
    assert controller.program.stop_rule == "stop-policy-optional-early-exit"


def test_each_phase_keeps_its_own_declared_key_representation():
    snapshot, _legacy, fold_factory = _factories(alpha=1.0)
    _folded, direct_contact, advance = _first_wave(
        fold_factory, snapshot, _DIRECT_TEXT
    )
    assert direct_contact.key_representation_id == (
        f"{kb_policy.CONTROLLER_POLICY_ID}:direct"
    )
    assert advance.next_contact.key_representation_id == (
        f"{kb_policy.CONTROLLER_POLICY_ID}:evidence"
    )
    assert direct_contact.matcher_policy_id == kb_policy.CONTROLLER_POLICY_ID


def test_an_unknown_phase_instruction_override_is_refused_by_name():
    snapshot = _red_green_controller_snapshot()
    with pytest.raises(kb_policy.RailsError, match="unknown phase instruction"):
        kb_policy.make_kb_alpha_blend_phase_controller_factory(
            snapshot=snapshot,
            rank_weights=RANK_WEIGHTS,
            fuse_knobs=FUSE_KNOBS,
            alpha=0.5,
            top_k_per_dimension=10,
            instructions={"nope": "text"},
        )


def test_a_per_phase_identity_map_must_name_every_phase():
    program = kb_policy_program()
    with pytest.raises(RailsControllersError, match="must name every phase"):
        EvidenceAgentController(
            program=program,
            material_for_phase=lambda name, ctx: None,
            contact_identity={"direct": ("k", "m")},
        )


def kb_policy_program():
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )

    return default_phase_program(kb_policy.ALPHA_BLEND_PROGRAM_ID)


# ---------------------------------------------------------------------------
# 3. The declared delta
# ---------------------------------------------------------------------------


def test_the_fold_seals_the_direct_answer_and_the_legacy_shape_does_not():
    """The one behavioural difference, pinned rather than discovered."""

    snapshot, legacy_factory, fold_factory = _factories(alpha=1.0)
    _legacy, _legacy_contact, legacy_advance = _first_wave(
        legacy_factory, snapshot, _DIRECT_TEXT
    )
    _folded, _fold_contact, fold_advance = _first_wave(
        fold_factory, snapshot, _DIRECT_TEXT
    )

    assert legacy_advance.new_agent_states == ()
    assert legacy_advance.next_query_state.agent_state_ids == ()

    assert len(fold_advance.new_agent_states) == 1
    sealed = fold_advance.new_agent_states[0]
    assert sealed.state_id == "direct:s1"
    assert sealed.state_kind == "phase:direct"
    assert sealed.content == _DIRECT_TEXT
    assert fold_advance.next_query_state.agent_state_ids == ("direct:s1",)
    # ... and the retrieval decision it carries is the same one either way.
    assert (
        fold_advance.transition.new_value_ids
        == legacy_advance.transition.new_value_ids
    )
