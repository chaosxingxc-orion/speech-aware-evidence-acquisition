"""``FrozenCoreClient`` (bridge mission, 2026-08-17): the REAL ``CoreClient``
delegating to ``core.model.FrozenCoreAdapter``. Engineering-only, ZERO live
model contact -- every test here uses a fake gate and a fake transport,
mirroring ``tests/unit/test_frozen_core_adapter.py``'s own
``_OpenGate``/``_fake_transport`` doubles.
"""

from __future__ import annotations

import hashlib
import json
import struct
import wave
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import (
    ExecutionPlan,
    ExecutionScopeError,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.core.model.slices import SliceRecord
from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreError,
    SpeechFeatureChunkData,
    materialize_speech_feature_packet,
)
from speech_aware_evidence_acquisition.rails import (
    DEFAULT_RAILS_ARM,
    AgentStateArtifact,
    AudioRef,
    FrozenCoreClient,
    FrozenCoreClientError,
    build_payload_binding,
    build_slice_registry,
)
from speech_aware_evidence_acquisition.rails.core_client import (
    _speech_supply_evidence_id,
)

_SHA_A = "a" * 64


class _OpenGate:
    """Mirrors tests/unit/test_frozen_core_adapter.py's own _OpenGate."""

    def __init__(self):
        self.checked_plans = []

    def assert_model_touch_allowed(self, plan):
        self.checked_plans.append(plan)


class _CapturingTransport:
    """A fake, in-process transport -- never opens a socket. Records every
    parsed request payload and returns a canned/responder-driven text."""

    def __init__(self, responder=None):
        self.calls: list[dict] = []
        self._responder = responder

    def __call__(self, request_bytes: bytes) -> bytes:
        assert isinstance(request_bytes, bytes)
        payload = json.loads(request_bytes.decode("utf-8"))
        self.calls.append(payload)
        text = self._responder(payload) if self._responder is not None else "ok"
        return json.dumps(
            {"text": text, "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
        ).encode("utf-8")


def _write_wav(
    path: Path, *, sample_rate_hz: int = 16000, seconds: float = 1.0
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = int(sample_rate_hz * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        handle.writeframes(b"\x00\x00" * n_frames)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class _FakeSample:
    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


class _World:
    # NX programme E1: the rows the fixture writes; a subclass may widen the roster.
    SAMPLE_SPECS = (("s1", 2.0), ("s2", 3.5))

    def __init__(
        self, tmp_path: Path, *, sample_rate_hz: int = 16000, data_root: Path | None = None
    ) -> None:
        self.data_root = data_root if data_root is not None else tmp_path / "data"
        self.carrier_root = self.data_root / "datasets" / "fake-carrier"
        self.media_dir = self.carrier_root / "media"
        self.run_dir = tmp_path / "run"
        self.samples: list[_FakeSample] = []
        for sample_id, seconds in self.SAMPLE_SPECS:
            relpath = f"datasets/fake-carrier/media/{sample_id}.wav"
            path = self.data_root / relpath
            _write_wav(path, sample_rate_hz=sample_rate_hz, seconds=seconds)
            self.samples.append(
                _FakeSample(
                    sample_id=sample_id,
                    audio_ref=AudioRef(
                        path=relpath, sha256=_sha256_file(path)
                    ).validate(),
                    audio_seconds=seconds,
                )
            )

    def media_relpath(self, sample_id: str) -> str:
        return next(s for s in self.samples if s.sample_id == sample_id).audio_ref.path


def _plan(**overrides) -> ExecutionPlan:
    values = dict(
        run_id="SAEA-E-TEST-frozen-core-client",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="fake-carrier",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash("f" * 64, "bare-core", _SHA_A),
        attempt_id="attempt-frozen-core-client-0001",
    )
    values.update(overrides)
    return ExecutionPlan(**values)


def _binding(world: _World):
    return build_payload_binding(
        carrier_lock_key="fake-carrier",
        samples=world.samples,
        data_root=world.data_root,
        carrier_root=world.carrier_root,
    )


def _client(
    world, tmp_path, *, gate=None, transport=None, plan=None, binding=None, **kwargs
) -> tuple[FrozenCoreClient, _OpenGate, _CapturingTransport]:
    gate = gate or _OpenGate()
    transport = transport or _CapturingTransport()
    client = FrozenCoreClient(
        plan=plan or _plan(),
        gate=gate,
        transport=transport,
        run_dir=world.run_dir,
        binding=binding if binding is not None else _binding(world),
        **kwargs,
    )
    return client, gate, transport


def _zero_supply_messages(media_relpath: str):
    return (
        {"role": "system", "content": "Transcribe the speech verbatim."},
        {
            "role": "user",
            "content": [{"type": "input_audio", "media_relpath": media_relpath}],
        },
    )


def _supplied_messages(media_relpath: str, *texts: str):
    content = [{"type": "text", "text": text} for text in texts]
    content.append({"type": "input_audio", "media_relpath": media_relpath})
    return (
        {"role": "system", "content": "Transcribe the speech verbatim."},
        {"role": "user", "content": content},
    )


def _speech_feature_world(world: _World, tmp_path: Path):
    feature_root = tmp_path / "features"
    packets = {}
    bindings = {}
    for sample in world.samples:
        packet = materialize_speech_feature_packet(
            feature_root=feature_root,
            packet_id=f"slurp/train/{sample.sample_id}",
            audio_sha256=sample.audio_ref.sha256,
            encoder_receipt_sha256="e" * 64,
            decoder_gguf_sha256="d" * 64,
            mmproj_sha256="f" * 64,
            position_mode="mrope_1d",
            causal_attention=True,
            chunks=(
                SpeechFeatureChunkData(
                    n_tokens=2,
                    n_pos=2,
                    n_embd=4,
                    feature_bytes=struct.pack("<8f", *range(8)),
                    position_bytes=struct.pack("<8i", 0, 1, 0, 1, 0, 1, 0, 1),
                ),
            ),
        )
        packets[sample.sample_id] = packet
        bindings[sample.sample_id] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }
    return feature_root, packets["s1"], bindings


def _speech_feature_messages(packet, *texts: str):
    content = [{"type": "text", "text": text} for text in texts]
    content.append(
        {
            "type": "input_speech_features",
            "speech_features": {
                "packet_id": packet.packet_id,
                "sha256": packet.packet_sha256,
                "role": "query",
            },
        }
    )
    return (
        {"role": "system", "content": "Choose exactly one opaque key id."},
        {"role": "user", "content": content},
    )


# ---------------------------------------------------------------------------
# build_payload_binding
# ---------------------------------------------------------------------------


def test_build_payload_binding_probes_real_sample_rate_from_the_wav_header(tmp_path):
    world = _World(tmp_path, sample_rate_hz=22050)
    binding = _binding(world)
    assert binding.sample_facts["s1"] == (2.0, 22050)
    assert binding.sample_facts["s2"] == (3.5, 22050)
    assert binding.media_relpaths["s1"] == "datasets/fake-carrier/media/s1.wav"
    assert binding.allowed_sample_ids == frozenset({"s1", "s2"})


def test_build_payload_binding_rejects_empty_samples(tmp_path):
    world = _World(tmp_path)
    with pytest.raises(FrozenCoreClientError, match="at least one sample"):
        build_payload_binding(
            carrier_lock_key="fake-carrier",
            samples=(),
            data_root=world.data_root,
            carrier_root=world.carrier_root,
        )


def test_build_payload_binding_rejects_duplicate_sample_ids(tmp_path):
    world = _World(tmp_path)
    with pytest.raises(FrozenCoreClientError, match="duplicate sample_id"):
        build_payload_binding(
            carrier_lock_key="fake-carrier",
            samples=world.samples + [world.samples[0]],
            data_root=world.data_root,
            carrier_root=world.carrier_root,
        )


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------


def test_construction_checks_the_gate_exactly_once(tmp_path):
    world = _World(tmp_path)
    _, gate, _ = _client(world, tmp_path)
    assert len(gate.checked_plans) == 1


def test_construction_rejects_a_paper_scale_profile(tmp_path):
    world = _World(tmp_path)
    with pytest.raises(ExecutionScopeError, match="paper-scale"):
        _client(
            world, tmp_path, plan=_plan(execution_profile="paper-scale-confirmatory")
        )


def test_construction_rejects_an_arm_with_a_different_field_set(tmp_path):
    # The exemplar was "bare-core" until 2026-09-04, when this bridge learned
    # the evidence-FREE field sets it needs for the direct-baseline
    # calibration's two raw-audio cells (see
    # tests/unit/test_rails_core_client_native_tools.py's own zero-supply
    # section). The assertion itself is unchanged -- an arm whose payload
    # this bridge does not build is still refused at construction -- so the
    # example simply moves to an arm that genuinely remains unsupported.
    world = _World(tmp_path)
    with pytest.raises(FrozenCoreClientError, match="different field set"):
        _client(world, tmp_path, arm="fixed-retrieval")


def test_construction_rejects_an_unknown_arm(tmp_path):
    world = _World(tmp_path)
    with pytest.raises(FrozenCoreClientError, match="unknown D2 arm"):
        _client(world, tmp_path, arm="not-a-real-arm")


def test_default_arm_is_fixed_legal_context(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    assert client.arm == DEFAULT_RAILS_ARM == "fixed-legal-context"


def test_speech_feature_arm_builds_audited_packet_payload_on_existing_adapter(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    messages = (
        {"role": "system", "content": "Choose exactly one opaque key id."},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "key-001: turn a light on",
                    "evidence_id": "key:facet:K001",
                    "source_uri": "knowledge-snapshot://snapshot/facet:K001",
                    "knowledge_role": "key",
                },
                {
                    "type": "input_speech_features",
                    "speech_features": {
                        "packet_id": packet.packet_id,
                        "sha256": packet.packet_sha256,
                        "role": "query",
                    },
                },
            ],
        },
    )
    text = client.complete(
        messages,
        speech_feature_sample_id="s1",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="m1-listwise-v1",
    )
    assert text == "ok"
    payload = transport.calls[0]
    assert payload["speech_feature_parts"] == [
        {"packet_id": packet.packet_id, "sha256": packet.packet_sha256, "role": "query"}
    ]
    assert payload["query_source"] == "speech_features"
    assert payload["key_representation_id"] == "k1-text-card-v1"
    assert payload["matcher_policy_id"] == "m1-listwise-v1"
    assert payload["mmproj_loaded"] is False
    assert payload["media_relpath"] == world.media_relpath("s1")
    assert payload["supplied_evidence"][0]["knowledge_role"] == "key"


def test_prevalidated_packet_set_skips_constructor_scan(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.rails import core_client

    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    prepared = core_client.validate_speech_packet_set(
        feature_root, bindings, _binding(world)
    )
    monkeypatch.setattr(
        core_client, "load_speech_feature_packets",
        lambda *args, **kwargs: pytest.fail("constructor revalidated prepared packet set"),
    )
    client, _gate, _transport = _client(
        world, tmp_path, arm="speech-feature-query",
        speech_feature_root=feature_root, speech_packet_bindings=bindings,
        validated_packet_set=prepared,
    )
    assert client.arm == "speech-feature-query"
    assert not prepared.matches(
        feature_root, {"s1": bindings["s1"]}, _binding(world)
    )


def test_prevalidated_packet_set_rejects_a_different_audio_root(tmp_path):
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    from speech_aware_evidence_acquisition.rails import core_client

    prepared = core_client.validate_speech_packet_set(feature_root, bindings, _binding(world))
    other_root = tmp_path / "other-audio-root"
    other_root.mkdir()
    assert not prepared.matches(feature_root, bindings, replace(_binding(world), data_root=other_root))


def test_prevalidated_packet_set_rejects_unsupported_arm(tmp_path):
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    from speech_aware_evidence_acquisition.rails import core_client

    prepared = core_client.validate_speech_packet_set(feature_root, bindings, _binding(world))
    with pytest.raises(FrozenCoreClientError, match="only valid"):
        _client(world, tmp_path, validated_packet_set=prepared)


def test_prevalidated_packet_set_rejects_mismatched_bindings(tmp_path):
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    from speech_aware_evidence_acquisition.rails import core_client

    prepared = core_client.validate_speech_packet_set(
        feature_root, bindings, _binding(world)
    )
    mismatched = dict(bindings)
    mismatched["s1"] = {"packet_id": bindings["s1"]["packet_id"], "sha256": "0" * 64}
    with pytest.raises(FrozenCoreClientError, match="does not match"):
        _client(
            world,
            tmp_path,
            arm="speech-feature-query",
            speech_feature_root=feature_root,
            speech_packet_bindings=mismatched,
            validated_packet_set=prepared,
        )


def test_prevalidated_packet_set_keeps_request_time_packet_validation(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    from speech_aware_evidence_acquisition.rails import core_client

    prepared = core_client.validate_speech_packet_set(
        feature_root, bindings, _binding(world)
    )
    client, _gate, _transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
        validated_packet_set=prepared,
    )
    feature_path = feature_root / packet.packet_id / packet.chunks[0].feature_relpath
    feature_path.write_bytes(b"modified-after-preprocess")

    with pytest.raises(FrozenCoreError, match="feature bytes"):
        client.complete(
            _speech_feature_messages(packet, "Stable opaque key catalog."),
            speech_feature_sample_id="s1",
            key_representation_id="k1-text-card-v1",
            matcher_policy_id="m1-listwise-v1",
        )


def test_speech_feature_arm_uses_content_stable_evidence_ids_for_prefix_reuse(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )

    for instruction in ("Choose one key.", "Verify the selected key."):
        client.complete(
            _speech_feature_messages(packet, "Stable opaque key catalog.", instruction),
            speech_feature_sample_id="s1",
            key_representation_id="k1-text-card-v1",
            matcher_policy_id="m11-agent-loop-v1",
        )

    first, second = transport.calls
    assert first["request_id"] != second["request_id"]
    assert (
        first["supplied_evidence"][0]["evidence_id"]
        == second["supplied_evidence"][0]["evidence_id"]
    )
    assert (
        first["supplied_evidence"][1]["evidence_id"]
        != second["supplied_evidence"][1]["evidence_id"]
    )
    assert first["supplied_evidence"][0]["evidence_id"].startswith("speech-supply-00-")


def test_speech_feature_arm_traces_agent_state_and_control_separately_from_supply(
    tmp_path,
):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    messages = _speech_feature_messages(packet)
    messages[1]["content"].insert(
        0,
        {
            "type": "text",
            "text": "Use the dim-light operation.",
            "evidence_id": "value:dim-light",
            "source_uri": "knowledge-snapshot://abc/value:dim-light",
        },
    )
    state = AgentStateArtifact(
        state_id="state:operation-needed",
        state_kind="intent-factor",
        content="The unresolved factor is the requested operation.",
        source_query_state_sha256="1" * 64,
        source_response_sha256="2" * 64,
        producer_policy_id="organize-v1",
        cited_value_ids=(),
    )

    client.complete(
        messages,
        speech_feature_sample_id="s1",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="agent-loop-v1",
        agent_state=(state.as_json(),),
        agent_contact_id="contact-2",
        contact_instruction="Solve the task using speech and visible evidence.",
    )

    payload = transport.calls[0]
    assert payload["supplied_evidence"] == [
        {
            "evidence_id": "value:dim-light",
            "source_uri": "knowledge-snapshot://abc/value:dim-light",
            "content": "Use the dim-light operation.",
        }
    ]
    assert [item["role"] for item in payload["history"]] == [
        "agent_state",
        "control",
    ]
    assert payload["history"][0]["state_id"] == "state:operation-needed"
    assert payload["history"][1]["content"] == (
        "Solve the task using speech and visible evidence."
    )


def test_speech_feature_arm_normalizes_malformed_agent_state_to_client_error(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, _ = _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    malformed = {
        "state_id": "state:bad",
        "state_kind": "intent-factor",
        "content": "Malformed source binding.",
        "source_query_state_sha256": "not-a-hash",
        "source_response_sha256": "2" * 64,
        "producer_policy_id": "organize-v1",
        "cited_value_ids": [],
    }

    with pytest.raises(FrozenCoreClientError, match="malformed Agent state"):
        client.complete(
            _speech_feature_messages(packet),
            speech_feature_sample_id="s1",
            key_representation_id="k1-text-card-v1",
            matcher_policy_id="agent-loop-v1",
            agent_state=(malformed,),
            agent_contact_id="contact-1",
            contact_instruction="Organize the evidence.",
        )


@pytest.mark.parametrize(
    ("index", "text"),
    ((-1, "valid"), (True, "valid"), (0, ""), (0, None)),
)
def test_speech_supply_evidence_id_rejects_unstable_inputs(index, text):
    with pytest.raises(FrozenCoreClientError, match="speech supply"):
        _speech_supply_evidence_id(index, text)


def test_speech_feature_construction_uses_one_bounded_batch_validation(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.rails import core_client as client_module

    world = _World(tmp_path)
    feature_root, _, bindings = _speech_feature_world(world, tmp_path)
    original = client_module.load_speech_feature_packets
    calls = []

    def tracked_loader(root, descriptors, **kwargs):
        calls.append((root, tuple(descriptors), kwargs))
        return original(root, descriptors, **kwargs)

    monkeypatch.setattr(client_module, "load_speech_feature_packets", tracked_loader)
    _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )

    assert len(calls) == 1
    assert calls[0][0] == feature_root.resolve()
    assert calls[0][2]["workers"] == 8
    assert [descriptor["packet_id"] for descriptor in calls[0][1]] == [
        bindings[sample_id]["packet_id"] for sample_id in sorted(bindings)
    ]


def test_speech_feature_arm_refuses_raw_audio_or_unbound_query_packet(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, _ = _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    with pytest.raises(FrozenCoreClientError, match="must not carry input_audio"):
        client.complete(
            _zero_supply_messages(world.media_relpath("s1")),
            speech_feature_sample_id="s1",
            key_representation_id="k1",
            matcher_policy_id="m1",
        )
    forged = _speech_feature_messages(packet)
    forged[1]["content"][0]["speech_features"]["packet_id"] = "slurp/train/other"
    with pytest.raises(FrozenCoreClientError, match="bound packet"):
        client.complete(
            forged,
            speech_feature_sample_id="s1",
            key_representation_id="k1",
            matcher_policy_id="m1",
        )


def test_speech_feature_arm_requires_packet_on_every_decision_call(tmp_path):
    world = _World(tmp_path)
    feature_root, _, bindings = _speech_feature_world(world, tmp_path)
    client, _, _ = _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    messages = (
        {"role": "system", "content": "Choose one key."},
        {"role": "user", "content": [{"type": "text", "text": "key-001"}]},
    )
    with pytest.raises(FrozenCoreClientError, match="exactly one query packet"):
        client.complete(
            messages,
            speech_feature_sample_id="s1",
            key_representation_id="k1",
            matcher_policy_id="m2-step-2",
        )


# ---------------------------------------------------------------------------
# complete() -- zero-supply
# ---------------------------------------------------------------------------


def test_complete_zero_supply_sends_the_full_d2_field_set_and_returns_text(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(world, tmp_path)

    text = client.complete(_zero_supply_messages(world.media_relpath("s1")))

    assert text == "ok"
    assert len(transport.calls) == 1
    payload = transport.calls[0]
    assert set(payload) == {
        "request_id",
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
        "task_instruction",
        "history",
        "decoding_params",
        "supplied_evidence",
        "evidence_provenance",
    }
    assert payload["sample_id"] == "s1"
    assert payload["carrier_lock_key"] == "fake-carrier"
    assert payload["speech_ref"] == "fake-carrier/s1"
    assert payload["media_relpath"] == world.media_relpath("s1")
    assert payload["audio_seconds"] == 2.0
    assert payload["sample_rate_hz"] == 16000
    assert payload["task_instruction"] == "Transcribe the speech verbatim."
    assert payload["history"] == []
    assert payload["decoding_params"] == {}
    assert payload["supplied_evidence"] == []
    assert payload["evidence_provenance"] == []


def test_complete_forwards_decoding_params(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(world, tmp_path)
    client.complete(
        _zero_supply_messages(world.media_relpath("s1")),
        decoding_params={"temperature": 0, "seed": 1},
    )
    assert transport.calls[0]["decoding_params"] == {"temperature": 0, "seed": 1}


def test_complete_request_ids_are_distinct_and_incrementing(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(world, tmp_path)
    client.complete(_zero_supply_messages(world.media_relpath("s1")))
    client.complete(_zero_supply_messages(world.media_relpath("s2")))
    assert transport.calls[0]["request_id"] == "rails-0001"
    assert transport.calls[1]["request_id"] == "rails-0002"


# ---------------------------------------------------------------------------
# complete() -- supplied arm
# ---------------------------------------------------------------------------


def test_complete_supplied_builds_one_evidence_item_per_text_part(tmp_path):
    world = _World(tmp_path)

    def responder(payload):
        return f"saw {len(payload['supplied_evidence'])} evidence items"

    client, _, transport = _client(
        world, tmp_path, transport=_CapturingTransport(responder)
    )
    text = client.complete(
        _supplied_messages(
            world.media_relpath("s1"), "roster: kitchen", "roster: email"
        )
    )

    assert text == "saw 2 evidence items"
    payload = transport.calls[0]
    assert [item["content"] for item in payload["supplied_evidence"]] == [
        "roster: kitchen",
        "roster: email",
    ]
    assert len({item["evidence_id"] for item in payload["supplied_evidence"]}) == 2
    assert len(payload["evidence_provenance"]) == 2
    for provenance in payload["evidence_provenance"]:
        assert set(provenance) == {"lock_key", "relpath", "sha256"}


# ---------------------------------------------------------------------------
# complete() -- malformed messages / unresolved media
# ---------------------------------------------------------------------------


def test_complete_rejects_the_wrong_number_of_messages(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="exactly 2 messages"):
        client.complete(({"role": "system", "content": "x"},))


def test_complete_rejects_a_missing_input_audio_part(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="exactly one input_audio"):
        client.complete(
            (
                {"role": "system", "content": "x"},
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "no audio here"}],
                },
            )
        )


def test_complete_rejects_more_than_one_input_audio_part(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    relpath = world.media_relpath("s1")
    with pytest.raises(FrozenCoreClientError, match="more than one input_audio"):
        client.complete(
            (
                {"role": "system", "content": "x"},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "media_relpath": relpath},
                        {"type": "input_audio", "media_relpath": relpath},
                    ],
                },
            )
        )


def test_complete_rejects_an_unknown_content_part_type(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="unsupported content part type"):
        client.complete(
            (
                {"role": "system", "content": "x"},
                {"role": "user", "content": [{"type": "logit_bias", "value": 1}]},
            )
        )


def test_complete_rejects_an_unresolvable_media_relpath(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="not bound to any sample"):
        client.complete(
            _zero_supply_messages("datasets/fake-carrier/media/unknown.wav")
        )


# ---------------------------------------------------------------------------
# complete() -- text-only mode (P-KEY machinery, 2026-08-19 amendment).
#
# THE TEST LESSON (recurring, now twice in this program): these tests drive
# FrozenCoreClient.complete() -- the REAL client's own validation layer --
# never MockCoreClient, which validates nothing and could not have caught the
# attempt-1 abort in the first place (docs/readiness/2026-08-18-pkey-
# preregistration-REGISTERED.md section 7's own attempt-1 accounting).
# ---------------------------------------------------------------------------


def _text_only_messages(*texts: str):
    content = [{"type": "text", "text": text} for text in texts]
    return (
        {"role": "system", "content": "Answer using only the text below."},
        {"role": "user", "content": content},
    )


def test_complete_text_only_sample_id_sends_the_bound_samples_own_media_facts(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(world, tmp_path)

    text = client.complete(
        _text_only_messages("The user said: turn on the kitchen light"),
        text_only_sample_id="s1",
    )

    assert text == "ok"
    assert len(transport.calls) == 1
    payload = transport.calls[0]
    # SAME full D2 field set an audio request sends -- text-only mode changes
    # nothing about the payload SHAPE, only how it is resolved.
    assert set(payload) == {
        "request_id",
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
        "task_instruction",
        "history",
        "decoding_params",
        "supplied_evidence",
        "evidence_provenance",
    }
    assert payload["sample_id"] == "s1"
    assert payload["media_relpath"] == world.media_relpath("s1")
    assert payload["audio_seconds"] == 2.0
    assert payload["sample_rate_hz"] == 16000
    assert [item["content"] for item in payload["supplied_evidence"]] == [
        "The user said: turn on the kitchen light",
    ]


def test_complete_text_only_sample_id_rejects_a_message_carrying_audio(tmp_path):
    """A registered text-only arm is audio-free BY CONSTRUCTION
    (rails.probes.pkey_flight.assemble_txt_messages's own invariant) -- a
    caller naming text_only_sample_id on a message that still carries an
    input_audio part is refused, never silently accepted."""

    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    with pytest.raises(
        FrozenCoreClientError, match="must not carry an input_audio content part"
    ):
        client.complete(
            _supplied_messages(world.media_relpath("s1"), "some text"),
            text_only_sample_id="s1",
        )


def test_complete_text_only_sample_id_rejects_an_unknown_sample(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="not bound to any sample"):
        client.complete(
            _text_only_messages("hello"), text_only_sample_id="not-a-real-sample"
        )


def test_complete_text_only_sample_id_rejects_an_empty_string(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="non-empty string"):
        client.complete(_text_only_messages("hello"), text_only_sample_id="")


def test_complete_default_mode_still_refuses_zero_audio_parts_when_text_only_is_not_named(
    tmp_path,
):
    """The DEFAULT AUDIO invariant is untouched: a caller that never opts
    into text_only_sample_id still gets the pre-2026-08-19 refusal -- this is
    exactly the invariant the attempt-1 abort's own error message quoted."""

    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="exactly one input_audio"):
        client.complete(_text_only_messages("The user said: hello"))


def test_complete_default_mode_still_refuses_two_audio_parts(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    relpath = world.media_relpath("s1")
    with pytest.raises(FrozenCoreClientError, match="more than one input_audio"):
        client.complete(
            (
                {"role": "system", "content": "x"},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "media_relpath": relpath},
                        {"type": "input_audio", "media_relpath": relpath},
                    ],
                },
            ),
            text_only_sample_id=None,
        )


def test_complete_text_only_mode_produces_a_distinct_request_id_sequence_alongside_audio_calls(
    tmp_path,
):
    """text-only and audio requests share the SAME request_id counter/
    transport path -- no parallel accounting."""

    world = _World(tmp_path)
    client, _, transport = _client(world, tmp_path)
    client.complete(_zero_supply_messages(world.media_relpath("s1")))
    client.complete(_text_only_messages("The user said: hi"), text_only_sample_id="s2")
    assert transport.calls[0]["request_id"] == "rails-0001"
    assert transport.calls[1]["request_id"] == "rails-0002"
    assert transport.calls[1]["sample_id"] == "s2"


# ---------------------------------------------------------------------------
# flight lock (advisory, threaded through)
# ---------------------------------------------------------------------------


def test_flight_lock_is_none_when_absent(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    assert client.flight_lock is None


def test_flight_lock_is_threaded_through_when_present(tmp_path):
    world = _World(tmp_path)
    lock_path = world.data_root / "locks" / "flight.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps({"study_head": "deadbeef", "pid": 123}), encoding="utf-8"
    )
    client, _, _ = _client(world, tmp_path)
    assert client.flight_lock == {"study_head": "deadbeef", "pid": 123}


# ---------------------------------------------------------------------------
# close() / lifecycle
# ---------------------------------------------------------------------------


def test_close_returns_manifest_hash_cost_and_timings(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    client.complete(_zero_supply_messages(world.media_relpath("s1")))

    summary = client.close()

    assert summary["run_id"] == "SAEA-E-TEST-frozen-core-client"
    assert summary["arm"] == "fixed-legal-context"
    assert (
        isinstance(summary["trace_manifest_hash"], str)
        and summary["trace_manifest_hash"]
    )
    assert summary["cost"]["calls_used"] == 1
    assert summary["request_count"] == 1
    assert len(summary["timings"]) == 1
    timing = summary["timings"][0]
    assert timing["request_id"] == "rails-0001"
    assert timing["sample_id"] == "s1"
    assert timing["latency_seconds"] >= 0.0
    assert client.timings[0].sample_id == "s1"


def test_close_twice_raises(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    client.close()
    with pytest.raises(FrozenCoreClientError, match="close\\(\\) called twice"):
        client.close()


def test_complete_after_close_raises(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    client.close()
    with pytest.raises(FrozenCoreClientError, match="after close"):
        client.complete(_zero_supply_messages(world.media_relpath("s1")))


# ---------------------------------------------------------------------------
# register_slice -- silence-swap-style runtime-derived media
# ---------------------------------------------------------------------------


def test_register_slice_resolves_a_derived_media_relpath_to_its_parent_sample(tmp_path):
    world = _World(tmp_path)
    plan = _plan()
    registry = build_slice_registry(
        data_root=world.data_root, run_id=plan.run_id, samples=world.samples
    )
    client, _, transport = _client(world, tmp_path, plan=plan, slice_registry=registry)

    parent_relpath = world.media_relpath("s1")
    parent_sha256 = _sha256_file(world.data_root / parent_relpath)
    slice_relpath = registry.slice_relpath("s1", 0)
    slice_path = world.data_root / slice_relpath
    # A duration DIFFERENT from the parent (2.0s) -- proves complete() reads
    # the SLICE's own facts, not the parent's, once registered.
    _write_wav(slice_path, sample_rate_hz=8000, seconds=1.25)
    record = SliceRecord(
        sample_id="s1",
        parent_media_relpath=parent_relpath,
        parent_sha256=parent_sha256,
        start_seconds=0.0,
        end_seconds=1.25,
        audio_seconds=1.25,
        sample_rate_hz=8000,
        media_relpath=slice_relpath,
        sha256=_sha256_file(slice_path),
        bytes=slice_path.stat().st_size,
        iteration=0,
    )

    client.register_slice(record)
    client.complete(_zero_supply_messages(slice_relpath))

    payload = transport.calls[0]
    assert payload["sample_id"] == "s1"
    assert payload["media_relpath"] == slice_relpath
    assert payload["audio_seconds"] == 1.25
    assert payload["sample_rate_hz"] == 8000


def test_register_slice_without_a_registry_raises(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path)
    record = SliceRecord(
        sample_id="s1",
        parent_media_relpath=world.media_relpath("s1"),
        parent_sha256="a" * 64,
        start_seconds=0.0,
        end_seconds=1.0,
        audio_seconds=1.0,
        sample_rate_hz=16000,
        media_relpath="derived/obs-slices/x/s1/i0000.wav",
        sha256="b" * 64,
        bytes=1,
        iteration=0,
    )
    with pytest.raises(FrozenCoreClientError, match="slice_registry"):
        client.register_slice(record)

def test_last_attempted_request_id_is_set_before_transport_and_is_not_a_timing(tmp_path):
    world = _World(tmp_path)
    def fail(_payload):
        raise RuntimeError("synthetic transport failure")
    client, _, _ = _client(world, tmp_path, transport=_CapturingTransport(responder=fail))
    assert client.last_attempted_request_id is None
    with pytest.raises(RuntimeError, match="synthetic"):
        client.complete(_zero_supply_messages(world.media_relpath("s1")))
    assert client.last_attempted_request_id == "rails-0001"
    assert client.timings == ()


@pytest.mark.parametrize("supplied", [False, True])
def test_prepared_requests_preserve_legacy_wire_without_preparation_contacts(tmp_path, supplied):
    legacy_world = _World(tmp_path / "legacy")
    prepared_world = _World(tmp_path / "prepared")
    legacy, _, legacy_transport = _client(legacy_world, tmp_path / "legacy")
    prepared_client, gate, prepared_transport = _client(prepared_world, tmp_path / "prepared")
    messages = (
        _supplied_messages(legacy_world.media_relpath("s1"), "Frozen example")
        if supplied else _zero_supply_messages(legacy_world.media_relpath("s1"))
    )
    checked_before = len(gate.checked_plans)
    if supplied:
        with pytest.raises(FrozenCoreClientError, match="raw supplied evidence"):
            prepared_client.prepare_request(messages, decoding_params={"max_tokens": 64})
        assert not prepared_transport.calls
        assert prepared_client._request_counter == 0
        legacy.close()
        prepared_client.close()
        return
    request = prepared_client.prepare_request(messages, decoding_params={"max_tokens": 64})
    assert not prepared_transport.calls
    assert prepared_client._request_counter == 0
    assert len(gate.checked_plans) == checked_before
    assert not prepared_client._timings
    legacy.complete(messages, decoding_params={"max_tokens": 64, "id_slot": 1})
    prepared_client.complete_prepared(request, id_slot=1)
    assert prepared_transport.calls == legacy_transport.calls
    with pytest.raises(FrozenCoreClientError, match="consumed"):
        prepared_client.complete_prepared(request, id_slot=1)
    assert len(prepared_transport.calls) == 1
    legacy.close()
    prepared_client.close()


def test_prepared_request_cannot_change_content_or_cross_clients(tmp_path):
    world = _World(tmp_path / "one")
    client, _, transport = _client(world, tmp_path / "one")
    other_world = _World(tmp_path / "two")
    other, _, other_transport = _client(other_world, tmp_path / "two")
    request = client.prepare_request(_zero_supply_messages(world.media_relpath("s1")))
    changed = replace(request, payload_bytes=request.payload_bytes.replace(b"verbatim", b"changed"))
    with pytest.raises(FrozenCoreClientError, match="changed"):
        client.complete_prepared(changed)
    with pytest.raises(FrozenCoreClientError, match="foreign"):
        other.complete_prepared(request)
    copy = request.as_payload()
    copy["task_instruction"] = "Changed independent copy"
    client.complete_prepared(request)
    assert "verbatim" in transport.calls[0]["task_instruction"]
    assert not other_transport.calls
    client.close()
    other.close()


def test_failed_prepared_send_cannot_repeat_and_close_discards_unused_templates(tmp_path):
    world = _World(tmp_path)
    def fail(_):
        raise RuntimeError("synthetic transport failure")
    client, _, transport = _client(world, tmp_path, transport=_CapturingTransport(fail))
    request = client.prepare_request(_zero_supply_messages(world.media_relpath("s1")))
    with pytest.raises(Exception, match="synthetic transport failure"):
        client.complete_prepared(request)
    with pytest.raises(FrozenCoreClientError, match="consumed"):
        client.complete_prepared(request)
    assert len(transport.calls) == 1
    unused = client.prepare_request(_zero_supply_messages(world.media_relpath("s2")))
    client.close()
    assert not client._prepared_requests
    with pytest.raises(FrozenCoreClientError, match="after close"):
        client.complete_prepared(unused)


class _CompletionMetadataTransport:
    """Return source-specific native provenance through the real adapter."""

    def __init__(self, tool_calls, *, barrier=None):
        self.calls = []
        self.tool_calls = tool_calls
        self.barrier = barrier

    def __call__(self, request_bytes):
        payload = json.loads(request_bytes)
        self.calls.append(payload)
        if self.barrier is not None:
            self.barrier.wait(timeout=10)
        return json.dumps({
            "text": "answer-" + payload["sample_id"],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            "tool_calls": self.tool_calls,
        }).encode()


@pytest.mark.parametrize("prepared", [False, True])
@pytest.mark.parametrize("tool_calls", [
    None,
    [],
    [{"id": "native-call-1", "type": "function",
      "function": {"name": "observe_speech", "arguments": "{malformed-json"}}],
])
def test_completion_metadata_preserves_native_provenance_and_legacy_wire(
    tmp_path, prepared, tool_calls,
):
    world = _World(tmp_path / "metadata")
    old_world = _World(tmp_path / "legacy")
    transport = _CompletionMetadataTransport(tool_calls)
    old_transport = _CompletionMetadataTransport(tool_calls)
    client, _, _ = _client(world, tmp_path / "metadata", transport=transport)
    old_client, _, _ = _client(old_world, tmp_path / "legacy", transport=old_transport)
    messages = _zero_supply_messages(world.media_relpath("s1"))
    if prepared:
        request = client.prepare_request(messages, decoding_params={"max_tokens": 256})
        assert transport.calls == []
        reply = client.complete_prepared_with_metadata(request, id_slot=1)
        with pytest.raises(FrozenCoreClientError, match="consumed"):
            client.complete_prepared_with_metadata(request, id_slot=1)
    else:
        reply = client.complete_with_metadata(
            messages, decoding_params={"max_tokens": 256, "id_slot": 1},
        )
    text = old_client.complete(
        messages, decoding_params={"max_tokens": 256, "id_slot": 1},
    )
    assert transport.calls == old_transport.calls
    assert reply.text == text == "answer-s1"
    assert reply.request_id == "rails-0001"
    assert reply.sample_id == "s1"
    assert reply.agent_contact_id is None
    assert reply.tool_calls == tool_calls
    assert reply.request_sha256 == client.timings[0].request_sha256
    assert reply.response_sha256 == client.timings[0].response_sha256
    assert reply.response_text_sha256 == hashlib.sha256(text.encode()).hexdigest()
    reply.assert_binding(sample_id="s1", agent_contact_id=None, response_text=text)
    for wrong in [
        {"sample_id": "s2", "agent_contact_id": None, "response_text": text},
        {"sample_id": "s1", "agent_contact_id": "foreign", "response_text": text},
        {"sample_id": "s1", "agent_contact_id": None, "response_text": text + "x"},
    ]:
        with pytest.raises(FrozenCoreClientError, match="completion binding"):
            reply.assert_binding(**wrong)
    if tool_calls:
        mutable_copy = reply.tool_calls
        mutable_copy[0]["function"]["arguments"] = "{}"
        assert reply.tool_calls == tool_calls
    client.close()
    old_client.close()


def test_completion_metadata_is_local_to_each_concurrent_response(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    world = _World(tmp_path)
    transport = _CompletionMetadataTransport(None, barrier=Barrier(2))
    client, _, _ = _client(world, tmp_path, transport=transport)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(
            lambda sample: client.complete_with_metadata(
                _zero_supply_messages(world.media_relpath(sample)),
            ),
            ("s1", "s2"),
        ))
    assert [reply.sample_id for reply in replies] == ["s1", "s2"]
    assert [reply.text for reply in replies] == ["answer-s1", "answer-s2"]
    assert len({reply.request_id for reply in replies}) == 2
    assert len({reply.request_sha256 for reply in replies}) == 2
    for reply in replies:
        reply.assert_binding(
            sample_id=reply.sample_id, agent_contact_id=None, response_text=reply.text,
        )
    client.close()


@pytest.mark.parametrize("prepared", [False, True])
def test_completion_metadata_binds_actual_native_speech_contact(tmp_path, prepared):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    native_calls = [{
        "id": "call-observe-1", "type": "function",
        "function": {"name": "observe_speech", "arguments": '{"mode":"asr-transcript"}'},
    }]
    transport = _CompletionMetadataTransport(native_calls)
    client, _, _ = _client(
        world, tmp_path, transport=transport,
        arm="speech-feature-query-native-tools",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
        tool_schemas=[{
            "type": "function",
            "function": {
                "name": "observe_speech",
                "description": "Decode the current speech on demand.",
                "parameters": {"type": "object", "properties": {
                    "mode": {"type": "string", "enum": ["asr-transcript"]},
                }},
            },
        }],
    )
    arguments = {
        "speech_feature_sample_id": "s1",
        "key_representation_id": "speech-key",
        "matcher_policy_id": "native-agent",
        "agent_state": (),
        "agent_contact_id": "decision-1",
        "contact_instruction": "Answer or request needed evidence.",
    }
    if prepared:
        request = client.prepare_request(_speech_feature_messages(packet), **arguments)
        reply = client.complete_prepared_with_metadata(request, id_slot=0)
    else:
        reply = client.complete_with_metadata(_speech_feature_messages(packet), **arguments)
    reply.assert_binding(
        sample_id="s1", agent_contact_id="decision-1", response_text="answer-s1",
    )
    assert reply.tool_calls == native_calls
    assert reply.tool_calls_sha256 == hashlib.sha256(reply.tool_calls_json).hexdigest()
    assert transport.calls[0]["history"][-1]["contact_id"] == "decision-1"
    client.close()


def test_registered_tool_invocation_uses_shared_counter_without_model_debit(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(world, tmp_path)
    client.record_tool_call()
    client.record_tool_call(2)
    assert transport.calls == []
    summary = client.close()
    assert summary["cost"]["tool_calls"] == 3
    assert summary["cost"]["calls_used"] == 0
    assert summary["cost"]["audio_seconds_used"] == 0
    with pytest.raises(FrozenCoreClientError, match="after close"):
        client.record_tool_call()
