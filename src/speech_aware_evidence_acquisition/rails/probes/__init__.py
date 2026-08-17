"""Probe-specific flight orchestration built on top of the rails layer.

A registered probe with more than the two frozen rails arms
(``rails.runner.RAILS_ARMS`` is fixed to exactly ``("zero-supply",
"supplied")``) needs its own orchestration loop over the SAME primitives
(``TaskAdapter.assemble_prompt`` / ``CoreClient.complete`` /
``TaskAdapter.score``) rather than a distortion of that frozen two-arm
contract. Each probe gets its own module here; nothing is re-exported at
this package's top level (mirrors ``rails.adapters``'s own "concrete
adapters are NOT re-exported, they pull in their own carrier-specific
modules" discipline).
"""

from __future__ import annotations
