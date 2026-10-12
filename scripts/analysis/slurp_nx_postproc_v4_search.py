#!/usr/bin/env python3
"""R0.4 / E4: the deterministic post-processing v4 search over sealed SLURP pools (zero GPU).

NX node-extreme programme v1 (``docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md``,
sections B W3, C1 E4, C2 R0.4, F2). The base graph of NX is review-off, so the "review" function
moves to deterministic verification at delivery. This driver searches that verification offline,
over sealed bytes, at the offline-read floor of about 0.67 pp
(``docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`` section 2c).

PART A -- single-sample rules over the delivered answer of a temperature-0 run. The baseline is the
sealed delivered column, which already carries normaliser v3 (``saea-deliver-normalise-v3``). Every
candidate rule is deterministic and computable from the delivered answer, the row's sealed supplied
knowledge and TRAIN statistics only. The TRAIN statistics come from ONE pinned pool, the R5 pool
``size-pool-annotated-exemplars-minus-r01`` (TRAIN minus Fold A, Fold B, R01 and R01C, the pool the
registered scope-rule table was built from); its disjointness from Fold A and R01C is re-proved at
run time. Rules, in their fixed application order (a combination applies its members in this order):

  fx-article        strip a leading determiner (the/a/an/my/this/next/at/in/on/to/for/your/our) from a
                    filler of slot type t when the TRAIN pool shows that SLURP annotation excludes it:
                    among pool fillers of type t whose utterance offers the word immediately before the
                    span, the span includes it in < 10 % of >= 10 opportunities
  fx-oclock         strip a trailing "o'clock" from a time filler under the same conditional statistic
  fx-month-ordinal  month + cardinal day (1..31) -> month + ordinal, when the TRAIN pool writes the
                    ordinal in > 50 % of >= 20 month + day-number date fillers
  scope             the registered ``saea-deliver-scope-rule-v1`` (pinned table, its own thresholds)
  ti0 / ti1         type-by-intent support: drop an entity whose slot type co-occurs with the delivered
                    intent in 0 TRAIN pool exemplars (ti0) or in < 1 % of that intent's exemplars (ti1);
                    an intent absent from the pool is left alone
  vs-type / vs-any  value-in-supply support: drop an entity whose (type, folded value) is not printed in
                    the row's supplied exemplars (vs-type), or whose folded value is printed nowhere in
                    the row's supply (exemplars under any type, or a supplied slot-contract card)
  ee5 / ee10        explicit-empty: drop every entity on a row whose delivered intent carries entities
                    in < 5 % (ee5) / < 10 % (ee10) of its TRAIN pool exemplars; an empty delivered entity
                    list is never filled (owner decision 199)

``--select`` reads every rule alone and every combination of the grid (fx toggles x scope x ti x vs x
ee) on cell A2 (``SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1``, DEV-2000-ADDED, 1,000 rows). The
selection rule is fixed here, before any number is read: the combination with the highest A2 pooled
SLU-F1 point delta (ties -> fewer rules), then pruned of passengers (a member whose removal does not
lower the point is removed, repeatedly). ``--confirm --rules a,b,c`` reads that ONE ordered rule list
once on TRAIN Fold A (``SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1``, 1,080 rows) and refuses to run twice.
The lock candidate is the Fold-A CI95 lower bound > 0.

PART B -- multi-sample self-consistency (the entity support filter of
``scripts/analysis/slurp_sample_aggregation_offline_read.py``, R3: the R1 medoid of the k samples,
minus its entities supported by fewer than s of the k samples) over the sealed five-sample pools
ROLL-1 (R01C, 625 rows) and ROLL-3 (DEV-2000-ADDED, 1,000 rows; PLAN policy, not COMP-1b -- the two
pools are never pooled), at s in {2,3} of k = 3 (samples 0..2) and s in {2,3,4} of k = 5, alone and
followed by the Part-A rule list (``--rules``). The reference is the precedent's R0-mean-single: the
mean count matrix of the k single-sample arms (each sample projected by v3, as the sealed per-sample
scorer did).

Scoring. All numbers are the official SLURP pooled SLU-F1 (micro F1 over the word- and char-distance
TP/FP/FN of ``reproduction.slurp_scoring.score_slu``, the port whose official identity check every
sealed scoring passed) and the joint intent exact. The in-process arithmetic is PROVED, not assumed:
every row of every unedited column reproduces its sealed per-sample official fields exactly, or the
read stops. ``--score-copy`` additionally scores the selected column once through the registered
scorer on a derived copy under the analysis root (the ``score_copy`` idiom of the aggregation read).

Estimator. Paired whole-utterance cluster bootstrap (cluster = SLURP utterance id from the governed
loader; DEV-2000-ADDED carries 87 utterances with two recordings), 10,000 draws, seed 20260915, numpy
``default_rng`` -- the aggregation read's estimator with the cluster lifted from row to utterance;
percentile CI95. ``--row-cluster`` reproduces the precedent's row-cluster form as a control.

Gold discipline: gold enters only offline, on the scoring side, through the governed loader
``data.slurp.load_slurp_split`` (``train`` / ``devel``); the test split is refused. No utterance text,
transcript, gold value, filler or model output text is printed or persisted in ``report.json``: rule
ids, slot TYPE names, scenario names, counts, pp and hashes only. Derived copies written by
``--score-copy`` (answer text, needed by the scorer) live under the analysis root, never the repository.
Zero model, server, tokenizer, encoder, embedder, network and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_search.py --select
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_search.py --confirm \\
        --rules fx-article,scope,ee5 [--score-copy]
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_search.py --part B \\
        --pool roll1 --rules fx-article,scope,ee5
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import itertools
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-NX-POSTPROC-V4-SEARCH-V1"
SCHEMA = "saea-slurp-nx-postproc-v4-search-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
BOOT_DRAWS = 10_000
BOOT_SEED = 20260915
FLOOR_PP = 0.67

#: The TRAIN statistics pool (R5: TRAIN minus Fold A, Fold B, R01, R01C).
STATS_POOL = ("knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
              "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63")
FOLD_A_ROSTER = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
R01C_ROSTER = "docs/receipts/rosters/slurp-stage3-construction-r01c.json"

POOLS: dict[str, dict[str, Any]] = {
    "a2": {"run_id": "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1",
           "attempt": "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1",
           "scorer": "slurp-slu-official", "split": "devel", "rows": 1000},
    "fold-a": {"run_id": "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1",
               "attempt": "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1",
               "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080},
    "roll1": {"run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
              "attempt": "attempt-slurp-native-stage3-rollout-r01-generation-v1",
              "score_root": "analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1",
              "scorer": "slurp-slu-official-projected-v3-train", "split": "train", "rows": 625,
              "policy": "v2.0 PLAN rollout (ROLL-1), five temperature-0.7 Solver samples",
              "published_r3_3_of_5": {"slu_f1_pp": 59.28, "delta_pp": 1.40}},
    "roll3": {"run_id": "SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1",
              "attempt": "attempt-slurp-native-stage3-roll-3-dev2000-added-v1-generation",
              "score_root": "analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1",
              "scorer": "slurp-slu-official-projected-v3", "split": "devel", "rows": 1000,
              "policy": "PLAN policy (ROLL-3), five temperature-0.7 Solver samples -- NOT COMP-1b"},
}

RULE_ORDER = ("fx-article", "fx-oclock", "fx-month-ordinal", "scope", "ti0", "ti1", "vs-type", "vs-any",
              "ee5", "ee10")
#: Mutually exclusive families (one member at most per combination).
EXCLUSIVE = ({"ti0", "ti1"}, {"vs-type", "vs-any"}, {"ee5", "ee10"})
DETERMINERS = ("the", "a", "an", "my", "this", "next", "at", "in", "on", "to", "for", "your", "our")
ARTICLE_MAX_INCLUDED_SHARE = 0.10
ARTICLE_MIN_OPPORTUNITIES = 10
OCLOCK_MIN_OPPORTUNITIES = 5
ORDINAL_MIN_SHARE = 0.5
ORDINAL_MIN_N = 20
TI1_SHARE = 0.01
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december")
CARD_DAY = {w: i + 1 for i, w in enumerate(
    "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())}
CARD_DAY.update({"thirty": 30})
ORD_WORD = {i + 1: w for i, w in enumerate(
    "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth "
    "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth".split())}
ORD_WORD[30] = "thirtieth"
ORD_UNITS = {i: ORD_WORD[i] for i in range(1, 10)}
ORD_SET = set(ORD_WORD.values())
COUNT_FIELDS = ("slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn", "slu_f1_char_tp", "slu_f1_char_fp",
                "slu_f1_char_fn", "slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn")


class SearchError(RuntimeError):
    """A sealed input is missing, drifted, or does not reproduce."""


# ---------------------------------------------------------------------------
# helpers


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def parse_rules(value: str | None) -> list[str]:
    if not value:
        return []
    rules = [r.strip() for r in value.split(",") if r.strip()]
    unknown = [r for r in rules if r not in RULE_ORDER]
    if unknown:
        raise SystemExit(f"unknown rule ids: {unknown}; known: {list(RULE_ORDER)}")
    for family in EXCLUSIVE:
        if len(family & set(rules)) > 1:
            raise SystemExit(f"rules {sorted(family & set(rules))} are mutually exclusive")
    return sorted(set(rules), key=RULE_ORDER.index)


# ---------------------------------------------------------------------------
# TRAIN statistics (the R5 pool only)


class TrainStats:
    """Every TRAIN-derived quantity a rule consults, from the pinned R5 pool."""

    def __init__(self, pool_values: Mapping[str, Mapping[str, Any]]):
        self.intent_n: Counter = Counter()
        self.intent_with_entities: Counter = Counter()
        self.intent_type: dict[str, Counter] = defaultdict(Counter)
        included: Counter = Counter()
        excluded: Counter = Counter()
        oclock_in = oclock_out = 0
        month_card = month_ord = 0
        for value in pool_values.values():
            intent = value["intent"]
            self.intent_n[intent] += 1
            self.intent_with_entities[intent] += int(bool(value["fillers"]))
            words = value["utterance"].split()
            for slot_type, fillers in value["fillers"].items():
                self.intent_type[intent][slot_type] += 1
                for filler in fillers:
                    tokens = filler.split()
                    if not tokens:
                        continue
                    for det in DETERMINERS:
                        if tokens[0] == det and len(tokens) > 1:
                            included[(slot_type, det)] += 1
                        elif _span_preceded_by(words, tokens, det):
                            excluded[(slot_type, det)] += 1
                    if slot_type == "time":
                        if tokens[-1] in ("o'clock", "oclock"):
                            oclock_in += 1
                        elif _span_followed_by(words, tokens, ("o'clock", "oclock")):
                            oclock_out += 1
                    if slot_type == "date":
                        for i in range(len(tokens) - 1):
                            if tokens[i] in MONTHS:
                                if tokens[i + 1] in CARD_DAY:
                                    month_card += 1
                                elif tokens[i + 1] in ORD_SET:
                                    month_ord += 1
        self.article_strip: set = set()
        self.article_table: dict[str, dict[str, Any]] = {}
        for key in sorted(set(included) | set(excluded)):
            n = included[key] + excluded[key]
            share = included[key] / n if n else None
            strip = n >= ARTICLE_MIN_OPPORTUNITIES and share is not None and share < ARTICLE_MAX_INCLUDED_SHARE
            if strip:
                self.article_strip.add(key)
            self.article_table[f"{key[0]}|{key[1]}"] = {"included": included[key], "excluded": excluded[key],
                                                        "strip": strip}
        n_oclock = oclock_in + oclock_out
        self.oclock = {"included": oclock_in, "excluded": oclock_out,
                       "strip": n_oclock >= OCLOCK_MIN_OPPORTUNITIES and oclock_in / max(n_oclock, 1)
                       < ARTICLE_MAX_INCLUDED_SHARE}
        n_month = month_card + month_ord
        self.month_ordinal = {"cardinal": month_card, "ordinal": month_ord,
                              "convert": n_month >= ORDINAL_MIN_N and month_ord / max(n_month, 1) > ORDINAL_MIN_SHARE}

    def type_share(self, intent: str, slot_type: str) -> float | None:
        n = self.intent_n.get(intent, 0)
        return None if n == 0 else self.intent_type[intent][slot_type] / n

    def entity_rate(self, intent: str) -> float | None:
        n = self.intent_n.get(intent, 0)
        return None if n == 0 else self.intent_with_entities[intent] / n

    def summary(self) -> dict:
        return {
            "pool_exemplars": sum(self.intent_n.values()), "intents": len(self.intent_n),
            "intent_type_bindings": sum(len(v) for v in self.intent_type.values()),
            "intents_entity_rate_below_5pct": sum(1 for i in self.intent_n if self.entity_rate(i) < 0.05),
            "intents_entity_rate_below_10pct": sum(1 for i in self.intent_n if self.entity_rate(i) < 0.10),
            "article_strip_pairs": sorted(f"{t}|{d}" for t, d in self.article_strip),
            "article_table": self.article_table, "oclock": self.oclock, "month_ordinal": self.month_ordinal,
        }


def _span_preceded_by(words: list, tokens: list, det: str) -> bool:
    n = len(tokens)
    for i in range(1, len(words) - n + 1):
        if words[i:i + n] == tokens and words[i - 1] == det:
            return True
    return False


def _span_followed_by(words: list, tokens: list, nxt: tuple) -> bool:
    n = len(tokens)
    for i in range(0, len(words) - n):
        if words[i:i + n] == tokens and words[i + n] in nxt:
            return True
    return False


# ---------------------------------------------------------------------------
# the rules (pure; entities are (original index, SlotEntity) pairs; labels never change)


class RowContext:
    __slots__ = ("intent", "printed", "printed_values", "cards")

    def __init__(self, intent: str | None, printed: set | None, cards: list | None):
        self.intent = intent
        self.printed = printed
        self.printed_values = None if printed is None else {v for _t, v in printed}
        self.cards = cards


def _fx_article(entities, ctx, stats, env):
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import fold
    SE = env["SlotEntity"]
    out = []
    for index, entity in entities:
        tokens = entity.filler.split()
        if len(tokens) > 1 and (entity.type, fold(tokens[0])) in stats.article_strip:
            entity = SE(type=entity.type, filler=" ".join(tokens[1:]))
        out.append((index, entity))
    return out


def _fx_oclock(entities, ctx, stats, env):
    if not stats.oclock["strip"]:
        return entities
    SE = env["SlotEntity"]
    out = []
    for index, entity in entities:
        tokens = entity.filler.split()
        if entity.type == "time" and len(tokens) > 1 and tokens[-1].lower() in ("o'clock", "oclock"):
            entity = SE(type=entity.type, filler=" ".join(tokens[:-1]))
        out.append((index, entity))
    return out


def _fx_month_ordinal(entities, ctx, stats, env):
    if not stats.month_ordinal["convert"]:
        return entities
    SE = env["SlotEntity"]
    out = []
    for index, entity in entities:
        if entity.type == "date":
            tokens = entity.filler.split()
            changed = False
            for i in range(len(tokens) - 1):
                if tokens[i].lower() in MONTHS:
                    nxt = tokens[i + 1].lower()
                    # "twenty one" -> "twenty first"; a bare day word -> its ordinal
                    if nxt == "twenty" and i + 2 < len(tokens) and tokens[i + 2].lower() in CARD_DAY \
                            and CARD_DAY[tokens[i + 2].lower()] < 10:
                        tokens[i + 2] = ORD_UNITS[CARD_DAY[tokens[i + 2].lower()]]
                        changed = True
                    elif nxt == "thirty" and i + 2 < len(tokens) and tokens[i + 2].lower() == "one":
                        tokens[i + 2] = "first"
                        changed = True
                    elif nxt in CARD_DAY and not (i + 2 < len(tokens) and tokens[i + 2].lower() in CARD_DAY):
                        tokens[i + 1] = ORD_WORD[CARD_DAY[nxt]]
                        changed = True
            if changed:
                entity = SE(type=entity.type, filler=" ".join(tokens))
        out.append((index, entity))
    return out


def _scope(entities, ctx, stats, env):
    from speech_aware_evidence_acquisition.rails.delivery_normalisers import scope_rule_drops
    drops = set(scope_rule_drops([e.filler for _i, e in entities], env["scope_table"]))
    return [pair for k, pair in enumerate(entities) if k not in drops]


def _ti(threshold_zero: bool):
    def rule(entities, ctx, stats, env):
        if ctx.intent is None or stats.intent_n.get(ctx.intent, 0) == 0:
            return entities
        out = []
        for index, entity in entities:
            share = stats.type_share(ctx.intent, entity.type)
            drop = (share == 0.0) if threshold_zero else (share < TI1_SHARE)
            if not drop:
                out.append((index, entity))
        return out
    return rule


def _vs(any_type: bool):
    def rule(entities, ctx, stats, env):
        from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import fold
        if ctx.printed is None:
            raise SearchError("a value-in-supply rule needs the row's supply, and it is not loaded")
        out = []
        for index, entity in entities:
            value = fold(entity.filler)
            if any_type:
                keep = value in ctx.printed_values or _in_cards(value, ctx.cards)
            else:
                keep = (entity.type, value) in ctx.printed
            if keep:
                out.append((index, entity))
        return out
    return rule


def _in_cards(value: str, cards: list | None) -> bool:
    if not cards or len(value) < 3:
        return False
    pattern = re.compile(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])")
    return any(pattern.search(body) for body in cards)


def _ee(rate: float):
    def rule(entities, ctx, stats, env):
        if not entities or ctx.intent is None:
            return entities
        r = stats.entity_rate(ctx.intent)
        return [] if (r is not None and r < rate) else entities
    return rule


RULES: dict[str, Callable] = {
    "fx-article": _fx_article, "fx-oclock": _fx_oclock, "fx-month-ordinal": _fx_month_ordinal,
    "scope": _scope, "ti0": _ti(True), "ti1": _ti(False), "vs-type": _vs(False), "vs-any": _vs(True),
    "ee5": _ee(0.05), "ee10": _ee(0.10),
}


def apply_rules(rules: Sequence[str], entities: Sequence, ctx: RowContext, stats: TrainStats, env: dict) -> list:
    pairs = list(enumerate(entities))
    for rule in sorted(rules, key=RULE_ORDER.index):
        pairs = RULES[rule](pairs, ctx, stats, env)
    return pairs


# ---------------------------------------------------------------------------
# scoring (in-process, proved against the sealed official per-sample rows)


def score_vector(gold: Mapping[str, Any], scenario, action, entities) -> list[float]:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import score_slu
    s = score_slu(gold_scenario=gold["scenario"], gold_action=gold["action"], gold_entities=list(gold["entities"]),
                  predicted_scenario=scenario, predicted_action=action, predicted_entities=list(entities))
    return [float(getattr(s, f)) for f in COUNT_FIELDS] + [float(s.scenario_action_exact)]


def sealed_vector(row: Mapping[str, Any]) -> list[float]:
    return [float(row[f]) for f in COUNT_FIELDS] + [1.0 if float(row["scenario_action_exact"]) >= 1.0 else 0.0]


def pooled(matrix) -> dict[str, float]:
    import numpy as np
    s = matrix.sum(axis=0)
    tp, fp, fn = s[0] + s[3], s[1] + s[4], s[2] + s[5]
    slu = 0.0 if (2 * tp + fp + fn) == 0 else 2 * tp / (2 * tp + fp + fn)
    etp, efp, efn = s[6], s[7], s[8]
    span = 0.0 if (2 * etp + efp + efn) == 0 else 2 * etp / (2 * etp + efp + efn)
    return {"slu_f1_pp": 100.0 * float(slu), "span_f1_pp": 100.0 * float(span),
            "intent_pp": 100.0 * float(s[9]) / matrix.shape[0]}


def row_f1(vec) -> float:
    tp, fp, fn = vec[0] + vec[3], vec[1] + vec[4], vec[2] + vec[5]
    return 1.0 if (tp + fp + fn) == 0 else 2 * tp / (2 * tp + fp + fn)


class Bootstrap:
    """Paired whole-cluster bootstrap weights, drawn once and shared by every contrast of a read."""

    def __init__(self, ids: Sequence[str], cluster_of: Mapping[str, str], draws: int = BOOT_DRAWS,
                 seed: int = BOOT_SEED):
        import numpy as np
        clusters = sorted({cluster_of[s] for s in ids})
        index = {c: k for k, c in enumerate(clusters)}
        row_cluster = np.array([index[cluster_of[s]] for s in ids], dtype=np.int64)
        rng = np.random.default_rng(seed)
        picks = rng.integers(0, len(clusters), size=(draws, len(clusters)))
        cw = np.zeros((draws, len(clusters)), dtype=np.float64)
        for d in range(draws):
            cw[d] = np.bincount(picks[d], minlength=len(clusters))
        self.weights = cw[:, row_cluster]
        self.clusters = len(clusters)
        self.rows = len(ids)

    def contrast(self, left, right) -> dict[str, Any]:
        import numpy as np

        def slu(m):
            s = self.weights @ m
            tp, fp, fn = s[:, 0] + s[:, 3], s[:, 1] + s[:, 4], s[:, 2] + s[:, 5]
            den = 2 * tp + fp + fn
            return 100.0 * np.where(den == 0, 0.0, 2 * tp / np.maximum(den, 1e-12)), s

        ls, lsum = slu(left)
        rs, rsum = slu(right)
        d = rs - ls
        tot = self.weights.sum(axis=1)
        di = 100.0 * (rsum[:, 9] - lsum[:, 9]) / tot
        pl, pr = pooled(left), pooled(right)
        return {
            "left_slu_f1_pp": round(pl["slu_f1_pp"], 4), "right_slu_f1_pp": round(pr["slu_f1_pp"], 4),
            "delta_slu_pp": round(pr["slu_f1_pp"] - pl["slu_f1_pp"], 4),
            "ci95_slu_pp": [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)],
            "delta_span_pp": round(pr["span_f1_pp"] - pl["span_f1_pp"], 4),
            "delta_intent_pp": round(pr["intent_pp"] - pl["intent_pp"], 4),
            "ci95_intent_pp": [round(float(np.percentile(di, 2.5)), 4), round(float(np.percentile(di, 97.5)), 4)],
        }


# ---------------------------------------------------------------------------
# sealed inputs


def load_gold(lock, data_root: Path, split: str) -> dict:
    if split not in ("train", "devel"):
        raise SearchError(f"split {split!r} is not read (the test split is closed)")
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity
    return {r.sample_id: {"scenario": r.scenario, "action": r.action, "utterance_id": r.utterance_id,
                          "entities": tuple(SlotEntity(type=e.type, filler=e.filler) for e in r.entities)}
            for r in load_slurp_split(lock, data_root, split, workers=4)}


def load_supply(data_root: Path, spec: Mapping[str, Any], GP, W5) -> dict:
    """Per row: the (type, folded value) pairs the supplied exemplars print, and the supplied card bodies
    (the S1 taxonomy's own loaders, unchanged)."""
    phases = GP.load_phases(data_root, {"label": spec["run_id"], "run_id": spec["run_id"],
                                        "attempt": spec["attempt"]})
    m1 = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    m1_by_key = {vid.split("value:", 1)[-1]: v for vid, v in m1.items()}
    cards = GP.load_contract_bodies(data_root)
    out, unresolved = {}, 0
    for sid, ph in phases["rows"].items():
        printed = set()
        for key in ph["ex_rendered"]:
            value = m1_by_key.get(key)
            if value is None:
                unresolved += 1
                continue
            printed |= W5.printed_pairs(value.content)
        out[sid] = {"printed": printed, "cards": [cards["bodies"].get(c, "") for c in ph["contracts"]],
                    "exemplars": len(ph["ex_rendered"]), "cards_n": len(ph["contracts"])}
    return {"rows": out, "phases": [phases["relpath"], phases["sha256"]],
            "m1_snapshot": [W5.M1_SNAPSHOT["relpath"], W5.M1_SNAPSHOT["sha256"]],
            "cards": [cards["relpath"], cards["sha256"]], "unresolved_exemplar_keys": unresolved}


def load_delivered(data_root: Path, spec: Mapping[str, Any]) -> dict:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response
    directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
    outputs = directory / f"{spec['run_id']}.outputs.jsonl"
    scores = directory / f"{spec['run_id']}.scores.json"
    rows = {}
    for record in iter_jsonl(outputs):
        scenario, action, entities, parsed = parse_slu_response(record.get("text") or "")
        rows[str(record["sample_id"])] = {"scenario": scenario, "action": action, "entities": list(entities),
                                          "parsed": bool(parsed)}
    block = json.loads(scores.read_text(encoding="utf-8"))[spec["scorer"]]
    sealed = {str(r["sample_id"]): r for r in block["per_sample"]}
    if len(rows) != spec["rows"] or set(rows) != set(sealed):
        raise SearchError(f"{spec['run_id']}: not the complete {spec['rows']}-row roster")
    return {"rows": rows, "sealed": sealed,
            "official": {"slu_f1_pp": 100.0 * float(block["aggregate"]["official"]["slu_f1"]),
                         "intent_pp": 100.0 * float(block["aggregate"]["official"]["intent_accuracy"])},
            "outputs": [str(outputs.relative_to(data_root)), sha256_file(outputs)],
            "scores": [str(scores.relative_to(data_root)), sha256_file(scores)]}


def roster_disjointness(data_root: Path, rosters: Sequence[str]) -> dict:
    W3A = import_path(REPO_ROOT / "scripts/build_slurp_intent_contrast_cards.py", "build_slurp_intent_contrast_cards")
    if tuple(W3A.POOL) != STATS_POOL:
        raise SearchError("the statistics pool pin differs from the contrast-card builder's R5 pool")
    utterances = W3A.load_pool(data_root)["utterances"]
    out = {}
    for relpath in rosters:
        roster = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        ids = {":".join(str(item["sample_id"]).split(":")[:3]) for item in roster["items"]}
        overlap = len(utterances & ids)
        if overlap:
            raise SearchError(f"the TRAIN statistics pool intersects {relpath} on {overlap} utterances")
        out[relpath] = {"utterances": len(ids), "overlap_with_stats_pool": 0}
    return out


# ---------------------------------------------------------------------------
# Part A


def entity_class(gold_entities, pred_entities) -> dict[int, str]:
    """pred index -> exact / spurious / other, against gold (offline diagnostics only)."""
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items
    its = entity_items(tuple(gold_entities), tuple(pred_entities))
    spurious = {it["pred_index"] for it in its if it["gold_index"] is None and it["pred_index"] is not None}
    matched = {it["pred_index"] for it in its if it["pred_index"] is not None}
    return {i: ("spurious" if i in spurious else "exact" if i not in matched else "other")
            for i in range(len(pred_entities))}


class ColumnBuilder:
    """Applies a rule list to every row of a delivered column and returns its count matrix plus
    edit diagnostics, re-scoring only the rows the rules edited."""

    def __init__(self, ids, delivered, gold, contexts, stats, env, base_matrix, base_classes):
        self.ids, self.delivered, self.gold = ids, delivered, gold
        self.contexts, self.stats, self.env = contexts, stats, env
        self.base_matrix, self.base_classes = base_matrix, base_classes

    def build(self, rules: Sequence[str], keep_texts: bool = False) -> dict:
        import numpy as np
        matrix = self.base_matrix.copy()
        diag = Counter()
        dropped_types: dict[str, Counter] = defaultdict(Counter)
        saves = harms = 0
        texts = {}
        edited_ids = []
        for k, sid in enumerate(self.ids):
            row = self.delivered[sid]
            ents = row["entities"]
            if not row["parsed"] or not ents or not rules:
                continue
            pairs = apply_rules(rules, ents, self.contexts[sid], self.stats, self.env)
            kept = [i for i, _e in pairs]
            new = [e for _i, e in pairs]
            if new == list(ents):
                continue
            edited_ids.append(sid)
            diag["rows_edited"] += 1
            changed = sum(1 for i, e in pairs if e != ents[i])
            diag["fillers_changed"] += changed
            for i in range(len(ents)):
                if i not in kept:
                    cls = self.base_classes[sid][i]
                    diag["entities_dropped"] += 1
                    diag[f"dropped_{cls}"] += 1
                    dropped_types[ents[i].type][cls] += 1
            vec = score_vector(self.gold[sid], row["scenario"], row["action"], new)
            if vec[9] != matrix[k, 9]:
                raise SearchError("a rule changed intent; rules must never touch labels")
            before, after = row_f1(matrix[k]), row_f1(vec)
            saves += int(after > before + 1e-12)
            harms += int(after < before - 1e-12)
            matrix[k] = np.array(vec)
            if keep_texts:
                texts[sid] = new
        diag["row_saves"], diag["row_harms"] = saves, harms
        return {"matrix": matrix, "diag": dict(sorted(diag.items())),
                "dropped_types": {t: dict(c) for t, c in sorted(dropped_types.items())},
                "edited_ids": edited_ids, "texts": texts}


def per_scenario(ids, gold, base, edited) -> dict:
    groups = defaultdict(list)
    for k, sid in enumerate(ids):
        groups[gold[sid]["scenario"]].append(k)
    table = {}
    for name in sorted(groups):
        rows = groups[name]
        b, e = pooled(base[rows]), pooled(edited[rows])
        table[name] = {"rows": len(rows), "delta_pp": round(e["slu_f1_pp"] - b["slu_f1_pp"], 4),
                       "rows_edited": int(sum(1 for k in rows if (base[k] != edited[k]).any()))}
    equal = sum(v["delta_pp"] for v in table.values()) / len(table)
    return {"per_scenario": table, "equal_scenario_delta_pp": round(equal, 4),
            "natural_mixture_delta_pp": round(pooled(edited)["slu_f1_pp"] - pooled(base)["slu_f1_pp"], 4)}


def supply_signal(ids, delivered, gold, contexts, classes) -> dict:
    """Precision / recall of the value-in-supply signal against gold, over delivered entities."""
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import fold
    table = {}
    for name in ("type", "any"):
        c = Counter()
        for sid in ids:
            ctx = contexts[sid]
            for i, e in enumerate(delivered[sid]["entities"]):
                value = fold(e.filler)
                signal = ((e.type, value) in ctx.printed) if name == "type" else \
                    (value in ctx.printed_values or _in_cards(value, ctx.cards))
                cls = classes[sid][i]
                c[f"{'in' if signal else 'out'}_{cls}"] += 1
        n_in = sum(v for k, v in c.items() if k.startswith("in_"))
        n_out = sum(v for k, v in c.items() if k.startswith("out_"))
        exact = c["in_exact"] + c["out_exact"]
        spur = c["in_spurious"] + c["out_spurious"]
        table[name] = {
            "counts": dict(sorted(c.items())), "entities_in_supply": n_in, "entities_not_in_supply": n_out,
            "p_exact_given_in": round(c["in_exact"] / n_in, 4) if n_in else None,
            "p_exact_given_out": round(c["out_exact"] / n_out, 4) if n_out else None,
            "recall_exact_by_in": round(c["in_exact"] / exact, 4) if exact else None,
            "share_spurious_out": round(c["out_spurious"] / spur, 4) if spur else None,
            "drop_rule_precision_spurious": round(c["out_spurious"] / n_out, 4) if n_out else None,
        }
    return table


def grid() -> list[tuple[str, ...]]:
    combos = []
    for fx in itertools.product((False, True), repeat=3):
        for sc in (False, True):
            for ti in (None, "ti0", "ti1"):
                for vs in (None, "vs-type", "vs-any"):
                    for ee in (None, "ee5", "ee10"):
                        rules = [r for r, on in zip(("fx-article", "fx-oclock", "fx-month-ordinal"), fx) if on]
                        if sc:
                            rules.append("scope")
                        rules += [r for r in (ti, vs, ee) if r]
                        if rules:
                            combos.append(tuple(sorted(rules, key=RULE_ORDER.index)))
    return combos


def prepare_partA(args, pool_key: str) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.rails import delivery_normalisers as DN
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity
    import numpy as np

    GP = import_path(REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py",
                     "slurp_gold_position_and_solver_freedom_read")
    W5 = import_path(REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py",
                     "slurp_w5_fold_a_offline_estimate")
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    spec = POOLS[pool_key]
    disjoint = roster_disjointness(data_root, (FOLD_A_ROSTER, R01C_ROSTER))
    pool = GP.load_exemplar_pool(data_root, STATS_POOL[0])
    if pool["content_sha256"] != STATS_POOL[1]:
        raise SearchError("the statistics pool is not the pinned content hash")
    stats = TrainStats(pool["values"])
    table = DN.ScopeRuleTable.from_bytes((data_root / DN.SCOPE_RULE_TABLE_RELPATH).read_bytes(),
                                         expected_sha256=DN.SCOPE_RULE_TABLE_SHA256)
    gold = load_gold(lock, data_root, spec["split"])
    delivered = load_delivered(data_root, spec)
    ids = sorted(delivered["rows"])
    missing = [s for s in ids if s not in gold]
    if missing:
        raise SearchError(f"{len(missing)} roster ids absent from the {spec['split']} gold")
    supply = load_supply(data_root, spec, GP, W5)
    if set(supply["rows"]) != set(ids):
        raise SearchError("the phase artefact does not cover the roster")
    # the base matrix, proved row by row against the sealed official scoring
    base = np.zeros((len(ids), 10), dtype=np.float64)
    mismatches = 0
    for k, sid in enumerate(ids):
        row = delivered["rows"][sid]
        vec = score_vector(gold[sid], row["scenario"], row["action"], row["entities"])
        sealed = sealed_vector(delivered["sealed"][sid])
        if any(abs(a - b) > 1e-9 for a, b in zip(vec, sealed)):
            mismatches += 1
        base[k] = np.array(vec)
    if mismatches:
        raise SearchError(f"{mismatches} rows: in-process scoring does not reproduce the sealed official fields")
    if abs(pooled(base)["slu_f1_pp"] - delivered["official"]["slu_f1_pp"]) > 1e-6:
        raise SearchError("in-process pooled SLU-F1 does not reproduce the official aggregate")
    contexts = {}
    for sid in ids:
        r = delivered["rows"][sid]
        intent = f"{r['scenario']}_{r['action']}" if r["parsed"] and r["scenario"] is not None else None
        contexts[sid] = RowContext(intent, supply["rows"][sid]["printed"], supply["rows"][sid]["cards"])
    classes = {sid: entity_class(gold[sid]["entities"], delivered["rows"][sid]["entities"]) for sid in ids}
    env = {"SlotEntity": SlotEntity, "scope_table": table}
    builder = ColumnBuilder(ids, delivered["rows"], gold, contexts, stats, env, base, classes)
    cluster_of = {sid: (sid if args.row_cluster else gold[sid]["utterance_id"]) for sid in ids}
    boot = Bootstrap(ids, cluster_of)
    return {"spec": spec, "stats": stats, "gold": gold, "delivered": delivered, "ids": ids, "base": base,
            "contexts": contexts, "classes": classes, "builder": builder, "boot": boot, "supply": supply,
            "disjoint": disjoint, "pool": pool, "table": table, "lock": lock, "data_root": data_root}


def base_block(P) -> dict:
    d = P["delivered"]
    n_entities = sum(len(r["entities"]) for r in d["rows"].values())
    return {"run_id": P["spec"]["run_id"], "attempt": P["spec"]["attempt"], "scorer": P["spec"]["scorer"],
            "split": P["spec"]["split"], "rows": len(P["ids"]), "clusters": P["boot"].clusters,
            "official": {k: round(v, 4) for k, v in d["official"].items()},
            "in_process": {k: round(v, 4) for k, v in pooled(P["base"]).items()},
            "rows_reproduced_exactly": len(P["ids"]), "delivered_entities": n_entities,
            "rows_with_entities": sum(1 for r in d["rows"].values() if r["entities"]),
            "unparsed_rows": sum(1 for r in d["rows"].values() if not r["parsed"]),
            "outputs": d["outputs"], "scores": d["scores"]}


def common_block(P) -> dict:
    return {
        "stats_pool": {"relpath": STATS_POOL[0], "content_sha256": STATS_POOL[1],
                       "file_sha256": P["pool"]["sha256"], "disjointness": P["disjoint"]},
        "train_stats": P["stats"].summary(),
        "scope_table": {"relpath": "prepared/SAEA-SLURP-SCOPE-RULE-TABLE-V1/table-v1.json", "sha256": P["table"].sha256},
        "supply": {k: v for k, v in P["supply"].items() if k != "rows"},
        "bootstrap": {"draws": BOOT_DRAWS, "seed": BOOT_SEED,
                      "cluster": "row" if P.get("row_cluster") else "utterance_id",
                      "clusters": P["boot"].clusters, "rows": P["boot"].rows},
    }


def read_combo(P, rules: Sequence[str], keep_texts: bool = False) -> dict:
    col = P["builder"].build(rules, keep_texts=keep_texts)
    out = P["boot"].contrast(P["base"], col["matrix"])
    if out["delta_intent_pp"] != 0.0:
        raise SearchError("intent moved")
    out.update({"rules": list(rules), "diag": col["diag"], "dropped_types": col["dropped_types"]})
    return out, col


def select_partA(args) -> dict:
    P = prepare_partA(args, "a2")
    P["row_cluster"] = args.row_cluster
    started = time.time()
    singles = {}
    for rule in RULE_ORDER:
        res, _col = read_combo(P, (rule,))
        singles[rule] = res
    combos = {}
    for rules in grid():
        res, _col = read_combo(P, rules)
        combos["+".join(rules)] = res
    # the declared selection: max point (ties -> fewer rules), then prune passengers
    best = max(combos.values(), key=lambda r: (round(r["delta_slu_pp"], 6), -len(r["rules"])))
    chosen = list(best["rules"])
    pruning = []
    changed = True
    while changed and len(chosen) > 1:
        changed = False
        current = combos["+".join(chosen)]["delta_slu_pp"]
        for rule in list(chosen):
            reduced = [r for r in chosen if r != rule]
            point = combos["+".join(reduced)]["delta_slu_pp"]
            if point >= current:
                pruning.append({"removed": rule, "point_without": point, "point_with": current})
                chosen = reduced
                changed = True
                break
    selected, col = read_combo(P, tuple(chosen), keep_texts=True)
    ablation = {}
    for rule in chosen:
        reduced = [r for r in chosen if r != rule]
        if reduced:
            ablation[rule] = {"point_without": combos["+".join(reduced)]["delta_slu_pp"],
                              "marginal_pp": round(selected["delta_slu_pp"] - combos["+".join(reduced)]["delta_slu_pp"], 4)}
        else:
            ablation[rule] = {"point_without": 0.0, "marginal_pp": selected["delta_slu_pp"]}
    scen = per_scenario(P["ids"], P["gold"], P["base"], col["matrix"])
    signal = supply_signal(P["ids"], P["delivered"]["rows"], P["gold"], P["contexts"], P["classes"])
    top = sorted(combos.values(), key=lambda r: -r["delta_slu_pp"])[:15]
    copy = maybe_score_copy(args, P, col, "select-a2", chosen)
    return {
        "mode": "select", "pool": "a2", "base": base_block(P), **common_block(P),
        "single_rules": singles, "combinations_read": len(combos),
        "top_combinations": [{k: r[k] for k in ("rules", "delta_slu_pp", "ci95_slu_pp", "diag")} for r in top],
        "all_combinations": {k: {"delta_slu_pp": r["delta_slu_pp"], "ci95_slu_pp": r["ci95_slu_pp"]}
                             for k, r in sorted(combos.items())},
        "selection_rule": "max A2 pooled SLU-F1 point delta (ties -> fewer rules); then remove any member whose "
                          "removal does not lower the point, repeatedly",
        "argmax": best["rules"], "pruning": pruning, "selected": selected, "selected_ablation": ablation,
        "selected_per_scenario": scen, "value_in_supply_signal": signal, "score_copy": copy,
        "seconds": round(time.time() - started, 1),
    }


def confirm_partA(args) -> dict:
    rules = parse_rules(args.rules)
    if not rules:
        raise SystemExit("--confirm needs --rules (the ordered list selected on A2)")
    out_dir = Path(args.data_root) / "analysis" / READ_ID / "confirm-fold-a"
    if (out_dir / "report.json").exists() and not args.allow_rewrite_identical:
        raise SystemExit(f"{out_dir / 'report.json'} exists: the Fold-A confirmation is read once")
    P = prepare_partA(args, "fold-a")
    P["row_cluster"] = args.row_cluster
    result, col = read_combo(P, tuple(rules), keep_texts=True)
    scen = per_scenario(P["ids"], P["gold"], P["base"], col["matrix"])
    copy = maybe_score_copy(args, P, col, "confirm-fold-a", rules)
    lock_candidate = result["ci95_slu_pp"][0] > 0
    return {"mode": "confirm", "pool": "fold-a", "base": base_block(P), **common_block(P), "rules": rules,
            "result": result, "per_scenario": scen, "lock_candidate": lock_candidate,
            "lock_rule": "Fold-A CI95 lower bound > 0", "score_copy": copy}


def maybe_score_copy(args, P, col, label: str, rules: Sequence[str]) -> dict | None:
    """Score the rule column once through the registered scorer on a derived copy (identity proof)."""
    if not args.score_copy:
        return None
    from speech_aware_evidence_acquisition.core.base import SCORERS
    import speech_aware_evidence_acquisition.core.scorers  # noqa: F401
    from speech_aware_evidence_acquisition.rails.slurp_projection_v3 import render_slurp_answer
    out_dir = Path(args.data_root) / "analysis" / READ_ID / label
    out_dir.mkdir(parents=True, exist_ok=True)
    directory = P["data_root"] / "runs" / P["spec"]["run_id"] / P["spec"]["attempt"]
    texts = {str(r["sample_id"]): r.get("text") or "" for r in iter_jsonl(directory / f"{P['spec']['run_id']}.outputs.jsonl")}
    lines = []
    for sid in P["ids"]:
        if sid in col["texts"]:
            row = P["delivered"]["rows"][sid]
            text = render_slurp_answer(row["scenario"], row["action"], col["texts"][sid])
        else:
            text = texts[sid]
        lines.append(json.dumps({"sample_id": sid, "text": text}, ensure_ascii=False, sort_keys=True))
    copy = out_dir / "v4-column-outputs.jsonl"
    copy.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    scorer_id = P["spec"]["scorer"]
    started = time.time()
    result = SCORERS.resolve(scorer_id)(copy, P["lock"], P["data_root"])
    if not result["aggregate"]["identity_check"]["passed"]:
        raise SearchError("the registered scorer's port/official identity check failed on the copy")
    official = 100.0 * float(result["aggregate"]["official"]["slu_f1"])
    in_process = pooled(col["matrix"])["slu_f1_pp"]
    if abs(official - in_process) > 1e-6:
        raise SearchError(f"registered scorer {official} != in-process {in_process}")
    return {"scorer": scorer_id, "copy_sha256": sha256_file(copy), "rules": list(rules),
            "official_slu_f1_pp": round(official, 6), "in_process_slu_f1_pp": round(in_process, 6),
            "official_intent_pp": round(100.0 * float(result["aggregate"]["official"]["intent_accuracy"]), 4),
            "seconds": round(time.time() - started, 1)}


# ---------------------------------------------------------------------------
# Part B


def partB(args) -> dict:
    import numpy as np
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.rails import delivery_normalisers as DN
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity, parse_slu_response

    AG = import_path(REPO_ROOT / "scripts/analysis/slurp_sample_aggregation_offline_read.py",
                     "slurp_sample_aggregation_offline_read")
    GP = import_path(REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py",
                     "slurp_gold_position_and_solver_freedom_read")
    W5 = import_path(REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py",
                     "slurp_w5_fold_a_offline_estimate")
    pool_key = args.pool
    if pool_key not in ("roll1", "roll3"):
        raise SystemExit("--part B reads --pool roll1 or roll3")
    spec = POOLS[pool_key]
    rules = parse_rules(args.rules)
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    disjoint = roster_disjointness(data_root, (FOLD_A_ROSTER, R01C_ROSTER))
    pool = GP.load_exemplar_pool(data_root, STATS_POOL[0])
    if pool["content_sha256"] != STATS_POOL[1]:
        raise SearchError("the statistics pool is not the pinned content hash")
    stats = TrainStats(pool["values"])
    table = DN.ScopeRuleTable.from_bytes((data_root / DN.SCOPE_RULE_TABLE_RELPATH).read_bytes(),
                                         expected_sha256=DN.SCOPE_RULE_TABLE_SHA256)
    env = {"SlotEntity": SlotEntity, "scope_table": table}
    gold = load_gold(lock, data_root, spec["split"])
    directory = data_root / "runs" / spec["run_id"] / spec["attempt"]
    sealed = AG.load_sealed_run(directory, spec["run_id"])
    score_root = data_root / spec["score_root"]
    rendered_root = AG.load_rollout_score_root(score_root, spec["scorer"], 5)
    ids = sorted(sealed)
    if len(ids) != spec["rows"]:
        raise SearchError("not the complete roster")
    supply = None
    if any(r.startswith("vs-") for r in rules):
        supply = load_supply(data_root, spec, GP, W5)
    normaliser = DN.DELIVERY_NORMALISERS.resolve(DN.DELIVER_NORMALISE_V3)

    def project(text: str):
        """v3 projection of one answer text, then parse -- the projected scorer's own triple."""
        s, a, ents, ok = parse_slu_response(normaliser(text).text)
        return s, a, list(ents), bool(ok)

    def ctx_for(sid, s, a, ok):
        intent = f"{s}_{a}" if ok and s is not None else None
        if supply is None:
            return RowContext(intent, set(), [])
        return RowContext(intent, supply["rows"][sid]["printed"], supply["rows"][sid]["cards"])

    def vec_with_rules(sid, s, a, ents, ok, apply: bool):
        if apply and rules and ok and ents:
            ents = [e for _i, e in apply_rules(rules, ents, ctx_for(sid, s, a, ok), stats, env)]
        return score_vector(gold[sid], s, a, ents)

    # single-sample arms, proved against the sealed per-sample scores
    single = {}
    single_v4 = {}
    mismatch = 0
    for index in range(5):
        m = np.zeros((len(ids), 10))
        mv = np.zeros((len(ids), 10))
        for k, sid in enumerate(ids):
            s, a, ents, ok = project(rendered_root["rendered"][index][sid])
            m[k] = vec_with_rules(sid, s, a, ents, ok, False)
            if any(abs(x - y) > 1e-9 for x, y in zip(m[k], sealed_vector(rendered_root["scored"][index][sid]))):
                mismatch += 1
            mv[k] = vec_with_rules(sid, s, a, ents, ok, True)
        single[index], single_v4[index] = m, mv
    if mismatch:
        raise SearchError(f"{mismatch} sample-rows: in-process projected scoring does not reproduce the sealed scores")

    cluster_of = {sid: (sid if args.row_cluster else gold[sid]["utterance_id"]) for sid in ids}
    boot = Bootstrap(ids, cluster_of)
    out_k = {}
    for k_samples, levels in ((3, (2, 3)), (5, (2, 3, 4))):
        subset = list(range(k_samples))
        ref = np.mean([single[i] for i in subset], axis=0)
        ref_v4 = np.mean([single_v4[i] for i in subset], axis=0)
        arms = {}
        medoid_m = np.zeros((len(ids), 10))
        filt = {s: np.zeros((len(ids), 10)) for s in levels}
        filt_v4 = {s: np.zeros((len(ids), 10)) for s in levels}
        dropped = Counter()
        for k, sid in enumerate(ids):
            record = sealed[sid]
            answers = {i: a for i, a in AG._parsed_answers(record).items() if i in subset}
            if not answers:
                empty = project(AG.EMPTY_ANSWER)
                v = vec_with_rules(sid, *empty, False)
                medoid_m[k] = v
                for s in levels:
                    filt[s][k] = v
                    filt_v4[s][k] = v
                continue
            chosen, _d = AG.medoid_index(answers, sorted(answers))
            base = answers[chosen]
            medoid_text = AG.render_answer({"scenario": base.scenario, "action": base.action,
                                            "entities": [{"type": e.type, "filler": e.filler} for e in base.entities]})
            medoid_m[k] = vec_with_rules(sid, *project(medoid_text), False)
            for s in levels:
                kept = [{"type": e.type, "filler": e.filler} for e in base.entities
                        if AG.support_of_entity(e, answers, AG.FLOWN_SIMILARITY_THRESHOLD) >= s]
                dropped[s] += len(base.entities) - len(kept)
                text = AG.render_answer({"scenario": base.scenario, "action": base.action, "entities": kept})
                ps = project(text)
                filt[s][k] = vec_with_rules(sid, *ps, False)
                filt_v4[s][k] = vec_with_rules(sid, *ps, True)
        arms["R0-mean-single"] = {"slu_f1_pp": round(pooled(ref)["slu_f1_pp"], 4)}
        arms["R0-mean-single+v4"] = boot.contrast(ref, ref_v4)
        arms["R1-medoid"] = boot.contrast(ref, medoid_m)
        for s in levels:
            arms[f"R3-support-{s}-of-{k_samples}"] = {**boot.contrast(ref, filt[s]), "entities_dropped": dropped[s]}
            arms[f"R3-support-{s}-of-{k_samples}+v4 vs R0-mean-single+v4"] = boot.contrast(ref_v4, filt_v4[s])
            arms[f"R3-support-{s}-of-{k_samples}+v4 vs R0-mean-single"] = boot.contrast(ref, filt_v4[s])
        out_k[str(k_samples)] = arms
    control = None
    if pool_key == "roll1":
        published = spec["published_r3_3_of_5"]
        got = out_k["5"]["R3-support-3-of-5"]
        control = {"published": published, "reproduced_slu_f1_pp": got["right_slu_f1_pp"],
                   "reproduced_delta_pp": got["delta_slu_pp"],
                   "matches_to_0_01": abs(got["right_slu_f1_pp"] - published["slu_f1_pp"]) < 0.01
                   and abs(got["delta_slu_pp"] - published["delta_pp"]) < 0.01}
    return {"mode": "partB", "pool": pool_key, "policy": spec["policy"], "rules": rules,
            "run": {"run_id": spec["run_id"], "attempt": spec["attempt"], "score_root": spec["score_root"],
                    "scorer": spec["scorer"], "split": spec["split"], "rows": len(ids),
                    "render_manifest_sha256": sha256_file(score_root / "render-manifest.json")},
            "stats_pool": {"relpath": STATS_POOL[0], "content_sha256": STATS_POOL[1], "disjointness": disjoint},
            "bootstrap": {"draws": BOOT_DRAWS, "seed": BOOT_SEED,
                          "cluster": "row" if args.row_cluster else "utterance_id", "clusters": boot.clusters},
            "sample_rows_reproduced_exactly": 5 * len(ids), "by_k": out_k, "control": control}


# ---------------------------------------------------------------------------


def strip_time(text: str) -> str:
    return re.sub(r'"(generated_at|seconds)": [^,\n]*', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part", choices=("A", "B"), default="A")
    parser.add_argument("--pool", default=None, help="Part B: roll1 | roll3 (Part A pools are fixed by --select/--confirm)")
    parser.add_argument("--rules", default=None, help="comma-separated rule ids (applied in the fixed rule order)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--select", action="store_true", help="Part A: search every rule and combination on A2")
    mode.add_argument("--confirm", action="store_true", help="Part A: read --rules once on TRAIN Fold A")
    parser.add_argument("--score-copy", action="store_true",
                        help="score the selected column once through the registered scorer on a derived copy")
    parser.add_argument("--row-cluster", action="store_true", help="cluster = row (precedent control)")
    parser.add_argument("--allow-rewrite-identical", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--label", default=None, help="output sub-directory override")
    args = parser.parse_args(argv)

    if args.part == "A":
        if args.select:
            report, label = select_partA(args), "select-a2"
        elif args.confirm:
            report, label = confirm_partA(args), "confirm-fold-a"
        else:
            raise SystemExit("--part A needs --select or --confirm")
    else:
        report, label = partB(args), f"partb-{args.pool}"
    if args.row_cluster:
        label += "-rowcluster"
    label = args.label or label
    report.update({"read_id": READ_ID, "schema": SCHEMA, "status": "DESCRIPTIVE",
                   "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "driver_sha256": sha256_file(Path(__file__)),
                   "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                                "network": 0, "gpu": 0, "paid_api": 0,
                                "registered_scorer_on_copy": 1 if report.get("score_copy") else 0}})
    text = json.dumps(report, indent=1, sort_keys=True, default=str) + "\n"
    out_dir = Path(args.data_root) / "analysis" / READ_ID / label
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(text, encoding="utf-8", newline="\n")
    content = hashlib.sha256(strip_time(text).encode("utf-8")).hexdigest()
    print(json.dumps({"report": str(out_dir / "report.json"), "sha256": sha256_file(out_dir / "report.json"),
                      "content_sha256_without_time": content}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
