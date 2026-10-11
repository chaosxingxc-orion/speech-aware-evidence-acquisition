"""SLURP lock v2.2 (module step 7, NX 2026-10-09): the v4g delivery normaliser.

Records ``docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md`` and
``docs/readiness/2026-10-09-slurp-module-step7-v4g-default-v1.md``. v2.2 = the v2.1
layer with ONE leaf moved, ``native_episode.deliver_normaliser.normaliser``
``saea-deliver-normalise-v3`` -> ``saea-deliver-normalise-v4g`` (component
``delivery-normaliser``, state ``on (lock)``). A block naming no ``lock``, ``v2.0`` or
``v2.1`` compiles exactly as before. Since owner decision 249 (2026-10-10) v2.2 is the
module's ``CURRENT_LOCK`` (the null arm of new cells and the harness ``module`` class's
OFF arm); it is still selected only by a block's ``lock`` key. The normaliser is version ``1`` and loads its pinned TRAIN tables by hash
(``rails.delivery_normalisers``).

CONSTRUCTION VARIANT (2026-10-12). Both locks have a construction variant, ``consumption_module.construction_roster: "r01c"``
(``slurp_module_construction.py``), which re-pins the ``train-exemplars`` pool to the minus-r01 twin so the construction roster R01C
(whose rows lie inside the lock's own pool) passes the runner's knowledge-source guard. It is a mechanism over the lock, not a lock: every
other leaf is byte-identical, the loader accepts it only on R01C, and v2.3 refuses it (the ``ace-playbook`` i0 anchor names 50 R01C ids).
It exists ONLY to flow the material-source column (the typed loop's proposer tables and ACE reflector material) without self-leakage; it
never delivers a benefit claim.
"""

from __future__ import annotations

import copy
from typing import Callable, Mapping

LOCK_V2_0, LOCK_V2_1, LOCK_V2_2 = "v2.0", "v2.1", "v2.2"
V3_NORMALISER = "saea-deliver-normalise-v3"
LOCK_V2_2_DELIVER_NORMALISER = "saea-deliver-normalise-v4g"
LOCK_V2_2_DELIVER_NORMALISER_VERSION = "1"

#: ``{lock version: the deliver normaliser id its layer carries}``.
LOCK_DELIVER_NORMALISERS: Mapping[str, str] = {
    LOCK_V2_0: V3_NORMALISER,
    LOCK_V2_1: V3_NORMALISER,
    LOCK_V2_2: LOCK_V2_2_DELIVER_NORMALISER,
}

#: Lock-layer component states v2.2 records beyond v2.1.
LOCK_V2_2_COMPONENT_STATES: Mapping[str, Mapping[str, str]] = {
    "delivery-normaliser": {
        "state": "on (lock)",
        "record": "docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md",
        "normaliser": LOCK_V2_2_DELIVER_NORMALISER,
    },
}


def default_deliver_normaliser_for_lock(lock: str | None) -> str:
    """The profile's default delivery normaliser under a lock id: v4g under ``v2.2``,
    v3 under ``v2.0`` / ``v2.1`` / no ``lock`` key."""

    if lock is None:
        return V3_NORMALISER
    try:
        return LOCK_DELIVER_NORMALISERS[lock]
    except KeyError:
        raise KeyError(f"{lock!r} is not a SLURP lock version; known: {sorted(LOCK_DELIVER_NORMALISERS)}") from None


def lock_deliver_normalisers() -> Mapping[str, Callable[[], str]]:
    """The ``CarrierHooks.lock_deliver_normalisers`` table."""

    return {lock: (lambda name=name: name) for lock, name in LOCK_DELIVER_NORMALISERS.items()}


def layer_from_v2_1(v2_1_layer: Mapping[str, object]) -> Mapping[str, object]:
    """The v2.1 layer with the delivery normaliser moved v3 -> v4g. Fail-closed on the v3
    starting leaf, on v4g's registration and on the guard constants the lock record pins."""

    from ...core.base import DELIVERY_NORMALISERS  # noqa: PLC0415
    from .. import delivery_normalisers as dn  # noqa: PLC0415
    from ..consumption_module import ConsumptionModuleConfigError  # noqa: PLC0415

    if (dn.DELIVER_NORMALISE_V4G != LOCK_V2_2_DELIVER_NORMALISER
            or dn.DELIVER_NORMALISE_V4G_VERSION != LOCK_V2_2_DELIVER_NORMALISER_VERSION
            or dn.V4G_GUARDS.ti1_min_exemplars != 100
            or dn.V4G_GUARDS.ee_wilson_max_upper != 0.10
            or dn.V4G_GUARDS.ee_wilson_z != 1.959963984540054
            or LOCK_V2_2_DELIVER_NORMALISER not in DELIVERY_NORMALISERS.names()):
        raise ConsumptionModuleConfigError(
            f"lock {LOCK_V2_2}: {LOCK_V2_2_DELIVER_NORMALISER} version "
            f"{LOCK_V2_2_DELIVER_NORMALISER_VERSION} is not registered with the locked guard constants"
        )
    layer = copy.deepcopy(dict(v2_1_layer))
    deliver = layer["native_episode"].get("deliver_normaliser")
    if not isinstance(deliver, dict) or deliver.get("normaliser") != V3_NORMALISER:
        raise ConsumptionModuleConfigError(
            f"lock {LOCK_V2_2}: the v2.1 layer's deliver normaliser is not {V3_NORMALISER!r}"
        )
    deliver["normaliser"] = LOCK_V2_2_DELIVER_NORMALISER
    return layer
