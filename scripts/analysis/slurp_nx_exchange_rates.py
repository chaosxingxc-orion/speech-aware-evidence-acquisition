#!/usr/bin/env python3
"""NX R0.2 / E3: node-local -> official exchange rates on the sealed COMP-1b bytes (zero GPU).

Programme ``docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`` (sections C0.1, C1 E3, C2 R0.2,
C3).  Every NX round must declare its predicted official effect before flight (decision 192); this read
supplies the conversion table it cites, measured once on two sealed, officially scored pools:

* ``comp1b_fold_a`` -- ``SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1`` (TRAIN Fold A, 1,080 rows);
* ``a2``            -- ``SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1`` (DEV-2000-ADDED, 1,000 rows).

Per pool it computes:

1. the Solver node (first raw answer, from the sealed MODEL_RESPONSE of the row's first Solver contact) and the
   delivered counterpart (sealed ``outputs.jsonl``): parse validity, entity exact-set correctness, empty-gold
   false fill, non-empty exact, per slot type; and the official pooled SLU-F1 change of ONE (and ten) extra
   exactly-correct row(s), removed false fill(s) on empty-gold rows, recovered MISSING entity(ies), removed
   SPURIOUS entity(ies) -- analytic (TP/FP/FN edit of the pooled micro F1, the headroom note's
   ``gain_pp``) and empirical (exact in-process re-score of each real candidate edit, the headroom
   ``Rescorer``);
2. intent: pp per converted row and the Perception-side split of the delivered intent errors
   (``slurp_node_gain_ledger.derive_arm`` fields ``perc_rank`` / ``d_ok`` / ``d_parsed``);
3. the C3 failure-class contrast table at the Solver node and at delivery: class (SPURIOUS / MISSING /
   WRONG-TYPE / BOUNDARY / NEAR / WRONG-VALUE / FORMAT, plus the row classes EMPTY-GOLD-FILL and PARSE-FAIL)
   x slot type x value-in-supply (E1 / E2 / E3 / none, the S1 taxonomy's ``supply_class`` over the headroom
   note's ``evidence_class``) x request-structure bins (first-Solver prompt tokens, supplied item count).

It re-implements nothing: loaders and classes come from ``slurp_s1_slu_error_taxonomy`` (arm specs, scores,
gold split), the node ledger (``load_node_states``, ``derive_arm``), the error-source read (``load_outputs``,
``slu_counts``, ``repaired``), the gold-position read (``load_phases``, exemplar pool, contract bodies), the W5
estimate (``printed_pairs``, M1 snapshot) and the headroom read (``pooled_f1``, ``gain_pp``, ``Rescorer``,
``evidence_class``).  New here: the first-Solver trace pass (prompt tokens, supplied counts, finish reason, raw
parse) and the aggregations.

Gold discipline: gold enters only offline through the governed SLURP loader (TRAIN via ``ES.load_gold``, DEV via
``data.slurp.load_slurp_split`` on ``devel``); the test split is never read.  Text discipline: no utterance
text, transcript, gold value, filler, card body or model output is printed or persisted -- only ids, counts,
rates, pp, slot TYPE names, class names and hashes.  Zero model, server, tokenizer, encoder, embedder,
scorer-subprocess, network and GPU contacts (prompt tokens are the server's own sealed ``usage`` counts).

Deterministic apart from ``generated_at``.  ``--check`` re-derives and compares.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_exchange_rates.py \\
        --data-root "$SPEECHRL_DATA_DIR" \\
        --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

READ_ID = "SAEA-SLURP-NX-EXCHANGE-RATES-V1"
RECIPE = "slurp-nx-exchange-rates-offline-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")

POOLS = ("comp1b_fold_a", "a2")
ENTITY_CLASSES = ("SPURIOUS", "MISSING", "WRONG-TYPE", "BOUNDARY", "NEAR", "WRONG-VALUE", "FORMAT")
ROW_CLASSES = ("EMPTY-GOLD-FILL", "PARSE-FAIL")
SUPPLY = ("E1", "E2", "E3", "none")
NODES = ("s1", "d")
UNITS = (1, 10)
TOP_TYPES = 15
SOLVER_MAX_TOKENS = 512


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


def pct(num, den) -> float | None:
    return round(100.0 * num / den, 2) if den else None


# ---------------------------------------------------------------------------
# pure parts


def quartile_bins(values: list) -> list:
    """Three cut points (25/50/75 %, inclusive method) -> four labelled bins; deterministic per pool."""
    qs = statistics.quantiles(sorted(values), n=4, method="inclusive")
    return [round(q, 2) for q in qs]


def bin_label(value: float, cuts: list) -> str:
    if value <= cuts[0]:
        return f"Q1 <= {cuts[0]:g}"
    if value <= cuts[1]:
        return f"Q2 <= {cuts[1]:g}"
    if value <= cuts[2]:
        return f"Q3 <= {cuts[2]:g}"
    return f"Q4 > {cuts[2]:g}"


def supply_of(value_fold: str, typ: str, printed: set, card_hit: bool) -> str:
    """E1 exemplars print (type, value); E2 value under another type; E3 a delivered card names it; none."""
    if (typ, value_fold) in printed:
        return "E1"
    if any(v == value_fold for _, v in printed):
        return "E2"
    if card_hit:
        return "E3"
    return "none"


def conditional(rows: list, cond, outcome) -> dict:
    sub = [r for r in rows if cond(r)]
    hit = sum(1 for r in sub if outcome(r))
    return {"n": len(sub), "k": hit, "pct": pct(hit, len(sub))}


# ---------------------------------------------------------------------------
# trace pass: the first Solver contact of every row


def first_solver_contacts(path: Path, ids: set) -> dict:
    """sample_id -> structural fields of the first Solver request/response (ids, counts, hashes only).
    The raw response text is held in memory for parsing and discarded."""
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    first, out, sid_of = {}, {}, {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            head = line[:120]
            if '"MODEL_REQUEST"' in head:
                rec = json.loads(line)
                payload = (rec.get("payload") or {}).get("payload") or {}
                rid = rec["record_id"].split("/")[0]
                role = str(payload.get("key_representation_id") or "").rsplit(":", 1)[-1]
                sid = payload.get("sample_id")
                if role != "solver" or sid not in ids or sid in first:
                    continue
                first[sid] = rid
                sid_of[rid] = sid
                supplied = [str(e.get("evidence_id")) for e in payload.get("supplied_evidence") or ()]
                dp = payload.get("decoding_params") or {}
                out[sid] = {
                    "request_id": rid,
                    "supplied_items": len(supplied),
                    "supplied_exemplars": sum(1 for e in supplied if e.startswith("train-exemplars::")),
                    "supplied_cards": sum(1 for e in supplied if e.startswith("slot-contracts::")),
                    "supplied_boundaries": sum(1 for e in supplied if e.startswith("intent-boundaries::")),
                    "history_entries": len(payload.get("history") or ()),
                    "tool_schemas": len(payload.get("tool_schemas") or ()),
                    "response_format": (dp.get("response_format") or {}).get("type") if isinstance(
                        dp.get("response_format"), dict) else dp.get("response_format"),
                    "tool_choice": dp.get("tool_choice"), "max_tokens": dp.get("max_tokens"),
                }
            elif '"MODEL_RESPONSE"' in head or '"MODEL_WIRE_RESPONSE"' in head:
                rec = json.loads(line)
                rid = rec["record_id"].split("/")[0]
                target = sid_of.get(rid)
                if target is None:
                    continue
                payload = rec.get("payload") or {}
                if rec["channel"] == "MODEL_RESPONSE":
                    text = payload.get("text") or ""
                    usage = payload.get("usage") or {}
                    scenario, action, entities, parsed = parse_slu_response(text)
                    stripped = text.lstrip()
                    out[target].update({
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "raw_parsed": bool(parsed),
                        "raw_intent": f"{scenario}_{action}" if parsed and scenario and action else None,
                        "raw_entities": tuple((e.type, e.filler) for e in entities),
                        "raw_tool_call_tag": "<tool_call>" in text,
                        "raw_fenced": "```" in text,
                        "raw_leading": stripped[:1] if stripped[:1] in "{[`<" else ("alpha" if stripped[:1].isalpha()
                                                                                       else "other"),
                    })
                    del text
                else:
                    out[target]["finish_reason"] = payload.get("finish_reason")
    return out


# ---------------------------------------------------------------------------
# per pool


def derive_pool(spec: dict, data_root: Path, gold: dict, pool: dict, m1_values: dict, cards: dict,
                NG, HR, S1, W5) -> dict:
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items, fold

    ES, GP = NG.ES, NG.GP
    phases = GP.load_phases(data_root, spec)
    directory = phases["directory"]
    outputs = ES.load_outputs(directory, spec["run_id"])
    scores = S1.load_scores(directory, spec["run_id"], spec["scorer"])
    nodes = NG.load_node_states(data_root, spec)
    ids = sorted(scores["rows"])
    if len(ids) != spec["rows"] or sorted(outputs["rows"]) != ids or sorted(phases["rows"]) != ids:
        raise ReadError(f"{spec['label']}: roster disagrees across scores / outputs / phases")
    if any(s not in gold for s in ids):
        raise ReadError(f"{spec['label']}: roster ids absent from the {spec['split']} gold")
    trace_path = directory / f"{spec['run_id']}.trace.jsonl"
    contacts = first_solver_contacts(trace_path, set(ids))
    no_solver = [s for s in ids if s not in contacts or "raw_parsed" not in contacts[s]]

    gold_e = {s: gold[s]["entities"] for s in ids}
    pred_d = {s: outputs["rows"][s]["entities"] for s in ids}
    rescorer = HR.Rescorer(gold_e, pred_d, ES.slu_counts, ids)
    if any(abs(a - b) > 1e-6 for a, b in zip(rescorer.base, scores["totals"])):
        raise ReadError(f"{spec['label']}: in-process totals do not reproduce the sealed official totals")
    T = scores["totals"]
    base_f1 = HR.pooled_f1(T)

    arm = {"label": spec["label"], "phases": phases["rows"], "outputs": outputs["rows"], "scores": scores["rows"],
           "nodes": nodes["rows"]}
    derived = NG.derive_arm(arm, gold, ids, pool, m1_values)
    drow = derived["rows"]
    m1_by_key = {vid.split("value:", 1)[-1]: v for vid, v in m1_values.items()}

    checks = Counter()
    rows = []
    for s in ids:
        c = contacts.get(s, {})
        s1_state = nodes["rows"][s]["solvers"][0] if nodes["rows"][s]["solvers"] else None
        raw_parsed = c.get("raw_parsed", False)
        raw_ents = tuple(ES.SlotEntity(t, f) for t, f in c.get("raw_entities", ()))
        if s1_state is not None and "raw_parsed" in c:
            checks["first_solver_state_parse_equals_raw_response_parse"] += int(s1_state["parsed"] == raw_parsed)
            checks["first_solver_state_entities_equal_raw_response_entities"] += int(
                tuple(s1_state["entities"]) == raw_ents)
            checks["rows_with_first_solver"] += 1
        printed = set()
        for key in phases["rows"][s]["ex_rendered"]:
            value = m1_by_key.get(key)
            if value is not None:
                printed |= W5.printed_pairs(value.content)
        card_ids = phases["rows"][s]["contracts"]

        def card_hit(value_fold: str) -> bool:
            if len(value_fold) < 3:
                return False
            pattern = re.compile(r"(?<![a-z0-9])" + re.escape(value_fold) + r"(?![a-z0-9])")
            return any(pattern.search(cards["bodies"].get(cid, "")) for cid in card_ids)

        node_items = {}
        for node, ents, parsed in (("s1", raw_ents, raw_parsed), ("d", pred_d[s], outputs["rows"][s]["parsed"])):
            # an unparsed answer scores as no entities (official scorer, S1 taxonomy): its gold items are MISSING
            its = entity_items(gold_e[s], ents if parsed else ())
            for it in its:
                if it["gold_index"] is None:
                    e = ents[it["pred_index"]]
                    it["supply"] = supply_of(fold(e.filler), e.type, printed, card_hit(fold(e.filler)))
                else:
                    g = gold_e[s][it["gold_index"]]
                    it["supply"] = supply_of(fold(g.filler), g.type, printed, card_hit(fold(g.filler)))
            node_items[node] = {"parsed": parsed, "items": its, "n_pred": len(ents)}
        rows.append({
            "sample_id": s, "gold_empty": not gold_e[s], "gold_n": len(gold_e[s]),
            "gold_types": [g.type for g in gold_e[s]],
            "s1_parsed": raw_parsed, "d_parsed": outputs["rows"][s]["parsed"],
            # exact set as the official scorer sees it: an unparsed answer is scored as no entities
            "s1_exact": not node_items["s1"]["items"],
            "d_exact": not node_items["d"]["items"],
            "s1_fill": raw_parsed and node_items["s1"]["n_pred"] > 0,
            "d_fill": outputs["rows"][s]["parsed"] and node_items["d"]["n_pred"] > 0,
            "items": node_items,
            "prompt_tokens": c.get("prompt_tokens"), "supplied_items": c.get("supplied_items"),
            "contact": {k: c.get(k) for k in ("supplied_exemplars", "supplied_cards", "supplied_boundaries",
                                              "history_entries", "tool_schemas", "response_format", "tool_choice",
                                              "max_tokens", "completion_tokens", "finish_reason",
                                              "raw_tool_call_tag", "raw_fenced", "raw_leading")},
            "perc_rank": drow[s]["perc_rank"], "s1_ok": drow[s]["s1_ok"], "d_ok": drow[s]["d_ok"],
            "d_intent_parsed": drow[s]["d_parsed"],
        })
    n = len(rows)

    # ---- 1. node metrics -------------------------------------------------
    def node_metrics(node: str) -> dict:
        parsed = sum(r[f"{node}_parsed"] for r in rows)
        empty = [r for r in rows if r["gold_empty"]]
        nonempty = [r for r in rows if not r["gold_empty"]]
        cls = Counter(it["kind"] for r in rows for it in r["items"][node]["items"])
        return {"parse_valid": parsed, "parse_valid_pct": pct(parsed, n),
                "entity_exact_set_rows": sum(r[f"{node}_exact"] for r in rows),
                "entity_exact_set_pct": pct(sum(r[f"{node}_exact"] for r in rows), n),
                "empty_gold_rows": len(empty),
                "empty_gold_false_fill": sum(r[f"{node}_fill"] for r in empty),
                # an unparsed answer delivers no entities, i.e. a correct empty on an empty-gold row (S1 convention)
                "empty_gold_correct_empty": sum(not r[f"{node}_fill"] for r in empty),
                "nonempty_gold_rows": len(nonempty),
                "nonempty_exact": sum(r[f"{node}_exact"] for r in nonempty),
                "gold_items": sum(r["gold_n"] for r in rows),
                "gold_items_exact": sum(r["gold_n"] for r in rows)
                - sum(1 for r in rows for it in r["items"][node]["items"] if it["gold_index"] is not None),
                "classes": {k: cls.get(k, 0) for k in ENTITY_CLASSES}}

    nodes_out = {node: node_metrics(node) for node in NODES}

    # per slot type (gold items exact at each node, spurious predicted under the type)
    gold_by_type = Counter(t for r in rows for t in r["gold_types"])
    by_type = []
    for t, g in sorted(gold_by_type.items(), key=lambda kv: (-kv[1], kv[0])):
        entry = {"type": t, "gold_items": g}
        for node in NODES:
            wrong = sum(1 for r in rows for it in r["items"][node]["items"]
                        if it["gold_index"] is not None and it["type"] == t)
            entry[f"{node}_exact"] = g - wrong
            entry[f"{node}_exact_pct"] = pct(g - wrong, g)
            entry[f"{node}_spurious"] = sum(1 for r in rows for it in r["items"][node]["items"]
                                            if it["kind"] == "SPURIOUS" and it["type"] == t)
        by_type.append(entry)
    spur_only_types = Counter(it["type"] for r in rows for it in r["items"]["d"]["items"]
                              if it["kind"] == "SPURIOUS" and it["type"] not in gold_by_type)

    # node -> delivered transfer
    transfer = {
        "d_exact_given_s1_exact": conditional(rows, lambda r: r["s1_exact"], lambda r: r["d_exact"]),
        "d_exact_given_s1_parsed_not_exact": conditional(rows, lambda r: r["s1_parsed"] and not r["s1_exact"],
                                                         lambda r: r["d_exact"]),
        "d_exact_given_s1_unparsed": conditional(rows, lambda r: not r["s1_parsed"], lambda r: r["d_exact"]),
        "d_parsed_given_s1_unparsed": conditional(rows, lambda r: not r["s1_parsed"], lambda r: r["d_parsed"]),
        "d_fill_given_s1_fill_empty_gold": conditional(rows, lambda r: r["gold_empty"] and r["s1_fill"],
                                                       lambda r: r["d_fill"]),
        "d_fill_given_s1_no_fill_empty_gold": conditional(rows, lambda r: r["gold_empty"] and r["s1_parsed"]
                                                          and not r["s1_fill"], lambda r: r["d_fill"]),
    }

    # ---- official exchange rates -------------------------------------------
    analytic = {}
    for u in UNITS:
        analytic[f"remove_{u}_spurious_entity_pp"] = round(HR.gain_pp(T, fp_removed=u), 4)
        analytic[f"recover_{u}_missing_entity_pp"] = round(HR.gain_pp(T, fn_recovered=u), 4)
        analytic[f"repair_{u}_wrong_entity_pp"] = round(HR.gain_pp(T, fp_removed=u, fn_recovered=u), 4)

    def mean_gain(edits: list) -> dict:
        gains = [rescorer.gain(e) for e in edits]
        if not gains:
            return {"n": 0}
        return {"n": len(gains), "mean_pp": round(statistics.fmean(gains), 4),
                "median_pp": round(statistics.median(gains), 4),
                "x10_linear_pp": round(10 * statistics.fmean(gains), 4),
                "all_at_once_pp": round(rescorer.gain({k: v for e in edits for k, v in e.items()}), 4)
                if all(len(e) == 1 for e in edits) and len({k for e in edits for k in e}) == len(edits) else None}

    d_wrong_rows = [r for r in rows if not r["d_exact"]]
    exact_row_edits = {
        "any_non_exact_row": [{r["sample_id"]: list(gold_e[r["sample_id"]])} for r in d_wrong_rows],
        "non_empty_gold_row": [{r["sample_id"]: list(gold_e[r["sample_id"]])} for r in d_wrong_rows
                               if not r["gold_empty"]],
        "empty_gold_false_fill_row": [{r["sample_id"]: []} for r in d_wrong_rows if r["gold_empty"]],
        "s1_parsed_not_exact_row": [{r["sample_id"]: list(gold_e[r["sample_id"]])} for r in d_wrong_rows
                                    if r["s1_parsed"] and not r["s1_exact"]],
    }
    empirical = {f"one_extra_exact_row.{k}": mean_gain(v) for k, v in exact_row_edits.items()}
    spur_edits, miss_edits = [], []
    for r in rows:
        s = r["sample_id"]
        for it in r["items"]["d"]["items"]:
            if it["kind"] == "SPURIOUS":
                spur_edits.append({s: ES.repaired(gold_e[s], pred_d[s], [it])})
            elif it["kind"] == "MISSING":
                miss_edits.append({s: ES.repaired(gold_e[s], pred_d[s], [it])})
    empirical["remove_one_spurious_entity"] = mean_gain(spur_edits)
    empirical["recover_one_missing_entity"] = mean_gain(miss_edits)
    for k in ("remove_one_spurious_entity", "recover_one_missing_entity"):
        empirical[k]["all_at_once_pp"] = None  # rows can carry several items; the per-item mean is the rate
    false_fill_rows = [r for r in rows if r["gold_empty"] and r["d_fill"]]
    empirical["empty_gold_false_fill.spurious_entities_per_row"] = round(
        statistics.fmean(r["items"]["d"]["n_pred"] for r in false_fill_rows), 4) if false_fill_rows else None

    # node-unit -> official: one more raw-exact Solver row buys the transfer gap times the row value
    gap = (transfer["d_exact_given_s1_exact"]["pct"] - transfer["d_exact_given_s1_parsed_not_exact"]["pct"]) / 100.0
    row_val = empirical["one_extra_exact_row.s1_parsed_not_exact_row"].get("mean_pp", 0.0)
    node_rates = {
        "per_raw_exact_row_pp": round(gap * row_val, 4),
        "per_raw_exact_row_x10_pp": round(10 * gap * row_val, 4),
        "transfer_gap_d_exact": round(gap, 4),
        "row_value_pp_s1_parsed_not_exact": row_val,
        "per_delivered_exact_row_pp": empirical["one_extra_exact_row.any_non_exact_row"].get("mean_pp"),
        "per_false_fill_removed_row_pp": empirical["one_extra_exact_row.empty_gold_false_fill_row"].get("mean_pp"),
        "note": "per_raw_exact_row assumes the raw-exact -> delivered-exact transfer measured on this pool "
                "holds for the newly exact rows; it is an expectation, not a measurement",
    }

    # ---- 2. intent ---------------------------------------------------------
    wrong = [r for r in rows if not r["d_ok"]]
    split = Counter()
    for r in wrong:
        if not r["d_intent_parsed"]:
            split["delivered_unparsed"] += 1
        elif r["perc_rank"] is None:
            split["gold_not_on_perception_shortlist"] += 1
        elif r["perc_rank"] > 1:
            split["gold_on_shortlist_not_rank_1"] += 1
        else:
            split["gold_rank_1_solver_chose_otherwise"] += 1
    rank_conv = {}
    for label, cond in (("rank_1", lambda r: r["perc_rank"] == 1), ("rank_2", lambda r: r["perc_rank"] == 2),
                        ("rank_3_plus", lambda r: r["perc_rank"] is not None and r["perc_rank"] >= 3),
                        ("off_list", lambda r: r["perc_rank"] is None)):
        rank_conv[label] = conditional(rows, cond, lambda r: r["d_ok"])
    not1 = conditional(rows, lambda r: r["perc_rank"] != 1, lambda r: r["d_ok"])
    intent = {
        "rows": n, "delivered_correct": sum(r["d_ok"] for r in rows),
        "delivered_accuracy_pct": pct(sum(r["d_ok"] for r in rows), n),
        "solver_first_correct": sum(r["s1_ok"] for r in rows),
        "pp_per_converted_row": round(100.0 / n, 4), "pp_per_10_converted_rows": round(1000.0 / n, 4),
        "delivered_wrong_rows": len(wrong), "delivered_wrong_split": {k: split.get(k, 0) for k in (
            "delivered_unparsed", "gold_not_on_perception_shortlist", "gold_on_shortlist_not_rank_1",
            "gold_rank_1_solver_chose_otherwise")},
        "delivered_correct_by_perception_rank": rank_conv,
        "delivered_correct_given_not_rank_1": not1,
        "pp_per_perception_rank_1_gain": round((rank_conv["rank_1"]["pct"] - not1["pct"]) / n, 4)
        if not1["n"] else None,
    }

    # ---- 3. contrast table -------------------------------------------------
    pts = [r["prompt_tokens"] for r in rows if r["prompt_tokens"] is not None]
    sup = [r["supplied_items"] for r in rows if r["supplied_items"] is not None]
    pt_cuts, sup_cuts = quartile_bins(pts), quartile_bins(sup)
    for r in rows:
        r["pt_bin"] = bin_label(r["prompt_tokens"], pt_cuts) if r["prompt_tokens"] is not None else "n/a"
        r["sup_bin"] = bin_label(r["supplied_items"], sup_cuts) if r["supplied_items"] is not None else "n/a"
    contrast = {}
    for node in NODES:
        cube = Counter()
        for r in rows:
            for it in r["items"][node]["items"]:
                cube[(it["kind"], it["type"], it["supply"], r["pt_bin"], r["sup_bin"])] += 1
            if r["gold_empty"] and r[f"{node}_fill"]:
                cube[("EMPTY-GOLD-FILL", "-", "-", r["pt_bin"], r["sup_bin"])] += 1
            if not r[f"{node}_parsed"]:
                cube[("PARSE-FAIL", "-", "-", r["pt_bin"], r["sup_bin"])] += 1
        marg = defaultdict(Counter)
        for (k, t, e, pb, sb), v in cube.items():
            marg["class"][k] += v
            marg["class_x_supply"][f"{k}|{e}"] += v
            marg["class_x_prompt_bin"][f"{k}|{pb}"] += v
            marg["class_x_supplied_bin"][f"{k}|{sb}"] += v
            marg["class_x_type"][f"{k}|{t}"] += v
        rows_per_bin = {"prompt_bin": dict(sorted(Counter(r["pt_bin"] for r in rows).items())),
                        "supplied_bin": dict(sorted(Counter(r["sup_bin"] for r in rows).items()))}
        contrast[node] = {"cube": sorted([list(k) + [v] for k, v in cube.items()]),
                          "marginals": {k: dict(sorted(v.items())) for k, v in marg.items()},
                          "rows_per_bin": rows_per_bin}
    structure = {
        "prompt_token_cuts": pt_cuts, "supplied_item_cuts": sup_cuts,
        "prompt_tokens_mean": round(statistics.fmean(pts), 1) if pts else None,
        "supplied_items_mean": round(statistics.fmean(sup), 2) if sup else None,
        "first_solver_contact_fields": {
            k: dict(sorted(Counter(str(r["contact"][k]) for r in rows).items()))
            for k in ("history_entries", "tool_schemas", "response_format", "tool_choice", "max_tokens",
                      "finish_reason", "supplied_cards", "supplied_boundaries")},
        "completion_tokens_at_cap": sum(1 for r in rows if (r["contact"]["completion_tokens"] or 0)
                                        >= SOLVER_MAX_TOKENS),
        "raw_unparsed_features": {
            k: dict(sorted(Counter(str(r["contact"][k]) for r in rows if not r["s1_parsed"]).items()))
            for k in ("finish_reason", "raw_tool_call_tag", "raw_fenced", "raw_leading")},
        "rows_without_first_solver_contact": len(no_solver),
    }
    checks.update({f"phase.{k}": v for k, v in phases["checks"].items()})
    return {
        "label": spec["label"], "title": spec["title"], "split": spec["split"], "rows": n,
        "inputs": {"run_id": spec["run_id"], "attempt": spec["attempt"], "scorer": spec["scorer"],
                   "phases": [phases["relpath"], phases["sha256"]],
                   "outputs": [str((directory / outputs["relpath"]).relative_to(data_root)), outputs["sha256"]],
                   "scores": [str((directory / scores["relpath"]).relative_to(data_root)), scores["sha256"]],
                   "trace": [str(trace_path.relative_to(data_root)), digest(trace_path)]},
        "structural_checks": dict(sorted(checks.items())),
        "pooled_totals_word_plus_char": {"tp": round(T[0], 6), "fp": round(T[1], 6), "fn": round(T[2], 6),
                                         "slu_f1": round(base_f1, 4)},
        "nodes": nodes_out, "transfer": transfer, "by_type": by_type,
        "spurious_only_types_delivered": dict(spur_only_types.most_common()),
        "analytic_rates": analytic, "empirical_rates": empirical, "node_rates": node_rates,
        "intent": intent, "contrast": contrast, "request_structure": structure,
    }


# ---------------------------------------------------------------------------


def build(args) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock

    S1 = import_path(REPO_ROOT / "scripts/analysis/slurp_s1_slu_error_taxonomy.py", "slurp_s1_slu_error_taxonomy")
    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    HR = import_path(REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py",
                     "slurp_slu_consumption_headroom")
    ES, GP, W5 = NG.ES, NG.GP, NG.W5
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    m1_values = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    cards = GP.load_contract_bodies(data_root)
    out, gold_cache = {}, {}
    for label in POOLS:
        spec = next(a for a in S1.ARMS if a["label"] == label)
        if spec["split"] not in gold_cache:
            gold_cache[spec["split"]] = S1.load_gold_split(lock, data_root, spec["split"], ES)
        out[label] = derive_pool(spec, data_root, gold_cache[spec["split"]], pool, m1_values, cards,
                                 NG, HR, S1, W5)
    return {
        "read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "splits_read": sorted(gold_cache),
        "inputs": {"exemplar_pool": [pool["relpath"], pool["sha256"]],
                   "slot_contracts": [cards["relpath"], cards["sha256"]],
                   "m1_snapshot_content_hash": [W5.M1_SNAPSHOT["relpath"], W5.M1_SNAPSHOT["sha256"]]},
        "drivers": {name: [str(p.relative_to(REPO_ROOT)), digest(p)] for name, p in (
            ("s1_taxonomy", REPO_ROOT / "scripts/analysis/slurp_s1_slu_error_taxonomy.py"),
            ("node_gain_ledger", REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py"),
            ("consumption_headroom", REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py"),
            ("error_sources", REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py"),
            ("w5_estimate", REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py"))},
        "pools": out,
    }


# ---------------------------------------------------------------------------
# rendering


def md_table(header: list, rows: list) -> str:
    out = ["| " + " | ".join(str(h) for h in header) + " |",
           "| " + " | ".join("---" if i == 0 else "---:" for i in range(len(header))) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render(r: dict) -> str:
    P = r["pools"]
    L = list(P)
    out = [f"# {READ_ID} tables", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers. "
           "Counts, pp, slot type names and class names only.", ""]
    out += ["## Pools", "", md_table(["pool", "split", "rows", "TP", "FP", "FN", "SLU-F1"],
                                     [[p, P[p]["split"], P[p]["rows"]] + [P[p]["pooled_totals_word_plus_char"][k]
                                      for k in ("tp", "fp", "fn", "slu_f1")] for p in L]), ""]
    keys = ["parse_valid", "entity_exact_set_rows", "empty_gold_rows", "empty_gold_false_fill",
            "empty_gold_correct_empty", "nonempty_gold_rows", "nonempty_exact", "gold_items", "gold_items_exact"]
    out += ["## Solver first raw answer (s1) vs delivered (d)", "",
            md_table(["metric"] + [f"{p} {nd}" for p in L for nd in NODES],
                     [[k] + [P[p]["nodes"][nd][k] for p in L for nd in NODES] for k in keys]
                     + [[f"class {c}"] + [P[p]["nodes"][nd]["classes"][c] for p in L for nd in NODES]
                        for c in ENTITY_CLASSES]), ""]
    out += ["## Transfer s1 -> d", "",
            md_table(["conditional"] + L, [[k] + [f"{P[p]['transfer'][k]['k']}/{P[p]['transfer'][k]['n']} "
                                                  f"({P[p]['transfer'][k]['pct']})" for p in L]
                                           for k in P[L[0]]["transfer"]]), ""]
    out += ["## Official exchange rates (pp of pooled SLU-F1)", "",
            md_table(["rate"] + L, [[k] + [P[p]["analytic_rates"][k] for p in L] for k in P[L[0]]["analytic_rates"]]
                     + [[f"empirical {k} mean (n)"] + [f"{P[p]['empirical_rates'][k].get('mean_pp')} "
                                                       f"({P[p]['empirical_rates'][k].get('n')})" for p in L]
                        for k in P[L[0]]["empirical_rates"] if isinstance(P[L[0]]["empirical_rates"][k], dict)]
                     + [[k] + [P[p]["node_rates"][k] for p in L] for k in P[L[0]]["node_rates"] if k != "note"]),
            ""]
    out += ["## Intent", "", md_table(["quantity"] + L, [[k] + [json.dumps(P[p]["intent"][k]) if isinstance(
        P[p]["intent"][k], dict) else P[p]["intent"][k] for p in L] for k in P[L[0]]["intent"]]), ""]
    for p in L:
        out += [f"### Per slot type ({p}; top {TOP_TYPES} by gold items)", "",
                md_table(["type", "gold", "s1 exact", "s1 %", "d exact", "d %", "s1 spurious", "d spurious"],
                         [[t["type"], t["gold_items"], t["s1_exact"], t["s1_exact_pct"], t["d_exact"],
                           t["d_exact_pct"], t["s1_spurious"], t["d_spurious"]] for t in P[p]["by_type"][:TOP_TYPES]]),
                ""]
    for p in L:
        for nd in NODES:
            m = P[p]["contrast"][nd]["marginals"]
            classes = list(ENTITY_CLASSES) + list(ROW_CLASSES)
            out += [f"### Contrast ({p}, node {nd}): class x value-in-supply", "",
                    md_table(["class", "total"] + list(SUPPLY),
                             [[c, m["class"].get(c, 0)] + [m["class_x_supply"].get(f"{c}|{e}", 0) for e in SUPPLY]
                              for c in classes]), ""]
            for dim, key in (("prompt_bin", "class_x_prompt_bin"), ("supplied_bin", "class_x_supplied_bin")):
                bins = list(P[p]["contrast"][nd]["rows_per_bin"][dim])
                out += [f"### Contrast ({p}, node {nd}): class x {dim} (rows per bin in the header)", "",
                        md_table(["class"] + [f"{b} (rows {P[p]['contrast'][nd]['rows_per_bin'][dim][b]})"
                                              for b in bins],
                                 [[c] + [m[key].get(f"{c}|{b}", 0) for b in bins] for c in classes]), ""]
        out += [f"### Request structure ({p})", "", "```json", json.dumps(P[p]["request_structure"], indent=1), "```", ""]
    return "\n".join(out) + "\n"


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
    texts = {"report.json": json.dumps(report, indent=1, sort_keys=True) + "\n", "tables.md": render(report)}
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
