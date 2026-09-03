"""Tests for pure post-seal retrieval-reachability analysis."""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_retrieval_reachability import (
    DIMENSIONS,
    RetrievalReachabilityError,
    RetrievalReachabilitySample,
    audit_retrieval_reachability_at_k,
)


def _sample(
    sample_id: str = "sample-b",
    *,
    sealed: bool = True,
    required_tool_ids: tuple[str, ...] = ("tool-a", "tool-b"),
    ranked_tool_ids: tuple[str, ...] = ("tool-a", "tool-x", "tool-b"),
    required_skeleton_ids: tuple[str, ...] = ("skeleton-a",),
    ranked_skeleton_ids: tuple[str, ...] = ("skeleton-x", "skeleton-a"),
    required_value_rule_ids: tuple[str, ...] = ("rule-a",),
    ranked_value_rule_ids: tuple[str, ...] = ("rule-a", "rule-x"),
) -> RetrievalReachabilitySample:
    return RetrievalReachabilitySample(
        sample_id=sample_id,
        retrieval_sealed=sealed,
        required_tool_ids=required_tool_ids,
        ranked_tool_ids=ranked_tool_ids,
        required_skeleton_ids=required_skeleton_ids,
        ranked_skeleton_ids=ranked_skeleton_ids,
        required_value_rule_ids=required_value_rule_ids,
        ranked_value_rule_ids=ranked_value_rule_ids,
    )


def test_reports_per_sample_metrics_for_each_dimension_at_k() -> None:
    result = audit_retrieval_reachability_at_k(samples=(_sample(),), k=2)

    assert result.k == 2
    assert result.dimensions == DIMENSIONS
    sample = result.samples[0]
    tool = sample.metrics["tool"]
    assert tool.required_count == 2
    assert tool.retrieved_count_at_k == 2
    assert tool.matched_required_count_at_k == 1
    assert tool.required_item_recall_at_k == 0.5
    assert tool.full_set_coverage_at_k is False
    assert tool.distractor_burden_at_k == 1
    assert tool.precision_at_k == 0.5

    skeleton = sample.metrics["skeleton"]
    assert skeleton.required_item_recall_at_k == 1.0
    assert skeleton.full_set_coverage_at_k is True
    assert skeleton.distractor_burden_at_k == 1
    assert skeleton.precision_at_k == 0.5

    value_rule = sample.metrics["value_rule"]
    assert value_rule.required_item_recall_at_k == 1.0
    assert value_rule.full_set_coverage_at_k is True
    assert value_rule.distractor_burden_at_k == 1
    assert value_rule.precision_at_k == 0.5


def test_aggregate_metrics_are_micro_ratios_and_sample_coverage_fraction() -> None:
    samples = (
        _sample(sample_id="sample-b"),
        _sample(
            sample_id="sample-a",
            required_tool_ids=("tool-c",),
            ranked_tool_ids=("tool-z", "tool-c"),
            required_skeleton_ids=(),
            ranked_skeleton_ids=("skeleton-z",),
            required_value_rule_ids=("rule-b",),
            ranked_value_rule_ids=(),
        ),
    )

    result = audit_retrieval_reachability_at_k(samples=samples, k=2)

    assert tuple(sample.sample_id for sample in result.samples) == (
        "sample-a",
        "sample-b",
    )
    tool = result.aggregate["tool"]
    assert tool.sample_count == 2
    assert tool.total_required_count == 3
    assert tool.total_retrieved_count_at_k == 4
    assert tool.total_matched_required_count_at_k == 2
    assert tool.required_item_recall_at_k == pytest.approx(2 / 3)
    assert tool.full_set_coverage_at_k == 0.5
    assert tool.total_distractor_burden_at_k == 2
    assert tool.mean_distractor_burden_at_k == 1.0
    assert tool.precision_at_k == 0.5

    skeleton = result.aggregate["skeleton"]
    assert skeleton.required_item_recall_at_k == 1.0
    assert skeleton.full_set_coverage_at_k == 1.0
    assert skeleton.total_distractor_burden_at_k == 2
    assert skeleton.precision_at_k == pytest.approx(1 / 3)

    value_rule = result.aggregate["value_rule"]
    assert value_rule.required_item_recall_at_k == 0.5
    assert value_rule.full_set_coverage_at_k == 0.5
    assert value_rule.precision_at_k == 0.5


def test_empty_required_and_retrieved_sets_have_explicit_vacuous_semantics() -> None:
    result = audit_retrieval_reachability_at_k(
        samples=(
            _sample(
                required_tool_ids=(),
                ranked_tool_ids=(),
                required_skeleton_ids=(),
                ranked_skeleton_ids=(),
                required_value_rule_ids=(),
                ranked_value_rule_ids=(),
            ),
        ),
        k=5,
    )

    for dimension in DIMENSIONS:
        per_sample = result.samples[0].metrics[dimension]
        aggregate = result.aggregate[dimension]
        assert per_sample.required_item_recall_at_k == 1.0
        assert per_sample.full_set_coverage_at_k is True
        assert per_sample.precision_at_k == 1.0
        assert aggregate.required_item_recall_at_k == 1.0
        assert aggregate.full_set_coverage_at_k == 1.0
        assert aggregate.precision_at_k == 1.0


def test_canonical_json_is_input_order_independent_and_scope_is_explicit() -> None:
    first = _sample(sample_id="sample-a")
    second = _sample(sample_id="sample-b")

    forward = audit_retrieval_reachability_at_k(samples=(first, second), k=3)
    reverse = audit_retrieval_reachability_at_k(samples=(second, first), k=3)

    assert forward.canonical_json() == reverse.canonical_json()
    payload = json.loads(forward.canonical_json())
    assert payload["schema"] == "saea-a2t-postseal-retrieval-reachability-v1"
    assert payload["analysis_phase"] == "post-seal"
    assert payload["runtime_eligible"] is False
    assert payload["upper_bound_kind"] == "retrieval-coverage-oracle"
    assert "not a model-consumption upper bound" in payload["scope_note"]
    assert "never be used at runtime" in payload["scope_note"]


@pytest.mark.parametrize("bad_k", (True, False, 0, -1, 1.0, "2"))
def test_rejects_invalid_k(bad_k: object) -> None:
    with pytest.raises(RetrievalReachabilityError, match="k must"):
        audit_retrieval_reachability_at_k(samples=(_sample(),), k=bad_k)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("sample_id", "", "sample_id"),
        ("retrieval_sealed", 1, "retrieval_sealed"),
        ("required_tool_ids", "tool-a", "sequence"),
        ("required_tool_ids", ("tool-a", "tool-a"), "duplicate"),
        ("required_tool_ids", ("tool-a", 7), "non-empty text"),
        ("ranked_skeleton_ids", ("",), "non-empty text"),
        ("ranked_value_rule_ids", ("rule-a", "rule-a"), "duplicate"),
    ),
)
def test_strictly_validates_sample_field_types_and_duplicates(
    field: str,
    value: object,
    message: str,
) -> None:
    values = _sample().__dict__ | {field: value}
    malformed = RetrievalReachabilitySample(**values)  # type: ignore[arg-type]

    with pytest.raises(RetrievalReachabilityError, match=message):
        audit_retrieval_reachability_at_k(samples=(malformed,), k=2)


def test_rejects_unsealed_and_duplicate_samples_and_non_sequence_input() -> None:
    with pytest.raises(RetrievalReachabilityError, match="not sealed"):
        audit_retrieval_reachability_at_k(samples=(_sample(sealed=False),), k=2)
    with pytest.raises(RetrievalReachabilityError, match="duplicate sample_id"):
        audit_retrieval_reachability_at_k(
            samples=(_sample(sample_id="same"), _sample(sample_id="same")),
            k=2,
        )
    with pytest.raises(RetrievalReachabilityError, match="samples must"):
        audit_retrieval_reachability_at_k(samples="not-a-sequence", k=2)  # type: ignore[arg-type]


def test_rejects_malformed_sample_object_and_empty_sample_collection() -> None:
    with pytest.raises(RetrievalReachabilityError, match=r"samples\[0\]"):
        audit_retrieval_reachability_at_k(samples=(object(),), k=1)  # type: ignore[arg-type]
    with pytest.raises(RetrievalReachabilityError, match="non-empty"):
        audit_retrieval_reachability_at_k(samples=(), k=1)
