# Owner decisions pending

Explicit scope items this repository's implementers cannot resolve on their own authority.
Per-item disposition (accept, defer with a dated amendment, or reject) is an owner action; this
file only records what is open and why. See design spec §6
(`docs/superpowers/specs/2026-08-05-saea-r0-repair-trust-boundary-design.md`, umbrella) for the
governing framing.

## Owner disposition 2026-08-07 (in-session directive)

The owner accepted the two items put to them at the close of the R0 repair campaign:

1. **Entity/QA scorer adapters are OUT of R0 scope** (item 1 below). They stay unregistered; the
   format decisions listed there remain for a later readiness memo. No adapter is to be faked.
2. **The residual boundaries are accepted as R0 boundaries** — specifically: (a) the run bundle is a
   self-consistency check, not an authenticity proof (a writer with run-directory access can forge a
   coherent, finalizable bundle, because raw response bytes are not persisted and the chain has no
   external anchor); (b) the GGUF cheap-identity fast path cannot detect an in-place byte
   replacement that preserves size and mtime.

**Interpretation note (recorded because the directive was terse):** "前两项接受" is read as accepting
the *proposed dispositions* — defer entity/QA out of R0, and accept (a) and (b) as boundaries. If the
owner instead intended entity/QA adapters to be built inside R0, that is the opposite of what is
recorded here and should be corrected before the fresh third-party review consumes this file.

Still open and NOT covered by this disposition: R0.3 (`SAEA-E-001`) execution authority, which has
not been granted; no model touch has occurred.

## 1. Entity/QA scorer adapters (R0 repair T8, invariant I8 partial)

**Status:** not registered. `core/scorers.py` registers `asr-wer` and `cost` only.
`scoring/entity.py` (`score_entities`) and `scoring/qa.py` (`qa_exact_match`, `qa_token_f1`) remain
frozen, hash-pinned pure functions with no adapter wiring them to a reference layer through the
`SCORERS` registry.

**Why no adapter was written (do not fake one):**

- **Entity.** A reference layer *exists on disk* for `earnings21-original` (and the ConEC
  Earnings21 side): `transcripts/wer_tags/<sample_id>.wer_tag.json` plus the `.nlp` file's own
  `wer_tags` column (inspected locally under `SPEECHRL_DATA_DIR`; no content committed by this
  task). Freezing an adapter over it requires resolving three format decisions this task has no
  authority to make unilaterally:
  1. the `.nlp` file's `wer_tags` column is **Python-repr list syntax** (e.g. `['0', '1', '6']`),
     not JSON — parsing it needs a decision (regex vs. `ast.literal_eval`) that becomes part of
     the frozen scoring contract, not an implementation detail;
  2. an entity ID can label **multiple, not-necessarily-contiguous** tokens (README:
     "Entities can be comprised of single and multiple tokens... only one entity can be labeled
     with any given ID") — grouping token spans into one entity mention needs a specified,
     hash-pinned algorithm, exactly the kind of decision E0 D3 froze for WER/entity/QA
     normalization and that a later, unreviewed choice should not quietly make;
  3. `scoring.entity.score_entities(expected, predicted)` takes flat entity **strings**; whether
     the expected-side string is the entity mention text, the `entity_type` label, or a
     `"{type}:{text}"` composite is itself a scoring-contract decision;
  4. only `earnings21-original` (and ConEC's Earnings21 side) carries this layer at all —
     `earnings22-original`'s `data/identity.py` layers have no `wer_tags` entry, so any adapter
     would start carrier-scoped, another explicit-scope decision.

  This is not a new finding: `.superpowers/sdd/2026-08-05-speech-aware-evidence-acquisition-r0-vertical-slice/task-14-brief.md`
  already named "entity/QA reference extraction from `wer_tags`/ConEC annotations" as a known,
  intentional deferral pending a **readiness memo that pins the format** — that memo was never
  written. The R0 repair design spec (`docs/superpowers/specs/2026-08-05-saea-r0-repair-trust-boundary-design.md`
  §6.1, umbrella) independently lists "entity/QA scorer adapter 是否属于 R0 交付（其参考层格式尚未冻结）"
  as an owner-disposition item, not an implementer one.
- **QA.** No spoken-QA reference layer is wired into this study at all. `data/identity.py` defines
  no QA layer for any carrier. `slue-sqa-5` and `contextasr-bench` (the secondary carriers named in
  `docs/engineering.md`) do exist as raw acquired bytes under `SPEECHRL_DATA_DIR/datasets/` (Parquet
  files for `slue-sqa-5`, inspected locally for file presence only), but neither has a carrier
  loader, an identity layer, nor any per-sample reference format ever specified in this repository.
  Registering a QA adapter would mean inventing a new carrier's reference contract from scratch,
  which is new-experiment-shaped work, not a scorer-seam wiring task.

**What was inspected (format discovery only, per task-8 brief; no dataset content committed):**
`transcripts/wer_tags/*.wer_tag.json` structure and one sample's parsed keys/values under
`earnings21-original`; the `.nlp` file header and `wer_tags`/`tags` column values for the same
sample; `datasets/earnings21-22/earnings21/README.md`'s own file-format documentation (entity ID
semantics, multi-token entities); `datasets/conec/README.md`'s directory layout; the presence and
top-level layout of `datasets/slue-sqa-5/` and `datasets/contextasr-bench/`.

**Requested disposition:** either (a) commission a readiness memo that pins the entity reference
format (parse rule for the `wer_tags` column, span-grouping rule, and the string a scorer compares)
so a later task can implement `core.scorers` adapters against a frozen contract, explicitly scoped
to `earnings21-original` first; or (b) accept that entity/QA scoring is out of scope for R0 and
defer it to R1 or later, recorded as a deviation rather than silently absent.

**Addendum 2026-08-13 (owner decision D-3): the ENTITY half is resolved and wired.** The three
format decisions above are now pinned, implemented in `data.carriers.EntityLayout`/
`data.references.reference_entity_mentions`, and registered as the `entity-wer` scorer in
`core.scorers.score_entity_wer_outputs` (`core.base.SCORERS`), usable both in-run and offline/deferred
(`scripts/score_entity_wer.py` / `speech_aware_evidence_acquisition.analysis.entity_wer_offline`):

1. the `.nlp` file's `wer_tags` column is parsed with `ast.literal_eval` (a Python literal, refused if
   it is not a list of strings).
2. an entity ID's member tokens are grouped in reference order, never assumed contiguous.
3. `scoring.entity.score_entities` compares the entity MENTION TEXT (raw reference tokens joined by a
   space, normalized internally by the frozen `normalize_text_v1` every other scorer already uses) —
   never the `entity_type` label or a composite; `entity_type` is carried alongside as metadata for
   the per-class breakdown, unchanged from the frozen module's own contract.
4. scope is exactly `data.carriers.entity_scoped_carrier_lock_keys()` — today, `earnings21-original`
   only (`earnings22-original` has no `wer_tags` layer at all, E0 D1); a row naming any other carrier
   fails closed.

`entity_wer := 1 - recall` (0.0 when a sample/class has no gold entities, not `EntityScore.recall`'s
own 0.0-when-empty convention run through `1 - recall`, which would misleadingly read as a 100% error
rate). The `entity-wer`-reads-the-`.nlp`-file reference-identity re-check (IMPORTANT 2, IMPORTANT
list item 5 below) was widened to cover `entity-wer` alongside `asr-wer` in
`core.scorers._assert_scoring_entry_gate`. **Not extended by this addendum:** the `wer_tags` sidecar
(`<id>.wer_tag.json`) itself carries NO D1-identity re-verification at scoring time (unlike the
`.nlp` file it sits beside) — `contracts.FrozenCoreGate.verify_reference_identity` was not touched,
scoped deliberately to keep this addition to `core.scorers.py`/`data.*` and out of the
security-critical gate; a future task that wants that coverage needs a `d1_layer_key`-style fact on
`EntityLayout` and a `contracts.py` change, an owner-level decision given what it changes about this
study's trust boundary. QA remains unregistered exactly as recorded above; nothing in this addendum
changes that.

## 2. GPU/CPU/peak-VRAM cost accounting (design spec §6.2, I8) — engineering closed by T7

T8 (above) restated this as open. R0 repair T7 (`core/resources.py`, `core/model.py`,
`core/driver.py`, `core/bundle.py`) closes it by *measured sampling*, per the design spec's
commitment, not by deferral:

- **GPU-seconds / peak VRAM MiB:** `core.resources.NvidiaSmiSampler` polls
  `nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits` on a background
  thread (fixed interval, default 1s) from `core.driver.run_experiment`, accumulating a
  utilization-weighted GPU-seconds figure and the peak reported VRAM. `core.driver._cli_run` (the
  live-run CLI entry point) is the ONLY call site that resolves a real sampler
  (`core.resources.resolve_resource_sampler`); every other caller — library code, every test — gets
  `run_experiment`'s own no-op `NullSampler` default, so no test can be surprised into shelling out to
  a real GPU tool. **Deviation, machine-conditional, not a design gap:** on any machine where
  `nvidia-smi` is not on `PATH` (or fails at poll time), the run's cost block carries the literal
  `NOT_AVAILABLE` for `gpu_seconds`/`peak_vram_mib` plus a `gpu_sampling_reason` string — this is the
  owner-accepted fallback the design spec anticipated (§6.2), not a silent omission; no further owner
  action is required per run, only awareness that a GPU-less or `nvidia-smi`-less environment degrades
  automatically rather than failing the run.
- **CPU-seconds:** `core.resources.cpu_seconds_snapshot` (`os.times()`, process + children,
  user + system) sampled at the start and end of `run_experiment`; always measured, never
  NOT_AVAILABLE (`os.times()` is stdlib and cross-platform, including Windows, where the children
  fields simply read 0.0 — a platform fact, not a sampling failure).
- **Evidence volume:** `supplied_evidence_bytes` / `admitted_evidence_bytes`, aggregated in
  `run_experiment` from the same per-sample `supply_content_bytes` figure already computed for the
  SUPPLY trace record; "admitted" narrows to samples the policy actually admitted
  (`SampleOutcome.admitted`) — R0's only policy (`FixedPolicy`) always admits, so the two totals
  coincide today; the split exists for a future rejecting policy (e.g. X3).
- **Tool calls:** `FrozenCoreAdapter.record_tool_call()` / `cost_summary()["tool_calls"]` — zero
  today (no registered tool-using policy), wired through the adapter every `SampleContext` already
  carries so a future policy increments the existing choke point rather than inventing a new one.
- **Gate/setup latency:** `gate_setup_seconds`, wall-clock time in `run_experiment` from function
  entry through split/carrier/evidence resolution and `FrozenCoreAdapter` construction (gate check +
  attempt reservation included), before the per-sample request loop starts.
- **Failed-attempt cost:** `failed_attempt_calls` / `failed_attempt_audio_seconds`, summed via
  `core.attempts.AttemptStore.actual_usage_in_states` over sibling attempts under the same `run_id`
  that are (as of manifest time) `ABORTED`, excluding the reporting attempt's own spend. Present on
  BOTH a successful run's `RunResult.cost` and a failed run's own best-effort `core.bundle`-built
  ABORTED-manifest cost block (`core.bundle._best_effort_cost_for_aborted_attempt`) — an ABORTED
  manifest never carries `cost=None` after T7; fields that genuinely cannot be recovered post-hoc
  (latency/tokens/tool_calls/cpu/gpu/evidence/gate_setup — the in-memory adapter/sampler state a
  failed `run_experiment` call never returns) are the literal `NOT_AVAILABLE` with a shared
  `cost_unavailable_reason` string, never a silent omission.

**Two disclosed, bounded approximations in the GPU sampler (T7 fix round, not new deviations requiring
disposition — documented for completeness):** (1) `gpu_seconds` undercounts by at most one polling
interval (default 1.0s) since the final partial span before `stop()` is never recorded — a coarse
instrumentation figure measured in GPU-*hours*, not a precise billing meter (no numeric GPU-hours
ceiling is enforced since the 2026-08-06 owner amendment retired the first-slice caps,
`SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS`; the undercount's negligibility no longer rests on any
specific hour bound); (2) `gpu_seconds`/`peak_vram_mib` are `nvidia-smi`'s DEVICE-wide totals, not
this run's process-scoped share; `device_index` (default `0`) pins which device is queried but does
not add per-process attribution — correct for this study's documented single-GPU dev box. See
`core/resources.py`'s module docstring for the full rationale.

**Manifest schema decision:** `RUN_MANIFEST_SCHEMA` stays `saea-run-manifest-v1` (no version bump).
`core.bundle.verify_bundle` performs no fixed-key-set check on the `cost` block (only
`core.scorers.score_cost_outputs` requires it be a non-empty dict, itself with no key-set check
either), so a manifest built before T7 (the old 5-field cost shape) still verifies and still scores
end to end — proved by `tests/unit/test_bundle.py::test_verify_bundle_accepts_a_pre_t7_five_field_cost_shape`.

This item's original ask was two-part: (a) implement measured sampling rather than deferring it, and
(b) if sampling is genuinely unavailable on a given machine, the owner must accept that as a
deviation rather than the implementer silently deciding it. Part (a) is now delivered exactly as
design spec §6.2 already specified. Part (b) is satisfied structurally, not by a fresh ad-hoc
decision here: every NOT_AVAILABLE occurrence is machine-conditional (missing/failing `nvidia-smi`
on whichever machine runs a given attempt), self-documenting (a `gpu_sampling_reason` /
`cost_unavailable_reason` string travels with every occurrence, in the run manifest itself), and
falls back automatically rather than failing the run — the exact shape §6.2 pre-authorized. No NEW
owner decision is required beyond that pre-authorization; this record stays here as the audit trail
of it being fulfilled, not as a still-open question blocking anything.

## 3. R0.3 `SAEA-E-001` execution authorization

Restated for visibility (design spec §6.3): R0.3 smoke and R1 do not start before the fresh
independent re-review passes and the owner has acted on items 1–2 above.

## 4. I-4 media identity: audio-seconds plausibility bound is not an exact re-derivation

**Status:** closed at a documented, bounded level; residue recorded here rather than silently
narrowed (external-threat-model review, R0 repair round).

**What is now bound.** At model-touch time (`core.model.FrozenCoreAdapter` construction,
`contracts.FrozenCoreGate.verify_media_identity`), for EXACTLY the samples the run's verified split
can touch: (a) the live media file's re-measured (size, SHA-256) is checked against D1's own frozen
per-sample facts (`docs/receipts/artifacts/d1-identity.json`) — a substituted `.mp3` is refused; (b)
the loader-reported, CSV-derived `audio_seconds` (the figure this run's own plan and its
pre-registered exposure-ledger row are cross-checked against — no numeric ceiling since the
2026-08-06 owner amendment, `SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS`, retired the first-slice
caps) must imply a plausible MP3 bitrate against that SAME frozen byte size (4-512 kbps, widened
past the 16-320 kbps empirically observed across all 44 earnings21 and all 125 earnings22 real
samples). Full-carrier re-hash (~770 MB) on every gate open was measured and rejected as needlessly
slow relative to what a bounded first-slice run can ever touch (today's dev/discovery splits: 10-44
samples); re-hashing exactly the run's split scales with what the run can actually send instead.

**What is NOT bound, and cannot be from what E0 D1 already closed over.** D1 records per-file byte
size and SHA-256 for media, and the SET of sample ids each metadata CSV names — it never captured the
metadata CSV's own numeric field VALUES (`audio_length`, `File Length (seconds)`) at closure time, so
there is no frozen "correct" duration to compare a live CSV cell against exactly. The plausibility
bound above therefore catches only a GROSS manipulation (any edit implying a bitrate outside
[4, 512] kbps — the demonstrated attack, 4422s edited to 0.044s, misses this band by roughly six
orders of magnitude) — a MODEST, precise edit that keeps the implied bitrate inside the band (e.g.
4422s edited to 3000s) is not detected by this check. Exactly re-deriving true audio duration would
require decoding the MP3 stream (frame-header parsing or an audio-library dependency), which is out
of scope for this hardening pass (`contracts.py` is deliberately stdlib-only, module docstring; the
package declares zero runtime dependencies, `pyproject.toml`).

**Requested disposition:** accept the plausibility bound as R0's closure level (the residue is a
narrow, bounded, machine-conditional gap — not an unbounded one) and defer exact duration
re-derivation to whichever future task first needs audio decoding for another reason (e.g. a scorer
or evidence-source adapter), rather than adding a new dependency solely for this check now.

## 5. IMPORTANT 2 (fix-wave3, external-threat-model review round 3): reference-identity carrier coverage

**Status:** closed at a documented, bounded level — `contracts.FrozenCoreGate.verify_reference_identity`
re-hashes the `.nlp` reference bytes `data.references.reference_tokens` reads, against D1's frozen
per-file identity, for exactly `_REFERENCE_SCOPED_CARRIER_LOCK_KEYS = {"earnings21-original",
"earnings22-original"}` — the same two carriers `data.references._NLP_SUBDIR` (and therefore
`reference_tokens` itself) supports today. Wired into `core.scorers._assert_scoring_entry_gate`,
scoped to exactly the bundle's own verified split, and runs only when `asr-wer` is among the
manifest's configured scorers (the only scorer that reads a reference layer at all).

**What is NOT bound, and why.** `conec` carries no reference layer `reference_tokens` can read at
all (its D1 identity layer is named `e21_nlp_references`, a DIFFERENT key with DIFFERENTLY-hashed
bytes than earnings21-original's own `nlp_references` — same D1 receipt, distinct file set) — scoring
conec was never reachable through `reference_tokens` before this fix, and `verify_reference_identity`
correctly fails closed for it (any carrier outside the scoped set refuses) rather than silently
reusing earnings21's facts or silently skipping the check. Should a future task register a conec-aware
scorer adapter that DOES read `e21_nlp_references`, `_REFERENCE_SCOPED_CARRIER_LOCK_KEYS` (contracts.py)
and `_NLP_SUBDIR` (data/references.py) both need a coordinated update — an owner-level decision, not an
implementer one, since it changes what this study's formal scoring path is allowed to touch.

**Requested disposition:** accept the current two-carrier scope as R0's closure level; revisit only if
and when a conec-aware or other-carrier reference adapter is ever registered.

## 6. MINOR 2 (fix-wave3, external-threat-model review round 3): ledger cells bound to shape, not full re-derivation

**Status:** partially closed. `core.bundle.verify_bundle` now genuinely CHECKS three manifest cells
`core.tracking.bundle_ledger_cells`/`ledger_row_for_bundle` treat as machine-derived (refusing any
hand-supplied cell that disagrees) — previously all three were asserted, not derived, so any
self-consistent-LOOKING value passed unconditionally:

- **`study_commit`** — now shape-validated: a genuine 40-hex git commit, or the ABORTED-only
  `UNAVAILABLE:<non-empty reason>` marker (a COMPLETED manifest may never carry the latter — checked
  independently, unchanged from the existing T6 fix-2 round behavior).
- **`config.config_hash`** — now shape-validated: a genuine 64-hex SHA-256.
- **`scorers`** — now bound to the real `core.base.SCORERS` registry: a non-empty list of non-empty
  strings, every one of which names a scorer `core.scorers` actually registered.

**What is NOT bound, and why.** None of the three is fully RE-DERIVED from independent ground truth:

- `study_commit` is not re-verified against a live `git rev-parse HEAD` — a manifest legitimately
  outlives the commit it was built against (the study repo moves on), so `verify_bundle` cannot
  meaningfully re-run `git` at verify time the way it re-hashes artifact bytes. A well-SHAPED but
  factually wrong 40-hex value is not caught.
- `config.config_hash` is not re-derived from the four named config fragments' actual file contents.
  Genuine re-derivation requires calling `core.config.compose(repo_root, ...)` again, which needs
  `repo_root` (a parameter `verify_bundle` does not take today — it takes only a manifest path,
  by design, per its own docstring) AND the real `configs/<kind>/<name>.json` files on disk under
  that root. This study's own test suite (`tests/unit/test_bundle.py`, ~30 call sites) deliberately
  builds manifests against SYNTHETIC fragment names ("m"/"d"/"b"/"e") that name no real file on
  disk — full re-derivation would therefore require either a broad, disproportionate-to-a-Minor-
  finding test-fixture migration (real config fragment files for every synthetic `repo_root` these
  tests already use) or giving `verify_bundle` a new `repo_root` parameter with per-call-site
  opt-in, both deferred here as out of scope for this fix wave.
- `scorers` is bound to "every named scorer is registered", not to "matches what the composed config
  actually declared for this arm/experiment" — the same `compose()`/`repo_root` access gap as
  `config_hash` above. A manifest whose scorers were legitimately (or maliciously) trimmed to omit
  the task metric (e.g. `["cost"]` alone for a bundle whose real experiment config declared
  `["asr-wer", "cost"]`) still verifies; only a scorer NAME core.scorers never registered is refused.
  A blanket "must include asr-wer" rule was deliberately NOT added: `["cost"]`-only bundles are an
  existing, legitimate, already-tested configuration (T8's cost scorer exists as a standalone metric),
  so refusing them here would contradict established, accepted behavior rather than close a gap.

**Requested disposition:** accept shape-validation as this fix wave's closure level for all three
cells (a genuine improvement over "any string passes" — the demonstrated `["cost"]`-only-bundle
concern is narrowed to "the artifact hashes cell is honestly what was computed," never eliminated
outright); defer full config-fragment re-derivation to a task that also budgets the test-fixture
migration it requires, or to a design change that binds config-fragment CONTENT hashes into the
manifest at build time (so `verify_bundle` could re-derive without filesystem access to `configs/`).

## 7. GGUF cheap-identity fast path (R0 repair perf, 2026-08-06) — accepted, owner-approved scope reduction

**Status:** closed at a documented, bounded level; accepted rather than left as a silent
narrowing (owner instruction 2026-08-06: "stop re-hashing the 34.7 GB GGUF model set on every gate
open").

**What changed.** `FrozenCoreGate._validate_runtime` (`contracts.py`) previously re-hashed every
GGUF file from bytes on EVERY gate open — measured 142–175s per call in WSL2 over the 9p mount onto
the Windows-hosted `SPEECHRL_DATA_DIR`, run on every `scripts/reproduce.sh` dry run and every real
run. It now defaults to a cheap-identity check per GGUF file — absolute path, byte size,
`st_mtime_ns`, and OS file identity (`st_ino`/`st_dev` via Python's own `os.stat()`; on Windows
CPython already populates these from the NTFS file ID via `GetFileInformationByHandle` — verified
empirically stable and non-zero on this checkout, so no separate `ctypes`/`nFileIndex` path was
needed) — against a cache at `<SPEECHRL_DATA_DIR>/.saea-runtime-identity-cache.json` (never
committed, outside the repo, bound to the runtime receipt's own SHA-256 so a changed receipt
invalidates it outright). A full SHA-256 re-hash of the GGUF set still runs whenever: any
cheap-identity field differs from the cached record, a cache record is missing/corrupt/malformed
(fail-safe — a bad cache is treated as absent, never trusted), the runtime receipt itself changed,
the caller explicitly requests it (`full_hash=True`, or `RUNTIME_FULL_HASH_ENV`/
`scripts/reproduce.sh --full`), or — the gate's own default when no explicit choice is made — this
is the first gate open of the current process for a given runtime-receipt identity (a real model
touch, `core.model.FrozenCoreAdapter`, never overrides `full_hash` and therefore always pays this
floor cost at least once per session before it can ever be fast-pathed). Runtime libraries under
`build/bin` and the llama.cpp launcher binary are UNCHANGED: always fully re-hashed from bytes,
unconditionally, every gate open (~249 MB total — cheap, and it is the code that actually runs).
Every other check the gate performs (E0 closure, the D3 scoring freeze, exposure
pre-registration, carrier scope, the llama.cpp build binary, runtime libraries) is unconditionally
re-verified from scratch on every call regardless of the GGUF identity cache.

**What is NOT bound, and why — the accepted residual weakness.** Stated precisely, not overstated:
the fast path defends against a WRONG, PARTIAL, or ACCIDENTALLY-REPLACED model set — a different
file swapped in, a truncated or resumed download, a stale/foreign `SPEECHRL_DATA_DIR`. It does NOT
defend against an adversary who edits a GGUF file's bytes in place while deliberately preserving
its size, last-modified time and OS file identity (e.g. `open(path, "r+b")` followed by
`os.utime()` restoring the original timestamp) — that specific tamper is silently accepted by the
fast path. This is a genuine, accepted, owner-approved narrowing of what "the gate verified the
model bytes" means for the common case, not an oversight: it is pinned by an explicit test
(`tests/contract/test_runtime_identity_fastpath.py::
test_bytes_replaced_same_size_and_mtime_restored_is_the_documented_residual_weakness`), not left as
prose alone, and the authoritative full SHA-256 check (`full_hash=True` /
`scripts/reproduce.sh --full`) remains available and unconditionally correct whenever this residual
gap matters (e.g. immediately before a real model touch on a machine whose provenance is not
already trusted).

**Requested disposition:** accept the cheap-identity fast path, and the residual weakness it
leaves, as R0's closure level for this perf fix (owner instruction 2026-08-06 already authorizes
this scope reduction); revisit only if a future task needs a stronger per-file tamper guarantee
than size/mtime/file-id (e.g. a periodic background full re-hash, or an external attestation of the
asset fetch) cheaper than re-hashing 34.7 GB on every gate open.

## 8. IMPORTANT 1 (fix-wave4, external-threat-model review round 4): evidence-identity carrier coverage and negative-control scoping

**Status:** closed at a documented, bounded level -- `contracts.FrozenCoreGate.verify_evidence_identity`
re-hashes the evidence bytes `core.evidence._conec_contexts` reads, against D1's frozen per-file
identity (`docs/receipts/artifacts/d1-identity.json`, `conec.layers.e21_contexts`), for exactly the
sample ids a run's own evidence source supplied non-empty evidence for. Wired into
`core.model.lifecycle._AttemptLifecycleMixin._open_gate_and_attempt` alongside the pre-existing
media-identity rail (I-4) -- both re-verified at `FrozenCoreAdapter` construction, before any model
touch. Scoring does not read evidence today (`core.scorers` imports only `data.references`, never
`core.evidence`), so unlike the reference-identity rail there is no second call site inside
`core.scorers._assert_scoring_entry_gate` to wire yet; if a future scorer ever reads evidence, that
call site needs the same treatment `_assert_scoring_entry_gate` already gives references.

**What is bound.** The evidence layer's location is derived entirely from `carrier_lock_key`'s own
`data.carriers.CarrierDescriptor.evidence` (an `EvidenceLayout`: lock key, subdir, extension, AND the
new `d1_layer_key` field this fix adds -- `e21_contexts` is not derivable from `subdir` by any fixed
rule, unlike the reference layer's `nlp_references` key, which happens to equal its subdir's last
segment for both registered carriers today). A carrier whose descriptor declares no evidence layer at
all (`descriptor.evidence is None` -- today `earnings22-original`, whose ConEC contexts are a
different-shaped, never-read per-call-PDF layer) fails closed inside `verify_evidence_identity` itself,
independent of `core.evidence._conec_contexts`'s own pre-existing internal refusal for the same case --
so a future evidence source that forgets that internal check is still caught by the gate.

**Deliberate scoping decision: identity is verified BEFORE `evidence_mismatch`/`rotated_mismatch`.**
`core.driver.run_experiment` builds the gate's `evidence_relpaths` facts from the evidence source's
ORIGINAL, pre-rotation output -- i.e. "sample X's own evidence source call produced genuine,
D1-identity-matching bytes" -- and only afterward, if the config sets `evidence_mismatch: true`, does
`rotated_mismatch` reassign that already-verified content to a DIFFERENT sample id for the negative
control. The alternative (verifying identity against whichever sample ultimately RECEIVES the content,
post-rotation) was rejected: `rotated_mismatch` is an intentional, in-process reassignment of genuine
D1-tracked bytes for a scoring probe, not a tampering attack, and re-deriving "sample id -> relpath"
naively per RECEIVING sample after rotation would check the WRONG (the receiving sample's own, untouched)
file instead of the file whose bytes were actually supplied -- silently verifying something other than
what left the process. Checking pre-rotation instead verifies the byte-integrity of the evidence CORPUS
the run's evidence source drew from, which is the property IMPORTANT 1 is actually about (a tampered
on-disk context file), and composes correctly regardless of whether `evidence_mismatch` is set.

**What is NOT bound, and why.** `earnings22-original` has no evidence-identity coverage because it has
no evidence layer to cover: `_conec_contexts` has never read Earnings22's ConEC contexts (a different,
per-call PDF-packet shape), so no config can legitimately supply earnings22 evidence today regardless of
this rail. Should a future task register an earnings22-aware (or other-carrier) evidence source, its
`CarrierDescriptor.evidence` needs a matching `EvidenceLayout` (including a genuine `d1_layer_key` D1
records) before `verify_evidence_identity` can cover it -- an owner-level decision if it changes what
this study's runtime is allowed to read, not an implementer one.

**Requested disposition:** accept the current earnings21-original-only evidence-identity coverage, and
the pre-rotation scoping decision above, as this fix wave's closure level; revisit only if and when an
earnings22-aware (or other-carrier) evidence source is ever registered.
