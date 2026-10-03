"""A pending, wrong or duplicated official job blocks the whole family read."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import context_configuration_source as source
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def fixture(tmp_path):
    ids = [f"slurp:train:{i}:audio" for i in range(2)]
    members = []
    for i in range(2):
        run, attempt = f"run-{i}", f"attempt-{i}"
        member = {"run_id": run, "attempt_id": attempt, "config_hash": str(i) * 64, "protocol_hash": "b" * 64,
                  "label": "legacy-trajectory-" + ("primary" if i == 0 else "aa")}
        members.append(member)
        directory = tmp_path / "runs" / run / attempt
        directory.mkdir(parents=True)
        manifest_path = directory / (run + ".run-manifest.json")
        manifest = {"run_id": run, "status": "COMPLETED", "study_commit": "c" * 40,
                    "config": {"config_hash": member["config_hash"]},
                    "plan": {"protocol_hash": member["protocol_hash"], "split_role": "discovery"},
                    "attempt": {"attempt_id": attempt}, "split": {"count": 2, "ids": ids}}
        manifest_path.write_text(json.dumps(manifest))
        attempt_path = tmp_path / "attempts" / run / (attempt + ".json")
        attempt_path.parent.mkdir(parents=True)
        attempt_path.write_text(json.dumps({"state": "FINALIZED"}))
        job = {"job_id": attempt, "manifest": str(manifest_path)}
        (directory / "score-jobs.jsonl").write_text(json.dumps(job) + "\n")
        batch = directory / "score-batch/batch-summary.json"
        batch.parent.mkdir()
        batch.write_text(json.dumps({"job_count": 1, "succeeded": 1, "failed": 0,
                                     "include_per_sample": True, "jobs": [{**job, "status": "succeeded",
                                     "returncode": 0, "operation": "finalize"}]}))
    return {"members": members, "rows_per_member": 2}, ids


def mutate_json(path, **changes):
    value = json.loads(path.read_text())
    value.update(changes)
    path.write_text(json.dumps(value))


@pytest.mark.parametrize("fault", ["opened", "missing_manifest", "wrong_config", "wrong_protocol", "test",
                                   "wrong_rows", "wrong_commit", "duplicate_job", "failed_job", "missing_job",
                                   "not_finalized", "missing_per_sample", "path_escape", "duplicate_member"])
def test_whole_family_operational_gate_precedes_all_seal_and_quality_reads(tmp_path, monkeypatch, fault):
    registration, ids = fixture(tmp_path)
    directory = tmp_path / "runs/run-1/attempt-1"
    manifest_path = directory / "run-1.run-manifest.json"
    batch = directory / "score-batch/batch-summary.json"
    if fault == "opened":
        mutate_json(tmp_path / "attempts/run-1/attempt-1.json", state="OPENED")
    elif fault == "missing_manifest":
        manifest_path.unlink()
    elif fault == "wrong_config":
        mutate_json(manifest_path, config={"config_hash": "z" * 64})
    elif fault == "wrong_protocol":
        mutate_json(manifest_path, plan={"protocol_hash": "z" * 64, "split_role": "discovery"})
    elif fault == "test":
        mutate_json(manifest_path, plan={"protocol_hash": "b" * 64, "split_role": "test"})
    elif fault == "wrong_rows":
        mutate_json(manifest_path, split={"count": 2, "ids": [ids[0], ids[0]]})
    elif fault == "wrong_commit":
        mutate_json(manifest_path, study_commit="d" * 40)
    elif fault == "duplicate_job":
        p = directory / "score-jobs.jsonl"
        p.write_text(p.read_text() * 2)
    elif fault == "failed_job":
        mutate_json(batch, failed=1)
    elif fault == "missing_job":
        batch.unlink()
    elif fault == "not_finalized":
        value = json.loads(batch.read_text())
        value["jobs"][0]["operation"] = "score"
        batch.write_text(json.dumps(value))
    elif fault == "missing_per_sample":
        mutate_json(batch, include_per_sample=False)
    elif fault == "path_escape":
        registration["members"][1]["run_id"] = "../escape"
    elif fault == "duplicate_member":
        registration["members"][1] = registration["members"][0]
    monkeypatch.setattr(source, "verify_bundle", lambda *_: pytest.fail("seal/result opened before whole family gate"))
    with pytest.raises((PolicyError, FileNotFoundError)):
        source.preflight_members(registration, data_root=tmp_path, sample_ids=ids, commit="c" * 40)


def test_all_complete_metadata_then_every_seal(tmp_path, monkeypatch):
    registration, ids = fixture(tmp_path)
    seen = []
    def verify(path):
        seen.append(Path(path).name)
        return SimpleNamespace(attempt_state="FINALIZED")
    monkeypatch.setattr(source, "verify_bundle", verify)
    result = source.preflight_members(registration, data_root=tmp_path, sample_ids=ids, commit="c" * 40)
    assert len(result) == len(seen) == 2
    assert [r["manifest"]["run_id"] for r in result] == ["run-0", "run-1"]


def test_bad_seal_stops_before_numeric_reader(tmp_path, monkeypatch):
    registration, ids = fixture(tmp_path)
    monkeypatch.setattr(source, "verify_bundle", lambda *_: SimpleNamespace(attempt_state="OPENED"))
    with pytest.raises(PolicyError, match="seal"):
        source.preflight_members(registration, data_root=tmp_path, sample_ids=ids, commit="c" * 40)


@pytest.mark.parametrize("fault", [None, "cohort", "changed_score", "audit_reject"])
def test_numeric_join_uses_existing_official_custody_and_original_timing(tmp_path, monkeypatch, fault):
    registration, ids = fixture(tmp_path)
    monkeypatch.setattr(source, "verify_bundle", lambda *_: SimpleNamespace(attempt_state="FINALIZED"))
    entries = source.preflight_members(registration, data_root=tmp_path, sample_ids=ids, commit="c" * 40)
    for entry in entries:
        path, run = entry["manifest_path"], entry["manifest"]["run_id"]
        for name in (run + ".phases.json", "flight-receipts.json"):
            (path.parent / name).write_text("{}")
        (path.parent / "scores.json").write_text(json.dumps({"slurp-slu-official-train": {
            "aggregate": {"official": {"slu_f1": 0.5}, "port_micro": {"intent_accuracy": 1}}}}))
    verified = SimpleNamespace(sample_ids=ids)
    calls = []
    def feedback(**kwargs):
        binding = kwargs["binding"]
        calls.append(binding)
        path = tmp_path / binding["manifest"]["relpath"]
        pin = source._pin(path.parent / "scores.json", tmp_path)
        if fault == "changed_score":
            (path.parent / "scores.json").write_text("{}")
        return {"terminal_feedback": [{"sample_id": sid, "tp": 1, "fp": 1, "fn": 1,
                                        "intent_exact": 1, "fallback_flags": [], "format_ok": True}
                                       for sid in (ids[:1] if fault == "cohort" else ids)],
                "resolved_auxiliary_sources": {"scores": pin}, "content_sha256": "f" * 64}
    monkeypatch.setattr(source, "verify_native_episode_source", lambda **_: verified)
    monkeypatch.setattr(source, "load_system_feedback", feedback)
    monkeypatch.setattr(source, "_row_cost_and_terminal", lambda _: {sid: {"model_calls": 4} for sid in ids})
    monkeypatch.setattr(source, "export_system_sample_timing", lambda s: {"original": s is verified})
    monkeypatch.setattr(source, "export_system_node_timing", lambda s: {"original": s is verified})
    audits = []
    def audit(*args, **kwargs):
        audits.append(kwargs["member"]["label"])
        if fault == "audit_reject":
            raise PolicyError("actual request audit refused")
        return {"contacts_verified": 4, "original_fit_receipts": 4}
    monkeypatch.setattr(source, "_audit_context_source", audit)
    if fault:
        with pytest.raises(PolicyError):
            source.read_numeric_members(entries, data_root=tmp_path, frozen_repo=tmp_path)
        if fault == "audit_reject":
            assert calls == []
    else:
        result = source.read_numeric_members(entries, data_root=tmp_path, frozen_repo=tmp_path)
        assert set(result) == {"run-0", "run-1"} and len(calls) == 2
        assert result["run-0"]["official"] == {"slu_f1": 0.5, "intent": 1}
        assert result["run-0"]["sample_timing"]["original"]
        assert result["run-0"]["context_execution"]["contacts_verified"] == 4
        assert result["run-0"]["experiment_stage_timing"]["generation_wall_seconds"] is None
        assert audits == ["legacy-trajectory-primary", "legacy-trajectory-aa"]
        assert result["run-0"]["rows"][ids[0]]["model_calls"] == 4
        assert all(set(c) == {"schema", "execution_profile", "feedback_role", "scorer_id",
                               "manifest", "phases", "flight_receipts", "score_jobs"} for c in calls)


def test_data_source_pin_rejects_escape(tmp_path):
    with pytest.raises(PolicyError, match="escaped"):
        source._pin(tmp_path.parent / "outside", tmp_path)


def test_stage_timing_preserves_nested_boundaries_and_missingness():
    flight = {"stages": {
        "preprocess": {"duration_seconds": 2, "packet_validation_seconds": 0.5},
        "serve": {"startup_seconds": 0},
        "run_phases": {"wall_seconds": 120, "client_initialization_seconds": 3},
        "score": {"duration_seconds": 60, "private_result": "never export"},
    }}
    result = source.describe_stage_timing(flight, {"elapsed_seconds": 55, "jobs": [
        {"elapsed_seconds": 54, "private_result": "never export"}]})
    assert result["generation_wall_seconds"] == 120
    assert result["score_stage_seconds"] == 60
    assert result["score_batch_seconds"] == 55
    assert result["official_finalize_worker_seconds"] == 54
    assert result["client_initialization_seconds"] == 3
    assert result["preprocess_seconds"] == 2
    assert result["packet_validation_seconds"] == 0.5
    assert result["service_startup_seconds"] == 0
    assert "not additive" in result["measurement_boundary"]
    assert "never export" not in json.dumps(result)
    empty = source.describe_stage_timing({}, {})
    assert all(value is None for key, value in empty.items() if key.endswith("_seconds"))
    assert "sample" in empty["measurement_boundary"]
    assert not any("per_sample" in key or "speedup" in key or "total" in key for key in result)


@pytest.mark.parametrize("bad", [-1, True, "12", float("nan"), float("inf")])
@pytest.mark.parametrize("field", ["generation", "scoring"])
def test_stage_timing_rejects_invalid_numeric_evidence(bad, field):
    flight = {"stages": {"run_phases": {"wall_seconds": bad}}} if field == "generation" else {}
    batch = {"jobs": [{"elapsed_seconds": bad}]} if field == "scoring" else {}
    with pytest.raises(PolicyError, match="stage timing"):
        source.describe_stage_timing(flight, batch)


def test_stage_timing_refuses_multiple_workers_instead_of_averaging():
    with pytest.raises(PolicyError, match="one"):
        source.describe_stage_timing({}, {"jobs": [{"elapsed_seconds": 2}, {"elapsed_seconds": 3}]})


@pytest.mark.parametrize("label", ["legacy-trajectory-aa", "before-speech-role-primary"])
def test_source_audit_keeps_shared_renderer_and_original_session_identity(tmp_path, monkeypatch, label):
    from test_context_execution_audit import world
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    placement = "legacy" if label.startswith("legacy") else "before-speech-v1"
    scheduler = "role" if "-role-" in label else "trajectory"
    actor, report, flight_pin, transport = world(tmp_path, placement, scheduler)
    report["content_sha256"] = content_hash(report)
    actor.bundle.manifest = {"session_receipt": {"path": str(tmp_path / "session.json"), "sha256": "f" * 64}}
    actor.composed.values["model_materialization_root"] = str(tmp_path)
    seen = []
    session = object()
    def resolve(path, sha):
        assert path == tmp_path / "session.json" and sha == "f" * 64
        seen.append("session")
        return b'{"original":true}'
    def session_from(doc):
        assert doc == {"original": True}
        return session
    def build(values, data, **kwargs):
        assert values is actor.composed.values and data == tmp_path
        assert kwargs == {"repo_root": tmp_path, "session": session,
                          "runtime_receipt": {"pinned": True}, "runtime_root": tmp_path}
        seen.append("shared-renderer")
        return transport
    def materialize(value, **kwargs):
        assert value is actor and kwargs["round_id"] == "context-matrix-n20-root-audit-v1"
        seen.append("complete-source")
        return report
    monkeypatch.setattr(source, "resolve_pinned_session_receipt", resolve)
    monkeypatch.setattr(source.SessionReceipt, "from_json", session_from)
    monkeypatch.setattr(source, "resolve_runtime_receipt_path", lambda *a: tmp_path / "runtime.json")
    monkeypatch.setattr(source, "load_runtime_receipt", lambda path: {"pinned": True})
    monkeypatch.setattr(source, "build_configured_transport", build)
    monkeypatch.setattr(source, "materialize_semantic_trajectories", materialize)
    result = source._audit_context_source(actor, member={"label": label}, flight_pin=flight_pin,
        data_root=tmp_path, frozen_repo=tmp_path)
    assert result["contacts_verified"] == 1
    assert seen == ["complete-source", "session", "shared-renderer"]
    assert result["wire_requests"]["artifact"]["relpath"].startswith("analysis/context-matrix-n20-wire/")
    monkeypatch.setattr(source, "build_configured_transport", lambda *a, **k: pytest.fail("cached audit must not need service"))
    monkeypatch.setattr(source, "resolve_pinned_session_receipt", lambda *a, **k: pytest.fail("cached audit must not need session"))
    replay = source._audit_context_source(actor, member={"label": label}, flight_pin=flight_pin,
        data_root=tmp_path, frozen_repo=tmp_path)
    assert replay == result


def test_unregistered_audit_label_fails_before_renderer(tmp_path):
    with pytest.raises(PolicyError, match="label"):
        source._audit_context_source(None, member={"label": "foreign"}, flight_pin={},
                                     data_root=tmp_path, frozen_repo=tmp_path)


@pytest.mark.parametrize("layout", ["legacy", "before-speech"])
@pytest.mark.parametrize("schedule", ["trajectory", "panel"])
def test_registered_schedule_identity_has_exact_owner_and_node_policy(layout, schedule):
    label = f"{layout}-{schedule}-pair2-aa"
    member = {"label": label, "layout": layout, "schedule": schedule,
              "run_id": f"SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-{label.upper()}-V1",
              "job_keys": [[f"sample-{i}", None] for i in range(20)]}
    placement, scheduler, namespace, identity = source.context_member_identity(member)
    assert placement == ("legacy" if layout == "legacy" else "before-speech-v1")
    assert scheduler == schedule and namespace == "node-panel-schedule-n20"
    if schedule == "panel":
        assert identity["group_index"] == (3 if layout == "legacy" else 7)
        assert identity["max_jobs"] == 160 and identity["group_size"] == 20
        assert identity["job_keys"] == member["job_keys"]
    else:
        assert identity is None


@pytest.mark.parametrize("field", ["label", "run_id", "layout", "schedule", "job_keys"])
def test_schedule_identity_refuses_foreign_or_misbound_owner(field):
    member = {"label": "legacy-panel-pair1-primary", "layout": "legacy", "schedule": "panel",
              "run_id": "SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-LEGACY-PANEL-PAIR1-PRIMARY-V1",
              "job_keys": [[f"sample-{i}", None] for i in range(20)]}
    member[field] = [] if field == "job_keys" else "foreign"
    with pytest.raises(PolicyError):
        source.context_member_identity(member)
