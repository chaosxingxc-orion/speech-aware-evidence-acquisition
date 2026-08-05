"""Carrier loaders registered under their lock keys (the carrier seam)."""

from __future__ import annotations

from .base import CARRIERS
from ..data.loader import load_earnings21, load_earnings22

CARRIERS.register("earnings21-original", load_earnings21)
CARRIERS.register("earnings22-original", load_earnings22)
