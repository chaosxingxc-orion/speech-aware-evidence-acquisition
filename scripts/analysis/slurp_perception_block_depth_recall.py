#!/usr/bin/env python3
"""SLURP Perception boundary block: depth, recall and note behaviour (offline, DESCRIPTIVE).

Read id ``SAEA-SLURP-PERCEPTION-BLOCK-DEPTH-RECALL-OFFLINE-V1``. Model-free: zero model, server,
tokenizer, encoder, embedder, GPU, network and paid-API contacts; no official-scorer subprocess
(the per-row official scores are read from the sealed score files); ``core.flight.cli`` and
``lease_cli`` are never invoked. Gold enters only offline through the governed TRAIN loader
(``data.slurp.load_slurp_split``). Utterance text, transcripts, slot fillers, note text and model
output are never printed or persisted: only ids, intent labels (closed label set), counts, ranks,
rates, AUCs, pp and hashes.

Four questions (the coordinator's brief after P-SV-3, 2026-09-30):

1. **Shorter block (retrieval side).** For AGREE and COMP-1b (TRAIN Fold A) and P-SV-1's
   delivering branch ``a-agree`` (TRAIN Fold B), the boundary block is recomputed at depths
   3/4/5/6/8/12 through the production constructor (``rails.phase_supply._provider_factory``, the
   flown ``fuse_coverage`` with ``m = top_l = d``) from the pinned sealed vectors and agreement
   table. The depth-8 block must equal the sealed block on every row, and the depth-12 block on
   Fold B must equal P-SV-3's sealed ``b-depth`` supply on every row. Reported: gold-in-block,
   gold rank inside the block, the retrieval ceiling on the in-block-not-in-note intent-wrong
   rows, and the recall cost of truncation. The score profile asks whether a score or margin cut
   separates gold from non-gold at a given block position (AUC by position) and evaluates two
   variable-depth rules cross-fitted by sha256(utterance id) halves.
2. **Off-block recall.** Gold's fused rank under five keys (description cosine, description +
   agreement = AGREE, centroid cosine, centroid + agreement = COMP-1b, exemplar vote = the
   agreement table alone) on the off-block rows, entry into the top 8 / 12 / 20, the dominant
   gold intents, and the net-row effect of each key at depth 8 over all rows.
3. **Note behaviour vs depth.** P-SV-3's sealed branch records (``a-agree`` depth 8,
   ``b-depth`` depth 12, ``t-twin`` depth 8): note length, P(gold in note | gold in block) by
   block rank, and the block ranks of the rows ``b-depth`` dropped.
4. **Solver-side contrast.** P-SV-1's level-2 columns: the rank-2 conversions (41.5 % vs 19.5 %)
   as paired row counts, what the ``b-top2contrast`` Solver actually received, and whether the
   effect survives on rows where both notes put gold at rank 2.

``--check`` re-derives both outputs and compares them with the written files apart from
``generated_at``.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import math
import pickle
import re
import sys
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-PERCEPTION-BLOCK-DEPTH-RECALL-OFFLINE-V1"
RECIPE = "slurp-perception-block-depth-recall-offline-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
SCORER = "slurp-slu-official-train"
ROWS = 1080
FLOWN_D = 8
DEPTHS = (3, 4, 5, 6, 8, 12)
SWEEP_DEPTHS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
CAP = 12
ENTRY_CUTS = (8, 12, 20)
IB_VALUE_PREFIX = "intent-boundaries::intent-boundary:"
IB_FACET_MARK = "intent-boundary:"
BOOT_DRAWS = 10_000
BOOT_SEED = 20260929
GRID_Q = tuple(round(0.05 * i, 2) for i in range(1, 20))

CFG_AGREE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
CFG_COMP1B = "configs/baseline/slurp-native-stage3-comp1b-fold-a-baseline-v1.json"
CFG_PSV1 = "configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1-resume.json"
CFG_PSV3 = "configs/baseline/slurp-native-stage3-psv3-fold-b-baseline-v1.json"

RUN_AGREE = ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1")
RUN_COMP1B = ("SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1", "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1")
RUN_PSV1 = ("SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1", "attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only")
RUN_PSV3 = ("SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1", "attempt-slurp-native-stage3-psv3-fold-b-generation-v1")

#: retrieval keys: (facet source config, rank weights). "vote" is the agreement table alone.
KEYS = ("desc_cos", "desc_agree", "cent_cos", "cent_agree", "vote")
KEY_TITLES = {
    "desc_cos": "description key, cosine only (the raw speech key before rank_weights)",
    "desc_agree": "description key + agreement (AGREE, flown on Fold A and in P-SV)",
    "cent_cos": "centroid key, cosine only",
    "cent_agree": "centroid key + agreement (COMP-1b)",
    "vote": "exemplar vote (agreement share alone; zero-share intents unranked)",
}


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
# pure functions (unit-tested on fakes)


def rank_of(order, item):
    """1-based rank of ``item`` in ``order`` or ``None``."""
    for i, x in enumerate(order):
        if x == item:
            return i + 1
    return None


def dedupe(ids) -> list:
    return list(dict.fromkeys(i for i in ids if isinstance(i, str) and i))


def strip_value(value_id: str) -> str:
    """``intent-boundaries::intent-boundary:<intent>`` or ``intent-boundary:<intent>`` -> ``<intent>``."""
    return value_id.split(IB_FACET_MARK, 1)[-1]


def auc(scores, labels):
    """P(score of a positive > score of a negative), ties one half (Mann-Whitney). ``None`` if degenerate."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    allv = sorted((s, i) for i, s in enumerate(scores))
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[allv[k][1]] = avg
        i = j + 1
    rpos = sum(r for r, y in zip(ranks, labels) if y)
    npos, nneg = len(pos), len(neg)
    return (rpos - npos * (npos + 1) / 2.0) / (npos * nneg)


def split_half(utterance_id: str) -> int:
    """The supply-abstention read's utterance half (sha256 of the utterance id, mod 2)."""
    return int(hashlib.sha256(str(utterance_id).encode("utf-8")).hexdigest(), 16) % 2


def quantile(values, q: float) -> float:
    xs = sorted(values)
    pos = q * (len(xs) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def bucket(rank) -> str:
    if rank is None:
        return "not recalled"
    if rank <= 8:
        return "1-8"
    if rank <= 12:
        return "9-12"
    if rank <= 20:
        return "13-20"
    return "21-60"


def variable_depth(scores, rule: str, delta: float, cap: int = CAP) -> int:
    """Depth of a variable block over a descending score list.

    ``gap``: keep every item within ``delta`` of the top score (at least 1, at most ``cap``).
    ``cliff``: stop after the first position whose drop to the next item is >= ``delta``
    ("deliver until the margin drops"; at least 1, at most ``cap``).
    """
    s = list(scores)[:cap + 1]
    if not s:
        return 0
    if rule == "gap":
        return max(1, sum(1 for x in s[:cap] if s[0] - x <= delta))
    if rule == "cliff":
        for p in range(min(cap, len(s))):
            if p + 1 < len(s) and s[p] - s[p + 1] >= delta:
                return p + 1
        return min(cap, len(s))
    raise ValueError(rule)


def depth_rows(pool_rows: dict, depths=DEPTHS, ref: int = FLOWN_D) -> list:
    """Per depth: gold-in-block rows, rank histogram inside the block, target coverage and the
    truncation cost against the reference depth.

    ``pool_rows``: sid -> {"rank": fused gold rank or None, "on_note": bool, "correct": bool,
    "target": bool (intent-wrong, gold off the note, gold in the reference block)}.
    """
    out = []
    for d in depths:
        inb = {s for s, r in pool_rows.items() if r["rank"] is not None and r["rank"] <= d}
        ref_in = {s for s, r in pool_rows.items() if r["rank"] is not None and r["rank"] <= ref}
        lost = ref_in - inb
        gained = inb - ref_in
        hist = Counter(pool_rows[s]["rank"] for s in inb)
        out.append({
            "d": d,
            "gold_in_block": len(inb),
            "gold_in_block_pct": round(100.0 * len(inb) / len(pool_rows), 2) if pool_rows else 0.0,
            "rank_hist": {str(k): hist[k] for k in sorted(hist)},
            "targets_in_block": sum(1 for s in inb if pool_rows[s]["target"]),
            "targets_total": sum(1 for r in pool_rows.values() if r["target"]),
            "lost_vs_ref": len(lost),
            "lost_vs_ref_note_had_gold": sum(1 for s in lost if pool_rows[s]["on_note"]),
            "lost_vs_ref_delivered_correct": sum(1 for s in lost if pool_rows[s]["correct"]),
            "gained_vs_ref": len(gained),
            "gained_vs_ref_intent_wrong": sum(1 for s in gained if not pool_rows[s]["correct"]),
        })
    return out


def note_given_block_rank(pool_rows: dict, max_rank: int) -> dict:
    """P(gold on the note | gold at block rank r), r = 1..max_rank, plus 'off block'."""
    out = {}
    for r in list(range(1, max_rank + 1)) + ["off"]:
        sel = [x for x in pool_rows.values()
               if (x["block_rank"] == r if r != "off" else x["block_rank"] is None)]
        n = len(sel)
        k = sum(1 for x in sel if x["on_note"])
        out[str(r)] = {"rows": n, "on_note": k, "pct": round(100.0 * k / n, 2) if n else None}
    return out


def variable_sweep(scores_by_row: dict, gold_rank: dict, targets: set, rule: str, deltas) -> list:
    out = []
    ids = sorted(scores_by_row)
    for delta in deltas:
        depth = {s: variable_depth(scores_by_row[s], rule, delta) for s in ids}
        inb = [s for s in ids if gold_rank[s] is not None and gold_rank[s] <= depth[s]]
        out.append({"rule": rule, "delta": round(delta, 6), "mean_depth": round(sum(depth.values()) / len(ids), 3),
                    "gold_in_block": len(inb), "targets_in_block": sum(1 for s in inb if s in targets)})
    return out


def crossfit_variable(scores_by_row: dict, gold_rank: dict, half: dict, rule: str, deltas, ref: int = FLOWN_D) -> dict:
    """On each half choose the delta with the smallest mean depth whose in-half gold-in-block count
    is at least the fixed-``ref`` count on that half; apply it to the other half."""
    chosen, applied = {}, {}
    for h in (0, 1):
        own = {s: v for s, v in scores_by_row.items() if half[s] == h}
        fixed = sum(1 for s in own if gold_rank[s] is not None and gold_rank[s] <= ref)
        best = None
        for delta in deltas:
            depth = {s: variable_depth(own[s], rule, delta) for s in own}
            rec = sum(1 for s in own if gold_rank[s] is not None and gold_rank[s] <= depth[s])
            md = sum(depth.values()) / len(own)
            if rec >= fixed and (best is None or md < best[1] - 1e-12):
                best = (delta, md)
        chosen[h] = None if best is None else best[0]
    total_depth, rec, fixed_rec, n = 0, 0, 0, 0
    for h in (0, 1):
        delta = chosen[1 - h]
        other = [s for s in scores_by_row if half[s] == h]
        for s in other:
            d = ref if delta is None else variable_depth(scores_by_row[s], rule, delta)
            total_depth += d
            rec += int(gold_rank[s] is not None and gold_rank[s] <= d)
            fixed_rec += int(gold_rank[s] is not None and gold_rank[s] <= ref)
            n += 1
        applied[h] = delta
    return {"rule": rule, "delta_chosen_on_half": {str(k): (None if v is None else round(v, 6)) for k, v in chosen.items()},
            "out_of_half_mean_depth": round(total_depth / n, 3) if n else None,
            "out_of_half_gold_in_block": rec, "fixed_ref_gold_in_block": fixed_rec, "rows": n}


def crossfit_budget(scores_by_row: dict, gold_rank: dict, half: dict, rule: str, deltas, budget: float) -> dict:
    """On each half choose the delta with the highest in-half gold-in-block count whose in-half mean
    depth is <= ``budget``; apply it to the other half. Compared with the fixed depth floor(budget)."""
    chosen = {}
    for h in (0, 1):
        own = [s for s in scores_by_row if half[s] == h]
        best = None
        for delta in deltas:
            depth = {s: variable_depth(scores_by_row[s], rule, delta) for s in own}
            md = sum(depth.values()) / len(own)
            rec = sum(1 for s in own if gold_rank[s] is not None and gold_rank[s] <= depth[s])
            if md <= budget and (best is None or rec > best[1]):
                best = (delta, rec)
        chosen[h] = None if best is None else best[0]
    total_depth, rec, n = 0, 0, 0
    fixed_d = int(math.floor(budget))
    fixed_rec = 0
    for h in (0, 1):
        delta = chosen[1 - h]
        for s in (x for x in scores_by_row if half[x] == h):
            d = fixed_d if delta is None else variable_depth(scores_by_row[s], rule, delta)
            total_depth += d
            rec += int(gold_rank[s] is not None and gold_rank[s] <= d)
            fixed_rec += int(gold_rank[s] is not None and gold_rank[s] <= fixed_d)
            n += 1
    return {"rule": rule, "budget_mean_depth": budget,
            "delta_chosen_on_half": {str(k): (None if v is None else round(v, 6)) for k, v in chosen.items()},
            "out_of_half_mean_depth": round(total_depth / n, 3) if n else None,
            "out_of_half_gold_in_block": rec, "fixed_depth": fixed_d, "fixed_depth_gold_in_block": fixed_rec}


def entry_counts(ranks: dict, rows, cuts=ENTRY_CUTS) -> dict:
    rows = list(rows)
    out = {"rows": len(rows), "buckets": dict(sorted(Counter(bucket(ranks[s]) for s in rows).items()))}
    for c in cuts:
        out[f"top{c}"] = sum(1 for s in rows if ranks[s] is not None and ranks[s] <= c)
    return out


def net_rows(base_rank: dict, alt_rank: dict, flags: dict, d: int = FLOWN_D) -> dict:
    """Rows whose gold enters / leaves the depth-``d`` block when the key changes.
    ``flags``: sid -> {"correct": bool, "on_note": bool}."""
    enters = [s for s in base_rank if not _in(base_rank[s], d) and _in(alt_rank[s], d)]
    leaves = [s for s in base_rank if _in(base_rank[s], d) and not _in(alt_rank[s], d)]
    return {"enters": len(enters), "leaves": len(leaves), "net": len(enters) - len(leaves),
            "enters_intent_wrong": sum(1 for s in enters if not flags[s]["correct"]),
            "leaves_delivered_correct": sum(1 for s in leaves if flags[s]["correct"]),
            "leaves_note_had_gold": sum(1 for s in leaves if flags[s]["on_note"]),
            "gold_in_block_base": sum(1 for s in base_rank if _in(base_rank[s], d)),
            "gold_in_block_alt": sum(1 for s in alt_rank if _in(alt_rank[s], d))}


def _in(rank, d: int) -> bool:
    return rank is not None and rank <= d


def paired_boot(diffs: list, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> list:
    """Percentile CI95 of the mean of paired per-row differences (row bootstrap)."""
    import numpy as np

    x = np.asarray(diffs, dtype=float)
    if len(x) == 0:
        return [None, None]
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), (draws, len(x)))].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)]


def pick_class(pick, note: list, gold: str) -> str:
    if pick is None:
        return "unparsed"
    if pick == gold:
        return "gold"
    if note and pick == note[0]:
        return "note rank 1 (not gold)"
    if pick in note:
        return "other note candidate"
    return "off the note"


# ---------------------------------------------------------------------------
# I/O


def build(args) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot, QueryState
    from speech_aware_evidence_acquisition.rails.phase_supply import (
        _provider_factory, load_phase_supply_specs, load_sealed_agreement, load_sealed_segment_vectors,
        load_sealed_vectors)
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    BR = import_path(REPO_ROOT / "scripts/analysis/slurp_perception_branch_read.py", "slurp_perception_branch_read")
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    records = load_slurp_split(lock, data_root, "train", workers=4)
    gold = {r.sample_id: r.intent for r in records}
    utt = {r.sample_id: r.utterance_id for r in records}
    del records
    files = {}

    def note_ids_from_content(content):
        try:
            payload = json.loads(content or "")
            return dedupe(str(c.get("intent_id")) for c in payload.get("candidates") or ())
        except (ValueError, AttributeError, TypeError):
            return []

    def load_run_phases(run):
        run_id, attempt = run
        path = data_root / "runs" / run_id / attempt / f"{run_id}.phases.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        files[str(path.relative_to(data_root))] = digest(path)
        rows = {}
        for res in doc["phases"][0]["results"]:
            note = []
            for st in res.get("agent_states") or ():
                if st.get("state_kind") == "phase:perception":
                    note = note_ids_from_content(st.get("content"))
                    break
            block = [strip_value(v) for v in res["initial_query_state"]["retrieved_value_ids"] if IB_FACET_MARK in v]
            rows[res["sample_id"]] = {"note": note, "block": block}
        del doc
        return rows

    def load_scores(path):
        block = json.loads(path.read_text(encoding="utf-8"))[SCORER]
        files[str(path.relative_to(data_root))] = digest(path)
        return {str(s["sample_id"]): bool(s["scenario_action_exact"] >= 1.0) for s in block["per_sample"]}, \
            block["aggregate"]["official"]["intent_accuracy"]

    def load_branch_rows(run):
        run_id, attempt = run
        path = data_root / "runs" / run_id / attempt / f"{run_id}.outputs.jsonl"
        files[str(path.relative_to(data_root))] = digest(path)
        out = {}
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                rec = row["native_episode_receipt"]["perception_branches"]
                br = {}
                for item in rec["branches"]:
                    br[item["branch_id"]] = {
                        "note": list(BR.branch_candidates(item)),
                        "supplied": [strip_value(v) for v in item.get("supplied_value_ids") or ()],
                        "solver_supply": list(item.get("candidate_supply_value_ids") or ()),
                        "presentation_skip_reason": item.get("presentation_skip_reason"),
                        "contrast_rendered": item.get("contrast_block_sha256") is not None,
                        "solver_request_sha256": item.get("solver_request_sha256"),
                    }
                out[row["sample_id"]] = {"branches": br, "delivered": rec.get("delivered_branch_id"),
                                         "level": rec.get("level")}
        return out

    def load_first_visit(run, arm):
        run_id, attempt = run
        path = data_root / "runs" / run_id / attempt / "supply-variants" / f"arm-{arm}-first-visit-outputs.jsonl"
        files[str(path.relative_to(data_root))] = digest(path)
        picks = {}
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                sc, ac, _ents, parsed = parse_slu_response(r.get("text") or "")
                picks[r["sample_id"]] = f"{sc}_{ac}" if parsed and sc is not None and ac is not None else None
        return picks

    # ---- retrieval: production constructor, five keys, depth sweep on the flown keys
    def base_spec(cfg_rel):
        cfg = json.loads((REPO_ROOT / cfg_rel).read_text(encoding="utf-8"))
        store = cfg["knowledge_stores"]["intent-boundaries"]
        spec = load_phase_supply_specs({"phase_supply": store["phase_supply"]}, default_phase_program(cfg["policy"]))["perception"]
        return spec, store

    agree_spec, agree_store = base_spec(CFG_AGREE)
    comp1b_spec, _ = base_spec(CFG_COMP1B)
    psv1_spec, psv1_store = base_spec(CFG_PSV1)
    psv3_spec, _ = base_spec(CFG_PSV3)
    snap_json = json.loads((data_root / agree_store["snapshot"]["relpath"]).read_text(encoding="utf-8"))
    snap = KnowledgeSnapshot.from_frozen_json(snap_json)
    if snap.content_hash() != agree_store["snapshot"]["sha256"] or psv1_store["snapshot"]["sha256"] != agree_store["snapshot"]["sha256"]:
        raise ReadError("boundary snapshot pin mismatch")
    facet_ids = sorted(f.facet_id for f in snap.facets)
    files[agree_store["snapshot"]["relpath"]] = agree_store["snapshot"]["sha256"]
    for src in (agree_spec.facet_source, comp1b_spec.facet_source):
        files[src["relpath"]] = src["sha256"]
    for rel in (CFG_AGREE, CFG_COMP1B, CFG_PSV1, CFG_PSV3):
        files["repo:" + rel] = digest(REPO_ROOT / rel)
    checks = Counter()
    for a, b, name in ((agree_spec, psv1_spec, "psv1"), (agree_spec, psv3_spec, "psv3"), (agree_spec, comp1b_spec, "comp1b")):
        for fld in ("rank_policy", "fuse_policy", "k", "tau", "dimensions", "rank_weights", "fuse_coverage"):
            checks[f"{name}_spec_equals_agree_on_{fld}"] += int(getattr(a, fld) == getattr(b, fld))
    checks["psv1_facets_equal_agree_facets"] = int(psv1_spec.facet_source["sha256"] == agree_spec.facet_source["sha256"])
    checks["comp1b_facets_are_centroid"] = int(comp1b_spec.facet_source["sha256"] != agree_spec.facet_source["sha256"])

    vec_cache = {}

    def vectors(source, spec):
        key = source["sha256"]
        if key not in vec_cache:
            vec_cache[key] = load_sealed_vectors(data_root / source["relpath"], expected_sha256=source["sha256"],
                                                 dimensions=spec.dimensions)
            files[source["relpath"]] = source["sha256"]
        return vec_cache[key]

    def fold_inputs(spec):
        q = load_sealed_segment_vectors(data_root / spec.query_source["relpath"], expected_sha256=spec.query_source["sha256"],
                                        dimensions=spec.dimensions)
        agr = load_sealed_agreement(data_root / spec.agreement_source["relpath"], expected_sha256=spec.agreement_source["sha256"],
                                    dimension="agreement:exemplar-intent", facet_ids=facet_ids)
        files[spec.query_source["relpath"]] = spec.query_source["sha256"]
        files[spec.agreement_source["relpath"]] = spec.agreement_source["sha256"]
        return q, agr

    def rank_rows(spec, facet_src, weights, qvec, agr, ids, depths=()):
        """sid -> {"order": [intent...], "scores": [...], "blocks": {d: [intent...]}}"""
        s = replace(spec, facet_source=facet_src, rank_weights=weights)
        fvec = vectors(facet_src, s)
        use_agr = agr if float(weights.get("w_agree", 0.0)) > 0 else None
        factories = {None: _provider_factory(s, snapshot=snap, snapshot_sha256=snap.content_hash(), facet_vectors=fvec,
                                             provider_for_phase=None, agreement_scores=use_agr)}
        for d in depths:
            cov = dict(s.fuse_coverage or {})
            cov.update({"m": d, "top_l": d})
            factories[d] = _provider_factory(replace(s, fuse_coverage=cov), snapshot=snap, snapshot_sha256=snap.content_hash(),
                                             facet_vectors=fvec, provider_for_phase=None, agreement_scores=use_agr)
        out = {}
        for sid in ids:
            state = QueryState(query_id=f"block-depth-read:perception:{sid}", query_sample_id=sid,
                               speech_packet_id=f"block-depth-read:{sid}", speech_packet_sha256="0" * 64,
                               use_split_identity_hash="0" * 64).validate()
            row = {"blocks": {}}
            for d, factory in factories.items():
                provider = factory()
                rk = provider.candidates({"query_state": state, "query_segments": qvec[sid].segments}, k=s.k)
                if d is None:
                    rr = provider.last_rank_result()
                    row["order"] = [str(c.facet_id).split(IB_FACET_MARK, 1)[-1] for c in rr.candidates]
                    row["scores"] = [float(c.score) for c in rr.candidates]
                else:
                    dec = provider.fuse([rk], k=s.k, policy_id=s.fuse_policy)
                    row["blocks"][d] = [strip_value(v) for v in dec.selected_value_ids]
            out[sid] = row
        return out

    def vote_order(agr, sid):
        shares = agr.get(sid, {})
        items = sorted(((v, str(f).split(IB_FACET_MARK, 1)[-1]) for f, v in shares.items() if v > 0), key=lambda t: (-t[0], t[1]))
        return [i for _, i in items]

    W_COS = {"w_cos": 1.0, "w_agree": 0.0, "w_prior": 0.0}
    W_AGR = dict(agree_spec.rank_weights)
    cent_src = comp1b_spec.facet_source

    # ---- sealed pools
    agree_ph = load_run_phases(RUN_AGREE)
    comp_ph = load_run_phases(RUN_COMP1B)
    ids_a = sorted(agree_ph)
    if sorted(comp_ph) != ids_a or len(ids_a) != ROWS:
        raise ReadError("Fold A rosters differ")
    run_dir = lambda run: data_root / "runs" / run[0] / run[1]  # noqa: E731
    agree_ok, agree_acc = load_scores(run_dir(RUN_AGREE) / f"{RUN_AGREE[0]}.scores.json")
    comp_ok, comp_acc = load_scores(run_dir(RUN_COMP1B) / f"{RUN_COMP1B[0]}.scores.json")
    psv1 = load_branch_rows(RUN_PSV1)
    psv3 = load_branch_rows(RUN_PSV3)
    ids_b = sorted(psv1)
    if sorted(psv3) != ids_b or len(ids_b) != ROWS:
        raise ReadError("Fold B rosters differ")
    col = {}
    for run, arms in ((RUN_PSV1, ("a-agree", "b-top2contrast", "t-twin")), (RUN_PSV3, ("a-agree", "b-depth", "t-twin"))):
        for arm in arms:
            col[(run[0], arm)] = load_scores(run_dir(run) / "supply-variants" / f"arm-{arm}-{SCORER}-scores.json")
    picks = {arm: load_first_visit(RUN_PSV1, arm) for arm in ("a-agree", "b-top2contrast", "t-twin")}

    # ---- recompute
    qa, agr_a = fold_inputs(agree_spec)
    qb, agr_b = fold_inputs(psv1_spec)
    if comp1b_spec.query_source["sha256"] != agree_spec.query_source["sha256"] or comp1b_spec.agreement_source["sha256"] != agree_spec.agreement_source["sha256"]:
        raise ReadError("COMP-1b query / agreement inputs differ from AGREE's")
    def compute_all():
        out = {"A": {}, "B": {}}
        out["A"]["desc_agree"] = rank_rows(agree_spec, agree_spec.facet_source, W_AGR, qa, agr_a, ids_a, depths=DEPTHS)
        out["A"]["cent_agree"] = rank_rows(agree_spec, cent_src, W_AGR, qa, agr_a, ids_a, depths=DEPTHS)
        out["A"]["desc_cos"] = rank_rows(agree_spec, agree_spec.facet_source, W_COS, qa, agr_a, ids_a)
        out["A"]["cent_cos"] = rank_rows(agree_spec, cent_src, W_COS, qa, agr_a, ids_a)
        out["B"]["desc_agree"] = rank_rows(psv1_spec, psv1_spec.facet_source, W_AGR, qb, agr_b, ids_b, depths=DEPTHS)
        out["B"]["cent_agree"] = rank_rows(psv1_spec, cent_src, W_AGR, qb, agr_b, ids_b)
        out["B"]["desc_cos"] = rank_rows(psv1_spec, psv1_spec.facet_source, W_COS, qb, agr_b, ids_b)
        out["B"]["cent_cos"] = rank_rows(psv1_spec, cent_src, W_COS, qb, agr_b, ids_b)
        return out

    cache = Path(args.cache) if args.cache else None
    if cache is not None and cache.is_file():
        R = pickle.loads(cache.read_bytes())
    else:
        R = compute_all()
        if cache is not None:
            cache.write_bytes(pickle.dumps(R))
    for fold, agr, ids in (("A", agr_a, ids_a), ("B", agr_b, ids_b)):
        R[fold]["vote"] = {sid: {"order": vote_order(agr, sid), "scores": [], "blocks": {}} for sid in ids}

    # custody checks
    for sid in ids_a:
        a, c = R["A"]["desc_agree"][sid], R["A"]["cent_agree"][sid]
        checks["A_desc_agree_d8_equals_sealed_agree_block"] += int(a["blocks"][8] == agree_ph[sid]["block"])
        checks["A_cent_agree_d8_equals_sealed_comp1b_block"] += int(c["blocks"][8] == comp_ph[sid]["block"])
        for pool, rr in (("desc_agree", a), ("cent_agree", c)):
            checks[f"A_{pool}_every_depth_block_is_rank_prefix"] += int(all(rr["blocks"][d] == rr["order"][:len(rr["blocks"][d])] for d in DEPTHS))
            checks[f"A_{pool}_every_depth_block_full_width"] += int(all(len(rr["blocks"][d]) == d for d in DEPTHS))
    for sid in ids_b:
        b = R["B"]["desc_agree"][sid]
        br1, br3 = psv1[sid]["branches"], psv3[sid]["branches"]
        checks["B_desc_agree_d8_equals_psv1_a_supply"] += int(b["blocks"][8] == br1["a-agree"]["supplied"])
        checks["B_desc_agree_d8_equals_psv3_a_supply"] += int(b["blocks"][8] == br3["a-agree"]["supplied"])
        checks["B_desc_agree_d12_equals_psv3_b_depth_supply"] += int(b["blocks"][12] == br3["b-depth"]["supplied"])
        checks["B_desc_agree_every_depth_block_is_rank_prefix"] += int(all(b["blocks"][d] == b["order"][:len(b["blocks"][d])] for d in DEPTHS))
        checks["B_desc_agree_every_depth_block_full_width"] += int(all(len(b["blocks"][d]) == d for d in DEPTHS))
        checks["B_psv1_delivered_branch_is_a"] += int(psv1[sid]["delivered"] == "a-agree")
        checks["B_psv3_delivered_branch_is_a"] += int(psv3[sid]["delivered"] == "a-agree")
    for k in ("A_desc_agree_d8_equals_sealed_agree_block", "A_cent_agree_d8_equals_sealed_comp1b_block",
              "B_desc_agree_d8_equals_psv1_a_supply"):
        if checks[k] < ROWS - 4:
            raise ReadError(f"recomputed block does not reproduce the sealed block: {k}={checks[k]}")

    def gold_ranks(fold, key, ids):
        return {s: rank_of(R[fold][key][s]["order"], gold[s]) for s in ids}

    ranks = {f: {k: gold_ranks(f, k, ids) for k in KEYS} for f, ids in (("A", ids_a), ("B", ids_b))}

    # sealed-block rank (the block the model actually saw) for note conversions
    def sealed_block_rank(block, g):
        return rank_of(block, g)

    # ---- Q1 pools
    pools = {}

    def make_pool(name, ids, key_rank, block_of, note_of, ok):
        rows = {}
        for s in ids:
            g = gold[s]
            rnk = key_rank[s]
            on_note = g in note_of(s)
            rows[s] = {"rank": rnk, "block_rank": sealed_block_rank(block_of(s), g), "on_note": on_note,
                       "correct": ok[s], "target": (not ok[s]) and (not on_note) and rnk is not None and rnk <= FLOWN_D}
        pools[name] = rows

    make_pool("agree_fold_a", ids_a, ranks["A"]["desc_agree"], lambda s: agree_ph[s]["block"], lambda s: agree_ph[s]["note"], agree_ok)
    make_pool("comp1b_fold_a", ids_a, ranks["A"]["cent_agree"], lambda s: comp_ph[s]["block"], lambda s: comp_ph[s]["note"], comp_ok)
    psv1_a_ok = col[(RUN_PSV1[0], "a-agree")][0]
    make_pool("psv1_a_fold_b", ids_b, ranks["B"]["desc_agree"], lambda s: psv1[s]["branches"]["a-agree"]["supplied"],
              lambda s: psv1[s]["branches"]["a-agree"]["note"], psv1_a_ok)
    pool_keys = {"agree_fold_a": ("A", "desc_agree", ids_a), "comp1b_fold_a": ("A", "cent_agree", ids_a),
                 "psv1_a_fold_b": ("B", "desc_agree", ids_b)}

    q1 = {}
    for name, rows in pools.items():
        fold, key, ids = pool_keys[name]
        wrong = [s for s in ids if not rows[s]["correct"]]
        repro = {"rows": len(ids), "intent_wrong": len(wrong),
                 "intent_wrong_gold_off_note": sum(1 for s in wrong if not rows[s]["on_note"]),
                 "intent_wrong_gold_off_note_in_block": sum(1 for s in wrong if not rows[s]["on_note"] and _in(rows[s]["rank"], 8)),
                 "intent_wrong_gold_off_note_off_block": sum(1 for s in wrong if not rows[s]["on_note"] and not _in(rows[s]["rank"], 8)),
                 "gold_off_note_in_block_all_rows": sum(1 for s in ids if not rows[s]["on_note"] and _in(rows[s]["rank"], 8)),
                 "note_size_hist": dict(sorted(Counter(str(len((agree_ph if name == 'agree_fold_a' else comp_ph)[s]["note"]) if fold == "A"
                                                         else len(psv1[s]["branches"]["a-agree"]["note"])) for s in ids).items()))}
        # score profile: AUC by position of the gap-to-top and of the successive drop
        prof = {}
        feats_pooled = {"gap_to_top": ([], []), "drop_from_previous": ([], []), "score": ([], [])}
        for p in range(2, CAP + 1):
            gaps, drops, labels = [], [], []
            for s in ids:
                sc = R[fold][key][s]["scores"]
                if len(sc) < p:
                    continue
                gaps.append(sc[0] - sc[p - 1])
                drops.append(sc[p - 2] - sc[p - 1])
                labels.append(rows[s]["rank"] == p)
                feats_pooled["gap_to_top"][0].append(sc[0] - sc[p - 1])
                feats_pooled["drop_from_previous"][0].append(sc[p - 2] - sc[p - 1])
                feats_pooled["score"][0].append(sc[p - 1])
                for f in feats_pooled:
                    feats_pooled[f][1].append(rows[s]["rank"] == p)
            a_gap, a_drop = auc(gaps, labels), auc(drops, labels)
            prof[str(p)] = {"gold_at_position": sum(labels), "items": len(labels),
                            "auc_gap_to_top": None if a_gap is None else round(a_gap, 4),
                            "auc_drop_from_previous": None if a_drop is None else round(a_drop, 4),
                            "median_gap_gold": round(quantile([g for g, y in zip(gaps, labels) if y], 0.5), 4) if sum(labels) else None,
                            "median_gap_nongold": round(quantile([g for g, y in zip(gaps, labels) if not y], 0.5), 4)}
        pooled = {f: round(auc(v[0], v[1]), 4) for f, v in feats_pooled.items()}
        # row-level: is the top-1 minus top-2 margin (or the 8th score) informative about gold position > 3?
        row_top_margin = [(R[fold][key][s]["scores"] + [0.0, 0.0])[0] - (R[fold][key][s]["scores"] + [0.0, 0.0])[1] for s in ids]
        deep = [rows[s]["rank"] is None or rows[s]["rank"] > 3 for s in ids]
        # variable-depth sweeps
        scores_by_row = {s: R[fold][key][s]["scores"] for s in ids}
        gold_rank = {s: rows[s]["rank"] for s in ids}
        targets = {s for s in ids if rows[s]["target"]}
        gaps_all = [sc[0] - x for sc in scores_by_row.values() for x in sc[1:CAP]]
        drops_all = [sc[i] - sc[i + 1] for sc in scores_by_row.values() for i in range(min(CAP, len(sc) - 1))]
        grid_gap = sorted({round(quantile(gaps_all, q), 6) for q in GRID_Q})
        grid_cliff = sorted({round(quantile(drops_all, q), 6) for q in GRID_Q})
        half = {s: split_half(utt[s]) for s in ids}
        fixed_curve = [{"d": d, "gold_in_block": sum(1 for s in ids if _in(gold_rank[s], d)),
                        "targets_in_block": sum(1 for s in targets if _in(gold_rank[s], d))} for d in SWEEP_DEPTHS]
        q1[name] = {
            "fold": fold, "key": key, "reproduction": repro,
            "depth_table": depth_rows(rows, DEPTHS),
            "note_given_block_rank": note_given_block_rank(rows, FLOWN_D),
            "note_catches_gold_at_block_rank_gt_d": {str(d): sum(1 for r in rows.values() if r["on_note"] and r["block_rank"] is not None and r["block_rank"] > d) for d in DEPTHS if d < FLOWN_D},
            "score_profile_by_position": prof,
            "score_profile_pooled_auc_positions_2_12": pooled,
            "row_margin_auc_gold_deeper_than_3": round(auc(row_top_margin, deep), 4),
            "fixed_depth_curve": fixed_curve,
            "variable_gap_sweep": variable_sweep(scores_by_row, gold_rank, targets, "gap", grid_gap),
            "variable_cliff_sweep": variable_sweep(scores_by_row, gold_rank, targets, "cliff", grid_cliff),
            "crossfit_gap": crossfit_variable(scores_by_row, gold_rank, half, "gap", grid_gap),
            "crossfit_cliff": crossfit_variable(scores_by_row, gold_rank, half, "cliff", grid_cliff),
            "crossfit_gap_budget": [crossfit_budget(scores_by_row, gold_rank, half, "gap", grid_gap, b) for b in (5.0, 6.0)],
            "half_sizes": dict(sorted(Counter(str(v) for v in half.values()).items())),
        }

    # ---- Q2 off-block recall
    q2 = {"keys": KEY_TITLES, "sets": {}, "net_rows_at_depth_8": {}, "intent_counts": {}}
    ra = pools["agree_fold_a"]
    set_a34 = [s for s in ids_a if not ra[s]["correct"] and not _in(ra[s]["rank"], 8)]
    set_a40 = [s for s in ids_a if not _in(ra[s]["rank"], 8)]
    set_a34_offnote = [s for s in set_a34 if not ra[s]["on_note"]]
    rc = pools["comp1b_fold_a"]
    set_c_wrong_off = [s for s in ids_a if not rc[s]["correct"] and not _in(rc[s]["rank"], 8)]
    br = lambda s, b: psv3[s]["branches"][b]  # noqa: E731
    absent_a = [s for s in ids_b if gold[s] not in br(s, "a-agree")["note"]]
    absent_b = [s for s in ids_b if gold[s] not in br(s, "b-depth")["note"]]
    rb = ranks["B"]["desc_agree"]
    sets = {
        "A: AGREE intent-wrong, gold off the depth-8 block": ("A", set_a34),
        "A: AGREE all rows, gold off the depth-8 block": ("A", set_a40),
        "A: COMP-1b intent-wrong, gold off its depth-8 block": ("A", set_c_wrong_off),
        "B: P-SV-3 a-agree note absent, gold off the depth-8 block": ("B", [s for s in absent_a if not _in(rb[s], 8)]),
        "B: P-SV-3 a-agree note absent, gold in the depth-8 block": ("B", [s for s in absent_a if _in(rb[s], 8)]),
        "B: P-SV-3 b-depth note absent, gold off the depth-12 block": ("B", [s for s in absent_b if not _in(rb[s], 12)]),
        "B: P-SV-3 b-depth note absent, gold in the depth-12 block": ("B", [s for s in absent_b if _in(rb[s], 12)]),
        "B: P-SV-1 a-agree intent-wrong, gold off the depth-8 block": ("B", [s for s in ids_b if not psv1_a_ok[s] and not _in(rb[s], 8)]),
    }
    q2["checks"] = {"A_intent_wrong_off_block_off_note": len(set_a34_offnote), "A_intent_wrong_off_block": len(set_a34),
                    "B_psv3_a_absent": len(absent_a), "B_psv3_b_absent": len(absent_b)}
    for label, (fold, rows_) in sets.items():
        q2["sets"][label] = {k: entry_counts(ranks[fold][k], rows_) for k in KEYS}
    flags_a = {s: {"correct": agree_ok[s], "on_note": ra[s]["on_note"]} for s in ids_a}
    flags_b = {s: {"correct": psv1_a_ok[s], "on_note": pools["psv1_a_fold_b"][s]["on_note"]} for s in ids_b}
    for fold, flags in (("A", flags_a), ("B", flags_b)):
        q2["net_rows_at_depth_8"][fold] = {k: net_rows(ranks[fold]["desc_agree"], ranks[fold][k], flags) for k in KEYS if k != "desc_agree"}
        # hybrid (not pinned): flown top-6 + the first two new intents of another key
        for other in ("cent_agree", "vote", "cent_cos"):
            hyb = {}
            for s in flags:
                base = R[fold]["desc_agree"][s]["order"][:6]
                extra = [i for i in R[fold][other][s]["order"] if i not in base][:2]
                blk = base + extra
                hyb[s] = rank_of(blk, gold[s])
            q2["net_rows_at_depth_8"][fold][f"hybrid desc_agree top-6 + {other} next 2"] = net_rows(ranks[fold]["desc_agree"], hyb, flags)
    for label in ("A: AGREE intent-wrong, gold off the depth-8 block", "B: P-SV-3 a-agree note absent, gold off the depth-8 block",
                  "B: P-SV-3 b-depth note absent, gold off the depth-12 block"):
        fold, rows_ = sets[label]
        q2["intent_counts"][label] = Counter(gold[s] for s in rows_).most_common(10)
        q2["intent_counts"][label + " (distinct intents)"] = len({gold[s] for s in rows_})

    # ---- Q3 note behaviour vs depth (P-SV-3)
    q3 = {}
    branch_ids = ("a-agree", "b-depth", "t-twin")
    for b in branch_ids:
        size = Counter(len(br(s, b)["note"]) for s in ids_b)
        rows_b = {}
        for s in ids_b:
            blk = br(s, b)["supplied"]
            rows_b[s] = {"block_rank": rank_of(blk, gold[s]), "on_note": gold[s] in br(s, b)["note"]}
        inb = [r for r in rows_b.values() if r["block_rank"] is not None]
        cand_ranks = Counter()
        for s in ids_b:
            blk = br(s, b)["supplied"]
            for c in br(s, b)["note"]:
                rr = rank_of(blk, c)
                cand_ranks["off block" if rr is None else str(rr)] += 1
        top1_block = Counter()
        for s in ids_b:
            n = br(s, b)["note"]
            if n:
                rr = rank_of(br(s, b)["supplied"], n[0])
                top1_block["off" if rr is None else str(rr)] += 1
        q3[b] = {"note_size_hist": {str(k): size[k] for k in sorted(size)},
                 "mean_note_size": round(sum(len(br(s, b)["note"]) for s in ids_b) / len(ids_b), 3),
                 "gold_in_block": len(inb), "gold_in_block_and_note": sum(1 for r in inb if r["on_note"]),
                 "p_note_given_block_pct": round(100.0 * sum(1 for r in inb if r["on_note"]) / len(inb), 2),
                 "gold_on_note_off_block": sum(1 for r in rows_b.values() if r["block_rank"] is None and r["on_note"]),
                 "note_given_block_rank": note_given_block_rank(rows_b, 12),
                 "note_candidate_block_rank_hist": {k: cand_ranks[k] for k in sorted(cand_ranks, key=lambda x: (x == "off block", int(x) if x.isdigit() else 99)) if cand_ranks[k]},
                 "note_rank1_block_rank_hist": {k: top1_block[k] for k in sorted(top1_block, key=lambda x: (x == "off", int(x) if x.isdigit() else 99))}}
    # paired A vs B / A vs T
    for other in ("b-depth", "t-twin"):
        dropped, gained = [], []
        for s in ids_b:
            a_on = gold[s] in br(s, "a-agree")["note"]
            o_on = gold[s] in br(s, other)["note"]
            if a_on and not o_on:
                dropped.append(s)
            if o_on and not a_on:
                gained.append(s)
        q3[f"a-agree vs {other}"] = {
            "a_kept_other_dropped": len(dropped), "other_kept_a_dropped": len(gained),
            "dropped_gold_block_rank_in_other": dict(sorted(Counter(str(rank_of(br(s, other)["supplied"], gold[s]) or "off") for s in dropped).items(), key=lambda t: (t[0] == "off", int(t[0]) if t[0].isdigit() else 99))),
            "dropped_gold_rank_in_a_note": dict(sorted(Counter(str(rank_of(br(s, "a-agree")["note"], gold[s])) for s in dropped).items())),
            "dropped_other_note_size": dict(sorted(Counter(str(len(br(s, other)["note"])) for s in dropped).items())),
            "gained_gold_block_rank_in_other": dict(sorted(Counter(str(rank_of(br(s, other)["supplied"], gold[s]) or "off") for s in gained).items(), key=lambda t: (t[0] == "off", int(t[0]) if t[0].isdigit() else 99))),
        }

    # ---- Q4 Solver-side contrast (P-SV-1 level 2)
    b1 = lambda s, b: psv1[s]["branches"][b]  # noqa: E731
    okc = {b: col[(RUN_PSV1[0], b)][0] for b in ("a-agree", "b-top2contrast", "t-twin")}
    q4 = {"level": dict(Counter(str(psv1[s]["level"]) for s in ids_b)),
          "official_intent_accuracy": {b: col[(RUN_PSV1[0], b)][1] for b in okc}}
    conv = {}
    for b in okc:
        c = Counter()
        for s in ids_b:
            r = rank_of(b1(s, b)["note"], gold[s])
            key = "absent" if r is None else str(r) if r <= 3 else "4+"
            c[(key, "rows")] += 1
            c[(key, "correct")] += int(okc[b][s])
        conv[b] = {k: {"rows": c[(k, "rows")], "correct": c[(k, "correct")],
                       "pct": round(100.0 * c[(k, "correct")] / c[(k, "rows")], 2) if c[(k, "rows")] else None}
                   for k in ("1", "2", "3", "4+", "absent")}
    q4["conversion_by_own_note_rank"] = conv
    # picks on own rank-2 rows
    pk = {}
    for b in okc:
        rows2 = [s for s in ids_b if rank_of(b1(s, b)["note"], gold[s]) == 2]
        pk[b] = dict(sorted(Counter(pick_class(picks[b][s], b1(s, b)["note"], gold[s]) for s in rows2).items()))
        pk[b]["pick_parse_agrees_with_official_intent"] = sum(1 for s in ids_b if (picks[b][s] == gold[s]) == okc[b][s])
    q4["solver_pick_on_own_rank2_rows"] = pk
    # paired tables
    def cross(anchor, other):
        rows_ = [s for s in ids_b if rank_of(b1(s, anchor)["note"], gold[s]) == 2]
        tab = Counter()
        for s in rows_:
            r = rank_of(b1(s, other)["note"], gold[s])
            key = "absent" if r is None else str(r) if r <= 3 else "4+"
            tab[(key, "rows")] += 1
            tab[(key, f"{anchor} correct")] += int(okc[anchor][s])
            tab[(key, f"{other} correct")] += int(okc[other][s])
        out = {k: {"rows": tab[(k, "rows")], f"{anchor}_correct": tab[(k, f"{anchor} correct")],
                   f"{other}_correct": tab[(k, f"{other} correct")]} for k in ("1", "2", "3", "absent") if tab[(k, "rows")]}
        diffs = [int(okc[other][s]) - int(okc[anchor][s]) for s in rows_]
        return {"anchor_rank2_rows": len(rows_), f"{anchor}_correct": sum(okc[anchor][s] for s in rows_),
                f"{other}_correct": sum(okc[other][s] for s in rows_), "by_other_note_rank": out,
                "paired_diff_rows": sum(diffs), "paired_diff_ci95_rate": paired_boot(diffs)}
    q4["paired_a_rank2_rows_vs_b"] = cross("a-agree", "b-top2contrast")
    q4["paired_b_rank2_rows_vs_a"] = cross("b-top2contrast", "a-agree")
    q4["paired_a_rank2_rows_vs_t"] = cross("a-agree", "t-twin")
    both = [s for s in ids_b if rank_of(b1(s, "a-agree")["note"], gold[s]) == 2 and rank_of(b1(s, "b-top2contrast")["note"], gold[s]) == 2]
    same_list = [s for s in both if b1(s, "a-agree")["note"] == b1(s, "b-top2contrast")["note"]]
    same_top2 = [s for s in both if b1(s, "a-agree")["note"][:2] == b1(s, "b-top2contrast")["note"][:2]]

    def disc(rows_):
        a = [okc["a-agree"][s] for s in rows_]
        b = [okc["b-top2contrast"][s] for s in rows_]
        return {"rows": len(rows_), "a_correct": sum(a), "b_correct": sum(b),
                "b_only": sum(1 for x, y in zip(a, b) if y and not x), "a_only": sum(1 for x, y in zip(a, b) if x and not y),
                "b_contrast_rendered": sum(1 for s in rows_ if b1(s, "b-top2contrast")["contrast_rendered"]),
                "solver_supply_identical_a_b": sum(1 for s in rows_ if b1(s, "a-agree")["solver_supply"] == b1(s, "b-top2contrast")["solver_supply"])}
    q4["both_notes_gold_rank2"] = disc(both)
    q4["both_notes_gold_rank2_same_top2_pair"] = disc(same_top2)
    q4["both_notes_gold_rank2_identical_list"] = disc(same_list)
    # T twin as the same analysis' null
    both_t = [s for s in ids_b if rank_of(b1(s, "a-agree")["note"], gold[s]) == 2 and rank_of(b1(s, "t-twin")["note"], gold[s]) == 2]
    q4["both_notes_gold_rank2_a_vs_t"] = {"rows": len(both_t), "a_correct": sum(okc["a-agree"][s] for s in both_t),
                                          "t_correct": sum(okc["t-twin"][s] for s in both_t)}
    # what the B Solver received (sealed receipts)
    recv = Counter()
    for s in ids_b:
        a_, b_ = b1(s, "a-agree"), b1(s, "b-top2contrast")
        recv["rows"] += 1
        recv["b_contrast_block_rendered_in_perception_request"] += int(b_["contrast_rendered"])
        recv["solver_supply_ids_identical_a_b"] += int(a_["solver_supply"] == b_["solver_supply"])
        recv["solver_supply_id_sets_identical_a_b"] += int(set(a_["solver_supply"]) == set(b_["solver_supply"]))
        recv["notes_identical_lists_a_b"] += int(a_["note"] == b_["note"])
        recv["solver_request_differs_a_b"] += int(a_["solver_request_sha256"] != b_["solver_request_sha256"])
    q4["what_b_solver_received"] = dict(recv)
    # whole-population contributions (row counts) of the rank-2 conversion difference
    q4["rank_mass"] = {b: {k: conv[b][k]["rows"] for k in ("1", "2", "3", "absent")} for b in okc}

    return {"read_id": READ_ID, "recipe": RECIPE, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "DESCRIPTIVE", "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                                                  "gpu": 0, "network": 0, "official_scorer_subprocess": 0},
            "driver_sha256": digest(Path(__file__)),
            "inputs": dict(sorted(files.items())), "checks": dict(sorted(checks.items())),
            "official_intent_accuracy": {"agree": agree_acc, "comp1b": comp_acc},
            "q1_shorter_block": q1, "q2_off_block_recall": q2, "q3_note_vs_depth": q3, "q4_solver_contrast": q4}


def render(r: dict) -> str:
    parts = [f"# {READ_ID}", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers (decisions 28, 86).", "",
             "Machine tables; every number in the results note is quoted from `report.json`.", ""]
    parts += ["## checks", "", "```json", json.dumps(r["checks"], indent=2, sort_keys=True), "```", ""]
    for name, q in r["q1_shorter_block"].items():
        parts += [f"## Q1 {name} ({q['key']}, fold {q['fold']})", ""]
        parts += ["| d | gold in block | % | targets in block | lost vs 8 | lost: note had gold | lost: delivered correct | gained vs 8 |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for x in q["depth_table"]:
            parts.append(f"| {x['d']} | {x['gold_in_block']} | {x['gold_in_block_pct']} | {x['targets_in_block']} / {x['targets_total']} | "
                         f"{x['lost_vs_ref']} | {x['lost_vs_ref_note_had_gold']} | {x['lost_vs_ref_delivered_correct']} | {x['gained_vs_ref']} |")
        parts += ["", "```json", json.dumps({k: q[k] for k in ("reproduction", "note_given_block_rank", "note_catches_gold_at_block_rank_gt_d",
                                                                 "score_profile_pooled_auc_positions_2_12", "row_margin_auc_gold_deeper_than_3",
                                                                 "crossfit_gap", "crossfit_cliff", "crossfit_gap_budget", "fixed_depth_curve")}, indent=2, sort_keys=True), "```", ""]
    parts += ["## Q2", "", "```json", json.dumps(r["q2_off_block_recall"], indent=2, sort_keys=True), "```", ""]
    parts += ["## Q3", "", "```json", json.dumps(r["q3_note_vs_depth"], indent=2, sort_keys=True), "```", ""]
    parts += ["## Q4", "", "```json", json.dumps(r["q4_solver_contrast"], indent=2, sort_keys=True), "```", ""]
    return "\n".join(parts) + "\n"


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"|Generated `[^`]*`', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the written outputs")
    parser.add_argument("--cache", default=None, help="development only: pickle of the recomputed rank lists (ids and scores)")
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
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
