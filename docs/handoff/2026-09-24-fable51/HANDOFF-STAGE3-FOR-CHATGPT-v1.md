# Stage-3 handoff for ChatGPT: the complete experiment plan and the current state

Author: Fable 5.1 (root coordinator). Created 2026-09-24 (UTC). **Last refreshed: 2026-09-25 01:30 UTC**
(this is ONE living document: when a new result lands, the key conclusions in sections 4, 6 and 7 are
rewritten in place and the refresh stamp moves; there is no log section). Study repository:
`studies/speech-aware-evidence-acquisition` on `master` (HEAD at writing: `cc9fd097`; every commit
named below is on `master`). Umbrella repo: `exploring-l4-intelligence` (`wiki/Research-Objective.md`
carries the five-line current state). Language of every document: English (program policy); the
owner converses in Chinese.

This document is written for a second AI collaborator (ChatGPT) who may be asked to reason about
the plan, propose experiments, or review claims. It is self-contained: nothing here needs the
conversation history. Where a fact is a measurement, the sealed run id and the analysis root are
named so the number can be re-derived; where a fact is a decision, the owner-decision number is
named (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, rows 1-114).

---

## 1. What the program is

A research program on **training-free, reward-guided inference-time control of a frozen speech
omni model**. The frozen core is Qwen3-Omni-30B-A3B-Instruct (GGUF q4_k_m, llama.cpp server on
one RTX 5090 Laptop, np4 x 24,576-token slots, max 512 completion tokens), reached only across an
API-shaped boundary. Zero parameter updates. No second answering LLM. No transcript tokens anywhere
(owner rule 2026-09-06). Gold never enters runtime.

Carrier of record: **SLURP** (spoken language understanding: scenario / action / entities; the
official metric is the SLURP `evaluate.py` pooled SLU-F1 with the intent accuracy beside it). The
other two admitted carriers (Earnings21+ConEC, Audio2Tool) are parked behind SLURP for Stage 3.

The system under study is a **plan** of four nodes over the frozen core, one contact each plus a
review loop: Perception (produces a bounded intent-candidate list from the speech plus retrieved
intent cards) -> Solver (answers with intent + entities, given the candidates, retrieved exemplars
and slot contracts) -> Reviewer (verdict) -> Planner (route: accept / one revision). Its supply
comes from knowledge stores built from TRAIN only (exemplars keyed by speech embeddings, slot
contracts, intent cards). The plan is fixed as **"v2.0 lock"** (`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`, owner decision of 2026-09-22).

## 2. The measurement protocol every Stage-3 claim obeys

- **Rosters.** TRAIN Fold A: 1,080 recordings, 125 speakers, 18 scenarios x 60
  (`docs/receipts/rosters/slurp-evo-fold-a-v2.json`). Construction subset R01C: 625 TRAIN
  recordings disjoint from Fold A / Fold B / DEV-1000 / DEV-2000-ADDED / every knowledge-source
  utterance (decision 102). Fresh dev roster DEV-2000-ADDED: 1,000 devel recordings
  (`docs/receipts/rosters/slurp-dev-2000-added-v1.json`, gold per-scenario labels withheld per
  item). Test split: 13,078 rows, prepared, **never read** (decisions 99, 107, 108: one read, only
  after a fresh-roster gain exists; deferred on 2026-09-24).
- **Comparators are sealed bytes**, never re-flown: TRAIN Fold A PLAN
  `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` (official SLU-F1 63.63 / intent 82.22) and its
  request-identical replicate PLANr `...-LOCK-REPLICATE-V1` (63.80 / 82.50); DEV-2000-ADDED PLAN
  `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` (65.40 / 76.60) and its replicate
  `...-DEV2000-ADDED-REPLICATE-V1` (65.15 / 76.80, sealed 2026-09-24).
- **Own null.** The admission margin of a roster is the CI95 half-width of PLAN vs PLANr on that
  roster (paired whole-speaker bootstrap on Fold A, utterance-clustered on DEV-2000-ADDED; 10,000
  draws, seed 20260915): Fold A h_SLU 1.2485 / h_intent 0.9943; DEV-2000-ADDED h_SLU 1.2525 /
  h_intent 1.1520. The own null is sealed BEFORE any arm's contrast on that roster.
- **Decision rule (registered per cell, decision 99 / 25).** ADMITTED iff the paired official
  pooled SLU-F1 delta has CI95 lower bound > 0 AND intent is non-inferior at the own null;
  NEUTRAL when both guards are non-inferior without a proven gain; HARMFUL on a measured loss
  (CI95 upper bound below zero or a point estimate beyond the margin). Width alone is never
  HARMFUL. A **derangement twin** (the same store with its values re-attached by a within-node
  permutation) decides attribution (form vs content), never admission.
- **Hygiene.** Registration before contact (exposure ledger row + ExecutionPlan + decision receipt
  in `$SPEECHRL_DATA_DIR/coordination/<cell>/`), one official score per complete manifest, every
  Stage-3 cell carries a training-free-RL algorithm label resolving in
  `core.stage3_algorithms` (decision 101; gate `scripts/checks/stage3_algorithm_label_check.py`),
  every verdict carries a per-scenario table and a cost row, GPU flights only through the batch
  driver scheduled task (decision 77), four-row form smoke before every new form.
- **Dev numbers are development numbers** (decisions 28 / 86): nothing on TRAIN or DEV is a
  claim; the one-shot test read makes the claim.

## 3. What Stage 3 built (the engineering baseline, closed)

The training-free RL loop over the locked plan, with two algorithm families implemented and a
third registered:

| step | artefact | run / script | state |
| --- | --- | --- | --- |
| ROLL-1 rollout | 625 R01C rows x 5 Solver samples, 5,347 contacts | run `SAEA-SLURP-STAGE3-ROLLOUT-*` (see `docs/readiness/2026-09-22-slurp-stage3-construction-r01-preparations-v1.md`) | sealed 2026-09-23 |
| S3-3 scoring | per-sample official scores on copies, best/worst pairs, 225 disagreeing rows | `scripts/analysis/stage3_rollout_score.py` | done |
| ADV-1 advantage | the frozen core reads best-vs-worst trajectories + construction gold and writes node-targeted 4-line statements (NODE / DELTA-KIND / TARGET / STATEMENT); 225 rows -> 396 blocks, 100 % legal | run `SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1`; `docs/results/2026-09-23-slurp-stage3-advantage-r01-read.md` | sealed |
| S3-5 curation / release | store `stage3-deltas-v1r` (379 values, intent-facet routed), per-node `context_supply` routes (Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception 4 unconditional) | `scripts/build_slurp_stage3_delta_store.py`, `core.driver prepare-semantic-knowledge` | released |
| CELL-1 | plan + v1r vs PLAN, Fold A, + twin | `SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1` (+ `...-TWIN-V1`); verdict `docs/results/2026-09-23-slurp-stage3-delta-cell-r01-verdict.md` | READ |
| retention (decision 83) | per-scenario band vs PLANr x frontier rule over the CELL-1 read: 200 kept / 179 retired -> `stage3-deltas-v2` | `scripts/build_slurp_stage3_delta_retention.py`; `docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/iteration-2-retention-v1.md` | released |
| CELL-2 | plan + v2 vs PLAN, Fold A, + twin | `SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1` (+ twin); verdict `docs/results/2026-09-24-slurp-stage3-delta-cell-r02-verdict.md` | READ |
| GEPA proposer | one reflective contact per (scenario, node) group: 68 groups over 173 R01C rows, best/worst trajectories + current deltas -> 335 proposal blocks | `SAEA-SLURP-STAGE3-GEPA-R01-V1`; `rails/stage3_gepa.py`, runbook `scripts/flights/batch/gepa_to_deltas.sh` | sealed |
| GEPA store | `stage3-deltas-gepa-v1` (448 values = 248 new + 200 retained; permitted roster = ADV-1 disagreeing receipt, the v1r / v2 precedent) + twin | `docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/` | released |
| CELL-1-GEPA | plan + gepa-v1 vs PLAN, Fold A, + twin | `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1` (+ twin); verdict `docs/results/2026-09-24-slurp-stage3-delta-cell-gepa-r01-verdict.md` | READ |
| scenario gate | row-level gate on the candidate-bound routes: policy `majority-candidate-scenario-not-in-v1`, reads only the row's own Perception candidates; registry `core.base.STAGE3_SUPPLY_GATE_POLICIES`; skip receipt `scenario-gate-closed` | commit `060d822c`; design `docs/readiness/2026-09-24-slurp-stage3-scenario-gate-design-v1.md` | merged, 35 tests |
| CELL-3 | plan + v2 through the gate (Perception seeds dropped) on DEV-2000-ADDED vs the sealed B6 PLAN, own null from PLANr-DEV2000, + twin | `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1` (+ twin); verdict `docs/results/2026-09-24-slurp-stage3-delta-cell-r03-gate-verdict.md` | READ (closes the line, decision 111) |
| ACE family | registered in `core.stage3_algorithms` (`ace-grow-refine-v1`), not flown | -- | planned, now deprioritised |

Supporting tooling (all on `master`): batch driver family (`scripts/flights/batch/batch_driver.sh`,
`batch_chain_*.sh`, `repin_loop_generic.sh`, `mint_decision_receipt.py --out-name`,
`gpu_warm.sh` pre-step warm-up after a cold-GPU STOP on 2026-09-24), the cell verdict writer
(`scripts/flights/batch/cell1_verdict.py --cell r01|r02|gepa`), reads
(`scripts/analysis/plan_cell_read.py` for Fold A cells; `scripts/analysis/slurp_paired_roster_read.py`
for DEV rosters; `scripts/analysis/stage3_delta_consumption_read.py` per-node consumption), three
model-free diagnostics (`slurp_general_scenario_diagnostic.py`,
`slurp_cell3_fresh_roster_loss_diagnostic.py`, and the bad-case bank in flight), the offline dry
run `analysis/native_episode_dry_run.py` that every new form passes before a flip.

## 4. Results (every number is paired against the sealed comparator at the roster's own null)

| cell | roster | official SLU-F1 (comp -> arm) | delta, CI95 | intent delta, CI95 | verdict |
| --- | --- | --- | --- | --- | --- |
| CELL-1 (deltas v1r) | Fold A | 63.63 -> 63.15 | -0.48 [-2.18, +1.24] | -0.74 [-2.17, +0.57] | NEUTRAL by width; non-inferiority not proven |
| CELL-1 twin | Fold A | 63.63 -> 63.19 | -0.44 [-1.94, +0.99] | +0.09 | form control |
| CELL-2 (deltas v2, retention) | Fold A | 63.63 -> 64.27 | **+0.64 [-0.76, +1.92]** (non-inferior, unproven) | -0.09 [-1.22, +0.96] (0.23 pp beyond the margin) | NEUTRAL by width |
| CELL-2 twin | Fold A | 63.63 -> 63.68 | +0.05 [-1.52, +1.62] | -0.93 [-2.40, +0.41] | arm minus twin +0.59 / +0.83 |
| CELL-1-GEPA (deltas gepa-v1) | Fold A | 63.63 -> 63.60 | -0.04 [-1.58, +1.39] | -0.09 [-1.54, +1.32] | NEUTRAL by width |
| CELL-1-GEPA twin | Fold A | 63.63 -> 62.87 | -0.76 [-2.39, +0.76] | -0.28 [-1.51, +0.89] | arm minus twin +0.73 / +0.19 |
| CELL-3 (gated v2, fresh roster) | DEV-2000-ADDED | 65.40 -> 63.95 | **-1.44 [-2.88, -0.05]** | 0.00 [-1.01, +1.00] | HARMFUL by the registered rule (SLU guard) |
| CELL-3 twin | DEV-2000-ADDED | 65.40 -> 65.78 | +0.38 [-0.97, +1.75] | 0.00 [-1.21, +1.20] | NEUTRAL; arm minus twin -1.82 SLU: the loss is the store's CONTENT on the fresh roster, not the form |

Against the Stage-2 lock (B5e official 62.34 / 80.09) every Stage-3 arm is significantly higher
(CELL-2 +1.93 SLU [+0.56, +3.34] / +2.04 intent [+0.74, +3.34]); that gain belongs to the locked
v2.0 plan, which every Stage-3 cell must beat.

What the reads and diagnostics established (owner decision 113 wording: state what was gained and
how, never "no gain"):

1. **Content sits above form on both families** (arm minus twin +0.59 / +0.83 for v2, +0.73 /
   +0.19 for GEPA), and **iteration 1 -> 2 moved the arm the right way** (+1.12 SLU, +0.65 intent;
   harm scenarios contracted, winners grew: audio +14.5, weather +9.7 content gains where the
   store has reach). All inside the own-null band.
2. **`general` is a form cost, not a content gap** (`docs/results/2026-09-24-slurp-general-scenario-diagnostic.md`):
   the twin loses as much as the arm on the 60 general rows, no value targets general, harm is
   diffuse, the whole stratum is worth at most 0.56 pp intent on Fold A.
3. **The Fold-A-selected store does not transfer** (`docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md`):
   on the 355 gate-closed rows (byte-identical prompts) CELL-3 reads -2.20 while PLANr reads +0.61
   on the same rows (run-to-run noise at n = 355 is about +-2 pp); the store's attributable part on
   supplied rows is -0.35 pp above its own null, an entity-precision cost (`date` +29 FP behind
   date-bearing slot-contract / reviewer-criterion deltas); harm is diffuse over 120 values; Fold A
   winners average +0.33 on DEV vs Fold A losers +0.99 (sign agreement 49/96); a perfect gate
   reaches only ~PLAN (-0.51 [-1.40, +0.37]). The CELL-3 twin (same gate, deranged values) is NEUTRAL (+0.38),
   so on the fresh roster the content of the Fold-A-selected store is what harms; carrying a supply is not.
4. **The measurement floor is a BETWEEN-flight phenomenon** (ROLL-AA, route F2,
   `docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`): inside ONE flight,
   byte-identical prompts at temperature 0 repeat the delivered answer on 91.5 % of rows and flip
   the delivered INTENT on 0 of 200, giving h_within 0.735 pp SLU and 0.000 pp intent at n = 200;
   across flights the same identity reads +-1.25 pp pooled (n about 1,000) and +-2 pp on 355-row
   splits, and the program's earlier "28 % of raw outputs, 5 % of intents" diffuseness was measured
   across flights, not within one. Consequences: a mechanism flown as its own campaign must target
   >= 2 pp of recoverable mass to be readable, while a variant interleaved per row inside one
   campaign is readable at about 0.4 pp on 625 rows -- so per-row variant interleaving inside one
   campaign is the engineering item that makes the optimisation space searchable (VAR-2).
5. **Engineering assets retained**: the closed loop, the gate mechanism, the fresh-roster own-null
   protocol, the batch driver hardening, the diagnostics, the verdict writer, the label gate.

Owner decisions of 2026-09-24: 108 test read deferred; 110 (gate on DEV-2000-ADDED) ratified after
the flight; **111 the semantic-delta APPLICATION line is closed** (no more gating / pruning /
re-ranking cells over the v1r / v2 / gepa stores); **112 the next route is inference-time sample
aggregation** (offline read first, then Fold A, DEV, test); 113 the record states what was gained
and how; 114 DEV-remainder comparators only after a positive offline read.

## 5. The diagnosis behind the pivot (why the delta line carried no information)

- The rollouts varied only Solver decoding under ONE fixed context; the differences were decoding
  noise, and the "advantage" learned from them ranked noise (no out-of-fold transfer).
- The policy was expressed as advice text appended to node context. In-context learning copies
  format, label space and conventions from DEMONSTRATIONS; abstract instructions barely change
  behaviour. Every advice supply paid a form cost (the twins) for no content effect.
- The reward was sparse (terminal SLU only), with no verifier and no dense per-class proxy.
- The Reviewer node has no evidence to judge with (ACCEPT 98.4 %, five executed revisions per
  1,000 rows): the review loop is not an optimisation space as built.

The owner's directive (2026-09-24, recorded in memory and in this handoff): training-free RL gains
come from rolling out VARIATIONS of prompts, data and content construction over an optimisation
space, scored per variant, with the winners encoded into demonstrations, constraints and selection
rules -- never from running a simple algorithm mechanically and declaring a conclusion.

## 6. The bad-case structure of the locked plan (what the next rollouts must move)

Measured by the bad-case bank (`docs/results/2026-09-24-slurp-plan-bad-case-bank.md`, script
`scripts/analysis/slurp_plan_bad_case_bank.py`, 2,080 typed rows, every number re-derived from the
sealed per-sample scores; ledger row `SAEA-SLURP-PLAN-BAD-CASE-BANK-V1` closed). Fold A / DEV-2000-ADDED.

| class (PLAN) | rows T / D | stable-wrong T / D | SLU headroom pp T / D | intent headroom pp T / D | what it is |
| --- | ---: | ---: | ---: | ---: | --- |
| ENTITY-MIXED (FN and FP on one row) | 193 / 195 | 187 / 190 | +17.4 / +16.5 | 0 | half of all recoverable SLU; never moved by any plan module; dominated by same-type SPAN-BOUNDARY containments (77 of 168 mismatches), only 4 / 168 reachable by any surface normalisation |
| INTENT-UNCOVERED (gold outside Perception's list) | 130 / 169 | 127 / 165 | +5.4 / +6.8 | +12.0 / +16.9 | 68 % / 73 % of intent errors; the delivered wrong intent was itself a candidate 95 % of the time: a CANDIDATE-PROPOSAL failure, not a selection failure |
| ENTITY-FN-ONLY | 84 / 65 | 72 / 60 | +5.1 / +4.0 | 0 | `date` leads (70 / 74); the slot's own contract was supplied on 100 % of date / time FN rows: contract text is exhausted |
| ENTITY-FP-ONLY | 131 / 108 | 120 / 95 | +4.8 / +3.5 | 0 | 41.5 % / 48.4 % of empty-gold rows emit entities; the plan CREATES 58 / 41 FP-ONLY rows from direct-correct rows. CORRECTION 2026-09-24 20:00 UTC: the exemplar pool DOES hold entity-free values (2,949 of 9,354 = 31.5 %); the bank's zero was its parser counting the rendered token `none` as a slot type. What the supply never shows is the Solver contract's own empty ANSWER form (`"entities":[]`); the re-rendered view `train-exemplars-with-empty-v1` tests that one factor |
| INTENT-COVERED (gold in the list, wrong pick) | 61 / 63 | 57 / 60 | +2.4 / +2.7 | +5.7 / +6.3 | selection among candidates |
| ALL-BAD | 600 / 602 | 563 / 571 | +36.4 / +34.6 | +17.8 / +23.4 | -- |

Stability: only 7.2 % / 6.6 % of rows flip between PLAN and PLANr at row level; the bad mass is
STABLE and therefore a real optimisation target. Direct -> PLAN: +151 / +165 net repairs, but
ENTITY-MIXED (82 / 92), FN-ONLY (61 / 37) and FP-ONLY (24 / 17) rows sit untouched.

Gold-free runtime signatures (what a policy can key on): the supplied exemplars' intent agreement
with candidate 1 falls from 0.70 to 0.20 (Fold A; 0.75 -> 0.21 DEV) on INTENT-UNCOVERED rows -- a
directly gateable trigger for broader candidate construction; far-field +11 / +13 pp on the
entity classes; Planner REVISE +6.9 pp; the deliver-normaliser changing the answer +10 pp on
MIXED. Three plan constants separate nothing (20 exemplars, 0 entity-free exemplars, no
compaction).

Consequences for the rollout design: (1) candidate PROPOSAL (Perception K, neighbour-intent union,
exemplar-intent agreement as the trigger) carries all the intent headroom; (2) the empty-answer FORM of the entity-free demonstrations (rendered `none`, never the contract's `"entities":[]`) is a one-factor construction lever against the +4 pp FP-ONLY headroom; (3) span-boundary
resolution (ENTITY-MIXED) is the largest SLU mass and needs demonstrations of boundary
conventions and sample-level consensus (aggregation), not contracts or normalisers; (4) the
greedy diffuseness lever is real but bounded (row-level flips 7 %).

## 7. The comprehensive experiment plan from here and the fast-validation routes (Stage 3, revised 2026-09-24)

### 7.1 The three policy layers

Every layer is learned by rolling out CONSTRUCTION VARIANTS per row (same node, K variants, within
one flight, paired per row), scored by dense per-class proxies (entity F1 by slot type, candidate
coverage, intent exact), aggregated by group-relative advantage per runtime-observable state, and
validated out of fold.

**Layer 1: demonstrations (data).** Actions: source (TRAIN gold exemplars vs the core's own
gold-verified rollout outputs = bootstrapped demonstrations), k in {5, 8, 12}, selection (speech
neighbours / candidate-intent aligned / slot-type matched / empty-entity share / channel matched),
rendering (raw-line conventions vs structured). Reward: entity F1 by type, FP mass. State keys:
predicted scenario, candidate margin, exemplar-intent agreement, channel, duration.
**Layer 2: constraints (content / contracts).** Per-intent legal slot-type schema at the delivery
node (llama.cpp grammar / json_schema; deterministic, zero tokens), slot-contract rendering,
date / time serialisation rules, the "no entity" rule. Reward: type-swap and illegal-type mass.
**Layer 3: selection (inference-time RL).** Disagreement-triggered adaptive sampling (N = 5 only
where the first two samples disagree), deterministic verifiers (legal intent inventory, intent ->
legal slot types, date / time validators), majority / support commit delivering a medoid sample
(invariant I7: the delivered text is a model response), a Reviewer fed with evidence.

### 7.2 Evaluation methodology

(a) An A/A null inside one flight (the identical prompt twice) measures the within-flight paired
noise, expected far below the +-1.25 pp cross-flight band; every variant rollout at n = 200 is read
against that within-flight margin. (b) Search on small batches (200 construction rows, K variants
per row, paired), confirm at full scale (Fold A 1,080 at the own null, then DEV-2000-ADDED at its
own null). (c) Select variants on DEV-remainder rows, validate on Fold A / B, claim on the one test
read (decision 108). A route is worth a flight only when it names the bad class it moves, its
recoverable upper bound from the bad-case bank is >= 2 pp on the target roster, its first read fits
in one day, and it costs <= 4 GPU-hours before that read.

### 7.3 The fast-validation routes (ordered by information per GPU-hour; status and result refreshed in place)

| # | route | target bad class | first read | GPU-h to first read | status | key conclusion |
| --- | --- | --- | --- | ---: | --- | --- |
| F0 | Bad-case bank of the locked plan | all | zero-contact script over the sealed arms | 0 | DONE (`docs/results/2026-09-24-slurp-plan-bad-case-bank.md`) | intent errors are candidate-PROPOSAL failures with a gold-free trigger (exemplar-intent agreement 0.70 -> 0.20); ENTITY-MIXED = half the SLU headroom, span boundaries; 0 entity-free exemplars in the pool (+4 pp FP headroom); contract text and surface normalisation exhausted |
| F1 | Offline sample aggregation over ROLL-1's five sealed samples (all temperature 0.7) | greedy diffuseness; entity FP | zero-contact script (`docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md`) | 0 | DONE | no I7-compatible rule beats one sample (medoid +0.03 [-0.63, +0.71]); the support-filter editing rule at s = 3 reads +1.40 [+0.55, +2.29] but only on the 400 agreeing rows and mostly as FP suppression on the 191 no-gold-entity rows, at 2.09x contacts; oracle best-of-5 +6.55 (+12.55 on disagreeing rows) = the verifier headroom no rule reaches |
| F2 | Within-flight A/A null: the identical PLAN prompt twice per row inside one flight, 200 R01C rows, greedy | measurement floor | per-row paired delta distribution | 0.5 (flown) | DONE (`docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`) | **h_within 0.735 pp SLU / 0.000 pp intent at n = 200**; 91.5 % byte-identical, 0 intent flips, 15 entity-set flips; the +-1.25 pp band is between-flight, so within-flight interleaving buys about 3x the power (VAR-2 engineering item) |
| F3 | VAR-1 construction-variant family on R01C (625 rows, full plan): PLAN, PLANr (the R01C cross-flight own null), exemplars k 10 / k 30 / intent-diversified (c 4), Perception k 16 with 5 candidates; paired per row, reads = per-row variant table, entity FP / FN by slot type, Perception candidate coverage, advantage per state | entity FN / FP, same-type distance, intent coverage | six campaigns in one chain, flight commit `3ade29ff`, receipt `slurp-stage3-var1-admission-v1` | ~6.5 | FLYING since 2026-09-24 23:48 UTC (SAEA-Batch-Chain-VAR1) | EX-DIV also lowers the demonstration count (EX-K10 is its count-only control); the variant driver (FP / FN by type, coverage, advantage) must land before the variant reads (VAR1-OPEN-1 / 2) |
| F4 | Candidate-proposal rollout: Perception K / neighbour-intent union / exemplar-intent-agreement-triggered broadening; the coverage read comes free from every VAR-1 flight's Perception receipts | INTENT-UNCOVERED (+12 / +17 pp intent headroom) | gold-in-candidates coverage per variant per state | (in F3, then ~1) | DESIGN after VAR-1's coverage read | -- |
| F5 | Per-intent legal slot-type constraint at the delivery node (llama.cpp json_schema / grammar): offline mass count first, then a four-row smoke and a Fold A cell | type swap (4.7 %), illegal types, part of FP | offline count, then the admission rule | 0, then ~2 | DESIGN | -- |
| F6 | Bootstrapped demonstrations: the core's own gold-verified rollout outputs rendered as exemplars in its own output format, retrieved by speech key (DSPy-style bootstrap, ExpeL-style successful trajectories) | conventions, entity FN / FP | inside F3 as a source variant | (in F3) | DESIGN | -- |
| F7 | AGG-1 inference-time selection cell as framed (adaptive N + medoid commit) | greedy diffuseness | -- | -- | CLOSED by F1 (nil at 1x-equivalent rules; the FP mass is pursued at 1x through F10) | the open question left is the +6.5 pp oracle gap: a SELECTION probe (one contact per row shown the five sealed samples, asked to pick; 625 rows, ~0.3 GPU-h) would say whether the core can verify better than it generates -- queued after VAR-1 as F11 |
| F8 | Reviewer with evidence: sample disagreement, per-entity support counts and checker results instead of one draft | review loop inert (ACCEPT 98.4 %) | inside F7's form | (in F7) | DESIGN | -- |
| F10 | Empty-answer demonstrations: the exemplar view re-rendered so entity-free lines end in the Solver contract's exact empty form (`train-exemplars-with-empty-v1`, released, content hash `e3998525...`; the pool already held 31.5 % entity-free values, the bank's zero was a parser artefact) | ENTITY-FP-ONLY (+4.8 / +3.5 pp SLU headroom) | one ~1 GPU-h variant flight; legal on Fold A / DEV, needs a minus-r01 sibling for R01C | ~1 | RELEASED; cell to register (Fold A vs PLAN or a VAR-1 sibling after the minus-r01 build) | -- |
| F12 | VAR-2 per-row supply-variant interleaving inside ONE campaign | all construction levers; about 3x the power of VAR-1's design | mechanism MERGED (`578a76b2`): `native_episode.roles.solver.supply_variants` with K arms (2-8), the delivering arm last and override-free so invariant I7 needs no exception, K per-arm routers, per-arm sealed custody and `validate_supply_variant_receipt`, 26 named refusals, new program `phase-native-candidates-review-revise-variants4-v1` (ceiling 17), existing forms byte-identical (70 tests) | 0 so far, then ~1.5 | MECHANISM DONE; cell to register | **A Perception-k arm is impossible**: the first phase's supply is seeded once into the row's single QueryState before the flight, so it cannot differ between arms of one row. Exemplar / slot-contract knobs vary per arm at the Solver. Before any VAR-2 number is reported, `core/bundle/outputs.py` must learn `supply_variants` (invariant I7g reads `solver_group` only) |
| F11 | VERIFY-1 verifier-selection probe: one contact per R01C row carrying the row's SPEECH plus its five sealed ROLL-1 samples, asked to pick the best; read = choice distribution / position bias, oracle agreement, SLU of the chosen sample vs the single-sample mean / medoid / oracle | the +6.5 pp oracle gap (+12.5 pp on the score-disagreeing rows) | 625 contacts + a four-row smoke | ~0.3 | REGISTERING with one authorised harness change (branch `fable/verify1b`) | Two material routes exist and neither fits: the construction route is text-only by the D2 freeze, the speech-carrying `sealed-manifest` route renders only the row's delivered answer. Ruling: add an opt-in `sealed-samples-manifest` binding (existing cells byte-identical). Population ruling: **420 of 625 rows render >= 2 distinct answers** (the informative population); the 205 single-answer rows are a built-in POSITION-BIAS control. The registry record `inference-time-verification-v1` (scoring, selection) is merged |
| F9 | Contract / instruction search (GEPA-style on the task contract: date / time serialisation, "no entity" rule, per-type convention line), selected on DEV-remainder rows, validated on Fold A / B | date / time FN, empty-gold FP | small-batch paired search, then a cell | ~2 | LATER (after F3 / F5) | -- |

Closed routes (do not reopen): the semantic-delta APPLICATION line (gating / pruning / re-ranking
over the v1r / v2 / gepa stores, owner decision 111); a `general`-targeted mechanism (form cost,
upper bound 0.56 pp intent); entity-FP suppression by filtering deltas (<= 0.12 pp).

### 7.4 Sequence and cost (GPU-hours on the resident session)

| step | what | cost | read |
| --- | --- | --- | --- |
| 0 (now, zero GPU) | F0 bad-case bank; F1 offline aggregation read | 0 | `docs/results/2026-09-24-slurp-plan-bad-case-bank.md`, `docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md` |
| 1 | F2 A/A null (200 rows) -> h_within | ~0.4 | within-flight margin |
| 2 | F3 ROLL-2-VARIANTS on R01C and F4 Perception coverage rollout on Fold A | ~1.5 + ~1 | per-row paired variant tables, advantage per state |
| 3 | policy tables (layers 1 + 2, incl. F5 if its offline count clears 1 pp) -> CELL-4 on Fold A vs PLAN at the own null, four-row smoke first | ~2 | admission rule |
| 4 | CELL-4 replicate on DEV-2000-ADDED at its sealed own null | ~2 | fresh-roster admission |
| 5 | F7 AGG-1 (if F1 clears +1.5 pp): Fold A, then DEV | ~3.5 + 3.5 | admission rule |
| 6 | the one-shot test read (decision 108) only after a fresh-roster gain | ~21 (13,078 rows) | the claim beside the published SLURP ladder |

Fallback (decision 112-B): a core swap study if the construction-variant and aggregation lines are
both negative on the fresh roster. Every result rewrites the "status" and "key conclusion" cells
above and the conclusions of sections 4 and 6; nothing is appended as a log.

## 8. Open items and hazards a collaborator must know

- CELL-3 is fully read and closed (verdict `docs/results/2026-09-24-slurp-stage3-delta-cell-r03-gate-verdict.md`,
  commit `5f52262a`); the GPU is idle until route F2 is registered, minted and flipped.
- DEV-2000-ADDED has no gold per-scenario labels per row; per-scenario tables there use the
  predicted majority scenario (stated as such).
- `plan_cell_read.py` reads Fold A cells only (TRAIN scorer siblings); DEV cells use
  `slurp_paired_roster_read.py`.
- Greedy decoding is not bitwise reproducible across batch compositions: never compare across
  flights without the own null; prefer within-flight paired variants for search.
- The GPU falls into a cold state (~7 W, ~10 TFLOP/s) within a minute of a sealed campaign; the
  driver now warms before every step (`gpu_warm.sh`); the Legion SmartFanMode must be 3.
- Untracked files count as dirt for `core.flight.cli check`; sibling flips invalidate each other;
  converge every cell's re-pin loop at one HEAD before countersigning
  (`docs/readiness/...`, memory `flip-convergence-untracked-files`).
- Paid API spend stays 0; no transcript tokens; no gold at runtime; test split unread.

## 9. Where things live

- Decisions: `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`.
- Specs: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`,
  `docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md`,
  `docs/readiness/2026-09-24-slurp-stage3-scenario-gate-design-v1.md`.
- Verdicts and reads: `docs/results/2026-09-2{3,4}-slurp-stage3-*`, results ledger
  `docs/results/stage2-results-ledger.md`, exposure ledger `docs/exposure-ledger.md`.
- Sealed bytes: `$SPEECHRL_DATA_DIR/runs/<run id>/<attempt>/`; analyses
  `$SPEECHRL_DATA_DIR/analysis/<root>/`; stores `$SPEECHRL_DATA_DIR/knowledge/slurp/semantic/`.
- This document is the single living Stage-3 handoff; section 7.3 is the fast-validation board.
