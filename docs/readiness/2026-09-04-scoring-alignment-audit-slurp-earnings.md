# Scoring alignment audit: Earnings-21 and SLURP against the published brackets (2026-09-04)

Zero-contact. No model call, no GPU, no llama-server, no tool or embedding contact, no network, no
audio decode, no test split, no installs. Every number below is a pure function of already-sealed
outputs bytes plus a frozen reference layer, produced by the registered scorers this repository
already owns.

Exposure rows: `SAEA-E21-MF-SCORING-ALIGNMENT-V1`, `SAEA-SLURP-MF-SCORING-ALIGNMENT-V1`
(`docs/exposure-ledger.md`, both registered before any scorer touched a reference).
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-04-scoring-alignment-earnings/`
and `.../2026-09-04-scoring-alignment-slurp/`.

## The rule being applied

Owner directive, 2026-09-04: *aligned* = within 3 points of the official/published number;
*better by more than 3* is also acceptable; and a hard floor — the frozen Qwen3-Omni Q4_K_M must
never score below what a degraded (smaller / older / more quantized) model is published to reach on
the same dataset. A literature sweep the same day established that **no Qwen-published number exists
for SLURP, Earnings-21, Earnings-22 or ConEC**, so every target below is a third-party cross-system
comparison, never a reproduction.

## Headline

1. **Earnings-21 aligns, comfortably, under the field-standard metric.** Corpus-level WER with the
   Whisper `EnglishTextNormalizer` on both sides is **7.14 %** for the bare frozen core on the ten
   sealed discovery calls, against `whisper-large-v3`'s published **9.71** — a 2.57-point margin on
   the good side of the 3-point band — and every degraded-model floor (Whisper medium.en 10.2,
   small.en 10.8, base.en 12.5, tiny.en 17.0, FastConformer 13.84, Qwen2-Audio-7B 26.06) is cleared.
   The number is on 10 of 44 calls and excludes the corpus's known pathological file; it is not yet
   a like-for-like row.
2. **The ConEC-names WER gain does not survive the field-standard normalizer.** Under frozen
   `saea-scoring-v1` the names arm is the best arm (10.28 vs 12.03 corpus); under the Whisper
   normalizer it is the worst (7.46 vs 7.14). The mechanism is deletions: 933 to 1,451, concentrated
   in two calls. Entity recall still improves strongly under both metrics. Any future ConEC-supply
   claim on WER must name its normalizer.
3. **SLURP does not align, and cannot.** No published prompt-only SLU-F1 computed with the official
   `evaluate.py` exists for any audio LLM, so there is no like-for-like target at any protocol. The
   locked BLEND cell clears the weakest published *intent* pipeline (75.70 vs Google/SF-ID 72.06)
   and fails the weakest published *SLU-F1* pipeline by 22 points (41.69 vs 64.02). The bare core
   (M0) fails both. Every published row is a system trained on SLURP.
4. **Two scoring-path defects found on sealed artifacts, reported and not patched** (section 3):
   the Earnings manifests cannot emit the two new scorers through the verified path, and the August
   SLURP flights have no run manifest and the wrong row key.

## 1. Carrier: Earnings-21 (plus the two ConEC arms)

Output set: `SAEA-E-005B-N10-{zero,matched,names}`, attempts `...044ccc` / `...30cb33` / `...30d1a1`,
the frozen ten calls of `r4-e21-sub10` (split identity `744c4b2e...8a61`, study commit `c28e3a4`),
8.446 h, 342 fixed 90-second windows per arm, no VAD trim, no overlap. Identity anchors: the
recomputed `asr-wer` mean equals the sealed `scores.json` value to 0.0 for all three arms, and the
recomputed `entity-wer` corpus value equals the prior sealed offline read exactly.

| output set | metric (definition, normalizer, aggregation) | ours | published target (system, split, source) | delta | degraded-model floor | verdict |
|---|---|---|---|---|---|---|
| zero (`bare-core`) | WER, Whisper `EnglishTextNormalizer` both sides, **corpus** | **7.137** | `openai/whisper-large-v3` 9.71 (Earnings-21, all 44, ASR Leaderboard long-form CSV) | −2.57 | Whisper medium.en 10.2 | **aligned**; floor cleared |
| zero | same | 7.137 | Whisper large-v2 9.7 (Whisper paper App. D.4, all 44) | −2.56 | small.en 10.8 | **aligned**; cleared |
| zero | same | 7.137 | TRADE speech-LLM 9.75 (arXiv:2606.08486 Table 2) | −2.61 | base.en 12.5 | **aligned**; cleared |
| zero | same | 7.137 | FastConformer FT+LCA+GT 13.84 (same table) | −6.70 | tiny.en 17.0 | **aligned-better**; cleared |
| zero | same | 7.137 | Qwen2-Audio-7B 26.06 (FinAudio; **normalizer unnamed**) | −18.92 | — | not comparable as a target; cleared as a floor |
| matched (`conec-contexts`) | same | 7.241 | whisper-large-v3 9.71 | −2.47 | all four Whisper floors | **aligned**; cleared |
| names (`conec-names`) | same | 7.460 | whisper-large-v3 9.71 | −2.25 | all four Whisper floors | **aligned**; cleared |
| zero / matched / names | WER, Whisper norm, **mean of per-call** | 7.281 / 7.374 / 7.819 | no published row uses this aggregation | — | — | reported for completeness only |
| zero / matched / names | WER, frozen `saea-scoring-v1`, **corpus** | 12.025 / 12.000 / 10.278 | — | — | — | **not comparable**: different metric family |
| zero / matched / names | WER, frozen `saea-scoring-v1`, **mean of per-call** | 12.385 / 12.394 / 10.879 | — | — | — | the sealed 2026-08-15 verdict's own numbers |

Reference words: 77,148 under `saea-scoring-v1`, 75,751 under the Whisper normalizer (which strips
the fillers `hmm|mm|mhm|mmm|uh|um`, bracketed and parenthesised spans, and standardizes numerals,
currency and contractions on both sides). The `saea-scoring-v1` corpus figures happen to fall within
3 points of 9.71 as well; that is a coincidence between two unrelated normalizers and must never be
reported as an alignment.

### 1.1 The normalizer-dependent sign flip

| arm | `saea-scoring-v1` corpus | Whisper-norm corpus | Whisper-norm S / D / I |
|---|---|---|---|
| zero | 12.025 | 7.137 | 2396 / 933 / 2077 |
| matched | 12.000 | 7.241 | 2272 / 1168 / 2045 |
| names | 10.278 | 7.460 | 2265 / 1451 / 1935 |

The names roster trades substitutions and insertions for deletions. Per call, the Whisper-normalized
deletion counts move 58 to 222 on 4385072, 41 to 226 on 4389907, 221 to 293 on 4366429 and 41 to 87
on 4387383. The Whisper normalizer collapses most of the substitution and insertion differences the
in-house metric credits — numerals, contractions, fillers — and leaves the deletions standing. The
2026-08-15 N10 verdict's headline (names best by 1.50 macro points, p = .027) is a
`saea-scoring-v1` statement and does not transfer to the published metric family.

### 1.2 Entity WER

`entity-wer` is **mention-level `1 − recall`** over the `.nlp` `wer_tags` sidecar: a gold mention
counts correct only when every one of its normalized token positions is an exact `align()` hit, so
its precision is 1.0 by construction and only the recall-derived error rate carries information.
Aggregation is a **corpus-level count ratio** (as fstalign does) but over **mentions**, not over
entity-tagged reference tokens; the normalizer that precedes it is the frozen `normalize_text_v1`,
not the Whisper normalizer. fstalign was not installed and not run.

| output set | metric | ours | ConEC Table 2 target | delta | ConEC floor (row 1) | verdict |
|---|---|---|---|---|---|---|
| zero / matched / names | entity WER, all 24 classes, corpus, 8,284 mentions | 32.01 / 29.10 / 19.95 | no published row in this family | — | — | descriptive |
| zero / matched / names | entity WER, ConEC's 8 non-numeric classes, 1,612 mentions | 26.92 / 21.46 / 21.65 | ConEC prints no pooled non-numeric column | — | — | descriptive |
| matched | PERSON | 17.4 | 28.9 (row 8, Whisper large, no ctx) | −11.5 | 45.9 (ceiling 13.0) | **aligned-better**; floor cleared |
| matched | ORG | 23.0 | 19.6 | +3.4 | 29.5 (ceiling 17.7) | not aligned; floor cleared |
| names | GPE | 18.6 | 17.0 | +1.6 | 18.8 (ceiling 12.9) | **aligned**; floor cleared |
| matched / names | LOC | 2.7 | 5.85 | −3.15 | 5.85 (ceiling 5.46) | **aligned-better**; floor cleared |
| names | PRODUCT | 28.9 | 18.7 | +10.2 | 24.2 (ceiling 19.2) | not aligned; **floor failed** |
| names | EVENT | 31.5 | 2.78 | +28.7 | 43.1 (ceiling 35.6) | not aligned; floor cleared |
| zero / names | NORP | 19.0 | 8.54 | +10.5 | 9.55 (ceiling 5.53) | not aligned; **floor failed** |
| names | FAC | 63.6 | 21.6 | +42.0 | 28.7 (ceiling 16.6) | not aligned; **floor failed** |

Per-arm non-numeric class table (entity WER %, mention-level):

| arm | PERSON | ORG | GPE | LOC | PRODUCT | EVENT | NORP | FAC |
|---|---|---|---|---|---|---|---|---|
| zero | 22.6 | 29.3 | 24.0 | 5.4 | 62.2 | 42.5 | 19.0 | 72.7 |
| matched | 17.4 | 23.0 | 18.9 | 2.7 | 37.8 | 45.2 | 23.8 | 72.7 |
| names | 18.1 | 25.8 | 18.6 | 2.7 | 28.9 | 31.5 | 19.0 | 63.6 |
| gold mentions in our ten calls | 447 | 608 | 333 | 74 | 45 | 73 | 21 | 11 |

Mandatory caveats. **Segment-level vs long-form**: ConEC segments Earnings-21 at sentence boundaries
and Whisper large scores 7.98 there against 10.3 on whole files, so roughly 2.3 points of any
overall-WER gap is segmentation, not system. **fstalign not run here**: ConEC's stack is Whisper
normalizer then fstalign with Rev's synonym and reference-normalization files; ours is
`normalize_text_v1` then a mention-level recall. **System class**: ConEC rows 1–5 are a 71.5M
zipformer trained in-domain on SPGISpeech; only row 8 (Whisper large) is comparable in kind to a
frozen general model. **Support**: PRODUCT, EVENT, NORP and FAC carry 45, 73, 21 and 11 gold
mentions in these ten calls, so those four verdicts are directional at best.

### 1.3 Subset caveat, stated plainly

Ten calls — 4330115, 4365024, 4365948, 4366429, 4366522, 4384964, 4385072, 4387383, 4389907,
4397829 — 30,406.93 s = **8.446 h**, 21.5 % of the corpus's 39 h 15 min; per-call 30.3 to 74.6 min.
Every published row is on all 44 files, including `4346923`, the 16 kHz Industrial Goods call the
Earnings-21 paper singles out as degrading every system. That file is **not** in our ten. Whisper's
own long-form decoding heuristics move Earnings-21 by 1.1 points (10.7 greedy to 9.63 with
previous-text conditioning, Whisper Table 7), so a ±3-point band around 9.7 is only about three
times the reference literature's own protocol spread.

### 1.4 What a model contact would still be needed for (Earnings)

- **All 44 Earnings-21 calls through `core.flight.FlightRuntime`** (about 39 h of audio, about 1,600
  fixed 90-second windows per arm). The only way to remove the subset caveat and quote a number
  directly against 9.71.
- **A self-run `whisper-large-v3` calibration anchor on our exact rows**, through the same chunking
  and the same `core.scoring_batch` scorer. This is the only route that makes a 3-point claim
  meaningful at all, because it removes the normalizer, aggregation, chunking, subset and
  quantization confounds together — the same move the Audio2Tool carrier already made against
  arXiv:2604.22821 Table 3. It is not a frozen-core contact and needs its own registration.
- **ConEC's own sentence segmentation plus the Whisper-normalizer to fstalign stack**, for a
  like-for-like ConEC Table 2 row. fstalign is not installed and installing it was out of scope.
- **Earnings-22 short form** against the one same-model published target
  (Qwen3-Omni-30B-A3B-Instruct 9.79 zero-shot on the 2,741-utterance ESB test subset, NVIDIA NeMo
  AutoModel; cross-read 12.3 on the leaderboard English subset, Nemotron arXiv:2604.24954v2
  Table 8 — the two vendor reports of the same frozen model disagree by 2.5 points, most of the
  owner's tolerance). Drafted in
  `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-preregistration.md`; blocked on one
  owner decision because all six ESB test calls sit in this study's confirmatory split.

## 2. Carrier: SLURP

Output sets: sealed `SAEA-DEV1000-BASELINE-LOCK` arms M0 (`attempt-20260825T053342Z-dev1000m0`) and
BLEND (`attempt-20260825T054707Z-dev1000blend`), and sealed `SAEA-DEV500-CONFIRMATORY` arms M0,
BLEND, RANDRET and RANDICL. Scorer: the registered `slurp-slu-official`, which runs the real,
unmodified official `scripts/evaluation/evaluate.py` at pinned commit `8eb1654...311f1` in
`~/.venvs/slurp-official-eval` (never modified) with `--average micro --errors --table-layout csv`,
and additionally asserts numeric identity against this study's per-sample port. **All six arms
passed that identity check** (max absolute difference 1.1e-16). `split_id="devel"`,
`allow_heldout=False`: the held-out test split was never named, loaded or scored.

| output set | metric (official `evaluate.py`, micro) | n gold / n predicted / skipped | ours | published target (system, split, source) | delta | degraded-model floor | verdict |
|---|---|---|---|---|---|---|---|
| DEV-1000 BLEND | intent (scen_act) accuracy % | 1000 / 1000 / 0 | **75.70** | Gold/HerMiT 84.84 (gold transcripts, test, SLURP Table 7) | −9.14 | — | not aligned (below) |
| DEV-1000 BLEND | same | 1000 / 1000 / 0 | 75.70 | Multi-SLURP/HerMiT 78.33 (strong ASR to NLU pipeline, test, Table 7) | −2.63 | — | **aligned** |
| DEV-1000 BLEND | same | 1000 / 1000 / 0 | 75.70 | Google/SF-ID 72.06 (weak commercial pipeline, test, Table 7) | +3.64 | Google/SF-ID 72.06 | **aligned-better**; floor cleared |
| DEV-1000 BLEND | same | 1000 / 1000 / 0 | 75.70 | ChatGPT on oracle transcripts, 0-shot 79.25 (He & Garner arXiv:2305.13512, prompt-only, 60 intents) | −3.55 | — | not aligned (below, by 0.55) |
| DEV-1000 BLEND | same | 1000 / 1000 / 0 | 75.70 | ChatGPT on Whisper ASR, 10-shot 72.89 (same) | +2.81 | — | **aligned** |
| DEV-1000 M0 | same | 1000 / 1000 / 0 | **53.60** | Google/SF-ID 72.06 (weakest published pipeline) | −18.46 | Google/SF-ID 72.06 | not aligned; **floor failed** |
| DEV-1000 M0 | same | 1000 / 1000 / 0 | 53.60 | Multi-SLURP/HerMiT 78.33 | −24.73 | — | not aligned (below) |
| DEV-1000 BLEND | **SLU-F1** % | 1000 / 1000 / 0 | **41.69** | Multi-SLURP/HerMiT 70.84 (best in the original paper, test, Table 8) | −29.15 | Google/SF-ID 64.02 | not aligned; **floor failed** |
| DEV-1000 M0 | SLU-F1 % | 1000 / 1000 / 0 | **36.90** | Multi-SLURP/HerMiT 70.84 | −33.94 | Google/SF-ID 64.02 | not aligned; **floor failed** |
| DEV-1000 BLEND | SLU-F1 % vs the only prompt-only published slot number | 1000 / 1000 / 0 | 41.69 | ChatGPT slot-filling F1 12.03–13.35 (He & Garner, 10/20/30-shot) | +28.3 to +29.7 | — | **aligned-better**, but a different F1 definition (see caveat 1) |
| DEV-1000 BLEND | scenario accuracy % | 1000 / 1000 / 0 | 83.90 | Gold/HerMiT 90.15 | −6.25 | Google/SF-ID 78.87 | not aligned; floor cleared |
| DEV-1000 BLEND | action accuracy % | 1000 / 1000 / 0 | 77.60 | Gold/HerMiT 86.99 | −9.39 | Google/SF-ID 74.31 | not aligned; floor cleared |

Full official table, all six sealed arms (percent, micro; for the single-label blocks micro
P = R = F1 = accuracy):

| arm | roster | n gold | n predicted | skipped | unparsed | scenario | action | **intent (scen_act)** | entities (strict) | Word-F1 | Char-F1 | **SLU-F1** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DEV-1000 M0 (direct) | DEV-1000 | 1000 | 1000 | 0 | 5 | 70.00 | 61.50 | **53.60** | 21.94 | 34.66 | 39.46 | **36.90** |
| DEV-1000 BLEND (locked cell) | DEV-1000 | 1000 | 1000 | 0 | 2 | 83.90 | 77.60 | **75.70** | 27.27 | 39.41 | 44.24 | **41.69** |
| DEV-500 M0 (direct) | DEV-500 | 500 | 500 | 0 | 3 | 68.20 | 61.40 | **51.80** | 19.16 | 33.25 | 38.18 | **35.54** |
| DEV-500 BLEND | DEV-500 | 500 | 500 | 0 | 0 | 81.00 | 74.20 | **71.80** | 22.64 | 36.82 | 41.65 | **39.09** |
| DEV-500 RANDRET (negative control) | DEV-500-NEW400 | 400 | 400 | 0 | 1 | 71.25 | 62.75 | **56.50** | 18.58 | 33.62 | 38.50 | **35.89** |
| DEV-500 RANDICL (negative control) | DEV-500-NEW400 | 400 | 400 | 0 | 3 | 64.50 | 56.00 | **47.00** | 23.10 | 35.06 | 40.55 | **37.60** |

**N-predicted.** No arm has a gold roster row without a prediction, so the number with unanswered
rows counted as wrong equals the official number in every row. That had to be checked rather than
assumed: `evaluate.py` pairs with `if gold_id in pred_examples:`, so an unanswered gold row never
touches TP/FP/FN. The receipt demonstrates the hazard on this repository's own data — the same 1,000
DEV-1000 M0 predictions scored against the whole 8,690-recording devel gold set print exactly the
roster-scoped numbers (70.00 / 61.50 / 53.60 / SLU-F1 36.90) while 7,690 gold rows go unscored and
unpenalised. The two 400-row control arms were separately verified to be exactly the
`DEV-500-NEW400` sub-roster, not 500-row arms with 100 refusals.

**Microphone channel.** SLURP encodes the channel in the filename: `audio-<epoch>-headset.flac` is
the close-range headset take, `audio-<epoch>.flac` the far-field mic-array take of the same sentence.
Devel is 4,173 headset / 4,517 far-field; DEV-1000 is 478 / 522, DEV-500 is 236 / 264,
DEV-500-NEW400 is 194 / 206 — all within half a point of the natural devel proportion, so no roster
is a headset-only easier subset. Per-channel intent accuracy shows far-field is 1.1 to 5.0 points
*better* on five of six arms (DEV-1000 M0: headset 51.05 vs far-field 55.94), i.e. these errors are
label choice, not acoustics. **Zero SLURP-synt rows** can enter by construction:
`data.slurp._AUDIO_SUBDIR_FOR_SPLIT` maps `devel` to `slurp_real` only.

**Identity anchor.** The 2026-08-25 lock read recorded pooled DEV-1000 correctness
(`scenario_action_exact`) M0 0.536 / BLEND 0.757 through the per-sample port. The official
`evaluate.py` intent (scen_act) column reproduces both exactly (53.60 / 75.70), so the official
scorer and this study's own correctness definition agree on this carrier with no adjustment.

### 2.1 Caveats that must travel with the SLURP tables

1. **There is no like-for-like target.** No published prompt-only SLU-F1 computed with the official
   script exists for any audio LLM, Qwen or otherwise; every verified SLU-F1 comes from a model
   trained or tuned on SLURP. He & Garner's 12.03–13.35 is a slot-filling F1 over 60 intents on
   oracle transcripts, not this script's `SLUF1` block (word- plus char-distance confusion matrices
   summed), so the +28-point reading means "prompt-only slot filling is the known collapse point and
   this system is well above the one published prompt-only number", not a matched metric.
2. **Devel vs test.** Every published row is the official test split (2,974 sentences / 13,078
   recordings). Ours are devel rosters. The SLURP paper's own Table 5 puts the devel/test ASR gap at
   0.1–0.5 points, so the splits are close, but they are not the same split.
3. **Roster shape.** DEV-1000, DEV-500 and DEV-500-NEW400 are scenario-stratified near-equal-per-
   scenario stress rosters (TVD 0.22–0.24 from the natural TRAIN mixture, recorded in
   `docs/checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-slurp/`), not
   call-volume-weighted samples. The published tables are natural mixture.
4. **Label space.** The SLURP paper never states an intent count; downstream work reports 60, 65 or
   69. This study scores free-form `{scenario, action}` strings against gold strings with no closed
   label list offered to the model — strictly harder than a 60-way classification prompt and far
   harder than AIR-Bench's 4-way MCQ (Qwen2.5-Omni 75.5, which is not this metric and is not
   comparable).
5. **BLEND is the mechanism, not a baseline.** BLEND is the locked knowledge cell (retrieval plus
   alpha-blend over a TRAIN-mined knowledge plane). The bare frozen core is M0. A floor claim about
   "our frozen Q4_K_M" should be read against M0.
6. **Known inconsistencies in the SLURP paper itself** (reported, not fixed): the introduction says
   55 entity types and Table 4 says 56; the split totals sum to 72,396 audio files against Table 2's
   72,277 and 16,521 sentences against Table 3's 17,181.

### 2.2 What a model contact would still be needed for (SLURP)

- **The official test split.** A prompt-only SLU-F1 on the 13,078-recording official test split,
  computed with this exact script, does not exist anywhere in the literature. Producing it would be
  the first of its kind and is the only way to make any SLURP number here directly comparable to
  Tables 7 and 8. It requires a preregistered confirmatory read (`allow_heldout=True`), which this
  repository's split discipline forbids without one.
- **A natural-mixture devel read**, before any single "SLURP devel" number is quoted beside a
  natural-mixture published row.
- **A closed-label-list arm**, to match He & Garner's 60-way classification protocol.

## 3. Two defects found on the sealed artifacts (reported, not patched)

1. **Earnings: the verified path cannot emit the new scorers.** The three sealed manifests declare
   `"scorers": ["asr-wer", "cost"]`, and `core.scorers.score_bundle` runs exactly the manifest's own
   list. `core.scoring_batch` therefore reproduces the sealed `asr-wer` numbers (all three jobs
   returned `"verified": true`, mean WER identical to the sealed value) but **cannot** produce
   `asr-wer-whisper` or `entity-wer` for these bundles; editing a sealed manifest to add them would
   break its hash binding. The two new metrics were therefore produced by resolving the **same
   registered scorer objects** directly against the sealed `outputs.jsonl` — the pattern
   `analysis.entity_wer_offline` already established for the deferred entity read — gated by two
   identity anchors. A durable fix belongs in the manifest scorer list of future Earnings runs, not
   in a rewrite of a sealed artifact.
2. **SLURP: no run manifest, and the wrong row key.** The August SLURP flights predate the canonical
   `core.flight.FlightRuntime.seal` contract. Their attempt directories carry `flight-state.json`,
   `arm*-outputs.jsonl`, `execution-plan.json` and trace artifacts but **no `*.run-manifest.json`**,
   so `core.scoring_batch` (which refuses any job whose manifest is not a `*.run-manifest.json`) is
   inapplicable to this carrier's sealed August artifacts; and those rows carry
   `final_response_text` where every registered scorer reads `text`. The re-score therefore wrote a
   1:1 **key-rename projection** of the sealed bytes (`{"sample_id": unchanged, "text": the sealed
   final_response_text verbatim}`), recorded the SHA-256 of both source and projection, and scored
   the projection. No response text was altered and no row added or dropped. A durable fix is to
   seal future SLURP flights through `FlightRuntime.seal`, which already writes the canonical rows.

## 4. Bottom line for the owner

- **Earnings-21: aligned under the published metric, on a 10-of-44 subset.** 7.14 % against 9.71,
  every degraded floor cleared. The next move that would make this a defensible claim is not more
  mechanism work but a calibration anchor: run `whisper-large-v3` through our own chunking and our
  own scorer on our own rows. Given that Whisper's decoding heuristics alone move this dataset by
  1.1 points, and that two vendors report the same frozen Qwen3-Omni on Earnings-22 as 9.79 and
  12.3, the 3-point tolerance is smaller than the reference literature's own protocol noise.
- **ConEC entity supply is real but metric-fragile.** Entity recall improves 32.01 to 19.95 corpus
  entity WER with the names roster, and PERSON/GPE/LOC beat or match ConEC's Whisper-large
  no-context row; but the WER gain that headline rests on disappears under the Whisper normalizer,
  and PRODUCT/NORP/FAC sit below ConEC's own no-biasing floor.
- **SLURP has no alignment target, and that is the finding.** The gap in the literature — no
  prompt-only official-script SLU-F1 for any audio LLM — is an opportunity for this study, not a
  measurement failure. What the sealed numbers do say: intent classification survives prompting
  (BLEND 75.70 clears the weakest published trained pipeline), slot filling does not (SLU-F1 41.69
  against a 64.02 floor) — the exact asymmetry He & Garner found for a text cascade, and the exact
  asymmetry an evidence-acquisition control plane exists to attack.

---

## Addendum, 2026-09-05 — the Earnings-21 subset caveat is discharged

Section 1.3's subset caveat and section 1.4's first bullet are both closed, and section 3's defect 1
is durably fixed. `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (attempt `attempt-20260904T233816Z-bcd338`,
study commit `44db2e9d`) flew **all 44 discovery calls** — 39.263 h, 1,593 fixed 90-second windows —
under the sealed arm's own protocol on build `04ccc72a` with the bf16 mmproj resident on the GPU, and
declared `asr-wer-whisper`, `asr-wer`, `entity-wer` and `cost` **in the manifest**, so the
paper-facing number now comes out of `core.scoring_batch`'s verified path instead of the out-of-band
read this audit had to use.

**Corpus WER under the Whisper `EnglishTextNormalizer`, all 44 calls: 8.200 %** against
`openai/whisper-large-v3`'s 9.71 — **ALIGNED** (band ≤ 12.71 pass; strict Whisper medium.en floor
≤ 10.2 pass; every other floor cleared; ALIGNED-BETTER < 6.71 not reached).

Three things this audit could not know, now measured:

1. **`4346923` costs 0.312 points.** The 43 calls without it score 7.888; its own WER is 18.94 %, the
   worst of the 44. The caveat was right that it matters, and it is now inside the number.
2. **The 7.137 → 8.200 gap is the corpus, not the build.** The same ten calls re-measured on the new
   build and the new audio path score **7.185** (+0.048), while the other 34 score **8.470**. The
   August number was right about what it measured; what it measured was the easier half.
3. **Entity WER over all 44** is 30.36 % corpus over 38,366 gold mentions (the ten gave 32.01 % over
   8,284). The per-class table is in the verdict.

Section 3's defect 1 is fixed for future Earnings runs exactly as this audit recommended — in the
manifest scorer list, not by rewriting a sealed artifact. One new defect surfaced on the way and is
recorded there too: call `4320211` references an entity id its `wer_tags` sidecar never lists (one id
of 38,377 across the 44 calls), which refused all four scorers on the sealed manifest until
`data.references` learned to label an absent annotation `__UNTYPED__` and count it. The regression
anchor holds to the digit: this audit's own published `SAEA-E-005B-N10-zero` entity numbers —
32.01 % over 8,284 mentions — reproduce unchanged after that repair.

Section 1.4's remaining bullets stand unchanged, and its **whisper-large-v3 calibration anchor on our
own rows** is now the obvious next move: it is the only route that removes the normalizer,
aggregation, chunking, decoding-heuristic and quantization confounds together.

Verdict: `docs/readiness/2026-09-04-e21-full44-direct-baseline-v1-verdict.md`. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-e21-full44-direct-baseline-v1/`.


## Addendum, 2026-09-05 (second) — the Earnings-22 short-form cell flew, and it does not align

Section 1.4 named "Earnings-22 short form against the one same-model published target" as the
measurement that would still need a model contact. It was preregistered
(`docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-preregistration.md`) on the dated owner
allowance of 2026-09-04 that permits one read of the six ESB test calls, and flown as
`SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1` on 2026-09-05: all 2,735 published ESB test utterances, cut
locally from the six locked MP3s at the published boundaries, one utterance per contact, raw audio
through the resident bf16 mmproj, greedy, build `04ccc72a`.

**NOT ALIGNED. 15.937 % corpus WER under the Whisper `EnglishTextNormalizer` against
Qwen3-Omni-30B-A3B-Instruct's own published 9.79** (+6.15) and its cross-read 12.3 (+3.64). The
band test, the strict `whisper-large-v3` floor (11.59) and even the loose `whisper-base.en` floor
(15.09) all fail; of the nine published floors on that column only `whisper-tiny.en`'s 19.12 is
cleared.

This is the first **same-model** comparison this study has been able to make on any carrier, and it
sharpens what this audit's headline 1 can be read to mean. Earnings-21's 8.200 % over all 44
discovery calls stands and is still ALIGNED — but it is a **cross-system** comparison, on
**long-form** 90-second windows, against a **verbatim** `.nlp` reference layer. Point the same
frozen core, the same build and the byte-identical instruction at short sentence-length clips scored
against a **cleaned** reference and the number moves by nearly eight points. Neither result
contradicts the other; together they say that this study's Earnings numbers are far more sensitive
to segmentation and reference convention than to the model.

The gap decomposes, and not toward recognition. Insertions are 59.2 % of all errors; the hypothesis
runs 1.0749x the reference in length, longer on 1,556 of 2,735 rows and shorter on 317; and an
**oracle** cut of each hypothesis to its own reference word count — a diagnostic upper bound, never
an achievable result and never fitted — moves the figure 5.48 points to 10.456, which would sit
inside the band and under the strict floor. Collapsing repeated words buys at most 0.33 points and
makes the number worse when applied to the hypothesis alone; dropping every utterance under 3 s buys
1.22. The leading suspects are the prompt (deliberately held byte-identical to the Earnings-21
flight's, and therefore asking for verbatim disfluent output against a reference that is not
verbatim) and the segmentation (one sentence-length clip, no context, no way to know where it ends;
the length ratio rises monotonically from 1.039 at 16-40 s to 1.147 at 2-4 s). Quantization is
untested by this flight and remains the live suspect for the residual 0.67 points.

Section 1.4's other two open items are unchanged and are now more clearly the priority: a self-run
`whisper-large-v3` anchor over these exact rows through this exact scorer would turn 11.59 from a
published row into a measured one and remove the normalizer, aggregation, chunking and subset
confounds together; and ConEC's own sentence segmentation plus the fstalign stack is still not
installed. Full verdict:
`docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-verdict.md`; numbers under
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-e22-esb-shortform-alignment-400-v1/verdict/`.

---

## Addendum, 2026-09-05 — SLURP caveat 4 is wrong, and section 2.2's closed-label-list arm has flown

Two corrections and one result. Verdict:
`docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md`; receipts under
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-closed-list-direct-baseline-v1/`
and `.../2026-09-05-slurp-closed-list-headroom/`.

**Correction 1 — caveat 4 is factually wrong about the flown arm.** It states that this study
"scores free-form `{scenario, action}` strings against gold strings with no closed label list
offered to the model". A closed list *was* offered. `_INSTRUCTION` is only half the system
message: `rails/runner.py::_agent_messages` appends `"\n\nTask contract:\n"` plus
`SlurpAdapter.build_task_contract`, which is `render_slurp_ontology(load_slurp_ontology(...))`.
All 1,000 sealed DEV-1000 M0 `MODEL_REQUEST` records carry one identical 5,747-character
instruction (sha256 `cef52789…86b8`) enumerating **18 scenarios, 46 actions and 55 entity types**
with 263 example fillers. What it never carried is the **pairing**: two flat lists imply
18 x 46 = 828 intents where only **60** `(scenario, action)` pairs occur in train, and
`SlurpOntology` had no field able to hold them. The audit's conclusion that the protocol was
harder than the literature's still stands; its stated reason does not.

**Correction 2 — the gap was measurable on the audit's own sealed bytes.** Model-free row
`SAEA-SLURP-MF-CLOSED-LIST-HEADROOM-V1`, zero contacts, no gold: **32.20 %** of M0's sealed
predictions name a `(scenario, action)` pair that does not occur in train, against 8.60 %
naming an unlisted scenario, 6.90 % an unlisted action and 0.28 % an unlisted entity type. The
three lists the prompt did carry were respected; the one it did not carry held 69 % of M0's
46.4-point intent error. BLEND's figure is 2.10 %.

**Section 2.2's missing arm has now flown** (`SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`): the
sealed M0 prompt plus a pure 1,836-character suffix naming the 60 legal pairs, the 55 entity
types and the closed-choice constraint, everything else identical — same 1,000 rows at the same
identity hash, same packets, same build, same `-np 8 -c 65536`, same greedy `max_tokens 64`, one
contact per sample.

| arm | scenario | action | **intent** | entities strict | Word-F1 | Char-F1 | **SLU-F1** |
|---|---|---|---|---|---|---|---|
| **closed-list direct** | 81.00 | 73.90 | **71.40** | 21.91 | 33.69 | 38.20 | **35.80** |
| DEV-1000 M0 | 70.00 | 61.50 | 53.60 | 21.94 | 34.66 | 39.46 | 36.90 |
| DEV-1000 BLEND | 83.90 | 77.60 | 75.70 | 27.27 | 39.41 | 44.24 | 41.69 |

Three things follow for this audit's own conclusions.

1. **The asymmetry is confirmed and is now measured on an aligned baseline.** Intent +17.80 pp
   paired (CI90 [+15.70, +19.90]; +17.60 on the unexposed 500), SLU-F1 −1.10. Intent
   classification survives prompting; slot filling does not. Intent 71.40 is **aligned** with
   Google/SF-ID 72.06 (−0.66) and with ChatGPT-on-Whisper-ASR 72.89 (−1.49); SLU-F1 35.80 still
   **fails the 64.02 degraded-model floor** by 28.22. Scenario 81.00 clears the 78.87 floor;
   action 73.90 misses the 74.31 floor by 0.41.
2. **"BLEND clears the weakest published trained pipeline" needs re-scoping.** BLEND's +22.10 pp
   intent margin was measured against M0. Against the protocol-aligned arm it is **+4.30 pp**
   pooled, and **+2.60 pp with a 90 % CI of [−0.20, +5.60]** on the rows unexposed at the lock
   tier. 80.5 % of the locked knowledge cell's SLURP intent gain is reproducible from 1,836
   characters of prompt, with no retrieval and no second contact. The 2026-08-25 lock statistic
   itself is unchanged; what it *means* is not.
3. **Defect 2 is discharged for this carrier.** This was the first SLURP cell flown through
   `core.flight.FlightRuntime`. Its seal wrote a real `*.run-manifest.json` with canonical rows
   keyed `text`, and `core.scoring_batch` ran all three declared scorers over the complete
   manifest in one process. Only the two sealed August arms still needed the key-rename
   projection; the sealed M0 and BLEND columns above reproduce this audit's numbers exactly, to
   the second decimal, on all seven metrics.

Section 2.2's other two open items are unchanged: the official test split remains untouched, and
a natural-mixture devel read is still owed before any single "SLURP devel" number is quoted
beside a natural-mixture published row.

## Addendum, 2026-09-07 — Earnings-22 short form aligns once the serving path stops gluing an unmasked constant to the last word

The 2026-09-05 addendum above recorded the Earnings-22 short-form cell as **NOT ALIGNED at corpus
Whisper-normalized WER 15.937**, with the miss shaped as output discipline: insertions were 59.2 %
of all errors and the hypothesis ran 1.0749 times the reference's length. That diagnosis is now
resolved, on the six ESB test calls themselves, by a factor the study had never varied — the audio
the protocol delivers.

`SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1` (attempt `attempt-20260907T110507Z-cafdc7`, 2,735 of 2,735
contacts) re-read the same population with exactly 2.0 s of digital silence appended to each clip
and everything else byte-identical to the sealed arm. **Corpus Whisper-normalized WER 9.2377 %**,
against the published 9.79 and the cross-read 12.3: the band test (`<= 12.79`) and the strict floor
(`<= 11.59`) both pass, every one of the nine degraded-model floors is cleared including
`qwen3-asr-1.7b` at 9.73, and the verdict is **ALIGNED**. Paired against the sealed arm on the same
segments the delta is **−6.6988** points, CI90 [−7.0373, −6.3753] stratified by call, with 1,385 rows
improved against 155 worsened. The insertion share falls 59.16 % → 27.62 %, the length ratio 1.0749 →
0.9999, the boundary category mass 7.1465 → 1.0916 WER points, and the tail insertion block collapses
from 3,068 inserted words to 91 while the head block barely moves.

**The number carries a protocol difference and is not a like-for-like reproduction.** Deviation
`D-TS2-3`: the published systems did not append silence. What the tail addresses is a defect of THIS
study's serving path that the published path does not have — `mtmd_audio_preprocessor_qwen3a` glues
up to 0.99 s of unmasked, non-silent `0.0` constant to the end of a clip and charges 13 audio tokens
for it, where the HF `Qwen3OmniMoeProcessor` masks that block away — so the honest reading is that
the tail moves our input processing closer *in effect* to the published path's, not that it
reproduces it. The full rule, the licensed sentence and the limits are in
`docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-verdict.md`.

**Earnings-22 test is closed.** The 2026-09-04 owner allowance permitted one read of these six calls
and the 2026-09-07 owner GO permitted a second; both are spent. No third read is proposed, the 109
remaining confirmatory calls and the ESB validation split are untouched, and any further Earnings-22
work moves to dev or stops.
