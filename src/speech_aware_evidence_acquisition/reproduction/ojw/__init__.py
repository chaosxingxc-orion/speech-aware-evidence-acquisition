"""openJiuwen-backed obs-agent-loop executor (owner directive 2026-08-08).

The agent layer is BUILT ON the openJiuwen framework (openJiuwen-ai/
agent-core, Huawei, Apache-2.0), reusing framework constructs maximally:
the OBS sliding-buffer loop runs as a framework ``LoopGroup`` body inside
an ``AdvancedLoopComponent`` whose continue-decision is a ``FuncCondition``,
over the Pregel graph engine — no hand-rolled scheduling. The design record
is ``docs/readiness/2026-08-08-ojw-rebuild-notes.md``; the adoption red
lines are ``docs/readiness/2026-08-08-openjiuwen-adoption.md``:

1. **Single door** — the only model-call path is our
   ``FrozenCoreASR(ComponentExecutable)`` component wrapping the
   constructor-injected ``core.model.FrozenCoreAdapter.request`` callable.
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

OJW_POLICY_NAME = "obs-agent-loop-ojw"

OJW_INSTALL_HINT = (
    "policy 'obs-agent-loop-ojw' requires the openjiuwen framework, which is "
    "not importable in this environment; install the pinned version into the "
    "WSL research venv (see docs/readiness/2026-08-08-ojw-rebuild-notes.md) "
    "— openjiuwen never enters pyproject.toml (D2 zero-dependency gate) — or "
    "use the plain 'obs-agent-loop' policy"
)


def openjiuwen_available() -> bool:
    """True when the openjiuwen framework is importable (runtime-detected,
    never a pyproject dependency — same discipline as ``obs_vad: webrtc``)."""

    try:
        import openjiuwen  # noqa: F401, PLC0415 (runtime detection only)
    except ImportError:
        return False
    return True
