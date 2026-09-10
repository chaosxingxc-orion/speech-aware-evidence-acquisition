"""Prepared-cache configuration reaches the one shared transport factory."""

import hashlib
import json
import struct
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.config import (
    ConfigError,
    prepared_window_feature_cache,
)
from speech_aware_evidence_acquisition.core.configured_transport import (
    build_configured_transport,
)
from speech_aware_evidence_acquisition.core.model import (
    LlamaServerTransport,
    PreparedFeatureCacheError,
    legacy_audio_feature_cache_key,
)
from speech_aware_evidence_acquisition.core.preparation import (
    canonical_bytes,
    digest,
    prepare_artifact,
)
from speech_aware_evidence_acquisition.core.preparation_feature_cache import (
    prepare_feature_cache_audit,
)
from speech_aware_evidence_acquisition.core.preparation_feature_provenance import (
    PROVENANCE_KIND,
    PROVENANCE_SCHEMA,
    PROVENANCE_STATE,
)
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WindowFeatureEncoderIdentity,
    WindowRequestBatch,
)
from speech_aware_evidence_acquisition.core.session import (
    ModelFileRef,
    SESSION_RECEIPT_SCHEMA,
    SessionReceipt,
    SessionError,
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _world(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.configured_transport as module
    import speech_aware_evidence_acquisition.core.model.transport as transport_module

    data = tmp_path / "data"
    data.mkdir()
    media = data / "windows/sample.wav"
    media.parent.mkdir()
    media.write_bytes(b"synthetic pcm")
    parent = data / "parent.wav"
    parent.write_bytes(b"parent")
    payload = {
        "request_id": "request-1",
        "carrier_lock_key": "earnings21-original",
        "sample_id": "sample",
        "speech_ref": "earnings21-original/sample",
        "media_relpath": "windows/sample.wav",
        "audio_seconds": 1.0,
        "sample_rate_hz": 16000,
        "task_instruction": "Transcribe the speech.",
        "history": [],
        "decoding_params": {"temperature": 0},
    }
    source = {
        "sample_id": "sample",
        "parent_media_relpath": "parent.wav",
        "parent_sha256": _sha(parent.read_bytes()),
        "start_seconds": 0.0,
        "end_seconds": 1.0,
        "audio_seconds": 1.0,
        "sample_rate_hz": 16000,
        "media_relpath": "windows/sample.wav",
        "sha256": _sha(media.read_bytes()),
        "bytes": media.stat().st_size,
        "iteration": 0,
        "preprocess": [],
        "pre_sha256": None,
    }
    identity = WindowFeatureEncoderIdentity(
        runtime_receipt_sha256="1" * 64,
        build_commit="2" * 40,
        decoder_gguf_sha256="3" * 64,
        mmproj_sha256="4" * 64,
    )
    cache = data / "cache"
    cache.mkdir()
    key = legacy_audio_feature_cache_key(media.read_bytes())
    (cache / f"{key}_o0.feat").write_bytes(
        struct.pack("<QQ", 2, 4) + b"\x00" * 32
    )
    batch = WindowRequestBatch(
        payloads=(payload,),
        request_keys=("sample#w0001",),
        source_bindings=(source,),
    )
    audit_path = data / "prepared/audit.json"
    audit_result = prepare_feature_cache_audit(
        audit_path,
        batches={"generation": batch},
        data_root=data,
        encoder_identity=identity,
        legacy_cache_dir=cache,
        expected_n_embd=4,
    )
    audit = json.loads(audit_path.read_text())["output"]
    provenance_output = {
        "schema": PROVENANCE_SCHEMA,
        "state": PROVENANCE_STATE,
        "encoder_identity": identity.as_json(),
        "cache_audit_file_sha256": audit_result["sha256"],
        "inventory_sha256": audit["inventory_sha256"],
        "feature_outputs": [
            {
                "audio_sha256": item["audio_sha256"],
                "cache_key": item["cache_key"],
                "chunks": item["chunks"],
            }
            for item in audit["entries"]
        ],
    }
    provenance_path = data / "prepared/provenance.json"
    provenance_result = prepare_artifact(
        provenance_path,
        kind=PROVENANCE_KIND,
        inputs={"synthetic": True},
        producer=lambda: provenance_output,
    )
    values = {
        "transport": "llama-server",
        "base_url": "http://127.0.0.1:8080",
        "server_args": ["--no-mmproj-offload"],
        "server_env": {
            "LLAMA_MTMD_FEAT_CACHE_DIR": str(cache),
            "LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT": "1",
        },
        "feature_encoder_runtime_receipt": "receipts/encoder.json",
        "prepared_window_feature_cache": {
            "audit": {
                "relpath": audit_path.relative_to(data).as_posix(),
                "sha256": audit_result["sha256"],
            },
            "provenance": {
                "relpath": provenance_path.relative_to(data).as_posix(),
                "sha256": provenance_result["sha256"],
            },
            "expected_n_embd": 4,
        },
    }
    models = (
        ModelFileRef("models/decoder.gguf", "3" * 64),
        ModelFileRef("models/mmproj.gguf", "4" * 64),
    )
    session = SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA,
        study=STUDY_SLUG,
        session_id="session",
        binary_path="bin/server",
        binary_sha256="5" * 64,
        argv=("bin/server", "--no-mmproj-offload"),
        pid=123,
        host="127.0.0.1",
        port=8080,
        model_files=models,
        started_at="2026-09-10T00:00:00+00:00",
        startup_stdout_sha256="6" * 64,
    )
    verification_calls = []

    def verify(**kwargs):
        verification_calls.append(kwargs)
        return SimpleNamespace(encoder_identity=identity)

    monkeypatch.setattr(module, "verify_feature_encoder_runtime", verify)
    monkeypatch.setattr(transport_module, "assert_session_alive", lambda *args: None)
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    return SimpleNamespace(
        data=data,
        media=media,
        payload=payload,
        identity=identity,
        values=values,
        session=session,
        runtime_root=runtime_root,
        runtime_receipt={},
        audit_path=audit_path,
        provenance_path=provenance_path,
        verification_calls=verification_calls,
    )


def _factory(posted):
    def build(values, data_root, **kwargs):
        return LlamaServerTransport(
            values["base_url"],
            data_root,
            kwargs["session"],
            kwargs["runtime_receipt"],
            kwargs["runtime_root"],
            post=lambda url, body: posted.append(body)
            or json.dumps(
                {
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {},
                }
            ).encode(),
            feature_cache_guard=kwargs["feature_cache_guard"],
        )

    return build


def test_absent_opt_in_preserves_exact_historical_factory_kwargs(tmp_path):
    captured = []

    def factory(*args, **kwargs):
        captured.append((args, kwargs))
        return "transport"

    values = {"transport": "fake"}
    result = build_configured_transport(
        values,
        tmp_path,
        repo_root=tmp_path,
        session="session",
        runtime_receipt={"runtime": True},
        runtime_root=tmp_path,
        transport_factory=factory,
    )
    assert result == "transport"
    assert captured == [
        (
            (values, tmp_path),
            {
                "session": "session",
                "runtime_receipt": {"runtime": True},
                "runtime_root": tmp_path,
            },
        )
    ]


def test_configured_guard_applies_to_render_and_post(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch)
    posted = []
    transport = build_configured_transport(
        world.values,
        world.data,
        repo_root=tmp_path,
        session=world.session,
        runtime_receipt=world.runtime_receipt,
        runtime_root=world.runtime_root,
        transport_factory=_factory(posted),
    )
    body = transport.render_request(canonical_bytes(world.payload))
    assert body["messages"][1]["content"][-1]["type"] == "input_audio"
    transport(canonical_bytes(world.payload))
    assert len(posted) == 1
    assert len(world.verification_calls) == 1
    assert world.verification_calls[0]["repo_root"] == tmp_path
    assert world.verification_calls[0]["data_root"] == world.data
    assert world.verification_calls[0]["runtime_root"] == world.runtime_root
    assert world.verification_calls[0]["generation_receipt"] is world.runtime_receipt
    world.media.write_bytes(b"changed pcm")
    with pytest.raises(PreparedFeatureCacheError, match="source SHA256"):
        transport.render_request(canonical_bytes(world.payload))
    with pytest.raises(PreparedFeatureCacheError, match="source SHA256"):
        transport(canonical_bytes(world.payload))
    assert len(posted) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        lambda world: world.values["prepared_window_feature_cache"]["audit"].update(
            sha256="9" * 64
        ),
        lambda world: world.values["prepared_window_feature_cache"]["audit"].update(
            relpath="../audit.json"
        ),
        lambda world: world.values["server_env"].pop(
            "LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT"
        ),
        lambda world: world.values["server_args"].clear(),
        lambda world: world.values.update(server_env=[]),
        lambda world: world.values.update(server_args="invalid"),
        lambda world: world.values["server_env"].pop("LLAMA_MTMD_FEAT_CACHE_DIR"),
        lambda world: world.values["prepared_window_feature_cache"]["audit"].update(
            relpath="prepared/missing-audit.json"
        ),
        lambda world: setattr(
            world, "session", replace(world.session, argv=("bin/server",))
        ),
    ],
)
def test_wrong_pins_paths_or_strict_serving_identity_refuse_before_factory(
    tmp_path, monkeypatch, mutation
):
    world = _world(tmp_path, monkeypatch)
    mutation(world)
    calls = []
    with pytest.raises((ConfigError, ValueError, SessionError)):
        build_configured_transport(
            world.values,
            world.data,
            repo_root=tmp_path,
            session=world.session,
            runtime_receipt=world.runtime_receipt,
            runtime_root=world.runtime_root,
            transport_factory=lambda *args, **kwargs: calls.append(1),
        )
    assert calls == []


def test_wrong_verified_encoder_identity_refuses_before_factory(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.configured_transport as module

    world = _world(tmp_path, monkeypatch)
    wrong = WindowFeatureEncoderIdentity(
        runtime_receipt_sha256="7" * 64,
        build_commit="2" * 40,
        decoder_gguf_sha256="3" * 64,
        mmproj_sha256="4" * 64,
    )
    monkeypatch.setattr(
        module,
        "verify_feature_encoder_runtime",
        lambda **kwargs: SimpleNamespace(encoder_identity=wrong),
    )
    calls = []
    with pytest.raises(ValueError, match="encoder identities differ"):
        build_configured_transport(
            world.values,
            world.data,
            repo_root=tmp_path,
            session=world.session,
            runtime_receipt=world.runtime_receipt,
            runtime_root=world.runtime_root,
            transport_factory=lambda *args, **kwargs: calls.append(1),
        )
    assert calls == []


def test_missing_verified_encoder_receipt_refuses_before_factory(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.configured_transport as module

    world = _world(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "verify_feature_encoder_runtime", lambda **kwargs: None)
    with pytest.raises(ValueError, match="feature_encoder_runtime_receipt"):
        build_configured_transport(
            world.values,
            world.data,
            repo_root=tmp_path,
            session=world.session,
            runtime_receipt=world.runtime_receipt,
            runtime_root=world.runtime_root,
            transport_factory=lambda *args, **kwargs: pytest.fail("factory called"),
        )


def test_self_consistent_provenance_with_wrong_audit_binding_refuses(
    tmp_path, monkeypatch
):
    world = _world(tmp_path, monkeypatch)
    document = json.loads(world.provenance_path.read_text())
    document["output"]["cache_audit_file_sha256"] = "9" * 64
    document["output_sha256"] = digest(document["output"])
    world.provenance_path.write_text(json.dumps(document))
    world.values["prepared_window_feature_cache"]["provenance"]["sha256"] = _sha(
        world.provenance_path.read_bytes()
    )
    calls = []
    with pytest.raises(ValueError, match="does not bind the audit"):
        build_configured_transport(
            world.values,
            world.data,
            repo_root=tmp_path,
            session=world.session,
            runtime_receipt=world.runtime_receipt,
            runtime_root=world.runtime_root,
            transport_factory=lambda *args, **kwargs: calls.append(1),
        )
    assert calls == []


def test_self_consistent_provenance_with_changed_feature_descriptor_refuses(
    tmp_path, monkeypatch
):
    world = _world(tmp_path, monkeypatch)
    document = json.loads(world.provenance_path.read_text())
    document["output"]["feature_outputs"][0]["chunks"][0]["file_sha256"] = (
        "9" * 64
    )
    document["output_sha256"] = digest(document["output"])
    world.provenance_path.write_text(json.dumps(document))
    world.values["prepared_window_feature_cache"]["provenance"]["sha256"] = _sha(
        world.provenance_path.read_bytes()
    )
    calls = []
    with pytest.raises(ValueError, match="feature descriptors differ"):
        build_configured_transport(
            world.values,
            world.data,
            repo_root=tmp_path,
            session=world.session,
            runtime_receipt=world.runtime_receipt,
            runtime_root=world.runtime_root,
            transport_factory=lambda *args, **kwargs: calls.append(1),
        )
    assert calls == []


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda output: output.update(state="incomplete"), "not complete"),
        (
            lambda output: output.update(inventory_sha256="9" * 64),
            "inventory identities differ",
        ),
    ],
)
def test_incomplete_or_wrong_inventory_provenance_refuses(
    tmp_path, monkeypatch, mutation, message
):
    world = _world(tmp_path, monkeypatch)
    document = json.loads(world.provenance_path.read_text())
    mutation(document["output"])
    document["output_sha256"] = digest(document["output"])
    world.provenance_path.write_text(json.dumps(document))
    world.values["prepared_window_feature_cache"]["provenance"]["sha256"] = _sha(
        world.provenance_path.read_bytes()
    )
    with pytest.raises(ValueError, match=message):
        build_configured_transport(
            world.values,
            world.data,
            repo_root=tmp_path,
            session=world.session,
            runtime_receipt=world.runtime_receipt,
            runtime_root=world.runtime_root,
            transport_factory=lambda *args, **kwargs: pytest.fail("factory called"),
        )


def test_config_parser_rejects_extra_or_malformed_fields():
    assert prepared_window_feature_cache({}) is None
    with pytest.raises(ConfigError, match="exactly"):
        prepared_window_feature_cache(
            {"prepared_window_feature_cache": {"audit": {}, "extra": True}}
        )


def test_registered_factory_enforces_prepared_cache_for_four_requests(tmp_path, monkeypatch):
    """Exercise the real registry factory; fake only session liveness and HTTP."""
    world = _world(tmp_path, monkeypatch)
    transport = build_configured_transport(
        world.values, world.data, repo_root=tmp_path, session=world.session,
        runtime_receipt=world.runtime_receipt, runtime_root=world.runtime_root,
    )
    posted = []

    def post(_url, body):
        posted.append(json.loads(body))
        return json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {}}).encode()

    monkeypatch.setattr(transport, "_post", post)
    for index in range(4):
        payload = {**world.payload, "request_id": f"prepared-request-{index}"}
        transport(canonical_bytes(payload))
    assert len(posted) == 4
    assert all(body["messages"][1]["content"][-1]["type"] == "input_audio" for body in posted)
    world.media.write_bytes(b"changed pcm")
    with pytest.raises(PreparedFeatureCacheError, match="source SHA256"):
        transport(canonical_bytes(world.payload))
    assert len(posted) == 4
