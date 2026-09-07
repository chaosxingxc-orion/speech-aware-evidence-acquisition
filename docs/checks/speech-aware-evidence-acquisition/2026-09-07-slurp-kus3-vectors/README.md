# KU-S3 sealed vectors — receipt (2026-09-07)

Exposure row `SAEA-SLURP-KU-S3-VECTORS-V1`, profile `model-free-check`. Generator
`scripts/build_slurp_kus3_vectors.py`. Preregistration
`docs/readiness/2026-09-07-slurp-consumption-ku-s3-v1-preregistration.md`, section 4.

**Zero frozen-core contacts, zero tool contacts, zero embedding contacts, zero GPU hours, zero
network, zero paid spend.** No new embedding pass happened and none may: every float here is a
byte-for-byte copy of a float the registered pass `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1` produced
on 2026-09-06, and each source file was re-hashed against that pass's own receipt before a line of
it was read.

## What this converts, and why a conversion is needed

`rails.phase_supply.load_sealed_vectors` reads a JSONL whose every line is
`{"id": ..., "vectors": {"<dimension>": [...]}}` and refuses any other shape. The MF-7b audit wrote
`{"id": ..., "vector": [...]}`, because its own consumer is dimension-free. Same floats, same order,
same ids; one key renamed and one nesting level added. Every written file was then read back through
the flight's own loader at **max abs delta 0.0**.

| file (`$SPEECHRL_DATA_DIR/vectors/slurp-kus3/`) | role | rows × dims | source set |
|---|---|---|---|
| `facet-vectors.jsonl` | key | 11,514 × 2048 | `nemotron-train-text` |
| `query-vectors-speech.jsonl` | query, key (a) | 1,000 × 2048 | `q-speech-nemotron` |
| `query-vectors-speech-state.jsonl` | query, key (b) | 1,000 × 2048 | `q-speech-nemotron-fused` |
| `query-vectors-speech-twin.jsonl` | query, the form twin | 1,000 × 2048 | `q-speech-nemotron`, deranged |

The key ids are `facet:content:<slurp_id>` — already, exactly, the content facet ids
`rails.knowledge_build` mints — which is why cell KU-S3 needs no new knowledge provider.

## The twin

`saea-kus3-within-predicted-scenario-derangement-v1`. Rows are bucketed by the scenario their
**sealed closed-list response names** — the prediction, never gold, and the same information the
phase's own state fill already conditions on — and inside each bucket the sorted sample ids are
rotated by one. Measured: 24 buckets, **0 rows receive their own vector**, 3 of 1,000 cross a bucket
(the singleton buckets `movies`, `sport`, `sports`, pooled and rotated among themselves).

## Boundary

The held-out test split was never named, loaded or hashed. No devel sentence text and no gold label
was read. The bytes live under `SPEECHRL_DATA_DIR` and never enter Git; `vectors.json` carries their
sha256s, row counts, dimensions, L2-norm statistics and the read-back deltas.
