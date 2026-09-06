# MF-7b — SLURP retrieval-key audit, GPU part (2026-09-06)

Receipts for the omni-embedding half of the SLURP retrieval-key audit. Verdict and protocol:
`docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2.md`. Preregistration, committed before the
first contact: `docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2-preregistration.md`.

**Verdict in one line: the gate is not cleared, neighbour retrieval on SLURP intent is CLOSED, and
the reason is not the encoder — Omni-Embed-Nemotron reaches recall@5 87.40 against the transcript
ceiling's 93.80, but its vote (75.80) only ties the re-locked comparator (75.20).**

Exposure rows, all three registered in `docs/exposure-ledger.md` before the first contact:

* `SAEA-SLURP-MF7B-LCO-EMBEDDING-V1` — LCO-Embedding-Omni-3B on the pinned featcache
  `llama-server --embedding --pooling last`, GPU; 13,575 tool contacts, 0.2565 GPU-h,
  **0 frozen-core**.
* `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1` — Omni-Embed-Nemotron-3B in bf16 on CUDA through plain
  `transformers`; 13,575 tool contacts plus a 7-contact loader dry run, 0.1101 GPU-h,
  **0 frozen-core**.
* `SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2` — the model-free read; **zero model, GPU, tool, embedding,
  network and audio contacts**.

## Files

| file | what it carries |
|---|---|
| `summary.json` | the whole audit over the 11,514 TRAIN utterance-text keys: per-set tables at k ∈ {1, 5, 10} × {NEW500, OLD500, pooled}, absolute CI90s, paired delta CI90s, the ranker block with its closed-form fusion margin, the re-locked comparator block with its identity anchors, and the applied `decision_v2` table (`decision_v1_rule` carries MF-7's own rule for comparison) |
| `summary-label-keys.json` | the same audit over the 60 intent-label-description keys — reported separately and never deciding the gate |
| `per-query-set-table.json`, `per-query-set-table-label-keys.json` | the per-set × per-k × per-population tables alone |
| `per-scenario-table.json`, `per-scenario-table-label-keys.json` | the per-stratum table every verdict on this program must carry |
| `cosine-separation.json` | the cross-modal separation: matched against unmatched cosine distributions per speech set, in both key spaces, non-gating |
| `key-space-coherence.json` | each tower on its own terms — nearest-other-row intent agreement inside the text key space and inside the speech query space, plus TRAIN text → its own label |
| `decontamination.json` | the split boundaries: `test` never named or loaded, keys are TRAIN construction data, DEV-1000 prior-exposed, **no devel sentence text read at all in this part** |
| `MANIFEST.sha256` | sha256 over every other file in this directory |

## Reproduction

```bash
cd <repo> && source ~/.venvs/speechrl/bin/activate
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src CUDA_VISIBLE_DEVICES=
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data

# the re-locked per-row comparator mask (fails closed on 73.10 / 75.20 / 71.00)
python scripts/slurp_mf7b_comparator_mask.py --write
# the audit itself, both key spaces
python scripts/run_slurp_retrieval_key_audit_v2.py --write
# each tower on its own terms
python scripts/slurp_mf7b_key_space_coherence.py --write
```

The vectors live under `$SPEECHRL_DATA_DIR/vectors/slurp-mf7b/` (and MF-7's under
`vectors/slurp-mf7/`) and never enter Git; their sha256s are carried in `summary.json` under each
query set's `provenance`, and each producing pass left its own
`saea-mf7-vectors-receipt-v1` receipt beside them (`lco.receipt.json`, `nemotron.receipt.json`,
`comparator-mask.receipt.json`). Regenerating the vectors needs the GPU:

```bash
# LCO: start one resident server, then the pass, then stop it
CUDA_VISIBLE_DEVICES=0 /home/chao/llama.cpp-featcache/build/bin/llama-server \
  --host 127.0.0.1 --port 8093 \
  -m $SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf/LCO-Embedding-Omni-3B-Q8_0.gguf \
  --mmproj $SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf/mmproj-LCO-Embedding-Omni-3b-F16.gguf \
  --embedding --pooling last -ngl 999 -c 8192 -b 2048 -ub 2048 -np 1 -fa on
python scripts/slurp_mf7b_lco_embedding_pass.py --sets keys,labels,speech,fused
# Nemotron: nothing resident on the card at the same time
python scripts/slurp_mf7b_nemotron_embedding_pass.py --sets labels,keys,speech,fused
```

## Identity anchors, all fail-closed

* the reconstructed per-row comparator mask reproduces the published projected-v2 intent levels
  **73.10 pooled / 75.20 NEW500 / 71.00 OLD500** exactly, **and** the inherited unprojected
  **71.40 / 73.20 / 69.60** from the same sealed bytes (17 rows flip right, 0 flip wrong — the
  projection verdict's own 17 saves / 0 harms);
* the sealed key npz `vectors-content-facets.npz` and the sealed closed-list outputs are re-hashed
  against their manifests before use;
* MF-7's four CPU sets reproduce their own published recall, vote, filler and echo figures to the
  digit under the new mask (only the corrective columns move, because only the mask moved);
* both GGUF files match the umbrella lock's sha256; both encoder passes' jitter pairs are
  bit-exact.

## What this receipt does NOT establish

It measures what retrieved neighbours *contain* under a majority-vote consumer, not what a frozen
core would *do* with them. The LCO numbers are licensed for its published llama.cpp embedding
protocol only (readiness note section 4). No admission, promotion, superiority, generality or
Stage-3 claim follows.
