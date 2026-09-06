"""``FrozenCoreClient`` on the construction-proposer arm (E2.4, 2026-09-05).

``"construction-proposer-text"`` is the one D2 arm whose field set carries
gold (``contracts.CONSTRUCTION_VISIBLE_ARMS`` /
``e0.d2_leakage.ARM_VISIBLE_FIELDS``), and only CONSTRUCTION gold. What this
file proves about the bridge, end to end and with no live contact:

* the arm's field set is accepted (bare-core's zero-supply set plus exactly
  ``construction_targets``), and every other arm still refuses the kwarg;
* the targets are bound ONCE at construction and validated to the exact
  ``{"sample_id", "target"}`` shape, so a per-request caller can never widen
  what gold the core sees;
* the contact is TEXT-ONLY: a request that names no ``text_only_sample_id``
  is refused before a byte is sent, and the payload that IS sent carries the
  targets and nothing else beyond the arm's declared fields.

Engineering-only, ZERO live model contact: a fake arm-aware gate and a fake
capturing transport, mirroring the doubles in
``test_rails_core_client_native_tools.py``.
"""

from __future__ import annotations

import hashlib
import json
import wave
from dataclasses import dataclass
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import (
    CONSTRUCTION_VISIBLE_FIELD,
    ExecutionPlan,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.rails import (
    AudioRef,
    FrozenCoreClient,
    FrozenCoreClientError,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.core_client import (
    _ACCEPTED_ARM_FIELD_SETS,
    _CONSTRUCTION_PROPOSER_ARM_FIELDS,
)

PROPOSER_ARM = "construction-proposer-text"
_SHA_A = "a" * 64
_TARGETS = (
    {"sample_id": "tier1_direct:000101", "target": "setLighting(deviceId='l1')"},
    {"sample_id": "tier2_parametric:000202", "target": "setAlarm(time='07:00')"},
)


class _ArmAwareGate:
    """A gate double with the E2.4 signature -- it records the arm it was
    told about, which is what the real gate needs in order to check the
    construction-roster binding at all."""

    def __init__(self) -> None:
        self.checked: list[tuple[object, str | None]] = []

    def assert_model_touch_allowed(self, plan, *, full_hash=None, diagnostics=None, arm=None):
        self.checked.append((plan, arm))
        return None


class _CapturingTransport:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, request_bytes: bytes) -> bytes:
        self.calls.append(json.loads(request_bytes.decode("utf-8")))
        return json.dumps(
            {"text": "ok", "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
        ).encode("utf-8")


def _write_wav(path: Path, *, seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * int(16000 * seconds))


@dataclass(frozen=True)
class _FakeSample:
    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


class _World:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "data"
        self.carrier_root = self.data_root / "datasets" / "fake-carrier"
        self.run_dir = tmp_path / "run"
        self.samples: list[_FakeSample] = []
        for sample_id, seconds in (("s1", 2.0), ("s2", 3.5)):
            relpath = f"datasets/fake-carrier/media/{sample_id}.wav"
            path = self.data_root / relpath
            _write_wav(path, seconds=seconds)
            self.samples.append(
                _FakeSample(
                    sample_id=sample_id,
                    audio_ref=AudioRef(
                        path=relpath,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    ).validate(),
                    audio_seconds=seconds,
                )
            )


def _plan(**overrides) -> ExecutionPlan:
    values = dict(
        run_id="SAEA-E-TEST-construction-proposer",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="fake-carrier",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash("f" * 64, PROPOSER_ARM, _SHA_A),
        attempt_id="attempt-construction-proposer-0001",
    )
    values.update(overrides)
    return ExecutionPlan(**values)


def _client(world: _World, *, arm: str = PROPOSER_ARM, **kwargs):
    gate = _ArmAwareGate()
    transport = _CapturingTransport()
    client = FrozenCoreClient(
        plan=_plan(),
        gate=gate,
        transport=transport,
        run_dir=world.run_dir,
        binding=build_payload_binding(
            carrier_lock_key="fake-carrier",
            samples=world.samples,
            data_root=world.data_root,
            carrier_root=world.carrier_root,
        ),
        arm=arm,
        **kwargs,
    )
    return client, gate, transport


def _text_messages():
    """The proposer's own message shape: everything the core is asked to read
    lives in the system message (``task_instruction``) and in the audited
    ``construction_targets`` field. The user content list is EMPTY on
    purpose -- a zero-supply arm has nowhere to record a free-floating user
    text part, and the client refuses one rather than sending text the
    audited payload does not carry."""

    return (
        {"role": "system", "content": "Propose one tool description."},
        {"role": "user", "content": []},
    )


# ---------------------------------------------------------------------------
# field set
# ---------------------------------------------------------------------------


def test_the_arms_field_set_is_accepted_and_is_bare_core_plus_one_field() -> None:
    declared = frozenset(ARM_VISIBLE_FIELDS[PROPOSER_ARM])
    assert declared == _CONSTRUCTION_PROPOSER_ARM_FIELDS
    assert declared in _ACCEPTED_ARM_FIELD_SETS
    assert declared == frozenset(ARM_VISIBLE_FIELDS["bare-core"]) | {
        CONSTRUCTION_VISIBLE_FIELD
    }


def test_the_arm_requires_construction_targets(tmp_path: Path) -> None:
    world = _World(tmp_path)
    with pytest.raises(FrozenCoreClientError, match="non-empty construction_targets"):
        _client(world)
    with pytest.raises(FrozenCoreClientError, match="non-empty construction_targets"):
        _client(world, construction_targets=())


def test_every_other_arm_refuses_the_kwarg(tmp_path: Path) -> None:
    world = _World(tmp_path)
    with pytest.raises(
        FrozenCoreClientError, match="not a construction-proposer arm"
    ):
        _client(world, arm="bare-core", construction_targets=_TARGETS)


@pytest.mark.parametrize(
    "entry",
    [
        {"sample_id": "s", "target": "t", "extra": "smuggled"},
        {"sample_id": "s"},
        {"sample_id": "", "target": "t"},
        {"sample_id": "s", "target": ""},
        "not-a-mapping",
    ],
)
def test_a_target_entry_of_any_other_shape_is_refused(tmp_path: Path, entry) -> None:
    world = _World(tmp_path)
    with pytest.raises(FrozenCoreClientError, match="construction_targets"):
        _client(world, construction_targets=(entry,))


# ---------------------------------------------------------------------------
# the request itself
# ---------------------------------------------------------------------------


def test_the_arm_is_text_only_and_the_payload_carries_the_targets(
    tmp_path: Path,
) -> None:
    world = _World(tmp_path)
    client, gate, transport = _client(world, construction_targets=_TARGETS)
    text = client.complete(_text_messages(), text_only_sample_id="s1")
    assert text == "ok"
    # The gate was told which arm it was gating -- without that the real gate
    # cannot check the construction-roster binding at all.
    assert gate.checked and gate.checked[0][1] == PROPOSER_ARM
    payload = transport.calls[0]
    assert set(payload) == set(ARM_VISIBLE_FIELDS[PROPOSER_ARM])
    assert payload[CONSTRUCTION_VISIBLE_FIELD] == [dict(entry) for entry in _TARGETS]
    assert payload["sample_id"] == "s1"
    # text-only: the request the transport received carries no audio input
    # of any kind, only the arm's declared fields.
    assert "input_audio" not in json.dumps(transport.calls[0])
    client.close()


def test_a_free_floating_user_text_part_is_refused_on_this_zero_supply_arm(
    tmp_path: Path,
) -> None:
    """The arm declares no evidence fields, so a user text part has nowhere
    to be recorded in the audited payload; the bridge refuses it rather than
    sending the core text the receipt does not name."""

    world = _World(tmp_path)
    client, _gate, transport = _client(world, construction_targets=_TARGETS)
    with pytest.raises(FrozenCoreClientError, match="declares no evidence fields"):
        client.complete(
            (
                {"role": "system", "content": "Propose one tool description."},
                {"role": "user", "content": [{"type": "text", "text": "smuggled"}]},
            ),
            text_only_sample_id="s1",
        )
    assert transport.calls == []
    client.close()


def test_an_audio_request_on_the_proposer_arm_is_refused(tmp_path: Path) -> None:
    world = _World(tmp_path)
    client, _gate, transport = _client(world, construction_targets=_TARGETS)
    with pytest.raises(FrozenCoreClientError, match="text_only_sample_id"):
        client.complete(
            (
                {"role": "system", "content": "Propose one tool description."},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "media_relpath": "datasets/fake-carrier/media/s1.wav",
                        }
                    ],
                },
            )
        )
    assert transport.calls == []
    client.close()


def test_the_targets_are_bound_once_and_never_aliased(tmp_path: Path) -> None:
    world = _World(tmp_path)
    mutable = [dict(entry) for entry in _TARGETS]
    client, _gate, transport = _client(world, construction_targets=mutable)
    mutable[0]["target"] = "MUTATED-AFTER-CONSTRUCTION"
    client.complete(_text_messages(), text_only_sample_id="s1")
    payload = transport.calls[0]
    assert payload[CONSTRUCTION_VISIBLE_FIELD][0]["target"] == _TARGETS[0]["target"]
    client.close()
