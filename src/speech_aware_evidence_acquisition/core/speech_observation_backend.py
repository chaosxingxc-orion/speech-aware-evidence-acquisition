"""Bounded local Whisper decoding for prepared speech observations."""

from __future__ import annotations

import importlib
import math
from pathlib import Path
import re
import sys
from threading import Lock
from typing import Mapping, Sequence

from .speech_preparation_runtime import BoundedAudioPrefetch


OUTPUT_SCHEMA = "saea-prepared-speech-observation-v1"
MAX_AUDIO_SECONDS = 30.0
WHISPER_SAMPLE_RATE = 16000
MAX_WHISPER_SAMPLES = int(MAX_AUDIO_SECONDS * WHISPER_SAMPLE_RATE)


class SpeechObservationBackendError(ValueError):
    """Refuse an unbound, truncated, concurrent, or malformed decode request."""


_INVENTORY_KEYS = {
    "schema",
    "model",
    "checkpoint_path",
    "checkpoint_sha256",
    "whisper_source_path",
}
_PROTOCOL_KEYS = {
    "schema",
    "device",
    "cpu_workers",
    "batch_size",
    "language",
    "task",
    "temperature",
    "beam_size",
    "sample_len",
    "without_timestamps",
    "fp16",
    "no_speech_threshold",
    "logprob_threshold",
}
_OPTIONAL_PROTOCOL_KEYS = {"cpu_thread_limits", "source_selection"}
_CPU_THREAD_LIMIT_KEYS = {"inference_threads", "interop_threads"}
_SOURCE_KEYS = {
    "media_path",
    "audio_sha256",
    "verified_fingerprint",
    "source_frames",
    "source_sample_rate_hz",
    "start_frame",
    "end_frame",
}


def _exact_keys(value, expected, label, *, optional=frozenset()):
    if not isinstance(value, Mapping):
        raise SpeechObservationBackendError(f"{label} must be an object")
    unknown = set(value) - expected
    missing = expected - set(optional) - set(value)
    if unknown:
        raise SpeechObservationBackendError(f"{label} has unknown fields: {sorted(unknown)}")
    if missing:
        raise SpeechObservationBackendError(f"{label} lacks fields: {sorted(missing)}")


def _absolute_path(value, label):
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise SpeechObservationBackendError(f"{label} must be an absolute path")
    return value


def _sha256(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise SpeechObservationBackendError(f"{label} must be a lowercase SHA-256")


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise SpeechObservationBackendError(f"{label} must be finite")
    return float(value)


def _validate_inventory(inventory):
    _exact_keys(inventory, _INVENTORY_KEYS, "Whisper inventory")
    if inventory["schema"] != "saea-local-whisper-backend-inventory-v1":
        raise SpeechObservationBackendError("Whisper inventory schema is invalid")
    if inventory["model"] != "large-v3":
        raise SpeechObservationBackendError("Whisper inventory model must be large-v3")
    _absolute_path(inventory["checkpoint_path"], "Whisper checkpoint_path")
    _absolute_path(inventory["whisper_source_path"], "Whisper whisper_source_path")
    _sha256(inventory["checkpoint_sha256"], "Whisper checkpoint_sha256")


def _validate_protocol(protocol):
    _exact_keys(
        protocol,
        _PROTOCOL_KEYS | _OPTIONAL_PROTOCOL_KEYS,
        "Whisper decoding protocol",
        optional=_OPTIONAL_PROTOCOL_KEYS,
    )
    if protocol["schema"] != "saea-local-whisper-decode-v1":
        raise SpeechObservationBackendError("Whisper decoding protocol schema is invalid")
    if (
        "source_selection" in protocol
        and protocol["source_selection"] != "bounded-span-v1"
    ):
        raise SpeechObservationBackendError(
            "Whisper source_selection must be 'bounded-span-v1' when supplied"
        )
    if not isinstance(protocol["device"], str) or not (
        protocol["device"] == "cpu"
        or re.fullmatch(r"cuda(?::\d+)?", protocol["device"])
    ):
        raise SpeechObservationBackendError(
            "Whisper device must be cpu or name one explicit CUDA device"
        )
    if protocol["device"] == "cpu" and protocol["fp16"] is not False:
        raise SpeechObservationBackendError("Whisper CPU device requires fp16=false")
    for field, upper in (("cpu_workers", 8), ("batch_size", None), ("beam_size", None), ("sample_len", None)):
        value = protocol[field]
        if type(value) is not int or value < 1 or (upper is not None and value > upper):
            raise SpeechObservationBackendError(f"Whisper {field} is invalid")
    if "cpu_thread_limits" in protocol:
        limits = protocol["cpu_thread_limits"]
        _exact_keys(limits, _CPU_THREAD_LIMIT_KEYS, "Whisper CPU thread limits")
        if protocol["device"] != "cpu":
            raise SpeechObservationBackendError(
                "Whisper CPU thread limits require device='cpu'"
            )
        for field in sorted(_CPU_THREAD_LIMIT_KEYS):
            value = limits[field]
            if type(value) is not int or value < 1:
                raise SpeechObservationBackendError(
                    f"Whisper CPU thread limit {field} must be a positive integer"
                )
        if (
            protocol["cpu_workers"]
            + limits["inference_threads"]
            + limits["interop_threads"]
            > 8
        ):
            raise SpeechObservationBackendError(
                "Whisper CPU thread envelope exceeds eight workers"
            )
    if protocol["language"] != "en":
        raise SpeechObservationBackendError("Whisper language must be 'en'")
    if protocol["task"] != "transcribe":
        raise SpeechObservationBackendError("Whisper task must be 'transcribe'")
    if protocol["temperature"] != 0 or isinstance(protocol["temperature"], bool):
        raise SpeechObservationBackendError("Whisper temperature must be zero")
    if protocol["without_timestamps"] is not True:
        raise SpeechObservationBackendError("Whisper without_timestamps must be true")
    if type(protocol["fp16"]) is not bool:
        raise SpeechObservationBackendError("Whisper fp16 must be boolean")
    no_speech = _finite(protocol["no_speech_threshold"], "Whisper no_speech_threshold")
    if not 0.0 <= no_speech <= 1.0:
        raise SpeechObservationBackendError("Whisper no_speech_threshold must be within [0, 1]")
    _finite(protocol["logprob_threshold"], "Whisper logprob_threshold")


def _validate_source(source, *, source_selection=None):
    _exact_keys(source, _SOURCE_KEYS, "speech observation source")
    _absolute_path(source["media_path"], "speech observation media_path")
    _sha256(source["audio_sha256"], "speech observation audio_sha256")
    fingerprint = source["verified_fingerprint"]
    if (
        not isinstance(fingerprint, (list, tuple))
        or len(fingerprint) != 3
        or any(type(item) is not int or item < 0 for item in fingerprint)
    ):
        raise SpeechObservationBackendError("speech observation verified_fingerprint is invalid")
    for field in ("source_frames", "source_sample_rate_hz", "start_frame", "end_frame"):
        if type(source[field]) is not int:
            raise SpeechObservationBackendError(f"speech observation {field} must be an integer")
    frames = source["source_frames"]
    rate = source["source_sample_rate_hz"]
    start = source["start_frame"]
    end = source["end_frame"]
    if frames < 1 or rate < 1 or not 0 <= start < end <= frames:
        raise SpeechObservationBackendError("speech observation source frame geometry is invalid")
    if source_selection is None and (start != 0 or end != frames):
        raise SpeechObservationBackendError(
            "speech observation backend v1 requires the full utterance"
        )
    if (end - start) / rate > MAX_AUDIO_SECONDS:
        raise SpeechObservationBackendError("speech observation exceeds 30 seconds")


_CPU_THREAD_LIMITS_LOCK = Lock()
_APPLIED_CPU_THREAD_LIMITS: tuple[int, int] | None = None


def _apply_cpu_thread_limits(torch, protocol):
    """Apply one process-global CPU envelope and refuse later drift."""

    if "cpu_thread_limits" not in protocol:
        return
    limits = protocol["cpu_thread_limits"]
    desired = (limits["inference_threads"], limits["interop_threads"])
    setters = (
        getattr(torch, "set_num_threads", None),
        getattr(torch, "set_num_interop_threads", None),
    )
    getters = (
        getattr(torch, "get_num_threads", None),
        getattr(torch, "get_num_interop_threads", None),
    )
    if not all(callable(function) for function in setters + getters):
        raise SpeechObservationBackendError(
            "Torch does not expose enforceable CPU thread controls"
        )

    global _APPLIED_CPU_THREAD_LIMITS
    with _CPU_THREAD_LIMITS_LOCK:
        if _APPLIED_CPU_THREAD_LIMITS is None:
            try:
                setters[0](desired[0])
                setters[1](desired[1])
            except Exception as error:
                raise SpeechObservationBackendError(
                    "Torch refused the configured CPU thread limits"
                ) from error
            actual = (getters[0](), getters[1]())
            if actual != desired:
                raise SpeechObservationBackendError(
                    "Torch CPU thread limits differ after application"
                )
            _APPLIED_CPU_THREAD_LIMITS = desired
            return

        if _APPLIED_CPU_THREAD_LIMITS != desired:
            raise SpeechObservationBackendError(
                "configured Whisper CPU thread limits drifted within this process"
            )
        actual = (getters[0](), getters[1]())
        if actual != desired:
            raise SpeechObservationBackendError(
                "Torch CPU thread limits drifted after application"
            )


def _load_whisper_stack(inventory, protocol):
    """Import the declared official source and load only the exact local checkpoint."""
    source_root = Path(inventory["whisper_source_path"]).resolve()
    source_text = str(source_root)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    whisper = importlib.import_module("whisper")
    module_path = Path(whisper.__file__).resolve()
    if not module_path.is_relative_to(source_root):
        raise SpeechObservationBackendError("Whisper import did not resolve under declared source path")
    audio = importlib.import_module("whisper.audio")
    tokenizer = importlib.import_module("whisper.tokenizer")
    torch = importlib.import_module("torch")
    _apply_cpu_thread_limits(torch, protocol)
    model = whisper.load_model(
        inventory["checkpoint_path"],
        device=protocol["device"],
        in_memory=False,
    )
    return whisper, audio, torch, tokenizer, model.eval()


def _diagnostic_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class LocalWhisperBackend:
    """Decode full utterances or explicitly selected bounded source spans."""

    def __init__(self, inventory, protocol, data_root, event):
        _validate_inventory(inventory)
        _validate_protocol(protocol)
        if not callable(event):
            raise SpeechObservationBackendError("speech observation event must be callable")
        self.inventory = dict(inventory)
        self.protocol = dict(protocol)
        self.data_root = Path(data_root)
        self.event = event
        self.prefetch = BoundedAudioPrefetch(protocol["cpu_workers"])
        self.stack = None
        self._decode_lock = Lock()
        self._closed = False

    def prepare_sources(self, sources):
        if self._closed:
            raise SpeechObservationBackendError("speech observation backend is closed")
        sources = list(sources)
        if not sources:
            raise SpeechObservationBackendError("speech observation sources must be non-empty")
        for source in sources:
            _validate_source(
                source, source_selection=self.protocol.get("source_selection")
            )
        self.prefetch.prepare_sources(sources)

    def _ensure_stack(self):
        if self.stack is None:
            self.event("model_load_started")
            self.stack = _load_whisper_stack(self.inventory, self.protocol)
            self.event("model_load_finished")
        else:
            _apply_cpu_thread_limits(self.stack[2], self.protocol)
        return self.stack

    def _decode_batch_locked(self, sources, prefetch):
        whisper, audio, torch, tokenizer_module, model = self._ensure_stack()
        try:
            tokenizer = tokenizer_module.get_tokenizer(
                model.is_multilingual,
                num_languages=model.num_languages,
                language="en",
                task="transcribe",
            )
            initial_token_count = len(tokenizer.sot_sequence_including_notimestamps)
            decoder_context = model.dims.n_text_ctx
        except (AttributeError, TypeError, ValueError) as error:
            raise SpeechObservationBackendError(
                "Whisper model lacks a bounded decoder context"
            ) from error
        if (
            type(decoder_context) is not int
            or decoder_context < 1
            or self.protocol["sample_len"] + initial_token_count > decoder_context
        ):
            raise SpeechObservationBackendError(
                "Whisper sample_len exceeds the decoder context after initial tokens"
            )
        waves = []
        for source in sources:
            self.event("data_wait_started")
            wave = prefetch.take(source)
            self.event("data_wait_finished")
            if not hasattr(wave, "__len__") or not 0 < len(wave) <= MAX_WHISPER_SAMPLES:
                raise SpeechObservationBackendError(
                    "speech observation audio would require duration truncation"
                )
            waves.append(wave)
        self.event("mel_started")
        mels = []
        for wave in waves:
            padded_wave = audio.pad_or_trim(wave, audio.N_SAMPLES)
            mel = audio.log_mel_spectrogram(padded_wave, model.dims.n_mels)
            if not hasattr(mel, "shape") or mel.shape[-1] != audio.N_FRAMES:
                raise SpeechObservationBackendError(
                    "Whisper mel construction did not produce exactly 3000 frames"
                )
            mels.append(mel)
        batch = torch.stack(mels).to(self.protocol["device"])
        self.event("mel_finished")
        options = whisper.DecodingOptions(
            language="en",
            task="transcribe",
            temperature=0,
            beam_size=self.protocol["beam_size"],
            sample_len=self.protocol["sample_len"],
            without_timestamps=True,
            fp16=self.protocol["fp16"],
            prompt=None,
            prefix=None,
        )
        self.event("speech_tool_forward_started")
        try:
            results = whisper.decode(model, batch, options)
        finally:
            self.event("speech_tool_forward_finished")
        if not isinstance(results, Sequence) or len(results) != len(sources):
            raise SpeechObservationBackendError(
                "Whisper batch result count differs from source order"
            )
        return [self._render_result(result) for result in results]

    def decode_batch(self, sources):
        if self._closed:
            raise SpeechObservationBackendError("speech observation backend is closed")
        sources = list(sources)
        if not sources or len(sources) > self.protocol["batch_size"]:
            raise SpeechObservationBackendError("speech observation batch_size bound is violated")
        for source in sources:
            _validate_source(
                source, source_selection=self.protocol.get("source_selection")
            )
        if not self._decode_lock.acquire(blocking=False):
            raise SpeechObservationBackendError("concurrent Whisper decode is forbidden")
        try:
            return self._decode_batch_locked(sources, self.prefetch)
        finally:
            self._decode_lock.release()

    def decode_selected(self, source):
        """Decode only one already-selected source while retaining loaded weights."""

        if self._closed:
            raise SpeechObservationBackendError("speech observation backend is closed")
        _validate_source(source, source_selection=self.protocol.get("source_selection"))
        with self._decode_lock:
            selected_prefetch = BoundedAudioPrefetch(self.protocol["cpu_workers"])
            try:
                selected_prefetch.prepare_sources([source])
                return self._decode_batch_locked([source], selected_prefetch)[0]
            finally:
                selected_prefetch.close()

    def _render_result(self, result):
        raw_text = getattr(result, "text", None)
        raw_tokens = getattr(result, "tokens", None)
        if not isinstance(raw_text, str) or not isinstance(raw_tokens, (list, tuple)):
            raise SpeechObservationBackendError("Whisper result lacks raw text or tokens")
        if any(type(token) is not int for token in raw_tokens):
            raise SpeechObservationBackendError("Whisper result tokens must be integers")
        avg_logprob = _diagnostic_number(getattr(result, "avg_logprob", None))
        no_speech_prob = _diagnostic_number(getattr(result, "no_speech_prob", None))
        if avg_logprob is None or no_speech_prob is None:
            raise SpeechObservationBackendError("Whisper result lacks finite confidence diagnostics")
        stripped = raw_text.strip()
        capped = len(raw_tokens) >= self.protocol["sample_len"]
        low_speech = (
            no_speech_prob > self.protocol["no_speech_threshold"]
            and avg_logprob <= self.protocol["logprob_threshold"]
        )
        status = "unsupported" if capped else ("empty" if not stripped or low_speech else "ok")
        language_probs = getattr(result, "language_probs", None)
        if isinstance(language_probs, Mapping):
            language_probs = {
                str(key): _diagnostic_number(value) for key, value in language_probs.items()
            }
        else:
            language_probs = None
        return {
            "schema": OUTPUT_SCHEMA,
            "status": status,
            "transcript": stripped if status == "ok" else "",
            "diagnostics": {
                "raw_text": raw_text,
                "tokens": list(raw_tokens),
                "language": getattr(result, "language", None),
                "language_probs": language_probs,
                "avg_logprob": avg_logprob,
                "no_speech_prob": no_speech_prob,
                "temperature": _diagnostic_number(getattr(result, "temperature", None)),
                "compression_ratio": _diagnostic_number(
                    getattr(result, "compression_ratio", None)
                ),
                "output_cap_reached": capped,
                "low_speech": low_speech,
            },
        }

    def __call__(self, source):
        return self.decode_batch([source])[0]

    def close(self):
        if not self._closed:
            self.prefetch.close()
            self.stack = None
            self._closed = True
