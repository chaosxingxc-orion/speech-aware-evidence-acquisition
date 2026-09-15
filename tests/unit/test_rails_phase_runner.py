"""C4a: rails.phase_runner.run_agent_phase / run_program, exercised entirely
against a fake ``agent_runner`` that captures kwargs and returns a
``SimpleNamespace`` summary -- mirroring
``rails.probes.a2t_semantic_agentloop``'s and
``rails.probes.a2t_select_fill_agentloop``'s own ``run_phase`` tests. No
real ``run_speech_native_agent_loop`` call, no model/GPU/network contact.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import phase_runner as pr
from speech_aware_evidence_acquisition.rails.execution_units import (
    ExecutionUnit,
    ExecutionUnitRoster,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter

_SHA_A = "a" * 64


class _FakeAdapter(TaskAdapter):
    SERVING_SLOTS = 3
    SERVING_SLOT_TOKENS = 4096
    SERVING_MAX_TOKENS = 256

    def load_split(self, split_id):
        return ()

    def build_task_contract(self, sample, obs):
        return "contract"


def _bindings(sample_ids):
    return {
        sample_id: {"packet_id": f"speech/{sample_id}", "sha256": f"{index:064x}"}
        for index, sample_id in enumerate(sample_ids)
    }


def _query_state(sample_id: str) -> QueryState:
    return QueryState(
        query_id=f"run:{sample_id}:step0",
        query_sample_id=sample_id,
        speech_packet_id=f"speech/{sample_id}",
        speech_packet_sha256=_SHA_A,
        use_split_identity_hash=_SHA_A,
    ).validate()


def _bare_summary(sample_ids, *, agent_executor_id="openjiuwen-workflow-v1", contacts_per_result=1):
    results = tuple(
        SimpleNamespace(
            sample_id=sample_id,
            contacts=tuple(object() for _ in range(contacts_per_result)),
        )
        for sample_id in sample_ids
    )
    return SimpleNamespace(agent_executor_id=agent_executor_id, results=results)


def _execution_unit_roster() -> ExecutionUnitRoster:
    """Two registered source records for one unchanged parent sample."""
    from speech_aware_evidence_acquisition.core.model import SliceRecord

    def record(iteration: int) -> SliceRecord:
        return SliceRecord(
            sample_id="s1",
            parent_media_relpath="speech/s1.wav",
            parent_sha256=_SHA_A,
            start_seconds=float(iteration),
            end_seconds=float(iteration + 1),
            audio_seconds=1.0,
            sample_rate_hz=16000,
            media_relpath=f"runs/slices/s1-{iteration}.wav",
            sha256=f"{iteration + 1:064x}",
            bytes=4,
            iteration=iteration,
        )

    return ExecutionUnitRoster(
        units=(
            ExecutionUnit("s1", "s1/window-0", record(0)),
            ExecutionUnit("s1", "s1/window-1", record(1)),
        )
    )


def _unit_summary(phase_name: str, roster: ExecutionUnitRoster):
    results = tuple(
        SimpleNamespace(
            sample_id=unit.parent_sample_id,
            execution_unit_id=unit.request_key,
            contacts=(object(),),
            final_response_text=f"{phase_name}:{unit.request_key}",
            initial_query_state=_query_state(unit.parent_sample_id),
        )
        for unit in roster.units
    )
    return SimpleNamespace(agent_executor_id="openjiuwen-workflow-v1", results=results)


_PHASES_DECLARING_RESPONSE_FORMAT = frozenset({"select", "fill"})


def _material_for_phase(name, ctx):
    # "select" and "fill" (phase-select-then-fill-v1) are the only phases,
    # across all four shipped programs, that declare a response_format_id --
    # supply a placeholder object schema for them so
    # EvidenceAgentController's declared-id<->material-presence check is
    # satisfied generically.
    response_format = (
        {"type": "object"} if name in _PHASES_DECLARING_RESPONSE_FORMAT else None
    )
    return PhaseMaterial(
        instruction=f"do {name} for {ctx.sample_id}",
        response_format=response_format,
        contact_id=f"c-{name}-{ctx.sample_id}",
        purpose=name,
    )


def _run_agent_phase_defaults(**overrides):
    values = dict(
        phase_name="draft",
        program=rc.default_phase_program("phase-draft-revise-v1"),
        adapter=_FakeAdapter(),
        plan=SimpleNamespace(),
        data_root=Path("."),
        core_client=SimpleNamespace(),
        split_id="all",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=_bindings(("s1", "s2")),
        trace_sink=SimpleNamespace(),
        decoding_params={},
        material_for_phase=_material_for_phase,
    )
    values.update(overrides)
    return values


# ---------------------------------------------------------------------------
# run_agent_phase: geometry derivation and solo-program controller wiring
# ---------------------------------------------------------------------------


def test_run_agent_phase_derives_slot_count_and_queue_depth_from_adapter_geometry():
    captured: dict[str, object] = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return _bare_summary(("s1", "s2"))

    returned = pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))

    assert captured["slot_count"] == 3
    assert captured["queue_depth"] == 12
    assert captured["max_contacts"] == 1
    assert captured["agent_executor_id"] == "openjiuwen-workflow-v1"
    assert returned.results


def test_run_agent_phase_forwards_artifact_result_kind_to_shared_runner():
    captured: dict[str, object] = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return _bare_summary(("s1", "s2"))

    pr.run_agent_phase(
        **_run_agent_phase_defaults(agent_runner=fake_runner),
        result_kind="artifact",
    )

    assert captured["result_kind"] == "artifact"


def test_run_agent_phase_namespaces_trace_records_by_phase():
    """core.tracing.TraceSink refuses a duplicate record id and every phase
    of a program shares one sink, so the second phase of a two-phase program
    would kill the run on its first emitted record -- after its contacts
    were spent. The namespace is what makes the shared sink safe."""

    captured: dict[str, object] = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return _bare_summary(("s1", "s2"))

    pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))

    assert captured["trace_record_namespace"] == _run_agent_phase_defaults()["phase_name"]


def test_agent_record_base_keeps_the_suffix_every_trace_reader_matches():
    from speech_aware_evidence_acquisition.rails.runner import _agent_record_base

    assert _agent_record_base("s1", None) == "s1/agent-loop"
    namespaced = _agent_record_base("s1", "select")
    assert namespaced == "s1/select/agent-loop"
    # The namespace goes BEFORE "agent-loop", so "/agent-loop/runtime-use"
    # remains the record-id suffix existing readers match on.
    assert f"{namespaced}/runtime-use".endswith("/agent-loop/runtime-use")


def test_run_agent_phase_honors_explicit_slot_count_and_queue_depth():
    captured: dict[str, object] = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return _bare_summary(("s1", "s2"))

    pr.run_agent_phase(
        **_run_agent_phase_defaults(
            agent_runner=fake_runner, slot_count=7, queue_depth=9
        )
    )
    assert captured["slot_count"] == 7
    assert captured["queue_depth"] == 9


def test_run_agent_phase_registers_solo_program_and_builds_scoped_controller():
    def fake_runner(**kwargs):
        registry = kwargs["controller_registry"]
        policy_id = kwargs["controller_policy_id"]
        assert policy_id == "phase-draft-revise-v1:draft"
        controller = registry.resolve(policy_id)("s1")
        assert controller.program.phase_names() == ("draft",)
        assert controller.program.max_contacts == 1
        return _bare_summary(("s1", "s2"))

    pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))


def test_run_agent_phase_forwards_run_identity_kwargs_unchanged():
    plan = SimpleNamespace(marker="plan")
    core_client = SimpleNamespace(marker="core")
    knowledge_snapshot = SimpleNamespace(marker="snapshot")
    data_root = Path("some/root")

    def fake_runner(**kwargs):
        assert kwargs["plan"] is plan
        assert kwargs["core_client"] is core_client
        assert kwargs["knowledge_snapshot"] is knowledge_snapshot
        assert kwargs["data_root"] == data_root
        assert kwargs["split_id"] == "all"
        return _bare_summary(("s1", "s2"))

    pr.run_agent_phase(
        **_run_agent_phase_defaults(
            plan=plan,
            core_client=core_client,
            knowledge_snapshot=knowledge_snapshot,
            data_root=data_root,
            agent_runner=fake_runner,
        )
    )


def test_run_agent_phase_unknown_phase_name_is_refused():
    def fake_runner(**kwargs):  # pragma: no cover - must never be reached
        raise AssertionError("agent_runner must not be called for an unknown phase")

    with pytest.raises(rc.RailsControllersError, match="no phase named"):
        pr.run_agent_phase(
            **_run_agent_phase_defaults(phase_name="nonexistent", agent_runner=fake_runner)
        )


# ---------------------------------------------------------------------------
# run_agent_phase: input refusals
# ---------------------------------------------------------------------------


def test_run_agent_phase_refuses_response_format_in_run_level_decoding_params():
    def fake_runner(**kwargs):  # pragma: no cover
        raise AssertionError("must be refused before dispatch")

    with pytest.raises(pr.PhaseRunnerError, match="response_format"):
        pr.run_agent_phase(
            **_run_agent_phase_defaults(
                decoding_params={"response_format": {}}, agent_runner=fake_runner
            )
        )


def test_run_agent_phase_refuses_empty_speech_packet_bindings():
    def fake_runner(**kwargs):  # pragma: no cover
        raise AssertionError("must be refused before dispatch")

    with pytest.raises(pr.PhaseRunnerError, match="non-empty mapping"):
        pr.run_agent_phase(
            **_run_agent_phase_defaults(speech_packet_bindings={}, agent_runner=fake_runner)
        )


def test_run_agent_phase_refuses_expected_row_count_mismatch_with_bindings():
    def fake_runner(**kwargs):  # pragma: no cover
        raise AssertionError("must be refused before dispatch")

    with pytest.raises(pr.PhaseRunnerError, match="exactly 5"):
        pr.run_agent_phase(
            **_run_agent_phase_defaults(expected_row_count=5, agent_runner=fake_runner)
        )


def test_run_agent_phase_refuses_non_positive_slot_count():
    def fake_runner(**kwargs):  # pragma: no cover
        raise AssertionError("must be refused before dispatch")

    with pytest.raises(pr.PhaseRunnerError, match="positive int"):
        pr.run_agent_phase(
            **_run_agent_phase_defaults(slot_count=0, agent_runner=fake_runner)
        )


def test_run_agent_phase_refuses_queue_depth_below_slot_count():
    def fake_runner(**kwargs):  # pragma: no cover
        raise AssertionError("must be refused before dispatch")

    with pytest.raises(pr.PhaseRunnerError, match="queue_depth"):
        pr.run_agent_phase(
            **_run_agent_phase_defaults(slot_count=4, queue_depth=2, agent_runner=fake_runner)
        )


# ---------------------------------------------------------------------------
# run_agent_phase: returned-summary validation
# ---------------------------------------------------------------------------


def test_run_agent_phase_refuses_wrong_agent_executor_id_in_summary():
    def fake_runner(**kwargs):
        return _bare_summary(("s1", "s2"), agent_executor_id="reference-trajectory-v1")

    with pytest.raises(pr.PhaseRunnerError, match="agent_executor_id"):
        pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))


def test_run_agent_phase_refuses_row_count_mismatch_with_bindings():
    def fake_runner(**kwargs):
        return _bare_summary(("s1",))  # only one row for a two-sample split

    with pytest.raises(pr.PhaseRunnerError, match="exactly 2 results"):
        pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))


def test_run_agent_phase_refuses_duplicate_sample_ids():
    def fake_runner(**kwargs):
        return _bare_summary(("s1", "s1"))

    with pytest.raises(pr.PhaseRunnerError, match="duplicate sample ids"):
        pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))


def test_run_agent_phase_refuses_result_identities_differing_from_bindings():
    def fake_runner(**kwargs):
        return _bare_summary(("s1", "sX"))

    with pytest.raises(pr.PhaseRunnerError, match="differ from speech_packet_bindings"):
        pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))


def test_run_agent_phase_refuses_result_without_exactly_one_contact():
    def fake_runner(**kwargs):
        return _bare_summary(("s1", "s2"), contacts_per_result=2)

    with pytest.raises(pr.PhaseRunnerError, match="exactly one contact"):
        pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))


def test_run_agent_phase_accepts_two_execution_units_for_one_parent():
    roster = _execution_unit_roster()

    def fake_runner(**kwargs):
        assert kwargs["execution_units"] is roster
        return _unit_summary("direct", roster)

    summary = pr.run_agent_phase(
        **_run_agent_phase_defaults(
            speech_packet_bindings=_bindings(("s1",)),
            execution_units=roster,
            expected_row_count=2,
            agent_runner=fake_runner,
        )
    )

    assert [result.execution_unit_id for result in summary.results] == [
        "s1/window-0",
        "s1/window-1",
    ]
    assert [result.sample_id for result in summary.results] == ["s1", "s1"]


def test_run_agent_phase_refuses_duplicate_execution_unit_ids():
    roster = _execution_unit_roster()

    def fake_runner(**kwargs):
        summary = _unit_summary("direct", roster)
        duplicate_fields = dict(summary.results[1].__dict__)
        duplicate_fields["execution_unit_id"] = "s1/window-0"
        duplicate = SimpleNamespace(
            **duplicate_fields
        )
        return SimpleNamespace(
            agent_executor_id=summary.agent_executor_id,
            results=(summary.results[0], duplicate),
        )

    with pytest.raises(pr.PhaseRunnerError, match="duplicate execution identities"):
        pr.run_agent_phase(
            **_run_agent_phase_defaults(
                speech_packet_bindings=_bindings(("s1",)),
                execution_units=roster,
                expected_row_count=2,
                agent_runner=fake_runner,
            )
        )


def test_run_agent_phase_refuses_non_tuple_results():
    def fake_runner(**kwargs):
        return SimpleNamespace(agent_executor_id="openjiuwen-workflow-v1", results=[])

    with pytest.raises(pr.PhaseRunnerError, match="non-empty results tuple"):
        pr.run_agent_phase(**_run_agent_phase_defaults(agent_runner=fake_runner))


# ---------------------------------------------------------------------------
# run_program: phase-by-phase sequencing and sealed-state threading
# ---------------------------------------------------------------------------


def _threading_fake_runner(call_order: list[str]):
    """A fake ``agent_runner`` that still resolves and drives the REAL
    controller ``run_agent_phase`` registered (one contact per sample,
    since every solo-phase program has ``max_contacts=1``), so
    ``material_for_phase`` -- and therefore ``run_program``'s own sealed
    state threading -- is genuinely exercised rather than bypassed."""

    def fake_runner(**kwargs):
        policy_id = kwargs["controller_policy_id"]
        call_order.append(policy_id)
        registry = kwargs["controller_registry"]
        factory = registry.resolve(policy_id)
        phase_name = policy_id.rsplit(":", 1)[-1]
        units = getattr(kwargs.get("execution_units"), "units", ())
        identities = (
            tuple((unit.parent_sample_id, unit.request_key) for unit in units)
            if units
            else tuple((sample_id, None) for sample_id in kwargs["speech_packet_bindings"])
        )
        results = []
        for sample_id, execution_unit_id in identities:
            controller = factory(sample_id)
            query_state = _query_state(sample_id)
            context = AgentRuntimeContext(
                sample_id=sample_id,
                knowledge_snapshot_sha256=_SHA_A,
                catalog_facet_ids=(),
                catalog_value_ids=(),
                query_state=query_state,
                task_contract="contract",
                agent_states=(),
                prior_response_sha256s=(),
                contact_index=0,
            )
            contact = controller.initial_contact(context)
            response_text = f"{phase_name}-response-for-{sample_id}"
            advance = controller.advance(context, contact, response_text)
            assert advance.transition.action_kind == "stop"
            result = SimpleNamespace(
                sample_id=sample_id,
                contacts=(contact,),
                final_response_text=response_text,
                initial_query_state=query_state,
            )
            if execution_unit_id is not None:
                result.execution_unit_id = execution_unit_id
            results.append(result)
        return SimpleNamespace(
            agent_executor_id="openjiuwen-workflow-v1", results=tuple(results)
        )

    return fake_runner


def test_run_program_iterates_phases_in_declared_order():
    program = rc.default_phase_program("phase-draft-revise-v1")
    call_order: list[str] = []

    summaries = pr.run_program(
        program=program,
        adapter=_FakeAdapter(),
        plan=SimpleNamespace(),
        data_root=Path("."),
        core_client=SimpleNamespace(),
        split_id="all",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=_bindings(("s1",)),
        trace_sink=SimpleNamespace(),
        decoding_params={},
        material_for_phase=lambda name, ctx, sealed: _material_for_phase(name, ctx),
        agent_runner=_threading_fake_runner(call_order),
    )

    assert len(summaries) == 2
    assert call_order == [
        "phase-draft-revise-v1:draft",
        "phase-draft-revise-v1:revise",
    ]


def test_run_program_threads_each_phases_sealed_state_to_the_next():
    program = rc.default_phase_program("phase-select-then-fill-v1")
    call_order: list[str] = []
    seen_material_calls: list[tuple[str, dict]] = []

    def material_for_phase(name, ctx, sealed):
        seen_material_calls.append((name, dict(sealed)))
        return _material_for_phase(name, ctx)

    pr.run_program(
        program=program,
        adapter=_FakeAdapter(),
        plan=SimpleNamespace(),
        data_root=Path("."),
        core_client=SimpleNamespace(),
        split_id="all",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=_bindings(("s1", "s2")),
        trace_sink=SimpleNamespace(),
        decoding_params={},
        material_for_phase=material_for_phase,
        agent_runner=_threading_fake_runner(call_order),
    )

    # The barrier: "fill"'s own run_agent_phase call (and therefore its
    # material_for_phase calls) only ever happens after "select"'s
    # run_agent_phase call has ALREADY RETURNED a full-roster summary --
    # call_order records strict phase-then-phase ordering, never interleaved.
    assert call_order == [
        "phase-select-then-fill-v1:select",
        "phase-select-then-fill-v1:fill",
    ]
    select_calls = [entry for entry in seen_material_calls if entry[0] == "select"]
    fill_calls = [entry for entry in seen_material_calls if entry[0] == "fill"]
    assert all(sealed == {} for _name, sealed in select_calls)
    assert len(fill_calls) == 2
    for _name, sealed in fill_calls:
        assert set(sealed) == {"s1", "s2"}
        for sample_id, artifact in sealed.items():
            assert artifact.content == f"select-response-for-{sample_id}"
            assert artifact.state_kind == "phase:select"
            assert artifact.producer_policy_id == program.program_id


def test_run_program_threads_predecessors_by_execution_unit_for_one_parent():
    program = rc.default_phase_program("phase-select-then-fill-v1")
    roster = _execution_unit_roster()
    seen_fill_predecessors: list[dict] = []

    def material_for_phase(name, ctx, sealed):
        if name == "fill":
            seen_fill_predecessors.append(dict(sealed))
        return _material_for_phase(name, ctx)

    pr.run_program(
        program=program,
        adapter=_FakeAdapter(),
        plan=SimpleNamespace(),
        data_root=Path("."),
        core_client=SimpleNamespace(),
        split_id="all",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=_bindings(("s1",)),
        execution_units=roster,
        trace_sink=SimpleNamespace(),
        decoding_params={},
        material_for_phase=material_for_phase,
        expected_row_count=2,
        agent_runner=_threading_fake_runner([]),
    )

    assert len(seen_fill_predecessors) == 2
    for sealed in seen_fill_predecessors:
        assert set(sealed) == {"s1/window-0", "s1/window-1"}
        assert sealed["s1/window-0"].content == "select-response-for-s1"
        assert sealed["s1/window-1"].content == "select-response-for-s1"


def test_run_program_returns_one_summary_per_phase_in_order():
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    call_order: list[str] = []

    summaries = pr.run_program(
        program=program,
        adapter=_FakeAdapter(),
        plan=SimpleNamespace(),
        data_root=Path("."),
        core_client=SimpleNamespace(),
        split_id="all",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=_bindings(("s1",)),
        trace_sink=SimpleNamespace(),
        decoding_params={},
        material_for_phase=lambda name, ctx, sealed: _material_for_phase(name, ctx),
        agent_runner=_threading_fake_runner(call_order),
    )
    assert len(summaries) == len(program.phases) == 2
    assert [summary.results[0].sample_id for summary in summaries] == ["s1", "s1"]


def test_run_continuous_program_accepts_two_execution_units_for_one_parent():
    roster = _execution_unit_roster()
    program = rc.default_phase_program("phase-direct-only-v1")
    captured: dict[str, object] = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return _unit_summary("direct", roster)

    summary = pr.run_continuous_program(
        program=program,
        adapter=_FakeAdapter(),
        plan=SimpleNamespace(),
        data_root=Path("."),
        core_client=SimpleNamespace(),
        split_id="all",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=_bindings(("s1",)),
        execution_units=roster,
        trace_sink=SimpleNamespace(),
        decoding_params={},
        material_for_phase=lambda name, ctx, sealed: _material_for_phase(name, ctx),
        agent_runner=fake_runner,
    )

    assert captured["execution_units"] is roster
    assert [result.execution_unit_id for result in summary.results] == [
        "s1/window-0",
        "s1/window-1",
    ]


def test_run_program_requires_callable_material_for_phase():
    program = rc.default_phase_program("phase-direct-only-v1")
    with pytest.raises(pr.PhaseRunnerError, match="material_for_phase"):
        pr.run_program(
            program=program,
            adapter=_FakeAdapter(),
            plan=SimpleNamespace(),
            data_root=Path("."),
            core_client=SimpleNamespace(),
            split_id="all",
            knowledge_snapshot=SimpleNamespace(),
            speech_packet_bindings=_bindings(("s1",)),
            trace_sink=SimpleNamespace(),
            decoding_params={},
            material_for_phase="not callable",  # type: ignore[arg-type]
        )
