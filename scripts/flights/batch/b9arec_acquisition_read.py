"""The B9a-rec ACQUISITION READ (model-free, decision 58): rows routed ACQUIRE, what the kind (a) re-query acquired, and the
official per-row outcome of those rows against the sealed PLAN arm. Reads sealed outputs + sealed per-sample official scores only;
prints counts, ids-free aggregates and hashes -- never utterance text, gold or model output."""
import os
import json, io, glob, collections, statistics, hashlib, sys

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ARM = f"{DATA}/runs/SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-V1/attempt-slurp-native-plan-acquisition-b9a-recovery-train-fold-a-generation-v1"
CMP = f"{DATA}/runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
OUT = f"{DATA}/analysis/SAEA-SLURP-PLAN-ACQUISITION-B9A-RECOVERY-PAIRED-ANALYSIS-V1/acquisition-read.json"


def per_sample(run_dir):
    p = glob.glob(f"{run_dir}/*.scores.json")[0]
    d = json.load(io.open(p, encoding="utf-8"))["slurp-slu-official-train"]["per_sample"]
    return {r["sample_id"]: r for r in d}, hashlib.sha256(open(p, "rb").read()).hexdigest()


def receipts(run_dir):
    p = glob.glob(f"{run_dir}/*.outputs.jsonl")[0]
    rows = {}
    for line in io.open(p, encoding="utf-8"):
        r = json.loads(line)
        rows[r["sample_id"]] = r.get("native_episode_receipt") or {}
    return rows, hashlib.sha256(open(p, "rb").read()).hexdigest()


arm_scores, arm_scores_sha = per_sample(ARM)
cmp_scores, cmp_scores_sha = per_sample(CMP)
arm_rec, arm_out_sha = receipts(ARM)
cmp_rec, cmp_out_sha = receipts(CMP)
assert set(arm_scores) == set(cmp_scores) == set(arm_rec) == set(cmp_rec), "roster mismatch"

groups = collections.defaultdict(list)
acq_facts = []
for sid, rec in arm_rec.items():
    seq = tuple(p.get("action") for p in rec.get("planner_routes") or [])
    key = "ACQUIRE" if "ACQUIRE" in seq else ("REVISE" if "REVISE" in seq else ("NONE" if not seq else "ACCEPT-ONLY"))
    groups[key].append(sid)
    if key == "ACQUIRE":
        for a in (rec.get("acquisition") or {}).get("acquisitions") or []:
            acq_facts.append({"sample": sid, "kind": a.get("kind"), "item_count": a.get("item_count"), "evidence_chars": a.get("evidence_chars"),
                              "provenance_ids": len(a.get("provenance_ids") or []), "state_filters": len(a.get("state_filters") or []),
                              "contacts_used": a.get("contacts_used"), "revision_count": a.get("revision_count"), "planner_action": a.get("planner_action")})

cmp_seq = {sid: tuple(p.get("action") for p in rec.get("planner_routes") or []) for sid, rec in cmp_rec.items()}


def outcome(sids, metric):
    a = [arm_scores[s][metric] for s in sids]; c = [cmp_scores[s][metric] for s in sids]
    saves = sum(1 for x, y in zip(a, c) if x > y); harms = sum(1 for x, y in zip(a, c) if x < y)
    return {"n": len(sids), "arm_mean": round(statistics.mean(a) * 100, 2) if a else None, "comparator_mean": round(statistics.mean(c) * 100, 2) if c else None,
            "delta_pp": round((statistics.mean(a) - statistics.mean(c)) * 100, 2) if a else None, "saves": saves, "harms": harms, "ties": len(sids) - saves - harms}


report = {"schema": "saea-b9a-acquisition-read-v1", "execution_profile": "model-free-check", "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
          "inputs": {"arm_outputs_sha256": arm_out_sha, "arm_scores_sha256": arm_scores_sha, "comparator_outputs_sha256": cmp_out_sha, "comparator_scores_sha256": cmp_scores_sha},
          "route_groups": {k: len(v) for k, v in groups.items()},
          "comparator_route_on_the_acquire_rows": dict(collections.Counter(cmp_seq[s] for s in groups["ACQUIRE"]).most_common()),
          "acquisitions": {"count": len(acq_facts),
                           "item_count_hist": dict(collections.Counter(a["item_count"] for a in acq_facts)),
                           "evidence_chars": {"min": min((a["evidence_chars"] for a in acq_facts), default=None), "median": statistics.median([a["evidence_chars"] for a in acq_facts]) if acq_facts else None, "max": max((a["evidence_chars"] for a in acq_facts), default=None)},
                           "provenance_ids_hist": dict(collections.Counter(a["provenance_ids"] for a in acq_facts)),
                           "state_filters_hist": dict(collections.Counter(a["state_filters"] for a in acq_facts)),
                           "contacts_used_total": sum(a["contacts_used"] or 0 for a in acq_facts),
                           "kinds": dict(collections.Counter(a["kind"] for a in acq_facts))},
          "outcomes": {}}
for g in ("ACQUIRE", "REVISE", "ACCEPT-ONLY", "NONE"):
    sids = groups.get(g, [])
    if sids:
        report["outcomes"][g] = {"scenario_action_exact": outcome(sids, "scenario_action_exact"), "slu_f1_f1": outcome(sids, "slu_f1_f1"), "slot_f1_exact_f1": outcome(sids, "slot_f1_exact_f1")}
# the arm's whole-roster per-row means for context
allsid = list(arm_rec)
report["outcomes"]["ALL"] = {"scenario_action_exact": outcome(allsid, "scenario_action_exact"), "slu_f1_f1": outcome(allsid, "slu_f1_f1")}
# comparator-side mirror: rows the COMPARATOR revised
cmp_rev = [s for s, q in cmp_seq.items() if "REVISE" in q]
report["comparator_revise_rows"] = {"n": len(cmp_rev), "overlap_with_arm_acquire": len(set(cmp_rev) & set(groups["ACQUIRE"])), "overlap_with_arm_revise": len(set(cmp_rev) & set(groups.get("REVISE", [])))}
raw = json.dumps(report, indent=2, sort_keys=True)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(raw + "\n")
print(raw)
print("sha256", hashlib.sha256((raw + "\n").encode()).hexdigest())
