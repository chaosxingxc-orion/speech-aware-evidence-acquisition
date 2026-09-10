"""A raw phase attempt settles only from every verified scored derivative."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import pytest
import test_e21_repair_loop as repair_fixtures


from speech_aware_evidence_acquisition.core.attempts import AttemptError, AttemptStore
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.bundle.settlement import (
    SCHEMA,
    settle_phase_delivery_attempt,
    verify_phase_delivery_settlement,
)
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    SavedScoreReceiptRef,
    capture_score_source,
    write_complete_score_receipt,
)


repair_repo = repair_fixtures.repair_repo


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _world(tmp_path, monkeypatch, cells=("first", "second")):
    from speech_aware_evidence_acquisition.core.bundle import settlement

    data = tmp_path / "data"
    repo = tmp_path / "repo"
    repo.mkdir()
    attempt = AttemptStore(data / "attempts").open_attempt(
        "parent", "attempt-parent", carrier_lock_key="carrier",
        reserved_calls=2, reserved_audio_seconds=2.0,
    )
    outputs = data / "runs/parent/parent.outputs.jsonl"
    outputs.parent.mkdir(parents=True)
    outputs.write_text('{"sample_id":"s1"}\n{"sample_id":"s2"}\n')
    declarations = tuple({
        "cell_id": cell,
        "parent_cell_id": "generation",
        "response_postprocessor": "synthetic",
        "response_postprocessor_params": {},
        "source_selector": {
            "schema": "saea-phase-response-pair-v1",
            "program_id": "phase",
            "program_sha256": "d" * 64,
            "predecessor_phase": "draft",
            "response_phase": "revise",
        },
    } for cell in cells)
    parent_path = outputs.parent / "parent.run-manifest.json"
    parent_document = {
        "schema": "saea-run-manifest-v1",
        "status": "COMPLETED",
        "run_id": "parent",
        "study_commit": "e" * 40,
        "required_phase_deliveries": list(declarations),
        "attempt": {
            "state_path": str(attempt.path),
            "run_id": "parent",
            "attempt_id": "attempt-parent",
        },
        "cost": {"calls_used": 2, "audio_seconds": 2.0},
        "config": {
            "config_hash": "a" * 64,
            "fragments": {
                "model": "m", "dataset": "d", "baseline": "b", "experiment": "e"
            },
        },
        "split": {"identity_hash": "b" * 64, "count": 2, "ids": ["s1", "s2"]},
        "scorers": ["official", "cost"],
        "outputs": {"path": str(outputs), "sha256": _sha(outputs)},
    }
    parent_path.write_text(json.dumps(parent_document, sort_keys=True))
    parent = VerifiedBundle(
        parent_path, parent_document, outputs,
        ({"sample_id": "s1"}, {"sample_id": "s2"}), {},
        frozenset({"s1", "s2"}), "OPENED",
    )
    parent_meta = {"path": str(parent_path.resolve()), "sha256": _sha(parent_path)}
    bundles = {parent_path.resolve(): parent}
    refs = []
    derivatives = {}
    for cell, declaration in zip(cells, declarations):
        directory = data / "derived" / cell
        directory.mkdir(parents=True)
        derived_outputs = directory / f"{cell}.outputs.jsonl"
        derived_outputs.write_text(outputs.read_text())
        derived_manifest = directory / f"{cell}.run-manifest.json"
        derived_document = {
            "schema": "saea-derived-delivery-v1",
            "status": "COMPLETED",
            "run_id": f"parent--delivery-{cell}",
            "declaration": declaration,
            "parent": parent_meta,
            "config": {"config_hash": "a" * 64},
            "split": {"identity_hash": "b" * 64, "count": 2, "ids": ["s1", "s2"]},
            "scorers": ["official", "cost"],
            "outputs": {"path": str(derived_outputs), "sha256": _sha(derived_outputs)},
            "cost": {"calls_used": 0, "additional_model_contacts": 0},
        }
        derived_manifest.write_text(json.dumps(derived_document, sort_keys=True))
        derived = VerifiedBundle(
            derived_manifest.resolve(), derived_document, derived_outputs.resolve(),
            ({"sample_id": "s1"}, {"sample_id": "s2"}), {},
            frozenset({"s1", "s2"}), "DERIVED",
        )
        bundles[derived_manifest.resolve()] = derived
        derivatives[cell] = derived
        score_dir = data / "scores" / cell
        score_dir.mkdir(parents=True)
        result = score_dir / f"{cell}.score.json"
        result.write_text(json.dumps({
            "manifest": str(derived_manifest.resolve()),
            "verified": True,
            "scores": {
                "official": {
                    "aggregate": {"score": 1},
                    "per_sample": [{"sample_id": "s1"}, {"sample_id": "s2"}],
                },
                "cost": {"aggregate": {"calls_used": 0}, "per_sample": []},
            },
        }))
        receipt_path = score_dir / f"{cell}.complete-score-receipt.json"
        ref = write_complete_score_receipt(
            receipt_path, job_id=cell, result_path=result,
            source=capture_score_source(derived), verified_bundle=derived,
        )
        refs.append(ref)

    monkeypatch.setattr(
        settlement, "verify_bundle", lambda path: bundles[Path(path).resolve()]
    )
    monkeypatch.setattr(
        settlement, "recorded_phase_delivery_declarations",
        lambda bundle, repo_root: declarations,
    )
    return {
        "data": data, "repo": repo, "attempt": attempt, "parent": parent,
        "refs": refs, "derivatives": derivatives, "bundles": bundles,
        "settlement": data / "settlements/parent.json",
    }


def test_all_declared_scored_derivatives_finalize_once_and_exact_retry_converges(
    tmp_path, monkeypatch,
):
    world = _world(tmp_path, monkeypatch)
    raw = {
        path: path.read_bytes()
        for path in (
            world["parent"].manifest_path, world["parent"].outputs_path,
            *(bundle.manifest_path for bundle in world["derivatives"].values()),
            *(bundle.outputs_path for bundle in world["derivatives"].values()),
        )
    }

    result = settle_phase_delivery_attempt(
        world["parent"].manifest_path, repo_root=world["repo"],
        score_receipts=world["refs"], settlement_path=world["settlement"],
    )
    retry = settle_phase_delivery_attempt(
        world["parent"].manifest_path, repo_root=world["repo"],
        score_receipts=world["refs"], settlement_path=world["settlement"],
    )

    assert result.attempt_state == "FINALIZED" and result.reused is False
    assert retry.receipt_sha256 == result.receipt_sha256 and retry.reused is True
    attempt_document = json.loads(world["attempt"].path.read_text())
    assert attempt_document["state"] == "FINALIZED"
    assert attempt_document["finalization"] == {
        "path": str(world["settlement"].resolve()),
        "sha256": result.receipt_sha256,
        "kind": SCHEMA,
    }
    receipt = verify_phase_delivery_settlement(
        world["settlement"], repo_root=world["repo"]
    )
    assert [row["cell_id"] for row in receipt["deliveries"]] == ["first", "second"]
    assert receipt["parent"]["cost_attribution"] == "parent generation is charged once"
    assert all(row["cost"]["calls_used"] == 0 for row in receipt["deliveries"])
    assert all(path.read_bytes() == content for path, content in raw.items())


@pytest.mark.parametrize("case", ["missing", "extra", "duplicate"])
def test_settlement_requires_exactly_one_score_receipt_per_cell(
    tmp_path, monkeypatch, case,
):
    world = _world(tmp_path, monkeypatch)
    refs = list(world["refs"])
    if case == "missing":
        refs.pop()
    elif case == "extra":
        refs.append(SavedScoreReceiptRef("extra", refs[0].path, refs[0].sha256))
    else:
        refs.append(refs[0])
    with pytest.raises(BundleError, match="cover|required|repeat"):
        settle_phase_delivery_attempt(
            world["parent"].manifest_path, repo_root=world["repo"],
            score_receipts=refs, settlement_path=world["settlement"],
        )
    assert world["attempt"].state() == "OPENED"


def test_foreign_parent_or_changed_score_bytes_refuse_before_finalization(
    tmp_path, monkeypatch,
):
    world = _world(tmp_path, monkeypatch)
    first = world["derivatives"]["first"]
    original_parent = first.manifest["parent"]
    first.manifest["parent"] = {"path": "/foreign", "sha256": "f" * 64}
    with pytest.raises(BundleError, match="foreign parent"):
        settle_phase_delivery_attempt(
            world["parent"].manifest_path, repo_root=world["repo"],
            score_receipts=world["refs"], settlement_path=world["settlement"],
        )
    first.manifest["parent"] = original_parent

    score_result = Path(json.loads(world["refs"][0].path.read_text())["score_result"]["path"])
    score_result.write_text(score_result.read_text() + " ")
    with pytest.raises(BundleError, match="score result hash mismatch"):
        settle_phase_delivery_attempt(
            world["parent"].manifest_path, repo_root=world["repo"],
            score_receipts=world["refs"], settlement_path=world["settlement"],
        )
    assert world["attempt"].state() == "OPENED"


def test_crash_after_publish_leaves_exact_receipt_for_retry(
    tmp_path, monkeypatch,
):
    from speech_aware_evidence_acquisition.core.bundle import settlement

    world = _world(tmp_path, monkeypatch)
    real_finalize = settlement.AttemptHandle.finalize_with_receipt
    monkeypatch.setattr(
        settlement.AttemptHandle,
        "finalize_with_receipt",
        lambda *args, **kwargs: (_ for _ in ()).throw(AttemptError("injected crash")),
    )
    with pytest.raises(BundleError, match="injected crash"):
        settle_phase_delivery_attempt(
            world["parent"].manifest_path, repo_root=world["repo"],
            score_receipts=world["refs"], settlement_path=world["settlement"],
        )
    assert world["settlement"].is_file()
    assert world["attempt"].state() == "OPENED"

    monkeypatch.setattr(settlement.AttemptHandle, "finalize_with_receipt", real_finalize)
    result = settle_phase_delivery_attempt(
        world["parent"].manifest_path, repo_root=world["repo"],
        score_receipts=world["refs"], settlement_path=world["settlement"],
    )
    assert result.reused is True
    assert world["attempt"].state() == "FINALIZED"


def test_concurrent_settle_and_abort_leave_one_terminal_state(
    tmp_path, monkeypatch,
):
    world = _world(tmp_path, monkeypatch)
    barrier = threading.Barrier(2)
    outcomes = []

    def settle():
        barrier.wait()
        try:
            outcomes.append(settle_phase_delivery_attempt(
                world["parent"].manifest_path, repo_root=world["repo"],
                score_receipts=world["refs"], settlement_path=world["settlement"],
            ))
        except BundleError as error:
            outcomes.append(error)

    def abort():
        barrier.wait()
        outcomes.append(AttemptStore(world["data"] / "attempts").abort_if_opened(
            "parent", "attempt-parent", reason="concurrent abort"
        ))

    threads = [threading.Thread(target=settle), threading.Thread(target=abort)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)
    document = json.loads(world["attempt"].path.read_text())
    assert document["state"] in {"FINALIZED", "ABORTED"}
    if document["state"] == "FINALIZED":
        assert document["finalization"]["kind"] == SCHEMA
    else:
        assert "finalization" not in document


@pytest.mark.parametrize("state", ["ABORTED", "RESERVED"])
def test_nonopened_attempt_refuses_without_publishing(tmp_path, monkeypatch, state):
    world = _world(tmp_path, monkeypatch)
    document = json.loads(world["attempt"].path.read_text())
    document["state"] = state
    world["attempt"].path.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="not OPENED"):
        settle_phase_delivery_attempt(
            world["parent"].manifest_path, repo_root=world["repo"],
            score_receipts=world["refs"], settlement_path=world["settlement"],
        )
    assert not world["settlement"].exists()


def test_different_existing_settlement_and_changed_derivative_refuse(
    tmp_path, monkeypatch,
):
    world = _world(tmp_path, monkeypatch)
    world["settlement"].parent.mkdir(parents=True)
    world["settlement"].write_text("{}")
    with pytest.raises(BundleError, match="existing phase delivery settlement differs"):
        settle_phase_delivery_attempt(
            world["parent"].manifest_path, repo_root=world["repo"],
            score_receipts=world["refs"], settlement_path=world["settlement"],
        )
    world["settlement"].unlink()

    derivative = world["derivatives"]["first"]
    derivative.manifest_path.write_text(derivative.manifest_path.read_text() + " ")
    with pytest.raises(BundleError, match="manifest hash mismatch"):
        settle_phase_delivery_attempt(
            world["parent"].manifest_path, repo_root=world["repo"],
            score_receipts=world["refs"], settlement_path=world["settlement"],
        )
    assert world["attempt"].state() == "OPENED"


def test_settlement_never_invokes_a_scorer(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core import scorers

    world = _world(tmp_path, monkeypatch)
    monkeypatch.setattr(
        scorers, "score_bundle",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("settlement must not score")
        ),
    )
    settle_phase_delivery_attempt(
        world["parent"].manifest_path, repo_root=world["repo"],
        score_receipts=world["refs"], settlement_path=world["settlement"],
    )


def test_terminal_verifier_checks_attempt_receipt_hash_binding(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    settle_phase_delivery_attempt(
        world["parent"].manifest_path, repo_root=world["repo"],
        score_receipts=world["refs"], settlement_path=world["settlement"],
    )
    document = json.loads(world["settlement"].read_text())
    world["settlement"].write_text(json.dumps(document, indent=4))
    with pytest.raises(BundleError, match="does not bind"):
        verify_phase_delivery_settlement(
            world["settlement"], repo_root=world["repo"]
        )


def test_markerless_obs_parent_settles_from_recorded_declarations_without_rescoring(
    synthetic_world, tmp_path, repair_repo, monkeypatch,
):
    from test_delivery_bundle import generation as generation_fixture
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.core.bundle.delivery import build_delivery_bundle
    from speech_aware_evidence_acquisition.core.bundle import settlement
    from speech_aware_evidence_acquisition.core import scorers

    # Exercise the real generation/replay verifier and the actual recorded Git
    # declarations; only the score numbers are synthetic fixture data.
    generate = generation_fixture.__wrapped__(
        synthetic_world, tmp_path, repair_repo, monkeypatch
    )
    parent_path, kwargs = generate()
    parent = verify_bundle(parent_path)
    assert "required_phase_deliveries" not in parent.manifest
    refs = []
    source_bytes = {parent_path: parent_path.read_bytes()}
    for cell in ("constrained", "free"):
        path = build_delivery_bundle(
            **kwargs, derivative_cell_id=cell, output_dir=tmp_path / cell
        )
        bundle = verify_bundle(path)
        source_bytes[path] = path.read_bytes()
        source_bytes[bundle.outputs_path] = bundle.outputs_path.read_bytes()
        score_dir = synthetic_world.data_root / "scores" / cell
        score_dir.mkdir(parents=True)
        result = score_dir / "score.json"
        result.write_text(json.dumps({
            "manifest": str(path), "verified": True,
            "scores": {
                name: {
                    "aggregate": {"fixture_score": 1},
                    "per_sample": [] if name == "cost" else [
                        {"sample_id": sid} for sid in sorted(bundle.split_ids)
                    ],
                }
                for name in bundle.manifest["scorers"]
            },
        }))
        refs.append(write_complete_score_receipt(
            score_dir / "complete-score-receipt.json", job_id=cell,
            result_path=result, source=capture_score_source(bundle),
            verified_bundle=bundle,
        ))
    monkeypatch.setattr(
        scorers, "score_bundle",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("settlement cannot invoke a scorer")
        ),
    )
    target = synthetic_world.data_root / "settlements/obs-parent.json"
    with pytest.raises(BundleError, match="cover"):
        settlement.settle_delivery_attempt(
            parent_path, repo_root=kwargs["repo_root"],
            score_receipts=refs[:1], settlement_path=target,
        )
    assert not target.exists()
    settled = settlement.settle_delivery_attempt(
        parent_path, repo_root=kwargs["repo_root"],
        score_receipts=refs, settlement_path=target,
    )
    assert settled.attempt_state == "FINALIZED"
    receipt = settlement.verify_delivery_settlement(
        target, repo_root=kwargs["repo_root"]
    )
    assert receipt["schema"] == "saea-delivery-settlement-v1"
    assert [x["cell_id"] for x in receipt["required_deliveries"]] == ["constrained", "free"]
    assert "required_phase_deliveries" not in receipt
    assert receipt["parent"]["cost_attribution"] == "parent generation is charged once"
    retry = settlement.settle_delivery_attempt(
        parent_path, repo_root=kwargs["repo_root"],
        score_receipts=refs, settlement_path=target,
    )
    assert retry.reused and retry.receipt_sha256 == settled.receipt_sha256
    assert all(path.read_bytes() == raw for path, raw in source_bytes.items())


def test_legacy_declarations_use_recorded_git_not_later_worktree_or_foreign_parent(
    synthetic_world, tmp_path, repair_repo, monkeypatch,
):
    from dataclasses import replace
    from test_delivery_bundle import generation as generation_fixture
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle, settlement

    generate = generation_fixture.__wrapped__(
        synthetic_world, tmp_path, repair_repo, monkeypatch
    )
    parent_path, kwargs = generate()
    parent = verify_bundle(parent_path)
    repo = kwargs["repo_root"]
    expected = settlement._required_declarations(parent, repo)
    assert [row["cell_id"] for row in expected] == ["constrained", "free"]
    experiment = kwargs["experiment_path"]
    document = json.loads(experiment.read_text())
    document["delivery_derivatives"].pop()
    experiment.write_text(json.dumps(document))
    # Later working-tree edits cannot shrink the required evidence.
    assert settlement._required_declarations(parent, repo) == expected
    changed = dict(parent.manifest)
    changed["config"] = {
        **changed["config"],
        "fragments": {**changed["config"]["fragments"], "baseline": "foreign"},
    }
    with pytest.raises(BundleError, match="no legacy deliveries"):
        settlement._required_declarations(replace(parent, manifest=changed), repo)


def test_missing_phase_marker_cannot_be_downgraded_to_legacy_settlement(
    tmp_path, monkeypatch,
):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.bundle import settlement, git_commit

    world = _world(tmp_path, monkeypatch)
    parent = world["parent"]
    declarations = parent.manifest["required_phase_deliveries"]
    document = {
        "cells": [{
            "cell_id": "generation", "model_fragment": "m",
            "dataset_fragment": "d", "baseline_fragment": "b",
        }],
        "delivery_derivatives": declarations,
    }
    monkeypatch.setattr(
        git_commit, "_git",
        lambda *args: (0, json.dumps(document) if args[-2] == "show" else "", ""),
    )
    without_marker = {k: v for k, v in parent.manifest.items() if k != "required_phase_deliveries"}
    with pytest.raises(BundleError, match="original manifest marker"):
        settlement._required_declarations(
            replace(parent, manifest=without_marker), world["repo"]
        )
