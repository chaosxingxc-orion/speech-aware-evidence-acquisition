# KC-E1f verdict — REJECTED, and what was measured to say so

Exposure row `SAEA-E21-KC-E1F-VERDICT-V1` (`model-free-check`), registered and committed before the
first sealed byte was opened. **Zero model, GPU, tool, embedder, tokenizer, network, audio-decode and
paid-API contacts.** Reference transcripts and `wer_tags` are reached only through the registered
scoring path's own loaders (`data.references`, `reproduction.conec_entity_scoring`,
`reproduction.numeric_value_accuracy`, `reproduction.semantic_impact`), inside
`scripts/e21_window_pairing_read.py`; nothing else in this receipt opens a reference, and the §5.1
attribution instrument opens none at all — it compares two sealed hypothesis sets to each other.

The verdict, the rule quoted verbatim, and every reading of it:
`docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v1-verdict.md`. **This directory holds the evidence;
the note holds the argument.**

## The one-line result

**REJECTED** — the preregistration's own word is HARMFUL. The primary is met on both legs (PERSON
entity-WER reduction **+3.737 pp** [+2.653, +4.855] against the sealed comparator and **+3.840 pp**
[+2.752, +4.958] against the token-matched twin, call-clustered CI90); **corpus-WER non-inferiority,
the guard that rejected KC-E1, passes in this cell's favour** (−0.045 pp [−0.061, −0.029], the arm
strictly better); and **two guards fail** — numeric-value accuracy at the call-pooled figure
(+0.0103 pp [−0.0212, +0.0512], lower bound below zero although the point estimate is better) and
over-generation (+0.00028 pp [−0.00199, +0.00255], upper bound above zero on a difference of **one
insertion in 10,700**).

## The three arms and the identity anchor

| arm | run id | attempt | anchor | corpus WER, per-window sum vs sealed | S / D / I |
|---|---|---|---|---|---|
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | `attempt-20260904T233816Z-bcd338` | 30/30 **PASS** | 8.1995 % vs 8.200 % | 13,098 / 5,701 / 10,700 |
| form twin | `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1` | `attempt-20260908T072231Z-ec8a5b` | 30/30 **PASS** | 8.2015 % vs 8.201 % | 13,105 / 5,699 / 10,702 |
| treatment | `SAEA-E21-KC-E1F-REPAIR-44-V1` | `attempt-20260908T040832Z-ecda9c` | 30/30 **PASS** | 8.1545 % vs 8.154 % | 12,936 / 5,700 / 10,701 |

The comparator is not only the comparator: it is **both treated arms' pass 1**, the bytes they edited.

Each arm's 1,593 per-window rows re-aggregate to its own sealed corpus WER, S/D/I, reference words,
the eight published ConEC classes, the non-entity and unlabelled buckets, the negation-critical counts
and the numeric partition **exactly**, through the fixed window-pairing instrument whose
`obs_delivered_text` branch reads the DELIVERED post-processed span rather than the raw pass-2 answer.
The class anchor is then widened to **every** key of the mirror's `by_entity_type` — 29 buckets × 3
arms = **87 checks, 87 PASS** — against each arm's own committed score receipt, so no column of the
per-class table is unanchored. The verdict runner refuses to compute a contrast for an arm whose
anchor is not `PASS`, and re-checks each rows file's SHA-256 against the one its anchor recorded.

## The §5.1 attribution, which runs before any contrast and can abort the read

`scripts/e21_kc_e1f_normalization_attribution.py`, receipts in `attribution/`. The delivery guarantee
is exact in RAW whitespace-token space and the scored numbers are NORMALIZED, so §5.1 requires every
normalized deletion/insertion move to be carried by a substituted span, and calls anything else a
defect that aborts the read.

| | KC-E1f | KU-E1fc |
|---|---:|---:|
| raw whitespace tokens, both sides | 372,488 | 372,488 |
| differing raw positions (= the flight's own count) | 2,545 | 2,154 |
| substituted spans | 1,890 | 1,528 |
| normalized-word delta vs comparator | **+2** | **+4** |
| `(I − D)` delta from the anchors | **+2** | **+4** |
| carried by substituted spans and their ±8-token boundary | **100 %** | **100 %** |
| interior tokens more than 8 tokens from any substitution | 342,028 | 346,820 |
| interior segments whose contribution moved | **0** | **0** |
| the same identity, per call | **44 / 44 PASS** | **44 / 44 PASS** |

The attribution's own normalized word counts (364,764 / 364,766 / 364,768) equal each arm's **own
sealed scorer's** `hypothesis_words` exactly. At the operation level, **zero** windows on **any** of
the 29 class buckets in **either** arm moved a deletion count without carrying an accepted
substitution; the five windows carrying the PERSON deletion move 83 → 80 carry 3, 1, 3, 4 and 1
substituted spans respectively.

**Content-free by construction.** Not one hypothesis character is in this receipt: spans are recorded
as index ranges, token counts, normalized word counts and a character-class shape signature. The full
span tables live beside the per-window rows under `SPEECHRL_DATA_DIR` and their SHA-256 values are
pinned in `attribution/*/attribution.json`.

## What is in each file

| file | what |
|---|---|
| `result-summary.json` | the whole read: the decision block with every guard applied as written, the three identity anchors, the 87-check class anchor, the §5.1 attribution and its five checks per arm, the operation-delta localization, the three contrasts (total / form / content) over 34 metrics under three interval readings and two weightings, both saturation sensitivities, the descriptive window layer with the exact sign test, the 44-row per-call block, the E5 halves, both repair ledgers and the token covariate |
| `per-call-table.md` | the 44 calls: corpus WER and PERSON entity WER in all three arms, PERSON reference words, each cell's accepted substitutions and saturated windows |
| `token-throughput-covariate.json` | the measured +7-token match (min = median = max = 7 on 1,593 of 1,593 windows), both flights' token, cost, throughput and serving-monitor blocks, with each receipt's SHA-256 |
| `reaggregation/{comparator,kc-e1f,ku-e1fc}/reaggregation.json` | the identity anchor of each arm — every check, the pooled buckets, the per-call numeric rows, the rows file's path and SHA-256 |
| `attribution/{kc-e1f,ku-e1fc}/attribution.json` | the §5.1 receipt: construction checks, the `(I − D)` identity, the interior-zero proof, every span with a non-zero normalization delta, the per-window movement table and the per-call table |
| `MANIFEST.sha256` | this directory's byte manifest |

## How it was produced

```
python scripts/e21_window_pairing_read.py --run-id <run> \
    --out-dir docs/checks/.../2026-09-08-e21-kc-e1f-verdict/reaggregation/<slug> \
    --rows-out $SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/kce1f-verdict-window-rows-<slug>.json

python scripts/e21_kc_e1f_normalization_attribution.py \
    --treated-run-id <run> --treated-attempt-id <attempt> \
    --out-dir docs/checks/.../2026-09-08-e21-kc-e1f-verdict/attribution/<slug>

python scripts/e21_kc_e1f_verdict_read.py \
    --reaggregation-dir docs/checks/.../2026-09-08-e21-kc-e1f-verdict/reaggregation \
    --attribution-dir  docs/checks/.../2026-09-08-e21-kc-e1f-verdict/attribution \
    --rows-dir $SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1 \
    --out-dir  docs/checks/.../2026-09-08-e21-kc-e1f-verdict
```

Seed 20260903, 10,000 replicates, CI90, pairing at the fixed 90-second window and clustering at the
call — the frozen constants of `analysis.e21_window_pairing`, not arguments this read chose.
