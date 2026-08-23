# openJiuwen adoption memo (owner directives, 2026-08-08)

Owner directives (session, escalating, 2026-08-08): the agent layer is to be
BUILT ON openJiuwen (openJiuwen-ai/agent-core, Huawei, Apache-2.0), reusing
the framework maximally instead of writing our own orchestration logic.

## Source-analysis facts (repo cloned to WSL ~/openjiuwen-src, GitCode mirror)

- Python >=3.11,<3.14 (our venv: 3.12 ✓); Apache-2.0; active (2,095 commits).
- **Custom components**: `core/workflow/components/component.py` —
  `ComponentExecutable.on_invoke` override wraps arbitrary Python; base class
  has ZERO coupling to the framework's LLM clients (LLMComponent is just one
  component type). → our single-door component is clean.
- **Native loops**: `core/workflow/components/flow/loop/LoopGroup`
  (condition/body/post_body sub-nodes, Func/Expression conditions, loop-max
  guard) over a Pregel graph engine — carries the OBS sliding-buffer loop
  without custom scheduling.
- **Context compression is framework-native**: `core/context_engine/
  processor/compressor/*` (dialogue/round-level/full compactors) — the
  owner-directed context-management/compression layer reuses this.
- Also reusable later: `core/retrieval/` (agentic retriever, query rewriter —
  T-series), `agent_teams/memory/`, `pysbd` (text sentence boundaries for
  the Node-1 cut rule), observability hooks.
- **Dependency footprint is platform-grade** (~40 direct deps incl.
  anthropic/openai/dashscope/deepseek clients, transformers, pymilvus,
  fastmcp, sqlalchemy stack). URL scan found provider endpoints + one web
  search API (bocha) in client code; no obvious telemetry, runtime audit
  pending (eval agent).

## Red lines (unchanged by adoption)

1. **Single door**: the model-invocation component is OURS
   (`FrozenCoreASR(ComponentExecutable)` wrapping
   `core.model.FrozenCoreAdapter` — gate, ExecutionPlan, metering, slice
   binding, session receipt intact). The framework's LLM/model clients and
   any cloud/web-search tools are NEVER instantiated (paid API = 0).
2. **D2 zero-dependency gate**: `openjiuwen` installs into the WSL venv
   (exact version + hash recorded in runtime environment records), never
   into `pyproject.toml`.
3. **Deterministic equivalence**: the openJiuwen executor must produce
   trace-hash-identical results to the plain-Python obs-loop policy (now the
   reference fixture) on the same inputs before any registered run uses it.

## Rebuild plan

Worktree agent builds: workflow graph (LoopGroup OBS loop; Node-2 arms as
branches; re-ask routing via conditions), FrozenCoreASR single-door
component, DSP functions registered as framework local tools, equivalence
tests. Runs (segmented SAEA-E-001, R4 mini arms) execute on the openJiuwen
executor after equivalence passes. Eval-agent runtime report (install
footprint, determinism run, telemetry audit, version pin) appends here when
it lands.

## Speech-native knowledge AgentLoop continuation (2026-08-23)

The shared speech-native knowledge runner now requires an explicit executor
identity. Formal AgentLoop execution uses `openjiuwen-workflow-v1`; the
dependency-free `reference-trajectory-v1` remains only as a semantic
equivalence oracle and cannot execute parallel contact batches.

The pinned openJiuwen runtime carries the control flow as a native graph:

```text
AdvancedLoopComponent(FuncCondition)
  -> PrepareAgentWave
  -> [ExecuteAgentContact_0 ... ExecuteAgentContact_N]  # logical fan-out
  -> AggregateAgentWave                                # ordered fan-in
  -> next loop condition
```

The graph is built from the existing `Workflow`, `LoopGroup`, and
`AdvancedLoopComponent` seam in `reproduction/ojw/`; no new experiment
script or framework model client is introduced. Each active contact calls
the constructor-injected repository `CoreClient`, so ExecutionPlan gating,
the receipt-bound resident llama.cpp service, pre-materialized speech
packets, and repository tracing remain the only model-contact door.

Every branch and every subsequent loop wave rebuilds the request from the
same original speech packet. Agent-produced text/state is carried in
openJiuwen structured session state as auxiliary context and never replaces
the speech query. The framework owns loop execution, component concurrency,
and fan-in barriers; the repository owns scientific transition validation,
knowledge BUILD/USE separation, contact budgets, deterministic branch
ordering, slot assignment, and post-runtime scoring.

The admitted runtime is exactly `openjiuwen==0.1.16.post2`; an absent or
different version fails before workflow construction. Each trajectory leases
one primary llama.cpp slot through every wave. Same-trajectory branches are
serialized on that slot so speech-prefix KV remains reusable, while different
samples run concurrently across slots. Cancellation waits for the underlying
synchronous contact to settle before returning a slot. Workflow admission is
bounded by `queue_depth`, and the first fatal error stops new admission.

The formal production vertical slice reuses the existing P-SLU profile driver.
M1 exposes complete TRAIN-built `KeyFacet` material and performs one listwise
speech-to-key decision. M2 first performs one speech-only semantic analysis,
then exposes the same key material and invokes a second decision with both the
original speech packet and the generated `AgentStateArtifact`. Key facets are
transported as `knowledge_role=key`; `ValueBundle` content is not used as key
text and task-target mapping remains deterministic metadata. Dynamic value or
facet acquisition must carry a hash-bound `RankResult` and `FusionDecision`.

The admission tests require cross-sample parallel overlap, same-trajectory slot
affinity, deterministic ordered aggregation, exact reference-trajectory
semantic equivalence, multi-wave state transitions, aggregate response binding
for AgentState artifacts, cancellation settlement, bounded 100-sample
admission, and pre-contact refusal of oversized waves. The openJiuwen-absent
suite remains valid through the existing lazy import and skip/refusal boundary.
