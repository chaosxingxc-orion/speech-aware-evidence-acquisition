"""Pure-function gates for the ``content_facet_target`` correctness audit.

No sealed bytes and no data root are touched here. These tests reproduce the
audited defect in miniature -- a mapping named for content facets that is in
fact keyed by every facet a target-bearing value touches -- so that the audit's
two readings cannot silently converge under a later refactor, and so that the
measurement which decides every admitted-set call site (a facet outside the
content-facet NPZ receives no cosine-family dimension at all) stays pinned.
"""

from __future__ import annotations

import numpy as np

from speech_aware_evidence_acquisition.analysis import (
    a2t_lexical_ceiling as lex,
    content_facet_target_audit as audit,
    contrast_fewshot_preanalysis as cf,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)

_SHA = "b" * 64


def _mixed_dimension_snapshot() -> KnowledgeSnapshot:
    """Two values, each associating one content, one label, one prior and one
    speaker facet -- the exact shape both landed carriers have."""

    return KnowledgeSnapshot(
        snapshot_id="content-facet-target-audit-v1",
        source_split_identity_hash=_SHA,
        source_sample_ids=("train:u1", "train:u2"),
        builder_policy_id="test-builder-v1",
        facets=(
            KeyFacet("facet:content:u1", "content", "text", "red apple", ("train:u1",)),
            KeyFacet("facet:content:u2", "content", "text", "green leaf", ("train:u2",)),
            KeyFacet("facet:label:red", "label", "text", "red", ("train:u1",)),
            KeyFacet("facet:label:green", "label", "text", "green", ("train:u2",)),
            KeyFacet("facet:prior:red", "prior", "text", "red prior", ("train:u1",)),
            KeyFacet("facet:speaker:s1", "speaker", "text", "speaker one", ("train:u1",)),
        ),
        values=(
            ValueBundle(
                value_id="value:u1",
                content="evidence u1",
                associated_facet_ids=(
                    "facet:content:u1",
                    "facet:label:red",
                    "facet:prior:red",
                    "facet:speaker:s1",
                ),
                source_sample_ids=("train:u1",),
                provenance_refs=("sample:train:u1",),
                task_target="red",
                prior_score=0.7,
            ),
            ValueBundle(
                value_id="value:u2",
                content="evidence u2",
                associated_facet_ids=("facet:content:u2", "facet:label:green"),
                source_sample_ids=("train:u2",),
                provenance_refs=("sample:train:u2",),
                task_target="green",
                prior_score=0.3,
            ),
        ),
    ).validate()


def _bundle(snapshot: KnowledgeSnapshot) -> cf.SnapshotBundle:
    """A bundle whose NPZ carries CONTENT facets only, as both landed ones do,
    with ``content_facet_target`` built exactly as the audited code builds it."""

    facet_ids = ("facet:content:u1", "facet:content:u2")
    matrix = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float64)
    content_facet_target: dict[str, str] = {}
    for value in snapshot.values:
        for facet_id in value.associated_facet_ids:
            content_facet_target.setdefault(facet_id, value.task_target)
    return cf.SnapshotBundle(
        snapshot=snapshot,
        snapshot_sha256=_SHA,
        facet_ids=facet_ids,
        matrix=matrix,
        facet_index={facet_id: index for index, facet_id in enumerate(facet_ids)},
        npz_sha256=_SHA,
        label_targets={},
        label_texts={},
        values_by_id={value.value_id: value for value in snapshot.values},
        content_facet_target=content_facet_target,
        facet_indices_by_target={},
        values_by_target={},
        facet_id_rank=np.asarray([0, 1], dtype=np.int64),
        prior_dimension_recall={},
    )


class TestKeyComposition:
    def test_the_mapping_is_keyed_by_every_dimension_the_value_touches(self) -> None:
        """THE AUDITED DEFECT, in miniature: the name says content, the keys
        say content AND label AND prior AND speaker."""

        composition = audit.key_composition(
            _bundle(_mixed_dimension_snapshot()), carrier="test"
        )
        assert composition.keys_total == 6
        assert composition.keys_by_dimension == {
            "content": 2,
            "label": 2,
            "prior": 1,
            "speaker": 1,
        }
        assert composition.content_keys == 2
        assert composition.non_content_keys == 4

    def test_the_content_restricted_reference_agrees_with_the_content_count(self) -> None:
        snapshot = _mixed_dimension_snapshot()
        composition = audit.key_composition(_bundle(snapshot), carrier="test")
        assert composition.reference_content_keys == len(lex.content_facet_targets(snapshot))
        assert composition.reference_content_keys == composition.content_keys

    def test_no_non_content_key_reaches_the_content_facet_npz(self) -> None:
        """The set fact every admitted-set call site rests on."""

        composition = audit.key_composition(
            _bundle(_mixed_dimension_snapshot()), carrier="test"
        )
        assert composition.non_content_keys_inside_the_npz == 0
        assert composition.npz_ids_by_dimension == {"content": 2}


class TestAdmittedSetScope:
    def test_a_facet_outside_the_npz_receives_no_vector_at_all(self) -> None:
        """``_max_cosine`` therefore returns 0.0 for it and the admission test
        ``>= tau`` refuses it for any positive tau."""

        scope = audit.admitted_set_scope(
            _bundle(_mixed_dimension_snapshot()), carrier="test"
        )
        assert scope["facets_probed"] == 6
        assert scope["facets_outside_the_npz_answered_with_a_vector"] == 0
        assert scope["facets_outside_the_npz_answered_with_no_vector"] == 4
        assert scope["non_content_facets_carrying_a_vector"] == 0
        assert scope["cosine_family_dimensions_returned"] == ["content"]
        assert float(scope["frozen_tau"]) > 0.0


class TestBothReadings:
    def test_the_two_readings_differ_by_exactly_the_non_content_facets(self) -> None:
        snapshot = _mixed_dimension_snapshot()
        bundle = _bundle(snapshot)
        dimension_of = {facet.facet_id: facet.dimension for facet in snapshot.facets}
        assert audit._both_readings_for_target(bundle, dimension_of, "red") == (4, 1)
        assert audit._both_readings_for_target(bundle, dimension_of, "green") == (2, 1)
