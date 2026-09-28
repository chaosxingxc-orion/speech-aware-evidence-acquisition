#!/usr/bin/env python3
"""Knowledge-wave cells (W1, W3a, W4): quantities a recipe reports BESIDE the standard paired read.

The registered read (``scripts/flights/read_paired_cell.sh`` -> ``scripts/analysis/stage3_paired_read.py``)
writes the contrasts, per-scenario tables, delivery / conversion and the frontier row. This script adds,
from sealed bytes only, what several wave recipes ask for beside the verdict:

1. Per-role prompt-token accounting: for every contact, the role (``USE`` record ``use_role_id``), the
   sealed ``COST`` prompt / completion tokens and the wire response's prefilled tokens
   (``timings.prompt_n``), joined on the contact prefix of ``record_id``; per role, contacts and the
   mean per contact, for the arm and the in-chain A/A, and arm minus A/A.
2. Named row sets (``--row-set NAME=path.json[:json.key.path]``, a JSON list of sample ids or of
   objects carrying ``sample_id``): per set, the A/A -> arm intent (``scenario_action_exact``)
   transition counts and the per-row SLU-F1 mean on both arms; ``--row-by-row NAME`` additionally
   lists each id with its 0/1 intent and per-row SLU-F1.

Written to a NEW sibling ``<analysis root>/beside/beside-v1.json`` (refused if it exists). MODEL-FREE:
zero model, tokenizer, encoder, scorer, server and network contacts. Counts, ids and hashes only: no
utterance text, transcript, gold label string or model output is printed or persisted.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

PROMPT_FIELDS = ("prompt_tokens_per_contact", "prefilled_tokens_per_contact", "completion_tokens_per_contact")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_dir(data: Path, run: str, attempt: str) -> Path:
    return data / "runs" / run / attempt


def role_tokens(data: Path, run: str, attempt: str) -> dict:
    trace = run_dir(data, run, attempt) / f"{run}.trace.jsonl"
    role, cost, pre = {}, {}, {}
    with trace.open("rb") as f:
        for raw in f:
            head = raw[:40]
            if b'"USE"' not in head and b'"COST"' not in head and b'"MODEL_WIRE_RESPONSE"' not in head:
                continue
            rec = json.loads(raw)
            ch, rid = rec.get("channel"), rec.get("record_id", "")
            key = rid.split("/", 1)[0]
            p = rec.get("payload") or {}
            if ch == "USE" and "use_role_id" in p:
                role[key] = p["use_role_id"]
            elif ch == "COST":
                cost[key] = (int(p.get("prompt_tokens") or 0), int(p.get("completion_tokens") or 0))
            elif ch == "MODEL_WIRE_RESPONSE":
                wire = json.loads(base64.b64decode(p["response_b64"]))
                t = wire.get("timings") or {}
                if t.get("prompt_n") is not None:
                    pre[key] = int(t["prompt_n"])
                del wire
    agg: dict[str, Counter] = defaultdict(Counter)
    for key, (pt, ct) in cost.items():
        r = role.get(key, "UNATTRIBUTED")
        agg[r]["contacts"] += 1
        agg[r]["prompt_tokens"] += pt
        agg[r]["completion_tokens"] += ct
        if key in pre:
            agg[r]["with_prefill"] += 1
            agg[r]["prefilled_tokens"] += pre[key]
    out = {}
    for r, c in sorted(agg.items()):
        n = c["contacts"]
        out[r] = {
            "contacts": n,
            "prompt_tokens_per_contact": round(c["prompt_tokens"] / n, 1) if n else None,
            "completion_tokens_per_contact": round(c["completion_tokens"] / n, 1) if n else None,
            "prefilled_tokens_per_contact": round(c["prefilled_tokens"] / c["with_prefill"], 1) if c["with_prefill"] else None,
            "prompt_tokens_total": c["prompt_tokens"],
        }
    return {"trace_sha256": sha(trace), "roles": out}


def per_sample(data: Path, run: str, attempt: str, scorer: str):
    path = run_dir(data, run, attempt) / f"{run}.scores.json"
    doc = json.loads(path.read_text())
    return {r["sample_id"]: r for r in doc[scorer]["per_sample"]}, sha(path)


def load_ids(spec: str, repo: Path) -> list[str]:
    path, _, keypath = spec.partition(":")
    obj = json.loads((repo / path).read_text(encoding="utf-8"))
    for k in [k for k in keypath.split(".") if k]:
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    if obj and isinstance(obj[0], dict):
        obj = [o["sample_id"] for o in obj]
    return list(obj)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--repo-root", required=True, type=Path)
    ap.add_argument("--analysis-root", required=True, help="relative to the data root")
    ap.add_argument("--arm", required=True, help="RUN/ATTEMPT")
    ap.add_argument("--aa", required=True, help="RUN/ATTEMPT")
    ap.add_argument("--scorer", default="slurp-slu-official-train")
    ap.add_argument("--row-set", action="append", default=[])
    ap.add_argument("--row-by-row", action="append", default=[])
    a = ap.parse_args()
    out_dir = a.data_root / a.analysis_root / "beside"
    target = out_dir / "beside-v1.json"
    if target.exists():
        raise SystemExit(f"REFUSED: {target} exists (a sealed read is never overwritten)")
    arms = {"aa": a.aa.split("/", 1), "arm": a.arm.split("/", 1)}
    doc = {
        "schema": "saea-stage3-wave-beside-v1",
        "arms": {k: {"run_id": v[0], "attempt_id": v[1]} for k, v in arms.items()},
        "driver_sha256": sha(Path(__file__)),
        "tokens": {},
        "row_sets": {},
    }
    scores = {}
    for k, (run, att) in arms.items():
        doc["tokens"][k] = role_tokens(a.data_root, run, att)
        scores[k], doc["arms"][k]["scores_sha256"] = per_sample(a.data_root, run, att, a.scorer)
    delta = {}
    for r in sorted(set(doc["tokens"]["aa"]["roles"]) | set(doc["tokens"]["arm"]["roles"])):
        L, R = doc["tokens"]["aa"]["roles"].get(r), doc["tokens"]["arm"]["roles"].get(r)
        if L and R:
            delta[r] = {f: (round(R[f] - L[f], 1) if R[f] is not None and L[f] is not None else None) for f in PROMPT_FIELDS}
            delta[r]["contacts"] = R["contacts"] - L["contacts"]
    doc["tokens"]["delta_arm_minus_aa"] = delta
    for spec in a.row_set:
        name, _, src = spec.partition("=")
        ids = load_ids(src, a.repo_root)
        trans: Counter = Counter()
        slu = {"aa": 0.0, "arm": 0.0}
        rows = []
        for sid in ids:
            left, right = scores["aa"][sid], scores["arm"][sid]
            li, ri = int(bool(left["scenario_action_exact"])), int(bool(right["scenario_action_exact"]))
            trans[("right" if li else "wrong") + "_to_" + ("right" if ri else "wrong")] += 1
            slu["aa"] += float(left["slu_f1_f1"])
            slu["arm"] += float(right["slu_f1_f1"])
            rows.append({"sample_id": sid, "intent_aa": li, "intent_arm": ri,
                         "slu_f1_row_aa": round(float(left["slu_f1_f1"]) * 100, 2),
                         "slu_f1_row_arm": round(float(right["slu_f1_f1"]) * 100, 2)})
        n = len(ids)
        block = {"source": src, "rows": n, "intent_transitions": dict(trans),
                 "per_row_slu_f1_mean_aa": round(100 * slu["aa"] / n, 2) if n else None,
                 "per_row_slu_f1_mean_arm": round(100 * slu["arm"] / n, 2) if n else None}
        if name in a.row_by_row:
            block["row_by_row"] = rows
        doc["row_sets"][name] = block
    out_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"written": str(target), "sha256": sha(target)}))
    print(json.dumps(doc["tokens"]["delta_arm_minus_aa"], indent=1))
    for k in ("aa", "arm"):
        print(k, json.dumps(doc["tokens"][k]["roles"]))
    for name, b in doc["row_sets"].items():
        print(name, json.dumps(b))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
