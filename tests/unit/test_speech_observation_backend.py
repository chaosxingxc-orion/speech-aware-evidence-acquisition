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


def bounded_cpu_protocol(**changes):
    values = protocol(
        device="cpu",
        cpu_workers=2,
        batch_size=1,
        sample_len=256,
        fp16=False,
        cpu_thread_limits={"inference_threads": 5, "interop_threads": 1},
    )
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


class FakeTorchThreads:
    def __init__(self, events, *, refuse=None, apply=True):
        self.events = events
        self.refuse = refuse
        self.apply = apply
        self.inference_threads = 97
        self.interop_threads = 89

    def set_num_threads(self, value):
        self.events.append(("set_num_threads", value))
        if self.refuse == "inference":
            raise RuntimeError("synthetic inference refusal")
        if self.apply:
            self.inference_threads = value

    def set_num_interop_threads(self, value):
        self.events.append(("set_num_interop_threads", value))
        if self.refuse == "interop":
            raise RuntimeError("synthetic interop refusal")
        if self.apply:
            self.interop_threads = value

    def get_num_threads(self):
        self.events.append(("get_num_threads", self.inference_threads))
        return self.inference_threads

    def get_num_interop_threads(self):
        self.events.append(("get_num_interop_threads", self.interop_threads))
        return self.interop_threads


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


def fake_imports(monkeypatch, torch, events):
    class FakeModel:
        def eval(self):
            events.append(("model_eval", None))
            return self

    def load_model(path, *, device, in_memory):
        events.append(("load_model", (path, device, in_memory)))
        return FakeModel()

    source = inventory()["whisper_source_path"]
    modules = {
        "whisper": SimpleNamespace(
            __file__=source + "/whisper/__init__.py", load_model=load_model
        ),
        "whisper.audio": SimpleNamespace(),
        "whisper.tokenizer": SimpleNamespace(),
        "torch": torch,
    }
    monkeypatch.setattr(
        backend.importlib, "import_module", lambda name: modules[name]
    )


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


def test_bounded_span_protocol_preserves_registered_selected_frames(monkeypatch):
    calls = {}
    selected = source("selected", frames=480000, start_frame=16000, end_frame=32000)
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(
        backend,
        "_load_whisper_stack",
        lambda *_: fake_stack([FakeResult("selected", [1], -0.1, 0.0)], calls),
    )
    worker = backend.LocalWhisperBackend(
        inventory(), protocol(batch_size=1, source_selection="bounded-span-v1"),
        "/unused", lambda _: None,
    )

    worker.prepare_sources([selected])
    assert FakePrefetch.instances[-1].prepared == [selected]
    assert worker.decode_batch([selected])[0]["transcript"] == "selected"
    assert calls["pads"] == [("/verified/selected.flac", 16000, 480000)]
    assert calls["mels"] == [("/verified/selected.flac", 480000, 128)]


def test_bounded_span_protocol_keeps_decode_selected_source_geometry(monkeypatch):
    calls = {}
    selected = source("selected", frames=480000, start_frame=32000, end_frame=64000)
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(
        backend,
        "_load_whisper_stack",
        lambda *_: fake_stack([FakeResult("selected", [1], -0.1, 0.0)], calls),
    )
    worker = backend.LocalWhisperBackend(
        inventory(), protocol(batch_size=1, source_selection="bounded-span-v1"),
        "/unused", lambda _: None,
    )

    assert worker.decode_selected(selected)["transcript"] == "selected"
    assert FakePrefetch.instances[-1].prepared == [selected]
    assert calls["pads"] == [("/verified/selected.flac", 32000, 480000)]
    assert FakePrefetch.instances[-1].closed


@pytest.mark.parametrize(
    "selected",
    [
        source("negative", start_frame=-1, end_frame=1),
        source("empty", start_frame=10, end_frame=10),
        source("outside", start_frame=0, end_frame=16001),
        source("oversize", frames=480001, start_frame=0, end_frame=480001),
    ],
)
def test_bounded_span_protocol_refuses_invalid_or_oversize_geometry(monkeypatch, selected):
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    worker = backend.LocalWhisperBackend(
        inventory(), protocol(batch_size=1, source_selection="bounded-span-v1"),
        "/unused", lambda _: None,
    )
    with pytest.raises(backend.SpeechObservationBackendError):
        worker.prepare_sources([selected])
    assert FakePrefetch.instances[-1].prepared == []


@pytest.mark.parametrize("selection", ["full-utterance-v1", None, True])
def test_source_selection_only_accepts_bounded_span_v1(selection):
    with pytest.raises(backend.SpeechObservationBackendError, match="source_selection"):
        backend.LocalWhisperBackend(
            inventory(), protocol(source_selection=selection), "/unused", lambda _: None
        )


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


@pytest.mark.parametrize(
    "limits,protocol_changes,match",
    [
        (None, {}, "must be an object"),
        ({"inference_threads": 5}, {}, "lacks fields"),
        (
            {"inference_threads": 5, "interop_threads": 1, "extra": 1},
            {},
            "unknown fields",
        ),
        ({"inference_threads": True, "interop_threads": 1}, {}, "positive integer"),
        ({"inference_threads": 5, "interop_threads": 0}, {}, "positive integer"),
        (
            {"inference_threads": 5, "interop_threads": 1},
            {"device": "cuda:0", "fp16": True},
            "require device='cpu'",
        ),
        (
            {"inference_threads": 6, "interop_threads": 1},
            {},
            "exceeds eight workers",
        ),
    ],
)
def test_cpu_thread_envelope_refuses_before_eager_work(
    monkeypatch, limits, protocol_changes, match
):
    created = []

    class RefusingPrefetch:
        def __init__(self, _workers):
            created.append(True)

    monkeypatch.setattr(backend, "BoundedAudioPrefetch", RefusingPrefetch)
    configured = bounded_cpu_protocol(
        cpu_thread_limits=limits, **protocol_changes
    )
    with pytest.raises(backend.SpeechObservationBackendError, match=match):
        backend.LocalWhisperBackend(
            inventory(), configured, "/unused", lambda _: None
        )
    assert created == []


def test_cpu_thread_limits_apply_once_before_lazy_model_load(monkeypatch):
    events = []
    torch = FakeTorchThreads(events)
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(backend, "_APPLIED_CPU_THREAD_LIMITS", None)
    fake_imports(monkeypatch, torch, events)

    first = backend.LocalWhisperBackend(
        inventory(), bounded_cpu_protocol(), "/unused", lambda _: None
    )
    second = backend.LocalWhisperBackend(
        inventory(), bounded_cpu_protocol(), "/unused", lambda _: None
    )
    assert events == []

    first._ensure_stack()
    first._ensure_stack()
    second._ensure_stack()

    assert [event for event in events if event[0] == "set_num_threads"] == [
        ("set_num_threads", 5)
    ]
    assert [event for event in events if event[0] == "set_num_interop_threads"] == [
        ("set_num_interop_threads", 1)
    ]
    load_positions = [
        index for index, event in enumerate(events) if event[0] == "load_model"
    ]
    assert len(load_positions) == 2
    assert events.index(("set_num_threads", 5)) < load_positions[0]
    assert events.index(("set_num_interop_threads", 1)) < load_positions[0]


def test_changed_cpu_thread_limits_are_refused_before_second_load(monkeypatch):
    events = []
    torch = FakeTorchThreads(events)
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(backend, "_APPLIED_CPU_THREAD_LIMITS", None)
    fake_imports(monkeypatch, torch, events)
    backend.LocalWhisperBackend(
        inventory(), bounded_cpu_protocol(), "/unused", lambda _: None
    )._ensure_stack()

    changed = bounded_cpu_protocol(
        cpu_thread_limits={"inference_threads": 4, "interop_threads": 1}
    )
    with pytest.raises(
        backend.SpeechObservationBackendError, match="configured.*drifted"
    ):
        backend.LocalWhisperBackend(
            inventory(), changed, "/unused", lambda _: None
        )._ensure_stack()
    assert len([event for event in events if event[0] == "load_model"]) == 1


def test_observed_torch_thread_drift_is_refused(monkeypatch):
    events = []
    torch = FakeTorchThreads(events)
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(backend, "_APPLIED_CPU_THREAD_LIMITS", None)
    fake_imports(monkeypatch, torch, events)
    backend.LocalWhisperBackend(
        inventory(), bounded_cpu_protocol(), "/unused", lambda _: None
    )._ensure_stack()
    torch.inference_threads = 4

    with pytest.raises(
        backend.SpeechObservationBackendError, match="drifted after application"
    ):
        backend.LocalWhisperBackend(
            inventory(), bounded_cpu_protocol(), "/unused", lambda _: None
        )._ensure_stack()
    assert len([event for event in events if event[0] == "load_model"]) == 1


def test_loaded_backend_refuses_thread_drift_before_next_decode(monkeypatch):
    calls, events = {}, []
    results = [FakeResult("unused", [1], -0.1, 0.0)]
    torch = FakeTorchThreads(events)
    torch.inference_threads = 5
    torch.interop_threads = 1
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(backend, "_APPLIED_CPU_THREAD_LIMITS", (5, 1))
    worker = backend.LocalWhisperBackend(
        inventory(), bounded_cpu_protocol(), "/unused", lambda _: None
    )
    loaded = list(fake_stack(results, calls))
    loaded[2] = torch
    worker.stack = tuple(loaded)
    item = source()
    worker.prepare_sources([item])
    torch.inference_threads = 4

    with pytest.raises(
        backend.SpeechObservationBackendError, match="drifted after application"
    ):
        worker.decode_batch([item])
    assert "decode" not in calls
    assert not [event for event in events if event[0].startswith("set_num")]


@pytest.mark.parametrize("refuse", ["inference", "interop"])
def test_torch_thread_limit_application_failure_is_not_silent(monkeypatch, refuse):
    events = []
    torch = FakeTorchThreads(events, refuse=refuse)
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(backend, "_APPLIED_CPU_THREAD_LIMITS", None)
    fake_imports(monkeypatch, torch, events)

    with pytest.raises(backend.SpeechObservationBackendError, match="Torch refused"):
        backend.LocalWhisperBackend(
            inventory(), bounded_cpu_protocol(), "/unused", lambda _: None
        )._ensure_stack()
    assert not [event for event in events if event[0] == "load_model"]


def test_torch_thread_limit_mismatch_after_set_is_refused(monkeypatch):
    events = []
    torch = FakeTorchThreads(events, apply=False)
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(backend, "_APPLIED_CPU_THREAD_LIMITS", None)
    fake_imports(monkeypatch, torch, events)

    with pytest.raises(
        backend.SpeechObservationBackendError, match="differ after application"
    ):
        backend.LocalWhisperBackend(
            inventory(), bounded_cpu_protocol(), "/unused", lambda _: None
        )._ensure_stack()
    assert not [event for event in events if event[0] == "load_model"]


def test_legacy_protocol_does_not_require_or_apply_torch_thread_controls(monkeypatch):
    events = []
    torch = SimpleNamespace()
    monkeypatch.setattr(backend, "BoundedAudioPrefetch", FakePrefetch)
    monkeypatch.setattr(backend, "_APPLIED_CPU_THREAD_LIMITS", None)
    fake_imports(monkeypatch, torch, events)

    worker = backend.LocalWhisperBackend(
        inventory(), protocol(device="cpu", fp16=False, batch_size=1),
        "/unused", lambda _: None,
    )
    worker._ensure_stack()
    assert [event[0] for event in events] == ["load_model", "model_eval"]


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


def test_decode_selected_reuses_loaded_stack_and_closes_each_small_prefetch(monkeypatch):
    calls = {}
    results = [FakeResult("selected", [1], -0.1, 0.0)]
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
        "/unused", lambda _: None,
    )
    assert worker.decode_selected(source("one"))["transcript"] == "selected"
    assert worker.decode_selected(source("two"))["transcript"] == "selected"

    assert len(calls["loads"]) == 1
    assert all(item.closed for item in FakePrefetch.instances[-2:])
    assert worker.stack is not None
    worker.close()
