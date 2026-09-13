"""On-demand local speech observation after a source-bound model action."""

from __future__ import annotations

import json
import math
from pathlib import Path
from threading import Lock
from types import MappingProxyType
from typing import Callable, Mapping

from ..core.preparation import (
    PreparationError,
    canonical_bytes,
    digest,
    hash_stable_file,
    load_artifact,
    prepare_artifact,
)
from ..core.session.serving import _refuse_low_host_memory
from ..core.speech_observation_backend import (
    LocalWhisperBackend,
    OUTPUT_SCHEMA,
    _validate_inventory,
    _validate_protocol,
)
from .errors import RailsError
from .speech_observation import SpeechObservationSelection, _confined


LIVE_RESULT_SCHEMA = "saea-live-speech-observation-result-v1"
LIVE_SELECTION_SCHEMA = "saea-live-speech-observation-selection-v1"
LIVE_LINEAGE_SCHEMA = "saea-live-speech-observation-lineage-v1"
LIVE_RECEIPT_SCHEMA = "saea-live-speech-observation-provider-receipt-v1"
LIVE_ARTIFACT_KIND = "live-speech-observation-v1"
_SOURCE_FIELDS = {
    "packet_id",
    "packet_sha256",
    "source_audio_relpath",
    "source_audio_sha256",
    "source_audio_duration_seconds",
}
_ARGUMENT_FIELDS = {"span", "representation", "distinction"}
_SHA_CHARS = frozenset("0123456789abcdef")


class LiveSpeechObservationError(RailsError):
    """A selected live observation is stale, unbound, or malformed."""


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or set(value) - _SHA_CHARS:
        raise LiveSpeechObservationError(f"{field} must be a lowercase SHA-256")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiveSpeechObservationError(f"{field} must be non-empty text")
    return value


def _validate_arguments(arguments: object) -> dict[str, str]:
    if not isinstance(arguments, Mapping) or set(arguments) != _ARGUMENT_FIELDS:
        raise LiveSpeechObservationError(
            "live speech observation arguments must contain exactly "
            "span, representation and distinction"
        )
    if arguments["span"] != "full-utterance":
        raise LiveSpeechObservationError("live speech observation span must be full-utterance")
    if arguments["representation"] != "asr-transcript":
        raise LiveSpeechObservationError(
            "live speech observation representation must be asr-transcript"
        )
    distinction = _text(arguments["distinction"], "live speech observation distinction")
    if len(distinction) > 512:
        raise LiveSpeechObservationError(
            "live speech observation distinction exceeds 512 characters"
        )
    return {
        "span": "full-utterance",
        "representation": "asr-transcript",
        "distinction": distinction,
    }


def _validate_source_binding(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != _SOURCE_FIELDS:
        raise LiveSpeechObservationError(
            "live speech source binding has the wrong fields"
        )
    duration = value["source_audio_duration_seconds"]
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or not 0 < float(duration) <= 30
    ):
        raise LiveSpeechObservationError(
            "live speech source duration must be within 30 seconds"
        )
    relpath = value["source_audio_relpath"]
    if not isinstance(relpath, str) or not relpath:
        raise LiveSpeechObservationError("live speech source path must be relative text")
    # Confine syntax now without touching the file.
    try:
        _confined(Path("/"), relpath, "live speech source path")
    except RailsError as error:
        raise LiveSpeechObservationError(str(error)) from error
    return {
        "packet_id": _text(value["packet_id"], "live speech packet ID"),
        "packet_sha256": _sha(value["packet_sha256"], "live speech packet hash"),
        "source_audio_relpath": relpath,
        "source_audio_sha256": _sha(
            value["source_audio_sha256"], "live speech audio hash"
        ),
        "source_audio_duration_seconds": float(duration),
    }


def _resolve_selected_source(data_root: Path, binding: Mapping[str, object]):
    _, path = _confined(data_root, binding["source_audio_relpath"], "live speech source path")
    try:
        _size, measured, fingerprint = hash_stable_file(path, "live speech source")
        if measured != binding["source_audio_sha256"]:
            raise LiveSpeechObservationError("live speech source hash changed")
        import soundfile

        info = soundfile.info(path)
        duration = info.frames / info.samplerate
        if not math.isclose(
            duration,
            binding["source_audio_duration_seconds"],
            rel_tol=0,
            abs_tol=1e-6,
        ):
            raise LiveSpeechObservationError("live speech source duration changed")
        after = path.stat()
        if (after.st_ino, after.st_size, after.st_mtime_ns) != fingerprint:
            raise LiveSpeechObservationError("live speech source changed during validation")
    except (OSError, ValueError, PreparationError) as error:
        if isinstance(error, LiveSpeechObservationError):
            raise
        raise LiveSpeechObservationError(str(error)) from error
    return {
        "media_path": str(path),
        "audio_sha256": measured,
        "verified_fingerprint": fingerprint,
        "source_frames": info.frames,
        "source_sample_rate_hz": info.samplerate,
        "start_frame": 0,
        "end_frame": info.frames,
    }


class LiveSpeechObservationProvider:
    """Cache exact local ASR only after an admitted, model-selected contact."""

    def __init__(
        self,
        *,
        inventory: Mapping[str, object],
        protocol: Mapping[str, object],
        source_bindings: Mapping[str, Mapping[str, object]],
        data_root: Path,
        output_root: Path,
        contact: Callable[..., Mapping[str, object]],
        backend_factory=LocalWhisperBackend,
        host_memory_guard=None,
        source_resolver=None,
    ) -> None:
        try:
            _validate_inventory(inventory)
            _validate_protocol(protocol)
        except ValueError as error:
            raise LiveSpeechObservationError(str(error)) from error
        if protocol["device"] != "cpu" or protocol["fp16"] is not False:
            raise LiveSpeechObservationError(
                "live speech observation v1 requires CPU with fp16=false"
            )
        if not isinstance(source_bindings, Mapping) or not source_bindings:
            raise LiveSpeechObservationError(
                "live speech observation requires source bindings"
            )
        if not callable(contact):
            raise LiveSpeechObservationError(
                "live speech observation requires a contact callback"
            )
        self.inventory = dict(inventory)
        self.protocol = dict(protocol)
        self.source_bindings = {
            _text(sample_id, "live speech sample ID"): _validate_source_binding(binding)
            for sample_id, binding in source_bindings.items()
        }
        self.data_root = Path(data_root)
        self.output_root = Path(output_root)
        self.contact = contact
        self.backend_factory = backend_factory
        self.host_memory_guard = host_memory_guard or (
            lambda: _refuse_low_host_memory(14.0)
        )
        self.source_resolver = source_resolver or (
            lambda binding: _resolve_selected_source(self.data_root, binding)
        )
        self._inventory_sha256 = digest(self.inventory)
        self._protocol_sha256 = digest(self.protocol)
        self._backend = None
        self._lock = Lock()
        self._invocations = 0
        self._cache_hits = 0
        self._new_forwards = 0
        self._failures = 0
        self._artifacts: set[str] = set()
        self._closed = False

    def _event(self, phase, **_facts):
        if phase == "speech_tool_forward_started":
            self._new_forwards += 1

    def _binding_for_context(self, context: object) -> tuple[str, dict[str, object]]:
        sample_id = getattr(context, "sample_id", None)
        query = getattr(context, "query_state", None)
        if (
            not isinstance(sample_id, str)
            or query is None
            or getattr(query, "query_sample_id", None) != sample_id
        ):
            raise LiveSpeechObservationError(
                "live speech observation context has a stale sample binding"
            )
        binding = self.source_bindings.get(sample_id)
        if binding is None:
            raise LiveSpeechObservationError(
                "live speech observation sample is outside the source roster"
            )
        if (
            getattr(query, "speech_packet_id", None) != binding["packet_id"]
            or getattr(query, "speech_packet_sha256", None)
            != binding["packet_sha256"]
        ):
            raise LiveSpeechObservationError(
                "live speech observation context has a stale packet binding"
            )
        return sample_id, binding

    def _artifact_inputs(self, binding, arguments):
        return {
            "schema": "saea-live-speech-observation-inputs-v1",
            "inventory_sha256": self._inventory_sha256,
            "protocol_sha256": self._protocol_sha256,
            "source": dict(binding),
            "span": arguments["span"],
            "representation": arguments["representation"],
        }

    def observe(self, *, context, arguments, source_response_sha256):
        """Return one existing selection shape after warm lookup or one debit."""

        normalized_arguments = _validate_arguments(arguments)
        source_response_sha256 = _sha(
            source_response_sha256, "live speech source response hash"
        )
        sample_id, binding = self._binding_for_context(context)
        inputs = self._artifact_inputs(binding, normalized_arguments)
        cache_key = digest(inputs)
        path = self.output_root / cache_key[:2] / f"{cache_key}.json"
        contact_receipt = None

        with self._lock:
            if self._closed:
                raise LiveSpeechObservationError(
                    "live speech observation provider is closed"
                )
            self._invocations += 1

            def produce():
                nonlocal contact_receipt
                if self._backend is None:
                    self.host_memory_guard()
                contact_receipt = self.contact(
                    sample_id=sample_id,
                    audio_seconds=binding["source_audio_duration_seconds"],
                    source={
                        "audio_sha256": binding["source_audio_sha256"],
                        "span": {
                            "kind": "full-utterance",
                            "start_seconds": 0.0,
                            "end_seconds": binding["source_audio_duration_seconds"],
                        },
                    },
                    arguments=dict(normalized_arguments),
                    source_response_sha256=source_response_sha256,
                    cache_key=cache_key,
                )
                if not isinstance(contact_receipt, Mapping):
                    raise LiveSpeechObservationError(
                        "live speech contact callback must return a receipt"
                    )
                canonical_bytes(contact_receipt)
                source = self.source_resolver(binding)
                if self._backend is None:
                    self._backend = self.backend_factory(
                        self.inventory,
                        self.protocol,
                        self.data_root,
                        self._event,
                    )
                backend_output = self._backend.decode_selected(source)
                if (
                    not isinstance(backend_output, Mapping)
                    or backend_output.get("schema") != OUTPUT_SCHEMA
                    or backend_output.get("status")
                    not in {"ok", "empty", "timeout", "unsupported"}
                    or not isinstance(backend_output.get("transcript"), str)
                    or not isinstance(backend_output.get("diagnostics"), Mapping)
                ):
                    raise LiveSpeechObservationError(
                        "live speech backend output is invalid"
                    )
                if (
                    backend_output["status"] == "ok"
                    and not backend_output["transcript"].strip()
                ) or (
                    backend_output["status"] != "ok"
                    and backend_output["transcript"]
                ):
                    raise LiveSpeechObservationError(
                        "live speech backend output status contradicts its transcript"
                    )
                resolved_source = {
                    key: value
                    for key, value in source.items()
                    if key != "media_path"
                }
                resolved_source["verified_fingerprint"] = list(
                    resolved_source["verified_fingerprint"]
                )
                return {
                    "schema": LIVE_RESULT_SCHEMA,
                    "status": backend_output["status"],
                    "transcript": backend_output["transcript"],
                    "backend_output": dict(backend_output),
                    "resolved_source": resolved_source,
                    "contact": dict(contact_receipt),
                }

            try:
                artifact_receipt = prepare_artifact(
                    path,
                    kind=LIVE_ARTIFACT_KIND,
                    inputs=inputs,
                    producer=produce,
                    contact_class="speech-tool",
                )
                output = load_artifact(
                    path,
                    expected_sha256=artifact_receipt["sha256"],
                    kind=LIVE_ARTIFACT_KIND,
                    inputs=inputs,
                )
            except BaseException:
                self._failures += 1
                raise
            if artifact_receipt["cache"] == "warm":
                self._cache_hits += 1
            artifact_sha256 = artifact_receipt["sha256"]
            self._artifacts.add(artifact_sha256)

        status = output["status"]
        evidence_id = f"live-speech-observation:{artifact_sha256}:{sample_id}"
        visible = MappingProxyType({
            "schema": LIVE_SELECTION_SCHEMA,
            "evidence_id": evidence_id,
            "status": status,
            "transcript": output["transcript"],
            "artifact_sha256": artifact_sha256,
            "sample_id": sample_id,
            "speech_packet_id": binding["packet_id"],
            "speech_packet_sha256": binding["packet_sha256"],
            "source_uri": (
                f"live-speech-observation://{artifact_sha256}/{evidence_id}"
            ),
        })
        lineage = {
            "schema": LIVE_LINEAGE_SCHEMA,
            "cache": artifact_receipt["cache"],
            "cache_key": cache_key,
            "artifact_path": str(path),
            "artifact_sha256": artifact_sha256,
            "output_sha256": json.loads(path.read_bytes())["output_sha256"],
            "inventory_sha256": self._inventory_sha256,
            "protocol_sha256": self._protocol_sha256,
            "source": dict(binding),
            "resolved_source": dict(output["resolved_source"]),
            "arguments": dict(normalized_arguments),
            "source_response_sha256": source_response_sha256,
            "producer_contact": dict(output["contact"]),
            "new_contact": contact_receipt is not None,
        }
        if contact_receipt is not None:
            lineage["contact"] = dict(contact_receipt)
        return SpeechObservationSelection(
            visible=visible, lineage=MappingProxyType(lineage)
        )

    def receipt(self) -> dict[str, object]:
        with self._lock:
            return {
                "schema": LIVE_RECEIPT_SCHEMA,
                "invocations": self._invocations,
                "cache_hits": self._cache_hits,
                "new_forwards": self._new_forwards,
                "failures": self._failures,
                "artifacts": sorted(self._artifacts),
            }

    def close(self) -> None:
        with self._lock:
            if self._backend is not None:
                self._backend.close()
                self._backend = None
            self._closed = True
