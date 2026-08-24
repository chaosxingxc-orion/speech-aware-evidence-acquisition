# KB text-embedding pass — SAEA-SN-TOOL-KB-TEXT-EMB-PASS

Date: 2026-08-23 (executed 2026-08-24T03:38:50Z). Status: **COMPLETED, one shot.**
Exposure row: `SAEA-SN-TOOL-KB-TEXT-EMB-PASS` (`docs/exposure-ledger.md`).
Authority: docs/readiness/2026-08-23-dev100-campaign-preregistration.md section 5.1 (prep prerequisite 1); owner rulings 2026-08-23-knowledge-plane-baseline-rulings.md section 7 revised sequence.

Prep prerequisite #1 of the DEV-100 iterative optimization campaign: embed the KB-BUILD
`size-full` TRAIN snapshot's text material with the pinned tool-level embedder, land vectors
plus manifests, and leave the resident decoder completely untouched.

## What was embedded

| family | source field | count | dims | file | sha256 |
|---|---|---|---|---|---|
| content facets | `KeyFacet.representation` where `dimension == "content"` | 11,514 | 1024 | `vectors-content-facets.npz` | `0bcb955a3a0ab84880f0d039ae702e77d1247ed23c3b8cecb468cbb1e0221c72` |
| values | `ValueBundle.content` | 11,514 | 1024 | `vectors-values.npz` | `daa20244843af46a69afa6f76a46de231356c48785ff0cceed83cbc37a4b3ad3` |

Not embedded: the 349 `label` / `prior` / `speaker`
facets — label / prior / speaker facets are recalled by prior mass and exact-key agreement, never by vector similarity (DEV-100 preregistration section 5.1).

Both `.npz` files and `embeddings-manifest.json` (sha256 `69f6fbc4f47152cc2b4ae316350a69ce22075c30f3d03f3d0bb50a4abe34391b`)
live under `$SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/size-full/` and never
enter Git; `docs/receipts/knowledge/slurp-kb-size-full-embeddings.json` carries their hashes.

Each `.npz` holds three aligned arrays: `vectors` (float32, N×1024), `ids`, and
`text_sha256` (SHA-256 over the exact UTF-8 text embedded into that row), so a consumer can
re-verify the pairing without re-reading the 40 MB snapshot.

## Identity

- Snapshot `slurp-kb-distmodel-76e61b0666162aa7`, content hash
  `e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57` — re-verified in-process before any contact
  (file sha256 `f1cb8e024aa239298c4c2fe19fa9a026a891136fcff4b45b88061043121475fc`).
- Embedder: `qwen3-embedding-0.6b-gguf` (umbrella lock revision `370f27d7550e0def9b39c1f16d3fbaa13aa67728`),
  `models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf` sha256 `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`, dim 1024.
- Server: receipt-pinned `llama.cpp-featcache/build/bin/llama-server` sha256 `d0b42ace8d8e02dc772a0e4a1e1667068b3ad799b1ca4c98c741cf89d58404f2`
  (build `04ccc72a2207347ca76161b93fd9d846dd0a8675`), argv:
  `--host 127.0.0.1 --port 8082 -m /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf --embedding --pooling last -ngl 0 -c 4096 -b 4096 -ub 4096 -np 1 -t 16`.
- Server props: `{"build_info": "b8-04ccc72a2", "model_path": "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf", "total_slots": 1}`.

## Gates

- **Encode-only structural check**: PASS. Guards 1+2
  (import / endpoint-string) swept the pinned module set
  ['speech_aware_evidence_acquisition.rails.embedding_client', 'speech_aware_evidence_acquisition.rails.local_encoder_client', 'speech_aware_evidence_acquisition.rails.probes.pemb3m_flight', 'speech_aware_evidence_acquisition.rails.probes.pemb4r_flight'] **and this pass's own runner source**
  before the server was spawned; guard 3 (client surface) ran on the live
  `EmbeddingClient`; guard 4 (payload keys) ran on all
  23,030 request payloads on the real wire path, not merely
  the first.
- **Resident decoder untouched**: verdict `true`. PID
  607 stayed continuously resident on port 8080; its server log
  measured 1,117,739 bytes / sha256
  `177b972d81bcf02cf26dbcacfc8cd9f6ca81b1ae695395022923da1faa557e02` **byte-identical and hash-identical** before and
  after. The embedder ran CPU-only (`-ngl 0`) in its own session on port
  8082 with its own log, and was stopped by receipt-bound pid, never a
  pattern-matched kill.
- **Jitter pair**: the same text embedded at session start and at session end —
  cosine 1.000000000000, bit-identical `true`. E-1 Mission C measured GPU-side
  non-bit-exactness (cosine 0.999910) for this exact model; CPU-served, the repeat is
  bit-exact, so no tolerance needs to be declared for these vectors.
- **Consumer-side verification** (model-free, `runner/verify_vectors.py`): all 18 checks pass —
  both `.npz` re-hash to the manifest, shapes are (11,514 × 1024) float32, every value is
  finite, ids are unique and in exact snapshot order, every `text_sha256[i]` re-derives from
  the snapshot's own text, no zero-norm rows, and the `facet_vectors` callable
  `rails.kb_policy` expects builds from the file and returns `{}` for a label facet.

## Accounting

23,030 pinned-TOOL embedding contacts (registered ceiling
25,000), **0** frozen-core contacts, **0** metered audio seconds,
**0.0** GPU-h (-ngl 0: nothing offloaded; the pass is CPU-only). Wall time
31.1 min end to end, spawn+load
10.1 s, 12.42 texts/s
over the two embedding blocks (content facets 8.1 min,
values 22.8 min).

## Storage semantics

vectors are stored EXACTLY as the pinned llama.cpp server returned them. That server L2-normalizes pooled embeddings by default, which the measured l2_norms confirm; this pass adds no normalization of its own, so a consumer that wants a different normalization applies it at the point of use. text_sha256[i] is SHA-256 over the UTF-8 bytes of the exact text embedded into row i, so a consumer can re-verify the pairing without the snapshot.

Measured L2 norms: content facets
[1.000000, 1.000000], values
[1.000000, 1.000000].

## Consumption caution

The content-facet vectors are the K-side 'content' dimension the saea-kb-alpha-blend-v1 policy's multidim recall consumes (rails.kb_policy takes facet_vectors as facet_id -> {dimension: vector}). The VALUE vectors are produced because the DEV-100 preregistration section 5.1 names both text families, but the owner's Q-K-V ruling (2026-08-23-knowledge-plane-baseline-rulings.md section 1.3) states that V is consumed, never embedded as key material. Value vectors must therefore NOT be used as recall keys without an explicit owner decision; they are available for evidence-side work (deduplication, supply-side reranking, diagnostics) only.

## Frame

Artifact-producing prep pass (DEV-100 prep prerequisite 1). No accuracy, promotion, admission, or superiority claim follows from this receipt; its only product is the KB-side vector material the DEV-100 campaign's alpha-blend policy consumes. Vectors and the manifest live on the data root and never enter Git; this receipt carries their hashes.

## Files here

- `runner/` — the exact scripts that produced this record (runner, env, syntax check,
  preflight, one-shot launcher, consumer-side verifier, receipt/README/ledger builders).
