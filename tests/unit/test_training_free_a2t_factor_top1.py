"""Tests for the preregistered semantic-factor top-1 AgentLoop."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_factor_top1 as factor,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ItemScore


REPO_ROOT = Path(__file__).resolve().parents[2]

REGISTRY = (
    {
        "tool_id": "11",
        "domain": "smart_home",
        "category": "lighting",
        "tool_name": "setLightBrightness",
        "signature": "setLightBrightness(deviceId: String, brightness: Int)",
        "description": "Set the brightness of a light in a room.",
        "argument_defaults": "deviceId=lamp; brightness=50",
        "argument_constraints": "brightness: [0-100]",
    },
    {
        "tool_id": "12",
        "domain": "smart_home",
        "category": "lighting",
        "tool_name": "getLightStatus",
        "signature": "getLightStatus(deviceId: String)",
        "description": "Get whether a room light is on and its brightness.",
        "argument_defaults": "deviceId=lamp",
        "argument_constraints": "",
    },
    {
        "tool_id": "20",
        "domain": "weather",
        "category": "forecast",
        "tool_name": "getWeatherForecast",
        "signature": "getWeatherForecast(location: String, days: Int?)",
        "description": "Get a weather forecast for a location.",
        "argument_defaults": "days=1",
        "argument_constraints": "days: [1-10]",
    },
)


def _factor_payload(**overrides: object) -> str:
    payload: dict[str, object] = {
        "task_action": "set",
        "task_object": "room light brightness",
        "qualifiers": ["kitchen", "bright"],
        "argument_hints": [
            {"role": "brightness", "value_hint": "eighty percent"},
            {"role": "room", "value_hint": "kitchen"},
        ],
        "uncertainty": "low",
    }
    payload.update(overrides)
    return json.dumps(payload)


def _score(exact: int, *, tool: int | None = None) -> ItemScore:
    tool_value = exact if tool is None else tool
    return ItemScore(
        tool_accuracy=float(tool_value),
        exact_match=float(exact),
        slot_true_positives=exact,
        slot_expected_total=1,
        slot_predicted_total=1,
    )


def test_factor_parser_canonicalizes_order_and_duplicates() -> None:
    parsed = factor.parse_semantic_factors(
        _factor_payload(
            qualifiers=[" bright ", "kitchen", "bright"],
            argument_hints=[
                {"role": "room", "value_hint": " kitchen "},
                {"role": "brightness", "value_hint": "eighty   percent"},
                {"role": "room", "value_hint": "kitchen"},
            ],
        ),
        registry_tool_names=tuple(row["tool_name"] for row in REGISTRY),
    )
    assert parsed.status == "valid-nonempty"
    assert parsed.factors is not None
    assert parsed.factors.qualifiers == ("bright", "kitchen")
    assert [(hint.role, hint.value_hint) for hint in parsed.factors.argument_hints] == [
        ("brightness", "eighty percent"),
        ("room", "kitchen"),
    ]
    assert parsed.canonical_json == json.dumps(
        parsed.factors.as_json(), ensure_ascii=True, separators=(",", ":")
    )


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"extra": "field"}, "exact fields"),
        ({"task_action": "turn on\nnow"}, "ASCII"),
        ({"task_object": "caf\u00e9"}, "ASCII"),
        ({"task_object": "setLightBrightness"}, "tool name"),
        ({"uncertainty": "certain"}, "uncertainty"),
    ],
)
def test_factor_parser_fails_closed_on_schema_or_leakage(
    payload: dict[str, object], reason: str
) -> None:
    raw = json.loads(_factor_payload())
    raw.update(payload)
    if "extra" in payload:
        raw["extra"] = payload["extra"]
    parsed = factor.parse_semantic_factors(
        json.dumps(raw),
        registry_tool_names=tuple(row["tool_name"] for row in REGISTRY),
    )
    assert parsed.status == "invalid"
    assert reason in parsed.reason
    assert parsed.factors is None


def test_factor_parser_marks_a_valid_empty_state() -> None:
    parsed = factor.parse_semantic_factors(
        _factor_payload(
            task_action="",
            task_object="",
            qualifiers=[],
            argument_hints=[],
            uncertainty="high",
        ),
        registry_tool_names=tuple(row["tool_name"] for row in REGISTRY),
    )
    assert parsed.status == "valid-empty"
    assert parsed.factors is not None


def test_top1_retrieval_is_order_invariant_and_strips_defaults() -> None:
    parsed = factor.parse_semantic_factors(
        _factor_payload(),
        registry_tool_names=tuple(row["tool_name"] for row in REGISTRY),
    )
    assert parsed.factors is not None
    first = factor.retrieve_registry_top1(parsed.factors, REGISTRY)
    second = factor.retrieve_registry_top1(parsed.factors, tuple(reversed(REGISTRY)))
    assert first == second
    assert first.available is True
    assert first.tool_name == "setLightBrightness"
    assert first.ranking_relation == "unique-top"
    assert first.positive_document_count >= 1
    supplied = json.loads(first.prompt_block)
    assert supplied["tool_name"] == "setLightBrightness"
    assert "argument_defaults" not in supplied
    assert len(first.prompt_block.splitlines()) == 1


def test_top1_retrieval_records_ties_and_unavailable_queries() -> None:
    tied_registry = (
        {**REGISTRY[0], "tool_id": "2", "tool_name": "setAlpha"},
        {**REGISTRY[0], "tool_id": "1", "tool_name": "setBeta"},
    )
    generic = factor.SemanticFactors(
        task_action="set",
        task_object="light",
        qualifiers=(),
        argument_hints=(),
        uncertainty="medium",
    )
    tied = factor.retrieve_registry_top1(generic, tied_registry)
    assert tied.ranking_relation == "tied-top"
    assert tied.tool_name == "setBeta"
    empty = replace(generic, task_action="zzzz", task_object="yyyy")
    unavailable = factor.retrieve_registry_top1(empty, REGISTRY)
    assert unavailable.available is False
    assert unavailable.ranking_relation == "no-positive"
    assert unavailable.prompt_block == ""


def test_runtime_state_uses_relations_and_buckets_not_literal_identity() -> None:
    parsed = factor.parse_semantic_factors(
        _factor_payload(),
        registry_tool_names=tuple(row["tool_name"] for row in REGISTRY),
    )
    assert parsed.factors is not None
    retrieval = factor.retrieve_registry_top1(parsed.factors, REGISTRY)
    m0 = json.dumps(
        [{"name": "getLightStatus", "arguments": {"deviceId": "kitchen"}}]
    )
    state = factor.extract_runtime_state(parsed, retrieval, m0)
    assert state.m0_relation == "m0-known-disagrees"
    assert state.factor_status == "valid-nonempty"
    assert state.ranking_relation == "unique-top"
    assert state.nonempty_field_count == "three-or-more"
    serialized = json.dumps(state.coarse_key + state.detailed_key)
    assert "setLightBrightness" not in serialized
    matching = factor.extract_runtime_state(
        parsed,
        retrieval,
        json.dumps([{"name": "setLightBrightness", "arguments": {}}]),
    )
    assert matching.m0_relation == "m0-contains-top1"
    unresolved = factor.extract_runtime_state(parsed, retrieval, "not-json")
    assert unresolved.m0_relation == "m0-unresolved"


def _synthetic_outcomes() -> tuple[factor.FactorTop1Outcome, ...]:
    positive_state = factor.FactorTop1State(
        factor_status="valid-nonempty",
        uncertainty="low",
        m0_relation="m0-known-disagrees",
        ranking_relation="unique-top",
        positive_document_count="two-to-five",
        matched_token_fraction="majority-at-least-one-half",
        nonempty_field_count="three-or-more",
    )
    harmful_state = replace(
        positive_state,
        uncertainty="high",
        matched_token_fraction="minority-below-one-half",
    )
    rows: list[factor.FactorTop1Outcome] = []
    for index in range(10):
        rows.append(
            factor.FactorTop1Outcome(
                sample_id=f"positive-{index:02d}",
                group_id=f"group-{index % 5}",
                state=positive_state,
                supply_available=True,
                top1_gold_tool_correct=True,
                stop_score=_score(0),
                supply_score=_score(1),
            )
        )
        rows.append(
            factor.FactorTop1Outcome(
                sample_id=f"harmful-{index:02d}",
                group_id=f"group-{index % 5}",
                state=harmful_state,
                supply_available=True,
                top1_gold_tool_correct=True,
                stop_score=_score(1),
                supply_score=_score(0),
            )
        )
    return tuple(rows)


def test_crossfit_policy_selects_safe_factor_state_and_contributes_control() -> None:
    screen = factor.screen_candidates(
        _synthetic_outcomes(), resend_absolute_exact_count_difference=0, n_replicates=200
    )
    assert screen.promotion_passed is True
    assert screen.selected_candidate == factor.COARSE_CANDIDATE
    report = screen.reports[screen.selected_candidate]
    assert report.metrics.used == 10
    assert report.metrics.stopped == 10
    assert report.metrics.saved == 10
    assert report.metrics.harmed == 0
    assert report.metrics.net_gain == 10
    assert report.metrics.always_use_net_gain == 0
    assert report.metrics.fold_net_gains == (2, 2, 2, 2, 2)
    assert report.gates["top1_information_gain"] is True
    assert report.gates["control_vs_always_use"] is True


def test_resend_floor_is_a_strict_promotion_gate() -> None:
    screen = factor.screen_candidates(
        _synthetic_outcomes(),
        resend_absolute_exact_count_difference=10,
        n_replicates=200,
    )
    assert screen.promotion_passed is False
    assert all(
        report.gates["gain_exceeds_resend_floor"] is False
        for report in screen.reports.values()
    )


def test_policy_artifact_is_self_hashed_and_fail_closed() -> None:
    outcomes = _synthetic_outcomes()
    screen = factor.screen_candidates(
        outcomes, resend_absolute_exact_count_difference=0, n_replicates=200
    )
    artifact = factor.build_policy_artifact(
        outcomes,
        screen,
        source_hashes={
            "m0": "a" * 64,
            "factors": "b" * 64,
            "main": "c" * 64,
            "resend": "d" * 64,
            "registry": "e" * 64,
        },
        resend_absolute_exact_count_difference=0,
        offline_attempts=0,
    )
    factor.assert_self_hash(artifact)
    factor.assert_policy_admits_support(artifact)
    assert artifact["policy"]["parameter_training"] == "none"
    with pytest.raises(factor.FactorTop1Error, match="outbound"):
        factor.build_policy_artifact(
            outcomes,
            screen,
            source_hashes={
                "m0": "a" * 64,
                "factors": "b" * 64,
                "main": "c" * 64,
                "resend": "d" * 64,
                "registry": "e" * 64,
            },
            resend_absolute_exact_count_difference=0,
            offline_attempts=1,
        )


def test_committed_contract_matches_implementation_constants() -> None:
    contract = json.loads(
        (
            REPO_ROOT
            / "configs/experiment/a2t-training-free-factor-top1-104-v1.json"
        ).read_text(encoding="utf-8")
    )
    assert contract["experiment_id"] == factor.EXPERIMENT_ID
    assert contract["retriever"]["policy_id"] == factor.RETRIEVER_POLICY_ID
    assert contract["retriever"]["k1"] == factor.BM25_K1
    assert contract["retriever"]["b"] == factor.BM25_B
    assert contract["training_free_reward_memory"]["folds"] == factor.N_FOLDS
    assert contract["promotion_gates"]["saved_exact_matches_at_least"] == (
        factor.MIN_SAVED
    )
    assert contract["promotion_gates"]["harmful_uses_at_most"] == factor.MAX_HARMED
    assert contract["resend_control"]["count"] == factor.RESEND_COUNT
