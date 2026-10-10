# NX R6 under owner decision 245: node-local optimisation first, then cascade optimisation of the Perception -> Solver communication template

Author: Claude Fable 5.1 (root coordinator), 2026-10-10. Status: design of record for rounds R6-R8 of the NX programme
(`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`), written while R5 flies. Model-free: no model,
server, GPU, network or paid-API contact was made for this note; every number below is quoted from a sealed read with
its file. No utterance text, transcript, gold value, note body or model output appears here.

## 0. The owner's ruling (decision 245, 2026-10-10)

Verbatim (Chinese, chat): 「决策245：可以先各自优化后，再级联优化，各自优化过程中，不需要考虑彼此之间的连接关系。在级联优化
过程中，前置节点要考虑如何传递更有效的信息给到后置节点，这里面更重要的是优化通信模板，明确好对后续判定最有效的要素长什么
样，同时可以返回多选项连同执行度让后续节点去选择，或者后续节点把这个任务当做是一个重排序任务。你注意，这里面最重要的是提供
稳定且额外的信息增益！」

English: "Decision 245: optimise each node on its own first, then optimise the cascade. During the node-local phase,
ignore the connections between nodes. During the cascade phase, the upstream node must work out how to pass MORE
EFFECTIVE information to the downstream node; what matters most there is optimising the COMMUNICATION TEMPLATE: define
what the elements most useful to the downstream judgement look like. The upstream may also return several options
together with their confidence (執行度, read as 置信度) for the downstream node to choose from, or the downstream node
treats the task as a RE-RANKING task. Note: the most important thing is to provide STABLE and ADDITIONAL information
gain."

Coordinator's reading, recorded as the rule for R6-R8 (owner may object):

1. Two phases per cascade pair. Phase 1 (node-local): each node is optimised against a node-local metric computed at
   that node against offline gold, with the interface frozen (non-delivering arms; the downstream never sees the
   change). Phase 2 (cascade): the message from the upstream node to the downstream node is the object; candidates are
   communication templates; the downstream either consumes the message deterministically, chooses among offered
   options, or re-ranks them.
2. Acceptance in both phases is INFORMATION GAIN, defined in section 4: additional (beyond what the downstream already
   has) and stable (same sign, CI95 lower bound above zero, on two disjoint rosters). The decision-192 registration
   bar (>= 1.5 pp predicted at a measured conversion) applies where a delivered-metric claim is made (the cascade cells
   R7/R8); a node-local measurement cell (R6-P1) is judged on its node metric and its information gain, and its
   delivered-metric effect is estimated offline from its own sealed columns before any cascade cell is registered.

## 1. Facts that bound the design (code and sealed reads)

| fact | source |
| --- | --- |
| The Perception note contract `slurp-intent-hypotheses-v1` is sent to llama-server as a `json_schema` response format, so decoding is grammar-constrained: `additionalProperties: false`; `candidates` 1-3 items; each item exactly `intent_id` (enum of legal ids), `distinction` (string, `max_distinction_chars` 128), `evidence_refs` and `unresolved_fields` (arrays with `maxItems` 0 in the lock base). A key such as `entity_presence` CANNOT appear in a v1 note whatever the template asks. | `rails/artifact_results.py` (`slurp_intent_hypotheses_response_format`), `core/model/adapter.py` (json_schema wrapper), lock base `configs/baseline/slurp-native-stage3-nx-r5-composed-dev2000-added-baseline-v1.json` (`max_evidence_refs` 0, `max_unresolved_fields` 0) |
| A template arm may not change the node's response format (one axis per arm; the delivering arm is the locked path, invariant I7). A new note schema is therefore a node-contract change = a new base, not an arm. | `docs/readiness/2026-10-10-slurp-nx-perception-template-column-instrument-v1/README.md` section 7 item 3 |
| The Solver sees the Perception note VERBATIM as the Perception state's content; a level-2 branch Solver contact sees its own arm's note. | `rails/runner.py` `_perception_note_view`, `_perception_branch_solver_view` |
| The level-2 Perception template instrument gives, per arm, one Perception contact AND one Solver contact with the LOCKED Solver template over that arm's note: the node-local read and the "locked consumer" cascade read come from the same flight. Ceiling `2 + 2 (K - 1)`; Perception fit numbers measured on P-SV-4: base prompt 2,577 tokens, 149 per supplied item, completion ceiling 512, slot 24,576. | instrument README sections 1-3; `configs/baseline/slurp-native-stage3-psv4-fold-b-baseline-v1.json` |
| Perception carries NO entity information today: `evidence_refs` and `unresolved_fields` are empty on 1,080/1,080 rows of both R1 flights (AUC 0.500 for "gold empty"); note length, candidate count and distinction length are noise (0.45-0.54). | `docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md` section 3 |
| The best pre-Solver signal is the supply's entity-free exemplar share N1 (AUC 0.856 [0.832, 0.877]); TRAIN intent priors 0.73-0.75; audio duration 0.67; all pre-Solver combined 0.864; adding the lock Solver's own answer 0.893. | same, section 3 |
| A core presence verdict gated by N1 >= 0.2 (`c3verdict`) is worth **+0.75 [+0.27, +1.24]** (i1) and **+0.98 [+0.50, +1.48]** (i2) pp official SLU-F1 on the v4g base, 0 intent rows moved, false fill 91 -> 64 / 93 -> 60, 3 non-empty exact rows lost per flight. The ungated verdict +0.06 / +0.45. The deterministic gate alone +0.13 / -0.04 cross-fitted. | same, section 4 |
| Exchange rates: +0.033 pp per empty-gold false fill removed; -0.070 pp per non-empty exact row lost; +0.056 pp per raw-exact Solver row gained. | `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` |
| Rows the aggressive Solver arm lost (22 / 23): single-entity `date` / `time` / `food_type` / `media_type` rows on intents with TRAIN entity rate about 0.8, gold intent at rank 1 on 18 / 21, 14-20 entity-bearing exemplars in view; the N1 gate did not protect 17 / 22 and 18 / 23 of them. | R6 offline note section 5 |
| Solver-side empty decisions are closed under the plateau rule (R1 iterations 1 and 2 NOT NOMINATED; the gated empty decisions lost the effect: i2-c1 -0.88, i2-c2 -0.90 with false fill +9.95). Stage S (supply at the Solver) closed at +0.20 best (decision 238). | `docs/results/2026-10-10-slurp-nx-r1-i2-solver-fold-b-column-read.md`; registry rows 238-239 |
| Measurement instrument: < 200 rows = form proof; same-flight paired node column floor 1.49 pp SLU at n = 1,080 (borrowed until a node-column cell measures its own twin null); offline re-score floor 0.67 pp. | `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` |

Consequence for the channel: within the v1 contract the ONLY free Perception -> Solver channel is the `distinction`
string of each candidate (128 characters; the locked v3 template further asks for at most 12 English words) plus the
ORDER and COUNT of candidates. Confidence fields are forbidden by the v3 template text and by the schema. A richer
channel (explicit presence verdict, heard-mention options with confidence) needs a v2 note contract, which is a new
Perception base (section 3, step 2d).

## 2. Phase 1: node-local optimisation (interfaces frozen)

### 2.1 Which nodes still have a node-local objective

| node | node-local objective | state |
| --- | --- | --- |
| Perception, intent | gold on list, rank 1 | CLOSED: P-SV-1..4 levers exhausted (`docs/results/2026-10-09-slurp-psv4-fold-b-branch-read.md`); intent LOCKED at COMP-1b (decision 229) |
| **Perception, entities** | an entity-PRESENCE verdict and a HEARD-MENTION list of its own, scored at the node against offline gold | OPEN -- nothing measured yet (the node emits no entity information today). **R6-P1.** |
| Solver | raw entity exact-set per row | CLOSED under the plateau rule (R1 i1/i2); re-opens only as a CONSUMER in phase 2 |
| Supply at the Solver | exemplar / card / key variants | CLOSED (decision 238); its statistics (N1, intent prior) are consumed deterministically as gate features |
| Post-processing | delivered normaliser | LOCKED v4g (`docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md`); v5 deterministic grid rules refuted (R6 offline note, section 6) |

### 2.2 Cell R6-P1: the Perception entity column (TRAIN Fold B)

* **Instrument.** Perception template column (level-2 branch group, receipt `saea-perception-branch-arms-v4`), review-off
  module graph on the COMP-1b lock (lock v2.2 at delivery), roster TRAIN Fold B (1,080 rows, 392 empty-gold), arms
  p1, p2, p3 + twin `aa` + delivering `lock`; K = 5, ceiling 2 + 2 x 4 = 10 contacts per row, 10,800 model calls,
  about 4.1 GPU-h at the measured 44 requests per minute (np4). The delivering arm is byte-identical to the lock (I7),
  so the delivered answer is unchanged: this is a MEASUREMENT cell.
* **Channel used.** The v1 `distinction` string, with a fixed ASCII tag grammar at its head, defined once and pinned
  with the templates (the reader parses exactly this grammar):
  `E=none|some|unsure` [`; M=<type>:<spoken surface>` up to 3 mentions] `; ` <distinction of at most 8 words>. All
  within 128 characters; a candidate without the tag is `absent`, a malformed tag is `invalid`; both are counted and
  reported per arm. The tag sits on EVERY candidate so the rank-1 verdict and a list-level majority are both readable.
* **Candidates** (authored from the aggregate tables of the R6 offline note, never from utterance text; each with its
  mechanism hypothesis and the failure class it targets):
  * `p1` presence only (`E=` tag, no mentions): tests whether the core can judge "no entity expressed" from speech at
    the Perception node, where the supply is intent-boundary exemplars rather than slot exemplars; targets the 91-93
    v4g false fills per 1,080.
  * `p2` presence + heard mentions (`E=` and up to three `M=` pairs with the entity type from the legal inventory and
    the spoken surface): tests whether the node can OFFER entity options; targets the 22-23 single-entity `date` /
    `time` / `food_type` / `media_type` rows the aggressive Solver emptied and the 107/407 "value in supply, not
    delivered" class (exchange-rate note).
  * `p3` presence with a hedge (`E=unsure` allowed when speech is short or noisy) + mentions: tests whether an abstain
    option raises the precision of `none` (the gate consumer needs precision, not recall).
  * Templates live under `configs/probes/nx/perception/r6/`, byte-pinned, `template_tokens` measured; each keeps the v3
    intent instructions unchanged (coverage, legal ids, order, no padding, no confidence fields) so the intent
    guard is a fair test of the tag's cost.
* **Node-local primary metric.** On the rank-1 candidate: AUC, precision and recall of `E=none` for "gold has no
  entity"; precision and recall of `E=some` for "gold has an entity". Secondary: heard-mention containment -- the share
  of gold entities whose (type, normalised surface) appears among the arm's `M=` pairs, and the share of offered
  pairs that are gold (option precision); the `unsure` rate; tag parse rate. Guards (paired against `lock`): gold on
  list, rank-1 share, candidate count, prompt tokens, `note_parse_status`; a guard moving by more than the twin's own
  movement plus 0.65 pp fails the arm.
* **Information-gain read (section 4) from the same columns, 0 GPU.** (i) Additional: cross-fitted AUC of
  {N1, intent prior, arm verdict} minus cross-fitted AUC of {N1, intent prior} for "gold empty", with a cluster
  bootstrap CI; the arm passes if the lower bound is above zero. (ii) Delivered-metric estimate: the R6 offline
  driver's `c3verdict` rule with the verdict source swapped from the Solver arm to the Perception arm (`E=none` on the
  rank-1 candidate), gated by N1 >= 0.2 and by the sweep's cross-fitted alternatives, applied to the lock Solver
  column on the v4g base: pp with CI, false fills removed, non-empty exact lost, intent rows moved (must be 0).
  (iii) Locked-consumer read: each arm's own level-2 Solver column (the locked Solver template reading the tagged
  note) against lock's Solver column -- false fill on empty-gold, non-empty exact, normalised exact-set, intent rows
  moved. This answers, for free, whether the Solver already uses the tags when it sees them.
* **Declared expectation (decision 192 form, measurement cell).** Node metric: `E=none` recall >= 0.80 and precision
  >= 0.75 on empty-gold rows (the Solver-side c3 verdict measured 0.81-0.83 / 0.74-0.76); information gain: cross-fit
  AUC increment > 0 (CI-LB); delivered-metric estimate via the gate +0.75..+0.98 pp IF the Perception verdict matches
  the c3 verdict's quality, less if it only mirrors N1. The arm's own exchange: each false fill the gate removes
  +0.033, each exact row lost -0.070.
* **Plateau rule.** Two evaluated Perception-entity rounds without an arm clearing the node-local acceptance close the
  node; the next lever is then the v2 contract (2d) or the supply-side presence prior, in that order.

### 2.3 Exposure

Fold B is the selection roster (decision 229/231 discipline: Fold B selects, Fold A confirms, DEV composes, test only
under a signed allowance). Fold B's cumulative exposure after R1 i1/i2 and P-SV-4 is recorded in the exposure ledger;
R6-P1 adds one more exposure of the same 1,080 rows. Gold enters only the offline reader through the governed loaders.

## 3. Phase 2: cascade optimisation of the Perception -> Solver message

### 3.1 The elements the downstream judgement needs (the message schema, in priority order)

| element | why (measured) | form in v1 (distinction tag) | form in v2 (contract change) |
| --- | --- | --- | --- |
| presence verdict with reliability | the gate consumer converts recall x precision into +0.033/-0.070 exchanges; N1 alone AUC 0.856, the Solver's own verdict 0.81 | `E=none|some|unsure` on each candidate; list majority = reliability proxy | `entity_presence: none|some|unsure`, `presence_confidence: high|low` |
| heard-mention options (type + spoken surface) | 107/407 delivered errors had the value in the supply; the lost rows are single `date`/`time`/`food_type`/`media_type` mentions the Solver dropped | up to 3 `M=type:surface` pairs | `heard_mentions: [{type, surface, confidence}]`, up to 6, ordered |
| intent options in order | exists today (1-3 candidates, rank 1 = 97.6 % of the correct deliveries) | unchanged | unchanged; order = confidence |
| what is UNRESOLVED | lets the downstream know what to verify rather than invent | `E=unsure` | `unresolved_fields` re-enabled (maxItems > 0) |

"Confidence" is encoded as ORDER plus a two-level tag; numeric probabilities are not asked for (the v3 ban stands:
the core's self-reported numbers were never calibrated here).

### 3.2 Consumers, cheapest first

* **2a. Deterministic consumer at delivery (0 GPU, from R6-P1).** The `verdict x N1 gate` rule becomes a registered
  delivery component (`saea-deliver-normalise-v4g` + `presence-gate-v1`), its parameters selected on Fold B and
  confirmed on Fold A (section 3.3). This is the shortest path to a delivered gain and it changes no template of the
  Solver.
* **2b. The locked Solver as consumer (0 GPU, from R6-P1).** The level-2 Solver columns show whether the v2 Solver
  template already uses tagged notes. If it does (CI-LB > 0 on normalised exact-set or false fill with no non-empty
  loss), the tagged Perception template alone is a cascade candidate.
* **2c. The Solver as chooser / re-ranker (R7, about 3 GPU-h).** A Solver template column (E1 Solver form) on the base
  whose Perception template is the Phase-1 winner (Fold A-confirmed), K <= 4 wordings that (i) treat `M=` pairs as
  options to VERIFY against the speech and choose among, never to invent from; (ii) treat `E=none` as a reason to
  return an empty list unless the speech contradicts it; (iii) re-rank: list every heard option the Solver confirms,
  in spoken order. Read with the Solver column reader; nomination rule of the NX programme (official pooled SLU-F1
  vs lock CI-LB > 0, above the twin, intent guard <= 7 rows).
* **2d. The v2 note contract (engineering, conditional).** Registered only if 2a-2c show that the verdict or the
  options carry gain but the 128-character channel is the binding constraint (tag parse rate low, mentions
  truncated, intent guard failing because the distinction lost its words). It is a Perception node-contract change
  (`slurp-intent-hypotheses-v2`: `max_evidence_refs` / `max_unresolved_fields` > 0 or the two new keys), hence a new
  base with its own A/A, not an arm.

### 3.3 Confirmation and composition

* **R6-A (Fold A, two arms, about 1.3 GPU-h):** the selected Perception template vs lock on TRAIN Fold A (1,080) with
  the in-chain twin; the gate parameters fixed from Fold B; read = node metric, information gain, and the
  delivered-metric estimate of the gate on Fold A. A lock of the Perception template and of `presence-gate-v1` needs
  CI-LB > 0 on BOTH folds for the information-gain term (stability) and no intent movement.
* **R8 (DEV-2000-ADDED, composed, about 2.5 GPU-h):** lock v2.3 = v2.2 + Perception template + presence gate (+ R7
  Solver consumer if nominated) vs lock v2.2 with the in-chain replicate; bar = the cross-flight / composed bar of the
  programme; NOMINATED -> the next test-sample allowance (decision 241 terms).

## 4. The information-gain criterion (the acceptance rule of this design)

For a message element m sent from node U to node D about decision d (here: "the gold entity list is empty"; later:
"this heard option is a gold entity"), with baseline features B that D already has (the supply statistics N1 and the
intent prior; for the delivered estimate also D's own answer):

* **Gain** g(m) = AUC_cf(B + m) - AUC_cf(B), cross-fitted over two utterance-hash halves so no row is scored by a model
  that saw it; CI95 by whole-utterance cluster bootstrap (2,000 draws for AUC, 10,000 for pp contrasts; seeds
  20261010 / 20260915 as in the R6 offline driver).
* **Additional** = CI-LB of g(m) > 0 on the selection roster, AND the delivered-metric estimate through the registered
  consumer (the gate, or the Solver column) has CI-LB > 0 after conditioning on D's own verdict (the post-Solver
  combination, today 0.893 ceiling), so that m is not merely a re-statement of what D already decides.
* **Stable** = the same sign and CI-LB > 0 on the confirmation roster (Fold A) with the rule FIXED on Fold B, and the
  intent guard at zero rows moved; for a composed lock, reproduced on DEV-2000-ADDED against the in-chain replicate.
* **Exchange** = every accepted element states its pp through the measured exchange rates (false fill +0.033,
  non-empty exact -0.070, raw-exact +0.056 per row of 1,080), so the registration bar of the cascade cell is a
  prediction at a measured conversion (decision 192 form).

An element that is informative but unstable (sign flips across folds, or gain only on one utterance-hash half) is
recorded and NOT locked; an element that is stable but not additional (mirrors N1) is dropped.

## 5. Round plan, cost, order

| round | object | roster | GPU-h | reads | gate to the next |
| --- | --- | --- | ---: | --- | --- |
| R5 (flying) | composed read, lock v2.2 | DEV-2000-ADDED | ~2.3 | official | its verdict (NOMINATED -> test allowance; carriers stay held) |
| **R6-P1** | Perception entity column, p1-p3 + twin + lock | TRAIN Fold B | ~4.1 | node metric; information gain; gate estimate; locked-consumer columns (all from one flight) | an arm passes node acceptance AND additional gain |
| R6-A | selected Perception template vs lock, 2 arms + twin | TRAIN Fold A | ~1.3 | same, rule fixed on Fold B | stable on both folds -> lock template + `presence-gate-v1` |
| R7 | Solver consumer column, K <= 4 | TRAIN Fold B | ~3.2 | Solver column reader, NX nomination rule | CI-LB > 0 vs lock -> Fold A confirm (~1.3) |
| R8 | lock v2.3 vs v2.2, in-chain replicate | DEV-2000-ADDED | ~2.5 | composed read | NOMINATED -> allowance draft |

About 12-15 GPU-h over the next 10 days at one experiment in flight. R6-P1 is registered during the R5 read and flies
as soon as R5's GPU is free (SLURP-only GPU, decisions 187/242). If R6-P1 plateaus (two rounds), the Perception-entity
node closes and the order becomes 2d (v2 contract) then the supply-side presence prior (predicted about +0.1 pp, R6
offline note item 6), i.e. the system is asked again for a different upstream input, per decision 239.

## 6. Engineering prerequisites (model-free; built after R5 seals, no code agents on the tree during a campaign)

1. **Tag grammar + reader (E2b).** `scripts/analysis/slurp_nx_perception_column_read.py` gains a `distinction_tag`
   parser (`E=` / `M=` grammar above) beside the `entity_presence` key reader; outputs per arm the presence metrics,
   mention containment / option precision, parse / invalid rates; synthetic-record tests. The grammar text is pinned
   under `configs/probes/nx/perception/r6/TAG-GRAMMAR-v1.md` and quoted by every template.
2. **Information-gain driver.** `scripts/analysis/slurp_nx_r6_upstream_empty.py` gains `--verdict-source
   perception-arm:<arm>` and `--gain-baseline {n1,n1+prior,n1+prior+lock}`; outputs the cross-fitted AUC increment
   with CI and the gate estimate per arm; reuses the v4 driver's `load_gold`, `pooled`, `Bootstrap`.
3. **R6 family scripts.** `scripts/flights/nx/nx_r6_*` cloned from the R1 family with `node = perception` (derive,
   registration writer copying the minted baseline pin, mint receipt, loop-form flip, batch chain, dry run, read
   wrapper); `tests/unit/test_nx_r6_cell_registration.py` (model-free preflight: ceiling, FIT cap, budget, twin,
   receipt ids, program id `phase-native-module-v1-c10`).
4. **Fit numbers** measured on the cell's own `native_contact_fit` pass at ceiling 10 (P-SV-4's 2,577 / 149 / 512 are
   the prior; Perception contacts are far below the slot, the level-2 Solver contacts are bounded by the realised
   gate as today).
5. **Candidates** p1-p3 authored by the coordinator from the aggregate tables (section 2.2), reviewed against the
   refusal list (no supply knob, no response-format change, under 128 characters per candidate string, no
   confidence numbers), `template_tokens` measured, READMEs with mechanism hypotheses.
6. **Registration package** `docs/readiness/2026-10-1x-slurp-nx-r6-perception-fold-b-v1/` with `stage3_measurement`
   (`same-flight-node-column`, `template_variants.node = perception`, candidate_arms 3, twin true, the declared
   expectation of section 2.2), preregistration fence, ledger rows, countersign -> mint -> flip (then the registered
   plan-pin refresh + second flip) -> gate -> chain.

## 7. Risks and how the design meets them

| risk | mitigation |
| --- | --- |
| Overloading `distinction` costs intent (the Solver reads the same string to choose the intent) | intent guards paired against lock and the twin in the same flight; p1 (tag only) isolates the cost of the tag from the cost of mentions |
| The core ignores the tag instruction under the grammar | parse / invalid rates are first-class outputs; an arm under 90 % parse is reported as a form failure, not a verdict |
| The verdict merely mirrors N1 (not additional) | the cross-fitted increment over {N1, prior} is the acceptance term; a mirror gives 0 and is dropped |
| Mentions are truncated by 128 characters | p2 limits to 3 pairs; truncation rate is reported; a high rate is the trigger for 2d |
| Fold B re-exposure | recorded as cumulative exposure; selection on Fold B, confirmation on Fold A, composition on DEV |
| Spending GPU on a measurement cell under the 1.5 pp bar | the owner's 245 phase-1 rule (node-local, interfaces ignored); the delivered estimate is still produced offline before any cascade cell is registered |

## 8. Decisions requested (registry rows 246-248, PROPOSED)

* **246** Register and fly R6-P1 as designed (three Perception candidates + twin + lock, TRAIN Fold B, ~4.1 GPU-h,
  node-local measurement with the free locked-consumer cascade read) as the next flight after the R5 read.
  Recommended: yes.
* **247** Adopt section 4 as the acceptance rule of node-local and cascade rounds (information gain: additional and
  stable, with the exchange-rate pp statement); decision 192's 1.5 pp bar binds the cascade cells that claim a
  delivered gain (R7/R8), not the node-local measurement cell. Recommended: yes.
* **248** The v2 note contract (`slurp-intent-hypotheses-v2`, explicit presence and heard-mention options with a
  two-level confidence) is engineered only on the 2d trigger (gain present, channel binding), as a new Perception
  base with its own A/A. Recommended: conditional, as stated.
