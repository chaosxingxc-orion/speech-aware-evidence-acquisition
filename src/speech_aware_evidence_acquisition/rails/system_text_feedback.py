"""Complete-family official feedback for external, parameter-free text updates."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .group_relative_feedback import build_group_relative_feedback
from .hashing import content_hash
from .native_episode_receipt import validate_native_episode_delivery_receipt
from .system_text_policy import PolicyError, canonical, require


def _number(value):
    require(type(value) in (int, float) and math.isfinite(value), "feedback must be finite numeric data")
    return float(value)


def _counts(counts):
    values = [_number(counts[f"slu_f1_{axis}_{kind}"]) for kind in ("tp", "fp", "fn")
              for axis in ("word", "char")]
    require(all(v >= 0 for v in values), "entity counts must be nonnegative")
    return tuple(values[i] + values[i + 1] for i in (0, 2, 4))


def feedback_utility(counts, reference_f1):
    """Linearized pooled-F1 utility; not a replacement official metric or gradient."""
    reference = _number(reference_f1)
    require(0 <= reference <= 1, "reference F1 must be frozen on the zero-to-one scale")
    tp, fp, fn = _counts(counts)
    return 2 * tp - reference * (2 * tp + fp + fn)


def paired_relative_returns(values):
    require(len(values) >= 2, "relative feedback needs at least two complete trajectories")
    values = [_number(v) for v in values]
    mean = math.fsum(values) / len(values)
    std = math.sqrt(math.fsum((v - mean) ** 2 for v in values) / len(values))
    return [(v - mean) / std if std else 0.0 for v in values]


def _absolute_json(pin):
    path = Path(pin["path"])
    require(path.is_absolute(), "feedback source path must be absolute")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin["sha256"], "feedback source hash differs")
    return json.loads(raw)


def preflight_family(bindings, expected_members):
    """Inspect ALL members' operational metadata before opening any task result.

    expected_members is the preregistered candidate-to-run mapping, not inferred
    from the sources that happen to exist. Verified seals are checked next by the
    shared reward-link reader; a COMPLETED manifest flag alone is insufficient.
    """
    ids = [b.get("candidate_id") for b in bindings]
    require(len(ids) >= 2 and len(set(ids)) == len(ids) and set(ids) == set(expected_members),
            "all members of the complete family are required")
    manifests = []
    for binding in bindings:
        config = binding["config"]
        manifest = _absolute_json(config["manifest"])
        run = expected_members[binding["candidate_id"]]
        require(manifest.get("status") == "COMPLETED" and manifest.get("run_id") == run,
                "complete family member identity/status differs")
        require(manifest.get("plan", {}).get("split_role") == "discovery", "only TRAIN feedback is allowed")
        roster = _absolute_json(config["construction_roster"])
        sample_ids = [r["sample_id"] for r in roster["items"]]
        require(sample_ids and all(s.startswith("slurp:train:") for s in sample_ids),
                "only TRAIN feedback is allowed")
        attempt = manifest["attempt"]
        state = json.loads(Path(attempt["state_path"]).read_text())
        require(state.get("state") == "FINALIZED" and state.get("run_id") == run
                and state.get("attempt_id") == attempt["attempt_id"], "attempt is not finalized")
        job_path = Path(config["manifest"]["path"]).parent / "score-jobs.jsonl"
        jobs = [json.loads(line) for line in job_path.read_text().splitlines() if line.strip()]
        require(len(jobs) == 1 and Path(jobs[0]["manifest"]).resolve() == Path(config["manifest"]["path"]).resolve(),
                "exactly one official score job per complete member is required")
        manifests.append((manifest, jobs[0]))
    return manifests


def _pinned_rows(pin, label):
    """Verify before parsing, then verify again while streaming the pinned bytes."""
    path = Path(pin["path"])
    require(path.is_absolute(), "feedback source path must be absolute")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    require(digest.hexdigest() == pin["sha256"], f"{label} bytes changed")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            if line.strip():
                row = json.loads(line)
                require(isinstance(row, dict), f"{label} row is not an object")
                yield row
    require(digest.hexdigest() == pin["sha256"], f"{label} bytes changed during read")


def _row_cost_and_terminal(manifest, *, include_sample_timing=False):
    """Stream attributed costs, including failed contacts, without retaining answers.

    The production adapter binds MODEL_RESPONSE by its record_id suffix, not a
    request_id field in the response payload. Keep only compact identity/usage
    indexes, so out-of-order records do not lose usage or require the full trace.
    """
    result, requests, responses, tool_contacts = {}, {}, {}, {}
    timing_records, timing_refs = [], {}
    for output in _pinned_rows(manifest["outputs"], "terminal"):
        sid = output["sample_id"]
        require(sid not in result, "duplicate terminal sample identity")
        receipt = output.get("native_episode_receipt")
        require(isinstance(receipt, dict), "complete system terminal receipt is missing")
        terminal = validate_native_episode_delivery_receipt(receipt, error_type=PolicyError)
        role_counts = {}
        for visit in receipt["role_visits"]:
            contacts = visit.get("execution_receipt", {}).get("contacts", [])
            role_counts[visit["role_id"]] = role_counts.get(visit["role_id"], 0) + len(contacts)
        result[sid] = {"model_calls": 0, "tool_calls": 0, "role_contacts": role_counts,
                       "tool_events": dict.fromkeys(("attempt", "result", "failed", "rejected"), 0),
                       "delivery_kind": terminal.kind,
                       "reliable_completion": terminal.kind in {"accepted", "terminal"},
                       "abstained": terminal.kind in {"abstention", "context-abstention"},
                       "trace": manifest["raw_trace"], "terminal_output": manifest["outputs"],
                       "omissions": [], "wall_time_seconds": None}
        tool_contacts[sid] = set()

    for record in _pinned_rows(manifest["raw_trace"], "trace"):
        payload, record_id = record["payload"], record["record_id"]
        if include_sample_timing and "use_sample_execution_timing" in payload:
            timing = payload["use_sample_execution_timing"]
            require(isinstance(timing, dict) and timing.get("sample_id") in result
                    and record_id.startswith(timing["sample_id"] + "/")
                    and record_id.endswith("/sample-execution-timing")
                    and timing["sample_id"] not in timing_refs,
                    "timing trace identity differs or is duplicated")
            timing_records.append(timing)
            timing_refs[timing["sample_id"]] = {"record_id": record_id, "content_sha256": content_hash(payload)}
        if record["channel"] == "MODEL_REQUEST":
            request = payload.get("payload", {})
            sid = request.get("sample_id")
            if sid is None:
                continue  # Derived stitching records are not extra model calls.
            require(sid in result, "trace request is outside the terminal cohort")
            identity = request.get("request_id")
            require(isinstance(identity, str) and record_id == identity + "/request", "request trace identity differs")
            require(identity not in requests, "duplicate model request identity")
            requests[identity] = sid
            result[sid]["model_calls"] += 1
        elif record["channel"] == "MODEL_RESPONSE":
            require(record_id.endswith("/response"), "response trace identity differs")
            identity = record_id.removesuffix("/response")
            require(payload.get("request_id", identity) == identity, "response request identity differs")
            require(identity not in responses, "duplicate model response identity")
            usage = payload.get("usage", {})
            responses[identity] = usage if isinstance(usage, dict) else {}
        else:
            for axis in ("use", "obs"):
                sid = payload.get(axis + "_sample_id")
                if sid not in result:
                    continue
                events = result[sid]["tool_events"]
                for part in record_id.split("/"):
                    if part.startswith("tool-") and part[5:] in events:
                        events[part[5:]] += 1
                invocation = payload.get(axis + "_tool_invocation")
                if isinstance(invocation, dict):
                    identity = (axis, invocation.get("request_id"), invocation.get("tool_call_id"))
                    require(all(isinstance(value, str) and value for value in identity), "tool contact identity missing")
                    tool_contacts[sid].add(identity)

    usages = {sid: [] for sid in result}
    for identity, sid in requests.items():
        if identity in responses:
            usages[sid].append(responses[identity])
    for sid, row in result.items():
        require(row["model_calls"] > 0, "terminal row has no attributed model requests")
        usage = usages[sid]
        row["missing_model_responses"] = row["model_calls"] - len(usage)
        row["tool_calls"] = len(tool_contacts[sid])
        for key in ("prompt_tokens", "completion_tokens"):
            row[key] = (sum(u[key] for u in usage) if len(usage) == row["model_calls"]
                        and all(type(u.get(key)) is int and u[key] >= 0 for u in usage) else None)
    if include_sample_timing:
        from ..analysis.system_cache_cost import summarize_sample_execution_timing, CacheCostError
        try:
            report = summarize_sample_execution_timing(timing_records, expected_sample_ids=list(result))
        except CacheCostError as error:
            raise PolicyError(str(error)) from error
        records_by_id = {r["sample_id"]: r for r in timing_records}
        for measured in report["samples"]:
            sid = measured["sample_id"]
            result[sid].update(wall_time_seconds=measured["elapsed_seconds"], sample_timing=measured,
                sample_timing_record=records_by_id[sid], sample_timing_trace=timing_refs[sid])
    return result


def learning_read_authority(authority):
    """Keep a whole-family commitment without disclosing blind allocation outcomes."""
    projected = dict(authority)
    registration = projected.pop("stage_registration", None)
    if registration is not None:
        projected["stage_registration_sha256"] = content_hash(registration)
    return projected


@dataclass(frozen=True)
class CompleteSystemFeedback:
    document_json: str

    def as_json(self):
        return json.loads(self.document_json)

    def learning_view(self, candidate_ids):
        """Project own-branch evidence after the entire round passes its read gate."""
        d = self.as_json()
        require(d.get("schema") != "saea-complete-system-pilot-evidence-v1",
                "pilot evidence is not optimizer feedback")
        require(len(candidate_ids) >= 2 and len(set(candidate_ids)) == len(candidate_ids)
                and set(candidate_ids) <= set(d["summaries"])
                and all(cid.startswith("L-") or cid in {"seed", "seed-aa"} for cid in candidate_ids),
                "learning feedback must contain only the learning branch or initial seed pair")
        family_sha = content_hash(d)
        d["summaries"] = {k: v for k, v in d["summaries"].items() if k in candidate_ids}
        feedback = d["feedback"]
        feedback["candidate_ids"] = list(candidate_ids)
        feedback["sources"] = [s for s in feedback["sources"] if s["candidate_id"] in candidate_ids]
        for group in feedback["groups"]:
            group["members"] = [m for m in group["members"] if m["candidate_id"] in candidate_ids]
            # Recompute rather than leaking blind scores through group normalization.
            relative = paired_relative_returns([m["utility"] for m in group["members"]])
            for member, advantage in zip(group["members"], relative, strict=True):
                member["relative_return"] = advantage
                # Old multi-metric centering used the entire round too.
                member.pop("quality", None)
        d["read_gate_family_sha256"] = family_sha
        if "read_authority" in d:
            d["read_authority"] = learning_read_authority(d["read_authority"])
        return CompleteSystemFeedback(canonical(d))

    @classmethod
    def from_family(cls, bindings, *, expected_members, family_id, reference=None, initial_reference_member=None,
                    measurement_profile=None):
        if measurement_profile is not None:
            from .system_search_measurement import validate_profile
            validate_profile(measurement_profile)
        metadata = preflight_family(bindings, expected_members)
        require(all(manifest.get("split", {}).get("count", 0) >= 400
                    for manifest, _ in metadata),
                "system search feedback requires at least 400 rows before any task-result read")
        from ..core.bundle.verify import verify_bundle
        for binding in bindings:
            verified = verify_bundle(Path(binding["config"]["manifest"]["path"]))
            require(verified.attempt_state == "FINALIZED", "family seal verification failed")
        grouped = build_group_relative_feedback(bindings)
        require(grouped["carrier_lock_key"] == "slurp" and len(grouped["groups"]) >= 400,
                "system search feedback requires the entire registered cohort of at least 400 rows")
        by_candidate, summaries = _official_family_rows(bindings, metadata, grouped, measurement_profile=measurement_profile)
        if reference is None:
            require(initial_reference_member in summaries, "initial reference member must be preregistered")
            reference = {"family_id": family_id, "candidate_id": initial_reference_member,
                         "source_sha256": content_hash(grouped["sources"]),
                         "sample_ids": [g["sample_id"] for g in grouped["groups"]],
                         "f1": summaries[initial_reference_member]["slu_f1"]}
        else:
            require(initial_reference_member is None and isinstance(reference, CompleteSystemFeedback),
                    "freeze the original reference instead of recomputing it")
            reference = reference.as_json()["reference"]
        for group in grouped["groups"]:
            utilities = [feedback_utility(m["native_counts"], reference["f1"]) for m in group["members"]]
            relative = paired_relative_returns(utilities)
            for member, utility, advantage in zip(group["members"], utilities, relative, strict=True):
                member.update(utility=utility, relative_return=advantage,
                              execution=by_candidate[member["candidate_id"]][group["sample_id"]])
        result = {"schema": "saea-complete-system-feedback-v1", "family_id": family_id,
                  "reference": reference, "summaries": summaries, "feedback": grouped,
                  "interpretation": "Whole-system realized return; no node causal credit or policy gradient.",
                  "model_contacts_added": 0, "scorer_contacts_added": 0}
        if measurement_profile is not None:
            result["measurement_profile"] = measurement_profile
        return cls(canonical(result))


def _summarize_official_sample_timing(rows, analysis_ids):
    """Preserve real admission order while pairing the unchanged analysis cohort."""
    from ..analysis.system_cache_cost import summarize_sample_execution_timing
    require(set(rows) == set(analysis_ids) and len(analysis_ids) == len(set(analysis_ids)),
            "timing analysis cohort differs")
    records = [row["sample_timing_record"] for row in rows.values()]
    ordered = sorted(records, key=lambda row: row["admission_index"])
    admission_ids = [row["sample_id"] for row in ordered]
    require(set(admission_ids) == set(analysis_ids), "timing admission cohort differs")
    return summarize_sample_execution_timing(records, expected_sample_ids=admission_ids)


def _official_family_rows(bindings, metadata, grouped, *, measurement_profile=None):
    """Read common official counts and attributed costs after every seal passes."""
    by_candidate, summaries = {}, {}
    if measurement_profile is not None:
        from .system_search_measurement import validate_profile
        validate_profile(measurement_profile)
    for binding, (manifest, job) in zip(bindings, metadata, strict=True):
        cid = binding["candidate_id"]
        require(binding["config"]["projection"]["scorer"] == "slurp-slu-official-train",
                "system updates require the official TRAIN scorer")
        receipt = _absolute_json(binding["config"]["complete_score_receipt"])
        require(receipt["job_id"] == job["job_id"], "official score identity differs from sole job")
        score = _absolute_json(receipt["score_result"])["scores"]["slurp-slu-official-train"]
        aggregate = score["aggregate"]
        require(aggregate["identity_check"]["passed"] is True, "official sufficient-count identity failed")
        rows = (_row_cost_and_terminal(manifest) if measurement_profile is None else
                _row_cost_and_terminal(manifest, include_sample_timing=True))
        require(set(rows) == {g["sample_id"] for g in grouped["groups"]}, "terminal cohort differs")
        by_candidate[cid] = rows
        summaries[cid] = {"slu_f1": aggregate["official"]["slu_f1"],
                          "intent": aggregate["port_micro"]["intent_accuracy"],
                          "model_calls": sum(r["model_calls"] for r in rows.values()),
                          "tool_calls": sum(r["tool_calls"] for r in rows.values()),
                          "reliable_completion_rate": sum(r["reliable_completion"] for r in rows.values()) / len(rows)}
        if measurement_profile is not None:
            from .system_text_policy import sha
            report = _summarize_official_sample_timing(rows, [g["sample_id"] for g in grouped["groups"]])
            require(all(report[k] == measurement_profile[k] for k in ("slot_count", "queue_depth")),
                    "sample timing scheduling envelope differs from profile")
            session = manifest["session_receipt"]["sha256"]
            sha(session)
            summaries[cid].update(sample_timing=report, timing_session_sha256=session)
    if measurement_profile is not None:
        require(len({s["timing_session_sha256"] for s in summaries.values()}) == 1,
                "measured family mixes serving session receipts")
    return by_candidate, summaries
