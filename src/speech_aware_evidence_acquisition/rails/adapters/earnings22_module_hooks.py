"""Earnings-22's model-free direct layer for the shared consumption module.

Reuse the generic transcription request and numeric-unit parser, without
Earnings-21's ConEC terms, source pins or component admissions. No E22 own null
or system layer is established by this profile. All armed components and locks
remain refused until separately registered and validated on this carrier.
The existing whole-dev adapter, shared executor and official WER scorer retain
their own contracts; this file declares no experiment, roster or source release.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..consumption_module import DIRECT_LAYER_KEYS, CarrierHooks
from .earnings_module_hooks import DIRECT_PROGRAM, earnings_tool_offer_units

PROFILE = "earnings22"
LOCK_BASELINE_FRAGMENT = "e22-native-window-direct-base-v1"
DEFAULT_DELIVER_NORMALISER = "saea-deliver-earnings22-text-v1"
_REPO_ROOT = Path(__file__).resolve().parents[4]


def carrier_module_hooks(*, repo_root: Path | None = None) -> CarrierHooks:
    """Resolve an all-off composition layer, with no E22 component admission."""

    root = _REPO_ROOT if repo_root is None else Path(repo_root)

    def lock_layer() -> Mapping[str, object]:
        from ...core.config import read_fragment  # noqa: PLC0415

        fragment = read_fragment(root, "baseline", LOCK_BASELINE_FRAGMENT)
        return {key: fragment[key] for key in DIRECT_LAYER_KEYS}

    return CarrierHooks(
        profile=PROFILE,
        lock_layer=lock_layer,
        # This is the shared direct program, not a claim of an E22 flight.
        flown_programs={(1, None): DIRECT_PROGRAM},
        delivered_units=earnings_tool_offer_units,
        default_deliver_normaliser=lambda: DEFAULT_DELIVER_NORMALISER,
        roster_pin_paths=(),
        tool_offer_units=earnings_tool_offer_units,
        carrier_components={},
    )
