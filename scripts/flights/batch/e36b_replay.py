"""E36b model-free replay: for the 18 sealed B9a-rec rows that routed ACQUIRE, how many values of the plan's released stores
(composite snapshot, hash-verified through the real loader) match the row's recorded state filters, excluding the ids the row
already held. Zero contacts. Prints counts and ids-free aggregates only (no value text, no utterance text)."""
import os
import json, io, glob, collections, sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
sys.path.insert(0, str(REPO / "src"))
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding

exp = json.load(io.open(REPO / "configs/experiment/slurp-native-plan-acquisition-b9a-recovery-v1.json", encoding="utf-8"))
cell = exp["cells"][0]
composed = compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], "slurp-native-plan-acquisition-b9a-recovery-v1")
binding = load_knowledge_store_binding(composed.values, data_root=DATA)
snap = binding.composite_snapshot
values = list(snap.values)
print("stores", list(binding.store_ids), "| composite values", len(values))
by_store = collections.Counter(next((s for s in binding.store_ids if v.value_id.startswith(s + "::")), "?") for v in values)
print("values per store", dict(by_store))

run = DATA / "runs/SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-V1/attempt-slurp-native-plan-acquisition-b9a-recovery-train-fold-a-generation-v1"
out = glob.glob(str(run / "*.outputs.jsonl"))[0]
supply = json.load(io.open(glob.glob(str(DATA / "prepared/SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-V1/phase-supply-v*.json"))[-1], encoding="utf-8"))
sup_values = (supply.get("output") or {}).get("values") or {}
print("prepared supply phases", list(sup_values.keys())[:5])


def visible_ids(sample_id):
    ids = set()
    for phase, rows in sup_values.items():
        for vid in (rows.get(sample_id) or []):
            ids.add(vid)
    return ids


def match(value, tokens):
    hay = [value.content.casefold()] + [f.casefold() for f in value.associated_facet_ids]
    return sum(1 for t in tokens if any(t in h for h in hay))


rows_hit = []
for line in io.open(out, encoding="utf-8"):
    r = json.loads(line); rec = r.get("native_episode_receipt") or {}
    acqs = (rec.get("acquisition") or {}).get("acquisitions") or []
    if not acqs:
        continue
    sid = r["sample_id"]
    vis = visible_ids(sid)
    for a in acqs:
        tokens = [str(t).casefold() for t in (a.get("state_filters") or [])]
        scored = []
        for v in values:
            if v.value_id in vis:
                continue
            m = match(v, tokens)
            if m:
                scored.append((m, v.value_id))
        scored.sort(key=lambda x: (-x[0], x[1]))
        top5 = scored[:5]
        rows_hit.append({"tokens": len(tokens), "visible": len(vis), "candidates": len(scored),
                         "top5_min_hits": min((m for m, _ in top5), default=0), "top5_max_hits": max((m for m, _ in top5), default=0),
                         "top5_stores": dict(collections.Counter(next((s for s in binding.store_ids if vid.startswith(s + "::")), "?") for _, vid in top5))})
print("ACQUIRE rows replayed", len(rows_hit))
print("candidates per row (non-visible values matching >= 1 token):", sorted(x["candidates"] for x in rows_hit))
print("rows with >= 1 candidate", sum(1 for x in rows_hit if x["candidates"]), "| with >= 5", sum(1 for x in rows_hit if x["candidates"] >= 5))
print("top-5 max token hits per row", sorted(x["top5_max_hits"] for x in rows_hit))
agg = collections.Counter()
for x in rows_hit: agg.update(x["top5_stores"])
print("top-5 items by store (all rows)", dict(agg))
print("visible ids per row", sorted(set(x["visible"] for x in rows_hit)), "| tokens per row", sorted(x["tokens"] for x in rows_hit))
