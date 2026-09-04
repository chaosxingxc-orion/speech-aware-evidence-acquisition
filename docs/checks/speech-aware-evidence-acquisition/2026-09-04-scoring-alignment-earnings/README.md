# Earnings-21 scoring alignment, zero contact (2026-09-04)

Exposure row: `SAEA-E21-MF-SCORING-ALIGNMENT-V1` (`docs/exposure-ledger.md`). Profile
`model-free-check`, reference-reading. **Zero model, GPU, tool, embedding, network and audio
contacts** — every number is a pure function of already-sealed outputs bytes and the frozen
`earnings21-original` reference layer.

## What was scored

Three sealed, FINALIZED bundles on the frozen ten discovery calls of `r4-e21-sub10`
(split identity `744c4b2e2d2eece3b05c68089c02000e38c96d5c62db8055d9c421fd509a8f61`,
study commit `c28e3a45899847fe1f6ff456953cec696a7060d8`):

| run | attempt | arm | evidence source | baseline fragment |
|---|---|---|---|---|
| `SAEA-E-005B-N10-zero` | `attempt-20260814T235515Z-044ccc` | `bare-core` | `none` | `fixed-batch-zero-locked-buf90` |
| `SAEA-E-005B-N10-matched` | `attempt-20260815T011459Z-30cb33` | `fixed-legal-context` | `conec-contexts` | `fixed-batch-matched-locked-buf90` |
| `SAEA-E-005B-N10-names` | `attempt-20260815T025126Z-30d1a1` | `fixed-legal-context` | `conec-names` | `fixed-batch-names-locked-buf90` |

Observation geometry (identical in all three arms, from the sealed `obs-derivation` artifacts):
fixed 90-second windows, no VAD trim, no overlap, 342 windows over 30,406.93 s = **8.446 h**, i.e.
**10 of the corpus's 44 calls (~21.5 % of its 39 h 15 min)**. Per-call durations 30.3–74.6 min.
The pathological call `4346923` (16 kHz, Industrial Goods, the file the Earnings-21 paper says
degrades every system) is **not** in this ten.

## Two scoring paths, and why both were needed

1. **Verified path** — `core.scoring_batch` (`saea-driver score-batch --jobs ... --include-per-sample`),
   one complete `run-manifest.json` per job, three jobs, three workers, nothing sharded.
   Files: `verified-score-batch-jobs.jsonl`, `verified-score-batch-summary.json`,
   `verified-score-batch-read.json`. All three jobs returned `"verified": true` and reproduced
   their sealed `asr-wer` aggregate exactly.
   **Limit found:** the sealed manifests declare `"scorers": ["asr-wer", "cost"]`, and
   `core.scorers.score_bundle` runs exactly the manifest's own list. The verified path therefore
   **cannot** emit `asr-wer-whisper` or `entity-wer` for these bundles; changing the sealed
   manifest to add them would break its hash binding. This is reported, not patched.
2. **Registered-scorer path** — the same registered scorer objects (`core.base.SCORERS.resolve`)
   applied directly to the sealed `outputs.jsonl`, exactly as
   `analysis.entity_wer_offline` already does for the deferred entity read.
   File: `rescore.json` (schema `saea-earnings21-scoring-alignment-v1`), produced by
   `rescore.py` in this directory.

Two identity anchors gate every new number: the recomputed `asr-wer` mean must equal the sealed
`scores.json` value bit for bit, and the recomputed `entity-wer` corpus value must equal the
prior sealed offline read under `SPEECHRL_DATA_DIR/derived/entity-wer/`.

## Metric definitions used here

| scorer | normalizer | unit | aggregation reported |
|---|---|---|---|
| `asr-wer` | frozen `saea-scoring-v1` (`scoring/normalize.tokens_v1`) | word | corpus (micro) **and** mean of per-call WER |
| `asr-wer-whisper` | vendored Whisper `EnglishTextNormalizer` (upstream `v20240930`) on **both** sides, then whitespace split | word | corpus (micro) **and** mean of per-call WER |
| `entity-wer` | frozen `normalize_text_v1` on the mention string | **entity mention** | corpus count ratio `1 - correct/expected`, **and** mean of per-call values |

Corpus-level WER is `sum(S+D+I) / sum(hits+S+D)` computed from the counts each scorer already
records per call; no alignment is re-implemented here.

**`entity-wer` is not fstalign's entity WER.** fstalign divides alignment errors on entity-tagged
reference *tokens* by entity-tagged reference *tokens*. This scorer divides *mentions not
reproduced verbatim* by *gold mentions*: a mention counts correct only when every one of its
normalized token positions is an exact `align()` hit (no partial credit), so its precision is
trivially 1.0 by construction and only the recall-derived error rate is meaningful. The two
families are not interchangeable. fstalign was **not** installed or run.

## Results — both aggregations, both WER families

Reference words: 77,148 under `saea-scoring-v1`, 75,751 under the Whisper normalizer (the
normalizer removes the fillers `hmm|mm|mhm|mmm|uh|um`, bracketed/parenthesised spans, and
standardizes numerals, currency and contractions on **both** sides).

| arm | `asr-wer` corpus | `asr-wer` mean-of-calls | **Whisper-norm corpus** | Whisper-norm mean-of-calls | S / D / I (Whisper) |
|---|---|---|---|---|---|
| zero (`bare-core`) | 12.025 | 12.385 | **7.137** | 7.281 | 2396 / 933 / 2077 |
| matched (`conec-contexts`) | 12.000 | 12.394 | **7.241** | 7.374 | 2272 / 1168 / 2045 |
| names (`conec-names`) | 10.278 | 10.879 | **7.460** | 7.819 | 2265 / 1451 / 1935 |

Per-call Whisper-normalized WER (%), sorted by call id:

| call | minutes | zero | matched | names |
|---|---|---|---|---|
| 4330115 | 41.0 | 7.18 | 7.00 | 6.65 |
| 4365024 | 72.1 | 6.91 | 6.86 | 7.04 |
| 4365948 | 42.0 | 4.46 | 4.85 | 4.68 |
| 4366429 | 66.8 | 6.50 | 6.72 | 6.78 |
| 4366522 | 30.3 | 6.28 | 5.65 | 5.60 |
| 4384964 | 67.0 | 8.04 | 8.26 | 7.62 |
| 4385072 | 42.7 | 5.12 | 6.02 | 7.33 |
| 4387383 | 36.0 | 6.78 | 7.60 | 7.73 |
| 4389907 | 34.3 | 13.34 | 12.71 | 16.79 |
| 4397829 | 74.6 | 8.19 | 8.08 | 7.96 |

Per-call `saea-scoring-v1` WER (%), the frozen in-house metric, for completeness (this family has no
published counterpart and must never be compared to one):

| call | reference words | zero | matched | names |
|---|---|---|---|---|
| 4330115 | 6690 | 11.75 | 10.72 | 9.22 |
| 4365024 | 11851 | 12.19 | 12.58 | 9.75 |
| 4365948 | 6785 | 10.30 | 9.24 | 7.46 |
| 4366429 | 11442 | 11.11 | 11.20 | 9.85 |
| 4366522 | 4249 | 11.01 | 12.33 | 10.10 |
| 4384964 | 10301 | 11.23 | 11.71 | 9.74 |
| 4385072 | 6605 | 11.48 | 12.66 | 10.33 |
| 4387383 | 3686 | 12.75 | 13.81 | 10.77 |
| 4389907 | 4136 | 19.66 | 18.16 | 21.86 |
| 4397829 | 11403 | 12.37 | 11.53 | 9.73 |

### The finding that matters most: the ConEC-names gain is normalizer-dependent

Under the frozen `saea-scoring-v1` metric the names roster is the best arm by 1.75 points corpus /
1.51 points macro — the 2026-08-15 N10 verdict's headline. **Under the Whisper normalizer that
ordering inverts**: names is the *worst* arm (7.460 vs 7.137). The mechanism is visible in the
counts: the names roster trades substitutions and insertions for **deletions** (933 → 1,451
Whisper-normalized deletions), concentrated in two calls — 4385072 (58 → 222) and 4389907
(41 → 226), with 4366429 (221 → 293) and 4387383 (41 → 87) contributing. The Whisper normalizer
collapses most of the substitution/insertion differences the in-house metric credits (numerals,
contractions, fillers) and leaves the deletions standing. Any claim that ConEC-names supply
improves Earnings-21 WER must state which normalizer it is under.

## Entity WER

Corpus-level (`1 - correct/expected` over gold mentions), all 24 `wer_tags` classes present in
these ten calls, 8,284 gold mentions:

| arm | corpus entity WER | mean of per-call | correct / expected |
|---|---|---|---|
| zero | 32.014 | 33.814 | 5,632 / 8,284 |
| matched | 29.104 | 30.906 | 5,873 / 8,284 |
| names | 19.954 | 21.848 | 6,631 / 8,284 |

These reproduce the prior sealed offline reads under
`$SPEECHRL_DATA_DIR/derived/entity-wer/<run>/` exactly (second identity anchor).

Restricted to the eight **non-numeric** classes ConEC Table 2 reports (PERSON, ORG, GPE, LOC,
PRODUCT, EVENT, NORP, FAC — 1,612 gold mentions of the 8,284):

| arm | subset entity WER | PERSON | ORG | GPE | LOC | PRODUCT | EVENT | NORP | FAC |
|---|---|---|---|---|---|---|---|---|---|
| zero | 26.92 | 22.6 | 29.3 | 24.0 | 5.4 | 62.2 | 42.5 | 19.0 | 72.7 |
| matched | 21.46 | 17.4 | 23.0 | 18.9 | 2.7 | 37.8 | 45.2 | 23.8 | 72.7 |
| names | 21.65 | 18.1 | 25.8 | 18.6 | 2.7 | 28.9 | 31.5 | 19.0 | 63.6 |
| **ConEC row 8** — Whisper large, no context | (7.98 overall WER) | **28.9** | **19.6** | **17.0** | **5.85** | **18.7** | **2.78** | **8.54** | **21.6** |
| **ConEC row 1** — no-biasing floor (71.5M zipformer, in-domain) | (10.41) | 45.9 | 29.5 | 18.8 | 5.85 | 24.2 | 43.1 | 9.55 | 28.7 |
| **ConEC row 5** — oracle ceiling (same zipformer) | (9.69) | 13.0 | 17.7 | 12.9 | 5.46 | 19.2 | 35.6 | 5.53 | 16.6 |

Class supports in our ten calls: PERSON 447, ORG 608, GPE 333, LOC 74, PRODUCT 45, EVENT 73,
NORP 21, FAC 11. The last four are too small to carry a 3-point judgement.

## Alignment against the published Earnings-21 bracket (owner rule, 2026-09-04)

**Whisper-normalizer family only.** All published rows are corpus-level, whole-recording, all 44
files. Ours is corpus-level, whole-recording (90-s windows concatenated), **10 of the 44 calls**.

| ours (corpus, Whisper norm) | published row | source | delta (ours − published) | verdict |
|---|---|---|---|---|
| zero **7.137** | `openai/whisper-large-v3` **9.71** | ASR Leaderboard long-form CSV, 44 files | −2.57 | **aligned** |
| matched **7.241** | same 9.71 | " | −2.47 | **aligned** |
| names **7.460** | same 9.71 | " | −2.25 | **aligned** |
| zero 7.137 | Whisper large-v2 **9.7** | Whisper paper App. D.4 | −2.56 | **aligned** |
| zero 7.137 | TRADE speech-LLM **9.75** | arXiv:2606.08486 Table 2 | −2.61 | **aligned** |
| zero 7.137 | FastConformer **13.84** | same table | −6.70 | **aligned-better** |

Degraded-model floor rule (our WER must never be higher than a degraded system's published WER):

| floor | number | zero 7.137 | matched 7.241 | names 7.460 |
|---|---|---|---|---|
| Whisper medium.en (App. D.4) | 10.2 | clear | clear | clear |
| Whisper small.en | 10.8 | clear | clear | clear |
| Whisper base.en | 12.5 | clear | clear | clear |
| Whisper tiny.en | 17.0 | clear | clear | clear |
| FastConformer FT+LCA+GT | 13.84 | clear | clear | clear |
| Qwen2-Audio-7B (FinAudio, **normalizer unnamed**) | 26.06 | clear | clear | clear |

**Every floor is cleared and every Whisper-normalizer target is aligned.** Caveats that must
travel with that sentence:

1. **Subset.** Ten calls — 4330115, 4365024, 4365948, 4366429, 4366522, 4384964, 4385072, 4387383,
   4389907, 4397829 — 8.446 h of the corpus's 39 h 15 min (21.5 %). The corpus's known
   pathological file `4346923` (16 kHz, Industrial Goods; the Earnings-21 paper: "If this file is
   excluded from evaluation, our internal Kaldi model is the most accurate") is **not** in the ten.
   Every published row includes it. A like-for-like number needs all 44 calls.
2. **Protocol noise exceeds the tolerance.** Whisper large-v2's own decoding heuristics move
   Earnings-21 by 1.1 points (10.7 greedy → 9.63 with previous-text conditioning, Whisper Table 7),
   so a ±3-point band around 9.7 is only about three times the reference's own protocol spread.
3. **Reference source.** Our reference is the frozen `.nlp` token stream joined with spaces and then
   Whisper-normalized; the leaderboard normalizes its own reference text and additionally forgives
   split-vs-joined compounds (`kaldialign.batch_error_rate(..., merge_compounds=True)`). We do not
   apply `merge_compounds`, which can only work against us.
4. **Never mix families.** The fstalign family (Rev ESPNet 11.3 / 12.8, Microsoft 15.8, Google 17.8,
   the repo's per-class entity table) uses Rev's synonym and reference-normalization files, not the
   Whisper normalizer. The frozen in-house `saea-scoring-v1` corpus numbers (12.03 / 12.00 / 10.28)
   happen to land within 3 points of 9.71 as well, but that is a coincidence of two unrelated
   metrics and must never be reported as an alignment.

### Entity WER against the ConEC bracket

| class | ours (best arm) | ConEC row 8 (Whisper large, no ctx) | verdict | ConEC row 1 floor | floor cleared? |
|---|---|---|---|---|---|
| PERSON | 17.4 (matched) | 28.9 | **aligned-better** (−11.5) | 45.9 | yes (all arms) |
| ORG | 23.0 (matched) | 19.6 | not aligned (+3.4) | 29.5 | yes (all arms) |
| GPE | 18.6 (names) | 17.0 | **aligned** (+1.6) | 18.8 | names yes (18.6); matched fails by 0.1 (18.9); zero fails (24.0) |
| LOC | 2.7 (matched/names) | 5.85 | **aligned-better** (−3.15) | 5.85 | yes (all arms) |
| PRODUCT | 28.9 (names) | 18.7 | not aligned (+10.2) | 24.2 | **no** (all arms) |
| EVENT | 31.5 (names) | 2.78 | not aligned (+28.7) | 43.1 | names/zero yes, matched **no** (45.2) |
| NORP | 19.0 (zero/names) | 8.54 | not aligned (+10.5) | 9.55 | **no** (all arms) |
| FAC | 63.6 (names) | 21.6 | not aligned (+42.0) | 28.7 | **no** (all arms) |

Caveats: **segment-level vs long-form** (ConEC segments Earnings-21 at sentence boundaries; Whisper
large scores 7.98 there against 10.3 on whole files — roughly 2.3 points of the gap is the
segmentation, not the system); **fstalign was not run here** and is not installed, so this is a
mention-level `1 − recall` metric against a token-level fstalign metric; ConEC rows 1–5 are a 71.5M
zipformer trained in-domain on SPGISpeech, a different system class; and PRODUCT/EVENT/NORP/FAC
carry 45/73/21/11 mentions in our ten calls.

## What a model contact would still be needed for

- **All 44 Earnings-21 calls through `FlightRuntime`.** The only way to remove caveat 1 and quote a
  number directly against 9.71. ~39 h of audio, ~1,600 fixed 90-s windows per arm.
- **A self-run `whisper-large-v3` calibration anchor on our exact rows.** The literature report's
  option (b): run one well-specified reference system through the same chunking and the same
  `core.scoring_batch` scorer, and report the omni numbers relative to *that*. This removes the
  normalizer, aggregation, chunking, subset and quantization confounds in one move, and is the only
  route that makes a 3-point claim meaningful given caveat 2. It is not a frozen-core contact and
  needs its own registration.
- **ConEC's own sentence segmentation.** Comparing to ConEC Table 2 legitimately needs ConEC's
  segmentation and the Whisper-normalizer→fstalign stack; fstalign is not installed and installing
  it is out of scope for this read.
- **Earnings-22 short form.** The one same-model published target (Qwen3-Omni-30B-A3B-Instruct
  9.79, NVIDIA NeMo AutoModel; cross-read 12.3, Nemotron arXiv:2604.24954v2 Table 8) is on the
  2,741-utterance ESB test subset. `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-preregistration.md`
  drafts that cell; it is blocked on one owner decision because all six ESB test calls sit in this
  study's confirmatory split.

## Files

- `verified-score-batch-jobs.jsonl`, `verified-score-batch-summary.json`,
  `verified-score-batch-read.json` — the `core.scoring_batch` verified path.
- `rescore.json` (schema `saea-earnings21-scoring-alignment-v1`) — the registered-scorer path.
  This file is `rescore.py`'s output with every per-sample `ref_hit_mask` array dropped for size;
  nothing else changed. SHA-256 of the full, unmodified output:
  `906b399242b268fe45ad1258c59791e7989262e09b18ab75318921ed547bb41f`.
- `rescore.py` — the exact script that produced it.
- `MANIFEST.sha256` — SHA-256 of every file in this directory.
