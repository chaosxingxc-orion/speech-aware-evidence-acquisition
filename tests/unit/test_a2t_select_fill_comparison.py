"""Pure post-seal analysis for the fresh SELECT/FILL four-arm experiment."""

from __future__ import annotations

from copy import deepcopy

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_select_fill_comparison import (
    ARM_ORDER,
    DIRECT_M0,
    JOINT_DRAFT_REVISE,
    JOINT_ONE_CALL,
    SELECT_THEN_FILL,
    AnalysisError,
    analyze_select_fill_comparison,
    distinct_name_set_equal,
    name_multiplicity_equal,
    tier_stratified_paired_bootstrap,
)


IDS = tuple(
    [f"tier1_direct:{index:06d}" for index in range(4)]
    + [f"tier2_parametric:{index:06d}" for index in range(4)]
)


def _outcome(
    sample_id: str,
    *,
    exact: float = 0.0,
    tool: float = 1.0,
    slot: float = 0.5,
    parsed: bool = True,
) -> dict[str, object]:
    return {
        "sample_id": sample_id,
        "tier": sample_id.split(":", 1)[0],
        "exact_match": exact,
        "tool_accuracy": tool,
        "slot_f1": slot,
        "parsed": parsed,
    }


def _inputs() -> dict[str, object]:
    outcomes = {
        arm: [_outcome(sample_id) for sample_id in IDS]
        for arm in ARM_ORDER
    }
    # Split saves rows 0, 1, and 4 versus both joint controls, harms row 2,
    # and ties the other rows.  It improves direct on rows 0 and 4 only.
    for arm in (JOINT_ONE_CALL, JOINT_DRAFT_REVISE):
        outcomes[arm][2]["exact_match"] = 1.0
    for index in (0, 1, 4):
        outcomes[SELECT_THEN_FILL][index].update(
            exact_match=1.0, slot_f1=1.0
        )
    for index in (1,):
        outcomes[DIRECT_M0][index]["exact_match"] = 1.0
    outcomes[SELECT_THEN_FILL][3].update(parsed=False, tool_accuracy=0.0)
    for index in (5, 6):
        outcomes[SELECT_THEN_FILL][index]["tool_accuracy"] = 0.0
        outcomes[JOINT_ONE_CALL][index]["tool_accuracy"] = 0.0
        outcomes[JOINT_DRAFT_REVISE][index]["tool_accuracy"] = 0.0

    reachability = [
        {
            "sample_id": sample_id,
            "tier": sample_id.split(":", 1)[0],
            "sealed": True,
            "required_tools_reachable": index != 5,
        }
        for index, sample_id in enumerate(IDS)
    ]
    selector = [
        {
            "sample_id": sample_id,
            "tier": sample_id.split(":", 1)[0],
            "sealed": True,
            "distinct_name_set_correct": index not in {3, 5},
            "multiplicity_correct": index not in {3, 5, 6},
            "gold_call_count": 2 if index in {1, 6} else 1,
        }
        for index, sample_id in enumerate(IDS)
    ]
    joint = [
        {
            "sample_id": sample_id,
            "tier": sample_id.split(":", 1)[0],
            "sealed": True,
            "one_call_distinct_name_set_correct": index != 5,
            "one_call_multiplicity_correct": index not in {5, 6},
            "draft_distinct_name_set_correct": index != 5,
            "draft_multiplicity_correct": index not in {5, 6},
            "revised_distinct_name_set_correct": index != 5,
            "revised_multiplicity_correct": index not in {5, 6},
        }
        for index, sample_id in enumerate(IDS)
    ]
    efficiency = {
        arm: {
            "prompt_tokens": 1000 + index,
            "contacts": 8 * (2 if arm in {JOINT_DRAFT_REVISE, SELECT_THEN_FILL} else 1),
            "raw_total_latency_seconds": 20.0 + index,
        }
        for index, arm in enumerate(ARM_ORDER)
    }
    official = {}
    for arm, rows in outcomes.items():
        per_tier = {}
        for tier in sorted({str(row["tier"]) for row in rows}):
            tier_rows = [row for row in rows if row["tier"] == tier]
            per_tier[tier] = {
                "samples": len(tier_rows),
                "exact_match": sum(float(row["exact_match"]) for row in tier_rows)
                / len(tier_rows),
                "tool_accuracy": sum(float(row["tool_accuracy"]) for row in tier_rows)
                / len(tier_rows),
                "slot_precision": 0.8,
                "slot_recall": 0.6,
                "slot_f1": 0.6857142857142857,
            }
        official[arm] = {
            "overall": {
                "samples": len(rows),
                "exact_match": sum(float(row["exact_match"]) for row in rows)
                / len(rows),
                "tool_accuracy": sum(float(row["tool_accuracy"]) for row in rows)
                / len(rows),
                "slot_precision": 0.75,
                "slot_recall": 0.5,
                "slot_f1": 0.6,
            },
            "per_tier": per_tier,
        }
    return {
        "outcomes_by_arm": outcomes,
        "official_metrics_by_arm": official,
        "candidate_reachability": reachability,
        "selector_diagnostics": selector,
        "joint_diagnostics": joint,
        "efficiency_by_arm": efficiency,
        "post_seal": True,
        "bootstrap_replicates": 250,
    }


def _refresh_official_accuracy(inputs: dict[str, object]) -> None:
    outcomes = inputs["outcomes_by_arm"]
    official = inputs["official_metrics_by_arm"]
    assert isinstance(outcomes, dict) and isinstance(official, dict)
    for arm, rows in outcomes.items():
        groups = {
            "overall": rows,
            **{
                tier: [row for row in rows if row["tier"] == tier]
                for tier in sorted({str(row["tier"]) for row in rows})
            },
        }
        for group, members in groups.items():
            target = (
                official[arm]["overall"]
                if group == "overall"
                else official[arm]["per_tier"][group]
            )
            target["exact_match"] = sum(
                float(row["exact_match"]) for row in members
            ) / len(members)
            target["tool_accuracy"] = sum(
                float(row["tool_accuracy"]) for row in members
            ) / len(members)


def test_builds_metrics_diagnostics_attribution_and_paired_effects() -> None:
    inputs = _inputs()

    report = analyze_select_fill_comparison(**inputs)

    assert report["schema"] == "saea-a2t-select-fill-comparison-v1"
    assert report["analysis_phase"] == "post-seal"
    assert report["row_count"] == 8
    assert report["arms"][SELECT_THEN_FILL]["overall"] == {
        "samples": 8,
        "exact_match": 3 / 8,
        "tool_accuracy": 5 / 8,
        "slot_precision": 0.75,
        "slot_recall": 0.5,
        "slot_f1": 0.6,
        "paired_item_slot_f1": 11 / 16,
        "parse_rate": 7 / 8,
    }
    assert report["arms"][SELECT_THEN_FILL]["per_tier"]["tier1_direct"][
        "exact_match"
    ] == 0.5
    assert report["attribution"][SELECT_THEN_FILL]["overall"]["counts"] == {
        "SUPPLY": 1,
        "SELECT": 2,
        "FILL": 2,
        "SUCCESS": 3,
    }
    assert report["candidate_reachability"]["overall"] == {
        "samples": 8,
        "reachable_count": 7,
        "reachable_rate": 7 / 8,
    }
    assert report["attribution"][SELECT_THEN_FILL]["by_sample"][IDS[5]] == "SUPPLY"
    assert report["attribution"][DIRECT_M0]["overall"]["counts"]["SUPPLY"] == 0
    assert report["selector_diagnostics"]["overall"] == {
        "samples": 8,
        "distinct_name_set_accuracy": 6 / 8,
        "multiplicity_accuracy": 5 / 8,
        "combined_accuracy": 5 / 8,
    }
    assert report["selector_diagnostics"]["multi_call"]["samples"] == 2
    assert report["joint_name_diagnostics"]["draft"]["overall"][
        "combined_accuracy"
    ] == 6 / 8
    conditional = report["conditional_fill_diagnostic"]
    assert conditional["conditioning_event"] == (
        "sealed SELECT name multiplicity matches the expected calls"
    )
    assert conditional["overall"]["eligible_rows"] == 5
    assert conditional["overall"]["exact_accuracy"] == 3 / 5

    primary = report["paired_contrasts"]["split_vs_revise"]
    assert primary["role"] == "primary"
    assert primary["exact"]["saves"] == 3
    assert primary["exact"]["harms"] == 1
    assert primary["exact"]["ties"] == 4
    assert primary["exact"]["sign_test"]["p_value"] == pytest.approx(0.625)
    assert primary["metrics"]["exact_match"]["point_estimate"] == 0.25
    assert primary["metrics"]["exact_match"]["paired_bootstrap"]["seed"] == 20260903
    assert primary["metrics"]["exact_match"]["paired_bootstrap"][
        "stratification"
    ] == "tier"
    assert set(report["paired_contrasts"]) == {
        "split_vs_revise",
        "split_vs_joint_one_call",
        "split_vs_direct_m0",
    }
    assert report["efficiency"] == inputs["efficiency_by_arm"]


def test_official_micro_slot_f1_is_not_replaced_by_item_macro() -> None:
    inputs = _inputs()
    report = analyze_select_fill_comparison(**inputs)

    overall = report["arms"][SELECT_THEN_FILL]["overall"]
    assert overall["slot_f1"] == 0.6
    assert overall["paired_item_slot_f1"] == 11 / 16
    primary = report["paired_contrasts"]["split_vs_revise"]
    assert "slot_f1" not in primary["metrics"]
    assert "paired_item_slot_f1" in primary["metrics"]


def test_duplicate_names_use_distinct_set_and_counter_predicates() -> None:
    expected = ("calendar.create", "calendar.create", "mail.send")

    assert distinct_name_set_equal(expected, ("calendar.create", "mail.send"))
    assert not name_multiplicity_equal(expected, ("calendar.create", "mail.send"))
    assert name_multiplicity_equal(
        expected, ("mail.send", "calendar.create", "calendar.create")
    )


def test_attribution_is_mutually_exclusive_and_exhaustive_per_arm_and_tier() -> None:
    report = analyze_select_fill_comparison(**_inputs())

    for arm in ARM_ORDER:
        overall = report["attribution"][arm]["overall"]
        assert set(overall["counts"]) == {"SUPPLY", "SELECT", "FILL", "SUCCESS"}
        assert sum(overall["counts"].values()) == 8
        assert sum(overall["rates"].values()) == pytest.approx(1.0)
        for tier in report["attribution"][arm]["per_tier"].values():
            assert sum(tier["counts"].values()) == tier["samples"]
    assert all(
        tier["counts"]["SUPPLY"] == 0
        for tier in report["attribution"][DIRECT_M0]["per_tier"].values()
    )


def test_tier_stratified_bootstrap_is_deterministic_and_resamples_paired_rows() -> None:
    tiers = {sample_id: sample_id.split(":", 1)[0] for sample_id in IDS}
    values = {sample_id: float(index % 3) for index, sample_id in enumerate(IDS)}

    first = tier_stratified_paired_bootstrap(
        sample_ids=IDS,
        tiers_by_id=tiers,
        statistic=lambda ids: sum(values[item] for item in ids) / len(ids),
        n_replicates=500,
        seed=20260903,
    )
    second = tier_stratified_paired_bootstrap(
        sample_ids=tuple(reversed(IDS)),
        tiers_by_id=tiers,
        statistic=lambda ids: sum(values[item] for item in ids) / len(ids),
        n_replicates=500,
        seed=20260903,
    )

    assert first == second
    assert first.n_replicates == 500
    assert first.seed == 20260903
    assert first.ci_level == 0.90
    assert first.strata == ("tier1_direct", "tier2_parametric")


def test_preregistered_promotion_requires_every_gate() -> None:
    inputs = _inputs()
    outcomes = inputs["outcomes_by_arm"]
    assert isinstance(outcomes, dict)
    # A decisive fixture: every split row succeeds and both joint controls and
    # direct fail.  The lower bootstrap bounds are therefore exactly +1.
    for row in outcomes[SELECT_THEN_FILL]:
        row.update(exact_match=1.0, tool_accuracy=1.0, slot_f1=1.0, parsed=True)
    for arm in (DIRECT_M0, JOINT_ONE_CALL, JOINT_DRAFT_REVISE):
        for row in outcomes[arm]:
            row.update(exact_match=0.0, tool_accuracy=0.0, slot_f1=0.5, parsed=True)
    for row in inputs["candidate_reachability"]:
        row["required_tools_reachable"] = True
    for row in inputs["selector_diagnostics"]:
        row.update(distinct_name_set_correct=True, multiplicity_correct=True)
    for row in inputs["joint_diagnostics"]:
        row.update(
            one_call_distinct_name_set_correct=False,
            one_call_multiplicity_correct=False,
            revised_distinct_name_set_correct=False,
            revised_multiplicity_correct=False,
        )

    _refresh_official_accuracy(inputs)
    report = analyze_select_fill_comparison(**inputs)

    decision = report["promotion_decision"]
    assert decision["promote"] is True
    assert all(decision["gates"].values())

    regressed = deepcopy(inputs)
    regressed_outcomes = regressed["outcomes_by_arm"]
    assert isinstance(regressed_outcomes, dict)
    # Split loses two net exact rows in one tier against direct M0.
    for index in range(4):
        regressed_outcomes[SELECT_THEN_FILL][index]["exact_match"] = 0.0
    for index in (0, 1):
        regressed_outcomes[DIRECT_M0][index].update(
            exact_match=1.0, tool_accuracy=1.0
        )
    _refresh_official_accuracy(regressed)
    failed = analyze_select_fill_comparison(**regressed)["promotion_decision"]
    assert failed["promote"] is False
    assert failed["gates"]["no_tier_over_one_net_exact_loss"] is False


def test_refuses_gold_derived_inputs_before_post_seal() -> None:
    inputs = _inputs()
    inputs["post_seal"] = False
    with pytest.raises(AnalysisError, match="post-seal"):
        analyze_select_fill_comparison(**inputs)

    inputs = _inputs()
    inputs["selector_diagnostics"][0]["sealed"] = False
    with pytest.raises(AnalysisError, match="sealed"):
        analyze_select_fill_comparison(**inputs)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data["outcomes_by_arm"].pop(DIRECT_M0), "four arms"),
        (lambda data: data["outcomes_by_arm"][DIRECT_M0].pop(), "identities"),
        (
            lambda data: data["candidate_reachability"].__setitem__(
                0, data["candidate_reachability"][1]
            ),
            "duplicate",
        ),
        (
            lambda data: data["joint_diagnostics"][0].__setitem__("tier", "wrong"),
            "tier",
        ),
        (
            lambda data: data["outcomes_by_arm"][DIRECT_M0][0].__setitem__(
                "exact_match", 2.0
            ),
            "within",
        ),
        (
            lambda data: data["outcomes_by_arm"][DIRECT_M0][0].__setitem__(
                "tool_accuracy", 0.5
            ),
            "binary",
        ),
        (
            lambda data: data["selector_diagnostics"][0].__setitem__(
                "multiplicity_correct", False
            ),
            "disagrees with official tool accuracy",
        ),
        (
            lambda data: data["efficiency_by_arm"][DIRECT_M0].__setitem__(
                "contacts", -1
            ),
            "nonnegative",
        ),
    ],
)
def test_refuses_malformed_or_misaligned_inputs(mutation, message: str) -> None:
    inputs = _inputs()
    mutation(inputs)
    with pytest.raises(AnalysisError, match=message):
        analyze_select_fill_comparison(**inputs)


def test_population_mode_requires_exactly_104_identities_and_13_per_tier() -> None:
    inputs = _inputs()
    inputs["population_mode"] = True
    inputs["bootstrap_replicates"] = 10_000
    with pytest.raises(AnalysisError, match="exactly 104"):
        analyze_select_fill_comparison(**inputs)

    population_ids = tuple(
        f"tier{tier}_kind:{index:06d}"
        for tier, count in [(1, 12), (2, 14), *[(tier, 13) for tier in range(3, 9)]]
        for index in range(count)
    )
    inputs = _inputs()
    inputs["population_mode"] = True
    inputs["bootstrap_replicates"] = 10_000
    inputs["outcomes_by_arm"] = {
        arm: [_outcome(sample_id) for sample_id in population_ids]
        for arm in ARM_ORDER
    }
    inputs["candidate_reachability"] = [
        {
            "sample_id": sample_id,
            "tier": sample_id.split(":", 1)[0],
            "sealed": True,
            "required_tools_reachable": True,
        }
        for sample_id in population_ids
    ]
    inputs["selector_diagnostics"] = [
        {
            "sample_id": sample_id,
            "tier": sample_id.split(":", 1)[0],
            "sealed": True,
            "distinct_name_set_correct": True,
            "multiplicity_correct": True,
            "gold_call_count": 1,
        }
        for sample_id in population_ids
    ]
    inputs["joint_diagnostics"] = [
        {
            "sample_id": sample_id,
            "tier": sample_id.split(":", 1)[0],
            "sealed": True,
            "one_call_distinct_name_set_correct": True,
            "one_call_multiplicity_correct": True,
            "draft_distinct_name_set_correct": True,
            "draft_multiplicity_correct": True,
            "revised_distinct_name_set_correct": True,
            "revised_multiplicity_correct": True,
        }
        for sample_id in population_ids
    ]
    with pytest.raises(AnalysisError, match="13 rows per tier"):
        analyze_select_fill_comparison(**inputs)
