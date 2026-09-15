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
from .execution_units import ExecutionUnit, ExecutionUnitRoster
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


def _validate_source_binding(value: object, *, maximum_seconds=30.0) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != _SOURCE_FIELDS:
        raise LiveSpeechObservationError(
            "live speech source binding has the wrong fields"
        )
    duration = value["source_audio_duration_seconds"]
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or float(duration) <= 0
        or (maximum_seconds is not None and float(duration) > maximum_seconds)
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



def normalize_live_span_arguments(arguments: object) -> dict[str, object]:
    """Validate a model-selected interval relative to its current execution unit."""
    if not isinstance(arguments, Mapping) or set(arguments) != _ARGUMENT_FIELDS:
        raise LiveSpeechObservationError("span observation requires span, representation and distinction")
    span = arguments["span"]
    if not isinstance(span, Mapping) or set(span) != {"start_seconds", "end_seconds"}:
        raise LiveSpeechObservationError("span must contain start_seconds and end_seconds")
    start, end = span["start_seconds"], span["end_seconds"]
    if (
        any(isinstance(v, bool) or not isinstance(v, (int, float))
            or not math.isfinite(v) for v in (start, end))
        or not 0 <= start < end
    ):
        raise LiveSpeechObservationError("span bounds must be finite and increasing")
    legacy = _validate_arguments({**arguments, "span": "full-utterance"})
    return {**legacy, "span": {"start_seconds": float(start), "end_seconds": float(end)}}


def select_execution_unit_span(unit: ExecutionUnit, arguments: object):
    """Round outward to source frames, then enforce unit and 30-second bounds."""
    if not isinstance(unit, ExecutionUnit):
        raise LiveSpeechObservationError("span selection requires an execution unit")
    unit.validate()
    arguments = normalize_live_span_arguments(arguments)
    source = unit.slice_record
    rate = source.sample_rate_hz
    duration = source.audio_seconds
    if (
        type(rate) is not int or rate <= 0
        or isinstance(duration, bool) or not isinstance(duration, (int, float))
        or not math.isfinite(duration) or duration <= 0
    ):
        raise LiveSpeechObservationError("execution unit source geometry is invalid")
    start, end = (arguments["span"][key] for key in ("start_seconds", "end_seconds"))
    if end > duration:
        raise LiveSpeechObservationError("selected span is outside the execution unit")
    first, last = math.floor(start * rate), math.ceil(end * rate)
    if not 0 <= first < last <= round(duration * rate):
        raise LiveSpeechObservationError("selected frame span is outside the execution unit")
    seconds = (last - first) / rate
    if seconds > 30:
        raise LiveSpeechObservationError("selected frame span exceeds 30 seconds")
    return {
        "kind": "unit-relative-frames", "start_frame": first, "end_frame": last,
        "sample_rate_hz": rate,
    }, seconds


def execution_unit_source_bindings(roster: ExecutionUnitRoster):
    """Expose registered unit audio addresses without pretending they are parents."""
    if not isinstance(roster, ExecutionUnitRoster):
        raise LiveSpeechObservationError("speech sources require an ExecutionUnitRoster")
    parents = tuple(dict.fromkeys(unit.parent_sample_id for unit in roster.units))
    roster.validate(parent_sample_ids=parents, max_contacts=1)
    bindings = {}
    for unit in roster.units:
        query = unit.query_descriptor("speech_features")
        source = unit.slice_record
        bindings[unit.request_key] = _validate_source_binding({
            "packet_id": query["packet_id"], "packet_sha256": query["sha256"],
            "source_audio_relpath": source.media_relpath,
            "source_audio_sha256": source.sha256,
            "source_audio_duration_seconds": source.audio_seconds,
        }, maximum_seconds=None)
    return bindings


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
        execution_units: ExecutionUnitRoster | None = None,
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
        self._execution_units = {}
        if execution_units is not None:
            expected = execution_unit_source_bindings(execution_units)
            if dict(source_bindings) != expected:
                raise LiveSpeechObservationError("live speech sources differ from execution units")
            if protocol.get("source_selection") != "bounded-span-v1":
                raise LiveSpeechObservationError("execution-unit speech requires bounded-span-v1")
            self._execution_units = {unit.request_key: unit for unit in execution_units.units}
            self.source_bindings = expected
        else:
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

    def _binding_for_context(self, context: object):
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
        unit_id = getattr(context, "execution_unit_id", None)
        unit = self._execution_units.get(unit_id)
        if self._execution_units:
            if (
                unit is None or unit.parent_sample_id != sample_id
                or getattr(context, "execution_unit_binding", None) != unit.as_json()
            ):
                raise LiveSpeechObservationError("live speech context has a stale execution unit")
        elif unit_id is not None:
            raise LiveSpeechObservationError("legacy speech sources cannot alias an execution unit")
        binding = self.source_bindings.get(unit_id if unit is not None else sample_id)
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
        return sample_id, binding, unit

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
        """Preserve the historical complete-short-utterance tool semantics."""
        if self._execution_units:
            raise LiveSpeechObservationError("execution units require the explicit span tool")
        return self._observe(
            context=context, arguments=_validate_arguments(arguments),
            source_response_sha256=source_response_sha256, span_mode=False,
        )

    def observe_span(self, *, context, arguments, source_response_sha256):
        """Decode only a model-selected span in the current registered unit."""
        if not self._execution_units:
            raise LiveSpeechObservationError("span tool requires registered execution units")
        return self._observe(
            context=context, arguments=normalize_live_span_arguments(arguments),
            source_response_sha256=source_response_sha256, span_mode=True,
        )

    def _observe(self, *, context, arguments, source_response_sha256, span_mode):
        normalized_arguments = arguments
        source_response_sha256 = _sha(
            source_response_sha256, "live speech source response hash"
        )
        sample_id, binding, unit = self._binding_for_context(context)
        selected_span = {
            "kind": "full-utterance", "start_seconds": 0.0,
            "end_seconds": binding["source_audio_duration_seconds"],
        }
        audio_seconds = binding["source_audio_duration_seconds"]
        unit_facts = {}
        inputs = self._artifact_inputs(binding, normalized_arguments)
        if span_mode:
            selected_span, audio_seconds = select_execution_unit_span(unit, normalized_arguments)
            unit_facts = {
                "execution_unit_id": unit.request_key,
                "execution_unit_binding_sha256": digest(unit.as_json()),
            }
            inputs = {
                **inputs, "schema": "saea-live-speech-observation-inputs-v2",
                "execution_unit": unit.as_json(), "span": dict(selected_span),
            }
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
                    audio_seconds=audio_seconds,
                    source={
                        "audio_sha256": binding["source_audio_sha256"],
                        "span": dict(selected_span),
                    },
                    **unit_facts,
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
                if span_mode:
                    if (
                        source["source_sample_rate_hz"] != selected_span["sample_rate_hz"]
                        or selected_span["end_frame"] > source["source_frames"]
                    ):
                        raise LiveSpeechObservationError("selected source frame geometry changed")
                    source = {**source, "start_frame": selected_span["start_frame"],
                              "end_frame": selected_span["end_frame"]}
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
            **({"execution_unit_id": unit.request_key, "source_span": dict(selected_span)}
               if span_mode else {}),
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
            **({**unit_facts, "selected_span": dict(selected_span)} if span_mode else {}),
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

    def validate_span_selection(self, *, context, arguments, source_response_sha256, selection):
        """Bind returned tool evidence to this exact unit, request and selected frames."""
        sample_id, binding, unit = self._binding_for_context(context)
        span, _seconds = select_execution_unit_span(unit, arguments)
        if not isinstance(selection, SpeechObservationSelection):
            raise LiveSpeechObservationError("span tool returned an unbound selection")
        visible, lineage = selection.visible, selection.lineage
        if (
            visible.get("schema") != LIVE_SELECTION_SCHEMA
            or visible.get("sample_id") != sample_id
            or visible.get("execution_unit_id") != unit.request_key
            or visible.get("speech_packet_id") != binding["packet_id"]
            or visible.get("speech_packet_sha256") != binding["packet_sha256"]
            or visible.get("source_span") != span
            or lineage.get("execution_unit_id") != unit.request_key
            or lineage.get("execution_unit_binding_sha256") != digest(unit.as_json())
            or lineage.get("source") != binding
            or lineage.get("selected_span") != span
            or lineage.get("arguments") != normalize_live_span_arguments(arguments)
            or lineage.get("source_response_sha256") != source_response_sha256
        ):
            raise LiveSpeechObservationError("span tool returned foreign evidence")

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
