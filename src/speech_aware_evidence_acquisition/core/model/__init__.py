"""Frozen-core adapter and transports: the ONLY model request path (R0).

Discipline (docs/engineering.md): the gate is checked in the same process
that sends requests (no check-then-run-elsewhere TOCTOU gap); the D2 per-arm
visible-field allowlist is enforced as an exact key set on every request —
the choke point that makes a leakage a hard error rather than a convention.
The real llama-server endpoint shape is confirmed at R0 smoke time against
the receipt-pinned build — tests inject `post` and never open a socket.

R0 repair refactor stage 1 (behaviour-preserving): this used to be one
~730-line ``model.py`` module. It is now this package (``paths.py`` for the
shared media-path helpers, ``adapter.py`` for ``FrozenCoreAdapter``,
``transport.py`` for ``LlamaServerTransport`` + its ``TRANSPORTS``
registration) purely for file size -- every name below was already part of
this module's public surface and remains importable from exactly
``speech_aware_evidence_acquisition.core.model`` as before.

R0 repair refactor stage 2 (part C, pure move, no behaviour change):
``adapter.py`` itself further split into ``lifecycle.py``
(``_AttemptLifecycleMixin``) and ``request_types.py`` (``CoreResponse``/
``ALLOWED_DECODING_KEYS``/``_canonical``) -- same "every name stays
importable from exactly this package" guarantee.
"""

from __future__ import annotations


class FrozenCoreError(RuntimeError):
    """The adapter refuses: unknown arm, allowlist violation, exhausted budget,
    payload<->plan<->split value mismatch (I3), or media confinement (I4)."""


class FrozenCoreContextSizeError(FrozenCoreError):
    """E20 (2026-09-19): the SERVER refused this request as too wide.

    Exactly one error class of the built fork:
    ``ERROR_TYPE_EXCEED_CONTEXT_SIZE``, which
    ``tools/server/server-common.cpp:59-62`` renders as HTTP 400 with
    ``error.type == "exceed_context_size_error"``. Every other HTTP status,
    and every other 400, still raises the plain :class:`FrozenCoreError`
    the transport has always raised -- this subclass exists only so an
    episode running ``native_episode.context_fit_policy ==
    "compact-or-abstain"`` can turn that one fact into a retained row
    instead of losing the rest of the flight.

    ``server_message`` is the fork's own diagnostic sentence ("request (%d
    tokens) exceeds the available context size (%d tokens), try increasing
    it"), recorded verbatim in the row's terminal disposition.
    """

    #: The ``error.type`` the fork returns for this refusal, and the ONLY
    #: value this class is raised for.
    WIRE_ERROR_TYPE = "exceed_context_size_error"

    def __init__(self, message: str, *, server_message: str | None = None) -> None:
        super().__init__(message)
        self.server_message = server_message


from .paths import (  # noqa: E402
    _DRIVE_PREFIX,
    _normalized_relative_path,
    _resolve_confined,
    _resolve_confined_any,
)
from .slices import (  # noqa: E402
    OBS_SLICES_SUBDIR,
    PARENT_DURATION_TOLERANCE_SECONDS,
    SliceRecord,
    SliceRegistry,
)
from .binding import _PayloadBindingMixin  # noqa: E402
from .request_types import (  # noqa: E402
    ALLOWED_DECODING_KEYS,
    MAX_TOP_LOGPROBS,
    CoreResponse,
    WireResponseMetadataError,
    _canonical,
    wire_response_message,
)
from .lifecycle import _AttemptLifecycleMixin  # noqa: E402
from .adapter import FrozenCoreAdapter  # noqa: E402
from .transport import (  # noqa: E402
    LlamaServerTransport,
    _default_post,
    _llama_server_factory,
)
from .prepared_feature_cache import (  # noqa: E402
    PreparedFeatureCacheError,
    PreparedFeatureCacheGuard,
)
from .speech_features import (  # noqa: E402
    PACKET_MANIFEST_NAME,
    PROMOTION_MODE_ENCODE_AND_PROMOTE,
    PROMOTION_MODE_PROMOTE_ONLY,
    PROMOTION_MODES,
    PROMOTION_RECEIPT_OPTIONAL_KEYS,
    SPEECH_FEATURE_PACKET_SCHEMA,
    SPEECH_PACKET_PROMOTION_RECEIPT_SCHEMA,
    LegacyCachedChunkDescriptor,
    LegacyFeatureCacheInspection,
    SharedSpeechFeaturePacketRecord,
    SpeechFeatureChunkData,
    SpeechFeatureChunkV1,
    SpeechFeaturePacketV1,
    inspect_legacy_cached_speech_feature_cache,
    legacy_audio_feature_cache_key,
    load_speech_feature_packet,
    load_speech_feature_packet_ids,
    load_speech_feature_packets,
    load_speech_packet_promotion_receipt,
    materialize_legacy_cached_speech_feature_packet,
    materialize_legacy_cached_speech_feature_packets,
    materialize_speech_feature_packet,
)

__all__ = [
    "ALLOWED_DECODING_KEYS",
    "MAX_TOP_LOGPROBS",
    "CoreResponse",
    "WireResponseMetadataError",
    "FrozenCoreAdapter",
    "FrozenCoreContextSizeError",
    "FrozenCoreError",
    "PreparedFeatureCacheError",
    "PreparedFeatureCacheGuard",
    "LlamaServerTransport",
    "OBS_SLICES_SUBDIR",
    "PARENT_DURATION_TOLERANCE_SECONDS",
    "SliceRecord",
    "SliceRegistry",
    "PACKET_MANIFEST_NAME",
    "PROMOTION_MODE_ENCODE_AND_PROMOTE",
    "PROMOTION_MODE_PROMOTE_ONLY",
    "PROMOTION_MODES",
    "PROMOTION_RECEIPT_OPTIONAL_KEYS",
    "SPEECH_FEATURE_PACKET_SCHEMA",
    "SPEECH_PACKET_PROMOTION_RECEIPT_SCHEMA",
    "LegacyCachedChunkDescriptor",
    "LegacyFeatureCacheInspection",
    "SharedSpeechFeaturePacketRecord",
    "SpeechFeatureChunkData",
    "SpeechFeatureChunkV1",
    "SpeechFeaturePacketV1",
    "_AttemptLifecycleMixin",
    "_DRIVE_PREFIX",
    "_PayloadBindingMixin",
    "_canonical",
    "wire_response_message",
    "_default_post",
    "_llama_server_factory",
    "_normalized_relative_path",
    "_resolve_confined",
    "_resolve_confined_any",
    "inspect_legacy_cached_speech_feature_cache",
    "legacy_audio_feature_cache_key",
    "load_speech_feature_packet",
    "load_speech_feature_packet_ids",
    "load_speech_feature_packets",
    "load_speech_packet_promotion_receipt",
    "materialize_legacy_cached_speech_feature_packet",
    "materialize_legacy_cached_speech_feature_packets",
    "materialize_speech_feature_packet",
]
