"""Bind preserved numeric response measurements to one finite server-log prefix.

This pure analysis helper grants no READ permission. Call it only after the
original complete-family reader, or an explicitly qualified structural proof.
It does not contact an endpoint, change a slot, read a quality value or infer a
cache hit from final residency. Exact textual context identity is descriptive;
it is not proof that the tokenizer produced an identical full prefix.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from statistics import mean

from ..rails.hashing import content_hash


class SlotHistoryError(ValueError):
    """Original numeric measurements do not uniquely establish slot custody."""


_LINE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)\.(\d+) I slot\s+[^:]+: id\s+(\d+)\s*\| task\s+(\d+)\s*\| (.*)$")
_PROMPT = re.compile(r"prompt eval time =\s*([0-9.]+) ms /\s*(\d+) tokens")
_DECODE = re.compile(r"eval time =\s*([0-9.]+) ms /\s*(\d+) tokens")
_STOP = re.compile(r"stop processing: n_tokens = (\d+), truncated = (\d+)")
_SPEECH = re.compile(r"decoded mmproj-free speech feature chunk, n_tokens = (\d+)")
_PRESSURE = ("cache size limit", "cache token limit", "context shift", "purging", "evict")
_MEASUREMENTS = ("input_tokens", "reused_input_tokens", "evaluated_input_tokens",
                 "generated_tokens", "prefill_ms", "generation_ms", "client_transport_ms")
_CUSTODY = ("request_id", "sample_id", "role_id", "requested_slot_id",
            "system_message_sha256", "role_query_sha256", "request_body_sha256")


def _require(ok, message):
    if not ok:
        raise SlotHistoryError(message)


def contacts_from_numeric_members(numeric, members):
    """Join every original wire-context contact and numeric node-cost contact."""
    runs = [m["run_id"] for m in members]
    _require(runs and len(set(runs)) == len(runs) and set(numeric) == set(runs),
             "numeric family must match every registered member")
    result = []
    for member in members:
        run = member["run_id"]
        source = numeric[run]
        costs = source["node_timing"]["contacts"]
        wires = source["context_execution"]["contacts"]
        index = {c["request_id"]: c for c in costs}
        _require(len(index) == len(costs) and len({c["request_id"] for c in wires}) == len(wires)
                 and set(index) == {c["request_id"] for c in wires} and wires,
                 "wire and node-cost contact coverage differs")
        for wire in wires:
            cost = index[wire["request_id"]]
            _require(all(cost[k] == wire[k] for k in ("sample_id", "role_id")),
                     "numeric contact belongs to another sample or role")
            result.append({
                "run_id": run, "layout": member["layout"], "schedule": member["schedule"],
                **{k: wire[k] for k in _CUSTODY},
                "measurements": dict(cost["measurements"]),
            })
    return result


def _tasks(lines):
    tasks = {}
    for lineno, line in enumerate(lines, 1):
        match = _LINE.match(line)
        if not match:
            continue
        minutes, seconds, millis, micros, slot, task_id = map(int, match.groups()[:6])
        at = minutes * 60 + seconds + millis / 1000 + micros / 1000000
        message = match[7].strip()
        task = tasks.setdefault(task_id, {
            "task_id": task_id, "actual_slot_id": slot, "speech_chunk_tokens": []})
        _require(task["actual_slot_id"] == slot, "server task changed slot identity")
        if message.startswith("processing task,"):
            _require("start_line" not in task, "server task has duplicate start; log epochs may be mixed")
            task.update(start_line=lineno, start_seconds=at)
        for pattern, keys in (
                (_PROMPT, ("prefill_ms", "evaluated_input_tokens")),
                (_DECODE, ("generation_ms", "generated_tokens"))):
            measured = pattern.match(message)
            if measured:
                values = (float(measured[1]), int(measured[2]))
                _require(math.isfinite(values[0]), "nonfinite server measurement")
                for key, value in zip(keys, values):
                    _require(key not in task or task[key] == value, "server task has conflicting timing")
                    task[key] = value
        stopped = _STOP.match(message)
        if stopped:
            _require("release_line" not in task, "server task has duplicate release")
            task.update(release_line=lineno, release_seconds=at, truncated=int(stopped[2]))
        speech = _SPEECH.match(message)
        if speech:
            task["speech_chunk_tokens"].append(int(speech[1]))
    return tasks


def _validated_contacts(contacts):
    rows = list(contacts)
    _require(rows, "complete contact list is empty")
    seen = set()
    for row in rows:
        for key in ("run_id", "request_id", "sample_id", "role_id", "layout", "schedule"):
            _require(isinstance(row.get(key), str) and row[key], "contact identity is missing")
        identity = (row["run_id"], row["request_id"])
        _require(identity not in seen, "duplicate original contact")
        seen.add(identity)
        slot = row.get("requested_slot_id")
        _require(slot is None or type(slot) is int and slot >= -1, "invalid requested slot")
        for key in ("system_message_sha256", "role_query_sha256", "request_body_sha256"):
            _require(isinstance(row.get(key), str) and re.fullmatch("[0-9a-f]{64}", row[key]),
                     "context or request hash is invalid")
        values = row.get("measurements", {})
        for key in _MEASUREMENTS:
            value = values.get(key)
            if key in ("evaluated_input_tokens", "generated_tokens", "prefill_ms", "generation_ms"):
                _require(value is not None, "required original timing is unavailable")
            if value is not None:
                kind = type(value) is int if key.endswith("tokens") else type(value) in (int, float)
                _require(kind and value >= 0 and math.isfinite(value), "invalid original measurement")
    return rows


def _summary(rows):
    groups = defaultdict(list)
    for row in rows:
        key = (row["schedule"], row["layout"], row["role_id"], row["successor_kind"])
        groups[key].append(row)
    result = []
    for (schedule, layout, role, kind), group in sorted(groups.items()):
        measurements = {}
        for name in _MEASUREMENTS:
            values = [r["measurements"].get(name) for r in group]
            known = [v for v in values if v is not None]
            measurements[name] = {
                "observed_contacts": len(known), "total_contacts": len(group),
                "mean_observed": mean(known) if known else None,
                "complete_total": sum(known) if len(known) == len(group) else None}
        result.append({"schedule": schedule, "layout": layout, "role_id": role,
                       "successor_kind": kind, "contacts": len(group), "measurements": measurements})
    return result


def audit_slot_history(contacts, server_log: bytes, *, expected_sha256: str):
    """Require a unique timing/count join for every original model invocation.

    The pinned build logs milliseconds rounded to two decimals. Match within
    0.0051 ms, both measured token counts and both timing fields; never use a
    requested slot to resolve a collision. Reject absent/ambiguous/reused tasks,
    truncation, conflicting identity and overlapping tasks on an actual slot.
    Preserve unrelated predecessor tasks rather than skipping to a convenient
    known contact. Only line numbers of scoped pressure events leave this helper.
    """
    rows = _validated_contacts(contacts)
    _require(isinstance(server_log, bytes) and hashlib.sha256(server_log).hexdigest() == expected_sha256,
             "finite server log hash differs")
    try:
        lines = server_log.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise SlotHistoryError("server log is not UTF-8") from error
    tasks = _tasks(lines)
    by_counts, by_slot = defaultdict(list), defaultdict(list)
    for task in tasks.values():
        if "start_line" in task:
            by_slot[task["actual_slot_id"]].append(task)
        required = ("start_line", "release_line", "prefill_ms", "generation_ms",
                    "evaluated_input_tokens", "generated_tokens")
        if all(k in task for k in required):
            _require(task["start_line"] < task["release_line"]
                     and task["start_seconds"] <= task["release_seconds"], "server task clock/order reverses")
            by_counts[(task["evaluated_input_tokens"], task["generated_tokens"])].append(task)
    previous = {}
    for group in by_slot.values():
        group.sort(key=lambda t: t["start_line"])
        for left, right in zip(group, group[1:]):
            if "release_seconds" in left:
                _require(left["release_seconds"] <= right["start_seconds"],
                         "server tasks overlap on one actual slot")
            previous[right["task_id"]] = left
    joined, used = [], set()
    for row in rows:
        values = row["measurements"]
        options = [t for t in by_counts[(values["evaluated_input_tokens"], values["generated_tokens"])]
                   if abs(t["prefill_ms"] - values["prefill_ms"]) <= .0051
                   and abs(t["generation_ms"] - values["generation_ms"]) <= .0051]
        _require(len(options) == 1, "original contact has missing or ambiguous server task")
        task = options[0]
        _require(task["task_id"] not in used, "multiple contacts reused one server task")
        used.add(task["task_id"])
        _require(row["requested_slot_id"] in (None, -1, task["actual_slot_id"])
                 and task["truncated"] == 0, "actual slot differs or server truncated the request")
        joined.append({**row, "measurements": dict(values), "server": dict(task)})
    indexed = {r["server"]["task_id"]: r for r in joined}
    joined.sort(key=lambda r: r["server"]["start_line"])
    for row in joined:
        predecessor = previous.get(row["server"]["task_id"])
        prior = indexed.get(predecessor["task_id"]) if predecessor else None
        same_sample = bool(prior and prior["sample_id"] == row["sample_id"])
        same_context = bool(prior and all(prior[k] == row[k] for k in (
            "layout", "system_message_sha256", "role_query_sha256")))
        if prior is None:
            kind = "outside-family" if predecessor else "log-boundary"
        elif prior["role_id"] != row["role_id"]:
            kind = "different-node-" + ("same-sample" if same_sample else "different-sample")
        elif not same_context:
            kind = "same-node-context-change"
        else:
            kind = "same-node-same-context-" + ("same-sample" if same_sample else "different-sample")
        row.update(
            previous_server_task_id=predecessor["task_id"] if predecessor else None,
            previous_contact={"run_id": prior["run_id"], "request_id": prior["request_id"]} if prior else None,
            same_sample=same_sample if prior else None, same_context_identity=same_context if prior else None,
            same_request_body=(prior["request_body_sha256"] == row["request_body_sha256"]) if prior else None,
            successor_kind=kind)
    first = min(r["server"]["start_line"] for r in joined)
    last = max(r["server"]["release_line"] for r in joined)
    report = {
        "schema": "saea-llama-slot-history-v1", "server_log_sha256": expected_sha256,
        "server_log_bytes": len(server_log), "contact_scope_lines": [first, last],
        "contacts": joined, "summary": _summary(joined), "server_assignment_verified": True,
        "pressure_event_lines": {term: [i for i in range(first, last + 1) if term in lines[i - 1].lower()]
                                 for term in _PRESSURE},
        "model_contacts_added": 0, "scorer_contacts_added": 0,
        "limitations": [
            "Overlapping contact timers are not exclusive GPU time; queue delay is not inferred.",
            "Same role, context identity or input is not proof of identical token prefixes; use measured reuse.",
            "A repeated sample may reuse speech/history; do not equate it with changed-input static-prefix reuse.",
            "No logged pressure event in this finite scope does not prove that eviction is impossible.",
            "Only a unique numeric timing/count match establishes the observed slot; no slot is inferred.",
            "Inherited slot state, request order and coupled scheduling limit causal interpretation.",
        ]}
    report["content_sha256"] = content_hash(report)
    return report
