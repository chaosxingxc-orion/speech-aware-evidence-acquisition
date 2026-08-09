# openJiuwen rebuild notes — obs-agent-loop-ojw (2026-08-08)

Deliverable of the worktree rebuild task under the adoption memo
(`2026-08-08-openjiuwen-adoption.md`). The obs loop now runs as a second,
equivalence-proven executor `obs-agent-loop-ojw`
(`src/.../reproduction/ojw/`), built ON the openJiuwen framework. The plain
`obs-agent-loop` policy is untouched and remains the reference fixture.

## Pinned version

- **openjiuwen 0.1.16.post2** (PyPI sdist/wheel, installed clean into a
  throwaway WSL python3.12 venv on 2026-08-08). This is the pin for the
  research venv until the eval-agent runtime report supersedes it.
- Windows install is IMPOSSIBLE, not merely inconvenient: the only Windows
  interpreter on this machine is Python 3.14.3 and openjiuwen declares
  `requires-python >=3.11,<3.14` — pip refuses before resolution. The
  sanctioned WSL-side fallback was used (throwaway venvs
  `~/ojw-eqtest-plain-venv` / `~/ojw-eqtest-full-venv`, safe to delete;
  `~/.venvs/speechrl` untouched).
- `pysbd 0.3.4` arrives as an openjiuwen dependency (probe result below).

## WSL install command for the research venv (operator runs this)

```bash
wsl -d Ubuntu-24.04
source ~/.venvs/speechrl/bin/activate
pip install openjiuwen==0.1.16.post2
pip show openjiuwen | head -2   # record Name/Version in the runtime environment record
```

`openjiuwen` NEVER enters `pyproject.toml` (D2 zero-dependency gate, red
line 2). The repo suite passes with it absent — openjiuwen-dependent tests
skip (verified, see §test record).

## What maps to which framework construct

| our concern | framework construct | where |
|---|---|---|
| OBS sliding-buffer loop scheduling | `AdvancedLoopComponent` over its internal `PregelGraph` (condition → body → post_body → condition) | `ojw/runner.py` |
| loop body (feed → asr → boundary → accept) | `LoopGroup` (a `BaseWorkflow` sub-graph) with four `WorkflowComponent` nodes in a linear chain | `ojw/runner.py` + `ojw/components.py` |
| audio-not-exhausted continue-decision (+ trim consumption, runaway guard, degenerate-window exit — everything the plain `while` head decides) | `FuncCondition(state.should_continue)` | `ojw/state.py` |
| loop-max guard | the SAME condition callable (`state.max_iterations`, plain policy's exact arithmetic). The framework's `LOOP_NUMBER_MAX_LIMIT` env only applies to number-typed `LoopComponent` loops, not `FuncCondition` loops | `ojw/state.py` |
| single door to the frozen core | our `FrozenCoreASR(WorkflowComponent)` — `invoke` override calling the constructor-injected `core.model.FrozenCoreAdapter.request` (tests inject fakes). No framework LLM client is imported or instantiated anywhere in `ojw/` | `ojw/components.py` |
| iteration-local dataflow (slice spec → response → resolution) | framework `${node.field}` `inputs_schema` refs (session io-state) | `ojw/runner.py` |
| loop-carried knowledge (accepted spans → conditioning tail) | session GLOBAL state (`update_global_state`/`get_global_state`, key `obs_agent_loop_accepted_spans`); written by AcceptAdvance, read by FeedBuffer next round | `ojw/components.py` |
| static per-sample values (sample identity, task instruction, evidence, arm, decoding params) | outer `Workflow` `Start` component maps driver-built invoke inputs into session state; components read them back via `get_global_state("start.<key>")` — resolved by the driver pre-loop exactly as today | `ojw/runner.py` (`build_invoke_inputs`) |
| outer graph | `Workflow` + `Start`/`End`, `create_workflow_session()` per sample | `ojw/runner.py` |
| entry into the existing driver | new policy `obs-agent-loop-ojw` in the ONE policy registry (`core/policies.py`); `run_experiment`'s sample loop, budget metering, slice rail, tracing all untouched | `ojw/policy.py` |
| DSP + slice rail | NOT framework constructs, by design: `reproduction/obs_audio.py` functions and `core/model/slices.py` registry are BELOW the framework layer and are called as plain functions (owner ruling: the framework tool base is reserved for the phase-2 model-invoked re-ask arm; wrapping pipeline DSP as tools would change semantics to model-decided invocation) | `ojw/components.py` |

Inheritance discipline (owner ruling, final): `FeedBuffer` / `FrozenCoreASR`
/ `BoundaryResolve` / `AcceptAdvance` derive from the framework's
`ComponentExecutable` line via `WorkflowComponent` (the framework's own
standard user-component base = `ComponentExecutable` + `ComponentComposable`;
the composable half is what `LoopGroup.add_workflow_comp` requires).
`LoopGroup`, `FuncCondition`, `Session`, the Pregel engine are composed,
never subclassed.

## Per-sample workflow execution ceiling (real-run blocker fix, 2026-08-08)

First live SAEA-E-001 attempt on this executor died per sample with
`[100101] workflow execution exceeded time limit of 60 seconds`: the
framework's session config ships a builtin
`WORKFLOW_EXECUTE_TIMEOUT: 60` default
(`openjiuwen/core/session/config/base.py::SessionConfig._load_builtin_configs_`),
read by `Workflow.invoke`
(`workflow.py: invoke_timeout = workflow_session.config().get_env(
WORKFLOW_EXECUTE_TIMEOUT)`) and enforced by
`Workflow._execute_with_timeout`, which raises
`StatusCode.WORKFLOW_EXECUTION_TIMEOUT` (100101) on expiry and treats a
non-positive value as NO limit. No dry run could trigger it (fake
transport is instant); a real call's loop runs 15-20 minutes.

Exact framework API used for the fix: the sanctioned env-override chain
`create_workflow_session(envs={WORKFLOW_EXECUTE_TIMEOUT: <seconds>})` →
`Workflow._create_workflow_session` → `config().set_envs(...)`, which
merges over the builtin default (`WORKFLOW_EXECUTE_TIMEOUT` is the
constant `"_execute_timeout"`, re-exported by `openjiuwen.core.session`).
No framework internals are patched.

Study-side wiring:

- fragment key `ojw_workflow_timeout_seconds` (all three ojw baseline
  fragments carry `21600`; the key flows into config_hash →
  protocol_hash). Absent → generous 6 h/sample backstop
  (`DEFAULT_WORKFLOW_TIMEOUT_SECONDS`, `reproduction/ojw/__init__.py`);
  `<= 0` disables the limit (framework convention, passed through
  deliberately rather than inventing a second disable spelling); boolean/
  non-numeric/non-finite values refuse (`policy.workflow_timeout_seconds`)
  — a typo must never silently re-enable the 60 s kill. This is a hang
  backstop, not a budget rail — budgets remain the plan's calls/audio caps
  on the adapter.
- a real 100101 kill is translated in `runner.execute_obs_workflow` into
  an `ObsLoopError` naming the knob and the configured value.
- tests: spy on `runner.create_workflow_session` proves the configured
  value (and the absent-key default) genuinely reaches the framework
  session env; an end-to-end test reproduces the live kill (tiny ceiling +
  slow adapter → framework 100101 → actionable ObsLoopError); parser
  semantics are covered openjiuwen-free in the absent-file suite.
- note: a blocking transport call cannot be interrupted mid-request by the
  asyncio timeout — the kill lands at the next await point after the
  blocking call returns (this matches the live incident's log shape).

## Bounded per-slice retry (second live-run finding, 2026-08-08)

Second real attempt: 27 slice requests succeeded, then one HTTP request
hung server-side for the transport's full socket timeout; the transport's
`TimeoutError` propagated (the ojw vertex wrapped it as 100054) and the
whole attempt died. Fix: ONE shared helper,
`reproduction/obs_loop.py::request_slice_with_retry`, called by BOTH
executors (the plain policy's request site and the ojw `FrozenCoreASR`
component), so retry behaviour can never diverge:

- retryable = `SLICE_RETRYABLE_EXCEPTIONS = (FrozenCoreError,
  TimeoutError, ConnectionError)`; anything else (a bug) propagates
  immediately, never retried. A budget/binding `FrozenCoreError` retried
  once fails identically and spends nothing, so no carve-out is needed.
- each retry is a FRESH request: derived request id (`<id>-r1`, `-r2`…),
  fresh payload build, separately traced and metered by the adapter —
  exactly what the +headroom in `planned_model_calls` exists for. The
  final failure propagates unchanged (fail-closed as before).
- audit visibility: the iteration's OBS record (both executors, identical
  field) carries `obs_retry_of` = the ORIGINAL request id (None on the
  ordinary path); the failed original's MODEL_REQUEST record and its
  metered spend precede it in the trace, so an auditor sees both calls.
  The outputs row chains the request id that actually answered.
- knob: `obs_slice_retry_max` (default 1; 0 disables) — a real obs_* key
  in `ObsLoopConfig` (unknown-key check covers typos), declared in all
  seven obsloop/obsfixed/ojw baseline fragments → config_hash →
  protocol_hash.
- tests: plain-suite `TestSliceRetry` (flaky-once completes with two
  attempts visible; second failure propagates; retry 0 disables; the
  helper retries FrozenCoreError but never foreign exceptions) + the
  `retry-flaky` equivalence scenario driving BOTH executors through the
  same flaky adapter (identical retry id, trace, payload sequence).

## Batch inference — sample-level concurrency (owner directive 2026-08-08)

Owner directive: experiments must use BATCH inference, not one-by-one.

**What parallelizes: samples. What cannot: intra-call slices.** Slice k+1's
window start IS slice k's resolved boundary, so a call's slice chain is
inherently sequential — no implementation could overlap it without
inventing the boundary it hasn't heard yet. Concurrency therefore lives at
the sample level: N whole calls in flight, each running its own strictly
sequential obs loop. The plain policy stays sequential by definition — it
is the equivalence reference fixture.

Mechanism (`reproduction/ojw/runner.py::execute_obs_batch`):
`asyncio.gather` over one task per sample, bounded by an
`asyncio.Semaphore(obs_batch_samples)`; the semaphore also caps PEAK MEMORY
because each sample decodes its own PCM inside its task, under the
semaphore, so at most `obs_batch_samples` decoded calls are ever live. Real
overlap comes from `FrozenCoreASR` hopping the blocking adapter call to a
worker thread (`asyncio.to_thread`) — without that, N "concurrent" samples
would serialize on the event-loop thread. The per-sample pipeline
(`policy._prepare_state` / `_finalize_sample`) is shared VERBATIM with the
sequential entry point, so a batched sample is byte-identical to a
sequential one.

**Determinism (the part that matters for the record).** Nothing observable
depends on completion order:

- **Outputs rows**: the driver builds contexts in split-id order, hands the
  whole list to `run_samples`, and writes rows from the returned list, which
  is aligned to the input order (`asyncio.gather` preserves argument order).
- **Trace**: the per-run trace file stays single and append-only. Each
  sample's ENTIRE trace — driver preamble (OBS/ORG/SUPPLY), policy records,
  and the shared adapter's per-request records — buffers in its own
  `core.tracing.TraceBuffer`; the driver flushes buffers into the real
  `TraceSink` in split-id order after gather completes. Chosen over
  flush-on-completion-with-a-lock precisely because ordering is then decided
  by a `for` loop rather than by a race. Within a sample, record order is
  emission order, exactly as sequential.
- **Adapter routing**: one adapter serves all samples, so its records are
  routed to the current sample's buffer through a contextvar
  (`core.tracing.DispatchingSink` + `set_current_trace_buffer`), task-local
  under asyncio and copied into `to_thread` workers. With no buffer set it
  falls through to the real sink — the sequential path is untouched.
- **Failures**: all tasks are allowed to settle (`return_exceptions=True`,
  no completion-order cancellation) and the FIRST failed sample in split-id
  order is raised. Tested with two concurrently-failing samples whose
  wall-clock failure order is the OPPOSITE of split-id order.

**Metering under concurrency (rail).** `core/model/adapter.py` now holds a
`threading.Lock` across [fresh sibling read → budget checks → MODEL_REQUEST
record → durable `record_usage`], plus the post-transport aggregate
counters. The transport call itself stays OUTSIDE the lock — holding it
across a multi-second model request would serialize away the very
concurrency this exists to provide. This closes the in-process
simultaneous-double-read the I3 comment explicitly left open; the
cross-PROCESS case remains `core.attempts`'s concern, unchanged. Verified
by a 12-thread hammer against a 5-call budget (exactly 5 succeed, exact
in-process AND durable metering, exactly 5 MODEL_REQUEST records); with the
lock neutralized the same hammer lets 6 through, so the test proves the
lock rather than merely passing.

**Slice-file collisions: none by construction.** Slice paths are
`derived/obs-slices/<run_id>/<sample_id>/i<NNNN>.wav`
(`SliceRegistry.slice_relpath`) — the sample id is a path component, so two
concurrent samples cannot collide, and within a sample iterations are
sequential. Asserted directly (disjoint path sets per sample, every path
containing its own sample id, all registered and written).

**Knob**: `obs_batch_samples` (default 4 in the three ojw fragments; 1 =
exactly today's sequential behaviour) → config_hash → protocol_hash.
Validated in both `ObsLoopConfig` and the driver; a config demanding
batching from a policy that implements only `run_sample` refuses
fail-closed BEFORE the attempt slot is reserved, so no budget is spent.

**Server-side flags (operator sets these)**: `-np 4` (4 parallel slots) and
`-c 32768` total context so each slot gets 8k — matching the per-slice
~3k-token need with headroom. Expected 2-4x wall-clock on the
CPU-expert-bound MoE; `obs_batch_samples` should not exceed `-np` (extra
samples would just queue server-side).

## Framework findings that shaped the build

1. **None deletes.** The session state merge
   (`openjiuwen.core.session.utils.update_dict`) treats a None value as a
   KEY DELETION. A component output like `{"pre_sha256": None}` arrives at
   the next node WITHOUT the key. All None-able fields
   (`pre_sha256`, `estimate`, `snapped`, empty accepted/dropped) are
   therefore read back with `.get()` — missing IS the None that was set.
   Found by the first real run (KeyError in `accept`); pinned by the
   equivalence tests.
2. **Build inside the loop.** Graph vertices create asyncio primitives at
   construction; the workflow must be built inside the running event loop
   (`asyncio.run(_build_and_invoke(...))`), else Py3.12 deprecation warnings
   and cross-loop future risk.
3. **`AdvancedLoopComponent` composes directly** into a `Workflow` via
   `add_workflow_comp` (it is `ComponentComposable`); the higher-level
   `LoopComponent` wrapper only admits static loop types
   (array/number/expression/always-true), so the dynamic condition uses the
   engine layer directly — the same object `LoopComponent` itself drives.
4. **Cross-scope session reads work.** Nodes inside the `LoopGroup`
   sub-session resolve `get_global_state("start.<key>")` and the flat
   global keys written by in-loop nodes; verified by the passing
   equivalence suite (bare-core, evidence-arm and tail scenarios all depend
   on it).
5. **Framework logs add, never replace.** openJiuwen emits its own
   structured graph/workflow logs (loguru events, checkpoint saves on
   error). Our TraceSink records are emitted by our components only and are
   byte-identical to the plain policy's — the framework's observability is
   additive, exactly as the task requires.

## Determinism findings

- Structural argument: the loop body is a LINEAR four-node chain inside
  `AdvancedLoopComponent`'s Pregel graph, so every super-step has exactly
  one ready node (`PregelLoop._run_step` collects ready nodes and runs
  them; with one active node per step there is no concurrent-ordering
  freedom). The condition router is invoked exactly once per round.
- Empirical: `TestDeterminism::test_determinism_five_runs` runs the
  model-tails fixture 5x on fresh worlds and asserts the full artifact
  fingerprint (trace records minus the volatile `latency_seconds`,
  derivation-record bytes, outcome row) is identical across all five runs
  AND equal to the plain policy's reference fingerprint. Passed on
  openjiuwen 0.1.16.post2 (2026-08-08, WSL python3.12).
- Caveat recorded: this determinism claim covers linear-chain bodies. A
  future graph with parallel branches would put multiple nodes in one
  super-step (`TaskExecutorPool` awaits them concurrently) and would need
  its own ordering proof before any registered run.

## pysbd decision (kept our cut rule)

Rule (owner): adopt pysbd for the sentence-cut only if byte-equivalent
behaviour can be pinned. It cannot — pysbd segments semantically while the
frozen rule (`obs_audio.accept_up_to_boundary`: rfind of
`SENTENCE_FINAL_CHARS` inside the boundary-share window) is positional.
Probe (pysbd 0.3.4, 2026-08-08):

```
text = 'We met Dr. Smith today. He was fine'   (window limit 14)
frozen-rule accepted: 'We met Dr.'
pysbd segments: [('We met Dr. Smith today. ', 0, 24), ('He was fine', 24, 35)]
```

pysbd refuses the abbreviation boundary ("Dr.") the frozen rule cuts at,
and its first admissible boundary (char 24) lies OUTSIDE the 14-char
window — any pysbd-based cut changes accepted spans. Kept ours;
pysbd-as-tier is a possible future ablation arm with its own
pre-registration, not a v1 swap.

## Residual custom logic (honest list — what is NOT framework-reused, and why)

1. `state.ObsSampleState` — plain-Python per-sample state holder. Heavy,
   non-serializable run objects (decoded PCM array, `SliceRegistry`,
   `TraceSink`, config) are constructor-injected, not session state: the
   framework session is a serializing/merging store (None-deletion,
   checkpointing) and is the wrong home for multi-hundred-MB PCM or for
   objects whose identity the slice rail depends on. Loop-carried TEXT
   state does live in framework session state.
2. `state.should_continue` — the condition callable's body (trim
   consumption, runaway arithmetic, exhaustion epsilon, degenerate-window
   check) is our logic by necessity: it IS the science of the loop policy,
   not scheduling. The framework supplies the loop engine around it.
3. The accepted-spans mirror: `AcceptAdvance` writes the span to session
   global state (the loop's dataflow home) AND appends to the state holder
   (the post-loop stitch/artifact writer's home). Two homes because the
   post-workflow policy code runs after the session is gone; divergence is
   impossible to miss — the equivalence suite compares stitched text,
   derivation records and every trace record against the plain reference.
4. Post-loop stitch/derivation emission (`policy.py` after
   `execute_obs_workflow`) — identical to the plain policy's tail section
   (same descriptors, same records, same artifact schema); driver-side by
   design, since the outputs-row binding (I7) is a study-rail concern, not
   an orchestration concern.
5. Runaway signaling: the plain policy raises mid-loop; the framework
   condition cannot raise without the error being rewrapped as a framework
   `BaseError`, so the condition flags `state.runaway` and exits, and the
   policy raises the SAME `ObsLoopError` after the workflow returns —
   identical trace prefix and call count.
6. **Deliberate non-reuse: `core.context_engine` compressors** (owner
   ruling, final): they are LLM-driven (ModelClientConfig); our
   carry/rolling state is deterministic extraction. When the carry arm
   lands, it is a plain component — not a compressor subclass.
7. **Deliberate non-reuse: framework tool base for DSP** (owner ruling,
   final): VAD/slicing/rms-norm remain plain functions called by
   components; the tool abstraction (model-decided invocation) is reserved
   for the phase-2 selective re-ask arm (denoise-relisten).
8. **Deliberate non-wire: `foundation/llm` model clients** (owner ruling,
   Q1): their `openai_model_client` is api_base-configurable and CAN reach
   llama-server, but the frozen-core path stays on OUR transport
   (gate/plan/metering/slice rails). The foundation/llm layer is RESERVED
   for future tool-level models only (local embedding for T-series, a
   pinned local judge) — noted here as the seam; nothing wired now.

## Test record (2026-08-08, WSL Ubuntu-24.04, python3.12)

- Plain venv (openjiuwen ABSENT): `3 failed, 909 passed, 15 skipped` —
  the ojw executor module skips via its importorskip marker; the
  openjiuwen-free ojw tests (registration, install-hint refusal, condition
  semantics) pass.
- Full venv (openjiuwen 0.1.16.post2): `3 failed, 917 passed, 15 skipped`
  — the 9 ojw executor tests all pass (equivalence x6 scenarios,
  determinism 5x, single-door, stitched/registry checks); the
  absent-refusal test skips instead. Same 3 environmental failures, same
  14 pre-existing skips in both venvs.
- The 3 failures are PRE-EXISTING and environmental, reproduced unchanged
  at the base commit (7acd3ec) with this task's changes stashed:
  `test_cli_module_dispatch.py` (2) and `test_bundle.py::test_cli_score_
  manifest_mode_is_verified_and_authoritative` (1). Both classes are
  artifacts of running from a `.claude/worktrees/` checkout: the umbrella
  lock resolves relative to the registered layout
  `<umbrella>/studies/<study>/` (the worktree is not there), and WSL git
  cannot read a Windows-created worktree's `gitdir: D:/...` pointer. They
  pass in the operator's normal environment (the main checkout at the
  registered path). Ruff likewise reports 9 pre-existing F401s in older
  test files, byte-identical on the main checkout master — none in this
  task's files.

## Operator runbook deltas (vs `2026-08-08-obs-segmentation-notes.md` §5)

1. One-time: install the pin into the research venv (§WSL install command
   above) and record Name/Version in the runtime environment record.
2. To run any arm on the openJiuwen executor, select the ojw baseline
   fragment — v1 ships `--baseline bare-core-ojw` (identical knobs to
   `bare-core-obsloop`, only `policy` differs, so the OBS behaviour is
   byte-equivalent by the merged test suite). Everything else in the
   runbook (exposure pre-registration, planned budgets, run dirs,
   artifacts) is unchanged — same trace kinds/fields, same
   `<run_id>.obs-derivation.<sample_id>.json`, same slice tree.
3. Equivalence gate before registered use (red line 3): with openjiuwen
   installed, `pytest tests/unit/test_obs_loop_ojw.py` must be green in the
   research venv on the pinned version. If the pin ever moves, rerun this
   gate and append the new version here.
4. Framework logs (loguru graph/workflow events) will appear on stderr
   during ojw runs; they are additive observability and are NOT part of
   the run's trace record set. The trace jsonl remains the audit surface.
5. Batch inference: the ojw fragments declare `obs_batch_samples: 4`. Start
   llama-server with `-np 4 -c 32768` (8k per slot) so the four in-flight
   samples each get their own slot; keep `obs_batch_samples <= -np`. Set it
   to 1 to reproduce the sequential behaviour exactly (same rows, same
   trace). Note the per-sample workflow ceiling below is wall-clock, so
   under batching a sample's elapsed time includes time spent waiting on
   server slots — the 6 h default has ample room for this, but a much
   larger batch on a slower server is the case to watch.
6. Per-sample ceiling: every ojw fragment declares
   `ojw_workflow_timeout_seconds` (21600). If a sample dies with an
   ObsLoopError naming this knob, the loop genuinely ran past 6 hours —
   raise the value in the fragment (a config change, so a new
   config_hash/protocol_hash) or set it `<= 0` to disable; never shrink it
   below the longest call's expected loop time (~1.5-2 h worst case on a
   75 min call at min-advance clamping).
