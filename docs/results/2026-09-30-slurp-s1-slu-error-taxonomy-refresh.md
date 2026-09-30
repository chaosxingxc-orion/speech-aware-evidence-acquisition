# S1 SLU error-taxonomy refresh on the COMP-1b bytes: the taxonomy is stable across arms, and neither S2 nor S5 reaches 1.5 pp at a measured conversion (DESCRIPTIVE, offline)

Date: 2026-09-30. Read id `SAEA-SLURP-S1-SLU-ERROR-TAXONOMY-REFRESH-V1`, recipe
`slurp-s1-slu-error-taxonomy-refresh-v1`. Round S1 of the Stage-3 slot-extraction programme
(`docs/readiness/2026-09-30-slurp-stage3-replan-v6.md` section 2). Written by Claude Opus 5.5, the analysis agent on
the coordinator's brief, in worktree `fable/s1taxonomy` (base master `4586a0dcc`).

**Status: DESCRIPTIVE.** These are development numbers on DEV-2000-ADDED (a development roster) and TRAIN Fold A (a
construction roster), per owner decisions 28 and 86. The note makes no test, generalisation or superiority claim. It
registers nothing, admits nothing and authorises no flight. The verdict word belongs to the coordinator.

**Contacts: zero of every kind.** The read made no model, server, tokenizer, encoder, embedder, GPU, network or
paid-API contact and ran no official-scorer subprocess. `core.flight.cli`, `lease_cli`, re-pins, the queue and the
flight worktree were not touched. The milestone flight was in progress while this read ran; the read is CPU-only
(4 threads, peak 0.72 GB).

**Gold and text discipline.** Gold entered only offline and only on the scoring side, through the governed SLURP
loader `data.slurp.load_slurp_split`: `train` for Fold A, and `devel` for DEV-2000-ADDED. The `devel` path is the one
the 2026-09-24 CELL-3 fresh-roster diagnostic uses. The test split was not read. No utterance text, transcript, gold
value, filler, card body or model output is printed or persisted. Only counts, pp, rates, slot TYPE names, scenario
names, ids and hashes appear.

## 0. Method

**Driver.** The driver is `scripts/analysis/slurp_s1_slu_error_taxonomy.py`. It is new and lives under
`scripts/analysis/`; nothing under `rails/` was touched. Its unit test is `tests/unit/test_slurp_s1_slu_error_taxonomy.py`
(12 synthetic tests, including the new `--arms` flag).

The driver re-implements no class and no origin. It imports these unchanged:

- from the node ledger (`scripts/analysis/slurp_node_gain_ledger.py`): `load_node_states`, `derive_arm` and
  `slot_ledger`. These give the per-gold-item delivered class and the origin split, exactly as defined on 2026-09-28;
- from the error-source read: `load_outputs`, `repaired`, `slu_counts` and the TRAIN `load_gold`;
- from the gold-position read: `load_phases`, the exemplar pool and the slot-contract bodies;
- W5's `printed_pairs`;
- from the consumption-headroom read (`scripts/analysis/slurp_slu_consumption_headroom.py`): the pooled-F1
  arithmetic, the exact counterfactual `Rescorer`, `trade_pp`, `items_for_target` and `evidence_class`;
- from `analysis.sealed_credit.entity_states`: `entity_items`.

The new code is limited to three things: the arm table (scorer key and gold split per arm), the `devel` gold loader,
and the aggregations.

**Arms.** All five use the same program, `phase-native-candidates-review-revise-v1`.

| label | run | roster | role |
| --- | --- | --- | --- |
| (a) `a2` | `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1` | DEV-2000-ADDED, 1,000 | A2 arm |
| (b) `a2_aa` | `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1` | DEV-2000-ADDED, 1,000 | A2's in-chain A/A |
| (c) `comp1b_fold_a` | `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` | TRAIN Fold A, 1,080 | COMP-1b arm |
| context | `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` | TRAIN Fold A, 1,080 | COMP-1b's in-chain A/A |
| control | `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` | TRAIN Fold A, 1,080 | v6 baseline |

**Built-in checks.** The run stops unless all three of these hold:

- **Sealed totals.** Every arm's in-process word-plus-char totals reproduce its sealed official totals to 1e-6.
- **Item join.** The item join reproduces the ledger's SPURIOUS and gold-side counts.
- **Control.** The AGREE control reproduces the v6 baseline:
  - classes: MISSING 173, SPURIOUS 253, WRONG-TYPE 51, BOUNDARY 75, WRONG-VALUE 41, NEAR 56, FORMAT 11;
  - origins: consumption 107, hearing-visible 71, undetermined 229;
  - the N1 gate at 0.6: 128 rows and 28 spurious entities.

  It reproduced all of them.

**Cross-checks against published numbers.** Independent numbers reproduce as well:

- Zero-gold FP and emitting rows are 160 / 140 (A2), 169 / 153 (A/A), 185 / 161 (COMP-1b) and 186 / 162 (COMP-1 A/A).
  These match the A2 read's section 4 and the COMP-1b read's section 4.
- COMP-1b's classes match the E5 read's section 2 table: SPURIOUS 262, BOUNDARY 68, FORMAT 10, NEAR 57, WRONG-VALUE 42
  and WRONG-TYPE 54.

**Class definitions.** These are the error-source read's, unchanged. Exact `{type, filler}` matches are removed
first. Same-type leftovers are then classed FORMAT, BOUNDARY, NEAR or WRONG-VALUE. Cross-type leftovers that carry
the same, a span-related or a near value become WRONG-TYPE. Everything else is MISSING or SPURIOUS.

**Oracle.** "Oracle pp" is the exact isolated in-process re-score with that item set repaired to gold, over the whole
roster, using the official arithmetic.

**Origin.** Origin is the ledger's rule, for gold-side errors only:

- **consumption:** the gold span is contiguous in the Perception note, or the item was right at the Solver's first
  answer and was broken later;
- **hearing-visible:** the note carries a near or partial form;
- **undetermined:** the note is silent.

**Supply evidence.** This is the headroom note's section 3 precedence, restricted to what the row's Solver was
supplied:

- E1: the row's exemplars print the gold (type, value);
- E2: the value is printed under another type;
- E3: a delivered slot-contract card names the value;
- none: the value is not in the supply.

The TRAIN-value-list class (E4) is not computed. It would need the full TRAIN list on the DEV arms, and "none" here
is E4 plus E5.

**Outputs.** They are under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-S1-SLU-ERROR-TAXONOMY-REFRESH-V1/`: `report.json`,
`tables.md` and `content-sha256.json`. Content hashes with `generated_at` removed are `report.json`
`9d9eac5835a21fbc99bddbac0fb8d6585a846101daf5360843c0d385e6f0a214` and `tables.md`
`246c8ed556086e423bbb0b2cb5e3fb87e2906b0b60ae22ef2560721d940f07a2`. A `--check` re-run reported IDENTICAL apart from
`generated_at`. Every number below is quoted from `tables.md`.

## 1. The three per-arm tables

The table below also carries the COMP-1 A/A on Fold A (context) and the AGREE control, so that each arm sits beside
its same-roster comparator. "Items / oracle pp" throughout.

| class | (a) A2 DEV | (b) A2 A/A DEV | (c) COMP-1b Fold A | COMP-1 A/A Fold A | AGREE Fold A (v6) |
| --- | ---: | ---: | ---: | ---: | ---: |
| SPURIOUS | 249 / 7.84 | 263 / 8.22 | 262 / 8.62 | 274 / 9.18 | 253 / 8.46 |
| MISSING | 188 / 9.96 | 197 / 10.39 | 189 / 10.81 | 188 / 10.70 | 173 / 9.80 |
| WRONG-TYPE | 67 / 5.72 | 60 / 5.10 | 54 / 4.91 | 47 / 4.27 | 51 / 4.63 |
| BOUNDARY | 73 / 2.43 | 69 / 2.43 | 68 / 2.70 | 66 / 2.20 | 75 / 2.88 |
| NEAR | 36 / 1.10 | 37 / 1.12 | 57 / 1.80 | 55 / 1.84 | 56 / 1.84 |
| WRONG-VALUE | 46 / 2.80 | 50 / 3.06 | 42 / 2.25 | 43 / 2.30 | 41 / 2.12 |
| FORMAT | 10 / 0.27 | 6 / 0.16 | 10 / 0.35 | 12 / 0.42 | 11 / 0.39 |
| **all error items / oracle all** | **669 / 34.07** | **682 / 34.60** | **682 / 36.39** | **685 / 35.79** | **660 / 34.84** |
| sealed SLU-F1 | 65.93 | 65.40 | 63.61 | 64.21 | 65.16 |
| gold items / predicted | 1,027 / 1,088 | 1,027 / 1,093 | 941 / 1,014 | 941 / 1,027 | 941 / 1,021 |

**Intent-right rows** own most of the mass on every arm. Each cell is items / oracle pp.

| arm | SPURIOUS | MISSING | WRONG-TYPE | BOUNDARY |
| --- | --- | --- | --- | --- |
| A2 | 171 / 5.19 | 136 / 7.36 | 43 / 3.67 | 64 / 2.15 |
| A2 A/A | 175 / 5.25 | 123 / 6.68 | 37 / 3.14 | 56 / 1.92 |
| COMP-1b | 194 / 6.16 | 152 / 8.83 | 42 / 3.81 | 63 / 2.49 |

**Origin of the delivered gold-side errors** (items / oracle pp; kinds; supply evidence E1 / E2 / E3 / none):

| origin | (a) A2 | (b) A2 A/A | (c) COMP-1b | AGREE (v6) |
| --- | --- | --- | --- | --- |
| consumption | 127 / 7.14 | 120 / 7.16 | 101 / 6.21 | 107 / 6.47 |
| of which at the Solver (gold span contiguous in the note) | 126 | 120 | 97 | 103 |
| of which value printed in the exemplars | 71 | 63 | 59 | 55 |
| hearing-visible (note near / partial) | 79 / 3.80 | 64 / 3.07 | 77 / 3.91 | 71 / 3.47 |
| undetermined (note silent) | 214 / 12.05 | 235 / 12.80 | 242 / 13.59 | 229 / 12.45 |
| of which the value was in the supply (E1 + E2 + E3) | 81 | 98 | 112 | 107 |
| all gold-side errors with the value printed by M1 (E1) | 165 | 166 | 177 | 163 |

**Origin by class, arm (a) A2.** Columns MISSING / WRONG-TYPE / BOUNDARY / NEAR / WRONG-VALUE / FORMAT:

- consumption: 64 / 24 / 25 / 2 / 6 / 6;
- hearing-visible: 21 / 13 / 23 / 15 / 5 / 2;
- undetermined: 103 / 30 / 25 / 19 / 35 / 2.

The same breakdown for (b) and (c) is in `tables.md`, section "Origin x class".

**SPURIOUS split.** Columns are (a) A2 / (b) A2 A/A / (c) COMP-1b / AGREE.

| SPURIOUS split | (a) | (b) | (c) | AGREE |
| --- | ---: | ---: | ---: | ---: |
| filler contiguous in the note | 86 | 89 | 78 | 74 |
| filler not in the note | 163 | 174 | 184 | 179 |
| on zero-gold rows (oracle pp) | 160 (4.84) | 169 (5.06) | 185 (5.86) | 178 (5.73) |
| on gold rows (oracle pp) | 89 (2.60) | 94 (2.72) | 77 (2.31) | 75 (2.29) |

**Empty-gold rows (the decision-199 "right to say no slot" mass):**

| quantity | (a) A2 | (b) A2 A/A | (c) COMP-1b | COMP-1 A/A | AGREE |
| --- | ---: | ---: | ---: | ---: | ---: |
| zero-gold rows | 314 | 314 | 414 | 414 | 414 |
| correctly empty | **174** | 161 | **253** | 252 | 255 |
| spurious-filled | **140** | 153 | **161** | 162 | 159 |
| spurious entities on them | 160 | 169 | 185 | 186 | 178 |
| spurious-filled rows with intent right | 88 | 99 | 116 | 114 | 113 |
| oracle pp, empty every spurious-filled row | 4.84 | 5.06 | 5.86 | 5.93 | 5.73 |
| gold rows delivered empty (items missed) | 40 (50) | 49 (58) | 53 (55) | 59 (65) | 45 (49) |

**Per slot type.** The top 15 types per arm are in `tables.md`. The heads are:

- **(a) A2.**
  - `date`: 177 gold, 82 errors (MISSING 43, BOUNDARY 15), oracle 3.70.
  - `event_name`: 115 gold, 67 errors (MISSING 26, SPURIOUS 24), oracle 2.86.
  - `person`: 58 errors (SPURIOUS 25, NEAR 12), oracle 2.19.
  - `place_name`: 43 errors (SPURIOUS 16, WRONG-TYPE 10), oracle 2.18.
  - `definition_word`: 36 errors, 28 of them SPURIOUS on 28 gold, oracle 1.20.
  - `time` 1.67; `media_type` 1.33, where MISSING is 17 of 28.
- **(b) A2 A/A.** The same head: `date` 3.78, `event_name` 3.61, `person` 2.11, `place_name` 1.73.
- **(c) COMP-1b.** `date` 4.50 (MISSING 46), `place_name` 2.45, `business_name` 1.93 (NEAR 13), `food_type` 1.83
  (SPURIOUS 20), `time` 1.73, `event_name` 1.57.

**Per scenario.** The per-scenario table for A2 was unavailable in the A2 read, because the roster receipt withholds
the stratum. It is now available from the devel gold on the scoring side. DEV-2000-ADDED is not stratified.

- **(a) A2, error mass.** The mass concentrates in calendar (221 rows, oracle 8.94, SLU-F1 within 72.03) and play
  (203 rows, oracle 7.76, SLU-F1 54.49), then qa (3.90) and email (2.33).
- **(a) A2, general.** General has the lowest SLU-F1 within, at 35.12. Its errors are 34 SPURIOUS of 45, on 46
  zero-gold of 62 rows.
- **(a) against (b).** A2 is higher than its A/A on calendar (+2.41 within) and email (+3.80), and lower on play
  (-3.39) and lists (-5.97).
- **(c) COMP-1b.** The worst within-stratum SLU-F1 are general 17.02, music 49.21 and lists 51.13. The largest oracle
  masses are takeaway 3.18 (MISSING 29), social 2.87 (SPURIOUS 32) and calendar 2.70. General's SPURIOUS rises to 30
  from AGREE's 25, which is the general-scenario flag of the COMP-1b read (-15.54).

## 2. Deltas against the AGREE baseline counts in v6

A2 lives on a different roster, with 1,027 gold items against 941. The clean contrasts are therefore the same-roster
ones: (c) minus AGREE, and (a) minus (b). The raw A2 minus AGREE counts are given only for orientation.

| class | (c) COMP-1b - AGREE, Fold A | (a) A2 - (b) A/A, DEV | (a) A2 - AGREE (cross-roster) | rate per gold item: A2 / AGREE |
| --- | ---: | ---: | ---: | --- |
| SPURIOUS | +9 (+0.16 pp) | -14 (-0.38 pp) | -4 | 0.242 / 0.269 |
| MISSING | +16 (+1.02 pp) | -9 (-0.43 pp) | +15 | 0.183 / 0.184 |
| WRONG-TYPE | +3 (+0.28 pp) | +7 (+0.62 pp) | +16 | 0.065 / 0.054 |
| BOUNDARY | -7 (-0.18 pp) | +4 (0.00 pp) | -2 | 0.071 / 0.080 |
| NEAR | +1 (-0.04 pp) | -1 (-0.02 pp) | -20 | 0.035 / 0.060 |
| WRONG-VALUE | +1 (+0.13 pp) | -4 (-0.26 pp) | +5 | 0.045 / 0.044 |
| FORMAT | -1 (-0.04 pp) | +4 (+0.11 pp) | -1 | 0.010 / 0.012 |
| origin: consumption | -6 | +7 | +20 | -- |
| origin: hearing-visible | +6 | +15 | +8 | -- |
| origin: undetermined | +13 | -21 | -15 | -- |
| zero-gold spurious-filled rows | +2 | -13 | (314 vs 414 zero-gold rows) | 0.446 / 0.384 of zero-gold rows |

What moved:

1. **COMP-1b leaves the slot taxonomy where AGREE had it.** On Fold A the class moves are small (no own null is computed here), and the
   COMP-1b arm and its A/A differ by -12 SPURIOUS, +1 MISSING, +7 WRONG-TYPE and +2 BOUNDARY. The
   intent-supply change reorders nothing on the slot side. The one visible drift is MISSING +16 against AGREE, but
   the A/A has 188 as well, so this is not COMP-1b-specific.
2. **On DEV the shape is the same.** MISSING and SPURIOUS remain the two largest classes: 9.96 and 7.84 pp on A2,
   against 9.80 and 8.46 on AGREE. NEAR is smaller per gold item (0.035 vs 0.060). WRONG-TYPE is a little larger
   (0.065 vs 0.054, led by `place_name` 10 and `relation` on the A/A).
3. **Origin is stable.**
   - Undetermined is the largest origin on every arm, at 12.05-13.59 pp.
   - Consumption is 6.2-7.2 pp, and hearing-visible is 3.1-3.9.
   - On every arm, 163-177 of the gold-side errors had their value printed by M1 and were still wrong.
4. **Zero-gold emission under A2 is the lowest of the five arms**, at 140 of 314 zero-gold rows. The A/A has 153. The
   S5 target mass is therefore smaller on A2 than on AGREE: 160 FP and 4.84 pp oracle, against 178 and 5.73.

## 3. Addressable mass for S2 and S5 at measured conversions

**The bar.** Every "expected" figure multiplies this read's exact oracle by a conversion measured elsewhere. It is an
analogue, not a measurement of the mechanism. The bar is decision 192: at least **1.5 pp** predicted official SLU-F1.
In item terms that is 26.5 converted FN recoveries on A2 and 24.4 on COMP-1b Fold A, or 52.1 and 50.6 converted FP
removals.

**The rates.** All are quoted, none is measured here:

| rate | value | source |
| --- | ---: | --- |
| M1 delivered-filler conversion | 0.2471 | headroom note section 1, `2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md:51` |
| W4 value list | 0.0515 (5 of 97) | headroom note section 2, `2026-09-28-slurp-w4-fold-a-read.md:189-190` |
| F10 explicit empty answer | 22 / 142 FP removed with 13 / 142 exact items lost per zero-gold FP | headroom note section 2, `2026-09-25-slurp-f10-complete-verdict.md:18-21` |
| DEV-2000 five-sample vote-rule reach | 14.4 / 162.2 = 0.0888 | headroom note section 2, `2026-09-28-slurp-empty-entity-offline-read.md:128-134` |
| E5 transcript gold-span containment (Whisper large-v3, Fold A) | 0.7513 | `2026-09-30-slurp-e5-transcript-consistency-oracle-read.md` section 1; used only as a ceiling multiplier for S2 |

### S2: the missing-slot proposal tool (target: MISSING)

| quantity | (a) A2 | (b) A2 A/A | (c) COMP-1b |
| --- | ---: | ---: | ---: |
| MISSING items (rows) / oracle pp | 188 (168) / 9.96 | 197 (178) / 10.39 | 189 (172) / 10.81 |
| on intent-right rows / oracle pp | 136 / 7.36 | 123 / 6.68 | 152 / 8.83 |
| by origin: consumption / hearing / undetermined | 64 / 21 / 103 | 60 / 19 / 118 | 52 / 22 / 115 |
| by supply: E1 / E2 / E3 / none | 94 / 0 / 14 / 80 | 99 / 0 / 14 / 84 | 104 / 1 / 14 / 70 |
| **value not in the supply: items / oracle pp** | **80 / 4.43** | 84 / 4.64 | **70 / 4.22** |
| expected at M1 (0.2471), not-in-supply | **1.09** | 1.15 | **1.04** |
| expected at E5 containment x M1 | 0.82 | 0.86 | 0.78 |
| expected at W4 list (0.0515) | 0.23 | 0.24 | 0.22 |
| expected at E5 containment x W4 | 0.17 | 0.18 | 0.16 |
| (double-counted, not a prediction) all MISSING x M1 | 2.46 | 2.57 | 2.67 |

**Why the not-in-supply subset.** The headroom note (section 2, "consumption with the gold value printed in the
exemplars") treats printing as already spent: an item whose value the supply already shows, and which is still
missed, is the residual after M1's 0.2471. A proposal tool therefore adds new information only on the not-in-supply
MISSING items, and applying M1 to all 188 would count the printing twice. That makes the defensible S2 prediction
**1.09 pp on A2 and 1.04 on COMP-1b Fold A**, at the most favourable measured rate. It drops to 0.82 / 0.78 once the
tool's own transcript must contain the span, and to about 0.2 at the list rate.

**What would be needed.** To reach 1.5 pp alone, the offered proposal must convert about 0.33 of the not-in-supply
items (26.5 of 80 on A2), or 0.44 once containment is applied. No measured slot mechanism converts above 0.2471.

**Not yet multiplied in.** The E5 call-decision precision (0.2455 at a 10 % call rate, v6 S2 row) would lower these
further.

### S5: the explicit no-slot decision (target: SPURIOUS on zero-gold rows)

| quantity | (a) A2 | (b) A2 A/A | (c) COMP-1b |
| --- | ---: | ---: | ---: |
| spurious-filled zero-gold rows / spurious entities | 140 / 160 | 153 / 169 | 161 / 185 |
| oracle pp (empty every spurious-filled row) | 4.84 | 5.06 | 5.86 |
| expected at F10's measured empty-answer effect: FP removed / exact lost / gross / **net** pp | 24.8 / 14.7 / +0.71 / **-0.14** | 26.2 / 15.5 / +0.74 / -0.16 | 28.7 / 16.9 / +0.84 / **-0.23** |
| expected at the DEV-2000 vote-rule reach (0.0888; harm not netted) | 0.43 | 0.45 | 0.52 |
| expected at M1 (0.2471; a printing rate, not an empty-answer measurement) | 1.19 | 1.25 | 1.45 |
| N1 gate at 0.6: rows gated (zero-gold / gold) / rows changed | 51 (43 / 8) / 17 | 51 (43 / 8) / 19 | 128 (122 / 6) / 26 |
| N1: spurious removed / exact lost / partial lost | 15 / 0 / 3 | 17 / 0 / 2 | 24 / 3 / 1 |
| N1 oracle net pp / at M1 | 0.42 / 0.10 | 0.41 / 0.10 | 0.55 / 0.13 |

**Reading the S5 table.**

- **The only measured analogue of an explicit empty answer is net negative on every arm.** F10 gives -0.14 on A2 and
  -0.23 on COMP-1b.
- **The M1 figure is not a measurement.** 1.19 on A2 and 1.45 on COMP-1b assume a "none" option converts like a
  printed exemplar value, with zero recall harm. Even so, it stays under 1.5 on all three arms.
- **The N1 gate is precise but small.** On DEV it gates 51 rows and changes 17: 0.42 pp at oracle, 0.10 at M1.
- **The A2 mass is already smaller than AGREE's.** A2 emits on 140 zero-gold rows against its A/A's 153 (the A2 read's interval, -13 [-29, +3], includes zero).
- **The recall-harm budget from the supply-abstention note (section 4) still binds.** To reach 1.5 pp at zero harm
  needs 52.1 converted FP removals on A2, which is 0.33 of the 160. The 0.22-exact-per-FP ceiling applies on top.

## 4. What S1 says about registering S2 / S5 (decision 192, at least 1.5 pp offline)

**Neither S2 nor S5 clears 1.5 pp at a measured conversion, alone, on the COMP-1b bytes.**

- **S2.** The non-double-counted prediction is **1.09 pp on A2 and 1.04 on COMP-1b Fold A**, at M1's 0.2471, the best
  measured slot conversion. It is 0.82 / 0.78 inside the transcript's containment and about 0.2 at the list rate. S2
  is not registrable on these numbers. S2a (offline design and oracle) is still worth running, but its job is to
  produce a *measured* conversion on the 80 not-in-supply MISSING items. The declared effect needs at least 0.33 of
  them (0.44 with containment).
- **S5.** The zero-gold SPURIOUS mass is real but not separable enough. It is 160 FP on 140 A2 rows (4.84 pp oracle),
  already below the A/A's 169 / 153. Its only measured empty-answer analogue (F10) is net negative (-0.14). The one
  precise trigger (N1 at 0.6) touches 17 DEV rows for 0.10 pp at M1. v6's condition, "registers only if S1 finds a
  separable SPURIOUS mass", is therefore not met. S5's step 6a (the "no entities" option in the contract) can be
  built model-free as a shadow component, but not registered as a column on its own.
- **Composed.** S2 at M1 (1.09) plus S5 at F10 (-0.14) is 0.95. S2 plus S5 plus S4's +0.49 on A2 is about 1.44, still
  short, and S4 is a different decode-free factor. Crossing 1.5 by composition would need S5 at M1 (1.19), a rate
  that measures printing, not abstention. That is not admissible under decision 192.
- **Where the mass is.** The largest mass on every arm is the undetermined origin (12.05 pp on A2) and the 163-177
  gold-side errors whose value M1 already printed.

  The next registrable SLU item therefore has to come from one of two places:

  - a **measured** conversion on those printed-and-missed items (S3's target, 8.98 pp on AGREE, currently closed);
  - a new hearing instrument for the undetermined, not-in-supply items.

  Neither S2 nor S5 as scoped in v6 reaches them.

## 5. Reproduce

```bash
# WSL, model-free; ~2 min when the governed loaders are warm (8.4 min cold), peak 0.72 GB
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 PYTHONPATH=src python -B scripts/analysis/slurp_s1_slu_error_taxonomy.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
# the same with --check: IDENTICAL apart from generated_at
# --arms a2,a2_aa selects arms (outputs then go to a sub-directory arms-<labels>/)
python -B -m pytest -q tests/unit/test_slurp_s1_slu_error_taxonomy.py
```

Input pins, each run's phases, outputs and scores sha256, and the driver hashes of every imported script are in
`report.json` (`arms.<label>.inputs`, `inputs`, `drivers`).
