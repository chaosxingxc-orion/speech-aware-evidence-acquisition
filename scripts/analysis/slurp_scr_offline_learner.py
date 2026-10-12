#!/usr/bin/env python3
"""SCR TF-0: the offline learner of sealed-credit routing (SCR) over typed actions (TF-RL line, owner decision 252).

Offline, zero GPU, zero model contact. Design of record:
``docs/readiness/2026-10-10-slurp-tfrl-sealed-credit-routing-design-v1.md`` sections 1-3 and 6.

SCR is an off-policy, direct-method router. Every sealed same-flight column is a COMPLETE counterfactual (every action has an
outcome on every row), so the policy is a regression from a model-free pre-Solver context signature to the per-row reward
difference (action minus lock), fitted on one utterance-hash half and scored on the other (cross-fitting, both directions).
A row is routed to the action with the highest predicted gain only when that gain exceeds a margin tied to the exchange
rates; otherwise it stays on the lock.

Pools (TRAIN Fold B, 1,080 rows, all sealed):

* ``i1``  NX R1 iteration 1 Solver template column (arms lock, aa, r1-c1 .. r1-c5);
* ``i2``  NX R1 iteration 2 Solver template column (arms lock, aa, r1-i2-c1 .. r1-i2-c5);
* ``r6``  NX R6-P1 Perception template column, each arm followed by its own level-2 Solver answer (arms lock, aa, p1, p2, p3).

Each arm's rendered first-visit column ``supply-variants/arm-<id>-first-visit-outputs.jsonl`` is scored in-process with the
official scorer path of the R6 offline driver (v3 as sealed, then the registered v4g normaliser, which is what lock v2.2
delivers); the v3 in-process score must reproduce the sealed per-sample fields and the official pooled aggregate or the run
stops. Reward of an action on a row = the change in the row's official count vector (word/char TP/FP/FN, slot-exact TP/FP/FN,
intent indicator) against the SAME-FLIGHT lock row; the routed column is the reference lock column (i1) plus the chosen
actions' same-flight deltas (node-local credit), re-scored exactly (pooled official SLU-F1) with the paired whole-utterance
cluster bootstrap (10,000 draws, seed 20260915). ``empty`` is the post-Solver deterministic action "empty the lock row".

Gold discipline: gold enters only offline through the governed SLURP loader (the v4 search driver's ``load_gold``, TRAIN),
as reward and as evaluation strata; the context signature is built from sealed receipts and the pinned TRAIN tables only and
takes no gold argument. The test split is never read. Text discipline: no utterance text, transcript, gold value, filler,
exemplar text, note body or model output is printed or persisted -- ids, counts, rates, pp, CIs, hashes and labels only.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_scr_offline_learner.py --dry
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_scr_offline_learner.py --no-write   # full run, nothing written
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_scr_offline_learner.py              # write-once outputs
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

READ_ID = "SAEA-SLURP-SCR-TF0-V1"
TABLE_ID = "SAEA-SLURP-SCR-ROUTING-TABLE-V1"
RECIPE = "slurp-scr-tf0-offline-learner-v1"
SCHEMA = "saea-slurp-scr-tf0-v1"
TABLE_SCHEMA = "saea-slurp-scr-routing-table-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROSTER = "docs/receipts/rosters/slurp-evo-fold-b-v2.json"
BOOT_DRAWS = 10_000
BOOT_SEED = 20260915
FLOOR_PP = 0.67                    # the offline floor (design section 1)
MIN_LEAF = 60
#: default routing margin = this fraction of the false-fill exchange rate, per routed row: a leaf must on average deliver one
#: removed false fill (0.033 pp) per ten routed rows. (The first draft used FLOOR_PP / MIN_LEAF = 0.0112 pp/row, i.e. a
#: 60-row leaf must clear the whole 0.67 pp floor alone; no realistic leaf does, it routed zero rows, and it stays in the
#: sensitivity table.)
MARGIN_FRACTION = 0.1
MAX_DEPTH = 3
#: exchange rates, pp of pooled official SLU-F1 per row (docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md)
RATE_FALSE_FILL_REMOVED = 0.033
RATE_NONEMPTY_EXACT = 0.070
RATE_RAW_EXACT = 0.056
NOOP = "lock"
EMPTY = "empty"
CONTACTS = {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer_subprocess": 0,
            "network": 0, "gpu": 0, "paid_api": 0}


class ScrError(RuntimeError):
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
R6 = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_r6_upstream_empty.py", "slurp_nx_r6_upstream_empty")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def r4(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)


def assert_zero_contacts(report: dict) -> None:
    contacts = report.get("contacts")
    if contacts != CONTACTS or any(contacts.values()):
        raise ScrError("a contact counter is non-zero: this read is model-free")


# ---------------------------------------------------------------------------
# catalogue: pools, actions, subsets

POOLS = {
    "i1": {"run_id": "SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1",
           "attempt": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-generation-v1",
           "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080,
           "arms": ("lock", "aa", "r1-c1", "r1-c2", "r1-c3", "r1-c4", "r1-c5")},
    "i2": {"run_id": "SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1",
           "attempt": "attempt-slurp-native-stage3-nx-r1-i2-solver-fold-b-generation-v1",
           "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080,
           "arms": ("lock", "aa", "r1-i2-c1", "r1-i2-c2", "r1-i2-c3", "r1-i2-c4", "r1-i2-c5")},
    "r6": {"run_id": R6.R6_RUN_ID, "attempt": R6.R6_ATTEMPT_ID,
           "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080,
           "arms": ("lock", "aa", "p1", "p2", "p3")},
}
REFERENCE_POOL = "i1"


def build_catalog() -> dict:
    """action id -> {kind, pool, arm, family}. ``lock`` is the no-op; ``empty`` the post-Solver deterministic action."""
    catalog = {NOOP: {"kind": "noop", "pool": None, "arm": None, "family": NOOP},
               EMPTY: {"kind": "post", "pool": None, "arm": None, "family": EMPTY}}
    for k in range(1, 6):
        catalog[f"r1-c{k}"] = {"kind": "template", "pool": "i1", "arm": f"r1-c{k}", "family": f"c{k}"}
        catalog[f"r1-i2-c{k}"] = {"kind": "template", "pool": "i2", "arm": f"r1-i2-c{k}", "family": f"c{k}"}
    for p in ("p1", "p2", "p3"):
        catalog[f"r6-{p}"] = {"kind": "perception", "pool": "r6", "arm": p, "family": f"r6-{p}"}
    # post-Solver composite (the R6 'c3verdict' delivery): empty the lock row only where that flight's aggressive arm c3
    # answered empty -- the only learned-by-design lever on record that clears CI-LB > 0 (with the N1 >= 0.2 gate)
    catalog["empty-if-c3-i1"] = {"kind": "post", "pool": "i1", "arm": "r1-c3", "family": "vc3", "verdict": True}
    catalog["empty-if-c3-i2"] = {"kind": "post", "pool": "i2", "arm": "r1-i2-c3", "family": "vc3", "verdict": True}
    return catalog


CATALOG = build_catalog()
DEFAULT_ACTIONS = (NOOP, "r1-c3", "r1-i2-c3", "r1-c5", "r1-i2-c4", EMPTY)


def subsets_of(actions) -> dict:
    """The reported action sets: the chosen set, its Solver-template and post-Solver members, and every loadable action."""
    acts = [a for a in actions if a != NOOP]
    verdict = [a for a in CATALOG if CATALOG[a].get("verdict")]
    post = [a for a in acts if CATALOG[a]["kind"] == "post"]
    out = {"default": [NOOP, *acts],
           "solver_template_only": [NOOP, *[a for a in acts if CATALOG[a]["kind"] == "template"]],
           "post_solver_only": [NOOP, *post],
           "default_plus_verdict": [NOOP, *acts, *[a for a in verdict if a not in acts]],
           "post_solver_plus_verdict": [NOOP, *post, *[a for a in verdict if a not in post]],
           "extended_all_loadable": [a for a in CATALOG]}
    return {k: v for k, v in out.items() if len(v) > 1}


# ---------------------------------------------------------------------------
# row reward arithmetic (count vectors: 9 count fields + intent indicator, as DRV.score_vector)


def pred_items(m):
    return m[:, 6] + m[:, 7]


def is_exact(m):
    return (m[:, 7] == 0) & (m[:, 8] == 0)


def linear_gain(base, delta):
    """Per-row first-order change of the pooled official SLU-F1 (pp) from adding ``delta`` to ``base`` row counts.
    F = 2TP / (2TP + FP + FN); dF = (dN - F dD) / D with N = 2TP, D = 2TP + FP + FN. Linear in the row's count deltas."""
    import numpy as np
    s = base.sum(axis=0)
    tp, fp, fn = s[0] + s[3], s[1] + s[4], s[2] + s[5]
    den = 2 * tp + fp + fn
    if den <= 0:
        return np.zeros(len(delta))
    f = 2 * tp / den
    dtp, dfp, dfn = delta[:, 0] + delta[:, 3], delta[:, 1] + delta[:, 4], delta[:, 2] + delta[:, 5]
    return 100.0 * (2 * dtp - f * (2 * dtp + dfp + dfn)) / den


def indicators(lock4, alt4, lock3, alt3, gold_empty):
    """Per-row integer credit indicators of an action against the same-flight lock row:
    ``ff`` +1 when a false fill (empty-gold row with a predicted entity) is removed, -1 when one is created;
    ``ne`` +1/-1 when a non-empty-gold row gains/loses its exact entity set (delivered, v4g);
    ``raw`` +1/-1 the same on any row for the raw sealed (v3) Solver answers."""
    import numpy as np
    ge = np.asarray(gold_empty, dtype=bool)
    ff = np.where(ge, (pred_items(lock4) > 0).astype(int) - (pred_items(alt4) > 0).astype(int), 0)
    ne = np.where(~ge, is_exact(alt4).astype(int) - is_exact(lock4).astype(int), 0)
    raw = is_exact(alt3).astype(int) - is_exact(lock3).astype(int)
    return {"ff": ff, "ne": ne, "raw": raw}


def routed_matrix(view, choice):
    """The reference lock column plus the chosen actions' same-flight count deltas."""
    import numpy as np
    out = view["base"].copy()
    choice = np.asarray(choice, dtype=object)
    for action, delta in view["deltas"].items():
        mask = choice == action
        if mask.any():
            out[mask] += delta[mask]
    return out


# ---------------------------------------------------------------------------
# learners: shallow regression trees (exportable), L2 logistic decomposition


def _best_split(X, y, min_leaf):
    import numpy as np
    n = len(y)
    total = float(y.sum())
    best = None
    sizes = np.arange(1, n)
    for j in range(X.shape[1]):
        order = np.argsort(X[:, j], kind="mergesort")
        xs, ys = X[order, j], y[order]
        left = np.cumsum(ys)[:-1]
        valid = (sizes >= min_leaf) & (n - sizes >= min_leaf) & (xs[:-1] < xs[1:])
        if not valid.any():
            continue
        score = np.where(valid, left ** 2 / sizes + (total - left) ** 2 / (n - sizes), -np.inf)
        k = int(np.argmax(score))
        gain = float(score[k] - total ** 2 / n)
        if best is None or gain > best[0] + 1e-12:
            threshold = float((xs[k] + xs[k + 1]) / 2.0)
            if threshold >= xs[k + 1]:
                threshold = float(xs[k])
            best = (gain, j, threshold)
    return best


def fit_tree(X, y, names, *, max_depth: int = MAX_DEPTH, min_leaf: int = MIN_LEAF, shrink: float = 0.0,
             _path: str = "") -> dict:
    """CART regression tree (variance reduction), depth <= ``max_depth``, every leaf >= ``min_leaf`` rows. A node is a dict
    ``{"leaf": id, "n", "value"}`` or ``{"feature", "threshold", "left" (x <= threshold), "right"}``. ``shrink`` pulls a leaf mean
    toward 0 (value = sum / (n + shrink))."""
    import numpy as np
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n = len(y)
    split = None if max_depth <= 0 or n < 2 * min_leaf else _best_split(X, y, min_leaf)
    if split is None or split[0] <= 1e-12:
        return {"leaf": _path or "root", "n": int(n), "value": float(y.sum() / (n + shrink)) if n else 0.0}
    _gain, j, threshold = split
    mask = X[:, j] <= threshold
    return {"feature": names[j], "threshold": threshold,
            "left": fit_tree(X[mask], y[mask], names, max_depth=max_depth - 1, min_leaf=min_leaf, shrink=shrink,
                             _path=_path + "L"),
            "right": fit_tree(X[~mask], y[~mask], names, max_depth=max_depth - 1, min_leaf=min_leaf, shrink=shrink,
                              _path=_path + "R")}


def tree_leaf(tree: dict, row: dict) -> dict:
    node = tree
    while "leaf" not in node:
        node = node["left"] if row[node["feature"]] <= node["threshold"] else node["right"]
    return node


def tree_predict(tree: dict, X, names) -> "np.ndarray":
    import numpy as np
    index = {nm: k for k, nm in enumerate(names)}
    out = np.zeros(len(X))
    for i in range(len(X)):
        node = tree
        while "leaf" not in node:
            node = node["left"] if X[i][index[node["feature"]]] <= node["threshold"] else node["right"]
        out[i] = node["value"]
    return out


def tree_leaf_ids(tree: dict, X, names) -> list:
    index = {nm: k for k, nm in enumerate(names)}
    out = []
    for i in range(len(X)):
        node = tree
        while "leaf" not in node:
            node = node["left"] if X[i][index[node["feature"]]] <= node["threshold"] else node["right"]
        out.append(node["leaf"])
    return out


def tree_leaves(tree: dict, conditions=()) -> list:
    if "leaf" in tree:
        return [{"leaf": tree["leaf"], "n": tree["n"], "value": tree["value"], "rule": list(conditions)}]
    f, t = tree["feature"], tree["threshold"]
    return (tree_leaves(tree["left"], [*conditions, f"{f} <= {t!r}"])
            + tree_leaves(tree["right"], [*conditions, f"{f} > {t!r}"]))


class Learner:
    """``tree``: shallow regression tree of the per-row gain. ``logistic``: L2 logistic models of P(gain > 0) and P(gain < 0)
    with the training mean magnitudes (the binary-case decomposition): predicted gain = p_up m_up - p_down m_down."""

    def __init__(self, kind: str, names, *, max_depth=MAX_DEPTH, min_leaf=MIN_LEAF, shrink=0.0, l2=1.0):
        if kind not in ("tree", "logistic"):
            raise ScrError(f"learner must be tree or logistic; got {kind!r}")
        self.kind, self.names = kind, list(names)
        self.max_depth, self.min_leaf, self.shrink, self.l2 = max_depth, min_leaf, shrink, l2

    def fit(self, X, y):
        import numpy as np
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if self.kind == "tree":
            return {"kind": "tree", "tree": fit_tree(X, y, self.names, max_depth=self.max_depth,
                                                     min_leaf=self.min_leaf, shrink=self.shrink)}
        up, down = y > 1e-9, y < -1e-9
        model = {"kind": "logistic", "m_up": float(y[up].mean()) if up.any() else 0.0,
                 "m_down": float((-y[down]).mean()) if down.any() else 0.0}
        for key, flag in (("up", up), ("down", down)):
            if flag.sum() < 5 or (~flag).sum() < 5:
                model[key] = {"const": float(flag.mean())}
            else:
                model[key] = R6.fit_logistic(X, flag.astype(np.float64), l2=self.l2)
        return model

    def predict(self, model, X):
        import numpy as np
        X = np.asarray(X, dtype=np.float64)
        if model["kind"] == "tree":
            return tree_predict(model["tree"], X, self.names)
        p = {}
        for key in ("up", "down"):
            m = model[key]
            p[key] = np.full(len(X), m["const"]) if "const" in m else R6.predict_logistic(m, X)
        return p["up"] * model["m_up"] - p["down"] * model["m_down"]


def crossfit(X, targets: dict, halves, learner: Learner) -> dict:
    """Out-of-fold predicted gain per action: each utterance-hash half is scored by a model fitted on the other half."""
    import numpy as np
    h = np.asarray(halves)
    out = {a: np.zeros(len(h)) for a in targets}
    for k in (0, 1):
        train, test = h != k, h == k
        for action, y in targets.items():
            model = learner.fit(X[train], np.asarray(y)[train])
            out[action][test] = learner.predict(model, X[test])
    return out


def choose(pred: dict, actions, margin: float):
    """Route a row to the action with the highest predicted gain when it exceeds ``margin``; otherwise the lock."""
    import numpy as np
    names = [a for a in actions if a != NOOP]
    n = len(next(iter(pred.values()))) if pred else 0
    if not names:
        return np.array([NOOP] * n, dtype=object)
    P = np.stack([np.asarray(pred[a], dtype=np.float64) for a in names], axis=1)
    best = np.argmax(P, axis=1)
    top = P[np.arange(len(P)), best]
    return np.where(top > margin, np.array(names, dtype=object)[best], NOOP).astype(object)


# ---------------------------------------------------------------------------
# the context signature (model-free, pre-Solver, gold-free)

FEATURE_GROUPS = {
    "pre": ("n1_share", "n1_same_intent", "rate_rank1", "rate_vote", "rate_shortlist_max", "candidates",
            "distinction_tokens_rank1", "unresolved_rank1", "evidence_refs_rank1", "audio_seconds", "headset",
            "top1_cosine"),
    "tag": ("p1_none_score", "p1_tag_ok"),
    "post": ("lock_items", "lock_intent_rate"),
}
FEATURE_DOC = {
    "n1_share": "N1: entity-free share of the row's 20 supplied exemplars (exemplar pool snapshot annotations)",
    "n1_same_intent": "entity-free share among supplied exemplars of Perception's rank-1 intent (N1 when none supplied)",
    "rate_rank1": "TRAIN entity-carrying rate of Perception's rank-1 intent (intent-entity-rate-v1.json); missing -> median",
    "rate_vote": "TRAIN entity rate of the majority intent of the 20 supplied exemplars",
    "rate_shortlist_max": "max TRAIN entity rate over Perception's shortlist",
    "candidates": "Perception shortlist size (candidate count of the registered note)",
    "distinction_tokens_rank1": "whitespace-token length of the rank-1 candidate's distinction (count only)",
    "unresolved_rank1": "count of the rank-1 candidate's unresolved fields",
    "evidence_refs_rank1": "count of the rank-1 candidate's evidence references",
    "audio_seconds": "audio duration in seconds (roster receipt; trace value when present)",
    "headset": "1 for a headset recording, 0 for far-field (roster receipt item flag)",
    "top1_cosine": "top-1 cosine score among the supplied exemplars",
    "p1_none_score": "OPTIONAL: R6-P1 p1 presence tag on the rank-1 candidate: E=none 1.0, unsure 0.5, some 0.0, not-ok 0.5",
    "p1_tag_ok": "OPTIONAL: 1 when the p1 rank-1 tag parses under TAG-GRAMMAR-v1, else 0",
    "lock_items": "OPTIONAL (post-Solver): predicted entity count of the lock answer after v4g",
    "lock_intent_rate": "OPTIONAL (post-Solver): TRAIN entity rate of the lock answer's delivered intent",
}


def row_signature(phase: dict, trace: dict, pool: dict, table: dict, roster_item: dict | None) -> dict:
    """The pre-Solver features of one row from the sealed receipts (phase signals, trace audio) and the pinned TRAIN
    tables. No gold argument exists by construction. ``None`` marks a feature that is not computable for the row."""
    note = phase["note"]
    ids = note["ids"] if note else []
    rates = [R6.rate_of(table, i) for i in ids]
    known = [r for r in rates if r is not None]
    ex = [pool["values"].get(k) for k in phase["ex_ids"]]
    ex = [e for e in ex if e is not None]
    free = [e["n_entities"] == 0 for e in ex]
    same = [e["n_entities"] == 0 for e in ex if ids and e["intent"] == ids[0]]
    votes = Counter(e["intent"] for e in ex)
    vote_intent = votes.most_common(1)[0][0] if votes else None
    audio = trace.get("audio_seconds") or (roster_item or {}).get("audio_seconds")
    return {
        "n1_share": (sum(free) / len(free)) if free else None,
        "n1_same_intent": (sum(same) / len(same)) if same else ((sum(free) / len(free)) if free else None),
        "rate_rank1": rates[0] if rates else None,
        "rate_vote": R6.rate_of(table, vote_intent),
        "rate_shortlist_max": max(known) if known else None,
        "candidates": float(len(ids)) if note else None,
        "distinction_tokens_rank1": float(note["distinction_tokens"][0]) if note and note["distinction_tokens"] else None,
        "unresolved_rank1": float(note["unresolved"][0]) if note and note["unresolved"] else None,
        "evidence_refs_rank1": float(note["evidence_refs"][0]) if note and note["evidence_refs"] else None,
        "audio_seconds": float(audio) if audio else None,
        "headset": None if roster_item is None or "headset" not in roster_item else float(bool(roster_item["headset"])),
        "top1_cosine": float(phase["ex_scores"][0]) if phase["ex_scores"] else None,
    }


def fill_values(sigs: dict, ids, features) -> dict:
    """Median of the known values per feature over the reference rows (pinned in the routing table)."""
    out = {}
    for f in features:
        known = sorted(sigs[s][f] for s in ids if sigs[s].get(f) is not None)
        out[f] = float(known[len(known) // 2]) if known else 0.0
    return out


def design_matrix(sigs: dict, ids, features, fill: dict):
    import numpy as np
    X = np.array([[fill[f] if sigs[s].get(f) is None else sigs[s][f] for f in features] for s in ids], dtype=np.float64)
    filled = {f: int(sum(sigs[s].get(f) is None for s in ids)) for f in features}
    return X, filled


# ---------------------------------------------------------------------------
# views: a reference column, its same-flight deltas, and the row metadata


def make_view(*, ids, utt, scenario, gold_empty, base, twin, deltas, ind, kinds=None) -> dict:
    import numpy as np
    return {"ids": list(ids), "utt": list(utt), "scenario": list(scenario),
            "gold_empty": np.asarray(gold_empty, dtype=bool), "base": np.asarray(base, dtype=np.float64),
            "twin": None if twin is None else np.asarray(twin, dtype=np.float64),
            "deltas": {a: np.asarray(d, dtype=np.float64) for a, d in deltas.items()}, "ind": ind,
            "halves": np.array([R6.half_of(u) for u in utt])}


def gains_of(view, intent_weight: float = 0.0) -> dict:
    """Per-action per-row reward difference against the lock: the linearised pooled SLU-F1 pp (plus, with
    ``intent_weight``, that many pp of intent per intent-correct row: 100 / n)."""
    out = {}
    n = len(view["ids"])
    for action, delta in view["deltas"].items():
        g = linear_gain(view["base"], delta)
        if intent_weight:
            g = g + intent_weight * 100.0 * delta[:, 9] / n
        out[action] = g
    return out


def stratum_weights(scenarios):
    import numpy as np
    counts = Counter(scenarios)
    n, s = len(scenarios), len(counts)
    return np.array([n / (s * counts[x]) for x in scenarios], dtype=np.float64)


def evaluate_choice(view, choice, boot, *, detail: bool = False, aa=None) -> dict:
    """Pooled official SLU-F1 of the routed column against the lock (and the twin), intent guard, routed shares, exchange
    arithmetic and, with ``detail``, the per-stratum and empty/non-empty tables."""
    import numpy as np
    base = view["base"]
    choice = np.asarray(choice, dtype=object)
    routed = routed_matrix(view, choice)
    c = boot.contrast(base, routed)
    n = len(choice)
    moved = choice != NOOP
    shares = {a: int((choice == a).sum()) for a in sorted({str(x) for x in choice}) if a != NOOP}
    ff = ne_lost = ne_gain = raw_net = 0
    for a in shares:
        mask = choice == a
        ind = view["ind"][a]
        ff += int(ind["ff"][mask].sum())
        ne_lost += int((ind["ne"][mask] < 0).sum())
        ne_gain += int((ind["ne"][mask] > 0).sum())
        raw_net += int(ind["raw"][mask].sum())
    predicted = RATE_FALSE_FILL_REMOVED * ff + RATE_NONEMPTY_EXACT * (ne_gain - ne_lost)
    out = {
        "rows": n, "rows_routed": int(moved.sum()), "routed_share": r4(moved.mean()),
        "routed_rows_by_action": shares,
        "slu_f1_lock_pp": c["left_slu_f1_pp"], "slu_f1_routed_pp": c["right_slu_f1_pp"],
        "delta_vs_lock_slu_pp": c["delta_slu_pp"], "ci95_vs_lock_slu_pp": c["ci95_slu_pp"],
        "delta_span_pp": c["delta_span_pp"],
        "delta_intent_pp": c["delta_intent_pp"], "ci95_intent_pp": c["ci95_intent_pp"],
        "intent_rows_moved": int(np.sum(np.abs(routed[:, 9] - base[:, 9]) > 1e-9)),
        "exchange": {"false_fills_removed_net": ff, "nonempty_exact_lost": ne_lost, "nonempty_exact_gained": ne_gain,
                     "raw_exact_rows_net": raw_net,
                     "predicted_pp_false_fill_x0.033_plus_nonempty_exact_x0.070": round(predicted, 4),
                     "predicted_pp_raw_exact_x0.056": round(RATE_RAW_EXACT * raw_net, 4),
                     "realised_pp": c["delta_slu_pp"]},
    }
    twin = aa if aa is not None else view.get("twin")
    if twin is not None:
        t = boot.contrast(twin, routed)
        out["delta_vs_twin_slu_pp"] = t["delta_slu_pp"]
        out["ci95_vs_twin_slu_pp"] = t["ci95_slu_pp"]
    if detail:
        scen = np.array(view["scenario"], dtype=object)
        ge = view["gold_empty"]
        strata = {}
        for s in sorted(set(view["scenario"])):
            mask = scen == s
            p = DRV.pooled(routed[mask])["slu_f1_pp"] - DRV.pooled(base[mask])["slu_f1_pp"]
            ci = boot.contrast(base * mask[:, None], routed * mask[:, None])["ci95_slu_pp"]
            strata[s] = {"rows": int(mask.sum()), "routed": int((mask & moved).sum()), "delta_slu_pp": r4(p), "ci95": ci}
        w = stratum_weights(view["scenario"])[:, None]
        eq = boot.contrast(base * w, routed * w)
        out["per_scenario"] = strata
        out["equal_stratum"] = {"delta_slu_pp": eq["delta_slu_pp"], "ci95": eq["ci95_slu_pp"],
                                "natural_mixture_delta_slu_pp": c["delta_slu_pp"]}
        halves = {}
        for name, mask in (("empty_gold", ge), ("non_empty_gold", ~ge)):
            cc = boot.contrast(base * mask[:, None], routed * mask[:, None])
            halves[name] = {"rows": int(mask.sum()), "routed": int((mask & moved).sum()),
                            "delta_slu_pp_of_all_rows_pooled": cc["delta_slu_pp"], "ci95": cc["ci95_slu_pp"]}
        halves["empty_gold"]["false_fills_removed_net"] = int(sum(
            int(view["ind"][a]["ff"][(choice == a) & ge].sum()) for a in shares))
        halves["non_empty_gold"]["exact_lost"] = int(sum(
            int((view["ind"][a]["ne"][(choice == a) & ~ge] < 0).sum()) for a in shares))
        halves["non_empty_gold"]["exact_gained"] = int(sum(
            int((view["ind"][a]["ne"][(choice == a) & ~ge] > 0).sum()) for a in shares))
        out["empty_vs_non_empty"] = halves
    return out


def oracle_choice(view, actions, extra=None):
    """Per-row best action by realised linear gain (lock when no action gains): the ceiling, inflated by decoding noise."""
    import numpy as np
    g = gains_of(view)
    names = [a for a in actions if a != NOOP and a in g]
    if not names:
        return np.array([NOOP] * len(view["ids"]), dtype=object)
    P = np.stack([g[a] for a in names], axis=1)
    best = np.argmax(P, axis=1)
    return np.where(P[np.arange(len(P)), best] > 1e-12, np.array(names, dtype=object)[best], NOOP).astype(object)


# ---------------------------------------------------------------------------
# the analysis of one view (pure given view / signature / parameters)


def analyse(view, sigs: dict, params: dict, boot, *, fill: dict, groups_available: dict, actions, headline: tuple) -> dict:
    """Cross-fitted routing for every learner x feature-group variant and every reported action subset."""
    import numpy as np
    ids = view["ids"]
    subsets = subsets_of(actions)
    avail = [a for a in view["deltas"]]
    subsets = {k: [a for a in v if a == NOOP or a in avail] for k, v in subsets.items()}
    subsets = {k: v for k, v in subsets.items() if len(v) > 1}
    g = gains_of(view, params.get("intent_weight", 0.0))
    margin = params["margin_pp_per_row"]
    report = {"actions_loaded": avail, "subsets": subsets, "variants": {}}
    out_choice = {}
    for learner_kind in params["learners"]:
        for gname, features in params["feature_variants"].items():
            if not groups_available.get(gname, True):
                report["variants"][f"{learner_kind}|{gname}"] = {"unavailable": True}
                continue
            X, filled = design_matrix(sigs, ids, features, fill)
            learner = Learner(learner_kind, features, max_depth=params["max_depth"], min_leaf=params["min_leaf"],
                              shrink=params["shrink"])
            oof = crossfit(X, {a: g[a] for a in avail}, view["halves"], learner)
            key = f"{learner_kind}|{gname}"
            rec = {"features": list(features), "filled_rows": filled, "subsets": {}}
            for sname, sub in subsets.items():
                choice = choose(oof, sub, margin)
                is_head = (learner_kind, gname) == headline
                rec["subsets"][sname] = evaluate_choice(view, choice, boot, detail=is_head)
                if is_head:
                    out_choice[sname] = choice
            report["variants"][key] = rec
            if (learner_kind, gname) == headline:
                report["headline_oof"] = {a: r4(float(np.mean(oof[a]))) for a in avail}
                report["_oof"] = oof
    report["_choice"] = out_choice
    return report


def margin_sensitivity(view, sigs, params, boot, *, fill, actions, headline) -> dict:
    learner_kind, gname = headline
    features = params["feature_variants"][gname]
    X, _ = design_matrix(sigs, view["ids"], features, fill)
    g = gains_of(view, params.get("intent_weight", 0.0))
    avail = list(view["deltas"])
    learner = Learner(learner_kind, features, max_depth=params["max_depth"], min_leaf=params["min_leaf"],
                      shrink=params["shrink"])
    oof = crossfit(X, {a: g[a] for a in avail}, view["halves"], learner)
    sub = subsets_of(actions)["default"]
    sub = [a for a in sub if a == NOOP or a in avail]
    out = {}
    d = params["margin_pp_per_row"]
    for label, m in (("zero", 0.0), ("0.5x default", 0.5 * d), ("default", d), ("2x default", 2 * d), ("4x default", 4 * d),
                     ("floor/min_leaf (0.67/60)", FLOOR_PP / params["min_leaf"])):
        r = evaluate_choice(view, choose(oof, sub, m), boot)
        out[f"{label} ({m:.5f} pp/row)"] = {k: r[k] for k in (
            "rows_routed", "routed_rows_by_action", "delta_vs_lock_slu_pp", "ci95_vs_lock_slu_pp", "delta_intent_pp",
            "intent_rows_moved")}
    return out


#: the R6 offline note's fixed gate, the machinery control: empty the lock row where the aggressive arm c3 emptied it AND
#: N1 >= 0.2, v4g base (docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md): delta pp, false fills base -> new
R6_GATE_REFERENCE = {"i1": {"delta_slu_pp": 0.75, "false_fills": (91, 64), "nonempty_exact_lost": 3},
                     "i2": {"delta_slu_pp": 0.98, "false_fills": (93, 60), "nonempty_exact_lost": 3}}


def fixed_rule_checks(local: dict, local_sigs: dict, boot) -> dict:
    """Reproduce the R6 gate through this driver's delta machinery; a mismatch stops the run."""
    import numpy as np
    out = {}
    for key, ref in R6_GATE_REFERENCE.items():
        if key not in local:
            continue
        view = local[key]["view"]
        n1 = np.array([local_sigs[key][s]["n1_share"] for s in view["ids"]])
        action = f"empty-if-c3-{key}"
        choice = np.where(n1 >= 0.2, action, NOOP).astype(object)
        r = evaluate_choice(view, choice, boot)
        routed = routed_matrix(view, choice)
        ge = view["gold_empty"]
        ff = (int((ge & (pred_items(view["base"]) > 0)).sum()), int((ge & (pred_items(routed) > 0)).sum()))
        rec = {"fired": r["rows_routed"], "delta_slu_pp": r["delta_vs_lock_slu_pp"], "ci95": r["ci95_vs_lock_slu_pp"],
               "false_fills_base_to_new": list(ff), "nonempty_exact_lost": r["exchange"]["nonempty_exact_lost"],
               "intent_rows_moved": r["intent_rows_moved"], "r6_note": ref}
        if (abs(rec["delta_slu_pp"] - ref["delta_slu_pp"]) > 0.0051 or ff != ref["false_fills"]
                or rec["nonempty_exact_lost"] != ref["nonempty_exact_lost"] or rec["intent_rows_moved"] != 0):
            raise ScrError(f"{key}: the R6 gate is not reproduced by the delta machinery: {rec}")
        rec["reproduced"] = True
        out[key] = rec
    return out


def single_actions(view, boot) -> dict:
    """Context: each action applied to every row (same-flight delta on the reference column)."""
    import numpy as np
    out = {}
    for a in view["deltas"]:
        r = evaluate_choice(view, np.array([a] * len(view["ids"]), dtype=object), boot)
        out[a] = {k: r[k] for k in ("delta_vs_lock_slu_pp", "ci95_vs_lock_slu_pp", "delta_intent_pp", "intent_rows_moved",
                                    "exchange")}
    return out


def oracle_block(view, actions, boot) -> dict:
    import numpy as np
    subsets = subsets_of(actions)
    out = {}
    for sname, sub in subsets.items():
        sub = [a for a in sub if a == NOOP or a in view["deltas"]]
        if len(sub) < 2:
            continue
        r = evaluate_choice(view, oracle_choice(view, sub), boot)
        out[sname] = {k: r[k] for k in ("rows_routed", "routed_rows_by_action", "delta_vs_lock_slu_pp",
                                        "ci95_vs_lock_slu_pp", "delta_intent_pp", "intent_rows_moved")}
    # the noise-only ceiling: the in-chain twin has no real effect, so best-of-{lock, twin} per row is pure selection on noise
    if view.get("twin") is not None:
        twin_delta = view["twin"] - view["base"]
        g = linear_gain(view["base"], twin_delta)
        probe = dict(view)
        probe["deltas"] = {"aa": twin_delta}
        probe["ind"] = {"aa": {"ff": np.zeros(len(g), dtype=int), "ne": np.zeros(len(g), dtype=int),
                               "raw": np.zeros(len(g), dtype=int)}}
        choice = np.where(g > 1e-12, "aa", NOOP).astype(object)
        r = evaluate_choice(probe, choice, boot)
        out["noise_only_twin_best_of_lock_and_aa"] = {k: r[k] for k in (
            "rows_routed", "delta_vs_lock_slu_pp", "ci95_vs_lock_slu_pp", "delta_intent_pp")}
    return out


# ---------------------------------------------------------------------------
# leave-one-pool-out: fit on pool P (one utterance half), score pool Q (the other half): row- AND flight-disjoint


def lopo(view_p, X_p, view_q, X_q, fam_p: dict, fam_q: dict, params, boot_q, features) -> dict:
    """``fam_p`` / ``fam_q`` map a family label to that pool's action id (``lock`` excluded). Rows are the same utterances in
    both pools; a row of Q's half h is routed by a model fitted on P's rows of the other half, and P's gains use P's own lock."""
    import numpy as np
    if view_p["ids"] != view_q["ids"]:
        raise ScrError("the pools do not cover the same rows")
    fams = [f for f in fam_p if f in fam_q]
    gp = gains_of(view_p, params.get("intent_weight", 0.0))
    learner = Learner(params["learners"][0], features, max_depth=params["max_depth"], min_leaf=params["min_leaf"],
                      shrink=params["shrink"])
    h = view_p["halves"]
    pred = {f: np.zeros(len(h)) for f in fams}
    for k in (0, 1):
        train, test = h != k, h == k
        for f in fams:
            model = learner.fit(X_p[train], gp[fam_p[f]][train])
            pred[f][test] = learner.predict(model, X_q[test])
    choice_f = choose(pred, [NOOP, *fams], params["margin_pp_per_row"])
    choice_q = np.array([NOOP if c == NOOP else fam_q[c] for c in choice_f], dtype=object)
    r = evaluate_choice(view_q, choice_q, boot_q)
    keep = ("rows_routed", "routed_rows_by_action", "slu_f1_lock_pp", "slu_f1_routed_pp", "delta_vs_lock_slu_pp",
            "ci95_vs_lock_slu_pp", "delta_intent_pp", "intent_rows_moved", "exchange")
    return {"families": fams, **{k: r[k] for k in keep}}


# ---------------------------------------------------------------------------
# routing table: the fitted policy, human-readable and executable from the signature alone


def build_routing_table(view, sigs, params, *, fill, features, actions, oof, groups) -> dict:
    """Fit one tree per action on ALL rows (the pinned policy). Cells = realised combinations of the per-action leaves; each
    cell carries the chosen action, n, the in-sample mean gain of the chosen action, the per-half means, and the cross-fitted
    mean gain (the out-of-fold policy's realised gain on the cell's rows) with the share of rows that policy agreed on."""
    import numpy as np
    ids = view["ids"]
    X, _ = design_matrix(sigs, ids, features, fill)
    g = gains_of(view, params.get("intent_weight", 0.0))
    names = [a for a in actions if a != NOOP and a in g]
    learner = Learner("tree", features, max_depth=params["max_depth"], min_leaf=params["min_leaf"], shrink=params["shrink"])
    trees, pred, leaf_ids = {}, {}, {}
    for a in names:
        trees[a] = learner.fit(X, g[a])["tree"]
        pred[a] = tree_predict(trees[a], X, features)
        leaf_ids[a] = tree_leaf_ids(trees[a], X, features)
    choice = choose(pred, [NOOP, *names], params["margin_pp_per_row"])
    oof_choice = choose(oof, [NOOP, *names], params["margin_pp_per_row"]) if oof else choice
    zero = np.zeros(len(ids))

    def realised(c):
        return np.array([0.0 if x == NOOP else g[x][i] for i, x in enumerate(c)])

    own, xf = realised(choice), realised(oof_choice)
    cells = {}
    for i in range(len(ids)):
        key = tuple(leaf_ids[a][i] for a in names)
        cells.setdefault(key, []).append(i)
    cell_rows = []
    for key, rows in cells.items():
        rows = np.array(rows)
        act = str(choice[rows[0]])
        h = view["halves"][rows]
        gain_a = zero[rows] if act == NOOP else g[act][rows]
        cell_rows.append({
            "cell": dict(zip(names, key)), "action": act, "n": int(len(rows)),
            "in_sample_mean_gain_pp_per_row": r4(float(own[rows].mean())),
            "chosen_action_mean_gain_by_half_pp_per_row": {
                str(k): r4(float(gain_a[h == k].mean())) if (h == k).any() else None for k in (0, 1)},
            "xfit_mean_gain_pp_per_row": r4(float(xf[rows].mean())),
            "xfit_policy_agrees_share": r4(float((oof_choice[rows] == act).mean())),
            "xfit_total_gain_pp": r4(float(xf[rows].sum()))})
    cell_rows.sort(key=lambda c: (-c["n"], str(c["cell"])))
    return {
        "schema": TABLE_SCHEMA, "table_id": TABLE_ID, "feature_group": groups, "features": list(features),
        "fill_values": fill, "margin_pp_per_row": params["margin_pp_per_row"], "noop_action": NOOP,
        "action_order": names, "trees": trees,
        "leaves": {a: [dict(x, mean_gain_pp_per_row=r4(x["value"])) for x in tree_leaves(trees[a])] for a in names},
        "cells": cell_rows,
        "decision_procedure": (
            "for each action, descend its tree on the row's signature (a missing feature takes its fill value; go left when "
            "feature <= threshold); the leaf value is that action's predicted gain in pp of pooled SLU-F1 per row; route to the "
            "action with the highest predicted gain when it exceeds margin_pp_per_row, otherwise stay on 'lock'; ties go to the "
            "earlier action in action_order"),
        "in_sample_routed_rows": int((choice != NOOP).sum()),
        "_choice": choice,
    }


def route_row(table: dict, signature: dict) -> str:
    """Execute the pinned table on one row's signature alone (the runtime rule)."""
    row = {f: (table["fill_values"][f] if signature.get(f) is None else signature[f]) for f in table["features"]}
    best, best_gain = NOOP, table["margin_pp_per_row"]
    for action in table["action_order"]:
        value = tree_leaf(table["trees"][action], row)["value"]
        if value > best_gain:
            best, best_gain = action, value
    return best


def render_table_md(table: dict, receipt: dict) -> str:
    out = [f"# {table['table_id']}", "",
           f"Fitted on {receipt['rows']} rows ({receipt['pool_roster']}); features {table['feature_group']}; margin "
           f"{table['margin_pp_per_row']:.5f} pp/row; in-sample rows routed {table['in_sample_routed_rows']}. "
           "No utterance text, transcript, gold value or model output appears here.", "", "## Decision procedure", "",
           table["decision_procedure"], "", "## Feature definitions (exact; computed before the Solver, gold-free)", ""]
    out += ["| feature | definition | fill value |", "| --- | --- | ---: |"]
    for f in table["features"]:
        out.append(f"| `{f}` | {FEATURE_DOC[f]} | {table['fill_values'][f]:.6g} |")
    out += ["", "## Per-action leaves (bins of the predicted gain)", ""]
    for a in table["action_order"]:
        out += [f"### `{a}`", "", "| leaf | n | predicted gain pp/row | rule |", "| --- | ---: | ---: | --- |"]
        for leaf in table["leaves"][a]:
            out.append(f"| {leaf['leaf']} | {leaf['n']} | {leaf['value']:+.5f} | "
                       f"{' AND '.join(leaf['rule']) if leaf['rule'] else 'always'} |")
        out.append("")
    out += ["## Routing cells (realised leaf combinations -> action)", "",
            "| action | n | in-sample gain pp/row | cross-fitted gain pp/row | xfit agrees | cross-fitted total pp | "
            "chosen-action gain by half |", "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for c in table["cells"]:
        out.append(f"| {c['action']} | {c['n']} | {c['in_sample_mean_gain_pp_per_row']} | {c['xfit_mean_gain_pp_per_row']} | "
                   f"{c['xfit_policy_agrees_share']} | {c['xfit_total_gain_pp']} | "
                   f"{c['chosen_action_mean_gain_by_half_pp_per_row']} |")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# sealed loaders


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def pool_files(data_root: Path, spec: dict) -> dict:
    sv = data_root / "runs" / spec["run_id"] / spec["attempt"] / "supply-variants"
    return {arm: (sv / f"arm-{arm}-first-visit-outputs.jsonl", sv / f"arm-{arm}-{spec['scorer']}-scores.json")
            for arm in spec["arms"]}


def load_pool(key: str, spec: dict, data_root: Path, gold_all: dict, arms) -> dict:
    """Every requested arm of a sealed column: v3 columns verified against the sealed official fields, then v4g columns."""
    import numpy as np
    files, texts, sealed, meta = pool_files(data_root, spec), {}, {}, {}
    for arm in arms:
        fpath, spath = files[arm]
        texts[arm] = {str(r["sample_id"]): r.get("text") or "" for r in iter_jsonl(fpath)}
        block = json.loads(spath.read_text(encoding="utf-8"))[spec["scorer"]]
        sealed[arm] = {str(r["sample_id"]): r for r in block["per_sample"]}
        meta[arm] = {"first_visit": [str(fpath.relative_to(data_root)), digest(fpath)],
                     "scores": [str(spath.relative_to(data_root)), digest(spath)],
                     "official_slu_f1_pp": round(100.0 * float(block["aggregate"]["official"]["slu_f1"]), 4)}
    ids = sorted(texts[arms[0]])
    if len(ids) != spec["rows"] or any(sorted(texts[a]) != ids or sorted(sealed[a]) != ids for a in arms):
        raise ScrError(f"{key}: arm columns do not cover the same {spec['rows']} rows")
    if any(s not in gold_all for s in ids):
        raise ScrError(f"{key}: roster ids absent from the TRAIN gold")
    gold = {s: gold_all[s] for s in ids}
    out = {"ids": ids, "v3": {}, "v3_empty": {}, "v4g": {}, "v4g_empty": {}, "meta": {}, "gold": gold}
    for arm in arms:
        m, m_e = R6.score_texts(ids, texts[arm], gold)
        sv = np.array([DRV.sealed_vector(sealed[arm][s]) for s in ids])
        bad = int(np.sum(np.any(np.abs(m - sv) > 1e-9, axis=1)))
        if bad:
            raise ScrError(f"{key}/{arm}: in-process scoring differs from the sealed per-sample fields on {bad} rows")
        pooled_v3 = DRV.pooled(m)["slu_f1_pp"]
        if abs(pooled_v3 - meta[arm]["official_slu_f1_pp"]) > 1e-3:
            raise ScrError(f"{key}/{arm}: pooled in-process SLU-F1 {pooled_v3:.4f} does not reproduce the official aggregate "
                           f"{meta[arm]['official_slu_f1_pp']}")
        t4, changed, version = R6.apply_v4g(ids, texts[arm])
        m4, m4_e = R6.score_texts(ids, t4, gold)
        out["v3"][arm], out["v3_empty"][arm], out["v4g"][arm], out["v4g_empty"][arm] = m, m_e, m4, m4_e
        if arm == "lock":
            out["lock_intent"] = R6.delivered_intent(t4, ids)
        meta[arm].update({"v3_in_process_slu_f1_pp": r4(pooled_v3), "v3_sealed_per_sample_rows_reproduced": len(ids),
                          "v4g_slu_f1_pp": r4(DRV.pooled(m4)["slu_f1_pp"]), "v4g_rows_changed": changed,
                          "v4g_normaliser_version": version})
    out["meta"] = meta
    del texts
    return out


def pool_action(action: str, info: dict, p: dict, gold_empty):
    """(count delta, credit indicators) of an action against the SAME pool's lock column (same-flight credit)."""
    import numpy as np
    lock4, lock3 = p["v4g"]["lock"], p["v3"]["lock"]
    if action == EMPTY:
        alt4, alt3 = p["v4g_empty"]["lock"], p["v3_empty"]["lock"]
    elif info.get("verdict"):
        fired = (pred_items(p["v4g"][info["arm"]]) == 0)[:, None]
        alt4 = np.where(fired, p["v4g_empty"]["lock"], lock4)
        alt3 = np.where(fired, p["v3_empty"]["lock"], lock3)
    else:
        alt4, alt3 = p["v4g"][info["arm"]], p["v3"][info["arm"]]
    return alt4 - lock4, indicators(lock4, alt4, lock3, alt3, gold_empty)


def load_p1_tag(data_root: Path) -> dict:
    """The OPTIONAL feature group: R6-P1 p1 rank-1 presence tag per row (notes parsed in memory by the E2b reader)."""
    import slurp_nx_perception_column_read as PCR
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    spec = POOLS["r6"]
    directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
    bundle = verify_bundle(directory / f"{spec['run_id']}.run-manifest.json")
    sealed = PCR.load_sealed_columns(bundle.outputs_rows, bundle.trace_records,
                                     tag_sets=PCR.parse_tag_set_args(["p3=none,some,unsure"]))
    if "p1" not in sealed["arm_ids"]:
        raise ScrError("the R6 run has no p1 arm")
    out = {}
    for sid, note in sealed["notes"]["p1"].items():
        v, _word = R6.verdict_row(note["tag"])
        out[sid] = {"p1_none_score": v["p_none_score"], "p1_tag_ok": v["p_tag_ok"]}
    return out


def build_inputs(args) -> dict:
    """Load every sealed pool and assemble the composite view, the pool-local views and the signatures."""
    import numpy as np
    from speech_aware_evidence_acquisition.data.lock import load_lock
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    gold_all = DRV.load_gold(lock, data_root, "train")
    slot_types = {str(e.type).lower() for row in gold_all.values() for e in row["entities"]}
    table_path = data_root / R6.RATE_TABLE
    rate_table = json.loads(table_path.read_text(encoding="utf-8"))
    ex_pool = R6.load_exemplar_annotations(data_root)
    roster_path = REPO_ROOT / ROSTER
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    roster_items = {it["sample_id"]: it for it in roster["items"]}

    wanted = {CATALOG[a]["pool"] for a in args.actions if CATALOG[a]["pool"]} | {REFERENCE_POOL}
    if args.extended:
        wanted |= {"i1", "i2", "r6"}
    pools, sigs_by_pool = {}, {}
    notes = {}
    for key in ("i1", "i2", "r6"):
        if key not in wanted:
            continue
        spec = POOLS[key]
        arms = tuple(spec["arms"])
        pools[key] = load_pool(key, spec, data_root, gold_all, arms)
        directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
        ids = pools[key]["ids"]
        phases = R6.load_phase_signals(directory / f"{spec['run_id']}.phases.json", slot_types)
        trace = R6.load_perception_trace(directory / f"{spec['run_id']}.trace.jsonl", set(ids))
        pools[key]["phases_sha256"] = phases["sha256"]
        pools[key]["phase_checks"] = phases["checks"]
        sigs_by_pool[key] = {s: row_signature(phases["rows"][s], trace.get(s, {}), ex_pool, rate_table, roster_items.get(s))
                             for s in ids}
        notes[key] = {s: (phases["rows"][s]["note"] or {}).get("ids", [None])[:1] for s in ids}
    ref = pools[REFERENCE_POOL]
    ids = ref["ids"]
    if any(pools[k]["ids"] != ids for k in pools):
        raise ScrError("the pools do not cover the same rows")
    if set(ids) != set(roster_items):
        raise ScrError("the pool rows are not the Fold B roster")
    gold = ref["gold"]
    gold_empty = [not gold[s]["entities"] for s in ids]
    utt = [gold[s]["utterance_id"] for s in ids]
    scenario = [gold[s]["scenario"] for s in ids]

    base = ref["v4g"]["lock"]
    deltas, ind = {}, {}
    for action, info in CATALOG.items():
        if action == NOOP:
            continue
        home = pools[REFERENCE_POOL] if info["pool"] is None else pools.get(info["pool"])
        if home is None:
            continue
        deltas[action], ind[action] = pool_action(action, info, home, gold_empty)
    if not np.all(deltas[EMPTY][:, 9] == 0):
        raise ScrError("the post-Solver 'empty' action moved an intent indicator")
    view = make_view(ids=ids, utt=utt, scenario=scenario, gold_empty=gold_empty, base=base, twin=ref["v4g"]["aa"],
                     deltas=deltas, ind=ind)

    # pool-local views (own lock, own arms) for the leave-one-pool-out check
    local = {}
    for key in ("i1", "i2"):
        if key not in pools:
            continue
        p = pools[key]
        d_loc, i_loc, fam = {}, {}, {}
        for action, info in CATALOG.items():
            if action == NOOP or (info["pool"] not in (None, key)):
                continue
            d_loc[action], i_loc[action] = pool_action(action, info, p, gold_empty)
            fam[info["family"]] = action
        local[key] = {"view": make_view(ids=ids, utt=utt, scenario=scenario, gold_empty=gold_empty, base=p["v4g"]["lock"],
                                        twin=p["v4g"]["aa"], deltas=d_loc, ind=i_loc), "families": fam}

    # the reference signature; the OPTIONAL tag group from the R6 flight; the optional post-Solver group
    sigs = {s: dict(sigs_by_pool[REFERENCE_POOL][s]) for s in ids}
    groups_available = {"pre": True, "tag": False, "post": True}
    tag_error = None
    if args.tag:
        try:
            tags = load_p1_tag(data_root)
            for s in ids:
                sigs[s].update(tags[s])
            groups_available["tag"] = True
        except Exception as error:  # a loader failure is a reported limitation, never a silent fallback
            tag_error = f"{type(error).__name__}: {error}"[:300]
    lock_items = pred_items(base)
    for k, s in enumerate(ids):
        sigs[s]["lock_items"] = float(lock_items[k])
        sigs[s]["lock_intent_rate"] = R6.rate_of(rate_table, ref["lock_intent"][s])
    local_sigs = {key: {s: dict(sigs_by_pool[key][s]) for s in ids} for key in local}
    for key in local:
        for k, s in enumerate(ids):
            local_sigs[key][s]["lock_items"] = float(pred_items(pools[key]["v4g"]["lock"])[k])
            local_sigs[key][s]["lock_intent_rate"] = R6.rate_of(rate_table, pools[key]["lock_intent"][s])

    agreement = {}
    for key in pools:
        if key == REFERENCE_POOL:
            continue
        same = sum(1 for s in ids if notes[key][s] == notes[REFERENCE_POOL][s])
        diff_n1 = [abs(sigs_by_pool[key][s]["n1_share"] - sigs_by_pool[REFERENCE_POOL][s]["n1_share"]) for s in ids
                   if sigs_by_pool[key][s]["n1_share"] is not None and sigs_by_pool[REFERENCE_POOL][s]["n1_share"] is not None]
        agreement[key] = {"rank1_intent_same_as_reference": same / len(ids),
                          "mean_abs_n1_share_difference": r4(float(np.mean(diff_n1))) if diff_n1 else None}
    return {"view": view, "local": local, "sigs": sigs, "local_sigs": local_sigs, "pools": pools,
            "groups_available": groups_available, "tag_error": tag_error, "signature_agreement": agreement,
            "rate_table": [R6.RATE_TABLE, digest(table_path)], "exemplar_pool": [ex_pool["relpath"], ex_pool["sha256"]],
            "roster": [ROSTER, digest(roster_path)], "roster_split_identity_hash": roster.get("split_identity_hash"),
            "gold_empty_rows": int(sum(gold_empty)), "boot_clusters": len(set(utt))}


# ---------------------------------------------------------------------------
# run


def default_params(args) -> dict:
    min_leaf = args.min_leaf
    margin = args.margin_pp_per_row if args.margin_pp_per_row is not None else MARGIN_FRACTION * RATE_FALSE_FILL_REMOVED
    groups = {"pre": FEATURE_GROUPS["pre"], "pre+p1tag": FEATURE_GROUPS["pre"] + FEATURE_GROUPS["tag"],
              "pre+post": FEATURE_GROUPS["pre"] + FEATURE_GROUPS["post"]}
    return {"max_depth": args.max_depth, "min_leaf": min_leaf, "margin_pp_per_row": margin, "shrink": args.shrink,
            "intent_weight": args.intent_weight, "learners": ["tree", "logistic"], "feature_variants": groups,
            "draws": args.draws, "seed": args.seed}


GROUP_NEEDS = {"pre": "pre", "pre+p1tag": "tag", "pre+post": "post"}


def run(args) -> dict:
    inputs = build_inputs(args)
    view, params = inputs["view"], default_params(args)
    boot = DRV.Bootstrap(view["ids"], dict(zip(view["ids"], view["utt"])), draws=args.draws, seed=args.seed)
    avail = {g: inputs["groups_available"][GROUP_NEEDS[g]] for g in params["feature_variants"]}
    sigs = inputs["sigs"]
    fill = fill_values(sigs, view["ids"], sorted({f for fs in params["feature_variants"].values() for f in fs}))
    actions = tuple(args.actions)
    headline = ("tree", "pre")
    main = analyse(view, sigs, params, boot, fill=fill, groups_available=avail, actions=actions, headline=headline)
    oof = main.pop("_oof")
    choice = main.pop("_choice")
    sensitivity = margin_sensitivity(view, sigs, params, boot, fill=fill, actions=actions, headline=headline)
    singles = single_actions(view, boot)
    oracle = oracle_block(view, actions, boot)
    # reference twin nulls of each pool
    twins = {}
    for key, p in inputs["pools"].items():
        twins[key] = {"aa_minus_lock_slu_pp": r4(DRV.pooled(p["v4g"]["aa"])["slu_f1_pp"] - DRV.pooled(p["v4g"]["lock"])["slu_f1_pp"]),
                      "ci95": boot.contrast(p["v4g"]["lock"], p["v4g"]["aa"])["ci95_slu_pp"],
                      "lock_v4g_slu_f1_pp": r4(DRV.pooled(p["v4g"]["lock"])["slu_f1_pp"]),
                      "lock_v4g_intent_pp": r4(DRV.pooled(p["v4g"]["lock"])["intent_pp"])}
    # leave-one-pool-out (row- and flight-disjoint)
    lopo_out = {}
    if "i1" in inputs["local"] and "i2" in inputs["local"]:
        feats = list(FEATURE_GROUPS["pre"])
        base_fams = {CATALOG[a]["family"] for a in actions if a != NOOP and CATALOG[a]["kind"] in ("template", "post")}
        for set_name, fams in (("default", base_fams), ("default_plus_verdict", base_fams | {"vc3"})):
            for src, dst in (("i1", "i2"), ("i2", "i1")):
                vp, vq = inputs["local"][src], inputs["local"][dst]
                fam_p = {f: a for f, a in vp["families"].items() if f in fams}
                fam_q = {f: vq["families"][f] for f in fam_p if f in vq["families"]}
                if not fam_p:
                    continue
                Xp, _ = design_matrix(inputs["local_sigs"][src], view["ids"], feats, fill)
                Xq, _ = design_matrix(inputs["local_sigs"][dst], view["ids"], feats, fill)
                lopo_out[f"{set_name}|{src}->{dst}"] = lopo(vp["view"], Xp, vq["view"], Xq, fam_p, fam_q, params, boot,
                                                            feats)
    reproduction = fixed_rule_checks(inputs["local"], inputs["local_sigs"], boot)
    # the pinned routing table (tree, pre-Solver features, the chosen action set)
    names = [a for a in actions if a != NOOP and a in view["deltas"]]
    table = build_routing_table(view, sigs, params, fill=fill, features=list(FEATURE_GROUPS["pre"]),
                                actions=[NOOP, *names], oof={a: oof[a] for a in names}, groups="pre")
    table_choice = table.pop("_choice")
    mismatch = sum(1 for i, s in enumerate(view["ids"])
                   if route_row(table, {f: sigs[s].get(f) for f in table["features"]}) != table_choice[i])
    if mismatch:
        raise ScrError(f"the executable table disagrees with the fitted policy on {mismatch} rows")
    pools_meta = {k: {"run_id": POOLS[k]["run_id"], "attempt": POOLS[k]["attempt"], "rows": len(p["ids"]),
                      "arms": p["meta"], "phases_sha256": p["phases_sha256"], "phase_checks": p["phase_checks"]}
                  for k, p in inputs["pools"].items()}
    report = {
        "read_id": READ_ID, "recipe": RECIPE, "schema": SCHEMA, "status": "DESCRIPTIVE",
        "note": "development numbers (owner decisions 28 and 86); Fold B pools, cross-fitted by utterance-hash halves; "
                "zero contacts; no utterance text, transcript, gold value or model output is persisted",
        "inputs": {"pools": pools_meta, "rate_table": inputs["rate_table"], "exemplar_pool": inputs["exemplar_pool"],
                   "roster": inputs["roster"], "roster_split_identity_hash": inputs["roster_split_identity_hash"],
                   "reference_pool": REFERENCE_POOL, "rows": len(view["ids"]), "empty_gold_rows": inputs["gold_empty_rows"],
                   "clusters": inputs["boot_clusters"]},
        "parameters": {k: (list(v) if isinstance(v, tuple) else v) for k, v in params.items() if k != "feature_variants"},
        "feature_groups": {k: list(v) for k, v in params["feature_variants"].items()},
        "feature_definitions": {f: FEATURE_DOC[f] for fs in params["feature_variants"].values() for f in fs},
        "actions_requested": list(actions), "catalog": {a: CATALOG[a] for a in CATALOG},
        "bootstrap": {"unit": "whole utterance", "draws": args.draws, "seed": args.seed},
        "twin_nulls": twins, "reference_lock_v4g_slu_f1_pp": r4(DRV.pooled(view["base"])["slu_f1_pp"]),
        "reference_twin_v4g_slu_f1_pp": r4(DRV.pooled(view["twin"])["slu_f1_pp"]),
        "signature_agreement_with_reference_flight": inputs["signature_agreement"],
        "feature_groups_available": inputs["groups_available"], "tag_group_error": inputs["tag_error"],
        "single_action_everywhere": singles, "oracle": oracle, "crossfit": main,
        "margin_sensitivity_headline_default_subset": sensitivity,
        "leave_one_pool_out": lopo_out, "machinery_control_r6_gate_reproduced": reproduction,
        "routing_table_summary": {"in_sample_routed_rows": table["in_sample_routed_rows"], "cells": len(table["cells"]),
                                  "leaves": {a: len(v) for a, v in table["leaves"].items()},
                                  "executable_table_reproduces_fitted_policy_rows": len(view["ids"])},
        "contacts": dict(CONTACTS), "driver_sha256": digest(Path(__file__)),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    assert_zero_contacts(report)
    receipt = {
        "schema": "saea-slurp-scr-routing-table-receipt-v1", "table_id": TABLE_ID, "read_id": READ_ID, "rows": len(view["ids"]),
        "pool_roster": f"{ROSTER} (split identity {inputs['roster_split_identity_hash']})",
        "inputs": {k: {"run_id": v["run_id"], "attempt": v["attempt"], "phases_sha256": v["phases_sha256"],
                       "columns": {arm: {"first_visit_sha256": m["first_visit"][1], "scores_sha256": m["scores"][1],
                                         "v4g_slu_f1_pp": m["v4g_slu_f1_pp"]} for arm, m in v["arms"].items()}}
                   for k, v in pools_meta.items()},
        "rate_table": inputs["rate_table"], "exemplar_pool": inputs["exemplar_pool"], "roster": inputs["roster"],
        "actions": list(table["action_order"]), "feature_group": "pre", "features": table["features"],
        "parameters": report["parameters"], "bootstrap_seed": args.seed, "bootstrap_draws": args.draws,
        "driver_sha256": report["driver_sha256"], "contacts": dict(CONTACTS),
        "generated_at": report["generated_at"],
    }
    return {"report": report, "table": table, "receipt": receipt}


# ---------------------------------------------------------------------------
# rendering


def md(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def ci(c) -> str:
    return "-" if not c else f"[{c[0]:+.2f}, {c[1]:+.2f}]"


def render(rep: dict) -> str:
    out = [f"# {rep['read_id']} tables", "", rep["note"], "",
           f"rows {rep['inputs']['rows']} ({rep['inputs']['empty_gold_rows']} empty-gold); reference lock (v4g) SLU-F1 "
           f"{rep['reference_lock_v4g_slu_f1_pp']}; margin {rep['parameters']['margin_pp_per_row']:.5f} pp/row; "
           f"bootstrap {rep['bootstrap']}", "", "## Twin nulls (aa minus lock, v4g)", "",
           md(["pool", "lock SLU-F1", "aa - lock pp", "CI95"],
              [[k, v["lock_v4g_slu_f1_pp"], v["aa_minus_lock_slu_pp"], ci(v["ci95"])] for k, v in rep["twin_nulls"].items()]),
           "", "## Machinery control: the R6 gate (empty where c3 empties and N1 >= 0.2) reproduced through the delta path", "",
           md(["flight", "fired", "delta SLU pp", "CI95", "false fills base->new", "NE exact lost", "intent rows", "R6 note"],
              [[k, v["fired"], v["delta_slu_pp"], ci(v["ci95"]), v["false_fills_base_to_new"], v["nonempty_exact_lost"],
                v["intent_rows_moved"], v["r6_note"]] for k, v in rep["machinery_control_r6_gate_reproduced"].items()]),
           "", "## Single action applied everywhere (same-flight delta on the reference lock)", "",
           md(["action", "delta SLU pp", "CI95", "delta intent pp", "intent rows moved"],
              [[a, v["delta_vs_lock_slu_pp"], ci(v["ci95_vs_lock_slu_pp"]), v["delta_intent_pp"], v["intent_rows_moved"]]
               for a, v in rep["single_action_everywhere"].items()]), ""]
    cf = rep["crossfit"]
    for vkey, rec in cf["variants"].items():
        out += [f"## Cross-fitted routing: {vkey}", ""]
        if rec.get("unavailable"):
            out += ["feature group unavailable", ""]
            continue
        rows = []
        for sname, r in rec["subsets"].items():
            rows.append([sname, r["rows_routed"], r["routed_rows_by_action"], f"{r['delta_vs_lock_slu_pp']:+.2f}",
                         ci(r["ci95_vs_lock_slu_pp"]), f"{r.get('delta_vs_twin_slu_pp', float('nan')):+.2f}",
                         ci(r.get("ci95_vs_twin_slu_pp")), f"{r['delta_intent_pp']:+.2f}", r["intent_rows_moved"]])
        out += [md(["subset", "routed rows", "by action", "vs lock pp", "CI95", "vs aa pp", "CI95", "intent pp",
                    "intent rows moved"], rows), ""]
    head = cf["variants"]["tree|pre"]["subsets"]
    out += ["## Headline (tree, pre-Solver signature): exchange arithmetic", ""]
    out += [md(["subset", "false fills removed (net)", "NE exact lost", "NE exact gained", "raw exact net",
                "pred pp (FF x0.033 + NE x0.070)", "pred pp (raw x0.056)", "realised pp"],
               [[s, r["exchange"]["false_fills_removed_net"], r["exchange"]["nonempty_exact_lost"],
                 r["exchange"]["nonempty_exact_gained"], r["exchange"]["raw_exact_rows_net"],
                 r["exchange"]["predicted_pp_false_fill_x0.033_plus_nonempty_exact_x0.070"],
                 r["exchange"]["predicted_pp_raw_exact_x0.056"], r["exchange"]["realised_pp"]] for s, r in head.items()]), ""]
    for sname, r in head.items():
        if "per_scenario" not in r:
            continue
        out += [f"### Per-stratum ({sname}); equal-stratum weighting {r['equal_stratum']['delta_slu_pp']:+.2f} "
                f"{ci(r['equal_stratum']['ci95'])} vs natural mixture {r['equal_stratum']['natural_mixture_delta_slu_pp']:+.2f}",
                "", md(["scenario", "rows", "routed", "delta SLU pp (within scenario)", "CI95"],
                       [[k, v["rows"], v["routed"], v["delta_slu_pp"], ci(v["ci95"])] for k, v in r["per_scenario"].items()]),
                "", md(["gold", "rows", "routed", "delta pp (pooled over all rows, subset only)", "CI95", "extra"],
                       [[k, v["rows"], v["routed"], v["delta_slu_pp_of_all_rows_pooled"], ci(v["ci95"]),
                         {x: y for x, y in v.items() if x in ("false_fills_removed_net", "exact_lost", "exact_gained")}]
                        for k, v in r["empty_vs_non_empty"].items()]), ""]
    out += ["## Oracle per-row best action (ceiling; inflated by decoding noise)", "",
            md(["subset", "rows", "delta SLU pp", "CI95", "delta intent pp"],
               [[k, v["rows_routed"], v["delta_vs_lock_slu_pp"], ci(v["ci95_vs_lock_slu_pp"]), v["delta_intent_pp"]]
                for k, v in rep["oracle"].items()]), "",
            "## Margin sensitivity (headline tree, default subset; descriptive)", "",
            md(["margin", "routed", "delta SLU pp", "CI95", "intent pp", "intent rows"],
               [[k, v["rows_routed"], v["delta_vs_lock_slu_pp"], ci(v["ci95_vs_lock_slu_pp"]), v["delta_intent_pp"],
                 v["intent_rows_moved"]] for k, v in rep["margin_sensitivity_headline_default_subset"].items()]), "",
            "## Leave-one-pool-out (fit on one pool and one utterance half, score the other pool's other half)", "",
            md(["direction", "families", "routed", "by action", "lock pp", "routed pp", "delta pp", "CI95", "intent rows"],
               [[k, v["families"], v["rows_routed"], v["routed_rows_by_action"], v["slu_f1_lock_pp"], v["slu_f1_routed_pp"],
                 v["delta_vs_lock_slu_pp"], ci(v["ci95_vs_lock_slu_pp"]), v["intent_rows_moved"]]
                for k, v in rep["leave_one_pool_out"].items()]), ""]
    return "\n".join(out) + "\n"


def strip_time(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if '"generated_at"' not in line)


def jsonable(x):
    import numpy as np
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    return x


def dump(obj) -> str:
    return json.dumps(jsonable(obj), indent=1, sort_keys=True) + "\n"


def refuse_overwrite(*dirs: Path) -> None:
    for d in dirs:
        if d.exists():
            raise SystemExit(f"refusing to overwrite {d} (write-once)")


def dry(args) -> int:
    data_root = Path(args.data_root)
    ident = {"read_id": READ_ID, "table_id": TABLE_ID, "driver_sha256": digest(Path(__file__)),
             "parameters": {"max_depth": args.max_depth, "min_leaf": args.min_leaf,
                            "margin_pp_per_row": args.margin_pp_per_row if args.margin_pp_per_row is not None
                            else MARGIN_FRACTION * RATE_FALSE_FILL_REMOVED, "draws": args.draws, "seed": args.seed},
             "actions": list(args.actions), "out_dirs": [f"analysis/{READ_ID}", f"prepared/{TABLE_ID}"],
             "out_dirs_exist": [(data_root / "analysis" / READ_ID).exists(), (data_root / "prepared" / TABLE_ID).exists()],
             "pools": {}}
    for key, spec in POOLS.items():
        files = pool_files(data_root, spec)
        ident["pools"][key] = {"run_id": spec["run_id"], "attempt": spec["attempt"], "arms": {}}
        for arm, (fpath, spath) in files.items():
            ident["pools"][key]["arms"][arm] = {
                "first_visit": [str(fpath.relative_to(data_root)), digest(fpath) if fpath.exists() else None],
                "scores": [str(spath.relative_to(data_root)), digest(spath) if spath.exists() else None]}
    for rel in (R6.RATE_TABLE, R6.EX_SNAPSHOT):
        p = data_root / rel
        ident.setdefault("pinned", {})[rel] = digest(p) if p.exists() else None
    ident["roster"] = [ROSTER, digest(REPO_ROOT / ROSTER)]
    ident["contacts"] = dict(CONTACTS)
    print(json.dumps(ident, indent=1, sort_keys=True))
    return 0


def parse_actions(value: str):
    actions = [a.strip() for a in value.split(",") if a.strip()]
    unknown = [a for a in actions if a not in CATALOG]
    if unknown:
        raise SystemExit(f"unknown actions {unknown}; known {sorted(CATALOG)}")
    if NOOP not in actions:
        actions.insert(0, NOOP)
    return tuple(actions)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--actions", type=parse_actions, default=DEFAULT_ACTIONS,
                        help="comma-separated action ids (default: " + ",".join(DEFAULT_ACTIONS) + ")")
    parser.add_argument("--extended", action="store_true", help="also load every pool for the extended-all-loadable subset")
    parser.add_argument("--min-leaf", type=int, default=MIN_LEAF)
    parser.add_argument("--max-depth", type=int, default=MAX_DEPTH)
    parser.add_argument("--margin-pp-per-row", type=float, default=None,
                        help="route only when the predicted gain exceeds this pp per row (default: 0.1 x the 0.033 pp "
                             "false-fill exchange rate)")
    parser.add_argument("--shrink", type=float, default=0.0)
    parser.add_argument("--intent-weight", type=float, default=0.0,
                        help="add this many pp of intent per intent-correct row to the reward (default 0: SLU-F1 only)")
    parser.add_argument("--draws", type=int, default=BOOT_DRAWS)
    parser.add_argument("--seed", type=int, default=BOOT_SEED)
    parser.add_argument("--no-tag", dest="tag", action="store_false", help="skip the optional R6-P1 p1 tag feature group")
    parser.add_argument("--dry", action="store_true", help="print identities only")
    parser.add_argument("--no-write", action="store_true", help="run everything, print the headline, write nothing")
    args = parser.parse_args(argv)
    if args.dry:
        return dry(args)
    data_root = Path(args.data_root)
    out_dir = data_root / "analysis" / READ_ID
    table_dir = data_root / "prepared" / TABLE_ID
    if not args.no_write:
        refuse_overwrite(out_dir, table_dir)
    result = run(args)
    report, table, receipt = result["report"], result["table"], result["receipt"]
    texts = {"report.json": dump(report), "tables.md": render(report)}
    table_texts = {"routing-table-v1.json": dump(table), "routing-table-v1.md": render_table_md(table, receipt)}
    receipt["table_files_sha256"] = {n: hashlib.sha256(t.encode("utf-8")).hexdigest() for n, t in table_texts.items()}
    receipt["report_sha256_generated_at_stripped"] = {
        n: hashlib.sha256(strip_time(t).encode("utf-8")).hexdigest() for n, t in texts.items()}
    head = {s: {k: r[k] for k in ("rows_routed", "routed_rows_by_action", "delta_vs_lock_slu_pp", "ci95_vs_lock_slu_pp",
                                  "delta_intent_pp", "intent_rows_moved")}
            for s, r in report["crossfit"]["variants"]["tree|pre"]["subsets"].items()}
    if args.no_write:
        print(json.dumps(jsonable(head), indent=1))
        return 0
    out_dir.mkdir(parents=True)
    table_dir.mkdir(parents=True)
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    for name, text in table_texts.items():
        (table_dir / name).write_text(text, encoding="utf-8", newline="\n")
    (table_dir / "receipt.json").write_text(dump(receipt), encoding="utf-8", newline="\n")
    (out_dir / "content-sha256.json").write_text(dump(receipt["report_sha256_generated_at_stripped"]), encoding="utf-8",
                                                 newline="\n")
    print("wrote", out_dir)
    print("wrote", table_dir)
    print(json.dumps(jsonable(head), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
