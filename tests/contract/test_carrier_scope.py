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


@pytest.mark.requires_wsl2_execution_authority
def test_p1_exposure_names_earnings21_but_plan_carrier_is_general_audio(world):
    """Campaign probe P1: exposure row names earnings21-original, plan carrier fsd50k.

    The fixture's default ledger row already carries ``earnings21-original dev`` in the
    carrier column (``world.CARRIER``); a plan claiming the general-audio carrier
    ``fsd50k`` must still be refused even though the row was pre-registered. (This
    variant is refused at the row/plan carrier-binding step, since the row never
    names fsd50k at all -- see the next test for the denylist step itself.)"""

    _add_lock_dataset(world, "fsd50k", profiles=["retained-cross-domain"])
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(world.plan(carrier_lock_key="fsd50k"))


@pytest.mark.requires_wsl2_execution_authority
def test_p1_denylist_path_is_pinned_when_row_also_names_general_audio_carrier(world):
    """Standing regression for the denylist check itself (not just row binding).

    Here the exposure row is made to legitimately name ``fsd50k`` too, so the
    carrier-binding step passes and the touch reaches carrier *resolution*. The
    general-audio denylist inside ``_resolve_carrier_dataset_entry`` must still
    refuse it. Without this variant, a future refactor could silently delete the
    denylist check and P1 would keep passing via row-binding mismatch alone."""

    _add_lock_dataset(world, "fsd50k", profiles=["retained-cross-domain"])
    plan = _row(world, carrier_cell="fsd50k dev", carrier_lock_key="fsd50k")
    with pytest.raises(GateClosed, match="general-audio"):
        world.gate().assert_model_touch_allowed(plan)


@pytest.mark.requires_wsl2_execution_authority
def test_ambiguous_two_carrier_cell_is_refused(world):
    """A row naming two known carriers cannot authorize either one.

    Closes the unanchored-substring bypass: under the old
    ``plan.carrier_lock_key in carrier_cell`` check, a single pre-registered row
    naming both carriers would have satisfied the check for either carrier
    identity, letting one budget row be claimed twice under different carriers
    without a fresh pre-registration."""

    _add_lock_dataset(world, "earnings22-original", profiles=["speech-aware-core"])
    plan = _row(
        world,
        carrier_cell="earnings21-original + earnings22-original, dev",
        carrier_lock_key="earnings21-original",
    )
    with pytest.raises(GateClosed, match="exactly one known carrier lock key"):
        world.gate().assert_model_touch_allowed(plan)


@pytest.mark.requires_wsl2_execution_authority
def test_substring_prefix_carrier_name_does_not_falsely_match(world):
    """A carrier name that is a textual prefix of another carrier's name must not
    be accepted by an unanchored substring test (e.g. "earnings2" must not match
    inside "earnings22-original")."""

    _add_lock_dataset(world, "earnings2", profiles=["speech-aware-core"])
    _add_lock_dataset(world, "earnings22-original", profiles=["speech-aware-core"])
    plan = _row(world, carrier_cell="earnings22-original dev", carrier_lock_key="earnings2")
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(plan)


def test_resolve_carrier_dataset_entry_directly_refuses_model_and_unknown_keys(world):
    """Direct coverage of ``_resolve_carrier_dataset_entry``'s own refusal for a
    model key or an unregistered key. Through the full
    ``assert_model_touch_allowed`` path this branch is now only reachable when
    the exposure row itself names a *known dataset* carrier that still isn't the
    plan's carrier (row-binding refuses model/unknown keys first, since they can
    never be the row's unambiguous named carrier); this test keeps the branch
    itself exercised directly."""

    gate = world.gate()
    with pytest.raises(GateClosed, match="not a dataset entry"):
        gate._resolve_carrier_dataset_entry(MODEL_LOCK_KEY)
    with pytest.raises(GateClosed, match="not a dataset entry"):
        gate._resolve_carrier_dataset_entry("totally-unregistered-key")


@pytest.mark.requires_wsl2_execution_authority
def test_plan_carrier_that_is_a_lock_model_entry_is_refused(world):
    """A model lock key can never authorize as a speech carrier."""

    plan = _row(world, carrier_cell=f"{MODEL_LOCK_KEY} dev", carrier_lock_key=MODEL_LOCK_KEY)
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(plan)


@pytest.mark.requires_wsl2_execution_authority
def test_valid_carrier_but_exposure_row_names_a_different_carrier_is_refused(world):
    """The plan's carrier is legitimate, but the pre-registered row names another one."""

    _add_lock_dataset(world, "earnings22-original", profiles=["speech-aware-core"])
    plan = _row(world, carrier_cell="earnings22-original dev", carrier_lock_key=world.CARRIER)
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(plan)


@pytest.mark.requires_wsl2_execution_authority
def test_carrier_lock_entry_without_profiles_field_fails_closed(world):
    """A dataset entry present in the lock but lacking a profiles field is refused,
    not silently treated as in-scope."""

    _add_lock_dataset(world, "orphan-carrier", with_profiles=False)
    plan = _row(world, carrier_cell="orphan-carrier dev", carrier_lock_key="orphan-carrier")
    with pytest.raises(GateClosed, match="profiles"):
        world.gate().assert_model_touch_allowed(plan)


@pytest.mark.requires_wsl2_execution_authority
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


@pytest.mark.requires_wsl2_execution_authority
def test_legitimate_saea_row_and_earnings22_plan_is_accepted(world):
    """No false positive: a second genuine core carrier with a correctly bound
    exposure row still opens the gate."""

    _add_lock_dataset(world, "earnings22-original", profiles=["speech-aware-core"])
    plan = _row(world, carrier_cell="earnings22-original dev", carrier_lock_key="earnings22-original")
    world.gate().assert_model_touch_allowed(plan)
