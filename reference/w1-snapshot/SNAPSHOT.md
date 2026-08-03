# W1 reference snapshot (rescued 2026-08-03)

Source repository: `https://github.com/chaosxingxc-orion/speech-mllm-training-free-rl.git` (the W1
legacy work repository). Its **local checkout was retired on 2026-08-03 by owner ruling; the remote
is retained as a cold backup** unlinked from the program (tombstone:
umbrella `wiki/archive/program/w1-w4-retirement/`; machine registry:
umbrella `docs/integrity/retired-repository-registry.json`; offline bundle under
`SPEECHRL_DATA_DIR/program-archives/`).

This directory holds the **thirteen** files registered as adoption candidates in
`docs/migration-manifest.md`, copied verbatim: ten from the final commit `7ed41f62` working tree
before the local deletion, and three recovered from remote history immediately afterwards. Per-file
SHA-256 in `SHA256SUMS` (verified against the source bytes at copy time).

Status of every file: **`QUARANTINED_REFERENCE_NOT_EXECUTABLE`** — nothing here is imported by the
package, the directory is outside the `src/` package discovery path, and it must never be added to
`sys.path`. The two best-of-N runners embed hardcoded `/mnt/d/.../common/src` path insertions and W1
repo-layout assumptions; they are reference reading material, not runnable entrypoints. Promotion of
any file into `src/` requires a dated adoption row in the migration manifest, removal of absolute
paths, passing tests in this repository, and a fresh hash. If never adopted, this directory is
deletable.

Provenance and licensing: all thirteen files were authored inside the program's own W1 repository
(no third-party code); they are covered by this repository's private-stage license policy (see
`LICENSE` and `NOTICE`).

| File | Original path in W1 | Source commit | SHA-256 | Status | Adoption target |
|---|---|---|---|---|---|
| `baselines/two_pass_runner.py` | `scripts/baselines/two_pass_runner.py` | `7ed41f62` | `72b3ad531ba43b96b743fa1c3efe3e97c2bc8d137236f2f0ef1680ef588a7a4a` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../models/` frozen-core adapter reference |
| `baselines/provenance.py` | `scripts/baselines/provenance.py` | `7ed41f62` | `189bffabdf768811800edfac5257809cd679c3379192cf3680d070aaa6c95c95` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../tracing/` |
| `baselines/metrics.py` | `scripts/baselines/metrics.py` | `7ed41f62` | `84b472f193d8cee366a3405ec837dac4ace8596c7be76baf828f59724847b269` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../scoring/` |
| `baselines/stats.py` | `scripts/baselines/stats.py` | `7ed41f62` | `8c15cb575e9c61d5a7cf9388b345b4219bfe0e9bba9aa8b9c2b335bb7bda3e1a` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../scoring/` + experiment stats |
| `baselines/deterministic_draw.py` | `scripts/baselines/deterministic_draw.py` | `7ed41f62` | `7e6444ddf8ebbb10d883296bf302a5a26a6c36b42b32302fead9af3eb3835fe0` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../scoring/` + experiment stats |
| `loaders/_common.py` | `scripts/loaders/_common.py` | `7ed41f62` | `14fcfe894ded238311922c510b2137099c7dc3f34820e2f75a9c7c0e66cf6172` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../data/` loader skeleton (pattern only) |
| `loaders/registry.py` | `scripts/loaders/registry.py` | `7ed41f62` | `4341626d418f852efe4bf9bbde8290e0c4f1ba7c00069b8f8a07bc602f801b11` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../data/` loader skeleton (pattern only) |
| `knowledge/kb_retrieve.py` | `scripts/knowledge/kb_retrieve.py` | `7ed41f62` | `8e710b4b88eac87eb6d31dacce83abbe8bb447e5c43c4da0d386cff30dad6725` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../evidence/` (defer to method) |
| `knowledge/kb_schema.py` | `scripts/knowledge/kb_schema.py` | `7ed41f62` | `0b00820978c9de77b2e0eb617d1660b46630fff0594b2d7fdc08e4bf996a2295` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../evidence/` (defer to method) |
| `knowledge/corpus_lock.py` | `scripts/knowledge/corpus_lock.py` | `7ed41f62` | `3587a55a3a13fc2e7e472311a75a70c005754d4a3f7b47c4c632abffa6f1c7fb` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | `src/.../evidence/` (defer to method) |
| `baselines/repro_asr_best_of_n_v2.py` | `scripts/repro_asr_best_of_n_v2.py` | `28d8f0d` | `88ff6bc5053d5422e1b9a3c192cf027921e05b8433f1855f8c214d10c5c13702` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | best-of-N runner reference (livelock fix bundle); hardcoded paths must be removed at adoption |
| `baselines/repro_asr_best_of_n_llamacpp.py` | `scripts/repro_asr_best_of_n_llamacpp.py` | `f9d111a` | `23a8f86ebf55e17cece862762e37e26d4e2eb49ce1d2fc07c49396527cfa95f0` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | original best-of-N runner reference; hardcoded paths must be removed at adoption |
| `gpu_session.sh` | `scripts/gpu_session.sh` | `7ed41f62` | `cf9e39495afe60d9aa8a590acd850030446251db4943a82dc58f877a3710b12b` | QUARANTINED_REFERENCE_NOT_EXECUTABLE | GPU serving-session harness reference (LLAMA_CACHE_RAM knob) |
