"""Complete derived scoring binds one verified parent and never reruns a side."""
import hashlib
import json
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.core import scoring_batch
from speech_aware_evidence_acquisition.core.base import SCORERS, CoreError

SCORER = "test-derived-complete-score-v1"
CALLS = []


def _score(path, _lock, _root):
    CALLS.append(str(path))
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    return {
        "aggregate": {"identity_check": {"passed": True},
                      "official": {"slu_f1": 0.5, "intent_accuracy": 0.5}},
        "per_sample": [{"sample_id": row["sample_id"], "slu_f1_f1": 0.5}
                       for row in rows],
    }


try:
    SCORERS.register(SCORER, _score)
except CoreError:
    pass


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
