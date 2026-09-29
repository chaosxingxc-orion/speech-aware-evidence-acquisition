# COMP-1 official SLU-F1 harm, attributed: the Solver cited-answer contract makes the Solver emit entities on zero-gold rows; the I7n unwrap adds 0 entities and the AGREE supply adds none (DESCRIPTIVE)

Read on 2026-09-29 by Claude Fable 5.1, the analysis agent, in worktree `fable/comp1slu`. The read is model-free.
`core.flight.cli` and `lease_cli` were not invoked. There was no model, server, encoder, embedder, tokenizer, scorer
subprocess, network or GPU contact. The read ran as a CPU sidecar while the G5 chain was flying.

- **Script.** `scripts/analysis/slurp_comp1_slu_harm_attribution.py`. It has a `--check` mode that re-derives the
  report and compares every byte except `generated_at`. The committed report passed that check.
- **Test.** `tests/unit/test_slurp_comp1_slu_harm_attribution.py` runs on fakes (7 passed).
- **Report.** `docs/results/2026-09-29-slurp-comp1-slu-harm-attribution/report.json`. Every number below is copied
  from it. The section names in parentheses are its keys.
- **Gold.** Gold was read offline through the governed TRAIN loader `data.slurp.load_slurp_split`, the loader the
  AGREE error-source read uses. It was hashed in-process.
- **What was not printed or persisted.** No utterance text, transcript, gold value, filler, intent name or model
  output. Only ids, counts, slot type names, scenario names, pp and hashes appear.

**DESCRIPTIVE.** These are development numbers on TRAIN Fold A (owner decisions 28 and 86). They are never a test or
generalisation claim. The verdict word belongs to the coordinator (decision 139).

## 1. Inputs and structural checks

Six sealed arms were read on the same 1,080 roster rows (`docs/receipts/rosters/slurp-evo-fold-a-v2.json`):

- COMP-1 seal-only. Its outputs sha256 is `98b9494e...b119` and its scores sha256 is `af567f9a...ac40`. Both equal
  the seal in `docs/results/2026-09-29-slurp-comp1-fold-a-read.md`.
- Its in-chain A/A, `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`.
- The AGREE arm, `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`.
- The AGREE in-chain A/A, `SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1`.
- PLAN and PLANr.

Every input hash is in `inputs_sha256`.

Structural checks (`structural`):

- **Exact counts reproduced.** The exact {type, filler} matcher reproduces every sealed per-sample
  `slot_f1_exact_{tp,fp,fn}` and `scenario_action_exact` on all six arms, with 0 mismatching rows.
- **Raw Solver texts.** For the four trace-carrying arms, the raw final Solver response was recovered by the
  normaliser's `input_sha256` for 1,080 / 1,080 rows. It came from the flown traces; for COMP-1 these are the
  original attempt and resume 3. It parses as an answer on 1,080 COMP-1 rows and on 1,079 rows of each of the other
  three arms, each of which has one unparsed row.
- **Perception shortlist.** It parsed on 1,080 / 1,080 rows.
- **COMP-1 Solver supply.** It was read from the sealed `solver_citations.supplied_value_ids` on 1,080 / 1,080 rows.
  It equals the traced request's `supplied_evidence` on the 950 rows whose request sha256 is present in the two
  traces, with 0 disagreeing.

## 2. The pooled accounting (`pooled`, `contrasts`)

| arm | entity TP | FP | FN | emitted | FP on the 414 zero-gold rows | zero-gold rows emitting | official SLU-F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| COMP-1 | 538 | 611 | 403 | 1,149 | 288 | 252 | 61.97 |
| COMP-1 A/A | 530 | 497 | 411 | 1,027 | 186 | 162 | 64.21 |
| AGREE | 534 | 487 | 407 | 1,021 | 178 | 159 | 65.16 |
| AGREE A/A | 519 | 492 | 422 | 1,011 | 187 | 167 | 63.31 |
| PLAN | 527 | 492 | 414 | 1,019 | 195 | 172 | 63.63 |
| PLANr | 512 | 475 | 429 | 987 | 181 | 159 | 63.80 |

Paired contrasts on the same rows. The CI95 is a row bootstrap of the summed per-row FP delta (10,000 draws, seed
20260929).

| contrast | d FP all rows [CI95] | d FP on zero-gold rows [CI95] | d FP on the 666 gold-entity rows | d TP | d emitted | d official SLU-F1 pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **COMP-1 - its A/A** | **+114 [+72, +154]** | **+102 [+75, +129]** | +12 | +8 | +122 | **-2.24** |
| COMP-1 - AGREE | +124 [+93, +156] | +110 [+88, +133] | +14 | +4 | +128 | -3.19 |
| AGREE - its own A/A | -5 [-32, +22] | -9 [-27, +9] | +4 | +15 | +10 | +1.85 |
| AGREE - COMP-1 A/A | -10 [-46, +23] | -8 [-29, +12] | -2 | +4 | -6 | +0.94 |
| null: COMP-1 A/A - AGREE A/A | +5 [-24, +38] | -1 [-18, +17] | +6 | +11 | +16 | +0.90 |
| null: PLAN - PLANr | +17 [-8, +42] | +14 [0, +29] | +3 | +15 | +32 | -0.17 |
| null: COMP-1 A/A - PLAN | +5 [-26, +39] | -9 [-27, +11] | +14 | +3 | +8 | +0.58 |

Of the +114 extra FP, **102 (89 %) sit on the 414 rows whose gold carries no entity**. On those rows TP cannot move.
On the gold-entity rows, COMP-1 is +12 FP and +8 TP / -8 FN: recall slightly up, precision roughly flat. All three
same-bytes null pairs keep the zero-gold FP delta inside [-27, +29]. The COMP-1 zero-gold delta (+102) is 3.5 times
the widest null bound.

## 3. The attribution table

**pp conversion (`pp_conversion`).** This recomputes the headroom note's approximate "1 FP ~ 0.03 pp" exactly. One
exact FP whose type is absent from the row's gold adds 1.0 to both the word and the char FP sums of the official
SLU-F1. The unit test pins this against `score_slu`. At the pooled totals that FP is worth **-0.0265 pp** (COMP-1
totals) to **-0.0292 pp** (A/A totals).

**Counterfactuals (`counterfactual_swaps_official_slu_f1`).** These are row swaps of the sealed per-sample word and
char counts, starting from COMP-1 as flown (61.97):

| rows swapped to the A/A | pooled SLU-F1 |
| --- | ---: |
| the 414 zero-gold rows | 64.80 (+2.83 pp; +0.58 above the A/A's 64.21) |
| the 666 gold-entity rows | 61.37 (-0.60 pp) |
| the 180 rows where COMP-1 emits more entities | 63.98 (+2.01 pp) |

| channel | what was measured | items | pp |
| --- | --- | --- | --- |
| **(a) the cited-answer unwrap itself** (I7n, `saea-deliver-cited-answer-normalise-v3-v1`) | Raw envelope parsed by the contract's own strict parser (1,080 / 1,080 parse as envelopes). Its `answer` entities were compared with the delivered entities (`channel_a_unwrap`). | **0 added**. Raw answer 1,149 = delivered 1,149. The entity count is equal on 1,080 / 1,080 rows and the type multiset is equal on 1,080 / 1,080. 0 delivered types are absent from the raw answer. The answer bytes equal the unwrap-stage output on 1,080 / 1,080. The 75 rows that are not entity-identical differ only by the locked projection v3 filler rule (82 filler changes, 21 label changes); the A/A's own v3 changed 90 rows. | **0.00** |
| **(b) the Solver emitting more entities under the contract** | Raw-answer entity counts before any normaliser (`channel_b_raw_emission`) | Raw answer entities: COMP-1 1,149 vs A/A 1,027 (**+122**) vs AGREE 1,021 (+128). On zero-gold rows: 288 vs 186 vs 178, and 252 / 162 / 159 rows emitting. Exact FP: **+114 [+72, +154]**, of which **+102** are on zero-gold rows. | **-2.83** on the zero-gold rows (swap). That is the whole guard loss and more; the gold-entity rows are +0.60 pp for COMP-1. Marginal: 102 FP x 0.0265-0.0292 = 2.7-3.0 pp. |
| **(c) the AGREE / centroid supply changing the Solver's input** | AGREE (same agreement term and supply block, no contract) vs its own and the COMP-1 A/A. COMP-1 contrast split by supply identity (`channel_c_splits`). | AGREE - own A/A: FP **-5 [-32, +22]**, zero-gold FP -9. AGREE - COMP-1 A/A: FP -10. Inside COMP-1 the zero-gold FP rise per zero-gold row does not depend on whether the supply changed (table below). | **+0.15 to +0.29** (a -5 to -10 FP reduction x 0.029), inside the null. The supply channel does not carry the harm. |

Channel (c) split, COMP-1 minus its A/A. A rate is the zero-gold FP delta per zero-gold row.

| split | rows (zero-gold) | d FP | d FP on zero-gold rows | rate |
| --- | --- | ---: | ---: | ---: |
| Perception shortlist identical to the A/A's | 170 (63) | +13 | +15 | 0.24 |
| Perception shortlist changed | 910 (351) | +101 | +87 | 0.25 |
| slot-contract supply identical to the A/A's | 275 (99) | +25 | +28 | 0.28 |
| slot-contract supply changed | 805 (315) | +89 | +74 | 0.23 |
| COMP-1 vs AGREE, shortlist identical | 385 (147) | +49 | +44 | 0.30 |
| COMP-1 vs AGREE, shortlist changed | 695 (267) | +75 | +66 | 0.25 |

- **Exemplars.** The TRAIN-exemplar supply the Solver receives (speech-keyed, k 20) is identical to the comparator's
  on 1,080 / 1,080 rows in every pair.
- **Same splits on AGREE.** The same splits on AGREE vs its A/A give zero-gold deltas of -7 (shortlist identical) and
  -2 (shortlist changed).

So the rise appears at the same rate on rows whose supply did not change. It is absent when the same agreement term
flies without the contract. The composition's retrieval side changes which intent-boundary entries and slot
contracts reach the Solver. It does not change how many entities the Solver emits.

**The centroid key alone has no flown Fold A arm.** Two facts bound it:

- The centroid key changes Perception's supply, and so the shortlist and the slot contracts. The FP rise does not
  follow those changes.
- COMP-1 vs AGREE differ in the centroid key and the contract. On the 385 rows where their shortlists are identical,
  COMP-1 still adds +44 zero-gold FP.

## 4. Where the extra FP sit (`fp_by_slot_type`, `by_scenario`)

Largest per-type FP changes, COMP-1 - A/A (AGREE - AGREE A/A in brackets):

- device_type +22 [-1]
- list_name +14 [0]
- change_amount +10 [-1]
- event_name +9 [+2]
- news_topic +9 [+3]
- business_type +7 [+3]
- date +6 [-4]
- `none` +5 [0]: a literal type `none`, 6 vs 1
- time +5 [+1]
- food_type -10 [-2], the largest decrease

Per scenario, the FP delta and the pooled SLU-F1 if only that scenario's 60 rows are swapped back to the A/A
(from 61.97):

| scenario | d FP | pooled SLU-F1 after swap |
| --- | ---: | --- |
| audio | +30 | 62.89 (+0.92 pp) |
| music | +15 | 62.31 |
| recommendation | +15 | 61.99 |
| lists | +14 | 62.37 |
| general | +13 | 62.49 (+0.52 pp) |
| cooking | -11 | 61.62 |
| datetime | -6 | 61.77 |

AGREE - its A/A moves each scenario's FP by between -7 and +5; audio is +1.

## 5. The audio scenario, -41.04 pp (`audio`)

The audio scenario has 60 rows. **50 of them carry no gold entity.** Only 10 rows give the scenario any TP mass, so a
few FP dominate its pooled precision.

- **The loss is one systematic pattern.** COMP-1 emits an entity on 26 zero-gold audio rows where the A/A emitted
  none or fewer:
  - on 19 rows, 0 -> 1 entity;
  - on 6 rows, 0 -> 2 entities;
  - on 1 row, 1 -> 2 entities.
- **The spurious types.** They are always `device_type` and / or `change_amount`:
  - `device_type` alone on 15 rows;
  - `change_amount` + `device_type` on 6 rows;
  - `change_amount` alone on 4 rows;
  - `device_type` + `house_place` on 1 row.
- **Audio FP by type across the four arms:**

  | type | COMP-1 | A/A | AGREE | AGREE A/A |
  | --- | ---: | ---: | ---: | ---: |
  | `device_type` | 24 | 2 | 5 | 3 |
  | `change_amount` | 12 | 3 | 5 | 4 |

- **Totals.** Audio d FP is +30 and d TP is -1.
- **Not driven by intent or shortlist.** COMP-1's intent is correct on 18 of the 26 rows. Perception's shortlist is
  identical to the A/A's on 4 of the 26.
- **What the pattern looks like.** This is a volume- or device-style command answered with a device and/or amount
  slot that the gold annotation does not carry.
- **Per-row listing.** It is in `audio.changed_rows` (ids and counts only).

General (-17.46 pp) is the same mechanism, spread thinner. The scenario has 50 zero-gold rows, d FP is +13 and d TP is
-3. The types are spread: joke_type, news_topic, person, and `none`.

## 6. The 30 vs 21 PLAN-correct intent harms (`intent_harms_on_plan_correct_rows`, `intent_flips_on_identical_shortlists`)

There are 888 PLAN-correct rows:

- COMP-1 is wrong on 30 of them and the A/A on 21.
- 8 rows are wrong in both.
- 22 rows are wrong only under COMP-1.
- 13 rows are wrong only under the A/A.

**The 9 extra harms come with a changed shortlist, not a changed Solver choice.** Of the 22 COMP-1-only harms, **21
come with a Perception shortlist different from the A/A's**. Only 1 has an identical shortlist:
`slurp:train:001878:audio-1434541191-headset`. AGREE, which has no contract, shows the same shape: 33 wrong vs 21, and
25 AGREE-only harms of which 2 have an identical shortlist. That row is one of the two. On COMP-1's 30 harms:

- gold is in COMP-1's own shortlist on 22;
- the delivered intent is COMP-1's own rank-1 on 23.

These are Perception-ranking harms of the supply, which AGREE already carries.

**On identical shortlists the contract does not move the Solver's intent choice:**

| pair | rows with identical shortlist | delivered intent differs | to gold / from gold | picks rank-1 |
| --- | ---: | ---: | --- | --- |
| COMP-1 vs A/A | 170 | 6 | 3 / 1 | 166 vs 166 |
| AGREE vs A/A | 344 | 5 | 2 / 2 | 333 vs 336 |
| null: A/A vs AGREE A/A | 739 | 21 | 8 / 7 | 703 vs 703 |

The cited template `configs/probes/slurp_native_role_solver_cited_v1.txt` contains no candidate-count instruction.
The report checks this as `solver_template.comp1_template_mentions_candidate_count: false`. Its only diff against
`slurp_native_role_solver_v2.txt` is:

- the envelope output example;
- the sentence "The answer object is the task answer.";
- the citation paragraph (intent ids, and "one entry per answered entity type" with up to three ids).

## 7. Mechanism probe (`mechanism_probe`), descriptive only

- **What the entities cite.** Under the contract, 592 of COMP-1's 611 FP entities cite a TRAIN-exemplar id for their
  type, and 529 of its 538 TP entities do too. Only 7 FP cite a slot contract, 1 FP cites an intent boundary, 3 FP
  have an empty list and 8 FP have no citation entry. So the citation does not tell a spurious entity from a correct
  one.
- **Slot-contract types.** An FP's type is among the supplied slot-contract types on 97-99 % of FP in every arm, with
  the contract and without it.

The data is consistent with the citation instruction making the Solver anchor its answer on the supplied exemplars'
annotations, and so emit their slots on commands that do not state them. This read cannot separate the two parts of
the contract:

- the prompt text: the cited template;
- the constrained decoding: the per-contact JSON-schema grammar, whose `answer` member is an unconstrained object,
  against the A/A's unconstrained free text.

## What this note does not claim

- No test, held-out or generalisation claim, and no verdict word (decisions 28, 86 and 139).
- It does not show that the centroid key alone is harmless on the slot side. No centroid-only Fold A arm exists.
  Section 3 shows only that the FP rise does not follow the supply changes the centroid key causes.
- It does not separate the cited template's instruction text from the envelope's constrained decoding. Both belong to
  the one registered component `saea-solver-cited-answer-v1`.
- It does not claim the mechanism in section 7. That is a descriptive association.
- The bootstrap intervals are row-bootstrap intervals of count deltas. They are not the registered analysis recipe's
  intervals. The registered read remains `docs/results/2026-09-29-slurp-comp1-fold-a-read.md`.

## Recommendation to the coordinator

- **The named component.** The evidence supports one named component as the cause of the SLU-F1 guard loss: **the
  Solver cited-answer contract `saea-solver-cited-answer-v1`**. That is the cited Solver template together with its
  envelope response format.
- **How it causes the loss.** It makes the Solver emit entities on rows whose gold has none: +102 FP on the 414
  zero-gold rows, worth -2.83 pp of pooled SLU-F1. The audio scenario's `device_type` / `change_amount` pattern is its
  largest single instance.
- **Exonerated components:**
  - The I7n unwrap normaliser. It adds 0 entities, byte-proven on 1,080 / 1,080 rows. It is not a bug, and no
    normaliser fix is indicated.
  - The AGREE supply. AGREE vs its A/A is FP -5 [-32, +22] and SLU +1.85.
- **The intent side.** The contract does not change the Solver's intent choice on unchanged shortlists. The extra
  intent harms (22 vs 13 one-sided) come with Perception's changed shortlist, which is the supply.

**Smallest next cell.** COMP-1 minus the citation contract, that is, AGREE + centroid key, on TRAIN Fold A. The Solver
setting is:

- policy `phase-native-candidates-review-revise-v1`;
- Solver template `slurp_native_role_solver_v2.txt`;
- no response format;
- deliver normaliser `saea-deliver-normalise-v3`.

Everything else keeps COMP-1's bytes. Read it against the same in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`.

The attribution predicts:

- zero-gold FP inside the same-bytes null band (about [-27, +29]);
- official SLU-F1 no worse than -h_SLU (-1.2485);
- the intent gain of the two retrieval factors preserved (COMP-1's +4.26 minus whatever the contract contributed; on
  identical shortlists that is 3 to-gold / 1 from-gold rows).

That cell would also be the first flown centroid-plus-agreement arm, which closes the one gap in channel (c). If the
citation edge (gap G1) is still wanted for credit assignment, the contract should return only after that cell. It
should come back as its own single-factor cell whose instruction bounds entity emission (for example, it cites only
entities the speech states and leaves `entities` empty otherwise). No composed cell should carry it before then
(decision 138).
