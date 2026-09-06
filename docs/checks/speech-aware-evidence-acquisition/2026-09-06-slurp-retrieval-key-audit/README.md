# MF-7 — SLURP retrieval-key audit (2026-09-06)

Model-free receipts for prerequisite MF-7. **Zero frozen-core contacts, zero GPU.** Verdict and
protocol: `docs/readiness/2026-09-06-slurp-retrieval-key-audit-v1.md`.

Exposure rows, both registered in `docs/exposure-ledger.md` before the first read:

* `SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V1` — the reads (sealed baseline per-row official scores,
  sealed KU-S1c drafts, TRAIN content facets, DEV-1000 gold intent/entities, and — named
  explicitly — the devel sentence text, read only to compute the `q-gold-text` embeddings and
  written to nothing).
* `SAEA-SLURP-MF7-EMBEDDING-CPU-V1` — the CPU encoder passes: the pinned Qwen3-Embedding-0.6B-Q8_0
  llama-server at `-ngl 0` (2,000 text contacts) and Xiaomi GLAP on `device="cpu"` (1,000 audio
  forwards + 11,514 text forwards).

## Files

| file | what it carries |
|---|---|
| `summary.json` | the whole audit: per-query-set tables at k ∈ {1, 5, 10} × {NEW500, OLD500, pooled}, absolute CI90s, paired delta CI90s, the ranker block with its closed-form fusion margin, and the applied decision table |
| `per-query-set-table.json` | the per-set × per-k × per-population tables alone, for a reader who wants only the numbers |
| `per-scenario-table.json` | the per-stratum table every verdict on this program must carry — one row per gold scenario, per set, per population, at the decision k |
| `decontamination.json` | the split boundaries: `test` never named or loaded, keys are TRAIN construction data, DEV-1000 is prior-exposed, and the devel sentence text reaches no artifact |
| `MANIFEST.sha256` | sha256 over every other file in this directory |

## Reproduction

```bash
cd <repo> && source ~/.venvs/speechrl/bin/activate
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src CUDA_VISIBLE_DEVICES=
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
python scripts/run_slurp_retrieval_key_audit.py --write
```

The vectors the audit consumes live under `$SPEECHRL_DATA_DIR/vectors/slurp-mf7/` and never enter
Git; their sha256s are carried in `summary.json` under each query set's `provenance`, and the
producer passes' own receipts (`qwen3emb-queries.receipt.json`, `glap.receipt.json`) sit beside
them on the data root.

Adding the GPU query sets needs no code change: drop their JSONL pairs into the same directory in
the same `saea-mf7-vectors-v1` schema and pass `--query-set`. Section 6 of the readiness note is
the runbook.

## What this receipt does NOT establish

It measures what retrieved neighbours *contain*, not what a frozen core would *do* with them. A
query set that clears the corrective-power gate has shown an upper bound on a voting consumer, not
an admitted cell. No admission, promotion, superiority, generality or Stage-3 claim follows.
