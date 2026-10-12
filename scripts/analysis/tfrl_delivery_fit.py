#!/usr/bin/env python3
"""E-T3: the cross-fitted delivery-threshold fitter (zero GPU, text-free).

Design: ``docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md``
section 3.4 (delivery and scope candidates are not predicted; they are MEASURED offline, cross-fitted, and
accepted on CI95-LB > 0 and a point >= 0.67 pp) and section 5.3 (the same criterion over the column of the
state the candidate edits).

It takes ONE delivery-rule family of the v4g grammar (``rails/delivery_normalisers.py``: ``V4_STAGES``,
``V4G_GUARDS``) and ONE sealed, officially scored column, and answers: if the family's threshold is fitted on
one half of the fold and applied to the other half (both ways), what pooled SLU-F1 change does the
cross-fitted column buy over the sealed column, with what CI?  Families (each has one threshold ``t``):

* ``ee``      -- drop every entity of a row whose delivered intent carries entities in a TRAIN-pool share
                 whose Wilson upper bound (z = V4G_WILSON_Z) is below ``t`` (v4g ee10 is ``t = 0.10``);
                 an empty entity list is never filled (owner decision 199);
* ``ti``      -- drop an entity whose slot type co-occurs with the delivered intent in a TRAIN-pool share
                 below ``t``, only on an intent with at least ceil(1 / t) pool exemplars (v4g ti1 is
                 ``t = 0.01``, 100 exemplars);
* ``article`` -- strip a leading determiner of a filler of slot type ``x`` when ``x`` includes it in a
                 TRAIN-pool share below ``t`` over >= 10 opportunities (v4 fx-article is ``t = 0.10``).

* ``oclock``  -- strip a trailing ``o'clock`` / ``oclock`` token from a ``time`` filler of more than one token
                 (v4g stage ``fx-oclock``).  The rule has NO threshold: the grid is the single nominal point
                 ``t = 1.0`` and the fit is a plain paired read of apply-versus-not on the sealed column (applied
                 unconditionally, whatever the pool statistic decided for the lock; the report records that
                 decision).  ``--types`` / ``--intents`` restrict it to the candidate's slot types / delivered
                 intents (empty = unrestricted).

Statistics come from ONE pinned pool (the R5 pool, ``slurp_nx_postproc_v4_search.STATS_POOL``) whose
disjointness from Fold A and R01C is re-proved at run time.  Labels never change; only entities do.

Procedure (seed 20260915, the repo convention):
1. clusters = the fold's SLURP utterance ids, sorted; a ``numpy.default_rng(seed)`` permutation puts the first
   ceil(n / 2) clusters in half A and the rest in half B;
2. for each half H: fit ``t*(H)`` = the grid point with the highest pooled SLU-F1 point delta on H (ties: the
   fewer edited rows, then the smaller t); evaluate it on the OTHER half;
3. the cross-fitted column takes, for every row of half B, the edit of ``t*(A)`` and, for every row of half A,
   the edit of ``t*(B)``; its delta over the sealed column and its whole-utterance cluster-bootstrap CI95 (10,000
   draws, ``slurp_nx_postproc_v4_search.Bootstrap``) is the predicted effect;
4. the emitted rule uses ``t_full`` = the threshold fitted on the whole fold, and is emitted ONLY if the
   cross-fitted CI lower bound is above 0 (exit status 3 and no rule table otherwise).  The point >= 0.67 pp
   floor is reported as ``meets_point_floor`` and left to the driver's selection rule.

Output: ``fit-report-v1.json`` (``rule_table`` is null when refused) with ``report_sha256``.  Counts, rates, rule
and family names only; the same forbidden-key self-check as ``tfrl_contrast_tables.py``.  Zero model, server,
tokenizer, encoder, embedder, network and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/tfrl_delivery_fit.py --family ee \\
        --run-id SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1 \\
        --attempt attempt-slurp-native-stage3-nx-r5-composed-dev2000-added-generation-v1 \\
        --scorer slurp-slu-official --split devel --rows 1000
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCHEMA = "saea-tfrl-delivery-fit-v1"
SEED = 20260915
FLOOR_PP = 0.67
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
READ_ID = "SAEA-SLURP-TFRL-DELIVERY-FIT-V1"
FORBIDDEN_KEYS = frozenset({"text", "transcript", "gold", "value_text", "utterance", "answer"})
MAX_STRING = 200
ARTICLE_MIN_OPPORTUNITIES = 10
OCLOCK_TOKENS = ("o'clock", "oclock")

#: family -> default grid.  The v4g point of each family is on its grid.
GRIDS: dict[str, tuple[float, ...]] = {
    "ee": (0.02, 0.05, 0.10, 0.15, 0.20, 0.30),
    "ti": (0.005, 0.01, 0.02, 0.05, 0.10),
    "article": (0.05, 0.10, 0.20, 0.30, 0.50),
    "oclock": (1.0,),          # no threshold: one nominal point, a paired apply-vs-not read
}
FAMILIES = tuple(GRIDS)


class FitError(RuntimeError):
    """A sealed input is missing or drifted, or the report would carry forbidden content."""


# ---------------------------------------------------------------------------
# pure parts


def utterance_halves(clusters: Sequence[str], seed: int = SEED) -> tuple[set, set]:
    """Deterministic split of the sorted cluster ids into two halves (A gets the extra one on odd counts)."""

    import numpy as np

    ordered = sorted(set(clusters))
    order = np.random.default_rng(seed).permutation(len(ordered))
    cut = (len(ordered) + 1) // 2
    half_a = {ordered[i] for i in order[:cut]}
    half_b = {ordered[i] for i in order[cut:]}
    return half_a, half_b


def pooled_slu(matrix) -> float:
    """Pooled micro SLU-F1 (pp) of a count matrix whose first six columns are word/char tp, fp, fn."""

    s = matrix.sum(axis=0)
    tp, fp, fn = s[0] + s[3], s[1] + s[4], s[2] + s[5]
    den = 2 * tp + fp + fn
    return 0.0 if den == 0 else 100.0 * float(2 * tp / den)


def choose_threshold(grid: Sequence[float], delta_pp: Mapping[float, float],
                     edited_rows: Mapping[float, int]) -> float:
    """Highest point delta; ties -> fewer edited rows, then the smaller threshold (deterministic)."""

    return sorted(grid, key=lambda t: (-round(delta_pp[t], 9), edited_rows[t], t))[0]


def assert_text_free(node, path: str = "$") -> None:
    if isinstance(node, Mapping):
        for key, value in node.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise FitError(f"forbidden key {key!r} at {path}")
            assert_text_free(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for k, value in enumerate(node):
            assert_text_free(value, f"{path}[{k}]")
    elif isinstance(node, str) and len(node) > MAX_STRING:
        raise FitError(f"string longer than {MAX_STRING} characters at {path}")


def seal(document: dict, key: str) -> dict:
    assert_text_free(document)
    body = {k: v for k, v in document.items() if k != key}
    out = dict(body)
    out[key] = hashlib.sha256(json.dumps(body, indent=2, sort_keys=True).encode("utf-8")).hexdigest()
    return out


def article_strip_set(article_table: Mapping[str, Mapping], threshold: float) -> set:
    """The (type, determiner) pairs stripped at ``threshold`` (included share below it, >= 10 opportunities)."""

    out = set()
    for key, row in article_table.items():
        n = row["included"] + row["excluded"]
        if n >= ARTICLE_MIN_OPPORTUNITIES and row["included"] / n < threshold:
            typ, det = key.split("|", 1)
            out.add((typ, det))
    return out


def apply_family(family: str, t: float, pairs: list, intent: str | None, stats, env: Mapping) -> list:
    """One family at threshold ``t`` over (index, entity) pairs of one parsed delivered answer."""

    if not pairs:
        return pairs
    if family == "ee":
        if intent is None or stats.intent_n.get(intent, 0) == 0:
            return pairs
        upper = env["wilson_upper_bound"](stats.intent_with_entities.get(intent, 0), stats.intent_n[intent],
                                          env["z"])
        return [] if upper < t else pairs
    if family == "ti":
        if intent is None or stats.intent_n.get(intent, 0) < math.ceil(1.0 / t):
            return pairs
        return [(i, e) for i, e in pairs if stats.type_share(intent, e.type) >= t]
    if family == "article":
        strip = env["strip_cache"].setdefault(t, article_strip_set(stats.article_table, t))
        out = []
        for i, e in pairs:
            tokens = e.filler.split()
            if len(tokens) > 1 and (e.type, env["fold"](tokens[0])) in strip:
                e = env["SlotEntity"](type=e.type, filler=" ".join(tokens[1:]))
            out.append((i, e))
        return out
    if family == "oclock":
        intents, types = env.get("intents") or (), env.get("types") or ()
        if intents and intent not in intents:
            return pairs
        out = []
        for i, e in pairs:
            tokens = e.filler.split()
            if (e.type == "time" and (not types or e.type in types) and len(tokens) > 1
                    and tokens[-1].lower() in OCLOCK_TOKENS):
                e = env["SlotEntity"](type=e.type, filler=" ".join(tokens[:-1]))
            out.append((i, e))
        return out
    raise FitError(f"unknown family {family!r}; known: {list(FAMILIES)}")


# ---------------------------------------------------------------------------
# the read


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build_column(V4, P: Mapping, family: str, t: float, env: Mapping):
    """The sealed column's count matrix with the family at ``t`` applied; plus edit diagnostics."""

    import numpy as np

    matrix = P["base"].copy()
    diag = Counter()
    edited = np.zeros(len(P["ids"]), dtype=bool)
    for k, sid in enumerate(P["ids"]):
        row = P["delivered"]["rows"][sid]
        ents = row["entities"]
        if not row["parsed"] or not ents:
            continue
        ctx = P["contexts"][sid]
        pairs = apply_family(family, t, list(enumerate(ents)), ctx.intent, P["stats"], env)
        new = [e for _i, e in pairs]
        if new == list(ents):
            continue
        kept = {i for i, _e in pairs}
        edited[k] = True
        diag["rows_edited"] += 1
        diag["fillers_changed"] += sum(1 for i, e in pairs if e != ents[i])
        for i in range(len(ents)):
            if i not in kept:
                diag["entities_dropped"] += 1
                diag["dropped_" + P["classes"][sid][i]] += 1
        vec = V4.score_vector(P["gold"][sid], row["scenario"], row["action"], new)
        if vec[9] != matrix[k, 9]:
            raise FitError("a rule changed intent; rules must never touch labels")
        before, after = V4.row_f1(matrix[k]), V4.row_f1(vec)
        diag["row_saves"] += int(after > before + 1e-12)
        diag["row_harms"] += int(after < before - 1e-12)
        matrix[k] = np.array(vec)
    return matrix, edited, dict(sorted(diag.items()))


def fit(args) -> dict:
    import numpy as np

    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import fold
    from speech_aware_evidence_acquisition.rails import delivery_normalisers as DN
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    V4 = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py", "slurp_nx_postproc_v4_search")
    key = "tfrl-fit-column"
    V4.POOLS[key] = {"run_id": args.run_id, "attempt": args.attempt, "scorer": args.scorer, "split": args.split,
                     "rows": args.rows}
    ns = argparse.Namespace(data_root=args.data_root, lock=args.lock, row_cluster=False)
    P = V4.prepare_partA(ns, key)
    ids = P["ids"]
    grid = tuple(sorted(args.grid)) if args.grid else GRIDS[args.family]
    env = {"SlotEntity": SlotEntity, "fold": fold, "wilson_upper_bound": DN.wilson_upper_bound,
           "z": DN.V4G_WILSON_Z, "strip_cache": {},
           "intents": tuple(sorted(getattr(args, "intents", None) or ())), "types": tuple(sorted(getattr(args, "types", None) or ()))}

    columns, edited, diags = {}, {}, {}
    for t in grid:
        columns[t], edited[t], diags[t] = build_column(V4, P, args.family, t, env)

    clusters = [P["gold"][s]["utterance_id"] for s in ids]
    half_a, half_b = utterance_halves(clusters, args.seed)
    in_a = np.array([c in half_a for c in clusters])
    in_b = ~in_a
    base = P["base"]

    def delta_on(mask, t):
        return pooled_slu(columns[t][mask]) - pooled_slu(base[mask])

    def fit_on(mask):
        d = {t: delta_on(mask, t) for t in grid}
        n_edit = {t: int((edited[t] & mask).sum()) for t in grid}
        return choose_threshold(grid, d, n_edit), d

    t_a, d_a = fit_on(in_a)
    t_b, d_b = fit_on(in_b)
    cross = base.copy()
    cross[in_b] = columns[t_a][in_b]       # fitted on A, applied to B
    cross[in_a] = columns[t_b][in_a]       # fitted on B, applied to A
    contrast = P["boot"].contrast(base, cross)
    if contrast["delta_intent_pp"] != 0.0:
        raise FitError("intent moved")
    t_full, d_full = fit_on(np.ones(len(ids), dtype=bool))
    lower = contrast["ci95_slu_pp"][0]
    refused = not (lower > 0.0)
    scen = V4.per_scenario(ids, P["gold"], base, cross)
    report = {
        "schema": SCHEMA,
        "family": args.family,
        "grammar": "v4g (rails/delivery_normalisers.py V4_STAGES / V4G_GUARDS)",
        "source": {"run_id": args.run_id, "attempt": args.attempt, "scorer": args.scorer, "split": args.split,
                   "rows": len(ids), "clusters": P["boot"].clusters,
                   "outputs": P["delivered"]["outputs"], "scores": P["delivered"]["scores"],
                   "stats_pool": [V4.STATS_POOL[0], V4.STATS_POOL[1]]},
        "procedure": {"seed": args.seed, "bootstrap_draws": V4.BOOT_DRAWS, "bootstrap_seed": V4.BOOT_SEED,
                      "grid": list(grid), "half_a_clusters": len(half_a), "half_b_clusters": len(half_b),
                      "half_a_rows": int(in_a.sum()), "half_b_rows": int(in_b.sum())},
        "fits": {
            "half_a": {"threshold": t_a, "in_sample_delta_pp": round(d_a[t_a], 4),
                       "held_out_delta_pp_on_b": round(delta_on(in_b, t_a), 4)},
            "half_b": {"threshold": t_b, "in_sample_delta_pp": round(d_b[t_b], 4),
                       "held_out_delta_pp_on_a": round(delta_on(in_a, t_b), 4)},
            "full": {"threshold": t_full, "in_sample_delta_pp": round(d_full[t_full], 4)},
            "grid_deltas_full_pp": {str(t): round(d_full[t], 4) for t in grid},
        },
        "cross_fitted": {
            "delta_slu_pp": contrast["delta_slu_pp"], "ci95_slu_pp": contrast["ci95_slu_pp"],
            "delta_intent_pp": contrast["delta_intent_pp"],
            "left_slu_f1_pp": contrast["left_slu_f1_pp"], "right_slu_f1_pp": contrast["right_slu_f1_pp"],
            "meets_ci_lower_bound": not refused, "meets_point_floor": contrast["delta_slu_pp"] >= FLOOR_PP,
            "floor_pp": FLOOR_PP,
            "rows_edited": int(sum(1 for k in range(len(ids)) if (base[k] != cross[k]).any())),
            "per_scenario": scen,
        },
        "full_threshold_edits": diags[t_full],
        "scope": {"types": list(env["types"]), "intents": list(env["intents"])},
        "refused": refused,
        "refusal_reason": ("cross-fitted CI95 lower bound is not above 0" if refused else None),
        "rule_table": None if refused else {
            "schema": "saea-tfrl-delivery-rule-table-v1",
            "family": args.family,
            "parameters": {"threshold": t_full,
                           **({"wilson_z": DN.V4G_WILSON_Z, "interval": "wilson-score-upper"}
                              if args.family == "ee" else {}),
                           **({"min_pool_exemplars": math.ceil(1.0 / t_full)} if args.family == "ti" else {}),
                           **({"min_opportunities": ARTICLE_MIN_OPPORTUNITIES,
                               "strip_pairs": len(article_strip_set(P["stats"].article_table, t_full))}
                              if args.family == "article" else {}),
                           **({"tokens": list(OCLOCK_TOKENS), "types": list(env["types"]), "intents": list(env["intents"]),
                               "pool_decision_strip": bool(getattr(P["stats"], "oclock", {}).get("strip"))}
                              if args.family == "oclock" else {})},
            "fitted_on": {"run_id": args.run_id, "rows": len(ids), "split": args.split},
            "per_half_thresholds": {"half_a": t_a, "half_b": t_b},
            "predicted_slu_pp": contrast["delta_slu_pp"],
            "predicted_ci95_slu_pp": contrast["ci95_slu_pp"],
        },
    }
    return seal(report, "report_sha256")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--family", required=True, choices=FAMILIES)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--scorer", default="slurp-slu-official")
    parser.add_argument("--split", required=True, choices=("train", "devel"))
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--grid", type=lambda v: [float(x) for x in v.split(",")], default=None,
                        help="comma-separated thresholds (default: the family grid)")
    parser.add_argument("--types", type=lambda v: [x for x in v.split(",") if x], default=None,
                        help="comma-separated slot types the oclock family is restricted to (default: unrestricted)")
    parser.add_argument("--intents", type=lambda v: [x for x in v.split(",") if x], default=None,
                        help="comma-separated delivered intents the oclock family is restricted to (default: unrestricted)")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", DEFAULT_DATA_ROOT))
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)
    report = fit(args)
    out_dir = Path(args.out_dir) if args.out_dir else \
        Path(args.data_root) / "analysis" / "SAEA-SLURP-TFRL-TABLES-DEV-V1" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"fit-report-{args.family}-v1.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cf = report["cross_fitted"]
    print(f"tfrl delivery fit: family={args.family} cross-fitted {cf['delta_slu_pp']:+.4f} pp "
          f"CI95 {cf['ci95_slu_pp']} refused={report['refused']} wrote {out}")
    return 3 if report["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
