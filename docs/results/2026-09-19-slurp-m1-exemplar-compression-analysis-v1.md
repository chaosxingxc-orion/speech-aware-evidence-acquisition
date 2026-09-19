# M1 exemplar supply: where the k = 20 tokens go, and what a smaller or compact block would keep

Model-free compression analysis of cell B1's speech-keyed TRAIN exemplar supply (module M1) over
the sealed arms, under **owner decision 46** of 2026-09-19, extended by **decision 47** (sections
6-8) and **decision 49** (sections 9-11)
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`).

**Zero contacts.** No model, tokenizer, encoder, ASR, tool, scorer, server or network was reached.
Every number is read from sealed bytes already on disk: the flown traces' `MODEL_REQUEST` payloads,
their `MODEL_RESPONSE.usage` fields, their `MODEL_WIRE_RESPONSE` server timings, the sealed
`scores.json` / `outputs.jsonl`, the knowledge snapshots and the two sealed vector files. The
retrieval scores in section 4 family (c) are inner products between two sealed vector files
recomputed here -- arithmetic on bytes already on disk, not an encoder call.

**Gold use.** SLURP TRAIN annotations were joined **offline, for the diagnostics only**. No
utterance text, no filler surface form and no gold sentence is printed or persisted anywhere in
this report, in the receipt or in the intermediate artifacts: every text comparison runs on the
SHA-256 digest of the lower-cased, stripped string.

Driver, intermediates and hashes:
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-M1-EXEMPLAR-COMPRESSION-ANALYSIS-V1/` (README there).
Committed receipt: `docs/receipts/slurp-m1-exemplar-compression-analysis-v1.json`.

---

## 0. The four findings that decide the ranking

1. **The premise needs correcting.** The twenty-line exemplar block is **not** the largest
   prompt-token contributor. It costs **737 tokens** per Solver contact -- **7.8 %** of that
   contact's prompt and **8.9 %** of the row's GPU prefill. The `slot-contracts` block in the same
   request is **26,010 characters, roughly 5,070 tokens, about seven times larger**. Lever L3's
   "22-item block" is the *whole* supplied-evidence block, of which the exemplars are the smallest
   third.
2. **What M1 actually buys is slot fillers, not intents.** Of the 277 rows where B1 beat the sealed
   anchor on SLU-F1, **213 (76.9 %) changed only the slots**, 2 changed only the intent. Of the 154
   saves that gained a newly correct filler, **133 (86.4 %) have that exact filler surface printed
   in the block**. Any form that keeps the vote and drops the raw lines throws away the mechanism.
3. **The tail is nearly free to drop, and nearly free to keep.** Ranks 11-20 buy **+1.48 pp** of
   gold-intent coverage and **+2.5 pp** of slot-type recall for **39 %** of the block's characters.
   Only **1 of 43** sealed intent saves depends on an exemplar beyond rank 12.
4. **Relevance order is already discarded at the rendering boundary.** The rendered block is
   the cosine top-20 on **1080 / 1080** rows, but it is rendered in **lexicographic `evidence_id`
   order on 1080 / 1080** rows; mean Spearman between rendered position and true rank is **0.007**.
   The model is handed twenty neighbours and is told nothing about which is closest.

And one finding the owner's decision 49 anticipated: the raw block is rendered into **four of the
five contacts of every row**, and is prefilled **three times** per row (section 9).

---

## 1. Where the tokens go

### 1.1 Method

The block's token cost is **measured, not estimated**: for each row, the sealed Solver contact's
`usage.prompt_tokens` in the B1 arm minus the same row's sealed Solver contact in the anchor
(`SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`). The difference is restricted to
the **816 of 1,080** rows whose non-exemplar evidence composition *and* character count match
exactly, so the residual is the exemplar block and nothing else. The chars-per-token ratio the
simulations use is derived from that same paired difference by least squares through the origin.

Rendering contract (production `core.model.transport`): each supplied-evidence item becomes one
user text part `[evidence <evidence_id>] <content>`; there is no block heading. The "heading" of
each exemplar line is its own `[evidence train-exemplars::value:<slurp_id>] ` prefix.

### 1.2 The measurement

| quantity | value |
| --- | ---: |
| paired rows (matched non-exemplar composition) | 816 / 1,080 |
| block cost, mean | **737.3 prompt tokens** |
| block cost, median / p10 / p90 | 718.5 / 621 / 886 |
| block rendered characters, mean / median / p90 | 2,660.8 / 2,595 / 3,254 |
| of which raw value text | 1,874.4 (70.4 %) |
| of which `[evidence ...] ` prefixes | 786.4 (29.6 %) |
| **measured chars per token on the block** | **3.634** (ratio of means 3.624) |
| per line, rendered chars mean / median / p90 / max | 133.0 / 126 / 180 / 436 |
| per line, tokens (at 3.634) | 36.6 / 34.7 / 49.5 / 120 |
| k on every row | exactly 20 (min = max = 20) |

Cross-checks that agree: the B1-minus-anchor Solver **client** delta per row is **+783.5** tokens,
and the B1-minus-anchor Solver **prefill** delta per row is **+760.4** tokens. A multivariate OLS of
prompt tokens on per-store characters gives a lower coefficient (4.88 chars/token, 545 tokens) --
it is collinear across stores and is reported only as a loose bound; the paired difference is exact
and is what this report uses.

### 1.3 The block's share

| level | B1 | anchor | delta | block share |
| --- | ---: | ---: | ---: | ---: |
| Solver contact, prompt tokens (median) | 9,762 | 8,964 | +798 | 7.4 % |
| Solver contact, prompt tokens (mean) | 9,511 | 8,749 | +762 | **7.8 %** |
| row, client prompt tokens | 45,730.5 | 42,591.0 | **+3,139.5** | **6.9 %** |
| row, GPU prefilled tokens | 25,932.6 | 23,619.4 | **+2,313.1** | **8.9 %** |
| flight, GPU hours / 1,080 rows | 3.859 | 3.653 | **+0.207** | 5.4 % |

The anchor recovery predates the flight-receipt stage file, so its wall is reconstructed from its
own sealed latency total at the B1 flight's measured slot efficiency (1.1406 wall-over-latency at
four slots); B1's 3.859 GPU hours is its receipt's own `wall_seconds`.

### 1.4 What else is in the Solver prompt

Solver contact of the B1 arm, median characters, with tokens from the per-store least-squares
densities (the exemplar row is the exact paired measurement):

| component | chars | chars/token | tokens | share of prompt |
| --- | ---: | ---: | ---: | ---: |
| `slot-contracts` (11 values) | 26,010 | 5.13 | **~5,070** | **~52 %** |
| history (agent state + control) | 11,377 | ~6.2 | ~1,830 | ~19 % |
| system message (task contract) | 8,118 | ~6.2 | ~1,310 | ~13 % |
| `intent-boundaries` (8 cards) | 6,022 | 7.53 | ~800 | ~8 % |
| **`train-exemplars` (20 lines)** | **2,595** | **3.63** | **737** | **~7.6 %** |
| speech packet (query audio) | -- | -- | ~24 | ~0.2 % |

The exemplar lines are the **densest** text in the request (3.63 chars/token against 5.1-7.5 for the
card stores), because they are natural speech transcriptions rather than repeated template prose.
A character saved on an exemplar line therefore buys about 1.5x the tokens a character saved on a
slot-contract card would.

---

## 2. Which ranks matter (offline gold join, diagnostic only)

### 2.1 Cumulative coverage by k

Ranks are the **true cosine ranks**, recomputed here; k means "the k best neighbours", which is
*not* the order the sealed request renders them in (section 4.2).

| k | gold intent present | gold slot-type recall | all gold types present | same-intent type recall | gold filler recall | all gold fillers present | block chars | block tokens |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 0.8852 | 0.9060 | 0.8724 | 0.8091 | 0.4421 | 0.3754 | 688 | 189 |
| 8 | 0.9139 | 0.9333 | 0.9144 | 0.8527 | 0.4932 | 0.4204 | 1,088 | 299 |
| 10 | 0.9204 | 0.9383 | 0.9234 | 0.8647 | 0.5167 | 0.4414 | 1,355 | 373 |
| 12 | 0.9278 | 0.9471 | 0.9339 | 0.8780 | 0.5302 | 0.4580 | 1,617 | 445 |
| 15 | 0.9352 | 0.9538 | 0.9399 | 0.8868 | 0.5515 | 0.4745 | 2,011 | 554 |
| **20** | **0.9426** | **0.9598** | **0.9474** | **0.8963** | **0.5719** | **0.4940** | **2,661** | **732** |

The A2 pre-flight audit (`docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md`) predicted
filler recall 0.566 and type recall 0.960 at k = 20; measured on the **flown bytes** they are 0.5719
and 0.9598 -- the audit reproduces. Its "gold intent among neighbours" of 0.9565 reads 0.9426 here;
the audit counted over its own candidate construction, this counts the twenty lines the Solver
actually received.

### 2.2 Where the first gold-intent neighbour sits

| rank | rows | cumulative | cumulative share |
| ---: | ---: | ---: | ---: |
| 1 | 782 | 782 | 0.7241 |
| 2 | 95 | 877 | 0.8120 |
| 3 | 36 | 913 | 0.8454 |
| 4 | 26 | 939 | 0.8694 |
| 5 | 17 | 956 | 0.8852 |
| 6-8 | 31 | 987 | 0.9139 |
| 9-10 | 7 | 994 | 0.9204 |
| 11-12 | 8 | 1,002 | 0.9278 |
| 13-15 | 8 | 1,010 | 0.9352 |
| 16-19 | 8 | 1,018 | 0.9426 |
| never | 62 | 1,080 | 1.0000 |

Median first hit **rank 1**, mean 1.86, p90 rank 4. **2.22 %** of rows first meet their gold intent
beyond rank 10 and **1.48 %** beyond rank 12.

### 2.3 Redundancy, duplicates, echo

| quantity | value |
| --- | ---: |
| distinct intents among the 20, mean / median | 3.75 / 3 |
| distinct intents, p10 / p90 | 1 / 7 |
| top intent's share of the 20, mean / median | 0.713 / 0.750 |
| intent entropy, mean | 1.117 bits |
| largest single-intent group, mean size | 14.26 of 20 |
| **rows with 5 or more neighbours of one intent** | **1,059 / 1,080 (98.06 %)** |
| rows where all 20 share one intent | 169 |
| rows with a duplicated utterance digest inside the block | **0** |
| rows echoing the row's own utterance | **2** (2 lines of 21,600; 0.0093 %) |

Per-intent group sizes across all rows (a "group" is one intent inside one row's twenty): size 1 x
1,636, 2 x 582, 3 x 276, 4 x 207, 5 x 132, 6 x 113, 7 x 78, 8 x 88, 9 x 75, 10 x 71, 11 x 48,
12 x 52, 13 x 70, 14 x 57, 15 x 56, 16 x 64, 17 x 68, 18 x 98, 19 x 113, **20 x 169**.

The fold exclusion holds: echo is 2 lines in 21,600, and no line is repeated inside a row. The
block is **massively redundant by intent**: on average the twenty lines carry 3.75 labels, and one
label owns 14 of the 20.

### 2.4 Score spread

| quantity | value |
| --- | ---: |
| cosine at true rank 1, mean | 0.3703 |
| cosine at true rank 20, mean | 0.3159 |
| absolute drop rank 1 to 20, mean | 0.0544 |
| rank 10 / rank 1 ratio, mean | 0.884 |

The similarity surface is **flat**: rank 20 still scores 85 % of rank 1. Score-gap truncation has
almost no signal to cut on (section 4, family c, confirms it).

---

## 3. Did rank matter to the delivered answer

| quantity | value |
| --- | ---: |
| rows where B1 is intent-exact and the anchor is not ("intent saves") | 43 |
| rows where the anchor is intent-exact and B1 is not ("intent harms") | 19 |
| net intent | **+24** |
| rows where B1's per-row SLU-F1 exceeds the anchor's | 277 |
| rows where it falls below | 62 |
| mean per-row SLU-F1 delta | **+0.0914** |

### 3.1 The rank of the supporting exemplar

"Supporting exemplar" = the best-ranked neighbour whose intent equals the intent B1 delivered.

| quantity | intent saves (43) | intent harms (19) |
| --- | ---: | ---: |
| no supporting exemplar in the block | 1 | 12 |
| median support rank | 1 | 4 |
| mean support rank | 2.43 | 4.71 |
| within rank 5 | 88.4 % | 21.1 % |
| within rank 8 | 90.7 % | 36.8 % |
| within rank 12 | 95.3 % | 36.8 % |
| **beyond rank 10** | **3 rows (7.0 %)** | 0 |
| **beyond rank 12** | **1 row (2.3 %)** | 0 |

Save support rank histogram: rank 1 x 27, rank 2 x 7, rank 3 x 2, rank 5 x 2, rank 8 x 1,
rank 11 x 1, rank 12 x 1, rank 14 x 1.

The nineteen harms are the opposite shape: **12 of 19** delivered an intent that appears nowhere in
the block, so the harm is not the block copying a wrong neighbour -- it is the block failing to hold
the row and the Solver drifting. Trimming k does not repair those rows.

### 3.2 What actually changed on a save (decision 49)

Of the **277** SLU-F1 saves, comparing B1's delivered object with the anchor's:

| what changed | rows | share |
| --- | ---: | ---: |
| **slots only** (types and/or fillers; same intent) | **213** | **76.9 %** |
| intent and slots | 28 | 10.1 % |
| intent only | 2 | 0.7 % |
| neither set changed (scoring-side normalisation) | 34 | 12.3 % |

Filler provenance on those saves:

| quantity | value |
| --- | ---: |
| saves that gained a newly correct filler | 154 |
| of which the exact filler surface is printed in the block | **133 (86.4 %)** |
| of which that surface appears **only** beyond rank 10 | 12 |

**This is the load-bearing result of the whole analysis.** M1 is a convention-transfer mechanism:
the Solver copies filler surface forms out of the raw exemplar lines. A compressed form that keeps
intent information and discards the raw lines removes the thing that is working. Section 10 prices
exactly that trade.

---

## 4. Simulated compressions

All predictions use the measured 3.634 chars/token of section 1 and the true rank order of
section 2. "Saves support dropped" counts, of the 42 intent saves whose supporting exemplar is in
the block, how many lose it. "Save-filler retention" counts, of the 133 saves whose newly correct
filler surface is in the block, how many keep it -- the section 3.2 metric, and the one to read.
"Saved / row" is four renders (section 9).

| # | form | k (mean) | chars | tokens | saved / contact | saved / row | saving | gold intent | type recall | filler recall | saves support dropped | save-filler retention |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| -- | **as flown, k = 20** | 20.00 | 2,661 | 732 | -- | -- | -- | 0.9426 | 0.9598 | 0.5719 | 0/42 | 133/133 |
| a | rank top-15 | 15.00 | 2,011 | 554 | 179 | 715 | 24.4 % | 0.9352 | 0.9538 | 0.5515 | 0/42 | **0.955** |
| a | **rank top-12** | 12.00 | 1,617 | 445 | **287** | **1,148** | **39.2 %** | 0.9278 | 0.9471 | 0.5302 | 1/42 | **0.887** |
| a | rank top-10 | 10.00 | 1,355 | 373 | 359 | 1,437 | 49.1 % | 0.9204 | 0.9383 | 0.5167 | 3/42 | 0.880 |
| a | rank top-8 | 8.00 | 1,088 | 299 | 433 | 1,733 | 59.1 % | 0.9139 | 0.9333 | 0.4932 | 3/42 | 0.850 |
| a | rank top-5 | 5.00 | 688 | 189 | 543 | 2,172 | 74.2 % | 0.8852 | 0.9060 | 0.4421 | 4/42 | 0.774 |
| b | per-intent cap 3, then 20 | 7.69 | 1,048 | 289 | 444 | 1,774 | 60.6 % | **0.9426** | 0.9232 | 0.4563 | **0/42** | 0.820 |
| b | per-intent cap 3, then 12 | 7.27 | 995 | 274 | 458 | 1,833 | 62.6 % | 0.9389 | 0.9202 | 0.4526 | **0/42** | 0.812 |
| b | per-intent cap 2, then 20 | 5.99 | 820 | 226 | 506 | 2,024 | 69.2 % | **0.9426** | 0.9090 | 0.4258 | **0/42** | 0.752 |
| b | per-intent cap 2, then 12 | 5.85 | 802 | 221 | 512 | 2,048 | 69.9 % | 0.9407 | 0.9075 | 0.4228 | **0/42** | 0.744 |
| c | score gap >= 0.90 x top | 10.70 | 1,436 | 395 | 337 | 1,349 | 46.0 % | 0.9065 | 0.9195 | 0.4900 | 2/42 | 0.887 |
| c | score gap >= 0.93 x top | 6.52 | 884 | 243 | 489 | 1,955 | 66.8 % | 0.8722 | 0.8798 | 0.4465 | 5/42 | 0.797 |
| c | score gap >= 0.95 x top | 4.12 | 563 | 155 | 577 | 2,307 | 78.8 % | 0.8324 | 0.8427 | 0.3890 | 10/42 | 0.609 |
| c | score gap >= 0.97 x top | 2.40 | 330 | 91 | 641 | 2,564 | 87.6 % | 0.7907 | 0.7910 | 0.3447 | 10/42 | 0.549 |

**(a) Smaller k.** Monotone and well behaved. **k = 12** is the knee: 39 % of the block for -1.48 pp
gold intent, -1.27 pp type recall, -4.17 pp filler recall, one save's support lost and 88.7 % of the
save-filler surfaces kept. k = 10 costs almost as much coverage for only ten more points of saving.

**(b) Per-intent cap.** Cap 2 or 3 is the **best intent-coverage-per-token** form in the table: it
preserves gold intent at the full 0.9426 while cutting 60-69 % of the block, and it never drops a
save's supporting *intent*. But it is the **worst filler form per token retained**: it deletes the
within-intent repetition, and within-intent repetition is exactly where the filler surfaces live
(save-filler retention falls to 0.744-0.820, while rank top-12 at a smaller saving keeps 0.887).
Given section 3.2 this family is a trap: it optimises the axis M1 is not winning on.

**(c) Score-gap truncation.** Rejected. The similarity surface is flat (section 2.4), so any
threshold tight enough to save tokens (0.95 x top gives mean k = 4.12) also cuts gold intent to
0.8324 and save-filler retention to 0.609. The induced k distribution is unstable -- at 0.95 x top
it runs p10 = 1 to p90 = 9 -- and a data-dependent per-row block size breaks the fixed prompt-fit
ceiling the flight gate checks.

### 4.1 Compact rendering, measured exactly on the sealed lines

The rendered line is `[evidence train-exemplars::value:<slurp_id>] <utterance> | <intent> |
<type>=<filler>; <type>=<filler>`. The evidence-id prefix alone is **29.6 %** of the block.

| rendering | chars / row | tokens saved / contact | tokens saved / row | coverage change |
| --- | ---: | ---: | ---: | --- |
| as flown | 2,660.8 | -- | -- | -- |
| store alias `tex:<id>` for `train-exemplars::value:<id>` | 2,280.8 | **104.6** | **418** | **exactly none** |
| + compact slot notation (`;` and `=` become `\|` and `:`) | 2,270.0 | 107.6 | 430 | none |
| + utterance capped at 80 chars (1,232 of 21,600 lines) | 2,254.0 | 112.0 | 448 | truncates 5.7 % of lines |
| + utterance capped at 60 chars | 2,207.2 | 124.8 | 499 | truncates more |
| no evidence id at all (one ordinal per line) | 1,894.4 | 210.9 | 844 | none, but breaks citation |

4,965 of 21,600 lines (23.0 %) carry no slot annotation at all -- they are `<utterance> | <intent>`
only, so for them the raw line is intent evidence that the vote of section 6 already summarises.

The **store alias is a free 14.3 % of the block with zero coverage change** and no semantic risk:
the id stays unique and addressable, so `cited_value_ids` and the I7 custody chain keep working.
Dropping the id entirely saves 28.6 % but removes the handle the Reviewer and the agent-state
citation mechanism use; not recommended without a separate custody change.

### 4.2 Ordering -- the finding that changes how family (a) should be read

| quantity | value |
| --- | ---: |
| rows whose rendered **set** is the cosine top-20 | **1,080 / 1,080** |
| rows rendered in **descending cosine** order | **0 / 1,080** |
| rows rendered in **lexicographic `evidence_id`** order | **1,080 / 1,080** |
| mean Spearman(rendered position, true rank) | **0.0073** |

The retrieval produces a rank and the renderer throws it away. Two consequences.

* A per-request `COMPACT` disposition that drops the tail **today** drops an arbitrary subset.
  Measured: keeping the first 12 *rendered* lines gives gold intent 0.9056 and save-filler
  retention 0.932, against 0.9278 and 0.887 for the true top-12 at the same token cost; keeping the
  first 8 rendered gives 0.8750 and 0.805 against 0.9139 and 0.850 for the true top-8. The two
  orders disagree by 2 to 4 pp in both directions depending on the metric, which is itself the
  proof that position carries no information to the model today.
* **Most-relevant-first ordering is free** -- zero tokens, one sort key -- and it is a prerequisite
  for every tail-dropping disposition, including decision 45's `COMPACT`. It should ride along with
  whatever cell flies, and it is the one change that could plausibly *raise* the score rather than
  merely hold it.

### 4.3 Interaction with lever L1 and with slot store v2

* **With L1 (constant tool rendering).** L1 removes about 13,100 prefilled tokens per row
  (`docs/results/2026-09-19-slurp-throughput-root-cause-v1.md`); the exemplar block's 2,313
  prefilled tokens per row then become **17.7 %** of a post-L1 row rather than 8.9 %. Compression is
  worth relatively more after L1 and absolutely the same. L1 must still land first, or L3-class work
  will be credited with L1's gain.
* **With slot store v2 (B5e).** Measured on the sealed B5e arm: the same 20-line block renders at
  2,659.4 characters -- the exemplar supply is identical to B1's -- while the Solver prompt rises to
  a median 10,102 tokens because the slot block grows from 26,010 to 27,919 characters. The exemplar
  block's share **falls** to 7.3 %. The two blocks are additive; compressing exemplars does not
  interact with the slot store.
* **The real L3 target is `slot-contracts`, not `train-exemplars`.** At about 5,070 tokens per
  Solver contact it is roughly 6.9x the exemplar block. This analysis does not touch it; it is
  flagged as the larger opportunity and deserves its own model-free audit.

---

## 5. Ranked proposal under decision 46's own menu

Ranking by saving per unit of risk to the measured mechanism (section 3.2), restricted to the
decision-46 menu. Section 11 gives the final ranking across all three decisions.

1. **Compact rendering + rank ordering + k = 12** combined: about **385 tokens** per Solver contact,
   **1,540 per row**, 47 % of the block; gold intent 0.9278, save-filler retention 0.887.
2. **Compact rendering alone** (k unchanged): 105 tokens per contact, 418 per row, **zero** coverage
   change -- the only strictly free item on the menu.
3. **k = 12 alone**: 287 per contact, 1,148 per row, -1.48 pp intent, -4.17 pp filler recall.
4. **Per-intent cap**: best intent-per-token, worst filler-per-token; rejected on section 3.2.
5. **Score-gap truncation**: rejected on section 2.4.

---

## 6. Samples versus intents, and the neighbour vote as a classifier (decision 47)

### 6.1 Confirmation: the block carries samples

| quantity | value |
| --- | ---: |
| lines per row | **20 samples**, never intents |
| total lines across 1,080 rows | 21,600 |
| distinct pool values used | 4,990 of the 9,354-value pool |
| lines parsing as `<utterance> \| <intent> \| <slots>` | 21,600 / 21,600 |
| lines carrying a slot annotation | 16,635 (77.0 %) |
| lines with intent only | 4,965 (23.0 %) |

Each line is one TRAIN utterance with its gold intent and its gold slot annotation. The block is
twenty **samples**; the intent information in it is implicit, and the model must count for itself.

### 6.2 The vote

Neighbour vote = intent counts over the k neighbours, ties broken by best rank.

| m | vote precision at k = 20 | at k = 15 | at k = 12 | at k = 8 | at k = 5 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | **0.7537** | 0.7546 | 0.7630 | 0.7537 | 0.7630 |
| 2 | 0.8676 | 0.8667 | 0.8694 | 0.8565 | 0.8472 |
| 3 | **0.9056** | 0.9037 | 0.9000 | 0.8907 | 0.8787 |
| 5 | 0.9287 | 0.9241 | 0.9194 | 0.9102 | 0.8852 |

**The vote is saturated by k = 12.** Precision at 1, 2 and 3 is within 0.6 pp of its k = 20 value
already at k = 12, and at m = 1 it is actually higher. Ranks 13-20 add nothing to the vote.

### 6.3 What the model does with the vote

| quantity | value |
| --- | ---: |
| top-voted intent is the gold intent | 0.7537 |
| **B1 official intent accuracy** | **0.8019** |
| anchor official intent accuracy | 0.7796 |
| twin official intent accuracy | 0.7815 |
| B1 delivered intent equals the top-voted intent | 0.7370 |
| anchor delivered intent equals the top-voted intent | 0.7241 |
| B1 delivered = top-voted **and** correct | 0.6907 |

Two readings. First, **the Solver beats its own neighbour vote by +4.8 pp**: it is not a vote
follower, and a form that hands it the vote as a conclusion would cap it below where it already
performs. Second, the exemplars move the delivered intent toward the vote by only **+1.3 pp** over
the anchor, which is consistent with section 3.2's finding that M1's gain is not an intent effect.

### 6.4 The twin's vote

| quantity | B1 arm | derangement twin |
| --- | ---: | ---: |
| vote precision at 1 | 0.7537 | **0.3472** |
| at 2 | 0.8676 | 0.4537 |
| at 3 | 0.9056 | 0.4991 |
| delivered = top-voted | 0.7370 | 0.3806 |

The twin's vote is near-uninformative and its Solver ignores it accordingly, yet the twin still
beats the anchor by +4.77 pp SLU-F1 (`docs/results/2026-09-18-slurp-b1-twin-verdict.md`).
**The 38 % "presence" share of M1's gain is not carried by the vote at all** -- it is carried by
having annotated examples of the task's output form in front of the model. That is a property of
raw lines, not of an aggregate.

### 6.5 Exemplars per intent needed to keep the gold slot types

Over the 666 of 1,080 rows that have at least one gold entity, counting within the gold intent's own
neighbour group:

| exemplars needed | rows | cumulative share of the 666 |
| ---: | ---: | ---: |
| 1 | 513 | 0.7703 |
| 2 | 68 | 0.8724 |
| 3 | 5 | 0.8799 |
| not coverable within the gold-intent group at any r | 80 | -- |

**One** correctly chosen exemplar of the right intent covers 77 % of rows' gold slot types and two
cover 87 %; the residual 12 % is unreachable from same-intent neighbours at any r. This is the
strongest argument for a small few-shot set -- and it is about slot *types*, not surfaces.

---

## 7. Aggregated rendering (decision 47)

Form: `NEIGHBOUR VOTE: <intent> x<count> ...` (top-m) plus, per listed intent, `type:count`, plus r
raw exemplar lines per listed intent rendered with the compact store alias.

| m | r | chars | tokens | saved / contact | saved / row | saving | gold intent listed | type recall | filler recall | saves intent unlisted |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| -- | -- | 2,661 | 732 | -- | -- | -- | 0.9426 | 0.9598 | **0.5719** | 0/42 |
| 3 | 1 | 520 | 143 | 589 | 2,357 | 80.5 % | 0.9056 | 0.9458 | **0.3246** | 4/42 |
| 3 | 2 | 756 | 208 | 524 | 2,097 | 71.6 % | 0.9056 | 0.9458 | **0.4097** | 4/42 |
| 5 | 1 | 643 | 177 | 555 | 2,221 | 75.8 % | 0.9287 | 0.9561 | **0.3418** | 1/42 |
| 5 | 2 | 900 | 248 | 484 | 1,935 | 66.2 % | 0.9287 | 0.9561 | **0.4209** | 1/42 |

The aggregate is remarkable on two axes and poor on the third. **Slot-type recall is essentially
preserved** (0.9458-0.9561 against 0.9598), because the `type:count` aggregate is a lossless summary
of the types the neighbours carry -- and it is preserved at a quarter of the tokens. **Intent
coverage at m = 5 is 0.9287**, only 1.4 pp below the full block. But **filler recall collapses from
0.5719 to 0.32-0.42**, because filler surfaces exist only in raw lines and r lines per intent is a
fraction of the twenty.

Ranked against section 4: at equal tokens the aggregate dominates every k-truncation *on intent and
type* (m = 5, r = 1 at 177 tokens beats rank top-5 at 189 tokens on all three of intent, type and
filler) and loses to them *on filler at higher budgets* (rank top-8 at 299 tokens keeps 0.4932
filler recall where m = 5, r = 2 at 248 tokens keeps 0.4209). Since section 3.2 says the gain is
filler-shaped, the aggregate is **not** a free compression: it is a different mechanism that must be
measured, not assumed.

---

## 8. Prefix and staging (decision 47)

### 8.1 What the prefix already carries

The system message is **byte-identical across all 5,425 contacts and all five roles**: 8,118
characters, one SHA-256. It already contains the legal intent inventory -- the 18 scenarios with
their actions, declared in the text as "60 in total" -- and 55 entity type names. So the **60 intent
ids are already constant prefix**; what is *not* in the prefix is the 60 intent **cards**.

### 8.2 The cards, and what they would cost

The card view that exists is the **intent-boundary store**, `intent-boundaries-v1`: 60 values, one
per intent, one per legal intent id. (The KV-2 "cards" view is a *slot vocabulary* view and it is
`NOT_ADMITTED_ROTATING_TWIN_GATE_FAILED` in the results ledger; it is not the artifact for this.)

| quantity | value |
| --- | ---: |
| cards | 60 |
| raw characters, all 60 | 42,133 |
| rendered characters, all 60 | **45,779** (mean 763 per card) |
| supplied per row today | 8 cards, 6,022 rendered characters |
| estimated tokens, all 60 | **6,100 - 7,150** (see caveat) |
| estimated tokens, today's 8 | about 800 |

**Caveat, and something I could not verify.** There is no tokenizer contact available and no sealed
arm renders a different number of boundary cards, so the card density cannot be *measured* the way
the exemplar block was. The range comes from two independent least-squares fits -- 7.53 chars/token
from the Solver contacts, 6.39 from the Perception contacts -- bracketed by the Perception request's
whole-text ratio of 6.91. Treat 6,600 plus or minus 550 tokens as an estimate.

### 8.3 The arithmetic of the prefix move

| quantity | today | all 60 in the constant prefix |
| --- | ---: | ---: |
| prefix tokens (system + cards) | ~1,310 | ~7,900 |
| prefix prefilled | once per slot, cached thereafter | once per slot, cached thereafter |
| amortised prefix prefill per row (4 slots over 1,080 rows) | ~4.9 | **~29.3** |
| per-row boundary-card client tokens (5.02 contacts) | ~4,020 | **0** |
| per-row boundary-card prefill (measured: ~3 distinct prefills) | ~2,400 | **0** |
| **net prefill change per row** | -- | **about -2,370** |
| **net client-token change per row** | -- | **+35,000, all of it cached prefix** |

The prefill saving is real and is about the same size as the entire exemplar block. Three costs must
be stated with it.

* **Semantics, not tokens, is the risk.** Today's 8 cards are the row's **speech-retrieved** top-8;
  they are the OBS-to-ORG narrowing that produces Perception's at most three candidates. Putting all
  60 in the prefix **deletes that narrowing**. That is a mechanism change of unknown sign, not an
  efficiency change, and it must not be flown as if it were free.
* **KV budget.** `serving_slot_tokens` is 24,576. The Planner's p90 prompt is 13,397 today; adding
  about 6,600 of constant prefix puts p90 near 20,000 and p99 above it. The geometry needs a
  prompt-fit re-check before this could fly at np4.
* **The prefix must actually lead.** Evidence items typed `knowledge_role: "value"` are placed
  **after** the speech query part under `knowledge-speech-state-v2`, so they are not prefix at all
  today. The cards would have to move into the system message or be re-typed as `key`, which is a
  transport change touching every carrier.

### 8.4 The staged design, priced

Proposal: the Solver drafts from the vote plus at most three candidate cards; the drafted intent's
filler exemplars are fetched afterwards through E18 `knowledge-requery`, keyed by speech plus the
drafted intent as state.

**Contacts.** `knowledge-requery` costs **0 model contacts**
(`docs/superpowers/specs/2026-09-19-e18-acquisition-node-design.md`, section 2a). The **Solver
revision after the acquisition costs 1**. Today the flight runs **5.023 contacts per row**
(Perception 1.000, Solver 1.006, Reviewer 2.010, Planner 1.006 -- the REVISE path fires on 9 of
1,080 rows). Staging makes the revision the norm: **6.02 contacts per row, +20 %**.

**Price of that contact, measured.** A Solver contact's median completion is 24 tokens, so decode is
cheap: about 0.6 s per row at the sealed 24.0 ms per generated token. Prefill is the cost. The
sealed traces show that a row's *consecutive same-role* contacts do reuse the slot prefix -- the
Reviewer's two contacts cost 9,212 prefilled tokens per row against a 4,582 per-contact mean, that
is one full prefill plus one small one -- so a revision placed immediately after the draft should
prefill only the acquired block plus the new state, on the order of **1,500 to 2,500 tokens**.

| item | prefilled tokens per row |
| --- | ---: |
| saving: today's whole exemplar block removed from 4 renders | **-2,313** |
| saving: boundary cards moved to the prefix (section 8.3) | **-2,370** |
| cost: amortised prefix | +29 |
| cost: the acquired block still rendered on the revision and after | +400 to +800 |
| cost: one extra Solver contact's marginal prefill | **+1,500 to +2,500** |
| **net** | **-1,700 to -3,500** |

So the staged design is **prefill-neutral to modestly positive** only because the prefix move is
bundled into it. Scored on its own -- staging without the prefix move -- it costs +1,900 to +3,300
and saves 2,313, that is **about zero**. It is a capability proposal, not an efficiency one, and it
should be argued on capability.

**Information boundary.** Clean. The acquisition key is the row's own sealed speech vector,
restricted by state; the drafted intent is the model's own output, which the 2026-09-06 ruling
admits as state beside speech and forbids only as a text-only key. `derive_state_filters` restricts
a speech-keyed ranking rather than replacing it. Gold never enters. The dedupe requirement over
`retrieved_value_ids` is what the aborted B1 attempt 1 tripped over, and E3c's
`restrict_repeat_visit_supply` plus E18's own dedupe already cover it.

**The risk, quantified.** If the acquisition narrows to the drafted intent, it fetches the right
intent's exemplars only when the draft is right. B1's official intent accuracy is **0.8019** and the
top-voted intent is gold on **0.7537**. Today the block holds a gold-intent exemplar on **0.9426**
of rows. Narrowing on the draft therefore cuts the availability of gold-intent exemplars by
**-14.1 pp** (0.9426 to 0.8019) -- and it cuts it precisely on the rows that were already going
wrong. Narrowing on the top-3 vote instead (0.9056) costs -3.7 pp and is the safer key.

---

## 9. Per-role presence of the block today (decision 49)

Per row, over the 1,080 sealed rows. "Block present" is read from the request's own
`supplied_evidence`; "prefill delta" is B1 minus the sealed anchor on `timings.prompt_n`.

| role | contacts / row | block present | block chars | block tokens per contact | block client tokens / row | measured prefill delta / row |
| --- | ---: | :--: | ---: | ---: | ---: | ---: |
| Perception | 1.000 | **no** | 0 | 0 | 0 | -12.5 (noise) |
| Solver | 1.006 | **yes** | 2,660 | 732 | 737 | **+760.4** |
| Reviewer 1 and 2 | 2.010 | **yes, both** | 2,660 | 732 | 1,472 | **+783.3** |
| Planner | 1.006 | **yes** | 2,660 | 732 | 737 | **+781.9** |
| **total** | **5.023** | **4.02 renders** | -- | -- | **2,946** | **+2,313.1** |

**The block is not confined to the Solver boundary.** It is rendered into four of the five contacts
of every row. The measured client-token delta per row is **+3,139.5** -- the table's 2,946 plus the
extra contacts on REVISE rows. In prefill terms it is paid **three times**, not once: the Reviewer's
second contact reuses the first's prefix, but the Solver, the Reviewer pair and the Planner each pay
a full 760 to 783 token prefill, because a row's contacts are interleaved across four slots and the
prefix does not survive between them.

**The owner's instinct is right about the repetition and understates it.** Confining the raw block
to the Solver alone -- rendering an intent and slot-type summary to the Planner and Reviewer instead
-- would save about **1,553 prefilled tokens per row, 67 % of the block's prefill cost**, with **no
change at all to what the Solver sees**, and therefore with a strong prior of exact neutrality on
the official number. That is a larger saving than k = 12 (1,148 client tokens, about 575 prefilled)
and it touches no coverage curve in this report.

One caveat before that is called free: the Reviewer's job includes checking the Solver's answer
against its evidence, and it cites value ids. A Reviewer that no longer sees the lines it is asked
to audit is a behaviour change. The summary it receives must carry the value ids so the citation
path survives, and the twin in section 11.1 exists to measure exactly this.

---

## 10. The owner's vote-plus-few-shot form, priced (decision 49)

Form: `NEIGHBOUR VOTE: <intent> x<count> ...` (top-m) `| SLOT TYPES SEEN: <intent>: type:count ...`
`| FEW-SHOT: at most `cap` raw lines in total, at most one per listed intent, best-scored first`.

| m | few-shot cap | chars | tokens | saved / contact | saved / row | saving | gold intent listed | type recall | filler recall | saves intent unlisted |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| -- | as flown, 20 lines | 2,661 | 732 | -- | -- | -- | 0.9426 | 0.9598 | **0.5719** | 0/42 |
| 3 | 2 | 446 | 123 | 610 | 2,438 | 83.2 % | 0.9056 | 0.9458 | 0.3021 | 4/42 |
| 3 | 3 | 520 | 143 | 589 | 2,357 | 80.5 % | 0.9056 | 0.9458 | 0.3246 | 4/42 |
| **5** | **2** | **483** | **133** | **599** | **2,395** | **81.8 %** | **0.9287** | **0.9561** | **0.3023** | **1/42** |
| 5 | 3 | 557 | 153 | 579 | 2,316 | 79.1 % | 0.9287 | 0.9561 | 0.3278 | 1/42 |
| 3 | 0 (vote only) | 222 | 61 | 671 | 2,685 | 91.7 % | 0.9056 | 0.9458 | **0.0000** | 4/42 |
| 5 | 0 (vote only) | 258 | 71 | 661 | 2,644 | 90.3 % | 0.9287 | 0.9561 | **0.0000** | 1/42 |

### 10.1 Reading it against section 3.2

The owner's hypothesis splits cleanly into two claims and the sealed data answers them differently.

* **"The aggregated intent information is what matters."** Partly true, and cheaply obtained. m = 5
  costs 71 tokens against 732 and keeps **0.9287 of gold-intent listing and 0.9561 of slot-type
  recall** -- 99 % of the intent coverage and 99.6 % of the type coverage for **10 %** of the
  tokens. That is the strongest efficiency result in this report.
* **"A few-shot capacity of 2-3 raw lines is enough."** This is where the risk is, and it is
  measurable. Filler recall falls from 0.5719 to **0.302-0.328**. Section 3.2 says 76.9 % of B1's
  277 SLU saves were slot-only changes and 133 of the 154 newly correct fillers were printed in the
  block. A 2-3 line few-shot set cannot carry twenty lines' worth of surface forms, and vote-only
  carries none at all.
* **The presence floor.** The twin -- deranged, so its vote is near-noise at 0.347 precision -- still
  beat the anchor by **+4.77 pp**. That floor is bought by having annotated examples of the output
  form present at all, so a few-shot set of 2-3 lines should keep most of it. The **key** share --
  +7.83 pp, 62 % of M1's gain -- is bought by the examples being *this row's* neighbours, and
  section 3.2 localises that share in the filler surfaces. A vote-only form should be expected to
  lose most of the 62 %, and a 2-3 line form to lose part of it.

### 10.2 Predicted effect, stated as a prediction

Taking M1's +12.61 pp as 38 % presence (+4.77) and 62 % key (+7.83), and using save-filler retention
as the proxy for the key share that survives:

| form | tokens / contact | presence share kept | key share kept (proxy) | predicted SLU delta vs anchor |
| --- | ---: | ---: | ---: | ---: |
| as flown, k = 20 | 732 | 1.00 | 1.00 | +12.61 (measured) |
| compact rendering only | 627 | 1.00 | 1.00 | **+12.6, free** |
| rank top-12, compact | 385 | 1.00 | 0.89 | about +11.7 |
| vote (m = 5) + 3 lines | 153 | ~0.85 | ~0.33 | about **+6.7** |
| vote (m = 5) only | 71 | ~0.30 | 0.00 | about **+1.4** |

The last two rows are **predictions from an offline proxy, not measurements**, and they are the
reason this form must not be registered as a "free saving".

---

## 11. Final ranking and the one cell to register first

Criterion: tokens saved per unit of *measured* risk to the mechanism section 3.2 identified.

| rank | form | client tokens saved / row | prefill saved / row | risk to the measured mechanism | evidence class |
| ---: | --- | ---: | ---: | --- | --- |
| **1** | **Confine the raw block to the Solver; summary to Planner and Reviewer; compact store alias; rank order** | **~2,300** | **~1,800** | **none to the Solver's own input** | measured |
| 2 | Compact rendering alone (store alias + compact slots) | 430 | ~340 | **zero, provably** | measured |
| 3 | Rank top-12 + compact + rank order | 1,540 | ~1,200 | -1.5 pp intent, -4.2 pp filler, 1/42 saves | measured curves |
| 4 | Intent cards into the constant prefix | prefill only | ~2,370 | deletes the OBS-to-ORG narrowing; KV budget | estimated |
| 5 | Vote (m = 5) + 2-3 few-shot lines (owner's form) | ~2,320 | ~1,800 | **-24 pp filler recall**; predicted -5 to -6 pp SLU | predicted |
| 6 | Staged draft-then-acquire (E18) | ~0 | ~0 | -14.1 pp gold-intent availability if keyed on the draft | estimated |
| 7 | Per-intent cap | ~1,800 | ~1,400 | best intent/token, worst filler/token | measured |
| 8 | Score-gap truncation | ~2,000 | ~1,600 | unstable k; -11 pp intent | measured |

### 11.1 The cell to register first

**M1-COMPACT-1: one Solver-identical rendering change.** It is the only item on the list whose
Solver input is *provably unchanged in meaning* while its token cost falls, so it is the cleanest
possible test of decision 46's question, and it is the fastest way to buy GPU hours back for the
queue.

**Form.**

* The raw twenty-line block is rendered **only** into the Solver contact.
* The Planner and the two Reviewer contacts receive, in its place, the aggregated view --
  `NEIGHBOUR VOTE` plus `SLOT TYPES SEEN` plus **the twenty value ids**, so `cited_value_ids` and
  the I7 custody chain are untouched: about 90 tokens instead of 732.
* Every exemplar line renders with the compact store alias `tex:<slurp_id>` -- 14.3 % of the block,
  zero coverage change.
* The block is ordered **most-relevant-first** (descending retrieval score), replacing today's
  lexicographic order.
* k stays at **20**. Nothing about the Solver's coverage curves moves.

**Predicted saving.** About 2,300 client tokens and about 1,800 prefilled tokens per row -- roughly
7 % of the row's prefill, about **0.16 GPU hours per 1,080 rows** at the measured 2,048 tokens per
second, and proportionally more after L1.

**Config keys** -- a new rendering mode on the exemplar supply, knobs only:

```
knowledge_stores.train-exemplars.phase_supply.solver.render:       "raw-ranked-compact-v1"
knowledge_stores.train-exemplars.phase_supply.solver.render_order: "score-desc"
knowledge_stores.train-exemplars.phase_supply.solver.id_alias:     "tex"
knowledge_stores.train-exemplars.projection.planner:               "vote-summary-v1"
knowledge_stores.train-exemplars.projection.reviewer:              "vote-summary-v1"
knowledge_stores.train-exemplars.projection.vote_m:                5
```

No new module under `rails/probes/`, no `TaskAdapter` subclass, no new controller: one renderer
registered in the existing `core.base` rendering registry plus config fragments -- exactly the
"one base, thin derivations" rule of the 2026-09-03 owner directives.

**Comparator.** The sealed B1 arm,
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2` (scores
`a7105b328509a8bd00c4678fd076e9be4d242b6189bb82bbd290bd596e3c9078`), read paired on the same TRAIN
Fold A roster of 1,080 rows.

**Margins.** B1's **own null**, once cell B1r supplies it (owner decision 38). Until then the cell
does not read: it must not inherit B0r's `h_SLU = 1.1218` / `h_intent = 1.0051`, and it must not be
assumed neutral.

**Decision rule.** NEUTRAL on the official SLU-F1 and on intent, within B1r's own-null half-widths,
means **the saving is free -- adopt**. Positive beyond the half-width is ADMITTED. **HARMFUL
requires a measured loss** (decision 25), never interval width alone.

**The form twin it needs.** A *rendering* twin, not a k twin: same k = 20, same ordering, compact
alias against full alias, raw block on all four roles against Solver only. Two arms separate the two
changes.

* `M1-COMPACT-1a` -- compact alias plus rank order, block still on all four roles. Isolates the
  rendering change.
* `M1-COMPACT-1b` -- 1a plus Solver-only confinement. Isolates the repetition removal, which is the
  part that could change Reviewer and Planner behaviour.

If 1b reads HARMFUL while 1a reads NEUTRAL, the repetition is load-bearing for the Reviewer, and
that finding is itself worth the flight.

**Order in the queue.** After **EFF-1** (in flight), after **B1r** -- which supplies the margins
this cell reads against, and without which no verdict is possible -- and after **B8b-anchor**. It is
independent of all three, and it needs no new asset, no new retrieval and no new prompt text.

### 11.2 Second, and what should not be registered as an efficiency cell

**Second:** `M1-K12-1`, rank top-12 with the same compact rendering. It is a real coverage change
(-1.48 pp gold intent, -4.17 pp filler recall, 1 of 42 saves loses its support) with a real saving,
and it should be read on its own after the free item has banked its GPU hours.

**Not as an efficiency cell:** the owner's vote-plus-few-shot form (section 10) and the staged E18
design (section 8.4). Both are **mechanism changes with a predicted cost to the measured mechanism**
-- -24 pp filler recall and -14.1 pp gold-intent availability respectively -- and pricing them as
compressions would mis-frame a NEUTRAL result as a free saving and a HARMFUL result as a compression
failure. If the owner wants the aggregated form, it should fly as an *effectiveness* cell with its
own hypothesis ("the intent histogram plus a small few-shot set is sufficient"), its own bar, and
the vote-only arm as its floor -- and section 10.2 predicts it reads around +6.7 pp against the
anchor rather than +12.6.

---

## 12. What I could not verify

* **Token counts for text that never flew.** There is no tokenizer contact, so every simulated
  form's token count is characters divided by the 3.634 chars/token measured on the sealed block.
  That ratio is exact for exemplar lines and is **not** valid for the vote header and the
  `type:count` aggregate, which are label-dense and will tokenize worse -- more tokens per character
  -- than natural speech text. Sections 7 and 10 therefore **understate** the aggregate forms' token
  cost, probably by 10 to 25 %. The direction of the ranking does not change, because the aggregate
  forms are already ranked below the free items.
* **The 60-card prefix size** is an estimate, 6,100 to 7,150 tokens, bracketed by three
  least-squares fits, because no sealed arm renders a different number of boundary cards.
* **The `slot-contracts` block's token cost** (about 5,070) is a least-squares estimate, not a
  paired measurement: no sealed TRAIN Fold A arm omits that store at the Solver. Its headline role
  in section 0 finding 1 is therefore an estimate; the exemplar block's 737 is a measurement.
* **Every predicted score in section 10.2.** They are offline proxies built from save-filler
  retention and the twin's presence/key split. They are predictions and they are labelled as such.
* **Whether the Reviewer's behaviour depends on seeing the raw lines.** Section 9's proposal assumes
  it does not; the twin arm `M1-COMPACT-1b` exists precisely because that assumption is unverified.
* **Whether the prefix cache would actually hold a 7,900-token constant prefix** across the whole
  flight at np4 with `serving_slot_tokens` 24,576. The KV arithmetic is stated in section 8.3; it
  has not been demonstrated.
* **Greedy decoding is not bitwise reproducible** across batch compositions on this server, so every
  cross-arm row-level comparison in section 3 is against *sealed outputs*, never re-decoded.
* The **EFF-1** campaign was in flight throughout; its run directory was not opened.
