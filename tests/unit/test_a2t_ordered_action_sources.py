from __future__ import annotations

import copy
import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_ordered_action_sources import (
    OrderedActionSourceError,
    project_ordered_action_sources,
)


ALPHA_ID = "tier1_direct:000002"
BETA_ID = "tier3_multi_intent:000007"


def _model_text(*names: str) -> str:
    return json.dumps([{"name": name, "arguments": {}} for name in names])


def _inputs() -> dict[str, object]:
    roster_rows = [
        {"sample_id": BETA_ID, "tier": "tier3_multi_intent", "id": 7, "query_idx": 31},
        {"sample_id": ALPHA_ID, "tier": "tier1_direct", "id": 2, "query_idx": 12},
    ]
    entries_by_tier = {
        "tier1_direct": [
            {
                "id": 2,
                "query_idx": 12,
                "tool_name": "alpha",
                "expected_tool_call": "alpha()",
                "extracted_params": {},
                "additional_tool_calls": None,
            },
            # An unselected row may be malformed gold. The helper must never parse it.
            {"id": 99, "query_idx": 99, "tool_name": None},
        ],
        "tier3_multi_intent": {
            7: {
                "id": 7,
                "query_idx": 31,
                "tool_name": "beta",
                "expected_tool_call": "beta(); beta()",
                "extracted_params": {},
                "additional_tool_calls": ["gamma(); beta()"],
            }
        },
    }
    direct_output_rows = [
        {"sample_id": ALPHA_ID, "text": "No tool call."},
        {"sample_id": BETA_ID, "text": _model_text("beta", "gamma", "beta", "beta")},
    ]
    system_output_rows = [
        {"sample_id": BETA_ID, "text": _model_text("beta", "beta", "gamma", "beta")},
        {"sample_id": ALPHA_ID, "text": _model_text("alpha")},
    ]
    direct_official_rows = [
        {
            "sample_id": BETA_ID,
            "tier": "tier3_multi_intent",
            "gold_tool": "beta",
            "num_expected_tools": 2,
        },
        {
            "sample_id": ALPHA_ID,
            "tier": "tier1_direct",
            "gold_tool": "alpha",
            "num_expected_tools": 1,
        },
    ]
    system_official_rows = copy.deepcopy(direct_official_rows)
    direct_v2_rows = [
        {
            "sample_id": ALPHA_ID,
            "tier": "tier1_direct",
            "parsed": False,
            "tool_accuracy": 0.0,
            "tool_accuracy_multiset": 0.0,
        },
        {
            "sample_id": BETA_ID,
            "tier": "tier3_multi_intent",
            "parsed": True,
            "tool_accuracy": 0.0,
            "tool_accuracy_multiset": 1.0,
        },
    ]
    system_v2_rows = [
        {
            "sample_id": BETA_ID,
            "tier": "tier3_multi_intent",
            "parsed": True,
            "tool_accuracy": 1.0,
            "tool_accuracy_multiset": 1.0,
        },
        {
            "sample_id": ALPHA_ID,
            "tier": "tier1_direct",
            "parsed": True,
            "tool_accuracy": 1.0,
            "tool_accuracy_multiset": 1.0,
        },
    ]
    return {
        "roster_rows": roster_rows,
        "entries_by_tier": entries_by_tier,
        "direct_output_rows": direct_output_rows,
        "system_output_rows": system_output_rows,
        "direct_official_rows": direct_official_rows,
        "system_official_rows": system_official_rows,
        "direct_v2_rows": direct_v2_rows,
        "system_v2_rows": system_v2_rows,
    }


def _project(inputs: dict[str, object]) -> list[dict[str, object]]:
    return project_ordered_action_sources(**inputs)  # type: ignore[arg-type]


def test_projects_sorted_sequences_flags_and_distinct_expected_counts_without_mutation():
    inputs = _inputs()
    before = copy.deepcopy(inputs)

    rows = _project(inputs)

    assert inputs == before
    assert rows == [
        {
            "sample_id": ALPHA_ID,
            "tier": "tier1_direct",
            "expected_tool_names": ["alpha"],
            "direct_predicted_tool_names": [],
            "system_predicted_tool_names": ["alpha"],
            "direct_parsed": False,
            "system_parsed": True,
            "official_expected_count": 1,
            "expanded_expected_count": 1,
        },
        {
            "sample_id": BETA_ID,
            "tier": "tier3_multi_intent",
            "expected_tool_names": ["beta", "beta", "gamma", "beta"],
            "direct_predicted_tool_names": ["beta", "gamma", "beta", "beta"],
            "system_predicted_tool_names": ["beta", "beta", "gamma", "beta"],
            "direct_parsed": True,
            "system_parsed": True,
            "official_expected_count": 2,
            "expanded_expected_count": 4,
        },
    ]


@pytest.mark.parametrize(
    "collection_name",
    [
        "direct_output_rows",
        "system_output_rows",
        "direct_official_rows",
        "system_official_rows",
        "direct_v2_rows",
        "system_v2_rows",
    ],
)
@pytest.mark.parametrize("fault", ["missing", "extra", "duplicate"])
def test_rejects_nonexact_or_duplicate_sample_id_sets(collection_name: str, fault: str):
    inputs = _inputs()
    rows = list(inputs[collection_name])  # type: ignore[arg-type]
    if fault == "missing":
        rows.pop()
    elif fault == "extra":
        rows.append({"sample_id": "tier8_intent_blending:999999"})
    else:
        rows.append(copy.deepcopy(rows[0]))
    inputs[collection_name] = rows

    with pytest.raises(OrderedActionSourceError, match=collection_name):
        _project(inputs)


@pytest.mark.parametrize(
    ("target", "field", "value", "message"),
    [
        ("direct_official_rows", "gold_tool", "wrong", "gold_tool"),
        ("system_official_rows", "num_expected_tools", 9, "expected count"),
        ("direct_v2_rows", "parsed", False, "parsed"),
        ("system_v2_rows", "tool_accuracy", 0.0, "ordered"),
        ("direct_v2_rows", "tool_accuracy_multiset", 0.0, "multiset"),
    ],
)
def test_rejects_persisted_score_contradictions(
    target: str, field: str, value: object, message: str
):
    inputs = _inputs()
    rows = copy.deepcopy(inputs[target])
    assert isinstance(rows, list)
    beta = next(row for row in rows if row["sample_id"] == BETA_ID)
    beta[field] = value
    inputs[target] = rows

    with pytest.raises(OrderedActionSourceError, match=message):
        _project(inputs)


def test_rejects_roster_manifest_query_association_mismatch():
    inputs = _inputs()
    roster = copy.deepcopy(inputs["roster_rows"])
    assert isinstance(roster, list)
    roster[0]["query_idx"] = 32
    inputs["roster_rows"] = roster

    with pytest.raises(OrderedActionSourceError, match="query_idx"):
        _project(inputs)


@pytest.mark.parametrize(
    "roster_mutation",
    [
        lambda rows: rows + [copy.deepcopy(rows[0])],
        lambda rows: [{**rows[0], "sample_id": "tier3_multi_intent:000008"}, *rows[1:]],
        lambda rows: [{**rows[0], "id": True}, *rows[1:]],
    ],
)
def test_rejects_duplicate_or_internally_inconsistent_roster(roster_mutation):
    inputs = _inputs()
    inputs["roster_rows"] = roster_mutation(copy.deepcopy(inputs["roster_rows"]))

    with pytest.raises(OrderedActionSourceError, match="roster"):
        _project(inputs)


def test_rejects_missing_text_and_nonbinary_v2_fields():
    inputs = _inputs()
    outputs = copy.deepcopy(inputs["direct_output_rows"])
    assert isinstance(outputs, list)
    outputs[0].pop("text")
    inputs["direct_output_rows"] = outputs
    with pytest.raises(OrderedActionSourceError, match="text"):
        _project(inputs)

    inputs = _inputs()
    scores = copy.deepcopy(inputs["direct_v2_rows"])
    assert isinstance(scores, list)
    scores[0]["tool_accuracy"] = 0.5
    inputs["direct_v2_rows"] = scores
    with pytest.raises(OrderedActionSourceError, match="binary"):
        _project(inputs)
