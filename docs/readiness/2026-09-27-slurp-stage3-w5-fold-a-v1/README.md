# Cell W5: slot-side retrieval (knowledge wave, owner decision 170)

Registered before contact 2026-09-27 at study commit `29ec0008`; both cells **held**.
Nothing here authorises a flight, a flip or an admission entry. Development numbers only (owner decisions 28 and 86).

**What W5 is.** The retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, official SLU-F1 65.16 / intent 85.83 on TRAIN Fold A)
with ONE store ADDED: `knowledge_stores.slot-exemplars`, a second speech-keyed TRAIN exemplar route delivered to
the **Solver**, the node that fills slots -- the M1 mechanism (row-matched content keyed by the row's own speech),
now scoped by the row's intent shortlist. Per row it delivers **nine slot-bearing TRAIN exemplars**: three for each of
the first three intents of the row's AGREE boundary ranking (written-key cosine + 1.0 x the pinned exemplar vote -- the
retrieval-side analogue of Perception's three candidates), nearest first by the row's own sealed speech vector, never
an utterance the M1 route already delivers on that row, filled by the nearest other slot-bearing exemplars where a
shortlist intent has fewer than three inside the recall (85.94 % of delivered items come from the shortlist tier;
639 of 1,080 rows need no fill).

| item | value |
| --- | --- |
| store | `slot-exemplars`, role `train-exemplars`; release `83f175704a09e1721e4d61666979925133a25ea80fc4918fc68a56e527a122a3` binding the ALREADY RELEASED R01-excluded pool snapshot (content `6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63`, 8,554 utterances) |
| route | `phase_supply.solver`: the M1 route's own speech query and TRAIN key vectors; recall k 300; `saea-rank-wcos-prior-agree-v1` at w_cos 0 / w_prior 0 / w_agree 1; `saea-fuse-associated-values-v1` m 300 / c 1 / top_l 9 |
| the per-row order | `prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1/agreement.jsonl` (sha256 `f12540f19730d713594c4f63ce7b68c66ef508b8bb2dbb897ae9541087aceb96`), a sealed-agreement table carrying a strictly decreasing share per listed facet |
| verification | the replayed boundary order reproduces the AGREE delivered eight on 1080 / 1,080 rows; the route as it will fly selects exactly the intended nine on 1080 / 1,080 rows |
| construction | `scripts/build_slurp_slot_exemplar_scope_w5.py` (model-free; contacts model 0 / tokenizer 0 / encoder 0 / embedder 0 / scorer 0 / GPU 0); NO encoder pass is needed (the M1 query and key vector files already cover every row and every pool utterance) |
| unchanged | the M1 route, the boundary channel and its agreement term, the slot-contract cards and their candidate supply, roster, geometry, session, program, templates, normaliser, scorers |

**Roster exclusion proof** (in the build receipt): 1080 Fold A rows / 1080 utterances against 8554 pool values /
8554 utterances / 34,474 recordings: **0 Fold A utterances in the pool** (utterance identity = first three
sample-id fields, any recording refuses the build). The pool is a strict subset of the flown M1 pool (800 M1 utterances -- the R01 rows -- are
outside it). No Fold A gold, flight output or score entered the construction.

**What W5 is not.** It does not enable `native-candidate-slot-view-v1` (decisions 125/126): that view scopes the
intent-role rows of cards a row already receives and performs no retrieval or filtering; card selection is W1's factor
and card content W4's, so enabling it would be a second factor. It reads no live Perception output: no code path
conditions a phase supply on Perception's candidates, so the pre-flight retrieval shortlist stands in (decision 47's
"speech plus the drafted intent", realised pre-flight).

**Primary metric.** SLU-F1 is PRIMARY because W5 acts on SLOTS: it adds row-matched slot-bearing TRAIN exemplars to the node that fills slots (the M1 mechanism, whose admitted gains were slot-only: 213 of 277 B1 saves changed only slots), and owner decision 133 makes intent primary only for intent-acting mechanisms. Among the wave's cells W1 (card selection) and W3 (intent contrast) read intent primary; W4 (slot conventions) and W5 read SLU primary -- W5 is the wave's one slot-RETRIEVAL cell (row-matched content keyed by the row's own speech), W4 a card-content cell.

**Entity taxonomy.** W5 is read against the 2026-09-27 error-source read's classes (MISSING / SPURIOUS / WRONG-TYPE /
BOUNDARY / WRONG-VALUE / NEAR / FORMAT; `entity_items` imported unchanged by the estimate).

## Declared expectation: NO-HARM (from measured numbers only, row 139)

| kind (error-source taxonomy) | AGREE items | gold value printed by W5 | already printed by M1 | NEWLY printed by W5 | expected pp |
| --- | ---: | ---: | ---: | ---: | ---: |
| MISSING | 173 | 72 | 90 | 9 | 0.126 |
| SPURIOUS | 253 | 0 | 0 | 0 | -- |
| WRONG-TYPE | 51 | 4 | 14 | 0 | 0.0 |
| BOUNDARY | 75 | 18 | 29 | 1 | 0.0095 |
| WRONG-VALUE | 41 | 3 | 6 | 0 | 0.0 |
| NEAR | 56 | 6 | 20 | 0 | 0.0 |
| FORMAT | 11 | 0 | 4 | 0 | -- |

The W5 block prints the gold value of 72 MISSING items, but the row's own M1 block already prints
90 MISSING items' values without converting them: the missed values are mostly already in front of the
Solver. W5 NEWLY prints **9 MISSING + 1 BOUNDARY items on 10 rows** (of the audit's 157 in-list
items, at most these). At M1's measured delivered-filler conversion (0.2471: 133 newly correct fillers printed in the
block over 0.5719 x 941 printed gold fillers, docs/results/2026-09-19-slurp-m1-exemplar-compression-analysis-v1.md sections 2.1 and 3.2; a lower bound) times the error-source read's
isolated pp per repaired item, the expectation is **0.1355 pp** (oracle 0.5482 pp if every newly printed item
converted). The direct analogue agrees: VAR-1 (R01C 625) exemplar budget 30 vs 20 read **+0.09 [-1.47, +1.60]** SLU. M1's
own +13.70 SLU (replicate) is not the basis: it was read against a system without exemplars. Both measured figures sit
far below the 2.5 pp benefit floor at n = 1,080, so the arm is declared `admission` `no-harm`, `harm_margin_pp`
1.2485 (SLU) with intent 0.9943 the guard, `expected_effect_pp` 0.0, `claims_benefit` false, `replicate_run_id`
`SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`.

**Named risks (counts, AGREE rows).** All 414 empty-gold rows receive nine slot-bearing exemplars
(SPURIOUS is the largest error class, 253 items; K3); 9,119 of 12,345 printed (type, value) pairs are of types the
row's gold does not carry. On 89 rows the gold intent is outside the shortlist that scopes the block
(18 of them intent-correct on AGREE); 98 rows receive no gold-intent exemplar from W5 (M1's twenty are unchanged).

## Token cost and Fit

| phase | contacts (carrying the M1 block) | added tokens mean / max | realised prompt max (AGREE) | projected max |
| --- | ---: | --- | ---: | ---: |
| perception | 1080 (0) | 0.0 / 0.0 | 3769 | 3769 |
| planner | 1099 (1099) | 450.5 / 612.8 | 14561 | 15053 |
| reviewer | 1103 (1103) | 450.5 / 612.8 | 14413 | 14905 |
| solver | 1103 (1103) | 450.5 / 612.8 | 14426 | 14918 |

The W5 block is 451.0 tokens per contact on average (max 612.8) at 3.634
characters per token (measured on the flown M1 exemplar block; same line form); per row +1378.7 tokens mean (max
3056.1), 3.95 % of the AGREE prompt volume. the widest realised request per phase on the sealed AGREE trace plus that contact's W5 block (every Solver, Reviewer and Planner contact carries the M1 block and would carry the W5 block the same way) stays below the live operational budget (24576 slot - 3072 reserve - 512 completion = 20992): Solver 14426 -> 14918, Reviewer 14413 -> 14905, Planner 14561 -> 15053; no realised request is projected to compact.

W5 is registered to fly ALONE on the AGREE form, like W4; it composes with W1 and W4 later without change (it adds a store, it edits none). The binding facts are (a) the physical margin the runtime's own pre-flight (core.flight.cli check, placeholder 4 bytes per token on the widest representative request) reports after W5 -- a COMPACT_REQUIRED preflight with a non-negative PHYSICAL margin proceeds under the armed compact-or-abstain policy (the AGREE, COMP-1 and W4 cells already read COMPACT_REQUIRED on the Solver), a negative one refuses -- and (b) the realised requests projected from the sealed AGREE trace (token_cost.compaction_projection).

| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |
| --- | --- | --- | ---: | ---: | ---: |
| arm | perception | ALLOW | 19449 | 1512 | 4584 |
| arm | reviewer | ALLOW | 19313 | 1648 | 4720 |
| arm | planner | ALLOW | 19252 | 1709 | 4781 |
| arm | solver | COMPACT_REQUIRED | 22037 | -1076 | 1996 |
| smoke | perception | ALLOW | 19449 | 1512 | 4584 |
| smoke | reviewer | ALLOW | 19312 | 1649 | 4721 |
| smoke | planner | ALLOW | 19251 | 1710 | 4782 |
| smoke | solver | COMPACT_REQUIRED | 22036 | -1075 | 1997 |

## Files

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-w5-fold-a-v1-preregistration.md` | the preregistration, with the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact; the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read; `run_ids.read` = `SAEA-SLURP-STAGE3-W5-FOLD-A-PAIRED-READ-V1` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/w5/w5_mint_receipt.py` |

**Sequence.** (1) The coordinator registers the shared A/A `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` and the wave chain. (2) Root countersigns
the DRAFT rows (four flight rows and two model-free rows; the READ row stays draft until the seal), mints
`coordination/slurp-stage3-w5-fold-a-v1/root-admission-v1.json` with `scripts/flights/w5/w5_mint_receipt.py`. (3) Flip with `scripts/flights/w5/w5_flip.sh` (smoke,
then arm; minted first-phase supplies must reproduce the AGREE digests). (4) Chain: Append W5 to the knowledge-wave chain (scripts/flights/wave/batch_chain_wave.sh, branch fable/waveaa) as one more step after W4: add a catalogue entry 'w5' with experiment/cell slurp-native-stage3-w5-fold-a-v1, smoke slurp-native-stage3-w5-fold-a-smoke-4-v1, campaign_plan configs/campaign/slurp-native-stage3-w5-fold-a-v1.json, run ids SAEA-SLURP-STAGE3-W5-FOLD-A-V1 / -FIT-V1 / -SMOKE-4-V1, owner root-slurp-native-stage3-w5-fold-a-v1, and accept step lists ending in 'w4 w5'.

**Budgets.** Arm 11,880 generation contacts, 47,520 FIT endpoints, 33,930 speech seconds,
12.0 GPU hours; smoke 44 / 176 / 117 / 1.0 -- the AGREE arithmetic.
