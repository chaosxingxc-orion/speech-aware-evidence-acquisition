"""Shared full-roster fitting of actual transport requests, without generation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .preparation import PreparationError, canonical_bytes, digest, measure_request


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


def boundary_identity(payloads: Sequence[Mapping[str, object]]) -> str:
    # These two routing values never enter the prompt; worker assignment may
    # change them. Completion limits and every model-visible field stay bound.
    normalized = []
    for payload in payloads:
        row = {k: v for k, v in payload.items() if k != "request_id"}
        if isinstance(row.get("decoding_params"), Mapping):
            row["decoding_params"] = {
                k: v for k, v in row["decoding_params"].items() if k != "id_slot"
            }
        normalized.append(row)
    return digest(sorted(normalized, key=lambda p: str(p.get("sample_id"))))


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
) -> dict[str, object]:
    """Fit every actual body; retain only hashes, counts, and sample identities.

    Transport rendering is the exact function used by generation. A supplied
    speech-count resolver supports both feature packets and already measured
    raw-speech repair windows; it must never substitute duration estimates.
    """
    ids = [p.get("sample_id") for p in payloads]
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
        row = measure_request(
            client,
            body,
            media_marker=media_marker,
            speech_tokens=speech_counts(payload),
            slot_tokens=slot_tokens,
            fit_multiple=fit_multiple,
            special_tokens=special_tokens,
        )
        rows.append({"sample_id": payload["sample_id"], **row})
    worst = min(rows, key=lambda row: row["margin_tokens"])
    return {
        "sample_count": len(rows),
        "rows": rows,
        "boundary_sha256": boundary_identity(payloads),
        "every_request_fits": all(row["fits"] for row in rows),
        "worst_sample_id": worst["sample_id"],
        "minimum_margin_tokens": worst["margin_tokens"],
    }


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
) -> dict[str, object]:
    """Attach to the root session and prepare one single-phase full-roster fit.

    A cold fit requires the normal execution-plan/exposure gate plus the root
    capability. A warm fit verifies the immutable inputs without any endpoint.
    An interrupted cold fit leaves a durable contact journal and cannot restart
    under the same artifact path.
    """
    import os

    from .driver.speech_native import _LoopbackPromptAuditClient
    from .base import TRANSPORTS
    from .preparation import prepare_artifact
    from .session.worker import attach_worker_session

    context = runtime.preparation_context()
    payloads = runtime.materialize_phase_requests()
    inputs = runtime.request_fit_inputs(payloads)
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
            transport = (
                transport_factory or TRANSPORTS.resolve(str(values["transport"]))
            )(
                values,
                context["data_root"],
                session=session,
                runtime_receipt=context["runtime_receipt"],
                runtime_root=context["runtime_root"],
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
                expected_sample_ids=context["sample_ids"],
                transport=transport,
                client=client,
                speech_counts=counts,
                media_marker=marker,
                slot_tokens=int(context["geometry"]["slot_tokens"]),
                fit_multiple=float(values.get("prompt_fit_multiple", 1.0)),
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
