"""Model-free exact-window encoding provenance validation."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    digest,
    prepare_artifact,
)
from speech_aware_evidence_acquisition.core.preparation_feature_cache import (
    FEATURE_CACHE_AUDIT_KIND,
    FEATURE_CACHE_AUDIT_SCHEMA,
    FEATURE_CACHE_AUDIT_STATE,
)
from speech_aware_evidence_acquisition.core.preparation_feature_provenance import (
    ENCODING_RECORD_SCHEMA,
    PROVENANCE_SCHEMA,
    PROVENANCE_STATE,
    canonical_receipt_sha256,
    load_preprocess_stop_chain,
    prepare_window_feature_provenance,
    validate_window_feature_encoding_record,
)
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WINDOW_FEATURE_INVENTORY_SCHEMA,
)
from speech_aware_evidence_acquisition.core.session import (
    ModelFileRef,
    PROCESS_STATE_DEFUNCT,
    PROCESS_STATE_GONE,
    PROCESS_STATE_RUNNING,
    SESSION_RECEIPT_SCHEMA_V2,
    SessionReceipt,
    write_session_receipt,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _identity():
    return {
        "runtime_receipt_sha256": "a" * 64,
        "build_commit": "b" * 40,
        "decoder_gguf_sha256": "c" * 64,
        "mmproj_sha256": "d" * 64,
    }


def _world(tmp_path, *, audio=("1" * 64, "2" * 64)):
    runtime = {
        "role": "preprocess",
        "llama_cpp": {
            "binary_path": "bin/llama-server",
            "binary_sha256": "e" * 64,
            "build_commit": _identity()["build_commit"],
        },
        "gguf_files": [
            {"path": "models/decoder.gguf", "sha256": _identity()["decoder_gguf_sha256"]},
            {"path": "models/mmproj-audio.gguf", "sha256": _identity()["mmproj_sha256"]},
        ],
    }
    runtime_path = tmp_path / "runtime.json"
    runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
    identity = dict(_identity(), runtime_receipt_sha256=_sha(runtime_path.read_bytes()))

    session = SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA_V2,
        study=STUDY_SLUG,
        session_id="root-preprocess-session",
        binary_path="bin/llama-server",
        binary_sha256="e" * 64,
        argv=("llama-server", "-m", "models/decoder.gguf", "--mmproj", "models/mmproj-audio.gguf"),
        pid=987654,
        host="127.0.0.1",
        port=8081,
        model_files=(
            ModelFileRef("models/decoder.gguf", identity["decoder_gguf_sha256"]),
            ModelFileRef("models/mmproj-audio.gguf", identity["mmproj_sha256"]),
        ),
        started_at="2026-09-10T00:00:00+00:00",
        startup_stdout_sha256=_sha(b""),
        role="preprocess",
        server_env_keys=("LLAMA_MTMD_FEAT_CACHE_DIR",),
    ).validate()
    session_path = tmp_path / "session.json"
    write_session_receipt(session_path, session)
    stop = {
        "schema": "saea-session-stop-receipt-v1",
        "study": STUDY_SLUG,
        "session_id": session.session_id,
        "session_role": "preprocess",
        "session_receipt_sha256": canonical_receipt_sha256(session.as_json()),
        "runtime_receipt_sha256": canonical_receipt_sha256(runtime),
        "pid": session.pid,
        "termination_signal": "SIGTERM",
        "forced": False,
        "stopped_at": "2026-09-10T00:10:00+00:00",
        "final_process_state": "gone",
    }
    stop_path = tmp_path / "stop.json"
    stop_path.write_text(json.dumps(stop), encoding="utf-8")

    inputs = [
        {
            "audio_sha256": sha,
            "requests": [{"batch": "generation-arm-a", "request_key": f"sample#w{i + 1:04d}"}],
        }
        for i, sha in enumerate(audio)
    ]
    inventory = {
        "schema": WINDOW_FEATURE_INVENTORY_SCHEMA,
        "state": "inputs-verified-features-not-materialized",
        "encoder_identity": identity,
        "batches": [],
        "encoding_inputs": inputs,
    }
    audit_entries = [
        {
            "audio_sha256": sha,
            "cache_key": str(1000 + i),
            "requests": item["requests"],
            "chunks": [{"relative_filename": f"{1000 + i}_o0.feat"}],
        }
        for i, (sha, item) in enumerate(zip(audio, inputs, strict=True))
    ]
    audit = {
        "schema": FEATURE_CACHE_AUDIT_SCHEMA,
        "state": FEATURE_CACHE_AUDIT_STATE,
        "inventory": inventory,
        "inventory_sha256": digest(inventory),
        "encoder_identity": identity,
        "legacy_cache_dir": str(tmp_path / "cache"),
        "expected_n_embd": 4,
        "entries": audit_entries,
    }
    audit_path = tmp_path / "audit.json"
    prepare_artifact(
        audit_path,
        kind=FEATURE_CACHE_AUDIT_KIND,
        inputs={"synthetic": True},
        producer=lambda: audit,
    )
    encoding = {
        "schema": ENCODING_RECORD_SCHEMA,
        "study": STUDY_SLUG,
        "run_id": "SAEA-E21-ENCODE-FOUR",
        "attempt_id": "attempt-encode-four",
        "session_id": session.session_id,
        "runtime_receipt_file_sha256": _sha(runtime_path.read_bytes()),
        "runtime_receipt_document_sha256": canonical_receipt_sha256(runtime),
        "session_receipt_file_sha256": _sha(session_path.read_bytes()),
        "inventory_sha256": digest(inventory),
        "encoder_identity": identity,
        "trace_manifest_hash": "f" * 64,
        "cost": {"calls_used": len(audio), "audio_seconds_used": 2.0},
        "current_contact_count": len(audio),
        "entries": [
            {
                "audio_sha256": sha,
                "cache_key": str(1000 + i),
                "status": "encoded",
                "success": True,
                "current_contact_id": f"encode-{i}",
                "source_contact_id": None,
                "source_provenance_receipt_sha256": None,
            }
            for i, sha in enumerate(audio)
        ],
    }
    encoding_path = tmp_path / "encoding.json"
    encoding_path.write_text(json.dumps(encoding), encoding="utf-8")
    return {
        "runtime": runtime_path,
        "session": session_path,
        "stop": stop_path,
        "audit": audit_path,
        "encoding": encoding_path,
        "encoding_document": encoding,
        "identity": identity,
    }


def _drop_encoding_entry(record):
    record["entries"].pop()
    record["current_contact_count"] -= 1
    record["cost"]["calls_used"] -= 1


def _prepare(tmp_path, world, *, sources=()):
    return prepare_window_feature_provenance(
        tmp_path / "provenance.json",
        runtime_receipt_path=world["runtime"],
        session_receipt_path=world["session"],
        stop_receipt_path=world["stop"],
        encoding_record_path=world["encoding"],
        cache_audit_path=world["audit"],
        expected_run_id="SAEA-E21-ENCODE-FOUR",
        expected_attempt_id="attempt-encode-four",
        expected_session_id="root-preprocess-session",
        source_provenance_paths=sources,
    )


def test_builds_source_bound_complete_provenance_with_foreign_batch_names(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_feature_provenance as module

    world = _world(tmp_path)
    monkeypatch.setattr(module, "process_state", lambda pid: PROCESS_STATE_GONE)

    result = _prepare(tmp_path, world)
    document = json.loads((tmp_path / "provenance.json").read_text(encoding="utf-8"))
    output = document["output"]

    assert result["cache"] == "cold"
    assert output["schema"] == PROVENANCE_SCHEMA
    assert output["state"] == PROVENANCE_STATE
    assert output["run_id"] == "SAEA-E21-ENCODE-FOUR"
    assert output["unique_audio_count"] == 2
    assert output["inventory_sha256"] == world["encoding_document"]["inventory_sha256"]
    assert output["encoder_identity"] == world["identity"]
    assert {entry["cache_key"] for entry in output["entries"]} == {"1000", "1001"}
    assert output["current_contact_count"] == 2
    assert output["stop_receipt_file_sha256"] == _sha(world["stop"].read_bytes())


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (_drop_encoding_entry, "coverage"),
        (lambda record: record["entries"].append(deepcopy(record["entries"][0])), "duplicate"),
        (lambda record: record["entries"][0].update(audio_sha256="9" * 64), "coverage"),
        (lambda record: record["entries"][0].update(cache_key="9999"), "coverage"),
        (lambda record: record["entries"][0].update(success=False, status="failed"), "failed"),
        (lambda record: record.update(current_contact_count=1), "contact count"),
        (lambda record: record["cost"].update(calls_used=1), "calls_used"),
        (lambda record: record.update(runtime_receipt_file_sha256="9" * 64), "runtime receipt"),
        (lambda record: record.update(session_receipt_file_sha256="9" * 64), "session receipt"),
        (lambda record: record.update(inventory_sha256="9" * 64), "inventory"),
        (lambda record: record.update(trace_manifest_hash="invalid"), "SHA256"),
        (lambda record: record["encoder_identity"].pop("mmproj_sha256"), "encoder identity"),
        (lambda record: record["entries"][0].update(status="unknown"), "status"),
        (
            lambda record: record["entries"][0].update(source_contact_id="invented"),
            "source receipt",
        ),
        (
            lambda record: record["entries"][1].update(
                current_contact_id=record["entries"][0]["current_contact_id"]
            ),
            "duplicate current",
        ),
    ],
)
def test_refuses_incomplete_duplicate_or_wrong_encoding_evidence(
    tmp_path, monkeypatch, mutation, message
):
    import speech_aware_evidence_acquisition.core.preparation_feature_provenance as module

    world = _world(tmp_path)
    record = world["encoding_document"]
    mutation(record)
    world["encoding"].write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(module, "process_state", lambda pid: PROCESS_STATE_GONE)

    with pytest.raises(PreparationError, match=message):
        _prepare(tmp_path, world)


def test_partial_failure_record_remains_a_valid_diagnostic_but_not_final_proof(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_feature_provenance as module

    world = _world(tmp_path)
    record = world["encoding_document"]
    record["entries"][0].update(status="failed", success=False)
    record["current_contact_count"] = 1
    record["cost"]["calls_used"] = 1
    validated = validate_window_feature_encoding_record(
        record,
        expected_run_id="SAEA-E21-ENCODE-FOUR",
        expected_attempt_id="attempt-encode-four",
        expected_session_id="root-preprocess-session",
    )
    assert validated["entries"][0]["status"] == "failed"

    world["encoding"].write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(module, "process_state", lambda pid: PROCESS_STATE_GONE)
    with pytest.raises(PreparationError, match="failed"):
        _prepare(tmp_path, world)


@pytest.mark.parametrize(
    ("target", "mutation", "message"),
    [
        ("encoding", lambda doc: doc["encoder_identity"].update(mmproj_sha256="9" * 64), "encoder identity"),
        ("encoding", lambda doc: doc.update(session_id="foreign-session"), "session_id"),
        ("runtime", lambda doc: doc.update(role="inference"), "preprocess"),
        ("stop", lambda doc: doc.update(runtime_receipt_sha256="9" * 64), "does not match"),
        ("audit", lambda doc: doc["output"]["encoder_identity"].update(mmproj_sha256="9" * 64), "output hash mismatch"),
    ],
)
def test_refuses_wrong_runtime_encoder_session_stop_or_audit_identity(
    tmp_path, monkeypatch, target, mutation, message
):
    import speech_aware_evidence_acquisition.core.preparation_feature_provenance as module

    world = _world(tmp_path)
    selected = world[target]
    document = json.loads(selected.read_text(encoding="utf-8"))
    mutation(document)
    selected.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(module, "process_state", lambda pid: PROCESS_STATE_GONE)

    with pytest.raises(PreparationError, match=message):
        _prepare(tmp_path, world)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda output: output.update(state="declared-only"), "schema or state"),
        (
            lambda output: output["entries"].append(deepcopy(output["entries"][0])),
            "duplicate",
        ),
        (
            lambda output: output["entries"][0].update(audio_sha256="9" * 64),
            "inventory unique audio",
        ),
        (
            lambda output: output["entries"][0].update(cache_key=1000),
            "decimal FNV",
        ),
    ],
)
def test_refuses_self_consistent_but_invalid_cache_audit(
    tmp_path, monkeypatch, mutation, message
):
    import speech_aware_evidence_acquisition.core.preparation_feature_provenance as module

    world = _world(tmp_path)
    wrapper = json.loads(world["audit"].read_text(encoding="utf-8"))
    mutation(wrapper["output"])
    wrapper["output_sha256"] = digest(wrapper["output"])
    world["audit"].write_text(json.dumps(wrapper), encoding="utf-8")
    monkeypatch.setattr(module, "process_state", lambda pid: PROCESS_STATE_GONE)

    with pytest.raises(PreparationError, match=message):
        _prepare(tmp_path, world)


@pytest.mark.parametrize("target", ["runtime", "session", "stop", "encoding", "audit"])
def test_refuses_missing_bound_receipt(tmp_path, monkeypatch, target):
    import speech_aware_evidence_acquisition.core.preparation_feature_provenance as module

    world = _world(tmp_path)
    world[target].unlink()
    monkeypatch.setattr(module, "process_state", lambda pid: PROCESS_STATE_GONE)

    with pytest.raises(PreparationError, match="cannot (stat|read)"):
        _prepare(tmp_path, world)


@pytest.mark.parametrize(
    ("stop_mutation", "state", "message"),
    [
        (lambda stop: stop.update(forced=True), PROCESS_STATE_GONE, "forced"),
        (lambda stop: stop.update(termination_signal="UNKNOWN"), PROCESS_STATE_GONE, "normal"),
        (lambda stop: None, PROCESS_STATE_DEFUNCT, "not gone"),
        (lambda stop: None, PROCESS_STATE_RUNNING, "not gone"),
    ],
)
def test_refuses_forced_unknown_or_unresolved_stop(
    tmp_path, monkeypatch, stop_mutation, state, message
):
    import speech_aware_evidence_acquisition.core.preparation_feature_provenance as module

    world = _world(tmp_path)
    stop = json.loads(world["stop"].read_text(encoding="utf-8"))
    stop_mutation(stop)
    world["stop"].write_text(json.dumps(stop), encoding="utf-8")
    monkeypatch.setattr(module, "process_state", lambda pid: state)

    with pytest.raises(PreparationError, match=message):
        _prepare(tmp_path, world)


def test_warm_reuse_requires_matching_prior_final_provenance(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_feature_provenance as module

    world = _world(tmp_path)
    monkeypatch.setattr(module, "process_state", lambda pid: PROCESS_STATE_GONE)
    _prepare(tmp_path, world)
    prior_path = tmp_path / "provenance.json"
    prior_sha = _sha(prior_path.read_bytes())

    warm_root = tmp_path / "warm"
    warm_root.mkdir()
    warm = _world(warm_root)
    record = warm["encoding_document"]
    for current, prior in zip(record["entries"], world["encoding_document"]["entries"], strict=True):
        current.update(
            status="verified-warm-reuse",
            current_contact_id=None,
            source_contact_id=prior["current_contact_id"],
            source_provenance_receipt_sha256=prior_sha,
        )
    record["current_contact_count"] = 0
    record["cost"]["calls_used"] = 0
    warm["encoding"].write_text(json.dumps(record), encoding="utf-8")

    result = _prepare(warm_root, warm, sources=(prior_path,))
    assert result["cache"] == "cold"
    warm_output = json.loads(
        (warm_root / "provenance.json").read_text(encoding="utf-8")
    )["output"]
    assert warm_output["current_contact_count"] == 0
    assert all(
        entry["status"] == "verified-warm-reuse"
        for entry in warm_output["entries"]
    )

    record["entries"][0]["source_contact_id"] = "wrong"
    warm["encoding"].write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(PreparationError, match="source contact"):
        prepare_window_feature_provenance(
            warm_root / "wrong.json",
            runtime_receipt_path=warm["runtime"],
            session_receipt_path=warm["session"],
            stop_receipt_path=warm["stop"],
            encoding_record_path=warm["encoding"],
            cache_audit_path=warm["audit"],
            expected_run_id="SAEA-E21-ENCODE-FOUR",
            expected_attempt_id="attempt-encode-four",
            expected_session_id="root-preprocess-session",
            source_provenance_paths=(prior_path,),
        )


def test_public_stop_loader_accepts_legacy_shape_and_checks_chain(tmp_path):
    world = _world(tmp_path)
    stop = json.loads(world["stop"].read_text(encoding="utf-8"))
    stop.pop("final_process_state")
    world["stop"].write_text(json.dumps(stop), encoding="utf-8")

    session, loaded = load_preprocess_stop_chain(
        session_receipt_path=world["session"],
        stop_receipt_path=world["stop"],
        runtime_receipt=json.loads(world["runtime"].read_text(encoding="utf-8")),
    )
    assert session.session_id == "root-preprocess-session"
    assert loaded == stop
