#!/usr/bin/env python3
"""Post-hoc query-surface diagnosis; no reranking, labels, or model calls."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import system_acquisition_requery_read as reader


def query_surface(review, filters, kept):
    """Count protocol artifacts without treating textual calls as executed tools."""
    try:
        parsed = json.loads(review)
    except ValueError:
        parsed = None
    review_only = reader.derive_state_filters({"review": review})
    review_only_tokens = reader.existing._tokenize(" ".join(review_only))
    return {
        "strict_json_tool_call_object": isinstance(parsed, dict) and "tool_call" in parsed,
        "tool_call_marker_in_review": "tool_call" in review,
        "retained_call_from_tool_call_filter": "tool_call" in filters and "call" in kept,
        "retained_acquire_token": "acquire" in kept,
        "acquire_key_introduced_by_hypothetical_action": (
            "acquire" in kept and "acquire" not in review_only_tokens),
        "retained_other_token": bool(set(kept) - {"call", "acquire"}),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    recipe, _ = reader._pinned_json(reader.REPO, {
        "relpath": "docs/readiness/2026-09-25-stage3-system-requery-read-v1.json",
        "sha256": "5c388bed87980bc066dba724655549c1872f189324a7fb0422ced6a0a3026f6c"},
        "replay recipe")
    replay, replay_sha = reader._pinned_json(args.data_root, {
        "relpath": recipe["output_relpath"],
        "sha256": "0d9e630c48b19b707cbdf0880641e9fde2310e11a2a156e183f4fb85c0080565"},
        "completed replay")
    out = {"schema": "saea-requery-query-surface-diagnostic-v1",
           "timing": "Post-hoc after availability replay; diagnostic only, no tuned policy.",
           "supersedes": "query-surface.json, whose retained ACQUIRE count did not establish whether review or hypothetical plan introduced it",
           "replay_sha256": replay_sha, "arms": {},
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "additional_retrieval_queries": 0, "model_contacts_added": 0,
           "scope": "Protocol markers are textual artifacts, not executed tool actions."}
    for arm, spec in recipe["arms"].items():
        feedback, _ = reader._pinned_json(args.data_root, spec["feedback"], "verified feedback")
        manifest, _ = reader._pinned_json(args.data_root, spec["source_bindings"]["manifest"], "manifest")
        ts = feedback["system_trajectories"]["trajectories"]
        records = reader.load_requests(manifest, args.data_root, ts)
        f = manifest["config"]["fragments"]
        cfg = reader.compose(reader.REPO, f["model"], f["dataset"], f["baseline"], f["experiment"])
        if cfg.config_hash != manifest["config"]["config_hash"]:
            raise ValueError("source configuration differs")
        binding = reader.load_knowledge_store_binding(cfg.values, data_root=args.data_root)
        values = {v.value_id: v for v in binding.composite_snapshot.values}
        vocabulary, df = reader.existing.build_vocabulary(values)
        replay_rows = {row["sample_id"]: row for row in replay["arms"][arm]["rows"]}
        rows = []
        for trajectory in ts:
            boundary = reader.review_boundary(trajectory, records)
            if boundary is None:
                rows.append({"sample_id": trajectory["sample_id"], "boundary_available": False})
                continue
            filters = reader.derive_state_filters({"review": boundary["review"], "plan": "ACQUIRE"})
            if reader.content_hash(list(filters)) != replay_rows[trajectory["sample_id"]]["filters_sha256"]:
                raise ValueError("query differs from completed replay")
            visible = set().union(*(vocabulary[e] for e in boundary["visible_ids"]))
            kept = {t for t in reader.existing._tokenize(" ".join(filters))
                    if len(t) >= 4 and df[t] > 0 and df[t] / len(values) <= 0.05 and t not in visible}
            rows.append({"sample_id": trajectory["sample_id"], "boundary_available": True,
                         **query_surface(boundary["review"], filters, kept)})
        counts = Counter()
        for row in rows:
            counts.update({k: int(v) for k, v in row.items()
                           if isinstance(v, bool)})
        available = [row for row in replay_rows.values() if row["boundary_available"]]
        returned_sets = Counter(tuple(row["returned_ids"]) for row in available)
        result = {"summary": dict(counts), "rows": rows,
                  "distinct_return_sets": len(returned_sets),
                  "top_three_return_set_counts": [v for _, v in returned_sets.most_common(3)]}
        out["arms"][arm] = result
        print(json.dumps({"arm": arm, **{k: v for k, v in result.items() if k != "rows"}}), flush=True)
    out["content_sha256"] = reader.content_hash(out)
    path = args.data_root / Path(recipe["output_relpath"]).parent / "query-surface-v2.json"
    print(json.dumps({"output": str(path), "sha256": reader.write_system_feedback(path, out)}))


if __name__ == "__main__":
    main()
