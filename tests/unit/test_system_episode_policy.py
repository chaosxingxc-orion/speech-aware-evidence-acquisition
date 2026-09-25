"""Whole-episode selection through the existing graph, without live inference."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
import test_native_episode_runner as harness_module
from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from speech_aware_evidence_acquisition.rails.finite_action_policy import (
    PolicySnapshot, PolicyDecision, RoundDescriptor, TerminalFeedback, update_complete_round,
)
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import PolicySchedule
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_episode_policy import SystemEpisodePolicy, SystemEpisodePolicyError
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available


def _policy(bindings, roster=("s1",), *, emit=None):
    snapshot = PolicySnapshot.create(actions=tuple(bindings), states=("episode-start",), f0=0.58)
    schedule = PolicySchedule(
        round_id="synthetic-system-round", mode="construction", snapshot_sha256=snapshot.sha256,
        roster_ids=roster, roster_identity_sha256=content_hash(list(roster)),
        split_identity_hash="b"*64, seed=17,
        allocation_kind="balanced-without-replacement", epsilon=None,
        initial_quotas=tuple(len(roster)//len(bindings) + (i < len(roster)%len(bindings))
                             for i in range(len(bindings))),
    ).bind(snapshot)
    return SystemEpisodePolicy(snapshot=snapshot, schedule=schedule, actions=bindings,
        source_hashes={name: {"resolved_config": content_hash({"action": name})} for name in bindings},
        emit_decision=emit)


def _install(harness, monkeypatch, *, roster, learned_snapshot=None):
    real = harness_module.NativeEpisodeRunBinding
    captured = {}
    def factory(**kwargs):
        ordinary = real(**kwargs)
        revised = replace(ordinary, config=replace(ordinary.config, max_revisions=1))
        accepted = replace(ordinary, config=replace(ordinary.config, max_revisions=0, exhaustion_policy="deliver-latest-solver"))
        def emitted(record):
            harness.events.append(("system-decision", record["sample_id"]))
        actions = {"repair-enabled": revised, "accept-only": accepted}
        if learned_snapshot is None:
            policy = _policy(actions, roster, emit=emitted)
        else:
            schedule = PolicySchedule(
                round_id="synthetic-next-round", mode="evaluation",
                snapshot_sha256=learned_snapshot.sha256, roster_ids=roster,
                roster_identity_sha256=content_hash(list(roster)), split_identity_hash="b"*64,
                seed=18, allocation_kind="epsilon-greedy", epsilon=0.0, initial_quotas=(),
            ).bind(learned_snapshot)
            policy = SystemEpisodePolicy(
                snapshot=learned_snapshot, schedule=schedule, actions=actions,
                source_hashes={n: {"resolved_config": content_hash({"action": n})} for n in actions},
                emit_decision=emitted,
            )
        captured["policy"] = policy
        return replace(ordinary, system_episode_policy=policy)
    monkeypatch.setattr(harness_module, "NativeEpisodeRunBinding", factory)
    return captured


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_complete_policy_changes_real_graph_and_is_selected_before_first_fit(tmp_path, monkeypatch):
    harness = _ActualEpisodeHarness(tmp_path, sample_count=2, max_revisions=1,
        max_contacts=7, planner_actions=("REVISE", "ACCEPT"), overlap=True)
    captured = _install(harness, monkeypatch, roster=("s1", "s2"))
    try:
        summary = harness.run()
    finally:
        harness.close()
    receipts = []
    for result in summary.results:
        receipt = result.native_episode_receipt
        choice = receipt["system_policy_decision"]
        receipts.append(choice)
        assert choice["sample_id"] == result.sample_id
        assert choice["decision"]["state_id"] == "episode-start"
        expected = 2 if choice["decision"]["action"] == "repair-enabled" else 1
        assert sum(v["stage"] == "solver" for v in receipt["role_visits"]) == expected
        assert harness.events.index(("system-decision", result.sample_id)) < harness.events.index(
            ("fit", (result.sample_id, "perception", 1, 1)))
        trace_rows = [p["org_system_policy_decision"] for c, _, p in harness.trace.records
                      if c == "ORG" and "org_system_policy_decision" in p
                      and p["org_system_policy_decision"]["sample_id"] == result.sample_id]
        assert trace_rows == [choice]
        ids = [rid for _, rid, _ in harness.trace.records]
        first_id = receipt["role_visits"][0]["execution_receipt"]["contacts"][0]["request_id"] + "/request"
        assert ids.index(result.sample_id + "/system-policy/initial") < ids.index(first_id)
        assert choice["selection_scope"] == "complete-episode-policy"
    assert {r["decision"]["action"] for r in receipts} == {"repair-enabled", "accept-only"}
    assert len(captured["policy"].decisions) == 2


def test_rejects_changed_shared_service_or_program_envelope():
    from test_native_episode_runner import _config, _program
    from speech_aware_evidence_acquisition.rails.native_episode_config import NativeEpisodeRunBinding
    f = lambda *args: None
    base = NativeEpisodeRunBinding(config=_config(max_revisions=1,max_contacts=7),
        program=_program(max_contacts=7), material_for_phase=f, render_request=f, request_gate=f)
    for altered in (replace(base, request_gate=lambda *args: None),
                    replace(base, config=replace(base.config, max_contacts=8)),
                    replace(base, config=replace(base.config, local_tool_workers=1)),
                    replace(base, program=replace(base.program, program_id="different"))):
        with pytest.raises(SystemEpisodePolicyError, match="envelope"):
            _policy({"base": base, "altered": altered}, ("s1","s2"))


def test_selection_requires_pristine_source_and_cannot_be_replayed():
    from test_native_episode_runner import _config, _program
    from speech_aware_evidence_acquisition.rails.native_episode_config import NativeEpisodeRunBinding
    from test_finite_supply_policy import context
    f = lambda *args: None
    base = NativeEpisodeRunBinding(config=_config(max_revisions=1,max_contacts=7),
        program=_program(max_contacts=7), material_for_phase=f, render_request=f, request_gate=f)
    original = context()
    query = original.query_state
    ctx = SimpleNamespace(sample_id="s1", query_state=query, agent_states=(),
                          prior_response_sha256s=(), contact_index=0)
    p = _policy({"base": base})
    with pytest.raises(SystemEpisodePolicyError, match="before"):
        p.select(SimpleNamespace(**{**ctx.__dict__, "contact_index": 1}))
    with pytest.raises(SystemEpisodePolicyError, match="before"):
        p.select(SimpleNamespace(**{**ctx.__dict__, "agent_states": original.agent_states}))
    selected, record = p.select(ctx)
    assert selected is base
    assert record["pre_action_query_sha256"] == query.content_hash()
    assert record["decision"]["propensity"] == 1
    with pytest.raises(SystemEpisodePolicyError, match="already"):
        p.select(ctx)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_synthetic_terminal_feedback_updates_then_reexecutes_complete_system(tmp_path, monkeypatch):
    first = _ActualEpisodeHarness(tmp_path/"first", sample_count=2, max_revisions=1,
        max_contacts=7, planner_actions=("REVISE", "ACCEPT"), overlap=True)
    with monkeypatch.context() as patch:
        bound = _install(first, patch, roster=("s1", "s2"))
        try:
            result = first.run()
        finally:
            first.close()
    policy = bound["policy"]
    snapshot_before = policy.snapshot.sha256
    # Synthetic feedback deliberately favors ACCEPT. It tests plumbing only;
    # these invented counts are never serialized as scientific observations.
    rows = []
    for output in result.results:
        receipt = output.native_episode_receipt
        decision = PolicyDecision.from_json(receipt["system_policy_decision"]["decision"])
        good = decision.action == "accept-only"
        rows.append(TerminalFeedback(
            sample_id=output.sample_id, trajectory_sha256=content_hash(receipt),
            source_hashes=(
                ("synthetic_terminal", content_hash({"text": output.final_response_text})),
                ("system_action_space", receipt["system_policy_decision"]["action_space_sha256"]),
                ("system_action_definition", receipt["system_policy_decision"]["selected_definition_sha256"]),
            ),
            decision=decision, action=decision.action, logged_propensity=decision.propensity,
            tp=1 if good else 0, fp=0 if good else 1, fn=0,
            intent_exact=1, format_ok=True,
            fallback_flags=("synthetic-latest-solver",) if good else (),
        ))
    schedule = policy.schedule
    descriptor = RoundDescriptor(
        round_id=schedule.round_id, roster_ids=schedule.roster_ids,
        roster_sha256=schedule.roster_identity_sha256, snapshot_sha256=policy.snapshot.sha256,
        epsilon=schedule.epsilon, allocation_kind=schedule.allocation_kind,
        initial_quotas=schedule.initial_quotas,
    )
    learned = update_complete_round(policy.snapshot, descriptor, rows)
    assert policy.snapshot.sha256 == snapshot_before
    assert learned.preferred_action("episode-start") == "accept-only"
    assert len(learned.credited) == 2
    assert any(c.fallback_flags for c in learned.credited)
    altered_sources = {
        name: {"resolved_config": content_hash({"changed_action": name})}
        for name in policy.actions
    }
    with pytest.raises(SystemEpisodePolicyError, match="action space"):
        SystemEpisodePolicy(
            snapshot=learned, schedule=replace(schedule, snapshot_sha256=learned.sha256),
            actions=policy.actions, source_hashes=altered_sources,
        )
    second = _ActualEpisodeHarness(tmp_path/"second", sample_count=2, max_revisions=1,
        max_contacts=7, planner_actions=("REVISE", "ACCEPT"), overlap=True)
    with monkeypatch.context() as patch:
        _install(second, patch, roster=("s1", "s2"), learned_snapshot=learned)
        try:
            rerun = second.run()
        finally:
            second.close()
    for output in rerun.results:
        receipt = output.native_episode_receipt
        assert receipt["system_policy_decision"]["decision"]["action"] == "accept-only"
        assert receipt["system_policy_decision"]["decision"]["snapshot_sha256"] == learned.sha256
        assert sum(v["stage"] == "solver" for v in receipt["role_visits"]) == 1
    assert len(learned.credited) == 2


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_parent_binding_envelope_is_checked_before_the_graph(tmp_path, monkeypatch):
    harness = _ActualEpisodeHarness(tmp_path, sample_count=1, max_revisions=1,
        max_contacts=7, planner_actions=("ACCEPT",))
    real = harness_module.NativeEpisodeRunBinding
    def factory(**kwargs):
        ordinary = real(**kwargs)
        policy = _policy({"base": ordinary})
        return replace(ordinary, request_gate=lambda request: None, system_episode_policy=policy)
    monkeypatch.setattr(harness_module, "NativeEpisodeRunBinding", factory)
    try:
        with pytest.raises(SystemEpisodePolicyError, match="envelope"):
            harness.run()
    finally:
        receipt = harness.close()
    assert receipt["request_count"] == 0
