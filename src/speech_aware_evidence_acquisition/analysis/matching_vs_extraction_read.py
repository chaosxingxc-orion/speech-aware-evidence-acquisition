"""MATCHING versus EXTRACTION: the zero-contact conditioned SECONDARY reading.

Exposure row ``SAEA-SN-MF-MATCHING-VS-EXTRACTION-READ`` (registered before any
computation, ledger commit ``f11e6148``): zero frozen-core contacts, zero
embedding-tool contacts, zero tokenizer contacts, zero HTTP or socket
requests, zero audio decoded, zero GPU hours. Every byte read here is already
landed and already scored -- the four sealed per-arm ``*-outputs.jsonl``
files under ``SPEECHRL_DATA_DIR``, the committed mechanical reports and check
artifacts, the committed split receipts, and gold read STRICTLY scoring-side
over two populations whose seal the landed DEV-1000 lock read and the landed
A2T G1 read have already broken. Nothing written here puts gold on a runtime
path, and no knob and no line under ``rails/`` is touched.

The question
------------
Both scorers in this study compute TWO things and the whole campaign has so
far reported and optimized only the first:

* **MATCHING** -- pick the right intent (SLURP ``scenario_action_exact``) or
  the right tool (Audio2Tool ``tool_accuracy``);
* **EXTRACTION** -- pull structured content out of the signal (SLURP
  ``slot_f1_exact`` and the official ``slu_f1``; Audio2Tool ``exact_match``,
  i.e. the full name-PLUS-ARGUMENT multiset, with the slot triple F1 beside
  it).

The architectural claim is that the knowledge plane owns matching and
SUPPLIES ENOUGH INFORMATION FOR extraction. Nobody has measured whether the
supply actually serves extraction.

The confound this module exists to kill
---------------------------------------
On SLURP the aggregate extraction score improved (+3.5438 slot-F1 points on
the unexposed half). But getting the intent right also constrains which slot
types are plausible, so that gain may be entirely DOWNSTREAM of the matching
gain. The only way to separate the two is to CONDITION ON MATCHING, which is
what this module does, twice over:

1. **(primary)** a JOINT four-cell partition of the population on the matching
   outcome of BOTH arms (both matched / only BLEND matched / only M0 matched /
   neither), with extraction reported inside each cell. Because the joint cells
   are the same set of samples for both arms, every cell delta is PAIRED and
   the aggregate delta decomposes EXACTLY as ``sum_c w_c * delta_c`` with a
   single shared weight vector and no reweighting residue. The **(a)/(b)**
   attribution then falls out with no modelling at all: **(a)** is the sum of
   the two DISCORDANT cells (only-BLEND-matched, only-M0-matched), where the
   arms' matching outcomes differ and any extraction movement is mechanically
   downstream of the matching movement, and **(b)** is the sum of the two
   CONCORDANT cells (both-matched, neither-matched), where no matching movement
   can explain any extraction movement at all;
2. **(cross-check)** a MARGINAL two-group (matched / unmatched, each arm by its
   OWN matching outcome) Oaxaca-style decomposition of the same aggregate
   delta. Both weighting orders are published, because a two-term Oaxaca
   decomposition is path dependent. Its within-group term compares two
   DIFFERENT sample sets (M0's matched group is not BLEND's matched group), so
   it is reported as a cross-check and never as the attribution -- and where
   the two views name different dominant terms, the report says so and says
   why rather than picking the flattering one.

The statistical caveat that travels with every conditioned number
-----------------------------------------------------------------
Cell membership is a function of the OUTCOME of both arms, so conditioning on
it is conditioning on a post-treatment variable. The conditioned cells are
therefore DESCRIPTIVE and can carry selection (collider) bias; they are a
MECHANISM reading and never an effect size, and this is doubly true of the
small cells, whose n this module publishes for exactly that reason.

Governance, fixed in the ledger row before any number was seen
---------------------------------------------------------------
* The SLURP **unexposed 500** is the locked baseline's population. The
  already-landed aggregates restated by the fidelity gate were computed INSIDE
  the one-shot lock read, so restating them is not a new read -- but every
  CONDITIONED statistic this module computes on that half **is a SECONDARY
  reading**, is labelled as such in every table, and **must not be used to
  revise, re-tune or restate the LOCK**.
* The A2T **G1 104-item population is EXPOSED**; reading it again is free and
  carries the exposed-tier secondary-reading caveat at every citation.
* A small-n cell is a MECHANISM reading, never an effect size.

The fidelity gate is necessary, not decorative
----------------------------------------------
Before a single new number is read, this module re-scores all four sealed
output files through the SAME imported scoring path the flown reads used and
must reproduce the ALREADY-LANDED aggregates to the sample and to full float
precision. A mismatch is a fail-closed :class:`ReadError`, never a warning:
a re-scoring path that differs from the flown one would make everything
downstream untrustworthy.

Deliberate reuse -- nothing here is re-implemented
--------------------------------------------------
:mod:`.dev1000_lock_read` owns the SLURP population/arm pins and their hash
verification; :mod:`.dev500_confirmatory_read` owns the SLURP arm scorer and
the paired-comparison shape; :mod:`.dev100_damage_channel_analysis` owns the
scoring-side gold loader; :mod:`.dev100_reviewer_audit` owns the offline
guard, the bootstrap wrapper and the McNemar accounting;
:mod:`.bootstrap` owns the resampling primitive and the mandated seed;
``reproduction.slurp_scoring`` owns ``parse_slu_response``/``score_slu`` and
-- because :class:`SluScore` is a frozen dataclass of SUMMABLE ingredients --
its own corpus-level micro ``slot_f1_exact`` and official ``slu_f1``
properties, which this module obtains by summing ingredients into a synthetic
:class:`SluScore` rather than by writing a second P/R/F1;
``rails.adapters.audio2tool.Audio2ToolAdapter.score`` and
``reproduction.toolcall_scoring.score_item``/``aggregate`` own the A2T
scoring and its micro slot aggregation behind the frozen ``a2t-scorer-v1``;
:mod:`.a2t_read` owns the empty-tool-call rule and the tier projection.

What this module does NOT do
----------------------------
It changes no knob, re-tunes nothing, re-flies nothing, contacts nothing,
opens no new population, and authorizes no claim. It is descriptive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from . import a2t_read as a2t
from . import bootstrap as bs
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from . import dev500_confirmatory_read as d5
from . import dev1000_lock_read as d1k

ReadError = d5.ReadError

SCHEMA = "saea-matching-vs-extraction-read-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-MATCHING-VS-EXTRACTION-READ"
LEDGER_COMMIT = "f11e6148"

BOOTSTRAP_N = bs.DEFAULT_N_REPLICATES
BOOTSTRAP_SEED = bs.DEFAULT_SEED

CHECK_DIR_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-matching-vs-extraction"
)

# The imported ``bootstrap_gain`` hard-codes a resampling string naming the
# DEV-100 ids. The module is NOT edited (it is pinned to already-sealed
# reads), so the correction travels with every block that carries the label,
# exactly as the landed A2T G1 read does.
BOOTSTRAP_LABEL_ERRATUM = (
    "the imported dev100_reviewer_audit.bootstrap_gain hard-codes a resampling string reading "
    "'over the 100 DEV-100 ids'; the actual resampling universe is named by this block's own "
    "'resampling_universe' field. The module is NOT edited -- it is pinned to already-sealed "
    "reads -- so both the returned label and this correction are carried."
)

CONDITIONING_CAVEAT = (
    "cell membership is a function of the OUTCOME of both arms, so every conditioned number is "
    "conditioned on a POST-TREATMENT variable and can carry selection (collider) bias. The "
    "conditioned cells are DESCRIPTIVE mechanism readings, never effect sizes, and a small-n "
    "cell is a mechanism reading whatever its interval says."
)

SLURP_SECONDARY_LABEL = (
    "SECONDARY READING on the LOCKED baseline's unexposed-500 population. The already-landed "
    "aggregates were computed inside the one-shot lock read; these CONDITIONED statistics are a "
    "secondary reading and MUST NOT be used to revise, re-tune or restate the LOCK."
)
SLURP_EXPOSED_LABEL = (
    "SECONDARY READING on the nested PRIOR-EXPOSED DEV-500; never pooled into the lock claim."
)
A2T_EXPOSED_LABEL = (
    "SECONDARY READING on the EXPOSED A2T-G1-104 subset (campaign plan section 3.3): every "
    "number is a secondary reading and can never be a campaign claim; the claim interval needs "
    "n >= 400 UNEXPOSED and belongs to G2."
)

# ---------------------------------------------------------------------------
# Fidelity-gate targets, quoted from the ALREADY-LANDED artifacts
# ---------------------------------------------------------------------------

SLURP_VERDICT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/read-verdict.json"
)
A2T_VERDICT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/g1-read-attempt4.json"
)

SLURP_FIDELITY_TARGETS = {
    "unexposed500": {
        "M0": {"scenario_action_exact": 278, "slot_f1_exact_mean": 0.17097619047619048},
        "BLEND": {"scenario_action_exact": 379, "slot_f1_exact_mean": 0.20641428571428572},
    },
    "exposed500": {
        "M0": {"scenario_action_exact": 258, "slot_f1_exact_mean": 0.12224761904761905},
        "BLEND": {"scenario_action_exact": 378, "slot_f1_exact_mean": 0.15097142857142856},
    },
}

A2T_FIDELITY_TARGETS = {
    "M0": {"tool_accuracy_count": 62, "exact_match_count": 29, "empty_call_count": 14},
    "BLEND": {"tool_accuracy_count": 63, "exact_match_count": 29, "empty_call_count": 3},
}

# ---------------------------------------------------------------------------
# A2T pins (the SLURP pins are imported from the lock-read module)
# ---------------------------------------------------------------------------

A2T_RUN_ID = "SAEA-A2T-G1"
A2T_CHECK_DIR_RELPATH = "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1"
A2T_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-G1-104.json"
A2T_RECEIPT_SHA256 = "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"


@dataclass(frozen=True)
class A2tArmPin:
    arm_id: str
    stub: str
    attempt_id: str
    report_basename: str
    report_sha256: str
    outputs_basename: str
    outputs_sha256: str


A2T_ARM_PINS = (
    A2tArmPin(
        arm_id="M0",
        stub="arm1-m0",
        attempt_id="attempt-20260825T100735Z-a2tg1m0",
        report_basename="arm1-m0-mechanical-report.json",
        report_sha256="7e5e9223c48b1bc457b2b02cb54050d208d717b376326ab5061da8847366ab37",
        outputs_basename="arm1-m0-outputs.jsonl",
        outputs_sha256="dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467",
    ),
    A2tArmPin(
        arm_id="BLEND",
        stub="arm2-blend",
        attempt_id="attempt-20260825T144405Z-a2tg1blend",
        report_basename="arm2-blend-mechanical-report-attempt4.json",
        report_sha256="641c4b5ae82cdda1b2d8508bb95e52035fe1b3d119ea170f10906779df459436",
        outputs_basename="arm2-blend-outputs.jsonl",
        outputs_sha256="24a7864263226f4918076571aee359d40ee76838f9cea1da2bbae38f6b6bdd18",
    ),
)

CELL_ORDER = ("both_matched", "blend_only_matched", "m0_only_matched", "neither_matched")
CELL_DEFINITIONS = {
    "both_matched": "matching correct under BOTH arms -- the CONDITIONED cell and the headline",
    "blend_only_matched": "matching correct under BLEND only -- extraction is expected to move here simply because matching moved",
    "m0_only_matched": "matching correct under M0 only",
    "neither_matched": "matching wrong under both arms",
}


# ---------------------------------------------------------------------------
# Cell partition (carrier-agnostic)
# ---------------------------------------------------------------------------


def partition_cells(
    *, sample_ids: Sequence[str], m0_match: Mapping[str, int], blend_match: Mapping[str, int]
) -> dict[str, tuple[str, ...]]:
    """The joint four-cell partition on the MATCHING outcome of both arms.

    Deterministic (input order preserved) and provably exhaustive: the four
    cells are asserted disjoint and to cover the population exactly."""

    cells: dict[str, list[str]] = {name: [] for name in CELL_ORDER}
    for sid in sample_ids:
        a, b = int(m0_match[sid]), int(blend_match[sid])
        if a not in (0, 1) or b not in (0, 1):
            raise ReadError(f"{sid}: matching outcome is not binary ({a!r}, {b!r})")
        if a == 1 and b == 1:
            cells["both_matched"].append(sid)
        elif a == 0 and b == 1:
            cells["blend_only_matched"].append(sid)
        elif a == 1 and b == 0:
            cells["m0_only_matched"].append(sid)
        else:
            cells["neither_matched"].append(sid)
    total = sum(len(v) for v in cells.values())
    if total != len(sample_ids):
        raise ReadError("the four cells do not cover the population exactly")
    frozen = {name: tuple(v) for name, v in cells.items()}
    seen: set[str] = set()
    for members in frozen.values():
        if seen & set(members):
            raise ReadError("the four cells are not disjoint")
        seen |= set(members)
    return frozen


# ---------------------------------------------------------------------------
# Bootstrap helpers -- the mandated primitive, the mandated seed
# ---------------------------------------------------------------------------


def _bootstrap_block(
    *,
    sample_ids: Sequence[str],
    statistic: Callable[[Sequence[str]], float],
    resampling_universe: str,
    units: str,
) -> dict[str, object]:
    """The campaign's own bootstrap output shape for a statistic that is not
    a simple difference of per-sample values (a micro-aggregated ratio).

    Same primitive, same seed, same N, same 90%/95% percentile construction
    as :func:`.dev100_reviewer_audit.bootstrap_gain` -- that function is used
    verbatim wherever the statistic IS a difference of per-sample values, and
    this wrapper exists only for the ratio statistics it cannot express."""

    result = bs.paired_cluster_bootstrap(
        sample_ids=sample_ids,
        statistic=statistic,
        n_replicates=BOOTSTRAP_N,
        seed=BOOTSTRAP_SEED,
        ci_level=0.90,
    )
    ordered = sorted(result.replicates)
    ci95_low = bs._percentile(ordered, 0.025)
    ci95_high = bs._percentile(ordered, 0.975)
    at_or_below_zero = sum(1 for value in result.replicates if value <= 0.0)
    return {
        "point_estimate": result.point_estimate,
        "units": units,
        "sigma_hat": result.sigma_hat,
        "ci90_low": result.ci_low,
        "ci90_high": result.ci_high,
        "ci90_excludes_zero": result.ci_low > 0.0 or result.ci_high < 0.0,
        "ci95_low": ci95_low,
        "ci95_high": ci95_high,
        "ci95_excludes_zero": ci95_low > 0.0 or ci95_high < 0.0,
        "replicates_at_or_below_zero": at_or_below_zero,
        "replicate_share_at_or_below_zero": at_or_below_zero / result.n_replicates,
        "n_replicates": result.n_replicates,
        "seed": result.seed,
        "resampling_universe": resampling_universe,
        "resampling": (
            "per-sample paired cluster bootstrap; the SAME resampled multiset scores both arms, "
            "preserving the pairing"
        ),
    }


def _mean_gain_block(
    *,
    sample_ids: Sequence[str],
    m0: Mapping[str, float],
    blend: Mapping[str, float],
    resampling_universe: str,
    units: str,
) -> dict[str, object]:
    """``dev100_reviewer_audit.bootstrap_gain`` verbatim, on per-sample floats.

    Its ``_gain_statistic`` is ``100 * mean(blend[i] - m0[i])``, which is the
    paired delta of a per-sample MEAN metric in points -- exactly the
    quantity the landed ``slot_f1_exact_mean`` aggregates report. Reused as
    is, never re-implemented, so a conditioned interval here is produced by
    the same code path as the landed lock-read intervals."""

    block = dict(
        ra.bootstrap_gain(
            sample_ids=sample_ids,
            m0=m0,
            blend=blend,
            n_replicates=BOOTSTRAP_N,
            seed=BOOTSTRAP_SEED,
        )
    )
    block["units"] = units
    block["resampling_universe"] = resampling_universe
    block["bootstrap_label_erratum"] = BOOTSTRAP_LABEL_ERRATUM
    return block


# ---------------------------------------------------------------------------
# Decomposition (carrier-agnostic)
# ---------------------------------------------------------------------------


def joint_cell_contributions(
    *,
    cells: Mapping[str, Sequence[str]],
    n_total: int,
    m0_value: Mapping[str, float],
    blend_value: Mapping[str, float],
) -> dict[str, object]:
    """Exact arithmetic decomposition of the aggregate extraction delta over
    the JOINT four-cell partition.

    Because the joint cells are the same samples for both arms, the aggregate
    delta is ``sum_c (n_c / N) * (mean_blend,c - mean_m0,c)`` with ONE shared
    weight vector -- there is no reweighting term in this view at all, which
    is precisely why the marginal decomposition below is also computed. The
    reconstruction is asserted to close to 1e-9."""

    rows: dict[str, object] = {}
    reconstructed = 0.0
    for name in CELL_ORDER:
        members = tuple(cells[name])
        n_c = len(members)
        weight = n_c / n_total if n_total else 0.0
        if n_c:
            mean_m0 = sum(m0_value[sid] for sid in members) / n_c
            mean_blend = sum(blend_value[sid] for sid in members) / n_c
            delta = mean_blend - mean_m0
        else:
            mean_m0 = mean_blend = delta = 0.0
        contribution = weight * delta
        reconstructed += contribution
        rows[name] = {
            "n": n_c,
            "weight": weight,
            "M0_mean": mean_m0,
            "BLEND_mean": mean_blend,
            "delta": delta,
            "delta_points": 100.0 * delta,
            "contribution_to_aggregate_delta": contribution,
            "contribution_points": 100.0 * contribution,
        }
    aggregate_m0 = (
        sum(m0_value[sid] for cell in cells.values() for sid in cell) / n_total if n_total else 0.0
    )
    aggregate_blend = (
        sum(blend_value[sid] for cell in cells.values() for sid in cell) / n_total
        if n_total
        else 0.0
    )
    aggregate_delta = aggregate_blend - aggregate_m0
    if abs(reconstructed - aggregate_delta) > 1e-9:
        raise ReadError(
            "the joint cell contributions do not reconstruct the aggregate extraction delta "
            f"({reconstructed!r} vs {aggregate_delta!r})"
        )
    # ---- the (a)/(b) split, on the ONE partition where both arms are paired ----
    # (a) DISCORDANT cells -- the two arms' matching outcomes DIFFER, so the
    #     extraction movement inside them is mechanically downstream of the
    #     matching movement; this is "the part attributable to the matching gain".
    # (b) CONCORDANT cells -- both arms have the SAME matching status, so no
    #     matching movement can explain any extraction movement inside them;
    #     this is the net within-matching-status extraction effect, and its
    #     ``both_matched`` half is the CONDITIONED headline.
    a_term = float(rows["blend_only_matched"]["contribution_to_aggregate_delta"]) + float(
        rows["m0_only_matched"]["contribution_to_aggregate_delta"]
    )
    b_term = float(rows["both_matched"]["contribution_to_aggregate_delta"]) + float(
        rows["neither_matched"]["contribution_to_aggregate_delta"]
    )
    if abs((a_term + b_term) - aggregate_delta) > 1e-9:
        raise ReadError("the concordant/discordant (a)/(b) split does not close")
    denominator = abs(a_term) + abs(b_term)
    if abs(a_term) > abs(b_term):
        verdict = "(a) THE MATCHING-GAIN REWEIGHTING DOMINATES"
    elif abs(b_term) > abs(a_term):
        verdict = "(b) THE NET WITHIN-MATCHING-STATUS EXTRACTION EFFECT DOMINATES"
    else:
        verdict = "(a) AND (b) ARE EQUAL IN MAGNITUDE"

    return {
        "cells": rows,
        "aggregate_M0_mean": aggregate_m0,
        "aggregate_BLEND_mean": aggregate_blend,
        "aggregate_delta": aggregate_delta,
        "aggregate_delta_points": 100.0 * aggregate_delta,
        "reconstructed_delta": reconstructed,
        "reconstruction_residual": reconstructed - aggregate_delta,
        "ab_split": {
            "a_matching_attributable": a_term,
            "a_points": 100.0 * a_term,
            "a_cells": ["blend_only_matched", "m0_only_matched"],
            "a_definition": (
                "the two DISCORDANT cells, where the arms' matching outcomes differ: extraction "
                "movement inside them is mechanically downstream of the matching movement"
            ),
            "b_matching_independent": b_term,
            "b_points": 100.0 * b_term,
            "b_cells": ["both_matched", "neither_matched"],
            "b_definition": (
                "the two CONCORDANT cells, where both arms share a matching status: no matching "
                "movement can explain any extraction movement inside them"
            ),
            "b_both_matched_component_points": 100.0
            * float(rows["both_matched"]["contribution_to_aggregate_delta"]),
            "b_neither_matched_component_points": 100.0
            * float(rows["neither_matched"]["contribution_to_aggregate_delta"]),
            "a_share_of_absolute_total": (abs(a_term) / denominator) if denominator else 0.0,
            "b_share_of_absolute_total": (abs(b_term) / denominator) if denominator else 0.0,
            "closes_exactly": True,
            "verdict": verdict,
        },
        "note": (
            "the JOINT partition uses one shared weight vector for both arms, so every cell delta "
            "is PAIRED over the same samples and the aggregate delta apportions across cells with "
            "no reweighting residue. The (a)/(b) split above is therefore the primary attribution: "
            "(a) is the discordant (matching-attributable) contribution and (b) the concordant "
            "(matching-independent) one. The MARGINAL Oaxaca decomposition beside it is a "
            "cross-check on a DIFFERENT partition whose within-group term compares two DIFFERENT "
            "sample sets, which is why the two views can name different dominant terms."
        ),
    }


def marginal_decomposition(
    *,
    sample_ids: Sequence[str],
    m0_match: Mapping[str, int],
    blend_match: Mapping[str, int],
    m0_value: Mapping[str, float],
    blend_value: Mapping[str, float],
) -> dict[str, object]:
    """The (a)/(b) split of the aggregate extraction delta.

    Each arm is partitioned by its OWN matching outcome into matched (share
    ``p``) and unmatched (share ``1-p``) groups, so that
    ``E_arm = p_arm * mu_arm_matched + (1 - p_arm) * mu_arm_unmatched``. The
    aggregate delta then splits, exactly, into

    * **(a) composition / reweighting** -- the part attributable to the
      MATCHING gain: ``(p_B - p_0) * (mu_0_matched - mu_0_unmatched)``;
    * **(b) net within-cell extraction effect** --
      ``p_B * (mu_B_matched - mu_0_matched) + (1 - p_B) * (mu_B_unmatched - mu_0_unmatched)``.

    A two-term Oaxaca decomposition is PATH DEPENDENT, so the mirrored
    ordering (reweighting evaluated at BLEND's conditional means, within-cell
    evaluated at M0's shares) is computed too and both are published. A
    verdict that holds under only one ordering is reported as unstable."""

    ids = tuple(sample_ids)
    n = len(ids)
    if not n:
        raise ReadError("marginal_decomposition requires a non-empty population")

    def group(match: Mapping[str, int], want: int) -> tuple[str, ...]:
        return tuple(sid for sid in ids if int(match[sid]) == want)

    m0_matched, m0_unmatched = group(m0_match, 1), group(m0_match, 0)
    blend_matched, blend_unmatched = group(blend_match, 1), group(blend_match, 0)

    def mean(values: Mapping[str, float], members: Sequence[str]) -> float:
        return sum(values[sid] for sid in members) / len(members) if members else 0.0

    p0 = len(m0_matched) / n
    pb = len(blend_matched) / n
    mu0_m, mu0_u = mean(m0_value, m0_matched), mean(m0_value, m0_unmatched)
    mub_m, mub_u = mean(blend_value, blend_matched), mean(blend_value, blend_unmatched)

    e0 = p0 * mu0_m + (1.0 - p0) * mu0_u
    eb = pb * mub_m + (1.0 - pb) * mub_u
    aggregate_delta = eb - e0

    a_primary = (pb - p0) * (mu0_m - mu0_u)
    b_primary = pb * (mub_m - mu0_m) + (1.0 - pb) * (mub_u - mu0_u)
    a_mirror = (pb - p0) * (mub_m - mub_u)
    b_mirror = p0 * (mub_m - mu0_m) + (1.0 - p0) * (mub_u - mu0_u)

    for label, (a_term, b_term) in (
        ("primary", (a_primary, b_primary)),
        ("mirror", (a_mirror, b_mirror)),
    ):
        if abs((a_term + b_term) - aggregate_delta) > 1e-9:
            raise ReadError(
                f"the {label} (a)/(b) decomposition does not close "
                f"({a_term + b_term!r} vs {aggregate_delta!r})"
            )

    def verdict(a_term: float, b_term: float) -> str:
        if abs(a_term) > abs(b_term):
            return "(a) THE MATCHING-GAIN REWEIGHTING DOMINATES"
        if abs(b_term) > abs(a_term):
            return "(b) THE NET WITHIN-CELL EXTRACTION EFFECT DOMINATES"
        return "(a) AND (b) ARE EQUAL IN MAGNITUDE"

    verdict_primary = verdict(a_primary, b_primary)
    verdict_mirror = verdict(a_mirror, b_mirror)
    return {
        "n": n,
        "M0_matching_rate": p0,
        "BLEND_matching_rate": pb,
        "matching_rate_delta": pb - p0,
        "M0_extraction_matched_mean": mu0_m,
        "M0_extraction_unmatched_mean": mu0_u,
        "BLEND_extraction_matched_mean": mub_m,
        "BLEND_extraction_unmatched_mean": mub_u,
        "M0_matched_n": len(m0_matched),
        "M0_unmatched_n": len(m0_unmatched),
        "BLEND_matched_n": len(blend_matched),
        "BLEND_unmatched_n": len(blend_unmatched),
        "M0_aggregate_extraction": e0,
        "BLEND_aggregate_extraction": eb,
        "aggregate_delta": aggregate_delta,
        "aggregate_delta_points": 100.0 * aggregate_delta,
        "primary_ordering": {
            "a_reweighting_from_matching_gain": a_primary,
            "a_points": 100.0 * a_primary,
            "b_net_within_cell_extraction": b_primary,
            "b_points": 100.0 * b_primary,
            "a_share_of_absolute_total": (
                abs(a_primary) / (abs(a_primary) + abs(b_primary))
                if (abs(a_primary) + abs(b_primary))
                else 0.0
            ),
            "closes_exactly": True,
            "verdict": verdict_primary,
            "definition": (
                "(a) = (p_BLEND - p_M0) * (mu_M0_matched - mu_M0_unmatched); "
                "(b) = p_BLEND * (mu_BLEND_matched - mu_M0_matched) + "
                "(1 - p_BLEND) * (mu_BLEND_unmatched - mu_M0_unmatched)"
            ),
        },
        "mirror_ordering": {
            "a_reweighting_from_matching_gain": a_mirror,
            "a_points": 100.0 * a_mirror,
            "b_net_within_cell_extraction": b_mirror,
            "b_points": 100.0 * b_mirror,
            "a_share_of_absolute_total": (
                abs(a_mirror) / (abs(a_mirror) + abs(b_mirror))
                if (abs(a_mirror) + abs(b_mirror))
                else 0.0
            ),
            "closes_exactly": True,
            "verdict": verdict_mirror,
            "definition": (
                "(a) = (p_BLEND - p_M0) * (mu_BLEND_matched - mu_BLEND_unmatched); "
                "(b) = p_M0 * (mu_BLEND_matched - mu_M0_matched) + "
                "(1 - p_M0) * (mu_BLEND_unmatched - mu_M0_unmatched)"
            ),
        },
        "verdict_stable_across_orderings": verdict_primary == verdict_mirror,
        "verdict": verdict_primary if verdict_primary == verdict_mirror else "UNSTABLE ACROSS ORDERINGS",
        "path_dependence_note": (
            "a two-term Oaxaca decomposition is path dependent; both weighting orders are "
            "published and the verdict is only reported as settled when it holds under both."
        ),
    }


# ---------------------------------------------------------------------------
# SLURP carrier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlurpScored:
    """Per-sample SLURP outcome, keeping the FULL summable scoring ingredients."""

    match: Mapping[str, int]
    slot_f1: Mapping[str, float]
    parsed: Mapping[str, bool]
    scores: Mapping[str, object]  # sample_id -> SluScore


def score_slurp_arm(*, arm: d5.ArmOutputs, gold_by_sample: Mapping[str, object]) -> SlurpScored:
    """The registered scorer, retaining every :class:`SluScore` ingredient.

    ``parse_slu_response`` + ``score_slu`` are the SAME two calls
    :func:`.dev500_confirmatory_read.score_arm` makes; this function only
    keeps more of the result (the summable TP/FP/FN ingredients the corpus
    micro metrics need). :func:`read` cross-checks it sample by sample
    against ``score_arm`` itself, so the two paths cannot drift."""

    from ..reproduction.slurp_scoring import parse_slu_response, score_slu

    match: dict[str, int] = {}
    slot_f1: dict[str, float] = {}
    parsed_by_sample: dict[str, bool] = {}
    scores: dict[str, object] = {}
    for sample_id, text in arm.responses.items():
        gold = gold_by_sample[sample_id]
        scenario, action, entities, parsed = parse_slu_response(text)
        result = score_slu(
            gold_scenario=gold.scenario,
            gold_action=gold.action,
            gold_entities=gold.entities,
            predicted_scenario=scenario,
            predicted_action=action,
            predicted_entities=tuple(entities),
        )
        match[sample_id] = 1 if result.scenario_action_exact == 1.0 else 0
        slot_f1[sample_id] = float(result.slot_f1_exact[2])
        parsed_by_sample[sample_id] = bool(parsed)
        scores[sample_id] = result
    return SlurpScored(match=match, slot_f1=slot_f1, parsed=parsed_by_sample, scores=scores)


def slurp_extraction_block(
    *, scored: SlurpScored, sample_ids: Sequence[str]
) -> dict[str, object]:
    """One arm's extraction profile over one id set.

    ``slot_f1_exact_mean`` is the MACRO mean of per-sample F1 -- the exact
    quantity the landed ``field_decomposition_*`` profiles publish. The
    corpus-level MICRO metrics come from summing :class:`SluScore`
    ingredients into a synthetic :class:`SluScore` and reading its OWN
    properties, so ``slot_f1_exact`` (exact {type, filler} match; NOT the
    official SLU-F1) and the official ``slu_f1`` (word- plus char-distance
    micro) are computed by the frozen scorer, never re-derived here."""

    from ..reproduction.slurp_scoring import SluScore

    ids = tuple(sample_ids)
    n = len(ids)
    if not n:
        return {"n": 0, "note": "empty cell -- no extraction statistic is defined"}
    fields = (
        "scenario_action_exact",
        "scenario_exact",
        "action_exact",
        "slot_f1_exact_tp",
        "slot_f1_exact_fp",
        "slot_f1_exact_fn",
        "slu_f1_word_tp",
        "slu_f1_word_fp",
        "slu_f1_word_fn",
        "slu_f1_char_tp",
        "slu_f1_char_fp",
        "slu_f1_char_fn",
    )
    totals = {
        name: sum(float(getattr(scored.scores[sid], name)) for sid in ids) for name in fields
    }
    micro = SluScore(**totals)
    slot_p, slot_r, slot_f1_measure = micro.slot_f1_exact
    slu_p, slu_r, slu_f1_measure = micro.slu_f1
    return {
        "n": n,
        "matching_correct": sum(scored.match[sid] for sid in ids),
        "matching_accuracy": sum(scored.match[sid] for sid in ids) / n,
        "unparsed": sum(1 for sid in ids if not scored.parsed[sid]),
        # MACRO -- the landed aggregate's own metric.
        "slot_f1_exact_mean": sum(scored.slot_f1[sid] for sid in ids) / n,
        # MICRO -- corpus-level, from the frozen scorer's own properties.
        "slot_f1_exact_micro_precision": slot_p,
        "slot_f1_exact_micro_recall": slot_r,
        "slot_f1_exact_micro_f1": slot_f1_measure,
        "slot_f1_exact_tp": totals["slot_f1_exact_tp"],
        "slot_f1_exact_fp": totals["slot_f1_exact_fp"],
        "slot_f1_exact_fn": totals["slot_f1_exact_fn"],
        "slu_f1_micro_precision": slu_p,
        "slu_f1_micro_recall": slu_r,
        "slu_f1_micro_f1": slu_f1_measure,
        "metric_naming_discipline": (
            "slot_f1_exact is the exact {type, filler} dict match (the official script's plain "
            "'entities' row); slu_f1 is the OFFICIAL combined word-distance + char-distance "
            "metric. They are never interchanged and never relabelled as each other."
        ),
    }


def slurp_cell_table(
    *,
    population_label: str,
    exposure_label: str,
    sample_ids: Sequence[str],
    m0: SlurpScored,
    blend: SlurpScored,
) -> dict[str, object]:
    """The conditioned four-cell table plus both decompositions for one
    SLURP population."""

    ids = tuple(sample_ids)
    cells = partition_cells(sample_ids=ids, m0_match=m0.match, blend_match=blend.match)
    rows: dict[str, object] = {}
    for name in CELL_ORDER:
        members = cells[name]
        row: dict[str, object] = {
            "definition": CELL_DEFINITIONS[name],
            "n": len(members),
            "share_of_population": len(members) / len(ids),
            "M0": slurp_extraction_block(scored=m0, sample_ids=members),
            "BLEND": slurp_extraction_block(scored=blend, sample_ids=members),
        }
        if members:
            macro_delta = (
                sum(blend.slot_f1[sid] for sid in members) / len(members)
                - sum(m0.slot_f1[sid] for sid in members) / len(members)
            )
            row["slot_f1_exact_mean_delta_points"] = 100.0 * macro_delta
            row["slot_f1_exact_micro_f1_delta_points"] = 100.0 * (
                float(row["BLEND"]["slot_f1_exact_micro_f1"])
                - float(row["M0"]["slot_f1_exact_micro_f1"])
            )
            row["slu_f1_micro_f1_delta_points"] = 100.0 * (
                float(row["BLEND"]["slu_f1_micro_f1"]) - float(row["M0"]["slu_f1_micro_f1"])
            )
            row["bootstrap_slot_f1_exact_mean_delta"] = _mean_gain_block(
                sample_ids=members,
                m0=m0.slot_f1,
                blend=blend.slot_f1,
                resampling_universe=f"the {len(members)} ids of the {name} cell of {population_label}",
                units="slot-F1 points (100 x per-sample-mean difference)",
            )
            row["bootstrap_slu_f1_micro_delta"] = _bootstrap_block(
                sample_ids=members,
                statistic=_slu_micro_delta_statistic(m0=m0, blend=blend),
                resampling_universe=f"the {len(members)} ids of the {name} cell of {population_label}",
                units="official SLU-F1 points (100 x micro-F1 difference)",
            )
            row["mcnemar_matching_within_cell"] = (
                "not applicable -- the cell is defined by the matching outcome"
            )
        rows[name] = row
    return {
        "population": population_label,
        "exposure_label": exposure_label,
        "n": len(ids),
        "conditioning_caveat": CONDITIONING_CAVEAT,
        "matching": d5.paired_comparison(
            label=f"MATCHING (scenario_action_exact): paired BLEND - M0 over {population_label}",
            population=population_label,
            sample_ids=ids,
            baseline_name="M0",
            baseline=m0.match,
            treatment_name="BLEND",
            treatment=blend.match,
        ),
        "cells": rows,
        "joint_decomposition_slot_f1_exact_mean": joint_cell_contributions(
            cells=cells, n_total=len(ids), m0_value=m0.slot_f1, blend_value=blend.slot_f1
        ),
        "marginal_decomposition_slot_f1_exact_mean": marginal_decomposition(
            sample_ids=ids,
            m0_match=m0.match,
            blend_match=blend.match,
            m0_value=m0.slot_f1,
            blend_value=blend.slot_f1,
        ),
        "aggregate_M0": slurp_extraction_block(scored=m0, sample_ids=ids),
        "aggregate_BLEND": slurp_extraction_block(scored=blend, sample_ids=ids),
    }


def _slu_micro_delta_statistic(*, m0: SlurpScored, blend: SlurpScored):
    """100 x (official micro SLU-F1 of BLEND minus of M0) on an id multiset.

    The micro metric is a RATIO of summed ingredients, so it cannot be
    expressed as a mean of per-sample values and needs its own statistic
    closure; the resampling primitive and seed are unchanged."""

    from ..reproduction.slurp_scoring import SluScore

    fields = (
        "slu_f1_word_tp",
        "slu_f1_word_fp",
        "slu_f1_word_fn",
        "slu_f1_char_tp",
        "slu_f1_char_fp",
        "slu_f1_char_fn",
    )
    zero = {
        "scenario_action_exact": 0.0,
        "scenario_exact": 0.0,
        "action_exact": 0.0,
        "slot_f1_exact_tp": 0.0,
        "slot_f1_exact_fp": 0.0,
        "slot_f1_exact_fn": 0.0,
    }

    def micro(scored: SlurpScored, ids: Sequence[str]) -> float:
        totals = dict(zero)
        for name in fields:
            totals[name] = sum(float(getattr(scored.scores[sid], name)) for sid in ids)
        return SluScore(**totals).slu_f1[2]

    def statistic(ids: Sequence[str]) -> float:
        return 100.0 * (micro(blend, ids) - micro(m0, ids))

    return statistic


# ---------------------------------------------------------------------------
# Audio2Tool carrier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tScored:
    """Per-sample A2T outcome from BOTH the adapter and the frozen item scorer."""

    match: Mapping[str, int]
    exact_match: Mapping[str, int]
    slot_f1: Mapping[str, float]
    empty_call: Mapping[str, bool]
    parsed: Mapping[str, bool]
    items: Mapping[str, object]  # sample_id -> ItemScore


def load_a2t_arm(*, pin: A2tArmPin, repo_root: Path, data_root: Path) -> dict[str, str]:
    """One sealed A2T arm's per-sample response texts, hash-verified first."""

    report_path = Path(repo_root) / A2T_CHECK_DIR_RELPATH / pin.report_basename
    d5._require_hash(report_path, pin.report_sha256, f"A2T {pin.arm_id} committed report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if str(report["run_id"]) != A2T_RUN_ID or str(report["arm_id"]) != pin.arm_id:
        raise ReadError(f"A2T {pin.arm_id}: committed report names a different run/arm")
    if str(report["attempt_id"]) != pin.attempt_id:
        raise ReadError(f"A2T {pin.arm_id}: committed report names a different attempt")
    run_dir = Path(data_root) / "runs" / A2T_RUN_ID / pin.attempt_id
    if Path(str(report["run_dir"])) != run_dir:
        raise ReadError(f"A2T {pin.arm_id}: committed report's run_dir is not the pinned dir")
    outputs_path = run_dir / pin.outputs_basename
    if Path(str(report["mechanical"]["opaque_outputs"])) != outputs_path:
        raise ReadError(f"A2T {pin.arm_id}: committed report names other outputs bytes")
    d5._require_hash(outputs_path, pin.outputs_sha256, f"A2T {pin.arm_id} sealed outputs")

    responses: dict[str, str] = {}
    with outputs_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            sample_id = str(record["sample_id"])
            if sample_id in responses:
                raise ReadError(f"A2T {pin.arm_id}: duplicate sample {sample_id}")
            responses[sample_id] = str(record["final_response_text"])
    return responses


def score_a2t_arm(*, adapter, gold, responses: Mapping[str, str]) -> A2tScored:
    """Score through the adapter AND through the frozen item scorer directly.

    ``Audio2ToolAdapter.score`` is the exact call the landed G1 read makes and
    is what the fidelity gate is checked against; ``score_item`` is the same
    function the adapter itself calls, used here only to retain the slot
    TP/expected/predicted totals the adapter's float-only return drops. The
    two are asserted equal sample by sample, so this cannot become a second
    scorer."""

    from ..reproduction.toolcall_scoring import parse_tool_calls_text, score_item
    from ..rails.adapters.audio2tool import Audio2ToolSample

    placeholder = a2t_placeholder_audio_ref()
    match: dict[str, int] = {}
    exact: dict[str, int] = {}
    slot_f1: dict[str, float] = {}
    empty: dict[str, bool] = {}
    parsed_by_sample: dict[str, bool] = {}
    items: dict[str, object] = {}
    for sample_id, text in responses.items():
        sample = Audio2ToolSample(
            sample_id=sample_id,
            audio_ref=placeholder,
            audio_seconds=0.0,
            media_relpath="",
        )
        metrics = adapter.score(sample, text)
        predicted, parsed = parse_tool_calls_text(text)
        item = score_item(gold[sample_id], predicted)
        if (
            float(metrics["tool_accuracy"]) != item.tool_accuracy
            or float(metrics["exact_match"]) != item.exact_match
            or float(metrics["slot_f1"]) != item.slot_f1
            or bool(metrics["parsed"]) != bool(parsed)
        ):
            raise ReadError(
                f"A2T {sample_id}: the adapter and the frozen item scorer disagree -- the two "
                "scoring paths have drifted and the read STOPS"
            )
        if item.exact_match == 1.0 and item.tool_accuracy != 1.0:
            raise ReadError(
                f"A2T {sample_id}: exact_match without tool_accuracy contradicts the scorer's own "
                "containment property"
            )
        match[sample_id] = int(item.tool_accuracy == 1.0)
        exact[sample_id] = int(item.exact_match == 1.0)
        slot_f1[sample_id] = float(item.slot_f1)
        empty[sample_id] = a2t.is_empty_tool_call(text)
        parsed_by_sample[sample_id] = bool(parsed)
        items[sample_id] = item
    return A2tScored(
        match=match,
        exact_match=exact,
        slot_f1=slot_f1,
        empty_call=empty,
        parsed=parsed_by_sample,
        items=items,
    )


def a2t_placeholder_audio_ref():
    """The landed G1 read's own placeholder: ``score`` never touches audio."""

    from ..rails.obs import AudioRef

    return AudioRef(path="unused", sha256="0" * 64).validate()


def a2t_extraction_block(*, scored: A2tScored, sample_ids: Sequence[str]) -> dict[str, object]:
    """One arm's A2T extraction profile over one id set."""

    from ..reproduction.toolcall_scoring import aggregate

    ids = tuple(sample_ids)
    n = len(ids)
    if not n:
        return {"n": 0, "note": "empty cell -- no extraction statistic is defined"}
    agg = aggregate(scored.items[sid] for sid in ids)
    tool_correct = sum(scored.match[sid] for sid in ids)
    exact_correct = sum(scored.exact_match[sid] for sid in ids)
    return {
        "n": n,
        "tool_accuracy_count": tool_correct,
        "tool_accuracy": tool_correct / n,
        "exact_match_count": exact_correct,
        "exact_match": exact_correct / n,
        "gap_tool_accuracy_minus_exact_match": (tool_correct - exact_correct) / n,
        "conditional_exact_match_given_tool_correct": (
            exact_correct / tool_correct if tool_correct else None
        ),
        "slot_f1_mean": sum(scored.slot_f1[sid] for sid in ids) / n,
        "slot_micro_precision": agg.slot_precision,
        "slot_micro_recall": agg.slot_recall,
        "slot_micro_f1": agg.slot_f1,
        "slot_true_positives": agg.slot_true_positives,
        "slot_expected_total": agg.slot_expected_total,
        "slot_predicted_total": agg.slot_predicted_total,
        "empty_call_count": sum(1 for sid in ids if scored.empty_call[sid]),
        "empty_call_rate": sum(1 for sid in ids if scored.empty_call[sid]) / n,
        "unparsed_count": sum(1 for sid in ids if not scored.parsed[sid]),
    }


def _a2t_slot_micro_delta_statistic(*, m0: A2tScored, blend: A2tScored):
    from ..reproduction.toolcall_scoring import aggregate

    def statistic(ids: Sequence[str]) -> float:
        return 100.0 * (
            aggregate(blend.items[sid] for sid in ids).slot_f1
            - aggregate(m0.items[sid] for sid in ids).slot_f1
        )

    return statistic


def a2t_cell_table(
    *, sample_ids: Sequence[str], m0: A2tScored, blend: A2tScored
) -> dict[str, object]:
    ids = tuple(sample_ids)
    cells = partition_cells(sample_ids=ids, m0_match=m0.match, blend_match=blend.match)
    rows: dict[str, object] = {}
    for name in CELL_ORDER:
        members = cells[name]
        row: dict[str, object] = {
            "definition": CELL_DEFINITIONS[name],
            "n": len(members),
            "share_of_population": len(members) / len(ids),
            "M0": a2t_extraction_block(scored=m0, sample_ids=members),
            "BLEND": a2t_extraction_block(scored=blend, sample_ids=members),
        }
        if members:
            em_delta = (
                sum(blend.exact_match[sid] for sid in members)
                - sum(m0.exact_match[sid] for sid in members)
            )
            row["exact_match_delta_samples"] = em_delta
            row["exact_match_delta_pp"] = 100.0 * em_delta / len(members)
            row["slot_f1_mean_delta_points"] = 100.0 * (
                sum(blend.slot_f1[sid] for sid in members) / len(members)
                - sum(m0.slot_f1[sid] for sid in members) / len(members)
            )
            row["slot_micro_f1_delta_points"] = 100.0 * (
                float(row["BLEND"]["slot_micro_f1"]) - float(row["M0"]["slot_micro_f1"])
            )
            row["bootstrap_exact_match_delta"] = _mean_gain_block(
                sample_ids=members,
                m0=m0.exact_match,
                blend=blend.exact_match,
                resampling_universe=f"the {len(members)} ids of the {name} cell of A2T-G1-104",
                units="exact-match percentage points",
            )
            row["bootstrap_slot_micro_f1_delta"] = _bootstrap_block(
                sample_ids=members,
                statistic=_a2t_slot_micro_delta_statistic(m0=m0, blend=blend),
                resampling_universe=f"the {len(members)} ids of the {name} cell of A2T-G1-104",
                units="slot micro-F1 points",
            )
            row["mcnemar_exact_match_within_cell"] = ra.mcnemar(
                sum(
                    1
                    for sid in members
                    if m0.exact_match[sid] == 0 and blend.exact_match[sid] == 1
                ),
                sum(
                    1
                    for sid in members
                    if m0.exact_match[sid] == 1 and blend.exact_match[sid] == 0
                ),
            )
        rows[name] = row
    return {
        "population": "A2T-G1-104 (104 EXPOSED)",
        "exposure_label": A2T_EXPOSED_LABEL,
        "n": len(ids),
        "conditioning_caveat": CONDITIONING_CAVEAT,
        "structural_containment": (
            "reproduction.toolcall_scoring.score_item computes exact_match as equality of the full "
            "name-plus-argument multiset and tool_accuracy as equality of the tool-NAME multiset, so "
            "exact_match == 1 STRUCTURALLY implies tool_accuracy == 1. Extraction is therefore "
            "identically zero in every cell for the arm that failed matching -- asserted per sample, "
            "not assumed."
        ),
        "matching": d5.paired_comparison(
            label="MATCHING (tool_accuracy): paired BLEND - M0 over A2T-G1-104",
            population="A2T-G1-104 (104 EXPOSED)",
            sample_ids=ids,
            baseline_name="M0",
            baseline=m0.match,
            treatment_name="BLEND",
            treatment=blend.match,
        ),
        "cells": rows,
        "joint_decomposition_exact_match": joint_cell_contributions(
            cells=cells, n_total=len(ids), m0_value=m0.exact_match, blend_value=blend.exact_match
        ),
        "joint_decomposition_slot_f1_mean": joint_cell_contributions(
            cells=cells, n_total=len(ids), m0_value=m0.slot_f1, blend_value=blend.slot_f1
        ),
        "marginal_decomposition_exact_match": marginal_decomposition(
            sample_ids=ids,
            m0_match=m0.match,
            blend_match=blend.match,
            m0_value=m0.exact_match,
            blend_value=blend.exact_match,
        ),
        "marginal_decomposition_slot_f1_mean": marginal_decomposition(
            sample_ids=ids,
            m0_match=m0.match,
            blend_match=blend.match,
            m0_value=m0.slot_f1,
            blend_value=blend.slot_f1,
        ),
        "aggregate_M0": a2t_extraction_block(scored=m0, sample_ids=ids),
        "aggregate_BLEND": a2t_extraction_block(scored=blend, sample_ids=ids),
    }


# ---------------------------------------------------------------------------
# The read
# ---------------------------------------------------------------------------


def _float_equal(measured: float, target: float) -> bool:
    """Full float precision -- byte equality of the two doubles."""

    return float(measured) == float(target)


def read(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Execute the registered zero-contact conditioned reading."""

    attempts = ra.arm_offline_guard()

    repo_root = Path(repo_root)
    data_root = Path(data_root)

    # ---------------- SLURP: load and score -------------------------------
    populations = d1k.load_populations(repo_root)
    slurp_arms = {
        pin.arm_id: d1k.load_arm(pin=pin, repo_root=repo_root, data_root=data_root)
        for pin in d1k.ARM_PINS
    }
    expected = set(populations.dev1000)
    for arm in slurp_arms.values():
        if set(arm.responses) != expected:
            raise ReadError(f"{arm.pin.arm_id}: sealed outputs do not cover exactly DEV-1000")

    gold_by_sample = dc._load_gold(
        data_root=data_root, repo_root=repo_root, sample_ids=set(populations.dev1000)
    )
    slurp_scored = {
        arm_id: score_slurp_arm(arm=arm, gold_by_sample=gold_by_sample)
        for arm_id, arm in slurp_arms.items()
    }
    # Cross-check against the campaign's OWN scorer, sample by sample.
    reference = {
        arm_id: d5.score_arm(arm=arm, gold_by_sample=gold_by_sample)
        for arm_id, arm in slurp_arms.items()
    }
    for arm_id, ref in reference.items():
        mine = slurp_scored[arm_id]
        for sid in populations.dev1000:
            if ref.correct[sid] != mine.match[sid] or ref.slot_f1[sid] != mine.slot_f1[sid]:
                raise ReadError(
                    f"SLURP {arm_id}/{sid}: this module's scoring differs from "
                    "dev500_confirmatory_read.score_arm -- the read STOPS"
                )

    # ---------------- SLURP fidelity gate ---------------------------------
    slurp_gate: dict[str, object] = {"targets_source": SLURP_VERDICT_RELPATH, "checks": []}
    slurp_gate_pass = True
    id_sets = {"unexposed500": populations.new500, "exposed500": populations.dev500}
    for pop_name, ids in id_sets.items():
        for arm_id in ("M0", "BLEND"):
            target = SLURP_FIDELITY_TARGETS[pop_name][arm_id]
            scored = slurp_scored[arm_id]
            measured_match = sum(scored.match[sid] for sid in ids)
            measured_mean = sum(scored.slot_f1[sid] for sid in ids) / len(ids)
            ok_match = measured_match == int(target["scenario_action_exact"])
            ok_mean = _float_equal(measured_mean, float(target["slot_f1_exact_mean"]))
            slurp_gate_pass = slurp_gate_pass and ok_match and ok_mean
            slurp_gate["checks"].append(
                {
                    "population": pop_name,
                    "arm": arm_id,
                    "metric": "scenario_action_exact",
                    "target": int(target["scenario_action_exact"]),
                    "measured": measured_match,
                    "pass": ok_match,
                }
            )
            slurp_gate["checks"].append(
                {
                    "population": pop_name,
                    "arm": arm_id,
                    "metric": "slot_f1_exact_mean",
                    "target": float(target["slot_f1_exact_mean"]),
                    "measured": measured_mean,
                    "target_repr": repr(float(target["slot_f1_exact_mean"])),
                    "measured_repr": repr(measured_mean),
                    "pass": ok_mean,
                }
            )
    slurp_gate["pass"] = slurp_gate_pass

    # ---------------- A2T: load and score ---------------------------------
    from ..data.audio2tool import load_expected_calls
    from ..data.lock import load_lock, umbrella_lock_path
    from ..rails.adapters.audio2tool import Audio2ToolAdapter

    receipt_path = repo_root / A2T_RECEIPT_RELPATH
    d5._require_hash(receipt_path, A2T_RECEIPT_SHA256, "A2T-G1-104 committed receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    a2t_ids = tuple(sorted(str(item["sample_id"]) for item in receipt["items"]))
    if len(a2t_ids) != int(receipt["count"]) or len(set(a2t_ids)) != len(a2t_ids):
        raise ReadError("the A2T-G1-104 receipt count disagrees with its items")

    lock = load_lock(umbrella_lock_path(repo_root))
    adapter = Audio2ToolAdapter(lock, data_root, repo_root=repo_root)
    a2t_gold = load_expected_calls(lock, data_root, repo_root=repo_root)
    missing = [sid for sid in a2t_ids if sid not in a2t_gold]
    if missing:
        raise ReadError(f"A2T gold missing for {missing[:5]!r}")

    a2t_responses = {
        pin.arm_id: load_a2t_arm(pin=pin, repo_root=repo_root, data_root=data_root)
        for pin in A2T_ARM_PINS
    }
    for arm_id, responses in a2t_responses.items():
        if tuple(sorted(responses)) != a2t_ids:
            raise ReadError(f"A2T {arm_id}: sealed outputs do not cover exactly A2T-G1-104")
    a2t_scored = {
        arm_id: score_a2t_arm(adapter=adapter, gold=a2t_gold, responses=responses)
        for arm_id, responses in a2t_responses.items()
    }

    # ---------------- A2T fidelity gate -----------------------------------
    a2t_gate: dict[str, object] = {"targets_source": A2T_VERDICT_RELPATH, "checks": []}
    a2t_gate_pass = True
    for arm_id in ("M0", "BLEND"):
        scored = a2t_scored[arm_id]
        target = A2T_FIDELITY_TARGETS[arm_id]
        measured = {
            "tool_accuracy_count": sum(scored.match[sid] for sid in a2t_ids),
            "exact_match_count": sum(scored.exact_match[sid] for sid in a2t_ids),
            "empty_call_count": sum(1 for sid in a2t_ids if scored.empty_call[sid]),
        }
        for metric, value in measured.items():
            ok = value == int(target[metric])
            a2t_gate_pass = a2t_gate_pass and ok
            a2t_gate["checks"].append(
                {
                    "population": "A2T-G1-104",
                    "arm": arm_id,
                    "metric": metric,
                    "target": int(target[metric]),
                    "measured": value,
                    "pass": ok,
                }
            )
    a2t_gate["pass"] = a2t_gate_pass

    gate_pass = slurp_gate_pass and a2t_gate_pass
    if not gate_pass:
        failures = [c for c in slurp_gate["checks"] + a2t_gate["checks"] if not c["pass"]]
        raise ReadError(
            "FIDELITY GATE FAILED -- the re-scoring path differs from the flown one and NOTHING "
            f"downstream is trustworthy. Failing checks: {json.dumps(failures)}"
        )

    # ---------------- The conditioned tables ------------------------------
    slurp_tables = {
        "unexposed500": slurp_cell_table(
            population_label="DEV-1000-NEW500 (500 UNEXPOSED)",
            exposure_label=SLURP_SECONDARY_LABEL,
            sample_ids=populations.new500,
            m0=slurp_scored["M0"],
            blend=slurp_scored["BLEND"],
        ),
        "exposed500": slurp_cell_table(
            population_label="DEV-500 (500 PRIOR-EXPOSED)",
            exposure_label=SLURP_EXPOSED_LABEL,
            sample_ids=populations.dev500,
            m0=slurp_scored["M0"],
            blend=slurp_scored["BLEND"],
        ),
    }
    a2t_table = a2t_cell_table(
        sample_ids=a2t_ids, m0=a2t_scored["M0"], blend=a2t_scored["BLEND"]
    )

    scoreboard = build_scoreboard(slurp_tables=slurp_tables, a2t_table=a2t_table)

    return {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_ledger_row": EXPOSURE_ROW_ID,
        "ledger_commit": LEDGER_COMMIT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "targets": list(attempts.targets),
            "armed_before_first_input": True,
        },
        "question": (
            "these tasks decompose into MATCHING (pick the right intent / the right tool) and "
            "EXTRACTION (pull structured content out of the signal). Every campaign so far "
            "reported and optimized MATCHING only. Does the supply serve EXTRACTION, on either "
            "carrier, once matching is conditioned on?"
        ),
        "fidelity_gate": {
            "pass": gate_pass,
            "slurp": slurp_gate,
            "a2t": a2t_gate,
            "semantics": (
                "re-score per sample through the SAME imported scoring path the flown reads used "
                "and reproduce the already-landed aggregates to the sample and to full float "
                "precision (byte equality of the doubles). A mismatch is fail-closed."
            ),
        },
        "pins": {
            "slurp_receipts": dict(populations.receipt_hashes),
            "slurp_arms": [
                {
                    "arm_id": pin.arm_id,
                    "attempt_id": pin.attempt_id,
                    "outputs_sha256": pin.outputs_sha256,
                    "report_sha256": pin.report_sha256,
                }
                for pin in d1k.ARM_PINS
            ],
            "a2t_receipt_sha256": A2T_RECEIPT_SHA256,
            "a2t_arms": [
                {
                    "arm_id": pin.arm_id,
                    "attempt_id": pin.attempt_id,
                    "outputs_sha256": pin.outputs_sha256,
                    "report_sha256": pin.report_sha256,
                }
                for pin in A2T_ARM_PINS
            ],
        },
        "bootstrap": {
            "n_replicates": BOOTSTRAP_N,
            "seed": BOOTSTRAP_SEED,
            "procedure": (
                "analysis.bootstrap.paired_cluster_bootstrap via "
                "analysis.dev100_reviewer_audit.bootstrap_gain for difference-of-per-sample-value "
                "statistics, and via a local statistic closure for the micro-aggregated ratio "
                "statistics; 90% and 95% percentile CIs, identical seed and N to the DEV-500 and "
                "DEV-1000 reads."
            ),
        },
        "slurp": slurp_tables,
        "audio2tool": a2t_table,
        "two_axis_scoreboard": scoreboard,
        "hard_stop": (
            "This read is DESCRIPTIVE. It authorizes NO knob change, NO re-tune, NO re-flight, NO "
            "revision or restatement of the DEV-1000 LOCK, NO test contact, NO generality or "
            "superiority claim, NO G2 opening and NO Stage-3 activity. The SLURP unexposed-500 "
            "conditioned statistics are a SECONDARY reading on the locked baseline's population; "
            "the A2T numbers are a secondary reading on an EXPOSED population at n=104."
        ),
    }


def build_scoreboard(
    *, slurp_tables: Mapping[str, object], a2t_table: Mapping[str, object]
) -> list[dict[str, object]]:
    """One ``matching | extraction`` row per landed cell.

    Replaces the matching-only scoreboard: every landed (carrier, population,
    arm) cell gets BOTH axes, so a matching gain can never again be reported
    without the extraction number that belongs beside it."""

    rows: list[dict[str, object]] = []
    for key, label in (
        ("unexposed500", "SLURP DEV-1000-NEW500 (500 UNEXPOSED)"),
        ("exposed500", "SLURP DEV-500 (500 PRIOR-EXPOSED)"),
    ):
        table = slurp_tables[key]
        for arm in ("M0", "BLEND"):
            block = table[f"aggregate_{arm}"]
            rows.append(
                {
                    "carrier": "SLURP (slot-SLU)",
                    "population": label,
                    "arm": arm,
                    "matching_metric": "scenario_action_exact",
                    "matching": block["matching_accuracy"],
                    "matching_count": block["matching_correct"],
                    "extraction_metric": "slot_f1_exact_mean (macro) / slu_f1 (official micro)",
                    "extraction_slot_f1_exact_mean": block["slot_f1_exact_mean"],
                    "extraction_slot_f1_exact_micro_f1": block["slot_f1_exact_micro_f1"],
                    "extraction_slu_f1_micro_f1": block["slu_f1_micro_f1"],
                    "n": block["n"],
                    "exposure": table["exposure_label"],
                }
            )
    for arm in ("M0", "BLEND"):
        block = a2t_table[f"aggregate_{arm}"]
        rows.append(
            {
                "carrier": "Audio2Tool",
                "population": "A2T-G1-104 (104 EXPOSED)",
                "arm": arm,
                "matching_metric": "tool_accuracy",
                "matching": block["tool_accuracy"],
                "matching_count": block["tool_accuracy_count"],
                "extraction_metric": "exact_match (name+argument multiset) / slot micro-F1",
                "extraction_exact_match": block["exact_match"],
                "extraction_exact_match_count": block["exact_match_count"],
                "extraction_slot_micro_f1": block["slot_micro_f1"],
                "conditional_exact_match_given_tool_correct": block[
                    "conditional_exact_match_given_tool_correct"
                ],
                "n": block["n"],
                "exposure": a2t_table["exposure_label"],
            }
        )
    return rows


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "MATCHING versus EXTRACTION: the zero-contact conditioned secondary reading over the "
            "sealed SLURP DEV-1000 and Audio2Tool G1 arms."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    report = read(repo_root=Path(args.repo_root), data_root=Path(args.data_root))
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")

    gate = report["fidelity_gate"]
    print(f"FIDELITY GATE: {'PASS' if gate['pass'] else 'FAIL'}")
    print(
        "offline guard outbound attempts: "
        f"{report['offline_guard']['outbound_connection_attempts']}"
    )
    def _ab(block, unit: str) -> None:
        split = block["ab_split"]
        print(
            f"  aggregate {block['aggregate_delta_points']:+.4f} {unit} = "
            f"(a) {split['a_points']:+.4f} + (b) {split['b_points']:+.4f}   "
            f"[both-matched {split['b_both_matched_component_points']:+.4f}, "
            f"neither {split['b_neither_matched_component_points']:+.4f}]"
        )
        print(
            f"  -> {split['verdict']}  "
            f"(|a| share {split['a_share_of_absolute_total']:.4f})"
        )

    for key, label in (("unexposed500", "UNEXPOSED500"), ("exposed500", "EXPOSED500")):
        table = report["slurp"][key]
        both = table["cells"]["both_matched"]
        print(
            f"SLURP {label}: both-matched n={both['n']}  "
            f"slot-F1 mean delta {both.get('slot_f1_exact_mean_delta_points', 0.0):+.4f} pts  "
            f"SLU-F1 micro delta {both.get('slu_f1_micro_f1_delta_points', 0.0):+.4f} pts"
        )
        _ab(table["joint_decomposition_slot_f1_exact_mean"], "pts")
        marginal = table["marginal_decomposition_slot_f1_exact_mean"]
        print(
            f"  cross-check (marginal Oaxaca): a {marginal['primary_ordering']['a_points']:+.4f} / "
            f"b {marginal['primary_ordering']['b_points']:+.4f} -> {marginal['verdict']}"
        )
    a2t_table = report["audio2tool"]
    a2t_both = a2t_table["cells"]["both_matched"]
    print(
        f"A2T: both-matched n={a2t_both['n']}  "
        f"exact-match delta {a2t_both.get('exact_match_delta_pp', 0.0):+.4f} pp  "
        f"slot micro-F1 delta {a2t_both.get('slot_micro_f1_delta_points', 0.0):+.4f} pts"
    )
    _ab(a2t_table["joint_decomposition_exact_match"], "pp")
    _ab(a2t_table["joint_decomposition_slot_f1_mean"], "pts")
    print(f"wrote {out_path}")
    print(f"report sha256: {_sha256_bytes(payload.encode('utf-8'))}")
    return 0


__all__ = [
    "A2T_ARM_PINS",
    "A2T_FIDELITY_TARGETS",
    "CELL_ORDER",
    "EXPOSURE_ROW_ID",
    "SCHEMA",
    "SLURP_FIDELITY_TARGETS",
    "A2tScored",
    "SlurpScored",
    "a2t_cell_table",
    "a2t_extraction_block",
    "build_scoreboard",
    "joint_cell_contributions",
    "load_a2t_arm",
    "main",
    "marginal_decomposition",
    "partition_cells",
    "read",
    "score_a2t_arm",
    "score_slurp_arm",
    "slurp_cell_table",
    "slurp_extraction_block",
]


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
