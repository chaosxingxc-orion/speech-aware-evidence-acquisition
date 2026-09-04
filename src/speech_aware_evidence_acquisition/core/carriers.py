"""Carrier loaders registered under their lock keys (the carrier seam).

Consolidation slice C1 ("one carrier registry"): registrations used to be a
parallel, hand-maintained list of ``CARRIERS.register(...)`` calls that had
to be kept in sync with ``data.carriers``' own descriptor registry by
convention -- exactly the kind of duplicated "one true definition" this
study's carrier layer otherwise avoids (``data/carriers.py`` module
docstring). Registrations are now DERIVED from that descriptor registry: the
only fact this module still hand-lists is ``_LOADERS`` (which loader serves
which lock key); :func:`_register_descriptor_backed_loaders` registers every
one of them into ``core.base.CARRIERS`` and fails closed at IMPORT time if
``_LOADERS`` and ``data.carriers.registered_carrier_lock_keys()`` ever
disagree in either direction -- a descriptor with no loader, or a loader with
no descriptor. Adding a future carrier means registering ONE new descriptor
(``data.carriers.register_carrier_descriptor``) plus ONE new entry in
``_LOADERS`` -- never separately maintained lists that can silently drift
apart.
"""

from __future__ import annotations

from typing import Mapping

from .base import CARRIERS
from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY, load_audio2tool
from ..data.carriers import registered_carrier_lock_keys
from ..data.loader import load_earnings21, load_earnings22
from ..data.slurp import (
    SLURP_LOCK_KEY,
    load_slurp_engineering_carrier,
    load_slurp_speech_native_carrier,
    slurp_governed_carrier_root,
)


class CarrierRegistryError(RuntimeError):
    """``data.carriers``' descriptor registry and this module's loader table
    (``_LOADERS``) disagree: a descriptor has no registered loader, or a
    loader is registered for a lock key ``data.carriers`` has never heard
    of."""


class SlurpEngineeringCarrier:
    """The label-free SLURP engineering view plus its governed media root.

    The lock's ``local_subdir`` names an upstream raw checkout, while the
    hash-pinned natural speech used here lives beside the governed metadata.
    Exposing an explicit root resolver lets the generic driver retain its
    carrier confinement rail without special-casing SLURP.
    """

    def __call__(self, lock, root):
        return load_slurp_engineering_carrier(lock, root)

    def load_for_config(self, lock, root, *, dataset_path, values):
        split_name = values.get("split_name")
        count = values.get("count")
        if not isinstance(split_name, str) or not split_name:
            raise ValueError("SLURP speech-native dataset split_name must be non-empty")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError("SLURP speech-native dataset count must be positive")
        return load_slurp_speech_native_carrier(
            lock,
            root,
            config_path=dataset_path,
            expected_split_name=split_name,
            expected_count=count,
        )

    def carrier_root(self, lock, root):
        return slurp_governed_carrier_root(lock, root)


# The one explicit fact this module still hand-lists: which loader serves
# which lock key. Every key here must have a matching ``data.carriers``
# descriptor, and every registered descriptor must have a matching entry
# here -- enforced by :func:`_register_descriptor_backed_loaders` below, not
# merely by convention.
_LOADERS: Mapping[str, object] = {
    "earnings21-original": load_earnings21,
    "earnings22-original": load_earnings22,
    SLURP_LOCK_KEY: SlurpEngineeringCarrier(),
    # P1 scaffold: frozen-receipt-scoped Audio2Tool loader (data/audio2tool.py).
    # Runnable end to end against both a synthetic lock and the real umbrella
    # lock -- the 'audio2tool' entry landed in docs/datasets.lock.json
    # (asset_catalog, status COMPLETE), and the bounded discovery probe it
    # gates is admitted by the 2026-08-15 owner amendment (umbrella
    # wiki/experiments/speech-aware-evidence-acquisition/
    # 2026-08-15-owner-go-dual-track-agentic.md, Amendment 1).
    AUDIO2TOOL_LOCK_KEY: load_audio2tool,
}


def _register_descriptor_backed_loaders(
    loaders: Mapping[str, object],
    descriptor_lock_keys: frozenset[str],
) -> Mapping[str, object]:
    """Register every one of ``loaders`` into ``core.base.CARRIERS``,
    fail-closed if ``loaders`` and ``descriptor_lock_keys`` disagree in
    EITHER direction:

    1. a lock key in ``descriptor_lock_keys`` with no entry in ``loaders`` --
       ``data.carriers`` knows this carrier's layout facts but no code path
       can actually load its samples;
    2. a lock key in ``loaders`` with no entry in ``descriptor_lock_keys`` --
       a loader is registered for a carrier ``data.carriers`` has never heard
       of, so no consumer (``data.references``, ``core.evidence``,
       ``contracts.gate_identity``, ...) can resolve its reference/evidence/
       entity/task facts.

    Exposed as its own function (rather than inlined at module scope) so
    ``tests/unit/test_carrier_registry_unification.py`` can simulate a
    mismatch against FAKE tables without registering anything into the real
    ``core.base.CARRIERS``/``data.carriers`` registries."""

    loader_keys = frozenset(loaders)
    missing_loaders = descriptor_lock_keys - loader_keys
    if missing_loaders:
        raise CarrierRegistryError(
            f"carrier descriptor(s) {sorted(missing_loaders)} have no registered loader "
            "in core.carriers._LOADERS"
        )
    missing_descriptors = loader_keys - descriptor_lock_keys
    if missing_descriptors:
        raise CarrierRegistryError(
            f"loader(s) registered for {sorted(missing_descriptors)} have no matching "
            "data.carriers.CarrierDescriptor"
        )
    for lock_key, loader in loaders.items():
        CARRIERS.register(lock_key, loader)
    return loaders


_REGISTERED_LOADERS = _register_descriptor_backed_loaders(
    _LOADERS, registered_carrier_lock_keys()
)


def registered_carrier_loaders() -> Mapping[str, object]:
    """Every loader this module registered into ``core.base.CARRIERS``, keyed
    by lock key -- the same mapping :func:`_register_descriptor_backed_loaders`
    built at import time, exposed read-only for a caller (e.g. a test
    asserting the descriptor<->loader set matches) that needs the whole
    table rather than resolving one loader at a time through
    ``core.base.CARRIERS.resolve``."""

    return _REGISTERED_LOADERS
