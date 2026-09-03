from __future__ import annotations

import json
import math

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_dense_candidate_validation import (
    DenseCandidateValidationError,
    analyze_dense_candidate_validation,
    reciprocal_rank_fusion,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _row(
    unit_id: str,
    *,
    query_idx: int,
    text: str,
    tool: str,
    tier: str = "tier1_direct",
    extras: tuple[str, ...] = (),
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=unit_id,
        tier=tier,
        query_idx=query_idx,
        text=text,
        domain="private",
        category="private",
        tool_id=query_idx,
        tool_name=tool,
        arg_signature=(),
        arg_pairs=(),
        call_render="PRIVATE",
        extra_call_names=extras,
        call_count=1 + len(extras),
        sample_ids=(unit_id,),
        item_ids=(query_idx,),
        media_relpath_by_sample_id={},
        speaker_ids=("private",),
    )


def _semantic_fixture() -> tuple[
    tuple[A2tKbRow, ...], dict[str, tuple[float, ...]], tuple[tuple[str, ...], ...]
]:
    rows = (
        _row("a-build", query_idx=0, text="quartz meadow", tool="alphaTool"),
        _row("b-build", query_idx=1, text="velvet harbor", tool="betaTool"),
        _row("c-build", query_idx=2, text="silver comet", tool="gammaTool"),
        _row(
            "a-valid",
            query_idx=3,
            text="opaque request one",
            tool="alphaTool",
            tier="tier4_implicit",
        ),
        _row(
            "b-valid",
            query_idx=4,
            text="opaque request two",
            tool="betaTool",
            tier="tier4_implicit",
        ),
        _row(
            "c-valid",
            query_idx=5,
            text="opaque request three",
            tool="gammaTool",
            tier="tier4_implicit",
        ),
    )
    vectors = {
        "a-build": (1.0, 0.0, 0.0),
        "b-build": (0.0, 1.0, 0.0),
        "c-build": (0.0, 0.0, 1.0),
        "a-valid": (0.99, 0.01, 0.0),
        "b-valid": (0.01, 0.99, 0.0),
        "c-valid": (0.0, 0.01, 0.99),
    }
    folds = (
        ("a-valid", "b-valid", "c-valid"),
        ("a-build", "b-build", "c-build"),
    )
    return rows, vectors, folds


def test_dense_centroids_recover_semantics_and_report_three_methods() -> None:
    rows, vectors, folds = _semantic_fixture()

    result = analyze_dense_candidate_validation(
        construction_rows=rows,
        vectors_by_unit_id=vectors,
        registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
        validation_folds=folds,
        k_grid=(1, 2),
        query_batch_size=2,
    )
    report = result.report

    assert report["schema"] == "saea-a2t-dense-candidate-validation-v2"
    assert set(report["methods"]) == {
        "bm25",
        "dense",
        "rrf",
        "dense_exemplar",
        "rrf_exemplar",
    }
    assert (
        report["methods"]["dense"]["pooled"]["k_metrics"]["1"]["full_set_coverage"]
        == 1.0
    )
    assert (
        report["methods"]["dense"]["pooled"]["k_metrics"]["1"]["full_set_coverage"]
        > report["methods"]["bm25"]["pooled"]["k_metrics"]["1"]["full_set_coverage"]
    )
    assert (
        report["methods"]["dense"]["pooled"]["per_tier"]["tier4_implicit"]["1"][
            "full_set_coverage"
        ]
        == 1.0
    )
    assert report["population"]["vector_dimension"] == 3
    assert report["dense_design"]["batched_matrix_cosine"] is True
    assert report["dense_exemplar_design"]["query_batch_size"] == 2
    assert (
        report["dense_exemplar_design"]["full_query_by_build_matrix_materialized"]
        is False
    )
    assert set(report["methods"]["dense"]["pooled"]["near_duplicate_sensitivity"]) >= {
        "threshold",
        "near_duplicate",
        "no_near_duplicate",
    }
    assert (
        report["methods"]["dense"]["pooled"]["near_duplicate_sensitivity"][
            "near_duplicate"
        ]["unit_count"]
        + report["methods"]["dense"]["pooled"]["near_duplicate_sensitivity"][
            "no_near_duplicate"
        ]["unit_count"]
        == 6
    )
    assert report["scope"]["construction_training_rows_only"] is True
    assert report["scope"]["caller_supplied_precomputed_vectors_only"] is True
    assert report["scope"]["model_contacts"] == 0
    assert report["scope"]["network_contacts"] == 0
    assert report["provenance"]["vector_values_emitted"] is False
    assert report["provenance"]["source_text_emitted"] is False
    assert len(report["provenance"]["validated_float64_vector_mapping_sha256"]) == 64
    assert (
        report["methods"]["dense_exemplar"]["pooled"]["near_duplicate_sensitivity"][
            "no_near_duplicate"
        ]["unit_count"]
        == 6
    )
    assert json.loads(result.canonical_json) == report
    assert "opaque request" not in result.canonical_json
    assert "0.99" not in result.canonical_json


def test_max_exemplar_recovers_a_multimodal_label_with_misleading_centroid() -> None:
    rows = (
        _row("a-positive", query_idx=0, text="source north", tool="alphaTool"),
        _row("a-negative", query_idx=1, text="source south", tool="alphaTool"),
        _row("b-mode", query_idx=2, text="source east", tool="betaTool"),
        _row(
            "a-query",
            query_idx=3,
            text="unseen wording",
            tool="alphaTool",
            tier="tier4_implicit",
        ),
    )
    vectors = {
        "a-positive": (1.0, 0.0),
        "a-negative": (-0.8, 0.6),
        "b-mode": (0.8, 0.6),
        "a-query": (1.0, 0.0),
    }

    report = analyze_dense_candidate_validation(
        construction_rows=rows,
        vectors_by_unit_id=vectors,
        registry_tool_names=("alphaTool", "betaTool"),
        validation_folds=(("a-query",), ("a-negative", "a-positive", "b-mode")),
        k_grid=(1,),
        query_batch_size=1,
    ).report

    assert (
        report["methods"]["dense_exemplar"]["pooled"]["k_metrics"]["1"][
            "full_set_coverage"
        ]
        > report["methods"]["dense"]["pooled"]["k_metrics"]["1"]["full_set_coverage"]
    )
    assert report["dense_exemplar_design"]["tool_score"] == (
        "maximum cosine over every build-row vector attached to the tool"
    )
    assert all(
        fold["maximum_exemplar_query_batch_rows"] <= 1 for fold in report["fold_design"]
    )


def test_dense_centroids_attach_extra_labels_to_each_build_row() -> None:
    rows = (
        _row(
            "build-ab",
            query_idx=0,
            text="source one",
            tool="alphaTool",
            extras=("betaTool",),
        ),
        _row("build-c", query_idx=1, text="source two", tool="gammaTool"),
        _row(
            "build-a",
            query_idx=2,
            text="source three",
            tool="alphaTool",
            tier="tier2_parametric",
        ),
        _row("valid-b", query_idx=3, text="target one", tool="betaTool"),
        _row("valid-c", query_idx=4, text="target two", tool="gammaTool"),
        _row(
            "valid-a",
            query_idx=5,
            text="target three",
            tool="alphaTool",
            tier="tier2_parametric",
        ),
    )
    vectors = {
        "build-ab": (1.0, 0.0),
        "build-c": (0.0, 1.0),
        "build-a": (0.8, 0.6),
        "valid-b": (1.0, 0.0),
        "valid-c": (0.0, 1.0),
        "valid-a": (0.8, 0.6),
    }

    report = analyze_dense_candidate_validation(
        construction_rows=rows,
        vectors_by_unit_id=vectors,
        registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
        validation_folds=(
            ("valid-a", "valid-b", "valid-c"),
            ("build-a", "build-ab", "build-c"),
        ),
        k_grid=(2,),
    ).report

    assert report["dense_design"]["primary_and_extra_labels_attached"] is True
    assert (
        report["methods"]["dense"]["pooled"]["k_metrics"]["2"]["full_set_coverage"]
        == 1.0
    )


def test_dense_analysis_accepts_numpy_vector_rows_without_python_tuple_copy() -> None:
    import numpy as np

    rows, vectors, folds = _semantic_fixture()
    array_vectors = {
        unit_id: np.asarray(vector, dtype=np.float32)
        for unit_id, vector in vectors.items()
    }

    report = analyze_dense_candidate_validation(
        construction_rows=rows,
        vectors_by_unit_id=array_vectors,
        registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
        validation_folds=folds,
        k_grid=(1,),
    ).report

    assert report["population"]["vector_dimension"] == 3
    assert (
        report["methods"]["dense"]["pooled"]["k_metrics"]["1"]["full_set_coverage"]
        == 1.0
    )


def test_rrf_combines_complementary_rankings_and_breaks_ties_by_tool_name() -> None:
    ranking = reciprocal_rank_fusion(
        ("alpha", "target", "beta", "gamma"),
        ("gamma", "target", "beta", "alpha"),
        constant=60,
    )

    assert ranking == ("target", "alpha", "gamma", "beta")


def test_seed_and_fold_count_generate_the_existing_grouped_assignment() -> None:
    rows, vectors, _folds = _semantic_fixture()

    report = analyze_dense_candidate_validation(
        construction_rows=rows,
        vectors_by_unit_id=vectors,
        registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
        seed=17,
        fold_count=2,
        k_grid=(1,),
    ).report

    assert report["split_policy"]["source"] == "existing_grouped_fold_assigner"
    assert report["population"]["fold_count"] == 2


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (
            lambda values: {
                key: value for key, value in values.items() if key != "a-build"
            },
            "exactly cover",
        ),
        (lambda values: {**values, "unknown": (1.0, 0.0, 0.0)}, "exactly cover"),
        (lambda values: {**values, "a-build": (1.0, 0.0)}, "same dimension"),
        (lambda values: {**values, "a-build": (0.0, 0.0, 0.0)}, "nonzero"),
        (lambda values: {**values, "a-build": (math.nan, 0.0, 0.0)}, "finite"),
    ),
)
def test_vector_validation_fails_closed(mutate, message: str) -> None:
    rows, vectors, folds = _semantic_fixture()

    with pytest.raises(DenseCandidateValidationError, match=message):
        analyze_dense_candidate_validation(
            construction_rows=rows,
            vectors_by_unit_id=mutate(vectors),
            registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
            validation_folds=folds,
            k_grid=(1,),
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({}, "exactly one fold source"),
        (
            {
                "validation_folds": (("a-valid", "b-valid", "c-valid"),),
            },
            "at least two",
        ),
        (
            {
                "validation_folds": (
                    ("a-valid", "b-valid", "c-valid"),
                    ("a-build", "b-build"),
                ),
            },
            "exactly once",
        ),
        (
            {
                "validation_folds": (
                    ("a-valid", "b-valid", "c-valid"),
                    ("a-build", "b-build", "unknown"),
                ),
            },
            "unknown unit",
        ),
    ),
)
def test_fold_validation_fails_closed(kwargs: dict[str, object], message: str) -> None:
    rows, vectors, _folds = _semantic_fixture()

    with pytest.raises(DenseCandidateValidationError, match=message):
        analyze_dense_candidate_validation(
            construction_rows=rows,
            vectors_by_unit_id=vectors,
            registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
            k_grid=(1,),
            **kwargs,
        )


def test_query_batch_size_must_be_a_positive_integer() -> None:
    rows, vectors, folds = _semantic_fixture()

    with pytest.raises(DenseCandidateValidationError, match="query_batch_size"):
        analyze_dense_candidate_validation(
            construction_rows=rows,
            vectors_by_unit_id=vectors,
            registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
            validation_folds=folds,
            k_grid=(1,),
            query_batch_size=0,
        )
