"""Shared fitting of actual transport requests, without generation."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .preparation import PreparationError, canonical_bytes, digest, measure_request
from .model.paths import _canonical_window_route_path


class GuardedTokenizer:
    """Check the root lease and bounded contact permission at every endpoint."""

    def __init__(
        self,
        client,
        *,
        guard: Callable[[], None],
        contact_cap: int,
        contact_sink: Callable[[str, str], None] | None = None,
    ):
        if (
            isinstance(contact_cap, bool)
            or not isinstance(contact_cap, int)
            or contact_cap < 1
        ):
            raise PreparationError("tokenizer contact cap must be a positive integer")
        self.client, self.guard, self.contact_cap = client, guard, contact_cap
        self.counts: Counter[str] = Counter()
        self.contact_sink = contact_sink

    def request_json(self, method, path, payload=None):
        if (method, path) not in {
            ("GET", "/props"),
            ("POST", "/apply-template"),
            ("POST", "/tokenize"),
            ("POST", "/v1/chat/completions/input_tokens"),
        }:
            raise PreparationError("fit client refuses a non-tokenizer route")
        if self.counts.total() >= self.contact_cap:
            raise PreparationError("tokenizer contact cap exhausted")
        self.guard()
        self.counts[f"{method} {path}"] += 1  # failed contacts count too
        if self.contact_sink is not None:
            self.contact_sink(method, path)
        return self.client.request_json(method, path, payload)


def rendered_speech_feature_descriptors(
    body: Mapping[str, object],
) -> tuple[dict[str, object], ...]:
    """Return every speech-feature descriptor in actual rendered wire order."""

    messages = body.get("messages")
    if not isinstance(messages, Sequence) or isinstance(messages, (str, bytes)):
        raise PreparationError("rendered request messages must be a sequence")
    descriptors = []
    for message_index, message in enumerate(messages):
        if not isinstance(message, Mapping):
            raise PreparationError(
                f"rendered request messages[{message_index}] must be a mapping"
            )
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part_index, part in enumerate(content):
            if not isinstance(part, Mapping) or part.get("type") != "input_speech_features":
                continue
            descriptor = part.get("speech_features")
            if (
                not isinstance(descriptor, Mapping)
                or set(descriptor) != {"packet_id", "sha256", "role"}
                or descriptor.get("role") not in {"query", "key"}
                or not all(
                    isinstance(descriptor.get(key), str) and descriptor[key]
                    for key in ("packet_id", "sha256")
                )
            ):
                raise PreparationError(
                    "rendered request speech feature descriptor is malformed at "
                    f"messages[{message_index}].content[{part_index}]"
                )
            descriptors.append(dict(descriptor))
    return tuple(descriptors)


def rendered_raw_speech_sha256(body: Mapping[str, object]) -> str:
    """Return the one raw-audio query digest from an actual rendered request.

    Native raw requests carry their source path in the prepared payload, while
    the wire body carries the audio bytes. Requiring exactly one decoded
    input_audio part makes the two representations comparable without trusting
    a transport-provided duration or a synthetic feature descriptor.
    """
    messages = body.get("messages")
    if not isinstance(messages, Sequence) or isinstance(messages, (str, bytes)):
        raise PreparationError("rendered request messages must be a sequence")
    audio_parts = []
    for message_index, message in enumerate(messages):
        if not isinstance(message, Mapping):
            raise PreparationError(
                f"rendered request messages[{message_index}] must be a mapping"
            )
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part_index, part in enumerate(content):
            if (
                isinstance(part, Mapping)
                and part.get("type") == "input_speech_features"
            ):
                raise PreparationError(
                    "native raw fit refuses rendered speech feature input at "
                    f"messages[{message_index}].content[{part_index}]"
                )
            if isinstance(part, Mapping) and part.get("type") == "input_audio":
                audio_parts.append((message_index, part_index, part))
    if len(audio_parts) != 1:
        raise PreparationError("native raw fit requires exactly one rendered input_audio")
    message_index, part_index, part = audio_parts[0]
    audio = part.get("input_audio")
    encoded = audio.get("data") if isinstance(audio, Mapping) else None
    if not isinstance(encoded, str) or not encoded:
        raise PreparationError(
            "native raw fit rendered input_audio data is malformed at "
            f"messages[{message_index}].content[{part_index}]"
        )
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise PreparationError("native raw fit rendered input_audio is not base64") from error
    return hashlib.sha256(raw).hexdigest()


def packet_token_counts(
    payload: Mapping[str, object],
    *,
    feature_root: Path,
    decoder_sha256: str,
    loader=None,
) -> tuple[int, ...]:
    """Read exact chunk counts from the same hash-validated packet descriptors."""
    from .model.speech_features import load_speech_feature_packets

    descriptors = payload.get("speech_feature_parts")
    if not isinstance(descriptors, list) or not descriptors:
        raise PreparationError("packet fit requires actual speech feature descriptors")
    if any(
        not isinstance(d, Mapping)
        or set(d) != {"packet_id", "sha256", "role"}
        or d["role"] not in {"query", "key"}
        for d in descriptors
    ):
        raise PreparationError("packet fit descriptor shape mismatch")
    packets = (loader or load_speech_feature_packets)(
        feature_root,
        tuple(
            {"packet_id": d["packet_id"], "sha256": d["sha256"]} for d in descriptors
        ),
        expected_decoder_gguf_sha256=decoder_sha256,
    )
    return tuple(sum(chunk.n_tokens for chunk in packet.chunks) for packet in packets)


def canonical_window_sources(
    source_bindings: Sequence[Mapping[str, object]],
) -> tuple[dict[str, object], ...]:
    """Normalize only the run-owned slice path; retain all source facts."""
    return tuple(
        {
            **source,
            "media_relpath": _canonical_window_route_path(source.get("media_relpath")),
        }
        for source in source_bindings
    )


def boundary_identity(
    payloads: Sequence[Mapping[str, object]], *, window_routes: bool = False
) -> str:
    # These two routing values never enter the prompt; worker assignment may
    # change them. Completion limits and every model-visible field stay bound.
    normalized = []
    for payload in payloads:
        row = {k: v for k, v in payload.items() if k != "request_id"}
        provenance = payload.get("evidence_provenance")
        if isinstance(provenance, list):
            normalized_provenance = []
            for index, source in enumerate(provenance):
                if isinstance(source, Mapping) and source.get("lock_key") == "rails-supply":
                    # This is a trace address minted from the concurrently assigned
                    # request ID, not a model-visible evidence source. Validate its
                    # exact ownership before replacing only the routing segment.
                    request_id = payload.get("request_id")
                    expected = f"rails-message/{request_id}/{index}"
                    if not isinstance(request_id, str) or not request_id or source.get("relpath") != expected:
                        raise PreparationError("rails supply provenance is not bound to this request")
                    source = {**source, "relpath": f"rails-message/<request>/{index}"}
                normalized_provenance.append(source)
            row["evidence_provenance"] = normalized_provenance
        if window_routes:
            row["media_relpath"] = _canonical_window_route_path(
                row.get("media_relpath")
            )
        if isinstance(row.get("decoding_params"), Mapping):
            row["decoding_params"] = {
                k: v for k, v in row["decoding_params"].items() if k != "id_slot"
            }
        normalized.append(row)
    return digest(
        sorted(
            normalized,
            key=lambda p: (str(p.get("sample_id")), str(p.get("media_relpath"))),
        )
    )


def fit_requests(
    payloads: Sequence[Mapping[str, object]],
    *,
    expected_sample_ids: Sequence[str],
    transport,
    client,
    speech_counts: Callable[[Mapping[str, object]], Sequence[int]],
    media_marker: str,
    slot_tokens: int,
    fit_multiple: float = 1.0,
    special_tokens: int = 2,
    request_key: Callable[[Mapping[str, object]], str] | None = None,
    request_measure: Callable | None = None,
    rendered_bodies: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Fit every actual body; retain only hashes, counts, and sample identities.

    Transport rendering is the exact function used by generation. Callers that
    already validated a rendered body may pass it without rendering a second
    time. A supplied speech-count resolver supports both feature packets and
    already measured raw-speech repair windows; it must never substitute
    duration estimates.
    """
    ids = [request_key(p) if request_key else p.get("sample_id") for p in payloads]
    if (
        not ids
        or len(set(ids)) != len(ids)
        or len(set(expected_sample_ids)) != len(expected_sample_ids)
        or set(ids) != set(expected_sample_ids)
    ):
        raise PreparationError("fit must cover the complete unique roster")
    if rendered_bodies is not None and len(rendered_bodies) != len(payloads):
        raise PreparationError("rendered fit bodies must match the request roster")
    rows = []
    for index, payload in enumerate(payloads):
        body = (
            transport.render_request(canonical_bytes(payload))
            if rendered_bodies is None
            else rendered_bodies[index]
        )
        if not isinstance(body, Mapping):
            raise PreparationError("rendered fit body must be a mapping")
        effective_descriptors = rendered_speech_feature_descriptors(body)
        speech_payload = payload
        if effective_descriptors or "speech_feature_parts" in payload:
            speech_payload = {
                **payload,
                "speech_feature_parts": [
                    dict(descriptor) for descriptor in effective_descriptors
                ],
            }
        if request_measure is None:
            row = measure_request(
                client,
                body,
                media_marker=media_marker,
                speech_tokens=speech_counts(speech_payload),
                slot_tokens=slot_tokens,
                fit_multiple=fit_multiple,
                special_tokens=special_tokens,
            )
        else:
            row = request_measure(
                client,
                body,
                slot_tokens=slot_tokens,
                fit_multiple=fit_multiple,
                special_tokens=special_tokens,
            )
        row = {"sample_id": payload["sample_id"], **row}
        if request_key is not None:
            row["request_key"] = request_key(payload)
        rows.append(row)
    worst = min(rows, key=lambda row: row["margin_tokens"])
    return {
        "sample_count": len(rows),
        "rows": rows,
        "boundary_sha256": boundary_identity(payloads),
        "every_request_fits": all(row["fits"] for row in rows),
        "worst_sample_id": worst["sample_id"],
        "minimum_margin_tokens": worst["margin_tokens"],
    }


def materialize_request_fit_batch(runtime, *, execution_plan=None):
    """Select the registered source-window fit builder without changing its prompt."""

    values = getattr(getattr(runtime, "_composed", None), "values", {})
    prepared_units = (
        isinstance(values, Mapping)
        and values.get("prepared_execution_units") is not None
    )
    if runtime._adapter.preprocess_plan().get("kind") != "raw-speech-windows":
        if prepared_units:
            raise PreparationError(
                "prepared execution unit fit requires the raw-speech-windows adapter"
            )
        return None
    if not prepared_units:
        if execution_plan is None:
            return runtime.materialize_window_batch()
        return runtime.materialize_window_batch(execution_plan=execution_plan)
    roster = runtime.execution_unit_roster()
    if roster is None:
        raise PreparationError("prepared execution unit fit has no validated roster")
    payloads = runtime.materialize_phase_requests()
    if len(payloads) != len(roster.units):
        raise PreparationError("prepared execution unit fit does not cover every unit")
    from .preparation_windows import WindowRequestBatch

    return WindowRequestBatch(
        tuple(payloads),
        tuple(unit.request_key for unit in roster.units),
        tuple(unit.slice_record.trace_view() for unit in roster.units),
    )


@dataclass(frozen=True)
class PreparedPhaseRequests:
    """Keep real single-phase requests immutable until root begins fitting."""

    run_id: str
    attempt_id: str
    payload_bytes: tuple[bytes, ...]
    inputs_bytes: bytes


def _validate_phase_roster(payloads, context):
    expected = context["sample_ids"]
    actual = [payload.get("sample_id") for payload in payloads]
    if (
        not actual or len(set(actual)) != len(actual)
        or len(set(expected)) != len(expected) or set(actual) != set(expected)
    ):
        raise PreparationError("prepared phase must cover the complete unique roster")


def materialize_phase_fit(runtime) -> PreparedPhaseRequests:
    """Complete shared request construction before any service is started."""
    context = runtime.preparation_context()
    payloads = runtime.materialize_phase_requests()
    _validate_phase_roster(payloads, context)
    return PreparedPhaseRequests(
        context["run_id"], context["attempt_id"],
        tuple(canonical_bytes(payload) for payload in payloads),
        canonical_bytes(runtime.request_fit_inputs(payloads)),
    )


def _consume_phase_fit(runtime, prepared, context):
    if not isinstance(prepared, PreparedPhaseRequests) or (
        prepared.run_id != context["run_id"]
        or prepared.attempt_id != context["attempt_id"]
    ):
        raise PreparationError("prepared phase run or attempt identity changed")
    if not isinstance(prepared.payload_bytes, tuple) or not all(
        isinstance(raw, bytes) for raw in prepared.payload_bytes
    ) or not isinstance(prepared.inputs_bytes, bytes):
        raise PreparationError("prepared phase must contain immutable canonical bytes")
    try:
        payloads = tuple(json.loads(raw) for raw in prepared.payload_bytes)
        if any(not isinstance(payload, dict) for payload in payloads):
            raise ValueError("payload is not an object")
        if tuple(canonical_bytes(p) for p in payloads) != prepared.payload_bytes:
            raise ValueError("payload is not canonical")
        _validate_phase_roster(payloads, context)
        inputs = runtime.request_fit_inputs(payloads)
        if canonical_bytes(inputs) != prepared.inputs_bytes:
            raise PreparationError("prepared phase request configuration or source changed")
    except (TypeError, ValueError, KeyError) as error:
        raise PreparationError(f"invalid prepared phase: {error}") from error
    return payloads, inputs


def fit_phase_runtime(
    runtime,
    path: Path,
    *,
    policy,
    contact_cap: int,
    attach=None,
    client_factory=None,
    transport_factory=None,
    speech_counter=None,
    window_batch=None,
    prepared_phase: PreparedPhaseRequests | None = None,
) -> dict[str, object]:
    """Attach to the root session and fit a full phase or actual window batch.

    A cold fit requires the normal execution-plan/exposure gate plus the root
    capability. A warm fit verifies the immutable inputs without any endpoint.
    An interrupted cold fit leaves a durable contact journal and cannot restart
    under the same artifact path. Independent raw-speech window batches use
    the server multimodal input-count route, with no estimated-token fallback.
    """
    import os

    from .driver.speech_native import _LoopbackPromptAuditClient
    from .configured_transport import build_configured_transport
    from .preparation import prepare_artifact, measure_multimodal_request
    from .session.worker import attach_worker_session

    if window_batch is not None and prepared_phase is not None:
        raise PreparationError("choose either prepared phase requests or a window batch")
    context = runtime.preparation_context()
    if prepared_phase is not None:
        payloads, inputs = _consume_phase_fit(runtime, prepared_phase, context)
    else:
        # The runtime dispatches raw windows before any service attachment.
        # Frozen phase batches bypass rematerialization and remain source-bound.
        if window_batch is None:
            materialize = getattr(runtime, "materialize_request_fit_batch", None)
            if callable(materialize):
                window_batch = materialize(
                    execution_plan=context.get("execution_plan")
                )
        payloads = (
            runtime.materialize_phase_requests()
            if window_batch is None
            else window_batch.payloads
        )
        inputs = (
            runtime.request_fit_inputs(payloads)
            if window_batch is None
            else runtime.request_fit_inputs(payloads, window_batch=window_batch)
        )

    if window_batch is not None:
        if {p["sample_id"] for p in payloads} != set(context["sample_ids"]):
            raise PreparationError("window fit does not cover the runtime call roster")
    prepared_text = context["values"].get("arm") == "prepared-context-text"
    if prepared_text:
        from ..rails.prepared_text import validate_prepared_text_payload
        try:
            for payload in payloads:
                validate_prepared_text_payload(payload)
        except ValueError as error:
            raise PreparationError(str(error)) from error
    path = Path(path)

    def produce():
        from .session.resource_guard import assert_admission, resource_limits
        limits = resource_limits(context["values"])
        session, session_dir = None, None
        runtime.authorize_preparation_contacts(contact_cap=contact_cap)

        def guard():
            policy.assert_lease(
                context["data_root"],
                run_id=context["run_id"],
                attempt_id=context["attempt_id"],
            )
            if limits is not None and session is not None:
                assert_admission(session_dir, session, limits)

        guard()
        journal = path.with_name(path.name + ".contacts.jsonl")
        journal.parent.mkdir(parents=True, exist_ok=True)
        try:
            stream = journal.open("x", encoding="utf-8")
        except FileExistsError as error:
            raise PreparationError(
                "prior fit contact journal requires a new registered attempt"
            ) from error
        with stream:
            session_dir, document, session = (attach or attach_worker_session)(
                policy=policy,
                data_root=context["data_root"],
                run_id=context["run_id"],
                attempt_id=context["attempt_id"],
                required_identity=context["required_identity"],
                runtime_receipt=context["runtime_receipt"],
                runtime_root=context["runtime_root"],
            )
            client = GuardedTokenizer(
                (client_factory or _LoopbackPromptAuditClient)(
                    host=session.host, port=session.port, timeout_seconds=600.0
                ),
                guard=guard,
                contact_cap=contact_cap,
            )

            def record_contact(method, route):
                stream.write(
                    canonical_bytes(
                        {
                            "contact": client.counts.total(),
                            "method": method,
                            "route": route,
                            "run_id": context["run_id"],
                            "attempt_id": context["attempt_id"],
                            "session_id": document["session_id"],
                        }
                    ).decode()
                    + "\n"
                )
                stream.flush()
                os.fsync(stream.fileno())

            client.contact_sink = record_contact
            props = client.request_json("GET", "/props", None)
            marker = props.get("media_marker") if isinstance(props, Mapping) else None
            if not isinstance(marker, str) or not marker:
                raise PreparationError("resident tokenizer has no media marker")
            values = context["values"]
            transport = build_configured_transport(
                values,
                context["data_root"],
                # FlightRuntime owns the repository root. Lightweight legacy
                # fit fakes omit it; the default path is never consulted when
                # the prepared-cache opt-in is absent.
                repo_root=getattr(runtime, "_repo_root", Path()),
                session=session,
                runtime_receipt=context["runtime_receipt"],
                runtime_root=context["runtime_root"],
                transport_factory=transport_factory,
            )
            decoder_hashes = {
                entry.sha256
                for entry in session.model_files
                if "mmproj" not in Path(entry.path).name.lower()
            }
            if len(decoder_hashes) != 1:
                raise PreparationError("fit requires exactly one decoder identity")
            decoder_sha256 = next(iter(decoder_hashes))

            def counts(payload):
                if prepared_text:
                    return ()
                if speech_counter is not None:
                    return speech_counter(payload)
                return packet_token_counts(
                    payload,
                    feature_root=Path(
                        str(values.get("speech_feature_root", context["data_root"]))
                    ),
                    decoder_sha256=decoder_sha256,
                )

            result = fit_requests(
                payloads,
                expected_sample_ids=(
                    context["sample_ids"]
                    if window_batch is None
                    else window_batch.request_keys
                ),
                transport=transport,
                client=client,
                speech_counts=counts,
                media_marker=marker,
                slot_tokens=int(context["geometry"]["slot_tokens"]),
                fit_multiple=float(
                    values.get(
                        "prompt_fit_multiple", 1.0 if window_batch is None else 2.0
                    )
                ),
                request_key=None if window_batch is None else window_batch.request_key,
                request_measure=(
                    None if window_batch is None or "speech_feature_parts" in payloads[0]
                    else measure_multimodal_request
                ),
            )
            return {
                **result,
                "session_id": document["session_id"],
                "session_identity_sha256": digest(context["required_identity"]),
                "contact_counts": dict(client.counts),
                "contacts": client.counts.total(),
                "generation_contacts": 0,
            }

    return prepare_artifact(
        path,
        kind="request-fit",
        inputs=inputs,
        producer=produce,
        contact_class="tokenizer",
    )


def validate_live_phase_fit_config(values, program):
    """Validate the opt-in before service contact; historical defaults are inert."""
    import re

    barrier = values.get("whole_roster_wave_barrier", False)
    if not isinstance(barrier, bool):
        raise PreparationError("whole_roster_wave_barrier must be a boolean")
    spec = values.get("live_phase_fit")
    if not barrier:
        if spec is not None:
            raise PreparationError("live_phase_fit requires whole_roster_wave_barrier")
        return None
    if not isinstance(spec, Mapping) or set(spec) != {
        "run_id",
        "attempt_id",
        "contact_cap",
    }:
        raise PreparationError(
            "whole-roster live fitting requires run_id, attempt_id and contact_cap"
        )
    for key in ("run_id", "attempt_id"):
        if (
            not isinstance(spec[key], str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", spec[key]) is None
        ):
            raise PreparationError(f"live fit {key} must be one plain path segment")
    cap = spec["contact_cap"]
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise PreparationError("live fit contact_cap must be a positive integer")
    names = tuple(program.phase_names())
    if (
        not names
        or len(set(names)) != len(names)
        or any(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None for name in names
        )
    ):
        raise PreparationError("live fit requires unique plain phase names")
    if (
        values.get("prepared_request_fit") is not None
        or values.get("prompt_fit_receipt") is not None
    ):
        raise PreparationError(
            "live phase fitting cannot reuse a sealed-predecessor fit"
        )
    if values.get("native_contact_fit") is not None:
        raise PreparationError(
            "live phase fitting is mutually exclusive with native contact fitting"
        )
    return dict(spec)


def complete_phase_endpoint_count(
    phase_count: int, row_count: int, *, media_count: int = 1,
) -> int:
    """Count properties, template and text-segment tokenization endpoints."""
    if (
        isinstance(phase_count, bool) or not isinstance(phase_count, int)
        or phase_count < 1 or isinstance(row_count, bool)
        or not isinstance(row_count, int) or row_count < 1
    ):
        raise PreparationError("live fit requires positive phase and row counts")
    if isinstance(media_count, bool) or not isinstance(media_count, int) or media_count < 0:
        raise PreparationError("live fit media count must be a nonnegative integer")
    return phase_count * (1 + (2 + media_count) * row_count)


def build_live_phase_fit_gate(
    runtime,
    program,
    plan,
    *,
    client_factory=None,
    active_roster=None,
    native_active_roster=False,
):
    """Fit actual live waves under one generation lease and a separate tool plan.

    No model responses are synthesized. Each callback receives the same
    PreparedCoreRequest objects the runner will send. A failed or interrupted
    phase remains journaled and cannot be retried under this fit identity.
    """
    import os
    from dataclasses import asdict, replace

    from ..rails.core_client import PreparedCoreRequest
    from .driver.speech_native import _LoopbackPromptAuditClient
    from .preparation import prepare_artifact

    values = runtime._composed.values
    spec = validate_live_phase_fit_config(values, program)
    if spec is None:
        raise PreparationError("live phase fitting was not configured")
    if not isinstance(native_active_roster, bool):
        raise PreparationError("native_active_roster must be a boolean")
    if native_active_roster:
        if active_roster is not None:
            raise PreparationError(
                "native active roster cannot be combined with a planner roster"
            )
        if program.stop_rule != "native-answer-or-tool":
            raise PreparationError(
                "native active roster requires the native-answer-or-tool stop rule"
            )
    if spec["run_id"] == plan.run_id or spec["attempt_id"] == plan.attempt_id:
        raise PreparationError(
            "tokenizer fit requires distinct run and attempt identities"
        )
    prepared_text = values.get("arm") == "prepared-context-text"
    if not runtime.uses_speech_feature_packets() and not prepared_text:
        raise PreparationError(
            "live phase fitting requires validated feature packets or prepared text"
        )
    if runtime._session is None or runtime._transport is None:
        raise PreparationError("live phase fitting requires an attached root session")
    if active_roster is not None and not callable(active_roster):
        raise PreparationError("active_roster must derive the roster from prior decisions")
    expected_ids = tuple(sample.sample_id for sample in runtime._samples)
    phases = tuple(program.phase_names())
    required_contacts = complete_phase_endpoint_count(
        len(phases), len(expected_ids), media_count=0 if prepared_text else 1,
    )
    if spec["contact_cap"] != required_contacts:
        raise PreparationError(
            "live fit cap must equal the registered complete phase endpoint count: "
            f"expected {required_contacts}, got {spec['contact_cap']}"
        )
    fit_plan = replace(
        plan,
        run_id=spec["run_id"],
        attempt_id=spec["attempt_id"],
        planned_model_calls=spec["contact_cap"],
    ).validate()
    runtime.assert_generation_lease()
    runtime._gate_touch(runtime._gate, fit_plan)
    runtime._require_exposure_row_unconsumed(fit_plan.run_id)
    fit_root = runtime._data_root / "prepared" / fit_plan.run_id / fit_plan.attempt_id
    fit_root.mkdir(parents=True, exist_ok=True)
    identity = runtime.session_required_identity()
    session = runtime._session
    decoder_hashes = {
        entry.sha256
        for entry in session.model_files
        if "mmproj" not in Path(entry.path).name.lower()
    }
    if len(decoder_hashes) != 1:
        raise PreparationError("live fit requires one decoder identity")
    decoder_sha256 = next(iter(decoder_hashes))
    guarded = GuardedTokenizer(
        None,
        guard=runtime.assert_generation_lease,
        contact_cap=spec["contact_cap"],
    )
    completed = []
    prior_native_ids = expected_ids

    def fit_wave(phase, batch):
        nonlocal prior_native_ids
        if len(completed) >= len(phases) or phase != phases[len(completed)]:
            raise PreparationError("live fit phase order changed or repeated")
        if (
            not isinstance(batch, tuple)
            or not batch
            or any(not isinstance(request, PreparedCoreRequest) for request in batch)
        ):
            raise PreparationError("live fit requires immutable prepared core requests")
        payloads = tuple(request.as_payload() for request in batch)
        if prepared_text:
            from ..rails.prepared_text import validate_prepared_text_payload
            try:
                for payload in payloads:
                    validate_prepared_text_payload(payload)
            except ValueError as error:
                raise PreparationError(str(error)) from error
        payload_ids = tuple(payload.get("sample_id") for payload in payloads)
        if native_active_roster:
            if not completed:
                if payload_ids != expected_ids:
                    raise PreparationError(
                        "native live fit first wave requires the exact registered roster"
                    )
            else:
                selected = set(payload_ids)
                ordered_subset = tuple(
                    sample_id for sample_id in prior_native_ids
                    if sample_id in selected
                )
                if (
                    len(selected) != len(payload_ids)
                    or payload_ids != ordered_subset
                ):
                    raise PreparationError(
                        "native live fit roster cannot grow or resurrect stopped ids"
                    )
            wave_ids = payload_ids
        else:
            wave_ids = (
                expected_ids
                if active_roster is None
                else tuple(active_roster(phase))
            )
            if (
                len(set(wave_ids)) != len(wave_ids)
                or not set(wave_ids) <= set(expected_ids)
                or (phase == phases[0] and wave_ids != expected_ids)
            ):
                raise PreparationError(
                    "live fit active roster differs from the registered roster"
                )
            if set(payload_ids) != set(wave_ids) or len(payloads) != len(wave_ids):
                raise PreparationError(
                    "live fit requires the full registered roster at every phase"
                    if active_roster is None
                    else "live fit requires the complete planner-selected roster "
                    "for this phase"
                )
        runtime.assert_generation_lease()
        inputs = runtime.request_fit_inputs(payloads)
        inputs = {**inputs, "live_phase": phase, "fit_plan": asdict(fit_plan)}
        if active_roster is not None or native_active_roster:
            inputs = {**inputs, "active_sample_ids": list(wave_ids)}
        path = fit_root / (phase + ".request-fit.json")
        journal = path.with_name(path.name + ".contacts.jsonl")
        # Refuse both completed and interrupted same-identity phases.
        if path.exists() or journal.exists():
            raise PreparationError(
                "live fit identity already has contact or result evidence"
            )

        def produce():
            # A completed generation wave can outlive HTTP keep-alive. Open a
            # fresh audit client at the next phase boundary; never replay a
            # failed request. The shared guard retains cumulative contact counts.
            guarded.client = (client_factory or _LoopbackPromptAuditClient)(
                host=session.host, port=session.port, timeout_seconds=600.0
            )
            before = guarded.counts.total()
            with journal.open("x", encoding="utf-8") as stream:

                def record_contact(method, route):
                    stream.write(
                        canonical_bytes(
                            {
                                "contact": guarded.counts.total(),
                                "method": method,
                                "route": route,
                                "run_id": fit_plan.run_id,
                                "attempt_id": fit_plan.attempt_id,
                                "generation_run_id": plan.run_id,
                                "session_id": session.session_id,
                                "phase": phase,
                            }
                        ).decode()
                        + "\n"
                    )
                    stream.flush()
                    os.fsync(stream.fileno())

                guarded.contact_sink = record_contact
                props = guarded.request_json("GET", "/props", None)
                marker = (
                    props.get("media_marker") if isinstance(props, Mapping) else None
                )
                if not isinstance(marker, str) or not marker:
                    raise PreparationError("resident tokenizer has no media marker")
                result = fit_requests(
                    payloads,
                    expected_sample_ids=wave_ids,
                    transport=runtime._transport,
                    client=guarded,
                    speech_counts=lambda payload: (
                        () if prepared_text else packet_token_counts(
                            payload,
                            feature_root=Path(str(values["speech_feature_root"])),
                            decoder_sha256=decoder_sha256,
                        )
                    ),
                    media_marker=marker,
                    slot_tokens=int(runtime._adapter.serving_geometry()["slot_tokens"]),
                    fit_multiple=float(values.get("prompt_fit_multiple", 1.0)),
                )
                return {
                    **result,
                    "phase": phase,
                    "session_id": session.session_id,
                    "session_identity_sha256": digest(identity),
                    "contacts": guarded.counts.total() - before,
                    "cumulative_contacts": guarded.counts.total(),
                    "generation_contacts": 0,
                }

        receipt = prepare_artifact(
            path,
            kind="request-fit",
            inputs=inputs,
            producer=produce,
            contact_class="tokenizer",
        )
        document = json.loads(path.read_text(encoding="utf-8"))
        if document["output"].get("every_request_fits") is not True:
            raise PreparationError("live phase requests exceed the registered capacity")
        runtime.assert_generation_lease()
        completed.append({"phase": phase, **receipt})
        if native_active_roster:
            prior_native_ids = wave_ids

    fit_wave.receipts = completed
    fit_wave.execution_plan = fit_plan
    return fit_wave


def validate_native_contact_fit_config(values, program):
    """Validate opt-in fitting for actual variable native-role contacts."""
    import re

    spec = values.get("native_contact_fit")
    if spec is None:
        return None
    required = {"run_id", "attempt_id", "contact_cap"}
    allowed = required | {"max_speech_packets"}
    if (
        not isinstance(spec, Mapping)
        or not required <= set(spec)
        or not set(spec) <= allowed
    ):
        raise PreparationError(
            "native contact fitting requires run_id, attempt_id and contact_cap"
        )
    for key in ("run_id", "attempt_id"):
        if (
            not isinstance(spec[key], str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", spec[key]) is None
        ):
            raise PreparationError(
                f"native contact fit {key} must be one plain path segment"
            )
    cap = spec["contact_cap"]
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise PreparationError(
            "native contact fit contact_cap must be a positive integer"
        )
    max_speech_packets = spec.get("max_speech_packets", 1)
    if (
        isinstance(max_speech_packets, bool)
        or not isinstance(max_speech_packets, int)
        or max_speech_packets < 1
    ):
        raise PreparationError(
            "native contact fit max_speech_packets must be a positive integer"
        )
    barrier = values.get("whole_roster_wave_barrier", False)
    if not isinstance(barrier, bool):
        raise PreparationError("whole_roster_wave_barrier must be a boolean")
    conflicts = any(
        values.get(key) is not None
        for key in ("live_phase_fit", "prepared_request_fit", "prompt_fit_receipt")
    ) or barrier
    if conflicts:
        raise PreparationError(
            "native contact fitting is mutually exclusive with other fit modes "
            "and the whole-roster wave barrier"
        )
    if getattr(program, "stop_rule", None) != "native-role-episode":
        raise PreparationError(
            "native contact fitting requires the native-role-episode stop rule"
        )
    max_contacts = getattr(program, "max_contacts", None)
    if (
        isinstance(max_contacts, bool)
        or not isinstance(max_contacts, int)
        or max_contacts < 1
    ):
        raise PreparationError(
            "native contact fitting requires a positive program.max_contacts"
        )
    return {**dict(spec), "max_speech_packets": max_speech_packets}


def _native_contact_control_identity(
    payload: Mapping[str, object],
) -> tuple[str, str]:
    """Return the sample and final control contact bound by one request."""
    sample_id = payload.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id:
        raise PreparationError("native contact has no sample_id")
    history = payload.get("history")
    if (
        not isinstance(history, Sequence)
        or isinstance(history, (str, bytes))
        or not history
        or any(not isinstance(item, Mapping) for item in history)
    ):
        raise PreparationError("native contact has no bound control history")
    controls = [item for item in history if item.get("role") == "control"]
    if len(controls) != 1 or controls[0] is not history[-1]:
        raise PreparationError(
            "native contact requires exactly one final control binding"
        )
    contact_id = controls[0].get("contact_id")
    if not isinstance(contact_id, str) or not contact_id:
        raise PreparationError("native contact has no agent_contact_id")
    return sample_id, contact_id


def _native_contact_identity(
    payload: Mapping[str, object],
) -> tuple[str, str, tuple[dict[str, object], ...]]:
    sample_id, contact_id = _native_contact_control_identity(payload)
    descriptors = payload.get("speech_feature_parts")
    if (
        not isinstance(descriptors, list)
        or not descriptors
        or any(
            not isinstance(descriptor, Mapping)
            or set(descriptor) != {"packet_id", "sha256", "role"}
            or descriptor.get("role") not in {"query", "key"}
            or not isinstance(descriptor.get("packet_id"), str)
            or not descriptor["packet_id"]
            or not isinstance(descriptor.get("sha256"), str)
            or len(descriptor["sha256"]) != 64
            or any(
                character not in "0123456789abcdef"
                for character in descriptor["sha256"]
            )
            for descriptor in descriptors
        )
        or sum(descriptor["role"] == "query" for descriptor in descriptors) != 1
    ):
        raise PreparationError(
            "native contact speech feature descriptor binding is malformed"
        )
    return sample_id, contact_id, tuple(dict(item) for item in descriptors)


def _native_raw_contact_identity(
    payload: Mapping[str, object],
) -> tuple[str, str, dict[str, str]]:
    """Validate the source identity required for one raw native contact."""
    sample_id, contact_id = _native_contact_control_identity(payload)
    if "speech_feature_parts" in payload:
        raise PreparationError("native raw contact refuses mixed feature input")
    raw = payload.get("raw_speech_query")
    media_relpath = payload.get("media_relpath")
    if (
        not isinstance(raw, Mapping)
        or set(raw) != {"media_relpath", "sha256"}
        or not isinstance(media_relpath, str)
        or not media_relpath
        or raw.get("media_relpath") != media_relpath
        or not isinstance(raw.get("sha256"), str)
        or len(raw["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in raw["sha256"])
    ):
        raise PreparationError("native raw contact source identity is malformed")
    return sample_id, contact_id, {
        "media_relpath": media_relpath,
        "sha256": raw["sha256"],
    }


def build_native_contact_fit_gate(
    runtime,
    program,
    base_plan,
    *,
    client_factory=None,
):
    """Fit only realized native-role requests under the bound execution lease.

    This gate certifies a variable trajectory one actual immutable request at
    a time. It is not a whole-roster static capacity guarantee: branches that
    never execute have no request body and receive no fit receipt. The plan
    reserves the complete endpoint protocol for each possible request: feature
    contacts use tokenizer endpoints, and raw-speech contacts use exactly one
    resident multimodal measurement endpoint. A realized feature contact spends
    only its actual packet count plus three endpoints.
    """
    import os
    import threading
    from dataclasses import asdict, replace

    from ..rails.core_client import PreparedCoreRequest
    from .driver.speech_native import _LoopbackPromptAuditClient
    from .preparation import prepare_artifact

    values = runtime._composed.values
    spec = validate_native_contact_fit_config(values, program)
    if spec is None:
        raise PreparationError("native contact fitting was not configured")
    if (
        spec["run_id"] == base_plan.run_id
        or spec["attempt_id"] == base_plan.attempt_id
    ):
        raise PreparationError(
            "tokenizer fit requires distinct run and attempt identities"
        )
    feature_packets = runtime.uses_speech_feature_packets()
    if not feature_packets and runtime._arm() != "raw-speech-agent-native-tools":
        raise PreparationError(
            "native raw contact fitting requires the raw-speech-agent-native-tools arm"
        )
    if runtime._session is None or runtime._transport is None:
        raise PreparationError(
            "native contact fitting requires an attached root session"
        )
    expected_ids = tuple(sample.sample_id for sample in runtime._samples)
    if (
        not expected_ids
        or any(
            not isinstance(sample_id, str) or not sample_id
            for sample_id in expected_ids
        )
        or len(set(expected_ids)) != len(expected_ids)
    ):
        raise PreparationError(
            "native contact fitting requires a unique registered sample roster"
        )
    roster_loader = getattr(runtime, "execution_unit_roster", None)
    unit_roster = roster_loader() if callable(roster_loader) else None
    if unit_roster is not None:
        unit_roster.validate(parent_sample_ids=expected_ids, max_contacts=program.max_contacts)
    maximum_requests = (
        len(unit_roster.units) if unit_roster is not None else len(expected_ids)
    ) * program.max_contacts
    # Feature contacts need /props, /apply-template, and one /tokenize per
    # feature packet plus one prompt tokenization. Raw contacts instead use
    # the resident multimodal counting endpoint on the rendered WAV body.
    endpoints_per_contact = spec["max_speech_packets"] + 3 if feature_packets else 1
    required_cap = maximum_requests * endpoints_per_contact
    if spec["contact_cap"] != required_cap:
        raise PreparationError(
            "native contact fit cap must equal the registered maximum endpoint count"
        )
    fit_plan = replace(
        base_plan,
        run_id=spec["run_id"],
        attempt_id=spec["attempt_id"],
        planned_model_calls=spec["contact_cap"],
    ).validate()
    runtime.assert_generation_lease()
    runtime._gate_touch(runtime._gate, fit_plan)
    runtime._require_exposure_row_unconsumed(fit_plan.run_id)
    fit_root = runtime._data_root / "prepared" / fit_plan.run_id / fit_plan.attempt_id
    fit_root.mkdir(parents=True, exist_ok=True)
    identity = runtime.session_required_identity()
    session = runtime._session
    decoder_sha256 = None
    if feature_packets:
        decoder_hashes = {
            entry.sha256
            for entry in session.model_files
            if "mmproj" not in Path(entry.path).name.lower()
        }
        if len(decoder_hashes) != 1:
            raise PreparationError("native contact fit requires one decoder identity")
        decoder_sha256 = next(iter(decoder_hashes))
    guarded = GuardedTokenizer(
        None,
        guard=runtime.assert_generation_lease,
        contact_cap=spec["contact_cap"],
    )
    completed: list[dict[str, object]] = []
    used_contact_ids: set[str] = set()
    sample_contacts: Counter[str] = Counter()
    fit_lock = threading.Lock()

    def fit_contact(prepared_request):
        if not isinstance(prepared_request, PreparedCoreRequest):
            raise PreparationError(
                "native contact fit requires an immutable PreparedCoreRequest"
            )
        try:
            payload = prepared_request.as_payload()
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise PreparationError(f"invalid prepared native contact: {error}") from error
        if not isinstance(payload, dict):
            raise PreparationError("prepared native contact payload must be an object")
        with fit_lock:
            if feature_packets:
                if "raw_speech_query" in payload:
                    raise PreparationError(
                        "native feature contact refuses raw speech input"
                    )
                sample_id, contact_id, descriptors = _native_contact_identity(payload)
                raw_speech_query = None
            else:
                sample_id, contact_id, raw_speech_query = _native_raw_contact_identity(
                    payload
                )
                descriptors = ()
            if sample_id not in expected_ids:
                raise PreparationError(
                    "native contact sample differs from the registered roster"
                )
            if contact_id in used_contact_ids:
                raise PreparationError(
                    f"native contact repeated agent_contact_id {contact_id!r}"
                )
            unit_fields = {}
            budget_key = sample_id
            if unit_roster is not None:
                unit = runtime.execution_unit_for_contact(sample_id, contact_id)
                if feature_packets:
                    runtime.validate_execution_unit_feature_payload(unit, payload)
                else:
                    runtime.validate_execution_unit_observation(unit, raw_speech_query)
                budget_key = unit.request_key
                unit_fields = {
                    "execution_unit_id": unit.request_key,
                    "execution_unit_binding": unit.as_json(),
                    "execution_unit_roster_sha256": unit_roster.content_hash(),
                }
            if sample_contacts[budget_key] >= program.max_contacts:
                raise PreparationError(
                    "native contact exceeded its per-unit contact ceiling"
                    if unit_roster is not None
                    else "native contact exceeded its per-sample contact ceiling"
                )
            if feature_packets and len(descriptors) > spec["max_speech_packets"]:
                raise PreparationError(
                    "native contact speech feature descriptor count exceeds its "
                    "registered maximum"
                )
            runtime.assert_generation_lease()
            body = runtime._transport.render_request(prepared_request.payload_bytes)
            if not isinstance(body, Mapping):
                raise PreparationError("native contact transport returned no request body")
            if feature_packets:
                rendered_descriptors = rendered_speech_feature_descriptors(body)
                if rendered_descriptors != descriptors:
                    raise PreparationError(
                        "native contact rendered descriptor binding differs from its "
                        "prepared request"
                    )
            elif rendered_raw_speech_sha256(body) != raw_speech_query["sha256"]:
                raise PreparationError(
                    "native raw contact rendered audio differs from its prepared request"
                )
            contact_identity_sha256 = digest(
                {"sample_id": sample_id, "agent_contact_id": contact_id}
            )
            path = fit_root / f"{contact_identity_sha256}.request-fit.json"
            journal = path.with_name(path.name + ".contacts.jsonl")
            if path.exists() or journal.exists():
                raise PreparationError(
                    "native contact fit identity already has contact or result evidence"
                )
            inputs = runtime.request_fit_inputs((payload,))
            inputs = {
                **inputs,
                "native_contact": {
                    "sample_id": sample_id,
                    "agent_contact_id": contact_id,
                    "contact_identity_sha256": contact_identity_sha256,
                    **(
                        {"speech_packet_count": len(descriptors)}
                        if feature_packets
                        else {"raw_speech_query": raw_speech_query}
                    ),
                    "capacity_scope": "actual-variable-trajectory-contact",
                    **unit_fields,
                },
                "fit_plan": asdict(fit_plan),
            }
            used_contact_ids.add(contact_id)
            sample_contacts[budget_key] += 1

            def produce():
                guarded.client = (client_factory or _LoopbackPromptAuditClient)(
                    host=session.host, port=session.port, timeout_seconds=600.0
                )
                before = guarded.counts.copy()
                with journal.open("x", encoding="utf-8") as stream:

                    def record_contact(method, route):
                        stream.write(
                            canonical_bytes(
                                {
                                    "contact": guarded.counts.total(),
                                    "method": method,
                                    "route": route,
                                    "run_id": fit_plan.run_id,
                                    "attempt_id": fit_plan.attempt_id,
                                    "generation_run_id": base_plan.run_id,
                                    "session_id": session.session_id,
                                    "sample_id": sample_id,
                                    "agent_contact_id": contact_id,
                                    "contact_identity_sha256": contact_identity_sha256,
                                    **unit_fields,
                                }
                            ).decode()
                            + "\n"
                        )
                        stream.flush()
                        os.fsync(stream.fileno())

                    guarded.contact_sink = record_contact
                    marker = None
                    if feature_packets:
                        props = guarded.request_json("GET", "/props", None)
                        marker = (
                            props.get("media_marker")
                            if isinstance(props, Mapping)
                            else None
                        )
                        if not isinstance(marker, str) or not marker:
                            raise PreparationError(
                                "resident tokenizer has no media marker"
                            )
                    from .preparation import measure_multimodal_request
                    speech_counts = (
                        (
                            lambda actual: packet_token_counts(
                                actual,
                                feature_root=Path(str(values["speech_feature_root"])),
                                decoder_sha256=decoder_sha256,
                            )
                        )
                        if feature_packets
                        else (lambda _actual: ())
                    )
                    result = fit_requests(
                        (payload,),
                        expected_sample_ids=(sample_id,),
                        transport=runtime._transport,
                        client=guarded,
                        speech_counts=speech_counts,
                        media_marker=marker,
                        slot_tokens=int(
                            runtime._adapter.serving_geometry()["slot_tokens"]
                        ),
                        fit_multiple=float(values.get("prompt_fit_multiple", 1.0)),
                        rendered_bodies=(body,),
                        request_measure=(
                            None if feature_packets else measure_multimodal_request
                        ),
                    )
                    contact_counts = guarded.counts - before
                    return {
                        **result,
                        "sample_id": sample_id,
                        "agent_contact_id": contact_id,
                        "contact_identity_sha256": contact_identity_sha256,
                        **(
                            {"speech_packet_count": len(descriptors)}
                            if feature_packets
                            else {"raw_speech_query": raw_speech_query}
                        ),
                        "capacity_scope": "actual-variable-trajectory-contact",
                        **unit_fields,
                        "session_id": session.session_id,
                        "session_identity_sha256": digest(identity),
                        "contact_counts": dict(contact_counts),
                        "contacts": contact_counts.total(),
                        "cumulative_contacts": guarded.counts.total(),
                        "generation_contacts": 0,
                    }

            receipt = prepare_artifact(
                path,
                kind="request-fit",
                inputs=inputs,
                producer=produce,
                contact_class="tokenizer",
            )
            document = json.loads(path.read_text(encoding="utf-8"))
            if document["output"].get("every_request_fits") is not True:
                raise PreparationError(
                    "native contact request exceeds the registered capacity"
                )
            runtime.assert_generation_lease()
            completed.append(
                {
                    "sample_id": sample_id,
                    "agent_contact_id": contact_id,
                    "contact_identity_sha256": contact_identity_sha256,
                    **receipt,
                }
            )

    fit_contact.receipts = completed
    fit_contact.execution_plan = fit_plan
    return fit_contact


def revalidate_phase_fit(runtime, *, registration, registration_sha256, data_root):
    """Derive a contact-free fit after a reviewed runtime-only repair.

    Require the complete real boundary and every non-implementation input to
    match the immutable measurement. This operation neither refreshes the
    service attestation nor authorizes generation. The caller must register
    the exact implementation change before materializing dataset requests.
    """
    import hashlib
    from copy import deepcopy
    from .preparation import load_artifact, prepare_artifact
    from .model.paths import _normalized_relative_path, _resolve_confined
    from .model import FrozenCoreError

    root = Path(data_root).resolve()
    if (
        registration.get("schema") != "saea-request-fit-revalidation-registration-v1"
        or registration.get("execution_profile") != "model-free-check"
        or registration.get("new_endpoint_contacts") != 0
        or not registration.get("reason")
        or digest(registration) != registration_sha256
    ):
        raise PreparationError("invalid model-free fit revalidation registration")

    def confined(relative, *, exists):
        try:
            return _resolve_confined(
                root, _normalized_relative_path(relative, "fit revalidation"),
                root, "fit revalidation", strict=exists,
            )
        except (ValueError, OSError, FrozenCoreError) as error:
            raise PreparationError(f"invalid fit revalidation path: {error}") from error

    source_pin = registration["source"]
    source = confined(source_pin["relpath"], exists=True)
    destination = confined(registration["output_relpath"], exists=False)
    if source == destination:
        raise PreparationError("fit revalidation must preserve its source")
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != source_pin["sha256"]:
        raise PreparationError("fit revalidation source hash mismatch")
    document = json.loads(raw)
    old_inputs = document["inputs"]
    if digest(old_inputs) != registration["source_inputs_sha256"]:
        raise PreparationError("fit revalidation source inputs mismatch")
    measured = load_artifact(
        source, expected_sha256=source_pin["sha256"], kind="request-fit", inputs=old_inputs,
    )
    if document["contact_class"] != "tokenizer" or "revalidation" in measured:
        raise PreparationError("fit revalidation requires an original measured artifact")

    journal_pin = registration["source_journal"]
    journal_path = confined(journal_pin["relpath"], exists=True)
    if journal_path != source.with_name(source.name + ".contacts.jsonl"):
        raise PreparationError("fit revalidation source journal path mismatch")
    journal_raw = journal_path.read_bytes()
    if hashlib.sha256(journal_raw).hexdigest() != journal_pin["sha256"]:
        raise PreparationError("fit revalidation source journal hash mismatch")
    journal = [json.loads(line) for line in journal_raw.splitlines()]
    if (
        len(journal) != journal_pin["line_count"] or len(journal) != measured["contacts"]
        or measured.get("generation_contacts") != 0
        or any(row.get("contact") != i for i, row in enumerate(journal, 1))
        or dict(Counter(f"{row['method']} {row['route']}" for row in journal))
        != measured["contact_counts"]
    ):
        raise PreparationError("fit revalidation source journal accounting mismatch")

    expected = deepcopy(old_inputs)
    implementation = expected["sources"]["implementation"]
    changes = registration["implementation_changes"]
    if not isinstance(changes, Mapping) or not changes or not set(changes) <= {
        "runtime", "preparation_fit"
    }:
        raise PreparationError("fit revalidation permits only reviewed runtime/fit code changes")
    for name, change in changes.items():
        if (
            not isinstance(change, Mapping) or set(change) != {"before", "after"}
            or implementation.get(name) != change["before"]
            or change["before"] == change["after"]
            or not isinstance(change["after"], str) or len(change["after"]) != 64
            or any(c not in "0123456789abcdef" for c in change["after"])
        ):
            raise PreparationError("fit revalidation implementation binding mismatch")
        implementation[name] = change["after"]

    context = runtime.preparation_context()
    payloads = runtime.materialize_phase_requests()
    _validate_phase_roster(payloads, context)
    current = runtime.request_fit_inputs(payloads)
    if current != expected or boundary_identity(payloads) != current["sources"]["boundary_sha256"]:
        raise PreparationError("fit revalidation changed requests, config, service, or sources")
    ids = set(context["sample_ids"])
    rows = measured.get("rows")
    if (
        measured.get("every_request_fits") is not True
        or measured.get("boundary_sha256") != current["sources"]["boundary_sha256"]
        or measured.get("sample_count") != len(ids)
        or not isinstance(rows, list) or len(rows) != len(ids)
        or any(not isinstance(row, dict) or row.get("fits") is not True for row in rows)
        or {row.get("sample_id") for row in rows} != ids
    ):
        raise PreparationError("fit revalidation source does not certify the full roster")
    output = {
        **measured,
        "contacts": 0, "contact_counts": {}, "generation_contacts": 0,
        "revalidation": {
            "schema": "saea-request-fit-revalidation-v1",
            "registration_sha256": registration_sha256,
            "source": dict(source_pin), "source_journal": dict(journal_pin),
            "source_output_sha256": document["output_sha256"],
            "source_inputs_sha256": digest(old_inputs),
            "source_measurement_contacts": measured.get("contacts"),
            "source_measurement_contact_counts": measured.get("contact_counts"),
            "implementation_changes": changes, "new_endpoint_contacts": 0,
            "reason": registration["reason"],
        },
    }
    return prepare_artifact(
        destination, kind="request-fit", inputs=current,
        producer=lambda: output, contact_class="model-free",
    )
