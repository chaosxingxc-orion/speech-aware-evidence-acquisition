"""Audit actual pre-Solver state on sealed complete episodes, without learning."""
from __future__ import annotations

from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
from statistics import mean

from ..rails.finite_action_policy import official_utility
from ..rails.finite_policy_artifacts import _pinned_json
from ..rails.finite_supply_policy import agreement_state
from ..rails.hashing import content_hash
from ..rails.knowledge import AgentStateArtifact
from ..rails.slurp_intent_hypotheses import parse_slurp_intent_hypothesis_state
from .system_rollout_groups import load_group_source, _artifact, _jsonl


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def project_prefix(*, sample_id, perception_state, solver_payload, legal_ids, labels,
                   candidate_reader):
    """Use only the first Perception and the first Solver's supplied evidence.

    This boundary follows the fixed initial supply. It cannot be reused before
    Perception or to choose that supply without a separately logged preview.
    No terminal annotation, Planner route or future supply is accepted here.
    """
    state = AgentStateArtifact.from_json(perception_state)
    _require(solver_payload["sample_id"] == sample_id, "prefix crosses samples")
    parsed = parse_slurp_intent_hypothesis_state(
        state, expected_sample_id=sample_id, legal_intent_ids=legal_ids, **candidate_reader)
    candidates = tuple(item.intent_id for item in parsed.candidates)
    evidence = solver_payload.get("supplied_evidence")
    _require(isinstance(evidence, list), "prefix has no explicit evidence list")
    ids = [item["evidence_id"] for item in evidence
           if item["evidence_id"].startswith("train-exemplars::")]
    _require(len(ids) == len(set(ids)), "prefix repeats an exemplar")
    local_ids = tuple(item.split("::", 1)[1] for item in ids)
    _require(all(value in labels for value in local_ids), "prefix uses an unbound exemplar")
    agreement = agreement_state(candidates, [labels[v] for v in local_ids])
    raw = json.loads(state.content)
    raw_count = len(raw["candidates"])
    return {
        "status":"available",
        "boundary":"after-initial-supply-before-first-solver",
        "candidate_count":len(candidates), "raw_candidate_count":raw_count,
        "candidate_ids_sha256":content_hash(list(candidates)),
        "candidate_first_sha256":content_hash(candidates[0]),
        "perception_state_sha256":state.content_hash(),
        "exemplar_top_agreement":agreement, "exemplar_count":len(local_ids),
        "exemplar_ids_sha256":content_hash(sorted(local_ids)),
        "exemplar_ids":list(local_ids),
        "candidate_count_x_agreement":f"{len(candidates)}::{agreement}",
    }


def load_prefixes(*, data_root, source_pin, label, legal_ids, labels, candidate_reader):
    """Recheck previously verified complete sources and bind the precise prefix."""
    root = Path(data_root)
    complete = load_group_source(data_root=root, feedback_pin=source_pin, label=label)
    feedback, _ = _pinned_json(root, source_pin, "verified feedback")
    phases, _ = _pinned_json(root, feedback["source_bindings"]["phases"], "sealed phases")
    manifest, _ = _pinned_json(root, feedback["source_bindings"]["manifest"], "sealed manifest")
    phase_rows = {row["sample_id"]:row for row in phases["phases"][0]["results"]}
    trajectories = feedback["system_trajectories"]["trajectories"]
    _require(tuple(phase_rows) == tuple(complete["ordered_sample_ids"]), "phase order differs")
    wanted, by_id = {}, {}
    for trajectory in trajectories:
        sid = trajectory["sample_id"]
        _require(content_hash(phase_rows[sid]) == trajectory["source_phase_result_sha256"],
                 "phase differs from verified full trajectory")
        visits = trajectory["role_visits"]
        perception = next((v for v in visits if v["stage"] == "perception"), None)
        solver = next((v for v in visits if v["stage"] == "solver"), None)
        if not solver or not solver["contacts"]:
            by_id[sid] = {"sample_id":sid,"status":"not_reached"}
            continue
        _require(perception and perception["contacts"] and perception["index"] < solver["index"],
                 "first Solver lacks an earlier Perception")
        first = solver["contacts"][0]
        preceding = perception["contacts"][-1]
        wanted[first["request_record_id"]] = (sid, "solver", first["request_record_sha256"])
        wanted[preceding["response_record_id"]] = (sid, "perception", preceding["response_record_sha256"])
        by_id[sid] = {"trajectory":trajectory, "solver_contact":first,
                     "perception_contact":preceding, "records":{}}
    trace_path, trace_sha = _artifact(root, manifest["raw_trace"])
    for position, record in enumerate(_jsonl(trace_path, trace_sha)):
        binding = wanted.get(record["record_id"])
        if binding is None:
            continue
        sid, kind, expected = binding
        _require(kind not in by_id[sid]["records"], "prefix repeats a source record")
        _require(content_hash(record["payload"]) == expected, "prefix trace binding differs")
        by_id[sid]["records"][kind] = (position, record["payload"])
    rows = []
    for sid in complete["ordered_sample_ids"]:
        source = by_id[sid]
        if source.get("status") == "not_reached":
            rows.append(source)
            continue
        records = source["records"]
        _require(set(records) == {"solver","perception"}, "prefix trace is incomplete")
        _require(records["perception"][0] < records["solver"][0], "future Perception entered prefix")
        phase = phase_rows[sid]
        states = [s for s in phase["agent_states"] if s["state_kind"] == "phase:perception"]
        _require(bool(states), "Perception state is missing")
        state = states[0]
        _require(state["source_response_sha256"] == records["perception"][1]["response_text_sha256"],
                 "state is not the initial Perception response")
        payload = records["solver"][1]["payload"]
        _require(content_hash(payload) == source["solver_contact"]["request_payload_sha256"],
                 "first Solver payload differs")
        row = project_prefix(sample_id=sid,perception_state=state,solver_payload=payload,
            legal_ids=legal_ids,labels=labels,candidate_reader=candidate_reader)
        # Union is a diagnostic comparator only. Never feed it to project_prefix.
        union = sorted({v.split("::",1)[1] for wave in phase.get("waves",[])
                        for v in (wave.get("transition") or {}).get("new_value_ids",[])
                        if v.startswith("train-exemplars::")})
        row.update(sample_id=sid, trajectory_sha256=source["trajectory"]["trajectory_sha256"],
            solver_request_sha256=source["solver_contact"]["request_record_sha256"],
            solver_request_record_id=source["solver_contact"]["request_record_id"],
            whole_episode_union_matches_prefix=union == sorted(row["exemplar_ids"]),
            extra_later_exemplars=len(set(union)-set(row["exemplar_ids"])))
        rows.append(row)
    return {"label":label,"rows":rows,"complete":complete}


AXES = ("candidate_count","exemplar_top_agreement","candidate_count_x_agreement")


def _terminal_summary(rows, f0):
    if not rows:
        return {"rows":0}
    counts = {k:sum(row[k] for row in rows) for k in ("tp","fp","fn")}
    denominator = 2*counts["tp"]+counts["fp"]+counts["fn"]
    return {"rows":len(rows),**counts,
        "pooled_slu_f1":2*counts["tp"]/denominator if denominator else 0.0,
        "intent_accuracy":mean(row["intent_exact"] for row in rows),
        "mean_utility":mean(official_utility(tp=row["tp"],fp=row["fp"],fn=row["fn"],f0=f0) for row in rows),
        "fallback_rows":sum(bool(row["fallback_flags"]) for row in rows),
        "revision_reached":sum(row["revision_reached"] for row in rows)}


def summarize_audit(sources, *, scenario_of, f0):
    """Report occupancy/stability and a separate descriptive terminal join."""
    _require(len(sources)==2,"repeat audit requires exactly two complete sources")
    reference = sources[0]["complete"]
    ids = reference["ordered_sample_ids"]
    output = {"schema":"saea-system-decision-state-audit-result-v1","rows":len(ids),
              "actor_states":{},"terminal_diagnostics":{},"repeat_stability":{}}
    indexes = []
    for source in sources:
        _require(source["complete"]["ordered_sample_ids"]==ids,"repeat rosters differ")
        rows = source["rows"]
        index = {row["sample_id"]:row for row in rows}
        terminal = {row["sample_id"]:row for row in source["complete"]["rows"]}
        _require(list(index)==ids and set(scenario_of)==set(ids),"state/stratum population differs")
        indexes.append(index)
        available = [row for row in rows if row["status"]=="available"]
        block = {"available":len(available),"not_reached":len(rows)-len(available),
                 "normalized_width_changed":sum(row["raw_candidate_count"]!=row["candidate_count"] for row in available),
                 "whole_episode_union_differs":sum(not row["whole_episode_union_matches_prefix"] for row in available),
                 "axes":{}}
        diagnostics = {
            "all_rows":_terminal_summary([terminal[sid] for sid in ids],f0),
            "boundary_not_reached":_terminal_summary(
                [terminal[row["sample_id"]] for row in rows if row["status"]!="available"],f0),
        }
        for axis in AXES:
            groups = defaultdict(list)
            for row in available:
                groups[str(row[axis])].append(row["sample_id"])
            block["axes"][axis] = {
                cell:{"rows":len(members),"balanced_expected_below20_per_action":{
                    str(k):len(members)/k < 20 for k in (2,3)}}
                for cell,members in sorted(groups.items())}
            diagnostics[axis] = {}
            for cell,members in sorted(groups.items()):
                per_scenario = {s:_terminal_summary([terminal[sid] for sid in members if scenario_of[sid]==s],f0)
                                for s in sorted({scenario_of[sid] for sid in members})}
                diagnostics[axis][cell] = {
                    "natural":_terminal_summary([terminal[sid] for sid in members],f0),
                    "per_scenario":per_scenario,
                    "equal_present_scenario":{
                        metric:mean(v[metric] for v in per_scenario.values())
                        for metric in ("pooled_slu_f1","intent_accuracy","mean_utility")},
                    "interpretation":"Descriptive conditional outcomes, not action effects or a learned policy.",
                }
        output["actor_states"][source["label"]] = block
        output["terminal_diagnostics"][source["label"]] = diagnostics
    left,right = indexes
    fields = (*AXES,"candidate_ids_sha256","candidate_first_sha256","exemplar_ids_sha256")
    for field in fields:
        available = [sid for sid in ids if left[sid]["status"]==right[sid]["status"]=="available"]
        output["repeat_stability"][field] = {
            "comparable_rows":len(available),
            "changed":sum(left[sid][field]!=right[sid][field] for sid in available),
            "transition_counts":dict(Counter(
                f"{left[sid][field]} -> {right[sid][field]}" for sid in available))
                if field in AXES else None,
        }
    output["state_rows"] = {source["label"]:copy.deepcopy(source["rows"]) for source in sources}
    output["policy_updated"] = False
    return output
