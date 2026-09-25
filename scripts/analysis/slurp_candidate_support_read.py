#!/usr/bin/env python3
"""Read candidate support from previously verified full TRAIN trajectories."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import mean
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from speech_aware_evidence_acquisition.analysis.slurp_candidate_support import candidate_sets
from speech_aware_evidence_acquisition.analysis.system_feedback import write_system_feedback
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact, KnowledgeSnapshot
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import parse_slurp_intent_hypothesis_state
import slurp_var1_variant_read as var1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(value):
    unsigned = dict(value)
    require(unsigned.pop("content_sha256") == content_hash(unsigned), "content fingerprint differs")


def summarize(rows):
    keys = list(rows[0]["coverage"])
    return {
        "rows": len(rows),
        "final_intent_accuracy": mean(r["final_intent_correct"] for r in rows),
        "exemplars_alone_covered": sum(r["exemplars_covered"] for r in rows),
        "projections": {
            key: {
                "covered": sum(r["coverage"][key] for r in rows),
                "coverage": mean(r["coverage"][key] for r in rows),
                "added_covered_over_baseline": sum(
                    r["coverage"][key] and not r["coverage"]["baseline"] for r in rows),
                "mean_candidate_count": mean(r["width"][key] for r in rows),
                "max_candidate_count": max(r["width"][key] for r in rows),
                "candidate_count_distribution": dict(sorted(Counter(r["width"][key] for r in rows).items())),
            } for key in keys
        },
        "terminal_contingency": {
            "covered_but_final_intent_wrong": sum(r["coverage"]["baseline"] and not r["final_intent_correct"] for r in rows),
            "missed_but_existing_examples_cover_and_final_intent_wrong": sum(
                not r["coverage"]["baseline"] and r["coverage"]["union"] and not r["final_intent_correct"] for r in rows),
            "both_miss_and_final_intent_wrong": sum(not r["coverage"]["union"] and not r["final_intent_correct"] for r in rows),
            "final_intent_correct_outside_baseline": sum(r["final_intent_correct"] and not r["coverage"]["baseline"] for r in rows),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    args = parser.parse_args()
    recipe = json.loads(args.recipe.read_text())
    require(recipe["read_id"] == "SAEA-SLURP-STAGE3-CANDIDATE-SUPPORT-READ-V1"
            and recipe["execution_profile"] == "model-free-check", "unregistered read")
    data = args.data_root
    audit, _ = _pinned_json(data, recipe["state_audit"], "actual prefix audit")
    fingerprint(audit)
    prior_recipe, prior_sha = _pinned_json(REPO, recipe["state_audit_recipe"], "prefix recipe")
    require(audit["recipe_sha256"] == prior_sha, "prefix recipe differs")
    roster, _ = _pinned_json(REPO, prior_recipe["roster"], "roster")
    ids = [item["sample_id"] for item in roster["items"]]
    require(len(ids) == len(set(ids)) == 625, "population differs")
    scenario_of = {item["sample_id"]: item["stratum"] for item in roster["items"]}
    snapshots = {}
    for key in ("intent-boundaries", "train-exemplars"):
        pin = {k: audit["knowledge_sources"][key][k] for k in ("relpath", "sha256")}
        raw, _ = _pinned_json(data, pin, "released knowledge")
        snapshot = KnowledgeSnapshot.from_frozen_json(raw)
        require(snapshot.content_hash() == audit["knowledge_sources"][key]["snapshot_content_sha256"],
                "released knowledge content differs")
        snapshots[key] = snapshot
    legal = tuple(v.value_id.removeprefix("intent-boundary:") for v in snapshots["intent-boundaries"].values)
    require(len(legal) == len(set(legal)) == 60, "full label inventory differs")
    labels = {v.value_id: v.task_target for v in snapshots["train-exemplars"].values}
    require(all(label in legal for label in labels.values()), "unknown exemplar label")
    prepared = {}
    for source in audit["sources"]:
        arm = source["label"]
        feedback, _ = _pinned_json(data, source["feedback"], "complete feedback")
        fingerprint(feedback)
        require(feedback["split_identity_hash"] == prior_recipe["split_identity_hash"]
                and feedback["feedback_role"] == "construction", "split/role differs")
        phases, _ = _pinned_json(data, feedback["source_bindings"]["phases"], "sealed phases")
        phase_rows = phases["phases"][0]["results"]
        state_rows = audit["state_rows"][arm]
        trajectories = feedback["system_trajectories"]["trajectories"]
        terminal = feedback["terminal_feedback"]
        require(all([r["sample_id"] for r in rows] == ids
                    for rows in (phase_rows, state_rows, trajectories, terminal)), "ordered population differs")
        rows = []
        for phase, state, trajectory, final in zip(phase_rows, state_rows, trajectories, terminal):
            require(state["status"] == "available", "this registered source has an unavailable prefix")
            require(content_hash(phase) == trajectory["source_phase_result_sha256"]
                    and trajectory["trajectory_sha256"] == state["trajectory_sha256"]
                    and final["trajectory_sha256"] == state["trajectory_sha256"], "trajectory custody differs")
            perception = next(s for s in phase["agent_states"] if s["state_kind"] == "phase:perception")
            artifact = AgentStateArtifact.from_json(perception)
            require(artifact.content_hash() == state["perception_state_sha256"], "initial state differs")
            parsed = parse_slurp_intent_hypothesis_state(artifact, expected_sample_id=state["sample_id"],
                legal_intent_ids=legal, **prior_recipe["candidate_reader"])
            candidates = [item.intent_id for item in parsed.candidates]
            require(content_hash(candidates) == state["candidate_ids_sha256"], "candidate projection differs")
            exemplar_ids = state["exemplar_ids"]
            require(len(exemplar_ids) == len(set(exemplar_ids))
                    and content_hash(sorted(exemplar_ids)) == state["exemplar_ids_sha256"],
                    "actual first-Solver exemplar identities differ")
            examples = [labels[value] for value in exemplar_ids]
            projections = candidate_sets(candidates, examples, recipe["candidate_caps"])
            rows.append({"state": state, "projections": projections, "examples": set(examples),
                         "final": final})
        prepared[arm] = rows
    print(json.dumps({"stage": "all-actor-prefixes-verified", "arms": list(prepared)}), flush=True)
    gold = var1.load_gold(args.lock, data, "train")
    out = {
        "schema": "saea-slurp-candidate-support-result-v1",
        "read_id": recipe["read_id"],
        "recipe_sha256": hashlib.sha256(args.recipe.read_bytes()).hexdigest(),
        "state_audit": recipe["state_audit"],
        "gold_metadata_sha256": gold["metadata_sha256"],
        "source_feedback": audit["sources"],
        "interpretation": recipe["interpretation"],
        "contacts_added": recipe["contacts_added"],
        "policy_updated": False, "system_gain_measured": False, "arms": {},
    }
    for arm, inputs in prepared.items():
        rows = []
        for item in inputs:
            state = item["state"]
            sid = state["sample_id"]
            target = gold["records"][sid]
            require(target.scenario == scenario_of[sid], "scenario binding differs")
            wanted = f"{target.scenario}_{target.action}"
            projections = item["projections"]
            rows.append({
                "sample_id": sid, "trajectory_sha256": state["trajectory_sha256"],
                "scenario": scenario_of[sid], "agreement_state": state["exemplar_top_agreement"],
                "exemplars_covered": wanted in item["examples"],
                "coverage": {k: wanted in v for k, v in projections.items()},
                "width": {k: len(v) for k, v in projections.items()},
                "projection_sha256": {k: content_hash(v) for k, v in projections.items()},
                "final_intent_correct": bool(item["final"]["intent_exact"]),
            })
        scenarios = {s: summarize([r for r in rows if r["scenario"] == s])
                     for s in sorted(set(scenario_of.values()))}
        out["arms"][arm] = {
            "natural": summarize(rows), "per_scenario": scenarios,
            "equal_scenario_coverage": {k: mean(v["projections"][k]["coverage"] for v in scenarios.values())
                                      for k in rows[0]["coverage"]},
            "by_agreement": {s: summarize([r for r in rows if r["agreement_state"] == s])
                             for s in sorted({r["agreement_state"] for r in rows})},
            "rows": rows,
        }
    out["content_sha256"] = content_hash(out)
    output = data / recipe["output_relpath"]
    digest = write_system_feedback(output, out)
    print(json.dumps({"output": str(output), "sha256": digest,
                      "summary": {k: v["natural"] for k, v in out["arms"].items()}}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
