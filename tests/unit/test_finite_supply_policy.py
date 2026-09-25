"""Pre-action supply selection over synthetic shared-rail states."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.controllers import seal_phase_response_state
from speech_aware_evidence_acquisition.rails.finite_action_policy import PolicySnapshot, sample_action
from speech_aware_evidence_acquisition.rails.finite_supply_policy import (
    AGREEMENT_STATES, EpisodeSupplyPolicy, FiniteSupplyPolicyError,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from test_rails_controllers import _phase_supply


def context(sample="s1", *, phase="perception", content="candidate-a"):
    query = QueryState("query-" + sample, sample, "speech-" + sample, "a" * 64, "b" * 64)
    state = seal_phase_response_state(
        phase_name=phase, sample_id=sample, state_content=content,
        raw_response_text=content, source_query_state_sha256=query.content_hash(),
        producer_policy_id="test-policy",
    )
    return SimpleNamespace(
        sample_id=sample, query_state=query, agent_states=(state,),
        prior_response_sha256s=(state.source_response_sha256,),
        knowledge_snapshot_sha256="c" * 64,
    )


def policy(*, preview_ids=("x", "y"), labels=None, emitted=None):
    snapshot = PolicySnapshot.create(actions=("default20", "examples10"), states=AGREEMENT_STATES, f0=0.58)
    calls = []
    schedule = SimpleNamespace(
        snapshot_sha256=snapshot.sha256, roster_ids=("s1",),
        decision_for=lambda sid, state, snap: (
            sample_action(snap, state_id=state, epsilon=1, draw=0.9), 0
        ),
        sha256="d" * 64,
    )
    def preview(ctx):
        calls.append("preview")
        return _phase_supply(ctx, value_ids=preview_ids) if preview_ids else None
    def action(name):
        def supply(phase, ctx):
            calls.append(name)
            return _phase_supply(ctx, value_ids=(name,))
        return supply
    routes = {name: action(name) for name in snapshot.actions}
    return EpisodeSupplyPolicy(
        snapshot=snapshot, schedule=schedule, phase_id="solver", perception_phase="perception",
        preview_supply=preview, preview_snapshot_sha256="c" * 64,
        preview_labels=labels or {"x": "candidate-a", "y": "candidate-b"},
        action_supplies=routes, default_supply=lambda phase, ctx: None,
        candidate_reader=lambda state, sid: (state.content,),
        emit_decision=emitted.append if emitted is not None else None,
    ), calls


def test_selects_after_perception_and_retains_action_across_revision():
    emitted = []
    bound, calls = policy(emitted=emitted)
    first = context()
    assert bound("reviewer", first) is None and calls == []
    assert bound("solver", first).fusion_decision.selected_value_ids == ("examples10",)
    assert calls == ["preview", "examples10"] and len(emitted) == 1
    row = emitted[0]
    assert row["state_id"] == "agree-0.50-0.75"
    assert row["preview"]["exposed_to_model"] is False
    assert row["preview"]["selected_value_ids"] == ["x", "y"]
    revised = SimpleNamespace(**vars(first))
    solver = seal_phase_response_state(
        phase_name="solver", sample_id="s1", state_content="changed",
        raw_response_text="changed", source_query_state_sha256=first.query_state.content_hash(),
        producer_policy_id="test-policy",
    )
    revised.agent_states += (solver,)
    revised.prior_response_sha256s += (solver.source_response_sha256,)
    assert bound("solver", revised).fusion_decision.selected_value_ids == ("examples10",)
    assert calls == ["preview", "examples10", "examples10"] and len(emitted) == 1


def test_first_decision_rejects_future_state_or_wrong_source():
    bound, _ = policy()
    with pytest.raises(FiniteSupplyPolicyError, match="first Perception"):
        bound("solver", context(phase="solver"))
    bad = context()
    bad.agent_states = (replace(bad.agent_states[0], source_query_state_sha256="e" * 64),)
    with pytest.raises(FiniteSupplyPolicyError, match="query"):
        bound("solver", bad)
    with pytest.raises(FiniteSupplyPolicyError, match="roster"):
        bound("solver", context("unknown"))


def test_empty_preview_and_missing_training_label_are_distinct():
    bound, _ = policy(preview_ids=())
    bound("solver", context())
    assert bound.receipt["decisions"]["s1"]["state_id"] == "no-exemplars"
    bound, _ = policy(preview_ids=("missing",))
    with pytest.raises(FiniteSupplyPolicyError, match="label"):
        bound("solver", context())


def test_preview_cannot_belong_to_a_different_snapshot():
    bound, _ = policy()
    bound.preview_snapshot_sha256 = "e" * 64
    with pytest.raises(FiniteSupplyPolicyError, match="snapshot"):
        bound("solver", context())
