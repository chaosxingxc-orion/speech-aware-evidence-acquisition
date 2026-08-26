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
  `local_subdir`, with file count and total bytes bound to the umbrella `datasets.lock.json` entry.
  **GGUF identity, changed scope (owner decision 2026-08-06, `docs/owner-decisions-pending.md`
  item 7):** re-hashing the pinned ~34.7 GB GGUF set from bytes on *every* gate open measured
  142-175s over the WSL2 9p mount onto the Windows-hosted data root, which made routine
  verification (`scripts/reproduce.sh`, run before/after every commit) painfully slow without
  making a genuine model touch any safer for the overwhelming common case — nothing about the
  files changed since the last real verification. The gate now defaults to a cheap-identity fast
  path per GGUF file: absolute path, byte size, `st_mtime_ns`, and OS file identity (`st_ino`/
  `st_dev` via Python's own `os.stat()` — CPython already populates these on Windows from the NTFS
  file ID via `GetFileInformationByHandle`, verified stable and non-zero on this checkout; no
  separate `ctypes`/`nFileIndex` path is needed) compared against a cache
  (`<SPEECHRL_DATA_DIR>/.saea-runtime-identity-cache.json`, never committed, bound to the runtime
  receipt's own SHA-256). A full SHA-256 re-hash still runs whenever any cheap-identity field
  differs, a cache record is missing/corrupt, the runtime receipt itself changed, the caller
  explicitly asks (`full_hash=True` / `scripts/reproduce.sh --full`), or — the gate's own SAFE
  default — this is the first gate open of the current process/session
  (`contracts.FrozenCoreGate.assert_model_touch_allowed`'s own `full_hash=None` default; a real
  model touch, `core.model.FrozenCoreAdapter`, never overrides this). **STATED GUARANTEE, changed
  and precise, not overstated: the fast path defends against a WRONG, PARTIAL, or
  ACCIDENTALLY-REPLACED model set — it does NOT defend against an adversary who edits a GGUF
  file's bytes in place while deliberately preserving its size, mtime and OS file identity**; this
  residual weakness is pinned by an explicit test
  (`tests/contract/test_runtime_identity_fastpath.py`), not left as prose alone. `llama-server` is
  a ~18 KB launcher, so the receipt binds **every regular file in `build/bin`** (inference/audio
  `.so` libraries included) as an exact set, **always fully re-hashed from bytes, unconditionally,
  every gate open** (~249 MB total — cheap, and it is the code that actually runs; `full_hash` has
  no effect here). The 40-hex build commit must be prefix-matched by the binary's self-reported
  build hash (`llama-server --version` at receipt time), and a dirty tree or stale build is refused
  at
  generation; absolute paths, traversal, duplicates and extra files are refused. In `build/bin`
  any non-file entry (subdirectory, symlink that is not a regular file) is refused; in the scoring
  package, nested sources must be named by the freeze, and non-source files, dangling symlinks and
  symlinked directories are refused (plain subdirectories are legal only because every `.py`
  inside them must be frozen). The exposure row a plan cites is cross-checked field by field
  (profile, split role, split identity hash, consumed=no, registered calls/audio-seconds/GPU-hours
  ≥ planned; every budget cell must be a finite non-negative number). **Budget caps, retired (owner
  amendment 2026-08-06, `SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS`,
  `wiki/experiments/speech-aware-evidence-acquisition/
  2026-08-06-owner-budget-caps-retirement-contract.md`):** the first-slice numeric ceilings
  that used to live here (≤3,000 calls / ≤72,000 audio seconds / ≤40 GPU-hours, formerly
  `contracts.FIRST_SLICE_CAPS`, formerly summed as slice totals across every registered ledger row
  by `contracts.FrozenCoreGate._require_exposure_preregistration`, and formerly checked per plan by
  `ExecutionPlan.validate()`) are gone; no numeric ceiling is enforced anymore, machine or otherwise.
  What the owner amendment explicitly keeps, and what the gate still enforces: paid API = 0 and the
  Stage-3 stop line; exposure pre-registration (profile/split role/split identity hash/carrier);
  one-time `(run_id, attempt_id)` attempt semantics; and the per-row/per-plan self-consistency above
  — a registered row must be ≥ the plan's own declared budget, and `ExecutionPlan.validate()` still
  requires every budget field to be a finite positive number (integral where applicable), just with
  no upper bound. Do not reintroduce a cap without a new dated owner amendment. The process that opens
  the gate must be the process that starts llama-server, immediately afterward — the gate's own
  pass/fail DECISION is never cached or shared across processes or separated from the launch it
  authorizes; the GGUF identity cache above is a narrow, internal, per-file performance optimization
  for one sub-check, never a substitute for calling the gate itself, which still re-verifies E0
  closure, the scoring freeze, exposure pre-registration, carrier scope, the llama.cpp build binary
  and every runtime library from scratch on every single call. The freeze binds source bytes, not
  compiled bytecode: the gate itself refuses (M-1 hardening, external-threat-model review) if
  `scoring/__pycache__` contains any entry, so a locally planted `.pyc` co-located with the frozen
  sources is refused rather than silently invisible to the freeze. That on-disk walk alone is not a
  complete guarantee: `sys.pycache_prefix`/`PYTHONPYCACHEPREFIX` relocates every `.pyc` the
  interpreter would read or write into a mirrored tree the walk never visits, and
  `PYTHONDONTWRITEBYTECODE=1` only stops a NEW `.pyc` being written — it does nothing to stop an
  ALREADY-planted one from being read and executed (writing is not reading). The gate therefore also
  refuses outright, at model-touch time, if either `sys.pycache_prefix` or `PYTHONPYCACHEPREFIX` is
  set for the checking process, and refuses if any already-imported `speech_aware_evidence_
  acquisition.scoring` submodule loaded from this checked tree was loaded from a non-`.py` file or
  carries a `__cached__` location outside it (`FrozenCoreGate._assert_no_relocated_bytecode_cache`).
  Stated precisely, not overstated: this proves no relocated-cache configuration is active for THIS
  checking process and that every scoring submodule it has already imported from the checked tree came
  from source with no cache recorded elsewhere — it does not, and cannot, prove no OTHER process with
  its own `PYTHONPYCACHEPREFIX` holds a forged cache it could execute independently of this gate check.
  Still run the R0 runner with `PYTHONDONTWRITEBYTECODE=1` and an unset `PYTHONPYCACHEPREFIX` as
  defense in depth — but the machine-checked guarantee above is the one actually enforced, not that
  environment variable alone. The gate's own real-repo-tree tests
  (`tests/contract/test_real_receipts.py`, `tests/unit/test_e0_generators.py::TestCloseAndGate`)
  point `source_root` at this checkout's actual `scoring/`, so the TEST SESSION enforces the same
  discipline on itself (`tests/conftest.py`, both a module-level `sys.dont_write_bytecode = True` +
  `scoring/__pycache__` purge at conftest-import time — early enough to precede collection-time
  imports writing fresh bytecode — and a session-scoped autouse fixture re-asserting both as defense
  in depth) — a stray `.pyc` left by some earlier, unrelated interpreter can no longer make the
  suite's own outcome nondeterministic. Umbrella-lock identity: the gate reads
  `docs/datasets.lock.json` exactly once per `assert_model_touch_allowed` call and returns its
  SHA-256, which the adapter carries into the run manifest's cost block (`umbrella_lock_sha256`) for
  the ledger's "dataset rev" cell (M-3). D1 media identity: at model-touch time the adapter asks the
  gate to re-verify exactly the run's split's media against D1's frozen per-file byte/SHA-256 facts,
  and to sanity-check each sample's loader-reported `audio_seconds` against that same frozen byte
  size for MP3-bitrate plausibility (I-4; see `contracts.FrozenCoreGate.verify_media_identity` for
  the documented residue this leaves — a plausibility bound, not an exact duration re-derivation).
  D1 evidence identity (IMPORTANT 1, external review round 4): the same construction-time check for
  evidence — `contracts.FrozenCoreGate.verify_evidence_identity` re-verifies exactly the sample ids
  the run's evidence source supplied non-empty evidence for against D1's frozen evidence-layer bytes
  (today: `earnings21-original` via `conec.layers.e21_contexts` only — see
  `docs/owner-decisions-pending.md` item 8 for scope and the pre-rotation negative-control scoping
  decision). The R0 frozen-core adapter must enforce the per-arm
  visible-field **allowlists** frozen in the D2 artifact as its request choke point — the
  boundary blocklist alone is necessary, not sufficient. Canonical binding:
  `FrozenCoreGate.for_study_repo`.
- Compute: WSL2 Ubuntu-24.04, RTX 5090 (sm_120), `~/.venvs/speechrl` Python 3.12.
  WSL2 is the sole formal execution authority for experiments, data validation,
  tests, server lifecycle, and model contact. Native Windows is restricted to
  Git/status synchronization and must never run a duplicate experiment or test.
  `contracts.assert_wsl_execution_environment` enforces this boundary before a
  formal model touch, and `core.session.start_session` enforces it before loading
  or spawning llama.cpp. Native Linux and containers also fail closed because
  they are not the receipt-bound WSL2 compute environment.

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
  attempt; a run's own `FrozenCoreAdapter` never lets combined sibling-attempt
  actual usage exceed **its own** plan's declared calls/audio-seconds. (The
  slice-wide conservative-maximum check that used to compare a ledger-registered
  total against `AttemptStore.all_actual_usage()` for a global cap was retired by
  the 2026-08-06 owner amendment; per-row registered ≥ planned, checked at
  `assert_model_touch_allowed`, is unaffected.)
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

**Lint scope (`lint` job), stated plainly, not as "clean":** the gate runs
`ruff check src` only, not the whole active tree. Repo-wide, `ruff check .` (with
the quarantined `reference/w1-snapshot/` excluded and its 12 findings therefore
never counted here) currently reports **8 findings, confined entirely to
`tests/`** — trivial `F401`/`F811` unused-import/redefinition cases in
`test_exposure_and_gate.py`, `test_real_receipts.py`, `test_attempts.py`,
`test_bundle.py`, `test_driver.py` and `test_frozen_core_adapter.py`. `src/` is
clean under the same command (`ruff check src` → 0 findings). The gate is
deliberately scoped to `src/` rather than fixed to 0-over-everything because
`tests/` was, and at the time of writing still is, actively being edited by
concurrently-landing repair tasks that own those specific files; folding
`tests/` into the `lint` job is a follow-up for whichever task next closes out
those files, not silently dropped.

**R0 operator-path repair (2026-08-07), correcting the claim above:** an
independent rereview found `ruff check src` was NOT actually clean at the
reviewed commit — one `F841` (an unused `n` in
`contracts/ledger.py::_strip_same_line_comments`) — despite this doc's own
"0 findings" claim above. That variable is now removed; `ruff check src` is
verified 0 findings again as of this fix. The same rereview also found
`python -m speech_aware_evidence_acquisition.core.driver` could not dispatch
at all: turning `core/driver.py` into a package left no `core/driver/
__main__.py`, and `python -m <package>` only ever executes a package's own
`__main__.py`, never its `__init__.py` (whose `if __name__ == "__main__":`
guard was therefore dead code for that invocation form). Both a
`__main__.py` and a `saea-driver` console script (`pyproject.toml`'s
`[project.scripts]`) now exist, calling the same `core.driver.cli.main`
either way; `.github/workflows/ci.yml`'s `contracts` job now asserts both
dispatch for real (not merely `--help`/no-args inside `scripts/*.sh`, which
exit before ever reaching Python) via
`tests/contract/test_cli_module_dispatch.py`'s real-subprocess tests. A new
`saea-driver smoke` subcommand (`core/driver/smoke.py`) collapses the R0
smoke runbook's plan/session/run/finalize sequence into one command; its
`--dry-run` path (TEST-ONLY, never a real model touch) is covered by
`tests/unit/test_driver_smoke.py`, run in CI's `contracts` job. See
`docs/runbooks/2026-08-05-r0-smoke.md` for the corrected operator sequence.

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

## R0 repair T8 — formal control configs + scorer seam

Three named engineering controls from the owner contract (bare core, fixed legal context, fixed
retrieval) plus the random/mismatched-evidence negative control are now runnable named configs
under `configs/baseline/`: `bare-core.json` (pre-existing), `fixed-legal-context.json`,
`fixed-retrieval.json`, `mismatched-evidence.json` (`evidence_mismatch: true`, layered on
`fixed-legal-context`). Each composes (disjoint keys) with the real `configs/{model,dataset,
experiment}/*.json` fragments and, loaded from the committed file (not retyped by hand), drives a
synthetic end-to-end `core.driver.run_experiment` call — see
`tests/unit/test_config_composition.py` and `tests/unit/test_driver.py`. `fixed-retrieval` wires
its `retrieval_query` as a top-level composed value (a baseline-fragment key, mirroring
`task_instruction`); `core.driver.run_experiment` reads it via `values.get("retrieval_query")` into
`SampleContext.retrieval_query`, which `core.policies.build_arm_payload` requires non-empty for
that arm. Both evidence-bearing configs use `evidence_source: "conec-contexts"`, which is
`earnings21-original`-scoped in R0 (`core/evidence.py::_conec_contexts` reads a fixed
`earnings21/contexts/<sample_id>.txt` relpath regardless of which carrier a run names).

**`SCORERS` registry (`core/scorers.py`), current and complete:** `asr-wer` (WER against the
carrier's frozen `.nlp` reference layer) and `cost` (T8: reads the **sibling run manifest's**
`cost` block — same `run_dir`, same `run_id` stem as `outputs_path`, the exact naming convention
`core.bundle.build_manifest` already uses — never a parallel accounting path; fails closed if no
such manifest exists or it carries no `cost` block). `scoring/entity.py` and `scoring/qa.py` remain
frozen, hash-pinned functions with **no** registered adapter: the reference-layer format they would
need (Earnings21 `wer_tags`, a spoken-QA carrier) was never pinned by an owner-approved readiness
memo. See `docs/owner-decisions-pending.md` for the full record of what was inspected and what
remains open — do not read the *absence* of an entity/QA scorer as an oversight; it is a deferred,
explicitly recorded scope item.

## R0 repair T7 — cost accounting completion (invariant I8)

`core.model.FrozenCoreAdapter.cost_summary()` previously reported only calls / audio seconds /
latency / prompt+completion tokens. The run aggregate (`RunResult.cost`, threaded unchanged into
the T6 run manifest's `cost` block) now also carries: `gpu_seconds` / `peak_vram_mib` (via the
injectable `core.resources.ResourceSampler` seam — `NvidiaSmiSampler` polls `nvidia-smi
--query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits` on a background thread,
`NullSampler` and any sampling failure record the literal `NOT_AVAILABLE` plus a
`gpu_sampling_reason`); `cpu_seconds` (`os.times()`, process + children, always measured);
`gate_setup_seconds` (wall time from `run_experiment` entry through `FrozenCoreAdapter`
construction, i.e. split/carrier/evidence resolution + gate check + attempt reservation, before the
per-sample request loop); `supplied_evidence_bytes` / `admitted_evidence_bytes` (aggregated from the
same per-sample `supply_content_bytes` figure already computed for the SUPPLY trace record;
"admitted" narrows to `SampleOutcome.admitted` samples); `tool_calls`
(`FrozenCoreAdapter.record_tool_call()`, zero today — no registered policy is tool-using, but wired
through the adapter's existing metering choke point for a future one); and `failed_attempt_calls` /
`failed_attempt_audio_seconds` (`core.attempts.AttemptStore.actual_usage_in_states`, sibling attempts
under the same `run_id` that are ABORTED, excluding the reporting attempt's own spend).

**Test hygiene:** `core.driver.run_experiment`/`run_experiment_bundled` default `resource_sampler` to
a no-op `NullSampler` — `core.driver._cli_run` (the live-run CLI entry point) is the ONLY call site
that resolves a real sampler (`core.resources.resolve_resource_sampler`), so no library caller or
test can be surprised into shelling out to a real `nvidia-smi`; every unit test injects a fake
sampler or accepts the default NOT_AVAILABLE.

**`failed_attempt_calls`/`failed_attempt_audio_seconds` is itself best-effort (T7 fix, reviewer-flagged
IMPORTANT):** this lookup runs AFTER a run has already fully succeeded (every model call made,
outputs/trace already durable). A corrupted or unreadable SIBLING attempt file for the same `run_id`
(someone else's crash, not this run's) must never raise and — via `run_experiment_bundled`'s
`except Exception` — silently convert a genuinely successful, budget-spent run into a false ABORTED
manifest. On a read failure only this pair degrades to `NOT_AVAILABLE` with a
`failed_attempt_cost_reason`; every other cost field, including this run's own spend, is unaffected.
Mirrors `core.bundle._best_effort_cost_for_aborted_attempt`'s identical read, which already wrapped
this the same way for the ABORTED path.

**Two disclosed, bounded approximations in `NvidiaSmiSampler` (T7 fix, reviewer-flagged MINOR, see
`core/resources.py` module docstring for the full rationale):**

1. `gpu_seconds` undercounts by at most one `interval_seconds` (default 1.0s): the final partial span
   between the last recorded poll and `stop()` is never recorded. This is a coarse instrumentation
   figure measured in GPU-*hours*, not a precise billing meter — chosen over polling once more inside
   `stop()` for simplicity and one fewer shutdown-path failure mode. (No numeric GPU-hours ceiling is
   enforced since the 2026-08-06 owner amendment retired the first-slice caps; this approximation's
   negligibility no longer rests on any specific hour bound.)
2. `gpu_seconds`/`peak_vram_mib` are `nvidia-smi`'s DEVICE-wide totals (every process on that GPU),
   not this run's share alone; `device_index` (default `0`, also `resolve_resource_sampler`'s default)
   pins WHICH device is queried (`--id=<device_index>`) but does not add per-process attribution.
   Correct for this study's documented single-GPU dev box; a shared/multi-tenant GPU host would need
   real per-process attribution this module does not attempt.

**ABORTED manifests never carry `cost=None` after T7 either:** `core.bundle
._best_effort_cost_for_aborted_attempt` reads the failed attempt's own durable usage (and any prior
sibling ABORTED attempts' usage) straight from `core.attempts.AttemptStore` — the only state that
survives a `run_experiment` exception, since its in-memory adapter/sampler state does not. Every
field that genuinely cannot be recovered post-hoc (latency/tokens/tool_calls/cpu/gpu/evidence/
gate_setup) is the literal `NOT_AVAILABLE` with a shared `cost_unavailable_reason`, never a silent
omission.

**Manifest schema decision:** `RUN_MANIFEST_SCHEMA` stays `saea-run-manifest-v1` — no version bump.
`core.bundle.verify_bundle` performs no fixed-key-set check on the `cost` block (nor does
`core.scorers.score_cost_outputs`, which only requires a non-empty dict), so a manifest built before
T7 (the old 5-field cost shape) still verifies and still scores end to end.

See `docs/owner-decisions-pending.md` §2 for the full record (what is measured, what degrades to
NOT_AVAILABLE and why, and why no further owner decision is required beyond design spec §6.2's
existing pre-authorization).

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
frozen-core entry gate, execution-scope guard, snapshot quarantine, governance alignment and the
current, R0-form entrypoint contract (not the retired pre-R0 "always refuses" behavior):
`reproduce.sh --help` / `evaluate.sh --help` are model-free and exit 0, `evaluate.sh` with no
arguments refuses with exit 2, neither entrypoint contains a model-touch code path, and
`reproduce.sh` forwards a runtime root to the verify gate (`tests/contract/test_scripts_fail_closed.py`).

Execution scope (consolidated contract §6/§7; umbrella 续93): every model touch must present a
structured `contracts.ExecutionPlan` — profile, carrier lock key, split role (`discovery`/`dev`
only), split identity hash, planned calls/GPU-hours/audio-seconds (each a finite positive number,
integral where applicable — no numeric ceiling since the 2026-08-06 owner amendment retired the
first-slice caps), and protocol hash. `FrozenCoreGate.assert_model_touch_allowed(plan)` validates
the plan before reading any byte, then requires the run to be pre-registered in
`docs/exposure-ledger.md` with a registered budget ≥ the plan's own declared budget, and the
carrier to exist in the umbrella lock, then verifies both receipts. Bare profile strings,
`confirmatory` splits, under-registered plans and unregistered runs all fail closed — a paper-scale
run cannot be smuggled in under an allowed profile label. Stage-3 work runs only in a separately
admitted paper repository.

**`tests/unit/test_session.py`, native-Windows/WSL2 split (deliberate, owner-approved, not a
coverage reduction):** the I5 process-identity/socket-ownership probes that need a SECOND,
genuinely spawned "pinned binary" process — a fresh COPY of an executable at a brand-new pytest
`tmp_path` every run — that also binds a real LISTENING socket are marked POSIX-only
(`skipif(os.name == "nt", ...)`). On native Windows that exact combination makes Defender Firewall
prompt for an unrecognized executable image on essentially every run (the allow-rule it creates
points at that run's `tmp_path`, which no longer exists next run, so the very next run prompts
again). Those probes already run clean under WSL2, this program's compute authority, and are
unaffected. Native Windows keeps its coverage of the same underlying Windows API
(`GetExtendedTcpTable` / `core.session._windows_verify_pid_owns_listening_socket`) via a new
in-process test class, `TestWindowsSocketOwnershipInProcess`: it binds a real loopback TCP listener
INSIDE the pytest process itself (v4 and v6) — no new executable image, so no new firewall prompt —
and asserts ownership is correctly attributed to `os.getpid()`, refused for a different pid, and
that the T5 fix-3 `(family, address, port)` keying correctly separates IPv4 from IPv6 rather than
matching by port number alone. One thing this native-Windows in-process substitute does **not**
cover (still WSL2-only): the fix-3 "secondary bug" scenario where a v4 listener and a v6 listener
are owned by two genuinely DIFFERENT pids sharing the same port number, proving the Windows
owner-table merge no longer lets a v6 entry silently overwrite the v4 owner — an in-process test can
only ever bind both sockets as itself, which cannot distinguish fixed from regressed code there;
`test_attach_succeeds_for_v4_session_despite_unrelated_v6_listener_same_port` and its two sibling
split-forgery tests still exercise that end to end under WSL2. Tests that spawn `sys.executable`
directly (un-copied, a stable path across runs) are unaffected by any of this and keep running on
native Windows.

**GitHub CI runs a SUBSET, and the excluded tests are named and counted (2026-08-26).**
`ubuntu-latest` is a clean, single-repository, plain-Linux container, and two of this study's real
preconditions are absent there and cannot be faked: (1) the WSL2 compute authority, which
`contracts.plan.assert_wsl_execution_environment()` requires by kernel release, so every test that
drives the real `FrozenCoreGate.assert_model_touch_allowed` or `core.session.start_session` past its
profile check is correctly REFUSED on the runner; and (2) the umbrella checkout, since seven tests
read the real umbrella `docs/datasets.lock.json` at `REPO_ROOT.parent.parent`, which lives in a
different Git repository. Two markers name those preconditions -
`requires_wsl2_execution_authority` (115 tests, 112 functions across 9 files) and
`requires_umbrella_checkout` (7 tests) - and `.github/workflows/ci.yml` deselects them with `-m`.
This is an exclusion, never a weakening: nothing is skipped, deleted, softened or patched, the gate
itself is unchanged, and on the WSL2 host all 122 still run exactly as before. The honesty
conditions are enforced, not promised. The workflow step **"Environment exclusions are exactly the
declared inventory"** prints every excluded node id, prints both counts and then ASSERTS them
(`test "${wsl2}" -eq 115`, `test "${umbrella}" -eq 7`), so marking one more test fails CI on the
number until a human looks at it; `--strict-markers` is in `addopts`, so a misspelled marker is an
error rather than an inert decorator; and the mutation probe
`tests/contract/test_execution_scope.py::test_gate_calls_the_wsl2_authority_check_before_reading_any_receipt`
runs IN CI and fails if the WSL2 call is ever removed from the gate (its `start_session` twin,
`TestStartSessionSpawn::test_spawn_refuses_outside_wsl_before_any_process_or_asset_access`, has been
passing in CI throughout). An autouse fixture patching `platform.release` across the suite was
considered and refused: it would disable a fail-closed execution-authority gate everywhere at once.

**Pins are over Git blob bytes, and CRLF is refused (2026-08-26).** Umbrella `CLAUDE.md`: "Git blob
bytes are the evidence hash authority ... not CRLF working-tree bytes". `.gitattributes` declares
`* text=auto eol=lf`, so every text artifact's blob is LF; a Windows working tree that still holds
CRLF for a pinned file hashes to a value no clean checkout can reproduce, which is exactly how the
D-GATES pin (`da59b6e1...` from 32790 CRLF bytes, against the blob's `6ab241b1...` from 32445 LF
bytes) reached `master` and broke CI. `analysis.stage2a_synthesis_verification.crlf_defect` now
refuses such a file BY NAME in all three pinned-artifact loops, and
`tests/unit/test_scoreboard_v5_verification.py::TestPinsAreOverGitBlobBytes` carries both a standing
invariant (no pinned artifact holds CRLF on disk) and a mutation gate. Hashing the blob instead of
the disk was rejected: these verifiers also hash freshly written, not-yet-committed receipts, where
substituting committed bytes would report a stale digest as current.
