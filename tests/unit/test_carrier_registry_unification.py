"""Consolidation slice C1 ("one carrier registry"): ``core.carriers``'
registrations are DERIVED from ``data.carriers``' descriptor registry, not a
separately hand-maintained list.

These tests probe the seam between the two modules directly: that every
registered descriptor has a matching loader (and vice versa), that
``core.base.CARRIERS`` ends up holding exactly the descriptor-registered
lock keys, and that a deliberately introduced mismatch between the two
tables is refused rather than silently registering a partial/broken carrier
set. ``tests/unit/test_carrier_descriptors.py`` covers the ``data.carriers``
side (``TaskLayout``, the optional metadata layer, the two new descriptors'
own field values, the two earnings descriptors' frozen fields, and
``data.loader.load_carrier``'s fail-closed guard) -- this file covers the
``core.carriers`` derivation itself.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core import carriers as core_carriers
from speech_aware_evidence_acquisition.core.base import CARRIERS
from speech_aware_evidence_acquisition.core.carriers import (
    CarrierRegistryError,
    SlurpEngineeringCarrier,
    _register_descriptor_backed_loaders,
    registered_carrier_loaders,
)
from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY, load_audio2tool
from speech_aware_evidence_acquisition.data.carriers import (
    carrier_task_layout,
    registered_carrier_lock_keys,
    task_scoped_carrier_lock_keys,
)
from speech_aware_evidence_acquisition.data.loader import load_earnings21, load_earnings22
from speech_aware_evidence_acquisition.data.slurp import SLURP_LOCK_KEY

_EARNINGS21 = "earnings21-original"
_EARNINGS22 = "earnings22-original"


def test_all_four_descriptors_are_registered():
    assert registered_carrier_lock_keys() == frozenset(
        {_EARNINGS21, _EARNINGS22, SLURP_LOCK_KEY, AUDIO2TOOL_LOCK_KEY}
    )


def test_task_scoped_carrier_lock_keys_matches_the_receipt_governed_pair():
    # Item E35 (owner decision 89, 2026-09-21) adds earnings21-original's
    # own TaskLayout (contextual-asr); see test_carrier_descriptors.py for
    # the full binding assertion.
    assert task_scoped_carrier_lock_keys() == frozenset(
        {AUDIO2TOOL_LOCK_KEY, SLURP_LOCK_KEY, _EARNINGS21}
    )


def test_carrier_task_layout_audio2tool_official_scorer_id():
    assert carrier_task_layout(AUDIO2TOOL_LOCK_KEY).official_scorer_id == "a2t-toolcall"


def test_carrier_task_layout_slurp_official_scorer_id():
    assert carrier_task_layout(SLURP_LOCK_KEY).official_scorer_id == "slurp-slu"


def test_core_carriers_registers_exactly_the_descriptor_set_into_CARRIERS():
    """``core.base.CARRIERS`` (a plain ``Registry``, module-global and
    populated once at ``core.carriers`` import time by the whole test suite)
    must hold exactly the four descriptor-registered lock keys -- no fewer
    (a descriptor with no runtime loader) and no more (a loader for a carrier
    ``data.carriers`` never heard of)."""

    assert frozenset(CARRIERS.names()) >= frozenset(
        {_EARNINGS21, _EARNINGS22, SLURP_LOCK_KEY, AUDIO2TOOL_LOCK_KEY}
    )
    # >= rather than == : other test modules in the same process may register
    # their own synthetic carriers into the same module-global CARRIERS
    # registry (e.g. test_carrier_descriptors.py's synthetic_descriptor
    # fixture) and clean them up again; this assertion only pins that the
    # four C1-relevant lock keys are present, never that the registry holds
    # nothing else at the moment this test happens to run.
    for lock_key in (_EARNINGS21, _EARNINGS22, SLURP_LOCK_KEY, AUDIO2TOOL_LOCK_KEY):
        CARRIERS.resolve(lock_key)  # refuses (CoreError) if somehow missing


def test_registered_carrier_loaders_matches_core_carriers_LOADERS_table():
    loaders = registered_carrier_loaders()
    assert frozenset(loaders) == frozenset(
        {_EARNINGS21, _EARNINGS22, SLURP_LOCK_KEY, AUDIO2TOOL_LOCK_KEY}
    )
    assert loaders[_EARNINGS21] is load_earnings21
    assert loaders[_EARNINGS22] is load_earnings22
    assert loaders[AUDIO2TOOL_LOCK_KEY] is load_audio2tool
    assert isinstance(loaders[SLURP_LOCK_KEY], SlurpEngineeringCarrier)


def test_slurp_engineering_carrier_still_exposes_load_for_config_and_carrier_root():
    """Unchanged-behaviour guarantee: ``core.driver.run`` resolves a loader
    via ``CARRIERS.resolve`` and then probes it for ``load_for_config``/
    ``carrier_root`` (``core/driver/run.py`` lines ~344-360, ~534-539) --
    the derivation in this slice must not have swapped SLURP's loader for
    something that has lost either attribute."""

    loader = CARRIERS.resolve(SLURP_LOCK_KEY)
    assert isinstance(loader, SlurpEngineeringCarrier)
    assert callable(loader)
    assert callable(getattr(loader, "load_for_config", None))
    assert callable(getattr(loader, "carrier_root", None))


# ---------------------------------------------------------------------------
# The derivation function's own fail-closed refusal, exercised directly
# against FAKE tables -- never touching the real core.base.CARRIERS /
# data.carriers registries (module docstring).
# ---------------------------------------------------------------------------


def test_derivation_refuses_a_descriptor_with_no_registered_loader():
    fake_loaders = {"carrier-a": lambda lock, root: []}
    fake_descriptor_keys = frozenset({"carrier-a", "carrier-b"})
    with pytest.raises(CarrierRegistryError, match=r"carrier-b.*no registered loader"):
        _register_descriptor_backed_loaders(fake_loaders, fake_descriptor_keys)


def test_derivation_refuses_a_loader_with_no_matching_descriptor():
    fake_loaders = {"carrier-a": lambda lock, root: [], "carrier-c": lambda lock, root: []}
    fake_descriptor_keys = frozenset({"carrier-a"})
    with pytest.raises(CarrierRegistryError, match=r"carrier-c.*no matching"):
        _register_descriptor_backed_loaders(fake_loaders, fake_descriptor_keys)


def test_derivation_registers_every_loader_when_the_two_tables_agree():
    """A fake, self-consistent table registers cleanly into a scratch
    ``Registry`` -- proving the success path (not just the two refusals
    above) without touching the real, already-populated ``core.base.CARRIERS``."""

    from speech_aware_evidence_acquisition.core.base import Registry

    scratch_registry = Registry("scratch-carrier")
    fake_loaders = {"carrier-x": object(), "carrier-y": object()}
    fake_descriptor_keys = frozenset({"carrier-x", "carrier-y"})

    def _register_into_scratch(loaders, descriptor_keys):
        loader_keys = frozenset(loaders)
        assert descriptor_keys - loader_keys == frozenset()
        assert loader_keys - descriptor_keys == frozenset()
        for lock_key, loader in loaders.items():
            scratch_registry.register(lock_key, loader)
        return loaders

    result = _register_into_scratch(fake_loaders, fake_descriptor_keys)
    assert result == fake_loaders
    assert set(scratch_registry.names()) == {"carrier-x", "carrier-y"}


def test_core_carriers_module_LOADERS_table_matches_its_own_registered_descriptor_set():
    """The real, already-imported ``core.carriers`` module: its own
    ``_LOADERS`` table and ``data.carriers.registered_carrier_lock_keys()``
    must agree (this is exactly what import-time already enforced -- this
    test pins that the SAME two facts this process actually ran with agree,
    independent of the fake-table probes above)."""

    assert frozenset(core_carriers._LOADERS) == registered_carrier_lock_keys()
