#!/usr/bin/env python3
"""SLU consumption headroom on the retained AGREE arm (TRAIN Fold A), offline.

Owner decision 192 (2026-09-29): before any SLU mechanism is registered, a purely
offline information-gain analysis must show a predicted gain of at least 1.5 pp
official pooled SLU-F1 (the measured same-flight SLU contrast half-width at
n = 1,080, decision 190); otherwise the mechanism goes cross-flight on
DEV-2000-ADDED (bar 2.5 pp) or nowhere.  This read answers which SLU-side
mechanisms, if any, have that much addressable, convertible headroom.

What it computes (all on the sealed AGREE arm ``SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1``):

1. The pp conversion of item counts.  Official pooled SLU-F1 is the F1 of the
   word-distance plus char-distance TP/FP/FN totals.  One wholly spurious
   prediction contributes 1.0 FP to each channel; one wholly missed gold item
   contributes 1.0 FN to each channel.  So removing k pure false positives moves
   FP by -2k, and recovering k missed items exactly moves TP by +2k and FN by
   -2k.  The table is analytic over the sealed totals (read through
   ``analysis.sealed_credit.row_states.load_scores``), and it is cross-checked
   against an exact in-process counterfactual re-score of the whole class.
2. Exact oracle pp per mechanism-addressable item set (in-process counterfactual
   re-score with the official arithmetic, ``reproduction.slurp_scoring.score_slu``
   through the error-source read's ``repaired`` / ``slu_counts``).
3. The origin split of the node information-gain ledger, re-derived through the
   ledger's own ``derive_arm`` / ``slot_ledger`` (imported unchanged) and checked
   against its published counts.
4. One diagnostic for the 229 undetermined items: where, if anywhere, the gold
   value is present in what the row's Solver was supplied (exemplar printed
   pairs, delivered slot-contract card text), else in TRAIN's own value list for
   the type, else nowhere but the audio.
5. Two model-free scope measurements for SPURIOUS: whether the row's own 20
   delivered exemplars already show the predicted phrase untagged, and a
   deterministic pool-mined do-not-tag rule evaluated exactly (gain and harm).
6. The W5 newly-shown count (re-derived with W5's own ``printed_pairs``) and the
   value-vocabulary route's addressable count.

Gold discipline: gold enters only offline, through the governed TRAIN loader
``data.slurp.load_slurp_split`` (the loader ``ES.load_gold`` wraps), on the
scoring side.  Text discipline: no utterance text, transcript, gold value,
filler, card body or model output is printed or persisted -- only ids, counts,
rates, pp, slot TYPE names, class names and hashes.  Zero model, server,
tokenizer, encoder, embedder, scorer-subprocess, network and GPU contacts.

Deterministic apart from ``generated_at``.  ``--check`` re-derives and compares.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_slu_consumption_headroom.py \\
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
for _p in (str(REPO_ROOT / "src"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from speech_aware_evidence_acquisition.reproduction.slurp_scoring import _prf  # noqa: E402

READ_ID = "SAEA-SLURP-SLU-CONSUMPTION-HEADROOM-OFFLINE-V1"
RECIPE = "slurp-slu-consumption-headroom-offline-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
SCORER = "slurp-slu-official-train"
ROWS = 1080

# one entity item moves the word-distance and the char-distance channel by 1.0 each
ITEM_UNITS = 2.0
KS = (10, 20, 35, 50, 74, 107, 142, 173, 253)
TARGET_PP = 1.5          # decision 190/192: same-flight SLU contrast half-width at n = 1,080
CROSS_FLIGHT_BAR_PP = 2.5
# conversion assumptions (task brief): oracle; CONV probe 32/70; M1 delivered-filler conversion
CONVERSIONS = (("oracle", 1.0, "every addressed item converts"),
               ("conv_probe", 32 / 70, "CONV probe, 32 of 70 newly delivered boundary rows converted "
                                       "(docs/results/2026-09-27-slurp-conv-probe-read.md)"),
               ("m1_measured", 133 / (0.5719 * 941), "M1 delivered-filler conversion 133 / (0.5719 x 941) "
                                                     "(docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md:51)"))
# published counts the re-derivation must reproduce (node ledger, 2026-09-28, sections 2.3 and 2.4)
LEDGER_EXPECT = {"delivered_gold_side_errors": 407, "consumption_origin": 107, "consumption_origin_at_solver": 103,
                 "consumption_origin_value_printed_in_knowledge": 55, "hearing_span_visible_near_or_partial": 71,
                 "undetermined_note_silent": 229, "spurious_d": 253, "spurious_d_in_note": 74,
                 "relisten_contiguous": 35, "relisten_all": 142}
W5_EXPECT_NEWLY = 10
W5_BUILD = "prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1"
SCOPE_MIN_OCC = 5
SCOPE_THRESHOLDS = (0.5, 0.8, 0.9)
VOCAB_TOP_N = 20
LOO_CLOSED, LOO_SEMI = 0.9, 0.6
RELISTEN_KINDS = ("BOUNDARY", "NEAR", "FORMAT")
MAX_NGRAM = 8


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
# pure arithmetic (unit-tested on fakes)


def pooled_f1(totals) -> float:
    """Official pooled SLU-F1 in percent from combined (word + char) TP/FP/FN."""
    return 100.0 * _prf(*totals)[2]


def moved(totals, fp_removed: float = 0.0, fn_recovered: float = 0.0):
    tp, fp, fn = totals
    return (tp + ITEM_UNITS * fn_recovered, fp - ITEM_UNITS * fp_removed, fn - ITEM_UNITS * fn_recovered)


def gain_pp(totals, fp_removed: float = 0.0, fn_recovered: float = 0.0) -> float:
    return pooled_f1(moved(totals, fp_removed, fn_recovered)) - pooled_f1(totals)


def conversion_table(totals, ks=KS) -> list:
    return [{"k": k, "remove_k_fp_pp": round(gain_pp(totals, fp_removed=k), 4),
             "recover_k_fn_pp": round(gain_pp(totals, fn_recovered=k), 4),
             "both_k_each_pp": round(gain_pp(totals, fp_removed=k, fn_recovered=k), 4)} for k in ks]


def items_for_target(totals, target_pp: float, mode: str) -> float:
    """Continuous number of CONVERTED items k* at which the gain reaches ``target_pp``.
    ``mode``: 'fp' (remove k FPs), 'fn' (recover k FNs), 'both' (k of each)."""

    def gain(k):
        return gain_pp(totals, fp_removed=k if mode in ("fp", "both") else 0.0,
                       fn_recovered=k if mode in ("fn", "both") else 0.0)

    hi = max(totals[1], totals[2]) / ITEM_UNITS
    if gain(hi) < target_pp:
        return math.inf
    lo = 0.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if gain(mid) >= target_pp:
            hi = mid
        else:
            lo = mid
    return hi


def minimum_items(totals, target_pp: float, conversions=CONVERSIONS) -> dict:
    out = {}
    for mode in ("fp", "fn", "both"):
        k_star = items_for_target(totals, target_pp, mode)
        row = {"converted_items_continuous": round(k_star, 3)}
        for label, rate, _ in conversions:
            row[f"addressable_items_at_{label}"] = math.ceil(k_star / rate - 1e-9)
        out[mode] = row
    return out


def trade_pp(totals, fp_removed: float = 0.0, exact_lost: float = 0.0) -> float:
    """Gain of removing ``fp_removed`` pure false positives while losing ``exact_lost`` exact items
    (each lost exact item: TP -1 and FN +1 per channel)."""
    tp, fp, fn = totals
    after = (tp - ITEM_UNITS * exact_lost, fp - ITEM_UNITS * fp_removed, fn + ITEM_UNITS * exact_lost)
    return pooled_f1(after) - pooled_f1(totals)


def expected_pp(oracle_pp: float, rate) -> float | None:
    return None if rate is None else round(oracle_pp * rate, 4)


def ngrams(tokens: list, max_n: int = MAX_NGRAM) -> set:
    return {tuple(tokens[i:i + n]) for n in range(1, max_n + 1) for i in range(len(tokens) - n + 1)}


def scope_counts(exemplars: list) -> tuple:
    """(occurrence counter, tagged counter) over n-grams, counted once per exemplar.
    ``exemplars``: list of (utterance tokens, [filler token lists])."""
    occ, tagged = Counter(), Counter()
    for tokens, fillers in exemplars:
        occ.update(ngrams(tokens))
        inside = set()
        for f in fillers:
            inside |= ngrams(f)
        tagged.update(inside)
    return occ, tagged


def untagged_share(phrase: tuple, occ: Counter, tagged: Counter):
    n = occ.get(phrase, 0)
    if n == 0:
        return n, None
    return n, 1.0 - min(tagged.get(phrase, 0), n) / n


def row_untagged(phrase: tuple, exemplars: list) -> bool:
    """True if one of the row's own exemplars contains the phrase outside every tagged filler."""
    for tokens, fillers in exemplars:
        if phrase in ngrams(tokens, len(phrase)) and not any(phrase in ngrams(f, len(phrase)) for f in fillers):
            return True
    return False


def evidence_class(printed_same_type: bool, printed_any_type: bool, in_card: bool, in_vocab: bool) -> str:
    if printed_same_type:
        return "E1 exemplars print the gold (type, value)"
    if printed_any_type:
        return "E2 exemplars print the value under another type"
    if in_card:
        return "E3 a delivered slot-contract card names the value"
    if in_vocab:
        return "E4 not supplied; in TRAIN's own value list for the type"
    return "E5 nowhere but the audio (not supplied, not in TRAIN's value list)"


EVIDENCE_CLASSES = ("E1 exemplars print the gold (type, value)", "E2 exemplars print the value under another type",
                    "E3 a delivered slot-contract card names the value",
                    "E4 not supplied; in TRAIN's own value list for the type",
                    "E5 nowhere but the audio (not supplied, not in TRAIN's value list)")


def vocab_classes(values_by_type: dict) -> dict:
    """The knowledge-content audit's rule: leave-one-utterance-out value coverage over TRAIN outside
    Fold A; closed >= 0.9, semi-closed >= 0.6, else open."""
    out = {}
    for t, counter in values_by_type.items():
        total = sum(counter.values())
        covered = sum(c for c in counter.values() if c >= 2)
        cov = covered / total if total else 0.0
        out[t] = "closed" if cov >= LOO_CLOSED else "semi-closed" if cov >= LOO_SEMI else "open"
    return out


# ---------------------------------------------------------------------------
# counterfactual scoring


class Rescorer:
    """Exact in-process re-score of edited rows against the sealed-equal base totals."""

    def __init__(self, gold: dict, pred: dict, counts_fn, ids: list):
        self.gold, self.pred, self.counts_fn, self.ids = gold, pred, counts_fn, ids
        self.base_rows = {sid: counts_fn(gold[sid], pred[sid]) for sid in ids}
        self.base = tuple(sum(self.base_rows[s][i] for s in ids) for i in range(3))

    def totals_with(self, new_preds: dict) -> tuple:
        delta = [0.0, 0.0, 0.0]
        for sid, pred in new_preds.items():
            after = self.counts_fn(self.gold[sid], pred)
            for i in range(3):
                delta[i] += after[i] - self.base_rows[sid][i]
        return tuple(self.base[i] + delta[i] for i in range(3))

    def gain(self, new_preds: dict) -> float:
        return pooled_f1(self.totals_with(new_preds)) - pooled_f1(self.base)

    def edited_rows(self, new_preds: dict) -> dict:
        rows = dict(self.base_rows)
        for sid, pred in new_preds.items():
            rows[sid] = self.counts_fn(self.gold[sid], pred)
        return rows


def repair_preds(rows_items: dict, gold: dict, pred: dict, repaired_fn) -> dict:
    """sid -> the prediction list with exactly the given entity items repaired to gold."""
    return {sid: repaired_fn(gold[sid], pred[sid], items) for sid, items in rows_items.items() if items}


def drop_preds(drops: dict, pred: dict) -> dict:
    return {sid: [e for i, e in enumerate(pred[sid]) if i not in idx] for sid, idx in drops.items() if idx}


def group_items(items: list) -> dict:
    out = defaultdict(list)
    for it in items:
        out[it["sample_id"]].append(it["entity_item"])
    return out


# ---------------------------------------------------------------------------
# derivation


def build(args) -> dict:
    from speech_aware_evidence_acquisition.analysis.sealed_credit import row_states as RS
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import (
        canonical, contiguous_in, entity_items, fold)
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split

    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    ES, GP, W5 = NG.ES, NG.GP, NG.W5

    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    records = load_slurp_split(lock, data_root, "train", workers=4)
    gold = {r.sample_id: {"intent": r.intent, "scenario": r.scenario, "action": r.action,
                          "entities": tuple(ES.SlotEntity(e.type, e.filler) for e in r.entities)} for r in records}
    utt_of = {r.sample_id: r.utterance_id for r in records}

    spec = NG.ARMS[0]
    if spec["run_id"] != "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1":
        raise ReadError("the ledger's primary arm is not the AGREE arm")
    phases = GP.load_phases(data_root, spec)
    directory = phases["directory"]
    outputs = ES.load_outputs(directory, spec["run_id"])
    scores = ES.load_scores(directory, spec["run_id"])
    sealed = RS.load_scores(directory, spec["run_id"], SCORER)
    nodes = NG.load_node_states(data_root, spec)
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    m1_values = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    ids = sorted(scores["rows"])
    if len(ids) != ROWS:
        raise ReadError("roster is not the 1,080-row Fold A roster")

    # 1. sealed totals and the conversion table
    sealed_totals = tuple(sum(sealed["rows"][s][k] for s in ids) for k in ("tp", "fp", "fn"))
    pred = {sid: outputs["rows"][sid]["entities"] for sid in ids}
    gold_e = {sid: gold[sid]["entities"] for sid in ids}
    rescorer = Rescorer(gold_e, pred, ES.slu_counts, ids)
    if any(abs(a - b) > 1e-6 for a, b in zip(rescorer.base, sealed_totals)):
        raise ReadError("in-process totals do not reproduce the sealed official totals")
    base_f1 = pooled_f1(sealed_totals)

    # 2. the ledger's own item derivation (imported unchanged) and its origin split
    arm = {"label": spec["label"], "phases": phases["rows"], "outputs": outputs["rows"], "scores": scores["rows"],
           "nodes": nodes["rows"]}
    derived = NG.derive_arm(arm, gold, ids, pool, m1_values)
    ledger = NG.slot_ledger(derived["rows"], derived["items"], ids)
    ot = ledger["origin_totals"]
    got = {"delivered_gold_side_errors": ot["delivered_gold_side_errors"], "consumption_origin": ot["consumption_origin"],
           "consumption_origin_at_solver": ot["consumption_origin_at_solver"],
           "consumption_origin_value_printed_in_knowledge": ot["consumption_origin_value_printed_in_knowledge"],
           "hearing_span_visible_near_or_partial": ot["hearing_span_visible_near_or_partial"],
           "undetermined_note_silent": ot["undetermined_note_silent"],
           "spurious_d": ledger["spurious_edges"]["d"],
           "spurious_d_in_note": ledger["spurious_edges"]["d_spurious_filler_contiguous_in_note"],
           "relisten_contiguous": ledger["relisten_addressable"].get("contiguous_in_note", 0),
           "relisten_all": ledger["relisten_addressable"].get("contiguous_in_note", 0)
           + ledger["relisten_addressable"].get("not_contiguous", 0)}
    if got != LEDGER_EXPECT:
        raise ReadError(f"ledger re-derivation differs from the published counts: {got}")

    # join the ledger items with the entity items (pred indices for the counterfactual)
    gold_items, spurious_items = [], []
    for sid in ids:
        its = entity_items(gold_e[sid], pred[sid])
        by_gold = {it["gold_index"]: it for it in its if it["gold_index"] is not None}
        tokens = nodes["rows"][sid]["perception"]["tokens"] if nodes["rows"][sid]["perception"] else []
        for it in its:
            if it["gold_index"] is None:
                filler = pred[sid][it["pred_index"]]
                spurious_items.append({"sample_id": sid, "entity_item": it, "type": it["type"],
                                       "in_note": contiguous_in(canonical(filler.filler).split(), tokens),
                                       "no_gold_row": not gold_e[sid],
                                       "intent_ok": derived["rows"][sid]["d_ok"],
                                       "phrase": tuple(fold(filler.filler).split())})
        for li in (i for i in derived["items"] if i["sample_id"] == sid):
            if li["d"] == "EXACT":
                continue
            it = by_gold[li["gold_index"]]
            if it["kind"] != li["d"]:
                raise ReadError("ledger item kind and entity item kind disagree")
            gold_items.append({**li, "entity_item": it})
    if len(gold_items) != 407 or len(spurious_items) != 253:
        raise ReadError("item join does not reproduce 407 / 253")

    def oracle(items) -> float:
        return round(rescorer.gain(repair_preds(group_items(items), gold_e, pred, ES.repaired)), 4)

    def sel(pred_fn):
        return [i for i in gold_items if pred_fn(i)]

    classes = {
        "MISSING (all)": sel(lambda i: i["d"] == "MISSING"),
        "SPURIOUS (all)": spurious_items,
    }
    cross = {k: {"items": len(v), "exact_oracle_pp": oracle(v)} for k, v in classes.items()}
    cross["MISSING (all)"]["analytic_pp"] = round(gain_pp(sealed_totals, fn_recovered=len(classes["MISSING (all)"])), 4)
    cross["SPURIOUS (all)"]["analytic_pp"] = round(gain_pp(sealed_totals, fp_removed=len(spurious_items)), 4)
    cross["MISSING (all)"]["error_source_isolated_pp"] = 9.80
    cross["SPURIOUS (all)"]["error_source_isolated_pp"] = 8.46

    # 3. addressable item sets
    cons_all = sel(lambda i: i["origin"].startswith("consumption"))
    cons_solver = sel(lambda i: i["origin"].startswith("consumption: note"))
    cons_printed = sel(lambda i: i["origin"].startswith("consumption") and i["k_value_printed"])
    hearing = sel(lambda i: i["origin"].startswith("hearing"))
    und = sel(lambda i: i["origin"].startswith("undetermined"))
    relisten35 = sel(lambda i: i["d"] in RELISTEN_KINDS and i["note"] == "CONTIGUOUS")
    relisten142 = sel(lambda i: i["d"] in RELISTEN_KINDS)
    hearing_or_relisten = [i for i in gold_items if i in hearing or i in relisten35]
    sp_in = [s for s in spurious_items if s["in_note"]]
    sp_out = [s for s in spurious_items if not s["in_note"]]
    sp_nogold = [s for s in spurious_items if s["no_gold_row"]]
    sp_ok = [s for s in spurious_items if s["intent_ok"]]

    def kinds(items):
        return dict(sorted(Counter(i["d"] if "d" in i else "SPURIOUS" for i in items).items()))

    sets = {}
    for label, items in (("consumption origin, total", cons_all),
                         ("consumption at the Solver (gold span contiguous in the note)", cons_solver),
                         ("consumption origin with the gold value printed in the exemplars", cons_printed),
                         ("consumption at the Solver, MISSING only", [i for i in cons_solver if i["d"] == "MISSING"]),
                         ("consumption at the Solver, span/type kinds (not MISSING)",
                          [i for i in cons_solver if i["d"] != "MISSING"]),
                         ("hearing/span visible (note near or partial)", hearing),
                         ("re-listen addressable, gold contiguous in note (BOUNDARY/NEAR/FORMAT)", relisten35),
                         ("re-listen kinds, all (BOUNDARY/NEAR/FORMAT)", relisten142),
                         ("hearing-visible 71 union re-listen 35", hearing_or_relisten),
                         ("undetermined (note silent)", und),
                         ("SPURIOUS, filler contiguous in the note", sp_in),
                         ("SPURIOUS, filler not in the note", sp_out),
                         ("SPURIOUS on rows with no gold entity", sp_nogold),
                         ("SPURIOUS on intent-right rows", sp_ok)):
        sets[label] = {"items": len(items), "kinds": kinds(items), "exact_oracle_pp": oracle(items),
                       "rows": len({i["sample_id"] for i in items})}

    # 4. evidence split (the 229 diagnostic), vocabulary route, W5 newly shown
    fold_utts = {utt_of[s] for s in ids}
    # utterance-deduplicated value counts per type (one count per utterance, not per recording)
    values_by_type = defaultdict(Counter)
    utt_seen = set()
    for r in records:
        if r.utterance_id in fold_utts or r.utterance_id in utt_seen:
            continue
        utt_seen.add(r.utterance_id)
        for t, f in {(e.type, fold(e.filler)) for e in r.entities}:
            values_by_type[t][f] += 1
    vclass = vocab_classes(values_by_type)
    top_n = {t: {f for f, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:VOCAB_TOP_N]}
             for t, c in values_by_type.items()}
    card_bodies = GP.load_contract_bodies(data_root)
    card_missing = Counter()

    def in_cards(sid, value) -> bool:
        if len(value) < 3:
            return False
        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])")
        for cid in phases["rows"][sid]["contracts"]:
            body = card_bodies["bodies"].get(cid)
            if body is None:
                card_missing["unresolved"] += 1
                continue
            if pattern.search(body):
                return True
        return False

    m1_by_key = {vid.split("value:", 1)[-1]: v for vid, v in m1_values.items()}
    for i in gold_items:
        g = gold_e[i["sample_id"]][i["gold_index"]]
        value = fold(g.filler)
        i["_in_vocab"] = value in values_by_type.get(g.type, ())
        i["_in_top_n"] = value in top_n.get(g.type, ())
        i["_vclass"] = vclass.get(g.type, "absent")
        i["_evidence"] = evidence_class(i["k_value_printed"], i["k_value_printed_any_type"],
                                        in_cards(i["sample_id"], value), i["_in_vocab"])
    split = {}
    for label, items in (("undetermined (229)", und), ("consumption origin (107)", cons_all),
                         ("hearing-visible (71)", hearing), ("all delivered gold-side errors (407)", gold_items)):
        table = {}
        for ev in EVIDENCE_CLASSES:
            sub = [i for i in items if i["_evidence"] == ev]
            table[ev] = {"items": len(sub), "MISSING": sum(i["d"] == "MISSING" for i in sub),
                         "not MISSING": sum(i["d"] != "MISSING" for i in sub)}
        split[label] = {"by_evidence": table, "kinds": kinds(items),
                        "exact_oracle_pp_by_evidence": {ev: oracle([i for i in items if i["_evidence"] == ev])
                                                        for ev in EVIDENCE_CLASSES}}
    und_miss = [i for i in und if i["d"] == "MISSING"]
    split["undetermined (229)"]["missing_vs_not"] = {
        "MISSING": {"items": len(und_miss), "exact_oracle_pp": oracle(und_miss)},
        "not MISSING (a value of some type was emitted for the mention)":
            {"items": len(und) - len(und_miss), "exact_oracle_pp": oracle([i for i in und if i["d"] != "MISSING"])}}

    # vocabulary route: gold-side error items whose value is in TRAIN's list and not already printed by M1
    vocab_sets = {}
    for label, pred_fn in (
            ("in TRAIN value list, not printed by M1", lambda i: i["_in_vocab"] and not i["k_value_printed"]),
            ("... closed types only", lambda i: i["_in_vocab"] and not i["k_value_printed"] and i["_vclass"] == "closed"),
            (f"... in the type's top-{VOCAB_TOP_N} values", lambda i: i["_in_top_n"] and not i["k_value_printed"]),
            ("in TRAIN value list, already printed by M1 (still wrong)",
             lambda i: i["_in_vocab"] and i["k_value_printed"])):
        items = [i for i in gold_items if pred_fn(i)]
        vocab_sets[label] = {"items": len(items), "kinds": kinds(items), "exact_oracle_pp": oracle(items)}

    # W5 newly shown (W5's own printed_pairs over its selection; newly = printed by W5, not by M1)
    selection = {}
    with (data_root / W5_BUILD / "selection-v1.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                selection[row["id"]] = row
    w5_values = W5.snapshot_values(data_root, W5.W5_SNAPSHOT)
    w5_newly = []
    w5_newly_after_vocab_filter = []
    for i in gold_items:
        sel_row = selection[i["sample_id"]]
        g = gold_e[i["sample_id"]][i["gold_index"]]
        pair = (g.type, ES.fold(g.filler))
        m1_pairs = set().union(*(W5.printed_pairs(m1_values[v].content) for v in sel_row["m1_value_ids"])) \
            if sel_row["m1_value_ids"] else set()
        w5_pairs = set().union(*(W5.printed_pairs(w5_values[v].content) for v in sel_row["w5_value_ids"]))
        if pair in w5_pairs and pair not in m1_pairs:
            w5_newly.append(i)
            if i["_in_vocab"] and i["_vclass"] in ("closed", "semi-closed"):
                w5_newly_after_vocab_filter.append(i)
    if len(w5_newly) != W5_EXPECT_NEWLY:
        raise ReadError(f"W5 newly-shown re-derivation gives {len(w5_newly)}, not {W5_EXPECT_NEWLY}")
    w5 = {"newly_shown": {"items": len(w5_newly), "kinds": kinds(w5_newly), "exact_oracle_pp": oracle(w5_newly)},
          "newly_shown_kept_by_a_closed_or_semi_closed_vocabulary_filter":
              {"items": len(w5_newly_after_vocab_filter), "exact_oracle_pp": oracle(w5_newly_after_vocab_filter)}}

    # 5. SPURIOUS scope measurements
    ex_tokens = {}
    for key, v in pool["values"].items():
        ex_tokens[key] = (v["utterance"].split(), [f.split() for fl in v["fillers"].values() for f in fl])
    occ, tagged = scope_counts(list(ex_tokens.values()))
    rows_ex = {sid: [ex_tokens[k] for k in phases["rows"][sid]["ex_rendered"] if k in ex_tokens] for sid in ids}

    def row_scope(sid, phrase):
        return bool(phrase) and row_untagged(phrase, rows_ex[sid])

    sp_row_shown = [s for s in spurious_items if row_scope(s["sample_id"], s["phrase"])]

    def prediction_view(pred_by_sid: dict, with_row_scope: bool) -> list:
        """Every delivered prediction with its class (spurious / exact / other matched) and pool scope stats."""
        out = []
        for sid in ids:
            its = entity_items(gold_e[sid], pred_by_sid[sid])
            spur_idx = {it["pred_index"] for it in its if it["gold_index"] is None}
            matched_idx = {it["pred_index"] for it in its if it["pred_index"] is not None}
            for pi, e in enumerate(pred_by_sid[sid]):
                phrase = tuple(fold(e.filler).split())
                n, u = untagged_share(phrase, occ, tagged)
                out.append({"sample_id": sid, "pred_index": pi, "spurious": pi in spur_idx,
                            "exact": pi not in matched_idx, "occ": n, "untagged": u,
                            "row_shown_untagged": row_scope(sid, phrase) if with_row_scope else None})
        return out

    def scope_rule_eval(pred_by_sid: dict, rs: "Rescorer", views: list) -> dict:
        rules = {}
        for theta in SCOPE_THRESHOLDS:
            hit = [p for p in views if p["occ"] >= SCOPE_MIN_OCC and p["untagged"] is not None and p["untagged"] >= theta]
            drops = defaultdict(set)
            for p in hit:
                drops[p["sample_id"]].add(p["pred_index"])
            new = drop_preds(drops, pred_by_sid)
            b = NG.boot_f1(ids, rs.base_rows, rs.edited_rows(new))
            rules[f"untagged share >= {theta}, pool occurrences >= {SCOPE_MIN_OCC}"] = {
                "predictions_dropped": len(hit), "spurious_dropped": sum(p["spurious"] for p in hit),
                "exact_dropped": sum(p["exact"] for p in hit),
                "other_matched_dropped": sum(not p["spurious"] and not p["exact"] for p in hit),
                "rows": len(drops), "exact_pp": round(rs.gain(new), 4), "bootstrap_pp": b}
        return rules

    all_preds = prediction_view(pred, True)
    if sum(p["spurious"] for p in all_preds) != 253 or sum(p["exact"] for p in all_preds) != 534:
        raise ReadError("prediction view does not reproduce 253 spurious / 534 exact")
    exact_row_shown = sum(1 for p in all_preds if p["exact"] and p["row_shown_untagged"])
    # replicate: the same rule (same pool statistics, same thresholds) on the wave A/A bytes re-flown
    wave = NG.ARMS[1]
    wave_dir = data_root / "runs" / wave["run_id"] / wave["attempt"]
    wave_out = ES.load_outputs(wave_dir, wave["run_id"])
    wave_pred = {sid: wave_out["rows"][sid]["entities"] for sid in ids}
    wave_sealed = RS.load_scores(wave_dir, wave["run_id"], SCORER)
    wave_rs = Rescorer(gold_e, wave_pred, ES.slu_counts, ids)
    wave_totals = tuple(sum(wave_sealed["rows"][s][k] for s in ids) for k in ("tp", "fp", "fn"))
    if any(abs(a - b) > 1e-6 for a, b in zip(wave_rs.base, wave_totals)):
        raise ReadError("wave A/A in-process totals do not reproduce its sealed totals")
    spurious_scope = {
        "spurious_with_the_phrase_shown_untagged_in_the_rows_own_20_exemplars": len(sp_row_shown),
        "exact_predictions_with_the_phrase_shown_untagged_in_the_rows_own_20_exemplars": exact_row_shown,
        "exact_predictions": sum(p["exact"] for p in all_preds),
        "spurious_with_pool_occurrences_ge_min": sum(1 for p in all_preds if p["spurious"] and p["occ"] >= SCOPE_MIN_OCC),
        "oracle_pp_row_shown_spurious": oracle(sp_row_shown),
        "deterministic_pool_rule": scope_rule_eval(pred, rescorer, all_preds),
        "deterministic_pool_rule_on_wave_aa_replicate": scope_rule_eval(wave_pred, wave_rs, prediction_view(wave_pred, False)),
        "wave_aa": {"run_id": wave["run_id"], "scores": [wave_sealed["relpath"], wave_sealed["sha256"]],
                    "outputs": [wave_out["relpath"], wave_out["sha256"]], "slu_f1": round(pooled_f1(wave_totals), 4)},
    }

    # no-gold rows: an oracle explicit-empty decision
    nogold_rows = [sid for sid in ids if not gold_e[sid]]
    fp_only_rows = [sid for sid in nogold_rows if pred[sid]]
    empty_all = rescorer.gain({sid: [] for sid in fp_only_rows})
    # F10 (docs/results/2026-09-25-slurp-f10-complete-verdict.md:18-21): exemplar-delivered empty answers moved
    # empty-gold exact FP 142 -> 120 and non-empty exact FN 384 -> 397 on R01C 625; scaled per empty-gold FP
    f10_fp_rate, f10_fn_per_fp = 22 / 142, 13 / 142
    f10_fp = len(sp_nogold) * f10_fp_rate
    f10_fn = len(sp_nogold) * f10_fn_per_fp
    b4 = {"rows_without_gold_entities": len(nogold_rows), "fp_only_rows": len(fp_only_rows),
          "spurious_on_fp_only_rows": len(sp_nogold), "oracle_pp_empty_every_fp_only_row": round(empty_all, 4),
          "dev2000_rule_reach_fp_only": [14.4, 162.2],
          "expected_pp_at_the_dev2000_rule_reach": round(empty_all * 14.4 / 162.2, 4),
          "f10_scaled": {"fp_removed": round(f10_fp, 2), "exact_items_lost": round(f10_fn, 2),
                         "gain_pp_fp_only": round(gain_pp(sealed_totals, fp_removed=f10_fp), 4),
                         "net_pp_with_the_fn_harm": round(trade_pp(sealed_totals, fp_removed=f10_fp, exact_lost=f10_fn), 4)}}

    # composition sets (exact oracle of the union, overlaps removed)
    def union(*lists):
        seen, out = set(), []
        for lst in lists:
            for i in lst:
                key = (i["sample_id"], i["gold_index"])
                if key not in seen:
                    seen.add(key)
                    out.append(i)
        return out

    vocab_new = [i for i in gold_items if i["_in_vocab"] and not i["k_value_printed"]]
    composition = {
        "vocabulary route (not printed by M1) union W5 newly shown": {
            "items": len(union(vocab_new, w5_newly)), "exact_oracle_pp": oracle(union(vocab_new, w5_newly))},
        "W5 newly shown inside the vocabulary route": len([i for i in w5_newly if i in vocab_new]),
    }

    conv = {label: {"rate": round(rate, 4), "source": src} for label, rate, src in CONVERSIONS}
    return {
        "read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "arm": {"run_id": spec["run_id"], "attempt": spec["attempt"],
                "scores": [sealed["relpath"], sealed["sha256"]], "phases": [phases["relpath"], phases["sha256"]],
                "outputs": [outputs["relpath"], outputs["sha256"]]},
        "inputs": {"exemplar_pool": [pool["relpath"], pool["sha256"]],
                   "slot_contracts": [card_bodies["relpath"], card_bodies["sha256"]],
                   "w5_selection_sha256": digest(data_root / W5_BUILD / "selection-v1.jsonl"),
                   "m1_snapshot_content_hash": W5.M1_SNAPSHOT["sha256"], "w5_snapshot_content_hash": W5.W5_SNAPSHOT["sha256"]},
        "drivers": {name: [str(p.relative_to(REPO_ROOT)), digest(p)] for name, p in (
            ("node_gain_ledger", REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py"),
            ("error_sources", REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py"),
            ("w5_estimate", REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py"))},
        "sealed_totals_word_plus_char": {"tp": round(sealed_totals[0], 6), "fp": round(sealed_totals[1], 6),
                                         "fn": round(sealed_totals[2], 6), "slu_f1": round(base_f1, 4)},
        "item_units": ITEM_UNITS, "target_pp": TARGET_PP, "cross_flight_bar_pp": CROSS_FLIGHT_BAR_PP,
        "conversions": conv,
        "conversion_table": conversion_table(sealed_totals),
        "minimum_items_for_target": minimum_items(sealed_totals, TARGET_PP),
        "minimum_items_for_cross_flight_bar": minimum_items(sealed_totals, CROSS_FLIGHT_BAR_PP),
        "whole_class_cross_check": cross,
        "ledger_reproduction": got,
        "addressable_sets": sets,
        "evidence_split": split,
        "vocabulary_route": vocab_sets,
        "vocabulary_classes": dict(sorted(Counter(vclass.values()).items())),
        "w5": w5,
        "spurious_scope": spurious_scope,
        "explicit_empty": b4,
        "composition": composition,
        "measured_analogues": {
            "w4_card_value_list": {"converted": 5, "addressed": 97,
                                   "rate": round(5 / 97, 4),
                                   "source": "docs/results/2026-09-28-slurp-w4-fold-a-read.md:189-190 "
                                             "(K2 omission listed 85 -> 83, wrong filler listed 12 -> 9; cross-flight vs wave A/A)"},
            "vocabulary_route_expected_pp_at_w4_rate": round(vocab_sets["in TRAIN value list, not printed by M1"]["exact_oracle_pp"] * 5 / 97, 4),
            "vocabulary_route_expected_pp_at_m1_rate": round(vocab_sets["in TRAIN value list, not printed by M1"]["exact_oracle_pp"] * CONVERSIONS[2][1], 4),
            "w5_expected_pp_at_m1_rate": round(w5["newly_shown"]["exact_oracle_pp"] * CONVERSIONS[2][1], 4),
        },
        "card_ids_unresolved": card_missing.get("unresolved", 0),
    }


# ---------------------------------------------------------------------------
# rendering


def md_table(header: list, rows: list) -> str:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render(r: dict) -> str:
    t = r["sealed_totals_word_plus_char"]
    parts = [f"# {READ_ID}", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers (decisions 28, 86).", "",
             f"Sealed totals (word + char): TP {t['tp']}, FP {t['fp']}, FN {t['fn']}; pooled SLU-F1 {t['slu_f1']}.", "",
             "## Conversion table (analytic, converted items)", "",
             md_table(["k", "remove k FP pp", "recover k FN pp", "both (k each) pp"],
                      [[c["k"], c["remove_k_fp_pp"], c["recover_k_fn_pp"], c["both_k_each_pp"]] for c in r["conversion_table"]]),
             "", "## Minimum items", ""]
    for bar, key in ((r["target_pp"], "minimum_items_for_target"), (r["cross_flight_bar_pp"], "minimum_items_for_cross_flight_bar")):
        parts.append(f"Bar {bar} pp:")
        parts.append("")
        parts.append(md_table(["mode", "converted items k*", "addressable at oracle", "at conv_probe", "at m1_measured"],
                              [[m, v["converted_items_continuous"], v["addressable_items_at_oracle"],
                                v["addressable_items_at_conv_probe"], v["addressable_items_at_m1_measured"]]
                               for m, v in r[key].items()]))
        parts.append("")
    parts += ["## Whole-class cross-check", "",
              md_table(["class", "items", "analytic pp", "exact oracle pp", "error-source isolated pp"],
                       [[k, v["items"], v["analytic_pp"], v["exact_oracle_pp"], v["error_source_isolated_pp"]]
                        for k, v in r["whole_class_cross_check"].items()]),
              "", "## Addressable sets (exact oracle)", "",
              md_table(["set", "items", "rows", "exact oracle pp", "kinds"],
                       [[k, v["items"], v["rows"], v["exact_oracle_pp"], json.dumps(v["kinds"])]
                        for k, v in r["addressable_sets"].items()]),
              "", "## Evidence split", ""]
    for label, block in r["evidence_split"].items():
        parts.append(f"### {label}")
        parts.append("")
        parts.append(md_table(["evidence", "items", "MISSING", "not MISSING", "exact oracle pp"],
                              [[ev, v["items"], v["MISSING"], v["not MISSING"], block["exact_oracle_pp_by_evidence"][ev]]
                               for ev, v in block["by_evidence"].items()]))
        parts.append("")
        if "missing_vs_not" in block:
            parts.append(md_table(["undetermined", "items", "exact oracle pp"],
                                  [[k, v["items"], v["exact_oracle_pp"]] for k, v in block["missing_vs_not"].items()]))
            parts.append("")
    parts += ["## Vocabulary route", "",
              md_table(["set", "items", "exact oracle pp", "kinds"],
                       [[k, v["items"], v["exact_oracle_pp"], json.dumps(v["kinds"])] for k, v in r["vocabulary_route"].items()]),
              "", f"Vocabulary classes: {json.dumps(r['vocabulary_classes'])}", "",
              "## W5", "", "```json", json.dumps(r["w5"], indent=2, sort_keys=True), "```", "",
              "## SPURIOUS scope", "", "```json", json.dumps(r["spurious_scope"], indent=2, sort_keys=True), "```", "",
              "## Explicit empty", "", "```json", json.dumps(r["explicit_empty"], indent=2, sort_keys=True), "```", "",
              "## Composition", "", "```json", json.dumps(r["composition"], indent=2, sort_keys=True), "```", ""]
    return "\n".join(parts)


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"|Generated `[^`]*`', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the written outputs")
    args = parser.parse_args(argv)
    report = build(args)
    out_dir = Path(args.data_root) / ANALYSIS_DIR
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
