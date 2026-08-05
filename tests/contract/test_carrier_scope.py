"""T2 regression probes: carrier scope allowlist + exposure carrier binding.

Invariant I2 (r0-repair design §3): a plan carrier must resolve to a genuine speech
dataset entry in the umbrella lock (never a model entry, never a general-audio asset,
never an entry whose scope cannot be proven), AND the pre-registered exposure row's
carrier column must actually name that same carrier. Campaign probe P1: an exposure
row naming earnings21-original must not authorize a plan whose carrier is a
general-audio asset such as ``fsd50k``.
"""

import pytest

from speech_aware_evidence_acquisition.contracts import (
    ALLOWED_CARRIER_PROFILES,
    MODEL_LOCK_KEY,
    GateClosed,
    general_audio_deny_lock_keys,
)

from gate_fixture import GateFixture


@pytest.fixture()
def world(tmp_path):
    return GateFixture(tmp_path)


def _add_lock_dataset(world, name, *, kind="dataset", profiles=None, with_profiles=True):
    """Register an extra ``asset_catalog``-shaped entry in the fixture's synthetic lock."""

    entry = {"name": name, "kind": kind}
    if with_profiles:
        entry["profiles"] = profiles if profiles is not None else ["speech-aware-core"]
    world.lock.setdefault("asset_catalog", []).append(entry)
    return entry


def _row(world, *, carrier_cell, carrier_lock_key=None, note="probe"):
    world.write_ledger_rows(
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {carrier_cell} | dev | {'a' * 64} | no "
        f"| 10 | 600 | 1.0 | none | none | {note} |\n"
    )
    return world.plan(carrier_lock_key=carrier_lock_key or world.CARRIER)


def test_constants_are_frozen_to_the_expected_scope(world):
    deny = general_audio_deny_lock_keys(world.source_root)
    assert deny == frozenset({"fsd50k", "audioset-metadata-features", "esc-50"})
    assert ALLOWED_CARRIER_PROFILES == frozenset(
        {
            "speech-aware-core",
            "speech-aware-secondary",
            "speech-aware-diagnostics",
            "speech-aware-small-public",
        }
    )
    # The denylisted general-audio profile can never be one of the allowed profiles.
    assert not (deny & ALLOWED_CARRIER_PROFILES)


def test_p1_exposure_names_earnings21_but_plan_carrier_is_general_audio(world):
    """Campaign probe P1: exposure row names earnings21-original, plan carrier fsd50k.

    The fixture's default ledger row already carries ``earnings21-original dev`` in the
    carrier column (``world.CARRIER``); a plan claiming the general-audio carrier
    ``fsd50k`` must still be refused even though the row was pre-registered."""

    _add_lock_dataset(world, "fsd50k", profiles=["retained-cross-domain"])
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(world.plan(carrier_lock_key="fsd50k"))


def test_plan_carrier_that_is_a_lock_model_entry_is_refused(world):
    """A model lock key can never authorize as a speech carrier."""

    plan = _row(world, carrier_cell=f"{MODEL_LOCK_KEY} dev", carrier_lock_key=MODEL_LOCK_KEY)
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(plan)


def test_valid_carrier_but_exposure_row_names_a_different_carrier_is_refused(world):
    """The plan's carrier is legitimate, but the pre-registered row names another one."""

    _add_lock_dataset(world, "earnings22-original", profiles=["speech-aware-core"])
    plan = _row(world, carrier_cell="earnings22-original dev", carrier_lock_key=world.CARRIER)
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(plan)


def test_carrier_lock_entry_without_profiles_field_fails_closed(world):
    """A dataset entry present in the lock but lacking a profiles field is refused,
    not silently treated as in-scope."""

    _add_lock_dataset(world, "orphan-carrier", with_profiles=False)
    plan = _row(world, carrier_cell="orphan-carrier dev", carrier_lock_key="orphan-carrier")
    with pytest.raises(GateClosed, match="profiles"):
        world.gate().assert_model_touch_allowed(plan)


def test_out_of_scope_profile_is_refused_even_when_not_explicitly_denylisted(world):
    """Defense in depth: a dataset whose profiles simply do not intersect the
    speech-aware scope is refused even if it is not one of the three named
    general-audio assets."""

    _add_lock_dataset(world, "some-other-catalog-asset", profiles=["local-candidates"])
    plan = _row(
        world,
        carrier_cell="some-other-catalog-asset dev",
        carrier_lock_key="some-other-catalog-asset",
    )
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(plan)


def test_legitimate_saea_row_and_earnings22_plan_is_accepted(world):
    """No false positive: a second genuine core carrier with a correctly bound
    exposure row still opens the gate."""

    _add_lock_dataset(world, "earnings22-original", profiles=["speech-aware-core"])
    plan = _row(world, carrier_cell="earnings22-original dev", carrier_lock_key="earnings22-original")
    world.gate().assert_model_touch_allowed(plan)
