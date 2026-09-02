"""Offline same-16 comparator for the frozen A2T G1 M0 output rows.

This module reads only sealed output JSONL files and scorer-side gold.  It
never opens audio, contacts a model, or uses the network.  The output rows
are copied unchanged so the comparator cannot silently alter the landed row
shape.
"""
from __future__ import annotations

import argparse, json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "src"))
from speech_aware_evidence_acquisition.data.audio2tool import load_expected_calls
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import parse_tool_calls_text, score_item
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter

G5_IDS = tuple(sorted(("tier1_direct:002609", "tier1_direct:002728", "tier2_parametric:003923", "tier2_parametric:006317", "tier3_multi_intent:002995", "tier3_multi_intent:003153", "tier4_implicit:001074", "tier4_implicit:001148", "tier5_needle:000241", "tier5_needle:002215", "tier6_correction:002179", "tier6_correction:003197", "tier7_multiturn:000545", "tier7_multiturn:002120", "tier8_intent_blending:000581", "tier8_intent_blending:000720")))

def rows(path: Path) -> dict[str, dict]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line); out[str(row["sample_id"])] = row
    return out

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--g5", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    m0path = Path(data_root()) / "runs/SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/arm1-m0-outputs.jsonl"
    m0 = rows(m0path)
    if not set(G5_IDS) <= set(m0): raise SystemExit("frozen G1 M0 does not cover G5 SELECTED_IDS")
    g5 = rows(args.g5)
    if set(g5) != set(G5_IDS): raise SystemExit("G5 outputs do not cover exactly SELECTED_IDS")
    lock = load_lock(REPO); root = data_root()
    expected = load_expected_calls(lock, root, repo_root=REPO)
    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    result = {"schema":"saea-a2t-g5-same16-comparator-v1", "selected_ids":list(G5_IDS), "m0_rows":[m0[sid] for sid in G5_IDS], "rows":[], "aggregate":{}}
    for sid in G5_IDS:
        sm = next(s for s in adapter.load_split("discovery") if s.sample_id == sid)
        def metric(row):
            pred, parsed = parse_tool_calls_text(str(row.get("final_response_text", row.get("response_text", ""))))
            sc = score_item(expected[sid], pred)
            return {"exact":int(sc.exact_match),"tool":int(sc.tool_accuracy),"slot_f1":sc.slot_f1,"parsed":int(parsed),"predicted_calls":len(pred)}
        a,b=metric(m0[sid]),metric(g5[sid]); result["rows"].append({"sample_id":sid,"m0":a,"g5":b,"paired":{"exact":"win" if b["exact"]>a["exact"] else "loss" if b["exact"]<a["exact"] else "tie","tool":"win" if b["tool"]>a["tool"] else "loss" if b["tool"]<a["tool"] else "tie"}})
    for key in ("exact","tool","parsed"):
        result["aggregate"][key]={arm:sum(r[arm][key] for r in result["rows"]) for arm in ("m0","g5")}
    result["aggregate"]["paired_exact"]={x:sum(r["paired"]["exact"]==x for r in result["rows"]) for x in ("win","loss","tie")}
    result["aggregate"]["paired_tool"]={x:sum(r["paired"]["tool"]==x for r in result["rows"]) for x in ("win","loss","tie")}
    args.out.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")

if __name__ == "__main__": main()
