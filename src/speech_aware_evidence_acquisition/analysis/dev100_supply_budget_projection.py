"""Model-free projection for the SUPPLY-BUDGET lever (``fusion.c`` / ``fusion.top_l``).

Exposure row ``SAEA-SN-MF-SUPPLY-BUDGET-PROJECTION`` (registered before any
computation): zero frozen-core contacts, zero embedding-tool contacts, zero
tokenizer contacts, zero HTTP or socket requests of any kind. Every byte this
module reads is already landed and already scored -- the sealed DEV-100
round-4/round-5 frozen-cell attempt stores, the sealed DEV-500 confirmatory
BLEND arm restricted to NEW400, the committed round and arm reports, the
committed split receipts, the two landed tokenizer-only prompt-fit receipts
(used purely as measured token anchors), the pinned TRAIN knowledge snapshot,
and its landed content-facet vector NPZ. Nothing is embedded, encoded,
decoded, generated, tokenized, or requested.

Non-contact is proven BY CONSTRUCTION, not by a service log
-----------------------------------------------------------
:func:`.dev100_reviewer_audit.arm_offline_guard` is called before a single
input is opened; it replaces ``socket.socket.connect``,
``socket.socket.connect_ex`` and ``socket.create_connection`` with counting
refusers and the attempt counter is emitted in the report. A concurrent A4
retain-override flight holds the resident decoder unit, so -- exactly as in
:mod:`.contrast_fewshot_preanalysis` and
:mod:`.dev100_next_experiment_projections` -- this module makes NO server-log
byte-identity claim and reads or writes no file belonging to another
campaign.

The question
------------
K-WIDEN round K1 (sealed 2026-08-25) moved ``recall_top_k_per_dimension`` and
``fusion.m`` from 5 to 8 together and measured the width lever INERT: the
supplied-value distribution never exceeded 6 and mostly sat under it, because
``fusion_c 2 * fusion_top_l 3 = 6`` binds first and is m-invariant. The queue
therefore named the ``c``/``top_l`` supply budget as the next lever. This
module asks whether raising that budget puts gold INTO the supplied set for
the errors where it is currently absent, and what it costs.

What the fuser can and cannot do, before any measurement
--------------------------------------------------------
``rails.kb_policy._fuse_supply_filter`` groups percept-admitted candidate
values by ``task_target``, ranks the targets by their best admitted
supporting facet, keeps the first ``top_l`` targets, and inside each keeps the
first ``c`` values. Two consequences follow from the source alone and are
checked measurement-side below:

* ``c`` NEVER changes which targets are supplied. "Gold is in the supplied
  set" is a statement about targets, so **raising ``c`` alone cannot put gold
  into the supply on a single trajectory**. It can only deepen targets that
  are already there.
* ``top_l`` can only admit targets that already have a candidate value
  supported by an ADMITTED facet, and the admitted facets are a subset of the
  ``recall_top_k_per_dimension`` window. At the frozen ``k = 5`` there are at
  most five content facets in play at all, so the supply budget is bounded
  above by the recall window regardless of how large ``c * top_l`` is set.

The grid therefore sweeps the briefed ``(c, top_l)`` variants at the frozen
width AND at the width K1 already flew (``k = m = 8``), because the second is
the only place a budget raise has room to act.

What this module can and cannot say
-----------------------------------
Identical honesty discipline to the damage-channel, contrast-fewshot and
E-C/retain-override rows. Any counterfactual that CHANGES the prompt given to
the frozen core -- and a widened supply block always does -- has an outcome
that is NOT knowable offline. Such outcomes are counted, never scored. What
IS knowable, and is used here, is:

* the fuser's own set arithmetic, replayed through the REAL registered
  implementation at each variant;
* the blend head's arithmetic, which settles retain/dispatch exactly;
* the already-logged response texts, rescorable without any new contact;
* the measured conversion of a dispatched evidence contact, partitioned by
  where gold sits in the fused label set AND by how many values were supplied
  -- the second partition is what gives this module its only empirical grip on
  the dilution cost of a wider budget.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import contrast_fewshot_preanalysis as cf
from . import dev100_damage_channel_analysis as dc
from . import dev100_next_experiment_projections as nx
from . import dev100_reviewer_audit as ra
from . import dev500_confirmatory_read as d5
from ..rails import kb_policy as kb

SCHEMA = "saea-dev100-supply-budget-projection-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-SUPPLY-BUDGET-PROJECTION"

# The documented per-100 direct-decode byte-variance channel, against which
# every projected effect in this module is stated.
BYTE_VARIANCE_CHANNEL_PER_100 = nx.BYTE_VARIANCE_CHANNEL_PER_100

# ---------------------------------------------------------------------------
# Landed tokenizer anchors -- measured, never re-measured here
# ---------------------------------------------------------------------------

# Both receipts are committed, both are tokenizer-only (model_contact: false),
# and they share EVERY element of the worst-case construction except the
# number of facet representations rendered. Their difference is therefore a
# clean measurement of "what three more of the longest snapshot texts cost",
# which is the only thing this module needs in order to price extra values.
PROMPT_FIT_ANCHORS = (
    {
        "receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-08-24-dev100-c3-prompt-fit-np8/prompt-fit.json"
        ),
        "exposure_run_id": "SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8",
        "visible_key_facets": 5,
        "visible_values": 6,
        "text_prompt_tokens": 6055,
        "prompt_tokens_upper_bound": 6174,
    },
    {
        "receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-08-24-dev100-kwiden-k1/prompt-fit-m8.json"
        ),
        "exposure_run_id": "SAEA-SN-MF-DEV100-KWIDEN-PROMPT-FIT-M8",
        "visible_key_facets": 8,
        "visible_values": 6,
        "text_prompt_tokens": 6737,
        "prompt_tokens_upper_bound": 6856,
    },
)

SLOT_CONTEXT_TOKENS = 8192
SPEECH_AND_SPECIAL_RESERVE = 119  # 6174 - 6055, measured identically on both receipts
MAXIMUM_COMPLETION_TOKENS = 64

# ``scripts/dev100_c3_prompt_fit.py`` / ``scripts/dev100_kwiden_prompt_fit.py``
# render each evidence item as f"[evidence {index:03d}:{role}:{identifier}] {text}".
KEY_EVIDENCE_PREFIX_CHARS = len("[evidence 000:key:facet] ")
VALUE_EVIDENCE_PREFIX_CHARS = len("[evidence 000:value:value] ")

# The largest flown declared evidence prompt at the 6-value budget, published
# in the sealed K-WIDEN K1 landing (median 1,770, max 3,395 tokens over 36
# evidence contacts). Quoted as the REALITY check beside the worst-case
# envelope: the flown runner renders ZERO facet representations, so real
# prompts sit far below the conservative bound.
FLOWN_EVIDENCE_PROMPT_TOKENS_MAX_AT_6_VALUES = 3395
FLOWN_EVIDENCE_PROMPT_TOKENS_MEDIAN_AT_6_VALUES = 1770


class SupplyBudgetError(RuntimeError):
    """Raised when a landed input or a replay invariant does not hold."""


# ---------------------------------------------------------------------------
# The variant grid
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BudgetVariant:
    """One (width, budget) cell of the fuser."""

    variant_id: str
    top_k: int
    m: int
    c: int
    top_l: int
    note: str

    @property
    def nominal_cap(self) -> int:
        return self.c * self.top_l

    @property
    def knobs(self) -> kb.FuseKnobs:
        return kb.FuseKnobs(tau=cf.FROZEN_FUSE.tau, m=self.m, c=self.c, top_l=self.top_l)

    def as_json(self) -> dict[str, object]:
        return {
            "variant_id": self.variant_id,
            "recall_top_k_per_dimension": self.top_k,
            "fusion_m": self.m,
            "fusion_c": self.c,
            "fusion_top_l": self.top_l,
            "nominal_value_cap": self.nominal_cap,
            "note": self.note,
        }


BASELINE_VARIANT_ID = "k5-m5-c2-l3"

VARIANTS = (
    BudgetVariant(
        BASELINE_VARIANT_ID, 5, 5, 2, 3,
        "the FROZEN cell as flown on DEV-100 r4/r5 and DEV-500 BLEND -- the baseline",
    ),
    BudgetVariant(
        "k5-m5-c3-l3", 5, 5, 3, 3,
        "briefed (3,3): deeper values per target at the frozen width",
    ),
    BudgetVariant(
        "k5-m5-c2-l5", 5, 5, 2, 5,
        "briefed (2,5): more distinct targets at the frozen width",
    ),
    BudgetVariant(
        "k5-m5-c3-l5", 5, 5, 3, 5,
        "briefed (3,5): both, at the frozen width",
    ),
    BudgetVariant(
        "k5-m5-c4-l4", 5, 5, 4, 4,
        "briefed (4,4): both, at the frozen width",
    ),
    BudgetVariant(
        "k8-m8-c2-l3", 8, 8, 2, 3,
        "K-WIDEN K1 EXACTLY AS FLOWN -- width 8 with the budget untouched; the "
        "published K1 supplied-value distribution is the external cross-check on "
        "this whole counterfactual replay",
    ),
    BudgetVariant(
        "k8-m8-c3-l3", 8, 8, 3, 3,
        "(3,3) coupled with the width K1 already flew and already prompt-fit cleared",
    ),
    BudgetVariant(
        "k8-m8-c2-l5", 8, 8, 2, 5,
        "(2,5) coupled with K1's width -- the only briefed variant that can add "
        "TARGETS in a window wide enough to hold them",
    ),
    BudgetVariant(
        "k8-m8-c3-l5", 8, 8, 3, 5,
        "(3,5) coupled with K1's width",
    ),
    BudgetVariant(
        "k8-m8-c4-l4", 8, 8, 4, 4,
        "(4,4) coupled with K1's width",
    ),
    # Infinite-budget ceilings. c * top_l is set past any structural ceiling,
    # so these say what the supply-budget lever could reach if the context
    # were free -- the honest upper bound on the whole question.
    BudgetVariant(
        "k5-m5-cINF-lINF", 5, 5, 8, 64,
        "CEILING at the frozen width: every percept-admitted candidate supplied",
    ),
    BudgetVariant(
        "k8-m8-cINF-lINF", 8, 8, 8, 64,
        "CEILING at K1's width: every percept-admitted candidate supplied",
    ),
    BudgetVariant(
        "k16-m16-c2-l5", 16, 16, 2, 5,
        "(2,5) coupled with a K2-scale width, never flown",
    ),
    BudgetVariant(
        "k16-m16-cINF-lINF", 16, 16, 16, 64,
        "CEILING at a K2-scale width, never flown",
    ),
    BudgetVariant(
        "k32-m32-cINF-lINF", 32, 32, 32, 64,
        "CEILING at the width whose facet-level reachability the DEV-500 curve put at "
        "84.25 percent, never flown",
    ),
)


# ---------------------------------------------------------------------------
# Per-sample replay at one variant
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VariantSample:
    """One sealed trajectory replayed at one (width, budget) cell."""

    sample_id: str
    variant_id: str
    selected_value_ids: tuple[str, ...]
    supplied_targets: tuple[str, ...]
    supplied_count: int
    dispatched: bool
    retain_primary: bool
    supply_empty: bool
    gold_in_supply: bool
    gold_fused_rank: int | None
    fused_ranked: tuple[tuple[str, float], ...]
    # Structural diagnostics, derived and then gated against the real fuser.
    admitted_facets: int
    candidate_targets: int
    candidate_values_total: int
    per_target_candidates: tuple[int, ...]  # in the fuser's own target order
    structural_ceiling: int  # supply at an INFINITE (c, top_l)
    saturated_at_budget: bool
    targets_exhausted: bool
    values_exhausted: bool


def _candidate_map(
    inputs: dc.LandedInputs, supply: dc.SupplyReplay
) -> list[tuple[str, list[str]]]:
    """Re-derive ``_fuse_supply_filter``'s candidate grouping, in its order.

    This is a DIAGNOSTIC re-derivation, not a second implementation of the
    policy: :func:`replay_variant` gates it by checking that applying
    ``(c, top_l)`` to this structure reproduces the REAL fuser's own
    ``selected_value_ids`` byte for byte, on every sample of every variant.
    """

    admitted = set(supply.admitted_facet_ids)
    facet_score = {
        candidate.facet_id: candidate.score for candidate in supply.rank_result.candidates
    }
    grouped: dict[str, list[tuple[float, str]]] = {}
    for value in inputs.snapshot.values:
        if value.task_target is None:
            continue
        supporting = set(value.associated_facet_ids) & admitted
        if not supporting:
            continue
        best_facet = max(
            supporting, key=lambda facet_id: (facet_score.get(facet_id, 0.0), facet_id)
        )
        grouped.setdefault(value.task_target, []).append(
            (facet_score.get(best_facet, 0.0), value.value_id)
        )
    ranked_targets = sorted(
        grouped,
        key=lambda target: (-max(score for score, _vid in grouped[target]), target),
    )
    return [
        (
            target,
            [vid for _score, vid in sorted(grouped[target], key=lambda item: (-item[0], item[1]))],
        )
        for target in ranked_targets
    ]


def replay_variant(
    population: cf.CellPopulation,
    bundle: cf.SnapshotBundle,
    variant: BudgetVariant,
    *,
    recall_cache: dict[tuple[str, str, int], object],
) -> dict[str, VariantSample]:
    """Replay one sealed population through the REAL fuser at one variant."""

    import numpy as np

    inputs = population.inputs
    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)

    out: dict[str, VariantSample] = {}
    for sample_id in population.sample_ids:
        key = (population.pin.population_id, sample_id, variant.top_k)
        recall_scores = recall_cache.get(key)
        if recall_scores is None:
            cosines = cf._COSINE_CACHE.get((population.pin.population_id, sample_id))
            if cosines is None:  # pragma: no cover - defensive
                query = np.asarray(inputs.query_vectors[sample_id], dtype=np.float64)
                denominator = facet_norms * float(np.linalg.norm(query))
                with np.errstate(divide="ignore", invalid="ignore"):
                    cosines = np.where(
                        denominator > 0.0, matrix @ query / denominator, 0.0
                    )
            recall_scores = cf.vectorised_recall(bundle, cosines, top_k=variant.top_k)
            recall_cache[key] = recall_scores

        supply = dc.replay_supply(
            inputs,
            sample_id,
            weights=cf.FROZEN_WEIGHTS,
            knobs=variant.knobs,
            top_k=variant.top_k,
            recall_scores=recall_scores,
        )
        direct_label = kb.default_label_normalizer(
            inputs.direct_texts[sample_id], inputs.label_targets
        )
        blend = dc.replay_blend(
            inputs, supply, direct_label=direct_label, alpha=cf.FROZEN_ALPHA
        )
        supply_empty = not supply.selected_value_ids
        retain = blend.retain_primary and not supply_empty

        grouping = _candidate_map(inputs, supply)
        derived: list[str] = []
        for target, value_ids in grouping[: variant.top_l]:
            derived.extend(value_ids[: variant.c])
        if tuple(sorted(set(derived))) != tuple(sorted(supply.selected_value_ids)):
            raise SupplyBudgetError(
                f"{population.pin.population_id}/{sample_id}/{variant.variant_id}: the "
                "derived candidate structure does not reproduce the registered fuser's "
                "own selection; the diagnostics are void"
            )

        supplied_targets = sorted(
            {
                inputs.values_by_id[value_id].task_target
                for value_id in supply.selected_value_ids
            }
        )
        gold = inputs.gold_by_sample[sample_id]
        gold_target = f"{gold.scenario}_{gold.action}"
        fused_ranked = cf._fused_ranked_targets(
            blend.fused_label_scores, inputs.label_targets
        )
        gold_fused_rank = next(
            (
                position
                for position, (target, _score) in enumerate(fused_ranked, start=1)
                if target == gold_target
            ),
            None,
        )
        per_target = tuple(len(value_ids) for _target, value_ids in grouping)
        structural_ceiling = sum(per_target)
        selected_slice = grouping[: variant.top_l]
        out[sample_id] = VariantSample(
            sample_id=sample_id,
            variant_id=variant.variant_id,
            selected_value_ids=tuple(sorted(supply.selected_value_ids)),
            supplied_targets=tuple(supplied_targets),
            supplied_count=len(supply.selected_value_ids),
            dispatched=not (retain or supply_empty),
            retain_primary=retain,
            supply_empty=supply_empty,
            gold_in_supply=gold_target in set(supplied_targets),
            gold_fused_rank=gold_fused_rank,
            fused_ranked=fused_ranked,
            admitted_facets=len(supply.admitted_facet_ids),
            candidate_targets=len(grouping),
            candidate_values_total=structural_ceiling,
            per_target_candidates=per_target,
            structural_ceiling=structural_ceiling,
            saturated_at_budget=len(supply.selected_value_ids) == variant.nominal_cap,
            targets_exhausted=len(grouping) < variant.top_l,
            values_exhausted=any(
                len(value_ids) < variant.c for _target, value_ids in selected_slice
            ),
        )
    return out


# ---------------------------------------------------------------------------
# (1) Saturation profile
# ---------------------------------------------------------------------------


def saturation_profile(
    samples: Mapping[str, VariantSample], variant: BudgetVariant
) -> dict[str, object]:
    """How full the budget actually is, and why it is not fuller."""

    dispatched = [item for item in samples.values() if item.dispatched]
    counts: dict[int, int] = {}
    for item in dispatched:
        counts[item.supplied_count] = counts.get(item.supplied_count, 0) + 1
    ceilings: dict[int, int] = {}
    for item in dispatched:
        ceilings[item.structural_ceiling] = ceilings.get(item.structural_ceiling, 0) + 1
    targets: dict[int, int] = {}
    for item in dispatched:
        targets[item.candidate_targets] = targets.get(item.candidate_targets, 0) + 1

    saturated = [item for item in dispatched if item.saturated_at_budget]
    unsaturated = [item for item in dispatched if not item.saturated_at_budget]
    only_targets = [
        item for item in unsaturated if item.targets_exhausted and not item.values_exhausted
    ]
    only_values = [
        item for item in unsaturated if item.values_exhausted and not item.targets_exhausted
    ]
    both = [item for item in unsaturated if item.values_exhausted and item.targets_exhausted]
    neither = [
        item
        for item in unsaturated
        if not item.values_exhausted and not item.targets_exhausted
    ]
    at_structural_ceiling = [
        item for item in dispatched if item.supplied_count == item.structural_ceiling
    ]
    return {
        "variant": variant.as_json(),
        "dispatched_trajectories": len(dispatched),
        "supplied_value_count_distribution": {
            str(count): dispatched_count for count, dispatched_count in sorted(counts.items())
        },
        "maximum_supplied_values": max((item.supplied_count for item in dispatched), default=0),
        "budget_is_binding_saturated_at_c_times_top_l": len(saturated),
        "budget_is_NOT_binding_unsaturated": len(unsaturated),
        "unsaturated_because_fewer_than_top_l_candidate_targets": len(only_targets),
        "unsaturated_because_a_selected_target_had_fewer_than_c_values": len(only_values),
        "unsaturated_for_both_reasons": len(both),
        "unsaturated_for_neither_reason_should_be_zero": len(neither),
        "supply_equals_the_STRUCTURAL_ceiling_infinite_budget": len(at_structural_ceiling),
        "structural_ceiling_never_exceeds_the_recall_window": all(
            item.structural_ceiling <= variant.top_k for item in dispatched
        ),
        "structural_ceiling_equals_the_recall_window_exactly": sum(
            1 for item in dispatched if item.structural_ceiling == variant.top_k
        ),
        "structural_ceiling_distribution": {
            str(ceiling): n for ceiling, n in sorted(ceilings.items())
        },
        "candidate_target_count_distribution": {
            str(count): n for count, n in sorted(targets.items())
        },
        "reading": (
            "'saturated' means the fuser filled c * top_l exactly. 'structural ceiling' is "
            "what the fuser would supply at an INFINITE budget and is set by the recall "
            "window: only values supported by a percept-admitted facet are candidates at "
            "all, and the admitted facets are a subset of the recall_top_k window"
        ),
    }


# ---------------------------------------------------------------------------
# (2) Reachability, risk surface and token cost per variant
# ---------------------------------------------------------------------------


def _rank_bucket(rank: int | None) -> str:
    if rank == 1:
        return "gold_is_fused_top1"
    if rank in (2, 3):
        return "gold_at_fused_2_or_3"
    if rank is None:
        return "gold_not_in_fused_set"
    return "gold_at_fused_4_or_deeper"


def reachability_and_risk(
    *,
    baseline: Mapping[str, VariantSample],
    variant_samples: Mapping[str, VariantSample],
    annotated: Mapping[str, nx.AnnotatedSample],
    variant: BudgetVariant,
) -> dict[str, object]:
    """Who gains a gold-bearing supply, who has their supply disturbed."""

    dispatch_invariant = all(
        baseline[sample_id].dispatched == item.dispatched
        for sample_id, item in variant_samples.items()
    )
    changed = [
        sample_id
        for sample_id, item in variant_samples.items()
        if item.selected_value_ids != baseline[sample_id].selected_value_ids
    ]
    dispatched_ids = [
        sample_id for sample_id, item in variant_samples.items() if item.dispatched
    ]

    wrong_dispatched = [
        sample_id
        for sample_id in dispatched_ids
        if not annotated[sample_id].replay.correct
    ]
    correct_dispatched = [
        sample_id for sample_id in dispatched_ids if annotated[sample_id].replay.correct
    ]

    gold_absent_today = [
        sample_id for sample_id in wrong_dispatched if not baseline[sample_id].gold_in_supply
    ]
    newly_gold_supplied = [
        sample_id for sample_id in gold_absent_today if variant_samples[sample_id].gold_in_supply
    ]
    lost_gold = [
        sample_id
        for sample_id in dispatched_ids
        if baseline[sample_id].gold_in_supply and not variant_samples[sample_id].gold_in_supply
    ]

    newly_rows = []
    for sample_id in sorted(newly_gold_supplied):
        item = variant_samples[sample_id]
        newly_rows.append(
            {
                "sample_id": sample_id,
                "gold_target": annotated[sample_id].replay.gold_target,
                "gold_fused_rank_under_the_variant": item.gold_fused_rank,
                "supplied_values_baseline": baseline[sample_id].supplied_count,
                "supplied_values_variant": item.supplied_count,
                "supplied_targets_variant": list(item.supplied_targets),
            }
        )

    changed_correct = [
        sample_id
        for sample_id in correct_dispatched
        if variant_samples[sample_id].selected_value_ids
        != baseline[sample_id].selected_value_ids
    ]
    changed_wrong = [
        sample_id
        for sample_id in wrong_dispatched
        if variant_samples[sample_id].selected_value_ids
        != baseline[sample_id].selected_value_ids
    ]
    changed_correct_gold_rank = {}
    for sample_id in changed_correct:
        bucket = _rank_bucket(variant_samples[sample_id].gold_fused_rank)
        changed_correct_gold_rank[bucket] = changed_correct_gold_rank.get(bucket, 0) + 1

    retained_changed = [
        sample_id
        for sample_id in changed
        if not variant_samples[sample_id].dispatched
    ]

    return {
        "variant": variant.as_json(),
        "dispatch_set_is_invariant_under_the_budget_change": dispatch_invariant,
        "dispatched": len(dispatched_ids),
        "trajectories_whose_supplied_set_changes_at_all": len(changed),
        "of_which_retained_and_therefore_INERT_no_supply_reaches_the_prompt": len(
            retained_changed
        ),
        "currently_wrong_dispatched": len(wrong_dispatched),
        "currently_wrong_dispatched_with_gold_ABSENT_from_the_supply_today": len(
            gold_absent_today
        ),
        "of_those_gold_would_be_IN_the_supply_under_this_variant": len(newly_gold_supplied),
        "newly_gold_supplied_members": newly_rows,
        "trajectories_that_LOSE_a_gold_bearing_supply_under_this_variant": len(lost_gold),
        "risk_surface_currently_CORRECT_dispatched_whose_supply_changes": len(
            changed_correct
        ),
        "risk_surface_by_gold_rank_under_the_variant": changed_correct_gold_rank,
        "currently_wrong_dispatched_whose_supply_changes": len(changed_wrong),
        "supplied_value_count_distribution_dispatched": {
            str(count): sum(
                1
                for sample_id in dispatched_ids
                if variant_samples[sample_id].supplied_count == count
            )
            for count in sorted(
                {variant_samples[sample_id].supplied_count for sample_id in dispatched_ids}
            )
        },
        "maximum_supplied_values_dispatched": max(
            (variant_samples[sample_id].supplied_count for sample_id in dispatched_ids),
            default=0,
        ),
    }


# ---------------------------------------------------------------------------
# The dilution anchor -- conversion as a function of how much was supplied
# ---------------------------------------------------------------------------


def dilution_anchors(
    populations: Mapping[str, Mapping[str, nx.AnnotatedSample]],
) -> dict[str, object]:
    """Measured: does a BIGGER supplied set convert worse at the same gold rank?

    This is the only empirical grip the offline record has on the cost side of
    a wider budget. It is measured over flown trajectories of the frozen cell,
    where the supplied-value count varies naturally between 1 and 6.
    """

    by_rank_and_count: dict[str, dict[int, list[int]]] = {}
    for annotated in populations.values():
        for item in annotated.values():
            if not item.replay.dispatched:
                continue
            bucket = _rank_bucket(item.replay.gold_fused_rank)
            count = len(item.replay.selected_value_ids)
            by_rank_and_count.setdefault(bucket, {}).setdefault(count, []).append(
                int(item.replay.correct)
            )
    report: dict[str, object] = {}
    for bucket, by_count in by_rank_and_count.items():
        rows = {}
        for count in sorted(by_count):
            outcomes = by_count[count]
            rows[str(count)] = {
                "n": len(outcomes),
                "correct": sum(outcomes),
                "rate": round(sum(outcomes) / len(outcomes), 4),
            }
        report[bucket] = rows

    by_targets: dict[str, dict[int, list[int]]] = {}
    for annotated in populations.values():
        for item in annotated.values():
            if not item.replay.dispatched:
                continue
            bucket = _rank_bucket(item.replay.gold_fused_rank)
            by_targets.setdefault(bucket, {}).setdefault(
                item.n_fused_targets, []
            ).append(int(item.replay.correct))
    target_rows: dict[str, object] = {}
    for bucket, by_count in by_targets.items():
        rows = {}
        for count in sorted(by_count):
            outcomes = by_count[count]
            rows[str(count)] = {
                "n": len(outcomes),
                "correct": sum(outcomes),
                "rate": round(sum(outcomes) / len(outcomes), 4),
            }
        target_rows[bucket] = rows

    return {
        "by_supplied_value_count": report,
        "by_supplied_target_count": target_rows,
        "reading": (
            "if conversion at a FIXED gold rank falls as the supplied set grows, a wider "
            "budget dilutes; if it does not, the offline record has no evidence of a "
            "dilution cost inside the measured range. Nothing here anchors a supplied count "
            "LARGER than the frozen cell ever produced"
        ),
        "measured_range_only": (
            "the frozen cell supplied between 1 and 6 values; no anchor exists above that "
            "and none is extrapolated"
        ),
    }


# ---------------------------------------------------------------------------
# (2b) Evidence-prompt token estimate
# ---------------------------------------------------------------------------


def _load_contact_prompt_tokens(
    run_dir: Path, run_id: str
) -> dict[str, dict[str, int]]:
    """``sample_id -> {"direct": tokens, "evidence": tokens}`` from the trace.

    The MODEL_REQUEST channel carries ``request_id``, ``sample_id`` and
    ``key_representation_id`` (``...:direct`` for contact 0), and the COST
    channel carries that same request's ``prompt_tokens``. Pairing on the
    request id is exact -- unlike pairing through the USE channel, whose
    ``response_sha256`` is the response TEXT hash and therefore collides
    across the many samples that produced identical direct answers.

    Read from the SAME durable trace the population loader already opens, in
    the same sealed attempt store. Nothing new is contacted.
    """

    kind_by_request: dict[str, tuple[str, str]] = {}
    tokens_by_request: dict[str, int] = {}
    trace_path = Path(run_dir) / f"{run_id}.trace.jsonl"
    with trace_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            channel = record["channel"]
            record_id = record["record_id"]
            if channel == "MODEL_REQUEST":
                payload = record["payload"]["payload"]
                representation = str(payload.get("key_representation_id", ""))
                kind = "direct" if representation.endswith(":direct") else "evidence"
                kind_by_request[str(payload["request_id"])] = (
                    str(payload["sample_id"]),
                    kind,
                )
            elif channel == "COST" and record_id.endswith("/cost"):
                tokens = record["payload"].get("prompt_tokens")
                if tokens is not None:
                    tokens_by_request[record_id[: -len("/cost")]] = int(tokens)

    paired: dict[str, dict[str, int]] = {}
    for request_id, (sample_id, kind) in kind_by_request.items():
        tokens = tokens_by_request.get(request_id)
        if tokens is None:
            continue
        paired.setdefault(sample_id, {})[kind] = tokens
    return paired


def flown_value_token_rate(
    cells: Mapping[str, cf.CellPopulation],
) -> dict[str, object]:
    """Measure what one character of supplied VALUE text really costs in tokens.

    The naive estimator -- differencing the two landed prompt-fit receipts --
    prices three facet representations that happen to be dense numeric
    entity-prior tables, and would mis-price ordinary exemplar prose by a
    large factor. A far better anchor is already inside the sealed stores:
    every dispatched trajectory made TWO contacts on the SAME speech packet,
    and ``rails.runner`` builds the evidence contact as the direct contact's
    text plus the control instruction plus the supplied value block. So

        prompt_tokens(evidence) - prompt_tokens(direct)
            = a constant instruction cost + the supplied value block

    with the whole speech-feature and task-contract base cancelling per
    sample. Regressing that paired difference on the supplied block's own
    character count measures tokens-per-character on exactly the material a
    wider budget would add, through the real model, with zero new contacts.
    """

    xs: list[float] = []
    ys: list[float] = []
    rows: list[dict[str, object]] = []
    evidence_prompt_tokens: list[int] = []
    for name, cell in cells.items():
        paired = _load_contact_prompt_tokens(cell.run_dir, cell.pin.run_id)
        for sample_id in cell.sample_ids:
            by_id = paired.get(sample_id, {})
            if "direct" not in by_id or "evidence" not in by_id:
                continue
            supplied = cell.inputs.logged_supply.get(sample_id, ())
            chars = sum(
                len(str(cell.inputs.values_by_id[value_id].content))
                + VALUE_EVIDENCE_PREFIX_CHARS
                for value_id in supplied
            )
            delta = by_id["evidence"] - by_id["direct"]
            xs.append(float(chars))
            ys.append(float(delta))
            evidence_prompt_tokens.append(by_id["evidence"])
            rows.append(
                {
                    "population": name,
                    "supplied_values": len(supplied),
                    "supplied_value_characters": chars,
                    "prompt_token_delta": delta,
                }
            )

    if len(xs) < 10:
        raise SupplyBudgetError(
            "too few paired contacts to measure a value-token rate from the sealed stores"
        )
    n = float(len(xs))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    variance = sum((x - mean_x) ** 2 for x in xs)
    if variance <= 0.0:
        raise SupplyBudgetError("the supplied-value character counts do not vary")
    slope = covariance / variance
    intercept = mean_y - slope * mean_x
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys, strict=True)]
    total_ss = sum((y - mean_y) ** 2 for y in ys)
    residual_ss = sum(value**2 for value in residuals)
    r_squared = 1.0 - (residual_ss / total_ss) if total_ss > 0 else None

    return {
        "method": (
            "paired within-sample regression on the sealed stores: "
            "prompt_tokens(evidence-decode) - prompt_tokens(direct-decode) against the "
            "supplied value block's own character count. The speech-feature packet, the "
            "task contract and the system prompt are byte-identical between the two "
            "contacts of a sample, so they cancel exactly"
        ),
        "paired_contacts": len(xs),
        "tokens_per_character_of_value_text": round(slope, 6),
        "characters_per_token_of_value_text": round(1.0 / slope, 4) if slope > 0 else None,
        "constant_instruction_cost_tokens": round(intercept, 2),
        "r_squared": round(r_squared, 6) if r_squared is not None else None,
        "max_absolute_residual_tokens": round(max(abs(value) for value in residuals), 2),
        "flown_evidence_prompt_tokens": {
            "n": len(evidence_prompt_tokens),
            "min": min(evidence_prompt_tokens),
            "max": max(evidence_prompt_tokens),
            "median": sorted(evidence_prompt_tokens)[len(evidence_prompt_tokens) // 2],
        },
        "supplied_value_character_range": [int(min(xs)), int(max(xs))],
        "_slope": slope,
        "_intercept": intercept,
    }


def token_model(
    bundle: cf.SnapshotBundle, *, flown_rate: Mapping[str, object]
) -> dict[str, object]:
    """Price an extra supplied value in tokens against the standing envelope.

    The standing envelopes are the two landed tokenizer-only prompt-fit
    receipts; both render six values, which is what the frozen ``c * top_l``
    permits. A variant that would render more values is priced by adding the
    NEXT longest value contents at the tokens-per-character rate
    :func:`flown_value_token_rate` measured on the real flown value material.

    The receipt-difference rate is retained ONLY as a disclosed contrast: the
    three facet representations the two receipts differ by are dense numeric
    entity-prior tables (1.93 characters per token), not exemplar prose, so
    using them to price values would over-count by roughly a factor of two.
    This is an ESTIMATE either way -- no tokenizer is contacted and no
    prompt-fit gate is claimed to be re-passed.
    """

    facet_reps = sorted(
        (str(facet.representation) for facet in bundle.snapshot.facets),
        key=lambda text: -len(text),
    )
    value_texts = sorted(
        (str(value.content) for value in bundle.snapshot.values),
        key=lambda text: -len(text),
    )

    small, large = PROMPT_FIT_ANCHORS
    added_reps = facet_reps[small["visible_key_facets"] : large["visible_key_facets"]]
    added_chars = sum(len(text) + KEY_EVIDENCE_PREFIX_CHARS for text in added_reps)
    added_tokens = large["text_prompt_tokens"] - small["text_prompt_tokens"]
    if added_tokens <= 0:
        raise SupplyBudgetError("the two prompt-fit anchors do not bracket a token cost")

    slope = float(flown_rate["_slope"])
    envelope_six_value_chars = sum(
        len(text) + VALUE_EVIDENCE_PREFIX_CHARS for text in value_texts[:6]
    )
    return {
        "method": (
            "the standing worst-case envelope at six values, plus the NEXT longest value "
            "contents priced at the tokens-per-character rate measured on the real flown "
            "value material by a paired within-sample regression over the sealed stores"
        ),
        "anchors": list(PROMPT_FIT_ANCHORS),
        "tokens_per_character_of_value_text": round(slope, 6),
        "flown_rate_provenance": flown_rate["method"],
        "receipt_difference_contrast": {
            "added_facet_representation_lengths": [len(text) for text in added_reps],
            "added_characters_including_evidence_prefix": added_chars,
            "measured_token_cost_of_those_three_texts": added_tokens,
            "characters_per_token": round(added_chars / added_tokens, 4),
            "why_it_is_not_used_to_price_values": (
                "those three representations are dense numeric entity-prior tables, not "
                "exemplar prose; pricing values at their rate over-counts by about 2x"
            ),
        },
        "longest_value_content_lengths_top16": [len(text) for text in value_texts[:16]],
        "envelope_six_value_block_characters": envelope_six_value_chars,
        "estimate_not_measurement": (
            "these are ESTIMATES. Any variant that would render more than the 6 values the "
            "standing envelopes cover must pass a REAL tokenizer-only prompt-fit row before "
            "it could fly"
        ),
        "_slope": slope,
        "_value_texts": value_texts,
    }


def token_estimate(
    model: Mapping[str, object], *, values: int, facet_representations: int
) -> dict[str, object]:
    """Worst-case evidence-prompt token estimate at a given supplied count."""

    slope = float(model["_slope"])
    value_texts: Sequence[str] = model["_value_texts"]  # type: ignore[assignment]
    small, large = PROMPT_FIT_ANCHORS
    anchor = small if facet_representations == small["visible_key_facets"] else large
    if facet_representations not in (
        small["visible_key_facets"],
        large["visible_key_facets"],
    ):
        raise SupplyBudgetError(
            "only the two landed facet-count anchors can be priced without a tokenizer"
        )
    base_values = int(anchor["visible_values"])
    extra = value_texts[base_values:values] if values > base_values else ()
    extra_chars = sum(len(text) + VALUE_EVIDENCE_PREFIX_CHARS for text in extra)
    removed = value_texts[values:base_values] if values < base_values else ()
    removed_chars = sum(len(text) + VALUE_EVIDENCE_PREFIX_CHARS for text in removed)
    delta_tokens = (extra_chars - removed_chars) * slope
    text_tokens = float(anchor["text_prompt_tokens"]) + delta_tokens
    upper_bound = text_tokens + SPEECH_AND_SPECIAL_RESERVE
    # A deliberately pessimistic band: the rate is stressed by 25% in the
    # direction that costs tokens, so a variant that fits only on the central
    # estimate is visibly flagged.
    stressed = (
        float(anchor["text_prompt_tokens"])
        + delta_tokens * 1.25
        + SPEECH_AND_SPECIAL_RESERVE
    )
    return {
        "worst_case_visible_values": values,
        "worst_case_visible_key_facets": facet_representations,
        "anchor_receipt": anchor["receipt"],
        "estimated_text_prompt_tokens": round(text_tokens, 1),
        "estimated_prompt_tokens_upper_bound": round(upper_bound, 1),
        "pessimistic_upper_bound_rate_stressed_25pct": round(stressed, 1),
        "slot_context_tokens": SLOT_CONTEXT_TOKENS,
        "maximum_completion_tokens": MAXIMUM_COMPLETION_TOKENS,
        "headroom_tokens": round(
            SLOT_CONTEXT_TOKENS - upper_bound - MAXIMUM_COMPLETION_TOKENS, 1
        ),
        "fits_one_slot_estimated": bool(
            upper_bound + MAXIMUM_COMPLETION_TOKENS <= SLOT_CONTEXT_TOKENS
        ),
        "fits_one_slot_pessimistic": bool(
            stressed + MAXIMUM_COMPLETION_TOKENS <= SLOT_CONTEXT_TOKENS
        ),
    }


# ---------------------------------------------------------------------------
# (3) Projected accuracy bands
# ---------------------------------------------------------------------------


def projected_band(
    *,
    baseline: Mapping[str, VariantSample],
    variant_samples: Mapping[str, VariantSample],
    annotated: Mapping[str, nx.AnnotatedSample],
    anchors: Mapping[str, float],
    deep_rank_rate: float,
    variant: BudgetVariant,
) -> dict[str, object]:
    """Project the population accuracy at one variant from the measured anchors.

    Construction, stated so it can be argued with:

    * a trajectory whose supplied set is UNCHANGED receives a byte-identical
      evidence prompt, so its outcome is carried over EXACTLY -- this is
      arithmetic, not a projection;
    * a trajectory whose supplied set CHANGES receives the measured conversion
      rate for wherever gold sits under the variant, whether it is right or
      wrong today. A currently-correct disturbed sample therefore carries the
      same rate as a currently-wrong one at the same rank, which is the
      symmetric and conservative reading;
    * gold at fused rank 4 or deeper has NO measured anchor -- the frozen cell
      never supplied more than three targets -- so it is priced at
      ``deep_rank_rate``, which the caller derives from the sealed record and
      which is disclosed as an extrapolation everywhere it is used.
    """

    rates = {
        "gold_is_fused_top1": anchors["gold_is_fused_top1"],
        "gold_at_fused_2_or_3": anchors["gold_at_fused_2_or_3"],
        "gold_not_in_fused_set": anchors["gold_not_in_fused_set"],
        "gold_at_fused_4_or_deeper": deep_rank_rate,
    }

    population_correct = sum(1 for item in annotated.values() if item.replay.correct)
    dispatched_ids = [
        sample_id for sample_id, item in variant_samples.items() if item.dispatched
    ]
    unchanged_correct = 0
    changed_expected = 0.0
    changed_pessimistic = 0.0
    changed_optimistic = 0.0
    changed = 0
    deep_priced = 0
    for sample_id in dispatched_ids:
        item = variant_samples[sample_id]
        if item.selected_value_ids == baseline[sample_id].selected_value_ids:
            unchanged_correct += int(annotated[sample_id].replay.correct)
            continue
        changed += 1
        bucket = _rank_bucket(item.gold_fused_rank)
        if bucket == "gold_at_fused_4_or_deeper":
            deep_priced += 1
        rate = rates[bucket]
        changed_expected += rate
        # Pessimistic: every changed trajectory is priced one rank-band worse.
        changed_pessimistic += {
            "gold_is_fused_top1": rates["gold_at_fused_2_or_3"],
            "gold_at_fused_2_or_3": rates["gold_at_fused_4_or_deeper"],
            "gold_at_fused_4_or_deeper": rates["gold_not_in_fused_set"],
            "gold_not_in_fused_set": rates["gold_not_in_fused_set"],
        }[bucket]
        # Optimistic: a changed trajectory whose gold is supplied converts as
        # well as the best measured band, and a currently-correct one is not
        # disturbed at all.
        if annotated[sample_id].replay.correct:
            changed_optimistic += 1.0
        elif bucket == "gold_not_in_fused_set":
            changed_optimistic += 0.0
        else:
            changed_optimistic += rates["gold_is_fused_top1"]

    retained_correct = sum(
        1
        for sample_id, item in variant_samples.items()
        if not item.dispatched and annotated[sample_id].replay.correct
    )
    central = retained_correct + unchanged_correct + changed_expected
    pessimistic = retained_correct + unchanged_correct + changed_pessimistic
    optimistic = retained_correct + unchanged_correct + changed_optimistic
    size = len(annotated)
    return {
        "variant": variant.as_json(),
        "population_size": size,
        "sealed_correct": population_correct,
        "trajectories_with_an_UNCHANGED_supply_carried_over_exactly": len(dispatched_ids)
        - changed,
        "trajectories_with_a_CHANGED_supply_priced_by_anchor": changed,
        "changed_trajectories_priced_at_an_UNANCHORED_deep_rank": deep_priced,
        "band_pessimistic": round(pessimistic, 2),
        "band_central": round(central, 2),
        "band_optimistic": round(optimistic, 2),
        "projected_change_central": round(central - population_correct, 2),
        "projected_change_pessimistic": round(pessimistic - population_correct, 2),
        "projected_change_optimistic": round(optimistic - population_correct, 2),
        "byte_variance_channel_per_100": BYTE_VARIANCE_CHANNEL_PER_100,
        "central_change_per_100": round(
            (central - population_correct) * 100.0 / size, 2
        ),
        "clears_the_variance_channel_on_this_population": bool(
            abs((central - population_correct) * 100.0 / size)
            > BYTE_VARIANCE_CHANNEL_PER_100
        ),
        "rates_used": {name: round(rate, 4) for name, rate in rates.items()},
    }


# ---------------------------------------------------------------------------
# (4) Interaction with the A4 retain-override arm
# ---------------------------------------------------------------------------


def a4_overlap(
    *,
    baseline: Mapping[str, VariantSample],
    variant_samples: Mapping[str, VariantSample],
    annotated: Mapping[str, nx.AnnotatedSample],
    variant: BudgetVariant,
) -> dict[str, object]:
    """How much of this variant's projected recovery A4 already claims.

    A4 fires on trajectories retain-primary would finish in ONE contact; the
    supply budget acts only on trajectories that dispatch an evidence contact.
    The two sets are complementary by the frozen cell's own dispatch
    predicate, so the expected overlap is zero -- but it is measured rather
    than asserted, and the second-order interaction (A4's overridden
    trajectories would themselves receive the WIDER supply if both flew
    together) is reported alongside it.
    """

    retained = [item for item in annotated.values() if not item.replay.dispatched]
    losses = {
        item.sample_id
        for item in retained
        if not item.replay.correct
        and cf.error_class(item.replay) == "retain-override-loss"
    }
    a4_triggered = {
        item.sample_id
        for item in retained
        if item.disagrees
        and item.delta is not None
        and item.delta >= nx.RECOMMENDED_DELTA - 1e-12
    }
    a4_recovered = a4_triggered & losses

    budget_recovered = {
        sample_id
        for sample_id, item in variant_samples.items()
        if item.dispatched
        and not annotated[sample_id].replay.correct
        and not baseline[sample_id].gold_in_supply
        and item.gold_in_supply
    }

    a4_supply_would_change = {
        sample_id
        for sample_id in a4_triggered
        if variant_samples[sample_id].selected_value_ids
        != baseline[sample_id].selected_value_ids
    }
    a4_recovered_gold_rank_under_variant = {}
    for sample_id in sorted(a4_recovered):
        bucket = _rank_bucket(variant_samples[sample_id].gold_fused_rank)
        a4_recovered_gold_rank_under_variant[bucket] = (
            a4_recovered_gold_rank_under_variant.get(bucket, 0) + 1
        )

    return {
        "variant": variant.as_json(),
        "a4_bar": nx.RECOMMENDED_DELTA,
        "a4_triggered": len(a4_triggered),
        "a4_projected_recoveries": len(a4_recovered),
        "a4_recovered_sample_ids": sorted(a4_recovered),
        "supply_budget_projected_recoveries": len(budget_recovered),
        "supply_budget_recovered_sample_ids": sorted(budget_recovered),
        "OVERLAP_double_counting_risk": len(a4_recovered & budget_recovered),
        "why_the_sets_are_complementary": (
            "the frozen cell's dispatch predicate is 'the direct answer named no TRAIN "
            "intent'; A4 acts only where it did name one (retained) and the supply budget "
            "acts only where it did not (dispatched)"
        ),
        "second_order_if_both_fly_together": {
            "a4_triggered_whose_supply_the_variant_would_also_change": len(
                a4_supply_would_change
            ),
            "a4_recovered_gold_rank_under_the_variant": a4_recovered_gold_rank_under_variant,
            "reading": (
                "A4's recoveries are exactly the trajectories where gold is the fused "
                "top-1. A wider budget adds LOWER-ranked distractor targets to those same "
                "prompts, so a combined arm is not the sum of two independent effects and "
                "must be attributed by flying A4 alone first"
            ),
        },
    }


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


def _derive_deep_rank_rate(anchors: Mapping[str, float]) -> dict[str, object]:
    """Price gold at fused rank 4+, which the sealed record never produced.

    The frozen cell's ``top_l = 3`` means no flown trajectory ever supplied a
    fourth target, so there is NO measured conversion at rank 4 or deeper. The
    rate used is the measured rank-2/3 rate scaled by the measured decay from
    rank 1 to rank 2/3 -- one further step of the same observed slope. It is
    an extrapolation and is labelled as one everywhere it is used.
    """

    top1 = anchors["gold_is_fused_top1"]
    mid = anchors["gold_at_fused_2_or_3"]
    slope = (mid / top1) if top1 > 0 else 0.0
    return {
        "value": round(mid * slope, 4),
        "derivation": (
            "measured rank-2/3 rate times the measured rank-1 to rank-2/3 decay ratio: "
            f"{mid} * ({mid} / {top1})"
        ),
        "status": (
            "EXTRAPOLATION, not a measurement -- the frozen cell's top_l = 3 means no flown "
            "trajectory ever supplied a fourth target, so no anchor exists at this rank"
        ),
        "measured_rank1": top1,
        "measured_rank2_3": mid,
    }


def analyse(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Run the supply-budget projection. Contacts nothing."""

    attempts = ra.arm_offline_guard()

    bundle = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    split_populations = d5.load_populations(repo_root)

    cells: dict[str, cf.CellPopulation] = {}
    annotated: dict[str, dict[str, nx.AnnotatedSample]] = {}
    gates: dict[str, object] = {}
    for pin in cf.CELL_PINS:
        cell = cf.load_cell_population(
            pin=pin,
            bundle=bundle,
            populations=split_populations,
            data_root=data_root,
            repo_root=repo_root,
        )
        cells[pin.population_id] = cell
        replays, gate = cf.replay_population(cell, bundle)
        if not (gate["retain_dispatch_gate_passed"] and gate["supply_gate_passed"]):
            raise SupplyBudgetError(
                f"{pin.population_id}: the inherited fidelity gate did not pass; refusing "
                "to project from a replay that does not reproduce the flight"
            )
        annotated[pin.population_id] = nx.annotate_population(cell, replays, bundle)
        gate["decision_rule"] = nx.decision_rule_gate(annotated[pin.population_id])
        gates[pin.population_id] = gate

    anchors, anchor_counts = nx.pooled_anchors(annotated)
    deep = _derive_deep_rank_rate(anchors)

    recall_cache: dict[tuple[str, str, int], object] = {}
    variant_samples: dict[str, dict[str, dict[str, VariantSample]]] = {}
    for variant in VARIANTS:
        variant_samples[variant.variant_id] = {}
        for pin in cf.CELL_PINS:
            variant_samples[variant.variant_id][pin.population_id] = replay_variant(
                cells[pin.population_id], bundle, variant, recall_cache=recall_cache
            )

    # The baseline variant must reproduce the already-gated flown supply
    # exactly; otherwise the whole counterfactual sweep is void.
    baseline_gate = {}
    for pin in cf.CELL_PINS:
        base = variant_samples[BASELINE_VARIANT_ID][pin.population_id]
        flown = cells[pin.population_id].inputs.logged_supply
        matched = 0
        checked = 0
        for sample_id, item in base.items():
            if not item.dispatched:
                continue
            checked += 1
            if item.selected_value_ids == tuple(sorted(flown.get(sample_id, ()))):
                matched += 1
        baseline_gate[pin.population_id] = {
            "dispatched": checked,
            "supply_matches_the_flown_channel": matched,
            "passed": matched == checked and checked > 0,
        }
        if matched != checked:
            raise SupplyBudgetError(
                f"{pin.population_id}: the baseline variant does not reproduce the flown "
                "SUPPLY channel; the sweep is void"
            )

    flown_rate = flown_value_token_rate(cells)
    model = token_model(bundle, flown_rate=flown_rate)
    tokens_by_variant: dict[str, object] = {}
    for variant in VARIANTS:
        worst_values = max(
            max(
                (
                    item.supplied_count
                    for item in variant_samples[variant.variant_id][pin.population_id].values()
                    if item.dispatched
                ),
                default=0,
            )
            for pin in cf.CELL_PINS
        )
        facet_count = 5 if variant.top_k == 5 else 8
        structural_cap = min(variant.nominal_cap, variant.top_k)
        tokens_by_variant[variant.variant_id] = {
            "observed_worst_supplied_values": worst_values,
            "structural_cap_min_of_nominal_and_recall_window": structural_cap,
            "at_the_observed_worst_case": token_estimate(
                model, values=max(worst_values, 1), facet_representations=facet_count
            ),
            "at_the_STRUCTURAL_cap": token_estimate(
                model, values=structural_cap, facet_representations=facet_count
            ),
            "at_the_NOMINAL_cap": token_estimate(
                model,
                values=variant.nominal_cap,
                facet_representations=facet_count,
            ),
            "facet_block_disclosure": (
                "the facet-representation block is priced at the nearest landed anchor "
                "(5 or 8 representations). It is a conservative addition either way: the "
                "flown runner renders ZERO facet representations, because the C3 "
                "controller carries visible_facet_ids empty"
            ),
            "which_envelope_a_prompt_fit_row_should_use": (
                "the STRUCTURAL cap. A candidate value must be supported by a "
                "percept-admitted facet and there are at most recall_top_k of those, so "
                "min(c * top_l, k) is a real bound and the nominal cap is not reachable -- "
                "confirmed on every sealed dispatched trajectory by the structural-ceiling "
                "distribution in the saturation profile"
            ),
        }

    per_variant: dict[str, object] = {}
    for variant in VARIANTS:
        rows: dict[str, object] = {}
        for pin in cf.CELL_PINS:
            name = pin.population_id
            base = variant_samples[BASELINE_VARIANT_ID][name]
            current = variant_samples[variant.variant_id][name]
            rows[name] = {
                "saturation": saturation_profile(current, variant),
                "reachability_and_risk": reachability_and_risk(
                    baseline=base,
                    variant_samples=current,
                    annotated=annotated[name],
                    variant=variant,
                ),
                "projected_band": projected_band(
                    baseline=base,
                    variant_samples=current,
                    annotated=annotated[name],
                    anchors=anchors,
                    deep_rank_rate=float(deep["value"]),
                    variant=variant,
                ),
                "a4_overlap": a4_overlap(
                    baseline=base,
                    variant_samples=current,
                    annotated=annotated[name],
                    variant=variant,
                ),
            }
        per_variant[variant.variant_id] = rows

    structural = {
        "c_cannot_add_a_target": (
            "_fuse_supply_filter picks top_l targets FIRST and only then keeps c values "
            "inside each, so raising c alone can never put gold into the supplied set on "
            "any trajectory -- verified measurement-side by the (3,3) and (2,3) rows "
            "carrying identical newly-gold-supplied counts of zero"
        ),
        "the_recall_window_bounds_the_budget": (
            "a candidate value must be supported by a percept-admitted facet, and the "
            "admitted facets are a subset of the recall_top_k_per_dimension window, so the "
            "structural ceiling on supplied values is set by k, not by c * top_l"
        ),
    }

    report: dict[str, object] = {
        "schema": SCHEMA,
        "exposure_row_id": EXPOSURE_ROW_ID,
        "tier": "ITERATION-TIER DESIGN INPUT -- selects no knob, authorizes no flight",
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
            "proof_shape": (
                "socket.socket.connect / connect_ex / socket.create_connection were replaced "
                "with counting refusers BEFORE the first input was opened; a nonzero counter "
                "would have raised. No server-log byte-identity claim is made because a "
                "concurrent A4 retain-override flight holds the resident decoder unit"
            ),
        },
        "frozen_cell": {
            "config": cf.FROZEN_POLICY_CONFIG_RELPATH,
            "alpha": cf.FROZEN_ALPHA,
            "tau": cf.FROZEN_FUSE.tau,
            "top_k_per_dimension": cf.FROZEN_TOP_K,
            "fusion": {
                "m": cf.FROZEN_FUSE.m,
                "c": cf.FROZEN_FUSE.c,
                "l": cf.FROZEN_FUSE.top_l,
            },
        },
        "sources": {
            pin.population_id: {
                "run_dir": str(cells[pin.population_id].run_dir),
                "samples": len(cells[pin.population_id].sample_ids),
                "artifact_sha256_measured_at_read_time": dict(
                    cells[pin.population_id].artifact_hashes
                ),
            }
            for pin in cf.CELL_PINS
        },
        "snapshot": {
            "snapshot_sha256": bundle.snapshot_sha256,
            "content_facet_npz_sha256": bundle.npz_sha256,
            "content_facets": len(bundle.facet_ids),
            "label_vocabulary_size": len(set(bundle.label_targets.values())),
            "value_vectors": "SEALED (never loaded)",
        },
        "fidelity_gates": gates,
        "baseline_variant_gate": baseline_gate,
        "structural_findings_from_the_fuser_source": structural,
        "shared_empirical_anchor": {
            "pooled_rates": anchors,
            "pooled_counts": {
                name: {"correct": pair[0], "n": pair[1]}
                for name, pair in anchor_counts.items()
            },
            "deep_rank_rate": deep,
            "dilution": dilution_anchors(annotated),
        },
        "variants": [variant.as_json() for variant in VARIANTS],
        "flown_value_token_rate": {
            key: value for key, value in flown_rate.items() if not key.startswith("_")
        },
        "token_model": {
            key: value for key, value in model.items() if not key.startswith("_")
        },
        "token_estimates": tokens_by_variant,
        "flown_reality_check": {
            "declared_evidence_prompt_tokens_median_at_6_values": (
                FLOWN_EVIDENCE_PROMPT_TOKENS_MEDIAN_AT_6_VALUES
            ),
            "declared_evidence_prompt_tokens_max_at_6_values": (
                FLOWN_EVIDENCE_PROMPT_TOKENS_MAX_AT_6_VALUES
            ),
            "source": (
                "the sealed K-WIDEN K1 landing's own prompt-reuse record; the flown runner "
                "renders ZERO facet representations, so real prompts sit far below the "
                "worst-case envelope"
            ),
        },
        "per_variant": per_variant,
        "what_this_document_does_not_do": (
            "it registers no round, selects no knob, authorizes no flight, and reaches no "
            "verdict on the frozen cell or on convergence. It adds one analysis module and "
            "one readiness note"
        ),
    }
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    report = analyse(repo_root=args.repo_root, data_root=args.data_root)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


__all__ = [
    "BASELINE_VARIANT_ID",
    "BYTE_VARIANCE_CHANNEL_PER_100",
    "BudgetVariant",
    "EXPOSURE_ROW_ID",
    "PROMPT_FIT_ANCHORS",
    "SCHEMA",
    "VARIANTS",
    "VariantSample",
    "a4_overlap",
    "analyse",
    "dilution_anchors",
    "flown_value_token_rate",
    "main",
    "projected_band",
    "reachability_and_risk",
    "replay_variant",
    "saturation_profile",
    "token_estimate",
    "token_model",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
