"""Model-free tests for per-contact native trajectory fitting."""

from __future__ import annotations

import base64
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts.plan import ExecutionPlan
from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    canonical_bytes,
)
from speech_aware_evidence_acquisition.core.preparation_fit import (
    build_native_contact_fit_gate,
    validate_live_phase_fit_config,
    validate_native_contact_fit_config,
)
from speech_aware_evidence_acquisition.rails.core_client import PreparedCoreRequest


SHA = "a" * 64


def _plan(**overrides) -> ExecutionPlan:
    values = {
        "run_id": "generation-run",
        "attempt_id": "generation-attempt",
        "execution_profile": "bounded-discovery-probe",
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "split_identity_hash": SHA,
        "planned_model_calls": 4,
        "planned_gpu_hours": 0.5,
        "planned_speech_audio_seconds": 10,
        "protocol_hash": "b" * 64,
    }
    values.update(overrides)
    return ExecutionPlan(**values).validate()


def _program(*, max_contacts=2, stop_rule="native-role-episode"):
    return SimpleNamespace(
        max_contacts=max_contacts,
        stop_rule=stop_rule,
        phase_names=lambda: ("native-episode",),
    )


def _values(**overrides):
    values = {
        "native_contact_fit": {
            "run_id": "fit-run",
            "attempt_id": "fit-attempt",
            "contact_cap": 16,
        },
        "speech_feature_root": "/synthetic-feature-root",
    }
    values.update(overrides)
    return values


@dataclass(frozen=True)
class _Sample:
    sample_id: str


class _Transport:
    def __init__(self):
        self.calls = []

    def render_request(self, raw):
        self.calls.append(raw)
        payload = json.loads(raw)
        speech_parts = [
            {
                "type": "input_speech_features",
                "speech_features": descriptor,
            }
            for descriptor in payload["speech_feature_parts"]
        ]
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": payload["task_instruction"]},
                        *speech_parts,
                    ],
                }
            ],
            "max_tokens": payload["decoding_params"]["max_tokens"],
        }


class _Tokenizer:
    def __init__(self, **_kwargs):
        self.calls = []

    def request_json(self, method, path, payload):
        self.calls.append((method, path, payload))
        if (method, path) == ("GET", "/props"):
            return {"media_marker": "<media>"}
        if path == "/apply-template":
            marker_count = sum(
                part.get("type") == "input_speech_features"
                for message in payload["messages"]
                for part in message["content"]
            )
            return {"prompt": "<media>".join(["text"] * (marker_count + 1))}
        if path == "/tokenize":
            return {"tokens": [1]}
        raise AssertionError((method, path))


class _RawTransport:
    def __init__(self, raw=b"RIFF synthetic native raw speech"):
        self.raw = raw
        self.calls = []

    def render_request(self, raw):
        self.calls.append(raw)
        payload = json.loads(raw)
        return {
            "messages": [
                {"role": "system", "content": payload["task_instruction"]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": base64.b64encode(self.raw).decode("ascii")
                            },
                        }
                    ],
                },
            ],
            "max_tokens": payload["decoding_params"]["max_tokens"],
        }


class _RawTokenizer(_Tokenizer):
    def request_json(self, method, path, payload):
        self.calls.append((method, path, payload))
        if (method, path) == ("POST", "/v1/chat/completions/input_tokens"):
            return {"input_tokens": 7}
        raise AssertionError((method, path))


class _Runtime:
    def __init__(self, tmp_path, values=None):
        self._composed = SimpleNamespace(values=values or _values())
        self._data_root = self._repo_root = self._runtime_root = tmp_path
        self._samples = (_Sample("s1"), _Sample("s2"))
        self._transport = _Transport()
        self._session = SimpleNamespace(
            host="127.0.0.1",
            port=9999,
            session_id="synthetic-session",
            model_files=(SimpleNamespace(path="decoder.gguf", sha256="c" * 64),),
        )
        self._adapter = SimpleNamespace(serving_geometry=lambda: {"slot_tokens": 128})
        self._gate = object()
        self.touches = []
        self.unconsumed = []
        self.lease_checks = 0

    def uses_speech_feature_packets(self):
        return True

    def assert_generation_lease(self):
        self.lease_checks += 1

    def _gate_touch(self, gate, fit_plan):
        assert gate is self._gate
        self.touches.append(fit_plan)

    def _require_exposure_row_unconsumed(self, run_id):
        self.unconsumed.append(run_id)

    def session_required_identity(self):
        return {"session": "synthetic-session", "decoder": "c" * 64}

    def request_fit_inputs(self, payloads):
        return {
            "config_sha256": "d" * 64,
            "split_identity_hash": SHA,
            "sources": {"payloads": payloads},
        }


def _prepared(
    sample_id: str, contact_id: str, *, speech_packets: int = 1
) -> PreparedCoreRequest:
    return PreparedCoreRequest(
        canonical_bytes(
            {
                "request_id": "saea-prepared-request",
                "sample_id": sample_id,
                "task_instruction": "Answer the spoken request.",
                "history": [
                    {
                        "turn": 1,
                        "role": "control",
                        "contact_id": contact_id,
                        "content": "Act in the assigned role.",
                        "content_sha256": "e" * 64,
                    }
                ],
                "speech_feature_parts": [
                    {
                        "packet_id": f"{sample_id}-packet-{index}",
                        "sha256": str(index) * 64,
                        "role": "query" if index == 1 else "key",
                    }
                    for index in range(1, speech_packets + 1)
                ],
                "decoding_params": {"max_tokens": 4},
            }
        ),
        object(),
    )


def _raw_prepared(sample_id: str, contact_id: str, raw: bytes) -> PreparedCoreRequest:
    return PreparedCoreRequest(
        canonical_bytes(
            {
                "request_id": "saea-prepared-request",
                "sample_id": sample_id,
                "media_relpath": f"media/{sample_id}.wav",
                "raw_speech_query": {
                    "media_relpath": f"media/{sample_id}.wav",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                },
                "task_instruction": "Answer the spoken request.",
                "history": [
                    {
                        "turn": 1,
                        "role": "control",
                        "contact_id": contact_id,
                        "content": "Act in the assigned role.",
                        "content_sha256": "e" * 64,
                    }
                ],
                "decoding_params": {"max_tokens": 4},
            }
        ),
        object(),
    )


def _raw_runtime(tmp_path):
    runtime = _Runtime(
        tmp_path,
        _values(
            native_contact_fit={
                "run_id": "fit-run",
                "attempt_id": "fit-attempt",
                # Two roster entries x two allowed contacts x one actual
                # resident multimodal counting endpoint.
                "contact_cap": 4,
            }
        ),
    )
    runtime._transport = _RawTransport()
    runtime.uses_speech_feature_packets = lambda: False
    runtime._arm = lambda: "raw-speech-agent-native-tools"
    return runtime


def test_native_raw_contact_fit_measures_the_rendered_audio_request(tmp_path):
    runtime = _raw_runtime(tmp_path)
    tokenizer = _RawTokenizer()
    gate = build_native_contact_fit_gate(
        runtime,
        _program(),
        _plan(),
        client_factory=lambda **_kwargs: tokenizer,
    )
    request = _raw_prepared("s1", "raw-contact-1", runtime._transport.raw)

    gate(request)

    assert gate.execution_plan.planned_model_calls == 4
    assert runtime.lease_checks >= 3
    assert [(method, path) for method, path, _ in tokenizer.calls] == [
        ("POST", "/v1/chat/completions/input_tokens")
    ]
    rendered = runtime._transport.render_request(request.payload_bytes)
    assert tokenizer.calls[0][2] == rendered
    artifact = json.loads(open(gate.receipts[0]["path"], encoding="utf-8").read())
    assert artifact["inputs"]["native_contact"]["raw_speech_query"] == request.as_payload()[
        "raw_speech_query"
    ]
    assert artifact["output"]["rows"][0]["measurement"] == (
        "resident-multimodal-input-tokens"
    )
    assert artifact["output"]["contacts"] == 1
    assert artifact["output"]["raw_speech_query"] == request.as_payload()[
        "raw_speech_query"
    ]
    with pytest.raises(PreparationError, match="repeated agent_contact_id"):
        gate(request)
    assert len(tokenizer.calls) == 1


def test_native_contact_fit_refuses_nonraw_nonfeature_arm_before_lease(tmp_path):
    runtime = _raw_runtime(tmp_path)
    runtime._arm = lambda: "construction-proposer-text"

    with pytest.raises(PreparationError, match="raw-speech-agent-native-tools"):
        build_native_contact_fit_gate(runtime, _program(), _plan())

    assert runtime.lease_checks == 0
    assert runtime.touches == []
    assert runtime.unconsumed == []


@pytest.mark.parametrize(
    "change", ["feature", "source", "rendered-audio", "rendered-feature"]
)
def test_native_raw_contact_fit_refuses_mixed_or_unbound_audio_before_contact(
    tmp_path, change
):
    runtime = _raw_runtime(tmp_path)
    tokenizer = _RawTokenizer()
    request = _raw_prepared("s1", "raw-contact-1", runtime._transport.raw)
    payload = request.as_payload()
    if change == "feature":
        payload["speech_feature_parts"] = []
    elif change == "source":
        payload["raw_speech_query"]["media_relpath"] = "media/other.wav"
    elif change == "rendered-audio":
        runtime._transport.raw += b"changed"
    else:
        render = runtime._transport.render_request

        def mixed_render(raw):
            body = render(raw)
            body["messages"][1]["content"].append(
                {
                    "type": "input_speech_features",
                    "speech_features": {
                        "packet_id": "fake-packet",
                        "sha256": "f" * 64,
                        "role": "query",
                    },
                }
            )
            return body

        runtime._transport.render_request = mixed_render
    if change not in {"rendered-audio", "rendered-feature"}:
        request = PreparedCoreRequest(canonical_bytes(payload), object())
    gate = build_native_contact_fit_gate(
        runtime,
        _program(),
        _plan(),
        client_factory=lambda **_kwargs: tokenizer,
    )

    with pytest.raises(
        PreparationError, match="mixed|source identity|rendered audio|rendered speech feature"
    ):
        gate(request)

    assert tokenizer.calls == []
    assert not list(tmp_path.rglob("*.contacts.jsonl"))


def test_native_contact_gate_fits_each_actual_request_with_registered_budget(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = _Runtime(tmp_path)
    clients = []

    def client_factory(**kwargs):
        client = _Tokenizer(**kwargs)
        clients.append(client)
        return client

    gate = build_native_contact_fit_gate(
        runtime, _program(), _plan(), client_factory=client_factory
    )

    assert gate.execution_plan.run_id == "fit-run"
    assert gate.execution_plan.attempt_id == "fit-attempt"
    assert gate.execution_plan.planned_model_calls == 16
    assert gate.execution_plan.protocol_hash == _plan().protocol_hash
    assert runtime.touches == [gate.execution_plan]
    assert runtime.unconsumed == ["fit-run"]

    requests = (
        _prepared("s1", "s1-perception-1"),
        _prepared("s2", "s2-perception-1"),
        _prepared("s1", "s1-solver-1"),
    )
    for request in requests:
        gate(request)

    assert len(clients) == 3
    assert runtime._transport.calls == [request.payload_bytes for request in requests]
    assert [
        [(method, path) for method, path, _ in client.calls] for client in clients
    ] == [
        [
            ("GET", "/props"),
            ("POST", "/apply-template"),
            ("POST", "/tokenize"),
            ("POST", "/tokenize"),
        ]
    ] * 3
    assert [receipt["sample_id"] for receipt in gate.receipts] == ["s1", "s2", "s1"]
    assert [receipt["agent_contact_id"] for receipt in gate.receipts] == [
        "s1-perception-1",
        "s2-perception-1",
        "s1-solver-1",
    ]
    assert len({receipt["contact_identity_sha256"] for receipt in gate.receipts}) == 3
    for index, receipt in enumerate(gate.receipts, start=1):
        artifact = json.loads(open(receipt["path"], encoding="utf-8").read())
        assert artifact["output"]["every_request_fits"] is True
        assert artifact["output"]["contacts"] == 4
        assert artifact["output"]["cumulative_contacts"] == index * 4
        assert (
            artifact["output"]["capacity_scope"] == "actual-variable-trajectory-contact"
        )
        journal = receipt["path"] + ".contacts.jsonl"
        assert len(open(journal, encoding="utf-8").read().splitlines()) == 4


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"live_phase_fit": {"run_id": "other"}}, "mutually exclusive"),
        ({"prepared_request_fit": {"relpath": "old"}}, "mutually exclusive"),
        ({"prompt_fit_receipt": {"relpath": "old"}}, "mutually exclusive"),
        ({"whole_roster_wave_barrier": True}, "mutually exclusive"),
    ],
)
def test_native_contact_fit_config_refuses_other_fit_modes(overrides, error):
    with pytest.raises(PreparationError, match=error):
        validate_native_contact_fit_config(_values(**overrides), _program())


def test_native_contact_fit_requires_exact_schema_and_native_episode_program():
    with pytest.raises(PreparationError, match="run_id, attempt_id and contact_cap"):
        validate_native_contact_fit_config(
            _values(native_contact_fit={"run_id": "fit-run"}), _program()
        )
    with pytest.raises(PreparationError, match="native-role-episode"):
        validate_native_contact_fit_config(
            _values(), _program(stop_rule="native-answer-or-tool")
        )
    assert (
        validate_native_contact_fit_config(
            _values(
                native_contact_fit={
                    "run_id": "fit-run",
                    "attempt_id": "fit-attempt",
                    "contact_cap": 20,
                    "max_speech_packets": 2,
                }
            ),
            _program(),
        )["max_speech_packets"]
        == 2
    )


def test_live_phase_validator_also_refuses_native_contact_fit():
    values = _values(
        whole_roster_wave_barrier=True,
        live_phase_fit={
            "run_id": "live-fit-run",
            "attempt_id": "live-fit-attempt",
            "contact_cap": 1,
        },
    )

    with pytest.raises(PreparationError, match="mutually exclusive"):
        validate_live_phase_fit_config(values, _program())


def test_native_contact_fit_refuses_wrong_cap_before_lease_or_exposure(tmp_path):
    runtime = _Runtime(
        tmp_path,
        _values(
            native_contact_fit={
                "run_id": "fit-run",
                "attempt_id": "fit-attempt",
                "contact_cap": 15,
            }
        ),
    )

    with pytest.raises(PreparationError, match="cap must equal"):
        build_native_contact_fit_gate(runtime, _program(), _plan())

    assert runtime.lease_checks == 0
    assert runtime.touches == []
    assert runtime.unconsumed == []


def test_native_contact_fit_supports_registered_multi_packet_requests(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    monkeypatch.setattr(
        fitting,
        "packet_token_counts",
        lambda payload, **_kwargs: tuple(
            1 for _descriptor in payload["speech_feature_parts"]
        ),
    )
    runtime = _Runtime(
        tmp_path,
        _values(
            native_contact_fit={
                "run_id": "fit-run",
                "attempt_id": "fit-attempt",
                "contact_cap": 20,
                "max_speech_packets": 2,
            }
        ),
    )
    tokenizer = _Tokenizer()
    gate = build_native_contact_fit_gate(
        runtime,
        _program(),
        _plan(),
        client_factory=lambda **_kwargs: tokenizer,
    )

    gate(_prepared("s1", "two-packet-contact", speech_packets=2))

    assert gate.execution_plan.planned_model_calls == 20
    assert [(method, path) for method, path, _ in tokenizer.calls] == [
        ("GET", "/props"),
        ("POST", "/apply-template"),
        ("POST", "/tokenize"),
        ("POST", "/tokenize"),
        ("POST", "/tokenize"),
    ]
    artifact = json.loads(open(gate.receipts[0]["path"], encoding="utf-8").read())
    assert artifact["output"]["contacts"] == 5
    assert artifact["output"]["speech_packet_count"] == 2


@pytest.mark.parametrize("mode", ["over-bound", "descriptor-changed"])
def test_native_contact_fit_validates_rendered_descriptor_binding_before_contact(
    tmp_path, monkeypatch, mode
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = _Runtime(tmp_path)
    tokenizer = _Tokenizer()
    if mode == "descriptor-changed":
        original_render = runtime._transport.render_request

        def changed(raw):
            body = original_render(raw)
            body["messages"][0]["content"][1]["speech_features"]["sha256"] = "f" * 64
            return body

        runtime._transport.render_request = changed
    request = _prepared(
        "s1", "binding-contact", speech_packets=2 if mode == "over-bound" else 1
    )
    gate = build_native_contact_fit_gate(
        runtime,
        _program(),
        _plan(),
        client_factory=lambda **_kwargs: tokenizer,
    )

    with pytest.raises(PreparationError, match="descriptor"):
        gate(request)

    assert tokenizer.calls == []
    assert not list(tmp_path.rglob("*.contacts.jsonl"))


def test_native_contact_fit_freezes_roster_and_refuses_reuse_or_sample_overrun(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    tokenizer = _Tokenizer()
    runtime = _Runtime(tmp_path)
    gate = build_native_contact_fit_gate(
        runtime,
        _program(),
        _plan(),
        client_factory=lambda **_kwargs: tokenizer,
    )
    runtime._samples = (_Sample("replacement"),)

    with pytest.raises(PreparationError, match="registered roster"):
        gate(_prepared("replacement", "replacement-1"))
    gate(_prepared("s1", "globally-unique-1"))
    with pytest.raises(PreparationError, match="repeated agent_contact_id"):
        gate(_prepared("s2", "globally-unique-1"))
    gate(_prepared("s1", "globally-unique-2"))
    calls_after_ceiling = len(tokenizer.calls)
    with pytest.raises(PreparationError, match="per-sample contact ceiling"):
        gate(_prepared("s1", "globally-unique-3"))
    assert len(tokenizer.calls) == calls_after_ceiling


@pytest.mark.parametrize("failure", ["capacity", "endpoint"])
def test_native_contact_fit_preserves_failed_contact_journal_and_refuses_retry(
    tmp_path, monkeypatch, failure
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))

    class FailingTokenizer(_Tokenizer):
        def request_json(self, method, path, payload):
            if failure == "endpoint" and path == "/tokenize" and len(self.calls) == 3:
                self.calls.append((method, path, payload))
                raise RuntimeError("synthetic tokenizer failure")
            return super().request_json(method, path, payload)

    runtime = _Runtime(tmp_path)
    if failure == "capacity":
        runtime._adapter = SimpleNamespace(serving_geometry=lambda: {"slot_tokens": 1})
    tokenizer = FailingTokenizer()
    gate = build_native_contact_fit_gate(
        runtime,
        _program(),
        _plan(),
        client_factory=lambda **_kwargs: tokenizer,
    )
    request = _prepared("s1", "failed-contact")
    error = "exceed" if failure == "capacity" else "synthetic tokenizer failure"

    with pytest.raises((PreparationError, RuntimeError), match=error):
        gate(request)

    journals = list(tmp_path.rglob("*.contacts.jsonl"))
    assert len(journals) == 1
    assert len(journals[0].read_text().splitlines()) == 4
    calls_after_failure = len(tokenizer.calls)
    with pytest.raises(PreparationError, match="repeated agent_contact_id"):
        gate(request)
    assert len(tokenizer.calls) == calls_after_failure
    assert gate.receipts == []


def test_native_contact_fit_serializes_tokenizer_endpoints(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    state_lock = threading.Lock()
    active = 0
    maximum_active = 0

    class ObservedTokenizer(_Tokenizer):
        def request_json(self, method, path, payload):
            nonlocal active, maximum_active
            with state_lock:
                active += 1
                maximum_active = max(maximum_active, active)
            try:
                time.sleep(0.005)
                return super().request_json(method, path, payload)
            finally:
                with state_lock:
                    active -= 1

    gate = build_native_contact_fit_gate(
        _Runtime(tmp_path),
        _program(),
        _plan(),
        client_factory=lambda **kwargs: ObservedTokenizer(**kwargs),
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(gate, _prepared("s1", "s1-contact")),
            pool.submit(gate, _prepared("s2", "s2-contact")),
        ]
        for future in futures:
            future.result()

    assert maximum_active == 1
    assert len(gate.receipts) == 2


def test_native_raw_fit_budgets_and_observations_are_isolated_by_window(tmp_path):
    from types import MethodType
    from pathlib import Path
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
    from speech_aware_evidence_acquisition.core.model.slices import SliceRecord, SliceRegistry
    from speech_aware_evidence_acquisition.rails.execution_units import ExecutionUnit, ExecutionUnitRoster, execution_unit_scope

    runtime = _raw_runtime(tmp_path)
    runtime._samples = (_Sample("s1"),)
    parent = tmp_path / "media/s1.wav"
    parent.parent.mkdir(parents=True)
    parent.write_bytes(b"RIFF original two-second parent")
    registry = SliceRegistry(
        data_root=tmp_path, run_id="source-inventory",
        parent_facts={"s1": ("media/s1.wav", 2.0)},
    )
    units = []
    for index in range(2):
        relpath = registry.slice_relpath("s1", index)
        path = tmp_path / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = f"RIFF window {index}".encode()
        path.write_bytes(raw)
        record = registry.register(SliceRecord(
            sample_id="s1", parent_media_relpath="media/s1.wav",
            parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
            start_seconds=float(index), end_seconds=float(index + 1),
            audio_seconds=1.0, sample_rate_hz=16000,
            media_relpath=relpath, sha256=hashlib.sha256(raw).hexdigest(),
            bytes=len(raw), iteration=index,
        ))
        units.append(ExecutionUnit("s1", f"s1#w{index + 1:04d}", record))
    roster = ExecutionUnitRoster(tuple(units))
    runtime.execution_unit_roster = lambda: roster
    runtime._execution_unit_registry = registry
    runtime.execution_unit_for_contact = MethodType(FlightRuntime.execution_unit_for_contact, runtime)
    runtime.validate_execution_unit_observation = MethodType(FlightRuntime.validate_execution_unit_observation, runtime)
    tokenizer = _RawTokenizer()
    gate = build_native_contact_fit_gate(runtime, _program(), _plan(),
        client_factory=lambda **_kwargs: tokenizer)
    assert gate.execution_plan.planned_model_calls == 4

    def request(index, contact_index, source_index=None):
        unit = units[index]
        source = units[index if source_index is None else source_index].slice_record
        raw = (tmp_path / source.media_relpath).read_bytes()
        runtime._transport.raw = raw
        contact = execution_unit_scope(unit.request_key) + f"/role:{contact_index}"
        payload = _raw_prepared("s1", contact, raw).as_payload()
        payload["media_relpath"] = source.media_relpath
        payload["raw_speech_query"]["media_relpath"] = source.media_relpath
        return PreparedCoreRequest(canonical_bytes(payload), object())

    gate(request(0, 1))
    with pytest.raises(FlightRuntimeError, match="(window|unit)"):
        gate(request(0, 2, source_index=1))
    assert len(tokenizer.calls) == 1
    gate(request(0, 2))
    with pytest.raises(PreparationError, match="per-unit contact ceiling"):
        gate(request(0, 3))
    assert len(tokenizer.calls) == 2
    gate(request(1, 1))
    gate(request(1, 2))
    assert len(tokenizer.calls) == 4
    assert [json.loads(Path(receipt["path"]).read_text())["inputs"]["native_contact"]["execution_unit_id"]
            for receipt in gate.receipts] == ["s1#w0001", "s1#w0001", "s1#w0002", "s1#w0002"]
