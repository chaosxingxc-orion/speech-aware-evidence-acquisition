# Cell E4-1: the core-native targeted re-listen, shadow delivery on TRAIN Fold A (owner decision 185)

Registered before contact 2026-09-29 at study commit `b54dfb4de`; both cells **held**.
Nothing here authorises a flight, a flip or an admission entry. Development numbers only (owner decisions 28 and 86).
Design: `docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md` (sections 1, 4 and the section 8 coordinator rulings); motivation: `docs/results/2026-09-28-slurp-node-information-gain-ledger.md` sections 4-5.

**What E4-1 is.** The retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, official SLU-F1 65.16 / intent 85.83 on TRAIN Fold A)
with exactly two registered changes:

1. **The program switch -- the ONLY base change besides the relisten block.** `policy`
   `phase-native-candidates-review-revise-v1` (ceiling 11) -> `phase-native-candidates-review-revise-relisten-v1` (ceiling 17 = 11 + 2 x
   `max_slots_per_row` 3). The two fragments differ only in `program_id` and `max_contacts`. As in W-SV-1, the
   model-visible request text carries two program-identity fields the switch moves (the program id inside quoted
   prior contact ids; `remaining_model_contacts`, +6), so the delivered path equals AGREE's modulo those two fields.
2. **The relisten block** `native_episode.relisten` (field names from `rails.relisten.RELISTEN_CONFIG_KEYS`):

```json
{
  "blind_template_id": "slurp_relisten_blind_v1",
  "confirm_template_id": "slurp_relisten_confirm_v1",
  "delivery": "shadow",
  "max_slots_per_row": 3,
  "policy": "saea-obs-targeted-relisten-v1",
  "value_max_words": 8
}
```

Post-accept, after the deliver normaliser, for up to 3 delivered entities per row in delivery order: a BLIND contact
(packet + decided intent + slot type, never the delivered value `c`; `slurp-relisten-value-v1`) and, when its value is
canonically different, unheard or unparsed, a FORCED-CHOICE contact (`c` against the blind value or the unheard
sentinel, order fixed by `sha256(sample_id, slot type)`; the decided intent only; `slurp-relisten-confirm-v1`).
**Shadow delivery (ruling 5):** the DELIVERED answer is the AGREE form's own and is never mutated; each row seals a
`saea-relisten-v1` receipt (contact ids, hashes, dispositions, votes -- never the value's bytes).

**Estimand and claim.** Per shadow column, SLU-F1(column) - SLU-F1(delivered) on the same flight's rows; the columns
differ only by accepted replacements (a) and, for (b), drops. `measurement_design` `same-flight-shadow-relisten`,
`shadow_delivery` true, `columns` [`relisten-replace-only`, `relisten-replace-drop-unheard`]; claim ceiling **`nominated`**.

**Primary metric.** Official pooled SLU-F1 (micro), each shadow column against the delivered column. **Intent is
identical between the columns by construction** (bind() never re-opens the decided intent); it is tested per row and
the read refuses on any difference.

**Declared expectation, ceilings and the bar.** `expected_effect_pp` **0.0** for both columns, `claims_benefit` false
(ruling 7: no measured analogue exists). Ceilings stated beside, never as the expectation: upper bound 4.09 pp SLU-F1
(NEAR + WRONG-VALUE, 97 items) and 0 pp intent; re-listen-addressable BOUNDARY + NEAR + FORMAT **35** of 142 items;
SPURIOUS **253** predictions, **74** with the filler in the Perception note (column b's target); hearing share
**17-74 %** of the 407 delivered gold-side errors (4.09 x p about 0.71-3.0 pp). The bar is the design's own null,
provisionally **0.735 x sqrt(200 / n) = 0.3163 pp SLU-F1 at n = 1080** (`scripts/checks/stage3_effect_floor_check.py`, design
`same-flight-shadow-relisten`, ROLL-AA anchor). `tuning_roster` `none` (nothing was tuned), `read_roster` `SLURP-EVO-FOLD-A-V2`.

**Variant cost.** Up to +6 contacts per row (3 blind + 3 confirm), each re-sending the row's packet: at most
18507.1706 s extra audio per flight (6 x the Fold A total 3084.5284375 s; 17.1363 s per row).
On the sealed AGREE answers the blind contacts number **1018** (0.9426 per row;
rows by delivered entity count {"0": 300, "1": 582, "2": 158, "3": 37, "4": 3}) re-sending 3290.3193 s, plus at most as many
confirm contacts (6580.6385 s if every one fires). Measured by `scripts/flights/e4/e4_cost_measure.py`.

## The decision rule (fixed here)

SAME-FLIGHT SHADOW-COLUMN READ (owner decision 185; design section 4 with the section 8 rulings; claim ceiling 'nominated'). The DELIVERED column is the flight's own sealed answer, scored once by the flight with slurp-slu-official-train. Each shadow column -- relisten-replace-only (a: the section 1 acceptance rule) and relisten-replace-drop-unheard (b: a, plus dropping an entity when both contacts vote unheard) -- is rendered by the pure bind() from the same flight's sealed saea-relisten-v1 receipts and trace (AT1: a row with no accepted replacement and no drop renders byte-identical to the delivered text) and scored ONCE with slurp-slu-official-train through core.scoring_batch.score_complete_derived_copy; each contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260915). PRIMARY: official pooled SLU-F1 (micro), shadow column minus delivered column. GUARD: intent is identical between each shadow column and the delivered column BY CONSTRUCTION (bind() never re-opens the decided intent); it is tested per row and the read REFUSES on any difference. THE BAR: the design's own null (ruling 7: 'the bar is the twin/shadow null'), provisional until this cell measures it: scripts/checks/stage3_effect_floor_check.py design same-flight-shadow-relisten, 0.735 x sqrt(200 / n) = 0.3163 pp SLU-F1 at n = 1080. Per column: NOMINATED iff the SLU-F1 CI95 lower bound is above zero AND the point delta exceeds 0.3163 pp AND the intent guard holds; SHADOW HARM iff the SLU-F1 CI95 upper bound is below zero AND the point delta's magnitude exceeds 0.3163 pp; otherwise NOT NOMINATED (within the null). The two columns are two pre-declared rules read from one contact stream; no rule search (decision 179). A nomination claims nothing at system level: promotion means binding in delivery and a full-system read against an in-chain A/A (design section 4). Descriptive, never gating: saves and harms by error kind (gold read on the scoring side only), the per-type table, the blind-disposition and confirm-vote tallies, and equal-scenario weighting; every verdict carries the per-scenario table.

## Columns

| column | what | file under `<data root>/runs/SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1/attempt-slurp-native-stage3-relisten-fold-a-generation-v1/supply-variants/` |
| --- | --- | --- |
| delivered | the flight's own sealed answer and score (LEFT of both contrasts) | (the flight's own `.scores.json`) |
| `relisten-replace-only` | shadow column (a), replace-only | `arm-relisten-replace-only-slurp-slu-official-train-scores.json` |
| `relisten-replace-drop-unheard` | shadow column (b), replace + drop-when-both-unheard | `arm-relisten-replace-drop-unheard-slurp-slu-official-train-scores.json` |

`scripts/flights/e4/e4_read.sh` refuses unless the READ row `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1` is root countersigned, renders and scores both columns once
(`scripts/analysis/stage3_rollout_score.py --mode relisten`), tests the intent guard, then runs
`scripts/analysis/stage3_paired_read.py --right-column relisten-replace-only` and `--right-column relisten-replace-drop-unheard` against the delivered column.

## Shadow delivery proof (the W-SV-1 arm-A method)

Verdict **IDENTICAL_MODULO_PROGRAM_IDENTITY** (`docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1/shadow-proof-v1.json`, tool `scripts/flights/e4/e4_shadow_proof.py`, 120 rows dispatched serially against a fake POST under one common scratch run id, zero model/server/tokenizer/encoder/scorer contacts; the canned Solver answer carries one entity so the relisten stage fires, the canned blind answer alternates heard=false / a different heard value, the canned confirm answers A).

| proof | result |
| --- | --- |
| composed config: differing leaves by class | {"bookkeeping": 40, "program-switch": 1, "relisten-block": 6, "supply-pin": 2}; request-affecting [] |
| prepared first-phase supply output = AGREE registered and committed | True (`eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae`) |
| delivered-path contacts POST-body identical to AGREE, exactly | 0 / 663 |
| the same after mapping the program id and masking remaining_model_contacts | 663 / 663 (unpaired E4-1 0, unpaired AGREE 0); by role {"perception": {"contacts": 120, "normalised_identical": 120, "post_body_identical": 0}, "planner": {"contacts": 181, "normalised_identical": 181, "post_body_identical": 0}, "reviewer": {"contacts": 181, "normalised_identical": 181, "post_body_identical": 0}, "solver": {"contacts": 181, "normalised_identical": 181, "post_body_identical": 0}} |
| relisten contacts (all extra, post-accept) | 240 by kind {"blind": 120, "confirm": 120}; blind bodies carrying the delivered value 0 (must be 0); confirm bodies carrying it 120 (by design) |
| delivered text identical to AGREE (sha256 per row) | 120 / 120 |
| per-row contact_count(E4-1) - contact_count(AGREE) = captured relisten contacts | 0 / 120; histogram {"0": 120} |
| shadow checks | True |

## The four-row dry run

Rows `slurp:train:000215:audio-1502200839`, `slurp:train:001461:audio-1489672182`, `slurp:train:002697:audio-1501756377`, `slurp:train:003384:audio--1505406264` (roster positions [31, 126, 237, 284]): the first four
Fold A rows whose sealed AGREE answer delivered >= 3 entities AND whose delivered entity set differed between the AGREE
arm and its wave A/A re-fly (14 such rows) -- a model-free, gold-free rule chosen so that the dry
run exercises the blind path (12 blind contacts on the sealed AGREE answers) and, through entity
instability, the forced-choice path. Pass conditions (design section 6 step 2): every row with a delivered entity seals
`saea-relisten-v1`; **at least one forced-choice contact fires**; the realised contact count equals the AGREE-form
contacts plus the receipts' `contacts_used`; zero truncations; the delivered text untouched; both shadow columns render;
0 intent differences. Budget 68 / 272 / 196 s / 1.0 GPU-h.

## Fit

| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |
| --- | --- | --- | ---: | ---: | ---: |
| arm | perception | ALLOW | 19451 | 1510 | 4582 |
| arm | reviewer | ALLOW | 19315 | 1646 | 4718 |
| arm | planner | ALLOW | 19254 | 1707 | 4779 |
| arm | solver | COMPACT_REQUIRED | 21280 | -319 | 2753 |
| arm | blockers | null | | | |
| smoke | perception | ALLOW | 19447 | 1532 | 4604 |
| smoke | reviewer | ALLOW | 19311 | 1668 | 4740 |
| smoke | planner | ALLOW | 19250 | 1729 | 4801 |
| smoke | solver | COMPACT_REQUIRED | 21276 | -297 | 2775 |
| smoke | blockers | null | | | |

The check report carries no relisten-specific line; the relisten budget is the ceiling term (+6 per row) inside every plan cap.

## Files

| file | what it holds |
| --- | --- |
| `../2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-preregistration.md` | the preregistration, with the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact; the CANONICAL `stage3_measurement` |
| `shadow-proof-v1.json` | the shadow-delivery proof |
| `protocol-registered-v1.json` | identities, hashes, the rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the dry run's plans |
| `analysis-recipe-v1.json` | the column read; `run_ids.read` = `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/e4/e4_mint_receipt.py` |

**Sequence.** (1) Root countersigns the four DRAFT flight rows (the READ row stays draft until the seal and is
countersigned before any column score is opened) and mints `coordination/slurp-stage3-relisten-fold-a-v1/root-admission-v1.json` with
`scripts/flights/e4/e4_mint_receipt.py`. (2) Flip with `scripts/flights/e4/e4_flip.sh` (smoke, then arm, one converging
loop; the arm's minted supply must reproduce the AGREE digest). (3) `scripts/flights/e4/batch_chain_e4.sh` on the
slurp-np4 session through the batch driver (dry run, then the one-arm campaign; decision 77). (4) `scripts/flights/e4/e4_read.sh`.

**Budgets.** Arm 18,360 generation contacts (1,080 x 17), 73,440 FIT endpoints,
52,437 speech seconds, 18.5 GPU hours; dry run
68 / 272 / 196 / 1.0 --
the AGREE arithmetic at ceiling 17. Expected spend about 4.06 + 0.9426 blind + at most as many confirm contacts per row.
