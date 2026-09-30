# Test-sample milestone: COMP-1b against the locked plan on SLURP-TEST-SAMPLE-3010-V1

Registered before contact 2026-09-29 at study commit `881b1787c` (owner decisions 151 and 202);
both cells **held** and **blocked** (below). Nothing here authorises a contact, a flip, a mint or a countersignature.

**Authority.** The signed allowance `docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json` (status `authorised`, owner decision 151) names the two read run ids
used here: `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1` (THE COMPARATOR: the locked v2.0 plan as flown, unchanged) and `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1`
(one dev-admitted composed arm). Owner decision 202: GO once cell A2 (`slurp-native-stage3-comp1b-dev2000-added-v1`) reads NOMINATED or better.
Each read run id gets ONE attempt, ever; the milestone number is consumed whatever the outcome.

**What it is.** MILESTONE-01 is cell A2's arm (COMP-1b) with only the roster moved to the signed test sample: the locked v2.0 plan + (1) the agreement term (w_agree 1.0, recall k 60, delivered 8-1-8) with this roster's own vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1 + (2) the centroid boundary key + (3) no citation contract + (4) nothing else. MILESTONE-00-PLAN is the sealed DEV plan arm (the v2.0 lock as flown) with only the roster moved. Proven by `registered-facts-v1.json` (`composed_config_diffs`): each milestone cell differs
from its DEV source by roster-bound, role-bound (final-report: split role, allowance pin, the TEST scorer sibling
`slurp-slu-official-test`, the one-attempt failure policy) and bookkeeping paths alone, and the arm-vs-comparator delta on
the sample equals A2's arm-vs-DEV-plan delta (recall k 8 -> 60, w_agree, agreement table, centroid key). Derived by
`scripts/flights/comp1/derive_slurp_comp1b_testsample_cells.py`.

**What the allowance forbids, so this package does not carry it.** No four-row smoke on the sample (no smoke run id is
permitted, and a smoke under a read id would consume its one attempt; the form proof is A2's own DEV smoke of the same
composition plus the model-free `check` at the flip). No direct-baseline read. No recovery or resume.

**Measurement.** `cross-flight-with-in-chain-replicate`, n = 3,010 (682 prompts), intent primary, `expected_effect_pp`
**4.6** -- RE-DECLARED 2026-09-30 from the cell A2 read (was A2's own declared 3.8; `redeclaration` in the facts, owner decision 139: a measured number, not a prior). Guard: official SLU-F1 at a FALLBACK null --
no own null exists for the sample; the DEV-2000-ADDED own null scaled by sqrt(913 / 682) (prompt level, conservative):
h_intent 1.3329, h_SLU 1.4492 (recording-scaled 0.664 /
0.7219). FLAGGED.

**Report form.** Intent and SLU-F1 reported separately, each in the post-stratified natural mixture and equal-stratum
(58 intents) weightings, per-intent and per-scenario. A milestone read is development evidence under owner decision 28
("dev numbers are not test claims"): it may say whether COMP-1b held its DEV-nominated intent gain against the locked
system on a test sample; it is never a test claim, never the final read, never publication-grade.

**Post-stratification: inside the official scorer, aggregates only** (coordinator ruling 2026-09-30;
`registered-facts-v1.json` `post_stratification_read`). The roster receipt allows gold only as per-intent aggregate
counts (no label beside a sample id) and the allowance lets gold be read only by the official scorer after delivery, so
no per-row gold bank is used (the DRAFT row `SAEA-SLURP-TEST-SAMPLE-3010-GOLD-BANK-V1`, on the unmerged branch
`fable/samplegoldbank`, is not pursued). The read (`--strata-source scorer`) runs the official-scoring step's
`--strata-inside-scorer` mode (`core.scoring_strata`) in its own process: gold intent through the
`slurp-slu-official-test` binding, in memory; 59 strata counted, 58 carried (general_greet is closure-only, dropped and
the weights renormalised); intent = sum_h w_h * mean_h, SLU-F1 = F1(sum_h w_h*TP_h/n_h, sum_h w_h*FP_h/n_h,
sum_h w_h*FN_h/n_h), equal stratum = the mean of the 58 per-stratum deltas; 10,000 draws, seed 20260929, prompt
clusters resampled within strata. It writes ONE file, `scorer-strata-aggregate.json` (per stratum n_h and per arm
intent-correct / TP / FP / FN totals; weighted deltas; CI95s; input hashes; receipt hash). Never written: a per-row
stratum, any row-level output pairing a sample id with a gold field, a gold label beside an id, text or model output.

**Blockers before the flip.**

1. OWNER GATE (decisions 151 and 202): cell A2 must read NOMINATED or better and the coordinator must report the dev-admitted composed arm to the owner in conversation; the root countersignature of the first milestone row names that report (allowance first_contact_gate).
2. ALLOWANCE: CLEARED -- owner decision 207 signed the successor allowance docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json (sha256 be2bfa5a612d30cf46a2356efa5e8cf5a54707370b4f57378a278bb835fd0ed8), which names both FIT run ids as preparation-kind (non-read) run ids; both fragments pin its bytes (the v1 file is superseded, never edited).
3. PREPARATIONS: preparations 2 and 3 of the sample (SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1, SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1; label-free, owner decision 156) have run and their artifacts are pinned (sample_preparation_pins: 6 pins, verified against the data-root bytes by scripts/flights/comp1/derive_slurp_comp1b_testsample_cells.py --data-root). No sample-preparation pin remains pending (this roster's agreement table and its receipt are pinned from the builder's own receipt, ledger row SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1); the only zero pins are each cell's own first-phase supply, minted at the flip (item E16): ['prepared/SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1/phase-supply-v1.json', 'prepared/SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1/phase-supply-v1.json'].
4. EXPECTATION: CLEARED -- re-declared 3.8 -> 4.6 from the A2 read on 2026-09-30 (registered-facts redeclaration; redeclared_from_a2_read true).
5. READ DRIVER: scripts/analysis/stage3_paired_read.py reports the raw roster mean as 'natural_mixture'; on the floored sample that is NOT the natural-mixture number (design note section 5: post-stratify per-intent accuracy by full-test shares, the roster receipt's weightings block). The post-stratified weighting must land in the read path, with tests on fakes, before the READ row is countersigned.

**Runs.** `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1` / `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1`; `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1` / `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1`. READ `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-READ-V1`.

**Declare, mint, flip, queue, read** (after every blocker clears): (1) root countersigns the five DRAFT rows (naming the
conversational report) and mints `coordination/slurp-stage3-comp1b-testsample-v1/root-admission-v1.json` with `scripts/flights/comp1/comp1b_testsample_mint_receipt.py`;
(2) `scripts/flights/comp1/comp1b_testsample_flip.sh` re-pins comparator then arm to one HEAD; (3)
`scripts/flights/comp1/batch_chain_comp1b_testsample.sh` queues the two-cell campaign (no smoke); (4) after both seals
the READ row is countersigned and `bash scripts/flights/comp1/comp1b_testsample_read.sh` reads it.

## Coordinator ruling on the prompt fit (Fable 5.1, 2026-09-30)

Source: `docs/results/2026-09-30-slurp-milestone-prompt-fit-note.md` (merged `06c160ca`).

1. The check-time `COMPACT_REQUIRED` on the sample's Solver (operational margin −306 tokens) is the same fixed
   worst-case estimate that A2 and the DEV plan arm showed at check time (−316). It is not a new condition. Neither
   DEV cell compacted a row at flight (A2 0 / 1,000; plan arm 0 / 1,000), and the largest real Solver prompt was
   14,125 tokens against the 20,990-token prompt limit.
2. Both milestone cells keep `context_fit_policy: compact-or-abstain` and the `native_contact_fit` step unchanged. No
   config, pin or registration changes before the flip.
3. The milestone read must report `context_fit.compacted_contacts` for both arms. If either count is non-zero, the
   read shows the paired delta with the compacted rows excluded beside the registered paired delta; the registered
   delta stays the primary number.
