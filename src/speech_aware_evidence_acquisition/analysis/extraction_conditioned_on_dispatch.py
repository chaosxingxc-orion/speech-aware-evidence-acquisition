"""EXTRACTION CONDITIONED ON DISPATCH: the zero-contact follow-up secondary reading.

Exposure row ``SAEA-SN-MF-EXTRACTION-CONDITIONED-ON-DISPATCH`` (registered
before any computation, ledger commit ``849a09c7``): zero frozen-core
contacts, zero embedding-tool contacts, zero tokenizer contacts, zero HTTP or
socket requests, zero audio decoded, zero GPU hours, zero new dependencies.
Every byte read here is already landed and already scored. Nothing written
here puts gold on a runtime path, no knob is changed, and no line under
``rails/`` is touched.

The defect under test
---------------------
The landed matching-versus-extraction read
(:mod:`.matching_vs_extraction_read`, document
``docs/readiness/2026-08-25-matching-vs-extraction-read.md`` at commit
``d4c75c7a``) partitioned each population by the two arms' MATCHING outcome
and concluded that, conditioned on matching, the supply does not serve
extraction. Its fidelity gate passed to full float precision and its
arithmetic closes -- that work is sound as far as it goes.

**But it never conditioned on whether the trajectory actually RECEIVED
SUPPLY.** In this controller a RETAINED trajectory stops at contact 0 and is
handed no evidence at all; only a DISPATCHED trajectory receives supply. A
cell dominated by retained trajectories therefore CANNOT exhibit a supply
effect -- not because the supply fails, but because there was none. The
landed document's conditioned headline may consequently be, in the main, a
statement about UNSUPPLIED trajectories.

This module tests that suspicion rather than assuming it, by crossing the
four matching cells with the DISPATCH/RETAIN branch the controller actually
took.

The branch is READ, never re-derived
------------------------------------
The branch decision comes from the sealed per-sample mechanical record of the
BLEND arm, hash-pinned before it is opened:

* **SLURP** -- ``arm2-blend-mechanical.json`` of attempt
  ``attempt-20260825T054707Z-dev1000blend`` under run
  ``SAEA-DEV1000-BASELINE-LOCK``, sha256 ``e55b6632...c828e``. DISPATCH is
  ``contacts == 2`` and RETAIN is ``contacts == 1``; the dispatch side is
  further split by ``override_fires`` into ``dead_direct_dispatch`` and
  ``override_dispatch``, exactly as
  :func:`.dev1000_lock_read.dispatch_decomposition` defines them. The loader
  :func:`.dev1000_lock_read.load_per_sample_mechanical` already cross-checks
  those bytes against the committed mechanical report, so the branch is
  proved twice before it is used once.
* **Audio2Tool** -- ``arm2-blend-mechanical.json`` of attempt
  ``attempt-20260825T144405Z-a2tg1blend`` under run ``SAEA-A2T-G1``, sha256
  ``59458c49...644e`` (the value the landed A2T gold-absence diagnosis report
  already carries). DISPATCH is ``not retained_primary``, exactly as
  :mod:`.cross_carrier_ceiling_decomposition` reads it.

**Dispatch is a property of the BLEND arm alone.** The M0 arm is
single-contact and supplies nothing; the asymmetry is stated at every
citation rather than hidden. A RETAINED BLEND trajectory answers with its own
contact-0 direct decode, which is a DIFFERENT decode of the same prompt from
the M0 arm's -- so a retained pair can still differ through decode variance,
and this module measures that channel on the retained set instead of assuming
it away.

The two caveats that travel with every conditioned number
---------------------------------------------------------
Cell membership here is a function of arm OUTCOMES **and** of a
POST-TREATMENT branch decision (itself an outcome of the controller acting on
the trajectory), so every conditioned number carries selection (collider)
bias twice over. These are DESCRIPTIVE MECHANISM READINGS, NEVER EFFECT
SIZES, and a small-n cell is a mechanism reading whatever its interval says.
Both rules were fixed in the ledger row before any n was known.

Deliberate reuse -- nothing here is re-implemented
--------------------------------------------------
:mod:`.matching_vs_extraction_read` owns the scorers, the extraction blocks,
the four-cell partition, the bootstrap wrappers and the fidelity-gate
targets; :mod:`.dev1000_lock_read` owns the SLURP population/arm pins and the
mechanical loader; :mod:`.dev500_confirmatory_read` owns the hash gate and
the paired-comparison shape; :mod:`.dev100_reviewer_audit` owns the offline
guard, the bootstrap wrapper and the McNemar accounting; :mod:`.bootstrap`
owns the resampling primitive and the mandated seed.

What this module does NOT do
----------------------------
It changes no knob, re-tunes nothing, re-flies nothing, contacts nothing,
opens no new population, and authorizes no claim. It is descriptive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from . import bootstrap as bs
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from . import dev500_confirmatory_read as d5
from . import dev1000_lock_read as d1k
from . import matching_vs_extraction_read as mve

ReadError = d5.ReadError

SCHEMA = "saea-extraction-conditioned-on-dispatch-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-EXTRACTION-CONDITIONED-ON-DISPATCH"
LEDGER_COMMIT = "849a09c7"

BOOTSTRAP_N = bs.DEFAULT_N_REPLICATES
BOOTSTRAP_SEED = bs.DEFAULT_SEED

CHECK_DIR_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-08-25-extraction-conditioned-on-dispatch"
)

#: The landed document this reading audits, and the receipt it published.
AUDITED_DOCUMENT_RELPATH = "docs/readiness/2026-08-25-matching-vs-extraction-read.md"
AUDITED_DOCUMENT_COMMIT = "d4c75c7a"
AUDITED_RECEIPT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-matching-vs-extraction/"
    "read-report.json"
)
AUDITED_RECEIPT_SHA256 = (
    "378757b5bc3292395cbdc82a19c936912edaf61725cede012bfad6b77ffd6523"
)

#: The two sealed BLEND branch records, pinned before they are opened.
SLURP_BLEND_MECHANICAL_SHA256 = (
    "e55b6632d85a0037fb928d565fb2ef1b40c987c915dd98a9f2599d78113c828e"
)
A2T_BLEND_MECHANICAL_SHA256 = (
    "59458c491368a117721041e4ba1538549f3e1e28bdb342e4927703ad5892644e"
)

DISPATCH_ORDER = ("dispatched", "retained")

BRANCH_ASYMMETRY_NOTE = (
    "DISPATCH is a property of the BLEND arm ALONE. The M0 arm is single-contact and supplies "
    "nothing, so 'the dispatched trajectories' means 'the trajectories the BLEND controller chose "
    "to supply', scored under BOTH arms on the same sample ids. A RETAINED BLEND trajectory "
    "answers with its OWN contact-0 direct decode, which is a DIFFERENT decode of the same prompt "
    "from the M0 arm's, so a retained pair can still differ through decode variance alone."
)

DOUBLE_CONDITIONING_CAVEAT = (
    "cell membership is a function of the arms' matching OUTCOMES **and** of a POST-TREATMENT "
    "branch decision (the dispatch decision is itself an outcome of the controller acting on the "
    "trajectory), so every conditioned number here carries selection (collider) bias TWICE OVER. "
    "These are DESCRIPTIVE MECHANISM READINGS, NEVER EFFECT SIZES, and a small-n cell is a "
    "mechanism reading whatever its interval says. Both rules were fixed in the ledger row before "
    "any n was known."
)

SLURP_OVERRIDE_CAVEAT = (
    "the FLOWN BLEND arm is the v2 policy, whose delta retain-override can dispatch a trajectory "
    "whose direct label WAS recovered. The LOCKED v1 cell would have RETAINED those override "
    "fires. This module takes the branch AS THE CONTROLLER ACTUALLY DECIDED IT (contacts == 2), "
    "because the sealed answers being scored are the flown v2 answers; the three-way split "
    "(retain_primary / dead_direct_dispatch / override_dispatch) is published so the v1 reading "
    "can be recovered from the same table."
)

SLURP_SECONDARY_LABEL = mve.SLURP_SECONDARY_LABEL
SLURP_EXPOSED_LABEL = mve.SLURP_EXPOSED_LABEL
A2T_EXPOSED_LABEL = mve.A2T_EXPOSED_LABEL


# ---------------------------------------------------------------------------
# The branch, READ from the sealed mechanical records
# ---------------------------------------------------------------------------


def slurp_branch(*, blend_arm) -> dict[str, dict[str, object]]:
    """The flown SLURP branch, per sample, from the sealed BLEND mechanical record.

    ``load_per_sample_mechanical`` hash-verifies the bytes at load AND
    cross-checks the override / dead-direct / recovered counts against the
    committed mechanical report, so the branch is proved twice before it is
    used once. Nothing is re-derived here: the flight's own ``contacts`` field
    IS the decision."""

    if blend_arm.pin.mechanical_sha256 != SLURP_BLEND_MECHANICAL_SHA256:
        raise ReadError(
            "the SLURP BLEND mechanical pin is not the sha256 this row registered "
            f"({blend_arm.pin.mechanical_sha256} vs {SLURP_BLEND_MECHANICAL_SHA256})"
        )
    records = d1k.load_per_sample_mechanical(arm=blend_arm)
    branch: dict[str, dict[str, object]] = {}
    for sample_id, record in records.items():
        contacts = int(record["contacts"])
        if contacts not in (1, 2):
            raise ReadError(f"{sample_id}: unexpected contact count {contacts}")
        override = bool(record["override_fires"])
        if contacts == 1:
            trajectory = "retain_primary"
        elif override:
            trajectory = "override_dispatch"
        else:
            trajectory = "dead_direct_dispatch"
        if contacts == 1 and override:
            raise ReadError(
                f"{sample_id}: the override fired but the trajectory took one contact -- the "
                "sealed record contradicts itself"
            )
        branch[sample_id] = {
            "dispatched": contacts == 2,
            "trajectory_class": trajectory,
            "contacts": contacts,
            "direct_label_recovered": bool(record["direct_label_recovered"]),
        }
    return branch


def a2t_branch(
    *, data_root: Path, sample_ids: Sequence[str]
) -> tuple[dict[str, dict[str, object]], str]:
    """The flown Audio2Tool branch, per sample, from the sealed BLEND record.

    The file is hash-verified against the value the landed gold-absence
    diagnosis report already carries BEFORE a single field is read, and the
    predicate is ``not retained_primary`` -- byte-for-byte the one
    :mod:`.cross_carrier_ceiling_decomposition` uses."""

    path = (
        Path(data_root)
        / "runs"
        / mve.A2T_RUN_ID
        / "attempt-20260825T144405Z-a2tg1blend"
        / "arm2-blend-mechanical.json"
    )
    measured = d5._require_hash(
        path, A2T_BLEND_MECHANICAL_SHA256, "A2T BLEND attempt-4 sealed mechanical record"
    )
    records = json.loads(path.read_text(encoding="utf-8"))
    missing = [sid for sid in sample_ids if sid not in records]
    if missing:
        raise ReadError(f"A2T mechanical record does not cover {missing[:5]!r}")
    branch: dict[str, dict[str, object]] = {}
    for sample_id in sample_ids:
        record = records[sample_id]
        dispatched = not bool(record["retained_primary"])
        branch[sample_id] = {
            "dispatched": dispatched,
            "trajectory_class": "dispatch" if dispatched else "retain_primary",
            "direct_label_recovered": bool(record["direct_label_recovered"]),
            "supplied_value_ids": len(record.get("fusion_selected_value_ids") or ()),
        }
        if not dispatched and branch[sample_id]["supplied_value_ids"]:
            raise ReadError(
                f"A2T {sample_id}: a RETAINED trajectory carries a non-empty supply -- the sealed "
                "record contradicts the controller's own branch semantics"
            )
    return branch, measured


# ---------------------------------------------------------------------------
# The eight-cell cross-tabulation
# ---------------------------------------------------------------------------


def cross_tabulate(
    *,
    sample_ids: Sequence[str],
    cells: Mapping[str, Sequence[str]],
    branch: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """The four matching cells crossed against DISPATCH/RETAIN.

    n is published for EVERY one of the eight cells and both sets of marginals
    are asserted to close against the population, so the table cannot silently
    drop a trajectory."""

    rows: dict[str, object] = {}
    total = 0
    dispatch_marginal = {"dispatched": 0, "retained": 0}
    for name in mve.CELL_ORDER:
        members = tuple(cells[name])
        dispatched = tuple(s for s in members if branch[s]["dispatched"])
        retained = tuple(s for s in members if not branch[s]["dispatched"])
        if len(dispatched) + len(retained) != len(members):
            raise ReadError(f"{name}: the dispatch split does not cover the matching cell")
        total += len(members)
        dispatch_marginal["dispatched"] += len(dispatched)
        dispatch_marginal["retained"] += len(retained)
        classes: dict[str, int] = {}
        for sid in members:
            key = str(branch[sid]["trajectory_class"])
            classes[key] = classes.get(key, 0) + 1
        rows[name] = {
            "definition": mve.CELL_DEFINITIONS[name],
            "n": len(members),
            "share_of_population": len(members) / len(sample_ids),
            "dispatched_n": len(dispatched),
            "retained_n": len(retained),
            "dispatched_share_of_cell": (
                len(dispatched) / len(members) if members else None
            ),
            "trajectory_classes": dict(sorted(classes.items())),
            "dispatched_ids": list(dispatched),
        }
    if total != len(sample_ids):
        raise ReadError("the eight-cell cross-tabulation does not cover the population")
    flown_dispatched = sum(1 for sid in sample_ids if branch[sid]["dispatched"])
    if dispatch_marginal["dispatched"] != flown_dispatched:
        raise ReadError("the cross-tabulation's dispatch marginal disagrees with the branch record")
    class_marginal: dict[str, int] = {}
    for sid in sample_ids:
        key = str(branch[sid]["trajectory_class"])
        class_marginal[key] = class_marginal.get(key, 0) + 1
    return {
        "cells": rows,
        "matching_marginal": {name: len(cells[name]) for name in mve.CELL_ORDER},
        "dispatch_marginal": dispatch_marginal,
        "trajectory_class_marginal": dict(sorted(class_marginal.items())),
        "n": len(sample_ids),
        "branch_asymmetry": BRANCH_ASYMMETRY_NOTE,
        "double_conditioning_caveat": DOUBLE_CONDITIONING_CAVEAT,
        "marginals_close": True,
    }


def dispatch_strata(
    *, sample_ids: Sequence[str], branch: Mapping[str, Mapping[str, object]]
) -> dict[str, tuple[str, ...]]:
    """The population split into the DISPATCHED and RETAINED strata."""

    return {
        "dispatched": tuple(s for s in sample_ids if branch[s]["dispatched"]),
        "retained": tuple(s for s in sample_ids if not branch[s]["dispatched"]),
    }


# ---------------------------------------------------------------------------
# Generic exact contribution decomposition over an arbitrary partition
# ---------------------------------------------------------------------------


def partition_contributions(
    *,
    groups: Mapping[str, Sequence[str]],
    n_total: int,
    m0_value: Mapping[str, float],
    blend_value: Mapping[str, float],
    order: Sequence[str] | None = None,
) -> dict[str, object]:
    """``sum_g (n_g / N) * (mean_blend,g - mean_m0,g)``, asserted to close.

    Same arithmetic as :func:`.matching_vs_extraction_read.joint_cell_contributions`,
    generalized to any exhaustive disjoint partition -- which is what the
    eight-cell matching-by-dispatch grid is."""

    names = tuple(order) if order is not None else tuple(groups)
    seen: set[str] = set()
    covered = 0
    rows: dict[str, object] = {}
    reconstructed = 0.0
    for name in names:
        members = tuple(groups[name])
        if seen & set(members):
            raise ReadError(f"partition group {name} overlaps an earlier group")
        seen |= set(members)
        covered += len(members)
        n_g = len(members)
        weight = n_g / n_total if n_total else 0.0
        if n_g:
            mean_m0 = sum(m0_value[sid] for sid in members) / n_g
            mean_blend = sum(blend_value[sid] for sid in members) / n_g
            delta = mean_blend - mean_m0
        else:
            mean_m0 = mean_blend = delta = 0.0
        contribution = weight * delta
        reconstructed += contribution
        rows[name] = {
            "n": n_g,
            "weight": weight,
            "M0_mean": mean_m0,
            "BLEND_mean": mean_blend,
            "delta": delta,
            "delta_points": 100.0 * delta,
            "contribution_to_aggregate_delta": contribution,
            "contribution_points": 100.0 * contribution,
        }
    if covered != n_total:
        raise ReadError(
            f"the partition covers {covered} ids but the population has {n_total}"
        )
    all_ids = tuple(sorted(seen))
    aggregate_m0 = sum(m0_value[s] for s in all_ids) / n_total if n_total else 0.0
    aggregate_blend = sum(blend_value[s] for s in all_ids) / n_total if n_total else 0.0
    aggregate_delta = aggregate_blend - aggregate_m0
    if abs(reconstructed - aggregate_delta) > 1e-9:
        raise ReadError(
            "the partition contributions do not reconstruct the aggregate delta "
            f"({reconstructed!r} vs {aggregate_delta!r})"
        )
    return {
        "groups": rows,
        "aggregate_M0_mean": aggregate_m0,
        "aggregate_BLEND_mean": aggregate_blend,
        "aggregate_delta": aggregate_delta,
        "aggregate_delta_points": 100.0 * aggregate_delta,
        "reconstructed_delta": reconstructed,
        "reconstruction_residual": reconstructed - aggregate_delta,
        "closes_to_1e_9": True,
    }


def three_way_decomposition(
    *,
    cells: Mapping[str, Sequence[str]],
    branch: Mapping[str, Mapping[str, object]],
    n_total: int,
    m0_value: Mapping[str, float],
    blend_value: Mapping[str, float],
    metric_label: str,
) -> dict[str, object]:
    """The landed (a)/(b) split, RE-DONE with dispatch in it.

    * **MATCHING-ATTRIBUTABLE** -- the two DISCORDANT matching cells
      (only-BLEND-matched, only-M0-matched), where the arms' matching outcomes
      differ, so extraction movement inside them is mechanically downstream of
      the matching movement. This is the landed document's (a) unchanged.
    * **SUPPLY-ATTRIBUTABLE** -- the two CONCORDANT matching cells restricted
      to the DISPATCHED trajectories. Only here did evidence actually reach the
      core with the matching status held fixed, so only here can a supply
      effect on extraction appear at all.
    * **DECODE-VARIANCE / UNSUPPLIED RESIDUE** -- the two CONCORDANT matching
      cells restricted to the RETAINED trajectories. These trajectories were
      handed NO evidence; the BLEND arm answered with its own contact-0 direct
      decode. Any movement here is decode variance between two separate runs of
      the same prompt, and cannot be a supply effect.

    The landed (b) term is exactly the sum of the last two, so this
    decomposition strictly refines the landed one rather than replacing it."""

    groups: dict[str, list[str]] = {
        "matching_attributable": [],
        "supply_attributable_dispatched": [],
        "decode_variance_unsupplied_retained": [],
    }
    for name in ("blend_only_matched", "m0_only_matched"):
        groups["matching_attributable"].extend(cells[name])
    for name in ("both_matched", "neither_matched"):
        for sid in cells[name]:
            if branch[sid]["dispatched"]:
                groups["supply_attributable_dispatched"].append(sid)
            else:
                groups["decode_variance_unsupplied_retained"].append(sid)
    order = (
        "matching_attributable",
        "supply_attributable_dispatched",
        "decode_variance_unsupplied_retained",
    )
    block = partition_contributions(
        groups={k: tuple(v) for k, v in groups.items()},
        n_total=n_total,
        m0_value=m0_value,
        blend_value=blend_value,
        order=order,
    )
    terms = {
        name: float(block["groups"][name]["contribution_to_aggregate_delta"]) for name in order
    }
    denominator = sum(abs(v) for v in terms.values())
    dominant = max(order, key=lambda name: abs(terms[name]))
    landed_b = (
        terms["supply_attributable_dispatched"]
        + terms["decode_variance_unsupplied_retained"]
    )
    return {
        "metric": metric_label,
        **block,
        "terms_points": {name: 100.0 * value for name, value in terms.items()},
        "share_of_absolute_total": {
            name: (abs(value) / denominator if denominator else 0.0)
            for name, value in terms.items()
        },
        "dominant_term": dominant,
        "landed_b_term_recovered_points": 100.0 * landed_b,
        "definitions": {
            "matching_attributable": (
                "the two DISCORDANT matching cells; identical to the landed document's (a) term"
            ),
            "supply_attributable_dispatched": (
                "the two CONCORDANT matching cells restricted to DISPATCHED trajectories -- the "
                "ONLY place where evidence actually reached the core with matching status held "
                "fixed, and therefore the only place a supply effect on extraction can appear"
            ),
            "decode_variance_unsupplied_retained": (
                "the two CONCORDANT matching cells restricted to RETAINED trajectories -- handed "
                "NO evidence at all; the BLEND arm answered with its own contact-0 direct decode, "
                "so any movement here is decode variance between two separate runs and cannot be "
                "a supply effect"
            ),
        },
        "refines_the_landed_split": (
            "the landed (b) 'matching-independent' term is EXACTLY the sum of the last two terms "
            "here, so this decomposition refines the landed one rather than contradicting it"
        ),
        "double_conditioning_caveat": DOUBLE_CONDITIONING_CAVEAT,
    }


# ---------------------------------------------------------------------------
# SLURP: the dispatched-versus-retained contrast
# ---------------------------------------------------------------------------


def slurp_stratum_contrast(
    *,
    label: str,
    stratum: str,
    population_label: str,
    sample_ids: Sequence[str],
    m0: mve.SlurpScored,
    blend: mve.SlurpScored,
) -> dict[str, object]:
    """One SLURP dispatch stratum: matching, macro extraction, micro extraction."""

    ids = tuple(sample_ids)
    row: dict[str, object] = {
        "label": label,
        "stratum": stratum,
        "population": population_label,
        "n": len(ids),
        "M0": mve.slurp_extraction_block(scored=m0, sample_ids=ids),
        "BLEND": mve.slurp_extraction_block(scored=blend, sample_ids=ids),
    }
    if not ids:
        row["note"] = "empty stratum -- no contrast is defined"
        return row
    universe = f"the {len(ids)} {stratum} ids of {population_label}"
    row["matching"] = d5.paired_comparison(
        label=f"MATCHING (scenario_action_exact): paired BLEND - M0 over the {stratum} stratum",
        population=f"{population_label} / {stratum}",
        sample_ids=ids,
        baseline_name="M0",
        baseline=m0.match,
        treatment_name="BLEND",
        treatment=blend.match,
    )
    row["slot_f1_exact_mean_delta_points"] = 100.0 * (
        sum(blend.slot_f1[s] for s in ids) / len(ids)
        - sum(m0.slot_f1[s] for s in ids) / len(ids)
    )
    row["slot_f1_exact_micro_f1_delta_points"] = 100.0 * (
        float(row["BLEND"]["slot_f1_exact_micro_f1"])
        - float(row["M0"]["slot_f1_exact_micro_f1"])
    )
    row["slu_f1_micro_f1_delta_points"] = 100.0 * (
        float(row["BLEND"]["slu_f1_micro_f1"]) - float(row["M0"]["slu_f1_micro_f1"])
    )
    row["bootstrap_slot_f1_exact_mean_delta"] = mve._mean_gain_block(
        sample_ids=ids,
        m0=m0.slot_f1,
        blend=blend.slot_f1,
        resampling_universe=universe,
        units="slot-F1 points (100 x per-sample-mean difference)",
    )
    row["bootstrap_slu_f1_micro_delta"] = mve._bootstrap_block(
        sample_ids=ids,
        statistic=mve._slu_micro_delta_statistic(m0=m0, blend=blend),
        resampling_universe=universe,
        units="official SLU-F1 points (100 x micro-F1 difference)",
    )
    return row


def slurp_dispatch_table(
    *,
    population_label: str,
    exposure_label: str,
    sample_ids: Sequence[str],
    m0: mve.SlurpScored,
    blend: mve.SlurpScored,
    branch: Mapping[str, Mapping[str, object]],
    m0_texts: Mapping[str, str],
    blend_texts: Mapping[str, str],
) -> dict[str, object]:
    """The full SLURP conditioned-on-dispatch reading for one population."""

    ids = tuple(sample_ids)
    cells = mve.partition_cells(sample_ids=ids, m0_match=m0.match, blend_match=blend.match)
    strata = dispatch_strata(sample_ids=ids, branch=branch)

    # The eight-cell grid, as an exhaustive partition for the decomposition.
    grid: dict[str, tuple[str, ...]] = {}
    for name in mve.CELL_ORDER:
        for stratum in DISPATCH_ORDER:
            key = f"{name}|{stratum}"
            want = stratum == "dispatched"
            grid[key] = tuple(s for s in cells[name] if bool(branch[s]["dispatched"]) is want)
    grid_order = tuple(
        f"{name}|{stratum}" for name in mve.CELL_ORDER for stratum in DISPATCH_ORDER
    )

    # Per-cell-per-stratum extraction, for the eight cells that are non-empty.
    eight_cell_extraction: dict[str, object] = {}
    for key in grid_order:
        members = grid[key]
        entry: dict[str, object] = {"n": len(members)}
        if members:
            entry["M0"] = mve.slurp_extraction_block(scored=m0, sample_ids=members)
            entry["BLEND"] = mve.slurp_extraction_block(scored=blend, sample_ids=members)
            entry["slot_f1_exact_mean_delta_points"] = 100.0 * (
                sum(blend.slot_f1[s] for s in members) / len(members)
                - sum(m0.slot_f1[s] for s in members) / len(members)
            )
            entry["slu_f1_micro_f1_delta_points"] = 100.0 * (
                float(entry["BLEND"]["slu_f1_micro_f1"])
                - float(entry["M0"]["slu_f1_micro_f1"])
            )
            entry["bootstrap_slot_f1_exact_mean_delta"] = mve._mean_gain_block(
                sample_ids=members,
                m0=m0.slot_f1,
                blend=blend.slot_f1,
                resampling_universe=f"the {len(members)} ids of {key} in {population_label}",
                units="slot-F1 points (100 x per-sample-mean difference)",
            )
            entry["bootstrap_slu_f1_micro_delta"] = mve._bootstrap_block(
                sample_ids=members,
                statistic=mve._slu_micro_delta_statistic(m0=m0, blend=blend),
                resampling_universe=f"the {len(members)} ids of {key} in {population_label}",
                units="official SLU-F1 points (100 x micro-F1 difference)",
            )
        eight_cell_extraction[key] = entry

    # Decode-variance channel, measured on THIS population's retained set.
    retained = strata["retained"]
    retained_matching_divergent = sum(
        1 for s in retained if m0.match[s] != blend.match[s]
    )
    retained_slot_divergent = sum(1 for s in retained if m0.slot_f1[s] != blend.slot_f1[s])
    retained_text_identical = sum(1 for s in retained if m0_texts[s] == blend_texts[s])

    return {
        "population": population_label,
        "exposure_label": exposure_label,
        "n": len(ids),
        "branch_asymmetry": BRANCH_ASYMMETRY_NOTE,
        "double_conditioning_caveat": DOUBLE_CONDITIONING_CAVEAT,
        "override_caveat": SLURP_OVERRIDE_CAVEAT,
        "cross_tabulation": cross_tabulate(sample_ids=ids, cells=cells, branch=branch),
        "strata": {
            stratum: slurp_stratum_contrast(
                label=f"{population_label} / {stratum.upper()}",
                stratum=stratum,
                population_label=population_label,
                sample_ids=strata[stratum],
                m0=m0,
                blend=blend,
            )
            for stratum in DISPATCH_ORDER
        },
        "eight_cell_extraction": eight_cell_extraction,
        "eight_cell_contributions_slot_f1_exact_mean": partition_contributions(
            groups=grid,
            n_total=len(ids),
            m0_value=m0.slot_f1,
            blend_value=blend.slot_f1,
            order=grid_order,
        ),
        "three_way_decomposition_slot_f1_exact_mean": three_way_decomposition(
            cells=cells,
            branch=branch,
            n_total=len(ids),
            m0_value=m0.slot_f1,
            blend_value=blend.slot_f1,
            metric_label="slot_f1_exact_mean (macro)",
        ),
        "three_way_decomposition_matching": three_way_decomposition(
            cells=cells,
            branch=branch,
            n_total=len(ids),
            m0_value={s: float(v) for s, v in m0.match.items()},
            blend_value={s: float(v) for s, v in blend.match.items()},
            metric_label="scenario_action_exact (matching)",
        ),
        "decode_variance_channel_on_retained": {
            "retained_n": len(retained),
            "retained_with_divergent_matching_outcome": retained_matching_divergent,
            "retained_with_divergent_slot_f1": retained_slot_divergent,
            "retained_divergent_slot_f1_share": (
                retained_slot_divergent / len(retained) if retained else None
            ),
            "retained_with_byte_identical_response_text": retained_text_identical,
            "retained_with_divergent_response_text": len(retained) - retained_text_identical,
            "retained_response_text_divergence_rate": (
                (len(retained) - retained_text_identical) / len(retained) if retained else None
            ),
            "interpretation": (
                "these trajectories received NO evidence, so every one of these divergences is "
                "decode variance between two separate runs of the same prompt. This is the "
                "channel measured on THIS population rather than imported from another."
            ),
        },
        "aggregate_M0": mve.slurp_extraction_block(scored=m0, sample_ids=ids),
        "aggregate_BLEND": mve.slurp_extraction_block(scored=blend, sample_ids=ids),
    }


# ---------------------------------------------------------------------------
# Audio2Tool: the dispatched-versus-retained contrast
# ---------------------------------------------------------------------------


def a2t_stratum_contrast(
    *,
    stratum: str,
    sample_ids: Sequence[str],
    m0: mve.A2tScored,
    blend: mve.A2tScored,
) -> dict[str, object]:
    ids = tuple(sample_ids)
    row: dict[str, object] = {
        "stratum": stratum,
        "population": "A2T-G1-104 (104 EXPOSED)",
        "n": len(ids),
        "M0": mve.a2t_extraction_block(scored=m0, sample_ids=ids),
        "BLEND": mve.a2t_extraction_block(scored=blend, sample_ids=ids),
    }
    if not ids:
        row["note"] = "empty stratum -- no contrast is defined"
        return row
    universe = f"the {len(ids)} {stratum} ids of A2T-G1-104"
    row["matching"] = d5.paired_comparison(
        label=f"MATCHING (tool_accuracy): paired BLEND - M0 over the {stratum} stratum",
        population=f"A2T-G1-104 / {stratum}",
        sample_ids=ids,
        baseline_name="M0",
        baseline=m0.match,
        treatment_name="BLEND",
        treatment=blend.match,
    )
    em_delta = sum(blend.exact_match[s] for s in ids) - sum(m0.exact_match[s] for s in ids)
    row["exact_match_delta_samples"] = em_delta
    row["exact_match_delta_pp"] = 100.0 * em_delta / len(ids)
    row["slot_micro_f1_delta_points"] = 100.0 * (
        float(row["BLEND"]["slot_micro_f1"]) - float(row["M0"]["slot_micro_f1"])
    )
    row["slot_predicted_total_delta"] = int(
        row["BLEND"]["slot_predicted_total"]
    ) - int(row["M0"]["slot_predicted_total"])
    row["slot_true_positives_delta"] = int(row["BLEND"]["slot_true_positives"]) - int(
        row["M0"]["slot_true_positives"]
    )
    row["bootstrap_exact_match_delta"] = mve._mean_gain_block(
        sample_ids=ids,
        m0=m0.exact_match,
        blend=blend.exact_match,
        resampling_universe=universe,
        units="exact-match percentage points",
    )
    row["bootstrap_slot_micro_f1_delta"] = mve._bootstrap_block(
        sample_ids=ids,
        statistic=mve._a2t_slot_micro_delta_statistic(m0=m0, blend=blend),
        resampling_universe=universe,
        units="slot micro-F1 points",
    )
    row["mcnemar_exact_match"] = ra.mcnemar(
        sum(1 for s in ids if m0.exact_match[s] == 0 and blend.exact_match[s] == 1),
        sum(1 for s in ids if m0.exact_match[s] == 1 and blend.exact_match[s] == 0),
    )
    return row


def a2t_triple_attribution(
    *,
    sample_ids: Sequence[str],
    m0: mve.A2tScored,
    blend: mve.A2tScored,
    branch: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Where do BLEND's EXTRA predicted argument triples come from?

    The landed document reports the A2T slot micro-F1 aggregate at -2.5781
    points, with BLEND emitting 26 more predicted argument triples (202 ->
    228) for exactly one more true positive (74 -> 75). If those extra triples
    sit in the 15 DISPATCHED trajectories, the supply caused them and the
    'empty-call repair pays for itself on the extraction axis' story is a real
    mechanism claim. If they are spread across the RETAINED trajectories --
    which received no evidence at all -- it is a mis-attribution and the true
    cause is decode variance."""

    ids = tuple(sample_ids)
    per_sample: list[dict[str, object]] = []
    totals = {
        stratum: {"predicted_delta": 0, "tp_delta": 0, "n": 0, "n_moved": 0}
        for stratum in DISPATCH_ORDER
    }
    for sid in ids:
        stratum = "dispatched" if branch[sid]["dispatched"] else "retained"
        predicted_delta = int(blend.items[sid].slot_predicted_total) - int(
            m0.items[sid].slot_predicted_total
        )
        tp_delta = int(blend.items[sid].slot_true_positives) - int(
            m0.items[sid].slot_true_positives
        )
        totals[stratum]["n"] += 1
        totals[stratum]["predicted_delta"] += predicted_delta
        totals[stratum]["tp_delta"] += tp_delta
        if predicted_delta or tp_delta:
            totals[stratum]["n_moved"] += 1
            per_sample.append(
                {
                    "sample_id": sid,
                    "stratum": stratum,
                    "trajectory_class": branch[sid]["trajectory_class"],
                    "M0_predicted_triples": int(m0.items[sid].slot_predicted_total),
                    "BLEND_predicted_triples": int(blend.items[sid].slot_predicted_total),
                    "predicted_triple_delta": predicted_delta,
                    "M0_true_positives": int(m0.items[sid].slot_true_positives),
                    "BLEND_true_positives": int(blend.items[sid].slot_true_positives),
                    "true_positive_delta": tp_delta,
                    "expected_triples": int(m0.items[sid].slot_expected_total),
                    "M0_empty_call": bool(m0.empty_call[sid]),
                    "BLEND_empty_call": bool(blend.empty_call[sid]),
                    "M0_parsed": bool(m0.parsed[sid]),
                    "BLEND_parsed": bool(blend.parsed[sid]),
                }
            )
    grand_predicted = sum(int(v["predicted_delta"]) for v in totals.values())
    grand_tp = sum(int(v["tp_delta"]) for v in totals.values())
    aggregate_m0 = mve.a2t_extraction_block(scored=m0, sample_ids=ids)
    aggregate_blend = mve.a2t_extraction_block(scored=blend, sample_ids=ids)
    if grand_predicted != int(aggregate_blend["slot_predicted_total"]) - int(
        aggregate_m0["slot_predicted_total"]
    ):
        raise ReadError("the per-sample predicted-triple deltas do not sum to the aggregate")
    if grand_tp != int(aggregate_blend["slot_true_positives"]) - int(
        aggregate_m0["slot_true_positives"]
    ):
        raise ReadError("the per-sample true-positive deltas do not sum to the aggregate")
    denominator = sum(abs(int(v["predicted_delta"])) for v in totals.values())
    return {
        "aggregate_predicted_triple_delta": grand_predicted,
        "aggregate_true_positive_delta": grand_tp,
        "M0_predicted_total": int(aggregate_m0["slot_predicted_total"]),
        "BLEND_predicted_total": int(aggregate_blend["slot_predicted_total"]),
        "M0_true_positive_total": int(aggregate_m0["slot_true_positives"]),
        "BLEND_true_positive_total": int(aggregate_blend["slot_true_positives"]),
        "expected_total": int(aggregate_m0["slot_expected_total"]),
        "by_stratum": {k: dict(v) for k, v in totals.items()},
        "dispatched_share_of_absolute_predicted_delta": (
            abs(int(totals["dispatched"]["predicted_delta"])) / denominator
            if denominator
            else None
        ),
        "per_sample_movers": per_sample,
        "sums_close": True,
        "question": (
            "are BLEND's extra predicted argument triples concentrated in the DISPATCHED "
            "trajectories (the supply caused them) or spread across the RETAINED ones (decode "
            "variance)? This block answers it by counting, not by inference."
        ),
    }


def a2t_dispatch_table(
    *,
    sample_ids: Sequence[str],
    m0: mve.A2tScored,
    blend: mve.A2tScored,
    branch: Mapping[str, Mapping[str, object]],
    m0_texts: Mapping[str, str],
    blend_texts: Mapping[str, str],
) -> dict[str, object]:
    ids = tuple(sample_ids)
    cells = mve.partition_cells(sample_ids=ids, m0_match=m0.match, blend_match=blend.match)
    strata = dispatch_strata(sample_ids=ids, branch=branch)

    grid: dict[str, tuple[str, ...]] = {}
    for name in mve.CELL_ORDER:
        for stratum in DISPATCH_ORDER:
            want = stratum == "dispatched"
            grid[f"{name}|{stratum}"] = tuple(
                s for s in cells[name] if bool(branch[s]["dispatched"]) is want
            )
    grid_order = tuple(
        f"{name}|{stratum}" for name in mve.CELL_ORDER for stratum in DISPATCH_ORDER
    )

    eight_cell_extraction: dict[str, object] = {}
    for key in grid_order:
        members = grid[key]
        entry: dict[str, object] = {"n": len(members)}
        if members:
            entry["M0"] = mve.a2t_extraction_block(scored=m0, sample_ids=members)
            entry["BLEND"] = mve.a2t_extraction_block(scored=blend, sample_ids=members)
            entry["exact_match_delta_samples"] = sum(
                blend.exact_match[s] for s in members
            ) - sum(m0.exact_match[s] for s in members)
            entry["slot_micro_f1_delta_points"] = 100.0 * (
                float(entry["BLEND"]["slot_micro_f1"]) - float(entry["M0"]["slot_micro_f1"])
            )
        eight_cell_extraction[key] = entry

    retained = strata["retained"]
    retained_match_divergent = sum(1 for s in retained if m0.match[s] != blend.match[s])
    retained_em_divergent = sum(
        1 for s in retained if m0.exact_match[s] != blend.exact_match[s]
    )
    retained_slot_divergent = sum(1 for s in retained if m0.slot_f1[s] != blend.slot_f1[s])
    retained_text_identical = sum(1 for s in retained if m0_texts[s] == blend_texts[s])

    return {
        "population": "A2T-G1-104 (104 EXPOSED)",
        "exposure_label": A2T_EXPOSED_LABEL,
        "n": len(ids),
        "branch_asymmetry": BRANCH_ASYMMETRY_NOTE,
        "double_conditioning_caveat": DOUBLE_CONDITIONING_CAVEAT,
        "cross_tabulation": cross_tabulate(sample_ids=ids, cells=cells, branch=branch),
        "strata": {
            stratum: a2t_stratum_contrast(
                stratum=stratum, sample_ids=strata[stratum], m0=m0, blend=blend
            )
            for stratum in DISPATCH_ORDER
        },
        "eight_cell_extraction": eight_cell_extraction,
        "eight_cell_contributions_exact_match": partition_contributions(
            groups=grid,
            n_total=len(ids),
            m0_value={s: float(v) for s, v in m0.exact_match.items()},
            blend_value={s: float(v) for s, v in blend.exact_match.items()},
            order=grid_order,
        ),
        "three_way_decomposition_exact_match": three_way_decomposition(
            cells=cells,
            branch=branch,
            n_total=len(ids),
            m0_value={s: float(v) for s, v in m0.exact_match.items()},
            blend_value={s: float(v) for s, v in blend.exact_match.items()},
            metric_label="exact_match (name+argument multiset)",
        ),
        "three_way_decomposition_slot_f1_mean": three_way_decomposition(
            cells=cells,
            branch=branch,
            n_total=len(ids),
            m0_value=m0.slot_f1,
            blend_value=blend.slot_f1,
            metric_label="slot_f1 macro mean",
        ),
        "three_way_decomposition_matching": three_way_decomposition(
            cells=cells,
            branch=branch,
            n_total=len(ids),
            m0_value={s: float(v) for s, v in m0.match.items()},
            blend_value={s: float(v) for s, v in blend.match.items()},
            metric_label="tool_accuracy (matching)",
        ),
        "triple_attribution": a2t_triple_attribution(
            sample_ids=ids, m0=m0, blend=blend, branch=branch
        ),
        "decode_variance_channel_on_retained": {
            "retained_n": len(retained),
            "retained_with_divergent_matching_outcome": retained_match_divergent,
            "retained_with_divergent_exact_match": retained_em_divergent,
            "retained_with_divergent_slot_f1": retained_slot_divergent,
            "retained_divergent_slot_f1_share": (
                retained_slot_divergent / len(retained) if retained else None
            ),
            "retained_with_byte_identical_response_text": retained_text_identical,
            "retained_with_divergent_response_text": len(retained) - retained_text_identical,
            "retained_response_text_divergence_rate": (
                (len(retained) - retained_text_identical) / len(retained) if retained else None
            ),
            "campaign_measured_channel_note": (
                "the A2T G1 campaign measured this carrier's multi-slot decode-variance channel "
                "at about 1.9 pp of score noise on 104 samples "
                "(docs/readiness/2026-08-25-a2t-admission-scale-sweep.md section 8); the counts "
                "here are that channel measured directly on the retained set of THIS population"
            ),
        },
        "aggregate_M0": mve.a2t_extraction_block(scored=m0, sample_ids=ids),
        "aggregate_BLEND": mve.a2t_extraction_block(scored=blend, sample_ids=ids),
    }


# ---------------------------------------------------------------------------
# The read
# ---------------------------------------------------------------------------


def read(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Execute the registered zero-contact conditioned-on-dispatch reading."""

    attempts = ra.arm_offline_guard()

    repo_root = Path(repo_root)
    data_root = Path(data_root)

    # ---------------- SLURP: load, score, and gate ------------------------
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
        arm_id: mve.score_slurp_arm(arm=arm, gold_by_sample=gold_by_sample)
        for arm_id, arm in slurp_arms.items()
    }
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

    slurp_gate: dict[str, object] = {
        "targets_source": mve.SLURP_VERDICT_RELPATH,
        "checks": [],
    }
    slurp_gate_pass = True
    id_sets = {"unexposed500": populations.new500, "exposed500": populations.dev500}
    for pop_name, ids in id_sets.items():
        for arm_id in ("M0", "BLEND"):
            target = mve.SLURP_FIDELITY_TARGETS[pop_name][arm_id]
            scored = slurp_scored[arm_id]
            measured_match = sum(scored.match[sid] for sid in ids)
            measured_mean = sum(scored.slot_f1[sid] for sid in ids) / len(ids)
            ok_match = measured_match == int(target["scenario_action_exact"])
            ok_mean = mve._float_equal(measured_mean, float(target["slot_f1_exact_mean"]))
            slurp_gate_pass = slurp_gate_pass and ok_match and ok_mean
            slurp_gate["checks"].extend(
                [
                    {
                        "population": pop_name,
                        "arm": arm_id,
                        "metric": "scenario_action_exact",
                        "target": int(target["scenario_action_exact"]),
                        "measured": measured_match,
                        "pass": ok_match,
                    },
                    {
                        "population": pop_name,
                        "arm": arm_id,
                        "metric": "slot_f1_exact_mean",
                        "target": float(target["slot_f1_exact_mean"]),
                        "measured": measured_mean,
                        "target_repr": repr(float(target["slot_f1_exact_mean"])),
                        "measured_repr": repr(measured_mean),
                        "pass": ok_mean,
                    },
                ]
            )
    slurp_gate["pass"] = slurp_gate_pass

    # ---------------- A2T: load, score, and gate --------------------------
    from ..data.audio2tool import load_expected_calls
    from ..data.lock import load_lock, umbrella_lock_path
    from ..rails.adapters.audio2tool import Audio2ToolAdapter

    receipt_path = repo_root / mve.A2T_RECEIPT_RELPATH
    d5._require_hash(receipt_path, mve.A2T_RECEIPT_SHA256, "A2T-G1-104 committed receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    a2t_ids = tuple(sorted(str(item["sample_id"]) for item in receipt["items"]))
    if len(a2t_ids) != int(receipt["count"]) or len(set(a2t_ids)) != len(a2t_ids):
        raise ReadError("the A2T-G1-104 receipt count disagrees with its items")

    lock = load_lock(umbrella_lock_path(repo_root))
    adapter = Audio2ToolAdapter(lock, data_root, repo_root=repo_root)
    a2t_gold = load_expected_calls(lock, data_root, repo_root=repo_root)
    a2t_responses = {
        pin.arm_id: mve.load_a2t_arm(pin=pin, repo_root=repo_root, data_root=data_root)
        for pin in mve.A2T_ARM_PINS
    }
    for arm_id, responses in a2t_responses.items():
        if tuple(sorted(responses)) != a2t_ids:
            raise ReadError(f"A2T {arm_id}: sealed outputs do not cover exactly A2T-G1-104")
    a2t_scored = {
        arm_id: mve.score_a2t_arm(adapter=adapter, gold=a2t_gold, responses=responses)
        for arm_id, responses in a2t_responses.items()
    }

    a2t_gate: dict[str, object] = {"targets_source": mve.A2T_VERDICT_RELPATH, "checks": []}
    a2t_gate_pass = True
    for arm_id in ("M0", "BLEND"):
        scored = a2t_scored[arm_id]
        target = mve.A2T_FIDELITY_TARGETS[arm_id]
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

    if not (slurp_gate_pass and a2t_gate_pass):
        failures = [c for c in slurp_gate["checks"] + a2t_gate["checks"] if not c["pass"]]
        raise ReadError(
            "FIDELITY GATE FAILED -- the re-scoring path differs from the flown one and NOTHING "
            f"downstream is trustworthy. Failing checks: {json.dumps(failures)}"
        )

    # ---------------- The branch, READ ------------------------------------
    slurp_branch_all = slurp_branch(blend_arm=slurp_arms["BLEND"])
    a2t_branch_map, a2t_mechanical_sha = a2t_branch(data_root=data_root, sample_ids=a2t_ids)

    # ---------------- The conditioned tables ------------------------------
    slurp_tables = {
        "unexposed500": slurp_dispatch_table(
            population_label="DEV-1000-NEW500 (500 UNEXPOSED)",
            exposure_label=SLURP_SECONDARY_LABEL,
            sample_ids=populations.new500,
            m0=slurp_scored["M0"],
            blend=slurp_scored["BLEND"],
            branch=slurp_branch_all,
            m0_texts=slurp_arms["M0"].responses,
            blend_texts=slurp_arms["BLEND"].responses,
        ),
        "exposed500": slurp_dispatch_table(
            population_label="DEV-500 (500 PRIOR-EXPOSED)",
            exposure_label=SLURP_EXPOSED_LABEL,
            sample_ids=populations.dev500,
            m0=slurp_scored["M0"],
            blend=slurp_scored["BLEND"],
            branch=slurp_branch_all,
            m0_texts=slurp_arms["M0"].responses,
            blend_texts=slurp_arms["BLEND"].responses,
        ),
    }
    a2t_table = a2t_dispatch_table(
        sample_ids=a2t_ids,
        m0=a2t_scored["M0"],
        blend=a2t_scored["BLEND"],
        branch=a2t_branch_map,
        m0_texts=a2t_responses["M0"],
        blend_texts=a2t_responses["BLEND"],
    )

    return {
        "schema": SCHEMA,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "exposure_row": EXPOSURE_ROW_ID,
        "ledger_commit": LEDGER_COMMIT,
        "audited_document": {
            "path": AUDITED_DOCUMENT_RELPATH,
            "commit": AUDITED_DOCUMENT_COMMIT,
            "receipt": AUDITED_RECEIPT_RELPATH,
            "receipt_sha256": AUDITED_RECEIPT_SHA256,
            "defect_under_test": (
                "the landed read partitioned on the two arms' MATCHING outcome only and never "
                "conditioned on whether the trajectory RECEIVED SUPPLY. A RETAINED trajectory "
                "stops at contact 0 and is handed no evidence at all, so a retained-dominated "
                "cell cannot exhibit a supply effect -- not because the supply fails but because "
                "there was none."
            ),
        },
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "targets": list(attempts.targets),
            "armed_before_first_input": True,
            "resident_llama_server": "pid 38623 port 8090 NOT contacted, probed, reconfigured or stopped",
        },
        "spend": {
            "frozen_core_contacts": 0,
            "embedding_tool_contacts": 0,
            "tokenizer_contacts": 0,
            "http_or_socket_requests": 0,
            "audio_seconds": 0,
            "gpu_hours": 0.0,
            "new_dependencies": 0,
        },
        "fidelity_gate": {
            "pass": True,
            "slurp": slurp_gate,
            "a2t": a2t_gate,
            "note": (
                "identical to the landed read's gate: the four sealed output files are re-scored "
                "through the SAME imported path and must reproduce the landed aggregates to the "
                "sample and to full float precision, else the read STOPS."
            ),
        },
        "branch_sources": {
            "slurp": {
                "artifact": (
                    f"$SPEECHRL_DATA_DIR/runs/{d1k.RUN_ID}/"
                    f"{slurp_arms['BLEND'].pin.attempt_id}/"
                    f"{slurp_arms['BLEND'].pin.mechanical_basename}"
                ),
                "sha256": SLURP_BLEND_MECHANICAL_SHA256,
                "predicate": "DISPATCH := contacts == 2; RETAIN := contacts == 1",
                "sub_split": (
                    "the dispatch side is split by override_fires into dead_direct_dispatch and "
                    "override_dispatch, exactly as dev1000_lock_read.dispatch_decomposition does"
                ),
                "cross_checked_against": (
                    "the committed arm2-blend-mechanical-report.json retain_override block and "
                    "the per-sample contact counts, by load_per_sample_mechanical"
                ),
                "override_caveat": SLURP_OVERRIDE_CAVEAT,
            },
            "a2t": {
                "artifact": (
                    f"$SPEECHRL_DATA_DIR/runs/{mve.A2T_RUN_ID}/"
                    "attempt-20260825T144405Z-a2tg1blend/arm2-blend-mechanical.json"
                ),
                "sha256": a2t_mechanical_sha,
                "registered_sha256": A2T_BLEND_MECHANICAL_SHA256,
                "predicate": "DISPATCH := not retained_primary",
                "cross_checked_against": (
                    "asserted per sample: a RETAINED trajectory must carry an EMPTY "
                    "fusion_selected_value_ids list"
                ),
                "source_of_the_registered_hash": (
                    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-gold-absence/"
                    "diagnosis-report.json"
                ),
            },
            "asymmetry": BRANCH_ASYMMETRY_NOTE,
        },
        "slurp": slurp_tables,
        "a2t": a2t_table,
        "governance": {
            "slurp_unexposed500": SLURP_SECONDARY_LABEL,
            "slurp_exposed500": SLURP_EXPOSED_LABEL,
            "a2t": A2T_EXPOSED_LABEL,
            "double_conditioning": DOUBLE_CONDITIONING_CAVEAT,
            "authorizes": (
                "NOTHING. No knob change, no re-tune, no re-flight, no new arm, no threshold "
                "move, no claim, no test contact, no new population, no G2 opening, no Stage-3 "
                "activity. The DEV-1000 LOCK stands exactly as landed at d9fef537."
            ),
        },
        "uncertainty": {
            "primitive": "analysis.bootstrap.paired_cluster_bootstrap via dev100_reviewer_audit.bootstrap_gain",
            "n_replicates": BOOTSTRAP_N,
            "seed": BOOTSTRAP_SEED,
            "intervals": "90% and 95% percentile",
            "label_erratum": mve.BOOTSTRAP_LABEL_ERRATUM,
        },
    }


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "EXTRACTION CONDITIONED ON DISPATCH: the zero-contact follow-up reading over the "
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

    print(f"FIDELITY GATE: {'PASS' if report['fidelity_gate']['pass'] else 'FAIL'}")
    print(
        "offline guard outbound attempts: "
        f"{report['offline_guard']['outbound_connection_attempts']}"
    )
    for key, table in report["slurp"].items():
        xtab = table["cross_tabulation"]
        print(f"\nSLURP {key} (n={table['n']}) -- dispatch marginal {xtab['dispatch_marginal']}")
        for name in mve.CELL_ORDER:
            row = xtab["cells"][name]
            print(
                f"  {name:>20}: n={row['n']:>4}  dispatched={row['dispatched_n']:>4}  "
                f"retained={row['retained_n']:>4}"
            )
        for stratum in DISPATCH_ORDER:
            block = table["strata"][stratum]
            if not block["n"]:
                continue
            print(
                f"  [{stratum}] n={block['n']}  macro slot-F1 "
                f"{block['slot_f1_exact_mean_delta_points']:+.4f} pts  official SLU-F1 "
                f"{block['slu_f1_micro_f1_delta_points']:+.4f} pts"
            )
        three = table["three_way_decomposition_slot_f1_exact_mean"]
        print(f"  three-way: {three['terms_points']}  dominant={three['dominant_term']}")

    xtab = report["a2t"]["cross_tabulation"]
    print(f"\nA2T (n={report['a2t']['n']}) -- dispatch marginal {xtab['dispatch_marginal']}")
    for name in mve.CELL_ORDER:
        row = xtab["cells"][name]
        print(
            f"  {name:>20}: n={row['n']:>4}  dispatched={row['dispatched_n']:>4}  "
            f"retained={row['retained_n']:>4}"
        )
    print(f"  triple attribution: {report['a2t']['triple_attribution']['by_stratum']}")

    digest = _sha256_bytes(payload.encode("utf-8"))
    print(f"\nreport: {out_path}\nsha256: {digest}")
    return 0


__all__ = [
    "SCHEMA",
    "EXPOSURE_ROW_ID",
    "CHECK_DIR_RELPATH",
    "DISPATCH_ORDER",
    "slurp_branch",
    "a2t_branch",
    "cross_tabulate",
    "dispatch_strata",
    "partition_contributions",
    "three_way_decomposition",
    "slurp_stratum_contrast",
    "slurp_dispatch_table",
    "a2t_stratum_contrast",
    "a2t_triple_attribution",
    "a2t_dispatch_table",
    "read",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
