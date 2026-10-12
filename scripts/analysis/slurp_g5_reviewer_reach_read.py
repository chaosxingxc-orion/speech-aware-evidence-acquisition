#!/usr/bin/env python3
"""Cell G5 Reviewer reach read beside the standard paired read (model-free, DESCRIPTIVE).

G5 deletes the retired-tool order from the Reviewer instruction (owner decisions 153, 160). The
standard paired driver (``scripts/flights/read_paired_cell.sh``) gives intent / SLU-F1 against the
shared in-chain A/A. This driver adds what the recipe's structural stage asks for, on BOTH arms:

* Reviewer and Planner reach: Reviewer visits per row, the Planner routes (REVISE and the rest), rows
  the loop revised;
* repairs vs breaks: per row, the FIRST Solver answer's intent against the DELIVERED intent, each
  against TRAIN gold (offline, scoring side only): repair = first wrong -> delivered right, break =
  first right -> delivered wrong; and the same for the entity multiset (exact set match);
* the Reviewer prompt tokens per contact from the sealed COST records (declared delta -51);
* a model-free count of Reviewer responses that narrate a tool call or a tool result (the regex of
  ``scripts/analysis/slurp_reviewer_credit_table.py``).

No utterance text, gold value, Reviewer text or model output is printed or persisted: counts, rates
and hashes only. Zero model, server, tokenizer, encoder, scorer-subprocess, network and GPU contacts.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-STAGE3-G5-FOLD-A-PAIRED-ANALYSIS-V1"
ARMS = (
    ("aa", "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1", "attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1"),
    ("g5", "SAEA-SLURP-STAGE3-G5-FOLD-A-V1", "attempt-slurp-native-stage3-g5-fold-a-generation-v1"),
)
NARRATION = re.compile(r"tool[_ ]?call|tool result|\"tool\"\s*:|get_task_contract|task[-_ ]contract", re.I)
DECLARED_REVIEWER_TOKEN_DELTA = -51
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def parse(text: str):
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    scenario, action, entities, ok = parse_slu_response(text or "")
    intent = (scenario, action) if ok and scenario is not None and action is not None else None
    return intent, Counter((e.type, e.filler) for e in entities) if ok else Counter()


def role_costs(trace: Path) -> dict:
    role_by_resp, resp_sha, cost = {}, {}, {}
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            rid, channel, payload = record["record_id"], record["channel"], record["payload"]
            base = rid.rsplit("/", 1)[0]
            if channel == "USE" and rid.endswith("/native-role-contact"):
                role_by_resp[payload["use_response_sha256"]] = payload["use_role_id"]
            elif channel == "MODEL_RESPONSE":
                resp_sha[base] = payload["response_sha256"]
            elif channel == "COST":
                cost[base] = payload
    out = defaultdict(list)
    for base, c in cost.items():
        out[role_by_resp.get(resp_sha.get(base), "?")].append(c.get("prompt_tokens") or 0)
    return out


def arm_read(data_root: Path, run: str, attempt: str, gold_intent: dict, gold_ents: dict) -> dict:
    directory = data_root / "runs" / run / attempt
    phases = json.loads((directory / f"{run}.phases.json").read_text(encoding="utf-8"))
    delivered = {}
    with (directory / f"{run}.outputs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            delivered[row["sample_id"]] = parse(row.get("text") or "")
    c = Counter()
    routes = Counter()
    visits_per_row = Counter()
    for result in phases["phases"][0]["results"]:
        sid = result["sample_id"]
        states = result.get("agent_states") or ()
        solvers = [s.get("content") or "" for s in states if s.get("state_kind") == "phase:solver"]
        reviewers = [s.get("content") or "" for s in states if s.get("state_kind") == "phase:reviewer"]
        receipt = result.get("native_episode_receipt") or {}
        row_routes = [r.get("action") for r in receipt.get("planner_routes") or ()]
        routes.update(str(r) for r in row_routes)
        visits_per_row[len(reviewers)] += 1
        c["rows"] += 1
        c["reviewer_visits"] += len(reviewers)
        c["solver_visits"] += len(solvers)
        c["rows_revised"] += len(solvers) > 1
        c["reviewer_narration"] += sum(1 for t in reviewers if NARRATION.search(t))
        c["rows_with_reviewer_narration"] += any(NARRATION.search(t) for t in reviewers)
        if not solvers:
            c["rows_without_solver_state"] += 1
            continue
        first_intent, first_ents = parse(solvers[0])
        final_intent, final_ents = delivered[sid]
        g_i, g_e = gold_intent[sid], gold_ents[sid]
        f_ok, d_ok = first_intent == g_i, final_intent == g_i
        c["first_intent_correct"] += f_ok
        c["delivered_intent_correct"] += d_ok
        c["intent_repair"] += (not f_ok) and d_ok
        c["intent_break"] += f_ok and not d_ok
        c["intent_changed_first_to_delivered"] += first_intent != final_intent
        fe_ok, de_ok = first_ents == g_e, final_ents == g_e
        c["entity_set_repair"] += (not fe_ok) and de_ok
        c["entity_set_break"] += fe_ok and not de_ok
        c["entities_changed_first_to_delivered"] += first_ents != final_ents
        if len(solvers) > 1:
            c["revised_intent_repair"] += (not f_ok) and d_ok
            c["revised_intent_break"] += f_ok and not d_ok
            c["revised_intent_changed"] += first_intent != final_intent
            c["revised_entities_changed"] += first_ents != final_ents
    costs = role_costs(directory / f"{run}.trace.jsonl")
    rev = costs.get("reviewer") or []
    return {
        "counts": dict(sorted(c.items())),
        "planner_routes": dict(sorted(routes.items())),
        "reviewer_visits_per_row_histogram": {str(k): v for k, v in sorted(visits_per_row.items())},
        "contacts_by_role": {k: len(v) for k, v in sorted(costs.items())},
        "reviewer_prompt_tokens": {"contacts": len(rev), "mean": round(statistics.fmean(rev), 2) if rev else None,
                                   "median": statistics.median(rev) if rev else None},
        "sealed": {"phases_sha256": sha256_file(directory / f"{run}.phases.json"),
                   "outputs_sha256": sha256_file(directory / f"{run}.outputs.jsonl")},
    }


def main(argv=None) -> int:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    out = data_root / "analysis" / READ_ID / "reviewer-reach"
    if out.exists() and any(out.iterdir()):
        print(f"REFUSED: {out} already holds files", file=sys.stderr)
        return 5
    records = load_slurp_split(load_lock(Path(args.lock)), data_root, "train", workers=4)
    gold_intent = {r.sample_id: (r.scenario, r.action) for r in records}
    gold_ents = {r.sample_id: Counter((e.type, e.filler) for e in r.entities) for r in records}
    report = {"schema": "saea-slurp-g5-reviewer-reach-read-v1", "read_id": READ_ID,
              "generated_at": datetime.now(timezone.utc).isoformat(), "arms": {}}
    for label, run, attempt in ARMS:
        report["arms"][label] = {"run": run, "attempt": attempt,
                                 **arm_read(data_root, run, attempt, gold_intent, gold_ents)}
    aa, g5 = report["arms"]["aa"]["reviewer_prompt_tokens"], report["arms"]["g5"]["reviewer_prompt_tokens"]
    report["reviewer_prompt_token_delta_per_contact"] = {
        "mean": round(g5["mean"] - aa["mean"], 2), "median": g5["median"] - aa["median"],
        "declared": DECLARED_REVIEWER_TOKEN_DELTA}
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
                                     newline="\n")
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
