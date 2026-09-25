"""Verify configured action selection and actual tool-result state."""

from dataclasses import replace
import hashlib
import json
import pytest
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.phase_tools import (
    build_phase_tools,
    PhaseToolError,
)
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from test_phase_planner import _context as _old_context, _material
from test_rails_runner import _knowledge_snapshot


def _context():
    snapshot = _knowledge_snapshot()
    return replace(_old_context(), knowledge_snapshot_sha256=snapshot.content_hash())


TASK = "saea-tool-task-contract-v1"
KNOWLEDGE = "saea-tool-phase-knowledge-v1"


def config(mode="core-choice", **kw):
    entry = {"mode": mode, "allowed_tools": [TASK], "knowledge_views": ["text"]}
    if mode == "fixed":
        entry["fixed_action"] = {"tool_id": TASK, "arguments": {}}
    entry.update(kw)
    return {"phase_tools": {"draft": entry}}


def staged(response, context=None):
    ctx = context or _context()
    sha = hashlib.sha256(response.encode()).hexdigest()
    state = AgentStateArtifact(
        state_id="draft:s1",
        state_kind="phase:draft",
        content=response,
        source_query_state_sha256=ctx.query_state.content_hash(),
        source_response_sha256=sha,
        producer_policy_id="phase-draft-revise-v1",
        cited_value_ids=(),
    ).validate()
    return replace(ctx, agent_states=(state,), prior_response_sha256s=(sha,))


def action(ctx, **kw):
    doc = {
        "tool_id": TASK,
        "arguments": {},
        "query_state_sha256": ctx.query_state.content_hash(),
    }
    doc.update(kw)
    return json.dumps(doc)


def test_empty_config_has_no_dispatcher():
    assert (
        build_phase_tools(
            {},
            rc.default_phase_program("phase-draft-revise-v1"),
            snapshot=_knowledge_snapshot(),
        )
        is None
    )


@pytest.mark.parametrize("mode", ["fixed", "core-choice"])
def test_real_tool_returns_bound_state_and_same_legal_contract(mode, monkeypatch):
    from speech_aware_evidence_acquisition.rails.tools import ToolEntry

    calls = []
    original = ToolEntry.call

    def observed(self, *args, **kwargs):
        calls.append(self.manifest.tool_id)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ToolEntry, "call", observed)
    ctx = _context()
    tool = build_phase_tools(
        config(mode),
        rc.default_phase_program("phase-draft-revise-v1"),
        snapshot=_knowledge_snapshot(),
    )
    state = staged(action(ctx))
    outcome = tool("draft", "revise", state)
    assert calls == [TASK]
    result = json.loads(outcome.state.content)
    assert result["result"]["task_contract"] == ctx.task_contract
    assert result["selection_mode"] == mode
    assert (
        outcome.state.source_response_sha256
        == state.agent_states[-1].source_response_sha256
    )
    assert outcome.supply is None
    with pytest.raises(PhaseToolError, match="already"):
        tool("draft", "revise", state)


@pytest.mark.parametrize(
    "bad",
    [
        {"tool_id": "unknown"},
        {"arguments": {"path": "/etc/passwd"}},
        {"query_state_sha256": "f" * 64},
    ],
)
def test_bad_model_actions_refuse_before_tool_call(bad, monkeypatch):
    from speech_aware_evidence_acquisition.rails.tools import ToolEntry

    monkeypatch.setattr(
        ToolEntry, "call", lambda *a, **kw: pytest.fail("tool was contacted")
    )
    tool = build_phase_tools(
        config(),
        rc.default_phase_program("phase-draft-revise-v1"),
        snapshot=_knowledge_snapshot(),
    )
    with pytest.raises(PhaseToolError):
        tool("draft", "revise", staged(action(_context(), **bad)))


def test_final_phase_and_unknown_config_are_rejected():
    p = rc.default_phase_program("phase-draft-revise-v1")
    for bad in (
        {"phase_tools": {"revise": config()["phase_tools"]["draft"]}},
        config(extra=True),
        config(mode="anything"),
    ):
        with pytest.raises(PhaseToolError):
            build_phase_tools(bad, p, snapshot=_knowledge_snapshot())


def test_action_instruction_has_state_and_capabilities_but_not_private_data():
    p = rc.default_phase_program("phase-draft-revise-v1")
    tool = build_phase_tools(config(), p, snapshot=_knowledge_snapshot())
    text = tool.instruction_for_phase("draft", _context())
    assert TASK in text and _context().query_state.content_hash() in text
    assert tool.instruction_for_phase("revise", _context()) == ""


def test_controller_carries_tool_result_to_solver_and_preserves_answer_authority():
    p = rc.default_phase_program("phase-draft-revise-v1")
    tool = build_phase_tools(config(), p, snapshot=_knowledge_snapshot())
    controller = rc.EvidenceAgentController(
        program=p, material_for_phase=_material, tools_for_phase=tool
    )
    ctx = _context()
    contact = controller.initial_contact(ctx)
    assert TASK in contact.instruction
    response = action(ctx)
    move = controller.advance(ctx, contact, response)
    assert len(move.new_agent_states) == 2
    assert move.new_agent_states[1].state_kind == "tool-result"
    assert move.next_query_state.agent_state_ids == tuple(
        x.state_id for x in move.new_agent_states
    )
    assert move.transition.new_agent_state_ids == move.next_query_state.agent_state_ids
    ctx2 = replace(
        ctx,
        query_state=move.next_query_state,
        agent_states=move.new_agent_states,
        prior_response_sha256s=(hashlib.sha256(response.encode()).hexdigest(),),
        contact_index=1,
    )
    final = controller.advance(ctx2, move.next_contact, "Solver answer")
    assert final.final_response_contact_id == move.next_contact.contact_id


@pytest.mark.parametrize("policy", ["fixed", "obs-agent-loop-ojw"])
def test_runtime_refuses_inert_tool_config_before_any_gate(policy, tmp_path):
    from test_flight_runtime import _make_runtime, _FakeGate
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError

    gate = _FakeGate()
    runtime = _make_runtime(
        tmp_path,
        gate=gate,
        config_kwargs={"policy": policy, "baseline_extra": config("fixed")},
    )
    with pytest.raises(FlightRuntimeError, match="phase_tools"):
        runtime.preflight()
    assert not gate.calls


def test_paired_action_requires_prepared_catalog_before_dispatch():
    with pytest.raises(PhaseToolError, match="prepared knowledge"):
        build_phase_tools(
            config(knowledge_views=["paired"]),
            rc.default_phase_program("phase-draft-revise-v1"),
            snapshot=_knowledge_snapshot(),
        )


def test_cross_snapshot_and_modified_state_refuse_before_contact(monkeypatch):
    from speech_aware_evidence_acquisition.rails.tools import ToolEntry

    monkeypatch.setattr(
        ToolEntry, "call", lambda *a, **kw: pytest.fail("unexpected tool contact")
    )
    ctx = staged(action(_context()))
    tool = build_phase_tools(
        config(),
        rc.default_phase_program("phase-draft-revise-v1"),
        snapshot=_knowledge_snapshot(),
    )
    for bad in (
        replace(ctx, knowledge_snapshot_sha256="f" * 64),
        replace(ctx, agent_states=(replace(ctx.agent_states[-1], content="changed"),)),
    ):
        with pytest.raises(PhaseToolError):
            tool("draft", "revise", bad)


def test_configuration_runs_public_runtime_wire_path(tmp_path):
    from test_flight_runtime import _make_runtime
    from test_rails_frozen_core_client import (
        _World,
        _speech_feature_world,
        _binding as payload_binding,
    )
    from test_rails_runner import _FakeAdapter
    from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient
    from speech_aware_evidence_acquisition.rails.phase_runner import run_program

    world = _World(tmp_path)
    feature_root, _, packets = _speech_feature_world(world, tmp_path)
    baseline = {
        "phase_tools": {
            "plan": {
                "mode": "fixed",
                "allowed_tools": [TASK],
                "fixed_action": {"tool_id": TASK, "arguments": {}},
            }
        },
        "phase_material": {
            phase: {
                "instruction_template": f"probes/{phase}.txt",
                "predecessor_binding": "none",
            }
            for phase in ("plan", "solve")
        },
    }
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "arm": "speech-feature-query",
            "policy": "phase-task-tools-then-solve-v1",
            "model_extra": {"speech_feature_root": str(feature_root)},
            "baseline_extra": baseline,
        },
        adapter_cls=lambda _lock, _root: _FakeAdapter(samples=tuple(world.samples)),
        client_factory=FrozenCoreClient,
        phase_runner=run_program,
        payload_binding_factory=lambda **_kw: payload_binding(world),
    )
    dataset = runtime._repo_root / "configs/dataset/d.json"
    dataset.write_text(
        json.dumps({"carrier_lock_key": "fake-carrier", "split_id": "all"})
    )
    for phase in ("plan", "solve"):
        p = runtime._repo_root / f"configs/probes/{phase}.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"Solve the task during {phase}.")
    runtime._load_knowledge_snapshot = _knowledge_snapshot
    runtime.speech_packet_bindings = lambda: packets
    runtime._speech_feature_root = lambda: feature_root
    receipt = runtime.wire_check(
        seal_and_score=False, response_text="synthetic Solver answer"
    )
    assert receipt["model_contacts"] == 0 and receipt["contact_count"] == 4
    assert receipt["dispatch"]["dispatch"] == "phase-program-continuous"
    assert receipt["dispatch"]["phase_tools"]["attempts"] == 2
    assert receipt["dispatch"]["phase_tools"]["completed"] == 2


@pytest.mark.parametrize("bad", [None, "", "named-store-maybe", {}, 1, True])
def test_explicit_invalid_value_rendering_refuses_even_without_tools(bad):
    with pytest.raises(PhaseToolError, match="knowledge_value_rendering"):
        build_phase_tools(
            {"knowledge_value_rendering": bad},
            rc.default_phase_program("phase-draft-revise-v1"),
            snapshot=_knowledge_snapshot(),
        )


def test_plain_rendering_configuration_does_not_create_tool_authority():
    assert build_phase_tools(
        {"knowledge_value_rendering": "canonical-plain-v1"},
        rc.default_phase_program("phase-draft-revise-v1"),
        snapshot=_knowledge_snapshot(),
    ) is None
