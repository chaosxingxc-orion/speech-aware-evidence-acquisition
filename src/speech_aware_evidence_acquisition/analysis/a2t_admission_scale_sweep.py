"""A2T ADMISSION-SCALE DEFECT -- the offline audit and the fix specification.

Row ``SAEA-SN-MF-A2T-ADMISSION-SCALE-SWEEP`` (model-free-check), registered in
``docs/exposure-ledger.md`` BEFORE any number here was computed.

THE FINDING, STATED FIRST. The registered ranker
``saea-rank-wcos-prior-agree-v1`` forms ``w_cos * max_cosine + w_prior *
max_prior + w_agree * agreement``. ``max_cosine`` is bounded by 1 by
construction. ``max_prior`` is NOT bounded by anything: it is whatever
``kb._facet_prior_mass`` reads off the snapshot, and on the Audio2Tool
knowledge base it reaches 4.1. Putting the two in one weighted sum is an
IMPLEMENTATION DEFECT -- an owner ruling this module adopts as settled and does
not re-argue. The consequence is measured here: on all 104 Audio2Tool
trajectories the prior-mass facets occupy the entire top-m window, no content
facet is ever percept-admitted, no value is ever supplied, and every trajectory
retains. **The stage-G1 "paired first signal" therefore measured a BROKEN
CONFIGURATION, and no paradigm-level conclusion about Audio2Tool follows from
it.**

WHY IT SURVIVED ON SLURP, and why that is the specification material. No
content facet ever carries prior mass on either carrier, so on BOTH carriers
the comparison that decides the window is a content COSINE against a prior
MASS -- two scales in one sum, always. SLURP got away with it only because its
prior mass happens to be a genuine conditional probability bounded by 1, which
puts ``w_prior * sup(prior) = 0.300`` just under ``w_cos * tau = 0.325``. The
margin is 0.025. Audio2Tool's builder emits an unbounded ratio and the same
code inverts.

WHAT THIS MODULE COMPUTES:

1. :func:`scale_audit` -- the per-dimension score distributions on BOTH
   carriers, the commensurability invariant the locked cell silently relied on,
   and the eviction it causes. This is the verification material for the fix.
2. :func:`sweep_carrier` -- every candidate normalization form and admission
   structure a CORRECT implementation might choose, replayed through
   ``rails.kb_policy``'s OWN pure functions. :func:`fix_verification` reports
   which form is PRINCIPLED -- bounded, order-preserving, query-independent,
   one change -- never which form scores best on Audio2Tool.
3. :func:`decisive_quantities` and :func:`alpha_gate_analysis` -- forward-looking
   material for the post-fix re-flight: what the repaired supply path would
   actually reach, and the SECOND, independent ceiling that admission repair
   does not touch.
4. :func:`fix_verification` -- the fix specification's proof obligation,
   discharged by measurement: every candidate form is replayed over the sealed
   SLURP DEV-1000 NEW500 flight and its admitted set, supply and dispatch
   decision are compared trajectory by trajectory against the frozen cell's
   own. With ``max_prior = 0.0`` on every content facet and ``sup(prior) = 1.0``
   on SLURP, a bounding normalization is an IDENTITY there, and this module
   proves it rather than claiming it.

REUSE, NEVER REIMPLEMENTATION. Recall goes through
``contrast_fewshot_preanalysis.vectorised_recall`` (cross-checked against real
``kb.multidim_recall`` calls); ranking, admission, fusion and the blend head go
through ``dev100_damage_channel_analysis.replay_supply`` / ``replay_blend``,
which call ``kb_policy``'s registered ranker, registered fuser,
``_fused_label_scores``, ``_blend_scores`` and ``_argmax_labels`` directly.
Audio2Tool answers are scored by the frozen ``a2t-scorer-v1`` through
``Audio2ToolAdapter.score``. Conversion anchors are imported from
``k1_hybrid_ranking_gate``. Exactly TWO functions wrap rather than call, and
each says so in its own docstring: :func:`_per_dimension_supply` and
:func:`_split_scale_supply`.

WHAT IT DOES NOT DO. It changes no knob and writes nothing under ``configs/``,
``rails/`` or ``core/``. It opens no model session, no embedding sidecar and no
tokenizer: :func:`run` arms ``dev100_reviewer_audit.arm_offline_guard`` BEFORE
the first input is opened and writes the recorded outbound-attempt count into
the receipt. The resident np2 A2T service on port 8090 is never contacted,
probed, reconfigured or stopped.

TOKEN FIGURES ARE ESTIMATES, ALWAYS LABELLED. Counting real tokens requires the
server's ``/tokenize``, which is a contact. :func:`token_model` instead
calibrates a characters-per-token constant against the ALREADY-LANDED
``prompt-fit-np2.json`` receipt, whose two measured envelopes differ by exactly
the evidence block, and applies it to each variant's own supplied values. The
constant is deliberately CONSERVATIVE: the landed worst case also counted five
key facets, which ``rails.runner._agent_messages`` never renders for this
controller because ``visible_facet_ids`` stays empty.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=<repo>/src \
      python -m speech_aware_evidence_acquisition.analysis.a2t_admission_scale_sweep \
        --repo-root <repo> --data-root $SPEECHRL_DATA_DIR --out <receipt>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import a2t_read
from . import contrast_fewshot_preanalysis as cf
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from . import k1_hybrid_ranking_gate as k1
from ..rails import kb_policy as kb
from ..rails.knowledge import KnowledgeSnapshot, RankResult, RankedFacet

SCHEMA = "saea-a2t-admission-scale-sweep-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-A2T-ADMISSION-SCALE-SWEEP"


class SweepError(RuntimeError):
    """A pinned input does not match, or a replay contradicts a sealed
    record. Never raised for a legitimate data shape."""


# ---------------------------------------------------------------------------
# The frozen cell, imported rather than restated
# ---------------------------------------------------------------------------

FROZEN_ALPHA = cf.FROZEN_ALPHA
FROZEN_TOP_K = cf.FROZEN_TOP_K
FROZEN_WEIGHTS = cf.FROZEN_WEIGHTS
FROZEN_FUSE = cf.FROZEN_FUSE
FROZEN_POLICY_CONFIG_RELPATH = cf.FROZEN_POLICY_CONFIG_RELPATH
FROZEN_POLICY_CONFIG_SHA256 = (
    "d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919"
)

#: How many samples per carrier are cross-checked against a REAL
#: ``kb.multidim_recall`` call before the vectorised recall is believed.
RECALL_FIDELITY_PROBES = cf.RECALL_FIDELITY_PROBES


# ---------------------------------------------------------------------------
# Pinned Audio2Tool inputs -- every one already landed and hash-checked
# ---------------------------------------------------------------------------

A2T_RUN_ID = "SAEA-A2T-G1"
A2T_ATTEMPT_ID = "attempt-20260825T125051Z-a2tg1blend"
A2T_CHECK_DIR_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1"
)
A2T_REPORT_BASENAME = "arm2-blend-mechanical-report-attempt3.json"
A2T_REPORT_SHA256 = (
    "56bf0a7592d2b595da86dab84ad7c0ae8246d1afc150f4cb695f2c9efcc0b520"
)
A2T_PASS_A_BASENAME = "pass-a-direct-outputs.jsonl"
A2T_PASS_A_SHA256 = (
    "73e28511f419cd67b1721d829438f8c102e725e01243c9a9f000e00d92aadc9c"
)
A2T_PROJECTION_BASENAME = "dispatch-projection.json"
A2T_PROJECTION_SHA256 = (
    "c27b0be62bab33d0172a2611841ac48e9d31f98049591ace883b93bd6a9dcb36"
)
A2T_PROMPT_FIT_BASENAME = "prompt-fit-np2.json"
A2T_PROMPT_FIT_SHA256 = (
    "0c77812d9439b6a7d6d3ff0227fc27924f617245d1ec9a0cbca20960f090946b"
)
A2T_SUBSET_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-G1-104.json"
A2T_SUBSET_RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
A2T_SNAPSHOT_RELPATH = (
    "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
)
A2T_SNAPSHOT_SHA256 = (
    "ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2"
)
A2T_EMBEDDING_RECEIPT_RELPATH = (
    "docs/receipts/knowledge/a2t-kb-size-full-embeddings.json"
)
A2T_LABEL_VOCABULARY_SIZE = 151
A2T_SPLIT_ID = "A2T-G1-104"
A2T_SPLIT_COUNT = 104

#: The two TEXT envelopes the landed np2 prompt-fit receipt MEASURED, and the
#: serving geometry the campaign plan section 8.1 derived. The token model is
#: calibrated against the difference between them and nothing else.
PROMPT_FIT_M0_TEXT_TOKENS = 13236
PROMPT_FIT_BLEND_TEXT_TOKENS = 19047
PROMPT_FIT_SPEECH_WORST = 364
PROMPT_FIT_OUTPUT_CEILING = 1024
PROMPT_FIT_SPECIAL_RESERVE = 2
DERIVED_SLOT_TOKENS = 32768


# ---------------------------------------------------------------------------
# The variant grid -- fixed before execution
# ---------------------------------------------------------------------------

#: Prior-mass transforms. Each is a pure rescaling of the PRIOR-MASS dimension
#: scores AFTER recall and BEFORE ranking; none of them changes which facets
#: were recalled, none touches the cosine dimensions, and none touches percept
#: admission (which reads only NON-prior-mass dimensions and is therefore
#: numerically untouched by every one of them).
PRIOR_TRANSFORMS = (
    "none",
    "clip1",
    "globalmax",
    "dimsup-floor1",
    "minmax-q",
    "z-q",
    "rrf-dim",
)

#: The reciprocal-rank-fusion constant, imported from the K1 gate rather than
#: re-chosen here.
RRF_K = k1.RRF_K


@dataclass(frozen=True)
class Variant:
    """One single change to the ranker/fuser scale handling."""

    variant_id: str
    prior_transform: str
    m: int
    admission: str  # "global" | "per-dimension"
    family: str
    change: str

    def validate(self) -> "Variant":
        if self.prior_transform not in PRIOR_TRANSFORMS:
            raise SweepError(f"unknown prior transform {self.prior_transform!r}")
        if self.admission not in ("global", "per-dimension"):
            raise SweepError(f"unknown admission scope {self.admission!r}")
        if self.m <= 0:
            raise SweepError("m must be positive")
        return self

    @property
    def knobs(self) -> kb.FuseKnobs:
        return kb.FuseKnobs(
            tau=FROZEN_FUSE.tau, m=self.m, c=FROZEN_FUSE.c, top_l=FROZEN_FUSE.top_l
        ).validate()


VARIANTS: tuple[Variant, ...] = tuple(
    variant.validate()
    for variant in (
        Variant(
            variant_id="V0-FROZEN",
            prior_transform="none",
            m=5,
            admission="global",
            family="baseline",
            change="none -- the locked v1 cell exactly as flown",
        ),
        Variant(
            variant_id="A1-CLIP1",
            prior_transform="clip1",
            m=5,
            admission="global",
            family="a-normalization",
            change=(
                "prior mass clipped to min(mass, 1.0) before ranking -- the "
                "declared [0,1] bound of a conditional probability, restored"
            ),
        ),
        Variant(
            variant_id="A2-GLOBALMAX",
            prior_transform="globalmax",
            m=5,
            admission="global",
            family="a-normalization",
            change=(
                "prior mass divided by the snapshot's own maximum prior mass "
                "before ranking -- order-preserving rescaling into [0,1]"
            ),
        ),
        Variant(
            variant_id="A6-DIMSUP-FLOOR1",
            prior_transform="dimsup-floor1",
            m=5,
            admission="global",
            family="a-normalization",
            change=(
                "every dimension divided by max(1.0, that dimension's own sup "
                "over the recalled set) before ranking -- THE RULE THE LANDED "
                "REPAIR IMPLEMENTS, reproduced here so this audit checks it "
                "rather than describes it"
            ),
        ),
        Variant(
            variant_id="A3-MINMAX-Q",
            prior_transform="minmax-q",
            m=5,
            admission="global",
            family="a-normalization",
            change=(
                "per-QUERY min-max of the recalled prior-mass scores before "
                "ranking"
            ),
        ),
        Variant(
            variant_id="A4-Z-Q",
            prior_transform="z-q",
            m=5,
            admission="global",
            family="a-normalization",
            change=(
                "per-QUERY z-normalization of the recalled prior-mass scores "
                "before ranking"
            ),
        ),
        Variant(
            variant_id="A5-RRF-DIM",
            prior_transform="rrf-dim",
            m=5,
            admission="global",
            family="a-normalization",
            change=(
                "every dimension's score replaced by 1/(60 + rank-within-that-"
                "dimension) before ranking -- the canonical scale-free "
                "cross-dimension combiner; admission still reads the ORIGINAL "
                "cosine scale, which requires splitting the mapping the ranker "
                "scores from the mapping the fuser admits on"
            ),
        ),
        Variant(
            variant_id="B1-M8",
            prior_transform="none",
            m=8,
            admission="global",
            family="b-window",
            change="m raised 5 -> 8 at UNCHANGED normalization",
        ),
        Variant(
            variant_id="B2-M16",
            prior_transform="none",
            m=16,
            admission="global",
            family="b-window",
            change="m raised 5 -> 16 at UNCHANGED normalization",
        ),
        Variant(
            variant_id="B3-M32",
            prior_transform="none",
            m=32,
            admission="global",
            family="b-window",
            change="m raised 5 -> 32 at UNCHANGED normalization",
        ),
        Variant(
            variant_id="C1-PERDIM",
            prior_transform="none",
            m=5,
            admission="per-dimension",
            family="c-admission",
            change=(
                "the fuser's top-m window is taken over the COSINE-FAMILY "
                "sub-ordering instead of the global ordering -- a per-dimension "
                "top-m rather than one global one"
            ),
        ),
        Variant(
            variant_id="D1-CLIP1-M8",
            prior_transform="clip1",
            m=8,
            admission="global",
            family="d-combination",
            change="A1 and B1 together",
        ),
        Variant(
            variant_id="D2-CLIP1-M16",
            prior_transform="clip1",
            m=16,
            admission="global",
            family="d-combination",
            change="A1 and B2 together",
        ),
        Variant(
            variant_id="D3-CLIP1-PERDIM",
            prior_transform="clip1",
            m=5,
            admission="per-dimension",
            family="d-combination",
            change="A1 and C1 together",
        ),
        Variant(
            variant_id="D4-MINMAXQ-PERDIM",
            prior_transform="minmax-q",
            m=5,
            admission="per-dimension",
            family="d-combination",
            change="A3 and C1 together",
        ),
    )
)

BASELINE_VARIANT_ID = "V0-FROZEN"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return dc._sha256_file(Path(path))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> str:
    measured = _sha256_file(path)
    if measured != expected:
        raise SweepError(f"{label} hashes to {measured}, not the pinned {expected}")
    return measured


def _descriptives(values: Sequence[float]) -> dict[str, object]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"count": 0}

    def quantile(fraction: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = fraction * (len(ordered) - 1)
        low = int(math.floor(position))
        high = min(low + 1, len(ordered) - 1)
        weight = position - low
        return ordered[low] * (1.0 - weight) + ordered[high] * weight

    return {
        "count": len(ordered),
        "min": ordered[0],
        "p10": quantile(0.10),
        "median": quantile(0.50),
        "mean": sum(ordered) / len(ordered),
        "p90": quantile(0.90),
        "max": ordered[-1],
    }


def _max_cosine(dim_scores: Mapping[str, float]) -> float:
    return dc._max_cosine(dim_scores)


def _max_prior(dim_scores: Mapping[str, float]) -> float:
    return dc._max_prior(dim_scores)


def _is_cosine_family(dim_scores: Mapping[str, float]) -> bool:
    return any(dim not in kb.PRIOR_MASS_DIMENSIONS for dim in dim_scores)


# ---------------------------------------------------------------------------
# The prior-mass transforms
# ---------------------------------------------------------------------------


def snapshot_max_prior_mass(snapshot: KnowledgeSnapshot) -> float:
    """The largest prior mass ANY prior-mass-dimension facet carries.

    Computed through ``kb._facet_prior_mass`` -- kb's own definition of what a
    prior-mass facet's score is -- so the audit measures the same quantity the
    ranker consumes rather than a look-alike read off the raw JSON."""

    values_by_facet: dict[str, list[object]] = {}
    for value in snapshot.values:
        for facet_id in value.associated_facet_ids:
            values_by_facet.setdefault(facet_id, []).append(value)
    best = 0.0
    for facet in snapshot.facets:
        if facet.dimension not in kb.PRIOR_MASS_DIMENSIONS:
            continue
        best = max(best, kb._facet_prior_mass(facet, values_by_facet))
    return best


def apply_prior_transform(
    recall_scores: Mapping[str, Mapping[str, float]],
    *,
    mode: str,
    global_max: float,
) -> dict[str, dict[str, float]]:
    """Rescale ONLY the prior-mass dimension scores of one recall result.

    Every mode leaves the recalled facet SET untouched, leaves every
    cosine-family score untouched, and therefore leaves percept admission --
    which reads only non-prior-mass dimensions -- numerically identical. What
    changes is where the prior-mass facets sit in the ranker's weighted sum,
    which is exactly the scale question this row is about.
    """

    if mode == "rrf-dim":
        raise SweepError(
            "the rrf-dim combiner rewrites every dimension, not only prior mass; "
            "it is routed through _split_scale_supply, never through here"
        )
    if mode == "none":
        return {facet_id: dict(scores) for facet_id, scores in recall_scores.items()}

    prior_values = [
        score
        for scores in recall_scores.values()
        for dim, score in scores.items()
        if dim in kb.PRIOR_MASS_DIMENSIONS
    ]

    if mode == "clip1":

        def rescale(score: float) -> float:
            return min(score, 1.0)

    elif mode == "globalmax":
        if global_max <= 0.0:
            raise SweepError("globalmax transform needs a positive snapshot maximum")

        def rescale(score: float) -> float:
            return score / global_max

    elif mode == "dimsup-floor1":
        # Divide EVERY dimension by max(1.0, sup over that dimension's own
        # recalled scores). This is the rule the landed repair implements, and
        # it is reproduced here so the audit machine-checks that repair rather
        # than describing it. Two lemmas make it deterministic despite reading
        # the recalled set:
        #   (a) on a cosine-family dimension the sup cannot exceed 1, so the
        #       divisor is exactly 1.0 and the transform is the identity --
        #       which is why tau keeps its meaning;
        #   (b) on a prior-mass dimension multidim_recall truncates by
        #       DESCENDING score, so the recalled sup IS the snapshot sup for
        #       that dimension, on every query. The apparent query-dependence
        #       is provably inert for exactly the dimensions that need fixing.
        sup_by_dimension: dict[str, float] = {}
        for scores in recall_scores.values():
            for dim, score in scores.items():
                sup_by_dimension[dim] = max(sup_by_dimension.get(dim, 0.0), score)
        divisors = {
            dim: max(1.0, sup) for dim, sup in sup_by_dimension.items()
        }
        return {
            facet_id: {dim: score / divisors[dim] for dim, score in scores.items()}
            for facet_id, scores in recall_scores.items()
        }

    elif mode == "minmax-q":
        if not prior_values:
            return {facet_id: dict(s) for facet_id, s in recall_scores.items()}
        low = min(prior_values)
        high = max(prior_values)
        span = high - low

        def rescale(score: float) -> float:
            return 1.0 if span <= 0.0 else (score - low) / span

    elif mode == "z-q":
        if len(prior_values) < 2:
            return {facet_id: dict(s) for facet_id, s in recall_scores.items()}
        mean = statistics.fmean(prior_values)
        stdev = statistics.pstdev(prior_values)

        def rescale(score: float) -> float:
            return 0.0 if stdev <= 0.0 else (score - mean) / stdev

    else:  # pragma: no cover - guarded by Variant.validate
        raise SweepError(f"unknown prior transform {mode!r}")

    out: dict[str, dict[str, float]] = {}
    for facet_id, scores in recall_scores.items():
        out[facet_id] = {
            dim: (rescale(score) if dim in kb.PRIOR_MASS_DIMENSIONS else score)
            for dim, score in scores.items()
        }
    return out


def rrf_dimension_scores(
    recall_scores: Mapping[str, Mapping[str, float]], *, k: int = RRF_K
) -> dict[str, dict[str, float]]:
    """Replace EVERY dimension's score by its reciprocal rank within that
    dimension -- the canonical scale-free cross-dimension combiner.

    Unlike the prior-mass rescalings this rewrites the COSINE dimension too,
    which is exactly why it cannot be applied through the registered fuser
    unchanged: percept admission compares ``max_cosine`` against ``tau``, and
    ``tau = 0.65`` lives on the cosine scale, not on a 1/(k+rank) scale. See
    :func:`_split_scale_supply`."""

    by_dimension: dict[str, list[tuple[float, str]]] = {}
    for facet_id, dim_scores in recall_scores.items():
        for dimension, score in dim_scores.items():
            by_dimension.setdefault(dimension, []).append((score, facet_id))
    out: dict[str, dict[str, float]] = {facet_id: {} for facet_id in recall_scores}
    for dimension, items in by_dimension.items():
        items.sort(key=lambda item: (-item[0], item[1]))
        for rank, (_score, facet_id) in enumerate(items, start=1):
            out[facet_id][dimension] = 1.0 / (k + rank)
    return out


def _split_scale_supply(
    inputs: dc.LandedInputs,
    sample_id: str,
    *,
    rank_scores: Mapping[str, Mapping[str, float]],
    admit_scores: Mapping[str, Mapping[str, float]],
    knobs: kb.FuseKnobs,
    per_dimension: bool,
) -> dc.SupplyReplay:
    """Rank on one scale, admit on another -- THE SECOND WRAP, and the reason
    a rank-based cross-dimension combiner is NOT a one-line fix.

    ``kb._fuse_supply_filter`` receives a single ``recall_scores`` mapping and
    uses it for BOTH the percept-admission threshold and (through the ranker's
    output) the window. A rank-based combiner has to move the ranker's scale
    without moving the admission scale, so the two mappings must be split.
    Everything inside the ranker and the fuser is still kb's own code; what
    this function supplies is the split, and the fact that it is needed at all
    is itself a finding about that combiner."""

    ranker = kb.rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
    fuser = kb.fuse_supplyfilter_factory(knobs)
    state = dc._query_state(sample_id, inputs.snapshot_sha256)
    rank_result = ranker(
        snapshot_sha256=inputs.snapshot_sha256,
        query_state=state,
        recall_scores=rank_scores,
    )
    if per_dimension:
        rank_result = RankResult(
            snapshot_sha256=rank_result.snapshot_sha256,
            query_state_sha256=rank_result.query_state_sha256,
            ranking_policy_id=rank_result.ranking_policy_id,
            candidates=tuple(
                RankedFacet(
                    facet_id=candidate.facet_id, score=candidate.score
                ).validate()
                for candidate in rank_result.candidates
                if _is_cosine_family(admit_scores.get(candidate.facet_id, {}))
            ),
        ).validate()
    decision = fuser(
        snapshot=inputs.snapshot,
        snapshot_sha256=inputs.snapshot_sha256,
        query_state=state,
        rank_result=rank_result,
        recall_scores=admit_scores,
    )
    top_m = tuple(candidate.facet_id for candidate in rank_result.candidates[: knobs.m])
    admitted = tuple(
        facet_id
        for facet_id in top_m
        if _max_cosine(admit_scores.get(facet_id, {})) >= knobs.tau
    )
    dims_total = len({dim for scores in admit_scores.values() for dim in scores})
    return dc.SupplyReplay(
        sample_id=sample_id,
        recall_scores=admit_scores,
        rank_result=rank_result,
        selected_value_ids=tuple(decision.selected_value_ids),
        supporting_facet_ids=tuple(decision.supporting_facet_ids),
        admitted_facet_ids=admitted,
        top_m_facet_ids=top_m,
        dims_total=dims_total,
    )


# ---------------------------------------------------------------------------
# The ONE wrap: per-dimension admission
# ---------------------------------------------------------------------------


def _per_dimension_supply(
    inputs: dc.LandedInputs,
    sample_id: str,
    *,
    recall_scores: Mapping[str, Mapping[str, float]],
    knobs: kb.FuseKnobs,
) -> dc.SupplyReplay:
    """Per-dimension top-m admission -- THE ONE PLACE THIS MODULE WRAPS.

    ``kb._fuse_supply_filter`` takes its top-m window off the head of the
    GLOBAL ranked ordering, and no argument of the registered fuser can ask it
    for anything else. So this function does the smallest possible wrap: it
    calls kb's OWN registered ranker unchanged, then hands the registered
    fuser a :class:`RankResult` whose candidate list is RESTRICTED to the
    cosine-family facets, so the fuser's own ``candidates[:m]`` slice IS the
    cosine dimension's own top-m.

    What is still kb's own code, byte for byte: the ranker, the percept
    admission predicate, the coverage floor and ceiling, the task_target
    grouping, the value ordering, and the :class:`FusionDecision` contract.
    What this function supplies: the partition of the ranked list by dimension
    family, and nothing else. Dropping the prior-mass facets from the
    candidate list cannot change WHICH values are reachable -- a prior-mass
    facet can never be percept-admitted, because admission reads only
    non-prior-mass dimensions -- it only changes the window and, downstream,
    the ``facet_score`` a supplied value's strength is read off in
    ``kb._fused_label_scores``, which then becomes that value's CONTENT facet
    score rather than its tool's raw prior mass. That is the intended
    semantics of computing content admission separately from the prior
    dimensions.
    """

    ranker = kb.rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
    fuser = kb.fuse_supplyfilter_factory(knobs)
    state = dc._query_state(sample_id, inputs.snapshot_sha256)
    global_rank = ranker(
        snapshot_sha256=inputs.snapshot_sha256,
        query_state=state,
        recall_scores=recall_scores,
    )
    cosine_family = tuple(
        RankedFacet(facet_id=candidate.facet_id, score=candidate.score).validate()
        for candidate in global_rank.candidates
        if _is_cosine_family(recall_scores.get(candidate.facet_id, {}))
    )
    rank_result = RankResult(
        snapshot_sha256=global_rank.snapshot_sha256,
        query_state_sha256=global_rank.query_state_sha256,
        ranking_policy_id=global_rank.ranking_policy_id,
        candidates=cosine_family,
    ).validate()
    decision = fuser(
        snapshot=inputs.snapshot,
        snapshot_sha256=inputs.snapshot_sha256,
        query_state=state,
        rank_result=rank_result,
        recall_scores=recall_scores,
    )
    top_m = tuple(candidate.facet_id for candidate in rank_result.candidates[: knobs.m])
    admitted = tuple(
        facet_id
        for facet_id in top_m
        if _max_cosine(recall_scores.get(facet_id, {})) >= knobs.tau
    )
    dims_total = len({dim for scores in recall_scores.values() for dim in scores})
    return dc.SupplyReplay(
        sample_id=sample_id,
        recall_scores=recall_scores,
        rank_result=rank_result,
        selected_value_ids=tuple(decision.selected_value_ids),
        supporting_facet_ids=tuple(decision.supporting_facet_ids),
        admitted_facet_ids=admitted,
        top_m_facet_ids=top_m,
        dims_total=dims_total,
    )


def variant_supply(
    inputs: dc.LandedInputs,
    sample_id: str,
    *,
    base_recall: Mapping[str, Mapping[str, float]],
    variant: Variant,
    global_max_prior: float,
) -> dc.SupplyReplay:
    """One variant's supply for one trajectory, through kb's own stages."""

    if variant.prior_transform == "rrf-dim":
        return _split_scale_supply(
            inputs,
            sample_id,
            rank_scores=rrf_dimension_scores(base_recall),
            admit_scores={
                facet_id: dict(scores) for facet_id, scores in base_recall.items()
            },
            knobs=variant.knobs,
            per_dimension=variant.admission == "per-dimension",
        )
    recall_scores = apply_prior_transform(
        base_recall, mode=variant.prior_transform, global_max=global_max_prior
    )
    if variant.admission == "global":
        return dc.replay_supply(
            inputs,
            sample_id,
            weights=FROZEN_WEIGHTS,
            knobs=variant.knobs,
            top_k=FROZEN_TOP_K,
            recall_scores=recall_scores,
        )
    return _per_dimension_supply(
        inputs, sample_id, recall_scores=recall_scores, knobs=variant.knobs
    )


# ---------------------------------------------------------------------------
# Carrier inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CarrierInputs:
    """One carrier's landed material, in the shape every stage here reads."""

    carrier_id: str
    bundle: cf.SnapshotBundle
    inputs: dc.LandedInputs
    sample_ids: tuple[str, ...]
    direct_texts: Mapping[str, str]
    gold_target: Mapping[str, str]
    baseline_correct: Mapping[str, bool]
    flown_dispatched: Mapping[str, bool]
    flown_supply: Mapping[str, tuple[str, ...]]
    artifact_hashes: Mapping[str, str]
    notes: Mapping[str, object]


def load_a2t_bundle(*, data_root: Path, repo_root: Path) -> cf.SnapshotBundle:
    """The Audio2Tool analogue of :func:`cf.load_snapshot_bundle`.

    Identical construction, identical refusals, pointed at the A2T snapshot and
    its landed content-facet NPZ. The VALUE vectors are never opened -- the
    locked cell seals them and none were ever produced for this carrier."""

    import numpy as np

    snapshot_path = Path(data_root) / A2T_SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    snapshot_sha256 = snapshot.content_hash()
    if snapshot_sha256 != A2T_SNAPSHOT_SHA256:
        raise SweepError(
            f"A2T snapshot hashes to {snapshot_sha256}, not the pinned "
            f"{A2T_SNAPSHOT_SHA256}"
        )

    receipt = json.loads(
        (Path(repo_root) / A2T_EMBEDDING_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    facet_block = receipt["vectors"]["content_facets"]
    npz_path = snapshot_path.parent / facet_block["file"]
    measured_npz = _require_hash(
        npz_path, facet_block["sha256"], "A2T content-facet NPZ"
    )
    npz = np.load(npz_path)
    facet_ids = tuple(str(value) for value in npz["ids"])
    matrix = np.asarray(npz["vectors"], dtype=np.float64)
    if matrix.shape[0] != len(facet_ids):
        raise SweepError(f"unexpected A2T facet vector shape {matrix.shape}")
    facet_index = {facet_id: index for index, facet_id in enumerate(facet_ids)}

    label_targets = kb._label_identities(snapshot)
    if len(label_targets) != A2T_LABEL_VOCABULARY_SIZE:
        raise SweepError(
            f"A2T label vocabulary is {len(label_targets)}, not "
            f"{A2T_LABEL_VOCABULARY_SIZE}"
        )
    label_texts = {
        facet.facet_id: facet.representation
        for facet in snapshot.facets
        if facet.facet_id in label_targets
    }
    values_by_id = {value.value_id: value for value in snapshot.values}
    content_facet_target: dict[str, str] = {}
    values_by_target: dict[str, list[str]] = {}
    for value in snapshot.values:
        if value.task_target is None:
            continue
        values_by_target.setdefault(value.task_target, []).append(value.value_id)
        for facet_id in value.associated_facet_ids:
            content_facet_target.setdefault(facet_id, value.task_target)

    by_target: dict[str, list[int]] = {}
    for facet_id, target in content_facet_target.items():
        index = facet_index.get(facet_id)
        if index is not None:
            by_target.setdefault(target, []).append(index)
    facet_indices_by_target = {
        target: np.asarray(sorted(indices), dtype=np.int64)
        for target, indices in by_target.items()
    }

    lexicographic = sorted(range(len(facet_ids)), key=lambda index: facet_ids[index])
    facet_id_rank = np.empty(len(facet_ids), dtype=np.int64)
    for position, index in enumerate(lexicographic):
        facet_id_rank[index] = position

    prior_dimension_recall = kb.multidim_recall(
        snapshot, {}, lambda _facet_id: {}, FROZEN_TOP_K
    )

    return cf.SnapshotBundle(
        snapshot=snapshot,
        snapshot_sha256=snapshot_sha256,
        facet_ids=facet_ids,
        matrix=matrix,
        facet_index=facet_index,
        npz_sha256=measured_npz,
        label_targets=label_targets,
        label_texts=label_texts,
        values_by_id=values_by_id,
        content_facet_target=content_facet_target,
        facet_indices_by_target=facet_indices_by_target,
        values_by_target={
            target: tuple(sorted(ids)) for target, ids in values_by_target.items()
        },
        facet_id_rank=facet_id_rank,
        prior_dimension_recall=prior_dimension_recall,
    )


def load_a2t_carrier(*, data_root: Path, repo_root: Path) -> CarrierInputs:
    """The sealed A2T G1 attempt-3 BLEND arm, loaded and identity-checked.

    Query TEXTS are the arm's own landed Pass-A direct decodes. Query VECTORS
    are the arm's own landed ``query-vectors.jsonl`` rows, and every text is
    re-hashed against the ``text_sha256`` its own vector record carries, so a
    text substitution is impossible and the sweep reads exactly what the policy
    read in flight. GOLD is opened over the EXPOSED 104 whose seal the landed
    G1 read already broke; no unexposed material is touched.
    """

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    check_dir = repo_root / A2T_CHECK_DIR_RELPATH

    report_sha = _require_hash(
        check_dir / A2T_REPORT_BASENAME,
        A2T_REPORT_SHA256,
        "the landed A2T attempt-3 BLEND report",
    )
    report = json.loads((check_dir / A2T_REPORT_BASENAME).read_text(encoding="utf-8"))
    if report["attempt_id"] != A2T_ATTEMPT_ID or report["arm_id"] != "BLEND":
        raise SweepError("the pinned A2T report is not the attempt-3 BLEND arm")
    if report["frozen_cell"]["policy_config_sha256"] != FROZEN_POLICY_CONFIG_SHA256:
        raise SweepError("the pinned A2T report did not fly the locked v1 cell")

    receipt_path = repo_root / A2T_SUBSET_RECEIPT_RELPATH
    _require_hash(receipt_path, A2T_SUBSET_RECEIPT_SHA256, "the A2T-G1-104 receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt["split_name"] != A2T_SPLIT_ID or receipt["count"] != A2T_SPLIT_COUNT:
        raise SweepError("the A2T subset receipt identity drifted")
    sample_ids = tuple(sorted(str(item["sample_id"]) for item in receipt["items"]))

    bundle = load_a2t_bundle(data_root=data_root, repo_root=repo_root)
    run_dir = data_root / "runs" / A2T_RUN_ID / A2T_ATTEMPT_ID
    _require_hash(
        run_dir / A2T_PASS_A_BASENAME,
        A2T_PASS_A_SHA256,
        "the sealed A2T Pass-A direct outputs",
    )

    direct_texts: dict[str, str] = {}
    with (run_dir / A2T_PASS_A_BASENAME).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = str(row["direct_response_text"])
            if _sha256_text(text) != str(row["direct_response_sha256"]):
                raise SweepError(
                    f"{row['sample_id']}: Pass-A text does not hash to its own record"
                )
            direct_texts[str(row["sample_id"])] = text
    if tuple(sorted(direct_texts)) != sample_ids:
        raise SweepError("the landed Pass-A texts do not cover the subset exactly")

    query_vectors: dict[str, tuple[float, ...]] = {}
    text_digests: dict[str, str] = {}
    with (run_dir / "query-vectors.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            contact_id = str(record["contact_id"])
            if not contact_id.startswith("query:"):
                continue
            sample_id = contact_id.split("query:", 1)[1]
            query_vectors[sample_id] = tuple(float(v) for v in record["values"])
            text_digests[sample_id] = str(record["text_sha256"])
    missing = set(sample_ids) - set(query_vectors)
    if missing:
        raise SweepError(f"{len(missing)} A2T samples have no landed query vector")
    for sample_id in sample_ids:
        if _sha256_text(direct_texts[sample_id]) != text_digests[sample_id]:
            raise SweepError(
                f"{sample_id}: the Pass-A text does not re-hash to the digest the "
                "flight's own embedding record carries"
            )

    mechanical = json.loads(
        (run_dir / "arm2-blend-mechanical.json").read_text(encoding="utf-8")
    )
    flown_dispatched = {
        sample_id: not bool(mechanical[sample_id]["retained_primary"])
        for sample_id in sample_ids
    }
    flown_supply = {
        sample_id: tuple(
            sorted(mechanical[sample_id].get("fusion_selected_value_ids") or ())
        )
        for sample_id in sample_ids
    }

    final_texts: dict[str, str] = {}
    with (run_dir / "arm2-blend-outputs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            final_texts[str(row["sample_id"])] = str(row["final_response_text"])

    # ---- gold, and the frozen a2t-scorer-v1 read of the landed answers ----
    from ..data.audio2tool import load_expected_calls
    from ..data.lock import load_lock, umbrella_lock_path
    from ..rails.adapters.audio2tool import Audio2ToolAdapter

    lock = load_lock(umbrella_lock_path(repo_root))
    adapter = Audio2ToolAdapter(lock, data_root, repo_root=repo_root)
    gold_calls = load_expected_calls(lock, data_root, repo_root=repo_root)
    gold_target: dict[str, str] = {}
    baseline_correct: dict[str, bool] = {}
    for sample_id in sample_ids:
        calls = gold_calls.get(sample_id)
        if not calls:
            raise SweepError(f"{sample_id}: no gold tool calls")
        gold_target[sample_id] = str(calls[0].name)
        scored = adapter.score(
            _a2t_scoring_sample(sample_id), final_texts[sample_id]
        )
        baseline_correct[sample_id] = float(scored["tool_accuracy"]) == 1.0

    facet_vectors = cf._facet_vector_lookup(bundle)
    inputs = dc.LandedInputs(
        snapshot=bundle.snapshot,
        snapshot_sha256=bundle.snapshot_sha256,
        facet_vector_ids=bundle.facet_ids,
        facet_vector_matrix=bundle.matrix,
        facet_vectors=facet_vectors,
        facet_npz_sha256=bundle.npz_sha256,
        query_vectors=query_vectors,
        direct_texts=direct_texts,
        evidence_texts={},
        logged_supply=flown_supply,
        logged_winner_labels={},
        gold_by_sample=gold_target,
        round_scores={},
        round_reports={},
        label_targets=bundle.label_targets,
        label_texts=bundle.label_texts,
        values_by_id=bundle.values_by_id,
        content_facet_target=bundle.content_facet_target,
    )

    return CarrierInputs(
        carrier_id="audio2tool/A2T-G1-104",
        bundle=bundle,
        inputs=inputs,
        sample_ids=sample_ids,
        direct_texts=direct_texts,
        gold_target=gold_target,
        baseline_correct=baseline_correct,
        flown_dispatched=flown_dispatched,
        flown_supply=flown_supply,
        artifact_hashes={
            A2T_REPORT_BASENAME: report_sha,
            A2T_PASS_A_BASENAME: A2T_PASS_A_SHA256,
            "arm2-blend-mechanical.json": _sha256_file(
                run_dir / "arm2-blend-mechanical.json"
            ),
            "arm2-blend-outputs.jsonl": _sha256_file(
                run_dir / "arm2-blend-outputs.jsonl"
            ),
            "query-vectors.jsonl": _sha256_file(run_dir / "query-vectors.jsonl"),
            "snapshot": bundle.snapshot_sha256,
            "content-facet-npz": bundle.npz_sha256,
        },
        notes={
            "query_texts": (
                "the arm's OWN landed Pass-A direct decodes, each re-hashed "
                "against the text_sha256 of its own landed query-vector record"
            ),
            "gold": (
                "opened over the EXPOSED A2T-G1-104 only, whose seal the landed "
                "G1 read already broke; scored by the frozen a2t-scorer-v1 via "
                "Audio2ToolAdapter.score, reused and never reimplemented"
            ),
            "normalizer": "the campaign's A2T primary-tool carrier analogue",
        },
    )


def _a2t_scoring_sample(sample_id: str):
    """The placeholder sample ``Audio2ToolAdapter.score`` actually reads.

    ``a2t_read`` documents that ``score`` touches only ``sample.sample_id``;
    this reuses that module's own placeholder audio reference rather than
    constructing a second convention."""

    from ..rails.adapters.audio2tool import Audio2ToolSample

    return Audio2ToolSample(
        sample_id=sample_id,
        audio_ref=a2t_read._PLACEHOLDER_AUDIO_REF,
        audio_seconds=0.0,
        media_relpath="",
    )


def a2t_label_normalizer(response_text: object, label_targets: Mapping[str, str]):
    """The campaign's own A2T carrier analogue, byte-for-byte.

    Identical to the normalizer the flown launcher and the landed
    ``scripts/a2t_g1_dispatch_projection.py`` use: the answer's OWN parsed
    call list, PRIMARY tool name, matched EXACTLY against the label
    vocabulary. Gold is never consulted here."""

    from ..reproduction.toolcall_scoring import parse_tool_calls_text

    if not isinstance(response_text, str):
        return None
    try:
        calls, parsed = parse_tool_calls_text(response_text)
    except Exception:  # noqa: BLE001 - a defective answer is simply unlabelled
        return None
    if not parsed or not calls:
        return None
    identity = calls[0].name
    if not isinstance(identity, str) or not identity:
        return None
    matches = sorted(
        facet_id for facet_id, target in label_targets.items() if target == identity
    )
    return matches[0] if matches else None


def load_slurp_carrier(*, data_root: Path, repo_root: Path) -> tuple[
    CarrierInputs, dict[str, object], Mapping[str, cf.SampleReplay]
]:
    """The SLURP DEV-1000 BLEND arm restricted to the UNEXPOSED NEW500.

    Loaded through ``k1_hybrid_ranking_gate``'s own pins and
    ``contrast_fewshot_preanalysis``'s own loaders, and gated by
    ``cf.replay_population``'s own flight gate -- including K1's proved
    v2-override exception, since the DEV-1000 arm flew the v2 delta-override
    that the lock read falsified and the locked v1 cell does not carry."""

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    bundle = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    populations = k1.load_populations(repo_root)
    pin_hashes = k1.assert_dev1000_byte_pins(repo_root=repo_root, data_root=data_root)
    override_fires = k1.load_override_fires(data_root=data_root)
    population = cf.load_cell_population(
        pin=k1.DEV1000_PIN,
        bundle=bundle,
        populations=populations,
        data_root=data_root,
        repo_root=repo_root,
    )
    replays, flight_gate = cf.replay_population(population, bundle)
    mismatches = {
        str(item["sample_id"])
        for item in flight_gate["retain_dispatch_decision_mismatches"]
    }
    unexplained = mismatches - override_fires
    flight_gate["v2_override_deviation"] = {
        "explanation": (
            "the DEV-1000 BLEND arm flew the v2 delta>=0.14 retain-override, which "
            "the lock read FALSIFIED out of sample and which the locked v1 cell "
            "does not carry; the v1 replay therefore disagrees with the flown "
            "contact count on exactly the override fires"
        ),
        "override_fires_in_population": len(
            override_fires & set(population.sample_ids)
        ),
        "mismatches_all_explained_by_the_override": not unexplained,
        "unexplained_mismatch_sample_ids": sorted(unexplained)[:10],
    }
    if unexplained:
        raise SweepError(
            f"{len(unexplained)} SLURP dispatch mismatches are NOT override fires"
        )
    if not flight_gate["supply_gate_passed"]:
        raise SweepError("the flown SLURP SUPPLY was not reproduced exactly")
    query_identity = k1.assert_query_text_identity(population=population)
    if not query_identity["passed"]:
        raise SweepError("a SLURP direct text does not match its flown query digest")
    flight_gate["query_text_identity"] = query_identity

    carrier = CarrierInputs(
        carrier_id="slurp/DEV-1000-NEW500",
        bundle=bundle,
        inputs=population.inputs,
        sample_ids=tuple(population.sample_ids),
        direct_texts=population.inputs.direct_texts,
        gold_target={
            sample_id: replays[sample_id].gold_target
            for sample_id in population.sample_ids
        },
        baseline_correct={
            sample_id: bool(replays[sample_id].correct)
            for sample_id in population.sample_ids
        },
        flown_dispatched={
            sample_id: population.logged_contacts[sample_id] == 2
            for sample_id in population.sample_ids
        },
        flown_supply={
            sample_id: tuple(sorted(population.inputs.logged_supply.get(sample_id, ())))
            for sample_id in population.sample_ids
        },
        artifact_hashes={**dict(population.artifact_hashes), **pin_hashes},
        notes={
            "role": (
                "the SCALE CONTROL and the carrier the pre-registered "
                "tuning-versus-defect discriminator is evaluated against"
            ),
            "normalizer": "kb_policy.default_label_normalizer (the SLU analogue)",
        },
    )
    return carrier, flight_gate, replays


# ---------------------------------------------------------------------------
# Recall, once per trajectory, shared by every variant
# ---------------------------------------------------------------------------


def base_recall_scores(carrier: CarrierInputs) -> tuple[
    dict[str, dict[str, dict[str, float]]], dict[str, object]
]:
    """``multidim_recall`` at the frozen top-k for every trajectory.

    Vectorised through ``cf.vectorised_recall`` -- the same function the
    contrast-fewshot and K1 rows already gated -- and cross-checked against a
    REAL ``kb.multidim_recall`` call on the first
    :data:`RECALL_FIDELITY_PROBES` trajectories before any variant is scored.
    The recall stage is variant-INDEPENDENT by construction (every variant
    changes only how the recalled scores are combined), so it is computed once.
    """

    import numpy as np

    bundle = carrier.bundle
    inputs = carrier.inputs
    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)

    recalls: dict[str, dict[str, dict[str, float]]] = {}
    probes = 0
    for position, sample_id in enumerate(carrier.sample_ids):
        query = np.asarray(inputs.query_vectors[sample_id], dtype=np.float64)
        denominator = facet_norms * float(np.linalg.norm(query))
        with np.errstate(divide="ignore", invalid="ignore"):
            cosines = np.where(denominator > 0.0, matrix @ query / denominator, 0.0)
        scores = cf.vectorised_recall(bundle, cosines, top_k=FROZEN_TOP_K)
        if position < RECALL_FIDELITY_PROBES:
            reference = kb.multidim_recall(
                bundle.snapshot,
                {"content": inputs.query_vectors[sample_id]},
                inputs.facet_vectors,
                FROZEN_TOP_K,
            )
            if set(reference) != set(scores):
                raise SweepError(
                    f"{sample_id}: vectorised recall admitted a different facet set "
                    "than kb.multidim_recall"
                )
            for facet_id, dim_scores in reference.items():
                for dimension, score in dim_scores.items():
                    if abs(score - scores[facet_id][dimension]) > 1e-9:
                        raise SweepError(
                            f"{sample_id}/{facet_id}/{dimension}: vectorised recall "
                            "disagrees with kb.multidim_recall"
                        )
            probes += 1
        recalls[sample_id] = scores
    return recalls, {
        "probes_cross_checked_against_kb_multidim_recall": probes,
        "trajectories": len(recalls),
        "top_k_per_dimension": FROZEN_TOP_K,
    }


# ---------------------------------------------------------------------------
# 1. The scale audit
# ---------------------------------------------------------------------------


def scale_audit(
    carrier: CarrierInputs,
    recalls: Mapping[str, Mapping[str, Mapping[str, float]]],
) -> dict[str, object]:
    """Every ranker dimension's score distribution, and the eviction it causes.

    The ranker is ``w_cos * max_cosine + w_prior * max_prior + w_agree *
    agreement``. This measures each of the three terms as the ranker itself
    sees them, on the recalled candidate pool, per trajectory.
    """

    bundle = carrier.bundle
    global_max = snapshot_max_prior_mass(bundle.snapshot)

    prior_recall = bundle.prior_dimension_recall
    prior_by_dimension: dict[str, list[float]] = {}
    for facet_id, dim_scores in prior_recall.items():
        for dimension, score in dim_scores.items():
            prior_by_dimension.setdefault(dimension, []).append(score)

    best_cosines: list[float] = []
    content_in_top_m: list[int] = []
    prior_facets_above_best_content: list[int] = []
    admissible_content: list[int] = []
    admissible_content_outranked: list[int] = []
    agreement_values: set[float] = set()
    dims_total_values: set[int] = set()
    single_dimension_facets = 0
    total_facets = 0

    for sample_id in carrier.sample_ids:
        scores = recalls[sample_id]
        dims_total = len({dim for s in scores.values() for dim in s})
        dims_total_values.add(dims_total)
        cosine_scores: list[tuple[float, str]] = []
        prior_scores: list[tuple[float, str]] = []
        for facet_id, dim_scores in scores.items():
            total_facets += 1
            if len(dim_scores) == 1:
                single_dimension_facets += 1
            agreement_values.add(len(dim_scores) / dims_total if dims_total else 0.0)
            if _is_cosine_family(dim_scores):
                cosine_scores.append((_max_cosine(dim_scores), facet_id))
            else:
                prior_scores.append((_max_prior(dim_scores), facet_id))
        best_cosine = max((score for score, _ in cosine_scores), default=0.0)
        best_cosines.append(best_cosine)
        ranked = sorted(
            (
                (
                    FROZEN_WEIGHTS.w_cos * _max_cosine(dim_scores)
                    + FROZEN_WEIGHTS.w_prior * _max_prior(dim_scores)
                    + FROZEN_WEIGHTS.w_agree
                    * (len(dim_scores) / dims_total if dims_total else 0.0),
                    facet_id,
                )
                for facet_id, dim_scores in scores.items()
            ),
            key=lambda item: (-item[0], item[1]),
        )
        top_m = [facet_id for _score, facet_id in ranked[: FROZEN_FUSE.m]]
        content_in_top_m.append(
            sum(1 for facet_id in top_m if _is_cosine_family(scores[facet_id]))
        )
        best_content_score = max(
            (
                score
                for score, facet_id in ranked
                if _is_cosine_family(scores[facet_id])
            ),
            default=0.0,
        )
        prior_facets_above_best_content.append(
            sum(
                1
                for score, facet_id in ranked
                if not _is_cosine_family(scores[facet_id])
                and score > best_content_score
            )
        )
        admissible = [
            facet_id
            for _score, facet_id in ranked
            if _is_cosine_family(scores[facet_id])
            and _max_cosine(scores[facet_id]) >= FROZEN_FUSE.tau
        ]
        admissible_content.append(len(admissible))
        admissible_scores = {
            facet_id: FROZEN_WEIGHTS.w_cos * _max_cosine(scores[facet_id])
            + FROZEN_WEIGHTS.w_agree
            * (len(scores[facet_id]) / dims_total if dims_total else 0.0)
            for facet_id in admissible
        }
        worst_admissible = min(admissible_scores.values(), default=None)
        if worst_admissible is None:
            admissible_content_outranked.append(0)
        else:
            admissible_content_outranked.append(
                sum(
                    1
                    for score, facet_id in ranked
                    if not _is_cosine_family(scores[facet_id])
                    and score > worst_admissible
                )
            )

    bound = FROZEN_WEIGHTS.w_cos * FROZEN_FUSE.tau / FROZEN_WEIGHTS.w_prior
    return {
        "ranker": {
            "form": "w_cos * max_cosine + w_prior * max_prior + w_agree * agreement",
            "w_cos": FROZEN_WEIGHTS.w_cos,
            "w_prior": FROZEN_WEIGHTS.w_prior,
            "w_agree": FROZEN_WEIGHTS.w_agree,
            "tau": FROZEN_FUSE.tau,
            "m": FROZEN_FUSE.m,
            "top_k_per_dimension": FROZEN_TOP_K,
        },
        "dimension_inventory": {
            "facets_by_dimension": dict(
                Counter(facet.dimension for facet in carrier.bundle.snapshot.facets)
            ),
            "prior_mass_dimensions": sorted(kb.PRIOR_MASS_DIMENSIONS),
            "dims_total_observed": sorted(dims_total_values),
            "agreement_values_observed": sorted(agreement_values),
            "recalled_facets_carrying_exactly_one_dimension": single_dimension_facets,
            "recalled_facets_total": total_facets,
            "agreement_term_is_constant_and_cancels": len(agreement_values) == 1,
        },
        "cosine_dimension": {
            "best_content_cosine_per_trajectory": _descriptives(best_cosines),
            "trajectories_with_best_cosine_at_or_above_tau": sum(
                1 for value in best_cosines if value >= FROZEN_FUSE.tau
            ),
            "weighted_contribution_at_tau": FROZEN_WEIGHTS.w_cos * FROZEN_FUSE.tau,
            "weighted_contribution_at_max": FROZEN_WEIGHTS.w_cos
            * max(best_cosines, default=0.0),
        },
        "prior_mass_dimensions": {
            "recalled_prior_mass_facets": len(prior_recall),
            "per_dimension_scores": {
                dimension: _descriptives(values)
                for dimension, values in sorted(prior_by_dimension.items())
            },
            "recalled_prior_masses_sorted_desc": sorted(
                (
                    max(dim_scores.values())
                    for dim_scores in prior_recall.values()
                ),
                reverse=True,
            ),
            "snapshot_max_prior_mass": global_max,
            "weighted_contribution_at_snapshot_max": FROZEN_WEIGHTS.w_prior
            * global_max,
            "prior_recall_is_query_independent": (
                "prior-mass recall reads no vector: it is the same candidate set "
                "and the same scores for every trajectory on a given snapshot"
            ),
        },
        "the_invariant": {
            "statement": (
                "every ADMISSIBLE content facet outranks every prior-mass facet if "
                "and only if w_prior * sup(prior_score) < w_cos * tau, because the "
                "agreement term is identical for every recalled facet and cancels"
            ),
            "required_bound_on_sup_prior_score": bound,
            "measured_sup_prior_score": global_max,
            "invariant_holds": global_max < bound,
            "margin": bound - global_max,
            "why_it_was_never_written_down": (
                "on SLURP prior_score is intent_total_in_scenario / scenario_total "
                "and intent is nested strictly inside scenario, so the ratio is a "
                "genuine conditional probability and cannot exceed 1; the cell was "
                "inside the bound by construction and nothing had to enforce it"
            ),
        },
        "eviction": {
            "content_facets_in_the_top_m_window": _descriptives(content_in_top_m),
            "trajectories_with_zero_content_facets_in_top_m": sum(
                1 for value in content_in_top_m if value == 0
            ),
            "prior_facets_ranked_above_the_best_content_facet": _descriptives(
                prior_facets_above_best_content
            ),
            "admissible_content_facets_per_trajectory": _descriptives(
                admissible_content
            ),
            "prior_facets_ranked_above_the_WEAKEST_admissible_content_facet": (
                _descriptives(admissible_content_outranked)
            ),
            "trajectories_where_any_prior_facet_outranks_an_admissible_content_facet": (
                sum(1 for value in admissible_content_outranked if value > 0)
            ),
            "m_needed_to_admit_every_admissible_content_facet": max(
                (
                    outranked + admissible
                    for outranked, admissible in zip(
                        admissible_content_outranked, admissible_content
                    )
                ),
                default=0,
            ),
        },
    }


# ---------------------------------------------------------------------------
# 2. The variant sweep
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VariantSample:
    """One trajectory under one variant."""

    sample_id: str
    dispatched: bool
    retain_primary: bool
    direct_label_recovered: bool
    supply_empty: bool
    selected_value_ids: tuple[str, ...]
    admitted_facet_ids: tuple[str, ...]
    content_facets_in_top_m: int
    gold_facet_admitted: bool
    gold_supplied: bool
    gold_target_rank: int | None
    supplied_targets: tuple[str, ...]
    supplied_value_count: int
    evidence_characters: int
    correct: bool
    direct_correct: bool
    baseline_dispatched: bool
    supply_identical_to_baseline: bool


def _evidence_characters(
    snapshot_values: Mapping[str, object], selected_value_ids: Sequence[str]
) -> int:
    """Characters the evidence block would carry for one supply.

    ``rails.runner._agent_messages`` renders one text part per VISIBLE VALUE
    (the controller never populates ``visible_facet_ids``, so no key facet is
    ever rendered) plus the transport's per-part evidence marker. This counts
    the value contents and the markers and nothing else; the fixed control
    instruction is variant-independent and is added once by
    :func:`token_model`."""

    total = 0
    for index, value_id in enumerate(sorted(set(selected_value_ids))):
        value = snapshot_values[value_id]
        marker = "[evidence %03d:value:value] " % index
        total += len(marker) + len(str(value.content))
    return total


def sweep_carrier(
    carrier: CarrierInputs,
    recalls: Mapping[str, Mapping[str, Mapping[str, float]]],
    *,
    normalizer,
    variants: Sequence[Variant] = VARIANTS,
) -> tuple[dict[str, dict[str, VariantSample]], dict[str, object]]:
    """Every variant over every trajectory, through kb's own stages."""

    bundle = carrier.bundle
    inputs = carrier.inputs
    global_max = snapshot_max_prior_mass(bundle.snapshot)
    direct_labels = {
        sample_id: normalizer(carrier.direct_texts[sample_id], inputs.label_targets)
        for sample_id in carrier.sample_ids
    }

    baseline: dict[str, VariantSample] = {}
    out: dict[str, dict[str, VariantSample]] = {}
    timings: dict[str, float] = {}

    for variant in variants:
        started = time.perf_counter()
        is_baseline = variant.variant_id == BASELINE_VARIANT_ID
        rows: dict[str, VariantSample] = {}
        for sample_id in carrier.sample_ids:
            supply = variant_supply(
                inputs,
                sample_id,
                base_recall=recalls[sample_id],
                variant=variant,
                global_max_prior=global_max,
            )
            blend = dc.replay_blend(
                inputs,
                supply,
                direct_label=direct_labels[sample_id],
                alpha=FROZEN_ALPHA,
            )
            supply_empty = not supply.selected_value_ids
            dispatched = (not supply_empty) and (not blend.retain_primary)
            gold = carrier.gold_target[sample_id]
            admitted = tuple(sorted(supply.admitted_facet_ids))
            gold_facet_admitted = any(
                bundle.content_facet_target.get(facet_id) == gold
                for facet_id in admitted
            )
            supplied_targets = tuple(
                sorted(
                    {
                        str(bundle.values_by_id[value_id].task_target)
                        for value_id in supply.selected_value_ids
                        if bundle.values_by_id[value_id].task_target is not None
                    }
                )
            )
            fused_ranked = cf._fused_ranked_targets(
                blend.fused_label_scores, inputs.label_targets
            )
            gold_fused_rank = next(
                (
                    position
                    for position, (target, _score) in enumerate(fused_ranked, start=1)
                    if target == gold
                ),
                None,
            )
            content_in_top_m = sum(
                1
                for facet_id in supply.top_m_facet_ids
                if _is_cosine_family(supply.recall_scores.get(facet_id, {}))
            )
            baseline_row = baseline.get(sample_id)
            rows[sample_id] = VariantSample(
                sample_id=sample_id,
                dispatched=dispatched,
                retain_primary=bool(blend.retain_primary),
                direct_label_recovered=direct_labels[sample_id] is not None,
                supply_empty=supply_empty,
                selected_value_ids=tuple(sorted(supply.selected_value_ids)),
                admitted_facet_ids=admitted,
                content_facets_in_top_m=content_in_top_m,
                gold_facet_admitted=gold_facet_admitted,
                gold_supplied=gold in supplied_targets,
                gold_target_rank=gold_fused_rank,
                supplied_targets=supplied_targets,
                supplied_value_count=len(supply.selected_value_ids),
                evidence_characters=_evidence_characters(
                    bundle.values_by_id, supply.selected_value_ids
                ),
                correct=bool(carrier.baseline_correct[sample_id]),
                direct_correct=bool(carrier.baseline_correct[sample_id]),
                baseline_dispatched=(
                    dispatched
                    if is_baseline
                    else (bool(baseline_row.dispatched) if baseline_row else False)
                ),
                supply_identical_to_baseline=(
                    True
                    if is_baseline
                    else (
                        baseline_row is not None
                        and baseline_row.selected_value_ids
                        == tuple(sorted(supply.selected_value_ids))
                    )
                ),
            )
        if variant.variant_id == BASELINE_VARIANT_ID:
            baseline = rows
        out[variant.variant_id] = rows
        timings[variant.variant_id] = time.perf_counter() - started

    return out, {
        "variants": len(variants),
        "trajectories": len(carrier.sample_ids),
        "seconds_per_variant": timings,
        "baseline_variant_id": BASELINE_VARIANT_ID,
        "note": (
            "baseline_dispatched / supply_identical_to_baseline are filled from "
            "the V0-FROZEN pass, which is evaluated first"
        ),
    }


def baseline_fidelity_gate(
    carrier: CarrierInputs,
    rows: Mapping[str, VariantSample],
    *,
    supply_checked_on: str = "all",
    explained_decision_mismatch_ids: frozenset[str] = frozenset(),
) -> dict[str, object]:
    """V0-FROZEN must reproduce the FLOWN decision on every trajectory.

    ``supply_checked_on`` exists because the two carriers log supply
    differently: the A2T arm dispatched nothing, so its per-sample record
    carries a null supply on every trajectory and the comparison is total. The
    SLURP arm logs a SUPPLY channel only where it actually dispatched, so the
    honest comparison there is on the flown-dispatched subset -- which is the
    same subset ``cf.replay_population``'s own gate checks, and that gate has
    already run and passed before this one is reached.

    ``explained_decision_mismatch_ids`` carries the DEV-1000 arm's v2
    delta-override fires: that arm flew the v2 candidate the lock read
    falsified, so a v1 replay MUST disagree with it on exactly those samples.
    """

    decision_matches = 0
    decision_mismatches: list[str] = []
    supply_matches = 0
    supply_checked = 0
    supply_mismatches: list[str] = []
    for sample_id in carrier.sample_ids:
        row = rows[sample_id]
        if row.dispatched == carrier.flown_dispatched[sample_id]:
            decision_matches += 1
        else:
            decision_mismatches.append(sample_id)
        if supply_checked_on == "dispatched" and not carrier.flown_dispatched[sample_id]:
            continue
        supply_checked += 1
        if row.selected_value_ids == carrier.flown_supply[sample_id]:
            supply_matches += 1
        else:
            supply_mismatches.append(sample_id)
    total = len(carrier.sample_ids)
    unexplained = sorted(set(decision_mismatches) - set(explained_decision_mismatch_ids))
    return {
        "trajectories": total,
        "supply_checked_on": supply_checked_on,
        "flown_dispatch_decision_reproduced": decision_matches,
        "dispatch_mismatch_sample_ids": decision_mismatches[:10],
        "explained_decision_mismatches": len(decision_mismatches) - len(unexplained),
        "unexplained_decision_mismatch_sample_ids": unexplained[:10],
        "supply_comparisons": supply_checked,
        "flown_supply_reproduced": supply_matches,
        "supply_mismatch_sample_ids": supply_mismatches[:10],
        "passed": not unexplained and supply_matches == supply_checked,
    }


def variant_table(
    carrier: CarrierInputs,
    sweep: Mapping[str, Mapping[str, VariantSample]],
    token_calibration: Mapping[str, object] | None,
) -> dict[str, object]:
    """The headline table: one row per variant."""

    table: dict[str, object] = {}
    baseline_rows = sweep[BASELINE_VARIANT_ID]
    for variant in VARIANTS:
        rows = sweep[variant.variant_id]
        dispatched = [row for row in rows.values() if row.dispatched]
        counts = Counter(row.supplied_value_count for row in rows.values())
        changed_supply = sum(
            1
            for sample_id, row in rows.items()
            if row.selected_value_ids != baseline_rows[sample_id].selected_value_ids
        )
        changed_admitted = sum(
            1
            for sample_id, row in rows.items()
            if row.admitted_facet_ids != baseline_rows[sample_id].admitted_facet_ids
        )
        changed_dispatch = sum(
            1
            for sample_id, row in rows.items()
            if row.dispatched != baseline_rows[sample_id].dispatched
        )
        worst_chars = max((row.evidence_characters for row in rows.values()), default=0)
        table[variant.variant_id] = {
            "family": variant.family,
            "change": variant.change,
            "prior_transform": variant.prior_transform,
            "m": variant.m,
            "admission": variant.admission,
            "trajectories": len(rows),
            "would_dispatch": len(dispatched),
            "dispatch_rate": len(dispatched) / max(1, len(rows)),
            "trajectories_with_any_admitted_facet": sum(
                1 for row in rows.values() if row.admitted_facet_ids
            ),
            "trajectories_with_content_in_top_m": sum(
                1 for row in rows.values() if row.content_facets_in_top_m > 0
            ),
            "content_facets_in_top_m": _descriptives(
                [row.content_facets_in_top_m for row in rows.values()]
            ),
            "gold_bearing_supply_admitted": sum(
                1 for row in rows.values() if row.gold_supplied
            ),
            "gold_bearing_supply_admitted_on_dispatched": sum(
                1 for row in dispatched if row.gold_supplied
            ),
            "gold_facet_inside_admitted_window": sum(
                1 for row in rows.values() if row.gold_facet_admitted
            ),
            "supplied_value_count_distribution": {
                str(count): occurrences for count, occurrences in sorted(counts.items())
            },
            "supplied_value_count": _descriptives(
                [row.supplied_value_count for row in rows.values()]
            ),
            "trajectories_whose_supply_differs_from_the_frozen_cell": changed_supply,
            "trajectories_whose_admitted_set_differs_from_the_frozen_cell": (
                changed_admitted
            ),
            "trajectories_whose_dispatch_differs_from_the_frozen_cell": (
                changed_dispatch
            ),
            "dispatch_sample_ids": sorted(row.sample_id for row in dispatched),
            "dispatch_equals_direct_label_not_recovered": (
                sorted(row.sample_id for row in dispatched)
                == sorted(
                    row.sample_id
                    for row in rows.values()
                    if not row.direct_label_recovered
                )
            ),
            "evidence_prompt_token_estimate": (
                estimate_tokens(worst_chars, token_calibration)
                if token_calibration is not None
                else {
                    "estimate": False,
                    "worst_evidence_characters": worst_chars,
                    "note": (
                        "the token model is calibrated against the AUDIO2TOOL "
                        "prompt-fit receipt and does not apply to this carrier"
                    ),
                }
            ),
        }
    return table


def alpha_gate_analysis(
    carrier: CarrierInputs,
    sweep: Mapping[str, Mapping[str, VariantSample]],
) -> dict[str, object]:
    """The SECOND gate, which admission repair does not touch.

    ``kb._blend_scores`` gives the direct label ``alpha * fused + (1 - alpha)``
    and every other label ``alpha * fused``. ``kb._fused_label_scores``
    normalizes the fused scores to sum to 1, so no label's fused score can
    exceed 1. Therefore whenever a direct label IS recovered:

        blended[direct]  >=  1 - alpha  =  0.55
        blended[other]   <=  alpha      =  0.45

    and the direct label wins uniquely, for EVERY supply, at the frozen
    ``alpha = 0.45``. Repairing admission cannot change that. So the set of
    trajectories the supply path can ever act on is exactly the set whose
    direct answer yields NO in-vocabulary label -- an upper bound on the
    reachable population that is arithmetic, not empirical. This function
    measures the bound and checks it against every variant.
    """

    label_free = sorted(
        sample_id
        for sample_id, row in sweep[BASELINE_VARIANT_ID].items()
        if not row.direct_label_recovered
    )
    per_variant = {}
    for variant in VARIANTS:
        rows = sweep[variant.variant_id]
        dispatched = sorted(row.sample_id for row in rows.values() if row.dispatched)
        per_variant[variant.variant_id] = {
            "would_dispatch": len(dispatched),
            "dispatched_outside_the_label_free_set": sorted(
                set(dispatched) - set(label_free)
            ),
            "label_free_trajectories_not_dispatched": len(
                set(label_free) - set(dispatched)
            ),
        }
    return {
        "arithmetic": (
            "at alpha = %.2f a recovered direct label scores at least %.2f while "
            "every rival scores at most %.2f, because kb._fused_label_scores "
            "normalizes the fused scores to sum to 1; the direct label therefore "
            "wins uniquely for EVERY possible supply"
        )
        % (FROZEN_ALPHA, 1.0 - FROZEN_ALPHA, FROZEN_ALPHA),
        "alpha": FROZEN_ALPHA,
        "direct_label_wins_unconditionally_while_alpha_below": 0.5,
        "trajectories": len(carrier.sample_ids),
        "direct_label_recovered": len(carrier.sample_ids) - len(label_free),
        "label_free_trajectories": len(label_free),
        "label_free_sample_ids": label_free,
        "reachable_ceiling_share": len(label_free) / max(1, len(carrier.sample_ids)),
        "by_variant": per_variant,
        "consequence": (
            "ADMISSION REPAIR IS NECESSARY BUT NOT SUFFICIENT. However the top-m "
            "window is fixed, the supply path can only ever change the answer of a "
            "trajectory whose direct decode produced no in-vocabulary label. Every "
            "other trajectory retains by arithmetic"
        ),
    }


# ---------------------------------------------------------------------------
# The token model -- an ESTIMATE, always labelled
# ---------------------------------------------------------------------------


def token_calibration(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Characters per token, calibrated against the LANDED prompt-fit receipt.

    The receipt measured two envelopes with the resident tokenizer: the direct
    envelope at 13,236 text tokens and the worst-case evidence envelope at
    19,047. They differ by exactly the evidence block the worst case carried --
    the five LONGEST facet representations and the six LONGEST value contents
    in the snapshot, plus the fixed control instruction. Reconstructing that
    block's character count locally therefore fixes a characters-per-token
    constant with zero contacts.
    """

    check_dir = Path(repo_root) / A2T_CHECK_DIR_RELPATH
    _require_hash(
        check_dir / A2T_PROMPT_FIT_BASENAME,
        A2T_PROMPT_FIT_SHA256,
        "the landed np2 prompt-fit receipt",
    )
    receipt = json.loads(
        (check_dir / A2T_PROMPT_FIT_BASENAME).read_text(encoding="utf-8")
    )
    by_envelope = {
        str(entry["envelope_id"]): entry for entry in receipt["envelopes"]
    }
    m0_tokens = int(by_envelope["m0-direct-decode"]["text_prompt_tokens"])
    blend_tokens = int(
        by_envelope["blend-evidence-decode-worst"]["text_prompt_tokens"]
    )
    if (m0_tokens, blend_tokens) != (
        PROMPT_FIT_M0_TEXT_TOKENS,
        PROMPT_FIT_BLEND_TEXT_TOKENS,
    ):
        raise SweepError("the landed prompt-fit envelopes moved")

    snapshot_path = Path(data_root) / A2T_SNAPSHOT_RELPATH
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    key_texts = [
        str(facet["representation"])
        for facet in sorted(
            snapshot["facets"], key=lambda f: -len(str(f.get("representation", "")))
        )[: FROZEN_FUSE.m]
    ]
    value_texts = [
        str(value["content"])
        for value in sorted(
            snapshot["values"], key=lambda v: -len(str(v.get("content", "")))
        )[: FROZEN_FUSE.c * FROZEN_FUSE.top_l]
    ]
    control_instruction = (
        "Decide under the task contract already given above, now "
        "considering the retrieved evidence. Answer using the speech "
        "query together with the supplied knowledge evidence."
    )
    characters = len(control_instruction)
    for index, text in enumerate(key_texts):
        characters += len("[evidence %03d:key:facet] " % index) + len(text)
    for offset, text in enumerate(value_texts):
        index = len(key_texts) + offset
        characters += len("[evidence %03d:value:value] " % index) + len(text)

    evidence_tokens = blend_tokens - m0_tokens
    return {
        "measured_direct_envelope_text_tokens": m0_tokens,
        "measured_worst_evidence_envelope_text_tokens": blend_tokens,
        "measured_evidence_block_tokens": evidence_tokens,
        "reconstructed_worst_evidence_block_characters": characters,
        "characters_per_token": characters / evidence_tokens,
        "control_instruction_characters": len(control_instruction),
        "basis": (
            "the ALREADY-LANDED prompt-fit-np2.json receipt, whose two envelopes "
            "were measured by the resident tokenizer at a registered contact. "
            "NOTHING is tokenized here"
        ),
        "conservatism": (
            "the landed worst case also counted FIVE key facets, which "
            "rails.runner._agent_messages never renders for this controller "
            "because the controller leaves visible_facet_ids empty; the constant "
            "is therefore derived from a block LARGER than any variant can emit"
        ),
        "slot_tokens": DERIVED_SLOT_TOKENS,
        "speech_worst_tokens": PROMPT_FIT_SPEECH_WORST,
        "output_ceiling_tokens": PROMPT_FIT_OUTPUT_CEILING,
        "special_token_reserve": PROMPT_FIT_SPECIAL_RESERVE,
    }


def estimate_tokens(
    evidence_characters: int, calibration: Mapping[str, object]
) -> dict[str, object]:
    """One variant's worst evidence prompt against the derived slot."""

    per_token = float(calibration["characters_per_token"])
    total_characters = evidence_characters + int(
        calibration["control_instruction_characters"]
    )
    evidence_tokens = math.ceil(total_characters / per_token)
    required = (
        int(calibration["measured_direct_envelope_text_tokens"])
        + evidence_tokens
        + int(calibration["speech_worst_tokens"])
        + int(calibration["output_ceiling_tokens"])
        + int(calibration["special_token_reserve"])
    )
    slot = int(calibration["slot_tokens"])
    return {
        "estimate": True,
        "worst_evidence_characters": evidence_characters,
        "estimated_evidence_block_tokens": evidence_tokens,
        "estimated_required_tokens_per_slot": required,
        "derived_slot_tokens": slot,
        "estimated_margin": slot - required,
        "fits": required <= slot,
    }


# ---------------------------------------------------------------------------
# 3. The decisive quantity
# ---------------------------------------------------------------------------


def decisive_quantities(
    carrier: CarrierInputs,
    sweep: Mapping[str, Mapping[str, VariantSample]],
) -> dict[str, object]:
    """For the dispatching variants: the conversion PRECONDITION, then a band.

    The precondition is measured on this carrier and is not a projection: how
    many trajectories that are WRONG TODAY would carry the gold tool's facet
    inside the admitted window, and how many would actually have gold in the
    supplied set. The accuracy band on top of it is a PROJECTION built from
    conversion anchors MEASURED ON SLURP and imported from
    ``k1_hybrid_ranking_gate``; Audio2Tool has NO measured conversion anchors
    of its own, and the first dispatching A2T flight is what would establish
    them.
    """

    wrong_today = [
        sample_id
        for sample_id in carrier.sample_ids
        if not carrier.baseline_correct[sample_id]
    ]
    correct_today = [
        sample_id
        for sample_id in carrier.sample_ids
        if carrier.baseline_correct[sample_id]
    ]
    out: dict[str, object] = {
        "population": {
            "n": len(carrier.sample_ids),
            "correct_today": len(correct_today),
            "wrong_today": len(wrong_today),
        },
        "anchors": {
            "source": (
                "MEASURED ON SLURP and imported from "
                "analysis.k1_hybrid_ranking_gate; pooled over the three sealed "
                "SLURP populations"
            ),
            "fused_top1": k1.ANCHOR_TOP1,
            "fused_rank_2_or_3": k1.ANCHOR_RANK23,
            "absent": k1.ANCHOR_ABSENT,
            "fused_rank_4_plus_EXTRAPOLATED": k1.ANCHOR_RANK4PLUS_EXTRAPOLATED,
        },
        "CROSS_CARRIER_WARNING": (
            "AUDIO2TOOL HAS NO MEASURED CONVERSION ANCHORS. Every projected band "
            "below prices an Audio2Tool trajectory at a rate measured on SLURP "
            "spoken-SLU intent recovery, a different task with a different label "
            "space, a different answer shape and a different frozen-core failure "
            "profile. The bands are DESIGN INPUTS for sizing a flight, never "
            "results, and the FIRST DISPATCHING AUDIO2TOOL FLIGHT IS WHAT WOULD "
            "ESTABLISH THIS CARRIER'S OWN ANCHORS"
        ),
        "by_variant": {},
    }

    for variant in VARIANTS:
        rows = sweep[variant.variant_id]
        dispatched = [row for row in rows.values() if row.dispatched]
        if not dispatched:
            out["by_variant"][variant.variant_id] = {
                "would_dispatch": 0,
                "note": "no trajectory dispatches; there is nothing to convert",
            }
            continue
        wrong_dispatched = [row for row in dispatched if not row.correct]
        correct_dispatched = [row for row in dispatched if row.correct]
        wrong_rows = [row for row in rows.values() if not row.correct]
        correct_rows = [row for row in rows.values() if row.correct]
        projection = k1.conversion_projection(replays=rows, natives=rows)
        out["by_variant"][variant.variant_id] = {
            "would_dispatch": len(dispatched),
            "dispatched_and_wrong_today": len(wrong_dispatched),
            "dispatched_and_correct_today": len(correct_dispatched),
            "wrong_today_with_gold_facet_in_the_admitted_window": sum(
                1 for row in wrong_dispatched if row.gold_facet_admitted
            ),
            "wrong_today_with_gold_bearing_supply": sum(
                1 for row in wrong_dispatched if row.gold_supplied
            ),
            "wrong_today_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE": sum(
                1 for row in wrong_rows if row.gold_supplied
            ),
            "correct_today_with_gold_bearing_supply": sum(
                1 for row in correct_rows if row.gold_supplied
            ),
            "wrong_today_with_gold_at_fused_target_rank_1": sum(
                1 for row in wrong_dispatched if row.gold_target_rank == 1
            ),
            "wrong_today_with_gold_at_fused_target_rank_2_or_3": sum(
                1 for row in wrong_dispatched if row.gold_target_rank in (2, 3)
            ),
            "correct_today_dispatched_without_gold_bearing_supply": sum(
                1 for row in correct_dispatched if not row.gold_supplied
            ),
            "gold_fused_rank_distribution_on_dispatched": {
                str(rank): count
                for rank, count in sorted(
                    Counter(
                        row.gold_target_rank if row.gold_target_rank else 0
                        for row in dispatched
                    ).items()
                )
            },
            "projected_band_CROSS_CARRIER": projection,
        }
    return out


# ---------------------------------------------------------------------------
# 4. Fix verification -- the properties a correct implementation must have
# ---------------------------------------------------------------------------

#: Which candidate forms are commensurable, order-preserving and
#: query-independent. Fixed here as a PROPERTY table, not inferred from the
#: Audio2Tool numbers: the question is which form is PRINCIPLED, never which
#: form scores best on one carrier.
TRANSFORM_PROPERTIES: Mapping[str, Mapping[str, object]] = {
    "none": {
        "bounded_output": False,
        "order_preserving": True,
        "query_independent": True,
        "single_change_to_the_ranker": True,
        "note": (
            "the defect itself: an unbounded score inside a weighted sum with a "
            "score bounded by 1"
        ),
    },
    "clip1": {
        "bounded_output": True,
        "order_preserving": False,
        "query_independent": True,
        "single_change_to_the_ranker": True,
        "note": (
            "restores the declared bound but flattens every mass above 1 into a "
            "tie, so it is a GUARD against an out-of-contract prior rather than a "
            "normalization of one"
        ),
    },
    "globalmax": {
        "bounded_output": True,
        "order_preserving": True,
        "query_independent": True,
        "single_change_to_the_ranker": True,
        "note": (
            "divides by the snapshot own supremum for that dimension: bounded, "
            "strictly order-preserving, computed once per snapshot, deterministic, "
            "hashable into the receipt, and the EXACT IDENTITY whenever the "
            "dimension is already a probability"
        ),
    },
    "dimsup-floor1": {
        "bounded_output": True,
        "order_preserving": True,
        "query_independent": True,
        "single_change_to_the_ranker": True,
        "note": (
            "the landed repair. Divides each dimension by max(1.0, its own sup "
            "over the recalled set), so a dimension already inside its declared "
            "bound is left EXACTLY untouched and only one that escaped its range "
            "is shrunk. Query-independent in effect and provably so: on a "
            "cosine-family dimension the divisor is exactly 1.0, and on a "
            "prior-mass dimension recall truncates by descending score, so the "
            "recalled sup is the snapshot sup on every query. The divisor is >= 1 "
            "by construction, so the rule can neither divide by zero nor amplify"
        ),
    },
    "minmax-q": {
        "bounded_output": True,
        "order_preserving": True,
        "query_independent": False,
        "single_change_to_the_ranker": True,
        "note": (
            "the same facet receives a different score depending on which other "
            "candidates a query happened to recall, and the weakest recalled prior "
            "facet is forced to exactly 0 whatever its true mass; neither is "
            "auditable and neither is cacheable"
        ),
    },
    "z-q": {
        "bounded_output": False,
        "order_preserving": True,
        "query_independent": False,
        "single_change_to_the_ranker": True,
        "note": (
            "not bounded at all -- a z-score can exceed 1 and can go negative, so "
            "it does not restore commensurability; measured on Audio2Tool it still "
            "leaves the two heaviest prior facets above every content facet"
        ),
    },
    "rrf-dim": {
        "bounded_output": True,
        "order_preserving": True,
        "query_independent": False,
        "single_change_to_the_ranker": False,
        "note": (
            "scale-free by construction, but percept admission compares max_cosine "
            "against tau on the COSINE scale, so a rank-based combiner forces the "
            "ranker mapping and the fuser admission mapping apart -- two changes, "
            "not one -- and it discards the magnitude information the fuser uses to "
            "rank task targets and to order values within a target"
        ),
    },
}


#: The variant that reproduces the LANDED repair, and the audit's own
#: independently-derived recommendation. They are expected to agree exactly.
LANDED_REPAIR_VARIANT_ID = "A6-DIMSUP-FLOOR1"
RECOMMENDED_VARIANT_ID = "A2-GLOBALMAX"


def _landed_repair_cross_check(
    *,
    a2t_sweep: Mapping[str, Mapping[str, VariantSample]],
    slurp_sweep: Mapping[str, Mapping[str, VariantSample]] | None,
) -> dict[str, object]:
    """Does the LANDED repair behave identically to the audit's recommendation?

    The audit derived ``A2-GLOBALMAX`` -- divide a prior-mass dimension by the
    snapshot's own supremum -- from the property table alone. The landed repair
    divides every dimension by ``max(1.0, sup over the recalled set)``. For a
    prior-mass dimension those two divisors are the SAME number, because
    ``multidim_recall`` truncates by descending score and therefore always
    retains that dimension's maximum; for a cosine-family dimension the landed
    rule's divisor is exactly 1.0. They should therefore agree trajectory by
    trajectory on both carriers, and this checks it rather than assuming it."""

    out: dict[str, object] = {
        "landed_repair_variant": LANDED_REPAIR_VARIANT_ID,
        "audit_recommendation_variant": RECOMMENDED_VARIANT_ID,
        "why_they_should_agree": (
            "for a prior-mass dimension the sup over the recalled set IS the "
            "snapshot sup, because multidim_recall truncates by descending "
            "score and therefore always retains that dimension's maximum; for a "
            "cosine-family dimension the landed rule's divisor is "
            "max(1.0, sup <= 1) = 1.0, an exact identity"
        ),
    }
    for carrier_name, sweep in (("audio2tool", a2t_sweep), ("slurp", slurp_sweep)):
        if sweep is None:
            out[carrier_name] = None
            continue
        landed = sweep[LANDED_REPAIR_VARIANT_ID]
        recommended = sweep[RECOMMENDED_VARIANT_ID]
        differing = sorted(
            sample_id
            for sample_id, row in landed.items()
            if (
                row.selected_value_ids != recommended[sample_id].selected_value_ids
                or row.admitted_facet_ids != recommended[sample_id].admitted_facet_ids
                or row.dispatched != recommended[sample_id].dispatched
            )
        )
        out[carrier_name] = {
            "trajectories": len(landed),
            "trajectories_where_the_two_rules_differ": len(differing),
            "differing_sample_ids": differing[:10],
            "agree_exactly": not differing,
        }
    return out


def fix_verification(
    *,
    a2t_audit: Mapping[str, object],
    slurp_audit: Mapping[str, object],
    a2t_sweep: Mapping[str, Mapping[str, VariantSample]],
    slurp_sweep: Mapping[str, Mapping[str, VariantSample]] | None,
) -> dict[str, object]:
    """Verification material for the fix, not an argument about whether to fix.

    THE DEFECT IS SETTLED (owner ruling): comparing an unbounded prior mass
    against a cosine bounded by 1 inside a single weighted sum is an
    implementation defect in the ranker. This function supplies what an
    implementer needs in order to act on that ruling: which candidate form
    satisfies the properties a correct commensurable-scale fusion must have,
    and -- the binding proof obligation -- whether that form is an EXACT
    IDENTITY on the locked SLURP cell, measured trajectory by trajectory
    against the sealed DEV-1000 NEW500 flight rather than asserted.
    """

    bound = float(a2t_audit["the_invariant"]["required_bound_on_sup_prior_score"])
    a2t_sup = float(a2t_audit["the_invariant"]["measured_sup_prior_score"])
    slurp_sup = float(slurp_audit["the_invariant"]["measured_sup_prior_score"])

    per_variant: dict[str, object] = {}
    for variant in VARIANTS:
        properties = dict(TRANSFORM_PROPERTIES[variant.prior_transform])
        a2t_rows = a2t_sweep[variant.variant_id]
        a2t_base = a2t_sweep[BASELINE_VARIANT_ID]
        slurp_identity: dict[str, object] | None = None
        if slurp_sweep is not None:
            base = slurp_sweep[BASELINE_VARIANT_ID]
            rows = slurp_sweep[variant.variant_id]
            slurp_identity = {
                "trajectories": len(rows),
                "supply_differs": sum(
                    1
                    for sample_id, row in rows.items()
                    if row.selected_value_ids != base[sample_id].selected_value_ids
                ),
                "admitted_set_differs": sum(
                    1
                    for sample_id, row in rows.items()
                    if row.admitted_facet_ids != base[sample_id].admitted_facet_ids
                ),
                "dispatch_differs": sum(
                    1
                    for sample_id, row in rows.items()
                    if row.dispatched != base[sample_id].dispatched
                ),
            }
            slurp_identity["is_an_exact_identity_on_the_locked_cell"] = (
                slurp_identity["supply_differs"] == 0
                and slurp_identity["admitted_set_differs"] == 0
                and slurp_identity["dispatch_differs"] == 0
            )
        window_change = variant.m != FROZEN_FUSE.m or variant.admission != "global"
        restores_scale = bool(properties["bounded_output"]) and (
            variant.prior_transform != "none"
        )
        reasons: list[str] = []
        if not properties["bounded_output"] and variant.prior_transform != "none":
            reasons.append("does not restore a bounded, commensurable scale")
        if not properties["single_change_to_the_ranker"]:
            reasons.append(
                "forces a SECOND change, to the admission path, because tau lives "
                "on the cosine scale"
            )
        if not properties["query_independent"]:
            reasons.append(
                "the same facet scores differently depending on what else a query "
                "recalled, so the score is neither cacheable nor auditable"
            )
        if not properties["order_preserving"]:
            reasons.append("is not order-preserving")
        if variant.prior_transform == "none" and not window_change:
            verdict = "BASELINE -- the defective configuration exactly as flown"
        elif variant.prior_transform == "none":
            verdict = (
                "NOT A FIX -- moves the window or its scope while leaving the "
                "incommensurable scale in place"
            )
        elif not restores_scale or not properties["query_independent"] or not (
            properties["single_change_to_the_ranker"]
        ):
            verdict = "REJECTED -- " + "; ".join(reasons)
        elif window_change:
            verdict = (
                "CARRIES A CORRECT NORMALIZATION but bundles an unnecessary "
                "window change with it"
            )
        elif not properties["order_preserving"]:
            verdict = (
                "ACCEPTABLE GUARD -- bounded, auditable and SLURP-identical, but "
                "not order-preserving"
            )
        else:
            verdict = (
                "PRINCIPLED FIX -- bounded, order-preserving, query-independent, "
                "one change"
            )
        per_variant[variant.variant_id] = {
            "prior_transform": variant.prior_transform,
            "m": variant.m,
            "admission": variant.admission,
            "properties": properties,
            "restores_a_bounded_commensurable_scale": restores_scale,
            "changes_the_window_or_its_scope": window_change,
            "a2t_trajectories_with_content_admitted": sum(
                1 for row in a2t_rows.values() if row.admitted_facet_ids
            ),
            "a2t_admitted_set_differs_from_the_frozen_cell": sum(
                1
                for sample_id, row in a2t_rows.items()
                if row.admitted_facet_ids != a2t_base[sample_id].admitted_facet_ids
            ),
            "slurp_identity_proof": slurp_identity,
            "property_violations": reasons,
            "verdict": verdict,
        }

    return {
        "settled": (
            "OWNER RULING, adopted here without re-argument: the unnormalized "
            "prior-mass dimension is a BUG in the ranker. Comparing an unbounded "
            "prior mass against a cosine bounded by 1 inside one weighted sum is "
            "an implementation defect, not a design trade-off and not a paradigm "
            "boundary. This section supplies the specification and the "
            "verification material for the fix; it does not re-open the question"
        ),
        "why_slurp_masked_it": (
            "two facts together, both measured here. FIRST, no content facet ever "
            "carries prior mass: prior-mass recall reads the label and prior "
            "dimensions only, so on BOTH carriers every ranker comparison that "
            "matters is a content COSINE against a prior MASS -- two different "
            "scales inside one weighted sum. SECOND, SLURP prior mass is bounded "
            "by 1 because rails.knowledge_build computes it as "
            "intent_total_in_scenario / scenario_total over a strict "
            "scenario -> action -> intent hierarchy, so the numerator row set is "
            "contained in the denominator row set. rails.knowledge_build_a2t "
            "computes tool_total / category_total, and a tool_name is NOT "
            "contained in one (domain, category) -- the G0 report own finding "
            "that tool_id is not a join key and that ten tool ids carry a "
            "different tool_name in the manifests than in the registry. The "
            "containment that made the SLURP ratio a probability does not hold on "
            "Audio2Tool, so the same defective ranker produced a correct-looking "
            "ordering on one carrier and an inverted one on the other"
        ),
        "commensurability_invariant": {
            "statement": (
                "every ADMISSIBLE content facet outranks every prior-mass facet "
                "if and only if w_prior * sup(prior_score) < w_cos * tau, because "
                "the agreement term is identical for every recalled facet and "
                "cancels exactly"
            ),
            "required_bound_on_sup_prior_score": bound,
            "slurp_sup_prior_score": slurp_sup,
            "slurp_inside_the_bound": slurp_sup < bound,
            "slurp_margin": bound - slurp_sup,
            "a2t_sup_prior_score": a2t_sup,
            "a2t_inside_the_bound": a2t_sup < bound,
            "a2t_margin": bound - a2t_sup,
            "a2t_violation_factor": (a2t_sup / bound) if bound else None,
        },
        "identity_obligation": (
            "a correct fix MUST reproduce the locked cell behaviour on SLURP "
            "exactly. The obligation is discharged here by measurement, not by "
            "argument: every candidate form is replayed over the sealed DEV-1000 "
            "NEW500 flight through the identical code path, and its admitted set, "
            "its supply and its dispatch decision are compared trajectory by "
            "trajectory against the frozen cell own"
        ),
        "landed_repair_cross_check": _landed_repair_cross_check(
            a2t_sweep=a2t_sweep, slurp_sweep=slurp_sweep
        ),
        "by_variant": per_variant,
    }


# ---------------------------------------------------------------------------
# Which ranker was actually imported
# ---------------------------------------------------------------------------

#: The symbol a repaired ranker is expected to introduce. Its PRESENCE is what
#: distinguishes a post-fix ``rails.kb_policy`` from the flown one; this module
#: only records which it loaded, and never edits either.
REPAIR_MARKER = "_dimension_scales"

PRE_FIX_STATE = "pre-fix"
POST_FIX_STATE = "post-fix"


def kb_policy_provenance() -> dict[str, object]:
    """Record the EXACT ranker source this run imported.

    This audit is about a defect in ``rails.kb_policy``'s ranker, so which
    bytes of that module were loaded is part of the result, not a detail. The
    V0-FROZEN fidelity gate is the semantic half of the same check: it requires
    the baseline replay to reproduce the FLOWN decision and supply, which only
    the flown ranker can do.
    """

    source_path = Path(kb.__file__ or "")
    text = source_path.read_text(encoding="utf-8")
    carries_repair = REPAIR_MARKER in text
    return {
        "module_path": str(source_path),
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "carries_a_dimension_normalization": carries_repair,
        "repair_marker": REPAIR_MARKER,
        "state": POST_FIX_STATE if carries_repair else PRE_FIX_STATE,
        "semantics": (
            "the audit of the defect must run against the ranker that flew. A "
            "run whose V0-FROZEN replay reproduces the flown zero-dispatch is "
            "certified pre-fix by that gate alone, independently of this hash"
        ),
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(
    *,
    repo_root: Path,
    data_root: Path,
    with_slurp: bool = True,
    expect_state: str = PRE_FIX_STATE,
) -> dict[str, object]:
    """Execute the sweep. Offline guard armed before any input is opened."""

    attempts = ra.arm_offline_guard()
    repo_root = Path(repo_root)
    data_root = Path(data_root)
    started = time.perf_counter()
    provenance = kb_policy_provenance()
    if expect_state not in (PRE_FIX_STATE, POST_FIX_STATE):
        raise SweepError("expect_state must be %r or %r" % (PRE_FIX_STATE, POST_FIX_STATE))
    if provenance["state"] != expect_state:
        raise SweepError(
            "this run expected the %s ranker but imported the %s one from %s; "
            "the audit of the defect must run against the ranker that flew"
            % (expect_state, provenance["state"], provenance["module_path"])
        )

    policy_path = repo_root / FROZEN_POLICY_CONFIG_RELPATH
    policy_sha = _require_hash(
        policy_path, FROZEN_POLICY_CONFIG_SHA256, "the locked v1 policy cell"
    )
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    knobs = policy["knobs"]
    if (
        float(knobs["alpha"]) != FROZEN_ALPHA
        or float(knobs["tau"]) != FROZEN_FUSE.tau
        or int(knobs["recall_top_k_per_dimension"]) != FROZEN_TOP_K
        or int(knobs["fusion"]["m"]) != FROZEN_FUSE.m
        or int(knobs["fusion"]["c"]) != FROZEN_FUSE.c
        or int(knobs["fusion"]["l"]) != FROZEN_FUSE.top_l
        or float(knobs["rank_weights"]["w_cos"]) != FROZEN_WEIGHTS.w_cos
        or float(knobs["rank_weights"]["w_prior"]) != FROZEN_WEIGHTS.w_prior
        or float(knobs["rank_weights"]["w_agree"]) != FROZEN_WEIGHTS.w_agree
    ):
        raise SweepError("the locked cell's knobs are not the ones this sweep replays")

    # ---- Audio2Tool, the primary carrier ---------------------------------
    a2t = load_a2t_carrier(data_root=data_root, repo_root=repo_root)
    a2t_recalls, a2t_recall_gate = base_recall_scores(a2t)
    a2t_audit = scale_audit(a2t, a2t_recalls)
    a2t_sweep, a2t_sweep_meta = sweep_carrier(
        a2t, a2t_recalls, normalizer=a2t_label_normalizer
    )
    a2t_gate = baseline_fidelity_gate(a2t, a2t_sweep[BASELINE_VARIANT_ID])
    a2t_gate["certifies_the_flown_ranker"] = (
        "PASS means the V0-FROZEN replay reproduced the flown decision and "
        "supply on every trajectory, which only the ranker that flew can do. "
        "ONCE THE FIX LANDS THIS GATE MUST FAIL ON AUDIO2TOOL and must still "
        "pass on SLURP -- that pair is the regression test for the repair"
    )
    if not a2t_gate["passed"]:
        raise SweepError(
            "the V0-FROZEN replay does not reproduce the flown A2T decision/supply"
        )
    calibration = token_calibration(repo_root=repo_root, data_root=data_root)
    a2t_table = variant_table(a2t, a2t_sweep, calibration)
    a2t_decisive = decisive_quantities(a2t, a2t_sweep)
    a2t_alpha_gate = alpha_gate_analysis(a2t, a2t_sweep)

    # ---- SLURP, the scale control and the discriminator's own carrier ----
    slurp_block: dict[str, object] | None = None
    slurp_audit: dict[str, object] | None = None
    slurp_sweep: dict[str, dict[str, VariantSample]] | None = None
    if with_slurp:
        slurp, slurp_flight_gate, _slurp_replays = load_slurp_carrier(
            data_root=data_root, repo_root=repo_root
        )
        slurp_recalls, slurp_recall_gate = base_recall_scores(slurp)
        slurp_audit = scale_audit(slurp, slurp_recalls)
        slurp_sweep, slurp_sweep_meta = sweep_carrier(
            slurp, slurp_recalls, normalizer=kb.default_label_normalizer
        )
        slurp_gate = baseline_fidelity_gate(
            slurp,
            slurp_sweep[BASELINE_VARIANT_ID],
            supply_checked_on="dispatched",
            explained_decision_mismatch_ids=frozenset(
                k1.load_override_fires(data_root=data_root)
            ),
        )
        if not slurp_gate["passed"]:
            raise SweepError(
                "the V0-FROZEN replay does not reproduce the flown SLURP "
                "decision/supply outside the proved v2 override fires"
            )
        slurp_block = {
            "carrier_id": slurp.carrier_id,
            "n": len(slurp.sample_ids),
            "artifact_hashes": dict(slurp.artifact_hashes),
            "flight_replay_gate": slurp_flight_gate,
            "recall_gate": slurp_recall_gate,
            "baseline_fidelity_gate": slurp_gate,
            "alpha_gate": alpha_gate_analysis(slurp, slurp_sweep),
            "sweep_meta": slurp_sweep_meta,
            "scale_audit": slurp_audit,
            "variant_table": variant_table(slurp, slurp_sweep, None),
            "notes": dict(slurp.notes),
        }

    verification = fix_verification(
        a2t_audit=a2t_audit,
        slurp_audit=slurp_audit if slurp_audit is not None else a2t_audit,
        a2t_sweep=a2t_sweep,
        slurp_sweep=slurp_sweep,
    )

    return {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "contacts": {
            "model": 0,
            "tool": 0,
            "tokenizer": 0,
            "gold_opened_beyond_already_open_seals": False,
            "outbound_connection_attempts": attempts.count,
            "outbound_targets": list(attempts.targets),
        },
        "kb_policy_provenance": provenance,
        "frozen_cell": {
            "policy_config": FROZEN_POLICY_CONFIG_RELPATH,
            "policy_config_sha256": policy_sha,
            "alpha": FROZEN_ALPHA,
            "tau": FROZEN_FUSE.tau,
            "m": FROZEN_FUSE.m,
            "c": FROZEN_FUSE.c,
            "top_l": FROZEN_FUSE.top_l,
            "top_k_per_dimension": FROZEN_TOP_K,
            "rank_weights": {
                "w_cos": FROZEN_WEIGHTS.w_cos,
                "w_prior": FROZEN_WEIGHTS.w_prior,
                "w_agree": FROZEN_WEIGHTS.w_agree,
            },
            "kb_policy_last_commit_expected": "f1060078",
            "no_knob_is_changed_by_this_row": True,
        },
        "variant_grid": [
            {
                "variant_id": variant.variant_id,
                "family": variant.family,
                "prior_transform": variant.prior_transform,
                "m": variant.m,
                "admission": variant.admission,
                "change": variant.change,
            }
            for variant in VARIANTS
        ],
        "audio2tool": {
            "carrier_id": a2t.carrier_id,
            "n": len(a2t.sample_ids),
            "artifact_hashes": dict(a2t.artifact_hashes),
            "recall_gate": a2t_recall_gate,
            "baseline_fidelity_gate": a2t_gate,
            "sweep_meta": a2t_sweep_meta,
            "scale_audit": a2t_audit,
            "variant_table": a2t_table,
            "decisive_quantities": a2t_decisive,
            "alpha_gate": a2t_alpha_gate,
            "notes": dict(a2t.notes),
        },
        "slurp_control": slurp_block,
        "token_model": calibration,
        "fix_verification": verification,
        "wall_seconds": time.perf_counter() - started,
        "hard_stop": (
            "ITERATION-TIER DESIGN INPUT. This row changes no knob, opens no "
            "unexposed tier, authorizes no flight, and licenses no generality, "
            "superiority or Stage-3 claim"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A2T admission-scale sweep")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--no-slurp", action="store_true")
    parser.add_argument(
        "--expect-state",
        choices=(PRE_FIX_STATE, POST_FIX_STATE),
        default=PRE_FIX_STATE,
        help=(
            "which rails.kb_policy state this run must import. The audit of the "
            "defect runs against the ranker that flew (pre-fix); a post-fix "
            "re-read must say so explicitly"
        ),
    )
    args = parser.parse_args(argv)
    report = run(
        repo_root=args.repo_root,
        data_root=args.data_root,
        with_slurp=not args.no_slurp,
        expect_state=args.expect_state,
    )
    payload = json.dumps(report, indent=1, sort_keys=True, default=str)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8", newline="\n")
        print("written: %s" % args.out)
        print("sha256 : %s" % _sha256_file(args.out))
    else:
        print(payload)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
