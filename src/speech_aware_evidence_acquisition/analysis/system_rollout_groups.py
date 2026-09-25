"""Group complete construction episodes without manufacturing node/action credit.

Inputs are previously verified, hash-pinned complete system feedback exports.
Grouping is a diagnostic and future learner input, not a policy update.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path

from ..rails.finite_action_policy import official_utility
from ..rails.finite_policy_artifacts import _confined_file, _pinned_json
from ..rails.hashing import content_hash
from ..reproduction.slurp_scoring import parse_slu_response


class RolloutGroupError(ValueError):
    """Complete source identity or group membership is inconsistent."""


def _require(condition, message):
    if not condition:
        raise RolloutGroupError(message)


def _fingerprint(document, field, label):
    unsigned = dict(document)
    claimed = unsigned.pop(field, None)
    _require(claimed == content_hash(unsigned), f"{label} fingerprint differs")


def normalized_answer_hash(text):
    """Ignore JSON formatting and entity order, preserving duplicates and values."""
    scenario, action, entities, parsed = parse_slu_response(text)
    value = ({"scenario": scenario, "action": action,
              "entities": sorted((e.type, e.filler) for e in entities)}
             if parsed else {"invalid_response": text})
    return content_hash(value)


def _artifact(root, metadata):
    path = Path(str(metadata["path"])).resolve()
    try:
        relpath = str(path.relative_to(Path(root).resolve()))
    except ValueError as error:
        raise RolloutGroupError("source artifact escapes the data root") from error
    return _confined_file(root, relpath), metadata["sha256"]


def _jsonl(path, expected_sha):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            yield json.loads(line)
    _require(digest.hexdigest() == expected_sha, "source JSONL hash differs")


def initial_speech_input_hash(payload):
    """Bind the original speech input independently of instruction or policy text."""
    fields = ("sample_id", "carrier_lock_key", "media_relpath", "speech_ref",
              "speech_packet_sha256", "sample_rate_hz", "audio_seconds")
    _require(all(payload.get(k) is not None for k in fields),
             "first speech identity is incomplete")
    return content_hash({k: payload[k] for k in fields})


def load_group_source(*, data_root, feedback_pin, label):
    """Resolve complete actor input/output identities; no model, scorer or gold load.

    The pinned report was produced by load_system_feedback's full native/score
    verifier. Recheck its content and underlying pinned sources before grouping.
    No live or partial manifest is accepted.
    """
    root = Path(data_root)
    feedback, feedback_sha = _pinned_json(root, feedback_pin, "complete system feedback")
    _fingerprint(feedback, "content_sha256", "feedback")
    _require(feedback.get("schema") == "saea-slurp-system-feedback-v1"
             and feedback.get("feedback_role") == "construction",
             "only complete construction system feedback is admitted")
    _require(feedback.get("policy_supply_receipt") is None
             and feedback.get("policy_episode_decisions") is None,
             "logged optimized decisions require their registered policy-credit join")
    for name in ("manifest", "phases", "flight_receipts", "score_jobs"):
        _pinned_json(root, feedback["source_bindings"][name], name)
    for name, pin in feedback["resolved_auxiliary_sources"].items():
        _pinned_json(root, pin, name)
    manifest, _ = _pinned_json(root, feedback["source_bindings"]["manifest"], "manifest")
    _require(manifest["status"] == "COMPLETED", "source is not complete")
    _require(manifest["run_id"] == feedback["run_id"]
             and manifest["plan"]["attempt_id"] == feedback["attempt_id"],
             "feedback run or attempt identity differs")
    exported = feedback["system_trajectories"]
    _fingerprint(exported, "document_sha256", "trajectory export")
    _require(exported["source"]["manifest_content_sha256"] == content_hash(manifest)
             and exported["source"]["config_hash"] == manifest["config"]["config_hash"],
             "trajectory source differs from its manifest")
    ids = exported["sample_ids"]
    _require(ids and len(ids) == len(set(ids)), "source roster is empty or duplicated")
    _require(set(ids) == set(manifest["split"]["ids"])
             and len(ids) == manifest["split"]["count"]
             and feedback["split_identity_hash"] == manifest["split"]["identity_hash"],
             "source split identity differs")
    trajectories = exported["trajectories"]
    terminal = feedback["terminal_feedback"]
    _require([r["sample_id"] for r in trajectories] == ids
             and [r["sample_id"] for r in terminal] == ids,
             "trajectory or terminal population differs from the full roster")
    wanted = {}
    for trajectory in trajectories:
        _fingerprint(trajectory, "trajectory_sha256", "trajectory")
        contacts = [c for visit in trajectory["role_visits"] for c in visit["contacts"]]
        _require(bool(contacts), "cannot prove common speech input for a zero-contact episode")
        contact = contacts[0]
        key = contact["request_record_id"]
        _require(key not in wanted, "source episodes alias a first request")
        wanted[key] = (trajectory["sample_id"], contact)
    inputs = {}
    trace_path, trace_sha = _artifact(root, manifest["raw_trace"])
    for record in _jsonl(trace_path, trace_sha):
        if record["record_id"] not in wanted:
            continue
        sid, contact = wanted[record["record_id"]]
        _require(sid not in inputs, "source repeats a first request")
        request = record["payload"]
        payload = request["payload"]
        _require(content_hash(request) == contact["request_record_sha256"]
                 and content_hash(payload) == contact["request_payload_sha256"]
                 and payload["sample_id"] == sid, "first request differs from verified trajectory")
        inputs[sid] = initial_speech_input_hash(payload)
    _require(set(inputs) == set(ids), "first request set does not cover the source")
    output_path, output_sha = _artifact(root, manifest["outputs"])
    outputs = {}
    for output in _jsonl(output_path, output_sha):
        sid = output["sample_id"]
        _require(not output.get("native_episode_receipt", {}).get("system_policy_decision"),
                 "logged whole-policy decisions require their registered policy-credit join")
        _require(sid not in outputs, "duplicate delivered output")
        outputs[sid] = output
    _require(set(outputs) == set(ids), "delivered output population differs")
    rows = []
    for trajectory, score in zip(trajectories, terminal):
        sid = trajectory["sample_id"]
        output = outputs[sid]
        _require(score["trajectory_sha256"] == trajectory["trajectory_sha256"]
                 and score["delivered_output_sha256"] == content_hash(output)
                 and trajectory["final_output"]["record_sha256"] == content_hash(output),
                 "terminal feedback or delivered output belongs to another episode")
        visits = trajectory["role_visits"]
        rows.append({
            "sample_id": sid, "trajectory_sha256": trajectory["trajectory_sha256"],
            "input_sha256": inputs[sid],
            "normalized_answer_sha256": normalized_answer_hash(output["text"]),
            **{k: copy.deepcopy(score[k]) for k in
               ("tp", "fp", "fn", "intent_exact", "format_ok", "fallback_flags")},
            "role_visits": [v["stage"] for v in visits],
            "revision_reached": sum(v["stage"] == "solver" for v in visits) > 1,
            "delivery_kind": trajectory["delivery"]["kind"],
            "model_contacts": sum(len(v["contacts"]) for v in visits),
            "tool_events": len(trajectory["tool_events"]),
        })
    return {
        "label": label, "run_id": feedback["run_id"], "attempt_id": feedback["attempt_id"],
        "feedback_sha256": feedback_sha, "feedback_role": feedback["feedback_role"],
        "split_identity_hash": feedback["split_identity_hash"],
        "model_fragment": manifest["config"]["fragments"]["model"],
        "session_receipt_sha256": manifest["session_receipt"]["sha256"],
        "config_hash": manifest["config"]["config_hash"],
        "ordered_sample_ids": list(ids), "rows": rows,
    }


def group_complete_system_sources(sources, *, f0, standard_deviation_floor=1e-8):
    """Keep all full episodes and score within-input groups using frozen utility.

    These normalized advantages are a declared numeric adaptation, not the
    upstream TF-GRPO semantic updater. Historical fixed-run allocation has no
    logged propensity and is not retroactively called randomized policy sampling.
    """
    sources = tuple(sources)
    _require(len(sources) >= 2, "a group needs at least two complete sources")
    official_utility(tp=0, fp=0, fn=0, f0=f0)
    _require(isinstance(standard_deviation_floor, (int, float))
             and not isinstance(standard_deviation_floor, bool)
             and math.isfinite(standard_deviation_floor) and standard_deviation_floor > 0,
             "advantage scale floor must be positive and finite")
    reference = sources[0]
    roster = reference["ordered_sample_ids"]
    _require(roster and len(roster) == len(set(roster)), "roster is empty or duplicated")
    identities, labels, fingerprints = set(), set(), set()
    indexed = []
    for source in sources:
        identity = (source["run_id"], source["attempt_id"])
        _require(identity not in identities and source["label"] not in labels,
                 "source identity or label is duplicated")
        identities.add(identity)
        labels.add(source["label"])
        _require(source["feedback_role"] == "construction", "evaluation feedback cannot enter groups")
        for key in ("split_identity_hash", "model_fragment", "session_receipt_sha256"):
            _require(source[key] == reference[key], f"group {key} differs")
        _require(source["ordered_sample_ids"] == roster, "full ordered roster differs")
        rows = source["rows"]
        _require([row["sample_id"] for row in rows] == roster, "terminal population differs")
        for row in rows:
            _require(row["trajectory_sha256"] not in fingerprints, "trajectory credited more than once")
            fingerprints.add(row["trajectory_sha256"])
            _require(type(row["intent_exact"]) in (float, int) and row["intent_exact"] in (0, 1),
                     "intent must be numeric zero or one")
            _require(isinstance(row["format_ok"], bool), "format status must be boolean")
        indexed.append({row["sample_id"]: row for row in rows})
    groups = []
    summary = Counter()
    for sid in roster:
        rows = [index[sid] for index in indexed]
        _require(len({row["input_sha256"] for row in rows}) == 1,
                 "group members do not share the same first speech input")
        utilities = [official_utility(tp=row["tp"], fp=row["fp"], fn=row["fn"], f0=f0)
                     for row in rows]
        mean = math.fsum(utilities) / len(utilities)
        variance = math.fsum((u - mean) ** 2 for u in utilities) / len(utilities)
        std = math.sqrt(variance)
        tied = len(set(utilities)) == 1
        intent_diff = len({row["intent_exact"] for row in rows}) > 1
        answer_diff = len({row["normalized_answer_sha256"] for row in rows}) > 1
        members = []
        for source, row, utility in zip(sources, rows, utilities):
            members.append({
                "source_label": source["label"], **copy.deepcopy(row),
                "utility": utility,
                "advantage": 0.0 if tied else (utility - mean) / max(std, standard_deviation_floor),
                "action_probability": None,
                "decision_status": "historical-allocation-not-an-optimized-action-decision",
            })
            summary["episodes_without_revision"] += not row["revision_reached"]
            summary["episodes_with_fallback"] += bool(row["fallback_flags"])
            summary["model_contacts"] += row["model_contacts"]
        groups.append({
            "sample_id": sid, "input_sha256": rows[0]["input_sha256"],
            "members": members, "utility_mean": mean, "utility_std_population": std,
            "utility_margin": max(utilities) - min(utilities), "utility_tied": tied,
            "intent_disagreement": intent_diff, "normalized_answer_disagreement": answer_diff,
        })
        summary["utility_tied_groups"] += tied
        summary["utility_informative_groups"] += not tied
        summary["intent_disagreement_groups"] += intent_diff
        summary["normalized_answer_disagreement_groups"] += answer_diff
        summary["answer_disagreement_with_tied_utility_groups"] += answer_diff and tied
        summary["groups"] += 1
    report = {
        "schema": "saea-complete-system-rollout-groups-v1",
        "scope": "construction-diagnostic-only", "learning_authorized": False,
        "reward_scope": "complete delivered system",
        "frozen_f0": f0, "standard_deviation_floor": standard_deviation_floor,
        "group_size": len(sources),
        "sources": [{k: copy.deepcopy(v) for k, v in source.items()
                     if k not in ("rows", "ordered_sample_ids")} for source in sources],
        "groups": groups, "summary": dict(summary),
        "model_contacts_added": 0, "scorer_contacts_added": 0,
        "claim_boundary": "No local causal attribution, sampled-policy propensity, semantic update or RL gain.",
    }
    report["content_sha256"] = content_hash(report)
    return report
