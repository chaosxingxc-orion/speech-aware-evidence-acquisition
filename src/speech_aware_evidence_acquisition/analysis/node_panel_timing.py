"""Verify complete owner and whole-node timing after the exact family READ.

No serving contact, score, policy update or claim of exclusive GPU time occurs.
Original submission and admission clocks retain every recorded wait.
"""
from collections import defaultdict
import statistics

from ..rails.hashing import content_hash


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _integer(value):
    return type(value) is int and value >= 0


def _stage(event):
    return event["round_index"], event["node_index"]


def audit_member_node_timing(source, contacts, *, panel_id, group_index,
                             group_size, max_jobs, job_keys):
    """Join an owner's original callbacks to all original fitted model requests."""
    cfg = source.composed.values.get("native_node_pipeline", {})
    _require(cfg.get("schema") == "saea-native-node-pipeline-v1"
             and _integer(group_index) and type(group_size) is int and group_size > 0
             and type(max_jobs) is int and max_jobs >= group_size * (group_index + 1)
             and max_jobs % group_size == 0
             and cfg.get("group_size") == group_size and cfg.get("max_jobs") == max_jobs,
             "panel configuration differs from registered ownership")
    order = cfg.get("node_order", [])
    _require(order and len(order) == len(set(order)), "panel node order is ambiguous")
    _require(isinstance(panel_id, str) and panel_id, "panel identity is required")
    _require(len(job_keys) == group_size and all(len(k) == 2 and k[1] is None for k in job_keys),
             "exact whole-utterance jobs are required")
    ids = [k[0] for k in job_keys]
    _require(len(set(ids)) == group_size and set(ids) == set(source.sample_ids),
             "panel job roster differs from complete source")
    samples, events, pins = {}, [], []
    for record_id, payload in source.bundle.trace_records.items():
        for field in ("use_sample_execution_timing", "use_node_pipeline_timing"):
            if field not in payload:
                continue
            value = payload[field]
            _require(isinstance(value, dict) and value.get("sample_id") in ids
                     and value.get("execution_unit_id") is None
                     and value.get("panel_id") == panel_id
                     and value.get("status") == "completed" and value.get("error_type") is None,
                     "timing identity, status or owner differs")
            sid = value["sample_id"]
            pins.append({"record_id": record_id, "content_sha256": content_hash(payload)})
            if field == "use_sample_execution_timing":
                i = ids.index(sid)
                _require(sid not in samples and value.get("schema") == "saea-sample-execution-timing-v1"
                         and value.get("admission_index") == i
                         and value.get("panel_admission_index") == group_index * group_size + i
                         and value.get("panel_expected_samples") == max_jobs
                         and value.get("expected_samples") == group_size and value.get("slot_count") == 4,
                         "sample timing order or complete coverage differs")
                clocks = [value.get(k) for k in ("batch_started_ns", "panel_execution_started_ns", "admitted_ns", "finished_ns")]
                _require(all(_integer(x) for x in clocks) and clocks == sorted(clocks),
                         "invalid original sample clock")
                samples[sid] = dict(value)
            else:
                ni, kind = value.get("node_index"), value.get("kind")
                _require(value.get("schema") == "saea-node-pipeline-timing-v1"
                         and value.get("group_index") == group_index and _integer(ni)
                         and ni < len(order) and order[ni] == value.get("node_id")
                         and _integer(value.get("round_index")) and kind in ("prepare", "model", "tool"),
                         "node timing identity or stage differs")
                slot = value.get("slot_id")
                _require(slot is None if kind == "prepare" else type(slot) is int and 0 <= slot < 4,
                         "node callback slot is invalid")
                clocks = [value.get(k) for k in ("queued_ns", "started_ns", "finished_ns")]
                _require(all(_integer(x) for x in clocks) and clocks == sorted(clocks),
                         "invalid node callback clock")
                events.append(dict(value))
    _require(set(samples) == set(ids) and events, "incomplete sample or node timing")
    _require(len({s["batch_started_ns"] for s in samples.values()}) == 1
             and len({s["panel_execution_started_ns"] for s in samples.values()}) == 1,
             "panel submission origin changed within an owner")
    for event in events:
        timer = samples[event["sample_id"]]
        _require(timer["admitted_ns"] <= event["queued_ns"] <= event["finished_ns"] <= timer["finished_ns"],
                 "node callback escaped its original sample interval")
    models = [e for e in events if e["kind"] == "model"]
    _require(len(models) == len(contacts) and len({c["request_id"] for c in contacts}) == len(contacts),
             "model callback coverage differs from fitted contacts")
    for sid in ids:
        measured = sorted((e for e in models if e["sample_id"] == sid), key=lambda e: e["started_ns"])
        requests = [c for c in contacts if c["sample_id"] == sid]
        _require(len(measured) == len(requests) and measured,
                 "sample model callbacks are missing or duplicated")
        for event, request in zip(measured, requests, strict=True):
            _require(event["node_id"] == request["role_id"] and event["slot_id"] == request["requested_slot_id"],
                     "model callback role or slot differs from its original request")
        _require(all(a["finished_ns"] <= b["started_ns"] for a, b in zip(measured, measured[1:])),
                 "one sample has overlapping model callbacks")
    return {"schema": "saea-node-panel-member-timing-v1", "panel_id": panel_id,
            "group_index": group_index, "group_size": group_size, "max_jobs": max_jobs,
            "node_order": list(order), "samples": [samples[sid] for sid in ids],
            "events": events, "model_contacts": len(models), "source_records": pins}


def combine_node_panel_timings(members):
    """Validate every registered group together before reporting panel timing."""
    _require(isinstance(members, list) and len(members) >= 2, "complete panel owners are required")
    first = members[0]
    for key in ("panel_id", "group_size", "max_jobs", "node_order"):
        _require(all(m.get(key) == first[key] for m in members), "panel identity or geometry differs")
    group_size, jobs = first["group_size"], first["max_jobs"]
    _require(len(members) * group_size == jobs
             and sorted(m["group_index"] for m in members) == list(range(len(members))),
             "missing or duplicate panel owner")
    members = sorted(members, key=lambda m: m["group_index"])
    samples = [s for m in members for s in m["samples"]]
    _require(len(samples) == jobs and [s["panel_admission_index"] for s in samples] == list(range(jobs))
             and len({s["batch_started_ns"] for s in samples}) == 1
             and len({s["panel_execution_started_ns"] for s in samples}) == 1,
             "global job order or submission origin differs")
    events = [e for m in members for e in m["events"]]
    work = [e for e in events if e["kind"] != "prepare"]
    prepares = [e for e in events if e["kind"] == "prepare"]
    groups = defaultdict(list)
    for event in work:
        groups[_stage(event)].append(event)
    _require(groups, "panel has no executed stages")
    stages, previous_end = [], None
    for key, stage in sorted(groups.items()):
        start = min(e["started_ns"] for e in stage)
        end = max(e["finished_ns"] for e in stage)
        prep = [e for e in prepares if _stage(e) == key]
        participants = {(e["group_index"], e["sample_id"]) for e in stage}
        _require(participants <= {(e["group_index"], e["sample_id"]) for e in prep},
                 "model stage lacks prepared participants")
        _require(previous_end is None or previous_end <= start, "model stages crossed the global barrier")
        _require(prep and max(e["finished_ns"] for e in prep) <= start, "model stage crossed final preparation")
        stages.append({"stage": list(key), "node_id": stage[0]["node_id"],
                       "model_contacts": sum(e["kind"] == "model" for e in stage),
                       "tool_callbacks": sum(e["kind"] == "tool" for e in stage),
                       "started_ns": start, "finished_ns": end,
                       "wall_seconds": (end - start) / 1e9,
                       "gap_after_previous_seconds": None if previous_end is None else (start - previous_end) / 1e9})
        previous_end = end
    for slot in range(4):
        active = sorted((e for e in work if e["slot_id"] == slot), key=lambda e: e["started_ns"])
        _require(all(a["finished_ns"] <= b["started_ns"] for a, b in zip(active, active[1:])),
                 "simultaneous callbacks reused one slot")
    for prep in prepares:
        earlier = [e for e in work if e["group_index"] == prep["group_index"] and _stage(e) < _stage(prep)]
        _require(not earlier or max(e["finished_ns"] for e in earlier) <= prep["started_ns"],
                 "CPU preparation crossed its own group predecessor")
    overlap = sum(any(_stage(e) < _stage(p) and e["started_ns"] < p["finished_ns"]
                      and p["started_ns"] < e["finished_ns"] for e in work) for p in prepares)
    return {"schema": "saea-whole-node-panel-timing-v1", "panel_id": first["panel_id"],
            "jobs": jobs, "model_contacts": sum(e["kind"] == "model" for e in work),
            "barriers_verified": True, "prefetch_overlap_events": overlap, "stages": stages,
            "submission_to_terminal_mean_seconds": statistics.mean((s["finished_ns"] - s["batch_started_ns"]) / 1e9 for s in samples),
            "admission_to_terminal_mean_seconds": statistics.mean((s["finished_ns"] - s["admitted_ns"]) / 1e9 for s in samples),
            "first_admitted_seconds": (samples[0]["finished_ns"] - samples[0]["admitted_ns"]) / 1e9,
            "remaining_sample_mean_seconds": statistics.mean((s["finished_ns"] - s["admitted_ns"]) / 1e9 for s in samples[1:]),
            "group_mean_seconds": [statistics.mean((s["finished_ns"] - s["admitted_ns"]) / 1e9 for s in m["samples"]) for m in members],
            "scope": "Original recorded panel/sample/callback clocks;not exclusive GPU time,task quality or a speedup estimate."}
