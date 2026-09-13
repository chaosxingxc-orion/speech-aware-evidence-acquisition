"""Named knowledge stores retain independent pins through shared retrieval."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.controllers import PhaseSupply
from speech_aware_evidence_acquisition.rails.knowledge import (
    FusionDecision,
    KnowledgeSnapshot,
    RankResult,
    RankedFacet,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    KnowledgeStoreError,
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.phase_tools import (
    PHASE_KNOWLEDGE_TOOL,
    PhaseToolError,
    build_phase_tools,
)
from test_phase_native_tools import Custody, NativeProgram, call, staged_native
from test_rails_runner import _knowledge_snapshot


def _write(path, document):
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _store_snapshot(store_id: str) -> KnowledgeSnapshot:
    source = _knowledge_snapshot()
    return replace(
        source,
        snapshot_id=f"{store_id}-v1",
        builder_policy_id=f"saea-{store_id}-builder-v1",
    ).validate()


def _config(tmp_path, store_ids=("intent-boundaries", "slot-contracts")):
    stores, snapshots = {}, {}
    for store_id in store_ids:
        snapshot = _store_snapshot(store_id)
        snapshot_relpath = f"knowledge/{store_id}/snapshot.json"
        snapshot_path = tmp_path / snapshot_relpath
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(snapshot.frozen_json()), encoding="utf-8")
        source_relpath = f"knowledge/{store_id}/construction-source.json"
        source_sha = _write(tmp_path / source_relpath, {"ids": ["train-source"]})
        release_relpath = f"knowledge/{store_id}/release.json"
        release = {
            "schema": "saea-knowledge-store-release-v1",
            "store_id": store_id,
            "store_role": store_id,
            "snapshot_sha256": snapshot.content_hash(),
            "source_split_identity_hash": snapshot.source_split_identity_hash,
            "builder_policy_id": snapshot.builder_policy_id,
            "source": {"relpath": source_relpath, "sha256": source_sha},
        }
        release_sha = _write(tmp_path / release_relpath, release)
        query_relpath = f"knowledge/{store_id}/query.jsonl"
        facet_relpath = f"knowledge/{store_id}/facets.jsonl"
        query_sha = _write(
            tmp_path / query_relpath, {"id": "s1", "vectors": {"operation": [1.0]}}
        )
        facet_sha = _write(
            tmp_path / facet_relpath,
            {"id": snapshot.facets[0].facet_id, "vectors": {"operation": [1.0]}},
        )

        def source(relpath, sha, signal):
            return {
                "kind": "sealed-vectors",
                "relpath": relpath,
                "sha256": sha,
                "tool_contact_ledger_row": "SYNTHETIC-NO-CONTACT",
                "embedded_signal": signal,
            }

        supply = {
            "provider": "kb-facet-v1",
            "rank_policy": "saea-rank-wcos-prior-agree-v1",
            "fuse_policy": "saea-fuse-supplyfilter-v1",
            "k": 1,
            "tau": 0.0,
            "dimensions": ["operation"],
            "query_source": source(query_relpath, query_sha, "speech: synthetic query"),
            "facet_source": source(facet_relpath, facet_sha, "text: synthetic facet"),
        }
        stores[store_id] = {
            "store_role": store_id,
            "snapshot": {
                "relpath": snapshot_relpath,
                "sha256": snapshot.content_hash(),
            },
            "release": {"relpath": release_relpath, "sha256": release_sha},
            "phase_supply": {"decision-2": supply, "final": supply},
        }
        snapshots[store_id] = snapshot
    return {"knowledge_stores": stores}, snapshots


def _supply(snapshot, context):
    facet, value = snapshot.facets[0].facet_id, snapshot.values[0].value_id
    rank = RankResult(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=context.query_state.content_hash(),
        ranking_policy_id="rank-v1",
        candidates=(RankedFacet(facet_id=facet, score=1.0),),
    ).validate()
    return PhaseSupply(
        rank_result=rank,
        fusion_decision=FusionDecision(
            snapshot_sha256=snapshot.content_hash(),
            query_state_sha256=context.query_state.content_hash(),
            rank_result_sha256=rank.content_hash(),
            fusion_policy_id="fuse-v1",
            supporting_facet_ids=(facet,),
            selected_value_ids=(value,),
        ).validate(),
    ).validate()


def test_loader_verifies_independent_release_snapshot_and_source_pins(tmp_path):
    config, snapshots = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    assert binding.store_ids == ("intent-boundaries", "slot-contracts")
    assert binding.snapshot_for("intent-boundaries") == snapshots["intent-boundaries"]
    assert binding.composite_snapshot.content_hash() == binding.binding_sha256
    assert len({value.value_id for value in binding.composite_snapshot.values}) == 2
    assert all("::" in value.value_id for value in binding.composite_snapshot.values)


@pytest.mark.parametrize("changed", ["snapshot", "release", "source"])
def test_loader_refuses_changed_or_missing_pins_before_returning_values(
    tmp_path, changed
):
    config, _ = _config(tmp_path, ("intent-boundaries",))
    spec = config["knowledge_stores"]["intent-boundaries"]
    if changed == "snapshot":
        spec["snapshot"]["sha256"] = "f" * 64
    elif changed == "release":
        spec["release"]["sha256"] = "f" * 64
    else:
        release = json.loads((tmp_path / spec["release"]["relpath"]).read_text())
        (tmp_path / release["source"]["relpath"]).write_text("changed")
    with pytest.raises(KnowledgeStoreError):
        load_knowledge_store_binding(config, data_root=tmp_path)


def test_loader_rejects_malformed_store_role(tmp_path):
    config, _ = _config(tmp_path)
    config["knowledge_stores"]["slot-contracts"]["store_role"] = "not a role"
    with pytest.raises(KnowledgeStoreError, match="role"):
        load_knowledge_store_binding(config, data_root=tmp_path)


def test_absent_stores_preserve_legacy_while_explicit_empty_refuses(tmp_path):
    assert load_knowledge_store_binding({}, data_root=tmp_path) is None
    with pytest.raises(KnowledgeStoreError, match="non-empty"):
        load_knowledge_store_binding({"knowledge_stores": {}}, data_root=tmp_path)


def _native_config(store_ids):
    return {
        "phase_tools": {
            phase: {
                "mode": "native-tools",
                "allowed_tools": [PHASE_KNOWLEDGE_TOOL],
                "knowledge_views": ["text"],
                "knowledge_store_ids": list(store_ids),
            }
            for phase in ("decision-1", "decision-2")
        }
    }


def test_native_model_selects_each_store_and_joint_history_keeps_both(tmp_path):
    config, snapshots = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    calls = []

    def supplied(store_id, phase, context):
        calls.append((store_id, phase))
        return _supply(snapshots[store_id], context)

    dispatcher = build_phase_tools(
        _native_config(binding.store_ids),
        NativeProgram(),
        snapshot=binding.composite_snapshot,
        knowledge_stores=binding,
        supply_for_store=supplied,
        tool_contact=Custody(),
    )
    schema = dispatcher.native_tool_schemas()[0]["function"]["parameters"]
    assert schema["properties"]["store_id"]["enum"] == list(binding.store_ids)
    first_context = staged_native(
        call(PHASE_KNOWLEDGE_TOOL, {"store_id": "intent-boundaries", "view": "text"})
    )
    first_context.knowledge_snapshot_sha256 = binding.binding_sha256
    first = dispatcher("decision-1", "decision-2", first_context)
    first_doc = json.loads(first.state.content)
    assert first_doc["result"]["store_id"] == "intent-boundaries"
    assert first_doc["result"]["store_snapshot_sha256"] == snapshots[
        "intent-boundaries"
    ].content_hash()
    assert first_doc["result"]["composite_snapshot_sha256"] == binding.binding_sha256
    assert first_doc["result"]["local_rank_sha256"] != first_doc["result"][
        "qualified_rank_sha256"
    ]
    second_context = staged_native(
        call(PHASE_KNOWLEDGE_TOOL, {"store_id": "slot-contracts", "view": "text"}),
        phase="decision-2",
        prior_states=(first.state,),
        query_state=replace(
            first_context.query_state,
            retrieved_value_ids=first.supply.fusion_decision.selected_value_ids,
        ),
    )
    second_context.knowledge_snapshot_sha256 = binding.binding_sha256
    second = dispatcher("decision-2", "final", second_context)
    assert calls == [("intent-boundaries", "decision-2"), ("slot-contracts", "final")]
    ids = (
        *first.supply.fusion_decision.selected_value_ids,
        *second.supply.fusion_decision.selected_value_ids,
    )
    query = replace(
        second_context.query_state,
        retrieved_value_ids=ids,
        agent_state_ids=(first.state.state_id, second.state.state_id),
    )
    blocks = dispatcher.render_values(
        binding.composite_snapshot, query, (first.state, second.state)
    )
    assert len(blocks) == 2
    assert {block["store_id"] for block in blocks} == {
        "intent-boundaries",
        "slot-contracts",
    }
    assert all("store_release_sha256=" in block["text"] for block in blocks)


def test_real_request_gate_retains_exact_qualified_store_evidence(tmp_path):
    from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
    from speech_aware_evidence_acquisition.rails.controllers import (
        EvidenceAgentController,
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
    from speech_aware_evidence_acquisition.rails.runner import (
        run_speech_native_agent_loop,
    )
    from test_native_agent_runner import _controller_registry
    from test_rails_frozen_core_client import (
        _World,
        _client,
        _plan,
        _speech_feature_world,
    )
    from test_rails_runner import _FakeAdapter

    config, _ = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    program = default_phase_program("native-answer-or-tool-v1")
    router = build_knowledge_store_supply(
        binding, program=program, data_root=tmp_path
    )
    dispatcher = build_phase_tools(
        _native_config(binding.store_ids),
        program,
        snapshot=binding.composite_snapshot,
        knowledge_stores=binding,
        supply_for_store=router,
        tool_contact=Custody(),
    )

    class StoreTransport:
        def __init__(self):
            self.calls = []

        def __call__(self, request_bytes):
            payload = json.loads(request_bytes)
            self.calls.append(payload)
            phase = payload["history"][-1]["contact_id"].rsplit(":", 1)[-1]
            if phase == "final":
                tool_calls, text = None, "final-answer"
            else:
                store = (
                    "intent-boundaries"
                    if phase == "decision-1"
                    else "slot-contracts"
                )
                tool_calls = [
                    {
                        "id": f"call-{phase}",
                        "type": "function",
                        "function": {
                            "name": PHASE_KNOWLEDGE_TOOL,
                            "arguments": json.dumps(
                                {"store_id": store, "view": "text"}, sort_keys=True
                            ),
                        },
                    }
                ]
                text = "tool"
            return json.dumps(
                {
                    "text": text,
                    "usage": {"prompt_tokens": 8, "completion_tokens": 4},
                    "tool_calls": tool_calls,
                }
            ).encode()

    world = _World(tmp_path / "world")
    feature_root, _packet, packet_bindings = _speech_feature_world(
        world, tmp_path / "world"
    )
    transport = StoreTransport()
    plan = _plan(planned_model_calls=3)
    client, _, _ = _client(
        world,
        tmp_path / "world",
        plan=plan,
        transport=transport,
        arm="speech-feature-query-native-tools",
        speech_feature_root=feature_root,
        speech_packet_bindings=packet_bindings,
        tool_schemas=list(dispatcher.native_tool_schemas()),
    )
    registry = _controller_registry(
        "named-stores-test-v1",
        lambda _sample_id: EvidenceAgentController(
            program=program,
            tools_for_phase=dispatcher,
            material_for_phase=lambda phase, context: PhaseMaterial(
                instruction="Use the named knowledge tools as needed.",
                response_format=None,
                contact_id=f"{context.sample_id}:{phase}",
                purpose=phase,
            ),
        ),
    )
    fitted = []
    try:
        summary = run_speech_native_agent_loop(
            data_root=world.data_root,
            plan=plan,
            adapter=_FakeAdapter(samples=(world.samples[0],)),
            core_client=client,
            split_id="all",
            knowledge_snapshot=binding.composite_snapshot,
            speech_packet_bindings={"s1": packet_bindings["s1"]},
            controller_policy_id="named-stores-test-v1",
            controller_registry=registry,
            max_contacts=3,
            slot_count=1,
            queue_depth=1,
            trace_sink=TraceBuffer(plan.run_id),
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params={"max_tokens": 256},
            request_batch_gate=lambda batch: fitted.append(
                tuple(request.as_payload() for request in batch)
            ),
            whole_roster_wave_barrier=True,
            knowledge_value_renderer=dispatcher.render_values,
        )
    finally:
        client.close()
    assert summary.results[0].final_response_text == "final-answer"
    assert len(fitted) == 3
    second_wire = json.dumps(fitted[1][0], sort_keys=True)
    final_wire = json.dumps(fitted[2][0], sort_keys=True)
    assert fitted[1][0]["supplied_evidence"] == transport.calls[1][
        "supplied_evidence"
    ]
    assert fitted[2][0]["supplied_evidence"] == transport.calls[2][
        "supplied_evidence"
    ]
    assert "intent-boundaries::" in second_wire
    assert "store_release_sha256=" in second_wire
    assert "intent-boundaries::" in final_wire
    assert "slot-contracts::" in final_wire
    assert final_wire.count("store_release_sha256=") == 2


def test_disallowed_store_and_cross_store_citation_refuse(tmp_path):
    config, snapshots = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    dispatcher = build_phase_tools(
        _native_config(("intent-boundaries",)),
        NativeProgram(),
        snapshot=binding.composite_snapshot,
        knowledge_stores=binding,
        supply_for_store=lambda _store, _phase, context: _supply(
            snapshots["slot-contracts"], context
        ),
        tool_contact=Custody(),
    )
    rejected = staged_native(
        call(PHASE_KNOWLEDGE_TOOL, {"store_id": "slot-contracts", "view": "text"})
    )
    rejected.knowledge_snapshot_sha256 = binding.binding_sha256
    assert (
        json.loads(dispatcher("decision-1", "decision-2", rejected).state.content)[
            "schema"
        ]
        == "saea-phase-tool-error-v1"
    )
    crossed = staged_native(
        call(PHASE_KNOWLEDGE_TOOL, {"store_id": "intent-boundaries", "view": "text"})
    )
    crossed.knowledge_snapshot_sha256 = binding.binding_sha256
    with pytest.raises(PhaseToolError, match="store"):
        dispatcher("decision-1", "decision-2", crossed)


def test_legacy_native_schema_and_result_bytes_are_unchanged():
    from test_phase_native_tools import dispatcher
    from test_rails_controllers import _phase_supply

    snapshot = _knowledge_snapshot()
    old = dispatcher(
        PHASE_KNOWLEDGE_TOOL,
        supply=lambda _phase, context: _phase_supply(
            context,
            value_ids=(snapshot.values[0].value_id,),
            facet_ids=(snapshot.facets[0].facet_id,),
        ),
    )
    parameters = old.native_tool_schemas()[0]["function"]["parameters"]
    assert set(parameters["properties"]) == {"view"}
    assert parameters["required"] == ["view"]
    context = staged_native(call(PHASE_KNOWLEDGE_TOOL, {"view": "text"}))
    document = json.loads(old("decision-1", "decision-2", context).state.content)
    assert "store_id" not in document["result"]


def test_flight_runtime_loads_named_releases_as_the_shared_snapshot(tmp_path):
    from test_flight_runtime import _make_runtime

    data_root = tmp_path / "data"
    data_root.mkdir()
    config, _ = _config(data_root)
    runtime = _make_runtime(
        tmp_path,
        config_kwargs={"baseline_extra": config},
    )
    runtime._prepare()
    snapshot = runtime._load_knowledge_snapshot()
    assert snapshot.content_hash() == runtime._knowledge_store_binding.binding_sha256
    assert runtime._knowledge_store_binding.store_ids == (
        "intent-boundaries",
        "slot-contracts",
    )


def test_named_prompt_bound_qualifies_and_retains_prior_store_evidence(tmp_path):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )

    config, _ = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    stub = SimpleNamespace(
        _composed=SimpleNamespace(values=config),
        _knowledge_store_binding=binding,
        _load_knowledge_snapshot=lambda: binding.composite_snapshot,
    )
    bound = FlightRuntime._phase_supply_prompt_bound(
        stub, default_phase_program("native-answer-or-tool-v1")
    )
    assert len(bound["decision-2"]) == 2
    assert len(bound["final"]) == 2
    final_text = "\n".join(text for text, _role in bound["final"])
    assert "intent-boundaries::" in final_text
    assert "slot-contracts::" in final_text
    assert final_text.count("store_release_sha256=") == 2


def test_shared_phase_supply_builds_and_routes_each_independent_store(tmp_path):
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from test_phase_tools import _context

    config, _ = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding,
        program=default_phase_program("native-answer-or-tool-v1"),
        data_root=tmp_path,
    )
    context = _context()
    intent = router("intent-boundaries", "decision-2", context)
    slot = router("slot-contracts", "decision-2", context)
    assert (
        intent.rank_result.snapshot_sha256
        == binding.snapshot_for("intent-boundaries").content_hash()
    )
    assert (
        slot.rank_result.snapshot_sha256
        == binding.snapshot_for("slot-contracts").content_hash()
    )
    assert (
        router.receipt["stores"]["intent-boundaries"]["store_release_sha256"]
        != router.receipt["stores"]["slot-contracts"]["store_release_sha256"]
    )


def test_flight_runtime_resolves_named_store_supply_without_a_launcher(tmp_path):
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from test_flight_runtime import _make_runtime

    data_root = tmp_path / "data"
    data_root.mkdir()
    config, _ = _config(data_root)
    config.update(_native_config(("intent-boundaries", "slot-contracts")))
    runtime = _make_runtime(
        tmp_path,
        config_kwargs={
            "policy": "native-answer-or-tool-v1",
            "arm": "speech-feature-query-native-tools",
            "baseline_extra": config,
        },
    )
    runtime._prepare()
    snapshot = runtime._load_knowledge_snapshot()
    supply, specs = runtime._resolve_phase_supply(
        default_phase_program("native-answer-or-tool-v1"), snapshot
    )
    assert supply is None
    assert set(specs) == {"decision-2", "final"}
    assert (
        runtime._knowledge_store_supply.receipt["binding_sha256"]
        == snapshot.content_hash()
    )
