"""Loop engineering item E-T6 (owner decision 263-A / 265, 2026-10-11): multi-store
``release_swaps`` in the supply-variant arms.

An arm may repoint SEVERAL stores at once (one swap per distinct store) through
``release_swaps``; the single ``release_swap`` stays the one-store form. This file
proves, model-free: the parse and its fail-closed refusals, the receipt v5 layout
and its validator (I7v, per store), that every group with at most one swap per arm
still seals the v3 receipt byte for byte, the consumption-module supply column and
its compile, the flight's one-off router over several swapped stores, the per-arm
sealed record, and the readers' per-store verification against a declaration.
"""

from __future__ import annotations

import copy
import json

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    SUPPLY_VARIANT_RECEIPT_SCHEMA,
    SUPPLY_VARIANT_RECEIPT_SCHEMA_V5,
    supply_variant_arm_release_swaps,
    validate_supply_variant_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    MULTI_STORE_RELEASE_SWAPS_SUPPORTED,
    SupplyVariantArm,
    SupplyVariantError,
    SupplyVariantReleaseSwap,
    parse_supply_variant_release_swaps,
    parse_supply_variants,
    supply_variant_arm_record,
    supply_variant_receipt,
)

from test_consumption_module_supply_columns import (
    ALT,
    ALT_RELEASE,
    EX_K,
    FIT,
    _compose,
    _supply_block,
)
from test_knowledge_store_release_alternates import _add_alternate, _fake_runtime
from test_knowledge_stores import _config
from test_phase_tools import _context

EX_STORE = "train-exemplars"
SC_STORE = "slot-contracts"
EX_REL = "ex/alt.json"
SC_REL = "sc/alt.json"
STORES = (EX_STORE, SC_STORE, "intent-boundaries")
ALTERNATES = {EX_STORE: (EX_REL,), SC_STORE: (SC_REL,)}
EX_SWAP = {"store_id": EX_STORE, "release": EX_REL}
SC_SWAP = {"store_id": SC_STORE, "release": SC_REL}


def _block(*, swaps=None, swap=None, extra_arms=()):
    arm = {"arm_id": "both", "max_supplied_items": 40}
    if swaps is not None:
        arm["release_swaps"] = swaps
    if swap is not None:
        arm["release_swap"] = swap
    arms = [arm, *extra_arms, {"arm_id": "lock", "deliver": True, "max_supplied_items": 40}]
    return {"arms": arms, "fit_estimate": dict(FIT), "arm_visits": "first"}


def _parse(block, **kwargs):
    options = {
        "phase_id": "solver", "first_phase_id": "perception",
        "declared_stores": STORES, "declared_alternate_relpaths": ALTERNATES,
    }
    options.update(kwargs)
    return parse_supply_variants(block, **options)


def _records(group, *, v5=None):
    v5 = group.uses_release_swaps if v5 is None else v5
    return [
        supply_variant_arm_record(
            arm=arm, arm_index=index, contact_id=f"c{index}",
            supplied_value_ids=("v0",) if (arm.deliver or arm.replicate_of) else (f"v{index}",),
            release_swaps_group=v5,
        )
        for index, arm in enumerate(group.arms)
    ]


def _v5_receipt(group=None):
    group = group or _parse(_block(swaps=[SC_SWAP, EX_SWAP]))
    return group, supply_variant_receipt(group=group, phase_id="solver", records=_records(group))


def _validate(receipt, group):
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id=group.delivered_arm.arm_id,
        phase_id="solver",
    )


# ---------------------------------------------------------------------------
# 1. The parse
# ---------------------------------------------------------------------------


def test_a_two_store_arm_parses_ordered_by_store_and_the_group_seals_v5():
    group = _parse(_block(swaps=[SC_SWAP, EX_SWAP]))
    arm = group.arm("both")
    assert arm.release_swap is None
    assert [swap.store_id for swap in arm.release_swaps] == [SC_STORE, EX_STORE]
    assert arm.all_release_swaps == arm.release_swaps
    assert arm.as_json()["release_swaps"] == [SC_SWAP, EX_SWAP]
    assert group.uses_release_swaps and group.receipt_schema == SUPPLY_VARIANT_RECEIPT_SCHEMA_V5
    assert group.delivered_arm.all_release_swaps == ()


def test_the_plural_spelling_of_one_store_is_the_singular_arm_and_keeps_v3():
    plural = _parse(_block(swaps=[EX_SWAP]))
    singular = _parse(_block(swap=EX_SWAP))
    assert plural.arms == singular.arms
    arm = plural.arm("both")
    assert arm.release_swap == SupplyVariantReleaseSwap(EX_STORE, EX_REL) and arm.release_swaps == ()
    assert arm.as_json() == singular.arm("both").as_json() and "release_swaps" not in arm.as_json()
    assert not plural.uses_release_swaps and plural.receipt_schema == SUPPLY_VARIANT_RECEIPT_SCHEMA


def test_a_group_with_one_swap_per_arm_seals_the_v3_receipt_byte_for_byte():
    group = _parse(_block(swap=EX_SWAP, extra_arms=[
        {"arm_id": "knob", "max_supplied_items": 40,
         "overrides": {f"knowledge_stores.{EX_STORE}.phase_supply.solver.k": 10}},
    ]))
    receipt = supply_variant_receipt(group=group, phase_id="solver", records=_records(group))
    assert receipt["schema"] == "saea-supply-variant-arms-v3"
    # the exact v3 row: a ``release_swap`` key, no ``release_swaps`` key
    assert receipt["arms"][0] == {
        "arm_index": 0, "arm_id": "both", "deliver": False, "replicate_of": None,
        "release_swap": EX_SWAP, "contact_id": "c0", "resolved_knobs": [],
        "supplied_value_ids": ["v0"], "supplied_item_count": 1, "max_supplied_items": 40,
    }
    assert all("release_swaps" not in row for row in receipt["arms"])
    assert receipt["arms"][2]["release_swap"] is None
    _validate(receipt, group)
    json.dumps(receipt, sort_keys=True)


@pytest.mark.parametrize(
    "block,message",
    [
        pytest.param(
            _block(swaps=[EX_SWAP, EX_SWAP]),
            "more than once", id="repeated-store"),
        pytest.param(
            _block(swaps=[EX_SWAP, {"store_id": "no-such-store", "release": EX_REL}]),
            "does not declare", id="unknown-store"),
        pytest.param(
            _block(swaps=[EX_SWAP, {"store_id": SC_STORE, "release": "sc/missing.json"}]),
            "absent from its declared alternates", id="release-absent-from-alternates"),
        pytest.param(
            _block(swaps=[EX_SWAP, {"store_id": "intent-boundaries", "release": "ib/alt.json"}]),
            "absent from its declared alternates", id="store-with-no-declared-alternates"),
        pytest.param(_block(swaps=[]), "non-empty list", id="empty-list"),
        pytest.param(_block(swaps=EX_SWAP), "non-empty list", id="not-a-list"),
        pytest.param(_block(swaps="ex"), "non-empty list", id="string"),
        pytest.param(
            _block(swaps=[EX_SWAP, {"store_id": SC_STORE}]),
            "exactly store_id and release", id="entry-shape"),
        pytest.param(
            _block(swaps=[EX_SWAP, dict(SC_SWAP, extra=1)]),
            "exactly store_id and release", id="entry-extra-key"),
        pytest.param(
            _block(swaps=[EX_SWAP, SC_SWAP], swap=EX_SWAP),
            "declares both release_swap and release_swaps", id="both-spellings"),
    ],
)
def test_the_parse_is_fail_closed(block, message):
    with pytest.raises(SupplyVariantError, match=message):
        _parse(block)


def test_the_delivering_arm_and_the_twin_carry_no_swaps():
    block = _block(swaps=[EX_SWAP, SC_SWAP])
    block["arms"][-1]["release_swaps"] = [EX_SWAP, SC_SWAP]
    with pytest.raises(SupplyVariantError, match="delivering arm 'lock' must declare no"):
        _parse(block)
    twin = {"arm_id": "aa", "replicate_of": "lock", "max_supplied_items": 40,
            "release_swaps": [EX_SWAP, SC_SWAP]}
    with pytest.raises(SupplyVariantError, match="names replicate_of and must declare no"):
        _parse(_block(swaps=[EX_SWAP, SC_SWAP], extra_arms=[twin]))


def test_two_arms_with_the_same_swap_set_are_duplicates_but_a_subset_is_not():
    other = {"arm_id": "again", "max_supplied_items": 40, "release_swaps": [SC_SWAP, EX_SWAP]}
    with pytest.raises(SupplyVariantError, match="declare the same overrides"):
        _parse(_block(swaps=[EX_SWAP, SC_SWAP], extra_arms=[other]))
    subset = {"arm_id": "one", "max_supplied_items": 40, "release_swap": EX_SWAP}
    group = _parse(_block(swaps=[EX_SWAP, SC_SWAP], extra_arms=[subset]))
    assert group.arm_ids == ("both", "one", "lock") and group.uses_release_swaps


def test_the_arm_dataclass_normalises_and_refuses_inconsistent_swaps():
    ex, sc = SupplyVariantReleaseSwap(EX_STORE, EX_REL), SupplyVariantReleaseSwap(SC_STORE, SC_REL)
    common = dict(arm_id="a", deliver=False, knobs=(), max_supplied_items=4)
    assert SupplyVariantArm(**common, release_swaps=(ex, sc)).release_swaps == (sc, ex)
    one = SupplyVariantArm(**common, release_swaps=(ex,))
    assert one.release_swap == ex and one.release_swaps == ()
    with pytest.raises(SupplyVariantError, match="declares both"):
        SupplyVariantArm(**common, release_swap=ex, release_swaps=(sc,))
    with pytest.raises(SupplyVariantError, match="names a store twice"):
        SupplyVariantArm(**common, release_swaps=(ex, SupplyVariantReleaseSwap(EX_STORE, "x")))


def test_the_list_parser_is_exported_and_orders_by_store():
    swaps = parse_supply_variant_release_swaps(
        [EX_SWAP, SC_SWAP], declared_stores=STORES, declared_alternate_relpaths=ALTERNATES)
    assert [swap.store_id for swap in swaps] == [SC_STORE, EX_STORE]


# ---------------------------------------------------------------------------
# 2. Receipt v5 and I7v per store
# ---------------------------------------------------------------------------


def test_the_v5_receipt_layout():
    group, receipt = _v5_receipt()
    assert receipt["schema"] == "saea-supply-variant-arms-v5" == SUPPLY_VARIANT_RECEIPT_SCHEMA_V5
    assert set(receipt) == {
        "schema", "phase_id", "arm_count", "delivered_arm_id", "arm_visits", "visit_index",
        "fit_estimate", "arms",
    }
    both, lock = receipt["arms"]
    assert both["release_swaps"] == [SC_SWAP, EX_SWAP] and "release_swap" not in both
    assert lock["release_swaps"] == [] and "release_swap" not in lock
    assert set(both) == {
        "arm_index", "arm_id", "deliver", "replicate_of", "release_swaps", "contact_id",
        "resolved_knobs", "supplied_value_ids", "supplied_item_count", "max_supplied_items",
    }
    _validate(receipt, group)
    assert supply_variant_arm_release_swaps(both) == [SC_SWAP, EX_SWAP]
    assert supply_variant_arm_release_swaps(lock) == []


def test_the_reader_normaliser_agrees_across_schemas():
    v3_group = _parse(_block(swap=EX_SWAP))
    v3 = supply_variant_receipt(group=v3_group, phase_id="solver", records=_records(v3_group))
    assert supply_variant_arm_release_swaps(v3["arms"][0]) == [EX_SWAP]
    assert supply_variant_arm_release_swaps(v3["arms"][1]) == []
    assert supply_variant_arm_release_swaps({"arm_id": "v1-row"}) == []


def _mutations():
    def swaps(rows, value):
        rows[0]["release_swaps"] = value
    return [
        pytest.param(lambda rows: swaps(rows, [EX_SWAP, EX_SWAP]), "names a store twice", id="repeated-store"),
        pytest.param(lambda rows: swaps(rows, [EX_SWAP, SC_SWAP]), "ordered by store_id", id="unordered"),
        pytest.param(lambda rows: swaps(rows, [dict(SC_SWAP, extra=1)]), "invalid shape", id="entry-extra-key"),
        pytest.param(lambda rows: swaps(rows, [{"store_id": SC_STORE}]), "invalid shape", id="entry-missing-key"),
        pytest.param(lambda rows: swaps(rows, [dict(SC_SWAP, release="")]), "invalid shape", id="empty-release"),
        pytest.param(lambda rows: swaps(rows, "sc"), "invalid shape|must be a", id="not-a-list"),
        pytest.param(lambda rows: rows[0].__setitem__("release_swap", None), "invalid shape", id="v3-key-in-v5-row"),
        pytest.param(lambda rows: rows[0].pop("release_swaps"), "invalid shape", id="missing-key"),
        pytest.param(lambda rows: swaps(rows, []), "at least one knob", id="arm-swapping-nothing"),
        pytest.param(
            lambda rows: rows[1].__setitem__("release_swaps", [SC_SWAP]),
            "delivering supply variant arm must declare no release_swaps", id="delivering-arm-swaps"),
    ]


@pytest.mark.parametrize("mutate,message", _mutations())
def test_the_v5_validator_refuses_every_malformed_store_entry(mutate, message):
    group, receipt = _v5_receipt()
    receipt = copy.deepcopy(receipt)
    mutate(receipt["arms"])
    with pytest.raises(ValueError, match=message):
        _validate(receipt, group)


def test_the_v5_validator_refuses_a_twin_with_swaps():
    twin = {"arm_id": "aa", "replicate_of": "lock", "max_supplied_items": 40}
    group = _parse(_block(swaps=[EX_SWAP, SC_SWAP], extra_arms=[twin]))
    receipt = supply_variant_receipt(group=group, phase_id="solver", records=_records(group))
    _validate(receipt, group)
    receipt["arms"][1]["release_swaps"] = [SC_SWAP]
    with pytest.raises(ValueError, match="twin arm .* must declare no release_swaps"):
        _validate(receipt, group)


def test_an_unregistered_schema_is_still_refused_and_v3_rows_cannot_carry_release_swaps():
    group, receipt = _v5_receipt()
    bad = copy.deepcopy(receipt)
    bad["schema"] = "saea-supply-variant-arms-v9"
    with pytest.raises(ValueError, match="unregistered schema"):
        _validate(bad, group)
    v3 = copy.deepcopy(receipt)
    v3["schema"] = SUPPLY_VARIANT_RECEIPT_SCHEMA
    with pytest.raises(ValueError, match="invalid shape"):
        _validate(v3, group)


def test_a_delivering_arm_of_a_v5_receipt_must_open_the_row_state():
    group, receipt = _v5_receipt()
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id="lock", phase_id="solver",
        retrieved_value_ids=["v0", "z"],
    )
    with pytest.raises(ValueError, match="ordered prefix"):
        validate_supply_variant_receipt(
            receipt, arm_ids=group.arm_ids, delivered_arm_id="lock", phase_id="solver",
            retrieved_value_ids=["z"],
        )


# ---------------------------------------------------------------------------
# 3. The consumption module's supply column
# ---------------------------------------------------------------------------

SC_ALT_RELEASE = "knowledge/slurp/alt-sc/release.json"
SC_ALT = [{
    "release": {"relpath": SC_ALT_RELEASE, "sha256": "c" * 64},
    "snapshot": {"relpath": "knowledge/slurp/alt-sc/snapshot.json", "sha256": "d" * 64},
}]
COL_EX = {"store_id": EX_STORE, "release": ALT_RELEASE}
COL_SC = {"store_id": SC_STORE, "release": SC_ALT_RELEASE}


def _two_store_block(release_swaps=None, **column_extra):
    block = _supply_block()
    block["supply_frame"]["alternates"][SC_STORE] = copy.deepcopy(SC_ALT)
    block["columns"][1] = {
        "column_id": "ace", "kind": "supply", "node": "solver", "max_supplied_items": 55,
        "release_swaps": copy.deepcopy([COL_SC, COL_EX] if release_swaps is None else release_swaps),
        **column_extra,
    }
    return block


def test_a_two_store_column_compiles_to_one_arm_with_both_swaps_and_passes_all_alternates():
    composed = cm.compile_module(_two_store_block(), carrier_module_hooks())
    values = composed.values()
    arms = values["native_episode"]["roles"]["solver"]["supply_variants"]["arms"]
    ace = next(arm for arm in arms if arm["arm_id"] == "ace")
    assert ace["release_swaps"] == [COL_SC, COL_EX] and "release_swap" not in ace
    for arm in arms:
        if arm["arm_id"] in ("aa", "lock"):
            assert "release_swaps" not in arm and "release_swap" not in arm
    stores = values["knowledge_stores"]
    assert stores[EX_STORE]["alternates"] == ALT[EX_STORE]
    assert stores[SC_STORE]["alternates"] == SC_ALT
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c5", 5)


def test_a_two_store_column_loads_through_the_runtime_loader_and_verifies():
    block = _two_store_block()
    composed, values = _compose(block)
    program = default_phase_program(values["policy"])
    parsed = load_native_episode_config(values, program)
    group = parsed.supply_variant_group
    assert group.uses_release_swaps and group.receipt_schema == SUPPLY_VARIANT_RECEIPT_SCHEMA_V5
    assert [s.store_id for s in group.arm("ace").release_swaps] == [SC_STORE, EX_STORE]
    assert group.delivered_arm.all_release_swaps == ()
    cm.verify_declared_module(block, values)
    edited = copy.deepcopy(values)
    arm = next(a for a in edited["native_episode"]["roles"]["solver"]["supply_variants"]["arms"]
               if a["arm_id"] == "ace")
    arm["release_swaps"].pop()
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, edited)


def test_the_one_store_block_is_byte_identical_whichever_way_it_is_spelled():
    singular = _supply_block()
    plural = _supply_block()
    plural["columns"][1].pop("release_swap")
    plural["columns"][1]["release_swaps"] = [{"store_id": EX_STORE, "release": ALT_RELEASE}]
    a = cm.compile_module(singular, carrier_module_hooks()).values()
    b = cm.compile_module(plural, carrier_module_hooks()).values()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    ace = next(x for x in a["native_episode"]["roles"]["solver"]["supply_variants"]["arms"]
               if x["arm_id"] == "ace")
    assert ace == {"arm_id": "ace", "max_supplied_items": 55, "release_swap": COL_EX}
    assert cm.parse_consumption_module_block(singular).supply_columns[1].supply == \
        cm.parse_consumption_module_block(plural).supply_columns[1].supply


def test_the_column_identity_ignores_the_order_of_the_stores():
    a = cm.parse_consumption_module_block(_two_store_block([COL_SC, COL_EX]))
    b = cm.parse_consumption_module_block(_two_store_block([COL_EX, COL_SC]))
    assert a.supply_columns[1].supply == b.supply_columns[1].supply


@pytest.mark.parametrize(
    "mutate,message",
    [
        pytest.param(lambda b: b["columns"][1].update(release_swaps=[]), "non-empty list", id="empty"),
        pytest.param(lambda b: b["columns"][1].update(release_swaps=[dict(COL_EX), dict(COL_EX)]),
                     "names a store twice", id="repeated-store"),
        pytest.param(lambda b: b["columns"][1].update(release_swaps=[COL_EX, {"store_id": SC_STORE}]),
                     "exactly {store_id, release}", id="shape"),
        pytest.param(lambda b: b["columns"][1].update(release_swap=COL_EX),
                     "both release_swap and release_swaps", id="both"),
    ],
)
def test_the_column_parse_refuses_a_malformed_plural_swap(mutate, message):
    block = _two_store_block()
    mutate(block)
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.parse_consumption_module_block(block)


@pytest.mark.parametrize(
    "mutate,message",
    [
        pytest.param(lambda b: b["columns"][1]["release_swaps"][0].update(release="knowledge/x.json"),
                     "absent from its declared alternates", id="release-absent"),
        pytest.param(lambda b: b["supply_frame"]["alternates"].pop(SC_STORE),
                     "absent from its declared alternates", id="store-without-alternates"),
        pytest.param(lambda b: b["columns"][1]["release_swaps"][0].update(store_id="no-such-store"),
                     "does not declare", id="unknown-store"),
    ],
)
def test_the_compiler_applies_the_rails_refusals_to_every_swapped_store(mutate, message):
    block = _two_store_block()
    mutate(block)
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.compile_module(block, carrier_module_hooks())


def test_the_v5_node_receipt_schema_is_a_registered_node_receipt():
    receipt = cm.module_header_receipt(
        cm.compile_module(_two_store_block(), carrier_module_hooks()),
        node_receipts=[{"schema": "saea-supply-variant-arms-v5", "pointer": "supply_variants"}],
    )
    cm.validate_module_header_receipt(receipt)


# ---------------------------------------------------------------------------
# 4. The flight: one-off router over several swapped stores, and the binding
# ---------------------------------------------------------------------------


def _two_alternate_config(tmp_path):
    config, snapshots = _config(tmp_path, ("intent-boundaries", SC_STORE))
    alt_a, rel_a = _add_alternate(tmp_path, config, "intent-boundaries", marker="ALT-A")
    alt_b, rel_b = _add_alternate(tmp_path, config, SC_STORE, marker="ALT-B")
    return config, snapshots, {"intent-boundaries": (alt_a, rel_a), SC_STORE: (alt_b, rel_b)}


def test_the_router_loads_every_swapped_store_from_its_alternate(tmp_path):
    config, snapshots, alts = _two_alternate_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program = default_phase_program("native-answer-or-tool-v1")
    base = FlightRuntime._supply_action_router(runtime, program, "base", ())
    swaps = tuple(
        SupplyVariantReleaseSwap(store_id=store, release_relpath=alts[store][1])
        for store in ("intent-boundaries", SC_STORE)
    )
    both = FlightRuntime._supply_action_router(runtime, program, "both", (), release_swap=swaps)
    for store, (alt_snapshot, _) in alts.items():
        assert both.receipt["stores"][store]["store_snapshot_sha256"] == alt_snapshot.content_hash()
        assert both.receipt["stores"][store]["store_snapshot_sha256"] != \
            base.receipt["stores"][store]["store_snapshot_sha256"]
    assert both.knowledge_store_binding.composite_snapshot.content_hash() != \
        base.knowledge_store_binding.composite_snapshot.content_hash()
    # a one-store arm leaves the other store on the base pins
    only_first = FlightRuntime._supply_action_router(
        runtime, program, "one", (), release_swap=swaps[0])
    assert only_first.receipt["stores"][SC_STORE]["store_snapshot_sha256"] == \
        base.receipt["stores"][SC_STORE]["store_snapshot_sha256"]
    # a one-element list is the one-store form
    as_list = FlightRuntime._supply_action_router(
        runtime, program, "one", (), release_swap=(swaps[0],))
    assert as_list.receipt == only_first.receipt


def test_the_router_refuses_a_repeated_store_an_undeclared_release_and_an_undeclared_store(tmp_path):
    config, _, alts = _two_alternate_config(tmp_path)
    runtime = _fake_runtime(config, data_root=tmp_path)
    program = default_phase_program("native-answer-or-tool-v1")
    rel = alts["intent-boundaries"][1]
    twice = (SupplyVariantReleaseSwap("intent-boundaries", rel),
             SupplyVariantReleaseSwap("intent-boundaries", rel))
    with pytest.raises(FlightRuntimeError, match="names a store twice"):
        FlightRuntime._supply_action_router(runtime, program, "x", (), release_swap=twice)
    missing = (SupplyVariantReleaseSwap("intent-boundaries", rel),
               SupplyVariantReleaseSwap(SC_STORE, "knowledge/none.json"))
    with pytest.raises(FlightRuntimeError, match="does not declare as an alternate"):
        FlightRuntime._supply_action_router(runtime, program, "x", (), release_swap=missing)
    undeclared = (SupplyVariantReleaseSwap("intent-boundaries", rel),
                  SupplyVariantReleaseSwap("not-a-store", "x.json"))
    with pytest.raises(FlightRuntimeError, match="names undeclared store"):
        FlightRuntime._supply_action_router(runtime, program, "x", (), release_swap=undeclared)


def test_the_binding_seals_one_store_receipt_per_swapped_store_for_a_v5_group():
    from types import SimpleNamespace

    group = _parse(_block(swaps=[SC_SWAP, EX_SWAP], extra_arms=[
        {"arm_id": "one", "max_supplied_items": 40, "release_swap": EX_SWAP}]))
    alt_snapshot = SimpleNamespace(content_hash=lambda: "alt")
    seen = {}

    def receipt_of(store):
        return {"store_id": store, "store_snapshot_sha256": f"snap-{store}"}

    def fake_router(program, action_id, knobs, *, release_swap=None):
        seen[action_id] = release_swap
        binding = SimpleNamespace(composite_snapshot=alt_snapshot, store_receipt=receipt_of)
        return SimpleNamespace(automatic_for_phase=f"route-{action_id}",
                               knowledge_store_binding=binding)

    runtime = SimpleNamespace(
        _knowledge_store_binding=SimpleNamespace(), _knowledge_store_router_options={},
        _phase_supply_receipt=None, _supply_action_router=fake_router,
    )
    resolve = FlightRuntime._supply_variant_binding(
        runtime, SimpleNamespace(supply_variant_group=group), program=object())
    assert seen["lock"] is None
    assert seen["one"] == SupplyVariantReleaseSwap(EX_STORE, EX_REL)
    assert tuple(s.store_id for s in seen["both"]) == (SC_STORE, EX_STORE)
    assert set(resolve.release_swap_snapshots) == {"both", "one"}
    sealed = runtime._phase_supply_receipt["supply_variant_release_swaps"]
    assert sealed["both"] == {SC_STORE: receipt_of(SC_STORE), EX_STORE: receipt_of(EX_STORE)}
    assert sealed["one"] == {EX_STORE: receipt_of(EX_STORE)}
    assert "lock" not in sealed


# ---------------------------------------------------------------------------
# 5. The readers: every sealed swap against its declaration
# ---------------------------------------------------------------------------


def test_the_sealed_swap_list_equals_the_declaration_for_n_stores():
    group, receipt = _v5_receipt()
    for arm, row in zip(group.arms, receipt["arms"]):
        assert supply_variant_arm_release_swaps(row) == [s.as_json() for s in arm.all_release_swaps]
    tampered = copy.deepcopy(receipt["arms"][0])
    tampered["release_swaps"][0]["release"] = "sc/other.json"
    assert supply_variant_arm_release_swaps(tampered) != \
        [s.as_json() for s in group.arm("both").all_release_swaps]


def test_the_rollout_scorer_and_the_column_reader_know_the_v5_receipt():
    import importlib.util
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "scripts" / "analysis"
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location(
            "et6_column_read", root / "slurp_nx_solver_column_read.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["et6_column_read"] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(root))
    assert module.KIND_BY_SCHEMA[SUPPLY_VARIANT_RECEIPT_SCHEMA_V5] == "supply"
    assert module.KIND_BY_SCHEMA[SUPPLY_VARIANT_RECEIPT_SCHEMA] == "supply"
    source = (root / "stage3_rollout_score.py").read_text(encoding="utf-8")
    assert "supply_variant_arm_release_swaps(sealed) != declared_swaps" in source


# ---------------------------------------------------------------------------
# 6. The archive view: the typed validator admits a two-store candidate
# ---------------------------------------------------------------------------


def test_the_multi_store_flag_is_set_for_the_archive_view_writer():
    assert MULTI_STORE_RELEASE_SWAPS_SUPPORTED is True
