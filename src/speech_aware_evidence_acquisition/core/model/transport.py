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
from ..base import CoreError, NATIVE_EVIDENCE_PROJECTIONS, TRANSPORTS
from ..preparation import canonical_bytes
from ..session import (
    SessionError,
    SessionReceipt,
    assert_session_alive,
    require_loopback,
)
from . import FrozenCoreContextSizeError, FrozenCoreError
from . import native_evidence_projection as _native_evidence_projection_registration  # noqa: F401
from . import native_slot_binding_view as _native_slot_binding_view_registration  # noqa: F401
from ..reasoning_knobs import (
    RETAIN_DIAGNOSTIC_POLICY,
    REASONING_BYTES_POLICIES,
    REASONING_BYTES_POLICY,
    REASONING_WIRE_KEYS,
    ReasoningKnobError,
    ReasoningRetention,
    budget_message_from_server_args,
    project_reasoning_out_of_wire,
    reasoning_summary,
    validate_request_controls,
)
from .native_history import project_native_history
from .paths import _normalized_relative_path, _resolve_confined
from .prepared_feature_cache import PreparedFeatureCacheGuard
from .request_types import (
    NATIVE_TOOL_REQUEST_CONTROL_KEYS,
    native_tool_request_controls,
)
from .speech_features import load_speech_feature_packets


_SPEECH_FEATURE_PROMPT_ORDERS = frozenset(
    {
        "speech-features-text-keys-v1",
        "speech-query-prefix-v2",
        "knowledge-speech-state-v2",
    }
)

_RAW_NATIVE_PROMPT_ORDER = "native-raw-speech-v1"

#: Payload fields a TEXT-ONLY CONSTRUCTION request may never carry (see
#: :func:`_assert_text_only_construction_payload`). The first six are the
#: formal speech-feature request's own fields, exactly as ``rails.core_client``
#: attaches them; the last three are every other payload field that puts MEDIA
#: on the wire (the raw native query identity and the v3 exemplar-bank /
#: delta-candidate media carriers).
_TEXT_ONLY_CONSTRUCTION_REFUSED_FIELDS = (
    "query_source",
    "mmproj_loaded",
    "speech_feature_parts",
    "speech_packet_sha256",
    "key_representation_id",
    "matcher_policy_id",
    "raw_speech_query",
    "exemplar_bank",
    "delta_candidates",
)


def _assert_text_only_construction_payload(
    payload: Mapping[str, object], prompt_order: str
) -> None:
    """Fail closed on a construction-visible payload that is not text-only.

    A payload carrying ``construction_targets`` AND a speech-feature field (or
    a media part) is UNDEFINED: the two request shapes disagree about what the
    frozen core is being asked to perceive, and rendering it as either one
    would send a prompt no receipt describes. A non-empty ``history`` is
    refused for the same reason -- the text-only render has nowhere to put
    Agent state/control, so keeping it would silently drop it off the wire
    while the audited payload still recorded it.
    """

    present = [
        field
        for field in _TEXT_ONLY_CONSTRUCTION_REFUSED_FIELDS
        if field in payload
    ]
    if present:
        raise FrozenCoreError(
            "a text-only construction request under prompt_order "
            f"{prompt_order!r} must carry no speech-feature field and no media "
            f"part; got {present}"
        )
    history = payload.get("history")
    if history:
        raise FrozenCoreError(
            "a text-only construction request under prompt_order "
            f"{prompt_order!r} has nowhere to render Agent state/control; "
            "refusing rather than dropping a non-empty history off the wire"
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
            role not in {None, "key", "value"} for role in knowledge_roles
        ):
            raise FrozenCoreError(
                "speech knowledge roles must align one-to-one as key/value/absent"
            )
        key_text_parts = [
            part
            for part, role in zip(text_parts, knowledge_roles, strict=True)
            if role == "key"
        ]
        # Untyped observations remain evidence, not knowledge keys or values.
        # Preserve their order with retrieved values in the mutable suffix.
        mutable_evidence_parts = [
            part
            for part, role in zip(text_parts, knowledge_roles, strict=True)
            if role != "key"
        ]
    else:
        key_text_parts = []
        mutable_evidence_parts = []
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
        mutable_state_parts = [*mutable_evidence_parts, *state_parts]
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
                *mutable_evidence_parts,
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
            prepared_version = item.get("prepared_feedback_state_version")
            if prepared_version is not None or state_kind == "prepared-training-feedback":
                from ...rails.prepared_feedback import PreparedFeedbackStateArtifact

                prepared_fields = {
                    "turn", "role", "state_id", "state_kind", "content", "content_sha256",
                    "cited_value_ids", "prepared_feedback_state_version",
                    "prepared_artifact_sha256", "source_feedback_sha256",
                    "construction_roster_sha256", "model_context_sha256",
                }
                if set(item) != prepared_fields:
                    raise FrozenCoreError(
                        f"history[{index}] prepared feedback state has wrong fields"
                    )
                try:
                    PreparedFeedbackStateArtifact.from_json({
                        "prepared_feedback_state_version": item["prepared_feedback_state_version"],
                        "state_id": state_id,
                        "state_kind": state_kind,
                        "content": content,
                        "cited_value_ids": item["cited_value_ids"],
                        "prepared_artifact_sha256": item["prepared_artifact_sha256"],
                        "source_feedback_sha256": item["source_feedback_sha256"],
                        "construction_roster_sha256": item["construction_roster_sha256"],
                        "model_context_sha256": item["model_context_sha256"],
                    })
                except (KeyError, TypeError, ValueError) as error:
                    raise FrozenCoreError(
                        f"history[{index}] prepared feedback state is malformed: {error}"
                    ) from error
                rendered.append(f"[agent state {state_id} kind={state_kind}] {content}")
                continue
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


REASONING_CONTENT_GUARD_THINK_MARKER = "refuse-think-marker-in-content"
_REASONING_MARKERS = ("<think>", "</think>", "<thinking>", "</thinking>")


def reasoning_marker_in_content(text: object) -> str | None:
    """The first reasoning marker found in a delivered content string, else None (decision 266-E guard)."""

    if not isinstance(text, str):
        return None
    lowered = text.lower()
    for marker in _REASONING_MARKERS:
        if marker in lowered:
            return marker
    return None


def _exceed_context_message(status: int, detail: str) -> str | None:
    """The server's own message when a 400 is the context-size refusal.

    ``None`` for every other status and every other 400, including a body
    this cannot parse: a transport that guessed "probably a context
    overflow" from unparsed bytes would degrade rows on schema errors too.
    E20 (2026-09-19).
    """

    if status != 400:
        return None
    try:
        document = json.loads(detail)
    except (TypeError, ValueError):
        return None
    if not isinstance(document, Mapping):
        return None
    error = document.get("error")
    if not isinstance(error, Mapping):
        return None
    if error.get("type") != FrozenCoreContextSizeError.WIRE_ERROR_TYPE:
        return None
    message = error.get("message")
    return message if isinstance(message, str) and message else "exceed_context_size_error"


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
        preserve_wire_responses: bool = False,
        feature_cache_guard: PreparedFeatureCacheGuard | None = None,
        native_evidence_projection: str | None = None,
        native_evidence_projection_context: object | None = None,
        native_role_query_placement: str | None = None,
        reasoning_content_guard: str | None = None,
        reasoning_telemetry: bool = False,
        forced_close_message: str | None = None,
        reasoning_bytes_policy: str | None = None,
        reasoning_retention: ReasoningRetention | None = None,
    ) -> None:
        # Owner ruling 330 A (2026-10-18): the default is decision 286's projection (``hash-and-stats-only-v1``). The ONE exception,
        # ``retain-diagnostic-v1``, needs a ``ReasoningRetention`` -- which only a plan naming the diagnostic run id can build -- and a
        # reasoning-guarded transport; a retention object under any other policy, or the policy without it, is refused.
        if reasoning_bytes_policy is None:
            reasoning_bytes_policy = REASONING_BYTES_POLICY
        if reasoning_bytes_policy not in REASONING_BYTES_POLICIES:
            raise SessionError(f"reasoning_bytes_policy must be one of {sorted(REASONING_BYTES_POLICIES)}")
        if (reasoning_bytes_policy == RETAIN_DIAGNOSTIC_POLICY) != (reasoning_retention is not None):
            raise SessionError("reasoning_bytes_policy retain-diagnostic-v1 and a ReasoningRetention are required together")
        if reasoning_retention is not None and not isinstance(reasoning_retention, ReasoningRetention):
            raise SessionError("reasoning_retention must be a ReasoningRetention built from the diagnostic plan")
        if reasoning_retention is not None and reasoning_content_guard is None:
            raise SessionError("reasoning retention requires a reasoning_content_guard transport")
        self._reasoning_bytes_policy = reasoning_bytes_policy
        self._reasoning_retention = reasoning_retention
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
            _RAW_NATIVE_PROMPT_ORDER,
            *_SPEECH_FEATURE_PROMPT_ORDERS,
        ):
            raise SessionError(
                f"unknown prompt_order {prompt_order!r}; allowed: "
                "'system-instruction-v1', 'evidence-first-system-v2', "
                "'evidence-first-system-v3', 'native-raw-speech-v1', "
                f"{', '.join(repr(item) for item in sorted(_SPEECH_FEATURE_PROMPT_ORDERS))}"
            )
        self._prompt_order = prompt_order
        if native_role_query_placement is not None:
            if not isinstance(native_role_query_placement, str) or native_role_query_placement != "before-speech-v1":
                raise SessionError("native_role_query_placement must be before-speech-v1 or absent")
            if prompt_order not in _SPEECH_FEATURE_PROMPT_ORDERS | {_RAW_NATIVE_PROMPT_ORDER}:
                raise SessionError("native_role_query_placement requires a native prompt_order")
        self._native_role_query_placement = native_role_query_placement
        # Owner decision 266-E: an opt-in fail-closed guard for a reasoning (thinking) model. The delivered content channel
        # must never carry reasoning text; the server flag --reasoning-format deepseek routes thoughts to
        # message.reasoning_content, which this transport never reads. Absent for every other fragment (no behaviour change).
        if reasoning_content_guard is not None and reasoning_content_guard != REASONING_CONTENT_GUARD_THINK_MARKER:
            raise SessionError(f"reasoning_content_guard must be {REASONING_CONTENT_GUARD_THINK_MARKER} or absent")
        self._reasoning_content_guard = reasoning_content_guard
        # Thinking-core harness knobs (decision 283 A): opt-in per-contact reasoning telemetry on the envelope, enabled only
        # for a fragment that declares reasoning knobs. ``forced_close_message`` is the text of the server flag
        # --reasoning-budget-message (pinned by the fragment's forced_close_message_sha256); None means a forced close cannot
        # be detected from bytes. Both absent for every other fragment: the envelope and the request bytes do not move.
        if not isinstance(reasoning_telemetry, bool):
            raise SessionError("reasoning_telemetry must be a boolean")
        if reasoning_telemetry and reasoning_content_guard is None:
            raise SessionError("reasoning_telemetry requires reasoning_content_guard")
        if forced_close_message is not None and (not isinstance(forced_close_message, str) or not forced_close_message):
            raise SessionError("forced_close_message must be a non-empty string or absent")
        self._reasoning_telemetry = reasoning_telemetry
        self._forced_close_message = forced_close_message
        if native_evidence_projection is not None:
            if not isinstance(native_evidence_projection, str):
                raise SessionError(
                    "native_evidence_projection must be a registered string policy id "
                    f"or None, got {type(native_evidence_projection).__name__}"
                )
            if prompt_order not in _SPEECH_FEATURE_PROMPT_ORDERS | {
                _RAW_NATIVE_PROMPT_ORDER
            }:
                raise SessionError(
                    "native_evidence_projection is supported only by the native raw "
                    "and speech-feature prompt orders; got prompt_order "
                    f"{prompt_order!r}"
                )
            try:
                projector = NATIVE_EVIDENCE_PROJECTIONS.resolve(
                    native_evidence_projection
                )
            except CoreError as error:
                raise SessionError(str(error)) from error
            validator = getattr(projector, "validate_context", None)
            if validator is None:
                if native_evidence_projection_context is not None:
                    raise SessionError(
                        f"native evidence projection {native_evidence_projection!r} "
                        "does not accept a projection context"
                    )
            else:
                if not callable(validator):
                    raise SessionError(
                        f"native evidence projection {native_evidence_projection!r} "
                        "has a non-callable validate_context hook"
                    )
                if native_evidence_projection_context is None:
                    raise SessionError(
                        f"native evidence projection {native_evidence_projection!r} "
                        "requires a bound projection context"
                    )
                try:
                    validator(native_evidence_projection_context)
                except ValueError as error:
                    raise SessionError(
                        f"native evidence projection context is invalid: {error}"
                    ) from error
        elif native_evidence_projection_context is not None:
            raise SessionError(
                "native_evidence_projection_context requires a registered "
                "native_evidence_projection"
            )
        self._native_evidence_projection = native_evidence_projection
        self._native_evidence_projection_context = (
            native_evidence_projection_context
        )
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
        if user_turn_text is not None and prompt_order in (
            _SPEECH_FEATURE_PROMPT_ORDERS | {_RAW_NATIVE_PROMPT_ORDER}
        ):
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
        if omit_system_message and prompt_order in (
            _SPEECH_FEATURE_PROMPT_ORDERS | {_RAW_NATIVE_PROMPT_ORDER}
        ):
            raise SessionError(
                f"omit_system_message is not supported under prompt_order "
                f"{prompt_order!r}; the speech-feature orders own their message "
                "assembly"
            )
        self._omit_system_message = bool(omit_system_message)
        # Exact HTTP response capture is an explicit provenance opt-in. The
        # historical default stays completely untouched: no extra envelope
        # fields and no sibling trace record are produced when this is false.
        if not isinstance(preserve_wire_responses, bool):
            raise SessionError(
                "preserve_wire_responses must be a bool, got "
                f"{type(preserve_wire_responses).__name__}"
            )
        self._preserve_wire_responses = preserve_wire_responses
        self._feature_cache_guard = feature_cache_guard
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

    def render_request_with_receipt(
        self, request_bytes: bytes
    ) -> tuple[dict[str, object], dict[str, object] | None]:
        """Materialize the send body and its optional projection receipt.

        The receipt collector is local to this invocation. It is never kept on
        the transport, so concurrent request preparation cannot observe or
        overwrite another request's provenance.
        """
        projection_receipts: list[Mapping[str, object]] = []
        layout_receipts: list[Mapping[str, object]] = []
        role_query_placement = getattr(self, "_native_role_query_placement", None)
        evidence_projection = getattr(self, "_native_evidence_projection", None)
        projection_context = getattr(
            self, "_native_evidence_projection_context", None
        )
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
        audio_relpath = None
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
        prepared_text = "prepared_text" in payload
        text_only = CONSTRUCTION_VISIBLE_FIELD in payload or prepared_text
        if self._prompt_order not in _SPEECH_FEATURE_PROMPT_ORDERS and not text_only:
            audio_relpath, audio_part = _load_audio_part(
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
        # 2026-09-23 defect (cell ADV-1 SMOKE, FIRST LAUNCH REFUSED BEFORE
        # ANY CONTACT): a construction-visible payload under a SPEECH prompt
        # order had no branch at all. The smoke
        # (``slurp-native-stage3-advantage-r01-smoke-4-v1``) composes the
        # RESIDENT np4/ctx24k model fragment, whose ``prompt_order`` is
        # ``speech-query-prefix-v2``, with the ONE text-only construction
        # dispatch (``core.flight.runtime._run_construction_proposer`` ->
        # ``rails.core_client.FrozenCoreClient.complete`` ->
        # ``core.policies.build_arm_payload``). That dispatch sends the
        # D2-frozen construction field set -- the rendered instruction as the
        # system message, an EMPTY user content list, ``construction_targets``
        # and NONE of the five speech-feature fields -- so the speech-feature
        # branch below refused it at its very first rail ("speech feature
        # request query_source must be 'speech_features'"), with zero contacts
        # spent.
        #
        # The repair belongs HERE, in the renderer, not in a new fragment:
        # ``prompt_order`` travels inside the COMPARED session identity
        # (``model_fragment_sha256`` hashes the whole fragment;
        # ``core.session.serving.SERVING_IDENTITY_FIELDS``), so a sibling
        # fragment declaring a text prompt order could not attach to the
        # resident session at all.
        #
        # The render is EXACTLY the ``evidence-first-system-v2`` render of the
        # same payload: system message, empty user content, zero audio parts
        # (the ``text_only`` computation above already skipped the loader), no
        # speech-feature field required and no speech packet opened. Every
        # other payload under a speech order falls through to the branch below
        # with its refusals unchanged, in the same order.
        text_only_construction = (
            text_only and self._prompt_order in _SPEECH_FEATURE_PROMPT_ORDERS
        )
        construction_receipt: dict[str, object] | None = None
        if prepared_text:
            from ...rails.prepared_text import validate_prepared_text_payload
            try:
                validate_prepared_text_payload(payload)
            except ValueError as error:
                raise FrozenCoreError(str(error)) from error
            if evidence_projection is not None or self._user_turn_text is not None:
                raise FrozenCoreError("prepared text cannot add a projection or user-turn text")
            self._assert_system_message_suppression_is_lossless(payload, evidence_texts=[])
            state_texts = _speech_history_texts(payload["history"])
            messages = self._messages(str(payload["task_instruction"]), [
                {"type": "text", "text": text} for text in state_texts
            ])
            construction_receipt = {
                "text_only_prepared": True, "prompt_order": self._prompt_order,
                "observed_audio_seconds": 0, "audio_parts": 0, "speech_packets": 0,
                "prepared_artifact_sha256": payload["history"][0]["prepared_artifact_sha256"],
            }
        elif text_only_construction:
            _assert_text_only_construction_payload(payload, self._prompt_order)
            if evidence_projection is not None:
                raise FrozenCoreError(
                    "native evidence projection is undefined for a text-only "
                    "construction request: it projects speech/raw native "
                    "history into the request, and this payload carries no "
                    "speech query, no evidence and no history"
                )
            self._assert_system_message_suppression_is_lossless(
                payload, evidence_texts=evidence_texts
            )
            system_text = "\n\n".join(
                [*evidence_texts, str(payload["task_instruction"])]
            )
            messages = self._messages(system_text, self._user_content([]))
            construction_receipt = {
                "text_only_construction": True,
                "prompt_order": self._prompt_order,
                "reason": (
                    f"payload carries {CONSTRUCTION_VISIBLE_FIELD!r} under "
                    f"speech prompt order {self._prompt_order!r}; rendered as "
                    "the evidence-first system order renders it -- system "
                    "instruction plus an empty user content list, zero audio "
                    "parts and zero speech packets (2026-09-23, ADV-1 smoke)"
                ),
            }
        elif self._prompt_order in _SPEECH_FEATURE_PROMPT_ORDERS:
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
            from .native_framework_history import project_native_framework_history

            framework_projection = project_native_framework_history(
                payload=payload, messages=messages, state_texts=state_texts,
                evidence_projection=evidence_projection,
                projection_context=projection_context,
                receipt_sink=projection_receipts.append,
                role_query_placement=role_query_placement,
                layout_receipt_sink=layout_receipts.append,
            )
            if framework_projection is None:
                messages, historical_descriptors = project_native_history(
                    payload=payload, messages=messages, state_texts=state_texts,
                )
            else:
                messages, historical_descriptors = framework_projection
            packet_identities = {
                (item["packet_id"], item["sha256"])
                for item in validated_descriptors
            }
            for descriptor in historical_descriptors:
                identity = (descriptor["packet_id"], descriptor["sha256"])
                if identity not in packet_identities:
                    validated_descriptors.append(descriptor)
                    packet_identities.add(identity)
            # Validate historical native speech returns through the same
            # confined, hash-pinned loader as the current query and supply.
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
        elif self._prompt_order == _RAW_NATIVE_PROMPT_ORDER:
            if audio_part is None:
                raise FrozenCoreError(
                    "native raw speech requires exactly one original input_audio query"
                )
            if "speech_feature_parts" in payload:
                raise FrozenCoreError(
                    "native raw speech refuses mixed raw and feature query identities"
                )
            raw_identity = payload.get("raw_speech_query")
            required_identity_fields = {"media_relpath", "sha256"}
            if (
                not isinstance(raw_identity, Mapping)
                or set(raw_identity) != required_identity_fields
            ):
                raise FrozenCoreError(
                    "native raw speech requires raw_speech_query with exact fields "
                    "['media_relpath', 'sha256']"
                )
            raw_identity_relpath = raw_identity["media_relpath"]
            raw_identity_sha256 = raw_identity["sha256"]
            actual_raw_sha256 = hashlib.sha256(
                base64.b64decode(audio_part["input_audio"]["data"])
            ).hexdigest()
            if (
                not isinstance(raw_identity_relpath, str)
                or raw_identity_relpath != audio_relpath
                or not isinstance(raw_identity_sha256, str)
                or raw_identity_sha256 != actual_raw_sha256
            ):
                raise FrozenCoreError(
                    "native raw speech identity differs from the loaded original audio"
                )
            state_texts = _speech_history_texts(payload.get("history", []))
            content = [
                *({"type": "text", "text": text} for text in evidence_texts),
                audio_part,
                *({"type": "text", "text": text} for text in state_texts),
            ]
            _assert_agent_history_suffix(
                prompt_order=self._prompt_order,
                content=content,
                state_texts=state_texts,
            )
            messages = [
                {"role": "system", "content": payload["task_instruction"]},
                {"role": "user", "content": content},
            ]
            from .native_framework_history import project_native_framework_history

            framework_projection = project_native_framework_history(
                payload=payload, messages=messages, state_texts=state_texts,
                evidence_projection=evidence_projection,
                projection_context=projection_context,
                receipt_sink=projection_receipts.append,
                role_query_placement=role_query_placement,
                layout_receipt_sink=layout_receipts.append,
            )
            if framework_projection is None:
                messages, historical_descriptors = project_native_history(
                    payload=payload, messages=messages, state_texts=state_texts,
                )
            else:
                messages, historical_descriptors = framework_projection
            if historical_descriptors:
                raise FrozenCoreError(
                    "native raw speech refuses historical speech-feature descriptors"
                )
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
        # Historical requests omit `tool_choice`, leaving the template's own
        # default tool-use behavior unchanged. Optional native per-contact
        # controls are validated and projected below. Every arm
        # that does not declare `tool_schemas` (core.policies.build_arm_payload
        # refuses to attach it otherwise) leaves `payload.get(...)` at None
        # here and this body is byte-identical to before this arm existed.
        tool_schemas = payload.get("tool_schemas")
        if tool_schemas is not None:
            if not isinstance(tool_schemas, list):
                raise FrozenCoreError("payload tool_schemas must be a list")
            if tool_schemas:
                body["tools"] = tool_schemas
            elif payload.get("decoding_params", {}).get("tool_choice") != "none":
                raise FrozenCoreError(
                    "empty tool_schemas requires decoding_params tool_choice 'none'"
                )
        decoding_params = dict(payload.get("decoding_params", {}))  # type: ignore[arg-type]
        try:
            native_controls = native_tool_request_controls(
                decoding_params, native_tools=tool_schemas is not None
            )
        except ValueError as error:
            raise FrozenCoreError(str(error)) from error
        body.update(native_controls)
        if REASONING_WIRE_KEYS & set(decoding_params):
            # Thinking-core knobs (decision 283 A): the two per-request reasoning fields are forwarded verbatim, shape-checked, and
            # only to a transport armed with the reasoning guard (an Instruct fragment never declares them).
            if not getattr(self, "_reasoning_content_guard", None):
                raise FrozenCoreError(
                    "decoding_params carries reasoning request controls but the transport has no reasoning_content_guard"
                )
            try:
                validate_request_controls(decoding_params)
            except ReasoningKnobError as error:
                raise FrozenCoreError(str(error)) from error
        for key, value in decoding_params.items():
            if key in NATIVE_TOOL_REQUEST_CONTROL_KEYS:
                continue
            if key in body:
                raise FrozenCoreError(
                    f"decoding_params key {key!r} collides with the constructed "
                    "request body and would silently override it"
                )
            body[key] = value
        if self._feature_cache_guard is not None:
            self._feature_cache_guard.validate(payload, body)
        receipt = None
        if construction_receipt is not None:
            # A receipt for the text-only construction render, carried on the
            # SAME channel as the native-evidence-projection receipt but never
            # confused with it: the two are mutually exclusive (the branch
            # above refuses a bound projection), and ``__call__`` emits only
            # the projection one to the ORG trace.
            request_id = payload.get("request_id")
            if not isinstance(request_id, str) or not request_id:
                raise FrozenCoreError(
                    "a text-only construction request requires a non-empty "
                    "payload request_id"
                )
            receipt = {
                **construction_receipt,
                "input_request_id": request_id,
                "input_request_bytes_sha256": hashlib.sha256(
                    request_bytes
                ).hexdigest(),
                "rendered_body_canonical_sha256": hashlib.sha256(
                    canonical_bytes(body)
                ).hexdigest(),
            }
        elif evidence_projection is not None:
            if len(projection_receipts) != 1:
                raise FrozenCoreError(
                    "native evidence projection must produce exactly one receipt; "
                    f"got {len(projection_receipts)}"
                )
            request_id = payload.get("request_id")
            if not isinstance(request_id, str) or not request_id:
                raise FrozenCoreError(
                    "native evidence projection requires a non-empty payload request_id"
                )
            receipt = dict(projection_receipts[0])
            receipt.update(
                input_request_id=request_id,
                input_request_bytes_sha256=hashlib.sha256(request_bytes).hexdigest(),
                rendered_body_canonical_sha256=hashlib.sha256(
                    canonical_bytes(body)
                ).hexdigest(),
            )
        elif projection_receipts:
            raise FrozenCoreError(
                "native evidence projection emitted a receipt without an enabled policy"
            )
        if role_query_placement is not None:
            if len(layout_receipts) != 1 or construction_receipt is not None:
                raise FrozenCoreError("native role query layout requires exactly one native framework contact")
            request_id = payload.get("request_id")
            if not isinstance(request_id, str) or not request_id:
                raise FrozenCoreError("native role query layout requires a payload request_id")
            if receipt is None:
                receipt = {
                    "schema": "saea-native-role-query-layout-receipt-v1",
                    "input_request_id": request_id,
                    "input_request_bytes_sha256": hashlib.sha256(request_bytes).hexdigest(),
                    "rendered_body_canonical_sha256": hashlib.sha256(canonical_bytes(body)).hexdigest(),
                }
            receipt["role_query_layout"] = dict(layout_receipts[0])
        return body, receipt

    def render_request(self, request_bytes: bytes) -> dict[str, object]:
        """Materialize the exact send body with all checks, without POST."""

        body, _receipt = self.render_request_with_receipt(request_bytes)
        return body

    def __call__(self, request_bytes: bytes) -> bytes:
        body, projection_receipt = self.render_request_with_receipt(request_bytes)
        # The text-only construction receipt (2026-09-23, ADV-1) rides the
        # same return channel but is NOT a projection record: it names no
        # projection policy, so emitting it as one would seal an ORG
        # ``native-evidence-projection`` event for a contact that never had
        # one. Only the projection receipt reaches the trace, exactly as
        # before this branch existed.
        if projection_receipt is not None and not (
            projection_receipt.get("text_only_construction")
            or projection_receipt.get("text_only_prepared")
        ):
            from ..tracing import TraceBuffer, get_current_trace_buffer

            trace_buffer = get_current_trace_buffer()
            if not isinstance(trace_buffer, TraceBuffer):
                raise FrozenCoreError(
                    "native evidence projection requires an active native trace buffer "
                    "before dispatch"
                )
            if projection_receipt.get("schema") != "saea-native-role-query-layout-receipt-v1":
                trace_buffer.emit(
                    "ORG",
                    projection_receipt["input_request_id"]
                    + "/native-evidence-projection",
                    {"org_native_evidence_projection": projection_receipt},
                )
            if "role_query_layout" in projection_receipt:
                trace_buffer.emit(
                    "ORG", projection_receipt["input_request_id"] + "/native-role-query-layout",
                    {"org_native_role_query_layout": projection_receipt},
                )
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
            # E20 (2026-09-19): ONE error class degrades. The built fork
            # answers a prompt at or above the slot width with HTTP 400 and
            # ``error.type == "exceed_context_size_error"``
            # (``tools/server/server-common.cpp:59-62``); that -- and only
            # that -- becomes FrozenCoreContextSizeError, so an episode
            # running ``context_fit_policy == "compact-or-abstain"`` can
            # retain the row. Every other status, and every other 400,
            # raises exactly the FrozenCoreError it always did. The
            # classification reads the parsed body, never a substring of a
            # free-text message.
            context_message = _exceed_context_message(error.code, detail)
            if context_message is not None:
                raise FrozenCoreContextSizeError(
                    f"server returned HTTP {error.code} {error.reason}: {detail}",
                    server_message=context_message,
                ) from error
            raise FrozenCoreError(
                f"server returned HTTP {error.code} {error.reason}: {detail}"
            ) from error
        stored_raw = raw
        reasoning_summary_stored: dict[str, object] | None = None
        try:
            parsed = json.loads(raw.decode("utf-8"))
            choice = parsed["choices"][0]
            message = choice["message"]
            # Owner decision 286: the reasoning bytes never reach the envelope or the preserved wire response. A response that
            # carries ``message.reasoning_content`` is re-serialized without it (a ``reasoning`` object replaces it) BEFORE any
            # further read; everything sealed downstream, including ``wire_response_sha256``, is defined over this stored
            # projection. A response without the key is untouched byte for byte.
            retained_receipt: dict[str, object] | None = None
            if getattr(self, "_reasoning_retention", None) is not None:
                # Ruling 330 A: the bytes go to the diagnostic directory BEFORE the projection removes them from ``parsed``;
                # the projection below is unchanged, so the stored wire response and the envelope still carry no bytes.
                held = message.get("reasoning_content") if isinstance(message, Mapping) else None
                if isinstance(held, str):
                    sent = json.loads(request_bytes)
                    params = sent.get("decoding_params") if isinstance(sent, Mapping) else None
                    retained_receipt = self._reasoning_retention.retain(
                        sent.get("sample_id") if isinstance(sent, Mapping) else None,
                        params.get("thinking_budget_tokens") if isinstance(params, Mapping) else None,
                        held,
                    )
            stored_raw, reasoning_summary_stored = project_reasoning_out_of_wire(
                parsed, raw, getattr(self, "_forced_close_message", None),
            )
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
            leak: str | None = None
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
            leak = reasoning_marker_in_content(text) if getattr(self, "_reasoning_content_guard", None) else None
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
            if self._preserve_wire_responses:
                # Return a provenance-only envelope so the adapter can emit
                # the exact received bytes before re-raising the historical
                # malformed-response failure. It has no model-visible text.
                return json.dumps(
                    {
                        "wire_response_b64": base64.b64encode(stored_raw).decode("ascii"),
                        "wire_response_sha256": hashlib.sha256(stored_raw).hexdigest(),
                        "wire_finish_reason": None,
                        "wire_response_error": str(error),
                    }
                ).encode("utf-8")
            raise FrozenCoreError(
                f"transport returned a malformed response: {error}"
            ) from error
        if leak:
            # Fail closed BEFORE anything is returned or persisted: reasoning text is never delivered (decision 266-E).
            raise FrozenCoreError(
                f"delivered content carries a reasoning marker ({leak}); refusing the response (reasoning_content_guard)"
            )
        envelope: dict[str, object] = {"text": text, "usage": usage}
        if getattr(self, "_reasoning_content_guard", None):
            # Owner decision 266-E (cap amendment): a reasoning core can spend its whole completion budget on reasoning and leave
            # ``content`` empty. The server's finish reason is forwarded ONLY under the opt-in reasoning guard, so an empty delivery can
            # be receipted as a cap hit (``rails.runner.EMPTY_COMPLETION_SCHEMA``); every other transport envelope is byte-identical.
            envelope["finish_reason"] = choice.get("finish_reason") if isinstance(choice, Mapping) else None
        if reasoning_summary_stored is not None:
            # Decision 286: hash and statistics of the dropped reasoning bytes -- on every path, whatever the knobs.
            envelope["reasoning"] = reasoning_summary_stored
            if retained_receipt is not None:
                envelope["reasoning_retention"] = retained_receipt
        elif getattr(self, "_reasoning_telemetry", False):
            # Decision 283 A: a reasoning fragment whose response carried no reasoning channel still reports zero counts.
            raw_usage = parsed.get("usage") if isinstance(parsed, Mapping) else None
            details = raw_usage.get("completion_tokens_details") if isinstance(raw_usage, Mapping) else None
            envelope["reasoning"] = reasoning_summary(
                None, getattr(self, "_forced_close_message", None),
                details.get("reasoning_tokens") if isinstance(details, Mapping) else None,
                choice.get("finish_reason") if isinstance(choice, Mapping) else None,
            )
        if self._preserve_wire_responses:
            # Keep the server bytes exactly as received. The adapter validates
            # the envelope and emits these fields on a separate trace channel;
            # MODEL_RESPONSE keeps its historical text/usage shape; its
            # normalized-envelope hash necessarily includes these opt-in fields.
            # ``wire_response_sha256`` is the hash of the STORED wire response (the decision-286 projection when the response
            # carried reasoning; the server bytes otherwise). ``reasoning["reasoning_content_sha256"]`` binds the dropped bytes.
            envelope["wire_response_b64"] = base64.b64encode(stored_raw).decode("ascii")
            envelope["wire_response_sha256"] = hashlib.sha256(stored_raw).hexdigest()
            envelope["wire_finish_reason"] = (
                choice.get("finish_reason") if isinstance(choice, Mapping) else None
            )
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
    feature_cache_guard: PreparedFeatureCacheGuard | None = None,
    reasoning_retention: ReasoningRetention | None = None,
):
    if "reasoning_bytes_policy" in values:
        # Ruling 330 A: the retention exception is never declarable in a model fragment; only a diagnostic plan builds it.
        raise SessionError("reasoning_bytes_policy cannot be declared in a model fragment")
    projection_id = values.get("native_evidence_projection")
    params_present = "native_evidence_projection_params" in values
    if params_present and not isinstance(
        values["native_evidence_projection_params"], Mapping
    ):
        raise SessionError(
            "native_evidence_projection_params must be a mapping when declared"
        )
    projection_context = None
    if projection_id is None:
        if params_present:
            raise SessionError(
                "native_evidence_projection_params requires native_evidence_projection"
            )
    elif isinstance(projection_id, str):
        try:
            projector = NATIVE_EVIDENCE_PROJECTIONS.resolve(projection_id)
        except CoreError as error:
            raise SessionError(str(error)) from error
        binder = getattr(projector, "bind_config", None)
        if binder is None:
            if params_present:
                raise SessionError(
                    "native_evidence_projection_params is not accepted by "
                    f"unbound projection {projection_id!r}"
                )
        else:
            if not callable(binder):
                raise SessionError(
                    f"native evidence projection {projection_id!r} has a "
                    "non-callable bind_config hook"
                )
            try:
                projection_context = binder(values, data_root)
            except ValueError as error:
                raise SessionError(
                    f"native evidence projection configuration is invalid: {error}"
                ) from error
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
        preserve_wire_responses=(
            values["preserve_wire_responses"]
            if "preserve_wire_responses" in values
            else False
        ),
        feature_cache_guard=feature_cache_guard,
        native_evidence_projection=(
            values["native_evidence_projection"]
            if "native_evidence_projection" in values
            else None
        ),
        native_evidence_projection_context=projection_context,
        native_role_query_placement=values.get("native_role_query_placement"),
        reasoning_content_guard=values.get("reasoning_content_guard"),
        # Decision 283 A: absent from every fragment that declares no reasoning knob, so those transports keep their envelope.
        reasoning_telemetry=bool(
            {"reasoning_budget_tokens", "answer_reserve_tokens", "enable_thinking", "forced_close_message_sha256"}
            & set(values)
        ),
        forced_close_message=budget_message_from_server_args(values.get("server_args")),
        reasoning_bytes_policy=RETAIN_DIAGNOSTIC_POLICY if reasoning_retention is not None else None,
        reasoning_retention=reasoning_retention,
    )


TRANSPORTS.register("llama-server", _llama_server_factory)
