#!/usr/bin/env python3
"""Registered complete-system descriptive read; no model or scorer invocation."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from speech_aware_evidence_acquisition.analysis.native_episode_source import verify_native_episode_source
from speech_aware_evidence_acquisition.core.bundle.artifacts import _verify_artifact
from speech_aware_evidence_acquisition.analysis.slurp_system_attribution import (
    answer_view, describe_changes, summarize_rows, cross_node_summary, tool_activity_summary,
    candidate_recovery_view, candidate_recovery_summary,
)
from speech_aware_evidence_acquisition.analysis.system_feedback import write_system_feedback
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json
from speech_aware_evidence_acquisition.rails.hashing import content_hash
import slurp_var1_variant_read as var1


def _response(source, visit):
    final = visit["execution_receipt"]["final_contact"]
    return source.bundle.trace_records[final["request_id"] + "/response"]["text"]


def _candidate_ids(phase):
    for state in phase["agent_states"]:
        if state.get("state_kind") != "phase:perception":
            continue
        try:
            value = json.loads(state["content"])
        except (ValueError, TypeError):
            return []
        if not isinstance(value, dict) or not isinstance(value.get("candidates"), list):
            return []
        return [c["intent_id"] for c in value["candidates"]
                if isinstance(c, dict) and isinstance(c.get("intent_id"), str)]
    return []


def _context(source, visit):
    """Record supplied information, not an inferred semantic use of it."""
    contacts = []
    for contact in visit["execution_receipt"]["contacts"]:
        payload = source.bundle.trace_records[contact["request_id"] + "/request"]["payload"]
        history = payload.get("history", [])
        evidence = payload.get("supplied_evidence", [])
        tool_schemas = payload.get("tool_schemas", [])
        instruction_in_history = any(
            "call the available task-contract tool exactly once" in item.get("content", "")
            for item in history if isinstance(item, dict))
        contacts.append({
            "request_id": contact["request_id"],
            "speech_packet_sha256": payload.get("speech_packet_sha256"),
            "evidence_ids": sorted(item["evidence_id"] for item in evidence),
            "evidence_store_counts": dict(Counter(
                item["evidence_id"].split("::", 1)[0] for item in evidence)),
            "history_state_kinds": [item["state_kind"] for item in history if "state_kind" in item],
            "tool_schema_count": len(tool_schemas),
            "text_input_chars": {
                "task_instruction": len(payload.get("task_instruction", "")),
                "history": sum(len(item.get("content", "")) for item in history if isinstance(item, dict)),
                "supplied_evidence": sum(len(item.get("content", "")) for item in evidence),
            },
            "task_contract_call_required_without_schema": instruction_in_history and not tool_schemas,
        })
    return {"stage": visit["stage"], "contacts": contacts}


def analyze_arm(source, feedback, gold):
    if feedback["run_id"] != source.plan.run_id or feedback["attempt_id"] != source.plan.attempt_id:
        raise ValueError("feedback differs from the verified complete source")
    exported = feedback["system_trajectories"]
    if exported["source"]["phase_artifact_sha256"] != source.phase_artifact_sha256:
        raise ValueError("feedback refers to another phase source")
    if exported["source"]["outputs_sha256"] != source.bundle.manifest["outputs"]["sha256"]:
        raise ValueError("feedback refers to another output source")
    trajectories = {row["sample_id"]: row for row in exported["trajectories"]}
    terminal = {row["sample_id"]: row for row in feedback["terminal_feedback"]}
    ids = source.sample_ids
    if set(trajectories) != set(ids) or set(terminal) != set(ids) or not set(ids) <= set(gold):
        raise ValueError("complete trajectory population does not align")
    scores = json.loads(_verify_artifact(
        source.bundle.manifest["scores"], "attached scores",
        confine_to=source.bundle.manifest_path.resolve().parent))
    score_rows = {row["sample_id"]: row for row in
                  scores["slurp-slu-official-train"]["per_sample"]}
    rows = []
    for sid in ids:
        target = gold[sid]
        phase = source.phase_results[sid]
        native = phase["native_episode_receipt"]
        visits = native["role_visits"]
        solvers = [visit for visit in visits if visit["stage"] == "solver"]
        first = answer_view(_response(source, solvers[0]), target) if solvers else None
        last = answer_view(_response(source, solvers[-1]), target) if solvers else None
        delivered = answer_view(source.output_rows[sid]["text"], target)
        scores = score_rows[sid]
        for count in ("tp", "fp", "fn"):
            if delivered["entity_" + count] != scores["slot_f1_exact_" + count]:
                raise ValueError("exact diagnostic disagrees with sealed official exact counts")
        if delivered["intent_correct"] != bool(terminal[sid]["intent_exact"]):
            raise ValueError("intent diagnostic disagrees with terminal feedback")
        candidates = _candidate_ids(phase)
        covered = f"{target.scenario}_{target.action}" in candidates
        if not delivered["format_ok"]:
            error = "malformed"
        elif not delivered["intent_correct"]:
            error = "covered_intent_wrong" if covered else "uncovered_intent_wrong"
        elif delivered["entity_exact"]:
            error = "correct"
        else:
            error = "entity_" + ("mixed" if delivered["entity_fp"] and delivered["entity_fn"] else
                                "fp_only" if delivered["entity_fp"] else "fn_only")
        contexts = [_context(source, visit) for visit in visits]
        interrupted = native.get("interrupted_role")
        if interrupted:
            contexts.append({**_context(source, interrupted), "interrupted": True})
        row = {
            "sample_id": sid, "scenario": target.scenario,
            "trajectory_sha256": trajectories[sid]["trajectory_sha256"],
            "candidate_covered": covered, "candidate_count": len(set(candidates)),
            "empty_target": not target.entities,
            "solver_visits": len(solvers),
            "review_visits": sum(v["stage"] == "review" for v in visits),
            "planner_actions": [route["action"] for route in native["planner_routes"]],
            "routes": trajectories[sid]["planner_routes"],
            "first": first, "last": last, "delivered": delivered,
            "final_error_group": error,
            "fallback_flags": terminal[sid]["fallback_flags"],
            "role_context": contexts,
            "tool_events": trajectories[sid]["tool_events"],
            **describe_changes(first, last, delivered),
        }
        projection = trajectories[sid].get("candidate_proposal")
        if (("candidate_proposal" in native) != (projection is not None)
                or projection is not None and (
                    projection["receipt"] != native["candidate_proposal"]
                    or projection["receipt_sha256"] != content_hash(native["candidate_proposal"]))):
            raise ValueError("candidate proposal feedback differs from the whole verified source")
        candidate = candidate_recovery_view(
            trajectories[sid], gold_intent=f"{target.scenario}_{target.action}",
            first=first, last=last, delivered=delivered,
        )
        if candidate is not None:
            row["candidate_recovery"] = candidate
        rows.append(row)
    result = {
        "summary": summarize_rows(rows), "cross_node": cross_node_summary(rows),
        "rows": rows, "tool_activity": tool_activity_summary(rows),
    }
    candidates = candidate_recovery_summary(rows)
    if candidates is not None:
        result["candidate_recovery"] = candidates
    return result



def recipe_roster(recipe, repo_root):
    """Keep the historical recipe valid; require explicit pins for later reads."""
    if recipe.get("read_run_id") == "SAEA-SLURP-STAGE3-SYSTEM-TRAJECTORY-READ-V1":
        registered = json.loads((repo_root / "docs/readiness/2026-09-24-slurp-stage3-var1-v1/registered-facts-v1.json").read_text())
        roster_pin = registered["pins"]["roster"]
        pair = ("plan", "planr")
        legacy = True
    else:
        if (recipe.get("schema") != "saea-slurp-system-attribution-read-v1"
                or recipe.get("execution_profile") != "model-free-check"
                or recipe.get("feedback_role") != "construction"
                or recipe.get("status") != "sealed"):
            raise ValueError("attribution requires a registered construction read")
        registration, _ = _pinned_json(repo_root, recipe["registration"], "prospective attribution scope")
        if registration.get("read_id") != recipe.get("read_run_id"):
            raise ValueError("attribution registration identity differs")
        roster_pin = recipe["roster"]
        if roster_pin != registration.get("roster"):
            raise ValueError("attribution roster differs from registration")
        if set(recipe["arms"]) != set(registration["arms"]):
            raise ValueError("attribution arms differ from registration")
        for arm, expected in registration["arms"].items():
            run, attempt = expected["run_id"], expected["attempt_id"]
            if recipe["arms"][arm]["manifest"]["relpath"] != f"runs/{run}/{attempt}/{run}.run-manifest.json":
                raise ValueError("attribution source differs from registered run")
        pair = tuple(recipe["comparison"])
        legacy = False
    if len(pair)!=2 or pair[0]==pair[1] or set(pair)!=set(recipe["arms"]):
        raise ValueError("attribution comparison must cover exactly two distinct arms")
    roster = var1.load_roster(repo_root, roster_pin["relpath"], "utterance_id")
    if roster["sha256"] != roster_pin["sha256"] or roster["split_role"] != "discovery":
        raise ValueError("registered discovery roster changed")
    if not legacy and (roster["split_identity_hash"] != roster_pin["split_identity_hash"]
                       or len(roster["ids"]) != roster_pin["rows"]):
        raise ValueError("attribution split identity or size changed")
    return roster, pair, legacy


def run(args):
    recipe = json.loads(args.recipe.read_text())
    data = args.data_root
    roster, pair, legacy = recipe_roster(recipe, REPO)
    print(json.dumps({"stage": "governed-train-label-read", "rows": len(roster["ids"])}), flush=True)
    gold = var1.load_gold(args.lock, data, "train")
    out = {"schema": "saea-slurp-system-attribution-v1",
           "read_run_id": recipe["read_run_id"],
           "recipe_sha256": hashlib.sha256(args.recipe.read_bytes()).hexdigest(),
           "gold_metadata_sha256": gold["metadata_sha256"], "roster_sha256": roster["sha256"],
           "metric_scope": "Strict exact intermediate diagnostics, not official intermediate SLU-F1; official terminal scores reused",
           "arms": {}, "model_contacts_added": 0, "scorer_contacts_added": 0}
    pins = dict(value.split("=", 1) for value in args.feedback_sha256)
    if set(pins) != set(recipe["arms"]):
        raise ValueError("feedback pins must name every registered arm exactly")
    for arm, binding in recipe["arms"].items():
        print(json.dumps({"stage": "whole-source-attribution", "arm": arm}), flush=True)
        feedback, raw_sha = _pinned_json(data, {
            "relpath": recipe["output_relpath"] + "/" + arm + "-system-feedback.json",
            "sha256": pins[arm]}, "whole system feedback")
        unsigned = dict(feedback)
        if unsigned.pop("content_sha256") != content_hash(unsigned):
            raise ValueError("whole system feedback content changed")
        if feedback["source_bindings"] != binding:
            raise ValueError("feedback binding differs from registration")
        source = verify_native_episode_source(
            manifest_path=data / binding["manifest"]["relpath"],
            expected_manifest_sha256=binding["manifest"]["sha256"],
            phase_artifact_path=data / binding["phases"]["relpath"],
            expected_phase_sha256=binding["phases"]["sha256"],
            repo_root=args.source_repo_root, data_root=data)
        if set(source.sample_ids) != set(roster["ids"]):
            raise ValueError("source changed the full registered roster")
        result = analyze_arm(source, feedback, gold["records"])
        result["feedback_file_sha256"] = raw_sha
        out["arms"][arm] = result
        print(json.dumps({"stage": "attributed", "arm": arm, "summary":
                          {key: value for key, value in result["summary"].items() if key != "per_scenario"}}), flush=True)
        del source, feedback
    left = {row["sample_id"]: row for row in out["arms"][pair[0]]["rows"]}
    right = {row["sample_id"]: row for row in out["arms"][pair[1]]["rows"]}
    out["comparison"] = list(pair)
    out["repeat_task_stability" if legacy else "paired_terminal_task_agreement"] = dict(Counter(
        ("both_correct" if left[sid]["delivered"]["task_exact"] else "both_wrong")
        if left[sid]["delivered"]["task_exact"] == right[sid]["delivered"]["task_exact"]
        else "flipping" for sid in left))
    out["content_sha256"] = content_hash(out)
    sha = write_system_feedback(args.output, out)
    print(json.dumps({"status": "complete", "sha256": sha, "output": str(args.output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--source-repo-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--feedback-sha256", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
