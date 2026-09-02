"""Model-free tests for the generic G5 PLAN -> COMPILE -> EXECUTE boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_g5_agentloop import (
    BUNDLE_ASCII_BYTE_CAP,
    EXECUTE_COMPLETION_TOKENS,
    FALLBACK_STATUS,
    G5_QUEUE_DEPTH,
    G5_SLOT_COUNT,
    PER_SLOT_PROMPT_TOKENS,
    PLAN_COMPLETION_TOKENS,
    PLAN_STATE_ASCII_BYTE_CAP,
    CompiledContract,
    CompiledFamilyBundle,
    FamilyTaxon,
    G5AgentLoopAdapter,
    G5AgentLoopController,
    G5AgentLoopError,
    ParsedPlan,
    parse_plan_response,
    run_g5_agentloop,
)


TAXONOMY = (
    FamilyTaxon("communication", ("send", "reply")),
    FamilyTaxon("calendar", ("create", "update")),
)


def _samples(count: int = 2) -> tuple[Audio2ToolSample, ...]:
    return tuple(
        Audio2ToolSample(
            sample_id=f"tier{index + 1}:sample-{index:02d}",
            audio_ref=AudioRef(
                path=f"audio/{index:02d}.wav", sha256=f"{index + 1:064x}"
            ),
            audio_seconds=1.0,
            media_relpath=f"audio/{index:02d}.wav",
        )
        for index in range(count)
    )


def _snapshot() -> KnowledgeSnapshot:
    facets = (
        KeyFacet(
            facet_id="facet:communication",
            dimension="action-family",
            representation_kind="closed-family",
            representation="Communication family contracts.",
            source_sample_ids=("train:1",),
        ),
        KeyFacet(
            facet_id="facet:calendar",
            dimension="action-family",
            representation_kind="closed-family",
            representation="Calendar family contracts.",
            source_sample_ids=("train:1",),
        ),
    )
    values = (
        ValueBundle(
            value_id="value:communication:send",
            content="CONTRACT C-SEND: registered name sendMessage; complete skeleton.",
            associated_facet_ids=("facet:communication",),
            source_sample_ids=("train:1",),
            provenance_refs=("fixture:communication",),
        ),
        ValueBundle(
            value_id="value:calendar:create",
            content="CONTRACT K-CREATE: registered name createEvent; complete skeleton.",
            associated_facet_ids=("facet:calendar",),
            source_sample_ids=("train:1",),
            provenance_refs=("fixture:calendar",),
        ),
    )
    return KnowledgeSnapshot(
        snapshot_id="g5-fixture",
        source_split_identity_hash="a" * 64,
        source_sample_ids=("train:1",),
        builder_policy_id="fixture-builder",
        facets=facets,
        values=values,
    ).validate()


class _Compiler:
    taxonomy = TAXONOMY
    fallback_family_tags = ("communication", "calendar")
    registered_tool_names = ("sendMessage", "createEvent")

    def __init__(self, *, synthetic_literals: tuple[str, ...] = ()) -> None:
        self.calls: list[ParsedPlan] = []
        self.synthetic_literals = synthetic_literals

    def compile(self, plan: ParsedPlan) -> CompiledFamilyBundle:
        self.calls.append(plan)
        family_tags = plan.selected_family_tags
        contracts: list[CompiledContract] = []
        if "communication" in family_tags:
            contracts.append(
                CompiledContract(
                    contract_id="contract:communication:send",
                    family_tag="communication",
                    facet_id="facet:communication",
                    value_id="value:communication:send",
                    content=(
                        "CONTRACT C-SEND: registered name sendMessage; complete skeleton."
                    ),
                )
            )
        if "calendar" in family_tags:
            contracts.append(
                CompiledContract(
                    contract_id="contract:calendar:create",
                    family_tag="calendar",
                    facet_id="facet:calendar",
                    value_id="value:calendar:create",
                    content=(
                        "CONTRACT K-CREATE: registered name createEvent; complete skeleton."
                    ),
                )
            )
        return CompiledFamilyBundle(
            family_tags=family_tags,
            contracts=tuple(contracts),
            complete=True,
            selection_mode="full-unranked-compatible",
            synthetic_literals=self.synthetic_literals,
        )


def _plan_json() -> str:
    return json.dumps(
        {
            "operations": [
                {
                    "family": "communication",
                    "operation": "send",
                    "values": [
                        {"label": "recipient", "span": "Alex"},
                        {"label": "content", "span": "the status update"},
                    ],
                    "correction": False,
                    "supersedes": [],
                    "turn_refs": ["current"],
                    "role": "user",
                },
                {
                    "family": "calendar",
                    "operation": "create",
                    "values": [{"label": "date", "span": "Friday"}],
                    "correction": True,
                    "supersedes": [0],
                    "turn_refs": ["current", "prior:1"],
                    "role": "user",
                },
            ]
        },
        separators=(",", ":"),
    )


def _context(step: int = 0, *, states=(), values=(), facets=()):
    query_state = QueryState(
        query_id="query-1",
        query_sample_id="dev:1",
        speech_packet_id="speech-1",
        speech_packet_sha256="b" * 64,
        use_split_identity_hash="c" * 64,
        loop_step=step,
        visible_facet_ids=facets,
        agent_state_ids=tuple(state.state_id for state in states),
        retrieved_value_ids=values,
    ).validate()
    return SimpleNamespace(
        sample_id="private-sample-id",
        knowledge_snapshot_sha256=_snapshot().content_hash(),
        query_state=query_state,
        task_contract="Closed taxonomy: communication=[send,reply]; calendar=[create,update].",
        agent_states=states,
        prior_response_sha256s=(),
        contact_index=step,
    )


def test_exact_parser_preserves_operation_value_and_turn_order() -> None:
    parsed = parse_plan_response(
        _plan_json(),
        taxonomy=TAXONOMY,
        fallback_family_tags=("communication", "calendar"),
        forbidden_terms=("sendMessage", "createEvent"),
    )

    assert parsed.valid is True
    assert parsed.selected_family_tags == ("communication", "calendar")
    assert [item.operation for item in parsed.operations] == ["send", "create"]
    assert [span.label for span in parsed.operations[0].values] == [
        "recipient",
        "content",
    ]
    assert parsed.operations[1].supersedes == (0,)
    assert parsed.operations[1].turn_refs == ("current", "prior:1")
    assert parsed.canonical_json == _plan_json()


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        '{"operations":[],"sample_id":"secret"}',
        _plan_json().replace('"communication"', '"unknown"', 1),
        _plan_json().replace('"Alex"', '"sendMessage"', 1),
        _plan_json().replace('"supersedes":[0]', '"supersedes":[1]'),
        _plan_json() + " trailing",
        "x" * (PLAN_STATE_ASCII_BYTE_CAP + 1),
    ],
)
def test_invalid_plan_is_frozen_fallback_without_raw_leakage(raw: str) -> None:
    parsed = parse_plan_response(
        raw,
        taxonomy=TAXONOMY,
        fallback_family_tags=("communication", "calendar"),
        forbidden_terms=("sendMessage", "createEvent"),
    )

    assert parsed.valid is False
    assert parsed.status == FALLBACK_STATUS
    assert parsed.selected_family_tags == ("communication", "calendar")
    assert raw not in parsed.canonical_json
    assert all(
        term not in parsed.canonical_json.casefold()
        for term in ("tool", "gold", "sample", "secret", "sendmessage")
    )


def test_plan_contact_has_fixed_nonfinal_protocol_and_decoding() -> None:
    compiler = _Compiler()
    controller = G5AgentLoopController(
        compiler=compiler,
        snapshot=_snapshot(),
        speech_feature_tokens=2_000,
    )

    contact = controller.initial_contact(_context())

    instruction = contact.instruction.casefold()
    assert contact.decoding_params == {
        "max_tokens": PLAN_COMPLETION_TOKENS,
        "temperature": 0,
    }
    assert "original speech" in instruction
    assert "closed family taxonomy" in instruction
    assert "no tool names" in instruction
    assert "no final answer" in instruction
    assert "response_format" not in instruction
    assert "sample_id" not in instruction


def test_compile_is_contact_free_full_unranked_and_execute_is_sole_final() -> None:
    compiler = _Compiler()
    snapshot = _snapshot()
    controller = G5AgentLoopController(
        compiler=compiler,
        snapshot=snapshot,
        speech_feature_tokens=2_000,
    )
    context = _context()
    plan_contact = controller.initial_contact(context)

    advance = controller.advance(context, plan_contact, _plan_json())

    assert len(compiler.calls) == 1
    assert compiler.calls[0].selected_family_tags == (
        "communication",
        "calendar",
    )
    assert advance.transition.action_kind == "acquire"
    assert advance.transition.new_value_ids == (
        "value:communication:send",
        "value:calendar:create",
    )
    assert advance.transition.new_facet_ids == (
        "facet:communication",
        "facet:calendar",
    )
    assert len(advance.new_agent_states) == 1
    plan_state = advance.new_agent_states[0]
    assert plan_state.content == _plan_json()
    assert "private-sample-id" not in plan_state.content
    assert "sendMessage" not in plan_state.content
    assert len(plan_state.content.encode("ascii")) <= PLAN_STATE_ASCII_BYTE_CAP
    assert advance.next_contact is not None
    assert advance.next_contact.decoding_params == {
        "max_tokens": EXECUTE_COMPLETION_TOKENS,
        "temperature": 0,
    }
    assert "final" in advance.next_contact.instruction.casefold()
    assert controller.last_bundle is not None
    assert controller.last_bundle.selection_mode == "full-unranked-compatible"
    assert len(controller.last_bundle.render().encode("ascii")) <= BUNDLE_ASCII_BYTE_CAP

    final_context = _context(
        1,
        states=(plan_state,),
        values=advance.transition.new_value_ids,
        facets=advance.transition.new_facet_ids,
    )
    stopped = controller.advance(
        final_context,
        advance.next_contact,
        '[{"name":"sendMessage","arguments":{}}]',
    )
    assert stopped.next_contact is None
    assert stopped.final_response_contact_id == advance.next_contact.contact_id


def test_invalid_plan_compiles_fixed_fallback_once_without_retry() -> None:
    compiler = _Compiler()
    controller = G5AgentLoopController(
        compiler=compiler,
        snapshot=_snapshot(),
        speech_feature_tokens=2_000,
    )
    context = _context()
    contact = controller.initial_contact(context)

    advance = controller.advance(context, contact, "invalid and unrecoverable")

    assert len(compiler.calls) == 1
    assert compiler.calls[0].valid is False
    assert compiler.calls[0].selected_family_tags == compiler.fallback_family_tags
    assert advance.next_contact is not None
    assert advance.new_agent_states[0].content == (
        '{"operations":[],"status":"INVALID_FALLBACK"}'
    )


def test_bundle_refuses_incomplete_ranked_mismatched_or_synthetic_content() -> None:
    snapshot = _snapshot()
    context = _context()

    for compiler in (
        _Compiler(synthetic_literals=("example@example.com",)),
        _Compiler(),
    ):
        controller = G5AgentLoopController(
            compiler=compiler,
            snapshot=snapshot,
            speech_feature_tokens=2_000,
        )
        contact = controller.initial_contact(context)
        if not compiler.synthetic_literals:
            original = compiler.compile

            def mismatched(plan: ParsedPlan) -> CompiledFamilyBundle:
                bundle = original(plan)
                first = bundle.contracts[0]
                changed = CompiledContract(
                    contract_id=first.contract_id,
                    family_tag=first.family_tag,
                    facet_id=first.facet_id,
                    value_id=first.value_id,
                    content="A synthetic literal not present in the frozen snapshot.",
                )
                return CompiledFamilyBundle(
                    family_tags=bundle.family_tags,
                    contracts=(changed, *bundle.contracts[1:]),
                    complete=True,
                    selection_mode="full-unranked-compatible",
                )

            compiler.compile = mismatched  # type: ignore[method-assign]
        with pytest.raises(G5AgentLoopError, match="synthetic|snapshot"):
            controller.advance(context, contact, _plan_json())


def test_state_bundle_and_prompt_envelope_caps_fail_closed() -> None:
    compiler = _Compiler()
    snapshot = _snapshot()
    controller = G5AgentLoopController(
        compiler=compiler,
        snapshot=snapshot,
        speech_feature_tokens=PER_SLOT_PROMPT_TOKENS,
    )
    context = _context()
    with pytest.raises(G5AgentLoopError, match="prompt envelope"):
        controller.initial_contact(context)

    oversized = CompiledFamilyBundle(
        family_tags=("communication",),
        contracts=(
            CompiledContract(
                contract_id="contract:large",
                family_tag="communication",
                facet_id="facet:communication",
                value_id="value:communication:send",
                content="x" * (BUNDLE_ASCII_BYTE_CAP + 1),
            ),
        ),
        complete=True,
        selection_mode="full-unranked-compatible",
    )
    with pytest.raises(G5AgentLoopError, match="bundle byte cap"):
        oversized.validate(requested_family_tags=("communication",))


@dataclass(frozen=True)
class _Result:
    sample_id: str
    final_response_text: str
    contacts: tuple[object, ...]


def _summary(samples: tuple[Audio2ToolSample, ...], contacts: int = 2) -> object:
    return SimpleNamespace(
        agent_executor_id="openjiuwen-workflow-v1",
        results=tuple(
            _Result(sample.sample_id, "[]", tuple(object() for _ in range(contacts)))
            for sample in samples
        ),
    )


def test_run_boundary_uses_openjiuwen_two_contacts_slot2_queue4_and_trace_sink(
    tmp_path: Path,
) -> None:
    samples = _samples()
    adapter = G5AgentLoopAdapter(
        samples,
        split_id="g5-fixture",
        taxonomy=TAXONOMY,
    )
    calls: list[dict[str, object]] = []
    trace_sink = object()

    def runner(**kwargs):
        calls.append(kwargs)
        factory = kwargs["controller_registry"].resolve(kwargs["controller_policy_id"])
        assert isinstance(factory(samples[0].sample_id), G5AgentLoopController)
        return _summary(samples)

    summary = run_g5_agentloop(
        data_root=tmp_path,
        plan=object(),
        adapter=adapter,
        core_client=object(),
        knowledge_snapshot=_snapshot(),
        speech_packet_bindings={sample.sample_id: {} for sample in samples},
        speech_feature_tokens_by_sample={sample.sample_id: 2_000 for sample in samples},
        compiler=_Compiler(),
        trace_sink=trace_sink,
        agent_runner=runner,
    )

    assert len(summary.results) == len(samples)
    assert calls[0]["agent_executor_id"] == "openjiuwen-workflow-v1"
    assert calls[0]["max_contacts"] == 2
    assert calls[0]["slot_count"] == G5_SLOT_COUNT == 2
    assert calls[0]["queue_depth"] == G5_QUEUE_DEPTH == 4
    assert calls[0]["bootstrap_facet_ids"] == ()
    assert calls[0]["bootstrap_value_ids"] == ()
    assert calls[0]["trace_sink"] is trace_sink


def test_adapter_keeps_taxonomy_closed_and_original_speech_primary() -> None:
    sample = _samples(1)[0]
    adapter = G5AgentLoopAdapter(
        (sample,), split_id="g5-fixture", taxonomy=TAXONOMY
    )

    contract = adapter.build_task_contract(sample, object())
    prompt = adapter.assemble_prompt(sample, None)

    assert "communication=[send,reply]" in contract
    assert "calendar=[create,update]" in contract
    assert sample.sample_id not in contract
    assert "sendMessage" not in contract
    assert prompt[1]["content"][0]["media_relpath"] == sample.media_relpath
    assert adapter.score(sample, "[]") == {"scoring_deferred": True}
    assert adapter.extract_consumption(sample, None, "[]").records == ()
