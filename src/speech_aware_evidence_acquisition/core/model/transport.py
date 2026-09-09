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

Two request-shaping config keys sit beside ``prompt_order`` and travel in
``config_hash`` -> ``protocol_hash`` exactly as it does. ``user_turn_text``
(+ ``user_turn_audio_first``, 2026-09-04) puts a fixed sentence in the USER
turn after the audio, which is what the published Audio2Tool protocol sends.
``omit_system_message`` (2026-09-05) drops the system message entirely, which
is what the Qwen3-Omni model card's "Setting for Evaluation" section
prescribes for every evaluation benchmark ("No ``system prompt`` should be
set"; "the text should come after multimodal data"). Both default to the
pre-existing shape, so a cell that declares neither renders byte-identical
requests to the ones it rendered before either key existed.

Speech-feature AgentLoops use explicit cache layouts. A speech-query prefix
places the query packet before knowledge and mutable state so a task-affine
slot can retain the query KV across steps. The dual-prefix knowledge-speech-
state layout places only the frozen text/audio key index before the query and
keeps retrieved values, Agent state, and instructions after it, allowing both
cross-sample knowledge-prefix reuse and within-trajectory speech-prefix reuse.
The historical
``speech-features-text-keys-v1`` order remains unchanged for replay.
"""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...contracts.identifiers import CONSTRUCTION_VISIBLE_FIELD
from ..base import TRANSPORTS
from ..session import (
    SessionError,
    SessionReceipt,
    assert_session_alive,
    require_loopback,
)
from . import FrozenCoreError
from .paths import _normalized_relative_path, _resolve_confined
from .speech_features import load_speech_feature_packets


_SPEECH_FEATURE_PROMPT_ORDERS = frozenset(
    {
        "speech-features-text-keys-v1",
        "speech-query-prefix-v2",
        "knowledge-speech-state-v2",
    }
)


def _ordered_speech_feature_content(
    *,
    prompt_order: str,
    evidence_texts: list[str],
    feature_parts: list[dict[str, object]],
    state_texts: Sequence[str] = (),
    knowledge_roles: Sequence[str | None] = (),
) -> list[dict[str, object]]:
    """Build one cache-explicit speech-feature user content sequence."""

    text_parts: list[dict[str, object]] = [
        {"type": "text", "text": text} for text in evidence_texts
    ]
    state_parts: list[dict[str, object]] = [
        {"type": "text", "text": text} for text in state_texts
    ]
    if knowledge_roles:
        if len(knowledge_roles) != len(text_parts) or any(
            role not in {"key", "value"} for role in knowledge_roles
        ):
            raise FrozenCoreError(
                "explicit speech knowledge roles must align one-to-one as key/value"
            )
        key_text_parts = [
            part
            for part, role in zip(text_parts, knowledge_roles, strict=True)
            if role == "key"
        ]
        value_text_parts = [
            part
            for part, role in zip(text_parts, knowledge_roles, strict=True)
            if role == "value"
        ]
    else:
        key_text_parts = []
        value_text_parts = []
    if prompt_order == "speech-features-text-keys-v1":
        return [*text_parts, *feature_parts, *state_parts]

    query_parts = [
        part
        for part in feature_parts
        if part["speech_features"]["role"] == "query"  # type: ignore[index]
    ]
    key_parts = [
        part
        for part in feature_parts
        if part["speech_features"]["role"] == "key"  # type: ignore[index]
    ]
    if len(query_parts) != 1:
        raise FrozenCoreError(
            "formal speech feature request must carry exactly one query packet"
        )

    # Historical matcher calls encode the mutable step instruction as their
    # final evidence item. New AgentLoop calls use D2's separate ``history``
    # field, so every evidence item remains SUPPLY and all ORG/CONTROL state
    # is appended after the stable speech/knowledge prefix.
    if knowledge_roles:
        stable_text_parts = key_text_parts
        mutable_state_parts = [*value_text_parts, *state_parts]
    elif state_parts:
        stable_text_parts = text_parts
        mutable_state_parts = state_parts
    else:
        stable_text_parts = text_parts[:-1]
        mutable_state_parts = text_parts[-1:]
    if prompt_order == "speech-query-prefix-v2":
        return [*query_parts, *stable_text_parts, *key_parts, *mutable_state_parts]
    if prompt_order == "knowledge-speech-state-v2":
        if knowledge_roles:
            return [
                *key_text_parts,
                *key_parts,
                *query_parts,
                *value_text_parts,
                *state_parts,
            ]
        return [
            *text_parts[:1],
            *key_parts,
            *query_parts,
            *text_parts[1:],
            *state_parts,
        ]
    raise FrozenCoreError(f"unsupported speech feature prompt order {prompt_order!r}")


def _assert_agent_history_suffix(
    *,
    prompt_order: str,
    content: Sequence[Mapping[str, object]],
    state_texts: Sequence[str],
) -> None:
    """Fail closed unless every rendered Agent history part survives ordering."""

    if not state_texts:
        return
    expected = tuple({"type": "text", "text": text} for text in state_texts)
    if tuple(content[-len(expected) :]) != expected:
        raise FrozenCoreError(
            f"{prompt_order} must preserve Agent state/control as an ordered suffix"
        )


def _speech_history_texts(history: object) -> list[str]:
    """Validate and render speech-native ORG/CONTROL history."""

    if not isinstance(history, list):
        raise FrozenCoreError("speech feature payload history must be a list")
    rendered: list[str] = []
    for index, item in enumerate(history):
        if not isinstance(item, Mapping):
            raise FrozenCoreError(f"history[{index}] must be a mapping")
        role = item.get("role")
        content = item.get("content")
        content_sha256 = item.get("content_sha256")
        if not isinstance(content, str) or not content:
            raise FrozenCoreError(f"history[{index}] content must be non-empty text")
        if (
            not isinstance(content_sha256, str)
            or hashlib.sha256(content.encode("utf-8")).hexdigest() != content_sha256
        ):
            raise FrozenCoreError(f"history[{index}] content hash mismatch")
        if role == "agent_state":
            state_id = item.get("state_id")
            state_kind = item.get("state_kind")
            if not isinstance(state_id, str) or not state_id:
                raise FrozenCoreError(f"history[{index}] agent_state requires state_id")
            if not isinstance(state_kind, str) or not state_kind:
                raise FrozenCoreError(
                    f"history[{index}] agent_state requires state_kind"
                )
            for field in (
                "source_query_state_sha256",
                "source_response_sha256",
            ):
                value = item.get(field)
                if (
                    not isinstance(value, str)
                    or len(value) != 64
                    or any(character not in "0123456789abcdef" for character in value)
                ):
                    raise FrozenCoreError(
                        f"history[{index}] agent_state requires lowercase 64-hex {field}"
                    )
            producer = item.get("producer_policy_id")
            cited = item.get("cited_value_ids")
            if not isinstance(producer, str) or not producer:
                raise FrozenCoreError(
                    f"history[{index}] agent_state requires producer_policy_id"
                )
            if not isinstance(cited, list) or not all(
                isinstance(value_id, str) and value_id for value_id in cited
            ):
                raise FrozenCoreError(
                    f"history[{index}] agent_state cited_value_ids must be a string list"
                )
            rendered.append(f"[agent state {state_id} kind={state_kind}] {content}")
            continue
        if role == "control":
            contact_id = item.get("contact_id")
            if not isinstance(contact_id, str) or not contact_id:
                raise FrozenCoreError(f"history[{index}] control requires contact_id")
            rendered.append(f"[agent control {contact_id}] {content}")
            continue
        raise FrozenCoreError(
            f"history[{index}] role must be 'agent_state' or 'control'"
        )
    return rendered


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
        raise FrozenCoreError(
            f"{field} label must be a non-empty string, got {label!r}"
        )
    if "media_relpath" not in item:
        raise FrozenCoreError(f"{field} missing required 'media_relpath'")
    relative, audio_part = _load_audio_part(
        data_root, item["media_relpath"], f"transport {field}.media_relpath"
    )
    return (
        label,
        relative,
        [{"type": "text", "text": f"[exemplar {label}]"}, audio_part],
    )


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
            raise FrozenCoreError(
                f"{field} text must be a non-empty string, got {text!r}"
            )
        return [{"type": "text", "text": f"[candidate] {text}"}]
    if not has_media:
        raise FrozenCoreError(f"{field} must contain either 'text' or 'media_relpath'")
    if "label" not in item:
        raise FrozenCoreError(f"{field} missing required 'label'")
    label = item["label"]
    if not isinstance(label, str) or not label:
        raise FrozenCoreError(
            f"{field} label must be a non-empty string, got {label!r}"
        )
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
        feature_root: Path | None = None,
        user_turn_text: str | None = None,
        user_turn_audio_first: bool = True,
        omit_system_message: bool = False,
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
            *_SPEECH_FEATURE_PROMPT_ORDERS,
        ):
            raise SessionError(
                f"unknown prompt_order {prompt_order!r}; allowed: "
                "'system-instruction-v1', 'evidence-first-system-v2', "
                "'evidence-first-system-v3', "
                f"{', '.join(repr(item) for item in sorted(_SPEECH_FEATURE_PROMPT_ORDERS))}"
            )
        self._prompt_order = prompt_order
        # Fragment-driven user-turn text (2026-09-04, Audio2Tool official-
        # protocol replication). The published Audio2Tool protocol puts a
        # fixed sentence in the USER turn AFTER the audio ("Convert this
        # voice command to a tool call."); every arm this repository had
        # built until now sends a user turn carrying nothing but evidence
        # text and the audio, with the whole instruction in the system
        # message. Rather than hard-code the sentence or fork a payload
        # builder, the composed config declares it: `user_turn_text` (the
        # exact string, part of config_hash -> protocol_hash like every other
        # request-shaping key) and `user_turn_audio_first` (whether it goes
        # after or before the audio part; the official order is after).
        # DEFAULT None: every pre-existing cell renders byte-identically,
        # which tests/unit/test_llama_server_transport.py asserts directly.
        if user_turn_text is not None and (
            not isinstance(user_turn_text, str) or not user_turn_text.strip()
        ):
            raise SessionError(
                "user_turn_text must be a non-empty string when declared; an empty "
                "user text part would put a meaningless content part on the wire"
            )
        if user_turn_text is not None and prompt_order in _SPEECH_FEATURE_PROMPT_ORDERS:
            # The speech-feature orders build their user content through
            # _ordered_speech_feature_content, whose ordering contract is
            # asserted by _assert_agent_history_suffix. Appending a free text
            # part there would silently change what that assertion is
            # protecting, so it is refused rather than guessed at; no packet
            # cell of this replication is flown.
            raise SessionError(
                f"user_turn_text is not supported under prompt_order {prompt_order!r}; "
                "the speech-feature orders own their user content ordering"
            )
        self._user_turn_text = user_turn_text
        self._user_turn_audio_first = bool(user_turn_audio_first)
        # Fragment-driven SYSTEM-MESSAGE SUPPRESSION (2026-09-05, Earnings-22
        # DEV ESB shape-C arm). The Qwen3-Omni model card's "Setting for
        # Evaluation" section states, for every evaluation benchmark, "No
        # `system prompt` should be set" and "the text should come AFTER
        # multimodal data in the sequence". `user_turn_text` /
        # `user_turn_audio_first` already express the second half; this key
        # expresses the first. It is a request-shaping config key like every
        # other one here, so it travels inside config_hash -> protocol_hash
        # and a cell that does not declare it renders byte-identically to
        # before this key existed (DEFAULT False; asserted directly by
        # tests/unit/test_llama_server_transport.py).
        #
        # Fail-closed, because the failure mode is SILENT: dropping the
        # system message would otherwise drop `task_instruction` off the wire
        # while every receipt, trace record and protocol hash still recorded
        # it, i.e. the run would be measuring an unrecorded prompt. So the
        # instruction must have a declared home in the user turn, and (see
        # __call__) it must be byte-identical to the string the payload
        # carries; evidence and exemplar banks, which live in the system
        # message under the v2/v3 orders, are refused outright rather than
        # silently discarded.
        if not isinstance(omit_system_message, bool):
            raise SessionError(
                "omit_system_message must be a bool, got "
                f"{type(omit_system_message).__name__}"
            )
        if omit_system_message and user_turn_text is None:
            raise SessionError(
                "omit_system_message requires user_turn_text: without a system "
                "message the task instruction has no place on the wire, and "
                "dropping it silently would make every recorded protocol hash "
                "describe a prompt that was never sent"
            )
        if omit_system_message and prompt_order in _SPEECH_FEATURE_PROMPT_ORDERS:
            raise SessionError(
                f"omit_system_message is not supported under prompt_order "
                f"{prompt_order!r}; the speech-feature orders own their message "
                "assembly"
            )
        self._omit_system_message = bool(omit_system_message)
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
        self._feature_root = Path(feature_root) if feature_root is not None else None
        if self._prompt_order in _SPEECH_FEATURE_PROMPT_ORDERS:
            if session.role != "inference":
                raise SessionError(
                    f"{self._prompt_order} requires a decoder-only inference session"
                )
            if self._feature_root is None:
                raise SessionError(
                    f"{self._prompt_order} requires a fixed feature_root"
                )
            try:
                self._feature_root = self._feature_root.resolve(strict=True)
            except OSError as error:
                raise SessionError(
                    f"speech feature_root is unavailable: {self._feature_root}: {error}"
                ) from error
            if not self._feature_root.is_dir():
                raise SessionError(
                    f"speech feature_root must be a directory: {self._feature_root}"
                )
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

    def _user_content(self, content: list[dict[str, object]]) -> list[dict[str, object]]:
        """``content`` plus the configured user-turn text part, if any.

        Identity function when no ``user_turn_text`` is configured, which is
        every arm that predates the Audio2Tool official-protocol cell -- see
        the constructor's note. When it IS configured, the text part goes
        after the whole content (the official order: audio, then the
        sentence) or, under ``user_turn_audio_first: false``, before it.
        """

        if self._user_turn_text is None:
            return content
        part = {"type": "text", "text": self._user_turn_text}
        return [*content, part] if self._user_turn_audio_first else [part, *content]

    def _messages(
        self, system_content: object, user_content: object
    ) -> list[dict[str, object]]:
        """``[system, user]``, or ``[user]`` alone under ``omit_system_message``.

        The one place the message list is built for every non-speech-feature
        prompt order, so the suppression cannot be applied to one order and
        forgotten on another. Identity behaviour (a system message followed by
        the user message) for every cell that does not declare the key, which
        is every cell that predates it.
        """

        user = {"role": "user", "content": user_content}
        if self._omit_system_message:
            return [user]
        return [{"role": "system", "content": system_content}, user]

    def _assert_system_message_suppression_is_lossless(
        self,
        payload: Mapping[str, object],
        *,
        evidence_texts: Sequence[str],
        exemplar_bank: Sequence[object] = (),
    ) -> None:
        """Refuse any request whose system message carries content that would
        be lost if the system message were dropped.

        Three things can travel in a system message here: the task
        instruction, the evidence block (v2/v3) and the exemplar bank (v3).
        Under ``omit_system_message`` the instruction must be carried by the
        declared ``user_turn_text`` BYTE FOR BYTE -- so what the payload,
        the trace and the protocol hash record as ``task_instruction`` is
        exactly what the model was told -- and the other two must be absent.
        """

        if not self._omit_system_message:
            return
        instruction = payload.get("task_instruction")
        if not isinstance(instruction, str) or instruction != self._user_turn_text:
            raise FrozenCoreError(
                "omit_system_message requires the payload's task_instruction to be "
                "byte-identical to the configured user_turn_text; got "
                f"{instruction!r} against {self._user_turn_text!r}. Otherwise the "
                "recorded instruction is not the instruction that was sent"
            )
        if evidence_texts:
            raise FrozenCoreError(
                "omit_system_message refuses a request carrying evidence: the "
                "evidence block travels in the system message under the "
                "evidence-first orders and would be silently dropped"
            )
        if exemplar_bank:
            raise FrozenCoreError(
                "omit_system_message refuses a request carrying an exemplar bank: "
                "the bank travels in the system message and would be silently dropped"
            )

    def render_request(self, request_bytes: bytes) -> dict[str, object]:
        """Materialize the actual send body with all identity checks, without POST."""
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
        audio_part = None
        # The ONE text-only arm: a construction-proposer payload declares
        # ``construction_targets`` (``contracts.identifiers.
        # CONSTRUCTION_VISIBLE_FIELD``, the D2 freeze), writes an ARTIFACT from
        # construction exemplars rendered into its system message, and sends no
        # audio at all -- ``core.flight.runtime._run_construction_proposer``
        # sends an EMPTY user content list, and ``rails.core_client`` builds the
        # payload from ``text_only_sample_id`` for exactly that reason. The
        # payload still NAMES its anchor's ``media_relpath`` so the gate's
        # media-identity rail and the trace can bind a real recording, but
        # loading those bytes onto the wire would both contradict the arm's own
        # registered scope ("zero audio parts are sent") and be refused outright
        # by an mmproj-free server, which is what every EVO cell serves.
        text_only = CONSTRUCTION_VISIBLE_FIELD in payload
        if self._prompt_order not in _SPEECH_FEATURE_PROMPT_ORDERS and not text_only:
            _, audio_part = _load_audio_part(
                self._data_root, payload["media_relpath"], "transport media_relpath"
            )
        # Prefix-cache-friendly order (see module docstring, 2026-08-09,
        # measured): stable evidence text FIRST, variable audio LAST -- the
        # evidence formatting string and per-field iteration order
        # (supplied_evidence then retrieved_evidence) are unchanged, only
        # their position relative to the audio part moves.
        evidence_texts: list[str] = []
        knowledge_roles: list[str | None] = []
        for field in ("supplied_evidence", "retrieved_evidence"):
            for item in payload.get(field, []):  # type: ignore[union-attr]
                evidence_texts.append(
                    f"[evidence {item['evidence_id']}] {item['content']}"
                )
                knowledge_role = item.get("knowledge_role")
                if knowledge_role is not None and knowledge_role not in {
                    "key",
                    "value",
                }:
                    raise FrozenCoreError(
                        "speech knowledge_role must be 'key', 'value', or absent"
                    )
                knowledge_roles.append(knowledge_role)
        if self._prompt_order in _SPEECH_FEATURE_PROMPT_ORDERS:
            if payload.get("query_source") != "speech_features":
                raise FrozenCoreError(
                    "speech feature request query_source must be 'speech_features'"
                )
            if payload.get("mmproj_loaded") is not False:
                raise FrozenCoreError(
                    "formal speech feature request must bind mmproj_loaded=false"
                )
            for field in ("key_representation_id", "matcher_policy_id"):
                value = payload.get(field)
                if not isinstance(value, str) or not value:
                    raise FrozenCoreError(
                        f"formal speech feature request {field} must be a non-empty string"
                    )
            descriptors = payload.get("speech_feature_parts")
            if not isinstance(descriptors, list) or not descriptors:
                raise FrozenCoreError(
                    "formal speech feature request must carry speech_feature_parts"
                )
            feature_parts: list[dict[str, object]] = []
            query_count = 0
            decoder_hashes = {
                entry.sha256
                for entry in self._session.model_files
                if "mmproj" not in Path(entry.path).name.lower()
            }
            if len(decoder_hashes) != 1:
                raise FrozenCoreError(
                    "inference session must bind exactly one decoder identity for packets"
                )
            decoder_sha256 = next(iter(decoder_hashes))
            validated_descriptors: list[dict[str, str]] = []
            for index, descriptor in enumerate(descriptors):
                required = {"packet_id", "sha256", "role"}
                if not isinstance(descriptor, Mapping) or set(descriptor) != required:
                    raise FrozenCoreError(
                        f"speech_feature_parts[{index}] must have exact keys "
                        f"{sorted(required)}"
                    )
                role = descriptor["role"]
                if role not in {"query", "key"}:
                    raise FrozenCoreError(
                        f"speech_feature_parts[{index}] role must be 'query' or 'key'"
                    )
                query_count += int(role == "query")
                validated_descriptors.append(dict(descriptor))
                feature_parts.append(
                    {
                        "type": "input_speech_features",
                        "speech_features": dict(descriptor),
                    }
                )
            load_speech_feature_packets(
                self._feature_root,
                tuple(
                    {
                        "packet_id": descriptor["packet_id"],
                        "sha256": descriptor["sha256"],
                    }
                    for descriptor in validated_descriptors
                ),
                workers=8,
                expected_decoder_gguf_sha256=decoder_sha256,
            )
            if query_count != 1:
                raise FrozenCoreError(
                    "formal speech feature request must carry exactly one query packet"
                )
            query_sha256 = next(
                descriptor["sha256"]
                for descriptor in descriptors
                if descriptor["role"] == "query"
            )
            if payload.get("speech_packet_sha256") != query_sha256:
                raise FrozenCoreError(
                    "speech_packet_sha256 must equal the actual query packet hash"
                )
            state_texts = _speech_history_texts(payload.get("history", []))
            content = _ordered_speech_feature_content(
                prompt_order=self._prompt_order,
                evidence_texts=evidence_texts,
                feature_parts=feature_parts,
                state_texts=state_texts,
                knowledge_roles=(knowledge_roles if any(knowledge_roles) else ()),
            )
            _assert_agent_history_suffix(
                prompt_order=self._prompt_order,
                content=content,
                state_texts=state_texts,
            )
            messages = [
                {"role": "system", "content": payload["task_instruction"]},
                {"role": "user", "content": content},
            ]
        elif self._prompt_order == "evidence-first-system-v2":
            # Stable-first order: [system: evidence…, instruction(+tail at its
            # end)][user: audio]. The evidence formatting strings are
            # byte-identical to v1; only their position moves.
            self._assert_system_message_suppression_is_lossless(
                payload, evidence_texts=evidence_texts
            )
            system_text = "\n\n".join(
                [*evidence_texts, str(payload["task_instruction"])]
            )
            messages = self._messages(
                system_text,
                self._user_content([] if audio_part is None else [audio_part]),
            )
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
            self._assert_system_message_suppression_is_lossless(
                payload, evidence_texts=evidence_texts, exemplar_bank=exemplar_bank
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
            messages = self._messages(
                system_content, self._user_content([*delta_parts, audio_part])
            )
        else:
            self._assert_system_message_suppression_is_lossless(
                payload, evidence_texts=evidence_texts
            )
            content: list[dict[str, object]] = [
                {"type": "text", "text": text} for text in evidence_texts
            ]
            content.append(audio_part)
            content = self._user_content(content)
            messages = self._messages(payload["task_instruction"], content)
        body: dict[str, object] = {"messages": messages}
        # Native tool-calling arm (D1a, "bare-core-native-tools"): the ONLY
        # payload field this transport reads outside decoding_params/prompt
        # content. Sent verbatim as the OpenAI-compatible `tools` key so the
        # GGUF chat template renders `<tools>...</tools>` itself -- no
        # `tool_choice` is ever added (module goal: let the template's own
        # default tool-use behavior decide, never force a call). Every arm
        # that does not declare `tool_schemas` (core.policies.build_arm_payload
        # refuses to attach it otherwise) leaves `payload.get(...)` at None
        # here and this body is byte-identical to before this arm existed.
        tool_schemas = payload.get("tool_schemas")
        if tool_schemas is not None:
            if not isinstance(tool_schemas, list) or not tool_schemas:
                raise FrozenCoreError("payload tool_schemas must be a non-empty list")
            body["tools"] = tool_schemas
        for key, value in dict(payload.get("decoding_params", {})).items():  # type: ignore[arg-type]
            if key in body:
                raise FrozenCoreError(
                    f"decoding_params key {key!r} collides with the constructed "
                    "request body and would silently override it"
                )
            body[key] = value
        return body

    def __call__(self, request_bytes: bytes) -> bytes:
        body = self.render_request(request_bytes)
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
            choice = parsed["choices"][0]
            message = choice["message"]
            # Native tool-calling arm (D1a): read tool_calls off the message
            # ONLY when it is actually a mapping carrying a non-empty list --
            # `isinstance` guards a malformed `message` shape from raising an
            # uncaught AttributeError on `.get` (message could be any JSON
            # value if the server misbehaves; a non-mapping falls straight
            # through to the legacy `message["content"]` read below, which
            # fails closed via the existing except clause exactly as before
            # this arm existed).
            response_tool_calls = (
                message.get("tool_calls") if isinstance(message, Mapping) else None
            )
            tool_call_argument_parse_errors: list[int] = []
            if isinstance(response_tool_calls, list) and response_tool_calls:
                # Canonicalize into the SAME `[{"name": ..., "arguments":
                # {...}}]` text shape the a2t-toolcall scorer already reads
                # off the free-text direct arm's `text` field -- this arm
                # requires no scorer change. Only `function.arguments`
                # parsing is lenient (module docstring precedent: a
                # malformed per-item value degrades rather than aborting the
                # whole response) -- everything else about a malformed
                # tool_calls entry (missing `function`/`name`) still raises
                # via the existing except clause below, same as a malformed
                # `content` always has.
                canonical_calls: list[dict[str, object]] = []
                for index, call in enumerate(response_tool_calls):
                    function = call["function"]
                    name = function["name"]
                    raw_arguments = function.get("arguments")
                    try:
                        arguments = (
                            json.loads(raw_arguments)
                            if isinstance(raw_arguments, str)
                            else None
                        )
                        if not isinstance(arguments, dict):
                            raise ValueError(
                                "tool call arguments must decode to a JSON object"
                            )
                    except (TypeError, ValueError):
                        arguments = {}
                        tool_call_argument_parse_errors.append(index)
                    canonical_calls.append({"name": name, "arguments": arguments})
                text = json.dumps(canonical_calls)
            else:
                text = message["content"]
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
        envelope: dict[str, object] = {"text": text, "usage": usage}
        if isinstance(response_tool_calls, list) and response_tool_calls:
            # Raw pass-through (unmodified: still the server's own
            # function.arguments JSON STRING, never the parsed dict above) so
            # a caller that wants the untouched wire shape never has to
            # re-derive it from the canonical `text` array.
            envelope["tool_calls"] = response_tool_calls
            if tool_call_argument_parse_errors:
                envelope["tool_call_argument_parse_errors"] = tool_call_argument_parse_errors
        # obs-replay-loop policy (reproduction.replay_loop, 2026-08-13): only
        # ADD the "logprobs" key when the server's own choice actually
        # carried one (i.e. the request asked for it via
        # decoding_params.logprobs -- module docstring of
        # core.model.request_types.ALLOWED_DECODING_KEYS). Every
        # pre-existing/default request never sets that decoding param, the
        # server never echoes a "logprobs" key on the choice, and this
        # envelope stays byte-identical to before this field existed
        # (tests/unit/test_llama_server_transport.py's strict equality
        # check on the canned no-logprobs response depends on exactly this).
        if isinstance(choice, Mapping) and "logprobs" in choice:
            envelope["logprobs"] = choice["logprobs"]
        return json.dumps(envelope).encode("utf-8")


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
        feature_root=(
            Path(str(values["speech_feature_root"]))
            if "speech_feature_root" in values
            else None
        ),
        # Absent from every fragment that predates the Audio2Tool official-
        # protocol cell, so those cells keep sending byte-identical requests.
        user_turn_text=(
            str(values["user_turn_text"]) if "user_turn_text" in values else None
        ),
        user_turn_audio_first=bool(values.get("user_turn_audio_first", True)),
        # Absent from every fragment that predates the 2026-09-05 Earnings-22
        # DEV ESB shape-C arm, so those cells keep sending byte-identical
        # requests. Read with `values[...]` rather than `bool(values.get(...))`
        # so a malformed value reaches the constructor's type check instead of
        # being silently coerced to True by Python truthiness.
        omit_system_message=(
            values["omit_system_message"] if "omit_system_message" in values else False
        ),
    )


TRANSPORTS.register("llama-server", _llama_server_factory)
