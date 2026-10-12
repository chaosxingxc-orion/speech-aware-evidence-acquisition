#!/usr/bin/env python3
"""VER-1 offline composer (owner decision 257, 2026-10-10): the verification layer's delivery rule over sealed pools.

Offline, zero GPU, zero model contact. VER-1 = the lock v2.2 Solver sampled N times per row (the ROLL form), a support filter
over the samples (an entity is kept iff it is supported by >= s of the N samples), the c3 presence verdict (the first-visit
output of a template arm: "answered no entity") gated by the pre-Solver entity-free share N1 >= theta, and the registered
v4g normaliser. This driver evaluates every delivery rule of that family as a delivered column scored in-process with the
official path (the SLURP port, identity-checked against the official evaluate.py by the sealed scorers; v3 label/filler
projection and v4g are applied through the registered delivery normalisers, never re-implemented here), on any sealed pool:

* a SAMPLE POOL run: ``<run>.outputs.jsonl`` rows that carry ``solver_group.samples`` (the ROLL-form custody). Loader is generic
  over the run id; sample 0 may be greedy (the VER-1a Fold B pool) or a temperature-0.7 draw (ROLL-1/2/3);
* an optional VERDICT column: the first-visit output of a template arm of an NX R1 run on the same rows (``r1-c3`` of
  iteration 1, ``r1-i2-c3`` of iteration 2); verdict = the arm answered no entity after the registered v4g normaliser;
* the pre-Solver signature N1 (the share of the 20 supplied exemplars that carry no entity) from a sealed ``phases.json``
  through the R6 driver's ``row_signals``;
* the registered normalisers (``saea-deliver-normalise-v3`` / ``-v4`` / ``-v4g``) from ``core.base.DELIVERY_NORMALISERS``.

Rules (each a delivered column): the support filter at ``s`` over the first ``n`` samples on a base sample (``first`` = sample
0, ``medoid`` = the aggregation read's R1 medoid) with the intent of the base, of sample 0 or of the plurality of the samples;
the registered ``saea-commit-plurality-support-v1`` at ``min_support = s``; the c3verdict x N1 >= theta gate (a fired row
delivers its labels with an empty entity list) over the bare first sample and over every filtered column; each at the
sealed base normaliser and under v4g. Selected thresholds (s, theta) are cross-fitted by utterance-hash halves.

Comparators: the pool's first sample ``S0``, the mean of the first ``n`` single-sample arms ``MEAN`` (the aggregation read's
R0), the sealed delivered commit of the pool run re-scored in-process (``DELIVERED``), a lock column and an A/A twin when the
verdict pool supplies them. Statistics: pooled official SLU-F1 and intent, whole-cluster paired bootstrap (10,000 draws, seed
20260915), per-stratum tables (scenario natural / equal; empty-gold vs non-empty), false fills removed, non-empty exact rows
lost / gained, intent rows moved, the exchange arithmetic (0.033 / 0.070 / 0.056 pp per row) and the per-row oracle ceilings.

Machinery controls (``--mode controls``) MUST reproduce before any new number is reported: the ROLL-1 s=3-of-5 filter
(+1.40 [+0.55, +2.29] at row clusters), the ROLL-3 2-of-3 filter over v4 (+0.84 [+0.19, +1.49]) and 3-of-5 (+1.11 [+0.33,
+1.91]), and the R6 c3verdict x N1 >= 0.2 gate on v4g for R1 i1 / i2 (+0.75 / +0.98).

Gold discipline: gold enters only offline through the governed SLURP loaders (TRAIN / DEVEL; the test split is refused);
the test-sample runs are never opened. Text discipline: no utterance text, transcript, gold value, filler, note body or model
output is printed or persisted -- ids are not persisted either; counts, rates, pp, CIs, hashes and labels only.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_ver1_offline.py --mode controls
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_ver1_offline.py --mode read --pool roll2 --label ROLL2-FOLD-A
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_ver1_offline.py --mode read --run-id <RUN> --attempt <ATTEMPT> \\
        --split train --rows 1080 --verdict i1,i2 --label VER1A-FOLD-B
    # a verdict column of another flight (the VER-1c Fold A c3 column), combinable with --verdict:
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_ver1_offline.py --mode read --run-id <POOL RUN> --attempt <ATTEMPT> \\
        --split train --rows 1080 --n 3 --s 2 --thetas 0.2 --verdict-run <RUN>:<ATTEMPT>:r1-c3 --label VER1B-FOLD-A
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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

READ_ID_PREFIX = "SAEA-SLURP-VER1-OFFLINE"
RECIPE = "slurp-ver1-offline-composer-v1"
SCHEMA = "saea-slurp-ver1-offline-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
BOOT_DRAWS = 10_000
BOOT_SEED = 20260915
FLOOR_PP = 0.67
THETAS = tuple(round(0.1 * k, 1) for k in range(1, 10))
GATE_THETA = 0.2
SIMILARITY = 0.8
RATE_FALSE_FILL_REMOVED = 0.033
RATE_NONEMPTY_EXACT = 0.070
RATE_RAW_EXACT = 0.056
NORM_IDS = {"v3": "saea-deliver-normalise-v3", "v4": "saea-deliver-normalise-v4", "v4g": "saea-deliver-normalise-v4g"}
CONTACTS = {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer_subprocess": 0,
            "network": 0, "gpu": 0, "paid_api": 0}
#: the delivery rule forms: (sample the entities are taken from, source of the intent label)
FORMS = (("first", "first"), ("first", "plurality"), ("medoid", "base"))
#: the form the VER-1 proposal names (sample 0 = today's delivery; its labels)
PRIMARY_FORM = ("first", "first")

#: sealed sample pools the driver knows by name (run ids, attempts and scorers from the pool-read notes).
POOLS = {
    "roll1": {"run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
              "attempt": "attempt-slurp-native-stage3-rollout-r01-generation-v1",
              "score_root": "analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1",
              "scorer": "slurp-slu-official-projected-v3-train", "sealed_scorer": "slurp-slu-official-train",
              "split": "train", "rows": 625, "base_norm": "v3",
              "label": "ROLL-1 R01C, v2.0 PLAN grouped Solver, five temperature-0.7 samples"},
    "roll2": {"run_id": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1",
              "attempt": "attempt-slurp-native-stage3-roll-2-fold-a-v1-generation",
              "score_root": "analysis/SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1",
              "scorer": "slurp-slu-official-projected-v3-train", "sealed_scorer": "slurp-slu-official-train",
              "split": "train", "rows": 1080, "base_norm": "v3",
              "label": "ROLL-2 TRAIN Fold A, grouped Solver, five temperature-0.7 samples"},
    "roll3": {"run_id": "SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1",
              "attempt": "attempt-slurp-native-stage3-roll-3-dev2000-added-v1-generation",
              "score_root": "analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1",
              "scorer": "slurp-slu-official-projected-v3", "sealed_scorer": "slurp-slu-official",
              "split": "devel", "rows": 1000, "base_norm": "v3",
              "label": "ROLL-3 DEV-2000-ADDED, grouped Solver, five temperature-0.7 samples"},
}


class ComposerError(RuntimeError):
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
AG = import_path(REPO_ROOT / "scripts/analysis/slurp_sample_aggregation_offline_read.py",
                 "slurp_sample_aggregation_offline_read")
SCR = import_path(REPO_ROOT / "scripts/analysis/slurp_scr_offline_learner.py", "slurp_scr_offline_learner")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def r4(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)


class Col(NamedTuple):
    """A delivered column: ten count columns per row, and the same column with every row's entity list emptied."""

    m: "object"
    e: "object"


# ---------------------------------------------------------------------------
# normalisers and scoring


def make_normaliser(name: str):
    """``none`` -> identity; ``v3`` / ``v4`` / ``v4g`` -> the registered delivery normaliser (memoised by text)."""

    if name == "none":
        return lambda text: text
    if name not in NORM_IDS:
        raise ComposerError(f"unknown normaliser {name!r}; choose none, {', '.join(NORM_IDS)}")
    from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
    from speech_aware_evidence_acquisition.rails import delivery_normalisers  # noqa: F401
    fn = DELIVERY_NORMALISERS.resolve(NORM_IDS[name])
    cache: dict = {}

    def normalise(text: str) -> str:
        out = cache.get(text)
        if out is None:
            out = cache[text] = fn(text).text
        return out

    return normalise


def score_col(ids, texts: dict, gold: dict, norm) -> Col:
    """Normalise each text, then the SLURP port: ten count columns per row (word/char TP/FP/FN, slot-exact TP/FP/FN,
    scenario-action exact) and the same with the entity list dropped."""
    normed = {sid: norm(texts[sid]) for sid in ids}
    m, e = R6.score_texts(list(ids), normed, gold)
    return Col(m, e)


def pred_items(m):
    return m[:, 6] + m[:, 7]


def verdict_flags(m_arm) -> list:
    """Verdict = the template arm answered no entity (the registered, normalised column predicts zero slot items)."""
    return [bool(x == 0) for x in pred_items(m_arm)]


def gate_fired(verdict, n1, theta: float) -> list:
    return [bool(v and x >= theta) for v, x in zip(verdict, n1)]


def apply_gate(col: Col, fired) -> Col:
    """A fired row delivers its labels with an empty entity list (the R6 ``empty`` behaviour)."""
    import numpy as np
    mask = np.asarray(fired, dtype=bool)
    out = col.m.copy()
    out[mask] = col.e[mask]
    return Col(out, col.e)


# ---------------------------------------------------------------------------
# the sample pool: loading, rendering, rules


def load_sample_pool(data_root: Path, spec: dict) -> dict:
    """The ROLL-form custody of a sealed run: per row the samples (parsed answers or None) and the delivered text."""
    directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
    if not directory.is_dir():
        raise ComposerError(f"no sealed attempt directory at {directory}")
    sealed = AG.load_sealed_run(directory, spec["run_id"])
    ids = sorted(sealed)
    if spec.get("rows") and len(ids) != spec["rows"]:
        raise ComposerError(f"{spec['run_id']}: {len(ids)} rows, expected {spec['rows']}")
    counts = {len(sealed[s]["samples"]) for s in ids}
    if len(counts) != 1 or min(counts) < 1:
        raise ComposerError(f"{spec['run_id']}: rows carry differing sample counts {sorted(counts)}")
    outputs = directory / f"{spec['run_id']}.outputs.jsonl"
    return {"ids": ids, "sealed": sealed, "n_samples": counts.pop(),
            "outputs": [str(outputs.relative_to(data_root)), digest(outputs)], "directory": directory}


def single_text(record: dict, index: int) -> str:
    """Sample ``index`` rendered through the canonical path (the empty answer when the sample is malformed)."""
    entry = record["samples"][index]
    return AG.render_answer(entry["parsed_answer"]) if entry["parsed_answer"] is not None else AG.EMPTY_ANSWER


def sub_answers(answers: dict, n: int) -> dict:
    return {i: a for i, a in answers.items() if i < n}


def pick_base(sub: dict, base: str):
    if not sub:
        return None
    if base == "first":
        return min(sub)
    if base == "medoid":
        return AG.medoid_index(sub, sorted(sub))[0]
    raise ComposerError(f"unknown base {base!r}")


def pick_intent(sub: dict, base_idx: int, mode: str) -> tuple:
    if mode == "base":
        a = sub[base_idx]
    elif mode == "first":
        a = sub[min(sub)]
    elif mode == "plurality":
        intent, _members = AG.plurality_intent_members(sub)
        if intent is None:
            a = sub[base_idx]
        else:
            return (str(intent[0]), str(intent[1]))
    else:
        raise ComposerError(f"unknown intent mode {mode!r}")
    return (a.scenario, a.action)


def row_supports(sub: dict, base_idx: int, similarity: float) -> list:
    """[(entity, number of valid samples that support it)] over the base sample's entities (the aggregation read's
    ``support_of_entity``: same type, normalised-filler character F1 >= similarity)."""
    return [(e, AG.support_of_entity(e, sub, similarity)) for e in sub[base_idx].entities]


def render_rule(intent: tuple, supports: list, s: int) -> str:
    kept = [{"type": e.type, "filler": e.filler} for e, support in supports if support >= s]
    return AG.render_answer({"scenario": intent[0], "action": intent[1], "entities": kept})


def rule_key(n: int, s: int, base: str, intent: str) -> str:
    return f"n{n}-s{s}-{base}-{intent}"


def build_rule_texts(sealed: dict, ids, n: int, ss, forms, similarity: float = SIMILARITY) -> dict:
    """Every support-filter rule over the first ``n`` samples: key -> {sample_id: rendered answer}. ``s = 1`` keeps every entity
    of the base sample (the unfiltered base, the aggregation read's R1 for the medoid)."""
    out = {rule_key(n, s, b, i): {} for (b, i) in forms for s in ss}
    for sid in ids:
        answers = sub_answers(AG._parsed_answers(sealed[sid]), n)
        if not answers:
            for key in out:
                out[key][sid] = AG.EMPTY_ANSWER
            continue
        base_cache: dict = {}
        for (b, i) in forms:
            if b not in base_cache:
                idx = pick_base(answers, b)
                base_cache[b] = (idx, row_supports(answers, idx, similarity))
            idx, supports = base_cache[b]
            intent = pick_intent(answers, idx, i)
            for s in ss:
                out[rule_key(n, s, b, i)][sid] = render_rule(intent, supports, s)
    return out


def build_registered_texts(sealed: dict, ids, n: int, ss, similarity: float = SIMILARITY) -> dict:
    """The registered ``saea-commit-plurality-support-v1`` at ``min_support = s`` over the first ``n`` samples."""
    from speech_aware_evidence_acquisition.core.base import COMMIT_POLICIES
    from speech_aware_evidence_acquisition.rails import commit_policies  # noqa: F401
    from speech_aware_evidence_acquisition.rails.commit_policies import SolverSampleVote
    policy = COMMIT_POLICIES.resolve(AG.FLOWN_COMMIT_POLICY)
    out = {f"n{n}-registered-s{s}": {} for s in ss}
    for sid in ids:
        answers = AG._parsed_answers(sealed[sid])
        votes = [SolverSampleVote(sample_index=i, parsed=answers.get(i)) for i in range(n)]
        for s in ss:
            outcome = policy(votes, min_support=s, similarity_threshold=similarity)
            out[f"n{n}-registered-s{s}"][sid] = AG.render_answer({
                "scenario": outcome.answer.scenario, "action": outcome.answer.action,
                "entities": [{"type": e.type, "filler": e.filler} for e in outcome.answer.entities]})
    return out


# ---------------------------------------------------------------------------
# statistics: contrasts, exchange arithmetic, strata, oracles, cross-fit


def contrast_block(boot, comp, new, *, comp_raw=None, new_raw=None, gold_empty=None, integer: bool = True) -> dict:
    """``new`` against ``comp`` (ten-column count matrices): delta with the paired CI95 and, for integer comparators, the false
    fills removed, the non-empty exact rows lost / gained, the intent rows moved and the exchange arithmetic. ``comp_raw`` /
    ``new_raw`` are the same columns at the base normaliser (for the raw-exact exchange; the same matrices when omitted)."""
    import numpy as np
    c = boot.contrast(comp, new)
    out = {"slu_f1_pp": c["right_slu_f1_pp"], "comparator_slu_f1_pp": c["left_slu_f1_pp"],
           "delta_slu_pp": c["delta_slu_pp"], "ci95_slu_pp": c["ci95_slu_pp"],
           "delta_span_pp": c["delta_span_pp"], "delta_intent_pp": c["delta_intent_pp"],
           "ci95_intent_pp": c["ci95_intent_pp"], "ci_lb_above_zero": bool(c["ci95_slu_pp"][0] > 0.0)}
    if integer and gold_empty is not None:
        ge = np.asarray(gold_empty, dtype=bool)
        comp_raw = comp if comp_raw is None else comp_raw
        new_raw = new if new_raw is None else new_raw
        ind = SCR.indicators(comp, new, comp_raw, new_raw, ge)
        ff, ne, raw = int(ind["ff"].sum()), ind["ne"], int(ind["raw"].sum())
        gained, lost = int((ne > 0).sum()), int((ne < 0).sum())
        out.update({
            "false_fill_rows_comparator": int(((pred_items(comp) > 0) & ge).sum()),
            "false_fill_rows_new": int(((pred_items(new) > 0) & ge).sum()),
            "false_fills_removed_net": ff,
            "nonempty_exact_lost": lost, "nonempty_exact_gained": gained,
            "raw_exact_rows_net": raw,
            "intent_rows_moved": int(np.sum(np.abs(new[:, 9] - comp[:, 9]) > 1e-9)),
            "rows_changed": int(np.sum(np.any(new != comp, axis=1))),
            "exchange": {
                "predicted_pp_false_fill_x0.033_plus_nonempty_exact_x0.070": round(
                    RATE_FALSE_FILL_REMOVED * ff + RATE_NONEMPTY_EXACT * (gained - lost), 4),
                "predicted_pp_raw_exact_x0.056": round(RATE_RAW_EXACT * raw, 4),
                "realised_pp": c["delta_slu_pp"]}})
    return out


def strata_block(boot, comp, new, scenario, gold_empty) -> dict:
    """Per-scenario deltas (natural), the equal-stratum weighting and the empty-gold / non-empty-gold split."""
    import numpy as np
    scen = np.array(scenario, dtype=object)
    ge = np.asarray(gold_empty, dtype=bool)
    per = {}
    for s in sorted(set(scenario)):
        mask = scen == s
        d = DRV.pooled(new[mask])["slu_f1_pp"] - DRV.pooled(comp[mask])["slu_f1_pp"]
        per[s] = {"rows": int(mask.sum()), "changed_rows": int(np.sum(np.any(new[mask] != comp[mask], axis=1))),
                  "delta_slu_pp": r4(d),
                  "ci95": boot.contrast(comp * mask[:, None], new * mask[:, None])["ci95_slu_pp"]}
    w = SCR.stratum_weights(list(scenario))[:, None]
    eq = boot.contrast(comp * w, new * w)
    halves = {}
    for name, mask in (("empty_gold", ge), ("non_empty_gold", ~ge)):
        # the contribution of one gold half to the pooled delta: only that half's rows take the new column. (A pooled F1
        # over the empty-gold rows alone is identically 0 -- no gold entity, no TP -- so it cannot carry a delta.)
        mixed = comp.copy()
        mixed[mask] = new[mask]
        cc = boot.contrast(comp, mixed)
        halves[name] = {"rows": int(mask.sum()), "changed_rows": int(np.sum(np.any(new[mask] != comp[mask], axis=1))),
                        "contribution_to_pooled_delta_pp": cc["delta_slu_pp"], "ci95": cc["ci95_slu_pp"]}
    return {"per_scenario": per,
            "equal_stratum": {"delta_slu_pp": eq["delta_slu_pp"], "ci95": eq["ci95_slu_pp"],
                              "natural_mixture_delta_slu_pp": r4(
                                  DRV.pooled(new)["slu_f1_pp"] - DRV.pooled(comp)["slu_f1_pp"])},
            "empty_vs_non_empty": halves}


def oracle_best_of(mats):
    """Per row the best of the given columns by the row's SLU-F1 (ties by intent, then the lowest index): an UPPER BOUND that
    sees the gold, never a rule."""
    import numpy as np
    stack = np.stack([np.asarray(x, dtype=np.float64) for x in mats])
    best = np.zeros(stack.shape[1:])
    for k in range(stack.shape[1]):
        keys = [(DRV.row_f1(stack[j][k]), stack[j][k][9]) for j in range(stack.shape[0])]
        j = max(range(len(keys)), key=lambda t: (keys[t][0], keys[t][1], -t))
        best[k] = stack[j][k]
    return best


def crossfit_pick(candidates: dict, base, halves) -> tuple:
    """Cross-fit the choice of one candidate column by utterance-hash halves: on each half fit the candidate with the highest
    pooled SLU-F1 on the OTHER half (ties: the first listed), and deliver that candidate's rows on this half."""
    import numpy as np
    h = np.asarray(halves)
    out = np.array(base, dtype=np.float64, copy=True)
    chosen = {}
    for k in (0, 1):
        fit, apply = h != k, h == k
        scored = [(DRV.pooled(np.asarray(m)[fit])["slu_f1_pp"], -pos, name)
                  for pos, (name, m) in enumerate(candidates.items())]
        best = max(scored)[2]
        chosen[f"half_{k}"] = best
        out[apply] = np.asarray(candidates[best])[apply]
    return out, chosen


# ---------------------------------------------------------------------------
# the composition: every rule of one pool as a delivered column, scored and contrasted


def _mean_m(cols, names):
    import numpy as np
    return np.mean([cols[n].m for n in names], axis=0)


def _n_of(key: str) -> int:
    return int(key.split("-")[0][1:])


def build_columns(*, ids, gold, sealed, n_samples, norm_names, ns, ss, forms, similarity, normalisers,
                  delivered=None, registered=True) -> dict:
    """Phase A: ``cols[norm][key]`` for the single-sample arms, every support-filter rule, the registered commit policy
    and the sealed delivered commit."""
    singles_text = [{sid: single_text(sealed[sid], i) for sid in ids} for i in range(n_samples)]
    rule_texts: dict = {}
    for n in ns:
        rule_texts.update(build_rule_texts(sealed, ids, n, [1] + [s for s in ss if 2 <= s <= n], forms, similarity))
        if registered:
            rule_texts.update(build_registered_texts(sealed, ids, n, [s for s in ss if 2 <= s <= n], similarity))
    cols: dict = {}
    for nm in norm_names:
        c: dict = {}
        for i in range(n_samples):
            c[f"single{i}"] = score_col(ids, singles_text[i], gold, normalisers[nm])
        for key, texts in rule_texts.items():
            c[key] = score_col(ids, texts, gold, normalisers[nm])
        if delivered is not None:
            c["DELIVERED"] = score_col(ids, delivered, gold, normalisers[nm])
        cols[nm] = c
    return cols


def comparators_of(cols_nm: dict, n: int, verdict_cols: dict) -> dict:
    """name -> (matrix, integer?) : S0, the mean of the first ``n`` singles, the delivered commit, lock / A/A columns."""
    comps = {"S0": (cols_nm["single0"].m, True), f"MEAN{n}": (_mean_m(cols_nm, [f"single{i}" for i in range(n)]), False)}
    if "DELIVERED" in cols_nm:
        comps["DELIVERED"] = (cols_nm["DELIVERED"].m, True)
    for vk, c in verdict_cols.items():
        comps[f"lock:{vk}"] = (c["lock"].m, True)
        if "aa" in c:
            comps[f"aa:{vk}"] = (c["aa"].m, True)
    return comps


def evaluate_pool(*, ids, gold, sealed, n_samples, norm_names, ns, ss, forms, thetas, similarity, boot,
                  verdicts=None, n1=None, delivered=None, detail=True, registered=True, normalisers=None,
                  extras=True) -> dict:
    """Every delivery rule of the VER-1 family over one sealed sample pool.

    ``sealed[sid]["samples"]`` is the ROLL-form custody (``slurp_sample_aggregation_offline_read.load_sealed_run``);
    ``gold[sid]`` the governed gold row; ``norm_names`` the normalisers a column is scored under (the first is the base, the
    pool's own scoring convention); ``verdicts`` maps a verdict-source key to ``{"flags": [...], "cols": {norm: {"lock": Col,
    "aa": Col}}}``; ``n1`` is the per-row entity-free share; ``delivered`` is {sample_id: sealed delivered text}. Returns the
    machine-readable report (no text, no ids)."""
    import numpy as np

    ids = list(ids)
    gold_empty = [not gold[s]["entities"] for s in ids]
    scenario = [gold[s]["scenario"] for s in ids]
    halves = [R6.half_of(gold[s]["utterance_id"]) for s in ids]
    verdicts = verdicts or {}
    if verdicts and n1 is None:
        raise ComposerError("a verdict gate needs the N1 signature")
    norms = normalisers or {nm: make_normaliser(nm) for nm in norm_names}
    base_norm = norm_names[0]
    ns = [n for n in ns if 1 <= n <= n_samples]
    if not ns:
        raise ComposerError("no usable sample count")
    n_max = max(ns)
    cols = build_columns(ids=ids, gold=gold, sealed=sealed, n_samples=n_samples, norm_names=norm_names, ns=ns, ss=ss,
                         forms=forms, similarity=similarity, normalisers=norms, delivered=delivered, registered=registered)
    rule_keys = [k for k in cols[base_norm] if k.startswith("n") and not k.startswith("single")]

    # phase A2: the gated variants (identical meta in every norm)
    variant_meta: dict = {}
    variants: dict = {nm: {} for nm in norm_names}
    for key in list(cols[base_norm]):
        variant_meta[key] = {"n": _n_of(key) if key in rule_keys else n_max, "gate": None}
        for nm in norm_names:
            variants[nm][key] = cols[nm][key]
    gate_bases = ["single0"] + [k for k in rule_keys if "-s1-" not in k]
    fired_of: dict = {}
    for vk, v in verdicts.items():
        for bkey in gate_bases:
            n = _n_of(bkey) if bkey in rule_keys else n_max
            for theta in thetas:
                fired = gate_fired(v["flags"], n1, theta)
                gkey = f"{'S0' if bkey == 'single0' else bkey}+gate[{vk},{theta}]"
                variant_meta[gkey] = {"n": n, "gate": {"verdict_source": vk, "theta": theta, "base": bkey,
                                                       "fired": int(sum(fired)),
                                                       "fired_empty_gold": int(sum(f and e for f, e in zip(fired, gold_empty)))}}
                fired_of[gkey] = fired
                for nm in norm_names:
                    variants[nm][gkey] = apply_gate(cols[nm][bkey], fired)

    out = {"rows": len(ids), "empty_gold_rows": int(sum(gold_empty)), "samples_in_pool": n_samples, "ns": ns,
           "ss": list(ss), "thetas": list(thetas), "forms": [list(f) for f in forms], "similarity": similarity,
           "base_norm": base_norm,
           "verdict_sources": {k: {"verdict_empty_rows": int(sum(v["flags"])),
                                   "verdict_on_empty_gold": int(sum(f and e for f, e in zip(v["flags"], gold_empty)))}
                               for k, v in verdicts.items()},
           "norms": {}}
    if n1 is not None:
        out["n1_share_quantiles"] = {str(q): r4(float(np.quantile(n1, q))) for q in (0.1, 0.25, 0.5, 0.75, 0.9)}

    for nm in norm_names:
        block: dict = {"comparators": {}, "variants": {}, "crossfit": {}, "oracles": {}}
        vcols = {vk: v["cols"][nm] for vk, v in verdicts.items() if nm in v["cols"]}
        vcols_base = {vk: v["cols"][base_norm] for vk, v in verdicts.items() if base_norm in v["cols"]}
        s0 = cols[nm]["single0"]
        for cname, (m, _i) in comparators_of(cols[nm], n_max, vcols).items():
            block["comparators"][cname] = {"slu_f1_pp": r4(DRV.pooled(m)["slu_f1_pp"]),
                                           "intent_pp": r4(DRV.pooled(m)["intent_pp"])}
        for i in range(n_samples):
            m = cols[nm][f"single{i}"].m
            block["comparators"][f"single{i}"] = {"slu_f1_pp": r4(DRV.pooled(m)["slu_f1_pp"]),
                                                  "intent_pp": r4(DRV.pooled(m)["intent_pp"])}
        for key, col in variants[nm].items():
            meta = variant_meta[key]
            n = meta["n"]
            rec = {"n": n, "pooled_slu_f1_pp": r4(DRV.pooled(col.m)["slu_f1_pp"]),
                   "pooled_intent_pp": r4(DRV.pooled(col.m)["intent_pp"]), "vs": {}}
            if meta["gate"]:
                rec["gate"] = meta["gate"]
            block["variants"][key] = rec
            if key.startswith("single"):
                continue
            comps = comparators_of(cols[nm], n, vcols)
            comps_raw = comparators_of(cols[base_norm], n, vcols_base)
            for cname, (cm, integer) in comps.items():
                rec["vs"][cname] = contrast_block(boot, cm, col.m, comp_raw=comps_raw[cname][0],
                                                  new_raw=variants[base_norm][key].m, gold_empty=gold_empty, integer=integer)
            gated = meta["gate"] is not None
            if detail and ((not gated and "-s1-" not in key) or (gated and meta["gate"]["theta"] == GATE_THETA)):
                rec["strata_vs_S0"] = strata_block(boot, s0.m, col.m, scenario, gold_empty)

        if extras:
            # cross-fit of the selected thresholds (s, theta) by utterance-hash halves
            for n in ns:
                s_list = [1] + [s for s in ss if 2 <= s <= n]
                comps = comparators_of(cols[nm], n, vcols)
                for (b, i) in forms:
                    cands = {f"s{s}": cols[nm][rule_key(n, s, b, i)].m for s in s_list}
                    picked, chosen = crossfit_pick(cands, s0.m, halves)
                    block["crossfit"][f"s::n{n}-{b}-{i}"] = {
                        "candidates": list(cands), "chosen": chosen, "floor_pp": FLOOR_PP,
                        "vs": {c: contrast_block(boot, cm, picked, gold_empty=gold_empty, integer=integer)
                               for c, (cm, integer) in comps.items()}}
                    for vk, v in verdicts.items():
                        vcands = {}
                        for s in s_list:
                            bcol = cols[nm][rule_key(n, s, b, i)]
                            vcands[f"s{s}|none"] = bcol.m
                            for theta in thetas:
                                vcands[f"s{s}|theta{theta}"] = apply_gate(bcol, gate_fired(v["flags"], n1, theta)).m
                        picked, chosen = crossfit_pick(vcands, s0.m, halves)
                        block["crossfit"][f"s-theta::{vk}::n{n}-{b}-{i}"] = {
                            "candidates": len(vcands), "chosen": chosen, "floor_pp": FLOOR_PP,
                            "vs": {c: contrast_block(boot, cm, picked, gold_empty=gold_empty, integer=integer)
                                   for c, (cm, integer) in comps.items()}}

            # per-row oracle ceilings (they see the gold; upper bounds, never rules)
            for n in ns:
                comps = comparators_of(cols[nm], n, vcols)
                oc: dict = {f"best_of_{n}_samples": oracle_best_of([cols[nm][f"single{i}"].m for i in range(n)]),
                            "perfect_gate_on_S0": apply_gate(s0, gold_empty).m}
                pool_mats = [s0.m]
                for s in [s for s in ss if 2 <= s <= n]:
                    fcol = cols[nm][rule_key(n, s, *PRIMARY_FORM)]
                    oc[f"perfect_gate_on_filter_s{s}"] = apply_gate(fcol, gold_empty).m
                    pool_mats.append(fcol.m)
                for vk, v in verdicts.items():
                    oc[f"perfect_verdict_gate_on_S0::{vk}"] = apply_gate(
                        s0, [bool(f and e) for f, e in zip(v["flags"], gold_empty)]).m
                    for s in [s for s in ss if 2 <= s <= n]:
                        fcol = cols[nm][rule_key(n, s, *PRIMARY_FORM)]
                        pool_mats.append(apply_gate(fcol, gate_fired(v["flags"], n1, GATE_THETA)).m)
                oc[f"best_of_rules_n{n}"] = oracle_best_of(pool_mats)
                block["oracles"][f"n{n}"] = {
                    name: {"slu_f1_pp": r4(DRV.pooled(m)["slu_f1_pp"]),
                           "delta_vs_S0_pp": contrast_block(boot, s0.m, m, integer=False)["delta_slu_pp"],
                           f"delta_vs_MEAN{n}_pp": contrast_block(boot, comps[f"MEAN{n}"][0], m, integer=False)["delta_slu_pp"]}
                    for name, m in oc.items()}
        out["norms"][nm] = block
    return out


# ---------------------------------------------------------------------------
# sealed inputs of the real-data side: gold, verdict pools, N1, custody verification


def load_gold(lock, data_root: Path, split: str) -> dict:
    if split not in ("train", "devel"):
        raise ComposerError(f"split {split!r} is not read (the test split is closed)")
    return DRV.load_gold(lock, data_root, split)


#: Verdict sources registered from the command line (``--verdict-run``): key -> the SCR pool spec plus ``aggressive`` (the verdict arm).
#: The built-in keys ``i1`` / ``i2`` (NX R1 iterations 1 / 2 on TRAIN Fold B) are never overwritten.
VERDICT_RUNS: dict = {}
VERDICT_RUN_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
VERDICT_SCORER = "slurp-slu-official-train"


def parse_verdict_run(value: str, *, rows: int) -> tuple:
    """``RUN_ID:ATTEMPT:ARM[:KEY]`` -> ``(key, spec)``: a sealed same-flight node-template column (E1: arms ``lock``, ``aa`` and the
    verdict ARM under ``runs/<run>/<attempt>/supply-variants/``) as a verdict source, on the pool's ``rows``. The key (default: the arm
    id) names the source in the rule keys (``+gate[<key>,<theta>]``) and the report."""
    parts = value.split(":")
    if len(parts) not in (3, 4) or not all(VERDICT_RUN_TOKEN.match(part) for part in parts):
        raise ComposerError(f"--verdict-run {value!r}: expected RUN_ID:ATTEMPT:ARM[:KEY], each made of letters, digits, '.', '_' or '-'")
    run_id, attempt, arm = parts[:3]
    key = parts[3] if len(parts) == 4 else arm
    if arm in ("lock", "aa"):
        raise ComposerError(f"--verdict-run {value!r}: the verdict arm must be a candidate template arm, not {arm!r}")
    if key in R6.FOLD_B or key in VERDICT_RUNS:
        raise ComposerError(f"--verdict-run {value!r}: the verdict key {key!r} is already taken; give a distinct 4th field")
    return key, {"run_id": run_id, "attempt": attempt, "scorer": VERDICT_SCORER, "split": "train", "rows": rows,
                 "arms": ("lock", "aa", arm), "aggressive": arm}


def verdict_run_ids(key: str) -> tuple:
    """(run id, attempt) of a verdict source: its N1 signature is read from that run's ``phases.json``."""
    if key in VERDICT_RUNS:
        return VERDICT_RUNS[key]["run_id"], VERDICT_RUNS[key]["attempt"]
    if key in R6.FOLD_B:
        return R6.FOLD_B[key]["run_id"], R6.FOLD_B[key]["attempt"]
    raise ComposerError(f"verdict source {key!r}: choose one of {sorted(R6.FOLD_B)} or register one with --verdict-run")


def load_verdict_source(data_root: Path, gold_all: dict, key: str, ids=None) -> dict:
    """An NX R1 iteration (``i1`` | ``i2``) or a ``--verdict-run`` column: the lock and A/A twin columns (sealed v3 and registered
    v4g, verified against the sealed per-sample fields by the SCR loader) and the c3 verdict flags (the arm answered no entity
    after v4g)."""
    if key in VERDICT_RUNS:
        agg, spec = VERDICT_RUNS[key]["aggressive"], VERDICT_RUNS[key]
    elif key in R6.FOLD_B:
        agg, spec = R6.FOLD_B[key]["aggressive"], SCR.POOLS[key]
    else:
        raise ComposerError(f"verdict source {key!r}: choose one of {sorted(R6.FOLD_B)} or register one with --verdict-run")
    p = SCR.load_pool(key, spec, data_root, gold_all, ("lock", "aa", agg))
    if ids is not None and list(p["ids"]) != list(ids):
        raise ComposerError(f"verdict source {key}: its rows are not the pool's rows")
    cols = {"v3": {a: Col(p["v3"][a], p["v3_empty"][a]) for a in ("lock", "aa")},
            "v4g": {a: Col(p["v4g"][a], p["v4g_empty"][a]) for a in ("lock", "aa")}}
    return {"key": key, "arm": agg, "ids": list(p["ids"]), "flags": verdict_flags(p["v4g"][agg]), "cols": cols,
            "run": [spec["run_id"], spec["attempt"]], "meta": p["meta"]}


def load_n1(data_root: Path, run_id: str, attempt: str, gold_all: dict, ids) -> tuple:
    """N1 = the entity-free share of the 20 supplied exemplars, from the run's sealed ``phases.json`` through the R6 driver's
    ``row_signals`` (note text parsed in memory and discarded); missing rows take the median (the R6 convention)."""
    directory = data_root / "runs" / run_id / attempt
    slot_types = {str(e.type).lower() for row in gold_all.values() for e in row["entities"]}
    phases = R6.load_phase_signals(directory / f"{run_id}.phases.json", slot_types)
    table_path = data_root / R6.RATE_TABLE
    table = json.loads(table_path.read_text(encoding="utf-8"))
    pool = R6.load_exemplar_annotations(data_root)
    values = [R6.row_signals(s, phases["rows"][s], {}, pool, table)["b_n1_share"] for s in ids]
    filled, missing = R6.fill_missing(values)
    return filled, {"phases_sha256": phases["sha256"], "missing_filled_with_median": missing,
                    "exemplar_pool": [pool["relpath"], pool["sha256"]], "rate_table": [R6.RATE_TABLE, digest(table_path)]}


def verify_custody(data_root: Path, spec: dict, pool: dict, gold: dict, norm_base, delivered_plain_col=None) -> dict:
    """Prove the in-process machinery against the sealed bytes of the pool: (1) the single-sample renderings equal the S3-3
    copies and score to the sealed per-sample official fields at the pool's own scorer; (2) the delivered commit scored
    in-process without projection reproduces the sealed unprojected scorer's fields. Missing artefacts are reported, not
    guessed; a mismatch raises."""
    import numpy as np
    ids = pool["ids"]
    rep: dict = {}
    if spec.get("score_root"):
        root = data_root / spec["score_root"]
        rr = AG.load_rollout_score_root(root, spec["scorer"], pool["n_samples"])
        text_bad = score_bad = 0
        for i in range(pool["n_samples"]):
            ours = {sid: single_text(pool["sealed"][sid], i) for sid in ids}
            text_bad += sum(1 for sid in ids if rr["rendered"][i][sid] != ours[sid])
            col = score_col(ids, ours, gold, norm_base)
            sv = np.array([DRV.sealed_vector(rr["scored"][i][sid]) for sid in ids])
            score_bad += int(np.sum(np.any(np.abs(col.m - sv) > 1e-9, axis=1)))
        if text_bad or score_bad:
            raise ComposerError(f"custody: {text_bad} rendered rows and {score_bad} scored rows differ from the sealed copies")
        rep["single_samples"] = {"rows_checked": len(ids) * pool["n_samples"], "text_mismatches": 0, "score_mismatches": 0,
                                 "scorer": spec["scorer"],
                                 "render_manifest_sha256": digest(root / "render-manifest.json")}
    if spec.get("sealed_scorer") and delivered_plain_col is not None:
        scores = pool["directory"] / f"{spec['run_id']}.scores.json"
        block = json.loads(scores.read_text(encoding="utf-8"))[spec["sealed_scorer"]]
        sealed = {str(r["sample_id"]): r for r in block["per_sample"]}
        sv = np.array([DRV.sealed_vector(sealed[sid]) for sid in ids])
        bad = int(np.sum(np.any(np.abs(delivered_plain_col.m - sv) > 1e-9, axis=1)))
        if bad:
            raise ComposerError(f"custody: the delivered commit's in-process score differs on {bad} rows")
        rep["delivered_commit"] = {"rows_checked": len(ids), "score_mismatches": 0, "sealed_scorer": spec["sealed_scorer"],
                                   "scores_sha256": digest(scores),
                                   "sealed_unprojected_slu_f1_pp": round(
                                       100.0 * float(block["aggregate"]["official"]["slu_f1"]), 4)}
    return rep


def delivered_texts(pool: dict) -> dict:
    return {sid: (pool["sealed"][sid].get("delivered_text") or "") for sid in pool["ids"]}


def make_boot(ids, gold, cluster: str):
    cluster_of = {sid: (sid if cluster == "row" else gold[sid]["utterance_id"]) for sid in ids}
    return DRV.Bootstrap(list(ids), cluster_of, draws=BOOT_DRAWS, seed=BOOT_SEED)


def read_pool(args, spec: dict, *, norm_names, ns, ss, forms, thetas, verdict_keys, signature, cluster, detail, registered,
              lock, data_root: Path, pool_root: Path | None = None) -> dict:
    """One real-data read: load the pool, verify the custody, load the verdict sources and N1, evaluate."""
    pool = load_sample_pool(pool_root or data_root, spec)
    ids = pool["ids"]
    gold_all = load_gold(lock, data_root, spec["split"])
    if any(s not in gold_all for s in ids):
        raise ComposerError("pool rows absent from the governed gold")
    gold = {s: gold_all[s] for s in ids}
    normalisers = {nm: make_normaliser(nm) for nm in dict.fromkeys(list(norm_names) + ["none", spec["base_norm"]])}
    delivered = delivered_texts(pool)
    custody = verify_custody(data_root, spec, pool, gold, normalisers[spec["base_norm"]],
                             score_col(ids, delivered, gold, normalisers["none"]) if spec.get("sealed_scorer") else None)
    verdicts, n1, n1_meta = {}, None, None
    for vk in verdict_keys:
        verdicts[vk] = load_verdict_source(data_root, load_gold(lock, data_root, "train"), vk, ids)
    if verdicts:
        sig = signature or next(iter(verdicts))
        gold_train = load_gold(lock, data_root, "train")
        run_id, attempt = verdict_run_ids(sig)
        n1, n1_meta = load_n1(data_root, run_id, attempt, gold_train, ids)
        n1_meta["signature_run"] = [run_id, attempt]
    boot = make_boot(ids, gold, cluster)
    report = evaluate_pool(ids=ids, gold=gold, sealed=pool["sealed"], n_samples=pool["n_samples"],
                           norm_names=list(norm_names), ns=ns, ss=ss, forms=forms, thetas=thetas, similarity=SIMILARITY,
                           boot=boot, verdicts=verdicts, n1=n1, delivered=delivered, detail=detail,
                           registered=registered, normalisers=normalisers)
    report["inputs"] = {"run_id": spec["run_id"], "attempt": spec["attempt"], "split": spec["split"], "outputs": pool["outputs"],
                        "label": spec.get("label"), "custody": custody, "n1": n1_meta,
                        "verdict_sources": {k: {"arm": v["arm"], "run": v["run"]} for k, v in verdicts.items()}}
    report["bootstrap"] = {"unit": cluster, "draws": BOOT_DRAWS, "seed": BOOT_SEED, "clusters": boot.clusters}
    return report


# ---------------------------------------------------------------------------
# machinery controls


#: (name, pool, norms, n, s, form, comparator, norm scored, expected delta pp, expected CI95, bootstrap cluster)
CONTROLS = (
    ("ROLL-1 R3 support 3-of-5 (aggregation read, row cluster)", "roll1", "v3", 5, 3, ("medoid", "base"), "MEAN5", 1.40,
     (0.55, 2.29), "row"),
    ("ROLL-1 R3 support 3-of-5 (v4 note, utterance cluster)", "roll1", "v3", 5, 3, ("medoid", "base"), "MEAN5", 1.40,
     (0.52, 2.28), "utterance"),
    ("ROLL-1 R1 medoid (row cluster)", "roll1", "v3", 5, 1, ("medoid", "base"), "MEAN5", 0.03, (-0.63, 0.71), "row"),
    ("ROLL-3 R3 support 2-of-3 over single (v3)", "roll3", "v3", 3, 2, ("medoid", "base"), "MEAN3", 1.46, (0.83, 2.08),
     "utterance"),
    ("ROLL-3 R3 support 3-of-5 over single (v3)", "roll3", "v3", 5, 3, ("medoid", "base"), "MEAN5", 2.06, (1.27, 2.88),
     "utterance"),
)
#: the v4 ("+v4") controls: filter+v4 vs single+v4 (the registered v4 normaliser)
CONTROLS_V4 = (
    ("ROLL-3 support 2-of-3 + v4 vs single + v4", "roll3", "v4", 3, 2, ("medoid", "base"), "MEAN3", 0.84, (0.19, 1.49),
     "utterance"),
    ("ROLL-3 support 3-of-5 + v4 vs single + v4", "roll3", "v4", 5, 3, ("medoid", "base"), "MEAN5", 1.11, (0.33, 1.91),
     "utterance"),
)
CONTROL_TOL = 0.0051
R6_GATE_CONTROLS = {"i1": {"delta_slu_pp": 0.75, "false_fills": (91, 64), "nonempty_exact_lost": 3},
                    "i2": {"delta_slu_pp": 0.98, "false_fills": (93, 60), "nonempty_exact_lost": 3}}


def control_matches(got_delta, got_ci, want_delta, want_ci) -> bool:
    return (abs(got_delta - want_delta) <= CONTROL_TOL and abs(got_ci[0] - want_ci[0]) <= CONTROL_TOL
            and abs(got_ci[1] - want_ci[1]) <= CONTROL_TOL)




def run_controls(lock, data_root: Path) -> dict:
    """Reproduce the documented numbers through this driver's machinery; the verdict says what matched."""
    results: list = []
    groups: dict = {}
    for row in CONTROLS + CONTROLS_V4:
        groups.setdefault((row[1], row[3], row[9]), []).append(row)
    loaded: dict = {}
    for (pool_key, n, cluster), rows in groups.items():
        spec = POOLS[pool_key]
        if pool_key not in loaded:
            pool = load_sample_pool(data_root, spec)
            gold_all = load_gold(lock, data_root, spec["split"])
            loaded[pool_key] = (pool, {sid: gold_all[sid] for sid in pool["ids"]})
        pool, gold = loaded[pool_key]
        ids = pool["ids"]
        norm_names = ["v3"] + (["v4"] if any(r[2] == "v4" for r in rows) else [])
        forms = sorted({r[5] for r in rows})
        ss = sorted({r[4] for r in rows if r[4] > 1})
        rep = evaluate_pool(ids=ids, gold=gold, sealed=pool["sealed"], n_samples=pool["n_samples"], norm_names=norm_names,
                            ns=[n], ss=ss, forms=forms, thetas=THETAS, similarity=SIMILARITY,
                            boot=make_boot(ids, gold, cluster), detail=False, registered=False, extras=False)
        for (name, _p, nm, _n, s, form, comp, want, want_ci, _c) in rows:
            v = rep["norms"][nm]["variants"][rule_key(n, s, *form)]["vs"][comp]
            results.append({"control": name, "pool": pool_key, "normaliser": nm, "n": n, "s": s, "cluster": cluster,
                            "comparator": comp, "pooled_slu_f1_pp": v["slu_f1_pp"], "got_delta_pp": v["delta_slu_pp"],
                            "got_ci95": v["ci95_slu_pp"], "documented_delta_pp": want, "documented_ci95": list(want_ci),
                            "reproduced": bool(control_matches(v["delta_slu_pp"], v["ci95_slu_pp"], want, want_ci))})
    # the R6 gate on R1 i1 / i2 (lock v4g, c3verdict x N1 >= 0.2)
    gold_train = load_gold(lock, data_root, "train")
    ids = gold = boot = gold_empty = None
    for key, ref in R6_GATE_CONTROLS.items():
        v = load_verdict_source(data_root, gold_train, key, ids)
        if ids is None:
            ids = v["ids"]
            gold = {s: gold_train[s] for s in ids}
            boot = make_boot(ids, gold, "utterance")
            gold_empty = [not gold[s]["entities"] for s in ids]
        n1, n1_meta = load_n1(data_root, R6.FOLD_B[key]["run_id"], R6.FOLD_B[key]["attempt"], gold_train, ids)
        lock_col = v["cols"]["v4g"]["lock"]
        fired = gate_fired(v["flags"], n1, GATE_THETA)
        new = apply_gate(lock_col, fired)
        mine = contrast_block(boot, lock_col.m, new.m, gold_empty=gold_empty)
        r6 = R6.gate_metrics(lock_col.m, lock_col.e, fired, gold_empty, boot)
        same_as_r6 = (abs(mine["delta_slu_pp"] - r6["delta_slu_pp"]) < 1e-9 and mine["ci95_slu_pp"] == r6["ci95_slu_pp"]
                      and mine["false_fill_rows_new"] == r6["false_fill_rows_new"]
                      and mine["nonempty_exact_lost"] == r6["nonempty_exact_lost"])
        ok = (abs(mine["delta_slu_pp"] - ref["delta_slu_pp"]) <= CONTROL_TOL
              and (mine["false_fill_rows_comparator"], mine["false_fill_rows_new"]) == ref["false_fills"]
              and mine["nonempty_exact_lost"] == ref["nonempty_exact_lost"] and mine["intent_rows_moved"] == 0
              and same_as_r6)
        results.append({"control": f"R6 gate c3verdict x N1 >= {GATE_THETA} on R1 {key} (lock, v4g)",
                        "fired": int(sum(fired)), "got_delta_pp": mine["delta_slu_pp"], "got_ci95": mine["ci95_slu_pp"],
                        "documented_delta_pp": ref["delta_slu_pp"],
                        "false_fill_rows_comparator_to_new": [mine["false_fill_rows_comparator"],
                                                              mine["false_fill_rows_new"]],
                        "documented_false_fills": list(ref["false_fills"]),
                        "nonempty_exact_lost": mine["nonempty_exact_lost"], "intent_rows_moved": mine["intent_rows_moved"],
                        "identical_to_r6_gate_metrics": bool(same_as_r6),
                        "n1_rows_filled_with_median": n1_meta["missing_filled_with_median"], "reproduced": bool(ok)})
    return {"mode": "controls", "all_reproduced": all(r["reproduced"] for r in results), "controls": results}


# ---------------------------------------------------------------------------
# rendering, output, CLI


def _ci(c) -> str:
    return "--" if not c else f"[{c[0]:+.2f}, {c[1]:+.2f}]"


def _vs_cells(v: dict) -> list:
    return [f"{v['delta_slu_pp']:+.2f} {_ci(v['ci95_slu_pp'])}"]


def md(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def render(report: dict) -> str:
    """Markdown tables: counts, rates, pp, CIs and labels only."""
    if report.get("mode") == "controls":
        rows = []
        for r in report["controls"]:
            rows.append([r["control"], f"{r['got_delta_pp']:+.2f} {_ci(r['got_ci95'])}",
                         f"{r['documented_delta_pp']:+.2f} {_ci(r.get('documented_ci95'))}", "yes" if r["reproduced"] else "NO"])
        return (f"# {report['read_id']}: machinery controls\n\nDESCRIPTIVE; zero contacts.\n\n"
                + md(["control", "reproduced", "documented", "match"], rows) + "\n")
    out = [f"# {report['read_id']}", "",
           f"DESCRIPTIVE; development numbers; zero contacts. Pool: {report['inputs'].get('label')}; rows {report['rows']} "
           f"({report['empty_gold_rows']} empty-gold); samples {report['samples_in_pool']}; bootstrap "
           f"{report['bootstrap']['unit']} clusters ({report['bootstrap']['clusters']}), {report['bootstrap']['draws']} draws, "
           f"seed {report['bootstrap']['seed']}.", ""]
    for nm, block in report["norms"].items():
        out += [f"## Normaliser {nm}", "", "Comparators (pooled official SLU-F1 pp, intent pp):", "",
                md(["column", "SLU-F1", "intent"], [[k, v["slu_f1_pp"], v["intent_pp"]] for k, v in block["comparators"].items()]),
                ""]
        comp_names = list(dict.fromkeys(c for r in block["variants"].values() for c in r["vs"]))
        header = ["variant", "SLU-F1", "intent"] + [f"vs {c}" for c in comp_names] + ["FF removed", "NE lost/gained",
                                                                                      "intent rows", "exch. pred."]
        for title, pick in (("Filter-only rules", lambda r: "gate" not in r and r["vs"]),
                            ("Gated rules (verdict x N1 >= theta)", lambda r: "gate" in r and r["vs"])):
            rows = []
            for key, r in block["variants"].items():
                if not pick(r):
                    continue
                cells = [key, r["pooled_slu_f1_pp"], r["pooled_intent_pp"]]
                for c in comp_names:
                    v = r["vs"].get(c)
                    cells.append(_vs_cells(v)[0] if v else "--")
                base = r["vs"].get("S0", {})
                cells += [base.get("false_fills_removed_net", "--"),
                          f"{base.get('nonempty_exact_lost', '--')}/{base.get('nonempty_exact_gained', '--')}",
                          base.get("intent_rows_moved", "--"),
                          base.get("exchange", {}).get("predicted_pp_false_fill_x0.033_plus_nonempty_exact_x0.070", "--")]
                rows.append(cells)
            if rows:
                out += [f"### {title}", "", md(header, rows), ""]
        if block["crossfit"]:
            rows = [[k, json.dumps(v["chosen"]), *[_vs_cells(v["vs"][c])[0] if c in v["vs"] else "--" for c in comp_names]]
                    for k, v in block["crossfit"].items()]
            out += ["### Cross-fitted thresholds (utterance-hash halves)", "",
                    md(["rule", "chosen per half", *[f"vs {c}" for c in comp_names]], rows), ""]
        headline = {k: r for k, r in block["variants"].items() if "strata_vs_S0" in r and "-first-first" in k
                    and "-s1-" not in k}
        if headline:
            rows = []
            for k, r in headline.items():
                st = r["strata_vs_S0"]
                eq, ev = st["equal_stratum"], st["empty_vs_non_empty"]
                rows.append([k, f"{eq['natural_mixture_delta_slu_pp']:+.2f}", f"{eq['delta_slu_pp']:+.2f} {_ci(eq['ci95'])}",
                             f"{ev['empty_gold']['contribution_to_pooled_delta_pp']:+.2f} {_ci(ev['empty_gold']['ci95'])} "
                             f"({ev['empty_gold']['changed_rows']} rows)",
                             f"{ev['non_empty_gold']['contribution_to_pooled_delta_pp']:+.2f} "
                             f"{_ci(ev['non_empty_gold']['ci95'])} ({ev['non_empty_gold']['changed_rows']} rows)"])
            out += ["### Strata vs S0 (the empty / non-empty split is the contribution of each gold half to the pooled "
                    "delta)", "",
                    md(["variant", "natural", "equal-scenario [CI95]", "empty-gold rows", "non-empty-gold rows"], rows), ""]
            scen = sorted(next(iter(headline.values()))["strata_vs_S0"]["per_scenario"])
            rows = [[s, next(iter(headline.values()))["strata_vs_S0"]["per_scenario"][s]["rows"],
                     *[f"{r['strata_vs_S0']['per_scenario'][s]['delta_slu_pp']:+.2f}" for r in headline.values()]]
                    for s in scen]
            out += ["Per-scenario delta (pp, within-scenario pooled; CIs in report.json):", "",
                    md(["scenario", "rows", *headline], rows), ""]
        if block["oracles"]:
            rows = [[f"{n}:{name}", o["slu_f1_pp"], o["delta_vs_S0_pp"]] for n, d in block["oracles"].items()
                    for name, o in d.items()]
            out += ["### Per-row oracle ceilings (see the gold; upper bounds, never rules)", "",
                    md(["oracle", "SLU-F1", "delta vs S0"], rows), ""]
    return "\n".join(out) + "\n"


def strip_time(text: str) -> str:
    import re
    return re.sub(r'"generated_at": "[^"]*"', '"generated_at": ""', text)


def write_once(data_root: Path, label: str, report: dict) -> Path:
    out_dir = data_root / "analysis" / f"{READ_ID_PREFIX}-{label}"
    if out_dir.exists():
        raise ComposerError(f"{out_dir} exists: outputs are write-once; pick a new --label or use --no-write")
    out_dir.mkdir(parents=True)
    text = json.dumps(report, indent=1, sort_keys=True, default=str) + "\n"
    (out_dir / "report.json").write_text(text, encoding="utf-8", newline="\n")
    (out_dir / "report.md").write_text(render(report), encoding="utf-8", newline="\n")
    return out_dir


def parse_csv(value: str, cast=str) -> list:
    return [cast(x) for x in value.split(",") if x.strip()]


def build_spec(args) -> dict:
    if args.pool:
        if args.pool not in POOLS:
            raise ComposerError(f"unknown pool {args.pool!r}; named pools {sorted(POOLS)}")
        return dict(POOLS[args.pool])
    if not (args.run_id and args.attempt and args.split):
        raise ComposerError("a pool needs --pool or --run-id, --attempt and --split")
    return {"run_id": args.run_id, "attempt": args.attempt, "split": args.split, "rows": args.rows,
            "score_root": args.score_root, "scorer": args.scorer, "sealed_scorer": args.sealed_scorer,
            "base_norm": args.base_norm, "label": args.run_id}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=("controls", "read"), required=True)
    parser.add_argument("--pool", default=None, help=f"named sealed pool: {', '.join(sorted(POOLS))}")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--attempt", default=None)
    parser.add_argument("--split", default=None, choices=("train", "devel"))
    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--score-root", default=None, help="analysis-root-relative S3-3 score root of the pool (custody proof)")
    parser.add_argument("--scorer", default=None, help="scorer id of the S3-3 score root")
    parser.add_argument("--sealed-scorer", default=None, help="scorer id of the run's own sealed scores.json")
    parser.add_argument("--base-norm", default="v3", choices=("none", "v3"))
    parser.add_argument("--n", default=None, help="comma list of sample counts n (default: all samples)")
    parser.add_argument("--s", default="2,3", help="comma list of support thresholds")
    parser.add_argument("--thetas", default=",".join(str(t) for t in THETAS))
    parser.add_argument("--verdict", default="", help="comma list of NX R1 iterations as verdict sources: i1,i2")
    parser.add_argument("--verdict-run", action="append", default=[], metavar="RUN_ID:ATTEMPT:ARM[:KEY]",
                        help="a sealed same-flight Solver template column (arms lock, aa and ARM under runs/<RUN_ID>/<ATTEMPT>/"
                             "supply-variants/) as a verdict source on the pool's rows, e.g. the VER-1c Fold A c3 column; repeatable; "
                             "combines with --verdict (the built-in i1,i2 keep working)")
    parser.add_argument("--signature", default=None,
                        help="verdict source whose run's phases.json carries N1: i1 | i2 | a --verdict-run key (default: first verdict)")
    parser.add_argument("--cluster", default="utterance", choices=("utterance", "row"))
    parser.add_argument("--no-detail", action="store_true")
    parser.add_argument("--no-registered", action="store_true")
    parser.add_argument("--label", default=None)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--pool-root", default=None, help="data root that holds the sample-pool run (default: --data-root)")
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.data.lock import load_lock
    data_root, lock = Path(args.data_root), load_lock(Path(args.lock))
    if args.mode == "controls":
        report = run_controls(lock, data_root)
        label = args.label or "CONTROLS"
    else:
        spec = build_spec(args)
        if not args.label:
            raise ComposerError("--label is required for a read")
        label = args.label
        pool_peek = load_sample_pool(Path(args.pool_root) if args.pool_root else data_root, spec)
        n_samples = pool_peek["n_samples"]
        ns = parse_csv(args.n, int) if args.n else [n_samples]
        ss = parse_csv(args.s, int)
        norm_names = [spec["base_norm"], "v4g"] if spec["base_norm"] != "v4g" else ["v4g"]
        verdict_keys = parse_csv(args.verdict)
        for value in args.verdict_run:
            key, run_spec = parse_verdict_run(value, rows=spec["rows"])
            VERDICT_RUNS[key] = run_spec
            verdict_keys.append(key)
        report = read_pool(args, spec, norm_names=norm_names, ns=ns, ss=ss, forms=list(FORMS),
                           thetas=parse_csv(args.thetas, float), verdict_keys=verdict_keys,
                           signature=args.signature, cluster=args.cluster, detail=not args.no_detail,
                           registered=not args.no_registered, lock=lock, data_root=data_root,
                           pool_root=Path(args.pool_root) if args.pool_root else None)
        report["mode"] = "read"
    report.update({"read_id": f"{READ_ID_PREFIX}-{label}", "recipe": RECIPE, "schema": SCHEMA, "status": "DESCRIPTIVE",
                   "normaliser_ids": NORM_IDS, "contacts": dict(CONTACTS),
                   "exchange_rates_pp_per_row": {"false_fill_removed": RATE_FALSE_FILL_REMOVED,
                                                 "nonempty_exact": RATE_NONEMPTY_EXACT, "raw_exact": RATE_RAW_EXACT},
                   "driver_sha256": digest(Path(__file__)),
                   "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    text = json.dumps(report, indent=1, sort_keys=True, default=str) + "\n"
    content = hashlib.sha256(strip_time(text).encode("utf-8")).hexdigest()
    if args.no_write:
        print(render(report))
        print(json.dumps({"written": None, "content_sha256_without_time": content}))
        return 0 if report.get("all_reproduced", True) else 2
    out_dir = write_once(data_root, label, report)
    print(render(report))
    print(json.dumps({"written": str(out_dir), "report_sha256": digest(out_dir / "report.json"),
                      "content_sha256_without_time": content}))
    return 0 if report.get("all_reproduced", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
