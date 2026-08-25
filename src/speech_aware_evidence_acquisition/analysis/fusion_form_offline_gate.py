"""THE FUSION-FORM OFFLINE GATE -- is THREE-KINDS-IN-ONE-SUM worth changing?

Exposure row ``SAEA-SN-MF-FUSION-FORM-OFFLINE-GATE``, registered at commit
``f5cef94c`` BEFORE any computation was performed. Zero frozen-core contacts,
zero pinned-tool embedding contacts, zero tokenizer contacts, zero HTTP or
socket requests, zero new dependencies, zero package installations. Every byte
this module reads is already landed and sealed.

The question
------------
``rails/kb_policy.py``'s registered ranker sums
``w_cos * max_cosine + w_prior * max_prior + w_agree * agreement`` into ONE
score, and the three summands are quantities of DIFFERENT KINDS: a cosine is a
similarity, ``max_prior`` is a probability mass, ``agreement`` is a coverage
fraction. The field's standard practice is to keep one comparison on one
bounded scale, and the literature's three canonical answers to
incommensurability are (i) convert similarities to a distribution and
interpolate it with a second distribution (kNN-LM, Tip-Adapter), (ii)
normalize each list then combine, and (iii) fuse RANKS rather than scores
(reciprocal-rank fusion).

The arms, exactly as registered
-------------------------------
``C0``   the CONTROL -- the live form exactly as landed, which must reproduce
         the flown decisions as a FAIL-CLOSED fidelity gate before any other
         arm's number is read.
``C1``   COSINE-ONLY facet ranking with ``tau``, ``k``, ``m``, ``c`` and
         ``top_l`` unchanged, so the prior dimension no longer competes for
         the top-``m`` window.
``C2``   ``C1`` plus the prior as a LABEL PRIOR entering ``_fused_label_scores``
         MULTIPLICATIVELY on the raw label score before normalization -- the
         Bayes / Tip-Adapter frequency-weighted-cache shape, parameter-free,
         introducing NO new knob.
``C2B``  the secondary registered comparator: instead of multiplying, it
         INTERPOLATES the retrieval distribution against the prior
         distribution at the pre-registered lambda grid 0.10 / 0.25 / 0.50 --
         the literal kNN-LM shape -- reported as a comparator only because it
         introduces a knob that is not in the frozen table.
``C3``   RRF ACROSS DIMENSIONS at ``K = 60``, the literature's third answer,
         carried as a comparator with the K1 gate's own measured result quoted
         beside it.

Only the SCORING differs between arms. The real ``kb_policy.multidim_recall``
(through :func:`.contrast_fewshot_preanalysis.vectorised_recall`, itself gated
against the real function), the real registered fuser
``kb_policy.fuse_supplyfilter_factory``, the real ``kb_policy._dimension_scales``
and the real ``kb_policy._fused_label_scores`` / ``_blend_scores`` /
``_argmax_labels`` are IMPORTED and called, never reimplemented. ``C0``'s
ranker is literally ``kb_policy.rank_wcos_prior_agree_factory``, and this
module's own C0 path is additionally gated against
:func:`.dev100_damage_channel_analysis.replay_supply` on every sample.

What this row is NOT
--------------------
THIS ROW GATES A CHANGE AND IS NOT ONE. No knob is changed, no line under
``rails/``, ``core/`` or ``configs/`` is written, nothing hash-pinned moves, no
snapshot is rebuilt, no receipt is displaced, no arm is re-flown, no new sample
is touched and no new gold surface is opened.

CONSERVATISM, carried into every number
---------------------------------------
These are offline replays over SEALED DECODES. A changed supply does NOT tell
us what the frozen core would have answered. Every downstream accuracy or
extraction number is a PROJECTION and is labelled one. Small-n strata are
mechanism readings, never effect sizes. Counts are reported, not adjectives.
Everything computed on the UNEXPOSED 500 is a SECONDARY READING on the locked
baseline's own population and MUST NOT be used to revise, re-tune or restate
THE LOCK, which stands exactly as landed at ``d9fef537``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from . import contrast_fewshot_preanalysis as cf
from . import cross_carrier_ceiling_decomposition as ccd
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from . import dev500_confirmatory_read as d5
from . import k1_hybrid_ranking_gate as k1
from ..rails import kb_policy as kb
from ..rails.knowledge import RankedFacet, RankResult

SCHEMA = "saea-fusion-form-offline-gate-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-FUSION-FORM-OFFLINE-GATE"
LEDGER_COMMIT = "f5cef94c"
VERDICT_RELPATH = "docs/readiness/2026-08-25-fusion-form-offline-gate.md"
CHECK_DIR_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-fusion-form-gate"
)

#: The pre-registered falsifier, quoted VERBATIM from the ledger row at
#: ``f5cef94c``. It is evaluated exactly as written and may not be re-worded,
#: narrowed or extended by this module.
FALSIFIER = (
    '"A candidate scoring form is REFUSED unless ALL FIVE clauses hold. (F1) MUST IMPROVE - '
    "the form must strictly raise at least one of: the number of samples whose first "
    "gold-bearing facet lies at rank 5 or better in the ranker's own candidate list, or the "
    "number of dispatched trajectories whose supplied task_target set contains the gold "
    "target. A form that is an EXACT IDENTITY on every measured quantity is NOT LICENSED FOR "
    "FLIGHT: it is refused as NO MEASURABLE GAIN, which is a different verdict from HARMFUL "
    "and must be reported as such. (F2) MUST NOT DEGRADE, MATCHING AXIS - the number of "
    "samples whose first gold-bearing facet is at rank 1 in the ranker's own candidate list "
    "must not fall, and the count of dispatched trajectories that LOSE gold-bearing supply "
    "must not exceed the count that GAIN it. This clause exists because the K1 gate's "
    "falsifier was ONE-SIDED and would have licensed a flight that loses: RRF-60 raised "
    "recall-at-5 while lowering recall-at-1, and under the measured, steeply rank-dependent "
    "conversion anchors 23 demotions against 9 promotions does not close. (F3) MUST NOT "
    "DEGRADE, EXTRACTION AXIS - supply is delivered ONLY to dispatched trajectories, and the "
    "measured extraction gain is conditioned on dispatch (unexposed-500 dispatched n = 163: "
    "macro slot-F1 +9.4391 pts CI90 [+4.3558, +14.5194], official SLU-F1 +13.7570 pts CI90 "
    "[+8.8840, +18.6695]). A form must not reduce the number of dispatched trajectories that "
    "receive a non-empty supply, and must not reduce the aggregate number of distinct "
    "supplied task_targets or the aggregate number of supplied values on the dispatched set. "
    "(F4) MUST NOT DEGRADE, DISPATCH RATE - the projected dispatch rate must not fall below "
    "90 percent of the flown rate on ANY population (SLURP unexposed flown-v2 163/500 = 32.60 "
    "percent, locked-v1 reachable 160/500 = 32.00 percent; SLURP exposed 177/500 = 35.40 "
    "percent; A2T 15/104 = 14.42 percent). A form projecting a relative dispatch-rate fall "
    "greater than 10 percent is an OFF-SWITCH and is refused on that ground alone, exactly as "
    "E-C and K3 were refused - K3 projected 15/104 down to 3/104, a fall of 80 percent. (F5) "
    "MUST NOT MOVE THE LOCKED CELL BLINDLY - the number of the 500 UNEXPOSED SLURP decisions "
    "the form changes is reported explicitly for every form; any form changing one or more of "
    "them cannot be recommended for flight on offline evidence alone and requires its own "
    "registered flight, because a changed supply does not tell us what the frozen core would "
    'have answered."'
)

#: The K1 gate's own measured result, quoted beside C3 wherever C3 is reported.
K1_RRF_PRIOR = (
    "K1 measured RRF-60 raising gold-facet recall@5 0.744 -> 0.762 while LOWERING recall@1 "
    "0.636 -> 0.590, and it was REFUSED for flight on exactly that basis"
)

#: The off-switch prior both E-C and K3 were refused on.
OFF_SWITCH_PRIOR = (
    "a form that quietly suppresses dispatch is an off-switch in disguise; E-C and K3 were "
    "both refused on that ground, K3 projecting 15/104 -> 3/104, a fall of 80 percent"
)


class GateError(RuntimeError):
    """A pinned input does not match, or a gated replay contradicts a sealed
    record. Never raised for a legitimate data shape."""


# ---------------------------------------------------------------------------
# REGISTERED CONSTANTS -- fixed by the ledger row, never re-tried after
# ---------------------------------------------------------------------------

#: The reciprocal-rank-fusion constant the row registers for C3.
RRF_K = 60

#: The pre-registered lambda grid for the C2B comparator. Its very existence
#: is why C2B is a COMPARATOR and not a candidate: it introduces a knob that
#: is not in the frozen knob table.
LAMBDA_GRID = (0.10, 0.25, 0.50)

FORM_C0 = "C0"
FORM_C1 = "C1"
FORM_C2 = "C2"
FORM_C3 = "C3"
C2B_FORMS = tuple(f"C2B-{value:.2f}" for value in LAMBDA_GRID)
FORMS = (FORM_C0, FORM_C1, FORM_C2) + C2B_FORMS + (FORM_C3,)

FORM_DESCRIPTIONS = {
    FORM_C0: (
        "CONTROL -- the live registered ranker, "
        "w_cos*max_cosine + w_prior*max_prior + w_agree*agreement"
    ),
    FORM_C1: "COSINE-ONLY facet ranking; tau, k, m, c, top_l unchanged",
    FORM_C2: (
        "C1 + prior as a LABEL PRIOR, multiplicative on the raw label score "
        "before normalization"
    ),
    FORM_C3: f"RRF ACROSS DIMENSIONS at K={RRF_K}",
}
for _lam in LAMBDA_GRID:
    FORM_DESCRIPTIONS[f"C2B-{_lam:.2f}"] = (
        f"COMPARATOR: C1 + kNN-LM interpolation of the retrieval distribution against the "
        f"prior distribution at lambda={_lam:.2f} (introduces a knob not in the frozen table)"
    )

#: The frozen cell, imported rather than restated.
FROZEN_ALPHA = cf.FROZEN_ALPHA
FROZEN_TOP_K = cf.FROZEN_TOP_K
FROZEN_WEIGHTS = cf.FROZEN_WEIGHTS
FROZEN_FUSE = cf.FROZEN_FUSE

#: The MEASURED extraction anchors the falsifier's F3 clause names, verbatim.
EXTRACTION_ANCHOR = {
    "population": "SLURP unexposed-500, DISPATCHED n = 163",
    "macro_slot_f1_pts": 9.4391,
    "macro_slot_f1_ci90": [4.3558, 14.5194],
    "official_slu_f1_pts": 13.7570,
    "official_slu_f1_ci90": [8.8840, 18.6695],
    "source": "docs/readiness/2026-08-25-extraction-conditioned-on-dispatch.md",
}

#: The flown dispatch rates F4 is evaluated against, verbatim from the row.
FLOWN_DISPATCH = {
    "SLURP-UNEXPOSED-500": {
        "flown_v2": (163, 500),
        "locked_v1_reachable": (160, 500),
    },
    "SLURP-EXPOSED-500": {"flown_v2": (177, 500)},
    "A2T-G1-104": {"flown_v2": (15, 104)},
}

#: F4's registered bar: a relative fall greater than 10 percent is an
#: OFF-SWITCH and is refused on that ground alone.
F4_MIN_RELATIVE_RATE = 0.90

#: The DEV-1000 BLEND arm read as BOTH halves. Same pin as
#: ``field_level_supply_accounting.DEV1000_ALL_PIN``, restated here only
#: because importing that module would drag its segmentation tables in.
DEV1000_ALL_PIN = cf.CellPin(
    population_id="DEV-1000",
    run_id=k1.DEV1000_PIN.run_id,
    attempt_id=k1.DEV1000_PIN.attempt_id,
    outputs_basename=k1.DEV1000_PIN.outputs_basename,
    arm_key=k1.DEV1000_PIN.arm_key,
    report_relpath=k1.DEV1000_PIN.report_relpath,
    report_arm_key=k1.DEV1000_PIN.report_arm_key,
    restrict_to=None,
)

SLURP_UNEXPOSED = "SLURP-UNEXPOSED-500"
SLURP_EXPOSED = "SLURP-EXPOSED-500"
A2T_POPULATION = "A2T-G1-104"

SECONDARY_READING = (
    "SECONDARY READING on the locked baseline's own population. It MUST NOT be used to "
    "revise, re-tune or restate THE LOCK, which stands exactly as landed at d9fef537."
)

PROJECTION_LABEL = (
    "PROJECTION, not a measurement: these are offline replays over SEALED decodes, and a "
    "changed supply does not tell us what the frozen core would have answered."
)


# ---------------------------------------------------------------------------
# The scoring forms -- the ONLY thing that differs between arms
# ---------------------------------------------------------------------------


def _sorted_rank_result(
    candidates: Sequence[RankedFacet], *, snapshot_sha256: str, query_state
) -> RankResult:
    """The registered ranker's own sort and its own result type."""

    ordered = sorted(candidates, key=lambda candidate: (-candidate.score, candidate.facet_id))
    return RankResult(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state.content_hash(),
        ranking_policy_id=kb.RANK_POLICY_ID,
        candidates=tuple(ordered),
    ).validate()


def score_cosine_only(
    recall_scores: Mapping[str, Mapping[str, float]], weights: kb.RankWeights
) -> dict[str, float]:
    """C1: ``w_cos * max_cosine``, and nothing else.

    The per-dimension divisor is the REAL :func:`kb_policy._dimension_scales`,
    so the cosine half of the score is bit-identical to what the live ranker
    computes for it. ``w_cos`` is retained even though it is a positive
    constant -- every consumer downstream is either order-based (the fuser's
    target ranking, its ``best_facet`` choice) or normalizes to sum 1
    (``_fused_label_scores``), so the ranking and the fused distribution are
    invariant to it; keeping it makes the arm literally "the live score with
    two summands deleted" rather than a re-scaled quantity.
    """

    scales = kb._dimension_scales(recall_scores)
    scored: dict[str, float] = {}
    for facet_id, dim_scores in recall_scores.items():
        cosines = [
            float(score) / scales[dim]
            for dim, score in dim_scores.items()
            if dim not in kb.PRIOR_MASS_DIMENSIONS
        ]
        scored[facet_id] = weights.w_cos * (max(cosines) if cosines else 0.0)
    return scored


def score_rrf(
    recall_scores: Mapping[str, Mapping[str, float]], *, rrf_k: int = RRF_K
) -> dict[str, float]:
    """C3: ``sum_d 1 / (K + rank_d)`` over the dimensions that recalled the facet.

    ``rank_d`` is the facet's position inside dimension ``d``'s own recalled
    list under ``multidim_recall``'s own ordering -- score descending,
    ``facet_id`` ascending. Magnitude is discarded, which is precisely what
    rank fusion is and precisely why ``_dimension_scales``' docstring already
    rejected it for the live path.
    """

    by_dimension: dict[str, list[tuple[float, str]]] = {}
    for facet_id, dim_scores in recall_scores.items():
        for dimension, score in dim_scores.items():
            by_dimension.setdefault(dimension, []).append((float(score), facet_id))
    scored: dict[str, float] = {facet_id: 0.0 for facet_id in recall_scores}
    for entries in by_dimension.values():
        entries.sort(key=lambda item: (-item[0], item[1]))
        for position, (_score, facet_id) in enumerate(entries, start=1):
            scored[facet_id] += 1.0 / (rrf_k + position)
    return scored


def rank_for_form(
    form: str,
    *,
    recall_scores: Mapping[str, Mapping[str, float]],
    snapshot_sha256: str,
    query_state,
    weights: kb.RankWeights,
) -> RankResult:
    """The one place the arms differ. C0 is the registered ranker itself."""

    if form == FORM_C0:
        ranker = kb.rank_wcos_prior_agree_factory(weights)
        return ranker(
            snapshot_sha256=snapshot_sha256,
            query_state=query_state,
            recall_scores=recall_scores,
        )
    if form == FORM_C1:
        scored = score_cosine_only(recall_scores, weights)
    elif form == FORM_C3:
        scored = score_rrf(recall_scores)
    else:
        raise GateError(f"{form} does not define its own ranking; it shares C1's")
    candidates = [
        RankedFacet(facet_id=facet_id, score=score) for facet_id, score in scored.items()
    ]
    return _sorted_rank_result(
        candidates, snapshot_sha256=snapshot_sha256, query_state=query_state
    )


def label_prior_masses(snapshot, label_targets: Mapping[str, str]) -> dict[str, float]:
    """The prior mass of every label facet, through ``kb_policy``'s own
    :func:`_facet_prior_mass`.

    Query-independent and therefore a per-snapshot constant: computed once and
    reused for every sample of every form. NOTE that this reads the WHOLE
    snapshot, not ``multidim_recall``'s top-``k`` truncation of the prior
    dimension -- a label prior covering only the five facets the prior
    dimension happens to recall would not be a prior over the label vocabulary
    at all.
    """

    values_by_facet: dict[str, list] = {}
    for value in snapshot.values:
        for facet_id in value.associated_facet_ids:
            values_by_facet.setdefault(facet_id, []).append(value)
    facets_by_id = {facet.facet_id: facet for facet in snapshot.facets}
    return {
        label_id: kb._facet_prior_mass(facets_by_id[label_id], values_by_facet)
        for label_id in label_targets
    }


def _normalize(scores: Mapping[str, float]) -> dict[str, float]:
    total = sum(scores.values())
    if total <= 0.0:
        return {key: 0.0 for key in scores}
    return {key: value / total for key, value in scores.items()}


def fused_label_scores_for_form(
    form: str,
    *,
    label_targets: Mapping[str, str],
    values_by_id: Mapping[str, object],
    selected_value_ids: Sequence[str],
    rank_result: RankResult,
    prior_masses: Mapping[str, float],
    prior_distribution: Mapping[str, float],
) -> dict[str, float]:
    """The blend head's input. C0/C1/C3 use the registered function unchanged.

    C2 multiplies the prior onto the raw label score BEFORE normalization.
    :func:`kb_policy._fused_label_scores` returns the ALREADY-normalized
    scores, and that normalization is a single positive scaling shared by
    every label, so multiplying its output by the prior and renormalizing is
    ALGEBRAICALLY IDENTICAL to multiplying the raw scores and normalizing
    once: ``(raw_i/T * p_i) / sum_j(raw_j/T * p_j) == (raw_i p_i) /
    sum_j(raw_j p_j)``. Reusing the registered function is therefore exact and
    is preferred to a second implementation of it.
    """

    fused = kb._fused_label_scores(
        label_targets, values_by_id, selected_value_ids, rank_result
    )
    if form in (FORM_C0, FORM_C1, FORM_C3):
        return dict(fused)
    if form == FORM_C2:
        weighted = {
            label_id: score * float(prior_masses.get(label_id, 0.0))
            for label_id, score in fused.items()
        }
        return _normalize(weighted)
    if form in C2B_FORMS:
        lam = float(form.split("-", 1)[1])
        return {
            label_id: (1.0 - lam) * score
            + lam * float(prior_distribution.get(label_id, 0.0))
            for label_id, score in fused.items()
        }
    raise GateError(f"unknown form {form!r}")


# ---------------------------------------------------------------------------
# One sample, one form
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FormReplay:
    """One sample replayed at one scoring form."""

    sample_id: str
    form: str
    candidate_rank_gold_content: int | None
    candidate_rank_gold_any: int | None
    admitted_facet_ids: tuple[str, ...]
    top_m_facet_ids: tuple[str, ...]
    selected_value_ids: tuple[str, ...]
    supplied_targets: tuple[str, ...]
    gold_supplied: bool
    gold_target_rank: int | None
    best_labels: tuple[str, ...]
    retain_primary: bool
    dispatched: bool


def _ordered_supplied_targets(
    *,
    selected_value_ids: Sequence[str],
    admitted_facet_ids: Sequence[str],
    values_by_id: Mapping[str, object],
    rank_result: RankResult,
) -> tuple[str, ...]:
    """Targets in the order the FUSER itself ranks them: by the score of the
    best admitted supporting facet. Identical construction to
    :func:`.k1_hybrid_ranking_gate.part_b`'s."""

    facet_score = {
        candidate.facet_id: candidate.score for candidate in rank_result.candidates
    }
    admitted = set(admitted_facet_ids)
    best_by_target: dict[str, float] = {}
    for value_id in selected_value_ids:
        value = values_by_id[value_id]
        target = value.task_target
        if target is None:
            continue
        supporting = set(value.associated_facet_ids) & admitted
        if not supporting:
            continue
        best = max(facet_score.get(facet_id, 0.0) for facet_id in supporting)
        best_by_target[target] = max(best_by_target.get(target, 0.0), best)
    return tuple(
        target for target, _ in sorted(best_by_target.items(), key=lambda kv: (-kv[1], kv[0]))
    )


def replay_form(
    *,
    form: str,
    sample_id: str,
    inputs: dc.LandedInputs,
    rank_result: RankResult,
    supply: dc.SupplyReplay,
    gold_target: str,
    direct_label: str | None,
    content_facet_ids: frozenset[str],
    content_facet_target: Mapping[str, str],
    prior_facet_target: Mapping[str, str],
    prior_masses: Mapping[str, float],
    prior_distribution: Mapping[str, float],
) -> FormReplay:
    """Assemble one sample's reported quantities at one form.

    ``rank_result`` and ``supply`` are supplied by the caller because C2 and
    C2B SHARE C1's ranking and therefore share its supply by construction --
    they differ from C1 only in the blend head, and re-running the fuser for
    them would be arithmetic waste, not extra evidence.
    """

    content_rank: int | None = None
    any_rank: int | None = None
    for position, candidate in enumerate(rank_result.candidates, start=1):
        facet_id = candidate.facet_id
        # ``content_facet_target`` is keyed by EVERY facet a task-target-bearing
        # value is associated with -- its content facet AND its label, prior and
        # speaker facets. The content reading must therefore be intersected with
        # the landed content-facet id set, or a prior-mass facet carrying the
        # gold intent would be counted as a gold-bearing CONTENT facet and the
        # candidate-list metric would silently become the wider reading.
        is_content_gold = (
            facet_id in content_facet_ids and content_facet_target.get(facet_id) == gold_target
        )
        is_prior_gold = prior_facet_target.get(facet_id) == gold_target
        if content_rank is None and is_content_gold:
            content_rank = position
        if any_rank is None and (is_content_gold or is_prior_gold):
            any_rank = position
        if content_rank is not None and any_rank is not None:
            break

    fused = fused_label_scores_for_form(
        form,
        label_targets=inputs.label_targets,
        values_by_id=inputs.values_by_id,
        selected_value_ids=supply.selected_value_ids,
        rank_result=rank_result,
        prior_masses=prior_masses,
        prior_distribution=prior_distribution,
    )
    blended = kb._blend_scores(inputs.label_targets, fused, direct_label, FROZEN_ALPHA)
    best = kb._argmax_labels(blended)
    supply_empty = not supply.selected_value_ids
    retain = (best == (direct_label,) and direct_label is not None) and not supply_empty

    ordered = _ordered_supplied_targets(
        selected_value_ids=supply.selected_value_ids,
        admitted_facet_ids=supply.admitted_facet_ids,
        values_by_id=inputs.values_by_id,
        rank_result=rank_result,
    )
    gold_rank = ordered.index(gold_target) + 1 if gold_target in ordered else None
    return FormReplay(
        sample_id=sample_id,
        form=form,
        candidate_rank_gold_content=content_rank,
        candidate_rank_gold_any=any_rank,
        admitted_facet_ids=tuple(sorted(supply.admitted_facet_ids)),
        top_m_facet_ids=tuple(supply.top_m_facet_ids),
        selected_value_ids=tuple(sorted(supply.selected_value_ids)),
        supplied_targets=ordered,
        gold_supplied=gold_target in ordered,
        gold_target_rank=gold_rank,
        best_labels=best,
        retain_primary=retain,
        dispatched=not (retain or supply_empty),
    )


# ---------------------------------------------------------------------------
# One population, all forms
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PopulationInputs:
    """Everything one population needs, already gated by its own C0 fidelity."""

    population_id: str
    carrier: str
    sample_ids: tuple[str, ...]
    inputs: dc.LandedInputs
    recall_scores: Mapping[str, Mapping[str, float]]
    gold_targets: Mapping[str, str]
    direct_labels: Mapping[str, str | None]
    flown_dispatched: Mapping[str, bool]
    flown_supply: Mapping[str, tuple[str, ...]]
    content_facet_ids: frozenset[str]
    content_facet_target: Mapping[str, str]
    prior_facet_target: Mapping[str, str]
    prior_masses: Mapping[str, float]
    prior_distribution: Mapping[str, float]
    full_kb_gold_position: Mapping[str, int | None]
    sealed_correct: Mapping[str, bool]
    direct_correct: Mapping[str, bool]


def replay_all_forms(
    population: PopulationInputs,
) -> tuple[dict[str, dict[str, FormReplay]], dict[str, object]]:
    """Every form on every sample, with C0 self-gated against the real
    ``dc.replay_supply``.

    C0, C1 and C3 each run the real fuser on their own ranking. C2 and every
    C2B point SHARE C1's ranking and supply exactly -- that is what "C1 plus a
    change to ``_fused_label_scores``" means -- and differ only in the blend
    head.
    """

    fuser_forms = (FORM_C0, FORM_C1, FORM_C3)
    out: dict[str, dict[str, FormReplay]] = {form: {} for form in FORMS}
    c0_self_gate_matches = 0
    c0_self_gate_mismatches: list[str] = []
    fuse_seconds = 0.0

    for sample_id in population.sample_ids:
        recall_scores = population.recall_scores[sample_id]
        state = dc._query_state(sample_id, population.inputs.snapshot_sha256)
        supplies: dict[str, dc.SupplyReplay] = {}
        ranks: dict[str, RankResult] = {}
        for form in fuser_forms:
            started = time.perf_counter()
            rank_result = rank_for_form(
                form,
                recall_scores=recall_scores,
                snapshot_sha256=population.inputs.snapshot_sha256,
                query_state=state,
                weights=FROZEN_WEIGHTS,
            )
            fuser = kb.fuse_supplyfilter_factory(FROZEN_FUSE)
            decision = fuser(
                snapshot=population.inputs.snapshot,
                snapshot_sha256=population.inputs.snapshot_sha256,
                query_state=state,
                rank_result=rank_result,
                recall_scores=recall_scores,
            )
            top_m = tuple(
                candidate.facet_id for candidate in rank_result.candidates[: FROZEN_FUSE.m]
            )
            admitted = tuple(
                facet_id
                for facet_id in top_m
                if dc._max_cosine(recall_scores.get(facet_id, {})) >= FROZEN_FUSE.tau
            )
            supplies[form] = dc.SupplyReplay(
                sample_id=sample_id,
                recall_scores=recall_scores,
                rank_result=rank_result,
                selected_value_ids=tuple(decision.selected_value_ids),
                supporting_facet_ids=tuple(decision.supporting_facet_ids),
                admitted_facet_ids=admitted,
                top_m_facet_ids=top_m,
                dims_total=len({dim for scores in recall_scores.values() for dim in scores}),
            )
            ranks[form] = rank_result
            fuse_seconds += time.perf_counter() - started

        # --- C0 SELF-GATE: this module's own C0 path must be the registered
        # --- path, value id for value id, on every single sample.
        reference = dc.replay_supply(
            population.inputs,
            sample_id,
            weights=FROZEN_WEIGHTS,
            knobs=FROZEN_FUSE,
            top_k=FROZEN_TOP_K,
            recall_scores=recall_scores,
        )
        if tuple(sorted(reference.selected_value_ids)) == tuple(
            sorted(supplies[FORM_C0].selected_value_ids)
        ) and tuple(sorted(reference.admitted_facet_ids)) == tuple(
            sorted(supplies[FORM_C0].admitted_facet_ids)
        ):
            c0_self_gate_matches += 1
        else:
            c0_self_gate_mismatches.append(sample_id)

        for form in FORMS:
            source = FORM_C1 if form not in fuser_forms else form
            out[form][sample_id] = replay_form(
                form=form,
                sample_id=sample_id,
                inputs=population.inputs,
                rank_result=ranks[source],
                supply=supplies[source],
                gold_target=population.gold_targets[sample_id],
                direct_label=population.direct_labels[sample_id],
                content_facet_ids=population.content_facet_ids,
                content_facet_target=population.content_facet_target,
                prior_facet_target=population.prior_facet_target,
                prior_masses=population.prior_masses,
                prior_distribution=population.prior_distribution,
            )

    gate = {
        "c0_path_reproduces_dc_replay_supply": c0_self_gate_matches,
        "c0_self_gate_mismatch_sample_ids": c0_self_gate_mismatches[:10],
        "c0_self_gate_passed": c0_self_gate_matches == len(population.sample_ids),
        "rank_and_fuse_seconds": fuse_seconds,
        "samples": len(population.sample_ids),
    }
    if not gate["c0_self_gate_passed"]:
        raise GateError(
            f"{population.population_id}: this module's own C0 path does not reproduce "
            "dev100_damage_channel_analysis.replay_supply -- no other arm's number may be read"
        )
    return out, gate


# ---------------------------------------------------------------------------
# The reported quantities
# ---------------------------------------------------------------------------


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def candidate_list_recall(
    replays: Mapping[str, FormReplay], *, attribute: str
) -> dict[str, object]:
    """Gold-facet recall at 1 and at 5 in the RANKER'S OWN candidate list."""

    total = len(replays)
    positions = [getattr(replay, attribute) for replay in replays.values()]
    at1 = sum(1 for position in positions if position is not None and position <= 1)
    at5 = sum(1 for position in positions if position is not None and position <= 5)
    absent = sum(1 for position in positions if position is None)
    return {
        "n": total,
        "recall_at_1_count": at1,
        "recall_at_1_rate": _rate(at1, total),
        "recall_at_5_count": at5,
        "recall_at_5_rate": _rate(at5, total),
        "gold_absent_from_candidate_list": absent,
    }


def supply_axis(
    replays: Mapping[str, FormReplay], gold_targets: Mapping[str, str]
) -> dict[str, object]:
    """The three F3 quantities plus the dispatch and gold-supply counts."""

    dispatched = [replay for replay in replays.values() if replay.dispatched]
    non_empty = [replay for replay in dispatched if replay.selected_value_ids]
    distinct_targets = sum(len(set(replay.supplied_targets)) for replay in dispatched)
    supplied_values = sum(len(replay.selected_value_ids) for replay in dispatched)
    gold_supplied = sum(
        1 for replay in dispatched if gold_targets[replay.sample_id] in replay.supplied_targets
    )
    return {
        "n": len(replays),
        "dispatched": len(dispatched),
        "dispatch_rate": _rate(len(dispatched), len(replays)),
        "dispatched_with_non_empty_supply": len(non_empty),
        "aggregate_distinct_supplied_task_targets_on_dispatched": distinct_targets,
        "aggregate_supplied_values_on_dispatched": supplied_values,
        "dispatched_with_gold_bearing_supply": gold_supplied,
        "admitted_facets_total": sum(
            len(replay.admitted_facet_ids) for replay in replays.values()
        ),
    }


def decision_delta(
    *,
    control: Mapping[str, FormReplay],
    variant: Mapping[str, FormReplay],
    gold_targets: Mapping[str, str],
    flown_dispatched: Mapping[str, bool],
    flown_supply: Mapping[str, tuple[str, ...]],
) -> dict[str, object]:
    """COUNTS -- never adjectives -- of what the variant moves against C0.

    A DECISION is the pair ``(dispatched, sorted selected_value_ids)``: it is
    exactly what the flight recorded and exactly what a re-flight would have
    to re-decide. The count against the FLOWN v2 record is reported beside the
    count against the replayed v1 control, because the two differ by the
    retain-override fires the lock read falsified out of sample.
    """

    changed_decisions: list[str] = []
    dispatch_flips: list[str] = []
    supply_changes: list[str] = []
    admitted_changes: list[str] = []
    gold_gain: list[str] = []
    gold_loss: list[str] = []
    changed_vs_flown = 0
    for sample_id, base in control.items():
        var = variant[sample_id]
        same_supply = base.selected_value_ids == var.selected_value_ids
        same_dispatch = base.dispatched == var.dispatched
        if not same_supply:
            supply_changes.append(sample_id)
        if not same_dispatch:
            dispatch_flips.append(sample_id)
        if not (same_supply and same_dispatch):
            changed_decisions.append(sample_id)
        if base.admitted_facet_ids != var.admitted_facet_ids:
            admitted_changes.append(sample_id)
        gold = gold_targets[sample_id]
        base_has = base.dispatched and gold in base.supplied_targets
        var_has = var.dispatched and gold in var.supplied_targets
        if var_has and not base_has:
            gold_gain.append(sample_id)
        if base_has and not var_has:
            gold_loss.append(sample_id)
        # The flight records a supply ONLY for a trajectory it dispatched; a
        # retained trajectory carries none, so the comparison is the dispatch
        # flag always and the supply only where the flight has one -- the same
        # semantics cross_carrier_ceiling_decomposition.fidelity_gate uses.
        flown_dispatch = bool(flown_dispatched.get(sample_id, False))
        if var.dispatched != flown_dispatch:
            changed_vs_flown += 1
        elif flown_dispatch and var.selected_value_ids != tuple(
            sorted(flown_supply.get(sample_id, ()))
        ):
            changed_vs_flown += 1
    return {
        "decisions_changed_vs_c0": len(changed_decisions),
        "decision_change_sample_ids": changed_decisions[:20],
        "dispatch_decision_flips_vs_c0": len(dispatch_flips),
        "supply_set_changes_vs_c0": len(supply_changes),
        "admitted_set_changes_vs_c0": len(admitted_changes),
        "dispatched_trajectories_GAINING_gold_bearing_supply": len(gold_gain),
        "dispatched_trajectories_LOSING_gold_bearing_supply": len(gold_loss),
        "gold_gain_sample_ids": gold_gain[:20],
        "gold_loss_sample_ids": gold_loss[:20],
        "decisions_differing_from_the_FLOWN_v2_record": changed_vs_flown,
    }


def conversion_projection(
    *,
    control: Mapping[str, FormReplay],
    variant: Mapping[str, FormReplay],
    gold_targets: Mapping[str, str],
    sealed_correct: Mapping[str, bool],
    direct_correct: Mapping[str, bool],
) -> dict[str, object]:
    """The MATCHING axis, priced with the campaign's own MEASURED anchors.

    Construction is :func:`.k1_hybrid_ranking_gate.conversion_projection`'s,
    unchanged, and its anchor function is IMPORTED rather than restated: a
    trajectory that retains carries its own direct decode's score exactly; a
    dispatched trajectory whose supplied set is byte-identical to the control's
    carries the sealed outcome exactly; only a dispatched trajectory whose
    supply CHANGED is priced, symmetrically for currently-correct and
    currently-wrong trajectories.
    """

    baseline_correct = sum(1 for sample_id in control if sealed_correct[sample_id])
    total = len(control)
    central = pessimistic = optimistic = 0.0
    exact_retained = exact_carried = changed = extrapolated = 0
    for sample_id, base in control.items():
        var = variant[sample_id]
        if not var.dispatched:
            outcome = 1.0 if direct_correct[sample_id] else 0.0
            central += outcome
            pessimistic += outcome
            optimistic += outcome
            exact_retained += 1
            continue
        if base.dispatched and base.selected_value_ids == var.selected_value_ids:
            outcome = 1.0 if sealed_correct[sample_id] else 0.0
            central += outcome
            pessimistic += outcome
            optimistic += outcome
            exact_carried += 1
            continue
        changed += 1
        rank = var.gold_target_rank if var.gold_supplied else None
        rate, label = k1._anchor_rate(rank)
        if label.startswith("fused rank 4+"):
            extrapolated += 1
        central += rate
        worse = None if rank is None else (rank + 2 if rank == 1 else rank + 1)
        pessimistic += k1._anchor_rate(worse)[0]
        if sealed_correct[sample_id]:
            optimistic += 1.0
        else:
            optimistic += k1.ANCHOR_TOP1 if var.gold_supplied else 0.0
    return {
        "label": PROJECTION_LABEL,
        "anchors": {
            "fused_top1": k1.ANCHOR_TOP1,
            "fused_rank_2_or_3": k1.ANCHOR_RANK23,
            "absent": k1.ANCHOR_ABSENT,
            "fused_rank_4_plus_EXTRAPOLATED": k1.ANCHOR_RANK4PLUS_EXTRAPOLATED,
            "source": "docs/readiness/2026-08-25-ec-and-retain-override-projections.md section 3",
        },
        "n": total,
        "sealed_baseline_correct": baseline_correct,
        "exact_outcomes_retained_trajectories": exact_retained,
        "exact_outcomes_identical_supply": exact_carried,
        "changed_trajectories_priced": changed,
        "changed_priced_at_the_unanchored_rank": extrapolated,
        "projected_pessimistic": pessimistic,
        "projected_central": central,
        "projected_optimistic": optimistic,
        "delta_pp_pessimistic": 100.0 * (pessimistic - baseline_correct) / total if total else 0.0,
        "delta_pp_central": 100.0 * (central - baseline_correct) / total if total else 0.0,
        "delta_pp_optimistic": 100.0 * (optimistic - baseline_correct) / total if total else 0.0,
        "variance_prior": k1.VARIANCE_PRIOR,
    }


def extraction_projection(
    *, control_axis: Mapping[str, object], variant_axis: Mapping[str, object]
) -> dict[str, object]:
    """The EXTRACTION axis, projected from the measured conditioned-on-dispatch
    gain.

    Supply is delivered ONLY to dispatched trajectories, so the measured gain
    (macro slot-F1 +9.4391 pts, official SLU-F1 +13.7570 pts, both conditioned
    on the 163 dispatched trajectories of the unexposed 500) is carried
    per-dispatched-trajectory and re-weighted by the variant's own dispatched
    count. This is a PROJECTION with a strictly LINEAR carrier assumption; it
    is not a measurement, and it is not an effect size.
    """

    base_dispatched = int(control_axis["dispatched_with_non_empty_supply"])
    var_dispatched = int(variant_axis["dispatched_with_non_empty_supply"])
    total = int(control_axis["n"])
    scale = _rate(var_dispatched, base_dispatched) if base_dispatched else 0.0
    base_values = int(control_axis["aggregate_supplied_values_on_dispatched"])
    var_values = int(variant_axis["aggregate_supplied_values_on_dispatched"])
    base_targets = int(
        control_axis["aggregate_distinct_supplied_task_targets_on_dispatched"]
    )
    var_targets = int(
        variant_axis["aggregate_distinct_supplied_task_targets_on_dispatched"]
    )
    value_scale = _rate(var_values, base_values) if base_values else 0.0
    target_scale = _rate(var_targets, base_targets) if base_targets else 0.0
    return {
        "label": PROJECTION_LABEL,
        "measured_anchor": EXTRACTION_ANCHOR,
        "assumption": (
            "STRICTLY LINEAR in the number of dispatched trajectories that receive a "
            "non-empty supply; the per-trajectory extraction gain is assumed unchanged, "
            "which a changed supply does not license and which no sealed decode can confirm"
        ),
        "control_dispatched_with_supply": base_dispatched,
        "variant_dispatched_with_supply": var_dispatched,
        "delivery_scale_vs_control": scale,
        "projected_macro_slot_f1_delta_pts_on_the_dispatched_set": (
            EXTRACTION_ANCHOR["macro_slot_f1_pts"] * scale
        ),
        "projected_official_slu_f1_delta_pts_on_the_dispatched_set": (
            EXTRACTION_ANCHOR["official_slu_f1_pts"] * scale
        ),
        "population_weighted_macro_pts": (
            EXTRACTION_ANCHOR["macro_slot_f1_pts"] * _rate(var_dispatched, total)
        ),
        "control_population_weighted_macro_pts": (
            EXTRACTION_ANCHOR["macro_slot_f1_pts"] * _rate(base_dispatched, total)
        ),
        "aggregate_supplied_values_control": base_values,
        "aggregate_supplied_values_variant": var_values,
        "aggregate_distinct_targets_control": base_targets,
        "aggregate_distinct_targets_variant": var_targets,
        "delivery_scale_by_supplied_values": value_scale,
        "delivery_scale_by_distinct_targets": target_scale,
        "projected_macro_slot_f1_delta_pts_scaled_by_supplied_values": (
            EXTRACTION_ANCHOR["macro_slot_f1_pts"] * value_scale
        ),
        "projected_macro_slot_f1_delta_pts_scaled_by_distinct_targets": (
            EXTRACTION_ANCHOR["macro_slot_f1_pts"] * target_scale
        ),
        "three_carriers_note": (
            "THREE linear carriers are reported because they disagree, and the disagreement "
            "is the point: a form can keep every dispatched trajectory while shrinking what "
            "each one carries. The trajectory-count carrier is the most favourable to a form "
            "that thins the supply; the supplied-value carrier is the least. None of the "
            "three is measured -- the measured quantity is a single conditioned-on-dispatch "
            "gain at the landed supply, and no sealed decode says what a thinner supply would "
            "have produced"
        ),
    }


def dispatch_rate_check(
    *, population_id: str, variant_axis: Mapping[str, object]
) -> dict[str, object]:
    """F4, evaluated against every flown rate the row registers for this
    population."""

    projected = float(variant_axis["dispatch_rate"])
    rows: dict[str, object] = {}
    passed = True
    for name, (count, total) in FLOWN_DISPATCH[population_id].items():
        flown_rate = count / total
        relative = projected / flown_rate if flown_rate else 0.0
        clause = relative >= F4_MIN_RELATIVE_RATE
        passed = passed and clause
        rows[name] = {
            "flown_count": count,
            "flown_total": total,
            "flown_rate": flown_rate,
            "projected_rate": projected,
            "relative_to_flown": relative,
            "relative_fall_pct": 100.0 * (1.0 - relative),
            "meets_the_90_percent_bar": clause,
        }
    return {"rows": rows, "passed": passed, "off_switch_prior": OFF_SWITCH_PRIOR}


# ---------------------------------------------------------------------------
# The falsifier, evaluated exactly as registered
# ---------------------------------------------------------------------------

#: The registration pairs "the ranker's OWN candidate list" with "the full-KB
#: CONTENT-FACET ordering" in one sentence, and only a facet carrying a cosine
#: dimension can ever be percept-admitted and therefore supply anything, so
#: F1/F2's "first gold-bearing facet" is read PRIMARILY as the first
#: gold-bearing CONTENT facet -- the same object every earlier read in this
#: repository measures. The wider reading (any facet whose task_target is the
#: gold target, prior-mass facets included) is evaluated in parallel and both
#: verdicts are published, so nothing rests on the choice.
GOLD_DEFINITIONS = ("content_facet", "any_facet")
GOLD_ATTRIBUTE = {
    "content_facet": "candidate_rank_gold_content",
    "any_facet": "candidate_rank_gold_any",
}


def falsifier_verdict(
    *,
    population_id: str,
    control: Mapping[str, object],
    variant: Mapping[str, object],
    delta: Mapping[str, object],
    unexposed_decisions_changed: int | None,
) -> dict[str, object]:
    """Evaluate F1-F5 on one form, on one population, exactly as written."""

    clauses: dict[str, object] = {}

    f1_by_definition: dict[str, object] = {}
    f2_by_definition: dict[str, object] = {}
    for definition in GOLD_DEFINITIONS:
        base_at5 = int(control["candidate_recall"][definition]["recall_at_5_count"])
        var_at5 = int(variant["candidate_recall"][definition]["recall_at_5_count"])
        base_at1 = int(control["candidate_recall"][definition]["recall_at_1_count"])
        var_at1 = int(variant["candidate_recall"][definition]["recall_at_1_count"])
        f1_by_definition[definition] = {
            "control_recall_at_5_count": base_at5,
            "variant_recall_at_5_count": var_at5,
            "raised": var_at5 > base_at5,
        }
        f2_by_definition[definition] = {
            "control_recall_at_1_count": base_at1,
            "variant_recall_at_1_count": var_at1,
            "did_not_fall": var_at1 >= base_at1,
        }

    base_gold_supply = int(control["supply_axis"]["dispatched_with_gold_bearing_supply"])
    var_gold_supply = int(variant["supply_axis"]["dispatched_with_gold_bearing_supply"])
    identity = bool(variant["identical_to_control_on_every_measured_quantity"])
    f1_primary = (
        f1_by_definition["content_facet"]["raised"] or var_gold_supply > base_gold_supply
    )
    clauses["F1_must_improve"] = {
        "clause": (
            "strictly raise at least one of: samples whose first gold-bearing facet lies at "
            "rank 5 or better in the ranker's own candidate list, or dispatched trajectories "
            "whose supplied task_target set contains the gold target"
        ),
        "candidate_list_recall_at_5": f1_by_definition,
        "control_dispatched_with_gold_bearing_supply": base_gold_supply,
        "variant_dispatched_with_gold_bearing_supply": var_gold_supply,
        "gold_supply_count_raised": var_gold_supply > base_gold_supply,
        "exact_identity_on_every_measured_quantity": identity,
        "holds_under_the_content_facet_reading": bool(f1_primary),
        "holds_under_the_any_facet_reading": bool(
            f1_by_definition["any_facet"]["raised"] or var_gold_supply > base_gold_supply
        ),
        "verdict_if_identity": (
            "NO MEASURABLE GAIN -- refused, and expressly NOT the same verdict as HARMFUL"
            if identity
            else None
        ),
        "holds": bool(f1_primary),
    }

    gold_gain = int(delta["dispatched_trajectories_GAINING_gold_bearing_supply"])
    gold_loss = int(delta["dispatched_trajectories_LOSING_gold_bearing_supply"])
    clauses["F2_must_not_degrade_matching"] = {
        "clause": (
            "the count at rank 1 in the ranker's own candidate list must not fall, and the "
            "count of dispatched trajectories that LOSE gold-bearing supply must not exceed "
            "the count that GAIN it"
        ),
        "candidate_list_recall_at_1": f2_by_definition,
        "dispatched_gaining_gold_bearing_supply": gold_gain,
        "dispatched_losing_gold_bearing_supply": gold_loss,
        "losses_do_not_exceed_gains": gold_loss <= gold_gain,
        "holds_under_the_content_facet_reading": bool(
            f2_by_definition["content_facet"]["did_not_fall"] and gold_loss <= gold_gain
        ),
        "holds_under_the_any_facet_reading": bool(
            f2_by_definition["any_facet"]["did_not_fall"] and gold_loss <= gold_gain
        ),
        "holds": bool(
            f2_by_definition["content_facet"]["did_not_fall"] and gold_loss <= gold_gain
        ),
        "why_this_clause_exists": K1_RRF_PRIOR,
    }

    base_axis = control["supply_axis"]
    var_axis = variant["supply_axis"]
    f3_rows = {
        "dispatched_with_non_empty_supply": (
            int(base_axis["dispatched_with_non_empty_supply"]),
            int(var_axis["dispatched_with_non_empty_supply"]),
        ),
        "aggregate_distinct_supplied_task_targets_on_dispatched": (
            int(base_axis["aggregate_distinct_supplied_task_targets_on_dispatched"]),
            int(var_axis["aggregate_distinct_supplied_task_targets_on_dispatched"]),
        ),
        "aggregate_supplied_values_on_dispatched": (
            int(base_axis["aggregate_supplied_values_on_dispatched"]),
            int(var_axis["aggregate_supplied_values_on_dispatched"]),
        ),
    }
    clauses["F3_must_not_degrade_extraction"] = {
        "clause": (
            "must not reduce the number of dispatched trajectories that receive a non-empty "
            "supply, nor the aggregate number of distinct supplied task_targets, nor the "
            "aggregate number of supplied values on the dispatched set"
        ),
        "measured_anchor": EXTRACTION_ANCHOR,
        "rows": {
            name: {"control": base, "variant": var, "not_reduced": var >= base}
            for name, (base, var) in f3_rows.items()
        },
        "holds": all(var >= base for base, var in f3_rows.values()),
    }

    f4 = dispatch_rate_check(population_id=population_id, variant_axis=var_axis)
    clauses["F4_must_not_degrade_dispatch_rate"] = {
        "clause": (
            "the projected dispatch rate must not fall below 90 percent of the flown rate on "
            "ANY population; a relative fall greater than 10 percent is an OFF-SWITCH and is "
            "refused on that ground alone"
        ),
        "rows": f4["rows"],
        "off_switch_prior": f4["off_switch_prior"],
        "holds": bool(f4["passed"]),
    }

    clauses["F5_must_not_move_the_locked_cell_blindly"] = {
        "clause": (
            "the number of the 500 UNEXPOSED SLURP decisions the form changes is reported "
            "explicitly for every form; any form changing one or more of them cannot be "
            "recommended for flight on offline evidence alone and requires its own "
            "registered flight"
        ),
        "unexposed_500_decisions_changed": unexposed_decisions_changed,
        "reported": unexposed_decisions_changed is not None,
        "changes_zero_locked_decisions": unexposed_decisions_changed == 0,
        "reading": (
            "evaluated under BOTH readings: the reporting duty is discharged for every form, "
            "and the STRICT reading -- the clause holds only when the count is zero -- is the "
            "one that gates a flight recommendation, because a nonzero count is exactly the "
            "condition the clause says offline evidence cannot settle"
        ),
        "holds": unexposed_decisions_changed == 0,
        "holds_under_the_reporting_duty_reading": unexposed_decisions_changed is not None,
    }

    all_hold = all(bool(clause["holds"]) for clause in clauses.values())
    if identity:
        verdict = "REFUSED -- NO MEASURABLE GAIN (an exact identity; expressly not HARMFUL)"
    elif all_hold:
        verdict = "SURVIVES the falsifier as registered"
    else:
        failed = [name for name, clause in clauses.items() if not clause["holds"]]
        verdict = "REFUSED -- " + ", ".join(failed)
    return {
        "clauses": clauses,
        "all_five_clauses_hold": all_hold,
        "verdict": verdict,
        "survival_authorizes_nothing": (
            "a survival would at most make a flight proposal worth writing; it authorizes no "
            "knob change, no re-flight and no claim, and any flight needs the owner's "
            "contact-cell decision, which is pending"
        ),
    }


# ---------------------------------------------------------------------------
# Population loading -- C0 fidelity FIRST, fail-closed
# ---------------------------------------------------------------------------


def _prior_facet_targets(snapshot) -> dict[str, str]:
    """``facet_id -> task_target`` for the PRIOR-MASS dimensions.

    Same construction as :func:`kb_policy._label_identities`, widened from the
    ``label`` dimension to every dimension in
    :data:`kb_policy.PRIOR_MASS_DIMENSIONS`, so the "any facet" reading of the
    falsifier's "gold-bearing facet" has a defensible referent.
    """

    values_by_facet: dict[str, list] = {}
    for value in snapshot.values:
        for facet_id in value.associated_facet_ids:
            values_by_facet.setdefault(facet_id, []).append(value)
    identities: dict[str, str] = {}
    for facet in snapshot.facets:
        if facet.dimension not in kb.PRIOR_MASS_DIMENSIONS:
            continue
        targets = {
            value.task_target
            for value in values_by_facet.get(facet.facet_id, ())
            if value.task_target is not None
        }
        if len(targets) == 1:
            identities[facet.facet_id] = next(iter(targets))
    return identities


def full_kb_fidelity_gate(
    *, repo_root: Path, positions: Mapping[str, int | None]
) -> dict[str, object]:
    """Reproduce the SEALED one-shot read's published gold-facet recall@k from
    this module's own full-KB content-facet ordering, before any form's number
    is read. Pins and grid imported from the K1 gate and the DEV-500 read."""

    relpath, sha256, expected_n = k1.FIDELITY_PINS["DEV-1000-NEW500"]
    path = Path(repo_root) / relpath
    measured = d5._require_hash(path, sha256, "DEV-1000-NEW500 committed read verdict")
    published = json.loads(path.read_text(encoding="utf-8"))["reachability_ceiling"]
    if int(published["n"]) != expected_n or len(positions) != expected_n:
        raise GateError("DEV-1000-NEW500: population size disagrees with the sealed verdict")
    rows: dict[str, object] = {}
    all_match = True
    for k in d5.RECALL_AT_K_GRID:
        count = sum(
            1 for position in positions.values() if position is not None and position <= k
        )
        expected = int(published["recall_at_k"][f"recall_at_{k}"]["count"])
        match = count == expected
        all_match = all_match and match
        rows[f"recall_at_{k}"] = {
            "recomputed_count": count,
            "published_count": expected,
            "rate": count / expected_n,
            "match": match,
        }
    absent = sum(1 for position in positions.values() if position is None)
    absent_match = absent == int(published["gold_bearing_facet_absent_from_kb"])
    return {
        "source": relpath,
        "source_sha256": measured,
        "n": expected_n,
        "rows": rows,
        "gold_absent_recomputed": absent,
        "gold_absent_published": int(published["gold_bearing_facet_absent_from_kb"]),
        "passed": all_match and absent_match,
    }


def load_slurp(
    *, repo_root: Path, data_root: Path
) -> tuple[dict[str, PopulationInputs], dict[str, object]]:
    """The DEV-1000 BLEND arm, read as BOTH halves, C0-gated against the flight."""

    import numpy as np

    bundle = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    shim = k1.load_populations(repo_root)
    dev1000_hashes = k1.assert_dev1000_byte_pins(repo_root=repo_root, data_root=data_root)
    override_fires = k1.load_override_fires(data_root=data_root)
    populations = d5.load_populations(repo_root)
    cell = cf.load_cell_population(
        pin=DEV1000_ALL_PIN,
        bundle=bundle,
        populations=populations,
        data_root=data_root,
        repo_root=repo_root,
    )
    if len(cell.sample_ids) != 1000:
        raise GateError(
            f"the DEV-1000 BLEND arm covers {len(cell.sample_ids)} samples, not 1000"
        )
    new500 = set(shim.new500)
    dev500 = set(shim.dev500)
    if new500 | dev500 != set(cell.sample_ids) or new500 & dev500:
        raise GateError("the DEV-1000 halves do not partition the flown arm")

    replays, flight_gate = cf.replay_population(cell, bundle)

    # The v2 retain-override deviation, PROVED rather than tolerated -- exactly
    # as the K1 gate proves it.
    mismatches = {
        str(item["sample_id"]) for item in flight_gate["retain_dispatch_decision_mismatches"]
    }
    unexplained = mismatches - override_fires
    flight_gate["v2_override_deviation"] = {
        "explanation": (
            "the DEV-1000 BLEND arm flew the v2 delta>=0.14 retain-override, which the lock "
            "read FALSIFIED out of sample and which the locked v1 cell does not carry; the v1 "
            "replay therefore disagrees with the flown contact count on exactly the override "
            "fires"
        ),
        "override_fires_in_population": len(override_fires & set(cell.sample_ids)),
        "mismatches_all_explained_by_the_override": not unexplained,
        "unexplained_mismatch_sample_ids": sorted(unexplained)[:10],
    }
    if unexplained:
        raise GateError(
            f"DEV-1000: {len(unexplained)} dispatch mismatches are NOT override fires -- "
            "the C0 replay does not reproduce the flight"
        )
    if not flight_gate["supply_gate_passed"]:
        raise GateError("DEV-1000: the flown SUPPLY was not reproduced exactly by C0")

    prior_facet_target = _prior_facet_targets(bundle.snapshot)
    prior_masses = label_prior_masses(bundle.snapshot, bundle.label_targets)
    prior_distribution = _normalize(prior_masses)

    recall_scores: dict[str, dict[str, dict[str, float]]] = {}
    direct_labels: dict[str, str | None] = {}
    direct_correct: dict[str, bool] = {}
    for sample_id in cell.sample_ids:
        cosines = cf._COSINE_CACHE[(DEV1000_ALL_PIN.population_id, sample_id)]
        recall_scores[sample_id] = cf.vectorised_recall(
            bundle, np.asarray(cosines), top_k=FROZEN_TOP_K
        )
        direct_labels[sample_id] = kb.default_label_normalizer(
            cell.inputs.direct_texts[sample_id], cell.inputs.label_targets
        )
        direct_correct[sample_id] = bool(
            dc.score_response(
                cell.inputs.gold_by_sample[sample_id], cell.inputs.direct_texts[sample_id]
            )["correct"]
        )

    halves = {
        SLURP_UNEXPOSED: tuple(sorted(new500)),
        SLURP_EXPOSED: tuple(sorted(dev500)),
    }
    out: dict[str, PopulationInputs] = {}
    for population_id, sample_ids in halves.items():
        out[population_id] = PopulationInputs(
            population_id=population_id,
            carrier="slurp",
            sample_ids=sample_ids,
            inputs=cell.inputs,
            recall_scores={sid: recall_scores[sid] for sid in sample_ids},
            gold_targets={sid: replays[sid].gold_target for sid in sample_ids},
            direct_labels={sid: direct_labels[sid] for sid in sample_ids},
            flown_dispatched={sid: cell.logged_contacts[sid] == 2 for sid in sample_ids},
            flown_supply={
                sid: tuple(sorted(cell.inputs.logged_supply.get(sid, ()))) for sid in sample_ids
            },
            content_facet_ids=frozenset(bundle.facet_ids),
            content_facet_target=bundle.content_facet_target,
            prior_facet_target=prior_facet_target,
            prior_masses=prior_masses,
            prior_distribution=prior_distribution,
            full_kb_gold_position={sid: replays[sid].gold_facet_position for sid in sample_ids},
            sealed_correct={sid: replays[sid].correct for sid in sample_ids},
            direct_correct={sid: direct_correct[sid] for sid in sample_ids},
        )

    gate = {
        "flight_replay_gate": flight_gate,
        "dev1000_byte_pins": dev1000_hashes,
        "artifact_hashes": dict(cell.artifact_hashes),
        "snapshot_sha256": bundle.snapshot_sha256,
        "content_facet_npz_sha256": bundle.npz_sha256,
        "content_facet_count": len(bundle.facet_ids),
        "value_vectors": "SEALED (never loaded)",
        "label_vocabulary": len(bundle.label_targets),
        "prior_mass_supremum_over_the_label_vocabulary": max(prior_masses.values()),
        "prior_mass_sum_over_the_label_vocabulary": sum(prior_masses.values()),
        "full_kb_fidelity_gate": full_kb_fidelity_gate(
            repo_root=repo_root,
            positions=out[SLURP_UNEXPOSED].full_kb_gold_position,
        ),
    }
    if not gate["full_kb_fidelity_gate"]["passed"]:
        raise GateError(
            "DEV-1000-NEW500: the recomputed full-KB gold-facet recall@k does not reproduce "
            "the sealed one-shot read -- no form's number may be read"
        )
    return out, gate


def load_a2t(*, repo_root: Path, data_root: Path) -> tuple[PopulationInputs, dict[str, object]]:
    """The sealed A2T attempt-4 BLEND arm, C0-gated by the cross-carrier read's
    own fail-closed fidelity gate."""

    import numpy as np

    carrier = ccd.load_a2t_attempt4(data_root=data_root, repo_root=repo_root)
    supplies, blends, direct_labels = ccd.replay_population(carrier)
    fidelity = ccd.fidelity_gate(carrier, supplies, blends, direct_labels)
    if not fidelity["gate_passed"]:
        raise GateError(
            "A2T-G1-104: C0 does not reproduce the flown supply, dispatch and label recovery "
            "-- no form's number may be read"
        )

    bundle = carrier.bundle
    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)
    full_kb_position: dict[str, int | None] = {}
    for sample_id in carrier.sample_ids:
        query = np.asarray(carrier.inputs.query_vectors[sample_id], dtype=np.float64)
        denominator = facet_norms * float(np.linalg.norm(query))
        with np.errstate(divide="ignore", invalid="ignore"):
            cosines = np.where(denominator > 0.0, matrix @ query / denominator, 0.0)
        order = np.argsort(-cosines, kind="stable")
        gold = carrier.gold_primary[sample_id]
        position: int | None = None
        for rank_position, index in enumerate(order, start=1):
            if bundle.content_facet_target.get(bundle.facet_ids[int(index)]) == gold:
                position = rank_position
                break
        full_kb_position[sample_id] = position

    prior_facet_target = _prior_facet_targets(bundle.snapshot)
    prior_masses = label_prior_masses(bundle.snapshot, carrier.inputs.label_targets)
    prior_distribution = _normalize(prior_masses)

    population = PopulationInputs(
        population_id=A2T_POPULATION,
        carrier="audio2tool",
        sample_ids=tuple(carrier.sample_ids),
        inputs=carrier.inputs,
        recall_scores={sid: supplies[sid].recall_scores for sid in carrier.sample_ids},
        gold_targets=dict(carrier.gold_primary),
        direct_labels=dict(direct_labels),
        flown_dispatched=dict(carrier.flown_dispatched),
        flown_supply={
            sid: tuple(sorted(carrier.flown_supply.get(sid, ()))) for sid in carrier.sample_ids
        },
        content_facet_ids=frozenset(bundle.facet_ids),
        content_facet_target=bundle.content_facet_target,
        prior_facet_target=prior_facet_target,
        prior_masses=prior_masses,
        prior_distribution=prior_distribution,
        full_kb_gold_position=full_kb_position,
        sealed_correct=dict(carrier.blend_correct),
        direct_correct=dict(carrier.direct_correct),
    )
    gate = {
        "fidelity_gate": fidelity,
        "artifact_hashes": dict(carrier.artifact_hashes),
        "snapshot_sha256": bundle.snapshot_sha256,
        "content_facet_count": len(bundle.facet_ids),
        "value_vectors": "SEALED (never loaded)",
        "label_vocabulary": len(carrier.inputs.label_targets),
        "prior_mass_supremum_over_the_label_vocabulary": max(prior_masses.values()),
        "prior_mass_sum_over_the_label_vocabulary": sum(prior_masses.values()),
        "pinned_snapshot_carries_the_pre_repair_prior": (
            "the pinned Audio2Tool snapshot is HISTORICAL evidence and carries the un-nested "
            "prior_score the semantics repair diagnosed (supremum 4.1, 193 of 12,601 values "
            "outside [0,1]); the repair built a corrected snapshot at a NEW path that nothing "
            "consumes, so C2's label prior on this carrier is a relative frequency and not a "
            "probability. kb_policy._dimension_scales divides it to the common scale before "
            "the ranker sees it, and C2's own normalization is invariant to its overall "
            "scale, but the limitation is reported rather than hidden"
        ),
    }
    return population, gate


# ---------------------------------------------------------------------------
# Per-population assembly
# ---------------------------------------------------------------------------


def _identity_key(replay: FormReplay) -> tuple:
    """Everything this gate observes about one sample at one form.

    Two forms fall in the same PER-SAMPLE identity class when this tuple agrees
    on every sample -- a strictly stronger relation than "an exact identity on
    every measured quantity", which is decided against
    :func:`reported_quantities` because that is the table a reader is shown.
    The blend head's own numbers are deliberately NOT in either: they are
    reported separately, because a fused-label-score difference the alpha veto
    discards is not a quantity of the decision surface at all.
    """

    return (
        replay.candidate_rank_gold_content,
        replay.candidate_rank_gold_any,
        replay.admitted_facet_ids,
        replay.top_m_facet_ids,
        replay.selected_value_ids,
        replay.supplied_targets,
        replay.gold_supplied,
        replay.gold_target_rank,
        replay.dispatched,
    )


#: Every component :func:`_identity_key` compares, named so the identity claim
#: can be read component by component instead of as one boolean.
IDENTITY_COMPONENTS = (
    "candidate_rank_gold_content",
    "candidate_rank_gold_any",
    "admitted_facet_ids",
    "top_m_facet_ids",
    "selected_value_ids",
    "supplied_targets",
    "gold_supplied",
    "gold_target_rank",
    "dispatched",
)


def identity_breakdown(
    *, control: Mapping[str, FormReplay], variant: Mapping[str, FormReplay]
) -> dict[str, object]:
    """How many samples differ on EACH measured component, not just whether any
    does.

    A single boolean would hide the distinction this gate turns on: a form can
    reorder the top-``m`` WINDOW -- which facets sit in it, and in what order --
    while leaving the ADMITTED subset of that window, the supply, the dispatch
    decision and every gold-position count exactly as landed. That is a
    different fact from "nothing changed", and it is reported as one.
    """

    counts = {name: 0 for name in IDENTITY_COMPONENTS}
    for sample_id, base in control.items():
        var = variant[sample_id]
        for name in IDENTITY_COMPONENTS:
            if getattr(base, name) != getattr(var, name):
                counts[name] += 1
    return {
        "samples": len(control),
        "samples_differing_by_component": counts,
        "components_that_move": [name for name, count in counts.items() if count],
        "identical_on_every_component": not any(counts.values()),
        "identical_on_every_decision_bearing_component": not any(
            counts[name]
            for name in (
                "admitted_facet_ids",
                "selected_value_ids",
                "supplied_targets",
                "gold_supplied",
                "gold_target_rank",
                "dispatched",
                "candidate_rank_gold_content",
                "candidate_rank_gold_any",
            )
        ),
    }


def blend_head_effect(
    *,
    control: Mapping[str, FormReplay],
    variant: Mapping[str, FormReplay],
    direct_labels: Mapping[str, str | None],
) -> dict[str, object]:
    """What the C2 / C2B layer actually moves, and why it cannot reach a decision.

    The alpha-veto theorem is IMPORTED from the cross-carrier read rather than
    restated: at ``alpha < 0.5`` a RECOVERED direct label is the strict unique
    argmax of the blend for EVERY possible supply, so the retain/dispatch
    decision is a function of direct-label recovery and supply emptiness alone.
    Anything entering ``_fused_label_scores`` is therefore structurally unable
    to change a dispatch decision at the locked cell. That is a description of
    the current policy form, not a proposal to change it.
    """

    argmax_changed = [
        sample_id
        for sample_id, base in control.items()
        if base.best_labels != variant[sample_id].best_labels
    ]
    decision_changed = [
        sample_id
        for sample_id, base in control.items()
        if base.dispatched != variant[sample_id].dispatched
    ]
    dispatched_with_label = [
        sample_id
        for sample_id, replay in variant.items()
        if replay.dispatched and direct_labels[sample_id] is not None
    ]
    return {
        "blend_argmax_changed_vs_c0": len(argmax_changed),
        "blend_argmax_changed_sample_ids": argmax_changed[:20],
        "retain_dispatch_decision_changed_vs_c0": len(decision_changed),
        "dispatched_trajectories_with_a_recovered_direct_label": len(dispatched_with_label),
        "alpha_veto_theorem": ccd.alpha_veto_theorem(FROZEN_ALPHA),
    }


def full_kb_recall(positions: Mapping[str, int | None]) -> dict[str, object]:
    """Gold-facet recall at 1 and at 5 in the FULL-KB content-facet ordering.

    Identical for every form by construction -- the full-KB ordering is a pure
    cosine ordering over the landed facet vectors and no arm touches it -- so
    it is reported once per population as the anchor the candidate-list numbers
    are read against.
    """

    total = len(positions)
    at1 = sum(1 for value in positions.values() if value is not None and value <= 1)
    at5 = sum(1 for value in positions.values() if value is not None and value <= 5)
    absent = sum(1 for value in positions.values() if value is None)
    return {
        "n": total,
        "recall_at_1_count": at1,
        "recall_at_1_rate": _rate(at1, total),
        "recall_at_5_count": at5,
        "recall_at_5_rate": _rate(at5, total),
        "gold_bearing_facet_absent_from_kb": absent,
        "identical_across_every_form": True,
        "why": (
            "the full-KB ordering is a pure cosine ordering over the landed content-facet "
            "vectors; no scoring form touches it"
        ),
    }


def reported_quantities(entry: Mapping[str, object]) -> dict[str, object]:
    """Exactly the numbers this gate PUBLISHES for one form on one population.

    "EXACT IDENTITY on every measured quantity", the phrase F1 turns on, is
    read against THIS dictionary -- the per-form table a reader sees -- rather
    than against per-sample internals. A form that reorders the top-``m``
    window without changing which of its members are admitted, what is
    supplied, or where gold sits has changed no measured quantity; the
    per-sample movement is still published, in ``identity_breakdown``, as the
    finer evidence.
    """

    out: dict[str, object] = {}
    for definition in GOLD_DEFINITIONS:
        block = entry["candidate_recall"][definition]
        for key in ("recall_at_1_count", "recall_at_5_count", "gold_absent_from_candidate_list"):
            out[f"candidate/{definition}/{key}"] = block[key]
    for key, value in entry["supply_axis"].items():
        if key.endswith("_rate"):
            continue
        out[f"supply/{key}"] = value
    return out


def analyse_population(
    population: PopulationInputs,
    forms: Mapping[str, Mapping[str, FormReplay]],
    *,
    unexposed_changes: Mapping[str, int] | None = None,
) -> dict[str, object]:
    """Every reported quantity, every form, on one population."""

    control = forms[FORM_C0]
    per_form: dict[str, object] = {}
    for form in FORMS:
        variant = forms[form]
        entry: dict[str, object] = {
            "description": FORM_DESCRIPTIONS[form],
            "role": "CONTROL" if form == FORM_C0 else "CANDIDATE OR COMPARATOR",
            "candidate_recall": {
                definition: candidate_list_recall(variant, attribute=GOLD_ATTRIBUTE[definition])
                for definition in GOLD_DEFINITIONS
            },
            "supply_axis": supply_axis(variant, population.gold_targets),
        }
        per_form[form] = entry

    for form in FORMS:
        variant = forms[form]
        entry = per_form[form]
        delta = decision_delta(
            control=control,
            variant=variant,
            gold_targets=population.gold_targets,
            flown_dispatched=population.flown_dispatched,
            flown_supply=population.flown_supply,
        )
        entry["decision_delta_vs_c0"] = delta
        breakdown = identity_breakdown(control=control, variant=variant)
        entry["identity_breakdown"] = breakdown
        entry["reported_quantities"] = reported_quantities(entry)
        entry["identical_to_control_on_every_measured_quantity"] = bool(
            entry["reported_quantities"] == per_form[FORM_C0]["reported_quantities"]
            and delta["decisions_changed_vs_c0"] == 0
            and delta["admitted_set_changes_vs_c0"] == 0
            and delta["dispatched_trajectories_GAINING_gold_bearing_supply"] == 0
            and delta["dispatched_trajectories_LOSING_gold_bearing_supply"] == 0
        )
        entry["identical_to_control_on_every_per_sample_component"] = bool(
            breakdown["identical_on_every_component"]
        )
        entry["blend_head_effect"] = blend_head_effect(
            control=control, variant=variant, direct_labels=population.direct_labels
        )
        entry["two_axis_scoreboard"] = {
            "matching_axis": conversion_projection(
                control=control,
                variant=variant,
                gold_targets=population.gold_targets,
                sealed_correct=population.sealed_correct,
                direct_correct=population.direct_correct,
            ),
            "extraction_axis": extraction_projection(
                control_axis=per_form[FORM_C0]["supply_axis"],
                variant_axis=entry["supply_axis"],
            ),
        }
        unexposed_changed = (
            unexposed_changes.get(form) if unexposed_changes is not None else None
        )
        entry["falsifier"] = falsifier_verdict(
            population_id=population.population_id,
            control=per_form[FORM_C0],
            variant=entry,
            delta=delta,
            unexposed_decisions_changed=unexposed_changed,
        )
        if form == FORM_C3:
            entry["k1_measured_prior"] = K1_RRF_PRIOR

    identity_matrix: dict[str, list[str]] = {}
    for left in FORMS:
        identity_matrix[left] = [
            right
            for right in FORMS
            if all(
                _identity_key(forms[left][sample_id]) == _identity_key(forms[right][sample_id])
                for sample_id in population.sample_ids
            )
        ]

    return {
        "population_id": population.population_id,
        "carrier": population.carrier,
        "n": len(population.sample_ids),
        "flown_dispatched": sum(1 for value in population.flown_dispatched.values() if value),
        "full_kb_content_facet_recall": full_kb_recall(population.full_kb_gold_position),
        "label_vocabulary": len(population.inputs.label_targets),
        "trajectories_with_a_recovered_direct_label": sum(
            1 for value in population.direct_labels.values() if value is not None
        ),
        "by_form": per_form,
        "form_identity_classes": identity_matrix,
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Execute the gate. Offline guard armed BEFORE the first input is opened."""

    attempts = ra.arm_offline_guard()

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()

    slurp_populations, slurp_sources = load_slurp(repo_root=repo_root, data_root=data_root)
    a2t_population, a2t_sources = load_a2t(repo_root=repo_root, data_root=data_root)

    replayed: dict[str, dict[str, dict[str, FormReplay]]] = {}
    self_gates: dict[str, object] = {}
    for population_id, population in list(slurp_populations.items()) + [
        (A2T_POPULATION, a2t_population)
    ]:
        forms, gate = replay_all_forms(population)
        replayed[population_id] = forms
        self_gates[population_id] = gate

    # F5 is defined on the UNEXPOSED 500 and is carried into every population's
    # verdict, because the clause is a property of the FORM, not of the
    # population it happens to be evaluated on.
    unexposed = slurp_populations[SLURP_UNEXPOSED]
    unexposed_forms = replayed[SLURP_UNEXPOSED]
    unexposed_changes = {
        form: int(
            decision_delta(
                control=unexposed_forms[FORM_C0],
                variant=unexposed_forms[form],
                gold_targets=unexposed.gold_targets,
                flown_dispatched=unexposed.flown_dispatched,
                flown_supply=unexposed.flown_supply,
            )["decisions_changed_vs_c0"]
        )
        for form in FORMS
    }

    results: dict[str, object] = {}
    for population_id, population in list(slurp_populations.items()) + [
        (A2T_POPULATION, a2t_population)
    ]:
        results[population_id] = analyse_population(
            population, replayed[population_id], unexposed_changes=unexposed_changes
        )
        results[population_id]["c0_self_gate"] = self_gates[population_id]
        if population_id == SLURP_UNEXPOSED:
            results[population_id]["reading_status"] = SECONDARY_READING

    # The overall verdict per form: a form is refused if it is refused on ANY
    # population, exactly as F4's "on ANY population" language requires.
    overall: dict[str, object] = {}
    for form in FORMS:
        per_population = {
            population_id: results[population_id]["by_form"][form]["falsifier"]["verdict"]
            for population_id in results
        }
        survives_everywhere = all(
            results[population_id]["by_form"][form]["falsifier"]["all_five_clauses_hold"]
            for population_id in results
        )
        identical_everywhere = all(
            results[population_id]["by_form"][form][
                "identical_to_control_on_every_measured_quantity"
            ]
            for population_id in results
        )
        if form == FORM_C0:
            verdict = (
                "CONTROL -- the live landed form. It is the baseline every other form is "
                "measured against, not a candidate, and its own F1 row is definitionally an "
                "identity rather than a finding."
            )
        elif identical_everywhere:
            verdict = (
                "REFUSED -- NO MEASURABLE GAIN (an exact identity on every measured quantity "
                "on every population; expressly NOT the same verdict as HARMFUL)"
            )
        elif survives_everywhere:
            verdict = "SURVIVES the falsifier as registered on every population"
        elif not any(
            results[population_id]["by_form"][form]["falsifier"]["all_five_clauses_hold"]
            for population_id in results
        ):
            verdict = "REFUSED on EVERY population"
        else:
            verdict = "REFUSED on at least one population"
        overall[form] = {
            "description": FORM_DESCRIPTIONS[form],
            "role": "CONTROL" if form == FORM_C0 else "CANDIDATE OR COMPARATOR",
            "verdict": verdict,
            "survives_on_every_population": survives_everywhere,
            "identical_to_control_on_every_population": identical_everywhere,
            "unexposed_500_decisions_changed": unexposed_changes[form],
            "per_population_verdict": per_population,
        }

    return {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "ledger_commit": LEDGER_COMMIT,
        "verdict_document": VERDICT_RELPATH,
        "started_at": started_at.isoformat(),
        "registered_constants": {
            "forms": list(FORMS),
            "form_descriptions": FORM_DESCRIPTIONS,
            "rrf_k": RRF_K,
            "lambda_grid": list(LAMBDA_GRID),
            "frozen_cell": {
                "alpha": FROZEN_ALPHA,
                "tau": FROZEN_FUSE.tau,
                "m": FROZEN_FUSE.m,
                "c": FROZEN_FUSE.c,
                "top_l": FROZEN_FUSE.top_l,
                "top_k_per_dimension": FROZEN_TOP_K,
                "w_cos": FROZEN_WEIGHTS.w_cos,
                "w_prior": FROZEN_WEIGHTS.w_prior,
                "w_agree": FROZEN_WEIGHTS.w_agree,
            },
            "gold_bearing_facet_readings": list(GOLD_DEFINITIONS),
        },
        "falsifier": {
            "registered_verbatim": FALSIFIER,
            "quoted_from": f"docs/exposure-ledger.md at {LEDGER_COMMIT}",
            "evaluated_as_written": True,
            "primary_population": SLURP_UNEXPOSED,
            "corroborating_populations": [SLURP_EXPOSED, A2T_POPULATION],
        },
        "priors_carried_into_the_recommendation": {
            "k1_rrf": K1_RRF_PRIOR,
            "off_switch": OFF_SWITCH_PRIOR,
            "honest_prior_registered_in_advance": (
                "kb_policy._dimension_scales' own proof already establishes that under the "
                "locked knob table the post-repair supremum of the prior contribution is "
                "w_prior * 1.0 = 0.300, strictly below w_cos * tau = 0.325, so EVERY "
                "percept-admissible content facet already outranks EVERY prior-mass facet by "
                "construction -- which makes C1 a strong candidate to measure as an EXACT "
                "IDENTITY on the admitted set, and F1 is written so that such a result is a "
                "refusal rather than a success"
            ),
            "second_honest_prior": (
                "post-repair prior_score is a CONDITIONAL probability inside its own "
                "conditioning cell -- p(intent given scenario) on SLURP, p(tool given domain "
                "and category) on A2T -- so it is a probability but NOT a label marginal, and "
                "C2's use of it as a label prior is correct only up to the unmodelled cell "
                "marginal"
            ),
        },
        "sources": {"slurp": slurp_sources, "audio2tool": a2t_sources},
        "populations": results,
        "verdict_by_form": overall,
        "zero_contact_proof": {
            "registered_contacts": {
                "frozen_core": 0,
                "pinned_tool_embedding": 0,
                "tokenizer": 0,
                "http_or_socket": 0,
            },
            "offline_guard": {
                "armed_before_any_input_was_opened": True,
                "outbound_connection_attempts": attempts.count,
                "targets": list(attempts.targets),
            },
            "resident_llama_server": (
                "pid 38623 on port 8090 was not started, stopped, probed, reconfigured or "
                "contacted"
            ),
            "new_dependencies_installed": 0,
        },
        "wall_seconds": time.perf_counter() - started,
        "scope": (
            "DEV-tier ITERATION design input. THIS ROW GATES A CHANGE AND IS NOT ONE: no knob "
            "is changed, no line under rails/, core/ or configs/ is written, nothing "
            "hash-pinned moves, no snapshot is rebuilt, no receipt is displaced, no arm is "
            "re-flown, no new sample is touched and no new gold surface is opened."
        ),
        "conservatism": PROJECTION_LABEL,
        "lock_status": SECONDARY_READING,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    report = run(repo_root=args.repo_root, data_root=args.data_root)
    payload = json.dumps(report, indent=2, sort_keys=True, default=str)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
        digest = _sha256_file(args.out)
        print(f"receipt {args.out} sha256 {digest}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
