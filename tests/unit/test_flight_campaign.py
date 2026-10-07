"""Fake-transport campaign integration: configuration to shared runtime and scoring."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import (
    CampaignError, CampaignCell, declared_readiness, run_campaign,
)
from speech_aware_evidence_acquisition.core.flight.receipts import (
    FLIGHT_STAGES, FlightReceipts, read_flight_receipts,
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
    assert report["flight_receipts"] == {}
    assert starter.calls == 0 and attached == []
    assert not (data / "locks/flight.lock").exists()
    assert not (data / "runs" / _SERVING_RUN_ID / "attempt-serving").exists()


def test_root_campaign_runs_existing_harness_and_complete_score_under_lease(tmp_path):
    repo, runtime_root, data = _serving_world(tmp_path)
    session_dir = _write_serving_session(repo, runtime_root, data)
    scored = []
    runtime, starter, attached = _serving_runtime(tmp_path, repo)
    original_score = runtime.score
    def score(**kwargs):
        assert not (data / "locks/flight.lock").exists()
        sealed = read_flight_receipts(
            data / "runs" / _SERVING_RUN_ID / "attempt-serving" / "flight-receipts.json"
        )
        assert "seal" in sealed["stages"] and "score" not in sealed["stages"]
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
    receipt_ref = report["flight_receipts"][_SERVING_RUN_ID]
    receipt_path = Path(receipt_ref["path"])
    assert receipt_path == (
        data / "runs" / _SERVING_RUN_ID / "attempt-serving" / "flight-receipts.json"
    ).resolve()
    assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == receipt_ref["sha256"]
    score_receipt = read_flight_receipts(receipt_path)["stages"]["score"]
    assert score_receipt["include_per_sample"] is True
    assert score_receipt["result"]


def test_campaign_preserves_genuine_partial_receipts_on_generation_failure(tmp_path):
    repo, runtime_root, data = _serving_world(tmp_path)
    _write_serving_session(repo, runtime_root, data)
    runtime, _, _ = _serving_runtime(tmp_path, repo)
    original_run_phases = runtime.run_phases

    def fail_after_run_phases():
        original_run_phases()
        raise RuntimeError("generation failed after the phase receipt")

    runtime.run_phases = fail_after_run_phases
    with pytest.raises(RuntimeError, match="generation failed"):
        run_campaign(
            [runtime], cells=[cell()], repo_root=repo, data_root=data,
            owner="coordinator", expected_session_id="serving-test",
        )

    persisted = read_flight_receipts(
        data / "runs" / _SERVING_RUN_ID / "attempt-serving" / "flight-receipts.json"
    )
    assert tuple(stage for stage in FLIGHT_STAGES if stage in persisted["stages"]) == (
        "preflight", "preprocess", "serve", "run_phases",
    )


def test_campaign_receipt_failure_does_not_hide_generation_failure(
    tmp_path, monkeypatch,
):
    from speech_aware_evidence_acquisition.core.flight import campaign

    repo, runtime_root, data = _serving_world(tmp_path)
    _write_serving_session(repo, runtime_root, data)
    runtime, _, _ = _serving_runtime(tmp_path, repo)
    original_run_phases = runtime.run_phases

    def fail_after_run_phases():
        original_run_phases()
        raise RuntimeError("primary generation failure")

    def fail_receipt(*args, **kwargs):
        raise OSError("receipt storage unavailable")

    runtime.run_phases = fail_after_run_phases
    monkeypatch.setattr(campaign, "persist_flight_receipts", fail_receipt)
    with pytest.raises(RuntimeError, match="primary generation failure") as raised:
        run_campaign(
            [runtime], cells=[cell()], repo_root=repo, data_root=data,
            owner="coordinator", expected_session_id="serving-test",
        )

    assert any("receipt storage unavailable" in note for note in raised.value.__notes__)


def test_campaign_preserves_seal_without_inventing_failed_score_stage(
    tmp_path, monkeypatch,
):
    from speech_aware_evidence_acquisition.core.flight import campaign

    repo, runtime_root, data = _serving_world(tmp_path)
    _write_serving_session(repo, runtime_root, data)
    runtime, _, _ = _serving_runtime(tmp_path, repo)
    original_writer = campaign.persist_flight_receipts
    writes = 0

    def fail_score(**kwargs):
        raise RuntimeError("scoring failed before its receipt")

    def fail_later_receipt(*args, **kwargs):
        nonlocal writes
        writes += 1
        if writes > 1:
            raise OSError("receipt update unavailable")
        return original_writer(*args, **kwargs)

    runtime.score = fail_score
    monkeypatch.setattr(campaign, "persist_flight_receipts", fail_later_receipt)
    with pytest.raises(RuntimeError, match="scoring failed") as raised:
        run_campaign(
            [runtime], cells=[cell()], repo_root=repo, data_root=data,
            owner="coordinator", expected_session_id="serving-test",
        )

    persisted = read_flight_receipts(
        data / "runs" / _SERVING_RUN_ID / "attempt-serving" / "flight-receipts.json"
    )
    completed = tuple(stage for stage in FLIGHT_STAGES if stage in persisted["stages"])
    assert completed[-1] == "seal"
    assert "score" not in persisted["stages"]
    assert any("receipt update unavailable" in note for note in raised.value.__notes__)


def test_campaign_preserves_complete_score_when_shutdown_fails(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import campaign

    repo, runtime_root, data = _serving_world(tmp_path)
    _write_serving_session(repo, runtime_root, data)
    runtime, _, _ = _serving_runtime(tmp_path, repo)
    original_shutdown = campaign.FlightQueue.shutdown

    def fail_after_shutdown(queue):
        original_shutdown(queue)
        raise RuntimeError("shutdown failed after score completion")

    monkeypatch.setattr(campaign.FlightQueue, "shutdown", fail_after_shutdown)
    with pytest.raises(RuntimeError, match="shutdown failed"):
        run_campaign(
            [runtime], cells=[cell()], repo_root=repo, data_root=data,
            owner="coordinator", expected_session_id="serving-test",
        )

    persisted = read_flight_receipts(
        data / "runs" / _SERVING_RUN_ID / "attempt-serving" / "flight-receipts.json"
    )
    assert "score" in persisted["stages"]


def test_worker_cli_requires_root_capability_before_runtime_build(monkeypatch):
    from speech_aware_evidence_acquisition.core.flight.cli import main
    with pytest.raises(SystemExit):
        main(["worker", "--repo-root", "/fake", "--data-root", "/fake",
              "--runtime-root", "/fake", "--lock-path", "/fake", "--experiment", "e",
              "--cell", "c"])


@pytest.mark.parametrize(
    "state, expected_exit",
    [
        ("failed", 1),
        ("preflight-failed", 1),
        ("held", 0),
        ("preparation-pending", 0),
        ("scored", 0),
    ],
)
def test_campaign_cli_exit_reflects_generation_failure(tmp_path, monkeypatch, state, expected_exit):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(cli, "__file__", str(repo / "src/package/core/flight/cli.py"))
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *args: (cell(),))
    monkeypatch.setattr(
        cli, "build_flight_runtime",
        # E16: a campaign launch verifies every prepared artifact before it
        # opens anything, so even a stub runtime answers that question.
        lambda *args, **kwargs: SimpleNamespace(verify_prepared_artifacts=lambda: ()),
    )
    monkeypatch.setattr(
        cli, "run_campaign",
        lambda *args, **kwargs: {
            "schema": "saea-campaign-status-v1",
            "states": {_SERVING_RUN_ID: {"state": state, "reason": "test state"}},
            "pending": [], "completed": [],
        },
    )

    result = cli.main([
        "campaign", "--repo-root", str(repo), "--data-root", str(tmp_path),
        "--runtime-root", str(tmp_path), "--lock-path", str(tmp_path / "lock"),
        "--experiment", "e", "--owner", "root", "--expected-session-id", "serving-test",
    ])

    assert result == expected_exit


def test_campaign_cli_forwards_runtime_and_lock_paths_to_shared_factory(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo = tmp_path / "repo"
    repo.mkdir()
    data_root = tmp_path / "data"
    runtime_root = tmp_path / "resident-runtime"
    lock_path = tmp_path / "custody" / "flight.lock"
    factory_calls = []

    monkeypatch.setattr(cli, "__file__", str(repo / "src/package/core/flight/cli.py"))
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *args: (cell(),))

    def build(*args, **kwargs):
        factory_calls.append((args, kwargs))
        return SimpleNamespace(verify_prepared_artifacts=lambda: ())

    monkeypatch.setattr(cli, "build_flight_runtime", build)
    monkeypatch.setattr(
        cli, "run_campaign",
        lambda *args, **kwargs: {
            "schema": "saea-campaign-status-v1",
            "states": {_SERVING_RUN_ID: {"state": "held", "reason": "test state"}},
            "pending": [], "completed": [],
        },
    )

    result = cli.main([
        "campaign", "--repo-root", str(repo), "--data-root", str(data_root),
        "--runtime-root", str(runtime_root), "--lock-path", str(lock_path),
        "--experiment", "e", "--owner", "root",
        "--expected-session-id", "serving-test",
    ])

    assert result == 0
    assert factory_calls == [((repo.resolve(), data_root.resolve()), {
        "model": "m", "dataset": "d", "baseline": "b", "experiment": "e",
        "run_id": _SERVING_RUN_ID, "attempt_id": "attempt-serving",
        "runtime_root": runtime_root, "lock_path": lock_path,
        "execution_policy": None,
    })]


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
    payload = json.dumps({
        "schema": "saea-campaign-decision-v1",
        "decision_id": "OWNER-DECISION-001",
        "status": "decided",
        "eligible_run_ids": [_SERVING_RUN_ID],
    }, sort_keys=True).encode()
    (tmp_path / "receipt").write_bytes(payload)
    doc = dict(cell().document)
    req = {
        "kind": "decision", "relpath": "receipt",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "expected_decision_id": "OWNER-DECISION-001",
    }
    doc["readiness"] = {"state": "ready", "requirements": [req]}
    assert declared_readiness(CampaignCell.from_document(doc), tmp_path).state == "ready"
    payload = json.dumps({**json.loads(payload), "status": "pending"}, sort_keys=True).encode()
    (tmp_path / "receipt").write_bytes(payload)
    req["sha256"] = hashlib.sha256(payload).hexdigest()
    state = declared_readiness(CampaignCell.from_document(doc), tmp_path)
    assert state.state == "held" and "not 'decided'" in state.reason
    req["sha256"] = "0" * 64
    assert declared_readiness(CampaignCell.from_document(doc), tmp_path).state == "held"
    req["relpath"] = "../receipt"
    with pytest.raises(CampaignError, match="confined"):
        declared_readiness(CampaignCell.from_document(doc), tmp_path)


@pytest.mark.parametrize(
    "mutate, reason",
    [
        (lambda receipt: receipt.update(status="rejected"), "not 'decided'"),
        (lambda receipt: receipt.update(decision_id="OWNER-DECISION-002"), "expected decision"),
        (lambda receipt: receipt.update(eligible_run_ids=["other-run"]), "not eligible"),
        (lambda receipt: receipt.update(eligible_run_ids=[_SERVING_RUN_ID, _SERVING_RUN_ID]), "unique nonempty"),
    ],
)
def test_decision_receipt_contract_holds_wrong_or_unknown_decisions(tmp_path, mutate, reason):
    import hashlib
    receipt = {
        "schema": "saea-campaign-decision-v1",
        "decision_id": "OWNER-DECISION-001",
        "status": "decided",
        "eligible_run_ids": [_SERVING_RUN_ID],
    }
    mutate(receipt)
    payload = json.dumps(receipt, sort_keys=True).encode()
    (tmp_path / "receipt").write_bytes(payload)
    doc = dict(cell().document)
    doc["readiness"] = {"state": "ready", "requirements": [{
        "kind": "decision", "relpath": "receipt",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "expected_decision_id": "OWNER-DECISION-001",
    }]}
    state = declared_readiness(CampaignCell.from_document(doc), tmp_path)
    assert state.state == "held" and reason in state.reason


def test_held_decision_does_not_look_up_resident_or_lease(tmp_path):
    import hashlib
    repo, _, data = _serving_world(tmp_path)
    runtime, starter, attached = _serving_runtime(tmp_path, repo)
    payload = json.dumps({
        "schema": "saea-campaign-decision-v1",
        "decision_id": "OWNER-DECISION-001",
        "status": "decided",
        "eligible_run_ids": ["different-run"],
    }, sort_keys=True).encode()
    (data / "decision.json").write_bytes(payload)
    document = dict(cell().document)
    document["readiness"] = {"state": "ready", "requirements": [{
        "kind": "decision", "relpath": "decision.json",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "expected_decision_id": "OWNER-DECISION-001",
    }]}
    report = run_campaign(
        [runtime], cells=[CampaignCell.from_document(document)], repo_root=repo,
        data_root=data, owner="coordinator", expected_session_id="serving-test",
        resident_finder=lambda _: pytest.fail("held decision must not look up resident"),
    )
    assert report["states"][_SERVING_RUN_ID]["state"] == "held"
    assert starter.calls == 0 and attached == []
    assert not (data / "locks/flight.lock").exists()


def test_absent_decision_receipt_stays_held(tmp_path):
    import hashlib
    payload = json.dumps({
        "schema": "saea-campaign-decision-v1",
        "decision_id": "OWNER-DECISION-001",
        "status": "decided",
        "eligible_run_ids": [_SERVING_RUN_ID],
    }, sort_keys=True).encode()
    document = dict(cell().document)
    document["readiness"] = {"state": "ready", "requirements": [{
        "kind": "decision", "relpath": "missing-decision.json",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "expected_decision_id": "OWNER-DECISION-001",
    }]}
    state = declared_readiness(CampaignCell.from_document(document), tmp_path)
    assert state.state == "held" and "missing-decision.json" in state.reason


def test_window_inventory_cli_requires_explicit_output(tmp_path):
    from speech_aware_evidence_acquisition.core.flight import cli

    with pytest.raises(SystemExit, match="2"):
        cli.main([
            "prepare-window-inventory",
            "--repo-root", str(tmp_path),
            "--data-root", str(tmp_path),
            "--runtime-root", str(tmp_path),
            "--lock-path", str(tmp_path / "lock"),
            "--experiment", "e",
            "--cell", "C",
        ])


@pytest.mark.parametrize("mode", [
    "check", "wire-check", "prepare-supply", "prepare-window-inventory",
    "prompt-fit", "prepare-window-features", "prepare-speech-observation-sources", "worker", "campaign",
])
def test_cli_routes_shared_modes_and_leaves_worker_scoring_to_root(tmp_path, monkeypatch, mode):
    import sys
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight import cli
    from speech_aware_evidence_acquisition.core.flight.lease import GenerationLease
    repo = tmp_path / "repo"
    calls = []
    class Runtime:
        def __init__(self):
            self.run_id = _SERVING_RUN_ID
            self.attempt_id = "attempt-serving"
            self.receipts = FlightReceipts(self.run_id, self.attempt_id)

        def _record(self, stage):
            self.receipts.record(stage, {"test": stage})

        def preflight(self, *, enforce_prepared_artifacts=True):
            calls.append("preflight")
            self._record("preflight")
            return {}
        def verify_prepared_artifacts(self):
            return ()
        def wire_check(self, **kwargs):
            assert kwargs == {"seal_and_score": False}
            calls.append("wire")
            return {}
        def prepare_phase_supply(self, path):
            calls.append("prepare")
            return {}
        def prepare_window_inventory(self, path):
            calls.append("window-inventory")
            return {}
        def prepare_speech_observation_sources(self, path):
            calls.append("speech-observation-sources")
            return {}
        def preprocess(self):
            calls.append("preprocess")
            self._record("preprocess")
        def serve(self):
            calls.append("serve")
            self._record("serve")
        def run_phases(self):
            calls.append("generate")
            self._record("run_phases")
        def seal(self):
            calls.append("seal")
            self._record("seal")
            return {"manifest_path": "complete-manifest.json"}
        def score(self, **kwargs):
            pytest.fail("standalone worker must not hold generation custody during scoring")
        def stop_serving(self):
            pytest.fail("standalone worker must not stop the root-owned service")
    monkeypatch.setattr(cli, "__file__", str(repo / "src/package/core/flight/cli.py"))
    selected_document = dict(cell().document)
    if mode == "check":
        selected_document["readiness"] = {"state": "held", "reason": "fit not yet registered"}
    if mode in {"prepare-window-inventory", "prepare-window-features", "prepare-speech-observation-sources"}:
        selected_document["allowed_execution_stages"] = [mode]
    monkeypatch.setattr(cli, "load_campaign_cells",
                        lambda *a: (CampaignCell.from_document(selected_document),))
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *a, **kw: Runtime())
    monkeypatch.setattr(cli, "run_campaign", lambda *a, **kw: {"campaign": True})
    monkeypatch.setitem(sys.modules, "speech_aware_evidence_acquisition.core.preparation_fit",
                        SimpleNamespace(fit_phase_runtime=lambda *a, **kw: {"fit": True}))
    def encode(*args, **kwargs):
        assert kwargs["policy"].expected_session_id == "serving-test"
        calls.append("window-features")
        return {"encoding": True}
    monkeypatch.setitem(sys.modules, "speech_aware_evidence_acquisition.core.preparation_window_encoding",
                        SimpleNamespace(prepare_window_feature_encoding=encode))
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
    elif mode == "prepare-window-inventory":
        assert calls == ["window-inventory"]
    elif mode == "prepare-window-features":
        assert calls == ["window-features"]
    elif mode == "prepare-speech-observation-sources":
        assert calls == ["speech-observation-sources"]


def test_fit_cell_cannot_be_dispatched_as_generation():
    document = dict(cell().document)
    document["allowed_execution_stages"] = ["prompt-fit"]
    fit = CampaignCell.from_document(document)
    fit.assert_mode("prompt-fit")
    with pytest.raises(CampaignError, match="stage"):
        fit.assert_mode("worker")
    with pytest.raises(CampaignError, match="stage"):
        fit.assert_mode("campaign")


def test_window_inventory_is_an_explicit_model_free_stage():
    undeclared = cell()
    undeclared.assert_mode("check")
    with pytest.raises(CampaignError, match="explicitly permit"):
        undeclared.assert_mode("prepare-window-inventory")

    document = dict(cell().document)
    document["allowed_execution_stages"] = ["prepare-window-inventory"]
    inventory = CampaignCell.from_document(document)
    inventory.assert_mode("prepare-window-inventory")
    with pytest.raises(CampaignError, match="stage"):
        inventory.assert_mode("wire-check")
    with pytest.raises(CampaignError, match="stage"):
        inventory.assert_mode("worker")


@pytest.mark.parametrize("stages", [[], ["unknown"], ["worker", "worker"], "worker"])
def test_stage_declaration_rejects_invalid_values(stages):
    document = dict(cell().document)
    document["allowed_execution_stages"] = stages
    with pytest.raises(CampaignError, match="stage"):
        CampaignCell.from_document(document)


def test_campaign_holds_fit_cell_before_service_or_lease(tmp_path):
    repo, _, data = _serving_world(tmp_path)
    runtime, starter, attached = _serving_runtime(tmp_path, repo)
    document = dict(cell().document)
    document["allowed_execution_stages"] = ["prompt-fit"]
    report = run_campaign(
        [runtime], cells=[CampaignCell.from_document(document)],
        repo_root=repo, data_root=data, owner="root", expected_session_id="session",
        resident_finder=lambda _: pytest.fail("fit cell must not look up a generation service"),
    )
    assert "stage" in report["states"][_SERVING_RUN_ID]["reason"]
    assert starter.calls == 0 and attached == []


def test_window_feature_encoding_requires_explicit_stage_and_root_custody(tmp_path):
    from speech_aware_evidence_acquisition.core.flight import cli
    with pytest.raises(CampaignError, match="explicitly permit"):
        cell().assert_mode("prepare-window-features")
    document = dict(cell().document)
    document["allowed_execution_stages"] = ["prepare-window-features"]
    encoding = CampaignCell.from_document(document)
    encoding.assert_mode("prepare-window-features")
    with pytest.raises(CampaignError, match="stage"):
        encoding.assert_mode("worker")
    with pytest.raises(SystemExit, match="2"):
        cli.main([
            "prepare-window-features", "--repo-root", str(tmp_path),
            "--data-root", str(tmp_path), "--runtime-root", str(tmp_path),
            "--lock-path", str(tmp_path / "lock"), "--experiment", "e",
            "--cell", "C", "--output", str(tmp_path / "receipt"),
        ])


def test_speech_source_export_requires_explicit_stage():
    undeclared = cell()
    with pytest.raises(CampaignError, match="explicitly permit"):
        undeclared.assert_mode("prepare-speech-observation-sources")


# ---------------------------------------------------------------------------
# E10 (owner decision 22, 2026-09-18): a recovery cell declares the aborted
# attempt it resumes in its COMMITTED experiment fragment, pinned by that
# attempt's trace sha256. There is no command-line flag: which rows a run
# keeps is registered, not typed at launch.
# ---------------------------------------------------------------------------


def test_a_recovery_cell_carries_its_resume_declaration():
    document = dict(cell().document)
    document["attempt_id"] = "attempt-serving-recovery"
    document["resume_from"] = {
        "attempt_id": "attempt-serving", "trace_sha256": "b" * 64,
    }
    recovery = CampaignCell.from_document(document)
    assert recovery.resume_from == {
        "attempt_id": "attempt-serving", "trace_sha256": "b" * 64,
    }
    assert cell().resume_from is None


def test_a_malformed_resume_declaration_refuses_at_cell_load():
    for resume in (
        {"attempt_id": "attempt-serving"},
        {"attempt_id": "attempt-serving", "trace_sha256": "not-a-hash"},
        {"attempt_id": "", "trace_sha256": "b" * 64},
    ):
        document = dict(cell().document)
        document["attempt_id"] = "attempt-serving-recovery"
        document["resume_from"] = resume
        with pytest.raises(CampaignError, match="resume_from"):
            CampaignCell.from_document(document)


def test_a_cell_may_not_declare_itself_as_its_own_predecessor():
    document = dict(cell().document)
    document["resume_from"] = {
        "attempt_id": document["attempt_id"], "trace_sha256": "b" * 64,
    }
    with pytest.raises(CampaignError, match="ABORTED attempt"):
        CampaignCell.from_document(document)
