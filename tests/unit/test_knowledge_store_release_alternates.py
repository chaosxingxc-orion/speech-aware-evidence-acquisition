"""Coordinator amendment, 2026-09-28 (docs/superpowers/specs/2026-09-27-
same-flight-supply-variant-instrument-design.md, "Coordinator amendment
(2026-09-28)"): the release-swap arm route.

An arm may select, for ONE store its base config names, an ALTERNATIVE
pinned release+snapshot the base ALSO declares under
``knowledge_stores.<store>.alternates`` -- never a component it discovers on
its own. Four layers, all model-free:

1. **The base field** -- ``rails.knowledge_stores`` parses and hash-verifies
   ``alternates`` exactly like the primary, and refuses a malformed one.
2. **The arm route** -- ``rails.supply_variants`` parses an arm's
   ``release_swap``, refuses a release absent from the named store's declared
   alternates, and refuses one on the delivering arm or a twin.
3. **The receipt** -- ``supply_variant_arm_record``/``supply_variant_receipt``
   record which release an arm consumed (schema v3), and
   ``validate_supply_variant_receipt`` accepts it.
4. **The runtime** -- ``core.flight.runtime.FlightRuntime._supply_action_
   router`` actually repoints the named store for that one arm, and
   ``_phase_seed_inputs``'s prepared-supply identity is sensitive to an
   alternate's pins.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
import json

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
    _knowledge_store_alternate_identity,
)
from speech_aware_evidence_acquisition.core.preparation import digest
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    KnowledgeStoreError,
    declared_alternate_release_relpaths,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    SUPPLY_VARIANT_RECEIPT_SCHEMA,
    validate_supply_variant_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    SupplyVariantError,
    SupplyVariantReleaseSwap,
    parse_supply_variant_release_swap,
    parse_supply_variants,
    supply_variant_arm_record,
    supply_variant_receipt,
)

from test_knowledge_stores import _config, _store_snapshot, _write
from test_phase_tools import _context

FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 640,
    "base_prompt_tokens": 9600,
    "tokens_per_supplied_item": 120,
}


def _add_alternate(tmp_path, config, store_id, *, marker="ALTERNATE"):
    """Mutate ``config["knowledge_stores"][store_id]`` in place, adding ONE
    alternate release+snapshot whose sole value's content is visibly
    different from the primary's (``marker`` prefixed), pinned with real
    SHA-256 bytes exactly like the primary."""

    primary_snapshot = _store_snapshot(store_id)
    alt_snapshot = replace(
        primary_snapshot,
        snapshot_id=f"{store_id}-alternate-v1",
        values=tuple(
            replace(value, content=f"{marker} {value.content}")
            for value in primary_snapshot.values
        ),
    ).validate()
    snapshot_relpath = f"knowledge/{store_id}/alternate-snapshot.json"
    snapshot_path = tmp_path / snapshot_relpath
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(alt_snapshot.frozen_json()), encoding="utf-8")
    source_relpath = f"knowledge/{store_id}/alternate-construction-source.json"
    source_sha = _write(tmp_path / source_relpath, {"ids": ["alt-train-source"]})
    release_relpath = f"knowledge/{store_id}/alternate-release.json"
    release = {
        "schema": "saea-knowledge-store-release-v1",
        "store_id": store_id,
        "store_role": store_id,
        "snapshot_sha256": alt_snapshot.content_hash(),
        "source_split_identity_hash": alt_snapshot.source_split_identity_hash,
        "builder_policy_id": alt_snapshot.builder_policy_id,
        "source": {"relpath": source_relpath, "sha256": source_sha},
    }
    release_sha = _write(tmp_path / release_relpath, release)
    config["knowledge_stores"][store_id]["alternates"] = [
        {
            "release": {"relpath": release_relpath, "sha256": release_sha},
            "snapshot": {
                "relpath": snapshot_relpath, "sha256": alt_snapshot.content_hash(),
            },
        }
    ]
    return alt_snapshot, release_relpath


# ---------------------------------------------------------------------------
# 1. The base field: rails.knowledge_stores
# ---------------------------------------------------------------------------


def test_loader_parses_alternates_and_declared_alternate_release_relpaths(tmp_path):
    config, _ = _config(tmp_path, ("intent-boundaries", "slot-contracts"))
    alt_snapshot, release_relpath = _add_alternate(tmp_path, config, "intent-boundaries")

    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    store = binding.store("intent-boundaries")
    assert len(store.alternates) == 1
    alternate = store.alternates[0]
    assert alternate.release_pin["relpath"] == release_relpath
    assert alternate.snapshot_pin["sha256"] == alt_snapshot.content_hash()
    assert store.alternate(release_relpath) is alternate
    with pytest.raises(KnowledgeStoreError, match="declares no alternate release"):
        store.alternate("knowledge/intent-boundaries/absent-release.json")
    # The other store declares no alternates: absent, empty, byte-identical.
    assert binding.store("slot-contracts").alternates == ()

    relpaths = declared_alternate_release_relpaths(config["knowledge_stores"])
    assert relpaths == {"intent-boundaries": (release_relpath,)}


def test_absent_alternates_key_composes_exactly_as_before(tmp_path):
    config, _ = _config(tmp_path, ("intent-boundaries",))
    assert "alternates" not in config["knowledge_stores"]["intent-boundaries"]
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    assert binding.store("intent-boundaries").alternates == ()
    assert declared_alternate_release_relpaths(config["knowledge_stores"]) == {}
    assert declared_alternate_release_relpaths(None) == {}
    assert declared_alternate_release_relpaths("not a mapping") == {}


@pytest.mark.parametrize(
    "mutate,match",
    [
        pytest.param(
            lambda spec: spec.__setitem__("alternates", "not-a-list"),
            "must be a list", id="not-a-list",
        ),
        pytest.param(
            lambda spec: spec["alternates"].__setitem__(0, {"release": {}}),
            "must carry exactly", id="missing-snapshot-key",
        ),
        pytest.param(
            lambda spec: spec["alternates"][0]["release"].__setitem__("sha256", "not-hex"),
            "sha256", id="bad-hash-format",
        ),
    ],
)
def test_loader_refuses_malformed_alternates(tmp_path, mutate, match):
    config, _ = _config(tmp_path, ("intent-boundaries",))
    _add_alternate(tmp_path, config, "intent-boundaries")
    mutate(config["knowledge_stores"]["intent-boundaries"])
    with pytest.raises(KnowledgeStoreError, match=match):
        load_knowledge_store_binding(config, data_root=tmp_path)


def test_loader_admits_an_alternate_whose_bytes_are_unverified_until_resolved(tmp_path):
    """Declaring an alternate that is never selected by any arm costs no
    extra load at flight assembly: only a CONTENT hash mismatch (bytes vs. a
    syntactically valid pin) is deferred, never a format or duplicate-name
    defect, which :func:`test_loader_refuses_malformed_alternates` and
    :func:`test_loader_refuses_a_duplicate_or_primary_colliding_alternate_relpath`
    already cover eagerly. The deferred hash IS caught the moment an arm
    actually resolves it -- see
    ``test_supply_action_router_refuses_a_release_alternate_whose_bytes_
    changed`` below."""

    config, _ = _config(tmp_path, ("intent-boundaries",))
    _add_alternate(tmp_path, config, "intent-boundaries")
    config["knowledge_stores"]["intent-boundaries"]["alternates"][0]["release"]["sha256"] = "f" * 64
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    assert binding.store("intent-boundaries").alternates[0].release_pin["sha256"] == "f" * 64


def test_loader_refuses_a_duplicate_or_primary_colliding_alternate_relpath(tmp_path):
    config, _ = _config(tmp_path, ("intent-boundaries",))
    _, release_relpath = _add_alternate(tmp_path, config, "intent-boundaries")
    spec = config["knowledge_stores"]["intent-boundaries"]
    # Two alternates naming the SAME release relpath.
    spec["alternates"].append(dict(spec["alternates"][0]))
    with pytest.raises(KnowledgeStoreError, match="twice"):
        load_knowledge_store_binding(config, data_root=tmp_path)
    # An alternate naming the PRIMARY's own release relpath.
    spec["alternates"] = [
        {"release": dict(spec["release"]), "snapshot": dict(spec["snapshot"])}
    ]
    with pytest.raises(KnowledgeStoreError, match="twice"):
        load_knowledge_store_binding(config, data_root=tmp_path)


# ---------------------------------------------------------------------------
# 2. The arm route: rails.supply_variants
# ---------------------------------------------------------------------------


def test_parse_supply_variant_release_swap_admits_and_refuses():
    admitted = {"intent-boundaries": ("knowledge/intent-boundaries/alternate-release.json",)}
    swap = parse_supply_variant_release_swap(
        {"store_id": "intent-boundaries", "release": admitted["intent-boundaries"][0]},
        declared_stores=("intent-boundaries", "slot-contracts"),
        declared_alternate_relpaths=admitted,
    )
    assert swap == SupplyVariantReleaseSwap(
        store_id="intent-boundaries",
        release_relpath="knowledge/intent-boundaries/alternate-release.json",
    )
    assert swap.as_json() == {
        "store_id": "intent-boundaries", "release": swap.release_relpath,
    }
    with pytest.raises(SupplyVariantError, match="absent from its declared alternates"):
        parse_supply_variant_release_swap(
            {"store_id": "slot-contracts", "release": admitted["intent-boundaries"][0]},
            declared_stores=("intent-boundaries", "slot-contracts"),
            declared_alternate_relpaths=admitted,
        )
    with pytest.raises(SupplyVariantError, match="this configuration does not declare"):
        parse_supply_variant_release_swap(
            {"store_id": "undeclared-store", "release": "x"},
            declared_stores=("intent-boundaries",),
            declared_alternate_relpaths=admitted,
        )
    with pytest.raises(SupplyVariantError, match="must be an object with exactly"):
        parse_supply_variant_release_swap(
            {"store_id": "intent-boundaries"},
            declared_stores=("intent-boundaries",),
            declared_alternate_relpaths=admitted,
        )


EX = "knowledge_stores.train-exemplars.phase_supply.solver"


def _release_swap_block(*, store="intent-boundaries", release="alt.json", extra_arm=None):
    arms = [
        {
            "arm_id": "swap", "max_supplied_items": 8,
            "release_swap": {"store_id": store, "release": release},
        },
        {"arm_id": "plan", "deliver": True, "max_supplied_items": 8},
    ]
    if extra_arm is not None:
        arms.insert(1, extra_arm)
    return {"arms": arms, "fit_estimate": dict(FIT)}


def _parse_release_swap(block=None, **kwargs):
    options = {
        "phase_id": "solver",
        "first_phase_id": "perception",
        "declared_stores": ("intent-boundaries", "slot-contracts", "train-exemplars"),
        "declared_alternate_relpaths": {"intent-boundaries": ("alt.json",)},
    }
    options.update(kwargs)
    return parse_supply_variants(block if block is not None else _release_swap_block(), **options)


def test_a_release_swap_arm_parses_and_is_absent_elsewhere():
    group = _parse_release_swap()
    swap_arm = group.arm("swap")
    assert swap_arm.release_swap == SupplyVariantReleaseSwap(
        store_id="intent-boundaries", release_relpath="alt.json",
    )
    assert swap_arm.knobs == ()
    assert swap_arm.as_json()["release_swap"] == {
        "store_id": "intent-boundaries", "release": "alt.json",
    }
    assert group.delivered_arm.release_swap is None


def test_release_swap_absent_from_declared_alternates_is_refused():
    with pytest.raises(SupplyVariantError, match="absent from its declared alternates"):
        _parse_release_swap(_release_swap_block(release="not-declared.json"))


def test_delivering_arm_cannot_carry_a_release_swap():
    block = _release_swap_block()
    block["arms"][1] = {
        "arm_id": "plan", "deliver": True, "max_supplied_items": 8,
        "release_swap": {"store_id": "intent-boundaries", "release": "alt.json"},
    }
    with pytest.raises(SupplyVariantError, match="must declare no"):
        _parse_release_swap(block)


def test_a_twin_cannot_carry_a_release_swap():
    block = _release_swap_block(extra_arm={
        "arm_id": "aa", "replicate_of": "plan", "max_supplied_items": 8,
        "release_swap": {"store_id": "intent-boundaries", "release": "alt.json"},
    })
    with pytest.raises(SupplyVariantError, match="must declare no release_swap"):
        _parse_release_swap(block)


def test_two_arms_with_the_identical_release_swap_are_refused_as_duplicates():
    block = _release_swap_block(extra_arm={
        "arm_id": "swap2", "max_supplied_items": 8,
        "release_swap": {"store_id": "intent-boundaries", "release": "alt.json"},
    })
    with pytest.raises(SupplyVariantError, match="declare the same overrides"):
        _parse_release_swap(block)


def test_twin_stays_byte_identical_to_a_under_the_release_swap_extension():
    """The twin (``replicate_of``) next to a release-swap arm still resolves
    NO overrides and NO release_swap of its own -- the extension changes
    nothing about its wire identity to the delivering arm A."""

    group = _parse_release_swap(_release_swap_block(extra_arm={
        "arm_id": "aa", "replicate_of": "plan", "max_supplied_items": 8,
    }))
    twin = group.arm("aa")
    assert twin.knobs == ()
    assert twin.release_swap is None
    assert group.arm_ids == ("swap", "aa", "plan")


# ---------------------------------------------------------------------------
# 3. The receipt: rails.supply_variants / rails.native_episode_receipt
# ---------------------------------------------------------------------------


def test_the_receipt_records_which_release_each_arm_consumed():
    group = _parse_release_swap()
    records = [
        supply_variant_arm_record(
            arm=group.arm("swap"), arm_index=0, contact_id="c0",
            supplied_value_ids=("intent-boundaries::value:dim-light",),
        ),
        supply_variant_arm_record(
            arm=group.arm("plan"), arm_index=1, contact_id="c1",
            supplied_value_ids=(),
        ),
    ]
    receipt = supply_variant_receipt(group=group, phase_id="solver", records=records)
    assert receipt["schema"] == SUPPLY_VARIANT_RECEIPT_SCHEMA
    assert receipt["arms"][0]["release_swap"] == {
        "store_id": "intent-boundaries", "release": "alt.json",
    }
    assert receipt["arms"][1]["release_swap"] is None
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
    )


@pytest.mark.parametrize(
    "mutate,match",
    [
        pytest.param(
            lambda rows: rows[0].__setitem__("release_swap", {"store_id": "x"}),
            "invalid shape", id="malformed-release-swap",
        ),
        pytest.param(
            lambda rows: (
                rows[1].__setitem__("deliver", True),
                rows[1].__setitem__(
                    "release_swap", {"store_id": "intent-boundaries", "release": "alt.json"},
                ),
            ),
            "the delivering supply variant arm must declare no", id="delivering-arm-swap",
        ),
    ],
)
def test_the_receipt_validator_refuses_a_malformed_release_swap(mutate, match):
    group = _parse_release_swap()
    records = [
        supply_variant_arm_record(
            arm=group.arm("swap"), arm_index=0, contact_id="c0", supplied_value_ids=(),
        ),
        supply_variant_arm_record(
            arm=group.arm("plan"), arm_index=1, contact_id="c1", supplied_value_ids=(),
        ),
    ]
    receipt = supply_variant_receipt(group=group, phase_id="solver", records=records)
    mutate(receipt["arms"])
    with pytest.raises(ValueError, match=match):
        validate_supply_variant_receipt(
            receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
        )


# ---------------------------------------------------------------------------
# 4. The runtime: core.flight.runtime.FlightRuntime._supply_action_router
# ---------------------------------------------------------------------------


def _fake_runtime(config, *, data_root):
    return SimpleNamespace(
        _composed=SimpleNamespace(values=config),
        _data_root=data_root,
        _knowledge_store_binding=load_knowledge_store_binding(config, data_root=data_root),
        _knowledge_store_router_options={},
    )


def test_supply_action_router_release_swap_renders_the_alternates_values(tmp_path):
    store_id = "intent-boundaries"
    config, snapshots = _config(tmp_path, (store_id, "slot-contracts"))
    alt_snapshot, release_relpath = _add_alternate(tmp_path, config, store_id)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program = default_phase_program("native-answer-or-tool-v1")
    context = _context()

    primary_router = FlightRuntime._supply_action_router(runtime, program, "primary-arm", ())
    swapped_router = FlightRuntime._supply_action_router(
        runtime, program, "swap-arm", (),
        release_swap=SupplyVariantReleaseSwap(store_id=store_id, release_relpath=release_relpath),
    )

    # The swapped router's receipt for the NAMED store is the ALTERNATE's own
    # pins -- proof it actually loaded and rendered that store from the
    # alternate's bytes, not the primary's.
    assert (
        swapped_router.receipt["stores"][store_id]["store_snapshot_sha256"]
        == alt_snapshot.content_hash()
    )
    assert (
        primary_router.receipt["stores"][store_id]["store_snapshot_sha256"]
        == snapshots[store_id].content_hash()
    )
    assert (
        swapped_router.receipt["stores"][store_id]["store_snapshot_sha256"]
        != primary_router.receipt["stores"][store_id]["store_snapshot_sha256"]
    )
    # Every OTHER store is untouched: its own pins are byte-identical (the
    # composite_snapshot_sha256 in the SAME receipt legitimately differs,
    # since the swap changes what the WHOLE composite hashes to).
    untouched_keys = {
        "store_id", "store_role", "store_snapshot_sha256",
        "store_release_sha256", "store_source_sha256",
    }
    assert {
        key: swapped_router.receipt["stores"]["slot-contracts"][key]
        for key in untouched_keys
    } == {
        key: primary_router.receipt["stores"]["slot-contracts"][key]
        for key in untouched_keys
    }
    # The resolved supply itself is qualified against a DIFFERENT composite
    # snapshot (the swapped store shifts the whole composite), confirmed
    # straight off the returned PhaseSupply, not just the receipt.
    swapped_supply = swapped_router(store_id, "decision-2", context)
    primary_supply = primary_router(store_id, "decision-2", context)
    assert (
        swapped_supply.fusion_decision.snapshot_sha256
        != primary_supply.fusion_decision.snapshot_sha256
    )


def test_supply_action_router_refuses_a_release_absent_from_the_alternates(tmp_path):
    store_id = "intent-boundaries"
    config, _ = _config(tmp_path, (store_id,))
    _add_alternate(tmp_path, config, store_id)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program = default_phase_program("native-answer-or-tool-v1")
    with pytest.raises(FlightRuntimeError, match="does not declare as an alternate"):
        FlightRuntime._supply_action_router(
            runtime, program, "swap-arm", (),
            release_swap=SupplyVariantReleaseSwap(
                store_id=store_id, release_relpath="knowledge/does-not-exist.json",
            ),
        )


def test_supply_action_router_refuses_a_release_alternate_whose_bytes_changed(tmp_path):
    """The deferred half of ``test_loader_admits_an_alternate_whose_bytes_
    are_unverified_until_resolved`` above: once an arm actually selects the
    alternate, ``load_knowledge_store_binding`` re-verifies its bytes with
    the SAME rigor as the primary, and a mismatch is refused."""

    store_id = "intent-boundaries"
    config, _ = _config(tmp_path, (store_id,))
    _, release_relpath = _add_alternate(tmp_path, config, store_id)
    config["knowledge_stores"][store_id]["alternates"][0]["release"]["sha256"] = "f" * 64
    runtime = _fake_runtime(config, data_root=tmp_path)
    program = default_phase_program("native-answer-or-tool-v1")
    with pytest.raises(FlightRuntimeError, match="SHA-256 mismatch"):
        FlightRuntime._supply_action_router(
            runtime, program, "swap-arm", (),
            release_swap=SupplyVariantReleaseSwap(
                store_id=store_id, release_relpath=release_relpath,
            ),
        )


def test_supply_action_router_refuses_an_undeclared_release_swap_store(tmp_path):
    config, _ = _config(tmp_path, ("intent-boundaries",))
    runtime = _fake_runtime(config, data_root=tmp_path)
    program = default_phase_program("native-answer-or-tool-v1")
    with pytest.raises(FlightRuntimeError, match="names undeclared store"):
        FlightRuntime._supply_action_router(
            runtime, program, "swap-arm", (),
            release_swap=SupplyVariantReleaseSwap(
                store_id="not-a-declared-store", release_relpath="x.json",
            ),
        )


# ---------------------------------------------------------------------------
# 4b. The W4-SV render fix: core.flight.runtime.FlightRuntime.
#     _supply_variant_binding exposes the alternate snapshot and its own
#     flight-owned receipt, one entry per release-swap arm.
#
# ``_supply_action_router`` is stubbed here: the claim "an alternate release
# actually resolves to the right binding" is already proven, model-free, by
# section 4 above (``test_supply_action_router_release_swap_renders_the_
# alternates_values`` and its neighbours). What is NEW here is the WIRING
# ``_supply_variant_binding`` adds on top -- routing each arm's own
# ``release_swap`` into ``_supply_action_router``, and splitting the result
# into the per-arm router table, the ``release_swap_snapshots`` bolted onto
# the returned resolver and the flight-owned receipt -- which a stub isolates
# without needing a full ``context_supply``/``candidate_supply`` store (the
# real router attaches ``automatic_for_phase`` only when one of those is
# declared; ``test_knowledge_stores._config`` declares neither).
# ---------------------------------------------------------------------------


def test_supply_variant_binding_exposes_the_release_swap_snapshot_and_receipt():
    """The W4-SV blocker fix (coordinator amendment, 2026-09-28): the bug the
    W4-SV registration found is that ``rails.runner`` rendered EVERY arm's
    request from the flight's own composite snapshot, so a release-swap
    alternate that keeps the primary's value ids (a content-only revision)
    silently rendered the primary's content. The fix is
    ``FlightRuntime._supply_variant_binding`` exposing, per release-swap arm,
    the alternate composite snapshot ``rails.runner`` must render from, plus a
    flight-owned receipt of the alternate's own resolved hashes -- present for
    that one arm alone."""

    store_id = "intent-boundaries"
    release_relpath = "knowledge/intent-boundaries/alternate-release.json"
    group = parse_supply_variants(
        {
            "arms": [
                {
                    "arm_id": "swap", "max_supplied_items": 8,
                    "release_swap": {"store_id": store_id, "release": release_relpath},
                },
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 8},
            ],
            "fit_estimate": dict(FIT),
        },
        phase_id="solver", first_phase_id="perception",
        declared_stores=(store_id,),
        declared_alternate_relpaths={store_id: (release_relpath,)},
    )
    native_config = SimpleNamespace(supply_variant_group=group)

    alt_store_receipt = {
        "store_id": store_id, "store_role": store_id,
        "store_snapshot_sha256": "b" * 64, "store_release_sha256": "c" * 64,
        "store_source_sha256": "d" * 64, "composite_snapshot_sha256": "e" * 64,
    }
    alt_snapshot = SimpleNamespace(content_hash=lambda: "alt-composite-hash")
    base_snapshot = SimpleNamespace(content_hash=lambda: "base-composite-hash")
    seen_release_swaps: dict[str, object] = {}

    def fake_supply_action_router(program, action_id, knobs, *, release_swap=None):
        seen_release_swaps[action_id] = release_swap
        if release_swap is not None:
            return SimpleNamespace(
                automatic_for_phase=f"route-{action_id}",
                knowledge_store_binding=SimpleNamespace(
                    composite_snapshot=alt_snapshot,
                    store_receipt=lambda sid: (
                        alt_store_receipt if sid == release_swap.store_id else None
                    ),
                ),
            )
        return SimpleNamespace(
            automatic_for_phase=f"route-{action_id}",
            knowledge_store_binding=SimpleNamespace(composite_snapshot=base_snapshot),
        )

    runtime = SimpleNamespace(
        _knowledge_store_binding=SimpleNamespace(composite_snapshot=base_snapshot),
        _knowledge_store_router_options={},
        _phase_supply_receipt=None,
        _supply_action_router=fake_supply_action_router,
    )

    resolve = FlightRuntime._supply_variant_binding(runtime, native_config, program=object())

    # ``_supply_action_router`` is called once per arm, with exactly that
    # arm's OWN declared ``release_swap`` (``None`` for the delivering arm).
    assert seen_release_swaps["swap"] == SupplyVariantReleaseSwap(
        store_id=store_id, release_relpath=release_relpath,
    )
    assert seen_release_swaps["plan"] is None

    # ONE alternate composite snapshot, keyed by the release-swap arm's id
    # alone -- the delivering arm never appears here.
    assert set(resolve.release_swap_snapshots) == {"swap"}
    assert resolve.release_swap_snapshots["swap"] is alt_snapshot

    # The flight-owned receipt records the alternate's resolved hashes, on
    # the release-swap arm alone -- never on the delivering arm.
    receipt = runtime._phase_supply_receipt
    assert set(receipt["supply_variant_release_swaps"]) == {"swap"}
    assert receipt["supply_variant_release_swaps"]["swap"] == alt_store_receipt


def test_supply_variant_binding_without_a_release_swap_arm_carries_no_extras():
    """Byte-identical to before this fix when no arm declares a release_swap:
    an empty ``release_swap_snapshots`` and no flight-owned receipt entry."""

    group = parse_supply_variants(
        {
            "arms": [
                {"arm_id": "narrow", "max_supplied_items": 4,
                 "overrides": {f"{EX}.k": 10}},
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 4},
            ],
            "fit_estimate": dict(FIT),
        },
        phase_id="solver", first_phase_id="perception",
        declared_stores=("train-exemplars",),
    )
    native_config = SimpleNamespace(supply_variant_group=group)

    def fake_supply_action_router(program, action_id, knobs, *, release_swap=None):
        assert release_swap is None
        return SimpleNamespace(automatic_for_phase=f"route-{action_id}")

    runtime = SimpleNamespace(
        _knowledge_store_binding=SimpleNamespace(),
        _knowledge_store_router_options={},
        _phase_supply_receipt=None,
        _supply_action_router=fake_supply_action_router,
    )

    resolve = FlightRuntime._supply_variant_binding(runtime, native_config, program=object())

    assert dict(resolve.release_swap_snapshots) == {}
    assert runtime._phase_supply_receipt is None


# ---------------------------------------------------------------------------
# 5. Identity: core.flight.runtime._knowledge_store_alternate_identity
# ---------------------------------------------------------------------------


def test_knowledge_store_alternate_identity_changes_with_an_alternates_pins(tmp_path):
    config, _ = _config(tmp_path, ("intent-boundaries",))
    assert _knowledge_store_alternate_identity(config["knowledge_stores"]) == {}
    assert digest(_knowledge_store_alternate_identity(config["knowledge_stores"])) == digest({})

    _add_alternate(tmp_path, config, "intent-boundaries")
    with_alternate = _knowledge_store_alternate_identity(config["knowledge_stores"])
    assert with_alternate != {}

    changed = json.loads(json.dumps(config["knowledge_stores"]))
    changed["intent-boundaries"]["alternates"][0]["release"]["sha256"] = "f" * 64
    with_changed_alternate = _knowledge_store_alternate_identity(changed)

    assert with_changed_alternate != with_alternate
    assert digest(with_changed_alternate) != digest(with_alternate)


def test_knowledge_store_alternate_identity_ignores_malformed_input():
    assert _knowledge_store_alternate_identity(None) == {}
    assert _knowledge_store_alternate_identity("not a mapping") == {}
    assert _knowledge_store_alternate_identity({"s": "not a mapping"}) == {}
    assert _knowledge_store_alternate_identity({"s": {"alternates": "not a list"}}) == {}
