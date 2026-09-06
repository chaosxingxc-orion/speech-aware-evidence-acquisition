# MF-7 — the SLURP retrieval-key audit (2026-09-06)

Prerequisite MF-7, owner GO 2026-09-06, amended the same day by the owner rule that **the
retrieval query must contain the speech signal**. Profile `model-free-check`; **zero frozen-core
contacts, zero GPU**. Exposure rows `SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V1` (the reads) and
`SAEA-SLURP-MF7-EMBEDDING-CPU-V1` (the CPU encoder passes), both registered before the first read.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-retrieval-key-audit/`.

Sections 1–4 and 6 of this note were written and committed **before the audit was run**; section 5
was appended afterwards. That ordering is the preregistration.

## 1. The question

Every SLURP retrieval cell so far has used the embedding of the frozen core's **own draft answer**
as the query, against the 11,514 TRAIN utterance texts as keys
(`rails.knowledge_provider.KbFacetProvider`, ranked by `saea-rank-wcos-prior-agree-v1`). KU-S1c
established that a second look at the same audio buys +0.30 pp intent, inside noise, and that
"contacts are not the lever on SLURP; constructed knowledge is". Before another consumption cell is
flown, the audit asks the prior question:

> **Which query signal, paired with TRAIN utterance texts as keys, retrieves neighbours that could
> CORRECT the closed-list baseline?**

Measured on DEV-1000, already consumed by the DEV ladder, so no new evaluation surface opens.
Reported on the unexposed NEW500 and the prior-exposed OLD500 separately, pooled 1,000 beside them.

## 2. What is a candidate and what is only a diagnostic

The owner rule of 2026-09-06 is binding and is encoded in the analysis module, not merely reported
by it (`analysis.slurp_retrieval_key_audit.DIAGNOSTIC_ONLY`, enforced in `decision()`):

| query set | contains speech | role | why |
|---|---|---|---|
| `q-draft` | no | **diagnostic only** | the lock's LEGACY signal; the query IS the model's own draft answer. Its point is the ECHO RATE — how much of the "retrieved evidence" is the model's own label coming back. |
| `q-gold-text` | no | **diagnostic only** | the query IS the gold sentence: the UPPER BOUND of any text key. Its point is to price the cross-modal loss and to say whether ANY text key is worth pursuing. |
| `q-speech-glap` | yes | candidate | DEV recordings through GLAP's audio encoder; keys = TRAIN texts through GLAP's text encoder. Run here, on CPU. |
| `q-speech-glap+state` | yes | candidate | the same speech query fused at RANK level with the agent's own intermediate state (the sealed draft's intent) under the registered ranker. Run here, on CPU. |
| `q-speech-lco`, `q-speech-lco+state` | yes | candidate | LCO-Embedding-Omni-3B. **Prepared, not run** (section 6). |
| `q-speech-nemotron`, `q-speech-nemotron+state` | yes | candidate | Omni-Embed-Nemotron-3B. **Prepared, not run** (section 6). |

Neither text-only set can win, however good its numbers are. A text-only query presupposes a
transcript the control plane does not have at retrieval time.

## 3. Protocol

**Keys.** The 11,514 TRAIN content facets of snapshot
`e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57` — one per TRAIN utterance, the
utterance text as the key representation — each carrying its TRAIN gold intent (`scenario_action`)
and its gold `{type, filler}` slots. TRAIN is construction data and is readable. For `q-draft` and
`q-gold-text` the key vectors are the **sealed** `vectors-content-facets.npz`
(sha256 `0bcb955a3a0ab84880f0d039ae702e77d1247ed23c3b8cecb468cbb1e0221c72`, re-verified before use,
zero new contacts). For a speech set the keys are re-embedded by that set's OWN model, because a
query may only be compared against keys embedded by the same encoder.

**Queries.** The DEV-1000 roster (split identity `9fb44e3384b8ad8e0d8f825b88eb0a3051c218b699975051d8a0481aabc0243b`),
1,000 rows, NEW500 the decision population. `q-draft` is the sealed KU-S1c **phase-1 draft response
text** per row (run `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1`, attempt
`attempt-20260906T042946Z-44720f`); the KU-S1 prep agent left only `facet-vectors.jsonl` under
`SPEECHRL_DATA_DIR/vectors/slurp-ku-s1/` — no `query-vectors.jsonl` and no query receipt — so the
draft texts were embedded here rather than reused. `q-gold-text` is the devel sentence text, read
**only** to compute embeddings under the audit row; it is written to no receipt, document, table
cell or log line. `q-speech-glap` is the recording waveform at 16 kHz.

**Baseline mask.** The per-row `scenario_action_exact` of the sealed closed-list direct baseline
`SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` (attempt `attempt-20260905T060424Z-2c5596`), official
`evaluate.py` scorer at pinned commit `8eb1654…311f1`.

**Neighbours.** Cosine top-k over the complete key set, k ∈ {1, 5, 10}, ties broken by ascending
facet id — the lock's own tie-break.

**Metrics** (per query set, per k, per population NEW500 / OLD500 / pooled, and per gold scenario):

1. **intent recall@k** — the gold intent appears among the k neighbours' TRAIN intents.
2. **vote accuracy@k** — the neighbours' MAJORITY intent equals gold, ties broken by best rank.
3. **corrective power** — among rows the sealed baseline got WRONG on intent, the share the
   majority would have SAVED; among rows it got RIGHT, the share it would have HARMED;
   net = saves − harms, in rows and in pp of the population.
4. **filler recall@k** — the share of the row's gold `{type, filler}` slots present verbatim among
   the neighbours' TRAIN slots. Both sides come through `data.slurp`'s official gold-side join
   (`" ".join(surface.lower())`), so "verbatim" is the official comparison with no second
   normalizer. Reported over the rows that HAVE at least one gold slot.
5. **echo rate** — the majority equals the sealed draft's own label. Reported for every set.

**The `+state` fusion.** Rank-level, under the registered ranker `saea-rank-wcos-prior-agree-v1`
with its registered weights and **no new knob**: `w_cos·max_cosine + w_prior·max_prior +
w_agree·agreement`, `w_cos = 0.5, w_prior = 0.3, w_agree = 0.2` read from
`configs/policy/kb-policy-v1.json`. The speech cosine is the content dimension; the PRIOR dimension
is the agent's own intermediate state — a key is recalled on it iff its TRAIN intent equals the
sealed draft's intent, mass 1.0 — and `agreement` is the lock's own fraction-of-recalled-dimensions
term. Two deliberate deviations from `rails.kb_policy`, both because this audits the KEY side
rather than replaying the locked cell: no per-dimension truncation before the union (an audit needs
a complete ranking), and the prior is the draft's intent rather than the snapshot's 60 TRAIN intent
priors.

**A closed-form property of that fusion, stated before the run.** A draft-agreeing key scores
`w_cos·c + w_prior + w_agree`; a disagreeing one scores `w_cos·c + w_agree/2`. The raw-cosine
advantage a disagreeing key needs is `(w_prior + w_agree/2)/w_cos = **0.8**`. Since SLURP cosines
live far inside that span, rank-level fusion at the registered weights is very close to a HARD
restriction to the draft's intent, and its vote is the draft's label whenever k such keys exist
(~190 TRAIN utterances per intent, so always). This is a property of the registered ranker, not a
choice made in the audit: `analysis.slurp_retrieval_key_audit.fusion_dominance_margin` computes it
and the receipt carries it. The prediction is therefore that `+state`'s echo rate is ~100 % and its
corrective power equals the draft label's own corrective power against the closed-list baseline.

**Statistics.** Stratified paired bootstrap, 10,000 replicates, seed 20260903, strata = gold
scenario, CI90, through this repository's single resampler `analysis.paired.paired_contrast` — the
same one every SLURP verdict uses. A single set's own level gets a CI by contrasting it against an
all-zero table, so there is exactly one bootstrap implementation in the repository.

## 4. The preregistered decision table (owner rule 2026-09-06, clause 3)

1. **KU-S1 flies with the speech-containing query set that has the highest net corrective power on
   NEW500.** The CI90 against the runner-up is reported. Ties go to the simpler signal: speech
   alone before speech+state, fewer models before more.
2. **If the best speech-containing set's net corrective power is below 2 pp of rows on NEW500,
   retrieval-by-neighbours on SLURP intent is CLOSED** and this note says so.
3. **The gap to `q-gold-text` is reported as the cross-modal loss.** `q-gold-text` also answers the
   separate question of whether ANY text key is worth pursuing: if even the gold-sentence query's
   net corrective power is under 2 pp, no text key can carry this mechanism.
4. **Filler recall@5 is reported for every set but does not gate.** It is the slot-side reading, and
   the slot side already has an admitted mechanism (KC-S1b's TRAIN slot schema, +8.55 SLU-F1).
5. `q-draft` and `q-gold-text` are never eligible to win, whatever their numbers.

No admission, promotion, superiority, generality or Stage-3 claim follows from this note. Its only
product is a gate on whether a KU-S1-prime retrieval cell is worth flying at all.

## 5. Results

*(appended after the run; see the receipt directory for the complete tables.)*

## 6. The GPU steps — prepared, not run

Mandatory follow-on, written so a fresh agent can run it verbatim after the current KC-A1 flight
releases the GPU. Register the row **before** the first contact:

> **`SAEA-SLURP-MF7-EMBEDDING-GPU-V1`** — tool-level speech/text encoders on the GPU; **0
> frozen-core contacts**. Two encoders over the same 1,000 DEV-1000 recordings and 11,514 TRAIN
> utterance texts MF-7 already used on CPU: (a) **LCO-Embedding-Omni-3B** (`models/lco-embedding-omni-3b-gguf`,
> `LCO-Embedding-Omni-3B-Q8_0.gguf` + `mmproj-LCO-Embedding-Omni-3b-F16.gguf`) through the pinned
> featcache `llama-server --embedding --pooling last`, audio delivered as base64 through the
> multimodal prompt shape; (b) **Omni-Embed-Nemotron-3B** (`models/omni-embed-nemotron-3b`) in bf16
> on CUDA, both modalities. Both write the SAME `saea-mf7-vectors-v1` JSONL schema as the CPU pass
> (`{"id": ..., "vector": [...]}`), so `scripts/run_slurp_retrieval_key_audit.py` re-runs unchanged
> with `--query-set`. Every forward pass is counted; no completion or chat endpoint is contacted;
> the SLURP `test` split is never named; no devel sentence text is written anywhere. Vectors land
> under `SPEECHRL_DATA_DIR/vectors/slurp-mf7/` and never enter Git.

### 6.1 Preconditions

* `nvidia-smi` shows no other resident server, or only one whose owner has released the card.
* **Check the power state first** (`nvidia-smi --query-gpu=enforced.power.limit --format=csv`): a
  35 W or 100 W cap means Legion SmartFanMode is throttling and the timings below are meaningless.
* `export PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=<repo>/src`, `SPEECHRL_DATA_DIR=…`, and **do not**
  `pip install` anything into the shared venv.
* Both `dev-rows.jsonl` and `train-facets.jsonl` already exist under
  `SPEECHRL_DATA_DIR/vectors/slurp-mf7/` — the GPU pass reuses them and must not regenerate them.

### 6.2 (a) LCO-Embedding-Omni-3B through llama-server

**The loader question, answered offline before any GPU time is spent.** The featcache build's
`/embedding` route is `server_routes::handle_embeddings_impl` in
`tools/server/server-context.cpp`, and it tokenizes with
`tokenize_input_prompts(ctx_server.vocab, ctx_server.mctx, prompt, true, true)` — it passes the
**mtmd context**. `tokenize_input_subprompt` in `tools/server/server-common.cpp` accepts

```json
{"content": {"prompt_string": "<__media__>", "multimodal_data": ["<base64 audio>"]}}
```

and routes it through `process_mtmd_prompt`, throwing `"Multimodal data provided, but model does
not support multimodal requests."` only when no mmproj is loaded. **So the embedding endpoint is
not text-only by construction: audio embeddings are reachable on this build provided the GGUF's
architecture loads and its mmproj declares an audio tower.** What is NOT yet proven offline is that
this build's `llama_model_load` accepts the LCO GGUF at all: the README says it was converted with
`ht-llama.cpp`, a *fork* that added `Qwen2_5OmniThinkerForConditionalGeneration`, and it advertises
`model_type: qwen2vl`. Run the loader probe below FIRST; if the server refuses the file, **drop LCO
and report the exact error** — do not patch or rebuild llama.cpp for it.

```bash
# LOADER PROBE — CPU, no GPU time, no embedding request. ~2 min, ~7 GB RAM.
CUDA_VISIBLE_DEVICES= /home/chao/llama.cpp-featcache/build/bin/llama-server \
  --host 127.0.0.1 --port 8093 \
  -m $SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf/LCO-Embedding-Omni-3B-Q8_0.gguf \
  --mmproj $SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf/mmproj-LCO-Embedding-Omni-3b-F16.gguf \
  --embedding --pooling last -ngl 0 -c 8192 -np 1 -t 6
# in another shell:
curl -s http://127.0.0.1:8093/props | head -c 400     # expect a model_path and a media marker
curl -s http://127.0.0.1:8093/embedding -H 'Content-Type: application/json' \
  -d '{"content": ["hello"]}' | head -c 200            # expect a 2048-dim vector
```

If both succeed, run the real pass on the GPU:

```bash
CUDA_VISIBLE_DEVICES=0 /home/chao/llama.cpp-featcache/build/bin/llama-server \
  --host 127.0.0.1 --port 8093 \
  -m $SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf/LCO-Embedding-Omni-3B-Q8_0.gguf \
  --mmproj $SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf/mmproj-LCO-Embedding-Omni-3b-F16.gguf \
  --embedding --pooling last -ngl 999 -c 8192 -b 8192 -ub 2048 -np 1 -fa on
```

**Memory envelope.** Q8_0 weights 3.45 GiB + F16 mmproj 2.44 GiB + KV at `-c 8192` ≈ 0.6 GiB +
CUDA context and compute buffers ≈ 1.5 GiB → **about 8 GiB of the 24,463 MiB card**, comfortable
beside nothing else. Do not raise `-c` above 8192: the audio tower's per-clip token count is small
(SLURP clips average 2.9 s) and a larger context only enlarges the KV allocation.

**Requests.** Text keys go through the plain shape the CPU pass already used
(`{"content": [<text>, …]}`, batch 16). Audio queries go one per request through the multimodal
shape, with the recording read as 16 kHz mono WAV bytes and base64-encoded:

```python
body = {"content": {"prompt_string": "<__media__>", "multimodal_data": [base64.b64encode(wav_bytes).decode()]}}
```

Write `lco-q-speech-query-vectors.jsonl` (1,000 rows, id = DEV sample id) and
`lco-key-vectors.jsonl` (11,514 rows, id = facet id), plus an `lco.receipt.json` in the same
`saea-mf7-vectors-receipt-v1` shape the CPU pass emitted: embedder block (gguf + mmproj sha256,
build commit `04ccc72a2207347ca76161b93fd9d846dd0a8675`, binary sha256, argv, `/props`), per-set
`{file, count, dims, sha256, bytes, l2_norms, wall_seconds, throughput}`, and an `accounting` block
with `frozen_core_contacts: 0`, `gpu_hours`, `embedding_tool_contacts`, `speech_audio_seconds`.

**Input-level `+state` for LCO** (owner rule clause 2b): a second query pass in which the audio and
the sealed draft text are ONE multimodal input —
`{"prompt_string": "<__media__>\n" + draft_text, "multimodal_data": [b64]}` — written as
`lco-fused-q-speech-query-vectors.jsonl`. Register it as its own query set; it is distinct from the
rank-level `+state` the audit script computes.

**Expected cost.** 12,514 forward passes; text keys dominate. At a 3B Q8 model on this card,
budget **20–35 minutes and well under 0.6 GPU-h**.

### 6.3 (b) Omni-Embed-Nemotron-3B on CUDA

**A blocker found offline, and its documented way round.** The model ships a
`sentence_bert_config.json` naming `sentence_transformers.base.modules.transformer.Transformer`
(sentence-transformers ≥ 5.4.0.dev0). **`import sentence_transformers` currently RAISES in the
shared venv**: it pulls `torchcodec`, which cannot load `libavutil.so.{58,59,60}` because **ffmpeg
is deliberately absent from this machine and must never be installed** (installing it would change
audio bytes and cold the 26 GB feature cache). The exact error is
`RuntimeError: Could not load libtorchcodec … OSError: libavutil.so.60: cannot open shared object
file`.

Therefore **do not use the sentence-transformers wrapper**. Load the model through plain
`transformers` and reproduce its three modules by hand — they are fully specified by the shipped
config and there is nothing to guess:

* module 0: `NVOmniEmbedModel` (`modeling_nv_omni_embed.py`, `trust_remote_code=True`) — a
  `Qwen2_5OmniThinkerForConditionalGeneration` whose text tower is made **bidirectional**
  (`is_causal = False` on every layer); take the last hidden state;
* module 1 (`1_Pooling/config.json`): **mean** pooling over the attention mask, `include_prompt:
  true`, 2048 dims;
* module 2: L2 normalise.

Inputs go through `Qwen2_5OmniProcessor` (`preprocessor_config.json`: `WhisperFeatureExtractor`,
128 mel bins, 16 kHz). The prompts from `config_sentence_transformers.json` are **`"query: "` for
the DEV speech queries and `"passage: "` for the TRAIN text keys** — use them, they are part of the
model's contract. Run bf16 on CUDA with `attn_implementation="sdpa"` (do not reach for flash-attn).
If `import sentence_transformers` is ever needed for something else, the only sanctioned
workaround is to make `torchcodec` unimportable for that process — never to install ffmpeg.

**Memory envelope.** 9.41 GB of safetensors in bf16 ≈ **9.5 GiB of weights**, plus activations for a
batch of 8 audio clips ≈ 2–3 GiB → **about 13 GiB of 24,463 MiB**. Comfortable alone; it will NOT
co-reside with a q4km 30B decoder, so this pass needs the card to itself.

Write `nemotron-q-speech-query-vectors.jsonl`, `nemotron-key-vectors.jsonl` and
`nemotron.receipt.json` in the same schema, plus the input-level fusion set
`nemotron-fused-q-speech-query-vectors.jsonl` (audio and the sealed draft text in ONE message, the
`message` modality of `sentence_bert_config.json`). **Expected cost: 15–30 minutes, under 0.5
GPU-h.**

### 6.4 Re-running the audit

No code change is needed. Drop the JSONL pairs into `SPEECHRL_DATA_DIR/vectors/slurp-mf7/` and:

```bash
python scripts/run_slurp_retrieval_key_audit.py --write \
  --query-set q-draft --query-set q-gold-text \
  --query-set q-speech-glap --query-set q-speech-glap+state \
  --query-set q-speech-lco --query-set q-speech-lco+state \
  --query-set q-speech-nemotron --query-set q-speech-nemotron+state
```

The catalogue in `scripts/run_slurp_retrieval_key_audit.py` already carries all eight names, their
file names, their encoders and their `contains_speech` / `fuses_state` flags. The decision table
re-applies itself over whatever sets are present.

### 6.5 The Qwen3-Omni option — priced, not run

The frozen core's own encoder is the one speech representation guaranteed to be in the same space
the answering model reasons in. Using it as a retrieval key would mean pooling the featcache
encoder features for **TRAIN packets**, and that is the whole cost:

* the 11,514 TRAIN utterances have **50,628 recordings**; a key per utterance needs one packet per
  chosen recording. Even at one recording per utterance that is 11,514 new speech packets against
  the 1,000 DEV packets that already exist;
* SLURP TRAIN audio for one recording per utterance is roughly **9.5 hours** (11,514 × ~2.97 s), and
  the September packet pipeline encodes at roughly 60× realtime on the mmproj path, so **about
  10 minutes of pure encoder time** — but the packets themselves are the cost: at the observed
  featcache packet size this adds **tens of GB** to the 26 GB cache, and the cache is hash-pinned;
* pooling is not defined for this path. The frozen core exposes no pooled sentence embedding; a
  mean over encoder frames is an **invented representation**, exactly the kind of self-invented
  metric the 2026-08-25 owner ruling told this study to stop producing while the agent layer is
  unconverged;
* and it needs the GPU for the whole build, in competition with real cells.

**Recommendation: do not run it.** If a later owner decision wants it, it should be its own
prerequisite with its own preregistration of the pooling definition, not a clause of MF-7.

## 7. Limits carried

* DEV-1000 is prior-exposed as a whole; NEW500 is the only unexposed half and is the decision
  population. Nothing here transfers to the held-out `test` split, which was never named or loaded.
* The audit measures what neighbours *contain*, not what a frozen core would *do* with them. A set
  that clears the gate has shown an upper bound on a voting consumer, not an admitted cell.
* Every number is offline arithmetic over sealed bytes plus tool-level encoders. No frozen-core
  contact was made, so nothing here revises any published arm's score.
