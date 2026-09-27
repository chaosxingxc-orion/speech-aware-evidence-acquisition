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
   max cosine, max prior mass, and agreement (the cross-dimension fraction,
   or, when the recall carries an :data:`AGREEMENT_DIMENSIONS` entry, that
   supplied per-row signal instead), each term first
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

import itertools
import json
import math
import operator
import threading
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

#: WAVE R7: the two CONTROL turns of ``saea-kb-alpha-blend-v1``, lifted out of
#: ``KbAlphaBlendController`` verbatim so the fold below and the controller
#: send the same bytes. Changing either changes both, which is the point.
_ALPHA_BLEND_INSTRUCTIONS = {
    "direct": (
        "Decide under the task contract already given above. Answer "
        "using only the speech query; no external knowledge has been "
        "supplied yet."
    ),
    "evidence": (
        "Decide under the task contract already given above, now "
        "considering the retrieved evidence. Answer using the speech "
        "query together with the supplied knowledge evidence."
    ),
}

RANK_POLICY_ID = "saea-rank-wcos-prior-agree-v1"
FUSE_POLICY_ID = "saea-fuse-supplyfilter-v1"
ASSOCIATED_VALUES_FUSE_POLICY_ID = "saea-fuse-associated-values-v1"
#: Knowledge-wave item W3 (owner decision 164): the supply-filter selection
#: with a PER-TARGET cap and a TOTAL width, so a block of exemplars can
#: carry at most ``c`` values of one task target while still delivering
#: ``top_l`` values. See :func:`select_target_capped`.
TARGET_CAP_FUSE_POLICY_ID = "saea-fuse-supplyfilter-target-cap-v1"
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

#: The reserved recall dimension the EXEMPLAR-INTENT AGREEMENT signal travels
#: on. No snapshot declares it and no builder emits it: a facet carries it
#: only when the caller MERGES a pre-computed, hash-pinned per-row agreement
#: table into the recall scores (``rails.phase_supply``'s ``agreement_source``,
#: produced by ``scripts/build_slurp_intent_exemplar_agreement.py``). Each
#: score is the share of the row's own top-``k`` exemplar recall whose frozen
#: build-time ``task_target`` equals this facet's target: a fraction in
#: ``[0, 1]``, self-excluded, speech-keyed, and gold-free.
EXEMPLAR_INTENT_AGREEMENT_DIMENSION = "agreement:exemplar-intent"

#: Dimensions the ranker reads as its AGREEMENT term rather than as a cosine
#: or a prior mass. Symmetrical with :data:`PRIOR_MASS_DIMENSIONS`: a
#: dimension named here contributes to neither ``max_cosine`` nor
#: ``max_prior``, is not counted in the cross-dimension total, and is not a
#: percept-admission cosine for either fuser.
AGREEMENT_DIMENSIONS = frozenset({EXEMPLAR_INTENT_AGREEMENT_DIMENSION})

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


def _l2_norm(vector: Sequence[float]) -> float:
    """The L2 norm of ``vector`` in the ONE arithmetic every cosine in this
    module is built from: ``math.sqrt`` of the builtin ``sum`` of the squares
    in the vector's own element order. :func:`_cosine` and the cached path
    inside :func:`multidim_recall` both come here, so a norm computed once
    and reused is the SAME float as a norm recomputed for every pair (the
    KU-S3 preregistration's section 5 "bit-exact 3x")."""

    return math.sqrt(sum(float(x) * float(x) for x in vector))


def _cosine_with_norms(
    a: Sequence[float], b: Sequence[float], norm_a: float, norm_b: float
) -> float:
    """``dot(a, b) / (norm_a * norm_b)``, ``0.0`` when either norm is not
    positive. The caller guarantees ``a`` and ``b`` are non-empty sequences
    of one length and that each norm is :func:`_l2_norm` of its vector."""

    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    return dot / (norm_a * norm_b)


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine of ONE pair, both norms computed here. This is the reference
    every vectorised analysis in this repository pins itself to, and its
    value is bitwise the value :func:`multidim_recall` scores through the
    key-norm cache below: same guards, same :func:`_l2_norm`, same
    :func:`_cosine_with_norms`."""

    if not isinstance(a, Sequence) or not isinstance(b, Sequence):
        return 0.0
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    return _cosine_with_norms(a, b, _l2_norm(a), _l2_norm(b))


class _KeyNormCache:
    """L2 norms of KEY vectors, each computed once per vector OBJECT.

    WHY (KU-S3 preregistration, section 5). :func:`multidim_recall` scores
    every content facet of the bound snapshot for every sample -- 11,514
    vectors of 2,048 floats on SLURP -- and the per-pair :func:`_cosine`
    recomputed BOTH L2 norms for every pair, which priced the pre-flight seed
    at a measured 2.28 s per sample of single-threaded CPU while the resident
    serving session idled. The key vectors do not change between samples, so
    their norms are the same floats every time; caching them removes two of
    the three passes per pair and changes no value, because :func:`_l2_norm`
    is the one norm arithmetic and a float computed once is the float
    computed again. Sharding, approximating and reducing ``k`` are the fixes
    the preregistration forbids; this is the one it names.

    KEYED BY the vector object's identity (``id``), with the object itself
    held in the entry so a hit is a hit on the SAME object: an ``id`` recycled
    after garbage collection can never alias another vector. Only immutable
    ``tuple`` vectors are cached (``rails.phase_supply.load_sealed_vectors``
    yields tuples); a ``list`` is recomputed on every call exactly as before,
    so an in-place mutation between calls can never return a stale norm.

    SCOPED TO one key set. After a recall that touched key vectors,
    :meth:`retain` keeps exactly the vectors that recall touched and drops
    every other entry, so the cache holds one key file's norms -- the flight's
    bound snapshot -- and never accumulates across key sets or pins more than
    the most recent one. Concurrent recalls over the same key set touch the
    same objects and retain the same entries; a miss under any interleaving
    recomputes the identical float. The lock only serialises mutation.
    """

    __slots__ = ("_entries", "_lock")

    def __init__(self) -> None:
        self._entries: dict[int, tuple[tuple[float, ...], float]] = {}
        self._lock = threading.Lock()

    def norm(self, vector: Sequence[float]) -> float:
        if type(vector) is not tuple:
            return _l2_norm(vector)
        key = id(vector)
        entry = self._entries.get(key)
        if entry is not None and entry[0] is vector:
            return entry[1]
        value = _l2_norm(vector)
        with self._lock:
            self._entries[key] = (vector, value)
        return value

    def retain(self, touched: set[int]) -> None:
        with self._lock:
            if touched != self._entries.keys():
                self._entries = {
                    key: entry for key, entry in self._entries.items() if key in touched
                }

    def __len__(self) -> int:
        return len(self._entries)


#: The one key-norm cache :func:`multidim_recall` consults. Module-level
#: because the provider that calls recall (``rails.knowledge_provider.
#: KbFacetProvider``) is rebuilt per decision while the key vectors it is
#: handed are the same objects for the whole flight.
_KEY_NORMS = _KeyNormCache()


# ---------------------------------------------------------------------------
# The vectorised pre-selection: the exact loop's scores, a fraction of its time
# ---------------------------------------------------------------------------

#: The widening, in cosine units, of the vectorised pre-selection in
#: :func:`_preselected_exact_scores`. The candidate set is every row whose
#: BLAS cosine reaches ``max(k-th BLAS cosine, 0) - 2 * slack``; the proof in
#: that function's docstring needs ``slack`` to bound the largest possible
#: disagreement between a BLAS cosine and the builtin-``sum`` cosine of the
#: same pair, which is ``2 * gamma_n + 4u`` (``u = 2**-53``,
#: ``gamma_n = n*u / (1 - n*u)``) for width ``n``: 4.6e-13 at the 2,048-wide
#: SLURP vectors and under 2.4e-10 at :data:`_PRESELECT_MAX_WIDTH`. 1e-9 keeps a
#: factor of four over the widest width admitted.
_PRESELECT_SLACK = 1e-9

#: The widest vector the slack above is proven for; a wider one is scored by
#: the exact loop.
_PRESELECT_MAX_WIDTH = 1 << 20

#: Every positive norm the pre-selection admits (key and query) lies in this
#: range, so no dot product overflows (``|dot| <= 2**800``) and underflowed
#: products are negligible against ``norm_q * norm_k >= 2**-800``: the rounding
#: bound above then holds as stated. A norm outside it (never seen on a sealed,
#: L2-normalised vector file) sends the dimension to the exact loop.
_PRESELECT_NORM_RANGE = (2.0**-400, 2.0**400)


class _KeyMatrix:
    """One key set as a read-only float64 matrix, or a remembered refusal.

    ``vectors`` holds the key vector OBJECTS the matrix was built from, in row
    order, so a lookup matches by identity (the same tuples, never an equal
    copy) and an ``id`` can never be recycled under it. ``matrix is None``
    records a key set the pre-selection refused (a non-float component, a
    non-finite value, a norm out of range) so the refusal is not re-derived
    on every recall. ``norm_values`` are :func:`_l2_norm` floats -- the very
    floats the exact loop divides by.
    """

    __slots__ = ("vectors", "matrix", "norms", "norm_values")

    def __init__(self, vectors, matrix, norms, norm_values) -> None:
        self.vectors = vectors
        self.matrix = matrix
        self.norms = norms
        self.norm_values = norm_values


class _KeyMatrixCache:
    """The parsed key matrices, built once per key set per process.

    The key vectors of a flight are the same tuple objects for its whole life
    (``rails.phase_supply.load_sealed_vectors`` loads each file once), so the
    float64 matrix the pre-selection multiplies is too. Bounded to the four
    most recently used key sets -- a flight recalls against one or two -- so
    alternating stores never rebuild and a long-lived process never pins a
    retired key set. Lookups compare row objects by identity; builds are
    serialised so two rows arriving together build one matrix, not two.
    """

    __slots__ = ("_entries", "_lock", "_build_lock", "_capacity")

    def __init__(self, capacity: int = 4) -> None:
        self._entries: list[_KeyMatrix] = []
        self._lock = threading.Lock()
        self._build_lock = threading.Lock()
        self._capacity = capacity

    def get(self, vectors: tuple) -> _KeyMatrix | None:
        with self._lock:
            for index, entry in enumerate(self._entries):
                if len(entry.vectors) == len(vectors) and all(
                    map(operator.is_, entry.vectors, vectors)
                ):
                    if index:
                        self._entries.insert(0, self._entries.pop(index))
                    return entry
        return None

    def get_or_build(self, vectors: tuple) -> _KeyMatrix:
        entry = self.get(vectors)
        if entry is not None:
            return entry
        with self._build_lock:
            entry = self.get(vectors)
            if entry is None:
                entry = _build_key_matrix(vectors)
                with self._lock:
                    self._entries.insert(0, entry)
                    del self._entries[self._capacity :]
        return entry

    def __len__(self) -> int:
        return len(self._entries)


def _norm_admitted(value: float) -> bool:
    low, high = _PRESELECT_NORM_RANGE
    return value == 0.0 or low <= value <= high


def _build_key_matrix(vectors: tuple) -> _KeyMatrix:
    """The float64 matrix of ``vectors`` (tuples of one width), or a refusal.

    Only builtin ``float`` components are admitted: they convert to float64
    exactly, which is the premise of the rounding bound. Norms come from
    :data:`_KEY_NORMS`, i.e. :func:`_l2_norm`, the exact loop's own floats.
    """

    import numpy as np  # noqa: PLC0415 -- kept off the package's import path

    refused = _KeyMatrix(vectors, None, None, None)
    if set(map(type, itertools.chain.from_iterable(vectors))) - {float}:
        return refused
    matrix = np.array(vectors, dtype=np.float64)
    if (
        matrix.ndim != 2
        or matrix.shape[0] != len(vectors)
        or not np.isfinite(matrix).all()
    ):
        return refused
    norm_values = tuple(_KEY_NORMS.norm(vector) for vector in vectors)
    if not all(_norm_admitted(value) for value in norm_values):
        return refused
    norms = np.array(norm_values, dtype=np.float64)
    matrix.flags.writeable = False
    norms.flags.writeable = False
    return _KeyMatrix(vectors, matrix, norms, norm_values)


#: The one key-matrix cache :func:`multidim_recall` consults.
_KEY_MATRICES = _KeyMatrixCache()


def _preselected_exact_scores(
    query_vector: Sequence[float],
    query_norm: float,
    facet_ids: Sequence[str],
    vectors: tuple,
    top_k: int,
) -> list[tuple[float, str]] | None:
    """The ``(score, facet_id)`` pairs of every row that can reach the top
    ``top_k``, each scored by the EXACT loop's own arithmetic, in row order --
    or ``None`` when the pre-selection does not apply (the caller then runs
    the exact loop over every row, as before).

    WHY. The exact loop scores every key with a builtin-``sum`` dot product:
    9,354 x 2,048 multiplications in the interpreter, 1.1-1.4 s per row on
    the SLURP exemplar store, run on the one event loop every in-flight row
    shares (owner decision 159's gap decomposition). A BLAS product does the
    same sweep in milliseconds, but in a different summation order, so its
    floats differ from the exact loop's in the last bits and a near-tie could
    swap. Nothing a BLAS float decides is delivered: it only chooses which
    rows the exact loop re-scores.

    THE PROOF that the delivered top ``k`` is unchanged. Let ``s`` be a row's
    exact score and ``t`` its BLAS score, both divided by the same float
    ``fl(norm_q * norm_k)``; ``|s - t| <= delta`` with ``delta`` =
    :data:`_PRESELECT_SLACK` (see there). Let ``T`` be the ``k``-th largest
    ``t`` (``-inf`` when there are at most ``k`` rows) and admit every row
    with ``t >= max(T, 0) - 2 * delta``.

    * A row the exact loop keeps has ``s > 0``, so ``t > -delta``: admitted
      whenever ``T <= delta``.
    * When ``T > delta``, the ``k`` rows with ``t >= T`` all have
      ``s >= T - delta > 0``, so the exact loop's ``k``-th score is at least
      ``T - delta``; every row it keeps has ``s`` at least that, hence
      ``t >= T - 2 * delta``: admitted.

    So every row of the exact top ``k`` -- ties included, since equal ``s``
    means equal treatment -- is re-scored here by :func:`_cosine_with_norms`
    with the same query norm and the same key norm, giving the same float;
    rows are returned in row order, so the caller's stable
    ``(-score, facet_id)`` sort and ``[:k]`` truncation yield the same list,
    the same scores and the same order the exact loop yields. Rows admitted
    beyond the top ``k`` are exact too and are cut by the same truncation.
    """

    if len(query_vector) > _PRESELECT_MAX_WIDTH:
        return None
    if any(type(x) is not float for x in query_vector):
        return None
    if query_norm == 0.0:
        # _cosine_with_norms answers 0.0 for every pair and 0.0 is never
        # admitted: the exact loop would keep nothing.
        return []
    if not _norm_admitted(query_norm):
        return None
    try:
        import numpy as np  # noqa: PLC0415 -- kept off the package's import path
    except ImportError:  # pragma: no cover - numpy ships with every study environment
        return None
    entry = _KEY_MATRICES.get_or_build(vectors)
    if entry.matrix is None or entry.matrix.shape[1] != len(query_vector):
        return None
    query = np.array(query_vector, dtype=np.float64)
    dots = entry.matrix @ query
    approx = np.full(dots.shape, -np.inf)
    np.divide(dots, entry.norms * query_norm, out=approx, where=entry.norms > 0.0)
    count = approx.shape[0]
    floor = 0.0
    if count > top_k:
        floor = max(float(np.partition(approx, count - top_k)[count - top_k]), 0.0)
    rows = np.flatnonzero(approx >= floor - 2.0 * _PRESELECT_SLACK)
    scored: list[tuple[float, str]] = []
    for row in rows.tolist():
        score = _cosine_with_norms(
            query_vector, vectors[row], query_norm, entry.norm_values[row]
        )
        if score > 0.0:
            scored.append((score, facet_ids[row]))
    return scored


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
    touched: set[int] = set()
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
            # The query norm ONCE per query and dimension, each key norm ONCE
            # per key vector across every query (:data:`_KEY_NORMS`). The
            # guards are :func:`_cosine`'s own, in its order: a pair it would
            # have scored 0.0 is skipped here, and 0.0 was never admitted.
            query_is_vector = isinstance(query_vector, Sequence) and len(query_vector) > 0
            query_norm = _l2_norm(query_vector) if query_is_vector else 0.0
            pair_ids: list[str] = []
            pair_vectors: list[Sequence[float]] = []
            # ``type(...) is dict`` / ``is tuple`` short-circuit the ABC
            # checks for the types every sealed table uses (a dict IS a
            # Mapping, a tuple IS a Sequence); any other type still takes the
            # full check, so what is admitted and refused is unchanged.
            for facet in dim_facets:
                candidate_vectors = facet_vectors(facet.facet_id)
                if type(candidate_vectors) is not dict and not isinstance(
                    candidate_vectors, Mapping
                ):
                    raise RailsError(
                        "multidim_recall: facet_vectors must return a mapping"
                    )
                facet_vector = candidate_vectors.get(dimension)
                if facet_vector is None:
                    continue
                if (
                    not query_is_vector
                    or (
                        type(facet_vector) is not tuple
                        and not isinstance(facet_vector, Sequence)
                    )
                    or len(facet_vector) != len(query_vector)
                ):
                    continue
                pair_ids.append(facet.facet_id)
                pair_vectors.append(facet_vector)
                touched.add(id(facet_vector))
            # Immutable key vectors (every sealed file) take the vectorised
            # pre-selection, which returns the exact loop's own scores for
            # every row that can reach the top k; anything else -- a list, a
            # non-float component, a non-finite value -- takes the exact loop.
            preselected = (
                _preselected_exact_scores(
                    query_vector,
                    query_norm,
                    pair_ids,
                    tuple(pair_vectors),
                    top_k_per_dimension,
                )
                if pair_vectors
                and all(type(vector) is tuple for vector in pair_vectors)
                else None
            )
            if preselected is not None:
                scored.extend(preselected)
            else:
                for facet_id, facet_vector in zip(pair_ids, pair_vectors):
                    score = _cosine_with_norms(
                        query_vector,
                        facet_vector,
                        query_norm,
                        _KEY_NORMS.norm(facet_vector),
                    )
                    if score > 0.0:
                        scored.append((score, facet_id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        for score, facet_id in scored[:top_k_per_dimension]:
            recalled.setdefault(facet_id, {})[dimension] = score
    if touched:
        _KEY_NORMS.retain(touched)
    return recalled


def multidim_segment_recall(
    snapshot: KnowledgeSnapshot,
    query_segments: Sequence[Mapping[str, Sequence[float] | None]],
    facet_vectors: Callable[[str], Mapping[str, Sequence[float]]],
    top_k_per_dimension: int,
) -> dict[str, dict[str, float]]:
    """Union each segment's existing per-dimension top-k candidates, then
    retain each admitted facet's maximum score per dimension before ranking.

    The existing segment recall keeps its cosine arithmetic and facet-id tie
    order; chronological segment order cannot alter this max merge.
    """

    if not isinstance(query_segments, Sequence) or isinstance(query_segments, (str, bytes)):
        raise RailsError("multidim_segment_recall: query_segments must be a sequence")
    if not query_segments:
        raise RailsError("multidim_segment_recall: query_segments must be non-empty")
    merged: dict[str, dict[str, float]] = {}
    for segment in query_segments:
        if not isinstance(segment, Mapping):
            raise RailsError("multidim_segment_recall: each segment must be a mapping")
        recalled = multidim_recall(
            snapshot, segment, facet_vectors, top_k_per_dimension
        )
        for facet_id, scores in recalled.items():
            target = merged.setdefault(facet_id, {})
            for dimension, score in scores.items():
                prior = target.get(dimension)
                if prior is None or score > prior:
                    target[dimension] = score
    return merged


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


def cosine_dimension_items(
    dim_scores: Mapping[str, float],
) -> list[tuple[str, float]]:
    """``(dimension, score)`` for this candidate's COSINE dimensions: every
    dimension that is neither a prior mass (:data:`PRIOR_MASS_DIMENSIONS`) nor
    an agreement signal (:data:`AGREEMENT_DIMENSIONS`).

    ONE definition for the three sites that need it -- the ranker's
    ``max_cosine`` and both fusers' percept admission -- so an agreement score
    can never be read as a cosine by one of them and not the others. With no
    agreement dimension present it yields exactly the pairs each site walked
    inline before, in the same order, so it is an exact identity on every
    recall this repository has flown.
    """

    return [
        (dimension, float(score))
        for dimension, score in dim_scores.items()
        if dimension not in PRIOR_MASS_DIMENSIONS
        and dimension not in AGREEMENT_DIMENSIONS
    ]


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

    # THE AGREEMENT TERM HAS TWO SOURCES, and which one is in force is a
    # property of the RECALL, never of a weight (authority: the 2026-09-26
    # intent-boundary retrieval read,
    # ``docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md``
    # sections 3 and 6).
    #
    #   * NO candidate carries an :data:`AGREEMENT_DIMENSIONS` entry -- every
    #     recall this repository has flown to date -- and the term is the
    #     CROSS-DIMENSION FRACTION it has always been: the share of the
    #     recalled dimensions that admitted this candidate. This is
    #     byte-for-byte the pre-change arithmetic, because ``agreement_dims``
    #     is then empty, ``dims_total`` counts exactly the dimensions it
    #     counted before, and the fraction is computed from the same
    #     ``len(dim_scores)``.
    #   * SOME candidate carries one -- only when a caller merged a
    #     pre-computed, hash-pinned agreement table into the recall -- and the
    #     term is THAT SIGNAL: this candidate's own agreement score, or 0.0
    #     when the signal gives it none. An intent that received no vote is a
    #     ZERO vote, not a missing input; a missing INPUT is refused upstream,
    #     in ``rails.knowledge_provider.KbFacetProvider.candidates``, never
    #     scored as zero here.
    #
    # Replacing rather than adding is deliberate. The cross-dimension fraction
    # is a CONSTANT on a single-dimension channel -- 1.0 for every candidate,
    # so it cannot affect the order -- and the channel this signal was
    # measured for recalls one dimension; summing the two would make one
    # weight mean two different things at once.
    agreement_dims = {
        dim
        for scores in recall_scores.values()
        for dim in scores
        if dim in AGREEMENT_DIMENSIONS
    }
    dims_total = len(
        {
            dim
            for scores in recall_scores.values()
            for dim in scores
            if dim not in AGREEMENT_DIMENSIONS
        }
    )
    # Cross-dimension commensurability (see :func:`_dimension_scales`): an
    # identity transform on every dimension that already respects its own
    # bound, which is why the locked SLURP cell is byte-unchanged.
    scales = _dimension_scales(recall_scores)
    candidates: list[RankedFacet] = []
    for facet_id, dim_scores in recall_scores.items():
        cosine_scores = [
            score / scales[dim]
            for dim, score in cosine_dimension_items(dim_scores)
        ]
        prior_scores = [
            float(score) / scales[dim]
            for dim, score in dim_scores.items()
            if dim in PRIOR_MASS_DIMENSIONS
        ]
        max_cosine = max(cosine_scores) if cosine_scores else 0.0
        max_prior = max(prior_scores) if prior_scores else 0.0
        if agreement_dims:
            supplied = [
                float(score)
                for dim, score in dim_scores.items()
                if dim in AGREEMENT_DIMENSIONS
            ]
            agreement = max(supplied) if supplied else 0.0
        else:
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
        # Percept admission is a COSINE floor, so it reads cosine dimensions
        # only: an agreement score is not evidence that this row's speech
        # matched this key (:func:`cosine_dimension_items`).
        cosine_scores = [
            score for _dim, score in cosine_dimension_items(recall_scores.get(facet_id, {}))
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


def fuse_associated_values_factory(
    knobs: FuseKnobs | None = None,
) -> Callable[..., FusionDecision]:
    """Supply associated content without requiring an answer-bearing target.

    Admit the first m ranked facets by cosine threshold. Traverse them in rank
    order, select at most c new values per facet in value-ID order, and stop at
    top_l values overall. A value shared by facets is supplied once. Existing
    visible values consume neither budget. Keep target-based fusion unchanged.
    """
    if knobs is None:
        raise RailsError("associated-value fusion requires explicit FuseKnobs")
    resolved = knobs.validate()

    def fuser(
        *,
        snapshot: KnowledgeSnapshot,
        snapshot_sha256: str,
        query_state: QueryState,
        rank_result: RankResult,
        recall_scores: Mapping[str, Mapping[str, float]],
    ) -> FusionDecision:
        rank_result.validate()
        visible = set(query_state.retrieved_value_ids)
        selected: list[str] = []
        supporting: list[str] = []
        values_by_facet: dict[str, list[str]] = {}
        for value in snapshot.values:
            if value.value_id in visible:
                continue
            for facet_id in value.associated_facet_ids:
                values_by_facet.setdefault(facet_id, []).append(value.value_id)
        seen = set(visible)
        for candidate in rank_result.candidates[:resolved.m]:
            facet_id = candidate.facet_id
            # A cosine floor, never an agreement floor
            # (:func:`cosine_dimension_items`).
            cosines = [
                score
                for _dimension, score in cosine_dimension_items(
                    recall_scores.get(facet_id, {})
                )
            ]
            if not cosines or max(cosines) < resolved.tau:
                continue
            count = 0
            for value_id in sorted(values_by_facet.get(facet_id, ())):
                if value_id in seen:
                    continue
                selected.append(value_id)
                seen.add(value_id)
                count += 1
                if count == resolved.c or len(selected) == resolved.top_l:
                    break
            if count:
                supporting.append(facet_id)
            if len(selected) == resolved.top_l:
                break
        return FusionDecision(
            snapshot_sha256=snapshot_sha256,
            query_state_sha256=query_state.content_hash(),
            rank_result_sha256=rank_result.content_hash(),
            fusion_policy_id=ASSOCIATED_VALUES_FUSE_POLICY_ID,
            supporting_facet_ids=tuple(supporting),
            selected_value_ids=tuple(selected),
        ).validate()

    return fuser


def select_target_capped(
    ranked: Sequence[tuple[str, float]],
    *,
    targets_by_facet: Mapping[str, Sequence[tuple[str, str]]],
    per_target_cap: int,
    total: int,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The W3 selection rule as a pure function (owner decision 164).

    ``ranked`` is the admitted candidate list in RANK ORDER as
    ``(facet_id, score)``; ``targets_by_facet`` maps a facet id to the
    ``(value_id, task_target)`` pairs it supports, each list in value-id
    order. Walk the facets in rank order and, within a facet, its values in
    value-id order; take a value unless its task target already holds
    ``per_target_cap`` taken values or the value was already taken; stop at
    ``total`` values. Returns ``(selected value ids in selection order,
    supporting facet ids in rank order)``.

    With ``per_target_cap >= total`` this is exactly the first ``total``
    values of the admitted ranking, which on a one-value-per-facet store is
    the flown ``saea-fuse-supplyfilter-v1`` selection at ``m = c = top_l``
    (``tests/unit/test_kb_policy_target_cap.py`` proves it). The offline
    tuning read (``scripts/analysis/slurp_w3_contrast_cap_offline.py``)
    imports THIS function, so the registered numbers and the flown selection
    are one rule.
    """

    for name, value in (("per_target_cap", per_target_cap), ("total", total)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise RailsError(f"select_target_capped: {name} must be a positive int")
    taken: list[str] = []
    seen: set[str] = set()
    supporting: list[str] = []
    per_target: dict[str, int] = {}
    for facet_id, _score in ranked:
        took_here = False
        for value_id, target in targets_by_facet.get(facet_id, ()):
            if value_id in seen or per_target.get(target, 0) >= per_target_cap:
                continue
            taken.append(value_id)
            seen.add(value_id)
            per_target[target] = per_target.get(target, 0) + 1
            took_here = True
            if len(taken) == total:
                break
        if took_here:
            supporting.append(facet_id)
        if len(taken) == total:
            break
    return tuple(taken), tuple(supporting)


def fuse_supplyfilter_target_cap_factory(
    knobs: FuseKnobs | None = None,
) -> Callable[..., FusionDecision]:
    """``saea-fuse-supplyfilter-target-cap-v1`` (knowledge-wave item W3).

    The knobs keep their :class:`FuseKnobs` meaning, read for this rule as:
    ``m`` the admission depth (the first ``m`` ranked facets whose best
    COSINE clears ``tau`` -- :func:`cosine_dimension_items`, never an
    agreement score, exactly as :func:`_fuse_supply_filter` admits), ``c``
    the per-task-target cap, and ``top_l`` the total number of values
    delivered. Values already visible on the query state are skipped and
    consume no budget, as in the supply filter; a value with no task target
    is never supplied, as in the supply filter. Explicit knobs are required:
    this rule has no default policy file.
    """

    if knobs is None:
        raise RailsError("target-capped supply-filter fusion requires explicit FuseKnobs")
    resolved = knobs.validate()

    def fuser(
        *,
        snapshot: KnowledgeSnapshot,
        snapshot_sha256: str,
        query_state: QueryState,
        rank_result: RankResult,
        recall_scores: Mapping[str, Mapping[str, float]],
    ) -> FusionDecision:
        rank_result.validate()
        visible = set(query_state.retrieved_value_ids)
        targets_by_facet: dict[str, list[tuple[str, str]]] = {}
        for value in snapshot.values:
            if value.value_id in visible or value.task_target is None:
                continue
            for facet_id in value.associated_facet_ids:
                targets_by_facet.setdefault(facet_id, []).append(
                    (value.value_id, value.task_target)
                )
        for entries in targets_by_facet.values():
            entries.sort()
        admitted: list[tuple[str, float]] = []
        for candidate in rank_result.candidates[: resolved.m]:
            cosines = [
                score
                for _dimension, score in cosine_dimension_items(
                    recall_scores.get(candidate.facet_id, {})
                )
            ]
            if cosines and max(cosines) >= resolved.tau:
                admitted.append((candidate.facet_id, candidate.score))
        selected, supporting = select_target_capped(
            admitted,
            targets_by_facet=targets_by_facet,
            per_target_cap=resolved.c,
            total=resolved.top_l,
        )
        return FusionDecision(
            snapshot_sha256=snapshot_sha256,
            query_state_sha256=query_state.content_hash(),
            rank_result_sha256=rank_result.content_hash(),
            fusion_policy_id=TARGET_CAP_FUSE_POLICY_ID,
            supporting_facet_ids=tuple(sorted(supporting)),
            selected_value_ids=tuple(sorted(selected)),
        ).validate()

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


@dataclass(frozen=True)
class AlphaBlendDecision:
    """One row's whole ``saea-kb-alpha-blend-v1`` acquire decision.

    WAVE R7 (owner Decision 12-F, 2026-09-08): this used to live inside
    :meth:`KbAlphaBlendController._advance_after_direct`, which is why the
    decision could not be reached from the shared base at all. It is now a
    module-level function over the same frozen organs
    (:func:`multidim_recall`, the registered ranker and fuser,
    :func:`_fused_label_scores`, :func:`_blend_scores`, :func:`_argmax_labels`),
    called by BOTH the retired-shape controller and
    :func:`make_kb_alpha_blend_phase_controller_factory`'s seams on
    ``rails.controllers.EvidenceAgentController``. The two therefore cannot
    diverge: there is one body, not two.

    ``retain_direct`` is the retain-primary shortcut -- the four ways the
    direct-decode answer already stands and no evidence contact is spent: no
    snapshot or no label targets, nothing recalled, nothing fused, or the
    direct label uniquely winning the pre-evidence blend.
    """

    direct_label: str | None
    rank_result: RankResult | None
    fusion_decision: FusionDecision | None
    best_labels: tuple[str, ...]
    retain_direct: bool
    retain_reason: str


def compute_alpha_blend_decision(
    *,
    response_text: str,
    snapshot: KnowledgeSnapshot | None,
    snapshot_sha256: str,
    query_state: QueryState,
    query_vectors: Mapping[str, Sequence[float] | None],
    facet_vectors: Callable[[str], Mapping[str, Sequence[float]]],
    normalizer: Normalizer,
    ranker: Callable[..., RankResult],
    fuser: Callable[..., FusionDecision],
    alpha: float,
    top_k_per_dimension: int,
    label_targets: Mapping[str, str],
    values_by_id: Mapping[str, "ValueBundle"],
) -> AlphaBlendDecision:
    """The ONE alpha-blend decision body (see :class:`AlphaBlendDecision`)."""

    direct_label = normalizer(response_text, label_targets)
    if snapshot is None or not label_targets:
        return AlphaBlendDecision(
            direct_label, None, None, (), True, "no-snapshot-or-no-label-targets"
        )
    recall_scores = multidim_recall(
        snapshot, query_vectors, facet_vectors, top_k_per_dimension
    )
    if not recall_scores:
        return AlphaBlendDecision(direct_label, None, None, (), True, "no-recall")
    rank_result = ranker(
        snapshot_sha256=snapshot_sha256,
        query_state=query_state,
        recall_scores=recall_scores,
    )
    fusion_decision = fuser(
        snapshot=snapshot,
        snapshot_sha256=snapshot_sha256,
        query_state=query_state,
        rank_result=rank_result,
        recall_scores=recall_scores,
    )
    if not fusion_decision.selected_value_ids:
        return AlphaBlendDecision(
            direct_label, rank_result, fusion_decision, (), True, "no-fused-values"
        )
    fused_label_scores = _fused_label_scores(
        label_targets, values_by_id, fusion_decision.selected_value_ids, rank_result
    )
    blended = _blend_scores(label_targets, fused_label_scores, direct_label, alpha)
    best_labels = _argmax_labels(blended)
    if best_labels == (direct_label,):
        # Retain-primary safety default: the direct-decode label uniquely wins
        # the blend without needing evidence at all -- no tie, nothing to
        # break. A TIE that merely INCLUDES the direct label is dispatched, so
        # "tie-break by the evidence-decode answer" has a real answer to
        # consult.
        return AlphaBlendDecision(
            direct_label,
            rank_result,
            fusion_decision,
            best_labels,
            True,
            "direct-label-uniquely-wins-the-blend",
        )
    return AlphaBlendDecision(
        direct_label, rank_result, fusion_decision, best_labels, False, ""
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
        decision = compute_alpha_blend_decision(
            response_text=response_text,
            snapshot=self._snapshot,
            snapshot_sha256=context.knowledge_snapshot_sha256,
            query_state=context.query_state,
            query_vectors=self._query_vectors,
            facet_vectors=self._facet_vectors,
            normalizer=self._normalizer,
            ranker=self._ranker,
            fuser=self._fuser,
            alpha=self._alpha,
            top_k_per_dimension=self._top_k,
            label_targets=self._label_targets,
            values_by_id=self._values_by_id,
        )
        self._direct_label = decision.direct_label
        if decision.retain_direct:
            return self._stop(context, contact)
        rank_result = decision.rank_result
        fusion_decision = decision.fusion_decision
        best_labels = decision.best_labels

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


# --- WAVE R7: the alpha-blend fold onto rails.controllers -------------------
#
# ``KbAlphaBlendController`` above is the migration source the owner rule keeps
# "until disposal". This is the disposal path: the SAME decision
# (:func:`compute_alpha_blend_decision`, one body, called by both) expressed as
# the two seams ``rails.controllers.EvidenceAgentController`` already exposes,
# on the ``phase-direct-evidence-alpha-blend-v1`` program that was written for
# exactly this shape.
#
# ``stop_policy`` is the retain-primary shortcut and ``supply_for_phase`` is the
# acquire; both read the STAGED context WAVE R7 gives them, which carries the
# direct phase's just-sealed answer -- the one thing the base could not see
# before, and the reason this decision had to live inside a controller class.
#
# ONE stated behavioural delta, and it is the standardization rather than a
# side effect: the base SEALS the direct answer as an
# ``AgentStateArtifact`` and carries it on the successor ``QueryState``, so the
# evidence contact sees it as an agent-state turn. The retired controller sealed
# nothing and the evidence contact saw only the retrieved values. Every other
# phase program in this repository traces its own answers that way, and a cell
# that wants the old shape is asking for an untraced intermediate answer.
# ``tests/unit/test_kb_alpha_blend_fold.py`` proves the decision equivalence
# branch by branch and pins this delta.
DIRECT_PHASE_NAME = "direct"
EVIDENCE_PHASE_NAME = "evidence"
ALPHA_BLEND_PROGRAM_ID = "phase-direct-evidence-alpha-blend-v1"
ALPHA_BLEND_ACTION_TARGET_REF = "kb-policy-v1:recall-rank-fuse"
_ALPHA_BLEND_CONTACT_IDS = {
    DIRECT_PHASE_NAME: _DIRECT_CONTACT_ID,
    EVIDENCE_PHASE_NAME: _EVIDENCE_CONTACT_ID,
}


def make_kb_alpha_blend_phase_controller_factory(
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
    instructions: Mapping[str, str] | None = None,
) -> Callable[[str], AgentController]:
    """The WAVE R7 fold: ``saea-kb-alpha-blend-v1``'s decision, on the base.

    Same keywords as :func:`make_kb_alpha_blend_controller_factory`, plus an
    optional ``instructions`` override for the two phases; the defaults are the
    retired controller's own two instruction strings, byte for byte, so the
    CONTROL turns are unchanged.
    """

    from .controllers import (  # noqa: PLC0415  (import cycle: controllers has no kb_policy dependency, but this keeps module import order free)
        EvidenceAgentController,
        PhaseSupply,
        default_phase_program,
    )
    from .material import PhaseMaterial

    snapshot.validate()
    resolved = _resolve_alpha_blend_knobs(
        config=config,
        rank_weights=rank_weights,
        fuse_knobs=fuse_knobs,
        alpha=alpha,
        top_k_per_dimension=top_k_per_dimension,
        normalizer=normalizer,
        query_vectors_by_sample=query_vectors_by_sample,
        facet_vectors=facet_vectors,
    )
    program = default_phase_program(ALPHA_BLEND_PROGRAM_ID)
    label_targets = _label_identities(snapshot)
    values_by_id = {value.value_id: value for value in snapshot.values}
    texts = dict(_ALPHA_BLEND_INSTRUCTIONS)
    if instructions is not None:
        unknown = set(instructions) - set(texts)
        if unknown:
            raise RailsError(
                f"alpha-blend fold: unknown phase instruction(s) {sorted(unknown)}"
            )
        texts.update({str(k): str(v) for k, v in instructions.items()})

    def factory(sample_id: str) -> AgentController:
        cached: dict[str, AlphaBlendDecision] = {}

        def decide(context: AgentRuntimeContext) -> AlphaBlendDecision:
            if DIRECT_PHASE_NAME not in cached:
                cached[DIRECT_PHASE_NAME] = compute_alpha_blend_decision(
                    response_text=context.agent_states[-1].content,
                    snapshot=snapshot,
                    snapshot_sha256=context.knowledge_snapshot_sha256,
                    query_state=context.query_state,
                    query_vectors=resolved["query_vectors_by_sample"].get(sample_id, {}),
                    facet_vectors=resolved["facet_vectors"],
                    normalizer=resolved["normalizer"],
                    ranker=resolved["ranker"],
                    fuser=resolved["fuser"],
                    alpha=resolved["alpha"],
                    top_k_per_dimension=resolved["top_k"],
                    label_targets=label_targets,
                    values_by_id=values_by_id,
                )
            return cached[DIRECT_PHASE_NAME]

        def material_for_phase(
            phase_name: str, _context: AgentRuntimeContext
        ) -> PhaseMaterial:
            phase = program.phase(phase_name)
            return PhaseMaterial(
                instruction=texts[phase_name],
                response_format=None,
                contact_id=_ALPHA_BLEND_CONTACT_IDS[phase_name],
                purpose=phase.purpose,
            ).validate()

        def stop_policy(
            context: AgentRuntimeContext, completed: Sequence[str]
        ) -> bool:
            if tuple(completed) != (DIRECT_PHASE_NAME,):
                return False
            return decide(context).retain_direct

        def supply_for_phase(
            next_phase_name: str, context: AgentRuntimeContext
        ) -> "PhaseSupply | None":
            if next_phase_name != EVIDENCE_PHASE_NAME:
                return None
            decision = decide(context)
            if decision.retain_direct:
                return None
            return PhaseSupply(
                rank_result=decision.rank_result,
                fusion_decision=decision.fusion_decision,
                action_target_ref=ALPHA_BLEND_ACTION_TARGET_REF,
            ).validate()

        return EvidenceAgentController(
            program=program,
            material_for_phase=material_for_phase,
            supply_for_phase=supply_for_phase,
            stop_policy=stop_policy,
            contact_identity={
                DIRECT_PHASE_NAME: (
                    f"{CONTROLLER_POLICY_ID}:{DIRECT_PHASE_NAME}",
                    CONTROLLER_POLICY_ID,
                ),
                EVIDENCE_PHASE_NAME: (
                    f"{CONTROLLER_POLICY_ID}:{EVIDENCE_PHASE_NAME}",
                    CONTROLLER_POLICY_ID,
                ),
            },
        )

    return factory


def _resolve_alpha_blend_knobs(
    *,
    config: Mapping[str, object] | None,
    rank_weights: RankWeights | None,
    fuse_knobs: FuseKnobs | None,
    alpha: float | None,
    top_k_per_dimension: int | None,
    normalizer: Normalizer | None,
    query_vectors_by_sample: Mapping[str, Mapping[str, Sequence[float] | None]] | None,
    facet_vectors: Callable[[str], Mapping[str, Sequence[float]]] | None,
) -> dict[str, object]:
    """The knob resolution :func:`make_kb_alpha_blend_controller_factory`
    performs, factored out so both factories resolve identically."""

    needs_config = config is None and any(
        value is None for value in (rank_weights, fuse_knobs, alpha, top_k_per_dimension)
    )
    resolved_config = (
        config if config is not None else (load_policy_config() if needs_config else None)
    )
    resolved_weights = (
        rank_weights if rank_weights is not None else rank_weights_from_config(resolved_config)
    )
    resolved_knobs = (
        fuse_knobs if fuse_knobs is not None else fuse_knobs_from_config(resolved_config)
    )
    return {
        "weights": resolved_weights,
        "knobs": resolved_knobs,
        "alpha": alpha if alpha is not None else alpha_from_config(resolved_config),
        "top_k": (
            top_k_per_dimension
            if top_k_per_dimension is not None
            else top_k_per_dimension_from_config(resolved_config)
        ),
        "normalizer": normalizer if normalizer is not None else default_label_normalizer,
        "query_vectors_by_sample": dict(query_vectors_by_sample or {}),
        "facet_vectors": (
            facet_vectors if facet_vectors is not None else (lambda facet_id: {})
        ),
        "ranker": rank_wcos_prior_agree_factory(resolved_weights),
        "fuser": fuse_supplyfilter_factory(resolved_knobs),
    }


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
    if ASSOCIATED_VALUES_FUSE_POLICY_ID not in KNOWLEDGE_FUSERS.names():
        KNOWLEDGE_FUSERS.register(
            ASSOCIATED_VALUES_FUSE_POLICY_ID, fuse_associated_values_factory
        )
    if TARGET_CAP_FUSE_POLICY_ID not in KNOWLEDGE_FUSERS.names():
        KNOWLEDGE_FUSERS.register(
            TARGET_CAP_FUSE_POLICY_ID, fuse_supplyfilter_target_cap_factory
        )
    if CONTROLLER_POLICY_ID not in AGENT_CONTROLLERS.names():
        AGENT_CONTROLLERS.register(CONTROLLER_POLICY_ID, _default_controller_factory)


register_kb_policy_v1()


__all__ = [
    "AGREEMENT_DIMENSIONS",
    "ASSOCIATED_VALUES_FUSE_POLICY_ID",
    "EXEMPLAR_INTENT_AGREEMENT_DIMENSION",
    "cosine_dimension_items",
    "fuse_associated_values_factory",
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
    "fuse_supplyfilter_target_cap_factory",
    "select_target_capped",
    "TARGET_CAP_FUSE_POLICY_ID",
    "load_policy_config",
    "compute_alpha_blend_decision",
    "make_kb_alpha_blend_controller_factory",
    "make_kb_alpha_blend_phase_controller_factory",
    "multidim_recall",
    "multidim_segment_recall",
    "rank_weights_from_config",
    "rank_wcos_prior_agree_factory",
    "register_kb_policy_v1",
    "top_k_per_dimension_from_config",
]
