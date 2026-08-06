"""Value types + helpers for one ``FrozenCoreAdapter.request`` call.

Split out of ``adapter.py`` (R0 repair refactor stage 2, part C, pure move,
no behaviour change) purely for file size.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping

# The exact set of decoding_params keys the frozen core will ever accept. This is
# the governance choke point (FrozenCoreAdapter.request): a config-supplied
# decoding_params mapping can never smuggle a "messages"/"model"/"stream"/... key
# through to the transport, where it would otherwise silently replace the
# constructed chat-completions body (dropping audio while the adapter still
# meters it as delivered).
ALLOWED_DECODING_KEYS = frozenset(
    {
        "temperature",
        "seed",
        "top_p",
        "top_k",
        "min_p",
        "max_tokens",
        "presence_penalty",
        "frequency_penalty",
    }
)


@dataclass(frozen=True)
class CoreResponse:
    text: str
    usage: Mapping[str, int]
    request_sha256: str
    response_sha256: str
    # R0 repair T6 (I7, run-bundle closure): sha256 of `text` alone. The
    # adapter only ever hashes the raw transport bytes for `response_sha256`
    # -- and those bytes are not exactly re-derivable later from `text` plus
    # `usage` alone (the transport builds them from a server-controlled
    # `usage` mapping whose key order is not itself pinned anywhere). Minimal
    # adapter change so the outputs<->response binding IS strictly
    # re-verifiable after the fact: `core.bundle.verify_bundle` recomputes
    # this hash from the outputs row's own `text` field and refuses on any
    # mismatch -- closing the reproduced defect where a row's `text` could be
    # mutated post-hoc while `response_sha256` stayed stale and unchecked.
    response_text_sha256: str
    latency_seconds: float


def _canonical(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
