# HARMFUL -- cell IDX: the knowledge index + pointer block on the B1-notool base, SLURP TRAIN Fold A, 1,080 rows

**Both registered guards show a measured loss against the sealed B1-notool arm.** Official pooled
SLU-F1 falls **-7.3719 pp, CI95 [-9.7248, -4.7967]** (62.1295 -> 54.7576) and intent falls
**-2.4074 pp, CI95 [-4.5554, -0.3188]** (80.0000 -> 77.5926). Each point estimate is below its own-null
margin (-1.2350 / -1.2212) **and** each CI95 upper bound is below zero, so owner decision 25's HARMFUL
form is satisfied twice over on each guard. Under the preregistration's section 3 the form is
**closed at decision 52's provisional defaults** and decision 52 reopens for the owner.

**The index consumption statement (owner decision 64, the recipe's `decision_rule.consumption`), now
decided WITH the twin, is MISLEADING TERSENESS.** The frozen core does read the index -- the delivered
slot types lie inside the row's pointed set on **86.28 %** of delivered instances against the base's
**71.77 %** measured against the *same* pointer blocks, and in the stratum whose L2 slot card was
expanded the arm's type-level recall rises 0.764 -> 0.859 -- but what the terse L1 line carries is not
enough to be right: precision in that same expanded stratum **collapses 0.671 -> 0.516**, filler format
compliance falls **99.31 % -> 98.71 %**, and the official number falls 7.37 pp. The line changes the
answer in the direction it points and the change is wrong. That is misleading terseness, not
non-consumption: NON-CONSUMPTION is excluded because the arm lies far outside the twin's null on both
metrics, and CONSUMPTION is excluded because (a)-(d) do not move together with the score (the deranged
twin cites *more* index ids than the arm, 42 rows against 24).

**The efficiency result, which is this cell's registered deliverable, is large and in the promised
direction.** Prefilled tokens per row fall **8,019.8 -> 3,379.1 (-57.9 %)**, GPU hours per 1,080 rows
**1.6108 -> 1.3340 (0.828x)**, contacts per minute **42.91 -> 53.41 (1.245x)** and the projected
13,078-row read **19.51 h -> 16.15 h**. Decision 50 admits a rendering form only if it lowers cost
**and loses nothing**; this one lowers cost and loses a great deal.

Date: 2026-09-21. Model-free read: **zero model, tokenizer, encoder, ASR, server and paid-API
contacts**. The one official score per arm was produced by that arm's own campaign at finalize; this
read invoked only the model-free projection-v3 and TRAIN symmetric scorers, over **copies** of the
sealed outputs written under its own analysis directory. The resident llama-server was never started,
stopped or queried -- its `server.log` and `monitor.jsonl` were read as files. No sealed artefact and
no file under `SPEECHRL_DATA_DIR/runs` or `/attempts` was written, moved or modified; nothing was
committed by this read.

Every table below is produced by a stage of the reusable driver
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B1-INDEX-PAIRED-ANALYSIS-V1/index_cell_read.py` (owner
decision 58: reads are executed by script). Section 12 names which stage produces which table and
the analysis directory's `README.md` carries the exact re-run commands.

Authority, applied unchanged:
[`docs/readiness/2026-09-20-slurp-b1-index-v1-preregistration.md`](../readiness/2026-09-20-slurp-b1-index-v1-preregistration.md)
sections 3-5 and its package
[`docs/readiness/2026-09-20-slurp-b1-index-v1/`](../readiness/2026-09-20-slurp-b1-index-v1/README.md)
(`analysis-recipe-v1.json`, `protocol-registered-v1.json`); the twin package
[`docs/readiness/2026-09-20-slurp-b1-index-twin-v1/`](../readiness/2026-09-20-slurp-b1-index-twin-v1/README.md);
owner decisions 64, 62, 61, 58, 57, 53, 52, 50, 48, 38, 28, 25, 23, 17, 14 and 7; the gating
comparator's sealed numbers and efficiency profile in
[`docs/results/2026-09-20-slurp-b1-notool-verdict.md`](2026-09-20-slurp-b1-notool-verdict.md); the
margins in [`docs/results/2026-09-19-slurp-b1-replicate-verdict.md`](2026-09-19-slurp-b1-replicate-verdict.md);
the index design and receipt fields in
[`docs/superpowers/specs/2026-09-19-e21-knowledge-index-design.md`](../superpowers/specs/2026-09-19-e21-knowledge-index-design.md).

---

## 1. What flew, re-derived and not assumed

| item | IDX (the arm) | IDXT (the twin) | B1-notool (gating comparator) |
| --- | --- | --- | --- |
| run id | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-INDEX-V1` | `...-INDEX-TWIN-V1` | `...-K20-NOTOOL-V1` |
| attempt | `attempt-slurp-native-exemplars-k20-index-train-fold-a-generation-v1` | `...-index-twin-train-fold-a-generation-v1` | `...-notool-train-fold-a-generation-v1` |
| manifest status / dirt | COMPLETED / empty | COMPLETED / empty | COMPLETED / empty |
| study commit | `38984e8084104676f23ac83e9bd54193f1ba21a2` | `9f2997d0a482d845d1543829951a9b9cf6d21763` | `23f011dddde358d21f840cfabb9952d72a33c2ec` |
| composed config hash | `6eb5366e...0c19c7` (= package `cells/arm/composed_config_hash`) | `1cdac2e8...365f85` | `abdf14e7...366382` |
| protocol hash | `3af1bf4e...fce6f4a8` (= package `cells/arm/protocol_hash`) | `99211f5d...1999c1ecdb` | `74331368...6029e8b8` |
| execution profile | `bounded-discovery-probe` | `bounded-discovery-probe` | `bounded-discovery-probe` |
| run-manifest sha256 | `695f7f7c8ce118befe344a5ce7789cc6f4fa6a0062b90a0f41fe58af959b6112` | `12aae0021493c0d09a30b27545290d71eb91e8c57b7ed5e9d117898a8a3c0ea9` | `b4ae2458...91a3e2b7` |
| scores sha256 | `c2268558f6e2a7b33fefcf58879cc8a387f4930fa2e26c3979c9e25d138631af` | `aaf7aefaf6ba00e3f4e4ee59c27794a3cf061cbb2a60617bd9c1c5aef44f3fc5` | `d45ed822...77409a5d` |
| outputs sha256 | `528a8918748411336cfabc10c8d0edaa7ad7a6c3e91cd6bf5575575e6b469a06` | `738a1d6fcb3453ed0c7f981ffea1a68ca47439d040f84727c1957ddbb6cb0b79` | `81b370bf...7abba82ca` |
| rows scored / distinct | 1,080 / 1,080 | 1,080 / 1,080 | 1,080 / 1,080 |
| official scoring jobs | 1 | 1 | 1 |
| view pinned in the receipt | `slurp-knowledge-index-v1`, release `bcfc220b...7235d2`, snapshot `f6d61056...cd4c` | `slurp-knowledge-index-twin-v1`, release `c77021cb...29eb27`, snapshot `9620a595...53ba1b`, `twin_of` = the arm's snapshot | none (no key) |

Every digest above was re-derived by hashing the bytes; each manifest was checked to pin the very
score file this read opened, to carry split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6` with role `discovery`, and to have
been sealed from a clean study tree. Roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json` (sha256 `1fe7908c...f9033d`), 1,080 rows, 18 scenarios
of 60, 125 speaker clusters, 523 headset / 557 far-field. **Row accounting: 1,080 in, 1,080 out on
every arm, no row dropped and no sample id invented.**

## 2. The STOP condition, both halves

* **The registered comparator aggregates reproduce from the sealed bytes.** B1-notool 62.1295 /
  80.0000 / 86.4815 / 81.1111 / 49.0276 and cell B1r 62.23 / 80.09 and the sealed B1 arm 61.14 / 80.19,
  each to within 0.005 pp. `analysis.null_calibration.pooled_f1` reproduces every arm's own official
  aggregate to better than 1e-6.
* **The margins are this read's own arithmetic.** Cell B1r's sealed own null (B1r minus B1) was
  recomputed here with the same estimator, seed 20260915 and 10,000 draws and checked field by field
  against its published verdict table: **h_SLU 1.2350** and **h_intent 1.2212** reproduce exactly, as
  do both intervals, both point estimates and the saves / harms / ties triple.

## 3. The official contrast and the registered guards

Paired whole-speaker cluster bootstrap, 125 clusters, 10,000 draws, seed 20260915. Delta = IDX minus
B1-notool; negative is worse.

| guard | B1-notool | IDX | delta pp | CI95 | CI90 | scenario-stratified CI90 | equal-scenario delta | margin | verdict |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | --- |
| **official pooled SLU-F1** | 62.1295 | **54.7576** | **-7.3719** | [-9.7248, -4.7967] | [-9.3456, -5.2500] | [-9.1498, -5.5943] | -7.6052 | 1.2350 | **MEASURED LOSS** |
| **intent (scenario+action)** | 80.0000 | **77.5926** | **-2.4074** | [-4.5554, -0.3188] | [-4.2086, -0.6672] | [-3.8889, -0.9259] | -2.4074 | 1.2212 | **MEASURED LOSS** |

Both HARMFUL tests fire on both guards: the point estimate is below -h (-7.3719 < -1.2350;
-2.4074 < -1.2212) and the CI95 upper bound is below zero (-4.7967 and -0.3188).

### 3.1 Secondaries and the saves / harms / ties table

| metric | B1-notool | IDX | delta pp | CI95 | saves | harms | ties | McNemar p |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| pooled span F1 (exact slots) | 49.0276 | 42.7232 | -6.3044 | [-9.1960, -3.0282] | -- | -- | -- | -- |
| intent (scenario+action) | 80.0000 | 77.5926 | -2.4074 | [-4.5554, -0.3188] | 40 | 66 | 974 | 0.0148 |
| scenario accuracy | 86.4815 | **87.5000** | **+1.0185** | [-0.5406, +2.5756] | 35 | 24 | 1,021 | 0.193 |
| action accuracy | 81.1111 | 78.4259 | -2.6852 | [-4.7316, -0.7596] | 36 | 65 | 979 | 0.0051 |
| per-row exact slot F1 | 31.5346 | 30.1138 | -1.4208 | [-3.3316, +0.6567] | 91 | 131 | 858 | 0.0087 |
| per-row SLU F1 | 40.6869 | 38.4879 | -2.1990 | [-3.7757, -0.3675] | 120 | 177 | 783 | 0.0011 |

**Scenario accuracy is the one thing the index improves** (+1.02 pp, interval straddling zero). The
loss is entirely in `action` and in the entity layer.

### 3.2 Companions (owner decisions 7 and 14; they decide nothing)

| view | B1-notool | IDX | IDXT | IDX minus B1-notool | CI95 |
| --- | ---: | ---: | ---: | ---: | --- |
| official SLU-F1 | 62.1295 | 54.7576 | 52.1598 | -7.3719 | [-9.7248, -4.7967] |
| projection v3 SLU-F1 | 63.5973 | 55.4244 | 52.9948 | -8.1729 | [-10.5695, -5.5518] |
| TRAIN symmetric SLU-F1 | 63.9741 | 55.7167 | 53.4019 | -8.2573 | [-10.7181, -5.6154] |
| official intent | 80.0000 | 77.5926 | 80.1852 | -2.4074 | -- |
| projection v3 intent | 81.8519 | **82.3148** | 81.2037 | +0.4630 | -- |

The v3 projection *reverses* the intent sign (+0.46 pp): the index makes the core emit more
scenario+action pairs that are illegal in the closed TRAIN inventory and the projection repairs them.
A diagnostic, never a decision quantity -- the official number is the number the rule reads.

## 4. The twin decomposition: content and form (owner decisions 61, 62)

| effect | definition | SLU-F1 delta pp | CI95 | intent delta pp | CI95 |
| --- | --- | ---: | --- | ---: | --- |
| **content** | IDX minus IDXT | **+2.5978** | [+0.8022, +4.4870] | **-2.5926** | [-4.3253, -0.8645] |
| **form** | IDXT minus B1-notool | **-9.9697** | [-12.4562, -7.3154] | **+0.1852** | [-1.9982, +2.3144] |
| total | IDX minus B1-notool | -7.3719 | [-9.7248, -4.7967] | -2.4074 | [-4.5554, -0.3188] |

**Read this the plain way. On the entity metric the damage is the FORM**: replacing the per-row
slot-contract cards and the raw exemplar block with an index plus pointers plus budgeted expansions
costs -9.97 pp of SLU-F1 even when the guidance attached to every id is scrambled, and restoring the
true id-to-line correspondence buys back only +2.60 pp of it. **On intent the damage is the CONTENT**:
the deranged twin is indistinguishable from the base (+0.19 pp, interval straddling zero) while the
true index costs -2.59 pp against it. The correct L1 `Activation boundary` lines make intent selection
*worse* than random lines do.

Both content effects exceed the own null (|+2.5978| > 1.2350; |-2.5926| > 1.2212), so both are
measured, not noise; and they point in opposite directions, which is why no single "the index content
helps" sentence can be written.

### 4.1 The per-row expansion-block length difference, and what it explains

Owner decision 62 warned that the derangement destroys the id-to-line correspondence and that the
twin's per-row expansion blocks are therefore **not** byte-matched to IDX's. Measured, from both
receipts' `expansion_block_chars` (the answering Solver contact of each row):

| statistic | IDX | IDXT | difference (IDX minus IDXT) |
| --- | ---: | ---: | ---: |
| median chars | 9,073.5 | 5,614.5 | +3,040.0 |
| mean chars | 8,766.9 | 5,741.0 | +3,025.9 |
| p90 chars | 10,261.2 | 6,781.2 | +5,021.0 |
| min / max chars | 2,024 / 12,700 | 1,358 / 9,439 | -2,061 / +7,729 |
| rows | 1,080 | 1,080 | longer on IDX 1,055; longer on IDXT 25; equal 0 |

Decile edges of the difference (chars): -2,061, 1,363, 1,812, 2,183, 2,633, 3,040, 3,500, 3,842,
4,132, 5,021, 7,729.

Association with the per-row official SLU-F1 difference (IDX minus IDXT, mean +2.23 pp, median 0.00):
**Pearson r = 0.074, Spearman rho = 0.096** -- weak. By quartile of the length difference the mean
per-row SLU-F1 difference is **+0.81 / +0.77 / +2.86 / +4.47 pp** (n = 282 / 258 / 270 / 270). So the
content effect is concentrated on the rows where IDX's expansion block is much larger than the twin's,
and **the +2.60 pp content effect is confounded with about 3,000 characters per row of extra expanded
card text**. The twin controls the form; it does not control the volume. This is the single largest
caveat on the content number and it is stated here, not buried.

## 5. The efficiency read (mandatory, reported whatever the verdict)

**The join is a measurement, not an estimate.** `n_tokens` at release minus generated plus one equals
the client's `usage.prompt_tokens` on **4,516 of 4,516 contacts (100.00 %)** for IDX, 4,559 of 4,559
for IDXT and 4,432 of 4,432 for B1-notool. **Scoping (how the shared session's log was cut):** the
resident session `serving-slurp-native-candidate-five-train-a-np4-v1` served all three flights and its
`server.log` now holds 7 process segments and 107,618,148 bytes, so each flight's tasks were selected
by that flight's **own sealed contact window** (`flight-receipts` `stages.run_phases.contact_window`),
converted to log-relative seconds through the session receipt's `started_at`, and then aligned to the
client contacts **per KV slot in launch order** (the config pins `decoding_params.id_slot =
"per-sample"`). The windows are disjoint: **IDX 2026-09-20T23:50:18Z -> 2026-09-21T01:18:40Z**, **IDXT
2026-09-21T01:31:07Z -> 02:54:55Z**, base 2026-09-20T20:04:46Z -> 21:51:26Z. The selected server
release records match the client contacts exactly and balance across the four slots
(IDX 1,082 / 1,187 / 1,145 / 1,102), so no other flight's record can have entered.
`monitor.jsonl`'s `requests_delta` reads 1,803 for the IDX window against 4,516 realized contacts and
is **not used** for any throughput number.

### 5.1 Headline

| quantity | **IDX (measured)** | B1-notool (base, measured) | IDXT (twin, measured) | render proof's prediction |
| --- | ---: | ---: | ---: | ---: |
| **prefilled tokens / row** | **3,379.1** | 8,019.8 | 2,795.7 | 3,096 (+9.1 % measured) |
| client prompt tokens / row | 33,750.0 | 33,082.0 | 32,219.8 | -- |
| completion tokens / row | 314.3 | 246.4 | 329.0 | -- |
| **GPU hours / 1,080 rows** | **1.3340** | 1.6108 | 1.2474 | -- |
| wall seconds | 5,302.4 | 6,400.4 | 5,028.7 | -- |
| contacts / row | 4.182 | 4.104 | 4.221 | -- |
| **contacts / minute** (server.log releases) | **53.41** | 42.91 | 56.84 | -- |
| packet re-decodes / row | 0.996 | 0.996 | 0.996 | -- |
| cache hit share | **89.99 %** | 75.76 % | 91.32 % | -- |
| aggregate prefill tok/s | 688.3 | 1,353.3 | 600.4 | -- |
| aggregate decode tok/s | 64.0 | 41.6 | 70.7 | -- |
| slot occupancy | 0.729 | 0.787 | 0.740 | -- |
| mean utilisation % | 74.96 | 77.72 | 71.33 | -- |
| parked fraction | 9.29 % | 9.21 % | 10.47 % | -- |
| truncations | 0 | 0 | 0 | -- |
| **projected 13,078-row read** | **16.15 h** | 19.51 h | 15.10 h | -- |

The B1-notool column was re-read from its own sealed `efficiency.json`, not quoted from prose.

### 5.2 Per position -- where the saving comes from, and where it does not

| position | role | client prompt med | prefilled med | cached | generated med | latency p50 | latency p90 | prefilled/row | share of row prefill | base prefilled/row | base cached |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | perception | 6,414 | 385 | 93.94 % | 137 | 4.81 | 6.22 | 388.9 | 11.51 % | 1,367.8 | 61.97 % |
| 1 | solver | 8,590 | 2,456 | 71.98 % | 24 | 3.10 | 4.20 | 2,389.1 | 70.70 % | 6,120.1 | 35.41 % |
| 2 | reviewer | 8,564 | 237 | 97.20 % | 136 | 4.64 | 7.88 | 237.8 | 7.04 % | 237.1 | 97.49 % |
| 3 | planner | 8,723 | 305 | 96.45 % | 2 | 0.42 | 2.25 | 302.8 | 8.96 % | 262.0 | 97.24 % |
| 4 | solver | 8,962 | 344 | 96.15 % | 25 | 1.41 | 2.94 | 22.8 | 0.68 % | 12.7 | 96.37 % |
| 5 | reviewer | 8,942 | 235 | 97.34 % | 168 | 5.96 | 9.59 | 15.7 | 0.47 % | 8.7 | 97.51 % |
| 6 | planner | 9,096 | 333 | 96.32 % | 2 | 0.44 | 2.25 | 22.0 | 0.65 % | 11.5 | 96.75 % |

The mechanism is visible in two columns. **Perception now pays 6,414 client tokens instead of 3,593**
-- the constant L0+L1 index (17,265 chars, 3,753 derived tokens) is a pure suffix of the contract fill
-- but because it is *constant* the slot's KV prefix supplies it, so Perception's prefill per row
*falls* 1,367.8 -> 388.9 and its cache share rises 61.97 % -> 93.94 %. **The Solver's prefill per row
falls 6,120.1 -> 2,389.1** because the per-row slot-contract cards and the raw exemplar block have been
replaced by a pointer block (mean 473.5 chars) plus budgeted expansions (mean 8,766.9 chars). That
single position is still **70.7 %** of all prefill, and it is where a further budget cut would pay.

Client-visible prompt tokens per row **rise** 33,082.0 -> 33,750.0 (+668.0, +2.0 %). This is an
**expected rise, not a regression**: the index is rendered on every contact of every row, so the client
counts it four or more times while the server prefills it once.

### 5.3 Request fit (all must fit)

| figure | IDX | B1-notool | IDXT | slot |
| --- | ---: | ---: | ---: | ---: |
| request-fit receipts | 4,516 | 4,432 | 4,559 | -- |
| FIT endpoints | 18,064 | 17,728 | 18,236 | cap 47,520 |
| every request fits | yes | yes | yes | -- |
| minimum margin tokens (phase) | 14,379 (planner) | 10,711 (planner) | 14,870 (planner) | 24,576 |
| widest realized request | 10,197 | 13,865 | 9,706 | 24,576 |

FIT run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-INDEX-FIT-V1`. The index *widens* the fit margin by 3,668
tokens, because the per-row cards it removes were larger than the per-row block it adds.

## 6. Index consumption (owner decision 64; the recipe's `diagnostics_required` item)

### 6.1 (a) Citations

| signal | B1-notool | IDX | IDXT |
| --- | ---: | ---: | ---: |
| rows with at least one citation | 0 | **24 (2.22 %)** | 42 (3.89 %) |
| citations resolved | 0 | 45 | 109 |
| citations unresolved | 0 | 2 | 3 |
| distinct cited ids | 0 | 41 | 76 |
| cited ids agreeing with the delivered intent | -- | **1** | 4 |
| cited ids agreeing with a delivered slot type | -- | **2** | 3 |

Citation is `permitted`, not required, and the core essentially declines it. Of 45 resolved citations
on 24 rows, **3 are consistent with what the row actually delivered**. The deranged twin cites nearly
twice as often, which settles the direction question: citation frequency is not evidence of
consumption here, it is noise.

### 6.2 (b) Pointer use, measured against the SAME pointer blocks

The pointer blocks are always **IDX's own**, taken from its sealed receipt for that sample id and
applied unchanged to the base's and the twin's delivered answers, so that "the answer follows the
pointers" is measured against "the answer would have followed them anyway". The pointer selection
depends only on the sealed Perception state, which the render proof showed identical.

| signal | B1-notool | IDX | IDXT |
| --- | ---: | ---: | ---: |
| delivered intent inside the row's pointer intent set | **95.35 %** (1,026 / 1,076) | **91.76 %** (991 / 1,080) | 97.31 % (1,051 / 1,080) |
| delivered intent inside the Perception top-3 pointer set | 87.92 % (946) | 83.15 % (898) | 89.07 % (962) |
| delivered slot types inside the pointed slot set | **71.77 %** (727 / 1,013) | **86.28 %** (937 / 1,086) | 83.51 % (927 / 1,110) |
| rows whose every delivered slot type is pointed | 510 | 709 | 660 |
| delivered slot-type instances | 1,013 | 1,086 | 1,110 |

Two facts, both important. **The slot pointers are obeyed** -- +14.5 pp over the base -- and the twin
obeys them almost as well (83.51 %), which is expected, because the derangement scrambles the
id-to-line correspondence and leaves the pointer *ids* themselves true. **The intent pointers are
obeyed LESS by the arm that sees them** (91.76 %) than by the base that never saw them (95.35 %) or by
the twin (97.31 %). Showing the core three candidate intents with their real `Activation boundary`
lines moved it *off* the candidate set **3.59 pp more often** than showing nothing did (35 rows of
about 1,080).

### 6.3 (c) Expansion use, by stratum

Slot types whose L2 card the arm expanded on that row (`expanded_ids`) versus slot types the arm only
pointed at. Type-level precision and recall against the row's gold entity types, held in memory and
never persisted; the filler-level number is the official scorer's own and is in section 3.

| stratum | arm | delivered instances | precision | recall | format-compliant fillers |
| --- | --- | ---: | ---: | ---: | ---: |
| **expanded** (L2 card shown) | B1-notool | 434 | **0.6705** | 0.7642 | 99.77 % |
| | **IDX** | **630** | **0.5159** | **0.8591** | 99.37 % |
| | IDXT | 575 | 0.5043 | 0.7561 | 97.91 % |
| **pointed only** (L1 line only) | B1-notool | 293 | 0.6928 | 0.7569 | 98.98 % |
| | **IDX** | 307 | 0.6319 | 0.7294 | 97.39 % |
| | IDXT | 352 | 0.5369 | 0.7020 | 96.02 % |

**This is the mechanism of the loss.** Expanding a slot card makes the core emit that slot type: 630
instances against the base's 434 on the same 1,080 rows and the same stratum definition. Recall rises
(0.764 -> 0.859) and **precision falls by 15.5 points** (0.671 -> 0.516). The index turns the expanded
ids into a to-do list, and the frozen core fills it whether the speech supports the slot or not. In
the pointed-only stratum, where the core has the L1 `Admissible formats` line and no card, both
precision and recall fall against the base.

### 6.4 (d) Format compliance overall

| signal | B1-notool | IDX | IDXT |
| --- | ---: | ---: | ---: |
| delivered fillers | 1,013 | 1,086 | 1,110 |
| machine-checkable fillers | 1,013 | 1,085 | 1,109 |
| **compliance rate** | **99.31 %** | **98.71 %** | 97.57 % |
| null-placeholder violations (shared section SM-1) | 5 | 11 | 25 |
| line-rule violations | 2 | 3 | 2 |

**How the regex per slot type was derived, and its honest limits.** Each of the view's 54 slot entries
carries an L1 `Admissible formats` line in English. The driver turns that line into a **violation**
regex by literal trigger matching -- "never digits and never a colon" -> `[0-9:]`; "do not convert noon
or morning to a numeric clock time" -> `[0-9]`; "do not resolve it to an ISO date" / "invent a year" ->
`\d{4}-\d{2}-\d{2}|\b(19|20)\d{2}\b`; "do not invent domains" and "without adding a URL" / "converting
it into a URL" -> `https?://|www\.|\.(com|org|net|io)\b`. **Only 6 of the 54 lines** (`app_name`,
`business_name`, `date`, `media_type`, `time`, `timeofday`) state a prohibition a regex can decide; the
other 48 say some form of "use the spoken form and do not invent", which no regex can adjudicate.
Every delivered filler is therefore additionally checked against the view's **shared** slot section
SM-1 ("omit this slot when no supported mention is present; do not invent a filler"), which a null
placeholder (`none`, `n/a`, `unknown`, `-`, ...) breaks; that rule applies to all 54 types. The rate is
**not** a general well-formedness measure and is comparable only between the arms of this read.

### 6.5 (e) The triple, and the statement

| | official SLU-F1 | official intent | official span F1 |
| --- | ---: | ---: | ---: |
| B1-notool (base) | 62.1295 | 80.0000 | 49.0276 |
| **IDX** | **54.7576** | **77.5926** | **42.7232** |
| IDXT (twin) | 52.1598 | 80.1852 | 40.1755 |

**Statement: MISLEADING TERSENESS.** Its antecedent in `decision_rule.consumption` is "IDX lies below
the base with (d) worse", and both hold: -7.37 pp on the primary and 98.71 % against 99.31 % on format
compliance. The other two are excluded on their own terms. **NON-CONSUMPTION** requires IDX to lie
inside IDXT's null with citations near zero and (b)-(d) not moving against the base; IDX lies 2.60 pp
above IDXT on SLU and 2.59 pp below it on intent, both beyond the own null, and (b) moves by +14.5 pp
on slot types, so the core plainly *is* reading the block. **CONSUMPTION** requires the arm to differ
from the twin beyond the own null **and** (a)-(d) to move in the same direction as the score; the first
conjunct holds and the second does not -- citations move the wrong way (the twin cites more), format
compliance moves the wrong way, and the expanded-stratum precision collapse means the signal the core
takes from the index is pushing the score down. The three clauses are not mutually exclusive on their
face; MISLEADING TERSENESS is stated because its antecedent is satisfied outright and its consequence
is the strictest.

**Contingency, fixed in the recipe before the flight: on MISLEADING TERSENESS the form is closed at
decision 52's provisional defaults and the owner decides.** The richer-granularity variant
(`expansion_budget.intent_card > 0`, a larger `slot_card` budget) is the NON-CONSUMPTION route and is
**not** the indicated next step under this reading; what the evidence points at instead is the
*expansion-as-to-do-list* failure -- the core emits the expanded types -- which a larger budget would
make worse, not better.

## 7. Structure: the index is constant, and nothing else moved

| claim | IDX | IDXT | B1-notool |
| --- | ---: | ---: | ---: |
| rows carrying the `saea-native-knowledge-index-v1` receipt | **1,080 / 1,080** | 1,080 / 1,080 | 0 (OFF arm seals no block) |
| contacts carrying the index receipt | **4,516 / 4,516** | 4,559 / 4,559 | -- |
| `distinct_system_message_sha256` per row | **1 on all 1,080** | 1 on all 1,080 | -- |
| distinct system-message sha256 over the WHOLE flight | **1** | 1 | -- |
| distinct rendered-index sha256 | **1** (`b279dcc0...8d4438`, 17,265 chars) | 1 | -- |
| distinct view pins / granularity / budget sets | 1 / 1 / 1 | 1 / 1 / 1 | -- |
| `degradation_steps` | **0** (0 rows) | 0 (0 rows) | -- |
| selection refusals (candidates / slot types / votes) | 0 / 0 / 0 | 0 / 0 / 0 | -- |
| requests carrying a tools array | **0 of 4,516** | 0 of 4,559 | 0 of 4,432 |
| every `tool_choice` is `none` | yes | yes | yes |
| **tool calls** | **0** (ceiling 0) | 0 | 0 |

**The Perception request differs from B1-notool's in exactly the armed keys, on 1,080 rows of 1,080.**
Comparing the bookkeeping-free reduction key by key (`request_id`, every `evidence_provenance`
relpath and `decoding_params.id_slot` excluded, plus each history entry's three per-flight state
identifiers; each entry's content and `content_sha256` stay compared), the differing key set is
`{task_instruction, supplied_evidence, history, evidence_provenance_content}` on **all 1,080 rows and
on no row anything else** -- exactly the sealed wire check's `W3_expected_armed_keys`. No row is
byte-identical, as the factor requires. The same holds on all 1,080 rows of the twin.

The recipe's inherited CONSTANCY table (`distinct_tool_schemas_sha256 == 1`) and its "native
task-contract call count against the anchor's realized 1,082" do not apply: this cell flies on the
tool-free 0-B base, `phase_tools` is absent, no arm seals a `saea-native-tool-schema-rendering-v1`
block and the registered ceiling is zero calls. The stronger claim is measured instead and holds:
**zero tool schemas on every one of the 4,516 requests**. Section 11 lists every such divergence.

## 8. Trajectory, dispositions and the review loop

| signal | **IDX** | B1-notool | IDXT |
| --- | ---: | ---: | ---: |
| contacts per row | **3: 19, 4: 989, 6: 1, 7: 71** | 3: 8, 4: 1,032, 7: 40 | 3: 41, 4: 945, 6: 2, 7: 92 |
| contacts per row (mean) | 4.182 | 4.104 | 4.221 |
| Reviewer contacts per row | 1: 1,008, 2: 72 | 1: 1,040, 2: 40 | 1: 986, 2: 94 |
| Planner routes / `REVISE` tokens | 1,132 / **81** | 1,112 / 43 | 1,131 / 102 |
| rows with at least one `REVISE` | **72** | 40 | 94 |
| `revision_limit` terminal dispositions | **9** | 3 | 8 |
| `finite_completion` rows (item E13) | **20** | 8 | 43 |
| `react_exhaustion` visits (item E22) | **0** | 0 | 0 |
| `planner_action_illegal` rows (item E8c) | **1** | 0 | 4 |
| rows the official scorer could not parse | **0** | 4 | 0 |
| aborts / recovery re-registrations | **0 / 0** | 0 / 0 | 0 / 0 |

**The finite completions are all the same shape and all are Reviewer 512-token cap hits.** 20 of the
1,152 Reviewer contacts reached the cap (base 8 of 1,120; twin 43 of 1,174), and the count of capped
contacts equals the count of `finite_completion` rows exactly on all three arms. Item E13's
`deliver-latest-or-abstain` retained every one of them; **the flight met zero aborts**, which is what
that declaration exists for. The count is a diagnostic here, not a decision quantity: the registered
all-rows number stays the number the rule reads, and the recipe's exclusion diagnostic is not needed to
change a verdict that is HARMFUL by 7.37 pp.

**The Reviewer talks more under the index.** Completion tokens median **90 -> 139**, p90 **171.1 ->
217.9**. The index gives the Reviewer 17,265 characters of addressable guidance and it writes longer
reviews about it, which is why the revise route opens up (72 rows against 40) and why more reviews run
into the 512-token cap. **`planner_action_illegal` fires once** (the E8c row disposition: the row is
retained and delivers its committed draft); the twin fires it four times.

**`react_exhaustion` is zero on all three arms**, as the registration expected: no role holds a tool,
so the Reviewer cannot loop on one.

## 9. Per scenario (diagnostic under owner decision 17, never a gate)

Intent, paired whole-speaker cluster bootstrap within each scenario, natural mixture (n = 60 each;
equal-scenario weighting is identical here because every scenario carries exactly 60 rows -- the
equal-scenario intent delta is -2.4074 pp, the same as the pooled figure, and the equal-scenario
pooled-SLU delta is -7.6052 against the natural -7.3719).

| scenario | B1-notool | IDX | delta pp | CI95 | saves/harms | net harmed | flags | pooled SLU base | pooled SLU IDX | delta |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| alarm | 86.67 | 91.67 | +5.00 | [-6.98, +13.46] | 5/2 | -3 | | 72.90 | 65.92 | -6.98 |
| audio | 78.33 | 76.67 | -1.67 | [-11.43, +5.13] | 3/4 | +1 | | 61.94 | 31.66 | **-30.28** |
| calendar | 80.00 | 80.00 | 0.00 | [-6.78, +6.56] | 2/2 | 0 | | 63.96 | 63.28 | -0.68 |
| cooking | 85.00 | 80.00 | -5.00 | [-12.96, +1.69] | 1/4 | +3 | | 64.49 | 58.09 | -6.39 |
| datetime | 88.33 | 86.67 | -1.67 | [-9.62, +5.17] | 2/3 | +1 | | 70.77 | 72.37 | +1.61 |
| email | 86.67 | 85.00 | -1.67 | [-9.62, +4.92] | 1/2 | +1 | | 54.41 | 48.79 | -5.62 |
| general | 41.67 | 41.67 | 0.00 | [-6.25, +7.28] | 2/2 | 0 | | 17.78 | 28.57 | **+10.79** |
| **iot** | 88.33 | 80.00 | **-8.33** | [-15.79, -1.72] | 0/5 | **+5** | **D17, BAND** | 68.18 | 57.86 | -10.33 |
| lists | 81.67 | 88.33 | +6.67 | [+1.67, +12.50] | 4/0 | -4 | | 50.55 | 52.28 | +1.73 |
| music | 70.00 | 66.67 | -3.33 | [-12.96, +5.56] | 3/5 | +2 | | 47.10 | 20.25 | **-26.85** |
| news | 81.67 | 83.33 | +1.67 | [-3.64, +7.84] | 2/1 | -1 | | 64.86 | 59.14 | -5.73 |
| **play** | 63.33 | **21.67** | **-41.67** | [-56.25, -25.92] | 3/28 | **+25** | **D17, BAND** | 52.33 | 46.04 | -6.29 |
| qa | 78.33 | 81.67 | +3.33 | [-3.13, +10.00] | 3/1 | -2 | | 57.77 | 52.14 | -5.63 |
| recommendation | 90.00 | 86.67 | -3.33 | [-10.00, +3.17] | 1/3 | +2 | | 67.48 | 67.38 | -0.10 |
| social | 75.00 | 76.67 | +1.67 | [-7.02, +10.17] | 4/3 | -1 | | 56.79 | 43.25 | -13.54 |
| takeaway | 85.00 | 88.33 | +3.33 | [0.00, +8.20] | 2/0 | -2 | | 60.66 | 54.84 | -5.82 |
| transport | 86.67 | 86.67 | 0.00 | [-5.00, +4.69] | 1/1 | 0 | | 66.77 | 46.88 | **-19.89** |
| weather | 93.33 | 95.00 | +1.67 | [0.00, +5.41] | 1/0 | -1 | | 75.85 | 68.95 | -6.90 |

**`play` is not a scenario effect, it is the whole intent loss and more.** Intent collapses 63.33 ->
21.67 with 28 harms against 3 saves; the roster-level intent delta is -2.41 pp and `play` alone
contributes -2.31 pp of it. **The twin does not show it** (`play` +6.67 pp, 9 saves / 5 harms,
interval straddling zero), so the collapse is caused by the *true* `Activation boundary` lines of the
`play` intent family, not by the index form. `iot` loses -8.33 pp on both arms, but only IDX's
interval clears zero ([-15.79, -1.72] against the twin's [-18.03, 0.00]), so `iot` is band-breaching on
IDX alone and D17-flagged on both.

**The music scenario, carried forward from the base's verdict (decision 63, D2).** The base's own
breach was `music` at **-8.33 pp intent, CI95 [-15.72, -1.75], net harmed +5, D17 flagged** against the
sealed B1 arm. **On IDX against that base, `music` intent moves only -3.33 pp, CI95 [-12.96, +5.56],
net harmed +2, and is neither band-breaching nor D17-flagged.** The index does not deepen the music
intent breach. It does, however, do the most entity damage there of any scenario but `audio`: pooled
SLU-F1 on `music` falls **47.10 -> 20.25 (-26.85 pp)**.

Band summary: IDX breaches the intent band on **`iot` and `play`** and is D17-flagged on the same two;
IDXT breaches on none and is D17-flagged on `iot` alone.

## 10. Cost and ceilings

| figure | **IDX** | B1-notool | IDXT | registered ceiling |
| --- | ---: | ---: | ---: | ---: |
| generation contacts (run-cumulative) | **4,516** | 4,432 | 4,559 | 11,880 |
| contacts per row | 4.182 | 4.104 | 4.221 | 11 max program |
| contacts by role (perception / solver / reviewer / planner) | 1,080 / 1,152 / 1,152 / 1,132 | 1,080 / 1,120 / 1,120 / 1,112 | 1,080 / 1,174 / 1,174 / 1,131 | -- |
| repeated speech seconds | **12,853.98** | 12,687.00 | 12,999.48 | 33,930 |
| client prompt tokens | 36,449,992 | 35,728,582 | 34,797,342 | -- |
| completion tokens | 339,457 | 266,131 | 355,292 | -- |
| **tool calls** | **0** | 0 | 0 | **0** |
| FIT endpoints | 18,064 | 17,728 | 18,236 | 47,520 |
| **GPU hours** | **1.3340** | 1.6108 | 1.2474 | 12.0 fit-inclusive |
| official complete scoring jobs | 1 | 1 | 1 | 1 |
| aborts / recovery re-registrations | 0 / 0 | 0 / 0 | 0 / 0 | at most 1 |

Tokens per contact by role, median / p90 (client prompt tokens; IDX against B1-notool):

| role | IDX median | IDX p90 | base median | base p90 | IDX completion median / p90 | base completion median / p90 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 6,414 | 6,439 | 3,593 | 3,650 | 137 / 143 | 133 / 144 |
| solver | 8,599 | 8,856 | 9,663 | 11,544 | 24 / 35 | 24 / 35 |
| reviewer | 8,573 | 8,831 | 9,644 | 11,519 | **139 / 218** | 90 / 171 |
| planner | 8,737 | 9,022 | 9,788 | 11,644 | 2 / 2 | 2 / 2 |

**Ledger closure inputs** for the coordinator (this read edits no ledger row): run
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-INDEX-V1`, attempt
`attempt-slurp-native-exemplars-k20-index-train-fold-a-generation-v1`, FINALIZED at study commit
`38984e80...ba21a2`; **4,516 generation contacts, 12,853.98 repeated speech seconds, 4,516 request-fit
receipts / 18,064 FIT endpoints (all fit), 0 tool calls, 1.334 GPU hours, one official complete score**;
all inside every registered ceiling; nothing exceeded, no recovery re-registration used.

## 11. The harness-admission consequence

The registered entry form is: class `episode`, key `native_episode.knowledge_index`, OFF = the key's
absence (`rails.config_tables.is_episode_null_arm`), ON = the flown block (view
`slurp-knowledge-index-v1` with its release and snapshot pins, granularity intent L1 `Activation
boundary` / slot L1 `Admissible formats` / edge L0, ordering `taxonomy-frequency-v1`, pointer budget
3 / 8 / 3, expansion budget 5 / 4 / 0, `solver_citation: permitted`).

**On this read no entry is written.** `harness_admission_check` requires every ADMITTED or NEUTRAL
module to appear in at least one default plan for its carrier, and decision 50 admits a rendering form
only if it lowers cost **and loses nothing**. This one lowers cost by 17.2 % of GPU hours and loses
7.37 pp of the primary, so:

* **the key stays out of the SLURP default plan**, and the plan keeps the sealed B1-notool form;
* **the form is closed at decision 52's provisional defaults** (preregistration section 3: "a HARMFUL
  read closes the form at these defaults and reopens decision 52");
* there is **no UNMET obligation** to carry: the twin has sealed and the content / form decomposition
  is reported in section 4, so the NEUTRAL-without-the-twin contingency of the preregistration never
  arises;
* the coordinator, not this read, writes any receipt row and takes the proposal below to the owner.

**What this read proposes the owner consider, and does not decide.** Three facts bear on decision 52.
(i) The **form** costs -9.97 pp of SLU-F1 on its own -- replacing the per-row cards with pointers plus
budgeted expansions is the larger half of the damage, and no re-tuning of granularity can recover it
while the expansion block is what carries the cards. (ii) The **expansion behaves as a to-do list**:
the core emits the expanded slot types (+45 % of delivered instances in that stratum) at 15.5 points
lower precision, so a *larger* `slot_card` budget is contraindicated and the richer-granularity variant
that NON-CONSUMPTION would have routed to is the wrong next cell under this reading. (iii) The **intent
L1 line is actively harmful**: the `play` family collapses -41.67 pp under the true lines and does not
move under deranged ones. If the owner keeps the index direction at all, the one-factor cell the
evidence points at is an **index with no expansion block** (`expansion_budget` all zero, pointers only)
read against this same base, not a richer one. It would also be the cheapest variant yet flown: the
Solver position, which is where the pointer block and the expansions land, is 70.7 % of this arm's
prefill, and the twin -- whose expansion blocks happen to be
about 3,000 characters shorter per row -- already reads 2,795.7 prefilled tokens per row against IDX's
3,379.1, which is the direction such a cell would push further.

## 12. Which stage produces which table (owner decision 58)

Driver: `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B1-INDEX-PAIRED-ANALYSIS-V1/index_cell_read.py`
(sha256 `a9f0e9ad11b9a9fa1450b501ce8751fae1ecfe7bc6a20e46636d2ab20f96bf4c`), parameterised by arm,
comparator, twin, package directory, view snapshot, margins and analysis root. The analysis directory's
`README.md` carries the exact command for every stage.

| stage | command | produces | sections here |
| --- | --- | --- | --- |
| `stop` | `--stage stop` | `cache/stop-raw.json` | 1, 2 |
| `structural` | `--stage structural` | `structural.json`, `cache/client-contacts-raw.json` | 7, 8 |
| `contrast` | `--stage contrast` | `score-contrasts.json`, `per-scenario-tables.json` | 3, 3.1, 3.2, 4, 9 |
| `consumption` | `--stage consumption` | `consumption.json` | 6, 4.1 |
| `efficiency` | `--stage efficiency` | `efficiency.json`, `throughput-tables.json` | 5, 5.1, 5.2, 5.3, 10 |
| `verdict` | `--stage verdict` | the decision block, all deliverables, `README.md` | the status line, 11 |

## 13. Where this read departs from the inherited recipe text

The recipe was generated from the B1-notool / EFF-1 packages and still carries their text. Where the
two disagree the recipe governs; where the recipe's text cannot apply, the stronger claim is measured
instead and the divergence is named here.

1. **`diagnostics_required`: "THE CONSTANCY TABLE ... `distinct_tool_schemas_sha256 == 1`"** -- the
   `tool_schema_rendering` key (item E17) is not armed on the 0-B base, so no arm seals that block.
   Measured instead: **zero tool schemas and `tool_choice: none` on every one of the 4,516 requests**.
2. **`diagnostics_required`: "NATIVE TASK-CONTRACT CALL COUNT against the anchor's realized 1,082"** --
   the registered ceiling for this cell is **zero**; realized zero.
3. **`diagnostics_required`: "FIRST-REQUEST BYTE IDENTITY"** -- correctly stated in the recipe as *not*
   byte-identical under this factor; section 7 reports what is claimed instead (one system-message sha,
   the receipt on every contact, no tools array, and the armed key set on 1,080 of 1,080 rows).
4. **`arms.arm.run_manifest_sha256 / scores_sha256 / outputs_sha256 = PENDING_SEAL`** and
   `expected_contacts_nominal = 4320` -- the recipe was registered before the flight sealed. The sealed
   digests are in section 1, re-derived from the bytes; realized contacts 4,516.
5. **`output.files` names `throughput-tables.json`; the spawn brief names `efficiency.json`** -- both
   are written with identical bytes so neither authority is contradicted.
6. **`output.verdict_document` = `docs/results/2026-09-2x-slurp-b1-notool-verdict.md`** -- an unfilled
   template path inherited from the B1-notool package, naming another cell. This verdict is written at
   the path the spawn brief names, `docs/results/2026-09-21-slurp-idx-knowledge-index-verdict.md`, and
   the divergence is recorded here rather than silently resolved.
7. **The spawn brief's "twin placeholder section"** is superseded by the twin's own seal: section 4 is
   the real decomposition and section 6.5 decides the consumption statement **with** the twin, exactly
   as `decision_rule.twin` and `decision_rule.consumption` require.

## 14. What is not claimed

Descriptive paired read on historically exposed TRAIN Fold A discovery rows plus a cost measurement of
the same flight. **These are development numbers (owner decision 28)**; nothing here is compared with a
published TEST baseline and no bar claim is made. No superiority, generalization, component-causal or
confirmatory claim; no cross-carrier claim; no geometry claim. The content / form decomposition is a
paired contrast between two flights on the same roster, geometry and session, and its content half is
confounded with about 3,000 characters per row of expansion-block length (section 4.1); it is not a
causal decomposition of "what the index knows". No claim is made that an L1 line suffices, or fails to
suffice, for any slot type outside the six whose `Admissible formats` line is machine-checkable. The
expansion-budget sweep, the ordering claim and the per-role budget reads remain unflown. No Fold B,
DEV-1000 or test-split row was read, and none is authorized by this verdict.

## 15. Files

Analysis root `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B1-INDEX-PAIRED-ANALYSIS-V1/`
(the recipe's `output.analysis_root` under `output.root: SPEECHRL_DATA_DIR`; nothing was written under
`runs/` or `attempts/`, and nothing in the repository but this verdict file).

| file | sha256 |
| --- | --- |
| `score-contrasts.json` | `34feb77fa339fb158e3914efc80cce91e9114924c81467094427327bbac596dc` |
| `efficiency.json` | `48fcea0f384b2a0cb0435b84d6b0aaa8c223cef83ccde923cd30bfc814b0191f` |
| `throughput-tables.json` | `48fcea0f384b2a0cb0435b84d6b0aaa8c223cef83ccde923cd30bfc814b0191f` |
| `per-scenario-tables.json` | `8217f6a244d4cf3565d61792511211dcbf8ed27c2404468a314318f4d44f390a` |
| `structural.json` | `67c0b69a28bf3f9eb0526cd1dd16953378b99551882a57a0fdfbd7ca2b5c98b0` |
| `consumption.json` | `1a4e72f2facdadf3fb6405cb9b64b8a9ca980c159394ffb05a3e91c36008b2da` |
| `README.md` | `c1a0680ed1146cb298c7cd2882598823c0675cb0735b4cbd8af166f29fe2fba8` |
| `index_cell_read.py` (the driver) | `a9f0e9ad11b9a9fa1450b501ce8751fae1ecfe7bc6a20e46636d2ab20f96bf4c` |

`score-contrasts.json` carries every input with its digest, the authority files with their digests, the
implementation files with their digests, the population block, the STOP checks, the own-null
reproduction, all four contrasts, the band, the companions, the structural block, the consumption block,
the efficiency block and the decision block.
