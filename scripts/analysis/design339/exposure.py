#!/usr/bin/env python3
"""Harm exposure under the cite-and-protect verifier: delivered EXACT items whose value the Whisper transcript does NOT
contain (a revision of them would pass the 'replaced value absent from transcript' guard). Aggregates only."""
import importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b339", HERE / "asr_trigger_bound.py"); B = importlib.util.module_from_spec(spec)
sys.modules["b339"] = B; spec.loader.exec_module(B)
G, E5 = B.G, B.E5
lock = G.load_lock(G.LOCK); sp = G.POPS["FOLDB"]
gold_all = {}
for r in G.load_slurp_split(lock, G.DATA, "train", workers=4):
    G.guard(r.sample_id)
    gold_all[r.sample_id] = {"intent": f"{r.scenario}_{r.action}", "scenario": r.scenario, "utt": r.utterance_id,
                             "ents": tuple(G.SlotEntity(type=e.type, filler=e.filler) for e in r.entities)}
rows = G.load_pop("FOLDB", sp, gold_all)["rows"]
wtx, _ = E5.load_catalog(G.DATA, "fold-b")
ex = exp = sp_n = sp_in = emp_rows = emp_ff = 0
for s, r in rows.items():
    gl = list(r["gold"])
    for p in r["pred"]:
        if p in gl:
            gl.remove(p); ex += 1; exp += int(not B.contained(p.filler, wtx[s]["canon"]))
    st, spur = E5.gold_kinds(r["gold"], r["pred"])
    for pi in spur:
        sp_n += 1; sp_in += int(B.contained(r["pred"][pi].filler, wtx[s]["canon"]))
out = {"exact_items": ex, "exact_value_not_in_whisper": exp, "spurious_items": sp_n, "spurious_value_in_whisper": sp_in}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8"); print(json.dumps(out))
