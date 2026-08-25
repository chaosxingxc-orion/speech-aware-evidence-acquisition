# STAGE-2A MATURED SYNTHESIS — what is established, what is not, and where the
# limit actually is

Date: 2026-08-25. Status: **SYNTHESIS — no new computation, ZERO CONTACTS, every carried number
machine-checked against its own source receipt.**
Row `SAEA-SN-MF-STAGE2A-MATURED-SYNTHESIS` (registered **before** any verification ran).
Verification module `src/speech_aware_evidence_acquisition/analysis/stage2a_synthesis_verification.py`.
Verification receipt
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-stage2a-synthesis/verification-report.json`.

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 HTTP or socket
requests, 0 audio seconds, 0.0 GPU hours, 0 new dependencies, 0 gold labels newly opened.** The
offline guard (`analysis.dev100_reviewer_audit.arm_offline_guard`, imported rather than
reimplemented) was armed before the first input was opened and recorded **0 outbound connection
attempts against 0 targets**. The resident np2 llama-server (pid 38623, port 8090) was not
contacted, probed, reconfigured or stopped. No knob was changed; nothing under `configs/`, `rails/`
or `core/` was written; new code landed only under `analysis/` and its test.

---

## 0. How to read this document, and what makes it checkable

Nine readiness documents landed on 2026-08-25. This is the one a reviewer reads instead of the
nine. It separates four things that the nine do not separate from each other: what is
**established**, what is **not established**, **where the limit actually is**, and the **epistemic
record** of claims made and withdrawn along the way.

**The verification rule this document was written under.** Every number below was checked against
the **receipt JSON that produced it**, never against another document's restatement of it. That is
not a promise: it is executable. Each quantity is declared in
`analysis/stage2a_synthesis_verification.py` as a `Claim` naming its receipt, the JSON path inside
that receipt, and the value carried here; the module re-hashes all twelve receipts with SHA-256 and
refuses to return unless **every** claim matches its receipt field. **351 checks passed, 0 failed:
332 receipt-field claims, 6 reductions over per-sample lists, 2 live-artifact digests and 11
source-line assertions, across 12 SHA-256-verified receipts — with 0 outbound connection
attempts.** A number that no receipt supports is not in this document; it is in §5. Where a figure
is arithmetic over verified fields rather than a field itself — a ratio, a difference, a percentage
of two counts — the text says so at the point of use.

Citations read `R-KEY · json/path`, where `R-KEY` is a row of the register below. The register
carries the full path and full digest once, so a citation is one hop from a hashed artifact rather
than from prose. Where a figure is a **range or a count over a receipt's per-sample list** rather
than a published field, the reduction is performed by the verification module and the citation says
so.

### Receipt register

| key | artifact | sha256 |
|---|---|---|
| **R-LOCK** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/read-verdict.json` | `2f8e295852e1c09d737467a62123586f097f938ec353dcbe58d258dadc1ea581` |
| **R-DEV500** | `docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev500-confirmatory-read/read-verdict.json` | `b3187fea6f23f637dfa8ac43718667b0286a5c034ea9304bfb03e7029bfc90a3` |
| **R-XC** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-cross-carrier-decomposition/decomposition-report.json` | `9a1903b35f3eff42dc7bf4caee5ba95235af855e9e0fc087ba8d9d7c0d8be5a1` |
| **R-SWEEP** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-admission-scale-sweep/sweep-report.json` | `88f606fe89eb42e675bdd4832a31b028638613eba71d712d3d4ee6cf7aa74d66` |
| **R-GOLD** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-gold-absence/diagnosis-report.json` | `64327e98ff9f91a4affdf75f25e98eb5500aa4ab2eeab8befa6d3978799a3e14` |
| **R-MVE** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-matching-vs-extraction/read-report.json` | `378757b5bc3292395cbdc82a19c936912edaf61725cede012bfad6b77ffd6523` |
| **R-ECD** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-extraction-conditioned-on-dispatch/read-report.json` | `7662fbc381e6994f3c71422154a0facfc86c0e99b656cf91670577036a337525` |
| **R-DEGEN** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-query-key-degeneracy/degeneracy-report.json` | `a1a40999dfddae7642cdc3eaa6763a8fcffe1874e5488210e41618c219a6aeae` |
| **R-FIELD** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-field-level-supply-accounting/accounting-report.json` | `ca973be873318deb6029f183045ac4074653dd1b5943c9113fb78d40766de4c6` |
| **R-ORACLE** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-oracle-query-bound/oracle-query-bound-report.json` | `b564362b64bb41df4d9055518bcd0cd88753e2796b3583ed0b95f626a2ece723` |
| **R-G1** | `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/g1-read-attempt4.json` | `cb5e56584a6d572f7b41b39542201ddb1b361755042eac66c3a70c55fd086f89` |
| **R-KWIDEN** | `docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-kwiden-k1/kwiden-k1-report.json` | `66a340da402f97f6495f87a6a0e3abfa312b3b7771652bd3087407eafee98f9f` |

*(This document carries no digest of its own verification receipt: the receipt records this
document's SHA-256, so a self-citation could never close. The pairing is the receipt's
`synthesis_document` block.)*

### Two caveats that travel with every conditioned number below

> **SECONDARY READING.** The SLURP DEV-1000-NEW500 is the **locked baseline's own population**.
> Every statistic computed on it after the one-shot lock read is a SECONDARY reading: descriptive,
> and it **must not be used to revise, re-tune or restate the LOCK**, which stands exactly as landed
> at `d9fef537`. The nested DEV-500 half and the whole A2T-G1-104 are exposed-tier.
>
> **DOUBLE POST-TREATMENT CONDITIONING.** Cells conditioned on the arms' matching outcome **and**
> on the controller's dispatch decision are conditioned on post-treatment variables twice over, so
> they carry selection (collider) bias. They are **mechanism readings, never effect sizes**, and a
> small-n cell is a mechanism reading whatever its interval says. Both rules were fixed in their
> rows' ledger entries before any n was known.

---

## 1. WHAT IS ESTABLISHED

### 1.1 The locked SLURP cell and its interval

One-shot read, pre-registered statistic, population and lock condition, on the **500 UNEXPOSED**
samples (DEV-1000 minus DEV-500).

| quantity | value | source |
|---|---|---|
| population | 500 unexposed | R-LOCK · `populations/unexposed_new500_n` |
| M0 | **278 / 500 = 55.60 %** | R-LOCK · `primary/M0_correct` |
| BLEND | **379 / 500 = 75.80 %** | R-LOCK · `primary/BLEND_correct` |
| paired delta | **+101 samples = +20.20 pp** | R-LOCK · `primary/delta_samples`, `primary/delta_pp` |
| 90 % CI | **[+17.20, +23.40]**, 0 of 10,000 replicates ≤ 0 | R-LOCK · `primary/bootstrap/ci90_low_pp`, `ci90_high_pp`, `replicates_at_or_below_zero` |
| 95 % CI | [+16.60, +24.00] | R-LOCK · `primary/bootstrap/ci95_low_pp`, `ci95_high_pp` |
| σ̂ | 1.8986 pp | R-LOCK · `primary/bootstrap/sigma_hat_pp` |
| McNemar | W→C **106** / C→W **5** | R-LOCK · `primary/mcnemar/n01_wrong_to_correct`, `n10_correct_to_wrong` |
| lock condition (CI90 low ≥ +10 pp) | **MET**, margin **+7.20 pp** | R-LOCK · `primary/lock_condition_met`, `ci90_lower_bound_margin_vs_threshold_pp` |

Bootstrap: `analysis.bootstrap.paired_cluster_bootstrap`, N = 10,000, seed 20260807 (R-LOCK ·
`primary/bootstrap/n_replicates`, `seed`) — the same primitive, N and seed as every other interval
in this document.

**The locked cell is v1, not v2.** The δ ≥ 0.14 retain-override was removed; with it removed the
same population reads **382 / 500 = +20.80 pp** (R-XC · `decomposition/slurp_unexposed500/
locked_v1_blend_correct`, `locked_v1_population_delta_pp`). The lock is therefore on the *better*
configuration, not the flown one. §3 R4 records why the override was removed.

### 1.2 Scale stability

| tier | delta | 90 % CI | σ̂ | source |
|---|---|---|---|---|
| DEV-500, unexposed 400 | **+19.75 pp** | [+16.50, +23.00] | 2.0563 | R-LOCK · `secondaries/scale_stability_vs_dev500/dev500_unexposed400/*` |
| DEV-1000, unexposed 500 | **+20.20 pp** | [+17.20, +23.40] | 1.8986 | R-LOCK · `primary/*` |

Each point estimate lies inside the other's 90 % interval and the intervals overlap — all three
assertions are booleans in the receipt, not eyeballed (R-LOCK ·
`secondaries/scale_stability_vs_dev500/dev1000_point_inside_dev500_ci90`,
`dev500_point_inside_dev1000_ci90`, `ci90_intervals_overlap`, all `true`). **The effect does not
shrink as the population doubles on disjoint held-out data.**

### 1.3 The ablation attribution: retrieval specificity is the mechanism

Four sealed arms on the DEV-500 NEW400 (400 unexposed).

| contrast | value | what it excludes | source |
|---|---|---|---|
| BLEND − ABL-RANDRET | **+15.75 pp**, CI90 [+12.50, +19.00] | that the second contact or the supply *structure* does the work | R-DEV500 · `secondaries/new400_blend_vs_randret/delta_pp`, `bootstrap/ci90_low_pp`, `ci90_high_pp` |
| ABL-RANDRET − M0 | **+4.00 pp** | the structural residue, reported rather than absorbed | R-DEV500 · `secondaries/new400_randret_vs_m0/delta_pp` |
| BLEND − ABL-RANDICL | **+25.25 pp** | — | R-DEV500 · `secondaries/new400_blend_vs_randicl/delta_pp` |
| ABL-RANDICL − M0 | **−5.50 pp**, CI90 [−9.50, −1.50] | that "any exemplars help" | R-DEV500 · `secondaries/new400_randicl_vs_m0/delta_pp`, `bootstrap/ci90_low_pp`, `ci90_high_pp` |

Generic in-context exemplars **actively hurt**. What is carried across carriers is a retrieval
signal, not a prompt-shape trick.

### 1.4 The ranker repair, and that it is identity-preserving on the locked cell

The ranker summed an *unbounded* prior mass with a cosine *bounded by 1* inside one weighted score.
The commensurability condition — every admissible content facet outranks every prior-mass facet iff
`w_prior · sup(prior_score) < w_cos · τ`, i.e. `sup(prior_score) < 1.08333` — held on SLURP by
**+0.0833** of margin at `sup = 1.0` and failed on Audio2Tool at `sup = 4.1`, a margin of
**−3.0167** (R-SWEEP · `slurp_control/scale_audit/the_invariant/*`,
`audio2tool/scale_audit/the_invariant/*`; both `invariant_holds` booleans are in the receipt). The
consequence, measured: on **104 of 104** A2T trajectories **zero** content facets reached the
top-`m` = 5 window, and `m` would have had to be **15** (R-SWEEP ·
`audio2tool/scale_audit/eviction/trajectories_with_zero_content_facets_in_top_m`,
`m_needed_to_admit_every_admissible_content_facet`).

The repair landed at commit `1341c2db` (`rails/kb_policy.py` sha256
`2a1c3d75e747db10f723044b05c08d232e1edf47f125d0889c1d2565ba1019af`, re-measured against the git
blob at that commit for this document). Its verified properties:

| obligation | measured | source |
|---|---|---|
| A2T dispatch, pre-fix → post-fix | **0 → 15** | R-SWEEP · `audio2tool/alpha_gate/by_variant/V0-FROZEN/would_dispatch`, `.../A6-DIMSUP-FLOOR1/would_dispatch` |
| the dispatch set equals the label-free set exactly | **0** label-free trajectories left undispatched | R-SWEEP · `audio2tool/alpha_gate/by_variant/A6-DIMSUP-FLOOR1/label_free_trajectories_not_dispatched` |
| gold-bearing supply admitted | **68** of 104 | R-SWEEP · `audio2tool/variant_table/A6-DIMSUP-FLOOR1/gold_bearing_supply_admitted` |
| **SLURP DEV-1000-NEW500 identity** — admitted set / supply / dispatch differ | **0 / 0 / 0 on 500** | R-SWEEP · `fix_verification/by_variant/A6-DIMSUP-FLOOR1/slurp_identity_proof/*` |
| the pre-fix baseline gate reproduced the flown supply and dispatch | **104 / 104** each | R-SWEEP · `audio2tool/baseline_fidelity_gate/flown_supply_reproduced`, `flown_dispatch_decision_reproduced` |

**The repair is an exact identity on the locked SLURP cell.** It is a defect repair, not a re-tune,
and the lock's numbers are unaffected by it.

### 1.5 NEW TODAY — the gain operates on BOTH the matching and the extraction axis, *where supply is delivered*

**The delivery rates come first, and they belong beside every number in this subsection.** Only a
DISPATCHED trajectory receives evidence; a RETAINED one stops at contact 0 and is handed nothing.
"Received supply" and "was dispatched" are the same set on both carriers, proved rather than
assumed (R-FIELD · `dispatch_cross_check/*`).

| carrier / population | received supply | delivery rate | source |
|---|---|---|---|
| **SLURP DEV-1000-NEW500 (unexposed)** | **163 of 500** | **32.60 %** | R-FIELD · `channel_cost/slurp/DEV-1000-NEW500 (UNEXPOSED)/two_rate/delivery/*` |
| **Audio2Tool A2T-G1-104 (exposed)** | **15 of 104** | **14.42 %** | R-FIELD · `channel_cost/audio2tool/two_rate/delivery/*` |

**Nothing in this subsection is a population effect. Every figure is conditional on delivery.**

#### The dispatched stratum, SLURP unexposed (n = 163 of 500 = 32.60 %)

| axis | M0 → BLEND | delta | CI90 | source |
|---|---|---|---|---|
| **MATCHING** `scenario_action_exact` | 7 → 100 | **+57.0552 pp** | **[+50.3067, +63.8037]** | R-ECD · `slurp/unexposed500/strata/dispatched/matching/*` |
| **EXTRACTION** macro `slot_f1_exact_mean` | 0.220552 → 0.314943 | **+9.4391 pts** | **[+4.3558, +14.5194]** (CI95 [+3.4794, +15.6179]) | R-ECD · `.../dispatched/bootstrap_slot_f1_exact_mean_delta/*` |
| **EXTRACTION** official micro `slu_f1` | 0.428761 → 0.566332 | **+13.7570 pts** | **[+8.8840, +18.6695]** (CI95 [+7.9762, +19.7020]) | R-ECD · `.../dispatched/bootstrap_slu_f1_micro_delta/*` |

Both extraction intervals exclude zero (`ci90_excludes_zero` `true` in the receipt for each). For
contrast, the **retained** stratum (n = 337, no evidence delivered) moves +2.3739 pp on matching and
**+0.6924** macro extraction points with a CI90 that does **not** exclude zero (R-ECD ·
`slurp/unexposed500/strata/retained/*`).

#### The matching-free cell — the cleanest evidence in the whole session

The dispatched stratum is still matching-confounded: matching moves +57 pp inside it. The cell that
removes the confound is **both arms matching-WRONG *and* supply delivered**, where no matching
movement can explain any extraction movement:

| `neither_matched \| dispatched` | n | delta | CI90 | source |
|---|---|---|---|---|
| macro `slot_f1_exact_mean` | **59** | **+6.7797 pts** | **[+1.6949, +11.8644]** | R-ECD · `slurp/unexposed500/eight_cell_extraction/neither_matched\|dispatched/bootstrap_slot_f1_exact_mean_delta/*` |
| official micro `slu_f1` | **59** | **+15.2312 pts** | **[+8.2127, +22.9778]** | R-ECD · `.../bootstrap_slu_f1_micro_delta/*` |

Both CI90 exclude zero. n = 59 of the 500-sample population; 59 of the 163 delivered.

#### The three-way decomposition, SLURP unexposed — aggregate **+3.5438** macro points

| term | cells | n | contribution | share | source |
|---|---|---|---|---|---|
| **(a) matching-attributable** | the two discordant matching cells | 111 | **+2.5438 pts** | **71.78 %** | R-ECD · `slurp/unexposed500/three_way_decomposition_slot_f1_exact_mean/terms_points/matching_attributable` |
| **(b1) supply-attributable** | concordant matching cells ∩ **DISPATCHED** | **62** | **+0.9333 pts** | **26.34 %** | R-ECD · `.../supply_attributable_dispatched` |
| **(b2) unsupplied residue / decode variance** | concordant ∩ retained | 327 | +0.0667 pts | 1.88 % | R-ECD · `.../decode_variance_unsupplied_retained` |
| aggregate | | 500 | **+3.5438 pts** | closes | R-ECD · `.../aggregate_delta_points`, `closes_to_1e_9` = `true` |

(a) dominates — that finding stands untouched. What is new is the split of the remaining
**+1.0000** point (R-ECD · `.../landed_b_term_recovered_points`): **93.33 % of it is
supply-attributable**, on the 62 trajectories where evidence actually reached the core with matching
status held fixed.

#### Audio2Tool, where supply is delivered (n = 15 of 104 = 14.42 %) — positive, and NOT separated from zero

| stratum | n | slot micro-F1 delta | CI90 | excludes zero? | source |
|---|---|---|---|---|---|
| **dispatched** | **15** | **+12.1212 pts** | [0.0000, +23.0769] | **NO** | R-ECD · `a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/*` |
| retained | 89 | **−3.0250 pts** | [−6.1940, −0.5941] | **yes** | R-ECD · `a2t/strata/retained/bootstrap_slot_micro_f1_delta/*` |

**The sign inverts on the dispatch axis.** The whole-population aggregate — slot micro-F1
0.437870 → 0.412088, a difference of **−2.5782 points** (R-ECD · `a2t/aggregate_M0/slot_micro_f1`,
`a2t/aggregate_BLEND/slot_micro_f1`; the difference is arithmetic, not a published field) — is the
weighted blend in which the unsupplied 89 dominate. The A2T three-way decomposition of the macro
slot-F1 mean confirms the sign: supply-attributable **+0.3205** pts (n = 11) against an unsupplied
residue of **−0.1282** pts (n = 88) and a matching-attributable term of −0.4808 pts (n = 5) —
R-ECD · `a2t/three_way_decomposition_slot_f1_mean/terms_points/*`, `groups/*/n`.

**What is established, stated exactly.** *On the SLURP unexposed half, where supply is delivered
(163 of 500), the gain operates on both axes: matching +57.0552 pp [+50.3067, +63.8037] and
extraction +9.4391 macro / +13.7570 official points, both intervals excluding zero; and in the
matching-free cell (n = 59) extraction still moves +6.7797 / +15.2312 points, both intervals
excluding zero.* On Audio2Tool the dispatched-stratum extraction sign is positive but its interval
touches zero at n = 15 of 104: that is a **mechanism reading**, not an established effect, and §2
carries it as not established.

---

## 2. WHAT IS NOT ESTABLISHED

**1. The Audio2Tool population delta is not separated from zero.** Tool accuracy 62 → 63 of 104 =
**+0.9615 pp**, CI90 **[−2.8846, +4.8077]**, CI95 identical, **41.56 %** of bootstrap replicates at
or below zero, McNemar mid-p 0.6875 (R-G1 · `paired_tool_accuracy/*`). Exact match **29 → 29 =
0.0000 pp**, CI90 [−1.9231, +1.9231] (R-G1 · `paired_exact_match/*`). The population is EXPOSED and
n = 104 sits below the campaign plan's own n ≥ 400 unexposed power floor. The tool-accuracy line
must never be reported without the exact-match line beside it.

**2. THE EXPOSED HALF DOES NOT REPLICATE THE SLURP SUPPLY TERM. This is the single strongest
caution on the extraction claim and it is carried here first among the negatives.**

| population | supply-attributable term (b1) | n | source |
|---|---|---|---|
| DEV-1000-NEW500 (**unexposed**) | **+0.9333 pts** (26.34 % of the aggregate) | 62 | R-ECD · `slurp/unexposed500/three_way_decomposition_slot_f1_exact_mean/terms_points/supply_attributable_dispatched` |
| DEV-500 (**prior-exposed**) | **−0.0533 pts** (1.79 %) | 57 | R-ECD · `slurp/exposed500/three_way_decomposition_slot_f1_exact_mean/terms_points/supply_attributable_dispatched` |

And the matching-free cell does not replicate either: on the exposed half `neither|dispatched`
(n = 55) reads **−0.4848** macro points with a CI90 that does **not** exclude zero (R-ECD ·
`slurp/exposed500/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/*`).
The two halves are the same carrier, the same policy cell and the same flight; the supply term is
positive and interval-separated on one and slightly negative on the other. **Until that is
explained, the extraction result in §1.5 is one population's result.**

**3. Gold-bearing supply converts 2 of 4 on Audio2Tool, and that is not multiplied into anything.**
Of the 15 dispatched, 4 carried the gold tool's own value and **2** ended correct; of the 11 that
did not, **1** ended correct (R-XC · `conditional_conversion/a2t_dispatched_with_gold_bearing_supply/
n`, `blend_correct`; `.../without_gold_bearing_supply/n`, `blend_correct`). n = 4 is a mechanism
reading. No document in this session extrapolates it, and neither does this one.

**4. No legal contact-0 construction is known that produces a tool-identifying query.** The oracle
rung establishes that a query which *identifies the tool* converts (§3); whether any runtime-legal
construction can produce one is explicitly declared unverified there and needs a model contact.

**5. Dispatch preservation under any query fix is unmeasured.** On Audio2Tool it is only
*projected*, from landed answers (§3 R3's K3 figures). On SLURP no dispatch projection of any kind
has been computed, by any row — the gold-absence diagnosis opened no SLURP run directory and the
degeneracy row did not close the gap.

**6. The test split is untouched and stays untouched.** FINAL60 remains reserved. Nothing in this
session read it, named a sample in it, or projected against it.

**7. Three further absences, carried rather than inferred.** No ablation arm has flown on
Audio2Tool, so nothing on that carrier attributes its effect to retrieval rather than to the second
contact. No Audio2Tool variance estimate exists that is independent of the n = 104 read's own
bootstrap. Whether the query-key degeneracy of §3 reproduces on an *unexposed* Audio2Tool
population has been measured on one exposed population only.

---

## 3. WHERE THE LIMIT ACTUALLY IS

This is the section that carries the most value, because four candidate explanations for the
Audio2Tool ceiling were each **refused by measurement** this session rather than argued away. Each
refusal is stated with the number that produced it.

### R1 — REFUSED: KB build coverage. **0 of 11.**

Of the 11 gold-absent dispatched trajectories, **0** are a BUILD defect and **11** are a RANKING
defect; the dominating sub-cause is recorded as `"RANKING"` in the receipt itself (R-GOLD ·
`q1_build_versus_ranking/case_a_build_coverage_defect/n`, `case_b_ranking_recall_defect/n`,
`dominating_sub_cause`). Over the whole 104-sample population, **0** trajectories have a gold tool
with no KB value and **0** have one with no vectored facet (R-GOLD ·
`q1_build_versus_ranking/population_coverage_context/*`). **A KB-construction lever has nothing to
fix on this population.**

### R2 — REFUSED: retrieval width and depth. **No admissible depth reaches gold.**

Under the locked `top_l` = 3, **0 of 11** gold values enter the supply at **any** depth up to the
full 12,601-facet KB; lifting `top_l` entirely reaches **2** of 11 (R-GOLD ·
`q2_reachability_curve/binding_stage/reached_at_some_depth_under_the_locked_top_l_3`,
`reached_at_some_depth_under_any_top_l`). The reachability of the same 11 rises from **0 at the
locked k = 5** to **1.000 at k = 512** — and none of that rise converts into an admitted supply
(R-GOLD · `q2_reachability_curve/curve_case_b_ranking_defect/recall_at_5/count`,
`recall_at_512/rate`).

**The prior that makes this decisive rather than merely arithmetical.** K-WIDEN K1 flew on exactly
the reachability argument — *the gold facet exists deeper, so widen* — and returned: supply changed
on **32 of 100** trajectories, **0 width-attributable flips** (R-KWIDEN ·
`width_supply_replay/supply_changed_count`, `width_attributable_flip_count`). A reachability curve
is evidence about reachability only; on this program's own record it has never been evidence about
conversion.

### R3 — REFUSED: the τ percept gate. **N1 clears τ on 15/15 and supplies gold on 0/15.**

τ is the stage that binds on 9 of the 11 (`top_l` binds the other 2) — R-GOLD ·
`q2_reachability_curve/binding_stage/blocked_by_the_tau_percept_gate`,
`blocked_by_the_top_l_target_budget_only`. The natural inference is that a query which lifts those
cosines past τ converts. **It is refused by measurement.**

The oracle rung's **N1** query uses no gold whatsoever — the L2-normalized mean of the vectored
content facets of the KB units in the trajectory's own tier, determined by the sample id alone,
constructible at runtime today. It lifts the gold-facet cosine from the landed below-τ band of
**0.565332 – 0.635625** (R-ORACLE · `landed_reproduction_gate/checks/tau_band_min/recomputed`,
`tau_band_max/recomputed`) to **0.7209 / 0.7898 / 0.8587** (min / median / max), clears τ on **15 of
15** — and supplies gold to **0 of 15**, binding at the recall window on 15 of 15 (R-ORACLE ·
`lower_constructions/summary/N1_gold_facet_cosine_min`, `_median`, `_max`,
`N1_gold_facet_clears_tau_of_all_dispatched`, `N1_gold_supplied_of_all_dispatched`,
`N1_binding_stage_histogram/recall_depth_k`).

The reason is in the same receipt: the lift raises **148–150 τ-passing targets simultaneously** and
the gold target lands at rank **11–99** among them — both are min/max **reductions** over R-ORACLE ·
`lower_constructions/per_sample[*]/N1_tier_prototype/tau_passing_targets_total` and
`.../gold_target_rank_among_tau_passing`, performed by the verification module rather than quoted.

> **τ is a threshold on similarity, and similarity is not the scarce resource. DISCRIMINATION is.**
> Any future argument from "the gold cosine is only **0.0144–0.0847** below τ" (R-DEGEN ·
> `a2t_control/tau_distance/dead_direct/gap_to_tau_min`, `gap_to_tau_max`) to "a small improvement
> converts" is refuted, at zero cost, on this carrier.

### R4 — REFUSED: a hand-fit dispatch override. **11/11 in sample, 0/3 with 3 damaged out of sample.**

The δ ≥ 0.14 retain-override's registered property was *zero loss by construction*. It fired 14
times on DEV-1000. On the **prior-exposed** half: 11 fires, **11 recovered, 0 damaged**. On the
**unexposed** half: 3 fires, **0 recovered, 3 damaged** — net −3 samples, realized **−0.60 pp**
(R-LOCK · `secondaries/override_subgroup/on_the_prior_exposed_500_no_claim/*`,
`realized_contribution_to_the_lock_statistic/*`). The receipt records the zero-loss property as
`zero_loss_property_held` = **`false`** (R-LOCK · `secondaries/override_subgroup/loss_side/
zero_loss_property_held`). It was removed from the locked cell.

**In-sample perfection is not evidence.** Any future dispatch-widening proposal inherits this prior
and must be gated out of sample.

### What remains: DISCRIMINATION UNDER A DEGENERATE QUERY

Four candidate explanations are gone. What the measurements leave standing is that the retrieval key
on the reachable subset carries almost no information about the utterance.

**The degeneracy, measured.** The 15 Audio2Tool dead-direct trajectories carry **5** distinct query
vectors — **0.3333** per trajectory — **11 of the 15 share ONE key** (73.33 % of the group) and that
one key produced exactly **ONE** flown supply; the 89 label-recovered trajectories carry
**0.9438** distinct keys per trajectory (R-DEGEN · `a2t_control/degeneracy/dead_direct/*`,
`.../label_recovered/distinct_query_vectors_per_trajectory`). The A2T control was a stop condition
and it reproduced the landed diagnosis with `control_reproduced` = `true`.

**The cause is the α veto, and it is arithmetic rather than an empirical regularity.** At α = 0.45
the recovered direct label beats every rival by a guaranteed margin of `1 − 2α` = **+0.10**, and the
worst margin actually observed over the 89 label-recovered trajectories is
**0.10000000000000003** — the structural floor is *attained*, not merely respected (R-XC ·
`ceiling_a_alpha_veto/theorem/guaranteed_margin_1_minus_2alpha`,
`evidence/worst_observed_direct_minus_best_rival`). So `retain == direct-label-recovered` is
structural, evidence can only ever reach the label-free set, and on Audio2Tool **93.33 %** of that
set's answers are structurally empty (R-DEGEN ·
`q3_cross_carrier_verdict/mechanism_discriminants/0/dead_structurally_empty_answer_rate`). **The α
veto selects exactly the trajectories whose contact-0 answer is empty — and the answer IS the
query.**

**This is carrier-scoped, and the boundary was measured rather than assumed.** The dead-over-live
degeneracy ratio is **0.353** on Audio2Tool but **1.240** (unexposed) and **1.027** (exposed) on
SLURP (R-DEGEN · `q3_cross_carrier_verdict/mechanism_discriminants/{0,1,2}/
dead_over_live_degeneracy_ratio`): on SLURP the veto selects the *more* key-diverse subset, so the
causal chain does not transfer. SLURP's dead-direct answers are structurally empty at **1.25 %** and
**1.81 %**, τ refuses the gold facet on only **10 of 160** and **14 of 166**, and the dead-direct
median gold-facet position is **1** against Audio2Tool's **83** (R-DEGEN ·
`slurp/halves/*/tau_distance/dead_direct/gold_facet_below_tau`,
`slurp/halves/UNEXPOSED-NEW500/retrieval/dead_direct/gold_facet_position_median`,
`a2t_control/retrieval/dead_direct/gold_facet_position_median`). SLURP's keys repeat because short
labels **collide**, not because answers are empty — and the proof it is benign collision is that it
happens *more* in the healthy label-recovered group (0.6853 and 0.7156 distinct keys per trajectory,
against the dead-direct 0.850 and 0.735).

### The oracle bound: the KB itself can deliver — and it names no legal fix

The pre-registered oracle (**O3**: every vectored content facet targeting the gold tool, each
withheld from the retrievable pool in turn; delivers if any does) supplies gold to **11 of the 11**
gold-absent trajectories. The decision bands were fixed in the registration before any number was
seen — ≤ 1 refutes, ≥ 8 survives — and the registered outcome is **SURVIVES** (R-ORACLE ·
`oracle_bound/summary/O3_gold_supplied_of_the_gold_absent`, `decision_rule/outcome`,
`bands_fixed_in_the_registration/*`).

| robustness | value | source |
|---|---|---|
| O3 maxima sitting at an exact KB twin | 6 of 11 | R-ORACLE · `oracle_bound/summary/O3_maxima_at_an_exact_twin` |
| **twin-free** gold-supplied of the 11 | **11 of 11** | R-ORACLE · `.../O3_TWIN_FREE_gold_supplied_of_the_gold_absent` |
| typical-case: a *randomly chosen* same-tool sibling query delivers | **1,596 / 1,871 = 85.30 %** | R-ORACLE · `.../O3_RATE_pooled_delivered`, `_tried`, `O3_RATE_pooled` |
| … twin-free | 1,562 / 1,837 = **85.03 %** | R-ORACLE · `.../O3_TWIN_FREE_pooled_rate` |
| the narrow, adversarially-anchored O2 | 6 of 11 (INCONCLUSIVE) | R-ORACLE · `.../O2_gold_supplied_of_the_gold_absent` |

**Under the oracle no stage binds**: τ, `k`, `m`, `c` and `top_l` are all sufficient for this
population once the query is right. **The cell is not the ceiling; the query is.**

> **AND THE ORACLE ENCODES TOOL IDENTITY, SO IT BOUNDS FROM ABOVE AND NAMES NO LEGAL FIX.** Every
> oracle query is built from the trajectory's own gold tool identity — information no runtime query
> could legally have. Supplying such a query is very nearly supplying the answer. Three things bound
> the reading further, all measured: (i) the substitution is most generous exactly where the
> subgroup is hardest — **8 of the 11** are `tier4_implicit` (6) or `tier7_multiturn` (2), tiers
> whose utterances are by the corpus's own construction *not* direct tool invocations (counts
> reduced by the verification module over R-ORACLE · `oracle_bound/per_sample[*]/sample_id`,
> filtered on `gold_absent_as_flown`); (ii) N1 shows
> the gap between "better" and "sufficient" is enormous — 15/15 clearing τ, 0/15 converting; and
> (iii) surviving **authorizes nothing**. The direction that survives is narrow: *a query that
> IDENTIFIES the tool converts; a query that is merely closer to the tool's neighbourhood does
> not.* Whether any legal contact-0 construction can produce the former is exactly what this
> session cannot answer.

**Decontamination, measured rather than asserted.** **0 of 104** evaluation units are in the KB;
**6 of 104** evaluation utterance *texts* appear verbatim as a KB content facet; **0** of those six
are among the 15 dispatched trajectories this bound measures (R-ORACLE · `utterance_leak_check/*`).

### The two channels the evidence actually acts through, for completeness

Separating what the Audio2Tool supply does when it fires: **form repair alone converts 1 of the 11
that changed form (9.1 %); gold-bearing supply converts 2 of 4 (50 %)** (R-GOLD ·
`q5_form_repair_channel/converted_without_gold_bearing_supply/n`,
`converted_with_gold_bearing_supply/n`, `form_repaired_n`). Contact-0 forms of the 15: **11 empty,
3 unparsed, 1 well-formed-but-out-of-vocabulary**; final forms: 12 well-formed non-empty, 3 still
empty; **11 changed form and 9 of those 11 are still wrong** (R-GOLD ·
`q5_form_repair_channel/contact0_form_classes/*`, `blend_final_form_classes/*`,
`form_repaired_but_still_wrong_n`). The empty-call collapse — M0 **14 / 104** → BLEND **3 / 104** —
is the FORM channel working, and **must never be substituted for an accuracy claim** (R-GOLD ·
`q5_form_repair_channel/empty_call_rate/*`; R-G1 · `headline/m0_empty_call_rate`,
`blend_empty_call_rate`).

**K3 is refused on Audio2Tool by the same discipline.** Its own carve-out — "leaves
out-of-vocabulary answers out-of-vocabulary, so dispatch is preserved" — preserves exactly **1 of
the 15**, because the flown dispatch set is 11 empty + 3 unparsed + 1 out-of-vocabulary; and
projected dispatch falls from **15/104** to **3/104** on the arm that measures actual form repair
(**−11.5385 pp, −80.0 % relative**) or to 13/104 on the decode-variance-only arm (**−1.9231 pp,
−13.3 %**) — R-GOLD · `k3_dispatch_projection/flown_dispatch_composition/*`,
`projection_upper_bound_on_repair/*`, `projection_lower_bound_on_repair/*`. **Any fix that improves the query by improving the ANSWER
recovers a direct label, and the α veto then suppresses dispatch one-for-one.**

### Why the two carriers differ in magnitude — the arithmetic that closes

| factor | Audio2Tool | SLURP unexposed 500 | ratio | source |
|---|---|---|---|---|
| reachable share | **14.42 %** | **32.00 %** | **2.2187 ×** | R-XC · `decomposition/cross_carrier/reachable_share/*`, `reachable_share_ratio_slurp_over_a2t` |
| within-reach conversion | **+13.3333 pp** | **+59.3750 pp** | **4.4531 ×** | R-XC · `.../within_reach_conversion_pp/*`, `within_reach_conversion_ratio_slurp_over_a2t` |
| reach × conversion | **+1.9231 pp** | **+19.0000 pp** | 9.88 × *(arithmetic: 19.0000 / 1.9231; not a published field)* | R-XC · `.../reach_times_conversion_pp/*` |
| retain-subgroup drift | −0.9615 pp | +1.6000 pp | sign differs | R-XC · `.../retain_drift_pp/*` |

Both decompositions close exactly against their observed population deltas (R-XC ·
`decomposition/audio2tool/closes_exactly`, `decomposition/slurp_unexposed500/
closes_exactly_as_flown`, both `true`), and the offline replay reproduced the flight's supply,
dispatch and direct-label recovery on **104 / 104** each (R-XC · `fidelity_gate/*`). **Reach and
conversion, multiplied, account for the whole gap; nothing is left over for "the method is weaker on
Audio2Tool" as a separate hypothesis.**

---

## 4. THE EPISTEMIC RECORD — four claims made and withdrawn

This is not self-flagellation. Each withdrawal was forced by a gate that was fixed before the number
was seen, and the four rows together are the evidence that the gating discipline works.

| claim made | what refuted it | the discipline that caught it |
|---|---|---|
| **1. "The Audio2Tool zero-dispatch is a paradigm boundary."** The Stage-G1 BLEND arm dispatched 0 of 104 and the result was read as the method failing to transfer. | **It was an implementation defect in the ranker.** `sup(prior_score)` = **4.1** against a required bound of **1.08333** — a violation of a commensurability condition nothing enforced (4.1 / 1.08333 = 3.78×, arithmetic); on **104/104** trajectories zero content facets reached the top-`m` window. Post-repair (`1341c2db`), dispatch **0 → 15** and the dispatch set equals the label-free set exactly, with the locked SLURP cell byte-identical on **0/500** differences. *(R-SWEEP · `audio2tool/scale_audit/the_invariant/*`, `.../eviction/trajectories_with_zero_content_facets_in_top_m`, `alpha_gate/by_variant/*/would_dispatch`, `fix_verification/by_variant/A6-DIMSUP-FLOOR1/slurp_identity_proof/*`)* | **Mechanism invariants reported as FALSIFIED rather than quietly passed.** G1 published `retain == direct-label-recovered` as FALSIFIED and its branch-only replay as VACUOUS. A falsified invariant forced an audit of the implementation instead of a conclusion about the paradigm. Both are now PASS (R-G1 · `mechanism/retain_equals_direct_label_recovered`, `mechanism/branch_only_replay_is_vacuous` = `false`). |
| **2. "KB coverage is the lever."** The gold-absence of 11 of 15 dispatched trajectories was expected to be a build hole to be filled with more values and deeper coverage. | **0 build defects.** Of the 11, **0** are BUILD and **11** are RANKING; over the whole 104, **0** trajectories have a gold tool with no KB value and **0** with no vectored facet. *(R-GOLD · `q1_build_versus_ranking/case_a_build_coverage_defect/n`, `case_b_ranking_recall_defect/n`, `population_coverage_context/*`)* | **The BUILD/RANKING partition and its fidelity gate were pre-registered.** The row fixed the split and its 104/104 ×3 precondition before computing, so a negative could not be re-partitioned after the numbers were seen. |
| **3. "SLURP's prior code was correct."** The admission-scale sweep priced the SLURP builder as safe *by construction* while the Audio2Tool builder was a bug — the receipt still records the reason as "prior_score is intent_total_in_scenario / scenario_total … so the ratio is a genuine conditional probability". | **It is the same unconditioned ratio, saved only by label nesting — verified here against source, not carried from prose.** `knowledge_build.py:698` divides `len(rows_by_intent_full[intent])`, accumulated **globally** at line 504, by `len(rows_by_scenario_full[scenario])`, accumulated globally at line 505. `knowledge_build_a2t.py:1087` divides `len(rows_by_tool_full[tool])` (line 853) by `len(rows_by_category_full[(domain, category)])` (line 854). **Neither expression restricts the numerator to the denominator's key.** SLURP's ratio is a probability only because `intent = f"{scenario}_{action}"` (line 202) nests intent inside scenario in the **label vocabulary** — and the local name `intent_total_in_scenario` asserts a restriction the code never performs. Under a non-nesting label scheme the SLURP builder would break exactly as the A2T one did. | **This synthesis's own verification rule.** The claim was re-checked against source rather than restated from the landed sweep's prose; all 11 line-level assertions are machine-checked in `analysis/stage2a_synthesis_verification.py::SOURCE_CLAIMS`. Two carriers, one latent defect: the A2T failure was the first time the vocabulary stopped protecting it. |
| **4. "The supply does not serve extraction."** The matching-conditioned read concluded, on both carriers, that once matching is held fixed the supply adds nothing. Its fidelity gate passed and its arithmetic closes exactly (R-MVE · `fidelity_gate/pass`; `slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/closes_exactly`). | **It was measured where no supply was delivered.** The conditioned cell holds **3 dispatched of 273** on SLURP unexposed, **2 of 255** on the exposed half and **0 of 60** on Audio2Tool. Where supply IS delivered: SLURP `neither\|dispatched` (n = 59) **+6.7797** macro pts CI90 [+1.6949, +11.8644] and **+15.2312** official pts CI90 [+8.2127, +22.9778]; A2T dispatched slot micro-F1 **+12.1212** pts. *(R-ECD · `slurp/unexposed500/cross_tabulation/cells/both_matched/dispatched_n`, `slurp/exposed500/.../dispatched_n`, `a2t/.../dispatched_n`, `slurp/unexposed500/eight_cell_extraction/neither_matched\|dispatched/*`, `a2t/strata/dispatched/*`)* | **Condition on the mechanism, not only on the outcome.** A successor row asked whether the cell had received any evidence at all — and reproduced the landed read's arithmetic **to the digit** before challenging its interpretation. The (a)-dominance finding survived untouched at **71.78 %** / **94.85 %**; only the reading of the residual changed. |

---

## 5. COULD NOT VERIFY — omitted rather than carried

Listed so their absence is visible rather than inferred. Each is a quantity that appears in a landed
document and that this synthesis declines to carry.

1. **Every cross-carrier "the A2T deficit is N× the SLURP deficit" ratio.** The gold-absence
   diagnosis publishes "5.7× to 11.3×, ≈7.6× at the midpoint"; its SLURP side is *quoted* from
   `docs/readiness/2026-08-25-key-construction-agenda-plan.md` §2.2 — a plan, not a receipt — as a
   range across three populations it does not name. The degeneracy row publishes 6.99× / 8.12× from
   its own DEV-1000 measurement, but those too are arithmetic over other fields rather than
   published fields. **This document carries no such ratio.** It carries the per-group rates
   instead, each of which is a receipt field: gold-in-top-5 on the dead-direct set is **26.67 %**
   (A2T), **70.00 %** (SLURP unexposed) and **69.88 %** (SLURP exposed), against **71.91 %**,
   **76.47 %** and **75.45 %** on the respective label-recovered sets, and the A2T median
   gold-facet cosine is **0.6054** dead against **0.8632** label-recovered (R-DEGEN ·
   `a2t_control/retrieval/*`, `slurp/halves/*/retrieval/*`).
2. **Every campaign spend figure** — 321 / 400 core contacts, 1,590.656 / 2,000 metered audio
   seconds, 79 remaining, 136 / 200 tool contacts. These live in the AttemptStore under
   `SPEECHRL_DATA_DIR`, outside Git; this row opened no run directory or attempt store. The
   cross-carrier verdict itself discloses that the 136 tool-contact figure is **not**
   AttemptStore-backed and is carried by report arithmetic. Nothing here is a spend claim.
3. **The "about 1.9 pp of score noise" Audio2Tool decode-variance estimate.** Superseded by direct
   per-population measurement of retained-set response-text divergence — **10.11 %** (A2T),
   **14.84 %** (SLURP unexposed), **16.72 %** (SLURP exposed) — which this document carries instead
   (R-ECD · `*/decode_variance_channel_on_retained/retained_response_text_divergence_rate`).
4. **Every per-field-group token figure in the field-level accounting.** They are estimates from a
   character-to-token model published under two competing models with their own calibration error;
   the row says so itself and refuses a per-group rate for collinearity. Only that row's
   **delivery rates** and its **parse-fidelity and dispatch cross-checks** are carried here, and
   those are counts.
5. **Any conversion estimate for the two `top_l`-blocked trajectories.** Lifting `top_l` would reach
   2 of 11; what that would convert to is unknown, and n = 2 could not measure it either way.
6. **A positive account of SLURP's residual dead-direct retrieval deficit.** Key collapse is refuted
   as its cause; no replacement is identified, and the standing confound (a bad key versus an
   intrinsically harder sample) cannot be resolved offline.
7. **Why identical SLURP texts embed to slightly different vectors.** Measured (**136** distinct
   vectors from **133** distinct texts on the unexposed dead-direct set of 160 — R-DEGEN ·
   `slurp/halves/UNEXPOSED-NEW500/degeneracy/dead_direct/distinct_query_vectors`,
   `distinct_contact0_texts`, `n`), not explained. No conclusion here depends on it; the
   distinct-TEXT ratio is the conservative floor and it is still 0.831 against A2T's 0.333.

### Disagreements found between landed documents, and the receipt that settles each

| disagreement | settled by | outcome |
|---|---|---|
| The Audio2Tool reachable-set form composition. The cross-carrier verdict's correction C1 wrote "**12 of the 15 became** well-formed non-empty tool calls"; the gold-absence diagnosis' correction C1 said 12 *ended* well-formed but only **11 changed** form. | **R-GOLD** · `q5_form_repair_channel/contact0_form_classes` = {empty 11, unparsed 3, well-formed-non-empty 1}, `blend_final_form_classes` = {well-formed-non-empty 12, empty 3}, `form_repaired_n` = **11** | The gold-absence reading is correct; the word to strike is "became". The twelfth (`tier1_direct:004159`) was already well-formed at contact 0 and dispatched for an out-of-vocabulary tool name. This document uses 11-changed / 12-ended. |
| The conditioned extraction verdict. `d4c75c7a` concluded the supply does not serve extraction; `6c6ec719` concluded it does where delivered. | **R-ECD** · `slurp/unexposed500/cross_tabulation/cells/both_matched/dispatched_n` = 3 of 273; `slurp/exposed500/...` = 2 of 255; `a2t/...` = **0** of 60 | Not an arithmetic conflict: R-ECD reproduces every one of R-MVE's four-cell contributions exactly. The landed conditioned cell held **270 of 273**, **253 of 255** and **60 of 60** trajectories that received no evidence at all, so it could not have shown a supply effect. §4 row 4 carries it. |
| The degeneracy clause I3's absolute bar of ≥ 0.90 distinct query vectors per dead-direct trajectory, written A2T-calibrated but directed at SLURP. | **R-DEGEN** · `slurp/halves/*/degeneracy/label_recovered/distinct_query_vectors_per_trajectory` = **0.6853** and **0.7156** | The bar is unsatisfiable-by-construction on SLURP: it would demand of the dead-direct subgroup a diversity SLURP's own *healthy* subgroup (0.685 / 0.716) does not reach. Correct on Audio2Tool, where the reference really is 0.9438. On SLURP it must bind as non-degradation. |
| The τ-gap framing ("all nine sit within 0.10 of the bar") read as "a small nudge converts". | **R-ORACLE** · `lower_constructions/summary/N1_gold_facet_clears_tau_of_all_dispatched` = 15, `N1_gold_supplied_of_all_dispatched` = **0** | The gap figures are right and the natural inference from them is wrong. §3 R3 carries the refutation. |
| The oracle rung's first version asserted decontamination from the builder's source; its own successor commit measured it. | **R-ORACLE** · `utterance_leak_check/eval_UNITS_present_in_the_kb` = 0, `eval_UTTERANCE_TEXTS_matching_a_kb_content_facet` = **6**, `text_matches_among_the_dispatched_15` = **0** | The measurement is carried, not the assertion. No number in that rung changes. |

One near-disagreement that is **not** one: the admission sweep's pre-flight projection bucketed the
gold-bearing dispatched trajectories as "2 at rank 1, 2 at rank 2–3"; the post-flight replay refines
it to rank 1: 2, rank 2: 2, rank 3: 0. That is a refinement of a coarser bucket, and the projection
matched the flight to the sample.

---

## 6. OPEN OWNER DECISIONS

None of these is an implementer's call, and this document makes none of them.

**D1 — the α trade, with its adverse δ prior.** Widening dispatch buys reach. The offline sizing is
already done: with no α gate, **68 of 104** Audio2Tool trajectories would carry gold-bearing supply,
of which **64** sit in the retained set — where **60 of the 89** retained trajectories are already
correct under BLEND (61 under M0), so a widened dispatch would be putting evidence in front of
mostly-correct answers (R-XC ·
`ceiling_b_gold_coverage/population_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE`,
`retained_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE`,
`decomposition/audio2tool/unreachable_subgroup_retain_primary/blend_correct`, `m0_correct`, `n`).
Two costs stand against it. First, the
**adverse prior of §3 R4**: the last hand-fit dispatch-widening rule was 11/11 in sample and 0/3
with 3 damaged out of sample, with a loss side that was "zero by construction". Second, a
**per-carrier α breaks the byte-identical transfer claim**, which is itself a scientific asset. This
is a trade framed for the owner — buy reach on one carrier, sell the strongest generality statement
the study has — never a tuning step.

**D2 — whether to open a new Audio2Tool contact cell.** The population effect is capped near +2 pp
by the mechanism itself (reach 14.42 % × within-reach conversion 13.3333 pp = **+1.9231 pp**), so a
whole-population design is the wrong thing to power against. Any such cell should be stratified on
the reachable set, or paired to remove the decode-variance channel, or it is not worth flying. The
cheapest thing that would make any Audio2Tool number interpretable is a repeated-decode replication
at fixed config.

**D3 — the hash-manifested release freeze of the locked baseline.** The lock names a configuration
(`configs/policy/kb-policy-v1-dev100.json`, sha256
`d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919`, re-measured for this document),
a KB snapshot, `rails/kb_policy.py` at `1341c2db` (sha256 `2a1c3d75…1019af`), and a serving profile.
Whether that set is frozen into a single hash manifest — so that every later comparison cites one
artifact rather than four — is an owner decision.

**D4 — the umbrella `required_truth` token list and the `STAGE2A_R0_INCOMPLETE` / `R1_WITHHELD`
endpoint tokens.** Umbrella
`docs/superpowers/specs/2026-08-25-research-objective-required-truth-reconciliation-decision-request.md`
is OPEN awaiting an owner decision on six failing `required_truth` tokens, and its Appendix A reports
that **both** trailing fields of the endpoint token
`DIRECTION_LOCAL_PIPELINE__R1_SUNSET__SPEECH_AWARE_EVIDENCE_ACQUISITION_OWNER_GO__STAGE2A_R0_INCOMPLETE__R1_WITHHELD`
are stale, not only the one flagged: R0.1 and R0.3 are closed and `R1_WITHHELD` was released by the
2026-08-08 owner GO. The successor value is the program endpoint token and is explicitly an owner
call. This study repository changes nothing there.

---

## 7. HARD STOP — what this synthesis does NOT authorize

This is a **synthesis over landed evidence at zero contacts**. It authorizes:

- **nothing to fly.** No model contact, no tool contact, no embedding contact, no tokenizer contact,
  no flight, no re-flight, no G2 opening, no new attempt on any run id. The resident service was not
  touched.
- **no knob change.** α, τ, `k`, `m`, `c`, `top_l`, `top_k` and the rank weights are read and
  reported, never written. `configs/`, `rails/` and `core/` are untouched. §3's findings about which
  stage binds, and §6/D1's sizing of what a different α could reach, are **measurements, not
  proposals**.
- **no revision of the LOCK.** Every SLURP unexposed-500 statistic here is a SECONDARY reading on the
  locked baseline's own population. It does not revise, re-tune, restate or re-open
  `SAEA-DEV1000-BASELINE-LOCK`, whose read was one-shot and is closed. The lock stands exactly as
  landed at `d9fef537`.
- **no claim.** No generality claim, no superiority claim, no cross-carrier transfer claim, and no
  conclusion about the method's capability beyond the two already-read populations. "The locked cell
  generalizes" is not established here and is not implied here.
- **no new agenda item.** The obvious reading of §3 — that a retrieval key which is a constant should
  be built from something other than an empty answer — is a design observation. Any such item needs
  its own registration, its own two-sided falsifier, its own dispatch-preservation clause and an
  owner decision, and this document opens none of them. **K3 stays REFUSED for Audio2Tool** and
  unprojected on SLURP.
- **no test contact. FINAL60 stays reserved.**
- **no Stage-3 activity of any kind**, no manuscript, no paper-scale profile, no promotion. Stage-3
  requires `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` into a `papers/<slug>` repository and this
  repository never accepts it.

`consumed` stays **no**: no seal is broken by this document and no split is newly opened. No gold
label was read by this row at all — every input is a receipt or a source file already committed to
this repository.
