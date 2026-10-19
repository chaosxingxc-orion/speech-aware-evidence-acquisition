"""Intent accuracy by gold rank on Perception's shortlist (DEV and Fold B v3.0 delivering arm). Aggregates only."""
import json, sys
from collections import Counter
sys.dont_write_bytecode = True
sys.path.insert(0, "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/analysis/gap_to_sota")
import gap_decomposition as G
lock = G.load_lock(G.LOCK)
out = {}
for name, spec in G.POPS.items():
    gold = {}
    for r in G.load_slurp_split(lock, G.DATA, spec["split"], workers=4):
        G.guard(r.sample_id)
        gold[r.sample_id] = {"intent": f"{r.scenario}_{r.action}", "scenario": r.scenario, "utt": r.utterance_id,
                             "ents": tuple(G.SlotEntity(type=e.type, filler=e.filler) for e in r.entities)}
    rows = G.load_pop(name, spec, gold)["rows"]
    tab = Counter(); ok = Counter(); bpos = Counter(); bok = Counter()
    for r in rows.values():
        k = "absent" if r["gold_intent"] not in r["cands"] else f"rank{r['cands'].index(r['gold_intent'])+1}_of_{len(r['cands'])}"
        tab[k] += 1; ok[k] += r["ok"]
        if r["gold_intent"] not in r["cands"]:
            b = "not_in_block" if r["gold_intent"] not in r["block"] else ("block_rank1" if r["block"][0] == r["gold_intent"] else "block_rank2-8")
            bpos[b] += 1; bok[b] += r["ok"]
    out[name] = {"by_shortlist_position": {k: {"n": tab[k], "acc": 100.0 * ok[k] / tab[k]} for k in sorted(tab)},
                 "absent_rows_by_block_position": {k: {"n": bpos[k], "acc": 100.0 * bok[k] / bpos[k]} for k in sorted(bpos)}}
print(json.dumps(out, indent=1))
open("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/analysis/gap_to_sota/rank-conversion.json", "w").write(json.dumps(out, indent=1) + "\n")
