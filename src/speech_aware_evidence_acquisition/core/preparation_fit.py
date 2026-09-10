"""Shared full-roster fitting of actual transport requests, without generation."""

from __future__ import annotations

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
) -> dict[str, object]:
    """Fit every actual body; retain only hashes, counts, and sample identities.

    Transport rendering is the exact function used by generation. A supplied
    speech-count resolver supports both feature packets and already measured
    raw-speech repair windows; it must never substitute duration estimates.
    """
    ids = [request_key(p) if request_key else p.get("sample_id") for p in payloads]
    if (
        not ids
        or len(set(ids)) != len(ids)
        or len(set(expected_sample_ids)) != len(expected_sample_ids)
        or set(ids) != set(expected_sample_ids)
    ):
        raise PreparationError("fit must cover the complete unique roster")
    rows = []
    for payload in payloads:
        body = transport.render_request(canonical_bytes(payload))
        if request_measure is None:
            row = measure_request(
                client,
                body,
                media_marker=media_marker,
                speech_tokens=speech_counts(payload),
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
    path = Path(path)

    def produce():
        runtime.authorize_preparation_contacts(contact_cap=contact_cap)

        def guard():
            policy.assert_lease(
                context["data_root"],
                run_id=context["run_id"],
                attempt_id=context["attempt_id"],
            )

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
    return dict(spec)


def build_live_phase_fit_gate(runtime, program, plan, *, client_factory=None):
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
    if spec["run_id"] == plan.run_id or spec["attempt_id"] == plan.attempt_id:
        raise PreparationError(
            "tokenizer fit requires distinct run and attempt identities"
        )
    if not runtime.uses_speech_feature_packets():
        raise PreparationError(
            "live phase fitting currently requires validated feature packets"
        )
    if runtime._session is None or runtime._transport is None:
        raise PreparationError("live phase fitting requires an attached root session")
    expected_ids = tuple(sample.sample_id for sample in runtime._samples)
    phases = tuple(program.phase_names())
    required_contacts = len(phases) * (1 + 3 * len(expected_ids))
    if spec["contact_cap"] != required_contacts:
        raise PreparationError(
            "live fit cap must equal the registered complete phase endpoint count"
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
        (client_factory or _LoopbackPromptAuditClient)(
            host=session.host, port=session.port, timeout_seconds=600.0
        ),
        guard=runtime.assert_generation_lease,
        contact_cap=spec["contact_cap"],
    )
    completed = []

    def fit_wave(phase, batch):
        if len(completed) >= len(phases) or phase != phases[len(completed)]:
            raise PreparationError("live fit phase order changed or repeated")
        if (
            not isinstance(batch, tuple)
            or not batch
            or any(not isinstance(request, PreparedCoreRequest) for request in batch)
        ):
            raise PreparationError("live fit requires immutable prepared core requests")
        payloads = tuple(request.as_payload() for request in batch)
        if {p.get("sample_id") for p in payloads} != set(expected_ids) or len(
            payloads
        ) != len(expected_ids):
            raise PreparationError(
                "live fit requires the full registered roster at every phase"
            )
        runtime.assert_generation_lease()
        inputs = runtime.request_fit_inputs(payloads)
        inputs = {**inputs, "live_phase": phase, "fit_plan": asdict(fit_plan)}
        path = fit_root / (phase + ".request-fit.json")
        journal = path.with_name(path.name + ".contacts.jsonl")
        # Refuse both completed and interrupted same-identity phases.
        if path.exists() or journal.exists():
            raise PreparationError(
                "live fit identity already has contact or result evidence"
            )

        def produce():
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
                    expected_sample_ids=expected_ids,
                    transport=runtime._transport,
                    client=guarded,
                    speech_counts=lambda payload: packet_token_counts(
                        payload,
                        feature_root=Path(str(values["speech_feature_root"])),
                        decoder_sha256=decoder_sha256,
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

    fit_wave.receipts = completed
    fit_wave.execution_plan = fit_plan
    return fit_wave
