"""NX-T R4 (2026-10-18, owner rulings 329 A / 332 A): the node-DECODING arm kind -- the rail, the receipt, the loader, the
module compiler and the request seam.

``rails.supply_variants.parse_decoding_variants`` is the sampling-parameter sibling of ``parse_template_variants``: each
candidate arm overrides exactly the SAMPLING parameters of its own Solver contact (temperature / top_p / top_k /
presence_penalty, a closed validated set with bounds); the delivering arm is LAST and carries no override; the twin carries
none; every other reach (the template, the evidence, the response format, the thinking budget and cap, the request seed, tool
authority) is refused BY NAME before any contact. Model-free: no model, server, tokenizer, GPU or network contact.
"""

from __future__ import annotations

import copy
import json
import math

import pytest

from speech_aware_evidence_acquisition.rails import native_episode_receipt as ner
from speech_aware_evidence_acquisition.rails import supply_variants as sv
from speech_aware_evidence_acquisition.rails.native_episode_receipt import validate_supply_variant_receipt
from speech_aware_evidence_acquisition.rails.supply_variants import (
    DECODING_VARIANT_KNOBS,
    SUPPLY_VARIANT_RECEIPT_SCHEMA_V6,
    SupplyVariantError,
    parse_decoding_variants,
    supply_variant_arm_record,
    supply_variant_receipt,
)

FIT = {"slot_tokens": 24576, "completion_ceiling": 4096, "base_prompt_tokens": 2000, "tokens_per_supplied_item": 235}
D1 = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
D2 = {**D1, "presence_penalty": 1.5}
D3 = {"temperature": 0.3, "top_p": 0.95, "top_k": 20}
D4 = {"temperature": 0, "presence_penalty": 1.5}
LOCKED_DECODING = {"temperature": 0, "seed": 20260913, "max_tokens": 4096, "thinking_budget_tokens": 3072}


def _block(**overrides):
    block = {
        "node": "solver",
        "arms": [
            {"arm_id": "d1", "decoding": dict(D1)},
            {"arm_id": "d2", "decoding": dict(D2)},
            {"arm_id": "d3", "decoding": dict(D3)},
            {"arm_id": "d4", "decoding": dict(D4)},
            {"arm_id": "aa", "replicate_of": "lock"},
            {"arm_id": "lock", "deliver": True},
        ],
        "max_supplied_items": 55,
        "template_tokens": 323,
        "fit_estimate": dict(FIT),
    }
    block.update(overrides)
    return block


def _parse(block=None, **kwargs):
    options = {"role_kind": "solver", "phase_id": "solver", "locked_decoding": LOCKED_DECODING}
    options.update(kwargs)
    return parse_decoding_variants(block if block is not None else _block(), **options)


def _mutated(mutate):
    block = _block()
    mutate(block)
    return block


# ---- the parse ----------------------------------------------------------------------------------------------------------------


def test_a_well_formed_group_parses_to_its_declared_order_and_kind():
    group = _parse()
    assert group.kind == "decoding" and group.is_decoding and not group.is_template and group.unvaried_evidence
    assert group.arm_ids == ("d1", "d2", "d3", "d4", "aa", "lock")
    assert group.arm_visits == "first" and group.delivered_arm.arm_id == "lock"
    assert group.receipt_schema == SUPPLY_VARIANT_RECEIPT_SCHEMA_V6 == ner.SUPPLY_VARIANT_RECEIPT_SCHEMA_V6 == "saea-supply-variant-arms-v6"
    assert group.arm("d1").decoding == D1 and group.arm("d2").decoding == D2
    assert group.arm("d4").decoding == {"temperature": 0, "presence_penalty": 1.5}
    for arm_id in ("aa", "lock"):
        assert group.arm(arm_id).decoding is None and group.arm(arm_id).decoding_override is None
    assert group.arm("aa").replicate_of == "lock"
    assert all(arm.knobs == () and arm.release_swap is None and arm.instruction_template is None for arm in group.arms)
    # every arm shares the locked template's token count and the one supply bound (the fit estimate)
    assert {arm.template_tokens for arm in group.arms} == {323} and {arm.max_supplied_items for arm in group.arms} == {55}
    document = group.as_json()
    assert document["kind"] == "decoding" and document["arms"][0]["decoding"] == D1
    assert "decoding" not in document["arms"][-1]


def test_the_closed_set_is_the_four_registered_parameters_and_one_table_serves_the_parser_and_the_receipt():
    assert set(DECODING_VARIANT_KNOBS) == {"temperature", "top_p", "top_k", "presence_penalty"}
    assert DECODING_VARIANT_KNOBS is ner.DECODING_VARIANT_KNOBS
    assert sv.SUPPLY_VARIANT_RECEIPT_SCHEMA_V6 == ner.SUPPLY_VARIANT_RECEIPT_SCHEMA_V6


@pytest.mark.parametrize("name,why", [
    ("seed", "request seed"), ("max_tokens", "completion cap"), ("thinking_budget_tokens", "thinking-budget axis"),
    ("chat_template_kwargs", "thinking switch"), ("response_format", "response format"), ("tool_choice", "tool authority"),
    ("parallel_tool_calls", "tool authority"), ("id_slot", "serving geometry"), ("min_p", "not admitted"),
    ("frequency_penalty", "not admitted"), ("logprobs", "not a sampling parameter"),
])
def test_a_parameter_another_axis_owns_is_refused_by_name_with_its_owner(name, why):
    block = _mutated(lambda b: b["arms"][0]["decoding"].update({name: 1}))
    with pytest.raises(SupplyVariantError, match=name) as raised:
        _parse(block)
    assert why in str(raised.value)


def test_an_unknown_parameter_is_refused_by_name():
    with pytest.raises(SupplyVariantError, match="unknown sampling parameter 'mirostat'"):
        _parse(_mutated(lambda b: b["arms"][0]["decoding"].update({"mirostat": 1})))


@pytest.mark.parametrize("name,value", [
    ("temperature", -0.1), ("temperature", 1.6), ("temperature", 2), ("top_p", 0), ("top_p", 1.01), ("top_p", -0.5),
    ("top_k", 0), ("top_k", 201), ("top_k", -3), ("presence_penalty", -0.5), ("presence_penalty", 2.5),
])
def test_an_out_of_bounds_value_is_refused(name, value):
    with pytest.raises(SupplyVariantError, match="outside"):
        _parse(_mutated(lambda b: b["arms"][0]["decoding"].update({name: value})))


@pytest.mark.parametrize("name,value,match", [
    ("temperature", True, "must be a number"), ("temperature", "0.6", "must be a number"), ("temperature", None, "must be a number"),
    ("temperature", math.nan, "finite|outside"), ("temperature", math.inf, "finite|outside"),
    ("top_k", 20.0, "must be an integer"), ("top_k", True, "must be a number"),
    ("top_p", [0.95], "must be a number"),
])
def test_a_mistyped_or_non_finite_value_is_refused(name, value, match):
    with pytest.raises(SupplyVariantError, match=match):
        _parse(_mutated(lambda b: b["arms"][0]["decoding"].update({name: value})))


def test_the_bounds_are_inclusive_where_stated():
    block = _mutated(lambda b: b["arms"][0].update(decoding={"temperature": 1.5, "top_p": 1.0, "top_k": 200, "presence_penalty": 2.0}))
    assert _parse(block).arm("d1").decoding["top_k"] == 200
    block = _mutated(lambda b: b["arms"][0].update(decoding={"temperature": 0, "presence_penalty": 0.0, "top_k": 1}))
    assert _parse(block).arm("d1").decoding["temperature"] == 0


@pytest.mark.parametrize("decoding", [{}, None, [], "T=0.6", [("temperature", 0.6)]])
def test_a_candidate_with_an_empty_or_non_object_decoding_is_refused(decoding):
    with pytest.raises(SupplyVariantError, match="non-empty object"):
        _parse(_mutated(lambda b: b["arms"][0].update(decoding=decoding)))


def test_a_candidate_without_a_decoding_is_refused():
    with pytest.raises(SupplyVariantError, match="must declare a decoding override"):
        _parse(_mutated(lambda b: b["arms"][0].pop("decoding")))


@pytest.mark.parametrize("key", ["instruction_template", "template_tokens", "overrides", "release_swap", "knobs", "max_supplied_items"])
def test_a_template_or_supply_reach_on_an_arm_is_refused(key):
    with pytest.raises(SupplyVariantError, match="overrides exactly its sampling parameters and nothing else"):
        _parse(_mutated(lambda b: b["arms"][0].update({key: {}})))


def test_an_unknown_arm_key_is_refused():
    with pytest.raises(SupplyVariantError, match="unknown keys"):
        _parse(_mutated(lambda b: b["arms"][0].update(thinking_policy={})))


def test_the_delivering_arm_and_the_twin_carry_no_override():
    with pytest.raises(SupplyVariantError, match="delivering arm or the twin and must declare no decoding"):
        _parse(_mutated(lambda b: b["arms"][-1].update(decoding={"temperature": 0.1})))
    with pytest.raises(SupplyVariantError, match="delivering arm or the twin and must declare no decoding"):
        _parse(_mutated(lambda b: b["arms"][-2].update(decoding={"temperature": 0.1})))


def test_the_delivering_arm_is_last_unique_and_the_twin_is_its_twin():
    with pytest.raises(SupplyVariantError, match="must be the LAST arm"):
        _parse(_mutated(lambda b: b["arms"].reverse()))
    with pytest.raises(SupplyVariantError, match="exactly one arm with deliver: true"):
        _parse(_mutated(lambda b: (b["arms"][0].pop("decoding"), b["arms"][0].update(deliver=True))))
    with pytest.raises(SupplyVariantError, match="not the delivering arm"):
        _parse(_mutated(lambda b: b["arms"][-2].update(replicate_of="d1")))
    with pytest.raises(SupplyVariantError, match="at most one replicate_of twin"):
        _parse(_mutated(lambda b: b["arms"].insert(0, {"arm_id": "aa2", "replicate_of": "lock"})))
    with pytest.raises(SupplyVariantError, match="distinct"):
        _parse(_mutated(lambda b: b["arms"][1].update(arm_id="d1")))


def test_the_node_the_key_set_and_the_candidate_count_are_checked():
    with pytest.raises(SupplyVariantError, match="exactly"):
        _parse(_mutated(lambda b: b.pop("template_tokens")))
    with pytest.raises(SupplyVariantError, match="exactly"):
        _parse(_mutated(lambda b: b.update(extra=1)))
    with pytest.raises(SupplyVariantError, match="declared on exactly the node it names"):
        _parse(_mutated(lambda b: b.update(node="perception")))
    for role in ("perception", "reviewer", "planner"):
        with pytest.raises(SupplyVariantError, match="may sit only at"):
            _parse(role_kind=role)
    with pytest.raises(SupplyVariantError, match="between 1 and 6 candidate"):
        _parse(_mutated(lambda b: b.update(arms=[{"arm_id": "aa", "replicate_of": "lock"}, {"arm_id": "lock", "deliver": True}])))
    seven = [{"arm_id": f"d{i}", "decoding": {"temperature": 0.1 * i}} for i in range(1, 8)]
    with pytest.raises(SupplyVariantError, match="between 1 and 6 candidate"):
        _parse(_mutated(lambda b: b.update(arms=seven + [{"arm_id": "lock", "deliver": True}])))


def test_two_arms_with_the_same_override_and_an_arm_equal_to_the_lock_are_refused():
    with pytest.raises(SupplyVariantError, match="same sampling override"):
        _parse(_mutated(lambda b: b["arms"][1].update(decoding={"top_k": 20, "top_p": 0.95, "temperature": 0.6})))
    with pytest.raises(SupplyVariantError, match="second spelling of the delivering arm"):
        _parse(_mutated(lambda b: b["arms"][0].update(decoding={"temperature": 0})))
    # the lock-equal rule needs the lock's decoding; absent, only the other refusals apply
    assert _parse(_mutated(lambda b: b["arms"][0].update(decoding={"temperature": 0})), locked_decoding=None).arm("d1").decoding == {"temperature": 0}
    # a different value for the same key is a real arm
    assert _parse(_mutated(lambda b: b["arms"][0].update(decoding={"temperature": 0.0001}))).arm("d1").decoding == {"temperature": 0.0001}


def test_the_prompt_fit_refusal_applies_to_every_arm():
    tight = dict(FIT, base_prompt_tokens=17000)
    with pytest.raises(SupplyVariantError, match="exceeds the .*-token limit"):
        _parse(_mutated(lambda b: b.update(fit_estimate=tight)))


# ---- the receipt --------------------------------------------------------------------------------------------------------------


IDS = ("value:a", "value:b")


def _receipt(group=None, *, ids_for=None):
    group = group or _parse()
    records = [
        supply_variant_arm_record(
            arm=arm, arm_index=index, contact_id=f"c{index}", supplied_value_ids=(ids_for or {}).get(arm.arm_id, IDS),
            decoding_group=True,
        )
        for index, arm in enumerate(group.arms)
    ]
    return group, supply_variant_receipt(group=group, phase_id="solver", records=records)


def _validate(receipt, group, **kwargs):
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id=group.delivered_arm.arm_id, phase_id="solver", **kwargs,
    )


def test_the_v6_receipt_carries_each_arms_decoding_override_and_validates():
    group, receipt = _receipt()
    assert receipt["schema"] == "saea-supply-variant-arms-v6" and receipt["arm_visits"] == "first"
    by_arm = {row["arm_id"]: row for row in receipt["arms"]}
    assert by_arm["d1"]["decoding_override"] == D1 and by_arm["d2"]["decoding_override"] == D2
    assert by_arm["d4"]["decoding_override"] == {"temperature": 0, "presence_penalty": 1.5}
    assert by_arm["aa"]["decoding_override"] is None and by_arm["lock"]["decoding_override"] is None
    assert all(row["resolved_knobs"] == [] and row["release_swap"] is None for row in receipt["arms"])
    assert by_arm["aa"]["replicate_of"] == "lock"
    _validate(receipt, group, retrieved_value_ids=IDS, arm_visits="first")
    # the receipt is JSON-stable (it travels the framework's node result and the sealed bundle)
    assert json.loads(json.dumps(receipt)) == receipt
    assert "saea-supply-variant-arms-v6" in __import__(
        "speech_aware_evidence_acquisition.rails.consumption_module", fromlist=["NODE_RECEIPT_SCHEMAS"]).NODE_RECEIPT_SCHEMAS


def _arm(receipt, arm_id):
    return next(row for row in receipt["arms"] if row["arm_id"] == arm_id)


RECEIPT_REFUSALS = [
    pytest.param(lambda r: _arm(r, "lock").update(decoding_override={"temperature": 0.2}), "delivering arm and the twin", id="delivering-with-an-override"),
    pytest.param(lambda r: _arm(r, "aa").update(decoding_override={"temperature": 0.2}), "delivering arm and the twin", id="twin-with-an-override"),
    pytest.param(lambda r: _arm(r, "d1").update(decoding_override=None), "well-formed decoding_override", id="candidate-without-an-override"),
    pytest.param(lambda r: _arm(r, "d1").update(decoding_override={}), "well-formed decoding_override", id="candidate-with-an-empty-override"),
    pytest.param(lambda r: _arm(r, "d1").update(decoding_override={"seed": 1}), "closed set", id="candidate-naming-the-seed"),
    pytest.param(lambda r: _arm(r, "d1").update(decoding_override={"temperature": 9}), "outside its bounds", id="candidate-out-of-bounds"),
    pytest.param(lambda r: _arm(r, "d1").update(decoding_override={"temperature": True}), "must be a number", id="candidate-with-a-boolean"),
    pytest.param(lambda r: _arm(r, "d2").update(decoding_override=dict(_arm(r, "d1")["decoding_override"])), "distinct sampling overrides", id="duplicate-override-in-the-receipt"),
    pytest.param(lambda r: _arm(r, "d1").update(resolved_knobs=[{"path": "a.b", "value": 1}]), "resolve no knobs", id="arm-with-a-knob"),
    pytest.param(lambda r: _arm(r, "d1").update(release_swap={"store_id": "s", "release": "r"}), "no release_swap", id="arm-with-a-release-swap"),
    pytest.param(lambda r: _arm(r, "d1").update(supplied_value_ids=["value:z"], supplied_item_count=1), "varies the sampling, never the evidence", id="arm-with-different-evidence"),
    pytest.param(lambda r: _arm(r, "d1").pop("decoding_override"), "invalid shape", id="a-missing-field"),
    pytest.param(lambda r: _arm(r, "d1").update(instruction_template=None), "invalid shape", id="a-v4-field-on-a-v6-row"),
    pytest.param(lambda r: r.update(schema="saea-supply-variant-arms-v9"), "unregistered schema", id="unknown-schema"),
]


@pytest.mark.parametrize("mutate,expected", RECEIPT_REFUSALS)
def test_the_receipt_validator_refuses_every_malformation(mutate, expected):
    group, receipt = _receipt()
    mutate(receipt)
    with pytest.raises(ValueError, match=expected):
        _validate(receipt, group)


def test_a_v3_v4_row_shape_is_not_accepted_under_v6_and_v6_rows_are_not_accepted_under_v3():
    group, receipt = _receipt()
    v3 = copy.deepcopy(receipt)
    v3["schema"] = "saea-supply-variant-arms-v3"
    with pytest.raises(ValueError, match="invalid shape"):
        _validate(v3, group)           # the v6 rows carry decoding_override, which a v3 row may not
    for row in v3["arms"]:
        row.pop("decoding_override")
    # a v3 receipt of a SUPPLY group needs a knob or a release swap on every non-delivering arm: this one has none
    with pytest.raises(ValueError, match="at least one knob"):
        _validate(v3, group)


def test_older_receipts_still_validate_unchanged():
    """No sealed data is rewritten: a v3 supply receipt and a v4 template receipt built with the existing record shapes validate."""

    from speech_aware_evidence_acquisition.rails.supply_variants import parse_template_variants  # noqa: PLC0415

    pin = {"relpath": "configs/probes/nx/t1.txt", "sha256": "a" * 64}
    template_group = parse_template_variants(
        {"node": "solver", "arms": [{"arm_id": "t1", "instruction_template": pin, "template_tokens": 400},
                                    {"arm_id": "lock", "deliver": True, "template_tokens": 380}],
         "max_supplied_items": 4, "fit_estimate": dict(FIT, base_prompt_tokens=9000)},
        role_kind="solver", phase_id="solver", locked_template="probes/slurp_native_role_solver_v2.txt",
    )
    records = [supply_variant_arm_record(arm=arm, arm_index=i, contact_id=f"c{i}", supplied_value_ids=IDS, template_group=True)
               for i, arm in enumerate(template_group.arms)]
    v4 = supply_variant_receipt(group=template_group, phase_id="solver", records=records)
    assert v4["schema"] == "saea-supply-variant-arms-v4"
    validate_supply_variant_receipt(v4, arm_ids=template_group.arm_ids, delivered_arm_id="lock", phase_id="solver", arm_visits="first")
    assert "decoding_override" not in v4["arms"][0] and "decoding" not in template_group.as_json()["arms"][0]


def test_an_arm_record_for_a_decoding_group_states_the_declared_override_only():
    group = _parse()
    record = supply_variant_arm_record(arm=group.arm("d2"), arm_index=1, contact_id="c1", supplied_value_ids=IDS, decoding_group=True)
    assert record["decoding_override"] == D2
    plain = supply_variant_arm_record(arm=group.arm("lock"), arm_index=5, contact_id="c5", supplied_value_ids=IDS)
    assert "decoding_override" not in plain           # every other record shape is byte-identical to before


# ---- the loader ---------------------------------------------------------------------------------------------------------------


def _loader_values(*, candidates=4, twin=True):
    from test_review_off_capacity import values  # noqa: PLC0415

    v = copy.deepcopy(values(False))
    v["phase_material"] = {"solver": {"instruction_template": "probes/slurp_native_role_solver_v2.txt"}}
    v["decoding_params"] = dict(LOCKED_DECODING)
    arms = [{"arm_id": f"d{i}", "decoding": {"temperature": 0.1 * i}} for i in range(1, candidates + 1)]
    if twin:
        arms.append({"arm_id": "aa", "replicate_of": "lock"})
    arms.append({"arm_id": "lock", "deliver": True})
    v["native_episode"]["roles"]["solver"]["decoding_variants"] = {
        "node": "solver", "arms": arms, "max_supplied_items": 55, "template_tokens": 323, "fit_estimate": dict(FIT),
    }
    return v


def _program(ceiling):
    from test_native_episode_config import program  # noqa: PLC0415

    return program(ceiling=ceiling)


def _load(v, ceiling):
    from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: PLC0415

    return load_native_episode_config(v, _program(ceiling))


def test_the_loader_parses_the_group_and_adds_k_minus_one_to_the_ceiling():
    # review-off graph: perception 1 + solver 1 = 2; K = 4 candidates + twin + lock = 6 -> 2 + 5
    config = _load(_loader_values(), 7)
    group = config.supply_variant_group
    assert config.max_contacts == 7 and group is not None and group.is_decoding and not group.is_template
    assert group.arm_ids == ("d1", "d2", "d3", "d4", "aa", "lock")
    assert config.supply_variant_arm_count == 6 and config.supply_variant_phase_id == "solver"
    assert config.role("solver").supply_variants is group


def test_the_program_ceiling_must_equal_the_bounded_graph_ceiling():
    with pytest.raises(ValueError, match="program contact ceiling must equal"):
        _load(_loader_values(), 6)


def test_the_loader_compares_an_override_with_the_locks_own_decoding():
    v = _loader_values()
    v["native_episode"]["roles"]["solver"]["decoding_variants"]["arms"][0]["decoding"] = {"temperature": 0}
    with pytest.raises(ValueError, match="second spelling of the delivering arm"):
        _load(v, 7)


def test_an_override_naming_another_axis_is_refused_by_the_loader():
    v = _loader_values()
    v["native_episode"]["roles"]["solver"]["decoding_variants"]["arms"][0]["decoding"] = {"seed": 3}
    with pytest.raises(ValueError, match="request seed is the lock's"):
        _load(v, 7)


@pytest.mark.parametrize("other,block", [
    ("template_variants", {"arms": [], "fit_estimate": {}}),
    ("supply_variants", {"arms": [], "fit_estimate": {}}),
])
def test_decoding_variants_cannot_share_a_node_with_another_fan_out(other, block):
    v = _loader_values()
    v["native_episode"]["roles"]["solver"][other] = block
    with pytest.raises(ValueError, match="cannot combine"):
        _load(v, 7)


@pytest.mark.parametrize("role", ["perception", "reviewer", "planner"])
def test_a_decoding_block_on_another_node_is_refused_by_name(role):
    v = _loader_values()
    block = v["native_episode"]["roles"]["solver"].pop("decoding_variants")
    v["native_episode"]["roles"][role]["decoding_variants"] = block
    with pytest.raises(ValueError, match=f"roles.{role}.decoding_variants is refused"):
        _load(v, 2)


def test_a_template_arm_key_is_refused_by_the_loader():
    v = _loader_values()
    v["native_episode"]["roles"]["solver"]["decoding_variants"]["arms"][0]["instruction_template"] = {
        "relpath": "probes/x.txt", "sha256": "a" * 64}
    with pytest.raises(ValueError, match="overrides exactly its sampling parameters"):
        _load(v, 7)


def test_a_config_without_the_key_is_unchanged():
    v = _loader_values()
    del v["native_episode"]["roles"]["solver"]["decoding_variants"]
    config = _load(v, 2)
    assert config.supply_variant_group is None and config.max_contacts == 2


def test_the_review_off_rehearsal_profile_admits_a_decoding_group():
    from speech_aware_evidence_acquisition.analysis import native_graph_rehearsal as graph  # noqa: PLC0415

    v = _loader_values()
    v["policy"] = "phase-native-module-v1-c7"
    v["native_graph_capacity_profile"] = "review-off-v1"
    parsed = graph.rehearsal_profile(v, "review-off-v1")
    assert parsed.max_contacts == 7 and parsed.supply_variant_group.is_decoding


# ---- the module compiler ------------------------------------------------------------------------------------------------------


def _decoding_columns(arms=(("d1", D1), ("d2", D2), ("d3", D3), ("d4", D4))):
    return [{"column_id": name, "kind": "decoding", "node": "solver", "decoding": dict(decoding)} for name, decoding in arms]


def _decoding_block(**kwargs):
    from test_consumption_module_review_off import review_off_block  # noqa: PLC0415

    block = review_off_block()
    block["columns"] = _decoding_columns(**kwargs)
    block["decoding_frame"] = {"max_supplied_items": 55, "template_tokens": 323, "twin": True, "fit_estimate": dict(FIT)}
    return block


def test_decoding_columns_compile_to_one_block_with_the_twin_and_the_lock_last():
    from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: PLC0415

    composed = cm.compile_module(_decoding_block(), carrier_module_hooks())
    values = composed.values()
    block = values["native_episode"]["roles"]["solver"]["decoding_variants"]
    assert block["node"] == "solver" and block["max_supplied_items"] == 55 and block["template_tokens"] == 323
    assert [(a["arm_id"], a.get("deliver"), a.get("replicate_of")) for a in block["arms"]] == [
        ("d1", None, None), ("d2", None, None), ("d3", None, None), ("d4", None, None), ("aa", None, "lock"), ("lock", True, None)]
    assert block["arms"][0]["decoding"] == D1 and block["arms"][3]["decoding"] == D4
    assert block["arms"][-1] == {"arm_id": "lock", "deliver": True} and block["arms"][-2] == {"arm_id": "aa", "replicate_of": "lock"}
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c7", 7)
    assert block["fit_estimate"] == FIT


def test_the_compiled_block_loads_through_the_runtime_loader_and_verifies():
    from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: PLC0415

    block = _decoding_block()
    composed = cm.compile_module(block, carrier_module_hooks())
    values = composed.values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    parsed = load_native_episode_config(values, default_phase_program(values["policy"]))
    assert parsed.max_contacts == composed.program_ceiling == 7 and parsed.supply_variant_group.is_decoding
    cm.verify_declared_module(block, values)
    edited = copy.deepcopy(values)
    edited["native_episode"]["roles"]["solver"]["decoding_variants"]["arms"][0]["decoding"]["temperature"] = 0.61
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, edited)


def test_the_block_identity_binds_the_decoding_override():
    from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: PLC0415

    a = cm.parse_consumption_module_block(_decoding_block())
    other = _decoding_block()
    other["columns"][0]["decoding"]["temperature"] = 0.61
    b = cm.parse_consumption_module_block(other)
    assert a.block_sha256 != b.block_sha256
    assert [c.kind for c in a.columns] == ["decoding"] * 4 and a.decoding_columns == a.columns and a.template_columns == ()
    assert a.columns[0].decoding == D1 and a.decoding_frame["template_tokens"] == 323


@pytest.mark.parametrize("mutate,match", [
    (lambda b: b["columns"][0]["decoding"].update(seed=1), "request seed"),
    (lambda b: b["columns"][0]["decoding"].update(max_tokens=9000), "completion cap"),
    (lambda b: b["columns"][0]["decoding"].update(temperature=5), "decoding"),
    (lambda b: b["columns"][0].update(decoding={}), "decoding"),
    (lambda b: b["columns"][0].pop("decoding"), "keys must be exactly"),
    (lambda b: b["columns"][0].update(template={"relpath": "x", "sha256": "a" * 64}), "keys must be exactly"),
    (lambda b: b.pop("decoding_frame"), "decoding_frame is required"),
    (lambda b: b["decoding_frame"].update(twin="yes"), "twin must be a bool"),
    (lambda b: b["columns"].append({"column_id": "t9", "kind": "template", "node": "solver",
                                    "template": {"relpath": "configs/probes/nx/t9.txt", "sha256": "a" * 64}, "template_tokens": 9}), "cannot be declared beside"),
    (lambda b: b["columns"][1].update(decoding=dict(D1)), "same sampling override"),
    (lambda b: b["columns"][1].update(node="perception"), "one node"),
])
def test_a_malformed_decoding_column_set_is_refused_by_name(mutate, match):
    from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: PLC0415

    block = _decoding_block()
    mutate(block)
    with pytest.raises(cm.ConsumptionModuleConfigError, match=match):
        cm.compile_module(block, carrier_module_hooks())


def test_a_decoding_frame_without_a_decoding_column_is_refused():
    from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: PLC0415
    from test_consumption_module_review_off import review_off_block  # noqa: PLC0415

    block = review_off_block()
    block["decoding_frame"] = {"max_supplied_items": 55, "template_tokens": 323, "twin": True, "fit_estimate": dict(FIT)}
    with pytest.raises(cm.ConsumptionModuleConfigError, match="decoding_frame is declared but no decoding column"):
        cm.parse_consumption_module_block(block)


def test_a_carrier_without_the_decoding_frame_refuses_the_column():
    import dataclasses  # noqa: PLC0415

    from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: PLC0415

    hooks = dataclasses.replace(carrier_module_hooks(), decoding_variant_frame=None)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="decoding_variant_frame"):
        cm.compile_module(_decoding_block(), hooks)
