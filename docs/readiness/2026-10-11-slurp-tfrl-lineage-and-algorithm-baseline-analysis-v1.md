# Training-free RL since Training-Free GRPO: the lineage, the baseline that fits this task, its deficits here, and what this study has done about them

Written 2026-10-11 by the coordinator (Fable 5.1) in answer to the owner's request of the same day (registry
section "Owner request 2026-10-11: return to the algorithm"). Model-free: no model, server, GPU, dataset or
paid-API contact was made. Literature facts come from the papers' own abstracts, method sections and
ablations as read on 2026-10-11 (arXiv ids given; numbers are the papers' own and are quoted only where they
bear on a design choice). Facts about this study are read from sealed records; every such figure carries its
file. Labels, counts and scores only; no utterance text, transcript, gold filler or model output.

Companion documents: `docs/results/2026-09-26-slurp-stage3-locked-tfrl-academic-baseline-v1.md` (what was
flown of the TF-GRPO and GEPA families here, and the four named shortcomings S1-S4) and the registry section
"Where training-free RL acts in this study" (decision 262, the stable-gain ledger).

---

## 0. The three answers in one paragraph each

**Q1 -- which academic baseline fits this task best?** Of the training-free lineage, the method whose problem
statement and update structure match this task is **ACE, agentic context engineering (arXiv 2510.04618)**:
an itemised, incrementally updated context store (grow-and-refine, never a whole-view rewrite) driven by
execution or verifier feedback, which is what the SLURP official scorer on TRAIN provides. Training-Free GRPO
(arXiv 2510.08191) is the lineage's named origin and must stay in the paper as the second comparator, but it
is a worse fit here for measured reasons: its signal exists only where a sampled group disagrees (empty on
400 of 625 rows in ROLL-1), its advantage is written as prose by the frozen core (the 30B-A3B core is a weak
reflector: Reviewer repair 0 of 100, ADV-1 node attribution wrong for more than half the blocks), and its
per-query experiences are selected on a single training score. GEPA (arXiv 2507.19457) needs instance-level
Pareto evaluation rollouts this rig cannot afford (S1). Memento (arXiv 2508.16153) and SEAM (arXiv
2602.02556) train a component (a case-selection policy; an experience generator) and are excluded by the
research boundary (no task-trained model).

**Q2 -- what does ACE still lack on this task?** Seven deficits, each tied to a measurement of this study:
(D1) its reflector/curator is the same frozen model, and ours cannot write reliable lessons; (D2) its items
are prose, and prose supplied to every row pays a form cost on a pooled micro metric that cancels the
content gain (the derangement twin reproduces the arms; the `general` stratum loses 10 pp on arm and twin
alike); (D3) its playbook is global, keyed by nothing: on a speech task the gain lives in speech-keyed
retrieval of typed knowledge (B1 +12.6 pp), which ACE has no operator for; (D4) it accepts deltas on a
single training score with no noise model, while this rig's request-identical A/A pair differs by +1.87 pp
[+0.41, +3.36]; (D5) it updates only between episodes and has no inference-time verifier, although the
best-of-5 oracle is +6.55 pp here; (D6) its context grows (ACE reports contexts of about 18k tokens) while
our serving slot leaves about 12k tokens of headroom beside a 10-11k Solver prompt; (D7) its updates are
unscoped, so a delta that helps one stratum harms another (RIZZ's negative-transfer finding; our CELL-3
scenario gate did not rescue the delta store).

**Q3 -- do we have measures for these deficits?** For D1, D2, D3, D4, D6 and D7: yes, implemented and
measured; they are the content of the sealed-credit loop of decision 262 (typed per-row official credit
instead of a prose reflector; typed knowledge entries and deterministic rules instead of prose items;
speech-keyed construction; a noise-floored, twin-controlled, fresh-roster acceptance test; a fixed supply
budget; stratum protection instead of global supply). Each measure has a replicated gain or a replicated null
behind it (section 5). For D5: tested (VER-1), about +0.9 pp at 6 contacts per row, closed as a lock
candidate; the headroom is real and unexploited. What is NOT yet done, and is the algorithmic gap the paper
must close: the loop has never run **autonomously for several iterations** with a proposer confined to typed
operators; every accepted update so far was authored or chosen by the coordinator from the credit tables.
Section 6 proposes that run (decision 263), with ACE in its published form as the in-flight comparator at the
same contact budget.

---

## 1. The lineage: what each work identified and how it changed the learning algorithm

The table follows the lineage from Training-Free GRPO forward and backward to its immediate ancestors. "Fix"
is the algorithmic change, not the headline number.

| work (arXiv) | problem the authors identified | algorithmic fix | what it still assumes |
| --- | --- | --- | --- |
| Dynamic Cheatsheet (2504.07952, 04-2025) | the model re-solves the same sub-problems; nothing persists across test queries | a test-time memory of reusable strategies and code snippets, curated at inference by the model itself | model-judged usefulness; unbounded growth; no verifier |
| GEPA (2507.19457, 07-2025) | RL from scalar rewards discards the textual feedback a trajectory carries and needs tens of thousands of rollouts | reflective prompt evolution: the model reads trajectories plus textual feedback and proposes prompt edits; a per-instance Pareto frontier keeps diversity and prevents collapse to one prompt; reports up to about 35x fewer rollouts than GRPO | each candidate is still evaluated by re-running the task; the frontier needs many instance-level evaluations |
| Memento (2508.16153, 08-2025) | memory retrieval by heuristics is not optimised for the downstream reward | a memory-augmented MDP with a learned case-selection policy (a small trained Q-function) over a case bank; the LLM stays frozen; reports +4.7 to +9.6 pp out of distribution | a task-trained retriever |
| ReasoningBank + MaTTS (2509.25140, 09-2025) | memories store raw trajectories or only successes; failures carry no lesson | distil generalisable strategies from successes AND self-judged failures; memory-aware test-time scaling generates several trajectories per task to enrich what is distilled | correctness is self-judged; the distiller is the same model |
| **Training-Free GRPO** (2510.08191, 10-2025) | RL fine-tuning of a large model is expensive, overfits on small data, and loses generality; plain prompting has no exploration or credit structure | keep the parameters frozen; sample a group of G rollouts per query; have the model state in words what separated better from worse members ("semantic advantage"); write the statements into an experience library with add / delete / modify / keep operations; prepend the library on later rows; a few epochs over about 100 training queries | a ground-truth reward on the training queries; group disagreement (G = 1 degrades in their ablation); a base model strong enough to write the lesson (their weaker base underperformed on the web task) |
| **ACE** (2510.04618, 10-2025) | two failure modes of context optimisers: **brevity bias** (optimisers compress toward short generic prompts and lose domain detail) and **context collapse** (a monolithic rewrite shrinks the context; their example: about 18,282 tokens to 122, accuracy 66.7 to 57.1) | generator / reflector / curator; the context is an itemised playbook; updates are **incremental delta items** (grow), de-duplicated and pruned (refine); never a whole-view rewrite; works from execution feedback without labels; reports +10.6 % on agent tasks and +12.3 % over GEPA on AppWorld | reflector quality (their ablation); long contexts and KV-cache reuse; not for tasks that need a concise instruction |
| Procedural Knowledge at Scale (2604.01348, 04-2026); Chain-of-Experience (2608.18027, 08-2026) | experiences do not transfer across tasks; libraries built per task are re-built from zero | a shared procedural-knowledge library across tasks; experience chained along a trajectory rather than stored as isolated items | the same reflector and the same acceptance by training score |
| SEAM (2602.02556, 02-2026) | experiences written by the frozen model are not optimised for their utility to the executor | train a separate experience generator with GRPO, the executor's downstream utility as the reward; the executor stays frozen | a trained generator |
| RIZZ (2606.20638, 06-2026) | **interference / negative transfer**: an update that helps one input family degrades another; unverified lessons accumulate | route updates to zero-interference memory branches by input family; accept only verified updates; store anti-patterns beside patterns | branch keys defined on text |
| credit-assignment line: iStar (implicit step rewards, ICLR 2026), HCAPO (2603.08754), VICT (2608.28128), SIOP (2605.04984); GRPO critiques (2602.05548) | one terminal scalar per trajectory gives every step the same credit; when all members of a group score alike the group advantage vanishes and the step gets no signal | step- or turn-level credit derived from the trajectory itself (implicit rewards, hierarchical advantages, turn-level credit without a verifier) | parameter updates (these are trained-RL works; the credit idea transfers, the optimiser does not) |

Three readings of the table that matter for this task:

1. **The lineage moved from "write a lesson" to "write a structured item, keep it incremental, verify it,
   and scope it."** TF-GRPO's single library of prose became ACE's itemised delta playbook, then RIZZ's
   verified, branch-routed memory. The direction of travel is toward typed, scoped, verified updates. This
   study's stable gains are all of that last kind (section 5).
2. **Every work in the training-free branch still selects updates on a single evaluation of the training
   score** and reports one run per setting. None states a noise model of its evaluator, a form control (what
   the same tokens do when the content is wrong), or a fresh-roster confirmation rule. On this rig the
   evaluator's own A/A variation exceeds the effects (S1), so the acceptance test is part of the algorithm,
   not a reporting detail.
3. **Credit assignment improved only in the trained branch.** The training-free works assign credit by
   asking the model (semantic advantage, reflector). The trained works compute it from the trajectory.
   This study computes it from the official scorer per row and per node (typed failure classes, exchange
   rates), which is the trained branch's idea carried into the training-free setting.

---

## 2. What is specific about this task (the facts a baseline has to fit)

| property | fact | source |
| --- | --- | --- |
| P1 input is speech | the row is an audio packet; there is no text query to key a memory by; the only inputs available to retrieval are speech embeddings and the core's own outputs | study `CLAUDE.md` research boundary; decision 128 (queries contain speech) |
| P2 closed, structured output with a decomposable reward | 18 scenarios x actions (closed intent list), slot types and fillers; the official scorer gives per-row, per-entity typed credit (SPURIOUS / MISSING / WRONG-TYPE / BOUNDARY / NEAR / WRONG-VALUE / FORMAT) and gold exists offline on TRAIN | `reproduction/slurp_scoring.py`; `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` |
| P3 evaluator noise | request-identical A/A arms differ by +1.87 pp SLU-F1 [+0.41, +3.36] across flights; 8.5 % of rows differ within a flight; the same-flight paired floor is 1.49 pp at n = 1,080 | instrument note 2026-09-26; decision 190 |
| P4 weak reflector | the core at Q4 repairs 0 of 100 drafts as Reviewer; after a true alarm 1 of 32 revisions is correct; ADV-1 attributed more than half of 396 advantage blocks to nodes that were not sampled | `docs/results/2026-10-08-simple-consumption-n100-complete-family.md`; locked baseline note 3.1 |
| P5 context budget | np4 slots of 24,576 tokens with a 3,072 reserve; the Solver prompt is 10-11k tokens; the full tool catalog alone is 13,914 tokens | memories `fit-gate-live-slot-reserve`; NX exchange note |
| P6 boundary | zero parameter training, no task-trained model, no second answering LLM; a frozen tool-level retriever or judge only when pinned and logged; paid API 0 | study `CLAUDE.md` |
| P7 effect sizes | the remaining headroom is 1-3 pp effects on a 64-67 SLU-F1 base; the published trained ceiling is HerMiT 70.84 | test-sample read 2026-10-10 |
| P8 where the mass is | 214 of 407 delivered gold-side errors on Fold A are consumption failures with the value in the supply; about 106 are hearing-type; about 40 % of rows have empty gold and false fill is the largest single loss | headroom note 2026-09-29 |

---

## 3. Q1 in detail: fitting each baseline to P1-P8

| baseline | P1 speech key | P2 typed credit | P3 noise | P4 reflector | P5 budget | P6 boundary | verdict here |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Training-Free GRPO | none (library prepended to all rows) | uses the score only to rank the group; the lesson is prose | one training score per epoch; no twin | the core writes the advantage | library grows per epoch | fits | **flown here in faithful shape (ROLL-1 -> ADV-1 -> CELL-1/2/3): -0.48 / +0.64 / -1.44 pp, twins reproduce the arms; signal empty on 64 % of rows (S3)** |
| GEPA | none | textual feedback | per-instance Pareto needs many evaluation rollouts | the core reflects | prompt-sized | fits | flown as CELL-1-GEPA: same shape as TF-GRPO, arm minus twin +0.73 inside the null |
| ReasoningBank + MaTTS | none | self-judged success/failure | one run | the core distils | grows | fits | not flown as such; its MaTTS half is our ROLL form (5 samples), where every deterministic aggregation rule read at most about +1 pp and self-judging (c3 verdict) added +0.5-0.8 |
| Memento | learned retriever could in principle take a speech key | reward-trained selection | trained offline | no reflector | case bank | **excluded** (task-trained Q-function) | not admissible |
| SEAM | none | utility-trained generator | trained | trained generator | items | **excluded** | not admissible |
| **ACE** | none (global playbook) | execution / verifier feedback; itemised deltas | one run; curator judges | the core reflects and curates | about 18k-token contexts | fits | **best structural fit: incremental typed items, verifier-driven, no group needed; registered here as `ace-grow-refine-v1`, never flown** |
| RIZZ | branch keys on text | verified-only updates; anti-patterns | one run | the core | branches | fits | the scoping idea is what CELL-3's gate attempted; the verified-only rule is our acceptance test |

**Why ACE and not TF-GRPO as the primary comparator.** TF-GRPO needs three things this task does not give
it: a disagreeing group on most rows (ROLL-1: 225 of 625), a reflector that can name the cause of the
difference (P4), and an evaluator quiet enough to accept a per-epoch library on one score (P3). ACE needs
none of the three: its unit of update is an item with a scope, its signal can be a verifier (the official
scorer on TRAIN rows), and it does not sample a group. Its two named failure modes, brevity bias and
context collapse, are also the ones observed in this study's own text learners: the K16 population learner
drifted to shorter generic templates with utility falling from -56 to -69 (NX audit A3), and the joint
system-text search produced no accepted change in five rounds. ACE's remedy (never rewrite the whole view;
add and refine items) is what this study's typed stores already do.

**What stays from TF-GRPO.** The outer loop shape (rollout -> credit -> update -> re-evaluate) and the
experience-library operations (add / delete / modify / keep) are the right vocabulary for the method
description, and the family has already been flown here at n = 1,080 with twins, which no other study of
the lineage reports. It remains the second comparator in the paper.

---

## 4. Q2 in detail: ACE's deficits on this task

| id | deficit of ACE as published | measurement in this study that shows it binds |
| --- | --- | --- |
| **D1 reflector** | the reflector and curator are the frozen model; ACE's ablation says reflector quality is decisive, and its reported numbers use strong proprietary or 600B-class reflectors | Reviewer repair 0 / 100; 1 / 32 correct after a true alarm; ADV-1 misattribution; paid API 0 means no external reflector (decision 255: local proposers only) |
| **D2 prose items** | items are natural-language bullets rendered into every row's context | derangement twins reproduce the arms (arm minus twin -0.04 / +0.59 / +0.73); `general` stratum: PLAN 30.23 SLU, CELL-2 19.61, its twin 20.00, intent -6.67 vs -11.67 (twin worse) -- the cost is carrying prose, not its content (S2) |
| **D3 no key** | one playbook per task, retrieved by inclusion, no input-conditioned selection | the largest gains here are retrieval gains keyed by speech: B1 exemplars k20 +12.61 [+10.54, +14.60], replicate +13.70; COMP-1b centroid keys + agreement vote intent +4.60 DEV / +5.80 test; ACE has no operator that changes the key or the vote |
| **D4 acceptance** | a delta is kept when the curator judges it helpful on the training signal; one run per setting | A/A offset +1.87 [+0.41, +3.36]; TF-GRPO winner values' sign agreement across venues 49 / 96; the 2026-09-26 instrument therefore requires n >= 1,080 paired, a form twin, a 1.49 pp floor, and Fold A / DEV / test confirmation (decision 247) |
| **D5 no inference-time verifier** | updates land between episodes; the running system never compares its own candidates | best-of-5 oracle +6.55 [+5.56, +7.56]; realised deterministic verification about +0.9 pp (VER-1, 5-sample filter s = 2: +0.85 / +1.03 / +0.76 across pools), Fold A confirmation of the composed rule NOT CONFIRMED (+0.56 [-0.40, +1.51]) |
| **D6 budget** | the playbook grows; ACE relies on long context and cache reuse | slot 24,576 tokens, Solver 10-11k, reserve 3,072; the prefix cache already serves 88.94 % of prompt tokens; dedup freed 3,120 tokens (decision 128); EFF-1's constant tool rendering alone broke 137 rows |
| **D7 scope / interference** | updates are global; RIZZ shows negative transfer across input families | CELL-3 scenario gate on the delta store: -1.44 [-2.88, -0.05] on DEV (not distinguishable from the flight offset), harm diffuse over 120 value ids (ten worst carry 26.3 %); the oracle gate over the store reaches only -0.51 vs PLAN |

Two deficits are not ACE's alone but are inherited by every member of the lineage: D4 (no noise model) and
D5 (no verifier at delivery). D3 is specific to speech input and is the one no published training-free
work addresses.

---

## 5. Q3 in detail: the measures taken, with their evidence

The sealed-credit loop (decision 262) is, operator by operator, ACE with D1-D4, D6 and D7 replaced:

| ACE operator | this study's replacement | status and evidence |
| --- | --- | --- |
| reflector writes lessons (D1) | **no free-text reflector**: credit is computed by the official scorer per row and per node (typed failure classes, exchange rates +0.062 pp per recovered MISSING, +0.091 per repaired wrong entity); candidates are proposed from aggregate contrast tables (NX C3 protocol), by hand or by a local proposer that may only fill typed slots | implemented (R0.2 exchange-rate note; R1 / R6 column reads); the free-text alternative was read five times at n >= 1,000 and never cleared noise |
| itemised prose playbook (D2) | **typed entries**: speech-keyed TRAIN exemplars (B1), slot-contract cards (B4b), centroid boundary keys and an agreement vote (COMP-1b), and deterministic delivery rules learned from TRAIN statistics (v4g: 431 rule combinations searched by official credit; +0.98 [+0.21, +1.74] on A2, confirmed Fold A +1.67, Fold B +1.55 [+0.81, +2.33]) | locked in v2.2; test sample SLU +1.67 [+0.53, +2.83] over COMP-1b |
| global inclusion (D3) | **speech-keyed construction**: retrieval key in the query's own embedding space, k fixed at 20, centroid keys for intent | locked; intent +4.60 DEV [+2.58, +6.73], +5.80 test [+4.04, +7.42]; R5 same chain +4.90 |
| curator accepts on one score (D4) | **the instrument as part of the method**: same-flight paired columns at n >= 1,080 or offline reads at the 0.67 pp floor; a derangement or request-identical twin on every arm; CI95-LB over the floor to select; Fold A, then DEV, then the signed test sample to confirm; cross-fit for any TRAIN-fitted rule (decisions 190, 192, 231, 247) | in force since 2026-09-26; it is what turned VER-1's in-sample +1.29 / +1.43 into an honest NOT CONFIRMED |
| grow (D6) | **fixed supply budget**: k = 20, dedup of retrieved values, no constant tool rendering, Perception note grammar-bound to one 128-char free field | locked (decisions 128, 245); EFF-1 and the R6 mention tags showed the channel binds before the information does |
| global update (D7) | **stratum protection instead of scoped prose**: the v4g scope rule and the empty-entity rate guard; no supply to strata that have no content for them; per-scenario tables on every read | locked in v4g; the scenario gate over prose (CELL-3) was the failed alternative |
| none (D5) | **deterministic verification at delivery** over extra samples: support filter, c3 verdict x N1 gate, greedy-first sampling | VER-1 read: about +0.9 pp at 6 contacts per row, closed as a lock candidate (decision 260); the oracle headroom (+6.55) stands unexploited |

**What is still missing.** The loop above has accepted five updates (B1, B4b, COMP-1b, v4g, review-off) in
about three weeks, and in every case a person chose the candidate from the tables and the instrument
accepted or refused it. Published training-free methods are judged as **algorithms**: given a training set
and a budget, they run several iterations without a person in the loop and the curve is reported. This study
has that curve only for the free-text learners (flat) and not for the typed loop. Two further gaps: the
D5 headroom (a verifier at delivery with real signal) and the stratum interference check (RIZZ) are not yet
standing parts of the read.

---

## 6. Proposal: decision 263, the autonomous typed loop with ACE as the in-flight comparator

**Object.** Run the sealed-credit loop autonomously for three iterations on the SLURP lock v2.2 with the
proposer confined to typed operators, and fly ACE in its published form beside it at the same contact budget,
so the paper has (a) the loop's curve and (b) a head-to-head against the best-fitting academic baseline on
this task, both under the instrument.

**The typed operator set (the proposer's only action space).** Each operator is a change to a registered,
hash-pinned artefact; the proposer (local model, decision 255) sees only the aggregate contrast tables of the
previous iteration and emits one candidate per operator class:

| class | operator | artefact | precedent |
| --- | --- | --- | --- |
| construction | per-scenario exemplar weights; which slot-type cards are built; centroid key source | exemplar index view, slot store, key view | B1, B4b, COMP-1b, K6p |
| supply | k per scenario within the fixed token budget; card-set selection | supply fragment | M1 k, VAR-2 |
| delivery | a rule from the v4g rule grammar (article, o'clock, scope, type inventory, rate guard families) with thresholds fitted on the iteration's own fold | normaliser table | v4g |
| scope | which scenarios an entry is routed to (RIZZ branch) | routing table | CELL-3 gate (as a form), v4g scope rule |

No operator may write free text into a node prompt; the note contract and the Solver contract stay as locked
(decision 245 consistency). Every candidate carries its predicted effect from the exchange-rate table
(decision 192) and is refused below 1.5 pp predicted.

**The ACE comparator arm.** `ace-grow-refine-v1` as registered: the core as reflector and curator over the
previous iteration's sealed trajectories and their typed credit tables (the credit is given to it; it writes
the items), an itemised playbook supplied to the Solver within the same token budget as the typed arm's
supply, delta updates only, de-duplication each iteration. This gives ACE its verifier (P2), removes the
budget confound (D6) and leaves D1, D2, D3 and D7 as the measured differences.

**Design and cost.** Per iteration one same-flight cell on TRAIN Fold B with three delivering-path columns
(lock, typed candidate, ACE candidate) at n = 1,080, about 2.5-3 GPU-h; selection by CI95-LB over 1.49 pp
against the lock column; after iteration 3 one Fold A confirmation of each arm's accumulated state (about
2 GPU-h); then the DEV composed read. Total about 11 GPU-h, two to three weeks at the current cadence,
SLURP only (decision 242 unchanged). Acceptance rule for the paper claim: the typed loop's cumulative gain
over the lock has CI-LB > 0 on Fold A after three iterations, and the ACE arm's does not, or does by less;
either outcome is reported.

**What it does not do.** It does not reopen free-text learners, the Reviewer loop, the Perception-note
contract, or any carrier GPU. It does not address D5; the hearing-pass tool line (261-B) remains the only
open D5 route and is designed separately (the evidence survey of 2026-10-11 found no record supporting it
yet; see the registry).

**Options for the owner.**
- **263-A (recommended)**: approve the autonomous typed loop with the ACE comparator as above.
- **263-B**: the typed loop alone (about 8 GPU-h); ACE compared only on paper against its published failure
  modes.
- **263-C**: no further SLURP algorithm rounds; package v2.2 and the stable-gain ledger (262) as the Stage-2
  result and release the carriers.
