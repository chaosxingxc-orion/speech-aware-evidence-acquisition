"""Complete saved raw scores settle without rescoring or changing sealed bytes."""

from __future__ import annotations

import json

import pytest
import test_e21_repair_loop as repair_fixtures
from test_delivery_settlement import _world

from speech_aware_evidence_acquisition.core.attempts import AttemptError
from speech_aware_evidence_acquisition.core.bundle import BundleError, settlement
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    SavedScoreReceiptRef,
    capture_score_source,
    write_complete_score_receipt,
)

repair_repo = repair_fixtures.repair_repo


def _score(bundle, target):
    target.mkdir(parents=True)
    result = target / "score.json"
    result.write_text(json.dumps({
        "manifest": str(bundle.manifest_path), "verified": True,
        "scores": {
            name: {
                "aggregate": {"fixture": 1},
                "per_sample": [] if name == "cost" else [
                    {"sample_id": sid} for sid in sorted(bundle.split_ids)
                ],
            }
            for name in bundle.manifest["scorers"]
        },
    }))
    ref = write_complete_score_receipt(
        target / "receipt.json", job_id="raw-score", result_path=result,
        source=capture_score_source(bundle), verified_bundle=bundle,
    )
    return ref, result


def _raw_world(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.bundle import git_commit

    world = _world(tmp_path, monkeypatch, cells=())
    parent = world["parent"]
    parent.manifest.pop("required_phase_deliveries")
    parent.manifest_path.write_text(json.dumps(parent.manifest, sort_keys=True))
    document = {"cells": [{
        "cell_id": "generation", "model_fragment": "m",
        "dataset_fragment": "d", "baseline_fragment": "b",
    }]}
    monkeypatch.setattr(
        git_commit, "_git",
        lambda *args: (0, json.dumps(document) if args[-2] == "show" else "", ""),
    )
    ref, result = _score(parent, world["data"] / "raw-score")
    world.update(ref=ref, result=result, experiment=document)
    return world


def _settle(world, **overrides):
    args = dict(
        repo_root=world["repo"], score_receipt=world["ref"],
        settlement_path=world["settlement"],
    )
    args.update(overrides)
    return settlement.settle_scored_attempt(world["parent"].manifest_path, **args)


def test_saved_raw_score_finalizes_once_without_rescoring_or_source_rewrite(
    synthetic_world, tmp_path, repair_repo, monkeypatch,
):
    from test_delivery_bundle import generation
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.core import scorers

    generate = generation.__wrapped__(
        synthetic_world, tmp_path, repair_repo, monkeypatch,
    )
    parent_path, kwargs = generate(declared_deliveries=False)
    parent = verify_bundle(parent_path)
    ref, score = _score(parent, synthetic_world.data_root / "raw-score")
    originals = {
        p: p.read_bytes() for p in (parent_path, parent.outputs_path, score, ref.path)
    }
    monkeypatch.setattr(
        scorers, "score_bundle",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("settlement cannot score")
        ),
    )
    target = synthetic_world.data_root / "settlements/raw.json"
    args = dict(
        repo_root=kwargs["repo_root"], score_receipt=ref, settlement_path=target,
    )
    first = settlement.settle_scored_attempt(parent_path, **args)
    retry = settlement.settle_scored_attempt(parent_path, **args)
    assert first.attempt_state == "FINALIZED" and not first.reused
    assert retry.reused and retry.receipt_sha256 == first.receipt_sha256
    receipt = settlement.verify_scored_attempt_settlement(
        target, repo_root=kwargs["repo_root"],
    )
    assert receipt["schema"] == "saea-scored-attempt-settlement-v1"
    assert receipt["score"]["score_receipt"]["sha256"] == ref.sha256
    assert all(p.read_bytes() == raw for p, raw in originals.items())
    with pytest.raises(BundleError, match="schema"):
        settlement.verify_delivery_settlement(target, repo_root=kwargs["repo_root"])


@pytest.mark.parametrize("case", ["phase", "legacy"])
def test_raw_settlement_cannot_bypass_registered_deliveries(tmp_path, monkeypatch, case):
    world = _raw_world(tmp_path, monkeypatch)
    if case == "phase":
        world["parent"].manifest["required_phase_deliveries"] = []
    else:
        world["experiment"]["delivery_derivatives"] = [{
            "cell_id": "free", "parent_cell_id": "generation",
            "response_postprocessor": "e21-free-transcript-v1",
            "response_postprocessor_params": {},
        }]
    with pytest.raises(BundleError, match="deliver"):
        _settle(world)
    assert world["attempt"].state() == "OPENED"
    assert not world["settlement"].exists()


@pytest.mark.parametrize("case", ["receipt", "score", "manifest", "cell", "aborted"])
def test_raw_settlement_rejects_changed_evidence_and_terminal_attempt(
    tmp_path, monkeypatch, case,
):
    world = _raw_world(tmp_path, monkeypatch)
    if case == "receipt":
        world["ref"].path.write_text(world["ref"].path.read_text() + " ")
    elif case == "score":
        world["result"].write_text(world["result"].read_text() + " ")
    elif case == "manifest":
        path = world["parent"].manifest_path
        path.write_text(path.read_text() + " ")
    elif case == "cell":
        ref = world["ref"]
        world["ref"] = SavedScoreReceiptRef("foreign", ref.path, ref.sha256)
    else:
        world["attempt"].mark_aborted("fixture terminal failure")
    with pytest.raises(BundleError):
        _settle(world)
    assert world["attempt"].state() != "FINALIZED"
    assert not world["settlement"].exists()


def test_raw_settlement_crash_and_exact_retry_preserve_one_binding(tmp_path, monkeypatch):
    world = _raw_world(tmp_path, monkeypatch)
    original = settlement.AttemptHandle.finalize_with_receipt
    monkeypatch.setattr(
        settlement.AttemptHandle, "finalize_with_receipt",
        lambda *args, **kwargs: (_ for _ in ()).throw(AttemptError("injected crash")),
    )
    with pytest.raises(BundleError, match="injected crash"):
        _settle(world)
    assert world["settlement"].exists()
    assert world["attempt"].state() == "OPENED"
    monkeypatch.setattr(settlement.AttemptHandle, "finalize_with_receipt", original)
    assert _settle(world).reused
    raw = world["settlement"].read_bytes()
    world["settlement"].write_bytes(raw + b" ")
    with pytest.raises(BundleError, match="does not bind"):
        settlement.verify_scored_attempt_settlement(
            world["settlement"], repo_root=world["repo"],
        )


def test_raw_settlement_confines_output_and_refuses_overwrite(tmp_path, monkeypatch):
    world = _raw_world(tmp_path, monkeypatch)
    with pytest.raises(BundleError, match="data root"):
        _settle(world, settlement_path=tmp_path / "outside.json")
    world["settlement"].parent.mkdir(parents=True)
    world["settlement"].write_text("{}")
    with pytest.raises(BundleError, match="existing"):
        _settle(world)
    assert world["attempt"].state() == "OPENED"


@pytest.mark.parametrize("case", ["incomplete", "derivative", "cost", "missing-receipt"])
def test_raw_settlement_requires_complete_ordinary_parent_and_saved_score(
    tmp_path, monkeypatch, case,
):
    world = _raw_world(tmp_path, monkeypatch)
    if case == "incomplete":
        world["parent"].manifest["status"] = "FAILED"
    elif case == "derivative":
        world["parent"].manifest["schema"] = "saea-derived-delivery-v1"
    elif case == "cost":
        world["parent"].manifest.pop("cost")
    else:
        world["ref"].path.unlink()
    with pytest.raises(BundleError):
        _settle(world)
    assert not world["settlement"].exists()


@pytest.mark.parametrize("case", ["json", "schema", "extra", "score", "parent"])
def test_raw_settlement_verifier_rejects_malformed_saved_receipt(
    tmp_path, monkeypatch, case,
):
    world = _raw_world(tmp_path, monkeypatch)
    _settle(world)
    path = world["settlement"]
    document = json.loads(path.read_text())
    if case == "json":
        path.write_text("{")
    else:
        if case == "schema":
            document["schema"] = "unknown"
        elif case == "extra":
            document["extra"] = "unbound"
        elif case == "score":
            document["score"] = None
        else:
            document["parent"] = None
        path.write_text(json.dumps(document))
    with pytest.raises(BundleError):
        settlement.verify_scored_attempt_settlement(path, repo_root=world["repo"])
