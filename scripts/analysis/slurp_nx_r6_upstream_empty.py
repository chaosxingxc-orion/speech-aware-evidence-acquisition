#!/usr/bin/env python3
"""NX R6 design read (owner decision 239): where should the empty-entity decision live UPSTREAM of the Solver?

Offline, zero GPU, zero model contact. Owner decision 239 (2026-10-10): when a local optimisation is shown to be
unattainable, hand the task to the system -- ask other nodes for more valuable or more easily obtained inputs; move
the empty-entity / non-empty-entity decision to a preceding node and, if useful, adjust the knowledge supply.

Inputs (all sealed, all read-only):

* the two NX R1 Solver template columns on TRAIN Fold B (1,080 rows, 392 empty-gold):
  iteration 1 ``SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1`` (aggressive-empty arm ``r1-c3``) and iteration 2
  ``SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1`` (``r1-i2-c3``); the delivering ``lock`` arm is the baseline.
  Per arm, the rendered first-visit column ``supply-variants/arm-<id>-first-visit-outputs.jsonl`` (the texts the
  official column scorer scored) and its sealed per-sample official fields; the in-process score of every row
  must reproduce the sealed per-sample fields exactly (the run stops otherwise).
* the sealed ``phases.json`` of each run (Perception note, supplied exemplar ids and cosine scores, boundary block)
  and the Perception request/response records of the trace (``audio_seconds``, completion tokens);
* the v4g statistics tables ``prepared/SAEA-SLURP-V4-TRAIN-STATISTICS-V1/intent-entity-rate-v1.json`` (TRAIN pool
  minus Fold A / Fold B / R01 / R01C: disjoint from every roster read here) and the exemplar pool snapshot the
  cells supplied from (entity annotations -> the N1 entity-free share);
* for the deterministic v5 read: the COMP-1b delivered columns of A2 (DEV-2000-ADDED) and TRAIN Fold A
  (the v4 search driver's ``POOLS``), with v4g applied in-process through the registered normaliser.

Questions answered (numbers in ``report.json``):

1. separability of empty-gold rows by signals available before the Solver answers (and two post-Solver ones);
2. the oracle value of an upstream verdict: rows where a threshold rule fires take the aggressive arm's row
   (``c3``), or the lock row emptied (``empty``), or the lock row emptied only where the aggressive arm emptied it
   (``c3verdict``); all other rows keep the lock row; official pooled SLU-F1 re-scored exactly in-process; on the
   sealed v3 columns and on the v4g-applied columns;
3. the non-empty rows the aggressive arm lost against lock, characterised by aggregate counts;
4. the deterministic v5 rule (v4g + "empty when the signal fires") on A2, Fold A and Fold B.

R6-P1 extension (owner decisions 245-247): ``--verdict-source perception-arm:<arm_id>`` swaps the verdict source of the
``c3verdict`` rule from the aggressive Solver arm to the rank-1 ``E=none`` of a sealed Perception template column (the R6
run; notes parsed in memory by ``slurp_nx_perception_column_read``'s tag parser), and ``--gain-baseline
{n1,n1+prior,n1+prior+lock}`` names the features the downstream node already has. It writes the cross-fitted AUC increment
of the verdict over that baseline (cluster bootstrap CI95, 2,000 draws, seed 20261010) and the gate estimate (verdict and
N1 >= 0.2 plus the fixed N1 grid) on the lock Solver column, v4g base (10,000 draws, seed 20260915): pp with CI95, false
fills removed, non-empty exact lost, intent rows moved. The original read is unchanged when the option is left at 'solver'.

Gold discipline: gold enters only offline through the governed SLURP loaders (TRAIN Fold A / Fold B through
``load_slurp_split(train)``, DEV-2000-ADDED through ``load_slurp_split(devel)``), the v4 search driver's
``load_gold``; the test split is never read. Text discipline: no utterance text, transcript, gold value, filler,
exemplar text, Perception note text or model output is printed or persisted -- only ids, counts, rates, AUCs, pp,
intent and slot TYPE labels, and hashes.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_r6_upstream_empty.py \\
        --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

READ_ID = "SAEA-SLURP-NX-R6-UPSTREAM-EMPTY-OFFLINE-V1"
RECIPE = "slurp-nx-r6-upstream-empty-offline-v1"
SCHEMA = "saea-slurp-nx-r6-upstream-empty-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")

FOLD_B = {
    "i1": {"run_id": "SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1",
           "attempt": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-generation-v1",
           "aggressive": "r1-c3", "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080},
    "i2": {"run_id": "SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1",
           "attempt": "attempt-slurp-native-stage3-nx-r1-i2-solver-fold-b-generation-v1",
           "aggressive": "r1-i2-c3", "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080},
}
DELIVERING = "lock"
TWIN = "aa"
RATE_TABLE = "prepared/SAEA-SLURP-V4-TRAIN-STATISTICS-V1/intent-entity-rate-v1.json"
EX_SNAPSHOT = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
EX_PREFIX = "train-exemplars::value:"
EX_FACET_PREFIX = "train-exemplars::facet:content:"
IB_PREFIX = "intent-boundaries::intent-boundary:"
V4G = "saea-deliver-normalise-v4g"
FLOOR_PP = 0.67
BAR_PP = 1.5
AUC_DRAWS = 2000
AUC_SEED = 20261010
FIRE_SHARES = tuple(round(0.05 * k, 2) for k in range(1, 13))       # 5 % .. 60 % of rows fire
RATE_THRESHOLDS = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)  # fire when the TRAIN entity rate < t
N1_THRESHOLDS = (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)  # fire when the entity-free share >= t
N1_BINS = (0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.01)
BEHAVIOURS = ("c3", "empty", "c3verdict")


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


DRV = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py", "slurp_nx_postproc_v4_search")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def r4(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)


# ---------------------------------------------------------------------------
# pure statistics


def auc(scores, labels) -> float | None:
    """P(score of a positive > score of a negative) + 0.5 P(tie); positives are label 1."""
    import numpy as np
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(labels, dtype=bool)
    npos, nneg = int(y.sum()), int((~y).sum())
    if npos == 0 or nneg == 0:
        return None
    uniq, inverse, counts = np.unique(s, return_inverse=True, return_counts=True)
    upper = np.cumsum(counts)
    avg = upper - (counts - 1) / 2.0
    ranks = avg[inverse]
    return float((ranks[y].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def boot_auc(scores, labels, clusters, draws: int = AUC_DRAWS, seed: int = AUC_SEED) -> list | None:
    import numpy as np
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(labels, dtype=bool)
    keys = sorted(set(clusters))
    index = {c: k for k, c in enumerate(keys)}
    members = defaultdict(list)
    for row, c in enumerate(clusters):
        members[index[c]].append(row)
    members = [np.array(members[k]) for k in range(len(keys))]
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        pick = rng.integers(0, len(keys), size=len(keys))
        rows = np.concatenate([members[k] for k in pick])
        a = auc(s[rows], y[rows])
        if a is not None:
            out.append(a)
    if not out:
        return None
    return [round(float(np.percentile(out, 2.5)), 4), round(float(np.percentile(out, 97.5)), 4)]


def wilson_upper(k: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 1.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return min(1.0, centre + margin)


def half_of(utterance_id: str) -> int:
    return int(hashlib.sha256(utterance_id.encode("utf-8")).hexdigest(), 16) % 2


def fit_logistic(X, y, l2: float = 1.0, iters: int = 50):
    """L2-penalised logistic regression by Newton steps on standardised features (intercept unpenalised)."""
    import numpy as np
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = np.hstack([np.ones((len(X), 1)), (X - mu) / sd])
    w = np.zeros(Z.shape[1])
    pen = np.full(Z.shape[1], l2)
    pen[0] = 0.0
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-Z @ w))
        g = Z.T @ (p - y) + pen * w
        H = (Z * (p * (1 - p))[:, None]).T @ Z + np.diag(pen)
        step = np.linalg.solve(H, g)
        w -= step
        if float(np.abs(step).max()) < 1e-10:
            break
    return {"mu": mu, "sd": sd, "w": w}


def predict_logistic(model, X):
    import numpy as np
    Z = np.hstack([np.ones((len(X), 1)), (np.asarray(X, dtype=np.float64) - model["mu"]) / model["sd"]])
    return 1.0 / (1.0 + np.exp(-Z @ model["w"]))


# ---------------------------------------------------------------------------
# sealed loaders


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_phase_signals(path: Path, slot_types: set) -> dict:
    """Per row: Perception note features (counts only), supplied exemplar ids and cosine scores, boundary block.
    Note text is parsed in memory and discarded."""
    document = json.loads(path.read_text(encoding="utf-8"))
    rows, checks = {}, Counter()
    for result in document["phases"][0]["results"]:
        sid = result["sample_id"]
        boundary = [v.split(IB_PREFIX, 1)[-1] for v in result["initial_query_state"]["retrieved_value_ids"]
                    if v.startswith(IB_PREFIX)]
        ex_ids, ex_scores = [], []
        for wave in result.get("waves") or ():
            selected = (wave.get("fusion_decision") or {}).get("selected_value_ids") or []
            if not any(v.startswith(EX_PREFIX) for v in selected):
                continue
            ex_ids = [v.split(EX_PREFIX, 1)[-1] for v in selected if v.startswith(EX_PREFIX)]
            ex_scores = [float(c["score"]) for c in (wave.get("rank_result") or {}).get("candidates") or ()
                         if str(c["facet_id"]).startswith(EX_FACET_PREFIX)]
            break
        note = None
        for state in result.get("agent_states") or ():
            if state.get("state_kind") != "phase:perception":
                continue
            try:
                payload = json.loads(state.get("content") or "")
                cands = payload.get("candidates") or []
                unresolved = [[str(u) for u in (c.get("unresolved_fields") or ())] for c in cands]
                note = {
                    "ids": [str(c.get("intent_id")) for c in cands],
                    "unresolved": [len(u) for u in unresolved],
                    "slot_named": [sum(1 for u in us if u.strip().lower() in slot_types) for us in unresolved],
                    "evidence_refs": [len(c.get("evidence_refs") or ()) for c in cands],
                    "distinction_tokens": [len(str(c.get("distinction") or "").split()) for c in cands],
                }
                del payload, cands, unresolved
            except (ValueError, AttributeError, TypeError):
                note = None
            break
        checks["rows"] += 1
        checks["perception_note_parsed"] += int(note is not None)
        checks["exemplars_20"] += int(len(ex_ids) == 20)
        checks["exemplar_scores_20"] += int(len(ex_scores) == 20)
        rows[sid] = {"boundary": boundary, "ex_ids": ex_ids, "ex_scores": sorted(ex_scores, reverse=True),
                     "note": note}
    del document
    return {"rows": rows, "checks": dict(sorted(checks.items())), "sha256": digest(path)}


def load_perception_trace(path: Path, ids: set) -> dict:
    """sample_id -> audio seconds and Perception completion tokens (first Perception contact)."""
    rid_of, out = {}, {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            head = line[:200]
            if '"MODEL_REQUEST"' in head:
                rec = json.loads(line)
                payload = (rec.get("payload") or {}).get("payload") or {}
                role = str(payload.get("key_representation_id") or "").rsplit(":", 1)[-1]
                sid = payload.get("sample_id")
                if role != "perception" or sid not in ids or sid in out:
                    continue
                rid = rec["record_id"].split("/")[0]
                rid_of[rid] = sid
                out[sid] = {"audio_seconds": float(payload.get("audio_seconds") or 0.0)}
            elif '"MODEL_RESPONSE"' in head:
                rec = json.loads(line)
                if rec.get("channel") != "MODEL_RESPONSE":
                    continue
                sid = rid_of.get(rec["record_id"].split("/")[0])
                if sid is None or "completion_tokens" in out[sid]:
                    continue
                usage = (rec.get("payload") or {}).get("usage") or {}
                out[sid]["completion_tokens"] = usage.get("completion_tokens")
                out[sid]["prompt_tokens"] = usage.get("prompt_tokens")
    return out


def load_exemplar_annotations(data_root: Path) -> dict:
    """value key -> (intent, entity-bearing?) from the pool snapshot; bodies are discarded."""
    path = data_root / EX_SNAPSHOT
    document = json.loads(path.read_text(encoding="utf-8"))
    pool = {}
    for value in document["values"]:
        parts = [p.strip() for p in (value.get("content") or "").split(" | ")]
        if len(parts) != 3:
            raise ReadError("an exemplar body does not carry three fields")
        types = []
        if parts[2] and parts[2] != "none":
            for chunk in parts[2].split("; "):
                name, _, _filler = chunk.partition("=")
                if name.strip():
                    types.append(name.strip())
        pool[value["value_id"].split("value:", 1)[-1]] = {"intent": parts[1], "n_entities": len(types)}
    del document
    return {"values": pool, "sha256": digest(path), "relpath": EX_SNAPSHOT}


def score_texts(ids, texts, gold):
    import numpy as np
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response
    m = np.zeros((len(ids), 10), dtype=np.float64)
    m_empty = np.zeros((len(ids), 10), dtype=np.float64)
    for k, sid in enumerate(ids):
        scenario, action, entities, _parsed = parse_slu_response(texts[sid])
        m[k] = DRV.score_vector(gold[sid], scenario, action, list(entities))
        m_empty[k] = DRV.score_vector(gold[sid], scenario, action, [])
    return m, m_empty


def apply_v4g(ids, texts):
    from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import replay_row
    from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
    from speech_aware_evidence_acquisition.rails import delivery_normalisers  # noqa: F401
    normaliser = DELIVERY_NORMALISERS.resolve(V4G)
    out, changed = {}, 0
    for sid in ids:
        replayed = replay_row({"sample_id": sid, "text": texts[sid]}, normaliser=normaliser)
        out[sid] = replayed["text"]
        changed += int(bool(replayed["changed"]))
    return out, changed, str(normaliser.version)


def delivered_intent(texts, ids):
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response
    out = {}
    for sid in ids:
        scenario, action, _e, parsed = parse_slu_response(texts[sid])
        out[sid] = f"{scenario}_{action}" if parsed and scenario and action else None
    return out


# ---------------------------------------------------------------------------
# row signals


def rate_of(table: dict, intent):
    n = table["intent_n"].get(intent)
    if not n:
        return None
    return table["intent_with_entities"].get(intent, 0) / n


def row_signals(sid, phase, trace, pool, table, lock_items=None, lock_intent=None) -> dict:
    """Signals oriented so that a HIGHER value means 'more likely empty'. ``None`` when not computable."""
    note = phase["note"]
    ids = note["ids"] if note else []
    rates = [rate_of(table, i) for i in ids]
    rates_known = [r for r in rates if r is not None]
    r1 = rates[0] if rates else None
    ex = [pool["values"].get(k) for k in phase["ex_ids"]]
    ex = [e for e in ex if e is not None]
    free = [e["n_entities"] == 0 for e in ex]
    same = [e["n_entities"] == 0 for e in ex if ids and e["intent"] == ids[0]]
    votes = Counter(e["intent"] for e in ex)
    vote_intent = votes.most_common(1)[0][0] if votes else None
    vote_rate = rate_of(table, vote_intent)
    sig = {
        "a_rate_rank1": None if r1 is None else 1.0 - r1,
        "a_rate_shortlist_max": None if not rates_known else 1.0 - max(rates_known),
        "a_rate_shortlist_mean": None if not rates_known else 1.0 - sum(rates_known) / len(rates_known),
        "a_rate_exemplar_vote": None if vote_rate is None else 1.0 - vote_rate,
        "b_n1_share": (sum(free) / len(free)) if free else None,
        "b_n1_same_intent": (sum(same) / len(same)) if same else ((sum(free) / len(free)) if free else None),
        "b_exemplar_top1_cosine_neg": -phase["ex_scores"][0] if phase["ex_scores"] else None,
        "c_unresolved_rank1_neg": None if not note or not note["unresolved"] else -float(note["unresolved"][0]),
        "c_unresolved_total_neg": None if not note else -float(sum(note["unresolved"])),
        "c_slot_named_rank1_neg": None if not note or not note["slot_named"] else -float(note["slot_named"][0]),
        "c_candidates_neg": None if not note else -float(len(ids)),
        "c_evidence_refs_rank1_neg": None if not note or not note["evidence_refs"] else -float(note["evidence_refs"][0]),
        "c_distinction_tokens_rank1_neg": None if not note or not note["distinction_tokens"]
        else -float(note["distinction_tokens"][0]),
        "c_note_completion_tokens_neg": None if trace.get("completion_tokens") is None
        else -float(trace["completion_tokens"]),
        "e_audio_seconds_neg": None if not trace.get("audio_seconds") else -float(trace["audio_seconds"]),
    }
    if lock_items is not None:
        sig["d_lock_items_neg"] = -float(lock_items)
    if lock_intent is not None or lock_items is not None:
        lr = rate_of(table, lock_intent)
        sig["d_lock_intent_rate"] = None if lr is None else 1.0 - lr
    return sig


SIGNAL_DOC = {
    "a_rate_rank1": "(a) 1 - TRAIN entity-carrying rate of Perception's rank-1 intent (v4g table)",
    "a_rate_shortlist_max": "(a) 1 - max TRAIN entity rate over Perception's shortlist",
    "a_rate_shortlist_mean": "(a) 1 - mean TRAIN entity rate over Perception's shortlist",
    "a_rate_exemplar_vote": "(a/b) 1 - TRAIN entity rate of the majority intent of the 20 supplied exemplars",
    "b_n1_share": "(b) N1: entity-free share of the 20 supplied exemplars",
    "b_n1_same_intent": "(b) entity-free share among supplied exemplars of the rank-1 intent (N1 when none)",
    "b_exemplar_top1_cosine_neg": "(b) minus the top-1 exemplar cosine",
    "c_unresolved_rank1_neg": "(c) minus the rank-1 candidate's unresolved-field count",
    "c_unresolved_total_neg": "(c) minus the note's total unresolved-field count",
    "c_slot_named_rank1_neg": "(c) minus the rank-1 unresolved fields that name a SLURP slot type",
    "c_candidates_neg": "(c) minus the note's candidate count",
    "c_evidence_refs_rank1_neg": "(c) minus the rank-1 candidate's evidence-ref count",
    "c_distinction_tokens_rank1_neg": "(c) minus the rank-1 distinction length in whitespace tokens",
    "c_note_completion_tokens_neg": "(c) minus Perception's completion tokens (note length)",
    "e_audio_seconds_neg": "(e) minus the audio duration in seconds",
    "d_lock_items_neg": "(d, post-Solver) minus the lock column's predicted item count",
    "d_lock_intent_rate": "(d, post-Solver) 1 - TRAIN entity rate of the lock column's delivered intent",
}
PRE_SIGNALS = [k for k in SIGNAL_DOC if not k.startswith("d_")]
POST_SIGNALS = ["d_lock_items_neg", "d_lock_intent_rate"]
COMBOS = {
    "x_rate_n1": ["a_rate_rank1", "b_n1_share"],
    "x_rate_n1_note": ["a_rate_rank1", "a_rate_shortlist_max", "b_n1_share", "b_n1_same_intent",
                       "c_unresolved_rank1_neg", "c_slot_named_rank1_neg", "c_evidence_refs_rank1_neg"],
    "x_pre_all": PRE_SIGNALS,
    "x_pre_all_plus_lock": PRE_SIGNALS + POST_SIGNALS,
}


def fill_missing(values):
    known = [v for v in values if v is not None]
    med = sorted(known)[len(known) // 2] if known else 0.0
    return [med if v is None else v for v in values], sum(v is None for v in values)


def crossfit_scores(ids, signals, features, labels, halves):
    import numpy as np
    X = np.array([[signals[s][f] for f in features] for s in ids], dtype=np.float64)
    y = np.array(labels, dtype=np.float64)
    h = np.array(halves)
    out = np.zeros(len(ids))
    for k in (0, 1):
        model = fit_logistic(X[h != k], y[h != k])
        out[h == k] = predict_logistic(model, X[h == k])
    return out.tolist()


# ---------------------------------------------------------------------------
# counterfactual mixing


def row_flags(vec):
    pred = vec[6] + vec[7]
    exact = vec[7] == 0 and vec[8] == 0
    return pred, exact


def mix(base, alt, base_empty, fired, behaviour):
    """A new column: fired rows take the behaviour's row, others the base row."""
    out = base.copy()
    for k, f in enumerate(fired):
        if not f:
            continue
        if behaviour == "c3":
            out[k] = alt[k]
        elif behaviour == "empty":
            out[k] = base_empty[k]
        elif behaviour == "c3verdict":
            if alt[k][6] + alt[k][7] == 0:
                out[k] = base_empty[k]
        else:
            raise ReadError(behaviour)
    return out


def column_metrics(base, new, gold_empty):
    import numpy as np
    pb, pn = DRV.pooled(base), DRV.pooled(new)
    ff_b = ff_n = ne_lost = ne_gain = 0
    for k in range(len(base)):
        bp, bx = row_flags(base[k])
        np_, nx = row_flags(new[k])
        if gold_empty[k]:
            ff_b += int(bp > 0)
            ff_n += int(np_ > 0)
        else:
            ne_lost += int(bx and not nx)
            ne_gain += int(nx and not bx)
    return {"delta_slu_pp": round(pn["slu_f1_pp"] - pb["slu_f1_pp"], 4),
            "slu_f1_pp": round(pn["slu_f1_pp"], 4),
            "false_fill_rows_base": ff_b, "false_fill_rows_new": ff_n,
            "nonempty_exact_lost": ne_lost, "nonempty_exact_gained": ne_gain,
            "intent_rows_changed": int(np.sum(base[:, 9] != new[:, 9])),
            "rows_changed": int(np.sum(np.any(base != new, axis=1)))}


def fire_by_share(values, share):
    """Fire on the top ``share`` of rows by signal (gold-free quantile; ties fire together)."""
    import numpy as np
    v = np.array([-np.inf if x is None else x for x in values], dtype=np.float64)
    cut = np.quantile(v[np.isfinite(v)], 1.0 - share)
    return [bool(x >= cut) for x in v], float(cut)


def sweep(ids, signals, sig_names, base, alt, base_empty, gold_empty, halves, boot, behaviours=BEHAVIOURS):
    rows = []
    for name in sig_names:
        values = [signals[s].get(name) for s in ids]
        if all(v is None for v in values):
            continue
        for beh in behaviours:
            for share in FIRE_SHARES:
                fired, cut = fire_by_share(values, share)
                new = mix(base, alt, base_empty, fired, beh)
                m = column_metrics(base, new, gold_empty)
                rows.append({"signal": name, "behaviour": beh, "rule": f"top {int(share * 100)} %",
                             "cut": round(cut, 4), "fired": int(sum(fired)),
                             "fired_empty_gold": int(sum(f and e for f, e in zip(fired, gold_empty))), **m})
            if name in ("a_rate_rank1", "d_lock_intent_rate", "a_rate_exemplar_vote"):
                for t in RATE_THRESHOLDS:
                    fired = [v is not None and (1.0 - v) < t for v in values]
                    new = mix(base, alt, base_empty, fired, beh)
                    m = column_metrics(base, new, gold_empty)
                    rows.append({"signal": name, "behaviour": beh, "rule": f"rate < {t:.2f}", "cut": t,
                                 "fired": int(sum(fired)),
                                 "fired_empty_gold": int(sum(f and e for f, e in zip(fired, gold_empty))), **m})
            if name.startswith("b_n1"):
                for t in N1_THRESHOLDS:
                    fired = [v is not None and v >= t for v in values]
                    new = mix(base, alt, base_empty, fired, beh)
                    m = column_metrics(base, new, gold_empty)
                    rows.append({"signal": name, "behaviour": beh, "rule": f"share >= {t:.1f}", "cut": t,
                                 "fired": int(sum(fired)),
                                 "fired_empty_gold": int(sum(f and e for f, e in zip(fired, gold_empty))), **m})
    return rows


def crossfit_rule(ids, values, base, alt, base_empty, gold_empty, halves, behaviour, boot):
    """Pick the top-share rule on one utterance half, apply it to the other half (both directions)."""
    import numpy as np
    h = np.array(halves)
    fired_all = [False] * len(ids)
    picks = {}
    for k in (0, 1):
        train = [i for i in range(len(ids)) if h[i] != k]
        test = [i for i in range(len(ids)) if h[i] == k]
        best = None
        for share in FIRE_SHARES:
            fired, cut = fire_by_share([values[i] for i in train], share)
            sub_base, sub_alt, sub_empty = base[train], alt[train], base_empty[train]
            new = mix(sub_base, sub_alt, sub_empty, fired, behaviour)
            d = DRV.pooled(new)["slu_f1_pp"] - DRV.pooled(sub_base)["slu_f1_pp"]
            if best is None or d > best[0] + 1e-12:
                best = (d, share, cut)
        picks[f"half_{k}_applied_rule"] = {"share_selected_on_other_half": best[1], "cut": round(best[2], 4),
                                           "train_half_delta_pp": round(best[0], 4)}
        for i in test:
            v = values[i]
            fired_all[i] = v is not None and v >= best[2]
    new = mix(base, alt, base_empty, fired_all, behaviour)
    contrast = boot.contrast(base, new)
    return {"picks": picks, "fired": int(sum(fired_all)), **column_metrics(base, new, gold_empty),
            "ci95_slu_pp": contrast["ci95_slu_pp"]}


# ---------------------------------------------------------------------------
# R6-P1: a Perception arm as the verdict source -- information gain and the gate estimate
#
# Owner decisions 245/247 (design note docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md
# sections 2.2 and 4). The verdict of the NX R6 run's Perception arm (rank-1 ``E=none`` of the tagged distinction,
# parsed in memory by the E2b reader) replaces the aggressive Solver arm as the ``c3verdict`` source:
#   * additional information: the cross-fitted AUC of {baseline + verdict} minus {baseline} for "gold empty", with a
#     whole-utterance cluster bootstrap CI (2,000 draws, seed 20261010);
#   * delivered-metric estimate: the lock Solver column on the v4g base with the rows emptied where the verdict is
#     ``none`` and N1 >= 0.2 (and the fixed N1 grid), pooled SLU-F1 re-scored exactly in-process with the paired
#     cluster bootstrap (10,000 draws, seed 20260915): pp with CI, false fills removed, non-empty exact lost,
#     intent rows moved.

PERCEPTION_SOURCE_PREFIX = "perception-arm:"
GAIN_READ_ID = "SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1"
GAIN_SCHEMA = "saea-slurp-nx-r6-perception-gain-v1"
#: baseline feature sets of the information-gain term: what the downstream node already has.
GAIN_BASELINES = {
    "n1": ["b_n1_share"],
    "n1+prior": ["b_n1_share", "a_rate_rank1"],
    "n1+prior+lock": ["b_n1_share", "a_rate_rank1", "d_lock_items_neg", "d_lock_intent_rate"],
}
VERDICT_FEATURES = ["p_none_score", "p_tag_ok"]
GATE_N1 = 0.2
GATE_DRAWS = 10_000
GATE_SEED = 20260915
#: the R6 run (nx_r6_family.py is the owner of these ids; test_nx_r6_cell_registration.py asserts they agree).
R6_RUN_ID = "SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1"
R6_ATTEMPT_ID = "attempt-slurp-native-stage3-nx-r6-perception-fold-b-generation-v1"
R6_ROWS = 1080


def parse_verdict_source(value: str) -> str | None:
    """``solver`` (the default, the original read) -> ``None``; ``perception-arm:<arm_id>`` -> the arm id."""

    if value == "solver":
        return None
    if value.startswith(PERCEPTION_SOURCE_PREFIX) and value[len(PERCEPTION_SOURCE_PREFIX):]:
        return value[len(PERCEPTION_SOURCE_PREFIX):]
    raise ReadError(f"--verdict-source must be 'solver' or '{PERCEPTION_SOURCE_PREFIX}<arm_id>'; got {value!r}")


def verdict_row(tag_summary: dict) -> tuple[dict, str | None]:
    """The two numeric features and the rank-1 verdict word of one arm note (``none`` / ``some`` / ``unsure`` when the
    tag is ``ok``, else its parse class ``absent`` / ``invalid``). Oriented like every signal: HIGHER = more likely
    empty (none 1.0, unsure 0.5, some 0.0). A note whose rank-1 tag is not ``ok`` carries the neutral 0.5 and
    ``p_tag_ok`` 0, so a missing verdict is a feature, never a median fill."""

    rank1 = tag_summary["rank1"]
    word = rank1["verdict"] if rank1["cls"] == "ok" else rank1["cls"]
    score = {"none": 1.0, "unsure": 0.5, "some": 0.0}.get(word)
    return {"p_none_score": 0.5 if score is None else score, "p_tag_ok": 0.0 if score is None else 1.0}, word


def boot_auc_increment(s_new, s_base, labels, clusters, draws: int = AUC_DRAWS, seed: int = AUC_SEED):
    """CI95 of ``AUC(s_new) - AUC(s_base)`` under one shared whole-cluster resample per draw."""

    import numpy as np
    new = np.asarray(s_new, dtype=np.float64)
    base = np.asarray(s_base, dtype=np.float64)
    y = np.asarray(labels, dtype=bool)
    keys = sorted(set(clusters))
    index = {c: k for k, c in enumerate(keys)}
    members = defaultdict(list)
    for row, c in enumerate(clusters):
        members[index[c]].append(row)
    members = [np.array(members[k]) for k in range(len(keys))]
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        pick = rng.integers(0, len(keys), size=len(keys))
        rows = np.concatenate([members[k] for k in pick])
        a, b = auc(new[rows], y[rows]), auc(base[rows], y[rows])
        if a is not None and b is not None:
            out.append(a - b)
    if not out:
        return None
    return [round(float(np.percentile(out, 2.5)), 4), round(float(np.percentile(out, 97.5)), 4)]


def gate_metrics(base, base_empty, fired, gold_empty, boot) -> dict:
    """The lock Solver column with the fired rows emptied: pooled SLU-F1 pp with its paired CI95, the false fills removed,
    the non-empty exact rows lost and gained, the intent rows moved."""

    new = mix(base, base, base_empty, fired, "empty")
    m = column_metrics(base, new, gold_empty)
    c = boot.contrast(base, new)
    return {
        "fired": int(sum(fired)),
        "fired_empty_gold": int(sum(f and e for f, e in zip(fired, gold_empty))),
        "delta_slu_pp": m["delta_slu_pp"], "ci95_slu_pp": c["ci95_slu_pp"],
        "delta_intent_pp": c["delta_intent_pp"],
        "false_fill_rows_base": m["false_fill_rows_base"], "false_fill_rows_new": m["false_fill_rows_new"],
        "false_fills_removed": m["false_fill_rows_base"] - m["false_fill_rows_new"],
        "nonempty_exact_lost": m["nonempty_exact_lost"], "nonempty_exact_gained": m["nonempty_exact_gained"],
        "intent_rows_moved": m["intent_rows_changed"], "rows_changed": m["rows_changed"],
    }


def perception_gain_core(
    *, ids, signals, gold_empty, utt, verdicts, rank1_values, base, base_empty, baseline: str,
    gate_n1: float = GATE_N1, grid=N1_THRESHOLDS, auc_draws: int = AUC_DRAWS, auc_seed: int = AUC_SEED,
    gate_draws: int = GATE_DRAWS, gate_seed: int = GATE_SEED,
) -> dict:
    """The information-gain term and the gate estimate of one Perception arm's rank-1 verdict. Pure: ``signals[sid]``
    carries the baseline features (``b_n1_share``, ``a_rate_rank1`` and, for ``n1+prior+lock``, the two ``d_lock_*``),
    ``verdicts[sid]`` the two verdict features, ``rank1_values[sid]`` the rank-1 verdict word (:func:`verdict_row`); ``base`` /
    ``base_empty`` are the lock Solver column on the v4g base and the same column with every row emptied
    (10 count columns per row, :data:`DRV.COUNT_FIELDS` + intent)."""

    import numpy as np

    if baseline not in GAIN_BASELINES:
        raise ReadError(f"--gain-baseline must be one of {sorted(GAIN_BASELINES)}; got {baseline!r}")
    ids = list(ids)
    features = GAIN_BASELINES[baseline]
    for sid in ids:
        missing = [f for f in features if signals[sid].get(f) is None]
        if missing:
            raise ReadError(f"{sid}: baseline feature(s) {missing} are not computable")
        signals[sid] = {**signals[sid], **verdicts[sid]}
    labels = [int(e) for e in gold_empty]
    halves = [half_of(u) for u in utt]
    s_base = crossfit_scores(ids, signals, features, labels, halves)
    s_new = crossfit_scores(ids, signals, features + VERDICT_FEATURES, labels, halves)
    s_verdict = [signals[s]["p_none_score"] for s in ids]
    a_base, a_new = auc(s_base, labels), auc(s_new, labels)
    increment = None if a_base is None or a_new is None else a_new - a_base
    per_half = {}
    for k in (0, 1):
        pick = [i for i, h in enumerate(halves) if h == k]
        hb = auc([s_base[i] for i in pick], [labels[i] for i in pick])
        hn = auc([s_new[i] for i in pick], [labels[i] for i in pick])
        per_half[f"half_{k}"] = {"rows": len(pick), "increment": None if hb is None or hn is None else r4(hn - hb)}
    ci = boot_auc_increment(s_new, s_base, labels, utt, draws=auc_draws, seed=auc_seed)
    gain = {
        "baseline": baseline, "baseline_features": features, "verdict_features": VERDICT_FEATURES,
        "rows": len(ids), "empty_gold_rows": int(sum(labels)),
        "rows_with_ok_rank1_tag": int(sum(1 for s in ids if verdicts[s]["p_tag_ok"] == 1.0)),
        "rank1_verdict_counts": dict(sorted(Counter(str(rank1_values[s]) for s in ids).items())),
        "auc_baseline": r4(a_base), "auc_with_verdict": r4(a_new),
        "auc_verdict_alone": r4(auc(s_verdict, labels)),
        "auc_verdict_alone_ci95": boot_auc(s_verdict, labels, utt, draws=auc_draws, seed=auc_seed),
        "increment": r4(increment), "increment_ci95": ci,
        "additional": bool(ci is not None and ci[0] > 0.0),
        "per_utterance_half": per_half,
        "cross_fit": "L2 logistic regression fitted on one utterance-hash half, scored on the other (both directions)",
        "bootstrap": {"unit": "whole utterance", "draws": auc_draws, "seed": auc_seed},
    }
    boot = DRV.Bootstrap(ids, dict(zip(ids, utt)), draws=gate_draws, seed=gate_seed)
    n1 = [signals[s]["b_n1_share"] for s in ids]
    none = [rank1_values[s] == "none" for s in ids]

    def evaluate(fired):
        return gate_metrics(base, base_empty, fired, gold_empty, boot)

    cross_with = crossfit_rule(ids, s_new, base, base, base_empty, gold_empty, halves, "empty", boot)
    cross_without = crossfit_rule(ids, s_base, base, base, base_empty, gold_empty, halves, "empty", boot)
    gate = {
        "base": "lock Solver column after the registered v4g normaliser, scored in-process (pooled SLU-F1)",
        "rule": f"empty the lock row where the rank-1 verdict is E=none AND N1 >= {gate_n1}",
        "primary": {"gate": f"E=none and n1>={gate_n1}",
                    **evaluate([bool(v and x >= gate_n1) for v, x in zip(none, n1)])},
        "grid_verdict_and_n1": {f"n1>={t}": evaluate([bool(v and x >= t) for v, x in zip(none, n1)]) for t in grid},
        "verdict_ungated": evaluate(none),
        "n1_gate_alone": {f"n1>={t}": evaluate([bool(x >= t) for x in n1]) for t in (gate_n1,)},
        "crossfit_top_share_with_verdict": cross_with,
        "crossfit_top_share_without_verdict": cross_without,
        "exchange_rates_pp_per_row": {"false_fill_removed": 0.033, "nonempty_exact_lost": -0.070},
        "bootstrap": {"unit": "whole utterance", "draws": gate_draws, "seed": gate_seed},
    }
    return {"gain": gain, "gate": gate}


def render_gain(report: dict) -> str:
    g, gate = report["gain"], report["gate"]
    p = gate["primary"]
    out = [f"# {report['read_id']} tables ({report['verdict_source']}, baseline {g['baseline']})", "",
           "DESCRIPTIVE; development numbers; zero contacts.", "",
           f"rows {g['rows']} ({g['empty_gold_rows']} empty-gold); rank-1 tags ok on {g['rows_with_ok_rank1_tag']}; "
           f"verdicts {g['rank1_verdict_counts']}", "",
           "## Information gain (cross-fitted AUC for \"gold empty\")", "",
           md(["baseline", "AUC baseline", "AUC with verdict", "increment", "CI95", "additional (CI-LB > 0)",
               "verdict alone AUC [CI95]"],
              [[g["baseline"], g["auc_baseline"], g["auc_with_verdict"], g["increment"], g["increment_ci95"],
                g["additional"], f"{g['auc_verdict_alone']} {g['auc_verdict_alone_ci95']}"]]),
           "", f"per utterance half: {json.dumps(g['per_utterance_half'])}", "",
           "## Gate estimate on the lock Solver column (v4g base)", "",
           md(["rule", "fired", "fired empty-gold", "delta SLU pp [CI95]", "false fills removed", "non-empty exact lost",
               "intent rows moved"],
              [[p["gate"], p["fired"], p["fired_empty_gold"], f"{p['delta_slu_pp']:+.2f} {ci(p['ci95_slu_pp'])}",
                p["false_fills_removed"], p["nonempty_exact_lost"], p["intent_rows_moved"]]]), "",
           "fixed N1 grid (verdict and N1 >= t):", ""]
    out.append(md(["t", "fired", "delta SLU pp [CI95]", "FF removed", "NE lost", "intent rows"],
                  [[k, v["fired"], f"{v['delta_slu_pp']:+.2f} {ci(v['ci95_slu_pp'])}", v["false_fills_removed"],
                    v["nonempty_exact_lost"], v["intent_rows_moved"]] for k, v in gate["grid_verdict_and_n1"].items()]))
    out += ["", "references:", "",
            md(["variant", "fired", "delta SLU pp [CI95]", "FF removed", "NE lost", "intent rows"],
               [["verdict ungated", *_gate_cells(gate["verdict_ungated"])],
                ["N1 gate alone", *_gate_cells(next(iter(gate["n1_gate_alone"].values())))],
                ["cross-fit top-share with verdict", *_gate_cells(gate["crossfit_top_share_with_verdict"])],
                ["cross-fit top-share without verdict", *_gate_cells(gate["crossfit_top_share_without_verdict"])]]),
            ""]
    return "\n".join(out) + "\n"


def _gate_cells(v: dict) -> list:
    slu = v.get("delta_slu_pp")
    interval = v.get("ci95_slu_pp")
    removed = v.get("false_fills_removed", v.get("false_fill_rows_base", 0) - v.get("false_fill_rows_new", 0))
    return [v.get("fired"), f"{slu:+.2f} {ci(interval)}", removed, v.get("nonempty_exact_lost"),
            v.get("intent_rows_changed", v.get("intent_rows_moved"))]


def build_perception_gain(args) -> dict:
    """The real-data side: opens the sealed R6 run, parses the Perception arm's notes in memory through the E2b reader,
    scores the lock Solver column in-process on the v4g base and hands everything to :func:`perception_gain_core`."""

    import numpy as np
    import slurp_nx_perception_column_read as PCR
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.data.lock import load_lock

    arm = parse_verdict_source(args.verdict_source)
    data_root = Path(args.data_root)
    directory = data_root / "runs" / args.run_id / args.attempt_id
    if not directory.is_dir():
        raise ReadError(f"no sealed attempt directory at {directory}")
    manifest = directory / f"{args.run_id}.run-manifest.json"
    bundle = verify_bundle(manifest)
    sealed = PCR.load_sealed_columns(bundle.outputs_rows, bundle.trace_records,
                                     tag_sets=PCR.parse_tag_set_args(args.tag_set))
    if arm not in sealed["arm_ids"] or arm in (sealed["delivering"], sealed["twin"]):
        raise ReadError(f"{arm!r} is not a candidate arm of the run (arms {list(sealed['arm_ids'])})")
    ids = sorted(sealed["notes"][sealed["delivering"]])
    lock = load_lock(Path(args.lock))
    gold_train = DRV.load_gold(lock, data_root, "train")
    if len(ids) != args.rows or any(s not in gold_train for s in ids):
        raise ReadError("the run's rows are not the expected TRAIN roster covered by the TRAIN gold")
    gold = {s: gold_train[s] for s in ids}
    slot_types = {str(e.type).lower() for row in gold_train.values() for e in row["entities"]}
    table_path = data_root / RATE_TABLE
    table = json.loads(table_path.read_text(encoding="utf-8"))
    pool = load_exemplar_annotations(data_root)
    texts, changed, _version = apply_v4g(ids, sealed["solver_texts"][sealed["delivering"]])
    base, base_empty = score_texts(ids, texts, gold)
    lock_intent = delivered_intent(texts, ids)
    lock_items = {s: base[k][6] + base[k][7] for k, s in enumerate(ids)}
    phases = load_phase_signals(directory / f"{args.run_id}.phases.json", slot_types)
    trace = load_perception_trace(directory / f"{args.run_id}.trace.jsonl", set(ids))
    signals = {s: row_signals(s, phases["rows"][s], trace.get(s, {}), pool, table,
                              lock_items=lock_items[s], lock_intent=lock_intent[s]) for s in ids}
    for name in SIGNAL_DOC:
        filled, _n = fill_missing([signals[s].get(name) for s in ids])
        for s, v in zip(ids, filled):
            signals[s][name] = v
    verdicts, rank1_values = {}, {}
    for s in ids:
        verdicts[s], rank1_values[s] = verdict_row(sealed["notes"][arm][s]["tag"])
    core = perception_gain_core(
        ids=ids, signals=signals, gold_empty=[not gold[s]["entities"] for s in ids],
        utt=[gold[s]["utterance_id"] for s in ids], verdicts=verdicts, rank1_values=rank1_values,
        base=base, base_empty=base_empty, baseline=args.gain_baseline,
    )
    return {
        "read_id": GAIN_READ_ID, "schema": GAIN_SCHEMA, "status": "DESCRIPTIVE",
        "verdict_source": args.verdict_source, "gain_baseline": args.gain_baseline,
        "inputs": {"run_id": args.run_id, "attempt_id": args.attempt_id, "rows": len(ids),
                   "manifest_sha256": digest(manifest), "phases_sha256": phases["sha256"],
                   "rate_table": [RATE_TABLE, digest(table_path)], "exemplar_pool": [pool["relpath"], pool["sha256"]],
                   "tag_sets": {a: list(v) for a, v in sealed["tag_sets"].items()},
                   "lock_v4g_rows_changed": changed,
                   "lock_v4g_slu_f1_pp": round(DRV.pooled(base)["slu_f1_pp"], 4)},
        **core,
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "driver_sha256": digest(Path(__file__)),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------------------
# build


def build(args) -> dict:
    import numpy as np

    data_root = Path(args.data_root)
    from speech_aware_evidence_acquisition.data.lock import load_lock
    lock = load_lock(Path(args.lock))
    gold_train = DRV.load_gold(lock, data_root, "train")
    table_path = data_root / RATE_TABLE
    table = json.loads(table_path.read_text(encoding="utf-8"))
    slot_types = set()
    for row in gold_train.values():
        for e in row["entities"]:
            slot_types.add(str(e.type).lower())
    pool = load_exemplar_annotations(data_root)
    report = {"read_id": READ_ID, "recipe": RECIPE, "schema": SCHEMA, "status": "DESCRIPTIVE",
              "inputs": {"rate_table": [RATE_TABLE, digest(table_path)], "exemplar_pool": [pool["relpath"], pool["sha256"]]},
              "signal_definitions": SIGNAL_DOC, "fold_b": {}}
    ee_wilson = sorted(i for i, n in table["intent_n"].items()
                       if wilson_upper(table["intent_with_entities"].get(i, 0), n) < 0.10)
    report["ee_wilson_intents"] = ee_wilson

    fold_b_rows = {}
    for key, spec in FOLD_B.items():
        directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
        sv = directory / "supply-variants"
        arms = (DELIVERING, TWIN, spec["aggressive"])
        texts, sealed = {}, {}
        files = {}
        for arm in arms:
            fpath = sv / f"arm-{arm}-first-visit-outputs.jsonl"
            spath = sv / f"arm-{arm}-{spec['scorer']}-scores.json"
            texts[arm] = {str(r["sample_id"]): r.get("text") or "" for r in iter_jsonl(fpath)}
            block = json.loads(spath.read_text(encoding="utf-8"))[spec["scorer"]]
            sealed[arm] = {str(r["sample_id"]): r for r in block["per_sample"]}
            files[arm] = {"first_visit": [str(fpath.relative_to(data_root)), digest(fpath)],
                          "scores": [str(spath.relative_to(data_root)), digest(spath)],
                          "official_slu_f1_pp": round(100.0 * float(block["aggregate"]["official"]["slu_f1"]), 4)}
        ids = sorted(texts[DELIVERING])
        if len(ids) != spec["rows"] or any(sorted(texts[a]) != ids or sorted(sealed[a]) != ids for a in arms):
            raise ReadError(f"{key}: arm columns do not cover the same {spec['rows']} rows")
        if any(s not in gold_train for s in ids):
            raise ReadError(f"{key}: roster ids absent from the TRAIN gold")
        gold = {s: gold_train[s] for s in ids}
        cols, cols_empty = {}, {}
        for arm in arms:
            m, m_e = score_texts(ids, texts[arm], gold)
            sv_m = np.array([DRV.sealed_vector(sealed[arm][s]) for s in ids])
            bad = int(np.sum(np.any(np.abs(m - sv_m) > 1e-9, axis=1)))
            if bad:
                raise ReadError(f"{key}/{arm}: in-process scoring differs from the sealed per-sample fields on {bad} rows")
            if abs(DRV.pooled(m)["slu_f1_pp"] - files[arm]["official_slu_f1_pp"]) > 1e-3:
                raise ReadError(f"{key}/{arm}: pooled in-process SLU-F1 does not reproduce the official aggregate")
            cols[arm], cols_empty[arm] = m, m_e
        # v4g applied in-process to every column
        cols_v4g, cols_v4g_empty, v4g_changed = {}, {}, {}
        for arm in arms:
            t4, changed, version = apply_v4g(ids, texts[arm])
            cols_v4g[arm], cols_v4g_empty[arm] = score_texts(ids, t4, gold)
            v4g_changed[arm] = changed
            if arm == DELIVERING:
                lock_intent = delivered_intent(t4, ids)
        phases = load_phase_signals(directory / f"{spec['run_id']}.phases.json", slot_types)
        trace = load_perception_trace(directory / f"{spec['run_id']}.trace.jsonl", set(ids))
        gold_empty = [not gold[s]["entities"] for s in ids]
        utt = [gold[s]["utterance_id"] for s in ids]
        halves = [half_of(u) for u in utt]
        lock_items = {s: cols[DELIVERING][k][6] + cols[DELIVERING][k][7] for k, s in enumerate(ids)}
        signals = {s: row_signals(s, phases["rows"][s], trace.get(s, {}), pool, table,
                                  lock_items=lock_items[s], lock_intent=lock_intent[s]) for s in ids}
        missing = {name: sum(signals[s].get(name) is None for s in ids) for name in SIGNAL_DOC}
        for name in SIGNAL_DOC:
            filled, _n = fill_missing([signals[s].get(name) for s in ids])
            for s, v in zip(ids, filled):
                signals[s][name] = v
        labels = [int(e) for e in gold_empty]
        for cname, feats in COMBOS.items():
            scores = crossfit_scores(ids, signals, feats, labels, halves)
            for s, v in zip(ids, scores):
                signals[s][cname] = v
        sep = {}
        for name in list(SIGNAL_DOC) + list(COMBOS):
            vals = [signals[s][name] for s in ids]
            a = auc(vals, labels)
            sep[name] = {"auc_empty": r4(a), "ci95": boot_auc(vals, labels, utt),
                         "missing_rows_filled_with_median": missing.get(name, 0),
                         "median_empty_gold": r4(float(np.median([v for v, e in zip(vals, gold_empty) if e]))),
                         "median_nonempty_gold": r4(float(np.median([v for v, e in zip(vals, gold_empty) if not e])))}
        # aggressive arm as a classifier of emptiness (its own presence judgement)
        agg = spec["aggressive"]
        agg_empty = [int(cols[agg][k][6] + cols[agg][k][7] == 0) for k in range(len(ids))]
        lock_empty = [int(lock_items[s] == 0) for s in ids]
        judge = {}
        for name, flags in (("lock", lock_empty), (agg, agg_empty)):
            tp = sum(f and e for f, e in zip(flags, gold_empty))
            fp = sum(f and not e for f, e in zip(flags, gold_empty))
            judge[name] = {"answers_empty_rows": int(sum(flags)), "empty_on_empty_gold": int(tp),
                           "empty_on_nonempty_gold": int(fp),
                           "recall_of_empty_gold": r4(tp / max(1, sum(gold_empty))),
                           "precision": r4(tp / max(1, tp + fp))}
        boot = DRV.Bootstrap(ids, dict(zip(ids, utt)))
        result = {"run_id": spec["run_id"], "attempt": spec["attempt"], "aggressive_arm": agg, "files": files,
                  "phases_sha256": phases["sha256"], "phase_checks": phases["checks"],
                  "trace_rows_with_audio": sum(1 for s in ids if trace.get(s, {}).get("audio_seconds")),
                  "rows": len(ids), "empty_gold_rows": int(sum(gold_empty)), "separability": sep,
                  "emptiness_judgement": judge, "v4g_rows_changed": v4g_changed,
                  "levels": {f"{b}:{arm}": round(DRV.pooled(c[arm])["slu_f1_pp"], 4)
                             for b, c in (("v3", cols), ("v4g", cols_v4g)) for arm in arms}}
        # Q2: counterfactual sweeps on both bases
        sig_names = PRE_SIGNALS + POST_SIGNALS + list(COMBOS)
        q2 = {}
        for bname, C, CE in (("v3", cols, cols_empty), ("v4g", cols_v4g, cols_v4g_empty)):
            base, alt, base_empty = C[DELIVERING], C[agg], CE[DELIVERING]
            ref = {
                "aggressive_everywhere": column_metrics(base, alt, gold_empty),
                "twin": column_metrics(base, C[TWIN], gold_empty),
                "oracle_c3_on_empty_gold": column_metrics(base, mix(base, alt, base_empty, gold_empty, "c3"), gold_empty),
                "oracle_empty_on_empty_gold": column_metrics(base, mix(base, alt, base_empty, gold_empty, "empty"), gold_empty),
                "c3verdict_everywhere": column_metrics(base, mix(base, alt, base_empty, [True] * len(ids), "c3verdict"), gold_empty),
            }
            for rk in ("aggressive_everywhere", "c3verdict_everywhere"):
                newc = alt if rk == "aggressive_everywhere" else mix(base, alt, base_empty, [True] * len(ids), "c3verdict")
                ref[rk]["ci95_slu_pp"] = boot.contrast(base, newc)["ci95_slu_pp"]
            rows = sweep(ids, signals, sig_names, base, alt, base_empty, gold_empty, halves, boot)
            best = {}
            for beh in BEHAVIOURS:
                for group, names in (("pre", PRE_SIGNALS + ["x_rate_n1", "x_rate_n1_note", "x_pre_all"]),
                                     ("post", POST_SIGNALS + ["x_pre_all_plus_lock"])):
                    cands = [r for r in rows if r["behaviour"] == beh and r["signal"] in names]
                    if not cands:
                        continue
                    top = max(cands, key=lambda r: (r["delta_slu_pp"], -r["fired"]))
                    values = [signals[s][top["signal"]] for s in ids]
                    if top["rule"].startswith("top"):
                        fired, _cut = fire_by_share(values, int(top["rule"].split()[1]) / 100.0)
                    elif top["rule"].startswith("rate"):
                        fired = [(1.0 - v) < top["cut"] for v in values]
                    else:
                        fired = [v >= top["cut"] for v in values]
                    newc = mix(base, alt, base_empty, fired, beh)
                    entry = dict(top)
                    entry["ci95_slu_pp_selected_in_sample"] = boot.contrast(base, newc)["ci95_slu_pp"]
                    entry["crossfit"] = crossfit_rule(ids, values, base, alt, base_empty, gold_empty, halves, beh, boot)
                    best[f"{beh}:{group}"] = entry
            # per-signal best (point) for the table
            per_signal = {}
            for r in rows:
                k = f"{r['signal']}|{r['behaviour']}"
                if k not in per_signal or r["delta_slu_pp"] > per_signal[k]["delta_slu_pp"]:
                    per_signal[k] = r
            q2[bname] = {"reference": ref, "best": best, "per_signal_best": per_signal, "sweep_rows": len(rows),
                         "sweep": rows if args.keep_sweep else None}
        result["counterfactual"] = q2
        # the N1 signal by bin: rows, empty-gold share, lock false fill, aggressive-arm emptying on non-empty rows
        bins = []
        for lo, hi in zip(N1_BINS[:-1], N1_BINS[1:]):
            ks = [k for k, s in enumerate(ids) if lo <= signals[s]["b_n1_share"] < hi]
            emp = [k for k in ks if gold_empty[k]]
            ne = [k for k in ks if not gold_empty[k]]
            bins.append({"n1_share": f"[{lo:.1f}, {min(hi, 1.0):.1f}{']' if hi > 1 else ')'}", "rows": len(ks),
                         "empty_gold": len(emp),
                         "lock_false_fill": sum(1 for k in emp if lock_items[ids[k]] > 0),
                         "aggressive_false_fill": sum(1 for k in emp if agg_empty[k] == 0),
                         "nonempty_lock_exact": sum(1 for k in ne if row_flags(cols[DELIVERING][k])[1]),
                         "nonempty_lock_exact_lost_by_aggressive": sum(
                             1 for k in ne if row_flags(cols[DELIVERING][k])[1] and not row_flags(cols[agg][k])[1]),
                         "nonempty_aggressive_answers_empty": sum(1 for k in ne if agg_empty[k] == 1)})
        result["n1_bins"] = bins
        # declared fixed rules (the same rule for both iterations): c3verdict / c3 gated by absolute N1 cuts
        fixed = {}
        for bname, C, CE in (("v3", cols, cols_empty), ("v4g", cols_v4g, cols_v4g_empty)):
            for beh in ("c3verdict", "c3"):
                for t in N1_THRESHOLDS:
                    fired = [signals[s]["b_n1_share"] >= t for s in ids]
                    newc = mix(C[DELIVERING], C[agg], CE[DELIVERING], fired, beh)
                    m = column_metrics(C[DELIVERING], newc, gold_empty)
                    m["ci95_slu_pp"] = boot.contrast(C[DELIVERING], newc)["ci95_slu_pp"]
                    m["fired"] = int(sum(fired))
                    fixed[f"{bname}|{beh}|n1>={t}"] = m
        result["fixed_n1_rules"] = fixed
        # Q3: non-empty rows the aggressive arm lost (v3, the sealed columns)
        best_pre = q2["v3"]["best"].get("c3:pre")
        values = [signals[s][best_pre["signal"]] for s in ids] if best_pre else None
        if best_pre and best_pre["rule"].startswith("top"):
            fired_best, _ = fire_by_share(values, int(best_pre["rule"].split()[1]) / 100.0)
        elif best_pre and best_pre["rule"].startswith("rate"):
            fired_best = [(1.0 - v) < best_pre["cut"] for v in values]
        elif best_pre:
            fired_best = [v >= best_pre["cut"] for v in values]
        rate_fire = [(1.0 - signals[s]["a_rate_rank1"]) < 0.30 for s in ids]
        lost = []
        for k, s in enumerate(ids):
            if gold_empty[k]:
                continue
            _bp, bx = row_flags(cols[DELIVERING][k])
            ap, ax = row_flags(cols[agg][k])
            if bx and not ax:
                lost.append((k, s, ap))
        intents = Counter(f"{gold[s]['scenario']}_{gold[s]['action']}" for _k, s, _a in lost)
        types = Counter(str(e.type) for _k, s, _a in lost for e in gold[s]["entities"])
        def dist(values_):
            return {"min": r4(min(values_)), "median": r4(sorted(values_)[len(values_) // 2]), "max": r4(max(values_))} if values_ else None
        ex_with = [round(20 * (1.0 - signals[s]["b_n1_share"])) for _k, s, _a in lost]
        nonempty_all_ex_with = [round(20 * (1.0 - signals[s]["b_n1_share"])) for k, s in enumerate(ids) if not gold_empty[k]]
        result["lost_nonempty_rows"] = {
            "rows": len(lost),
            "emptied_entirely": sum(1 for _k, _s, a in lost if a == 0),
            "truncated_or_changed": sum(1 for _k, _s, a in lost if a > 0),
            "gold_entities_per_row": dict(sorted(Counter(len(gold[s]["entities"]) for _k, s, _a in lost).items())),
            "gold_intents": dict(intents.most_common()),
            "gold_slot_types": dict(types.most_common()),
            "exemplars_with_entities_of_20": dist(ex_with),
            "exemplars_with_entities_of_20_all_nonempty_rows": dist(nonempty_all_ex_with),
            "rank1_intent_train_entity_rate": dist([1.0 - signals[s]["a_rate_rank1"] for _k, s, _a in lost]),
            "rank1_intent_train_entity_rate_all_nonempty_rows": dist(
                [1.0 - signals[s]["a_rate_rank1"] for k, s in enumerate(ids) if not gold_empty[k]]),
            "perception_rank1_unresolved": dict(sorted(Counter(int(-signals[s]["c_unresolved_rank1_neg"])
                                                               for _k, s, _a in lost).items())),
            "perception_rank1_slot_named": dict(sorted(Counter(int(-signals[s]["c_slot_named_rank1_neg"])
                                                               for _k, s, _a in lost).items())),
            "perception_rank1_equals_gold_intent": sum(
                1 for _k, s, _a in lost if (phases["rows"][s]["note"] or {}).get("ids", [None])[:1]
                == [f"{gold[s]['scenario']}_{gold[s]['action']}"]),
            "best_pre_rule": None if not best_pre else {"signal": best_pre["signal"], "rule": best_pre["rule"]},
            "best_pre_rule_fires_on_lost_rows": None if not best_pre else sum(1 for k, _s, _a in lost if fired_best[k]),
            "rate_below_0_30_fires_on_lost_rows": sum(1 for k, _s, _a in lost if rate_fire[k]),
        }
        report["fold_b"][key] = result
        fold_b_rows[key] = {"ids": ids, "signals": signals, "gold_empty": gold_empty, "cols_v4g": cols_v4g,
                            "cols_v4g_empty": cols_v4g_empty, "utt": utt}

    # Q4: deterministic v5 = v4g + 'empty when the rule fires', on A2 / Fold A / Fold B (lock column, i1)
    report["v5"] = v5_read(args, data_root, lock, table, pool, slot_types, fold_b_rows["i1"])
    report["contacts"] = {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                          "scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0}
    report["driver_sha256"] = digest(Path(__file__))
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return report


V5_RULES = ([("d_lock_intent_rate", "rate", t) for t in RATE_THRESHOLDS]
            + [("a_rate_rank1", "rate", t) for t in RATE_THRESHOLDS]
            + [("b_n1_share", "share", t) for t in N1_THRESHOLDS])


def v5_fire(signals, ids, name, kind, t):
    if kind == "rate":
        return [(1.0 - signals[s][name]) < t for s in ids]
    return [signals[s][name] >= t for s in ids]


def v5_read(args, data_root, lock, table, pool, slot_types, fold_b) -> dict:
    import numpy as np
    pools = {}
    for key in ("a2", "fold-a"):
        spec = dict(DRV.POOLS[key])
        directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
        gold_all = DRV.load_gold(lock, data_root, spec["split"])
        delivered = DRV.load_delivered(data_root, spec)
        ids = sorted(delivered["rows"])
        gold = {s: gold_all[s] for s in ids}
        del gold_all
        texts = {str(r["sample_id"]): r.get("text") or "" for r in iter_jsonl(directory / f"{spec['run_id']}.outputs.jsonl")}
        base3, _ = score_texts(ids, texts, gold)
        sv = np.array([DRV.sealed_vector(delivered["sealed"][s]) for s in ids])
        if int(np.sum(np.any(np.abs(base3 - sv) > 1e-9, axis=1))):
            raise ReadError(f"{key}: in-process scoring differs from the sealed per-sample fields")
        t4, changed, _v = apply_v4g(ids, texts)
        base, base_empty = score_texts(ids, t4, gold)
        intents = delivered_intent(t4, ids)
        phases = load_phase_signals(directory / f"{spec['run_id']}.phases.json", slot_types)
        signals = {}
        for s in ids:
            sig = row_signals(s, phases["rows"][s], {}, pool, table, lock_items=0, lock_intent=intents[s])
            signals[s] = sig
        for name in ("d_lock_intent_rate", "a_rate_rank1", "b_n1_share"):
            filled, _n = fill_missing([signals[s].get(name) for s in ids])
            for s, v in zip(ids, filled):
                signals[s][name] = v
        pools[key] = {"ids": ids, "signals": signals, "base": base, "base_empty": base_empty,
                      "gold_empty": [not gold[s]["entities"] for s in ids],
                      "utt": [gold[s]["utterance_id"] for s in ids],
                      "meta": {"run_id": spec["run_id"], "rows": len(ids), "v4g_rows_changed": changed,
                               "v3_slu_f1_pp": round(DRV.pooled(base3)["slu_f1_pp"], 4),
                               "v4g_slu_f1_pp": round(DRV.pooled(base)["slu_f1_pp"], 4),
                               "phases_sha256": phases["sha256"]}}
    pools["fold-b-lock"] = {"ids": fold_b["ids"], "signals": fold_b["signals"], "base": fold_b["cols_v4g"][DELIVERING],
                            "base_empty": fold_b["cols_v4g_empty"][DELIVERING], "gold_empty": fold_b["gold_empty"],
                            "utt": fold_b["utt"],
                            "meta": {"run_id": FOLD_B["i1"]["run_id"], "rows": len(fold_b["ids"]),
                                     "v4g_slu_f1_pp": round(DRV.pooled(fold_b["cols_v4g"][DELIVERING])["slu_f1_pp"], 4)}}
    table_rows = []
    for name, kind, t in V5_RULES:
        row = {"signal": name, "rule": f"{'rate <' if kind == 'rate' else 'share >='} {t}", "_rule": (name, kind, t)}
        for key, P in pools.items():
            fired = v5_fire(P["signals"], P["ids"], name, kind, t)
            new = mix(P["base"], P["base"], P["base_empty"], fired, "empty")
            m = column_metrics(P["base"], new, P["gold_empty"])
            row[key] = {"fired": int(sum(fired)), "delta_slu_pp": m["delta_slu_pp"],
                        "false_fill_removed": m["false_fill_rows_base"] - m["false_fill_rows_new"],
                        "nonempty_exact_lost": m["nonempty_exact_lost"]}
        table_rows.append(row)
    sel = max(table_rows, key=lambda r: r["a2"]["delta_slu_pp"])
    name, kind, t = sel["_rule"]
    selected = {"signal": name, "rule": sel["rule"], "selected_on": "a2 (point maximum over the declared grid)"}
    for key, P in pools.items():
        fired = v5_fire(P["signals"], P["ids"], name, kind, t)
        new = mix(P["base"], P["base"], P["base_empty"], fired, "empty")
        boot = DRV.Bootstrap(P["ids"], dict(zip(P["ids"], P["utt"])))
        c = boot.contrast(P["base"], new)
        selected[key] = {"delta_slu_pp": c["delta_slu_pp"], "ci95_slu_pp": c["ci95_slu_pp"],
                         "delta_intent_pp": c["delta_intent_pp"], "fired": int(sum(fired)),
                         "clears_floor_0_67": c["ci95_slu_pp"][0] > 0 and c["delta_slu_pp"] >= FLOOR_PP}
    for r in table_rows:
        r.pop("_rule")
    return {"pools": {k: P["meta"] for k, P in pools.items()}, "grid": table_rows, "selected": selected,
            "base": "v4g applied in-process to the delivered column (A2, Fold A) / the R1 lock column (Fold B)"}


# ---------------------------------------------------------------------------
# rendering


def md(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def ci(c) -> str:
    return "-" if not c else f"[{c[0]:+.2f}, {c[1]:+.2f}]"


def render(rep: dict) -> str:
    out = [f"# {rep['read_id']} tables", "", "DESCRIPTIVE; development numbers; zero contacts.", ""]
    for key, r in rep["fold_b"].items():
        out += [f"## Fold B {key} ({r['run_id']}, aggressive arm `{r['aggressive_arm']}`)", "",
                f"levels: {r['levels']}", "", "### Separability (AUC, higher signal = empty; cluster bootstrap CI95)", ""]
        out.append(md(["signal", "AUC", "CI95", "median empty-gold", "median non-empty", "filled"],
                      [[k, v["auc_empty"], v["ci95"], v["median_empty_gold"], v["median_nonempty_gold"],
                        v["missing_rows_filled_with_median"]] for k, v in r["separability"].items()]))
        out += ["", f"emptiness judgement: {json.dumps(r['emptiness_judgement'])}", ""]
        for bname, q in r["counterfactual"].items():
            out += [f"### Counterfactual on the {bname} base", "", "reference: " + json.dumps(q["reference"]), ""]
            out.append(md(["key", "signal", "rule", "fired", "fired empty-gold", "delta pp", "CI95 (in-sample)",
                           "FF base->new", "NE lost/gained", "intent rows", "cross-fit delta", "cross-fit CI95"],
                          [[k, b["signal"], b["rule"], b["fired"], b["fired_empty_gold"], b["delta_slu_pp"],
                            ci(b["ci95_slu_pp_selected_in_sample"]),
                            f"{b['false_fill_rows_base']}->{b['false_fill_rows_new']}",
                            f"{b['nonempty_exact_lost']}/{b['nonempty_exact_gained']}", b["intent_rows_changed"],
                            b["crossfit"]["delta_slu_pp"], ci(b["crossfit"]["ci95_slu_pp"])]
                           for k, b in q["best"].items()]))
            out += ["", "per-signal best point:", ""]
            out.append(md(["signal|behaviour", "rule", "fired", "delta pp", "FF base->new", "NE lost"],
                          [[k, v["rule"], v["fired"], v["delta_slu_pp"],
                            f"{v['false_fill_rows_base']}->{v['false_fill_rows_new']}", v["nonempty_exact_lost"]]
                           for k, v in sorted(q["per_signal_best"].items())]))
            out.append("")
        out += ["### Lost non-empty rows", "", "```", json.dumps(r["lost_nonempty_rows"], indent=1), "```", ""]
    v5 = rep["v5"]
    out += ["## v5 = v4g + empty when the rule fires", "", json.dumps(v5["pools"]), ""]
    out.append(md(["signal", "rule"] + [f"{k} delta (fired, FF-, NE lost)" for k in v5["pools"]],
                  [[r["signal"], r["rule"]] + [f"{r[k]['delta_slu_pp']:+.2f} ({r[k]['fired']}, {r[k]['false_fill_removed']}, "
                                               f"{r[k]['nonempty_exact_lost']})" for k in v5["pools"]]
                   for r in v5["grid"]]))
    out += ["", "selected: " + json.dumps(v5["selected"]), ""]
    return "\n".join(out) + "\n"


def strip_time(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if '"generated_at"' not in line)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--keep-sweep", action="store_true", help="persist every sweep row in report.json")
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the files on record")
    parser.add_argument("--verdict-source", default="solver",
                        help="'solver' (default: the original R1-column read) or 'perception-arm:<arm_id>' (R6-P1: the "
                             "rank-1 E=none of that arm's sealed Perception column, notes parsed in memory by the E2b reader)")
    parser.add_argument("--gain-baseline", default="n1+prior", choices=sorted(GAIN_BASELINES),
                        help="the features the downstream node already has (perception-arm mode)")
    parser.add_argument("--run-id", default=R6_RUN_ID, help="the sealed R6 run (perception-arm mode)")
    parser.add_argument("--attempt-id", default=R6_ATTEMPT_ID, help="the sealed R6 attempt (perception-arm mode)")
    parser.add_argument("--rows", type=int, default=R6_ROWS, help="expected row count (perception-arm mode)")
    parser.add_argument("--tag-set", action="append", default=[], metavar="ARM=VALUES",
                        help="the E= values an arm allows (E2b reader), e.g. p3=none,some,unsure; repeatable")
    args = parser.parse_args(argv)
    if parse_verdict_source(args.verdict_source) is not None:
        if args.check or args.keep_sweep:
            raise SystemExit("--check and --keep-sweep belong to the original read, not to --verdict-source perception-arm")
        report = build_perception_gain(args)
        out_dir = (Path(args.data_root) / "analysis" / GAIN_READ_ID
                   / parse_verdict_source(args.verdict_source) / args.gain_baseline.replace("+", "-"))
        if out_dir.exists():
            raise SystemExit(f"refusing to overwrite {out_dir}")
        texts = {"report.json": json.dumps(report, indent=1, sort_keys=True) + "\n", "tables.md": render_gain(report)}
        out_dir.mkdir(parents=True)
        for name, text in texts.items():
            (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
        print("wrote", out_dir)
        print(json.dumps({n: hashlib.sha256(strip_time(t).encode("utf-8")).hexdigest() for n, t in texts.items()}, indent=1))
        return 0
    report = build(args)
    out_dir = Path(args.data_root) / "analysis" / READ_ID
    texts = {"report.json": json.dumps(report, indent=1, sort_keys=True) + "\n", "tables.md": render(report)}
    hashes = {n: hashlib.sha256(strip_time(t).encode("utf-8")).hexdigest() for n, t in texts.items()}
    if args.check:
        same = all(strip_time((out_dir / n).read_text(encoding="utf-8")) == strip_time(t) for n, t in texts.items())
        print("IDENTICAL" if same else "DIFFERENT", json.dumps(hashes, indent=1))
        return 0 if same else 1
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    (out_dir / "content-sha256.json").write_text(json.dumps(hashes, indent=1, sort_keys=True) + "\n",
                                                 encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps(hashes, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
