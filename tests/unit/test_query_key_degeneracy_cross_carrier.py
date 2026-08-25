"""Pure-function gates for the cross-carrier query-key degeneracy row.

No sealed bytes and no data root are touched here: these tests pin the
arithmetic the row's conclusions rest on, so a later refactor cannot silently
change what "distinct query vectors per trajectory", "structurally empty
answer" or "distance below tau" mean.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis import (
    query_key_degeneracy_cross_carrier as qkd,
)


class TestVectorDigest:
    def test_identical_vectors_share_one_key(self) -> None:
        assert qkd.vector_digest((0.1, 0.2, 0.3)) == qkd.vector_digest([0.1, 0.2, 0.3])

    def test_a_different_vector_is_a_different_key(self) -> None:
        assert qkd.vector_digest((0.1, 0.2)) != qkd.vector_digest((0.1, 0.2000001))


class TestClusterBlock:
    """The A2T shape in miniature: three trajectories share one key and one
    supply, two carry their own."""

    @staticmethod
    def _fixture() -> dict[str, object]:
        ids = ("a", "b", "c", "d", "e")
        shared = (1.0, 0.0)
        vectors = {
            "a": shared,
            "b": shared,
            "c": shared,
            "d": (0.0, 1.0),
            "e": (0.5, 0.5),
        }
        texts = {
            "a": "[]",
            "b": "[]",
            "c": "[]",
            "d": "call setLighting",
            "e": "call setPowerState",
        }
        supplies = {
            "a": ("v1", "v2"),
            "b": ("v1", "v2"),
            "c": ("v1", "v2"),
            "d": ("v3",),
            "e": ("v4",),
        }
        return qkd._cluster_block(
            ids,
            label="fixture",
            query_vectors=vectors,
            texts=texts,
            supplies=supplies,
        )

    def test_distinct_keys_and_the_degeneracy_ratio(self) -> None:
        block = self._fixture()
        assert block["n"] == 5
        assert block["distinct_query_vectors"] == 3
        assert block["distinct_query_vectors_per_trajectory"] == pytest.approx(0.6)

    def test_the_largest_cluster_and_its_single_supply(self) -> None:
        block = self._fixture()
        assert block["largest_identical_query_cluster_size"] == 3
        assert block["largest_identical_query_cluster_share"] == pytest.approx(0.6)
        assert block["distinct_supplies_inside_the_largest_key_cluster"] == 1

    def test_distinct_supplies_are_counted_over_the_whole_group(self) -> None:
        block = self._fixture()
        assert block["distinct_supplies"] == 3
        assert block["distinct_supplies_per_trajectory"] == pytest.approx(0.6)
        assert block["empty_supplies"] == 0

    def test_text_and_vector_counts_are_both_published(self) -> None:
        block = self._fixture()
        assert block["distinct_contact0_texts"] == 3
        assert block["distinct_query_vectors_minus_distinct_texts"] == 0
        assert block["embedding_is_a_pure_function_of_the_text"] is True

    def test_identical_texts_with_different_vectors_are_flagged(self) -> None:
        """The measured SLURP condition: the same string embedded twice to two
        different vectors. The text count is then the conservative floor."""

        ids = ("a", "b")
        block = qkd._cluster_block(
            ids,
            label="fixture",
            query_vectors={"a": (1.0, 0.0), "b": (1.0, 1e-9)},
            texts={"a": "same", "b": "same"},
            supplies={"a": (), "b": ()},
        )
        assert block["distinct_contact0_texts"] == 1
        assert block["distinct_query_vectors"] == 2
        assert block["distinct_query_vectors_minus_distinct_texts"] == 1
        assert block["embedding_is_a_pure_function_of_the_text"] is False
        assert block["empty_supplies"] == 2


class TestAnswerContentProfile:
    def test_an_all_identical_empty_group_carries_no_content(self) -> None:
        ids = ("a", "b", "c")
        profile = qkd.answer_content_profile(
            ids,
            label="empty",
            texts={sample: "[]" for sample in ids},
            structurally_empty={sample: True for sample in ids},
        )
        assert profile["structurally_empty_answer_rate"] == pytest.approx(1.0)
        assert profile["distinct_contact0_texts"] == 1
        assert profile["modal_text_multiplicity"] == 3
        assert profile["tokens_outside_the_group_modal_text_median"] == 0
        assert profile["answers_with_zero_tokens_outside_the_modal_text"] == 3

    def test_a_varying_label_group_carries_content(self) -> None:
        texts = {
            "a": '{"scenario": "alarm", "action": "set"}',
            "b": '{"scenario": "email", "action": "send"}',
            "c": '{"scenario": "news", "action": "query"}',
        }
        profile = qkd.answer_content_profile(
            ("a", "b", "c"),
            label="labels",
            texts=texts,
            structurally_empty={sample: False for sample in texts},
        )
        assert profile["structurally_empty_answer_rate"] == pytest.approx(0.0)
        assert profile["distinct_contact0_texts"] == 3
        # Each answer carries two words the modal answer does not.
        assert profile["tokens_outside_the_group_modal_text_median"] == 2
        assert profile["answers_with_zero_tokens_outside_the_modal_text"] == 1


class TestTauDistance:
    def test_the_gap_is_measured_below_the_frozen_bar_only(self) -> None:
        gold = {"a": 0.62, "b": 0.64, "c": 0.70, "d": None}
        block = qkd.tau_distance(("a", "b", "c", "d"), label="fixture", gold_cosines=gold)
        assert block["tau"] == pytest.approx(0.65)
        assert block["n_with_gold_facet_in_kb"] == 3
        assert block["gold_facet_below_tau"] == 2
        assert block["gold_facet_at_or_above_tau"] == 1
        assert block["gap_to_tau_min"] == pytest.approx(0.01)
        assert block["gap_to_tau_max"] == pytest.approx(0.03)
        assert block["gap_to_tau_within_0_05"] == 2
        assert block["below_tau_cosine_min"] == pytest.approx(0.62)

    def test_an_exact_boundary_gap_is_not_counted_and_that_is_documented(self) -> None:
        """``tau - 0.60`` is 0.05000000000000004 in binary float, so the
        ``<= 0.05`` bucket excludes it. The landed measurement carries no gap
        within float epsilon of a bucket edge (the closest is 0.050749), so no
        published count depends on this; the behaviour is pinned here so a
        later reader does not mistake it for a bug or "fix" it silently into a
        different statistic."""

        block = qkd.tau_distance(("a",), label="fixture", gold_cosines={"a": 0.60})
        assert block["gap_to_tau_min"] > 0.05
        assert block["gap_to_tau_within_0_05"] == 0
        assert block["gap_to_tau_within_0_10"] == 1

    def test_a_group_with_no_gold_facet_reports_nulls_not_zeros(self) -> None:
        block = qkd.tau_distance(("a",), label="fixture", gold_cosines={"a": None})
        assert block["n_with_gold_facet_in_kb"] == 0
        assert block["gold_facet_below_tau_rate"] is None
        assert block["gap_to_tau_median"] is None


class TestFalsifierShape:
    """The deliverable's own shape is a gate: a one-sided falsifier is exactly
    the defect the K1 gate was faulted for."""

    @staticmethod
    def _falsifier() -> dict[str, object]:
        block = {
            "degeneracy": {
                "dead_direct": {"distinct_query_vectors_per_trajectory": 0.333},
                "label_recovered": {"distinct_query_vectors_per_trajectory": 0.944},
            }
        }
        half = {
            "degeneracy": {
                "dead_direct": {"distinct_query_vectors_per_trajectory": 0.85},
                "label_recovered": {"distinct_query_vectors_per_trajectory": 0.685},
            }
        }
        return qkd.separated_query_falsifier(block, {"HALF": half})

    def test_it_is_two_sided(self) -> None:
        falsifier = self._falsifier()
        assert falsifier["must_improve"]
        assert falsifier["must_not_degrade"]

    def test_it_carries_a_dispatch_preservation_clause(self) -> None:
        falsifier = self._falsifier()
        assert "D1" in falsifier["must_not_degrade"]
        assert "dispatch" in str(falsifier["must_not_degrade"]["D1"]).lower()

    def test_it_carries_the_degeneracy_clause_on_both_sides(self) -> None:
        falsifier = self._falsifier()
        assert "I3" in falsifier["must_improve"]
        assert "D5" in falsifier["must_not_degrade"]

    def test_it_names_its_trap_category(self) -> None:
        falsifier = self._falsifier()
        assert "SEPARATES" in str(falsifier["trap_category"]["category"])

    def test_the_anchors_are_measured_per_carrier(self) -> None:
        anchors = self._falsifier()["measured_anchors"]
        assert anchors["audio2tool_A2T_G1_104"][
            "dead_direct_distinct_query_vectors_per_trajectory"
        ] == pytest.approx(0.333)
        assert anchors["slurp_HALF"][
            "label_recovered_distinct_query_vectors_per_trajectory"
        ] == pytest.approx(0.685)
