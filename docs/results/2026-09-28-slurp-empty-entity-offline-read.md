# EMPTYENT offline read: the DEV-2000-ADDED pool's own null is 1.547 pp, and the explicit empty-entity rule moves pooled SLU-F1 by +0.256 [+0.067, +0.445] (DESCRIPTIVE)

Read 2026-09-28. The registered model-free read row `SAEA-SLURP-STAGE3-EMPTY-ENTITY-OFFLINE-V1` (owner
decision 171; package `docs/readiness/2026-09-27-slurp-stage3-empty-entity-offline-v1/`, preregistration
`docs/readiness/2026-09-27-slurp-stage3-empty-entity-offline-v1-preregistration.md`) was root countersigned
2026-09-28 04:58 UTC by the coordinator (Fable 5.1) before the read, and executed by Claude Opus 5.5 in
worktree `/home/chao/saea-worktrees/fable-b4read` (branch `fable/b4read`, base `86e6fe45`) exactly as the
package README states: stage `null` first (sealed 04:59:46Z), then stage `rule`, which read that sealed file
(05:00:22Z to 05:01:41Z). Script `scripts/analysis/empty_entity_offline_read.py` at the registered sha256
`0051c88c726146d344850bd707056892d7b46e3423778194ede2ec50d7f94bfe`; the imported resampling
`scripts/analysis/slurp_sample_aggregation_offline_read.py` at the registered sha256
`e81cf5bef3196e2359b1e96378a76468cce0c04997ef00d56ff2b33a08ad7f2e`, unchanged.

Contacts: five CPU official-scorer jobs over the five edited copies (stage `rule`, 16 to 24 s each), the only
contacts the row registers; zero model, tokenizer, encoder, embedder, llama-server, GPU and network contacts;
0 speech-audio seconds. Gold entered only inside the registered scorer. No utterance text, transcript, gold
label string, entity value or model answer is printed or persisted here or in the machine results.

Machine results under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-EMPTY-ENTITY-OFFLINE-V1/dev2000-added/`:
`null.json` sha256 `aea49f72597efee65ebb19df246392e9fbc978a18cfb30c8a3cc13941c919f47`; `rule-min3.json`
`0a741fc87f424bca9bccffaa5b5efaff2a4b449a6e485f3b0e3720a8da529531` (it records the sha256 of the null it read);
and a supplementary descriptive accounting (section 5), `supplementary-accounting.json`
`a62b6c3e46c4b068ad99b927a3af539b0844ddcb01044d2e043d4fe43cb46e32`, produced by `supplementary_accounting.py`
(copied beside, sha256 `4ed12ea3336147cfb7f380d910d4b1c29eb1eacd557587d4c9a0d83415b50804`) from the sealed
ROLL-3 score files and the rule's five scored copies, with no further scorer contact. Input pool:
`SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1` via its stage 1-3 read
`analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1` (render manifest sha256
`5f193003a43e3eae182a923b9bb208b2a74a9229ba6c392e383480a2dbd1e535`), scorer `slurp-slu-official-projected-v3`,
1,000 rows x 5 samples.

Status: **DESCRIPTIVE** -- development numbers on one sealed pool (owner decisions 28 and 86); no admission,
no disposition, no effectiveness claim. The registered decision rule is evaluated mechanically and the side
its outcome falls on is stated in section 4 without a verdict word.

## 1. Pool accounting (equal to the registered dry run)

1,000 rows; 17 malformed samples; 1,039 empty samples; 118 rows empty on all five samples. Emptiness-vote
histogram (well-formed empty samples per row): 0 -> 701, 1 -> 44, 2 -> 52, 3 -> 39, 4 -> 46, 5 -> 118.
At the registered `--min-empty 3` the rule fires on **203 rows** and edits **123 samples** (24.6
row-equivalents per mean single sample). All five counts equal `registered-facts-v1.json`.

## 2. Step 1 -- the offline null

Paired row bootstrap copied from the instrument note's section 2c/2d floor (`default_rng(20260915)`, 10,000
draws, row weights by `bincount`, percentile CI95). Half-width = (hi - lo) / 2, in pp. The last column is the
whole-utterance cluster variant (`--with-cluster-variant`, section 2e resampling), for comparison only.

| pair (i-j) | pooled SLU-F1 CI95 of (j - i) | SLU-F1 half-width | intent half-width | span-F1 half-width | per-row SLU half-width | cluster-variant SLU-F1 half-width |
| --- | --- | --- | --- | --- | --- | --- |
| 0-1 | [-2.711, +0.258] | 1.485 | 0.70 | 1.816 | 1.158 | 1.476 |
| 0-2 | [-1.036, +1.447] | 1.242 | 0.70 | 1.729 | 0.945 | 1.227 |
| 0-3 | [-1.314, +2.222] | 1.768 | 1.00 | 2.293 | 1.209 | 1.775 |
| 0-4 | [-3.067, -0.138] | 1.464 | 0.70 | 1.858 | 1.199 | 1.485 |
| 1-2 | [+0.157, +2.699] | 1.271 | 0.65 | 1.672 | 1.075 | 1.283 |
| 1-3 | [-0.288, +3.680] | 1.984 | 1.10 | 2.559 | 1.496 | 2.043 |
| 1-4 | [-1.794, +1.063] | 1.428 | 0.65 | 1.651 | 0.971 | 1.423 |
| 2-3 | [-1.423, +1.954] | 1.689 | 0.90 | 2.178 | 1.271 | 1.739 |
| 2-4 | [-3.096, -0.481] | 1.307 | 0.70 | 1.686 | 1.063 | 1.313 |
| 3-4 | [-3.922, -0.262] | 1.830 | 1.00 | 2.445 | 1.458 | 1.846 |
| **mean** | | **1.547 (THE NULL)** | **0.810 (the intent guard)** | 1.989 | 1.184 | 1.561 |
| median / min / max | | 1.474 / 1.242 / 1.984 | 0.70 / 0.65 / 1.10 | 1.837 / 1.651 / 2.559 | 1.178 / 0.945 / 1.496 | max 2.043 |

Each sample against `R0-mean-single` (same bootstrap), half-widths in pp:

| sample | SLU-F1 | intent | span-F1 | per-row SLU |
| --- | --- | --- | --- | --- |
| 0 | 0.904 | 0.47 | 1.185 | 0.683 |
| 1 | 0.973 | 0.47 | 1.205 | 0.751 |
| 2 | 0.759 | 0.40 | 1.024 | 0.624 |
| 3 | 1.295 | 0.73 | 1.682 | 0.956 |
| 4 | 0.921 | 0.48 | 1.161 | 0.734 |
| mean | 0.970 | 0.51 | 1.251 | 0.750 |

Reading. THE NULL (1.547 pp) is 2.3 x the 0.67 pp one-pool floor the synthesis assumed (instrument note
section 2c, n = 625, the medoid rule against mean-single) and 2.9 x the 0.53 pp offline floor the package
declared as `expected_effect_pp` at n = 1,000; even the single-sample-against-mean widths (mean 0.970) exceed
both. The row-unit width almost equals the whole-utterance cluster variant (mean 1.561, max 2.043; section
2e's pooled-micro 1.56), so the resampling unit is not what widens it: the contrast is. Two samples differ on
every row on which they disagree, whereas the section 2c floor measured a rule against the mean of the same
samples. Four of the ten pairwise intervals exclude zero (0-4, 1-2, 2-4, 3-4): the samples differ in level
(sample 4 lowest), not only in noise.

## 3. Step 2 -- the rule against the null

`RULE-mean-single` against `R0-mean-single`, same bootstrap, n = 1,000.

| metric | R0-mean-single | RULE-mean-single | delta (pp) | CI95 | half-width |
| --- | --- | --- | --- | --- | --- |
| pooled SLU-F1 (primary) | 63.097 | 63.353 | **+0.256** | **[+0.067, +0.445]** | 0.189 |
| span-F1 | 54.211 | 54.497 | +0.286 | [+0.082, +0.486] | 0.202 |
| intent exact (the guard) | 75.76 | 75.76 | **0.000** | **[0.000, 0.000]** | 0 |
| per-row SLU-F1 mean | 45.569 | 45.066 | -0.503 | [-0.736, -0.304] | 0.216 |

Word + char count mass removed per mean single sample: FP 44.04, TP 13.60. Intent is unchanged by
construction (scenario and action are never edited). The per-row SLU mean moves the other way because the
scorer assigns per-row SLU-F1 0.0 to a row with no gold and no predicted entity (all 759 such sample-rows of
R0 score 0.0), so emptying a spurious-entity row earns nothing per row while every TP removed costs.

## 4. The pre-declared rule and the side the numbers fall on

Registered before any number: the rule **CLEARS** (clears its own null as a gain) iff (a) the SLU-F1 CI95
lower bound > 0 AND (b) the SLU-F1 delta >= THE NULL AND (c) the intent CI95 lower bound >= -(the intent
guard). A clear licenses registering an arm with an in-chain A/A; nothing else.

| clause | value | bar | holds |
| --- | --- | --- | --- |
| (a) SLU-F1 CI95 lower bound > 0 | +0.067 | > 0 | yes |
| (b) SLU-F1 delta >= THE NULL | +0.256 | >= 1.547 | **no** (short by 1.291 pp; the delta is 17 % of the null) |
| (c) intent CI95 lower bound >= -guard | 0.000 | >= -0.810 | yes |

Side: **does not clear** (`clears: false` in `rule-min3.json`). The interval excludes zero on the positive
side, so the numbers are not on the harmful side; the point delta is far below the pool's own null, so they
are not on the gain side either. The delta is also below the synthesis' assumed floors (0.53 and 0.67 pp).
No verdict word is attached here.

## 5. Supplementary accounting (descriptive, no scorer contact)

**FP-only rows.** Defined from the scorer's own per-row counts: a sample-row is FP-only when its word + char
TP = 0 and FN = 0 (the gold carries no entity) and FP > 0. Mean over the five R0 samples: **162.2 FP-only
sample-rows (16.2 %)**, 151.8 clean-empty (15.2 %), 686 gold-bearing (68.6 %); 216 rows (21.6 %) are FP-only
in at least one sample. Per sample: 157 / 170 / 166 / 150 / 168. This is wider than the synthesis' quoted
12.1 % / 10.8 % (bad-case bank ENTITY-FP-ONLY class), which is a different class definition on a different
answer (the bank's delivered answer, not one projected sample); the two are not the same quantity and
neither is re-derived from the other here.

| per mean single sample | count |
| --- | --- |
| fired rows (203) whose sample was already clean-empty | 133.6 |
| fired rows whose sample was FP-only, edited to clean-empty | 14.4 |
| fired rows whose sample was gold-bearing (55 rows) | 55.0 |
| of which edited (entities removed from a gold-bearing sample) | 10.2 (TP lost 13.6, word + char) |
| FP-only sample-rows the rule leaves untouched | 147.8 of 162.2 (91.1 %) |

The rule reaches 14.4 of 162.2 FP-only sample-rows (8.9 %) and pays for them with 10.2 gold-bearing edits:
the emptiness vote is high mostly where the samples are already empty, and most FP-only rows carry a low
vote (the samples agree on emitting entities).

**Per channel.** The roster withholds the scenario stratum per item by design, so the ROLL-3 read's
precedent is followed: headset / far-field from the roster's own `headset` field.

| stratum | n | rows fired | R0 SLU-F1 | RULE SLU-F1 | delta SLU-F1 | delta intent |
| --- | --- | --- | --- | --- | --- | --- |
| far-field | 540 | 111 | 60.112 | 60.550 | +0.438 | 0.00 |
| headset | 460 | 92 | 66.422 | 66.468 | +0.046 | 0.00 |
| natural mixture | 1,000 | 203 | 63.097 | 63.353 | +0.256 [+0.067, +0.445] | 0.00 |
| equal-stratum | -- | -- | 63.350 | 63.590 | +0.240 [+0.048, +0.430] | 0.00 |

**Per modal predicted scenario.** The most frequent scenario over the five R0 samples (ties to the lowest
sample index): a model-output stratum, not gold, reported because the gold scenario is withheld. Strata of
n < 10 are listed but carry no weight in reading.

| predicted scenario | n | rows fired | R0 SLU-F1 | delta SLU-F1 |
| --- | --- | --- | --- | --- |
| calendar | 165 | 23 | 72.80 | +0.14 |
| qa | 153 | 13 | 61.76 | +0.05 |
| play | 145 | 37 | 52.36 | +0.04 |
| email | 85 | 16 | 59.30 | +0.73 |
| weather | 69 | 11 | 69.67 | -0.06 |
| iot | 57 | 8 | 64.89 | +0.73 |
| transport | 56 | 13 | 75.07 | +0.62 |
| lists | 50 | 22 | 58.64 | +0.94 |
| music | 49 | 11 | 67.65 | +0.35 |
| general | 42 | 14 | 35.32 | -1.05 |
| news | 29 | 5 | 60.70 | +0.62 |
| recommendation | 29 | 6 | 30.01 | -0.32 |
| audio | 26 | 13 | 15.93 | +0.52 |
| datetime | 17 | 7 | 56.51 | -1.68 |
| alarm | 11 | 3 | 61.57 | +0.61 |
| social | 6 | 1 | 53.68 | -4.77 |
| four further strata (n = 4, 3, 3, 1) | 11 | 0 | -- | 0.00 |
| natural mixture | 1,000 | 203 | 63.097 | +0.256 [+0.067, +0.445] |
| equal-stratum (20 strata) | -- | -- | 61.120 | +0.028 [-0.498, +0.395] |

The intent delta is 0.00 in every stratum. Under equal-stratum weighting by predicted scenario the interval
includes zero: the pooled movement is carried by the larger strata and offset in `general`, `datetime` and
`recommendation`.

## 6. Ambiguities and limits

- THE NULL is a sample-against-sample width, while the rule's delta is a rule-against-mean contrast whose
  own interval half-width is 0.189 pp. A rule that edits 24.6 row-equivalents of 1,000 has little room to
  reach 1.547 pp; this is a property of the registered bar, recorded here and not re-derived (instrument
  rule 6).
- The FP-only share by scorer counts (16.2 % per sample) differs from the synthesis' 10.8 % for DEV; the
  definitions differ (section 5).
- TRAIN Fold A (ROLL-2) is registered to be read beside once its stage 1-3 read exists; it was not run here.

## Coordinator verdict (Fable 5.1, 2026-09-28)

**INERT-BY-INSTRUMENT.** The SLU-F1 movement +0.256 [+0.067, +0.445] is a real but tiny gain: its interval
excludes zero, but it is about 17 % of the pool's own sample-vs-sample null (1.547 pp). No arm is registered.

Instrument finding recorded: the offline null of a multi-sample pool on DEV-2000-ADDED is 1.547 pp SLU-F1 /
0.810 intent, 2.3 x the 0.67 pp one-pool floor the synthesis assumed, so offline rule designs read on
multi-sample pools have little room to clear. The FP-only share is 16.2 % by the scorer's per-row
definition, against the 10.8 % the synthesis quoted.

The agent's numbers above are unchanged. The results-ledger SHA-256 `ffcfb945...` pins this note as the
agent wrote it, before this section was appended.
