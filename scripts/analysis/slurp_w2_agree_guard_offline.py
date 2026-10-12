#!/usr/bin/env python3
"""Knowledge-wave item W2: an offline test of a position-1 guard on the AGREE agreement vote.

Owner decision 164.  A model-free replay over receipt-pinned vectors, the two
receipt-pinned exemplar-intent agreement tables and the sealed AGREE / A/A
outputs: zero model, server, tokenizer, encoder, embedder, network, GPU and
paid-API contacts, and no official-scorer subprocess.

The AGREE arm ranks the 60 intent-boundary entries by ``cos + 1.0 * vote`` (the
written-key cosine at recall width 60 plus the self-excluded exemplar-intent
vote share) and delivers the first eight.  The error-source read
(``docs/results/2026-09-27-slurp-agree-arm-error-sources.md``) found 21 of its 31
harms are DEMOTIONS -- gold sat at position 1 before the term on 17 of them.  A
guard keeps the pre-agreement position-1 entry ``T`` (the cosine top) at
position 1 in some rows and lets the term reorder everything else.  Three
families, one parameter each, ``C`` the agreement order's top:

* ``cos-margin-pin`` (delta): pin ``T`` when ``cos[T] - cos[second]`` >= delta;
* ``incumbent-bonus`` (h): rank by ``cos + vote + h * [entry == T]``;
* ``vote-lead-pin`` (lead): pin ``T`` unless ``vote[C] - vote[T]`` >= lead.

Pinning puts ``T`` first and keeps the agreement order for the rest, so the
term still promotes entries from positions 2..60 and still delivers new ones.

Tuning discipline.  The family and its parameter are chosen on TRAIN Fold B
only (the filler family's Fold B agreement table and the Fold B intent-boundary
query vectors; Fold B TRAIN gold is allowed for tuning), by a rule fixed in
this file: maximise the model-expected intent change against the unguarded
term, where a row's expected correctness is P(intent correct | gold at block
position p) from the gold-position read's DEV-2000-ADDED column (a roster
disjoint from both folds); ties go to the rule that changes fewer blocks.
Fold A gold is read afterwards, on the scoring side only, to COUNT what the
chosen rule would have done to AGREE's sealed saves and harms.

The Fold A expectation.  Rows whose block the rule changes, valued with the
gold-position read's Fold A PLAN curve for gold entries already delivered
before the term (promotions and demotions), and with that curve scaled by the
measured conversion of a NEWLY delivered entry (cell CONV 32/70, cell KPROBE
24/55, each over the curve's own position-matched prior for the CONV roster)
for rows whose gold the term newly delivered.

Text discipline.  Ids, intent label names, positions, counts, rates and hashes
only; no utterance text, transcript, delivered answer or knowledge body.

    PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python \\
        scripts/analysis/slurp_w2_agree_guard_offline.py \\
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
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_agreement,
    load_sealed_segment_vectors,
)

READ_ID = "SAEA-SLURP-STAGE3-W2-AGREE-GUARD-OFFLINE-V1"
RECIPE = "slurp-w2-agree-guard-offline-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ANALYSIS_DIR = "analysis/" + READ_ID
GOLD_POSITION = REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py"
RANK_DIAGNOSTIC = REPO_ROOT / "scripts/analysis/slurp_intent_retrieval_rank_diagnostic.py"
ERROR_SOURCES_ROWS = "analysis/SAEA-SLURP-STAGE3-AGREE-ERROR-SOURCES-V1/rows.jsonl"

AGREEMENT_DIMENSION = "agreement:exemplar-intent"
FOLDS = {
    "B": {"query": ("vectors/slurp-intent-boundaries-train-fold-b-1080-v1/query-vectors-speech-segments.jsonl",
                    "83c5da6190fb2a65edf98a8f9ef35ff2cb310eb4e4b94eba9e04f9eedce9f299"),
          "agreement": ("prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1/agreement.jsonl",
                        "06990a86d20469c668ac4231990b49e5926d4771c9af8fbb13ae634b3ec21911")},
    "A": {"query": ("vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl",
                    "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b"),
          "agreement": ("prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl",
                        "018ca6ef0d10bbf8d19645994420820faf7f31961cf91a6080116e4b434016c1")},
}
W_AGREE = 1.0
DELIVERED = 8
ARMS = (
    {"label": "aa", "run_id": "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-agree-aa-fold-a-generation-v1"},
    {"label": "agree", "run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"},
)
SCORER = "slurp-slu-official-train"

# P(intent correct | gold at block position p), read SAEA-SLURP-MF-GOLD-POSITION-SOLVER-FREEDOM-V1
# (docs/results/2026-09-26-slurp-gold-position-and-solver-freedom-read.md, table B.1; "none" = the
# rows whose gold was not among the eight, from the same read's section A counts).
CURVE_DEV = {1: (553, 564), 2: (77, 94), 3: (38, 51), 4: (17, 31), 5: (13, 21), 6: (17, 22),
             7: (8, 15), 8: (7, 17), None: (36, 1000 - 815)}
CURVE_FOLD_A = {1: (699, 708), 2: (88, 119), 3: (24, 39), 4: (19, 30), 5: (5, 13), 6: (10, 17),
                7: (7, 10), 8: (8, 11), None: (28, 1080 - 947)}
# The 70 CONV rows' entry positions under the term (same read, table B.3, train-fold-a-plan).
CONV_ENTRY_POSITIONS = (24, 18, 12, 6, 1, 4, 3, 2)
CONV = (32, 70)     # analysis/SAEA-SLURP-STAGE3-CONV-FOLD-A-70-CONDITIONAL-RATE-V1
KPROBE = (24, 55)   # analysis/SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-CONDITIONAL-RATE-V1

GRIDS = {
    "cos-margin-pin": (0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15),
    "incumbent-bonus": (0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0),
    # midpoints of the 1/20 and 1/19 vote-share lattices, so no lead sits on a float edge
    "vote-lead-pin": (0.075, 0.125, 0.175, 0.225, 0.275, 0.325, 0.375, 0.45, 0.55, 0.65, 0.8, 1.5),
}


class ReadError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GP = import_path(GOLD_POSITION, "slurp_gold_position_and_solver_freedom_read")
RD = import_path(RANK_DIAGNOSTIC, "slurp_intent_retrieval_rank_diagnostic")
digest = GP.digest


def rate(cell) -> float:
    return cell[0] / cell[1]


def curve(table: dict) -> dict:
    return {p: rate(c) for p, c in table.items()}


def conversion_scale(conversion) -> float:
    fa = curve(CURVE_FOLD_A)
    matched = sum(n * fa[p + 1] for p, n in enumerate(CONV_ENTRY_POSITIONS)) / sum(CONV_ENTRY_POSITIONS)
    return rate(conversion) / matched, matched


def order(scores: dict) -> list:
    return [i for i, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def position(ordering: list, intent: str):
    block = ordering[:DELIVERED]
    return block.index(intent) + 1 if intent in block else None


# ---------------------------------------------------------------------------
# replay


def load_fold(data_root: Path, fold: str, store: dict) -> dict:
    spec = FOLDS[fold]
    queries = load_sealed_segment_vectors(data_root / spec["query"][0], expected_sha256=spec["query"][1],
                                          dimensions=(RD.IB_DIM,))
    agreement = load_sealed_agreement(data_root / spec["agreement"][0], expected_sha256=spec["agreement"][1],
                                      dimension=AGREEMENT_DIMENSION)
    ids = sorted(agreement)
    cosines = RD.recompute(store, queries, ids)
    rows, skipped = {}, []
    for sid in ids:
        cos = cosines.get(sid) or {}
        if not cos:
            skipped.append(sid)
            continue
        vote = {k.split("intent-boundary:", 1)[-1]: float(v) for k, v in agreement[sid].items()}
        pre = order(cos)
        agree = order({i: cos[i] + W_AGREE * vote.get(i, 0.0) for i in cos})
        rows[sid] = {"cos": cos, "vote": vote, "pre": pre, "agree": agree}
    return {"rows": rows, "skipped_no_query_vector": len(skipped), "agreement_rows": len(ids),
            "single_candidate_rows": sum(len(r["pre"]) < 2 for r in rows.values())}


def pin(row: dict) -> list:
    top = row["pre"][0]
    return [top] + [i for i in row["agree"] if i != top]


def guarded(row: dict, family: str, value: float) -> list:
    top, challenger = row["pre"][0], row["agree"][0]
    if top == challenger:
        return row["agree"]
    if family == "cos-margin-pin":
        second = row["cos"][row["pre"][1]] if len(row["pre"]) > 1 else 0.0
        return pin(row) if row["cos"][top] - second >= value else row["agree"]
    if family == "vote-lead-pin":
        lead = row["vote"].get(challenger, 0.0) - row["vote"].get(top, 0.0)
        return row["agree"] if lead >= value else pin(row)
    if family == "incumbent-bonus":
        cos, vote = row["cos"], row["vote"]
        return order({i: cos[i] + W_AGREE * vote.get(i, 0.0) + (value if i == top else 0.0) for i in cos})
    raise ReadError(family)


def model_delta(rows: dict, gold: dict, family: str, value: float, values: dict, newly_scale: float = 1.0):
    delta, changed, moves = 0.0, 0, Counter()
    for sid, row in rows.items():
        g = gold[sid]
        new = guarded(row, family, value)
        if new[:DELIVERED] == row["agree"][:DELIVERED]:
            continue
        changed += 1
        pa, pg = position(row["agree"], g), position(new, g)
        d = values[pg] - values[pa]
        if position(row["pre"], g) is None:
            d *= newly_scale
        delta += d
        if pa != pg:
            moves["gold_to_1" if pg == 1 else "gold_off_1" if pa == 1 else "gold_moves_below_1"] += 1
    return delta, changed, dict(sorted(moves.items()))


# ---------------------------------------------------------------------------
# Fold B: tuning


def tune(fold_b: dict, gold_b: dict) -> dict:
    values = curve(CURVE_DEV)
    rows = fold_b["rows"]
    curves, best = {}, None
    for family, grid in GRIDS.items():
        points = []
        for value in grid:
            delta, changed, moves = model_delta(rows, gold_b, family, value, values)
            points.append({"value": value, "delta_rows": round(delta, 4),
                           "delta_pp": round(100 * delta / len(rows), 4), "blocks_changed": changed,
                           "gold_moves": moves})
            key = (round(delta, 9), -changed)
            if best is None or key > best[0]:
                best = (key, family, value)
        curves[family] = points
    overturn = [s for s, r in rows.items() if r["agree"][0] != r["pre"][0]]
    return {"rows": len(rows), "curves": curves, "chosen": {"family": best[1], "value": best[2]},
            "unguarded_vs_pre_model_pp": round(100 * sum(values[position(r["agree"], gold_b[s])]
                                                         - values[position(r["pre"], gold_b[s])]
                                                         for s, r in rows.items()) / len(rows), 4),
            "overturn": overturn_table(rows, gold_b, overturn)}


def lead_bin(x: float) -> str:
    for hi, name in ((0.075, "<=1 vote"), (0.125, "2 votes"), (0.225, "3-4 votes"), (0.325, "5-6 votes")):
        if x < hi:
            return name
    return ">=7 votes"


def margin_bin(x: float) -> str:
    for hi, name in ((0.01, "<0.01"), (0.03, "0.01-0.03"), (0.06, "0.03-0.06")):
        if x < hi:
            return name
    return ">=0.06"


def signature(row: dict) -> tuple:
    top, ch = row["pre"][0], row["agree"][0]
    second = row["cos"][row["pre"][1]] if len(row["pre"]) > 1 else 0.0
    return (lead_bin(row["vote"].get(ch, 0.0) - row["vote"].get(top, 0.0)), margin_bin(row["cos"][top] - second))


def overturn_table(rows: dict, gold: dict, overturn: list) -> dict:
    """Where the term changes the top: whose entry is gold, by the exemplar vote's lead (in shares,
    binned on the vote lattice) and by the pre-agreement cosine margin."""

    table = {"lead": Counter(), "margin": Counter()}
    for sid in overturn:
        r = rows[sid]
        top, ch, g = r["pre"][0], r["agree"][0], gold[sid]
        who = "incumbent" if g == top else "challenger" if g == ch else "neither"
        lead, margin = signature(r)
        table["lead"][(lead, who)] += 1
        table["margin"][(margin, who)] += 1
    out = {"rows": len(overturn), "gold_is": dict(Counter(
        "incumbent" if gold[s] == rows[s]["pre"][0] else "challenger" if gold[s] == rows[s]["agree"][0]
        else "neither" for s in overturn))}
    for key, counter in table.items():
        out[key] = {f"{a}|{b}": n for (a, b), n in sorted(counter.items())}
    return out


# ---------------------------------------------------------------------------
# Fold A: counting


def load_scores(data_root: Path, arm: dict) -> dict:
    path = data_root / "runs" / arm["run_id"] / arm["attempt"] / f"{arm['run_id']}.scores.json"
    block = json.loads(path.read_text(encoding="utf-8"))[SCORER]
    return {"rows": {str(s["sample_id"]): bool(s["scenario_action_exact"]) for s in block["per_sample"]},
            "relpath": str(path.relative_to(data_root)), "sha256": digest(path)}


def evaluate_fold_a(fold_a: dict, gold_a: dict, arms: dict, transitions: dict) -> dict:
    rows = fold_a["rows"]
    values = curve(CURVE_FOLD_A)
    k_conv, matched = conversion_scale(CONV)
    k_kprobe, _ = conversion_scale(KPROBE)
    aa, ag = arms["aa"]["scores"]["rows"], arms["agree"]["scores"]["rows"]
    harms = sorted(s for s in rows if aa[s] and not ag[s])
    saves = sorted(s for s in rows if ag[s] and not aa[s])
    demotions = [s for s in harms if transitions[s] == "demoted"]
    delivery_saves = {t: [s for s in saves if transitions[s] == t] for t in ("newly-delivered", "promoted")}

    def point(family, value):
        worse = lambda s, new: (position(new, gold_a[s]) or 99) > (position(rows[s]["agree"], gold_a[s]) or 99)  # noqa: E731
        better = lambda s, new: (position(new, gold_a[s]) or 99) < (position(rows[s]["agree"], gold_a[s]) or 99)  # noqa: E731
        new = {s: guarded(rows[s], family, value) for s in rows}
        prevented = [s for s in demotions if position(new[s], gold_a[s]) == position(rows[s]["pre"], gold_a[s])]
        forfeited = {t: [s for s in lst if worse(s, new[s])] for t, lst in delivery_saves.items()}
        other_saves = [s for s in saves if s not in delivery_saves["newly-delivered"] + delivery_saves["promoted"]
                       and worse(s, new[s])]
        other_harms = [s for s in harms if s not in demotions and better(s, new[s])]
        n_forfeit = len(forfeited["newly-delivered"]) + len(forfeited["promoted"]) + len(other_saves)
        n_prevent = len(prevented) + len(other_harms)
        exp = {name: model_delta(rows, gold_a, family, value, values, k)[0]
               for name, k in (("position_only", 1.0), ("conv", k_conv), ("kprobe", k_kprobe))}
        changed = sum(new[s][:DELIVERED] != rows[s]["agree"][:DELIVERED] for s in rows)
        return {"value": value, "blocks_changed": changed,
                "demotion_harms_prevented": len(prevented),
                "prevented_gold_moves": dict(Counter(
                    f"{position(rows[s]['agree'], gold_a[s])}->{position(new[s], gold_a[s])}" for s in prevented)),
                "other_harms_helped": len(other_harms),
                "newly_delivered_saves_forfeited": len(forfeited["newly-delivered"]),
                "promoted_saves_forfeited": len(forfeited["promoted"]),
                "other_saves_hit": len(other_saves),
                "forfeited_gold_moves": dict(Counter(
                    f"{position(rows[s]['agree'], gold_a[s])}->{position(new[s], gold_a[s])}"
                    for lst in forfeited.values() for s in lst)),
                "prevents_more_than_it_forfeits": n_prevent > n_forfeit,
                "expected_rows": {k: round(v, 4) for k, v in exp.items()},
                "expected_pp": {k: round(100 * v / len(rows), 4) for k, v in exp.items()}}

    curves = {family: [point(family, v) for v in grid] for family, grid in GRIDS.items()}
    overturn = [s for s, r in rows.items() if r["agree"][0] != r["pre"][0]]
    # the flip rows a position-1 guard can touch at all: harms whose gold was the cosine top and the
    # term's top was the wrong entry, against saves whose gold IS the term's new top over a wrong incumbent
    harm_rows = [s for s in demotions if rows[s]["pre"][0] == gold_a[s] and rows[s]["agree"][0] != gold_a[s]]
    save_rows = [s for s in delivery_saves["newly-delivered"] + delivery_saves["promoted"]
                 if rows[s]["agree"][0] == gold_a[s] and rows[s]["pre"][0] != gold_a[s]]
    signatures = {name: {"rows": len(lst),
                         "lead": dict(sorted(Counter(signature(rows[s])[0] for s in lst).items())),
                         "margin": dict(sorted(Counter(signature(rows[s])[1] for s in lst).items()))}
                  for name, lst in (("position_1_demotion_harms", harm_rows), ("saves_gold_new_top", save_rows))}
    return {"rows": len(rows), "harms": len(harms), "saves": len(saves), "demotion_harms": len(demotions),
            "demotion_harms_from_position_1": sum(position(rows[s]["pre"], gold_a[s]) == 1 for s in demotions),
            "delivery_saves": {t: len(v) for t, v in delivery_saves.items()},
            "conversion_scales": {"conv": round(k_conv, 6), "kprobe": round(k_kprobe, 6),
                                  "position_matched_prior": round(matched, 6)},
            "curves": curves, "overturn": overturn_table(rows, gold_a, overturn), "flip_signatures": signatures}


def replay_checks(fold_a: dict, data_root: Path) -> dict:
    checks = Counter()
    phases = {arm["label"]: GP.load_phases(data_root, dict(arm, label=arm["label"])) for arm in ARMS}
    for sid, row in fold_a["rows"].items():
        checks["rows"] += 1
        checks["agree_top8_equals_sealed_block"] += int(row["agree"][:DELIVERED] == phases["agree"]["rows"][sid]["boundary"])
        checks["pre_top8_equals_sealed_aa_block"] += int(row["pre"][:DELIVERED] == phases["aa"]["rows"][sid]["boundary"])
    return {"checks": dict(sorted(checks.items())),
            "phases": {k: [v["relpath"], v["sha256"]] for k, v in phases.items()}}


# ---------------------------------------------------------------------------


def build(args) -> dict:
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    store = RD.load_store(data_root)
    fold_b = load_fold(data_root, "B", store)
    fold_a = load_fold(data_root, "A", store)
    records = load_slurp_split(lock, data_root, "train", workers=4)
    gold_all = {r.sample_id: r.intent for r in records}
    gold_b = {s: gold_all[s] for s in fold_b["rows"]}
    tuning = tune(fold_b, gold_b)  # Fold A gold is not in scope of this call
    gold_a = {s: gold_all[s] for s in fold_a["rows"]}
    del gold_all
    arms = {arm["label"]: {"scores": load_scores(data_root, arm)} for arm in ARMS}
    transitions = {}
    with (data_root / ERROR_SOURCES_ROWS).open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if "q1" in record:
                transitions[record["sample_id"]] = record["q1"]["transition"]
    replay = replay_checks(fold_a, data_root)
    evaluation = evaluate_fold_a(fold_a, gold_a, arms, transitions)
    chosen = tuning["chosen"]
    chosen_a = next(p for p in evaluation["curves"][chosen["family"]] if p["value"] == chosen["value"])
    any_point = [(f, p["value"]) for f, pts in evaluation["curves"].items() for p in pts
                 if p["prevents_more_than_it_forfeits"]]
    verdict = ("STOP" if not any_point else "REGISTER-CANDIDATE" if chosen_a["prevents_more_than_it_forfeits"]
               and chosen_a["expected_rows"]["conv"] > 0 else "STOP")
    return {
        "read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "inputs": {
            "intent_boundary_snapshot_file_sha256": store["snapshot_file_sha256"],
            "folds": {f: {"query": list(FOLDS[f]["query"]), "agreement": list(FOLDS[f]["agreement"])} for f in FOLDS},
            "sealed_scores": {k: [v["scores"]["relpath"], v["scores"]["sha256"]] for k, v in arms.items()},
            "sealed_phases": replay["phases"],
            "error_source_rows": [ERROR_SOURCES_ROWS, digest(data_root / ERROR_SOURCES_ROWS)],
            "curves_cited": {"dev2000_added_plan": {str(k): list(v) for k, v in CURVE_DEV.items()},
                             "train_fold_a_plan": {str(k): list(v) for k, v in CURVE_FOLD_A.items()},
                             "conv": list(CONV), "kprobe": list(KPROBE),
                             "conv_entry_positions": list(CONV_ENTRY_POSITIONS)}},
        "fold_b_shape": {k: v for k, v in fold_b.items() if k != "rows"},
        "fold_a_shape": {k: v for k, v in fold_a.items() if k != "rows"},
        "fold_a_replay": replay["checks"],
        "tuning_fold_b": tuning,
        "evaluation_fold_a": evaluation,
        "chosen_on_fold_a": chosen_a,
        "points_that_prevent_more_than_they_forfeit_on_fold_a": [list(p) for p in any_point],
        "verdict": verdict,
    }


def render(report: dict) -> str:
    t, e, c = report["tuning_fold_b"], report["evaluation_fold_a"], report["chosen_on_fold_a"]
    lines = [f"# {READ_ID}", "", f"verdict: **{report['verdict']}**", "",
             f"Fold A replay: {json.dumps(report['fold_a_replay'], sort_keys=True)}",
             f"Fold B shape: {json.dumps(report['fold_b_shape'], sort_keys=True)}", "",
             "## Fold B tuning (model-expected intent change vs the unguarded term, DEV-2000-ADDED curve)", "",
             f"unguarded term vs cosine order, model: {t['unguarded_vs_pre_model_pp']} pp; "
             f"chosen: {t['chosen']['family']} {t['chosen']['value']}", "",
             "| family | value | blocks changed | delta rows | delta pp | gold moves |", "| --- | ---: | ---: | ---: | ---: | --- |"]
    for family, pts in t["curves"].items():
        for p in pts:
            lines.append(f"| {family} | {p['value']} | {p['blocks_changed']} | {p['delta_rows']} | {p['delta_pp']} | "
                         f"{json.dumps(p['gold_moves'], sort_keys=True)} |")
    lines += ["", f"Fold B rows where the term changes the top: {json.dumps(t['overturn'], sort_keys=True)}", "",
              "## Fold A counts (AGREE sealed saves and harms; gold offline for counts only)", "",
              f"harms {e['harms']} (demotions {e['demotion_harms']}, from position 1 {e['demotion_harms_from_position_1']}); "
              f"saves {e['saves']} (delivery {json.dumps(e['delivery_saves'], sort_keys=True)}); "
              f"conversion scales {json.dumps(e['conversion_scales'], sort_keys=True)}", "",
              "| family | value | blocks changed | demotion harms prevented /21 | other harms helped | "
              "new-delivery saves forfeited /32 | promoted saves forfeited /28 | other saves hit | prevents > forfeits | "
              "expected pp (position only / CONV / KPROBE) |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for family, pts in e["curves"].items():
        for p in pts:
            x = p["expected_pp"]
            lines.append(f"| {family} | {p['value']} | {p['blocks_changed']} | {p['demotion_harms_prevented']} | "
                         f"{p['other_harms_helped']} | {p['newly_delivered_saves_forfeited']} | {p['promoted_saves_forfeited']} | "
                         f"{p['other_saves_hit']} | {'yes' if p['prevents_more_than_it_forfeits'] else 'no'} | "
                         f"{x['position_only']} / {x['conv']} / {x['kprobe']} |")
    lines += ["", f"chosen rule on Fold A: {json.dumps(c, sort_keys=True)}", "",
              f"Fold A rows where the term changes the top: {json.dumps(e['overturn'], sort_keys=True)}", "",
              f"Fold A flip signatures: {json.dumps(e['flip_signatures'], sort_keys=True)}", ""]
    return "\n".join(lines)


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"', "", text)


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
        bad = [n for n, text in texts.items() if strip_time((out_dir / n).read_text(encoding="utf-8")) != strip_time(text)]
        print("check:", "IDENTICAL apart from generated_at" if not bad else f"DIFFERS in {bad}")
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    manifest = {n: hashlib.sha256(strip_time(t).encode("utf-8")).hexdigest() for n, t in sorted(texts.items())}
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                                 encoding="utf-8", newline="\n")
    print("wrote", out_dir, "verdict", report["verdict"])
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
