"""Carrier loaders registered under their lock keys (the carrier seam)."""

from __future__ import annotations

from .base import CARRIERS
from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY, load_audio2tool
from ..data.loader import load_earnings21, load_earnings22
from ..data.slurp import (
    SLURP_LOCK_KEY,
    load_slurp_engineering_carrier,
    slurp_governed_carrier_root,
)


class SlurpEngineeringCarrier:
    """The label-free SLURP engineering view plus its governed media root.

    The lock's ``local_subdir`` names an upstream raw checkout, while the
    hash-pinned natural speech used here lives beside the governed metadata.
    Exposing an explicit root resolver lets the generic driver retain its
    carrier confinement rail without special-casing SLURP.
    """

    def __call__(self, lock, root):
        return load_slurp_engineering_carrier(lock, root)

    def carrier_root(self, lock, root):
        return slurp_governed_carrier_root(lock, root)

CARRIERS.register("earnings21-original", load_earnings21)
CARRIERS.register("earnings22-original", load_earnings22)
CARRIERS.register(SLURP_LOCK_KEY, SlurpEngineeringCarrier())
# P1 scaffold: frozen-receipt-scoped Audio2Tool loader (data/audio2tool.py).
# Runnable end to end against both a synthetic lock and the real umbrella
# lock -- the 'audio2tool' entry landed in docs/datasets.lock.json
# (asset_catalog, status COMPLETE), and the bounded discovery probe it
# gates is admitted by the 2026-08-15 owner amendment (umbrella
# wiki/experiments/speech-aware-evidence-acquisition/
# 2026-08-15-owner-go-dual-track-agentic.md, Amendment 1).
CARRIERS.register(AUDIO2TOOL_LOCK_KEY, load_audio2tool)
