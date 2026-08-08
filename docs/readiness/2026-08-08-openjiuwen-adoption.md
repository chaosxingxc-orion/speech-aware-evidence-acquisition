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
