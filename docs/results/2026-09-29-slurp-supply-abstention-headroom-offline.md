# SLURP supply-side abstention headroom (owner decision 199): no score-threshold rule gains; the entity-free exemplar share is the only supply signal that separates zero-gold rows (DESCRIPTIVE, offline)

Date: 2026-09-29. Read id `SAEA-SLURP-SUPPLY-ABSTENTION-HEADROOM-OFFLINE-V1`, recipe
`slurp-supply-abstention-headroom-offline-v1`. Written by Claude Fable 5.1, the analysis agent, in worktree
`fable/emptysupply` (base master `f26e3cdbb`).

The brief is owner decision 199 (2026-09-29): a slot may be none, and retrieval must be allowed to return EMPTY
instead of always k items. Today every supply node pads:

- 20 TRAIN exemplars to the Solver;
- 8 intent-boundary entries to Perception;
- the slot-contract view.

The question is how much official SLU-F1 (and what intent risk) a SUPPLY-SIDE abstention rule could address, measured
offline.

**Status: DESCRIPTIVE.** These are development numbers on TRAIN Fold A, a construction roster (owner decisions 28
and 86). No test, generalisation or superiority claim is made, and the verdict word belongs to the coordinator.

The read made zero contacts of every kind: model, server, tokenizer, encoder, embedder, GPU, network, paid API. It ran
no official-scorer subprocess. `core.flight.cli` and `lease_cli` were not invoked.

- **Gold.** Gold entered only offline, through the governed TRAIN loader `data.slurp.load_slurp_split`.
- **What is never printed or persisted.** Utterance text, transcripts, gold values, fillers, exemplar text and model
  output.
- **What appears.** Only ids, counts, rates, AUCs, pp, scenario names and hashes.

**Driver and outputs.**

- Driver: `scripts/analysis/slurp_supply_abstention_headroom.py`, sha256
  `6ccd2f2e623f6cae53308108265244953dcab58d424b426237cb9e3302f07e77`.
- Unit test on fakes: `tests/unit/test_slurp_supply_abstention_headroom.py` (11 passed).
- Machine outputs: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SUPPLY-ABSTENTION-HEADROOM-OFFLINE-V1/`. It holds
  `report.json`, `tables.md` and `content-sha256.json`. Every number below comes from `report.json`; the key is named
  in brackets.
- `--check` re-derived both files IDENTICAL apart from `generated_at`. The content hashes (with `generated_at`
  removed) are:
  - `report.json` `51d892e869cbbb386297134bd47469d07728b29979190f25d5cfbb788077a79c`;
  - `tables.md` `37666afdc448bc1c3f9c8a8a4322a4cb510094267338c8c1f9e067ae8e2804b1`.

The driver reuses the SLU consumption headroom driver's `Rescorer`, `pooled_f1`, `gain_pp`, `trade_pp`, `ngrams` and
`drop_preds`. That note's 89 / 81 row-shown untagged counts are asserted on every run.

**What this note does not claim.**

- It does not claim that any abstention rule works or fails in flight.
- Every "oracle" is an exact in-process re-score under the stated counterfactual: every support-losing prediction
  vanishes, or the Solver answers no entity on a gated row.
- Every "expected" figure multiplies that oracle by the M1 delivered-filler conversion 0.2471
  (`docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md:51`). M1 is an analogue, not a measurement of
  withdrawing supply.
- Nothing here measures how the frozen core behaves when it receives fewer exemplars. The "phrase support" proxy is
  the brief's own accounting: an entity whose value string appears in the delivered exemplars.

## 1. Score availability

Six sealed pools were read. The five Fold A arms share the same 1,080 rows:

- AGREE `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (SLU-F1 65.1575), the primary arm;
- its A/A `...-AGREE-AA-...` (63.3115);
- the wave A/A `...-WAVE1-AA-...` (64.1566);
- the COMP-1 A/A (64.2143);
- COMP-1 seal-only (61.9701).

The sixth pool is the two filler Fold B chunks C01 and C02 (180 rows each). [`arms`, `phases`, `fold_b_pools_score_availability`]

| supply node | per-item score persisted? | where | what the score is |
| --- | --- | --- | --- |
| Solver exemplars (k 20) | **yes**, for every delivered item | sealed `phases.json`, `waves[].rank_result.candidates[].score` of the Perception wave. Serialised at `src/speech_aware_evidence_acquisition/rails/runner.py:859-861`. The composite ranker passes each store's scores through unchanged (`rails/knowledge_stores.py:1932-1950`). | `w_cos * max_cosine` with `w_cos` 1, `w_agree` 0, `w_prior` 0 (`rails/kb_policy.py:1001-1004`). This is the cosine between the row's sealed speech vector and the Omni-Embed-Nemotron text key of each exemplar. The flown spec is `configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json`, `train-exemplars.phase_supply.solver`. |
| Perception boundary block (8) | **no**, ids only | Held in `initial_query_state.retrieved_value_ids`, the prepared artifact `prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/phase-supply-v2.json` (`output.values.perception`, ids only), and the trace SUPPLY record (ids only, `rails/runner.py:6606-6632`). The bootstrap selection returns ids only (`rails/phase_supply.py:1608-1614`). The E21w rank recorder runs only when `native_episode.knowledge_index` is armed (`rails/phase_supply.py:1370`, default `None` at `:1454`). It is not armed in this cell. | Recomputed model-free: `w_cos * max_cosine + w_agree * agreement` with both weights 1 and recall k 60 (`kb_policy.py:1001-1004`). The cosine is the maximum over segments (`kb_policy.py:718-748`). The inputs are the pinned facet vectors, segment query vectors and agreement table, through the production constructor `rails.phase_supply._provider_factory`. Checks: recomputed top-8 = sealed block on **1,080 / 1,080**, and = prepared supply on 1,080 / 1,080. This is a pure function of sealed vectors, with no embedder contact. [`boundary.checks`] |
| Slot-contract view | **no similarity score** | The same `rank_result`, `slot-contracts::` entries. | Ordinal integers n..1 on 1,080 / 1,080 rows (`contract_scores_are_ordinal_integers`), from `saea-ranked-candidate-round-robin-v1` (`rails/knowledge_provider.py:1440`). The order carries no evidence strength, so no threshold rule exists for it. |
| `rank_weights` terms | exemplar: only the cosine term is non-zero; boundary: cosine + agreement | as above | The terms are not persisted separately. The boundary total is recomputed. |

Coverage across pools:

- The exemplar ranked list (ids and scores) is **byte-identical to AGREE's on 1,080 / 1,080 rows** in the AGREE A/A,
  the wave A/A and the COMP-1 A/A. [`exemplar_ranked_list_identical_to_agree_rows`]
- COMP-1 seal-only has no `phases.json`. Its exemplar supply is identical to the comparator's on 1,080 / 1,080 rows
  (`git show fable/comp1slu:docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md`, section 3 "Exemplars"), so
  AGREE's scores apply.
- Both filler Fold B chunks persist exemplar scores on 180 / 180 rows at width 20. They are Fold B five-sample
  rollout pools and are not used for the abstention arithmetic below.

The exemplar scores are narrow, with top-1 quantiles 5 / 50 / 95 % = 0.245 / 0.373 / 0.480. The top-1 / top-2 margin
median is 0.0084. [`exemplar_score_distribution`, `feature_medians`]

## 2. Separability

AUC is P(score of a positive > score of a negative). A value below 0.5 means the low end of the score marks the
positive. The CI95 is a row bootstrap (2,000 draws, seed 20260929). [`separability_exemplar`, `boundary.separability`]

### 2.1 Solver exemplar supply (k 20), AGREE

| feature | no gold entity (414 of 1,080) | row emitted a SPURIOUS entity (227) | within the 414: zero-gold row emitted (159) |
| --- | --- | --- | --- |
| top-1 score | 0.518 [0.484, 0.554] | 0.399 [0.360, 0.440] | 0.322 [0.270, 0.377] |
| mean of top 5 | 0.522 [0.488, 0.559] | 0.404 [0.365, 0.445] | 0.320 [0.270, 0.375] |
| margin top-1 minus top-2 | 0.470 [0.434, 0.505] | 0.448 [0.407, 0.492] | 0.478 [0.421, 0.536] |
| spread top-1 minus top-20 | 0.467 [0.432, 0.502] | 0.428 [0.387, 0.471] | 0.441 [0.383, 0.498] |
| *entity-free share of the 20 exemplars (content, not a score)* | ***0.846 [0.821, 0.870]*** | 0.582 [0.539, 0.621] | 0.345 [0.291, 0.397] |

- **No retrieval score separates zero-gold rows.** Every CI contains 0.5 or sits next to it.
- **A low top-1 score marks rows that emit a spurious entity** (AUC 0.40; 0.32 inside the zero-gold rows). This is
  the direction in which abstaining would help. The replicate arms give the same picture:
  - top-1 AUC for "emitted a SPURIOUS entity" is 0.415 (AGREE A/A), 0.401 (wave A/A), 0.411 (COMP-1 A/A) and 0.445
    (COMP-1);
  - the entity-free share gives 0.569 to 0.586 on the three A/As and 0.676 on COMP-1.
- **The entity-free share is the one strong signal.** The median share is 0.35 on zero-gold rows and 0.05 on
  gold-entity rows.
- **Inside the zero-gold rows, a HIGHER entity-free share goes with LESS emission** (AUC 0.345). The Solver already
  follows that signal on part of the rows.

### 2.2 Perception boundary block (recomputed scores)

The gold intent is off the 8-entry block on **40** rows. **34** of those are among the 153 AGREE intent-wrong rows.
This reproduces the ledger's 34 (`docs/results/2026-09-28-slurp-node-information-gain-ledger.md:109`). Gold rank when
off the block: 9-12 on 7 rows, 13-20 on 6, 21-60 on 21, not recalled on 6. [`boundary`]

| feature | gold off block, all rows (40) | gold off block, among intent-wrong rows (34 of 153) | AGREE intent wrong (153) |
| --- | --- | --- | --- |
| top-1 boundary score | **0.152 [0.090, 0.228]** | 0.326 [0.222, 0.444] | **0.186 [0.155, 0.222]** |
| margin top-1 minus top-2 | 0.204 [0.142, 0.272] | 0.396 [0.285, 0.519] | 0.216 [0.184, 0.250] |
| 8th score | 0.482 [0.382, 0.583] | 0.576 [0.461, 0.686] | 0.473 [0.427, 0.519] |
| gap 8th minus 9th | 0.478 [0.385, 0.575] | 0.471 [0.360, 0.578] | 0.507 [0.454, 0.558] |

- **A low top boundary score strongly marks an off-block gold** (inverted AUC 0.85) and a wrong intent (0.81).
- **The marginal scores carry nothing.** The 8th score and the 8-9 gap are near 0.5, so a "cut the block at τ" rule
  has nothing to cut on.
- **The signal says "widen or re-query", not "deliver less".** The rows where the block is weakest are those whose
  gold lies outside it.

### 2.3 Slot-contract view

The view carries only ordinal scores (section 1). Separability is not defined for it.

## 3. Abstention rules on the Solver exemplar supply

A delivered prediction **loses support** under a rule when at least one delivered exemplar carries its phrase and no
retained exemplar does. Three phrase definitions are reported:

- **anywhere** (primary; the brief's wording);
- **tagged**, inside a slot filler;
- **untagged**, the headroom note's row-shown definition.

**Support recount on AGREE** [`support_recount.agree`]:

| class | total | supported anywhere | tagged | untagged (headroom note) |
| --- | --- | --- | --- | --- |
| SPURIOUS | 253 | 161 | 109 | **89** (reproduced) |
| exact | 534 | 407 | 400 | **81** (reproduced) |
| partial | 234 | 113 | 87 | 43 |

- Of the 178 spurious entities on zero-gold rows, 112 are supported anywhere.
- Exemplar support sits beside correct entities more often than beside spurious ones: 407 of 534 exact entities are
  supported, against 161 of 253 spurious. Withdrawing supported exemplars therefore puts more correct mass at risk
  than spurious mass.

**Rules and grids.** The grids were fixed in code; τ sits at quantile levels of gold-free score distributions.

| rule | what is withheld |
| --- | --- |
| R1 | the whole block when top-1 < τ |
| R1m | the whole block when mean top-5 < τ |
| R2 | every item below τ |
| R3 | all but the top m (1 or 5) when margin top-1 minus top-2 < τ |
| R4 | added after the section 2 AUC table: when the entity-free share ≥ θ, keep only the entity-free exemplars |

**Cross-fit.** τ is chosen on one sha256(utterance id) half (541 / 539 rows) and applied to the other. The two
out-of-half results are combined into one 1,080-row re-score.

**The pp conversion is exact at AGREE's totals.** One FP is worth 0.0296 pp and one FN 0.0612 pp
(`answer_side.fp_marginal_pp_at_agree_totals`, `fn_marginal_pp_at_agree_totals`). This is inside the brief's
0.0265-0.0292 FP range (at COMP-1 and A/A totals) and its ≈0.06 FN.

### 3.1 τ sweep summary (primary definition) [`sweeps["agree/anywhere"]`]

| rule, setting | rows abstained (zero-gold / gold) | spurious removed | exact lost | partial lost | delivered-intent support to 0 (correct / wrong rows) | gross pp | harm pp | **oracle net pp** | net at M1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1, q 0.05 (τ 0.245) | 54 (17 / 37) | 11 | 10 | 2 | 39 / 12 | +0.33 | -0.63 | **-0.31** | -0.08 |
| R1, q 0.20 (τ 0.309) | 216 (76 / 140) | 37 | 52 | 18 | 160 / 47 | +1.11 | -3.63 | **-2.54** | -0.63 |
| R1, q 0.50 (τ 0.373) | 540 (200 / 340) | 98 | 162 | 50 | 424 / 99 | +3.04 | -11.83 | **-9.00** | -2.22 |
| R1m, q 0.05 | 54 (16 / 38) | 9 | 11 | 2 | 37 / 13 | +0.27 | -0.67 | **-0.40** | -0.10 |
| R2, q 0.10 (τ 0.234) | 44 (14 / 30) | 13 | 13 | 2 | 34 / 13 | +0.39 | -0.82 | **-0.43** | -0.11 |
| R2, q 0.50 (τ 0.337) | 330 (115 / 215) | 72 | 112 | 42 | 264 / 84 | +2.20 | -8.03 | **-5.90** | -1.46 |
| R3, m 5, q 0.10 | 0 | 6 | 4 | 4 | 2 / 7 | +0.18 | -0.31 | **-0.14** | -0.03 |
| R3, m 1, q 0.20 | 0 | 33 | 29 | 12 | 28 / 14 | +0.99 | -2.06 | **-1.08** | -0.27 |
| R4, θ 0.5 | 0 (1,080 slot-bearing exemplars withheld) | 8 | 3 | 2 | 1 / 2 | +0.24 | -0.20 | **+0.04** | +0.01 |
| R4, θ 0.3 | 0 (3,257 withheld) | 24 | 20 | 5 | 8 / 10 | +0.72 | -1.31 | **-0.60** | -0.15 |

- **Every R1 / R1m / R2 / R3 setting is net negative.** The net-maximising τ is "no abstention" (q 0, net 0.00) in
  every family, under all three support definitions.
- The one in-sample exception is R1 q 0.15 under the narrow untagged definition, at +0.29. [`sweeps["agree/untagged"]`]
- Row abstention always takes out more gold-entity rows than zero-gold rows: 37 against 17 at the lightest setting.
  This is what the AUC of about 0.52 predicts.
- **Intent side effect.** At R1 q 0.05, 39 intent-correct rows lose every exemplar of their delivered intent. Only 12
  intent-wrong rows do, and those are the rows where it could help.

### 3.2 Best rule, CI and cross-fit [`best_in_sample_primary`, `best_per_family_in_sample_primary`, `crossfit_primary`]

| rule family | in-sample best (net pp) | cross-fitted choice (half 0 / half 1) | **cross-fitted oracle net pp [CI95]** | at M1 |
| --- | --- | --- | --- | --- |
| R1 (top-1) | q 0: 0.00 | q 0 / q 0 | **0.00 [0.00, 0.00]** | 0.00 |
| R1m (mean top-5) | q 0: 0.00 | q 0 / q 0 | **0.00 [0.00, 0.00]** | 0.00 |
| R2 (item threshold) | q 0: 0.00 | q 0 / q 0 | **0.00 [0.00, 0.00]** | 0.00 |
| R3 (top-m on small margin) | q 0: 0.00 | q 0 / q 0 | **0.00 [0.00, 0.00]** | 0.00 |
| R4 (entity-free share gate) | θ 0.5: +0.04 [-0.26, +0.33] | θ 0.5 / θ 0.9 | **-0.03 [-0.21, +0.12]** | -0.01 |

**The τ that maximises net pp is "deliver all 20" for every score rule. The net at that τ is 0.00, and the cross-fit
confirms 0.00.** Supply-side abstention on the exemplar channel, as a withdrawal of phrase support, **cannot reach
1.5 pp**. Its best cross-fitted value is 0.00, and its best in-sample value is +0.04 (R4).

The row-abstention bound over zero-gold rows alone assumes every spurious entity on an abstained zero-gold row
vanishes. It reaches +1.55 pp only at R1 q 0.20. That setting abstains 140 gold-entity rows, whose -3.63 pp harm is
excluded from the bound. [`row_abstention_zero_gold_upper_bound`]

### 3.3 The supply "none" signal used as a gate (N1) [`n1_none_share_gated_empty_answer`]

Decision 199 read literally is "let the retrieval say none". The one supply-side signal that separates zero-gold rows
is the entity-free share. **N1** takes it as the trigger for an explicit empty-entity answer on the gated rows. The
oracle assumes the Solver answers no entity on every gated row; the intent is unchanged.

| θ | rows gated (zero-gold / gold) | spurious removed | exact lost | partial lost | oracle net pp | net at M1 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.9 | 22 (22 / 0) | 5 | 0 | 0 | +0.15 | +0.04 |
| 0.8 | 51 (49 / 2) | 11 | 1 | 1 | +0.30 | +0.07 |
| 0.7 | 91 (87 / 4) | 19 | 2 | 1 | +0.47 | +0.12 |
| **0.6** | **128 (122 / 6)** | **28** | **3** | **1** | **+0.68 [+0.28, +1.10]** | **+0.17** |
| 0.5 | 176 (156 / 20) | 43 | 10 | 4 | +0.65 | +0.16 |
| 0.4 | 254 (203 / 51) | 65 | 24 | 14 | +0.32 | +0.08 |
| 0.3 | 348 (269 / 79) | 101 | 39 | 23 | +0.33 | +0.08 |

- **The gate is precise.** At θ 0.6, 122 of the 128 gated rows are zero-gold.
- **AGREE already emits little there.** Only 28 spurious entities sit on those rows.
- **Cross-fit.** The halves choose θ 0.5 and θ 0.3; the cross-fitted oracle is +0.01 [-0.91, +0.91]. The halves
  disagree between the flat 0.3-0.6 plateau and its low end, so this number carries no signal either way.
- **Decode replicates at θ 0.6.** The same rows are gated on every arm:

  | arm | oracle net pp | spurious removed |
  | --- | --- | --- |
  | AGREE A/A | +0.59 [+0.27, +0.97] | 23 |
  | wave A/A | +0.56 [+0.19, +0.96] | 24 |
  | COMP-1 A/A | +0.61 [+0.27, +0.97] | 25 |
  | **COMP-1** | **+1.78 [+1.23, +2.36]** | **70** |

  Under the cited-answer contract, which forces emission, the gated rows carry 2.5 times the spurious mass.

**Per-stratum table for the best supply-signal rule** (N1 θ 0.6 on AGREE; within-stratum pooled SLU-F1 change)
[`n1_none_share_gated_empty_answer.best_strata_by_scenario`]. The other 11 scenarios gate 0-2 rows each at 0.00 pp.

| scenario | rows | zero-gold rows | gated | gated zero-gold | spurious removed | exact lost | pp in stratum |
| --- | --- | --- | --- | --- | --- | --- | --- |
| music | 60 | 44 | 35 | 33 | 12 | 1 (+1 partial) | +9.04 |
| audio | 60 | 50 | 36 | 35 | 5 | 1 | +7.03 |
| general | 60 | 50 | 16 | 14 | 5 | 0 | +3.50 |
| lists | 60 | 34 | 15 | 15 | 3 | 0 | +2.42 |
| alarm | 60 | 24 | 4 | 4 | 3 | 0 | +1.63 |
| qa | 60 | 22 | 9 | 8 | 0 | 1 | -1.13 |
| iot | 60 | 29 | 7 | 7 | 0 | 0 | 0.00 |
| other 11 scenarios | 660 | 161 | 6 | 6 | 0 | 0 | 0.00 |

The gain is concentrated in audio / music / general / lists. These are the scenarios where COMP-1's forced emission
landed (the harm-attribution note, section 4).

## 4. Answer-side none (B4 re-examined under decision 199) [`answer_side`]

**Zero-gold emission across the sealed arms** (of the 414 zero-gold rows; spurious entities on those rows in
brackets):

| arm | zero-gold rows emitting |
| --- | --- |
| AGREE | 159 (178) |
| AGREE A/A | 167 (187) |
| wave A/A | 165 (188) |
| COMP-1 A/A | 162 (186) |
| COMP-1 | **252 (288)** |

These reproduce the harm-attribution note's 159 / 167 / 162 / 252.

**Measured forced-emission sensitivity.** Row flips of emit / no-emit on the 414 zero-gold rows:

- **COMP-1 vs its A/A: 103 rows emit only under COMP-1, 13 only under the A/A.** The net shift is 90 rows (21.7 % of
  414), carrying 102 spurious entities.
- Same-bytes pairs flip 21-33 rows each way: AGREE vs AGREE A/A 25 / 33, AGREE vs wave A/A 21 / 27, COMP-1 A/A vs
  AGREE A/A 22 / 27, wave A/A vs AGREE A/A 31 / 33.
- A Solver contract therefore moves about a fifth of the zero-gold rows beyond decode noise. That is the measured
  range a "none" option in the contract could plausibly move, in the other direction.

**Headroom:**

| target | fp removed | gross pp | net pp at the F10 harm ratio (0.591 exact lost per FP; `docs/results/2026-09-25-slurp-f10-complete-verdict.md:18-21`) |
| --- | --- | --- | --- |
| COMP-1 back to its A/A's zero-gold rate (row swap of sealed counts) | 102 | **+2.83** | -- (a swap; reproduces the harm note's +2.83) |
| AGREE: halve zero-gold emission (159 -> 79.5 rows) | 89 | **+2.75** | **-0.63** |
| AGREE: reverse a contract-sized shift (90 rows) | 100.75 | +3.13 | -0.72 |
| AGREE: oracle, empty every zero-gold emitting row | 178 | +5.73 | -- |

**Break-even.** For AGREE's halving to be net positive, the none option may cost at most **43 exact entities per 89
FP removed (0.48 per FP)**. To reach **1.5 pp** it may cost at most **19.7 (0.22 per FP)**. The only measured analogue
of an explicit empty answer, F10, cost 0.59 per FP. B4 with no supply trigger therefore stays net negative, which
matches the headroom note's -0.19.

The N1 gate of section 3.3 is the same "none" option restricted to rows the supply flags. Its measured precision is
6 gold-entity rows among 128 gated, and 3 exact entities put at risk per 28 FP. That is 0.11 per FP, under the 0.22
bar. Its whole mass, however, is 28 FP on AGREE: 0.68 pp.

## 5. Recommendation to the coordinator

1. **Close score-threshold abstention at the exemplar supply. Do not register it.**
   - Its best cross-fitted net is 0.00 pp for R1 / R1m / R2 / R3, and every non-trivial τ is negative.
   - At the lightest cut, R1 q 0.05 already gives -0.31 pp oracle and 39 intent-correct rows stripped of their
     intent's exemplars.
   - The retrieval cosine does not separate zero-gold rows (AUC 0.47-0.52).
   - **Abstention cannot reach 1.5 pp in this form.** No design is needed.
2. **Express decision 199 as a supply "none" SIGNAL, and compose it with the contract line (COMP-1b), not alone.**
   - The mechanism is N1: the entity-free exemplar share ≥ 0.6 triggers an explicit empty-entity decision.
   - Predicted on AGREE: oracle +0.68 [+0.28, +1.10] and +0.17 at M1, below the same-flight floor of 1.49. Alone it
     is therefore not resolvable as a supply-variant column.
   - Under a forced-emission contract the same gate reaches oracle **+1.78 [+1.23, +2.36]** on COMP-1. That is about
     0.4 pp of that value at M1, and up to 80 % of COMP-1's -2.24 pp loss at the oracle.
   - **Design:** a same-flight supply-variant column beside the next contract arm (COMP-1b or its successor), gated
     at θ 0.6 fixed now. The column is read against the 1.49 floor as "recovers the contract's zero-gold loss".
   - The cross-fit did not confirm θ (+0.01 [-0.91, +0.91]). θ 0.6 must therefore be declared before the flight,
     not tuned on its read.
3. **Keep answer-side B4 closed unless its recall cost is under 0.22 exact entities per FP removed.**
   - Halving zero-gold emission is worth +2.75 pp gross but -0.63 pp at F10's measured cost.
   - The measured contract sensitivity (a 90-row shift of 414) shows the Solver's zero-gold emission is movable by a
     contract. The same sensitivity makes a blanket "none" option risky on gold-entity rows.
   - If it is tried, it is cross-flight (DEV-2000-ADDED, bar 2.5 pp). The pre-registered gate is at most 20 exact
     entities lost per 89 FP removed.

Outside the SLU question, the one boundary-side signal is the top boundary score, which marks an off-block gold
intent (inverted AUC 0.85, 40 rows). It argues for widening or re-querying the block when the top score is low, not
for delivering less. It addresses at most the 34 intent-wrong off-block rows.

## 6. Method and reproduce

- **Arms and hashes.** `report.json` records the run, attempt, outputs sha256 and scores sha256 of every arm, plus the
  phases sha256 of every arm that has one. AGREE: phases `783299f1...`, outputs `6a4256e0...`, scores `01db05fa...`.
  For each arm, the in-process totals reproduce the sealed official totals to 1e-6; the driver refuses otherwise.
- **Boundary recompute inputs:**
  - snapshot `5520b844...`;
  - facet vectors `76e8d16a...`;
  - segment query vectors `e7a5b226...`;
  - agreement table `018ca6ef...`;
  - prepared supply `be70d4d0...`.
- **Exemplar pool.** `size-pool-annotated-exemplars` through `GP.load_exemplar_pool`. Exemplar texts stay in-process
  as n-gram sets.
- **Limits:**
  - phrase support is a proxy for what an exemplar contributes;
  - the M1 conversion is an analogue;
  - the R4 / N1 family and its grid were added after the first run's AUC table, so their in-sample numbers are
    selected;
  - the cross-fit is the guard, and it did not confirm N1's θ.

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_supply_abstention_headroom.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_supply_abstention_headroom.py --check \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```

Wall time is about 1.3 min and peak memory 0.67 GB.
