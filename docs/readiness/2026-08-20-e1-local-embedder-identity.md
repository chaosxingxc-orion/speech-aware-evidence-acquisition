# E-1 — local embedder feasibility + identity check (durable record)

Date: 2026-08-20. Status: **CLOSED — engineering verification, zero corpus contact** (one
synthetic 2 s sine WAV + one synthetic sentence; no dataset audio, no gold, no generation).
Context: the owner's local-first directive ("try the local omni model before the external
survey concludes") and the embedder-charter adjudication
(`2026-08-20-embedder-charter-adjudication.md`), whose P-EMB-3M design cites this report.
This document lands the agent-delivered E-1 findings as the repository record; it
SUPERSEDES the stack assumptions in `2026-08-20-omni-embedding-selection.md` §candidates
where they conflict (the ticket assumed LCO needs a new isolated `sentence-transformers`
venv — Mission B below refutes that: the local GGUF runs on the pinned llama.cpp).

## Mission A — local candidate identity verdicts

All under `$SPEECHRL_DATA_DIR/models/`. Lock provenance: five of six are
`LOCAL_CANDIDATE`/`UNRESOLVED_LOCAL_SOURCE`; only `omni-embed-nemotron-3b` has a resolved
pinned source (modelscope `nv-community/omni-embed-nemotron-3b`).

| Model | What it is | Speech-CONTENT semantics? | Stack | Dim | Verdict |
|---|---|---|---|---|---|
| glap | CLAP-style contrastive, speech+music+sound, label-caption trained | Weak (audio-type/label level) | transformers (trust_remote_code) | 1024 | **CONTROL-ONLY** |
| clsp | Zipformer2↔text contrastive on FCaps speaking-STYLE captions | No (paralinguistic style space) | transformers (custom) | 512 | **CONTROL-ONLY** (style-confound control) |
| meralion-speech-encoder-2 | BEST-RQ SSL audio encoder, no text tower | N/A — no joint space; zero-shot matching impossible training-free | transformers | 1024 | **UNFIT** |
| omni-embed-nemotron-3b | Qwen2.5-Omni-3B Thinker bi-encoder (NV-Retriever lineage); audio-content retrieval MEASURED (NDCG@10 0.82 LPM / 0.54 FineVideo) | **Yes, measured** | transformers pinned branch `v4.51.3-Qwen2.5-Omni-preview`; NOT llama.cpp | 2048 | **ARM-VIABLE** (strongest evidenced fit; NVIDIA OneWay NC + Qwen Research licenses) |
| lco-embedding-omni-3b-gguf | Same backbone family, LoRA+contrastive, last-token pooling; MIEB-benchmarked (general multimodal, not speech-specific) | Plausible/inherited — NOT independently speech-content benchmarked (open verification item) | **GGUF on the pinned llama.cpp** (Mission B) | 2048 | **ARM-VIABLE, PRIMARY** (only pinned-stack-native candidate; Apache-2.0) |
| lco-embedding-omni-7b-gguf | 7B sibling, MIEB-Lite SOTA | same caveat | GGUF via llama.cpp mtmd | 3584 | ARM-VIABLE (escalation option) |

## Mission B — LCO-3B GGUF on the pinned llama.cpp: WORKS (verified)

- Files: `LCO-Embedding-Omni-3B-Q8_0.gguf` (3.6 GB) + `mmproj-LCO-Embedding-Omni-3b-F16.gguf`
  (2.6 GB, required for audio). Pinned build `llama.cpp-featcache` @ `5d9dfcb` (upstream base
  `fdbd6abee` + 4 featcache-only patches); QWEN2VL arch + `qwen2.5o` whisper-style audio
  projector + the `multimodal_data`/`prompt_string` server schema are genuine mainline
  support, not fork additions.
- Text embedding dim 2048, bit-deterministic on repeat (CPU run). Audio embedding dim 2048
  (same space), bit-deterministic (CPU run); first audio call ~50 s CPU (whisper encoder pads
  to ~30 s chunk), warm repeat ~4.8 s. Verification ran `-ngl 0 --no-mmproj-offload`
  (GPU was campaign-occupied); GPU runs use `-ngl 999`.
- Upstream caveat logged by the server: `init_audio: audio input is in experimental stage
  and may have reduced quality` — residual quality risk, not a blocker.
- **Media-marker gotcha (reuse-critical)**: the LCO card's `"prompt_string": "<__media__>"`
  example is stale; upstream randomizes the marker per boot. Pin `LLAMA_MEDIA_MARKER` at
  launch or read `GET /props → media_marker`.
- Launch recipe (verified): `LLAMA_MEDIA_MARKER='<__media__>' llama-server -m <Q8_0> --mmproj
  <F16> --embedding --pooling last -ngl 999 -c 4096`; text `POST /embeddings
  {"content":"..."}`; audio `POST /embeddings {"content":[{"prompt_string":"<marker>",
  "multimodal_data":["<base64 wav>"]}]}`.

## Mission C — cascade arm (text embedder) resolution

Ollama-internal Qwen3-Embedding blobs exist locally but stay untouched (extraction
prohibited). Resolution: umbrella acquisition `qwen3-embedding-0.6b-gguf` (umbrella commit
`0d4865b`, HF `Qwen/Qwen3-Embedding-0.6B-GGUF` rev `370f27d`, Q8_0, sha256
`06507c7b…3439`). Sanity embed on the pinned build (`--embedding --pooling last`): dim 1024,
L2-norm ≈ 1.0; **GPU calls are NOT bit-exact across identical inputs** (cosine 0.999910,
max |Δ| 1.4e-3 — known llama.cpp CUDA batched-inference jitter). Any read suite comparing
its vectors must declare this tolerance; argmax-cosine verdicts are unaffected at this
magnitude.

## Consequences for P-EMB-3M

Primary arm LCO-3B via the Mission-B recipe; GLAP/CLSP as CONTROL-ONLY arms (they test
whether an audio-TYPE/STYLE space can fake content routing); nemotron optional escalation
(transformers pinned branch, NC license carried); cascade arm = core T0 self-transcription →
qwen3-embedding-0.6b text-text matching. Integration must pass the structural encode-only
machine check required by the adjudication. LCO's speech-content fit is UNVERIFIED — that is
exactly what P-EMB-3M measures, so no adoption claim precedes it.
