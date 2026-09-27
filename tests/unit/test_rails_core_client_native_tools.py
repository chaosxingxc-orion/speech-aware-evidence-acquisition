"""``FrozenCoreClient`` native tool-calling support (slice D1b, 2026-09-03):
extends the bridge (``rails.core_client.FrozenCoreClient``, tested in
``tests/unit/test_rails_frozen_core_client.py``) to accept the two D2
field-set patterns that add ``"tool_schemas"`` -- the raw-audio
(``_SUPPORTED_ARM_FIELDS``-shaped) pattern and the packet
(``_SPEECH_FEATURE_ARM_FIELDS``-shaped) pattern, "for BOTH audio paths"
(``rails.core_client``'s own module comment on ``_ACCEPTED_ARM_FIELD_SETS``).

Only ``"speech-feature-query-native-tools"`` is a real, D2-registered arm as
of this slice (``e0.d2_leakage.ARM_VISIBLE_FIELDS`` -- this repository adds
exactly ONE new arm key this slice, that module's own hard rule). The
raw-audio pattern's acceptance is exercised here via a test-LOCAL
``monkeypatch`` of ``ARM_VISIBLE_FIELDS`` (reverted automatically by pytest
at the end of each test) rather than a second real D2 arm registration, so
the client's generic "either audio path" field-set match is proven end to
end without touching the real D2 registry a second time.

Engineering-only, ZERO live model contact -- every test here uses a fake
gate and a fake transport, mirroring ``tests/unit/test_frozen_core_adapter.py``'s
own ``_OpenGate``/``_fake_transport`` doubles (and this module's own sibling,
``test_rails_frozen_core_client.py``). Fixtures are duplicated rather than
imported from that sibling file so the two test files never have to change
in lockstep.
"""

from __future__ import annotations

import hashlib
import json
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.core.model import (
    SpeechFeatureChunkData,
    materialize_speech_feature_packet,
)
from speech_aware_evidence_acquisition.data.audio2tool_tools import openai_tools_sha256
from speech_aware_evidence_acquisition.e0 import d2_leakage
from speech_aware_evidence_acquisition.rails import (
    AudioRef,
    FrozenCoreClient,
    FrozenCoreClientError,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.core_client import (
    _NATIVE_TOOLS_FIELD,
    _tool_schemas_sha256,
)

_SHA_A = "a" * 64

_TOOLS = (
    {
        "type": "function",
        "function": {
            "name": "turnOnLight",
            "description": "Turn on a named light.",
            "parameters": {
                "type": "object",
                "properties": {"zone": {"type": "string"}},
                "required": ["zone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setAlarm",
            "description": "Set an alarm.",
            "parameters": {
                "type": "object",
                "properties": {"time": {"type": "string"}},
                "required": ["time"],
            },
        },
    },
)


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
    def __init__(self, tmp_path: Path, *, sample_rate_hz: int = 16000) -> None:
        self.data_root = tmp_path / "data"
        self.carrier_root = self.data_root / "datasets" / "fake-carrier"
        self.media_dir = self.carrier_root / "media"
        self.run_dir = tmp_path / "run"
        self.samples: list[_FakeSample] = []
        for sample_id, seconds in (("s1", 2.0), ("s2", 3.5)):
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
        run_id="SAEA-E-TEST-native-tools-client",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="fake-carrier",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash("f" * 64, "bare-core", _SHA_A),
        attempt_id="attempt-native-tools-client-0001",
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
    world, tmp_path, *, gate=None, transport=None, plan=None, **kwargs
) -> tuple[FrozenCoreClient, _OpenGate, _CapturingTransport]:
    gate = gate or _OpenGate()
    transport = transport or _CapturingTransport()
    client = FrozenCoreClient(
        plan=plan or _plan(),
        gate=gate,
        transport=transport,
        run_dir=world.run_dir,
        binding=_binding(world),
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
# canonical hash: agreement with data.audio2tool_tools.openai_tools_sha256
# ---------------------------------------------------------------------------


def test_tool_schemas_sha256_agrees_with_the_data_module_canonical_hash():
    """The two-line canonical hash re-implemented locally in
    rails.core_client (module docstring: kept light, never importing
    data.audio2tool_tools) must agree byte-for-byte with the DRIVER-side
    canonical hash (data.audio2tool_tools.openai_tools_sha256, D1a) on the
    same synthetic tool list."""

    assert _tool_schemas_sha256(_TOOLS) == openai_tools_sha256(_TOOLS)


def test_tool_schemas_sha256_is_order_and_key_order_stable():
    reordered_entries = tuple(reversed(_TOOLS))
    assert _tool_schemas_sha256(_TOOLS) != _tool_schemas_sha256(reordered_entries)
    reordered_keys = tuple(
        {key: entry[key] for key in reversed(list(entry))} for entry in _TOOLS
    )
    assert _tool_schemas_sha256(_TOOLS) == _tool_schemas_sha256(reordered_keys)


# ---------------------------------------------------------------------------
# construction: native arm requires tool_schemas / non-native arm refuses it
# ---------------------------------------------------------------------------


def test_native_packet_arm_requires_tool_schemas(tmp_path):
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="non-empty tool_schemas"):
        _client(
            world,
            tmp_path,
            arm="speech-feature-query-native-tools",
            speech_feature_root=feature_root,
            speech_packet_bindings=bindings,
        )


@pytest.mark.parametrize("empty", [[], None], ids=["empty-list", "none"])
def test_native_packet_arm_rejects_an_empty_tool_schemas_sequence(tmp_path, empty):
    # Item E23b (b5b13d72) made the explicit empty TUPLE the tool-free native arm's accepted contract
    # (rails.core_client.tool_free_native_schemas; proven in test_e23_tool_free_native_arm.py). Every other empty
    # value -- an empty list, or no schemas at all -- is still refused by _validate_tool_schemas.
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="non-empty tool_schemas"):
        _client(
            world,
            tmp_path,
            arm="speech-feature-query-native-tools",
            speech_feature_root=feature_root,
            speech_packet_bindings=bindings,
            tool_schemas=empty,
        )


def test_default_arm_refuses_tool_schemas(tmp_path):
    world = _World(tmp_path)
    with pytest.raises(FrozenCoreClientError, match="not a native tool-calling arm"):
        _client(world, tmp_path, tool_schemas=_TOOLS)


def test_speech_feature_query_arm_refuses_tool_schemas(tmp_path):
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="not a native tool-calling arm"):
        _client(
            world,
            tmp_path,
            arm="speech-feature-query",
            speech_feature_root=feature_root,
            speech_packet_bindings=bindings,
            tool_schemas=_TOOLS,
        )


def test_native_packet_arm_rejects_an_entry_that_is_not_type_function(tmp_path):
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="type 'function'"):
        _client(
            world,
            tmp_path,
            arm="speech-feature-query-native-tools",
            speech_feature_root=feature_root,
            speech_packet_bindings=bindings,
            tool_schemas=({"type": "not-function", "function": {"name": "x"}},),
        )


def test_native_packet_arm_rejects_a_missing_function_name(tmp_path):
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    with pytest.raises(FrozenCoreClientError, match="function.name"):
        _client(
            world,
            tmp_path,
            arm="speech-feature-query-native-tools",
            speech_feature_root=feature_root,
            speech_packet_bindings=bindings,
            tool_schemas=({"type": "function", "function": {}},),
        )


def test_native_arm_rejects_duplicate_names_in_registered_superset(tmp_path):
    world = _World(tmp_path)
    duplicate = ({**_TOOLS[0], "function": dict(_TOOLS[0]["function"])},) * 2
    with pytest.raises(FrozenCoreClientError, match="duplicate function names"):
        _client(
            world, tmp_path, arm="bare-core-native-tools", tool_schemas=duplicate,
        )


def test_registered_superset_is_immune_to_nested_caller_mutation(tmp_path):
    world = _World(tmp_path)
    supplied = json.loads(json.dumps(_TOOLS))
    admitted = json.loads(json.dumps(_TOOLS))
    client, _, transport = _client(
        world, tmp_path, arm="bare-core-native-tools", tool_schemas=supplied,
    )
    admitted_hash = _tool_schemas_sha256(admitted)
    supplied[0]["function"]["description"] = "Changed after admission."
    supplied[0]["function"]["parameters"]["properties"]["zone"]["type"] = "integer"

    prepared = client.prepare_request(
        _zero_supply_messages(world.media_relpath("s1")),
    )
    exposed = prepared.as_payload()
    exposed["tool_schemas"][0]["function"]["description"] = "Changed payload copy."
    client.complete_prepared_with_metadata(prepared)
    client.complete(
        _zero_supply_messages(world.media_relpath("s2")),
        tool_names=("turnOnLight",),
    )

    assert transport.calls[0]["tool_schemas"] == admitted
    assert transport.calls[1]["tool_schemas"] == [admitted[0]]
    assert client.timings[0].tool_schemas_sha256 == admitted_hash
    assert client.close()["tool_schemas_sha256"] == admitted_hash


# ---------------------------------------------------------------------------
# payload byte-identity: packet path (real D2 arm) vs speech-feature-query
# ---------------------------------------------------------------------------


def test_native_packet_arm_payload_equals_speech_feature_query_plus_tool_schemas(
    tmp_path,
):
    """"speech-feature-query-native-tools" carries tool_schemas and is
    otherwise byte-identical to "speech-feature-query" for the same
    messages/sample/decision ids -- proven by constructing one client per
    arm against separately-materialized (but content-identical) worlds and
    comparing the exact request payloads a fake transport captured."""

    world_plain = _World(tmp_path / "plain")
    world_native = _World(tmp_path / "native")
    feature_root_plain, packet_plain, bindings_plain = _speech_feature_world(
        world_plain, tmp_path / "plain"
    )
    feature_root_native, packet_native, bindings_native = _speech_feature_world(
        world_native, tmp_path / "native"
    )

    plain_client, _, plain_transport = _client(
        world_plain,
        tmp_path / "plain",
        arm="speech-feature-query",
        speech_feature_root=feature_root_plain,
        speech_packet_bindings=bindings_plain,
    )
    native_client, _, native_transport = _client(
        world_native,
        tmp_path / "native",
        arm="speech-feature-query-native-tools",
        speech_feature_root=feature_root_native,
        speech_packet_bindings=bindings_native,
        tool_schemas=_TOOLS,
    )

    plain_client.complete(
        _speech_feature_messages(packet_plain, "roster: kitchen"),
        speech_feature_sample_id="s1",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="m1-listwise-v1",
    )
    native_client.complete(
        _speech_feature_messages(packet_native, "roster: kitchen"),
        speech_feature_sample_id="s1",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="m1-listwise-v1",
    )

    plain_payload = plain_transport.calls[0]
    native_payload = dict(native_transport.calls[0])
    assert native_payload.pop("tool_schemas") == list(_TOOLS)
    assert native_payload == plain_payload
    assert set(plain_payload) == set(
        d2_leakage.ARM_VISIBLE_FIELDS["speech-feature-query"]
    )


def test_native_packet_arm_payload_satisfies_the_adapters_own_allowlist(tmp_path):
    """A successful complete() call proves FrozenCoreAdapter.request's own
    exact-key allowlist check passed: the fake transport is only ever
    reached AFTER that check (core.model.adapter.FrozenCoreAdapter.request),
    so a captured payload is direct evidence the check accepted it."""

    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query-native-tools",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
        tool_schemas=_TOOLS,
    )

    client.complete(
        _speech_feature_messages(packet, "roster: kitchen"),
        speech_feature_sample_id="s1",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="m1-listwise-v1",
    )

    payload = transport.calls[0]
    assert set(payload) == set(
        d2_leakage.ARM_VISIBLE_FIELDS["speech-feature-query-native-tools"]
    )
    assert payload["tool_schemas"] == list(_TOOLS)


# ---------------------------------------------------------------------------
# payload byte-identity: raw-audio pattern (test-local synthetic arm) vs
# fixed-legal-context -- "for BOTH audio paths" (module comment).
#
# The D2 registry adds exactly ONE new arm this slice
# ("speech-feature-query-native-tools" -- e0.d2_leakage.py's own hard rule);
# the CLIENT's own acceptance logic is written generically for both shapes
# (rails.core_client._ACCEPTED_ARM_FIELD_SETS), so the raw-audio member of
# that pair is exercised here through a test-local monkeypatch of
# ARM_VISIBLE_FIELDS -- reverted automatically by pytest at the end of the
# test, never a mutation of the real D2 registry.
# ---------------------------------------------------------------------------


def test_raw_audio_native_arm_payload_equals_fixed_legal_context_plus_tool_schemas(
    tmp_path, monkeypatch
):
    synthetic_arm = "TESTONLY-fixed-legal-context-native-tools"
    monkeypatch.setitem(
        d2_leakage.ARM_VISIBLE_FIELDS,
        synthetic_arm,
        (*d2_leakage.ARM_VISIBLE_FIELDS["fixed-legal-context"], _NATIVE_TOOLS_FIELD),
    )

    world_plain = _World(tmp_path / "plain")
    world_native = _World(tmp_path / "native")

    plain_client, _, plain_transport = _client(
        world_plain, tmp_path / "plain", arm="fixed-legal-context"
    )
    native_client, _, native_transport = _client(
        world_native, tmp_path / "native", arm=synthetic_arm, tool_schemas=_TOOLS
    )

    plain_client.complete(_zero_supply_messages(world_plain.media_relpath("s1")))
    native_client.complete(_zero_supply_messages(world_native.media_relpath("s1")))

    plain_payload = plain_transport.calls[0]
    native_payload = dict(native_transport.calls[0])
    assert native_payload.pop("tool_schemas") == list(_TOOLS)
    assert native_payload == plain_payload


def test_raw_audio_native_arm_requires_tool_schemas(tmp_path, monkeypatch):
    synthetic_arm = "TESTONLY-fixed-legal-context-native-tools-2"
    monkeypatch.setitem(
        d2_leakage.ARM_VISIBLE_FIELDS,
        synthetic_arm,
        (*d2_leakage.ARM_VISIBLE_FIELDS["fixed-legal-context"], _NATIVE_TOOLS_FIELD),
    )
    world = _World(tmp_path)
    with pytest.raises(FrozenCoreClientError, match="non-empty tool_schemas"):
        _client(world, tmp_path, arm=synthetic_arm)


# ---------------------------------------------------------------------------
# close() -- tool_schemas_sha256 threaded through
# ---------------------------------------------------------------------------


def test_close_summary_carries_tool_schemas_sha256_for_a_native_arm(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, _transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query-native-tools",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
        tool_schemas=_TOOLS,
    )
    client.complete(
        _speech_feature_messages(packet, "roster: kitchen"),
        speech_feature_sample_id="s1",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="m1-listwise-v1",
    )

    summary = client.close()

    expected_hash = _tool_schemas_sha256(_TOOLS)
    assert expected_hash == openai_tools_sha256(_TOOLS)
    assert summary["arm"] == "speech-feature-query-native-tools"
    assert summary["tool_schemas_sha256"] == expected_hash
    assert summary["timings"][0]["tool_schemas_sha256"] == expected_hash
    assert client.timings[0].tool_schemas_sha256 == expected_hash


def test_one_native_client_scopes_tools_per_contact_and_preserves_default_bytes(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(
        world, tmp_path, arm="bare-core-native-tools", tool_schemas=_TOOLS
    )
    messages = _zero_supply_messages(world.media_relpath("s1"))
    default = client.prepare_request(messages)
    explicit_full = client.prepare_request(
        messages, tool_names=("turnOnLight", "setAlarm")
    )
    assert default.payload_bytes == explicit_full.payload_bytes

    proper = client.complete_with_metadata(
        messages, tool_names=("setAlarm",),
        decoding_params={"tool_choice": "auto", "parallel_tool_calls": False},
    )
    empty = client.complete_with_metadata(
        messages, tool_names=(), decoding_params={"tool_choice": "none"},
    )

    assert transport.calls[0]["tool_schemas"] == [_TOOLS[1]]
    assert transport.calls[1]["tool_schemas"] == []
    assert proper.tool_names == ("setAlarm",)
    assert proper.tool_schemas_sha256 == _tool_schemas_sha256((_TOOLS[1],))
    assert empty.tool_names == ()
    assert empty.tool_schemas_sha256 == _tool_schemas_sha256(())
    assert client.timings[0].tool_names == ("setAlarm",)
    assert client.timings[1].tool_names == ()
    assert client.close()["tool_schemas_sha256"] == _tool_schemas_sha256(_TOOLS)


@pytest.mark.parametrize("tool_names", [("unknown",), ("setAlarm", "setAlarm")])
def test_per_contact_tool_scope_refuses_unknown_or_duplicate_before_contact(
    tmp_path, tool_names,
):
    world = _World(tmp_path)
    client, gate, transport = _client(
        world, tmp_path, arm="bare-core-native-tools", tool_schemas=_TOOLS
    )
    checked_before = list(gate.checked_plans)
    with pytest.raises(FrozenCoreClientError, match="tool_names"):
        client.complete(
            _zero_supply_messages(world.media_relpath("s1")), tool_names=tool_names,
        )
    assert transport.calls == []
    assert gate.checked_plans == checked_before


def test_empty_scope_requires_none_and_non_native_client_refuses_selector(tmp_path):
    world = _World(tmp_path)
    native, _, native_transport = _client(
        world, tmp_path / "native", arm="bare-core-native-tools", tool_schemas=_TOOLS
    )
    with pytest.raises(FrozenCoreClientError, match="requires tool_choice 'none'"):
        native.complete(
            _zero_supply_messages(world.media_relpath("s1")), tool_names=(),
            decoding_params={"tool_choice": "auto"},
        )
    assert native_transport.calls == []

    plain_world = _World(tmp_path / "plain")
    plain, _, plain_transport = _client(plain_world, tmp_path / "plain")
    with pytest.raises(FrozenCoreClientError, match="native tool-calling arm"):
        plain.complete(
            _zero_supply_messages(plain_world.media_relpath("s1")), tool_names=(),
        )
    assert plain_transport.calls == []


def test_prepared_request_retains_selected_tools_through_owned_send(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(
        world, tmp_path, arm="bare-core-native-tools", tool_schemas=_TOOLS
    )
    request = client.prepare_request(
        _zero_supply_messages(world.media_relpath("s1")), tool_names=("setAlarm",),
    )
    assert request.as_payload()["tool_schemas"] == [_TOOLS[1]]

    completion = client.complete_prepared_with_metadata(request)

    assert transport.calls[0]["tool_schemas"] == [_TOOLS[1]]
    assert completion.tool_names == ("setAlarm",)
    assert completion.tool_schemas_sha256 == _tool_schemas_sha256((_TOOLS[1],))
    assert client.timings[0].tool_names == ("setAlarm",)


def test_close_summary_tool_schemas_sha256_is_none_for_a_non_native_arm(tmp_path):
    world = _World(tmp_path)
    client, _, _transport = _client(world, tmp_path)
    client.complete(_zero_supply_messages(world.media_relpath("s1")))

    summary = client.close()

    assert summary["arm"] == "fixed-legal-context"
    assert summary["tool_schemas_sha256"] is None
    assert summary["timings"][0]["tool_schemas_sha256"] is None
    assert client.timings[0].tool_schemas_sha256 is None


# ---------------------------------------------------------------------------
# 2026-09-04: the evidence-FREE raw-audio arms. This bridge was written for
# "fixed-legal-context", whose field set carries supplied_evidence /
# evidence_provenance; A0 flew zero-supply THROUGH that arm by sending two
# empty lists. "bare-core" and "bare-core-native-tools" declare no evidence
# fields at all, and FrozenCoreAdapter.request enforces
# set(payload) == ARM_VISIBLE_FIELDS[arm] EXACTLY, so those two empty lists
# are an allowlist violation for them -- which is why the direct-baseline
# calibration's two raw cells could not be constructed at all before this.
# ---------------------------------------------------------------------------


def test_bare_core_arm_is_accepted_and_omits_the_evidence_fields(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(world, tmp_path, arm="bare-core")

    client.complete(_zero_supply_messages(world.media_relpath("s1")))

    payload = transport.calls[0]
    assert set(payload) == set(d2_leakage.ARM_VISIBLE_FIELDS["bare-core"])
    assert "supplied_evidence" not in payload
    assert "evidence_provenance" not in payload


def test_bare_core_native_tools_arm_is_accepted_with_tool_schemas(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(
        world, tmp_path, arm="bare-core-native-tools", tool_schemas=_TOOLS
    )

    client.complete(_zero_supply_messages(world.media_relpath("s1")))

    payload = transport.calls[0]
    assert set(payload) == set(
        d2_leakage.ARM_VISIBLE_FIELDS["bare-core-native-tools"]
    )
    assert payload["tool_schemas"] == list(_TOOLS)


def test_bare_core_payload_equals_fixed_legal_context_minus_the_evidence_fields(
    tmp_path,
):
    """Factor D of the calibration compares these two audio paths, so the
    non-evidence half of the payload must be identical to what the
    evidence-carrying arm sends for the same messages."""

    world_bare = _World(tmp_path / "bare")
    world_legal = _World(tmp_path / "legal")
    bare_client, _, bare_transport = _client(
        world_bare, tmp_path / "bare", arm="bare-core"
    )
    legal_client, _, legal_transport = _client(
        world_legal, tmp_path / "legal", arm="fixed-legal-context"
    )

    bare_client.complete(_zero_supply_messages(world_bare.media_relpath("s1")))
    legal_client.complete(_zero_supply_messages(world_legal.media_relpath("s1")))

    legal_payload = dict(legal_transport.calls[0])
    assert legal_payload.pop("supplied_evidence") == []
    assert legal_payload.pop("evidence_provenance") == []
    assert dict(bare_transport.calls[0]) == legal_payload


def test_bare_core_arm_refuses_supply_text_it_cannot_record(tmp_path):
    world = _World(tmp_path)
    client, _, transport = _client(world, tmp_path, arm="bare-core")

    messages = [
        {"role": "system", "content": "instruction"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "roster: kitchen"},
                {"type": "input_audio", "media_relpath": world.media_relpath("s1")},
            ],
        },
    ]
    with pytest.raises(FrozenCoreClientError, match="declares no evidence fields"):
        client.complete(messages)
    assert transport.calls == []


def test_the_three_unsupported_arms_are_still_refused(tmp_path):
    """Widening the accepted field sets must not accidentally admit an arm
    whose payload this bridge does not build."""

    world = _World(tmp_path)
    for arm in ("fixed-retrieval", "exemplar-context", "fixed-legal-context-replay"):
        with pytest.raises(FrozenCoreClientError, match="different field set"):
            _client(world, tmp_path / arm, arm=arm)


# ---------------------------------------------------------------------------
# Phase 3a (2026-09-04): a response's ARRIVAL shape, carried through.
#
# core.model.transport canonicalizes a native message.tool_calls into the same
# [{"name": ..., "arguments": {...}}] text a free-text arm produces, so a
# sealed row cannot be read back to tell them apart. core.model.CoreResponse
# now carries the raw list; this bridge records how many came back.
# ---------------------------------------------------------------------------


def test_request_timing_records_native_tool_calls(tmp_path):
    world = _World(tmp_path)

    def _native_transport(request_bytes: bytes) -> bytes:
        return json.dumps(
            {
                "text": '[{"name": "setLighting", "arguments": {}}]',
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                "tool_calls": [
                    {
                        "id": "c0",
                        "type": "function",
                        "function": {"name": "setLighting", "arguments": "{}"},
                    }
                ],
            }
        ).encode("utf-8")

    client, _, _ = _client(
        world,
        tmp_path,
        arm="bare-core-native-tools",
        transport=_native_transport,
        tool_schemas=_TOOLS,
    )
    client.complete(_zero_supply_messages(world.media_relpath("s1")))

    timing = client.timings[0]
    assert timing.native_tool_calls == 1
    assert timing.as_json()["native_tool_calls"] == 1


def test_request_timing_records_text_arrival_as_none(tmp_path):
    """A response with no tool_calls key is a TEXT answer -- which is what
    the calibration smoke's native cells actually produced, and what the
    canonical-array text alone could not reveal."""

    world = _World(tmp_path)
    client, _, _ = _client(
        world, tmp_path, arm="bare-core-native-tools", tool_schemas=_TOOLS
    )
    client.complete(_zero_supply_messages(world.media_relpath("s1")))

    timing = client.timings[0]
    assert timing.native_tool_calls is None
    assert timing.as_json()["native_tool_calls"] is None


def test_non_native_arm_never_reports_native_tool_calls(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(world, tmp_path, arm="bare-core")
    client.complete(_zero_supply_messages(world.media_relpath("s1")))

    assert client.timings[0].native_tool_calls is None


def test_no_wire_metadata_stays_absent_on_core_completion(tmp_path):
    world = _World(tmp_path)
    client, _, _ = _client(
        world,
        tmp_path,
        arm="bare-core-native-tools",
        tool_schemas=_TOOLS,
    )
    completion = client.complete_with_metadata(
        _zero_supply_messages(world.media_relpath("s1")),
        decoding_params={"tool_choice": "auto"},
    )
    client.close()

    assert completion.wire_response_bytes is None
    assert completion.original_message is None
    assert completion.finish_reason is None
