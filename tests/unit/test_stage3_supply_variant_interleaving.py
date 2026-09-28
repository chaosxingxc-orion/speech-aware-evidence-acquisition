"""Item E42 (Stage-3 family VAR-2): per-row supply-variant interleaving.

Cell ROLL-AA measured the locked v2.0 plan against itself INSIDE one flight and
found ``h_within`` = 0.735 pp SLU / 0.000 pp intent at n = 200, against about
1.25 pp for the same identity flown as two campaigns
(``docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md``).
This module is the offline proof of the harness capability that argues for:
K declared knowledge-supply constructions at ONE node, inside ONE episode of
ONE campaign, paired per row, with exactly one of them delivered.

Four layers, all model-free:

1. **The rail** -- every refusal ``rails.supply_variants.parse_supply_variants``
   makes, and the pure ordered-id arithmetic a non-delivering arm renders with.
2. **The configuration** -- the arm group on the real derived VAR-2 fragment,
   the ceiling arithmetic (``1 + (1+1)*(1*1*4 + 3 + 1) = 17``), and the
   refusals the loader adds on top of the rail's.
3. **The custody** -- ``rails.native_episode_receipt.
   validate_supply_variant_receipt`` on a well-formed receipt and on every way
   of malforming it.
4. **The live wiring** -- the whole mechanism through the SAME
   ``_ActualEpisodeHarness`` fake transport the grouped-sampler proof uses:
   K real contacts, K arm-scoped requests, ONE contact batch, ONE registered
   Solver state, and the delivering arm's own text delivered.

Plus the byte-identity statement this change owes every existing form: the
VAR1-PLAN and v2.0-lock fragments compose to exactly the roles and ceilings
they composed before, and a contact that binds no arm carries no arm key in its
role custody document.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    NativeEpisodeRole,
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    SUPPLY_VARIANT_RECEIPT_SCHEMA,
    validate_supply_variant_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    MAX_SUPPLY_VARIANT_ARMS,
    SupplyVariantError,
    arm_supplied_value_ids,
    parse_supply_variants,
    supply_variant_arm_record,
    supply_variant_receipt,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    NativeRoleContactContext,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
VAR2_FRAGMENT = "slurp-native-stage3-var2-supply-variants-r01c-baseline-v1.json"
VAR1_PLAN_FRAGMENT = "slurp-native-stage3-var1-plan-r01c-baseline-v1.json"
PLAN_LOCK_FRAGMENT = "slurp-native-default-plan-lock-baseline-v1.json"

EX = "knowledge_stores.train-exemplars.phase_supply.solver"
SC = "knowledge_stores.slot-contracts.candidate_supply.solver"
FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 640,
    "base_prompt_tokens": 9600,
    "tokens_per_supplied_item": 120,
}


def _fragment(name):
    values = json.loads((BASELINE_DIR / name).read_text(encoding="utf-8"))
    # ``carrier_lock_key`` is produced by the runtime at prepare time, not
    # declared by a baseline fragment; the loader reads it for the
    # delivery-normaliser carrier check.
    values["carrier_lock_key"] = "slurp"
    return values


def _block(**overrides):
    block = {
        "arms": [
            {
                "arm_id": "exk10",
                "max_supplied_items": 38,
                "overrides": {f"{EX}.k": 10},
            },
            {"arm_id": "plan", "deliver": True, "max_supplied_items": 48},
        ],
        "fit_estimate": dict(FIT),
    }
    block.update(overrides)
    return block


def _parse(block=None, **kwargs):
    options = {
        "phase_id": "solver",
        "first_phase_id": "perception",
        "declared_stores": ("train-exemplars", "slot-contracts", "intent-boundaries"),
    }
    options.update(kwargs)
    return parse_supply_variants(block if block is not None else _block(), **options)


# ---------------------------------------------------------------------------
# 1. The rail
# ---------------------------------------------------------------------------


def test_a_well_formed_group_parses_to_its_declared_order():
    group = _parse()
    assert group.arm_ids == ("exk10", "plan")
    assert group.arm_count == 2
    assert group.delivered_arm.arm_id == "plan"
    assert group.arm("exk10").knobs[0].store_id == "train-exemplars"
    assert group.arm("exk10").knobs[0].route == "phase_supply"
    assert group.arm("exk10").knobs[0].tail == ("k",)
    assert group.arm("exk10").knobs[0].value == 10
    assert group.arm_at(1).deliver is True


def test_the_fit_estimate_uses_the_registered_reserve_arithmetic():
    group = _parse()
    fit = group.fit_estimate
    # 24,576-token live slot, one-eighth reserve capped at the registered
    # 8,192 (item E33): 24,576 // 8 = 3,072.
    assert fit.reserve_tokens == 3072
    assert fit.prompt_limit_tokens == 24576 - 3072 - 640 - 2
    assert fit.estimated_prompt_tokens(group.arm("exk10")) == 9600 + 38 * 120


@pytest.mark.parametrize(
    "mutate,expected",
    [
        pytest.param(
            lambda b: b["arms"][1].__setitem__("deliver", False),
            "exactly one arm with deliver",
            id="zero-delivering-arms",
        ),
        pytest.param(
            lambda b: b["arms"][0].__setitem__("deliver", True),
            "exactly one arm with deliver",
            id="two-delivering-arms",
        ),
        pytest.param(
            lambda b: b["arms"].insert(0, copy.deepcopy(b["arms"][0])),
            "arm ids must be distinct",
            id="arm-id-collision",
        ),
        pytest.param(
            lambda b: b["arms"].reverse(),
            "must be the LAST arm",
            id="delivering-arm-not-last",
        ),
        pytest.param(
            lambda b: b["arms"][1].__setitem__("overrides", {f"{EX}.k": 9}),
            "must declare no overrides",
            id="delivering-arm-carries-overrides",
        ),
        pytest.param(
            lambda b: b["arms"][0]["overrides"].__setitem__(f"{EX}.tau", 1),
            "does not admit",
            id="unknown-knob",
        ),
        pytest.param(
            lambda b: b["arms"][0]["overrides"].__setitem__(
                "knowledge_stores.train-exemplars.release.solver.sha256", 1
            ),
            "may re-cap only",
            id="unknown-route",
        ),
        pytest.param(
            lambda b: b["arms"][0]["overrides"].__setitem__(
                "knowledge_stores.train-exemplars.release.sha256", 1
            ),
            "is not a knob path",
            id="too-short-to-be-a-knob-path",
        ),
        pytest.param(
            lambda b: b["arms"][0]["overrides"].__setitem__(
                "decoding_params.temperature", 1
            ),
            "is not a knob path",
            id="outside-the-knob-root",
        ),
        pytest.param(
            lambda b: b["arms"][0]["overrides"].__setitem__(
                "knowledge_stores.intent-boundaries.phase_supply.perception.k", 16
            ),
            "FIRST phase",
            id="first-phase-knob",
        ),
        pytest.param(
            lambda b: b["arms"][0]["overrides"].__setitem__(
                "knowledge_stores.train-exemplars.phase_supply.reviewer.k", 4
            ),
            "may only re-cap the supply of its own node",
            id="another-nodes-phase",
        ),
        pytest.param(
            lambda b: b["arms"][0]["overrides"].__setitem__(
                "knowledge_stores.absent-store.phase_supply.solver.k", 4
            ),
            "does not declare",
            id="undeclared-store",
        ),
        pytest.param(
            lambda b: b["arms"][0].__setitem__("max_supplied_items", 500),
            "exceeds the",
            id="prompt-fit-estimate-over-the-slot",
        ),
        pytest.param(
            lambda b: b.pop("fit_estimate"),
            "must be an object with exactly",
            id="missing-fit-estimate",
        ),
        pytest.param(
            lambda b: b["arms"].__setitem__(0, {"arm_id": "x"}),
            "must carry exactly",
            id="arm-row-missing-keys",
        ),
        pytest.param(
            lambda b: b["arms"].__setitem__(0, dict(b["arms"][0], colour="red")),
            "must carry exactly",
            id="arm-row-unknown-key",
        ),
        pytest.param(
            lambda b: b["arms"].pop(0),
            "between 2 and",
            id="single-arm-group",
        ),
        pytest.param(
            lambda b: b["arms"][0]["overrides"].__setitem__(f"{EX}.k", 0),
            "must be a positive integer",
            id="non-positive-knob-value",
        ),
        pytest.param(
            lambda b: b["arms"].insert(
                0, {"arm_id": "twin", "max_supplied_items": 38,
                    "overrides": {f"{EX}.k": 10}}
            ),
            "same overrides",
            id="two-arms-one-construction",
        ),
    ],
)
def test_every_declared_refusal_is_raised_by_name(mutate, expected):
    block = _block()
    mutate(block)
    with pytest.raises(SupplyVariantError, match=expected):
        _parse(block)


def test_an_arm_group_larger_than_the_registered_bound_is_refused():
    block = _block()
    block["arms"] = [
        {"arm_id": f"a{index}", "max_supplied_items": 38,
         "overrides": {f"{EX}.k": index + 2}}
        for index in range(MAX_SUPPLY_VARIANT_ARMS)
    ] + [{"arm_id": "plan", "deliver": True, "max_supplied_items": 48}]
    with pytest.raises(SupplyVariantError, match="between 2 and"):
        _parse(block)


def test_a_non_delivering_arm_keeps_the_prefix_and_replaces_this_nodes_own_ids():
    # The row's accumulated state: two values an earlier phase supplied, then
    # three this node's own supply step acquired.
    accumulated = ("b::1", "b::2", "x::7", "x::8", "x::9")
    assert arm_supplied_value_ids(
        retrieved_value_ids=accumulated,
        node_acquired_value_ids=("x::7", "x::8", "x::9"),
        arm_selected_value_ids=("x::4",),
    ) == ("b::1", "b::2", "x::4")
    # A REVISE revisit: the node's cumulative contribution is the same set, so
    # the arm renders exactly what it rendered on the first visit.
    assert arm_supplied_value_ids(
        retrieved_value_ids=accumulated,
        node_acquired_value_ids=("x::9", "x::7", "x::8"),
        arm_selected_value_ids=("x::4",),
    ) == ("b::1", "b::2", "x::4")


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (
            {
                "retrieved_value_ids": ("b::1",),
                "node_acquired_value_ids": ("x::7",),
                "arm_selected_value_ids": (),
            },
            "cannot locate",
        ),
        (
            {
                "retrieved_value_ids": ("b::1", "x::7"),
                "node_acquired_value_ids": ("x::7",),
                "arm_selected_value_ids": ("x::4", "x::4"),
            },
            "must be unique",
        ),
        (
            {
                "retrieved_value_ids": ("b::1", "x::7"),
                "node_acquired_value_ids": ("x::7",),
                "arm_selected_value_ids": ("b::1",),
            },
            "re-supplies value",
        ),
    ],
)
def test_the_arm_id_arithmetic_refuses_an_unlocatable_or_overlapping_selection(
    kwargs, expected,
):
    with pytest.raises(SupplyVariantError, match=expected):
        arm_supplied_value_ids(**kwargs)


def test_an_arm_record_refuses_more_items_than_its_declared_bound():
    group = _parse()
    arm = group.arm("exk10")
    with pytest.raises(SupplyVariantError, match="max_supplied_items"):
        supply_variant_arm_record(
            arm=arm, arm_index=0, contact_id="c1",
            supplied_value_ids=tuple(f"x::{i}" for i in range(arm.max_supplied_items + 1)),
        )


def test_an_arm_record_refuses_resolved_knobs_it_did_not_declare():
    group = _parse()
    with pytest.raises(SupplyVariantError, match="differ from the knobs it declared"):
        supply_variant_arm_record(
            arm=group.arm("exk10"), arm_index=0, contact_id="c1",
            supplied_value_ids=("x::1",), resolved_knobs={f"{EX}.k": 10, f"{SC}.max_candidates": 4},
        )


# ---------------------------------------------------------------------------
# 2. The configuration and the ceiling
# ---------------------------------------------------------------------------


def test_the_derived_var2_fragment_composes_to_the_registered_ceiling():
    values = _fragment(VAR2_FRAGMENT)
    assert values["policy"] == "phase-native-candidates-review-revise-variants4-v1"
    program = default_phase_program(values["policy"])
    assert program.max_contacts == 17
    config = load_native_episode_config(values, program)
    # 1 Perception + (1 revision + 1) * (Solver 1 * 1 sample * 4 arms
    # + Reviewer 3 + Planner 1) = 1 + 2 * 8 = 17.
    assert config.max_contacts == 17
    assert config.supply_variant_arm_count == 4
    assert config.supply_variant_phase_id == "solver"
    group = config.supply_variant_group
    assert group.arm_ids == ("exk10", "exk30", "exdiv", "plan")
    assert group.delivered_arm.arm_id == "plan"
    assert group.delivered_arm.knobs == ()
    # Each variant differs from the delivering construction in its OWN declared
    # knobs and in nothing else.
    assert {knob.path for knob in group.arm("exdiv").knobs} == {
        f"{EX}.fuse_coverage.c"
    }
    assert {knob.value for knob in group.arm("exk30").knobs} == {30}


def test_the_four_arm_group_on_the_eleven_contact_plan_program_is_refused():
    values = _fragment(VAR2_FRAGMENT)
    values["policy"] = "phase-native-candidates-review-revise-v1"
    with pytest.raises(ValueError, match="contact ceiling"):
        load_native_episode_config(values, default_phase_program(values["policy"]))


@pytest.mark.parametrize(
    "mutate,expected",
    [
        pytest.param(
            lambda role: role.update(
                samples=2,
                decoding_overrides={"temperature": 0.7, "seed_offset": 0},
                commit={
                    "policy": "saea-commit-plurality-support-v1",
                    "min_support": 2,
                    "similarity_threshold": 0.8,
                },
            ),
            "cannot combine with a grouped Solver visit",
            id="beside-grouped-sampling",
        ),
        pytest.param(
            lambda role: role.update(max_iterations=2),
            "requires roles.solver.max_iterations 1",
            id="multi-iteration-node",
        ),
    ],
)
def test_the_loader_refuses_a_group_the_arm_to_contact_mapping_cannot_carry(
    mutate, expected,
):
    values = _fragment(VAR2_FRAGMENT)
    mutate(values["native_episode"]["roles"]["solver"])
    with pytest.raises(ValueError, match=expected):
        load_native_episode_config(values, default_phase_program(values["policy"]))


def test_a_group_beside_an_armed_knowledge_index_is_refused():
    values = _fragment(VAR2_FRAGMENT)
    values["native_episode"]["knowledge_index"] = {"view": "slurp-knowledge-index-v1"}
    with pytest.raises(ValueError, match="knowledge_index"):
        load_native_episode_config(values, default_phase_program(values["policy"]))


def test_only_the_solver_role_may_declare_an_arm_group():
    group = _parse()
    with pytest.raises(ValueError, match="only the Solver role"):
        NativeEpisodeRole(
            phase_id="reviewer", role_kind="reviewer", max_iterations=1,
            tool_names=(), supply_variants=group,
        )


def test_a_group_beside_role_tool_authority_is_refused():
    group = _parse()
    with pytest.raises(ValueError, match="tool authority"):
        NativeEpisodeRole(
            phase_id="solver", role_kind="solver", max_iterations=1,
            tool_names=("someTool",), supply_variants=group,
        )


def test_the_acquisition_role_carries_no_arm_group():
    group = _parse()
    with pytest.raises(ValueError, match="no role knobs"):
        NativeEpisodeRole(
            phase_id="acquisition", role_kind="acquisition", max_iterations=0,
            tool_names=(), acquisition_kinds=("knowledge-requery",),
            supply_variants=group,
        )


# ---------------------------------------------------------------------------
# 3. No existing episode form's bytes move
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected_ceiling",
    [(VAR1_PLAN_FRAGMENT, 11), (PLAN_LOCK_FRAGMENT, 11)],
)
def test_an_existing_form_composes_exactly_the_config_it_always_did(
    name, expected_ceiling,
):
    values = _fragment(name)
    program = default_phase_program(values["policy"])
    config = load_native_episode_config(values, program)
    assert config.max_contacts == expected_ceiling == program.max_contacts
    # The arm seam is UNREACHABLE for this form: no group, arm count 1, no
    # variant phase. The ceiling formula's new factor is therefore exactly 1
    # and the composed ceiling is the pre-E42 one.
    assert config.supply_variant_group is None
    assert config.supply_variant_arm_count == 1
    assert config.supply_variant_phase_id is None
    for role in config.roles:
        assert role.supply_variants is None


def test_the_composed_role_graph_of_the_locked_plan_is_hash_stable():
    """A pinned digest of the composed role graph of the v2.0 lock.

    Not decoration: it is the one assertion that fails if a future edit to
    ``NativeEpisodeRole`` changes what an EXISTING fragment composes to, which
    is precisely what item E42 must not do.
    """

    values = _fragment(PLAN_LOCK_FRAGMENT)
    config = load_native_episode_config(
        values, default_phase_program(values["policy"])
    )
    document = [
        {
            "phase_id": role.phase_id,
            "role_kind": role.role_kind,
            "max_iterations": role.max_iterations,
            "tool_names": list(role.tool_names),
            "history_scope": role.history_scope,
            "samples": role.samples,
            "decoding_overrides": role.decoding_overrides,
            "commit": role.commit,
            "twin": role.twin,
            "acquisition_kinds": list(role.acquisition_kinds),
            "max_completion_tokens": role.max_completion_tokens,
            "supply_variants": None if role.supply_variants is None else "declared",
        }
        for role in config.roles
    ]
    digest = hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert document == [
        {
            "phase_id": "perception", "role_kind": "perception", "max_iterations": 1,
            "tool_names": [], "history_scope": "full", "samples": 1,
            "decoding_overrides": None, "commit": None, "twin": None,
            "acquisition_kinds": [], "max_completion_tokens": None,
            "supply_variants": None,
        },
        {
            "phase_id": "solver", "role_kind": "solver", "max_iterations": 1,
            "tool_names": [], "history_scope": "full", "samples": 1,
            "decoding_overrides": None, "commit": None, "twin": None,
            "acquisition_kinds": [], "max_completion_tokens": None,
            "supply_variants": None,
        },
        {
            "phase_id": "reviewer", "role_kind": "reviewer", "max_iterations": 3,
            "tool_names": [], "history_scope": "full", "samples": 1,
            "decoding_overrides": None, "commit": None, "twin": None,
            "acquisition_kinds": [], "max_completion_tokens": None,
            "supply_variants": None,
        },
        {
            "phase_id": "planner", "role_kind": "planner", "max_iterations": 1,
            "tool_names": [], "history_scope": "full", "samples": 1,
            "decoding_overrides": None, "commit": None, "twin": None,
            "acquisition_kinds": [], "max_completion_tokens": None,
            "supply_variants": None,
        },
    ]
    assert len(digest) == 64


def test_a_contact_that_binds_no_arm_carries_no_arm_key():
    """Item E42's role-custody key is CONDITIONAL, so every contact of every
    episode form written before it keeps its ``role_request_bytes`` byte for
    byte."""

    plain = NativeRoleContactContext(sample_id="s1", agent_contact_id="c1")
    assert plain.variant_arm_id is None
    armed = NativeRoleContactContext(
        sample_id="s1", agent_contact_id="c1", variant_arm_id="exk10",
    )
    assert armed.variant_arm_id == "exk10"
    with pytest.raises(ValueError, match="variant_arm_id"):
        NativeRoleContactContext(sample_id="s1", agent_contact_id="c1", variant_arm_id="")


# ---------------------------------------------------------------------------
# 4. The receipt validator
# ---------------------------------------------------------------------------


def _receipt(group=None):
    group = group or _parse()
    records = [
        supply_variant_arm_record(
            arm=group.arm("exk10"), arm_index=0, contact_id="c0",
            supplied_value_ids=("b::1", "x::4"),
        ),
        supply_variant_arm_record(
            arm=group.arm("plan"), arm_index=1, contact_id="c1",
            supplied_value_ids=("b::1", "x::7", "x::8"),
        ),
    ]
    return supply_variant_receipt(group=group, phase_id="solver", records=records)


def _validate(receipt, **kwargs):
    group = _parse()
    options = {
        "arm_ids": group.arm_ids,
        "delivered_arm_id": group.delivered_arm.arm_id,
        "phase_id": "solver",
    }
    options.update(kwargs)
    validate_supply_variant_receipt(receipt, **options)


def test_a_well_formed_receipt_validates():
    receipt = _receipt()
    assert receipt["schema"] == SUPPLY_VARIANT_RECEIPT_SCHEMA
    assert receipt["arm_count"] == 2
    assert receipt["delivered_arm_id"] == "plan"
    assert [row["arm_id"] for row in receipt["arms"]] == ["exk10", "plan"]
    _validate(receipt)
    # The delivering arm's ids open the row's own accumulated state.
    _validate(receipt, retrieved_value_ids=("b::1", "x::7", "x::8", "later::1"))


@pytest.mark.parametrize(
    "mutate,expected",
    [
        pytest.param(
            lambda r: r.__setitem__("schema", "something-else"),
            "unregistered schema",
            id="wrong-schema",
        ),
        pytest.param(
            lambda r: r.__setitem__("phase_id", "reviewer"),
            "names another phase",
            id="wrong-phase",
        ),
        pytest.param(
            lambda r: r.__setitem__("arm_count", 3),
            "every declared arm",
            id="wrong-arm-count",
        ),
        pytest.param(
            lambda r: r.__setitem__("delivered_arm_id", "exk10"),
            "another delivering arm",
            id="wrong-delivered-arm",
        ),
        pytest.param(
            lambda r: r["arms"].pop(0),
            "every declared arm",
            id="missing-arm",
        ),
        pytest.param(
            lambda r: r["arms"].reverse(),
            "ascending arm_index",
            id="arms-physically-reversed",
        ),
        pytest.param(
            lambda r: (
                r["arms"][0].__setitem__("arm_id", "plan"),
                r["arms"][1].__setitem__("arm_id", "exk10"),
            ),
            "declared order",
            id="arm-ids-swapped-under-correct-indices",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__("arm_index", 5),
            "ascending arm_index",
            id="wrong-arm-index",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__("deliver", True),
            "declared delivering arm",
            id="two-delivering-rows",
        ),
        pytest.param(
            lambda r: r["arms"][1].__setitem__(
                "resolved_knobs", [{"path": f"{EX}.k", "value": 4}]
            ),
            "must resolve no knobs",
            id="delivering-row-resolves-knobs",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__("resolved_knobs", []),
            "at least one",
            id="variant-row-resolves-nothing",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__(
                "resolved_knobs", {f"{EX}.k": 10}
            ),
            "ordered sequence",
            id="resolved-knobs-as-a-dotted-mapping",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__(
                "resolved_knobs", [{"path": f"{EX}.k"}]
            ),
            "malformed resolved knobs",
            id="resolved-knob-missing-its-value",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__(
                "resolved_knobs",
                [
                    {"path": f"{EX}.k", "value": 10},
                    {"path": f"{EX}.fuse_coverage.c", "value": 4},
                ],
            ),
            "distinct and ordered by path",
            id="resolved-knobs-out-of-order",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__("supplied_item_count", 9),
            "disagrees with its ids",
            id="count-disagrees",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__("supplied_value_ids", ["x::4", "x::4"]),
            "must be unique",
            id="duplicate-ids",
        ),
        pytest.param(
            lambda r: r["arms"][0].__setitem__("max_supplied_items", 1),
            "more items than the bound",
            id="over-its-own-bound",
        ),
        pytest.param(
            lambda r: r["arms"][1].__setitem__("contact_id", "c0"),
            "distinct contact ids",
            id="shared-contact-id",
        ),
        pytest.param(
            lambda r: r.__setitem__("fit_estimate", {"slot_tokens": 1}),
            "fit estimate has an invalid shape",
            id="malformed-fit-estimate",
        ),
        pytest.param(
            lambda r: r.__setitem__("extra", 1),
            "invalid shape",
            id="unknown-receipt-key",
        ),
    ],
)
def test_the_receipt_validator_refuses_every_malformation(mutate, expected):
    receipt = _receipt()
    mutate(receipt)
    with pytest.raises(ValueError, match=expected):
        _validate(receipt)


def test_the_delivering_arms_ids_must_open_the_rows_own_state():
    receipt = _receipt()
    with pytest.raises(ValueError, match="ordered prefix"):
        _validate(receipt, retrieved_value_ids=("x::7", "b::1", "x::8"))


def test_a_receipt_whose_declared_delivering_arm_is_not_last_is_refused():
    receipt = _receipt()
    with pytest.raises(ValueError, match="last declared arm"):
        _validate(receipt, arm_ids=("plan", "exk10"), delivered_arm_id="plan")


# ---------------------------------------------------------------------------
# 5. The live wiring, through the shared fake transport
# ---------------------------------------------------------------------------

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

# Module-scoped autouse fixture spawning the fake llama-server-shaped process
# the transport dials; must be imported into this module's own namespace,
# exactly as every other runner proof in this suite does. Not called directly.
from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_native_episode_runner import (  # noqa: E402
    ACTIONS,
    PHASES,
    _ActualEpisodeHarness,
)

ARM_VALUE = "value:dim-light"


def _live_group():
    return parse_supply_variants(
        {
            "arms": [
                {
                    "arm_id": "wide",
                    "max_supplied_items": 4,
                    "overrides": {f"{EX}.k": 30},
                },
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 4},
            ],
            "fit_estimate": dict(FIT),
        },
        phase_id="solver",
        first_phase_id="perception",
        declared_stores=("train-exemplars",),
    )


def _live_config(*, group, max_contacts):
    """The review-off shape (Reviewer/Planner 0) with an arm-grouped Solver."""

    return NativeEpisodeConfig(
        episode_id="native-role-runner-proof-v1",
        max_revisions=0,
        actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase,
                role_kind=phase,
                max_iterations=0 if phase in {"reviewer", "planner"} else 1,
                tool_names=(),
                supply_variants=(group if phase == "solver" else None),
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
    )


def _arm_resolver(selections):
    """The flight-owned per-arm resolver, as a deterministic double.

    The runner reads exactly one thing off what this returns --
    ``fusion_decision.selected_value_ids`` -- so a namespace with that attribute
    chain exercises the real seam without a store on disk.
    """

    def resolve(*, arm_id, phase_id, context):
        assert phase_id == "solver"
        ids = selections[arm_id]
        if ids is None:
            return None
        return SimpleNamespace(
            fusion_decision=SimpleNamespace(selected_value_ids=tuple(ids))
        )

    return resolve


def _arm_output(key):
    """One distinct answer per arm, indexed by the harness's within-visit turn."""

    sample_id, phase, visit, turn = key
    if phase == "solver":
        return f"solver-arm-{turn}:{sample_id}"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_two_arm_visit_spends_two_contacts_and_delivers_the_last_arms_own_text(
    tmp_path,
):
    group = _live_group()
    # Perception 1 + Solver 1 visit * 2 arms = 3.
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=3, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=3)
    harness.supply_variant_for_phase = _arm_resolver(
        {"wide": (ARM_VALUE,), "plan": ()}
    )
    harness._output = _arm_output
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    assert close_summary["request_count"] == 3
    result = summary.results[0]
    assert len(result.contacts) == 3

    # The custody: one row per declared arm, in declared order, each bound to
    # its own contact, with the WIDE arm carrying the value its own route
    # selected and the delivering arm carrying the row's own state (empty here,
    # because this harness binds no ordinary supply_for_phase at all).
    receipt = result.supply_variants
    assert receipt is not None
    assert receipt["schema"] == SUPPLY_VARIANT_RECEIPT_SCHEMA
    assert [row["arm_id"] for row in receipt["arms"]] == ["wide", "plan"]
    assert [row["deliver"] for row in receipt["arms"]] == [False, True]
    assert receipt["arms"][0]["supplied_value_ids"] == [ARM_VALUE]
    assert receipt["arms"][1]["supplied_value_ids"] == []
    assert receipt["arms"][0]["resolved_knobs"] == [
        {"path": f"{EX}.k", "value": 30}
    ]
    assert receipt["arms"][1]["resolved_knobs"] == []
    assert len({row["contact_id"] for row in receipt["arms"]}) == 2
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids,
        delivered_arm_id=group.delivered_arm.arm_id, phase_id="solver",
        retrieved_value_ids=result.final_query_state.retrieved_value_ids,
    )

    # The delivered text is the LAST (delivering) arm's own response -- no
    # aggregate, so invariant I7 needs no new exception.
    assert result.final_response_text == _arm_output(
        (result.sample_id, "solver", 1, 2)
    )

    # ONE Solver state per visit, exactly as a grouped visit registers one.
    episode_receipt = result.native_episode_receipt
    assert [visit["stage"] for visit in episode_receipt["role_visits"]] == [
        "perception", "solver",
    ]
    assert "supply_variants" not in episode_receipt
    solver_states = [
        state for state in result.agent_states if state.state_kind == "phase:solver"
    ]
    assert len(solver_states) == 1
    assert solver_states[0].content == result.final_response_text

    # ONE wave for the whole arm group, naming both contacts as alternatives of
    # one another -- exactly the shape a grouped Solver visit's samples take.
    waves = [wave.as_json() for wave in result.waves]
    assert [wave["fanout_semantics"] for wave in waves] == [
        "single", "action_alternatives",
    ]
    group_wave = waves[1]
    assert group_wave["batch_id"].endswith(":variants")
    assert len(group_wave["contact_plans"]) == 2
    assert len(group_wave["response_sha256s"]) == 2
    # All K arms bind the SAME QueryState: they are independent constructions of
    # one draft, not a chain.
    assert len({
        plan["query_state_sha256"] for plan in group_wave["contact_plans"]
    }) == 1
    assert group_wave["query_state_sha256"] == (
        group_wave["contact_plans"][0]["query_state_sha256"]
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_two_arms_requests_differ_only_in_their_supplied_evidence(tmp_path):
    """The claim the whole form rests on, read off the REALISED request bytes.

    Two arms of one visit, sealed as two ``MODEL_REQUEST`` payloads: the arm's
    own ``supplied_evidence`` differs, and the decoding params, the task
    instruction, the speech packet, the tool schemas and the rendered contract
    do not. Nothing an arm declares can reach any of those, and this is the
    byte-level statement of it.
    """

    group = _live_group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=3, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=3)
    harness.supply_variant_for_phase = _arm_resolver(
        {"wide": (ARM_VALUE,), "plan": ()}
    )
    harness._output = _arm_output
    try:
        harness.run()
    finally:
        harness.close()

    requests = [
        payload["payload"]
        for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    # Perception, then the two Solver arms in declared order.
    assert len(requests) == 3
    wide, plan = requests[1], requests[2]

    def evidence(request):
        return [
            (block["evidence_id"], block["knowledge_role"])
            for block in request["supplied_evidence"]
        ]

    # The ONE declared difference.
    assert evidence(wide) == [(ARM_VALUE, "value")]
    assert evidence(plan) == []
    assert [item["relpath"] for item in wide["evidence_provenance"]]
    assert plan["evidence_provenance"] == []

    # ...and nothing else. Every field an arm may NOT reach, compared byte for
    # byte between the two arms of one visit.
    for field in (
        "decoding_params", "task_instruction", "tool_schemas",
        "speech_feature_parts", "speech_packet_sha256", "query_source",
        "key_representation_id", "matcher_policy_id", "carrier_lock_key",
        "media_relpath", "audio_seconds", "sample_rate_hz", "sample_id",
    ):
        assert wide[field] == plan[field], field
    # The exposed history is the same length and the same states; only the
    # arm's own control turn (its own contact id) differs, as it does between
    # any two contacts of any episode.
    assert len(wide["history"]) == len(plan["history"])
    assert wide["history"][0] == plan["history"][0]
    assert wide["history"][-1]["role"] == plan["history"][-1]["role"] == "control"


# ---------------------------------------------------------------------------
# 5b. The W4-SV blocker fix: a release-swap arm renders from its OWN
#     alternate composite snapshot, contact for contact, through the same
#     ``_ActualEpisodeHarness`` fake transport the tests above use.
# ---------------------------------------------------------------------------


def _release_swap_live_group():
    """Arm order matches the real W4-SV cell: a release-swap arm, a twin, then
    the delivering arm (docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-
    v1/README.md, arm order ``b-w4``/``t-twin``/``a-agree``)."""

    return parse_supply_variants(
        {
            "arms": [
                {
                    "arm_id": "swap", "max_supplied_items": 4,
                    "release_swap": {
                        "store_id": "train-exemplars", "release": "alt.json",
                    },
                },
                {"arm_id": "aa", "replicate_of": "plan", "max_supplied_items": 4},
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 4},
            ],
            "fit_estimate": dict(FIT),
        },
        phase_id="solver",
        first_phase_id="perception",
        declared_stores=("train-exemplars",),
        declared_alternate_relpaths={"train-exemplars": ("alt.json",)},
    )


def _alt_knowledge_snapshot(*, value_id=None, content=None):
    """One alternate composite snapshot for the release-swap arm to render
    from. Default: the SAME value id ``_knowledge_snapshot()`` carries, with
    its content prefixed -- a content-only revision, exactly the W4-SV
    ``slot-contracts-w4-v1`` vs ``v2`` shape (same 54 ids, 19 differing in
    content) that made arm B a silent second twin before this fix."""

    from dataclasses import replace as _replace

    from test_rails_runner import _knowledge_snapshot

    base = _knowledge_snapshot()
    if value_id is None and content is None:
        values = tuple(
            _replace(value, content=f"ALTERNATE {value.content}")
            for value in base.values
        )
    else:
        values = (
            _replace(base.values[0], value_id=value_id or base.values[0].value_id,
                      content=content if content is not None else base.values[0].content),
        )
    return _replace(base, snapshot_id="fake-train-knowledge-alternate-v1", values=values).validate()


def _release_swap_resolver(selections, *, release_swap_snapshots):
    """``_arm_resolver`` plus the ``release_swap_snapshots`` attribute
    ``rails.runner.supply_variant_messages`` reads for a release-swap arm
    (``core.flight.runtime.FlightRuntime._supply_variant_binding``'s own
    contract with the resolver it returns)."""

    resolve = _arm_resolver(selections)
    resolve.release_swap_snapshots = release_swap_snapshots
    return resolve


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_release_swap_arms_request_renders_the_alternates_content(tmp_path):
    """The W4-SV blocker fix, proven at the byte level: a content-only
    alternate (the SAME value id, different content) changes the release-swap
    arm's (B's) rendered evidence text, while the twin (T) and the delivering
    arm (A) keep rendering from the base snapshot -- byte-identical to before
    this fix, exactly as AT2 (``test_at2_...``) already proves for a twin
    beside an ordinary knob-recapping arm."""

    group = _release_swap_live_group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=4)
    harness.supply_variant_for_phase = _release_swap_resolver(
        {"swap": (ARM_VALUE,), "aa": (), "plan": ()},
        release_swap_snapshots={"swap": _alt_knowledge_snapshot()},
    )
    harness._output = _arm_output
    try:
        harness.run()
    finally:
        harness.close()

    requests = [
        payload["payload"]
        for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    # Perception, then swap / aa (twin) / plan (delivering), in declared order.
    assert len(requests) == 4
    swap, twin, plan = requests[1], requests[2], requests[3]

    def value_texts(request):
        return [
            block["content"] for block in request["supplied_evidence"]
            if block["knowledge_role"] == "value"
        ]

    # The ONE thing a release swap may change: the CONTENT of a value id the
    # base snapshot also carries.
    assert value_texts(swap) == [
        "ALTERNATE Use the dim-light operation when brightness must decrease.",
    ]
    # Neither the twin nor the delivering arm ever sees the alternate: the
    # release swap is declared on "swap" alone, so their own resolution
    # (empty, in this harness) renders from the base snapshot exactly as it
    # did before this fix -- and the twin stays byte-for-byte the delivering
    # arm's own payload (AT2's own comparison: every field but the per-contact
    # ``request_id`` and its one "control" history turn, which differ between
    # ANY two contacts of any episode).
    assert value_texts(twin) == value_texts(plan) == []
    for field in (
        "decoding_params", "task_instruction", "tool_schemas",
        "speech_feature_parts", "speech_packet_sha256", "query_source",
        "key_representation_id", "matcher_policy_id", "carrier_lock_key",
        "media_relpath", "audio_seconds", "sample_rate_hz", "sample_id",
        "supplied_evidence", "evidence_provenance",
    ):
        assert twin[field] == plan[field], field
    assert len(twin["history"]) == len(plan["history"])
    assert twin["history"][0] == plan["history"][0]
    assert twin["history"][-1]["role"] == plan["history"][-1]["role"] == "control"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_release_swap_arm_with_a_different_alternate_id_still_renders(tmp_path):
    """Regression safety: an alternate that introduces a value id the primary
    does not carry at all -- the release-swap shape that already worked
    before this fix, since the differing id alone made arm B's evidence_id
    visibly differ -- still renders correctly through the alternate snapshot."""

    alt_only_id = "value:alt-only"
    group = _release_swap_live_group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=4)
    harness.supply_variant_for_phase = _release_swap_resolver(
        {"swap": (alt_only_id,), "aa": (), "plan": ()},
        release_swap_snapshots={
            "swap": _alt_knowledge_snapshot(value_id=alt_only_id, content="Alt-only content."),
        },
    )
    harness._output = _arm_output
    try:
        harness.run()
    finally:
        harness.close()

    requests = [
        payload["payload"]
        for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    swap = requests[1]
    values = [
        (block["evidence_id"], block["content"]) for block in swap["supplied_evidence"]
        if block["knowledge_role"] == "value"
    ]
    assert values == [(alt_only_id, "Alt-only content.")]


# ---------------------------------------------------------------------------
# 6. The offline dry run, on a synthetic row
# ---------------------------------------------------------------------------


def _dry_run_walk(tmp_path, *, selections, program_max_contacts=3):
    """Walk a two-arm Solver visit of a SYNTHETIC row, contact-free.

    Zero model, tokenizer, encoder, server or network contact: the walk seals
    canned role answers with the production sealer, resolves each arm's supply
    through the same per-arm resolver shape a flight binds, and reports per arm
    the supplied item ids it would have rendered.
    """

    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        dry_run_native_episode,
    )
    from speech_aware_evidence_acquisition.rails.controllers import (
        PhaseProgram,
        PhaseSpec,
    )
    from speech_aware_evidence_acquisition.rails.material import PhaseMaterial

    from test_rails_frozen_core_client import _World, _plan
    from test_rails_runner import _FakeAdapter, _knowledge_snapshot

    world = _World(tmp_path)
    world.samples = world.samples[:1]
    sample = world.samples[0]
    adapter = _FakeAdapter(samples=tuple(world.samples))
    program = PhaseProgram(
        program_id="dry-run-variants-proof-v1",
        phases=tuple(
            PhaseSpec(
                name=phase,
                purpose="answer" if phase == "solver" else phase,
                knowledge="supplied",
                response_format_id=None,
                barrier=False,
            )
            for phase in PHASES
        ),
        max_contacts=program_max_contacts,
        stop_rule="native-role-episode",
    ).validate()
    group = _live_group()
    episode = _live_config(group=group, max_contacts=program_max_contacts)

    def material_for_phase(phase, context, prior):
        return PhaseMaterial(
            instruction=f"dry-run instruction for {phase}",
            response_format=None,
            contact_id=f"dry-run:{phase}",
            purpose="answer" if phase == "solver" else phase,
        ).validate()

    phase_binding = {
        "material_for_phase": material_for_phase,
        # No ordinary phase supply at all: the row's own accumulated state stays
        # the bootstrap (empty), so the delivering arm's resolution must be
        # empty too and the walk's own fail-closed check says so.
        "supply_for_phase": None,
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": {
            sample.sample_id: {
                "packet_id": sample.audio_ref.path,
                "sha256": sample.audio_ref.sha256,
            }
        },
        "query_source": "speech_audio",
        "supply_specs": {},
    }
    runtime = SimpleNamespace(
        _composed=SimpleNamespace(values={}),
        _plan=_plan(),
        _samples=tuple(world.samples),
        _adapter=adapter,
        _phase_supply_seeds=lambda *args, **kwargs: ({}, {}),
        _dry_run_binding={
            "policy": program.program_id,
            "program": program,
            "episode": episode,
            "phase_binding": phase_binding,
            "store_ids": (),
            "supply_variant_for_phase": _arm_resolver(selections),
        },
    )
    return dry_run_native_episode(
        runtime,
        answers={
            "perception": "perception draft",
            "solver": "solver draft",
        },
        node_order=("perception", "solver"),
    )


def test_the_dry_run_walks_every_arm_of_a_synthetic_row(tmp_path):
    result = _dry_run_walk(tmp_path, selections={"wide": (ARM_VALUE,), "plan": ()})
    document = result.as_json()

    # The per-arm table: one column per declared construction, attached to the
    # node whose supply it is.
    assert document["supplied_value_counts_by_arm"] == {"solver": {"wide": 1, "plan": 0}}
    assert document["delivered_arm_id"] == "plan"

    solver_node = next(
        node for node in document["nodes"] if node["phase"] == "solver"
    )
    assert [arm["arm_id"] for arm in solver_node["supply_variant_arms"]] == [
        "wide", "plan",
    ]
    assert [arm["arm_index"] for arm in solver_node["supply_variant_arms"]] == [0, 1]
    assert [arm["deliver"] for arm in solver_node["supply_variant_arms"]] == [
        False, True,
    ]
    wide, plan = solver_node["supply_variant_arms"]
    # The arms differ in exactly the declared knob, and in the ids that knob
    # selects.
    assert wide["resolved_knobs"] == [{"path": f"{EX}.k", "value": 30}]
    assert plan["resolved_knobs"] == []
    assert wide["supplied_value_ids"] == [ARM_VALUE]
    # The DEFAULT arm's supplied ids are byte-identical to the unvaried plan's:
    # here the row's own state is the empty bootstrap, and the arm renders
    # exactly it.
    assert plan["supplied_value_ids"] == []
    assert plan["supplied_value_ids"] == list(document["bootstrap_value_ids"])
    # Perception -- the node the arm group does NOT fan out -- carries no arms.
    perception = next(
        node for node in document["nodes"] if node["phase"] == "perception"
    )
    assert perception["supply_variant_arms"] == []
    # And the walk stays contact-free.
    assert document["run_id"].startswith("SAEA-")


def test_the_dry_run_refuses_a_delivering_arm_that_resolves_a_different_supply(
    tmp_path,
):
    with pytest.raises(Exception, match="unvaried construction"):
        _dry_run_walk(
            tmp_path, selections={"wide": (ARM_VALUE,), "plan": (ARM_VALUE,)}
        )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_declared_group_without_its_resolver_is_refused_before_any_contact(tmp_path):
    group = _live_group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=3, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=3)
    harness._output = _arm_output
    try:
        with pytest.raises(Exception, match="supply_variant_for_phase"):
            harness.run()
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_resolver_without_a_declared_group_is_refused(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=2, planner_actions=(),
    )
    harness.supply_variant_for_phase = _arm_resolver({"plan": ()})
    try:
        with pytest.raises(Exception, match="not declared"):
            harness.run()
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_delivering_arm_that_resolves_a_different_supply_is_refused(tmp_path):
    """The live, non-circular statement of the default arm's byte identity.

    The delivering arm declares no overrides, so the flight's own independent
    per-arm resolution of it must reproduce exactly what this row's ordinary
    supply step acquired at this node. Here the resolver is made to disagree,
    and the row dies rather than delivering a request the cell's own identity
    does not describe.
    """

    group = _live_group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=3, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=3)
    harness.supply_variant_for_phase = _arm_resolver(
        {"wide": (ARM_VALUE,), "plan": (ARM_VALUE,)}
    )
    harness._output = _arm_output
    try:
        with pytest.raises(Exception, match="unvaried construction"):
            harness.run()
    finally:
        harness.close()



# ---------------------------------------------------------------------------
# 7. The twin arm and arm_visits: "first" (owner decision 172, merge set B)
# ---------------------------------------------------------------------------

COMP1_FRAGMENT = "slurp-native-stage3-comp1-fold-a-baseline-v1.json"


def _twin_block(**overrides):
    block = {
        "arms": [
            {"arm_id": "aa", "replicate_of": "plan", "max_supplied_items": 48},
            {"arm_id": "plan", "deliver": True, "max_supplied_items": 48},
        ],
        "fit_estimate": dict(FIT),
    }
    block.update(overrides)
    return block


def test_a_twin_arm_resolves_no_overrides_and_names_the_delivering_arm():
    group = _parse(_twin_block())
    assert group.arm_visits == "every"
    twin = group.arm("aa")
    assert twin.replicate_of == "plan"
    assert twin.knobs == ()
    assert twin.deliver is False
    assert group.delivered_arm.replicate_of is None


def test_arm_visits_first_is_accepted_and_defaults_to_every():
    assert _parse(_twin_block(arm_visits="first")).arm_visits == "first"
    assert _parse(_twin_block()).arm_visits == "every"
    assert _parse().arm_visits == "every"  # the plain exk10/plan group, untouched


@pytest.mark.parametrize(
    "mutate,expected",
    [
        pytest.param(
            lambda b: b["arms"][0].__setitem__("replicate_of", "aa"),
            "not the delivering arm",
            id="twin-names-itself",
        ),
        pytest.param(
            lambda b: b["arms"][0].__setitem__("overrides", {f"{EX}.k": 4}),
            "must declare no overrides",
            id="twin-with-overrides",
        ),
        pytest.param(
            lambda b: b["arms"][1].__setitem__("replicate_of", "plan"),
            "cannot also be a twin",
            id="delivering-arm-declares-replicate-of",
        ),
        pytest.param(
            lambda b: b.__setitem__("arm_visits", "sometimes"),
            "must be one of",
            id="unknown-arm-visits-value",
        ),
        pytest.param(
            lambda b: b.__setitem__("colour", "red"),
            "must be an object with exactly",
            id="unknown-top-level-key",
        ),
    ],
)
def test_twin_and_arm_visits_refusals(mutate, expected):
    block = _twin_block()
    mutate(block)
    with pytest.raises(SupplyVariantError, match=expected):
        _parse(block)


def test_a_twin_does_not_collide_with_the_identical_override_refusal():
    # Both the twin and the delivering arm declare NO overrides; without the
    # replicate_of exemption this would raise "two supply_variants arms
    # declare the same overrides".
    group = _parse(_twin_block())
    assert group.arm_ids == ("aa", "plan")


def test_the_receipt_carries_replicate_of_and_the_v3_schema():
    group = _parse(_twin_block())
    records = [
        supply_variant_arm_record(
            arm=group.arm("aa"), arm_index=0, contact_id="c0",
            supplied_value_ids=("b::1",),
        ),
        supply_variant_arm_record(
            arm=group.arm("plan"), arm_index=1, contact_id="c1",
            supplied_value_ids=("b::1",),
        ),
    ]
    receipt = supply_variant_receipt(group=group, phase_id="solver", records=records)
    assert receipt["schema"] == "saea-supply-variant-arms-v3"
    assert receipt["arm_visits"] == "every"
    assert receipt["visit_index"] == 0
    assert receipt["arms"][0]["replicate_of"] == "plan"
    assert receipt["arms"][1]["replicate_of"] is None
    # Neither the twin nor the delivering arm carries a release_swap: this
    # block has none declared at all.
    assert receipt["arms"][0]["release_swap"] is None
    assert receipt["arms"][1]["release_swap"] is None
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
    )


def test_a_v1_receipt_still_validates_unchanged():
    group = _parse()  # the plain exk10/plan two-arm group, no twin
    records = [
        supply_variant_arm_record(
            arm=group.arm("exk10"), arm_index=0, contact_id="c0",
            supplied_value_ids=("x::4",),
        ),
        supply_variant_arm_record(
            arm=group.arm("plan"), arm_index=1, contact_id="c1",
            supplied_value_ids=(),
        ),
    ]
    v1_receipt = {
        "schema": "saea-supply-variant-arms-v1",
        "phase_id": "solver",
        "arm_count": 2,
        "delivered_arm_id": "plan",
        "fit_estimate": group.fit_estimate.as_json(),
        "arms": [
            {k: v for k, v in record.items() if k not in ("replicate_of", "release_swap")}
            for record in records
        ],
    }
    validate_supply_variant_receipt(
        v1_receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
    )


def test_a_v2_receipt_still_validates_unchanged():
    """Coordinator amendment, 2026-09-28: a v2 receipt sealed before the
    release-swap route existed (no ``release_swap`` key on any arm row) still
    validates unchanged -- no sealed E42b data is rewritten."""

    group = _parse(_twin_block())
    records = [
        supply_variant_arm_record(
            arm=group.arm("aa"), arm_index=0, contact_id="c0",
            supplied_value_ids=("b::1",),
        ),
        supply_variant_arm_record(
            arm=group.arm("plan"), arm_index=1, contact_id="c1",
            supplied_value_ids=("b::1",),
        ),
    ]
    v2_receipt = {
        "schema": "saea-supply-variant-arms-v2",
        "phase_id": "solver",
        "arm_count": 2,
        "delivered_arm_id": "plan",
        "arm_visits": "every",
        "visit_index": 0,
        "fit_estimate": group.fit_estimate.as_json(),
        "arms": [
            {k: v for k, v in record.items() if k != "release_swap"}
            for record in records
        ],
    }
    validate_supply_variant_receipt(
        v2_receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
    )


def test_a_twin_that_does_not_resolve_the_delivering_arms_ids_is_refused():
    group = _parse(_twin_block())
    records = [
        supply_variant_arm_record(
            arm=group.arm("aa"), arm_index=0, contact_id="c0",
            supplied_value_ids=("b::1",),
        ),
        supply_variant_arm_record(
            arm=group.arm("plan"), arm_index=1, contact_id="c1",
            supplied_value_ids=("b::2",),
        ),
    ]
    receipt = supply_variant_receipt(group=group, phase_id="solver", records=records)
    with pytest.raises(ValueError, match="does not resolve exactly the delivering arm's ids"):
        validate_supply_variant_receipt(
            receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
        )


def test_arm_visits_cross_check_against_the_declared_configuration():
    group = _parse(_twin_block(arm_visits="first"))
    records = [
        supply_variant_arm_record(
            arm=group.arm("aa"), arm_index=0, contact_id="c0", supplied_value_ids=(),
        ),
        supply_variant_arm_record(
            arm=group.arm("plan"), arm_index=1, contact_id="c1", supplied_value_ids=(),
        ),
    ]
    receipt = supply_variant_receipt(group=group, phase_id="solver", records=records)
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
        arm_visits="first",
    )
    with pytest.raises(ValueError, match="arm_visits disagrees"):
        validate_supply_variant_receipt(
            receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
            arm_visits="every",
        )


def _first_visit_block(arm_count):
    arms = [
        {"arm_id": f"extra{i}", "max_supplied_items": 38, "overrides": {f"{EX}.k": 10 + i}}
        for i in range(arm_count - 2)
    ]
    arms.append({"arm_id": "aa", "replicate_of": "plan", "max_supplied_items": 48})
    arms.append({"arm_id": "plan", "deliver": True, "max_supplied_items": 48})
    return {"arms": arms, "fit_estimate": dict(FIT), "arm_visits": "first"}


@pytest.mark.parametrize(
    "program_id,arm_count,expected_ceiling",
    [
        ("phase-native-candidates-review-revise-cited-variants2first-v1", 2, 12),
        ("phase-native-candidates-review-revise-cited-variants3first-v1", 3, 13),
    ],
)
def test_the_variantsnfirst_fragments_compose_to_base_plus_k_minus_one(
    program_id, arm_count, expected_ceiling,
):
    """K = 2 or 3 gives ceiling 12 or 13 on the 11-contact cited anchor
    (design section 2): under ``arm_visits: "first"`` the arm count is NOT
    multiplied into every revision -- that was VAR-2's own bug -- it is added
    ONCE as (K - 1)."""

    values = _fragment(COMP1_FRAGMENT)
    values["policy"] = program_id
    values["native_episode"]["roles"]["solver"]["supply_variants"] = _first_visit_block(
        arm_count
    )
    program = default_phase_program(program_id)
    assert program.max_contacts == expected_ceiling
    config = load_native_episode_config(values, program)
    assert config.max_contacts == expected_ceiling
    assert config.supply_variant_group.arm_visits == "first"
    assert config.supply_variant_group.arm_count == arm_count


@pytest.mark.parametrize(
    "program_id,arm_count,expected_ceiling",
    [
        ("phase-native-candidates-review-revise-variants2first-v1", 2, 12),
        ("phase-native-candidates-review-revise-variants3first-v1", 3, 13),
    ],
)
def test_the_uncited_variantsnfirst_fragments_compose_to_base_plus_k_minus_one(
    program_id, arm_count, expected_ceiling,
):
    """Coordinator amendment, 2026-09-28: the UNCITED twins of the cited
    variantsNfirst fragments above compose to the SAME ceiling arithmetic --
    the uncited 11-contact anchor plus (K - 1) -- since the formula depends
    only on ``arm_visits: "first"`` and the arm count, never on the Solver's
    response format. ``VAR2_FRAGMENT`` is the uncited baseline (its own
    ``deliver_normaliser`` does not unwrap a cited-answer envelope, so it
    composes with a Solver ``response_format_id`` of ``null``)."""

    values = _fragment(VAR2_FRAGMENT)
    values["policy"] = program_id
    values["native_episode"]["roles"]["solver"]["supply_variants"] = _first_visit_block(
        arm_count
    )
    program = default_phase_program(program_id)
    assert program.max_contacts == expected_ceiling
    config = load_native_episode_config(values, program)
    assert config.max_contacts == expected_ceiling
    assert config.supply_variant_group.arm_visits == "first"
    assert config.supply_variant_group.arm_count == arm_count


def test_a_variantsnfirst_program_under_the_default_every_ceiling_is_refused():
    """The variants2first program's OWN ceiling (12) is only ever reached
    under "first"; the ordinary "every" multiplication would need 1 +
    2*(2+3+1) = 13, not 12, so composing the anchor's block without
    ``arm_visits`` on this program id must fail the ceiling assertion."""

    values = _fragment(COMP1_FRAGMENT)
    program_id = "phase-native-candidates-review-revise-cited-variants2first-v1"
    values["policy"] = program_id
    block = _first_visit_block(2)
    del block["arm_visits"]
    values["native_episode"]["roles"]["solver"]["supply_variants"] = block
    with pytest.raises(ValueError, match="contact ceiling"):
        load_native_episode_config(values, default_phase_program(program_id))


# ---------------------------------------------------------------------------
# 8. AT2/AT3: the twin's wire identity and revision cardinality, live
# ---------------------------------------------------------------------------


def _twin_live_group(*, arm_visits="every"):
    return parse_supply_variants(
        {
            "arms": [
                {"arm_id": "aa", "replicate_of": "plan", "max_supplied_items": 4},
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 4},
            ],
            "fit_estimate": dict(FIT),
            "arm_visits": arm_visits,
        },
        phase_id="solver", first_phase_id="perception",
        declared_stores=("train-exemplars",),
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_at2_the_twins_wire_payload_equals_the_delivering_arms_byte_for_byte(tmp_path):
    group = _twin_live_group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=3, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=3)
    harness.supply_variant_for_phase = _arm_resolver({"aa": (), "plan": ()})
    harness._output = _arm_output
    try:
        harness.run()
    finally:
        harness.close()

    requests = [
        payload["payload"]
        for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    assert len(requests) == 3
    twin, plan = requests[1], requests[2]

    # Unlike an ordinary (overriding) arm, the twin's supplied evidence is
    # the SAME as the delivering arm's: both empty here (the harness binds
    # no ordinary supply_for_phase, so the delivering arm's own resolution --
    # and the twin's, which takes the identical base_messages(ctx) path --
    # is the row's empty bootstrap).
    assert twin["supplied_evidence"] == plan["supplied_evidence"] == []
    assert twin["evidence_provenance"] == plan["evidence_provenance"] == []

    # Every other field a wire payload carries, compared byte for byte
    # between the twin and the delivering arm (AT2): decoding, contract,
    # tools, the speech packet and the carrier/session identity. The ONE
    # thing this list deliberately excludes is the contact's own transport
    # identifier (``request_id``) and the one history turn that names it
    # (the "control" turn) -- those differ between ANY two contacts of any
    # episode, arm-grouped or not, and are not part of "the wire payload" the
    # design's variant_arm_id claim is about.
    for field in (
        "decoding_params", "task_instruction", "tool_schemas",
        "speech_feature_parts", "speech_packet_sha256", "query_source",
        "key_representation_id", "matcher_policy_id", "carrier_lock_key",
        "media_relpath", "audio_seconds", "sample_rate_hz", "sample_id",
        "supplied_evidence", "evidence_provenance",
    ):
        assert twin[field] == plan[field], field
    assert len(twin["history"]) == len(plan["history"])
    assert twin["history"][0] == plan["history"][0]
    assert twin["history"][-1]["role"] == plan["history"][-1]["role"] == "control"


def _live_config_with_review(*, group, max_contacts, max_revisions):
    """The review-ON shape (reviewer/planner one visit per round) with an
    arm-grouped Solver, the twin of ``_live_config`` above."""

    return NativeEpisodeConfig(
        episode_id="native-role-runner-proof-v1",
        max_revisions=max_revisions,
        actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase, role_kind=phase, max_iterations=1, tool_names=(),
                supply_variants=(group if phase == "solver" else None),
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
    )


def _revision_output(key):
    sample_id, phase, visit, turn = key
    if phase == "planner":
        return ("REVISE", "ACCEPT")[visit - 1]
    if phase == "solver":
        return f"solver-arm-{visit}-{turn}:{sample_id}"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_at3_a_revision_visit_under_first_contacts_one_arm(tmp_path):
    group = parse_supply_variants(
        {
            "arms": [
                {"arm_id": "wide", "max_supplied_items": 4, "overrides": {f"{EX}.k": 30}},
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 4},
            ],
            "fit_estimate": dict(FIT),
            "arm_visits": "first",
        },
        phase_id="solver", first_phase_id="perception",
        declared_stores=("train-exemplars",),
    )
    # Perception(1) + round0[Solver 2 arms + Reviewer 1 + Planner 1]=4 +
    # round1[Solver 1 + Reviewer 1 + Planner 1]=3 -> 8, exactly base_ceiling
    # (7, the _config() review-on anchor at max_revisions=1) + (K - 1) = 8.
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=8,
        planner_actions=("REVISE", "ACCEPT"),
    )
    harness.config = _live_config_with_review(group=group, max_contacts=8, max_revisions=1)
    harness.supply_variant_for_phase = _arm_resolver({"wide": (ARM_VALUE,), "plan": ()})
    harness._output = _revision_output
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    assert close_summary["request_count"] == 8
    result = summary.results[0]
    episode_receipt = result.native_episode_receipt
    solver_visits = [
        visit for visit in episode_receipt["role_visits"] if visit["stage"] == "solver"
    ]
    assert len(solver_visits) == 2
    assert len(solver_visits[0]["execution_receipt"]["contacts"]) == 2
    assert len(solver_visits[1]["execution_receipt"]["contacts"]) == 1

    receipt = result.supply_variants
    assert receipt is not None
    assert receipt["arm_visits"] == "first"
    assert receipt["visit_index"] == 0
    assert [row["arm_id"] for row in receipt["arms"]] == ["wide", "plan"]
    assert receipt["arm_count"] == 2

    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id="plan", phase_id="solver",
        arm_visits="first",
    )
    # The delivered text is the REVISIT's own (single, delivering-arm) answer.
    assert result.final_response_text == _revision_output(
        (result.sample_id, "solver", 2, 1)
    )


# ---------------------------------------------------------------------------
# 9. AT6: a fake sealed row under arm_visits "first" with a twin, I7v v2
# ---------------------------------------------------------------------------


def _sealed_row_first_visit_with_twin(revisions=1):
    """A synthetic sealed row: arm_visits "first", a twin arm, N revisions.

    Visit 0 (the arm-bearing visit) carries two contacts (the twin "aa" then
    the delivering "plan"); every later visit carries exactly one contact,
    through the ordinary path -- the v2 shape ``core.bundle.outputs.
    _verify_supply_variant_trace_binding`` checks.
    """

    sample = "slurp:train:synthetic-svinst"
    arm_name = "speech-feature-query-native-tools"

    def sha(value):
        return hashlib.sha256(value.encode()).hexdigest()

    trace, visits = {}, []
    arm_ids = ["aa", "plan"]
    contacts0 = []
    for index, arm_id in enumerate(arm_ids):
        rid = f"v0-{arm_id}"
        answer = f"answer-v0-{arm_id}"
        contact = {
            "agent_contact_id": f"solver:0:{index}", "request_id": rid,
            "request_sha256": sha(rid), "response_sha256": sha("envelope-" + rid),
            "response_text_sha256": sha(answer),
        }
        contacts0.append(contact)
        trace[rid + "/request"] = {
            "arm": arm_name, "payload": {"sample_id": sample},
            "payload_sha256": contact["request_sha256"],
        }
        trace[rid + "/response"] = {
            "text": answer, "response_sha256": contact["response_sha256"],
            "response_text_sha256": contact["response_text_sha256"],
        }
    visits.append({
        "role_id": "solver", "stage": "solver",
        "execution_receipt": {"contacts": contacts0, "final_contact": contacts0[-1]},
    })
    last = contacts0[-1]
    for revision in range(1, revisions + 1):
        rid = f"v{revision}"
        answer = f"answer-{rid}"
        contact = {
            "agent_contact_id": f"solver:{revision}:0", "request_id": rid,
            "request_sha256": sha(rid), "response_sha256": sha("envelope-" + rid),
            "response_text_sha256": sha(answer),
        }
        trace[rid + "/request"] = {
            "arm": arm_name, "payload": {"sample_id": sample},
            "payload_sha256": contact["request_sha256"],
        }
        trace[rid + "/response"] = {
            "text": answer, "response_sha256": contact["response_sha256"],
            "response_text_sha256": contact["response_text_sha256"],
        }
        visits.append({
            "role_id": "solver", "stage": "solver",
            "execution_receipt": {"contacts": [contact], "final_contact": contact},
        })
        last = contact
    trace["synthetic/org"] = {"org_final_query_state": {
        "query_sample_id": sample, "retrieved_value_ids": ["v:plan"],
    }}
    variant = {
        "schema": "saea-supply-variant-arms-v2", "phase_id": "solver",
        "arm_count": 2, "delivered_arm_id": "plan", "arm_visits": "first",
        "visit_index": 0,
        "fit_estimate": {
            "slot_tokens": 24576, "completion_ceiling": 512,
            "base_prompt_tokens": 100, "tokens_per_supplied_item": 10,
            "reserve_tokens": 3072, "prompt_limit_tokens": 20990,
        },
        "arms": [
            {"arm_index": 0, "arm_id": "aa", "deliver": False, "replicate_of": "plan",
             "contact_id": contacts0[0]["agent_contact_id"], "resolved_knobs": [],
             "supplied_value_ids": ["v:plan"], "supplied_item_count": 1,
             "max_supplied_items": 5},
            {"arm_index": 1, "arm_id": "plan", "deliver": True, "replicate_of": None,
             "contact_id": contacts0[1]["agent_contact_id"], "resolved_knobs": [],
             "supplied_value_ids": ["v:plan"], "supplied_item_count": 1,
             "max_supplied_items": 5},
        ],
    }
    row = {
        "request_id": last["request_id"], "sample_id": sample,
        "carrier_lock_key": "slurp", "arm": arm_name,
        "text": trace[last["request_id"] + "/response"]["text"],
        "admitted": True, "request_sha256": last["request_sha256"],
        "response_sha256": last["response_sha256"],
        "response_text_sha256": last["response_text_sha256"],
        "native_episode_receipt": {"role_visits": visits},
        "supply_variants": variant,
    }
    return row, trace, sample, arm_name


def test_at6_a_sealed_row_under_arm_visits_first_with_a_twin_passes_i7v():
    from speech_aware_evidence_acquisition.core.bundle.outputs import (
        _verify_outputs, _verify_outputs_trace_binding,
    )

    row, trace, sample, arm_name = _sealed_row_first_visit_with_twin(revisions=1)
    rows = _verify_outputs(
        (json.dumps(row) + "\n").encode(), frozenset({sample}), "slurp", arm_name,
    )
    _verify_outputs_trace_binding(rows, trace)


# ---------------------------------------------------------------------------
# 10. The W4-SV blocker fix: I7v (core.bundle.outputs) does not hash rendered
#     content against a snapshot -- it binds receipt/contact IDENTITY to the
#     trace -- so a release-swap arm's row (B) verifies exactly as A's and
#     T's already do above.
# ---------------------------------------------------------------------------


def _sealed_row_first_visit_with_release_swap(revisions=1):
    """The same synthetic-sealed-row shape as
    ``_sealed_row_first_visit_with_twin``, with arm 0 a release-swap arm
    (schema v3) instead of a twin."""

    sample = "slurp:train:synthetic-svrelease"
    arm_name = "speech-feature-query-native-tools"

    def sha(value):
        return hashlib.sha256(value.encode()).hexdigest()

    trace, visits = {}, []
    arm_ids = ["swap", "plan"]
    contacts0 = []
    for index, arm_id in enumerate(arm_ids):
        rid = f"v0-{arm_id}"
        answer = f"answer-v0-{arm_id}"
        contact = {
            "agent_contact_id": f"solver:0:{index}", "request_id": rid,
            "request_sha256": sha(rid), "response_sha256": sha("envelope-" + rid),
            "response_text_sha256": sha(answer),
        }
        contacts0.append(contact)
        trace[rid + "/request"] = {
            "arm": arm_name, "payload": {"sample_id": sample},
            "payload_sha256": contact["request_sha256"],
        }
        trace[rid + "/response"] = {
            "text": answer, "response_sha256": contact["response_sha256"],
            "response_text_sha256": contact["response_text_sha256"],
        }
    visits.append({
        "role_id": "solver", "stage": "solver",
        "execution_receipt": {"contacts": contacts0, "final_contact": contacts0[-1]},
    })
    last = contacts0[-1]
    for revision in range(1, revisions + 1):
        rid = f"v{revision}"
        answer = f"answer-{rid}"
        contact = {
            "agent_contact_id": f"solver:{revision}:0", "request_id": rid,
            "request_sha256": sha(rid), "response_sha256": sha("envelope-" + rid),
            "response_text_sha256": sha(answer),
        }
        trace[rid + "/request"] = {
            "arm": arm_name, "payload": {"sample_id": sample},
            "payload_sha256": contact["request_sha256"],
        }
        trace[rid + "/response"] = {
            "text": answer, "response_sha256": contact["response_sha256"],
            "response_text_sha256": contact["response_text_sha256"],
        }
        visits.append({
            "role_id": "solver", "stage": "solver",
            "execution_receipt": {"contacts": [contact], "final_contact": contact},
        })
        last = contact
    trace["synthetic/org"] = {"org_final_query_state": {
        "query_sample_id": sample, "retrieved_value_ids": ["v:plan"],
    }}
    variant = {
        "schema": "saea-supply-variant-arms-v3", "phase_id": "solver",
        "arm_count": 2, "delivered_arm_id": "plan", "arm_visits": "first",
        "visit_index": 0,
        "fit_estimate": {
            "slot_tokens": 24576, "completion_ceiling": 512,
            "base_prompt_tokens": 100, "tokens_per_supplied_item": 10,
            "reserve_tokens": 3072, "prompt_limit_tokens": 20990,
        },
        "arms": [
            {"arm_index": 0, "arm_id": "swap", "deliver": False, "replicate_of": None,
             "contact_id": contacts0[0]["agent_contact_id"], "resolved_knobs": [],
             "supplied_value_ids": ["v:swap"], "supplied_item_count": 1,
             "max_supplied_items": 5,
             "release_swap": {"store_id": "train-exemplars", "release": "alt.json"}},
            {"arm_index": 1, "arm_id": "plan", "deliver": True, "replicate_of": None,
             "contact_id": contacts0[1]["agent_contact_id"], "resolved_knobs": [],
             "supplied_value_ids": ["v:plan"], "supplied_item_count": 1,
             "max_supplied_items": 5, "release_swap": None},
        ],
    }
    row = {
        "request_id": last["request_id"], "sample_id": sample,
        "carrier_lock_key": "slurp", "arm": arm_name,
        "text": trace[last["request_id"] + "/response"]["text"],
        "admitted": True, "request_sha256": last["request_sha256"],
        "response_sha256": last["response_sha256"],
        "response_text_sha256": last["response_text_sha256"],
        "native_episode_receipt": {"role_visits": visits},
        "supply_variants": variant,
    }
    return row, trace, sample, arm_name


def test_a_sealed_row_with_a_release_swap_arm_passes_i7v():
    """I7v binds receipt/contact IDENTITY to the trace -- it never hashes a
    contact's rendered content against a knowledge snapshot -- so a
    release-swap arm's row (B) verifies exactly as an ordinary arm's or a
    twin's already does (``test_at6_...`` above); no change to
    ``core.bundle.outputs`` is needed for the W4-SV blocker fix."""

    from speech_aware_evidence_acquisition.core.bundle.outputs import (
        _verify_outputs, _verify_outputs_trace_binding,
    )

    row, trace, sample, arm_name = _sealed_row_first_visit_with_release_swap(revisions=1)
    rows = _verify_outputs(
        (json.dumps(row) + "\n").encode(), frozenset({sample}), "slurp", arm_name,
    )
    _verify_outputs_trace_binding(rows, trace)


def test_at6_a_later_visit_with_more_than_one_contact_is_refused():
    from speech_aware_evidence_acquisition.core.bundle import BundleError
    from speech_aware_evidence_acquisition.core.bundle.outputs import (
        _verify_outputs, _verify_outputs_trace_binding,
    )

    row, trace, sample, arm_name = _sealed_row_first_visit_with_twin(revisions=1)
    later_contacts = row["native_episode_receipt"]["role_visits"][1]["execution_receipt"]["contacts"]
    later_contacts.append(dict(later_contacts[0]))
    rows = _verify_outputs(
        (json.dumps(row) + "\n").encode(), frozenset({sample}), "slurp", arm_name,
    )
    with pytest.raises(Exception, match="I7v"):
        _verify_outputs_trace_binding(rows, trace)
    _ = BundleError  # imported for readers grepping the invariant name
