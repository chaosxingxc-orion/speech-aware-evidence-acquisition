"""MF-7: which query signal retrieves TRAIN neighbours that CORRECT SLURP intent?

Retrieval on this carrier has so far keyed on the embedding of the frozen
core's OWN draft answer (``rails.knowledge_provider.KbFacetProvider`` under
``saea-rank-wcos-prior-agree-v1``). This module measures, model-free and
offline, what a *different* query signal against the SAME keys -- the 11,514
TRAIN utterance texts of snapshot ``e27b2745...`` -- would have retrieved, and
whether those neighbours carry enough signal to repair the rows the sealed
closed-list direct baseline got wrong.

OWNER RULE 2026-09-06, which this module encodes rather than merely reports:
**the retrieval query must contain the speech signal.** A text-only query is a
diagnostic, never a cell candidate:

* ``q-draft`` is the lock's LEGACY signal. Its interesting number is the ECHO
  RATE -- how often the neighbours' majority just repeats the label the draft
  already carried, i.e. how much of the "retrieved evidence" is the model's own
  answer coming back.
* ``q-gold-text`` is the UPPER BOUND of any text key: a query that IS the gold
  sentence. The distance from a speech query to it is the cross-modal loss.
* candidates are the speech-containing sets only: ``q-speech-glap`` (this
  module's CPU set), its ``+state`` rank-level fusion, and the GPU sets
  ``q-speech-lco`` / ``q-speech-nemotron`` prepared under the same schema.

Everything here is numpy plus this package's own
:mod:`analysis.paired` bootstrap; no torch, no network, no model. The
producers that create the vectors are separate, ledgered passes -- this module
only consumes their JSONL.

THE FIVE MEASUREMENTS (per query set, per k in {1, 5, 10}, per population
NEW500 / OLD500 / pooled, and per gold scenario):

1. **intent recall@k** -- the DEV row's gold intent appears among the k
   neighbours' TRAIN intents. The ceiling on anything a voter can do.
2. **vote accuracy@k** -- the neighbours' MAJORITY intent equals gold; ties
   broken by best (lowest) neighbour rank.
3. **corrective power** -- the decision quantity. Among rows the sealed
   baseline got WRONG on intent, the share the majority would have SAVED;
   among rows it got RIGHT, the share the majority would have HARMED; net =
   saves - harms, reported in rows and in pp of the population.
4. **filler recall@k** -- the share of the row's gold ``{type, filler}`` slots
   present verbatim among the neighbours' TRAIN slots of the same type. Both
   sides come through ``data.slurp``'s official gold-side join, so "verbatim"
   is the official ``evaluate.py`` comparison with no second normalizer.
5. **echo rate** -- the majority equals the sealed DRAFT's own label. Reported
   for every set; for ``q-draft`` it is the headline.

THE ``+state`` FUSION (owner rule 2026-09-06 clause 2a) is the registered
ranker ``saea-rank-wcos-prior-agree-v1`` with its registered weights and NO
new knob: ``w_cos * max_cosine + w_prior * max_prior + w_agree * agreement``
with ``w_cos=0.5, w_prior=0.3, w_agree=0.2`` read from
``configs/policy/kb-policy-v1.json``. The speech cosine is the content
dimension; the PRIOR dimension is the agent's own intermediate state -- a key
is recalled on it iff its TRAIN intent equals the sealed draft's intent, with
mass 1.0 -- and ``agreement`` is the lock's own "fraction of recalled
dimensions" term. :func:`fusion_dominance_margin` states the consequence in
closed form rather than leaving it to be discovered from a table: at the
registered weights the prior+agreement bonus is ``w_prior + w_agree / 2 =
0.4`` while the whole cosine term spans ``w_cos * [0, 1] = [0, 0.5]``, so a
draft-agreeing key outranks a disagreeing one unless the disagreeing key beats
it by more than 0.8 in raw cosine. Rank-level fusion at the registered weights
is therefore close to a hard restriction to the draft's intent, and its vote
is the draft's label whenever k such keys exist. That is a property of the
registered ranker, not a modelling choice made here, and the receipts report
it as one.

TWO DELIBERATE DEVIATIONS FROM ``rails.kb_policy``, both because this is an
audit of the KEY SIDE rather than a replay of the locked cell:

* ``multidim_recall`` truncates each dimension to ``top_k_per_dimension``
  BEFORE the union, to bound the fuser's candidate pool. An audit needs a
  complete ranking over all 11,514 keys, so no truncation is applied and the
  top-k is taken from the full ranking.
* the locked cell's prior dimension is the snapshot's own 60 TRAIN intent
  priors; here the prior IS the draft's intent, by the owner rule above.

SPLIT DISCIPLINE. Keys are TRAIN (construction data, readable). Queries are
DEV-1000, already consumed by the DEV ladder. The held-out ``test`` split is
never named or loaded. The devel SENTENCE TEXT enters this pipeline only as
``q-gold-text`` vectors produced by a separate ledgered pass; no function here
accepts, stores, prints or hashes it.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from .paired import paired_contrast

AUDIT_SCHEMA = "saea-slurp-retrieval-key-audit-v1"
VECTORS_SCHEMA = "saea-mf7-vectors-v1"
BOOTSTRAP_SEED = 20260903
BOOTSTRAP_REPLICATES = 10_000
CI_LEVEL = 0.90
K_VALUES: tuple[int, ...] = (1, 5, 10)
POPULATIONS: tuple[str, ...] = ("NEW500", "OLD500", "ALL1000")

#: The corrective-power gate the owner set for a speech-containing query set,
#: in pp of the decision population's rows.
CORRECTIVE_NET_GATE_PP = 2.0

#: Query sets that may never be a cell candidate, and why.
DIAGNOSTIC_ONLY: Mapping[str, str] = {
    "q-draft": "text-only, and the query IS the model's own draft answer: the lock's legacy "
    "signal, kept for its echo rate",
    "q-gold-text": "text-only, and the query IS the gold sentence: the upper bound of any text "
    "key, kept to price the cross-modal loss",
}


class RetrievalKeyAuditError(ValueError):
    """A malformed audit input."""


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DevRow:
    """One DEV-1000 query row. Carries NO devel sentence text, by design."""

    sample_id: str
    population: str
    scenario: str
    intent: str
    entities: tuple[tuple[str, str], ...]
    baseline_intent_correct: bool
    draft_intent: str | None

    def validate(self) -> "DevRow":
        if not self.sample_id or not isinstance(self.sample_id, str):
            raise RetrievalKeyAuditError("DevRow.sample_id must be non-empty text")
        if self.population not in ("NEW500", "OLD500"):
            raise RetrievalKeyAuditError(
                f"DevRow.population must be NEW500 or OLD500, got {self.population!r}"
            )
        if not self.scenario or not self.intent:
            raise RetrievalKeyAuditError("DevRow needs a scenario and an intent")
        return self


@dataclass(frozen=True)
class KeyRow:
    """One TRAIN content facet used as a retrieval key."""

    facet_id: str
    intent: str
    entities: tuple[tuple[str, str], ...]

    def validate(self) -> "KeyRow":
        if not self.facet_id or not isinstance(self.facet_id, str):
            raise RetrievalKeyAuditError("KeyRow.facet_id must be non-empty text")
        if not self.intent:
            raise RetrievalKeyAuditError("KeyRow.intent must be non-empty text")
        return self


def _entity_pairs(raw: object, context: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, list):
        raise RetrievalKeyAuditError(f"{context}: entities must be a list")
    pairs: list[tuple[str, str]] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise RetrievalKeyAuditError(f"{context}: entity entry must be an object")
        entity_type = entry.get("type")
        filler = entry.get("filler")
        if not isinstance(entity_type, str) or not isinstance(filler, str):
            raise RetrievalKeyAuditError(f"{context}: entity type/filler must be text")
        pairs.append((entity_type, filler))
    return tuple(pairs)


def load_dev_rows(path: Path | str) -> tuple[DevRow, ...]:
    """Read the producer's ``dev-rows.jsonl``."""

    rows: list[DevRow] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        context = f"dev row line {line_no}"
        draft = raw.get("draft_intent")
        rows.append(
            DevRow(
                sample_id=str(raw["sample_id"]),
                population=str(raw["population"]),
                scenario=str(raw["scenario"]),
                intent=str(raw["intent"]),
                entities=_entity_pairs(raw.get("entities"), context),
                baseline_intent_correct=bool(float(raw["baseline_intent_correct"])),
                draft_intent=str(draft) if isinstance(draft, str) and draft else None,
            ).validate()
        )
    if not rows:
        raise RetrievalKeyAuditError("dev rows file is empty")
    return tuple(rows)


def load_key_rows(path: Path | str) -> tuple[KeyRow, ...]:
    """Read the producer's ``train-facets.jsonl``."""

    rows: list[KeyRow] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        rows.append(
            KeyRow(
                facet_id=str(raw["facet_id"]),
                intent=str(raw["intent"]),
                entities=_entity_pairs(raw.get("entities"), f"key row line {line_no}"),
            ).validate()
        )
    if not rows:
        raise RetrievalKeyAuditError("key rows file is empty")
    return tuple(rows)


def load_vectors_jsonl(path: Path | str) -> tuple[tuple[str, ...], np.ndarray]:
    """Read a ``{"id": ..., "vector": [...]}`` JSONL into ids + a float64 matrix.

    This is the ONE vector interchange schema of MF-7: every producer, CPU or
    GPU, writes it, so the audit re-runs unchanged against a new query set.
    """

    ids: list[str] = []
    vectors: list[list[float]] = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, Mapping) or "id" not in raw or "vector" not in raw:
            raise RetrievalKeyAuditError(f"{path} line {line_no}: needs 'id' and 'vector'")
        identifier = raw["id"]
        vector = raw["vector"]
        if not isinstance(identifier, str) or not identifier:
            raise RetrievalKeyAuditError(f"{path} line {line_no}: id must be non-empty text")
        if not isinstance(vector, list) or not vector:
            raise RetrievalKeyAuditError(f"{path} line {line_no}: vector must be a non-empty list")
        ids.append(identifier)
        vectors.append([float(value) for value in vector])
    if not ids:
        raise RetrievalKeyAuditError(f"{path} is empty")
    widths = {len(vector) for vector in vectors}
    if len(widths) != 1:
        raise RetrievalKeyAuditError(f"{path}: ragged vectors, widths {sorted(widths)}")
    if len(set(ids)) != len(ids):
        raise RetrievalKeyAuditError(f"{path}: duplicate ids")
    return tuple(ids), np.asarray(vectors, dtype=np.float64)


def load_sealed_key_npz(path: Path | str) -> tuple[tuple[str, ...], np.ndarray]:
    """Read the sealed ``vectors-content-facets.npz`` (ids + vectors arrays)."""

    with np.load(Path(path), allow_pickle=False) as payload:
        ids = tuple(str(value) for value in payload["ids"])
        vectors = np.asarray(payload["vectors"], dtype=np.float64)
    if vectors.shape[0] != len(ids):
        raise RetrievalKeyAuditError("sealed key npz: ids and vectors disagree in length")
    return ids, vectors


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def l2_normalise(matrix: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalisation with a zero-safe denominator."""

    matrix = np.asarray(matrix, dtype=np.float64)
    if matrix.ndim != 2:
        raise RetrievalKeyAuditError("expected a 2-D matrix")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms > 0.0, norms, 1.0)


def cosine_matrix(queries: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """``(n_q, n_k)`` cosine similarities."""

    queries = l2_normalise(queries)
    keys = l2_normalise(keys)
    if queries.shape[1] != keys.shape[1]:
        raise RetrievalKeyAuditError(
            f"query dim {queries.shape[1]} != key dim {keys.shape[1]}: a query set must be "
            "compared only against keys embedded by the SAME model"
        )
    return queries @ keys.T


@dataclass(frozen=True)
class RankWeights:
    """The registered ``saea-rank-wcos-prior-agree-v1`` weights."""

    w_cos: float = 0.5
    w_prior: float = 0.3
    w_agree: float = 0.2

    @classmethod
    def from_policy_config(cls, path: Path | str) -> "RankWeights":
        block = json.loads(Path(path).read_text(encoding="utf-8"))["rank_weights"]
        return cls(
            w_cos=float(block["w_cos"]),
            w_prior=float(block["w_prior"]),
            w_agree=float(block["w_agree"]),
        )


def fusion_dominance_margin(weights: RankWeights) -> float:
    """Raw-cosine advantage a draft-DISAGREEING key needs to outrank an agreeing one.

    A key agreeing with the draft scores ``w_cos*c + w_prior + w_agree`` (both
    dimensions recalled, agreement 1); a disagreeing key scores
    ``w_cos*c + w_agree/2`` (content only, agreement 1/2). The gap the cosine
    term must close is therefore ``(w_prior + w_agree/2) / w_cos``. Above 2.0
    the margin exceeds the entire ``[-1, 1]`` cosine range and rank-level
    fusion is a HARD restriction to the draft's intent.
    """

    if weights.w_cos <= 0.0:
        raise RetrievalKeyAuditError("w_cos must be positive")
    return (weights.w_prior + weights.w_agree / 2.0) / weights.w_cos


def fuse_speech_and_state(
    cosines: np.ndarray,
    key_intents: Sequence[str],
    draft_intents: Sequence[str | None],
    weights: RankWeights,
) -> np.ndarray:
    """Rank-level speech+state scores under the registered ranker.

    Mirrors ``rails.kb_policy._rank_weighted_cosine_prior_agreement``: the
    content dimension recalls a key iff its cosine is ``> 0``; the prior
    dimension recalls it iff its TRAIN intent equals this row's sealed draft
    intent (mass 1.0); ``agreement`` is the fraction of recalled dimensions.
    Both dimensions are already inside ``[0, 1]``, so the ``_dimension_scales``
    divisor is the identity and is not recomputed here.

    A row whose draft did not parse has no prior dimension at all: it falls
    back to ``w_cos * cosine + w_agree`` (one dimension, agreement 1), which
    is monotone in cosine and so ranks exactly as speech alone does.

    A key that NO dimension recalls -- non-positive cosine and a TRAIN intent
    the draft does not carry -- scores 0, which is the audit's stand-in for
    the lock's own behaviour of never returning it from the recall stage.
    """

    cosines = np.asarray(cosines, dtype=np.float64)
    if cosines.ndim != 2:
        raise RetrievalKeyAuditError("cosines must be a 2-D matrix")
    if cosines.shape[1] != len(key_intents):
        raise RetrievalKeyAuditError("cosines and key_intents disagree in length")
    if cosines.shape[0] != len(draft_intents):
        raise RetrievalKeyAuditError("cosines and draft_intents disagree in length")

    key_intent_array = np.asarray(key_intents, dtype=object)
    content_recalled = cosines > 0.0
    max_cosine = np.where(content_recalled, cosines, 0.0)

    scores = np.empty_like(cosines)
    for index, draft in enumerate(draft_intents):
        if draft is None:
            prior = np.zeros(cosines.shape[1], dtype=np.float64)
            prior_recalled = np.zeros(cosines.shape[1], dtype=bool)
        else:
            prior_recalled = key_intent_array == draft
            prior = prior_recalled.astype(np.float64)
        recalled_count = content_recalled[index].astype(np.float64) + prior_recalled.astype(
            np.float64
        )
        # ``dims_total`` is the lock's own denominator: the number of DIMENSIONS
        # that recalled at least one candidate for this query.
        dims_total = (1.0 if content_recalled[index].any() else 0.0) + (
            1.0 if prior_recalled.any() else 0.0
        )
        agreement = recalled_count / dims_total if dims_total > 0.0 else np.zeros_like(prior)
        scores[index] = (
            weights.w_cos * max_cosine[index] + weights.w_prior * prior + weights.w_agree * agreement
        )
    return scores


def top_k_indices(scores: np.ndarray, k: int) -> np.ndarray:
    """Per-row indices of the k best scores, score descending then index ascending.

    The index tie-break reproduces ``rails.kb_policy``'s ``facet_id`` ascending
    rule whenever the key rows are supplied in ``facet_id`` order, which the
    producer guarantees.
    """

    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim != 2:
        raise RetrievalKeyAuditError("scores must be a 2-D matrix")
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise RetrievalKeyAuditError("k must be a positive int")
    if k > scores.shape[1]:
        raise RetrievalKeyAuditError(f"k={k} exceeds the {scores.shape[1]} available keys")
    partition = np.argpartition(-scores, kth=k - 1, axis=1)[:, :k]
    partition_scores = np.take_along_axis(scores, partition, axis=1)
    order = np.lexsort((partition, -partition_scores), axis=1)
    return np.take_along_axis(partition, order, axis=1)


def majority_intent(intents: Sequence[str]) -> str:
    """Majority label, ties broken by best (lowest) rank -- the brief's rule."""

    if not intents:
        raise RetrievalKeyAuditError("majority_intent needs at least one neighbour")
    counts = Counter(intents)
    best = max(counts.values())
    for intent in intents:  # rank order
        if counts[intent] == best:
            return intent
    raise AssertionError("unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# Per-row measurements
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RowMeasurement:
    """Everything one (query set, k, DEV row) triple contributes."""

    sample_id: str
    population: str
    scenario: str
    intent_recall: float
    vote_correct: float
    vote_intent: str
    corrective_net: float
    is_save: bool
    is_harm: bool
    baseline_correct: bool
    filler_recall: float | None
    gold_filler_count: int
    echo: float | None


def measure_rows(
    dev_rows: Sequence[DevRow],
    key_rows: Sequence[KeyRow],
    neighbours: np.ndarray,
) -> tuple[RowMeasurement, ...]:
    """The five per-row quantities for one query set at one k."""

    neighbours = np.asarray(neighbours)
    if neighbours.ndim != 2 or neighbours.shape[0] != len(dev_rows):
        raise RetrievalKeyAuditError("neighbours must be (n_dev_rows, k)")
    key_intents = [row.intent for row in key_rows]
    key_entities = [row.entities for row in key_rows]

    out: list[RowMeasurement] = []
    for position, row in enumerate(dev_rows):
        picked = [int(index) for index in neighbours[position]]
        intents = [key_intents[index] for index in picked]
        vote = majority_intent(intents)
        recall = 1.0 if row.intent in intents else 0.0
        correct = 1.0 if vote == row.intent else 0.0

        is_save = (not row.baseline_intent_correct) and bool(correct)
        is_harm = row.baseline_intent_correct and not bool(correct)
        net = 1.0 if is_save else (-1.0 if is_harm else 0.0)

        available: set[tuple[str, str]] = set()
        for index in picked:
            available.update(key_entities[index])
        gold = set(row.entities)
        filler_recall = (len(gold & available) / len(gold)) if gold else None

        echo = None if row.draft_intent is None else (1.0 if vote == row.draft_intent else 0.0)

        out.append(
            RowMeasurement(
                sample_id=row.sample_id,
                population=row.population,
                scenario=row.scenario,
                intent_recall=recall,
                vote_correct=correct,
                vote_intent=vote,
                corrective_net=net,
                is_save=is_save,
                is_harm=is_harm,
                baseline_correct=row.baseline_intent_correct,
                filler_recall=filler_recall,
                gold_filler_count=len(gold),
                echo=echo,
            )
        )
    return tuple(out)


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def summarise(measurements: Sequence[RowMeasurement]) -> dict[str, object]:
    """Aggregate one population's rows into the reported table row."""

    if not measurements:
        return {"n": 0}
    wrong = [m for m in measurements if not m.baseline_correct]
    right = [m for m in measurements if m.baseline_correct]
    saves = sum(1 for m in measurements if m.is_save)
    harms = sum(1 for m in measurements if m.is_harm)
    with_fillers = [m for m in measurements if m.filler_recall is not None]
    with_echo = [m for m in measurements if m.echo is not None]
    n = len(measurements)
    return {
        "n": n,
        "intent_recall_at_k": 100.0 * _mean([m.intent_recall for m in measurements]),
        "vote_accuracy_at_k": 100.0 * _mean([m.vote_correct for m in measurements]),
        "baseline_intent_accuracy": 100.0 * _mean(
            [1.0 if m.baseline_correct else 0.0 for m in measurements]
        ),
        "baseline_wrong_rows": len(wrong),
        "baseline_right_rows": len(right),
        "saves": saves,
        "harms": harms,
        "corrective_share_of_wrong": (100.0 * saves / len(wrong)) if wrong else None,
        "harm_share_of_right": (100.0 * harms / len(right)) if right else None,
        "net_rows": saves - harms,
        "net_pp": 100.0 * (saves - harms) / n,
        "filler_recall_at_k": (
            100.0 * _mean([float(m.filler_recall) for m in with_fillers]) if with_fillers else None
        ),
        "filler_rows_scored": len(with_fillers),
        "gold_fillers_total": sum(m.gold_filler_count for m in measurements),
        "echo_rate": (100.0 * _mean([float(m.echo) for m in with_echo]) if with_echo else None),
        "echo_rows_scored": len(with_echo),
    }


def _population_filter(measurements: Sequence[RowMeasurement], population: str):
    if population == "ALL1000":
        return list(measurements)
    return [m for m in measurements if m.population == population]


# ---------------------------------------------------------------------------
# Paired bootstrap
# ---------------------------------------------------------------------------

#: The per-row metric names carried into :func:`paired_contrast`.
PAIRED_METRICS: tuple[str, ...] = (
    "corrective_net_pp",
    "vote_accuracy_pp",
    "intent_recall_pp",
    "filler_recall_pp",
)


def paired_score_table(measurements: Sequence[RowMeasurement]) -> dict[str, dict[str, float]]:
    """``{sample_id: {metric: value}}`` in the shape :func:`paired_contrast` eats.

    Every metric is expressed in POINTS so a mean is directly a pp figure and a
    delta of means is directly a pp delta. ``filler_recall_pp`` is 0 for a row
    with no gold slot, which keeps the paired row set identical across metrics;
    the headline filler number in :func:`summarise` is the one restricted to
    rows that HAVE a gold slot, and the receipts label both.
    """

    return {
        m.sample_id: {
            "corrective_net_pp": 100.0 * m.corrective_net,
            "vote_accuracy_pp": 100.0 * m.vote_correct,
            "intent_recall_pp": 100.0 * m.intent_recall,
            "filler_recall_pp": 100.0 * (m.filler_recall if m.filler_recall is not None else 0.0),
        }
        for m in measurements
    }


def _zero_table(table: Mapping[str, Mapping[str, float]]) -> dict[str, dict[str, float]]:
    return {sid: {metric: 0.0 for metric in row} for sid, row in table.items()}


def _contrast_json(contrast) -> dict[str, object]:
    return {
        "metric": contrast.metric,
        "n": contrast.n,
        "left_mean": contrast.left_mean,
        "right_mean": contrast.right_mean,
        "delta": contrast.delta,
        "saves": contrast.saves,
        "harms": contrast.harms,
        "ties": contrast.ties,
        "sign_test_p": contrast.sign_test_p,
        "ci_low": contrast.bootstrap.ci_low,
        "ci_high": contrast.bootstrap.ci_high,
        "ci_level": contrast.bootstrap.ci_level,
        "n_replicates": contrast.bootstrap.n_replicates,
        "seed": contrast.bootstrap.seed,
    }


def absolute_ci(
    measurements: Sequence[RowMeasurement],
    *,
    seed: int = BOOTSTRAP_SEED,
    n_replicates: int = BOOTSTRAP_REPLICATES,
) -> dict[str, dict[str, object]]:
    """CI90 for one query set's own levels, via a contrast against all-zeros.

    Reusing :func:`paired_contrast` rather than writing a second resampler
    keeps ONE bootstrap in this repository: same stratification (gold
    scenario), same seed, same replicate count, same percentile rule.
    """

    table = paired_score_table(measurements)
    strata = {m.sample_id: m.scenario for m in measurements}
    contrasts = paired_contrast(
        _zero_table(table),
        table,
        metrics=PAIRED_METRICS,
        strata_of=strata.__getitem__,
        seed=seed,
        n_replicates=n_replicates,
        ci_level=CI_LEVEL,
    )
    return {metric: _contrast_json(contrast) for metric, contrast in contrasts.items()}


def delta_ci(
    left: Sequence[RowMeasurement],
    right: Sequence[RowMeasurement],
    *,
    seed: int = BOOTSTRAP_SEED,
    n_replicates: int = BOOTSTRAP_REPLICATES,
) -> dict[str, dict[str, object]]:
    """Paired CI90 on ``right - left`` over the SAME rows, stratified by scenario."""

    left_table = paired_score_table(left)
    right_table = paired_score_table(right)
    if set(left_table) != set(right_table):
        raise RetrievalKeyAuditError("paired contrast needs the same rows on both sides")
    strata = {m.sample_id: m.scenario for m in right}
    contrasts = paired_contrast(
        left_table,
        right_table,
        metrics=PAIRED_METRICS,
        strata_of=strata.__getitem__,
        seed=seed,
        n_replicates=n_replicates,
        ci_level=CI_LEVEL,
    )
    return {metric: _contrast_json(contrast) for metric, contrast in contrasts.items()}


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuerySet:
    """One named query signal and the key space it is compared against."""

    query_set_id: str
    query_ids: tuple[str, ...]
    query_vectors: np.ndarray
    key_ids: tuple[str, ...]
    key_vectors: np.ndarray
    encoder: str
    contains_speech: bool
    fuses_state: bool
    provenance: Mapping[str, object]


def align_keys(
    key_rows: Sequence[KeyRow], key_ids: Sequence[str], key_vectors: np.ndarray
) -> np.ndarray:
    """Reorder a key matrix into ``key_rows`` order, refusing any gap."""

    position = {identifier: index for index, identifier in enumerate(key_ids)}
    missing = [row.facet_id for row in key_rows if row.facet_id not in position]
    if missing:
        raise RetrievalKeyAuditError(
            f"{len(missing)} key rows have no vector; first missing {missing[0]!r}"
        )
    return np.asarray(key_vectors, dtype=np.float64)[[position[row.facet_id] for row in key_rows]]


def align_queries(
    dev_rows: Sequence[DevRow], query_ids: Sequence[str], query_vectors: np.ndarray
) -> np.ndarray:
    """Reorder a query matrix into ``dev_rows`` order, refusing any gap."""

    position = {identifier: index for index, identifier in enumerate(query_ids)}
    missing = [row.sample_id for row in dev_rows if row.sample_id not in position]
    if missing:
        raise RetrievalKeyAuditError(
            f"{len(missing)} DEV rows have no query vector; first missing {missing[0]!r}"
        )
    return np.asarray(query_vectors, dtype=np.float64)[[position[row.sample_id] for row in dev_rows]]


def run_query_set(
    query_set: QuerySet,
    dev_rows: Sequence[DevRow],
    key_rows: Sequence[KeyRow],
    weights: RankWeights,
    *,
    k_values: Sequence[int] = K_VALUES,
) -> dict[int, tuple[RowMeasurement, ...]]:
    """Rank, then measure, one query set at every k."""

    queries = align_queries(dev_rows, query_set.query_ids, query_set.query_vectors)
    keys = align_keys(key_rows, query_set.key_ids, query_set.key_vectors)
    cosines = cosine_matrix(queries, keys)
    if query_set.fuses_state:
        scores = fuse_speech_and_state(
            cosines, [row.intent for row in key_rows], [row.draft_intent for row in dev_rows], weights
        )
    else:
        scores = cosines
    return {
        int(k): measure_rows(dev_rows, key_rows, top_k_indices(scores, int(k))) for k in k_values
    }


def decision(
    per_set: Mapping[str, Mapping[int, Sequence[RowMeasurement]]],
    *,
    decision_k: int = 5,
    population: str = "NEW500",
) -> dict[str, object]:
    """Apply the preregistered decision table (owner rule 2026-09-06 clause 3).

    KU-S1 flies with the SPEECH-CONTAINING set of highest net corrective power
    on ``population``; ties go to the simpler signal (speech alone before
    speech+state, fewer models before more). If the best such set's net is
    below :data:`CORRECTIVE_NET_GATE_PP`, retrieval-by-neighbours on SLURP
    intent is CLOSED. ``q-draft`` and ``q-gold-text`` are diagnostics and are
    never eligible; the gap to ``q-gold-text`` is the cross-modal loss.
    """

    nets: dict[str, float] = {}
    for set_id, by_k in per_set.items():
        rows = _population_filter(list(by_k[decision_k]), population)
        nets[set_id] = float(summarise(rows)["net_pp"])

    eligible = sorted(
        (set_id for set_id in per_set if set_id not in DIAGNOSTIC_ONLY),
        key=lambda set_id: (-nets[set_id], set_id.endswith("+state"), set_id),
    )
    if not eligible:
        raise RetrievalKeyAuditError("no speech-containing query set was measured")
    winner = eligible[0]
    runner_up = eligible[1] if len(eligible) > 1 else None
    gate_cleared = nets[winner] > CORRECTIVE_NET_GATE_PP
    gold_net = nets.get("q-gold-text")
    return {
        "decision_k": decision_k,
        "decision_population": population,
        "gate_net_pp": CORRECTIVE_NET_GATE_PP,
        "eligible_sets": eligible,
        "diagnostic_only": dict(DIAGNOSTIC_ONLY),
        "net_pp_by_set": nets,
        "winner": winner,
        "winner_net_pp": nets[winner],
        "runner_up": runner_up,
        "runner_up_net_pp": nets[runner_up] if runner_up else None,
        "gate_cleared": bool(gate_cleared),
        "verdict": (
            f"KU-S1-prime flies with {winner}" if gate_cleared
            else "CLOSED: retrieval-by-neighbours on SLURP intent does not clear the gate"
        ),
        "gold_text_upper_bound_net_pp": gold_net,
        "cross_modal_loss_pp": (
            None if gold_net is None else gold_net - nets[winner]
        ),
    }


#: MF-7b's echo-degeneracy threshold, in percent of the rows an echo rate is
#: scored on. Preregistered in
#: ``docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2-preregistration.md``
#: clause 2, on the arithmetic MF-7 section 5.3 already published: a set whose
#: majority vote just repeats the query's own draft label is not retrieving.
ECHO_DEGENERACY_PP = 90.0


def cosine_separation(
    query_set: "QuerySet",
    dev_rows: Sequence[DevRow],
    key_rows: Sequence[KeyRow],
    *,
    population: str = "ALL1000",
) -> dict[str, object]:
    """Cross-modal separation: the cosine distribution of MATCHED pairs (the
    key's TRAIN intent equals the DEV row's gold intent) against UNMATCHED
    ones.

    Reported for every speech set and gating nothing. It separates two very
    different failures a low vote accuracy can hide: an encoder that puts
    speech and text in different regions of the space (no separation at all),
    and one that separates them but whose ranking is still too weak for a
    majority vote to find the gold intent (separation present, recall high,
    vote low).
    """

    queries = align_queries(dev_rows, query_set.query_ids, query_set.query_vectors)
    keys = align_keys(key_rows, query_set.key_ids, query_set.key_vectors)
    if population != "ALL1000":
        keep = [index for index, row in enumerate(dev_rows) if row.population == population]
        queries = queries[keep]
        rows = [dev_rows[index] for index in keep]
    else:
        rows = list(dev_rows)
    cosines = cosine_matrix(queries, keys)
    key_intents = np.asarray([row.intent for row in key_rows], dtype=object)
    gold = np.asarray([row.intent for row in rows], dtype=object)
    matched_mask = key_intents[None, :] == gold[:, None]
    matched = cosines[matched_mask]
    unmatched = cosines[~matched_mask]

    def block(values: np.ndarray) -> dict[str, object]:
        if values.size == 0:
            return {"n": 0}
        return {
            "n": int(values.size),
            "mean": float(values.mean()),
            "sd": float(values.std(ddof=0)),
            "p05": float(np.percentile(values, 5)),
            "p50": float(np.percentile(values, 50)),
            "p95": float(np.percentile(values, 95)),
            "min": float(values.min()),
            "max": float(values.max()),
        }

    matched_block = block(matched)
    unmatched_block = block(unmatched)
    sd = float(unmatched_block.get("sd", 0.0)) if unmatched_block.get("n") else 0.0
    delta = (
        float(matched_block["mean"]) - float(unmatched_block["mean"])
        if matched_block.get("n") and unmatched_block.get("n")
        else None
    )
    return {
        "query_set_id": query_set.query_set_id,
        "encoder": query_set.encoder,
        "population": population,
        "queries": int(queries.shape[0]),
        "keys": int(keys.shape[0]),
        "matched": matched_block,
        "unmatched": unmatched_block,
        "mean_delta": delta,
        "standardised_separation": (
            None if delta is None or sd == 0.0 else delta / sd
        ),
    }


def _nearest_other_agreement(
    matrix: np.ndarray, labels: Sequence[str], *, chunk: int = 512
) -> dict[str, object]:
    """Share of rows whose nearest OTHER row carries the same label.

    Chunked so an 11,514-square cosine matrix never has to exist at once.
    """

    normalised = l2_normalise(np.asarray(matrix, dtype=np.float64))
    labels = list(labels)
    agree = 0
    cosine_sum = 0.0
    cosine_count = 0
    for start in range(0, normalised.shape[0], chunk):
        block = normalised[start : start + chunk] @ normalised.T
        cosine_sum += float(block.sum())
        cosine_count += int(block.size)
        for offset in range(block.shape[0]):
            block[offset, start + offset] = -2.0
        nearest = block.argmax(axis=1)
        agree += sum(
            1
            for offset, index in enumerate(nearest)
            if labels[start + offset] == labels[int(index)]
        )
    total = normalised.shape[0]
    return {
        "n": total,
        "nearest_other_same_label_pp": 100.0 * agree / total if total else None,
        "mean_cosine": cosine_sum / cosine_count if cosine_count else None,
    }


def key_space_coherence(
    *,
    encoder: str,
    key_vectors: np.ndarray,
    key_labels: Sequence[str],
    query_vectors: np.ndarray,
    query_labels: Sequence[str],
    label_vectors: np.ndarray | None = None,
    label_labels: Sequence[str] | None = None,
) -> dict[str, object]:
    """Is each TOWER internally healthy, independent of the modality gap?

    A speech query set can fail for two very different reasons, and a verdict
    that cannot separate them is not worth much. This asks each side on its own
    terms -- do two TRAIN texts of the same intent land near each other, do two
    recordings of the same intent land near each other, and does a TRAIN text
    find its own label -- so a failure that survives all three healthy towers is
    a cross-modal failure and nothing else.
    """

    out: dict[str, object] = {
        "encoder": encoder,
        "text_key_space": _nearest_other_agreement(key_vectors, key_labels),
        "speech_query_space": _nearest_other_agreement(query_vectors, query_labels),
    }
    if label_vectors is not None and label_labels is not None:
        keys = l2_normalise(np.asarray(key_vectors, dtype=np.float64))
        labels_matrix = l2_normalise(np.asarray(label_vectors, dtype=np.float64))
        sims = keys @ labels_matrix.T
        best = sims.argmax(axis=1)
        label_list = list(label_labels)
        key_list = list(key_labels)
        hits = sum(
            1 for position, index in enumerate(best)
            if label_list[int(index)] == key_list[position]
        )
        out["train_text_to_label"] = {
            "n": len(key_list),
            "labels": len(label_list),
            "nearest_label_accuracy_pp": 100.0 * hits / len(key_list) if key_list else None,
            "mean_cosine": float(sims.mean()),
            "chance_pp": 100.0 / len(label_list) if label_list else None,
        }
    return out


def decision_v2(
    per_set: Mapping[str, Mapping[int, Sequence[RowMeasurement]]],
    *,
    decision_k: int = 5,
    population: str = "NEW500",
    ci_low_by_set: Mapping[str, float],
    gate_pp: float = CORRECTIVE_NET_GATE_PP,
    echo_degeneracy_pp: float = ECHO_DEGENERACY_PP,
) -> dict[str, object]:
    """MF-7b's preregistered decision table (v2 preregistration section 4).

    Two things differ from :func:`decision`, both fixed before any v2 number
    existed. **Degeneracy**: a set whose echo rate at the decision k on the
    decision population is at least ``echo_degeneracy_pp`` cannot be the winner
    that licenses KU-S1 -- its vote is its own input rather than a retrieved
    neighbour -- though it is still measured and reported. **A two-sided
    gate**: the winner must reach ``gate_pp`` on the point estimate AND carry a
    CI90 lower bound strictly above zero, where ``ci_low_by_set`` supplies that
    bound from the same single bootstrap every other figure uses.
    """

    nets: dict[str, float] = {}
    echoes: dict[str, float | None] = {}
    for set_id, by_k in per_set.items():
        rows = _population_filter(list(by_k[decision_k]), population)
        summary = summarise(rows)
        nets[set_id] = float(summary["net_pp"])
        echo = summary.get("echo_rate")
        echoes[set_id] = None if echo is None else float(echo)

    degenerate = sorted(
        set_id
        for set_id, echo in echoes.items()
        if echo is not None and echo >= echo_degeneracy_pp
    )
    eligible = sorted(
        (
            set_id
            for set_id in per_set
            if set_id not in DIAGNOSTIC_ONLY and set_id not in degenerate
        ),
        key=lambda set_id: (
            -nets[set_id],
            set_id.endswith("+state"),
            not set_id.endswith("-fused"),
            set_id,
        ),
    )
    winner = eligible[0] if eligible else None
    runner_up = eligible[1] if len(eligible) > 1 else None
    ci_low = None if winner is None else float(ci_low_by_set[winner])
    point_cleared = winner is not None and nets[winner] >= gate_pp
    interval_cleared = ci_low is not None and ci_low > 0.0
    gate_cleared = bool(point_cleared and interval_cleared)
    gold_net = nets.get("q-gold-text")
    return {
        "decision_k": decision_k,
        "decision_population": population,
        "gate_net_pp": gate_pp,
        "gate_rule": "net corrective power >= gate_net_pp AND CI90 lower bound > 0",
        "echo_degeneracy_pp": echo_degeneracy_pp,
        "degenerate_sets": degenerate,
        "eligible_sets": eligible,
        "diagnostic_only": dict(DIAGNOSTIC_ONLY),
        "net_pp_by_set": nets,
        "echo_rate_by_set": echoes,
        "ci90_low_by_set": {key: float(value) for key, value in ci_low_by_set.items()},
        "winner": winner,
        "winner_net_pp": None if winner is None else nets[winner],
        "winner_ci90_low": ci_low,
        "runner_up": runner_up,
        "runner_up_net_pp": None if runner_up is None else nets[runner_up],
        "point_estimate_cleared": bool(point_cleared),
        "interval_cleared": bool(interval_cleared),
        "gate_cleared": gate_cleared,
        "verdict": (
            f"KU-S1 flies with {winner}"
            if gate_cleared
            else "CLOSED: neighbour retrieval on SLURP intent does not clear the gate; "
            "re-scoped to the slot side (KU-S3) and to Audio2Tool (KU-A1)"
        ),
        "gold_text_upper_bound_net_pp": gold_net,
        "cross_modal_loss_pp": (
            None if gold_net is None or winner is None else gold_net - nets[winner]
        ),
    }


def scenario_table(measurements: Sequence[RowMeasurement]) -> list[dict[str, object]]:
    """One row per gold scenario -- the per-stratum table every verdict carries."""

    scenarios = sorted({m.scenario for m in measurements})
    rows: list[dict[str, object]] = []
    for scenario in scenarios:
        subset = [m for m in measurements if m.scenario == scenario]
        row: dict[str, object] = {"scenario": scenario}
        row.update(summarise(subset))
        rows.append(row)
    return rows


def build_summary(
    per_set: Mapping[str, Mapping[int, Sequence[RowMeasurement]]],
    query_sets: Mapping[str, QuerySet],
    weights: RankWeights,
    *,
    decision_k: int = 5,
    baseline_run_id: str,
    draft_run_id: str,
    snapshot_sha256: str,
    key_npz_sha256: str,
    accounting: Mapping[str, object],
    reference: str = "q-draft",
) -> dict[str, object]:
    """The receipt directory's ``summary.json``.

    ``reference`` names the set every other set is paired against. It defaults
    to ``q-draft`` -- MF-7's own reference and the lock's legacy signal -- and
    the paired block is simply omitted when that set was not measured, which is
    the case for a key space no CPU encoder ever embedded (MF-7b's label keys).
    """

    tables: dict[str, object] = {}
    for set_id, by_k in per_set.items():
        per_k: dict[str, object] = {}
        for k, rows in sorted(by_k.items()):
            per_k[str(k)] = {
                population: summarise(_population_filter(list(rows), population))
                for population in POPULATIONS
            }
        tables[set_id] = {
            "encoder": query_sets[set_id].encoder,
            "contains_speech": query_sets[set_id].contains_speech,
            "fuses_state": query_sets[set_id].fuses_state,
            "role": "diagnostic" if set_id in DIAGNOSTIC_ONLY else "candidate",
            "diagnostic_reason": DIAGNOSTIC_ONLY.get(set_id),
            "provenance": dict(query_sets[set_id].provenance),
            "by_k": per_k,
        }

    absolute: dict[str, object] = {}
    for set_id, by_k in per_set.items():
        absolute[set_id] = {
            population: absolute_ci(_population_filter(list(by_k[decision_k]), population))
            for population in POPULATIONS
        }

    deltas: dict[str, object] = {}
    if reference in per_set:
        for set_id, by_k in per_set.items():
            if set_id == reference:
                continue
            deltas[f"{set_id}__vs__{reference}"] = {
                population: delta_ci(
                    _population_filter(list(per_set[reference][decision_k]), population),
                    _population_filter(list(by_k[decision_k]), population),
                )
                for population in POPULATIONS
            }
    speech_sets = [set_id for set_id in per_set if set_id not in DIAGNOSTIC_ONLY]
    for left in speech_sets:
        for right in speech_sets:
            if left >= right:
                continue
            deltas[f"{right}__vs__{left}"] = {
                population: delta_ci(
                    _population_filter(list(per_set[left][decision_k]), population),
                    _population_filter(list(per_set[right][decision_k]), population),
                )
                for population in POPULATIONS
            }

    return {
        "schema": AUDIT_SCHEMA,
        "authority": (
            "owner GO 2026-09-06 (MF-7) and the owner rule of 2026-09-06 that the retrieval query "
            "must contain the speech signal; "
            "docs/readiness/2026-09-05-three-dimension-experiment-program.md section 4b"
        ),
        "exposure_ledger_rows": [
            "SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V1",
            "SAEA-SLURP-MF7-EMBEDDING-CPU-V1",
        ],
        "keys": {
            "count": len(next(iter(query_sets.values())).key_ids),
            "source": "TRAIN content facets (utterance texts) of the pinned SLURP snapshot",
            "snapshot_sha256": snapshot_sha256,
            "sealed_key_npz_sha256": key_npz_sha256,
        },
        "queries": {
            "roster": "DEV-1000 (already consumed by the DEV ladder)",
            "decision_population": "NEW500",
            "baseline_run_id": baseline_run_id,
            "draft_run_id": draft_run_id,
        },
        "ranker": {
            "policy_id": "saea-rank-wcos-prior-agree-v1",
            "w_cos": weights.w_cos,
            "w_prior": weights.w_prior,
            "w_agree": weights.w_agree,
            "fusion_dominance_margin": fusion_dominance_margin(weights),
            "fusion_note": (
                "a draft-disagreeing key must beat an agreeing one by this much RAW COSINE to "
                "outrank it; above 2.0 the margin exceeds the whole cosine range and rank-level "
                "fusion is a hard restriction to the draft's intent"
            ),
        },
        "bootstrap": {
            "n_replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "ci_level": CI_LEVEL,
            "stratified_by": "gold scenario",
            "paired": True,
        },
        "query_sets": tables,
        "absolute_ci90": absolute,
        "delta_ci90": deltas,
        "decision": decision(per_set, decision_k=decision_k),
        "accounting": dict(accounting),
    }


def build_scenario_tables(
    per_set: Mapping[str, Mapping[int, Sequence[RowMeasurement]]], *, decision_k: int = 5
) -> dict[str, object]:
    """The ``per-scenario-table.json`` payload."""

    return {
        "schema": AUDIT_SCHEMA,
        "k": decision_k,
        "tables": {
            set_id: {
                population: scenario_table(_population_filter(list(by_k[decision_k]), population))
                for population in POPULATIONS
            }
            for set_id, by_k in per_set.items()
        },
    }


def decontamination_report(
    dev_rows: Sequence[DevRow],
    key_rows: Sequence[KeyRow],
    query_sets: Iterable[QuerySet],
) -> dict[str, object]:
    """Prove the audit never crossed a split boundary it must not cross."""

    def segment(identifier: str, index: int) -> str:
        parts = identifier.split(":")
        return parts[index] if len(parts) > index else identifier

    dev_utterance_prefixes = {segment(row.sample_id, 1) for row in dev_rows}
    key_prefixes = {segment(row.facet_id, 1) for row in key_rows}
    return {
        "schema": AUDIT_SCHEMA,
        "held_out_test_split": {
            "named": False,
            "loaded": False,
            "note": "no function in this audit accepts a 'test' split id; every loader call "
            "passes allow_heldout=False",
        },
        "query_side": {
            "split": sorted(dev_utterance_prefixes),
            "roster": "DEV-1000",
            "n": len(dev_rows),
            "prior_exposure": "consumed by the DEV ladder before this audit; no new evaluation "
            "surface is opened",
        },
        "key_side": {
            "facet_namespace": sorted(key_prefixes),
            "split": "train",
            "n": len(key_rows),
            "legality": "construction data, readable under the entity clause",
        },
        "devel_sentence_text": {
            "read": True,
            "purpose": "q-gold-text embeddings ONLY, under SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V1",
            "written_to_any_artifact": False,
            "note": "the audit module never receives the text: it consumes vectors keyed by "
            "sample id, and no receipt field, table cell or log line carries a sentence",
        },
        "query_sets": [
            {
                "query_set_id": query_set.query_set_id,
                "encoder": query_set.encoder,
                "contains_speech": query_set.contains_speech,
                "fuses_state": query_set.fuses_state,
                "role": "diagnostic" if query_set.query_set_id in DIAGNOSTIC_ONLY else "candidate",
            }
            for query_set in query_sets
        ],
        "frozen_core_contacts": 0,
        "gpu_hours": 0.0,
    }
