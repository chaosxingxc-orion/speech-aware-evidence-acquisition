"""Unit tests for the Perception-branch parser, ceiling and receipt helpers
(same-flight instrument phase 2, merge set C, item 2).
"""

import pytest

from speech_aware_evidence_acquisition.rails.supply_variants import (
    MAX_PERCEPTION_BRANCHES,
    PERCEPTION_BRANCH_LEVEL_NOTE,
    PERCEPTION_BRANCH_LEVEL_SOLVER,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA,
    PerceptionBranchError,
    SupplyVariantReleaseSwap,
    parse_perception_branches,
    perception_branch_ceiling,
    perception_branch_record,
    perception_branch_receipt,
)

FIT_ESTIMATE = {
    "slot_tokens": 24576,
    "completion_ceiling": 512,
    "base_prompt_tokens": 4000,
    "tokens_per_supplied_item": 100,
}
STORE = "intent-boundaries"
SHA = "a" * 64


def _block(branches, level=1, fit_estimate=None):
    return {
        "branches": branches,
        "fit_estimate": fit_estimate or FIT_ESTIMATE,
        "level": level,
    }


def _a(max_supplied_items=60):
    return {"branch_id": "A", "deliver": True, "max_supplied_items": max_supplied_items}


def _t(branch_id="T", max_supplied_items=60):
    return {"branch_id": branch_id, "replicate_of": "A", "max_supplied_items": max_supplied_items}


def _b_knob(branch_id="B", max_supplied_items=60, tail="k", value=60):
    return {
        "branch_id": branch_id,
        "max_supplied_items": max_supplied_items,
        "overrides": {f"knowledge_stores.{STORE}.phase_supply.perception.{tail}": value},
    }


def _parse(branches, **kwargs):
    kwargs.setdefault("first_phase_id", "perception")
    kwargs.setdefault("declared_stores", (STORE,))
    return parse_perception_branches(_block(branches, **{
        k: kwargs.pop(k) for k in ("level", "fit_estimate") if k in kwargs
    }), **kwargs)


def test_minimal_group_parses_a_last_with_required_twin():
    group = _parse([_b_knob(), _t(), _a()])
    assert group.branch_ids == ("B", "T", "A")
    assert group.delivering_branch.branch_id == "A"
    assert group.twin_branch.branch_id == "T"
    assert group.level == PERCEPTION_BRANCH_LEVEL_NOTE


def test_rank_weights_tail_admitted_and_targets_first_phase():
    group = _parse([_b_knob(tail="rank_weights.w_agree", value=0), _t(), _a()])
    assert group.branch("B").knobs[0].tail == ("rank_weights", "w_agree")


def test_knob_must_target_first_phase():
    with pytest.raises(PerceptionBranchError, match="FIRST phase"):
        _parse([
            {
                "branch_id": "B", "max_supplied_items": 60,
                "overrides": {f"knowledge_stores.{STORE}.phase_supply.solver.k": 8},
            },
            _t(), _a(),
        ])


def test_unadmitted_route_refused():
    with pytest.raises(PerceptionBranchError, match="re-cap only"):
        _parse([
            {
                "branch_id": "B", "max_supplied_items": 60,
                "overrides": {
                    f"knowledge_stores.{STORE}.candidate_supply.perception.max_candidates": 3
                },
            },
            _t(), _a(),
        ])


def test_release_swap_axis():
    group = _parse(
        [
            {
                "branch_id": "B", "max_supplied_items": 60,
                "release_swap": {
                    "store_id": STORE,
                    "release": f"knowledge/{STORE}/w4-release.json",
                },
            },
            _t(), _a(),
        ],
        declared_alternate_relpaths={STORE: (f"knowledge/{STORE}/w4-release.json",)},
    )
    assert group.branch("B").release_swap == SupplyVariantReleaseSwap(
        store_id=STORE, release_relpath=f"knowledge/{STORE}/w4-release.json",
    )


def test_presentation_axis_registered_check():
    with pytest.raises(PerceptionBranchError, match="not registered"):
        _parse(
            [
                {"branch_id": "B", "max_supplied_items": 60, "presentation_id": "not-a-real-one"},
                _t(), _a(),
            ],
            registered_presentation_ids=("top2-contrast-v1", "rank-visible-v1"),
        )
    group = _parse(
        [
            {"branch_id": "B", "max_supplied_items": 60, "presentation_id": "top2-contrast-v1"},
            _t(), _a(),
        ],
        registered_presentation_ids=("top2-contrast-v1", "rank-visible-v1"),
    )
    assert group.branch("B").presentation_id == "top2-contrast-v1"


def test_min_candidates_axis_bounded():
    with pytest.raises(PerceptionBranchError, match="exceeds"):
        _parse(
            [{"branch_id": "B", "max_supplied_items": 60, "min_candidates": 5}, _t(), _a()],
            max_candidates_ceiling=3,
        )
    group = _parse(
        [{"branch_id": "B", "max_supplied_items": 60, "min_candidates": 3}, _t(), _a()],
        max_candidates_ceiling=3,
    )
    assert group.branch("B").min_candidates == 3


def test_one_factor_per_non_a_branch():
    with pytest.raises(PerceptionBranchError, match="one factor"):
        _parse(
            [
                {
                    "branch_id": "B", "max_supplied_items": 60,
                    "overrides": {f"knowledge_stores.{STORE}.phase_supply.perception.k": 8},
                    "min_candidates": 3,
                },
                _t(), _a(),
            ],
            max_candidates_ceiling=3,
        )
    with pytest.raises(PerceptionBranchError, match="one factor"):
        _parse([{"branch_id": "B", "max_supplied_items": 60}, _t(), _a()])


def test_a_must_be_last_and_override_free():
    with pytest.raises(PerceptionBranchError, match="LAST branch"):
        _parse([_a(), _t(), _b_knob()])
    with pytest.raises(PerceptionBranchError, match="no axis"):
        _parse([
            _b_knob(), _t(),
            {
                **_a(),
                "overrides": {f"knowledge_stores.{STORE}.phase_supply.perception.k": 8},
            },
        ])


def test_exactly_one_twin_required():
    with pytest.raises(PerceptionBranchError, match="exactly one twin"):
        _parse([_b_knob(), _a()])
    with pytest.raises(PerceptionBranchError, match="exactly one twin"):
        _parse([_t(), _t(branch_id="T2"), _a()])


def test_twin_carries_no_axis():
    with pytest.raises(PerceptionBranchError, match="no axis"):
        _parse([
            {
                **_t(), "overrides": {f"knowledge_stores.{STORE}.phase_supply.perception.k": 8},
            },
            _a(),
        ])


def test_max_branches_upper_bound():
    def bk(i):
        return _b_knob(branch_id=f"B{i}", value=60 + i)

    ok = [bk(i) for i in range(6)] + [_t(), _a()]
    group = _parse(ok)
    assert len(group.branches) == MAX_PERCEPTION_BRANCHES

    over = [bk(i) for i in range(7)] + [_t(), _a()]
    with pytest.raises(PerceptionBranchError, match="between"):
        _parse(over)


def test_duplicate_axis_signature_refused():
    with pytest.raises(PerceptionBranchError, match="same axis"):
        _parse([
            _b_knob("B1", value=60), _b_knob("B2", value=60), _t(), _a(),
        ])


def test_fit_refusal():
    tight_fit = {**FIT_ESTIMATE, "base_prompt_tokens": 24000}
    with pytest.raises(PerceptionBranchError, match="exceeds"):
        _parse([_b_knob(), _t(), _a()], fit_estimate=tight_fit)


def test_ceiling_formula_level1_and_level2():
    assert perception_branch_ceiling(
        base_ceiling=11, branch_count=3, level=PERCEPTION_BRANCH_LEVEL_NOTE
    ) == 13
    assert perception_branch_ceiling(
        base_ceiling=11, branch_count=3, level=PERCEPTION_BRANCH_LEVEL_SOLVER
    ) == 15


def test_branch_record_and_receipt_level1():
    group = _parse([_b_knob(), _t(), _a()])
    records = [
        perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"c{index}",
            request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
            note_parse_status="ok", candidate_intent_ids=("intent_a", "intent_b"),
            supplied_value_ids=("v1", "v2"),
        )
        for index, branch in enumerate(group.branches)
    ]
    receipt = perception_branch_receipt(group=group, phase_id="perception", records=records)
    assert receipt["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA
    assert receipt["level"] == 1
    assert receipt["branch_visits"] == "first"
    assert receipt["visit_index"] == 0
    assert len(receipt["branches"]) == 3
    assert "solver_contact_id" not in receipt["branches"][0]


def test_branch_record_level2_fields_all_or_nothing():
    group = _parse([_b_knob(), _t(), _a()], level=2)
    branch = group.branch("B")
    with pytest.raises(PerceptionBranchError, match="all four"):
        perception_branch_record(
            branch=branch, branch_index=0, contact_id="c0",
            request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
            note_parse_status="ok", candidate_intent_ids=("intent_a",),
            supplied_value_ids=("v1",), solver_contact_id="sc0",
        )
    record = perception_branch_record(
        branch=branch, branch_index=0, contact_id="c0",
        request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
        note_parse_status="ok", candidate_intent_ids=("intent_a",),
        supplied_value_ids=("v1",),
        solver_contact_id="sc0", solver_request_sha256=SHA,
        solver_response_text_sha256=SHA, candidate_supply_value_ids=("v1",),
    )
    assert record["solver_contact_id"] == "sc0"
    assert record["candidate_supply_value_ids"] == ["v1"]
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_perception_branch_receipt,
)


def _sealed_receipt(group, level=1):
    records = []
    for index, branch in enumerate(group.branches):
        kwargs = dict(
            branch=branch, branch_index=index, contact_id=f"c{index}",
            request_sha256=(SHA if branch.deliver or branch.is_twin else "b" * 64),
            response_text_sha256="c" * 64, note_sha256="d" * 64,
            note_parse_status="ok", candidate_intent_ids=("intent_a", "intent_b"),
            supplied_value_ids=("v1", "v2"),
        )
        if level == 2:
            kwargs.update(
                solver_contact_id=f"sc{index}", solver_request_sha256="e" * 64,
                solver_response_text_sha256="f" * 64,
                candidate_supply_value_ids=("v1", "v2"),
            )
        records.append(perception_branch_record(**kwargs))
    return perception_branch_receipt(group=group, phase_id="perception", records=records)


def test_receipt_validator_accepts_a_sealed_level1_group():
    group = _parse([_b_knob(), _t(), _a()])
    receipt = _sealed_receipt(group, level=1)
    validate_perception_branch_receipt(
        receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
        twin_branch_id="T", phase_id="perception", level=1,
    )


def test_receipt_validator_accepts_a_sealed_level2_group():
    group = _parse([_b_knob(), _t(), _a()], level=2)
    receipt = _sealed_receipt(group, level=2)
    validate_perception_branch_receipt(
        receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
        twin_branch_id="T", phase_id="perception", level=2,
    )


def test_receipt_validator_refuses_wrong_level():
    group = _parse([_b_knob(), _t(), _a()], level=1)
    receipt = _sealed_receipt(group, level=1)
    with pytest.raises(ValueError, match="another level"):
        validate_perception_branch_receipt(
            receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
            twin_branch_id="T", phase_id="perception", level=2,
        )


def test_receipt_validator_accepts_a_twin_whose_request_sha256_differs_from_as():
    """A twin's ``request_sha256`` legitimately differs from the delivering
    branch's: both hash the WHOLE realised request, including the one
    history turn that names each contact's OWN identity (``request_id``),
    so two REAL, distinct contacts can never share one -- the same reason
    phase 1's own AT2 test compares specific wire-payload fields rather
    than a full-request digest between an arm and its twin. AT-P2 ("T's
    wire bytes equal A's") is a structural guarantee of
    ``rails.runner.perception_branch_messages`` itself (the twin takes
    ``base_messages(ctx)`` unchanged), not something re-checked here
    through digest equality -- ``tests/unit/test_perception_branch_live.py``
    proves it live. This receipt-level check is the supply-level proxy:
    the twin's ``supplied_value_ids`` must equal the delivering branch's
    exactly (checked below)."""

    group = _parse([_b_knob(), _t(), _a()])
    records = []
    for index, branch in enumerate(group.branches):
        request_sha = SHA if branch.deliver else "9" * 64
        records.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"c{index}",
            request_sha256=request_sha, response_text_sha256="c" * 64,
            note_sha256="d" * 64, note_parse_status="ok",
            candidate_intent_ids=("intent_a",), supplied_value_ids=("v1",),
        ))
    receipt = perception_branch_receipt(group=group, phase_id="perception", records=records)
    validate_perception_branch_receipt(
        receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
        twin_branch_id="T", phase_id="perception", level=1,
    )


def test_receipt_validator_refuses_twin_supplied_ids_mismatch():
    """The invariant AT-P2 actually reduces to at the receipt level: the
    twin must resolve EXACTLY the delivering branch's own supplied ids."""

    group = _parse([_b_knob(), _t(), _a()])
    records = []
    for index, branch in enumerate(group.branches):
        supplied = ("v1",) if branch.branch_id != "T" else ("v2",)
        records.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"c{index}",
            request_sha256=SHA, response_text_sha256="c" * 64,
            note_sha256="d" * 64, note_parse_status="ok",
            candidate_intent_ids=("intent_a",), supplied_value_ids=supplied,
        ))
    receipt = perception_branch_receipt(group=group, phase_id="perception", records=records)
    with pytest.raises(ValueError, match="does not resolve exactly the delivering"):
        validate_perception_branch_receipt(
            receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
            twin_branch_id="T", phase_id="perception", level=1,
        )


def test_receipt_validator_refuses_b_branch_with_no_axis_field():
    group = _parse([_b_knob(), _t(), _a()])
    receipt = _sealed_receipt(group, level=1)
    receipt["branches"][0]["min_candidates"] = None
    receipt["branches"][0]["resolved_knobs"] = []
    with pytest.raises(ValueError, match="exactly one axis"):
        validate_perception_branch_receipt(
            receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
            twin_branch_id="T", phase_id="perception", level=1,
        )


def test_receipt_validator_refuses_missing_branch_visits():
    group = _parse([_b_knob(), _t(), _a()])
    receipt = _sealed_receipt(group, level=1)
    receipt["branch_visits"] = "every"
    with pytest.raises(ValueError, match="branch_visits"):
        validate_perception_branch_receipt(
            receipt, branch_ids=group.branch_ids, delivered_branch_id="A",
            twin_branch_id="T", phase_id="perception", level=1,
        )


# ---------------------------------------------------------------------------
# prepared_seed (design section 5; the branch-seed-unpinned gate finding,
# scripts/checks/flight_registration_check.py).
# ---------------------------------------------------------------------------

PREPARED_SEED = {
    "relpath": "prepared/SAEA-SLURP-PERCEPTION-BRANCH-B-SEED-V1/seed.json",
    "sha256": "b" * 64,
}


def _b_knob_with_seed(prepared_seed=None):
    row = _b_knob()
    row["prepared_seed"] = prepared_seed if prepared_seed is not None else dict(PREPARED_SEED)
    return row


def test_a_b_branch_parses_its_own_pinned_prepared_seed():
    group = _parse([_b_knob_with_seed(), _t(), _a()])
    branch = group.branch("B")
    assert branch.prepared_seed == PREPARED_SEED
    assert branch.as_json()["prepared_seed"] == PREPARED_SEED


def test_a_and_t_may_not_carry_a_prepared_seed():
    a_row = _a()
    a_row["prepared_seed"] = dict(PREPARED_SEED)
    with pytest.raises(PerceptionBranchError, match="A or its twin"):
        _parse([_b_knob(), _t(), a_row])
    t_row = _t()
    t_row["prepared_seed"] = dict(PREPARED_SEED)
    with pytest.raises(PerceptionBranchError, match="A or its twin"):
        _parse([_b_knob(), t_row, _a()])


@pytest.mark.parametrize("mutate", [
    lambda seed: {**seed, "sha256": "not-hex"},
    lambda seed: {**seed, "sha256": "b" * 63},
    lambda seed: {**seed, "relpath": ""},
    lambda seed: {"relpath": seed["relpath"]},
    lambda seed: {**seed, "extra": "field"},
])
def test_a_malformed_prepared_seed_is_refused(mutate):
    with pytest.raises(PerceptionBranchError, match="prepared_seed"):
        _parse([_b_knob_with_seed(mutate(PREPARED_SEED)), _t(), _a()])


def test_prepared_seed_defaults_to_none_when_absent():
    group = _parse([_b_knob(), _t(), _a()])
    assert group.branch("B").prepared_seed is None
    assert group.branch("A").prepared_seed is None
    assert group.branch("T").prepared_seed is None
