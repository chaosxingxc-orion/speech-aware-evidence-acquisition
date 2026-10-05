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


def _exact_fields(value, fields, label):
    _require(isinstance(value, dict) and set(value) == set(fields), label)


def _nonnegative_integer(value):
    return type(value) is int and value >= 0


def _validate_projected_nodes(nodes, missing_roles):
    _require(isinstance(nodes, list) and bool(nodes), "recorded nodes required")
    seen, previous_visit = set(), -1
    for node in nodes:
        _require(isinstance(node, list) and len(node) == 5, "node shape differs")
        role, visit, interrupted, output, performance = node
        _require(type(role) is int and 0 <= role < len(ROLES)
                 and _nonnegative_integer(visit) and visit >= previous_visit
                 and type(interrupted) is bool, "node identity or visit order differs")
        previous_visit = visit
        seen.add(role)
        _require(isinstance(performance, list) and len(performance) == len(METRICS) + 1
                 and performance[-1] is None, "node quality must remain unmeasured")
        for value in performance[:-1]:
            if value is not None:
                _number(value, "finite nonnegative measured cost required")
        columns = FEEDBACK_SCHEMA["output_columns"][ROLES[role]]
        _require(isinstance(output, list) and len(output) == len(columns)
                 and type(output[0]) is bool, "output feature shape differs")
        if ROLES[role] == "planner":
            _require(type(output[1]) is int and output[1] in (0, 1, 2)
                     and output[0] == (output[1] != 2), "planner action encoding differs")
        elif not output[0]:
            _require(all(v is None for v in output[1:]), "invalid output has unavailable features")
        else:
            for index, value in enumerate(output[1:], 1):
                if columns[index] == "intent_changed":
                    _require(value is None or type(value) is bool, "intent change must be abstract")
                else:
                    _require(value is None or _nonnegative_integer(value), "output counts must be abstract")
    _require(isinstance(missing_roles, list)
             and all(type(r) is int for r in missing_roles)
             and missing_roles == [r for r in range(len(ROLES)) if r not in seen],
             "missing role accounting differs")


def abstract_population_feedback(source, *, expected_bundles, expected_family_id,
                                 expected_source_batch, sample_count, reference_f1):
    """Validate one cohort against its caller's configured exact policy bindings.

    This pure boundary validates representation and exact caller-supplied bindings,
    not source authorization. The caller must first verify full-family READ, seals,
    official scores and source hashes. Returned relative returns are descriptive
    same-input preferences, never node credit, policy gradients or adoption.
    """
    import re
    _require(isinstance(expected_bundles, dict) and len(expected_bundles) >= 2
             and all(isinstance(k, str) and k and k.isascii() for k in expected_bundles)
             and all(isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
                     for v in expected_bundles.values()), "configured exact policy bindings required")
    return _abstract_cohort_feedback(source, expected_bundles=expected_bundles,
        expected_family_id=expected_family_id, expected_source_batch=expected_source_batch,
        sample_count=sample_count, reference_f1=reference_f1)


def _abstract_cohort_feedback(source, *, expected_bundles, expected_family_id,
                              expected_source_batch, sample_count, reference_f1):
    """Share projection validation after a public boundary fixes exact membership."""
    from copy import deepcopy
    from ..rails.hashing import content_hash
    from ..rails.system_text_feedback import paired_relative_returns

    ids = list(expected_bundles)
    _require(type(sample_count) is int and sample_count > 0, "positive input count required")
    _number(reference_f1, "finite frozen reference required")
    _require(reference_f1 <= 1, "frozen reference must use zero-to-one scale")
    _exact_fields(source, ("source_batch", "family_id", "reference_f1", "templates"),
                  "abstract source fields differ")
    _require(source["family_id"] == expected_family_id
             and source["source_batch"] == expected_source_batch
             and type(source["reference_f1"]) in (int, float)
             and source["reference_f1"] == reference_f1, "exact source cohort/reference required")
    templates = source["templates"]
    _require(isinstance(templates, list) and len(templates) == len(ids), "all original cohort templates required")
    groups = [{"input_index": i, "members": []} for i in range(sample_count)]
    summaries = []
    for cid, template in zip(ids, templates, strict=True):
        _exact_fields(template, ("candidate_id", "bundle_id", "official_summary", "samples"),
                      "template fields differ")
        _require(template["candidate_id"] == cid and template["bundle_id"] == expected_bundles[cid],
                 "template identity/order differs")
        summary = template["official_summary"]
        _exact_fields(summary, ("slu_f1", "intent"), "official summary fields differ")
        for value in summary.values():
            if value is not None:
                _number(value, "finite official measurement required")
        samples = template["samples"]
        _require(isinstance(samples, list) and len(samples) == sample_count, "complete paired roster required")
        for index, sample in enumerate(samples):
            _exact_fields(sample, ("input_index", "nodes", "missing_roles", "terminal"),
                          "abstract sample fields differ")
            _require(type(sample["input_index"]) is int and sample["input_index"] == index,
                     "anonymous input order differs")
            _validate_projected_nodes(sample["nodes"], sample["missing_roles"])
            terminal = sample["terminal"]
            _exact_fields(terminal, ("official_counts", "intent_correct", "utility", "official_aggregate_f1",
                                    "reliable", "abstained", "sample_seconds"), "terminal fields differ")
            counts = terminal["official_counts"]
            _require(isinstance(counts, dict) and set(counts) <= COUNT_KEYS
                     and all(type(v) in (int, float) and math.isfinite(v) and v >= 0
                             for v in counts.values()), "official count shape differs")
            required = {f"slu_f1_{axis}_{kind}" for axis in ("word", "char") for kind in ("tp", "fp", "fn")}
            _require(required <= set(counts), "complete official terminal counts required")
            intent = terminal["intent_correct"]
            _require((intent is None or type(intent) in (int, float) and intent in (0, 1))
                     and intent == counts.get("scenario_action_exact"), "intent correctness differs")
            utility = terminal["utility"]
            _require(type(utility) in (int, float) and math.isfinite(utility)
                     and utility == feedback_utility(counts, reference_f1), "terminal utility differs")
            _require(terminal["official_aggregate_f1"] is None
                     and type(terminal["reliable"]) is bool and type(terminal["abstained"]) is bool,
                     "terminal flags or aggregate distinction differs")
            _number(terminal["sample_seconds"], "finite nonnegative sample latency required")
            groups[index]["members"].append({"candidate_id": cid, "nodes": deepcopy(sample["nodes"]),
                "missing_roles": list(sample["missing_roles"]), "terminal": deepcopy(terminal)})
        summaries.append({"candidate_id": cid, "bundle_id": expected_bundles[cid],
                          "official_summary": deepcopy(summary)})
    for group in groups:
        relative = paired_relative_returns([m["terminal"]["utility"] for m in group["members"]])
        for member, value in zip(group["members"], relative, strict=True):
            member["relative_return"] = value
    return {"schema": "saea-abstract-population-feedback-v1", "source_sha256": content_hash(source),
            "templates": summaries, "groups": groups, "runtime_admission": False,
            "interpretation": "Same-input relative returns guide template search only; zero variance is zero. "
                              "Node correctness and causal contribution remain unmeasured."}


def abstract_partitioned_population_feedback(sources, *, expected_partitions, population_config):
    """Project the complete configured population, preserving separate cohorts.

    This is a pure representation boundary, not a source reader or authorization
    gate. Its caller must verify all configured complete-family READs, seals, unique
    official scores, source hashes, control records and ordered roster hashes.
    Never use this function to export a partial family or create model authority.
    Controls stay in their source-qualified family packages; no pooled frontier,
    across-panel relative return or combined adoption decision is produced here.
    """
    import re
    from ..rails.hashing import content_hash
    from ..rails.experiment_population import validate_population_config

    config = validate_population_config(population_config)
    panels = [c["cohort_id"] for c in config["cohorts"]]
    _exact_fields(sources, panels, "all configured source partitions required")
    _exact_fields(expected_partitions, panels, "all configured partition contracts required")
    contracts = ("expected_bundles", "expected_family_id", "expected_source_batch",
                 "reference_f1", "sample_order_sha256")
    cohorts = {}
    for cohort in config["cohorts"]:
        panel = cohort["cohort_id"]
        contract, source = expected_partitions[panel], sources[panel]
        _exact_fields(contract, contracts, "partition contract fields differ")
        _exact_fields(source, ("source_batch", "family_id", "reference_f1", "templates",
                               "sample_order_sha256"), "partition source fields differ")
        ids = cohort["candidate_ids"]
        bundles = contract["expected_bundles"]
        _require(isinstance(bundles, dict) and list(bundles) == ids
                 and all(isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v)
                         for v in bundles.values()), "exact configured policy bindings required")
        roster = contract["sample_order_sha256"]
        _require(isinstance(roster, str) and re.fullmatch(r"[a-f0-9]{64}", roster)
                 and source["sample_order_sha256"] == roster
                 and roster == content_hash(cohort["sample_ids"]), "exact configured ordered roster hash required")
        _require(all(isinstance(contract[k], str) and bool(contract[k])
                     for k in ("expected_family_id", "expected_source_batch")),
                 "nonempty cohort identities required")
        for previous in cohorts:
            prior = expected_partitions[previous]
            _require(all(contract[k] != prior[k] for k in ("expected_family_id", "expected_source_batch")),
                     "distinct source cohort identities required")
            _require(contract["reference_f1"] == prior["reference_f1"], "same frozen reference required")
        result = _abstract_cohort_feedback(
            {k: v for k, v in source.items() if k != "sample_order_sha256"},
            **{k: v for k, v in contract.items() if k != "sample_order_sha256"},
            sample_count=len(cohort["sample_ids"]))
        result.update(schema="saea-abstract-configured-cohort-feedback-v1",
                      family_id=contract["expected_family_id"],
                      source_batch=contract["expected_source_batch"],
                      sample_order_sha256=roster, reference_f1=contract["reference_f1"],
                      source_sha256=content_hash(source))
        cohorts[panel] = result
    return {"schema": "saea-abstract-configured-population-feedback-v1", "cohorts": cohorts,
            "population_config_sha256": content_hash(config),
            "runtime_admission": False,
            "interpretation": "Separate source cohorts cover every configured policy. "
                              "Normalize each input within its own configured cohort only. "
                              "Do not compare standardized returns across cohorts, pool frontiers, "
                              "infer independent replication or claim node credit."}
