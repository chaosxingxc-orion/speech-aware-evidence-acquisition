"""In-process, transformers-backed encode-only client for GLAP/CLSP
(P-EMB-3M arms M2/M3, ``docs/readiness/
2026-08-20-pemb3m-preregistration-REGISTERED.md``).

Deliberately a SIBLING of ``rails.embedding_client`` (:class:`EmbeddingClient`),
never a variant of it: GLAP/CLSP speak NO wire protocol at all -- no HTTP, no
resident server, no port, no ``LLAMA_MEDIA_MARKER``. The "server" IS the
python process holding a loaded ``transformers`` model
(``docs/readiness/2026-08-20-e1-local-embedder-identity.md`` Mission A: GLAP
via ``transformers`` ``trust_remote_code``, dim 1024; CLSP via ``transformers``
custom code, dim 512). This module reuses :class:`~rails.embedding_client.
EmbeddingVector` / :class:`~rails.embedding_client.EmbeddingContact` directly
(both already generic over dim/kind -- never a second, parallel dataclass
pair).

Structurally encode-only (embedder-charter adjudication, ``docs/readiness/
2026-08-20-embedder-charter-adjudication.md`` section 2): every public
method on :class:`LocalTransformersEncoderClient` is ``embed_text``/
``embed_audio``-shaped; the class defines no ``generate``/``chat``/
``complete`` method, and its own real loading/encoding logic is never
imported at MODULE level (CLAUDE.md: "torch/transformers imports stay inside
the functions that use them") -- it is injected as two plain callables
(``encode_text_fn``/``encode_audio_fn``), themselves produced by a caller-
owned loader function that is the ONE place ``transformers``/``torch`` are
ever imported for this module's own real (non-test) use. ``rails.
encode_only_check`` sweeps this module's own source for forbidden
generation-endpoint strings and generation-client imports exactly like it
sweeps ``rails.embedding_client``.

Zero live model contact in this module or its own test suite: every test
drives :class:`MockLocalEncoderClient` or a synthetic ``encode_text_fn``/
``encode_audio_fn`` pair -- this module never imports ``torch`` or
``transformers`` itself and never loads real GLAP/CLSP weights.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence, runtime_checkable

from .embedding_client import EmbeddingContact, EmbeddingVector
from .errors import RailsError

# E-1 identity check (module docstring): GLAP dim 1024, CLSP dim 512 --
# pinned HERE as the two known local-encoder dims this study currently
# integrates; a future third local-transformers encoder would add its own
# named constant rather than overload either of these.
GLAP_EMBEDDING_DIM = 1024
CLSP_EMBEDDING_DIM = 512


class LocalEncoderClientError(RailsError):
    """A malformed local-encoder request/response, a fail-closed vector-
    legality violation (wrong dim / non-finite value), or a call made
    before the client's own one-time load/sanity step succeeded."""


def _assert_vector_legal(values: Sequence[float], *, context: str, expected_dim: int) -> None:
    if len(values) != expected_dim:
        raise LocalEncoderClientError(
            f"{context}: embedding dim {len(values)} != pinned {expected_dim}"
        )
    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise LocalEncoderClientError(
                f"{context}: embedding vector contains a non-finite value at index {index}: {value!r}"
            )


def _iso(epoch_seconds: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


@runtime_checkable
class LocalEncoderClientProtocol(Protocol):
    """The minimal shape :mod:`rails.probes.pemb3m_flight` drives for M2/M3
    -- satisfied by both the real :class:`LocalTransformersEncoderClient`
    and :class:`MockLocalEncoderClient`. Deliberately narrower than
    :class:`~rails.embedding_client.EmbeddingClientProtocol`: no
    ``verify_media_marker`` (module docstring: no wire protocol, no marker
    concept at all)."""

    def embed_text(self, *, contact_id: str, text: str) -> EmbeddingVector: ...

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes) -> EmbeddingVector: ...


class LocalTransformersEncoderClient:
    """The real in-process client. ``encode_text_fn``/``encode_audio_fn``
    are caller-injected callables (``str -> Sequence[float]`` /
    ``bytes -> Sequence[float]``) produced by a loader that imports
    ``transformers``/``torch`` only inside itself -- this class performs no
    such import of its own, mirroring :func:`~rails.embedding_client.
    _default_post`'s own "the real transport is a thin injectable closure"
    discipline."""

    def __init__(
        self,
        *,
        model_id: str,
        expected_dim: int,
        encode_text_fn: Callable[[str], Sequence[float]],
        encode_audio_fn: Callable[[bytes], Sequence[float]],
        now: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(model_id, str) or not model_id:
            raise LocalEncoderClientError("model_id must be a non-empty string")
        if not isinstance(expected_dim, int) or isinstance(expected_dim, bool) or expected_dim <= 0:
            raise LocalEncoderClientError("expected_dim must be a positive integer")
        self._model_id = model_id
        self._expected_dim = expected_dim
        self._encode_text_fn = encode_text_fn
        self._encode_audio_fn = encode_audio_fn
        self._now = now
        self._contacts: list[EmbeddingContact] = []

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def expected_dim(self) -> int:
        return self._expected_dim

    @property
    def contacts(self) -> tuple[EmbeddingContact, ...]:
        return tuple(self._contacts)

    def embed_text(self, *, contact_id: str, text: str) -> EmbeddingVector:
        if not isinstance(text, str) or not text:
            raise LocalEncoderClientError(f"embed_text contact {contact_id!r}: text must be a non-empty string")
        return self._encode(kind="text", contact_id=contact_id, encode=lambda: self._encode_text_fn(text))

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes) -> EmbeddingVector:
        if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
            raise LocalEncoderClientError(f"embed_audio contact {contact_id!r}: audio_bytes must be non-empty bytes")
        return self._encode(
            kind="audio", contact_id=contact_id, encode=lambda: self._encode_audio_fn(bytes(audio_bytes))
        )

    def _encode(self, *, kind: str, contact_id: str, encode: Callable[[], Sequence[float]]) -> EmbeddingVector:
        if not isinstance(contact_id, str) or not contact_id:
            raise LocalEncoderClientError(f"{kind} contact_id must be a non-empty string, got {contact_id!r}")
        context = f"{kind} contact {contact_id!r}"
        started_wall = self._now()
        raw_values = encode()
        latency = self._now() - started_wall
        values = tuple(float(value) for value in raw_values)
        _assert_vector_legal(values, context=context, expected_dim=self._expected_dim)
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


@dataclass
class MockLocalEncoderClient:
    """Deterministic, in-process :class:`LocalEncoderClientProtocol` for
    tests -- zero model contact, zero I/O. Mirrors ``rails.embedding_client.
    MockEmbeddingClient``'s own shape (``vector_source``/``calls``), minus
    the marker-verification concept this protocol never carries."""

    expected_dim: int = GLAP_EMBEDDING_DIM
    vector_source: Callable[[str, str], Sequence[float]] | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    def embed_text(self, *, contact_id: str, text: str) -> EmbeddingVector:
        return self._embed("text", contact_id)

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes) -> EmbeddingVector:
        return self._embed("audio", contact_id)

    def _embed(self, kind: str, contact_id: str) -> EmbeddingVector:
        from .embedding_client import deterministic_unit_vector

        self.calls.append((kind, contact_id))
        if self.vector_source is not None:
            values = tuple(float(value) for value in self.vector_source(kind, contact_id))
        else:
            values = deterministic_unit_vector(f"{kind}:{contact_id}", dims=self.expected_dim)
        _assert_vector_legal(values, context=f"mock {kind} contact {contact_id!r}", expected_dim=self.expected_dim)
        return EmbeddingVector(contact_id=contact_id, kind=kind, values=values)


# ---------------------------------------------------------------------------
# Import-feasibility gate (P-EMB-3M pre-flight gate (b), registration
# section 3 item 2): "GLAP/CLSP must import and produce one sanity embedding
# with the shared venv AS-IS. Any missing dependency -> that arm is
# DROPPED-DEPS (disclosed, never pip-installed)."
# ---------------------------------------------------------------------------

STATUS_OK = "OK"
STATUS_DROPPED_DEPS = "DROPPED-DEPS"

SANITY_TEXT = "sanity check"


@dataclass(frozen=True)
class ImportFeasibilityResult:
    arm_id: str
    model_id: str
    status: str  # STATUS_OK | STATUS_DROPPED_DEPS
    detail: str
    sanity_vector: EmbeddingVector | None = None


def run_import_feasibility_gate(
    *, arm_id: str, model_id: str, loader: Callable[[], LocalEncoderClientProtocol], sanity_text: str = SANITY_TEXT
) -> ImportFeasibilityResult:
    """Calls ``loader()`` (the ONLY place this gate ever imports/loads
    anything -- never this module itself) then embeds ``sanity_text`` once.
    ``ImportError`` (missing dependency in the shared venv AS-IS) is caught
    and reported as :data:`STATUS_DROPPED_DEPS`; the gate NEVER attempts a
    pip install and never suppresses any other exception (a real bug in a
    present dependency must surface loud, never be misreported as a missing
    one). ``docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md``
    section 3 item 2: "a dropped control never blocks M1/M4" -- this
    function's own return value carries that fact for the caller to act on;
    it never raises for a clean DROPPED-DEPS outcome."""

    try:
        client = loader()
    except ImportError as error:
        return ImportFeasibilityResult(
            arm_id=arm_id, model_id=model_id, status=STATUS_DROPPED_DEPS, detail=str(error)
        )
    try:
        vector = client.embed_text(contact_id=f"{arm_id}-sanity", text=sanity_text)
    except ImportError as error:
        return ImportFeasibilityResult(
            arm_id=arm_id, model_id=model_id, status=STATUS_DROPPED_DEPS, detail=str(error)
        )
    return ImportFeasibilityResult(
        arm_id=arm_id,
        model_id=model_id,
        status=STATUS_OK,
        detail=f"import + one sanity embed succeeded (dim {vector.dims})",
        sanity_vector=vector,
    )


__all__ = [
    "CLSP_EMBEDDING_DIM",
    "GLAP_EMBEDDING_DIM",
    "SANITY_TEXT",
    "STATUS_DROPPED_DEPS",
    "STATUS_OK",
    "ImportFeasibilityResult",
    "LocalEncoderClientError",
    "LocalEncoderClientProtocol",
    "LocalTransformersEncoderClient",
    "MockLocalEncoderClient",
    "run_import_feasibility_gate",
]
