import json

import pytest

from speech_aware_evidence_acquisition.reproduction.slurp_delivery import (
    DeliveryJoinError,
    join_slurp_rosters,
)


def row(sample_id, text):
    return {"sample_id": sample_id, "text": text}


def test_join_is_sorted_predecessor_authoritative_and_byte_stable():
    arm = [
        row("b", '{"entities": [{"type": "city", "filler": "München"}]}'),
        row("a", '{"scenario": "arm", "action": "wrong", "entities": []}'),
    ]
    predecessor = [
        row("a", '{"scenario": "music", "action": "play", "entities": []}'),
        row("b", '{"scenario": "calendar", "action": "set", "entities": []}'),
    ]

    projected, stats = join_slurp_rosters(arm, predecessor)

    assert [item["sample_id"] for item in projected] == ["a", "b"]
    assert [item["text"] for item in projected] == [
        '{"action": "play", "entities": [], "scenario": "music"}',
        '{"action": "set", "entities": [{"filler": "München", "type": "city"}], "scenario": "calendar"}',
    ]
    assert stats == {
        "rows": 2,
        "arm_response_unparsed": 0,
        "arm_response_carried_scenario_or_action": 1,
        "closed_list_unparsed": 0,
    }
    assert arm[0]["text"] == '{"entities": [{"type": "city", "filler": "München"}]}'


def test_join_preserves_historical_stats_for_malformed_and_extra_labels():
    arm = [
        row("a", "not json"),
        row("b", '{"scenario": "extra", "entities": []}'),
    ]
    predecessor = [
        row("a", '{"scenario": "music", "action": "play"}'),
        row("b", '{"scenario": "calendar", "action": "set"}'),
    ]

    projected, stats = join_slurp_rosters(arm, predecessor)

    assert stats == {
        "rows": 2,
        "arm_response_unparsed": 1,
        "arm_response_carried_scenario_or_action": 1,
        "closed_list_unparsed": 0,
    }
    assert json.loads(projected[0]["text"]) == {
        "scenario": "music",
        "action": "play",
        "entities": [],
    }
    assert json.loads(projected[1]["text"]) == {
        "scenario": "calendar",
        "action": "set",
        "entities": [],
    }


@pytest.mark.parametrize(
    ("arm", "predecessor"),
    [
        ([], [row("a", "{}")]),
        ([row("a", "{}")], []),
        ([row("a", "{}"), row("a", "{}")], [row("a", "{}")]),
        ([row("a", "{}")], [row("a", "{}"), row("a", "{}")]),
        ([row("", "{}")], [row("a", "{}")]),
        ([{"sample_id": "a"}], [row("a", "{}")]),
        ([row("a", "{}")], [row("b", "{}")]),
        ([row("a", "{}"), row("b", "{}")], [row("a", "{}")]),
    ],
)
def test_join_rejects_invalid_or_non_total_rosters(arm, predecessor):
    with pytest.raises(DeliveryJoinError):
        join_slurp_rosters(arm, predecessor)


def test_join_rejects_non_mapping_rows_and_non_string_ids():
    with pytest.raises(DeliveryJoinError):
        join_slurp_rosters([1], [row("a", "{}")])
    with pytest.raises(DeliveryJoinError):
        join_slurp_rosters([{"sample_id": 1, "text": "{}"}], [row("a", "{}")])


def test_historical_wrapper_keeps_jsonl_bytes(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "slurp_kc_s1_read", "scripts/slurp_kc_s1_read.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    arm = [row("z", '{"entities": [{"type": "city", "filler": "München"}]}')]
    predecessor = [row("z", '{"scenario": "music", "action": "play"}')]
    output, stats = module.project_joined(arm, predecessor, tmp_path / "joined.jsonl")

    payload = {
        "sample_id": "z",
        "text": json.dumps(
            {
                "scenario": "music",
                "action": "play",
                "entities": [{"type": "city", "filler": "München"}],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    }
    expected = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + chr(10)).encode("utf-8")
    assert output.read_bytes() == expected
    assert stats["rows"] == 1



def test_single_response_join_matches_roster_bytes_and_diagnostics():
    from speech_aware_evidence_acquisition.reproduction.slurp_delivery import (
        join_slurp_response,
    )

    direct = '{"scenario": "music", "action": "play", "entities": []}'
    slots = '{"scenario": "wrong", "entities": [{"type": "city", "filler": "München"}]}'
    expected_text, expected_stats = join_slurp_response(direct, slots)
    projected, stats = join_slurp_rosters(
        [row("sample", slots)], [row("sample", direct)]
    )

    assert projected == [{"sample_id": "sample", "text": expected_text}]
    assert stats == expected_stats


def test_single_response_join_malformed_labels_fail_closed():
    from speech_aware_evidence_acquisition.reproduction.slurp_delivery import (
        join_slurp_response,
    )

    text, diagnostics = join_slurp_response("not json", '{"scenario": "extra"}')
    assert json.loads(text) == {"scenario": "", "action": "", "entities": []}
    assert diagnostics == {
        "rows": 1,
        "arm_response_unparsed": 0,
        "arm_response_carried_scenario_or_action": 1,
        "closed_list_unparsed": 1,
    }


def test_live_delivery_postprocessor_is_registered_and_has_no_sealed_dependency():
    from speech_aware_evidence_acquisition.core import policies  # noqa: F401
    from speech_aware_evidence_acquisition.core.base import RESPONSE_POSTPROCESSORS

    rule_factory = RESPONSE_POSTPROCESSORS.resolve("slurp-intent-slots-delivery-v1")
    from speech_aware_evidence_acquisition.core.delivery import deliver_terminal_response

    result = deliver_terminal_response(
        '{"scenario": "music", "action": "play"}',
        '{"entities": [{"type": "city", "filler": "München"}]}',
        rule=rule_factory(),
    )
    assert result.refusal_reason is None
    assert result.diagnostics["rows"] == 1
    assert json.loads(result.text) == {
        "scenario": "music",
        "action": "play",
        "entities": [{"type": "city", "filler": "München"}],
    }


def test_live_phase_program_and_baselines_are_config_only():
    from pathlib import Path
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )

    program = default_phase_program("phase-direct-then-slots-v1")
    assert program.phase_names() == ("direct", "slots")
    assert program.phase("direct").barrier is True
    assert program.phase("slots").barrier is False
    assert program.max_contacts == 2
    assert program.stop_rule == "always-run-full-program"

    root = Path(__file__).parents[2]
    live = json.loads(
        (root / "configs/baseline/slurp-phase-live-intent-slots-schema-v1.json").read_text()
    )
    control = json.loads(
        (root / "configs/baseline/slurp-phase-live-direct-control-v1.json").read_text()
    )
    assert live["serving_slots"] == control["serving_slots"] == 4
    assert live["serving_slot_tokens"] == control["serving_slot_tokens"] == 16384
    assert live["phase_material"]["slots"]["predecessor_binding"] == "append-sealed-state"
    assert "predecessor_source" not in live["phase_material"]["slots"]
    assert live["knowledge_snapshot_sha256"] == control["knowledge_snapshot_sha256"]
    assert control["policy"] == "phase-direct-only-v1"
    assert live["policy"] == "phase-direct-then-slots-v1"
    assert "output_cap" not in live and "experiment_cell" not in live
    assert "response_postprocessor" not in live
    assert "delivery_basis" in live


def test_joint_hypothesis_delivery_takes_all_fields_from_final_answer():
    from speech_aware_evidence_acquisition.reproduction.slurp_delivery import (
        slurp_joint_hypothesis_delivery_rule,
    )

    predecessor = json.dumps({
        "schema": "saea-slurp-intent-hypotheses-v1",
        "semantics": "ranked-mutually-exclusive-intent-alternatives",
        "sample_id": "slurp:devel:0001",
        "candidates": [
            {"intent_id": "weather_query", "distinction": "Weather request.",
             "evidence_refs": [], "unresolved_fields": ["location"]},
            {"intent_id": "transport_taxi", "distinction": "Taxi request.",
             "evidence_refs": [], "unresolved_fields": ["destination"]},
        ],
    }, sort_keys=True)
    final = json.dumps({
        "scenario": "transport", "action": "taxi",
        "entities": [{"type": "destination", "filler": "the station"}],
    })

    result = slurp_joint_hypothesis_delivery_rule(
        predecessor, final,
        legal_intent_ids={"weather_query", "transport_taxi", "calendar_set"},
        max_candidates=3,
    )

    assert result.refusal_reason is None
    assert json.loads(result.text) == json.loads(final)
    assert result.diagnostics == {
        "rows": 1,
        "hypothesis_state_invalid": 0,
        "final_response_unparsed": 0,
        "final_intent_illegal": 0,
        "final_intent_outside_shortlist": 0,
        "final_authoritative": 1,
    }


@pytest.mark.parametrize(
    "final, reason",
    [
        ("", "empty_response"),
        ("not json", "malformed_final_response"),
        (
            '{"scenario":"transport","action":"taxi",'
            '"entities":[{"type":"destination"}]}',
            "malformed_final_response",
        ),
        (
            '{"scenario":"weather","scenario":"transport","action":"taxi",'
            '"entities":[]}',
            "malformed_final_response",
        ),
        ('{"scenario": "illegal", "action": "pair", "entities": []}', "illegal_final_intent"),
    ],
)
def test_joint_hypothesis_delivery_never_falls_back_to_predecessor(final, reason):
    from speech_aware_evidence_acquisition.reproduction.slurp_delivery import (
        slurp_joint_hypothesis_delivery_rule,
    )

    predecessor = json.dumps({
        "schema": "saea-slurp-intent-hypotheses-v1",
        "semantics": "ranked-mutually-exclusive-intent-alternatives",
        "sample_id": "slurp:devel:0001",
        "candidates": [
            {"intent_id": "weather_query", "distinction": "Weather request.",
             "evidence_refs": [], "unresolved_fields": ["location"]},
            {"intent_id": "transport_taxi", "distinction": "Taxi request.",
             "evidence_refs": [], "unresolved_fields": ["destination"]},
        ],
    }, sort_keys=True)
    result = slurp_joint_hypothesis_delivery_rule(
        predecessor, final,
        legal_intent_ids={"weather_query", "transport_taxi", "calendar_set"},
        max_candidates=3,
    )

    assert result.refusal_reason == reason
    assert result.text == final
    assert result.text != predecessor


def test_joint_delivery_accepts_a_legal_escape_outside_shortlist():
    from speech_aware_evidence_acquisition.reproduction.slurp_delivery import (
        slurp_joint_hypothesis_delivery_rule,
    )

    predecessor = json.dumps({
        "schema": "saea-slurp-intent-hypotheses-v1",
        "semantics": "ranked-mutually-exclusive-intent-alternatives",
        "sample_id": "s",
        "candidates": [
            {"intent_id": "weather_query", "distinction": "Weather request.",
             "evidence_refs": [], "unresolved_fields": []},
            {"intent_id": "transport_taxi", "distinction": "Taxi request.",
             "evidence_refs": [], "unresolved_fields": []},
        ],
    }, sort_keys=True)
    result = slurp_joint_hypothesis_delivery_rule(
        predecessor,
        '{"scenario": "calendar", "action": "set", "entities": []}',
        legal_intent_ids={"weather_query", "transport_taxi", "calendar_set"},
        max_candidates=2,
    )
    assert result.refusal_reason is None
    assert result.diagnostics["final_intent_outside_shortlist"] == 1


def test_joint_hypothesis_delivery_is_registered_separately():
    from speech_aware_evidence_acquisition.core import policies  # noqa: F401
    from speech_aware_evidence_acquisition.core.base import RESPONSE_POSTPROCESSORS

    assert RESPONSE_POSTPROCESSORS.resolve("slurp-joint-hypothesis-delivery-v1")


def test_joint_delivery_accepts_real_multiline_json_fence_and_rejects_fenced_duplicates():
    from speech_aware_evidence_acquisition.reproduction.slurp_delivery import (
        slurp_joint_hypothesis_delivery_rule,
    )

    predecessor = json.dumps({
        "schema": "saea-slurp-intent-hypotheses-v1",
        "semantics": "ranked-mutually-exclusive-intent-alternatives",
        "sample_id": "s",
        "candidates": [
            {"intent_id": "transport_taxi", "distinction": "Taxi request.",
             "evidence_refs": [], "unresolved_fields": []},
        ],
    }, sort_keys=True)
    legal = {"transport_taxi"}

    fenced = """  ```json
      {"scenario": "transport", "action": "taxi", "entities": []}
    ```  """
    accepted = slurp_joint_hypothesis_delivery_rule(
        predecessor, fenced, legal_intent_ids=legal, max_candidates=1
    )
    assert accepted.refusal_reason is None
    assert json.loads(accepted.text) == {
        "scenario": "transport", "action": "taxi", "entities": []
    }

    duplicated = """```json
    {"scenario": "weather", "scenario": "transport",
     "action": "taxi", "entities": []}
    ```"""
    refused = slurp_joint_hypothesis_delivery_rule(
        predecessor, duplicated, legal_intent_ids=legal, max_candidates=1
    )
    assert refused.refusal_reason == "malformed_final_response"
    assert refused.diagnostics["final_authoritative"] == 0
