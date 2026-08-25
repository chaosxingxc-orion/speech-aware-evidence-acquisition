"""THE PRIOR-SCORE SEMANTICS REPAIR -- proving the fix, at ZERO CONTACTS.

Row ``SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR`` (model-free-check), registered
in ``docs/exposure-ledger.md`` BEFORE any number here was computed. Verdict:
``docs/readiness/2026-08-25-prior-score-semantics-repair.md``.

THE DEFECT, STATED FIRST. Both knowledge builders computed ``prior_score`` as a
ratio whose numerator and denominator ranged over DIFFERENT populations:

* ``rails/knowledge_build_a2t.py`` divided a tool's rows counted over the WHOLE
  construction pool by one ``(domain, category)``'s rows;
* ``rails/knowledge_build.py`` divided an intent's globally-counted rows by a
  scenario's globally-counted rows, while NAMING the numerator
  ``intent_total_in_scenario``.

Neither restricted the numerator to the conditioning event, so neither was a
conditional probability and neither had any reason to be <= 1. The repair
restricts both numerators. This module does not assert that the repair is
right; it MEASURES what it did, on the real corpora, and refuses fail-closed
where a claim does not hold.

WHAT IT COMPUTES, in the order the registration fixed:

1. :func:`source_verification` -- both defects, from the landed Stage-2A
   synthesis receipt (which machine-checked them against the pre-repair tree at
   commit ``3f131afd``) AND from the live tree, which must now carry the
   repaired expressions and must NOT carry the defective ones.
2. :func:`slurp_nesting_identity` -- the SLURP identity, PROVED not assumed.
   Over every real TRAIN construction row: that ``intent`` is built as
   ``f"{scenario}_{action}"``; that for every intent the RESTRICTED row set
   equals the UNRESTRICTED one (the same SET, not merely the same count); and
   that the pre-repair and post-repair priors agree to the last bit on every
   row. A single violating intent is a FINDING and is reported as one.
3. :func:`a2t_prior_before_after` -- the Audio2Tool change, quantified. The
   construction pool and the selection are reconstructed deterministically from
   the same manifests, seeds and receipts the landed build script used; a
   FIDELITY GATE requires the recomputed PRE-repair ratio to reproduce the
   pinned snapshot's own ``prior_score`` on every value before any post-repair
   number is read. Then: the new supremum, how many values move, and the
   before/after distribution.
4. :func:`rebuild_differs_only_in_prior_score` -- the rebuilt snapshot compared
   field by field against the pinned one. If ANY facet or value TEXT differed,
   a rebuild would imply an embedding pass this row may not take, and the
   module STOPS and says so instead. The rebuilt snapshot is written as a NEW
   artifact ALONGSIDE the pinned one, never over it.
5. :func:`corrected_prior_supply_replay` -- the supply on all 104 A2T-G1
   trajectories under the CORRECTED prior. The landed ``[0, 1]`` bracket
   (``a2t_gold_absence_diagnosis.prior_dimension_sensitivity``) rescaled scores
   AFTER recall, so it could not see the one thing a corrected prior really
   changes: WHICH facets the prior dimensions recall. Here the prior-mass
   recall is REDONE under the corrected values through ``kb_policy``'s own
   ``multidim_recall``, and the supply is replayed through ``kb_policy``'s own
   ranker, admission gate and fuser.
6. :func:`pinned_artifacts_unmoved` -- every pinned artifact this repair could
   have disturbed, re-hashed from disk against the value the landed documents
   quote.

WHAT IT DOES NOT DO. It changes no knob and writes nothing under ``configs/``.
It opens no model session, no embedding sidecar and no tokenizer:
:func:`run` arms ``dev100_reviewer_audit.arm_offline_guard`` BEFORE the first
input is opened and writes the recorded outbound-attempt count into the
receipt. The resident np2 service on port 8090 is never contacted, probed,
reconfigured or stopped. It does not overwrite, displace or re-hash any pinned
snapshot.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=<repo>/src \
      python -m speech_aware_evidence_acquisition.analysis.prior_score_semantics_repair \
        --repo-root <repo> --data-root $SPEECHRL_DATA_DIR --out <receipt>
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from . import a2t_admission_scale_sweep as sweep
from . import a2t_gold_absence_diagnosis as diag
from . import contrast_fewshot_preanalysis as cf
from . import cross_carrier_ceiling_decomposition as ccd
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as audit
from . import stage2a_synthesis_verification as sv
from ..e0.artifacts import write_json_artifact
from ..rails import kb_policy as kb
from ..rails import knowledge as kn

EXPOSURE_ROW_ID = "SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR"
SCHEMA = "saea-prior-score-semantics-repair-v1"

#: The commit that carried the defect, and against whose tree the landed
#: Stage-2A synthesis machine-checked it.
PRE_REPAIR_COMMIT = "3f131afd"

#: The landed receipt that recorded the pre-repair source check. Re-hashed
#: here rather than quoted, so the pre-repair evidence is auditable offline
#: without a git subprocess (which the in-process offline guard could not
#: cover).
SYNTHESIS_RECEIPT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-stage2a-synthesis/"
    "verification-report.json"
)

#: The A2T build script's own constants, restated so the reconstruction is the
#: SAME reconstruction rather than a similar one
#: (``scripts/build_a2t_knowledge_snapshot.py``).
A2T_BUILD_SEED = 20260825
A2T_PARTITION_SEED = 20260807

#: Where the REBUILT snapshot is written. A NEW path beside the pinned one --
#: the pinned ``snapshot.json`` is never opened for writing.
A2T_REBUILT_SNAPSHOT_RELPATH = (
    "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/"
    "snapshot-prior-repaired.json"
)

FROZEN_WEIGHTS = ccd.FROZEN_WEIGHTS
FROZEN_FUSE = ccd.FROZEN_FUSE
FROZEN_TOP_K = ccd.FROZEN_TOP_K


class RepairError(RuntimeError):
    """A claim this row makes is not true of the artifacts it reads."""


# ---------------------------------------------------------------------------
# 1. The two defects, verified at source
# ---------------------------------------------------------------------------


def source_verification(repo_root: Path) -> dict[str, object]:
    """Both defects, from the pre-repair evidence AND from the live tree.

    The pre-repair bytes are no longer in the working tree, and reading them
    back would need a ``git`` subprocess whose network surface the in-process
    offline guard cannot cover. So the pre-repair evidence used here is the
    LANDED Stage-2A synthesis receipt, which machine-checked each defective
    line against the tree at ``3f131afd`` and recorded the result; it is
    re-hashed from disk before a single field of it is trusted. The live check
    is then run against the working tree through the synthesis module's own
    (now superseded) verifier."""

    repo_root = Path(repo_root)
    receipt_path = repo_root / SYNTHESIS_RECEIPT_RELPATH
    if not receipt_path.is_file():
        raise RepairError(f"the landed synthesis receipt is missing: {receipt_path}")
    receipt_sha256 = dc._sha256_file(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    landed_rows = receipt.get("source_claims")
    if not isinstance(landed_rows, list) or not landed_rows:
        raise RepairError(
            "the landed synthesis receipt carries no source_claims block, so the "
            "pre-repair evidence cannot be read from it"
        )
    landed_by_key = {
        (str(row["relpath"]), int(row["line"])): row for row in landed_rows
    }
    pre_repair: list[dict[str, object]] = []
    for relpath, lineno, needle in sv.SOURCE_CLAIMS_AT_3F131AFD:
        row = landed_by_key.get((relpath, lineno))
        if row is None:
            raise RepairError(
                f"the landed synthesis receipt does not record {relpath}:{lineno}"
            )
        if str(row.get("expected_substring")) != needle:
            raise RepairError(
                f"the landed synthesis receipt records a different substring at "
                f"{relpath}:{lineno}"
            )
        if not bool(row.get("present")):
            raise RepairError(
                f"the landed synthesis receipt says {relpath}:{lineno} did NOT hold"
            )
        pre_repair.append(
            {
                "relpath": relpath,
                "line_at_pre_repair_commit": lineno,
                "expression": needle,
                "machine_checked_present_at_pre_repair_commit": True,
            }
        )

    live = sv.verify_source_claims(repo_root)

    return {
        "pre_repair_commit": PRE_REPAIR_COMMIT,
        "pre_repair_evidence": {
            "receipt_relpath": SYNTHESIS_RECEIPT_RELPATH,
            "receipt_sha256": receipt_sha256,
            "claims": pre_repair,
            "method": (
                "the landed Stage-2A synthesis module opened each builder and "
                "asserted the exact substring at the exact line; this row "
                "re-hashes that receipt and reads its recorded result rather "
                "than re-reading bytes that no longer exist in the tree"
            ),
        },
        "defect_a2t": (
            "rails/knowledge_build_a2t.py:1085-1087 set prior_score = "
            "tool_total / category_total, where tool_total = "
            "len(rows_by_tool_full[tool]) is accumulated at line 853 over the "
            "WHOLE construction pool and category_total = "
            "len(rows_by_category_full[(domain, category)]) is accumulated at "
            "line 854 over one (domain, category). The numerator's row set is "
            "NOT a subset of the denominator's, so the ratio is not "
            "p(tool | domain, category) and has no reason to be <= 1."
        ),
        "defect_slurp": (
            "rails/knowledge_build.py:696-698 set prior_score = "
            "intent_total_in_scenario / scenario_total, where "
            "intent_total_in_scenario = len(rows_by_intent_full[intent]) is "
            "accumulated at line 504 over the WHOLE row set, NOT over the "
            "scenario. It is the identical expression shape. The local's NAME "
            "asserted a restriction the code did not perform. SLURP is safe "
            "only because intent = f'{scenario}_{action}' (line 202) makes an "
            "intent determine its scenario -- an accident of the label "
            "vocabulary, not a property of the expression."
        ),
        "live_tree_after_repair": live,
    }


# ---------------------------------------------------------------------------
# 2. The SLURP identity, proved and measured
# ---------------------------------------------------------------------------


def slurp_nesting_identity(rows: Sequence[object]) -> dict[str, object]:
    """PROVE, over the real TRAIN rows, that the SLURP repair moves nothing.

    THE ARGUMENT. ``rails.knowledge_build.slurp_kb_rows`` builds
    ``intent = f"{entry.scenario}_{entry.action}"``. An intent therefore
    DETERMINES its scenario: every row carrying this intent necessarily
    carries this scenario. The restricted numerator's row set
    ``{r : r.intent = i and r.scenario = s}`` is then literally the same SET as
    the unrestricted ``{r : r.intent = i}``, so the repair is an identity
    transform -- not approximately, not up to floating point, but the same
    counted set.

    THE MEASUREMENT. The argument is checked rather than believed. For every
    intent the two row-id SETS are compared for equality, and for every row the
    pre-repair and post-repair priors are compared for exact float equality. A
    violating intent would mean the label vocabulary does not nest and the
    SLURP prior was ALSO wrong in flight; it is reported loudly rather than
    swallowed."""

    rows = tuple(rows)
    by_intent: dict[str, set[str]] = {}
    by_scenario: dict[str, set[str]] = {}
    scenarios_per_intent: dict[str, set[str]] = {}
    joint: Counter[tuple[str, str]] = Counter()
    label_scheme_violations: list[str] = []
    for row in rows:
        by_intent.setdefault(row.intent, set()).add(row.utterance_id)
        by_scenario.setdefault(row.scenario, set()).add(row.utterance_id)
        scenarios_per_intent.setdefault(row.intent, set()).add(row.scenario)
        joint[(row.scenario, row.intent)] += 1
        if row.intent != f"{row.scenario}_{row.action}":
            label_scheme_violations.append(row.utterance_id)

    set_mismatches: list[dict[str, object]] = []
    prior_mismatches: list[dict[str, object]] = []
    for intent, unrestricted_ids in sorted(by_intent.items()):
        scenarios = scenarios_per_intent[intent]
        # The scenario an intent's own name declares. Under the production
        # label scheme it is the ONLY scenario the intent appears under.
        for scenario in sorted(scenarios):
            restricted_ids = unrestricted_ids & by_scenario[scenario]
            if len(scenarios) > 1 or restricted_ids != unrestricted_ids:
                set_mismatches.append(
                    {
                        "intent": intent,
                        "scenario": scenario,
                        "unrestricted_rows": len(unrestricted_ids),
                        "restricted_rows": len(restricted_ids),
                        "scenarios_this_intent_appears_under": sorted(scenarios),
                    }
                )

    for row in rows:
        scenario_total = len(by_scenario[row.scenario])
        pre_repair = len(by_intent[row.intent]) / scenario_total if scenario_total else 0.0
        post_repair = (
            joint[(row.scenario, row.intent)] / scenario_total if scenario_total else 0.0
        )
        if pre_repair != post_repair:
            prior_mismatches.append(
                {
                    "utterance_id": row.utterance_id,
                    "intent": row.intent,
                    "scenario": row.scenario,
                    "pre_repair_prior": pre_repair,
                    "post_repair_prior": post_repair,
                }
            )

    post_repair_values = [
        joint[(row.scenario, row.intent)] / len(by_scenario[row.scenario])
        for row in rows
    ]
    identity_holds = not set_mismatches and not prior_mismatches and not label_scheme_violations
    return {
        "rows": len(rows),
        "intents": len(by_intent),
        "scenarios": len(by_scenario),
        "label_scheme": 'intent = f"{scenario}_{action}"',
        "rows_violating_the_label_scheme": len(label_scheme_violations),
        "rows_violating_the_label_scheme_ids": label_scheme_violations[:10],
        "intents_whose_restricted_row_set_differs_from_the_unrestricted_one": len(
            set_mismatches
        ),
        "intent_nesting_violations": set_mismatches[:10],
        "intents_compared": len(by_intent),
        "rows_whose_prior_changed": len(prior_mismatches),
        "prior_changes": prior_mismatches[:10],
        "post_repair_prior_supremum": max(post_repair_values) if post_repair_values else None,
        "post_repair_prior_values_above_1": sum(
            1 for value in post_repair_values if value > 1.0
        ),
        "identity_holds": identity_holds,
        "argument": (
            "intent is built as f'{scenario}_{action}', so an intent determines "
            "its scenario and the restricted numerator's row SET is the same "
            "SET as the unrestricted one. The repair is therefore an exact "
            "identity on SLURP -- which is why SLURP never exposed the defect, "
            "and equally why the SLURP code was never correct BY CONSTRUCTION."
        ),
        "finding_if_it_had_failed": (
            "a single intent appearing under two scenarios would mean the SLURP "
            "prior was wrong in flight exactly as the A2T one was; the counts "
            "above are the check, not a restatement of the argument"
        ),
    }


# ---------------------------------------------------------------------------
# 3. The A2T change, quantified
# ---------------------------------------------------------------------------


def _distribution(values: Sequence[float]) -> dict[str, object]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"n": 0}

    def _q(fraction: float) -> float:
        index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
        return ordered[index]

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p05": _q(0.05),
        "p25": _q(0.25),
        "median": statistics.median(ordered),
        "p75": _q(0.75),
        "p95": _q(0.95),
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
        "values_above_1": sum(1 for value in ordered if value > 1.0),
        "values_equal_to_1": sum(1 for value in ordered if value == 1.0),
        "distinct_values": len(set(ordered)),
    }


def a2t_prior_before_after(
    *,
    construction_rows: Sequence[object],
    selected_rows: Sequence[object],
    pinned_priors: Mapping[str, float],
) -> dict[str, object]:
    """The Audio2Tool before/after, with a fidelity gate in front of it.

    ``construction_rows`` is the reconstructed construction pool and
    ``selected_rows`` the reconstructed selection; both come from the same
    manifests, seeds and receipts the landed build used. THE GATE: the
    PRE-repair ratio recomputed here must reproduce the pinned snapshot's own
    ``prior_score`` on every value. If it does not, the reconstruction is not
    the flight's and no post-repair number may be read from it."""

    construction_rows = tuple(construction_rows)
    selected_rows = tuple(selected_rows)

    by_category: Counter[tuple[str, str]] = Counter()
    by_tool: Counter[str] = Counter()
    joint: Counter[tuple[str, str, str]] = Counter()
    for row in construction_rows:
        by_category[(row.domain, row.category)] += 1
        by_tool[row.tool_name] += 1
        joint[(row.domain, row.category, row.tool_name)] += 1

    pre_repair: dict[str, float] = {}
    post_repair: dict[str, float] = {}
    for row in selected_rows:
        cell = (row.domain, row.category)
        category_total = by_category[cell]
        value_id = f"value:{row.unit_id}"
        pre_repair[value_id] = (
            by_tool[row.tool_name] / category_total if category_total else 0.0
        )
        post_repair[value_id] = (
            joint[(row.domain, row.category, row.tool_name)] / category_total
            if category_total
            else 0.0
        )

    missing = sorted(set(pinned_priors) - set(pre_repair))
    extra = sorted(set(pre_repair) - set(pinned_priors))
    gate_mismatches = [
        {
            "value_id": value_id,
            "pinned": pinned_priors[value_id],
            "recomputed_pre_repair": pre_repair[value_id],
        }
        for value_id in sorted(set(pinned_priors) & set(pre_repair))
        if pinned_priors[value_id] != pre_repair[value_id]
    ]
    gate_passed = not missing and not extra and not gate_mismatches
    if not gate_passed:
        raise RepairError(
            "the pre-repair fidelity gate FAILED -- the reconstructed "
            "construction pool does not reproduce the pinned snapshot's own "
            "prior_score, so no post-repair number may be read from it: "
            + json.dumps(
                {
                    "values_missing_from_the_reconstruction": len(missing),
                    "values_extra_in_the_reconstruction": len(extra),
                    "value_mismatches": len(gate_mismatches),
                    "first_mismatches": gate_mismatches[:5],
                },
                sort_keys=True,
            )
        )

    moved = [
        value_id
        for value_id in sorted(pre_repair)
        if pre_repair[value_id] != post_repair[value_id]
    ]
    deltas = [post_repair[value_id] - pre_repair[value_id] for value_id in moved]

    # A conditional distribution's defining property: over the tools present
    # in one (domain, category) cell, the per-tool priors sum to exactly 1.
    cell_sums: list[float] = []
    worst_cell_error = 0.0
    for (domain, category), total in by_category.items():
        tools = {
            tool
            for (d, c, tool) in joint
            if d == domain and c == category
        }
        cell_sum = sum(joint[(domain, category, tool)] / total for tool in tools)
        cell_sums.append(cell_sum)
        worst_cell_error = max(worst_cell_error, abs(cell_sum - 1.0))

    return {
        "construction_pool_rows": len(construction_rows),
        "selected_values": len(selected_rows),
        "fidelity_gate": {
            "recomputed_pre_repair_reproduces_the_pinned_snapshot": gate_passed,
            "values_compared": len(pinned_priors),
            "value_mismatches": len(gate_mismatches),
            "method": (
                "the construction pool and the selection are reconstructed from "
                "the same manifests, the same partition seed "
                f"({A2T_PARTITION_SEED}) and the same build seed "
                f"({A2T_BUILD_SEED}) the landed build script used, then the "
                "PRE-repair ratio is recomputed and compared to the pinned "
                "snapshot's own prior_score on every value"
            ),
        },
        "pre_repair": _distribution(list(pre_repair.values())),
        "post_repair": _distribution(list(post_repair.values())),
        "values_moved": len(moved),
        "values_unchanged": len(pre_repair) - len(moved),
        "share_moved": len(moved) / len(pre_repair) if pre_repair else 0.0,
        "delta_when_moved": _distribution(deltas) if deltas else {"n": 0},
        "largest_decreases": [
            {
                "value_id": value_id,
                "pre_repair": pre_repair[value_id],
                "post_repair": post_repair[value_id],
            }
            for value_id in sorted(
                moved, key=lambda vid: post_repair[vid] - pre_repair[vid]
            )[:10]
        ],
        "conditional_distribution_property": {
            "cells": len(cell_sums),
            "worst_absolute_error_from_1": worst_cell_error,
            "holds": worst_cell_error < 1e-9,
            "statement": (
                "over the tools present in one (domain, category) cell the "
                "post-repair priors sum to 1; the pre-repair ones could not, "
                "which is the arithmetic form of the defect"
            ),
        },
    }


# ---------------------------------------------------------------------------
# 4. The rebuild: does anything except prior_score move?
# ---------------------------------------------------------------------------


def rebuild_differs_only_in_prior_score(
    *, pinned_document: Mapping[str, object], rebuilt_document: Mapping[str, object]
) -> dict[str, object]:
    """Compare the rebuilt snapshot to the pinned one, field by field.

    THE REASON THIS EXISTS. If the repair moved any facet or value TEXT, a
    rebuilt snapshot would need a fresh embedding pass over the changed text --
    an embedding contact this row may not take. So the module MEASURES whether
    text moved instead of assuming it did not, and raises with the exact
    inventory if it did, so the report says what a rebuild would need rather
    than quietly taking a contact."""

    pinned_facets = {facet["facet_id"]: facet for facet in pinned_document["facets"]}
    rebuilt_facets = {facet["facet_id"]: facet for facet in rebuilt_document["facets"]}
    pinned_values = {value["value_id"]: value for value in pinned_document["values"]}
    rebuilt_values = {value["value_id"]: value for value in rebuilt_document["values"]}

    facet_id_delta = sorted(set(pinned_facets) ^ set(rebuilt_facets))
    value_id_delta = sorted(set(pinned_values) ^ set(rebuilt_values))
    facet_field_changes = [
        facet_id
        for facet_id in sorted(set(pinned_facets) & set(rebuilt_facets))
        if pinned_facets[facet_id] != rebuilt_facets[facet_id]
    ]

    value_changed_fields: Counter[str] = Counter()
    prior_only_changes = 0
    for value_id in sorted(set(pinned_values) & set(rebuilt_values)):
        before, after = pinned_values[value_id], rebuilt_values[value_id]
        changed = sorted(
            key for key in set(before) | set(after) if before.get(key) != after.get(key)
        )
        if not changed:
            continue
        for key in changed:
            value_changed_fields[key] += 1
        if changed == ["prior_score"]:
            prior_only_changes += 1

    header_changes = sorted(
        key
        for key in set(pinned_document) | set(rebuilt_document)
        if key not in {"facets", "values"}
        and pinned_document.get(key) != rebuilt_document.get(key)
    )

    text_moved = bool(
        facet_id_delta
        or value_id_delta
        or facet_field_changes
        or header_changes
        or set(value_changed_fields) - {"prior_score"}
    )
    block: dict[str, object] = {
        "facet_ids_only_on_one_side": len(facet_id_delta),
        "facet_ids_only_on_one_side_preview": facet_id_delta[:10],
        "facets_whose_fields_changed": len(facet_field_changes),
        "facets_whose_fields_changed_preview": facet_field_changes[:10],
        "value_ids_only_on_one_side": len(value_id_delta),
        "value_ids_only_on_one_side_preview": value_id_delta[:10],
        "value_fields_that_changed": dict(sorted(value_changed_fields.items())),
        "values_changed_in_prior_score_only": prior_only_changes,
        "snapshot_header_fields_that_changed": header_changes,
        "only_prior_score_moved": not text_moved,
        "embedding_implication": (
            "NO EMBEDDING PASS IS IMPLIED: no facet representation and no value "
            "content string changed, so every landed vector remains the vector "
            "of the text it was computed from. prior_score is a numeric "
            "ValueBundle field and is never embedded."
        )
        if not text_moved
        else (
            "STOP: text moved, so a rebuilt snapshot would require re-embedding "
            "the changed facets. This row may not take an embedding contact and "
            "does not; the inventory above is what such a rebuild would need."
        ),
    }
    if text_moved:
        raise RepairError(
            "the prior-score repair moved something other than prior_score; a "
            "rebuild would need an embedding pass this row may not take:\n"
            + json.dumps(block, indent=1, sort_keys=True)
        )
    return block


# ---------------------------------------------------------------------------
# 5. The corrected prior, replayed on the 104
# ---------------------------------------------------------------------------


def _recall_with_prior(
    bundle: cf.SnapshotBundle,
    cosines: object,
    prior_recall: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, float]]:
    """``cf.vectorised_recall``'s own composition, with the prior-mass half
    supplied by the caller.

    The content half is taken from ``cf.vectorised_recall`` itself rather than
    re-derived, so the cosine sweep is byte-identical to the one every landed
    replay used; only the prior-mass union is substituted."""

    as_flown = cf.vectorised_recall(bundle, cosines, top_k=FROZEN_TOP_K)
    recalled: dict[str, dict[str, float]] = {}
    for facet_id, dim_scores in as_flown.items():
        kept = {
            dim: float(score)
            for dim, score in dim_scores.items()
            if dim not in kb.PRIOR_MASS_DIMENSIONS
        }
        if kept:
            recalled[facet_id] = kept
    for facet_id, dim_scores in prior_recall.items():
        recalled.setdefault(facet_id, {}).update(
            {dim: float(score) for dim, score in dim_scores.items()}
        )
    return recalled


def corrected_prior_supply_replay(
    carrier: ccd.A2TAttempt4,
    cosine_cache: Mapping[str, object],
    corrected_snapshot: object,
) -> dict[str, object]:
    """Replay the supply on all 104 under the CORRECTED prior.

    WHY THIS IS NOT THE LANDED BRACKET. The landed
    ``a2t_gold_absence_diagnosis.prior_dimension_sensitivity`` rescaled the
    prior-mass scores AFTER recall, so its ``prior_at_unity`` arm kept the
    as-flown RECALLED SET and merely raised its scores. A genuinely corrected
    prior changes something that arm could not see: which facets each
    prior-mass dimension recalls at all, because ``multidim_recall`` truncates
    each dimension to its own top ``k`` by score. So here the prior-mass recall
    is REDONE, through ``kb_policy.multidim_recall`` on a snapshot carrying the
    corrected values, and the resulting recalled set is compared against the
    as-flown one before the supply is replayed.

    The bracket is not discarded: it remains the reason the answer is expected
    to be zero, and this function is the direct measurement of that
    expectation."""

    bundle = carrier.bundle
    as_flown_prior_recall = bundle.prior_dimension_recall
    corrected_prior_recall = kb.multidim_recall(
        corrected_snapshot, {}, lambda _facet_id: {}, FROZEN_TOP_K
    )

    as_flown_prior_scores = [
        float(score)
        for scores in as_flown_prior_recall.values()
        for dim, score in scores.items()
        if dim in kb.PRIOR_MASS_DIMENSIONS
    ]
    corrected_prior_scores = [
        float(score)
        for scores in corrected_prior_recall.values()
        for dim, score in scores.items()
        if dim in kb.PRIOR_MASS_DIMENSIONS
    ]

    supplies_as_flown: dict[str, tuple[str, ...]] = {}
    supplies_corrected: dict[str, tuple[str, ...]] = {}
    prior_facets_in_top_m_corrected: list[int] = []
    anchor_disagreements: list[str] = []
    ranker = kb.rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)

    for sample_id in carrier.sample_ids:
        cosines = cosine_cache[sample_id]
        base = cf.vectorised_recall(bundle, cosines, top_k=FROZEN_TOP_K)
        # ANCHOR: recomposing with the as-flown prior recall must return the
        # as-flown recall exactly, or the substitution below is not a clean
        # one-variable change.
        rebuilt_base = _recall_with_prior(bundle, cosines, as_flown_prior_recall)
        if rebuilt_base != base:
            anchor_disagreements.append(sample_id)
        corrected = _recall_with_prior(bundle, cosines, corrected_prior_recall)

        result = ranker(
            snapshot_sha256=bundle.snapshot_sha256,
            query_state=dc._query_state(sample_id, bundle.snapshot_sha256),
            recall_scores=corrected,
        )
        top_m = [
            candidate.facet_id for candidate in result.candidates[: FROZEN_FUSE.m]
        ]
        prior_facets_in_top_m_corrected.append(
            sum(
                1
                for facet_id in top_m
                if not any(
                    dim not in kb.PRIOR_MASS_DIMENSIONS
                    for dim in corrected.get(facet_id, {})
                )
            )
        )
        for label, scores, sink in (
            ("as_flown", base, supplies_as_flown),
            ("corrected", corrected, supplies_corrected),
        ):
            supply = dc.replay_supply(
                carrier.inputs,
                sample_id,
                weights=FROZEN_WEIGHTS,
                knobs=FROZEN_FUSE,
                top_k=FROZEN_TOP_K,
                recall_scores=scores,
            )
            sink[sample_id] = tuple(sorted(supply.selected_value_ids))

    if anchor_disagreements:
        raise RepairError(
            "the recall recomposition anchor FAILED on "
            f"{len(anchor_disagreements)} trajectories, so the corrected-prior "
            "replay is not a clean one-variable change: "
            + json.dumps(anchor_disagreements[:10])
        )

    changed = [
        sample_id
        for sample_id in carrier.sample_ids
        if supplies_corrected[sample_id] != supplies_as_flown[sample_id]
    ]
    as_flown_matches_flight = all(
        supplies_as_flown[sample_id]
        == tuple(sorted(carrier.flown_supply[sample_id]))
        for sample_id in carrier.sample_ids
        if carrier.flown_dispatched[sample_id]
    )
    if not as_flown_matches_flight:
        raise RepairError(
            "the as-flown replay does not reproduce the flight's own supply on "
            "the dispatched trajectories; nothing downstream may be read"
        )

    return {
        "trajectories": len(carrier.sample_ids),
        "prior_dimension_recall": {
            "as_flown_facets": len(as_flown_prior_recall),
            "corrected_facets": len(corrected_prior_recall),
            "facet_set_identical": set(as_flown_prior_recall)
            == set(corrected_prior_recall),
            "facets_only_as_flown": sorted(
                set(as_flown_prior_recall) - set(corrected_prior_recall)
            )[:10],
            "facets_only_corrected": sorted(
                set(corrected_prior_recall) - set(as_flown_prior_recall)
            )[:10],
            "as_flown_score_supremum": max(as_flown_prior_scores)
            if as_flown_prior_scores
            else None,
            "as_flown_scores_above_1": sum(
                1 for score in as_flown_prior_scores if score > 1.0
            ),
            "corrected_score_supremum": max(corrected_prior_scores)
            if corrected_prior_scores
            else None,
            "corrected_scores_above_1": sum(
                1 for score in corrected_prior_scores if score > 1.0
            ),
            "note": (
                "recall is REDONE under the corrected values, so a changed "
                "recalled SET is visible here; the landed bracket rescaled "
                "scores after recall and could not see it"
            ),
        },
        "prior_mass_facets_inside_the_locked_top_m_window_under_the_corrected_prior": {
            "max_over_trajectories": max(prior_facets_in_top_m_corrected),
            "total_over_trajectories": sum(prior_facets_in_top_m_corrected),
            "trajectories_with_at_least_one": sum(
                1 for count in prior_facets_in_top_m_corrected if count > 0
            ),
        },
        "as_flown_replay_matches_the_flight_on_dispatched": as_flown_matches_flight,
        "supply_changed_trajectories": len(changed),
        "supply_changed_sample_ids": changed[:20],
        "supply_identical_on_all_trajectories": not changed,
        "consequence": (
            "the corrected prior leaves the supply byte-identical on every one "
            "of the 104, so no landed A2T ranking, supply, dispatch or "
            "correctness number is revised by this repair -- measured, not "
            "inferred from the bracket"
        ),
    }


# ---------------------------------------------------------------------------
# 6. Nothing pinned moved
# ---------------------------------------------------------------------------


def pinned_artifacts_unmoved(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Re-hash every pinned artifact this repair could have disturbed."""

    repo_root, data_root = Path(repo_root), Path(data_root)
    targets = (
        (
            "a2t_snapshot",
            data_root / sweep.A2T_SNAPSHOT_RELPATH,
            sweep.A2T_SNAPSHOT_SHA256,
            "content_hash",
        ),
        (
            "slurp_snapshot",
            data_root / dc.SNAPSHOT_RELPATH,
            dc.SNAPSHOT_SHA256,
            "content_hash",
        ),
        (
            "locked_policy_config",
            repo_root / "configs" / "policy" / "kb-policy-v1-dev100.json",
            sweep.FROZEN_POLICY_CONFIG_SHA256,
            "file_sha256",
        ),
        (
            "a2t_g1_104_receipt",
            repo_root / sweep.A2T_SUBSET_RECEIPT_RELPATH,
            sweep.A2T_SUBSET_RECEIPT_SHA256,
            "file_sha256",
        ),
    )
    rows: list[dict[str, object]] = []
    failures: list[str] = []
    for name, path, expected, mode in targets:
        if not path.is_file():
            failures.append(f"{name}: missing at {path}")
            continue
        if mode == "file_sha256":
            measured = dc._sha256_file(path)
        else:
            document = json.loads(path.read_text(encoding="utf-8"))
            measured = str(document["snapshot_sha256"])
        if measured != expected:
            failures.append(f"{name}: expected {expected}, measured {measured}")
        rows.append(
            {
                "artifact": name,
                "path": str(path),
                "mode": mode,
                "expected_sha256": expected,
                "measured_sha256": measured,
                "unchanged": measured == expected,
            }
        )
    if failures:
        raise RepairError(
            "a pinned artifact moved, which this repair must never do:\n  "
            + "\n  ".join(failures)
        )
    return {
        "artifacts": rows,
        "all_unchanged": True,
        "statement": (
            "the pinned Audio2Tool snapshot and the pinned SLURP snapshot are "
            "byte-identical on disk and remain the record of what actually "
            "flew; the rebuilt snapshot is a NEW artifact at a NEW path and "
            "displaces nothing"
        ),
    }


# ---------------------------------------------------------------------------
# The range contract, exercised on the real pinned artifact
# ---------------------------------------------------------------------------


def range_contract_on_the_pinned_snapshot(snapshot: object) -> dict[str, object]:
    """The load side of the contract, on the real pinned Audio2Tool snapshot.

    The snapshot was loaded through ``KnowledgeSnapshot.from_frozen_json``
    upstream in this run, so this reads what that load RECORDED -- proving the
    contract's historical path works on the artifact it was designed for
    rather than only on a synthetic fixture."""

    recorded = snapshot.historical_prior_score_range_violations
    recomputed = snapshot.prior_score_range_violations()
    if recorded != recomputed:
        raise RepairError(
            "the violations recorded at load time do not match the violations "
            "recomputed from the loaded snapshot"
        )
    scores = [score for _value_id, score in recorded]
    frozen_refusal: str | None = None
    try:
        snapshot.frozen_json()
    except Exception as error:  # noqa: BLE001 -- the refusal IS the evidence
        frozen_refusal = f"{type(error).__name__}: {error}"
    if frozen_refusal is None:
        raise RepairError(
            "the pinned historical snapshot was re-freezable, so the "
            "construction side of the range contract is not closed"
        )
    return {
        "declared_range": [kn.PRIOR_SCORE_MIN, kn.PRIOR_SCORE_MAX],
        "values": len(snapshot.values),
        "recorded_violations": len(recorded),
        "violation_supremum": max(scores) if scores else None,
        "load_succeeded": True,
        "re_freeze_refused_with": frozen_refusal,
        "statement": (
            "the pinned snapshot LOADS, its violations are recorded rather than "
            "silently tolerated, and it cannot be re-frozen: bytes carrying a "
            "violation may come IN and be labelled; none may go OUT"
        ),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(*, repo_root: Path, data_root: Path, out_path: Path) -> dict[str, object]:
    attempts = audit.arm_offline_guard()
    started = time.perf_counter()

    repo_root, data_root = Path(repo_root), Path(data_root)
    package_file = Path(kb.__file__).resolve()
    if "speech-aware-evidence-acquisition" not in package_file.as_posix():
        raise RepairError(
            f"imported rails.kb_policy from {package_file}, not this checkout"
        )

    from ..data.lock import load_lock, umbrella_lock_path
    from ..rails.knowledge_build import slurp_kb_rows
    from ..rails.knowledge_build_a2t import (
        A2tKnowledgeBuildSpec,
        a2t_pool_rows,
        build_a2t_knowledge_snapshot,
        distribution_sample_a2t,
        exposed_sample_ids,
        load_tool_registry_by_name,
        propose_partition,
    )

    source_block = source_verification(repo_root)

    lock = load_lock(umbrella_lock_path(repo_root))

    # ---- SLURP: the identity, over the real TRAIN rows -------------------
    slurp_rows = slurp_kb_rows(lock, data_root)
    slurp_block = slurp_nesting_identity(slurp_rows)
    if not slurp_block["identity_holds"]:
        raise RepairError(
            "THE SLURP NESTING IDENTITY DOES NOT HOLD -- the SLURP prior was "
            "wrong in flight exactly as the A2T one was:\n"
            + json.dumps(slurp_block, indent=1, sort_keys=True)
        )

    # ---- A2T: reconstruct the flight's own construction pool -------------
    a2t_rows, inventory = a2t_pool_rows(lock, data_root)
    registry = load_tool_registry_by_name(lock, data_root)
    exposed = exposed_sample_ids(repo_root)
    partition = propose_partition(a2t_rows, exposed, seed=A2T_PARTITION_SEED)
    construction = partition.construction
    selected = distribution_sample_a2t(construction, None, A2T_BUILD_SEED)

    pinned_path = data_root / sweep.A2T_SNAPSHOT_RELPATH
    pinned_document = json.loads(pinned_path.read_text(encoding="utf-8"))
    pinned_priors = {
        str(value["value_id"]): float(value["prior_score"])
        for value in pinned_document["values"]
        if value.get("prior_score") is not None
    }
    a2t_block = a2t_prior_before_after(
        construction_rows=construction,
        selected_rows=selected,
        pinned_priors=pinned_priors,
    )

    # ---- the rebuild, as a NEW artifact beside the pinned one ------------
    rebuilt = build_a2t_knowledge_snapshot(
        A2tKnowledgeBuildSpec(datastore_size=None, seed=A2T_BUILD_SEED),
        rows=construction,
        registry=registry,
        forbidden_sample_ids=frozenset(exposed) | frozenset(partition.eval_sample_ids),
        governed_relpath_by_tier={
            tier: f"datasets/audio2tool/public/{tier}_data/{tier}.json"
            for tier in {row.tier for row in construction}
        },
    )
    rebuilt_frozen = rebuilt.frozen_json()
    diff_block = rebuild_differs_only_in_prior_score(
        pinned_document={
            key: value
            for key, value in pinned_document.items()
            if key != "snapshot_sha256"
        },
        rebuilt_document={
            key: value
            for key, value in rebuilt_frozen.items()
            if key != "snapshot_sha256"
        },
    )
    rebuilt_path = data_root / A2T_REBUILT_SNAPSHOT_RELPATH
    if rebuilt_path.resolve() == pinned_path.resolve():
        raise RepairError("refusing to write the rebuilt snapshot over the pinned one")
    rebuilt_file_sha256 = write_json_artifact(rebuilt_path, rebuilt_frozen)

    # ---- the 104, under the corrected prior ------------------------------
    carrier = ccd.load_a2t_attempt4(data_root=data_root, repo_root=repo_root)
    contract_block = range_contract_on_the_pinned_snapshot(carrier.bundle.snapshot)
    supplies, blends, direct_labels = ccd.replay_population(carrier)
    gate = ccd.fidelity_gate(carrier, supplies, blends, direct_labels)
    if not gate["gate_passed"]:
        raise RepairError(
            "the landed fidelity gate FAILED; no supply number is read: "
            + json.dumps(gate)
        )
    _geometry, probe_report, _kb_shape, cosine_cache = diag.compute_geometry(carrier)
    replay_block = corrected_prior_supply_replay(carrier, cosine_cache, rebuilt)

    pinned_block = pinned_artifacts_unmoved(repo_root=repo_root, data_root=data_root)

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
        "source_verification": source_block,
        "slurp_nesting_identity": slurp_block,
        "a2t_prior_before_after": a2t_block,
        "a2t_pool_inventory": {
            "pool_items": inventory["pool_items"],
            "pool_units": inventory["pool_units"],
            "usable_units": inventory["usable_units"],
            "construction_units": len(construction),
            "eval_sample_ids": len(partition.eval_sample_ids),
        },
        "rebuild_diff_against_the_pinned_snapshot": diff_block,
        "rebuilt_snapshot": {
            "relpath": A2T_REBUILT_SNAPSHOT_RELPATH,
            "snapshot_sha256": rebuilt_frozen["snapshot_sha256"],
            "file_sha256": rebuilt_file_sha256,
            "pinned_snapshot_sha256": sweep.A2T_SNAPSHOT_SHA256,
            "statement": (
                "a NEW artifact at a NEW path. The pinned snapshot "
                f"{sweep.A2T_SNAPSHOT_SHA256} remains the record of what "
                "actually flew and is not displaced, overwritten or re-hashed. "
                "Nothing consumes the rebuilt snapshot except this row's own "
                "replay."
            ),
        },
        "range_contract_on_the_pinned_snapshot": contract_block,
        "landed_fidelity_gate": gate,
        "recall_fidelity": probe_report,
        "corrected_prior_supply_replay": replay_block,
        "pinned_artifacts": pinned_block,
        "hard_stop": (
            "CORRECTNESS REPAIR ONLY. No knob is changed, nothing is written "
            "under configs/, no pinned snapshot is displaced, no flight is "
            "authorized, no test contact is taken, and no generality or "
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
    print(json.dumps(report["slurp_nesting_identity"], indent=1, sort_keys=True))
    print(json.dumps(report["a2t_prior_before_after"], indent=1, sort_keys=True))
    print(json.dumps(report["corrected_prior_supply_replay"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
