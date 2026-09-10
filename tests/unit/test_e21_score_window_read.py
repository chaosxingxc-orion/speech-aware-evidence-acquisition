"""Synthetic checks for saved-score partitioning; no references or model service."""

from copy import deepcopy

import pytest

from speech_aware_evidence_acquisition.analysis.e21_score_window_read import (
    decompose_scored_windows,
)
from speech_aware_evidence_acquisition.analysis.e21_window_pairing import WindowSpan
from speech_aware_evidence_acquisition.core.scorers import _conec_alignment_payload
from speech_aware_evidence_acquisition.reproduction import conec_entity_scoring as conec
from speech_aware_evidence_acquisition.reproduction import (
    numeric_value_accuracy as numeric,
)


def fixture(texts=("alice paid", "$20 today"), refs=None):
    spans = tuple(
        WindowSpan("call1", i + 1, f"r{i}", i * 90, (i + 1) * 90, 90, text)
        for i, text in enumerate(texts)
    )
    words = conec.hypothesis_whisper_words(" ".join(texts))
    refs = words if refs is None else refs
    owners = [("p1",)] + [()] * (len(refs) - 1)
    operations = conec.aligned_operations(refs, words)
    buckets = conec.entity_wer_buckets(operations, owners, {"p1": "PERSON"})
    row = {
        "sample_id": "call1",
        "by_entity_type": buckets,
        "alignment": _conec_alignment_payload(
            refs, words, operations, owners, {"p1": "PERSON"}
        ),
    }
    counts = numeric.numeric_value_counts(refs, words)
    counts["sample_id"] = "call1"
    doc = {
        "verified": True,
        "scores": {
            "conec-entity-wer-official": {
                "per_sample": [row],
                "aggregate": {"by_entity_type": buckets},
            },
            "numeric-value-accuracy-v1": {
                "per_sample": [counts],
                "aggregate": numeric.merge_numeric_counts([counts]),
            },
        },
    }
    return {"call1": spans}, doc


def test_partition_preserves_errors_entities_and_numeric_counts():
    windows, doc = fixture(refs=["bob", "paid", "$20", "yesterday"])
    result = decompose_scored_windows(windows, doc)
    overall = doc["scores"]["conec-entity-wer-official"]["aggregate"]["by_entity_type"][
        "__ALL__"
    ]
    for field in (
        "errors",
        "substitutions",
        "deletions",
        "insertions",
        "reference_words",
    ):
        assert result["aggregate"][field] == overall[field]
    assert len(result["rows"]) == 2
    assert result["entity_totals"]["PERSON"]["errors"] == 1
    assert result["per_call"][0]["numeric_matched_shortfall"] == 0
    assert result["reference_loader_invocations"] == 0
    retained = result["call_scores"]["conec-entity-wer-official"]
    assert (
        retained["aggregate"] == doc["scores"]["conec-entity-wer-official"]["aggregate"]
    )
    assert (
        retained["per_sample"][0]["by_entity_type"]
        == doc["scores"]["conec-entity-wer-official"]["per_sample"][0]["by_entity_type"]
    )
    assert "alignment" not in retained["per_sample"][0]


def test_whole_prefix_normalization_preserves_numeric_boundary_merge():
    windows, doc = fixture(("paid twenty", "one dollars today"))
    result = decompose_scored_windows(windows, doc)
    assert sum(row["hypothesis_words"] for row in result["rows"]) == len(
        doc["scores"]["conec-entity-wer-official"]["per_sample"][0]["alignment"][
            "hypothesis_words"
        ]
    )
    assert result["aggregate"]["errors"] == 0


def test_empty_window_and_trailing_deletion_remain_in_coverage():
    windows, doc = fixture(("hello", ""), refs=["hello", "world"])
    result = decompose_scored_windows(windows, doc)
    assert len(result["rows"]) == 2
    assert result["aggregate"]["deletions"] == 1


@pytest.mark.parametrize(
    "mutation", ["unverified", "missing_alignment", "hypothesis", "totals", "roster"]
)
def test_refuses_unbound_or_inconsistent_saved_statistics(mutation):
    windows, doc = fixture()
    doc = deepcopy(doc)
    if mutation == "unverified":
        doc["verified"] = False
    elif mutation == "missing_alignment":
        del doc["scores"]["conec-entity-wer-official"]["per_sample"][0]["alignment"]
    elif mutation == "hypothesis":
        windows, _ = fixture(("bob paid", "$20 today"))
    elif mutation == "totals":
        doc["scores"]["conec-entity-wer-official"]["aggregate"]["by_entity_type"][
            "__ALL__"
        ]["insertions"] += 1
    else:
        windows = {"wrong": next(iter(windows.values()))}
    with pytest.raises(ValueError):
        decompose_scored_windows(windows, doc)
