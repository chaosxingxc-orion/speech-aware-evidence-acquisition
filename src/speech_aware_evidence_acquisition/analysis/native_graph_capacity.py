"""Measured reachable native requests, with no duplicate synthetic history.

This stress rehearsal is not exhaustive over arbitrary future model strings.
The production runtime must still FIT every actual request before generation.
"""
import json
from pathlib import Path
from .native_graph_rehearsal import FourPathResponder, rehearse_native_graph


class FreshAuditConnections:
    """Do not reuse an HTTP socket across the long model-free graph walk.

    Create one shared-client instance per endpoint and close it afterward.
    A failed endpoint propagates immediately; no request is retried.
    """
    def __init__(self, factory):
        self.factory = factory

    def request_json(self, method, route, payload=None):
        client = self.factory()
        try:
            return client.request_json(method, route, payload)
        finally:
            connection = getattr(getattr(client, "local", None), "connection", None)
            if connection is not None:
                connection.close()


def bounded_response_texts(tokens, *, targets, intents):
    """Fill legal role fields, never exceeding the registered 512-token output."""
    if len(targets) != 2 or len(intents) != 3:
        raise ValueError("Capacity requires two slot targets and three intents")
    def perception(n):
        return json.dumps({"candidates": [{"intent_id": intent,
            "distinction": ("Synthetic distinction " + " evidence" * n)[:128],
            "evidence_refs": [], "unresolved_fields": []} for intent in intents]})
    def reviewer(n):
        return json.dumps({"findings": [{"kind": "boundary", "slot_types": targets,
            "draft_fragment": ("Synthetic fragment " + str(i) + " evidence" * n)[:256],
            "reason": ("Synthetic boundary " + str(i) + " evidence" * n)[:512]}
            for i in range(4)], "checked": ["Synthetic check " + str(i) for i in range(8)]})
    def solver(n):
        return "intent: " + intents[0] + "\nentities: none\nSynthetic structural explanation:" + " evidence" * n
    results, counts = {}, {}
    for role, build, upper in (("perception", perception, 15), ("reviewer", reviewer, 57), ("solver", solver, 512)):
        low, high = 0, upper
        if tokens(build(0)) > 512:
            raise ValueError("Minimal legal synthetic completion exceeds its budget")
        while low < high:
            mid = (low + high + 1) // 2
            if tokens(build(mid)) <= 512:
                low = mid
            else:
                high = mid - 1
        results[role] = build(low)
        counts[role] = tokens(results[role])
        if counts[role] > 512:
            raise ValueError("Synthetic completion exceeds the registered output budget")
    return results, counts


class CapacityResponder(FourPathResponder):
    """Use the proven four paths with bounded long role responses."""
    def __init__(self, sample_ids, targets, texts):
        super().__init__(sample_ids, targets)
        self.texts = texts

    def __call__(self, payload):
        result = super().__call__(payload)
        control = [h for h in payload["history"] if h.get("role") == "control"][-1]
        for role, text in self.texts.items():
            if ":" + role + ":" in control["contact_id"]:
                return {"role": "assistant", "content": text}
        return result


def measure_captured_requests(client, records, *, media_marker, speech_max, reserve=2048):
    """Measure unchanged actual wire bodies and one current completion reserve."""
    from ..core.preparation import measure_request
    rows = []
    for index, record in enumerate(records):
        body = record["request"]
        if body.get("max_tokens") != 512:
            raise ValueError("Preserve the full registered completion reserve")
        row = measure_request(client, body, media_marker=media_marker,
                              speech_tokens=(speech_max,), slot_tokens=24576)
        row.update(sample_id=record["sample_id"], captured_request_index=index,
                   additional_structural_reserve_tokens=reserve,
                   margin_after_structural_reserve=row["margin_tokens"] - reserve)
        row["fits"] = row["margin_after_structural_reserve"] >= 0
        rows.append(row)
    if not rows:
        raise ValueError("No reachable requests were captured")
    return rows


def fit_native_graph(runtime, path, *, policy, graph_factory, contact_cap=2048):
    """Use the shared lease and exposure guard for the separate FIT identity."""
    import os
    from ..core.bundle.git_commit import require_clean_study_repo
    from ..core.driver.speech_native import _LoopbackPromptAuditClient
    from ..core.preparation import digest, prepare_artifact
    from ..core.preparation_fit import GuardedTokenizer, packet_token_counts
    from ..core.session.worker import attach_worker_session
    from ..core.session.serving import SESSION_RECEIPT_NAME
    from ..core.session.resource_guard import assert_admission, resource_limits
    from ..rails.released_target_index import build_released_target_index

    context = runtime.preparation_context()
    values = context["values"]
    # Compare the execution configuration before any endpoint is authorized.
    probe = graph_factory()
    probe_context = probe.preparation_context()
    for key in ("policy", "native_episode", "phase_material", "phase_tools", "knowledge_stores",
                "native_prefix_slots", "native_node_batch", "native_role_query_placement"):
        if digest(values.get(key)) != digest(probe_context["values"].get(key)):
            raise ValueError("Graph proof differs from capacity configuration: " + key)
    if len(probe_context["sample_ids"]) != 4 or not set(probe_context["sample_ids"]) <= set(context["sample_ids"]):
        raise ValueError("The four proof rows must belong to the registered capacity roster")
    from .native_episode_dry_run import compose_dry_run
    compose_dry_run(probe, sample_limit=4)
    inputs = {"schema": "saea-native-graph-capacity-input-v1", "config_hash": runtime._composed.config_hash,
        "source_commit": require_clean_study_repo(runtime._repo_root),
        "graph_config_hash": probe._composed.config_hash, "roster": list(context["sample_ids"]),
        "output_reserve": 512, "structural_reserve": 2048,
        "method": "Actual production graph, longest released slot values and long bounded role replies"}

    def produce():
        runtime.authorize_preparation_contacts(contact_cap=contact_cap)
        directory, document, session = attach_worker_session(policy=policy,
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
                stream.flush()
                os.fsync(stream.fileno())
            client = GuardedTokenizer(FreshAuditConnections(lambda: _LoopbackPromptAuditClient(
                host=session.host, port=session.port, timeout_seconds=600)),
                guard=guard, contact_cap=contact_cap, contact_sink=record)
            marker = client.request_json("GET", "/props")["media_marker"]
            def tokens(text):
                return len(client.request_json("POST", "/tokenize", {"content": text,
                    "add_special": False, "parse_special": True})["tokens"])
            binding = probe._knowledge_store_binding
            legal = runtime._adapter.candidate_inventory().validate().candidate_ids
            slots = binding.store("slot-contracts")
            slot_index = build_released_target_index(slots, data_root=runtime._data_root,
                legal_candidate_ids=legal, target_axis="slot-type")
            intent_index = build_released_target_index(slots, data_root=runtime._data_root,
                legal_candidate_ids=legal)
            sizes = {v.value_id: tokens(binding.model_evidence_block("slot-contracts",
                local_evidence_id=v.value_id, content=v.content)["text"]) for v in slots.snapshot.values}
            ranked = sorted(((sizes[ids[0]], target, ids[0]) for target, ids in slot_index.mappings.items()),
                            key=lambda item: (-item[0], item[1]))
            selected = ranked[:2]
            targets = [r[1] for r in selected]
            targeted_values = {r[2] for r in selected}
            intents = binding.store("intent-boundaries")
            intent_sizes = {v.task_target: tokens(binding.model_evidence_block("intent-boundaries",
                local_evidence_id=v.value_id, content=v.content)["text"]) for v in intents.snapshot.values}
            def choose(exclude):
                remaining = [c for c in legal if not exclude.intersection(intent_index.mappings.get(c, ()))]
                chosen, included = [], set()
                for _ in range(3):
                    if not remaining:
                        raise ValueError("No legal three-candidate acquisition stress path")
                    pick = max(remaining, key=lambda c: (intent_sizes.get(c, 0) + sum(sizes[v] for v in
                        set(intent_index.mappings.get(c, ())) - included), c))
                    chosen.append(pick)
                    included.update(intent_index.mappings.get(pick, ()))
                    remaining.remove(pick)
                return chosen
            decoder, = {f.sha256 for f in session.model_files if "mmproj" not in Path(f.path).name.lower()}
            speech_max = max(sum(packet_token_counts({"speech_feature_parts": [{**d, "role": "query"}]},
                feature_root=Path(values["speech_feature_root"]), decoder_sha256=decoder))
                for d in runtime.speech_packet_bindings().values())
            proofs, all_rows = [], []
            for mode, excluded in (("new-acquisition", targeted_values), ("wide-automatic-supply", set())):
                chosen = choose(excluded)
                texts, response_counts = bounded_response_texts(tokens, targets=targets, intents=chosen)
                graph = graph_factory()
                roster = graph.preparation_context()["sample_ids"]
                output = runtime._data_root / "wire-check" / (path.parent.name + "-" + mode)
                proof = rehearse_native_graph(graph, session_path=directory / SESSION_RECEIPT_NAME,
                    respond=CapacityResponder(roster, targets, texts), output=output)
                if proof["terminal_rows"] != 4 or proof["synthetic_tool_calls"] != 3:
                    raise ValueError("Graph capacity failed its four-path contract")
                records = [json.loads(line) for line in (output / "requests.jsonl").read_text().splitlines()]
                tool_results = [json.loads(m["content"]) for r in records for m in r["request"]["messages"]
                                if m.get("role") == "tool"]
                nonempty = [r for r in tool_results if r.get("evidence")]
                if not nonempty or any(len(r["evidence"]) != 2 for r in nonempty):
                    raise ValueError("Longest released two-value return was not exercised")
                if mode == "new-acquisition" and any(r["result"]["supply_disposition"] != "acquired" for r in nonempty):
                    raise ValueError("The acquisition stress values were already visible")
                measured = measure_captured_requests(client, records, media_marker=marker, speech_max=speech_max)
                all_rows.extend({"mode": mode, **row} for row in measured)
                proofs.append({"mode": mode, "directory": str(output), "requests_sha256": proof["requests_sha256"],
                               "candidate_intents": chosen, "synthetic_response_tokens": response_counts,
                               "terminal_rows": proof["terminal_rows"], "synthetic_completions": proof["synthetic_completions"]})
            return {"schema": "saea-native-graph-capacity-v1", "rows": all_rows, "proofs": proofs,
                "every_request_fits": all(r["fits"] for r in all_rows), "selected_slots": selected,
                "maximum_speech_tokens_over_roster": speech_max, "contacts": client.counts.total(),
                "generation_contacts": 0, "scientific_results_read": False,
                "scope": "Reachable graph stress with measured longest tool values, not an exhaustive bound over arbitrary future text. Exact native per-contact FIT remains mandatory."}
    path.parent.mkdir(parents=True, exist_ok=True)
    return prepare_artifact(path, kind="request-fit", inputs=inputs, producer=produce, contact_class="tokenizer")
