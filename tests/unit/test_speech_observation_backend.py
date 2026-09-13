"""Fake-only contract tests for the bounded local Whisper backend."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core import speech_observation_backend as backend


SHA = "a" * 64


def inventory():
    return {
        "schema": "saea-local-whisper-backend-inventory-v1",
        "model": "large-v3",
        "checkpoint_path": "/verified/large-v3.pt",
        "checkpoint_sha256": SHA,
        "whisper_source_path": "/verified/openai-whisper-20250625",
    }


def protocol(**changes):
    values = {
        "schema": "saea-local-whisper-decode-v1",
        "device": "cuda:0",
        "cpu_workers": 2,
        "batch_size": 3,
        "language": "en",
        "task": "transcribe",
        "temperature": 0,
        "beam_size": 5,
        "sample_len": 12,
        "without_timestamps": True,
        "fp16": True,
        "no_speech_threshold": 0.6,
        "logprob_threshold": -1.0,
    }
    values.update(changes)
    return values


def source(name="one", *, frames=16000, start_frame=0, end_frame=None):
    if end_frame is None:
        end_frame = frames
    return {
        "media_path": f"/verified/{name}.flac",
        "audio_sha256": SHA,
        "verified_fingerprint": (1, 2, 3),
        "source_frames": frames,
        "source_sample_rate_hz": 16000,
        "start_frame": start_frame,
        "end_frame": end_frame,
    }


class FakePrefetch:
    instances = []

    def __init__(self, workers):
        self.workers = workers
        self.prepared = []
        self.closed = False
        self.__class__.instances.append(self)

    def prepare_sources(self, sources):
        self.prepared = list(sources)

    def take(self, item):
        assert item in self.prepared
        return [item["media_path"]] * (item["end_frame"] - item["start_frame"])

    def close(self):
        self.closed = True


class FakeTensor:
    def __init__(self, value, *, ndim=2, shape=(128, 3000)):
        self.value = value
        self.ndim = ndim
        self.shape = shape
        self.moves = []

    def to(self, device):
        self.moves.append(device)
        return self


@dataclass
class FakeResult:
    text: str
    tokens: list[int]
    avg_logprob: float
    no_speech_prob: float
    temperature: float = 0.0
    compression_ratio: float = 1.1
    language: str = "en"
    language_probs: object = None
    audio_features: object = None


def fake_stack(results, calls):
    class Options:
        def __init__(self, **kwargs):
            calls["options"] = kwargs

    def mel(wave, n_mels):
        calls.setdefault("mels", []).append((wave[0], len(wave), n_mels))
        return FakeTensor(wave[0])

    class PaddedWave:
        def __init__(self, value, length):
            self.value, self.length = value, length

        def __len__(self):
            return self.length

        def __getitem__(self, _index):
            return self.value

    def trim(value, length):
        calls.setdefault("pads", []).append((value[0], len(value), length))
        return PaddedWave(value[0], length)

    def decode(model, batch, options):
        calls["decode"] = (model, batch, options)
        return results

    whisper = SimpleNamespace(DecodingOptions=Options, decode=decode)
    audio = SimpleNamespace(
        log_mel_spectrogram=mel,
        pad_or_trim=trim,
        N_FRAMES=3000,
        N_SAMPLES=480000,
    )
    torch = SimpleNamespace(stack=lambda mels: FakeTensor([mel.value for mel in mels], ndim=3))
    model = SimpleNamespace(
        dims=SimpleNamespace(n_mels=128, n_text_ctx=16),
        is_multilingual=True,
        num_languages=100,
    )
    tokenizer = SimpleNamespace(
        get_tokenizer=lambda *_args, **_kwargs: SimpleNamespace(
            sot_sequence_including_notimestamps=(1, 2, 3, 4)
        )
    )
    return whisper, audio, torch, tokenizer, model


def test_native_batch_is_ordered_lazy_and_retains_bounded_diagnostics(monkeypatch):
    calls, events = {}, []
    results = [
        FakeResult("  first transcript  ", [1, 2], -0.2, 0.95),
        FakeResult("low confidence", [3], -1.2, 0.7),
        FakeResult("hit output cap", list(range(12)), -0.1, 0.0),
    ]
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(
        backend,
        "_load_whisper_stack",
        lambda actual_inventory, actual_protocol: (
            calls.setdefault("loads", []).append((actual_inventory, actual_protocol))
            or fake_stack(results, calls)
        ),
    )
    worker = backend.LocalWhisperBackend(inventory(), protocol(), "/unused", events.append)
    sources = [source("one"), source("two"), source("three")]
    worker.prepare_sources(sources)
    outputs = worker.decode_batch(sources)

    assert len(calls["loads"]) == 1
    assert calls["decode"][1].value == ["/verified/one.flac", "/verified/two.flac", "/verified/three.flac"]
    assert calls["decode"][1].moves == ["cuda:0"]
    assert calls["pads"] == [
        ("/verified/one.flac", 16000, 480000),
        ("/verified/two.flac", 16000, 480000),
        ("/verified/three.flac", 16000, 480000),
    ]
    assert calls["mels"] == [
        ("/verified/one.flac", 480000, 128),
        ("/verified/two.flac", 480000, 128),
        ("/verified/three.flac", 480000, 128),
    ]
    assert calls["options"] == {
        "language": "en", "task": "transcribe", "temperature": 0,
        "beam_size": 5, "sample_len": 12, "without_timestamps": True,
        "fp16": True, "prompt": None, "prefix": None,
    }
    assert [item["status"] for item in outputs] == ["ok", "empty", "unsupported"]
    assert [item["transcript"] for item in outputs] == ["first transcript", "", ""]
    assert outputs[0]["diagnostics"]["raw_text"] == "  first transcript  "
    assert outputs[2]["diagnostics"]["tokens"] == list(range(12))
    assert events == [
        "model_load_started", "model_load_finished",
        "data_wait_started", "data_wait_finished",
        "data_wait_started", "data_wait_finished",
        "data_wait_started", "data_wait_finished",
        "mel_started", "mel_finished",
        "speech_tool_forward_started", "speech_tool_forward_finished",
    ]

    # High no-speech alone does not erase a high-quality decoded result.
    assert outputs[0]["status"] == "ok"
    worker.close()
    assert FakePrefetch.instances[-1].closed


def test_singleton_delegates_and_model_loads_only_once(monkeypatch):
    calls = {}
    results = [FakeResult("answer", [1], -0.1, 0.0)]
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(
        backend, "_load_whisper_stack",
        lambda *_: fake_stack(results, calls),
    )
    worker = backend.LocalWhisperBackend(inventory(), protocol(batch_size=1), "/unused", lambda _: None)
    item = source()
    worker.prepare_sources([item])
    assert worker(item)["transcript"] == "answer"


@pytest.mark.parametrize(
    "bad_protocol,match",
    [
        ({**protocol(), "initial_prompt": "forbidden"}, "unknown fields"),
        (protocol(language=None), "language"),
        (protocol(task="translate"), "task"),
        (protocol(temperature=0.1), "temperature"),
        (protocol(without_timestamps=False), "without_timestamps"),
    ],
)
def test_protocol_refuses_unbound_or_context_bearing_options(bad_protocol, match):
    with pytest.raises(backend.SpeechObservationBackendError, match=match):
        backend.LocalWhisperBackend(inventory(), bad_protocol, "/unused", lambda _: None)


def test_duration_and_batch_bounds_fail_before_prefetch_or_model_load(monkeypatch):
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    worker = backend.LocalWhisperBackend(inventory(), protocol(batch_size=1), "/unused", lambda _: None)
    too_long = source(frames=480001)
    with pytest.raises(backend.SpeechObservationBackendError, match="30 seconds"):
        worker.prepare_sources([too_long])
    assert FakePrefetch.instances[-1].prepared == []
    with pytest.raises(backend.SpeechObservationBackendError, match="full utterance"):
        worker.prepare_sources([source(start_frame=1)])
    with pytest.raises(backend.SpeechObservationBackendError, match="batch_size"):
        worker.decode_batch([source("one"), source("two")])


def test_sample_len_must_fit_decoder_context_before_forward(monkeypatch):
    calls, events = {}, []
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(
        backend, "_load_whisper_stack",
        lambda *_: fake_stack([FakeResult("unused", [1], -0.1, 0.0)], calls),
    )
    worker = backend.LocalWhisperBackend(
        inventory(), protocol(batch_size=1, sample_len=13), "/unused", events.append
    )
    item = source()
    worker.prepare_sources([item])
    with pytest.raises(backend.SpeechObservationBackendError, match="decoder context"):
        worker.decode_batch([item])
    assert "speech_tool_forward_started" not in events


def test_cpu_protocol_requires_fp32_before_any_eager_work(monkeypatch):
    created = []

    class RefusingPrefetch:
        def __init__(self, _workers):
            created.append(True)

    monkeypatch.setattr(backend, "BoundedAudioPrefetch", RefusingPrefetch)
    with pytest.raises(backend.SpeechObservationBackendError, match="fp16"):
        backend.LocalWhisperBackend(
            inventory(), protocol(device="cpu", fp16=True), "/unused", lambda _: None
        )
    assert created == []


def test_cpu_decode_propagates_cpu_device_and_fp32_without_eager_work(monkeypatch):
    calls, events = {}, []
    results = [FakeResult("cpu transcript", [1], -0.1, 0.0)]
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(
        backend,
        "_load_whisper_stack",
        lambda actual_inventory, actual_protocol: (
            calls.setdefault("loads", []).append((actual_inventory, actual_protocol))
            or fake_stack(results, calls)
        ),
    )
    worker = backend.LocalWhisperBackend(
        inventory(), protocol(device="cpu", fp16=False, batch_size=1),
        "/unused", events.append,
    )
    assert calls == {}
    assert events == []
    assert FakePrefetch.instances[-1].prepared == []

    item = source()
    worker.prepare_sources([item])
    output = worker(item)

    assert output["transcript"] == "cpu transcript"
    assert calls["loads"][0][1]["device"] == "cpu"
    assert calls["decode"][1].moves == ["cpu"]
    assert calls["options"]["fp16"] is False


@pytest.mark.parametrize("device", ["cuda", "cuda:0"])
def test_existing_cuda_device_and_fp16_contract_remains_valid(monkeypatch, device):
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    worker = backend.LocalWhisperBackend(
        inventory(), protocol(device=device, fp16=True), "/unused", lambda _: None
    )
    assert worker.protocol["device"] == device
    assert worker.protocol["fp16"] is True
