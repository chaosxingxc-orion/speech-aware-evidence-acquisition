#!/usr/bin/env python3
"""Derive cell COMP-1's PER-CLASS ATTRIBUTION membership, model-free, before contact.

Owner decision 138: a composed round that fails to improve is read as a CONFLICT
DIAGNOSIS between its elements, never as a null, and "each round carries the
per-class attribution table the bad-case bank defines, which is what turns 'no
improvement' into 'these two elements conflict on this class'". Decision 152
names the classes for COMP-1's read: each of the 191 PLAN intent-wrong TRAIN
Fold A rows is classified as newly delivered by the agreement term, by the
centroid key, by both, already delivered but wrong, or the catch-all, and its
OUTCOME under COMP-1 is read beside its class after the seal.

This script fixes the MEMBERSHIP half of that table now, from committed and
receipt-pinned bytes only, so the read cannot draw the classes after the
numbers:

* the bad-case bank (``analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl``, digest
  pinned by the AGREE and KPROBE registrations): each Fold A row's ``plan_class``
  and gold intent -- gold used on the scoring side only, exactly as
  ``core.scoring_batch`` uses it;
* cell CONV's roster (the 70 rows whose gold boundary entry the agreement term
  NEWLY delivers) and cell KPROBE's roster (the 55 the centroid key newly
  delivers), both committed derivations;
* the A/A cell's own prepared first-phase supply (the locked plan's selection,
  output digest ``ba5e1faa...``) and the COMP-1 arm's own prepared supply: for
  every row, whether the row's gold intent's boundary value id is INSIDE the
  eight the Perception phase will be shown. That is the composed DELIVERY, and
  it is the quantity decision 152's expectation composes over: whether the two
  retrieval factors' newly-delivered sets add, overlap, or cancel under one
  ranker.

Classes, exclusive and attributed in this order over the 191 intent-wrong rows:

  ``delivered-but-wrong``   gold delivered under the locked plan (86 rows)
  ``newly-by-both``         in CONV's roster AND KPROBE's roster
  ``newly-by-agree``        in CONV's roster only
  ``newly-by-centroid``     in KPROBE's roster only
  ``catch-all``             none of the above

and, orthogonally, every row's delivery under COMP-1 (composed) and under the
A/A (locked), so a row that is newly delivered by one factor alone but LOST
under the composition is visible as such before the flight.

Sample ids, class labels, counts and hashes only: no utterance text, transcript,
gold label string as content, knowledge body or model output is printed or
persisted. ZERO model, server, encoder, embedder, scorer, tokenizer, network,
GPU and paid-API contacts.

    PYTHONDONTWRITEBYTECODE=1 python scripts/flights/comp1/comp1_attribution_classes.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" \\
        --output docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/attribution-classes-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "saea-comp1-attribution-classes-v1"
DERIVATION_ID = "SAEA-SLURP-STAGE3-COMP1-ATTRIBUTION-CLASSES-V1"
BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
BANK_ROSTER = "train-fold-a"
CONV_ROSTER = "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/roster-derivation-v1.json"
KPROBE_ROSTER = "docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1/roster-derivation-v1.json"
AA_SUPPLY = "prepared/SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1/phase-supply-v1.json"
ARM_SUPPLY = "prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1/phase-supply-v1.json"
AGREE_SUPPLY = "prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/phase-supply-v2.json"
PLAN_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
BOUNDARY_VALUE_PREFIX = "intent-boundaries::intent-boundary:"
PHASE = "perception"
INTENT_WRONG = ("INTENT-UNCOVERED", "INTENT-COVERED")
CLASSES = ("delivered-but-wrong", "newly-by-both", "newly-by-agree", "newly-by-centroid", "catch-all")


class DeriveError(RuntimeError):
    pass


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_supply(path: Path) -> tuple[dict, dict[str, list[str]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("kind") != "phase-supply" or set(document["output"]) != {"facets", "values"}:
        raise DeriveError(f"{path} is not a phase-supply artifact")
    values = document["output"]["values"]
    if set(values) != {PHASE}:
        raise DeriveError(f"{path} seeds a phase other than {PHASE!r}")
    return document, {str(k): list(v) for k, v in values[PHASE].items()}


def load_bank(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("roster") != BANK_ROSTER:
            continue
        sid = str(entry["sample_id"])
        if sid in rows:
            raise DeriveError("the bank carries a Fold A row twice")
        rows[sid] = {"plan_class": entry["plan_class"], "gold_intent": entry["gold_intent"]}
    if len(rows) != 1080:
        raise DeriveError(f"the bank's {BANK_ROSTER} roster has {len(rows)} rows, not 1,080")
    return rows


def id_list_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output", required=True, help="repo-relative output path")
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    repo = Path(args.repo_root).resolve()
    data = Path(args.data_root).resolve()

    bank_path = data / BANK
    bank = load_bank(bank_path)
    conv = json.loads((repo / CONV_ROSTER).read_text(encoding="utf-8"))
    kprobe = json.loads((repo / KPROBE_ROSTER).read_text(encoding="utf-8"))
    conv_ids = set(map(str, conv["roster"]["ids"]))
    kprobe_ids = set(map(str, kprobe["roster"]["ids"]))
    if len(conv_ids) != int(conv["roster"]["count"]) or len(kprobe_ids) != int(kprobe["roster"]["count"]):
        raise DeriveError("a committed roster's ids and count disagree")
    if id_list_sha256(conv_ids) != conv["roster"]["id_list_sha256"] or id_list_sha256(kprobe_ids) != kprobe["roster"]["id_list_sha256"]:
        raise DeriveError("a committed roster's ids do not hash to its id_list_sha256")

    aa_doc, aa_values = load_supply(data / AA_SUPPLY)
    arm_doc, arm_values = load_supply(data / ARM_SUPPLY)
    agree_doc, agree_values = load_supply(data / AGREE_SUPPLY)
    if aa_doc["output_sha256"] != PLAN_OUTPUT_SHA:
        raise DeriveError("the A/A supply is not the locked plan's selection (output digest differs)")
    if set(aa_values) != set(bank):
        raise DeriveError("the A/A supply does not seed exactly the 1,080 Fold A rows")
    if not set(arm_values) <= set(bank):
        raise DeriveError("the COMP-1 supply seeds a row outside Fold A")

    def delivered(values: dict[str, list[str]], sid: str) -> bool:
        gold_id = BOUNDARY_VALUE_PREFIX + str(bank[sid]["gold_intent"])
        return gold_id in values.get(sid, [])

    wrong = sorted(sid for sid, row in bank.items() if row["plan_class"] in INTENT_WRONG)
    if len(wrong) != 191:
        raise DeriveError(f"the bank has {len(wrong)} intent-wrong Fold A rows, not 191")
    if not conv_ids <= set(wrong) or not kprobe_ids <= set(wrong):
        raise DeriveError("a conversion roster contains a row that is not intent-wrong in the bank")
    plan_delivered = {sid for sid in wrong if delivered(aa_values, sid)}
    if plan_delivered & (conv_ids | kprobe_ids):
        raise DeriveError("a 'newly delivered' row is already delivered under the locked plan")

    per_row: dict[str, dict] = {}
    for sid in wrong:
        if sid in plan_delivered:
            klass = "delivered-but-wrong"
        elif sid in conv_ids and sid in kprobe_ids:
            klass = "newly-by-both"
        elif sid in conv_ids:
            klass = "newly-by-agree"
        elif sid in kprobe_ids:
            klass = "newly-by-centroid"
        else:
            klass = "catch-all"
        per_row[sid] = {
            "class": klass,
            "plan_class": bank[sid]["plan_class"],
            "delivered_locked_plan": sid in plan_delivered,
            "delivered_agree_alone": delivered(agree_values, sid),
            "delivered_comp1": delivered(arm_values, sid),
            "comp1_boundary_width": len(arm_values.get(sid, [])),
            "locked_boundary_width": len(aa_values.get(sid, [])),
        }

    def table(rows: dict[str, dict]) -> dict:
        out = {}
        for klass in CLASSES:
            members = {sid: r for sid, r in rows.items() if r["class"] == klass}
            out[klass] = {
                "rows": len(members),
                "by_plan_class": dict(sorted(Counter(r["plan_class"] for r in members.values()).items())),
                "delivered_under_comp1": sum(r["delivered_comp1"] for r in members.values()),
                "not_delivered_under_comp1": sum(not r["delivered_comp1"] for r in members.values()),
                "delivered_under_agree_alone": sum(r["delivered_agree_alone"] for r in members.values()),
                "ids": sorted(members),
                "outcome_under_comp1": "READ AFTER THE SEAL: per row, intent exact under COMP-1 / under the in-chain A/A / under the sealed PLAN arm (official scorer's scenario_action_exact)",
            }
        return out

    classes = table(per_row)
    comp1_delivered_wrong = sum(r["delivered_comp1"] for r in per_row.values())
    lost_under_comp1 = sorted(sid for sid, r in per_row.items() if (r["delivered_locked_plan"] or sid in conv_ids or sid in kprobe_ids) and not r["delivered_comp1"])
    gained_beyond_union = sorted(sid for sid, r in per_row.items() if r["class"] == "catch-all" and r["delivered_comp1"])

    # Whole-roster delivery and seeding facts (all 1,080 rows), so the read can
    # see harm on already-correct rows too.
    all_rows = {}
    for sid in sorted(bank):
        all_rows[sid] = {
            "plan_class": bank[sid]["plan_class"],
            "delivered_locked_plan": delivered(aa_values, sid),
            "delivered_comp1": delivered(arm_values, sid),
            "seeded_comp1": sid in arm_values,
        }
    by_class_all = {}
    for klass in sorted({r["plan_class"] for r in all_rows.values()}):
        members = [r for r in all_rows.values() if r["plan_class"] == klass]
        by_class_all[klass] = {
            "rows": len(members),
            "delivered_locked_plan": sum(r["delivered_locked_plan"] for r in members),
            "delivered_comp1": sum(r["delivered_comp1"] for r in members),
            "lost_under_comp1": sum(r["delivered_locked_plan"] and not r["delivered_comp1"] for r in members),
            "gained_under_comp1": sum(r["delivered_comp1"] and not r["delivered_locked_plan"] for r in members),
        }
    unseeded = sorted(sid for sid, r in all_rows.items() if not r["seeded_comp1"])
    width_hist = {
        "locked_plan": dict(sorted(Counter(len(v) for v in aa_values.values()).items())),
        "comp1": dict(sorted(Counter(len(v) for v in arm_values.values()).items())),
    }

    result = {
        "schema": SCHEMA,
        "derivation_id": DERIVATION_ID,
        "contact_class": "model-free",
        "contacts": {k: 0 for k in ("model", "server", "encoder", "embedder", "scorer", "tokenizer", "network", "gpu", "paid_api")},
        "inputs": {
            "bad_case_bank": {"relpath": BANK, "sha256": sha_file(bank_path), "roster": BANK_ROSTER},
            "conv_roster": {"relpath": CONV_ROSTER, "sha256": sha_file(repo / CONV_ROSTER), "count": len(conv_ids), "id_list_sha256": conv["roster"]["id_list_sha256"]},
            "kprobe_roster": {"relpath": KPROBE_ROSTER, "sha256": sha_file(repo / KPROBE_ROSTER), "count": len(kprobe_ids), "id_list_sha256": kprobe["roster"]["id_list_sha256"]},
            "aa_supply": {"relpath": AA_SUPPLY, "sha256": sha_file(data / AA_SUPPLY), "output_sha256": aa_doc["output_sha256"]},
            "arm_supply": {"relpath": ARM_SUPPLY, "sha256": sha_file(data / ARM_SUPPLY), "output_sha256": arm_doc["output_sha256"]},
            "agree_supply": {"relpath": AGREE_SUPPLY, "sha256": sha_file(data / AGREE_SUPPLY), "output_sha256": agree_doc["output_sha256"]},
        },
        "delivery_definition": (
            "a row's gold intent's boundary value id (intent-boundaries::intent-boundary:<gold intent>) is "
            "among the value ids the cell's own prepared first-phase supply seeds for that row -- the "
            "eight (or fewer) entries the Perception phase is shown"
        ),
        "class_order": list(CLASSES),
        "intent_wrong_rows": len(wrong),
        "classes": classes,
        "summary": {
            "delivered_under_locked_plan": len(plan_delivered),
            "newly_delivered_by_agree_alone_conv_roster": len(conv_ids),
            "newly_delivered_by_centroid_alone_kprobe_roster": len(kprobe_ids),
            "newly_by_both": classes["newly-by-both"]["rows"],
            "union_of_the_two_newly_delivered_sets": len(conv_ids | kprobe_ids),
            "delivered_under_comp1": comp1_delivered_wrong,
            "delivered_under_comp1_pct_of_intent_wrong": round(100.0 * comp1_delivered_wrong / len(wrong), 1),
            "rows_delivered_by_plan_or_a_single_factor_but_not_under_comp1": lost_under_comp1,
            "catch_all_rows_delivered_only_under_the_composition": gained_beyond_union,
        },
        "all_rows_by_bank_class": by_class_all,
        "comp1_boundary_width_histogram": width_hist,
        "rows_seeded_with_no_boundary_entry_under_comp1": unseeded,
        "per_row": per_row,
        "gold_use": (
            "Gold is read on the SCORING side only -- the bank's plan_class and gold intent -- to define "
            "the read's classes before contact, exactly as the AGREE and KPROBE registrations did. Gold "
            "reaches no query, no key, no weight, no selector and no runtime."
        ),
        "what_this_is_not": (
            "Not a verdict, not a claim and not a prediction: membership only. The outcome column is read "
            "after the seal by the registered recipe, and a delivery count is never a correctness count."
        ),
    }
    out_path = repo / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"written": args.output, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "summary": result["summary"], "classes": {k: {kk: vv for kk, vv in v.items() if kk != "ids" and kk != "outcome_under_comp1"} for k, v in classes.items()},
                      "unseeded": unseeded, "width": width_hist}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DeriveError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
