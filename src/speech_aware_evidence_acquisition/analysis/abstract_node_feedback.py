"""Deterministic content-free node feedback; grants no source READ or model authority."""
from __future__ import annotations
from collections import Counter
import json
import math
from ..rails.system_text_feedback import feedback_utility

ROLES = ("perception", "solver", "reviewer", "planner")
METRICS = ("client_transport_ms", "input_tokens", "reused_input_tokens", "evaluated_input_tokens",
           "generated_tokens", "prefill_ms", "generation_ms")
COUNT_KEYS = frozenset([f"{prefix}_{kind}" for prefix in ("slu_f1_word", "slu_f1_char", "slot_f1_exact")
                        for kind in ("tp", "fp", "fn")] + ["scenario_action_exact", "scenario_exact", "action_exact"])
FEEDBACK_SCHEMA = {
    "schema": "saea-abstract-node-feedback-v1",
    "node_columns": ["role_index", "visit_index", "interrupted", "output_features", "performance"],
    "roles": list(ROLES),
    "node_performance_columns": [*METRICS, "independent_quality_score"],
    "output_columns": {
        "perception": ["strict_schema", "candidates", "duplicate_intents", "nonempty_distinctions"],
        "solver": ["strict_schema", "entities", "unique_entities", "added_since_previous_valid_solver",
                   "removed_since_previous_valid_solver", "retained_since_previous_valid_solver", "intent_changed"],
        "reviewer": ["strict_schema", "findings", "type_meaning", "boundary", "existence",
                     "empty_fragment_findings", "fragments_present_in_latest_valid_solver", "checked"],
        "planner": ["strict_action", "action_index"]},
    "planner_actions": ["ACCEPT", "REVISE", "other"],
    "interpretation": "Counts and format checks describe recorded outputs, not their correctness. Entity deltas are exact type/filler multiset changes, not judged repairs. Fragment matches are literal source matches, not evidence validity. Node quality is unmeasured and null. Terminal utility uses official terminal counts and frozen reference F1; it is not official per-sample F1 or causal node credit. Missing measurements remain null. No utterance, entity value, label, knowledge, reason text or source address is exported."}

def _require(condition, message):
    if not condition:
        raise ValueError(message)

def _number(value, label):
    _require(type(value) in (int, float) and math.isfinite(value) and value >= 0, label)
    return value

def _object(text):
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None

def _task(value):
    return (isinstance(value, dict) and set(value) == {"scenario", "action", "entities"}
            and all(isinstance(value[k], str) and bool(value[k]) for k in ("scenario", "action"))
            and isinstance(value["entities"], list)
            and all(isinstance(e, dict) and set(e) == {"type", "filler"}
                    and all(isinstance(e[k], str) for k in e) for e in value["entities"]))

def abstract_output(role, text, *, previous_solver=None):
    """Return allowlisted structural counts only, never copied model content."""
    _require(role in ROLES and isinstance(text, str), "known role and text required")
    if role == "planner":
        action = text.strip()
        return [action in ("ACCEPT", "REVISE"), 0 if action == "ACCEPT" else 1 if action == "REVISE" else 2]
    obj = _object(text)
    bad = [False] + [None] * (len(FEEDBACK_SCHEMA["output_columns"][role]) - 1)
    if role == "solver":
        if not _task(obj):
            return bad
        pairs = Counter((e["type"], e["filler"]) for e in obj["entities"])
        prev = _object(previous_solver)
        delta = [None, None, None, None]
        if _task(prev):
            before = Counter((e["type"], e["filler"]) for e in prev["entities"])
            delta = [sum((pairs-before).values()), sum((before-pairs).values()),
                     sum((pairs & before).values()), (obj["scenario"], obj["action"]) != (prev["scenario"], prev["action"])]
        return [True, sum(pairs.values()), len(pairs), *delta]
    if role == "perception":
        if not (obj is not None and set(obj) == {"candidates"} and isinstance(obj["candidates"], list)
                and 1 <= len(obj["candidates"]) <= 3):
            return bad
        items = obj["candidates"]
        if not all(isinstance(e, dict) and set(e) == {"intent_id", "distinction", "evidence_refs", "unresolved_fields"}
                   and isinstance(e["intent_id"], str) and isinstance(e["distinction"], str)
                   and isinstance(e["evidence_refs"], list) and isinstance(e["unresolved_fields"], list) for e in items):
            return bad
        return [True, len(items), len(items)-len({e["intent_id"] for e in items}), sum(bool(e["distinction"]) for e in items)]
    if not (obj is not None and set(obj) == {"findings", "checked"}
            and isinstance(obj["findings"], list) and len(obj["findings"]) <= 4
            and isinstance(obj["checked"], list) and len(obj["checked"]) <= 8
            and all(isinstance(s, str) for s in obj["checked"])):
        return bad
    items = obj["findings"]
    if not all(isinstance(e, dict) and set(e) == {"kind", "slot_types", "draft_fragment", "reason"}
               and e["kind"] in ("type-meaning", "boundary", "existence")
               and isinstance(e["slot_types"], list) and 1 <= len(e["slot_types"]) <= 2
               and all(isinstance(s, str) for s in e["slot_types"])
               and isinstance(e["draft_fragment"], str) and isinstance(e["reason"], str)
               and len(e["reason"]) <= 512 for e in items):
        return bad
    kinds = Counter(e["kind"] for e in items)
    matches = (sum(bool(e["draft_fragment"]) and e["draft_fragment"] in previous_solver for e in items)
               if isinstance(previous_solver, str) else None)
    return [True, len(items), kinds["type-meaning"], kinds["boundary"], kinds["existence"],
            sum(not e["draft_fragment"] for e in items), matches, len(obj["checked"])]

def abstract_episode(contacts, *, counts, reference_f1, reliable, abstained, elapsed_seconds):
    """Project a source-qualified complete episode without any semantic summarizer.

    The caller must qualify the full family, seals, official scores and exact READ
    before joining these inputs. This pure function cannot authorize that read.
    """
    _require(isinstance(contacts, list) and bool(contacts), "complete contacts required")
    _require(type(reliable) is bool and type(abstained) is bool, "completion flags must be booleans")
    _number(elapsed_seconds, "finite nonnegative sample latency required")
    _require(isinstance(counts, dict) and set(counts) <= COUNT_KEYS, "unexpected score fields")
    numeric = {k: _number(v, "finite nonnegative official counts required") for k, v in counts.items()}
    utility = feedback_utility(numeric, reference_f1)
    nodes, previous, seen = [], None, set()
    last_visit = -1
    for contact in contacts:
        role, visit = contact["role"], contact["visit"]
        _require(role in ROLES and type(visit) is int and visit >= 0 and visit >= last_visit
                 and type(contact["interrupted"]) is bool, "node identity or order differs")
        last_visit = visit
        metrics = contact["measurements"]
        _require(isinstance(metrics, dict), "measurement object required")
        performance = [None if metrics.get(k) is None else _number(metrics[k], "invalid node cost") for k in METRICS]
        output = abstract_output(role, contact["text"], previous_solver=previous)
        nodes.append([ROLES.index(role), visit, contact["interrupted"], output, performance + [None]])
        seen.add(role)
        if role == "solver" and output[0] and not contact["interrupted"]:
            previous = contact["text"]
    return {"nodes": nodes, "missing_roles": [i for i, r in enumerate(ROLES) if r not in seen],
            "terminal": {"official_counts": numeric, "intent_correct": numeric.get("scenario_action_exact"),
                         "utility": utility, "official_aggregate_f1": None, "reliable": reliable,
                         "abstained": abstained, "sample_seconds": elapsed_seconds}}
