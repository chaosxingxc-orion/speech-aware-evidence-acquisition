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

"evidence-first-system-v3" (2026-08-12) is prep infrastructure for the
future listen-score-replay policy: a four-tier layout -- tier 1 [system]
task instruction, tier 2 [system] an ordered exemplar bank of (media,
label) pairs, tier 3 [user, before the target] 0..2 delta candidates
(media+label or text-only), tier 4 [user] the target audio -- built from
generic function parameters (payload fields), not a new config surface.
Bank content is serialized in CANONICAL (label, relpath) order, not
caller-supplied order, so the same bank always produces the same bytes
regardless of assembly order, in the same cache-friendly spirit as the v2
reorder above; delta candidates keep caller order (they are per-request,
position-sensitive, never a stable reusable prefix). An empty bank with no
delta candidates reduces to exactly v2's shape for the same inputs. No ops
benchmark exists yet for v3 -- unlike v1->v2 above, this is new, unmeasured
infrastructure.
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


def _load_audio_part(
    data_root: Path, media_relpath: object, field: str
) -> tuple[str, dict[str, object]]:
    """Confine and load ONE media item under ``data_root`` (I4, independent
    second rail -- see ``core.model.paths``): returns its normalized relpath
    (so canonical-sort callers, e.g. the exemplar bank below, have a stable
    sort key) and its ``input_audio`` wire content part. Shared by the
    single target-audio path and every exemplar-bank / delta-candidate media
    item below so the SAME confinement guarantee applies uniformly, never
    only to the first media item a request carries."""

    relative = _normalized_relative_path(media_relpath, field)
    media = _resolve_confined(data_root, relative, data_root, field, strict=False)
    if not media.is_file():
        raise FileNotFoundError(f"media missing for transport: {media}")
    data_b64 = base64.b64encode(media.read_bytes()).decode("ascii")
    return relative, {
        "type": "input_audio",
        "input_audio": {"data": data_b64, "format": media.suffix.lstrip(".").lower()},
    }


def _exemplar_bank_entry(
    data_root: Path, item: object, index: int
) -> tuple[str, str, list[dict[str, object]]]:
    """Validate ONE ``evidence-first-system-v3`` ``exemplar_bank`` entry (a
    required (media, label) pair; fail-closed on anything else) and build
    its wire content parts. Returns ``(label, relpath, parts)`` -- the
    caller sorts on ``(label, relpath)`` before flattening ``parts`` so the
    SAME bank serializes to the SAME bytes regardless of the order it was
    supplied in (tier 2 is a stable, cache-friendly bank, unlike tier 3's
    order-preserving delta candidates below)."""

    field = f"exemplar_bank[{index}]"
    if not isinstance(item, Mapping):
        raise FrozenCoreError(f"{field} must be a mapping, got {type(item).__name__}")
    if "label" not in item:
        raise FrozenCoreError(f"{field} missing required 'label'")
    label = item["label"]
    if not isinstance(label, str) or not label:
        raise FrozenCoreError(f"{field} label must be a non-empty string, got {label!r}")
    if "media_relpath" not in item:
        raise FrozenCoreError(f"{field} missing required 'media_relpath'")
    relative, audio_part = _load_audio_part(
        data_root, item["media_relpath"], f"transport {field}.media_relpath"
    )
    return label, relative, [{"type": "text", "text": f"[exemplar {label}]"}, audio_part]


def _delta_candidate_entry(
    data_root: Path, item: object, index: int
) -> list[dict[str, object]]:
    """Validate ONE ``evidence-first-system-v3`` ``delta_candidates`` entry
    -- either a text-only entry (``text``) or a (media, label) pair, never
    both; fail-closed on anything else -- and build its wire content parts
    in the exact position given (tier 3 candidates are per-request and
    order-sensitive, unlike tier 2's canonically-sorted bank above)."""

    field = f"delta_candidates[{index}]"
    if not isinstance(item, Mapping):
        raise FrozenCoreError(f"{field} must be a mapping, got {type(item).__name__}")
    has_text = "text" in item
    has_media = "media_relpath" in item
    if has_text and has_media:
        raise FrozenCoreError(
            f"{field} must be either a text-only entry ('text') or a "
            "(media_relpath, label) pair, not both"
        )
    if has_text:
        text = item["text"]
        if not isinstance(text, str) or not text:
            raise FrozenCoreError(f"{field} text must be a non-empty string, got {text!r}")
        return [{"type": "text", "text": f"[candidate] {text}"}]
    if not has_media:
        raise FrozenCoreError(f"{field} must contain either 'text' or 'media_relpath'")
    if "label" not in item:
        raise FrozenCoreError(f"{field} missing required 'label'")
    label = item["label"]
    if not isinstance(label, str) or not label:
        raise FrozenCoreError(f"{field} label must be a non-empty string, got {label!r}")
    _, audio_part = _load_audio_part(
        data_root, item["media_relpath"], f"transport {field}.media_relpath"
    )
    return [{"type": "text", "text": f"[candidate {label}]"}, audio_part]


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
        #
        # "evidence-first-system-v3" (2026-08-12) layers a four-tier
        # exemplar-bank/delta-candidate structure on top of v2's system-
        # message evidence placement -- see the module docstring for the
        # full tier breakdown. Prep infrastructure for the future
        # listen-score-replay policy, not yet ops-measured.
        if prompt_order not in (
            "system-instruction-v1",
            "evidence-first-system-v2",
            "evidence-first-system-v3",
        ):
            raise SessionError(
                f"unknown prompt_order {prompt_order!r}; allowed: "
                "'system-instruction-v1', 'evidence-first-system-v2', "
                "'evidence-first-system-v3'"
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
        # discards the data root via Path.__truediv__). ``_load_audio_part``
        # is the SAME confinement rail every exemplar-bank / delta-candidate
        # media item below goes through, never a target-audio-only special
        # case.
        _, audio_part = _load_audio_part(
            self._data_root, payload["media_relpath"], "transport media_relpath"
        )
        # Prefix-cache-friendly order (see module docstring, 2026-08-09,
        # measured): stable evidence text FIRST, variable audio LAST -- the
        # evidence formatting string and per-field iteration order
        # (supplied_evidence then retrieved_evidence) are unchanged, only
        # their position relative to the audio part moves.
        evidence_texts: list[str] = []
        for field in ("supplied_evidence", "retrieved_evidence"):
            for item in payload.get(field, []):  # type: ignore[union-attr]
                evidence_texts.append(f"[evidence {item['evidence_id']}] {item['content']}")
        if self._prompt_order == "evidence-first-system-v2":
            # Stable-first order: [system: evidence…, instruction(+tail at its
            # end)][user: audio]. The evidence formatting strings are
            # byte-identical to v1; only their position moves.
            system_text = "\n\n".join([*evidence_texts, str(payload["task_instruction"])])
            messages = [
                {"role": "system", "content": system_text},
                {"role": "user", "content": [audio_part]},
            ]
        elif self._prompt_order == "evidence-first-system-v3":
            # Four-tier layout (see module docstring): tier 1 [system] task
            # instruction, tier 2 [system] the canonically-ordered exemplar
            # bank, tier 3 [user, before the target] 0..2 order-preserving
            # delta candidates, tier 4 [user] the target audio (already
            # built above as `audio_part`, exactly like v1/v2). Evidence
            # placement is UNCHANGED from v2 so an empty bank with no delta
            # candidates reduces to EXACTLY v2's shape for the same inputs.
            exemplar_bank = payload.get("exemplar_bank", [])
            if not isinstance(exemplar_bank, list):
                raise FrozenCoreError("payload exemplar_bank must be a list")
            delta_candidates = payload.get("delta_candidates", [])
            if not isinstance(delta_candidates, list):
                raise FrozenCoreError("payload delta_candidates must be a list")
            if len(delta_candidates) > 2:
                raise FrozenCoreError(
                    "payload delta_candidates must contain at most 2 entries, got "
                    f"{len(delta_candidates)}"
                )
            instruction_text = str(payload["task_instruction"])
            if exemplar_bank:
                bank_entries = [
                    _exemplar_bank_entry(self._data_root, item, index)
                    for index, item in enumerate(exemplar_bank)
                ]
                # Canonical sort (see _exemplar_bank_entry's docstring): the
                # SAME bank serializes to the SAME bytes regardless of the
                # order it was assembled in.
                bank_entries.sort(key=lambda entry: (entry[0], entry[1]))
                system_content: object = (
                    [{"type": "text", "text": text} for text in evidence_texts]
                    + [{"type": "text", "text": instruction_text}]
                    + [part for _, _, parts in bank_entries for part in parts]
                )
            else:
                system_content = "\n\n".join([*evidence_texts, instruction_text])
            delta_parts = [
                part
                for index, item in enumerate(delta_candidates)
                for part in _delta_candidate_entry(self._data_root, item, index)
            ]
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": [*delta_parts, audio_part]},
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
