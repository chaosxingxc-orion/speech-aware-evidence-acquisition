# Engineering facts

Repository-local implementation facts only; research state and experiment ledger live in the
umbrella wiki.

## Runtime

- Frozen core: Qwen3-Omni-30B, llama.cpp llama-server resident (`-ngl 28`), GGUF Q8_0 + bf16
  mmproj. Asset identity: umbrella `docs/datasets.lock.json` key `qwen3-omni-30b-a3b-instruct-gguf`.
- Before the first model call, an E0 runtime receipt must pin the llama.cpp build commit and
  per-file GGUF sha256 (fail-closed; see the execution contract).
- Compute: WSL2 Ubuntu-24.04, RTX 5090 (sm_120), `~/.venvs/speechrl` Python 3.12.

## Carriers

Lock keys `earnings21-original`, `earnings22-original`, `conec` (profile `r2-core`). Bytes live
under `SPEECHRL_DATA_DIR`; loaders reference lock keys and materialized local paths, never bundle
bytes. D0 closure receipt: umbrella
`docs/checks/audio-aware-evidence-acquisition/2026-08-02-acquisition/`.

## First deliverable (R0 slice, two weeks)

Per the Stage-2A entry contract: package skeleton + deterministic config composition + tests;
locked loaders and scorer adapters for one discovery and one confirmatory carrier; frozen-core
adapter with request/response/cost tracing; evidence schema (provenance, OBS/SUPPLY separation,
admission, final use); MLflow/artifact linkage through the umbrella experiment index; three
engineering controls (bare core, canonical context form, simple fixed retrieval path); one
readiness-qualified closest-prior smoke/reproduction attempt; go/narrow/repair/stop memo.

## Licensing

No LICENSE file yet: private repository during Stage-2A; license is decided at first publication
transaction (owner decision).
