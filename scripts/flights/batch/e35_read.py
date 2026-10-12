"""E35 read (model-free, decision 58): the Earnings21 + ConEC carrier on FlightRuntime -- structural proof of the four-row pair
and the descriptive direct-versus-system contrast of the sub10 pair (10 calls, 342 windows) from the SEALED per-sample official
scores (asr-wer-whisper, conec-entity-wer-official, numeric-value-accuracy-v1, semantic-high-impact-error-rate-v1) and the
flight receipts. Prints counts, rates and hashes only -- never transcript text or gold. n = 10 calls: no effectiveness claim."""
import glob
import hashlib
import io
import json
import statistics
import sys

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
CELLS = {
    "four-row": {"direct": ("SAEA-E21-NATIVE-WINDOW-DIRECT-FOUR-ROW-V1", "attempt-e21-native-window-direct-four-row-v1"),
                 "system": ("SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1", "attempt-e21-native-window-system-four-row-recovery-v4")},
    "sub10": {"direct": ("SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1", "attempt-e21-native-window-direct-sub10-v1"),
              "system": ("SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1", "attempt-e21-native-window-system-sub10-v1")},
}
OUT = f"{DATA}/analysis/SAEA-E21-NATIVE-WINDOW-FLIGHTRUNTIME-E35-READ-V1"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load(run, att):
    d = f"{DATA}/runs/{run}/{att}"
    scores = glob.glob(f"{d}/*.scores.json"); outputs = glob.glob(f"{d}/*.outputs.jsonl"); manifest = glob.glob(f"{d}/*.run-manifest.json")
    if not (scores and outputs and manifest):
        return None
    sc = json.load(io.open(scores[0], encoding="utf-8")); man = json.load(io.open(manifest[0], encoding="utf-8"))
    rows = [json.loads(l) for l in io.open(outputs[0], encoding="utf-8")]
    att_rec = json.load(io.open(f"{DATA}/attempts/{run}/{att}.json", encoding="utf-8"))
    per_call = {}
    for scorer in ("asr-wer-whisper", "conec-entity-wer-official", "numeric-value-accuracy-v1", "semantic-high-impact-error-rate-v1"):
        for r in sc.get(scorer, {}).get("per_sample", []):
            sid = r.get("sample_id"); per_call.setdefault(sid, {})[scorer] = {k: v for k, v in r.items() if isinstance(v, (int, float)) and k not in ("sample_id",)}
    receipts = {}
    for r in rows:
        rec = r.get("native_episode_receipt") or {}
        units = r.get("execution_unit_delivery") or {}
        receipts[r["sample_id"]] = {"has_native_receipt": bool(rec), "planner_routes": [p.get("action") for p in (rec.get("planner_routes") or [])],
                                    "role_visits": [v.get("stage") for v in (rec.get("role_visits") or [])], "units_delivered": len(units) if isinstance(units, (list, dict)) else None}
    agg = {s: {k: v for k, v in sc[s]["aggregate"].items() if isinstance(v, (int, float))} for s in sc if isinstance(sc[s], dict) and "aggregate" in sc[s]}
    return {"run": run, "attempt": att, "state": att_rec.get("state"), "actual": att_rec.get("actual"), "manifest_status": man.get("status"), "study_commit": man.get("study_commit"),
            "rows": len(rows), "per_call": per_call, "receipts": receipts, "aggregate": agg, "sha256": {"scores": sha(scores[0]), "outputs": sha(outputs[0]), "manifest": sha(manifest[0])}}


report = {"schema": "saea-e35-flightruntime-read-v1", "execution_profile": "model-free-check", "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0}, "pairs": {}}
for pair, arms in CELLS.items():
    block = {}
    for arm, (run, att) in arms.items():
        block[arm] = load(run, att)
    d, s = block.get("direct"), block.get("system")
    if d and s and set(d["per_call"]) == set(s["per_call"]):
        calls = sorted(d["per_call"])
        contrast = {}
        for scorer, metric in (("asr-wer-whisper", "wer"), ("conec-entity-wer-official", "wer"), ("numeric-value-accuracy-v1", "accuracy"), ("semantic-high-impact-error-rate-v1", "high_impact_error_rate")):
            dv = [next((v for k, v in d["per_call"][c].get(scorer, {}).items() if metric in k), None) for c in calls]
            sv = [next((v for k, v in s["per_call"][c].get(scorer, {}).items() if metric in k), None) for c in calls]
            pairs_ = [(a, b) for a, b in zip(dv, sv) if a is not None and b is not None]
            if pairs_:
                deltas = [b - a for a, b in pairs_]
                contrast[scorer] = {"metric_key_contains": metric, "n_calls": len(pairs_), "direct_mean": round(statistics.mean(a for a, _ in pairs_), 4), "system_mean": round(statistics.mean(b for _, b in pairs_), 4),
                                    "delta_mean_system_minus_direct": round(statistics.mean(deltas), 4), "calls_improved": sum(1 for x in deltas if x < 0) if metric != "accuracy" else sum(1 for x in deltas if x > 0),
                                    "calls_worse": sum(1 for x in deltas if x > 0) if metric != "accuracy" else sum(1 for x in deltas if x < 0)}
        block["contrast_system_minus_direct"] = contrast
        block["note"] = "four-row: 4 windows of one call scored against the whole call's reference (structural only, deletions dominate by construction)" if pair == "four-row" else "sub10: whole calls; descriptive, n = 10 calls (no effectiveness claim, CLAUDE.md n >= 400)"
    report["pairs"][pair] = block
import os
os.makedirs(OUT, exist_ok=True)
raw = json.dumps(report, indent=2, sort_keys=True)
io.open(f"{OUT}/e35-read.json", "w", encoding="utf-8", newline="\n").write(raw + "\n")
for pair, block in report["pairs"].items():
    print("==", pair)
    for arm in ("direct", "system"):
        b = block.get(arm)
        if b: print("  ", arm, b["state"], b["actual"], "rows", b["rows"], "manifest", b["manifest_status"], "| agg", {k: round(v.get("corpus_wer", v.get("accuracy", v.get("high_impact_error_rate", 0))), 4) for k, v in b["aggregate"].items() if k != "cost"}, "| cost", {k: b["aggregate"].get("cost", {}).get(k) for k in ("calls_used", "audio_seconds_used")})
        else: print("  ", arm, "NOT SEALED")
    print("   contrast", json.dumps(block.get("contrast_system_minus_direct"))[:900])
    if block.get("system"): print("   system receipts sample", json.dumps(list(block["system"]["receipts"].values())[:1])[:300])
print("read sha256", hashlib.sha256((raw + "\n").encode()).hexdigest())
