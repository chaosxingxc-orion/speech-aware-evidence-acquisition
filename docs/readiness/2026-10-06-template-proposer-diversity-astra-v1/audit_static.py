"""Read only pinned public templates and the qualified aggregate actor capsule.

Report lexical diversity; never read per-input custody or execute any proposal.
This is a historical audit utility, not an experiment gate or semantic judge.
"""
import collections
import copy
import hashlib
import itertools
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path("/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/system-text-search/context-template-k16-v1/partitioned-update5-aggregate-v1")
PINS = {
    "actor-capsule-v1/manifest.json": "0875fa089670b28ac7824d8a1f74937577e79f949906dd6c119290d2d7638793",
    "actor-capsule-v1/actor-input.json": "6e376dab0142b79a826a779792a2308c88d6c581b7ef7d9cba4c6670b8f77d45",
    "actor-capsule-v1/output-contract.json": "32f8558dbd5e3b6eab12442a8c6f769782f3b0fe263a6529972dffa113d566c4",
    "original-response-v1.json": "d271861c890b1f0862eee396c00c7573b043a3e4a85e1c3431ecbd9ffb459eb8",
}

def read_pinned(rel):
    raw = (BASE / rel).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PINS[rel], rel
    return json.loads(raw)

def grams(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return set(zip(*(words[i:] for i in range(5))))

def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else None

def summary(values):
    values = sorted(x for x in values if x is not None)
    return {"pairs": len(values), "min": min(values), "median": statistics.median(values), "max": max(values)} if values else {"pairs": 0}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def population(templates, nodes):
    k = len(templates)
    assemblies = collections.Counter(canonical({n: x[n] for n in ("context_layout", "node_context")}) for x in templates)
    roles = {}
    for node in nodes:
        texts = [x["role_text"][node] for x in templates]
        parts = [x.split("\n\n") for x in texts]
        counts = collections.Counter(p for ps in parts for p in set(ps) if p.strip())
        common = {p for p, count in counts.items() if count >= math.ceil(0.75*k)}
        stripped = ["\n\n".join(p for p in ps if p not in common) for ps in parts]
        raw_sets, stripped_sets = list(map(grams, texts)), list(map(grams, stripped))
        roles[node] = {"unique_exact_texts": len(set(texts)), "characters": {"min": min(map(len,texts)), "median": statistics.median(map(len,texts)), "max": max(map(len,texts))},
          "raw_pairwise_5gram_jaccard": summary(jaccard(a,b) for a,b in itertools.combinations(raw_sets,2)),
          "common_paragraph_removed_pairwise_5gram_jaccard": summary(jaccard(a,b) for a,b in itertools.combinations(stripped_sets,2)),
          "common_paragraph_count": len(common), "common_paragraph_threshold_candidates": math.ceil(.75*k),
          "common_paragraph_character_fraction_mean": statistics.mean(sum(len(p) for p in ps if p in common)/len(t) for ps,t in zip(parts,texts))}
    return {"candidate_count": k, "unique_complete_systems": len({canonical(x) for x in templates}), "assemblies": [{"settings":json.loads(a),"count":c} for a,c in sorted(assemblies.items())], "roles": roles}

def main():
    manifest = read_pinned("actor-capsule-v1/manifest.json")
    actor = read_pinned("actor-capsule-v1/actor-input.json")
    contract = read_pinned("actor-capsule-v1/output-contract.json")
    response = read_pinned("original-response-v1.json")
    config_path = ROOT / "configs/experiments/slurp-context-template-partitioned-update5-aggregate-n20-v1.json"
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    ids = [cid for c in config["cohorts"] for cid in c["candidate_ids"]]
    nodes = config["nodes"]
    assert ids == actor["candidate_order"] == contract["ordered_candidate_ids"]
    assert ids == [b["candidate_id"] for b in response["branches"]]
    assert actor["schema"] == "saea-aggregate-template-actor-view-v1"
    assert actor["learner_profile"] == "aggregate-template-records-v1"
    assert len(actor["records"]) == actor["observed_rounds"] * len(ids)
    assert response["input_sha256"] == actor["optimizer_input_sha256"]
    assert response["actor_input_sha256"] == manifest["actor_input_sha256"]
    parent_rows = {r["candidate_id"]:r for r in actor["records"] if r["is_active_parent"]}
    assert set(parent_rows) == set(ids)
    result = {"schema":"saea-template-proposer-static-audit-v1", "source_pins": PINS,
      "experiment_config": {"path":str(config_path.relative_to(ROOT)), "sha256":hashlib.sha256(config_bytes).hexdigest()},
      "K":len(ids), "M":len(nodes), "N":len({sid for c in config["cohorts"] for sid in c["sample_ids"]}),
      "T":actor["observed_rounds"], "aggregate_records":len(actor["records"]), "method":"Lowercase alphanumeric word 5-gram set Jaccard. Common paragraph removal deletes exact double-newline paragraphs present in >=ceil(.75*K) candidates for that node; it removes recurring semantics too, not just schemas. Diagnostic only.", "populations":{}, "proposal_changes":[]}
    for iteration in sorted({r["evaluated_iteration"] for r in actor["records"]}):
        rows = [r for r in actor["records"] if r["evaluated_iteration"] == iteration]
        assert len(rows) == len(ids)
        ts = [{k:v for k,v in r["template"].items() if k != "bundle_id"} for r in rows]
        result["populations"][str(iteration)] = population(ts,nodes)
    children=[]
    for branch in response["branches"]:
        proposal=branch["proposal"]; cid=branch["candidate_id"]
        parent=parent_rows[cid]["template"]
        assert proposal["parent_ids"] == [parent["bundle_id"]]
        child=copy.deepcopy({k:v for k,v in parent.items() if k != "bundle_id"})
        changes=proposal["changes"]
        child["role_text"].update(changes.get("role_text",{}))
        for k in ("context_layout","node_context"):
            if k in changes: child[k]=changes[k]
        children.append(child)
        result["proposal_changes"].append({"candidate_id":cid,"changed_roles":[n for n in nodes if child["role_text"][n]!=parent["role_text"][n]],"changed_assembly_fields":[k for k in ("context_layout","node_context") if child[k]!=parent[k]],"no_change":not changes})
    result["populations"]["5-proposed-only"]=population(children,nodes)
    print(json.dumps(result,indent=2,ensure_ascii=True))

if __name__ == "__main__":
    main()
