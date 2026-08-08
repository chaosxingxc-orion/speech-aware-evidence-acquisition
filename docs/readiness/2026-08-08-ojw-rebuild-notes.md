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
