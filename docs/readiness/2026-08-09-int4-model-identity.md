# INT4 (Q4_K_M) second-model identity: plumbing landed, gate widened, operator sequence

Status: engineering plumbing AND the gate-side identity check are both DONE
and unit-tested (synthetic fixtures only — no real Q4_K_M bytes touched, no
llama.cpp rebuild, no model run). The gap this document originally reported
open (the gate's `model_lock_key` equality check was hardcoded to a single
constant) is now CLOSED (2026-08-09, same-day follow-up) — see "CLOSED
(2026-08-09 follow-up): the gate now binds to the DECLARED model" below for
the exact new semantics. What remains is owner-authority (the umbrella lock
edit) and operator-authority (materializing the files, running the
receipt-build script). No model was touched to produce this document; no
receipt was regenerated.

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

6. **(2026-08-09 follow-up) Gate identity widening** — `contracts.
   FrozenCoreGate` gained `expected_model_lock_key` (default: the frozen
   `contracts.MODEL_LOCK_KEY`); `_validate_runtime`/`_lock_model_entry`
   (`gate_runtime.py`) now assert against that field instead of the bare
   module constant. `core/config.py::model_lock_key` resolves the composed
   config's own declared key (fail-closed on missing/malformed, no default —
   every model fragment already declares one); `core/driver/smoke.py::
   _cli_smoke` and `core/driver/cli.py::_cli_run` pass it to `FrozenCoreGate.
   for_study_repo` alongside `runtime_receipt_relpath`, both derived from the
   SAME composed config. See the dedicated section below for the exact
   cross-binding refusal semantics and its test coverage.

## CLOSED (2026-08-09 follow-up): the gate now binds to the DECLARED model

`contracts/gate_runtime.py::_RuntimeValidationMixin._validate_runtime` no
longer compares the receipt's `model_lock_key` against a single hardcoded
module constant. `contracts.FrozenCoreGate` gained a new, keyword-only,
dataclass field:

```python
expected_model_lock_key: str = MODEL_LOCK_KEY   # default: the frozen Q8_0 key
```

and both identity checks now assert against **that** value instead:

```python
# _validate_runtime (gate_runtime.py)
if runtime["model_lock_key"] != self.expected_model_lock_key:
    raise GateClosed(...)

# _lock_model_entry (gate_runtime.py) -- the umbrella-lock ENTRY lookup that
# backs the GGUF file-set/size check is bound to the SAME declared key, not
# independently hardcoded, so the byte-level check can never validate a
# receipt against the WRONG model's lock entry either.
for entry in models:
    if entry.get("name") == self.expected_model_lock_key: ...
```

`FrozenCoreGate.for_study_repo` (the one production constructor) takes the
matching keyword argument, `expected_model_lock_key`, defaulting to the same
frozen constant — every existing call site that omits it is byte-identical
to before this change. The two real callers,
`core/driver/smoke.py::_cli_smoke` and `core/driver/cli.py::_cli_run`, both
now pass `expected_model_lock_key=core.config.model_lock_key(composed.values)`
alongside the `runtime_receipt_relpath=core.config.runtime_receipt_relpath
(composed.values)` they already passed — **the identical composed config
selects both the receipt FILE and the identity EXPECTATION**, so a run can
never pair one model's config with a different model's receipt: whichever
model fragment a run names, that fragment's own `model_lock_key` is what the
gate checks the receipt against, and that fragment's own `runtime_receipt`
key is which file gets read. `core.config.model_lock_key` fails closed
(`ConfigError`) on a missing/malformed value — a model fragment MUST declare
its own `model_lock_key` (already true of every fragment in this repo; unlike
`runtime_receipt`, this key has no default).

**Cross-binding refusal semantics** (`tests/contract/
test_model_lock_key_binding.py`, both directions): a gate constructed with
`expected_model_lock_key=B` but handed a receipt whose own `model_lock_key`
is `A` is refused with `GateClosed("runtime receipt model_lock_key 'A' does
not match the model this run declares ('B')")` — before any byte is read
from either model's files. The reverse pairing (`expected_model_lock_key=A`
default, receipt says `B`) is refused with the identical message shape. A
receipt that DOES match the declared key still goes through every existing
byte-level check unchanged (GGUF size/hash, llama.cpp build binary, runtime
libraries) — the widening only concerns WHICH model identity is legitimate to
assert about, never HOW rigorously that identity is then verified. A receipt
naming a model with no corresponding umbrella-lock entry is refused by
`_lock_model_entry` with `"<key> not found in datasets lock"`, naming the
DECLARED key, not the Q8_0 default.

The **session** half of this identity boundary (`core/session`:
`start_session`/`attach_session`/`LlamaServerTransport`) needed no code
change and was already immune to this exact cross-binding failure mode by
construction: `verify_against_runtime_receipt`/`_pinned_binary`/
`_pinned_model_files` compare a `SessionReceipt` only against whichever
`runtime_receipt` mapping object the caller hands them — nothing there is
keyed by `model_lock_key` or any hardcoded model constant — and both real CLI
call sites load that mapping via `core.session.load_runtime_receipt(core
.config.resolve_runtime_receipt_path(repo_root, composed.values))`, the
identical composed-config-driven path used for the gate. A session started
(or attached) under one model's config therefore has no path to be verified
against a different model's receipt in the real CLI flow. Proved directly
(not merely argued) in `tests/unit/test_session.py`:
`test_a_q8_matching_session_is_refused_against_the_q4km_runtime_receipt` and
its reverse pairing — a session genuinely matching one pinned model's runtime
receipt is refused when re-verified against the other's, using realistic
Q8_0-vs-Q4_K_M subdirectory shapes.

This makes a live, gate-enforced INT4 run possible end to end (pending the
operator/owner steps below): a run naming the `qwen3-omni-llamacpp-q4km`
model fragment resolves `receipts/runtime-q4km.json`, opens the gate with
`expected_model_lock_key="qwen3-omni-30b-a3b-instruct-gguf-q4km"`, and — once
that receipt is genuinely built from real, materialized Q4_K_M bytes (step 3
below) — passes every check the Q8_0 path always has, on its own model
identity.

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

### 4. CLOSED (2026-08-09 follow-up) — no longer open

The gate's `model_lock_key` equality check is now widened (see "CLOSED
(2026-08-09 follow-up)" above): `saea-driver smoke`/`run` against the
`qwen3-omni-llamacpp-q4km` model fragment correctly loads
`docs/receipts/runtime-q4km.json` (this task's original plumbing) AND opens
the gate against it, because the same fragment's `model_lock_key` field
(`"qwen3-omni-30b-a3b-instruct-gguf-q4km"`, already present in the committed
`configs/model/qwen3-omni-llamacpp-q4km.json`) now flows into
`FrozenCoreGate.for_study_repo(..., expected_model_lock_key=...)` at both
call sites. Nothing further is needed in `contracts/` for the identity
boundary itself. What remains open is exactly steps 1–3 above: materialize
the real Q4_K_M bytes, get the owner to add the umbrella-lock entry, and run
the receipt-build command against real files — none of which this or the
prior follow-up task performed.
