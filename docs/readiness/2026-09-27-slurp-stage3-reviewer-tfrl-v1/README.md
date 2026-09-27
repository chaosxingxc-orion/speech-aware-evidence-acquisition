# REV-TFRL-1: training-free RL optimisation of the Reviewer node (owner decision 165)

Owner decision 165 (2026-09-27, translated): *"nodes like the Reviewer can all be optimised and improved; do not
mechanically throw them away -- use training-free RL to optimise its behaviour on its own."* This package is the
design, the reward signal (the Reviewer's credit table over sealed pools), the offline inner loop, and the first
cell it selects. Registered before contact 2026-09-27 at study commit `4d459858` by
Claude Opus 5.5 (worktree `/home/chao/saea-worktrees/fable-revtfrl`, branch `fable/revtfrl`); all three cells **held**. Nothing here
authorises a flight, a flip or an admission entry. Development numbers only (owner decisions 28 and 86).

**Model-free.** Zero model, server, tokenizer, encoder, embedder, scorer-subprocess, network and GPU contacts; ports
8080 / 8081 untouched. Gold was read OFFLINE on the scoring side only (`data.slurp.load_slurp_split`), and no
utterance, transcript, gold string, Reviewer text or delivered answer is printed or persisted anywhere.

## 1. The reward signal: the Reviewer's credit table

`scripts/analysis/slurp_reviewer_credit_table.py` (read id `SAEA-SLURP-STAGE3-REVIEWER-CREDIT-TABLE-V1`, machine outputs `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-REVIEWER-CREDIT-TABLE-V1/`, numbers-only
twin [`credit-table-summary-v1.json`](credit-table-summary-v1.json)) reads every Reviewer visit of 22 sealed SLURP
arms: for each visit, the pre-review Solver draft's error class (scored offline), the Planner route that followed,
gold-free flags of the Reviewer's text (issue / endorse / none, tool narration, naming another shortlisted intent),
whether the revision changed intent or entities, and the visit's outcome (helped / hurt / neutral on intent and on the
row's entity errors). Every draft is scored with the runtime's own deliver projection and the in-process port of the
official metric; on every single-sample arm the port reproduces the sealed per-sample intent AND SLU counts of the
delivered answer on every row (625/625, 1,080/1,080, 1,000/1,000). On the grouped-Solver pools (ROLL-1, ROLL-AA,
ROLL-2, ROLL-3) the sealed score is of the unprojected committed text, so the port agrees on 94-98 % of rows; the loop
values there compare two drafts under one convention and are internally consistent. R01C and Fold A share no
recording and no utterance (checked from the committed dataset fragments).

**Pools.** SELECTION (TRAIN R01C, outside Fold A): VAR-1 PLAN / PLANR / EX-DIV / EX-K10 / EX-K30 / PER-K16C5, F10
control and empty, evidence-path control, ROLL-1, ROLL-AA (the locked Reviewer form, 6,753 visits), and the sealed
candidate-recovery control arm (the CONTRASTIVE Reviewer form, 1,010 visits). DESCRIPTIVE only: Fold A (PLAN,
PLANr, AGREE A/A, AGREE, ROLL-2, P1; R-PRIM's primitive form separately) and DEV-2000-ADDED (ROLL-3, the two PLAN DEV
arms). No candidate policy is evaluated on a descriptive pool.

### 1a. The locked Reviewer (selection pools, 6,753 visits)

| pre-review class | visits | REVISE % | revised | intent changed | intent helped / hurt | entity helped / hurt | entity-error delta |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| ALL | 6,753 | 5.45 | 355 | 130 | 64 / 9 | 79 / 53 | +13.70 |
| CORRECT | 1,661 | 2.05 | 34 | 5 | 0 / 5 | 0 / 19 | +65.14 |
| ENT-FN | 405 | 2.72 | 11 | 1 | 0 / 1 | 1 / 3 | +6.07 |
| ENT-FP | 810 | 5.56 | 43 | 0 | 0 / 0 | 17 / 1 | -32.14 |
| ENT-MIXED | 1,800 | 3.56 | 60 | 3 | 0 / 3 | 22 / 2 | -44.37 |
| INT-OFFLIST | 1,485 | 10.91 | 155 | 83 | 34 / 0 | 32 / 18 | -7.12 |
| INT-SHORTLIST | 585 | 8.89 | 52 | 38 | 30 / 0 | 7 / 10 | +26.12 |
| UNPARSED | 7 | 0.00 | 0 | 0 | 0 / 0 | 0 / 0 | +0.00 |

### 1b. The contrastive Reviewer (the sealed candidate-recovery control arm, R01C)

| pre-review class | visits | REVISE % | revised | intent changed | intent helped / hurt | entity helped / hurt | entity-error delta |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| ALL | 1,010 | 46.24 | 386 | 50 | 19 / 3 | 39 / 18 | -51.31 |
| CORRECT | 226 | 33.19 | 65 | 1 | 0 / 1 | 0 / 4 | +10.00 |
| ENT-FN | 57 | 33.33 | 16 | 1 | 0 / 1 | 0 / 0 | +0.00 |
| ENT-FP | 111 | 46.85 | 43 | 1 | 0 / 1 | 9 / 0 | -20.00 |
| ENT-MIXED | 272 | 45.22 | 101 | 0 | 0 / 0 | 14 / 5 | -22.43 |
| INT-OFFLIST | 238 | 57.14 | 110 | 36 | 12 / 0 | 10 / 7 | -11.79 |
| INT-SHORTLIST | 104 | 57.69 | 49 | 9 | 5 / 0 | 6 / 1 | -9.60 |
| UNPARSED | 2 | 100.00 | 2 | 2 | 2 / 0 | 0 / 1 | +2.50 |

### 1c. The locked Reviewer on Fold A (descriptive)

| pre-review class | visits | REVISE % | revised | intent changed | intent helped / hurt | entity helped / hurt | entity-error delta |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| ALL | 6,609 | 2.87 | 178 | 53 | 22 / 8 | 25 / 41 | +42.68 |
| CORRECT | 2,911 | 0.96 | 26 | 3 | 0 / 3 | 0 / 13 | +36.00 |
| ENT-FN | 540 | 2.22 | 12 | 1 | 0 / 1 | 3 / 4 | +0.44 |
| ENT-FP | 806 | 4.09 | 32 | 2 | 0 / 2 | 5 / 3 | -4.00 |
| ENT-MIXED | 1,165 | 1.72 | 19 | 2 | 0 / 2 | 3 / 1 | -5.82 |
| INT-OFFLIST | 801 | 8.61 | 61 | 32 | 12 / 0 | 11 / 15 | +9.05 |
| INT-SHORTLIST | 378 | 6.61 | 25 | 12 | 9 / 0 | 3 / 5 | +7.00 |
| UNPARSED | 8 | 37.50 | 3 | 1 | 1 / 0 | 0 / 0 | +0.00 |

**Where the Reviewer is useful, useless, harmful.**

- **Useful, rarely: intent repair.** When the locked loop revises a wrong-intent draft it repairs it often and almost
  never breaks a right one: 64 intent repairs against 9 intent breaks over the selection pools, 22 against 8 on Fold
  A. Its revisions of FALSE-POSITIVE-entity drafts also help (ENT-FP: 17 entity repairs, 1 harm; ENT-MIXED 22 / 2).
- **Useless, mostly: reach.** It routes REVISE on 5.45 % of visits; on drafts whose gold intent sat on Perception's
  own shortlist (the "Solver choice" class) on 8.89 %; on first visits the Planner routes REVISE on only 52 of
  the 554 such drafts (9.39 %). The text
  narrates a tool on 5,960 of 6,753 visits (88.3 %) -- the retired-tool order G5 removes --
  and a Reviewer whose text endorses the draft is followed to ACCEPT on 2,636 of
  2,653 visits.
- **Harmful, on correct drafts' entities.** Its 34 revisions of fully CORRECT drafts broke entities on 19 and intent on
  5 (entity-error delta +65.14 over the selection pools); on Fold A 26 revisions, 13 entity breaks, 3 intent breaks.
- **Net.** The loop's value over its own first drafts is small and mostly positive on intent: from
  -1.00 to
  +3.04 pp over the eleven locked selection pools, mean
  +0.738; on Fold A +0.185 (AGREE A/A) and
  -0.093 (AGREE); SLU-F1 from
  -0.748 to +0.989 over all 22 arms, most intervals spanning zero.
- **The contrastive form acts on almost every row and harms little.** It routes REVISE on 46.24 % of visits (57-58 %
  on wrong-intent drafts, 33 % on correct ones), yet its 65 revisions of correct drafts broke intent once and entities
  4 times, and over all 386 revisions it repaired intent 19 times against 3 breaks and cut the entity-error count by
  51.3. Its loop moved intent **+2.56 pp** over its own first drafts.

### 1d. The loop value per pool (delivered answer minus the same trajectory's first Solver draft)

| pool | use | rows | revision events | intent pp [CI95] | SLU-F1 pp [CI95] |
| --- | --- | ---: | ---: | --- | --- |
| agree-aa | fold-a | 1080 | 32 | +0.185 [-0.278, 0.648] | -0.187 [-0.503, 0.103] |
| agree-w1 | fold-a | 1080 | 23 | -0.093 [-0.463, 0.278] | +0.049 [-0.122, 0.215] |
| candrec | selection | 625 | 386 | +2.560 [1.12, 4.0] | +0.677 [-0.142, 1.6] |
| evpath-control | selection | 625 | 68 | +3.040 [1.6, 4.64] | +0.989 [0.343, 1.721] |
| f10-control | selection | 625 | 30 | +1.120 [0.32, 2.08] | +0.212 [-0.165, 0.624] |
| f10-empty | selection | 625 | 20 | +0.320 [-0.32, 0.96] | +0.139 [-0.142, 0.492] |
| p1 | fold-a | 1080 | 6 | +0.000 [0.0, 0.0] | +0.136 [0.0, 0.374] |
| plan-dev | dev | 1000 | 27 | +0.700 [0.2, 1.283] | +0.232 [0.0, 0.506] |
| plan-dev-r | dev | 1000 | 33 | +0.600 [0.099, 1.2] | -0.062 [-0.37, 0.282] |
| plan-lock | fold-a | 1080 | 38 | +0.463 [0.093, 0.926] | +0.146 [-0.268, 0.61] |
| planr | fold-a | 1080 | 26 | +0.370 [0.093, 0.741] | -0.118 [-0.422, 0.189] |
| r-prim | fold-a | 1080 | 11 | +0.000 [0.0, 0.0] | +0.089 [0.0, 0.207] |
| roll-1 | selection | 625 | 50 | +0.960 [0.16, 1.92] | -0.303 [-0.979, 0.288] |
| roll-2 | fold-a | 1080 | 53 | +0.370 [-0.185, 0.926] | -0.044 [-0.599, 0.528] |
| roll-3 | dev | 1000 | 32 | +0.200 [-0.298, 0.701] | +0.032 [-0.374, 0.456] |
| roll-aa | selection | 200 | 8 | -1.000 [-2.5, 0.0] | -0.748 [-2.006, 0.0] |
| var1-ex-div | selection | 625 | 35 | +0.960 [0.32, 1.76] | +0.261 [-0.327, 0.879] |
| var1-ex-k10 | selection | 625 | 28 | +0.320 [0.0, 0.8] | +0.117 [-0.255, 0.603] |
| var1-ex-k30 | selection | 625 | 26 | +1.120 [0.16, 2.08] | +0.301 [-0.195, 0.978] |
| var1-per-k16c5 | selection | 625 | 27 | +0.640 [0.0, 1.44] | +0.355 [-0.04, 0.828] |
| var1-plan | selection | 625 | 32 | +0.480 [0.0, 1.12] | +0.055 [-0.25, 0.394] |
| var1-planr | selection | 625 | 31 | +0.160 [-0.32, 0.8] | -0.149 [-0.765, 0.366] |

## 2. The optimisation design (node-scoped, training-free)

**Policy parameters of the Reviewer node.** (i) its instruction text; (ii) the evidence it is shown (today the whole
episode history: the eight boundary entries, twenty exemplars and slot cards, Perception's shortlist, the Solver
draft -- the "top-2 contrast" is already inside that history and the instruction decides whether the node uses it);
(iii) the intervention trigger (when its verdict may change the answer); (iv) the revision scope (what a revision may
change).

**Algorithm `sealed-credit-system-policy-v1`**, applied NODE-SCOPED as owner decision 165 rules it (per-node credit: the Reviewer's
revise / keep decisions and their outcomes in the sealed pools are the reward signal); its update step is a reflective
proposal in GEPA's manner (arXiv:2507.19457) restricted to one node, and every step is scored where this rig can see: (1) *rollout* -- the sealed pools already on disk and the flights
this design queues; (2) *scoring* -- offline, per draft, against gold on the scoring side; (3) *credit
assignment* -- per Reviewer VISIT, by the pre-review draft's error class; (4) *update* -- a reflective proposal of the
node's policy from the credit table (the proposer reads the table, names the failing class, and edits the policy for
it); (5) *selection* -- over sealed pools of TRAIN rows outside Fold A; (6) *context application* -- one flight of the
selected policy beside its in-chain A/A. The key property: **every trajectory seals the pre-review draft beside the
delivered answer, so the node's own effect (its loop value) is a paired within-trajectory contrast with no flight
offset** -- the between-flight band that hides small system effects does not enter the node's credit.

**What is scored offline and what needs a flight.**

Offline, exactly (zero GPU):
- WHEN a Reviewer verdict may change the answer (a gate over the sealed revision events: every gate of the grid, on each sealed pool, by re-scoring the answer the gated policy would deliver -- the pre-review draft when the gate refuses, the revised draft when it honours)
- WHAT a revision may change (scope: full, intent-only, entities-only), by merging the sealed pre-review and revised drafts and re-scoring
- the node's CREDIT per visit (helped / hurt / neutral on intent and on the row's entity errors, by the pre-review draft's error class) and its loop value over its own first drafts
- the choice between Reviewer FORMS that some sealed arm already flew, by their loop values on the same rows

Needs a flight:
- any Reviewer text or evidence view no sealed arm flew: its findings, the Planner's routing on them and the Solver's revision are new model contacts
- a trigger that makes the Reviewer act on rows where no sealed revision exists (a gate can only REMOVE sealed revisions offline, never add one)

**Round 1, run here.** The gate x scope grid (13 gates x 3 scopes over the sealed revision events, both Reviewer forms)
with a two-fold cross-fit by utterance:

- contrastive-candrec: fold 0 chose `Reviewer text raises an issue | full` -> held-out (intent, SLU) [0.0, 0.0]; fold 1 chose `all (as built) | full` -> held-out [0.0, 0.0]
- locked-v1: fold 0 chose `draft was not the exemplar-vote top | full` -> held-out (intent, SLU) [-0.024, -0.204]; fold 1 chose `Reviewer text raises an issue | full` -> held-out [-0.18, -0.002]

No gate and no scope beats honouring every revision: the existing revisions are net useful on intent and the node's
deficit is REACH, which a gate can only reduce. So the loop selects on the one dimension a sealed alternative exists
for -- the Reviewer's FORM -- by the node's own loop value on the SAME 625 R01C rows:

| form | loop value, intent pp |
| --- | ---: |
| locked (mean of 11 sealed pools) | +0.738 |
| contrastive (the candidate-recovery control arm) | +2.56 |
| **paired difference** | **+1.697 [+0.263, +3.143]** |

**The reflective update** (the proposer's edit, [`instruction-edit-proof-v1.json`](instruction-edit-proof-v1.json)):
the selected form's text, adapted to this plan and changed in nothing else --

- `replace`: "candidate proposal." -> "Perception candidates."
- `replace`: "The original" -> "Perception's"
- `replace`: "exemplar-supported additions" -> "the retrieved examples"
- `replace`: "evidence," -> "evidence and"
- `replace`: "result, and call only tools actually exposed in this turn." -> "result."
- `insert`: "" -> "request a transcript,"

`configs/probes/slurp_native_role_reviewer_contrastive_v1.txt` (sha256 `2b6de3b6cfdba2c248efc5a36e1d29b58220c09e0b673a9285cb1cf2ad51e3cf`, 194 words, 182 kept in order from the source).

**Selection data.** R01C (625 TRAIN construction rows, disjoint from Fold A); the decision-162 filler chunks, which
decision 168 places on Fold B's 1,080 TRAIN rows (outside Fold A), are the substrate of later rounds. Fold A gold entered the credit table
descriptively and never a selection.

**The read.** TRAIN Fold A 1,080, the in-chain A/A = the base (AGREE + G5's Reviewer text), intent primary, SLU-F1
guard, admitted on NO HARM, never reported as a gain; the node credit (loop value, per-class table) on both arms
beside it.

**Expectation (measured only, decision 139).** The paired difference +1.697 pp was
measured where 30.00 % of first drafts had the wrong intent; the base has 14.17 %
(AGREE, intent 85.83). A review loop acts only on wrong drafts, so the transfer is
1.697 x 0.1417 / 0.3000 = **+0.80 pp** (interval +0.12 to
+1.48). That is below the 2.5 pp cross-flight benefit bar and below the intent own-null half-width 0.9943, so
the cell claims no benefit: `admission` `no-harm`, `claims_benefit` false, `expected_effect_pp` 0.8.

**The confound.** The selection's measured object is the review loop of the sealed candidate-recovery control arm, which also changed the Planner's routing text, the Solver's instruction and the candidate proposal. This cell moves the Reviewer instruction ALONE (the brief scopes the optimisation to the node); the Planner keeps the locked routing text and the Solver the locked revision clause. The transfer is therefore an assumption stated here and tested by the read: the arm's own per-visit credit (REVISE rate per class, helped / hurt per revision, the entity-error delta on CORRECT drafts) is compared with the source arm's sealed credit, and a loop value far below the source's is read as 'the lift lived in the Planner / Solver texts', which names the next round's node.

**GPU budget.** Rate: docs/results/2026-09-27-slurp-agree-w1-fold-a-read.md: the AGREE arm's measured 1.8816 GPU-h per 1,080 rows at 4.06 contacts per row (serving monitor active seconds). Offline rounds: 0 GPU-h. This cell: smoke about 0.01 GPU-h; A/A about
1.8816 GPU-h; arm about 6,319 contacts, about 2.71 GPU-h; total about
4.6 GPU-h (caps 11,880 generation contacts and
12.0 GPU-h per cell are ceilings; smoke 44 / 1.0).
Next rounds: Reviewer variants the offline loop cannot score are flown on TRAIN rows outside Fold A (R01C, or the decision-162 filler chunks on Fold B, decision 168), K variants plus the as-built control in ONE campaign, each read by its own within-trajectory loop value: about 625 x 5.85 x 0.000429 = 1.6 GPU-h per 625-row variant, so K = 3 plus control is about 6.3 GPU-h; only the winner re-enters Fold A beside an in-chain A/A (about 4.6 GPU-h).

**Round 2 (queued by this design, not registered here).** Decision 165 names G5 as the node's first, no-harm step and
the Planner as the next node on the same route. The proposer reads REV-TFRL-1's own sealed credit table. If
the arm's REVISE reach lands near the source arm's but its correct-draft harm is higher, the next candidate is the
revision-scope text on the Solver side or the Planner's routing criterion (the source arm's other two texts), each a
one-node variant flown on R01C / filler rows in ONE campaign with the as-built control and read by loop value; if the
reach itself does not transfer, the next candidate is the Reviewer shown the top-2 contrast explicitly (a typed
evidence line: the draft's intent and Perception's strongest competitor, each with its boundary entry and exemplar
count), which needs one engineering item (a Reviewer evidence view) before it can be registered.

## 3. The registered cell

| cell | run id | Reviewer template | role |
| --- | --- | --- | --- |
| arm | `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-V1` | `probes/slurp_native_role_reviewer_contrastive_v1.txt` | the selected policy |
| in-chain A/A | `SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1` | `probes/slurp_native_role_reviewer_v1_g5_v1.txt` | the base, same chain |
| smoke | `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-SMOKE-4-V1` | `probes/slurp_native_role_reviewer_contrastive_v1.txt` | four rows, form only |

Derived by `scripts/flights/revtfrl/derive_slurp_revtfrl_cells.py` from the committed AGREE fragments; the composed-config diff against the AGREE parent is
the one pin plus bookkeeping (`registered-facts-v1.json`), re-proven by `tests/unit/test_revtfrl_config.py`. Every supply the flip mints
for the arm and the A/A must carry the sealed AGREE output digest `eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae` (the Reviewer text is not
an input to the first-phase supply). The READ row `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1` is registered with the flight (`analysis-recipe-v1.json`
`run_ids.read`).

**Mint, flip, queue.** Root countersigns the eight DRAFT exposure rows, mints `coordination/slurp-stage3-revtfrl-fold-a-v1/root-admission-v1.json` (id `slurp-stage3-revtfrl-fold-a-admission-v1`,
six eligible run ids) with `scripts/flights/revtfrl/revtfrl_mint_receipt.py`, flips with
`scripts/flights/revtfrl/revtfrl_flip.sh` (the generic re-pin loop over the three `revtfrl_repin_*.sh`, converged at one
HEAD), then queues `scripts/flights/revtfrl/batch_chain_revtfrl.sh` behind whatever occupies the np4 session (decision 77).

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-reviewer-tfrl-v1-preregistration.md` | the preregistration and the `stage3_measurement` fence |
| `credit-table-summary-v1.json` | the credit read's numbers (per pool, per class, triggers, loop values, grid, form selection) |
| `instruction-edit-proof-v1.json` | the proposer's edit list against the sealed source text |
| `registered-facts-v1.json` | every measured fact, the diffs, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the rule, the expectation, the confound |
| `*-plan-registered-v1.json` | the six flight plans |
| `analysis-recipe-v1.json` | the paired read plus the node credit; `run_ids.read` = `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1` |
| `root-admission-draft-v1.json` | the decision receipt root mints |
