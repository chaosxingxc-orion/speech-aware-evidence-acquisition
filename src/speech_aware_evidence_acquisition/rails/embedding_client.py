"""P-EMB embedding-tier client (SAEA-PROBE-pemb1-78 / SAEA-PROBE-pemb2-552,
``docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md``).

Deliberately a SIBLING of ``rails.core_client`` (:class:`CoreClient` /
:class:`FrozenCoreClient`), never a variant of it: the embedding tier speaks
a completely different wire protocol against a completely different
resident server. E-0's own binding facts (prereg opening paragraph, quoted
here so this module's own request-shape choices are traceable to them):

- pinned q4km GGUF + mmproj, ``--embedding --pooling mean``, its own port
  (never the same port a generation ``LlamaServerTransport`` talks to --
  embedding-mode and generation-mode servers can never coexist, module
  constant :data:`GENERATION_COEXISTENCE_NOTE`).
- ``LLAMA_MEDIA_MARKER`` is pinned via env AND independently re-verified
  against the live server's own ``GET /props`` before any request is sent
  (:meth:`EmbeddingClient.verify_media_marker`) -- fail-closed on mismatch,
  never trusted from the env alone.
- audio request shape is NOT chat-style ``input_audio``: it is
  ``{"content": [{"prompt_string": <marker>, "multimodal_data": [<base64
  audio>]}]}`` against ``POST /embedding``. Text request shape is plain
  content strings: ``{"content": [<text>]}``. NO instruct prefix on either
  side (E-0 measured a prefix shifting the pooled vector more than swapping
  the audio does).
- outputs are L2-normalized, dim :data:`EMBEDDING_DIM` (2048), bit-
  deterministic (encode+pool, zero sampling -- this client accepts no
  decoding-params argument anywhere, so there is no seam through which a
  sampling parameter could leak into a request).

Every request is a frozen-core contact (encode+pool) and is ledgered as a
call exactly like a generation request (prereg section 4): every
:meth:`embed_text`/:meth:`embed_audio` call is recorded as an
:class:`EmbeddingContact` (id, kind, latency, dims) via :attr:`contacts`,
mirroring ``rails.core_client.FrozenCoreClient.timings``.

Loopback-only (I5, reused via ``core.session.require_loopback`` rather than
re-implemented): the constructor refuses any ``base_url`` that is not
``127.0.0.1``/``::1``/``localhost``.

Zero live model contact in this module or its own test suite -- every test
drives a fake ``post``/``get`` pair or :class:`MockEmbeddingClient`.
"""

from __future__ import annotations

import base64
import json
import math
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol, Sequence, runtime_checkable

from ..core.session import SessionError, require_loopback
from .errors import RailsError

EMBEDDING_DIM = 2048

LLAMA_MEDIA_MARKER_ENV = "LLAMA_MEDIA_MARKER"
# The field this client expects GET /props to carry the live server's own
# media-placeholder token under. Established by the E-0 feasibility probe
# against the real pinned server (prereg: "verify the marker against GET
# /props at runtime, fail-closed on mismatch") -- if a future llama.cpp
# build ever renames this field, verify_media_marker refuses LOUD (missing
# key) rather than silently skipping verification; it never falls back to
# trusting the env-pinned value unverified.
PROPS_MEDIA_MARKER_FIELD = "media_marker"

EMBEDDING_ENDPOINT_PATH = "/embedding"
PROPS_ENDPOINT_PATH = "/props"

GENERATION_COEXISTENCE_NOTE = (
    "an embedding-mode llama-server (--embedding --pooling mean, forced n_batch 512) can "
    "never coexist with a generation-mode server (GPU time-shared, single resident model); "
    "the launcher must check for and refuse an orphan generation server before starting one"
)


class EmbeddingClientError(RailsError):
    """A malformed embedding request/response, a marker-verification
    failure, a fail-closed vector-legality violation (wrong dim / non-finite
    value), or a call made out of the required order (marker not yet
    verified, or after :meth:`EmbeddingClient.close`)."""


def resolve_expected_media_marker(env: Mapping[str, str] | None = None) -> str:
    """The pinned :data:`LLAMA_MEDIA_MARKER_ENV` value -- fail-closed if
    unset/empty (module docstring: pinned via env, never a code default).
    ``env`` defaults to the real process environment; injectable for tests."""

    import os

    source = os.environ if env is None else env
    value = source.get(LLAMA_MEDIA_MARKER_ENV)
    if not isinstance(value, str) or not value:
        raise EmbeddingClientError(
            f"{LLAMA_MEDIA_MARKER_ENV} is unset or empty -- the embedding-tier marker must be "
            "pinned via env before any embedding contact (prereg binding decisions)"
        )
    return value


def _iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _assert_vector_legal(values: Sequence[float], *, context: str) -> None:
    """Fail-closed on dim != :data:`EMBEDDING_DIM` or any non-finite
    (NaN/Inf) component -- never a soft flag."""

    if len(values) != EMBEDDING_DIM:
        raise EmbeddingClientError(
            f"{context}: embedding dim {len(values)} != pinned {EMBEDDING_DIM}"
        )
    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise EmbeddingClientError(
                f"{context}: embedding vector contains a non-finite value at index {index}: {value!r}"
            )


def _unwrap_pooled_vector(raw_vector: object, *, context: str) -> tuple[float, ...]:
    """llama.cpp's ``/embedding`` response nests a pooled vector as either a
    flat list of numbers or a single-row list-of-lists (per-token shape
    collapsed to one row by ``--pooling mean``) -- accept both, fail-closed
    on anything else (more than one row, empty, non-numeric)."""

    candidate = raw_vector
    if isinstance(candidate, list) and candidate and all(isinstance(item, list) for item in candidate):
        if len(candidate) != 1:
            raise EmbeddingClientError(
                f"{context}: expected a single pooled row, got {len(candidate)} rows "
                "(--pooling mean should always collapse to exactly one)"
            )
        candidate = candidate[0]
    if not isinstance(candidate, list) or not candidate:
        raise EmbeddingClientError(
            f"{context}: embedding vector must be a non-empty list of numbers, got {raw_vector!r}"
        )
    try:
        return tuple(float(item) for item in candidate)
    except (TypeError, ValueError) as error:
        raise EmbeddingClientError(
            f"{context}: embedding vector contains a non-numeric entry: {error}"
        ) from error


def _parse_embedding_response(raw: bytes, *, expected_count: int, context: str) -> list[tuple[float, ...]]:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EmbeddingClientError(f"{context}: embedding server returned invalid JSON: {error}") from error
    if not isinstance(parsed, list):
        raise EmbeddingClientError(
            f"{context}: embedding response must be a JSON array, got {type(parsed).__name__}"
        )
    if len(parsed) != expected_count:
        raise EmbeddingClientError(
            f"{context}: embedding response carries {len(parsed)} row(s), expected {expected_count}"
        )
    vectors: list[tuple[float, ...]] = []
    for row in parsed:
        if not isinstance(row, Mapping) or "embedding" not in row:
            raise EmbeddingClientError(f"{context}: embedding response row missing 'embedding' field: {row!r}")
        vectors.append(_unwrap_pooled_vector(row["embedding"], context=context))
    return vectors


@dataclass(frozen=True)
class EmbeddingVector:
    """One embedded contact's own pooled vector -- ``values`` is a plain
    ``tuple[float, ...]`` (not a numpy array) so this dataclass stays
    hashable/comparable/picklable without a numpy dependency at this layer;
    callers that want array math (``analysis.pemb_read``'s cosine matcher)
    convert at the point of use."""

    contact_id: str
    kind: str  # "audio" | "text"
    values: tuple[float, ...]

    @property
    def dims(self) -> int:
        return len(self.values)


@dataclass(frozen=True)
class EmbeddingContact:
    """One :meth:`EmbeddingClient.embed_text`/:meth:`embed_audio` call's own
    per-contact record (module docstring: "every request ... is ledgered as
    a call")."""

    contact_id: str
    kind: str
    started_at: str
    latency_seconds: float
    dims: int

    def as_json(self) -> dict[str, object]:
        return {
            "contact_id": self.contact_id,
            "kind": self.kind,
            "started_at": self.started_at,
            "latency_seconds": self.latency_seconds,
            "dims": self.dims,
        }


@runtime_checkable
class EmbeddingClientProtocol(Protocol):
    """The minimal shape :mod:`rails.probes.pemb_flight` drives -- satisfied
    by both the real :class:`EmbeddingClient` and :class:`MockEmbeddingClient`."""

    def verify_media_marker(self) -> Mapping[str, object]: ...

    def embed_text(self, *, contact_id: str, text: str) -> EmbeddingVector: ...

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes) -> EmbeddingVector: ...


def _default_post(timeout_seconds: float) -> Callable[[str, bytes], bytes]:
    def post(url: str, body: bytes) -> bytes:
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()

    return post


def _default_get(timeout_seconds: float) -> Callable[[str], bytes]:
    def get(url: str) -> bytes:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            return response.read()

    return get


class EmbeddingClient:
    """The real embedding-tier client -- ``POST /embedding`` against a
    resident, embedding-mode llama-server. ``post``/``get`` are injectable
    (default: stdlib ``urllib``, mirroring ``core.model.transport``'s own
    ``_default_post``) so every test drives a fake transport, never a real
    socket."""

    def __init__(
        self,
        *,
        base_url: str,
        expected_media_marker: str,
        post: Callable[[str, bytes], bytes] | None = None,
        get: Callable[[str], bytes] | None = None,
        timeout_seconds: float = 60.0,
        now: Callable[[], float] = time.time,
    ) -> None:
        try:
            require_loopback(base_url)
        except SessionError as error:
            raise EmbeddingClientError(str(error)) from error
        if not isinstance(expected_media_marker, str) or not expected_media_marker:
            raise EmbeddingClientError("expected_media_marker must be a non-empty string")
        self._base_url = base_url.rstrip("/")
        self._expected_marker = expected_media_marker
        self._post = post or _default_post(timeout_seconds)
        self._get = get or _default_get(timeout_seconds)
        self._now = now
        self._marker_verified = False
        self._verified_props: Mapping[str, object] | None = None
        self._contacts: list[EmbeddingContact] = []
        self._closed = False

    @property
    def contacts(self) -> tuple[EmbeddingContact, ...]:
        return tuple(self._contacts)

    @property
    def marker_verified(self) -> bool:
        return self._marker_verified

    def verify_media_marker(self) -> Mapping[str, object]:
        """Fail-closed re-verification of the env-pinned marker against the
        LIVE server's own ``GET /props`` (module docstring) -- must succeed
        before any :meth:`embed_text`/:meth:`embed_audio` call. Idempotent:
        calling this again re-verifies rather than trusting the first
        result."""

        raw = self._get(self._base_url + PROPS_ENDPOINT_PATH)
        try:
            props = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EmbeddingClientError(f"GET /props returned invalid JSON: {error}") from error
        if not isinstance(props, Mapping):
            raise EmbeddingClientError("GET /props did not return a JSON object")
        if PROPS_MEDIA_MARKER_FIELD not in props:
            raise EmbeddingClientError(
                f"GET /props carries no {PROPS_MEDIA_MARKER_FIELD!r} field -- cannot verify "
                f"{LLAMA_MEDIA_MARKER_ENV} against the live server; refusing rather than "
                "silently trusting the env-pinned value unverified"
            )
        actual = props[PROPS_MEDIA_MARKER_FIELD]
        if actual != self._expected_marker:
            raise EmbeddingClientError(
                f"embedding server /props reports {PROPS_MEDIA_MARKER_FIELD}={actual!r}, which "
                f"does not match the env-pinned {LLAMA_MEDIA_MARKER_ENV}={self._expected_marker!r} "
                "-- refusing (fail-closed on mismatch)"
            )
        self._marker_verified = True
        self._verified_props = props
        return props

    def _require_marker_verified(self) -> None:
        if not self._marker_verified:
            raise EmbeddingClientError(
                "verify_media_marker() must succeed before any embed_text/embed_audio call -- "
                "an unverified marker could silently mis-place multimodal_data against a server "
                "whose actual placeholder token differs from the env-pinned one"
            )

    def embed_text(self, *, contact_id: str, text: str) -> EmbeddingVector:
        """Plain content-string text embedding -- NO instruct prefix (module
        docstring)."""

        if not isinstance(text, str) or not text:
            raise EmbeddingClientError(f"embed_text contact {contact_id!r}: text must be a non-empty string")
        return self._send(contact_id=contact_id, kind="text", body={"content": [text]})

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes) -> EmbeddingVector:
        """Audio embedding via the non-chat-style marker schema (module
        docstring): ``{"content": [{"prompt_string": <marker>,
        "multimodal_data": [<base64>]}]}``. ``audio_bytes`` are base64-
        encoded here (RAW file bytes, whatever container the carrier ships --
        flac for SLURP, wav for Audio2Tool -- never re-encoded, mirroring
        ``core.model.transport._load_audio_part``'s own "read the file,
        base64 it" discipline)."""

        if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
            raise EmbeddingClientError(f"embed_audio contact {contact_id!r}: audio_bytes must be non-empty bytes")
        audio_b64 = base64.b64encode(bytes(audio_bytes)).decode("ascii")
        body = {
            "content": [
                {"prompt_string": self._expected_marker, "multimodal_data": [audio_b64]}
            ]
        }
        return self._send(contact_id=contact_id, kind="audio", body=body)

    def _send(self, *, contact_id: str, kind: str, body: Mapping[str, object]) -> EmbeddingVector:
        if self._closed:
            raise EmbeddingClientError("embed call after close()")
        if not isinstance(contact_id, str) or not contact_id:
            raise EmbeddingClientError(f"{kind} contact_id must be a non-empty string, got {contact_id!r}")
        self._require_marker_verified()
        context = f"{kind} contact {contact_id!r}"
        started_wall = self._now()
        # Determinism-friendly (module docstring): this method accepts no
        # decoding_params-shaped argument anywhere in its own signature or
        # body construction above -- there is no seam through which a
        # sampling parameter could ever be forwarded to the embedding
        # server.
        raw = self._post(self._base_url + EMBEDDING_ENDPOINT_PATH, json.dumps(body).encode("utf-8"))
        latency = self._now() - started_wall
        values = _parse_embedding_response(raw, expected_count=1, context=context)[0]
        _assert_vector_legal(values, context=context)
        self._contacts.append(
            EmbeddingContact(
                contact_id=contact_id,
                kind=kind,
                started_at=_iso(started_wall),
                latency_seconds=latency,
                dims=len(values),
            )
        )
        return EmbeddingVector(contact_id=contact_id, kind=kind, values=values)

    def close(self) -> dict[str, object]:
        if self._closed:
            raise EmbeddingClientError("close() called twice")
        self._closed = True
        return {
            "contact_count": len(self._contacts),
            "contacts": [contact.as_json() for contact in self._contacts],
        }


def assert_no_conflicting_generation_server(
    *, generation_server_reachable: Callable[[], bool], generation_base_url: str
) -> None:
    """Fail-closed pre-flight guard (module docstring:
    :data:`GENERATION_COEXISTENCE_NOTE`): refuses if a generation server
    still appears to be listening at ``generation_base_url``.
    ``generation_server_reachable`` is caller-injected (a launcher's own TCP
    connect probe or ``GET /health``) -- this module performs no socket I/O
    of its own, mirroring ``core.session.lifecycle``'s own injectable
    ``http_get_status`` discipline."""

    if generation_server_reachable():
        raise EmbeddingClientError(
            f"a generation server appears to still be listening at {generation_base_url!r} -- "
            f"{GENERATION_COEXISTENCE_NOTE}"
        )


# ---------------------------------------------------------------------------
# MockEmbeddingClient -- zero-I/O test double, mirrors rails.core_client.
# MockCoreClient's own pattern exactly (deterministic, in-process, records
# every call).
# ---------------------------------------------------------------------------


def deterministic_unit_vector(seed_text: str, *, dims: int = EMBEDDING_DIM) -> tuple[float, ...]:
    """A reproducible, L2-normalized pseudo-random vector keyed only by
    ``seed_text`` (stdlib ``random.Random`` seeded off it -- never real
    model output, never claims to encode anything about ``seed_text``'s own
    meaning). Used as :class:`MockEmbeddingClient`'s default vector source
    so a flight test exercises real cosine-matcher code against vectors
    that are at least legal (dim/finite) without needing numpy at this
    layer."""

    rng = random.Random(seed_text)
    raw = [rng.gauss(0.0, 1.0) for _ in range(dims)]
    norm = math.sqrt(sum(value * value for value in raw))
    if norm == 0.0:  # pragma: no cover -- astronomically unlikely for dims>=1
        raw[0] = 1.0
        norm = 1.0
    return tuple(value / norm for value in raw)


@dataclass
class MockEmbeddingClient:
    """Deterministic, in-process :class:`EmbeddingClientProtocol` for tests
    -- zero model contact, zero I/O, zero network. ``vector_source``
    resolves each call's vector from ``(kind, contact_id)`` (default:
    :func:`deterministic_unit_vector` seeded on ``f"{kind}:{contact_id}"``,
    so distinct contacts never collide and a test can still control
    similarity structure by passing its own source); ``calls`` records every
    ``(kind, contact_id)`` pair actually sent."""

    vector_source: Callable[[str, str], Sequence[float]] | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)
    marker_verified: bool = False
    props: Mapping[str, object] = field(default_factory=lambda: {"media_marker": "<__media__>"})

    def verify_media_marker(self) -> Mapping[str, object]:
        self.marker_verified = True
        return self.props

    def embed_text(self, *, contact_id: str, text: str) -> EmbeddingVector:
        return self._embed("text", contact_id)

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes) -> EmbeddingVector:
        return self._embed("audio", contact_id)

    def _embed(self, kind: str, contact_id: str) -> EmbeddingVector:
        if not self.marker_verified:
            raise EmbeddingClientError(
                "verify_media_marker() must succeed before any embed_text/embed_audio call"
            )
        self.calls.append((kind, contact_id))
        if self.vector_source is not None:
            values = tuple(float(value) for value in self.vector_source(kind, contact_id))
        else:
            values = deterministic_unit_vector(f"{kind}:{contact_id}")
        _assert_vector_legal(values, context=f"mock {kind} contact {contact_id!r}")
        return EmbeddingVector(contact_id=contact_id, kind=kind, values=values)


__all__ = [
    "EMBEDDING_DIM",
    "EMBEDDING_ENDPOINT_PATH",
    "GENERATION_COEXISTENCE_NOTE",
    "LLAMA_MEDIA_MARKER_ENV",
    "PROPS_ENDPOINT_PATH",
    "PROPS_MEDIA_MARKER_FIELD",
    "EmbeddingClient",
    "EmbeddingClientError",
    "EmbeddingClientProtocol",
    "EmbeddingContact",
    "EmbeddingVector",
    "MockEmbeddingClient",
    "assert_no_conflicting_generation_server",
    "deterministic_unit_vector",
    "resolve_expected_media_marker",
]
