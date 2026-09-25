#!/usr/bin/env python3
"""Replay existing acquisition availability on complete, source-bound trajectories.

No model, scorer, target labels or online policy execution. Raw state is resolved
only from previously verified source requests, and never copied into the report.
"""
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
import acquisition_requery_replay as existing
from speech_aware_evidence_acquisition.analysis.system_feedback import write_system_feedback
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.acquisition import (
    acquired_evidence_template, derive_state_filters, render_evidence_block,
)
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding

READ_ID = "SAEA-SLURP-STAGE3-SYSTEM-REQUERY-READ-V1"


def prefix_visits(trajectory):
    """Stop at the first Planner contact; a later revision cannot affect exclusion."""
    result = []
    for visit in trajectory["role_visits"]:
        result.append(visit)
        if visit["stage"] == "planner":
            return result
    return []


def review_boundary(trajectory, records):
    prefix = prefix_visits(trajectory)
    if not prefix or not prefix[-1]["contacts"]:
        return None
    visible = set()
    planner_payload = None
    planner_id = None
    for visit in prefix:
        contacts = visit["contacts"][:1] if visit["stage"] == "planner" else visit["contacts"]
        for contact in contacts:
            record = records[contact["request_record_id"]]
            payload = record["payload"]
            if (content_hash(record) != contact["request_record_sha256"]
                    or content_hash(payload) != contact["request_payload_sha256"]):
                raise ValueError("request fingerprint differs from verified export")
            if payload["sample_id"] != trajectory["sample_id"]:
                raise ValueError("request sample differs from trajectory")
            visible.update(item["evidence_id"] for item in payload["supplied_evidence"])
            if visit["stage"] == "planner":
                planner_payload = payload
                planner_id = contact["request_record_id"]
    reviews = [item for item in planner_payload["history"]
               if item.get("state_kind") == "phase:reviewer"]
    if len(reviews) != 1 or not isinstance(reviews[0].get("content"), str):
        raise ValueError("first Planner request must contain exactly one Reviewer state")
    return {"review": reviews[0]["content"], "visible_ids": sorted(visible),
            "planner_request_id": planner_id}


def require_known_evidence(ids, values):
    if not set(ids) <= set(values):
        raise ValueError("visible evidence is absent from the source knowledge snapshot")


def load_requests(manifest, data_root, trajectories):
    artifact = manifest["raw_trace"]
    path = Path(artifact["path"]).resolve()
    if not path.is_relative_to(data_root.resolve()):
        raise ValueError("trace path escapes data root")
    wanted = {contact["request_record_id"] for trajectory in trajectories
              for visit in prefix_visits(trajectory)
              for contact in (visit["contacts"][:1] if visit["stage"] == "planner"
                              else visit["contacts"])}
    digest = hashlib.sha256()
    records = {}
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            row = json.loads(line)
            if row["record_id"] in wanted:
                if row["record_id"] in records:
                    raise ValueError("duplicate trace record")
                records[row["record_id"]] = row["payload"]
    if digest.hexdigest() != artifact["sha256"] or set(records) != wanted:
        raise ValueError("trace hash or complete request set differs")
    return records


def replay_rows(trajectories, records, binding, native):
    values = {value.value_id: value for value in binding.composite_snapshot.values}
    vocabulary, frequency = existing.build_vocabulary(values)
    requery = existing.build_production_requery(native, binding)
    template = acquired_evidence_template(REPO)
    rows = []
    for trajectory in trajectories:
        row = {"sample_id": trajectory["sample_id"],
               "trajectory_sha256": trajectory["trajectory_sha256"]}
        boundary = review_boundary(trajectory, records)
        if boundary is None:
            rows.append({**row, "boundary_available": False})
            continue
        visible = boundary["visible_ids"]
        require_known_evidence(visible, values)
        filters = derive_state_filters({"review": boundary["review"], "plan": "ACQUIRE"})
        items = requery(phase_id="solver", filters=filters, exclude_value_ids=visible,
                        scope={"kinds": ["knowledge-requery"]}, context=None)
        ids = [item.evidence_id for item in items]
        diagnostic = existing._diagnose_row(
            filters=filters, exclude_value_ids=frozenset(visible),
            value_tokens=vocabulary, document_frequency=frequency, total_values=len(values),
            min_token_chars=4, max_document_frequency=0.05, exclude_visible_tokens=True, k=5)
        if ids != [entry[0] for entry in diagnostic["top"]] or set(ids) & set(visible):
            raise ValueError("production/diagnostic disagreement or repeated visible evidence")
        block = render_evidence_block(template, kind="knowledge-requery",
                                      policy_id="saea-acquire-knowledge-requery-v1", items=items)
        if not all(item.evidence_id in block for item in items):
            raise ValueError("registered evidence renderer omitted an acquired identity")
        rows.append({**row, "boundary_available": True,
                     "planner_request_id": boundary["planner_request_id"],
                     "review_sha256": content_hash(boundary["review"]),
                     "hypothetical_action": "ACQUIRE",
                     "filter_count": len(filters), "filters_sha256": content_hash(list(filters)),
                     "visible_ids": visible, "returned_ids": ids,
                     "returned_store_counts": dict(Counter(existing.store_of(binding, i) for i in ids)),
                     "returned_content_sha256": {item.evidence_id: content_hash(item.content)
                                                for item in items},
                     "rendered_block_sha256": content_hash(block),
                     "tokens_total": diagnostic["tokens_total"],
                     "tokens_kept": diagnostic["tokens_kept"],
                     "tokens_dropped_by_reason": diagnostic["tokens_dropped_by_reason"],
                     "candidate_count": diagnostic["candidates"]})
    available = [row for row in rows if row["boundary_available"]]
    drops, stores = Counter(), Counter()
    for row in available:
        drops.update(row["tokens_dropped_by_reason"])
        stores.update(row["returned_store_counts"])
    summary = {"rows": len(rows), "boundary_available": len(available),
               "boundary_unavailable": len(rows) - len(available),
               "nonempty_returns": sum(bool(row["returned_ids"]) for row in available),
               "return_count_distribution": dict(Counter(len(row["returned_ids"]) for row in available)),
               "tokens_kept_distribution": dict(Counter(row["tokens_kept"] for row in available)),
               "filter_count_distribution": dict(Counter(row["filter_count"] for row in available)),
               "tokens_dropped_by_reason": dict(drops), "returned_store_counts": dict(stores),
               "strata": "Not read: this availability diagnostic excludes target annotations.",
               "downstream_model_consumption": "Not executed; shared renderer only"}
    return {"knowledge_binding_sha256": binding.binding_sha256,
            "knowledge_values": len(values), "summary": summary, "rows": rows}


def run(args):
    recipe, recipe_sha = _pinned_json(REPO, {
        "relpath": str(args.recipe.resolve().relative_to(REPO)),
        "sha256": args.recipe_sha256}, "registered replay recipe")
    if recipe["read_run_id"] != READ_ID:
        raise ValueError("unregistered replay")
    policy = recipe["replay_policy"]
    if policy != {"policy": "saea-acquire-knowledge-requery-v1",
                  "retrieval": {"policy": "saea-requery-idf-v1", "min_token_chars": 4,
                                "max_document_frequency": 0.05, "exclude_visible_tokens": True},
                  "max_items_per_acquisition": 5, "max_state_filters": 8}:
        raise ValueError("registered retrieval parameters changed")
    experiment = "slurp-native-plan-acquisition-b9a-v2-v1"
    cell = existing._load_cell(REPO, experiment, experiment)
    e36 = compose(REPO, cell["model_fragment"], cell["dataset_fragment"],
                  cell["baseline_fragment"], experiment)
    native = existing.build_native_config(REPO, e36.values)
    if native.acquisition_retrieval != policy["retrieval"] or native.max_items_per_acquisition != 5:
        raise ValueError("held E36b configuration differs from registered replay")
    out = {"schema": "saea-system-requery-availability-v1", "read_run_id": READ_ID,
           "recipe_sha256": recipe_sha, "arms": {}, "model_contacts_added": 0,
           "scorer_contacts_added": 0, "scope": "hypothetical full-context availability only",
           "implementation_sha256": {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest()
                                    for name in [str(Path(__file__).relative_to(REPO)),
                                                 "scripts/analysis/acquisition_requery_replay.py",
                                                 "src/speech_aware_evidence_acquisition/core/flight/runtime.py",
                                                 "src/speech_aware_evidence_acquisition/rails/acquisition.py"]}}
    population = None
    for arm, spec in recipe["arms"].items():
        print(json.dumps({"stage": "source-bound-replay", "arm": arm}), flush=True)
        feedback, raw_sha = _pinned_json(args.data_root, spec["feedback"], "verified full-source feedback")
        unsigned = dict(feedback)
        if unsigned.pop("content_sha256") != content_hash(unsigned):
            raise ValueError("feedback content fingerprint mismatch")
        if feedback["source_bindings"] != spec["source_bindings"]:
            raise ValueError("feedback source bindings mismatch")
        exported = feedback["system_trajectories"]
        manifest, _ = _pinned_json(args.data_root, spec["source_bindings"]["manifest"], "source manifest")
        fragments = manifest["config"]["fragments"]
        composed = compose(REPO, fragments["model"], fragments["dataset"],
                           fragments["baseline"], fragments["experiment"])
        if composed.config_hash != manifest["config"]["config_hash"]:
            raise ValueError("source configuration has changed")
        binding = load_knowledge_store_binding(composed.values, data_root=args.data_root)
        if binding is None:
            raise ValueError("source knowledge binding is missing")
        trajectories = exported["trajectories"]
        ids = [row["sample_id"] for row in trajectories]
        if len(ids) != 625 or len(set(ids)) != 625 or set(ids) != set(exported["sample_ids"]):
            raise ValueError("whole registered population differs")
        if population is not None and population != set(ids):
            raise ValueError("replicate populations differ")
        population = set(ids)
        records = load_requests(manifest, args.data_root, trajectories)
        result = replay_rows(trajectories, records, binding, native)
        result["feedback_sha256"] = raw_sha
        result["trace_sha256"] = manifest["raw_trace"]["sha256"]
        result["config_hash"] = composed.config_hash
        out["arms"][arm] = result
        print(json.dumps({"arm": arm, "summary": result["summary"]}), flush=True)
    out["content_sha256"] = content_hash(out)
    output = args.data_root / recipe["output_relpath"]
    sha = write_system_feedback(output, out)
    print(json.dumps({"status": "complete", "output": str(output), "sha256": sha}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--recipe-sha256", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
