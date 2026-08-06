"""Attempt schema + state-machine string constants.

Split out of the former monolithic ``core/attempts.py`` (R0 repair refactor
stage 2, pure move, no behaviour change). See ``core/attempts/__init__.py``
for the full module docstring this package shares.
"""

from __future__ import annotations

ATTEMPT_SCHEMA = "saea-attempt-v1"

STATE_RESERVED = "RESERVED"
STATE_OPENED = "OPENED"
STATE_FINALIZED = "FINALIZED"
STATE_ABORTED = "ABORTED"
