# slurp-asrbias-foldb-transcription-v1: contextually biased Qwen3-ASR transcription of TRAIN Fold B (CPU sidecar)

Date: 2026-10-19. Owner direction (translated): "consider proper-noun-enhanced ASR decoding to raise the model's
performance; can we optimise a model like Qwen3-ASR?" Background: umbrella-registry sections "Owner rulings 341 A and 342 A",
"339 part 1 merged", "ASR339 qualification READ" (Qwen3-ASR 1.7B: canonical WER 0.120, but only 65 of 112 missed slot
values contained against Whisper large-v3's 70; the hard values are names, places and times).

This package is an INSTRUMENT, a sibling of `slurp-asr339-foldb-transcription-v1` (the V0 pass). It measures how far a
decoding context moves the tool's transcripts and the gold-span, missed-slot and value-error containment. It is never a
delivery step, makes zero core contacts (port 8080 is never touched), uses no GPU, answers nothing, and no transcript enters
a decision, prompt or retrieval key (decision 201). **Status: prepared, NOT run.** Only the 4-row smoke in section 6 ran.

## 1. Parts

| part | path |
| --- | --- |
| variant fragments (registry `VARIANT_IDS`) | `configs/asr_bias/variant-<id>.json` |
| slot-type descriptions (V1 vocabulary, 54 TRAIN types) | `configs/asr_bias/slot-type-descriptions-v1.json` |
| instrument (`build-lexicon`, `transcribe --variant`, `score` delegate) | `scripts/analysis/asr339/foldb_bias_transcription.py` |
| launch spec | `docs/readiness/2026-10-19-slurp-asrbias-foldb-transcription-v1/launch-spec.json` |
| tests | `tests/unit/test_asrbias_instrument.py` |
| sidecar and scoring (reused unchanged) | `scripts/flights/direct/asr_sidecar.sh`, `scripts/analysis/asr339/foldb_transcription.py` |

## 2. How the context reaches the model

The pinned GGUF's chat template is plain ChatML (`<|im_start|>role\n content <|im_end|>\n`, then `<|im_start|>assistant\n`).
It renders a `system` message as its own turn, exactly where the Qwen3-ASR model card puts the context terms. Verified on
the live 1.7B sidecar with `POST /apply-template`: a `system` message renders as `<|im_start|>system\n<context><|im_end|>\n
<|im_start|>user\n<__media_...><|im_end|>\n<|im_start|>assistant\n`, whereas a text part beside the audio renders glued to the
media marker inside the user turn. The instrument therefore sends the context as the **system message** and keeps the user turn
audio-only (the V0 request shape). Smoke evidence that the context is live: V1 and V2-n100 change the transcript of 2 and 1 of
4 rows against V0, and the prompt token count rises by the context size plus 5 template tokens.

## 3. Variants

Every variant is a fragment resolving in the module registry; none reads the row's own gold. Seeds and temperature are in the
fragment and in the catalog (`decoding`, `decoding_sha256`, `variant_config_sha256`).

| id | context (system message) | decoding | notes |
| --- | --- | --- | --- |
| v0 | none | greedy, temperature 0 | sealed by ASR339; rerun here only in smoke for the identical request shape |
| v1 | slot TYPE names, one-line description each (54 types, identical for every row) | greedy | about 506 tokens |
| v2-n30 | intent-scoped value lexicon, 30 values | greedy | about 105 tokens |
| v2-n100 | intent-scoped value lexicon, 100 values | greedy | up to 317 tokens (fewer when the intent's types run out of values) |
| v3-n30 / v3-n100 | v2-n30 / v2-n100 plus `logit_bias` +2.0 on the first token of each lexicon value | greedy | 31-170 biased tokens per row |
| v4-none / v4-n100 | none / v2-n100 | 5 sampled decodes, temperature 0.6, seeds 11-15 | a two-pass ceiling, see below |

**Lexicon construction (V2, V3, V4-n100).** Per row: the committed intent is the intent of the NX-T R2b `budget-3072` Fold B
delivered column (the v3.0 lock form, the same column the ASR339 scorer uses; the system's own output, not gold) -> the intent's
slot types with `P(type present | intent) >= 0.02`, descending -> a round-robin over those types taking each type's next most
frequent value, de-duplicated, capped at N. Value frequencies come from the TRAIN slot fillers counted over TRAIN
utterances that **exclude every Fold A and Fold B utterance** (the same exclusion the 339 bound script applies to its type
prior; the build keeps 9,354 utterances, the size of the `tfrl-folds-v1` knowledge view). A row's own utterance is therefore
excluded by construction, so a value that occurs only in the row's own utterance cannot appear in its context (unit-tested on a
synthetic case, with a no-exclusion control); a frequent value that also occurs in other TRAIN utterances is legitimate
knowledge. A row with no committed intent gets no lexicon context (none in the current Fold B column).

**Context budget.** Hard cap `CONTEXT_TOKEN_BUDGET = 768` tokens, counted per row with the sidecar's own tokenizer
(`/tokenize`); lexicon values are dropped from the tail until the text fits (`lexicon_trimmed` is logged), and an oversize V1
refuses. Per-row `context_chars`, `context_tokens`, `lexicon_values`, `bias_tokens` and the server's `prompt_tokens` are in
every row; the catalog carries the max and mean.

**First-token bias (V3).** For each lexicon value the first token of the value and of the value with a leading space (the
mid-sentence form) gets `+2.0` through llama-server `logit_bias`, skipping stop-word and under-3-character first words and
capping at 400 tokens. The bias is global to the decode (the request cannot scope it to a span), so it is a small nudge.

**N-best union (V4).** Five sampled decodes per clip, the transcripts joined with ` <SEP> ` into `transcript` (so the
unchanged `score --containment` measures a union-containment ceiling) and kept separately in `nbest`. Its WER is not
interpretable (the concatenation is five transcripts long); read V4 for containment only.

## 4. Outputs and scoring

`$SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-ASRBIAS-TRANSCRIPTS-V1/<model-id>/<variant>/` holds `transcripts.jsonl` (schema
`saea-asrbias-transcript-row-v1`: the ASR339 row fields plus `variant`, `variant_config_sha256`, `context_chars`,
`context_tokens`, `lexicon_values`, `lexicon_trimmed`, `bias_tokens`, `intent_known`, and `nbest` for V4), `catalog.json`
(schema `saea-asrbias-transcript-catalog-v1`: the ASR339 catalog fields plus `variant`, `variant_config`,
`variant_config_sha256`, `lexicon_sha256`, `type_descriptions_sha256`, context-token statistics) and, after scoring,
`score.json` (schema `saea-asr339-foldb-score-v1`). Scoring is the unchanged ASR339 path, run once per variant directory.
Comparators: Whisper large-v3 canonical WER 0.152, all-gold containment 0.7606, missed-slot 0.625 (70/112), value-error
0.367 (61/166); the V0 1.7B row is the within-tool control (WER 0.120, 65/112). The full-pass lexicon build writes
`.../SAEA-SLURP-ASRBIAS-TRANSCRIPTS-V1/lexicon/lexicon-v1.json`; its aggregate `gold_value_in_lexicon_aggregate`
(scoring side) is an upper bound on what a perfect use of the lexicon could recover: 41.4 % (N=30) and 55.5 % (N=100) of
the 944 Fold B gold slot values sit in their own row's composed lexicon.

## 5. Procedure for the full pass (root only)

```bash
export SPEECHRL_DATA_DIR=/home/chao/saea-data/speechrl-data
P=$SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-ASRBIAS-TRANSCRIPTS-V1
~/.venvs/speechrl/bin/python -B scripts/analysis/asr339/foldb_bias_transcription.py build-lexicon --out $P/lexicon/lexicon-v1.json
bash scripts/flights/direct/asr_sidecar.sh start qwen3-asr-1.7b &            # live background wrapper
for V in v1 v2-n30 v2-n100 v3-n30 v3-n100 v4-none v4-n100; do
  python3 -B scripts/analysis/asr339/foldb_bias_transcription.py transcribe --model-id qwen3-asr-1.7b --variant $V --full \
      --out-root $P --lexicon $P/lexicon/lexicon-v1.json
done
bash scripts/flights/direct/asr_sidecar.sh stop qwen3-asr-1.7b
for V in v1 v2-n30 v2-n100 v3-n30 v3-n100 v4-none v4-n100; do
  ~/.venvs/speechrl/bin/python -B scripts/analysis/asr339/foldb_bias_transcription.py score --containment \
      --transcripts $P/qwen3-asr-1.7b/$V --out $P/qwen3-asr-1.7b/$V/score.json
done
```

`--full` refuses unless `docs/exposure-ledger.md` carries `SAEA-SLURP-ASRBIAS-FOLD-B-V1` exactly once, reading
`consumed = no` and `countersigned`. A variant directory is one-shot (an existing `transcripts.jsonl` is never overwritten);
`--smoke` is limited to 4 rows and to `diagnostics/ASRBIAS-SMOKE/`. The 0.6B model takes the same commands with
`--model-id qwen3-asr-0.6b` (about 0.45 x the time) once the 1.7B read justifies it. Run when no generation flight needs the
host's RAM (about 6 GiB for the 1.7B sidecar); the GPU is hidden from the sidecar.

## 6. Smoke (first 4 Fold B rows, 1.7B, CPU, one sidecar) -- counts only

Under `$SPEECHRL_DATA_DIR/diagnostics/ASRBIAS-SMOKE/`. 4 clips and 20 reference tokens: nothing here is an estimate of
quality; it proves the plumbing and that the context moves the output.

| variant | canonical WER (edits / 20) | context tokens per row | lexicon values per row | bias tokens per row | s per clip | rows changed vs v0 (of 4) | all-gold containment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v0 | 0.50 (10) | 0 | 0 | 0 | 0.97 | 0 | 0.75 |
| v1 | 0.40 (8) | 506 x4 | 0 | 0 | 1.52 | 2 | 1.00 |
| v2-n30 | 0.50 (10) | 98 / 104 / 106 / 106 | 30 x4 | 0 | 1.35 | 0 | 0.75 |
| v2-n100 | 0.45 (9) | 317 / 211 / 294 / 294 | 100 / 66 / 100 / 100 | 0 | 2.04 | 1 | 0.75 |
| v3-n30 | 0.50 (10) | 98 / 104 / 106 / 106 | 30 x4 | 54 / 31 / 51 / 51 | 1.08 | 0 | 0.75 |
| v3-n100 | 0.45 (9) | 317 / 211 / 294 / 294 | 100 / 66 / 100 / 100 | 170 / 65 / 128 / 126 | 1.91 | 1 | 0.75 |
| v4-none | not interpretable (5 concatenated decodes) | 0 | 0 | 0 | 3.20 | 4 (concatenation; first decode 0) | 0.75 |
| v4-n100 | not interpretable | 317 / 211 / 294 / 294 | 100 / 66 / 100 / 100 | 0 | 3.28 | 4 (first decode 1) | 0.75 |

Every row status was `ok`; the V0 WER reproduces the ASR339 smoke (0.50). A bias of +2.0 on first tokens changed no row beyond
its V2 twin in this sample. 0.6B: V0 and V2-n100 ran (0.41 and 0.91 s per clip; 2 of 4 rows changed). `score --containment`
ran unchanged on every variant directory.

## 7. Cost estimate (CPU, from the smoke; allow +-30 %)

1.7B, 1,080 clips (3,155 audio seconds per decode), one variant at a time: v1 about 27 min, v2-n30 about 24, v2-n100 about 37,
v3-n30 about 24, v3-n100 about 36, v4-none about 58, v4-n100 about 59: **about 265 min (4.4 h) wall, 17,280 ASR calls**
(6 single-decode variants x 1,080 + 2 v4 variants x 5,400). The 0.6B model needs about 0.45 x that (about 2 h). Peak memory
about 5.2 GiB (1.7B) and 2.6 GiB (0.6B); CPU only, no GPU, no core call. Pipeline note: a second sidecar on another port could
run the 0.6B column in parallel when the host has about 8 GiB free.

## 8. Prepared exposure-ledger row (NOT appended; the root appends and countersigns it)

```
SAEA-SLURP-ASRBIAS-FOLD-B-V1 | 2026-10-19 | bounded-discovery-probe | TOOL CONTACT, instrument pass | split role discovery
(TRAIN Fold B, split identity hash 4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a, 1,080 rows) |
0 core calls; 17,280 ASR calls (1,080 clips x 7 biasing variants on qwen3-asr-1.7b: v1, v2-n30, v2-n100, v3-n30, v3-n100 greedy;
v4-none and v4-n100 five sampled decodes each; pinned build 04ccc72a2, CPU sidecar port 8190, bf16 GGUF + bf16 mmproj per the
umbrella lock) | 3,155 speech-audio seconds per decode |
purpose: contextual-biasing qualification of the open Qwen3-ASR 1.7B (type vocabulary, intent-scoped TRAIN value lexicon
excluding Fold A and Fold B utterances, first-token logit bias, n-best union) against the sealed V0 and Whisper large-v3
(WER, gold-span, missed-slot and value-error containment); the context carries no gold of the row, only the committed v3.0
intent and TRAIN-fold knowledge; transcripts never enter a decision, prompt or retrieval key (decision 201) |
one-shot per variant, no automatic retry | consumed = no | countersignature: pending (the root replaces this phrase with
"countersigned <timestamp> by <who>" before the pass)
```
