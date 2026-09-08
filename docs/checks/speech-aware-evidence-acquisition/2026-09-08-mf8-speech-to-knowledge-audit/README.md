# MF-8 — the speech-to-knowledge audit (2026-09-08)

Row id `SAEA-SLURP-MF8-SPEECH-TO-KNOWLEDGE-AUDIT-V1`, profile `model-free-check`.
**Zero model, GPU, tool, embedding, network and audio-decode contacts. Zero paid spend.**
Note: `docs/readiness/2026-09-08-mf8-speech-to-knowledge-audit-v1.md`.
Generator: `scripts/mf8_speech_to_knowledge_audit.py` (subcommands `speakers`, `comparator`,
`feasibility`, `judge`, `state`, `family`).

## Headline

| question | answer |
|---|---|
| 1. speaker structure | 135 of 137 devel speakers also record in TRAIN; **999 of 1,000** DEV-1000 rows have their own speaker in TRAIN with 338 recordings at the median. Same-speaker same-intent exemplars: **12 recordings / 6 sentences at the median**, **943** rows at ≥ 1, **734** at ≥ 5, **57** at zero |
| 2. where the comparator fails | 269 errors, **64.68 %** cross-scenario, **159** distinct confusion pairs, largest 13 rows. Candidate source (a) the comparator's own top-k **does not exist** (no logprobs were ever stored); (b) the predicted scenario's legal list caps at **35.32 %** on errors by construction; (c) the pinned Nemotron speech vectors put the gold in the top-3 distinct intents on **72.86 %** of failures and (b)+(c) at k = 8 on **86.62 %** |
| 2.5 legality judge | flags **42 of 1,000** rows at **100.00 %** precision and **zero** false flags; **25** remain wrong after projection v2 |
| 3. multi-audio feasibility | **YES on both routes.** The packet route already binds one `query` plus N `key` packets per request; the raw mmproj route consumes one bitmap per media marker. k = 3 / 5 / 8 add **126 / 211 / 337** tokens and the worst-case row at k = 8 uses **4,291 of 8,192** slot tokens |
| 4. state inventory | SLURP carries **no dialogue, session, turn, history or timestamp field** — prior-turn context does not exist. Standing state is the 60-pair closed list (already in the prompt) and 4,157 TRAIN fillers, of which **2,776 over 35 types** are standing-state types (`device_type` 75, `house_place` 38) |
| 5. priced family | KU-S4a/b/c, 1 core call per row, ≈ 0.115 GPU-h and ≈ 16,633 metered speech seconds per audio arm. Same-speaker coverage of candidates **92–93 %**, but the fully-covered stratum clears the n ≥ 400 rule **only at k = 3** (426 NEW500 rows against 388 at k = 5 and 341 at k = 8) |

## Identity anchors, fail-closed

The `comparator` read raises rather than reports if any of these stops reproducing from the sealed
bytes, and all four held:

* comparator intent **73.10** pooled / **71.00** OLD500 / **75.20** NEW500
  (`slurp-slu-official-projected-v2`);
* MF-7b `intent_recall_at_k` at k = 5 on NEW500: **83.20** (`q-speech-nemotron`) and **87.40**
  (`q-speech-nemotron-fused`), recomputed from the sealed Nemotron floats.

## Files

| file | content |
|---|---|
| `speaker-structure.json` | question 1, including the per-row table (1,000 rows) |
| `comparator-failure.json` | question 2, including the per-row prediction table |
| `legality-judge.json` | the deterministic legality judge's tiers, precision and reach |
| `multi-audio-feasibility.json` | question 3's cost arithmetic and geometry fit |
| `state-inventory.json` | question 4's field census and TRAIN entity inventory |
| `cell-family-price.json` | question 5's constructibility and coverage per k |

## Boundary

The held-out `test` split was never named, loaded, hashed or scored. **No devel sentence text was
read**: the DEV side is gold intent labels (availability counts and error attribution only) plus a
key-name census that counts field names and never a value. TRAIN gold text was read as knowledge
inventory. Audio was touched only as container headers — no waveform was decoded, no server was
started, no model or tokenizer was loaded, and `CUDA_VISIBLE_DEVICES` was empty throughout. The
Nemotron vectors are the sealed floats of `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1`, read and never
recomputed.

**Nothing here is admitted, promoted or preregistered**, and no superiority, generalization or
Stage-3 claim follows from it.
