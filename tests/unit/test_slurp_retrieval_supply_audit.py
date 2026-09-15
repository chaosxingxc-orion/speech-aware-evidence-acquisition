from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_retrieval_supply_audit import (
    AuditError,
    ObservedSupportRow,
    ReferenceIntentRow,
    build_audit_report,
    build_selection_grid,
    load_selection_anchor,
    write_new_json,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import qualify_id
from speech_aware_evidence_acquisition.rails.phase_supply import SealedSegmentQuery


_SHA = "a" * 64


def _snapshot() -> KnowledgeSnapshot:
    facets = (
        KeyFacet("f-a", "content", "text", "alpha", ("train:1",)),
        KeyFacet("f-b", "content", "text", "beta", ("train:1",)),
        KeyFacet("f-c", "content", "text", "gamma", ("train:1",)),
    )
    values = (
        ValueBundle("intent-boundary:a", "A", ("f-a",), ("train:1",), ("p:a",)),
        ValueBundle("intent-boundary:b", "Bee", ("f-b", "f-c"), ("train:1",), ("p:b",)),
        ValueBundle("intent-boundary:c", "Sea", ("f-c",), ("train:1",), ("p:c",)),
    )
    return KnowledgeSnapshot(
        snapshot_id="synthetic",
        source_split_identity_hash=_SHA,
        source_sample_ids=("train:1",),
        builder_policy_id="synthetic-v1",
        facets=facets,
        values=values,
    ).validate()


def _segments() -> dict[str, SealedSegmentQuery]:
    return {
        "s1": SealedSegmentQuery(
            audio_sha256="b" * 64,
            segments=(
                {"content": (1.0, 0.0)},
                {"content": (0.0, 1.0)},
            ),
        )
    }


def test_shared_segment_recall_preserves_ties_and_fuser_deduplicates_values():
    grid = build_selection_grid(
        snapshot=_snapshot(),
        query_vectors_by_sample=_segments(),
        facet_vectors={
            "f-a": {"content": (1.0, 0.0)},
            "f-b": {"content": (1.0, 0.0)},
            "f-c": {"content": (0.0, 1.0)},
        },
        ordered_sample_ids=("s1",),
        breadths=(1, 3),
        store_id="intent-boundaries",
        workers=1,
    )

    narrow = grid.by_breadth[1]["s1"]
    wide = grid.by_breadth[3]["s1"]
    assert narrow.ranked_facets == (("f-a", 1.0), ("f-c", 1.0))
    assert narrow.selected_value_ids == ("intent-boundary:a",)
    assert wide.ranked_facets == (
        ("f-a", 1.0),
        ("f-b", 1.0),
        ("f-c", 1.0),
    )
    assert wide.selected_value_ids == (
        "intent-boundary:a",
        "intent-boundary:b",
        "intent-boundary:c",
    )


def test_report_counts_own_card_only_and_positive_rank():
    grid = build_selection_grid(
        snapshot=_snapshot(),
        query_vectors_by_sample=_segments(),
        facet_vectors={
            "f-a": {"content": (1.0, 0.0)},
            "f-b": {"content": (1.0, 0.0)},
            "f-c": {"content": (0.0, 1.0)},
        },
        ordered_sample_ids=("s1",),
        breadths=(1, 3),
        store_id="intent-boundaries",
        workers=1,
    )
    observed = (
        ObservedSupportRow(
            sample_id="s1",
            selected_ids_sha256=content_hash(
                [qualify_id("intent-boundaries", item)
                 for item in grid.by_breadth[3]["s1"].selected_value_ids]
            ),
            own_intent_supplied=True,
            c0_covered=False,
        ),
    )
    report = build_audit_report(
        selection=grid,
        reference_rows=(ReferenceIntentRow("s1", "c", "music"),),
        observed_rows=observed,
        replay_breadth=3,
        expected_replay_own_supplied=1,
        expected_replay_supply_and_covered=0,
    )

    assert report["breadths"]["1"]["aggregate"]["own_intent_card_supplied"]["numerator"] == 0
    assert report["breadths"]["3"]["aggregate"]["own_intent_card_supplied"]["numerator"] == 1
    sample = report["breadths"]["3"]["samples"][0]
    assert sample["own_intent_card_supplied"] is True
    assert sample["positive_score_own_facet_rank"] == 3
    assert sample["selected_value_ids_sha256"] == observed[0].selected_ids_sha256
    assert "intent_id" not in sample
    assert "scenario_id" not in sample


def test_replay_refuses_selected_hash_or_count_drift():
    grid = build_selection_grid(
        snapshot=_snapshot(),
        query_vectors_by_sample=_segments(),
        facet_vectors={
            "f-a": {"content": (1.0, 0.0)},
            "f-b": {"content": (1.0, 0.0)},
            "f-c": {"content": (0.0, 1.0)},
        },
        ordered_sample_ids=("s1",),
        breadths=(3,),
        store_id="intent-boundaries",
        workers=1,
    )
    reference = (ReferenceIntentRow("s1", "c", "music"),)
    with pytest.raises(AuditError, match="selected value hash"):
        build_audit_report(
            selection=grid,
            reference_rows=reference,
            observed_rows=(ObservedSupportRow("s1", "0" * 64, True, False),),
            replay_breadth=3,
            expected_replay_own_supplied=1,
            expected_replay_supply_and_covered=0,
        )
    valid_hash = content_hash([
        qualify_id("intent-boundaries", item)
        for item in grid.by_breadth[3]["s1"].selected_value_ids
    ])
    with pytest.raises(AuditError, match="own-supplied count"):
        build_audit_report(
            selection=grid,
            reference_rows=reference,
            observed_rows=(ObservedSupportRow("s1", valid_hash, True, False),),
            replay_breadth=3,
            expected_replay_own_supplied=0,
            expected_replay_supply_and_covered=0,
        )


def test_selection_anchor_loader_extracts_identity_only_and_checks_pin_and_cohort(
    tmp_path: Path,
):
    path = tmp_path / "support.json"
    document = {
        "output": {
            "cohort": {
                "sample_count": 2,
                "ordered_sample_ids_sha256": content_hash(["s1", "s2"]),
            },
            "initial_intent_support": {
                "samples": [
                    {
                        "sample_id": "s1",
                        "supplied_intent_value_ids_sha256": "1" * 64,
                        "gold_intent_value_supplied": True,
                        "c0_gold_covered": False,
                    },
                    {
                        "sample_id": "s2",
                        "supplied_intent_value_ids_sha256": "2" * 64,
                        "gold_intent_value_supplied": False,
                        "c0_gold_covered": True,
                    },
                ]
            },
        }
    }
    raw = json.dumps(document).encode()
    path.write_bytes(raw)

    anchor = load_selection_anchor(
        path,
        expected_sha256=hashlib.sha256(raw).hexdigest(),
        expected_sample_ids=("s1", "s2"),
    )
    assert anchor.sample_ids == ("s1", "s2")
    assert anchor.selected_ids_sha256 == ("1" * 64, "2" * 64)
    assert not hasattr(anchor, "c0_covered")
    with pytest.raises(AuditError, match="SHA-256"):
        load_selection_anchor(path, expected_sha256="0" * 64, expected_sample_ids=("s1", "s2"))
    with pytest.raises(AuditError, match="ordered cohort"):
        load_selection_anchor(
            path,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            expected_sample_ids=("s2", "s1"),
        )


def test_selection_refuses_partial_or_extra_query_cohort():
    common = dict(
        snapshot=_snapshot(),
        facet_vectors={
            "f-a": {"content": (1.0, 0.0)},
            "f-b": {"content": (1.0, 0.0)},
            "f-c": {"content": (0.0, 1.0)},
        },
        breadths=(1,),
        store_id="intent-boundaries",
        workers=1,
    )
    with pytest.raises(AuditError, match="exact ordered cohort"):
        build_selection_grid(
            query_vectors_by_sample=_segments(),
            ordered_sample_ids=("s1", "missing"),
            **common,
        )
    with pytest.raises(AuditError, match="exact ordered cohort"):
        build_selection_grid(
            query_vectors_by_sample={**_segments(), "extra": _segments()["s1"]},
            ordered_sample_ids=("s1",),
            **common,
        )


def test_write_new_json_never_overwrites(tmp_path: Path):
    path = tmp_path / "result.json"
    first = write_new_json(path, {"schema": "first"})
    assert first["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(AuditError, match="already exists"):
        write_new_json(path, {"schema": "second"})


def test_reference_labels_cannot_change_sealed_selection():
    grid = build_selection_grid(
        snapshot=_snapshot(),
        query_vectors_by_sample=_segments(),
        facet_vectors={
            "f-a": {"content": (1.0, 0.0)},
            "f-b": {"content": (1.0, 0.0)},
            "f-c": {"content": (0.0, 1.0)},
        },
        ordered_sample_ids=("s1",),
        breadths=(3,),
        store_id="intent-boundaries",
        workers=1,
    )
    before = grid.commitment()
    selected_hash = grid.by_breadth[3]["s1"].selected_ids_sha256
    observed = (ObservedSupportRow("s1", selected_hash, True, True),)
    build_audit_report(
        selection=grid,
        reference_rows=(ReferenceIntentRow("s1", "a", "alarm"),),
        observed_rows=observed,
        replay_breadth=3,
        expected_replay_own_supplied=1,
        expected_replay_supply_and_covered=1,
    )
    build_audit_report(
        selection=grid,
        reference_rows=(ReferenceIntentRow("s1", "c", "music"),),
        observed_rows=observed,
        replay_breadth=3,
        expected_replay_own_supplied=1,
        expected_replay_supply_and_covered=1,
    )
    assert grid.commitment() == before
