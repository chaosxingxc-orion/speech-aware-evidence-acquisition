"""THE STAGE-2A MATURED SYNTHESIS -- the machine check that every number the
synthesis carries came from the RECEIPT that produced it.

Row ``SAEA-SN-MF-STAGE2A-MATURED-SYNTHESIS`` (model-free-check), registered in
``docs/exposure-ledger.md`` BEFORE this module ran.

WHY THIS EXISTS. Nine readiness documents landed on 2026-08-25. The synthesis
``docs/readiness/2026-08-25-stage2a-matured-synthesis.md`` is the one document
a reviewer reads instead of the nine. A synthesis is exactly the artifact in
which a number quietly drifts: it is restated from another document's prose
rather than re-read from the JSON the computation wrote, and a transposed digit
or a softened interval survives because nothing checks it. This module makes
that impossible for this document. Every quantity the synthesis carries is
declared here as a :class:`Claim` naming the receipt, the JSON path inside it,
and the expected value; :func:`run` re-hashes the receipt, walks the path, and
refuses to return unless every one matches.

WHAT IT DOES NOT DO. It computes no new experimental quantity. It opens no
sealed run directory, no attempt store and no split roster; every input is a
file already committed to this repository. It therefore proves FAITHFULNESS --
that the synthesis says what the receipts say -- and nothing about whether the
receipts are right, which is each landed row's own business.

THE THREE CHECKS, in the order :func:`run` performs them:

1. :func:`arm_offline_guard` (imported from :mod:`.dev100_reviewer_audit`, not
   reimplemented) is armed BEFORE the first input is opened, and its attempt
   counter is published. A model-free row's whole claim is that it contacts
   nothing; the process enforces it rather than asserting it.
2. :func:`verify_receipts` re-hashes every cited receipt with SHA-256 against
   the digest the landed documents quote. A digest mismatch stops the run: a
   number verified against the wrong bytes is not verified.
3. :func:`verify_claims` walks each declared JSON path and compares. Integers
   must match exactly; floats must match to :data:`FLOAT_TOLERANCE`, which is
   tight enough that a rounding difference in the fourth decimal fails.

A FOURTH CHECK THAT IS NOT ABOUT A NUMBER. :func:`verify_source_claims` reads
the two knowledge builders and asserts the structural fact the synthesis's
epistemic record turns on: that ``rails/knowledge_build.py`` and
``rails/knowledge_build_a2t.py`` compute ``prior_score`` with the IDENTICAL
expression shape -- a globally-counted numerator over a differently-keyed
globally-counted denominator -- so the SLURP ratio is a conditional probability
only because the SLURP label vocabulary happens to nest intent inside scenario,
never because the expression restricts anything. The claim was checked here
against source rather than carried over from the landed sweep's prose.

THAT DEFECT WAS SUBSEQUENTLY REPAIRED, AND THIS MODULE RECORDS THE REPAIR
RATHER THAN PRETENDING THE FINDING NEVER HELD. Row
``SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR``
(``docs/readiness/2026-08-25-prior-score-semantics-repair.md``) restricted both
numerators to their conditioning event, so the lines the synthesis cited are no
longer in the tree. The synthesis document and its landed receipt are NOT
rewritten. :func:`verify_source_claims` therefore now publishes the pre-repair
lines as a frozen historical block (:data:`SOURCE_CLAIMS_AT_3F131AFD`, anchored
at the last commit carrying them) and asserts against the LIVE tree that the
repaired expressions are present and the defective ones are gone. The finding
was true when it was made; the code it was made about has changed.

A FIFTH CHECK, ADDED 2026-09-08 WHEN A LOCKED ARTIFACT'S BYTES MOVED UNDER A
PROVEN-EQUIVALENT REFACTOR. WAVE R7 (fold commit ``02486939``, merged to
master as ``f45db5aa``; ``docs/readiness/2026-09-08-ojw-r7-rails-
standardization-v1.md`` section 3.2) hoisted the whole
``saea-kb-alpha-blend-v1`` acquire decision out of
``KbAlphaBlendController._advance_after_direct`` into the module-level
``rails.kb_policy.compute_alpha_blend_decision``, now called by BOTH the
retained controller and the new phase-program factory, and proved
branch-by-branch behaviourally equivalent to the retired shape by
``tests/unit/test_kb_alpha_blend_fold.py``. That changed ``kb_policy.py``'s
bytes -- and only that file; ``configs/policy/kb-policy-v1-dev100.json`` is
byte-identical -- so the digest :data:`FILE_DIGESTS` names for it no longer
matches the live tree. Per the 2026-09-08 P-EMB re-pin rule (umbrella
Decision 11-D): a behaviour-equivalent refactor of a locked artifact re-pins
the LIVE check; it does not freeze the check against bytes the tree no
longer carries, and it does not rewrite what was actually locked at
synthesis time. So the value the synthesis locked stays published,
unmodified, as :data:`FILE_DIGESTS_AT_SYNTHESIS`, and
:func:`verify_file_digests_at_synthesis` asserts it against the five sealed
2026-08-25 receipts (``gold_absence``, ``oracle_bound``, ``cross_carrier``,
``field_level``, ``degeneracy``) that independently recorded it, the same way
:data:`SOURCE_CLAIMS_AT_3F131AFD` above is a frozen historical record rather
than a live assertion. ANY FUTURE STAGE-2A CLAIM that cites "the
kb_policy.py digest the synthesis locked" must cite
:data:`FILE_DIGESTS_AT_SYNTHESIS`, not the live :data:`FILE_DIGESTS`.

FAIL-CLOSED. Every mismatch raises :class:`SynthesisVerificationError`. A
verification module that returns a report saying "3 of 214 failed" invites the
reader to skip the three.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .dev100_reviewer_audit import arm_offline_guard

SCHEMA = "saea-stage2a-synthesis-verification-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-STAGE2A-MATURED-SYNTHESIS"

SYNTHESIS_RELPATH = "docs/readiness/2026-08-25-stage2a-matured-synthesis.md"

#: Floats are compared to this absolute tolerance. The receipts publish full
#: double precision and the synthesis quotes four decimals, so anything looser
#: would let a mis-transcribed fourth decimal pass.
FLOAT_TOLERANCE = 5e-5


class SynthesisVerificationError(RuntimeError):
    """Raised when a receipt digest or a carried number does not match. Never
    raised for a legitimate data shape -- a synthesis check that tolerates a
    mismatch is worth nothing."""


_CHECKS = "docs/checks/speech-aware-evidence-acquisition"


@dataclass(frozen=True)
class Receipt:
    """One landed receipt, addressed by path and pinned by digest."""

    key: str
    relpath: str
    sha256: str
    produced_by: str


#: Every receipt the synthesis cites. The digests are the ones the landed
#: readiness documents quote; re-hashing them here is what makes "cite artifact
#: path plus sha256 beside each number" a check rather than a formatting habit.
RECEIPTS: tuple[Receipt, ...] = (
    Receipt(
        "lock_read",
        f"{_CHECKS}/2026-08-25-dev1000-lock-read/read-verdict.json",
        "2f8e295852e1c09d737467a62123586f097f938ec353dcbe58d258dadc1ea581",
        "the one-shot DEV-1000 baseline-lock read (d9fef537)",
    ),
    Receipt(
        "dev500_read",
        f"{_CHECKS}/2026-08-24-dev500-confirmatory-read/read-verdict.json",
        "b3187fea6f23f637dfa8ac43718667b0286a5c034ea9304bfb03e7029bfc90a3",
        "the DEV-500 confirmatory read (four sealed arms; the ablation attribution)",
    ),
    Receipt(
        "cross_carrier",
        f"{_CHECKS}/2026-08-25-cross-carrier-decomposition/decomposition-report.json",
        "9a1903b35f3eff42dc7bf4caee5ba95235af855e9e0fc087ba8d9d7c0d8be5a1",
        "the cross-carrier ceiling decomposition (54ed885c / 2bf4ccb7)",
    ),
    Receipt(
        "admission_sweep",
        f"{_CHECKS}/2026-08-25-a2t-admission-scale-sweep/sweep-report.json",
        "88f606fe89eb42e675bdd4832a31b028638613eba71d712d3d4ee6cf7aa74d66",
        "the A2T admission-scale defect audit and fix verification (repair 1341c2db)",
    ),
    Receipt(
        "gold_absence",
        f"{_CHECKS}/2026-08-25-a2t-gold-absence/diagnosis-report.json",
        "64327e98ff9f91a4affdf75f25e98eb5500aa4ab2eeab8befa6d3978799a3e14",
        "the A2T gold-absence diagnosis (aaa366ad)",
    ),
    Receipt(
        "matching_vs_extraction",
        f"{_CHECKS}/2026-08-25-matching-vs-extraction/read-report.json",
        "378757b5bc3292395cbdc82a19c936912edaf61725cede012bfad6b77ffd6523",
        "the matching-versus-extraction read (d4c75c7a; conditioned verdict SUPERSEDED)",
    ),
    Receipt(
        "extraction_on_dispatch",
        f"{_CHECKS}/2026-08-25-extraction-conditioned-on-dispatch/read-report.json",
        "7662fbc381e6994f3c71422154a0facfc86c0e99b656cf91670577036a337525",
        "the extraction-conditioned-on-dispatch read (6c6ec719; the supersession)",
    ),
    Receipt(
        "degeneracy",
        f"{_CHECKS}/2026-08-25-query-key-degeneracy/degeneracy-report.json",
        "a1a40999dfddae7642cdc3eaa6763a8fcffe1874e5488210e41618c219a6aeae",
        "the cross-carrier query-key degeneracy measurement (27129962)",
    ),
    Receipt(
        "field_level",
        f"{_CHECKS}/2026-08-25-field-level-supply-accounting/accounting-report.json",
        "ca973be873318deb6029f183045ac4074653dd1b5943c9113fb78d40766de4c6",
        "the field-level supply accounting (27b2be09)",
    ),
    Receipt(
        "oracle_bound",
        f"{_CHECKS}/2026-08-25-a2t-oracle-query-bound/oracle-query-bound-report.json",
        "b564362b64bb41df4d9055518bcd0cd88753e2796b3583ed0b95f626a2ece723",
        "the A2T oracle-query upper bound (274ce62a)",
    ),
    Receipt(
        "a2t_g1_read",
        f"{_CHECKS}/2026-08-25-a2t-g1/g1-read-attempt4.json",
        "cb5e56584a6d572f7b41b39542201ddb1b361755042eac66c3a70c55fd086f89",
        "the A2T G1 attempt-4 paired read (the flown A2T population numbers)",
    ),
    Receipt(
        "kwiden_k1",
        f"{_CHECKS}/2026-08-24-dev100-kwiden-k1/kwiden-k1-report.json",
        "66a340da402f97f6495f87a6a0e3abfa312b3b7771652bd3087407eafee98f9f",
        "the K-WIDEN K1 flown round plus its offline width-5 replay",
    ),
)

RECEIPTS_BY_KEY: Mapping[str, Receipt] = {r.key: r for r in RECEIPTS}


@dataclass(frozen=True)
class Claim:
    """One number the synthesis carries, bound to the receipt field it came
    from. ``path`` is a ``/``-joined JSON path; a segment is a mapping key or,
    where the value is a sequence, a base-10 index."""

    claim_id: str
    receipt: str
    path: str
    expected: Any


def _c(claim_id: str, receipt: str, path: str, expected: Any) -> Claim:
    return Claim(claim_id, receipt, path, expected)


_P = "primary"
_S = "secondaries"
_XC = "decomposition"
_ECD_U = "slurp/unexposed500"
_ECD_E = "slurp/exposed500"

#: Every quantity the synthesis carries, in the order the document uses them.
#: A number that is not in this tuple must not appear in the synthesis as a
#: measured value.
CLAIMS: tuple[Claim, ...] = (
    # -- (1) ESTABLISHED: the locked SLURP cell and its interval -------------
    _c("lock.n", "lock_read", "populations/unexposed_new500_n", 500),
    _c("lock.m0_correct", "lock_read", f"{_P}/M0_correct", 278),
    _c("lock.blend_correct", "lock_read", f"{_P}/BLEND_correct", 379),
    _c("lock.delta_samples", "lock_read", f"{_P}/delta_samples", 101),
    _c("lock.delta_pp", "lock_read", f"{_P}/delta_pp", 20.2),
    _c("lock.ci90_low", "lock_read", f"{_P}/bootstrap/ci90_low_pp", 17.2),
    _c("lock.ci90_high", "lock_read", f"{_P}/bootstrap/ci90_high_pp", 23.4),
    _c("lock.ci95_low", "lock_read", f"{_P}/bootstrap/ci95_low_pp", 16.6),
    _c("lock.ci95_high", "lock_read", f"{_P}/bootstrap/ci95_high_pp", 24.0),
    _c("lock.replicates_le_zero", "lock_read", f"{_P}/bootstrap/replicates_at_or_below_zero", 0),
    _c("lock.n_replicates", "lock_read", f"{_P}/bootstrap/n_replicates", 10000),
    _c("lock.seed", "lock_read", f"{_P}/bootstrap/seed", 20260807),
    _c("lock.sigma_hat", "lock_read", f"{_P}/bootstrap/sigma_hat_pp", 1.898559506151967),
    _c("lock.mcnemar_w2c", "lock_read", f"{_P}/mcnemar/n01_wrong_to_correct", 106),
    _c("lock.mcnemar_c2w", "lock_read", f"{_P}/mcnemar/n10_correct_to_wrong", 5),
    _c("lock.condition_met", "lock_read", f"{_P}/lock_condition_met", True),
    _c("lock.margin_pp", "lock_read", f"{_P}/ci90_lower_bound_margin_vs_threshold_pp", 7.199999999999999),
    _c("lock.threshold_pp", "lock_read", f"{_P}/lock_threshold_pp", 10.0),
    # -- (1) ESTABLISHED: scale stability ------------------------------------
    _c("scale.dev500_delta_pp", "lock_read", f"{_S}/scale_stability_vs_dev500/dev500_unexposed400/delta_pp", 19.75),
    _c("scale.dev500_n", "lock_read", f"{_S}/scale_stability_vs_dev500/dev500_unexposed400/n", 400),
    _c("scale.dev500_ci90_low", "lock_read", f"{_S}/scale_stability_vs_dev500/dev500_unexposed400/ci90_low_pp", 16.5),
    _c("scale.dev500_ci90_high", "lock_read", f"{_S}/scale_stability_vs_dev500/dev500_unexposed400/ci90_high_pp", 23.0),
    _c("scale.dev500_sigma", "lock_read", f"{_S}/scale_stability_vs_dev500/dev500_unexposed400/sigma_hat_pp", 2.0562578496810655),
    _c("scale.intervals_overlap", "lock_read", f"{_S}/scale_stability_vs_dev500/ci90_intervals_overlap", True),
    _c("scale.dev1000_in_dev500_ci", "lock_read", f"{_S}/scale_stability_vs_dev500/dev1000_point_inside_dev500_ci90", True),
    _c("scale.dev500_in_dev1000_ci", "lock_read", f"{_S}/scale_stability_vs_dev500/dev500_point_inside_dev1000_ci90", True),
    # -- (1) ESTABLISHED: the SLURP dispatch decomposition -------------------
    _c("disp.dead_n", "lock_read", f"{_S}/dispatch_decomposition_unexposed500/dead_direct_dispatch/n", 160),
    _c("disp.dead_m0", "lock_read", f"{_S}/dispatch_decomposition_unexposed500/dead_direct_dispatch/M0_correct", 5),
    _c("disp.dead_blend", "lock_read", f"{_S}/dispatch_decomposition_unexposed500/dead_direct_dispatch/BLEND_correct", 100),
    _c("disp.dead_delta_pp", "lock_read", f"{_S}/dispatch_decomposition_unexposed500/dead_direct_dispatch/delta_pp", 59.375),
    _c("disp.dead_share", "lock_read", f"{_S}/dispatch_decomposition_unexposed500/dead_direct_dispatch/share_of_population", 0.32),
    _c("disp.retain_n", "lock_read", f"{_S}/dispatch_decomposition_unexposed500/retain_primary/n", 337),
    _c("disp.retain_delta_pp", "lock_read", f"{_S}/dispatch_decomposition_unexposed500/retain_primary/delta_pp", 2.373887240356083),
    _c("disp.override_n", "lock_read", f"{_S}/dispatch_decomposition_unexposed500/override_dispatch/n", 3),
    # -- (1) ESTABLISHED: the delta override, falsified out of sample --------
    _c("delta.fires_total", "lock_read", f"{_S}/override_subgroup/fires_total", 14),
    _c("delta.exposed_fires", "lock_read", f"{_S}/override_subgroup/on_the_prior_exposed_500_no_claim/fires", 11),
    _c("delta.exposed_recovered", "lock_read", f"{_S}/override_subgroup/on_the_prior_exposed_500_no_claim/recovered", 11),
    _c("delta.exposed_damaged", "lock_read", f"{_S}/override_subgroup/on_the_prior_exposed_500_no_claim/damaged", 0),
    _c("delta.unexposed_fires", "lock_read", f"{_S}/override_subgroup/realized_contribution_to_the_lock_statistic/fires", 3),
    _c("delta.unexposed_recovered", "lock_read", f"{_S}/override_subgroup/realized_contribution_to_the_lock_statistic/recovered", 0),
    _c("delta.unexposed_damaged", "lock_read", f"{_S}/override_subgroup/realized_contribution_to_the_lock_statistic/damaged", 3),
    _c("delta.realized_pp", "lock_read", f"{_S}/override_subgroup/realized_contribution_to_the_lock_statistic/realized_pp", -0.6),
    _c("delta.zero_loss_held", "lock_read", f"{_S}/override_subgroup/loss_side/zero_loss_property_held", False),
    _c("delta.v1_blend_correct", "cross_carrier", f"{_XC}/slurp_unexposed500/locked_v1_blend_correct", 382),
    _c("delta.v1_delta_pp", "cross_carrier", f"{_XC}/slurp_unexposed500/locked_v1_population_delta_pp", 20.8),
    # -- (1) ESTABLISHED: ablation attribution (DEV-500 NEW400) --------------
    _c("abl.blend_vs_randret_pp", "dev500_read", f"{_S}/new400_blend_vs_randret/delta_pp", 15.75),
    _c("abl.blend_vs_randret_ci90_low", "dev500_read", f"{_S}/new400_blend_vs_randret/bootstrap/ci90_low_pp", 12.5),
    _c("abl.blend_vs_randret_ci90_high", "dev500_read", f"{_S}/new400_blend_vs_randret/bootstrap/ci90_high_pp", 19.0),
    _c("abl.randret_vs_m0_pp", "dev500_read", f"{_S}/new400_randret_vs_m0/delta_pp", 4.0),
    _c("abl.blend_vs_randicl_pp", "dev500_read", f"{_S}/new400_blend_vs_randicl/delta_pp", 25.25),
    _c("abl.randicl_vs_m0_pp", "dev500_read", f"{_S}/new400_randicl_vs_m0/delta_pp", -5.5),
    _c("abl.randicl_vs_m0_ci90_low", "dev500_read", f"{_S}/new400_randicl_vs_m0/bootstrap/ci90_low_pp", -9.5),
    _c("abl.randicl_vs_m0_ci90_high", "dev500_read", f"{_S}/new400_randicl_vs_m0/bootstrap/ci90_high_pp", -1.5),
    # -- (1) ESTABLISHED: the ranker repair, identity-preserving -------------
    _c("scale_defect.a2t_sup_prior", "admission_sweep", "audio2tool/scale_audit/the_invariant/measured_sup_prior_score", 4.1),
    _c("scale_defect.required_bound", "admission_sweep", "audio2tool/scale_audit/the_invariant/required_bound_on_sup_prior_score", 1.0833333333333335),
    _c("scale_defect.a2t_margin", "admission_sweep", "audio2tool/scale_audit/the_invariant/margin", -3.016666666666666),
    _c("scale_defect.a2t_holds", "admission_sweep", "audio2tool/scale_audit/the_invariant/invariant_holds", False),
    _c("scale_defect.slurp_sup_prior", "admission_sweep", "slurp_control/scale_audit/the_invariant/measured_sup_prior_score", 1.0),
    _c("scale_defect.slurp_margin", "admission_sweep", "slurp_control/scale_audit/the_invariant/margin", 0.08333333333333348),
    _c("scale_defect.slurp_holds", "admission_sweep", "slurp_control/scale_audit/the_invariant/invariant_holds", True),
    _c("scale_defect.zero_content_in_window", "admission_sweep", "audio2tool/scale_audit/eviction/trajectories_with_zero_content_facets_in_top_m", 104),
    _c("scale_defect.m_needed", "admission_sweep", "audio2tool/scale_audit/eviction/m_needed_to_admit_every_admissible_content_facet", 15),
    _c("scale_defect.v0_dispatch", "admission_sweep", "audio2tool/alpha_gate/by_variant/V0-FROZEN/would_dispatch", 0),
    _c("scale_defect.a6_dispatch", "admission_sweep", "audio2tool/alpha_gate/by_variant/A6-DIMSUP-FLOOR1/would_dispatch", 15),
    _c("scale_defect.a6_label_free_undispatched", "admission_sweep", "audio2tool/alpha_gate/by_variant/A6-DIMSUP-FLOOR1/label_free_trajectories_not_dispatched", 0),
    _c("scale_defect.a6_slurp_admitted_differs", "admission_sweep", "fix_verification/by_variant/A6-DIMSUP-FLOOR1/slurp_identity_proof/admitted_set_differs", 0),
    _c("scale_defect.a6_slurp_supply_differs", "admission_sweep", "fix_verification/by_variant/A6-DIMSUP-FLOOR1/slurp_identity_proof/supply_differs", 0),
    _c("scale_defect.a6_slurp_dispatch_differs", "admission_sweep", "fix_verification/by_variant/A6-DIMSUP-FLOOR1/slurp_identity_proof/dispatch_differs", 0),
    _c("scale_defect.a6_slurp_n", "admission_sweep", "fix_verification/by_variant/A6-DIMSUP-FLOOR1/slurp_identity_proof/trajectories", 500),
    _c("scale_defect.a6_gold_bearing", "admission_sweep", "audio2tool/variant_table/A6-DIMSUP-FLOOR1/gold_bearing_supply_admitted", 68),
    _c("scale_defect.baseline_gate_supply", "admission_sweep", "audio2tool/baseline_fidelity_gate/flown_supply_reproduced", 104),
    _c("scale_defect.baseline_gate_dispatch", "admission_sweep", "audio2tool/baseline_fidelity_gate/flown_dispatch_decision_reproduced", 104),
    # -- (1) ESTABLISHED: the alpha veto, and the two carriers' reach --------
    _c("alpha.structural_floor", "cross_carrier", "ceiling_a_alpha_veto/theorem/guaranteed_margin_1_minus_2alpha", 0.10000000000000003),
    _c("alpha.worst_observed", "cross_carrier", "ceiling_a_alpha_veto/evidence/worst_observed_direct_minus_best_rival", 0.10000000000000003),
    _c("alpha.a2t_recovered", "cross_carrier", "ceiling_a_alpha_veto/evidence/trajectories_with_a_recovered_direct_label", 89),
    _c("reach.a2t_share", "cross_carrier", f"{_XC}/cross_carrier/reachable_share/a2t", 0.14423076923076922),
    _c("reach.slurp_share", "cross_carrier", f"{_XC}/cross_carrier/reachable_share/slurp_unexposed500", 0.32),
    _c("reach.ratio", "cross_carrier", f"{_XC}/cross_carrier/reachable_share_ratio_slurp_over_a2t", 2.218666666666667),
    _c("conv.a2t_pp", "cross_carrier", f"{_XC}/cross_carrier/within_reach_conversion_pp/a2t", 13.333333333333334),
    _c("conv.slurp_pp", "cross_carrier", f"{_XC}/cross_carrier/within_reach_conversion_pp/slurp_unexposed500", 59.375),
    _c("conv.ratio", "cross_carrier", f"{_XC}/cross_carrier/within_reach_conversion_ratio_slurp_over_a2t", 4.453125),
    _c("product.a2t_pp", "cross_carrier", f"{_XC}/cross_carrier/reach_times_conversion_pp/a2t", 1.923076923076923),
    _c("product.slurp_pp", "cross_carrier", f"{_XC}/cross_carrier/reach_times_conversion_pp/slurp_unexposed500", 19.0),
    _c("drift.a2t_pp", "cross_carrier", f"{_XC}/cross_carrier/retain_drift_pp/a2t", -0.9615384615384616),
    _c("drift.slurp_pp", "cross_carrier", f"{_XC}/cross_carrier/retain_drift_pp/slurp_unexposed500", 1.6),
    _c("xc.a2t_closes", "cross_carrier", f"{_XC}/audio2tool/closes_exactly", True),
    _c("xc.slurp_closes", "cross_carrier", f"{_XC}/slurp_unexposed500/closes_exactly_as_flown", True),
    _c("xc.fidelity_supply", "cross_carrier", "fidelity_gate/supply_reproduced", 104),
    _c("xc.fidelity_dispatch", "cross_carrier", "fidelity_gate/dispatch_decision_reproduced", 104),
    _c("xc.fidelity_recovery", "cross_carrier", "fidelity_gate/direct_label_recovery_reproduced", 104),
    # -- (1) ESTABLISHED: the supply term on BOTH axes, where delivered ------
    _c("deliv.slurp_unexposed_n", "field_level", "channel_cost/slurp/DEV-1000-NEW500 (UNEXPOSED)/two_rate/delivery/contacts_that_received_supply", 163),
    _c("deliv.slurp_unexposed_pop", "field_level", "channel_cost/slurp/DEV-1000-NEW500 (UNEXPOSED)/two_rate/delivery/population_size", 500),
    _c("deliv.slurp_unexposed_rate", "field_level", "channel_cost/slurp/DEV-1000-NEW500 (UNEXPOSED)/two_rate/delivery/delivery_rate", 0.326),
    _c("deliv.a2t_n", "field_level", "channel_cost/audio2tool/two_rate/delivery/contacts_that_received_supply", 15),
    _c("deliv.a2t_pop", "field_level", "channel_cost/audio2tool/two_rate/delivery/population_size", 104),
    _c("deliv.a2t_rate", "field_level", "channel_cost/audio2tool/two_rate/delivery/delivery_rate", 0.144231),
    _c("deliv.cross_check_slurp", "field_level", "dispatch_cross_check/slurp_trajectories_with_non_empty_supply", 340),
    _c("deliv.cross_check_a2t", "field_level", "dispatch_cross_check/a2t_trajectories_with_non_empty_supply", 15),
    # matching axis, dispatched stratum
    _c("ecd.disp_m0_match", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/matching/M0_correct", 7),
    _c("ecd.disp_blend_match", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/matching/BLEND_correct", 100),
    _c("ecd.disp_match_pp", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/matching/delta_pp", 57.05521472392638),
    _c("ecd.disp_match_ci90_low", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/matching/bootstrap/ci90_low_pp", 50.306748466257666),
    _c("ecd.disp_match_ci90_high", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/matching/bootstrap/ci90_high_pp", 63.80368098159509),
    _c("ecd.disp_n", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/n", 163),
    _c("ecd.ret_n", "extraction_on_dispatch", f"{_ECD_U}/strata/retained/n", 337),
    _c("ecd.ret_match_pp", "extraction_on_dispatch", f"{_ECD_U}/strata/retained/matching/delta_pp", 2.373887240356083),
    # extraction axis, dispatched stratum
    _c("ecd.disp_macro_pts", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/bootstrap_slot_f1_exact_mean_delta/point_estimate_pp", 9.439088518843121),
    _c("ecd.disp_macro_ci90_low", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_low_pp", 4.355828220858895),
    _c("ecd.disp_macro_ci90_high", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_high_pp", 14.519427402862988),
    _c("ecd.disp_macro_ci90_excl", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_excludes_zero", True),
    _c("ecd.disp_slu_pts", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/bootstrap_slu_f1_micro_delta/point_estimate", 13.757043323670127),
    _c("ecd.disp_slu_ci90_low", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/bootstrap_slu_f1_micro_delta/ci90_low", 8.884029844371804),
    _c("ecd.disp_slu_ci90_high", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/bootstrap_slu_f1_micro_delta/ci90_high", 18.669490340410512),
    _c("ecd.disp_slu_ci90_excl", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/bootstrap_slu_f1_micro_delta/ci90_excludes_zero", True),
    _c("ecd.ret_macro_pts", "extraction_on_dispatch", f"{_ECD_U}/strata/retained/bootstrap_slot_f1_exact_mean_delta/point_estimate_pp", 0.6923837784371907),
    _c("ecd.ret_macro_ci90_excl", "extraction_on_dispatch", f"{_ECD_U}/strata/retained/bootstrap_slot_f1_exact_mean_delta/ci90_excludes_zero", False),
    # the cleanest cell: both arms matching-wrong AND supply delivered
    _c("ecd.nd_n", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/M0/n", 59),
    _c("ecd.nd_macro_pts", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/point_estimate_pp", 6.779661016949152),
    _c("ecd.nd_macro_ci90_low", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_low_pp", 1.694915254237288),
    _c("ecd.nd_macro_ci90_high", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_high_pp", 11.864406779661017),
    _c("ecd.nd_macro_ci90_excl", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_excludes_zero", True),
    _c("ecd.nd_slu_pts", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slu_f1_micro_delta/point_estimate", 15.231239819565115),
    _c("ecd.nd_slu_ci90_low", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slu_f1_micro_delta/ci90_low", 8.21272658914912),
    _c("ecd.nd_slu_ci90_high", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slu_f1_micro_delta/ci90_high", 22.977784937447844),
    _c("ecd.nd_slu_ci90_excl", "extraction_on_dispatch", f"{_ECD_U}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slu_f1_micro_delta/ci90_excludes_zero", True),
    # the three-way decomposition, unexposed
    _c("ecd3.u_a_pts", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/terms_points/matching_attributable", 2.543809523809525),
    _c("ecd3.u_a_share", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/share_of_absolute_total/matching_attributable", 0.7178177909164206),
    _c("ecd3.u_b1_pts", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/terms_points/supply_attributable_dispatched", 0.9333333333333332),
    _c("ecd3.u_b1_share", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/share_of_absolute_total/supply_attributable_dispatched", 0.263370061811341),
    _c("ecd3.u_b1_n", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/groups/supply_attributable_dispatched/n", 62),
    _c("ecd3.u_b2_pts", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/terms_points/decode_variance_unsupplied_retained", 0.06666666666666586),
    _c("ecd3.u_b2_n", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/groups/decode_variance_unsupplied_retained/n", 327),
    _c("ecd3.u_aggregate", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/aggregate_delta_points", 3.543809523809524),
    _c("ecd3.u_closes", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/closes_to_1e_9", True),
    _c("ecd3.u_landed_b", "extraction_on_dispatch", f"{_ECD_U}/three_way_decomposition_slot_f1_exact_mean/landed_b_term_recovered_points", 0.9999999999999991),
    # -- (2) NOT ESTABLISHED: the exposed half does not replicate ------------
    _c("ecd3.e_b1_pts", "extraction_on_dispatch", f"{_ECD_E}/three_way_decomposition_slot_f1_exact_mean/terms_points/supply_attributable_dispatched", -0.0533333333333334),
    _c("ecd3.e_b1_n", "extraction_on_dispatch", f"{_ECD_E}/three_way_decomposition_slot_f1_exact_mean/groups/supply_attributable_dispatched/n", 57),
    _c("ecd3.e_a_pts", "extraction_on_dispatch", f"{_ECD_E}/three_way_decomposition_slot_f1_exact_mean/terms_points/matching_attributable", 2.825714285714285),
    _c("ecd3.e_a_share", "extraction_on_dispatch", f"{_ECD_E}/three_way_decomposition_slot_f1_exact_mean/share_of_absolute_total/matching_attributable", 0.9485294117647057),
    _c("ecd3.e_aggregate", "extraction_on_dispatch", f"{_ECD_E}/three_way_decomposition_slot_f1_exact_mean/aggregate_delta_points", 2.872380952380951),
    _c("ecd.e_nd_macro_pts", "extraction_on_dispatch", f"{_ECD_E}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/point_estimate_pp", -0.48484848484848475),
    _c("ecd.e_nd_macro_ci90_excl", "extraction_on_dispatch", f"{_ECD_E}/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_excludes_zero", False),
    _c("ecd.e_nd_n", "extraction_on_dispatch", f"{_ECD_E}/eight_cell_extraction/neither_matched|dispatched/M0/n", 55),
    # -- (2) NOT ESTABLISHED: the A2T population delta -----------------------
    _c("a2t.m0_tool", "a2t_g1_read", "paired_tool_accuracy/m0_count", 62),
    _c("a2t.blend_tool", "a2t_g1_read", "paired_tool_accuracy/blend_count", 63),
    _c("a2t.tool_delta_pp", "a2t_g1_read", "paired_tool_accuracy/delta_pp", 0.9615384615384616),
    _c("a2t.tool_ci90_low", "a2t_g1_read", "paired_tool_accuracy/bootstrap/ci90_low_pp", -2.8846153846153846),
    _c("a2t.tool_ci90_high", "a2t_g1_read", "paired_tool_accuracy/bootstrap/ci90_high_pp", 4.8076923076923075),
    _c("a2t.tool_ci90_excl", "a2t_g1_read", "paired_tool_accuracy/bootstrap/ci90_excludes_zero", False),
    _c("a2t.tool_share_le_zero", "a2t_g1_read", "paired_tool_accuracy/bootstrap/replicate_share_at_or_below_zero", 0.4156),
    _c("a2t.tool_midp", "a2t_g1_read", "paired_tool_accuracy/mcnemar/mid_p_two_sided", 0.6875),
    _c("a2t.em_m0", "a2t_g1_read", "paired_exact_match/m0_count", 29),
    _c("a2t.em_blend", "a2t_g1_read", "paired_exact_match/blend_count", 29),
    _c("a2t.em_delta_pp", "a2t_g1_read", "paired_exact_match/delta_pp", 0.0),
    _c("a2t.em_ci90_low", "a2t_g1_read", "paired_exact_match/bootstrap/ci90_low_pp", -1.9230769230769231),
    _c("a2t.em_ci90_high", "a2t_g1_read", "paired_exact_match/bootstrap/ci90_high_pp", 1.9230769230769231),
    _c("a2t.dispatched", "a2t_g1_read", "mechanism/dispatched", 15),
    _c("a2t.retained", "a2t_g1_read", "mechanism/retained_primary", 89),
    _c("a2t.retain_eq_recovered", "a2t_g1_read", "mechanism/retain_equals_direct_label_recovered", True),
    _c("a2t.branch_only_replayed", "a2t_g1_read", "mechanism/branch_only_replay/trajectories_replayed", 15),
    _c("a2t.branch_only_vacuous", "a2t_g1_read", "mechanism/branch_only_replay_is_vacuous", False),
    _c("a2t.text_identical_to_m0", "a2t_g1_read", "decode_variance_attribution/trajectories_with_text_identical_to_m0", 93),
    _c("a2t.multi_tool_items", "a2t_g1_read", "tool_name_multiset_mapping/gold_multi_distinct_tool_items", 26),
    _c("a2t.empty_m0_rate", "a2t_g1_read", "headline/m0_empty_call_rate", 0.1346153846153846),
    _c("a2t.empty_blend_rate", "a2t_g1_read", "headline/blend_empty_call_rate", 0.028846153846153848),
    # -- (2) NOT ESTABLISHED: gold-bearing supply converts 2 of 4 ------------
    _c("conv.gold_bearing_n", "cross_carrier", "conditional_conversion/a2t_dispatched_with_gold_bearing_supply/n", 4),
    _c("conv.gold_bearing_blend", "cross_carrier", "conditional_conversion/a2t_dispatched_with_gold_bearing_supply/blend_correct", 2),
    _c("conv.gold_absent_n", "cross_carrier", "conditional_conversion/a2t_dispatched_without_gold_bearing_supply/n", 11),
    _c("conv.gold_absent_blend", "cross_carrier", "conditional_conversion/a2t_dispatched_without_gold_bearing_supply/blend_correct", 1),
    _c("conv.all_dispatched_blend", "cross_carrier", "conditional_conversion/a2t_dispatched_all/blend_correct", 3),
    _c("conv.all_dispatched_own_c0", "cross_carrier", "conditional_conversion/a2t_dispatched_all/own_contact0_direct_correct", 0),
    _c("conv.all_dispatched_vs_m0", "cross_carrier", "conditional_conversion/a2t_dispatched_all/blend_minus_m0_samples", 2),
    # -- (3) WHERE THE LIMIT IS: refusal 1, KB build coverage ---------------
    _c("limit.build_defects", "gold_absence", "q1_build_versus_ranking/case_a_build_coverage_defect/n", 0),
    _c("limit.ranking_defects", "gold_absence", "q1_build_versus_ranking/case_b_ranking_recall_defect/n", 11),
    _c("limit.dominating", "gold_absence", "q1_build_versus_ranking/dominating_sub_cause", "RANKING"),
    _c("limit.pop_no_kb_value", "gold_absence", "q1_build_versus_ranking/population_coverage_context/trajectories_whose_gold_tool_has_no_kb_value", 0),
    _c("limit.pop_no_vector", "gold_absence", "q1_build_versus_ranking/population_coverage_context/trajectories_whose_gold_tool_has_no_vectored_facet", 0),
    # -- (3) refusal 2, retrieval width / depth -----------------------------
    _c("limit.reached_at_locked_top_l", "gold_absence", "q2_reachability_curve/binding_stage/reached_at_some_depth_under_the_locked_top_l_3", 0),
    _c("limit.reached_if_top_l_lifted", "gold_absence", "q2_reachability_curve/binding_stage/reached_at_some_depth_under_any_top_l", 2),
    _c("limit.kwiden_supply_changed", "kwiden_k1", "width_supply_replay/supply_changed_count", 32),
    _c("limit.kwiden_flips", "kwiden_k1", "width_supply_replay/width_attributable_flip_count", 0),
    _c("limit.curve_case_b_at_512", "gold_absence", "q2_reachability_curve/curve_case_b_ranking_defect/recall_at_512/rate", 1.0),
    _c("limit.curve_case_b_at_5", "gold_absence", "q2_reachability_curve/curve_case_b_ranking_defect/recall_at_5/count", 0),
    _c("limit.curve_case_b_n", "gold_absence", "q2_reachability_curve/curve_case_b_ranking_defect/n", 11),
    # -- (3) refusal 3, the tau percept gate --------------------------------
    _c("limit.tau_blocked", "gold_absence", "q2_reachability_curve/binding_stage/blocked_by_the_tau_percept_gate", 9),
    _c("limit.top_l_blocked", "gold_absence", "q2_reachability_curve/binding_stage/blocked_by_the_top_l_target_budget_only", 2),
    _c("limit.n1_clears_tau", "oracle_bound", "lower_constructions/summary/N1_gold_facet_clears_tau_of_all_dispatched", 15),
    _c("limit.n1_supplies", "oracle_bound", "lower_constructions/summary/N1_gold_supplied_of_all_dispatched", 0),
    _c("limit.n1_binding_recall", "oracle_bound", "lower_constructions/summary/N1_binding_stage_histogram/recall_depth_k", 15),
    _c("limit.n1_cos_min", "oracle_bound", "lower_constructions/summary/N1_gold_facet_cosine_min", 0.7209419740717382),
    _c("limit.n1_cos_median", "oracle_bound", "lower_constructions/summary/N1_gold_facet_cosine_median", 0.7898153552729054),
    _c("limit.n1_cos_max", "oracle_bound", "lower_constructions/summary/N1_gold_facet_cosine_max", 0.858710697382477),
    _c("limit.tau_band_min", "oracle_bound", "landed_reproduction_gate/checks/tau_band_min/recomputed", 0.565332),
    _c("limit.tau_band_max", "oracle_bound", "landed_reproduction_gate/checks/tau_band_max/recomputed", 0.635625),
    _c("limit.gate_passed", "oracle_bound", "landed_reproduction_gate/gate_passed", True),
    # -- (3) refusal 4, the hand-fit dispatch override (delta) --------------
    #     covered by delta.* above; the in-sample/out-of-sample asymmetry is
    #     the refusal and is asserted there.
    # -- (3) what remains: discrimination under a degenerate query ----------
    _c("degen.a2t_dead_keys_per_traj", "degeneracy", "a2t_control/degeneracy/dead_direct/distinct_query_vectors_per_trajectory", 0.3333333333333333),
    _c("degen.a2t_dead_distinct", "degeneracy", "a2t_control/degeneracy/dead_direct/distinct_query_vectors", 5),
    _c("degen.a2t_dead_n", "degeneracy", "a2t_control/degeneracy/dead_direct/n", 15),
    _c("degen.a2t_cluster", "degeneracy", "a2t_control/degeneracy/dead_direct/largest_identical_query_cluster_size", 11),
    _c("degen.a2t_cluster_share", "degeneracy", "a2t_control/degeneracy/dead_direct/largest_identical_query_cluster_share", 0.7333333333333333),
    _c("degen.a2t_cluster_supplies", "degeneracy", "a2t_control/degeneracy/dead_direct/distinct_supplies_inside_the_largest_key_cluster", 1),
    _c("degen.a2t_live_keys_per_traj", "degeneracy", "a2t_control/degeneracy/label_recovered/distinct_query_vectors_per_trajectory", 0.9438202247191011),
    _c("degen.a2t_control_reproduced", "degeneracy", "a2t_control/control_reproduced", True),
    _c("degen.a2t_ratio", "degeneracy", "q3_cross_carrier_verdict/mechanism_discriminants/0/dead_over_live_degeneracy_ratio", 0.35317460317460314),
    _c("degen.slurp_u_ratio", "degeneracy", "q3_cross_carrier_verdict/mechanism_discriminants/1/dead_over_live_degeneracy_ratio", 1.240343347639485),
    _c("degen.slurp_e_ratio", "degeneracy", "q3_cross_carrier_verdict/mechanism_discriminants/2/dead_over_live_degeneracy_ratio", 1.0270706255986288),
    _c("degen.a2t_empty_rate", "degeneracy", "q3_cross_carrier_verdict/mechanism_discriminants/0/dead_structurally_empty_answer_rate", 0.9333333333333333),
    _c("degen.slurp_u_empty_rate", "degeneracy", "q3_cross_carrier_verdict/mechanism_discriminants/1/dead_structurally_empty_answer_rate", 0.0125),
    _c("degen.slurp_e_empty_rate", "degeneracy", "q3_cross_carrier_verdict/mechanism_discriminants/2/dead_structurally_empty_answer_rate", 0.018072289156626505),
    _c("degen.slurp_u_dead_keys", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/degeneracy/dead_direct/distinct_query_vectors_per_trajectory", 0.85),
    _c("degen.slurp_u_live_keys", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/degeneracy/label_recovered/distinct_query_vectors_per_trajectory", 0.6852941176470588),
    _c("degen.slurp_e_dead_keys", "degeneracy", "slurp/halves/EXPOSED-DEV500/degeneracy/dead_direct/distinct_query_vectors_per_trajectory", 0.7349397590361446),
    _c("degen.slurp_e_live_keys", "degeneracy", "slurp/halves/EXPOSED-DEV500/degeneracy/label_recovered/distinct_query_vectors_per_trajectory", 0.7155688622754491),
    _c("degen.a2t_below_tau", "degeneracy", "a2t_control/tau_distance/dead_direct/gold_facet_below_tau", 9),
    _c("degen.slurp_u_below_tau", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/tau_distance/dead_direct/gold_facet_below_tau", 10),
    _c("degen.slurp_e_below_tau", "degeneracy", "slurp/halves/EXPOSED-DEV500/tau_distance/dead_direct/gold_facet_below_tau", 14),
    _c("degen.slurp_u_dead_vectors", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/degeneracy/dead_direct/distinct_query_vectors", 136),
    _c("degen.slurp_u_dead_texts", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/degeneracy/dead_direct/distinct_contact0_texts", 133),
    _c("degen.slurp_u_dead_n", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/degeneracy/dead_direct/n", 160),
    _c("degen.slurp_e_dead_n", "degeneracy", "slurp/halves/EXPOSED-DEV500/degeneracy/dead_direct/n", 166),
    # the per-group gold-in-top-5 rates the cross-carrier magnitude story rests
    # on -- carried as rates rather than as either document's derived ratio
    _c("degen.a2t_dead_top5", "degeneracy", "a2t_control/retrieval/dead_direct/gold_in_top_5", 4),
    _c("degen.a2t_live_top5", "degeneracy", "a2t_control/retrieval/label_recovered/gold_in_top_5", 64),
    _c("degen.a2t_dead_top5_rate", "degeneracy", "a2t_control/retrieval/dead_direct/gold_in_top_5_rate_over_all_members", 0.26666666666666666),
    _c("degen.a2t_live_top5_rate", "degeneracy", "a2t_control/retrieval/label_recovered/gold_in_top_5_rate_over_all_members", 0.7191011235955056),
    _c("degen.slurp_u_dead_top5_rate", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/retrieval/dead_direct/gold_in_top_5_rate_over_all_members", 0.7),
    _c("degen.slurp_u_live_top5_rate", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/retrieval/label_recovered/gold_in_top_5_rate_over_all_members", 0.7647058823529411),
    _c("degen.slurp_e_dead_top5_rate", "degeneracy", "slurp/halves/EXPOSED-DEV500/retrieval/dead_direct/gold_in_top_5_rate_over_all_members", 0.6987951807228916),
    _c("degen.slurp_e_live_top5_rate", "degeneracy", "slurp/halves/EXPOSED-DEV500/retrieval/label_recovered/gold_in_top_5_rate_over_all_members", 0.7544910179640718),
    _c("degen.a2t_dead_cos_median", "degeneracy", "a2t_control/retrieval/dead_direct/gold_facet_cosine_median", 0.6054),
    _c("degen.a2t_live_cos_median", "degeneracy", "a2t_control/retrieval/label_recovered/gold_facet_cosine_median", 0.8632),
    _c("degen.a2t_gap_to_tau_min", "degeneracy", "a2t_control/tau_distance/dead_direct/gap_to_tau_min", 0.014374534597870081),
    _c("degen.a2t_gap_to_tau_max", "degeneracy", "a2t_control/tau_distance/dead_direct/gap_to_tau_max", 0.08466818252368002),
    _c("degen.a2t_dead_pos_median", "degeneracy", "a2t_control/retrieval/dead_direct/gold_facet_position_median", 83.0),
    _c("degen.slurp_u_dead_pos_median", "degeneracy", "slurp/halves/UNEXPOSED-NEW500/retrieval/dead_direct/gold_facet_position_median", 1.0),
    # -- (3) the oracle bound: the KB itself can deliver --------------------
    _c("oracle.o3", "oracle_bound", "oracle_bound/summary/O3_gold_supplied_of_the_gold_absent", 11),
    _c("oracle.gold_absent_n", "oracle_bound", "oracle_bound/summary/gold_absent_n", 11),
    _c("oracle.o3_twin_free", "oracle_bound", "oracle_bound/summary/O3_TWIN_FREE_gold_supplied_of_the_gold_absent", 11),
    _c("oracle.o3_pooled_rate", "oracle_bound", "oracle_bound/summary/O3_RATE_pooled", 0.8530197755211117),
    _c("oracle.o3_pooled_delivered", "oracle_bound", "oracle_bound/summary/O3_RATE_pooled_delivered", 1596),
    _c("oracle.o3_pooled_tried", "oracle_bound", "oracle_bound/summary/O3_RATE_pooled_tried", 1871),
    _c("oracle.o3_twin_free_rate", "oracle_bound", "oracle_bound/summary/O3_TWIN_FREE_pooled_rate", 0.8502994011976048),
    _c("oracle.o3_twins", "oracle_bound", "oracle_bound/summary/O3_maxima_at_an_exact_twin", 6),
    _c("oracle.o2", "oracle_bound", "oracle_bound/summary/O2_gold_supplied_of_the_gold_absent", 6),
    _c("oracle.outcome", "oracle_bound", "decision_rule/outcome", "SURVIVES"),
    _c("oracle.survives_at", "oracle_bound", "decision_rule/bands_fixed_in_the_registration/survives_at_or_above", 8),
    _c("oracle.refuted_at", "oracle_bound", "decision_rule/bands_fixed_in_the_registration/refuted_at_or_below", 1),
    _c("oracle.leak_units", "oracle_bound", "utterance_leak_check/eval_UNITS_present_in_the_kb", 0),
    _c("oracle.leak_texts", "oracle_bound", "utterance_leak_check/eval_UTTERANCE_TEXTS_matching_a_kb_content_facet", 6),
    _c("oracle.leak_in_dispatched", "oracle_bound", "utterance_leak_check/text_matches_among_the_dispatched_15", 0),
    # -- the FORM versus KNOWLEDGE channel ----------------------------------
    _c("form.repaired", "gold_absence", "q5_form_repair_channel/form_repaired_n", 11),
    _c("form.repaired_still_wrong", "gold_absence", "q5_form_repair_channel/form_repaired_but_still_wrong_n", 9),
    _c("form.converted_own_c0", "gold_absence", "q5_form_repair_channel/converted_against_own_contact0_n", 3),
    _c("form.form_channel_converts", "gold_absence", "q5_form_repair_channel/converted_without_gold_bearing_supply/n", 1),
    _c("form.knowledge_channel_converts", "gold_absence", "q5_form_repair_channel/converted_with_gold_bearing_supply/n", 2),
    _c("form.c0_empty", "gold_absence", "q5_form_repair_channel/contact0_form_classes/empty", 11),
    _c("form.c0_unparsed", "gold_absence", "q5_form_repair_channel/contact0_form_classes/unparsed", 3),
    _c("form.c0_wellformed", "gold_absence", "q5_form_repair_channel/contact0_form_classes/well-formed-non-empty", 1),
    _c("form.m0_empty_count", "gold_absence", "q5_form_repair_channel/empty_call_rate/m0_arm/count", 14),
    _c("form.blend_empty_count", "gold_absence", "q5_form_repair_channel/empty_call_rate/blend_arm/count", 3),
    # -- K3, refused on Audio2Tool ------------------------------------------
    _c("k3.upper_projected", "gold_absence", "k3_dispatch_projection/projection_upper_bound_on_repair/projected_dispatch_count", 3),
    _c("k3.upper_pp", "gold_absence", "k3_dispatch_projection/projection_upper_bound_on_repair/projected_dispatch_rate_change_pp", -11.538461538461538),
    _c("k3.upper_relative", "gold_absence", "k3_dispatch_projection/projection_upper_bound_on_repair/relative_change", -0.8),
    _c("k3.lower_projected", "gold_absence", "k3_dispatch_projection/projection_lower_bound_on_repair/projected_dispatch_count", 13),
    _c("k3.lower_pp", "gold_absence", "k3_dispatch_projection/projection_lower_bound_on_repair/projected_dispatch_rate_change_pp", -1.9230769230769231),
    _c("k3.lower_relative", "gold_absence", "k3_dispatch_projection/projection_lower_bound_on_repair/relative_change", -0.13333333333333333),
    _c("k3.carve_out_preserves", "gold_absence", "k3_dispatch_projection/flown_dispatch_composition/well_formed_but_out_of_vocabulary", 1),
    _c("k3.flown_dispatch_count", "gold_absence", "k3_dispatch_projection/projection_upper_bound_on_repair/flown_dispatch_count", 15),
    # -- (4) EPISTEMIC RECORD: the landed read whose interpretation was
    #        superseded. Its ARITHMETIC is confirmed by the successor and is
    #        carried here from its OWN receipt, so the synthesis quotes the
    #        withdrawn claim at the value the withdrawn document actually
    #        published rather than at the successor's restatement of it.
    _c("mve.fidelity_pass", "matching_vs_extraction", "fidelity_gate/pass", True),
    _c("mve.fidelity_slurp", "matching_vs_extraction", "fidelity_gate/slurp/pass", True),
    _c("mve.fidelity_a2t", "matching_vs_extraction", "fidelity_gate/a2t/pass", True),
    _c("mve.u_aggregate_pts", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/aggregate_delta_points", 3.543809523809524),
    _c("mve.u_a_pts", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/a_points", 2.5438095238095246),
    _c("mve.u_a_share", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/a_share_of_absolute_total", 0.7178177909164203),
    _c("mve.u_b_pts", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/b_points", 1.0000000000000002),
    _c("mve.u_b_both_component", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/b_both_matched_component_points", -0.06666666666666643),
    _c("mve.u_b_neither_component", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/b_neither_matched_component_points", 1.0666666666666667),
    _c("mve.u_closes", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/closes_exactly", True),
    _c("mve.u_both_n", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/cells/both_matched/n", 273),
    _c("mve.u_both_delta_pts", "matching_vs_extraction", "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/cells/both_matched/delta_points", -0.12210012210012167),
    _c("mve.e_both_n", "matching_vs_extraction", "slurp/exposed500/cells/both_matched/n", 255),
    _c("mve.e_both_slu_pts", "matching_vs_extraction", "slurp/exposed500/cells/both_matched/slu_f1_micro_f1_delta_points", -1.6351171950097831),
    _c("mve.e_both_slu_ci90_low", "matching_vs_extraction", "slurp/exposed500/cells/both_matched/bootstrap_slu_f1_micro_delta/ci90_low", -3.229105368742267),
    _c("mve.e_both_slu_ci90_high", "matching_vs_extraction", "slurp/exposed500/cells/both_matched/bootstrap_slu_f1_micro_delta/ci90_high", -0.11082574813623408),
    _c("mve.e_both_slu_ci90_excl", "matching_vs_extraction", "slurp/exposed500/cells/both_matched/bootstrap_slu_f1_micro_delta/ci90_excludes_zero", True),
    # -- the vacuity of the superseded conditioned cell ---------------------
    _c("vac.slurp_both_n", "extraction_on_dispatch", f"{_ECD_U}/cross_tabulation/cells/both_matched/n", 273),
    _c("vac.slurp_both_dispatched", "extraction_on_dispatch", f"{_ECD_U}/cross_tabulation/cells/both_matched/dispatched_n", 3),
    _c("vac.slurp_both_retained", "extraction_on_dispatch", f"{_ECD_U}/cross_tabulation/cells/both_matched/retained_n", 270),
    _c("vac.slurp_e_both_n", "extraction_on_dispatch", f"{_ECD_E}/cross_tabulation/cells/both_matched/n", 255),
    _c("vac.slurp_e_both_dispatched", "extraction_on_dispatch", f"{_ECD_E}/cross_tabulation/cells/both_matched/dispatched_n", 2),
    _c("vac.slurp_e_both_retained", "extraction_on_dispatch", f"{_ECD_E}/cross_tabulation/cells/both_matched/retained_n", 253),
    _c("vac.a2t_both_retained", "extraction_on_dispatch", "a2t/cross_tabulation/cells/both_matched/retained_n", 60),
    _c("vac.a2t_both_n", "extraction_on_dispatch", "a2t/cross_tabulation/cells/both_matched/n", 60),
    _c("vac.a2t_both_dispatched", "extraction_on_dispatch", "a2t/cross_tabulation/cells/both_matched/dispatched_n", 0),
    # -- the A2T sign inversion on the dispatch axis ------------------------
    _c("inv.a2t_disp_micro_pts", "extraction_on_dispatch", "a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/point_estimate", 12.121212121212123),
    _c("inv.a2t_disp_micro_ci90_low", "extraction_on_dispatch", "a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/ci90_low", 0.0),
    _c("inv.a2t_disp_micro_ci90_high", "extraction_on_dispatch", "a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/ci90_high", 23.076923076923077),
    _c("inv.a2t_disp_micro_ci90_excl", "extraction_on_dispatch", "a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/ci90_excludes_zero", False),
    _c("inv.a2t_ret_micro_pts", "extraction_on_dispatch", "a2t/strata/retained/bootstrap_slot_micro_f1_delta/point_estimate", -3.0249966324783104),
    _c("inv.a2t_ret_micro_ci90_low", "extraction_on_dispatch", "a2t/strata/retained/bootstrap_slot_micro_f1_delta/ci90_low", -6.194049268636866),
    _c("inv.a2t_ret_micro_ci90_high", "extraction_on_dispatch", "a2t/strata/retained/bootstrap_slot_micro_f1_delta/ci90_high", -0.594122935347456),
    _c("inv.a2t_ret_micro_ci90_excl", "extraction_on_dispatch", "a2t/strata/retained/bootstrap_slot_micro_f1_delta/ci90_excludes_zero", True),
    _c("inv.a2t_b1_pts", "extraction_on_dispatch", "a2t/three_way_decomposition_slot_f1_mean/terms_points/supply_attributable_dispatched", 0.32051282051282054),
    _c("inv.a2t_b2_pts", "extraction_on_dispatch", "a2t/three_way_decomposition_slot_f1_mean/terms_points/decode_variance_unsupplied_retained", -0.12820512820512434),
    _c("inv.a2t_a_pts", "extraction_on_dispatch", "a2t/three_way_decomposition_slot_f1_mean/terms_points/matching_attributable", -0.4807692307692308),
    _c("inv.a2t_b1_n", "extraction_on_dispatch", "a2t/three_way_decomposition_slot_f1_mean/groups/supply_attributable_dispatched/n", 11),
    _c("inv.a2t_b2_n", "extraction_on_dispatch", "a2t/three_way_decomposition_slot_f1_mean/groups/decode_variance_unsupplied_retained/n", 88),
    _c("inv.a2t_a_n", "extraction_on_dispatch", "a2t/three_way_decomposition_slot_f1_mean/groups/matching_attributable/n", 5),
    # the whole-population A2T slot micro-F1 endpoints; the -2.5782-point
    # aggregate the landed read quotes is their DIFFERENCE, not a field
    _c("inv.a2t_pop_micro_m0", "extraction_on_dispatch", "a2t/aggregate_M0/slot_micro_f1", 0.4378698224852071),
    _c("inv.a2t_pop_micro_blend", "extraction_on_dispatch", "a2t/aggregate_BLEND/slot_micro_f1", 0.41208791208791207),
    # -- the decode-variance channel ----------------------------------------
    _c("dv.slurp_u_rate", "extraction_on_dispatch", f"{_ECD_U}/decode_variance_channel_on_retained/retained_response_text_divergence_rate", 0.14836795252225518),
    _c("dv.slurp_e_rate", "extraction_on_dispatch", f"{_ECD_E}/decode_variance_channel_on_retained/retained_response_text_divergence_rate", 0.16718266253869968),
    _c("dv.a2t_rate", "extraction_on_dispatch", "a2t/decode_variance_channel_on_retained/retained_response_text_divergence_rate", 0.10112359550561797),
    # -- alpha sizing, and the retained set the sizing would reach ----------
    _c("size.if_no_alpha_population", "cross_carrier", "ceiling_b_gold_coverage/population_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE", 68),
    _c("size.if_no_alpha_retained", "cross_carrier", "ceiling_b_gold_coverage/retained_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE", 64),
    _c("size.retained_n", "cross_carrier", f"{_XC}/audio2tool/unreachable_subgroup_retain_primary/n", 89),
    _c("size.retained_blend_correct", "cross_carrier", f"{_XC}/audio2tool/unreachable_subgroup_retain_primary/blend_correct", 60),
    _c("size.retained_m0_correct", "cross_carrier", f"{_XC}/audio2tool/unreachable_subgroup_retain_primary/m0_correct", 61),
    _c("size.dispatched_direct_correct", "cross_carrier", "ceiling_b_gold_coverage/dispatched_direct_answer_correct", 0),
    # -- the dispatched stratum's own means, as quoted in the synthesis -----
    _c("means.disp_m0_macro", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/M0/slot_f1_exact_mean", 0.22055214723926383),
    _c("means.disp_blend_macro", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/BLEND/slot_f1_exact_mean", 0.314943032427695),
    _c("means.disp_m0_slu", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/M0/slu_f1_micro_f1", 0.4287614425229236),
    _c("means.disp_blend_slu", "extraction_on_dispatch", f"{_ECD_U}/strata/dispatched/BLEND/slu_f1_micro_f1", 0.5663318757596248),
    # -- the pinned identities the synthesis names --------------------------
    _c("pin.kb_policy_sha", "cross_carrier", "artifact_hashes/kb_policy.py", "2a1c3d75e747db10f723044b05c08d232e1edf47f125d0889c1d2565ba1019af"),
    _c("pin.locked_config_sha", "admission_sweep", "frozen_cell/policy_config_sha256", "d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919"),
    _c("pin.locked_config_path", "admission_sweep", "frozen_cell/policy_config", "configs/policy/kb-policy-v1-dev100.json"),
    _c("pin.alpha", "admission_sweep", "frozen_cell/alpha", 0.45),
    _c("pin.tau", "admission_sweep", "frozen_cell/tau", 0.65),
    _c("pin.top_l", "admission_sweep", "frozen_cell/top_l", 3),
    _c("pin.kb_values", "gold_absence", "kb_shape/snapshot_values", 12601),
    _c("pin.kb_vectored", "gold_absence", "kb_shape/content_facets_with_vectors", 12601),
    # -- the offline guards of the rungs being synthesised ------------------
    _c("guard.ecd_attempts", "extraction_on_dispatch", "offline_guard/outbound_connection_attempts", 0),
    _c("guard.xc_attempts", "cross_carrier", "contacts/outbound_connection_attempts", 0),
)


@dataclass(frozen=True)
class DerivedClaim:
    """A number the synthesis quotes as a RANGE or a COUNT over a receipt's
    per-sample list rather than as a single field. Declared separately so it is
    obvious which figures are reductions and which are published fields."""

    claim_id: str
    receipt: str
    list_path: str
    item_path: str
    reduce: str  # "min" | "max" | "count_prefix:<prefix>"
    expected: Any
    filter_path: str | None = None


#: Ranges and counts the synthesis quotes. Every one is a reduction over a
#: per-sample list the receipt publishes, so the reduction is performed here
#: rather than trusted from a landed document's prose.
DERIVED_CLAIMS: tuple[DerivedClaim, ...] = (
    # N1's refusal: the lift raises this many competitors past tau at once...
    DerivedClaim(
        "n1.tau_passing_min", "oracle_bound",
        "lower_constructions/per_sample",
        "N1_tier_prototype/tau_passing_targets_total", "min", 148,
    ),
    DerivedClaim(
        "n1.tau_passing_max", "oracle_bound",
        "lower_constructions/per_sample",
        "N1_tier_prototype/tau_passing_targets_total", "max", 150,
    ),
    # ...and the gold target lands this far down among them.
    DerivedClaim(
        "n1.gold_rank_min", "oracle_bound",
        "lower_constructions/per_sample",
        "N1_tier_prototype/gold_target_rank_among_tau_passing", "min", 11,
    ),
    DerivedClaim(
        "n1.gold_rank_max", "oracle_bound",
        "lower_constructions/per_sample",
        "N1_tier_prototype/gold_target_rank_among_tau_passing", "max", 99,
    ),
    # The oracle's generosity: which tiers the 11 gold-absent trajectories are.
    DerivedClaim(
        "oracle.tier4_of_11", "oracle_bound", "oracle_bound/per_sample",
        "sample_id", "count_prefix:tier4_implicit:", 6,
        filter_path="gold_absent_as_flown",
    ),
    DerivedClaim(
        "oracle.tier7_of_11", "oracle_bound", "oracle_bound/per_sample",
        "sample_id", "count_prefix:tier7_multiturn:", 2,
        filter_path="gold_absent_as_flown",
    ),
)


def _walk(document: Any, path: str, *, receipt_key: str) -> Any:
    """Resolve a ``/``-joined JSON path. A segment indexes a sequence when the
    current node is a sequence; otherwise it is a mapping key. Raises rather
    than returning a default -- a missing path is a failed verification, never
    a ``None``."""

    node: Any = document
    walked: list[str] = []
    for segment in path.split("/"):
        walked.append(segment)
        here = "/".join(walked)
        if isinstance(node, Mapping):
            if segment not in node:
                raise SynthesisVerificationError(
                    f"receipt {receipt_key!r}: path {path!r} has no key at {here!r}"
                )
            node = node[segment]
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
            try:
                index = int(segment)
            except ValueError as exc:  # pragma: no cover - declaration error
                raise SynthesisVerificationError(
                    f"receipt {receipt_key!r}: path {path!r} needs an index at {here!r}"
                ) from exc
            if not 0 <= index < len(node):
                raise SynthesisVerificationError(
                    f"receipt {receipt_key!r}: path {path!r} index out of range at {here!r}"
                )
            node = node[index]
        else:
            raise SynthesisVerificationError(
                f"receipt {receipt_key!r}: path {path!r} cannot descend at {here!r}"
            )
    return node


def _matches(measured: Any, expected: Any) -> bool:
    """Booleans compare by identity of truth value and TYPE -- ``True`` must
    not satisfy an expected ``1``, because a boolean field silently read as an
    integer is exactly the confusion this module exists to catch."""

    if isinstance(expected, bool) or isinstance(measured, bool):
        return isinstance(measured, bool) and isinstance(expected, bool) and measured == expected
    if isinstance(expected, str):
        return measured == expected
    if isinstance(expected, int) and not isinstance(measured, float):
        return measured == expected
    if isinstance(expected, (int, float)) and isinstance(measured, (int, float)):
        return abs(float(measured) - float(expected)) <= FLOAT_TOLERANCE
    return measured == expected


def sha256_of(path: Path) -> str:
    """SHA-256 over the file's bytes exactly as they sit on disk."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def crlf_defect(path: Path) -> str | None:
    """Return a diagnosis when a PINNED artifact carries CRLF line endings on disk.

    Executable form of the umbrella rule ("Git blob bytes are the evidence hash
    authority: use ``git show <commit>:<path>`` for historical evidence, not CRLF
    working-tree bytes"). ``.gitattributes`` here declares ``* text=auto eol=lf``,
    so every text artifact's blob is LF; a Windows working tree that still holds
    CRLF for such a file hashes to a value NO clean checkout can reproduce. A pin
    taken from those bytes is unreproducible by construction -- it passes on the
    machine that authored it and fails everywhere else, which is exactly how the
    D-GATES pin reached ``master`` and broke CI on 2026-08-25.

    Deliberately NOT solved by hashing the blob instead: these verifiers also hash
    freshly written, not-yet-committed receipts, and silently substituting the
    committed bytes there would report a stale digest as if it were current --
    a worse failure than the one being fixed. Refusing CRLF keeps "the bytes on
    disk" and "the bytes in the blob" identical, so the disk read IS the blob read.

    Returns ``None`` when the file is clean, so callers can append the diagnosis to
    whatever failure channel they already use.
    """

    if b"\r\n" not in path.read_bytes():
        return None
    return (
        f"CRLF line endings in the working tree at {path.as_posix()}: pins are over Git "
        "blob (LF) bytes, so this file's on-disk digest is unreproducible by any clean "
        "checkout. Re-checkout the file (e.g. `git stash`-free: delete it and "
        "`git checkout -- <path>`) before pinning or verifying it"
    )


def verify_receipts(repo_root: Path) -> dict[str, Any]:
    """Re-hash every cited receipt. Fail-closed: a digest mismatch means every
    number below it was read from bytes the landed documents did not cite."""

    rows: list[dict[str, Any]] = []
    for receipt in RECEIPTS:
        path = repo_root / receipt.relpath
        if not path.is_file():
            raise SynthesisVerificationError(f"receipt {receipt.key!r} missing at {receipt.relpath}")
        crlf = crlf_defect(path)
        if crlf is not None:
            raise SynthesisVerificationError(f"receipt {receipt.key!r}: {crlf}")
        measured = sha256_of(path)
        if measured != receipt.sha256:
            raise SynthesisVerificationError(
                f"receipt {receipt.key!r} sha256 mismatch: expected {receipt.sha256}, "
                f"measured {measured} at {receipt.relpath}"
            )
        rows.append(
            {
                "key": receipt.key,
                "relpath": receipt.relpath,
                "sha256": measured,
                "matches_the_landed_digest": True,
                "produced_by": receipt.produced_by,
            }
        )
    return {"receipts": rows, "receipts_verified": len(rows), "all_digests_match": True}


def load_receipts(repo_root: Path) -> dict[str, Any]:
    """Parse each verified receipt once. Explicit UTF-8: this repository's
    default codec on the primary dev machine is not UTF-8."""

    documents: dict[str, Any] = {}
    for receipt in RECEIPTS:
        with (repo_root / receipt.relpath).open(encoding="utf-8") as handle:
            documents[receipt.key] = json.load(handle)
    return documents


def verify_claims(documents: Mapping[str, Any]) -> dict[str, Any]:
    """Check every declared claim against the receipt field it names."""

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for claim in CLAIMS:
        if claim.receipt not in documents:  # pragma: no cover - declaration error
            raise SynthesisVerificationError(
                f"claim {claim.claim_id!r} names unknown receipt {claim.receipt!r}"
            )
        measured = _walk(documents[claim.receipt], claim.path, receipt_key=claim.receipt)
        ok = _matches(measured, claim.expected)
        if not ok:
            failures.append(
                f"{claim.claim_id}: receipt {claim.receipt} path {claim.path} "
                f"holds {measured!r}, synthesis carries {claim.expected!r}"
            )
        rows.append(
            {
                "claim_id": claim.claim_id,
                "receipt": claim.receipt,
                "receipt_sha256": RECEIPTS_BY_KEY[claim.receipt].sha256,
                "path": claim.path,
                "carried_by_the_synthesis": claim.expected,
                "measured_in_the_receipt": measured,
                "matches": ok,
            }
        )
    if failures:
        raise SynthesisVerificationError(
            "the synthesis carries numbers its receipts do not support:\n  "
            + "\n  ".join(failures)
        )
    return {"claims": rows, "claims_verified": len(rows), "all_claims_match": True}


def verify_derived_claims(documents: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce each declared per-sample list and compare against the range or
    count the synthesis quotes."""

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for claim in DERIVED_CLAIMS:
        if claim.receipt not in documents:  # pragma: no cover - declaration error
            raise SynthesisVerificationError(
                f"derived claim {claim.claim_id!r} names unknown receipt {claim.receipt!r}"
            )
        items = _walk(documents[claim.receipt], claim.list_path, receipt_key=claim.receipt)
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
            raise SynthesisVerificationError(
                f"derived claim {claim.claim_id!r}: {claim.list_path!r} is not a list"
            )
        selected = list(items)
        if claim.filter_path is not None:
            selected = [
                item
                for item in selected
                if _walk(item, claim.filter_path, receipt_key=claim.receipt)
            ]
        values = [_walk(item, claim.item_path, receipt_key=claim.receipt) for item in selected]
        if claim.reduce == "min":
            measured: Any = min(values)
        elif claim.reduce == "max":
            measured = max(values)
        elif claim.reduce.startswith("count_prefix:"):
            prefix = claim.reduce.split(":", 1)[1]
            measured = sum(1 for value in values if str(value).startswith(prefix))
        else:  # pragma: no cover - declaration error
            raise SynthesisVerificationError(
                f"derived claim {claim.claim_id!r}: unknown reducer {claim.reduce!r}"
            )
        ok = _matches(measured, claim.expected)
        if not ok:
            failures.append(
                f"{claim.claim_id}: {claim.reduce} over {claim.list_path}/*/{claim.item_path} "
                f"is {measured!r}, synthesis carries {claim.expected!r}"
            )
        rows.append(
            {
                "claim_id": claim.claim_id,
                "receipt": claim.receipt,
                "receipt_sha256": RECEIPTS_BY_KEY[claim.receipt].sha256,
                "list_path": claim.list_path,
                "item_path": claim.item_path,
                "filter_path": claim.filter_path,
                "reduce": claim.reduce,
                "items_reduced": len(values),
                "carried_by_the_synthesis": claim.expected,
                "measured_in_the_receipt": measured,
                "matches": ok,
            }
        )
    if failures:
        raise SynthesisVerificationError(
            "the synthesis carries reductions its receipts do not support:\n  "
            + "\n  ".join(failures)
        )
    return {
        "derived_claims": rows,
        "derived_claims_verified": len(rows),
        "all_derived_claims_match": True,
    }


#: THE HISTORICAL RECORD, FROZEN AND NO LONGER CHECKED AGAINST THE TREE.
#:
#: These are the exact lines the synthesis cited, as they stood at commit
#: ``3f131afd`` -- the last commit carrying the defect and the commit at which
#: the synthesis document was landed. The finding was true then and the
#: document that carries it is not rewritten. They are kept as DATA, published
#: into the receipt, because deleting them would erase the evidence that the
#: defect was real; they are not asserted against the working tree, because
#: they are no longer true of it. Each entry is
#: (relpath, line-number-at-3f131afd, substring).
SOURCE_CLAIMS_AT_3F131AFD: tuple[tuple[str, int, str], ...] = (
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        696,
        "scenario_total = len(rows_by_scenario_full.get(row.scenario, ()))",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        697,
        "intent_total_in_scenario = len(rows_by_intent_full.get(row.intent, ()))",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        698,
        "prior_score = intent_total_in_scenario / scenario_total",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        1085,
        "category_total = len(rows_by_category_full.get((row.domain, row.category), ()))",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        1086,
        "tool_total = len(rows_by_tool_full.get(row.tool_name, ()))",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        1087,
        "prior_score = tool_total / category_total",
    ),
)

#: THE ENGLISH SUCCESSOR, CHECKED AGAINST THE LIVE TREE. Each entry is
#: (relpath, substring) and the substring must be PRESENT somewhere in the
#: file. Line anchors are dropped deliberately: a line number is not part of
#: the claim, and pinning one made the check fail for the wrong reason the
#: moment the defect was repaired.
#:
#: Repair authority:
#: ``docs/readiness/2026-08-25-prior-score-semantics-repair.md``, exposure row
#: ``SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR``.
SOURCE_CLAIMS: tuple[tuple[str, str], ...] = (
    # SLURP: the numerator is now restricted to the conditioning event, and
    # the local's name finally describes what the expression computes.
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        "rows_by_intent_in_scenario_full[(row.scenario, row.intent)] += 1",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        "intent_total_in_scenario = rows_by_intent_in_scenario_full.get(",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        "prior_score = intent_total_in_scenario / scenario_total",
    ),
    # The label-vocabulary fact the SLURP repair is an IDENTITY because of --
    # unchanged by the repair and still the reason the defect stayed hidden.
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        'intent=f"{entry.scenario}_{entry.action}"',
    ),
    # Audio2Tool: the same restriction, on (domain, category).
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        "rows_by_tool_in_category_full[(row.domain, row.category, row.tool_name)] += 1",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        "tool_total_in_category = rows_by_tool_in_category_full.get(",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        "prior_score = tool_total_in_category / category_total",
    ),
    # The range contract whose absence let the same wrong ratio be written
    # twice, with both of its sides.
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        'assert_prior_scores_are_probabilities(values, builder="KB-BUILD")',
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        'assert_prior_scores_are_probabilities(values, builder="KB-BUILD-A2T")',
    ),
)

#: The expressions the repair REMOVED. Asserting their absence is what makes
#: the check a repair proof rather than a spelling test: a re-introduced
#: unconditioned ratio fails here even if the corrected one is also present
#: somewhere in the file.
SOURCE_CLAIMS_MUST_BE_ABSENT: tuple[tuple[str, str], ...] = (
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        "intent_total_in_scenario = len(rows_by_intent_full.get(row.intent, ()))",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        "tool_total = len(rows_by_tool_full.get(row.tool_name, ()))",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py",
        "prior_score = tool_total / category_total",
    ),
)


#: The two artifacts EXACTLY AS THE 2026-08-25 SYNTHESIS LOCKED THEM. Never
#: edit this tuple to track a later refactor -- it is the historical record,
#: and five sealed 2026-08-25 receipts (``gold_absence``, ``oracle_bound``,
#: ``cross_carrier``, ``field_level``, ``degeneracy``; see
#: :data:`_KB_POLICY_DIGEST_AT_SYNTHESIS_PATHS`) independently recorded the
#: ``kb_policy.py`` value under their own ``artifact_hashes`` block, so it is
#: not merely restated here -- :func:`verify_file_digests_at_synthesis` checks
#: it against them. See the module docstring's dated paragraph on the
#: 2026-09-08 FILE_DIGESTS split for why this tuple exists separately from the
#: live :data:`FILE_DIGESTS` below.
FILE_DIGESTS_AT_SYNTHESIS: tuple[tuple[str, str], ...] = (
    (
        "configs/policy/kb-policy-v1-dev100.json",
        "d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/kb_policy.py",
        "2a1c3d75e747db10f723044b05c08d232e1edf47f125d0889c1d2565ba1019af",
    ),
)

#: Live repository files the synthesis names by digest. Checking these closes a
#: gap the receipts cannot: a receipt records what a file hashed to WHEN THE
#: ROW RAN, and the synthesis asserts what the locked artifacts hash to NOW.
#:
#: 2026-09-08 RE-PIN: WAVE R7 (fold commit ``02486939``, merged as
#: ``f45db5aa``) hoisted ``KbAlphaBlendController``'s acquire decision into
#: the module-level ``rails.kb_policy.compute_alpha_blend_decision``, proved
#: behaviour-equivalent branch by branch against the retired shape by
#: ``tests/unit/test_kb_alpha_blend_fold.py``
#: (``docs/readiness/2026-09-08-ojw-r7-rails-standardization-v1.md`` section
#: 3.2). That changed ``kb_policy.py``'s bytes; the config fragment below is
#: untouched. The live pin moves to the equivalence-proven bytes;
#: :data:`FILE_DIGESTS_AT_SYNTHESIS` above keeps the value the five sealed
#: 2026-08-25 receipts actually recorded.
#:
#: 2026-09-09 RE-PIN: the KU-S3 key-norm cache (``rails.kb_policy._KeyNormCache``,
#: preregistration ``docs/readiness/2026-09-07-slurp-consumption-ku-s3-v1-
#: preregistration.md`` section 5, the "bit-exact 3x") computes each key
#: vector's L2 norm once instead of twice per pair, in the same arithmetic,
#: and is proven bitwise-identical by ``tests/unit/test_kb_policy_norm_cache.py``
#: (10,000 random pairs at dim 2048; the seeded selection on a fixed fixture
#: equal to the 2afb4b5c literal). ``kb_policy.py`` moved from
#: ``06368d7ad109cd3c22de126cd5cece5619a0fc73c48bb62b1e953644032a96e6`` to
#: ``336c5b951dd7e98abd63bcebc987bbad6676973a5ccc3e80d2d3db4fb3d88063``; the
#: config fragment is untouched.
#:
#: 2026-09-28 RE-PIN (owner decision 176, ``docs/readiness/2026-09-16-
#: slurp-next-stage-owner-decisions-v1.md`` row 176): two further merges
#: changed ``kb_policy.py``'s bytes. The fastrecall vectorisation (merge
#: ``75a3cab2f``, branch ``fable/fastrecall``) is proven delivery-identical
#: by ``docs/checks/speech-aware-evidence-acquisition/2026-09-27-fast-
#: recall-ranking-identity-v1/README.md``: 25,280 records (3,160 rows x 8)
#: compared between a pristine export of the old tree and this one, 0
#: mismatches, both dumps hashing to
#: ``538444aef3b458a9a337851b70cd04c590fe8d7c3103defba6f94fb9a169b47c``.
#: The W3 fuser (merge ``1b29a8b8b``, branch ``fable/w3``, owner decision
#: 164) adds a NEW ``KNOWLEDGE_FUSERS`` entry,
#: ``saea-fuse-supplyfilter-target-cap-v1``
#: (:data:`TARGET_CAP_FUSE_POLICY_ID`); it is used only by the Stage-3 W3
#: contrast-fold cells (``scripts/flights/w3/``,
#: ``docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/``) --
#: no ``configs/`` fragment and no Stage-2A plan names it. So the
#: synthesis's numbers are unchanged by either merge: the recall the
#: synthesis's cells depend on is bit-identical, and the new fuser is
#: dead code from the synthesis's point of view. ``kb_policy.py`` moved
#: from
#: ``336c5b951dd7e98abd63bcebc987bbad6676973a5ccc3e80d2d3db4fb3d88063`` to
#: ``b0d8d9d46d69f57c3ee377af61a301ec7cd8078b2c2a4bdd47e5ed2cd8f6c32b``; the
#: config fragment is untouched.
FILE_DIGESTS: tuple[tuple[str, str], ...] = (
    (
        "configs/policy/kb-policy-v1-dev100.json",
        "d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/kb_policy.py",
        "b0d8d9d46d69f57c3ee377af61a301ec7cd8078b2c2a4bdd47e5ed2cd8f6c32b",
    ),
)

#: Which receipt, and at what JSON path inside it, independently records
#: kb_policy.py's digest at synthesis time. Five of the eleven :data:`RECEIPTS`
#: carry it -- the 2026-08-25 A2T-carrier analyses that read the alpha-blend
#: policy module -- each under an ``artifact_hashes`` block, but the path to
#: that block is not uniform: ``field_level`` namespaces every artifact hash
#: key under an ``a2t:`` prefix, and ``degeneracy`` nests its A2T
#: ``artifact_hashes`` block one level down, under ``a2t_control`` (it also
#: has a SEPARATE ``slurp/artifact_hashes`` block that does not carry
#: kb_policy.py at all). Used only to assert
#: :data:`FILE_DIGESTS_AT_SYNTHESIS` against what was actually sealed -- never
#: to derive a live expectation.
_KB_POLICY_DIGEST_AT_SYNTHESIS_PATHS: tuple[tuple[str, str], ...] = (
    ("gold_absence", "artifact_hashes/kb_policy.py"),
    ("oracle_bound", "artifact_hashes/kb_policy.py"),
    ("cross_carrier", "artifact_hashes/kb_policy.py"),
    ("field_level", "artifact_hashes/a2t:kb_policy.py"),
    ("degeneracy", "a2t_control/artifact_hashes/kb_policy.py"),
)


def verify_file_digests(repo_root: Path) -> dict[str, Any]:
    """Re-hash the live locked artifacts the synthesis names."""

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for relpath, expected in FILE_DIGESTS:
        path = repo_root / relpath
        if not path.is_file():
            failures.append(f"{relpath} is missing")
            continue
        crlf = crlf_defect(path)
        if crlf is not None:
            failures.append(crlf)
            continue
        measured = sha256_of(path)
        if measured != expected:
            failures.append(f"{relpath}: expected {expected}, measured {measured}")
        rows.append(
            {"relpath": relpath, "expected_sha256": expected, "measured_sha256": measured,
             "matches": measured == expected}
        )
    if failures:
        raise SynthesisVerificationError(
            "a locked artifact the synthesis names does not hash to the value it carries:\n  "
            + "\n  ".join(failures)
        )
    return {"file_digests": rows, "file_digests_verified": len(rows)}


def verify_file_digests_at_synthesis(documents: Mapping[str, Any]) -> dict[str, Any]:
    """Assert :data:`FILE_DIGESTS_AT_SYNTHESIS` against the five sealed
    2026-08-25 receipts that independently recorded kb_policy.py's digest.

    2026-09-08 RE-PIN (module docstring's dated paragraph; see the comment on
    :data:`FILE_DIGESTS`). Since WAVE R7's equivalence-proven fold moved the
    live pin off the synthesis-time value, that value is no longer a live-tree
    assertion -- it must instead be pinned against the record that actually
    carries it, the same way :data:`SOURCE_CLAIMS_AT_3F131AFD` is a frozen
    historical block asserted against its own anchor commit rather than
    merely restated prose. Nothing here opens a new file: ``documents`` is the
    already-verified, already-parsed receipt set :func:`load_receipts` builds
    from the SAME :data:`RECEIPTS` digests :func:`verify_receipts` re-hashes."""

    expected = dict(FILE_DIGESTS_AT_SYNTHESIS)[
        "src/speech_aware_evidence_acquisition/rails/kb_policy.py"
    ]

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for receipt_key, path in _KB_POLICY_DIGEST_AT_SYNTHESIS_PATHS:
        if receipt_key not in documents:  # pragma: no cover - declaration error
            raise SynthesisVerificationError(
                f"FILE_DIGESTS_AT_SYNTHESIS check names unknown receipt {receipt_key!r}"
            )
        measured = _walk(documents[receipt_key], path, receipt_key=receipt_key)
        matches = measured == expected
        if not matches:
            failures.append(
                f"{receipt_key}/{path}: receipt carries {measured!r}, "
                f"FILE_DIGESTS_AT_SYNTHESIS carries {expected!r}"
            )
        rows.append(
            {"receipt": receipt_key, "path": path, "measured_sha256": measured, "matches": matches}
        )
    if failures:
        raise SynthesisVerificationError(
            "FILE_DIGESTS_AT_SYNTHESIS does not match a receipt that independently "
            "recorded kb_policy.py's digest at synthesis time:\n  " + "\n  ".join(failures)
        )
    return {
        "file_digests_at_synthesis": rows,
        "file_digests_at_synthesis_verified": len(rows),
    }


def verify_source_claims(repo_root: Path) -> dict[str, Any]:
    """Assert, from source, that BOTH builders now condition their prior.

    WHAT THE SYNTHESIS FOUND, AND IT WAS TRUE WHEN IT FOUND IT. At commit
    ``3f131afd`` both builders accumulated two independent counters over the
    WHOLE row set, keyed differently, and divided one by the other. Neither
    expression restricted the numerator to the denominator's key. On SLURP the
    numerator's row set was nevertheless contained in the denominator's, but
    only because ``intent = f"{scenario}_{action}"`` makes intent nest inside
    scenario in the LABEL VOCABULARY -- and the local name
    ``intent_total_in_scenario`` asserted a restriction the code never
    performed. That was the whole content of the withdrawn claim "SLURP's
    prior code was correct".

    WHAT IS TRUE NOW. Row ``SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR`` restricted
    both numerators to their conditioning event and added a fail-closed range
    contract on ``ValueBundle.prior_score``. So this function is an ENGLISH
    SUCCESSOR to the landed check, not a rewrite of it: the pre-repair lines
    stay published as :data:`SOURCE_CLAIMS_AT_3F131AFD`, and the live tree is
    asserted to carry the repaired expressions
    (:data:`SOURCE_CLAIMS`) and NOT to carry the defective ones
    (:data:`SOURCE_CLAIMS_MUST_BE_ABSENT`). The landed synthesis document and
    the landed receipt are untouched."""

    cache: dict[str, str] = {}

    def _text(relpath: str) -> str:
        if relpath not in cache:
            cache[relpath] = (repo_root / relpath).read_text(encoding="utf-8")
        return cache[relpath]

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for relpath, needle in SOURCE_CLAIMS:
        present = needle in _text(relpath)
        if not present:
            failures.append(f"{relpath} does not contain {needle!r}")
        rows.append(
            {"relpath": relpath, "expected_substring": needle, "present": present}
        )

    absent_rows: list[dict[str, Any]] = []
    for relpath, needle in SOURCE_CLAIMS_MUST_BE_ABSENT:
        absent = needle not in _text(relpath)
        if not absent:
            failures.append(
                f"{relpath} still contains the REPAIRED-AWAY expression {needle!r}"
            )
        absent_rows.append(
            {"relpath": relpath, "forbidden_substring": needle, "absent": absent}
        )

    if failures:
        raise SynthesisVerificationError(
            "a source claim the synthesis makes is not true of the source:\n  "
            + "\n  ".join(failures)
        )
    return {
        "source_claims": rows,
        "source_claims_verified": len(rows),
        "forbidden_source_claims": absent_rows,
        "forbidden_source_claims_verified": len(absent_rows),
        "source_claims_at_3f131afd": [
            {"relpath": relpath, "line": lineno, "substring": needle}
            for relpath, lineno, needle in SOURCE_CLAIMS_AT_3F131AFD
        ],
        "finding_as_landed_at_3f131afd": (
            "BOTH builders compute prior_score as count(key_N over ALL rows) / "
            "count(key_D over ALL rows) with key_N != key_D and no restriction of the "
            "numerator to the denominator's key. SLURP's ratio is a conditional "
            "probability only because intent = f'{scenario}_{action}' nests intent "
            "inside scenario in the LABEL VOCABULARY; the local name "
            "'intent_total_in_scenario' asserts a restriction the expression does not "
            "perform. The SLURP builder therefore carries the identical latent defect "
            "and would break exactly as the A2T builder did under a non-nesting label "
            "scheme."
        ),
        "finding_now": (
            "REPAIRED. Both builders now restrict the numerator to the "
            "conditioning event -- SLURP count(intent AND scenario) / "
            "count(scenario), Audio2Tool count(tool AND (domain, category)) / "
            "count((domain, category)) -- and both call "
            "knowledge.assert_prior_scores_are_probabilities on the values they "
            "assemble, so a non-probability prior_score can no longer be built. "
            "The SLURP repair is an EXACT IDENTITY because intent determines "
            "scenario; the Audio2Tool repair is not, and its before/after "
            "distribution is published in "
            "docs/readiness/2026-08-25-prior-score-semantics-repair.md. The "
            "landed synthesis document and its receipt are NOT rewritten: the "
            "pre-repair lines stay published above as the historical record."
        ),
    }


def run(*, repo_root: Path, out_path: Path | None = None) -> dict[str, Any]:
    """Arm the guard, verify the receipts, verify every carried number, verify
    the source claims. Returns the report; writes it when ``out_path`` is given."""

    attempts = arm_offline_guard()

    receipts_block = verify_receipts(repo_root)
    documents = load_receipts(repo_root)
    claims_block = verify_claims(documents)
    derived_block = verify_derived_claims(documents)
    digest_block = verify_file_digests(repo_root)
    digest_at_synthesis_block = verify_file_digests_at_synthesis(documents)
    source_block = verify_source_claims(repo_root)

    synthesis = repo_root / SYNTHESIS_RELPATH
    synthesis_block: dict[str, Any] = {"relpath": SYNTHESIS_RELPATH, "present": synthesis.is_file()}
    if synthesis.is_file():
        synthesis_block["sha256"] = sha256_of(synthesis)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "what_this_proves": (
            "FAITHFULNESS ONLY: every number the synthesis carries is the number its own "
            "source receipt holds, at the JSON path named here. It proves nothing about "
            "whether the receipts are right -- that is each landed row's own business -- "
            "and it computes no new experimental quantity."
        ),
        "offline_guard": {
            "armed_before_first_input": True,
            "outbound_connection_attempts": attempts.count,
            "targets": list(attempts.targets),
            "resident_llama_server": "pid 38623 port 8090 NOT contacted, probed, reconfigured or stopped",
        },
        "contacts": {
            "frozen_core": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "audio_seconds": 0.0,
            "gpu_hours": 0.0,
            "new_dependencies": 0,
        },
        "float_tolerance": FLOAT_TOLERANCE,
        "synthesis_document": synthesis_block,
        **receipts_block,
        **claims_block,
        **derived_block,
        **digest_block,
        **digest_at_synthesis_block,
        **source_block,
        "hard_stop": (
            "SYNTHESIS TIER. This module changes no knob, writes nothing under configs/, "
            "rails/ or core/, opens no sealed run directory, authorizes no flight and "
            "reaches no new empirical verdict."
        ),
    }

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="stage-2A matured synthesis verification")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    report = run(
        repo_root=Path(args.repo_root),
        out_path=Path(args.out) if args.out else None,
    )
    print(
        json.dumps(
            {
                "receipts_verified": report["receipts_verified"],
                "claims_verified": report["claims_verified"],
                "derived_claims_verified": report["derived_claims_verified"],
                "file_digests_verified": report["file_digests_verified"],
                "source_claims_verified": report["source_claims_verified"],
                "outbound_connection_attempts": report["offline_guard"]["outbound_connection_attempts"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
