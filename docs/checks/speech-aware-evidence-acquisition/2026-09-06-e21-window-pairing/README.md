# The Earnings pairing unit is the 90-second window, and the decomposition is lossless

Exposure row `SAEA-E21-MF-WINDOW-PAIRING-V1` (`model-free-check`), registered and committed before
the first file was opened. **Zero model, GPU, tool, embedder, tokenizer, network, audio-decode and
paid-API contacts**; no Earnings-22 read. References and `wer_tags` are reached only through the
registered scoring path's own loaders (`data.references`,
`reproduction.conec_entity_scoring`), never opened by hand.

Owner ruling, 2026-09-06: **pair at the 90-second window, cluster at the call.** Earnings-21 has 44
calls against a program rule of `n >= 400` paired units, and no statistics turn 44 into 400. The
units where the model contacts actually happen are the 1,593 fixed 90-second windows. This row
builds that instrument out of the sealed run and proves it loses nothing.

| | |
|---|---|
| source | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| population | all 44 `earnings21-original` discovery calls, 1,593 windows, split identity `fcc1b0bc…d69e` |
| module / runner | `analysis/e21_window_pairing.py` · `scripts/e21_window_pairing_read.py` |
| per-window rows | `$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/window-rows.json`, sha256 `e2e7da6ff07b4539a8bebd6adb040125344fbeaf6fd4be08db889b3a6827f800` — a per-request derivative of sealed model outputs, so it lives where those live and never in Git |
| resampling | seed **20260903**, **10,000** replicates, **CI90** (`analysis.e21_window_pairing.E21_WINDOW_*`) |
| wall clock | 603.3 s |

## 1. How a sealed call becomes 37 windows without re-running anything

`reproduction.obs_loop` sends N slice requests per call and emits ONE stitched hypothesis,
`" ".join(span for span in accepted_spans if span)`. Every piece is in the sealed trace: each
slice's own `MODEL_RESPONSE` text, the stitch record's `stitched_request_ids` in slice order, and
each slice's `OBS` window bounds. The per-window hypothesis is therefore **recovered, not
re-derived** — and before a single number is computed, `assert_stitch_reproduces_outputs` rebuilds
every one of the 44 sealed hypotheses **byte for byte** from the recovered spans.

**The one real difficulty, stated because it would otherwise be an invisible error.** The scorers
normalize the WHOLE stitched string at once, and the Whisper normalizer is not local at a span
boundary: on **13 of the 44** calls it merges number tokens across one, so normalizing each span
separately and concatenating yields **18 more words** than normalizing the stitch (e.g. `… to one` +
`.14 to $2.8 billion` → `… to one.14 to …`). Splitting the hypothesis per span is therefore not a
valid decomposition of what the scorer computed.

The construction that is: normalize each **prefix** of the stitch and take its word count.
`c_k` is the number of whole-string-normalized hypothesis words the first `k` windows account for.
On all 44 calls the sequence is **non-decreasing** and `c_K` equals the whole normalization's length
**exactly**, so `[c_{k-1}, c_k)` is a genuine partition of the hypothesis indices the scorer actually
aligned. A token the normalizer merged across a boundary is charged to the earlier window — a stated
convention, applied deterministically, moving no total.

Reference words then follow the hypothesis through the alignment: every operation of the trace
`conec-entity-wer-official` itself computes is charged to exactly one window, a deletion to the
window its hypothesis cursor stands in.

## 2. The proof — `reaggregation.json`, verdict **PASS**

Summing the 1,593 per-window rows reproduces the sealed corpus numbers exactly:

| check | per-window sum | sealed |
|---|---:|---:|
| windows / calls | 1,593 / 44 | 1,593 / 44 |
| substitutions | **13,098** | 13,098 |
| deletions | **5,701** | 5,701 |
| insertions | **10,700** | 10,700 |
| reference words | **359,765** | 359,765 |
| corpus WER % | **8.200** | 8.200 |
| ConEC `__ALL__` bucket % | **8.200** | 8.200 |
| non-entity % | **4.730** | 4.730 |
| `__UNLABELLED__` reference words | **1,479** | 1,479 |
| negation-critical HIGH reference words / insertions | **100 / 56** | 100 / 56 |

and every published entity class, with its reference-word count:

| class | per-window sum % | sealed % | ref words |
|---|---:|---:|---:|
| PERSON | **22.49** | 22.5 | 2,917 |
| ORG | **17.21** | 17.2 | 4,363 |
| GPE | **18.67** | 18.7 | 1,537 |
| LOC | **2.47** | 2.5 | 485 |
| PRODUCT | **19.23** | 19.2 | 390 |
| EVENT | **2.43** | 2.4 | 494 |
| NORP | **9.75** | 9.7 | 236 |
| FAC | **21.31** | 21.3 | 122 |

The sealed figures are the rounded ones the comparator note publishes; every reference-word count
matches to the unit and every rate to the digit that note prints.

## 3. The one metric that does NOT decompose exactly, and by how much

`asr-wer-whisper`, `conec-entity-wer-official` and `semantic-high-impact-error-rate-v1` are all
functions of the operation trace, so the partition is exact for all three.
**`numeric-value-accuracy-v1` is not.** It BAG-matches the call's reference numeric values against
the call's hypothesis numeric values, and a bag match inside a window is strictly stricter than one
across the call: a value spoken in window 3 and transcribed into window 4 matches at call level and
not at window level.

* `expected_numeric_words` partitions exactly: **9,734**, the sealed figure.
* `matched_numeric_words` falls short by **73 of 8,832 (0.827 %)**, spread over **27 of the 44**
  calls, at most **8** in any one call.
* Pooled accuracy therefore reads **89.984 %** at window level against the sealed **90.734 %**.

This is reported as a number, not hidden. A verdict that quotes numeric-value accuracy must quote
the level it was computed at, and the harm guard should stay on the call-pooled figure, where the
comparator's own 90.73 lives.

## 4. What the window unit buys — and what it does not

Stated plainly, because it is easy to oversell. For a **pooled** statistic with the call as the
cluster, resampling calls and pooling over their windows is arithmetically identical to resampling
calls and pooling over their totals: **the window unit changes no digit of the call-clustered
interval.** What it buys is exactly three things:

1. the **window-level interval** as an explicitly labelled optimistic bound (1,593 units treated as
   independent — which they are not);
2. a paired **saves / harms / ties** count and sign test at n = 1,593 instead of 44;
3. **per-window strata** — including the diarized speaker strata of `saea-diarization-v1`, which
   exist only at the window level.

A verdict that quotes the window-level interval as if it were the honest one is misreading this
receipt.

## 5. The resampler

`analysis.paired.paired_contrast` already takes `cluster_of`; this row adds
`analysis.paired.resampled_statistic`, which exposes the SAME stratum/cluster resampling machinery
for an arbitrary statistic. That matters because `paired_contrast`'s own bootstrap statistic is the
MEAN of per-unit differences, and every Earnings metric is a **pooled ratio** —
`sum(errors) / sum(reference words)` — where an 8-second tail window must not weigh as much as a
dense 90-second one. One resampler, two estimators, never a second implementation of "resample
clusters with replacement".

`tests/unit/test_analysis_paired.py` pins both directions: with a call-level effect the clustered
interval is **more than three times wider** than the window-level one, and with genuinely
independent windows the two agree within 0.6–1.6× — clustering is not a blunt widener.

## Files

| file | what it holds |
|---|---|
| `reaggregation.json` | every check above with its actual/expected pair, the pooled entity buckets, the semantic-impact totals, the window- and call-pooled numeric counts, the per-call numeric shortfall, and the rows file's path and SHA-256 |
| `MANIFEST.sha256` | this directory's own byte manifest |
