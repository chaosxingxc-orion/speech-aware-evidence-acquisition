# Engineering facts

Repository-local implementation facts only; research state and experiment ledger live in the
umbrella wiki.

## Runtime

- Frozen core: Qwen3-Omni-30B, llama.cpp llama-server resident (`-ngl 28`), GGUF Q8_0 + bf16
  mmproj. Asset identity: umbrella `docs/datasets.lock.json` key `qwen3-omni-30b-a3b-instruct-gguf`.
- Before the first model call, an E0 runtime receipt must pin the llama.cpp build commit and
  per-file GGUF sha256 (fail-closed; see the execution contract). Receipts are **verified, not
  trusted** (`contracts.FrozenCoreGate`, G0 closure 2026-08-04): versioned schemas
  (`saea-e0-closure-receipt-v1`, `saea-runtime-receipt-v1`) with study identity; D1–D4 each bind an
  artifact file whose SHA-256 is recomputed; model files resolve only as canonical relative paths
  under `SPEECHRL_DATA_DIR` inside the lock's `local_subdir`, with file count and total bytes bound
  to the umbrella `datasets.lock.json` entry and every file re-hashed; the build commit must be a
  full 40-hex commit backed by the re-hashed llama-server binary under the declared runtime root;
  absolute paths, traversal, duplicates and extra files are refused.
- Compute: WSL2 Ubuntu-24.04, RTX 5090 (sm_120), `~/.venvs/speechrl` Python 3.12.

## Carriers

Lock keys `earnings21-original`, `earnings22-original`, `conec` (profile `speech-aware-core`). Bytes live
under `SPEECHRL_DATA_DIR`; loaders reference lock keys and materialized local paths, never bundle
bytes. D0 closure receipt: umbrella
`docs/checks/speech-aware-evidence-acquisition/2026-08-02-acquisition/`.

Secondary speech carriers are `slue-sqa-5`, `contextasr-bench` and `ami-meeting-corpus` (profile
`speech-aware-secondary`); none is a core-start gate. `fsd50k`, `audioset-metadata-features` and
`esc-50` are retained cross-domain assets in the umbrella lock and are forbidden in this study's
source, configs and tests.

## First deliverable (R0 slice, two weeks)

Per the Stage-2A entry contract: package skeleton + deterministic config composition + tests;
locked loaders and scorer adapters for one discovery and one confirmatory carrier; frozen-core
adapter with request/response/cost tracing; evidence schema (provenance and separate
OBS/ORG/SUPPLY/USE channels); MLflow/artifact linkage through the umbrella experiment index; three
engineering controls (bare core, canonical context form, simple fixed retrieval path); one
readiness-qualified closest-prior smoke/reproduction attempt; go/narrow/repair/stop memo.

## Licensing

Private-stage policy recorded in `LICENSE` (2026-08-03): all rights reserved while the repository
is private; a public license, if any, is an owner decision at the first publication transaction.
`NOTICE` records the provenance of the quarantined `reference/w1-snapshot/` files (program-internal
W1 authorship; no third-party code vendored).

## Quality gate

`pytest` must collect at least one test and pass (CI treats pytest exit code 5 — no tests
collected — as failure). The model-free contract tests under `tests/contract/` are the E0
engineering floor: information boundary, OBS/ORG/SUPPLY/USE trace separation, exposure schema,
frozen-core entry gate, execution-scope guard, snapshot quarantine, governance alignment and
pre-R0 entrypoint refusal.

Execution scope (consolidated contract §6/§7): every model touch must declare a profile;
`FrozenCoreGate.assert_model_touch_allowed(execution_profile)` accepts only
`baseline-reproduction` and `bounded-discovery-probe` (after receipt verification), and
`contracts.assert_execution_scope` refuses `paper-scale-confirmatory` and every unknown profile
before any receipt is read. Stage-3 work runs only in a separately admitted paper repository.
