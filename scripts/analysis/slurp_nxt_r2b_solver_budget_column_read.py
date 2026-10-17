#!/usr/bin/env python3
"""slurp_nxt_r2b_solver_budget_column_read.py -- the preregistered READ of NX-T R2b (the Solver reasoning-budget raise on the Thinking core, TRAIN Fold B).

A thin entry over the NX-T R2 reader ``slurp_nxt_thinking_budget_column_read.py``: it loads a SECOND copy of that module with the family parameter set to
``nxt_r2b_family`` (``NXT_COLUMN_READ_FAMILY``), so R2's own module, and R2's behaviour, are untouched. The copy reads the R2b arm table (``nxt_r2b_arms.json``:
a reasoning budget AND a completion cap per node setting), counts cap hits against each node's own cap, and applies the R2b words for an arm whose budget is ABOVE
the delivering one (the R2 "cheaper" wording inverts):

  GAIN                  SLU CI95 lower bound > +|o|                                   (the raised Solver budget raises the score beyond the declared A/A width)
  HARM                  SLU CI95 upper bound < -|o|                                   (the raised budget loses more than the declared A/A width)
  NEEDS-NO-MORE-BUDGET  SLU CI95 upper bound <= +1.49 pp and intent CI95 upper bound <= +0.65 pp   (decision 190 floors: no resolved gain)
  UNRESOLVED            otherwise

with |o| = 1.15 pp (the declared same-core A/A offset; no twin flies) -- the first rule that applies. Stages (columns | smoke | read) are R2's. Model-free; no utterance
text, transcript, gold label, model output or reasoning text is printed or persisted.

    python -B scripts/analysis/slurp_nxt_r2b_solver_budget_column_read.py --stage smoke --data-root $SPEECHRL_DATA_DIR
    python -B scripts/analysis/slurp_nxt_r2b_solver_budget_column_read.py --stage read  --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
IMPL = _HERE / "slurp_nxt_thinking_budget_column_read.py"
FAMILY = "nxt_r2b_family"
MODULE_NAME = "slurp_nxt_thinking_budget_column_read__nxt_r2b_family"
FAMILY_ENV = "NXT_COLUMN_READ_FAMILY"


def load():
    """The R2 reader module, loaded under its own name with the R2b family selected (cached)."""

    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    previous = os.environ.get(FAMILY_ENV)
    os.environ[FAMILY_ENV] = FAMILY
    try:
        spec = importlib.util.spec_from_file_location(MODULE_NAME, IMPL)
        module = importlib.util.module_from_spec(spec)
        sys.modules[MODULE_NAME] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(MODULE_NAME, None)
            raise
    finally:
        if previous is None:
            os.environ.pop(FAMILY_ENV, None)
        else:
            os.environ[FAMILY_ENV] = previous
    return module


def __getattr__(name: str):
    return getattr(load(), name)


def main(argv=None) -> int:
    return load().main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
