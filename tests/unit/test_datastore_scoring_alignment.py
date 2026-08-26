"""Gates for the datastore scoring alignment row.

Every metric this module lands replaced a metric that could not fail, so each
test class here carries at least one FAILURE-MODE test: a mutation that must
move the metric, or an input the metric must refuse. A metric that only has
happy-path tests is exactly the defect being repaired.

Nothing here opens a run directory, a snapshot or the network, and nothing
calls :func:`~...datastore_scoring_alignment.run` -- that arms the
process-wide offline guard by replacing ``socket.socket.connect`` and never
restores it, which would leak into every later test in the same session.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import (
    datastore_scoring_alignment as dsa,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class _Facet:
    def __init__(self, facet_id: str, dimension: str, representation: str) -> None:
        self.facet_id = facet_id
        self.dimension = dimension
        self.representation = representation


class _Snapshot:
    def __init__(self, facets) -> None:
        self.facets = tuple(facets)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_normalise_text_folds_case_punctuation_and_whitespace(self) -> None:
        assert dsa.normalise_text("  Turn ON, the LIGHT!  ") == "turn on the light"
        assert dsa.normalise_text("turn on the light") == dsa.normalise_text("Turn on the light.")

    def test_normalise_text_does_not_collapse_distinct_utterances(self) -> None:
        assert dsa.normalise_text("turn on the light") != dsa.normalise_text("turn off the light")

    def test_quantile_is_nearest_rank_and_returns_a_count(self) -> None:
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert dsa._quantile(values, 0.5) == 5
        assert dsa._quantile(values, 0.05) == 1
        assert dsa._quantile(values, 1.0) == 10
        assert isinstance(dsa._quantile(values, 0.25), int)

    def test_quantile_refuses_an_empty_sequence_and_an_out_of_range_q(self) -> None:
        with pytest.raises(dsa.AlignmentError):
            dsa._quantile([], 0.5)
        with pytest.raises(dsa.AlignmentError):
            dsa._quantile([1, 2], 0.0)
        with pytest.raises(dsa.AlignmentError):
            dsa._quantile([1, 2], 1.5)


# ---------------------------------------------------------------------------
# METRIC 2 -- per-target support distribution
# ---------------------------------------------------------------------------


class TestSupportDistribution:
    def test_reports_the_long_tail_shape(self) -> None:
        report = dsa.support_distribution(
            support_by_target={"a": 10, "b": 3, "c": 1, "d": 1},
            task_target_space=["a", "b", "c", "d"],
        )
        assert report["task_target_space_size"] == 4
        assert report["total_exemplars"] == 15
        assert report["min"] == 1
        assert report["max"] == 10
        assert report["p50"] == 1
        assert report["targets_with_support_1"] == 2
        assert report["support_1_targets"] == ["c", "d"]
        assert report["targets_with_support_below_5"] == 3

    def test_FAILURE_MODE_a_task_target_the_datastore_lacks_reads_support_zero(self) -> None:
        """The whole point. ``intent_coverage``'s TRAIN-derived denominator could
        not express this; a task-derived denominator must."""

        covered = dsa.support_distribution(
            support_by_target={"a": 4, "b": 4},
            task_target_space=["a", "b"],
        )
        assert covered["targets_with_zero_support"] == 0

        uncovered = dsa.support_distribution(
            support_by_target={"a": 4, "b": 4},
            task_target_space=["a", "b", "getLockStatus"],
        )
        assert uncovered["targets_with_zero_support"] == 1
        assert uncovered["zero_support_targets"] == ["getLockStatus"]
        assert uncovered["min"] == 0

    def test_FAILURE_MODE_deleting_a_target_moves_the_zero_count_and_the_total(self) -> None:
        before = dsa.support_distribution(
            support_by_target={"a": 9, "b": 1}, task_target_space=["a", "b"]
        )
        after = dsa.support_distribution(
            support_by_target={"b": 1}, task_target_space=["a", "b"]
        )
        assert after["targets_with_zero_support"] == before["targets_with_zero_support"] + 1
        assert after["total_exemplars"] < before["total_exemplars"]
        assert "a" in after["zero_support_targets"]

    def test_a_datastore_target_outside_the_declared_space_is_reported_not_dropped(self) -> None:
        report = dsa.support_distribution(
            support_by_target={"a": 1, "rogue": 7}, task_target_space=["a"]
        )
        assert report["targets_outside_task_space"] == 1
        assert report["outside_task_space_targets"] == ["rogue"]
        assert report["total_exemplars"] == 1

    def test_identities_are_capped_but_the_count_is_exact(self) -> None:
        space = [f"t{index:03d}" for index in range(120)]
        report = dsa.support_distribution(
            support_by_target={}, task_target_space=space, identity_cap=10
        )
        assert report["targets_with_zero_support"] == 120
        assert len(report["zero_support_targets"]) == 10
        assert report["zero_support_targets_truncated"] == 110

    def test_refuses_an_empty_task_space_and_a_negative_support(self) -> None:
        with pytest.raises(dsa.AlignmentError):
            dsa.support_distribution(support_by_target={"a": 1}, task_target_space=[])
        with pytest.raises(dsa.AlignmentError):
            dsa.support_distribution(
                support_by_target={"a": -1}, task_target_space=["a"]
            )


# ---------------------------------------------------------------------------
# METRIC 3 -- gold recall@k
# ---------------------------------------------------------------------------


def _recall(**overrides):
    import numpy as np

    defaults = dict(
        # three facets: 0 -> target 0, 1 -> target 1, 2 -> target 0
        cosines=np.asarray([[0.9, 0.5, 0.1], [0.1, 0.8, 0.7]]),
        facet_target_index=np.asarray([0, 1, 0]),
        facet_id_rank=np.asarray([0, 1, 2]),
        candidate_mask=np.asarray([True, True, True]),
        gold_target_index=np.asarray([0, 0]),
        k_grid=(1, 2, 3),
    )
    defaults.update(overrides)
    return dsa.gold_recall_curve(**defaults)


class TestGoldRecallCurve:
    def test_ranks_the_best_gold_bearing_facet(self) -> None:
        report = _recall()
        # query 0: gold target 0 tops the ranking -> rank 1
        # query 1: facet 1 (0.8) outranks facet 2 (0.7) -> gold rank 2
        assert report["curve"]["recall_at_1"]["hits"] == 1
        assert report["curve"]["recall_at_2"]["hits"] == 2
        assert report["curve"]["recall_at_2"]["recall"] == 1.0
        assert report["best_gold_rank"]["max"] == 2

    def test_FAILURE_MODE_gold_absent_from_the_datastore_is_a_miss_not_a_dropped_query(
        self,
    ) -> None:
        """The denominator is the EVAL population. A query the datastore cannot
        serve must lower recall, never quietly leave the denominator."""

        import numpy as np

        report = _recall(gold_target_index=np.asarray([7, 7]))
        assert report["curve"]["recall_at_3"]["recall"] == 0.0
        assert report["curve"]["recall_at_3"]["n_queries"] == 2
        assert report["queries_whose_gold_target_has_no_exemplar"] == 2

    def test_FAILURE_MODE_restricting_the_datastore_lowers_recall(self) -> None:
        """This is what makes the scaling curve a curve rather than a constant."""

        import numpy as np

        full = _recall()
        restricted = _recall(candidate_mask=np.asarray([False, True, False]))
        assert restricted["curve"]["recall_at_3"]["recall"] < full["curve"]["recall_at_3"]["recall"]
        assert restricted["candidate_facets"] == 1

    def test_FAILURE_MODE_permuting_gold_moves_the_curve(self) -> None:
        import numpy as np

        truthful = _recall(gold_target_index=np.asarray([0, 1]))
        permuted = _recall(gold_target_index=np.asarray([1, 0]))
        assert truthful["curve"]["recall_at_1"]["hits"] != permuted["curve"]["recall_at_1"]["hits"]

    def test_a_non_positive_cosine_is_unreachable_at_every_k(self) -> None:
        import numpy as np

        report = _recall(
            cosines=np.asarray([[0.9, -0.5, -0.1], [0.9, -0.5, -0.1]]),
            gold_target_index=np.asarray([1, 1]),
        )
        assert report["curve"]["recall_at_3"]["recall"] == 0.0
        assert report["queries_whose_gold_exemplars_are_all_non_positive"] == 2

    def test_ties_break_on_facet_id_ascending_like_multidim_recall(self) -> None:
        import numpy as np

        # both facets score 0.5; facet_id_rank 0 wins, so gold (target 1,
        # facet_id_rank 1) sits at rank 2.
        report = dsa.gold_recall_curve(
            cosines=np.asarray([[0.5, 0.5]]),
            facet_target_index=np.asarray([0, 1]),
            facet_id_rank=np.asarray([0, 1]),
            candidate_mask=np.asarray([True, True]),
            gold_target_index=np.asarray([1]),
            k_grid=(1, 2),
        )
        assert report["curve"]["recall_at_1"]["hits"] == 0
        assert report["curve"]["recall_at_2"]["hits"] == 1

    def test_refuses_mismatched_shapes_an_empty_population_and_a_dead_mask(self) -> None:
        import numpy as np

        with pytest.raises(dsa.AlignmentError):
            _recall(facet_target_index=np.asarray([0, 1]))
        with pytest.raises(dsa.AlignmentError):
            _recall(gold_target_index=np.asarray([0]))
        with pytest.raises(dsa.AlignmentError):
            _recall(candidate_mask=np.asarray([False, False, False]))
        with pytest.raises(dsa.AlignmentError):
            _recall(k_grid=(0,))
        with pytest.raises(dsa.AlignmentError):
            _recall(
                cosines=np.zeros((0, 3)),
                gold_target_index=np.zeros((0,), dtype=int),
            )


# ---------------------------------------------------------------------------
# METRIC 4 -- decontamination as a measured intersection
# ---------------------------------------------------------------------------


class TestDecontaminationIntersection:
    def test_a_disjoint_datastore_measures_zero_at_every_granularity(self) -> None:
        report = dsa.decontamination_intersection(
            datastore_sample_ids=["train:1", "train:2"],
            datastore_texts=["set an alarm for six", "play some jazz please"],
            eval_items={"dev:1": "what is the weather in paris tomorrow"},
            ngram=3,
        )
        assert report["by_sample_id"]["eval_items_found_in_the_datastore"] == 0
        assert report["by_normalised_text"]["eval_items_found_in_the_datastore"] == 0
        assert report["by_ngram"]["eval_items_found_in_the_datastore"] == 0
        assert report["eval_population"] == 1

    def test_FAILURE_MODE_an_injected_eval_id_is_counted_and_named(self) -> None:
        report = dsa.decontamination_intersection(
            datastore_sample_ids=["train:1", "dev:1"],
            datastore_texts=["set an alarm for six"],
            eval_items={"dev:1": "what is the weather", "dev:2": "play jazz"},
            ngram=3,
        )
        assert report["by_sample_id"]["eval_items_found_in_the_datastore"] == 1
        assert report["by_sample_id"]["identities"] == ["dev:1"]
        assert report["by_sample_id"]["rate"] == 0.5

    def test_FAILURE_MODE_text_granularity_catches_what_the_id_check_cannot(self) -> None:
        """A verbatim eval utterance re-filed under a training id is a leak the
        landed id-only gate reports as ``clean``."""

        report = dsa.decontamination_intersection(
            datastore_sample_ids=["train:1"],
            datastore_texts=["What is the WEATHER?"],
            eval_items={"dev:1": "what is the weather"},
            ngram=3,
        )
        assert report["by_sample_id"]["eval_items_found_in_the_datastore"] == 0
        assert report["by_normalised_text"]["eval_items_found_in_the_datastore"] == 1
        assert report["by_normalised_text"]["identities"] == ["dev:1"]

    def test_FAILURE_MODE_ngram_granularity_catches_a_partial_overlap(self) -> None:
        report = dsa.decontamination_intersection(
            datastore_sample_ids=["train:1"],
            datastore_texts=["please tell me what is the weather in oslo"],
            eval_items={"dev:1": "what is the weather in madrid"},
            ngram=4,
        )
        assert report["by_normalised_text"]["eval_items_found_in_the_datastore"] == 0
        assert report["by_ngram"]["eval_items_found_in_the_datastore"] == 1

    def test_a_short_eval_item_contributes_its_whole_token_sequence(self) -> None:
        report = dsa.decontamination_intersection(
            datastore_sample_ids=[],
            datastore_texts=["yes"],
            eval_items={"dev:1": "yes"},
            ngram=8,
        )
        assert report["eval_items_shorter_than_ngram"] == 1
        assert report["by_ngram"]["eval_items_found_in_the_datastore"] == 1

    def test_reports_counts_and_identities_never_a_verdict_string(self) -> None:
        report = dsa.decontamination_intersection(
            datastore_sample_ids=["train:1"],
            datastore_texts=["a b c"],
            eval_items={"dev:1": "a b c"},
        )
        assert "verdict" not in json.dumps(report)
        assert "clean" not in json.dumps(report)

    def test_refuses_a_non_positive_ngram(self) -> None:
        with pytest.raises(dsa.AlignmentError):
            dsa.decontamination_intersection(
                datastore_sample_ids=[],
                datastore_texts=[],
                eval_items={"dev:1": "a"},
                ngram=0,
            )


# ---------------------------------------------------------------------------
# METRIC 1 -- the scaling curve
# ---------------------------------------------------------------------------


def _cell(size, actual, recall_1, recall_5, recall_64, full_recall, zero_support, median):
    population = "P"
    return {
        "requested_datastore_size": size,
        "datastore_size_actual": actual,
        "primary_population": population,
        "support": {"targets_with_zero_support": zero_support, "p50": median},
        "gold_recall": {
            population: {
                "candidate_facets": actual,
                "curve": {
                    "recall_at_1": {"recall": recall_1},
                    "recall_at_5": {"recall": recall_5},
                    "recall_at_64": {"recall": recall_64},
                },
                "recall_at_full_datastore": {"recall": full_recall},
            }
        },
    }


class TestScalingCurve:
    def test_a_moving_curve_is_informative_and_monotone(self) -> None:
        curve = dsa.scaling_curve(
            [
                _cell(100, 100, 0.1, 0.2, 0.3, 0.4, 5, 1),
                _cell(1000, 1000, 0.2, 0.4, 0.5, 0.6, 2, 8),
                _cell(None, 11514, 0.3, 0.6, 0.7, 0.9, 0, 90),
            ]
        )
        assert curve["curve_is_informative"] is True
        assert curve["distinct_recall_at_5_values"] == 3
        assert curve["monotone_non_decreasing_in_size"] is True
        assert curve["recall_at_5_span"] == pytest.approx(0.4)
        assert [row["datastore_size_actual"] for row in curve["rows"]] == [100, 1000, 11514]

    def test_FAILURE_MODE_a_flat_curve_is_reported_as_uninformative(self) -> None:
        """A curve that does not move across the swept axis cannot fail, which is
        the defect this whole row exists to replace."""

        curve = dsa.scaling_curve(
            [
                _cell(100, 100, 0.5, 0.6, 0.7, 0.8, 0, 9),
                _cell(1000, 1000, 0.5, 0.6, 0.7, 0.8, 0, 9),
                _cell(None, 11514, 0.5, 0.6, 0.7, 0.8, 0, 9),
            ]
        )
        assert curve["curve_is_informative"] is False
        assert curve["distinct_recall_at_5_values"] == 1
        assert curve["recall_at_5_span"] == 0.0

    def test_FAILURE_MODE_a_non_monotone_curve_is_reported(self) -> None:
        curve = dsa.scaling_curve(
            [
                _cell(100, 100, 0.1, 0.7, 0.3, 0.4, 5, 1),
                _cell(None, 11514, 0.3, 0.6, 0.7, 0.9, 0, 90),
            ]
        )
        assert curve["monotone_non_decreasing_in_size"] is False

    def test_refuses_a_single_point_curve(self) -> None:
        with pytest.raises(dsa.AlignmentError):
            dsa.scaling_curve([_cell(None, 11514, 0.3, 0.6, 0.7, 0.9, 0, 90)])


# ---------------------------------------------------------------------------
# The restriction proof that buys the curve at zero contacts
# ---------------------------------------------------------------------------


class TestRestrictionProof:
    def test_a_true_subset_passes(self) -> None:
        full = {"facet:content:1": "alpha", "facet:content:2": "beta"}
        reduced = _Snapshot(
            [
                _Facet("facet:content:1", "content", "alpha"),
                _Facet("facet:label:intent:x", "label", "2 utterances in this snapshot"),
            ]
        )
        proof = dsa.prove_restriction_is_exact(reduced_snapshot=reduced, full_content=full)
        assert proof["reduced_content_facets"] == 1
        assert proof["ids_are_a_subset"] is True

    def test_FAILURE_MODE_an_unknown_content_facet_id_raises(self) -> None:
        full = {"facet:content:1": "alpha"}
        reduced = _Snapshot([_Facet("facet:content:9", "content", "alpha")])
        with pytest.raises(dsa.AlignmentError, match="NOT exact"):
            dsa.prove_restriction_is_exact(reduced_snapshot=reduced, full_content=full)

    def test_FAILURE_MODE_a_drifted_representation_raises(self) -> None:
        """If a reduced tier's content text differed from the full tier's, the
        landed vector would be the wrong vector and the whole zero-contact
        route would be void."""

        full = {"facet:content:1": "alpha"}
        reduced = _Snapshot([_Facet("facet:content:1", "content", "alpha (1 in this snapshot)")])
        with pytest.raises(dsa.AlignmentError, match="NOT exact"):
            dsa.prove_restriction_is_exact(reduced_snapshot=reduced, full_content=full)

    def test_a_reduced_tier_with_no_content_facets_raises(self) -> None:
        with pytest.raises(dsa.AlignmentError):
            dsa.prove_restriction_is_exact(
                reduced_snapshot=_Snapshot([_Facet("facet:label:x", "label", "t")]),
                full_content={"facet:content:1": "alpha"},
            )

    def test_FAILURE_MODE_the_full_tier_must_cover_the_pinned_content_plane(self) -> None:
        """At the full tier a subset is not enough: if the rebuild covers only
        part of the pinned snapshot's content facets, the pinned NPZ is not the
        vector table for the corpus being restricted."""

        full = {"facet:content:1": "alpha", "facet:content:2": "beta"}
        reduced = _Snapshot([_Facet("facet:content:1", "content", "alpha")])
        assert (
            dsa.prove_restriction_is_exact(reduced_snapshot=reduced, full_content=full)[
                "pinned_content_facets_not_in_this_tier"
            ]
            == 1
        )
        with pytest.raises(dsa.AlignmentError, match="covers only"):
            dsa.prove_restriction_is_exact(
                reduced_snapshot=reduced, full_content=full, require_equality=True
            )

    def test_full_tier_equality_holds_when_the_planes_match(self) -> None:
        full = {"facet:content:1": "alpha"}
        reduced = _Snapshot([_Facet("facet:content:1", "content", "alpha")])
        proof = dsa.prove_restriction_is_exact(
            reduced_snapshot=reduced, full_content=full, require_equality=True
        )
        assert proof["equality_required_and_held"] is True
        assert proof["pinned_content_facets_not_in_this_tier"] == 0


class _HashedSnapshot:
    def __init__(self, digest: str) -> None:
        self._digest = digest

    def content_hash(self) -> str:
        return self._digest


class TestFullTierIdentity:
    def test_reports_a_whole_snapshot_hash_divergence_rather_than_hiding_it(self) -> None:
        identity = dsa._full_tier_identity(
            reduced=_HashedSnapshot("b" * 64),
            pinned_content_hash="a" * 64,
            content_facets_match=True,
        )
        assert identity["whole_snapshot_hash_reproduces"] is False
        assert identity["content_plane_reproduces_exactly"] is True
        assert identity["rebuilt_snapshot_content_hash"] == "b" * 64

    def test_reports_agreement_when_the_hashes_match(self) -> None:
        identity = dsa._full_tier_identity(
            reduced=_HashedSnapshot("a" * 64),
            pinned_content_hash="a" * 64,
            content_facets_match=True,
        )
        assert identity["whole_snapshot_hash_reproduces"] is True


# ---------------------------------------------------------------------------
# The mutation battery is itself fail-closed
# ---------------------------------------------------------------------------


class TestMutationBattery:
    def test_refuses_to_land_a_flat_scaling_curve(self) -> None:
        """The proof obligation is machine-enforced: a metric that cannot fail is
        REFUSED, not narrated."""

        cells = [
            _cell(100, 100, 0.5, 0.6, 0.7, 0.8, 0, 9),
            _cell(None, 11514, 0.5, 0.6, 0.7, 0.8, 0, 9),
        ]
        curve = dsa.scaling_curve(cells)
        with pytest.raises(dsa.AlignmentError, match="CONSTANT"):
            dsa.mutation_battery(
                cells=cells,
                curve=curve,
                support_inputs={"support_by_target": {"a": 1}, "task_target_space": ["a"]},
                recall_inputs={},
                decontamination_inputs={},
                carrier="synthetic",
            )


# ---------------------------------------------------------------------------
# The superseded metrics are kept beside the new ones, not deleted
# ---------------------------------------------------------------------------


class TestSupersededMetrics:
    def test_every_superseded_entry_points_at_a_landed_receipt_that_exists(self) -> None:
        assert dsa.SUPERSEDED_METRICS
        for entry in dsa.SUPERSEDED_METRICS:
            for relpath in str(entry["last_landed_receipt"]).split(" and "):
                assert (REPO_ROOT / relpath.strip()).is_file(), relpath

    def test_every_superseded_entry_names_its_audit_and_its_replacement(self) -> None:
        for entry in dsa.SUPERSEDED_METRICS:
            assert str(entry["classified_by"]).startswith("docs/readiness/")
            assert entry["classification"]
            assert entry["replaced_by"]

    def test_the_landed_receipts_still_carry_the_old_values_untouched(self) -> None:
        slurp = json.loads(
            (REPO_ROOT / "docs/receipts/knowledge/slurp-kb-size-full.json").read_text(
                encoding="utf-8"
            )
        )
        a2t = json.loads(
            (REPO_ROOT / "docs/receipts/knowledge/a2t-kb-size-full.json").read_text(
                encoding="utf-8"
            )
        )
        assert slurp["coverage_report"]["intent_coverage"] == 1.0
        assert slurp["decontamination"]["verdict"] == "clean"
        assert a2t["coverage_report"]["tool_coverage"] == 1.0
        assert a2t["decontamination"]["verdict"] == "clean"

    def test_field_practice_names_a_source_and_an_implementation_for_all_four(self) -> None:
        assert len(dsa.FIELD_PRACTICE) == 4
        implemented = {str(entry["implemented_by"]) for entry in dsa.FIELD_PRACTICE}
        assert implemented == {
            "scaling_curve",
            "support_distribution",
            "gold_recall_curve",
            "decontamination_intersection",
        }
        for entry in dsa.FIELD_PRACTICE:
            assert entry["field_source"]
            assert entry["our_own_prior_call"]

    def test_every_field_source_points_at_a_landed_in_repo_record(self) -> None:
        """This row took zero network contacts, so no source may be a fetched
        citation: each must be an addressable line in an already-landed file."""

        assert (REPO_ROOT / dsa.SURVEY_RELPATH).is_file()
        for entry in dsa.FIELD_PRACTICE:
            record = str(entry["source_record"])
            assert record.startswith(dsa.SURVEY_RELPATH), record
            assert entry["source_mapping_line"]
