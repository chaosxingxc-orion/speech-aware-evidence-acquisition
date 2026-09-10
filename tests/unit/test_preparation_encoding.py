import hashlib
from dataclasses import dataclass
import pytest
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_encoding import (
    encode_window_feature_cache,
)
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WINDOW_FEATURE_INVENTORY_SCHEMA,
)

SHA = "a" * 64


def inventory(tmp_path, duplicate=False):
    data = tmp_path / "data"
    data.mkdir()
    media = data / "slices" / "one.wav"
    media.parent.mkdir()
    media.write_bytes(b"synthetic pcm")
    audio = hashlib.sha256(media.read_bytes()).hexdigest()
    source = {
        "sample_id": "s",
        "parent_media_relpath": "parent.wav",
        "parent_sha256": SHA,
        "start_seconds": 0.0,
        "end_seconds": 1.0,
        "audio_seconds": 1.0,
        "sample_rate_hz": 16000,
        "media_relpath": "slices/one.wav",
        "sha256": audio,
        "bytes": len(media.read_bytes()),
        "iteration": 0,
        "preprocess": [],
        "pre_sha256": None,
    }
    req = {"request_key": "s#w1", "source_provenance": source}
    rows = [req, {**req, "request_key": "s#w2"}] if duplicate else [req]
    return (
        data,
        {
            "schema": WINDOW_FEATURE_INVENTORY_SCHEMA,
            "encoder_identity": {"build": "x"},
            "batches": [{"name": "batch", "requests": rows}],
            "encoding_inputs": [
                {
                    "audio_sha256": audio,
                    "requests": (
                        [
                            {"batch": "batch", "request_key": "s#w1"},
                            {"batch": "batch", "request_key": "s#w2"},
                        ]
                        if duplicate
                        else [{"batch": "batch", "request_key": "s#w1"}]
                    ),
                }
            ],
        },
        audio,
    )


@dataclass
class Timing:
    request_id: str


class Client:
    def __init__(self):
        self.calls = []
        self.timings = []
        self.closed = 0

    def register_slice(self, r):
        self.calls.append(("slice", r))

    def complete(self, messages, *, decoding_params=None):
        self.calls.append(("complete", messages))
        self.timings.append(Timing(f"request-{len(self.timings) + 1}"))
        return "ignored"

    def close(self):
        self.closed += 1
        return {
            "trace_manifest_hash": "b" * 64,
            "cost": {"calls_used": len(self.timings)},
        }


def kwargs(tmp_path, data, inv, client):
    cache = tmp_path / "cache"
    cache.mkdir()
    return dict(
        inventory=inv,
        data_root=data,
        client=client,
        custody_guard=lambda: None,
        encoder_identity={"build": "x"},
        legacy_cache_dir=cache,
        expected_n_embd=4,
        output_path=tmp_path / "result.json",
        run_id="run",
        attempt_id="attempt",
        session_id="session",
        runtime_receipt_file_sha256=SHA,
        runtime_receipt_document_sha256=SHA,
        session_receipt_file_sha256=SHA,
        decoding_params={"temperature": 0, "max_tokens": 1},
    )


def test_encodes_deduplicated_audio_and_closes(tmp_path, monkeypatch):
    data, inv, _ = inventory(tmp_path, duplicate=True)
    client = Client()
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda **kwargs: type(
            "Inspection",
            (),
            {
                "audio_sha256": hashlib.sha256(
                    kwargs["audio_path"].read_bytes()
                ).hexdigest(),
                "cache_key": __import__(
                    "speech_aware_evidence_acquisition.core.preparation_encoding",
                    fromlist=["legacy_audio_feature_cache_key"],
                ).legacy_audio_feature_cache_key(kwargs["audio_path"].read_bytes()),
                "chunks": (),
            },
        )(),
    )
    result = encode_window_feature_cache(**kwargs(tmp_path, data, inv, client))
    assert result["contact_class"] == "encoder"
    assert (
        client.closed == 1 and len([x for x in client.calls if x[0] == "complete"]) == 1
    )


def test_existing_unproven_cache_refuses_before_contact(tmp_path, monkeypatch):
    data, inv, audio = inventory(tmp_path)
    client = Client()
    args = kwargs(tmp_path, data, inv, client)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.legacy_audio_feature_cache_key",
        lambda _: "key",
    )
    (args["legacy_cache_dir"] / "key_o0.feat").write_bytes(b"bad")
    with pytest.raises(PreparationError, match="unproven"):
        encode_window_feature_cache(**args)
    assert not client.calls and client.closed == 1


def test_failed_transport_closes_and_records_attempted_id_without_retry(
    tmp_path, monkeypatch
):
    data, inv, _ = inventory(tmp_path)

    class Failing(Client):
        @property
        def last_attempted_request_id(self):
            return "request-1"

        def complete(self, *args, **kwargs):
            raise RuntimeError("transport failed")

    client = Failing()
    args = kwargs(tmp_path, data, inv, client)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda **kwargs: type(
            "Inspection",
            (),
            {
                "audio_sha256": hashlib.sha256(
                    kwargs["audio_path"].read_bytes()
                ).hexdigest(),
                "cache_key": __import__(
                    "speech_aware_evidence_acquisition.core.preparation_encoding",
                    fromlist=["legacy_audio_feature_cache_key"],
                ).legacy_audio_feature_cache_key(kwargs["audio_path"].read_bytes()),
                "chunks": (),
            },
        )(),
    )
    with pytest.raises(RuntimeError, match="transport failed"):
        encode_window_feature_cache(**args)
    partial = (tmp_path / "result.json.partial.json").read_text()
    assert '"failed"' in partial and '"request-1"' in partial
    assert client.closed == 1


def test_real_frozen_client_registers_slice_and_sends_one_raw_request(
    tmp_path, monkeypatch
):
    import json, wave
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.config import protocol_hash
    from speech_aware_evidence_acquisition.rails import (
        AudioRef,
        FrozenCoreClient,
        build_payload_binding,
        build_slice_registry,
    )

    class Sample:
        def __init__(self, sid, ref):
            self.sample_id = sid
            self.audio_ref = ref
            self.audio_seconds = 2.0

    class Gate:
        def assert_model_touch_allowed(self, plan):
            pass

    class Transport:
        def __init__(self):
            self.payloads = []

        def __call__(self, raw):
            self.payloads.append(json.loads(raw))
            return b'{"text":"ok","usage":{"prompt_tokens":1,"completion_tokens":1}}'

    data = tmp_path / "data"
    parent = data / "parent.wav"
    parent.parent.mkdir()
    with wave.open(str(parent), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\\0\\0" * 32000)
    parent_sha = hashlib.sha256(parent.read_bytes()).hexdigest()
    sample = Sample("s", AudioRef(path="parent.wav", sha256=parent_sha).validate())
    plan = ExecutionPlan(
        run_id="SAEA-E-ENCODE",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="fake",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=2,
        planned_gpu_hours=1,
        planned_speech_audio_seconds=2,
        protocol_hash=protocol_hash("f" * 64, "bare-core", "a" * 64),
        attempt_id="attempt-encode",
    )
    registry = build_slice_registry(
        data_root=data, run_id=plan.run_id, samples=[sample]
    )
    rel = registry.slice_relpath("s", 0)
    media = data / rel
    media.parent.mkdir(parents=True)
    with wave.open(str(media), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\\0\\0" * 16000)
    sha = hashlib.sha256(media.read_bytes()).hexdigest()
    source = {
        "sample_id": "s",
        "parent_media_relpath": "parent.wav",
        "parent_sha256": parent_sha,
        "start_seconds": 0.0,
        "end_seconds": 1.0,
        "audio_seconds": 1.0,
        "sample_rate_hz": 16000,
        "media_relpath": rel,
        "sha256": sha,
        "bytes": media.stat().st_size,
        "iteration": 0,
        "preprocess": [],
        "pre_sha256": None,
    }
    inv = {
        "schema": WINDOW_FEATURE_INVENTORY_SCHEMA,
        "encoder_identity": {"encoder": "x"},
        "batches": [
            {
                "name": "batch",
                "requests": [{"request_key": "s#w1", "source_provenance": source}],
            }
        ],
        "encoding_inputs": [
            {
                "audio_sha256": sha,
                "requests": [{"batch": "batch", "request_key": "s#w1"}],
            }
        ],
    }
    transport = Transport()
    client = FrozenCoreClient(
        plan=plan,
        gate=Gate(),
        transport=transport,
        run_dir=tmp_path / "run",
        binding=build_payload_binding(
            carrier_lock_key="fake", samples=[sample], data_root=data, carrier_root=data
        ),
        slice_registry=registry,
    )
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda **kwargs: type(
            "Inspection",
            (),
            {
                "audio_sha256": hashlib.sha256(
                    kwargs["audio_path"].read_bytes()
                ).hexdigest(),
                "cache_key": __import__(
                    "speech_aware_evidence_acquisition.core.preparation_encoding",
                    fromlist=["legacy_audio_feature_cache_key"],
                ).legacy_audio_feature_cache_key(kwargs["audio_path"].read_bytes()),
                "chunks": (),
            },
        )(),
    )
    result = encode_window_feature_cache(
        inventory=inv,
        data_root=data,
        client=client,
        custody_guard=lambda: None,
        encoder_identity={"encoder": "x"},
        legacy_cache_dir=cache,
        expected_n_embd=4,
        output_path=tmp_path / "out.json",
        run_id=plan.run_id,
        attempt_id=plan.attempt_id,
        session_id="session",
        runtime_receipt_file_sha256="b" * 64,
        runtime_receipt_document_sha256="c" * 64,
        session_receipt_file_sha256="d" * 64,
        decoding_params={"temperature": 0, "max_tokens": 1},
    )
    assert result["contact_class"] == "encoder" and len(transport.payloads) == 1
    assert transport.payloads[0]["media_relpath"] == rel


def test_identical_audio_in_distinct_batch_paths_uses_one_inventory_encoding_input(
    tmp_path, monkeypatch
):
    data, inv, audio = inventory(tmp_path)
    second = data / "slices" / "two.wav"
    second.write_bytes((data / "slices" / "one.wav").read_bytes())
    source = dict(inv["batches"][0]["requests"][0]["source_provenance"])
    source["media_relpath"] = "slices/two.wav"
    inv["batches"].append(
        {
            "name": "other",
            "requests": [{"request_key": "s#w2", "source_provenance": source}],
        }
    )
    inv["encoding_inputs"][0]["requests"].append(
        {"batch": "other", "request_key": "s#w2"}
    )
    client = Client()
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda **kwargs: type(
            "Inspection",
            (),
            {
                "audio_sha256": hashlib.sha256(
                    kwargs["audio_path"].read_bytes()
                ).hexdigest(),
                "cache_key": __import__(
                    "speech_aware_evidence_acquisition.core.preparation_encoding",
                    fromlist=["legacy_audio_feature_cache_key"],
                ).legacy_audio_feature_cache_key(kwargs["audio_path"].read_bytes()),
                "chunks": (),
            },
        )(),
    )
    encode_window_feature_cache(**kwargs(tmp_path, data, inv, client))
    assert len([call for call in client.calls if call[0] == "complete"]) == 1


def test_verified_warm_reuse_makes_zero_current_calls(tmp_path, monkeypatch):
    data, inv, audio = inventory(tmp_path)
    client = Client()
    args = kwargs(tmp_path, data, inv, client)
    key = __import__(
        "speech_aware_evidence_acquisition.core.preparation_encoding",
        fromlist=["legacy_audio_feature_cache_key"],
    ).legacy_audio_feature_cache_key((data / "slices/one.wav").read_bytes())
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda **kwargs: type(
            "Inspection", (), {"audio_sha256": audio, "cache_key": key, "chunks": ()}
        )(),
    )
    args["warm_provenance"] = {
        audio: {
            "audio_sha256": audio,
            "cache_key": key,
            "encoder_identity": {"build": "x"},
            "source_contact_id": "old-1",
            "source_provenance_receipt_sha256": "b" * 64,
        }
    }
    result = encode_window_feature_cache(**args)
    assert (
        client.calls == []
        and client.closed == 1
        and result["contact_class"] == "encoder"
    )


def test_custody_refusal_precedes_client_request(tmp_path, monkeypatch):
    data, inv, _ = inventory(tmp_path)
    client = Client()
    args = kwargs(tmp_path, data, inv, client)
    args["custody_guard"] = lambda: (_ for _ in ()).throw(
        PreparationError("custody refused")
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda **kwargs: type(
            "Inspection",
            (),
            {
                "audio_sha256": hashlib.sha256(
                    kwargs["audio_path"].read_bytes()
                ).hexdigest(),
                "cache_key": __import__(
                    "speech_aware_evidence_acquisition.core.preparation_encoding",
                    fromlist=["legacy_audio_feature_cache_key"],
                ).legacy_audio_feature_cache_key(kwargs["audio_path"].read_bytes()),
                "chunks": (),
            },
        )(),
    )
    with pytest.raises(PreparationError, match="custody"):
        encode_window_feature_cache(**args)
    assert client.calls == [] and client.closed == 1


def test_missing_or_wrong_shape_after_response_refuses_and_writes_partial(
    tmp_path, monkeypatch
):
    data, inv, _ = inventory(tmp_path)
    client = Client()
    args = kwargs(tmp_path, data, inv, client)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda **_: (_ for _ in ()).throw(PreparationError("wrong n_embd")),
    )
    with pytest.raises(PreparationError, match="wrong n_embd"):
        encode_window_feature_cache(**args)
    assert client.closed == 1 and (tmp_path / "result.json.partial.json").exists()


def test_warm_artifact_reuse_refuses_when_cache_disappears(tmp_path, monkeypatch):
    data, inv, _ = inventory(tmp_path)
    client = Client()
    args = kwargs(tmp_path, data, inv, client)
    key = __import__(
        "speech_aware_evidence_acquisition.core.preparation_encoding",
        fromlist=["legacy_audio_feature_cache_key"],
    ).legacy_audio_feature_cache_key((data / "slices/one.wav").read_bytes())
    (args["legacy_cache_dir"] / f"{key}_o0.feat").write_bytes(b"x")
    args["output_path"].write_text("{}")
    with pytest.raises(Exception, match="lacks feature output"):
        encode_window_feature_cache(**args)
    assert client.calls == []


def test_second_source_mutation_refuses_before_second_contact(tmp_path, monkeypatch):
    data, inv, first = inventory(tmp_path)
    second = data / "slices" / "two.wav"
    second.write_bytes(b"second source")
    second_sha = hashlib.sha256(second.read_bytes()).hexdigest()
    source = dict(inv["batches"][0]["requests"][0]["source_provenance"])
    source.update(
        {
            "media_relpath": "slices/two.wav",
            "sha256": second_sha,
            "bytes": second.stat().st_size,
            "iteration": 1,
        }
    )
    inv["batches"][0]["requests"].append(
        {"request_key": "s#w2", "source_provenance": source}
    )
    inv["encoding_inputs"].append(
        {
            "audio_sha256": second_sha,
            "requests": [{"batch": "batch", "request_key": "s#w2"}],
        }
    )

    class Mutating(Client):
        def complete(self, *args, **kwargs):
            value = super().complete(*args, **kwargs)
            if len(self.timings) == 1:
                second.write_bytes(b"changed after first")
            return value

        @property
        def last_attempted_request_id(self):
            return self.timings[-1].request_id if self.timings else None

    client = Mutating()
    args = kwargs(tmp_path, data, inv, client)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache",
        lambda **kwargs: type(
            "Inspection",
            (),
            {
                "audio_sha256": hashlib.sha256(
                    kwargs["audio_path"].read_bytes()
                ).hexdigest(),
                "cache_key": __import__(
                    "speech_aware_evidence_acquisition.core.preparation_encoding",
                    fromlist=["legacy_audio_feature_cache_key"],
                ).legacy_audio_feature_cache_key(kwargs["audio_path"].read_bytes()),
                "chunks": (),
            },
        )(),
    )
    with pytest.raises(PreparationError, match="changed after inventory"):
        encode_window_feature_cache(**args)
    assert len([call for call in client.calls if call[0] == "complete"]) == 1
    assert client.closed == 1 and (tmp_path / "result.json.partial.json").exists()


@pytest.mark.parametrize("mutate", [False, True])
def test_real_cache_artifact_reuse_closes_client_without_contact(tmp_path, mutate):
    import struct
    from speech_aware_evidence_acquisition.core.model import (
        legacy_audio_feature_cache_key,
    )

    data, inv, _ = inventory(tmp_path)
    key = legacy_audio_feature_cache_key((data / "slices/one.wav").read_bytes())
    args = kwargs(tmp_path, data, inv, Client())
    feature = args["legacy_cache_dir"] / f"{key}_o0.feat"

    class ProducingClient(Client):
        def complete(self, *positional, **named):
            result = super().complete(*positional, **named)
            feature.write_bytes(struct.pack("<QQ", 2, 4) + b"\x00" * 32)
            return result

    args["client"] = ProducingClient()
    encode_window_feature_cache(**args)
    original = args["output_path"].read_bytes()
    if mutate:
        feature.write_bytes(struct.pack("<QQ", 2, 4) + b"\x01" * 32)
    client = Client()
    args["client"] = client
    if mutate:
        with pytest.raises(PreparationError, match="descriptors changed"):
            encode_window_feature_cache(**args)
    else:
        assert encode_window_feature_cache(**args)["cache"] == "warm"
    assert client.calls == []
    assert client.closed == 1
    assert args["output_path"].read_bytes() == original


@pytest.mark.parametrize(
    "case",
    [
        "uncovered",
        "duplicate-request",
        "duplicate-reference",
        "wrong-source",
        "wrong-encoder",
    ],
)
def test_inventory_binding_refuses_before_any_encoder_contact(tmp_path, case):
    data, inv, _ = inventory(tmp_path)
    client = Client()
    args = kwargs(tmp_path, data, inv, client)
    request = inv["batches"][0]["requests"][0]
    reference = inv["encoding_inputs"][0]["requests"][0]
    if case == "uncovered":
        inv["batches"][0]["requests"].append({**request, "request_key": "s#w2"})
    elif case == "duplicate-request":
        inv["batches"][0]["requests"].append(dict(request))
    elif case == "duplicate-reference":
        inv["encoding_inputs"][0]["requests"].append(dict(reference))
    elif case == "wrong-source":
        reference["request_key"] = "other#w1"
    else:
        args["encoder_identity"] = {"build": "different"}
    with pytest.raises(PreparationError):
        encode_window_feature_cache(**args)
    assert client.calls == []
    assert not args["output_path"].exists()
