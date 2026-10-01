"""Nongenerative context stress rehearsal beside exact per-contact FIT.

This is a measured envelope, not a claim that one artificial string bounds every
possible tokenization of future model outputs. Exact native FIT remains mandatory.
No generated task answer, gold, score, test row or optimizer feedback is read.
"""
import copy
import json


def stress_body(messages, tools, values, contacts, completion):
    """Keep all supplied material and add the full episode's bounded history."""
    body = {"messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools),
            "max_tokens": completion}
    # Measured by the live tokenizer below; do not use character/token estimates.
    for index in range(contacts):
        body["messages"].append({"role": "assistant", "content": " evidence" * completion})
    body["messages"][-1]["tool_calls"] = [{"id": "capacity-lookup", "type": "function",
        "function": {"name": "saea-tool-knowledge-target-lookup-v1", "arguments":
                     '{"store_id":"slot-contracts","view":"text","candidate_ids":["type_a","type_b"],"distinction":"Capacity rehearsal only."}'}}]
    body["messages"].append({"role": "tool", "tool_call_id": "capacity-lookup",
        "content": json.dumps({"result": {"store_id": "slot-contracts", "supply_disposition": "acquired"},
                               "evidence": [{"content": text} for text in values]}, sort_keys=True)})
    body["messages"].append({"role": "user", "content":
        "Complete the next registered role after the knowledge result and Solver revision. "
        "This request is a capacity-only envelope and must never be sent to generation."})
    return body


def fit_stress(runtime, path, *, policy, contact_cap, attach=None):
    """Use the shared lease, exposure guard, session identity and tokenizer."""
    import os
    from pathlib import Path
    from ..core.bundle.git_commit import require_clean_study_repo
    from ..core.driver.speech_native import _LoopbackPromptAuditClient
    from ..core.preparation import canonical_bytes, digest, measure_request, prepare_artifact
    from ..core.preparation_fit import GuardedTokenizer, packet_token_counts
    from ..core.session.worker import attach_worker_session
    from ..core.session.resource_guard import assert_admission, resource_limits
    from ..rails.controllers import default_phase_program
    from ..rails.phase_tools import build_phase_tools

    context = runtime.preparation_context()
    values = context["values"]
    program = default_phase_program(str(values["policy"]))
    envelopes = runtime._phase_prompt_payloads(runtime._samples, program)
    binding = runtime._knowledge_store_binding
    store = binding.store("slot-contracts")
    visible = [binding.model_evidence_block("slot-contracts", local_evidence_id=v.value_id,
                content=v.content)["text"] for v in store.snapshot.values]
    def reject_tool_contact(*args, **kwargs):
        raise ValueError("Capacity rehearsal must never execute a tool")
    dispatcher = build_phase_tools(values, program, snapshot=binding.composite_snapshot,
                                   knowledge_stores=binding, tool_contact=reject_tool_contact)
    schemas = dispatcher.native_tool_schemas()
    inputs = {"schema": "saea-system-text-capacity-input-v1", "config_hash": runtime._composed.config_hash,
        "source_commit": require_clean_study_repo(runtime._repo_root),
        "envelopes": {k: digest(json.loads(v)) for k, v in envelopes.items()},
        "knowledge_sha256": store.snapshot.content_hash(), "tool_schemas_sha256": digest(schemas),
        "roster": list(context["sample_ids"]), "history_contacts": 13, "output_reserve": 512}

    def produce():
        runtime.authorize_preparation_contacts(contact_cap=contact_cap)
        directory, document, session = (attach or attach_worker_session)(policy=policy,
            data_root=context["data_root"], run_id=context["run_id"], attempt_id=context["attempt_id"],
            required_identity=context["required_identity"], runtime_receipt=context["runtime_receipt"],
            runtime_root=context["runtime_root"])
        limits = resource_limits(values)
        def guard():
            policy.assert_lease(context["data_root"], run_id=context["run_id"], attempt_id=context["attempt_id"])
            if limits is not None:
                assert_admission(directory, session, limits)
        journal = Path(str(path) + ".contacts.jsonl")
        with journal.open("x") as stream:
            def record(method, route):
                stream.write(json.dumps({"run_id": context["run_id"], "attempt_id": context["attempt_id"],
                    "method": method, "route": route, "contact": client.counts.total()}, sort_keys=True) + "\n")
                stream.flush(); os.fsync(stream.fileno())
            decoder = {f.sha256 for f in session.model_files if "mmproj" not in Path(f.path).name.lower()}
            if len(decoder) != 1:
                raise ValueError("Expected one decoder")
            bindings = runtime.speech_packet_bindings()
            speech_max = max(sum(packet_token_counts({"speech_feature_parts": [{**descriptor, "role": "query"}]},
                feature_root=Path(values["speech_feature_root"]), decoder_sha256=next(iter(decoder))))
                for descriptor in bindings.values())
            client = GuardedTokenizer(_LoopbackPromptAuditClient(host=session.host, port=session.port,
                timeout_seconds=600), guard=guard, contact_cap=contact_cap, contact_sink=record)
            marker = client.request_json("GET", "/props")["media_marker"]
            def tokens(text):
                return len(client.request_json("POST", "/tokenize", {"content": text,
                    "add_special": False, "parse_special": True})["tokens"])
            ranked = sorted(((tokens(text), text) for text in visible), key=lambda pair: (-pair[0], pair[1]))
            selected = [text for _, text in ranked[:2]]
            padding_tokens = tokens(" evidence" * 512)
            if padding_tokens < 512:
                raise ValueError("Synthetic history padding does not cover the declared completion reserve")
            rows = []
            for phase, raw in envelopes.items():
                body = stress_body(json.loads(raw), schemas, selected, 13, 512)
                row = measure_request(client, body, media_marker=marker, speech_tokens=(speech_max,),
                                      slot_tokens=24576)
                # Cover native limits, tool metadata, normalized Reviewer projection
                # and native-history serialization beyond the padded role contents.
                row["additional_structural_reserve_tokens"] = 2048
                row["margin_after_structural_reserve"] = row["margin_tokens"] - 2048
                row["fits"] = row["margin_after_structural_reserve"] >= 0
                rows.append({"phase": phase, **row})
            return {"schema": "saea-system-text-capacity-stress-v1", "rows": rows,
                "every_request_fits": all(r["fits"] for r in rows), "selected_value_tokens": [n for n, _ in ranked[:2]],
                "history_padding_tokens_per_contact": padding_tokens, "history_contacts": 13,
                "maximum_speech_tokens_over_roster": speech_max, "contacts": client.counts.total(),
                "generation_contacts": 0, "scientific_results_read": False,
                "scope": "Real-tokenizer conservative branch stress, not exhaustive certification of arbitrary future text. Native actual-request FIT remains mandatory."}
    path.parent.mkdir(parents=True, exist_ok=True)
    return prepare_artifact(path, kind="request-fit", inputs=inputs, producer=produce, contact_class="tokenizer")
