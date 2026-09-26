"""Generated slot-value edits preserve routing and construction lineage."""

import copy

import pytest

from speech_aware_evidence_acquisition.rails import semantic_knowledge_edits as edits
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_slot_contract_snapshot,
)


def rows():
    return [
        {
            "slot_id": "date",
            "intent_bindings": [
                {
                    "intent_id": "datetime_query",
                    "semantic_role": "Requested date scope.",
                }
            ],
            "extraction_cues": ["Extract the spoken date expression."],
            "admissible_formats": ["Spoken surface form."],
            "missing_behavior": "Omit when absent.",
            "ambiguity_behavior": "Preserve uncertainty.",
            "limitations": ["No invented dates."],
            "source_support": {
                "source_sample_ids": ["slurp:train:base"],
                "provenance_refs": ["fixture-base"],
            },
        }
    ]


def contract(base):
    return edits.slot_value_edit_contract(
        base,
        slot_ids=["date"],
        fields=["extraction_cues", "missing_behavior"],
        evidence_groups={"g1": ["slurp:train:new"], "g2": ["slurp:train:tie"]},
        max_edits=2,
        max_field_chars=300,
    )


def proposal(base):
    return {
        "schema": edits.PROPOSAL_SCHEMA,
        "base_rows_sha256": content_hash(base),
        "edits": [
            {
                "slot_id": "date",
                "field": "extraction_cues",
                "previous_value_sha256": content_hash(base[0]["extraction_cues"]),
                "replacement": ["Retain the full date expression supported by speech."],
                "evidence_group_ids": ["g1"],
            }
        ],
    }


def apply(base, prop=None, spec=None):
    return edits.apply_slot_value_edits(
        base,
        proposal(base) if prop is None else prop,
        contract=contract(base) if spec is None else spec,
        verified_generation_ref="artifact-run:" + "1" * 64,
    )


def test_value_edit_reuses_existing_builder_without_changing_routing_or_base():
    base = rows()
    original = copy.deepcopy(base)
    result = apply(base)
    assert base == original
    changed = result["rows"]
    assert changed[0]["intent_bindings"] == base[0]["intent_bindings"]
    assert changed[0]["extraction_cues"] != base[0]["extraction_cues"]
    assert set(changed[0]["source_support"]["source_sample_ids"]) == {
        "slurp:train:base",
        "slurp:train:new",
        "slurp:train:tie",
    }

    def build(rs):
        ids = tuple(
            sorted(
                {s for row in rs for s in row["source_support"]["source_sample_ids"]}
            )
        )
        return build_slot_contract_snapshot(
            AuthoredSemanticKnowledgeSpec("slurp", "2" * 64, ids),
            rows=rs,
        )

    old, new = build(base), build(changed)
    assert old.facets[0].representation == new.facets[0].representation
    assert old.values[0].associated_facet_ids == new.values[0].associated_facet_ids
    assert old.values[0].content != new.values[0].content
    assert result["admission"] == "candidate-only"
    assert result["optimizer_construction_sample_ids"] == [
        "slurp:train:new",
        "slurp:train:tie",
    ]


def test_no_change_preserves_rows_but_keeps_optimizer_exposure():
    base = rows()
    p = proposal(base)
    p["edits"] = []
    result = apply(base, p)
    assert result["rows"] == base
    assert result["changed_fields"] == []
    assert result["optimizer_construction_sample_ids"]


@pytest.mark.parametrize(
    "change",
    [
        "base",
        "stale",
        "binding",
        "slot",
        "unhashable-slot",
        "group",
        "extra",
        "duplicate",
        "too-long",
        "blank",
        "wrong-type",
        "non-english-script",
    ],
)
def test_bad_generated_edits_are_rejected_atomically(change):
    base = rows()
    before = copy.deepcopy(base)
    p = proposal(base)
    e = p["edits"][0]
    if change == "base":
        p["base_rows_sha256"] = "0" * 64
    elif change == "stale":
        e["previous_value_sha256"] = "0" * 64
    elif change == "binding":
        e["field"] = "intent_bindings"
    elif change == "slot":
        e["slot_id"] = "unknown"
    elif change == "unhashable-slot":
        e["slot_id"] = ["date"]
    elif change == "group":
        e["evidence_group_ids"] = ["future"]
    elif change == "extra":
        p["gold_label"] = "forbidden"
    elif change == "duplicate":
        p["edits"].append(copy.deepcopy(e))
    elif change == "too-long":
        e["replacement"] = ["x" * 301]
    elif change == "blank":
        e["replacement"] = [" "]
    elif change == "wrong-type":
        e["replacement"] = "string instead of list"
    else:
        e["replacement"] = ["\u65e5\u671f"]
    with pytest.raises(ValueError):
        apply(base, p)
    assert base == before


def test_training_scope_rejects_future_split_and_unused_edit_route():
    with pytest.raises(ValueError):
        edits.slot_value_edit_contract(
            rows(),
            slot_ids=["date"],
            fields=["intent_bindings"],
            evidence_groups={"g1": ["slurp:train:new"]},
            max_edits=1,
            max_field_chars=100,
        )
    with pytest.raises(ValueError):
        edits.slot_value_edit_contract(
            rows(),
            slot_ids=["date"],
            fields=["missing_behavior"],
            evidence_groups={"g1": ["slurp:test:future"]},
            max_edits=1,
            max_field_chars=100,
        )


def test_output_schema_binds_exact_fields_previous_values_and_group_ids():
    base = rows()
    schema = edits.slot_value_edit_response_format(contract(base))["json_schema"][
        "schema"
    ]
    assert schema["properties"]["base_rows_sha256"] == {"const": content_hash(base)}
    branches = schema["properties"]["edits"]["items"]["oneOf"]
    assert len(branches) == 2
    assert {b["properties"]["field"]["const"] for b in branches} == {
        "extraction_cues",
        "missing_behavior",
    }
    assert all(
        b["properties"]["evidence_group_ids"]["items"]["enum"] == ["g1", "g2"]
        for b in branches
    )
