#!/usr/bin/env python3
"""SLURP Reviewer-routed revision as a decision instrument (offline, DESCRIPTIVE).

Read id ``SAEA-SLURP-REVIEWER-REVISION-INSTRUMENT-OFFLINE-V1``. Model-free: zero model, server, tokenizer,
encoder, embedder, GPU, network and paid-API contacts; no official-scorer subprocess (sealed per-row official
intent flags are read only as a parse cross-check); ``core.flight.cli`` and ``lease_cli`` are never invoked.
Gold enters only offline through the governed TRAIN loader (``data.slurp.load_slurp_split``). Utterance text,
note text, exemplar bodies, gold values, Reviewer text and model output are never printed or persisted: only
ids, counts, rates, AUCs, pp and hashes.

The question (coordinator ruling R2 on
``docs/superpowers/specs/2026-09-30-solver-intent-decision-mechanism-design.md``): the Solver decision oracle
(``scripts/analysis/slurp_solver_decision_oracle.py``) found 62-82 flippable rows per pool (gold at note rank
2/3 while the Solver kept rank 1) and borrowed the REV-TFRL-1 conversion (10 / 54). On the already-sealed
Reviewer-routed revisions of every full-roster Fold A / Fold B pool, measure:

1. reach of the Reviewer's REVISE route against the oracle positives (recall, precision) and the route's AUC
   against the oracle label and against the oracle's signals;
2. conversion (REVISE on a positive -> the revised answer is gold; split by gold note rank 2 / 3), harm
   (REVISE on a first-right row -> the revision is wrong), and the net rows / pp of the loop with a paired
   bootstrap CI (cluster ``sample_id``, 10,000 draws, seed 20260929);
3. proxies for a declared low-confidence flag -- (a) the Solver's own switching (same row, and the
   leave-this-pool-out switching propensity over the other same-fold pools), (b) the REVISE route,
   (c) low boundary margin (and its model-visible twin, the exemplar-vote difference) -- with precision /
   recall against the oracle and the implied net rows at the measured REV-TFRL-1 conversion / harm,
   thresholds cross-fitted by utterance halves;
4. the verdict against the coordinator's thresholds (conversion >= 0.30 AND revise-decision precision
   >= 0.33) per pool and pooled.

Row-state primitives are the oracle's (``classify``, ``dedupe``, ``rank_of``, ``split_half``, ``auc``,
``score_margin``, ``f1_threshold``, ``scenario_of``, the ``CFG`` baselines and the REV-TFRL-1 anchor); the
oracle's fused-score recomputation is a closure inside its ``build`` and is mirrored here through the same
production constructor, with the oracle's custody check (recomputed depth-8 block == sealed block) deciding
per pool whether the margin is usable. Every Solver answer is parsed through the runtime's delivery projection
(the credit table's ``parse_answer``), so that the first answer and the delivered answer are read on the same
scale as the sealed official flag; the rows where the oracle's raw parse of the first answer differs are counted
in ``checks``.

``--check`` re-derives both outputs and compares them with the written files apart from ``generated_at``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))


def _import(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OR = _import(REPO_ROOT / "scripts/analysis/slurp_solver_decision_oracle.py", "slurp_solver_decision_oracle")

READ_ID = "SAEA-SLURP-REVIEWER-REVISION-INSTRUMENT-OFFLINE-V1"
RECIPE = "slurp-reviewer-revision-instrument-offline-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = OR.DEFAULT_LOCK
DEFAULT_DATA_ROOT = OR.DEFAULT_DATA_ROOT
ROWS = OR.ROWS
BOOT_DRAWS = 10_000
BOOT_SEED = 20260929
INTENT_FLOOR_PP = OR.INTENT_FLOOR_PP
#: coordinator ruling R2 thresholds
CONVERSION_BAR = 0.30
PRECISION_BAR = 0.33
#: measured REV-TFRL-1 anchor (quoted by the oracle from the REV-TFRL-1 read, section 4)
ANCHOR_C = OR.REVTFRL_CONVERSION[0] / OR.REVTFRL_CONVERSION[1]
ANCHOR_H = OR.REVTFRL_HARM[0] / OR.REVTFRL_HARM[1]

#: pool -> (fold, run id, reviewer form label). Every COMPLETED full-roster (1,080) Fold A / Fold B pool whose
#: phase artefact carries Perception, Planner, Reviewer and Solver states. Excluded (listed in the report):
#: COMP-1 and RELISTEN (seal-only, no agent states), ROLL-2 (grouped-sample Solver form), and every
#: partial roster (CONV-70, DET-50, RANKVIS-119, KPROBE-55, FILLER-180 x 6).
POOLS = {
    "revtfrl": ("A", "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-V1", "contrastive Reviewer (REV-TFRL-1 arm)"),
    "revtfrl_aa": ("A", "SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1", "standard (REV-TFRL-1 in-chain A/A)"),
    "agree": ("A", "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "standard"),
    "agree_aa": ("A", "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1", "standard"),
    "wave_aa": ("A", "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1", "standard"),
    "g5": ("A", "SAEA-SLURP-STAGE3-G5-FOLD-A-V1", "standard (G5 repaired Reviewer instruction)"),
    "comp1_aa": ("A", "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1", "standard"),
    "comp1b": ("A", "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1", "standard"),
    "w1_cardsel": ("A", "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1", "standard"),
    "w3": ("A", "SAEA-SLURP-STAGE3-W3-FOLD-A-V1", "standard"),
    "w4": ("A", "SAEA-SLURP-STAGE3-W4-FOLD-A-V1", "standard"),
    "w4sv": ("A", "SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1", "standard"),
    "wsv1": ("A", "SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1", "standard"),
    "psv1": ("B", "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1", "standard (P-SV level-2 episode)"),
    "psv2": ("B", "SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1", "standard (P-SV level-2 episode)"),
    "psv3": ("B", "SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1", "standard (P-SV level-2 episode)"),
}
EXCLUDED = {
    "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1": "seal-only attempt, no agent states",
    "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1": "seal-only attempt, no agent states",
    "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1": "grouped-sample Solver form (locked-v1-grouped5): first answer not comparable",
    "partial rosters": "CONV-FOLD-A-70, DET-NP1-FOLD-A-50-A/B, RANKVIS-FOLD-A-119, KPROBE-FOLD-A-55, FILLER-FOLD-B-C01..C06 (180 each)",
}
#: fused-score variants (fold, key) -> oracle baseline config key
FUSED_VARIANTS = {("A", "desc_agree"): "A", ("A", "cent_agree"): "A_cent", ("B", "desc_agree"): "B"}
SIGNALS = ("note_n", "margin_b", "r1_off_block_top", "ex_diff", "ex_r1", "ex_r2", "ex_top_is_r2",
           "same_scenario", "efs", "switch_prop")


class ReadError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# pure functions (unit-tested on fakes)


def row_state(result: dict, parse_pick, raw_pick=None) -> dict:
    """The per-row state of one sealed episode: the first Perception note (deduplicated, in order), every
    Solver answer's parsed intent pick in order, the Planner routes in order, the delivered exemplar keys
    and the sealed boundary block. ``parse_pick(text) -> intent | None`` (the delivery projection);
    ``raw_pick`` (optional) parses the first answer without it, for the oracle-parse cross-check only."""
    note, answers, first_raw = None, [], None
    for st in result.get("agent_states") or ():
        kind = st.get("state_kind")
        if kind == "phase:perception" and note is None:
            try:
                payload = json.loads(st.get("content") or "")
                note = OR.dedupe(str(c.get("intent_id")) for c in payload.get("candidates") or ())
            except (ValueError, AttributeError, TypeError):
                note = []
        elif kind == "phase:solver":
            if not answers and raw_pick is not None:
                first_raw = raw_pick(st.get("content"))
            answers.append(parse_pick(st.get("content")))
    receipt = result.get("native_episode_receipt") or {}
    routes = [str(r.get("action")) for r in receipt.get("planner_routes") or ()]
    ex = []
    for w in result.get("waves") or ():
        sel = (w.get("fusion_decision") or {}).get("selected_value_ids") or []
        if any(v.startswith(OR.EX_PREFIX) for v in sel):
            ex = [v.split(OR.EX_PREFIX, 1)[-1] for v in sel if v.startswith(OR.EX_PREFIX)]
            break
    block = [v.split(OR.IB_FACET_MARK, 1)[-1] for v in (result.get("initial_query_state") or {}).get(
        "retrieved_value_ids") or () if OR.IB_FACET_MARK in v]
    return {"note": note or [], "answers": answers, "routes": routes, "ex": ex, "block": block, "first_raw": first_raw}


def revision_record(state: dict, gold: str) -> dict:
    """Decision classes of one row (the oracle's ``classify`` on the FIRST answer) plus the Reviewer route
    on that first answer and the outcome of the revision it triggered.

    ``revise``: the Planner route after the first Reviewer visit is REVISE. ``executed``: a second Solver
    answer exists after it. ``revised_correct``: the immediate revision (second answer) is gold.
    ``final_correct``: the last Solver answer (the delivered draft) is gold. ``later_revise``: a REVISE
    route on a later visit only."""
    answers = state["answers"]
    first = answers[0] if answers else None
    c = OR.classify(state["note"], first, gold)
    routes = state["routes"]
    revise = bool(routes) and routes[0] == "REVISE"
    executed = revise and len(answers) >= 2
    revised = answers[1] if executed else first
    final = answers[-1] if answers else None
    return {**c, "first_correct": c["correct"], "revise": revise, "executed": executed,
            "later_revise": (not revise) and any(r == "REVISE" for r in routes[1:]),
            "revise_routes": sum(1 for r in routes if r == "REVISE"),
            "revised_correct": revised is not None and revised == gold,
            "final_correct": final is not None and final == gold,
            "revised_changed": executed and revised != first,
            "revised_rank": OR.rank_of(state["note"], revised) if executed and revised is not None else None,
            "switched": c["pick_rank"] in (2, 3) and len(state["note"]) >= 2}


def wilson(k: int, n: int, z: float = 1.959964) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(mid - half, 4), round(mid + half, 4)]


def rate(k: int, n: int):
    return round(k / n, 4) if n else None


def reach(records: list) -> dict:
    """Reach of the REVISE route (on the first answer) against the oracle positives."""
    pos = [r for r in records if r["label"] == 1]
    neg = [r for r in records if r["label"] == 0]
    cost = [r for r in records if r["decision"] and r["label"] is None]
    rev = [r for r in records if r["revise"]]
    tp = sum(1 for r in pos if r["revise"])
    rev_dec = [r for r in rev if r["decision"]]
    return {"positives": len(pos), "negatives": len(neg), "cost_rows": len(cost), "revise_rows": len(rev),
            "revise_rows_in_decision_set": len(rev_dec), "revise_on_positive": tp,
            "revise_on_negative": sum(1 for r in neg if r["revise"]),
            "revise_on_cost_row": sum(1 for r in cost if r["revise"]),
            "revise_on_switched_row": sum(1 for r in rev if r["switched"]),
            "revise_on_first_right": sum(1 for r in rev if r["first_correct"]),
            "later_revise_only_rows": sum(1 for r in records if r["later_revise"]),
            "recall": rate(tp, len(pos)), "recall_ci95": wilson(tp, len(pos)),
            "precision": rate(tp, len(rev)), "precision_ci95": wilson(tp, len(rev)),
            "precision_in_decision_set": rate(tp, len(rev_dec)),
            "revise_rate_positive": rate(tp, len(pos)),
            "revise_rate_negative": rate(sum(1 for r in neg if r["revise"]), len(neg)),
            "route_auc_vs_oracle_label": OR.auc([int(r["revise"]) for r in pos + neg], [1] * len(pos) + [0] * len(neg))}


def conversion(records: list, key: str = "final_correct") -> dict:
    """Conversion on REVISE-routed oracle positives (by gold note rank), harm on REVISE-routed first-right
    rows, and conversion on every REVISE-routed first-wrong row with gold on the note (rank <= 3)."""
    out = {}
    for gk in (2, 3):
        sel = [r for r in records if r["label"] == 1 and r["revise"] and r["gold_rank"] == gk]
        k = sum(1 for r in sel if r[key])
        out[f"gold_rank_{gk}"] = [k, len(sel)]
    sel = [r for r in records if r["label"] == 1 and r["revise"]]
    k = sum(1 for r in sel if r[key])
    out["positives"] = [k, len(sel)]
    out["conversion"] = rate(k, len(sel))
    out["conversion_ci95"] = wilson(k, len(sel))
    right = [r for r in records if r["revise"] and r["first_correct"]]
    kh = sum(1 for r in right if not r[key])
    out["first_right"] = [kh, len(right)]
    out["harm"] = rate(kh, len(right))
    out["harm_ci95"] = wilson(kh, len(right))
    rep = [r for r in records if r["revise"] and not r["first_correct"] and r["gold_rank"] in (1, 2, 3)]
    kr = sum(1 for r in rep if r[key])
    out["repairable_first_wrong_gold_on_note"] = [kr, len(rep)]
    off = [r for r in records if r["revise"] and not r["first_correct"] and r["gold_rank"] is None]
    out["first_wrong_gold_off_note"] = [sum(1 for r in off if r[key]), len(off)]
    return out


def paired_net(deltas_by_cluster: dict, n_rows: int, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> dict:
    """Net rows = sum of per-row deltas; pp over ``n_rows``; cluster bootstrap over the cluster keys
    (each cluster's summed delta and row count are resampled together)."""
    import numpy as np

    keys = sorted(deltas_by_cluster)
    d = np.array([sum(deltas_by_cluster[k]) for k in keys], dtype=float)
    m = np.array([len(deltas_by_cluster[k]) for k in keys], dtype=float)
    net = float(d.sum())
    rng = np.random.default_rng(seed)
    vals = np.empty(draws)
    for i in range(draws):
        idx = rng.integers(0, len(keys), len(keys))
        vals[i] = 100.0 * d[idx].sum() / m[idx].sum()
    return {"net_rows": int(net), "rows": int(m.sum()), "pp": round(100.0 * net / n_rows, 3),
            "ci95_pp": [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)],
            "saves": int(sum(1 for k in keys for x in deltas_by_cluster[k] if x > 0)),
            "harms": int(sum(1 for k in keys for x in deltas_by_cluster[k] if x < 0))}


def flag_eval(rows: list, flags: list, c: float = ANCHOR_C, h: float = ANCHOR_H) -> dict:
    """Operating point of a flag on decision rows (label 1 / 0 / None = cost row)."""
    tp = sum(1 for r, f in zip(rows, flags) if f and r["label"] == 1)
    fp = sum(1 for r, f in zip(rows, flags) if f and r["label"] == 0)
    cost = sum(1 for r, f in zip(rows, flags) if f and r["label"] is None)
    npos = sum(1 for r in rows if r["label"] == 1)
    called = tp + fp + cost
    net = tp * c - fp * h
    return {"flagged": called, "tp": tp, "fp": fp, "cost": cost, "precision": rate(tp, called),
            "precision_excl_cost": rate(tp, tp + fp), "recall": rate(tp, npos),
            "implied_net_rows": round(net, 2), "implied_pp": round(100.0 * net / ROWS, 3)}


def best_threshold(rows: list, key: str, c: float = ANCHOR_C, h: float = ANCHOR_H):
    """Flag ``score >= t``; t maximises implied net rows on ``rows`` (ties: the higher t). None if empty."""
    best = (None, -math.inf)
    for t in sorted({r[key] for r in rows}, reverse=True):
        e = flag_eval(rows, [r[key] >= t for r in rows], c, h)["implied_net_rows"]
        if e > best[1] + 1e-12:
            best = (t, e)
    return best[0]


def crossfit_flags(rows: list, key: str, rule: str = "net", c: float = ANCHOR_C, h: float = ANCHOR_H) -> tuple:
    """Cross-fitted flags: the threshold is chosen on one utterance half (``net``: implied net rows at
    (c, h); ``f1``: the oracle's F1 threshold against the label, cost rows counted as negatives) and
    applied to the other half. Returns (flags aligned with ``rows``, thresholds by half)."""
    flags = [False] * len(rows)
    thr = {}
    for hf in (0, 1):
        own = [r for r in rows if r["half"] == hf]
        if not own:
            continue
        if rule == "net":
            t = best_threshold(own, key, c, h)
        else:
            t = OR.f1_threshold([r[key] for r in own], [1 if r["label"] == 1 else 0 for r in own])
        thr[str(hf)] = None if t is None else round(float(t), 6)
        for i, r in enumerate(rows):
            if r["half"] != hf and t is not None:
                flags[i] = r[key] >= t
    return flags, thr


def switch_propensity(pick_rank_by_pool: dict, pool: str, sid: str) -> float | None:
    """Leave-this-pool-out share of the other pools whose first Solver answer left note rank 1 on ``sid``
    (among the pools where the row had a note of >= 2 candidates and a parsed first answer)."""
    elig = sw = 0
    for p, ranks in pick_rank_by_pool.items():
        if p == pool or sid not in ranks or ranks[sid] is None:
            continue
        elig += 1
        sw += int(ranks[sid] != 1)
    return (sw / elig) if elig else None


# ---------------------------------------------------------------------------
# I/O


def digest(path: Path) -> str:
    return OR.digest(path)


def build(args) -> dict:
    import numpy as np

    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot, QueryState
    from speech_aware_evidence_acquisition.rails.phase_supply import (
        _provider_factory, load_phase_supply_specs, load_sealed_agreement, load_sealed_segment_vectors,
        load_sealed_vectors)
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    NG = OR.import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    ES, GP = NG.ES, NG.GP
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    records = load_slurp_split(lock, data_root, "train", workers=4)
    gold = {r.sample_id: r.intent for r in records}
    utt = {r.sample_id: r.utterance_id for r in records}
    del records
    files, checks = {}, Counter()

    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import load_legal_intent_inventory

    CT = OR.import_path(REPO_ROOT / "scripts/analysis/slurp_reviewer_credit_table.py", "slurp_reviewer_credit_table")
    inventory = load_legal_intent_inventory(lock, data_root)

    def raw_pick(text):
        sc, ac, _e, ok = parse_slu_response(text or "")
        return f"{sc}_{ac}" if ok and sc is not None and ac is not None else None

    def parse_pick(text):
        # the runtime's delivery projection, then the official parse (the credit table's parse_answer)
        return CT.parse_answer(text or "", inventory)["intent"]

    pool_doc = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    files[pool_doc["relpath"]] = pool_doc["sha256"]
    ex_intent = {k: v["intent"] for k, v in pool_doc["values"].items()}
    ex_empty = {k: not v["fillers"] for k, v in pool_doc["values"].items()}
    del pool_doc

    # ---- sealed pools
    states, sealed = {}, {}
    for name, (fold, run_id, _form) in POOLS.items():
        hits = [p for p in sorted((data_root / "runs" / run_id).glob(f"*/{run_id}.phases.json"))
                if not p.parent.name.endswith("seal-only")]
        if len(hits) != 1:
            raise ReadError(f"{name}: expected one non-seal-only attempt with phases, found {len(hits)}")
        path = hits[0]
        files[str(path.relative_to(data_root))] = digest(path)
        doc = json.loads(path.read_text(encoding="utf-8"))
        states[name] = {res["sample_id"]: row_state(res, parse_pick, raw_pick) for res in doc["phases"][0]["results"]}
        del doc
        if len(states[name]) != ROWS:
            raise ReadError(f"{name}: roster is not 1,080 rows")
        score_paths = sorted((data_root / "runs" / run_id).glob(f"*/{run_id}.scores.json"))
        if not score_paths:
            raise ReadError(f"{name}: no sealed scores")
        sp = score_paths[0]
        files[str(sp.relative_to(data_root))] = digest(sp)
        block = json.loads(sp.read_text(encoding="utf-8"))
        key = sorted(k for k in block if k.startswith("slurp-slu-official") and isinstance(block[k], dict)
                     and block[k].get("per_sample"))[0]
        sealed[name] = {str(s["sample_id"]): bool(s["scenario_action_exact"] >= 1.0) for s in block[key]["per_sample"]}
        del block
    rosters = {f: sorted(states[n]) for n, (f, _r, _x) in POOLS.items()}
    for n, (f, _r, _x) in POOLS.items():
        if sorted(states[n]) != rosters[f]:
            raise ReadError(f"{n}: roster differs from its fold's")

    # ---- fused boundary scores (mirror of the oracle's closure, production constructor)
    def base_spec(cfg_rel):
        cfg = json.loads((REPO_ROOT / cfg_rel).read_text(encoding="utf-8"))
        files["repo:" + cfg_rel] = digest(REPO_ROOT / cfg_rel)
        store = cfg["knowledge_stores"]["intent-boundaries"]
        spec = load_phase_supply_specs({"phase_supply": store["phase_supply"]}, default_phase_program(cfg["policy"]))["perception"]
        return spec, store

    specs = {k: base_spec(OR.CFG[k]) for k in ("A", "A_cent", "B")}
    store_a = specs["A"][1]
    snap = KnowledgeSnapshot.from_frozen_json(json.loads((data_root / store_a["snapshot"]["relpath"]).read_text(encoding="utf-8")))
    if snap.content_hash() != store_a["snapshot"]["sha256"]:
        raise ReadError("boundary snapshot pin mismatch")
    files[store_a["snapshot"]["relpath"]] = store_a["snapshot"]["sha256"]
    facet_ids = sorted(f.facet_id for f in snap.facets)

    def fold_inputs(spec):
        q = load_sealed_segment_vectors(data_root / spec.query_source["relpath"], expected_sha256=spec.query_source["sha256"],
                                        dimensions=spec.dimensions)
        agr = load_sealed_agreement(data_root / spec.agreement_source["relpath"], expected_sha256=spec.agreement_source["sha256"],
                                    dimension="agreement:exemplar-intent", facet_ids=facet_ids)
        files[spec.query_source["relpath"]] = spec.query_source["sha256"]
        files[spec.agreement_source["relpath"]] = spec.agreement_source["sha256"]
        return q, agr

    def fused(spec, facet_src, qvec, agr, ids):
        s = replace(spec, facet_source=facet_src)
        fvec = load_sealed_vectors(data_root / facet_src["relpath"], expected_sha256=facet_src["sha256"], dimensions=s.dimensions)
        files[facet_src["relpath"]] = facet_src["sha256"]
        factory = _provider_factory(s, snapshot=snap, snapshot_sha256=snap.content_hash(), facet_vectors=fvec,
                                    provider_for_phase=None, agreement_scores=agr)
        out = {}
        for sid in ids:
            state = QueryState(query_id=f"revision-instrument:perception:{sid}", query_sample_id=sid,
                               speech_packet_id=f"revision-instrument:{sid}", speech_packet_sha256="0" * 64,
                               use_split_identity_hash="0" * 64).validate()
            provider = factory()
            rk = provider.candidates({"query_state": state, "query_segments": qvec[sid].segments}, k=s.k)
            rr = provider.last_rank_result()
            dec = provider.fuse([rk], k=s.k, policy_id=s.fuse_policy)
            out[sid] = {"order": [str(c.facet_id).split(OR.IB_FACET_MARK, 1)[-1] for c in rr.candidates],
                        "scores": [float(c.score) for c in rr.candidates],
                        "block": [str(v).split(OR.IB_FACET_MARK, 1)[-1] for v in dec.selected_value_ids]}
        return out

    qa, agr_a = fold_inputs(specs["A"][0])
    qb, agr_b = fold_inputs(specs["B"][0])
    FV = {}
    for (fold, key), ck in FUSED_VARIANTS.items():
        spec_base = specs["A"][0] if fold == "A" else specs["B"][0]
        q, agr = (qa, agr_a) if fold == "A" else (qb, agr_b)
        FV[(fold, key)] = fused(spec_base, specs[ck][0].facet_source, q, agr, rosters[fold])
    AGR = {"A": agr_a, "B": agr_b}

    # which fused variant reproduces each pool's sealed block
    variant = {}
    for name, (fold, _r, _x) in POOLS.items():
        matches = {key: sum(1 for s in rosters[fold] if FV[(f, key)][s]["block"] == states[name][s]["block"])
                   for (f, key) in FUSED_VARIANTS if f == fold}
        best = max(matches, key=lambda k: matches[k])
        checks[f"{name}_recomputed_block_equals_sealed_block_best_variant"] = matches[best]
        variant[name] = {"key": best, "block_matches": matches, "margin_usable": matches[best] == ROWS}

    # ---- per-row records
    recs = {}
    first_rank = {}  # pool -> sid -> first pick's note rank (None when note < 2 or unparsed)
    for name, (fold, _r, _x) in POOLS.items():
        rows = []
        F = FV[(fold, variant[name]["key"])]
        agr = AGR[fold]
        fr = {}
        for s in rosters[fold]:
            st, g = states[name][s], gold[s]
            rec = revision_record(st, g)
            checks[f"{name}_final_parse_agrees_with_sealed_official_intent"] += int(rec["final_correct"] == sealed[name][s])
            checks[f"{name}_exemplar_keys_unresolved"] += sum(1 for k in st["ex"] if k not in ex_intent)
            checks[f"{name}_reviewer_route_present"] += int(bool(st["routes"]))
            checks[f"{name}_first_pick_projected_equals_raw_oracle_parse"] += int(bool(st["answers"]) and st["answers"][0] == st["first_raw"])
            note = st["note"]
            fr[s] = rec["pick_rank"] if (len(note) >= 2 and st["answers"] and st["answers"][0] is not None) else None
            r = {"sid": s, "half": OR.split_half(utt[s]), **rec, "note_n": len(note)}
            if len(note) >= 2:
                r1, r2 = note[0], note[1]
                votes = Counter(ex_intent[k] for k in st["ex"] if k in ex_intent)
                top = votes.most_common()
                shares = {str(f).split(OR.IB_FACET_MARK, 1)[-1]: float(v) for f, v in (agr.get(s) or {}).items()}
                r.update({
                    "margin_b": OR.score_margin(F[s]["order"], F[s]["scores"], r1, r2) if variant[name]["margin_usable"] else None,
                    "r1_off_block_top": int(bool(st["block"]) and r1 != st["block"][0]),
                    "agr_diff": shares.get(r1, 0.0) - shares.get(r2, 0.0),
                    "ex_r1": votes.get(r1, 0), "ex_r2": votes.get(r2, 0), "ex_diff": votes.get(r1, 0) - votes.get(r2, 0),
                    "ex_top_is_r2": int(bool(top) and votes.get(r2, 0) > 0 and all(votes.get(r2, 0) > v for i, v in top if i != r2)),
                    "same_scenario": int(OR.scenario_of(r1) == OR.scenario_of(r2)),
                    "efs": (sum(1 for k in st["ex"] if ex_empty.get(k)) / len(st["ex"])) if st["ex"] else 0.0,
                })
            rows.append(r)
        recs[name] = rows
        first_rank[name] = fr
    # leave-pool-out switching propensity within the fold
    for name, (fold, _r, _x) in POOLS.items():
        same = {p: first_rank[p] for p, (f, _a, _b) in POOLS.items() if f == fold}
        for r in recs[name]:
            r["switch_prop"] = switch_propensity(same, name, r["sid"])

    # ---- analysis
    report_pools = {}
    for name, (fold, run_id, form) in POOLS.items():
        rows = recs[name]
        dec = [r for r in rows if r["decision"]]
        lab = [r for r in dec if r["label"] is not None]
        # fill missing signal values with the decision-set median (as the oracle does)
        sig_avail = [s for s in SIGNALS if any(r.get(s) is not None for r in dec)]
        for sgn in sig_avail:
            present = [r[sgn] for r in dec if r.get(sgn) is not None]
            fill = float(np.median(present)) if present else 0.0
            for r in dec:
                if r.get(sgn) is None:
                    r[sgn] = fill
        rch = reach(rows)
        conv_final = conversion(rows, "final_correct")
        conv_imm = conversion(rows, "revised_correct")
        # AUC: does the route track the oracle's signals? (target = REVISE among decision rows)
        route_auc = {s: (None if OR.auc([r[s] for r in dec], [int(r["revise"]) for r in dec]) is None
                         else round(OR.auc([r[s] for r in dec], [int(r["revise"]) for r in dec]), 4)) for s in sig_avail}
        label_auc = {s: (None if OR.auc([r[s] for r in lab], [r["label"] for r in lab]) is None
                         else round(OR.auc([r[s] for r in lab], [r["label"] for r in lab]), 4)) for s in sig_avail}
        # loop net (delivered minus first answer), whole roster, cluster = sample_id
        net_final = paired_net({r["sid"]: [int(r["final_correct"]) - int(r["first_correct"])] for r in rows}, ROWS)
        net_pos = sum(1 for r in rows if r["label"] == 1 and r["revise"] and r["final_correct"])
        # proxies (decision rows; score oriented so that larger = flag)
        for r in dec:
            r["neg_margin"] = -r["margin_b"] if "margin_b" in sig_avail else 0.0
            r["neg_ex_diff"] = -r["ex_diff"]
            r["revise_i"] = int(r["revise"])
        proxies = {}
        proxies["a1_own_switch"] = {"note": "0 flagged decision rows by construction (the decision set is the kept-r1 rows)",
                                    "switched_rows": sum(1 for r in rows if r["switched"]),
                                    "switched_right": sum(1 for r in rows if r["switched"] and r["first_correct"]),
                                    "switched_precision": rate(sum(1 for r in rows if r["switched"] and r["first_correct"]),
                                                               sum(1 for r in rows if r["switched"]))}
        proxies["a2_switch_propensity_any"] = flag_eval(dec, [r["switch_prop"] > 0 for r in dec])
        fl, th = crossfit_flags(dec, "switch_prop", "net")
        proxies["a2_switch_propensity_crossfit_net"] = {**flag_eval(dec, fl), "thresholds": th}
        proxies["b_revise_route"] = flag_eval(dec, [r["revise"] for r in dec])
        if "margin_b" in sig_avail and variant[name]["margin_usable"]:
            for rule in ("net", "f1"):
                fl, th = crossfit_flags(dec, "neg_margin", rule)
                proxies[f"c_low_margin_crossfit_{rule}"] = {**flag_eval(dec, fl), "thresholds_on_neg_margin": th}
        for rule in ("net", "f1"):
            fl, th = crossfit_flags(dec, "neg_ex_diff", rule)
            proxies[f"c2_low_vote_diff_crossfit_{rule}"] = {**flag_eval(dec, fl), "thresholds_on_neg_ex_diff": th}
        # combination: REVISE route AND low vote difference (cross-fitted on the vote threshold)
        fl, th = crossfit_flags(dec, "neg_ex_diff", "net")
        proxies["b_and_c2"] = flag_eval(dec, [f and r["revise"] for f, r in zip(fl, dec)])
        proxies["perfect_flag"] = flag_eval(dec, [r["label"] == 1 for r in dec])
        report_pools[name] = {
            "fold": fold, "run_id": run_id, "reviewer_form": form, "fused_variant": variant[name],
            "decision_rows": len(dec), "reach": rch, "conversion_delivered": conv_final,
            "conversion_immediate_revision": conv_imm,
            "loop_net_delivered_minus_first": net_final, "loop_net_rows_on_oracle_positives": net_pos,
            "route_auc_by_signal_decision_rows": route_auc, "label_auc_by_signal": label_auc,
            "proxies": proxies,
            "verdict": {"conversion": conv_final["conversion"], "precision": rch["precision"],
                        "conversion_clears": conv_final["conversion"] is not None and conv_final["conversion"] >= CONVERSION_BAR,
                        "precision_clears": rch["precision"] is not None and rch["precision"] >= PRECISION_BAR},
        }

    # ---- pooled
    def pooled(names):
        allr = [r for n in names for r in recs[n]]
        rch = reach(allr)
        cv = conversion(allr, "final_correct")
        by_sid = {}
        for n in names:
            for r in recs[n]:
                by_sid.setdefault(r["sid"], []).append(int(r["final_correct"]) - int(r["first_correct"]))
        net = paired_net(by_sid, ROWS * len(names))
        return {"pools": list(names), "reach": rch, "conversion_delivered": cv, "loop_net": net,
                "verdict": {"conversion": cv["conversion"], "precision": rch["precision"],
                            "conversion_clears": cv["conversion"] is not None and cv["conversion"] >= CONVERSION_BAR,
                            "precision_clears": rch["precision"] is not None and rch["precision"] >= PRECISION_BAR}}

    groups = {
        "all": list(POOLS),
        "standard_forms": [n for n in POOLS if n != "revtfrl"],
        "fold_a_standard": [n for n, v in POOLS.items() if v[0] == "A" and n != "revtfrl"],
        "fold_b": [n for n, v in POOLS.items() if v[0] == "B"],
    }
    report_pooled = {g: pooled(ns) for g, ns in groups.items()}
    # pooled proxy operating points (summed over pools), per proxy
    proxy_sum = {}
    for n in POOLS:
        for pk, pv in report_pools[n]["proxies"].items():
            if "tp" not in pv:
                continue
            acc = proxy_sum.setdefault(pk, Counter())
            acc["pools"] += 1
            for f in ("flagged", "tp", "fp", "cost"):
                acc[f] += pv[f]
            acc["positives"] += report_pools[n]["reach"]["positives"]
            acc["implied_net_rows"] += pv["implied_net_rows"]
    proxy_pooled = {k: {"pools": v["pools"], "flagged": v["flagged"], "tp": v["tp"], "fp": v["fp"], "cost": v["cost"],
                        "precision": rate(v["tp"], v["flagged"]), "recall": rate(v["tp"], v["positives"]),
                        "mean_implied_net_rows_per_pool": round(v["implied_net_rows"] / v["pools"], 2),
                        "mean_implied_pp_per_pool": round(100.0 * v["implied_net_rows"] / v["pools"] / ROWS, 3)}
                    for k, v in sorted(proxy_sum.items())}
    return {"read_id": READ_ID, "recipe": RECIPE, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "DESCRIPTIVE", "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                                                  "gpu": 0, "network": 0, "official_scorer_subprocess": 0},
            "driver_sha256": digest(Path(__file__)), "oracle_driver_sha256": digest(Path(OR.__file__)),
            "boot": {"draws": BOOT_DRAWS, "seed": BOOT_SEED},
            "thresholds": {"conversion": CONVERSION_BAR, "precision": PRECISION_BAR, "intent_floor_pp": INTENT_FLOOR_PP,
                           "intent_floor_rows": round(OR.rows_for_pp(INTENT_FLOOR_PP), 2)},
            "anchor_revtfrl": {"conversion": round(ANCHOR_C, 4), "harm": round(ANCHOR_H, 4)},
            "excluded": EXCLUDED, "inputs": dict(sorted(files.items())), "checks": dict(sorted(checks.items())),
            "pools": report_pools, "pooled": report_pooled, "proxy_pooled": proxy_pooled}


def render(r: dict) -> str:
    parts = [f"# {READ_ID}", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers (decisions 28, 86).", "",
             "## checks", "", "```json", json.dumps(r["checks"], indent=2, sort_keys=True), "```", "",
             "## Reach, conversion and harm (delivered answer)", "",
             "| pool | REVISE rows | positives | REVISE on pos | recall | precision | conv (r2 / r3) | conversion | harm | net rows | net pp [CI95] |",
             "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |"]
    for n, p in list(r["pools"].items()) + [("POOLED " + k, v) for k, v in r["pooled"].items()]:
        rc, cv = p["reach"], p["conversion_delivered"]
        net = p.get("loop_net_delivered_minus_first") or p.get("loop_net")
        parts.append(f"| {n} | {rc['revise_rows']} | {rc['positives']} | {rc['revise_on_positive']} | {rc['recall']} | {rc['precision']} | "
                     f"{cv['gold_rank_2'][0]}/{cv['gold_rank_2'][1]} ; {cv['gold_rank_3'][0]}/{cv['gold_rank_3'][1]} | {cv['conversion']} | "
                     f"{cv['harm']} ({cv['first_right'][0]}/{cv['first_right'][1]}) | {net['net_rows']} | {net['pp']} {net['ci95_pp']} |")
    parts += ["", "## Proxies", ""]
    for n, p in r["pools"].items():
        parts += [f"### {n}", "", "```json", json.dumps({"proxies": p["proxies"], "route_auc": p["route_auc_by_signal_decision_rows"],
                                                          "label_auc": p["label_auc_by_signal"], "fused_variant": p["fused_variant"],
                                                          "conversion_immediate_revision": p["conversion_immediate_revision"]},
                                                         indent=2, sort_keys=True), "```", ""]
    parts += ["## Proxy pooled", "", "```json", json.dumps(r["proxy_pooled"], indent=2, sort_keys=True), "```", ""]
    return "\n".join(parts) + "\n"


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
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
