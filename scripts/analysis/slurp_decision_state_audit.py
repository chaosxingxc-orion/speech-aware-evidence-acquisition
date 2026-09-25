#!/usr/bin/env python3
"""Source-pinned construction-state diagnostic; no inference or scoring."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/"src"))
from speech_aware_evidence_acquisition.analysis.slurp_decision_state_audit import (
    load_prefixes, summarize_audit,
)
from speech_aware_evidence_acquisition.analysis.system_feedback import write_system_feedback
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json, _confined_file
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root",type=Path,required=True)
    parser.add_argument("--recipe",type=Path,required=True)
    args = parser.parse_args()
    recipe = json.loads(args.recipe.read_text())
    if recipe.get("read_id") != "SAEA-SLURP-STAGE3-SYSTEM-DECISION-STATE-AUDIT-V1":
        raise ValueError("this read requires its registered diagnostic recipe")
    roster,_ = _pinned_json(REPO,recipe["roster"],"frozen roster")
    scenario_of = {item["sample_id"]:item["stratum"] for item in roster["items"]}
    snapshots,raw_pins = {},{}
    for name,pin in recipe["knowledge_snapshots"].items():
        path = _confined_file(args.data_root,pin["relpath"])
        raw = path.read_bytes()
        snapshot = KnowledgeSnapshot.from_frozen_json(json.loads(raw))
        if snapshot.content_hash() != pin["sha256"]:
            raise ValueError("released knowledge snapshot content differs")
        snapshots[name] = snapshot
        raw_pins[name] = {"relpath":pin["relpath"],"sha256":hashlib.sha256(raw).hexdigest(),
                         "snapshot_content_sha256":pin["sha256"]}
    legal = tuple(v.value_id.removeprefix("intent-boundary:")
                  for v in snapshots["intent-boundaries"].values)
    if len(legal)!=60 or len(set(legal))!=60:
        raise ValueError("released full label space differs")
    labels = {v.value_id:v.task_target for v in snapshots["train-exemplars"].values}
    if any(label not in legal for label in labels.values()):
        raise ValueError("released exemplar label is outside the legal inventory")
    sources = []
    for source in recipe["sources"]:
        print(json.dumps({"stage":"prefix-read","arm":source["label"]}),flush=True)
        result = load_prefixes(data_root=args.data_root, source_pin=source["feedback"],
            label=source["label"],legal_ids=legal,labels=labels,
            candidate_reader=recipe["candidate_reader"])
        if result["complete"]["split_identity_hash"]!=recipe["split_identity_hash"]:
            raise ValueError("source changed the registered split")
        sources.append(result)
    report = summarize_audit(sources,scenario_of=scenario_of,f0=recipe["frozen_f0"])
    report.update(read_id=recipe["read_id"],
        recipe_sha256=hashlib.sha256(args.recipe.read_bytes()).hexdigest(),
        sources=recipe["sources"],knowledge_sources=raw_pins,
        contacts_added=recipe["contacts"],frozen_f0=recipe["frozen_f0"],
        boundary=recipe["boundary"],interpretation=recipe["scope"])
    report["content_sha256"] = content_hash(report)
    output = args.data_root/recipe["output_relpath"]
    sha = write_system_feedback(output,report)
    print(json.dumps({"output":str(output),"sha256":sha,
        "actor_states":report["actor_states"],"repeat_stability":report["repeat_stability"]}),flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
