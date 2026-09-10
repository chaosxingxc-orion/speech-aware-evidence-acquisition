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
