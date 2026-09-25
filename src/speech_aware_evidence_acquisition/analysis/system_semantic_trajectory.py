"""Lossless actor-trace preparation for a future complete-system semantic updater.

No gold, official scores, model invocation, filtering or experience update occurs
here. This is a source materializer, not an algorithm flight or admission gate.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import re

from ..rails.hashing import content_hash
from .native_episode_source import VerifiedNativeEpisodeSource
from .system_rollout_groups import initial_speech_input_hash
from .system_trajectory import export_system_trajectories


class SemanticTrajectoryError(ValueError):
    """A complete actor episode cannot be materialized with exact provenance."""


def _record(trace, record_id, expected_hash):
    value = trace[record_id]
    if content_hash(value) != expected_hash:
        raise SemanticTrajectoryError("actor record differs from its verified trajectory")
    return value


def _episode(source, trajectory, round_id):
    trace = source.bundle.trace_records
    pool, contacts, tool_records = {}, [], []
    selected_records = set()

    def intern(value):
        key = content_hash({"value": value})
        pool.setdefault(key, copy.deepcopy(value))
        return key

    for visit in trajectory["role_visits"]:
        for contact in visit["contacts"]:
            request_id = contact["request_record_id"]
            response_id = contact["response_record_id"]
            request = _record(trace, request_id, contact["request_record_sha256"])
            response = _record(trace, response_id, contact["response_record_sha256"])
            body = request["payload"]
            if content_hash(body) != contact["request_payload_sha256"]:
                raise SemanticTrajectoryError("actor request payload changed")
            selected_records.update((request_id, response_id))
            wire_ref = contact["wire_response"]
            wire = None
            if "record_id" in wire_ref:
                record = _record(trace, wire_ref["record_id"], wire_ref["content_sha256"])
                try:
                    raw = base64.b64decode(record["response_b64"], validate=True)
                    text = raw.decode("utf-8")
                except (KeyError, ValueError, UnicodeError) as error:
                    raise SemanticTrajectoryError("wire response is not exact UTF-8 source text") from error
                if hashlib.sha256(raw).hexdigest() != record["response_sha256"]:
                    raise SemanticTrajectoryError("wire response bytes differ from their source hash")
                selected_records.add(wire_ref["record_id"])
                wire = {
                    "record_id": wire_ref["record_id"],
                    "record_sha256": wire_ref["content_sha256"],
                    "body_utf8_ref": intern(text),
                    "body_sha256": record["response_sha256"],
                }
            contacts.append({
                "visit_index": visit["index"], "role_id": visit["role_id"],
                "stage": visit["stage"], "interrupted": visit["interrupted"],
                "request_record_id": request_id, "response_record_id": response_id,
                "request_field_refs": {key: intern(value) for key, value in body.items()},
                "response_record_ref": intern(response), "wire_response": wire,
            })
    if not contacts:
        raise SemanticTrajectoryError("complete episode lacks an original actor input")
    for event in trajectory["tool_events"]:
        rid = event["record_id"]
        value = _record(trace, rid, event["trace_record_sha256"])
        tool_records.append({"record_id": rid, "record_ref": intern(value)})
        selected_records.add(rid)
    sid = trajectory["sample_id"]
    first = trace[contacts[0]["request_record_id"]]["payload"]
    input_sha = initial_speech_input_hash(first)
    split_hash = source.plan.split_identity_hash
    group_hash = content_hash({
        "round_id": round_id, "split_identity_hash": split_hash, "input_sha256": input_sha,
    })
    episode = {
        "schema": "saea-complete-episode-semantic-input-v1",
        "round_id": round_id, "split_identity_hash": split_hash,
        "input_sha256": input_sha, "input_group_sha256": group_hash,
        "trajectory": copy.deepcopy(trajectory),
        "contacts": contacts, "tool_records": tool_records,
        "timeline_record_ids": [rid for rid in trace if rid in selected_records],
        "control_receipt": {
            key: copy.deepcopy(source.phase_results[sid]["native_episode_receipt"][key])
            for key in ("planner_routes", "terminal_disposition", "deliver_normaliser",
                        "truncation_events", "abstention_receipt", "react_exhaustion",
                        "planner_action_illegal")
            if key in source.phase_results[sid]["native_episode_receipt"]
        },
        "delivered_text": source.output_rows[sid]["text"],
        "content_pool": pool,
        "reading_contract": (
            "Read the entire ordered episode. Resolve content_pool references to recover exact "
            "actor request fields, responses and tool records. The timeline preserves source record "
            "order. Interrupted responses are not authoritative delivered answers. Trace references "
            "without materialized content are provenance, not additional observations. No audio is "
            "replayed here; only its identity and recorded actor contexts are available. No reference "
            "answer or task reward is supplied by this score-free preparation."
        ),
    }
    episode["content_sha256"] = content_hash(episode)
    return episode


def materialize_semantic_trajectories(source: VerifiedNativeEpisodeSource, *, round_id: str):
    """Prepare every complete discovery episode without opening score artifacts.

    Production callers must obtain the source from verify_native_episode_source
    and register the read. The source split is not sufficient authorization for
    learning or a model-facing update. All actual summary/update requests still
    require their own execution plan and exact capacity admission.
    """
    if not isinstance(source, VerifiedNativeEpisodeSource):
        raise SemanticTrajectoryError("source must be a verified native episode source")
    if source.plan.split_role != "discovery":
        raise SemanticTrajectoryError("only discovery actor sources may be prepared")
    if not isinstance(round_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", round_id):
        raise SemanticTrajectoryError("round_id must be a nonempty registered identifier")
    split_hash = source.plan.split_identity_hash
    if not isinstance(split_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", split_hash):
        raise SemanticTrajectoryError("split identity must be a SHA-256")
    exported = export_system_trajectories(source)
    try:
        episodes = [_episode(source, trajectory, round_id) for trajectory in exported["trajectories"]]
    except (KeyError, TypeError, ValueError) as error:
        raise SemanticTrajectoryError(f"complete episode materialization failed: {error}") from error
    report = {
        "schema": "saea-system-semantic-trajectory-materialization-v1",
        "source": copy.deepcopy(exported["source"]),
        "sample_ids": list(source.sample_ids), "episodes": episodes,
        "learning_authorized": False, "model_contacts_added": 0, "scorer_contacts_added": 0,
        "claim_scope": "Exact actor-trace preparation, not summary inference or TF-GRPO reproduction.",
    }
    report["content_sha256"] = content_hash(report)
    return report


def tfgrpo_summary_fields(episode):
    """Build only the audited upstream summary input fields, not EvaluationSample.

    The pinned updater reads json.loads(item.trajectories)[0]["trajectory"].
    Put the complete episode there. Numeric feedback and eligibility require
    a separate registered adaptation; given_ground_truth=False hides upstream
    rewards too, so these fields must not be used as a complete update loop.
    """
    unsigned = dict(episode)
    claimed = unsigned.pop("content_sha256", None)
    if (episode.get("schema") != "saea-complete-episode-semantic-input-v1"
            or claimed != content_hash(unsigned)):
        raise SemanticTrajectoryError("semantic trajectory schema or fingerprint changed")
    rendered = json.dumps(episode, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "raw_question": "Registered speech task input " + episode["input_group_sha256"],
        "trajectories": json.dumps([{"trajectory": rendered}], ensure_ascii=False, separators=(",", ":")),
        "correct_answer": "", "reasoning": "",
    }
