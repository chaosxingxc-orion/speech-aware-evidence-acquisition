"""Complete derived scoring binds one verified parent and never reruns a side."""
import hashlib
import json
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.core import scoring_batch
from speech_aware_evidence_acquisition.core.base import SCORERS

SCORER = "test-derived-complete-score-v1"
CALLS = []
FAIL = {"mode": None}


def _score(path, _lock, _root):
    CALLS.append(str(path))
    assert (path.parent / "derived-scores.json.started.json").is_file()
    if FAIL["mode"] == "error":
        raise RuntimeError("synthetic scorer failure")
    if FAIL["mode"] == "interrupt":
        raise KeyboardInterrupt()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if FAIL["mode"] == "post_call":
        return {
            "aggregate": {"identity_check": {"passed": True}, "official": object()},
            "per_sample": [{"sample_id": row["sample_id"]} for row in rows],
        }
    return {
        "aggregate": {"identity_check": {"passed": True},
                      "official": {"slu_f1": 0.5, "intent_accuracy": 0.5}},
        "per_sample": [{"sample_id": row["sample_id"], "slu_f1_f1": 0.5}
                       for row in rows],
    }


@pytest.fixture(autouse=True)
def _registered_scorer(monkeypatch):
    # Registered per test and removed afterwards. It used to be registered at IMPORT time and never removed,
    # so from collection onward the process-global core.base.SCORERS carried a test-only id, and
    # test_engineering_base_check.py::test_regex_extraction_agrees_with_package_import (which compares the
    # registry against the canonical source scan) failed in every full-suite run while passing alone.
    monkeypatch.setitem(SCORERS._entries, SCORER, _score)


def _fixture(tmp_path, monkeypatch):
    parent = tmp_path / "runs" / "RUN" / "ATT" / "RUN.run-manifest.json"
    parent.parent.mkdir(parents=True)
    parent.write_text("{}")
    bundle = SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN",
                  "outputs": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", split_ids=frozenset(("a", "b")),
    )
    monkeypatch.setattr(scoring_batch, "verify_bundle", lambda path: bundle)
    copy = tmp_path / "copy.jsonl"
    copy.write_text("".join(json.dumps({"sample_id": sid, "text": "{}"}) + "\n"
                            for sid in ("a", "b")))
    return parent, copy


def _run(parent, copy, tmp_path):
    return scoring_batch.score_complete_derived_copy(
        parent_manifest=parent, outputs_copy=copy,
        expected_copy_sha256=hashlib.sha256(copy.read_bytes()).hexdigest(),
        scorer_id=SCORER, result_path=tmp_path / "derived-scores.json",
        lock={}, data_root=tmp_path, column_binding={"arm": "small", "visit": "first-solver"},
    )


def test_full_column_scores_once_and_reuses_exclusive_receipt(tmp_path, monkeypatch):
    CALLS.clear()
    FAIL["mode"] = None
    parent, copy = _fixture(tmp_path, monkeypatch)
    first = _run(parent, copy, tmp_path)
    assert len(CALLS) == 1
    assert _run(parent, copy, tmp_path) == first
    assert len(CALLS) == 1
    receipt = json.loads((tmp_path / "derived-scores.json.receipt.json").read_text())
    assert receipt["parent_run_id"] == "RUN"
    assert receipt["roster_count"] == 2
    assert receipt["scorer_id"] == SCORER
    assert receipt["column_binding"] == {"arm": "small", "visit": "first-solver"}
    parent.write_text("{\"changed\": true}")
    with pytest.raises(scoring_batch.ScoreBatchError, match="source binding"):
        _run(parent, copy, tmp_path)
    assert len(CALLS) == 1


def test_partial_column_and_modified_source_refused(tmp_path, monkeypatch):
    CALLS.clear()
    FAIL["mode"] = None
    parent, copy = _fixture(tmp_path, monkeypatch)
    copy.write_text(json.dumps({"sample_id": "a", "text": "{}"}) + "\n")
    with pytest.raises(scoring_batch.ScoreBatchError, match="complete parent roster"):
        _run(parent, copy, tmp_path)
    assert not CALLS
    copy.write_text("".join(json.dumps({"sample_id": sid, "text": "{}"}) + "\n"
                            for sid in ("a", "b")))
    _run(parent, copy, tmp_path)
    copy.write_text(copy.read_text() + " ")
    with pytest.raises(scoring_batch.ScoreBatchError):
        _run(parent, copy, tmp_path)


def test_missing_or_tampered_receipt_refuses_rescore(tmp_path, monkeypatch):
    CALLS.clear()
    FAIL["mode"] = None
    parent, copy = _fixture(tmp_path, monkeypatch)
    _run(parent, copy, tmp_path)
    receipt = tmp_path / "derived-scores.json.receipt.json"
    receipt.write_text("{}")
    with pytest.raises(scoring_batch.ScoreBatchError, match="source binding"):
        _run(parent, copy, tmp_path)
    assert len(CALLS) == 1
    receipt.unlink()
    with pytest.raises(scoring_batch.ScoreBatchError, match="partial derived score"):
        _run(parent, copy, tmp_path)
    assert len(CALLS) == 1


@pytest.mark.parametrize(("mode", "error"), [
    ("error", RuntimeError), ("interrupt", KeyboardInterrupt),
])
def test_failed_or_interrupted_invocation_cannot_be_retried(
    tmp_path, monkeypatch, mode, error
):
    CALLS.clear()
    FAIL["mode"] = mode
    parent, copy = _fixture(tmp_path, monkeypatch)
    try:
        with pytest.raises(error):
            _run(parent, copy, tmp_path)
    finally:
        FAIL["mode"] = None
    marker = tmp_path / "derived-scores.json.started.json"
    assert marker.is_file()
    started = json.loads(marker.read_text())
    assert started["parent_run_id"] == "RUN"
    assert started["outputs_copy_sha256"] == hashlib.sha256(copy.read_bytes()).hexdigest()
    assert started["column_binding"]["arm"] == "small"
    assert not (tmp_path / "derived-scores.json").exists()
    with pytest.raises(scoring_batch.ScoreBatchError, match="prior derived score invocation"):
        _run(parent, copy, tmp_path)
    assert len(CALLS) == 1


def test_post_invocation_result_failure_blocks_retry(tmp_path, monkeypatch):
    CALLS.clear()
    FAIL["mode"] = "post_call"
    parent, copy = _fixture(tmp_path, monkeypatch)
    try:
        with pytest.raises(TypeError):
            _run(parent, copy, tmp_path)
    finally:
        FAIL["mode"] = None
    assert (tmp_path / "derived-scores.json.started.json").is_file()
    assert not (tmp_path / "derived-scores.json").exists()
    with pytest.raises(scoring_batch.ScoreBatchError, match="prior derived score invocation"):
        _run(parent, copy, tmp_path)
    assert len(CALLS) == 1
