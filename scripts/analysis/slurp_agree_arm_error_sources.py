#!/usr/bin/env python3
"""Row-level attribution of the AGREE arm's gain and harm, and the source of its remaining error.

Owner decision 163, ANALYSIS track.  A model-free read over sealed bytes: zero
model, server, tokenizer, encoder, embedder, network, GPU and paid-API
contacts, and no official-scorer subprocess.  The only scoring arithmetic is
the repository's in-process SLURP port (``reproduction.slurp_scoring.score_slu``),
used for counterfactual entity repairs after it has been shown to reproduce
every sealed per-sample SLU count of the arm it is applied to.

Three questions, all on TRAIN Fold A (1,080 rows):

1.  AGREE's saves and harms against its in-chain A/A, row by row: the gold
    intent-boundary entry's delivery status and position in both arms,
    Perception's shortlist in both arms, whether the delivered intent came from
    the shortlist, and a harm class -- (i) delivery displaced gold, (ii) the
    delivered block is identical (only sampling / batch noise differs), (iii)
    other.  The noise floor is the flip rate between the three sealed flights
    of the SAME plan (A/A, PLAN, PLANr), stratified by the gold entry's
    position, applied to the rows of the AGREE contrast.
2.  The remaining error mass of the AGREE arm: every intent-wrong row in an
    exclusive partition (UNPARSED, CATCH-ALL, RETRIEVAL, CONSUMPTION split into
    Perception drop and Solver choice) with overlays (confusion scope and pair,
    stability across the null flights, gold-intent exemplar count, the
    perception-suspect entity criterion); and the official SLU-F1 gap split by
    entity error kind and slot type, with isolated counterfactual repairs.
3.  Per class: share of the remaining intent points / SLU-F1 gap and a ceiling.

Gold discipline.  Gold is read OFFLINE on the scoring side only, through the
governed TRAIN split and ``data.slurp.load_slurp_split`` (the path the
bad-case bank and the gold-position read use).  No gold value reaches a query,
key, selector, config or runtime; this script writes an analysis report and
nothing else.

Text discipline.  No utterance text, transcript, delivered answer, gold filler,
predicted filler or knowledge body is written or printed.  Fillers are compared
inside this process and leave it only as kinds, counts, slot TYPE names, intent
label names, ids and hashes.

Reproducibility.  Deterministic apart from ``generated_at``: every container is
sorted before it is consumed, there is no resampling, and ``--check`` re-runs
the derivation and compares every output byte except that one field.

    PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python \\
        scripts/analysis/slurp_agree_arm_error_sources.py \\
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
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_segment_vectors,
    load_sealed_vectors,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    SlotEntity,
    _prf,
    parse_slu_response,
    score_slu,
)
from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import (  # noqa: E402
    ENTITY_KINDS,
    NEAR_THRESHOLD,
    canonical,
    contiguous_in,
    entity_items,
    fold,
    norm_distance,
    pair_kind,
)
# ``entity_items``/``canonical``/``norm_distance``/``contiguous_in``/``pair_kind``/``fold``/
# ``ENTITY_KINDS``/``NEAR_THRESHOLD`` are the lifted primitives (design spec 2026-09-29, sealed-credit
# inner loop, task 2): this module keeps importing them under their original names so every call site
# below is unchanged, and ``--check`` reproduces the sealed report byte-for-byte.

READ_ID = "SAEA-SLURP-STAGE3-AGREE-ERROR-SOURCES-V1"
RECIPE = "slurp-agree-arm-error-sources-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ANALYSIS_DIR = "analysis/SAEA-SLURP-STAGE3-AGREE-ERROR-SOURCES-V1"
GOLD_POSITION = REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py"
RANK_DIAGNOSTIC = REPO_ROOT / "scripts/analysis/slurp_intent_retrieval_rank_diagnostic.py"

SCORER = "slurp-slu-official-train"
ROWS = 1080
PP_PER_ROW = 100.0 / ROWS
EX_SNAPSHOT = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
QUERY = "vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl"
QUERY_SHA = "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b"
CENTROID = "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl"
CENTROID_SHA = "16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532"
AGREE_WEIGHT = 1.0
FLOWN_K = 8
CATCH_ALL = ("general_quirky",)
# Measured conversions of a newly delivered gold entry (sealed probe reads, cited, not recomputed):
KPROBE_CONVERSION = (24, 55)   # analysis/SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-CONDITIONAL-RATE-V1
CONV_CONVERSION = (32, 70)     # analysis/SAEA-SLURP-STAGE3-CONV-FOLD-A-70-CONDITIONAL-RATE-V1
# NEAR_THRESHOLD is imported from analysis.sealed_credit.entity_states (0.4, unchanged).
NEAR_SENSITIVITY = (0.2, 0.3, 0.4, 0.5)

ARMS = (
    {"label": "aa", "title": "in-chain A/A (w_agree 0.0)",
     "run_id": "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-agree-aa-fold-a-generation-v1", "trace": True},
    {"label": "agree", "title": "AGREE (w_agree 1.0, k 60, fuse 8-1-8)",
     "run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "trace": True},
    {"label": "plan", "title": "PLAN lock",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
     "attempt": "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1", "trace": False},
    {"label": "planr", "title": "PLANr (replicate)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1",
     "attempt": "attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1", "trace": False},
)
NULL_PAIRS = (("aa", "plan"), ("aa", "planr"), ("plan", "planr"))
POS_STRATA = ("1", "2-8", "none")
# ENTITY_KINDS is imported from analysis.sealed_credit.entity_states (unchanged 7-tuple).
PRIMARY_CLASSES = ("UNPARSED", "CATCH-ALL", "RETRIEVAL", "CONSUMPTION-PERCEPTION-DROP", "CONSUMPTION-SOLVER-CHOICE")


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


def pct(num: float, den: float) -> float:
    return round(100.0 * num / den, 2) if den else 0.0


def pos_stratum(pos) -> str:
    return "none" if pos is None else "1" if pos == 1 else "2-8"


def poisson_interval(mean: float) -> list:
    """Central 95 % interval of a Poisson count with this mean (exact CDF walk)."""

    if mean <= 0:
        return [0, 0]
    low = None
    cdf, k, term = 0.0, 0, math.exp(-mean)
    while True:
        cdf += term
        if low is None and cdf >= 0.025:
            low = k
        if cdf >= 0.975:
            return [low, k]
        k += 1
        term *= mean / k


# ---------------------------------------------------------------------------
# canonical filler form and entity error classes: imported from
# analysis.sealed_credit.entity_states (design spec 2026-09-29, sealed-credit
# inner loop, task 2) -- fold, canonical, norm_distance, contiguous_in,
# pair_kind, entity_items, ENTITY_KINDS, NEAR_THRESHOLD.


_REL_DAY = {"today", "tomorrow", "tonight", "yesterday"}
_WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
             "mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays"}
_MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
           "november", "december"}
_PERIODS = {"week", "weekend", "month", "year", "weeks", "months", "years", "weekends"}
_DAYPARTS = {"morning", "afternoon", "evening", "night", "noon", "midnight", "tonight", "mornings", "evenings"}


def temporal_pattern(slot_type: str, filler: str):
    """A coarse, reproducible pattern class of a date or time gold value (class
    names only ever leave this process)."""

    if slot_type not in ("date", "time"):
        return None
    tokens = set(canonical(filler).split())
    has_digit = any(t.isdigit() for t in tokens)
    if slot_type == "date":
        if tokens & _REL_DAY:
            return "relative-day"
        if tokens & _WEEKDAYS:
            return "weekday"
        if tokens & _MONTHS or has_digit:
            return "calendar-date"
        if tokens & _PERIODS:
            return "period"
        return "other"
    if has_digit or tokens & {"am", "pm"}:
        return "clock"
    if tokens & _DAYPARTS:
        return "daypart"
    if tokens & {"minute", "minutes", "hour", "hours", "second", "seconds"}:
        return "duration"
    return "other"


def repaired(gold: tuple, pred: tuple, items: list) -> list:
    """The prediction list with exactly the given error items repaired to gold."""

    out = list(pred)
    drop, append = set(), []
    for item in items:
        if item["kind"] == "MISSING":
            append.append(gold[item["gold_index"]])
        elif item["kind"] == "SPURIOUS":
            drop.add(item["pred_index"])
        else:
            out[item["pred_index"]] = gold[item["gold_index"]]
    return [e for i, e in enumerate(out) if i not in drop] + append


def slu_counts(gold: tuple, pred) -> tuple:
    score = score_slu(gold_scenario="s", gold_action="a", gold_entities=list(gold),
                      predicted_scenario="s", predicted_action="a", predicted_entities=list(pred))
    return (score.slu_f1_word_tp + score.slu_f1_char_tp, score.slu_f1_word_fp + score.slu_f1_char_fp,
            score.slu_f1_word_fn + score.slu_f1_char_fn)


def micro_f1(totals) -> float:
    return 100.0 * _prf(*totals)[2]


# ---------------------------------------------------------------------------
# sealed arms


def load_scores(directory: Path, run_id: str) -> dict:
    path = directory / f"{run_id}.scores.json"
    block = json.loads(path.read_text(encoding="utf-8"))[SCORER]
    rows = {str(s["sample_id"]): s for s in block["per_sample"]}
    return {"rows": rows, "sha256": digest(path), "relpath": path.name,
            "official_intent_accuracy": block["aggregate"]["official"]["intent_accuracy"]}


def load_outputs(directory: Path, run_id: str) -> dict:
    path = directory / f"{run_id}.outputs.jsonl"
    rows = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            scenario, action, entities, parsed = parse_slu_response(record.get("text") or "")
            rows[record["sample_id"]] = {
                "parsed": bool(parsed),
                "intent": f"{scenario}_{action}" if parsed and scenario is not None and action is not None else None,
                "entities": tuple(SlotEntity(e.type, e.filler) for e in entities)}
    return {"rows": rows, "sha256": digest(path), "relpath": path.name}


def load_arm(data_root: Path, arm: dict, skip_trace: bool) -> dict:
    phases = GP.load_phases(data_root, arm)
    directory = phases["directory"]
    outputs = load_outputs(directory, arm["run_id"])
    scores = load_scores(directory, arm["run_id"])
    trace = None
    if arm["trace"] and not skip_trace:
        trace = GP.verify_trace(directory, arm, phases)
    return {"label": arm["label"], "title": arm["title"], "run_id": arm["run_id"], "attempt": arm["attempt"],
            "phases": phases["rows"], "phase_checks": phases["checks"],
            "phases_relpath": phases["relpath"], "phases_sha256": phases["sha256"],
            "outputs": outputs["rows"], "outputs_sha256": outputs["sha256"],
            "outputs_relpath": str((directory / outputs["relpath"]).relative_to(data_root)),
            "scores": scores["rows"], "scores_sha256": scores["sha256"],
            "scores_relpath": str((directory / scores["relpath"]).relative_to(data_root)),
            "official_intent_accuracy": scores["official_intent_accuracy"], "trace": trace}


def load_gold(lock, data_root: Path) -> dict:
    records = load_slurp_split(lock, data_root, "train", workers=4)
    return {r.sample_id: {"intent": r.intent, "scenario": r.scenario, "action": r.action,
                          "entities": tuple(SlotEntity(e.type, e.filler) for e in r.entities)}
            for r in records}


def structural_checks(arm: dict, gold: dict) -> dict:
    checks = Counter()
    for sample_id, sealed in sorted(arm["scores"].items()):
        out, g = arm["outputs"].get(sample_id), gold.get(sample_id)
        if out is None or g is None or sample_id not in arm["phases"]:
            checks["missing"] += 1
            continue
        checks["rows"] += 1
        checks["parse_agrees_with_sealed_parsed"] += int(out["parsed"] == bool(sealed.get("parsed", True)))
        checks["intent_agrees_with_sealed_exact"] += int((out["intent"] == g["intent"]) == bool(sealed["scenario_action_exact"]))
        tp, fp, fn = slu_counts(g["entities"], out["entities"])
        sealed_tp = sealed["slu_f1_word_tp"] + sealed["slu_f1_char_tp"]
        sealed_fp = sealed["slu_f1_word_fp"] + sealed["slu_f1_char_fp"]
        sealed_fn = sealed["slu_f1_word_fn"] + sealed["slu_f1_char_fn"]
        checks["slu_counts_agree_with_sealed"] += int(abs(tp - sealed_tp) < 1e-9 and abs(fp - sealed_fp) < 1e-9
                                                      and abs(fn - sealed_fn) < 1e-9)
    return dict(sorted(checks.items()))


# ---------------------------------------------------------------------------
# retrieval replay (agreement and centroid key) for rank context


def retrieval_replay(data_root: Path, row_ids: list, agree_arm: dict, pool: dict) -> dict:
    store = RD.load_store(data_root)
    queries = load_sealed_segment_vectors(data_root / QUERY, expected_sha256=QUERY_SHA, dimensions=(RD.IB_DIM,))
    cos_written = RD.recompute(store, queries, row_ids)
    centroid_vectors = load_sealed_vectors(data_root / CENTROID, expected_sha256=CENTROID_SHA, dimensions=(RD.IB_DIM,))
    if set(centroid_vectors) != set(store["facet_vectors"]):
        raise ReadError("centroid key file does not cover the released store's facets exactly")
    cos_centroid = RD.recompute(dict(store, facet_vectors=centroid_vectors), queries, row_ids)
    out, checks = {}, Counter()
    for sample_id in row_ids:
        sealed = agree_arm["phases"][sample_id]
        mine, votes = RD.own_key(sample_id), Counter()
        for key in sealed["ex_rendered"]:
            if mine is not None and key == mine:
                continue
            intent = pool["values"].get(key, {}).get("intent")
            if intent is not None:
                votes[intent] += 1
        total = sum(votes.values())
        share = {i: votes[i] / total for i in votes} if total else {}
        written = cos_written.get(sample_id, {})
        centroid = cos_centroid.get(sample_id, {})
        agree_order = RD.blend(written, share, AGREE_WEIGHT)
        comp1_order = RD.blend(centroid, share, AGREE_WEIGHT)
        checks["rows"] += 1
        checks["agree_replay_top8_equals_sealed_block"] += int(agree_order[:FLOWN_K] == sealed["boundary"])
        checks["agree_replay_top8_set_equals_sealed_block"] += int(set(agree_order[:FLOWN_K]) == set(sealed["boundary"]))
        out[sample_id] = {"agree_order": agree_order, "comp1_order": comp1_order, "written_order": RD.order(written),
                          "votes": dict(sorted(votes.items()))}
    return {"rows": out, "checks": dict(sorted(checks.items())), "store_snapshot_sha256": store["snapshot_file_sha256"]}


def rank_in(order: list, intent: str):
    return order.index(intent) + 1 if intent in order else None


# ---------------------------------------------------------------------------
# per-row facts


def row_facts(sample_id: str, arm: dict, gold_row: dict) -> dict:
    sealed, out, score = arm["phases"][sample_id], arm["outputs"][sample_id], arm["scores"][sample_id]
    g = gold_row["intent"]
    boundary, perception = sealed["boundary"], sealed["perception"]
    delivered = out["intent"]
    return {"correct": bool(score["scenario_action_exact"]), "parsed": out["parsed"], "delivered": delivered,
            "boundary": boundary, "perception": perception,
            "gold_pos": boundary.index(g) + 1 if g in boundary else None,
            "delivered_pos": boundary.index(delivered) + 1 if delivered in boundary else None,
            "gold_in_perception": g in perception, "delivered_in_perception": delivered in perception,
            "supply": sealed["solver_ids"], "ex_rendered": sealed["ex_rendered"], "contracts": sealed["contracts"]}


def transition(left: dict, right: dict) -> str:
    if left["boundary"] == right["boundary"]:
        return "identical-block"
    lp, rp = left["gold_pos"], right["gold_pos"]
    if lp is None and rp is None:
        return "never-delivered"
    if lp is None:
        return "newly-delivered"
    if rp is None:
        return "dropped"
    if rp < lp:
        return "promoted"
    if rp > lp:
        return "demoted"
    return "same-position-block-changed"


HARM_CLASS = {"dropped": "(i) displaced", "identical-block": "(ii) identical block",
              "demoted": "(iii) gold demoted", "same-position-block-changed": "(iii) gold same position, block changed",
              "promoted": "(iii) gold promoted", "never-delivered": "(iii) gold never delivered",
              "newly-delivered": "(iii) gold newly delivered"}
SAVE_CLASS = {"newly-delivered": "gold newly delivered", "promoted": "gold promoted",
              "identical-block": "identical block", "same-position-block-changed": "gold same position, block changed",
              "demoted": "gold demoted", "never-delivered": "gold never delivered", "dropped": "gold dropped"}


def flip_rows(arms: dict, left: str, right: str, ids: list) -> dict:
    saves, harms = [], []
    for sid in ids:
        lc = bool(arms[left]["scores"][sid]["scenario_action_exact"])
        rc = bool(arms[right]["scores"][sid]["scenario_action_exact"])
        if lc != rc:
            (saves if rc else harms).append(sid)
    return {"saves": saves, "harms": harms}


def null_floor(arms: dict, gold: dict, ids: list) -> dict:
    """Flip rates between flights of the same plan, stratified by the left
    arm's gold position.  Harm rate = right-wrong / left-correct rows."""

    pairs, pooled = {}, defaultdict(Counter)
    for left, right in NULL_PAIRS:
        flips = flip_rows(arms, left, right, ids)
        strata, identical, perc_changed, perc_set_changed = defaultdict(Counter), 0, 0, 0
        for sid in ids:
            lf = row_facts(sid, arms[left], gold[sid])
            rf = row_facts(sid, arms[right], gold[sid])
            strata[pos_stratum(lf["gold_pos"])]["left_correct" if lf["correct"] else "left_wrong"] += 1
            identical += int(lf["boundary"] == rf["boundary"])
            perc_changed += int(lf["boundary"] == rf["boundary"] and lf["perception"] != rf["perception"])
            perc_set_changed += int(lf["boundary"] == rf["boundary"] and set(lf["perception"]) != set(rf["perception"]))
        for kind in ("harms", "saves"):
            for sid in flips[kind]:
                strata[pos_stratum(row_facts(sid, arms[left], gold[sid])["gold_pos"])][kind] += 1
        for s, c in strata.items():
            pooled[s].update(c)
        pairs[f"{left}-vs-{right}"] = {
            "saves": len(flips["saves"]), "harms": len(flips["harms"]),
            "discordant": len(flips["saves"]) + len(flips["harms"]),
            "identical_block_rows": identical, "perception_list_changed_on_identical_block": perc_changed,
            "perception_set_changed_on_identical_block": perc_set_changed,
            "strata": {s: dict(sorted(strata[s].items())) for s in POS_STRATA}}
    rates = {}
    for s in POS_STRATA:
        c = pooled[s]
        rates[s] = {"harm_rate": c["harms"] / c["left_correct"] if c["left_correct"] else 0.0,
                    "save_rate": c["saves"] / c["left_wrong"] if c["left_wrong"] else 0.0,
                    "pooled": dict(sorted(c.items()))}
    return {"pairs": pairs, "rates": rates}


def q1(arms: dict, gold: dict, ids: list, null: dict, replay: dict) -> dict:
    aa, ar = arms["aa"], arms["agree"]
    flips = flip_rows(arms, "aa", "agree", ids)
    rows = {}
    for kind in ("saves", "harms"):
        for sid in flips[kind]:
            lf, rf = row_facts(sid, aa, gold[sid]), row_facts(sid, ar, gold[sid])
            t = transition(lf, rf)
            wrong_old_pos = (lf["boundary"].index(rf["delivered"]) + 1) if rf["delivered"] in lf["boundary"] else None
            rows[sid] = {
                "kind": kind[:-1], "gold_intent": gold[sid]["intent"], "transition": t,
                "class": (HARM_CLASS if kind == "harms" else SAVE_CLASS)[t],
                "gold_pos_aa": lf["gold_pos"], "gold_pos_agree": rf["gold_pos"],
                "block_identical": lf["boundary"] == rf["boundary"],
                "block_set_identical": set(lf["boundary"]) == set(rf["boundary"]),
                "supply_identical": lf["supply"] == rf["supply"],
                "exemplars_identical": lf["ex_rendered"] == rf["ex_rendered"],
                "perception_identical": lf["perception"] == rf["perception"],
                "gold_in_perception_aa": lf["gold_in_perception"], "gold_in_perception_agree": rf["gold_in_perception"],
                "delivered_aa": lf["delivered"], "delivered_agree": rf["delivered"],
                "delivered_in_perception_aa": lf["delivered_in_perception"],
                "delivered_in_perception_agree": rf["delivered_in_perception"],
                "delivered_pos_aa": lf["delivered_pos"], "delivered_pos_agree": rf["delivered_pos"],
                "wrong_answer_entry_moved_up": bool(
                    kind == "harms" and rf["delivered_pos"] is not None
                    and (wrong_old_pos is None or wrong_old_pos > rf["delivered_pos"])),
                "aa_gold_stratum": pos_stratum(lf["gold_pos"]),
                "votes_gold": replay["rows"][sid]["votes"].get(gold[sid]["intent"], 0),
                "votes_delivered_agree": replay["rows"][sid]["votes"].get(rf["delivered"], 0),
                "votes_delivered_aa": replay["rows"][sid]["votes"].get(lf["delivered"], 0)}
    rates = null["rates"]
    exp, block_rows, transitions_all = defaultdict(float), Counter(), Counter()
    by_transition = defaultdict(lambda: defaultdict(float))
    for sid in ids:
        lf, rf = row_facts(sid, aa, gold[sid]), row_facts(sid, ar, gold[sid])
        s = pos_stratum(lf["gold_pos"])
        block = "identical" if lf["boundary"] == rf["boundary"] else "changed"
        t = transition(lf, rf)
        transitions_all[t] += 1
        cell = by_transition[t]
        if lf["correct"]:
            cell["aa_correct"] += 1
            cell["expected_harms"] += rates[s]["harm_rate"]
            cell["harms"] += int(not rf["correct"])
        else:
            cell["aa_wrong"] += 1
            cell["expected_saves"] += rates[s]["save_rate"]
            cell["saves"] += int(rf["correct"])
        block_rows[block + ("_aa_correct" if lf["correct"] else "_aa_wrong")] += 1
        if lf["correct"]:
            exp[f"harms_{block}"] += rates[s]["harm_rate"]
            exp["harms_all"] += rates[s]["harm_rate"]
        else:
            exp[f"saves_{block}"] += rates[s]["save_rate"]
            exp["saves_all"] += rates[s]["save_rate"]
    observed = Counter()
    for r in rows.values():
        observed[f"{r['kind']}s_{'identical' if r['block_identical'] else 'changed'}"] += 1
        observed[f"{r['kind']}s_all"] += 1
    expected = {k: {"expected": round(v, 2), "poisson95": poisson_interval(v)} for k, v in sorted(exp.items())}
    transition_table = {}
    for t, cell in sorted(by_transition.items()):
        transition_table[t] = {
            "aa_correct": int(cell["aa_correct"]), "harms": int(cell["harms"]),
            "expected_null_harms": round(cell["expected_harms"], 2),
            "expected_null_harms_poisson95": poisson_interval(cell["expected_harms"]),
            "aa_wrong": int(cell["aa_wrong"]), "saves": int(cell["saves"]),
            "expected_null_saves": round(cell["expected_saves"], 2),
            "expected_null_saves_poisson95": poisson_interval(cell["expected_saves"])}
    noise_harms = sum(min(c["harms"], c["expected_null_harms"]) for c in transition_table.values())
    noise_saves = sum(min(c["saves"], c["expected_null_saves"]) for c in transition_table.values())
    within = sum(c["harms"] for c in transition_table.values()
                 if c["harms"] <= c["expected_null_harms_poisson95"][1])
    return {"rows": dict(sorted(rows.items())), "expected_null": expected, "observed": dict(sorted(observed.items())),
            "by_transition": transition_table,
            "noise_attributable": {"harms_sum_min_observed_expected": round(noise_harms, 2),
                                   "saves_sum_min_observed_expected": round(noise_saves, 2),
                                   "harms_in_transition_classes_within_null_interval": within},
            "block_rows": dict(sorted(block_rows.items())), "transitions_all_rows": dict(sorted(transitions_all.items()))}


def q1_tables(q: dict) -> dict:
    out = {}
    for kind in ("save", "harm"):
        rows = [r for r in q["rows"].values() if r["kind"] == kind]
        detail = {}
        for cls in sorted({r["class"] for r in rows}):
            sub = [r for r in rows if r["class"] == cls]
            detail[cls] = {
                "n": len(sub),
                "gold_in_perception_aa": sum(r["gold_in_perception_aa"] for r in sub),
                "gold_in_perception_agree": sum(r["gold_in_perception_agree"] for r in sub),
                "perception_identical": sum(r["perception_identical"] for r in sub),
                "delivered_in_perception_aa": sum(r["delivered_in_perception_aa"] for r in sub),
                "delivered_in_perception_agree": sum(r["delivered_in_perception_agree"] for r in sub),
                "supply_identical": sum(r["supply_identical"] for r in sub),
                "exemplars_identical": sum(r["exemplars_identical"] for r in sub),
                "gold_pos_aa": dict(sorted(Counter(str(r["gold_pos_aa"]) for r in sub).items())),
                "gold_pos_agree": dict(sorted(Counter(str(r["gold_pos_agree"]) for r in sub).items())),
                "wrong_answer_entry_moved_up": sum(r["wrong_answer_entry_moved_up"] for r in sub),
                "votes_favour_delivered_over_gold": sum(r["votes_delivered_agree"] > r["votes_gold"] for r in sub),
                "votes_favour_gold": sum(r["votes_gold"] > r["votes_delivered_agree"] for r in sub)}
        out[kind] = {"n": len(rows), "by_class": detail,
                     "gold_pos_matrix": dict(sorted(Counter(f"{r['gold_pos_aa']}->{r['gold_pos_agree']}" for r in rows).items()))}
    return out


# ---------------------------------------------------------------------------
# Q2: remaining error mass


def bucket_pos(p) -> str:
    return "none" if p is None else "1" if p == 1 else "2-3" if p <= 3 else "4-8"


def bucket_rank(r) -> str:
    return ("unranked" if r is None else "1-8" if r <= 8 else "9-12" if r <= 12 else "13-16" if r <= 16
            else "17-30" if r <= 30 else "31-60")


def bucket_ex(n: int) -> str:
    return "0" if n == 0 else "1-2" if n <= 2 else "3-5" if n <= 5 else "6-10" if n <= 10 else "11-20"


def q2_intent(arms: dict, gold: dict, ids: list, replay: dict, pool: dict, entity: dict) -> dict:
    ar = arms["agree"]
    rows = {}
    for sid in ids:
        f = row_facts(sid, ar, gold[sid])
        if f["correct"]:
            continue
        g, d = gold[sid]["intent"], f["delivered"]
        if not f["parsed"] or d is None:
            stage = "UNPARSED"
        elif f["gold_pos"] is None:
            stage = "RETRIEVAL"
        elif not f["gold_in_perception"]:
            stage = "CONSUMPTION-PERCEPTION-DROP"
        else:
            stage = "CONSUMPTION-SOLVER-CHOICE"
        catch_all = g in CATCH_ALL or d in CATCH_ALL
        primary = "UNPARSED" if stage == "UNPARSED" else "CATCH-ALL" if catch_all else stage
        ds = d.split("_", 1)[0] if d else None
        rp = replay["rows"].get(sid, {})
        rows[sid] = {
            "gold_intent": g, "delivered_intent": d, "stage": stage, "primary": primary, "catch_all": catch_all,
            "scope": "unparsed" if d is None else "within-scenario" if ds == gold[sid]["scenario"] else "cross-scenario",
            "gold_pos": f["gold_pos"], "delivered_pos": f["delivered_pos"],
            "gold_in_perception": f["gold_in_perception"], "delivered_in_perception": f["delivered_in_perception"],
            "perception_width": len(f["perception"]),
            "gold_agree_rank": rank_in(rp.get("agree_order", []), g),
            "gold_written_rank": rank_in(rp.get("written_order", []), g),
            "gold_comp1_rank": rank_in(rp.get("comp1_order", []), g),
            "gold_intent_exemplars": sum(1 for k in f["ex_rendered"] if pool["values"].get(k, {}).get("intent") == g),
            "delivered_intent_exemplars": sum(1 for k in f["ex_rendered"] if d is not None
                                              and pool["values"].get(k, {}).get("intent") == d),
            "votes_gold": rp.get("votes", {}).get(g, 0), "votes_delivered": rp.get("votes", {}).get(d, 0),
            "delivered_is_perception_first": bool(f["perception"]) and f["perception"][0] == d,
            "gold_is_perception_first": bool(f["perception"]) and f["perception"][0] == g,
            "null_flights_correct": sum(int(bool(arms[a]["scores"][sid]["scenario_action_exact"]))
                                        for a in ("aa", "plan", "planr")),
            "perception_suspect": entity["rows"][sid]["perception_suspect"],
            "has_gold_entities": bool(gold[sid]["entities"])}
    return rows


def q2_tables(rows: dict, arms: dict, gold: dict, ids: list) -> dict:
    wrong = [rows[s] for s in sorted(rows)]
    per_class = {}
    for cls in PRIMARY_CLASSES:
        sub = [r for r in wrong if r["primary"] == cls]
        per_class[cls] = {
            "n": len(sub), "pp": round(len(sub) * PP_PER_ROW, 2), "share_pct": pct(len(sub), len(wrong)),
            "within_scenario": sum(r["scope"] == "within-scenario" for r in sub),
            "cross_scenario": sum(r["scope"] == "cross-scenario" for r in sub),
            "perception_suspect": sum(r["perception_suspect"] for r in sub),
            "with_gold_entities": sum(r["has_gold_entities"] for r in sub),
            "stable_wrong_in_all_3_null_flights": sum(r["null_flights_correct"] == 0 for r in sub),
            "correct_in_some_null_flight": sum(r["null_flights_correct"] > 0 for r in sub),
            "gold_pos": dict(sorted(Counter(bucket_pos(r["gold_pos"]) for r in sub).items())),
            "delivered_in_block": sum(r["delivered_pos"] is not None for r in sub),
            "delivered_at_1": sum(r["delivered_pos"] == 1 for r in sub),
            "delivered_in_perception": sum(r["delivered_in_perception"] for r in sub),
            "gold_in_perception": sum(r["gold_in_perception"] for r in sub),
            "gold_intent_exemplars": dict(sorted(Counter(bucket_ex(r["gold_intent_exemplars"]) for r in sub).items())),
            "gold_agree_rank": dict(sorted(Counter(bucket_rank(r["gold_agree_rank"]) for r in sub).items())),
            "gold_comp1_rank": dict(sorted(Counter(bucket_rank(r["gold_comp1_rank"]) for r in sub).items())),
            "comp1_would_deliver": sum(r["gold_comp1_rank"] is not None and r["gold_comp1_rank"] <= FLOWN_K for r in sub),
            "agree_rank_9_to_16": sum(r["gold_agree_rank"] is not None and 9 <= r["gold_agree_rank"] <= 16 for r in sub),
            "exemplar_votes_favour_delivered": sum(r["votes_delivered"] > r["votes_gold"] for r in sub),
            "exemplar_votes_favour_gold": sum(r["votes_gold"] > r["votes_delivered"] for r in sub),
            "exemplar_votes_tied": sum(r["votes_gold"] == r["votes_delivered"] for r in sub),
            "delivered_is_perception_first": sum(r["delivered_is_perception_first"] for r in sub),
            "gold_is_perception_first": sum(r["gold_is_perception_first"] for r in sub)}
    consumption = {}
    for cls in ("CONSUMPTION-PERCEPTION-DROP", "CONSUMPTION-SOLVER-CHOICE"):
        sub = [r for r in wrong if r["stage"] == cls]
        consumption[cls] = {
            "all_stage_rows": len(sub),
            "by_gold_pos": dict(sorted(Counter(bucket_pos(r["gold_pos"]) for r in sub).items())),
            "delivered_at_1": sum(r["delivered_pos"] == 1 for r in sub),
            "delivered_above_gold": sum(r["delivered_pos"] is not None and r["gold_pos"] is not None
                                        and r["delivered_pos"] < r["gold_pos"] for r in sub),
            "delivered_in_perception": sum(r["delivered_in_perception"] for r in sub),
            "catch_all": sum(r["catch_all"] for r in sub)}
    pairs = Counter((r["gold_intent"], r["delivered_intent"] or "UNPARSED", r["scope"]) for r in wrong)
    gold_intents = Counter(r["gold_intent"] for r in wrong)
    catch = {"gold_general_quirky": sum(r["gold_intent"] in CATCH_ALL for r in wrong),
             "delivered_general_quirky": sum((r["delivered_intent"] or "") in CATCH_ALL for r in wrong),
             "stage_of_catch_all_rows": dict(sorted(Counter(r["stage"] for r in wrong if r["catch_all"]).items())),
             "catch_all_gold_rows_on_roster": sum(1 for s in ids if gold[s]["intent"] in CATCH_ALL),
             "catch_all_gold_rows_correct": sum(1 for s in ids if gold[s]["intent"] in CATCH_ALL
                                                and arms["agree"]["scores"][s]["scenario_action_exact"])}
    agree_rows = [row_facts(s, arms["agree"], gold[s]) for s in ids]
    on_list = [f for f in agree_rows if f["gold_in_perception"]]
    in_block_off_list = [f for f in agree_rows if f["gold_pos"] is not None and not f["gold_in_perception"]]
    return {"n_wrong": len(wrong), "pp_wrong": round(len(wrong) * PP_PER_ROW, 2),
            "per_class": per_class, "stage": dict(sorted(Counter(r["stage"] for r in wrong).items())),
            "consumption": consumption,
            "scope": dict(sorted(Counter(r["scope"] for r in wrong).items())),
            "stable_wrong_all": sum(r["null_flights_correct"] == 0 for r in wrong),
            "conversion_given_gold_on_list": [sum(f["correct"] for f in on_list), len(on_list)],
            "conversion_given_gold_in_block_off_list": [sum(f["correct"] for f in in_block_off_list), len(in_block_off_list)],
            "top_pairs": [{"gold": g, "delivered": d, "scope": s, "rows": n}
                          for (g, d, s), n in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))[:25]],
            "distinct_pairs": len(pairs), "pairs_with_one_row": sum(1 for n in pairs.values() if n == 1),
            "top_gold_intents": [{"gold": g, "rows": n}
                                 for g, n in sorted(gold_intents.items(), key=lambda kv: (-kv[1], kv[0]))[:15]],
            "catch_all": catch}


def entity_analysis(arm: dict, gold: dict, ids: list, pool: dict) -> dict:
    rows, items_all, base = {}, [], {}
    for sid in ids:
        g, p = gold[sid]["entities"], arm["outputs"][sid]["entities"]
        items = entity_items(g, p)
        base[sid] = slu_counts(g, p)
        sealed = arm["phases"][sid]
        demonstrated = set()
        for key in sealed["ex_rendered"]:
            demonstrated.update(pool["values"].get(key, {}).get("fillers", {}).keys())
        cards = set(sealed["contracts"])
        for item in items:
            item["temporal_pattern"] = (temporal_pattern(item["type"], g[item["gold_index"]].filler)
                                        if item["gold_index"] is not None else None)
            item["type_card_delivered"] = item["type"] in cards
            item["type_demonstrated_in_exemplars"] = item["type"] in demonstrated
        near_by = {str(t): any(i["kind"] in ("NEAR", "WRONG-VALUE", "WRONG-TYPE") and i["distance"] is not None
                               and 0 < i["distance"] <= t
                               and not (i["kind"] == "WRONG-TYPE" and i["sub"] == "same-value")
                               for i in items)
                   for t in NEAR_SENSITIVITY}
        intent_ok = bool(arm["scores"][sid]["scenario_action_exact"])
        rows[sid] = {"items": items, "perception_suspect": near_by[str(NEAR_THRESHOLD)], "near_by_threshold": near_by,
                     "intent_ok": intent_ok, "gold_entities": len(g), "pred_entities": len(p)}
        items_all.extend(dict(item, sample_id=sid, intent_ok=intent_ok) for item in items)
    totals = [sum(base[s][k] for s in ids) for k in range(3)]
    f1 = micro_f1(totals)

    def repair_gain(select) -> float:
        new = list(totals)
        for sid in ids:
            chosen = [i for i in rows[sid]["items"] if select(i, rows[sid])]
            if not chosen:
                continue
            counts = slu_counts(gold[sid]["entities"],
                                repaired(gold[sid]["entities"], arm["outputs"][sid]["entities"], chosen))
            for k in range(3):
                new[k] += counts[k] - base[sid][k]
        return round(micro_f1(new) - f1, 2)

    by_kind = {}
    for kind in ENTITY_KINDS:
        sub = [i for i in items_all if i["kind"] == kind]
        by_kind[kind] = {
            "items": len(sub), "on_intent_wrong_rows": sum(not i["intent_ok"] for i in sub),
            "subkinds": dict(sorted(Counter(i["sub"] for i in sub).items())),
            "type_card_delivered": sum(i["type_card_delivered"] for i in sub),
            "type_demonstrated_in_exemplars": sum(i["type_demonstrated_in_exemplars"] for i in sub),
            "repair_gain_pp": repair_gain(lambda i, r, k=kind: i["kind"] == k),
            "repair_gain_intent_right_rows_pp": repair_gain(lambda i, r, k=kind: i["kind"] == k and r["intent_ok"])}
    gold_by_type = Counter(e.type for s in ids for e in gold[s]["entities"])
    by_type = []
    for slot_type, n in sorted(Counter(i["type"] for i in items_all).items(), key=lambda kv: (-kv[1], kv[0])):
        sub = [i for i in items_all if i["type"] == slot_type]
        by_type.append({"type": slot_type, "items": n, "gold_items_on_roster": gold_by_type.get(slot_type, 0),
                        "kinds": dict(sorted(Counter(i["kind"] for i in sub).items())),
                        "repair_gain_pp": repair_gain(lambda i, r, t=slot_type: i["type"] == t)})
    temporal = {}
    for slot_type in ("date", "time"):
        gold_patterns = Counter(temporal_pattern(slot_type, e.filler) for s in ids for e in gold[s]["entities"]
                                if e.type == slot_type)
        errs = defaultdict(Counter)
        for i in items_all:
            if i["type"] == slot_type and i["temporal_pattern"] is not None:
                errs[i["temporal_pattern"]][i["kind"]] += 1
        temporal[slot_type] = {pattern: {"gold_items": gold_patterns[pattern],
                                         "error_items_by_kind": dict(sorted(errs[pattern].items()))}
                               for pattern in sorted(gold_patterns)}
    wrong_type_pairs = Counter(f"{i['type']}->{i['pred_type']}" for i in items_all if i["kind"] == "WRONG-TYPE")
    # cumulative ladder: kinds repaired one after another in descending isolated gain; increments sum to the gap
    ladder, chosen_kinds, previous = [], [], 0.0
    for kind in sorted(ENTITY_KINDS, key=lambda k: (-by_kind[k]["repair_gain_pp"], k)):
        chosen_kinds.append(kind)
        gain = repair_gain(lambda i, r, ks=tuple(chosen_kinds): i["kind"] in ks)
        ladder.append({"kind": kind, "cumulative_pp": gain, "increment_pp": round(gain - previous, 2)})
        previous = gain
    targeted = {
        "date relative-day MISSING": repair_gain(lambda i, r: i["type"] == "date" and i["kind"] == "MISSING"
                                                 and i["temporal_pattern"] == "relative-day"),
        "date MISSING (all patterns)": repair_gain(lambda i, r: i["type"] == "date" and i["kind"] == "MISSING"),
        "WRONG-TYPE same-value (span right, type wrong)": repair_gain(
            lambda i, r: i["kind"] == "WRONG-TYPE" and i["sub"] == "same-value"),
        "SPURIOUS on intent-right rows": repair_gain(lambda i, r: i["kind"] == "SPURIOUS" and r["intent_ok"]),
        "SPURIOUS on intent-wrong rows": repair_gain(lambda i, r: i["kind"] == "SPURIOUS" and not r["intent_ok"]),
        "NEAR + WRONG-VALUE (value-level, perception or invention)": repair_gain(
            lambda i, r: i["kind"] in ("NEAR", "WRONG-VALUE"))}
    near_rates = {}
    for threshold in NEAR_SENSITIVITY:
        key = str(threshold)
        wrong = [s for s in ids if not rows[s]["intent_ok"] and rows[s]["gold_entities"]]
        right = [s for s in ids if rows[s]["intent_ok"] and rows[s]["gold_entities"]]
        near_rates[key] = {"intent_wrong_rows_with_gold_entities": len(wrong),
                           "intent_wrong_flagged": sum(rows[s]["near_by_threshold"][key] for s in wrong),
                           "intent_right_rows_with_gold_entities": len(right),
                           "intent_right_flagged": sum(rows[s]["near_by_threshold"][key] for s in right)}
    return {"rows": rows, "slu_f1_micro": round(f1, 2), "gap_pp": round(100.0 - f1, 2), "totals": totals,
            "gold_items": sum(gold_by_type.values()), "pred_items": sum(len(arm["outputs"][s]["entities"]) for s in ids),
            "error_items": len(items_all), "by_kind": by_kind, "by_type": by_type,
            "all_repaired_pp": repair_gain(lambda i, r: True),
            "intent_wrong_rows_repaired_pp": repair_gain(lambda i, r: not r["intent_ok"]),
            "intent_right_rows_repaired_pp": repair_gain(lambda i, r: r["intent_ok"]),
            "near_rates": near_rates, "temporal_patterns": temporal, "ladder": ladder, "targeted_repairs": targeted,
            "wrong_type_pairs": dict(sorted(wrong_type_pairs.items(), key=lambda kv: (-kv[1], kv[0])))}


# ---------------------------------------------------------------------------
# tables (markdown fragment; the committed note quotes it)


def md_table(header: list, rows: list) -> str:
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join("---" if i == 0 else "---:" for i in range(len(header))) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def js(value) -> str:
    return json.dumps(value, sort_keys=True).replace("|", "/")


def render_tables(report: dict) -> str:
    out = [f"# {READ_ID} tables", "", f"Recipe `{RECIPE}`. Generated `{report['generated_at']}`.", ""]
    s = report["structural"]
    out += ["## Structural checks", "", md_table(
        ["arm", "rows", "parse agrees", "intent agrees", "SLU counts agree", "perception order agrees (trace)",
         "first solver order agrees (trace)", "official intent acc"],
        [[a, c["checks"].get("rows"), c["checks"].get("parse_agrees_with_sealed_parsed"),
          c["checks"].get("intent_agrees_with_sealed_exact"), c["checks"].get("slu_counts_agree_with_sealed"),
          (f"{c['trace']['perception_order_agrees']}/{c['trace']['perception_contacts']}" if c["trace"] else "n/a"),
          (f"{c['trace']['solver_order_agrees']}/{c['trace']['first_solver_contacts']}" if c["trace"] else "n/a"),
          c["official_intent_accuracy"]] for a, c in s["arms"].items()]), "",
        f"Agreement replay: {js(s['replay'])}", ""]
    q = report["q1"]
    out += ["## Q1 noise floor", "", md_table(
        ["null pair", "saves", "harms", "discordant", "identical block rows", "perception list changed on identical block",
         "perception set changed on identical block"],
        [[k, v["saves"], v["harms"], v["discordant"], v["identical_block_rows"], v["perception_list_changed_on_identical_block"],
          v["perception_set_changed_on_identical_block"]]
         for k, v in q["null"]["pairs"].items()]), "",
        md_table(["left gold stratum", "pooled left-correct", "pooled harms", "harm rate %", "pooled left-wrong",
                  "pooled saves", "save rate %"],
                 [[k, r["pooled"].get("left_correct", 0), r["pooled"].get("harms", 0), round(100 * r["harm_rate"], 2),
                   r["pooled"].get("left_wrong", 0), r["pooled"].get("saves", 0), round(100 * r["save_rate"], 2)]
                  for k, r in q["null"]["rates"].items()]), "",
        md_table(["quantity (AA vs AGREE)", "observed", "expected under the null", "Poisson 95 %"],
                 [[k, q["observed"].get(k, 0), v["expected"], v["poisson95"]] for k, v in q["expected_null"].items()]), "",
        f"Block rows (AA vs AGREE): {js(q['block_rows'])}; transitions over all rows: {js(q['transitions_all_rows'])}", "",
        md_table(["transition AA->AGREE", "AA-correct rows", "harms", "expected null harms", "null 95 %",
                  "AA-wrong rows", "saves", "expected null saves", "null 95 %"],
                 [[t, c["aa_correct"], c["harms"], c["expected_null_harms"], c["expected_null_harms_poisson95"],
                   c["aa_wrong"], c["saves"], c["expected_null_saves"], c["expected_null_saves_poisson95"]]
                  for t, c in q["by_transition"].items()]), "",
        f"Noise-attributable: {js(q['noise_attributable'])}", ""]
    for kind in ("save", "harm"):
        t = q["tables"][kind]
        out += [f"## Q1 {kind}s ({t['n']})", "", md_table(
            ["class", "rows", "gold pos AA", "gold pos AGREE", "gold on list AA", "gold on list AGREE", "list identical",
             "delivered from list AA", "delivered from list AGREE", "exemplars identical", "wrong answer's entry moved up",
             "votes favour delivered", "votes favour gold"],
            [[c, d["n"], js(d["gold_pos_aa"]), js(d["gold_pos_agree"]), d["gold_in_perception_aa"],
              d["gold_in_perception_agree"], d["perception_identical"], d["delivered_in_perception_aa"],
              d["delivered_in_perception_agree"], d["exemplars_identical"], d["wrong_answer_entry_moved_up"],
              d["votes_favour_delivered_over_gold"], d["votes_favour_gold"]]
             for c, d in t["by_class"].items()]), "",
            f"gold position AA->AGREE: {js(t['gold_pos_matrix'])}", ""]
    q2 = report["q2"]["tables"]
    out += ["## Q2 intent-wrong rows by primary class", "", md_table(
        ["class", "rows", "pp", "share %", "within", "cross", "gold pos", "delivered at 1", "delivered from list",
         "perception-suspect", "wrong in all 3 null flights", "gold-intent exemplars (of 20)", "COMP-1 replay delivers gold"],
        [[c, d["n"], d["pp"], d["share_pct"], d["within_scenario"], d["cross_scenario"], js(d["gold_pos"]),
          d["delivered_at_1"], d["delivered_in_perception"], d["perception_suspect"],
          d["stable_wrong_in_all_3_null_flights"], js(d["gold_intent_exemplars"]), d["comp1_would_deliver"]]
         for c, d in q2["per_class"].items()]), "",
        md_table(["class", "exemplar votes favour delivered", "favour gold", "tied", "delivered is Perception's first",
                  "gold is Perception's first", "gold agreement rank 9-16"],
                 [[c, d["exemplar_votes_favour_delivered"], d["exemplar_votes_favour_gold"], d["exemplar_votes_tied"],
                   d["delivered_is_perception_first"], d["gold_is_perception_first"], d["agree_rank_9_to_16"]]
                  for c, d in q2["per_class"].items()]), "",
        f"Stage partition (catch-all not split out): {js(q2['stage'])}; stable-wrong in all 3 null flights: {q2['stable_wrong_all']}", "",
        f"Consumption detail: {js(q2['consumption'])}", "",
        f"Conversion on AGREE: gold on the list {js(q2['conversion_given_gold_on_list'])}; "
        f"gold in the block but off the list {js(q2['conversion_given_gold_in_block_off_list'])}", "",
        f"RETRIEVAL gold rank under the flown agreement order: {js(q2['per_class']['RETRIEVAL']['gold_agree_rank'])}; "
        f"under the COMP-1 key (centroid + agreement): {js(q2['per_class']['RETRIEVAL']['gold_comp1_rank'])}", "",
        f"Catch-all: {js(q2['catch_all'])}", "",
        "### Confusion pairs (top 25)", "",
        md_table(["gold", "delivered", "scope", "rows"],
                 [[p["gold"], p["delivered"], p["scope"], p["rows"]] for p in q2["top_pairs"]]), "",
        f"Distinct pairs {q2['distinct_pairs']}, single-row pairs {q2['pairs_with_one_row']}; scope {js(q2['scope'])}", "",
        "### Gold intents carrying the most errors (top 15)", "",
        md_table(["gold", "rows"], [[g["gold"], g["rows"]] for g in q2["top_gold_intents"]]), ""]
    e = report["entities"]
    out += ["## Q2 SLU-F1 side", "",
            f"SLU-F1 micro {e['slu_f1_micro']}, gap {e['gap_pp']} pp; gold items {e['gold_items']}, predicted items "
            f"{e['pred_items']}, error items {e['error_items']}; all errors repaired {e['all_repaired_pp']} pp; repairs on "
            f"intent-wrong rows only {e['intent_wrong_rows_repaired_pp']} pp, intent-right rows only "
            f"{e['intent_right_rows_repaired_pp']} pp", "",
            md_table(["kind", "items", "on intent-wrong rows", "subkinds", "type card delivered", "type in exemplars",
                      "isolated repair pp", "repair on intent-right rows pp"],
                     [[k, d["items"], d["on_intent_wrong_rows"], js(d["subkinds"]), d["type_card_delivered"],
                       d["type_demonstrated_in_exemplars"], d["repair_gain_pp"], d["repair_gain_intent_right_rows_pp"]]
                      for k, d in e["by_kind"].items()]), "",
            "### Cumulative repair ladder (kinds in descending isolated gain; increments sum to the gap)", "",
            md_table(["kind added", "cumulative pp", "increment pp"],
                     [[x["kind"], x["cumulative_pp"], x["increment_pp"]] for x in e["ladder"]]), "",
            "### Targeted repairs", "",
            md_table(["repair", "pp"], [[k, v] for k, v in e["targeted_repairs"].items()]), "",
            "### By slot type (top 20 by error items)", "",
            md_table(["type", "gold items", "error items", "kinds", "isolated repair pp"],
                     [[t["type"], t["gold_items_on_roster"], t["items"], js(t["kinds"]), t["repair_gain_pp"]]
                      for t in e["by_type"][:20]]), "",
            "### Wrong-type pairs (gold type -> predicted type)", "", js(e["wrong_type_pairs"]), "",
            "### Temporal pattern classes (gold items; error items by kind)", "",
            md_table(["type", "pattern", "gold items", "error items by kind"],
                     [[t, p, v["gold_items"], js(v["error_items_by_kind"])]
                      for t, pats in e["temporal_patterns"].items() for p, v in pats.items()]), "",
            "### Perception-suspect criterion sensitivity", "",
            md_table(["threshold", "intent-wrong rows with gold entities", "flagged",
                      "intent-right rows with gold entities", "flagged"],
                     [[k, v["intent_wrong_rows_with_gold_entities"], v["intent_wrong_flagged"],
                       v["intent_right_rows_with_gold_entities"], v["intent_right_flagged"]]
                      for k, v in e["near_rates"].items()]), ""]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------


def build(args) -> tuple:
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    gold = load_gold(lock, data_root)
    arms = {arm["label"]: load_arm(data_root, arm, args.skip_trace) for arm in ARMS}
    ids = sorted(arms["agree"]["scores"])
    for label, arm in arms.items():
        if sorted(arm["scores"]) != ids or len(ids) != ROWS:
            raise ReadError(f"{label}: roster differs from the AGREE roster")
    pool = GP.load_exemplar_pool(data_root, EX_SNAPSHOT)
    structural = {"arms": {label: {"checks": structural_checks(arm, gold), "trace": arm["trace"],
                                   "phase_checks": arm["phase_checks"],
                                   "official_intent_accuracy": arm["official_intent_accuracy"]}
                           for label, arm in arms.items()}}
    replay = retrieval_replay(data_root, ids, arms["agree"], pool)
    structural["replay"] = replay["checks"]
    null = null_floor(arms, gold, ids)
    q1_out = q1(arms, gold, ids, null, replay)
    q1_out["null"] = null
    q1_out["tables"] = q1_tables(q1_out)
    entities = entity_analysis(arms["agree"], gold, ids, pool)
    q2_rows = q2_intent(arms, gold, ids, replay, pool, entities)
    inputs = {label: {"run_id": a["run_id"], "attempt": a["attempt"],
                      "phases": [a["phases_relpath"], a["phases_sha256"]],
                      "outputs": [a["outputs_relpath"], a["outputs_sha256"]],
                      "scores": [a["scores_relpath"], a["scores_sha256"]]} for label, a in arms.items()}
    inputs["exemplar_pool"] = [pool["relpath"], pool["sha256"]]
    inputs["query_vectors"] = [QUERY, QUERY_SHA]
    inputs["centroid_keys"] = [CENTROID, CENTROID_SHA]
    inputs["intent_boundary_snapshot_file_sha256"] = replay["store_snapshot_sha256"]
    report = {"read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
              "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                           "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
              "roster_rows": ROWS, "pp_per_row": PP_PER_ROW, "near_threshold": NEAR_THRESHOLD,
              "conversions_cited": {"kprobe": list(KPROBE_CONVERSION), "conv": list(CONV_CONVERSION)},
              "inputs": inputs, "structural": structural,
              "q1": {k: v for k, v in q1_out.items() if k != "rows"},
              "q2": {"tables": q2_tables(q2_rows, arms, gold, ids)},
              "entities": {k: v for k, v in entities.items() if k != "rows"}}
    row_lines = []
    for sid in ids:
        entry = {"sample_id": sid, "perception_suspect": entities["rows"][sid]["perception_suspect"],
                 "entity_items": entities["rows"][sid]["items"]}
        if sid in q1_out["rows"]:
            entry["q1"] = q1_out["rows"][sid]
        if sid in q2_rows:
            entry["q2"] = q2_rows[sid]
        row_lines.append(json.dumps(entry, sort_keys=True))
    return report, row_lines


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"|Generated `[^`]*`', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--skip-trace", action="store_true")
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the written outputs")
    args = parser.parse_args(argv)
    report, row_lines = build(args)
    out_dir = Path(args.data_root) / ANALYSIS_DIR
    texts = {"report.json": json.dumps(report, indent=2, sort_keys=True) + "\n",
             "rows.jsonl": "\n".join(row_lines) + "\n",
             "tables.md": render_tables(report)}
    if args.check:
        bad = [name for name, text in texts.items()
               if strip_time((out_dir / name).read_text(encoding="utf-8")) != strip_time(text)]
        print("check:", "IDENTICAL apart from generated_at" if not bad else f"DIFFERS in {bad}")
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    manifest = {name: hashlib.sha256(strip_time(text).encode("utf-8")).hexdigest() for name, text in sorted(texts.items())}
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                                 encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
