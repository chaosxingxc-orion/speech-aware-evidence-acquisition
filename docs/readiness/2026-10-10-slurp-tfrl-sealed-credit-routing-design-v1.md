# The TF-RL line under owner decision 252: sealed-credit routing (SCR) over typed actions, learned offline from counterfactual columns and flown as one policy arm

Author: Claude Fable 5.1 (root coordinator), 2026-10-10. Status: DESIGN PROPOSAL for owner decisions 254-256
(section 8). Model-free: no contact was made for this note; every number is quoted from a sealed read with its file.
Inputs: the TF-RL history survey compiled 2026-10-10 (scratch; its sources are the files cited below), the NX
programme (`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`), the R6 design
(`docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md`), the measurement instrument
(`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`), the locked-families baseline
(`docs/results/2026-09-26-slurp-stage3-locked-tfrl-academic-baseline-v1.md`).

## 0. The owner's requirement and what the record says

Decision 252 (verbatim in the registry): the system-level lock needs (1) the system beating a single model call
(base viable); (2) training-free RL showing clear gains from system-level reinforcement learning, with the TF-RL
algorithm's use in multimodal knowledge CONSTRUCTION and CONSUMPTION optimised and improved; (3) the comparison
against the published SOTA baseline observed on the test set.

(1) is on file (bare core -> PLAN on DEV-2000-ADDED: intent 61.7 -> 76.6, SLU-F1 38.1 -> 65.4,
`docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`; PLAN -> COMP-1b on the test sample intent
+5.80 [+4.04, +7.42]; v2.2 on the test sample in flight). (3) is a reporting rule from now on (section 7). (2) is the
open problem, and the record is unambiguous about what has NOT worked:

| what was learned | families (n cells) | best measured effect | why it failed (as filed) |
| --- | --- | --- | --- |
| free text (store deltas, GEPA prose, system text, K16 template populations, local K4) | CELL-1/2/3, GEPA, system-text L/B, K16 U2-U6, K4 Solver/Reviewer (about 20 cells) | nothing with CI-LB > 0 on n >= 1,000; K16 win counts 9/5/6 of 16 = coin | S1 unmeasurable gradient (A/A +1.87 > any update), S2 prose-as-policy (the twin reproduces the arm), S3 credit from decoding noise, W1 n = 20..100 |
| selection over samples (support filter, VERIFY-1, plurality) | AGG offline, VERIFY-1, commit line C11 | support filter s=3 +1.40 [+0.55, +2.29] (already flown by ROLL-1); VERIFY-1 intent +0.544 | gains are false-positive suppression on empty-gold rows; the rest is noise |
| statistics -> deterministic rules | v4g (TRAIN tables -> post-processing), the N1 x verdict gate | v4g +1.55 [+0.81, +2.33] Fold B, +0.98 [+0.25, +1.71] A2 (LOCKED); gate +0.75 / +0.98 on two flights (CI-LB > 0) | the ONLY learned components with CI-LB > 0 on n >= 1,000 |
| hand-designed knowledge (B1 exemplars, B4b slot store, AGREE, centroid key, COMP-1b) | Stage-2/3 waves | B1 +12.6, B4b +2.6, AGREE intent +3.3, COMP-1b intent +4.6/+5.8 | human-authored; no learner involved |

Two further facts shape the design. First, every column cell since 2026-09-25 produced COUNTERFACTUAL outcomes per
row: R1 i1/i2 (7 Solver template arms over the same sealed state, 1,080 rows each), R6-P1 (5 Perception arms each
with its own level-2 Solver answer), P-SV-1..4, W-SV-1 / W4-SV (supply-variant arms), ROLL-1/2/3 (5 samples per row),
VAR-1. Arms that are neutral ON AVERAGE were heterogeneous BY CONTEXT: R1's c3 empties right values on non-empty rows
but removes false fills on empty-gold rows, and routing between lock and c3 by one pre-Solver feature (N1 >= 0.2)
produced the gate's +0.75 / +0.98 -- the strongest learned effect on record. Second, the proposer must be local (paid
API 0): the frozen core in a text-only role already has three sealed seams (`rails/proposer.py` + `rails/evolution.py`
description overrides, `rails/stage3_advantage.py`, `rails/stage3_gepa_material.py`); every October template learner
used external GPT-6.x and none learned a change.

## 1. The algorithm: sealed-credit routing (SCR)

SCR is a training-free, off-policy, contextual-bandit learner over TYPED ACTIONS with node-local credit. It never
writes free text into the system; it learns WHICH of several pinned, already-measured actions to take for a row,
from counterfactual outcomes logged in sealed same-flight columns.

**State (pre-node context signature)**, all available before the node that acts and all model-free:
Perception rank-1 intent and its TRAIN entity rate; shortlist size and ranks; the supply statistics of the row's
own exemplars (N1 entity-free share, top-1 cosine, k delivered); audio seconds; channel (headset / far-field);
candidate-count and note-length features; for Solver-side actions also the Perception presence tag where emitted
(R6-P1 p1, AUC 0.671, additional over N1 + prior).

**Actions (typed, pinned, each already a measured arm)**:
- Solver USE actions: the locked Solver template v2 and the sealed template arms r1-c1..c5, r1-i2-c1..c5 (hashes in
  their READMEs); the deterministic delivery actions (v4g; empty-the-row; scope rule) as post-Solver actions.
- SUPPLY actions at the Solver: the measured supply variants (k = 10 / 20 / 30, N1 release, slot-store release,
  card selection) from W-SV-1 / W4-SV / Stage S designs -- flown ones first, unflown ones only after a column flight.
- Perception actions: the locked v3 template and the R6-P1 p1 tag template (the only one that parses); K6p key
  (P-SV-4) as a supply action.
- Selection actions over samples where a pool exists (ROLL: support filter, plurality) -- already locked as ROLL-1's
  delivery; kept as an action for completeness.

**Reward**: the official per-row SLU-F1 contribution of the delivered answer (TP/FP/FN of entities plus the intent
indicator), computed by the registered scorer over sealed outputs; credit is NODE-LOCAL because each column's
counterfactual changes exactly one node's action over the same sealed predecessor state (W2 of the NX audit).

**Learner**: direct-method off-policy evaluation with cross-fitting -- for each (context, action) the logged
counterfactual outcome is known for every action on every row (the columns are complete, not bandit-sampled), so
the policy is a classifier/regressor from context to the best action, fitted on one utterance-hash half and scored
on the other, exactly as the R6 offline driver already does for the gate (`scripts/analysis/slurp_nx_r6_upstream_empty.py`
cross-fit). Model class: shallow trees / L2 logistic over the signature with a minimum-leaf-size floor tied to the
exchange rates (a leaf must cover enough rows that its routing gain clears the 0.67 pp offline floor), plus a
"stay with lock" default so the policy only routes where the cross-fitted gain is positive. Output: a PINNED routing
table (context bins -> action id) with its training receipt, byte-hashed like the v4g TRAIN-statistics tables.

**Exploration**: new actions enter the pool only through the NX column instruments (K <= 6 arms per flight, twin,
delivering lock), authored by the local proposer from the aggregate contrast tables of the current routing policy's
residuals (the NX C3 protocol; the proposer is the frozen core in the text-only `construction-proposer-text` seam or a
hand author, both labelled). Exploitation = the routing table. This is the TF-RL loop: propose typed arms ->
measure them as columns -> learn the routing -> fly the routed policy -> re-propose from its residuals.

**Why this can clear the bar where text learning could not.** The routing never pays the S1/S2 costs: it changes no
template, so the twin reproduces nothing; the gain comes from per-row ACTION choice among measured arms, read offline
at 0.67 pp over 1,080 x K counterfactuals. The per-row oracle over R1's seven arms is large (R1 i1: c5 raw +2.50 and
c3 +0.96 pooled on disjoint row sets); the realistic cross-fit value is what TF-0 must measure before any flight
(section 3 decision rule).

## 2. Knowledge CONSTRUCTION and CONSUMPTION under SCR (the owner's "optimise and improve")

- **Consumption** = the USE-side actions above (which Solver instruction, which post-Solver delivery action, which
  Perception emission), routed per row. The locked COMP-1b consumption path is the default action everywhere.
- **Construction** = the SUPPLY-side actions and the tables that feed the context: the routing learner's context
  tables are built from TRAIN statistics exactly like v4g's (per-intent entity rates, per-slot-type priors, N1 bins)
  by `scripts/build_slurp_v4_train_statistics.py`-style builders (model-free, TRAIN only, R01/Fold A/Fold B
  excluded, byte-pinned). A second construction lever is per-context SUPPLY routing: for a context bin, supply k = 10
  vs 20 vs 30, release the N1 statistic or not, slot-store on or off -- learned from the supply-variant columns in the
  same way. Where no column exists yet for an action (e.g. Stage S's N1 release at M1), it is flown as a K-arm supply
  column first (E42 instrument), never assumed.
- **Improvement of the algorithm** is measured as the cross-fitted routing gain per round and the share of rows the
  policy routes away from the lock; each round's residual contrast tables (typed classes: MISSING / SPURIOUS /
  EMPTY-GOLD-FILL / value-in-supply-not-delivered / off-shortlist intent, `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`)
  tell the proposer which new typed arm to author.

## 3. Rounds, costs, decision rules

| round | object | GPU-h | read | gate to the next |
| --- | --- | --- | --- | --- |
| **TF-0** offline learner | SCR fitted over the sealed counterfactual pools on Fold B (R1 i1 + i2: 7 + 7 Solver arms over 1,080 rows; R6-P1: 5 Perception arms x level-2 Solver answers; P-SV-1..4; W-SV-1 / W4-SV on Fold A) with cross-fitting by utterance-hash halves; context tables built from TRAIN | 0 | cross-fitted delivered SLU-F1 and intent deltas vs lock with CI (10,000 draws, seed 20260915); routed-row share; per-stratum tables; exchange arithmetic; a FIXED routing table with receipt | the cross-fitted SLU-F1 gain has CI-LB > 0 AND point >= 1.5 pp (decision 192) OR >= 1.0 pp with CI-LB >= 0.5 when the intent guard is clean; otherwise the line reports the measured ceiling and stops |
| **E9 policy arm** (engineering) | a `policy_arm` kind in the template/supply column instruments: the delivering or a non-delivering arm chooses, per row, among pinned actions by the pinned routing table over the row's model-free context signature (runner: select the instruction template / supply knob before the node contact; receipt records the chosen action id per row); refusals mirror E1 (one axis, pinned table, no runtime text) | 0 | 4-row dry run through runtime.seal() with the REAL parsers (lesson of 2026-10-10) | gates PASS |
| **TF-1** routed column | Fold B 1,080: arms = routed-policy (non-delivering), the member arms it may choose that are not already lock, twin, lock delivering; same-flight; one cell | ~3-4 | official per-arm columns (NX nomination rule) + node-local reader + the TF-0 prediction vs realised | NOMINATED (CI-LB > 0, above twin) |
| **TF-2** Fold A | routed vs lock + twin, table FIXED from Fold B | ~1.3 | stable per decision 247 | lock the routing table as a module component |
| **TF-3** DEV composed | lock v2.3 = v2.2 + routing vs v2.2 with the in-chain replicate | ~2.5 | composed read | NOMINATED -> next test-sample allowance |
| TF-4 | the next proposer round: new typed arms from the routed policy's residual tables, K <= 6, Fold B column; the learner re-fits over the enlarged pool | ~4 per round | as TF-1 | plateau rule (two rounds without a routed gain) closes the line |

Total to a v2.3 candidate: about 7-8 GPU-h after TF-0; TF-0 and E9 are model-free and start now.

## 4. Measurement discipline (unchanged, restated)

Same-flight columns at n = 1,080 (decision 231); offline reads at 0.67 pp over sealed pools; cross-fitting so no row
is scored by a table that saw it; the twin null measured in every flight (two positive template twins on record:
R1 i1 +0.57, R6-P1 +0.72 [+0.12, +1.37]; one negative, i2 -0.43 -- the nomination rule stays "above the twin");
Fold B selects, Fold A confirms, DEV composes, test under a signed allowance; gold only in offline readers; the
information-gain rule (247) for message elements; decision 192's 1.5 pp for delivered claims; exposure cumulative on
Fold B is recorded (R1 i1, i2, P-SV-4, R6-P1, TF-1, TF-4 ...).

## 5. Carriers (Audio2Tool, Earnings-21/22)

The routing learner is carrier-agnostic: actions are pinned arms, contexts are model-free signatures, rewards are the
carrier's standard scorer per row (`a2t-toolcall`, Earnings WER + ConEC entity mirror). The carrier hooks already
exist (`docs/readiness/2026-09-30-...` carrier module hooks; ALL-OFF cells HELD). Under decision 252 they stay held
until the SLURP lock; the SCR code is written against `core.base` registries so a carrier column flight needs only
its descriptor, adapter and scorer registration (study CLAUDE.md "one base, thin derivations").

## 6. Engineering (model-free, Sonnet in worktrees; Fable reviews; Opus audits)

1. `scripts/analysis/slurp_scr_offline_learner.py` (TF-0): loads sealed column pools by run/attempt id, builds the
   context signature from sealed receipts and the TRAIN statistics tables, fits the cross-fitted routing policy,
   writes `report.json` + `tables.md` + the pinned routing table `prepared/SAEA-SLURP-SCR-ROUTING-TABLE-V1/` with a
   receipt; unit tests on synthetic pools; a `--dry` identity print. Reuses the R6 offline driver's cross-fit,
   bootstrap and `load_gold` paths.
2. Context tables: `scripts/build_slurp_scr_context_tables.py` (per-intent entity rate, per-slot-type prior, N1 bins;
   TRAIN pool minus Fold A / Fold B / R01 / R01C; pinned under `prepared/SAEA-SLURP-SCR-CONTEXT-TABLES-V1/`).
3. E9 `policy_arm` in `rails/supply_variants.py` / `rails/runner.py` / `rails/consumption_module.py` (+ the seal
   validator dispatch, receipt schema v5 with the per-row chosen action id, the readers' arm dispatch), tests
   through `runtime.seal()` and the real hypothesis/supply parsers.
4. The TF family scripts cloned from nx_r6 (`scripts/flights/tf/`), registration package, preflight test.

## 7. SOTA reporting (decision 252, clause 3)

Every milestone and test read states the published SLURP rows beside the repo numbers, with their split:
Multi-SLURP / HerMiT intent 78.33 / SLU-F1 70.84 (full test, trained pipeline); SF-ID 72.06 / 64.02; the
gold-transcript HerMiT upper bound 84.84 / 78.19; ChatGPT 0-shot on gold transcripts intent 79.25 (arXiv:2011.13205
Tables 7-8, arXiv:2305.13512, as quoted in `docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md`).
The repo's PLAN -> COMP-1b test-sample intent 77.02 -> 82.82 already sits above the published trained-pipeline
intent rows; SLU-F1 64.18 -> 64.98 sits at the SF-ID level and 6 pp under HerMiT. The gap the TF-RL line must
close for the lock is therefore on SLU-F1 (entities), not intent -- consistent with every headroom table on file
(consumption 210 items, SPURIOUS 179, hearing 106, empty-gold fill ceiling +3.4).

## 8. Decisions requested (254-256)

- **254** Adopt SCR (section 1) as the TF-RL line of decision 252 mode 2, starting with TF-0 at 0 GPU over the
  existing sealed counterfactual pools and the E9 policy-arm engineering in parallel; TF-1 flies only if TF-0's
  cross-fitted gain meets the rule in section 3. Recommended: yes.
- **255** The local proposer for new typed arms is the frozen core in its existing text-only seam
  (`construction-proposer-text`, EVO-S1 form) fed with aggregate contrast tables only (never text, never gold), or a
  hand author, both labelled; no external proposer (paid API 0). Recommended: yes.
- **256** Decision 253 option A (close the Perception-entity presence line) so the GPU after the successor-2 test
  read goes to TF-1 when TF-0 clears its rule; the p1 presence tag and the K6p key remain available to SCR as
  actions/contexts. Recommended: yes.
