"""Session-wide test discipline (root of the test tree).

M-1 follow-up (external-threat-model review, controller-flagged): the gate
correctly REFUSES a model touch if
``src/speech_aware_evidence_acquisition/scoring/__pycache__`` contains any
entry (``contracts.FrozenCoreGate._validate_scoring_freeze``) -- that
refusal is intentional and must stay. But several tests open the real gate
against the REAL repository's scoring package
(``tests/contract/test_real_receipts.py``,
``tests/unit/test_e0_generators.py::TestCloseAndGate``), so the SUITE's own
outcome must never depend on whether some earlier, unrelated interpreter
(a different Python version, an editor's language server, a prior manual
``python -c "import ..."``) happened to leave bytecode there. This makes the
same operator discipline already documented in ``docs/engineering.md`` and
the R0 smoke runbook (``PYTHONDONTWRITEBYTECODE=1`` + purge
``scoring/__pycache__``) self-enforcing for the test session itself, rather
than relying on whoever runs ``pytest`` to have remembered it.

Three guards now, at three different times:

1. A MODULE-LEVEL statement below (not inside a fixture): pytest imports
   this ``conftest.py`` before collecting a single test module, and
   collection itself -- ordinary ``import speech_aware_evidence_acquisition
   .core.scorers`` chains transitively into ``.scoring.*`` -- can write
   fresh ``__pycache__`` entries before any fixture, even a session-scoped
   autouse one, ever runs. Only a module-level guard is early enough to stop
   THIS session's own collection from planting the exact bytecode the M-1
   gate refusal exists to catch.
2. A session-scoped ``autouse`` fixture that re-asserts the same two guards
   immediately before the first test body runs -- defense in depth (a
   plugin resetting ``sys.dont_write_bytecode``, or a stray ``.pyc`` placed
   between collection and the first test), not a substitute for (1).
3. A FUNCTION-scoped ``autouse`` fixture, added after a controller-flagged
   regression: (1) and (2) guard THIS process's own ``sys.dont_write_
   bytecode``, but a test that spawns a real subprocess
   (``subprocess.run([sys.executable, ...])``, e.g.
   ``tests/contract/test_cli_module_dispatch.py``) starts a CHILD
   interpreter that does NOT inherit that flag -- only
   ``PYTHONDONTWRITEBYTECODE`` in the child's own environment does, and that
   is that test's own responsibility to set (see that module's docstring).
   When a test forgets, the child writes fresh ``.pyc`` files into
   ``scoring/__pycache__``, tripping the SAME M-1 refusal for every OTHER
   test that opens the real gate later IN THE SAME SESSION -- reproduced
   live: one such test polluted the tree and 16 unrelated, otherwise-passing
   tests across 6 files failed afterward, each passing again in isolation.
   Guard (3) purges again after EVERY test (not merely once per session), so
   the SUITE's own outcome is self-healing regardless of which test (this
   one's subprocess-spawning tests, or a future one) left bytecode behind --
   "make it not happen" (per-subprocess env, guarded where it is spawned) and
   "recover if it happens anyway" (this fixture) are both enforced, neither
   alone.

Purges ONLY ``scoring/__pycache__`` -- never any other directory -- and is a
no-op if it is already absent.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCORING_PYCACHE = (
    _REPO_ROOT / "src" / "speech_aware_evidence_acquisition" / "scoring" / "__pycache__"
)


def _purge_scoring_pycache() -> None:
    """Remove ONLY the frozen scoring package's own ``__pycache__``.

    A no-op if it is already absent. A SYMLINK named ``__pycache__`` is
    deliberately left alone here, not silently removed: that is exactly the
    shape ``contracts.FrozenCoreGate._validate_scoring_freeze`` refuses
    explicitly (a symlinked-directory freeze-evasion probe), and this
    session-hygiene helper must never quietly make that probe's setup
    disappear before a test gets to assert on it.
    """

    if _SCORING_PYCACHE.is_dir() and not _SCORING_PYCACHE.is_symlink():
        shutil.rmtree(_SCORING_PYCACHE)


# Executed at conftest IMPORT time (pytest's plugin/conftest loading happens
# before any test module is collected) -- see guard (1) in the module
# docstring above for why a fixture body alone would be too late.
sys.dont_write_bytecode = True
_purge_scoring_pycache()


@pytest.fixture(scope="session", autouse=True)
def _enforce_scoring_bytecode_discipline():
    """Guard (2): re-assert both guards right before the first test body
    runs. See the module docstring for why this exists alongside, not
    instead of, the module-level statements above."""

    sys.dont_write_bytecode = True
    _purge_scoring_pycache()
    yield


@pytest.fixture(autouse=True)
def _purge_scoring_pycache_after_every_test():
    """Guard (3): function-scoped, so it runs after EVERY test, not once per
    session -- the self-healing backstop for a subprocess-spawning test that
    forgot to disable bytecode writing in its child. See the module
    docstring's controller-flagged regression for exactly what this closes.
    A no-op when the directory is already absent (the overwhelmingly common
    case); never touches anything other than ``scoring/__pycache__``."""

    yield
    _purge_scoring_pycache()
