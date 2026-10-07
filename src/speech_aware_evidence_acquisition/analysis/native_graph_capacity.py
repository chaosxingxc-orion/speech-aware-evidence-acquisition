"""Measured reachable native requests, with no duplicate synthetic history.

This stress rehearsal is not exhaustive over arbitrary future model strings.
The production runtime must still FIT every actual request before generation.
"""
import json
from pathlib import Path
from .native_graph_rehearsal import (
    FourPathResponder, ReviewOffResponder, rehearse_native_graph, rehearsal_profile,
    LEGACY_PROFILE, require_prepared_graph_artifacts,
)


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


def bounded_response_texts(tokens, *, targets, intents, roles=("perception", "reviewer", "solver")):
    """Fill legal role fields, never exceeding the registered 512-token output."""
    if ("reviewer" in roles and len(targets) != 2) or len(intents) != 3:
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
        if role not in roles:
            continue
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


def bounded_lookup_distinction(tokens, *, targets):
    """Measure the full canonical synthetic tool-call text within its output reserve."""
    def text(n):
        return json.dumps([{"name": "saea-tool-knowledge-target-lookup-v1", "arguments": {
            "store_id": "slot-contracts", "view": "text", "candidate_ids": targets + ["synthetic_extra_slot_type"],
            "distinction": "e" * n}}])
    low, high = 1, 512
    if tokens(text(low)) > 512:
        raise ValueError("Minimal legal Solver tool call exceeds its output reserve")
    while low < high:
        mid = (low + high + 1) // 2
        if tokens(text(mid)) <= 512:
            low = mid
        else:
            high = mid - 1
    return "e" * low, tokens(text(low))


def native_graph_capacity_budget(values, *, slot_value_count, intent_value_count,
                                 graph_rows=4, media_parts=1, profile=LEGACY_PROFILE):
    """Pure guarded-endpoint upper bound; no source bytes or tokenizer are consumed."""
    if (any(type(n) is not int or n < 1 for n in (slot_value_count, intent_value_count, graph_rows, media_parts))
            or graph_rows != 4):
        raise ValueError("Capacity budget requires positive source counts and four graph rows")
    config = rehearsal_profile(values, profile)
    lookup = config is not None and config.solver_tool_access is not None
    modes = 2 if config is None or lookup else 1
    captures = modes * (22 if config is None else 11 if lookup else 8)
    # Each binary search has a minimal check, ceil(log2(upper+1)) probes
    # and a final measurement. Full review: upper15/57/512; P/S:15/512.
    padding = modes * (26 if config is None else 18 + (12 if lookup else 0))
    measurement = captures * (media_parts + 2)  # template plus every text part
    return {"profile": profile, "graph_rows": graph_rows, "supply_modes": modes,
            "captured_requests": captures, "ranking_tokenizer_endpoints": slot_value_count + intent_value_count,
            "padding_tokenizer_endpoints": padding, "request_measurement_endpoints": measurement,
            "contact_cap": 1 + slot_value_count + intent_value_count + padding + measurement}


class CapacityResponder(FourPathResponder):
    """Use the proven four paths with bounded long role responses."""
    def __init__(self, sample_ids, targets, texts):
        super().__init__(sample_ids, targets)
        self.texts = texts

    def __call__(self, payload):
        result = super().__call__(payload)
        if result.get("tool_calls"):
            return result
        control = [h for h in payload["history"] if h.get("role") == "control"][-1]
        for role, text in self.texts.items():
            if ":" + role + ":" in control["contact_id"]:
                return {"role": "assistant", "content": text}
        return result


def validate_review_off_capture(proof, records, *, lookup):
    """Require inactive-role omission and accepted post-tool final custody."""
    import hashlib

    paths = proof["terminal_paths"]
    if len(paths) != 4 or [p["sample_id"] for p in paths] != list(proof["sample_ids"]):
        raise ValueError("Review-off proof must preserve its four ordered terminal rows")
    finals, post_tool = {}, 0
    for path in paths:
        sample = path["sample_id"]
        if path["role_visits"] != ["perception", "solver"] or path["planner_routes"]:
            raise ValueError("Review-off proof contains inactive Reviewer/Planner paths")
        row = [r for r in records if r["sample_id"] == sample]
        role_order = []
        for record in row:
            control = [h for h in record["payload"]["history"] if h.get("role") == "control"][-1]
            role, = [r for r in ("perception", "solver", "reviewer", "planner") if ":" + r + ":" in control["contact_id"]]
            role_order.append(role)
        if role_order not in (["perception", "solver"], ["perception", "solver", "solver"]):
            raise ValueError("Review-off capture violates active role/contact bounds")
        final = row[-1]
        accepted = path["accepted_solver_receipt"]["final_contact"]
        content = final["synthetic_response"].get("content")
        if (not isinstance(content, str) or final["synthetic_response"].get("tool_calls")
                or accepted["request_sha256"] != final["prepared_request_sha256"]
                or accepted["response_text_sha256"] != hashlib.sha256(content.encode()).hexdigest()):
            raise ValueError("Accepted final Solver custody differs from the captured answer")
        finals[sample] = accepted["request_sha256"]
        tool_messages = [m for m in final["request"]["messages"] if m.get("role") == "tool"]
        if len(row) == 3:
            calls = row[-2]["synthetic_response"].get("tool_calls", [])
            if (not lookup or len(calls) != 1 or len(tool_messages) != 1
                    or tool_messages[0].get("tool_call_id") != calls[0]["id"]
                    or final["request"].get("tool_choice") != "none" or final["request"].get("tools")):
                raise ValueError("Solver lookup lost its tool result or reserved final response")
            post_tool += 1
        elif tool_messages:
            raise ValueError("Opt-out path manufactured a hidden lookup")
    receipts = proof["tool_receipts"]
    if len(receipts) != (2 if lookup else 0) or post_tool != (3 if lookup else 0):
        raise ValueError("Review-off proof did not exercise the exact optional lookup paths")
    for receipt in receipts:
        source = [r for r in records if r["sample_id"] == receipt["sample_id"]
                  and r["prepared_request_sha256"] == receipt["source_request_sha256"]]
        if (receipt["source_authority_role"] != "solver" or len(source) != 1
                or not source[0]["synthetic_response"].get("tool_calls")):
            raise ValueError("Solver tool custody is not bound to its captured source")
    return {"post_tool_final_requests": post_tool, "accepted_final_request_sha256": finals}


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


def capacity_rehearsal_outputs(data_root, artifact_path):
    """Bind scratch identity to the whole DATA-relative artifact, not its leaf."""
    from ..core.preparation import digest
    root = Path(data_root).resolve()
    relative = Path(artifact_path).resolve().relative_to(root).as_posix()
    identity = digest({"schema": "saea-capacity-scratch-v1", "artifact": relative})
    return {mode: root / "wire-check" / ("capacity-" + identity + "-" + mode)
            for mode in ("new-acquisition", "wide-automatic-supply")}


def fit_native_graph(runtime, path, *, policy, graph_factory, contact_cap=2048, profile=LEGACY_PROFILE):
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
    profile_config = rehearsal_profile(values, profile)
    # Compare the execution configuration before any endpoint is authorized.
    probe = graph_factory()
    probe_context = probe.preparation_context()
    for key in ("policy", "native_episode", "phase_material", "phase_tools", "knowledge_stores",
                "native_prefix_slots", "native_node_batch", "native_node_pipeline", "native_role_query_placement",
                "native_graph_capacity_profile"):
        if digest(values.get(key)) != digest(probe_context["values"].get(key)):
            raise ValueError("Graph proof differs from capacity configuration: " + key)
    if len(probe_context["sample_ids"]) != 4 or not set(probe_context["sample_ids"]) <= set(context["sample_ids"]):
        raise ValueError("The four proof rows must belong to the registered capacity roster")
    require_prepared_graph_artifacts(probe)
    from .native_episode_dry_run import compose_dry_run
    compose_dry_run(probe, sample_limit=4)
    budget = None
    if profile_config is not None:
        binding = probe._knowledge_store_binding
        budget = native_graph_capacity_budget(values,
            slot_value_count=len(binding.store("slot-contracts").snapshot.values),
            intent_value_count=len(binding.store("intent-boundaries").snapshot.values), profile=profile)
        if type(contact_cap) is not int or contact_cap < budget["contact_cap"]:
            raise ValueError("Registered tokenizer budget is below the complete capacity upper bound")
    inputs = {"schema": "saea-native-graph-capacity-input-v1", "config_hash": runtime._composed.config_hash,
        "source_commit": require_clean_study_repo(runtime._repo_root),
        "graph_config_hash": probe._composed.config_hash, "roster": list(context["sample_ids"]),
        "output_reserve": 512, "structural_reserve": 2048,
        "method": "Actual production graph, longest released slot values and long bounded role replies"}
    if profile != LEGACY_PROFILE:
        inputs["rehearsal_profile"] = profile
        inputs["endpoint_budget"] = budget
        inputs["registered_contact_cap"] = contact_cap

    def produce():
        scratch = capacity_rehearsal_outputs(runtime._data_root, path)
        for output in scratch.values():
            if output.exists():
                raise ValueError('Capacity rehearsal output already exists: ' + str(output))
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
            modes = (("new-acquisition", targeted_values), ("wide-automatic-supply", set()))
            if profile_config is not None and not profile_config.solver_tool_access:
                modes = (("wide-automatic-supply", set()),)
            for mode, excluded in modes:
                chosen = choose(excluded)
                roles = ("perception", "solver") if profile_config is not None else ("perception", "reviewer", "solver")
                texts, response_counts = bounded_response_texts(tokens, targets=targets, intents=chosen, roles=roles)
                graph = graph_factory()
                roster = graph.preparation_context()["sample_ids"]
                output = scratch[mode]
                options = {}
                if profile_config is not None:
                    lookup = profile_config.solver_tool_access is not None
                    distinction = "Capacity rehearsal only."
                    if lookup:
                        distinction, response_counts["solver_tool_call"] = bounded_lookup_distinction(tokens, targets=targets)
                    responder = ReviewOffResponder(roster, targets, texts=texts, lookup=lookup, distinction=distinction)
                    options["profile"] = profile
                else:
                    responder = CapacityResponder(roster, targets, texts)
                proof = rehearse_native_graph(graph, session_path=directory / SESSION_RECEIPT_NAME,
                    respond=responder, output=output, **options)
                expected_calls = (2 if profile_config.solver_tool_access else 0) if profile_config is not None else 3
                if proof["terminal_rows"] != 4 or proof["synthetic_tool_calls"] != expected_calls:
                    raise ValueError("Graph capacity failed its four-path contract")
                records = [json.loads(line) for line in (output / "requests.jsonl").read_text().splitlines()]
                tool_results = [json.loads(m["content"]) for r in records for m in r["request"]["messages"]
                                if m.get("role") == "tool"]
                nonempty = [r for r in tool_results if r.get("evidence")]
                expected_values = values["phase_tools"][profile_config.role("solver").phase_id]["knowledge_value_limit"] if profile_config is not None and profile_config.solver_tool_access else 2
                has_lookup = profile_config is None or profile_config.solver_tool_access is not None
                if has_lookup and (not nonempty or any(len(r["evidence"]) != expected_values for r in nonempty)):
                    raise ValueError("Longest released two-value return was not exercised")
                if mode == "new-acquisition" and any(r["result"]["supply_disposition"] != "acquired" for r in nonempty):
                    raise ValueError("The acquisition stress values were already visible")
                measured = measure_captured_requests(client, records, media_marker=marker, speech_max=speech_max)
                capture_checks = {}
                if profile_config is not None:
                    capture_checks = validate_review_off_capture(proof, records, lookup=has_lookup)
                all_rows.extend({"mode": mode, **row} for row in measured)
                proofs.append({"mode": mode, "directory": str(output), "requests_sha256": proof["requests_sha256"],
                               "candidate_intents": chosen, "synthetic_response_tokens": response_counts,
                               "terminal_rows": proof["terminal_rows"], "synthetic_completions": proof["synthetic_completions"],
                               **({"synthetic_tool_calls": proof["synthetic_tool_calls"], **capture_checks} if profile_config is not None else {})})
            result = {"schema": "saea-native-graph-capacity-v1", "rows": all_rows, "proofs": proofs,
                "every_request_fits": all(r["fits"] for r in all_rows), "selected_slots": selected,
                "maximum_speech_tokens_over_roster": speech_max, "contacts": client.counts.total(),
                "generation_contacts": 0, "scientific_results_read": False,
                "scope": "Reachable graph stress with measured longest tool values, not an exhaustive bound over arbitrary future text. Exact native per-contact FIT remains mandatory."}
            if profile_config is not None:
                result["rehearsal_profile"] = profile
                result["endpoint_budget"] = budget
            return result
    path.parent.mkdir(parents=True, exist_ok=True)
    return prepare_artifact(path, kind="request-fit", inputs=inputs, producer=produce, contact_class="tokenizer")
