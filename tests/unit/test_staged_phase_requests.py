"""Synthetic end-to-end coverage for the staged request gate."""

from __future__ import annotations

from pathlib import Path
import pytest

from speech_aware_evidence_acquisition.core.preparation_fit import boundary_identity
from speech_aware_evidence_acquisition.rails import controllers
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.phase_runner import (
    PhaseRunnerError,
    run_continuous_program,
    run_program,
)
from test_rails_frozen_core_client import (
    _CapturingTransport,
    _OpenGate,
    _World,
    _client,
    _plan,
    _speech_feature_world,
)
from test_rails_runner import _FakeAdapter, _knowledge_snapshot


def _world(tmp_path: Path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    transport = _CapturingTransport(
        lambda p: f"{p['history'][-1]['contact_id']}:{p['sample_id']}"
    )
    client, gate, _ = _client(
        world,
        tmp_path,
        gate=_OpenGate(),
        transport=transport,
        plan=_plan(planned_model_calls=4),
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    return world, feature_root, packet, bindings, client, gate, transport


def _material(calls):
    def material(phase, context, sealed):
        calls.append((phase, context.sample_id, dict(sealed)))
        if phase == "revise":
            assert (
                sealed[context.sample_id].content
                == f"contact-draft-{context.sample_id}:{context.sample_id}"
            )
        return PhaseMaterial(
            instruction=(
                f"Make the {phase} decision for {context.sample_id}."
                + (
                    f" Prior phase: {sealed[context.sample_id].content}"
                    if phase == "revise"
                    else ""
                )
            ),
            response_format=None,
            contact_id=f"contact-{phase}-{context.sample_id}",
            purpose=phase,
        )

    return material


def _run(tmp_path, *, request_batch_gate, probe=None, **overrides):
    world, root, packet, bindings, client, gate, transport = _world(tmp_path)
    calls = []
    values = dict(
        program=controllers.default_phase_program("phase-draft-revise-v1"),
        adapter=_FakeAdapter(samples=tuple(world.samples)),
        plan=_plan(planned_model_calls=4),
        data_root=world.data_root,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings=bindings,
        trace_sink=client._dispatching_sink,
        decoding_params={"temperature": 0},
        material_for_phase=_material(calls),
        expected_row_count=2,
        slot_count=1,
        queue_depth=2,
        request_batch_gate=request_batch_gate,
    )
    values.update(overrides)
    if probe is not None:
        probe.update(root=root, packet=packet, transport=transport)
    return run_program(**values), calls, client, gate, transport


def test_staged_two_phase_gate_prepares_exact_roster_then_dispatches_same_requests(
    tmp_path,
):
    seen, probe = [], {}

    def batch_gate(phase, requests):
        assert len(probe["transport"].calls) == (0 if phase == "draft" else 2)
        payloads = tuple(request.as_payload() for request in requests)
        assert {p["sample_id"] for p in payloads} == {"s1", "s2"}
        assert len(payloads) == 2
        seen.append((phase, payloads))

    summaries, material, client, gate, transport = _run(
        tmp_path, request_batch_gate=batch_gate, probe=probe
    )
    assert len(summaries) == 2
    assert [phase for phase, _ in seen] == ["draft", "revise"]
    assert len(transport.calls) == 4
    assert [row[:2] for row in material] == [
        ("draft", "s1"),
        ("draft", "s2"),
        ("revise", "s1"),
        ("revise", "s2"),
    ]
    assert all(not sealed for phase, _sample, sealed in material if phase == "draft")
    assert all(
        set(sealed) == {"s1", "s2"}
        for phase, _sample, sealed in material
        if phase == "revise"
    )
    actual = {p["history"][-1]["contact_id"]: p for p in transport.calls}
    for phase, prepared in seen:
        for payload in prepared:
            dispatched = actual[payload["history"][-1]["contact_id"]]
            assert boundary_identity((payload,)) == boundary_identity((dispatched,))
            assert dispatched["decoding_params"]["id_slot"] == 0
            assert dispatched["history"][-1]["role"] == "control"
            if phase == "revise":
                assert (
                    f"contact-draft-{dispatched['sample_id']}:{dispatched['sample_id']}"
                    in dispatched["history"][-1]["content"]
                )
    client.close()


def test_staged_gate_refusal_spends_zero_for_first_or_only_prior_phase_for_second(
    tmp_path,
):
    probe = {}

    def reject_first(phase, _requests):
        if phase == "draft":
            assert not probe["transport"].calls
            raise RuntimeError("draft refusal")

    with pytest.raises(RuntimeError, match="draft refusal"):
        _run(tmp_path / "first", request_batch_gate=reject_first, probe=probe)
    assert not probe["transport"].calls
    probe = {}

    def reject_second(phase, _requests):
        if phase == "revise":
            assert len(probe["transport"].calls) == 2
            raise RuntimeError("revise refusal")

    with pytest.raises(RuntimeError, match="revise refusal"):
        _run(tmp_path / "second", request_batch_gate=reject_second, probe=probe)
    assert len(probe["transport"].calls) == 2


def test_staged_dispatch_refuses_packet_corrupted_after_fit(tmp_path):
    probe = {}

    def corrupt(phase, _requests):
        if phase == "draft":
            path = next(probe["root"].rglob("*.f32"))
            path.write_bytes(path.read_bytes() + b"corrupt")

    with pytest.raises(Exception, match="sha256|size|feature"):
        _run(tmp_path, request_batch_gate=corrupt, probe=probe)


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"supply_for_phase": lambda *_: None}, PhaseRunnerError),
        ({"review_for_phase": lambda *_: None}, PhaseRunnerError),
        ({"bootstrap_facet_ids_by_phase": {"draft": ("x",)}}, PhaseRunnerError),
        ({"agent_executor_id": "reference-trajectory-v1"}, PhaseRunnerError),
    ],
)
def test_staged_gate_refuses_nonplain_or_fanout_execution(tmp_path, overrides, error):
    with pytest.raises(error):
        _run(tmp_path, request_batch_gate=lambda _phase, _requests: None, **overrides)


def _run_continuous(tmp_path, *, request_batch_gate):
    world, root, packet, bindings, client, gate, transport = _world(tmp_path)
    material_calls = []
    summary = run_continuous_program(
        program=controllers.default_phase_program("phase-draft-revise-v1"),
        adapter=_FakeAdapter(samples=tuple(world.samples)),
        plan=_plan(planned_model_calls=4),
        data_root=world.data_root,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings=bindings,
        trace_sink=client._dispatching_sink,
        decoding_params={"temperature": 0},
        material_for_phase=_material(material_calls),
        slot_count=1,
        queue_depth=2,
        whole_roster_wave_barrier=True,
        request_batch_gate=request_batch_gate,
    )
    return summary, material_calls, client, transport


def test_continuous_whole_roster_barrier_gates_real_waves_and_prior_state(tmp_path):
    gates = []
    transport_box = {}

    def gate(phase, requests):
        payloads = tuple(request.as_payload() for request in requests)
        assert {payload["sample_id"] for payload in payloads} == {"s1", "s2"}
        assert len(payloads) == 2
        if phase == "draft":
            assert not transport_box["transport"].calls
            assert all(
                not any(item["role"] == "agent_state" for item in payload["history"])
                for payload in payloads
            )
        elif phase == "revise":
            assert len(transport_box["transport"].calls) == 2
            assert all(
                any(item["role"] == "agent_state" for item in payload["history"])
                for payload in payloads
            )
            assert all(
                next(
                    item["producer_policy_id"]
                    for item in payload["history"]
                    if item["role"] == "agent_state"
                )
                == "phase-draft-revise-v1"
                for payload in payloads
            )
        else:  # pragma: no cover - two-phase fixture has a closed roster
            raise AssertionError(f"unexpected gate phase {phase!r}")
        gates.append((phase, payloads))

    # The gate observes actual prepared requests.  It never creates a response.
    world, root, packet, bindings, client, gate_handle, transport = _world(tmp_path)
    transport_box["transport"] = transport
    material_calls = []
    summary = run_continuous_program(
        program=controllers.default_phase_program("phase-draft-revise-v1"),
        adapter=_FakeAdapter(samples=tuple(world.samples)),
        plan=_plan(planned_model_calls=4),
        data_root=world.data_root,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings=bindings,
        trace_sink=client._dispatching_sink,
        decoding_params={"temperature": 0},
        material_for_phase=_material(material_calls),
        slot_count=1,
        queue_depth=2,
        whole_roster_wave_barrier=True,
        request_batch_gate=gate,
    )

    assert [phase for phase, _ in gates] == ["draft", "revise"]
    assert len(transport.calls) == 4
    assert [item[:2] for item in material_calls] == [
        ("draft", "s1"),
        ("draft", "s2"),
        ("revise", "s1"),
        ("revise", "s2"),
    ]
    assert len(summary.results) == 2
    client.close()


def test_continuous_whole_roster_second_gate_refusal_never_sends_second_wave(tmp_path):
    seen = []
    transport_box = {}

    def gate(phase, requests):
        seen.append((phase, tuple(request.as_payload() for request in requests)))
        if phase == "revise":
            assert len(transport_box["transport"].calls) == 2
            assert all(
                any(item["role"] == "agent_state" for item in payload["history"])
                for payload in seen[-1][1]
            )
            raise RuntimeError("second wave refused")

    world, root, packet, bindings, client, gate_handle, transport = _world(tmp_path)
    transport_box["transport"] = transport
    with pytest.raises(RuntimeError, match="second wave refused"):
        run_continuous_program(
            program=controllers.default_phase_program("phase-draft-revise-v1"),
            adapter=_FakeAdapter(samples=tuple(world.samples)),
            plan=_plan(planned_model_calls=4),
            data_root=world.data_root,
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings=bindings,
            trace_sink=client._dispatching_sink,
            decoding_params={"temperature": 0},
            material_for_phase=_material([]),
            slot_count=1,
            queue_depth=2,
            whole_roster_wave_barrier=True,
            request_batch_gate=gate,
        )
    assert [phase for phase, _ in seen] == ["draft", "revise"]
    assert len(transport.calls) == 2
    client.close()



@pytest.mark.parametrize("whole_roster", [False, True])
def test_review_planner_drives_real_ojw_and_only_flagged_sample_continues(
    tmp_path, whole_roster,
):
    from test_phase_planner import _binding, _program, _FLAGGED, _CLEAN
    from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
    from speech_aware_evidence_acquisition.rails.phase_planner import emit_planner_records

    world, _, _, bindings, client, _, transport = _world(tmp_path)
    transport._responder = lambda p: (
        _FLAGGED if p["history"][-1]["contact_id"] == "contact-draft-s1" else _CLEAN
    )
    _, reviewer, planner = _binding()
    gates, materials = [], []
    sink = TraceBuffer(client._dispatching_sink.run_id)

    def material(phase, context, sealed):
        materials.append((phase, context.sample_id))
        if phase == "revise":
            assert context.sample_id == "s1"
            assert sealed["s1"].content == _FLAGGED
        return PhaseMaterial(
            instruction=f"Transcribe {phase}.", response_format=None,
            contact_id=f"contact-{phase}-{context.sample_id}", purpose=phase,
        )

    def fit_gate(phase, requests):
        payloads = tuple(request.as_payload() for request in requests)
        if phase == "draft":
            assert len(transport.calls) == 0
            assert {p["sample_id"] for p in payloads} == {"s1", "s2"}
        else:
            assert phase == "revise"
            assert len(transport.calls) == 2
            assert [p["sample_id"] for p in payloads] == ["s1"]
            assert any(
                item["role"] == "agent_state" for item in payloads[0]["history"]
            )
        gates.append((phase, payloads))

    try:
        summary = run_continuous_program(
            program=_program(), adapter=_FakeAdapter(samples=tuple(world.samples)),
            plan=_plan(planned_model_calls=4), data_root=world.data_root,
            core_client=client, split_id="all",
            knowledge_snapshot=_knowledge_snapshot(), speech_packet_bindings=bindings,
            trace_sink=sink, decoding_params={"temperature": 0},
            material_for_phase=material, review_for_phase=reviewer, stop_policy=planner,
            slot_count=2, queue_depth=2, whole_roster_wave_barrier=whole_roster,
            request_batch_gate=fit_gate if whole_roster else None,
        )
        assert "openjiuwen" in summary.agent_executor_id.lower()
        assert len(transport.calls) == 3
        assert sorted(materials) == [("draft", "s1"), ("draft", "s2"), ("revise", "s1")]
        results = {row.sample_id: row for row in summary.results}
        assert len(results["s1"].contacts) == 2
        assert len(results["s2"].contacts) == 1
        assert results["s1"].final_response_text == results["s2"].final_response_text == _CLEAN
        assert len([row for row in sink.records if row[0] == "REVIEW"]) == 2
        assert emit_planner_records(planner, sink) == 2
        if whole_roster:
            assert [phase for phase, _ in gates] == ["draft", "revise"]
            prepared = {
                payload["history"][-1]["contact_id"]: payload
                for _, batch in gates for payload in batch
            }
            sent = {p["history"][-1]["contact_id"]: p for p in transport.calls}
            assert prepared.keys() == sent.keys()
            for contact_id, payload in prepared.items():
                assert boundary_identity((payload,)) == boundary_identity((sent[contact_id],))
    finally:
        client.close()
