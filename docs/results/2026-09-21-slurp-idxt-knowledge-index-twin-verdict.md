# HARMFUL (CONTROL) -- cell IDXT, the derangement twin of the knowledge index (`slurp-knowledge-index-twin-v1`, seed 20260920) on the sealed tool-free B1-notool base: the official pooled SLU-F1 delta against the comparator is -9.9697 pp [-12.46, -7.32], a measured loss on the primary guard under owner decision 25, while intent is non-inferior at +0.1852 pp [-2.00, +2.31]. **The twin is a CONTROL and enters no plan**: no default SLURP fragment, no harness-admission entry, no module, no contingency of its own. Its numbers exist only as the form term of the knowledge-index decomposition, and they are reported in the cell IDX verdict as such.

Read 2026-09-21 by the implementer, model-free, from the sealed bytes of three flights. Zero model,
tokenizer, encoder, ASR and server contacts; the official score was produced once inside each
sealed flight and was never re-run on a decision number. The only scorer invocations were the two
model-free companions (projection v3, TRAIN symmetric sibling) over COPIES of the sealed outputs.
Development numbers on an exposed discovery roster (owner decision 28).

Analysis root: `analysis/SAEA-SLURP-B1-INDEX-TWIN-PAIRED-ANALYSIS-V1` under `SPEECHRL_DATA_DIR`.
Driver: `twin_cell_read.py` (owner decision 58 -- every table below is regenerable by
`python twin_cell_read.py --stage <name> ...`; the root README carries the exact commands and the
stage-to-table map).

## 0. The cell

| item | value |
| --- | --- |
| arm | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-INDEX-TWIN-V1` / `attempt-slurp-native-exemplars-k20-index-twin-train-fold-a-generation-v1`, FINALIZED at study commit `9f2997d0a482d845d1543829951a9b9cf6d21763`, empty dirt |
| sealed digests | run manifest `12aae002...a3c0ea9`, scores `aaf7aefa...f44f3fc5`, outputs `738a1d6f...6bcb0b79` -- all three re-derived from the bytes by this read |
| factor | `native_episode.knowledge_index` armed on `slurp-knowledge-index-twin-v1` (release `c77021cb...`, snapshot `9620a595...`, `twin_of` = `slurp-knowledge-index-v1` / `f6d61056...`), one factor against the sealed base |
| comparator (gating) | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1`, sealed, never re-flown: official 62.1295 / 80.0000 |
| beside (never a gate) | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-INDEX-V1` / `...-index-train-fold-a-generation-v1`, FINALIZED at `38984e80`, scores `c2268558...`: official 54.7576 / 77.5926 |
| population | TRAIN Fold A, 1,080 rows, 18 scenarios x 60, 125 speaker clusters, 523 headset / 557 far-field, split identity `61b0f062...`, role `discovery` |
| margins | h_SLU 1.2350 / h_intent 1.2212, the decision-38 fallback (cell B1r's own null). **The B1-notool configuration has no replicate of its own**; the margins are imported from the exemplar-supplied configuration and this verdict says so wherever it reads against them. |
| estimator | paired whole-speaker cluster bootstrap, 10,000 draws, seed 20260915; scenario-stratified row bootstrap as sensitivity |

## 1. STOP, before any contrast was read

| clause | registered | recomputed from the sealed score bytes | reproduced |
| --- | ---: | ---: | --- |
| comparator official pooled SLU-F1 | 62.1295 | 62.1295 | yes |
| comparator official intent | 80.0000 | 80.0000 | yes |
| cell IDX official pooled SLU-F1 | 54.7576 | 54.7576 | yes |
| cell IDX official intent | 77.5926 | 77.5926 | yes |

Every arm's `pooled_f1` over its own per-sample rows reproduces its official aggregate to 1e-6, on
both micro metrics, on all three arms. Every manifest is COMPLETED, pins the score bytes this read
used, carries the registered split identity with role `discovery`, and was sealed on a clean tree.
No arm's decision score carries a label projection.

The two margins are not re-measured here. They were reproduced from the sealed bytes by the
B1-notool read (`analysis/SAEA-SLURP-B1-NOTOOL-PAIRED-ANALYSIS-V1/score-contrasts.json`, quoted with
its hash in `cache/stop.json`), whose `own_null_reproduction` block recomputed cell B1r's own null
field by field with the same estimator, seed and draws and matched h_SLU 1.2350 and h_intent 1.2212
to 1e-4.

## 2. The control reading, under the twin's registered rule

Delta = the twin minus the sealed comparator, in percentage points; negative is worse.

| guard | comparator | twin | delta pp | speaker CI95 | speaker CI90 | scenario-strat CI90 | equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| official pooled SLU micro F1 (primary) | 62.1295 | 52.1598 | **-9.9697** | [-12.46, -7.32] | [-12.07, -7.74] | [-11.91, -8.06] | -9.84 |
| intent (scenario+action) accuracy | 80.0000 | 80.1852 | **+0.1852** | [-2.00, +2.31] | [-1.65, +1.96] | [-1.30, +1.67] | +0.19 |

HARMFUL, under owner decision 25's form, on two independent clauses of the primary guard: the point
estimate -9.9697 pp is far below -1.2350, and the CI95 upper bound -7.3154 pp is below zero. The
second guard is not breached: intent is non-inferior (CI95 lower -2.00 does not clear -1.2212 as a
non-inferiority proof either, so the honest statement on intent is *no measured loss, and
non-inferiority not proven at the imported margin*).

Secondaries, same contrast: span F1 49.03 -> 40.18 (-8.85 [-11.90, -5.53]); scenario accuracy
86.48 -> 87.41 (+0.93); action accuracy 81.11 -> 81.57 (+0.46); per-row mean exact slot F1
31.53 -> 28.35 (-3.19 [-5.31, -0.98]); per-row mean SLU-F1 40.69 -> 36.26 (-4.43 [-6.26, -2.44]).
Intent saves 50 / harms 48 / ties 982, exact two-sided McNemar p = 0.9196 -- the intent guard is a
coin flip, and the whole loss is in the entities.

Companions beside the official number, deciding nothing. Projection v3: comparator 63.5973,
twin 52.9948, delta -10.6025 [-13.15, -7.94]; v3 intent -0.6481 [-2.61, +1.31]. TRAIN symmetric
sibling: comparator 63.9741, twin 53.4019, delta -10.5721 [-13.22, -7.81] (34 false merges on every
arm). Both companions carry the same sign and the same magnitude as the official read.

**This reading closes nothing and opens nothing.** A HARMFUL twin is itself a finding about the
FORM -- the constant index block, its pointer blocks and its budgeted expansions harm by about ten
points of SLU when their content is destroyed -- and it is reported in the IDX verdict. The twin
enters no plan whatever it reads.

## 3. The form / content decomposition

| effect | contrast | official pooled SLU-F1 | CI95 | intent | CI95 |
| --- | --- | ---: | --- | ---: | --- |
| **FORM** | twin minus comparator | **-9.9697** | [-12.46, -7.32] | **+0.1852** | [-2.00, +2.31] |
| **CONTENT** | cell IDX minus twin | **+2.5978** | [+0.80, +4.49] | **-2.5926** | [-4.33, -0.86] |
| TOTAL | cell IDX minus comparator | -7.3719 | [-9.72, -4.80] | -2.4074 | [-4.56, -0.32] |

Additivity holds exactly on the point estimates (form + content = -7.3719 pp = total, to 9e-16);
the intervals do not add and are not added.

Read plainly: **the index form carries the loss and its content recovers a quarter of it.** With
every id-to-line correspondence destroyed the arm loses 9.97 pp of SLU; restoring the correspondence
buys back 2.60 pp [+0.80, +4.49] and costs 2.59 pp of intent [-4.33, -0.86]. Cell IDX's total
-7.37 pp is therefore not a content failure of the knowledge index -- it is dominated by the
rendering form the index imposes, which the twin holds fixed.

One honesty note on what "FORM" means here. The twin is form-matched but not content-neutral: its
L2 cards are actively *wrong* for their ids. The form term is therefore "the index rendering with
its correspondence destroyed", not "the index rendering with no content at all", and it is an upper
bound on what a content-free rendering of the same shape would cost. This is inherent to a
derangement twin and is exactly why the twin is a control and never a plan candidate.

## 4. The expansion-block length difference (owner decision 62, mandatory)

From both sealed receipts' `knowledge_index.contacts[*].expansion_block_chars`. The per-row figure
is the row's largest expansion block; the perception contact carries none and every later contact of
a row renders the same block.

| quantity | value |
| --- | ---: |
| rows | 1,080 |
| twin expansion block, chars/row | mean 5,741.0, median 5,614.5, p10 4,683.9, p90 6,781.2, min 1,358, max 9,439 |
| cell IDX expansion block, chars/row | mean 8,766.9, median 9,073.5, p10 6,738.3, p90 10,261.2, min 2,024, max 12,700 |
| signed difference (twin minus IDX), chars | mean **-3,025.9**, median -3,040, min -7,729, max +2,061 |
| absolute difference, chars | mean **3,066.0**, median 3,040, p90 5,021, min 1, max 7,729 |
| sum of signed differences | **-3,267,983** (the twin's blocks are shorter in aggregate) |
| rows where the twin block is longer / IDX longer / equal | **25 / 1,055 / 0** |
| Pearson r / Spearman rho, signed difference vs per-row SLU-F1 difference | +0.0745 / +0.0959 |
| Pearson r / Spearman rho, \|difference\| vs per-row SLU-F1 difference | -0.0759 / -0.0960 |

| quartile of \|difference\| | n | mean \|difference\| chars | twin mean per-row SLU-F1 | IDX mean per-row SLU-F1 | mean per-row SLU-F1 difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| Q1 (most nearly matched) | 270 | 1,384 | 32.65 | 33.48 | **-0.83** |
| Q2 | 270 | 2,495 | 38.67 | 39.42 | **-0.75** |
| Q3 | 270 | 3,596 | 33.97 | 36.83 | **-2.86** |
| Q4 (most mismatched) | 270 | 4,789 | 39.74 | 44.21 | **-4.47** |

This is the single most important caveat of the decomposition, and it goes against the design's own
expectation. The derangement preserves the *multiset* of 54 slot cards, so the sum of per-card
length differences is zero by construction; but each row expands only the four cards its own
retrieval pointed at, and on 1,055 of 1,080 rows the cards the twin happens to hand that row are
shorter than the ones cell IDX hands it (mean 3,026 characters shorter per row, about 35 % of the
block). The design's "mean absolute difference about 641 characters, sum zero over the 54 cards" is
a statement about the card multiset; it is **not** the per-row, retrieval-weighted distribution, and
the per-row distribution is five times larger and one-sided.

The correlation with the per-row score difference is weak (|r| < 0.10), but the quartile table is
monotone in the tail: rows whose blocks are nearly the same length lose 0.8 pp of per-row SLU-F1 to
cell IDX, rows whose blocks differ most lose 4.5 pp. So a material part -- not all -- of the
measured CONTENT effect (+2.60 pp) is a length effect rather than a correspondence effect. The
content term should be read as an upper bound on what restoring the id-to-line correspondence buys.

## 5. Index consumption (decision 61; the twin clause of decision 64)

**(a) Citations.** Solver citation is permitted on both arms. Twin: 109 resolved, 3 unresolved, at
least one citation on 42 of 1,080 rows (3.89 %). Cell IDX: 24 rows (2.22 %), 2 unresolved. Citation
is near zero on both arms, and the arm whose ids point at the *wrong* content cites more often than
the arm whose ids are correct. Citation behaviour does not track content.

**(b) Pointer use, against the twin's own deranged pointer blocks as the null reference.**

| quantity | twin, own answers vs its own deranged blocks | **comparator's answers vs the SAME deranged blocks (the null reference)** | cell IDX, own answers vs its own blocks | comparator vs IDX's blocks |
| --- | ---: | ---: | ---: | ---: |
| delivered intent lies in the pointed intent set | **97.69 %** (1,055/1,080) | 95.35 % (1,026/1,076) | 91.76 % (991/1,080) | 95.35 % (1,026/1,076) |
| every delivered slot type lies in the pointed set | **78.75 %** (656/833) | 63.80 % (490/768) | 83.41 % (709/850) | 66.41 % (510/768) |
| delivered slot-type instances in the pointed set | **83.32 %** (899/1,079) | 69.41 % (683/984) | 86.04 % (912/1,060) | 71.24 % (701/984) |

This is decision 64's clause answered directly. Both index arms raise slot-type pointer agreement
about 14 points above the null reference (twin +13.9 pp, IDX +14.8 pp) -- the pointer block is
plainly followed. But the twin follows it *as well as* cell IDX does, and on the intent axis it
follows it **better** (97.69 % against 91.76 %), while the null reference already sits at 95.35 %.
A twin whose pointer-use share equals the index cell's is, in the decision's own words, direct
evidence that the pointers were not read *as knowledge*: what the pointer block supplies is a label
vocabulary the answer conforms to, not content the answer consults.

**(c) Expansion use.** Delivered slot TYPE against gold slot type, split by whether the row's own
index block expanded that type's L2 card, only pointed at it, or did not carry it.

| bucket | arm | precision | recall | F1 | fillers | spoken-form share |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| expanded | comparator (vs twin blocks) | 67.51 | 75.71 | 71.37 | 413 | 99.76 % |
| expanded | twin | **48.81** | 75.42 | 59.27 | 560 | 100.00 % |
| expanded | cell IDX | **51.54** | 85.91 | 64.43 | 630 | 99.84 % |
| pointed only | comparator (vs twin blocks) | 68.53 | 77.17 | 72.59 | 295 | 99.66 % |
| pointed only | twin | 52.84 | 73.23 | 61.39 | 366 | 99.45 % |
| pointed only | cell IDX | 62.63 | 72.94 | 67.39 | 307 | 99.67 % |
| not in the block | twin | 70.56 | 43.20 | 53.59 | 184 | 98.91 % |
| not in the block | cell IDX | 75.00 | 39.93 | 52.11 | 149 | 98.66 % |

The mechanism of the SLU loss is visible here and is the same on both index arms: expanding a card
makes the system *emit* that slot type. Precision in the expanded bucket collapses from about 68 %
(the comparator answering the same rows) to 48.8 % (twin) and 51.5 % (IDX), while recall holds or
rises. Delivered entities per flight: comparator 1,013, IDX 1,086, twin 1,110. The index form buys
recall with precision, and the pooled SLU micro F1 pays for it.

**(d) Format compliance**, under the one machine-checkable predicate the repository owns
(`rails.slot_audit`, `saea-spoken-form-v1`: no ASCII digit, colon or slash). A slot id is in scope
when *that view's own* `Admissible formats` line names the constraint -- 4 of 54 ids in each view,
and because of the derangement they are **different** ids: the true view names `S/date`,
`S/podcast_descriptor`, `S/time`, `S/timeofday`; the twin names `S/game_name`, `S/media_type`,
`S/music_genre`, `S/weather_descriptor`.

| reading | in-scope fillers | compliant |
| --- | ---: | ---: |
| twin, under its OWN deranged lines | 64 | 100.00 % |
| twin, under the TRUE lines (types it never advertised the rule for) | 203 | **99.01 %** |
| cell IDX, under the TRUE lines | 217 | 98.16 % |
| comparator (no index at all), under the TRUE lines | 196 | 98.47 % |
| comparator, under the deranged lines | 98 | 100.00 % |

Nothing moves. The twin obeys the spoken-form rule on `time`/`date`/`timeofday`/`podcast_descriptor`
at 99.01 % *although its prefix advertised that rule for four entirely different slot types*, and
the comparator, which saw no index at all, obeys it at 98.47 %. Compliance is a property of the
model and the exemplars, not of the L1 line. This is the cleanest single piece of evidence in the
cell that the L1 line is not read.

**(e) The triple.** Comparator 62.1295 / 80.0000; cell IDX 54.7576 / 77.5926; twin 52.1598 / 80.1852.

**Determination: undecided, with NON-CONSUMPTION the better-supported branch on the twin's own
evidence.** Exactly one clause points at CONSUMPTION -- cell IDX differs from the twin beyond the
own null on SLU (+2.5978 pp, CI95 lower +0.80, against h_SLU 1.2350) -- and that clause is
confounded by section 4: the twin's expansion blocks are shorter on 1,055 of 1,080 rows and the
loss grows monotonically with the mismatch. Meanwhile (a) citations are near zero and *higher* on
the twin, (b) pointer use is elevated equally on both arms and higher on the twin for intent,
(c) the expanded-bucket precision collapse is the same shape on both arms, and (d) format compliance
does not move at all and does not follow the advertised line. The arms also disagree in sign on
intent (+0.19 twin, -2.41 IDX), so "(a)-(d) move in the same direction as the score" is not
satisfied on either metric. MISLEADING TERSENESS is not evidenced: cell IDX does lie below the
comparator, but (d) is flat (98.16 % against 98.47 %, a difference of one filler).

The consumption determination of record, and the contingency it routes -- the richer-granularity
variant on NON-CONSUMPTION, closure at decision 52's defaults on MISLEADING TERSENESS -- belong to
the cell IDX verdict, which reads the same evidence from the index side. This verdict states the
twin's half and takes no routing decision.

## 6. Structural acceptance, restated on 1,080 rows

The twin's registered `smoke_acceptance` list, checked on the flown arm rather than on the four
smoke rows. Every clause holds.

| clause | value |
| --- | --- |
| one system-message sha over every contact | **yes** -- exactly one, `996d1f5727d05b6681215ca6023450ebdf73fee14a9dd9bcbdbaa16ab8abcacb`, over all 4,559 contacts of all 1,080 rows |
| index receipt on every contact | **yes** -- 4,559 of 4,559 carry both `index_sha256` and `system_message_sha256`; one index digest `cf754db2...`, one length 17,265, on every row |
| view pins on every row | release `c77021cb...` 1080/1080, snapshot `9620a595...` 1080/1080, `view_id` `slurp-knowledge-index-twin-v1` 1080/1080, `twin_of` = `slurp-knowledge-index-v1` / `f6d61056...` 1080/1080 |
| rendered header keeps the SOURCE view id | **yes, measured** -- the constant index is 17,265 characters on the twin *and* on cell IDX, with different bytes. The twin's own id is five characters longer, so a header carrying it would have made the index longer; the equal length is the proof that no byte before the index body shifted |
| degradation steps | **0** |
| granularity and budgets constant | 1080/1080 on `{edge: L0 Confusable exclusions, intent: L1 Activation boundary, slot: L1 Admissible formats}` and on pointer 3/8/3 + expansion 5/4/0 |
| no request carries a tools array | **yes** -- 4,559 of 4,559 requests carry `tool_schemas_count` 0 and `tool_choice` `none` |
| tool calls | **0** (no role holds an authority on the 0-B base) |
| row accounting | 1,080 in / 1,080 out, no row dropped, no sample id invented; 4,559 contacts, 4.221 per row |
| contacts per row | 3: 41, 4: 945, 6: 2, 7: 92 (comparator 3: 8, 4: 1,032, 7: 40; cell IDX 3: 19, 4: 989, 6: 1, 7: 71) |
| selection refusals | none recorded |

## 7. Dispositions

| arm | finite completions | planner_action_illegal | terminal reasons | REVISE routes | rows with a revision |
| --- | ---: | ---: | --- | ---: | ---: |
| twin | **43** | **4** | finite_completion 43, revision_limit 8 | 102 | 92 |
| cell IDX | 20 | 1 | finite_completion 20, revision_limit 9 | 81 | 71 |
| comparator | 8 | 0 | finite_completion 8, revision_limit 3 | 43 | 40 |

E13 (`deliver-latest-or-abstain`) and E22 (`continue-without-answer`) are harness declarations that
render no request byte; a finite-completion row is retained and scored as delivered and is never
filtered. No ReAct exhaustion occurred on any arm -- with no tool in the system the Reviewer cannot
loop on one.

The finite-completion count is non-zero, so the registered diagnostic is reported beside the
registered all-rows number, which stays the number the decision rule reads:

| primary metric | rows | pooled SLU-F1 delta | CI95 | intent delta | CI95 |
| --- | ---: | ---: | --- | ---: | --- |
| all rows (the REGISTERED number) | 1,080 | -9.9697 | [-12.46, -7.32] | +0.1852 | [-2.00, +2.31] |
| finite-completion rows excluded | 1,037 | -9.6886 | [-12.24, -7.17] | +0.3857 | [-1.86, +2.55] |

The verdict does not change: the 43 rows carry 0.28 pp of the 9.97 pp loss.

`planner_action_illegal` fires on 4 rows (item E8c: a row disposition, not a flight abort -- the row
is retained, delivers its committed draft, and records the sha256 and character count of the
offending action text). Cell IDX carries 1, the comparator 0. Both counts rise with the index form.

## 8. Efficiency

The server-log join is scoped to **this attempt's own sealed contact window**. The twin's flight
receipts give `contact_window` = 1789954267.010 .. 1789959295.733 epoch, i.e. **2026-09-21T01:31:07Z
to 02:54:55Z**; the session receipt's `started_at` converts that to the log's own relative clock
(32,165.0 s .. 37,193.7 s), and only tasks whose launch and release records fall inside that window
(+/-5 s) are selected. Cell IDX flew 2026-09-20T23:50:18Z .. 2026-09-21T01:18:40Z on the *same*
resident session and lies wholly outside the window, so none of its tasks can enter the join. The
proof is the per-slot count: client contacts 1,092 / 1,172 / 1,176 / 1,119 on slots 0-3 against
server tasks 1,092 / 1,172 / 1,176 / 1,119 -- exact, on every slot. The resident llama-server was
never started, stopped or queried.

**Join quality: 4,559 of 4,559 contacts join exactly, 100.00 %. The per-position figures below are
measurements, not estimates.**

| quantity | twin | cell IDX | comparator | source |
| --- | ---: | ---: | ---: | --- |
| generation contacts (per row) | 4,559 (4.221) | 4,516 (4.181) | 4,432 (4.104) | generation manifest |
| repeated speech seconds | 12,999.48 | 12,853.98 | 12,687.05 | generation manifest |
| client prompt tokens / row | 32,219.8 | 33,750.0 | 33,082.0 | generation manifest |
| completion tokens total | 355,292 | 339,457 | 266,131 | generation manifest |
| prefilled tokens / row | **2,795.7** | -- | -- | server.log join |
| cache hit share | **91.32 %** | -- | -- | server.log join |
| aggregate prefill tok/s ; decode tok/s | 600.4 ; 70.7 | -- | -- | server.log join |
| packet re-decodes / row | 0.996 | -- | -- | server.log join |
| truncations | 0 | -- | -- | server.log join |
| GPU hours / 1,080 rows | **1.2474** | 1.3340 | 1.6108 | monitor active seconds |
| generation wall seconds | 5,028.7 | 5,302.4 | 6,400.4 | flight receipts |
| wall seconds / row | 4.656 | 4.910 | 5.926 | flight receipts |
| contacts / minute (server.log releases) | **56.84** | -- | -- | server.log release records |
| slot occupancy ; utilisation ; parked | 0.740 ; 71.33 % ; 10.47 % | 0.729 ; 74.96 % ; 9.29 % | 0.787 ; 77.72 % ; 9.21 % | flight receipts + monitor |
| mean power | 82.60 W | 83.51 W | 84.75 W | monitor |
| projected 13,078-row read | **15.10 h** | 16.15 h | 19.51 h | GPU h/1,080 scaled |

Per position (the five-position program, plus the revision loop's three extra positions):

| position | role | n | client prompt med | prefilled med | cached | generated med | latency p50 / p90 | packet re-decode | prefilled/row | share of row prefill |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | perception | 1,080 | 6,414 | 385 | 93.94 % | 138 | 4.77 / 5.99 | 99.63 % | 389 | 13.91 % |
| 1 | solver | 1,080 | 7,920 | 1,777 | 77.36 % | 24 | 2.58 / 3.40 | 0.00 % | 1,796 | **64.23 %** |
| 2 | reviewer | 1,080 | 7,896 | 237 | 96.99 % | 133 | 4.64 / 8.18 | 0.00 % | 238 | 8.52 % |
| 3 | planner | 1,039 | 8,083 | 301 | 96.20 % | 2 | 0.42 / 1.77 | 0.00 % | 296 | 10.57 % |
| 4 | solver (revision) | 94 | 8,392 | 340 | 95.91 % | 25 | -- | 0.00 % | 30 | 1.06 % |
| 5 | reviewer (revision) | 94 | 8,361 | 235 | 97.18 % | 145 | -- | 0.00 % | 21 | 0.73 % |
| 6 | planner (revision) | 92 | 8,533 | 311 | 96.31 % | 2 | -- | 0.00 % | 27 | 0.96 % |

The index form does what it was designed to do on cost. Prefilled tokens fall to 2,796 per row --
the constant 17,265-character index is prefilled once per slot and then cached, so the cache hit
share is 91.3 % and the Solver's own expansion block is the only position that still pays
(64 % of all prefill). GPU hours per 1,080 rows fall 22.6 % against the comparator (1.2474 against
1.6108) and 6.5 % against cell IDX, because the twin's expansion blocks are the shorter ones. The
projected 13,078-row read falls from 19.5 h to 15.1 h. **None of this is claimable on this cell**:
the arm that produced it is a control that enters no plan, and the efficiency gain belongs to the
index form, which cell IDX measures at 16.15 h.

## 9. Per-scenario, both weightings

Full tables: `per-scenario-tables.json` (natural mixture and equal-scenario for all three
contrasts, both micro metrics and all five per-row metrics). Equal-scenario deltas for the gating
contrast: pooled SLU -9.84 pp against the natural-mixture -9.97 pp; intent +0.19 pp on both.
The two weightings agree.

The loss is broad, not a single scenario: 16 of 18 scenarios lose pooled SLU-F1, the worst being
`audio` -37.61, `music` -27.16, `social` -21.48, `transport` -21.47, `iot` -16.83; only `qa` (+5.51)
and `general` (+1.60) gain.

Intent band (owner decision 17, a diagnostic and never a gate): on the gating contrast **no scenario
loses intent beyond its own band** (no CI95 upper bound below zero), and one scenario is flagged at
five or more net harmed rows -- `iot`, -8.33 pp, 5 net harmed, CI95 [-18.03, 0.00]. Reported beside
the verdict; it does not change it, which is already HARMFUL on the roster-level measured loss.

Beside, on the content contrast (IDX minus twin), two scenarios lose intent beyond the band --
`play` (-48.33 pp, 29 net harmed, CI95 [-61.73, -34.04]) and `audio` (-6.67 pp, CI95
[-17.14, -1.67]) -- with `play` also decision-17 flagged. A 48-point intent collapse on one scenario
when the correct intent lines are restored is the largest single anomaly in this cell and belongs to
the cell IDX verdict's own diagnosis; this read only records it.

## 10. Cost against the registered ceilings

| figure | realized | registered ceiling |
| --- | ---: | ---: |
| generation contacts (run-cumulative) | 4,559 | 11,880 |
| repeated speech seconds | 12,999.48 | 33,930 |
| FIT request-fit receipts / endpoints | 4,559 / 18,236 | -- / 47,520 |
| GPU hours (fit inclusive) | 1.2474 | 12.0 |
| native task-contract tool calls | 0 | 0 (preregistration section 5) |
| official complete scoring jobs | 1 | 1 |

Every request fits: minimum margin 14,870 tokens, at the planner; maximum required 9,706 tokens
against the 24,576-token slot. No truncation on any of the 4,559 contacts.

## 11. What this read could not verify

* **No replicate of this cell, and no replicate of its base.** The margins are cell B1r's, imported
  under the decision-38 fallback; the B1-notool configuration has no own null. The -9.97 pp loss is
  eight times the imported margin, so the verdict does not turn on the import, but the intent
  guard's *non-inferiority* cannot be proven at an imported margin and this verdict does not claim
  it.
* **The length confound is measured, not removed.** Section 4 shows the twin's expansion blocks are
  systematically shorter; no length-matched twin was flown, so the content term (+2.60 pp) cannot be
  separated from the length term with the sealed bytes alone.
* **Format compliance covers 4 of 54 slot types.** The repository owns exactly one machine-checkable
  format predicate; the other 50 `Admissible formats` lines are prose from which no regex can be
  derived without inventing one. The compliance table is therefore a narrow probe, honestly labelled
  as such, and 64-217 fillers per cell is a small denominator.
* **Gold slot types were read to count precision and recall.** No gold label, filler or utterance
  text was printed or persisted by the read; only aggregates left the process.
* **`server.log` is not hash-pinned.** The resident session is still appending to it for later
  flights, so its whole-file digest is not stable; the window scoping and the exact per-slot counts
  are the audit path instead.
* **The consumption routing decision is not taken here.** It belongs to the cell IDX verdict.

## 12. Artefacts

All under `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B1-INDEX-TWIN-PAIRED-ANALYSIS-V1/`; the README in
that directory hashes every input and output and carries the exact command for every stage.

| file | sha256 |
| --- | --- |
| `score-contrasts.json` | `821acfd51d542ec7cc9e61e35cb051acf34382618473168e29bf6dba607e0af2` |
| `efficiency.json` | `fc8220981a12627b837a2efd66225077fe22fa05433f6c8a455d0a1fc16e7d4a` |
| `throughput-tables.json` | `18e7d1586c9752975b20b0f5736acbbb3b122ff080d3a14aa09aebc1da7eea3c` |
| `per-scenario-tables.json` | `ae39a50b2d42794c2845766ee773daf12152d70a1400f2dfc489322637365310` |
| `structural.json` | `8b872ba99f73bdf0292f1f8a98f31151e9df94c13063616c93e9babcfdbc3b67` |
| `length-difference.json` | `e2f0040bc6ed8dd5ed426184416e3b748c3ebf746a6f8ea3fffda208d33611fc` |
| `twin_cell_read.py` (the driver) | `c740df7ef7ad819896a36ca12434ab169d342a5c237b7ee0efe1c4264557e09b` |
| `README.md` | `7f6eb264bdff910aba676c5a72d029dfbcfca9b4d7ac13d2f96926ee373b7d28` |

## 13. Claim boundary

Descriptive paired read on historically exposed TRAIN Fold A discovery rows, plus a cost measurement
of the same flight. The twin is a CONTROL and enters no plan. No superiority, generalization,
component-causal, bar or confirmatory claim; no cross-carrier claim; no geometry claim; no claim
about the development bar. TRAIN Fold A is an exposed discovery roster and these are development
numbers (owner decision 28); they are never compared with a published TEST baseline.
