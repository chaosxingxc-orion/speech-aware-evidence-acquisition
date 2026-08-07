"""The ONE experiment driver: config + plan -> gate -> run -> outputs (R0).

Every Stage-2 run (R0 smoke, R1 reproduction, X probes, 2B deep digs) goes
through run_experiment(); an experiment differs from another only by its four
config fragments and, rarely, a newly registered component. RUNTIME PHASE:
this module never imports data.references.

R0 repair refactor stage 1 (behaviour-preserving): this used to be one
~740-line ``driver.py`` module. It is now this package (``run.py`` for
``run_experiment``/``run_experiment_bundled``/``load_split``, ``cli.py`` for
the ``saea-driver`` CLI subcommands) purely for file size -- every name below
was already part of this module's public surface and remains importable from
exactly ``speech_aware_evidence_acquisition.core.driver`` as before.

R0 operator-path repair (independent rereview
``2026-08-07-saea-r0-script-engineering-review-assessment.md`` finding B1):
``python -m some.package`` only ever executes ``some/package/__main__.py`` --
never a package's own ``__init__.py`` (that module-execution special case is
reserved for ``__main__.py`` alone). A prior ``if __name__ == "__main__":``
guard here was therefore dead code as a ``python -m`` entry point; it has
been removed in favour of an actual ``__main__.py`` (a two-line bridge to
``main`` below) plus a ``saea-driver`` console script
(``pyproject.toml``'s ``[project.scripts]``) -- both call exactly this
module's own ``main``, so there is exactly one implementation of CLI dispatch
regardless of which entry an operator uses.
"""

from __future__ import annotations

# build_manifest re-exported here (as the original flat driver.py's own
# `from .bundle import (..., build_manifest, ...)` accidentally did) because
# tests/unit/test_bundle.py does
# ``monkeypatch.setattr(driver_module, "build_manifest", ...)`` where
# ``driver_module`` IS this package -- ``bundled.py``'s own call sites reach
# it through a live reference to this package object rather than a bare/
# imported name, specifically so that patch is observed; see bundled.py's
# module comment.
from ..bundle import build_manifest
from .bundled import run_experiment_bundled
from .cli import _cli_finalize, _cli_run, _cli_score, _cli_smoke, main
from .run import _NO_SAMPLER_PROVIDED_REASON, load_split, run_experiment

__all__ = [
    "build_manifest",
    "load_split",
    "main",
    "run_experiment",
    "run_experiment_bundled",
    "_NO_SAMPLER_PROVIDED_REASON",
    "_cli_finalize",
    "_cli_run",
    "_cli_score",
    "_cli_smoke",
]
