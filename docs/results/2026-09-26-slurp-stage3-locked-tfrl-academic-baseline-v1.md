# The locked training-free RL families on this rig: an academic baseline

Written 2026-09-26 by the Stage-3 baseline-report agent (worktree `/home/chao/saea-worktrees/fable-baseline`,
branch `fable/baseline`). **Model-free**: zero model, tokenizer, encoder, ASR, embedder, scorer, server,
network, GPU and paid-API contacts were made to write it. Every number below is read from a record that was
already sealed and closed; no ledger row is opened or amended here, no cell is admitted, no flight is
authorised and no mechanism is promoted.

Labels, identifiers, counts, scores and hashes only. No utterance text, transcript, delivered text, gold
filler, predicted filler or statement content appears anywhere. Every figure is a **development** number on a
TRAIN construction fold or a DEV roster (owner decisions 28 and 86) and is never a test claim, a superiority
claim, a generalisation claim or a paper-scale claim.

Where this report and `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` touch the same
question, the instrument wins, and this report states the instrument's reading rather than the superseded one.

---

## 1. The rig and the object of optimisation

### 1.1 The frozen core and the service boundary

| item | value | source |
| --- | --- | --- |
| core | Qwen3-Omni-30B-A3B-Instruct, GGUF **Q4_K_M**, decoder-only (no `mmproj` on these cells) | `docs/exposure-ledger.md`, the `SAEA-SLURP-STAGE3-*` rows |
| engine | llama.cpp `llama-server`, the pinned local featcache checkout at commit `04ccc72a2207347ca76161b93fd9d846dd0a8675` | `docs/readiness/2026-08-21-speech-native-agent-loop-training-free-rl-plan.md` |
| device | one RTX 5090 **Laptop** GPU | `docs/readiness/2026-08-11-w3-w4-decode-recovery-plan.md` |
| serving geometry | `np4` x 24,576-token slots (98,304 total), 512 completion tokens, resident session `serving-slurp-native-candidate-five-train-a-np4-v1`, attached by every cell and never spawned or stopped by it | `docs/results/2026-09-22-slurp-v2-lock-v1.md` section 2 |
| access | across an API-shaped service boundary; **zero parameter updates**, no task-trained model, no second answering LLM | study `CLAUDE.md`, research boundary |

Nothing in any family below changes a weight, a tokenizer, a sampler implementation or a serving parameter.
The only things any of them changes are (a) the text a node is shown and (b) which of the episode's own
products is delivered.

### 1.2 The four-node plan that is the policy

The locked SLURP base v2.0 (`docs/results/2026-09-22-slurp-v2-lock-v1.md`;
`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json` at flight commit `e367a629`) is the policy
every Stage-3 cell is one factor on:

- **Perception -> Solver -> Reviewer x3 -> Planner**, `max_revisions` 1, `review_loop` on;
- M1 speech-keyed TRAIN exemplar supply at k = 20 (`train-exemplars`), M4b slot-contract cards v2, M3
  delivery normaliser v3 (`saea-deliver-normalise-v3`), the Reviewer's native toolkit RETIRED (`phase_tools`
  absent);
- failure-mode declarations: E13 `deliver-latest-or-abstain`, E22 `continue-without-answer`, E20
  `compact-or-abstain`;
- cost of the locked base: **4.1 contacts per row**, about **8,350 prefilled tokens per row**, **1.66-1.76
  GPU-h per 1,080 rows** at np4.

The bare-core comparator on every carrier is the `phase-direct-only-v1` program: one contact, no Perception,
no exemplar supply, no slot contracts, no review loop (`docs/results/2026-09-22-base-lock-v3.md` section 2).

### 1.3 Carrier, metric and rosters

The carrier is SLURP. The paper-facing number is the **official `evaluate.py` at commit
`8eb16545762be97ace75334109d73824217311f1`**, run once per complete manifest through `core.scoring_batch`,
reported as **pooled (micro) SLU-F1** with **intent accuracy** (joint `scenario_action_exact`) beside it.
Every contrast below is a paired row bootstrap, 10,000 draws, seed 20260915, clustered by utterance.

| roster | rows | split role | split identity | used for |
| --- | ---: | --- | --- | --- |
| TRAIN Fold A (`SLURP-EVO-FOLD-A-V2`) | 1,080 | discovery | `61b0f0625497` | the locked PLAN comparator and every iteration-1/2 delta cell |
| R01C construction (`SLURP-STAGE3-CONSTRUCTION-R01C`) | 625 | discovery | `f56bc386776421ae...` | the rollout, the advantage and reflection contacts, VAR-1, VERIFY-1 |
| DEV-2000-ADDED | 1,000 | dev | `ee6c43cd4dd8` | the fresh-roster reads (B6, CELL-3) |

The SLURP test split is closed (owner decisions 28, 86); no number here is a test number.

### 1.4 The Stage-2 result that is the thing to beat

Cell B6 (`docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`) is the system-level
advantage the Stage-3 families have to improve on, read on the **fresh** DEV-2000-ADDED roster:

| metric | bare core (`SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1`) | the system (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`) | delta | CI95 |
| --- | ---: | ---: | ---: | --- |
| official pooled SLU-F1 | 38.09 | **65.40** | **+27.30** | **[+24.05, +30.50]** |
| intent (scenario+action) | 61.70 | **76.60** | **+14.90** | **[+11.78, +18.03]** |

Its request-identical replicate `...-REPLICATE-V1` reads **65.15 / 76.80**. The cost of the advantage is 4.07
contacts per row and 1.655 GPU-h per 1,000 rows against the core's 1 contact and 0.087 GPU-h -- about 19x the
GPU time.

**This is the baseline's centre of gravity.** A 27.30 pp system-over-core advantage was built by *structure*
-- observation, organisation, supply and use as separate nodes -- with no learning at all. Everything in
sections 3 and 4 is an attempt to add a *learned* increment on top of that structure, and the largest effect
any of them produced is under 1 pp.

---

## 2. What "training-free RL" means on a frozen core

A reinforcement-learning loop is usually defined by what the update touches: parameters. On this rig the
parameters are unreachable by construction -- the core is a frozen GGUF behind a service boundary, and
zero-parameter training is a boundary condition of the study, not a design choice.

So the policy that can change here is exactly two things, and it is worth saying once, precisely:

> **The CONTEXT and the COMMIT.** The *context* is what each of the four nodes is shown before it generates:
> its instruction text, the exemplars, the slot contracts, the candidate list, any learned statements
> appended to it. The *commit* is which of the episode's own products is delivered: which of N Solver
> samples, edited how, under which registered commit policy. Nothing else is writable. A "training-free RL
> algorithm" on this rig is therefore a rule for editing one of those two objects from experience, and its
> rollout, scoring, credit-assignment, update and selection operators all terminate in one of those two
> writes.

That vocabulary is the registry's own, not a gloss invented here. Owner decision 101 requires every Stage-3
cell to carry a `stage3_algorithm` label whose id resolves in `core.base.STAGE3_ALGORITHMS`, and
`src/speech_aware_evidence_acquisition/core/stage3_algorithms.py` defines the operator vocabulary as
`rollout`, `scoring`, `credit_assignment`, `update`, `selection` and `context_application` -- the sixth added
precisely because on a frozen core "the policy update" and "the moment that update reaches a row's context"
are separable acts.

The re-statement matters because the published families were all specified against loops where a candidate
update is *evaluated by re-running the task and reading the score*. On this rig that evaluation step is the
expensive one and, as section 5 shows, the noisy one. Each family below is therefore reported twice: as the
published method, and as the thing this rig could actually build.

---

## 3. The families

### 3.1 Training-Free GRPO (group-relative semantic advantage)

**Registry record.** `tfgrpo-semantic-advantage-v1`, family `training-free-grpo`, citation
**`arXiv:2510.08191`**, status `base-loop`, operators `rollout` + `scoring` + `credit_assignment` + `update`
+ `context_application`.

**The published method, in three sentences.** Sample a group of trajectories for the same input and score
them; then, instead of turning the group-relative advantage into a gradient, have the model *state in words*
what distinguished the better members of the group from the worse. Those natural-language statements are an
experiential update: they accumulate in a store and are prepended to the context on later rows. The
parameters never move, and the group-relative comparison plays the role the advantage term plays in GRPO.

**How it was implemented here.** Faithfully in shape:

1. **ROLL-1** (`SAEA-SLURP-STAGE3-ROLLOUT-R01-V1`) is the group: the locked plan with
   `native_episode.roles.solver.samples = 5`, `decoding_overrides {temperature 0.7, seed_offset 0}`, the
   delivery normaliser removed (a grouped Solver forbids it, I7n), commit policy
   `saea-commit-plurality-support-v1` at `min_support 3` -- 625 R01C rows, **5,344 sealed role contacts =
   8.5504 per row** (`docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md` section 7).
2. **S3-3** scores every sample per row with the official scorer on copies
   (`SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1`).
3. **ADV-1** (`SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1`) is the credit-assignment contact: one contact per row on
   the **225 rows whose five samples differ in score**, 225/225 legal statement sets, 396 blocks, node
   attribution perception 124 / solver 159 / reviewer 99 / planner 14, about 0.07 GPU-h
   (`docs/results/2026-09-23-slurp-stage3-advantage-r01-read.md`).
4. **S3-5** curates those blocks into the released store `stage3-deltas-v1r` (379 node-targeted values) and
   **CELL-1** applies them: Solver 8 / Reviewer 4 / Planner 4 candidate-bound, Perception unconditional 4.

**Where the implementation necessarily departs.** Three departures, all forced by the rig and all material:

- **The group is a Solver group, not an episode group.** The published loop compares whole trajectories. Here
  only the Solver is sampled N times; Perception, Reviewer and Planner are visited once (3.1504 non-Solver
  contacts per row, invariant in N). The advantage statement therefore describes a *Solver* difference even
  when the model attributes it elsewhere -- and it did, for more than half the blocks (perception 124 +
  reviewer 99 + planner 14 of 396).
- **The update is a store, not a prompt rewrite.** The statements are appended to a provenance-tagged store
  and supplied per row by candidate-bound routing, because the plan's prompts are hash-pinned artefacts.
  That makes the update auditable and makes *reach* a variable the published method does not have: on CELL-1
  the Planner route reached 59.4 % of rows; on CELL-2, 18.3 %.
- **Credit is assigned only where the group disagreed** -- 225 of 625 rows. On the other 400 the five samples
  score identically, so the group-relative signal is empty by construction.

**What was flown, and what it measured.**

| cell | run id | roster | contacts | GPU-h | official SLU | intent |
| --- | --- | ---: | ---: | ---: | --- | --- |
| CELL-1 (store v1r, 379 values) | `SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1` | TRAIN Fold A 1,080 | 4,553 (4.216/row) | 1.8021 / 1,080 | 63.15 vs 63.63, **-0.48 [-2.18, +1.24]** | 81.48 vs 82.22, -0.74 [-2.17, +0.57] |
| CELL-1 twin (derangement) | `SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-V1` | TRAIN Fold A 1,080 | 4.142/row | 1.7879 / 1,080 | 63.19, -0.44 [-1.94, +0.99] | 82.31, +0.09 [-1.19, +1.30] |
| CELL-2 (store v2, the 200 values decision 83 retained) | `SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1` | TRAIN Fold A 1,080 | 4,483 (4.151/row) | 1.7679 / 1,080 | 64.27, **+0.64 [-0.76, +1.92]** | 82.13, -0.09 [-1.22, +0.96] |
| CELL-2 twin | `SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-V1` | TRAIN Fold A 1,080 | 4.080/row | 1.7120 / 1,080 | 63.68, +0.05 [-1.53, +1.51] | 81.30, -0.93 [-2.40, +0.41] |
| CELL-3 (v2 behind a scenario gate) | `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1` | DEV-2000-ADDED 1,000 | -- | -- | 63.95 vs 65.40, **-1.44 [-2.88, -0.05]** | 76.60, 0.00 [-1.01, +1.00] |
| CELL-3 twin | `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-V1` | DEV-2000-ADDED 1,000 | -- | -- | 65.78, +0.38 [-0.97, +1.75] | 76.60, 0.00 [-1.21, +1.20] |
| CELL-3's own null, in chain | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1` | DEV-2000-ADDED 1,000 | 4,090 | 1.649 | 65.15, -0.25 [-1.52, +0.98] | 76.80, +0.20 [-0.99, +1.31] |

The **derangement twin** is the family's form control: the same store, the same token volume, the same supply
shape, each value re-attached to a facet set that is not its own (a genuine form control on 363 of 379
values, 95.8 %). Arm minus twin -- descriptive, never a test -- is **-0.04 pp** (CELL-1), **+0.59 pp**
(CELL-2) and **-1.82 pp** (CELL-3).

**Measurement design and its floor.** CELL-1 and CELL-2 are cross-flight contrasts against a comparator
sealed in an earlier chain, **with no in-chain A/A replicate**. Under the instrument's rule 4 that design
supports **no verdict in either direction**: the bar for a cross-flight read at n = 1,080 is about 2.5 pp and
the unmeasured flight offset is of the same order as the whole effect. CELL-3 is the one delta cell that
*did* fly its own null in chain; its offset is -0.25 with half-width 1.2525, so its -1.44 does **not** exceed
the offset bound and the honest reading is **"not distinguishable from flight variance"**, not HARMFUL. Owner
decision 111 (close the semantic-delta application line) stands independently, on the absence of a
demonstrated benefit across four cells rather than on that single loss.

**Named failure mode: CREDIT FROM DECODING NOISE.** The advantage statement is fitted to a per-row difference
between samples drawn from one fixed context at temperature 0.7. The fresh-roster diagnostic
(`docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md` section 2a) measures the consequence:
of 86 Fold A winner values, 37 are negative out of fold, their mean per-row SLU delta on DEV-2000-ADDED is
**+0.33 pp against the 26 Fold A losers' +0.99 pp**, and **sign agreement across the two venues is 49 of
96** -- a coin toss. The per-value ranking the update is built from is noise.

### 3.2 GEPA (reflective Pareto evolution of the context)

**Registry record.** `gepa-reflective-pareto-v1`, family `gepa`, citation **`arXiv:2507.19457`**, status
`planned`, operators `credit_assignment` + `update` + `selection` + `context_application`.

**The published method, in three sentences.** Instead of a scalar advantage, mutate the instruction/context
*text* by having the model reflect on execution traces in natural language and propose a revision. Keep a
population of candidates and select survivors by a **Pareto frontier over per-instance scores** rather than
by the best average, so a candidate that wins on a minority of instances is not discarded. Iterate: reflect,
mutate, select.

**How it was implemented here.** One reflective contact per **(scenario, node) group**
(`docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/README.md`):

| item | value |
| --- | --- |
| run id | `SAEA-SLURP-STAGE3-GEPA-R01-V1` |
| groups = contacts | **68** (17 scenarios x 4 nodes; `music` has no eligible row) |
| distinct R01C rows whose trajectory and construction gold is shown | **173** (of ADV-1's own 225) |
| rows per group | 12 (44 groups), 11 (8), 10 (4), 6 (4), 2 (4), 1 (4) |
| rendered prompt size | min 2,477 / median 13,309 / max 16,281 characters |
| GPU-h ceiling (point estimate about 0.2) | 1.0 |
| release | `stage3-deltas-gepa-v1`: 248 values curated by the decision-83 frontier rule **plus** the 200 iteration-1 values decision 83 retained = **448** |

Each contact is shown that scenario's worst- and best-outcome ROLL-1 rows (disjoint halves of the ranked
list, at most 6 each) together with the node's *current released statements* for that scenario, and is asked
to revise and extend them.

**Where the implementation necessarily departs.** GEPA's selection operator is decision 83's per-scenario x
frontier retention rule, which was already in place -- so **this arm changes what is proposed, not how the
frontier is read**, and it is a single generation of evolution, not a population iterated to convergence.
The Pareto frontier is over *scenarios*, not over a held-out instance set, because a held-out set would
require a second flight. And the mutated text does not replace a prompt: it is released into the same
`stage3-deltas` store and supplied by the same `context_supply` route as CELL-1, so GEPA and Training-Free
GRPO differ **only** in the store they release
(`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`, "The GEPA and ACE arms").

**What was flown, and what it measured.**

| cell | run id | contacts | GPU-h / 1,080 | official SLU | intent |
| --- | --- | ---: | ---: | --- | --- |
| CELL-1-GEPA | `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1` | 4,508 (4.174/row) | 1.8628 | 63.60 vs 63.63, **-0.04 [-1.58, +1.39]** | 82.13 vs 82.22, -0.09 [-1.54, +1.32] |
| its twin | `SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-V1` | 4.137/row | 1.8912 | 62.87, -0.76 [-2.39, +0.76] | 81.94, -0.28 [-1.51, +0.89] |

Arm minus twin is **+0.73 pp SLU / +0.19 pp intent** (descriptive). Reach is far fuller than the v2 store's
-- 299 of 448 values supplied, Solver 93 % / Reviewer 91 % / Planner 90 % of rows against 68 / 64 / 18 % --
at prefilled tokens +14 % and GPU-h +6 %, and it buys no pooled effect.

**Measurement design and its floor.** Identical to CELL-1's: cross-flight against the sealed PLAN arm with
**no in-chain replicate**, so under rule 4 the -0.04 supports no verdict either way. Its intervals are wider
than CELL-2's.

**Named failure mode: PROSE-AS-POLICY.** Two families with genuinely different authoring mechanisms -- a
per-row advantage statement and a per-group reflective proposal -- produce the *same* per-scenario shape:
strata the store covers gain (audio +7.0, weather +7.8, datetime +4.7, iot +3.7), strata it does not cover
pay a cost (general -9.4, news -6.3, social -4.4, music -4.2), and the pool nets to zero. What is being
measured is largely the cost of carrying more prose, not the content of the prose. Section 5 argues this from
the twin.

### 3.3 Best-of-N / self-consistency with a verifier

**Registry record.** `inference-time-verification-v1`, family `test-time-scaling`, status `planned`,
operators `scoring` + `selection`; the citation the registry records is "self-consistency / best-of-N with a
verifier; see `docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md`".

**The published method, in two sentences.** Draw N samples for the same input and deliver the one the group
agrees on (self-consistency) or the one a verifier prefers (best-of-N with a verifier), spending inference
compute instead of training compute. The update is not persistent at all: nothing is learned between rows,
and the policy improvement happens inside a single episode.

**How it was implemented here -- the one family whose implementation does not have to depart.** Because
ROLL-1 sealed all five samples per row with full custody (invariant I7g: every raw sample's response bytes
are in the trace under that sample's contact id, the commit policy resolves in `core.base.COMMIT_POLICIES`
and is deterministic, and re-running it reproduces the delivered bytes -- re-derived on 625 of 625 rows), the
whole rule space can be evaluated **offline over the sealed bytes at zero GPU**. Two studies exist.

**(a) The offline rule study** (`docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md`), 625 R01C
rows, **zero model contacts** (seven scorer-on-copies runs only). Deltas against R0-mean-single:

| rule | I7 status | pooled SLU-F1 | dSLU | CI95 |
| --- | --- | ---: | ---: | --- |
| R1-medoid (deliver the group medoid verbatim) | verbatim | 57.91 | **+0.03** | [-0.63, +0.71] |
| R2-intent-plurality-medoid | verbatim | 57.84 | **-0.04** | [-0.71, +0.65] |
| R3-support-3-of-5 (medoid, then drop entities supported by fewer than 3 samples) | edited (I7g) | 59.28 | **+1.40** | **[+0.55, +2.29]** |
| PS-registered-support-3 (*the policy ROLL-1 already flew*) | edited (I7g) | 59.50 | **+1.62** | **[+0.77, +2.51]** |
| PS-registered-support-2 | edited (I7g) | 56.76 | -1.12 | [-1.94, -0.28] |
| R3-support-4-of-5 | edited (I7g) | 58.94 | +1.06 | [-0.07, +2.21] |
| **ORACLE best-of-5** | verbatim, upper bound only | 64.43 | **+6.55** | [+5.56, +7.56] |

Two findings decide the family. First, **selection buys nothing**: no rule that delivers one of the five
samples verbatim clears zero. Second, and sharper: **on the 225 rows where the samples actually disagree --
the rows the operator exists for -- not one rule's CI95 excludes zero**, while the oracle shows +12.55 pp
[+10.99, +14.15] of headroom there. The entire measured gain of the editing rules lives on the *agreeing*
rows and is pure pooled false-positive suppression: FP mass -16.2 % (144.3 units) for FN +1.4 % (9.7 units),
with 191 of 625 rows (30.6 %) carrying no gold entity at all. The operator is therefore not a "pick the
better sample" operator; it is an **entity-abstention rule that uses sample disagreement as its abstention
signal**. Cost of the N=5 grouped Solver: 8.5504 contacts per row = **2.09x** the locked plan's 4.1.

**(b) The live self-selection arm VERIFY-1**
(`docs/results/2026-09-25-slurp-verify1-complete-evidence.md`), run id
`SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-V1`, **625 contacts (1.00 per row)**, 0.08165 monitored active
generation GPU-h, 625/625 rows, every choice parsed, no malformed placeholder selected. Here the frozen core
itself reads a row's five candidate answers and names one:

| quantity | value | CI95 |
| --- | ---: | --- |
| chosen, official pooled SLU-F1 | 58.5816 | -- |
| chosen minus mean-single | **+0.7009** | [-0.2551, +1.6507] |
| chosen minus medoid | +0.6751 | [-0.3923, +1.7348] |
| chosen minus mean-single, **intent** | **+0.5440** | **[+0.0320, +1.0880]** |
| `row_f1_oracle` (label-informed, not a runtime policy) | 64.4664 | -- |
| `utility_oracle` (label-informed, not a runtime policy) | 66.6360 | -- |

The primary SLU benefit gate fails; the registered operational non-inferiority guard on intent passes, and
**that intent interval excluding zero is, with the entity support filter, one of only two effects in the
whole Stage-3 record that clears its own design's floor** (instrument section 4). All 205 identical-answer
rows chose position 1 -- compatible with deterministic tie-breaking, and no causal position claim is made.
The root decision on the record is explicit: do not promote the selector, do not enlarge sampling, close
VERIFY-1 as *benefit not proven*, not as proof that verification is ineffective.

**Measurement design and its floor.** Both reads are over **one sealed sample pool**, so no flight offset
enters and the floor is **h_offline about 0.67 pp at n = 625** -- the smallest floor this program has. These
are the program's most trustworthy numbers for exactly that reason.

**Named failure mode: NO VERIFIER IN THE LOOP.** Not a failure of this family but of the other two, and
visible from here: the published TF-GRPO and GEPA loops use the terminal score only to *select updates
offline*; neither ever lets the running system compare its own candidate outputs at delivery time. That is
the one place in this record where a non-noise signal appeared, and the oracle's +6.55 pp (all rows) /
+12.55 pp (disagreeing rows) says the headroom there is real and largely unreached.

### 3.4 ACE (agentic context engineering: generator / reflector / curator) -- registered, never flown

**Registry record.** `ace-grow-refine-v1`, family `ace`, status **`planned`**, operators `update` +
`selection` + `context_application`. The registry is explicit that **no identifier is recorded anywhere in
this repository for ACE**, so its citation is the design spec's own section rather than an arXiv id that
would have to be invented: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`, section
"The GEPA and ACE arms".

**The published method, in two sentences.** A generator produces trajectories, a reflector extracts lessons
from them, and a **curator** turns those lessons into *incremental delta items* over an evolving playbook --
growing the store by appended items and refining it by de-duplication, **never by rewriting a whole view**.
The claim is that incremental grow-and-refine avoids the context collapse whole-view rewriting causes.

**What exists here.** The record and nothing else. `ace-grow-refine-v1` is registered in
`src/speech_aware_evidence_acquisition/core/stage3_algorithms.py`; a grep of `configs/experiment/*.json`
finds the label on **zero** fragments (the labels in use are `tfgrpo-system-memory-disjoint-v1` 46,
`shared-rollout` 41, `tfgrpo-semantic-advantage-v1` 10, `none` 6, `inference-time-verification-v1` 4,
`gepa-reflective-pareto-v1` 4). The spec names the cell that would exist
(`SAEA-SLURP-STAGE3-DELTA-CELL-ACE-R01-V1`, store `stage3-deltas-ace-v1`) and says plainly that "neither
cell exists yet; registering one is a package plus a fragment carrying its own `stage3_algorithm` label, not
new wiring."

**Why it is not flown, in the instrument's terms.** The spec fixes ACE as a one-factor arm on the locked
plan, released through the same store and the same `context_supply` route, read against the same sealed
comparator and the same derangement twin as CELL-1. That is a **cross-flight** design. The instrument's rule
3 sets the readable bar for a cross-flight cell at about **3 pp at n = 625** and about **2.5 pp at
n = 1,080**, and additionally requires an in-chain request-identical replicate, which doubles the flight.

Now compare that bar with what the two sibling context-injection families actually produced on the same
route, the same store and the same comparator:

| arm | pooled SLU delta vs PLAN | arm minus its own form twin |
| --- | ---: | ---: |
| CELL-1 (TF-GRPO v1r, 379 values) | -0.48 | -0.04 |
| CELL-2 (TF-GRPO v2, 200 values) | +0.64 | +0.59 |
| CELL-1-GEPA (GEPA, 448 values) | -0.04 | +0.73 |

Every measured effect on this route is **under 0.75 pp**, and the largest *content* attribution any of them
reaches is +0.73 pp. ACE differs from GEPA only in the **update** operator -- the curator's dedup and
grow-only discipline -- while GEPA's own curator already used the S3-5 dedup rule (exact normalised text,
then token Jaccard >= 0.8, provenance merged into the survivor) that ACE would re-use. The plausible effect
size is therefore *at most* the spread already observed between two stores on the same route, which is under
1 pp: roughly **a quarter to a third of the cross-flight bar**, before the replicate is paid for.

The cost side is priced by the siblings. CELL-1 spent 4,553 contacts and 1.8021 GPU-h, its twin another
4.142 contacts per row and 1.7879 GPU-h; CELL-1-GEPA spent 4,508 contacts and 1.8628 GPU-h, its twin 1.8912.
An ACE arm plus its twin is therefore about **9,000 contacts and 3.6-3.8 GPU-h**, plus the reflector and
curator contacts, plus -- if rule 3 is obeyed -- an in-chain replicate of the same size again.

**The conclusion, stated explicitly: flying ACE as specified would produce cost, not evidence.** The design's
floor is three to four times the effect the design can plausibly produce, so the outcome of the flight is
decided by flight variance before the first contact. This is not a judgement that ACE is a weak algorithm; it
is a statement that **this rig cannot read it in this design**. ACE becomes readable only if its update is
re-cast into a design with no flight offset -- an offline curation read over the already-sealed ROLL-1 pool
at the 0.67 pp floor -- or if it is composed with other changes into a single variant large enough to clear
the 2.5-3 pp bar, which is precisely the instrument's section 5 prescription.

**The closest thing to an ACE instance this repository has.** The system-memory line registered as
`tfgrpo-system-memory-disjoint-v1` (46 config fragments; "model-synthesized atomic batch memory updates",
typed guidance, stable ids, disjoint forward construction cohorts) is grow-and-refine over a memory store in
all but name, and it is the line ChatGPT is running. Its most recent read is
`docs/results/2026-09-26-system-memory-batch002-consumption-verdict.md`:

- 8 actors, **4 distinct TRAIN inputs**, 4 stochastic trajectories per arm, **32 complete episodes**, 160
  model generations, 32 local memory dispatches, 8 official scores;
- provisional memory 54.1962 against empty memory 55.7598 on the arithmetic mean of four roster-level
  scores = **-1.5636 pp**;
- complete-task exactness 1/16 (empty) against 0/16 (memory); intent 15/16 in both arms.

**That number is not readable, and the record itself says why.** It is a four-draw mean over four inputs. The
instrument's floor table has a row for exactly this design -- "terminal feedback on 4-16 trajectories,
n = 4-16, floor: *not readable*, flight offset: *dominant*" -- and its rule 5 states that a batch under about
200 rows is a **form proof**, never evidence of benefit. The verdict's own reading agrees and is more
specific: the only paired Solver output that differs at all occurs **before the memory tool is called** (the
two Perception histories already differ there), fifteen of sixteen paired Solver output strings are
identical, every Planner chooses ACCEPT and no episode revises. So -1.56 pp is not a causal estimate of
harmful memory; it is four draws of decoding noise on four inputs. What the batch *does* establish is textual
uptake -- the selected record reaches Reviewer and Planner in all sixteen learned episodes and some reviews
reproduce its language -- together with three named system failure modes: advisory authority displacing
evidence checking, misrepresentation of the tool result, and a missing objection read as confirmation. Those
are form findings, and they are worth having; they are not an effect.

---

## 4. The cross-family table

Every row is a development number (decisions 28, 86). "Effect" is the pooled official SLU-F1 delta against
that arm's own comparator; "floor" is the CI95 half-width the design can resolve, from the instrument's floor
table.

| family / arm | what its update is | where it enters the episode | contacts spent | measured effect (SLU) | measurement design | design floor | verdict | failure mode |
| --- | --- | --- | ---: | --- | --- | ---: | --- | --- |
| **TF-GRPO** ROLL-1 + S3-3 + ADV-1 (substrate) | grouped samples, per-sample official scores, 396 natural-language advantage blocks | nothing yet -- it produces the store | 5,344 + 225 | n/a (structural PASS: 225/225 legal) | structural read of sealed bytes | n/a | substrate closed | -- |
| **TF-GRPO** CELL-1 (v1r, 379 values) | per-row semantic advantage statements appended to a store | node context, candidate-bound (Solver 8 / Rev 4 / Plan 4; Perception 4 unconditional) | 4,553 arm + about 4,473 twin | -0.48 [-2.18, +1.24] | cross-flight vs sealed PLAN, **no in-chain replicate** | about 2.5 pp bar at n=1,080 | **no verdict either way** (rule 4) | credit from decoding noise |
| **TF-GRPO** CELL-2 (v2, 200 retained) | same, after the decision-83 per-scenario x frontier retention | same | 4,483 arm + about 4,406 twin | +0.64 [-0.76, +1.92] | cross-flight vs sealed PLAN, **no in-chain replicate** | about 2.5 pp bar at n=1,080 | **no verdict either way** | credit from decoding noise |
| **TF-GRPO** CELL-3 (v2 behind a scenario gate) | store unchanged; the *application policy* is the factor | same, gated: 355/1,000 rows gate-closed, 568 supplied | arm + twin + 4,090 (PLANr) | -1.44 [-2.88, -0.05] | cross-flight **with** in-chain replicate (-0.25, h 1.2525) | 1.2525 sampling plus the measured offset | **not distinguishable from flight variance** | credit from decoding noise |
| **GEPA** GEPA-R01 (proposer) | per-(scenario, node) reflective mutation of the node's statements | nothing yet -- it produces the store | 68 | n/a | structural | n/a | substrate closed | -- |
| **GEPA** CELL-1-GEPA (448 values) | reflective proposals plus the 200 retained, selected by the per-scenario frontier | node context, same route as CELL-1; reach 299/448 values | 4,508 arm + about 4,468 twin | -0.04 [-1.58, +1.39] | cross-flight vs sealed PLAN, **no in-chain replicate** | about 2.5 pp bar at n=1,080 | **no verdict either way** | prose-as-policy |
| **Best-of-N** offline rule study | none persistent -- a delivery rule over 5 sealed samples | the commit, after the Solver group | **0 model** (7 scorer-on-copies) | medoid +0.03 [-0.63, +0.71]; support-3 **+1.40 [+0.55, +2.29]**; oracle +6.55 | offline over one sealed sample pool, n=625 | **0.67 pp** | selection nil; the edit rule clears its floor but is what ROLL-1 already flew | no verifier in the loop (headroom unreached) |
| **Best-of-N** VERIFY-1 (live self-selection) | none persistent -- the core names one of its own 5 answers | the commit | 625 (1.00/row), 0.08165 GPU-h | SLU +0.70 [-0.26, +1.65]; **intent +0.544 [+0.032, +1.088]** | one contact per row over the same sealed pool | about 0.67 pp grade | **benefit not proven, no admission** -- but the only live non-noise signal | no verifier in the loop |
| **ACE** `ace-grow-refine-v1` | curator turns reflector output into incremental delta items: grow by append, refine by dedup | would be the same store and the same `context_supply` route | **0 -- never flown** | none | would be cross-flight at n=625 or 1,080 | **3 pp / 2.5 pp bar** | **not flown: the bar is 3-4x the plausible effect** | unmeasurable gradient |
| *(nearest ACE instance)* system-memory batch002 | per-batch model-synthesised atomic memory updates | Reviewer memory tool, then Reviewer and Planner context | 160 generations over 32 episodes | -1.5636 pp on 4 draws | terminal feedback on 4-16 trajectories | **not readable** | form proof only | unmeasurable gradient |

---

## 5. Four named shortcomings of the locked families on these tasks

Each is argued from the record and given a short name so later documents can cite it.

### S1 -- THE UNMEASURABLE GRADIENT

*The published loops evaluate a candidate update by re-running the task and reading the score. On this rig
that read costs one to three GPU-hours and carries a flight offset larger than the update.*

The evidence is a pure A/A contrast. `SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1` and
`SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1` are **request-identical**: the same 625 R01C rows, the same plan, the
same knowledge, the same serving geometry, two consecutive campaigns of one chain (flight commit `3ade29ff`,
2026-09-24 23:48 to 2026-09-25 02:11 UTC). They differ by **+1.87 pp pooled SLU-F1, CI95 [+0.41, +3.36] --
an interval that excludes zero -- while intent moves -1.28 pp**
(`docs/results/2026-09-25-slurp-var1-complete-evidence.md`; instrument section 2b). No intervention was
applied. The mechanism is known: llama.cpp at temperature 0 is not bitwise reproducible across batch
compositions. Within one flight 8.5 % of rows differ (`SAEA-SLURP-STAGE3-ROLL-AA-V1`, 200 rows, 1,030
contacts: 183/200 = 91.5 % byte-identical, 0/200 intent flips, h_within 0.735 SLU / 0.000 intent); across
flights about a quarter of the rows move.

Against that, the updates themselves measure **-0.48, +0.64, -0.04 and -1.44 pp**. Every one is inside the
instrument's measured cross-flight offset. And the re-run is not cheap: 1.77-1.86 GPU-h per 1,080-row arm,
doubled by the mandatory form twin, doubled again by rule 3's in-chain replicate.

*You cannot climb a gradient you cannot see.* This is a property of the rig and the effect sizes, not of the
tasks, and it is the shortcoming from which the other three follow: because the outer evaluation is
unaffordable and noisy, each family is forced to fit its update to an *inner* proxy -- and S2 and S3 are what
those proxies turn out to be.

### S2 -- PROSE-AS-POLICY

*The update is natural-language advice appended to node context; a large part of what it moves is the cost of
carrying more prose, not the advice.*

The derangement twin exists to separate the two: the same store, the same token volume, the same supply
shape, every value re-attached to a facet set that is not its own. Across the three delta cells the twin
reproduces most of the arm's movement -- arm minus twin is **-0.04** (CELL-1), **+0.59** (CELL-2) and
**+0.73** (CELL-1-GEPA), all inside the plan's own null of 1.2485.

The sharpest instance is the `general` stratum
(`docs/results/2026-09-24-slurp-general-scenario-diagnostic.md`, the 60 `general` rows of TRAIN Fold A). It
is the hole both families dig, and it is a **form** hole:

| arm, on the 60 `general` rows | pooled SLU-F1 | delta vs PLAN | intent | intent delta |
| --- | ---: | ---: | ---: | ---: |
| PLAN (v2.0 lock) | 30.23 | -- | 43.33 | -- |
| CELL-1 (v1r) | 17.86 | -12.37 | 33.33 | **-10.00** |
| CELL-2 (v2) | 19.61 | -10.62 | 36.67 | **-6.67** |
| CELL-2 **twin** (deranged) | 20.00 | -10.23 | 31.67 | **-11.67** |

**The twin loses as much as the arms, and on intent it loses more.** No delta content exists for this stratum
at all: 0 of 200 v2 values declare a `general` target and 0 of the values that reached these rows was learned
from a `general` source row. So the whole loss on the stratum is the cost of carrying a supply into a context
that has nothing to say about it. The recoverable amount is also small -- 10.00 pp intent and 11.16 pp pooled
SLU-F1 on 60 rows is 0.56 pp and 0.24 pp on Fold A -- which is why the diagnostic's own recommendation was to
*protect* the stratum from the supply rather than try to win it.

That is the structural shortcoming: an update expressed as appended prose pays a token-volume and
attention-dilution cost on **every row it reaches**, including the rows it has nothing to say about, while
its content can only help the rows it covers. On a pooled micro metric the two cancel. CELL-1-GEPA is the
control for the authoring mechanism: a completely different reflective proposer, on the same route, produced
the same shape (gainers audio, weather, datetime, iot; losers general, news, social, music; pool zero).

### S3 -- CREDIT FROM DECODING NOISE

*Grouped samples under one fixed context differ by sampling, so a per-value advantage fitted to those
differences is fitted to noise.*

Three measurements, in increasing severity.

1. **The group's own signal is thin.** On 400 of 625 ROLL-1 rows the five samples score identically; credit
   can only be assigned on the remaining 225
   (`docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md` section 3).
2. **Where the samples do differ, no deterministic rule extracts value from the difference.** On those 225
   disagreeing rows *not one* aggregation rule's CI95 excludes zero, while the oracle reads +12.55 pp
   [+10.99, +14.15]. The disagreement is real and carries information; agreement-based statistics do not
   reach it.
3. **The fitted per-value ranking does not transfer.** Of 86 TRAIN Fold A winner values, 37 are negative on
   the fresh DEV-2000-ADDED roster; their mean per-row SLU delta there is **+0.33 pp, *lower* than the 26
   Fold A losers' +0.99 pp**, and **sign agreement across the two venues is 49 of 96**
   (`docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md` section 2a). The same diagnostic
   shows the harm is diffuse -- across 120 supplied value ids the ten worst carry only 26.3 % of the harm
   mass -- so no pruning rule can cut it, and an **oracle gate** over this store reaches 64.89 (-0.51 pp vs
   PLAN): the best any application policy over this store can do is stop doing harm.

Together they say that the group-relative semantic advantage, as this rig can compute it, is a measurement of
decoding variance dressed as a lesson.

### S4 -- NO VERIFIER IN THE LOOP

*The published loops trust the terminal score to select updates offline but never let the system choose among
its own trajectories at inference -- which is the one place a non-noise signal appeared.*

Both TF-GRPO and GEPA as specified use the official score exactly once: to rank rollouts so that an update
can be authored. Neither gives the running system any ability to compare its own candidate outputs at
delivery time. Yet:

- the sealed oracle over five samples is **+6.55 pp [+5.56, +7.56]** pooled and **+12.55 pp** on the
  disagreeing rows;
- the only two Stage-3 effects that clear their own design's floor are both selection/commit effects: the
  entity support filter at s=3, **+1.40 pp [+0.55, +2.29]**, and VERIFY-1's self-selection intent gain,
  **+0.544 pp [+0.032, +1.088]** (instrument section 4);
- and VERIFY-1 achieved its intent gain with **one extra contact per row (625 total, 0.08165 GPU-h)** --
  orders of magnitude cheaper than any delta-store iteration (ROLL-1 5,344 + ADV-1 225 + CELL-1 4,553 plus
  its twin, for one iteration).

The gap between the oracle and every realised rule is the clearest unexploited headroom in the record, and
none of the three locked update families is pointed at it.

---

## 6. The optimisation space this program defines

The instrument dictates the organising principle: **classify actions by whether this rig can measure them**,
not by what mechanism they belong to. An action is worth defining only together with the design that will
read it and that design's floor.

### Class A -- computable over a sealed sample pool. Floor 0.67 pp. Zero GPU.

**What is in it.** Selection among already-produced samples; the commit rule (which bytes are delivered and
how they are edited); verification; projection and normalisation of the delivered answer; re-ranking of
content that was *already retrieved*. Anything whose effect is a deterministic function of bytes that are
already sealed.

**Why it is first.** No new generation, so no flight offset at all, and the whole rule space can be swept in
one offline pass (the aggregation read evaluated 14 rules in a single deterministic, cache-reproducible run).
The floor is **h_offline about 0.67 pp at n = 625**, the smallest this program has, and it is also the class
where both floor-clearing effects already live.

**Bad-case headroom it can address** (`docs/results/2026-09-24-slurp-plan-bad-case-bank.md` section 6;
STABLE-WRONG is the honest target because the rest of each class is inside the replicate's own noise):

| class | TRAIN Fold A: SLU pp / stable-wrong | DEV-2000-ADDED: SLU pp / stable-wrong |
| --- | --- | --- |
| ENTITY-FP-ONLY (131 / 108 rows) | +4.76 / **+4.32** | +3.47 / **+3.06** |
| the FP half of ENTITY-MIXED (193 / 195 rows) | within +17.43 / +16.65 | within +16.47 / +16.08 |

The class is demonstrably live on that mass: the support filter removed 144.3 units of FP mass (-16.2 %) for
9.7 units of FN (+1.4 %), and 30.6 % of the construction rows carry no gold entity at all, so every entity
emitted there is pure pooled false positive. The N=1 form of the same idea -- a registered
`core.base.DELIVERY_NORMALISERS` entry under I7n, 1x contacts, no grouped Solver -- is the cheapest
unexplored action in the whole space.

### Class B -- new contacts, but comparable per row inside one campaign. Floor about 0.7 pp.

**What is in it.** Which view, which budget, which k a node consumes: exemplar depth, candidate width, supply
composition -- anything that can be varied *between arms of the same flight* so that the comparison is paired
per row and no cross-flight offset enters.

**Its two open prerequisites, as the instrument states them.** The `supply_variants` mechanism (item E42)
exists and is tested, but (a) the family was **closed after two aborts** and its re-authorisation is an owner
decision -- VAR-2's sole recovery aborted at 441 contacts on a cumulative-cardinality envelope the recovery
proof did not cover, 721 model contacts across both attempts and both smokes, no complete manifest and no
official score (`docs/results/2026-09-25-slurp-var2-closed-engineering-failure.md`) -- and (b)
**`core/bundle/outputs.py` must learn `supply_variants` before any number from it is reported** (instrument
rule 2).

**What it already produced.** VAR-1 is the one family that measured its own offset, because it flew PLANR
inside its own chain, and therefore read its variants correctly: the exemplar-k arms are **+0.07 / +0.09 pp
over PLANR**, not the +1.94 / +1.95 they read against PLAN (instrument section 4; the sealed levels are
exk10 60.44, exk30 60.46, PLANR 60.38). That correction is the whole argument for class B: the design, not
the mechanism, decided the earlier number.

**Bad-case headroom it can address.** INTENT-UNCOVERED -- the largest *intent* mass, and the one a wider or
differently-composed Perception view speaks to directly: **+5.41 pp SLU / +12.04 pp intent** on TRAIN Fold A
(stable-wrong +5.38 / +11.76) and **+6.82 / +16.90** on DEV-2000-ADDED (stable-wrong +6.68 / +16.50). On
TRAIN Fold A the gold intent was absent from Perception's first candidate list on 130 of 191 intent-error
rows, and on DEV on 169 of 232. ENTITY-FN-ONLY (+5.11 / +4.04 SLU) is the supply-composition half of the same
class.

### Class C -- changes what every node generates. Bar 2.5-3 pp. Must be composed.

**What is in it.** Candidate-proposal width as a policy, a new node, a new contract, a new response format --
anything that alters the generation of every row and therefore can only be read cross-flight.

**Why it must be composed rather than tested one at a time.** Rule 3 sets the bar at about **3 pp at
n = 625** and about **2.5 pp at n = 1,080** and requires an in-chain request-identical replicate. Nine
Stage-3 mechanism families have now been flown and not one single-factor change has produced an effect of
that size; the largest single-factor content attribution in the record is +0.73 pp. Testing class-C actions
one at a time therefore guarantees an unreadable result, whatever the action. The instrument's prescription
is the only one the arithmetic allows: **batch every action that truly needs new contacts into one composed
variant**, predict its effect offline over the sealed pool, and spend a flight only on the composed policy
the offline loop says will clear the bar.

**Bad-case headroom it can address.** The two classes nothing cheaper reaches: **ENTITY-MIXED**, the single
largest mass (193 / 195 rows, **+17.43 pp SLU on TRAIN, +16.47 on DEV**; stable-wrong +16.65 / +16.08, and
zero intent headroom -- it is pure entity work), and **INTENT-COVERED**, the selection failures where
Perception did propose the gold intent and the Solver chose otherwise (61 / 63 rows, +2.35 / +2.67 SLU and
**+5.65 / +6.30 intent**). For reference, a *perfect* repair of every bad row would be +34.20 SLU / +17.04
intent on TRAIN Fold A stable-wrong and +33.11 / +22.60 on DEV-2000-ADDED -- the exact upper bound of the
whole space.

### The shape of the space, in one sentence

Order the actions by measurability and the next moves fall out: **sweep class A offline until it is
exhausted** (it holds the only two floor-clearing effects and the cheapest unexplored action), **re-open
class B behind its two named prerequisites** (it addresses the largest intent mass), and **enter class C only
with a composed variant** whose offline prediction clears 2.5-3 pp.

---

## 7. What this baseline does not establish

It establishes no effectiveness, superiority, generalisation, component-causal, cross-carrier or paper-scale
claim for any family. Every number is a development number on an exposed TRAIN construction fold or a DEV
roster (owner decisions 28 and 86); the SLURP test split is closed and none of these figures is comparable
with a published TEST baseline. It does **not** show that Training-Free GRPO, GEPA, ACE or best-of-N
verification are weak algorithms: for three of the four, the design that read them could not have seen an
effect of the size they produce, which is a statement about this rig's instrument and not about the published
methods -- and for ACE nothing at all was measured. Neither does it show the converse: no arm here is
admitted, replicated or promoted; the two effects that clear their own floor are a re-measurement of a commit
policy the rollout had already flown and an intent-only non-inferiority guard, and both records refuse
promotion in their own words. The headroom figures of section 6 are exact upper bounds on a *perfect* repair
of a class, never forecasts of any rollout. And the class boundaries of section 6 are a measurement
convention, not a theory of what these systems need; they will change the moment the instrument does.

---

## 8. Records read

Sealed records this report is built from, all already closed:

- `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`
- `docs/results/2026-09-22-slurp-v2-lock-v1.md`, `docs/results/2026-09-22-base-lock-v3.md`
- `docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`
- `docs/results/2026-09-23-slurp-stage3-advantage-r01-read.md`
- `docs/results/2026-09-23-slurp-stage3-delta-cell-r01-verdict.md`
- `docs/results/2026-09-24-slurp-stage3-delta-cell-r02-verdict.md`
- `docs/results/2026-09-24-slurp-stage3-delta-cell-gepa-r01-verdict.md`
- `docs/results/2026-09-24-slurp-stage3-delta-cell-r03-gate-verdict.md`
- `docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md`
- `docs/results/2026-09-24-slurp-general-scenario-diagnostic.md`
- `docs/results/2026-09-24-slurp-plan-bad-case-bank.md`
- `docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md`
- `docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`
- `docs/results/2026-09-25-slurp-var1-complete-evidence.md`
- `docs/results/2026-09-25-slurp-var2-closed-engineering-failure.md`
- `docs/results/2026-09-25-slurp-verify1-complete-evidence.md`
- `docs/results/2026-09-26-system-memory-batch002-consumption-verdict.md`
- `docs/results/stage2-results-ledger.md`
- `docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/README.md`
- `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`
- `src/speech_aware_evidence_acquisition/core/stage3_algorithms.py`
- `docs/exposure-ledger.md` (run ids only)

### 8a. Three record defects observed while reading (reported, not repaired here)

1. **`core/stage3_algorithms.py` statuses lag the flights.** `gepa-reflective-pareto-v1` and
   `inference-time-verification-v1` are both `status="planned"` although CELL-1-GEPA and VERIFY-1 have flown
   and sealed. `ace-grow-refine-v1` is correctly `planned`.
2. **The CELL-1-GEPA verdict records two different algorithm labels.** Its title says
   `gepa-reflective-pareto-v1` (operators update + selection + context_application) and the results-ledger
   row agrees, but its own section 9 says `tfgrpo-semantic-advantage-v1`; the GEPA readiness README declares
   operators `credit_assignment` + `update`. Three statements, three operator sets.
3. **The "four launch failures, 320 metered contacts" caveat block appears verbatim in all three delta-cell
   verdicts** (CELL-1, CELL-2, CELL-1-GEPA), each time as "four launch failures preceded this flight". The
   four attempts it describes are the CELL-1 launch sequence. Whether the block in the CELL-2 and CELL-1-GEPA
   verdicts records three separate 320-contact events or is a copied caveat cannot be decided from these
   records, so this report attributes the 320 contacts once, to CELL-1.
