"""Value-only construction contracts over unchanged TRAIN retrieval keys."""

from dataclasses import replace
import json
import pytest
from test_knowledge_build_slot_filler_view import _rows
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    KnowledgeBuildSpec, build_knowledge_snapshot,
)
from speech_aware_evidence_acquisition.rails.knowledge_value_views import KnowledgeValueRenderer


def build(value_format="historical", rows=None):
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp", dimensions=("content",),
            view="slot-fillers", value_format=value_format,
        ),
        rows=_rows() if rows is None else rows, forbidden_sample_ids=frozenset(),
    )


@pytest.mark.parametrize("mode", ["typed-fillers", "slot-type-set", "intent-slot-frame"])
def test_only_value_content_and_snapshot_identity_change(mode):
    old, new = build(), build(mode)
    assert new.facets == old.facets
    assert new.source_sample_ids == old.source_sample_ids
    assert new.source_split_identity_hash == old.source_split_identity_hash
    for before, after in zip(old.values, new.values, strict=True):
        assert replace(after, content=before.content) == before
    assert new.snapshot_id != old.snapshot_id
    assert new.content_hash() != old.content_hash()
    assert build(mode).frozen_json() == new.frozen_json()


def test_typed_fillers_preserve_grounded_surface_forms_and_empty_observation():
    rows = _rows()
    rows = (replace(rows[0], entity_fillers={
        "date": ("not this friday", "next friday"),
        "time": ("nine am", "9:30"),
    }), *rows[1:])
    snapshot = build("typed-fillers", rows)
    values = {v.value_id: json.loads(v.content) for v in snapshot.values}
    assert values["value:1"] == {"observed_slot_examples": {
        "date": ["not this friday", "next friday"], "time": ["nine am", "9:30"],
    }}
    assert values["value:3"] == {"observed_slot_examples": {}}
    blocks = KnowledgeValueRenderer(snapshot).assemble(("value:1",), view="text")
    assert json.loads(blocks[0]["text"]) == values["value:1"]
    assert blocks[0]["knowledge_role"] == "value"


def test_labels_only_is_explicit_information_removal_not_hidden_normalization():
    value = next(v for v in build("slot-type-set").values if v.value_id == "value:1")
    assert json.loads(value.content) == {"observed_slot_types": ["date", "time"]}
    assert "friday" not in value.content and "alarm_set" not in value.content


def test_intent_frame_adds_declared_train_relation_only():
    value = next(v for v in build("intent-slot-frame").values if v.value_id == "value:1")
    assert json.loads(value.content) == {
        "observed_intent": "alarm_set",
        "observed_slot_examples": {"date": ["friday"], "time": ["nine am"]},
    }


@pytest.mark.parametrize("view,mode", [
    ("slot-fillers", "invented"), ("exemplar", "typed-fillers"),
])
def test_ambiguous_or_unknown_format_refuses(view, mode):
    with pytest.raises(RailsError, match="value_format"):
        KnowledgeBuildSpec(carrier_lock_key="slurp", view=view, value_format=mode).validate()
