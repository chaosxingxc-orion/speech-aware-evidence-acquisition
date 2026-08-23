"""P-EMB-4R per-modality mean-centering re-analysis -- MODEL-FREE, DESCRIPTIVE.

Work item: ``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md``
section 5, CPU queue, final entry ("per-modality mean-centering re-analysis of
the landed P-EMB-4R vectors (model-free; settles whether the 0.13-0.28 audio
cosine is a modality-cone artifact)"). Survey grounding: items 17 (modality
gap: Mind the Gap / I0T standardization / mean-shift calibration) and 28
(audio-text embedding granularity) of
``docs/readiness/2026-08-23-cross-modal-retrieval-survey.md``.

**Legality frame.** This module is a DESCRIPTIVE RE-ANALYSIS of already
CONSUMED artifacts: the seven-arm P-EMB-4R vector sets written by
``rails.probes.pemb4r_flight`` (attempt ``attempt-20260820T181837Z-3e6c8f``)
and consumed by the one-shot read of 2026-08-21
(``docs/checks/speech-aware-evidence-acquisition/2026-08-21-pemb4r-read/``).
It makes ZERO model contacts, starts no server, writes nothing to the
embedding namespace, and regenerates no vector. Gold scenario labels are used
SCORING-SIDE ONLY, offline, exactly as the consumed read used them. The
outputs are DESIGN INPUTS for knowledge-base construction; they carry no
verdict clause and cannot revise the consumed P-EMB-4R verdict. No function
in this module emits, computes, or names a registered verdict clause.

**Reproduce before re-analysing.** :func:`build_reanalysis` always recomputes
the BASELINE arm reports from the landed vectors through the SAME code the
consumed read used -- ``pemb4r_flight.build_arm_retrieval`` for retrieval and
``analysis.pemb4r_read.build_arm_report`` for vote/recall -- and compares them
field-by-field against the landed ``verdict.json``. A single disagreement is
reported as a hard reproduction failure; the corrected tables are still
computed but the report states plainly that the baseline did not reproduce.
The fast vectorised scorer this module needs for the corrected variants is
itself validated against ``build_arm_retrieval``'s own per-sample output
(:func:`verify_fast_path_against_flight`) before any corrected number is
produced, so the corrections inherit the flight's exact ranking conventions:
cosine over L2-normalised vectors, descending score, ties broken by ascending
bank id, K=5 majority vote with ties broken by highest mean cosine, and
recall@k over the ranked (never deduplicated) label sequence.

**Corrections.**

``meancenter`` -- the zero-cost modality-gap first move (survey item 17): L2-
normalise every vector, subtract the QUERY-side mean over that arm's own 60
query vectors from each query, subtract the KEY-side mean over that model's
own 900 bank vectors from each key, re-L2-normalise, re-score. Cosine is
scale-invariant, so the re-normalisation cannot change any ranking; it is
performed anyway so the reported scores are true cosines in the centred
space. ``meancenter-rawmean`` repeats the correction with means taken over
the RAW (un-normalised) vectors -- a sensitivity control on that one choice.

``key-mean-shift`` / ``key-zscore`` -- score standardisation (same survey
item). Standardising a SINGLE query's own 900 scores is a strictly increasing
affine map of those scores and therefore cannot reorder them
(:func:`per_query_zscore_is_rank_preserving` proves this empirically on the
landed matrices); the informative direction is the other axis. ``key-mean-
shift`` subtracts each KEY's own mean similarity across the 60 queries (the
hubness / mean-shift calibration correction); ``key-zscore`` additionally
divides by that key's own standard deviation. Both are TRANSDUCTIVE over the
query batch -- they read all 60 queries to score any one of them -- so they
are diagnostics of the score geometry, not a per-sample online policy.

``meancenter+key-mean-shift`` -- both corrections composed.

**Is centering a transductive read of the evaluation batch?** For the query
side, no: :func:`query_centroid_is_leave_one_out_equivalent` shows that
centering on the full-batch centroid and centering on the leave-one-out
centroid differ by a positive scalar factor ``n / (n - 1)`` and are therefore
IDENTICAL after re-L2-normalisation -- every cosine and every ranking is the
same. Query-side centering is a per-encoder, per-modality constant offset
that can be estimated once, offline, from any audio pool. The key side is
estimated purely from the 900 TRAIN bank vectors and never touches a query.
The two key-standardisation variants are different: they read all 60 queries
to score any one of them, so they are reported as score-geometry diagnostics
whose deployable form would estimate the per-key statistic from a train-side
query pool.

**Cone geometry.** :func:`cone_geometry` reports, per arm and per model, the
norm of the unit-space centroid (the cone-offset magnitude: 0 = isotropic,
1 = a degenerate ray), the cosine between the query centroid and the key
centroid, the centroid separation, and the mean of the full 60x900 cosine
matrix before and after centering -- the quantities that decide whether a low
audio cosine is a cone artifact or an information deficit.

Idempotence: every function here is a pure function of its inputs except the
thin CLI (:func:`main`), which performs all I/O.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

# Import-order guard (NOT cosmetic). As of study commit 418ec68 the package has
# a pre-existing import cycle: ``rails/__init__`` -> ``rails.consumption`` ->
# ``core.retrieval`` -> ``core/__init__`` -> ``core.driver.cli`` ->
# ``rails.probes.pslu_flight`` -> ``rails.adapters.slurp`` -> ``rails
# .consumption`` (still partially initialised) -> ImportError. Reaching
# ``core`` FIRST puts the partially-initialised package at a point where the
# submodule import inside ``rails.consumption`` resolves, so the cycle closes.
# The same defect currently stops ``scripts/pemb4r_read.py`` from importing at
# all; repairing it belongs to a task with authority over ``rails``/``core``,
# and this module -- a read-only re-analysis -- only routes around it.
from .. import core as _import_order_guard  # noqa: F401
from ..rails.probes import pemb4r_flight as flight
from ..rails.probes.pemb4r_flight import ARMS_BY_ID, AUDIO_ARM_IDS, TEXT_ARM_IDS
from . import pemb4r_read as read

REPORT_SCHEMA = "saea-pemb4r-meancenter-reanalysis-v1"

#: The consumed artifacts this module re-reads. Never re-flown here.
CONSUMED_FLIGHT_ATTEMPT_ID = "attempt-20260820T181837Z-3e6c8f"
CONSUMED_RETRIEVAL_PLAN_SHA256 = (
    "7150c6b3410de4cc883da7f5ef0798dd80e4beaf253037594e99ff8cf5cea768"
)
CONSUMED_READ_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-21-pemb4r-read"
)

#: Variant ids, in report order.
VARIANT_RAW = "raw"
VARIANT_MEANCENTER = "meancenter"
VARIANT_MEANCENTER_RAWMEAN = "meancenter-rawmean"
VARIANT_KEY_MEAN_SHIFT = "key-mean-shift"
VARIANT_KEY_ZSCORE = "key-zscore"
VARIANT_MEANCENTER_KEY_SHIFT = "meancenter+key-mean-shift"
VARIANT_IDS: tuple[str, ...] = (
    VARIANT_RAW,
    VARIANT_MEANCENTER,
    VARIANT_MEANCENTER_RAWMEAN,
    VARIANT_KEY_MEAN_SHIFT,
    VARIANT_KEY_ZSCORE,
    VARIANT_MEANCENTER_KEY_SHIFT,
)

#: Exact-reproduction tolerance. The baseline path reuses the consumed read's
#: own code, so the only expected difference is float formatting through JSON.
REPRODUCTION_TOLERANCE = 1e-12


class MeanCenterReanalysisError(RuntimeError):
    """An input artifact is missing or malformed, or a self-check tripped."""


# ---------------------------------------------------------------------------
# Vector plumbing.
# ---------------------------------------------------------------------------


def stack_vectors(vectors: Mapping[str, object]):
    """Return ``(sorted_ids, matrix)`` -- rows in ASCENDING id order.

    Ascending id order is load-bearing: ``pemb4r_flight._rank`` breaks score
    ties by ascending candidate id, and a stable argsort over an id-sorted
    matrix reproduces exactly that tie-break.
    """

    import numpy as np

    if not vectors:
        raise MeanCenterReanalysisError("stack_vectors: vectors must be non-empty")
    ids = tuple(sorted(vectors))
    matrix = np.asarray([np.asarray(vectors[key], dtype=np.float64) for key in ids], dtype=np.float64)
    if matrix.ndim != 2:
        raise MeanCenterReanalysisError("stack_vectors: vectors are not dimension-uniform")
    return ids, matrix


def l2_normalize_rows(matrix):
    import numpy as np

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.all(norms > 0.0):
        raise MeanCenterReanalysisError("l2_normalize_rows: a zero-norm vector cannot be normalised")
    return matrix / norms


def cosine_matrix(queries, keys):
    """Cosine of every query row against every key row."""

    return l2_normalize_rows(queries) @ l2_normalize_rows(keys).T


def mean_center(matrix, *, normalize_first: bool = True):
    """Subtract the row-mean of ``matrix`` from every row, then re-L2-normalise.

    ``normalize_first`` selects the mean's own space: unit-sphere (the
    standard modality-gap procedure, and the space in which ``||mean||`` is
    the interpretable cone-offset magnitude) or raw.
    """

    import numpy as np

    basis = l2_normalize_rows(matrix) if normalize_first else matrix
    centroid = basis.mean(axis=0)
    centred = basis - centroid
    norms = np.linalg.norm(centred, axis=1)
    if not np.all(norms > 0.0):
        raise MeanCenterReanalysisError("mean_center: a vector collapsed onto the centroid")
    return centred / norms[:, None], centroid


def key_mean_shift(scores):
    """Subtract each KEY's own mean score across the query batch (hubness)."""

    return scores - scores.mean(axis=0, keepdims=True)


def key_zscore(scores):
    """Standardise each KEY's own score distribution across the query batch."""

    import numpy as np

    centred = key_mean_shift(scores)
    std = scores.std(axis=0, keepdims=True)
    safe = np.where(std > 0.0, std, 1.0)
    return centred / safe


def query_centroid_is_leave_one_out_equivalent(matrix, *, tolerance: float = 1e-9) -> bool:
    """Is query-side mean-centering free of any batch-membership effect?

    Analytically it is. With ``n`` unit rows and centroid ``mu``, the
    leave-one-out centroid for row ``i`` is ``mu_i = (n*mu - x_i) / (n - 1)``,
    so ``x_i - mu_i = (n / (n - 1)) * (x_i - mu)`` -- a POSITIVE scalar
    multiple of the full-batch centred row, hence identical after
    re-L2-normalisation and therefore identical in every cosine and every
    ranking. That makes query-side centering a per-encoder constant offset,
    not a transductive read of the evaluation batch. This function checks the
    identity on the real matrix instead of asserting it.
    """

    import numpy as np

    unit = l2_normalize_rows(matrix)
    n = unit.shape[0]
    if n < 2:
        raise MeanCenterReanalysisError("query_centroid_is_leave_one_out_equivalent: need at least two rows")
    centroid = unit.mean(axis=0)
    full_batch = l2_normalize_rows(unit - centroid)
    loo_centroids = (n * centroid - unit) / (n - 1)
    leave_one_out = l2_normalize_rows(unit - loo_centroids)
    return bool(np.max(np.abs(full_batch - leave_one_out)) <= tolerance)


def per_query_zscore_is_rank_preserving(scores) -> bool:
    """Empirical proof that per-QUERY standardisation cannot reorder a query.

    Standardising one query's own scores is ``(s - mu) / sigma`` with
    ``sigma > 0`` -- a strictly increasing affine map, hence rank-preserving.
    This checks that claim against the real matrix rather than asserting it.
    """

    import numpy as np

    mu = scores.mean(axis=1, keepdims=True)
    sigma = scores.std(axis=1, keepdims=True)
    if not np.all(sigma > 0.0):
        raise MeanCenterReanalysisError("per_query_zscore_is_rank_preserving: a query has zero score variance")
    standardised = (scores - mu) / sigma
    raw_order = np.argsort(-scores, axis=1, kind="stable")
    z_order = np.argsort(-standardised, axis=1, kind="stable")
    return bool(np.array_equal(raw_order, z_order))


# ---------------------------------------------------------------------------
# Ranking that mirrors pemb4r_flight._rank exactly.
# ---------------------------------------------------------------------------


def topk_rows(
    scores,
    sample_ids: Sequence[str],
    bank_ids: Sequence[str],
    bank_labels: Mapping[str, str],
    *,
    k: int = flight.RETRIEVAL_K_PRIMARY,
) -> dict[str, dict[str, object]]:
    """Per-sample top-K rows in ``PerSampleRetrieval.as_json()`` shape.

    Mirrors ``pemb4r_flight._rank``: descending score, ties broken by
    ascending bank id (a STABLE argsort over id-sorted columns).
    """

    import numpy as np

    if scores.shape != (len(sample_ids), len(bank_ids)):
        raise MeanCenterReanalysisError("topk_rows: score matrix shape does not match the id sets")
    order = np.argsort(-scores, axis=1, kind="stable")[:, :k]
    rows: dict[str, dict[str, object]] = {}
    for row_index, sample_id in enumerate(sample_ids):
        columns = order[row_index]
        chosen_ids = tuple(bank_ids[column] for column in columns)
        chosen_scores = tuple(float(scores[row_index, column]) for column in columns)
        labels = tuple(bank_labels[bank_id] for bank_id in chosen_ids)
        rows[sample_id] = {
            "sample_id": sample_id,
            "top_k_bank_ids": list(chosen_ids),
            "top_k_cosines": list(chosen_scores),
            "top_k_labels": list(labels),
            "dedup_labels_k1": list(flight._dedup_labels(labels, 1)),
            "dedup_labels_k3": list(flight._dedup_labels(labels, 3)),
            "dedup_labels_k5": list(flight._dedup_labels(labels, 5)),
        }
    return rows


def retrieval_document_from_rows(rows_by_arm: Mapping[str, Mapping[str, dict[str, object]]]) -> dict[str, object]:
    """Wrap per-arm rows in the shape ``pemb4r_read.build_arm_report`` reads."""

    return {
        "schema": flight.RETRIEVAL_PLAN_SCHEMA,
        "k_primary": flight.RETRIEVAL_K_PRIMARY,
        "arms": {arm_id: {"per_sample": dict(rows)} for arm_id, rows in rows_by_arm.items()},
    }


def verify_fast_path_against_flight(
    arm_id: str,
    rows: Mapping[str, dict[str, object]],
    query_vectors: Mapping[str, object],
    bank_vectors: Mapping[str, object],
    bank_labels: Mapping[str, str],
    *,
    cosine_tolerance: float = 1e-12,
) -> tuple[str, ...]:
    """Compare :func:`topk_rows` output against ``build_arm_retrieval`` itself.

    Returns every disagreement; an empty tuple means the vectorised scorer is
    a faithful stand-in for the flight's own per-pair implementation, which is
    what licenses using it for the corrected variants.
    """

    reference = flight.build_arm_retrieval(arm_id, query_vectors, bank_vectors, bank_labels)
    problems: list[str] = []
    for sample_id, reference_row in sorted(reference.per_sample.items()):
        row = rows.get(sample_id)
        if row is None:
            problems.append(f"{arm_id}/{sample_id}: fast path produced no row")
            continue
        if tuple(row["top_k_bank_ids"]) != reference_row.top_k_bank_ids:
            problems.append(f"{arm_id}/{sample_id}: top_k_bank_ids differ from build_arm_retrieval")
        if tuple(row["top_k_labels"]) != reference_row.top_k_labels:
            problems.append(f"{arm_id}/{sample_id}: top_k_labels differ from build_arm_retrieval")
        deltas = [
            abs(float(a) - float(b))
            for a, b in zip(row["top_k_cosines"], reference_row.top_k_cosines)
        ]
        if deltas and max(deltas) > cosine_tolerance:
            problems.append(
                f"{arm_id}/{sample_id}: top_k_cosines differ by {max(deltas):.3e} > {cosine_tolerance:.0e}"
            )
    return tuple(problems)


# ---------------------------------------------------------------------------
# Cone geometry.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConeGeometry:
    arm_id: str
    model: str
    query_kind: str
    query_centroid_norm: float
    key_centroid_norm: float
    centroid_cosine: float
    centroid_separation: float
    mean_pair_cosine_raw: float
    mean_pair_cosine_centred: float
    mean_top1_cosine_raw: float
    mean_top1_cosine_centred: float
    query_raw_norm_mean: float
    query_raw_norm_std: float
    key_raw_norm_mean: float
    key_raw_norm_std: float


def cone_geometry(
    arm_id: str,
    queries,
    keys,
    *,
    mean_top1_raw: float,
    mean_top1_centred: float,
) -> ConeGeometry:
    """Unit-sphere centroid geometry for one arm's query set and key bank."""

    import numpy as np

    arm = ARMS_BY_ID[arm_id]
    unit_queries = l2_normalize_rows(queries)
    unit_keys = l2_normalize_rows(keys)
    query_centroid = unit_queries.mean(axis=0)
    key_centroid = unit_keys.mean(axis=0)
    query_norm = float(np.linalg.norm(query_centroid))
    key_norm = float(np.linalg.norm(key_centroid))
    centroid_cosine = (
        float(query_centroid @ key_centroid / (query_norm * key_norm))
        if query_norm > 0.0 and key_norm > 0.0
        else 0.0
    )
    centred_queries, _ = mean_center(queries)
    centred_keys, _ = mean_center(keys)
    query_raw_norms = np.linalg.norm(queries, axis=1)
    key_raw_norms = np.linalg.norm(keys, axis=1)
    return ConeGeometry(
        arm_id=arm_id,
        model=arm.model,
        query_kind=arm.query_kind,
        query_centroid_norm=query_norm,
        key_centroid_norm=key_norm,
        centroid_cosine=centroid_cosine,
        centroid_separation=float(np.linalg.norm(query_centroid - key_centroid)),
        mean_pair_cosine_raw=float((unit_queries @ unit_keys.T).mean()),
        mean_pair_cosine_centred=float((centred_queries @ centred_keys.T).mean()),
        mean_top1_cosine_raw=mean_top1_raw,
        mean_top1_cosine_centred=mean_top1_centred,
        query_raw_norm_mean=float(query_raw_norms.mean()),
        query_raw_norm_std=float(query_raw_norms.std()),
        key_raw_norm_mean=float(key_raw_norms.mean()),
        key_raw_norm_std=float(key_raw_norms.std()),
    )


# ---------------------------------------------------------------------------
# Variant score matrices.
# ---------------------------------------------------------------------------


def variant_scores(variant_id: str, queries, keys):
    """Score matrix for one correction variant. Pure; no gold anywhere."""

    if variant_id == VARIANT_RAW:
        return cosine_matrix(queries, keys)
    if variant_id == VARIANT_MEANCENTER:
        centred_q, _ = mean_center(queries)
        centred_k, _ = mean_center(keys)
        return centred_q @ centred_k.T
    if variant_id == VARIANT_MEANCENTER_RAWMEAN:
        centred_q, _ = mean_center(queries, normalize_first=False)
        centred_k, _ = mean_center(keys, normalize_first=False)
        return centred_q @ centred_k.T
    if variant_id == VARIANT_KEY_MEAN_SHIFT:
        return key_mean_shift(cosine_matrix(queries, keys))
    if variant_id == VARIANT_KEY_ZSCORE:
        return key_zscore(cosine_matrix(queries, keys))
    if variant_id == VARIANT_MEANCENTER_KEY_SHIFT:
        centred_q, _ = mean_center(queries)
        centred_k, _ = mean_center(keys)
        return key_mean_shift(centred_q @ centred_k.T)
    raise MeanCenterReanalysisError(f"variant_scores: unknown variant {variant_id!r}")


# ---------------------------------------------------------------------------
# Reproduction check against the consumed read.
# ---------------------------------------------------------------------------


_LANDED_FIELDS = (
    "vote_accuracy_k1",
    "vote_accuracy_k3",
    "vote_accuracy_k5",
    "recall_at_1",
    "recall_at_3",
    "recall_at_5",
    "n_samples",
)


def compare_against_landed(
    arm_reports: Mapping[str, read.Pemb4rArmReport],
    landed_verdict: Mapping[str, object],
    *,
    tolerance: float = REPRODUCTION_TOLERANCE,
) -> tuple[bool, tuple[str, ...], dict[str, dict[str, object]]]:
    """Field-by-field comparison of the recomputed baseline vs the landed read."""

    landed_arms = landed_verdict.get("arms")
    if not isinstance(landed_arms, Mapping):
        raise MeanCenterReanalysisError("landed verdict carries no 'arms' block")
    problems: list[str] = []
    table: dict[str, dict[str, object]] = {}
    for arm_id in flight.ARM_IDS:
        landed = landed_arms.get(arm_id)
        if not isinstance(landed, Mapping):
            problems.append(f"{arm_id}: absent from the landed verdict")
            continue
        recomputed = arm_reports[arm_id]
        row: dict[str, object] = {"arm_id": arm_id, "reproduced": True}
        for field in _LANDED_FIELDS:
            landed_value = landed.get(field)
            recomputed_value = getattr(recomputed, field)
            row[f"landed_{field}"] = landed_value
            row[f"recomputed_{field}"] = recomputed_value
            if landed_value is None or recomputed_value is None:
                if landed_value is not recomputed_value:
                    problems.append(f"{arm_id}.{field}: landed {landed_value!r} vs recomputed {recomputed_value!r}")
                    row["reproduced"] = False
                continue
            if abs(float(landed_value) - float(recomputed_value)) > tolerance:
                problems.append(
                    f"{arm_id}.{field}: landed {landed_value!r} vs recomputed {recomputed_value!r}"
                )
                row["reproduced"] = False
        landed_predictions = landed.get("predictions")
        if isinstance(landed_predictions, list):
            landed_gold = {
                str(entry["sample_id"]): str(entry["gold_scenario"]) for entry in landed_predictions
            }
            recomputed_gold = {p.sample_id: p.gold_scenario for p in recomputed.predictions}
            if landed_gold != recomputed_gold:
                problems.append(f"{arm_id}: scoring-side gold labels differ from the landed read")
                row["reproduced"] = False
            landed_votes = {
                str(entry["sample_id"]): str(entry["vote_label_k5"]) for entry in landed_predictions
            }
            recomputed_votes = {p.sample_id: p.vote_label_k5 for p in recomputed.predictions}
            differing = sorted(
                sample_id
                for sample_id in landed_votes
                if landed_votes.get(sample_id) != recomputed_votes.get(sample_id)
            )
            row["n_per_sample_vote_differences"] = len(differing)
            if differing:
                problems.append(f"{arm_id}: {len(differing)} per-sample K=5 vote label(s) differ from the landed read")
                row["reproduced"] = False
        table[arm_id] = row
    return (len(problems) == 0, tuple(problems), table)


# ---------------------------------------------------------------------------
# Top-level re-analysis.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reanalysis:
    reproduced: bool
    reproduction_problems: tuple[str, ...]
    reproduction_table: Mapping[str, dict[str, object]]
    fast_path_problems: tuple[str, ...]
    per_query_zscore_rank_preserving: Mapping[str, bool]
    query_centroid_leave_one_out_equivalent: Mapping[str, bool]
    variant_reports: Mapping[str, Mapping[str, read.Pemb4rArmReport]]
    geometry: Mapping[str, ConeGeometry]
    retrieval_plan_sha256: str


def build_reanalysis(
    *,
    query_vectors_by_arm: Mapping[str, Mapping[str, object]],
    bank_vectors_by_model: Mapping[str, Mapping[str, object]],
    bank_labels: Mapping[str, str],
    gold_scenarios: Mapping[str, str],
    landed_verdict: Mapping[str, object],
    retrieval_plan_sha256: str,
) -> Reanalysis:
    """Pure function of its inputs: reproduce first, then re-analyse."""

    rows_by_variant: dict[str, dict[str, dict[str, dict[str, object]]]] = {
        variant_id: {} for variant_id in VARIANT_IDS
    }
    fast_path_problems: list[str] = []
    zscore_invariance: dict[str, bool] = {}
    loo_equivalence: dict[str, bool] = {}
    mean_top1: dict[str, dict[str, float]] = {variant_id: {} for variant_id in VARIANT_IDS}
    stacked: dict[str, tuple] = {}

    for arm_id in flight.ARM_IDS:
        arm = ARMS_BY_ID[arm_id]
        query_vectors = query_vectors_by_arm[arm_id]
        bank_vectors = bank_vectors_by_model[arm.model]
        sample_ids, queries = stack_vectors(query_vectors)
        bank_ids, keys = stack_vectors(bank_vectors)
        stacked[arm_id] = (queries, keys)
        for variant_id in VARIANT_IDS:
            scores = variant_scores(variant_id, queries, keys)
            rows = topk_rows(scores, sample_ids, bank_ids, bank_labels)
            rows_by_variant[variant_id][arm_id] = rows
            mean_top1[variant_id][arm_id] = sum(
                float(row["top_k_cosines"][0]) for row in rows.values()
            ) / len(rows)
            if variant_id == VARIANT_RAW:
                fast_path_problems.extend(
                    verify_fast_path_against_flight(arm_id, rows, query_vectors, bank_vectors, bank_labels)
                )
                zscore_invariance[arm_id] = per_query_zscore_is_rank_preserving(scores)
                loo_equivalence[arm_id] = query_centroid_is_leave_one_out_equivalent(queries)

    variant_reports: dict[str, dict[str, read.Pemb4rArmReport]] = {}
    for variant_id in VARIANT_IDS:
        document = retrieval_document_from_rows(rows_by_variant[variant_id])
        variant_reports[variant_id] = {
            arm_id: read.build_arm_report(arm_id, document, gold_scenarios)
            for arm_id in flight.ARM_IDS
        }

    reproduced, problems, table = compare_against_landed(variant_reports[VARIANT_RAW], landed_verdict)

    geometry = {
        arm_id: cone_geometry(
            arm_id,
            stacked[arm_id][0],
            stacked[arm_id][1],
            mean_top1_raw=mean_top1[VARIANT_RAW][arm_id],
            mean_top1_centred=mean_top1[VARIANT_MEANCENTER][arm_id],
        )
        for arm_id in flight.ARM_IDS
    }

    return Reanalysis(
        reproduced=reproduced,
        reproduction_problems=problems,
        reproduction_table=table,
        fast_path_problems=tuple(fast_path_problems),
        per_query_zscore_rank_preserving=zscore_invariance,
        query_centroid_leave_one_out_equivalent=loo_equivalence,
        variant_reports=variant_reports,
        geometry=geometry,
        retrieval_plan_sha256=retrieval_plan_sha256,
    )


# ---------------------------------------------------------------------------
# Rendering.
# ---------------------------------------------------------------------------


def reanalysis_to_json(analysis: Reanalysis) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA,
        "probe_id": flight.PROBE_ID,
        "consumed": {
            "flight_attempt_id": CONSUMED_FLIGHT_ATTEMPT_ID,
            "read_dir": CONSUMED_READ_DIR,
            "retrieval_plan_sha256_expected": CONSUMED_RETRIEVAL_PLAN_SHA256,
            "retrieval_plan_sha256_observed": analysis.retrieval_plan_sha256,
            "retrieval_plan_sha256_matches": analysis.retrieval_plan_sha256
            == CONSUMED_RETRIEVAL_PLAN_SHA256,
        },
        "legality": {
            "model_contacts": 0,
            "artifact_status": "descriptive re-analysis of consumed artifacts",
            "gold_use": "scoring-side only, offline",
            "output_role": "design input; no verdict clause",
        },
        "reproduction": {
            "reproduced": analysis.reproduced,
            "problems": list(analysis.reproduction_problems),
            "fast_path_problems": list(analysis.fast_path_problems),
            "per_arm": analysis.reproduction_table,
        },
        "per_query_zscore_rank_preserving": dict(analysis.per_query_zscore_rank_preserving),
        "query_centroid_leave_one_out_equivalent": dict(analysis.query_centroid_leave_one_out_equivalent),
        "variants": {
            variant_id: {
                arm_id: {
                    "vote_accuracy_k1": report.vote_accuracy_k1,
                    "vote_accuracy_k3": report.vote_accuracy_k3,
                    "vote_accuracy_k5": report.vote_accuracy_k5,
                    "n_correct_k5": sum(1 for p in report.predictions if p.vote_correct_k5),
                    "recall_at_1": report.recall_at_1,
                    "recall_at_3": report.recall_at_3,
                    "recall_at_5": report.recall_at_5,
                    "mean_top1_score": sum(p.top_k_cosines[0] for p in report.predictions)
                    / max(1, len(report.predictions)),
                }
                for arm_id, report in analysis.variant_reports[variant_id].items()
            }
            for variant_id in VARIANT_IDS
        },
        "cone_geometry": {
            arm_id: {
                "model": row.model,
                "query_kind": row.query_kind,
                "query_centroid_norm": row.query_centroid_norm,
                "key_centroid_norm": row.key_centroid_norm,
                "centroid_cosine": row.centroid_cosine,
                "centroid_separation": row.centroid_separation,
                "mean_pair_cosine_raw": row.mean_pair_cosine_raw,
                "mean_pair_cosine_centred": row.mean_pair_cosine_centred,
                "mean_top1_cosine_raw": row.mean_top1_cosine_raw,
                "mean_top1_cosine_centred": row.mean_top1_cosine_centred,
                "query_raw_norm_mean": row.query_raw_norm_mean,
                "query_raw_norm_std": row.query_raw_norm_std,
                "key_raw_norm_mean": row.key_raw_norm_mean,
                "key_raw_norm_std": row.key_raw_norm_std,
            }
            for arm_id, row in analysis.geometry.items()
        },
    }


def render_reanalysis(analysis: Reanalysis) -> str:
    lines = [
        "P-EMB-4R per-modality mean-centering re-analysis (model-free, descriptive)",
        "=" * 84,
        "",
        "Consumed artifacts only: flight attempt "
        f"{CONSUMED_FLIGHT_ATTEMPT_ID}, read {CONSUMED_READ_DIR}.",
        "Zero model contacts. Gold used scoring-side only. Design input; no verdict clause.",
        "",
        f"retrieval_plan_sha256_matches={analysis.retrieval_plan_sha256 == CONSUMED_RETRIEVAL_PLAN_SHA256} "
        f"({analysis.retrieval_plan_sha256})",
        f"fast_path_problems={len(analysis.fast_path_problems)}",
        "",
        f"REPRODUCTION OF THE LANDED READ: {'PASS' if analysis.reproduced else 'FAIL'}",
    ]
    for arm_id in flight.ARM_IDS:
        row = analysis.reproduction_table.get(arm_id, {})
        lines.append(
            f"  [{arm_id}] reproduced={row.get('reproduced')} "
            f"vote_k5 landed={row.get('landed_vote_accuracy_k5')} recomputed={row.get('recomputed_vote_accuracy_k5')} "
            f"r@5 landed={row.get('landed_recall_at_5')} recomputed={row.get('recomputed_recall_at_5')} "
            f"vote_diffs={row.get('n_per_sample_vote_differences')}"
        )
    for problem in analysis.reproduction_problems:
        lines.append(f"  !! {problem}")
    lines.append("")
    lines.append(
        "per-query z-score rank-preserving: "
        + ", ".join(f"{arm_id}={value}" for arm_id, value in sorted(analysis.per_query_zscore_rank_preserving.items()))
    )
    lines.append(
        "query-centroid leave-one-out equivalent: "
        + ", ".join(
            f"{arm_id}={value}"
            for arm_id, value in sorted(analysis.query_centroid_leave_one_out_equivalent.items())
        )
    )
    lines.append("")

    for variant_id in VARIANT_IDS:
        lines.append(f"[{variant_id}]")
        for arm_id in flight.ARM_IDS:
            report = analysis.variant_reports[variant_id][arm_id]
            n_correct = sum(1 for p in report.predictions if p.vote_correct_k5)
            mean_top1 = sum(p.top_k_cosines[0] for p in report.predictions) / max(1, len(report.predictions))
            lines.append(
                f"  {arm_id:<7} vote_k5={report.vote_accuracy_k5:.4f} ({n_correct}/{report.n_samples}) "
                f"vote_k1={report.vote_accuracy_k1:.4f} vote_k3={report.vote_accuracy_k3:.4f} "
                f"r@1={report.recall_at_1:.4f} r@3={report.recall_at_3:.4f} r@5={report.recall_at_5:.4f} "
                f"mean_top1_score={mean_top1:+.4f}"
            )
        lines.append("")

    lines.append("Cone geometry (unit-sphere centroids)")
    lines.append(
        "  arm     kind   ||mu_q||  ||mu_k||  cos(mu_q,mu_k)  ||mu_q-mu_k||  mean_pair_raw  mean_pair_centred"
    )
    for arm_id in flight.ARM_IDS:
        row = analysis.geometry[arm_id]
        lines.append(
            f"  {arm_id:<7} {row.query_kind:<6} {row.query_centroid_norm:8.4f}  {row.key_centroid_norm:8.4f}  "
            f"{row.centroid_cosine:14.4f}  {row.centroid_separation:13.4f}  "
            f"{row.mean_pair_cosine_raw:13.4f}  {row.mean_pair_cosine_centred:17.4f}"
        )
    lines.append("")
    lines.append("Raw vector norms (are the landed vectors already unit-length?)")
    for arm_id in flight.ARM_IDS:
        row = analysis.geometry[arm_id]
        lines.append(
            f"  {arm_id:<7} query_norm={row.query_raw_norm_mean:.4f}+/-{row.query_raw_norm_std:.4f} "
            f"key_norm={row.key_raw_norm_mean:.4f}+/-{row.key_raw_norm_std:.4f}"
        )
    lines.append("")
    lines.append("Audio arms: " + ", ".join(AUDIO_ARM_IDS) + " | text controls: " + ", ".join(TEXT_ARM_IDS))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI (the only I/O in this module).
# ---------------------------------------------------------------------------


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pemb4r-meancenter-reanalysis",
        description=(
            "Model-free, descriptive re-analysis of the CONSUMED P-EMB-4R vectors under "
            "per-modality mean-centering and score standardisation. Reproduces the landed read "
            "first, then reports the corrected tables and the cone geometry. Zero model contacts."
        ),
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--embeddings-root", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--sample-manifest", type=Path, default=None)
    parser.add_argument("--landed-verdict", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    import hashlib
    import sys

    from ..data.lock import REPO_ROOT as _REPO_ROOT
    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import write_json_artifact
    from .pemb_read import gold_scenarios_for_run_a

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else _REPO_ROOT
    root = Path(args.embeddings_root) if args.embeddings_root else data_root()
    landed_verdict_path = args.landed_verdict or (repo_root / CONSUMED_READ_DIR / "verdict.json")
    sample_manifest_path = args.sample_manifest or (
        repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json"
    )

    try:
        lock = load_lock(umbrella_lock_path(repo_root))
        gold = gold_scenarios_for_run_a(
            lock, root, repo_root=repo_root, sample_manifest_path=sample_manifest_path
        )
        bank = flight.load_bank_manifest(root)
        bank_labels = {entry.bank_id: entry.gold_scenario for entry in bank.entries}
        bank_vectors = {model: flight.load_bank_vectors(root, model).vectors for model in flight.MODELS}
        query_vectors = {arm_id: flight.load_query_vectors(root, arm_id).vectors for arm_id in flight.ARM_IDS}
        retrieval_plan = flight.load_retrieval_plan(root)
        plan_sha256 = flight.retrieval_plan_document_sha256(retrieval_plan)
        landed_verdict = json.loads(Path(landed_verdict_path).read_text(encoding="utf-8"))
        if not isinstance(landed_verdict, Mapping):
            raise MeanCenterReanalysisError(f"{landed_verdict_path}: landed verdict must be a JSON object")
        analysis = build_reanalysis(
            query_vectors_by_arm=query_vectors,
            bank_vectors_by_model=bank_vectors,
            bank_labels=bank_labels,
            gold_scenarios=gold,
            landed_verdict=landed_verdict,
            retrieval_plan_sha256=plan_sha256,
        )
    except (MeanCenterReanalysisError, flight.Pemb4rFlightError, read.Pemb4rReadError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    document = reanalysis_to_json(analysis)
    document["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rendered = render_reanalysis(analysis)
    output_dir = Path(args.output_dir)
    write_json_artifact(output_dir / "meancenter-reanalysis.json", document)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote {output_dir / 'meancenter-reanalysis.json'}")
    return 0 if analysis.reproduced and not analysis.fast_path_problems else 1


__all__ = [
    "CONSUMED_FLIGHT_ATTEMPT_ID",
    "CONSUMED_READ_DIR",
    "CONSUMED_RETRIEVAL_PLAN_SHA256",
    "REPORT_SCHEMA",
    "REPRODUCTION_TOLERANCE",
    "VARIANT_IDS",
    "VARIANT_KEY_MEAN_SHIFT",
    "VARIANT_KEY_ZSCORE",
    "VARIANT_MEANCENTER",
    "VARIANT_MEANCENTER_KEY_SHIFT",
    "VARIANT_MEANCENTER_RAWMEAN",
    "VARIANT_RAW",
    "ConeGeometry",
    "MeanCenterReanalysisError",
    "Reanalysis",
    "build_reanalysis",
    "compare_against_landed",
    "cone_geometry",
    "cosine_matrix",
    "key_mean_shift",
    "key_zscore",
    "l2_normalize_rows",
    "main",
    "mean_center",
    "per_query_zscore_is_rank_preserving",
    "query_centroid_is_leave_one_out_equivalent",
    "reanalysis_to_json",
    "render_reanalysis",
    "retrieval_document_from_rows",
    "stack_vectors",
    "topk_rows",
    "variant_scores",
    "verify_fast_path_against_flight",
]


if __name__ == "__main__":  # pragma: no cover - thin CLI entry
    raise SystemExit(main())
