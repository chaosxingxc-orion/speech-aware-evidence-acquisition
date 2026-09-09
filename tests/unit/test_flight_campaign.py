"""Fake-transport campaign integration: configuration to shared runtime and scoring."""
import json

import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import (
    CampaignError, CampaignCell, declared_readiness, run_campaign,
)
from test_flight_runtime import (
    _serving_world, _serving_runtime, _write_serving_session, _SERVING_RUN_ID,
)


def cell():
    return CampaignCell.from_document({
        "cell_id": "C", "model_fragment": "m", "dataset_fragment": "d",
        "baseline_fragment": "b", "run_id": _SERVING_RUN_ID,
        "attempt_id": "attempt-serving", "readiness": {"state": "ready"},
    })


def test_config_requires_explicit_readiness_and_unique_identity():
    doc = {"cell_id": "c"}
    with pytest.raises(CampaignError, match="required"):
        CampaignCell.from_document(doc)
    doc = dict(cell().document)
    del doc["readiness"]
    with pytest.raises(CampaignError, match="readiness"):
        CampaignCell.from_document(doc)


def test_preparation_requirement_is_hash_pinned_and_visible(tmp_path):
    doc = dict(cell().document)
    doc["readiness"] = {
        "state": "ready", "requirements": [{
            "kind": "preparation", "relpath": "prepared/seed.json",
            "sha256": "a" * 64, "reason": "frozen seed artifact required",
        }],
    }
    state = declared_readiness(CampaignCell.from_document(doc), tmp_path)
    assert state.state == "preparation-pending"
    assert "seed" in state.reason


def test_campaign_without_resident_holds_without_opening_a_lease(tmp_path):
    repo, _, data = _serving_world(tmp_path)
    runtime, starter, attached = _serving_runtime(tmp_path, repo)
    report = run_campaign(
        [runtime], cells=[cell()], repo_root=repo, data_root=data,
        owner="coordinator", expected_session_id="serving-test",
    )
    assert report["states"][_SERVING_RUN_ID]["state"] == "held"
    assert starter.calls == 0 and attached == []
    assert not (data / "locks/flight.lock").exists()


def test_root_campaign_runs_existing_harness_and_complete_score_under_lease(tmp_path):
    repo, runtime_root, data = _serving_world(tmp_path)
    session_dir = _write_serving_session(repo, runtime_root, data)
    scored = []
    runtime, starter, attached = _serving_runtime(tmp_path, repo)
    original_score = runtime.score
    def score(**kwargs):
        assert not (data / "locks/flight.lock").exists()
        scored.append(kwargs)
        return original_score(**kwargs)
    runtime.score = score
    report = run_campaign(
        [runtime], cells=[cell()], repo_root=repo, data_root=data,
        owner="coordinator", expected_session_id="serving-test",
    )
    assert report["states"][_SERVING_RUN_ID]["state"] == "scored"
    assert scored == [{"include_per_sample": True}]
    assert starter.calls == 0
    assert attached == [session_dir / "session-receipt.json"]
    assert runtime.stop_serving() is None
    assert not (data / "locks/flight.lock").exists()


def test_worker_cli_requires_root_capability_before_runtime_build(monkeypatch):
    from speech_aware_evidence_acquisition.core.flight.cli import main
    with pytest.raises(SystemExit):
        main(["worker", "--repo-root", "/fake", "--data-root", "/fake",
              "--runtime-root", "/fake", "--lock-path", "/fake", "--experiment", "e",
              "--cell", "c"])


def test_config_loader_rejects_duplicate_or_empty_cells(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
    directory = tmp_path / "configs/experiment"
    directory.mkdir(parents=True)
    path = directory / "e.json"
    path.write_text(json.dumps({"cells": [cell().document, cell().document]}))
    with pytest.raises(CampaignError, match="repeats"):
        load_campaign_cells(tmp_path, "e")
    path.write_text(json.dumps({"cells": [cell().document]}))
    assert len(load_campaign_cells(tmp_path, "e")) == 1
    with pytest.raises(CampaignError, match="plain"):
        load_campaign_cells(tmp_path, "../e")


def test_readiness_requires_pinned_confined_receipts(tmp_path):
    import hashlib
    payload = b"approved preparation"
    (tmp_path / "receipt").write_bytes(payload)
    doc = dict(cell().document)
    req = {"kind": "decision", "relpath": "receipt", "sha256": hashlib.sha256(payload).hexdigest()}
    doc["readiness"] = {"state": "ready", "requirements": [req]}
    assert declared_readiness(CampaignCell.from_document(doc), tmp_path).state == "ready"
    req["sha256"] = "0" * 64
    assert declared_readiness(CampaignCell.from_document(doc), tmp_path).state == "held"
    req["relpath"] = "../receipt"
    with pytest.raises(CampaignError, match="confined"):
        declared_readiness(CampaignCell.from_document(doc), tmp_path)


@pytest.mark.parametrize("mode", ["check", "wire-check", "prepare-supply", "prompt-fit", "worker", "campaign"])
def test_cli_routes_shared_modes_and_leaves_worker_scoring_to_root(tmp_path, monkeypatch, mode):
    import sys
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight import cli
    from speech_aware_evidence_acquisition.core.flight.lease import GenerationLease
    repo = tmp_path / "repo"
    calls = []
    class Runtime:
        def preflight(self):
            calls.append("preflight")
            return {}
        def wire_check(self, **kwargs):
            assert kwargs == {"seal_and_score": False}
            calls.append("wire")
            return {}
        def prepare_phase_supply(self, path):
            calls.append("prepare")
            return {}
        def preprocess(self):
            calls.append("preprocess")
        def serve(self):
            calls.append("serve")
        def run_phases(self):
            calls.append("generate")
        def seal(self):
            calls.append("seal")
            return {"manifest_path": "complete-manifest.json"}
        def score(self, **kwargs):
            pytest.fail("standalone worker must not hold generation custody during scoring")
    monkeypatch.setattr(cli, "__file__", str(repo / "src/package/core/flight/cli.py"))
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *a: (cell(),))
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *a, **kw: Runtime())
    monkeypatch.setattr(cli, "run_campaign", lambda *a, **kw: {"campaign": True})
    monkeypatch.setitem(sys.modules, "speech_aware_evidence_acquisition.core.preparation_fit",
                        SimpleNamespace(fit_phase_runtime=lambda *a, **kw: {"fit": True}))
    args = [mode, "--repo-root", str(repo), "--data-root", str(tmp_path),
            "--runtime-root", str(tmp_path), "--lock-path", str(tmp_path / "lock"),
            "--experiment", "e", "--cell", "C", "--output", str(tmp_path / "receipt"),
            "--expected-session-id", "serving-test", "--contact-cap", "4", "--owner", "root"]
    with GenerationLease.acquire(
        tmp_path, owner="root", run_id=cell().run_id, attempt_id=cell().attempt_id,
        session_id="serving-test", study_head="a" * 40,
    ):
        args += ["--lease-token-file", str(tmp_path / "locks/flight.lock")]
        assert cli.main(args) == 0
    if mode == "worker":
        assert calls == ["preflight", "preprocess", "serve", "generate", "seal"]
