"""Synthetic attachment and pre-contact checks for configured window encoding."""

from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_window_encoding import (
    prepare_window_feature_encoding,
)


def test_absent_encoder_config_refuses_before_authorization(tmp_path):
    calls = []
    runtime = SimpleNamespace(
        preparation_context=lambda: {"values": {}},
        authorize_preparation_client=lambda **kw: calls.append(kw),
    )
    with pytest.raises(PreparationError, match="window_feature_preparation"):
        prepare_window_feature_encoding(
            runtime, tmp_path / "output.json", policy=object()
        )
    assert calls == []


def test_non_preprocess_runtime_refuses_before_any_attachment(tmp_path):
    runtime = SimpleNamespace(
        preparation_context=lambda: {
            "values": {
                "decoding_params": {"max_tokens": 1},
                "window_feature_preparation": {
                    "inventory_relpath": "input.json",
                    "inventory_sha256": "a" * 64,
                    "source_run_id": "source-run",
                    "expected_n_embd": 4,
                    "instruction": "Observe the speech.",
                },
            },
            "runtime_receipt": {"role": "inference"},
        }
    )
    with pytest.raises(PreparationError, match="preprocess"):
        prepare_window_feature_encoding(
            runtime, tmp_path / "output.json", policy=object()
        )


def _world(tmp_path):
    import json
    from test_preparation_runtime import _world as runtime_world
    from test_preparation_feature_cache import _batch
    from speech_aware_evidence_acquisition.core.preparation_runtime import (
        verify_feature_encoder_runtime,
    )
    from speech_aware_evidence_acquisition.core.preparation_windows import (
        prepare_window_feature_inventory,
    )
    from speech_aware_evidence_acquisition.core.session import load_runtime_receipt
    from speech_aware_evidence_acquisition.core.session.serving import (
        serving_session_dir,
        SESSION_RECEIPT_NAME,
    )

    repo, runtime_root, data, _, receipt, receipt_path = runtime_world(tmp_path)
    values = {
        "runtime_receipt": "receipts/preprocess.json",
        "model_materialization_root": str(data),
        "transport": "llama-server",
        "arm": "bare-core",
        "decoding_params": {"temperature": 0, "max_tokens": 1},
    }
    identity = verify_feature_encoder_runtime(
        repo_root=repo,
        data_root=data,
        runtime_root=runtime_root,
        values={
            **values,
            "feature_encoder_runtime_receipt": "receipts/preprocess.json",
        },
        generation_receipt=receipt,
        receipt_loader=load_runtime_receipt,
    ).encoder_identity
    batch = _batch(data, run="source-run")
    artifact = data / "inventory.json"
    prepared = prepare_window_feature_inventory(
        artifact,
        batches={"source-run": batch},
        data_root=data,
        encoder_identity=identity,
    )
    cache = tmp_path / "cache"
    cache.mkdir()
    values["server_env"] = {"LLAMA_MTMD_FEAT_CACHE_DIR": str(cache)}
    values["window_feature_preparation"] = {
        "inventory_relpath": "inventory.json",
        "inventory_sha256": prepared["sha256"],
        "source_run_id": "source-run",
        "expected_n_embd": 4,
        "instruction": "Observe the complete speech signal. Respond with OK.",
    }
    plan = SimpleNamespace(planned_model_calls=1)
    context = dict(
        values=values,
        runtime_receipt=receipt,
        data_root=data,
        repo_root=repo,
        runtime_root=runtime_root,
        execution_plan=plan,
        sample_ids=["sample-1"],
        run_id="encoding-run",
        attempt_id="attempt",
        required_identity={"role": "preprocess"},
    )
    events = []
    binding = SimpleNamespace(
        allowed_sample_ids={"sample-1"},
        media_relpaths={"sample-1": batch.source_bindings[0]["parent_media_relpath"]},
        sample_facts={"sample-1": (100, 16000)},
    )

    def authorize(**kw):
        events.append("gate")
        assert kw == {"contact_cap": 1}
        return plan, object()

    runtime = SimpleNamespace(
        preparation_context=lambda: context,
        authorize_preparation_client=authorize,
        frozen_core_client_kwargs=lambda **kw: {
            **kw,
            "binding": binding,
            "run_dir": data / "run",
            "arm": "bare-core",
        },
    )
    policy = SimpleNamespace(
        expected_session_id="cpu-session",
        assert_lease=lambda *_a, **_k: events.append("lease"),
    )
    directory = serving_session_dir(data, "cpu-session")
    directory.mkdir(parents=True)
    (directory / SESSION_RECEIPT_NAME).write_text(
        json.dumps({"synthetic": "verified by injected attacher"})
    )

    def attach(**kw):
        events.append("attach")
        return (
            directory,
            {"session_id": "cpu-session"},
            SimpleNamespace(role="preprocess"),
        )

    def transport(*_a, **_k):
        events.append("transport")
        return lambda _: b""

    clients = []
    from test_preparation_encoding import Client
    from test_preparation_feature_cache import _write_chunk

    class ProducingClient(Client):
        def __init__(self, **kw):
            super().__init__()
            clients.append(self)
            events.append("client")
            assert kw["slice_registry"].__class__.__name__ == "SliceRegistry"

        def complete(self, *args, **kw):
            value = super().complete(*args, **kw)
            source = batch.source_bindings[0]
            _write_chunk(cache, (data / source["media_relpath"]).read_bytes())
            return value

    options = dict(
        policy=policy,
        attach=attach,
        transport_factory=transport,
        client_factory=ProducingClient,
    )
    return runtime, options, context, events, clients, tmp_path / "encoding.json"


def test_configured_encoder_attaches_after_gate_and_reuses_without_contact(tmp_path):
    runtime, options, context, events, clients, output = _world(tmp_path)
    result = prepare_window_feature_encoding(runtime, output, **options)
    assert result["cache"] == "cold" and len(clients) == 1 and clients[0].closed == 1
    assert events.index("gate") < events.index("attach") < events.index("client")
    assert events.count("lease") >= 2
    events.clear()
    runtime.authorize_preparation_client = lambda **_: pytest.fail(
        "warm encoding must not reopen a gate/client"
    )
    assert (
        prepare_window_feature_encoding(runtime, output, **options)["cache"] == "warm"
    )
    assert events == [] and len(clients) == 1


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-roster",
        "wrong-prefix",
        "wrong-budget",
        "validation-mode",
        "wrong-parent",
        "wrong-inventory-hash",
    ],
)
def test_configured_input_faults_refuse_before_gate_or_attachment(tmp_path, fault):
    runtime, options, context, events, clients, output = _world(tmp_path)
    if fault == "wrong-roster":
        context["sample_ids"] = ["different"]
    elif fault == "wrong-prefix":
        context["values"]["window_feature_preparation"]["source_run_id"] = "different"
    elif fault == "wrong-budget":
        context["execution_plan"].planned_model_calls = 2
    elif fault == "validation-mode":
        context["values"]["server_env"]["LLAMA_MTMD_FEAT_CACHE_VALIDATE"] = "0"
    elif fault == "wrong-inventory-hash":
        context["values"]["window_feature_preparation"]["inventory_sha256"] = "0" * 64
    else:
        (context["data_root"] / "datasets/e21/sample-1.wav").write_bytes(
            b"changed parent"
        )
    with pytest.raises(PreparationError):
        prepare_window_feature_encoding(runtime, output, **options)
    assert events == [] and clients == [] and not output.exists()


def test_missing_resident_session_never_constructs_encoder_client(tmp_path):
    runtime, options, _context, events, clients, output = _world(tmp_path)

    def absent(**_kw):
        raise PreparationError("required resident session absent")

    options["attach"] = absent
    with pytest.raises(PreparationError, match="resident session absent"):
        prepare_window_feature_encoding(runtime, output, **options)
    assert events == ["gate", "lease"] and clients == []


@pytest.mark.parametrize("parameters", [{"max_tokens": 2}, {"max_tokens": True}, {}])
def test_invalid_encoding_parameters_refuse_before_opening_attempt(
    tmp_path, parameters
):
    runtime, options, context, events, clients, output = _world(tmp_path)
    context["values"]["decoding_params"] = parameters
    with pytest.raises(PreparationError, match="max_tokens"):
        prepare_window_feature_encoding(runtime, output, **options)
    assert events == [] and clients == []


def test_interrupted_encoding_refuses_without_leaving_client_open(tmp_path):
    runtime, options, _context, _events, clients, output = _world(tmp_path)
    output.with_name(output.name + ".encoder-started.json").write_text("{}")
    with pytest.raises(PreparationError, match="new registered attempt"):
        prepare_window_feature_encoding(runtime, output, **options)
    assert len(clients) == 1 and clients[0].closed == 1

def _warm_record_fixture(tmp_path, *, encoder_identity=None):
    import hashlib
    import struct

    from speech_aware_evidence_acquisition.core.model import (
        legacy_audio_feature_cache_key,
    )
    from speech_aware_evidence_acquisition.core.preparation import prepare_artifact
    from speech_aware_evidence_acquisition.core.preparation_encoding import (
        SCHEMA,
    )

    root = tmp_path / "data"
    root.mkdir()
    media = root / "warm.wav"
    audio = b"warm audio"
    media.write_bytes(audio)
    cache = root / "cache"
    cache.mkdir()
    key = legacy_audio_feature_cache_key(audio)
    feature = struct.pack("<QQ", 2, 4) + b"\x00" * 32
    chunk = cache / f"{key}_o0.feat"
    chunk.write_bytes(feature)
    identity = encoder_identity or {
        "runtime_receipt_sha256": "1" * 64,
        "build_commit": "a" * 40,
        "decoder_gguf_sha256": "2" * 64,
        "mmproj_sha256": "3" * 64,
    }
    output = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": "source-run",
        "attempt_id": "source-attempt",
        "session_id": "source-session",
        "runtime_receipt_file_sha256": "a" * 64,
        "runtime_receipt_document_sha256": "b" * 64,
        "session_receipt_file_sha256": "c" * 64,
        "inventory_sha256": "d" * 64,
        "encoder_identity": identity,
        "trace_manifest_hash": "e" * 64,
        "cost": {"calls_used": 1},
        "current_contact_count": 1,
        "entries": [{
            "audio_sha256": hashlib.sha256(audio).hexdigest(),
            "cache_key": key,
            "status": "encoded",
            "success": True,
            "current_contact_id": "source-contact",
            "source_contact_id": None,
            "source_provenance_receipt_sha256": None,
        }],
        "feature_outputs": [{
            "audio_sha256": hashlib.sha256(audio).hexdigest(),
            "cache_key": key,
            "chunks": [{
                "ordinal": 0,
                "relative_filename": f"{key}_o0.feat",
                "file_sha256": hashlib.sha256(feature).hexdigest(),
                "file_size": len(feature),
                "n_tokens": 2,
                "n_embd": 4,
            }],
        }],
    }
    artifact = root / "warm.json"
    prepare_artifact(
        artifact,
        kind="window-feature-encoding-v1",
        inputs={"source": "synthetic"},
        producer=lambda: output,
        contact_class="encoder",
    )
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    provenance = {
        "schema": "saea-window-feature-preparation-provenance-v1",
        "state": "source-bound-feature-cache-verified-serving-unqualified",
        "encoding_record_file_sha256": artifact_sha,
        "encoder_identity": identity,
        "entries": output["entries"],
        "feature_outputs": output["feature_outputs"],
    }
    provenance_path = root / "provenance.json"
    prepare_artifact(
        provenance_path,
        kind="window-feature-preparation-provenance-v1",
        inputs={"source": "synthetic"},
        producer=lambda: provenance,
        contact_class="model-free",
    )
    provenance_sha = hashlib.sha256(provenance_path.read_bytes()).hexdigest()
    return root, cache, output, artifact_sha, {
        "relpath": "warm.json",
        "sha256": artifact_sha,
        "provenance_relpath": "provenance.json",
        "provenance_sha256": provenance_sha,
    }, {
        "media_relpath": "warm.wav",
        "sha256": hashlib.sha256(audio).hexdigest(),
    }, identity, hashlib.sha256(audio).hexdigest()


def test_partial_warm_artifact_loads_verified_source_and_cache(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_window_encoding import (
        _warm_provenance,
    )

    root, cache, _output, _artifact_sha, binding, source, identity, audio = (
        _warm_record_fixture(tmp_path)
    )
    fresh_media = root / "fresh.wav"
    fresh_media.write_bytes(b"fresh audio")
    fresh_audio = __import__("hashlib").sha256(fresh_media.read_bytes()).hexdigest()
    warm = _warm_provenance(
        {"warm_encoding_artifacts": [binding]},
        root,
        cache,
        {
            audio: source,
            fresh_audio: {
                "media_relpath": "fresh.wav",
                "sha256": fresh_audio,
            },
        },
        identity,
        4,
    )
    assert warm[audio]["source_contact_id"] == "source-contact"
    assert len({audio, fresh_audio}) - len(warm) == 1
    assert warm[audio]["source_provenance_receipt_sha256"] == binding["provenance_sha256"]


def test_partial_warm_refuses_wrong_wrapper_hash_and_changed_cache(tmp_path):
    import struct

    from speech_aware_evidence_acquisition.core.preparation_window_encoding import (
        _warm_provenance,
    )

    root, cache, _output, _artifact_sha, binding, source, identity, audio = (
        _warm_record_fixture(tmp_path)
    )
    bad_binding = {**binding, "sha256": "0" * 64}
    with pytest.raises(PreparationError, match="invalid or unproven"):
        _warm_provenance(
            {"warm_encoding_artifacts": [bad_binding]},
            root,
            cache,
            {audio: source},
            identity,
            4,
        )
    next(cache.glob("*")).write_bytes(struct.pack("<QQ", 2, 4) + b"\x01" * 32)
    with pytest.raises(PreparationError, match="differs"):
        _warm_provenance(
            {"warm_encoding_artifacts": [binding]},
            root,
            cache,
            {audio: source},
            identity,
            4,
        )


def test_partial_warm_refuses_source_encoder_mismatch(tmp_path):
    from speech_aware_evidence_acquisition.core.preparation_window_encoding import (
        _warm_provenance,
    )

    root, cache, _output, _artifact_sha, binding, source, _identity, audio = (
        _warm_record_fixture(tmp_path)
    )
    with pytest.raises(PreparationError, match="encoder identity"):
        _warm_provenance(
            {"warm_encoding_artifacts": [binding]},
            root,
            cache,
            {audio: source},
            {
                "runtime_receipt_sha256": "1" * 64,
                "build_commit": "b" * 40,
                "decoder_gguf_sha256": "2" * 64,
                "mmproj_sha256": "3" * 64,
            },
            4,
        )

def test_runtime_partial_warm_caps_fresh_contacts(tmp_path, monkeypatch):
    import hashlib
    import json
    from types import SimpleNamespace

    import speech_aware_evidence_acquisition.core.preparation_window_encoding as module

    root, cache, _record, _artifact_sha, binding, warm_source, identity, warm_audio = (
        _warm_record_fixture(tmp_path)
    )
    warm_media = root / "derived/obs-slices/source-run/sample-1/i0000.wav"
    warm_media.parent.mkdir(parents=True)
    warm_media.write_bytes((root / "warm.wav").read_bytes())
    warm_parent = root / "warm-parent.wav"
    warm_parent.write_bytes(b"warm parent")
    fresh_parent = root / "fresh-parent.wav"
    fresh_parent.write_bytes(b"fresh parent")
    fresh_media = root / "derived/obs-slices/source-run/sample-2/i0000.wav"
    fresh_media.parent.mkdir(parents=True)
    fresh_media.write_bytes(b"fresh audio")
    fresh_source = {
        "sample_id": "sample-2",
        "parent_media_relpath": "fresh-parent.wav",
        "parent_sha256": hashlib.sha256(fresh_parent.read_bytes()).hexdigest(),
        "media_relpath": "derived/obs-slices/source-run/sample-2/i0000.wav",
        "sha256": hashlib.sha256(fresh_media.read_bytes()).hexdigest(),
    }
    sources = {
        warm_audio: {
            **warm_source,
            "sample_id": "sample-1",
            "media_relpath": "derived/obs-slices/source-run/sample-1/i0000.wav",
            "parent_media_relpath": "warm-parent.wav",
            "parent_sha256": hashlib.sha256(warm_parent.read_bytes()).hexdigest(),
        },
        fresh_source["sha256"]: fresh_source,
    }
    values = {
        "arm": "bare-core",
        "runtime_receipt": "receipts/preprocess.json",
        "decoding_params": {"max_tokens": 1},
        "server_env": {"LLAMA_MTMD_FEAT_CACHE_DIR": str(cache)},
        "window_feature_preparation": {
            "inventory_relpath": "inventory.json",
            "inventory_sha256": "a" * 64,
            "source_run_id": "source-run",
            "expected_n_embd": 4,
            "instruction": "Observe the speech.",
            "warm_encoding_artifacts": [binding],
        },
    }
    plan = SimpleNamespace(planned_model_calls=1)
    context = {
        "values": values,
        "runtime_receipt": {"role": "preprocess"},
        "data_root": root,
        "repo_root": root,
        "runtime_root": root,
        "execution_plan": plan,
        "sample_ids": ["sample-1", "sample-2"],
        "run_id": "run",
        "attempt_id": "attempt",
        "required_identity": {"role": "preprocess"},
    }
    events = []
    binding_obj = SimpleNamespace(
        allowed_sample_ids={"sample-1", "sample-2"},
        media_relpaths={"sample-1": "warm.wav", "sample-2": fresh_source["media_relpath"]},
        sample_facts={"sample-1": (1, 16000), "sample-2": (1, 16000)},
    )
    runtime = SimpleNamespace(
        preparation_context=lambda: context,
        authorize_preparation_client=lambda **kwargs: (
            events.append(("authorize", kwargs["contact_cap"])) or (plan, object())
        ),
        frozen_core_client_kwargs=lambda **kwargs: {"binding": binding_obj},
    )
    session_dir = module.serving_session_dir(root, "session")
    session_dir.mkdir(parents=True)
    (session_dir / module.SESSION_RECEIPT_NAME).write_text(
        json.dumps({"session_id": "session"})
    )
    policy = SimpleNamespace(
        expected_session_id="session",
        assert_lease=lambda *_a, **_k: events.append(("lease",)),
    )
    def attached(**_kwargs):
        return (
            session_dir,
            {"session_id": "session"},
            SimpleNamespace(role="preprocess"),
        )
    clients = []

    class Client:
        def __init__(self, **_kwargs):
            self.calls = []
            clients.append(self)

        def complete(self, *_args, **_kwargs):
            self.calls.append("complete")

    def fake_encode(*, client, warm_provenance, **_kwargs):
        assert len(warm_provenance) == 1
        client.complete()
        return {"current_contact_count": 1, "entries": ["warm", "fresh"]}

    monkeypatch.setattr(module, "_inventory", lambda *_args: {"encoder_identity": identity})
    monkeypatch.setattr(module, "window_encoding_sources", lambda *_args: sources)
    monkeypatch.setattr(module, "model_materialization_root", lambda _values: None)
    monkeypatch.setattr(
        module,
        "verify_feature_encoder_runtime",
        lambda **_kwargs: SimpleNamespace(
            encoder_identity=SimpleNamespace(as_json=lambda: identity),
            receipt_sha256="b" * 64,
        ),
    )
    monkeypatch.setattr(module, "build_configured_transport", lambda *_a, **_k: object())
    monkeypatch.setattr(module, "encode_window_feature_cache", fake_encode)
    result = module.prepare_window_feature_encoding(
        runtime,
        tmp_path / "output.json",
        policy=policy,
        attach=attached,
        client_factory=Client,
    )
    assert result["current_contact_count"] == 1
    assert events[0] == ("authorize", 1)
    assert len(clients) == 1 and clients[0].calls == ["complete"]

    import struct

    feature_path = next(cache.glob("*_o0.feat"))
    feature_path.write_bytes(struct.pack("<QQ", 2, 4) + b"\x01" * 32)
    events.clear()
    clients.clear()
    with pytest.raises(PreparationError, match="differs"):
        module.prepare_window_feature_encoding(
            runtime,
            tmp_path / "second-output.json",
            policy=policy,
            attach=attached,
            client_factory=Client,
        )
    assert events == [] and clients == []
