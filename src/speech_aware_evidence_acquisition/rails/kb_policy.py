"""C3: the first cross-task knowledge policy registered in the empty
``KNOWLEDGE_RANKERS`` / ``KNOWLEDGE_FUSERS`` / ``AGENT_CONTROLLERS``
registries (owner-approved 2026-08-23 knowledge-plane baseline program;
authority ``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md``
section 5, design basis section 1 -- the Q-K-V rulings).

Model-free by construction: every vector this module consumes (a query's
per-dimension embedding, a facet's per-dimension embedding) is INJECTED by
the caller through a plain callable/mapping; nothing here computes an
embedding, opens a model connection, or reads gold labels. The pipeline is
four independently testable, task-independent stages:

1. :func:`multidim_recall` -- cosine recall per vector-bearing dimension
   (e.g. ``content``/``speaker``) where both a query vector and a facet
   vector exist, union'd with prior-mass recall for metadata-only
   dimensions (``label``/``prior``, :data:`PRIOR_MASS_DIMENSIONS`) that have
   no vectors at all -- exactly the K-side split the ruling's Q-K-V section
   describes (content/speaker are embeddable; label/prior are TRAIN-derived
   statistics, "V ... carries priors and is modeled against the TRAIN set").
2. The ranker registered under :data:`RANK_POLICY_ID` -- a weighted sum of
   max cosine, max prior mass, and cross-dimension agreement, each term first
   brought onto one common scale by :func:`_dimension_scales` so the sum
   compares like with like, emitting a contract-valid, hash-bound
   :class:`~.knowledge.RankResult`. That normalisation is an exact identity
   on any dimension already inside its own bound, which is why it leaves the
   locked SLURP cell byte-unchanged; read :func:`_dimension_scales` for the
   defect it repairs and the proof.
3. The fuser registered under :data:`FUSE_POLICY_ID` -- percept admission
   (a cosine floor) over the top-``m`` ranked facets, then a coverage floor
   (every one of the top-``l`` distinct ``task_target``s gets >=1 value) and
   ceiling (<=``c`` values per ``task_target``), emitting a contract-valid
   :class:`~.knowledge.FusionDecision`.
4. The controller registered under :data:`CONTROLLER_POLICY_ID` -- a
   two-contact trajectory (direct decode, then acquire, then an
   evidence-conditioned decode) that blends a direct-decode label against
   the fused evidence's own label distribution via a discrete alpha weight.

Registry vs. run-time binding (why the controller factory below is
snapshot-optional): every ``core.base`` registry entry under
``AGENT_CONTROLLERS`` must satisfy ``rails.runner.AgentControllerFactory =
Callable[[str], AgentController]`` -- ONE argument, the sample id, with no
room for a per-run ``KnowledgeSnapshot`` (a load-time artifact this module
cannot know at import time). :func:`register_kb_policy_v1` therefore
registers a snapshot-free, maximally conservative default (it always
performs exactly the direct-decode contact and stops -- the same lawful
degenerate path :meth:`KbAlphaBlendController._advance_after_direct` already
takes when recall finds nothing to acquire). A real flight builds its OWN
snapshot-bound factory via :func:`make_kb_alpha_blend_controller_factory`
and passes it through a fresh ``core.base.Registry`` as
``controller_registry=`` to ``rails.runner.run_speech_native_agent_loop`` --
exactly the pattern this repository's own tests already use for every other
controller (``tests/unit/test_rails_runner.py``'s ``_controller_registry``
helper never relies on the bare global registry for scenario-specific
behaviour either).

Label vocabulary (task independence): the alpha-blend head only ever reads
``dimension == "label"`` facets that are directly associated with values
sharing exactly one non-``None`` ``task_target`` (:func:`_label_identities`)
-- for SLURP's scenario -> action -> intent hierarchy
(``rails.knowledge_build``) this selects exactly the leaf intent facets
(scenario/action facets carry no direct value association and are skipped);
for a flat single-level label task every label facet qualifies directly.
Nothing here reads a scenario/action/intent name, a slot schema, or any
other SLURP-specific vocabulary -- the same code path is exercised by this
module's own tests against both a 5-label and a 150-label synthetic
snapshot. The registered DEFAULT normalizer (:func:`default_label_normalizer`)
is the one place that departs from this: it parses a SLURP-shaped compact
JSON answer (``scenario``/``action``) to recover the identity it then
matches against :func:`_label_identities`'s own output. A task whose
answers are not shaped that way supplies its own ``normalizer`` -- the
``Normalizer`` injection point (module docstring stage 4) is unchanged.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.base import AGENT_CONTROLLERS, KNOWLEDGE_FUSERS, KNOWLEDGE_RANKERS
from .errors import RailsError
from .knowledge import (
    AgentStepTransition,
    FusionDecision,
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RankedFacet,
    RankResult,
    ValueBundle,
)
from .runner import AgentContactPlan, AgentController, AgentLoopAdvance, AgentRuntimeContext

RANK_POLICY_ID = "saea-rank-wcos-prior-agree-v1"
FUSE_POLICY_ID = "saea-fuse-supplyfilter-v1"
CONTROLLER_POLICY_ID = "saea-kb-alpha-blend-v1"

_DIRECT_CONTACT_ID = "direct-decode"
_EVIDENCE_CONTACT_ID = "evidence-decode"

# The two KB-BUILD dimensions (``rails.knowledge_build`` module docstring)
# that are TRAIN-derived statistics rather than embeddable payloads: they
# recall by prior mass, never by cosine. Any dimension not in this set is
# assumed vector-eligible (a task-independent default: a new dimension a
# future task introduces is cosine-recalled unless it is explicitly named
# here), matching ruling section 1.3's "K is multi-dimensional ... a further
# dimension" language.
PRIOR_MASS_DIMENSIONS = frozenset({"label", "prior"})

_CONFIG_SCHEMA = "saea-kb-policy-v1"
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_CONFIG_PATH = _REPO_ROOT / "configs" / "policy" / "kb-policy-v1.json"

Normalizer = Callable[[str, Mapping[str, str]], str | None]


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_policy_config(path: Path | None = None) -> dict[str, object]:
    """Load and shape-check the frozen knob table (module docstring)."""

    resolved = Path(path) if path is not None else DEFAULT_POLICY_CONFIG_PATH
    document = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping) or document.get("schema") != _CONFIG_SCHEMA:
        raise RailsError(f"kb-policy config {resolved} has an unexpected schema")
    for block in ("rank_weights", "recall", "fusion", "controller"):
        if not isinstance(document.get(block), Mapping):
            raise RailsError(f"kb-policy config {resolved} is missing block {block!r}")
    return dict(document)


@dataclass(frozen=True)
class RankWeights:
    """Weights for the ``saea-rank-wcos-prior-agree-v1`` ranker."""

    w_cos: float
    w_prior: float
    w_agree: float

    def validate(self) -> "RankWeights":
        for name in ("w_cos", "w_prior", "w_agree"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise RailsError(f"RankWeights.{name} must be a finite number")
        return self


@dataclass(frozen=True)
class FuseKnobs:
    """Knobs for the ``saea-fuse-supplyfilter-v1`` fuser.

    ``top_l`` is the ``l`` knob from the ruling/config file, renamed from
    the bare single letter to keep this module's own identifiers outside
    the ambiguous-name set this repository's ruff gate (E741, part of the
    pinned E7 selection) refuses.
    """

    tau: float
    m: int
    c: int
    top_l: int

    def validate(self) -> "FuseKnobs":
        if (
            isinstance(self.tau, bool)
            or not isinstance(self.tau, (int, float))
            or not math.isfinite(float(self.tau))
        ):
            raise RailsError("FuseKnobs.tau must be a finite number")
        for name in ("m", "c", "top_l"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise RailsError(f"FuseKnobs.{name} must be a positive int")
        return self


def rank_weights_from_config(config: Mapping[str, object]) -> RankWeights:
    block = config["rank_weights"]
    return RankWeights(
        w_cos=float(block["w_cos"]),
        w_prior=float(block["w_prior"]),
        w_agree=float(block["w_agree"]),
    ).validate()


def fuse_knobs_from_config(config: Mapping[str, object]) -> FuseKnobs:
    block = config["fusion"]
    return FuseKnobs(
        tau=float(block["tau"]),
        m=int(block["m"]),
        c=int(block["c"]),
        top_l=int(block["l"]),
    ).validate()


def top_k_per_dimension_from_config(config: Mapping[str, object]) -> int:
    return int(config["recall"]["top_k_per_dimension"])


def alpha_from_config(config: Mapping[str, object]) -> float:
    alpha = float(config["controller"]["alpha"])
    if not (0.0 <= alpha <= 1.0):
        raise RailsError("kb-policy config controller.alpha must be within [0, 1]")
    return alpha


# ---------------------------------------------------------------------------
# Stage 1: multi-dimensional recall
# ---------------------------------------------------------------------------


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not isinstance(a, Sequence) or not isinstance(b, Sequence):
        return 0.0
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
    norm_b = math.sqrt(sum(float(y) * float(y) for y in b))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _facet_prior_mass(
    facet: KeyFacet, values_by_facet: Mapping[str, Sequence[ValueBundle]]
) -> float:
    associated = values_by_facet.get(facet.facet_id, ())
    scores = [value.prior_score for value in associated if value.prior_score is not None]
    return max(scores) if scores else 0.0


def multidim_recall(
    snapshot: KnowledgeSnapshot,
    query_vectors: Mapping[str, Sequence[float] | None],
    facet_vectors: Callable[[str], Mapping[str, Sequence[float]]],
    top_k_per_dimension: int,
) -> dict[str, dict[str, float]]:
    """Recall candidate facets per dimension, union'd across dimensions.

    Cosine dimensions (anything not in :data:`PRIOR_MASS_DIMENSIONS`) recall
    a facet only when BOTH ``query_vectors[dimension]`` and
    ``facet_vectors(facet_id)[dimension]`` exist; :data:`PRIOR_MASS_DIMENSIONS`
    ("label"/"prior") recall by the max ``prior_score`` among the facet's
    directly associated values, independent of any vector. Each dimension's
    own candidate pool is truncated to its own top ``top_k_per_dimension``
    (score descending, ``facet_id`` ascending tie-break) BEFORE the union, so
    a facet with a strong single-dimension hit is never crowded out; the
    returned mapping's per-facet value carries only the dimensions that
    dimension actually admitted it under.
    """

    snapshot.validate()
    if (
        isinstance(top_k_per_dimension, bool)
        or not isinstance(top_k_per_dimension, int)
        or top_k_per_dimension <= 0
    ):
        raise RailsError("multidim_recall: top_k_per_dimension must be a positive int")
    if not isinstance(query_vectors, Mapping):
        raise RailsError("multidim_recall: query_vectors must be a mapping")
    if not callable(facet_vectors):
        raise RailsError("multidim_recall: facet_vectors must be callable")

    values_by_facet: dict[str, list[ValueBundle]] = {}
    for value in snapshot.values:
        for facet_id in value.associated_facet_ids:
            values_by_facet.setdefault(facet_id, []).append(value)

    dimensions = sorted({facet.dimension for facet in snapshot.facets})
    recalled: dict[str, dict[str, float]] = {}
    for dimension in dimensions:
        dim_facets = sorted(
            (facet for facet in snapshot.facets if facet.dimension == dimension),
            key=lambda facet: facet.facet_id,
        )
        scored: list[tuple[float, str]] = []
        if dimension in PRIOR_MASS_DIMENSIONS:
            for facet in dim_facets:
                mass = _facet_prior_mass(facet, values_by_facet)
                if mass > 0.0:
                    scored.append((mass, facet.facet_id))
        else:
            query_vector = query_vectors.get(dimension)
            if query_vector is None:
                continue
            for facet in dim_facets:
                candidate_vectors = facet_vectors(facet.facet_id)
                if not isinstance(candidate_vectors, Mapping):
                    raise RailsError(
                        "multidim_recall: facet_vectors must return a mapping"
                    )
                facet_vector = candidate_vectors.get(dimension)
                if facet_vector is None:
                    continue
                score = _cosine(query_vector, facet_vector)
                if score > 0.0:
                    scored.append((score, facet.facet_id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        for score, facet_id in scored[:top_k_per_dimension]:
            recalled.setdefault(facet_id, {})[dimension] = score
    return recalled


# ---------------------------------------------------------------------------
# Stage 2: weighted-cosine/prior/agreement ranker
# ---------------------------------------------------------------------------

# The scale every ranker dimension is expressed in. Cosine similarity is
# bounded by 1 as a theorem; the agreement term is a fraction of the recalled
# dimensions and is bounded by 1 by construction; a prior mass is INTENDED to
# be a conditional probability and so is bounded by 1 by construction too --
# whenever the KB builder that produced it actually nests its numerator inside
# its denominator. :func:`_dimension_scales` treats this number as the common
# scale, never as a knob.
_DIMENSION_SCORE_BOUND = 1.0


def _dimension_scales(
    recall_scores: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    """The per-dimension divisor that makes cross-dimension scores commensurable.

    THE DEFECT THIS REPAIRS (owner ruling 2026-08-25; authority
    ``docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/README.md``
    section "CORRECTION"). :func:`_rank_weighted_cosine_prior_agreement` sums
    ``w_cos * max_cosine + w_prior * max_prior + w_agree * agreement`` into ONE
    score. ``max_cosine`` and ``agreement`` cannot exceed 1, but ``max_prior``
    is whatever the KB builder's ratio happens to be, and the two builders in
    this repository do not agree about that:

    * ``rails.knowledge_build`` (SLURP) sets ``prior_score =
      intent_total_in_scenario / scenario_total`` and an intent is nested
      strictly inside its scenario, so the ratio is a genuine conditional
      probability -- measured sup over the pinned TRAIN snapshot
      ``e27b2745...`` is exactly **1.0**;
    * ``rails.knowledge_build_a2t`` (Audio2Tool) sets ``prior_score =
      tool_total / category_total`` where a tool's rows are counted across
      every domain while the denominator counts one (domain, category) only,
      so the ratio is NOT nested and NOT a probability -- measured sup over
      the pinned snapshot ``ec2f9ec4...`` is **4.1**, with 193 values above 1.

    Summing an unbounded quantity with a bounded one compares incommensurable
    things. On Audio2Tool the consequence was total: ``w_prior * 4.1 = 1.23``
    against a best ``w_cos * cos = 0.48``, so the ten prior-mass facets
    ``recall`` returns monopolised the fuser's ``top-m = 5`` window, the
    percept-admission gate (which reads only non-prior-mass dimensions) found
    nothing admissible, and NO content facet was admitted on any of 104 G1
    trajectories -- independently corroborated on 86 more. SLURP never
    exposed it because its sup is exactly at the bound.

    THE FIX. Every dimension is divided by ``max(1.0, sup_d)``, where ``sup_d``
    is that dimension's largest score over the recalled candidate set. After
    the division every dimension lands in the same ``[0, 1]`` range that
    cosine and agreement already occupied, so the weighted sum compares like
    with like. The rule is uniform -- prior-mass dimensions are not special
    cased -- deterministic given the recalled set, and parameter-free: the
    only constant is :data:`_DIMENSION_SCORE_BOUND`, which is the theoretical
    bound of the dimensions the weights were chosen against, not a tuned
    value.

    QUERY INDEPENDENCE, which is the property that disqualifies the other
    candidates. A divisor read off "whatever this query happened to recall"
    would give the same facet a different score from one trajectory to the
    next -- not cacheable, not auditable, not replayable. This one does not,
    and the argument is structural rather than empirical:

    * for a cosine dimension the divisor is the constant 1.0, because
      ``sup_d <= 1`` is a theorem and the floor takes over;
    * for a prior-mass dimension :func:`multidim_recall` reads no vector at
      all, so its candidate set and its scores are the same for every query
      against a given snapshot; and its truncation is score-descending, so
      the dimension's maximum can never be truncated away. The recalled
      supremum is therefore exactly the snapshot's own supremum for that
      dimension -- a per-snapshot constant.

    Reading the supremum off ``recall_scores`` rather than the snapshot is
    also the only option available at this boundary: the registered
    ``KNOWLEDGE_RANKERS`` signature hands the ranker a snapshot HASH, not a
    snapshot, and widening it would be a contract change.

    WHY THE FLOOR AT 1.0 RATHER THAN PLAIN MIN-MAX OR PLAIN MAX-NORMALISATION.
    Plain min-max over the recalled set would rescale a dimension that is
    already on the common scale, which (a) destroys the meaning of ``tau`` for
    the cosine dimension the fuser still thresholds on raw cosines, (b) maps
    the empirical minimum to 0 and so erases the difference between "a weak
    hit" and "no hit at all" -- a distinction this ranker relies on, since a
    facet recalled on one dimension carries no entry for the others -- and
    (c) is undefined when a dimension recalls a single candidate. Flooring the
    divisor at the bound keeps a well-behaved dimension untouched and only
    ever shrinks one that has escaped its own declared range. It also makes
    the divisor >= 1 by construction, so this function cannot divide by zero
    and cannot amplify a score. Plain max-normalisation (no floor) happens to
    behave identically on the two snapshots this repository has, only because
    SLURP's supremum sits exactly ON the bound; the floor makes that an
    invariant instead of a coincidence.

    The independent, zero-contact admission-scale sweep
    (``docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-admission-scale-sweep/sweep-report.json``)
    reached the same conclusion from the other direction: of the variants it
    graded, per-dimension supremum normalisation is the one it marks
    "PRINCIPLED FIX -- bounded, order-preserving, query-independent, one
    change", and it rejects query-dependent min-max, z-scoring, rank-based
    combination, and every ``m``-widening variant.

    CONSIDERED ALTERNATIVE: rank-based fusion (per-dimension rank, then
    reciprocal-rank combination, ``sum_d 1/(k + rank_d)``). It is the other
    principled answer to incommensurability and it is genuinely scale-free.
    It was rejected here for three reasons. It discards magnitude, so a
    cosine of 0.96 and one of 0.66 become indistinguishable whenever they are
    adjacent in rank, and this policy's whole downstream contract -- the
    fuser's ``tau`` admission, the controller's ``delta = cos_top1 -
    cos_direct`` signal -- is built on cosine MAGNITUDE. It introduces a new
    constant ``k`` that is not in the frozen knob table. And it cannot be an
    identity on the locked cell, which the repair below is required to be.

    THE IDENTITY PROPERTY (proof obligation of the repair). If every recalled
    dimension satisfies ``sup_d <= 1``, then every divisor is ``max(1.0,
    sup_d) == 1.0`` exactly, and IEEE-754 division by 1.0 is exact for every
    finite value: each candidate's per-dimension score, its ``max_cosine``,
    its ``max_prior`` and therefore its total score are bit-for-bit what the
    pre-repair ranker computed. The ordering, the :class:`RankResult` and its
    content hash, the :class:`FusionDecision` and the supplied value ids are
    consequently unchanged. This is exactly the SLURP regime -- cosine <= 1 is
    a theorem and the pinned TRAIN snapshot's prior sup is exactly 1.0 -- so
    the DEV-1000 locked baseline transfers untouched. See
    ``tests/unit/test_kb_policy_v1.py``'s replay of the sealed DEV-1000
    BLEND records for the empirical half of the same claim.

    AND THE PROPERTY IT RESTORES. Because a recalled facet carries entries
    only for the dimensions that admitted it, the agreement term is equal for
    every candidate whenever each is single-dimension, and cancels. Under the
    locked knob table (``configs/policy/kb-policy-v1-dev100.json``: ``w_cos``
    0.5, ``w_prior`` 0.3, ``tau`` 0.65) the post-repair supremum of the prior
    contribution is ``w_prior * 1.0 = 0.300``, strictly below ``w_cos * tau =
    0.325``. Every percept-admissible content facet therefore outranks every
    prior-mass facet, on ANY carrier, by construction rather than by luck.
    """

    sups: dict[str, float] = {}
    for dim_scores in recall_scores.values():
        for dimension, score in dim_scores.items():
            value = float(score)
            current = sups.get(dimension)
            if current is None or value > current:
                sups[dimension] = value
    return {
        dimension: (sup if sup > _DIMENSION_SCORE_BOUND else _DIMENSION_SCORE_BOUND)
        for dimension, sup in sups.items()
    }


def _rank_weighted_cosine_prior_agreement(
    weights: RankWeights,
    *,
    snapshot_sha256: str,
    query_state: QueryState,
    recall_scores: Mapping[str, Mapping[str, float]],
) -> RankResult:
    weights.validate()
    if not isinstance(recall_scores, Mapping):
        raise RailsError("rank: recall_scores must be a mapping")

    dims_total = len({dim for scores in recall_scores.values() for dim in scores})
    # Cross-dimension commensurability (see :func:`_dimension_scales`): an
    # identity transform on every dimension that already respects its own
    # bound, which is why the locked SLURP cell is byte-unchanged.
    scales = _dimension_scales(recall_scores)
    candidates: list[RankedFacet] = []
    for facet_id, dim_scores in recall_scores.items():
        cosine_scores = [
            float(score) / scales[dim]
            for dim, score in dim_scores.items()
            if dim not in PRIOR_MASS_DIMENSIONS
        ]
        prior_scores = [
            float(score) / scales[dim]
            for dim, score in dim_scores.items()
            if dim in PRIOR_MASS_DIMENSIONS
        ]
        max_cosine = max(cosine_scores) if cosine_scores else 0.0
        max_prior = max(prior_scores) if prior_scores else 0.0
        agreement = len(dim_scores) / dims_total if dims_total else 0.0
        score = (
            weights.w_cos * max_cosine
            + weights.w_prior * max_prior
            + weights.w_agree * agreement
        )
        candidates.append(RankedFacet(facet_id=facet_id, score=score))
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.facet_id))

    return RankResult(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state.content_hash(),
        ranking_policy_id=RANK_POLICY_ID,
        candidates=tuple(candidates),
    ).validate()


def rank_wcos_prior_agree_factory(
    weights: RankWeights | None = None,
) -> Callable[..., RankResult]:
    """Factory over :class:`RankWeights` (module docstring stage 2). With no
    ``weights``, loads :data:`DEFAULT_POLICY_CONFIG_PATH`."""

    resolved = (
        weights if weights is not None else rank_weights_from_config(load_policy_config())
    ).validate()

    def ranker(
        *,
        snapshot_sha256: str,
        query_state: QueryState,
        recall_scores: Mapping[str, Mapping[str, float]],
    ) -> RankResult:
        return _rank_weighted_cosine_prior_agreement(
            resolved,
            snapshot_sha256=snapshot_sha256,
            query_state=query_state,
            recall_scores=recall_scores,
        )

    return ranker


# ---------------------------------------------------------------------------
# Stage 3: percept-admission + coverage fuser
# ---------------------------------------------------------------------------


def _fuse_supply_filter(
    knobs: FuseKnobs,
    *,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    query_state: QueryState,
    rank_result: RankResult,
    recall_scores: Mapping[str, Mapping[str, float]],
) -> FusionDecision:
    knobs.validate()
    rank_result.validate()

    top_m_ids = tuple(candidate.facet_id for candidate in rank_result.candidates[: knobs.m])
    top_m_id_set = set(top_m_ids)

    def admitted(facet_id: str) -> bool:
        dim_scores = recall_scores.get(facet_id, {})
        cosine_scores = [
            score for dim, score in dim_scores.items() if dim not in PRIOR_MASS_DIMENSIONS
        ]
        return bool(cosine_scores) and max(cosine_scores) >= knobs.tau

    admitted_facets = {facet_id for facet_id in top_m_id_set if admitted(facet_id)}
    facet_score = {candidate.facet_id: candidate.score for candidate in rank_result.candidates}
    already_visible = set(query_state.retrieved_value_ids)

    # Group percept-admitted, not-yet-visible, task_target-bearing candidate
    # values by task_target, each tagged with the score of its best
    # admitted supporting facet.
    candidates_by_target: dict[str, list[tuple[float, ValueBundle, str]]] = {}
    for value in snapshot.values:
        if value.value_id in already_visible or value.task_target is None:
            continue
        supporting = set(value.associated_facet_ids) & admitted_facets
        if not supporting:
            continue
        best_facet = max(supporting, key=lambda facet_id: (facet_score.get(facet_id, 0.0), facet_id))
        candidates_by_target.setdefault(value.task_target, []).append(
            (facet_score.get(best_facet, 0.0), value, best_facet)
        )

    ranked_targets = sorted(
        candidates_by_target,
        key=lambda target: (
            -max(score for score, _value, _facet in candidates_by_target[target]),
            target,
        ),
    )
    top_l_targets = ranked_targets[: knobs.top_l]

    selected_value_ids: list[str] = []
    supporting_facet_ids: set[str] = set()
    for target in top_l_targets:
        ranked_candidates = sorted(
            candidates_by_target[target],
            key=lambda item: (-item[0], item[1].value_id),
        )
        for _score, value, facet_id in ranked_candidates[: knobs.c]:
            selected_value_ids.append(value.value_id)
            supporting_facet_ids.add(facet_id)

    return FusionDecision(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state.content_hash(),
        rank_result_sha256=rank_result.content_hash(),
        fusion_policy_id=FUSE_POLICY_ID,
        supporting_facet_ids=tuple(sorted(supporting_facet_ids)),
        selected_value_ids=tuple(sorted(set(selected_value_ids))),
    ).validate()


def fuse_supplyfilter_factory(
    knobs: FuseKnobs | None = None,
) -> Callable[..., FusionDecision]:
    """Factory over :class:`FuseKnobs` (module docstring stage 3). With no
    ``knobs``, loads :data:`DEFAULT_POLICY_CONFIG_PATH`."""

    resolved = (
        knobs if knobs is not None else fuse_knobs_from_config(load_policy_config())
    ).validate()

    def fuser(
        *,
        snapshot: KnowledgeSnapshot,
        snapshot_sha256: str,
        query_state: QueryState,
        rank_result: RankResult,
        recall_scores: Mapping[str, Mapping[str, float]],
    ) -> FusionDecision:
        return _fuse_supply_filter(
            resolved,
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            query_state=query_state,
            rank_result=rank_result,
            recall_scores=recall_scores,
        )

    return fuser


# ---------------------------------------------------------------------------
# Stage 4: alpha-blend controller
# ---------------------------------------------------------------------------


def _parse_scenario_action(response_text: str) -> tuple[str | None, str | None]:
    """The response's OWN parsed ``scenario``/``action`` fields -- gold is
    never consulted, and this reads only the model's answer text. Deferred
    import: ``rails.kb_policy`` stays import-time task-independent (module
    docstring "Label vocabulary") -- only actually calling the DEFAULT
    normalizer pulls in the SLU-shaped response parser, and only a task
    whose answers are shaped that way ever exercises this path at all."""

    from ..reproduction.slurp_scoring import parse_slu_response  # noqa: PLC0415

    scenario, action, _entities, parsed = parse_slu_response(response_text)
    if not parsed:
        return None, None
    return scenario, action


def default_label_normalizer(
    response_text: str, label_targets: Mapping[str, str]
) -> str | None:
    """Recovers a label facet's identity from the response's OWN parsed
    ``scenario``/``action`` fields -- never from gold, and never from a
    label facet's prose text. ``label_targets`` is a facet_id -> intent-
    identity mapping (:func:`_label_identities`'s own output, e.g. facet_id
    -> ``"alarm_query"``), not representation text: the parsed
    ``scenario``/``action`` are joined as ``f"{scenario}_{action}"`` and
    matched EXACTLY against ``label_targets``'s values. Ties (more than one
    facet_id sharing the same identity) are broken by ``facet_id``
    ascending.

    Repairs the label-identity binding defect the damage-channel analysis
    found (``docs/readiness/2026-08-24-dev100-damage-channel-analysis.md``
    sections 4.2 and 9): the previous implementation matched a label
    facet's prose ``representation`` (e.g. "Intent 'alarm_query'
    (scenario='alarm', action='query'); 130 TRAIN utterances...") as a
    substring of the response, but the task contract's answers are compact
    JSON, which never contains that prose -- the match fired on 0/100
    flown responses, so the alpha-blend's ``(1 - alpha)`` protect-direct
    term was never live and retain-primary could never fire. Matching the
    answer's own parsed identity instead recovers a label facet on 64/100
    flown direct answers (measured).

    Known, intentionally unaddressed residual (same sections): of the
    remaining 36/100, 5 name a real TRAIN intent only with ``scenario``
    and ``action`` exchanged, and 31 name a pair that is not a TRAIN
    intent in either order. This normalizer does NOT special-case the
    swap: the analysis measured the swap count but explicitly declined to
    endorse it as an unambiguous repair, leaving "widen the label
    vocabulary, tolerate the field swap, or tighten the answer format" as
    a separate, later design question. Those 36 samples stay dead-direct
    (this function returns ``None``) exactly as they did before this
    repair."""

    if not isinstance(response_text, str):
        return None
    scenario, action = _parse_scenario_action(response_text)
    if scenario is None or action is None:
        return None
    identity = f"{scenario}_{action}"
    matches = sorted(
        facet_id for facet_id, target in label_targets.items() if target == identity
    )
    return matches[0] if matches else None


def _label_identities(snapshot: KnowledgeSnapshot) -> dict[str, str]:
    """facet_id -> task_target for every label-dimension facet directly
    associated with values that share exactly one non-None task_target
    (module docstring "Label vocabulary")."""

    values_by_facet: dict[str, list[ValueBundle]] = {}
    for value in snapshot.values:
        for facet_id in value.associated_facet_ids:
            values_by_facet.setdefault(facet_id, []).append(value)
    identities: dict[str, str] = {}
    for facet in snapshot.facets:
        if facet.dimension != "label":
            continue
        associated = values_by_facet.get(facet.facet_id, ())
        targets = {value.task_target for value in associated if value.task_target is not None}
        if len(targets) == 1:
            identities[facet.facet_id] = next(iter(targets))
    return identities


def _fused_label_scores(
    label_targets: Mapping[str, str],
    values_by_id: Mapping[str, ValueBundle],
    selected_value_ids: Sequence[str],
    rank_result: RankResult,
) -> dict[str, float]:
    """Normalized-fused-label-score: for each label facet, the strongest
    ranked-facet score among the selected values whose ``task_target``
    matches that label, normalized to sum to 1 across labels (all zero when
    nothing was selected)."""

    facet_score = {candidate.facet_id: candidate.score for candidate in rank_result.candidates}
    raw: dict[str, float] = {}
    for label_id, target in label_targets.items():
        best = 0.0
        for value_id in selected_value_ids:
            value = values_by_id[value_id]
            if value.task_target != target:
                continue
            strength = max(
                (facet_score.get(facet_id, 0.0) for facet_id in value.associated_facet_ids),
                default=0.0,
            )
            best = max(best, strength)
        raw[label_id] = best
    total = sum(raw.values())
    if total <= 0.0:
        return {label_id: 0.0 for label_id in raw}
    return {label_id: score / total for label_id, score in raw.items()}


def _blend_scores(
    label_targets: Mapping[str, str],
    fused_label_scores: Mapping[str, float],
    direct_label: str | None,
    alpha: float,
) -> dict[str, float]:
    return {
        label_id: alpha * fused_label_scores.get(label_id, 0.0)
        + (1.0 - alpha) * (1.0 if label_id == direct_label else 0.0)
        for label_id in label_targets
    }


def _argmax_labels(blended: Mapping[str, float]) -> tuple[str, ...]:
    if not blended:
        return ()
    best = max(blended.values())
    return tuple(
        sorted(label_id for label_id, score in blended.items() if abs(score - best) <= 1e-9)
    )


class KbAlphaBlendController:
    """The :data:`CONTROLLER_POLICY_ID` controller (module docstring stage 4).

    Two contacts on the acquire path: ``direct-decode`` (zero values), then
    -- once recall/rank/fuse finds something to acquire, and the direct
    label is not already the pre-evidence blend's UNIQUE winner -- an
    ``evidence-decode`` contact (the fused values supplied as SUPPLY). A tie
    that merely includes the direct label is dispatched too, so evidence can
    break it. ``snapshot=None`` yields the
    conservative, always-direct-decode degenerate mode used by the module's
    default registry entry (module docstring); a real caller always
    constructs this through :func:`make_kb_alpha_blend_controller_factory`.
    """

    def __init__(
        self,
        *,
        snapshot: KnowledgeSnapshot | None,
        query_vectors: Mapping[str, Sequence[float] | None],
        facet_vectors: Callable[[str], Mapping[str, Sequence[float]]],
        normalizer: Normalizer,
        ranker: Callable[..., RankResult],
        fuser: Callable[..., FusionDecision],
        alpha: float,
        top_k_per_dimension: int,
    ) -> None:
        if not (0.0 <= alpha <= 1.0):
            raise RailsError("KbAlphaBlendController: alpha must be within [0, 1]")
        if (
            isinstance(top_k_per_dimension, bool)
            or not isinstance(top_k_per_dimension, int)
            or top_k_per_dimension <= 0
        ):
            raise RailsError(
                "KbAlphaBlendController: top_k_per_dimension must be a positive int"
            )
        self._snapshot = snapshot
        self._query_vectors = dict(query_vectors)
        self._facet_vectors = facet_vectors
        self._normalizer = normalizer
        self._ranker = ranker
        self._fuser = fuser
        self._alpha = float(alpha)
        self._top_k = top_k_per_dimension
        self._values_by_id: dict[str, ValueBundle] = (
            {} if snapshot is None else {value.value_id: value for value in snapshot.values}
        )
        self._label_targets: dict[str, str] = (
            {} if snapshot is None else _label_identities(snapshot)
        )
        self._direct_label: str | None = None
        self._pending_best_labels: tuple[str, ...] = ()
        # Test/provenance observability only -- never consulted by the
        # runner or by this controller's own control flow.
        self.last_winner_label: str | None = None

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if self._snapshot is not None and (
            context.knowledge_snapshot_sha256 != self._snapshot.content_hash()
        ):
            raise RailsError(
                "KbAlphaBlendController is bound to a different KnowledgeSnapshot"
            )
        return AgentContactPlan(
            contact_id=_DIRECT_CONTACT_ID,
            query_state_sha256=context.query_state.content_hash(),
            purpose="direct-decode",
            instruction=(
                "Decide under the task contract already given above. Answer "
                "using only the speech query; no external knowledge has been "
                "supplied yet."
            ),
            key_representation_id=f"{CONTROLLER_POLICY_ID}:direct",
            matcher_policy_id=CONTROLLER_POLICY_ID,
            decoding_params={},
        )

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: object,
    ) -> AgentLoopAdvance:
        if not isinstance(response_text, str):
            raise RailsError(
                "KbAlphaBlendController requires a single string response per contact"
            )
        if contact.contact_id == _DIRECT_CONTACT_ID:
            return self._advance_after_direct(context, contact, response_text)
        if contact.contact_id == _EVIDENCE_CONTACT_ID:
            return self._advance_after_evidence(context, contact, response_text)
        raise RailsError(
            f"KbAlphaBlendController received an unknown contact id {contact.contact_id!r}"
        )

    def _stop(
        self, context: AgentRuntimeContext, contact: AgentContactPlan
    ) -> AgentLoopAdvance:
        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=None,
            action_kind="stop",
            action_target_refs=(),
            new_value_ids=(),
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(),
            dropped_agent_state_ids=(),
        )
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
            final_response_contact_id=contact.contact_id,
        )

    def _advance_after_direct(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: str,
    ) -> AgentLoopAdvance:
        self._direct_label = self._normalizer(response_text, self._label_targets)

        if self._snapshot is None or not self._label_targets:
            return self._stop(context, contact)

        recall_scores = multidim_recall(
            self._snapshot, self._query_vectors, self._facet_vectors, self._top_k
        )
        if not recall_scores:
            return self._stop(context, contact)

        rank_result = self._ranker(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            query_state=context.query_state,
            recall_scores=recall_scores,
        )
        fusion_decision = self._fuser(
            snapshot=self._snapshot,
            snapshot_sha256=context.knowledge_snapshot_sha256,
            query_state=context.query_state,
            rank_result=rank_result,
            recall_scores=recall_scores,
        )
        if not fusion_decision.selected_value_ids:
            return self._stop(context, contact)

        fused_label_scores = _fused_label_scores(
            self._label_targets,
            self._values_by_id,
            fusion_decision.selected_value_ids,
            rank_result,
        )
        blended = _blend_scores(
            self._label_targets, fused_label_scores, self._direct_label, self._alpha
        )
        best_labels = _argmax_labels(blended)

        if best_labels == (self._direct_label,):
            # Retain-primary safety default (module docstring): the
            # direct-decode label uniquely wins the blend without needing
            # evidence at all -- no tie, nothing to break.
            # rails.runner._resolve_final_agent_response can only ever
            # select the response of the contact that JUST completed, so
            # "retain the direct-decode response" is realized here, before
            # an evidence-conditioned contact is ever dispatched, rather
            # than by re-selecting an earlier wave later (structurally
            # impossible once a later wave has run). A TIE that merely
            # includes direct_label among several best_labels is NOT
            # retained here -- it is dispatched to evidence-decode so
            # "tie-break by the evidence-decode answer" (module docstring)
            # has a real answer to consult; see _advance_after_evidence.
            return self._stop(context, contact)

        self._pending_best_labels = best_labels

        next_state = QueryState(
            query_id=context.query_state.query_id,
            query_sample_id=context.query_state.query_sample_id,
            speech_packet_id=context.query_state.speech_packet_id,
            speech_packet_sha256=context.query_state.speech_packet_sha256,
            use_split_identity_hash=context.query_state.use_split_identity_hash,
            loop_step=context.query_state.loop_step + 1,
            visible_facet_ids=context.query_state.visible_facet_ids,
            agent_state_ids=context.query_state.agent_state_ids,
            retrieved_value_ids=tuple(
                sorted(
                    set(context.query_state.retrieved_value_ids)
                    | set(fusion_decision.selected_value_ids)
                )
            ),
        ).validate()

        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=next_state.content_hash(),
            action_kind="acquire",
            action_target_refs=("kb-policy-v1:recall-rank-fuse",),
            new_value_ids=fusion_decision.selected_value_ids,
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(),
            dropped_agent_state_ids=(),
        )
        next_contact = AgentContactPlan(
            contact_id=_EVIDENCE_CONTACT_ID,
            query_state_sha256=next_state.content_hash(),
            purpose="evidence-decode",
            instruction=(
                "Decide under the task contract already given above, now "
                "considering the retrieved evidence. Answer using the speech "
                "query together with the supplied knowledge evidence."
            ),
            key_representation_id=f"{CONTROLLER_POLICY_ID}:evidence",
            matcher_policy_id=CONTROLLER_POLICY_ID,
            decoding_params={},
        )
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=next_state,
            new_agent_states=(),
            next_contact=next_contact,
            rank_result=rank_result,
            fusion_decision=fusion_decision,
        )

    def _advance_after_evidence(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: str,
    ) -> AgentLoopAdvance:
        evidence_label = self._normalizer(response_text, self._label_targets)
        best_labels = self._pending_best_labels
        if evidence_label in best_labels:
            self.last_winner_label = evidence_label
        elif best_labels:
            self.last_winner_label = best_labels[0]
        else:
            self.last_winner_label = None
        # rails.runner._resolve_final_agent_response can only ever select
        # the response of the contact that just completed, so this wave's
        # own text is the only legal final answer once this point is
        # reached. This wave is only ever reached when the pre-evidence
        # blend was NOT a unique direct-decode win (the
        # `best_labels == (self._direct_label,)` gate in
        # _advance_after_direct already retained the direct response for
        # that case, before this contact was ever dispatched). The common
        # case is `winner == evidence_label`, evidence-decode's own answer
        # confirming the numeric winner (a clean win, or a tie the evidence
        # answer broke). The residual case -- winner equals neither
        # response's normalized label (a multi-way tie the evidence answer
        # did not resolve, or direct_label itself surviving a tie the
        # evidence answer disagreed with) -- still legally returns this
        # wave's own real, evidence-grounded response text; there is no
        # legal alternative once this wave has run.
        return self._stop(context, contact)


def make_kb_alpha_blend_controller_factory(
    *,
    snapshot: KnowledgeSnapshot,
    query_vectors_by_sample: Mapping[str, Mapping[str, Sequence[float] | None]] | None = None,
    facet_vectors: Callable[[str], Mapping[str, Sequence[float]]] | None = None,
    normalizer: Normalizer | None = None,
    config: Mapping[str, object] | None = None,
    rank_weights: RankWeights | None = None,
    fuse_knobs: FuseKnobs | None = None,
    alpha: float | None = None,
    top_k_per_dimension: int | None = None,
) -> Callable[[str], AgentController]:
    """Build a snapshot-bound ``Callable[[str], AgentController]`` factory
    (module docstring "Registry vs. run-time binding"). Every keyword falls
    back to :func:`load_policy_config` when omitted; an explicit
    ``rank_weights``/``fuse_knobs``/``alpha``/``top_k_per_dimension``
    overrides only that one knob, without requiring the whole config.
    ``query_vectors_by_sample``/``facet_vectors`` are the INJECTED vectors
    (module docstring) -- omitted, every dimension recalls by prior mass
    only (never a model contact, never fabricated cosine)."""

    snapshot.validate()
    needs_config = config is None and any(
        value is None for value in (rank_weights, fuse_knobs, alpha, top_k_per_dimension)
    )
    resolved_config = config if config is not None else (load_policy_config() if needs_config else None)
    resolved_weights = (
        rank_weights if rank_weights is not None else rank_weights_from_config(resolved_config)
    )
    resolved_knobs = (
        fuse_knobs if fuse_knobs is not None else fuse_knobs_from_config(resolved_config)
    )
    resolved_alpha = alpha if alpha is not None else alpha_from_config(resolved_config)
    resolved_top_k = (
        top_k_per_dimension
        if top_k_per_dimension is not None
        else top_k_per_dimension_from_config(resolved_config)
    )
    resolved_normalizer = normalizer if normalizer is not None else default_label_normalizer
    resolved_query_vectors_by_sample = dict(query_vectors_by_sample or {})
    resolved_facet_vectors = (
        facet_vectors if facet_vectors is not None else (lambda facet_id: {})
    )

    ranker = rank_wcos_prior_agree_factory(resolved_weights)
    fuser = fuse_supplyfilter_factory(resolved_knobs)

    def factory(sample_id: str) -> AgentController:
        return KbAlphaBlendController(
            snapshot=snapshot,
            query_vectors=resolved_query_vectors_by_sample.get(sample_id, {}),
            facet_vectors=resolved_facet_vectors,
            normalizer=resolved_normalizer,
            ranker=ranker,
            fuser=fuser,
            alpha=resolved_alpha,
            top_k_per_dimension=resolved_top_k,
        )

    return factory


def _default_controller_factory(sample_id: str) -> AgentController:
    """Module-level default entry for ``AGENT_CONTROLLERS[CONTROLLER_POLICY_ID]``
    (module docstring "Registry vs. run-time binding")."""

    return KbAlphaBlendController(
        snapshot=None,
        query_vectors={},
        facet_vectors=lambda facet_id: {},
        normalizer=default_label_normalizer,
        ranker=rank_wcos_prior_agree_factory(RankWeights(w_cos=0.0, w_prior=0.0, w_agree=0.0)),
        fuser=fuse_supplyfilter_factory(FuseKnobs(tau=1.0, m=1, c=1, top_l=1)),
        alpha=0.5,
        top_k_per_dimension=1,
    )


def register_kb_policy_v1() -> None:
    """Idempotently register the ranker/fuser/controller factories into the
    shared ``core.base`` registries. Safe to call more than once (e.g. a
    second import of this module, or a direct re-call from a test) -- a name
    already present is left untouched rather than raising
    ``core.base.CoreError``'s duplicate-name refusal."""

    if RANK_POLICY_ID not in KNOWLEDGE_RANKERS.names():
        KNOWLEDGE_RANKERS.register(RANK_POLICY_ID, rank_wcos_prior_agree_factory)
    if FUSE_POLICY_ID not in KNOWLEDGE_FUSERS.names():
        KNOWLEDGE_FUSERS.register(FUSE_POLICY_ID, fuse_supplyfilter_factory)
    if CONTROLLER_POLICY_ID not in AGENT_CONTROLLERS.names():
        AGENT_CONTROLLERS.register(CONTROLLER_POLICY_ID, _default_controller_factory)


register_kb_policy_v1()


__all__ = [
    "CONTROLLER_POLICY_ID",
    "DEFAULT_POLICY_CONFIG_PATH",
    "FUSE_POLICY_ID",
    "PRIOR_MASS_DIMENSIONS",
    "RANK_POLICY_ID",
    "FuseKnobs",
    "KbAlphaBlendController",
    "Normalizer",
    "RankWeights",
    "alpha_from_config",
    "default_label_normalizer",
    "fuse_knobs_from_config",
    "fuse_supplyfilter_factory",
    "load_policy_config",
    "make_kb_alpha_blend_controller_factory",
    "multidim_recall",
    "rank_weights_from_config",
    "rank_wcos_prior_agree_factory",
    "register_kb_policy_v1",
    "top_k_per_dimension_from_config",
]
