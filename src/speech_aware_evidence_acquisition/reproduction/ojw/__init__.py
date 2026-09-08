"""openJiuwen-backed speech AgentLoop executors (owner directive 2026-08-08).

The agent layer is BUILT ON the openJiuwen framework (openJiuwen-ai/
agent-core, Huawei, Apache-2.0), reusing framework constructs maximally:
the OBS sliding-buffer loop and speech-native knowledge AgentLoop run as
framework ``LoopGroup`` bodies inside ``AdvancedLoopComponent`` instances
whose continue decisions are ``FuncCondition`` objects over the Pregel graph
engine — no hand-rolled Agent scheduling. The design record
is ``docs/readiness/2026-08-08-ojw-rebuild-notes.md``; the adoption red
lines are ``docs/readiness/2026-08-08-openjiuwen-adoption.md``:

1. **Single door** — model calls use either our
   ``FrozenCoreASR(ComponentExecutable)`` component or the speech Agent
   contact component's constructor-injected repository ``CoreClient``.
   The framework's own LLM/model clients (``foundation/llm``), web-search
   tools and anything network-bound are NEVER instantiated here.
2. **D2 zero-dependency gate** — ``openjiuwen`` never enters
   ``pyproject.toml``. Every module in this package that imports
   ``openjiuwen`` does so behind the lazy seam in ``policy.py``; the repo's
   test suite passes with openjiuwen absent (openjiuwen-dependent tests
   carry skip markers).
3. **Equivalence** — the openJiuwen executor reproduces the plain-Python
   ``obs-agent-loop`` policy's behaviour exactly (same accepted-span
   sequences, same slice derivation records, same stitched text, same
   trace records); proven by ``tests/unit/test_obs_loop_ojw.py``.

Import discipline: THIS module and ``state.py``/``policy.py`` import no
openjiuwen; ``components.py`` and ``runner.py`` do and are imported only
after ``openjiuwen_available()`` is proven (or fail with a clear
ObsLoopError naming the install path).
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

OJW_POLICY_NAME = "obs-agent-loop-ojw"
#: The KC-E1f repair sibling (owner Decision 12-F, 2026-09-08). Its class
#: lives in ``reproduction.repair_loop`` beside the plain policy's, but the
#: NAME lives here, with ``OJW_POLICY_NAME``, so the modules that must reason
#: about "which policies run on the openJiuwen executor" -- the prefetch
#: legality in ``reproduction.obs_loop`` and the driver's pipeline guard --
#: read one constant instead of repeating a string.
OJW_REPAIR_POLICY_NAME = "obs-repair-loop-ojw"
#: Every policy whose per-sample loop is the openJiuwen graph. The graph owns
#: one ``ObsSampleState`` per sample -- its own cursor, its own accepted
#: spans, its own session -- so two samples may overlap under the driver's
#: prefetch pipeline whatever the boundary mode, which is the one thing the
#: plain policy's SEQUENTIAL cutter cannot say about itself.
OJW_OBS_POLICY_NAMES = (OJW_POLICY_NAME, OJW_REPAIR_POLICY_NAME)
PINNED_OPENJIUWEN_VERSION = "0.1.16.post2"

# Per-sample workflow execution ceiling (real-run blocker, 2026-08-08): the
# framework kills every Workflow.invoke at a builtin 60-second default
# (openjiuwen.core.session.config.base.SessionConfig._load_builtin_configs_:
# WORKFLOW_EXECUTE_TIMEOUT=60 -> Workflow._execute_with_timeout -> error
# 100101), which no dry run could trigger (fake transport is instant) but a
# real 40-75-minute call's loop always does. The knob below rides in the
# baseline fragment (-> config_hash -> protocol_hash) and is injected via
# create_workflow_session(envs={...}) -- the framework's own override path.
# The default is deliberately generous (6 h per SAMPLE, not per request):
# it is a hang backstop, not a budget rail -- budgets are the plan's
# calls/audio-seconds caps on the adapter. Framework semantics: a value
# <= 0 disables the limit entirely (Workflow._execute_with_timeout treats
# non-positive as None).
OJW_WORKFLOW_TIMEOUT_KEY = "ojw_workflow_timeout_seconds"
DEFAULT_WORKFLOW_TIMEOUT_SECONDS = 21600.0


class OpenJiuwenExecutorError(RuntimeError):
    """The pinned openJiuwen workflow boundary refused malformed execution."""


OJW_INSTALL_HINT = (
    "policy 'obs-agent-loop-ojw' requires the openjiuwen framework, which is "
    "not importable in this environment; install the pinned version into the "
    "WSL research venv (see docs/readiness/2026-08-08-ojw-rebuild-notes.md) "
    "— openjiuwen never enters pyproject.toml (D2 zero-dependency gate) — or "
    "use the plain 'obs-agent-loop' policy"
)


def openjiuwen_available() -> bool:
    """True when the exact pinned openJiuwen runtime is installed.

    Detection never creates a framework client and openJiuwen remains absent
    from pyproject dependencies, matching the ``obs_vad: webrtc`` discipline.
    """

    try:
        return version("openjiuwen") == PINNED_OPENJIUWEN_VERSION
    except PackageNotFoundError:
        return False


def openjiuwen_runtime_version() -> str:
    """Return the exact admitted runtime version or fail closed."""

    try:
        installed = version("openjiuwen")
    except PackageNotFoundError as error:
        raise OpenJiuwenExecutorError(OJW_INSTALL_HINT) from error
    if installed != PINNED_OPENJIUWEN_VERSION:
        raise OpenJiuwenExecutorError(
            "openJiuwen runtime version mismatch: expected "
            f"{PINNED_OPENJIUWEN_VERSION}, found {installed}"
        )
    return installed
