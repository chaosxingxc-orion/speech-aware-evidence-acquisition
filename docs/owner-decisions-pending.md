# Owner decisions pending

Explicit scope items this repository's implementers cannot resolve on their own authority.
Per-item disposition (accept, defer with a dated amendment, or reject) is an owner action; this
file only records what is open and why. See design spec §6
(`docs/superpowers/specs/2026-08-05-saea-r0-repair-trust-boundary-design.md`, umbrella) for the
governing framing.

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
interval (default 1.0s) since the final partial span before `stop()` is never recorded — negligible
against a first-slice budget measured in GPU-*hours* (≤40h); (2) `gpu_seconds`/`peak_vram_mib` are
`nvidia-smi`'s DEVICE-wide totals, not this run's process-scoped share; `device_index` (default `0`)
pins which device is queried but does not add per-process attribution — correct for this study's
documented single-GPU dev box. See `core/resources.py`'s module docstring for the full rationale.

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
