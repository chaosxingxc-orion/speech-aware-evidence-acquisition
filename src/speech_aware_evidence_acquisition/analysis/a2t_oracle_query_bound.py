"""THE AUDIO2TOOL ORACLE-QUERY UPPER BOUND -- if the retrieval query were
maximally informative, would the gold value actually be SUPPLIED under the
locked cell? Computed arithmetically at ZERO CONTACTS.

Row ``SAEA-SN-MF-A2T-ORACLE-QUERY-BOUND`` (model-free-check), registered in
``docs/exposure-ledger.md`` BEFORE any number here was computed (``fed9a79c``).

THIS MODULE COMPUTES AN ORACLE AND NOTHING ELSE. Every query it builds uses
the trajectory's own GOLD TOOL identity -- information no runtime query could
legally have. Every number it produces therefore bounds the
"make the retrieval query better" direction from ABOVE. Nothing here is a
proposal, a method, a knob recommendation or a claim about achievable
accuracy. Its only job is to make a refutation cheap: if even the oracle
cannot deliver the gold value under the locked cell, the direction is dead
without spending a single contact.

THE QUESTION, STATED FIRST. The landed gold-absence diagnosis
(``docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md``) established that
of the 15 dispatched Audio2Tool trajectories, 11 received a supply carrying no
value of their gold tool; that all 11 are RANKING defects rather than BUILD
defects (the gold tool sits in the pinned snapshot with 144-189 values every
time); that no window depth reaches them under the locked ``top_l`` = 3; that 9
of the 11 are refused by the ``tau`` = 0.65 percept gate at a best gold-bearing
facet cosine of 0.565332-0.635625; and that the reason those cosines are low is
that the retrieval key on this subgroup is nearly a CONSTANT -- 15 trajectories,
5 distinct query vectors, 11 sharing the embedding of an empty tool call. The
open question is whether a better key would have converted, and it is the
question that decides whether any contact should be spent on the direction.

WHY THE ORACLE IS BUILT FROM KB VECTORS RATHER THAN THE UTTERANCE. The natural
oracle query is the embedding of the trajectory's OWN invocation utterance. That
vector does not exist on disk and this row may take no embedding contact:
``rails.knowledge_build_a2t.propose_partition`` reserves every evaluation item's
whole ``query_idx`` BLOCK out of the construction pool, and the flight embedded
contact-0 ANSWERS, never utterances. :func:`utterance_leak_check` MEASURES the
first clause rather than trusting it: 0 of 104 evaluation UNITS are in the KB,
and the 6 of 104 evaluation utterance TEXTS that do carry a verbatim KB twin
(two different ``query_idx`` blocks with the same string, which the block check
does not forbid) are all ``tier8_intent_blending`` and none of them is among the
15 dispatched trajectories this row measures. The oracle is therefore built from the gold tool's own landed
content-facet vectors -- embeddings of OTHER utterances that invoke the same
gold tool -- and that substitution is stated wherever a number is cited.

THE FOUR ORACLE QUERIES, all from already-landed vectors:

* **O1 ORACLE-SELF, the LEAKY ceiling.** Query = the landed vector of the
  gold-bearing content facet the diagnosis measured against the flown key, with
  the whole KB retrievable. That query IS a KB entry, so it retrieves itself at
  cosine 1.0. Reported as a leaky ceiling; it is NOT the bound.
* **O2 ORACLE-LOO, the HONEST bound.** The same query with that facet WITHHELD
  from the retrievable pool. This is the faithful simulation of the real
  decontaminated condition: on all 15 dispatched trajectories a legal query
  cannot match itself, because the utterance it would embed is not in the KB
  (measured, see above).
* **O3 ORACLE-BEST-LOO, the SUPREMUM over same-tool utterance queries, and THE
  HEADLINE.** For EVERY vectored content facet whose value's ``task_target`` is
  the gold tool, replay O2's construction with that facet as the query and
  withheld from the pool. The trajectory counts as gold-supplied if ANY of them
  delivers the gold value.
* **O4 ORACLE-CENTROID.** Query = the L2-normalized mean of all the gold tool's
  vectored content-facet vectors. Not a KB entry, so no exact self-match.

TWO LOWER CONSTRUCTIONS, both fixed in the registration:

* **N1 TIER-PROTOTYPE** -- a NON-oracle, runtime-legal query: the normalized
  mean of the vectored content facets of the KB units in the trajectory's own
  tier, which the sample id alone determines and which uses no gold at all.
* **N2 MIXING SENSITIVITY** -- the smallest ``lambda`` on a fixed grid at which
  the normalized mixture of the flown key and the O2 oracle direction delivers
  the gold value. A SENSITIVITY, explicitly not a bound. Its ``lambda`` = 0 cell
  is also a self-check: it must reproduce the as-flown supply exactly.

REUSE, NEVER REIMPLEMENTATION. Loading, replay, the fidelity gate and the gold
coverage block are imported from
:mod:`.cross_carrier_ceiling_decomposition`; the full-KB geometry and its
``kb_policy._cosine`` probe come from :mod:`.a2t_gold_absence_diagnosis`; recall
is :func:`.contrast_fewshot_preanalysis.vectorised_recall`, cross-checked
against REAL ``kb.multidim_recall`` calls; ranking, admission and fusion are
``rails.kb_policy``'s own registered ranker and fuser through
:func:`.dev100_damage_channel_analysis.replay_supply` at the locked knobs.

GOLD IS SCORING-SIDE ONLY. It is read from sealed records after the seal, never
on a runtime path. The oracle query vectors built here are analysis objects and
are never handed to a flown controller. The A2T-G1-104 subset is EXPOSED and its
seal was already broken by the landed G1 read; every statistic on it is a
secondary reading.

WHAT IT DOES NOT DO. It changes no knob and writes nothing under ``configs/``,
``rails/`` or ``core/``. It opens no model session, no embedding sidecar and no
tokenizer: :func:`run` arms ``dev100_reviewer_audit.arm_offline_guard`` BEFORE
the first input is opened and writes the recorded outbound-attempt count into
the receipt. The resident np2 A2T service on port 8090 is never contacted.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=<repo>/src \
      python -m speech_aware_evidence_acquisition.analysis.a2t_oracle_query_bound \
        --repo-root <repo> --data-root $SPEECHRL_DATA_DIR --out <receipt>
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Mapping, Sequence

from . import a2t_admission_scale_sweep as sweep
from . import a2t_gold_absence_diagnosis as diag
from . import contrast_fewshot_preanalysis as cf
from . import cross_carrier_ceiling_decomposition as ccd
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as audit
from ..rails import kb_policy as kb

EXPOSURE_ROW_ID = "SAEA-SN-MF-A2T-ORACLE-QUERY-BOUND"
SCHEMA = "saea-a2t-oracle-query-bound-v1"

FROZEN_ALPHA = ccd.FROZEN_ALPHA
FROZEN_WEIGHTS = ccd.FROZEN_WEIGHTS
FROZEN_FUSE = ccd.FROZEN_FUSE
FROZEN_TOP_K = ccd.FROZEN_TOP_K

#: The mixing grid for N2, fixed in the registration before the module ran.
LAMBDA_GRID: tuple[float, ...] = tuple(round(0.1 * step, 1) for step in range(11))

#: The landed tau band the fidelity gate must reproduce, quoted from
#: ``docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md`` section 3.2 and
#: ``docs/readiness/2026-08-25-query-key-degeneracy-cross-carrier.md``.
LANDED_TAU_BAND = (0.565332, 0.635625)

#: The landed dispatch split the fidelity gate must reproduce.
LANDED_DISPATCHED_N = 15
LANDED_GOLD_BEARING_N = 4
LANDED_GOLD_ABSENT_N = 11

#: The decision rule, fixed in the registration BEFORE any number was seen.
REFUTED_AT_OR_BELOW = 1
SURVIVES_AT_OR_ABOVE = 8

#: NEAR-DUPLICATE THRESHOLD -- chosen AFTER the first run, and labelled as such
#: everywhere it appears. The first run showed that 6 of the 11 gold-absent
#: trajectories have an O3 maximum at a best-other-gold cosine of exactly
#: 1.0000000000, i.e. the withheld query facet has an EXACT twin elsewhere in
#: the KB, so O3's "self-excluded" property is defeated by duplication rather
#: than by retrieval. The stratification below re-reads the SAME O3 loop with
#: every query that owns such a twin removed. It is a ROBUSTNESS
#: stratification of the pre-registered O3 block, never a replacement for it,
#: and it can only make the headline weaker or equal.
NEAR_DUPLICATE_COSINE = 0.99


class OracleBoundError(RuntimeError):
    """Raised when a pre-registered stop condition fails."""


# ---------------------------------------------------------------------------
# Pure vector helpers -- unit-testable without any landed byte
# ---------------------------------------------------------------------------


def l2_normalize(vector: Sequence[float]) -> tuple[float, ...]:
    """Unit-length copy of ``vector``.

    Cosine is invariant to the query's norm, so normalising changes nothing on
    its own; it exists so that MIXTURES of two vectors weight the two
    directions rather than the two magnitudes."""

    import math

    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if norm <= 0.0:
        raise OracleBoundError("l2_normalize: refusing to normalise a zero vector")
    return tuple(value / norm for value in values)


def mix_directions(
    left: Sequence[float], right: Sequence[float], weight: float
) -> tuple[float, ...]:
    """``(1 - weight)`` of ``left``'s direction plus ``weight`` of ``right``'s.

    Both sides are unit-normalised first, so ``weight`` is a mixture of
    DIRECTIONS and never an accident of one side's magnitude. ``weight`` = 0
    returns ``left``'s direction exactly and ``weight`` = 1 returns
    ``right``'s, which is what makes the ``lambda`` = 0 cell of N2 a self-check
    against the as-flown supply."""

    if not (0.0 <= float(weight) <= 1.0):
        raise OracleBoundError("mix_directions: weight must lie in [0, 1]")
    left_unit = l2_normalize(left)
    right_unit = l2_normalize(right)
    if len(left_unit) != len(right_unit):
        raise OracleBoundError("mix_directions: dimension mismatch")
    blended = [
        (1.0 - float(weight)) * a + float(weight) * b
        for a, b in zip(left_unit, right_unit)
    ]
    return l2_normalize(blended)


def classify_binding_stage(
    *,
    gold_supplied: bool,
    has_vectored_gold_facet: bool,
    best_gold_cosine: float | None,
    gold_facet_position: int | None,
    gold_facet_in_admitted_window: bool,
    gold_target_rank_among_tau_passing: int | None,
    tau: float = FROZEN_FUSE.tau,
    top_k: int = FROZEN_TOP_K,
    top_l: int = FROZEN_FUSE.top_l,
) -> dict[str, object]:
    """Name the FIRST stage that keeps the gold value out of the supply.

    The stages are ordered as the pipeline orders them: the KB must contain a
    vectored gold facet at all (a DATA property); its cosine must clear the
    ``tau`` percept gate (the bar is a KNOB, the cosine is DATA); it must fall
    inside the recall/ranker window ``k`` = ``m`` (a KNOB); and its TARGET must
    fall inside the ``top_l`` target budget (a KNOB).

    ``c`` cannot bind for the gold-TARGET criterion and that is structural, not
    empirical: on this carrier each content facet is associated with exactly one
    value, so once the gold target is inside ``top_l`` at least one of its values
    is always selected, whatever ``c`` is. The classification says so rather than
    leaving ``c`` as a silent possibility."""

    if gold_supplied:
        return {"stage": "supplied", "kind": None, "detail": "no stage binds"}
    if not has_vectored_gold_facet:
        return {
            "stage": "kb_coverage",
            "kind": "data",
            "detail": "the gold tool has no vectored content facet in the pinned snapshot",
        }
    if best_gold_cosine is None or best_gold_cosine < tau:
        return {
            "stage": "tau_gate",
            "kind": "data-against-a-knob",
            "detail": (
                f"the best gold-bearing facet scores {best_gold_cosine} against the "
                f"locked tau = {tau}; the percept gate refuses it at EVERY window "
                "depth, so no value of k or m is a fix. The bar is a knob of the "
                "locked cell; the cosine is a property of the data"
            ),
        }
    if gold_facet_position is None or gold_facet_position > top_k:
        return {
            "stage": "recall_depth_k",
            "kind": "knob",
            "detail": (
                f"the best gold-bearing facet clears tau but enters the recall "
                f"ordering only at position {gold_facet_position}, outside the "
                f"locked k = m = {top_k} window"
            ),
        }
    if not gold_facet_in_admitted_window:
        return {
            "stage": "recall_depth_k",
            "kind": "knob",
            "detail": (
                "the best gold-bearing facet clears tau and sits inside the recall "
                "window but is not in the admitted top-m set"
            ),
        }
    if (
        gold_target_rank_among_tau_passing is None
        or gold_target_rank_among_tau_passing > top_l
    ):
        return {
            "stage": "top_l_target_budget",
            "kind": "knob",
            "detail": (
                "the gold facet is admitted but its TARGET ranks "
                f"{gold_target_rank_among_tau_passing} among tau-passing targets, "
                f"outside the locked top_l = {top_l} target budget"
            ),
        }
    return {
        "stage": "unclassified",
        "kind": None,
        "detail": (
            "every named stage passes yet the gold value is absent; this must be "
            "reported rather than attributed"
        ),
    }


def decision_rule(gold_supplied: int, total: int) -> dict[str, object]:
    """The decision rule, fixed in the registration before any number was seen.

    ``<= 1`` of the gold-absent trajectories refutes the direction at zero cost;
    ``>= 8`` lets it survive this rung while authorizing nothing; anything in
    between is inconclusive."""

    if gold_supplied <= REFUTED_AT_OR_BELOW:
        outcome = "REFUTED"
        verdict = (
            f"{gold_supplied} of {total} gold-absent trajectories become "
            "gold-supplied even under an ORACLE query. The "
            "query-improvement direction is REFUTED AT ZERO COST on this "
            "carrier and no contacts should be spent on it"
        )
    elif gold_supplied >= SURVIVES_AT_OR_ABOVE:
        outcome = "SURVIVES"
        verdict = (
            f"{gold_supplied} of {total} gold-absent trajectories become "
            "gold-supplied under an ORACLE query. The direction SURVIVES this "
            "rung. Surviving AUTHORIZES NOTHING by itself: this is only an "
            "upper bound, and the K3 trap remains -- any fix that improves the "
            "query by making the ANSWER better recovers a direct label and the "
            "alpha veto then suppresses dispatch, projected 15/104 to 3/104, "
            "-80 percent"
        )
    else:
        outcome = "INCONCLUSIVE"
        verdict = (
            f"{gold_supplied} of {total} gold-absent trajectories become "
            "gold-supplied under an ORACLE query -- neither the refutation "
            "band (<= 1) nor the survival band (>= 8). INCONCLUSIVE"
        )
    return {
        "gold_supplied_under_the_oracle": gold_supplied,
        "of": total,
        "outcome": outcome,
        "verdict": verdict,
        "bands_fixed_in_the_registration": {
            "refuted_at_or_below": REFUTED_AT_OR_BELOW,
            "survives_at_or_above": SURVIVES_AT_OR_ABOVE,
            "inconclusive_between": [REFUTED_AT_OR_BELOW + 1, SURVIVES_AT_OR_ABOVE - 1],
        },
    }


# ---------------------------------------------------------------------------
# One oracle replay
# ---------------------------------------------------------------------------


def _mask_withheld(cosines, bundle, withhold: Sequence[str]):
    """Withhold facets from the retrievable pool by pushing them below every
    real cosine, so ``vectorised_recall``'s own ordering never reaches them."""

    import numpy as np

    if not withhold:
        return cosines
    masked = np.array(cosines, dtype=np.float64, copy=True)
    for facet_id in withhold:
        index = bundle.facet_index.get(facet_id)
        if index is not None:
            masked[int(index)] = -1.0
    return masked


def oracle_replay(
    carrier: ccd.A2TAttempt4,
    sample_id: str,
    cosines,
    *,
    withhold: Sequence[str] = (),
) -> dict[str, object]:
    """Replay recall -> rank -> admit -> fuse at the LOCKED knobs over one
    query's full-KB cosine vector, and measure every stage.

    ``cosines`` is the vectorised full-KB cosine sweep for the query under test;
    ranking, admission and fusion are ``kb_policy``'s own registered functions
    through :func:`dc.replay_supply`, so nothing about the pipeline changes."""

    import numpy as np

    bundle = carrier.bundle
    gold = carrier.gold_primary[sample_id]
    masked = _mask_withheld(cosines, bundle, withhold)
    order = np.lexsort((np.asarray(bundle.facet_id_rank), -masked))

    recall_scores = cf.vectorised_recall(bundle, masked, top_k=FROZEN_TOP_K)
    supply = dc.replay_supply(
        carrier.inputs,
        sample_id,
        weights=FROZEN_WEIGHTS,
        knobs=FROZEN_FUSE,
        top_k=FROZEN_TOP_K,
        recall_scores=recall_scores,
    )

    gold_indices = bundle.facet_indices_by_target.get(gold)
    withheld = set(withhold)
    best_gold_cosine: float | None = None
    best_gold_facet: str | None = None
    if gold_indices is not None and len(gold_indices) > 0:
        for index in np.asarray(gold_indices):
            facet_id = bundle.facet_ids[int(index)]
            if facet_id in withheld:
                continue
            score = float(masked[int(index)])
            if best_gold_cosine is None or score > best_gold_cosine:
                best_gold_cosine = score
                best_gold_facet = facet_id

    gold_position: int | None = None
    for rank_position, index in enumerate(order, start=1):
        facet_id = bundle.facet_ids[int(index)]
        if facet_id in withheld:
            continue
        if bundle.content_facet_target.get(facet_id) == gold:
            gold_position = rank_position
            break

    admitted = set(supply.admitted_facet_ids)
    gold_facet_admitted = any(
        bundle.content_facet_target.get(facet_id) == gold for facet_id in admitted
    )

    best_by_target: dict[str, float] = {}
    passing = np.nonzero(masked >= FROZEN_FUSE.tau)[0]
    for index in passing:
        facet_id = bundle.facet_ids[int(index)]
        if facet_id in withheld:
            continue
        target = bundle.content_facet_target.get(facet_id)
        if target is None:
            continue
        score = float(masked[int(index)])
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

    supplied_targets = tuple(
        sorted(
            {
                str(bundle.values_by_id[value_id].task_target)
                for value_id in supply.selected_value_ids
                if bundle.values_by_id[value_id].task_target is not None
            }
        )
    )
    gold_supplied = gold in supplied_targets

    binding = classify_binding_stage(
        gold_supplied=gold_supplied,
        has_vectored_gold_facet=best_gold_facet is not None,
        best_gold_cosine=best_gold_cosine,
        gold_facet_position=gold_position,
        gold_facet_in_admitted_window=gold_facet_admitted,
        gold_target_rank_among_tau_passing=gold_target_rank,
    )

    return {
        "sample_id": sample_id,
        "gold_primary_tool": gold,
        "withheld_facet_ids": tuple(sorted(withheld)),
        "best_gold_bearing_facet_id": best_gold_facet,
        "best_gold_bearing_facet_cosine": best_gold_cosine,
        "gold_facet_clears_tau_0_65": (
            best_gold_cosine is not None and best_gold_cosine >= FROZEN_FUSE.tau
        ),
        "gold_facet_recall_position": gold_position,
        "gold_facet_inside_admitted_window": gold_facet_admitted,
        "gold_target_rank_among_tau_passing": gold_target_rank,
        "tau_passing_targets_total": len(ranked_targets),
        "top1_cosine": float(masked[int(order[0])]),
        "supplied_targets": supplied_targets,
        "supplied_value_count": len(supply.selected_value_ids),
        "gold_supplied": gold_supplied,
        "binding_stage": binding,
    }


def _facet_cosines(matrix, facet_norms, index: int):
    """Full-KB cosine sweep for a query that IS one of the landed facet
    vectors, taken straight from the landed matrix -- no vector is constructed
    from text and nothing is embedded."""

    import numpy as np

    query = np.asarray(matrix[int(index)], dtype=np.float64)
    denominator = facet_norms * float(np.linalg.norm(query))
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denominator > 0.0, matrix @ query / denominator, 0.0)


# ---------------------------------------------------------------------------
# The oracle blocks
# ---------------------------------------------------------------------------


def oracle_bound(
    carrier: ccd.A2TAttempt4,
    geometry: Mapping[str, diag.SampleGeometry],
    dispatched: Sequence[str],
    gold_absent: Sequence[str],
) -> dict[str, object]:
    """O1 / O2 / O3 / O4 for every dispatched trajectory."""

    import numpy as np

    bundle = carrier.bundle
    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)

    rows: list[dict[str, object]] = []
    for sample_id in sorted(dispatched):
        geo = geometry[sample_id]
        gold = geo.gold_primary
        gold_indices = [
            int(index)
            for index in np.asarray(bundle.facet_indices_by_target.get(gold, ()))
        ]
        if not gold_indices:
            raise OracleBoundError(
                f"{sample_id}: the gold tool has no vectored content facet, which "
                "contradicts the landed diagnosis (0 BUILD defects)"
            )

        anchor_facet = geo.gold_facet_id
        if anchor_facet is None:
            raise OracleBoundError(
                f"{sample_id}: no gold-bearing facet under the flown key, which "
                "contradicts the landed diagnosis"
            )
        anchor_index = bundle.facet_index[anchor_facet]
        anchor_cosines = _facet_cosines(matrix, facet_norms, anchor_index)

        o1 = oracle_replay(carrier, sample_id, anchor_cosines)
        o2 = oracle_replay(
            carrier, sample_id, anchor_cosines, withhold=(anchor_facet,)
        )

        # O3 -- the supremum over same-tool utterance queries, self-excluded.
        best_o3: dict[str, object] | None = None
        best_o3_no_twin: dict[str, object] | None = None
        o3_supplied_count = 0
        o3_twin_queries = 0
        o3_no_twin_tried = 0
        o3_no_twin_supplied = 0
        for index in gold_indices:
            facet_id = bundle.facet_ids[index]
            cosines = _facet_cosines(matrix, facet_norms, index)
            outcome = oracle_replay(
                carrier, sample_id, cosines, withhold=(facet_id,)
            )
            outcome = dict(outcome)
            outcome["oracle_query_facet_id"] = facet_id
            best_other = float(outcome["best_gold_bearing_facet_cosine"] or -1.0)
            has_twin = best_other >= NEAR_DUPLICATE_COSINE
            outcome["query_has_a_near_duplicate_twin"] = has_twin
            if outcome["gold_supplied"]:
                o3_supplied_count += 1
            if has_twin:
                o3_twin_queries += 1
            else:
                o3_no_twin_tried += 1
                if outcome["gold_supplied"]:
                    o3_no_twin_supplied += 1
                incumbent_no_twin = (
                    (False, -1.0)
                    if best_o3_no_twin is None
                    else (
                        bool(best_o3_no_twin["gold_supplied"]),
                        float(
                            best_o3_no_twin["best_gold_bearing_facet_cosine"] or -1.0
                        ),
                    )
                )
                if (bool(outcome["gold_supplied"]), best_other) > incumbent_no_twin:
                    best_o3_no_twin = outcome
            if best_o3 is None:
                best_o3 = outcome
            else:
                incumbent = (
                    bool(best_o3["gold_supplied"]),
                    float(best_o3["best_gold_bearing_facet_cosine"] or -1.0),
                )
                if (bool(outcome["gold_supplied"]), best_other) > incumbent:
                    best_o3 = outcome
        assert best_o3 is not None

        centroid = l2_normalize(
            np.asarray(matrix[gold_indices], dtype=np.float64).mean(axis=0).tolist()
        )
        o4 = oracle_replay(
            carrier, sample_id, diag._cosines(matrix, facet_norms, centroid)
        )

        rows.append(
            {
                "sample_id": sample_id,
                "gold_primary_tool": gold,
                "gold_absent_as_flown": sample_id in set(gold_absent),
                "kb_vectored_facets_for_gold": len(gold_indices),
                "as_flown": {
                    "best_gold_bearing_facet_cosine": geo.gold_facet_cosine,
                    "gold_facet_recall_position": geo.gold_facet_position,
                    "gold_facet_clears_tau_0_65": geo.gold_facet_passes_tau,
                    "gold_target_rank_among_tau_passing": (
                        geo.gold_target_rank_by_best_cosine
                    ),
                    "top1_cosine": geo.top1_cosine,
                },
                "O1_oracle_self_LEAKY": o1,
                "O2_oracle_leave_one_out_HONEST": o2,
                "O3_oracle_best_leave_one_out_HEADLINE": best_o3,
                "O3_gold_tool_facets_that_deliver_gold": o3_supplied_count,
                "O3_gold_tool_facets_tried": len(gold_indices),
                "O3_delivery_rate_over_same_tool_sibling_queries": (
                    o3_supplied_count / len(gold_indices)
                ),
                "O3_TWIN_STRATIFICATION_post_registration": {
                    "queries_with_a_near_duplicate_twin": o3_twin_queries,
                    "queries_without_a_near_duplicate_twin": o3_no_twin_tried,
                    "delivered_without_a_near_duplicate_twin": o3_no_twin_supplied,
                    "delivery_rate_without_a_near_duplicate_twin": (
                        o3_no_twin_supplied / o3_no_twin_tried
                        if o3_no_twin_tried
                        else None
                    ),
                    "gold_supplied_by_some_twin_free_query": (
                        best_o3_no_twin is not None
                        and bool(best_o3_no_twin["gold_supplied"])
                    ),
                    "best_twin_free_query": best_o3_no_twin,
                },
                "O4_oracle_centroid": o4,
            }
        )

    def _count(key: str, ids: Sequence[str]) -> int:
        wanted = set(ids)
        return sum(
            1
            for row in rows
            if row["sample_id"] in wanted and row[key]["gold_supplied"]  # type: ignore[index]
        )

    absent = list(gold_absent)
    summary = {
        "dispatched_n": len(rows),
        "gold_absent_n": len(absent),
        "O1_gold_supplied_of_the_gold_absent": _count("O1_oracle_self_LEAKY", absent),
        "O2_gold_supplied_of_the_gold_absent": _count(
            "O2_oracle_leave_one_out_HONEST", absent
        ),
        "O3_gold_supplied_of_the_gold_absent": _count(
            "O3_oracle_best_leave_one_out_HEADLINE", absent
        ),
        "O4_gold_supplied_of_the_gold_absent": _count("O4_oracle_centroid", absent),
        "O1_gold_supplied_of_all_dispatched": _count(
            "O1_oracle_self_LEAKY", [row["sample_id"] for row in rows]
        ),
        "O2_gold_supplied_of_all_dispatched": _count(
            "O2_oracle_leave_one_out_HONEST", [row["sample_id"] for row in rows]
        ),
        "O3_gold_supplied_of_all_dispatched": _count(
            "O3_oracle_best_leave_one_out_HEADLINE",
            [row["sample_id"] for row in rows],
        ),
        "O4_gold_supplied_of_all_dispatched": _count(
            "O4_oracle_centroid", [row["sample_id"] for row in rows]
        ),
    }

    absent_rows = [row for row in rows if row["sample_id"] in set(absent)]
    for key, label in (
        ("O2_oracle_leave_one_out_HONEST", "O2"),
        ("O3_oracle_best_leave_one_out_HEADLINE", "O3"),
    ):
        cosines = [
            float(row[key]["best_gold_bearing_facet_cosine"])  # type: ignore[index]
            for row in absent_rows
            if row[key]["best_gold_bearing_facet_cosine"] is not None  # type: ignore[index]
        ]
        summary[f"{label}_gold_facet_cosine_min"] = min(cosines) if cosines else None
        summary[f"{label}_gold_facet_cosine_median"] = (
            statistics.median(cosines) if cosines else None
        )
        summary[f"{label}_gold_facet_cosine_max"] = max(cosines) if cosines else None
        summary[f"{label}_gold_facet_clears_tau"] = sum(
            1
            for row in absent_rows
            if row[key]["gold_facet_clears_tau_0_65"]  # type: ignore[index]
        )

    binding: dict[str, int] = {}
    for row in absent_rows:
        stage = str(
            row["O3_oracle_best_leave_one_out_HEADLINE"]["binding_stage"]["stage"]  # type: ignore[index]
        )
        binding[stage] = binding.get(stage, 0) + 1
    summary["O3_binding_stage_histogram_over_the_gold_absent"] = binding

    for key, label in (
        ("O2_oracle_leave_one_out_HONEST", "O2"),
        ("O1_oracle_self_LEAKY", "O1"),
        ("O4_oracle_centroid", "O4"),
    ):
        stages: dict[str, int] = {}
        for row in absent_rows:
            stage = str(row[key]["binding_stage"]["stage"])  # type: ignore[index]
            stages[stage] = stages.get(stage, 0) + 1
        summary[f"{label}_binding_stage_histogram_over_the_gold_absent"] = stages

    delivered = sum(
        int(row["O3_gold_tool_facets_that_deliver_gold"]) for row in absent_rows
    )
    tried = sum(int(row["O3_gold_tool_facets_tried"]) for row in absent_rows)
    rates = [
        float(row["O3_delivery_rate_over_same_tool_sibling_queries"])
        for row in absent_rows
    ]
    summary["O3_RATE_pooled_delivered"] = delivered
    summary["O3_RATE_pooled_tried"] = tried
    summary["O3_RATE_pooled"] = delivered / tried if tried else None
    summary["O3_RATE_per_trajectory_min"] = min(rates) if rates else None
    summary["O3_RATE_per_trajectory_median"] = (
        statistics.median(rates) if rates else None
    )
    summary["O3_RATE_per_trajectory_max"] = max(rates) if rates else None

    strat = [
        row["O3_TWIN_STRATIFICATION_post_registration"] for row in absent_rows
    ]
    twin_delivered = sum(
        int(block["delivered_without_a_near_duplicate_twin"]) for block in strat  # type: ignore[index]
    )
    twin_tried = sum(
        int(block["queries_without_a_near_duplicate_twin"]) for block in strat  # type: ignore[index]
    )
    summary["O3_TWIN_FREE_gold_supplied_of_the_gold_absent"] = sum(
        1 for block in strat if block["gold_supplied_by_some_twin_free_query"]  # type: ignore[index]
    )
    summary["O3_TWIN_FREE_pooled_delivered"] = twin_delivered
    summary["O3_TWIN_FREE_pooled_tried"] = twin_tried
    summary["O3_TWIN_FREE_pooled_rate"] = (
        twin_delivered / twin_tried if twin_tried else None
    )
    summary["O3_maxima_at_an_exact_twin"] = sum(
        1
        for row in absent_rows
        if float(
            row["O3_oracle_best_leave_one_out_HEADLINE"][  # type: ignore[index]
                "best_gold_bearing_facet_cosine"
            ]
            or -1.0
        )
        >= NEAR_DUPLICATE_COSINE
    )
    summary["near_duplicate_cosine_threshold_POST_REGISTRATION"] = (
        NEAR_DUPLICATE_COSINE
    )

    return {
        "oracle_warning": (
            "EVERY QUERY IN THIS BLOCK IS AN ORACLE. It is built from the "
            "trajectory's own GOLD TOOL identity, which no runtime query could "
            "legally have, so every count here BOUNDS THE DIRECTION FROM ABOVE "
            "and is not a proposal, a method or an achievable accuracy"
        ),
        "identity_leak_note": (
            "O1's query IS a KB entry and therefore retrieves ITSELF at cosine "
            "1.0. O2, O3 and O4 are the self-excluded constructions and O3 is "
            "the honest bound. None of the 15 dispatched trajectories this row "
            "measures can self-match, and that is MEASURED in "
            "utterance_leak_check rather than inferred: 0 of 104 evaluation "
            "UNITS are in the KB (the block decontamination in "
            "rails.knowledge_build_a2t.propose_partition), and the 6 of 104 "
            "evaluation utterance TEXTS that do have a verbatim KB twin are "
            "all tier8_intent_blending, 0 of them dispatched"
        ),
        "twin_stratification_note": (
            "POST-REGISTRATION AND LABELLED AS SUCH. O3's self-exclusion "
            "withholds the query facet itself, but the first run showed that "
            "several gold tools carry EXACT DUPLICATE utterances, so a "
            "withheld facet can still be matched at cosine 1.0 by its own twin "
            "-- identity leak by duplication rather than by self-match. The "
            f"O3_TWIN_* fields re-read the SAME O3 loop with the {NEAR_DUPLICATE_COSINE} "
            "threshold applied to every query's best OTHER gold-bearing cosine. "
            "The threshold was chosen after the numbers were seen; the "
            "stratification can only make the headline weaker or equal, and it "
            "never replaces the pre-registered O3 count"
        ),
        "gold_value_criterion": (
            "a trajectory is GOLD-SUPPLIED when some selected value's "
            "task_target is its gold PRIMARY tool -- the same criterion "
            "cross_carrier_ceiling_decomposition.gold_coverage uses. The "
            "trajectory's OWN gold value does not exist in the KB by "
            "decontamination, so a value-id criterion would be vacuous"
        ),
        "per_sample": rows,
        "summary": summary,
    }


def lower_constructions(
    carrier: ccd.A2TAttempt4,
    geometry: Mapping[str, diag.SampleGeometry],
    dispatched: Sequence[str],
    gold_absent: Sequence[str],
) -> dict[str, object]:
    """N1 (tier prototype, non-oracle) and N2 (the mixing sensitivity)."""

    import numpy as np

    bundle = carrier.bundle
    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)

    tier_indices: dict[str, list[int]] = {}
    for position, facet_id in enumerate(bundle.facet_ids):
        parts = facet_id.split(":")
        if len(parts) >= 4 and parts[0] == "facet" and parts[1] == "content":
            tier_indices.setdefault(parts[2], []).append(position)

    rows: list[dict[str, object]] = []
    for sample_id in sorted(dispatched):
        geo = geometry[sample_id]
        tier = sample_id.split(":", 1)[0]
        indices = tier_indices.get(tier, [])
        n1: dict[str, object] | None = None
        if indices:
            prototype = l2_normalize(
                np.asarray(matrix[indices], dtype=np.float64).mean(axis=0).tolist()
            )
            n1 = oracle_replay(
                carrier, sample_id, diag._cosines(matrix, facet_norms, prototype)
            )
            n1 = dict(n1)
            n1["tier"] = tier
            n1["tier_facets_averaged"] = len(indices)

        anchor_facet = geo.gold_facet_id
        assert anchor_facet is not None
        anchor_index = bundle.facet_index[anchor_facet]
        flown = carrier.inputs.query_vectors[sample_id]
        oracle_direction = tuple(float(v) for v in matrix[anchor_index].tolist())

        smallest: float | None = None
        ladder: list[dict[str, object]] = []
        for weight in LAMBDA_GRID:
            query = mix_directions(flown, oracle_direction, weight)
            outcome = oracle_replay(
                carrier,
                sample_id,
                diag._cosines(matrix, facet_norms, query),
                withhold=(anchor_facet,),
            )
            ladder.append(
                {
                    "lambda": weight,
                    "best_gold_bearing_facet_cosine": outcome[
                        "best_gold_bearing_facet_cosine"
                    ],
                    "gold_supplied": outcome["gold_supplied"],
                    "supplied_targets": outcome["supplied_targets"],
                }
            )
            if smallest is None and outcome["gold_supplied"]:
                smallest = weight

        rows.append(
            {
                "sample_id": sample_id,
                "gold_primary_tool": geo.gold_primary,
                "gold_absent_as_flown": sample_id in set(gold_absent),
                "N1_tier_prototype": n1,
                "N2_smallest_lambda_that_supplies_gold": smallest,
                "N2_ladder": ladder,
            }
        )

    absent = set(gold_absent)
    n1_stages: dict[str, int] = {}
    n1_cosines: list[float] = []
    n1_clears_tau = 0
    for row in rows:
        block = row["N1_tier_prototype"]
        if block is None:
            continue
        stage = str(block["binding_stage"]["stage"])  # type: ignore[index]
        n1_stages[stage] = n1_stages.get(stage, 0) + 1
        cosine = block["best_gold_bearing_facet_cosine"]  # type: ignore[index]
        if cosine is not None:
            n1_cosines.append(float(cosine))
        if block["gold_facet_clears_tau_0_65"]:  # type: ignore[index]
            n1_clears_tau += 1
    n1_absent = sum(
        1
        for row in rows
        if row["sample_id"] in absent
        and row["N1_tier_prototype"] is not None
        and row["N1_tier_prototype"]["gold_supplied"]  # type: ignore[index]
    )
    reached = [
        float(row["N2_smallest_lambda_that_supplies_gold"])
        for row in rows
        if row["sample_id"] in absent
        and row["N2_smallest_lambda_that_supplies_gold"] is not None
    ]
    return {
        "N1_semantics": (
            "TIER PROTOTYPE, a NON-oracle runtime-legal query: the normalized "
            "mean of the vectored content facets of the KB units in the "
            "trajectory's own tier. The sample id alone determines the tier, so "
            "no gold is used. It carries the correct tier prior and ZERO "
            "information about the individual utterance, which is exactly what "
            "makes it a floor rather than a bound"
        ),
        "N2_semantics": (
            "MIXING SENSITIVITY, explicitly NOT a bound: the smallest lambda at "
            "which the normalized mixture of the flown key and the O2 oracle "
            "direction delivers the gold value, with the oracle facet withheld "
            "throughout. The lambda = 0 cell is a self-check -- it must "
            "reproduce the as-flown supply"
        ),
        "per_sample": rows,
        "summary": {
            "N1_gold_supplied_of_the_gold_absent": n1_absent,
            "N1_gold_supplied_of_all_dispatched": sum(
                1
                for row in rows
                if row["N1_tier_prototype"] is not None
                and row["N1_tier_prototype"]["gold_supplied"]  # type: ignore[index]
            ),
            "N1_binding_stage_histogram": n1_stages,
            "N1_gold_facet_clears_tau_of_all_dispatched": n1_clears_tau,
            "N1_gold_facet_cosine_min": min(n1_cosines) if n1_cosines else None,
            "N1_gold_facet_cosine_median": (
                statistics.median(n1_cosines) if n1_cosines else None
            ),
            "N1_gold_facet_cosine_max": max(n1_cosines) if n1_cosines else None,
            "N2_gold_absent_reached_at_some_lambda": len(reached),
            "N2_smallest_lambda_min": min(reached) if reached else None,
            "N2_smallest_lambda_median": (
                statistics.median(reached) if reached else None
            ),
            "N2_smallest_lambda_max": max(reached) if reached else None,
            "N2_lambda_grid": list(LAMBDA_GRID),
        },
    }


def mixing_self_check(
    carrier: ccd.A2TAttempt4, lower: Mapping[str, object]
) -> dict[str, object]:
    """The ``lambda`` = 0 cell must reproduce the as-flown supply exactly.

    A mixing ladder whose zero end does not land on the flight is measuring
    something other than a perturbation of the flown key, so this is checked
    rather than asserted. It is evaluated with the oracle facet WITHHELD, so a
    disagreement is only recorded where the withheld facet was part of the flown
    supply -- which the check reports rather than hides."""

    matches = 0
    mismatches: list[dict[str, object]] = []
    for row in lower["per_sample"]:  # type: ignore[index]
        sample_id = str(row["sample_id"])
        zero_cell = next(
            cell for cell in row["N2_ladder"] if float(cell["lambda"]) == 0.0
        )
        flown_targets = tuple(
            sorted(
                {
                    str(carrier.bundle.values_by_id[value_id].task_target)
                    for value_id in carrier.flown_supply[sample_id]
                    if carrier.bundle.values_by_id[value_id].task_target is not None
                }
            )
        )
        if tuple(zero_cell["supplied_targets"]) == flown_targets:
            matches += 1
        else:
            mismatches.append(
                {
                    "sample_id": sample_id,
                    "lambda_zero_targets": zero_cell["supplied_targets"],
                    "flown_targets": flown_targets,
                }
            )
    return {
        "lambda_zero_reproduces_the_flown_supply": matches,
        "of": len(lower["per_sample"]),  # type: ignore[arg-type]
        "mismatches": mismatches,
        "semantics": (
            "evaluated with the oracle anchor facet withheld, so a mismatch is "
            "expected exactly where that facet supported the flown supply"
        ),
    }


# ---------------------------------------------------------------------------
# The pre-registered stop conditions
# ---------------------------------------------------------------------------


def utterance_leak_check(
    carrier: ccd.A2TAttempt4,
    *,
    repo_root: Path,
    data_root: Path,
    dispatched: Sequence[str],
) -> dict[str, object]:
    """Is any evaluation utterance itself a KB entry? MEASURED, not inferred.

    The oracle's whole framing rests on the claim that the trajectory's own
    utterance is not in the KB, so a legal query could never self-match. The
    BLOCK decontamination in ``rails.knowledge_build_a2t.propose_partition``
    guarantees that no evaluation UNIT is in the construction pool, but it says
    nothing about two DIFFERENT ``query_idx`` blocks carrying the same text.
    This function measures both, because the first was asserted from source and
    the second was not, and an unmeasured leak would understate the oracle."""

    from ..data.lock import load_lock, umbrella_lock_path
    from ..rails import knowledge_build_a2t as builder

    rows, _report = builder.a2t_pool_rows(
        load_lock(umbrella_lock_path(repo_root)), Path(data_root)
    )
    row_by_sample = {}
    for row in rows:
        for sample_id in row.sample_ids:
            row_by_sample[sample_id] = row

    kb_units: set[str] = set()
    kb_text_facets: dict[str, list[str]] = {}
    for facet in carrier.bundle.snapshot.facets:
        if facet.dimension != "content":
            continue
        kb_units.add(facet.facet_id.split("facet:content:", 1)[1])
        kb_text_facets.setdefault(facet.representation, []).append(facet.facet_id)

    unit_overlap: list[str] = []
    text_overlap: list[dict[str, object]] = []
    unresolved: list[str] = []
    for sample_id in carrier.sample_ids:
        row = row_by_sample.get(sample_id)
        if row is None:
            unresolved.append(sample_id)
            continue
        if row.unit_id in kb_units:
            unit_overlap.append(sample_id)
        hits = kb_text_facets.get(row.text)
        if hits:
            text_overlap.append(
                {
                    "sample_id": sample_id,
                    "eval_unit_id": row.unit_id,
                    "kb_facet_ids": sorted(hits),
                    "dispatched": sample_id in set(dispatched),
                }
            )

    dispatched_leaks = [
        item for item in text_overlap if item["dispatched"]
    ]
    return {
        "pool_units_read": len(rows),
        "population": len(carrier.sample_ids),
        "samples_with_no_pool_row": unresolved,
        "eval_UNITS_present_in_the_kb": len(unit_overlap),
        "eval_UNITS_present_in_the_kb_ids": unit_overlap,
        "eval_UTTERANCE_TEXTS_matching_a_kb_content_facet": len(text_overlap),
        "eval_UTTERANCE_TEXT_matches": text_overlap,
        "text_matches_among_the_dispatched_15": len(dispatched_leaks),
        "semantics": (
            "eval_UNITS_present_in_the_kb must be 0 -- that is the BLOCK "
            "decontamination `propose_partition` enforces fail-closed. A TEXT "
            "match is a WEAKER and separate condition: two different query_idx "
            "blocks may carry the same invocation string, in which case that "
            "evaluation utterance's embedding IS on disk under another facet "
            "id. Only a text match on a DISPATCHED trajectory would touch this "
            "row's oracle framing, so that count is reported separately"
        ),
    }


def landed_reproduction_gate(
    coverage: Mapping[str, object],
    geometry: Mapping[str, diag.SampleGeometry],
    gold_absent: Sequence[str],
) -> dict[str, object]:
    """Reproduce the landed split and the landed tau band BEFORE any oracle
    number is read. Fixed as a stop condition in the registration."""

    below = sorted(
        float(geometry[sample_id].gold_facet_cosine)
        for sample_id in gold_absent
        if geometry[sample_id].gold_facet_cosine is not None
        and geometry[sample_id].gold_facet_cosine < FROZEN_FUSE.tau
    )
    band = (round(below[0], 6), round(below[-1], 6)) if below else (None, None)
    checks = {
        "dispatched_n": (
            int(coverage["dispatched_n"]),  # type: ignore[arg-type]
            LANDED_DISPATCHED_N,
        ),
        "gold_bearing_dispatched": (
            int(coverage["dispatched_with_gold_bearing_supply"]),  # type: ignore[arg-type]
            LANDED_GOLD_BEARING_N,
        ),
        "gold_absent_dispatched": (
            int(coverage["dispatched_gold_absent_from_supply"]),  # type: ignore[arg-type]
            LANDED_GOLD_ABSENT_N,
        ),
        "gold_facets_below_tau_among_the_gold_absent": (len(below), 9),
        "tau_band_min": (band[0], LANDED_TAU_BAND[0]),
        "tau_band_max": (band[1], LANDED_TAU_BAND[1]),
    }
    disagreements = {
        name: {"recomputed": got, "landed": want}
        for name, (got, want) in checks.items()
        if got != want
    }
    return {
        "checks": {name: {"recomputed": got, "landed": want} for name, (got, want) in checks.items()},
        "disagreements": disagreements,
        "gate_passed": not disagreements,
        "semantics": (
            "a stop condition, not a decoration: an oracle bound computed on a "
            "population this row could not reproduce would not be a bound on "
            "the landed finding"
        ),
    }


def run(*, repo_root: Path, data_root: Path, out_path: Path) -> dict[str, object]:
    attempts = audit.arm_offline_guard()
    started = time.perf_counter()

    package_file = Path(kb.__file__).resolve()
    if not package_file.as_posix().startswith("/mnt/d/"):
        raise OracleBoundError(
            f"imported rails.kb_policy from {package_file}, not the /mnt/d/ checkout"
        )
    if "speech-aware-evidence-acquisition" not in package_file.as_posix():
        raise OracleBoundError(
            f"imported rails.kb_policy from {package_file}, not this checkout"
        )

    carrier = ccd.load_a2t_attempt4(data_root=data_root, repo_root=repo_root)
    supplies, blends, direct_labels = ccd.replay_population(carrier)
    gate = ccd.fidelity_gate(carrier, supplies, blends, direct_labels)
    if not gate["gate_passed"]:
        raise OracleBoundError(
            "the pre-registered fidelity gate FAILED; no oracle number is read: "
            + json.dumps(gate)
        )

    coverage = ccd.gold_coverage(carrier, supplies, blends)
    geometry, probe_report, kb_shape, cosine_cache = diag.compute_geometry(carrier)

    dispatched = list(coverage["dispatched_ids"])  # type: ignore[arg-type]
    per_sample = coverage["per_sample"]  # type: ignore[index]
    gold_absent = [
        sample_id
        for sample_id in dispatched
        if not per_sample[sample_id]["gold_supplied"]  # type: ignore[index]
    ]
    reproduction = landed_reproduction_gate(coverage, geometry, gold_absent)
    if not reproduction["gate_passed"]:
        raise OracleBoundError(
            "the landed-reproduction gate FAILED; no oracle number is read: "
            + json.dumps(reproduction)
        )

    leak = utterance_leak_check(
        carrier, repo_root=repo_root, data_root=data_root, dispatched=dispatched
    )
    oracle = oracle_bound(carrier, geometry, dispatched, gold_absent)
    lower = lower_constructions(carrier, geometry, dispatched, gold_absent)
    self_check = mixing_self_check(carrier, lower)
    summary = oracle["summary"]  # type: ignore[index]
    rule = decision_rule(
        int(summary["O3_gold_supplied_of_the_gold_absent"]),
        len(gold_absent),
    )
    rule["pre_registered_quantity"] = (
        "O3_gold_supplied_of_the_gold_absent -- the supremum over same-tool "
        "utterance queries with the query facet withheld, fixed as the headline "
        "in the registration before any number was seen"
    )
    rule["secondary_readings_NOT_the_registered_outcome"] = {
        "O2_anchor_only": decision_rule(
            int(summary["O2_gold_supplied_of_the_gold_absent"]), len(gold_absent)
        ),
        "O3_twin_free_post_registration": decision_rule(
            int(summary["O3_TWIN_FREE_gold_supplied_of_the_gold_absent"]),
            len(gold_absent),
        ),
        "semantics": (
            "read against the SAME pre-registered bands for transparency. The "
            "registered outcome is the O3 one above; these are reported so a "
            "reader can see how the count moves under a stricter or a narrower "
            "oracle, and neither one revises the registered outcome"
        ),
    }

    report: dict[str, object] = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "THIS_IS_AN_ORACLE": (
            "Every query measured here uses the trajectory's own GOLD TOOL "
            "identity -- information no runtime query could legally have. Every "
            "number BOUNDS THE DIRECTION FROM ABOVE. Nothing here is a proposal, "
            "a method, a knob recommendation or an achievable accuracy"
        ),
        "contacts": {
            "frozen_core": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "audio_seconds": 0.0,
            "gpu_hours": 0.0,
            "outbound_connection_attempts": attempts.count,
            "outbound_targets": list(attempts.targets),
            "vectors_constructed_from_text": 0,
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
        "landed_reproduction_gate": reproduction,
        "recall_fidelity": probe_report,
        "utterance_leak_check": leak,
        "population": {
            "dispatched_ids": sorted(dispatched),
            "gold_absent_ids": sorted(gold_absent),
            "gold_bearing_ids": sorted(set(dispatched) - set(gold_absent)),
            "exposure_caveat": (
                "A2T-G1-104 is EXPOSED; every statistic here is a SECONDARY "
                "READING and must not be used to revise, re-tune or restate the "
                "LOCK"
            ),
        },
        "oracle_bound": oracle,
        "lower_constructions": lower,
        "mixing_self_check": self_check,
        "decision_rule": rule,
        "hard_stop": (
            "BOUNDING RUNG ONLY. No knob is changed, no flight is authorized, no "
            "G2 is opened, no test contact is taken, and no generality or "
            "superiority claim follows from this artifact. A ceiling on a "
            "direction is never a measurement of a method"
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
    print(json.dumps(report["landed_reproduction_gate"], indent=1))
    leak = dict(report["utterance_leak_check"])  # type: ignore[arg-type]
    leak.pop("eval_UTTERANCE_TEXT_matches", None)
    leak.pop("semantics", None)
    print(json.dumps(leak, indent=1))
    print(json.dumps(report["oracle_bound"]["summary"], indent=1))
    print(json.dumps(report["lower_constructions"]["summary"], indent=1))
    print(json.dumps(report["decision_rule"], indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
