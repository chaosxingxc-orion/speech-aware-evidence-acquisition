# SLURP E5-1 transcript-consistency ORACLE read: the gold-span precondition fails (0.7513 < 0.80), no rule helps, and no model-visible signal selects the helpful rows (DESCRIPTIVE, offline)

Date: 2026-09-30. Read row `SAEA-SLURP-E5-TRANSCRIPT-CONSISTENCY-READ-V1` (root countersigned on master `3bac891a3`
before any transcript was compared with gold), recipe
`docs/readiness/2026-09-29-slurp-asr-tool-pass-v1/e5-1-read-recipe-v1.json`, design
`docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md`. Owner decision 201 (option A) and
directive 206: this is an INSTRUMENT / ORACLE. The three rules are oracle bounds of a system-applied check, never
runtime candidates; the runtime form under discussion (E5-2) is the frozen core OFFERED a pinned ASR tool and deciding
itself whether to call it. Written by Claude Opus 5.5 (analysis agent, coordinator's brief) in worktree
`fable/e5oracle`.

**Status: DESCRIPTIVE.** Development numbers on TRAIN Fold B (tuning) and TRAIN Fold A (read), both construction
rosters (owner decisions 28 and 86). No test, generalisation or superiority claim. The verdict word belongs to the
coordinator.

**Contacts: zero of every kind.** No model, server, tokenizer, encoder, embedder, GPU, network or scorer-subprocess
contact; `core.flight.cli` and `lease_cli` were not invoked. The E5-0 transcripts already existed (catalogs re-hashed
against their receipts before reading). Gold entered only through the governed TRAIN loader
`data.slurp.load_slurp_split`, offline, on the scoring side. No utterance text, transcript, gold value or model output
is printed or persisted: ids, counts, rates, AUCs, pp, type names and hashes only.

## 0. Inputs, drivers and outputs

- Transcript catalogs (E5-0, pinned Whisper large-v3, decoding config `b90432b6...`), 1,080 rows each, status `ok`
  on all 1,080: Fold A `prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1/fold-a/catalog.json` sha256 `de504e45...` (receipt
  `aa78b4bf...`, producer `SAEA-SLURP-ASR-TOOL-PASS-V1`); Fold B `.../fold-b/catalog.json` sha256 `31462f9b...`
  (receipt `6e5643f5...`, producer `SAEA-SLURP-ASR-TOOL-PASS-FOLD-B-V1`).
- Tuning arm (Fold B): the P-SV-2 flight's delivered column `SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1` (the AGREE arm on Fold
  B, the recipe's named tuning column; the driver reads `<RUN>.outputs.jsonl` only, which differs from the P-SV-2
  `arm-a-agree` first-visit column on 11 of 1,080 rows). P-SV-1 (seal-only) and P-SV-3 were loaded as arms but tuning
  uses the primary only.
- Read arms (Fold A): `agree` = `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (primary), `wave_aa` =
  `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (the AGREE bytes re-flown; `--replicate`), `comp1_aa` =
  `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` (COMP-1's in-chain A/A), `comp1b` = `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1`;
  E4-1 = `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1` seal-only attempt (`--expect-e4-broken 63`, matched). Every arm's
  in-process official totals reproduced its sealed `slurp-slu-official-train` totals.
- Driver `scripts/analysis/e5_transcript_consistency_read.py` (sha256 `e26fd0ec...c271`), unchanged. Supplement
  `scripts/analysis/e5_decision_oracle_supplement.py` (sha256 `3ea2105d...a1e1`, new on this branch; imports the
  driver's definitions and adds the perfect-repair ceiling, the cross-fit two-signal rule and the 206 gate arithmetic).
- Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-E5-TRANSCRIPT-CONSISTENCY-READ-V1/`:

| label | content | content sha256 |
| --- | --- | --- |
| `tune-fold-b` | params.json / report.json / tables.md | `189697e5...682e` / `442e3265...bd1` / `682d7ebc...0b8` |
| `read-fold-a` (primary agree, replicate wave_aa, + comp1_aa, comp1b, E4-1) | report.json / tables.md | `e2fd30da...806` / `4b747951...434` |
| `read-fold-a-comp1b` (primary comp1b) | report.json / tables.md | `e1905c37...be2f15` / `e63cf41c...7cc6` |
| `read-fold-a-decision-supplement` (agree) | report.json | `51deb056...06a3` |
| `read-fold-a-comp1b-decision-supplement` | report.json | `ecaa0131...ba24` |

Tuning (Fold B, point SLU-F1 delta vs the delivered column): R-SWAP -0.87 / -0.35 / -0.27 / -0.09 / +0.03 pp at
theta 0.5 / 0.6 / 0.7 / 0.8 / 0.9 (near off); R-DROP -0.92 (near off) / -0.69 (near on). Chosen `params.json`
(sha256 `189697e5ad97f4377c87737f2c7f4ecb29c9025e827ab55416489420e145682e`): theta 0.9, near_swap false,
near_drop true. Fold B gold-span containment 718 / 944 = 0.7606.

## 1. Stop conditions (pre-declared before E5-0 existed)

| precondition | value | threshold | result |
| --- | --- | --- | --- |
| Q6 gold-span containment (Fold A) | 707 / 941 = **0.7513** | >= 0.80 | **FAIL** |
| Q3 exact-value preservation on E4-1's 63 EXACT -> BOUNDARY items | 59 / 63 = **0.9365** (near variant identical) | >= 0.85 | pass |

`precondition_pass: false`. The registered consequence of a failing precondition is "stop the E5 line". The failure
replicates on the tuning fold (0.7606). Containment is lowest where slot errors concentrate: business_name 26 / 52 =
0.50, person 23 / 42 = 0.548, time 55 / 76 = 0.724, food_type 50 / 65 = 0.769, place_name 79 / 100 = 0.79 (date
0.848, media_type 0.825, event_name 0.878).

## 2. Delivered-wrong-value containment (Q2): the transcript "supports" many wrong values

Share of wrong delivered values that the transcript contains (so a consistency check would NOT reject them):

| error kind | agree | wave_aa | comp1_aa | comp1b |
| --- | --- | --- | --- | --- |
| BOUNDARY | 51/75 = 0.680 | 53/76 = 0.697 | 48/66 = 0.727 | 48/68 = 0.706 |
| FORMAT | 6/11 = 0.545 | 5/11 = 0.455 | 6/12 = 0.500 | 5/10 = 0.500 |
| NEAR | 32/56 = 0.571 | 27/54 = 0.500 | 32/55 = 0.582 | 31/57 = 0.544 |
| WRONG-VALUE | 14/41 = 0.341 | 14/42 = 0.333 | 12/43 = 0.279 | 15/42 = 0.357 |
| WRONG-TYPE | 41/51 = 0.804 | 47/54 = 0.870 | 39/47 = 0.830 | 45/54 = 0.833 |
| SPURIOUS | 148/253 = 0.585 | 154/269 = 0.573 | 148/274 = 0.540 | 150/262 = 0.573 |

## 3. The three rules: ORACLE upper bounds of a system-applied check (never runtime candidates)

Official in-process pooled SLU-F1 delta vs the delivered column, paired row bootstrap, 10,000 draws, seed 20260929:

| rule (setting) | agree (65.16) | wave_aa replicate (64.16) | comp1_aa (64.21) | comp1b (63.61) | agree: EXACT lost / converted / SPURIOUS removed |
| --- | --- | --- | --- | --- | --- |
| R-FLAG (no change; 247 flags) | 0.00 | 0.00 | 0.00 | 0.00 | 0 / 0 / 0 |
| R-DROP tuned (near on) | **-2.31 [-3.65, -1.00]** | -2.53 [-3.92, -1.18] | -1.40 [-2.83, +0.05] | -2.24 [-3.63, -0.88] | 59 / 0 / 104 |
| R-DROP preset (near off) | -2.37 [-3.74, -1.05] | -2.63 [-4.05, -1.26] | -1.40 [-2.87, +0.07] | -2.38 [-3.82, -1.00] | 59 / 0 / 107 |
| R-SWAP tuned (theta 0.9) | **-0.03 [-0.14, +0.07]** | -0.03 [-0.13, +0.07] | -0.02 [-0.12, +0.07] | -0.03 [-0.13, +0.07] | 3 / 1 / 0 (9 swaps) |
| R-SWAP theta 0.6 | -0.50 [-0.87, -0.13] | -0.60 [-0.98, -0.23] | -0.49 [-0.84, -0.14] | -0.55 [-0.92, -0.20] | 22 / 9 / 0 (93 swaps) |
| R-SWAP theta 0.8 | -0.11 [-0.31, +0.08] | -0.16 [-0.36, +0.03] | -0.14 [-0.32, +0.03] | -0.13 [-0.33, +0.07] | 10 / 4 / 0 (27 swaps) |

No setting clears the oracle bar (point >= +1.49 with CI95 low > 0, replicate >= +1.0, <= 1 EXACT lost per 5 net
gained); every point estimate is <= 0 on every arm. Per entity type on `agree` (actions / EXACT lost / wrong values
removed or moved):

| type | R-DROP tuned: drops / EXACT lost / non-EXACT dropped | R-SWAP theta 0.6: swaps / EXACT lost / -> EXACT |
| --- | --- | --- |
| business_name | 21 / 3 / 12 | 12 / 2 / 1 |
| person | 19 / 4 / 11 | 11 / 2 / 0 |
| time | 17 / 9 / 5 | 4 / 2 / 1 |
| food_type | 17 / 6 / 7 | 7 / 1 / 1 |
| media_type | 16 / 6 / 6 | 3 / 0 / 1 |
| place_name | 14 / 4 / 7 | 6 / 1 / 1 |
| list_name | 11 / 4 / 1 | 4 / 1 / 1 |
| device_type | 11 / 3 / 2 | - |
| date | 11 / 1 / 9 | 6 / 0 / 1 |
| event_name | 9 / 1 / 3 | 4 / 1 / 1 |

(R-DROP also removes 104 SPURIOUS entities, not broken down by type in the driver; its EXACT losses, 59 of 247 drops,
outweigh them.)

## 4. Tool-call decision oracle (primary `agree`)

A row "would have been helped" when a delivered value is not supported by the transcript while its matched gold span
is contained (the driver's definition, near-containment on as tuned).

- Helpful rows **29 of 1,080 = 2.69 %** (30 entities); flagged entities 247, flag precision 30 / 247 = 0.1215.
  comp1b: 24 rows = 2.22 % (25 entities), flag precision 0.0996.
- Helpful entities by type (delivered / flagged / helpful): media_type 54/16/6, business_name 61/21/5, person
  50/19/3, food_type 83/17/2, house_place 19/7/2, news_topic 22/5/2, place_name 102/14/2, eight types with 1.
- **Perfect-repair ceiling** (supplement; every helpful entity replaced by its matched gold value): agree **+1.62 pp
  [+1.04, +2.28]**, comp1b +1.21 [+0.73, +1.76]. This is the whole prize for a perfect verify-and-repair call on
  every helpful row, at 100 % call precision and 100 % conversion.
- Beside it (a different tool form, not a verify call): gold spans MISSING from the delivered column but contained in
  the transcript: 113 items on 106 rows (agree), 130 on 123 (comp1b). Repairing plus adding them: +8.21 [+6.95, +9.57]
  (agree), +8.89 [+7.59, +10.30] (comp1b) -- an oracle that also knows which transcript span is the slot and its type.

AUC of each model-visible signal for the helpful label (driver; Mann-Whitney, ties one half; below 0.5 means the
signal points the other way):

| signal | agree AUC | comp1b AUC |
| --- | --- | --- |
| Perception candidate-list length | 0.4492 | 0.4502 |
| note_parse_status (ok vs duplicates-collapsed, 1,057 / 23 rows) | 0.5109 | 0.5128 |
| delivered entity count | 0.6642 | 0.7151 |
| delivered type (best: media_type / business_name) | 0.6515 / 0.6127 | 0.6231 / 0.6203 |
| E4-1 blind / forced-choice disagreement | 0.6713 | 0.7015 |
| entity-free exemplar share | 0.3370 (0.663 reversed) | 0.2989 (0.701 reversed) |

**Best two-signal rule under cross-fit** (supplement: 5 stratified folds, seed 20260929; inside each training fold
every pair of the non-constant features (58 on each arm) is fitted by a two-feature L2 logistic regression and the pair with the best
training AUC is kept; held-out rows scored by that fold's model; precision = helpful rows among the top share of each
held-out fold, pooled):

| arm | chosen pair (folds) | out-of-fold AUC | precision at 10 % call rate | at 20 % |
| --- | --- | --- | --- | --- |
| agree | media_type + E4-1 disagreement (4 of 5); time + entity-free share (1) | 0.6707 | 8 / 110 = 0.0727 | 12 / 219 = 0.0548 |
| comp1b | five different pairs (entity count in 3) | 0.6601 | 5 / 110 = 0.0455 | 8 / 219 = 0.0365 |

## 5. The coordinator's proposed E5-2 gate (206) against the oracle

| quantity | agree | comp1b |
| --- | --- | --- |
| base rate b (helpful rows) | 0.0269 | 0.0222 |
| call-rate band [max(0.01, 0.5 b), min(0.50, 4 b)] | [0.0134, 0.1074] | [0.0111, 0.0889] |
| precision bar b + 0.10 / 2 b | 0.1269 / 0.0537 | 0.1222 / 0.0444 |
| cross-fit rule precision at band low end | 2 / 15 = 0.1333 | 1 / 15 = 0.0667 |
| cross-fit rule precision at band high end | 8 / 120 = 0.0667 | 4 / 100 = 0.0400 |
| cross-fit rule precision at 10 % | 0.0727 | 0.0455 |
| meets b + 0.10 inside the band | only at the 15-row low end (2 hits) | nowhere |
| meets 2 b inside the band | yes (agree) | at the low end only |

Derived (not in a report): at a 10 % call rate the best cross-fit rule reaches 8 of 29 helpful rows on agree, so even
with perfect repair on every reached row the yield is about 8 / 30 of the +1.62 pp ceiling, roughly +0.4 pp -- below
the decision-190 floor of 1.49 pp. The ceiling itself (+1.62) only just exceeds the floor, and only at 100 % recall.

Under the wider label (helpful, or a contained MISSING gold span; supplement `decision_oracle_by_label`): b = 0.1231
(agree) / 0.1343 (comp1b); cross-fit AUC 0.6514 / 0.6797 (entity-free share + entity count chosen in most folds);
precision at 10 % 0.2455 / 0.3091 against bars b + 0.10 = 0.2231 / 0.2343 and 2 b = 0.2463 / 0.2685 -- the b + 0.10
bar is met, 2 b is met on comp1b only. That label belongs to a different tool (a transcript-proposes-missing-slot
call), and its +8 pp ceiling assumes an oracle that also picks the right span and type.

## 6. What this read does not claim

- No runtime candidate: R-FLAG / R-DROP / R-SWAP are system-applied oracle bounds; the owner supplement to decision 201
  forbids a system-default tool application.
- No claim about what the frozen core would decide if offered a `verify_span` tool: the AUCs measure signals the core
  could see, not the core's own calling policy; the core might use content the signals do not capture (the audio).
- The wider-label numbers are not a design: adding missing slots from a transcript needs span and type selection the
  oracle assumes perfect.
- The E4-1 disagreement signal exists only in a system that runs the E4-1 relisten step.
- In-sample single-signal precision values in the supplement's `single_signal_in_sample` break ties by roster order and
  are uninformative for binary signals; the cross-fit table is the reported precision.
- TRAIN construction-roster development numbers (decisions 28 and 86); no DEV, test or generalisation claim.

## 7. Recommendation to the coordinator

**Close the E5 verify-span line** (E5-2 as a model-initiated `verify_span` call over the E5-0 transcript), for three
independent reasons, each sourced above:

1. The registered stop condition fires: gold-span containment 0.7513 < 0.80 on Fold A (0.7606 on Fold B); the pinned
   transcript does not contain a quarter of the gold spans, worst on business_name (0.50) and person (0.548).
2. The prize is small and the check is weak: 29 helpful rows (2.69 %), a perfect-repair ceiling of +1.62 [+1.04,
   +2.28] pp, and a transcript that contains 28-87 % of the wrong values by kind across the four arms (flag precision 0.1215); every
   system-applied rule is <= 0 on all four arms (R-DROP -2.31 [-3.65, -1.00], R-SWAP tuned -0.03 [-0.14, +0.07]).
3. The decision is not learnable from what the core can see: no named signal reaches AUC 0.70 on the primary arm
   (best 0.6713; 0.7151 on comp1b), the best cross-fit two-signal rule is 0.6707 out of fold, and its precision stays
   under the b + 0.10 bar across the proposed band except on a 15-row low end with 2 hits; at 10 % calls the reachable
   yield is about +0.4 pp.

If the owner wants the transcript route kept alive, the only direction the oracle does not rule out is a different
tool form -- a transcript that proposes MISSING slots (106 rows, +8.21 pp oracle ceiling, cross-fit precision 0.2455 at
10 % calls on agree) -- which would need its own design, its own precondition on span/type selection and a stronger
ASR than the one whose containment failed here; "instrument more" on the verify form is not recommended.

## Coordinator verdict (Fable 5.1, 2026-09-30)

- **E5 verify-span route: CLOSED at the oracle.** The registered stop condition fires: Whisper large-v3 transcripts contain 0.7513 of the gold spans on Fold A (0.7606 on Fold B) against the 0.80 floor, worst where the slot errors are (business_name 0.50, person 0.55, time 0.72); exact-value preservation on the 63 E4-broken items passes (0.9365). Every deterministic rule is an oracle upper bound at or below zero (R-DROP -2.31 [-3.65, -1.00] on AGREE); the tool-call decision oracle finds 29 of 1,080 rows where a call would help (2.69 %, perfect-repair ceiling +1.62 pp) and no model-visible signal above AUC 0.67, so the proposed E5-2 gate (206) cannot be met (precision 0.07 at a 10 % call rate). E5-2 is not registered; the E5-2 gate confirmation is moot.
- **What survives.** The transcripts are a sealed instrument (E5-0 receipts, 0 core contacts). The one direction the oracle does not rule out is a different tool form — the transcript PROPOSING slots that are missing entirely (106 rows; perfect-selection ceiling +8.21 [+6.95, +9.57] pp; cross-fit precision 0.25 at a 10 % call rate, clearing b + 0.10 but not 2b) — which needs its own design and a stronger ASR; it belongs to owner decision 209 option B (a new evidence kind), not to this route. Development number (decisions 28/86).
