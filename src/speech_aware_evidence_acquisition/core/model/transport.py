"""``LlamaServerTransport`` and its ``TRANSPORTS`` registration.

Split out of the former monolithic ``core/model.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).

Prefix-cache-friendly content order (2026-08-09, ops-measured; PROTOCOL-
AFFECTING): the user-message ``content`` list is ordered evidence text
parts FIRST, audio part LAST (system message already precedes both). An ops
benchmark on the real server, over 8 requests sharing an identical 23.3 KB
evidence block, measured audio-first (the prior order) against
evidence-first:

- audio-first: 26 cached tokens, 11,780 processed, 22,283 ms prefill,
  367.8 s total
- evidence-first: 9,607 cached tokens, 2,200 processed, 8,416 ms prefill,
  250.5 s total

i.e. 93% fewer prompt tokens processed, 72% less prefill, 32% less
wall-clock, because llama-server only reuses a KV-cache prefix that is
byte-identical AND contiguous from the start of the prompt (observed server
log: ``alloc: - prompt is already in the cache, skipping``). The system
message is already first and unaffected; putting the evidence block right
after it (instead of after the audio) makes [system, evidence...] the
stable, cacheable prefix, and the per-slice-variable audio -- which can
never be part of a reused prefix anyway -- last. Content placed AFTER the
audio does not break the cache, so nothing else about ordering matters
except audio-last.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Mapping

from ..base import TRANSPORTS
from ..session import SessionError, SessionReceipt, assert_session_alive, require_loopback
from . import FrozenCoreError
from .paths import _normalized_relative_path, _resolve_confined


def _default_post(timeout_seconds: float) -> Callable[[str, bytes], bytes]:
    def post(url: str, body: bytes) -> bytes:
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()

    return post


class LlamaServerTransport:
    def __init__(
        self,
        base_url: str,
        data_root: Path,
        session: SessionReceipt,
        runtime_receipt: Mapping[str, object],
        runtime_root: Path,
        timeout_seconds: float = 300.0,
        post: Callable[[str, bytes], bytes] | None = None,
        prompt_order: str = "system-instruction-v1",
    ) -> None:
        # Prompt ordering is part of the request's identity: the bytes the
        # model sees change with it, so it is a MODEL-CONFIG field (inside the
        # config hash), never a code default silently applied to existing
        # arms. "system-instruction-v1" is the historical order ([system:
        # instruction+tail][user: evidence…, audio]). "evidence-first-system-v2"
        # (SAEA-BENCH-cacheorder-q4km, 2026-08-11) moves the STABLE evidence
        # text into the system message ahead of the instruction(+tail), so the
        # cacheable prefix covers evidence+instruction and dies only at the
        # per-slice tail: measured under v1, the varying tail sits BEFORE the
        # evidence and the prefix cache scored 1 hit in 91 evidence slices;
        # the one hit re-prefilled exactly tail+audio (~799 tok), proving the
        # mechanism. Arms without evidence produce byte-identical requests
        # under both orders.
        if prompt_order not in ("system-instruction-v1", "evidence-first-system-v2"):
            raise SessionError(
                f"unknown prompt_order {prompt_order!r}; allowed: "
                "'system-instruction-v1', 'evidence-first-system-v2'"
            )
        self._prompt_order = prompt_order
        # R0 repair T5 (I5): there is no "no session" transport, mirroring the
        # T3 fail-closed constructor discipline for PayloadBindingContext --
        # a caller can never construct a transport that could ever be asked
        # to send without first proving WHO is going to answer. Its host/port
        # must be the exact endpoint this transport will talk to -- a session
        # receipt is only ever a proof about ONE specific loopback endpoint,
        # never a blanket credential.
        if not isinstance(session, SessionReceipt):
            raise SessionError(
                "LlamaServerTransport requires a core.session.SessionReceipt; got "
                f"{type(session).__name__} (no session receipt -> no send, I5)"
            )
        loopback_host, loopback_port = require_loopback(base_url)
        if (loopback_host, loopback_port) != (session.host, session.port):
            raise SessionError(
                f"transport base_url host/port {loopback_host}:{loopback_port} does not "
                f"match the session receipt's host/port {session.host}:{session.port}; "
                "refused (I5: a session receipt only authorizes the exact endpoint it "
                "was recorded for)"
            )
        self._url = base_url.rstrip("/") + "/v1/chat/completions"
        self._data_root = Path(data_root)
        self._post = post or _default_post(timeout_seconds)
        self._session = session
        self._runtime_receipt = runtime_receipt
        self._runtime_root = Path(runtime_root)
        # R0 repair T5 fix-1/fix-2 (I5, reviewer-flagged CRITICAL gap): full
        # liveness+PROCESS-IDENTITY re-verification, not merely a declared-
        # value comparison -- at construction AND (see __call__) on every
        # single send. A transport instance answers an entire run (potentially
        # many calls / hours of audio, per the plan's own declared budget --
        # no numeric ceiling since the 2026-08-06 owner amendment retired the
        # first-slice caps); a session proven valid once at construction time
        # proves nothing about who is listening later.
        self._assert_session_still_valid()

    def _assert_session_still_valid(self) -> None:
        assert_session_alive(self._session, self._runtime_receipt, self._runtime_root)

    def assert_session_alive(self) -> None:
        """Public re-verification entry point (R0 repair T5 fix-3): lets a
        holder of this transport (``core.model.FrozenCoreAdapter``)
        independently trigger the SAME liveness+identity check this class
        runs on every ``__call__`` -- a second enforcement call site, not an
        independently reimplemented rail (see ``core.session.
        assert_session_alive``'s docstring for why full reimplementation is
        not appropriate for a transport-specific concept like process
        identity)."""

        self._assert_session_still_valid()

    def __call__(self, request_bytes: bytes) -> bytes:
        # R0 repair T5 fix-2 (IMPORTANT, reviewer-flagged): re-verify on the
        # send path itself, every time -- not merely once at construction.
        # Cheap (a few KB re-hash of the launcher stub plus one process-image
        # lookup, never the multi-GB GGUF files), so there is no reason to
        # skip it on the hot path; a process that died or was replaced since
        # the last send is caught HERE, before this request does anything.
        self._assert_session_still_valid()
        payload: Mapping[str, object] = json.loads(request_bytes.decode("utf-8"))
        # I4, independent second rail: refuse absolute/backslash/traversal
        # media_relpath and anything resolving outside self._data_root on the
        # transport's OWN authority -- this must hold even if the adapter's
        # binding-context check were somehow bypassed or absent (the
        # reproduced defect: `self._data_root / <absolute path>` silently
        # discards the data root via Path.__truediv__).
        relative = _normalized_relative_path(payload["media_relpath"], "transport media_relpath")
        media = _resolve_confined(
            self._data_root,
            relative,
            self._data_root,
            "transport media_relpath",
            strict=False,
        )
        if not media.is_file():
            raise FileNotFoundError(f"media missing for transport: {media}")
        audio_b64 = base64.b64encode(media.read_bytes()).decode("ascii")
        # Prefix-cache-friendly order (see module docstring, 2026-08-09,
        # measured): stable evidence text FIRST, variable audio LAST -- the
        # evidence formatting string and per-field iteration order
        # (supplied_evidence then retrieved_evidence) are unchanged, only
        # their position relative to the audio part moves.
        evidence_texts: list[str] = []
        for field in ("supplied_evidence", "retrieved_evidence"):
            for item in payload.get(field, []):  # type: ignore[union-attr]
                evidence_texts.append(f"[evidence {item['evidence_id']}] {item['content']}")
        audio_part = {
            "type": "input_audio",
            "input_audio": {"data": audio_b64, "format": media.suffix.lstrip(".").lower()},
        }
        if self._prompt_order == "evidence-first-system-v2":
            # Stable-first order: [system: evidence…, instruction(+tail at its
            # end)][user: audio]. The evidence formatting strings are
            # byte-identical to v1; only their position moves.
            system_text = "\n\n".join([*evidence_texts, str(payload["task_instruction"])])
            messages = [
                {"role": "system", "content": system_text},
                {"role": "user", "content": [audio_part]},
            ]
        else:
            content: list[dict[str, object]] = [
                {"type": "text", "text": text} for text in evidence_texts
            ]
            content.append(audio_part)
            messages = [
                {"role": "system", "content": payload["task_instruction"]},
                {"role": "user", "content": content},
            ]
        body: dict[str, object] = {"messages": messages}
        for key, value in dict(payload.get("decoding_params", {})).items():  # type: ignore[arg-type]
            if key in body:
                raise FrozenCoreError(
                    f"decoding_params key {key!r} collides with the constructed "
                    "request body and would silently override it"
                )
            body[key] = value
        try:
            raw = self._post(self._url, json.dumps(body).encode("utf-8"))
        except urllib.error.HTTPError as error:
            # 2026-08-08: surface the server's diagnostic body — a bare
            # `HTTPError: 400` cost a metered call while discarding the one
            # string that says WHY (context overflow, schema, …).
            try:
                detail = error.read()[:2048].decode("utf-8", "replace")
            except OSError:
                detail = "<unreadable body>"
            raise FrozenCoreError(
                f"server returned HTTP {error.code} {error.reason}: {detail}"
            ) from error
        try:
            parsed = json.loads(raw.decode("utf-8"))
            text = parsed["choices"][0]["message"]["content"]
            # 2026-08-08: newer llama-server usage blocks carry nested
            # OpenAI-style `*_tokens_details` objects — a valid schema
            # extension, dropped here. Anything else keeps the original
            # fail-closed int() contract: a malformed scalar counter still
            # raises rather than being silently swallowed.
            usage = {
                str(k): int(v)
                for k, v in dict(parsed.get("usage", {})).items()
                if not isinstance(v, Mapping)
            }
        except (KeyError, TypeError, ValueError, IndexError, UnicodeError) as error:
            raise FrozenCoreError(
                f"transport returned a malformed response: {error}"
            ) from error
        return json.dumps({"text": text, "usage": usage}).encode("utf-8")


def _llama_server_factory(
    values: Mapping[str, object],
    data_root: Path,
    *,
    session: SessionReceipt,
    runtime_receipt: Mapping[str, object],
    runtime_root: Path,
):
    return LlamaServerTransport(
        str(values["base_url"]),
        data_root,
        session,
        runtime_receipt,
        runtime_root,
        float(values.get("timeout_seconds", 300.0)),
        prompt_order=str(values.get("prompt_order", "system-instruction-v1")),
    )


TRANSPORTS.register("llama-server", _llama_server_factory)
