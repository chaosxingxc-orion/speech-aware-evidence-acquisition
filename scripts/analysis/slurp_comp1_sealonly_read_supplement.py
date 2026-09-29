#!/usr/bin/env python3
"""Supplement to the COMP-1 Fold A paired read for the SEAL-ONLY arm (owner decision 189-A).

The registered driver (scripts/flights/read_paired_cell.sh -> scripts/analysis/stage3_paired_read.py)
wrote the gating score contrasts, the per-scenario tables and the structural summary, then stopped at
its phase stage: a seal-only attempt flies 0 rows, so it seals no ``phases.json`` and no
``generation-manifest.json``. This script computes, model-free and from sealed bytes only, the parts
of analysis recipe slurp-stage3-comp1-fold-a-resume-paired-analysis-v1 the driver did not reach:

* step 5, the per-class attribution table over the 191 PLAN intent-wrong rows (classes fixed before
  contact in attribution-classes-v1.json), and the harm split over the PLAN-correct rows by bank class;
* step 6, the unseeded row and the seven rows that lose delivery under the composition, by id;
* a delivery proxy for step 2: whether the Solver's recorded ``supplied_value_ids`` include the row's
  gold boundary value id (the Perception phase's own consumption lives in the predecessor traces);
* the entity over-emission split behind the pooled SLU-F1 guard;
* step 7 in part: Solver cited-envelope parse and finish histograms;
* the realised spend of the two contributing predecessor traces (wire usage and timings).

Gold intent is read from the governed bad-case bank on the scoring side only, to match a value id;
no utterance text, transcript, gold label string, intent name or model output is printed or
persisted: ids, counts, rates and hashes only. ZERO model, server, encoder, embedder, scorer,
tokenizer, network and GPU contacts.

    python -B scripts/analysis/slurp_comp1_sealonly_read_supplement.py --repo-root . \
        --data-root "$SPEECHRL_DATA_DIR" --output <analysis dir>/supplement-v1.json
"""
from __future__ import annotations

import argparse
import base64
import collections
import hashlib
import json
from pathlib import Path

RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
ARM_ATTEMPT = "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only"
AA_RUN = "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
AA_ATTEMPT = "attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1"
PLAN_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
PLAN_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
SCORER = "slurp-slu-official-train"
CLASSES = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/attribution-classes-v1.json"
ROSTER = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
PREDECESSORS = (
    "attempt-slurp-native-stage3-comp1-fold-a-generation-v1",
    "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3",
)
CONV = (32, 70)
KPROBE = (24, 55)
PP_PER_ROW = 100.0 / 1080


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_scores(data: Path, run: str, attempt: str) -> tuple[dict, str]:
    path = data / "runs" / run / attempt / f"{run}.scores.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {r["sample_id"]: r for r in doc[SCORER]["per_sample"]}, sha(path)


def load_outputs(data: Path, run: str, attempt: str) -> tuple[dict, str]:
    path = data / "runs" / run / attempt / f"{run}.outputs.jsonl"
    rows = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            parsed = None
            try:
                parsed = json.loads(row.get("text") or "")
            except (TypeError, ValueError):
                parsed = None
            intent_key = None
            n_entities = 0
            if isinstance(parsed, dict):
                intent_key = hashlib.sha256(
                    f"{parsed.get('scenario')}_{parsed.get('action')}".encode("utf-8")).hexdigest()
                ents = parsed.get("entities")
                n_entities = len(ents) if isinstance(ents, list) else 0
            citations = ((row.get("native_episode_receipt") or {}).get("solver_citations") or {}).get("contacts") or []
            rows[row["sample_id"]] = {"intent_key": intent_key, "entities": n_entities, "citations": citations}
    return rows, sha(path)


def wire_totals(trace: Path) -> dict:
    totals = collections.Counter()
    with trace.open("rb") as handle:
        for raw in handle:
            if b'"MODEL_WIRE_RESPONSE"' not in raw[:64]:
                continue
            record = json.loads(raw)
            if record.get("channel") != "MODEL_WIRE_RESPONSE":
                continue
            wire = json.loads(base64.b64decode(record["payload"]["response_b64"]))
            usage = wire.get("usage") or {}
            timings = wire.get("timings") or {}
            totals["contacts"] += 1
            totals["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            totals["completion_tokens"] += int(usage.get("completion_tokens") or 0)
            if timings.get("prompt_n") is not None:
                totals["with_timings"] += 1
                totals["prefilled_tokens"] += int(timings["prompt_n"])
                totals["cached_tokens"] += int(timings.get("cache_n") or 0)
                totals["prompt_ms"] += float(timings.get("prompt_ms") or 0.0)
                totals["predicted_ms"] += float(timings.get("predicted_ms") or 0.0)
    out = dict(totals)
    out["server_compute_hours_sum_of_contacts"] = (out.get("prompt_ms", 0.0) + out.get("predicted_ms", 0.0)) / 3.6e6
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    repo, data = Path(ns.repo_root), Path(ns.data_root)

    classes_doc = json.loads((repo / CLASSES).read_text(encoding="utf-8"))
    roster = json.loads((repo / ROSTER).read_text(encoding="utf-8"))
    scenario_of = {item["sample_id"]: item["stratum"] for item in roster["items"]}
    bank = {}
    with (data / BANK).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                bank[row["sample_id"]] = row

    arm_s, arm_s_sha = load_scores(data, RUN, ARM_ATTEMPT)
    aa_s, aa_s_sha = load_scores(data, AA_RUN, AA_ATTEMPT)
    plan_s, plan_s_sha = load_scores(data, PLAN_RUN, PLAN_ATTEMPT)
    arm_o, arm_o_sha = load_outputs(data, RUN, ARM_ATTEMPT)
    aa_o, aa_o_sha = load_outputs(data, AA_RUN, AA_ATTEMPT)
    ids = sorted(scenario_of)
    assert set(ids) == set(arm_s) == set(aa_s) == set(plan_s) == set(arm_o) == set(aa_o), "roster mismatch"

    def ok(scores: dict, sid: str) -> int:
        return int(scores[sid]["scenario_action_exact"] == 1.0)

    # Step 5: per-class attribution table over the PLAN intent-wrong rows.
    per_row = classes_doc["per_row"]
    table = {}
    for cls in classes_doc["class_order"]:
        members = [sid for sid, r in per_row.items() if r["class"] == cls]
        both_wrong = [s for s in members if not ok(aa_s, s) and not ok(arm_s, s)]
        same_wrong = sum(1 for s in both_wrong if arm_o[s]["intent_key"] == aa_o[s]["intent_key"])
        table[cls] = {
            "rows": len(members),
            "delivered_comp1_prepared": sum(1 for s in members if per_row[s]["delivered_comp1"]),
            "intent_exact_plan": sum(ok(plan_s, s) for s in members),
            "intent_exact_aa": sum(ok(aa_s, s) for s in members),
            "intent_exact_comp1": sum(ok(arm_s, s) for s in members),
            "wrong_to_gold_vs_aa": sum(1 for s in members if not ok(aa_s, s) and ok(arm_s, s)),
            "gold_aa_to_wrong_comp1": sum(1 for s in members if ok(aa_s, s) and not ok(arm_s, s)),
            "both_wrong_same_intent": same_wrong,
            "both_wrong_different_intent": len(both_wrong) - same_wrong,
        }
    newly = [s for s, r in per_row.items() if r["class"] in ("newly-by-both", "newly-by-agree", "newly-by-centroid")]
    newly_conv = sum(ok(arm_s, s) for s in newly)
    declared_rate = (CONV[0] + KPROBE[0]) / (CONV[1] + KPROBE[1])
    conversion = {
        "newly_delivered_rows": len(newly),
        "converted_to_gold_under_comp1": newly_conv,
        "conversion_rate": newly_conv / len(newly) if newly else None,
        "declared_basis": f"{CONV[0] + KPROBE[0]} of {CONV[1] + KPROBE[1]} = {declared_rate:.4f}",
        "declared_expected_rows": round(len(newly) * declared_rate, 2),
        "declared_expected_pp": round(len(newly) * declared_rate * PP_PER_ROW, 2),
        "realised_pp_from_newly_rows_vs_plan": round(newly_conv * PP_PER_ROW, 2),
        "per_factor_class_rate": {cls: (table[cls]["intent_exact_comp1"], table[cls]["rows"])
                                  for cls in ("newly-by-both", "newly-by-agree", "newly-by-centroid")},
        "single_factor_rates": {"CONV m/70": f"{CONV[0]}/{CONV[1]}", "KPROBE m/55": f"{KPROBE[0]}/{KPROBE[1]}"},
    }

    # Harm split over the PLAN-correct rows, by bank class.
    harm = collections.defaultdict(lambda: collections.Counter())
    for s in ids:
        if ok(plan_s, s):
            c = bank[s]["plan_class"]
            harm[c]["rows"] += 1
            harm[c]["comp1_wrong"] += 1 - ok(arm_s, s)
            harm[c]["aa_wrong"] += 1 - ok(aa_s, s)
    harm_total = collections.Counter()
    for c in harm.values():
        harm_total.update(c)

    # Step 6.
    special = {}
    for s in [*classes_doc["rows_seeded_with_no_boundary_entry_under_comp1"],
              *classes_doc["summary"]["rows_delivered_by_plan_or_a_single_factor_but_not_under_comp1"]]:
        special[s] = {"class": per_row.get(s, {}).get("class", "not-intent-wrong-under-plan"),
                      "plan": ok(plan_s, s), "aa": ok(aa_s, s), "comp1": ok(arm_s, s)}

    # Delivery proxy: the Solver's supplied intent-boundary ids.
    solver_delivered = {}
    for s in ids:
        target = "intent-boundaries::intent-boundary:" + bank[s]["gold_intent"]
        supplied = set()
        for contact in arm_o[s]["citations"]:
            supplied.update(contact.get("supplied_value_ids") or [])
        solver_delivered[s] = target in supplied
    wrong_ids = list(per_row)
    delivery = {
        "solver_supplied_gold_boundary_intent_wrong_rows": sum(solver_delivered[s] for s in wrong_ids),
        "prepared_delivered_comp1_intent_wrong_rows": sum(1 for s in wrong_ids if per_row[s]["delivered_comp1"]),
        "agreement_rows_on_intent_wrong": sum(1 for s in wrong_ids if solver_delivered[s] == per_row[s]["delivered_comp1"]),
        "solver_supplied_gold_boundary_all_rows": sum(solver_delivered.values()),
        "note": "proxy: the Solver's supplied_value_ids, not the Perception phase's consumption (in the predecessor traces)",
    }

    # Entity over-emission behind the SLU guard.
    ent = {"arm_emitted": sum(arm_o[s]["entities"] for s in ids), "aa_emitted": sum(aa_o[s]["entities"] for s in ids)}
    by_scen = collections.defaultdict(lambda: collections.Counter())
    for s in ids:
        sc = scenario_of[s]
        by_scen[sc]["emitted_delta"] += arm_o[s]["entities"] - aa_o[s]["entities"]
        by_scen[sc]["span_fp_delta"] += int(arm_s[s]["slot_f1_exact_fp"] - aa_s[s]["slot_f1_exact_fp"])
        by_scen[sc]["span_tp_delta"] += int(arm_s[s]["slot_f1_exact_tp"] - aa_s[s]["slot_f1_exact_tp"])
        by_scen[sc]["rows_more_entities"] += int(arm_o[s]["entities"] > aa_o[s]["entities"])
        by_scen[sc]["rows_fewer_entities"] += int(arm_o[s]["entities"] < aa_o[s]["entities"])
        by_scen[sc]["zero_gold_rows_emitting_arm"] += int(bank[s]["gold_entity_count"] == 0 and arm_o[s]["entities"] > 0)
        by_scen[sc]["zero_gold_rows_emitting_aa"] += int(bank[s]["gold_entity_count"] == 0 and aa_o[s]["entities"] > 0)
    ent_tot = collections.Counter()
    for c in by_scen.values():
        ent_tot.update(c)
    ent["totals"] = dict(ent_tot)
    ent["by_scenario"] = {k: dict(v) for k, v in sorted(by_scen.items())}

    # Citation envelope stats.
    parse = collections.Counter()
    finish = collections.Counter()
    solver_contacts = 0
    cited = 0
    for s in ids:
        for contact in arm_o[s]["citations"]:
            solver_contacts += 1
            p = contact.get("parse")
            parse[json.dumps(p, sort_keys=True) if isinstance(p, (dict, list)) else str(p)] += 1
            finish[str(contact.get("finish_reason"))] += 1
            cited += len(contact.get("cited_value_ids") or [])
    citations = {"solver_contacts": solver_contacts, "parse_histogram": dict(parse),
                 "finish_reason_histogram": dict(finish), "cited_ids_total": cited}

    spend = {}
    for att in PREDECESSORS:
        trace = data / "runs" / RUN / att / f"{RUN}.trace.jsonl"
        spend[att] = {"trace_sha256": sha(trace), **wire_totals(trace)}
        record = json.loads((data / "attempts" / RUN / f"{att}.json").read_text(encoding="utf-8"))
        spend[att]["attempt_actual"] = record.get("actual")

    out = {
        "schema": "saea-comp1-sealonly-read-supplement-v1",
        "inputs_sha256": {"arm_scores": arm_s_sha, "aa_scores": aa_s_sha, "plan_scores": plan_s_sha,
                          "arm_outputs": arm_o_sha, "aa_outputs": aa_o_sha,
                          "attribution_classes": sha(repo / CLASSES), "bank": sha(data / BANK)},
        "attribution_table": table,
        "newly_delivered_conversion": conversion,
        "plan_correct_harm_split_by_bank_class": {k: dict(v) for k, v in sorted(harm.items())},
        "plan_correct_harm_totals": dict(harm_total),
        "step6_rows": special,
        "delivery_proxy": delivery,
        "entity_over_emission": ent,
        "solver_citations": citations,
        "predecessor_spend": spend,
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0, "tokenizer": 0, "gpu": 0},
        "boundary": "TRAIN Fold A development numbers (owner decisions 28 and 86); ids, counts, rates and hashes only",
    }
    Path(ns.output).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("attribution_table", "newly_delivered_conversion", "plan_correct_harm_totals",
                                         "delivery_proxy", "solver_citations")}, indent=1))
    print(json.dumps(ent["totals"]))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "trace_sha256"} for k, v in spend.items()}))
    print(json.dumps(special))
    print(json.dumps({k: dict(v) for k, v in harm.items()}))
    print(json.dumps({k: {kk: v[kk] for kk in ("emitted_delta", "span_fp_delta", "span_tp_delta")} for k, v in ent["by_scenario"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
