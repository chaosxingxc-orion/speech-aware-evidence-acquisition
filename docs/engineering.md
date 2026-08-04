# Engineering facts

Repository-local implementation facts only; research state and experiment ledger live in the
umbrella wiki.

## Runtime

- Frozen core: Qwen3-Omni-30B, llama.cpp llama-server resident (`-ngl 28`), GGUF Q8_0 + bf16
  mmproj. Asset identity: umbrella `docs/datasets.lock.json` key `qwen3-omni-30b-a3b-instruct-gguf`.
- Before the first model call, an E0 runtime receipt must pin the llama.cpp build and per-file
  GGUF sha256 (fail-closed; see the execution contract). Receipts are **verified, not trusted**
  (`contracts.FrozenCoreGate`, G0 closure 2026-08-04, hardened after round-1 adversarial review):
  versioned schemas (`saea-e0-closure-receipt-v1`, `saea-runtime-receipt-v2`) with study identity;
  D1–D4 each bind an artifact file whose SHA-256 is recomputed, and the D3 artifact's frozen
  scoring-source hashes are re-measured against the live tree (an unlisted scoring module refuses);
  model files resolve only as canonical relative paths under `SPEECHRL_DATA_DIR` inside the lock's
  `local_subdir`, with file count and total bytes bound to the umbrella `datasets.lock.json` entry
  and every file re-hashed; `llama-server` is a ~18 KB launcher, so the receipt binds **every
  regular file in `build/bin`** (inference/audio `.so` libraries included) as an exact set, the
  40-hex build commit must be prefix-matched by the binary's self-reported build hash
  (`llama-server --version` at receipt time), and a dirty tree or stale build is refused at
  generation; absolute paths, traversal, duplicates and extra files are refused. The exposure row a
  plan cites is cross-checked field by field (profile, split role, split identity hash,
  consumed=no, registered budgets ≥ planned). Gate verification is instantaneous: the process that
  opens the gate must be the process that starts llama-server, immediately afterward — results are
  never cached or shared. Canonical binding: `FrozenCoreGate.for_study_repo`.
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

## E0 closure state (2026-08-04)

E0 D1–D4 are CLOSED and machine-bound: `docs/receipts/e0-closure.json` binds the four
deliverable artifacts under `docs/receipts/artifacts/` (identity, leakage negative
controls, scoring freeze, ten-sample four-axis trace) by re-measured SHA-256; the
runtime receipt `docs/receipts/runtime.json` (v2) pins the llama.cpp build commit,
its self-reported build hash, the launcher **and every runtime library in
`build/bin`**, plus the per-file GGUF SHA-256 against the umbrella lock. Generators
(model-free, stdlib-only):
`python -m speech_aware_evidence_acquisition.e0.generate d1|d2|d3|d4|close|runtime|verify`
(`verify` is a gate dry run against the real `contracts.FrozenCoreGate`; it touches no
model and authorizes nothing). The D4 sample selection is the upstream-curated
Earnings22 `subset10` (dev carrier); D4 receipts carry trace payload key names and
content hashes only — serialized traces are never committed. The closure event is
registered in `docs/exposure-ledger.md` (`SAEA-E0-CLOSURE-2026-08-04`, model-free,
consumed=no). Enforcement is machine-checked from both directions: the gate re-hashes
the frozen scoring sources and the runtime set at every touch attempt, and
`tests/contract/test_real_receipts.py` re-verifies the committed receipts (closure
chain, scoring freeze, runtime coherence) in CI on every push. Scoring is frozen for
per-segment units; whole-call alignment is out of scope for `saea-scoring-v1`.

## Quality gate

`pytest` must collect at least one test and pass (CI treats pytest exit code 5 — no tests
collected — as failure). The model-free contract tests under `tests/contract/` are the E0
engineering floor: information boundary, OBS/ORG/SUPPLY/USE trace separation, exposure schema,
frozen-core entry gate, execution-scope guard, snapshot quarantine, governance alignment and
pre-R0 entrypoint refusal.

Execution scope (consolidated contract §6/§7; umbrella 续93): every model touch must present a
structured `contracts.ExecutionPlan` — profile, carrier lock key, split role (`discovery`/`dev`
only), split identity hash, planned calls/GPU-hours/audio-seconds within the frozen first-slice
caps, and protocol hash. `FrozenCoreGate.assert_model_touch_allowed(plan)` validates the plan
before reading any byte, then requires the run to be pre-registered in `docs/exposure-ledger.md`
and the carrier to exist in the umbrella lock, then verifies both receipts. Bare profile strings,
`confirmatory` splits, over-cap plans and unregistered runs all fail closed — a paper-scale run
cannot be smuggled in under an allowed profile label. Stage-3 work runs only in a separately
admitted paper repository.
