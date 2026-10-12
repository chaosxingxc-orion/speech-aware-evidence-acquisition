#!/usr/bin/env python3
"""Attribution of the COMP-1 seal-only arm's official SLU-F1 harm (entity over-emission) to a component.

A model-free read over sealed bytes: zero model, server, tokenizer, encoder,
embedder, network, GPU and paid-API contacts, and no official-scorer
subprocess.  The only scoring arithmetic is the exact {type, filler} matcher of
the repository's SLURP port (``reproduction.slurp_scoring``), which is first
shown to reproduce every sealed per-sample exact-match count of each arm it is
applied to; every SLU-F1 number is summed from the sealed per-sample word and
char counts.

The finding explained (``docs/results/2026-09-29-slurp-comp1-fold-a-read.md``):
COMP-1 (AGREE supply + centroid boundary key + the Solver cited-answer contract
``saea-solver-cited-answer-v1`` with its I7n unwrap normaliser) against the
in-chain A/A on TRAIN Fold A (1,080 rows) gains intent but loses official
pooled SLU-F1; exact-match entity FP rises 497 -> 611.  Three channels:

(a) the unwrap itself: the raw Solver envelope from the flown traces is parsed
    with the contract's own strict parser and its ``answer`` entities are
    compared, row by row, with the delivered (unwrapped + projection v3)
    entities;
(b) the Solver emitting more entities under the contract: raw-answer and
    delivered entity counts and exact FP under COMP-1 vs the A/A vs the AGREE
    arm, split by zero-gold rows, slot type and scenario;
(c) the AGREE/centroid supply: AGREE against its own in-chain A/A and against
    the COMP-1 A/A, and the COMP-1 contrast split by whether Perception's
    shortlist and the Solver's supply are identical to the comparator's.

Plus: the per-scenario explanation of the audio loss, the PLAN-correct intent
harms (30 vs 21) split by shortlist identity, and exact pp conversions (the
marginal pp of one exact FP at the arm's pooled totals, and row-swap
counterfactuals over the sealed per-sample counts).

Gold discipline.  Gold is read OFFLINE on the scoring side only, through the
governed TRAIN split and ``data.slurp.load_slurp_split`` (the path the
bad-case bank and the AGREE error-source read use), and is hashed in-process.

Text discipline.  No utterance text, transcript, delivered answer, gold
filler, predicted filler, intent name or knowledge body is written or printed.
Fillers and intent labels are compared only as in-process hashes and leave
the process as counts, slot TYPE names, scenario names, ids and hashes.

Reproducibility.  Deterministic apart from ``generated_at`` (the bootstrap is
seeded); ``--check`` re-derives the report and compares every byte except that
field against the committed report.

    PYTHONDONTWRITEBYTECODE=1 ~/.venvs/speechrl/bin/python -B \\
        scripts/analysis/slurp_comp1_slu_harm_attribution.py \\
        --data-root "$SPEECHRL_DATA_DIR" \\
        --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json [--check]
"""

from __future__ import annotations
import os

import argparse
import collections
import hashlib
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-STAGE3-COMP1-SLU-HARM-ATTRIBUTION-V1"
SCHEMA = "saea-comp1-slu-harm-attribution-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
REPORT = "docs/results/2026-09-29-slurp-comp1-slu-harm-attribution/report.json"
ROSTER = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
SCORER = "slurp-slu-official-train"
BOOT_DRAWS = 10000
BOOT_SEED = 20260929

#: label -> (run, sealed attempt holding outputs/scores, attempts holding the flown trace or None)
ARMS = {
    "comp1": ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1",
              "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only",
              ("attempt-slurp-native-stage3-comp1-fold-a-generation-v1",
               "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3")),
    "aa": ("SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1",
           "attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1", None),
    "agree": ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
              "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", None),
    "agree_aa": ("SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1",
                 "attempt-slurp-native-stage3-agree-aa-fold-a-generation-v1", None),
    "plan": ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
             "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1", ()),
    "planr": ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1",
              "attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1", ()),
}
TRACE_ARMS = ("comp1", "aa", "agree", "agree_aa")
#: (left, right, role) -- every contrast is left minus right on the same 1,080 rows.
CONTRASTS = (
    ("comp1", "aa", "the finding: COMP-1 vs its in-chain A/A"),
    ("agree", "agree_aa", "channel c: AGREE supply vs its own in-chain A/A"),
    ("agree", "aa", "channel c: AGREE supply vs the COMP-1 A/A (cross-chain)"),
    ("comp1", "agree", "COMP-1 vs AGREE (centroid key + citation contract)"),
    ("aa", "agree_aa", "null: A/A vs A/A (same locked bytes, two chains)"),
    ("plan", "planr", "null: PLAN vs PLANr (same locked bytes)"),
    ("aa", "plan", "null: COMP-1 A/A vs PLAN (same locked bytes)"),
)
STORES = ("intent-boundaries", "slot-contracts", "train-exemplars")


class ReadError(RuntimeError):
    pass


def h16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


# ---------------------------------------------------------------------------
# pure arithmetic (unit-tested on fakes)


def exact_items(gold: list, pred: list) -> dict:
    """Exact {type, filler} matching, identical to the official SpanFMeasure
    (``reproduction.slurp_scoring._exact_counts``), plus the TYPE of every FP
    and FN and whether an FP's type occurs in the row's gold at all."""

    remaining = [tuple(g) for g in gold]
    gold_types = {g[0] for g in remaining}
    tp, fp_types = 0, []
    for entity in (tuple(p) for p in pred):
        if entity in remaining:
            tp += 1
            remaining.remove(entity)
        else:
            fp_types.append(entity[0])
    return {"tp": tp, "fp": len(fp_types), "fn": len(remaining), "fp_types": fp_types,
            "fn_types": [g[0] for g in remaining],
            "fp_gold_type": sum(1 for t in fp_types if t in gold_types),
            "fp_new_type": sum(1 for t in fp_types if t not in gold_types),
            "emitted": len(pred)}


def slu_totals(rows: dict, ids, swap: dict | None = None, swap_ids=frozenset()) -> tuple:
    """Summed official SLU-F1 ingredients (word + char TP, FP, FN) over ``ids``;
    rows in ``swap_ids`` take their counts from ``swap`` instead."""

    tp = fp = fn = 0.0
    for sid in ids:
        r = swap[sid] if sid in swap_ids else rows[sid]
        tp += r["slu_f1_word_tp"] + r["slu_f1_char_tp"]
        fp += r["slu_f1_word_fp"] + r["slu_f1_char_fp"]
        fn += r["slu_f1_word_fn"] + r["slu_f1_char_fn"]
    return tp, fp, fn


def f1(tp: float, fp: float, fn: float) -> float:
    denominator = 2 * tp + fp + fn
    return 100.0 * 2 * tp / denominator if denominator else 0.0


def marginal_pp_per_exact_fp(tp: float, fp: float, fn: float) -> float:
    """d SLU-F1 / d (one entity FP of a type absent from gold): such an FP adds
    exactly 1.0 to BOTH the word and the char FP sums (the official distance
    matcher charges a full FP when no gold entity shares its type)."""

    denominator = 2 * tp + fp + fn
    return -100.0 * 2 * tp * 2 / denominator ** 2


def raw_vs_delivered(raw: list | None, delivered: list) -> dict:
    if raw is None:
        return {"raw_missing": 1}
    return {"rows": 1, "raw_entities": len(raw), "delivered_entities": len(delivered),
            "count_equal": int(len(raw) == len(delivered)),
            "type_multiset_equal": int(sorted(e[0] for e in raw) == sorted(e[0] for e in delivered)),
            "entity_multiset_equal": int(sorted(map(tuple, raw)) == sorted(map(tuple, delivered))),
            "delivered_types_not_in_raw": sum(
                (collections.Counter(e[0] for e in delivered) - collections.Counter(e[0] for e in raw)).values())}


def paired_boot(deltas: list, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> list:
    """Percentile CI95 of the SUM of per-row deltas under a row bootstrap."""

    rng = random.Random(seed)
    n = len(deltas)
    sums = sorted(sum(deltas[rng.randrange(n)] for _ in range(n)) for _ in range(draws))
    return [sums[int(0.025 * draws)], sums[int(0.975 * draws) - 1]]


def contrast(left: dict, right: dict, ids) -> dict:
    out = collections.Counter()
    for sid in ids:
        a, b = left[sid], right[sid]
        out["rows"] += 1
        for key in ("tp", "fp", "fn", "emitted"):
            out["d_" + key] += a[key] - b[key]
        out["rows_more_entities"] += int(a["emitted"] > b["emitted"])
        out["rows_fewer_entities"] += int(a["emitted"] < b["emitted"])
    return dict(out)


# ---------------------------------------------------------------------------
# sealed inputs


def load_scores(data_root: Path, label: str) -> tuple:
    run, attempt, _ = ARMS[label]
    path = data_root / "runs" / run / attempt / f"{run}.scores.json"
    rows = {r["sample_id"]: r for r in json.loads(path.read_text(encoding="utf-8"))[SCORER]["per_sample"]}
    return rows, digest(path)


def parse_entities(payload) -> tuple:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import _as_slu_prediction

    parsed = _as_slu_prediction(payload)
    if parsed is None:
        return None, None
    return h16(f"{parsed[0]}_{parsed[1]}"), [(e.type, h16(e.filler)) for e in parsed[2]]


def extract_arm(data_root: Path, label: str) -> tuple:
    """Per-row hashed features of one trace-carrying arm; the texts never leave this function."""

    from speech_aware_evidence_acquisition.rails.solver_citation import SolverCitationError, parse_cited_answer
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    run, attempt, traces = ARMS[label]
    out_path = data_root / "runs" / run / attempt / f"{run}.outputs.jsonl"
    rows, need_text, need_req = {}, set(), {}
    with out_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            receipt = record["native_episode_receipt"]
            scenario, action, entities, ok = parse_slu_response(record.get("text") or "")
            normaliser = receipt["deliver_normaliser"]
            stages = normaliser.get("stages") or [normaliser]
            perception = [v for v in receipt["role_visits"] if v["role_id"] == "perception"]
            solver = [v for v in receipt["role_visits"] if v["role_id"] == "solver"]
            final_solver = solver[-1]["execution_receipt"]["final_contact"]
            citations = (receipt.get("solver_citations") or {}).get("contacts") or []
            row = {"delivered_intent": h16(f"{scenario}_{action}") if ok else None,
                   "delivered": [(e.type, h16(e.filler)) for e in entities],
                   "raw_sha": normaliser["input_sha256"], "unwrap_output_sha": stages[0]["output_sha256"],
                   "normaliser_changed": bool(normaliser["changed"]),
                   "fillers_changed": int(normaliser.get("fillers_changed") or 0),
                   "labels_changed": int(normaliser.get("labels_changed") or 0),
                   "perception_sha": perception[-1]["execution_receipt"]["final_contact"]["response_text_sha256"],
                   "solver_visits": len(solver),
                   "solver_request": (final_solver["request_id"], final_solver["request_sha256"]),
                   "cited_supply": sorted(citations[-1].get("supplied_value_ids") or []) if citations else None,
                   "citation_contacts": len(citations)}
            need_text.update((row["raw_sha"], row["perception_sha"]))
            need_req[final_solver["request_id"]] = final_solver["request_sha256"]
            rows[record["sample_id"]] = row
    texts, supplies = {}, {}
    trace_attempts = traces if traces else (attempt,)
    for trace_attempt in trace_attempts:
        with (data_root / "runs" / run / trace_attempt / f"{run}.trace.jsonl").open("rb") as handle:
            for raw in handle:
                head = raw[:40]
                if b'"MODEL_RESPONSE"' in head:
                    payload = json.loads(raw)["payload"]
                    if payload["response_text_sha256"] in need_text:
                        texts[payload["response_text_sha256"]] = payload["text"]
                elif b'"MODEL_REQUEST"' in head:
                    outer = json.loads(raw)["payload"]
                    inner = outer["payload"]
                    rid = inner.get("request_id")
                    if rid in need_req and need_req[rid] == outer.get("payload_sha256"):
                        supplies[(rid, outer["payload_sha256"])] = sorted(
                            e["evidence_id"] for e in inner.get("supplied_evidence") or [])
    checks = collections.Counter()
    for sid, row in rows.items():
        raw = texts.get(row["raw_sha"])
        checks["raw_found"] += raw is not None
        row["raw_parse"], row["raw"], row["raw_intent"], row["cited_entity_types"] = "missing", None, None, None
        row["cited_entities"] = None
        if raw is not None and label == "comp1":
            try:
                cited = parse_cited_answer(raw)
            except SolverCitationError:
                row["raw_parse"] = "envelope-refused"
            else:
                row["raw_parse"] = "envelope"
                row["raw_intent"], row["raw"] = parse_entities(cited.answer)
                row["cited_entity_types"] = sorted(c.type for c in cited.entity_citations)
                row["cited_entities"] = [(c.type, sorted({v.split("::", 1)[0] for v in c.evidence_ids}))
                                         for c in cited.entity_citations]
                row["cited_intent_ids"] = len(cited.intent_evidence_ids)
                checks["answer_bytes_equal_unwrap_output"] += int(
                    hashlib.sha256(cited.answer_text.encode("utf-8")).hexdigest() == row["unwrap_output_sha"])
        elif raw is not None:
            scenario, action, entities, ok = parse_slu_response(raw)
            row["raw_parse"] = "plain" if ok else "unparsed"
            if ok:
                row["raw_intent"] = h16(f"{scenario}_{action}")
                row["raw"] = [(e.type, h16(e.filler)) for e in entities]
        text = texts.get(row["perception_sha"])
        shortlist = None
        if text is not None:
            try:
                shortlist = [h16(str(c.get("intent_id"))) for c in json.loads(text).get("candidates") or ()]
            except (ValueError, AttributeError, TypeError):
                shortlist = None
        checks["perception_parsed"] += shortlist is not None
        row["shortlist"] = shortlist
        request_supply = supplies.get(row["solver_request"])
        checks["solver_request_matched"] += request_supply is not None
        if row["cited_supply"] is not None and request_supply is not None:
            checks["cited_supply_equals_request_supply"] += int(row["cited_supply"] == request_supply)
        supply = row["cited_supply"] if row["cited_supply"] is not None else request_supply
        row["supply"] = None if supply is None else {
            store: sorted(h16(v) for v in supply if v.split("::", 1)[0] == store) for store in STORES}
        # slot-contract ids spell a slot TYPE name (schema vocabulary, not a gold value)
        row["contract_types"] = None if supply is None else sorted(
            v.rsplit("slot-contract:", 1)[-1] for v in supply if v.startswith("slot-contracts::"))
        checks["supply_known"] += supply is not None
        del row["solver_request"], row["cited_supply"]
    return rows, dict(sorted(checks.items())), digest(out_path)


def load_gold(lock_path: str, data_root: Path, ids: set) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split

    gold = {}
    for record in load_slurp_split(load_lock(Path(lock_path)), data_root, "train", workers=4):
        if record.sample_id in ids:
            gold[record.sample_id] = {"intent": h16(f"{record.scenario}_{record.action}"),
                                      "entities": [(e.type, h16(e.filler)) for e in record.entities]}
    return gold


def load_delivered_plain(data_root: Path, label: str) -> dict:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    run, attempt, _ = ARMS[label]
    rows = {}
    with (data_root / "runs" / run / attempt / f"{run}.outputs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                scenario, action, entities, ok = parse_slu_response(record.get("text") or "")
                rows[record["sample_id"]] = {"delivered_intent": h16(f"{scenario}_{action}") if ok else None,
                                             "delivered": [(e.type, h16(e.filler)) for e in entities]}
    return rows


# ---------------------------------------------------------------------------
# the read


def build(args) -> dict:
    data_root = Path(args.data_root)
    roster = json.loads((REPO_ROOT / ROSTER).read_text(encoding="utf-8"))
    scenario_of = {item["sample_id"]: item["stratum"] for item in roster["items"]}
    ids = sorted(scenario_of)
    scores, inputs = {}, {}
    for label in ARMS:
        scores[label], inputs[label + "_scores"] = load_scores(data_root, label)
    features, trace_checks = {}, {}
    for label in TRACE_ARMS:
        features[label], trace_checks[label], inputs[label + "_outputs"] = extract_arm(data_root, label)
    for label in ("plan", "planr"):
        features[label] = load_delivered_plain(data_root, label)
    for label in ARMS:
        if sorted(features[label]) != ids or sorted(scores[label]) != ids:
            raise ReadError(f"{label}: roster mismatch")
    gold = load_gold(args.lock, data_root, set(ids))
    zero_gold = {s for s in ids if not gold[s]["entities"]}

    # per-row exact accounting, reproduced against the sealed per-sample counts
    acct, structural = {}, {}
    for label in ARMS:
        acct[label], mismatch = {}, 0
        for s in ids:
            item = exact_items(gold[s]["entities"], features[label][s]["delivered"])
            item["intent_ok"] = int(features[label][s]["delivered_intent"] == gold[s]["intent"])
            sealed = scores[label][s]
            mismatch += int((item["tp"], item["fp"], item["fn"]) != (
                sealed["slot_f1_exact_tp"], sealed["slot_f1_exact_fp"], sealed["slot_f1_exact_fn"]))
            mismatch += int(item["intent_ok"] != int(sealed["scenario_action_exact"] == 1.0))
            acct[label][s] = item
        structural[label] = {"rows": len(ids), "exact_or_intent_mismatch_vs_sealed": mismatch,
                             **(trace_checks.get(label) or {})}

    pooled = {}
    for label in ARMS:
        a = acct[label]
        tot = collections.Counter()
        for s in ids:
            tot.update({k: a[s][k] for k in ("tp", "fp", "fn", "emitted", "fp_gold_type", "fp_new_type", "intent_ok")})
            tot["zero_gold_rows_emitting"] += int(s in zero_gold and a[s]["emitted"] > 0)
            tot["fp_on_zero_gold_rows"] += a[s]["fp"] if s in zero_gold else 0
            tot["emitted_on_zero_gold_rows"] += a[s]["emitted"] if s in zero_gold else 0
        tp, fp, fn = slu_totals(scores[label], ids)
        pooled[label] = {**dict(sorted(tot.items())), "official_slu_f1": round(f1(tp, fp, fn), 4),
                         "span_f1_exact": round(f1(tot["tp"], tot["fp"], tot["fn"]), 4),
                         "marginal_pp_per_new_type_fp": round(marginal_pp_per_exact_fp(tp, fp, fn), 5)}

    contrasts = {}
    for left, right, role in CONTRASTS:
        block = {"role": role, "all": contrast(acct[left], acct[right], ids),
                 "zero_gold_rows": contrast(acct[left], acct[right], [s for s in ids if s in zero_gold]),
                 "gold_entity_rows": contrast(acct[left], acct[right], [s for s in ids if s not in zero_gold])}
        block["d_official_slu_f1_pp"] = round(pooled[left]["official_slu_f1"] - pooled[right]["official_slu_f1"], 4)
        block["d_fp_ci95_row_bootstrap"] = paired_boot([acct[left][s]["fp"] - acct[right][s]["fp"] for s in ids])
        block["d_fp_zero_gold_ci95_row_bootstrap"] = paired_boot(
            [acct[left][s]["fp"] - acct[right][s]["fp"] for s in ids if s in zero_gold])
        contrasts[f"{left}-{right}"] = block

    # channel a: the unwrap
    unwrap = collections.Counter()
    for s in ids:
        f = features["comp1"][s]
        unwrap.update(raw_vs_delivered(f["raw"], f["delivered"]))
        unwrap["raw_parse_" + f["raw_parse"]] += 1
        unwrap["normaliser_changed_rows"] += int(f["normaliser_changed"])
        unwrap["projection_v3_filler_changes"] += f["fillers_changed"]
        unwrap["projection_v3_label_changes"] += f["labels_changed"]
        if f["cited_entity_types"] is not None and f["raw"] is not None:
            unwrap["citation_entity_entries"] += len(f["cited_entity_types"])
            unwrap["rows_citation_types_equal_answer_types"] += int(
                f["cited_entity_types"] == sorted(e[0] for e in f["raw"]))
    raw_emission = {}
    for label in TRACE_ARMS:
        c = collections.Counter()
        for s in ids:
            f = features[label][s]
            c.update(raw_vs_delivered(f["raw"], f["delivered"]))
            if f["raw"] is not None and s in zero_gold:
                c["raw_entities_on_zero_gold_rows"] += len(f["raw"])
                c["zero_gold_rows_raw_emitting"] += int(bool(f["raw"]))
        raw_emission[label] = dict(sorted(c.items()))
    for label in ("aa", "agree", "agree_aa"):
        normaliser = collections.Counter()
        for s in ids:
            normaliser["normaliser_changed_rows"] += int(features[label][s]["normaliser_changed"])
        raw_emission[label].update(normaliser)
    raw_emission["comp1"]["normaliser_changed_rows"] = unwrap["normaliser_changed_rows"]

    # per slot type and per scenario
    by_type = collections.defaultdict(dict)
    for label in ("comp1", "aa", "agree", "agree_aa"):
        counter = collections.Counter()
        for s in ids:
            counter.update(acct[label][s]["fp_types"])
        for t, n in counter.items():
            by_type[t][label] = n
    fp_by_type = sorted(
        ({"type": t, **{k: v.get(k, 0) for k in ("comp1", "aa", "agree", "agree_aa")},
          "d_comp1_aa": v.get("comp1", 0) - v.get("aa", 0), "d_agree_agree_aa": v.get("agree", 0) - v.get("agree_aa", 0)}
         for t, v in by_type.items()), key=lambda r: (-r["d_comp1_aa"], r["type"]))
    by_scenario = {}
    for scenario in sorted(set(scenario_of.values())):
        members = [s for s in ids if scenario_of[s] == scenario]
        members_set = set(members)
        c = contrast(acct["comp1"], acct["aa"], members)
        g = contrast(acct["agree"], acct["agree_aa"], members)
        base_tp, base_fp, base_fn = slu_totals(scores["aa"], members)
        arm_tp, arm_fp, arm_fn = slu_totals(scores["comp1"], members)
        by_scenario[scenario] = {
            "rows": len(members), "zero_gold_rows": sum(1 for s in members if s in zero_gold),
            "comp1_minus_aa": c, "agree_minus_agree_aa": g,
            "slu_f1_aa": round(f1(base_tp, base_fp, base_fn), 2), "slu_f1_comp1": round(f1(arm_tp, arm_fp, arm_fn), 2),
            "pooled_slu_f1_if_scenario_rows_swapped_to_aa": round(
                f1(*slu_totals(scores["comp1"], ids, scores["aa"], members_set)), 4)}

    # channel c: shortlist and supply identity splits
    def split(left: str, right: str) -> dict:
        out = {}
        for s in ids:
            fl, fr = features[left][s], features[right][s]
            keys = {"shortlist_identical": fl["shortlist"] is not None and fl["shortlist"] == fr["shortlist"],
                    "solver_supply_identical": fl["supply"] is not None and fl["supply"] == fr["supply"],
                    "slot_contracts_identical": fl["supply"] is not None and fr["supply"] is not None
                    and fl["supply"]["slot-contracts"] == fr["supply"]["slot-contracts"],
                    "exemplars_identical": fl["supply"] is not None and fr["supply"] is not None
                    and fl["supply"]["train-exemplars"] == fr["supply"]["train-exemplars"],
                    "delivered_intent_same": fl["delivered_intent"] == fr["delivered_intent"]}
            for key, value in keys.items():
                bucket = out.setdefault(key, {}).setdefault(str(value).lower(), collections.Counter())
                bucket["rows"] += 1
                bucket["zero_gold_rows"] += int(s in zero_gold)
                for k in ("fp", "tp", "emitted"):
                    bucket["d_" + k] += acct[left][s][k] - acct[right][s][k]
                if s in zero_gold:
                    bucket["d_fp_zero_gold"] += acct[left][s]["fp"] - acct[right][s]["fp"]
        return {k: {kk: dict(vv) for kk, vv in sorted(v.items())} for k, v in sorted(out.items())}

    splits = {f"{l}-{r}": split(l, r) for l, r in (("comp1", "aa"), ("comp1", "agree"), ("agree", "aa"),
                                                    ("agree", "agree_aa"), ("aa", "agree_aa"))}

    # pp conversion and counterfactual swaps
    t = slu_totals(scores["comp1"], ids)
    more_rows = {s for s in ids if acct["comp1"][s]["emitted"] > acct["aa"][s]["emitted"]}
    swaps = {
        "comp1_as_flown": round(f1(*t), 4),
        "aa_as_flown": round(f1(*slu_totals(scores["aa"], ids)), 4),
        "comp1_zero_gold_rows_swapped_to_aa": round(f1(*slu_totals(scores["comp1"], ids, scores["aa"], zero_gold)), 4),
        "comp1_gold_entity_rows_swapped_to_aa": round(
            f1(*slu_totals(scores["comp1"], ids, scores["aa"], set(ids) - zero_gold)), 4),
        "comp1_rows_emitting_more_than_aa_swapped_to_aa": round(
            f1(*slu_totals(scores["comp1"], ids, scores["aa"], more_rows)), 4),
        "rows_emitting_more_than_aa": len(more_rows),
    }
    conversion = {
        "marginal_pp_per_new_type_fp_at_comp1_totals": round(marginal_pp_per_exact_fp(*t), 5),
        "marginal_pp_per_new_type_fp_at_aa_totals": round(marginal_pp_per_exact_fp(*slu_totals(scores["aa"], ids)), 5),
        "note": "one exact FP whose type is absent from the row's gold adds 1.0 to both the word and char FP sums",
    }

    # audio rows: transitions and listing (ids and counts only)
    audio = [s for s in ids if scenario_of[s] == "audio"]
    transitions = collections.Counter()
    listing = []
    for s in audio:
        a, b = acct["aa"][s], acct["comp1"][s]
        transitions[f"gold_entities={'yes' if gold[s]['entities'] else 'no'} aa_emitted={a['emitted']} comp1_emitted={b['emitted']}"] += 1
        if b["fp"] != a["fp"] or b["tp"] != a["tp"]:
            listing.append({"sample_id": s, "gold_entities": len(gold[s]["entities"]),
                            "aa": {"emitted": a["emitted"], "tp": a["tp"], "fp": a["fp"], "fp_types": sorted(a["fp_types"])},
                            "comp1": {"emitted": b["emitted"], "tp": b["tp"], "fp": b["fp"], "fp_types": sorted(b["fp_types"])},
                            "intent_ok_aa": a["intent_ok"], "intent_ok_comp1": b["intent_ok"],
                            "shortlist_identical": features["comp1"][s]["shortlist"] == features["aa"][s]["shortlist"]})
    audio_types = {label: dict(sorted(collections.Counter(
        t for s in audio for t in acct[label][s]["fp_types"]).items())) for label in ("comp1", "aa", "agree", "agree_aa")}
    audio_block = {"rows": len(audio), "zero_gold_rows": sum(1 for s in audio if s in zero_gold),
                   "transitions": dict(sorted(transitions.items())), "fp_types": audio_types,
                   "changed_rows": listing}

    # task 2: PLAN-correct intent harms
    plan_ok = [s for s in ids if acct["plan"][s]["intent_ok"]]
    harms = {}
    for arm in ("comp1", "agree"):
        rows_ = {}
        for s in plan_ok:
            for lab in (arm, "aa"):
                if not acct[lab][s]["intent_ok"]:
                    same = features[arm][s]["shortlist"] == features["aa"][s]["shortlist"]
                    sl = features[lab][s]["shortlist"] or []
                    rows_.setdefault(lab, collections.Counter()).update({
                        "wrong": 1, "shortlist_identical_arm_vs_aa": int(same),
                        "gold_in_own_shortlist": int(gold[s]["intent"] in sl),
                        "delivered_in_own_shortlist": int(features[lab][s]["delivered_intent"] in sl),
                        "delivered_is_own_rank1": int(bool(sl) and features[lab][s]["delivered_intent"] == sl[0])})
        both = [s for s in plan_ok if not acct[arm][s]["intent_ok"] and not acct["aa"][s]["intent_ok"]]
        only_arm = [s for s in plan_ok if not acct[arm][s]["intent_ok"] and acct["aa"][s]["intent_ok"]]
        only_aa = [s for s in plan_ok if acct[arm][s]["intent_ok"] and not acct["aa"][s]["intent_ok"]]

        def shortlist_split(rows__):
            same = [s for s in rows__ if features[arm][s]["shortlist"] == features["aa"][s]["shortlist"]]
            return {"rows": len(rows__), "shortlist_identical": len(same),
                    "shortlist_identical_rows": sorted(same)}
        harms[arm] = {"plan_correct_rows": len(plan_ok), "by_arm": {k: dict(v) for k, v in rows_.items()},
                      "wrong_in_both": len(both), "wrong_only_in_arm": shortlist_split(only_arm),
                      "wrong_only_in_aa": shortlist_split(only_aa)}
    # Solver intent flips on rows whose shortlist is identical, against the null pairs
    flips = {}
    for left, right in (("comp1", "aa"), ("agree", "aa"), ("aa", "agree_aa"), ("comp1", "agree")):
        c = collections.Counter()
        for s in ids:
            fl, fr = features[left][s], features[right][s]
            if fl["shortlist"] is None or fl["shortlist"] != fr["shortlist"]:
                continue
            c["rows_shortlist_identical"] += 1
            if fl["delivered_intent"] != fr["delivered_intent"]:
                c["delivered_intent_differs"] += 1
                c["to_gold"] += int(fl["delivered_intent"] == gold[s]["intent"])
                c["from_gold"] += int(fr["delivered_intent"] == gold[s]["intent"])
            sl = fl["shortlist"]
            c["left_picks_rank1"] += int(bool(sl) and fl["delivered_intent"] == sl[0])
            c["right_picks_rank1"] += int(bool(sl) and fr["delivered_intent"] == sl[0])
        flips[f"{left}-{right}"] = dict(sorted(c.items()))

    # mechanism probe: what COMP-1's entities cite, and whether an FP's type is a supplied slot contract
    mechanism = {}
    for label in ("comp1", "aa", "agree", "agree_aa"):
        c = collections.Counter()
        for s in ids:
            f, item = features[label][s], acct[label][s]
            contracts = set(f["contract_types"] or ())
            for t in item["fp_types"]:
                key = "zero_gold_row" if s in zero_gold else "gold_entity_row"
                c[f"fp_{key}"] += 1
                c[f"fp_{key}_type_is_supplied_slot_contract"] += int(t in contracts)
            c["rows"] += 1
            c["supplied_slot_contract_types"] += len(contracts)
        mechanism[label] = dict(sorted(c.items()))
    cite = collections.Counter()
    for s in ids:
        f, item = features["comp1"][s], acct["comp1"][s]
        if f["cited_entities"] is None:
            continue
        entries = collections.defaultdict(list)
        for t, stores in f["cited_entities"]:
            entries[t].append(stores)
        fp_left = collections.Counter(item["fp_types"])
        for t, _filler in f["delivered"]:
            kind = "fp" if fp_left[t] > 0 else "tp"
            if kind == "fp":
                fp_left[t] -= 1
            stores = entries[t].pop(0) if entries.get(t) else None
            label_ = "no-entry" if stores is None else ("empty" if not stores else "+".join(stores))
            cite[f"{kind}:{label_}"] += 1
    mechanism["comp1_entity_citation_sources"] = dict(sorted(cite.items()))

    template_diff = {
        "a_a_solver_template": "configs/probes/slurp_native_role_solver_v2.txt",
        "comp1_solver_template": "configs/probes/slurp_native_role_solver_cited_v1.txt",
        "a_a_sha256": digest(REPO_ROOT / "configs/probes/slurp_native_role_solver_v2.txt"),
        "comp1_sha256": digest(REPO_ROOT / "configs/probes/slurp_native_role_solver_cited_v1.txt"),
        "comp1_template_mentions_candidate_count": bool(re.search(
            r"min_candidates|at least \w+ candidates", (REPO_ROOT / "configs/probes/slurp_native_role_solver_cited_v1.txt")
            .read_text(encoding="utf-8"))),
    }

    return {
        "schema": SCHEMA, "read_id": READ_ID,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "boundary": "TRAIN Fold A development numbers (owner decisions 28 and 86); DESCRIPTIVE; ids, counts, "
                    "slot type names, scenario names, rates and hashes only",
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer_subprocess": 0,
                     "tokenizer": 0, "gpu": 0, "network": 0},
        "inputs_sha256": dict(sorted(inputs.items())),
        "roster": {"relpath": ROSTER, "rows": len(ids), "zero_gold_rows": len(zero_gold)},
        "structural": structural,
        "pooled": pooled,
        "contrasts": contrasts,
        "channel_a_unwrap": dict(sorted(unwrap.items())),
        "channel_b_raw_emission": raw_emission,
        "fp_by_slot_type": fp_by_type,
        "by_scenario": by_scenario,
        "channel_c_splits": splits,
        "pp_conversion": conversion,
        "counterfactual_swaps_official_slu_f1": swaps,
        "audio": audio_block,
        "intent_harms_on_plan_correct_rows": harms,
        "intent_flips_on_identical_shortlists": flips,
        "solver_template": template_diff,
        "mechanism_probe": mechanism,
    }


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the committed report")
    args = parser.parse_args(argv)
    text = json.dumps(build(args), indent=1, sort_keys=True) + "\n"
    path = REPO_ROOT / REPORT
    if args.check:
        same = strip_time(path.read_text(encoding="utf-8")) == strip_time(text)
        print("check:", "IDENTICAL apart from generated_at" if same else "DIFFERS")
        return 0 if same else 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print("wrote", path, hashlib.sha256(strip_time(text).encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
