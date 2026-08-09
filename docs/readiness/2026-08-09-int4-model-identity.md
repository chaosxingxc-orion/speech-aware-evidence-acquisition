# INT4 (Q4_K_M) second-model identity: plumbing landed, operator sequence

Status: engineering plumbing DONE and unit-tested (synthetic fixtures only — no
real Q4_K_M bytes touched, no llama.cpp rebuild, no model run). What remains is
owner-authority (the umbrella lock edit) and operator-authority (materializing
the files, running the receipt-build script). No model was touched to produce
this document; no receipt was regenerated.

## What changed

The runtime-receipt / model-identity machinery now supports a SECOND pinned
model (Q4_K_M GGUF) alongside the existing Q8_0, without touching the Q8_0
receipt, its default file location, or any existing caller's behaviour.

1. **`e0/runtime_receipt.py::build_runtime_receipt`** takes an optional
   `model_lock_key` parameter (default: `contracts.MODEL_LOCK_KEY`, the frozen
   Q8_0 key — unchanged for every existing caller). The built receipt's own
   `model_lock_key` field records exactly the key that was actually used to
   resolve the umbrella lock's `local_subdir`/`files`/`size_bytes`, so a
   receipt built for a different model entry is truthfully self-describing.

2. **Receipt-path selection** — every place that previously hard-coded
   `docs/receipts/runtime.json` now resolves it from the composed model
   config's optional `runtime_receipt` key (relative to the study repo's
   `docs/` directory), defaulting to `receipts/runtime.json` when the key is
   absent (`core/config.py::runtime_receipt_relpath` /
   `resolve_runtime_receipt_path`):
   - `contracts/gate.py::FrozenCoreGate.for_study_repo` — new keyword-only
     `runtime_receipt_relpath` parameter, default unchanged.
   - `core/driver/smoke.py::_cli_smoke` (non-dry-run path) — both the gate
     construction and the `load_runtime_receipt` call now read this key.
   - `core/driver/cli.py::_cli_run` (the "session start" / `attach_session`
     call site) — same.

   The key flows into `config_hash` → `protocol_hash` automatically: `compose()`
   already merges every fragment's top-level keys verbatim before hashing, so
   a fragment that declares `runtime_receipt` composes to a different hash
   than one that does not — no separate wiring was needed for that part.
   Every fragment that omits the key resolves to the exact same default path
   and the exact same `config_hash` as before this change (the default is
   applied only at consumption time, never injected into the merged config).

3. **New config fragment** `configs/model/qwen3-omni-llamacpp-q4km.json` — same
   shape as the existing batch-profile fragment
   (`configs/model/qwen3-omni-llamacpp-batch.json`), minus the
   `-ot .ffn_.*_exps.=CPU` CPU-offload override (the whole point of Q4_K_M: it
   fits entirely in 24 GB VRAM), plus the `runtime_receipt` selector:
   ```json
   {
     "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
     "transport": "llama-server",
     "base_url": "http://127.0.0.1:8080",
     "timeout_seconds": 900.0,
     "server_args": ["-c", "32768", "-np", "4", "-fa", "on", "-ngl", "999"],
     "decoding_params": {"temperature": 0, "seed": 20260803},
     "runtime_receipt": "receipts/runtime-q4km.json"
   }
   ```
   `server_args` is not yet consumed anywhere in this checkout's session-spawn
   code (`core/session/lifecycle.py::start_session` only ever passes `-m`/
   `--mmproj` + `extra_argv`) — it is carried as config-fragment data, matching
   the existing batch fragment's own shape. Wiring `server_args` into the
   actual `llama-server` launch argv is a separate, not-yet-landed capability
   this task did not touch or need to touch.

4. **Operator CLI** — extended the existing E0 entry point rather than adding a
   new script (`e0/generate.py`'s `runtime` subcommand already existed; adding
   a second, parallel `scripts/build_runtime_receipt.py` would have duplicated
   its lock/data-root/CLI-error handling for no benefit). Two new flags:
   `--model-lock-key` (default: the frozen Q8_0 key) and `--out` (default:
   `<receipts-dir>/runtime.json`). Prints the written file's SHA-256, as it
   already did for the Q8_0 case:
   ```
   python -m speech_aware_evidence_acquisition.e0.generate runtime \
       --runtime-root ~ \
       --model-lock-key qwen3-omni-30b-a3b-instruct-gguf-q4km \
       --out docs/receipts/runtime-q4km.json
   ```
   Neither flag was passed by any existing caller, so the default (Q8_0,
   `docs/receipts/runtime.json`) is byte-for-byte unaffected.

5. **Tests** (synthetic fixtures only, TDD): a non-default `model_lock_key`
   resolving a completely separate, synthetic umbrella-lock model entry
   (`tests/unit/test_e0_generators.py`); the CLI's new flags writing a named
   receipt to a named path without touching the default
   (`test_cli_runtime_command_writes_a_named_receipt_for_a_named_model`);
   receipt-path default/explicit/malformed resolution and the `config_hash`
   change it produces through the real `compose()` pipeline
   (`tests/unit/test_config_composition.py`); the real committed
   `qwen3-omni-llamacpp-q4km.json` fragment composing correctly with an
   existing dataset/baseline/experiment fragment
   (`test_q4km_repo_fragment_composes_with_the_expected_runtime_selection`);
   `FrozenCoreGate.for_study_repo`'s new parameter, and end-to-end fail-closed
   wiring through both `saea-driver smoke` (non-dry-run) and `saea-driver run`
   when the composed model names a receipt file that does not exist
   (`tests/unit/test_runtime_receipt_selection.py`,
   `tests/unit/test_driver_smoke.py`).

## What this change deliberately does NOT do

`contracts/gate_runtime.py::_RuntimeValidationMixin._validate_runtime` still
asserts the receipt's `model_lock_key` equals the single frozen
`contracts.MODEL_LOCK_KEY` constant (the Q8_0 key), unconditionally:

```python
if runtime["model_lock_key"] != MODEL_LOCK_KEY:
    raise GateClosed(...)
```

A Q4_K_M receipt's `model_lock_key` will legitimately be a *different* string
(it must name the Q4_K_M model's own umbrella-lock entry — see below), so a
real `FrozenCoreGate.assert_model_touch_allowed` call against
`docs/receipts/runtime-q4km.json` will currently be **refused at this check**,
even after the receipt itself is truthfully built and the umbrella lock entry
exists. This is intentional, not an oversight: widening the frozen-core
identity boundary to accept a second model is a materially different,
security-relevant change to `contracts/` (the D1–D4 / gate-runtime enforcement
surface), distinct from the receipt/config plumbing this task was scoped to,
and it was not part of the six deliverables this task specified. It needs its
own explicit review before landing — most naturally as a small, isolated
follow-up (thread a `model_lock_key` field through `FrozenCoreGate` itself,
defaulting to the current constant so every existing call site is unaffected,
exactly the same pattern already used here for `runtime_receipt_relpath`).
Until that lands, this change makes it possible to **build and select** a
second receipt with full identity verification of its own bytes
(`build_runtime_receipt` genuinely re-hashes whatever `model_lock_key` it is
given), but a live gate-enforced model touch against the Q4_K_M receipt is not
yet authorized by `contracts.FrozenCoreGate` as shipped.

## Operator sequence (WSL, speechrl venv, from the study repo root)

None of the steps below were run by this change. Steps 1 and 3 are the
operator's; step 2 is **owner-authority only** — this change does not, and
must not, edit `docs/datasets.lock.json` (the umbrella lock lives outside this
repository and is a shared, program-level asset).

### 1. Materialize the Q4_K_M files in their OWN directory

The Q4_K_M GGUF currently sits inside the existing Q8_0 directory
(`$SPEECHRL_DATA_DIR/models/qwen3-omni-30b-a3b-instruct-gguf/`) — that
placement is temporary and wrong for this design, because
`build_runtime_receipt` requires the resolved model directory to contain
**exactly** the lock entry's frozen file count and total byte count (extra
files make it fail closed). Move (or place, if using the official ggml-org
download instead of the local requant) the Q4_K_M GGUF **and a copy of the
mmproj bf16 file** into a new sibling directory:

```
$SPEECHRL_DATA_DIR/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/
    Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf
    mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf   # copy, not a move — the
                                                     # Q8_0 directory must keep
                                                     # its own copy untouched
```

The mmproj file must be a **copy**, not a symlink or a shared file across the
two directories: `build_runtime_receipt` and the gate both re-hash files by
their resolved path under `data_root`, and the exact-file-count/exact-byte-total
checks are per-directory — sharing one physical file between two "exactly
N files" directories works today (nothing currently forbids a hardlink or a
second copy at the byte level) but a symlink is refused elsewhere in this
codebase's identity checks on principle (dangling-symlink / non-regular-file
refusals throughout `contracts/`), so a plain copy is the only shape this
change was tested against and is the one to use. This repo never moves or
deletes files on disk — that is entirely the operator's action, outside any
tool call this task made.

### 2. OWNER adds the umbrella-lock entry (do NOT self-edit)

Draft snippet for `docs/datasets.lock.json`'s `models` array — every
`<PLACEHOLDER: ...>` must be filled from the ACTUAL materialized files (exact
byte counts measured after step 1, not estimated):

```json
{
  "name": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
  "kind": "model",
  "local_subdir": "models/qwen3-omni-30b-a3b-instruct-gguf-q4km",
  "source": {
    "kind": "hf-manual",
    "id": "<PLACEHOLDER: ggml-org/Qwen3-Omni-30B-A3B-Instruct-GGUF if the official ggml-org Q4_K_M download is used, OR a 'local-requant' kind + a note naming the exact requantization recipe/tool/commit if the locally-requantized copy is kept instead>"
  },
  "revision": "<PLACEHOLDER: 'unknown (no local metadata -- content-fingerprinted)' to match the Q8_0 entry's own convention, or the requant tool's own version/commit if locally produced>",
  "status": "COMPLETE",
  "size_h": "<PLACEHOLDER: e.g. '18.5G' -- human-readable, measured>",
  "size_bytes": "<PLACEHOLDER: exact sum of the Q4_K_M GGUF + copied mmproj bf16 file, in bytes -- this is the number build_runtime_receipt will check the materialized directory against, byte for byte>",
  "files": 2,
  "task": "-",
  "factor_family": "model",
  "note": "Q4_K_M GGUF + a COPY of the bf16 mmproj for llama.cpp -- fits entirely in 24 GB VRAM (-ngl 999, no CPU expert offload, unlike the Q8_0 -ngl 28 CPU-offload profile); own directory, separate from the Q8_0 pin (docs/readiness/2026-08-09-int4-model-identity.md)"
}
```

Notes on the placeholders: the umbrella lock's model entries carry no
per-file SHA-256 of their own (only `files`/`size_bytes`/`local_subdir` — the
existing Q8_0 entry has no `sha256` field either, since its `revision` is
already "content-fingerprinted"; a lock-level `sha256` field is only used
elsewhere in this lock for *download-verified* assets with a `filename`/`url`
pair). The Q4_K_M model's actual per-file SHA-256 identity is a
**study-level** artifact — it is what step 3's receipt-build command measures
and freezes, not something that belongs in the umbrella lock itself.

### 3. Build the receipt (after steps 1–2 both land)

```bash
cd studies/speech-aware-evidence-acquisition
source ~/.venvs/speechrl/bin/activate
PYTHONPATH=src python -m speech_aware_evidence_acquisition.e0.generate runtime \
    --runtime-root ~ \
    --model-lock-key qwen3-omni-30b-a3b-instruct-gguf-q4km \
    --out docs/receipts/runtime-q4km.json
```

This reuses the SAME llama.cpp checkout/binary/libraries already pinned by
`docs/receipts/runtime.json` (the launcher and its libraries are model-agnostic
— only `-m`/`--mmproj` change per model, both supplied at session-spawn time,
not baked into the receipt's `llama_cpp` block) — so no llama.cpp rebuild is
implied by this step alone; the command still fails closed exactly as the
Q8_0 path does today if the checked-out tree is dirty or the built binary's
self-reported version does not match `git rev-parse HEAD`. On success it
prints the written file's SHA-256, e.g.:

```
wrote docs/receipts/runtime-q4km.json sha256=<64-hex>
```

Commit `docs/receipts/runtime-q4km.json` once it is genuinely built from real
bytes — this task did not, and per its own instructions must not, generate
that file itself.

### 4. Still open after step 3 (owner review, separate from this task)

Widen `contracts/gate_runtime.py`'s `model_lock_key` equality check (see "What
this change deliberately does NOT do" above) before any real, gate-enforced
run against the Q4_K_M receipt can be attempted — until then, `saea-driver
smoke`/`run` against the `qwen3-omni-llamacpp-q4km` model fragment will
correctly load `docs/receipts/runtime-q4km.json` (this task's plumbing) but
will then be refused by the gate's still-single-key identity check (unchanged,
by design, in this task).
