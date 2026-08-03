# W1 reference snapshot (rescued 2026-08-03)

Source: `https://github.com/chaosxingxc-orion/speech-mllm-training-free-rl.git` @ commit
`7ed41f62e3f33f9f16d0fbbe2d13725ace62502f` (branch master) — the W1 legacy work repository,
deleted local+remote on 2026-08-03 by owner ruling (see umbrella Decision-Log and
`wiki/archive/program/w1-w4-retirement/`).

These are the ten files registered as adoption candidates in `docs/migration-manifest.md`,
copied verbatim before the source was destroyed. Per-file SHA-256 in `SHA256SUMS` (verified
against the source working tree at copy time; tree was clean at the pinned commit).

Status: **unintegrated reference**. Nothing here is imported by the package. Integration into
`src/` still requires a dated adoption row in the migration manifest plus passing tests, per
the copy-and-verify protocol. If never adopted, this directory is deletable.

| File | Original path in W1 |
|---|---|
| baselines/two_pass_runner.py | scripts/baselines/two_pass_runner.py |
| baselines/provenance.py | scripts/baselines/provenance.py |
| baselines/metrics.py | scripts/baselines/metrics.py |
| baselines/stats.py | scripts/baselines/stats.py |
| baselines/deterministic_draw.py | scripts/baselines/deterministic_draw.py |
| loaders/_common.py | scripts/loaders/_common.py |
| loaders/registry.py | scripts/loaders/registry.py |
| knowledge/kb_retrieve.py | scripts/knowledge/kb_retrieve.py |
| knowledge/kb_schema.py | scripts/knowledge/kb_schema.py |
| knowledge/corpus_lock.py | scripts/knowledge/corpus_lock.py |

| baselines/repro_asr_best_of_n_v2.py | scripts/repro_asr_best_of_n_v2.py (W1 @ `28d8f0d`; llama-server best-of-N with the proven livelock fix bundle) |
| baselines/repro_asr_best_of_n_llamacpp.py | scripts/repro_asr_best_of_n_llamacpp.py (W1 @ `f9d111a`; original genuine best-of-N runner) |
