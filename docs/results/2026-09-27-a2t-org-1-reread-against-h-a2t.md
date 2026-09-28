# A2T-ORG-1 re-read against h_A2T: KEEP -- the HARMFUL verdict stands on official tool accuracy (-3.23 pp at n = 4,000, twice h_A2T); the secondary losses are inside the null

Read 2026-09-27 by the analysis agent (Claude Opus 5.5, worktree `/home/chao/saea-worktrees/fable-org1reread`, branch
`fable/org1reread`) for owner decision 166's records pass. This is the item that
`docs/results/2026-09-27-verdict-reclassification.md` section 7 deferred ("re-read it when A2T-AA lands"). A2T-AA has
landed (`docs/results/2026-09-27-a2t-aa-paired-400-read.md`), and owner decision 167 accepts its half-widths as
Audio2Tool's null: h_A2T = 1.625 pp official tool accuracy, 1.375 pp official exact match, 1.875 pp repo tool
accuracy, and the A/A's macro parameter-F1 offset of +2.23 pp as the parameter-F1 margin.

Zero model, tokenizer, encoder, scorer, server, GPU and network contacts. Every number below is arithmetic over sealed
per-sample scores. Nothing was re-scored or re-flown. No utterance, transcript, gold label, tool-call argument or model
output was printed or persisted. No verdict note, receipt or exposure-ledger row was edited.

## 0. The answer

| item | class | reason |
| --- | --- | --- |
| A2T-ORG-1 HARMFUL (the primary: official tool accuracy) | **KEEP** | -3.225 pp, CI95 [-4.30, -2.13] at n = 4,000, the population the verdict was read on. The point is 2.0x h_A2T (1.625). The CI95 upper bound is also below -h_A2T, and the point clears the stricter A/A bound of offset + h = 1.000 + 1.625 = 2.625. The half whose comparator flew at ORG-1's own `-np 2` geometry reads -2.76 [-4.20, -1.32] on 2,500 rows, which is also beyond h. The status word does not change. |
| The verdict's section 4 claim that "every secondary metric moves the same way as the primary" | **KEEP-PROVISIONAL** | At n = 4,000 the direction holds: exact match -0.65 and macro parameter F1 -0.78. Both magnitudes are inside their margins (1.375 and 2.23). On the paired 400 both signs reverse (+1.00 and +0.33), and both of those values are also inside the margins. Rule missed: a secondary loss read inside the carrier's own null, from a cross-flight contrast with no in-chain A/A. Settling action: none. The ORG line is closed, and ORG-1 is not a component of any later mechanism. |

Decision 166's rule was applied as briefed. **KEEP** applies when the HARMFUL verdict stands with |effect| beyond
h_A2T on the official metric, or beyond 2.23 on parameter F1. **KEEP-PROVISIONAL** applies when the direction stands
but the magnitude is inside the null. **ADJUST** applies when the sign or the verdict word changes. The HARMFUL word
rests on official tool accuracy, and that is where the rule is applied. The per-tier and per-domain mechanism
readings in the verdict's sections 1-3 and 5 are strata with no null of their own. This pass classifies nothing
about them (section 5 below).

## 1. What was read

| item | value |
| --- | --- |
| ORG-1 | `SAEA-A2T-ORG1-DOMAIN-GROUPED-V1` / `attempt-20260905T171519Z-org1groupedraw`, study commit `227c0ef2`. Run manifest sha256 `55a6c23a...2087` (the verdict's pin). Scores sha256 `dcb0a683dbae76258137657b6cd43db72347c3a6cfa2f05c171f0a05541c579c`. 4,000 rows. |
| comparator (as the verdict paired it) | each row's own sealed 2026-09-04 official-protocol output, merged from `SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1` (500 rows, manifest `17acd0f4...`, scores `0f9ff243...`), `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1` (1,500 rows, manifest `7de74291...`, scores `886fb623...`) and `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1` (2,000 rows, manifest `1f43aab3...`, scores `28b2f7c3...`). Every manifest digest equals the receipt's `baseline_sources` pin, and every manifest pins its scores bytes. |
| roster | `A2T-PAIRED-400-V1` (`docs/receipts/rosters/a2t-paired-400-v1.json`, split identity `965f145f...0990a`), 50 rows per tier, drawn once at seed 20260921 from ORG-1's own union-4000. All 400 ids are in ORG-1's 4,000, and the tiers agree. |
| context only | `SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1` (the A/A pair's comparator; manifest `a3fb34c6...`, scores `2071602b...`), same 400 ids: levels and official tool-verdict agreement only |
| verdict receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-org1-domain-grouped-4000-v1/result-summary.json` |
| interval | the `bootstrap` function of `scripts/analysis/a2t_aa_paired_read.py` (sha256 `48392fa5...1d7e`, the A2T-AA driver): tier-stratified paired bootstrap with the row as the resampling unit within tier, CI95, 10,000 draws, seed 20260903 (the A2T-AA recipe's). Delta = ORG-1 minus baseline. Natural-mixture and equal-tier weightings. |
| driver | `scripts/analysis/a2t_org1_reread.py` (new; imports the A2T-AA driver's scorer map and bootstrap) |
| machine result | `$SPEECHRL_DATA_DIR/analysis/SAEA-A2T-ORG1-REREAD-H-A2T-V1/reread.json`, sha256 `03df9a48141c46c5e3a40e5fbc483a05eb577c5be98894e9876bd4994d8963aa` (ids-free: levels, deltas, intervals, counts and hashes) |

The full-4,000 read reproduces the verdict's own numbers exactly: 61.40 -> 58.175, 194 saves / 323 harms / 3,483
ties, exact match -0.650 and macro parameter F1 -0.775. Only the interval level changes, from CI90 to CI95.

## 2. The paired differences (ORG-1 minus baseline, pp, CI95)

Every tier holds the same number of rows (500 in the full read, 50 in the paired 400). The natural-mixture and
equal-tier weightings therefore coincide in the point estimate, and they gave identical intervals.

| metric | margin | n = 4,000: base -> ORG-1 | n = 4,000: delta [CI95] | n = 400: base -> ORG-1 | n = 400: delta [CI95] |
| --- | ---: | --- | --- | --- | --- |
| **official tool accuracy** | h_A2T 1.625 | 61.40 -> 58.175 | **-3.225 [-4.301, -2.125]** (194 / 323 / 3,483) | 60.25 -> 58.25 | **-2.000 [-5.750, +1.500]** (24 / 32 / 344) |
| official exact match | h_A2T_em 1.375 | 18.35 -> 17.70 | -0.650 [-1.325, +0.001] | 14.75 -> 15.75 | +1.000 [-0.750, +3.000] |
| repo tool accuracy (`a2t-toolcall`) | h_A2T_repo 1.875 | 53.35 -> 51.025 | -2.325 [-3.426, -1.225] | 51.75 -> 51.00 | -0.750 [-4.500, +3.000] |
| official macro parameter F1 | A/A offset 2.23 | 29.28 -> 28.51 | -0.775 [-1.517, -0.051] | 27.88 -> 28.22 | +0.334 [-1.741, +2.364] |
| official micro parameter F1 (context) | -- | 24.40 -> 23.36 | -1.031 [-1.838, -0.237] | 22.02 -> 21.83 | -0.191 [-2.742, +2.298] |
| official parse rate (context) | A/A h 0.625 | 99.775 -> 99.35 | -0.425 [-0.675, -0.200] | 99.25 -> 98.75 | -0.500 [-1.250, 0.000] |

Saves / harms / ties are given for official tool accuracy. The paired 400 is a tenth of the population, and its CI95
half-width on the primary (3.625) is more than twice h_A2T. It neither confirms nor contradicts a 3-point loss. Its
point (-2.00) is beyond h_A2T and has the same sign as the verdict.

**By comparator geometry** (the verdict's own section 6 item 2 split, re-bootstrapped here):

| rows whose comparator flew at | n | official tool accuracy | exact match | repo tool accuracy | macro parameter F1 |
| --- | ---: | --- | --- | --- | --- |
| `-np 2` (ORG-1's geometry; tiers 1, 3, 4, 6, 7) | 2,500 | **-2.760 [-4.200, -1.320]** | -0.080 [-0.840, +0.680] | -1.920 [-3.440, -0.400] | -0.329 [-1.232, +0.586] |
| `-np 3` (tiers 2, 5, 8) | 1,500 | -4.000 [-5.667, -2.333] | -1.600 [-2.800, -0.400] | -3.000 [-4.667, -1.333] | -1.518 [-2.747, -0.292] |
| paired 400, `-np 2` tiers | 250 | +0.80 (19 / 17) | +2.00 | +2.00 | +1.43 |
| paired 400, `-np 3` tiers | 150 | -6.67 (5 / 15) | -0.67 | -5.33 | -1.49 |

## 3. Per tier (official tool accuracy unless named; pp)

| tier | n = 4,000: base -> ORG-1 (delta) | saves / harms | n = 400: base -> ORG-1 (delta) | saves / harms | n = 400: exact / repo tool / macro pF1 deltas |
| --- | --- | --- | --- | --- | --- |
| tier1_direct | 65.60 -> 63.60 (-2.00) | 26 / 36 | 68.00 -> 70.00 (+2.00) | 2 / 1 | 0.00 / +2.00 / 0.00 |
| tier2_parametric | 79.60 -> 74.80 (-4.80) | 17 / 41 | 80.00 -> 76.00 (-4.00) | 1 / 3 | -2.00 / -4.00 / -5.60 |
| tier3_multi_intent | 65.00 -> 63.20 (-1.80) | 37 / 46 | 62.00 -> 64.00 (+2.00) | 6 / 5 | +8.00 / +8.00 / +2.44 |
| tier4_implicit | 28.20 -> 26.80 (-1.40) | 25 / 32 | 24.00 -> 24.00 (0.00) | 4 / 4 | 0.00 / 0.00 / +1.00 |
| tier5_needle | 80.80 -> 77.40 (-3.40) | 21 / 38 | 90.00 -> 80.00 (-10.00) | 2 / 7 | 0.00 / -10.00 / +1.00 |
| tier6_correction | 75.80 -> 71.00 (-4.80) | 20 / 44 | 66.00 -> 64.00 (-2.00) | 2 / 3 | +2.00 / -2.00 / +1.67 |
| tier7_multiturn | 49.40 -> 45.60 (-3.80) | 30 / 49 | 42.00 -> 44.00 (+2.00) | 5 / 4 | 0.00 / +2.00 / +2.03 |
| tier8_intent_blending | 46.80 -> 43.00 (-3.80) | 18 / 37 | 50.00 -> 44.00 (-6.00) | 2 / 5 | 0.00 / -2.00 / +0.13 |
| **pooled** | **61.40 -> 58.175 (-3.225)** | **194 / 323** | **60.25 -> 58.25 (-2.00)** | **24 / 32** | +1.00 / -0.75 / +0.33 |

Per domain on the paired 400 (official tool accuracy): smart_home 55.56 -> 51.96 (-3.59, 306 rows, 19 / 30),
wearables 79.73 -> 83.78 (+4.05, 74 rows, 4 / 1), smart_car 60.00 -> 60.00 (0.00, 20 rows). On 50 rows one row is
2 points, so the per-tier and per-domain cells of the paired 400 are one- to five-row movements and carry no weight
alone. The A/A itself moved tiers by -4 to +4 with nothing changed.

## 4. Where the verdict's comparator differs from the A/A pair's -- for the coordinator to judge

1. **A different direct arm and request form.** ORG-1 was paired against the 2026-09-04 official-protocol cells.
   These are text-registry prompts from three runs at three study commits (`e61b424a`, `b52c22b0`, `6c13fb6d`). h_A2T
   was measured on the 2026-09-15 native-role direct form (`SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1`) re-flown
   twice. On the same 400 ids the two direct arms sit at 60.25 and 61.75 official tool accuracy, and their
   official tool verdicts agree on 376 of 400 rows. They are close in level, but they are not the same request, so
   h_A2T is borrowed from a neighbouring form rather than measured on ORG-1's own.
2. **A different serving geometry.** The A/A flew on session v3, `-np 3` x 32,768 tokens per slot, `max_tokens`
   2048. ORG-1 flew at `-c 49152 -np 2` (24,576 per slot, `max_tokens` 256). Its comparator flew at `-np 2` (tiers 1,
   3, 4, 6, 7) and `-np 3` (tiers 2, 5, 8) on an older runtime session. The A2T-AA read shows that byte identity
   depends on the serving slot: 93.2 % for rows on the same slot against 69.7 % for rows on different slots.
3. **A cross-flight contrast with no in-chain A/A.** ORG-1 is one flight against an older sealed comparator, and
   instrument rule 4 would not admit a claim from that design today. h_A2T is a within-chain null. The between-day
   term is known only from A2T-AA's context section: each pass minus the 2026-09-15 direct rows read -1.0 and 0.0 on
   official tool accuracy. -3.225 exceeds h (1.625), offset + h (2.625), and the SLURP-derived scaled bar at
   4,000 rows (1.30). The KEEP does not rest on the choice between them.
4. **A different n.** h_A2T is valid at n = 400. The verdict was read at n = 4,000, where a same-design null would be
   narrower. Holding the 4,000-row effect to the 400-row h is conservative in the direction of KEEP-PROVISIONAL, and
   the effect still clears it.
5. **The paired 400 carries the geometry confound more heavily than the 4,000.** Its loss sits entirely in the
   150 rows whose comparator flew at `-np 3` (-6.67). The 250 geometry-matched rows read +0.80. On the full
   population the geometry-matched 2,500 rows read -2.76 [-4.20, -1.32], so the confound does not carry the loss
   there. The 400-row slice is too small to separate the two.

## 5. Not classified here

- The mechanism readings (cross-domain twin misses 621 -> 521, same-domain 898 -> 1,118, the named confusion
  pairs) are counts over one sealed pair and carry no interval. The "prompt-form cost" reading rests on per-domain
  strata: wearables -3.38 on 857 rows at n = 4,000, but +4.05 on 74 rows of the paired 400. Under decision 166's
  convention a per-stratum reading is not evidence. The verdict's own caution that a registry-shape change owes a
  same-shape control is a design rule, not a result, and KC-A1c already applied it.
- No owner decision rests on ORG-1 beyond closing the ORG-1 line and routing A2T-ORG-2 / KC-A1 to the official
  baseline, and the KEEP leaves both in place.

## 6. Records and checks

- New: this note, and `scripts/analysis/a2t_org1_reread.py`.
- Annotated (appended, nothing deleted or rewritten): `docs/results/stage2-results-ledger.md`, with one line after
  the A2T-ORG-1 structured row and one line in the reclassification routing section.
  `docs/results/stage2-results-ledger.json`, with a `reclassification_2026_09_27` field on the A2T-ORG-1 row and a
  `followups` entry in the top-level block of that name. The reclassification counts (57 items) are unchanged,
  because this item is a follow-on outside them.
- Not edited: the ORG-1 verdict note, its receipt, the exposure ledger, the owner-decision registry, the
  reclassification note and `docs/handoff/HANDOFF-TO-CHATGPT.md`.
