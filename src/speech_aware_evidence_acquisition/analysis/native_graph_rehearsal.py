"""Model-free execution of the production native graph and request renderer.

Only synthetic assistant responses enter this proof. It never opens a model
socket, scores a row, seals a research manifest, or alters a registered attempt.
Request capture is a structural rehearsal, not a capacity certificate.
"""
from __future__ import annotations

import base64
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from ..core.preparation import PreparationError, canonical_bytes, digest

PREFIX = "SAEA-WIRE-CHECK-"
LEGACY_PROFILE = "legacy-four-path-v1"
REVIEW_OFF_PROFILE = "review-off-v1"


def require_prepared_graph_artifacts(runtime):
    """Verify pinned seeds before dry-run fallback, session attachment or FIT."""
    for report in runtime.verify_prepared_artifacts():
        if report["identity_ok"] is not True or report.get("seed_ok") is False:
            raise PreparationError(
                f"Native graph {report['key']} is unusable: {report.get('reason')}"
            )


def rehearsal_profile(values, profile):
    """Validate a prospective P/S graph before scratch or endpoint authorization."""
    declared = values.get("native_graph_capacity_profile", LEGACY_PROFILE)
    if declared not in (LEGACY_PROFILE, REVIEW_OFF_PROFILE) or declared != profile:
        raise ValueError("Requested native rehearsal profile differs from its declared config profile")
    if profile == LEGACY_PROFILE:
        return None
    if profile != REVIEW_OFF_PROFILE:
        raise ValueError("Unknown native rehearsal profile")
    from ..rails.controllers import default_phase_program
    from ..rails.native_episode_config import load_native_episode_config

    config = load_native_episode_config(values, default_phase_program(values["policy"]))
    if (config is None or config.review_loop_enabled or config.max_revisions != 0
            or config.role("perception").max_iterations != 1
            # NX programme E1, Perception node: a TEMPLATE branch group is the
            # same P/S graph with extra Perception and Solver contacts; any
            # other branch group (per-branch seeds and routers) stays outside.
            or (config.role("perception").perception_branches is not None
                and not config.role("perception").perception_branches.renders_unvaried_evidence)
            or config.role("solver").samples != 1
            # NX programme E1: a node-template arm group is a P/S graph with
            # extra Solver contacts and no extra node, so the review-off
            # rehearsal admits it; a SUPPLY-kind group (per-arm routers) stays
            # outside this profile.
            or (config.role("solver").supply_variants is not None
                and not config.role("solver").supply_variants.unvaried_evidence)
            or config.acquisition_enabled or config.refresh_action is not None or config.relisten_json is not None
            or config.role("solver").max_iterations != (2 if config.solver_tool_access else 1)
            or any(r.tool_names for r in config.roles if r.role_kind != "solver")):
        raise ValueError("Review-off rehearsal requires the declared simple P/S graph")
    return config


class ReviewOffResponder:
    """Four P/S paths: opt-out, empty result, rejected call and maximum lookup."""

    def __init__(self, sample_ids, targets, *, texts, lookup, distinction="Capacity rehearsal only."):
        if (len(sample_ids) != 4 or len(set(sample_ids)) != 4
                or (lookup and (len(targets) != 2 or len(set(targets)) != 2))
                or not isinstance(distinction, str) or not 0 < len(distinction) <= 512):
            raise ValueError("Review-off proof needs four rows and bounded distinct targets")
        self.modes = dict(zip(sample_ids, ("decline", "empty", "rejected", "lookup"), strict=True))
        self.targets, self.texts, self.lookup, self.distinction = list(targets), texts, lookup, distinction
        self.turns = Counter()

    def __call__(self, payload):
        sample = payload["sample_id"]
        control = [h for h in payload["history"] if h.get("role") == "control"][-1]
        role, = [r for r in ("perception", "solver", "reviewer", "planner") if ":" + r + ":" in control["contact_id"]]
        if role not in ("perception", "solver"):
            raise ValueError("Review-off rehearsal contacted an inactive role")
        if role == "solver":
            self.turns[sample] += 1
            mode = self.modes[sample]
            if self.lookup and mode != "decline" and self.turns[sample] == 1:
                targets = (["synthetic_absent_slot_type"] if mode == "empty" else
                           self.targets + ["synthetic_extra_slot_type"] if mode == "rejected" else self.targets)
                args = {"store_id": "slot-contracts", "view": "text", "candidate_ids": targets,
                        "distinction": self.distinction}
                return {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "synthetic-lookup", "type": "function", "function": {
                        "name": "saea-tool-knowledge-target-lookup-v1", "arguments": json.dumps(args)}}]}
        return {"role": "assistant", "content": self.texts[role]}


class FourPathResponder:
    """Four fixed structural paths; no sampled answer or label is consumed."""

    def __init__(self, sample_ids, target_types):
        if len(sample_ids) != 4 or len(set(sample_ids)) != 4 or len(target_types) != 2:
            raise ValueError("Four distinct rows and two released slot types are required")
        self.modes = dict(zip(sample_ids, ("decline", "empty", "lookup", "revision"), strict=True))
        self.targets = list(target_types)
        self.turns = Counter()

    def __call__(self, payload):
        sample = payload["sample_id"]
        control = [item for item in payload["history"] if item.get("role") == "control"][-1]
        phase, = [role for role in ("perception", "solver", "reviewer", "planner")
                  if ":" + role + ":" in control["contact_id"]]
        text = {
            "perception": json.dumps({"candidates": [{"intent_id": "calendar_query",
                "distinction": "Synthetic branch rehearsal only.",
                "evidence_refs": [], "unresolved_fields": []}]}),
            "solver": "intent: calendar_query\nentities: none",
            "reviewer": json.dumps({"findings": [{"kind": "boundary", "slot_types": self.targets,
                "draft_fragment": "", "reason": "Synthetic type-boundary question; no spoken value is asserted."}],
                "checked": ["No task answer or label is used in this rehearsal."]}),
            "planner": "ACCEPT",
        }[phase]
        if phase == "planner":
            self.turns[sample] += 1
            turn = self.turns[sample]
            mode = self.modes[sample]
            if mode != "decline" and turn == 1:
                arguments = {"store_id": "slot-contracts", "view": "text",
                             "candidate_ids": (["synthetic_absent_slot_type"] if mode == "empty" else self.targets),
                             "distinction": "Synthetic capacity rehearsal of a type boundary only."}
                return {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "synthetic-lookup", "type": "function",
                    "function": {"name": "saea-tool-knowledge-target-lookup-v1",
                                 "arguments": json.dumps(arguments)}}]}
            if mode == "revision" and turn == 2:
                text = "REVISE"
        return {"role": "assistant", "content": text}



class RehearsalTransport:
    """Expose rendering only; no reference to a live dispatch callable."""

    def __init__(self, render, respond):
        self.render_request = render
        self.respond = respond
        self.records = []

    def __call__(self, raw):
        payload = json.loads(raw)
        message = self.respond(payload)
        if message.get("role") != "assistant":
            raise ValueError("Synthetic response must be an assistant message")
        calls = message.get("tool_calls")
        text = message.get("content")
        finish = "tool_calls" if calls else "stop"
        if calls:
            text = json.dumps([{"name": c["function"]["name"],
                               "arguments": json.loads(c["function"]["arguments"])}
                              for c in calls])
        elif not isinstance(text, str):
            raise ValueError("Synthetic assistant content must be text")
        request = self.render_request(raw)
        wire = canonical_bytes({"choices": [{"message": message, "finish_reason": finish}],
                                "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
        envelope = {"text": text, "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                    "wire_response_b64": base64.b64encode(wire).decode("ascii"),
                    "wire_response_sha256": hashlib.sha256(wire).hexdigest(),
                    "wire_finish_reason": finish}
        if calls:
            envelope["tool_calls"] = calls
        self.records.append({"sample_id": payload.get("sample_id"),
                             "payload": payload, "request": request,
                             "synthetic_response": message,
                             "prepared_request_sha256": hashlib.sha256(raw).hexdigest(),
                             "rendered_request_sha256": digest(request)})
        return canonical_bytes(envelope)


def synthetic_tool_contact(run_id, packets, record, facts):
    """Account released, deterministic lookup in a scratch attempt only."""
    from ..rails.native_tool_authority import validate_native_tool_authority
    from ..rails.hashing import content_hash
    if not run_id.startswith(PREFIX):
        raise ValueError("Synthetic tool custody requires a scratch run")
    authority = validate_native_tool_authority(facts.get("source_authority"))
    call, = authority["original_assistant_message"]["tool_calls"]
    fields = {"phase_id": "phase", "sample_id": "sample_id", "request_id": "request_id",
              "source_response_text_sha256": "source_response_sha256",
              "source_tool_calls_sha256": "tool_calls_sha256", "role_id": "source_authority_role"}
    if any(authority[key] != facts.get(value) for key, value in fields.items()):
        raise ValueError("Synthetic tool authority differs from its action")
    if (call["id"] != facts["tool_call_id"]
            or call["function"]["name"] != facts["tool_id"]
            or json.loads(call["function"]["arguments"]) != facts["arguments"]):
        raise ValueError("Synthetic tool arguments differ from their completion")
    packet = packets[facts["sample_id"]]
    record(count=1)
    return {"schema": "saea-native-phase-tool-contact-v2",
            **{k: facts[k] for k in ("sample_id", "phase", "next_phase", "tool_id",
                                   "source_response_sha256", "request_id",
                                   "tool_call_id", "tool_calls_sha256")},
            "arguments_sha256": digest(facts["arguments"]),
            "speech_packet_id": packet["packet_id"], "speech_packet_sha256": packet["sha256"],
            "source_authority_role": authority["role_id"],
            "source_authority_sha256": content_hash(authority),
            "source_request_sha256": authority["source_request_sha256"],
            "source_completion_sha256": authority["completion_sha256"]}


def rehearse_native_graph(runtime, *, session_path: Path, respond, output: Path, profile=LEGACY_PROFILE):
    """Run the complete configured roster with canned responses, never generation.

    Pass a fresh runtime. The role graph, state sealing, selection, tool
    dispatch, history projection and terminal delivery are production code.
    Scratch traces and request bodies are confined to DATA/wire-check.
    This function deliberately has no scorer or model-contact option.
    """
    from .native_episode_dry_run import compose_dry_run
    from ..core.configured_transport import build_configured_transport
    from ..core.flight.runtime import WireCheckGate
    from ..core.session import attach_session
    from ..rails.core_client import FrozenCoreClient
    from ..rails.phase_tools import build_phase_tools
    if runtime._client is not None or runtime._plan is not None:
        raise ValueError("Use a fresh runtime for synthetic rehearsal")
    context = runtime.preparation_context()
    if context["execution_plan"].split_role != "discovery":
        raise ValueError("Synthetic rehearsal permits discovery rosters only")
    values = context["values"]
    profile_config = rehearsal_profile(values, profile)
    require_prepared_graph_artifacts(runtime)
    tool_names = {name for spec in values.get("phase_tools", {}).values()
                  for name in spec.get("allowed_tools", ())}
    expected_tools = (set() if profile_config is not None and not profile_config.solver_tool_access
                      else {"saea-tool-knowledge-target-lookup-v1"})
    if tool_names != expected_tools:
        raise ValueError("Rehearsal permits only the released knowledge lookup")
    if values.get("live_speech_observations") or values.get("prepared_execution_units"):
        raise ValueError("Rehearsal does not admit live observations or execution units")
    output = Path(output).resolve()
    scratch_root = (runtime._data_root / "wire-check").resolve()
    if not output.is_relative_to(scratch_root) or output.exists():
        raise ValueError("Use a fresh output under DATA/wire-check")
    session = attach_session(session_path, runtime_receipt=context["runtime_receipt"],
                             runtime_root=runtime._runtime_root)
    renderer = build_configured_transport(values, runtime._data_root,
        repo_root=runtime._repo_root, session=session,
        runtime_receipt=context["runtime_receipt"], runtime_root=runtime._runtime_root)
    composed = compose_dry_run(runtime, sample_limit=len(context["sample_ids"]))
    suffix = uuid4().hex
    plan = replace(runtime._plan, run_id=PREFIX + "NATIVE-REHEARSAL-" + suffix,
                   attempt_id="attempt-wire-check-" + suffix,
                   planned_model_calls=len(context["sample_ids"]) * composed["program"].max_contacts)
    runtime._plan = plan
    runtime._phase_program_material = composed["phase_binding"]
    packets = runtime.speech_packet_bindings()
    tool_receipts = []
    def tool_contact(**facts):
        receipt = synthetic_tool_contact(plan.run_id, packets, runtime._client.record_tool_call, facts)
        tool_receipts.append(receipt)
        return receipt
    def tool_builder(*args, **kwargs):
        kwargs["tool_contact"] = tool_contact
        return build_phase_tools(*args, **kwargs)
    runtime._phase_tool_builder = tool_builder
    runtime._prepare_native_phase_runtime(composed["policy"])
    transport = RehearsalTransport(renderer.render_request, respond)
    runtime._transport = transport
    run_dir = scratch_root / plan.run_id / plan.attempt_id
    runtime._client = FrozenCoreClient(**runtime.frozen_core_client_kwargs(
        plan=plan, gate=WireCheckGate(), transport=transport, run_dir=run_dir))
    try:
        rows, contacts, _, dispatch, phases = runtime._dispatch_phase_program(
            runtime._client, plan, composed["policy"], model_free_check=True)
    finally:
        try:
            runtime._client.close()
        finally:
            runtime._abort_attempt(runtime._data_root, plan.run_id, plan.attempt_id,
                                   reason="Synthetic native graph rehearsal; zero model contacts")
    output.mkdir(parents=True)
    request_path = output / "requests.jsonl"
    with request_path.open("x") as stream:
        for record in transport.records:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    receipt = {"schema": "saea-native-graph-rehearsal-v1", "synthetic": True,
               "config_hash": runtime._composed.config_hash, "source_run_id": runtime.run_id,
               "scratch_run_id": plan.run_id, "scratch_attempt_id": plan.attempt_id,
               "sample_ids": context["sample_ids"], "terminal_rows": len(rows),
               "synthetic_completions": contacts, "synthetic_tool_calls": len(tool_receipts),
               "requests_sha256": hashlib.sha256(request_path.read_bytes()).hexdigest(),
               "tool_receipts": tool_receipts, "dispatch": dispatch, "phases": phases,
               "generation_contacts": 0, "tokenizer_contacts": 0, "official_score_jobs": 0,
               "capacity_verified": False, "scientific_results_read": False}
    if profile != LEGACY_PROFILE:
        receipt["rehearsal_profile"] = profile
    receipt["terminal_paths"] = [
        {"sample_id": row["sample_id"],
         "role_visits": [v["role_id"] for v in row["native_episode_receipt"]["role_visits"]],
         "planner_routes": row["native_episode_receipt"]["planner_routes"],
         "terminal_disposition": row["native_episode_receipt"].get("terminal_disposition"),
         "accepted_solver_receipt": row["native_episode_receipt"].get("accepted_solver_receipt")}
        for row in rows]
    (output / "receipt.json").write_bytes(canonical_bytes(receipt))
    return receipt

