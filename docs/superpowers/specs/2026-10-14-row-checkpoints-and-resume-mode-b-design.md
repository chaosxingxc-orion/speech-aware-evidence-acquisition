# Row checkpoints and resume mode B — design (owner decision 309, 2026-10-14)

Decision 309: "our ability to recover an interrupted experiment is far too weak — rectify it
systematically." This note records the defect, the design that closes it, the invariants it keeps and
what it refuses. Implementation: `core/row_checkpoint.py`, `core/flight/resume.py`
(`CheckpointPredecessor`, `read_checkpoint_predecessor`), `core/flight/runtime.py`
(`_attach_row_checkpoint`, `_checkpoint_row`, `_seal_row_checkpoint`), `rails/runner.py`
(`on_outcome`), `core/bundle/{manifest,outputs,verify}.py`, `contracts/gate_exposure.py`.

## 1. The defect

The NX-T R1 column attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-v1`
ran 12:18Z–15:29Z on 2026-10-14 (1,204 contacts, about 120 rows) and died in a Windows Update restart.
Its directory held only the session-attach receipt; its attempt record read OPENED. Mode A resume
(`core/flight/resume.py`) replays a predecessor TRACE, and there was none: about 3 GPU-h were lost and
a 30 GPU-h flight was exposed to total loss.

Why nothing reached disk (line numbers at base commit `77e6b9ee8`):

1. Every contact's trace records go into a per-node in-memory `TraceBuffer`
   (`rails/runner.py:7001-7002`, bound through `set_current_trace_buffer` at `7145-7154`), merged into
   one per-row buffer when the row settles (`6239-6241`, `7168-7172`), held in the row's
   `_AgentRuntimeOutcome.trace_buffer` (`6603`, `7303-7316`).
2. `_run_agent_openjiuwen` returns its outcomes only after EVERY row settled (`6946`, `7423-7425`), and
   only then does `run_speech_native_agent_loop` emit the gold-free runtime records and
   `flush_into` the trace sink (`8102-8121`). The only earlier flush is the exception path
   (`_flush_agent_state_traces`, `6638-6644`, `6936-6942`, `7380-7381`) — which a power loss or host
   restart never runs.
3. The sink handed to the runner is not the client's `TraceSink`; it is a second `TraceBuffer`
   (`core/flight/runtime.py:7636-7638`) that `_dispatch_phase_program` flushes into the client only in a
   `finally` after the whole program returned (`7993-7997`). `TraceSink.emit` appends and flushes per
   record (`core/tracing.py:185-224`) but creates its file lazily on the first record
   (`178`, `217-220`), and that first record is not emitted until step 2 finishes. So no
   `<run_id>.trace.jsonl` exists for the whole flight.
4. The canonical outputs rows are rendered by `_canonical_output_rows` (`runtime.py:11151`) only inside
   `seal()` (`12325-12331` via `_merged_canonical_rows`, `11873`); `_output_rows` itself exists only
   after the dispatch returns (`7999`).
5. The attempt record is opened at the first contact (`core/attempts/store.py:43-133`) and settled only by
   `seal()` or `abort()`; a dead process settles nothing.

## 2. Design

### 2.1 Row checkpoints (writer side)

After a row's episode completes — every contact and every arm of a multi-arm row (arms are visits inside
the one Solver episode, validated by the canonical stage against the DECLARED arm list) — the runner
calls the sink's optional `row_checkpoint` hook (`run_speech_native_agent_loop.settle_outcome`). The
hook is attached by `FlightRuntime._attach_row_checkpoint` only for the CONTINUOUS phase-program form,
where a sample settles exactly once. The runner emits the row's gold-free runtime records (`ORG`,
`SUPPLY`, `USE .../runtime-use`) at that moment instead of after the window; they go into the same
per-row buffer in the same position, and the buffers reach the trace sink in the same order, so an
uninterrupted flight's trace bytes are unchanged (proved by
`test_the_trace_the_client_writes_is_unchanged_by_checkpointing`). Scoring and the gold-bearing
`posthoc-use` record stay after the whole window.

`FlightRuntime._checkpoint_row` renders the row's canonical outputs record(s) through the SAME
`_canonical_output_rows` stage the seal uses, from the row's own result and the client's request records
for that sample, and appends ONE record to `<attempt dir>/<run_id>.rows.ckpt.jsonl`:

| field | content |
| --- | --- |
| `seq`, `prev_sha`, `sha` | hash chain: `sha = sha256(canonical JSON of the record without sha)`; `prev_sha` is the previous record's `sha` (all zeros for the header) |
| `sample_id`, `complete`, `reason` | the row; `complete = false` with the reason when the canonical stage refused it |
| `output_rows` | the canonical record(s), byte for byte what the seal writes |
| `trace`, `trace_sha256` | the row's serialized trace lines (exactly what `TraceSink` would write) and the hash of those lines as a trace file |
| `contacts`, `audio_seconds`, `cost` | this row's own spend, counted as `_scan_trace` counts a trace |

The header record carries the run, attempt, `protocol_hash`, `split_identity_hash`, `config_hash`, policy
and the code identity (sha256 of `runtime.py`, `rails/runner.py`, `core/row_checkpoint.py`).
Each append is one `write` + `flush` + `os.fsync`; a crash can therefore tear only the last line.
Design choice: the trace records live IN the checkpoint rather than in a second durable trace file, so
the checkpoint is self-contained custody and the live trace keeps its roster-ordered, seal-time shape.
The cost is that a flight's rows are stored twice (about 8 KB per synthetic row; a real native row is
larger).

A write failure raises: durability that silently stops is the defect being fixed. A canonical-rendering
failure does not raise; it records the row as not rendered with the reason (the seal still refuses such a
row on its own).

### 2.2 Seal

`seal()` closes the writer and holds the checkpoint against the rows it is about to write
(`compare_with_sealed`): every FLOWN sample needs exactly one checkpoint row, and every complete row's
record must equal the sealed row byte for byte; any disagreement refuses the seal before a bundle byte is
written. The manifest gains an optional `row_checkpoint` block (path, whole-file sha256, row counts, chain
tip); `verify_bundle` re-hashes the file, re-verifies the chain and the byte equality with the outputs.
A runner that never calls the hook (a test double) leaves an empty checkpoint, reported as
`NOT-EXERCISED` in the seal receipt and left out of the manifest rather than claimed.

### 2.3 Resume mode B (reader side)

`resume_from` takes `{"attempt_id", "checkpoint_sha256"}` beside the mode-A
`{"attempt_id", "trace_sha256"}`; a list may mix them. Preflight (model-free, before any server) calls
`read_checkpoint_predecessor`, which pins the whole file's sha256, verifies the chain, and checks the
header against this plan (`run_id`, `attempt_id`, `protocol_hash`, `split_identity_hash`) and the running
code identity. Every row that is complete, whose arm group is complete (`arm_count` equals the arms
present, indices `0..n-1`, delivering arm last — `arm_group_defect`), whose stored record names its own
sample, and whose stored trace holds the request/response the record names, is KEPT; every other started
row is INCOMPLETE with its reason and is re-flown whole. The flown roster is the roster minus the kept
rows; `resume.kept` / `flown` / `partial` and the kept-ids sha go into the receipts and the manifest
block exactly as for mode A.

The seal merges kept and live rows through the one canonical stage: a kept row is the stored record (no
replay); a flown row is rendered live. The manifest declares `predecessor_attempt` with `mode:
"checkpoint"`, `checkpoint_path` and `checkpoint_sha256` besides the mode-A fields.

### 2.4 I7r with a checkpoint predecessor

I7r — each row against exactly one trace — is unchanged. The block's `trace_path` names a trace file the
RESUME materializes under its OWN attempt directory
(`<attempt dir>/resume-predecessors/<predecessor>/<run_id>.trace.jsonl`, never in the predecessor's): the
kept rows' stored trace lines in checkpoint order. `verify_predecessor_attempt(s)` re-hashes it against the
declared sha256, re-reads the pinned checkpoint, and refuses unless the file equals byte for byte what the
kept rows' stored lines concatenate to (`_verify_checkpoint_predecessor`); then the ordinary
`_verify_resume_custody` runs against that trace. A kept row is therefore held against bytes its own
attempt durably recorded, through the same check a mode-A row gets.

### 2.5 The attempt registry

A crashed attempt stays OPENED forever (nothing settles it). `AttemptStore.open_attempt` is keyed by
`(run_id, attempt_id)`, so a new attempt id of the same run was always admitted by the store, and
`queue.py` (which only aborts attempts that FAIL under it) is not involved. The one rule that refused a
resume was the exposure gate's one-read budget for `final-report` runs
(`contracts/gate_exposure.py:_require_final_report_attempt_budget`, limit 1 for a read run id, "refused
even as a recovery"). Now:

* the resumed attempt writes `<attempt dir>/resume-declaration.json` BEFORE its first gate touch
  (`FlightRuntime._write_resume_declaration`);
* the gate exempts the attempts that file names from the count — and only those, only while they were never
  FINALIZED, and a declaration naming this attempt, a missing attempt or a FINALIZED one is refused by
  name (`_declared_resume_predecessors`). A fresh second attempt that declares nothing is counted exactly
  as before; a resume never opens a door to a third attempt;
* at `run_phases` the resume marks each predecessor ABORTED with the reason (`abort_if_opened`; an already
  settled record is untouched), so no dangling OPENED record outlives the process that died.

This is a deliberate narrow reading of the one-read protocol (section 4.4: no repeat, no best-of): a
resume keeps the predecessor's complete rows and flies only rows it never completed; nothing is selected
and no row is flown twice. It is an owner-visible interpretation of a protocol clause, so the engineer's
report flags it for the owner before this change is merged.

## 3. Invariants kept

* Gold, references and future turns never enter runtime: the row hook runs before scoring and sees only
  what the canonical stage already read.
* One writer per attempt directory: the writer refuses an existing file; a resume never writes into the
  predecessor's directory.
* The seal stays the authority: the checkpoint is checked against it and may refuse it; it never
  overrides it.
* The model contact count, request bytes and trace bytes of an uninterrupted flight are unchanged.
* "Code and request bytes unchanged": a checkpoint written under a different `runtime.py`, runner or
  checkpoint format, protocol, split or run is refused (not resumed).

## 4. Refused, by name

* a checkpoint file that hashes to other than the declared pin, a broken or reordered chain, an edited or
  deleted record, a duplicated sample;
* a header for another run, attempt, protocol, split or code identity;
* a resume of a fixed-policy, obs-policy, construction-visible, artifact-result or execution-unit flight
  (their dispatch does not checkpoint rows);
* a kept sample that is not a COMPLETE, arm-complete row of the pinned checkpoint (bundle side);
* two predecessors that both keep one sample; a kept sample that is also flown (I7r);
* a seal whose flown rows are not exactly the checkpoint's rows, or whose complete rows differ from the
  sealed bytes;
* a resume declaration naming a FINALIZED attempt, this attempt, or an attempt with no record.

## 5. Not covered / known limits

* The per-phase barrier form (`rails.phase_runner.run_program`) settles a sample only after its last
  phase, so it keeps no row checkpoint; neither do the fixed policy, the obs/Earnings dispatch and
  execution-unit rosters.
* Contacts of a row that was in flight when the process died are lost, and so are their costs in
  `cost_totals` (a lower bound, as for a trace-derived total).
* A flight whose runner never calls the hook is not checkpointed (reported `NOT-EXERCISED`).
* Merging this change moves `runtime.py` and `rails/runner.py`, which the prepared-artifact identity
  binds: every registered cell must be re-pinned at the flight commit.
