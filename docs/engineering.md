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
  generation; absolute paths, traversal, duplicates and extra files are refused. In `build/bin`
  any non-file entry (subdirectory, symlink that is not a regular file) is refused; in the scoring
  package, nested sources must be named by the freeze, and non-source files, dangling symlinks and
  symlinked directories are refused (plain subdirectories are legal only because every `.py`
  inside them must be frozen). The exposure row a plan cites is cross-checked field by field
  (profile, split role, split identity hash, consumed=no, registered calls/audio-seconds/GPU-hours
  ≥ planned; every budget cell must be a finite non-negative number), and the first-slice caps are
  enforced as **slice totals**: the gate sums every registered row and refuses a plan that would
  push the campaign over ≤3000 calls / ≤72000 audio seconds / ≤40 GPU-hours. Gate verification is
  instantaneous: the process that opens the gate must be the process that starts llama-server,
  immediately afterward — results are never cached or shared. The freeze binds source bytes, not
  compiled bytecode: the R0 runner must run with `PYTHONDONTWRITEBYTECODE=1` and purge
  `scoring/__pycache__` before opening the gate (a locally planted `.pyc` is outside what a
  same-machine gate can self-verify). The R0 frozen-core adapter must enforce the per-arm
  visible-field **allowlists** frozen in the D2 artifact as its request choke point — the
  boundary blocklist alone is necessary, not sufficient. Canonical binding:
  `FrozenCoreGate.for_study_repo`.
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

## R0 engineering baseline (delivered 2026-08-05)

Two-layer structure (owner direction 2026-08-05: maximize reuse, no
fragmentation). Layer 1 — ONE foundation package `core/`: one `Registry`
mechanism with five seams (CARRIERS, EVIDENCE_SOURCES, TRANSPORTS, POLICIES,
SCORERS), one gate-bound request path (`FrozenCoreAdapter` — D2 allowlist
exact-set choke point, per-plan budget metering), one experiment driver
(`core.driver.run_experiment`), append-only trace sink (repo-refusal), lazy
MLflow linkage + umbrella ledger-row renderer. Shared data layer:
`data/splits.py` (frozen partition, receipt `docs/receipts/splits.json`,
hash convention identical to the E0 ledger row), `data/references.py`
(scoring-side; only `core/scorers.py` may import it — AST contract test).
Layer 2 — experiments are configuration: four disjoint JSON fragments
(`configs/{model,dataset,baseline,experiment}/`); a new experiment is config
plus at most one newly registered component. Policies compose over the three
D2-frozen arm shapes; only `fixed` is implemented (X1/X3/X4 policies register
later without driver changes). Entrypoints `scripts/reproduce.sh` /
`scripts/evaluate.sh` are functional and model-free. First model touch:
`docs/runbooks/2026-08-05-r0-smoke.md` (owner-visible; requires ExecutionPlan
+ pre-registered exposure row; not executed by the delivery plan).

## R0 repair — trust-boundary components (invariants I1-I9)

The R0 repair campaign (`.superpowers/sdd/r0-repair/`) hardens the boundary between a
plan and a genuine, provably-scoped model touch. Beyond the run bundle + finalizer
(I7, detailed below), the campaign closed:

- **I1 verified splits** (`data/splits.py`, `core/split_receipt.py`): the committed
  splits receipt (`docs/receipts/splits.json`) must strict-parse (exact schema/keys,
  per-split carrier/role/count/id ordering and prefix agreement, an `identity_hash`
  recomputed from the ids) and match a **live loader recomputation** bit for bit;
  any disagreement fails closed.
- **I2 carrier scope** (`contracts.py` — `ALLOWED_CARRIER_PROFILES`,
  `general_audio_deny_lock_keys`): a plan's carrier must resolve to a genuine
  speech-aware profile in the umbrella lock and must not be on the general-audio
  denylist; the pre-registered exposure row's carrier column is cross-checked
  against the same plan carrier.
- **I3/I4 payload and media binding** (`core/model.py`, `core/base.py`
  `PayloadBindingContext`): the adapter verifies `payload.carrier_lock_key ==
  plan.carrier_lock_key`, `speech_ref == f"{carrier}/{sample_id}"`, `sample_id` is a
  member of the frozen split, and `audio_seconds` agrees with the loader. Media
  paths accept only normalized POSIX-relative form and must resolve inside the
  carrier's `local_subdir`; absolute paths, drive letters, backslashes, `..` and
  symlink escapes are refused at both the adapter and transport layers.
  (module `contracts.py`)
- **I5 session attestation** (`core/session.py`): every run binds a session receipt
  to the resident server's binary hash, pid, argv, listening port and model/mmproj
  paths (plus, as of the T5 fix-2 continuation, live kernel-level socket-ownership
  verification of the listening port) — no session receipt or an identity mismatch
  refuses the model touch.
- **I6 one-time attempt accounting** (`core/attempts.py`): `(run_id, attempt_id)` is
  a non-reusable primary key; the gate opens atomically/exclusively; actual usage is
  persisted **before** the send, not lost on failure; a retry requires a fresh
  attempt; slice caps take the conservative upper bound of "registered" and
  "actual" usage.
- **I7 run bundle + finalizer**: see the dedicated subsection immediately below.

**I9 CI truthfulness (this task, T9):** CI now reflects current R0 semantics rather
than pre-R0 refusal behavior. `.github/workflows/ci.yml` runs three jobs: `test`
(`uv sync --frozen`, build, `pytest -q`); `contracts` (installs the package, then
asserts today's real entrypoint behavior — `reproduce.sh --help` /
`evaluate.sh --help` exit 0 and print "model-free", `evaluate.sh` with no arguments
exits 2 — and runs the model-free `tests/contract/` subset, which needs no private
assets and touches no model); `lint` (`ruff check` over `src/`, the quarantined
`reference/w1-snapshot/` excluded via `pyproject.toml` and never reformatted). Every
assertion in the `contracts` job was verified locally (WSL2 Ubuntu-24.04) before
being committed: `reproduce.sh --help`/`evaluate.sh --help` → exit 0, "model-free" in
stdout; `evaluate.sh` with no args → exit 2; `tests/contract/` → 134 passed. Note
`reproduce.sh` with **no** arguments (as opposed to `--help`) is a *different*,
already-covered contract: with `SPEECHRL_DATA_DIR` unset it fails closed with exit
1 (`tests/contract/test_scripts_fail_closed.py` covers `--help` and the
`evaluate.sh` no-args case only; exit 1 for `reproduce.sh` with no args is not a
refusal-on-misuse case and is intentionally not asserted by CI).

**Coverage: `NOT_CONFIGURED`. Type-checking: `NOT_CONFIGURED`.** Neither is wired
into `pyproject.toml`, the dev dependency group, or CI; this is stated explicitly
per I9 rather than implied by an absence of failures.

**Config namespace (this task, T9):** `core/config.py`'s four-fragment composer
(`compose()`) reads only `configs/{model,dataset,baseline,experiment}/<name>.json`
— JSON is the one live *experiment-composition* namespace; a new experiment is
JSON config plus at most one newly registered component (see "R0 engineering
baseline" above). Two other, deliberately distinct things also live under
`configs/` and are **not** part of that namespace and are **kept, not deleted**:
- `configs/dataset/{conec,earnings21,earnings22}.yaml` and
  `configs/model/qwen3-omni-30b-a3b-instruct-gguf.yaml` are legacy-format,
  non-composer identity sidecars: `core/config.py` never reads them, but
  `tests/contract/test_governance_alignment.py::test_dataset_and_model_configs_reference_lock_keys_only`
  requires each to name its `lock_key` (and forbids any `sha256:` field — asset
  hashes live in the umbrella lock only) as an independent naming-discipline
  check, and `e0/d2_leakage.py`'s general-audio negative control scans every
  `configs/**/*.yaml` for `lock_key:` lines. Deleting them breaks that governance
  test (verified locally: `pytest tests/contract/test_governance_alignment.py -q`
  fails with `carrier config for earnings21-original is missing` once the files
  are removed) — they are retained and documented here as legacy/non-composer,
  not superseded.
- `configs/experiment/e0-model-free-closure.yaml` is a distinct, **live**,
  non-composer file: `contracts.general_audio_deny_lock_keys` and
  `e0/d2_leakage.py` read it directly, by hardcoded relative path, as the single
  source of truth for the general-audio exclusion denylist. It is not legacy.

## R0 repair T6 — atomic run bundle + finalizer (invariant I7)

Every attempt produces a `run-manifest.json` (`core.bundle`, schema
`saea-run-manifest-v1`) binding the study commit, config/protocol/plan/split
identity, artifact hashes and terminal status. `core.bundle.verify_bundle`
re-derives every hash from bytes on disk; `core.bundle.finalize_bundle` is the
only path to a FINALIZED attempt (verify → score → write scores → re-verify →
stubbable MLflow upload → machine-derived ledger row → mark FINALIZED).

**Scoring authority (`saea-driver score` / `scripts/evaluate.sh`):**
`--manifest` is the AUTHORITATIVE path — it re-verifies the bundle before
scoring and is the only mode whose result may be cited as a formal record.
`--outputs` (and the legacy positional `evaluate.sh <outputs.jsonl>` form)
scores a raw outputs file directly with **no split/trace/hash verification**;
it prints a loud warning and tags its result `"verified": false` — it exists
for ad-hoc/exploratory scoring only and must never be treated as an audit
record.

**Accepted scope boundary of I7 (state plainly, do not over-trust):** the
bundle chain is a *consistency* check over files on disk, not an
*authenticity* check that a response ever genuinely crossed the frozen-core
boundary. An attacker (or bug) with plain filesystem write access to a run's
`run_dir` — the same access a legitimate run already needs — can synthesize a
fully self-consistent bundle from scratch and `finalize_bundle` will accept
it end to end, because the raw response bytes a `response_sha256` hashes are
never independently persisted anywhere outside files the same writer
controls. See the `core/bundle.py` module docstring for the full statement;
closing this gap (an external, write-once transport log or a signed
attestation anchor) is out of scope for R0's local, single-machine trust
model.

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
