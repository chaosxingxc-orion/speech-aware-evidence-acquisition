"""Selected-TRAIN role coverage without changing retrieval semantics."""

from dataclasses import replace
import hashlib
import json

import pytest

from test_knowledge_build_slot_filler_view import _row, _rows
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    KnowledgeBuildSpec, build_knowledge_snapshot,
)
from speech_aware_evidence_acquisition.rails.knowledge_value_views import KnowledgeValueRenderer


def build(rows=None, *, mode="intent-role-coverage", size=None, forbidden=frozenset()):
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp", dimensions=("content",),
            view="slot-fillers", value_format=mode, datastore_size=size,
        ),
        rows=_rows() if rows is None else rows,
        forbidden_sample_ids=forbidden,
    )


def documents(snapshot):
    return {v.value_id: json.loads(v.content) for v in snapshot.values}


def test_role_coverage_adds_same_intent_support_to_the_existing_frame():
    value = documents(build())["value:1"]
    assert value["observed_intent"] == "alarm_set"
    assert value["observed_slot_examples"] == {"date": ["friday"], "time": ["nine am"]}
    assert value["intent_role_coverage"] == {
        "support_unit": "selected TRAIN utterance",
        "utterance_count": 2,
        "utterances_without_entity_annotations": 0,
        "observed_utterance_counts_by_role": {"date": 1, "time": 2},
        "interpretation": (
            "Observed roles are not required or exhaustive slots. "
            "Current speech determines entity presence and values."
        ),
    }


def test_missing_annotation_is_recorded_without_a_negative_presence_claim():
    value = documents(build())["value:3"]
    assert value["observed_slot_examples"] == {}
    assert value["intent_role_coverage"]["observed_utterance_counts_by_role"] == {
        "device_type": 1,
    }
    assert value["intent_role_coverage"]["utterances_without_entity_annotations"] == 1


def test_multiple_recordings_and_mentions_do_not_inflate_utterance_support():
    rows = _rows()
    first = replace(
        rows[0],
        sample_ids=rows[0].sample_ids + ("slurp:train:1:alternate",),
        speaker_by_sample_id={**rows[0].speaker_by_sample_id,
                              "slurp:train:1:alternate": "FO-002"},
        entity_fillers={"time": ("nine am", "ten am", "nine am")},
        entity_types=("time",),
    )
    value = documents(build((first, *rows[1:])))["value:1"]
    coverage = value["intent_role_coverage"]
    assert coverage["utterance_count"] == 2
    assert coverage["observed_utterance_counts_by_role"] == {"time": 2}


def test_unselected_rows_cannot_contribute_roles_or_provenance():
    snapshot = build(size=2)
    selected = {v.value_id.removeprefix("value:") for v in snapshot.values}
    for value in snapshot.values:
        doc = json.loads(value.content)
        source_rows = [r for r in _rows() if r.utterance_id in selected
                       and r.intent == doc["observed_intent"]]
        expected = {
            role: sum(bool(r.entity_fillers.get(role)) for r in source_rows)
            for role in sorted({role for r in source_rows for role in r.entity_fillers})
        }
        assert doc["intent_role_coverage"]["utterance_count"] == len(source_rows)
        assert doc["intent_role_coverage"]["observed_utterance_counts_by_role"] == expected
        membership_hash = hashlib.sha256(
            "\n".join(sorted(r.utterance_id for r in source_rows)).encode()
        ).hexdigest()
        assert (
            "governed-jsonl:slurp/metadata/train.jsonl#slurp_ids_sha256="
            + membership_hash
        ) in value.provenance_refs


def test_aggregate_membership_is_bound_without_replacing_anchor_associations():
    old, new = build(mode="intent-slot-frame"), build()
    expected_hash = hashlib.sha256(b"1\n2").hexdigest()
    for before, after in zip(old.values, new.values, strict=True):
        assert after.source_sample_ids == before.source_sample_ids
        assert set(before.provenance_refs) < set(after.provenance_refs)
        assert replace(after, content=before.content,
                       provenance_refs=before.provenance_refs) == before
    assert (
        "governed-jsonl:slurp/metadata/train.jsonl#slurp_ids_sha256="
        + expected_hash
    ) in new.values[0].provenance_refs


def test_keys_roster_and_priors_stay_identical_and_rendered_values_round_trip():
    old, new = build(mode="intent-slot-frame"), build()
    assert old.facets == new.facets
    assert old.source_sample_ids == new.source_sample_ids
    assert old.source_split_identity_hash == new.source_split_identity_hash
    assert old.snapshot_id != new.snapshot_id
    loaded = KnowledgeSnapshot.from_frozen_json(new.frozen_json())
    blocks = KnowledgeValueRenderer(loaded).assemble(("value:2", "value:1"))
    assert [b["evidence_id"] for b in blocks] == ["value:2", "value:1"]
    assert json.loads(blocks[0]["text"]) == documents(new)["value:2"]
    assert build(tuple(reversed(_rows()))).frozen_json() == new.frozen_json()


def test_a_single_unannotated_intent_has_zero_observed_roles_not_required_slots():
    row = _row("solo", scenario="iot", action="hue_lightoff", words="lights off")
    coverage = documents(build((row,)))["value:solo"]["intent_role_coverage"]
    assert coverage["utterance_count"] == coverage["utterances_without_entity_annotations"] == 1
    assert coverage["observed_utterance_counts_by_role"] == {}


def test_forbidden_construction_source_is_rejected_before_aggregation():
    forbidden = frozenset(_rows()[1].sample_ids)
    with pytest.raises(RailsError, match="decontamination"):
        build(forbidden=forbidden)


def test_duplicate_utterance_identity_is_rejected_instead_of_counted_twice():
    with pytest.raises(RailsError, match="unique utterance_id"):
        build((*_rows(), _rows()[0]))


def test_noncanonical_intent_is_not_silently_grouped_with_a_different_task():
    with pytest.raises(RailsError, match="canonical"):
        build((replace(_rows()[0], intent="set"), *_rows()[1:]))


def test_empty_filler_list_does_not_assert_an_observed_role():
    row = replace(_rows()[0], entity_types=(), entity_fillers={"time": ()})
    coverage = documents(build((row,)))["value:1"]["intent_role_coverage"]
    assert coverage["observed_utterance_counts_by_role"] == {}
    assert coverage["utterances_without_entity_annotations"] == 1
