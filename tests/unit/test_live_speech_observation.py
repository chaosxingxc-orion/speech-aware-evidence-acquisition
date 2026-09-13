"""Fake-only tests for model-selected local speech observations."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from threading import Barrier, Lock, Thread
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import live_speech_observation as live
from speech_aware_evidence_acquisition.rails.live_speech_observation import (
    LIVE_RESULT_SCHEMA,
    LIVE_SELECTION_SCHEMA,
    LiveSpeechObservationError,
    LiveSpeechObservationProvider,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def inventory(**changes):
    value = {
        "schema": "saea-local-whisper-backend-inventory-v1",
        "model": "large-v3",
        "checkpoint_path": "/verified/large-v3.pt",
        "checkpoint_sha256": SHA_A,
        "whisper_source_path": "/verified/whisper",
    }
    value.update(changes)
    return value


def protocol(**changes):
    value = {
        "schema": "saea-local-whisper-decode-v1",
        "device": "cpu",
        "cpu_workers": 2,
        "batch_size": 1,
        "language": "en",
        "task": "transcribe",
        "temperature": 0,
        "beam_size": 5,
        "sample_len": 224,
        "without_timestamps": True,
        "fp16": False,
        "no_speech_threshold": 0.6,
        "logprob_threshold": -1.0,
    }
    value.update(changes)
    return value


def binding(**changes):
    value = {
        "packet_id": "packet/s1",
        "packet_sha256": SHA_B,
        "source_audio_relpath": "audio/s1.flac",
        "source_audio_sha256": SHA_A,
        "source_audio_duration_seconds": 1.0,
    }
    value.update(changes)
    return value


def arguments(**changes):
    value = {
        "span": "full-utterance",
        "representation": "asr-transcript",
        "distinction": "Resolve uncertain words and entity values.",
    }
    value.update(changes)
    return value


def context(sample_id="s1"):
    query = SimpleNamespace(
        query_sample_id=sample_id,
        speech_packet_id="packet/s1",
        speech_packet_sha256=SHA_B,
    )
    return SimpleNamespace(sample_id=sample_id, query_state=query)


def resolved_source(source_binding):
    return {
        "media_path": "/data/" + source_binding["source_audio_relpath"],
        "audio_sha256": source_binding["source_audio_sha256"],
        "verified_fingerprint": (1, 2, 3),
        "source_frames": 16000,
        "source_sample_rate_hz": 16000,
        "start_frame": 0,
        "end_frame": 16000,
    }


class FakeBackend:
    def __init__(self, calls, *, fail=False, event=None):
        self.calls = calls
        self.fail = fail
        self.event = event or (lambda _phase: None)
        self.closed = False

    def decode_selected(self, source):
        self.calls.append(("decode", dict(source)))
        self.event("speech_tool_forward_started")
        if self.fail:
            raise RuntimeError("synthetic backend failure")
        return {
            "schema": "saea-prepared-speech-observation-v1",
            "status": "ok",
            "transcript": "turn on the kitchen lights",
            "diagnostics": {"raw_text": " turn on the kitchen lights "},
        }

    def close(self):
        self.closed = True


def make_provider(tmp_path, events, *, backend_fail=False, protocol_value=None):
    backend_holder = {}

    def contact(**facts):
        events.append(("contact", facts))
        return {"contact_id": f"speech-{len(events)}", "ordinal": len(events)}

    def guard():
        events.append(("guard", None))

    def resolver(source_binding):
        events.append(("source", dict(source_binding)))
        return resolved_source(source_binding)

    def factory(actual_inventory, actual_protocol, data_root, event):
        events.append(("backend", (actual_inventory, actual_protocol, data_root, event)))
        worker = FakeBackend(events, fail=backend_fail, event=event)
        backend_holder["value"] = worker
        return worker

    provider = LiveSpeechObservationProvider(
        inventory=inventory(),
        protocol=protocol_value or protocol(),
        source_bindings={"s1": binding()},
        data_root=tmp_path,
        output_root=tmp_path / "live-observations",
        contact=contact,
        backend_factory=factory,
        host_memory_guard=guard,
        source_resolver=resolver,
    )
    return provider, backend_holder


def test_constructor_and_no_call_path_perform_zero_work(tmp_path):
    events = []
    provider, _ = make_provider(tmp_path, events)
    assert events == []
    assert not (tmp_path / "live-observations").exists()
    assert provider.receipt() == {
        "schema": "saea-live-speech-observation-provider-receipt-v1",
        "invocations": 0,
        "cache_hits": 0,
        "new_forwards": 0,
        "failures": 0,
        "artifacts": [],
    }


def test_first_selected_call_debits_before_guard_audio_and_decode(tmp_path):
    events = []
    provider, _ = make_provider(tmp_path, events)
    selection = provider.observe(
        context=context(), arguments=arguments(), source_response_sha256=SHA_B
    )

    assert [event[0] for event in events] == [
        "guard", "contact", "source", "backend", "decode"
    ]
    assert selection.visible["schema"] == LIVE_SELECTION_SCHEMA
    assert selection.visible["transcript"] == "turn on the kitchen lights"
    assert selection.visible["speech_packet_id"] == "packet/s1"
    assert selection.lineage["schema"] == "saea-live-speech-observation-lineage-v1"
    assert selection.lineage["contact"]["contact_id"] == "speech-2"
    assert selection.lineage["producer_contact"] == selection.lineage["contact"]
    assert selection.lineage["resolved_source"]["source_frames"] == 16000
    assert selection.lineage["cache"] == "cold"
    artifact = json.loads(Path(selection.lineage["artifact_path"]).read_text())
    assert artifact["output"]["schema"] == LIVE_RESULT_SCHEMA
    assert artifact["output"]["backend_output"]["diagnostics"]["raw_text"].startswith(" ")
    assert provider.receipt()["new_forwards"] == 1


def test_identical_source_and_protocol_reuse_cache_without_contact_or_decode(tmp_path):
    events = []
    provider, _ = make_provider(tmp_path, events)
    first = provider.observe(
        context=context(), arguments=arguments(), source_response_sha256=SHA_B
    )
    event_count = len(events)
    second = provider.observe(
        context=context(), arguments=arguments(), source_response_sha256=SHA_A
    )

    assert len(events) == event_count
    assert second.visible == first.visible
    assert second.lineage["cache"] == "warm"
    assert "contact" not in second.lineage
    assert provider.receipt()["invocations"] == 2
    assert provider.receipt()["cache_hits"] == 1
    assert provider.receipt()["new_forwards"] == 1


@pytest.mark.parametrize(
    "changed_binding,changed_protocol",
    [
        (binding(source_audio_sha256=SHA_B), None),
        (None, protocol(sample_len=128)),
    ],
)
def test_changed_source_or_protocol_cannot_false_hit(
    tmp_path, changed_binding, changed_protocol
):
    events = []
    provider, _ = make_provider(tmp_path, events)
    first = provider.observe(
        context=context(), arguments=arguments(), source_response_sha256=SHA_A
    )
    provider.close()

    second_events = []
    second, _ = make_provider(
        tmp_path, second_events, protocol_value=changed_protocol or protocol()
    )
    if changed_binding is not None:
        second.source_bindings["s1"] = changed_binding
    second_result = second.observe(
        context=context(), arguments=arguments(), source_response_sha256=SHA_A
    )
    assert first.lineage["artifact_sha256"] != second_result.lineage["artifact_sha256"]
    assert [event[0] for event in second_events[:2]] == ["guard", "contact"]


def test_concurrent_identical_calls_decode_once(tmp_path):
    events = []
    provider, _ = make_provider(tmp_path, events)
    barrier = Barrier(3)
    results, failures = [], []
    result_lock = Lock()

    def run():
        barrier.wait()
        try:
            value = provider.observe(
                context=context(), arguments=arguments(), source_response_sha256=SHA_A
            )
            with result_lock:
                results.append(value)
        except Exception as error:  # pragma: no cover - asserted empty
            failures.append(error)

    threads = [Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert failures == []
    assert len(results) == 2
    assert [event[0] for event in events].count("contact") == 1
    assert [event[0] for event in events].count("decode") == 1
    assert provider.receipt()["cache_hits"] == 1


def test_contact_failure_prevents_source_read_and_backend(tmp_path):
    events = []

    def contact(**_facts):
        events.append("contact")
        raise RuntimeError("budget closed")

    provider = LiveSpeechObservationProvider(
        inventory=inventory(), protocol=protocol(), source_bindings={"s1": binding()},
        data_root=tmp_path, output_root=tmp_path / "live", contact=contact,
        backend_factory=lambda *_args: events.append("backend"),
        host_memory_guard=lambda: events.append("guard"),
        source_resolver=lambda _binding: events.append("source"),
    )
    with pytest.raises(RuntimeError, match="budget closed"):
        provider.observe(
            context=context(), arguments=arguments(), source_response_sha256=SHA_A
        )
    assert events == ["guard", "contact"]


def test_backend_failure_is_charged_and_start_marker_prevents_replay(tmp_path):
    events = []
    provider, _ = make_provider(tmp_path, events, backend_fail=True)
    with pytest.raises(RuntimeError, match="synthetic backend failure"):
        provider.observe(
            context=context(), arguments=arguments(), source_response_sha256=SHA_A
        )
    first_events = list(events)
    with pytest.raises(Exception, match="prior speech-tool preparation"):
        provider.observe(
            context=context(), arguments=arguments(), source_response_sha256=SHA_A
        )
    assert events == first_events
    receipt = provider.receipt()
    assert receipt["new_forwards"] == 1
    assert receipt["failures"] == 2


@pytest.mark.parametrize(
    "bad_arguments,match",
    [
        (arguments(span={"start": 0}), "full-utterance"),
        (arguments(representation="path"), "asr-transcript"),
        (arguments(distinction=""), "distinction"),
        ({**arguments(), "media_path": "/other.wav"}, "exactly"),
    ],
)
def test_arguments_refuse_paths_and_unbound_spans_before_contact(
    tmp_path, bad_arguments, match
):
    events = []
    provider, _ = make_provider(tmp_path, events)
    with pytest.raises(LiveSpeechObservationError, match=match):
        provider.observe(
            context=context(), arguments=bad_arguments, source_response_sha256=SHA_A
        )
    assert events == []


def test_context_and_packet_binding_are_exact(tmp_path):
    events = []
    provider, _ = make_provider(tmp_path, events)
    bad = context()
    bad.query_state.speech_packet_sha256 = SHA_A
    with pytest.raises(LiveSpeechObservationError, match="packet"):
        provider.observe(
            context=bad, arguments=arguments(), source_response_sha256=SHA_A
        )
    assert events == []


def test_two_selected_sources_reuse_one_backend_and_one_memory_guard(tmp_path):
    events = []

    def contact(**facts):
        events.append(("contact", facts["sample_id"]))
        return {"contact_id": "contact-" + facts["sample_id"]}

    provider = LiveSpeechObservationProvider(
        inventory=inventory(),
        protocol=protocol(),
        source_bindings={
            "s1": binding(),
            "s2": binding(
                packet_id="packet/s2",
                source_audio_relpath="audio/s2.flac",
                source_audio_sha256=SHA_B,
            ),
        },
        data_root=tmp_path,
        output_root=tmp_path / "live",
        contact=contact,
        backend_factory=lambda *_args: (
            events.append(("backend", None)) or FakeBackend(events, event=_args[-1])
        ),
        host_memory_guard=lambda: events.append(("guard", None)),
        source_resolver=lambda source_binding: resolved_source(source_binding),
    )
    provider.observe(
        context=context(), arguments=arguments(), source_response_sha256=SHA_A
    )
    second_context = SimpleNamespace(
        sample_id="s2",
        query_state=SimpleNamespace(
            query_sample_id="s2",
            speech_packet_id="packet/s2",
            speech_packet_sha256=SHA_B,
        ),
    )
    provider.observe(
        context=second_context, arguments=arguments(), source_response_sha256=SHA_B
    )

    assert [event[0] for event in events].count("guard") == 1
    assert [event[0] for event in events].count("backend") == 1
    assert [event[0] for event in events].count("decode") == 2
    assert provider.receipt()["new_forwards"] == 2


@pytest.mark.parametrize(
    "provider_changes,match",
    [
        ({"protocol": protocol(device="cuda", fp16=True)}, "requires CPU"),
        ({"protocol": protocol(fp16=True)}, "fp16"),
        ({"source_bindings": {}}, "source bindings"),
        ({"source_bindings": {"s1": binding(source_audio_duration_seconds=31)}}, "30 seconds"),
        ({"source_bindings": {"s1": binding(source_audio_relpath="../escape.wav")}}, "confined"),
        ({"contact": None}, "contact callback"),
    ],
)
def test_constructor_refuses_non_cpu_or_unbound_inputs(
    tmp_path, provider_changes, match
):
    values = {
        "inventory": inventory(),
        "protocol": protocol(),
        "source_bindings": {"s1": binding()},
        "data_root": tmp_path,
        "output_root": tmp_path / "live",
        "contact": lambda **_facts: {},
    }
    values.update(provider_changes)
    with pytest.raises(LiveSpeechObservationError, match=match):
        LiveSpeechObservationProvider(**values)


def test_unknown_sample_and_stale_sample_refuse_before_contact(tmp_path):
    events = []
    provider, _ = make_provider(tmp_path, events)
    with pytest.raises(LiveSpeechObservationError, match="outside"):
        provider.observe(
            context=context("s2"), arguments=arguments(), source_response_sha256=SHA_A
        )
    stale = context()
    stale.query_state.query_sample_id = "other"
    with pytest.raises(LiveSpeechObservationError, match="stale sample"):
        provider.observe(
            context=stale, arguments=arguments(), source_response_sha256=SHA_A
        )
    assert events == []


def test_nonreceipt_contact_refuses_before_source_or_backend(tmp_path):
    events = []
    provider = LiveSpeechObservationProvider(
        inventory=inventory(),
        protocol=protocol(),
        source_bindings={"s1": binding()},
        data_root=tmp_path,
        output_root=tmp_path / "live",
        contact=lambda **_facts: events.append("contact"),
        backend_factory=lambda *_args: events.append("backend"),
        host_memory_guard=lambda: events.append("guard"),
        source_resolver=lambda _binding: events.append("source"),
    )
    with pytest.raises(LiveSpeechObservationError, match="return a receipt"):
        provider.observe(
            context=context(), arguments=arguments(), source_response_sha256=SHA_A
        )
    assert events == ["guard", "contact"]


@pytest.mark.parametrize(
    "output,match",
    [
        ({"schema": "wrong"}, "output is invalid"),
        ({
            "schema": "saea-prepared-speech-observation-v1",
            "status": "empty",
            "transcript": "not empty",
            "diagnostics": {},
        }, "contradicts"),
    ],
)
def test_backend_output_must_be_a_valid_nonanswering_observation(
    tmp_path, output, match
):
    class OutputBackend:
        def decode_selected(self, _source):
            return output

        def close(self):
            pass

    provider = LiveSpeechObservationProvider(
        inventory=inventory(),
        protocol=protocol(),
        source_bindings={"s1": binding()},
        data_root=tmp_path,
        output_root=tmp_path / "live",
        contact=lambda **_facts: {"contact_id": "one"},
        backend_factory=lambda *_args: OutputBackend(),
        host_memory_guard=lambda: None,
        source_resolver=resolved_source,
    )
    with pytest.raises(LiveSpeechObservationError, match=match):
        provider.observe(
            context=context(), arguments=arguments(), source_response_sha256=SHA_A
        )


def test_closed_provider_refuses_without_contact(tmp_path):
    events = []
    provider, holder = make_provider(tmp_path, events)
    provider.close()
    with pytest.raises(LiveSpeechObservationError, match="closed"):
        provider.observe(
            context=context(), arguments=arguments(), source_response_sha256=SHA_A
        )
    assert events == []
    assert holder == {}


def test_default_selected_source_resolver_binds_synthetic_file_metadata(
    tmp_path, monkeypatch
):
    path = tmp_path / "audio/s1.flac"
    path.parent.mkdir()
    path.write_bytes(b"synthetic-not-audio")
    synthetic_binding = binding(
        source_audio_sha256=hashlib.sha256(path.read_bytes()).hexdigest()
    )
    monkeypatch.setitem(
        sys.modules,
        "soundfile",
        SimpleNamespace(info=lambda _path: SimpleNamespace(frames=16000, samplerate=16000)),
    )

    result = live._resolve_selected_source(tmp_path, synthetic_binding)

    assert result["media_path"] == str(path)
    assert result["audio_sha256"] == synthetic_binding["source_audio_sha256"]
    assert result["source_frames"] == result["end_frame"] == 16000
    assert result["start_frame"] == 0
