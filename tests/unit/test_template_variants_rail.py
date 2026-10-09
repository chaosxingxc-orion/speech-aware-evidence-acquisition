"""NX programme E1 (2026-10-09): the node-template arm kind -- the rail.

``rails.supply_variants.parse_template_variants`` is the node-template twin of
``parse_supply_variants``: each non-delivering, non-twin arm overrides exactly
ONE thing, the node's ``instruction_template`` (a hash-pinned relpath under
``probes/``), the delivering arm is LAST and carries no override, and every
other reach is refused by name before any contact. This module is the model-free
proof of the parse, the arm record, the v4 receipt and its validator.
"""

from __future__ import annotations

import copy

import pytest

from speech_aware_evidence_acquisition.rails import native_episode_receipt as ner
from speech_aware_evidence_acquisition.rails import supply_variants as sv
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_supply_variant_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    SUPPLY_VARIANT_RECEIPT_SCHEMA_V4,
    SupplyVariantError,
    parse_template_variants,
    supply_variant_arm_record,
    supply_variant_receipt,
)

FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 640,
    "base_prompt_tokens": 9600,
    "tokens_per_supplied_item": 120,
}
SHA_A, SHA_B, SHA_C, SHA_L = ("a" * 64, "b" * 64, "c" * 64, "d" * 64)
LOCKED = "probes/slurp_native_role_solver_v2.txt"


def _pin(name, sha):
    return {"relpath": f"configs/probes/nx/{name}.txt", "sha256": sha}


def _block(**overrides):
    block = {
        "node": "solver",
        "arms": [
            {"arm_id": "t1", "instruction_template": _pin("t1", SHA_A), "template_tokens": 410},
            {"arm_id": "t2", "instruction_template": _pin("t2", SHA_B), "template_tokens": 395},
            {"arm_id": "aa", "replicate_of": "lock"},
            {"arm_id": "lock", "deliver": True, "template_tokens": 380},
        ],
        "max_supplied_items": 48,
        "fit_estimate": dict(FIT),
    }
    block.update(overrides)
    return block


def _parse(block=None, **kwargs):
    options = {"role_kind": "solver", "phase_id": "solver", "locked_template": LOCKED}
    options.update(kwargs)
    return parse_template_variants(block if block is not None else _block(), **options)


def test_a_well_formed_group_parses_to_its_declared_order():
    group = _parse()
    assert group.kind == "template" and group.is_template
    assert group.arm_ids == ("t1", "t2", "aa", "lock")
    assert group.arm_visits == "first"
    assert group.delivered_arm.arm_id == "lock"
    assert group.delivered_arm.instruction_template is None
    assert group.delivered_arm.knobs == () and group.delivered_arm.release_swap is None
    t1 = group.arm("t1")
    # The ``configs/`` prefix is spelled out by the declaration and stripped to the
    # phase_material form.
    assert t1.instruction_template.relpath == "probes/nx/t1.txt"
    assert t1.instruction_template.sha256 == SHA_A
    assert group.arm("aa").replicate_of == "lock"
    assert group.arm("aa").instruction_template is None
    # Every arm shares ONE supply bound: the supply is unvaried.
    assert {arm.max_supplied_items for arm in group.arms} == {48}


def test_the_prefix_free_spelling_is_equivalent():
    block = _block()
    block["arms"][0]["instruction_template"] = {
        "relpath": "probes/nx/t1.txt", "sha256": SHA_A,
    }
    assert _parse(block).arm("t1").instruction_template.relpath == "probes/nx/t1.txt"


def test_the_fit_estimate_counts_the_arms_own_template():
    group = _parse()
    fit = group.fit_estimate
    assert fit.estimated_prompt_tokens(group.arm("t1")) == 9600 + 410 + 48 * 120
    assert fit.estimated_prompt_tokens(group.arm("lock")) == 9600 + 380 + 48 * 120
    # the twin renders the delivering arm's template and declares no tokens of its own
    assert group.arm("aa").template_tokens == 0


def test_six_candidates_plus_the_lock_and_a_twin_is_the_eight_arm_bound():
    block = _block()
    block["arms"] = [
        {"arm_id": f"t{i}", "instruction_template": _pin(f"t{i}", f"{i}" * 64),
         "template_tokens": 400}
        for i in range(1, 7)
    ] + [{"arm_id": "aa", "replicate_of": "lock"},
         {"arm_id": "lock", "deliver": True, "template_tokens": 380}]
    group = _parse(block)
    assert group.arm_count == sv.MAX_SUPPLY_VARIANT_ARMS == 8


def test_a_group_without_a_twin_parses():
    block = _block()
    block["arms"] = [a for a in block["arms"] if a["arm_id"] != "aa"]
    assert _parse(block).arm_ids == ("t1", "t2", "lock")


def _mutate(fn):
    def apply(block):
        fn(block)
        return block
    return apply


REFUSALS = [
    pytest.param(
        lambda b: b.update(extra=1), "exactly", id="unknown-block-key"),
    pytest.param(
        lambda b: b.pop("fit_estimate"), "exactly", id="missing-fit-estimate"),
    pytest.param(
        lambda b: b.update(node="reviewer"), "declared on exactly the node it names",
        id="variant-declared-on-another-node-than-named"),
    pytest.param(
        lambda b: b["arms"][0].update(overrides={"knowledge_stores.x.phase_supply.solver.k": 3}),
        "overrides exactly its instruction_template", id="supply-knob-override"),
    pytest.param(
        lambda b: b["arms"][0].update(release_swap={"store_id": "s", "release": "r"}),
        "overrides exactly its instruction_template", id="release-swap"),
    pytest.param(
        lambda b: b["arms"][0].update(max_supplied_items=3),
        "overrides exactly its instruction_template", id="per-arm-supply-bound"),
    pytest.param(
        lambda b: b["arms"][0].update(decoding_params={"temperature": 1}),
        "unknown keys", id="decoding-knob"),
    pytest.param(
        lambda b: b["arms"][0].pop("instruction_template"),
        "must declare an instruction_template", id="candidate-without-template"),
    pytest.param(
        lambda b: b["arms"][0]["instruction_template"].pop("sha256"),
        "exactly {relpath, sha256}", id="missing-sha256"),
    pytest.param(
        lambda b: b["arms"][0]["instruction_template"].update(sha256="A" * 64),
        "lowercase 64-hex", id="uppercase-sha256"),
    pytest.param(
        lambda b: b["arms"][0]["instruction_template"].update(sha256="ab"),
        "lowercase 64-hex", id="short-sha256"),
    pytest.param(
        lambda b: b["arms"][0]["instruction_template"].update(relpath="configs/baseline/x.txt"),
        "outside the allowed template roots", id="outside-allowed-roots"),
    pytest.param(
        lambda b: b["arms"][0]["instruction_template"].update(relpath="configs/probes/../x.txt"),
        "not a plain repository-relative path", id="parent-traversal"),
    pytest.param(
        lambda b: b["arms"][0]["instruction_template"].update(relpath="/etc/passwd"),
        "not a plain repository-relative path", id="absolute-path"),
    pytest.param(
        lambda b: b["arms"][0].update(template_tokens=0),
        "template_tokens must be a positive integer", id="no-template-tokens"),
    pytest.param(
        lambda b: b["arms"][3].update(template_tokens=0),
        "template_tokens must be a positive integer", id="delivering-arm-no-tokens"),
    pytest.param(
        lambda b: b["arms"][2].update(template_tokens=10),
        "twin and declares no template_tokens", id="twin-with-tokens"),
    pytest.param(
        lambda b: b["arms"][3].update(instruction_template=_pin("x", SHA_L)),
        "delivering arm or the twin and must declare no instruction_template",
        id="delivering-arm-carries-a-template"),
    pytest.param(
        lambda b: b["arms"][2].update(instruction_template=_pin("x", SHA_L)),
        "delivering arm or the twin and must declare no instruction_template",
        id="twin-carries-a-template"),
    pytest.param(
        lambda b: b["arms"].reverse(), "must be the LAST arm", id="delivering-arm-not-last"),
    pytest.param(
        lambda b: b["arms"][3].update(deliver=False, instruction_template=_pin("t3", SHA_C)),
        "exactly one arm with deliver", id="no-delivering-arm"),
    pytest.param(
        lambda b: (b["arms"][0].pop("instruction_template"), b["arms"][0].update(deliver=True)),
        "exactly one arm with deliver", id="two-delivering-arms"),
    pytest.param(
        lambda b: b["arms"][1].update(arm_id="t1"),
        "arm ids must be distinct", id="arm-id-collision"),
    pytest.param(
        lambda b: b["arms"][2].update(replicate_of="t1"),
        "which is not the delivering arm", id="twin-of-a-non-delivering-arm"),
    pytest.param(
        lambda b: b["arms"].insert(2, {"arm_id": "aa2", "replicate_of": "lock"}),
        "at most one replicate_of twin", id="two-twins"),
    pytest.param(
        lambda b: b["arms"][1].update(instruction_template=_pin("t1b", SHA_A)),
        "name the same template", id="duplicate-digest"),
    pytest.param(
        lambda b: b["arms"][1].update(instruction_template=_pin("t1", SHA_B)),
        "name the same template", id="duplicate-path"),
    pytest.param(
        lambda b: b["arms"][1].update(
            instruction_template={"relpath": LOCKED, "sha256": SHA_C}),
        "node's own locked template", id="candidate-equals-the-locked-template"),
    pytest.param(
        lambda b: b["arms"][0].update(template_tokens=9000),
        "exceeds", id="fit-refusal"),
]


@pytest.mark.parametrize("mutate,expected", REFUSALS)
def test_every_declared_refusal_is_raised_by_name(mutate, expected):
    block = copy.deepcopy(_block())
    mutate(block)
    with pytest.raises(SupplyVariantError, match=expected):
        _parse(block)


def test_a_role_other_than_the_solver_is_refused():
    with pytest.raises(SupplyVariantError, match="may sit only at"):
        _parse(_block(node="reviewer"), role_kind="reviewer", phase_id="reviewer")


def test_zero_and_seven_candidate_arms_are_refused():
    block = _block()
    block["arms"] = [{"arm_id": "lock", "deliver": True, "template_tokens": 380}]
    with pytest.raises(SupplyVariantError, match="between 1 and 6"):
        _parse(block)
    block["arms"] = [
        {"arm_id": f"t{i}", "instruction_template": _pin(f"t{i}", f"{i}" * 64),
         "template_tokens": 400}
        for i in range(1, 8)
    ] + [{"arm_id": "lock", "deliver": True, "template_tokens": 380}]
    with pytest.raises(SupplyVariantError, match="between 1 and 6"):
        _parse(block)


def test_a_non_object_block_is_refused():
    with pytest.raises(SupplyVariantError, match="exactly"):
        _parse([])


def test_the_supply_kind_parser_is_unchanged_by_the_new_kind():
    group = sv.parse_supply_variants(
        {
            "arms": [
                {"arm_id": "w", "max_supplied_items": 4,
                 "overrides": {"knowledge_stores.train-exemplars.phase_supply.solver.k": 30}},
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 4},
            ],
            "fit_estimate": dict(FIT),
        },
        phase_id="solver", first_phase_id="perception",
        declared_stores=("train-exemplars",),
    )
    assert group.kind == "supply" and not group.is_template
    assert "kind" not in group.as_json()
    assert "instruction_template" not in group.arm("w").as_json()


# ---------------------------------------------------------------------------
# The arm record, the v4 receipt and its validator.
# ---------------------------------------------------------------------------

IDS = ("value:a", "value:b")


def _receipt(group=None, ids_for=None):
    group = group or _parse()
    records = [
        supply_variant_arm_record(
            arm=arm, arm_index=index, contact_id=f"c{index}",
            supplied_value_ids=(ids_for or {}).get(arm.arm_id, IDS),
            template_group=True,
        )
        for index, arm in enumerate(group.arms)
    ]
    return group, supply_variant_receipt(group=group, phase_id="solver", records=records)


def _validate(receipt, group, **kwargs):
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids,
        delivered_arm_id=group.delivered_arm.arm_id, phase_id="solver", **kwargs,
    )


def test_the_schema_constant_is_one_string_in_both_modules():
    assert SUPPLY_VARIANT_RECEIPT_SCHEMA_V4 == ner.SUPPLY_VARIANT_RECEIPT_SCHEMA_V4
    assert SUPPLY_VARIANT_RECEIPT_SCHEMA_V4 == "saea-supply-variant-arms-v4"
    assert "saea-supply-variant-arms-v4" in __import__(
        "speech_aware_evidence_acquisition.rails.consumption_module",
        fromlist=["NODE_RECEIPT_SCHEMAS"],
    ).NODE_RECEIPT_SCHEMAS


def test_the_arm_rows_carry_the_resolved_template_pin_under_the_arm_id():
    group, receipt = _receipt()
    assert receipt["schema"] == SUPPLY_VARIANT_RECEIPT_SCHEMA_V4
    assert receipt["arm_visits"] == "first" and receipt["visit_index"] == 0
    rows = {row["arm_id"]: row for row in receipt["arms"]}
    assert rows["t1"]["instruction_template"] == {"relpath": "probes/nx/t1.txt", "sha256": SHA_A}
    assert rows["t2"]["instruction_template"] == {"relpath": "probes/nx/t2.txt", "sha256": SHA_B}
    assert rows["aa"]["instruction_template"] is None
    assert rows["lock"]["instruction_template"] is None
    assert all(row["resolved_knobs"] == [] and row["release_swap"] is None for row in rows.values())
    assert all(row["supplied_value_ids"] == list(IDS) for row in rows.values())
    _validate(receipt, group, arm_visits="first")


def test_a_supply_kind_receipt_is_still_v3_and_unchanged():
    group = sv.parse_supply_variants(
        {
            "arms": [
                {"arm_id": "w", "max_supplied_items": 4,
                 "overrides": {"knowledge_stores.train-exemplars.phase_supply.solver.k": 30}},
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 4},
            ],
            "fit_estimate": dict(FIT),
        },
        phase_id="solver", first_phase_id="perception",
        declared_stores=("train-exemplars",),
    )
    records = [
        supply_variant_arm_record(arm=arm, arm_index=i, contact_id=f"c{i}", supplied_value_ids=())
        for i, arm in enumerate(group.arms)
    ]
    receipt = supply_variant_receipt(group=group, phase_id="solver", records=records)
    assert receipt["schema"] == "saea-supply-variant-arms-v3"
    assert all("instruction_template" not in row for row in receipt["arms"])


def _arm(receipt, arm_id):
    return next(row for row in receipt["arms"] if row["arm_id"] == arm_id)


RECEIPT_REFUSALS = [
    pytest.param(
        lambda r: _arm(r, "t1").pop("instruction_template"),
        "invalid shape", id="missing-template-field"),
    pytest.param(
        lambda r: _arm(r, "t1").update(instruction_template=None),
        "must carry exactly one", id="candidate-without-template"),
    pytest.param(
        lambda r: _arm(r, "t1").update(instruction_template={"relpath": "x", "sha256": "z"}),
        "must carry exactly one", id="candidate-bad-sha"),
    pytest.param(
        lambda r: _arm(r, "lock").update(instruction_template={"relpath": "probes/x.txt", "sha256": SHA_L}),
        "must declare no instruction_template", id="delivering-arm-with-template"),
    pytest.param(
        lambda r: _arm(r, "aa").update(instruction_template={"relpath": "probes/x.txt", "sha256": SHA_L}),
        "must declare no instruction_template", id="twin-with-template"),
    pytest.param(
        lambda r: _arm(r, "t1").update(resolved_knobs=[{"path": "a.b.c.d", "value": 1}]),
        "resolve no knobs", id="arm-with-a-knob"),
    pytest.param(
        lambda r: _arm(r, "t1").update(release_swap={"store_id": "s", "release": "r"}),
        "no release_swap", id="arm-with-a-release-swap"),
    pytest.param(
        lambda r: _arm(r, "t1").update(supplied_value_ids=["value:z"], supplied_item_count=1),
        "varies the instruction, never the evidence", id="arm-with-different-evidence"),
    pytest.param(
        lambda r: _arm(r, "t2").update(instruction_template=dict(_arm(r, "t1")["instruction_template"])),
        "distinct templates", id="duplicate-template-in-the-receipt"),
    pytest.param(
        lambda r: r.update(schema="saea-supply-variant-arms-v9"),
        "unregistered schema", id="unknown-schema"),
]


@pytest.mark.parametrize("mutate,expected", RECEIPT_REFUSALS)
def test_the_receipt_validator_refuses_every_malformation(mutate, expected):
    group, receipt = _receipt()
    receipt = copy.deepcopy(receipt)
    mutate(receipt)
    with pytest.raises(ValueError, match=expected):
        _validate(receipt, group)


def test_the_delivering_arms_ids_must_open_the_rows_own_state():
    group, receipt = _receipt()
    _validate(receipt, group, retrieved_value_ids=[*IDS, "value:later"])
    with pytest.raises(ValueError, match="ordered prefix"):
        _validate(receipt, group, retrieved_value_ids=["value:other"])
