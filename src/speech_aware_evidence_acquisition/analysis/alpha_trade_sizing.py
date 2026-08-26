"""THE ALPHA TRADE SIZING -- how big is the decision the owner has open?

Exposure row ``SAEA-SN-MF-ALPHA-TRADE-SIZING``, registered at commit
``9ea74f6b`` BEFORE any computation was performed. Zero frozen-core contacts,
zero pinned-tool embedding contacts, zero tokenizer contacts, zero HTTP or
socket requests, zero new dependencies, zero package installations. Every byte
this module reads is already landed and sealed.

THIS ROW SIZES A DECISION AND DOES NOT TAKE IT
----------------------------------------------
No knob is changed, no line under ``rails/``, ``core/`` or ``configs/`` is
written, ``alpha`` stays 0.45 in the frozen cell, nothing hash-pinned moves, no
receipt is displaced, no arm is re-flown, no new sample is touched and no new
gold surface is opened. The module RECOMMENDS NO VALUE OF ALPHA and authorizes
no change.

Why it exists
-------------
Four independent model-free lines landed on 2026-08-25 and all four converge on
the same structural parameter, the alpha-blend weight:

1. REACH IS STRUCTURAL. :func:`kb_policy._blend_scores` gives the direct label
   ``alpha * f + (1 - alpha)`` and every rival at most ``alpha * f``, with
   ``f in [0, 1]`` and ``sum(f) in {0, 1}`` by construction, so at the locked
   ``alpha = 0.45`` the direct label wins by a GUARANTEED margin
   ``1 - 2*alpha = +0.10`` for EVERY possible supply. ``retain ==
   direct-label-recovered`` is therefore a property of the policy form, and
   reach is 15/104 = 14.42 percent on Audio2Tool and 160/500 = 32.00 percent
   on the SLURP unexposed half.
   (``docs/readiness/2026-08-25-cross-carrier-transfer-verdict.md``)
2. QUERY DEGENERACY. The alpha veto selects exactly the trajectories whose
   contact-0 answer is empty, and that empty answer IS the retrieval query.
   (``docs/readiness/2026-08-25-query-key-degeneracy-cross-carrier.md``,
   ``docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md``)
3. EXTRACTION DELIVERY. Supply is only ever delivered to trajectories that
   FAILED matching, so "the supply adds nothing on top of a correct intent" is
   UNTESTED rather than falsified.
   (``docs/readiness/2026-08-25-extraction-conditioned-on-dispatch.md``)
4. FUSION FORM. Every principled re-scoring of the ranker measured as an exact
   identity, because the alpha veto keeps the label layer out of every
   decision. (``docs/readiness/2026-08-25-fusion-form-offline-gate.md``)

What is computed
----------------
``alpha`` enters the trajectory ONLY at the blend head, strictly AFTER
recall / rank / fuse. The supply is therefore an ALPHA-INVARIANT object: this
module replays recall -> rank -> fuse ONCE per sample through the registered
path (:func:`dev100_damage_channel_analysis.replay_supply`, itself the
reference the fusion-form gate's C0 self-gate is measured against), and then
evaluates the REAL :func:`kb_policy._blend_scores` and
:func:`kb_policy._argmax_labels` at each grid point. Nothing about the blend is
reimplemented, and the dispatch branch is read off the controller's own
control flow in :meth:`kb_policy.KbAlphaBlendController._advance_after_direct`
rather than restated as an inequality.

What this row must NOT claim
----------------------------
A CHANGED DISPATCH DECISION DOES NOT TELL US WHAT THE FROZEN CORE WOULD HAVE
ANSWERED. There is no sealed decode for a trajectory that did not dispatch. So
reach, composition and supply quality are FACTS ABOUT THE MACHINERY, and every
outcome number is a PROJECTION and is labelled one. No expected-accuracy
headline is produced.

Everything computed on the SLURP UNEXPOSED 500 is a SECONDARY READING on the
locked baseline's own population and MUST NOT be used to revise, re-tune or
restate THE LOCK, which stands exactly as landed at ``d9fef537``.
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
from . import dev1000_lock_read as d1k
from . import fusion_form_offline_gate as ffg
from . import k1_hybrid_ranking_gate as k1
from . import query_key_degeneracy_cross_carrier as qkd
from ..rails import kb_policy as kb

SCHEMA = "saea-alpha-trade-sizing-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-ALPHA-TRADE-SIZING"

#: The commit the registration row is readable at. The row was authored and
#: written to ``docs/exposure-ledger.md`` BEFORE any input was opened; a
#: CONCURRENT session's ledger commit swept the already-present row into its
#: own tree write, so the registration is readable at that session's commit
#: rather than at one of this row's own. The row TEXT is unmodified and its
#: sha256 is published below, so the sweep changes where the row is read from
#: and nothing else.
LEDGER_COMMIT = "9ea74f6b"
LEDGER_ROW_SHA256 = "c0d6200cfe100d94ecde7e6e7b97467c9c0dd2c659fa6e38298ef3e4b0398062"
LEDGER_SWEEP_DISCLOSURE = (
    "the registration row was written to docs/exposure-ledger.md before this module's first "
    "input was opened, and was committed at 9ea74f6b -- a CONCURRENT session's ledger commit "
    "('ledger(scoreboard-v5)') which swept the already-present row in alongside its own. The "
    "row text is byte-unchanged and its sha256 is published here so the registration is "
    "verifiable independently of which commit message carries it"
)

VERDICT_RELPATH = "docs/readiness/2026-08-25-alpha-trade-sizing.md"
CHECK_DIR_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-alpha-trade-sizing"
)


class SizingError(RuntimeError):
    """A pinned input does not match, or a structural self-gate contradicts a
    sealed record. Never raised for a legitimate data shape."""


# ---------------------------------------------------------------------------
# REGISTERED CONSTANTS -- fixed by the ledger row, never re-tried after
# ---------------------------------------------------------------------------

#: The pre-registered alpha grid, spanning both sides of 0.5 because 0.5 is
#: where the guaranteed margin ``1 - 2*alpha`` inverts and dispatch stops being
#: confined to the label-free set.
ALPHA_GRID = (0.40, 0.45, 0.50, 0.55, 0.60, 0.65)

#: The frozen, LOCKED value, carried as the CONTROL. Imported, never restated.
CONTROL_ALPHA = cf.FROZEN_ALPHA

FROZEN_TOP_K = cf.FROZEN_TOP_K
FROZEN_WEIGHTS = cf.FROZEN_WEIGHTS
FROZEN_FUSE = cf.FROZEN_FUSE

SLURP_UNEXPOSED = ffg.SLURP_UNEXPOSED
SLURP_EXPOSED = ffg.SLURP_EXPOSED
A2T_POPULATION = ffg.A2T_POPULATION

#: The published reach counts at the LOCKED cell, which this module's own
#: control replay must reproduce EXACTLY before any other grid point's number
#: is read. Fail-closed.
PUBLISHED_CONTROL_REACH = {
    SLURP_UNEXPOSED: (
        160,
        500,
        "docs/readiness/2026-08-25-cross-carrier-transfer-verdict.md section 3.1 "
        "(reachable = label-free set, locked v1 cell)",
    ),
    SLURP_EXPOSED: (
        166,
        500,
        "docs/readiness/2026-08-25-query-key-degeneracy-cross-carrier.md section 3.2 "
        "(dead-direct 166 of 500 on the nested prior-exposed DEV-500)",
    ),
    A2T_POPULATION: (
        15,
        104,
        "docs/readiness/2026-08-25-cross-carrier-transfer-verdict.md section 3.1 "
        "(A2T reachable 15 of 104 = 14.42 percent)",
    ),
}

SECONDARY_READING = ffg.SECONDARY_READING
PROJECTION_LABEL = ffg.PROJECTION_LABEL

#: The adverse prior, carried in advance and reported beside the risk column.
ADVERSE_PRIOR = (
    "THE DELTA RETAIN-OVERRIDE. The delta >= 0.14 retain-override was the last attempt to widen "
    "dispatch beyond the alpha veto. Its registered property was ZERO LOSS BY CONSTRUCTION and it "
    "held on every exposed population (DEV-100 r4/r5, DEV-500 NEW400) and in the A4 flight. Out of "
    "sample it RECOVERED 0 OF 3 AND DAMAGED 3 OF 3 (net -3 samples, -0.60 pp) while the 11 fires in "
    "the previously-exposed half recovered 11 of 11; two of the three failures sat at "
    "delta = 0.140362, 0.000362 above the hand-fit bar. It was REMOVED from the locked cell "
    "(docs/readiness/2026-08-25-baseline-lock-verdict.md section 3; lock commit d9fef537). "
    "ALPHA IS A STRUCTURAL PARAMETER RATHER THAN A HAND-FIT RULE, so this prior does not transfer "
    "mechanically -- but the failure mode it names, that WIDENING DISPATCH DAMAGES TRAJECTORIES "
    "WHICH WERE ALREADY RIGHT, is exactly the quantity the risk column measures, and the two are "
    "reported side by side and never apart."
)

#: The cost beyond accuracy, stated as a TRADE and not a verdict.
TRADE_BEYOND_ACCURACY = {
    "byte_identical_transfer": (
        "The locked policy cell transferred to a SECOND CARRIER BYTE-IDENTICAL: "
        "configs/policy/kb-policy-v1-dev100.json (sha256 "
        "d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919), whose knobs block is "
        "byte-unchanged across the lock commit, ran Audio2Tool with no knob edited at all "
        "(docs/readiness/2026-08-25-cross-carrier-transfer-verdict.md section 1.3). CHANGING ALPHA "
        "BREAKS THAT PROPERTY. It is not an accuracy cost; it is the loss of a scientific asset -- "
        "arguably the single strongest sentence this study's second carrier has produced."
    ),
    "per_carrier_alpha": (
        "A PER-CARRIER alpha weakens the generality claim further than a single moved alpha does: "
        "it converts 'one cell, two carriers' into 'one method, tuned per carrier', which is a "
        "materially weaker statement and one a reviewer prices accordingly."
    ),
    "framing": (
        "This is stated as a TRADE and not a verdict. It is an OWNER decision: buy reach on one "
        "carrier, sell the strongest generality statement the study has. No implementer may make "
        "that trade, and this document does not make it."
    ),
    "source": "docs/readiness/2026-08-25-cross-carrier-transfer-verdict.md sections 1.3 and 4",
}

HARD_STOP = (
    "THIS DOCUMENT RECOMMENDS NO VALUE OF ALPHA AND AUTHORIZES NO CHANGE. It sizes a decision the "
    "owner has open; it does not take it, does not propose taking it, and does not recommend a "
    "value. No knob is changed, no line under rails/, core/ or configs/ is written, alpha stays "
    "0.45 in the frozen cell, nothing hash-pinned moves and no arm is re-flown. Every outcome "
    "number here is a PROJECTION, because a changed dispatch decision does not tell us what the "
    "frozen core would have answered and no sealed decode exists for a trajectory that did not "
    "dispatch. Everything computed on the SLURP unexposed 500 is a SECONDARY READING on the locked "
    "baseline's own population and MUST NOT be used to revise, re-tune or restate THE LOCK, which "
    "stands exactly as landed at d9fef537."
)


# ---------------------------------------------------------------------------
# The alpha-invariant trajectory record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Trajectory:
    """One sample's ALPHA-INVARIANT facts, replayed once.

    ``alpha`` enters only at the blend head, so recall, rank, fuse, the
    admitted set, the supply and every gold position are shared by every grid
    point by construction rather than by measurement.
    """

    sample_id: str
    direct_label: str | None
    supply_empty: bool
    selected_value_ids: tuple[str, ...]
    admitted_facet_ids: tuple[str, ...]
    supplied_targets: tuple[str, ...]
    gold_target: str
    gold_supplied: bool
    gold_target_rank: int | None
    fused_label_scores: Mapping[str, float]
    direct_correct: bool
    sealed_correct: bool
    m0_correct: bool | None
    flown_dispatched: bool
    direct_text: str


@dataclass(frozen=True)
class Decision:
    """The controller's own retain/dispatch decision at one alpha."""

    dispatched: bool
    branch: str
    best_labels: tuple[str, ...]


#: The five mutually exclusive branches of
#: ``KbAlphaBlendController._advance_after_direct``, named once.
BRANCH_RETAIN_EMPTY = "retain:supply-empty"
BRANCH_RETAIN_VETO = "retain:alpha-veto"
BRANCH_DISPATCH_DEAD = "dispatch:dead-direct"
BRANCH_DISPATCH_TIE = "dispatch:tie-includes-direct"
BRANCH_DISPATCH_OUTVOTED = "dispatch:outvoted"
BRANCHES = (
    BRANCH_RETAIN_EMPTY,
    BRANCH_RETAIN_VETO,
    BRANCH_DISPATCH_DEAD,
    BRANCH_DISPATCH_TIE,
    BRANCH_DISPATCH_OUTVOTED,
)

BRANCH_DESCRIPTIONS = {
    BRANCH_RETAIN_EMPTY: (
        "the fuser selected nothing, so _advance_after_direct returns before a blend is formed "
        "at all -- alpha-independent by construction"
    ),
    BRANCH_RETAIN_VETO: (
        "a RECOVERED direct label is the strict, unique argmax of the blend, so retain-primary "
        "fires and no evidence contact is ever dispatched"
    ),
    BRANCH_DISPATCH_DEAD: (
        "no direct label was recovered, so best_labels can never equal (direct_label,) and the "
        "trajectory dispatches whatever the supply says -- the whole reachable set below alpha 0.5"
    ),
    BRANCH_DISPATCH_TIE: (
        "the direct label is among several argmax labels but does not win uniquely; the "
        "controller dispatches so the evidence decode has a real answer to break the tie with"
    ),
    BRANCH_DISPATCH_OUTVOTED: (
        "a RECOVERED direct label is beaten outright by the supply -- structurally impossible "
        "below alpha = 0.5, where the guaranteed margin 1 - 2*alpha is strictly positive"
    ),
}


def decide(
    trajectory: Trajectory, *, alpha: float, label_targets: Mapping[str, str]
) -> Decision:
    """The controller's own decision, through the REGISTERED blend head.

    :func:`kb_policy._blend_scores` and :func:`kb_policy._argmax_labels` are
    IMPORTED and called; the branch is read off
    ``KbAlphaBlendController._advance_after_direct``'s own control flow --
    early return on an empty selection, retain-primary when
    ``best_labels == (direct_label,)``, dispatch otherwise -- rather than
    restated as an inequality that could drift from it.
    """

    if trajectory.supply_empty:
        return Decision(dispatched=False, branch=BRANCH_RETAIN_EMPTY, best_labels=())
    blended = kb._blend_scores(
        label_targets, trajectory.fused_label_scores, trajectory.direct_label, alpha
    )
    best = kb._argmax_labels(blended)
    direct = trajectory.direct_label
    if direct is None:
        return Decision(dispatched=True, branch=BRANCH_DISPATCH_DEAD, best_labels=best)
    if best == (direct,):
        return Decision(dispatched=False, branch=BRANCH_RETAIN_VETO, best_labels=best)
    if direct in best:
        return Decision(dispatched=True, branch=BRANCH_DISPATCH_TIE, best_labels=best)
    return Decision(dispatched=True, branch=BRANCH_DISPATCH_OUTVOTED, best_labels=best)


def margin_arithmetic(alpha: float) -> dict[str, object]:
    """The structural statement at one alpha, with no data at all.

    The theorem itself is IMPORTED from the cross-carrier read rather than
    restated; only the grid-point arithmetic is added.
    """

    guaranteed = (1.0 - alpha) - alpha
    # A rival can outvote a recovered direct label only when
    # alpha*f_rival > alpha*f_direct + (1 - alpha), i.e. when the fused mass
    # gap exceeds (1 - alpha)/alpha. sum(fused) <= 1 caps that gap at 1.0.
    required_gap = (1.0 - alpha) / alpha if alpha > 0.0 else float("inf")
    return {
        "alpha": alpha,
        "is_the_locked_control": alpha == CONTROL_ALPHA,
        "direct_label_floor_1_minus_alpha": 1.0 - alpha,
        "rival_ceiling_alpha": alpha,
        "guaranteed_margin_1_minus_2alpha": guaranteed,
        "veto_holds_for_every_supply": guaranteed > 1e-9,
        "fused_mass_gap_a_rival_must_exceed": required_gap,
        "that_gap_is_attainable": required_gap <= 1.0,
        "worst_case_is_an_exact_tie": abs(required_gap - 1.0) <= 1e-12,
        "reading": (
            "a recovered direct label is the strict unique argmax for EVERY possible supply"
            if guaranteed > 1e-9
            else (
                "the worst case (all fused mass on one rival) is an exact TIE, which "
                "_argmax_labels returns as a multi-label best set and the controller therefore "
                "DISPATCHES"
                if abs(required_gap - 1.0) <= 1e-12
                else "a supply concentrating more than the stated fused-mass gap outvotes the "
                "direct label outright"
            )
        ),
        "theorem": ccd.alpha_veto_theorem(alpha),
    }


# ---------------------------------------------------------------------------
# Population assembly
# ---------------------------------------------------------------------------


def build_trajectories(
    population: ffg.PopulationInputs, *, m0_correct: Mapping[str, bool] | None
) -> dict[str, Trajectory]:
    """Replay recall -> rank -> fuse ONCE per sample, through the registered path.

    :func:`dev100_damage_channel_analysis.replay_supply` is the reference the
    fusion-form gate's own C0 self-gate is measured against, and the loaders
    this module calls have already gated that path against the FLIGHT before
    returning. Nothing here re-derives a supply a second way.
    """

    inputs = population.inputs
    out: dict[str, Trajectory] = {}
    for sample_id in population.sample_ids:
        supply = dc.replay_supply(
            inputs,
            sample_id,
            weights=FROZEN_WEIGHTS,
            knobs=FROZEN_FUSE,
            top_k=FROZEN_TOP_K,
            recall_scores=population.recall_scores[sample_id],
        )
        fused = kb._fused_label_scores(
            inputs.label_targets,
            inputs.values_by_id,
            supply.selected_value_ids,
            supply.rank_result,
        )
        ordered = ffg._ordered_supplied_targets(
            selected_value_ids=supply.selected_value_ids,
            admitted_facet_ids=supply.admitted_facet_ids,
            values_by_id=inputs.values_by_id,
            rank_result=supply.rank_result,
        )
        gold = population.gold_targets[sample_id]
        out[sample_id] = Trajectory(
            sample_id=sample_id,
            direct_label=population.direct_labels[sample_id],
            supply_empty=not supply.selected_value_ids,
            selected_value_ids=tuple(sorted(supply.selected_value_ids)),
            admitted_facet_ids=tuple(sorted(supply.admitted_facet_ids)),
            supplied_targets=ordered,
            gold_target=gold,
            gold_supplied=gold in ordered,
            gold_target_rank=(ordered.index(gold) + 1 if gold in ordered else None),
            fused_label_scores=fused,
            direct_correct=bool(population.direct_correct[sample_id]),
            sealed_correct=bool(population.sealed_correct[sample_id]),
            m0_correct=(None if m0_correct is None else bool(m0_correct[sample_id])),
            flown_dispatched=bool(population.flown_dispatched[sample_id]),
            direct_text=inputs.direct_texts[sample_id],
        )
    return out


def load_slurp_m0(*, repo_root: Path, data_root: Path, gold_by_sample) -> dict[str, bool]:
    """The SEALED DEV-1000 M0 arm's per-sample correctness.

    Loaded through :func:`dev1000_lock_read.load_arm` (which hash-verifies the
    committed report AND the attempt-store bytes before a response is parsed)
    and scored through :func:`dev500_confirmatory_read.score_arm`, the
    repository's own registered scorer. Neither is reimplemented.
    """

    pins = [pin for pin in d1k.ARM_PINS if pin.arm_id == "M0"]
    if len(pins) != 1:
        raise SizingError("the DEV-1000 arm pins do not name exactly one M0 arm")
    arm = d1k.load_arm(pin=pins[0], repo_root=Path(repo_root), data_root=Path(data_root))
    scored = d5.score_arm(arm=arm, gold_by_sample=gold_by_sample)
    return {sid: bool(value) for sid, value in scored.correct.items()}


# ---------------------------------------------------------------------------
# The reported quantities
# ---------------------------------------------------------------------------


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def locked_outcome(
    trajectory: Trajectory, *, control_dispatched: bool
) -> bool:
    """The LOCKED cell's own final answer, exactly.

    A retained trajectory's final answer IS its contact-0 direct decode -- the
    runner can only ever select the response of the contact that just
    completed, and retain-primary fires before an evidence contact is ever
    dispatched. A control-dispatched trajectory's final answer is the sealed
    evidence decode. This is arithmetic over sealed records, not a projection.
    """

    return trajectory.sealed_correct if control_dispatched else trajectory.direct_correct


def reach_block(
    trajectories: Mapping[str, Trajectory],
    decisions: Mapping[str, Decision],
) -> dict[str, object]:
    """Q1: how many trajectories dispatch, and through which branch."""

    total = len(trajectories)
    dispatched = [sid for sid, d in decisions.items() if d.dispatched]
    branch_counts = {name: 0 for name in BRANCHES}
    for decision in decisions.values():
        branch_counts[decision.branch] += 1
    return {
        "n": total,
        "dispatched": len(dispatched),
        "dispatch_rate": _rate(len(dispatched), total),
        "retained": total - len(dispatched),
        "branch_counts": branch_counts,
        "branch_descriptions": BRANCH_DESCRIPTIONS,
        "branch_partition_sums_to_n": sum(branch_counts.values()) == total,
    }


def degeneracy_block(
    sample_ids: Sequence[str],
    trajectories: Mapping[str, Trajectory],
    query_vectors: Mapping[str, Sequence[float]],
    *,
    label: str,
) -> dict[str, object]:
    """Query-vector diversity, through the landed degeneracy definitions.

    :func:`query_key_degeneracy_cross_carrier._cluster_block` is IMPORTED and
    called on the RAW landed query vectors, so the degeneracy ratio reported
    here is the SAME quantity that read published and not a look-alike. Its key
    identity is :func:`query_key_degeneracy_cross_carrier.vector_digest`,
    itself byte-identical to the A2T gold-absence diagnosis' own digest.
    """

    ids = tuple(sorted(sample_ids))
    if not ids:
        return {
            "label": label,
            "n": 0,
            "distinct_query_vectors": 0,
            "distinct_query_vectors_per_trajectory": None,
            "largest_identical_query_cluster_size": 0,
            "largest_identical_query_cluster_share": None,
            "distinct_contact0_texts": 0,
            "note": "empty set -- no diversity statistic is defined on it",
        }
    return qkd._cluster_block(
        ids,
        label=label,
        query_vectors={sid: query_vectors[sid] for sid in ids},
        texts={sid: trajectories[sid].direct_text for sid in ids},
        supplies={sid: trajectories[sid].selected_value_ids for sid in ids},
    )


def composition_block(
    newly: Sequence[str],
    trajectories: Mapping[str, Trajectory],
    query_vectors: Mapping[str, Sequence[float]],
    *,
    control_dispatched: Mapping[str, bool],
) -> dict[str, object]:
    """Q2: who newly dispatches."""

    ids = tuple(sorted(newly))
    n = len(ids)
    m0_known = [sid for sid in ids if trajectories[sid].m0_correct is not None]
    m0_correct = sum(1 for sid in m0_known if trajectories[sid].m0_correct)
    locked_correct = sum(
        1
        for sid in ids
        if locked_outcome(trajectories[sid], control_dispatched=control_dispatched[sid])
    )
    recovered = sum(1 for sid in ids if trajectories[sid].direct_label is not None)
    return {
        "n": n,
        "sample_ids": list(ids[:25]),
        "M0_correct": m0_correct,
        "M0_wrong": len(m0_known) - m0_correct,
        "M0_coverage": len(m0_known),
        "M0_note": (
            "the SEALED knowledge-free arm's own scored answer, loaded through the pinned arm "
            "and scored by the repository's registered scorer"
        ),
        "correct_under_the_locked_cell": locked_correct,
        "wrong_under_the_locked_cell": n - locked_correct,
        "carries_a_recovered_direct_label": recovered,
        "carries_no_direct_label": n - recovered,
        "recovered_label_note": (
            "the label-free (dead-direct) set already dispatches at the locked alpha, so every "
            "trajectory that newly enters the dispatching set as alpha rises necessarily carries "
            "a RECOVERED direct label -- this count is reported rather than assumed"
        ),
        "query_vector_diversity": degeneracy_block(
            ids, trajectories, query_vectors, label="newly dispatching"
        ),
    }


def supply_quality_block(
    ids: Sequence[str], trajectories: Mapping[str, Trajectory]
) -> dict[str, object]:
    """Q3: what supply the newly dispatched would receive.

    The gold-side accounting is the gold-absence diagnosis' own: a supply
    "carries gold" when the ordered ``task_target`` set contains the
    trajectory's gold target, and the fused target rank is that target's
    position in the fuser's own ordering (by the score of its best ADMITTED
    supporting facet), through the IMPORTED
    :func:`fusion_form_offline_gate._ordered_supplied_targets`.
    """

    ids = tuple(sorted(ids))
    n = len(ids)
    non_empty = sum(1 for sid in ids if trajectories[sid].selected_value_ids)
    gold = [sid for sid in ids if trajectories[sid].gold_supplied]
    ranks = [trajectories[sid].gold_target_rank for sid in gold]
    histogram = {
        "fused_rank_1": sum(1 for r in ranks if r == 1),
        "fused_rank_2_or_3": sum(1 for r in ranks if r in (2, 3)),
        "fused_rank_4_or_worse": sum(1 for r in ranks if r is not None and r >= 4),
        "gold_absent_from_the_supply": n - len(gold),
    }
    return {
        "n": n,
        "would_receive_a_non_empty_supply": non_empty,
        "would_receive_a_gold_bearing_supply": len(gold),
        "gold_bearing_rate": _rate(len(gold), n),
        "fused_rank_histogram": histogram,
        "histogram_sums_to_n": sum(histogram.values()) == n,
        "aggregate_supplied_values": sum(
            len(trajectories[sid].selected_value_ids) for sid in ids
        ),
        "aggregate_distinct_supplied_task_targets": sum(
            len(set(trajectories[sid].supplied_targets)) for sid in ids
        ),
        "accounting": (
            "a supply CARRIES GOLD when its ordered task_target set contains the trajectory's "
            "gold target; the fused target rank is that target's position in the fuser's own "
            "ordering, by the score of its best ADMITTED supporting facet -- the same accounting "
            "docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md and the fusion-form gate use"
        ),
    }


def risk_block(
    newly: Sequence[str],
    trajectories: Mapping[str, Trajectory],
    *,
    control_dispatched: Mapping[str, bool],
    population_n: int,
) -> dict[str, object]:
    """Q4: currently-CORRECT trajectories put at risk. Reported beside reach.

    This is the quantity the delta retain-override failure was made of, and it
    is never shown apart from the reach it buys.
    """

    ids = tuple(sorted(newly))
    at_risk = [
        sid
        for sid in ids
        if locked_outcome(trajectories[sid], control_dispatched=control_dispatched[sid])
    ]
    gold_bearing = sum(1 for sid in at_risk if trajectories[sid].gold_supplied)
    gold_top1 = sum(
        1 for sid in at_risk if trajectories[sid].gold_target_rank == 1
    )
    return {
        "newly_dispatching": len(ids),
        "currently_correct_put_at_risk": len(at_risk),
        "share_of_the_newly_dispatching_set": _rate(len(at_risk), len(ids)),
        "share_of_the_population": _rate(len(at_risk), population_n),
        "of_those_at_risk_the_supply_carries_gold": gold_bearing,
        "of_those_at_risk_the_supply_names_gold_FIRST": gold_top1,
        "of_those_at_risk_the_supply_omits_gold": len(at_risk) - gold_bearing,
        "why_the_omission_count_matters": (
            "the measured anchor for a dispatched trajectory whose supply does NOT contain gold "
            "is 0 of 67 -- the frozen core never recovered gold from a supply that did not carry "
            "it -- so a currently-correct trajectory newly dispatched with a gold-absent supply "
            "is the exact shape of the delta override's out-of-sample damage"
        ),
        "adverse_prior": ADVERSE_PRIOR,
        "sample_ids": list(at_risk[:25]),
    }


def fused_gap_profile(trajectories: Mapping[str, Trajectory]) -> dict[str, object]:
    """POST-HOC DIAGNOSTIC, added after the registered quantities were computed.

    It introduces NO new outcome measure and carries NO verdict. It exists for
    one reason: the registered reach table came back FLAT from alpha 0.50 to
    alpha 0.65 on every population, and a reader is owed the mechanism rather
    than a mystery.

    The whole retain/dispatch decision at a recovered direct label is a
    function of ONE scalar -- the fused-mass gap
    ``max_rival fused(rival) - fused(direct)`` -- because
    ``blend(rival) >= blend(direct)`` reduces exactly to
    ``gap >= (1 - alpha) / alpha``. This block reports that scalar's
    distribution, so the shape of the reach curve is readable off the data
    instead of asserted.
    """

    gaps: list[float] = []
    one_hot = 0
    direct_zero = 0
    for trajectory in trajectories.values():
        if trajectory.direct_label is None or trajectory.supply_empty:
            continue
        fused = trajectory.fused_label_scores
        direct_mass = float(fused.get(trajectory.direct_label, 0.0))
        rivals = [
            float(score)
            for label_id, score in fused.items()
            if label_id != trajectory.direct_label
        ]
        best_rival = max(rivals) if rivals else 0.0
        gaps.append(best_rival - direct_mass)
        if abs(max(list(fused.values()) or [0.0]) - 1.0) <= 1e-9:
            one_hot += 1
        if direct_mass <= 1e-12:
            direct_zero += 1
    gaps.sort()
    n = len(gaps)
    buckets = {
        "gap_at_or_below_zero_direct_label_holds_the_top_fused_score": sum(
            1 for gap in gaps if gap <= 1e-9
        ),
        "gap_strictly_between_zero_and_one": sum(1 for gap in gaps if 1e-9 < gap < 1.0 - 1e-9),
        "gap_equal_to_one_all_fused_mass_on_a_single_rival": sum(
            1 for gap in gaps if gap >= 1.0 - 1e-9
        ),
    }
    thresholds = {}
    for alpha in ALPHA_GRID:
        bar = (1.0 - alpha) / alpha
        thresholds[f"{alpha:.2f}"] = {
            "gap_bar_1_minus_alpha_over_alpha": bar,
            "label_recovered_trajectories_clearing_it": sum(
                1 for gap in gaps if gap >= bar - 1e-9
            ),
        }
    return {
        "role": (
            "POST-HOC DIAGNOSTIC -- added after the registered quantities were computed, to "
            "explain the SHAPE of the registered reach table. It is not a registered quantity, "
            "introduces no outcome measure, and carries no verdict"
        ),
        "definition": (
            "gap = max_rival fused(rival) - fused(direct); a recovered direct label loses the "
            "blend exactly when gap >= (1 - alpha) / alpha, so the entire alpha decision is a "
            "threshold on this one scalar"
        ),
        "n_label_recovered_with_a_non_empty_supply": n,
        "gap_buckets": buckets,
        "gap_min": gaps[0] if n else None,
        "gap_median": gaps[n // 2] if n else None,
        "gap_max": gaps[-1] if n else None,
        "fused_distribution_is_one_hot": one_hot,
        "fused_distribution_gives_the_direct_label_zero_mass": direct_zero,
        "gap_bar_by_alpha": thresholds,
        "reading": (
            "the gap is not spread across the unit interval: it is concentrated at the two ENDS. "
            "Where it reaches 1.0 the fused distribution is one-hot on a single rival, and where "
            "it does not, the direct label already holds mass. Any alpha in [0.50, 1.00) "
            "therefore selects the SAME set, and alpha behaves as a SWITCH rather than a dial"
        ),
    }


def override_overlap_block(
    trajectories: Mapping[str, Trajectory],
    *,
    control_dispatched: Mapping[str, bool],
    variant_dispatched: Mapping[str, bool],
) -> dict[str, object]:
    """Where the alpha widening meets the delta retain-override's own fires.

    The v2 delta >= 0.14 retain-override is the only dispatch-widening rule
    this study has ever FLOWN, and it was falsified out of sample. Its fires
    are the only trajectories on these populations for which a real sealed
    evidence decode exists outside the control's dispatching set, so the
    overlap is reported explicitly rather than left implicit inside the
    projection's exact-outcome counts.
    """

    fires = sorted(
        sid
        for sid, trajectory in trajectories.items()
        if trajectory.flown_dispatched and not control_dispatched[sid]
    )
    reached = [sid for sid in fires if variant_dispatched[sid]]
    missed = [sid for sid in fires if not variant_dispatched[sid]]
    reached_correct = sum(1 for sid in reached if trajectories[sid].sealed_correct)
    reached_was_correct = sum(1 for sid in reached if trajectories[sid].direct_correct)
    return {
        "delta_override_fires_outside_the_control_dispatching_set": len(fires),
        "also_reached_by_this_alpha": len(reached),
        "NOT_reached_by_this_alpha": len(missed),
        "sample_ids_reached": reached[:25],
        "sample_ids_not_reached": missed[:25],
        "of_those_reached_were_correct_BEFORE_the_evidence_contact": reached_was_correct,
        "of_those_reached_were_correct_AFTER_the_sealed_evidence_contact": reached_correct,
        "status": (
            "MEASURED, not projected -- these trajectories were actually dispatched by the "
            "flight at this very supply and their answers are sealed"
        ),
        "reading": (
            "the alpha widening and the delta widening are OVERLAPPING but NOT NESTED: neither "
            "rule's reached set contains the other's, so the delta override's out-of-sample "
            "result is direct evidence about part of what alpha would reach and silent about "
            "the rest"
        ),
    }


def projection_block(
    trajectories: Mapping[str, Trajectory],
    *,
    control_dispatched: Mapping[str, bool],
    variant_dispatched: Mapping[str, bool],
) -> dict[str, object]:
    """Q5: the conversion-weighted PROJECTION. Every line is labelled one.

    Construction is :func:`fusion_form_offline_gate.conversion_projection`'s,
    unchanged, with its anchor function IMPORTED rather than restated: a
    trajectory that retains carries its own direct decode's score EXACTLY; a
    trajectory whose dispatch decision is unchanged carries the locked cell's
    outcome EXACTLY; only a trajectory whose DECISION CHANGES is priced.

    One refinement, and it removes projection rather than adding it: alpha does
    not touch the supply, so a newly dispatched trajectory that the FLIGHT
    itself dispatched (the v2 delta-override fires) has a REAL sealed evidence
    decode at the very same supply. Those are carried EXACTLY and counted
    separately -- they are the only MEASURED evidence this population holds
    about what widening dispatch actually does.
    """

    baseline = sum(
        1
        for sid, trajectory in trajectories.items()
        if locked_outcome(trajectory, control_dispatched=control_dispatched[sid])
    )
    total = len(trajectories)
    central = pessimistic = optimistic = 0.0
    exact_retained = exact_carried = exact_measured = priced = extrapolated = 0
    measured_ids: list[str] = []
    for sid, trajectory in trajectories.items():
        locked = locked_outcome(trajectory, control_dispatched=control_dispatched[sid])
        if not variant_dispatched[sid]:
            # A retained trajectory's final answer IS its contact-0 direct
            # decode. Exact, not projected.
            outcome = 1.0 if trajectory.direct_correct else 0.0
            central += outcome
            pessimistic += outcome
            optimistic += outcome
            exact_retained += 1
            continue
        if control_dispatched[sid]:
            # Dispatch unchanged and alpha does not touch the supply, so the
            # evidence prompt is byte-identical and the sealed outcome carries.
            outcome = 1.0 if trajectory.sealed_correct else 0.0
            central += outcome
            pessimistic += outcome
            optimistic += outcome
            exact_carried += 1
            continue
        if trajectory.flown_dispatched:
            # MEASURED, not projected: the FLIGHT dispatched this trajectory at
            # this very supply and its answer is sealed.
            outcome = 1.0 if trajectory.sealed_correct else 0.0
            central += outcome
            pessimistic += outcome
            optimistic += outcome
            exact_measured += 1
            measured_ids.append(sid)
            continue
        priced += 1
        rank = trajectory.gold_target_rank if trajectory.gold_supplied else None
        rate, label = k1._anchor_rate(rank)
        if label.startswith("fused rank 4+"):
            extrapolated += 1
        central += rate
        worse = None if rank is None else (rank + 2 if rank == 1 else rank + 1)
        pessimistic += k1._anchor_rate(worse)[0]
        if locked:
            optimistic += 1.0
        else:
            optimistic += k1.ANCHOR_TOP1 if trajectory.gold_supplied else 0.0
    return {
        "label": PROJECTION_LABEL,
        "no_expected_accuracy_headline": (
            "these bands are decision-sizing arithmetic, not a forecast, and no single number "
            "from this block may be quoted as an expected accuracy"
        ),
        "anchors": {
            "fused_top1_measured_108_of_110": k1.ANCHOR_TOP1,
            "fused_rank_2_or_3_measured_16_of_23": k1.ANCHOR_RANK23,
            "gold_absent_measured_0_of_67": k1.ANCHOR_ABSENT,
            "fused_rank_4_plus_EXTRAPOLATED_not_measured": k1.ANCHOR_RANK4PLUS_EXTRAPOLATED,
            "source": (
                "docs/readiness/2026-08-25-ec-and-retain-override-projections.md section 3 for "
                "the three MEASURED anchors; the rank-4-or-worse point is carried one step down "
                "the same measured slope by analysis.k1_hybrid_ranking_gate and is LABELLED AN "
                "EXTRAPOLATION wherever it is used, because the frozen top_l = 3 means no flown "
                "trajectory ever supplied a fourth target"
            ),
        },
        "n": total,
        "locked_cell_correct": baseline,
        "locked_cell_rate": _rate(baseline, total),
        "exact_outcomes_retained_trajectories": exact_retained,
        "exact_outcomes_dispatch_unchanged_identical_supply": exact_carried,
        "exact_outcomes_MEASURED_sealed_evidence_decode": exact_measured,
        "measured_sealed_evidence_decode_sample_ids": measured_ids[:25],
        "projected_trajectories_priced_at_an_anchor": priced,
        "priced_at_the_UNANCHORED_rank": extrapolated,
        "projected_pessimistic": pessimistic,
        "projected_central": central,
        "projected_optimistic": optimistic,
        "delta_pp_pessimistic": 100.0 * (pessimistic - baseline) / total if total else 0.0,
        "delta_pp_central": 100.0 * (central - baseline) / total if total else 0.0,
        "delta_pp_optimistic": 100.0 * (optimistic - baseline) / total if total else 0.0,
        "variance_prior": k1.VARIANCE_PRIOR,
        "construction": (
            "FOUR branches, three of them exact. (1) A trajectory that RETAINS carries its own "
            "contact-0 direct decode exactly, because the runner can only select the response of "
            "the contact that just completed. (2) A trajectory whose DISPATCH IS UNCHANGED "
            "carries its sealed outcome exactly, because alpha does not touch the supply and the "
            "evidence prompt is therefore byte-identical. (3) A NEWLY dispatched trajectory that "
            "the FLIGHT itself dispatched at the same supply carries its SEALED evidence decode "
            "exactly -- MEASURED, not projected. (4) Only a newly dispatched trajectory with no "
            "sealed evidence decode at all is PRICED, at the measured anchor for wherever gold "
            "sits in its supply, symmetrically for currently-correct and currently-wrong "
            "trajectories"
        ),
    }


# ---------------------------------------------------------------------------
# One population, the whole grid
# ---------------------------------------------------------------------------


def sweep_population(
    population: ffg.PopulationInputs, trajectories: Mapping[str, Trajectory]
) -> dict[str, object]:
    """Every registered quantity, at every grid point, on one population."""

    label_targets = population.inputs.label_targets
    query_vectors = population.inputs.query_vectors
    total = len(trajectories)

    decisions: dict[float, dict[str, Decision]] = {}
    for alpha in ALPHA_GRID:
        decisions[alpha] = {
            sid: decide(trajectory, alpha=alpha, label_targets=label_targets)
            for sid, trajectory in trajectories.items()
        }

    control = {sid: d.dispatched for sid, d in decisions[CONTROL_ALPHA].items()}

    # --- FAIL-CLOSED CONTROL GATE: the control replay must reproduce the
    # --- published reach for this population before any grid point is read.
    published, published_n, source = PUBLISHED_CONTROL_REACH[population.population_id]
    control_reach = sum(1 for value in control.values() if value)
    if total != published_n or control_reach != published:
        raise SizingError(
            f"{population.population_id}: the control replay dispatches {control_reach}/{total}, "
            f"not the published {published}/{published_n} -- no grid point's number may be read"
        )

    per_alpha: dict[str, object] = {}
    for alpha in ALPHA_GRID:
        variant = {sid: d.dispatched for sid, d in decisions[alpha].items()}
        newly = sorted(sid for sid in variant if variant[sid] and not control[sid])
        lost = sorted(sid for sid in variant if control[sid] and not variant[sid])
        entry: dict[str, object] = {
            "alpha": alpha,
            "role": "CONTROL (the locked, frozen value)" if alpha == CONTROL_ALPHA else "SWEEP POINT",
            "margin_arithmetic": margin_arithmetic(alpha),
            "reach": reach_block(trajectories, decisions[alpha]),
            "newly_dispatching_vs_control": composition_block(
                newly, trajectories, query_vectors, control_dispatched=control
            ),
            "no_longer_dispatching_vs_control": {
                "n": len(lost),
                "sample_ids": lost[:25],
                "note": (
                    "raising alpha can only ever ADD to the dispatching set -- the retain branch "
                    "needs a strict unique win that a larger alpha makes strictly harder -- so "
                    "this count is expected to be zero and is REPORTED rather than assumed"
                ),
            },
            "supply_quality_of_the_newly_dispatched": supply_quality_block(
                newly, trajectories
            ),
            "risk": risk_block(
                newly,
                trajectories,
                control_dispatched=control,
                population_n=total,
            ),
            "delta_override_overlap": override_overlap_block(
                trajectories,
                control_dispatched=control,
                variant_dispatched=variant,
            ),
            "projection": projection_block(
                trajectories,
                control_dispatched=control,
                variant_dispatched=variant,
            ),
        }
        per_alpha[f"{alpha:.2f}"] = entry

    control_dispatch_ids = sorted(sid for sid, value in control.items() if value)
    return {
        "population_id": population.population_id,
        "carrier": population.carrier,
        "n": total,
        "control_alpha": CONTROL_ALPHA,
        "control_gate": {
            "published_reach": f"{published}/{published_n}",
            "recomputed_reach": f"{control_reach}/{total}",
            "source": source,
            "passed": True,
        },
        "flown_dispatched": sum(
            1 for trajectory in trajectories.values() if trajectory.flown_dispatched
        ),
        "flown_minus_control_dispatch": sorted(
            sid
            for sid, trajectory in trajectories.items()
            if trajectory.flown_dispatched and not control[sid]
        ),
        "trajectories_with_a_recovered_direct_label": sum(
            1 for trajectory in trajectories.values() if trajectory.direct_label is not None
        ),
        "label_vocabulary": len(label_targets),
        "locked_cell_correct": sum(
            1
            for sid, trajectory in trajectories.items()
            if locked_outcome(trajectory, control_dispatched=control[sid])
        ),
        "fused_gap_profile_POST_HOC": fused_gap_profile(trajectories),
        "query_vector_diversity_whole_population": degeneracy_block(
            tuple(trajectories), trajectories, query_vectors, label="whole population"
        ),
        "query_vector_diversity_control_dispatching_set": degeneracy_block(
            control_dispatch_ids,
            trajectories,
            query_vectors,
            label="control dispatching set (the label-free reachable set)",
        ),
        "by_alpha": per_alpha,
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
    """Execute the sizing. Offline guard armed BEFORE the first input is opened."""

    attempts = ra.arm_offline_guard()

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()

    if CONTROL_ALPHA not in ALPHA_GRID:
        raise SizingError("the registered alpha grid does not contain the frozen control")
    if CONTROL_ALPHA != 0.45:
        raise SizingError("the frozen control alpha is not 0.45")

    slurp_populations, slurp_sources = ffg.load_slurp(
        repo_root=repo_root, data_root=data_root
    )
    a2t_population, a2t_sources = ffg.load_a2t(repo_root=repo_root, data_root=data_root)
    a2t_carrier = ccd.load_a2t_attempt4(data_root=data_root, repo_root=repo_root)

    slurp_m0 = load_slurp_m0(
        repo_root=repo_root,
        data_root=data_root,
        gold_by_sample=slurp_populations[SLURP_UNEXPOSED].inputs.gold_by_sample,
    )

    results: dict[str, object] = {}
    for population_id, population in list(slurp_populations.items()) + [
        (A2T_POPULATION, a2t_population)
    ]:
        m0 = slurp_m0 if population.carrier == "slurp" else dict(a2t_carrier.m0_correct)
        trajectories = build_trajectories(population, m0_correct=m0)
        results[population_id] = sweep_population(population, trajectories)
        if population_id == SLURP_UNEXPOSED:
            results[population_id]["reading_status"] = SECONDARY_READING

    # The structural self-check the theorem predicts: below alpha = 0.5 the
    # dispatching set is the label-free set exactly, so it cannot move with
    # alpha. Reported per population as a proof, never assumed.
    below_half = [alpha for alpha in ALPHA_GRID if alpha < 0.5]
    invariance = {
        population_id: {
            "alphas_below_0.5": below_half,
            "reach_at_each": [
                int(results[population_id]["by_alpha"][f"{alpha:.2f}"]["reach"]["dispatched"])
                for alpha in below_half
            ],
            "all_equal": len(
                {
                    int(
                        results[population_id]["by_alpha"][f"{alpha:.2f}"]["reach"][
                            "dispatched"
                        ]
                    )
                    for alpha in below_half
                }
            )
            == 1,
        }
        for population_id in results
    }
    if not all(row["all_equal"] for row in invariance.values()):
        raise SizingError(
            "the reach moved between two alphas below 0.5, which the veto theorem forbids -- "
            "the replay contradicts kb_policy._blend_scores"
        )

    return {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "ledger_commit": LEDGER_COMMIT,
        "ledger_row_sha256": LEDGER_ROW_SHA256,
        "ledger_registration_disclosure": LEDGER_SWEEP_DISCLOSURE,
        "verdict_document": VERDICT_RELPATH,
        "started_at": started_at.isoformat(),
        "registered_constants": {
            "alpha_grid": list(ALPHA_GRID),
            "control_alpha": CONTROL_ALPHA,
            "why_the_grid_spans_both_sides_of_0.5": (
                "0.5 is where the guaranteed margin 1 - 2*alpha inverts; below it a recovered "
                "direct label is the strict unique argmax for EVERY possible supply, at it the "
                "worst case is an exact tie which the controller dispatches, and above it a "
                "supply can outvote the direct label outright"
            ),
            "frozen_cell": {
                "alpha": CONTROL_ALPHA,
                "tau": FROZEN_FUSE.tau,
                "m": FROZEN_FUSE.m,
                "c": FROZEN_FUSE.c,
                "top_l": FROZEN_FUSE.top_l,
                "top_k_per_dimension": FROZEN_TOP_K,
                "w_cos": FROZEN_WEIGHTS.w_cos,
                "w_prior": FROZEN_WEIGHTS.w_prior,
                "w_agree": FROZEN_WEIGHTS.w_agree,
                "policy_config": cf.FROZEN_POLICY_CONFIG_RELPATH,
                "unchanged_by_this_row": True,
            },
            "published_control_reach": {
                population_id: {"count": count, "n": n, "source": source}
                for population_id, (count, n, source) in PUBLISHED_CONTROL_REACH.items()
            },
        },
        "alpha_is_a_post_fusion_parameter": (
            "alpha enters the trajectory ONLY at the blend head, strictly AFTER recall, rank and "
            "fuse. The admitted set, the supply, the supplied targets and every gold position are "
            "therefore ALPHA-INVARIANT by construction, and the ONLY thing a moved alpha can "
            "change is the retain/dispatch decision. That is why this sweep replays the supply "
            "once and evaluates the registered blend head six times, rather than the reverse"
        ),
        "post_hoc_additions_declared": {
            "fused_gap_profile_POST_HOC": (
                "the registered reach table came back FLAT from alpha 0.50 to alpha 0.65 on "
                "EVERY population. This diagnostic reports the distribution of the single scalar "
                "that decides the blend -- max_rival fused(rival) minus fused(direct) -- so the "
                "shape of the registered table is readable off the data rather than asserted. It "
                "was added AFTER the registered quantities were computed, introduces no outcome "
                "measure, and carries no verdict. It is declared here rather than folded "
                "silently into the registered set"
            )
        },
        "sources": {"slurp": slurp_sources, "audio2tool": a2t_sources},
        "populations": results,
        "veto_invariance_below_half": invariance,
        "trade_beyond_accuracy": TRADE_BEYOND_ACCURACY,
        "adverse_prior": ADVERSE_PRIOR,
        "hard_stop": HARD_STOP,
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
                "pid 38623 on port 8090 was treated as COLD and was not started, stopped, probed, "
                "reconfigured or contacted"
            ),
            "new_dependencies_installed": 0,
        },
        "wall_seconds": time.perf_counter() - started,
        "scope": (
            "DECISION SIZING for an OPEN OWNER DECISION. THIS ROW SIZES A DECISION AND DOES NOT "
            "TAKE IT: no knob is changed, no line under rails/, core/ or configs/ is written, "
            "alpha stays 0.45 in the frozen cell, nothing hash-pinned moves, no receipt is "
            "displaced, no arm is re-flown, no new sample is touched and no new gold surface is "
            "opened."
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
