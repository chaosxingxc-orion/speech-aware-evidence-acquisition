"""Carrier loaders registered under their lock keys (the carrier seam)."""

from __future__ import annotations

from .base import CARRIERS
from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY, load_audio2tool
from ..data.loader import load_earnings21, load_earnings22

CARRIERS.register("earnings21-original", load_earnings21)
CARRIERS.register("earnings22-original", load_earnings22)
# P1 scaffold: frozen-receipt-scoped Audio2Tool loader (data/audio2tool.py).
# Runnable end to end against both a synthetic lock and the real umbrella
# lock -- the 'audio2tool' entry landed in docs/datasets.lock.json
# (asset_catalog, status COMPLETE), and the bounded discovery probe it
# gates is admitted by the 2026-08-15 owner amendment (umbrella
# wiki/experiments/speech-aware-evidence-acquisition/
# 2026-08-15-owner-go-dual-track-agentic.md, Amendment 1).
CARRIERS.register(AUDIO2TOOL_LOCK_KEY, load_audio2tool)
