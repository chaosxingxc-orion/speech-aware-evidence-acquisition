"""Carrier loaders registered under their lock keys (the carrier seam)."""

from __future__ import annotations

from .base import CARRIERS
from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY, load_audio2tool
from ..data.loader import load_earnings21, load_earnings22

CARRIERS.register("earnings21-original", load_earnings21)
CARRIERS.register("earnings22-original", load_earnings22)
# P1 scaffold: frozen-receipt-scoped Audio2Tool loader (data/audio2tool.py).
# Runnable end to end today against a synthetic lock; against the REAL
# umbrella lock it fails closed at lock resolution until the owner amendment
# adds the 'audio2tool' entry -- deliberately the only missing piece.
CARRIERS.register(AUDIO2TOOL_LOCK_KEY, load_audio2tool)
