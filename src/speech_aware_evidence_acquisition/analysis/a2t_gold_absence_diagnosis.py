"""THE AUDIO2TOOL GOLD-ABSENCE DIAGNOSIS -- why the KB fails precisely on the
subgroup that dispatches, computed arithmetically at ZERO CONTACTS.

Row ``SAEA-SN-MF-A2T-GOLD-ABSENCE-DIAGNOSIS`` (model-free-check), registered in
``docs/exposure-ledger.md`` BEFORE any number here was computed.

THE QUESTION, STATED FIRST. The cross-carrier ceiling decomposition established
that of the 15 A2T trajectories surviving the structural alpha veto, only 4
received a supply carrying the gold tool's own value and 11 did not -- yet 68 of
104 would carry gold-bearing supply with NO alpha gate. So the KB serves the
alpha-vetoed majority about as well as SLURP's does and fails precisely on the
subgroup that dispatches. This module explains that correlation with numbers.

WHAT IT COMPUTES, in the order the registration fixed:

1. :func:`build_versus_ranking` -- Q1. For each gold-absent DISPATCHED
   trajectory, does the gold PRIMARY tool have ANY value in the pinned A2T
   ``KnowledgeSnapshot``, and does any of that value's content facets carry a
   landed vector? Splits into (a) BUILD coverage defect -- the gold tool has no
   value / no vectored facet at all -- and (b) RANKING defect -- present but not
   admitted. The two have completely different fixes, so the split is the
   deliverable.
2. :func:`reachability_curve` -- Q2. For every trajectory whose gold value
   exists, the best gold-bearing content facet's position under the CURRENT
   post-repair ranker over its OWN landed query vector, a recall-at-k curve on
   the fixed grid, and -- because a recall window is not an admitted window --
   the three DOWNSTREAM stages that each independently gate admission: the
   ``tau`` percept gate, the top-``m`` ranker window and the ``top_l`` target
   budget. The widened supply is then actually REPLAYED at each depth through
   ``kb_policy``'s own fuser, so "reaches it" is measured, not inferred.
3. :func:`dead_direct_contrast` -- Q3. The SLURP dead-direct retrieval deficit
   (gold-in-top-5 66.2-67.6 % vs 71.6-74.1 %; gold-facet cosine 0.775 vs 0.828)
   recomputed in its A2T form: 15 dead-direct against 89 label-recovered, on the
   two statistics the registration fixed before the module ran. Reported
   whichever way it comes out.
4. :func:`multiset_binding` -- Q4. The frozen ``a2t-scorer-v1`` demands equality
   of the full tool-name MULTISET. How many of the 15 are multi-tool gold at
   all, and how often did the supply carry only PART of a multi-tool gold
   answer?
5. :func:`form_repair_channel` -- Q5. The FORM channel sized separately from the
   KNOWLEDGE channel: empty/unparsed contact-0 answers becoming well-formed
   non-empty calls, independent of correctness, and the correctness delta
   attributable to each channel.
6. :func:`k3_dispatch_projection` -- the K3 (field-role-constrained contact-0)
   dispatch-rate projection the key-construction plan section 3 demands BEFORE
   the item may be considered, computed from landed answers only.

THE FIDELITY GATE IS NECESSARY, NOT DECORATIVE, and it was fixed in the
registration before any number was seen: no gold-coverage or gold-rank number is
read unless the offline supply replay reproduces the flight's OWN landed
per-sample supply, dispatch decision and direct-label recovery on 104 of 104.
:func:`run` refuses otherwise.

REUSE, NEVER REIMPLEMENTATION. Loading, replay, the fidelity gate and the gold
coverage block are imported from
:mod:`.cross_carrier_ceiling_decomposition`, and through it recall, ranking,
admission, fusion and the blend head all go through ``rails.kb_policy``'s own
registered ranker, registered fuser, ``_fused_label_scores``, ``_blend_scores``
and ``_argmax_labels``. Answers are scored by the frozen ``a2t-scorer-v1``
through ``rails.adapters.audio2tool.Audio2ToolAdapter.score``; call lists are
parsed by ``reproduction.toolcall_scoring.parse_tool_calls_text``; the empty-call
predicate is ``analysis.a2t_read.is_empty_tool_call``.

GOLD IS SCORING-SIDE ONLY. It is read from sealed records after the seal, never
on a runtime path; no gold value enters a prompt, a query vector or a policy
input. The A2T-G1-104 subset is EXPOSED and its seal was already broken by the
landed G1 read.

WHAT IT DOES NOT DO. It changes no knob and writes nothing under ``configs/``,
``rails/`` or ``core/``. It opens no model session, no embedding sidecar and no
tokenizer: :func:`run` arms ``dev100_reviewer_audit.arm_offline_guard`` BEFORE
the first input is opened and writes the recorded outbound-attempt count into
the receipt. The resident np2 A2T service on port 8090 is never contacted,
probed, reconfigured or stopped.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=<repo>/src \
      python -m speech_aware_evidence_acquisition.analysis.a2t_gold_absence_diagnosis \
        --repo-root <repo> --data-root $SPEECHRL_DATA_DIR --out <receipt>
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import a2t_admission_scale_sweep as sweep
from . import a2t_read
from . import contrast_fewshot_preanalysis as cf
from . import cross_carrier_ceiling_decomposition as ccd
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as audit
from ..rails import kb_policy as kb

EXPOSURE_ROW_ID = "SAEA-SN-MF-A2T-GOLD-ABSENCE-DIAGNOSIS"
SCHEMA = "saea-a2t-gold-absence-diagnosis-v1"

FROZEN_ALPHA = ccd.FROZEN_ALPHA
FROZEN_WEIGHTS = ccd.FROZEN_WEIGHTS
FROZEN_FUSE = ccd.FROZEN_FUSE
FROZEN_TOP_K = ccd.FROZEN_TOP_K

#: The reachability grid, fixed in the registration before the module ran. The
#: same shape the SLURP key-plane work produced, extended past 128 because this
#: KB is smaller and the tail is worth seeing whole.
DEPTH_GRID: tuple[int, ...] = (5, 8, 16, 32, 64, 128, 256, 512, 1024)

#: How many samples are cross-checked against a REAL ``kb.multidim_recall``
#: call before the vectorised full-KB cosine sweep is believed.
RECALL_FIDELITY_PROBES = cf.RECALL_FIDELITY_PROBES

#: The K-WIDEN prior, quoted from
#: ``docs/readiness/2026-08-25-key-construction-agenda-plan.md`` section 1. Any
#: depth recommendation this module's curve would license must carry it.
K_WIDEN_PRIOR = (
    "K-WIDEN K1 FLOWN plus its offline width-5 replay: widening the retrieval "
    "window changed the supply on 32 of 100 trajectories and produced 0 "
    "width-attributable flips (71/100 at delta -1). A reachability curve is "
    "evidence about REACHABILITY only; K-WIDEN is the measured counter-example "
    "to treating depth as conversion."
)

#: The SLURP dead-direct retrieval deficit, quoted from
#: ``docs/readiness/2026-08-25-key-construction-agenda-plan.md`` section 2.2.
#: Quoted, never recomputed -- this row opens no SLURP run directory.
SLURP_DEAD_DIRECT_DEFICIT = {
    "gold_in_top_5_dead_direct_range": [0.662, 0.676],
    "gold_in_top_5_label_recovered_range": [0.716, 0.741],
    "gold_facet_cosine_dead_direct": 0.775,
    "gold_facet_cosine_label_recovered": 0.828,
    "source": (
        "docs/readiness/2026-08-25-key-construction-agenda-plan.md section 2.2; "
        "QUOTED from the landed committed document, not recomputed here -- this "
        "row opens no SLURP run directory and touches no SLURP seal"
    ),
}


class DiagnosisError(RuntimeError):
    """A pinned identity or a pre-registered gate failed."""


# ---------------------------------------------------------------------------
# Full-KB dense geometry, computed once per sample
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SampleGeometry:
    """One trajectory's full-KB retrieval geometry over its landed query."""

    sample_id: str
    gold_primary: str
    dispatched: bool
    #: 1-based position of the best gold-bearing content facet in the recall
    #: ordering ``kb.multidim_recall`` itself uses (cosine descending, facet_id
    #: ascending), or ``None`` when no gold-bearing facet carries a vector.
    gold_facet_position: int | None
    gold_facet_id: str | None
    gold_facet_cosine: float | None
    #: 1-based rank of the gold TASK TARGET among all targets ordered by their
    #: best tau-passing facet cosine -- the quantity ``top_l`` gates.
    gold_target_rank_by_best_cosine: int | None
    gold_facet_passes_tau: bool
    top1_cosine: float
    tau_passing_targets_total: int
    kb_values_for_gold: int
    kb_facets_for_gold: int
    kb_vectored_facets_for_gold: int
    gold_in_label_vocabulary: bool


def _cosines(matrix, facet_norms, query_vector):
    import numpy as np

    query = np.asarray(query_vector, dtype=np.float64)
    denominator = facet_norms * float(np.linalg.norm(query))
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denominator > 0.0, matrix @ query / denominator, 0.0)


def compute_geometry(
    carrier: ccd.A2TAttempt4,
) -> tuple[dict[str, SampleGeometry], dict[str, object], dict[str, object]]:
    """Full-KB cosine geometry per trajectory, plus the recall fidelity probe.

    The ordering is ``kb.multidim_recall``'s OWN ordering (``np.lexsort`` on
    cosine descending with ``facet_id`` ascending as the tie-break), not a bare
    ``argsort``, so a position of ``p`` means exactly "this facet enters the
    recall window at ``top_k >= p``"."""

    import numpy as np

    bundle = carrier.bundle
    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)
    facet_id_rank = np.asarray(bundle.facet_id_rank)
    label_identities = set(bundle.label_targets.values())

    cosine_cache: dict[str, object] = {}
    geometry: dict[str, SampleGeometry] = {}
    recall_probes = 0
    cosine_probes = 0

    for probe_position, sample_id in enumerate(carrier.sample_ids):
        cosines = _cosines(matrix, facet_norms, carrier.inputs.query_vectors[sample_id])
        cosine_cache[sample_id] = cosines

        if probe_position < RECALL_FIDELITY_PROBES:
            reference = kb.multidim_recall(
                bundle.snapshot,
                {"content": carrier.inputs.query_vectors[sample_id]},
                carrier.inputs.facet_vectors,
                FROZEN_TOP_K,
            )
            replayed = cf.vectorised_recall(bundle, cosines, top_k=FROZEN_TOP_K)
            if set(reference) != set(replayed):
                raise DiagnosisError(
                    f"{sample_id}: vectorised recall admitted a different facet set "
                    "than kb.multidim_recall"
                )
            for facet_id, dim_scores in reference.items():
                for dimension, score in dim_scores.items():
                    if abs(score - replayed[facet_id][dimension]) > 1e-9:
                        raise DiagnosisError(
                            f"{sample_id}/{facet_id}/{dimension}: vectorised recall "
                            "score disagrees with kb.multidim_recall"
                        )
            recall_probes += 1

        order = np.lexsort((facet_id_rank, -cosines))
        gold = carrier.gold_primary[sample_id]

        gold_position: int | None = None
        gold_facet_id: str | None = None
        for rank_position, index in enumerate(order, start=1):
            facet_id = bundle.facet_ids[int(index)]
            if bundle.content_facet_target.get(facet_id) == gold:
                gold_position = rank_position
                gold_facet_id = facet_id
                break
        gold_cosine = (
            float(cosines[int(order[gold_position - 1])])
            if gold_position is not None
            else None
        )

        # Pin the vectorised cosine against kb_policy's own scalar cosine on
        # the window this sample's supply actually saw plus its gold facet.
        if probe_position < RECALL_FIDELITY_PROBES:
            probes = [int(index) for index in order[:8]]
            if gold_position is not None:
                probes.append(int(order[gold_position - 1]))
            query = tuple(
                float(value) for value in carrier.inputs.query_vectors[sample_id]
            )
            for index in probes:
                policy_value = kb._cosine(query, tuple(matrix[index].tolist()))
                if abs(policy_value - float(cosines[index])) > 1e-9:
                    raise DiagnosisError(
                        f"{sample_id}/{bundle.facet_ids[index]}: vectorised cosine "
                        "disagrees with kb_policy._cosine"
                    )
                cosine_probes += 1

        # The top_l stage orders TASK TARGETS by their best tau-passing facet
        # score. With every content facet carrying one dimension and zero prior
        # mass the ranker score is affine in the cosine, so ordering targets by
        # best tau-passing cosine is the same ordering -- and this module
        # verifies that claim empirically in `ranker_is_cosine_ordering`.
        best_by_target: dict[str, float] = {}
        tau = FROZEN_FUSE.tau
        passing = np.nonzero(cosines >= tau)[0]
        for index in passing:
            facet_id = bundle.facet_ids[int(index)]
            target = bundle.content_facet_target.get(facet_id)
            if target is None:
                continue
            score = float(cosines[int(index)])
            if score > best_by_target.get(target, -1.0):
                best_by_target[target] = score
        ranked_targets = sorted(best_by_target.items(), key=lambda item: (-item[1], item[0]))
        gold_target_rank = next(
            (
                position
                for position, (target, _score) in enumerate(ranked_targets, start=1)
                if target == gold
            ),
            None,
        )

        geometry[sample_id] = SampleGeometry(
            sample_id=sample_id,
            gold_primary=gold,
            dispatched=bool(carrier.flown_dispatched[sample_id]),
            gold_facet_position=gold_position,
            gold_facet_id=gold_facet_id,
            gold_facet_cosine=gold_cosine,
            gold_target_rank_by_best_cosine=gold_target_rank,
            gold_facet_passes_tau=(
                gold_cosine is not None and gold_cosine >= FROZEN_FUSE.tau
            ),
            top1_cosine=float(cosines[int(order[0])]),
            tau_passing_targets_total=len(ranked_targets),
            kb_values_for_gold=len(bundle.values_by_target.get(gold, ())),
            kb_facets_for_gold=sum(
                1
                for _facet_id, target in bundle.content_facet_target.items()
                if target == gold
            ),
            kb_vectored_facets_for_gold=int(
                len(bundle.facet_indices_by_target.get(gold, ()))
            ),
            gold_in_label_vocabulary=gold in label_identities,
        )

    probe_report = {
        "recall_fidelity_probes": recall_probes,
        "cosine_probes_against_kb_policy_cosine": cosine_probes,
        "semantics": (
            "the vectorised full-KB cosine sweep is not trusted until "
            "kb.multidim_recall admits the same facet set with the same scores "
            "on the probed samples and kb_policy._cosine reproduces each probed "
            "cosine to 1e-9"
        ),
    }
    kb_shape = {
        "content_facets_with_vectors": len(carrier.bundle.facet_ids),
        "snapshot_values": len(carrier.bundle.snapshot.values),
        "distinct_value_task_targets": len(carrier.bundle.values_by_target),
        "label_vocabulary_size": len(set(carrier.bundle.label_targets.values())),
        "content_facets_with_a_task_target": len(carrier.bundle.content_facet_target),
    }
    return geometry, probe_report, kb_shape, cosine_cache  # type: ignore[return-value]


def ranker_is_cosine_ordering(
    carrier: ccd.A2TAttempt4, cosine_cache: Mapping[str, object], *, depth: int = 128
) -> dict[str, object]:
    """Verify -- not assume -- that the registered ranker orders the recalled
    CONTENT facets exactly as the raw cosine does on this carrier.

    Section 2.1 of the key-construction plan established the affine collapse on
    SLURP. If it also holds here, "how deep must the window go" is a statement
    about the cosine ordering; if it does not, every depth claim below would
    have to be restated against the ranker's own order. Checked on every
    trajectory, at a window far deeper than the locked cell's."""

    bundle = carrier.bundle
    ranker = kb.rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
    agreements: set[float] = set()
    priors: set[float] = set()
    dims_totals: set[int] = set()
    checked = 0
    disagreements: list[str] = []
    for sample_id in carrier.sample_ids:
        recall_scores = cf.vectorised_recall(
            bundle, cosine_cache[sample_id], top_k=depth
        )
        state = dc._query_state(sample_id, bundle.snapshot_sha256)
        result = ranker(
            snapshot_sha256=bundle.snapshot_sha256,
            query_state=state,
            recall_scores=recall_scores,
        )
        # RankedFacet carries only (facet_id, score), so the score's own
        # components are recomputed here exactly as
        # kb._rank_weighted_cosine_prior_agreement computes them, through the
        # same _dimension_scales divisor.
        dims_total = len({dim for scores in recall_scores.values() for dim in scores})
        dims_totals.add(dims_total)
        content = [
            candidate
            for candidate in result.candidates
            if candidate.facet_id in bundle.content_facet_target
            and "content" in recall_scores.get(candidate.facet_id, {})
        ]
        for candidate in content:
            dim_scores = recall_scores[candidate.facet_id]
            prior_scores = [
                float(score)
                for dim, score in dim_scores.items()
                if dim in kb.PRIOR_MASS_DIMENSIONS
            ]
            agreements.add(round(len(dim_scores) / dims_total, 12))
            priors.add(round(max(prior_scores) if prior_scores else 0.0, 12))
        by_cosine = sorted(
            content,
            key=lambda candidate: (
                -float(recall_scores[candidate.facet_id]["content"]),
                candidate.facet_id,
            ),
        )
        if [candidate.facet_id for candidate in content] != [
            candidate.facet_id for candidate in by_cosine
        ]:
            disagreements.append(sample_id)
        checked += 1
    return {
        "trajectories_checked": checked,
        "recall_depth_used": depth,
        "content_facet_agreement_values": sorted(agreements),
        "content_facet_max_prior_values": sorted(priors),
        "recall_dims_total_values": sorted(dims_totals),
        "ranker_order_equals_cosine_order_on_content_facets": not disagreements,
        "disagreement_sample_ids": disagreements[:10],
        "consequence": (
            "with one dimension per content facet and zero prior mass the "
            "registered ranker's score is an affine map of the cosine, so the "
            "content-facet ordering IS the cosine ordering and every depth "
            "statement below is a statement about that single ordering"
        ),
    }


# ---------------------------------------------------------------------------
# The A2T prior-dimension defect, and whether it can touch any number here
# ---------------------------------------------------------------------------


def _rescale_prior(
    recall_scores: Mapping[str, Mapping[str, float]], mode: str
) -> dict[str, dict[str, float]]:
    """Three variants of the SAME recalled set, differing only in the
    prior-mass dimension's values.

    * ``as_flown`` -- untouched, i.e. the defective ``tool_total /
      category_total`` ratio the snapshot was built with;
    * ``prior_at_unity`` -- every prior-mass score set to 1.0, the SUPREMUM any
      genuine conditional probability ``p(tool | domain, category)`` could take;
    * ``prior_dropped`` -- the prior-mass dimension removed entirely, the
      INFIMUM.

    Any semantically corrected prior lies weakly between the second and the
    third, so if the supply is identical under both extremes then NO prior
    correction whatever can change it."""

    out: dict[str, dict[str, float]] = {}
    for facet_id, dim_scores in recall_scores.items():
        kept: dict[str, float] = {}
        for dim, score in dim_scores.items():
            if dim in kb.PRIOR_MASS_DIMENSIONS:
                if mode == "prior_dropped":
                    continue
                kept[dim] = 1.0 if mode == "prior_at_unity" else float(score)
            else:
                kept[dim] = float(score)
        if kept:
            out[facet_id] = kept
    return out


def prior_dimension_sensitivity(
    carrier: ccd.A2TAttempt4,
    cosine_cache: Mapping[str, object],
) -> dict[str, object]:
    """Bound the A2T prior defect's reach over every ranking statement here.

    THE DEFECT, already recorded in ``rails/kb_policy._dimension_scales``'s own
    docstring (owner ruling 2026-08-25):
    ``rails.knowledge_build_a2t`` sets ``prior_score = tool_total /
    category_total`` where ``tool_total`` counts a tool's rows across EVERY
    domain while ``category_total`` counts one ``(domain, category)`` only. The
    numerator is not a subset of the denominator, so the ratio is not a
    conditional probability and has no reason to be <= 1; the landed
    ``max(1.0, sup)`` repair is a monotone rescale of a wrong ratio, not a
    correction of it. The intended quantity is
    ``p(tool | domain, category) = count(tool AND category) / count(category)``.

    Rather than rebuild the snapshot under the corrected quantity -- which
    would need the source rows, a rebuild and a re-embed, none of which this
    zero-contact row may do -- this function BRACKETS every possible
    correction. A corrected prior is a probability, so it lies in ``[0, 1]``.
    The supply is replayed with the prior-mass dimension at its supremum (1.0
    everywhere) and at its infimum (removed), and both are compared against the
    as-flown supply on all 104 trajectories. If the supply is identical under
    both extremes, every ranking statement in this row is invariant to the
    defect, and the correction cannot move any number reported here."""

    bundle = carrier.bundle

    # The prior dimension's own shape on this snapshot, reproduced rather than
    # quoted from the kb_policy docstring.
    prior_recall = bundle.prior_dimension_recall
    prior_values = [
        float(score)
        for scores in prior_recall.values()
        for dim, score in scores.items()
        if dim in kb.PRIOR_MASS_DIMENSIONS
    ]
    snapshot_prior_values = [
        float(value.prior_score)
        for value in bundle.snapshot.values
        if value.prior_score is not None
    ]

    variants = ("as_flown", "prior_at_unity", "prior_dropped")
    supplies: dict[str, dict[str, tuple[str, ...]]] = {v: {} for v in variants}
    gold_supplied: dict[str, dict[str, bool]] = {v: {} for v in variants}
    prior_facets_in_top_m: list[int] = []

    ranker = kb.rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
    for sample_id in carrier.sample_ids:
        base = cf.vectorised_recall(bundle, cosine_cache[sample_id], top_k=FROZEN_TOP_K)
        state = dc._query_state(sample_id, bundle.snapshot_sha256)
        result = ranker(
            snapshot_sha256=bundle.snapshot_sha256,
            query_state=state,
            recall_scores=base,
        )
        top_m = [
            candidate.facet_id for candidate in result.candidates[: FROZEN_FUSE.m]
        ]
        prior_facets_in_top_m.append(
            sum(
                1
                for facet_id in top_m
                if not any(
                    dim not in kb.PRIOR_MASS_DIMENSIONS
                    for dim in base.get(facet_id, {})
                )
            )
        )
        gold = carrier.gold_primary[sample_id]
        for variant in variants:
            scores = _rescale_prior(base, variant)
            supply = dc.replay_supply(
                carrier.inputs,
                sample_id,
                weights=FROZEN_WEIGHTS,
                knobs=FROZEN_FUSE,
                top_k=FROZEN_TOP_K,
                recall_scores=scores,
            )
            supplies[variant][sample_id] = tuple(sorted(supply.selected_value_ids))
            gold_supplied[variant][sample_id] = any(
                bundle.values_by_id[value_id].task_target == gold
                for value_id in supply.selected_value_ids
            )

    def compare(variant: str) -> dict[str, object]:
        changed = [
            sample_id
            for sample_id in carrier.sample_ids
            if supplies[variant][sample_id] != supplies["as_flown"][sample_id]
        ]
        gold_changed = [
            sample_id
            for sample_id in carrier.sample_ids
            if gold_supplied[variant][sample_id] != gold_supplied["as_flown"][sample_id]
        ]
        return {
            "supply_changed_trajectories": len(changed),
            "supply_changed_sample_ids": changed[:20],
            "gold_supplied_flag_changed_trajectories": len(gold_changed),
            "gold_supplied_flag_changed_sample_ids": gold_changed[:20],
        }

    unity = compare("prior_at_unity")
    dropped = compare("prior_dropped")
    invariant = (
        unity["supply_changed_trajectories"] == 0
        and dropped["supply_changed_trajectories"] == 0
    )
    # The as-flown replay must also agree with the flight itself, which the
    # fidelity gate already asserted; re-stated here as the anchor of the
    # bracket.
    as_flown_matches_flight = all(
        supplies["as_flown"][sample_id]
        == tuple(sorted(carrier.flown_supply[sample_id]))
        for sample_id in carrier.sample_ids
        if carrier.flown_dispatched[sample_id]
    )
    return {
        "defect": (
            "rails.knowledge_build_a2t sets prior_score = tool_total / "
            "category_total, counting a tool's rows across EVERY domain against "
            "a single (domain, category) denominator. The numerator is not a "
            "subset of the denominator, so the ratio is not a conditional "
            "probability and has no reason to be <= 1. The intended quantity is "
            "p(tool | domain, category) = count(tool AND category) / "
            "count(category). The landed max(1.0, sup) repair in "
            "kb_policy._dimension_scales is a monotone rescale of a wrong "
            "ratio, not a correction of it."
        ),
        "already_recorded_at": (
            "rails/kb_policy.py _dimension_scales docstring (owner ruling "
            "2026-08-25), which states sup = 4.1 with 193 values above 1 on the "
            "pinned A2T snapshot ec2f9ec4..."
        ),
        "measured_prior_shape": {
            "prior_mass_facets_recalled": len(prior_recall),
            "recalled_prior_score_sup": max(prior_values) if prior_values else None,
            "recalled_prior_scores_above_1": sum(
                1 for value in prior_values if value > 1.0
            ),
            "snapshot_prior_mass_sup": (
                max(snapshot_prior_values) if snapshot_prior_values else None
            ),
            "snapshot_prior_mass_values_above_1": sum(
                1 for value in snapshot_prior_values if value > 1.0
            ),
        },
        "prior_mass_facets_inside_the_locked_top_m_window": {
            "max_over_trajectories": max(prior_facets_in_top_m),
            "total_over_trajectories": sum(prior_facets_in_top_m),
            "trajectories_with_at_least_one": sum(
                1 for count in prior_facets_in_top_m if count > 0
            ),
            "population": len(prior_facets_in_top_m),
        },
        "bracket": {
            "method": (
                "a corrected prior is a probability, so it lies in [0, 1]. The "
                "supply is replayed at the SUPREMUM (every prior-mass score set "
                "to 1.0) and at the INFIMUM (the prior-mass dimension removed "
                "entirely) and both are compared against the as-flown supply on "
                "all 104. Any semantically corrected prior lies weakly between "
                "the two, so agreement at both extremes is agreement everywhere."
            ),
            "prior_at_unity_vs_as_flown": unity,
            "prior_dropped_vs_as_flown": dropped,
            "as_flown_replay_matches_the_flight_on_dispatched": as_flown_matches_flight,
            "every_ranking_statement_here_is_invariant_to_the_prior_defect": invariant,
        },
        "disclosure": (
            "Q1's case-(b) membership and Q2's reachability curve are RANKING "
            "statements. They were computed under the as-flown, defective prior "
            "and are the record of what actually happened. The bracket above "
            "states, as a measurement rather than an assumption, whether any "
            "correction of that prior could move them."
        ),
    }


# ---------------------------------------------------------------------------
# Q1 -- BUILD coverage versus RANKING
# ---------------------------------------------------------------------------


def build_versus_ranking(
    carrier: ccd.A2TAttempt4,
    coverage: Mapping[str, object],
    geometry: Mapping[str, SampleGeometry],
) -> dict[str, object]:
    """Split the gold-absent DISPATCHED trajectories into BUILD and RANKING.

    (a) BUILD coverage defect -- the gold tool has NO value in the snapshot, or
        no content facet of that value carries a landed vector, so no ranking
        change whatever could ever surface it.
    (b) RANKING/recall defect -- the gold value is in the KB with a vectored
        facet, and the current key plane simply did not bring it into the
        admitted window."""

    per_sample = coverage["per_sample"]  # type: ignore[index]
    dispatched = list(coverage["dispatched_ids"])  # type: ignore[arg-type]
    gold_absent = [s for s in dispatched if not per_sample[s]["gold_supplied"]]

    build: list[dict[str, object]] = []
    ranking: list[dict[str, object]] = []
    for sample_id in sorted(gold_absent):
        geo = geometry[sample_id]
        row = {
            "sample_id": sample_id,
            "gold_primary_tool": geo.gold_primary,
            "kb_values_for_gold": geo.kb_values_for_gold,
            "kb_facets_for_gold": geo.kb_facets_for_gold,
            "kb_vectored_facets_for_gold": geo.kb_vectored_facets_for_gold,
            "gold_in_label_vocabulary": geo.gold_in_label_vocabulary,
            "gold_facet_position": geo.gold_facet_position,
            "gold_facet_cosine": geo.gold_facet_cosine,
            "gold_facet_passes_tau": geo.gold_facet_passes_tau,
            "gold_target_rank_by_best_cosine": geo.gold_target_rank_by_best_cosine,
            "top1_cosine": geo.top1_cosine,
            "blend_correct": bool(per_sample[sample_id]["blend_correct"]),
        }
        if geo.kb_values_for_gold == 0 or geo.kb_vectored_facets_for_gold == 0:
            build.append(row)
        else:
            ranking.append(row)

    total = len(gold_absent)
    dominating = (
        "RANKING"
        if len(ranking) > len(build)
        else ("BUILD" if len(build) > len(ranking) else "TIED")
    )
    return {
        "question": (
            "of the gold-absent DISPATCHED trajectories, which have no gold "
            "value in the KB at all (BUILD) and which have one that was not "
            "admitted (RANKING)?"
        ),
        "gold_absent_dispatched_n": total,
        "case_a_build_coverage_defect": {
            "n": len(build),
            "share": (len(build) / total) if total else None,
            "sample_ids": [row["sample_id"] for row in build],
            "rows": build,
            "fix": (
                "KB CONSTRUCTION -- the tool has no value or no vectored content "
                "facet in the pinned snapshot, so no ranker, no width and no key "
                "representation can ever surface it"
            ),
        },
        "case_b_ranking_recall_defect": {
            "n": len(ranking),
            "share": (len(ranking) / total) if total else None,
            "sample_ids": [row["sample_id"] for row in ranking],
            "rows": ranking,
            "fix": (
                "THE KEY PLANE -- the gold value is present and vectored; the "
                "current ranking did not bring it inside the admitted window"
            ),
        },
        "dominating_sub_cause": dominating,
        "population_coverage_context": {
            "trajectories_whose_gold_tool_has_no_kb_value": sum(
                1 for geo in geometry.values() if geo.kb_values_for_gold == 0
            ),
            "trajectories_whose_gold_tool_has_no_vectored_facet": sum(
                1 for geo in geometry.values() if geo.kb_vectored_facets_for_gold == 0
            ),
            "population": len(geometry),
            "reading": (
                "the same two counts over all 104, so the dispatched subgroup's "
                "split can be read against the carrier's own build coverage"
            ),
        },
    }


# ---------------------------------------------------------------------------
# Q2 -- the reachability curve, and which stage actually binds
# ---------------------------------------------------------------------------


def _widened_supply_reaches_gold(
    carrier: ccd.A2TAttempt4,
    sample_id: str,
    cosines,
    *,
    depth: int,
    top_l: int,
) -> bool:
    """Replay recall -> rank -> fuse at a widened window and ask whether a
    gold-bearing VALUE is actually selected. Measured through ``kb_policy``'s
    own fuser, never inferred from a rank."""

    recall_scores = cf.vectorised_recall(carrier.bundle, cosines, top_k=depth)
    knobs = kb.FuseKnobs(
        tau=FROZEN_FUSE.tau, m=depth, c=FROZEN_FUSE.c, top_l=top_l
    )
    supply = dc.replay_supply(
        carrier.inputs,
        sample_id,
        weights=FROZEN_WEIGHTS,
        knobs=knobs,
        top_k=depth,
        recall_scores=recall_scores,
    )
    gold = carrier.gold_primary[sample_id]
    return any(
        carrier.bundle.values_by_id[value_id].task_target == gold
        for value_id in supply.selected_value_ids
    )


def reachability_curve(
    carrier: ccd.A2TAttempt4,
    coverage: Mapping[str, object],
    geometry: Mapping[str, SampleGeometry],
    cosine_cache: Mapping[str, object],
    split: Mapping[str, object],
) -> dict[str, object]:
    """The recall-at-k curve for the case-(b) set, and the binding stage.

    A recall window is not an admitted window. Three stages sit between the
    recall ordering and the supply, and each can independently keep the gold
    value out: the ``tau`` percept gate, the top-``m`` ranker window, and the
    ``top_l`` target budget. This function reports the curve, then REPLAYS the
    widened supply at each depth so "reaches it" is a measurement."""

    case_b_ids = list(
        split["case_b_ranking_recall_defect"]["sample_ids"]  # type: ignore[index]
    )

    def curve(ids: Sequence[str]) -> dict[str, object]:
        total = len(ids)
        rows: dict[str, object] = {}
        for depth in DEPTH_GRID:
            count = sum(
                1
                for sample_id in ids
                if geometry[sample_id].gold_facet_position is not None
                and geometry[sample_id].gold_facet_position <= depth
            )
            rows[f"recall_at_{depth}"] = {
                "count": count,
                "rate": (count / total) if total else None,
            }
        reached = sum(
            1 for sample_id in ids if geometry[sample_id].gold_facet_position is not None
        )
        rows["recall_at_full_kb"] = {
            "count": reached,
            "rate": (reached / total) if total else None,
        }
        positions = sorted(
            geometry[sample_id].gold_facet_position
            for sample_id in ids
            if geometry[sample_id].gold_facet_position is not None
        )
        rows["n"] = total
        rows["gold_facet_position_min"] = positions[0] if positions else None
        rows["gold_facet_position_median"] = (
            statistics.median(positions) if positions else None
        )
        rows["gold_facet_position_max"] = positions[-1] if positions else None
        return rows

    dispatched = list(coverage["dispatched_ids"])  # type: ignore[arg-type]
    retained = [s for s in carrier.sample_ids if s not in set(dispatched)]

    per_sample_depth: list[dict[str, object]] = []
    for sample_id in sorted(case_b_ids):
        geo = geometry[sample_id]
        cosines = cosine_cache[sample_id]
        reached_at: int | None = None
        reached_at_unbounded_top_l: int | None = None
        for depth in DEPTH_GRID:
            if reached_at is None and _widened_supply_reaches_gold(
                carrier, sample_id, cosines, depth=depth, top_l=FROZEN_FUSE.top_l
            ):
                reached_at = depth
            if reached_at_unbounded_top_l is None and _widened_supply_reaches_gold(
                carrier,
                sample_id,
                cosines,
                depth=depth,
                top_l=len(set(carrier.bundle.label_targets.values())),
            ):
                reached_at_unbounded_top_l = depth
            if reached_at is not None and reached_at_unbounded_top_l is not None:
                break
        per_sample_depth.append(
            {
                "sample_id": sample_id,
                "gold_primary_tool": geo.gold_primary,
                "gold_facet_position": geo.gold_facet_position,
                "gold_facet_cosine": geo.gold_facet_cosine,
                "gold_facet_passes_tau_0_65": geo.gold_facet_passes_tau,
                "gold_target_rank_by_best_cosine": geo.gold_target_rank_by_best_cosine,
                "tau_passing_targets_total": geo.tau_passing_targets_total,
                "supply_reaches_gold_at_depth_locked_top_l_3": reached_at,
                "supply_reaches_gold_at_depth_unbounded_top_l": (
                    reached_at_unbounded_top_l
                ),
                "top1_cosine": geo.top1_cosine,
            }
        )

    binding_tau = sum(
        1 for row in per_sample_depth if not row["gold_facet_passes_tau_0_65"]
    )
    binding_top_l = sum(
        1
        for row in per_sample_depth
        if row["gold_facet_passes_tau_0_65"]
        and row["supply_reaches_gold_at_depth_locked_top_l_3"] is None
        and row["supply_reaches_gold_at_depth_unbounded_top_l"] is not None
    )
    reached_locked_top_l = sum(
        1
        for row in per_sample_depth
        if row["supply_reaches_gold_at_depth_locked_top_l_3"] is not None
    )
    reached_any = sum(
        1
        for row in per_sample_depth
        if row["supply_reaches_gold_at_depth_locked_top_l_3"] is not None
        or row["supply_reaches_gold_at_depth_unbounded_top_l"] is not None
    )

    return {
        "question": (
            "for the case-(b) trajectories whose gold value exists in the KB, "
            "what is its rank under the CURRENT post-repair ranker and how deep "
            "would the admitted window have to go to reach it?"
        ),
        "curve_case_b_ranking_defect": curve(case_b_ids),
        "curve_all_dispatched": curve(dispatched),
        "curve_all_retained": curve(retained),
        "curve_whole_population": curve(list(carrier.sample_ids)),
        "per_sample_depth": per_sample_depth,
        "binding_stage": {
            "case_b_n": len(case_b_ids),
            "blocked_by_the_tau_percept_gate": binding_tau,
            "blocked_by_the_top_l_target_budget_only": binding_top_l,
            "reached_at_some_depth_under_the_locked_top_l_3": reached_locked_top_l,
            "reached_at_some_depth_under_any_top_l": reached_any,
            "semantics": (
                "a facet whose best cosine is below tau = 0.65 is refused by the "
                "percept gate at EVERY window depth, so for those trajectories no "
                "value of k or m is a fix at all. A facet that passes tau but "
                "whose TARGET is outside the top_l = 3 target budget is refused by "
                "the budget, not by the window -- widening k or m cannot reach it "
                "either."
            ),
        },
        "admissibility": {
            "locked_cell_depth": {
                "top_k": FROZEN_TOP_K,
                "m": FROZEN_FUSE.m,
                "tau": FROZEN_FUSE.tau,
                "c": FROZEN_FUSE.c,
                "top_l": FROZEN_FUSE.top_l,
            },
            "any_depth_change_is_a_knob_change": (
                "k, m, tau, c and top_l are all cells of "
                "configs/policy/kb-policy-v1-dev100.json, which is LOCKED. No "
                "depth in this curve is admissible without an owner knob "
                "decision; this module computes the curve and makes no such "
                "decision."
            ),
            "k_widen_prior": K_WIDEN_PRIOR,
        },
    }


# ---------------------------------------------------------------------------
# Q3 -- the dead-direct query deficit
# ---------------------------------------------------------------------------


def query_key_degeneracy(
    carrier: ccd.A2TAttempt4, dead: Sequence[str], live: Sequence[str]
) -> dict[str, object]:
    """How much trajectory-specific information the retrieval key carries.

    The content-dimension query vector IS the embedding of the trajectory's OWN
    contact-0 answer text. When that answer is literally the same string on many
    trajectories -- which is what an EMPTY tool call is -- the query vector is
    the SAME vector, so those trajectories recall the same facets whatever the
    utterance was about. This function counts the distinct keys rather than
    assuming anything about them."""

    import hashlib

    def digest(sample_id: str) -> str:
        vector = carrier.inputs.query_vectors[sample_id]
        return hashlib.sha256(
            ",".join(repr(float(value)) for value in vector).encode("utf-8")
        ).hexdigest()

    def block(ids: Sequence[str], label: str) -> dict[str, object]:
        texts = Counter(carrier.direct_texts[sample_id] for sample_id in ids)
        keys = Counter(digest(sample_id) for sample_id in ids)
        largest_key, largest_count = (
            keys.most_common(1)[0] if keys else ("", 0)
        )
        cluster = sorted(
            sample_id for sample_id in ids if digest(sample_id) == largest_key
        )
        return {
            "label": label,
            "n": len(ids),
            "distinct_contact0_texts": len(texts),
            "distinct_query_vectors": len(keys),
            "distinct_query_vectors_per_trajectory": (
                len(keys) / len(ids) if ids else None
            ),
            "largest_identical_query_cluster_size": largest_count,
            "largest_identical_query_cluster_sample_ids": cluster,
            "largest_identical_query_cluster_share": (
                largest_count / len(ids) if ids else None
            ),
        }

    dead_block = block(dead, "dead-direct (dispatched)")
    live_block = block(live, "label-recovered (retained)")

    # What the largest degenerate cluster actually received. If one key is
    # shared, one supply is shared, and gold can only arrive by coincidence.
    cluster = list(dead_block["largest_identical_query_cluster_sample_ids"])
    supplies_in_cluster: dict[tuple[str, ...], list[str]] = {}
    for sample_id in cluster:
        targets = tuple(
            sorted(
                {
                    str(carrier.bundle.values_by_id[value_id].task_target)
                    for value_id in carrier.flown_supply[sample_id]
                    if carrier.bundle.values_by_id[value_id].task_target is not None
                }
            )
        )
        supplies_in_cluster.setdefault(targets, []).append(sample_id)
    constant_targets = (
        list(next(iter(supplies_in_cluster))) if len(supplies_in_cluster) == 1 else None
    )
    gold_inside = [
        sample_id
        for sample_id in cluster
        if constant_targets is not None
        and carrier.gold_primary[sample_id] in set(constant_targets)
    ]

    return {
        "question": (
            "does the retrieval key carry trajectory-specific information on "
            "the dead-direct subgroup at all?"
        ),
        "provenance": (
            "the content-dimension query vector is the embedding of the "
            "trajectory's OWN contact-0 answer text -- contact 0's output IS the "
            "retrieval key. Verified in this row by re-hashing each landed "
            "Pass-A text against the text_sha256 its own landed query-vector "
            "record carries (ccd.load_a2t_attempt4)."
        ),
        "dead_direct": dead_block,
        "label_recovered": live_block,
        "largest_cluster_supply": {
            "cluster_size": len(cluster),
            "distinct_flown_supplies_inside_the_cluster": len(supplies_in_cluster),
            "the_constant_supply_targets": constant_targets,
            "cluster_members_whose_gold_is_inside_the_constant_supply": len(
                gold_inside
            ),
            "cluster_members_whose_gold_is_inside_sample_ids": gold_inside,
            "reading": (
                "one key, one supply. Every trajectory in this cluster received "
                "the SAME targets whatever its utterance was about, so gold can "
                "only arrive by coincidence -- when the trajectory's own gold "
                "tool happens to be one of the constant targets."
            ),
        },
        "reading": (
            "a distinct-query-vector count below the trajectory count means "
            "several trajectories share ONE retrieval key and therefore ONE "
            "recalled facet set, whatever their utterances were about"
        ),
    }


def dead_direct_contrast(
    carrier: ccd.A2TAttempt4,
    coverage: Mapping[str, object],
    geometry: Mapping[str, SampleGeometry],
) -> dict[str, object]:
    """The A2T form of the SLURP dead-direct retrieval deficit.

    Both statistics were fixed in the registration before the module ran: the
    gold-in-top-5 rate over the full-KB dense ordering, and the median best
    gold-bearing facet cosine. Reported whichever way it comes out."""

    dispatched = set(coverage["dispatched_ids"])  # type: ignore[arg-type]
    dead = sorted(dispatched)
    live = sorted(s for s in carrier.sample_ids if s not in dispatched)

    def profile(ids: Sequence[str], label: str) -> dict[str, object]:
        total = len(ids)
        in_kb = [s for s in ids if geometry[s].gold_facet_position is not None]
        in_top5 = sum(
            1
            for s in ids
            if geometry[s].gold_facet_position is not None
            and geometry[s].gold_facet_position <= FROZEN_TOP_K
        )
        cosines = [
            geometry[s].gold_facet_cosine
            for s in ids
            if geometry[s].gold_facet_cosine is not None
        ]
        positions = sorted(
            geometry[s].gold_facet_position
            for s in ids
            if geometry[s].gold_facet_position is not None
        )
        return {
            "label": label,
            "n": total,
            "gold_present_in_kb": len(in_kb),
            "gold_in_top_5": in_top5,
            "gold_in_top_5_rate_over_all_members": (in_top5 / total) if total else None,
            "gold_in_top_5_rate_over_members_with_gold_in_kb": (
                (in_top5 / len(in_kb)) if in_kb else None
            ),
            "gold_facet_cosine_median": (
                statistics.median(cosines) if cosines else None
            ),
            "gold_facet_cosine_mean": (
                statistics.fmean(cosines) if cosines else None
            ),
            "gold_facet_position_median": (
                statistics.median(positions) if positions else None
            ),
            "top1_cosine_median": statistics.median(
                [geometry[s].top1_cosine for s in ids]
            )
            if ids
            else None,
        }

    dead_profile = profile(dead, "dead-direct (dispatched, no direct label recovered)")
    live_profile = profile(live, "label-recovered (retained by the alpha veto)")
    degeneracy = query_key_degeneracy(carrier, dead, live)

    def _delta(key: str) -> float | None:
        left = dead_profile[key]
        right = live_profile[key]
        if left is None or right is None:
            return None
        return float(left) - float(right)

    top5_delta = _delta("gold_in_top_5_rate_over_all_members")
    cosine_delta = _delta("gold_facet_cosine_median")
    deficit_present = bool(
        (top5_delta is not None and top5_delta < 0.0)
        and (cosine_delta is not None and cosine_delta < 0.0)
    )
    return {
        "question": (
            "is the SLURP dead-direct retrieval deficit present on Audio2Tool?"
        ),
        "dead_direct": dead_profile,
        "label_recovered": live_profile,
        "delta_dead_minus_live": {
            "gold_in_top_5_rate": top5_delta,
            "gold_in_top_5_rate_over_members_with_gold_in_kb": _delta(
                "gold_in_top_5_rate_over_members_with_gold_in_kb"
            ),
            "gold_facet_cosine_median": cosine_delta,
            "top1_cosine_median": _delta("top1_cosine_median"),
        },
        "deficit_present_on_both_statistics": deficit_present,
        "query_key_degeneracy": degeneracy,
        "slurp_reference": SLURP_DEAD_DIRECT_DEFICIT,
        "reading_rule": (
            "PRE-REGISTERED: reported whichever way it comes out. An ABSENT "
            "deficit is the headline finding, not a reason to re-partition the "
            "population or re-choose the statistic. n = 15 against n = 89; no "
            "interval is computed and none should be."
        ),
    }


# ---------------------------------------------------------------------------
# Q4 -- is the multiset requirement binding?
# ---------------------------------------------------------------------------


def multiset_binding(
    carrier: ccd.A2TAttempt4,
    coverage: Mapping[str, object],
    *,
    gold_calls: Mapping[str, Sequence[object]],
) -> dict[str, object]:
    """How often the supply carried only PART of a multi-tool gold answer."""

    per_sample = coverage["per_sample"]  # type: ignore[index]
    dispatched = sorted(coverage["dispatched_ids"])  # type: ignore[arg-type]

    rows: dict[str, dict[str, object]] = {}
    for sample_id in carrier.sample_ids:
        names = [str(call.name) for call in gold_calls[sample_id]]
        distinct = sorted(set(names))
        supplied = set(per_sample[sample_id]["supplied_targets"])
        covered = sorted(supplied & set(distinct))
        rows[sample_id] = {
            "gold_call_count": len(names),
            "gold_distinct_tools": distinct,
            "gold_distinct_tool_count": len(distinct),
            "multi_tool_gold": len(distinct) >= 2,
            "gold_multiset": dict(Counter(names)),
            "supplied_targets": list(sorted(supplied)),
            "gold_tools_covered_by_supply": covered,
            "gold_tools_covered_count": len(covered),
            "supply_covers_the_whole_gold_tool_set": (
                bool(distinct) and set(distinct) <= supplied
            ),
            "supply_covers_only_part_of_a_multi_tool_gold": (
                len(distinct) >= 2 and 0 < len(covered) < len(distinct)
            ),
            "blend_correct": bool(per_sample[sample_id]["blend_correct"]),
            "gold_supplied_primary": bool(per_sample[sample_id]["gold_supplied"]),
        }

    def block(ids: Sequence[str], label: str) -> dict[str, object]:
        multi = [s for s in ids if rows[s]["multi_tool_gold"]]
        partial = [
            s for s in ids if rows[s]["supply_covers_only_part_of_a_multi_tool_gold"]
        ]
        whole = [s for s in ids if rows[s]["supply_covers_the_whole_gold_tool_set"]]
        return {
            "label": label,
            "n": len(ids),
            "multi_tool_gold_n": len(multi),
            "multi_tool_gold_sample_ids": multi,
            "multi_tool_gold_share": (len(multi) / len(ids)) if ids else None,
            "supply_covered_the_whole_gold_tool_set_n": len(whole),
            "supply_covered_only_part_of_a_multi_tool_gold_n": len(partial),
            "supply_covered_only_part_sample_ids": partial,
            "multi_tool_gold_blend_correct": sum(
                1 for s in multi if rows[s]["blend_correct"]
            ),
            "single_tool_gold_blend_correct": sum(
                1 for s in ids if not rows[s]["multi_tool_gold"] and rows[s]["blend_correct"]
            ),
            "single_tool_gold_n": len(ids) - len(multi),
        }

    with_gold = [s for s in dispatched if per_sample[s]["gold_supplied"]]
    return {
        "question": (
            "the frozen scorer demands the full tool-name multiset. Among the "
            "dispatched trajectories, how often was the supply carrying only "
            "PART of a multi-tool gold answer?"
        ),
        "scorer_semantics": (
            "a2t-scorer-v1 tool accuracy is equality of the full tool-name "
            "MULTISET (collections.Counter over call names); the dispatch "
            "projection uses only the PRIMARY (first) call's name, so on a "
            "multi-tool item the projection is lossy by construction"
        ),
        "population": block(list(carrier.sample_ids), "all 104"),
        "dispatched_15": block(dispatched, "the 15 dispatched"),
        "dispatched_with_gold_bearing_supply_4": block(
            with_gold, "the dispatched trajectories whose supply carried gold"
        ),
        "per_sample": {
            sample_id: rows[sample_id] for sample_id in dispatched
        },
    }


# ---------------------------------------------------------------------------
# Q5 -- the FORM channel, sized separately from the KNOWLEDGE channel
# ---------------------------------------------------------------------------


def _form_class(text: str) -> str:
    from ..reproduction.toolcall_scoring import parse_tool_calls_text

    calls, parsed = parse_tool_calls_text(text)
    if not parsed:
        return "unparsed"
    if not calls:
        return "empty"
    return "well-formed-non-empty"


def form_repair_channel(
    carrier: ccd.A2TAttempt4,
    coverage: Mapping[str, object],
) -> dict[str, object]:
    """Separate the FORM channel from the KNOWLEDGE channel on the 15."""

    per_sample = coverage["per_sample"]  # type: ignore[index]
    dispatched = sorted(coverage["dispatched_ids"])  # type: ignore[arg-type]

    rows: dict[str, dict[str, object]] = {}
    for sample_id in dispatched:
        contact0 = _form_class(carrier.direct_texts[sample_id])
        final = _form_class(carrier.blend_final_texts[sample_id])
        label_at_contact0 = sweep.a2t_label_normalizer(
            carrier.direct_texts[sample_id], carrier.inputs.label_targets
        )
        label_at_final = sweep.a2t_label_normalizer(
            carrier.blend_final_texts[sample_id], carrier.inputs.label_targets
        )
        rows[sample_id] = {
            "contact0_form": contact0,
            "blend_final_form": final,
            "form_repaired": contact0 in ("empty", "unparsed")
            and final == "well-formed-non-empty",
            "contact0_in_vocabulary_label": label_at_contact0,
            "blend_final_in_vocabulary_label": label_at_final,
            "contact0_empty_by_frozen_predicate": bool(
                a2t_read.is_empty_tool_call(carrier.direct_texts[sample_id])
            ),
            "blend_final_empty_by_frozen_predicate": bool(
                a2t_read.is_empty_tool_call(carrier.blend_final_texts[sample_id])
            ),
            "gold_supplied": bool(per_sample[sample_id]["gold_supplied"]),
            "contact0_correct": bool(per_sample[sample_id]["direct_correct"]),
            "blend_correct": bool(per_sample[sample_id]["blend_correct"]),
            "m0_arm_correct": bool(per_sample[sample_id]["m0_correct"]),
        }

    form_repaired = [s for s in dispatched if rows[s]["form_repaired"]]
    converted = [
        s for s in dispatched if rows[s]["blend_correct"] and not rows[s]["contact0_correct"]
    ]
    converted_gold = [s for s in converted if rows[s]["gold_supplied"]]
    converted_form_only = [s for s in converted if not rows[s]["gold_supplied"]]
    repaired_still_wrong = [s for s in form_repaired if not rows[s]["blend_correct"]]

    contact0_classes = Counter(rows[s]["contact0_form"] for s in dispatched)
    final_classes = Counter(rows[s]["blend_final_form"] for s in dispatched)

    population_empty_m0 = sum(
        1
        for sample_id in carrier.sample_ids
        if a2t_read.is_empty_tool_call(carrier.m0_final_texts[sample_id])
    )
    population_empty_blend = sum(
        1
        for sample_id in carrier.sample_ids
        if a2t_read.is_empty_tool_call(carrier.blend_final_texts[sample_id])
    )

    return {
        "question": (
            "how many of the 15 changed FORM independent of correctness, and "
            "what is the correctness delta attributable to form repair alone "
            "versus to gold-bearing supply?"
        ),
        "dispatched_n": len(dispatched),
        "contact0_form_classes": dict(contact0_classes),
        "blend_final_form_classes": dict(final_classes),
        "form_repaired_n": len(form_repaired),
        "form_repaired_sample_ids": form_repaired,
        "form_repaired_but_still_wrong_n": len(repaired_still_wrong),
        "form_repaired_but_still_wrong_sample_ids": repaired_still_wrong,
        "converted_against_own_contact0_n": len(converted),
        "converted_with_gold_bearing_supply": {
            "n": len(converted_gold),
            "sample_ids": converted_gold,
            "channel": "KNOWLEDGE -- the supply named the gold tool",
        },
        "converted_without_gold_bearing_supply": {
            "n": len(converted_form_only),
            "sample_ids": converted_form_only,
            "channel": (
                "FORM -- no gold value was supplied, so the only thing the "
                "evidence contact can have done is repair the SHAPE of an "
                "answer the core already half-knew"
            ),
        },
        "empty_call_rate": {
            "m0_arm": {
                "count": population_empty_m0,
                "rate": population_empty_m0 / len(carrier.sample_ids),
            },
            "blend_arm": {
                "count": population_empty_blend,
                "rate": population_empty_blend / len(carrier.sample_ids),
            },
            "predicate": (
                "analysis.a2t_read.is_empty_tool_call, i.e. len(predicted) == 0, "
                "so unparsed answers count as empty too"
            ),
        },
        "per_sample": rows,
    }


# ---------------------------------------------------------------------------
# The K3 dispatch-rate projection
# ---------------------------------------------------------------------------


def k3_dispatch_projection(
    carrier: ccd.A2TAttempt4,
    coverage: Mapping[str, object],
    form: Mapping[str, object],
) -> dict[str, object]:
    """Project what a field-role-constrained contact-0 would do to DISPATCH.

    K3 constrains the first answer's FIELD ROLES so it is well-formed and typed.
    On this carrier the dispatch predicate fires exactly when
    ``a2t_label_normalizer`` returns ``None`` -- the answer did not parse, had no
    calls, or its PRIMARY tool name is outside the 151-entry vocabulary. A
    successful form constraint therefore removes the first two causes.

    The projection is bracketed by two LANDED measurements of the same
    trajectories rather than by an assumption:

    * UPPER bound on repair (lower bound on surviving dispatch): the BLEND arm's
      own final answers on the 15 -- the same core, the same trajectory,
      producing a well-formed call. This is optimistic about form because those
      answers were produced WITH evidence in context.
    * LOWER bound on repair (upper bound on surviving dispatch): the M0 arm's
      own single-contact answers on the same 15 ids -- the same prompt shape with
      no evidence at all, so any well-formed in-vocabulary answer there is
      attributable to decode variance rather than to any constraint."""

    rows = form["per_sample"]  # type: ignore[index]
    dispatched = sorted(coverage["dispatched_ids"])  # type: ignore[arg-type]
    population = len(carrier.sample_ids)
    flown_dispatch = len(dispatched)

    recovered_from_blend_final = [
        s for s in dispatched if rows[s]["blend_final_in_vocabulary_label"] is not None
    ]
    recovered_from_m0 = [
        s
        for s in dispatched
        if sweep.a2t_label_normalizer(
            carrier.m0_final_texts[s], carrier.inputs.label_targets
        )
        is not None
    ]
    out_of_vocabulary_at_contact0 = [
        s
        for s in dispatched
        if rows[s]["contact0_form"] == "well-formed-non-empty"
    ]

    def projection(recovered: Sequence[str], label: str) -> dict[str, object]:
        surviving = flown_dispatch - len(recovered)
        return {
            "label": label,
            "trajectories_that_would_recover_a_label": len(recovered),
            "recovered_sample_ids": list(recovered),
            "projected_dispatch_count": surviving,
            "projected_dispatch_rate": surviving / population,
            "flown_dispatch_count": flown_dispatch,
            "flown_dispatch_rate": flown_dispatch / population,
            "projected_dispatch_rate_change_pp": 100.0
            * (surviving - flown_dispatch)
            / population,
            "relative_change": (
                (surviving - flown_dispatch) / flown_dispatch
                if flown_dispatch
                else None
            ),
        }

    optimistic = projection(
        recovered_from_blend_final,
        "UPPER bound on form repair (BLEND arm's own final answers, evidence in "
        "context) -> LOWER bound on surviving dispatch",
    )
    conservative = projection(
        recovered_from_m0,
        "LOWER bound on form repair (M0 arm's own answers, no evidence) -> "
        "UPPER bound on surviving dispatch",
    )
    return {
        "question": (
            "the key-construction plan section 3 K3 requires the dispatch-rate "
            "change to be projected FIRST; if projected dispatch drops "
            "materially, K3 is an off-switch in disguise and is rejected like "
            "the E-C variant"
        ),
        "dispatch_predicate": (
            "a2t_label_normalizer returns None -- the answer did not parse, "
            "carried no calls, or its PRIMARY tool name is outside the "
            "151-entry label vocabulary. K3's form constraint removes the first "
            "two causes and leaves the third."
        ),
        "flown_dispatch_composition": {
            "empty": sum(1 for s in dispatched if rows[s]["contact0_form"] == "empty"),
            "unparsed": sum(
                1 for s in dispatched if rows[s]["contact0_form"] == "unparsed"
            ),
            "well_formed_but_out_of_vocabulary": len(out_of_vocabulary_at_contact0),
            "well_formed_but_out_of_vocabulary_sample_ids": out_of_vocabulary_at_contact0,
            "reading": (
                "only the third class survives a pure FORM constraint; the first "
                "two are exactly what a role constraint is designed to remove, "
                "and removing them removes the trajectory from the reachable set"
            ),
        },
        "projection_upper_bound_on_repair": optimistic,
        "projection_lower_bound_on_repair": conservative,
        "e_c_precedent": (
            "the rejected E-C variant forced label recovery on every sample and "
            "took evidence contacts to zero (projected 54-67/100 against 72). "
            "The plan admits K3 only because it leaves out-of-vocabulary answers "
            "out-of-vocabulary; that carve-out is measured here rather than "
            "assumed."
        ),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(*, repo_root: Path, data_root: Path, out_path: Path) -> dict[str, object]:
    attempts = audit.arm_offline_guard()
    started = time.perf_counter()

    package_file = Path(kb.__file__).resolve()
    if "speech-aware-evidence-acquisition" not in package_file.as_posix():
        raise DiagnosisError(
            f"imported rails.kb_policy from {package_file}, not this checkout"
        )

    carrier = ccd.load_a2t_attempt4(data_root=data_root, repo_root=repo_root)
    supplies, blends, direct_labels = ccd.replay_population(carrier)
    gate = ccd.fidelity_gate(carrier, supplies, blends, direct_labels)
    if not gate["gate_passed"]:
        raise DiagnosisError(
            "the pre-registered fidelity gate FAILED; no gold number is read: "
            + json.dumps(gate)
        )

    coverage = ccd.gold_coverage(carrier, supplies, blends)
    geometry, probe_report, kb_shape, cosine_cache = compute_geometry(carrier)
    ranker_check = ranker_is_cosine_ordering(carrier, cosine_cache)
    prior_sensitivity = prior_dimension_sensitivity(carrier, cosine_cache)

    split = build_versus_ranking(carrier, coverage, geometry)
    curve = reachability_curve(carrier, coverage, geometry, cosine_cache, split)
    contrast = dead_direct_contrast(carrier, coverage, geometry)

    from ..data.audio2tool import load_expected_calls
    from ..data.lock import load_lock, umbrella_lock_path

    gold_calls = load_expected_calls(
        load_lock(umbrella_lock_path(repo_root)), data_root, repo_root=repo_root
    )
    multiset = multiset_binding(carrier, coverage, gold_calls=gold_calls)
    form = form_repair_channel(carrier, coverage)
    k3 = k3_dispatch_projection(carrier, coverage, form)

    report: dict[str, object] = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "contacts": {
            "frozen_core": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "audio_seconds": 0.0,
            "gpu_hours": 0.0,
            "outbound_connection_attempts": attempts.count,
            "outbound_targets": list(attempts.targets),
            "gold_opened": (
                "SCORING-SIDE ONLY, over the EXPOSED A2T-G1-104 whose seal the "
                "landed G1 read already broke; never on a runtime path"
            ),
        },
        "frozen_cell": {
            "alpha": FROZEN_ALPHA,
            "tau": FROZEN_FUSE.tau,
            "m": FROZEN_FUSE.m,
            "c": FROZEN_FUSE.c,
            "top_l": FROZEN_FUSE.top_l,
            "top_k": FROZEN_TOP_K,
            "weights": {
                "w_cos": FROZEN_WEIGHTS.w_cos,
                "w_prior": FROZEN_WEIGHTS.w_prior,
                "w_agree": FROZEN_WEIGHTS.w_agree,
            },
            "policy_config_sha256_at_flight": sweep.FROZEN_POLICY_CONFIG_SHA256,
        },
        "artifact_hashes": dict(carrier.artifact_hashes),
        "kb_shape": kb_shape,
        "fidelity_gate": gate,
        "gold_coverage_dispatched": {
            "dispatched_n": coverage["dispatched_n"],
            "dispatched_with_gold_bearing_supply": coverage[
                "dispatched_with_gold_bearing_supply"
            ],
            "dispatched_gold_absent_from_supply": coverage[
                "dispatched_gold_absent_from_supply"
            ],
            "dispatched_gold_fused_rank_histogram": coverage[
                "dispatched_gold_fused_rank_histogram"
            ],
            "population_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE": coverage[
                "population_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE"
            ],
            "per_sample": {
                sample_id: coverage["per_sample"][sample_id]  # type: ignore[index]
                for sample_id in coverage["dispatched_ids"]  # type: ignore[union-attr]
            },
            "source": (
                "recomputed here through "
                "cross_carrier_ceiling_decomposition.gold_coverage on the same "
                "fidelity-gated replay, so the 4/11 split this row diagnoses is "
                "the same 4/11 the landed cross-carrier verdict reports"
            ),
        },
        "recall_fidelity": probe_report,
        "ranker_ordering_check": ranker_check,
        "a2t_prior_dimension_sensitivity": prior_sensitivity,
        "q1_build_versus_ranking": split,
        "q2_reachability_curve": curve,
        "q3_dead_direct_contrast": contrast,
        "q4_multiset_binding": multiset,
        "q5_form_repair_channel": form,
        "k3_dispatch_projection": k3,
        "hard_stop": (
            "DIAGNOSIS ONLY. No knob is changed, no flight is authorized, no G2 "
            "is opened, no test contact is taken, and no generality or "
            "superiority claim follows from this artifact."
        ),
    }
    report["wall_seconds"] = round(time.perf_counter() - started, 3)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report = run(
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
        out_path=Path(args.out),
    )
    print(json.dumps(report["fidelity_gate"], indent=1))
    print(json.dumps(report["q1_build_versus_ranking"], indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
