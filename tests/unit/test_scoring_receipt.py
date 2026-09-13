"""Complete, source-bound score receipts remain independently verifiable."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    SavedScoreReceiptRef,
    ScoreReceiptError,
    capture_score_source,
    verify_complete_score_receipt,
    write_complete_score_receipt,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle(tmp_path: Path) -> VerifiedBundle:
    tmp_path.mkdir(parents=True, exist_ok=True)
    parent = tmp_path / "parent.run-manifest.json"
    parent.write_text("parent", encoding="utf-8")
    outputs = tmp_path / "delivery.outputs.jsonl"
    outputs.write_text('{"sample_id":"s1"}\n{"sample_id":"s2"}\n', encoding="utf-8")
    manifest = tmp_path / "delivery.run-manifest.json"
    document = {
        "schema": "saea-derived-delivery-v1",
        "run_id": "parent--delivery-paired",
        "declaration": {"cell_id": "paired"},
        "parent": {"path": str(parent), "sha256": _sha(parent)},
        "config": {"config_hash": "a" * 64},
        "split": {"identity_hash": "b" * 64, "count": 2, "ids": ["s1", "s2"]},
        "scorers": ["official", "cost"],
        "outputs": {"path": str(outputs), "sha256": _sha(outputs)},
    }
    manifest.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    return VerifiedBundle(
        manifest, document, outputs,
        ({"sample_id": "s1"}, {"sample_id": "s2"}), {}, frozenset({"s1", "s2"}), "DERIVED",
    )


def _result(bundle: VerifiedBundle, *, ids=("s1", "s2")) -> dict:
    return {
        "manifest": str(bundle.manifest_path),
        "verified": True,
        "scores": {
            "official": {
                "aggregate": {"score": 1.0},
                "per_sample": [{"sample_id": sample_id} for sample_id in ids],
            },
            "cost": {"aggregate": {"calls": 0}, "per_sample": []},
        },
    }


def _write_receipt(tmp_path: Path, bundle: VerifiedBundle, result=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    result_path = tmp_path / "paired.score.json"
    result_path.write_text(json.dumps(result or _result(bundle)), encoding="utf-8")
    snapshot = capture_score_source(bundle)
    receipt_path = tmp_path / "paired.complete-score-receipt.json"
    write_complete_score_receipt(
        receipt_path,
        job_id="paired",
        result_path=result_path,
        source=snapshot,
        verified_bundle=bundle,
    )
    ref = SavedScoreReceiptRef("paired", receipt_path, _sha(receipt_path))
    return ref, result_path


def test_complete_receipt_binds_source_result_and_full_roster(tmp_path):
    bundle = _bundle(tmp_path)
    ref, _ = _write_receipt(tmp_path, bundle)

    verified = verify_complete_score_receipt(ref, bundle)

    assert verified["identity"]["cell_id"] == "paired"
    assert verified["identity"]["parent"] == bundle.manifest["parent"]
    assert verified["scorers"] == ["official", "cost"]


@pytest.mark.parametrize("ids", [("s1",), ("s1", "s1"), ("s1", "foreign")])
def test_complete_receipt_refuses_missing_duplicate_or_foreign_rows(tmp_path, ids):
    bundle = _bundle(tmp_path)
    with pytest.raises(ScoreReceiptError, match="complete roster"):
        _write_receipt(tmp_path, bundle, _result(bundle, ids=ids))


def test_independent_verification_refuses_changed_result_or_manifest(tmp_path):
    bundle = _bundle(tmp_path)
    ref, result_path = _write_receipt(tmp_path, bundle)
    result_path.write_text(result_path.read_text() + " ", encoding="utf-8")
    with pytest.raises(ScoreReceiptError, match="score result hash mismatch"):
        verify_complete_score_receipt(ref, bundle)

    second_dir = tmp_path / "second"
    second_bundle = _bundle(second_dir)
    ref, _ = _write_receipt(second_dir, second_bundle)
    second_bundle.manifest_path.write_text("changed", encoding="utf-8")
    with pytest.raises(ScoreReceiptError, match="manifest hash mismatch"):
        verify_complete_score_receipt(ref, second_bundle)


def test_independent_verification_refuses_changed_outputs_and_identity(tmp_path):
    bundle = _bundle(tmp_path)
    ref, _ = _write_receipt(tmp_path, bundle)
    bundle.outputs_path.write_text(bundle.outputs_path.read_text() + "{}\n")
    with pytest.raises(ScoreReceiptError, match="outputs hash mismatch"):
        verify_complete_score_receipt(ref, bundle)

    second = _bundle(tmp_path / "identity")
    ref, _ = _write_receipt(tmp_path / "identity", second)
    changed = dict(second.manifest)
    changed["config"] = {"config_hash": "d" * 64}
    changed_bundle = VerifiedBundle(
        second.manifest_path, changed, second.outputs_path, second.outputs_rows,
        second.trace_records, second.split_ids, second.attempt_state,
    )
    with pytest.raises(ScoreReceiptError, match="source identity mismatch"):
        verify_complete_score_receipt(ref, changed_bundle)


def test_independent_verification_refuses_changed_receipt_bytes(tmp_path):
    bundle = _bundle(tmp_path)
    ref, _ = _write_receipt(tmp_path, bundle)
    ref.path.write_text(ref.path.read_text() + " ")
    with pytest.raises(ScoreReceiptError, match="receipt hash mismatch"):
        verify_complete_score_receipt(ref, bundle)


@pytest.mark.parametrize(
    ("case", "match"),
    [
        ("unverified", "not verified"),
        ("wrong-manifest", "manifest identity"),
        ("missing-scorer", "configured scorers"),
        ("missing-shape", "aggregate and per_sample"),
    ],
)
def test_complete_receipt_refuses_noncomplete_score_shapes(tmp_path, case, match):
    bundle = _bundle(tmp_path)
    result = _result(bundle)
    if case == "unverified":
        result["verified"] = False
    elif case == "wrong-manifest":
        result["manifest"] = str(tmp_path / "foreign.run-manifest.json")
    elif case == "missing-scorer":
        result["scores"].pop("cost")
    elif case == "missing-shape":
        result["scores"]["official"].pop("per_sample")
    with pytest.raises(ScoreReceiptError, match=match):
        _write_receipt(tmp_path, bundle, result)


def test_independent_verification_refuses_cell_and_result_confinement_changes(tmp_path):
    bundle = _bundle(tmp_path)
    ref, _ = _write_receipt(tmp_path, bundle)
    with pytest.raises(ScoreReceiptError, match="cell identity"):
        verify_complete_score_receipt(
            SavedScoreReceiptRef("foreign", ref.path, ref.sha256), bundle
        )

    document = json.loads(ref.path.read_text())
    foreign = tmp_path.parent / "foreign.score.json"
    foreign.write_text(json.dumps(_result(bundle)))
    document["score_result"] = {"path": str(foreign), "sha256": _sha(foreign)}
    ref.path.write_text(json.dumps(document))
    changed_ref = SavedScoreReceiptRef("paired", ref.path, _sha(ref.path))
    with pytest.raises(ScoreReceiptError, match="result path"):
        verify_complete_score_receipt(changed_ref, bundle)


def test_cost_per_sample_list_is_exempt_from_roster_matching(tmp_path):
    bundle = _bundle(tmp_path)
    result = _result(bundle)
    result["scores"]["cost"]["per_sample"] = [{"diagnostic": "not roster-scored"}]
    ref, _ = _write_receipt(tmp_path, bundle, result)
    assert verify_complete_score_receipt(ref, bundle)["status"] == "complete"


def test_nonmapping_per_sample_row_and_nonstring_reference_hash_refuse(tmp_path):
    bundle = _bundle(tmp_path)
    result = _result(bundle)
    result["scores"]["official"]["per_sample"] = [
        {"sample_id": "s1"}, "not-a-row"
    ]
    with pytest.raises(ScoreReceiptError, match="complete roster"):
        _write_receipt(tmp_path, bundle, result)

    ref, _ = _write_receipt(tmp_path / "valid", _bundle(tmp_path / "valid"))
    with pytest.raises(ScoreReceiptError, match="reference is invalid"):
        verify_complete_score_receipt(
            SavedScoreReceiptRef(ref.cell_id, ref.path, 7), _bundle(tmp_path / "valid")
        )


def _finalized_bundle(tmp_path, *, ids=("s1", "s2")):
    from dataclasses import replace

    bundle = _bundle(tmp_path)
    document = dict(bundle.manifest)
    document["status"] = "COMPLETED"
    document.pop("declaration")
    document.pop("parent")
    scores = tmp_path / "run.scores.json"
    scores.write_text(json.dumps(_result(bundle, ids=ids)["scores"]), encoding="utf-8")
    document["scores"] = {"path": str(scores), "sha256": _sha(scores)}
    bundle.manifest_path.write_text(json.dumps(document), encoding="utf-8")
    return replace(bundle, manifest=document, attempt_state="FINALIZED")


def test_reuse_finalized_scores_preserves_originals_and_is_verifiable(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core import scoring_receipt as module

    bundle = _finalized_bundle(tmp_path / "run")
    before = {path: path.read_bytes() for path in (tmp_path / "run").iterdir()}
    reference = module.write_complete_saved_score_receipt(
        tmp_path / "reuse", job_id="original-finalize-job", verified_bundle=bundle,
    )

    document = verify_complete_score_receipt(reference, bundle)
    result = json.loads(Path(document["score_result"]["path"]).read_text())
    assert result["scores"] == json.loads(Path(bundle.manifest["scores"]["path"]).read_text())
    assert reference.cell_id == "original-finalize-job"
    assert {path: path.read_bytes() for path in before} == before
    source = json.loads((tmp_path / "reuse/source-reuse.json").read_text())
    assert source["scorer_invocations"] == 0
    assert source["source_scores"] == bundle.manifest["scores"]
    assert source["complete_score_receipt"]["sha256"] == reference.sha256
    assert source["source_manifest"] == document["manifest"]


@pytest.mark.parametrize("state", ["OPENED", "ABORTED", "DERIVED"])
def test_reuse_refuses_unfinalized_source(tmp_path, state):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core import scoring_receipt as module

    bundle = replace(_finalized_bundle(tmp_path / "run"), attempt_state=state)
    with pytest.raises(ScoreReceiptError, match="FINALIZED/COMPLETED"):
        module.write_complete_saved_score_receipt(
            tmp_path / "reuse", job_id="job", verified_bundle=bundle,
        )
    assert not (tmp_path / "reuse").exists()


def test_reuse_refuses_changed_saved_scores_before_writing(tmp_path):
    from speech_aware_evidence_acquisition.core import scoring_receipt as module

    bundle = _finalized_bundle(tmp_path / "run")
    Path(bundle.manifest["scores"]["path"]).write_text("{}")
    with pytest.raises(ScoreReceiptError, match="saved score.*hash"):
        module.write_complete_saved_score_receipt(
            tmp_path / "reuse", job_id="job", verified_bundle=bundle,
        )
    assert not (tmp_path / "reuse").exists()


@pytest.mark.parametrize("ids", [("s1",), ("s1", "s1"), ("s1", "foreign")])
def test_reuse_refuses_incomplete_saved_scoring(tmp_path, ids):
    from speech_aware_evidence_acquisition.core import scoring_receipt as module

    bundle = _finalized_bundle(tmp_path / "run", ids=ids)
    with pytest.raises(ScoreReceiptError, match="complete roster"):
        module.write_complete_saved_score_receipt(
            tmp_path / "reuse", job_id="job", verified_bundle=bundle,
        )
    assert not (tmp_path / "reuse").exists()


def test_reuse_refuses_overwrite(tmp_path):
    from speech_aware_evidence_acquisition.core import scoring_receipt as module

    bundle = _finalized_bundle(tmp_path / "run")
    destination = tmp_path / "reuse"
    module.write_complete_saved_score_receipt(
        destination, job_id="job", verified_bundle=bundle,
    )
    before = {path: path.read_bytes() for path in destination.iterdir()}
    with pytest.raises(ScoreReceiptError, match="fresh.*directory"):
        module.write_complete_saved_score_receipt(
            destination, job_id="job", verified_bundle=bundle,
        )
    assert {path: path.read_bytes() for path in before} == before
