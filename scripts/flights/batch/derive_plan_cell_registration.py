"""Derive the registration package of a ONE-FACTOR cell on the locked plan from the sealed cell PLAN package (decision 58:
script-derived registrations). The cell's fragments (baseline + smoke baseline + experiment + smoke experiment) must already
exist (an engineering item writes them); this tool: sets the fragments' native_contact_fit ids to the cell's own, writes the
readiness package (plans fresh + registered, protocol, analysis recipe, README, preregistration), the campaign plan, and the
four unconsumed exposure-ledger rows, all by id substitution from the PLAN package. Root then mints the decision receipt and
flips with repin_loop_generic.sh. Windows Python: run from the study root.

    python scripts/flights/batch/derive_plan_cell_registration.py --name review-primitives --runtag REVIEW-PRIMITIVES \
        --short R-PRIM --title "Cell R-PRIM: ..." --factor "..." --authority "owner decision 84; item E37" --date 2026-09-22
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC = "docs/readiness/2026-09-21-slurp-default-plan-lock-v1"
PLAN_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
PLAN_ATT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
PLANR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1"


def rd(p):
    return io.open(p, encoding="utf-8", newline="").read()


def wr(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def dump_like(raw, obj):
    m = re.search(r"\n( +)\"", raw)
    ind = len(m.group(1)) if m else 2
    return json.dumps(obj, indent=ind, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="cell slug used in fragment names, e.g. review-primitives")
    ap.add_argument("--runtag", required=True, help="run-id tag, e.g. REVIEW-PRIMITIVES")
    ap.add_argument("--short", required=True, help="short cell name for prose, e.g. R-PRIM")
    ap.add_argument("--title", required=True)
    ap.add_argument("--factor", required=True, help="one-paragraph statement of the ONE factor")
    ap.add_argument("--authority", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--stamp", default=None, help="ledger timestamp; default <date>T12:00:00")
    a = ap.parse_args()
    NAME, TAG, DATE = a.name, a.runtag, a.date
    STAMP = a.stamp or f"{DATE}T12:00:00.000000+00:00"
    NEW = f"docs/readiness/{DATE}-slurp-{NAME}-v1"
    CELL, SMOKE = f"slurp-native-{NAME}-v1", f"slurp-native-{NAME}-smoke-4-v1"
    RUN = f"SAEA-SLURP-NATIVE-{TAG}-V1"
    DEC = f"slurp-{NAME}-admission-v1"
    DEC_PATH = f"coordination/slurp-{NAME}-v1/root-admission-v1.json"
    IDS = [
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-SMOKE-4-FIT-V1", f"SAEA-SLURP-NATIVE-{TAG}-SMOKE-4-FIT-V1"),
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-SMOKE-4-V1", f"SAEA-SLURP-NATIVE-{TAG}-SMOKE-4-V1"),
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-FIT-V1", f"SAEA-SLURP-NATIVE-{TAG}-FIT-V1"),
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1", RUN),
        ("SAEA-SLURP-DEFAULT-PLAN-LOCK-PAIRED-ANALYSIS-V1", f"SAEA-SLURP-{TAG}-PAIRED-ANALYSIS-V1"),
        ("attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1", f"attempt-slurp-native-{NAME}-train-fold-a-generation-v1"),
        ("attempt-slurp-native-default-plan-lock-train-fold-a-fit-v1", f"attempt-slurp-native-{NAME}-train-fold-a-fit-v1"),
        ("attempt-slurp-native-default-plan-lock-smoke-4-generation-v1", f"attempt-slurp-native-{NAME}-smoke-4-generation-v1"),
        ("attempt-slurp-native-default-plan-lock-smoke-4-fit-v1", f"attempt-slurp-native-{NAME}-smoke-4-fit-v1"),
        ("slurp-native-default-plan-lock-smoke-4-baseline-v1", f"slurp-native-{NAME}-smoke-4-baseline-v1"),
        ("slurp-native-default-plan-lock-baseline-v1", f"slurp-native-{NAME}-baseline-v1"),
        ("slurp-native-default-plan-lock-smoke-4-v1", SMOKE),
        ("slurp-native-default-plan-lock-v1", CELL),
        ("saea-slurp-native-default-plan-lock", f"saea-slurp-native-{NAME}"),
        ("docs/readiness/2026-09-21-slurp-default-plan-lock-v1", NEW),
        ("coordination/slurp-default-plan-lock-v1/root-admission-v1.json", DEC_PATH),
        ("coordination/slurp-default-plan-lock-v1", f"coordination/slurp-{NAME}-v1"),
        ("slurp-default-plan-lock-admission-v1", DEC),
        ("slurp-default-plan-lock-v1", f"slurp-{NAME}-v1"),
        ("root-slurp-native-default-plan-lock", f"root-slurp-native-{NAME}"),
        ("Cell PLAN:", f"Cell {a.short}:"),
    ]

    def sub(s):
        for x, y in IDS:
            s = s.replace(x, y)
        return s

    written = []
    # 1. the cell's own fit ids on its fragments (never another cell's)
    for frag, fit_run, fit_att in ((f"configs/baseline/slurp-native-{NAME}-baseline-v1.json", f"SAEA-SLURP-NATIVE-{TAG}-FIT-V1", f"attempt-slurp-native-{NAME}-train-fold-a-fit-v1"),
                                   (f"configs/baseline/slurp-native-{NAME}-smoke-4-baseline-v1.json", f"SAEA-SLURP-NATIVE-{TAG}-SMOKE-4-FIT-V1", f"attempt-slurp-native-{NAME}-smoke-4-fit-v1")):
        raw = rd(frag); d = json.loads(raw)
        d["native_contact_fit"]["run_id"] = fit_run; d["native_contact_fit"]["attempt_id"] = fit_att
        d.pop("prepared_phase_supply", None)  # the flip prepares this cell's OWN supply under its run id (item E16)
        wr(frag, dump_like(raw, d)); written.append(frag)
    # 2. the campaign plan
    wr(f"configs/campaign/{CELL}.json", json.dumps({"cells": [{"cell": CELL, "experiment": CELL}], "schema": "saea-campaign-plan-v1"}, indent=2) + "\n")
    written.append(f"configs/campaign/{CELL}.json")
    # 3. the readiness package
    for name in sorted(os.listdir(SRC)):
        if name == "README.md" or name.startswith("slurp-native-"):
            continue
        raw = rd(f"{SRC}/{name}"); d = json.loads(sub(raw))
        d["registered_at_utc"] = STAMP
        def walk(x):
            if isinstance(x, dict):
                for k, v in list(x.items()):
                    if k == "factor" and isinstance(v, str): x[k] = a.factor
                    elif k == "reason" and isinstance(v, str) and "registered before contact" in v: x[k] = f"{a.title} registered before contact on {DATE} by script (decision 58) from the sealed cell PLAN package; comparator the sealed PLAN arm at the plan's own null (PLANr: h_SLU 1.2485 / h_intent 0.9943); nothing here authorises a flight, a readiness flip or an admission entry."
                    else: walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        walk(d)
        if name.startswith("protocol"):
            d["protocol_id"] = f"slurp-{NAME}-protocol-v1"
            d["comparator"] = {"run_id": PLAN_RUN, "attempt_id": PLAN_ATT, "official": {"slu_f1": 63.6304, "intent_accuracy": 82.2222}, "margins": {"h_slu": 1.2485, "h_intent": 0.9943, "source": f"the plan's own null, cell PLANr ({PLANR_RUN}), docs/results/2026-09-22-slurp-planr-v2-lock-replicate-verdict.md"}, "never_reflown": True}
            d["one_factor"] = a.factor
            d["authority"] = a.authority
        elif name.startswith("analysis-recipe"):
            d["recipe_id"] = f"slurp-{NAME}-paired-analysis-v1"; d["title"] = a.title + " -- paired read against the sealed PLAN arm at the plan's own null, with the frontier row"
            d["arms"] = {"arm": {"run_id": RUN, "attempt_id": f"attempt-slurp-native-{NAME}-train-fold-a-generation-v1", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
                         "comparator": {"run_id": PLAN_RUN, "attempt_id": PLAN_ATT, "role": "gating comparator, sealed, never re-flown"},
                         "margins": {"h_slu": 1.2485, "h_intent": 0.9943, "source": "the plan's own null (PLANr)"}}
            d["output"]["analysis_root"] = f"analysis/SAEA-SLURP-{TAG}-PAIRED-ANALYSIS-V1"
        wr(f"{NEW}/{name}", dump_like(raw, d)); written.append(f"{NEW}/{name}")
    readme = f"# {a.title}: launch runbook\n\nDerived {DATE} by `scripts/flights/batch/derive_plan_cell_registration.py` from the sealed cell PLAN package (decision 58).\nAuthority: {a.authority}.\n\n## The one factor\n\n{a.factor}\n\n## What is registered here\n\nBaselines `configs/baseline/slurp-native-{NAME}-baseline-v1.json` and `-smoke-4-baseline-v1.json`, experiments `configs/experiment/{CELL}.json` / `{SMOKE}.json`, campaign plan `configs/campaign/{CELL}.json`, this package, four exposure-ledger rows (`consumed = no`). Comparator: the sealed PLAN arm `{PLAN_RUN}` at the plan's own null (h_SLU 1.2485 / h_intent 0.9943).\n\n## Mint, re-pin, flip, queue\n\nDecision receipt `{DEC_PATH}` ({DEC}) minted by the coordinator; `scripts/flights/batch/repin_loop_generic.sh` flips the smoke then the arm (the prepared supply is built under this cell's own run id at the flip); the cell is queued on the SAEA-Batch-Driver (decision 77) on the SLURP geometry.\n\n## Not authorised by this package\n\nNo flight before the receipt is minted and both cells are flipped; no contact by this registration; no re-flying of the comparator; no test-split, Fold B or DEV read.\n"
    wr(f"{NEW}/README.md", readme); written.append(f"{NEW}/README.md")
    prereg = f"# {a.title}: preregistration\n\nRegistered {DATE} by the coordinator (Fable 5.1), by script from the sealed cell PLAN package (decision 58), before any contact. Development numbers only (owner decisions 28, 86).\n\n## The cell\n\n| item | value |\n| --- | --- |\n| base | the locked v2.0 plan, the sealed PLAN arm `{PLAN_RUN}` (63.6304 / 82.2222) |\n| factor | {a.factor} |\n| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, stores, k = 20, no phase_tools, contact ceiling 11 |\n| comparator | `{PLAN_RUN}`, never re-flown |\n| margins | the plan's own null (PLANr): h_SLU 1.2485, h_intent 0.9943 |\n| smoke | four engineering rows, structural acceptance |\n| runs | `{RUN}` / `-FIT-V1`; smoke `SAEA-SLURP-NATIVE-{TAG}-SMOKE-4-V1` / `-FIT-V1` |\n| authority | {a.authority} |\n\n## Decision rule (fixed here)\n\nNEUTRAL: both guards non-inferior at the plan's own null (CI95 lower bound of the paired official pooled SLU-F1 delta > -h_SLU and of the intent delta > -h_intent). ADMITTED: NEUTRAL and the SLU CI95 lower bound above zero. HARMFUL: a measured loss on either guard (decision 25). Frontier row (decision 75) and per-scenario tables in both weightings on every verdict; cell-specific engineering numbers (e.g. a parse rate) are reported beside the verdict as the preregistration of the engineering item states.\n\n## Budgets and failure rule\n\nCeilings as cell PLAN's (11,880 generation calls run-cumulative, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 GPU hours, one official complete score). First failure stops and preserves; one root-diagnosed recovery re-registration at most.\n"
    wr(f"{NEW}-preregistration.md", prereg); written.append(f"{NEW}-preregistration.md")
    # 4. ledger rows
    L = "docs/exposure-ledger.md"; led = rd(L); lines = led.split("\n")
    rows = {ln.split("|")[2].strip(): ln for ln in lines if ln.startswith("|") and ln.split("|")[2].strip().startswith("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-") and "REPLICATE" not in ln.split("|")[2]}
    assert len(rows) == 4, list(rows)
    existing = {ln.split("|")[2].strip() for ln in lines if ln.startswith("|")}
    new_rows = []
    for rid, ln in rows.items():
        cols = sub(ln).split("|")
        if cols[2].strip() in existing:
            continue
        cols[1] = f" {STAMP} "; cols[9] = " no "
        smoke = "SMOKE" in rid
        cols[4] = " " + ("Four-row form smoke of " if smoke else "") + a.title + ": " + a.factor[:400] + " "
        plan_rel = cols[14].strip(); sha = hashlib.sha256(io.open(plan_rel, "rb").read()).hexdigest() if os.path.exists(plan_rel) else "<pending>"
        notes = re.sub(r"Plan SHA256 [0-9a-f]{64}", f"Plan SHA256 {sha}", cols[15])
        notes = re.sub(r"\s*(Closed|Read|ABORTED|Consumed) 2026-09-\d\d \(Fable 5\.1\):.*$", "", notes).rstrip() + " "
        cols[15] = notes; new_rows.append("|".join(cols))
    last = max(i for i, ln in enumerate(lines) if ln.startswith("|")); lines[last + 1:last + 1] = new_rows
    wr(L, "\n".join(lines)); written.append(L)
    print("written", len(written), "| ledger rows added", len(new_rows))
    for p in written: print("  ", p)


if __name__ == "__main__":
    main()
