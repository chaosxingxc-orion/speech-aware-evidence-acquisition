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
NATIVE_TOOL_REQUEST_CONTROL_KEYS = frozenset({"tool_choice", "parallel_tool_calls"})


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
        # Native tool request controls remain in the audited per-contact
        # decoding mapping. The adapter restricts them to native-tool arms;
        # the transport moves them to the OpenAI request body's top level.
        *NATIVE_TOOL_REQUEST_CONTROL_KEYS,
    }
)


def native_tool_request_controls(
    decoding_params: Mapping[str, object], *, native_tools: bool
) -> dict[str, object]:
    """Validate and project optional native-tool request controls."""

    declared = NATIVE_TOOL_REQUEST_CONTROL_KEYS & set(decoding_params)
    if declared and not native_tools:
        raise ValueError(
            "native tool request controls are valid only for a native-tool arm"
        )
    controls: dict[str, object] = {}
    if "tool_choice" in decoding_params:
        tool_choice = decoding_params["tool_choice"]
        if not isinstance(tool_choice, str) or tool_choice not in {"auto", "none"}:
            raise ValueError("decoding_params tool_choice must be 'auto' or 'none'")
        controls["tool_choice"] = tool_choice
    if "parallel_tool_calls" in decoding_params:
        parallel = decoding_params["parallel_tool_calls"]
        if parallel is not False:
            raise ValueError("decoding_params parallel_tool_calls must be false")
        controls["parallel_tool_calls"] = False
    return controls


#: Upper bound this adapter accepts for ``decoding_params.top_logprobs``
#: (2026-09-08 logprob-as-judge probe). The pinned llama-server does not cap
#: the value itself -- ``tools/server/server-schema.cpp:175-177`` registers
#: ``n_probs`` with no hard limits -- but its OpenAI-compatible layer defaults
#: the field to 20 when ``logprobs: true`` arrives without it
#: (``tools/server/server-common.cpp:1529``), and 20 is the OpenAI contract's
#: own ceiling. Asking for more is a per-token full-vocabulary sort the study
#: has no use for, so the adapter refuses it here, before the call is metered,
#: rather than letting a config typo buy an expensive request.
MAX_TOP_LOGPROBS = 20


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
    # Native tool-calling arms (2026-09-04): the RAW ``message.tool_calls``
    # list llama-server returned, forwarded verbatim by the transport when
    # the response actually carried one. The transport canonicalizes those
    # calls into the same ``[{"name": ..., "arguments": {...}}]`` TEXT shape
    # a free-text arm produces, which is what makes one scorer serve both --
    # and is exactly why, after the fact, a canonical JSON array in a sealed
    # outputs row is indistinguishable from JSON the model authored as text.
    # The calibration smoke hit that ambiguity: three of four native rows
    # were canonical arrays and nothing recorded which mechanism produced
    # them. Carrying the raw list here settles it at the one place that sees
    # the envelope. ``None`` means the response carried no tool_calls key at
    # all, i.e. the model answered as text -- the byte-identical default for
    # every request that never asked for tools.
    tool_calls: object = None


def _canonical(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
