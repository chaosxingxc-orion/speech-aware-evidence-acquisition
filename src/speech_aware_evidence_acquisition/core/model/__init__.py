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


from .paths import _DRIVE_PREFIX, _normalized_relative_path, _resolve_confined  # noqa: E402
from .binding import _PayloadBindingMixin  # noqa: E402
from .request_types import ALLOWED_DECODING_KEYS, CoreResponse, _canonical  # noqa: E402
from .lifecycle import _AttemptLifecycleMixin  # noqa: E402
from .adapter import FrozenCoreAdapter  # noqa: E402
from .transport import (  # noqa: E402
    LlamaServerTransport,
    _default_post,
    _llama_server_factory,
)

__all__ = [
    "ALLOWED_DECODING_KEYS",
    "CoreResponse",
    "FrozenCoreAdapter",
    "FrozenCoreError",
    "LlamaServerTransport",
    "_AttemptLifecycleMixin",
    "_DRIVE_PREFIX",
    "_PayloadBindingMixin",
    "_canonical",
    "_default_post",
    "_llama_server_factory",
    "_normalized_relative_path",
    "_resolve_confined",
]
