"""Tests for the preregistered Audio2Tool schema-risk memory screen."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_schema_risk_memory as risk,
)
from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_self_consistency as selfcon,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ItemScore


REGISTRY = (
    {
        "tool_id": "1",
        "domain": "home",
        "category": "climate",
        "tool_name": "setFanMode",
        "signature": "setFanMode(deviceId: String, mode: FanMode, speed: Int?)",
        "description": "Set fan mode.",
        "argument_defaults": "deviceId=fan; mode=Auto",
        "argument_constraints": "mode: [Auto, On, Off], speed: [1-10]",
    },
    {
        "tool_id": "2",
        "domain": "vehicle",
        "category": "comfort",
        "tool_name": "setPetComfortMode",
        "signature": "setPetComfortMode(enabled: Boolean, targetTemp: Float)",
        "description": "Set pet comfort.",
        "argument_defaults": "enabled=True; targetTemp=22.0",
        "argument_constraints": "enabled: [True, False], targetTemp: [15.0-28.0]",
    },
    {
        "tool_id": "3",
        "domain": "vehicle",
        "category": "security",
        "tool_name": "setValetMode",
        "signature": "setValetMode(enabled: Boolean, pin: Int?)",
        "description": "Set valet mode.",
        "argument_defaults": "enabled=True",
        "argument_constraints": "enabled: [True, False], pin: [0000-9999]",
    },
    {
        "tool_id": "4",
        "domain": "home",
        "category": "lighting",
        "tool_name": "setColor",
        "signature": "setColor(deviceId: String, color: HsbColor)",
        "description": "Set light color.",
        "argument_defaults": "deviceId=lamp",
        "argument_constraints": "color: [Hue:0-360, Sat:0-100, Bri:0-100]",
    },
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _response(name: str, arguments: dict[str, object]) -> str:
    import json

    return json.dumps([{"name": name, "arguments": arguments}])


def _score(exact: int, tool: int | None = None) -> ItemScore:
    tool_value = exact if tool is None else tool
    return ItemScore(
        tool_accuracy=float(tool_value),
        exact_match=float(exact),
        slot_true_positives=exact,
        slot_expected_total=1,
        slot_predicted_total=1,
    )


def test_signature_parser_distinguishes_required_optional_and_generic_types() -> None:
    schema = risk.parse_pseudo_signature(
        "startCleaning(deviceId: String, zones: List<String>?, options: Map?)"
    )
    assert schema is not None
    assert schema.tool_name == "startCleaning"
    assert [(item.name, item.type_name, item.optional) for item in schema.parameters] == [
        ("deviceId", "String", False),
        ("zones", "List<String>", True),
        ("options", "Map", True),
    ]
    assert risk.parse_pseudo_signature("broken(x Int)") is None
    assert risk.parse_pseudo_signature("dup(x: Int, x: Int)") is None


def test_constraint_parser_handles_enums_ranges_negatives_and_ambiguity() -> None:
    constraints = risk.parse_argument_constraints(
        "mode: [Auto, On, Off], level: [1-10], offset: [-5.0 - 5.0], pin: [0000-9999]"
    )
    assert constraints["mode"].kind == "enum"
    assert constraints["mode"].enum_values == ("Auto", "On", "Off")
    assert constraints["level"].numeric_range == (1.0, 10.0)
    assert constraints["offset"].numeric_range == (-5.0, 5.0)
    assert constraints["pin"].numeric_range == (0.0, 9999.0)
    compound = risk.parse_argument_constraints(
        "color: [Hue:0-360, Sat:0-100, Bri:0-100]"
    )
    assert compound["color"].kind == "uncheckable"
    assert risk.parse_argument_constraints("not a clause") == {}


def test_response_risk_accepts_optional_omission_and_valid_constraints() -> None:
    state = risk.extract_response_risk(
        _response("setFanMode", {"deviceId": "fan-1", "mode": "Auto"}), REGISTRY
    )
    assert state.required_key_coverage == "complete"
    assert state.unknown_key_status == "none"
    assert state.type_status == "valid"
    assert state.constraint_status == "valid"
    assert state.violation_count == 0
    assert state.risk_class == "schema-clean"


@pytest.mark.parametrize(
    ("response", "expected_class", "expected_count"),
    [
        (_response("setFanMode", {"mode": "Auto"}), "missing-required", 1),
        (
            _response(
                "setFanMode", {"deviceId": "fan", "mode": "Auto", "ghost": 1}
            ),
            "extra-key",
            1,
        ),
        (
            _response("setPetComfortMode", {"enabled": "yes", "targetTemp": 22.0}),
            "type-invalid",
            1,
        ),
        (
            _response("setPetComfortMode", {"enabled": True, "targetTemp": 40.0}),
            "constraint-invalid",
            1,
        ),
    ],
)
def test_response_risk_separates_violation_channels(
    response: str, expected_class: str, expected_count: int
) -> None:
    state = risk.extract_response_risk(response, REGISTRY)
    assert state.risk_class == expected_class
    assert state.violation_count == expected_count


def test_uncheckable_constraint_is_not_mislabeled_invalid() -> None:
    state = risk.extract_response_risk(
        _response("setColor", {"deviceId": "lamp", "color": "blue"}), REGISTRY
    )
    assert state.constraint_status == "unresolved"
    assert state.violation_count == 0
    assert state.risk_class == "schema-clean"


def test_pair_state_is_order_duplicate_registry_and_consistent_rename_invariant() -> None:
    import json

    first = json.dumps(
        [
            {"name": "setFanMode", "arguments": {"deviceId": "fan", "mode": "Auto"}},
            {"name": "setValetMode", "arguments": {"enabled": True}},
        ]
    )
    second = _response("setFanMode", {"deviceId": "fan", "mode": "Auto", "speed": 99})
    reference = risk.extract_schema_risk_state(first, second, REGISTRY)
    reordered = json.dumps(list(reversed(json.loads(first))) + [json.loads(first)[0]])
    assert risk.extract_schema_risk_state(reordered, second, tuple(reversed(REGISTRY))) == reference

    renamed_registry = tuple(
        {
            **row,
            "tool_name": f"renamed_{row['tool_id']}",
            "signature": row["signature"].replace(
                row["tool_name"], f"renamed_{row['tool_id']}", 1
            ),
        }
        for row in REGISTRY
    )
    name_map = {row["tool_name"]: f"renamed_{row['tool_id']}" for row in REGISTRY}

    def rename_response(value: str) -> str:
        rows = json.loads(value)
        for row in rows:
            row["name"] = name_map[row["name"]]
        return json.dumps(rows)

    assert risk.extract_schema_risk_state(
        rename_response(first), rename_response(second), renamed_registry
    ) == reference


def test_pair_state_reports_lower_risk_and_fails_closed_on_invalid_json() -> None:
    risky = _response("setFanMode", {"mode": "Auto"})
    clean = _response("setFanMode", {"deviceId": "fan", "mode": "Auto"})
    state = risk.extract_schema_risk_state(risky, clean, REGISTRY)
    assert state.risk_relation == "observation-lower"
    assert state.m0.risk_class == "missing-required"
    invalid = risk.extract_schema_risk_state("not-json", clean, REGISTRY)
    assert invalid.risk_relation == "unresolved"
    assert invalid.m0.risk_class == "invalid-json"


def test_augment_outcomes_preserves_rewards_and_supply_availability() -> None:
    base = selfcon.SelfConsistencyOutcome(
        sample_id="tier1:000001",
        group_id="g1",
        state=selfcon.extract_self_consistency_state("[]", "[]"),
        supply_available=True,
        stop_score=_score(0, 1),
        supply_score=_score(1, 1),
    )
    augmented = risk.augment_outcomes(
        (base,),
        {base.sample_id: _response("setFanMode", {"mode": "Auto"})},
        {base.sample_id: _response("setFanMode", {"deviceId": "fan", "mode": "Auto"})},
        REGISTRY,
    )
    assert len(augmented) == 1
    assert augmented[0].delta == 1
    assert augmented[0].supply_available is True
    assert augmented[0].stop_score == base.stop_score
    assert augmented[0].state.risk_relation == "observation-lower"


def _synthetic_outcomes() -> tuple[risk.SchemaRiskOutcome, ...]:
    positive_state = risk.extract_schema_risk_state(
        _response("setFanMode", {"mode": "Auto"}),
        _response("setFanMode", {"deviceId": "fan", "mode": "Auto"}),
        REGISTRY,
    )
    negative_state = risk.extract_schema_risk_state(
        _response("setPetComfortMode", {"enabled": True, "targetTemp": 40.0}),
        _response("setPetComfortMode", {"enabled": True, "targetTemp": 40.0}),
        REGISTRY,
    )
    rows: list[risk.SchemaRiskOutcome] = []
    for index in range(10):
        rows.append(
            risk.SchemaRiskOutcome(
                sample_id=f"positive-{index:02d}",
                group_id=f"group-{index % 5}",
                state=positive_state,
                supply_available=True,
                stop_score=_score(0, 1),
                supply_score=_score(1, 1),
            )
        )
        rows.append(
            risk.SchemaRiskOutcome(
                sample_id=f"negative-{index:02d}",
                group_id=f"group-{index % 5}",
                state=negative_state,
                supply_available=True,
                stop_score=_score(1, 1),
                supply_score=_score(0, 0),
            )
        )
    return tuple(rows)


def test_crossfit_screen_can_select_safe_schema_risk_cell() -> None:
    screen = risk.screen_candidates(_synthetic_outcomes(), n_replicates=200)
    assert screen.promotion_passed is True
    assert screen.selected_candidate == risk.COARSE_CANDIDATE
    selected = screen.reports[screen.selected_candidate]
    assert selected.metrics.supplied == 10
    assert selected.metrics.saved == 10
    assert selected.metrics.harmed == 0
    assert selected.metrics.fold_net_gains == (2, 2, 2, 2, 2)


def test_policy_artifact_is_self_hashed_and_fail_closed() -> None:
    outcomes = _synthetic_outcomes()
    screen = risk.screen_candidates(outcomes, n_replicates=200)
    hashes = {"m0": "a" * 64, "repeat": "b" * 64, "supply": "c" * 64}
    artifact = risk.build_policy_artifact(
        outcomes, screen, source_hashes=hashes, offline_attempts=0
    )
    risk.assert_self_hash(artifact)
    risk.assert_policy_admits_support(artifact)
    assert artifact["execution_profile"] == "model-free-check"
    assert artifact["policy"]["parameter_training"] == "none"
    with pytest.raises(risk.SchemaRiskError, match="outbound"):
        risk.build_policy_artifact(
            outcomes, screen, source_hashes=hashes, offline_attempts=1
        )
    with pytest.raises(risk.SchemaRiskError, match="self hash"):
        risk.assert_self_hash({**artifact, "promotion_passed": False})
    negative = replace(screen, selected_candidate=None, promotion_passed=False)
    negative_artifact = risk.build_policy_artifact(
        outcomes, negative, source_hashes=hashes, offline_attempts=0
    )
    with pytest.raises(risk.SchemaRiskError, match="did not pass"):
        risk.assert_policy_admits_support(negative_artifact)


def test_committed_preregistration_matches_implementation_constants() -> None:
    contract = json.loads(
        (
            REPO_ROOT
            / "configs/experiment/a2t-training-free-schema-risk-memory-v1.json"
        ).read_text(encoding="utf-8")
    )
    assert contract["experiment_id"] == risk.EXPERIMENT_ID
    assert tuple(contract["runtime_state"]["candidates"]) == risk.CANDIDATE_IDS
    assert contract["memory_policy"]["default_action"] == selfcon.STOP_M0
    assert contract["promotion_gates"]["saved_exact_matches_at_least"] == selfcon.MIN_SAVED
    assert contract["promotion_gates"]["harmful_supplies_at_most"] == selfcon.MAX_HARMED
    assert contract["contacts"] == {
        "frozen_core": 0,
        "embedding_tool": 0,
        "tokenizer": 0,
        "http_or_socket": 0,
        "audio_seconds": 0,
        "gpu_hours": 0.0,
    }
