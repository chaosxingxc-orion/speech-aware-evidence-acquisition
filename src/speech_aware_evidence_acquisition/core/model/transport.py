"""``LlamaServerTransport`` and its ``TRANSPORTS`` registration.

Split out of the former monolithic ``core/model.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
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
    ) -> None:
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
        content: list[dict[str, object]] = [
            {
                "type": "input_audio",
                "input_audio": {"data": audio_b64, "format": media.suffix.lstrip(".").lower()},
            }
        ]
        for field in ("supplied_evidence", "retrieved_evidence"):
            for item in payload.get(field, []):  # type: ignore[union-attr]
                content.append(
                    {"type": "text", "text": f"[evidence {item['evidence_id']}] {item['content']}"}
                )
        body: dict[str, object] = {
            "messages": [
                {"role": "system", "content": payload["task_instruction"]},
                {"role": "user", "content": content},
            ],
        }
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
            usage = {str(k): int(v) for k, v in dict(parsed.get("usage", {})).items()}
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
    )


TRANSPORTS.register("llama-server", _llama_server_factory)
