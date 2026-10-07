"""Reward lineage consumes real verified synthetic bundles and saved native scores."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import test_bundle as bundle_fixtures

from speech_aware_evidence_acquisition.core.bundle import finalize_bundle, verify_bundle
from speech_aware_evidence_acquisition.core.roster import RosterItem, freeze_roster, write_roster
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    capture_score_source, write_complete_score_receipt,
)
from speech_aware_evidence_acquisition.rails.reward_links import (
    RewardLinkError, RewardProjection, build_experience_sources,
    build_reward_links, verify_reward_links, verify_experience_sources,
)

bundled_repo = bundle_fixtures.bundled_repo


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def completed_source(synthetic_world, bundled_repo, tmp_path):
    """Use the existing fake transport, actual bundle finalizer and real synthetic WER."""
    manifest, _, _, lock = bundle_fixtures._run_completed(
        synthetic_world, bundled_repo, tmp_path,
    )
    finalized = finalize_bundle(
        manifest, lock, synthetic_world.data_root, repo_root=bundled_repo[1],
        ledger_cells=bundle_fixtures._HUMAN_LEDGER_CELLS,
    )
    bundle = verify_bundle(manifest)
    assert bundle.attempt_state == "FINALIZED"
    scores = json.loads(finalized.scores_path.read_text())
    score_path = tmp_path / "first-score.json"
    score_path.write_text(json.dumps({
        "manifest": str(manifest), "verified": True, "scores": scores,
    }))
    ref = write_complete_score_receipt(
        tmp_path / "first-score-receipt.json", job_id="synthetic-native-first-score",
        result_path=score_path, source=capture_score_source(bundle),
        verified_bundle=bundle,
    )
    roster = freeze_roster(
        carrier_lock_key="earnings21-original",
        candidates=[RosterItem(sid, "synthetic") for sid in sorted(bundle.split_ids)],
        per_stratum=len(bundle.split_ids), seed=3, split_role="discovery",
        roster_id="synthetic-construction", roster_role="construction",
    )
    roster_path = tmp_path / "construction.json"
    write_roster(roster, roster_path)
    return manifest, ref, roster_path, bundle, score_path


def _projection():
    return RewardProjection(
        "native-synthetic-wer-v1", "asr-wer",
        ("mean_wer", "samples"),
        ("wer", "hits", "substitutions", "deletions", "insertions"),
    )


def test_complete_bundle_to_sources_preserves_native_feedback_and_raw_bytes(completed_source):
    manifest, ref, roster, bundle, score = completed_source
    paths = (manifest, bundle.outputs_path, score, ref.path, roster)
    before = {path: path.read_bytes() for path in paths}
    links = build_reward_links(manifest, ref, roster, _projection())
    assert len(links) == len(bundle.split_ids)
    assert set(link.source.source_sample_id for link in links) == bundle.split_ids
    outputs = {row["sample_id"]: row for row in bundle.outputs_rows}
    for link in links:
        sid = link.source.source_sample_id
        assert link.source.partition_role == "train"
        assert link.source.response_sha256 == outputs[sid]["response_text_sha256"]
        assert link.provenance["wire_response_sha256"] == outputs[sid]["response_sha256"]
        assert set(link.native_score_vector["per_sample"][sid]) == set(_projection().per_sample_fields)
        assert "token tags" not in json.dumps(link.as_json())
        assert all(event["axis"] in {"OBS", "ORG", "SUPPLY", "USE", "MODEL_REQUEST", "MODEL_RESPONSE", "COST"} for event in link.provenance["ordered_events"])
    assert verify_reward_links(links, manifest, ref, roster, _projection()) == links
    assert build_experience_sources(manifest, ref, roster, _projection()) == tuple(link.source for link in links)
    assert verify_experience_sources(links, manifest, ref, roster, _projection()) == tuple(link.source for link in links)
    assert all(path.read_bytes() == raw for path, raw in before.items())


@pytest.mark.parametrize("field", ["reference_words_text", "ref_hit_mask", "latency", "gold_id", "unknown_numeric"])
def test_reward_projection_refuses_undeclared_or_answer_bearing_fields(field):
    with pytest.raises(RewardLinkError):
        RewardProjection("bad", "asr-wer", ("mean_wer",), (field,))


def test_reward_projection_refuses_cost_and_unknown_scorers():
    for scorer in ("cost", "cost-v1", "unregistered-scorer"):
        with pytest.raises(RewardLinkError):
            RewardProjection("bad", scorer, ("mean",), ("mean",))


def test_slurp_projection_cannot_drop_native_sufficient_counts():
    with pytest.raises(RewardLinkError):
        RewardProjection("lossy", "slurp-slu-official", ("slu",), ("slu",))


@pytest.mark.parametrize("target", ["score", "receipt", "trace", "outputs"])
def test_mutated_source_is_rejected_by_real_upstream_verifiers(completed_source, target):
    manifest, ref, roster, bundle, score = completed_source
    paths = {
        "score": score, "receipt": ref.path,
        "trace": Path(bundle.manifest["raw_trace"]["path"]),
        "outputs": bundle.outputs_path,
    }
    path = paths[target]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises((RewardLinkError, ValueError, RuntimeError)):
        build_reward_links(manifest, ref, roster, _projection())


def test_evaluation_roster_cannot_become_reward_memory_source(completed_source):
    manifest, ref, roster, bundle, _ = completed_source
    evaluation = freeze_roster(
        carrier_lock_key="earnings21-original",
        candidates=[RosterItem(sid, "synthetic") for sid in sorted(bundle.split_ids)],
        per_stratum=len(bundle.split_ids), seed=3, split_role="discovery",
        roster_id="synthetic-evaluation", roster_role="evaluation",
    )
    other = roster.with_name("evaluation.json")
    write_roster(evaluation, other)
    with pytest.raises(RewardLinkError, match="construction"):
        build_reward_links(manifest, ref, other, _projection())


def test_changed_link_order_or_feedback_is_rejected(completed_source):
    manifest, ref, roster, _, _ = completed_source
    links = build_reward_links(manifest, ref, roster, _projection())
    with pytest.raises(RewardLinkError):
        verify_reward_links(tuple(reversed(links)), manifest, ref, roster, _projection())
    provenance = copy.deepcopy(dict(links[0].provenance))
    provenance["ordered_events"] = list(reversed(provenance["ordered_events"]))
    bad = replace(links[0], provenance=provenance)
    with pytest.raises(RewardLinkError):
        bad.validate()


def _slurp_source(completed_source, tmp_path, mode, *, native_framework=False,
                  carrier="slurp", sample_ids=None, scorer=None, score_function=None,
                  response_text=None, run_id="SAEA-SYNTHETIC-SLURP", trace_transform=None, session_receipt=None):
    """Build synthetic role traces; optional carriers reuse the same custody path."""
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan, TraceRecord
    from speech_aware_evidence_acquisition.core.attempts import AttemptStore
    from speech_aware_evidence_acquisition.core.config import protocol_hash
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
    from speech_aware_evidence_acquisition.core.model.native_framework_history import (
        framework_contact_instruction,
        native_tool_result_message,
    )
    from speech_aware_evidence_acquisition.rails.core_client import (
        CoreCompletion,
        _agent_history,
        _tool_schemas_sha256,
    )
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
    from speech_aware_evidence_acquisition.rails.native_tool_authority import (
        build_native_tool_authority,
    )
    from speech_aware_evidence_acquisition.rails.phase_tools import (
        CANDIDATE_CONTRACT_TOOL,
        TASK_CONTRACT_TOOL,
        _native_tool_schema,
    )
    from speech_aware_evidence_acquisition.rails.reward_links import SLURP_NATIVE_FIELDS

    _, _, _, seed_bundle, _ = completed_source
    root = tmp_path / (carrier + "-synthetic")
    root.mkdir()
    ids = sample_ids or ("slurp:train:1", "slurp:train:10")
    scorer = scorer or "slurp-slu-official-train"
    attempt_id = "synthetic-attempt"
    split_hash = split_identity_hash(prefixed(carrier, ids))
    stages = ([("perception", 0), ("solver", 0), ("reviewer", 0),
               ("reviewer", 1), ("planner", 0), ("solver", 1),
               ("reviewer", 2), ("reviewer", 3), ("planner", 1)]
              if mode == "native" else [(name, None) for name in ("plan", "solve", "revise")])
    call_count = len(ids) * len(stages)
    config_hash = content_hash({"synthetic": "three-phase"})
    protocol = protocol_hash(config_hash, "bare-core", split_hash)
    plan = ExecutionPlan(
        run_id=run_id, attempt_id=attempt_id, execution_profile="bounded-discovery-probe",
        carrier_lock_key=carrier, split_role="discovery", split_identity_hash=split_hash,
        planned_model_calls=call_count + 1, planned_gpu_hours=1, planned_speech_audio_seconds=60,
        protocol_hash=protocol,
    )
    handle = AttemptStore(root / "attempts").open_attempt(
        run_id, attempt_id, carrier_lock_key=carrier, reserved_calls=call_count + 1, reserved_audio_seconds=60,
    )
    documents, outputs, hashes = [], [], {}

    def emit(axis, rid, payload):
        record = TraceRecord(axis, rid, payload)
        documents.append(record.serialize())
        hashes[rid] = record.content_hash()

    def native_tool_state(*, sid, index, rid, cid, payload, text, iteration):
        """Build the real native custody shapes without contacting a service."""
        tool_id = TASK_CONTRACT_TOOL if iteration == 0 else CANDIDATE_CONTRACT_TOOL
        arguments = {} if tool_id == TASK_CONTRACT_TOOL else {
            "candidate_ids": ["synthetic-candidate-marker"],
        }
        schema = _native_tool_schema(
            tool_id, ("text",),
            candidate_limit=3 if tool_id == CANDIDATE_CONTRACT_TOOL else None,
        )
        calls = [{
            "id": f"synthetic-native-call-{index}-{iteration}",
            "type": "function",
            "function": {
                "name": tool_id,
                "arguments": json.dumps(arguments, sort_keys=True, separators=(",", ":")),
            },
        }]
        raw_calls = json.dumps(calls, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        assistant = {"role": "assistant", "content": text, "tool_calls": calls}
        wire = json.dumps({"choices": [{
            "message": assistant, "finish_reason": "tool_calls",
        }]}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        request_hash = content_hash(payload)
        completion = CoreCompletion(
            text=text, request_id=rid, sample_id=sid, agent_contact_id=cid,
            request_sha256=request_hash, response_sha256=hashlib.sha256(wire).hexdigest(),
            response_text_sha256=text_hash, tool_calls_json=raw_calls.encode("utf-8"),
            wire_response_bytes=wire, tool_names=(tool_id,),
            tool_schemas_sha256=_tool_schemas_sha256([schema]),
        )
        authority = build_native_tool_authority(
            completion, role_id="reviewer", phase_id="reviewer",
            selected_tool_schemas=[schema],
        )
        query_hash = content_hash({"query_sample_id": sid})
        source = AgentStateArtifact(
            state_id=f"phase:reviewer:{rid}", state_kind="phase:reviewer",
            content=text, source_query_state_sha256=query_hash,
            source_response_sha256=text_hash,
            producer_policy_id="synthetic-native-framework-v1", cited_value_ids=(),
        ).validate()
        result = {
            "evidence_id": f"synthetic-contract-evidence-{index}-{iteration}",
            "source_uri": f"synthetic-task-contract://opaque/{index}/{iteration}",
            "contract_status": "synthetic-contract-confirmed",
            "evidence_marker": "synthetic-task-contract-evidence-marker",
        }
        blocks = [{
            "type": "text", "evidence_id": result["evidence_id"],
            "source_uri": result["source_uri"],
            "text": "Synthetic task-contract evidence marker.",
        }]
        packet = payload["speech_feature_parts"][0]
        invocation = {
            "schema": "saea-native-phase-tool-contact-v2",
            "sample_id": sid, "phase": "reviewer", "next_phase": "reviewer",
            "tool_id": tool_id, "source_response_sha256": text_hash,
            "tool_call_id": calls[0]["id"],
            "tool_calls_sha256": completion.tool_calls_sha256,
            "speech_packet_id": packet["packet_id"],
            "speech_packet_sha256": packet["sha256"], "request_id": rid,
            "arguments_sha256": hashlib.sha256(
                json.dumps(arguments, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "source_authority_sha256": content_hash(authority),
            "source_authority_role": "reviewer",
            "source_request_sha256": authority["source_request_sha256"],
            "source_completion_sha256": authority["completion_sha256"],
        }
        document = {
            "schema": "saea-phase-tool-result-v2", "selection_mode": "native-tools",
            "tool_id": tool_id, "arguments": arguments,
            "query_state_sha256": query_hash, "source_response_sha256": text_hash,
            "snapshot_sha256": "a" * 64,
            "tool_source_sha256": "93b2f93e56c66cca66c1af79402395198bba6848e057c116811abc1c2018066a",
            "tool_call_id": calls[0]["id"], "tool_calls_sha256": completion.tool_calls_sha256,
            "core_request_id": rid, "sample_id": sid, "phase": "reviewer",
            "next_phase": "reviewer", "speech_packet_id": packet["packet_id"],
            "speech_packet_sha256": packet["sha256"],
            "native_source_state_id": source.state_id,
            "native_tool_calls_json": raw_calls, "source_authority": authority,
            "source_authority_sha256": content_hash(authority),
            "tool_invocation": invocation, "native_result_content": blocks,
            "native_result_content_sha256": content_hash({"blocks": blocks}),
            "result": result, "result_sha256": content_hash(result),
        }
        tool = AgentStateArtifact(
            state_id=f"tool-result:reviewer:{sid}:{iteration}", state_kind="tool-result",
            content=json.dumps(document, sort_keys=True),
            source_query_state_sha256=query_hash, source_response_sha256=text_hash,
            producer_policy_id="synthetic-native-framework-v1", cited_value_ids=(),
        ).validate()
        return completion, source, tool, document

    for index, sid in enumerate(ids):
        phase_contacts, phase_states = [], []
        native_artifacts, native_tool_documents, native_tool_artifacts = [], {}, {}
        for phase, iteration in stages:
            rid = f"opaque-{index}-{phase}" + (f"-{iteration}" if iteration is not None else "")
            cid = f"synthetic-program:{phase}:" + (f"{iteration}:" if iteration is not None else "") + sid
            text = f"synthetic-answer-{index}-{phase}" + (f"-{iteration}" if iteration is not None else "")
            if response_text is not None:
                text = response_text(sid, phase, iteration)
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            is_native_role = native_framework and mode == "native"
            is_native_reviewer = is_native_role and phase == "reviewer"
            is_native_tool_source = is_native_reviewer and iteration in (0, 2)
            if is_native_role:
                system = (
                    "Apply the synthetic SLU task contract."
                    if is_native_reviewer
                    else f"Perform the synthetic {phase} role."
                )
                query = (
                    "Review the Solver draft against the synthetic task contract."
                    if is_native_reviewer
                    else f"Perform the synthetic {phase} role for this utterance."
                )
                previous = native_tool_documents.get(iteration - 1) if is_native_reviewer else None
                local_ids = [] if previous is None else [
                    native_tool_artifacts[iteration - 1].state_id,
                ]
                framework_messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": query},
                ]
                if previous is not None:
                    framework_messages.extend([
                        dict(previous["source_authority"]["original_assistant_message"]),
                        native_tool_result_message(previous),
                    ])
                contact_instruction = framework_contact_instruction(
                    role_id=phase, sample_id=sid, contact_id=cid,
                    messages=framework_messages, local_tool_result_ids=local_ids,
                )
                payload = {
                    "sample_id": sid, "request_id": rid, "carrier_lock_key": carrier,
                    "task_instruction": system,
                    "speech_feature_parts": [{
                        "packet_id": f"synthetic-query-packet-{index}",
                        "sha256": hashlib.sha256(
                            f"synthetic-query-packet-{index}".encode()
                        ).hexdigest(),
                        "role": "query",
                    }],
                    "history": _agent_history(
                        agent_state=[artifact.as_json() for artifact in native_artifacts],
                        agent_contact_id=cid, contact_instruction=contact_instruction,
                    ),
                    "tool_schemas": (
                        [_native_tool_schema(
                            TASK_CONTRACT_TOOL if iteration == 0 else CANDIDATE_CONTRACT_TOOL,
                            ("text",),
                            candidate_limit=3 if iteration == 2 else None,
                        )] if is_native_tool_source else []
                    ),
                    "decoding_params": {
                        "tool_choice": "auto" if is_native_tool_source else "none",
                        "parallel_tool_calls": False,
                    },
                }
            else:
                payload = {
                    "sample_id": sid, "request_id": rid, "carrier_lock_key": carrier,
                    "history": [{"role": "control", "contact_id": cid}],
                }
            wire_hash = content_hash({"wire": text})
            native_completion = None
            if is_native_tool_source:
                native_completion, source_state, tool_state, tool_document = native_tool_state(
                    sid=sid, index=index, rid=rid, cid=cid, payload=payload, text=text,
                    iteration=iteration,
                )
                wire_hash = native_completion.response_sha256
            emit("MODEL_REQUEST", rid + "/request", {
                "arm": "bare-core", "payload": payload, "payload_sha256": content_hash(payload),
            })
            emit("MODEL_RESPONSE", rid + "/response", {
                "text": text, "response_sha256": wire_hash, "response_text_sha256": text_hash,
            })
            phase_contacts.append({"plan": {"contact_id": cid}, "response_sha256": text_hash})
            if mode == "native":
                if native_framework:
                    raw_calls = (
                        native_completion.tool_calls_json.decode("utf-8")
                        if native_completion is not None else "[]"
                    )
                    emit("TOOL", rid + "/native-completion", {
                        "schema": "saea-native-completion-v1",
                        "request_id": rid, "sample_id": sid, "agent_contact_id": cid,
                        "request_sha256": content_hash(payload),
                        "response_sha256": wire_hash,
                        "response_text_sha256": text_hash,
                        "native_tool_calls_json": raw_calls,
                        "native_tool_calls_sha256": hashlib.sha256(raw_calls.encode()).hexdigest(),
                    })
                emit("USE", rid + "/native-role-contact", {
                    "use_role_id": phase, "use_agent_contact_id": cid,
                    "use_request_sha256": content_hash(payload),
                    "use_response_sha256": wire_hash,
                    "use_response_text_sha256": text_hash,
                })
                if phase == "reviewer" and iteration in (0, 2):
                    call_id = (
                        native_completion.tool_calls[0]["id"]
                        if native_completion is not None else f"call-{iteration}"
                    )
                    suffix = content_hash({"request_id": rid, "tool_call_id": call_id})
                    emit("USE", f"{sid}/synthetic-program/{phase}/tool-result/{suffix}", {
                        "use_tool_id": (
                            native_completion.tool_names[0]
                            if native_completion is not None else "saea-tool-task-contract-v1"
                        ),
                        "use_core_request_id": rid, "use_tool_call_id": call_id,
                        "use_sample_id": sid, "use_phase": phase,
                        "use_source_response_sha256": text_hash,
                    })
                    if native_completion is not None:
                        native_artifacts.extend((source_state, tool_state))
                        native_tool_documents[iteration] = tool_document
                        native_tool_artifacts[iteration] = tool_state
            if phase != "revise":
                phase_states.append({"state_kind": "phase:" + phase,
                                     "source_response_sha256": text_hash})
            if mode == "separate":
                emit("ORG", f"{sid}/{phase}/agent-loop/org", {
                    "org_initial_query_state": {"query_sample_id": sid},
                    "org_final_query_state": {"query_sample_id": sid},
                })
                emit("USE", f"{sid}/{phase}/agent-loop/runtime-use", {
                    "use_contacts": [phase_contacts[-1]],
                    "use_final_response_sha256": text_hash,
                })
            if phase == "solve":
                emit("OBS", f"{sid}/synthetic-program/{phase}/tool-result", {
                    "obs_tool_id": "saea-tool-prepared-speech-observation-v1",
                    "obs_tool_manifest_sha256": "a" * 64,
                })
                emit("REVIEW", f"{sid}/synthetic-program/{phase}/review", {
                    "review_sample_id": sid, "review_phase": phase,
                    "review_response_sha256": text_hash,
                })
            if phase == "revise" or (mode == "native" and phase == "solver" and iteration == 1):
                selected_hash, selected_contact_id = text_hash, cid
                outputs.append({
                    "sample_id": sid, "request_id": rid, "carrier_lock_key": carrier,
                    "arm": "bare-core", "text": text, "admitted": True,
                    "request_sha256": content_hash(payload), "response_sha256": wire_hash,
                    "response_text_sha256": text_hash,
                })
        if mode in {"continuous", "native"}:
            base = f"{sid}/synthetic-program/agent-loop"
            query = {"query_sample_id": sid}
            emit("ORG", base + "/org", {
                "org_initial_query_state": query, "org_final_query_state": query,
                "org_agent_states": phase_states,
            })
            runtime_document = {
                "controller_policy_id": "synthetic-program",
                "agent_executor_id": "synthetic-executor", "agent_executor_version": "1",
                "knowledge_snapshot_sha256": "a" * 64,
                "initial_query_state_sha256": content_hash(query),
                "final_query_state_sha256": content_hash(query),
                "speech_packet_sha256": "b" * 64,
                "contacts": phase_contacts,
                "waves": [{"contact_plans": [contact["plan"]],
                           "response_sha256s": [contact["response_sha256"]],
                           "selected_final_contact_id": contact["plan"]["contact_id"]
                           if contact is phase_contacts[-1] else None}
                          for contact in phase_contacts],
                "transitions": [], "final_response_sha256": selected_hash,
            }
            if mode == "native":
                runtime_document["waves"] = [{
                    "contact_plans": [contact["plan"] for contact in phase_contacts],
                    "response_sha256s": [contact["response_sha256"] for contact in phase_contacts],
                    "selected_final_contact_id": selected_contact_id,
                }]
            runtime_hash = content_hash(runtime_document)
            emit("USE", base + "/runtime-use", {
                **{"use_" + key: value for key, value in runtime_document.items()},
                "use_runtime_trace_sha256": runtime_hash,
            })
            emit("USE", base + "/posthoc-use", {
                "use_runtime_trace_sha256": runtime_hash,
                "use_final_response_sha256": selected_hash, "use_metrics": {},
            })
    # A global event must stay source-bound without being assigned to either row.
    emit("TOOL", "global/tool-registry", {"tool_manifest_sha256": "b" * 64})
    if trace_transform is not None:
        rows, outputs = trace_transform([json.loads(row) for row in documents], outputs)
        documents = [TraceRecord(row["channel"], row["record_id"], row["payload"]).serialize()
                     for row in rows]
        hashes = {row["record_id"]: TraceRecord(
            row["channel"], row["record_id"], row["payload"]).content_hash() for row in rows}
        call_count = sum(row["channel"] == "MODEL_REQUEST" for row in rows)
    files = {
        "outputs": root / "outputs.jsonl",
        "raw_trace": root / "trace.jsonl",
        "trace_manifest": root / "trace-manifest.json",
    }
    files["outputs"].write_text("".join(json.dumps(row) + "\n" for row in outputs))
    files["raw_trace"].write_text("\n".join(documents) + "\n")
    files["trace_manifest"].write_text(json.dumps({"records": hashes}))
    manifest = copy.deepcopy(seed_bundle.manifest)
    manifest.update(
        run_id=run_id, exposure_run_id=run_id, protocol_hash=protocol,
        plan=vars(plan), config={"config_hash": config_hash, "fragments": {}},
        split={"carrier_lock_key": carrier, "ids": list(ids), "count": len(ids),
               "name": "synthetic-construction", "role": "discovery", "identity_hash": split_hash},
        attempt={"run_id": run_id, "attempt_id": attempt_id, "state_path": str(handle.path)},
        scorers=[scorer], scores=None,
    )
    if session_receipt is not None:
        manifest["session_receipt"] = session_receipt
    manifest["cost"]["calls_used"] = call_count
    for key, path in files.items():
        manifest[key] = {"path": str(path), "sha256": _sha(path)}
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest))
    handle.mark_finalized()
    bundle = verify_bundle(path)
    per_sample = [
        {"sample_id": sid, **{field: (index + 1 if field.endswith(("_tp", "_fp", "_fn")) else index)
                             for field in SLURP_NATIVE_FIELDS}}
        for index, sid in enumerate(ids)
    ]
    score = root / "score.json"
    scored = (score_function(files["outputs"]) if score_function is not None else
              {"aggregate": {"port_micro": {"samples": 2}}, "per_sample": per_sample})
    score.write_text(json.dumps({
        "manifest": str(path), "verified": True,
        "scores": {scorer: scored},
    }))
    ref = write_complete_score_receipt(
        root / "receipt.json", job_id="synthetic-slurp-score", result_path=score,
        source=capture_score_source(bundle), verified_bundle=bundle,
    )
    roster = freeze_roster(
        carrier_lock_key=carrier, candidates=[RosterItem(sid, "synthetic") for sid in ids],
        per_stratum=len(ids), seed=3, split_role="discovery",
        roster_id="synthetic-slurp-train", roster_role="construction",
    )
    roster_path = root / "roster.json"
    write_roster(roster, roster_path)
    if carrier == "audio2tool":
        from speech_aware_evidence_acquisition.rails.reward_links import A2T_NATIVE_FIELDS
        projection = RewardProjection("synthetic-a2t-official-v1", scorer,
                                      ("samples", "tool_accuracy", "exact_match", "param_f1"), A2T_NATIVE_FIELDS)
    else:
        projection = RewardProjection("slurp-native-v1", scorer,
                                      ("port_micro.samples",), SLURP_NATIVE_FIELDS)
    return path, ref, roster_path, projection, per_sample



@pytest.fixture(params=("separate", "continuous"))
def slurp_source(completed_source, tmp_path, request):
    return _slurp_source(completed_source, tmp_path, request.param)


@pytest.fixture
def native_slurp_source(completed_source, tmp_path):
    return _slurp_source(completed_source, tmp_path, "native")


@pytest.fixture
def native_training_slurp_source(completed_source, tmp_path):
    """Opt-in source with actual framework envelopes and native tool custody."""
    return _slurp_source(
        completed_source, tmp_path, "native", native_framework=True,
    )


def test_native_training_fixture_keeps_bound_framework_tool_custody(
    native_training_slurp_source,
):
    from speech_aware_evidence_acquisition.core.model.native_history import _bound_result

    path, _ref, _roster, _projection, _native = native_training_slurp_source
    manifest = json.loads(path.read_text())
    records = [
        json.loads(line) for line in Path(manifest["raw_trace"]["path"]).read_text().splitlines()
        if line
    ]
    requests = [
        row["payload"]["payload"] for row in records
        if row["channel"] == "MODEL_REQUEST"
    ]
    reviewer_continuation = next(
        payload for payload in requests
        if payload["request_id"].endswith("reviewer-1")
    )
    control = reviewer_continuation["history"][-1]
    envelope = json.loads(control["content"])
    assert envelope["schema"] == "saea-native-framework-contact-v1"
    assert [message["role"] for message in envelope["messages"]] == [
        "system", "user", "assistant", "tool",
    ]
    state_by_id = {
        state["state_id"]: state for state in reviewer_continuation["history"]
        if state["role"] == "agent_state"
    }
    tool_state = state_by_id[envelope["local_tool_result_ids"][0]]
    document, call, assistant = _bound_result(
        tool_state, state_by_id, set(), reviewer_continuation,
    )
    assert document["schema"] == "saea-phase-tool-result-v2"
    assert call["function"]["name"] == "saea-tool-task-contract-v1"
    assert assistant["tool_calls"] == [call]
    completion_rows = [
        row["payload"] for row in records
        if row["channel"] == "TOOL"
        and row["payload"].get("schema") == "saea-native-completion-v1"
    ]
    assert len(completion_rows) == 18
    request_by_id = {
        row["payload"]["payload"]["request_id"]: row["payload"]
        for row in records if row["channel"] == "MODEL_REQUEST"
    }
    response_by_id = {
        row["record_id"].removesuffix("/response"): row["payload"]
        for row in records if row["channel"] == "MODEL_RESPONSE"
    }
    assert all(
        row["request_sha256"] == request_by_id[row["request_id"]]["payload_sha256"]
        and row["response_sha256"] == response_by_id[row["request_id"]]["response_sha256"]
        and row["response_text_sha256"]
        == response_by_id[row["request_id"]]["response_text_sha256"]
        and hashlib.sha256(row["native_tool_calls_json"].encode()).hexdigest()
        == row["native_tool_calls_sha256"]
        for row in completion_rows
    )
    assert sum(row["native_tool_calls_json"] == "[]" for row in completion_rows) == 14


def test_native_role_revisits_keep_every_contact_and_accepted_solver(native_slurp_source):
    path, ref, roster, projection, native = native_slurp_source
    links = build_reward_links(path, ref, roster, projection)
    assert len(links) == 2
    for index, link in enumerate(links):
        events = link.provenance["ordered_events"]
        assert sum(event["axis"] == "MODEL_REQUEST" for event in events) == 9
        assert sum("/tool-result/" in event["record_id"] for event in events) == 2
        assert link.source.response_sha256 == hashlib.sha256(
            f"synthetic-answer-{index}-solver-1".encode()
        ).hexdigest()


def test_slurp_exact_sample_joins_keep_tools_reviews_and_sufficient_counts(slurp_source):
    path, ref, roster, projection, native = slurp_source
    links = build_reward_links(path, ref, roster, projection)
    native_by_id = {row["sample_id"]: row for row in native}
    for link in links:
        sid = link.source.source_sample_id
        events = link.provenance["ordered_events"]
        assert len([event for event in events if event["axis"] == "MODEL_REQUEST"]) == 3
        assert len([event for event in events if event["axis"] == "OBS"]) == 1
        assert len([event for event in events if event["axis"] == "REVIEW"]) == 1
        assert all(event["record_id"] != "global/tool-registry" for event in events)
        for key, value in link.native_score_vector["per_sample"][sid].items():
            assert value == native_by_id[sid][key]
        continuous = any(event["record_id"].endswith("/synthetic-program/agent-loop/org")
                         for event in events)
        assert len(link.provenance["ordered_actions"]) == (5 if continuous else 8)


def test_projection_round_trip_rejects_extra_fields():
    projection = _projection()
    assert RewardProjection.from_json(projection.as_json()) == projection
    with pytest.raises(RewardLinkError):
        RewardProjection.from_json({**projection.as_json(), "extra": "unbound"})


def _mutate_synthetic_trace(source, case):
    """Rebind intentionally malformed synthetic semantics without bypassing verification."""
    from speech_aware_evidence_acquisition.contracts import TraceRecord
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    path, _, roster, projection, _ = source
    assert path.parent.name == "slurp-synthetic"
    manifest = json.loads(path.read_text())
    trace_path = Path(manifest["raw_trace"]["path"])
    documents = [json.loads(line) for line in trace_path.read_text().split("\n") if line]
    by_id = {row["record_id"]: row for row in documents}
    sid, other = "slurp:train:1", "slurp:train:10"
    runtime_id = (f"{sid}/plan/agent-loop/runtime-use"
                  if f"{sid}/plan/agent-loop/runtime-use" in by_id
                  else f"{sid}/synthetic-program/agent-loop/runtime-use")
    use = by_id[runtime_id]["payload"]
    org = by_id[runtime_id.removesuffix("runtime-use") + "org"]["payload"]
    review = by_id.get(f"{sid}/synthetic-program/solve/review", {}).get("payload")
    solve_hash = by_id.get("opaque-0-solve/response", {}).get("payload", {}).get("response_text_sha256")
    if case.startswith("native_"):
        role = by_id["opaque-0-reviewer-0/native-role-contact"]["payload"]
        solver_hash = by_id["opaque-0-solver-0/response"]["payload"]["response_text_sha256"]
        tool = next(row["payload"] for row in documents
                    if row["record_id"].startswith(f"{sid}/synthetic-program/reviewer/tool-result/"))
        if case == "native_role":
            role["use_role_id"] = "solver"
        elif case == "native_contact_hash":
            role["use_request_sha256"] = "f" * 64
        elif case == "native_missing_role":
            documents.remove(by_id["opaque-0-reviewer-0/native-role-contact"])
        elif case == "native_state":
            next(state for state in org["org_agent_states"]
                 if state["state_kind"] == "phase:reviewer")["source_response_sha256"] = solver_hash
        elif case == "native_tool":
            tool["use_source_response_sha256"] = solver_hash
        elif case == "native_tool_missing_request":
            tool.pop("use_core_request_id")
        else:
            raise AssertionError(case)
    elif case == "request_identity":
        request = by_id["opaque-0-plan/request"]["payload"]
        request["payload"]["request_id"] = "opaque-1-plan"
        request["payload_sha256"] = content_hash(request["payload"])
    elif case == "response_namespace":
        by_id["opaque-0-plan/response"]["record_id"] += "/stale"
    elif case == "response_text_hash":
        by_id["opaque-0-plan/response"]["payload"]["response_text_sha256"] = "f" * 64
    elif case == "contact_sample":
        use["use_contacts"][0]["plan"]["contact_id"] = f"synthetic-program:plan:{other}"
    elif case == "contact_response":
        use["use_contacts"][0]["response_sha256"] = solve_hash
    elif case == "phase_final":
        use["use_final_response_sha256"] = solve_hash
    elif case == "org_sample":
        org["org_final_query_state"]["query_sample_id"] = other
    elif case == "review_sample":
        review["review_sample_id"] = other
    elif case == "review_phase_response":
        review["review_response_sha256"] = by_id["opaque-0-plan/response"]["payload"]["response_text_sha256"]
    elif case == "planner_sample":
        use["use_sample_id"] = other
    elif case == "tool_source_response":
        obs = by_id[f"{sid}/synthetic-program/solve/tool-result"]["payload"]
        obs["obs_source_response_sha256"] = by_id["opaque-1-solve/response"]["payload"]["response_text_sha256"]
    elif case == "tool_result_sample":
        by_id[f"{sid}/synthetic-program/solve/tool-result"]["payload"]["obs_result"] = {"sample_id": other}
    elif case == "wave_response":
        use["use_waves"] = [{"contact_plans": [use["use_contacts"][0]["plan"]],
                            "response_sha256s": ["f" * 64]}]
    elif case == "selected_final":
        use["use_waves"] = [{"contact_plans": [use["use_contacts"][0]["plan"]],
                            "response_sha256s": [use["use_contacts"][0]["response_sha256"]],
                            "selected_final_contact_id": "missing-contact"}]
    elif case == "unanswered_attempt":
        failed = copy.deepcopy(by_id["opaque-0-plan/request"])
        failed["record_id"] = "unanswered/request"
        failed["payload"]["payload"]["request_id"] = "unanswered"
        failed["payload"]["payload_sha256"] = content_hash(failed["payload"]["payload"])
        documents.insert(0, failed)
        manifest["cost"]["calls_used"] += 1
    else:
        raise AssertionError(case)
    # Keep the runtime document hash self-consistent so semantic tests cannot
    # pass merely by detecting an outer stale hash.
    if "use_runtime_trace_sha256" in use:
        fields = ("controller_policy_id", "agent_executor_id", "agent_executor_version",
                  "knowledge_snapshot_sha256", "initial_query_state_sha256",
                  "final_query_state_sha256", "speech_packet_sha256", "contacts",
                  "waves", "transitions", "final_response_sha256")
        use["use_runtime_trace_sha256"] = content_hash({key: use["use_" + key] for key in fields})
        posthoc = by_id[runtime_id.removesuffix("runtime-use") + "posthoc-use"]["payload"]
        posthoc["use_runtime_trace_sha256"] = use["use_runtime_trace_sha256"]
    records = [TraceRecord(row["channel"], row["record_id"], row["payload"]) for row in documents]
    trace_path.write_text("".join(record.serialize() + "\n" for record in records))
    tm = Path(manifest["trace_manifest"]["path"])
    tm.write_text(json.dumps({"records": {record.record_id: record.content_hash() for record in records}}))
    for key in ("raw_trace", "trace_manifest"):
        manifest[key]["sha256"] = _sha(manifest[key]["path"])
    path.write_text(json.dumps(manifest))
    bundle = verify_bundle(path)  # The existing general verifier genuinely accepts the fixture.
    ref = write_complete_score_receipt(
        path.parent / f"mutated-{case}-receipt.json", job_id=f"synthetic-{case}",
        result_path=path.parent / "score.json", source=capture_score_source(bundle),
        verified_bundle=bundle,
    )
    return path, ref, roster, projection


@pytest.mark.parametrize("case", [
    "request_identity", "response_namespace", "response_text_hash", "contact_sample",
    "contact_response", "phase_final", "org_sample", "review_sample",
    "review_phase_response", "planner_sample", "tool_source_response", "tool_result_sample",
    "wave_response", "selected_final",
])
def test_semantically_crossed_contacts_are_not_credited_to_a_valid_bundle(slurp_source, case):
    path, ref, roster, projection = _mutate_synthetic_trace(slurp_source, case)
    with pytest.raises(RewardLinkError):
        build_reward_links(path, ref, roster, projection)



def test_unanswered_attempt_is_retained_without_becoming_successful_credit(slurp_source):
    path, ref, roster, projection = _mutate_synthetic_trace(slurp_source, "unanswered_attempt")
    links = build_reward_links(path, ref, roster, projection)
    link = next(link for link in links if link.source.source_sample_id == "slurp:train:1")
    assert any(event["record_id"] == "unanswered/request" for event in link.provenance["ordered_events"])
    assert not any(event["record_id"] == "unanswered/response" for event in link.provenance["ordered_events"])
    assert link.source.response_sha256 == hashlib.sha256(b"synthetic-answer-0-revise").hexdigest()


def test_self_consistent_forgery_cannot_convert_through_verified_source_api(completed_source):
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    manifest, ref, roster, _, _ = completed_source
    links = build_reward_links(manifest, ref, roster, _projection())
    source = replace(links[0].source, response_sha256="f" * 64)
    forged = replace(links[0], source=source)
    forged = replace(forged, link_sha256=content_hash(forged.unsigned_json()))
    forged.validate()  # Local integrity is distinct from authoritative source verification.
    with pytest.raises(RewardLinkError):
        verify_experience_sources((forged,) + links[1:], manifest, ref, roster, _projection())


@pytest.mark.parametrize("case", [
    "native_role", "native_contact_hash", "native_missing_role",
    "native_state", "native_tool", "native_tool_missing_request",
])
def test_native_role_and_tool_sources_cannot_cross_roles(native_slurp_source, case):
    path, ref, roster, projection = _mutate_synthetic_trace(native_slurp_source, case)
    with pytest.raises(RewardLinkError):
        build_reward_links(path, ref, roster, projection)


def test_authored_official_projection_real_links_and_shared_evidence(completed_source, tmp_path):
    """Use actual seals, reward joins, cost reader and pooled cohort statistics."""
    from test_manual_architecture_authoring import helper
    from speech_aware_evidence_acquisition.rails.reward_links import SLURP_NATIVE_FIELDS
    from speech_aware_evidence_acquisition.analysis.system_text_pilot import _read_complete_evidence
    from speech_aware_evidence_acquisition.analysis.system_architecture_read import CompleteArchitectureEvidence
    from speech_aware_evidence_acquisition.analysis.system_text_update import _describe_complete_cohort
    from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
    from speech_aware_evidence_acquisition.rails.reward_link_io import build_reward_link_artifact
    projection = RewardProjection.from_json(helper.official_slurp_projection())
    ids = ["slurp:train:1", "slurp:train:10"]
    def saved_counts(_):
        rows = [{"sample_id": sid, **{f: (0 if f.endswith(("_fp", "_fn")) else 1)
                 for f in SLURP_NATIVE_FIELDS}} for sid in ids]
        return {"aggregate": {"identity_check": {"passed": True},
                "official": {"slu_f1": 1.0},
                "port_micro": {"slu_f1": 1.0, "intent_accuracy": 1.0}}, "per_sample": rows}
    def terminal_metadata(records, outputs):
        from speech_aware_evidence_acquisition.rails.hashing import content_hash
        for index, output in enumerate(outputs):
            contact = {"request_id": output["request_id"],
                       "response_sha256": output["response_sha256"],
                       "response_text_sha256": output["response_text_sha256"]}
            execution = {"contacts": [contact], "final_contact": contact}
            output["native_episode_receipt"] = {
                "role_visits": [{"stage": "solver", "role_id": "solver",
                                 "execution_receipt": execution}],
                "planner_routes": [], "accepted_solver_receipt": execution}
            timing = {"schema": "saea-sample-execution-timing-v1", "sample_id": output["sample_id"],
                "execution_unit_id": None, "admission_index": index, "expected_samples": 2,
                "slot_count": 4, "queue_depth": 16, "batch_started_ns": 0,
                "admitted_ns": (index + 1) * 1_000_000_000,
                "finished_ns": (index + 2) * 1_000_000_000,
                "status": "completed", "error_type": None}
            payload = {"use_sample_execution_timing": timing}
            records.append({"record_id": output["sample_id"] + "/synthetic-program/sample-execution-timing",
                "channel": "USE", "payload": payload, "content_sha256": content_hash(payload)})
        return records, outputs
    session = tmp_path / "synthetic-session.json"
    session.write_text(json.dumps({"session_id": "synthetic-only"}))
    session_pin = {"path": str(session), "sha256": _sha(session)}
    bindings, members = [], {}
    for label in ("seed", "seed-aa"):
        directory = tmp_path / label
        directory.mkdir()
        path, ref, roster, _, _ = _slurp_source(
            completed_source, directory, "native", run_id="SYNTHETIC-" + label,
            score_function=saved_counts, trace_transform=terminal_metadata, session_receipt=session_pin)
        manifest = json.loads(path.read_text())
        (path.parent / "score-jobs.jsonl").write_text(json.dumps({
            "manifest": str(path), "job_id": "synthetic-slurp-score"}) + "\n")
        config = {"schema": "saea-reward-link-artifact-config-v1", "manifest": {"path": str(path), "sha256": _sha(path)},
                  "complete_score_receipt": {"path": str(ref.path), "sha256": _sha(ref.path), "cell_id": ref.cell_id},
                  "construction_roster": {"path": str(roster), "sha256": _sha(roster)},
                  "projection": projection.as_json()}
        links = build_reward_links(path, ref, roster, projection)
        assert len(links) == 2
        assert set(links[0].native_score_vector["per_sample"][ids[0]]) == set(SLURP_NATIVE_FIELDS)
        artifact = build_reward_link_artifact(config, path.parent / "reward-links.json")
        bindings.append({"candidate_id": label, "config": config, "artifact": artifact})
        members[label] = {"bundle_id": "synthetic-policy", "run_id": manifest["run_id"],
                          "config_hash": manifest["config"]["config_hash"],
                          "attempt_id": manifest["attempt"]["attempt_id"]}
    recipe = {"expected_members": {k: v["run_id"] for k, v in members.items()},
              "sample_ids": ids, "required_rows_per_member": 2}
    registration = {"member_bindings": members, "registration_sha256": "a" * 64}
    def read(registration, recipe):
        return _read_complete_evidence(bindings, recipe=recipe, registration=registration,
            authority={"read_run_id": "SYNTHETIC-READ"}, family="synthetic-manual",
            schema="synthetic-evidence", evidence_type=CompleteArchitectureEvidence)
    with pytest.raises(PolicyError, match="measurement profile differs"):
        read(registration, {**recipe, "measurement_profile": {"slot_count": 4}})
    profile = {"schema": "saea-system-search-measurement-v2",
        "latency_scope": "sample-admission-to-settled-workflow-v1",
        "schedule": "sequential-trajectory", "slot_count": 4, "queue_depth": 16,
        "minimum_reliable_completion_rate": 1.0}
    recipe["measurement_profile"] = registration["measurement_profile"] = profile
    evidence = read(registration, recipe).as_json()
    report = _describe_complete_cohort(evidence, ids=ids, bindings=members,
        recipe={**recipe, "resampling": {"bootstrap_draws": 10, "confidence": .95,
            "seed": 1, "unit": "paired utterance; keep all recording variants together"}},
        roster={sid: {"sample_id": sid, "utterance_id": sid, "stratum": "synthetic"} for sid in ids},
        comparison_groups={"architecture": ("seed", "seed-aa", [])})
    assert report["sample_count"] == 2
