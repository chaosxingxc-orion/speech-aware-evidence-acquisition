"""Exercise guarded capacity production with synthetic sources and endpoints only."""
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

from speech_aware_evidence_acquisition.analysis import native_graph_capacity as cap
from test_review_off_capacity import captured_proof


@pytest.mark.parametrize("lookup", [False, True])
@pytest.mark.parametrize("short_budget", [False, True])
def test_producer_uses_exact_declared_budget_and_proves_maximum_return(tmp_path, monkeypatch, lookup, short_budget):
    import speech_aware_evidence_acquisition.analysis.native_episode_dry_run as dry
    import speech_aware_evidence_acquisition.core.bundle.git_commit as gc
    import speech_aware_evidence_acquisition.core.driver.speech_native as driver
    import speech_aware_evidence_acquisition.core.preparation_fit as pf
    import speech_aware_evidence_acquisition.core.session.worker as worker
    import speech_aware_evidence_acquisition.core.session.resource_guard as resource
    import speech_aware_evidence_acquisition.rails.released_target_index as index
    from speech_aware_evidence_acquisition.rails.consumption_module import compile_module
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.phase_material import load_phase_material_specs

    leaf = "prepared-solver-lookup-policy-v1.json" if lookup else "prepared-review-off-policy-v1.json"
    v = json.loads((Path(__file__).resolve().parents[2] / "docs/readiness/2026-10-07-slurp-simple-consumption-direction-v1" / leaf).read_text())
    block = v["native_episode"]["consumption_module"]
    v = compile_module(block, carrier_module_hooks()).apply_to(v)
    v["native_episode"]["consumption_module"] = block
    v.update(carrier_lock_key="slurp", native_graph_capacity_profile="review-off-v1")
    components = v["native_episode"]["consumption_module"]["components"]
    opportunity = next(c for c in components if c["component_id"] == "knowledge-consumption-opportunity")
    assert opportunity["params"]["reviewer_response_format_id"] == "saea-slot-review-handoff-v1"
    material = load_phase_material_specs(v, default_phase_program(v["policy"]))
    assert material["reviewer"].response_format_id is None
    v["speech_feature_root"] = str(tmp_path)
    slots = NS(snapshot=NS(values=[NS(value_id="a", content="long " * 200), NS(value_id="b", content="long " * 150),
                                    NS(value_id="c", content="small")]))
    intents = NS(snapshot=NS(values=[NS(value_id=s, task_target=s, content="intent") for s in "xyz"]))
    binding = NS(store=lambda name: slots if name == "slot-contracts" else intents,
                 model_evidence_block=lambda name, **kw: {"text": kw["content"]})
    context = {"values": v, "sample_ids": list("abcd"), "data_root": tmp_path, "runtime_root": tmp_path,
               "run_id": "capacity-FIT-V1", "attempt_id": "attempt", "required_identity": {}, "runtime_receipt": {}}
    inventory = NS(validate=lambda: NS(candidate_ids=list("xyz")))
    authorizations, guards, endpoints = [], [], []
    runtime = NS(preparation_context=lambda: context, _data_root=tmp_path, _repo_root=tmp_path,
                 verify_prepared_artifacts=lambda: (),
                 _composed=NS(config_hash="c" * 64), _knowledge_store_binding=binding,
                 _adapter=NS(candidate_inventory=lambda: inventory),
                 speech_packet_bindings=lambda: {"a": {"packet_id": "packet", "sha256": "d" * 64}},
                 authorize_preparation_contacts=lambda **kw: authorizations.append(kw["contact_cap"]))
    monkeypatch.setattr(gc, "require_clean_study_repo", lambda _: "a" * 40)
    monkeypatch.setattr(dry, "compose_dry_run", lambda *a, **kw: None)
    monkeypatch.setattr(pf, "packet_token_counts", lambda *a, **kw: (7,))
    monkeypatch.setattr(resource, "resource_limits", lambda _: None)
    monkeypatch.setattr(index, "build_released_target_index", lambda *a, **kw:
                        NS(mappings={"person": ("a",), "place": ("b",)} if kw.get("target_axis") else
                           {s: ("c",) for s in "xyz"}))
    session = NS(host="synthetic", port=1, model_files=[NS(path="decoder", sha256="d" * 64)])
    monkeypatch.setattr(worker, "attach_worker_session", lambda **kw: (tmp_path, {}, session))
    path = tmp_path / "capacity.json"
    class Client:
        def request_json(self, method, route, payload=None):
            assert guards and path.with_name(path.name + ".contacts.jsonl").read_text().strip()
            endpoints.append(route)
            if route == "/props":
                return {"media_marker": "MEDIA"}
            if route == "/apply-template":
                return {"prompt": "synthetic MEDIA context"}
            assert route == "/tokenize"
            return {"tokens": [0] * (len(payload["content"]) // 4 + 1)}
    monkeypatch.setattr(driver, "_LoopbackPromptAuditClient", lambda **kw: Client())
    def rehearse(graph, *, respond, output, **kw):
        assert kw["profile"] == "review-off-v1"
        assert respond.lookup is lookup
        proof, records = captured_proof(lookup)
        if lookup:
            records[-1]["request"]["messages"][0]["content"] = json.dumps({"evidence": [
                {"content": slots.snapshot.values[i].content} for i in (0, 1)],
                "result": {"supply_disposition": "acquired"}})
        output.mkdir(parents=True)
        (output / "requests.jsonl").write_text("\n".join(json.dumps(r) for r in records))
        return {**proof, "terminal_rows": 4, "synthetic_tool_calls": 2 if lookup else 0,
                "synthetic_completions": len(records), "requests_sha256": "a" * 64}
    monkeypatch.setattr(cap, "rehearse_native_graph", rehearse)
    budget = cap.native_graph_capacity_budget(v, slot_value_count=3, intent_value_count=3,
                                            profile="review-off-v1")
    if short_budget:
        with pytest.raises(ValueError, match="budget"):
            cap.fit_native_graph(runtime, path, policy=NS(assert_lease=lambda *a, **kw: guards.append(True)),
                                 graph_factory=lambda: runtime, contact_cap=1, profile="review-off-v1")
        assert not authorizations and not endpoints and not path.exists()
        return
    cap.fit_native_graph(runtime, path, policy=NS(assert_lease=lambda *a, **kw: guards.append(True)),
                         graph_factory=lambda: runtime, contact_cap=budget["contact_cap"], profile="review-off-v1")
    result = json.loads(path.read_text())["output"]
    assert result["contacts"] == len(endpoints) <= budget["contact_cap"]
    assert authorizations == [budget["contact_cap"]]
    assert result["generation_contacts"] == 0 and result["scientific_results_read"] is False
    assert len(result["rows"]) == budget["captured_requests"]
    assert all(p["post_tool_final_requests"] == (3 if lookup else 0) for p in result["proofs"])
    assert all(r["maximum_completion_tokens"] == 512 for r in result["rows"])


@pytest.mark.usefixtures("_spawn_live_matching_process")
def test_shared_solver_receives_two_released_values_then_reserved_final_answer(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
    from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
        build_intent_boundary_snapshot, build_slot_contract_snapshot,
    )
    from test_semantic_knowledge_build import _spec, _slot, _intent
    from test_candidate_semantic_supply import _store
    import test_solver_tool_consumption_runtime as shared

    def binding(path):
        stores = {}
        for store_id, builder, rows, sample in (
            ("intent-boundaries", build_intent_boundary_snapshot, [_intent()], "train-1"),
            ("slot-contracts", build_slot_contract_snapshot, [_slot(), _slot("event_name")], "train-2"),
        ):
            snapshot = builder(_spec(permitted_source_sample_ids=(sample,)), rows=rows)
            source = {"schema": "saea-authored-semantic-knowledge-source-v1",
                      "builder_policy_id": snapshot.builder_policy_id,
                      "source_split_identity_hash": snapshot.source_split_identity_hash, "rows": rows}
            stores[store_id] = _store(path, store_id, store_id, snapshot, source)
        return load_knowledge_store_binding({"knowledge_stores": stores}, data_root=path)
    monkeypatch.setattr(shared, "_binding", binding)
    harness = shared.harness_for(tmp_path, monkeypatch, arguments={"store_id": "slot-contracts", "view": "text",
        "candidate_ids": ["event_time", "event_name"], "distinction": "Read both fixed slot meanings."})
    try:
        result = harness.run().results[0]
    finally:
        receipt = harness.close()
    final = harness.prepared[("s1", "solver", 1, 2)]["rendered"]
    tool = json.loads(next(m["content"] for m in final["messages"] if m["role"] == "tool"))
    assert len(tool["evidence"]) == 2
    assert receipt["request_count"] == 3 and len(harness.tool_contacts) == 1
    assert final["tool_choice"] == "none" and not final.get("tools")
    assert [v["stage"] for v in result.native_episode_receipt["role_visits"]] == ["perception", "solver"]
    final_contact = result.native_episode_receipt["accepted_solver_receipt"]["final_contact"]
    assert final_contact == harness.traced_contact(final_contact["agent_contact_id"])
