#!/usr/bin/env python3
"""S1: SLU error-taxonomy refresh on the COMP-1b bytes (A2 on DEV-2000-ADDED, its A/A, COMP-1b on Fold A).

Round S1 of the Stage-3 slot-extraction programme (``docs/readiness/2026-09-30-slurp-stage3-replan-v6.md``
section 2).  It re-bases the delivered SLU error taxonomy that the AGREE arm fixed on 2026-09-27 onto the
bytes of the dev-admitted composed arm, so that the declared effects of S2 (missing-slot proposal) and S5
(explicit no-slot decision) can be computed on the arm they would be composed with.

This driver does not re-implement the taxonomy.  It imports, unchanged:

* the node ledger (``scripts/analysis/slurp_node_gain_ledger.py``): ``load_node_states``, ``derive_arm``,
  ``slot_ledger`` -- the per-gold-item delivered class and the origin split (consumption / hearing-visible /
  undetermined), exactly as the 2026-09-28 ledger defined them;
* the error-source read (through the ledger's ``ES``): ``load_outputs``, ``repaired``, ``slu_counts``,
  ``SlotEntity``, ``load_gold`` (TRAIN); the gold-position read (``GP``): ``load_phases``,
  ``load_exemplar_pool``, ``load_contract_bodies``; W5's ``printed_pairs`` / ``snapshot_values``;
* the consumption-headroom read (``scripts/analysis/slurp_slu_consumption_headroom.py``): ``pooled_f1``,
  ``gain_pp``, ``trade_pp``, ``items_for_target``, ``Rescorer``, ``repair_preds``, ``drop_preds``,
  ``group_items``, ``evidence_class`` and its measured conversion constants;
* ``analysis.sealed_credit.entity_states.entity_items`` / ``canonical`` / ``contiguous_in`` / ``fold``.

What is new here is only the arm table (with the scorer key and the gold split per arm), the devel gold
loader (the governed ``data.slurp.load_slurp_split`` on ``devel``, the path the 2026-09-24 CELL-3
fresh-roster diagnostic used), and the aggregations: per class, per origin, per slot type, per scenario,
the empty-gold split (decision 199), the N1 none-share gate, and the S2 / S5 addressable mass.

Flag ``--arms`` selects arm labels (default: all).  The AGREE arm is carried as the re-derivation control:
when it is selected, its counts must reproduce the v6 baseline (MISSING 173, SPURIOUS 253, WRONG-TYPE 51,
BOUNDARY 75, WRONG-VALUE 41, NEAR 56, FORMAT 11; origin 107 / 71 / 229; N1 at 0.6: 128 rows, 28 spurious)
or the run stops.

Gold discipline: gold enters only offline, through the governed SLURP loader, on the scoring side; it
reaches no query, key, selector, config or runtime.  The test split is not read.  Text discipline: no
utterance text, transcript, gold value, filler, card body or model output is printed or persisted -- only
ids, counts, rates, pp, slot TYPE names, scenario names, class names and hashes.  Zero model, server,
tokenizer, encoder, embedder, scorer-subprocess, network and GPU contacts.

Deterministic apart from ``generated_at``.  ``--check`` re-derives and compares.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_s1_slu_error_taxonomy.py \\
        --data-root "$SPEECHRL_DATA_DIR" \\
        --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

READ_ID = "SAEA-SLURP-S1-SLU-ERROR-TAXONOMY-REFRESH-V1"
RECIPE = "slurp-s1-slu-error-taxonomy-refresh-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")

#: label -> run, attempt, scorer key, gold split, roster size, role
ARMS = (
    {"label": "a2", "title": "A2 = COMP-1b on DEV-2000-ADDED (arm)",
     "run_id": "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1",
     "attempt": "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1",
     "scorer": "slurp-slu-official", "split": "devel", "rows": 1000, "trace": False},
    {"label": "a2_aa", "title": "A2 in-chain A/A (locked v2.0 plan re-flown) on DEV-2000-ADDED",
     "run_id": "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1",
     "attempt": "attempt-slurp-native-stage3-comp1-aa-dev2000-added-generation-v1",
     "scorer": "slurp-slu-official", "split": "devel", "rows": 1000, "trace": False},
    {"label": "comp1b_fold_a", "title": "COMP-1b on TRAIN Fold A (arm)",
     "run_id": "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1",
     "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080, "trace": False},
    {"label": "comp1_aa_fold_a", "title": "COMP-1b's in-chain A/A on TRAIN Fold A (context)",
     "run_id": "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1",
     "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080, "trace": False},
    {"label": "agree", "title": "AGREE arm on TRAIN Fold A (v6 baseline; re-derivation control)",
     "run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1",
     "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080, "trace": False},
)
CONTROL = "agree"
#: v6 section 2 baseline (docs/results/2026-09-27-slurp-agree-arm-error-sources.md section 3; node ledger 2.3;
#: supply-abstention headroom 3.3).  Asserted on the control arm.
AGREE_EXPECT = {"classes": {"MISSING": 173, "SPURIOUS": 253, "WRONG-TYPE": 51, "BOUNDARY": 75, "WRONG-VALUE": 41,
                            "NEAR": 56, "FORMAT": 11},
                "origin": {"consumption": 107, "hearing_visible": 71, "undetermined": 229},
                "n1_rows_gated": 128, "n1_spurious_removed": 28}

CLASSES = ("SPURIOUS", "MISSING", "WRONG-TYPE", "BOUNDARY", "NEAR", "WRONG-VALUE", "FORMAT")
GOLD_SIDE = CLASSES[1:]
ORIGINS = ("consumption", "hearing_visible", "undetermined")
SUPPLY = ("E1", "E2", "E3", "none")
N1_THETA = 0.6        # fixed in docs/results/2026-09-29-slurp-supply-abstention-headroom-offline.md section 5
TARGET_PP = 1.5       # decision 192
CROSS_FLIGHT_BAR_PP = 2.5
TOP_TYPES = 15

# Measured conversions, each quoted from the headroom note (the note's own sources in brackets); none invented.
RATES = {
    "m1": {"rate": 133 / (0.5719 * 941),
           "source": "M1 delivered-filler conversion 133 / (0.5719 x 941) = 0.2471; "
                     "docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md section 1 "
                     "(docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md:51)"},
    "w4_list": {"rate": 5 / 97,
                "source": "W4 card value list moved 5 of 97 listed items = 0.0515; headroom note section 2 "
                          "(docs/results/2026-09-28-slurp-w4-fold-a-read.md:189-190)"},
    "f10_fp_removed_per_zero_gold_fp": {"rate": 22 / 142,
                                        "source": "F10 empty-gold exact FP 142 -> 120 = 0.1549 removed per FP; "
                                                  "headroom note section 2 "
                                                  "(docs/results/2026-09-25-slurp-f10-complete-verdict.md:18-21)"},
    "f10_exact_lost_per_zero_gold_fp": {"rate": 13 / 142,
                                        "source": "F10 non-empty exact FN 384 -> 397 = 13 per 142 FP = 0.0915; "
                                                  "headroom note section 2 (same source)"},
    "dev2000_vote_rule_reach": {"rate": 14.4 / 162.2,
                                "source": "DEV-2000 five-sample vote rule reaches 14.4 of 162.2 FP-only sample-rows "
                                          "= 0.0888; headroom note section 2 "
                                          "(docs/results/2026-09-28-slurp-empty-entity-offline-read.md:128-134)"},
}
# S2 transcript containment (the E5 precondition read), used only as a stated ceiling multiplier.
E5_CONTAINMENT = {"rate": 707 / 941, "source": "Whisper large-v3 gold-span containment 707 / 941 = 0.7513 on Fold A; "
                                               "docs/results/2026-09-30-slurp-e5-transcript-consistency-oracle-read.md "
                                               "section 1"}


class ReadError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# pure parts (unit-tested on fakes)


def parse_arms(value: str | None, known=tuple(a["label"] for a in ARMS)) -> list:
    """``--arms`` flag: comma-separated labels, order kept, duplicates refused; ``None``/empty -> all."""
    if not value:
        return list(known)
    labels = [v.strip() for v in value.split(",") if v.strip()]
    unknown = [v for v in labels if v not in known]
    if unknown:
        raise ReadError(f"unknown arm label(s): {unknown}; known: {list(known)}")
    if len(set(labels)) != len(labels):
        raise ReadError("an arm label is repeated")
    return labels


def origin_short(origin: str) -> str:
    """The ledger's origin strings (``slurp_node_gain_ledger.slot_ledger.origin_of``) -> three classes."""
    if origin.startswith("consumption"):
        return "consumption"
    if origin.startswith("hearing"):
        return "hearing_visible"
    if origin.startswith("undetermined"):
        return "undetermined"
    raise ReadError(f"unknown origin {origin!r}")


def supply_class(evidence: str) -> str:
    """The headroom note's evidence class -> E1 / E2 / E3 (value in the supply) or ``none``."""
    return evidence[:2] if evidence[:2] in ("E1", "E2", "E3") else "none"


def class_counts(items: list) -> dict:
    c = Counter(i["kind"] for i in items)
    return {k: c.get(k, 0) for k in CLASSES}


def empty_gold_split(gold_e: dict, pred: dict, intent_ok: dict, ids: list) -> dict:
    """Decision-199 mass: zero-gold rows split into correctly-empty vs spurious-filled; gold rows delivered empty."""
    zero = [s for s in ids if not gold_e[s]]
    filled = [s for s in zero if pred[s]]
    gold_rows = [s for s in ids if gold_e[s]]
    empty_on_gold = [s for s in gold_rows if not pred[s]]
    return {"rows": len(ids), "zero_gold_rows": len(zero), "correctly_empty": len(zero) - len(filled),
            "spurious_filled": len(filled),
            "spurious_entities_on_zero_gold_rows": sum(len(pred[s]) for s in filled),
            "spurious_filled_intent_right": sum(1 for s in filled if intent_ok[s]),
            "gold_rows": len(gold_rows), "gold_rows_delivered_empty": len(empty_on_gold),
            "gold_items_on_gold_rows_delivered_empty": sum(len(gold_e[s]) for s in empty_on_gold)}


def none_share(rendered: list, fillers_by_key: dict) -> float | None:
    """Entity-free share of the row's rendered exemplars (the supply-abstention note's N1 signal).
    Keys absent from the pool are skipped; ``None`` if nothing resolves."""
    flags = [not fillers_by_key[k] for k in rendered if k in fillers_by_key]
    return sum(flags) / len(flags) if flags else None


def n1_gate(shares: dict, pred: dict, gold_e: dict, theta: float) -> dict:
    """Rows gated at ``share >= theta``; the rows an explicit empty answer would change (gated and emitting)."""
    gated = [s for s, v in shares.items() if v is not None and v >= theta]
    change = {s: [] for s in gated if pred[s]}
    return {"gated": gated, "change": change,
            "rows_gated_zero_gold": sum(1 for s in gated if not gold_e[s]),
            "rows_gated_gold": sum(1 for s in gated if gold_e[s])}


def expected(oracle_pp: float, rate: float) -> float:
    return round(oracle_pp * rate, 4)


# ---------------------------------------------------------------------------
# loaders


def load_scores(directory: Path, run_id: str, scorer: str) -> dict:
    path = directory / f"{run_id}.scores.json"
    block = json.loads(path.read_text(encoding="utf-8"))[scorer]
    rows = {str(s["sample_id"]): s for s in block["per_sample"]}
    totals = tuple(sum(float(r[f"slu_f1_word_{k}"]) + float(r[f"slu_f1_char_{k}"]) for r in rows.values())
                   for k in ("tp", "fp", "fn"))
    return {"rows": rows, "sha256": digest(path), "relpath": path.name, "totals": totals}


def load_gold_split(lock, data_root: Path, split: str, ES) -> dict:
    """Gold per sample id through the governed SLURP loader; ``train`` reuses ``ES.load_gold`` unchanged."""
    if split == "train":
        return ES.load_gold(lock, data_root)
    if split != "devel":
        raise ReadError(f"split {split!r} is not read by S1 (the test split is closed)")
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    records = load_slurp_split(lock, data_root, "devel", workers=4)
    return {r.sample_id: {"intent": r.intent, "scenario": r.scenario, "action": r.action,
                          "entities": tuple(ES.SlotEntity(e.type, e.filler) for e in r.entities)} for r in records}


# ---------------------------------------------------------------------------
# per-arm derivation


def derive(spec: dict, data_root: Path, gold: dict, pool: dict, m1_values: dict, cards: dict, NG, HR) -> dict:
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import (
        canonical, contiguous_in, entity_items, fold)

    ES, GP = NG.ES, NG.GP
    phases = GP.load_phases(data_root, spec)
    directory = phases["directory"]
    outputs = ES.load_outputs(directory, spec["run_id"])
    scores = load_scores(directory, spec["run_id"], spec["scorer"])
    nodes = NG.load_node_states(data_root, spec)
    ids = sorted(scores["rows"])
    if len(ids) != spec["rows"] or sorted(outputs["rows"]) != ids or sorted(phases["rows"]) != ids:
        raise ReadError(f"{spec['label']}: roster size or id set disagrees across scores / outputs / phases")
    missing_gold = [s for s in ids if s not in gold]
    if missing_gold:
        raise ReadError(f"{spec['label']}: {len(missing_gold)} roster ids absent from the {spec['split']} gold")

    pred = {s: outputs["rows"][s]["entities"] for s in ids}
    gold_e = {s: gold[s]["entities"] for s in ids}
    rescorer = HR.Rescorer(gold_e, pred, ES.slu_counts, ids)
    if any(abs(a - b) > 1e-6 for a, b in zip(rescorer.base, scores["totals"])):
        raise ReadError(f"{spec['label']}: in-process totals do not reproduce the sealed official totals")
    base_f1 = HR.pooled_f1(scores["totals"])

    arm = {"label": spec["label"], "phases": phases["rows"], "outputs": outputs["rows"], "scores": scores["rows"],
           "nodes": nodes["rows"]}
    derived = NG.derive_arm(arm, gold, ids, pool, m1_values)
    ledger = NG.slot_ledger(derived["rows"], derived["items"], ids)
    intent_ok = {s: derived["rows"][s]["d_ok"] for s in ids}

    def in_cards(sid, value) -> bool:
        if len(value) < 3:
            return False
        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])")
        return any(pattern.search(cards["bodies"].get(cid, "")) for cid in phases["rows"][sid]["contracts"])

    # unified item list: gold-side errors (ledger item joined with its entity item) + SPURIOUS predictions
    items = []
    ledger_by_row = defaultdict(list)
    for li in derived["items"]:
        ledger_by_row[li["sample_id"]].append(li)
    for sid in ids:
        its = entity_items(gold_e[sid], pred[sid])
        by_gold = {it["gold_index"]: it for it in its if it["gold_index"] is not None}
        tokens = nodes["rows"][sid]["perception"]["tokens"] if nodes["rows"][sid]["perception"] else []
        scen = gold[sid]["scenario"]
        for it in its:
            if it["gold_index"] is None:
                items.append({"sample_id": sid, "entity_item": it, "kind": "SPURIOUS", "type": it["type"],
                              "scenario": scen, "intent_ok": intent_ok[sid], "zero_gold_row": not gold_e[sid],
                              "in_note": contiguous_in(canonical(pred[sid][it["pred_index"]].filler).split(), tokens)})
        for li in ledger_by_row[sid]:
            if li["d"] == "EXACT":
                continue
            it = by_gold[li["gold_index"]]
            if it["kind"] != li["d"]:
                raise ReadError(f"{spec['label']}: ledger item kind and entity item kind disagree")
            value = fold(gold_e[sid][li["gold_index"]].filler)
            ev = HR.evidence_class(li["k_value_printed"], li["k_value_printed_any_type"], in_cards(sid, value), False)
            items.append({"sample_id": sid, "entity_item": it, "kind": li["d"], "type": li["type"], "scenario": scen,
                          "intent_ok": intent_ok[sid], "origin": origin_short(li["origin"]),
                          "origin_detail": li["origin"], "supply": supply_class(ev),
                          "value_printed": li["k_value_printed"]})

    def oracle(sub) -> float:
        return round(rescorer.gain(HR.repair_preds(HR.group_items(sub), gold_e, pred, ES.repaired)), 4)

    spurious = [i for i in items if i["kind"] == "SPURIOUS"]
    gold_errs = [i for i in items if i["kind"] != "SPURIOUS"]
    if len(spurious) != ledger["spurious_edges"]["d"] or len(gold_errs) != ledger["origin_totals"]["delivered_gold_side_errors"]:
        raise ReadError(f"{spec['label']}: item join does not reproduce the ledger's spurious / gold-side counts")

    # 1. classes
    classes = {}
    for k in CLASSES:
        sub = [i for i in items if i["kind"] == k]
        classes[k] = {"items": len(sub), "rows": len({i["sample_id"] for i in sub}),
                      "on_intent_right_rows": sum(i["intent_ok"] for i in sub),
                      "oracle_pp": oracle(sub),
                      "oracle_pp_intent_right_rows": oracle([i for i in sub if i["intent_ok"]])}
    all_oracle = oracle(items)

    # 2. origin x class (gold side) and supply evidence
    origin = {}
    for o in ORIGINS:
        sub = [i for i in gold_errs if i["origin"] == o]
        origin[o] = {"items": len(sub), "oracle_pp": oracle(sub),
                     "by_class": {k: sum(1 for i in sub if i["kind"] == k) for k in GOLD_SIDE},
                     "by_supply": {e: sum(1 for i in sub if i["supply"] == e) for e in SUPPLY}}
    ot = ledger["origin_totals"]
    origin_detail = {
        "consumption_at_solver_gold_span_contiguous_in_note": ot["consumption_origin_at_solver"],
        "consumption_introduced_after_solver": ot["consumption_origin_introduced_after_solver"],
        "consumption_with_value_printed_in_exemplars": ot["consumption_origin_value_printed_in_knowledge"],
        "all_gold_side_errors_with_value_printed_in_exemplars_E1": sum(1 for i in gold_errs if i["supply"] == "E1"),
        "undetermined_with_value_in_supply_E1_E2_E3": sum(1 for i in gold_errs
                                                         if i["origin"] == "undetermined" and i["supply"] != "none"),
    }
    spurious_split = {
        "filler_contiguous_in_note": sum(i["in_note"] for i in spurious),
        "filler_not_in_note": sum(not i["in_note"] for i in spurious),
        "on_zero_gold_rows": sum(i["zero_gold_row"] for i in spurious),
        "on_gold_rows": sum(not i["zero_gold_row"] for i in spurious),
        "on_intent_right_rows": sum(i["intent_ok"] for i in spurious),
        "oracle_pp_zero_gold_rows": oracle([i for i in spurious if i["zero_gold_row"]]),
        "oracle_pp_gold_rows": oracle([i for i in spurious if not i["zero_gold_row"]]),
    }

    # 3. per slot type
    gold_by_type = Counter(e.type for s in ids for e in gold_e[s])
    by_type = []
    for t, n in sorted(Counter(i["type"] for i in items).items(), key=lambda kv: (-kv[1], kv[0])):
        sub = [i for i in items if i["type"] == t]
        by_type.append({"type": t, "error_items": n, "gold_items": gold_by_type.get(t, 0),
                        "by_class": {k: sum(1 for i in sub if i["kind"] == k) for k in CLASSES},
                        "oracle_pp": oracle(sub)})

    # 4. per scenario (gold scenario, scoring side)
    by_scen = []
    for scen in sorted({gold[s]["scenario"] for s in ids}):
        rows_s = [s for s in ids if gold[s]["scenario"] == scen]
        sub = [i for i in items if i["scenario"] == scen]
        totals = [sum(rescorer.base_rows[s][k] for s in rows_s) for k in range(3)]
        by_scen.append({"scenario": scen, "rows": len(rows_s),
                        "zero_gold_rows": sum(1 for s in rows_s if not gold_e[s]),
                        "gold_items": sum(len(gold_e[s]) for s in rows_s),
                        "by_class": {k: sum(1 for i in sub if i["kind"] == k) for k in CLASSES},
                        "slu_f1_within": round(HR.pooled_f1(totals), 2),
                        "oracle_pp_whole_roster": oracle(sub)})

    # 5. empty-gold split (decision 199) and the S5 masses
    eg = empty_gold_split(gold_e, pred, intent_ok, ids)
    fp_only = {s: [] for s in ids if not gold_e[s] and pred[s]}
    eg["oracle_pp_empty_every_spurious_filled_row"] = round(rescorer.gain(fp_only), 4)
    shares = {s: none_share(phases["rows"][s]["ex_rendered"], {k: v["fillers"] for k, v in pool["values"].items()})
              for s in ids}
    gate = n1_gate(shares, pred, gold_e, N1_THETA)
    n1_items = Counter()
    for s in gate["change"]:
        spur_idx = {it["pred_index"] for it in entity_items(gold_e[s], pred[s]) if it["gold_index"] is None}
        matched = {it["pred_index"] for it in entity_items(gold_e[s], pred[s]) if it["pred_index"] is not None}
        for pi in range(len(pred[s])):
            n1_items["spurious_removed" if pi in spur_idx else "exact_removed" if pi not in matched
                     else "partial_removed"] += 1
    n1_oracle = round(rescorer.gain(gate["change"]), 4)
    n1 = {"theta": N1_THETA, "rows_gated": len(gate["gated"]), "rows_gated_zero_gold": gate["rows_gated_zero_gold"],
          "rows_gated_gold": gate["rows_gated_gold"], "rows_changed": len(gate["change"]),
          **{k: n1_items.get(k, 0) for k in ("spurious_removed", "exact_removed", "partial_removed")},
          "rows_with_no_resolvable_exemplar": sum(1 for v in shares.values() if v is None),
          "oracle_net_pp": n1_oracle, "expected_net_pp_at_m1": expected(n1_oracle, RATES["m1"]["rate"])}
    z = eg["spurious_entities_on_zero_gold_rows"]
    f10_fp = z * RATES["f10_fp_removed_per_zero_gold_fp"]["rate"]
    f10_fn = z * RATES["f10_exact_lost_per_zero_gold_fp"]["rate"]
    s5 = {"addressable_spurious_on_zero_gold_rows": z, "addressable_rows": eg["spurious_filled"],
          "oracle_pp": eg["oracle_pp_empty_every_spurious_filled_row"],
          "expected_pp_at_m1": expected(eg["oracle_pp_empty_every_spurious_filled_row"], RATES["m1"]["rate"]),
          "expected_pp_at_dev2000_rule_reach": expected(eg["oracle_pp_empty_every_spurious_filled_row"],
                                                        RATES["dev2000_vote_rule_reach"]["rate"]),
          "f10_scaled": {"fp_removed": round(f10_fp, 2), "exact_items_lost": round(f10_fn, 2),
                         "gross_pp": round(HR.gain_pp(scores["totals"], fp_removed=f10_fp), 4),
                         "net_pp": round(HR.trade_pp(scores["totals"], fp_removed=f10_fp, exact_lost=f10_fn), 4)},
          "n1_gate": n1,
          "fp_removed_needed_for_target_at_zero_harm": round(HR.items_for_target(scores["totals"], TARGET_PP, "fp"), 2)}

    # 6. S2 mass (MISSING, the missing-slot proposal's target)
    miss = [i for i in gold_errs if i["kind"] == "MISSING"]
    miss_or = oracle(miss)
    s2 = {"addressable_missing_items": len(miss), "rows": len({i["sample_id"] for i in miss}),
          "on_intent_right_rows": sum(i["intent_ok"] for i in miss),
          "oracle_pp": miss_or,
          "oracle_pp_intent_right_rows": oracle([i for i in miss if i["intent_ok"]]),
          "by_origin": {o: sum(1 for i in miss if i["origin"] == o) for o in ORIGINS},
          "by_supply": {e: sum(1 for i in miss if i["supply"] == e) for e in SUPPLY},
          "oracle_pp_value_not_in_supply": oracle([i for i in miss if i["supply"] == "none"]),
          "expected_pp_at_m1": expected(miss_or, RATES["m1"]["rate"]),
          "expected_pp_at_w4_list": expected(miss_or, RATES["w4_list"]["rate"]),
          "expected_pp_at_e5_containment_x_m1": expected(miss_or, E5_CONTAINMENT["rate"] * RATES["m1"]["rate"]),
          "expected_pp_at_e5_containment_x_w4_list": expected(miss_or, E5_CONTAINMENT["rate"] * RATES["w4_list"]["rate"]),
          "fn_recovered_needed_for_target": round(HR.items_for_target(scores["totals"], TARGET_PP, "fn"), 2),
          "fn_recovered_needed_for_cross_flight_bar": round(HR.items_for_target(scores["totals"], CROSS_FLIGHT_BAR_PP, "fn"), 2)}
    s2["missing_items_needed_at_m1"] = math.ceil(s2["fn_recovered_needed_for_target"] / RATES["m1"]["rate"] - 1e-9)
    # The headroom note (section 2, "consumption with the gold value printed in the exemplars") treats printing
    # as already spent for items whose value the supply shows: a proposal tool adds new information only on the
    # MISSING items whose value is NOT in the supply.  These rows are the non-double-counted S2 prediction.
    nis = s2["oracle_pp_value_not_in_supply"]
    s2["missing_items_value_not_in_supply"] = s2["by_supply"]["none"]
    s2["expected_pp_not_in_supply_at_m1"] = expected(nis, RATES["m1"]["rate"])
    s2["expected_pp_not_in_supply_at_w4_list"] = expected(nis, RATES["w4_list"]["rate"])
    s2["expected_pp_not_in_supply_at_e5_containment_x_m1"] = expected(nis, E5_CONTAINMENT["rate"] * RATES["m1"]["rate"])
    s2["expected_pp_not_in_supply_at_e5_containment_x_w4_list"] = expected(
        nis, E5_CONTAINMENT["rate"] * RATES["w4_list"]["rate"])

    checks = dict(derived["checks"])
    checks.update({f"phase.{k}": v for k, v in phases["checks"].items()})
    checks.update({f"node.{k}": v for k, v in nodes["checks"].items()})
    return {
        "label": spec["label"], "title": spec["title"], "split": spec["split"], "rows": len(ids),
        "inputs": {"run_id": spec["run_id"], "attempt": spec["attempt"], "scorer": spec["scorer"],
                   "phases": [phases["relpath"], phases["sha256"]],
                   "outputs": [str((directory / outputs["relpath"]).relative_to(data_root)), outputs["sha256"]],
                   "scores": [str((directory / scores["relpath"]).relative_to(data_root)), scores["sha256"]]},
        "structural_checks": dict(sorted(checks.items())),
        "sealed_totals_word_plus_char": {"tp": round(scores["totals"][0], 6), "fp": round(scores["totals"][1], 6),
                                         "fn": round(scores["totals"][2], 6), "slu_f1": round(base_f1, 4)},
        "intent_right_rows": sum(intent_ok.values()),
        "gold_items": sum(gold_by_type.values()), "pred_items": sum(len(pred[s]) for s in ids),
        "error_items": len(items), "oracle_pp_all_errors": all_oracle,
        "classes": classes, "origin": origin, "origin_detail": origin_detail,
        "ledger_origin_split": ledger["origin_split"], "spurious_split": spurious_split,
        "by_type": by_type, "by_scenario": by_scen, "empty_gold": eg, "s2": s2, "s5": s5,
    }


def control_check(arm: dict) -> dict:
    got = {"classes": {k: arm["classes"][k]["items"] for k in AGREE_EXPECT["classes"]},
           "origin": {k: arm["origin"][k]["items"] for k in ORIGINS},
           "n1_rows_gated": arm["s5"]["n1_gate"]["rows_gated"],
           "n1_spurious_removed": arm["s5"]["n1_gate"]["spurious_removed"]}
    if got != AGREE_EXPECT:
        raise ReadError(f"control arm does not reproduce the v6 baseline: {got}")
    return got


# ---------------------------------------------------------------------------


def build(args) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock

    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    HR = import_path(REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py", "slurp_slu_consumption_headroom")
    ES, GP, W5 = NG.ES, NG.GP, NG.W5
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    labels = parse_arms(args.arms)
    specs = [a for label in labels for a in ARMS if a["label"] == label]
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    m1_values = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    cards = GP.load_contract_bodies(data_root)
    gold_cache: dict = {}
    arms, control = {}, None
    for spec in specs:
        if spec["split"] not in gold_cache:
            gold_cache[spec["split"]] = load_gold_split(lock, data_root, spec["split"], ES)
        arms[spec["label"]] = derive(spec, data_root, gold_cache[spec["split"]], pool, m1_values, cards, NG, HR)
        if spec["label"] == CONTROL:
            control = control_check(arms[spec["label"]])
    return {
        "read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "splits_read": sorted(gold_cache), "arms_selected": labels,
        "control_reproduction": control, "agree_expect": AGREE_EXPECT,
        "rates": {k: {"rate": round(v["rate"], 4), "source": v["source"]} for k, v in RATES.items()},
        "e5_containment": {"rate": round(E5_CONTAINMENT["rate"], 4), "source": E5_CONTAINMENT["source"]},
        "target_pp": TARGET_PP, "cross_flight_bar_pp": CROSS_FLIGHT_BAR_PP,
        "inputs": {"exemplar_pool": [pool["relpath"], pool["sha256"]],
                   "slot_contracts": [cards["relpath"], cards["sha256"]],
                   "m1_snapshot_content_hash": [W5.M1_SNAPSHOT["relpath"], W5.M1_SNAPSHOT["sha256"]]},
        "drivers": {name: [str(p.relative_to(REPO_ROOT)), digest(p)] for name, p in (
            ("node_gain_ledger", REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py"),
            ("consumption_headroom", REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py"),
            ("error_sources", REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py"),
            ("w5_estimate", REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py"))},
        "arms": arms,
    }


# ---------------------------------------------------------------------------
# rendering


def md_table(header: list, rows: list) -> str:
    out = ["| " + " | ".join(str(h) for h in header) + " |",
           "| " + " | ".join("---" if i == 0 else "---:" for i in range(len(header))) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render(r: dict) -> str:
    A = r["arms"]
    labels = list(A)
    out = [f"# {READ_ID} tables", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers "
           "(decisions 28, 86). Counts, pp, type and scenario names only.", ""]
    out += ["## Arms", "", md_table(["arm", "split", "rows", "SLU-F1 (sealed)", "intent-right rows", "gold items",
                                      "predicted", "error items", "oracle all errors pp"],
                                     [[a, A[a]["split"], A[a]["rows"], A[a]["sealed_totals_word_plus_char"]["slu_f1"],
                                       A[a]["intent_right_rows"], A[a]["gold_items"], A[a]["pred_items"],
                                       A[a]["error_items"], A[a]["oracle_pp_all_errors"]] for a in labels]), ""]
    out += ["## Classes (items / exact isolated oracle pp)", "",
            md_table(["class"] + labels,
                     [[k] + [f"{A[a]['classes'][k]['items']} / {A[a]['classes'][k]['oracle_pp']:.2f}" for a in labels]
                      for k in CLASSES]), ""]
    out += ["## Classes on intent-right rows (items / oracle pp)", "",
            md_table(["class"] + labels,
                     [[k] + [f"{A[a]['classes'][k]['on_intent_right_rows']} / "
                             f"{A[a]['classes'][k]['oracle_pp_intent_right_rows']:.2f}" for a in labels]
                      for k in CLASSES]), ""]
    out += ["## Origin of delivered gold-side errors (items / oracle pp)", "",
            md_table(["origin"] + labels,
                     [[o] + [f"{A[a]['origin'][o]['items']} / {A[a]['origin'][o]['oracle_pp']:.2f}" for a in labels]
                      for o in ORIGINS]), ""]
    for a in labels:
        out += [f"### Origin x class, supply evidence ({a})", "",
                md_table(["origin"] + list(GOLD_SIDE) + list(SUPPLY),
                         [[o] + [A[a]["origin"][o]["by_class"][k] for k in GOLD_SIDE]
                          + [A[a]["origin"][o]["by_supply"][e] for e in SUPPLY] for o in ORIGINS]), "",
                md_table(["origin detail", "items"], [[k, v] for k, v in A[a]["origin_detail"].items()]), "",
                md_table(["SPURIOUS split", "value"], [[k, v] for k, v in A[a]["spurious_split"].items()]), ""]
    for a in labels:
        out += [f"### Per slot type ({a}; top {TOP_TYPES} by error items)", "",
                md_table(["type", "gold items", "error items"] + list(CLASSES) + ["oracle pp"],
                         [[t["type"], t["gold_items"], t["error_items"]] + [t["by_class"][k] for k in CLASSES]
                          + [t["oracle_pp"]] for t in A[a]["by_type"][:TOP_TYPES]]), ""]
    for a in labels:
        out += [f"### Per scenario ({a})", "",
                md_table(["scenario", "rows", "zero-gold rows", "gold items"] + list(CLASSES)
                         + ["SLU-F1 within", "oracle pp (whole roster)"],
                         [[s["scenario"], s["rows"], s["zero_gold_rows"], s["gold_items"]]
                          + [s["by_class"][k] for k in CLASSES] + [s["slu_f1_within"], s["oracle_pp_whole_roster"]]
                          for s in A[a]["by_scenario"]]), ""]
    out += ["## Empty-gold rows (decision 199)", "",
            md_table(["quantity"] + labels, [[k] + [A[a]["empty_gold"][k] for a in labels]
                                             for k in A[labels[0]]["empty_gold"]]), ""]
    out += ["## S2 mass (MISSING)", "",
            md_table(["quantity"] + labels, [[k] + [json.dumps(A[a]["s2"][k]) if isinstance(A[a]["s2"][k], dict)
                                                    else A[a]["s2"][k] for a in labels] for k in A[labels[0]]["s2"]]), ""]
    s5_keys = [k for k in A[labels[0]]["s5"] if not isinstance(A[labels[0]]["s5"][k], dict)]
    out += ["## S5 mass (SPURIOUS on zero-gold rows)", "",
            md_table(["quantity"] + labels, [[k] + [A[a]["s5"][k] for a in labels] for k in s5_keys]), "",
            md_table(["F10-scaled"] + labels, [[k] + [A[a]["s5"]["f10_scaled"][k] for a in labels]
                                               for k in A[labels[0]]["s5"]["f10_scaled"]]), "",
            md_table(["N1 gate"] + labels, [[k] + [A[a]["s5"]["n1_gate"][k] for a in labels]
                                            for k in A[labels[0]]["s5"]["n1_gate"]]), ""]
    out += ["## Rates (quoted, not measured here)", "",
            md_table(["rate", "value", "source"], [[k, v["rate"], v["source"]] for k, v in r["rates"].items()]
                     + [["e5_containment", r["e5_containment"]["rate"], r["e5_containment"]["source"]]]), ""]
    if r["control_reproduction"] is not None:
        out += ["## Control", "", f"AGREE re-derivation reproduces the v6 baseline: `{json.dumps(r['control_reproduction'])}`", ""]
    return "\n".join(out) + "\n"


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"|Generated `[^`]*`', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--arms", default=None,
                        help="comma-separated arm labels (default all): " + ",".join(a["label"] for a in ARMS))
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the written outputs")
    args = parser.parse_args(argv)
    report = build(args)
    out_dir = Path(args.data_root) / ANALYSIS_DIR
    if args.arms:
        out_dir = out_dir / ("arms-" + "-".join(parse_arms(args.arms)))
    texts = {"report.json": json.dumps(report, indent=2, sort_keys=True) + "\n", "tables.md": render(report)}
    if args.check:
        bad = [n for n, t in texts.items() if strip_time((out_dir / n).read_text(encoding="utf-8")) != strip_time(t)]
        print("check:", "IDENTICAL apart from generated_at" if not bad else f"DIFFERS in {bad}")
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    manifest = {n: hashlib.sha256(strip_time(t).encode("utf-8")).hexdigest() for n, t in sorted(texts.items())}
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                                 encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
