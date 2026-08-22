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
        # llama-server's OpenAI-compatible schema-constrained decoding. The
        # adapter validates the wrapper shape before the transport forwards it;
        # callers cannot use this key to replace messages, model identity, or
        # streaming behavior.
        "response_format",
        # llama-server slot pinning (SAEA-BENCH-idslot-q4km, 2026-08-11): an
        # integer here pins the request to one server slot so a sample's
        # stable evidence prefix stays in that slot's KV instead of being
        # re-prefilled every slice (measured: zero cache hits under free slot
        # assignment; ~4.4k evidence tokens re-prefilled per slice on the
        # evidence arms). A config fragment declares the SENTINEL
        # "per-sample" and the batch executor resolves it to an allocated
        # slot integer; the adapter refuses an unresolved sentinel
        # (adapter.request) so it can never reach the server as a string.
        "id_slot",
        # obs-replay-loop policy (reproduction.replay_loop, 2026-08-13): the
        # SCORE stage's optional per-token confidence signal. Requested only
        # when a run's ``replay_logprobs`` config key is true (default
        # false, byte-identical requests otherwise) -- llama-server's
        # OpenAI-compatible /v1/chat/completions endpoint shape:
        # ``"logprobs": true, "top_logprobs": 1`` on the request, a
        # ``choices[0].logprobs.content[]`` list of ``{"token", "logprob"}``
        # entries on the response. Real-server availability is not
        # guaranteed (prior offline exploration observed llama-server
        # sometimes omitting usable logprobs for a hypothesis) -- core.
        # model.transport/adapter forward whatever the server actually
        # returns, and core.replay_signals-consuming code treats an
        # absent/malformed logprobs object as "trigger unavailable", never
        # a crash.
        "logprobs",
        "top_logprobs",
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
    # obs-replay-loop policy (reproduction.replay_loop, 2026-08-13): the raw
    # ``choices[0].logprobs`` object llama-server returned, forwarded
    # verbatim by the transport when the request actually carried
    # ``decoding_params.logprobs: true`` (module comment above
    # ALLOWED_DECODING_KEYS). ``None`` is the pre-existing, byte-identical
    # default for every request that never asked for logprobs -- no
    # behaviour change for any caller that does not read this field.
    logprobs: object = None


def _canonical(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
