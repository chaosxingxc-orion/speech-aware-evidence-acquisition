"""CoreClient: the seam every rails runner call reaches "the model" through --
kept SEPARATE from ``core.model.FrozenCoreAdapter`` deliberately.

``FrozenCoreAdapter`` is the production, gate-enforced, budget-metered
request path (``PayloadBindingContext``, ``AttemptStore``, ``TraceSink``,
the D2 arm-field allowlist -- ``core.model.adapter``); wiring it in here
would mean this zero-model-contact engineering skeleton also has to
construct a live ``FrozenCoreGate``, an attempt store and a verified split,
none of which a rails-only test fixture has any business building, and B0's
mission is explicit: engineering only, ZERO model contact. ``CoreClient`` is
instead the minimal request seam a ``TaskAdapter``'s assembled messages
need. Optional formal speech-feature and Agent state/control bindings remain
on this one protocol; callers that omit them keep the historical audio/text
behavior.

That future task is :class:`FrozenCoreClient` below (bridge mission,
2026-08-17): it delegates every ``complete()`` call to a real
``FrozenCoreAdapter`` it owns, translating the rails ``messages`` shape
(``[{"role": "system", "content": <task_instruction>}, {"role": "user",
"content": [...text parts..., {"type": "input_audio", "media_relpath":
...}]}]`` -- exactly what ``rails.adapters.slurp.SlurpAdapter``/
``rails.adapters.audio2tool.Audio2ToolAdapter`` already assemble) into the
richer, D2-allowlisted payload shape ``FrozenCoreAdapter.request`` requires.
This module STILL never touches a real model, real gate, or real transport
itself: it is the bridge, not a flight -- every test here uses a fake gate
and a fake transport (mirroring ``tests/unit/test_frozen_core_adapter.py``'s
own ``_OpenGate``/``_fake_transport`` doubles), exactly like the rest of
this repository's own engineering-only test suite. Constructing a REAL
``FrozenCoreGate``, spawning a REAL session, and actually flying a probe
against a resident server is a *different*, later mission's job -- see
``docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md``'s own
"Preconditions" section, which names this bridge as exactly that
precondition.

D2 arm choice (single, fixed): :data:`DEFAULT_RAILS_ARM` --
``"fixed-legal-context"`` -- is the one D2-frozen arm whose field set this
bridge builds payloads for. It is a superset covering BOTH rails arms: the
zero-supply arm sends ``supplied_evidence: []`` / ``evidence_provenance: []``
(present-but-empty, never omitted -- ``FrozenCoreAdapter.request`` enforces
an EXACT key set per arm, so a field cannot simply be left out), the
supplied arm sends one evidence item per rails ``{"type": "text", ...}``
content part. ``"fixed-retrieval"`` is not used: rails never performs
retrieval (no ``retrieval_query`` concept in ``rails.runner``), so a
retrieval-shaped arm would always leave that field meaninglessly unset.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence, runtime_checkable

from ..contracts import (
    CONSTRUCTION_VISIBLE_FIELD,
    ExecutionPlan,
    assert_execution_scope,
)
from ..core.base import PayloadBindingContext
from ..core.flight_lock import read_flight_lock
from ..core.model import (
    FrozenCoreAdapter,
    FrozenCoreError,
    SliceRegistry,
    SpeechFeaturePacketV1,
    load_speech_feature_packets,
)
from ..core.model.binding import _PayloadBindingMixin
from ..core.model.request_types import CoreResponse, wire_response_message
from ..core.model.paths import _normalized_relative_path, _resolve_confined_any
from ..core.model.slices import SliceRecord
from ..core.tracing import DispatchingSink, TraceBuffer, TraceSink
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .errors import RailsError
from .execution_units import ExecutionUnit, ExecutionUnitRoster, execution_unit_scope
from .knowledge import AgentStateArtifact


@dataclass(frozen=True)
class CoreCompletion:
    """An immutable response bound to one actual adapter request.

    Native call bytes are retained without interpreting malformed arguments.
    Consumers receive independent decoded copies and must validate the binding
    before deciding whether this response authorizes an internal tool action.
    Historical text completions do not create or expose this object.
    """

    text: str
    request_id: str
    sample_id: str
    agent_contact_id: str | None
    request_sha256: str
    response_sha256: str
    response_text_sha256: str
    tool_calls_json: bytes = field(repr=False)
    # Exact preserved server response bytes. Absent for the historical
    # transport default; never reconstructed from normalized text.
    wire_response_bytes: bytes | None = field(default=None, repr=False, compare=False)
    # Derived from the actual built payload, after per-contact narrowing.
    # An empty tuple is a native tool-free contact; None is a non-native one.
    tool_names: tuple[str, ...] | None = None
    tool_schemas_sha256: str | None = None

    @property
    def tool_calls(self) -> object:
        """Return exact transport-forwarded calls, never repaired arguments."""
        return json.loads(self.tool_calls_json)

    @property
    def tool_calls_sha256(self) -> str:
        return hashlib.sha256(self.tool_calls_json).hexdigest()

    @property
    def original_message(self) -> Mapping[str, object] | None:
        return wire_response_message(self.wire_response_bytes, self.tool_calls)[0]

    @property
    def finish_reason(self) -> object | None:
        return wire_response_message(self.wire_response_bytes, self.tool_calls)[1]

    def assert_binding(
        self, *, sample_id: str, agent_contact_id: str | None,
        response_text: str,
    ) -> None:
        if (
            self.sample_id != sample_id
            or self.agent_contact_id != agent_contact_id
            or self.text != response_text
            or not isinstance(response_text, str)
            or hashlib.sha256(response_text.encode("utf-8")).hexdigest()
            != self.response_text_sha256
        ):
            raise FrozenCoreClientError("completion binding does not match this contact")


@dataclass(frozen=True)
class PreparedCoreRequest:
    """An immutable, client-owned request template; preparation spends no contact."""

    payload_bytes: bytes
    token: object = field(repr=False, compare=False)

    def as_payload(self) -> dict[str, object]:
        """Return an independent copy for the shared transport capacity check."""
        return json.loads(self.payload_bytes)


_PREPARED_REQUEST_ID = "saea-prepared-request"


@runtime_checkable
class CoreClient(Protocol):
    """One completion call: chat-style ``messages`` in, response text out.
    No implementation in THIS module ever touches a real model -- see
    :class:`MockCoreClient` below, the only implementation this engineering
    mission constructs.

    ``text_only_sample_id`` (P-KEY machinery, 2026-08-19): opt-in, default
    ``None`` -- every EXISTING caller never passes it and observes byte-
    identical behaviour. When a caller names a sample id here, ``messages``
    is a REGISTERED TEXT-ONLY arm's own prompt (e.g.
    ``rails.probes.pkey_flight.assemble_txt_messages``'s TXT-NOSUP/TXT-SUP
    output) -- audio-free BY CONSTRUCTION, never carrying an
    ``input_audio`` content part -- and ``text_only_sample_id`` is how the
    caller identifies WHICH bound sample this text-only request is about
    (a text-only ``messages`` shape carries no ``media_relpath`` a client
    could otherwise reverse-look-up). ``agent_state`` plus
    ``agent_contact_id``/``contact_instruction`` are accepted only together
    on a formal speech-feature request or the explicit raw native arm.
    They populate D2's separate
    ``history`` field, never ``supplied_evidence``. See
    :class:`FrozenCoreClient.complete` for the real validation this gates.
    """

    def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        decoding_params: Mapping[str, object] | None = None,
        text_only_sample_id: str | None = None,
        speech_feature_sample_id: str | None = None,
        raw_agent_sample_id: str | None = None,
        key_representation_id: str | None = None,
        matcher_policy_id: str | None = None,
        agent_state: Sequence[Mapping[str, object]] | None = None,
        agent_contact_id: str | None = None,
        contact_instruction: str | None = None,
        construction_target_ids: Sequence[str] | None = None,
        tool_names: Sequence[str] | None = None,
    ) -> str: ...


@dataclass
class MockCoreClient:
    """Deterministic, in-process ``CoreClient`` for tests -- zero model
    contact, zero I/O, zero network. ``responder`` resolves each call's
    response text from the messages it was given (default: a stable canned
    string plus a request counter, so distinct calls never collide);
    ``calls`` records every ``(messages, decoding_params)`` pair actually
    sent, for tests that assert on what a runner/adapter actually
    assembled."""

    responder: Callable[[Sequence[Mapping[str, object]]], str] | None = None
    calls: list[tuple[tuple[Mapping[str, object], ...], Mapping[str, object]]] = field(
        default_factory=list
    )

    def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        decoding_params: Mapping[str, object] | None = None,
        text_only_sample_id: str | None = None,
        speech_feature_sample_id: str | None = None,
        key_representation_id: str | None = None,
        matcher_policy_id: str | None = None,
        agent_state: Sequence[Mapping[str, object]] | None = None,
        agent_contact_id: str | None = None,
        contact_instruction: str | None = None,
        construction_target_ids: Sequence[str] | None = None,
    ) -> str:
        # text_only_sample_id is accepted (never validated -- this is a mock,
        # zero real invariants live here by design, module docstring) purely
        # so a flight that calls it unconditionally (rails.probes.pkey_flight's
        # own TXT-arm loops) works unchanged against BOTH this mock and the
        # real FrozenCoreClient below. THE TEST LESSON this repository keeps
        # re-learning: this acceptance is exactly why a test that only drives
        # THIS class can never catch a missing real invariant -- see
        # tests/unit/test_rails_frozen_core_client.py's own text-mode tests,
        # which drive FrozenCoreClient.complete directly instead.
        recorded_params = dict(decoding_params) if decoding_params else {}
        self.calls.append((tuple(messages), recorded_params))
        if self.responder is not None:
            return self.responder(messages)
        return f"mock-response-{len(self.calls)}"


class FrozenCoreClientError(RailsError):
    """The bridge refuses: a malformed rails ``messages`` shape, a
    ``media_relpath`` this client cannot resolve to a bound sample, or a D2
    arm whose field set this bridge does not know how to build a payload
    for."""


# The exact field set FrozenCoreClient's own payload builder produces --
# never grown ad hoc (module docstring: "the arm payload vocabulary never
# grows without a new D2 receipt", core.policies). A D2 arm is usable here
# iff its ARM_VISIBLE_FIELDS entry is EXACTLY this set.
_SUPPORTED_ARM_FIELDS = frozenset(
    {
        "request_id",
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
        "task_instruction",
        "history",
        "decoding_params",
        "supplied_evidence",
        "evidence_provenance",
    }
)

_SPEECH_FEATURE_ARM_FIELDS = _SUPPORTED_ARM_FIELDS | frozenset(
    {
        "speech_feature_parts",
        "speech_packet_sha256",
        "query_source",
        "key_representation_id",
        "matcher_policy_id",
        "mmproj_loaded",
    }
)

# Native tool-calling field-set extension (D1b, 2026-09-03): "for BOTH audio
# paths" -- a client bound to EITHER the raw-audio (_SUPPORTED_ARM_FIELDS) or
# the packet (_SPEECH_FEATURE_ARM_FIELDS) field set may ALSO be bound to that
# same field set plus exactly one extra field, "tool_schemas" (D1a's own
# "bare-core-native-tools" naming convention: a NEW field on a NEW arm, never
# grown ad hoc onto an existing frozen tuple -- core.policies module
# docstring). The raw-audio member is the explicit
# ``raw-speech-agent-native-tools`` D2 arm. Construction still fails closed for
# arm names absent from ARM_VISIBLE_FIELDS ("unknown D2 arm").
_NATIVE_TOOLS_FIELD = "tool_schemas"
_NATIVE_TOOLS_SUPPORTED_ARM_FIELDS = _SUPPORTED_ARM_FIELDS | frozenset(
    {_NATIVE_TOOLS_FIELD}
)
_RAW_NATIVE_ARM = "raw-speech-agent-native-tools"
_RAW_NATIVE_ARM_FIELDS = _NATIVE_TOOLS_SUPPORTED_ARM_FIELDS | {"raw_speech_query"}
_NATIVE_TOOLS_SPEECH_FEATURE_ARM_FIELDS = _SPEECH_FEATURE_ARM_FIELDS | frozenset(
    {_NATIVE_TOOLS_FIELD}
)

# Zero-supply raw-audio field sets (2026-09-04). Every field set above carries
# "supplied_evidence"/"evidence_provenance", because this bridge was written
# for "fixed-legal-context" (A0 flew zero-supply THROUGH that evidence-carrying
# arm, sending empty lists). "bare-core" and "bare-core-native-tools" declare no
# evidence fields at all, and FrozenCoreAdapter.request enforces
# set(payload) == ARM_VISIBLE_FIELDS[arm] EXACTLY, so a payload carrying two
# empty evidence lists is an allowlist violation for them, not a harmless
# extra. Accepting the evidence-free field sets here -- and omitting exactly
# those two keys from the payload for them -- is what makes the D1a arm
# "bare-core-native-tools" reachable at all.
_EVIDENCE_FIELDS = frozenset({"supplied_evidence", "evidence_provenance"})
_ZERO_SUPPLY_ARM_FIELDS = _SUPPORTED_ARM_FIELDS - _EVIDENCE_FIELDS
_NATIVE_TOOLS_ZERO_SUPPLY_ARM_FIELDS = _ZERO_SUPPLY_ARM_FIELDS | frozenset(
    {_NATIVE_TOOLS_FIELD}
)
# Construction-proposer field set (E2.4, 2026-09-05): bare-core's own
# zero-supply field set plus exactly one extra field,
# "construction_targets" -- the D2 arm on which the frozen core may see gold,
# and only CONSTRUCTION gold (e0.d2_leakage.ARM_VISIBLE_FIELDS
# ["construction-proposer-text"], contracts.CONSTRUCTION_VISIBLE_ARMS). Same
# "a NEW field on a NEW arm, never grown onto an existing frozen tuple"
# discipline as _NATIVE_TOOLS_FIELD above. The contact is text-only: the
# proposer is asked to write an artifact from construction exemplars, so
# there is no audio part at all and complete() takes the
# text_only_sample_id path.
_CONSTRUCTION_TARGETS_FIELD = CONSTRUCTION_VISIBLE_FIELD
_CONSTRUCTION_PROPOSER_ARM_FIELDS = _ZERO_SUPPLY_ARM_FIELDS | frozenset(
    {_CONSTRUCTION_TARGETS_FIELD}
)
_PREPARED_TEXT_ARM_FIELDS = _ZERO_SUPPLY_ARM_FIELDS | {"prepared_text"}
_ACCEPTED_ARM_FIELD_SETS = frozenset(
    {
        _SUPPORTED_ARM_FIELDS,
        _SPEECH_FEATURE_ARM_FIELDS,
        _NATIVE_TOOLS_SUPPORTED_ARM_FIELDS,
        _RAW_NATIVE_ARM_FIELDS,
        _NATIVE_TOOLS_SPEECH_FEATURE_ARM_FIELDS,
        _ZERO_SUPPLY_ARM_FIELDS,
        _NATIVE_TOOLS_ZERO_SUPPLY_ARM_FIELDS,
        _CONSTRUCTION_PROPOSER_ARM_FIELDS,
        _PREPARED_TEXT_ARM_FIELDS,
    }
)
_SPEECH_FEATURE_FAMILY_ARM_FIELDS = frozenset(
    {_SPEECH_FEATURE_ARM_FIELDS, _NATIVE_TOOLS_SPEECH_FEATURE_ARM_FIELDS}
)

DEFAULT_RAILS_ARM = "fixed-legal-context"


@dataclass(frozen=True)
class ValidatedSpeechPacketSet:
    """Immutable whole-roster packet validation prepared before serving.

    This object is an in-memory cache value. Callers must obtain it from
    :func:`validate_speech_packet_set`; the client independently verifies its
    bindings before using it and always revalidates request packet bytes.
    """

    feature_root: Path
    bindings: tuple[tuple[str, str, str], ...]
    media_relpaths: tuple[tuple[str, str], ...]
    data_root: Path
    packets: tuple[SpeechFeaturePacketV1, ...]
    decoder_gguf_sha256: str
    n_embd: int

    def matches(
        self,
        feature_root: Path,
        packet_bindings: Mapping[str, Mapping[str, str]],
        binding: PayloadBindingContext,
    ) -> bool:
        try:
            root = Path(feature_root).resolve(strict=True)
        except OSError:
            return False
        if set(packet_bindings) != set(binding.allowed_sample_ids):
            return False
        if any(
            not isinstance(entry, Mapping)
            or set(entry) != {"packet_id", "sha256"}
            or not isinstance(entry["packet_id"], str)
            or not isinstance(entry["sha256"], str)
            for entry in packet_bindings.values()
        ):
            return False
        expected = tuple(sorted(
            (sample_id, entry["packet_id"], entry["sha256"])
            for sample_id, entry in packet_bindings.items()
        ))
        media = tuple(sorted(binding.media_relpaths.items()))
        try:
            data_root = Path(binding.data_root).resolve(strict=True)
        except OSError:
            return False
        return (
            root == self.feature_root
            and data_root == self.data_root
            and expected == self.bindings
            and media == self.media_relpaths
            and {sample_id for sample_id, _, _ in self.bindings}
            == set(binding.allowed_sample_ids)
        )


def validate_speech_packet_set(
    feature_root: Path,
    packet_bindings: Mapping[str, Mapping[str, str]],
    binding: PayloadBindingContext,
    *,
    workers: int = 8,
) -> ValidatedSpeechPacketSet:
    """Validate every bound packet and audio file using the shared loaders."""
    if isinstance(workers, bool) or not isinstance(workers, int) or workers <= 0:
        raise FrozenCoreClientError("speech packet validation workers must be positive")
    try:
        root = Path(feature_root).resolve(strict=True)
    except OSError as error:
        raise FrozenCoreClientError(f"speech_feature_root is unavailable: {error}") from error
    if not root.is_dir() or set(packet_bindings) != set(binding.allowed_sample_ids):
        raise FrozenCoreClientError("speech packet bindings must cover the complete bound roster")
    ordered = tuple(sorted(packet_bindings))
    descriptors: list[dict[str, str]] = []
    bindings: list[tuple[str, str, str]] = []
    for sample_id in ordered:
        entry = packet_bindings[sample_id]
        if not isinstance(entry, Mapping) or set(entry) != {"packet_id", "sha256"}:
            raise FrozenCoreClientError(f"speech packet binding for {sample_id!r} is malformed")
        packet_id, sha256 = entry["packet_id"], entry["sha256"]
        if not isinstance(packet_id, str) or not isinstance(sha256, str):
            raise FrozenCoreClientError(f"speech packet binding for {sample_id!r} is malformed")
        descriptors.append({"packet_id": packet_id, "sha256": sha256})
        bindings.append((sample_id, packet_id, sha256))
    packets = load_speech_feature_packets(root, tuple(descriptors), workers=workers)

    def audio_sha256(sample_id: str) -> str:
        audio_path = Path(binding.data_root) / binding.media_relpaths[sample_id]
        return hashlib.sha256(audio_path.read_bytes()).hexdigest()

    with ThreadPoolExecutor(
        max_workers=min(workers, len(ordered)), thread_name_prefix="saea-speech-audio"
    ) as pool:
        audio_sha256s = tuple(pool.map(audio_sha256, ordered))
    for sample_id, packet, audio_digest in zip(ordered, packets, audio_sha256s, strict=True):
        if packet.audio_sha256 != audio_digest:
            raise FrozenCoreClientError(f"speech packet bound to {sample_id!r} does not match its audio bytes")
    decoders = {packet.decoder_gguf_sha256 for packet in packets}
    dimensions = {chunk.n_embd for packet in packets for chunk in packet.chunks}
    if len(decoders) != 1 or len(dimensions) != 1:
        raise FrozenCoreClientError("speech packet bindings must share one decoder identity and dimension")
    return ValidatedSpeechPacketSet(
        root, tuple(bindings), tuple(sorted(binding.media_relpaths.items())),
        Path(binding.data_root).resolve(strict=True), packets, next(iter(decoders)),
        next(iter(dimensions)),
    )


def _validate_construction_targets(
    construction_targets: Sequence[Mapping[str, object]] | None,
) -> tuple[dict[str, str], ...]:
    """A construction-proposer arm's own ``construction_targets`` invariant:
    a non-empty sequence of ``{"sample_id": str, "target": str}`` entries and
    nothing else.

    The exact-key check is the point. ``target`` is the construction row's
    gold rendered as English text (the tool-call string for Audio2Tool, the
    ``{scenario, action, entities}`` JSON for SLURP), and an entry carrying
    any further key would be an unaudited channel into the one arm on which
    gold is visible at all. Every entry is copied into a plain ``dict`` so
    the client's stored tuple never aliases a caller-owned mutable object.
    """

    if (
        construction_targets is None
        or not isinstance(construction_targets, Sequence)
        or isinstance(construction_targets, (str, bytes))
        or not construction_targets
    ):
        raise FrozenCoreClientError(
            "a construction-proposer arm requires a non-empty construction_targets "
            "sequence"
        )
    validated: list[dict[str, str]] = []
    for index, entry in enumerate(construction_targets):
        if not isinstance(entry, Mapping) or set(entry) != {"sample_id", "target"}:
            raise FrozenCoreClientError(
                f"construction_targets[{index}] must be a mapping with exactly the keys "
                "{'sample_id', 'target'}"
            )
        sample_id = entry["sample_id"]
        target = entry["target"]
        if not isinstance(sample_id, str) or not sample_id:
            raise FrozenCoreClientError(
                f"construction_targets[{index}].sample_id must be a non-empty string"
            )
        if not isinstance(target, str) or not target:
            raise FrozenCoreClientError(
                f"construction_targets[{index}].target must be a non-empty string"
            )
        validated.append({"sample_id": sample_id, "target": target})
    return tuple(validated)


def tool_free_native_schemas(tool_schemas: object) -> bool:
    """True for the explicit EMPTY tuple a tool-free native arm hands the
    client (item E23b): the arm keeps its native request contract while no
    role holds tool authority. ``None`` and non-empty sequences are not
    tool-free and go through :func:`_validate_tool_schemas` as before."""
    return isinstance(tool_schemas, tuple) and len(tool_schemas) == 0


def _validate_tool_schemas(
    tool_schemas: Sequence[Mapping[str, object]] | None,
) -> tuple[dict[str, object], ...]:
    """A native tool-calling arm's own ``tool_schemas`` invariant: a
    non-empty sequence of OpenAI-format ``{"type": "function", "function":
    {"name": ..., ...}}`` entries -- the exact shape
    ``data.audio2tool_tools.render_openai_tools`` produces (never imported
    here; module docstring -- this bridge's own dependency surface stays
    light). Every entry is copied through canonical JSON so no nested value in
    the client's stored tuple aliases a caller-owned mutable object."""

    if (
        tool_schemas is None
        or not isinstance(tool_schemas, Sequence)
        or isinstance(tool_schemas, (str, bytes))
        or not tool_schemas
    ):
        raise FrozenCoreClientError(
            "a native tool-calling arm requires a non-empty tool_schemas sequence"
        )
    validated: list[dict[str, object]] = []
    names: set[str] = set()
    for index, entry in enumerate(tool_schemas):
        if not isinstance(entry, Mapping):
            raise FrozenCoreClientError(
                f"tool_schemas[{index}] must be a mapping, got {type(entry).__name__}"
            )
        try:
            copied = json.loads(
                json.dumps(
                    entry,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            )
        except (TypeError, ValueError) as error:
            raise FrozenCoreClientError(
                f"tool_schemas[{index}] must be JSON-compatible"
            ) from error
        if not isinstance(copied, dict):
            raise FrozenCoreClientError(
                f"tool_schemas[{index}] must serialize to a JSON object"
            )
        entry = copied
        if entry.get("type") != "function":
            raise FrozenCoreClientError(
                f"tool_schemas[{index}] must declare type 'function'"
            )
        function = entry.get("function")
        if not isinstance(function, Mapping):
            raise FrozenCoreClientError(
                f"tool_schemas[{index}] must carry a 'function' mapping"
            )
        name = function.get("name")
        if not isinstance(name, str) or not name:
            raise FrozenCoreClientError(
                f"tool_schemas[{index}].function.name must be a non-empty string"
            )
        if name in names:
            raise FrozenCoreClientError(
                "tool_schemas must not contain duplicate function names"
            )
        names.add(name)
        validated.append(entry)
    return tuple(validated)


def _tool_schemas_sha256(tool_schemas: Sequence[Mapping[str, object]]) -> str:
    """SHA-256 of the canonical (sorted-key, compact) JSON of
    ``tool_schemas`` -- the SAME convention as
    ``data.audio2tool_tools.openai_tools_sha256``, re-implemented locally
    (never imported -- module docstring) so this bridge's own dependency
    surface stays light. A synthetic-list agreement test between the two
    lives in tests/unit/test_rails_core_client_native_tools.py."""

    blob = json.dumps(
        list(tool_schemas), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _probe_sample_rate_hz(path: Path) -> int:
    """Read ONLY the header of the audio file at ``path`` for its sample
    rate -- mirrors ``data.slurp._audio_seconds``'s own function-local,
    header-only ``soundfile`` read (repo convention: heavy imports stay
    function-local, package top-level imports stay light); never decodes
    audio frames. ``rails.task_adapter.TaskSample`` (unlike
    ``data.loader.SampleRef``) carries no ``sample_rate_hz`` field at all --
    every concrete rails carrier (SLURP flac, Audio2Tool wav) is header-
    readable via ``soundfile``, so this is the one place a rails-layer
    binding recovers the fact ``FrozenCoreAdapter``'s payload binding (I3)
    requires."""

    import soundfile  # deferred: heavy import stays function-local (repo convention)

    try:
        info = soundfile.info(str(path))
    except Exception as error:  # soundfile raises its own libsndfile error types
        raise FrozenCoreClientError(
            f"cannot read audio header of {path}: {error}"
        ) from error
    rate = info.samplerate
    if isinstance(rate, bool) or not isinstance(rate, int) or rate <= 0:
        raise FrozenCoreClientError(
            f"audio header of {path} reports sample rate {rate!r}"
        )
    return rate


def probe_sample_rate_hz(path: Path) -> int:
    """Public alias of :func:`_probe_sample_rate_hz` for callers outside this
    module that need the same header-only sample-rate probe -- e.g.
    ``rails.silence_swap.build_silence_swap_slice``, which matches a
    silence-swap control's generated format to the parent sample's own real
    header rate."""

    return _probe_sample_rate_hz(path)


def build_payload_binding(
    *,
    carrier_lock_key: str,
    samples: Sequence[object],
    data_root: Path,
    carrier_root: Path,
    derived_media_roots: Sequence[Path] = (),
    sample_rate_prober: Callable[[Path], int] = _probe_sample_rate_hz,
) -> PayloadBindingContext:
    """The :class:`~core.base.PayloadBindingContext` a :class:`FrozenCoreClient`
    needs, built directly from rails ``TaskSample`` objects (duck-typed:
    ``sample_id``/``audio_ref.path``/``audio_seconds``, exactly
    ``rails.task_adapter.TaskSample``'s own three fields) -- the rails-layer
    counterpart to ``core.driver.run_experiment``'s own construction from
    ``core.base.SampleRef`` objects. ``sample_rate_hz`` -- the one media fact
    a rails ``TaskSample`` does not carry -- is probed from each sample's own
    audio file header (never trusted from any payload; :func:`_probe_sample_rate_hz`
    by default, injectable for tests). ``carrier_root`` is the SAME per-carrier
    subdirectory ``data.lock.asset_dir(lock, carrier_lock_key, root)`` would
    resolve -- callers already hold ``lock``/``root`` for their own carrier
    loading and pass the result straight through, so this module (like the
    rest of ``rails``) never needs its own lock coupling.

    ``derived_media_roots`` is the composed dataset fragment's own declared
    derived media roots (``core.base.declared_derived_media_roots``), empty for
    every fragment that declares none. See
    :attr:`core.base.PayloadBindingContext.derived_media_roots`."""

    if not samples:
        raise FrozenCoreClientError(
            "build_payload_binding requires at least one sample"
        )
    allowed_sample_ids: set[str] = set()
    sample_facts: dict[str, tuple[float, int]] = {}
    media_relpaths: dict[str, str] = {}
    for sample in samples:
        sample_id = sample.sample_id
        if not isinstance(sample_id, str) or not sample_id:
            raise FrozenCoreClientError(
                f"sample_id must be a non-empty string, got {sample_id!r}"
            )
        if sample_id in allowed_sample_ids:
            raise FrozenCoreClientError(f"duplicate sample_id {sample_id!r} in samples")
        allowed_sample_ids.add(sample_id)
        media_relpath = sample.audio_ref.path
        media_relpaths[sample_id] = media_relpath
        sample_rate_hz = sample_rate_prober(Path(data_root) / media_relpath)
        sample_facts[sample_id] = (float(sample.audio_seconds), sample_rate_hz)
    return PayloadBindingContext(
        carrier_lock_key=carrier_lock_key,
        allowed_sample_ids=frozenset(allowed_sample_ids),
        sample_facts=sample_facts,
        data_root=Path(data_root),
        carrier_root=Path(carrier_root),
        media_relpaths=media_relpaths,
        derived_media_roots=tuple(Path(root) for root in derived_media_roots),
    ).validate()


#: A cell whose roster is this small or smaller is cheap enough to check EVERY
#: row's payload binding; above it, only the first and last row are checked
#: (see :func:`payload_binding_stage`). Chosen well above the largest
#: "-smoke4" population (4 rows) and well below the smallest full population
#: (400 rows), so the distinction tracks "smoke vs. full", not some incidental
#: roster size.
PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT = 16


@dataclass(frozen=True)
class PayloadBindingStageResult:
    """Receipt of one :func:`payload_binding_stage` run.

    ``bound`` is ``True`` only when every row named in ``rows_checked`` bound
    without refusal; ``failures`` carries the refusal message for each row
    that did not, keyed by sample id, and is empty exactly when ``bound`` is
    ``True``. ``rows_checked`` is a strict subset of the cell's roster
    (:data:`PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT`); ``rows_total`` is the
    roster's own size, so a receipt reader can tell "checked every row" from
    "checked the two endpoints" without recomputing the threshold."""

    dataset_fragment: str
    carrier_lock_key: str
    carrier_root: Path
    derived_media_roots: tuple[Path, ...]
    rows_checked: tuple[str, ...]
    rows_total: int
    bound: bool
    failures: Mapping[str, str]
    model_contacts: int = 0
    sockets_opened: int = 0

    def as_receipt(self) -> dict[str, object]:
        """JSON-safe view for a wire-check receipt document."""

        return {
            "dataset_fragment": self.dataset_fragment,
            "carrier_lock_key": self.carrier_lock_key,
            "carrier_root": str(self.carrier_root),
            "declared_derived_media_roots": [str(root) for root in self.derived_media_roots],
            "rows_checked": list(self.rows_checked),
            "rows_total": self.rows_total,
            "checked_every_row": self.rows_total <= len(self.rows_checked),
            "bound": self.bound,
            "failures": dict(self.failures),
            "model_contacts": self.model_contacts,
            "sockets_opened": self.sockets_opened,
        }


class _PayloadBindingStagePlan:
    """The one attribute :meth:`core.model.binding._PayloadBindingMixin.
    _enforce_payload_binding` reads off ``self._plan`` -- a real
    ``contracts.ExecutionPlan`` is not needed here, only the field the method
    actually compares against the payload's own ``carrier_lock_key``."""

    __slots__ = ("carrier_lock_key",)

    def __init__(self, carrier_lock_key: str) -> None:
        self.carrier_lock_key = carrier_lock_key


class _PayloadBindingStageProbe(_PayloadBindingMixin):
    """The production ``_enforce_payload_binding``, bound to a real binding
    context and nothing else.

    Deliberately NOT a :class:`~core.model.FrozenCoreAdapter`: constructing
    one opens a durable attempt against the shared data root and requires a
    live gate and transport, neither of which a model-free stage may
    construct. This mirrors
    ``scripts/checks/derived_media_confinement_check.py``'s own
    ``_BindingProbe`` -- the method under proof is the unmodified mixin
    function the adapter itself inherits, so the code path is the real one;
    only the attempt/transport lifecycle around it is absent, and no socket
    is ever touched."""

    def __init__(self, binding: PayloadBindingContext, carrier_lock_key: str) -> None:
        self._binding = binding
        self._plan = _PayloadBindingStagePlan(carrier_lock_key)
        self._slice_registry = None


def _payload_binding_stage_rows(samples: Sequence[object]) -> tuple[object, ...]:
    if not samples:
        raise FrozenCoreClientError("payload_binding_stage requires at least one sample")
    if len(samples) <= PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT:
        return tuple(samples)
    return (samples[0], samples[-1])


def payload_binding_stage(
    *,
    dataset_fragment: str,
    carrier_lock_key: str,
    samples: Sequence[object],
    data_root: Path,
    carrier_root: Path,
    derived_media_roots: Sequence[Path] = (),
    sample_rate_prober: Callable[[Path], int] = _probe_sample_rate_hz,
) -> PayloadBindingStageResult:
    """The shared payload-binding stage every wire check now runs between its
    request half and its seal half
    (``docs/readiness/2026-09-07-derived-media-confinement-v1.md`` section 5).

    Builds ONE real :class:`~core.base.PayloadBindingContext` through
    :func:`build_payload_binding` -- the identical construction
    ``core.driver.run_experiment``, ``core.driver.speech_native`` and
    ``core.flight.FlightRuntime`` themselves use, over the REAL carrier root
    (never a per-script ``carrier_root_resolver`` swap) plus this fragment's
    own declared derived media roots -- and drives the production
    ``core.model.binding._enforce_payload_binding`` against a synthetic
    payload carrying exactly the binding's own verified facts, for at least
    the first and last roster row (every row when there are
    :data:`PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT` or fewer).

    Zero sockets, zero servers, zero model contacts: no transport, gate or
    attempt store is ever constructed, here or in anything this function
    calls -- only ``PayloadBindingContext`` construction (pure, plus a
    per-sample audio-header probe) and one in-process method call per row
    checked. A row that does not bind is recorded in the result's
    ``failures``, never raised: the caller decides whether that refusal was
    the point (a synthetic undeclared-root cell) or a wire-readiness defect
    (a real cell)."""

    binding = build_payload_binding(
        carrier_lock_key=carrier_lock_key,
        samples=samples,
        data_root=data_root,
        carrier_root=carrier_root,
        derived_media_roots=derived_media_roots,
        sample_rate_prober=sample_rate_prober,
    )
    probe = _PayloadBindingStageProbe(binding, carrier_lock_key)
    checked = _payload_binding_stage_rows(samples)
    failures: dict[str, str] = {}
    for sample in checked:
        sample_id = sample.sample_id
        audio_seconds, sample_rate_hz = binding.sample_facts[sample_id]
        payload = {
            "carrier_lock_key": carrier_lock_key,
            "sample_id": sample_id,
            "speech_ref": f"{carrier_lock_key}/{sample_id}",
            "media_relpath": binding.media_relpaths[sample_id],
            "audio_seconds": audio_seconds,
            "sample_rate_hz": sample_rate_hz,
        }
        try:
            probe._enforce_payload_binding(payload, audio_seconds)
        except FrozenCoreError as error:
            failures[sample_id] = str(error)
    return PayloadBindingStageResult(
        dataset_fragment=dataset_fragment,
        carrier_lock_key=carrier_lock_key,
        carrier_root=Path(carrier_root),
        derived_media_roots=tuple(Path(root) for root in derived_media_roots),
        rows_checked=tuple(sample.sample_id for sample in checked),
        rows_total=len(samples),
        bound=not failures,
        failures=failures,
    )


@dataclass(frozen=True)
class MediaIdentityStageResult:
    """Receipt of one :func:`media_identity_stage` run.

    ``identity_closed`` is ``True`` only when BOTH halves passed: every id on
    the cell's roster is inside D1's media identity closure, and every row the
    stage actually loaded re-hashed to the identity D1 recorded for it.
    ``refusal`` carries the gate's OWN sentence when either half refused, and
    is ``None`` exactly when ``identity_closed`` is ``True``.

    ``d1_media_supplement`` / ``d1_media_supplement_sha256`` are the values the
    gate was CONSTRUCTED with -- i.e. what ``core.config.
    d1_media_supplement_relpath`` read out of the composed config, which is the
    exact seam the 2026-09-09 defect hid in: a fragment can declare a
    supplement under a carrier-prefixed key, satisfy payload confinement, and
    still hand the gate ``None`` here.
    """

    dataset_fragment: str
    carrier_lock_key: str
    d1_media_supplement: str | None
    d1_media_supplement_sha256: str | None
    closure_ids: int
    roster_ids_checked: int
    rows_verified: tuple[str, ...]
    identity_closed: bool
    refusal: str | None
    model_contacts: int = 0
    sockets_opened: int = 0

    def as_receipt(self) -> dict[str, object]:
        """JSON-safe view for a wire-check receipt document."""

        return {
            "dataset_fragment": self.dataset_fragment,
            "carrier_lock_key": self.carrier_lock_key,
            "d1_media_supplement": self.d1_media_supplement,
            "d1_media_supplement_sha256": self.d1_media_supplement_sha256,
            "closure_ids": self.closure_ids,
            "roster_ids_checked": self.roster_ids_checked,
            "rows_verified": list(self.rows_verified),
            "identity_closed": self.identity_closed,
            "refusal": self.refusal,
            "model_contacts": self.model_contacts,
            "sockets_opened": self.sockets_opened,
        }


def media_identity_stage(
    *,
    dataset_fragment: str,
    carrier_lock_key: str,
    values: Mapping[str, object],
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    roster_sample_ids: Sequence[str],
    samples: Sequence[object],
) -> MediaIdentityStageResult:
    """The shared MEDIA-IDENTITY stage every wire check now runs beside
    :func:`payload_binding_stage`: a cell is wire-ready only if it BINDS **and**
    is IDENTITY-CLOSED.

    THE THIRD BLIND SPOT (2026-09-09, ``docs/readiness/
    2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md``). Payload
    confinement and media identity are two different rails reading two
    different config keys, and the wire checks proved only the first. Six
    Audio2Tool derived-media fragments declared their D1 supplement under the
    carrier-prefixed key ``core.base.declared_derived_media_roots`` reads and
    NOT under the plain key ``core.flight.FlightRuntime.preflight`` builds the
    identity gate from, so confinement passed, the wire checks were green, and
    the first real request refused every roster id as outside D1's closure.

    This function closes that gap by constructing the REAL
    ``contracts.FrozenCoreGate`` exactly as ``FlightRuntime.preflight``
    constructs it -- same ``for_study_repo`` call, same four config-derived
    keyword arguments (``runtime_receipt_relpath``, ``expected_model_lock_key``,
    ``model_root`` and the D1 media supplement pair) off the same composed
    ``values`` -- and then running BOTH halves of the identity rail:

    * ``assert_media_identity_closure`` over EVERY id in ``roster_sample_ids``
      (membership only; no media file is opened, so a 400- or 1,000-row roster
      costs nothing), and
    * the production ``verify_media_identity`` over ``samples`` -- the same
      rows :func:`payload_binding_stage` loads -- which re-measures each media
      file on disk against D1's recorded size and SHA-256.

    Zero sockets, zero servers, zero model contacts: ``assert_model_touch_
    allowed`` is never called, no attempt is opened and no transport is
    constructed. A refusal is RETURNED, never raised, with the gate's own
    sentence, so the caller decides whether it was the point (a synthetic
    prefixed-only cell) or a wire-readiness defect (a real cell).
    """

    from ..contracts import (  # noqa: PLC0415 (import cost, not a cycle)
        FrozenCoreGate,
        GateClosed,
    )
    from ..core.config import (  # noqa: PLC0415
        ConfigError,
        d1_media_supplement_relpath,
        d1_media_supplement_sha256,
        model_lock_key,
        model_materialization_root,
        runtime_receipt_relpath,
    )

    try:
        supplement_relpath = d1_media_supplement_relpath(values)
        supplement_sha256 = d1_media_supplement_sha256(values)
    except ConfigError as error:
        # ``core.config.assert_d1_media_supplement_spellings_agree`` refuses a
        # fragment that declares its supplement ONLY under a carrier-prefixed
        # key -- the 2026-09-09 defect, now unrepresentable. A wire check
        # REPORTS that refusal as "not identity-closed" rather than exploding,
        # so one bad cell never hides the state of the others.
        return MediaIdentityStageResult(
            dataset_fragment=dataset_fragment,
            carrier_lock_key=carrier_lock_key,
            d1_media_supplement=None,
            d1_media_supplement_sha256=None,
            closure_ids=0,
            roster_ids_checked=len(roster_sample_ids),
            rows_verified=(),
            identity_closed=False,
            refusal=str(error),
        )
    configured_model_root = model_materialization_root(values)
    gate = FrozenCoreGate.for_study_repo(
        Path(repo_root),
        Path(data_root),
        Path(runtime_root),
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
        model_root=(
            Path(configured_model_root) if configured_model_root is not None else None
        ),
        d1_media_supplement_relpath=supplement_relpath,
        d1_media_supplement_sha256=supplement_sha256,
    )
    roster = [str(sample_id) for sample_id in roster_sample_ids]
    # ``sample.audio_ref.path`` is the same per-sample media relpath
    # :func:`build_payload_binding` records in
    # ``PayloadBindingContext.media_relpaths`` -- i.e. exactly the value the
    # production gate is handed at model-touch time.
    media_facts = {
        sample.sample_id: (sample.audio_ref.path, float(sample.audio_seconds))
        for sample in samples
    }
    refusal: str | None = None
    closure_ids = 0
    try:
        closure_ids = len(gate.media_identity_closure_ids(carrier_lock_key))
        gate.assert_media_identity_closure(carrier_lock_key, roster)
        if media_facts:
            gate.verify_media_identity(carrier_lock_key, media_facts)
    except GateClosed as error:
        refusal = str(error)
    return MediaIdentityStageResult(
        dataset_fragment=dataset_fragment,
        carrier_lock_key=carrier_lock_key,
        d1_media_supplement=supplement_relpath,
        d1_media_supplement_sha256=supplement_sha256,
        closure_ids=closure_ids,
        roster_ids_checked=len(roster),
        rows_verified=tuple(sorted(media_facts)),
        identity_closed=refusal is None,
        refusal=refusal,
    )


def build_slice_registry(
    *, data_root: Path, run_id: str, samples: Sequence[object]
) -> SliceRegistry:
    """A ready-to-register :class:`~core.model.SliceRegistry` for ``samples``
    -- the same ``parent_facts`` shape (``sample_id -> (media_relpath,
    audio_seconds)``) ``core.driver.run_experiment`` builds for its own
    ``SliceRegistry``, from rails ``TaskSample`` objects instead of
    ``core.base.SampleRef``. Only useful to a caller that intends to
    :meth:`FrozenCoreClient.register_slice` a runtime-derived variant (e.g. a
    silence-swap control) BEFORE any request names it; a flight that never
    needs one can omit this entirely (``FrozenCoreClient``'s own
    ``slice_registry`` parameter defaults to ``None``)."""

    parent_facts = {
        sample.sample_id: (sample.audio_ref.path, float(sample.audio_seconds))
        for sample in samples
    }
    return SliceRegistry(
        data_root=Path(data_root), run_id=run_id, parent_facts=parent_facts
    )


def _iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


@dataclass(frozen=True)
class RequestTiming:
    """One :meth:`FrozenCoreClient.complete` call's timing -- "record
    per-request timing" (bridge mission instruction). Reuses
    ``core.model.CoreResponse.latency_seconds`` (the adapter's own
    transport-call measurement) rather than re-measuring independently, so
    the two can never drift; ``started_at`` is this client's own wall-clock
    stamp of when the request was handed to the adapter."""

    request_id: str
    sample_id: str
    started_at: str
    latency_seconds: float
    # ``None`` for a non-native client; otherwise the exact selected schemas
    # on this contact. The close summary separately retains the immutable
    # constructor superset hash.
    tool_schemas_sha256: str | None = None
    # ``None`` distinguishes a non-native request from a native request whose
    # explicit final scope is empty.
    tool_names: tuple[str, ...] | None = None
    # 2026-09-04: the adapter's own per-request identity hashes, carried
    # through instead of discarded. core.bundle.verify_bundle REQUIRES every
    # outputs row to carry request_sha256/response_sha256/
    # response_text_sha256 (core.bundle.outputs._REQUIRED_OUTPUTS_FIELDS),
    # and this client -- which returns only response.text -- was the only
    # place they existed on the rails path, so a bundle sealed from a rails
    # flight could never verify. Defaulted to None so every pre-existing
    # construction site is untouched.
    request_sha256: str | None = None
    response_sha256: str | None = None
    response_text_sha256: str | None = None
    # How this response actually ARRIVED (2026-09-04). The transport
    # canonicalizes native tool calls into the same JSON-array text a
    # free-text arm produces, so a sealed row cannot be read back to tell
    # the two apart. ``None`` = the response carried no tool_calls key, i.e.
    # the model answered as text; an int = how many native tool calls came
    # back. Provenance only: it changes no audited payload, no outputs row
    # and no trace record.
    native_tool_calls: int | None = None
    # Internal delivery custody. Legacy serialized timing bytes stay unchanged.
    agent_contact_id: str | None = None
    terminal_saturated: bool = False

    def as_json(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "sample_id": self.sample_id,
            "started_at": self.started_at,
            "latency_seconds": self.latency_seconds,
            "tool_schemas_sha256": self.tool_schemas_sha256,
            "tool_names": None if self.tool_names is None else list(self.tool_names),
            "request_sha256": self.request_sha256,
            "response_sha256": self.response_sha256,
            "response_text_sha256": self.response_text_sha256,
            "native_tool_calls": self.native_tool_calls,
        }


def _parse_rails_messages(
    messages: Sequence[Mapping[str, object]],
    *,
    text_only: bool = False,
) -> tuple[str, str | None, list[str]]:
    """Extract ``(task_instruction, media_relpath, supply_texts)`` from a
    rails ``TaskAdapter.assemble_prompt`` output -- exactly the two-message
    ``[system, user]`` shape both ``SlurpAdapter`` and ``Audio2ToolAdapter``
    build (module docstring). Fail-closed on anything else: this bridge
    speaks exactly the shape those adapters produce, not an arbitrary chat
    transcript.

    ``text_only`` (default ``False``, EVERY pre-2026-08-19 caller): the
    AUDIO invariant -- the user message must carry EXACTLY one
    ``input_audio`` content part, never zero, never two -- is enforced
    exactly as before; the returned ``media_relpath`` is never ``None``.

    ``text_only=True`` (opt-in, :meth:`FrozenCoreClient.complete`'s own
    ``text_only_sample_id`` parameter -- P-KEY machinery, 2026-08-19): the
    INVERSE invariant is enforced instead -- the user message must carry
    ZERO ``input_audio`` content parts (a registered TEXT-ONLY arm, e.g.
    P-KEY's TXT-NOSUP/TXT-SUP, is audio-free BY CONSTRUCTION --
    ``rails.probes.pkey_flight.assemble_txt_messages``'s own module
    docstring: "TXT arms are audio-free by construction ... never appends
    an input_audio content part"). The returned ``media_relpath`` is always
    ``None`` in this mode; the caller (:meth:`FrozenCoreClient.complete`)
    resolves sample identity from its own ``text_only_sample_id`` argument
    instead, since a text-only ``messages`` shape carries no
    ``media_relpath`` a reverse index could look up."""

    if len(messages) != 2:
        raise FrozenCoreClientError(
            f"FrozenCoreClient expects exactly 2 messages (system, user), got {len(messages)}"
        )
    system_message, user_message = messages
    if (
        not isinstance(system_message, Mapping)
        or system_message.get("role") != "system"
    ):
        raise FrozenCoreClientError("messages[0] must be a mapping with role 'system'")
    task_instruction = system_message.get("content")
    if not isinstance(task_instruction, str) or not task_instruction:
        raise FrozenCoreClientError("system message content must be a non-empty string")
    if not isinstance(user_message, Mapping) or user_message.get("role") != "user":
        raise FrozenCoreClientError("messages[1] must be a mapping with role 'user'")
    content = user_message.get("content")
    if not isinstance(content, Sequence) or isinstance(content, (str, bytes)):
        raise FrozenCoreClientError(
            "user message content must be a list of content parts"
        )
    media_relpath: str | None = None
    supply_texts: list[str] = []
    for index, part in enumerate(content):
        if not isinstance(part, Mapping) or "type" not in part:
            raise FrozenCoreClientError(
                f"user content[{index}] must be a mapping with a 'type' key, got {part!r}"
            )
        part_type = part["type"]
        if part_type == "input_audio":
            if text_only:
                raise FrozenCoreClientError(
                    "text-only request must not carry an input_audio content part -- a registered "
                    "TEXT-ONLY arm is audio-free by construction (rails.probes.pkey_flight."
                    "assemble_txt_messages's own invariant)"
                )
            if media_relpath is not None:
                raise FrozenCoreClientError(
                    "user content carries more than one input_audio part"
                )
            candidate = part.get("media_relpath")
            if not isinstance(candidate, str) or not candidate:
                raise FrozenCoreClientError(
                    "input_audio content part must carry a non-empty media_relpath"
                )
            media_relpath = candidate
        elif part_type == "text":
            text = part.get("text")
            if not isinstance(text, str) or not text:
                raise FrozenCoreClientError(
                    "text content part must carry non-empty text"
                )
            supply_texts.append(text)
        else:
            raise FrozenCoreClientError(f"unsupported content part type {part_type!r}")
    if not text_only and media_relpath is None:
        raise FrozenCoreClientError(
            "user message must carry exactly one input_audio content part"
        )
    return task_instruction, media_relpath, supply_texts


def _typed_supply_part(part: Mapping[str, object]) -> dict[str, str | None]:
    """Preserve registered evidence identity across speech input forms."""
    text = part.get("text")
    if not isinstance(text, str) or not text:
        raise FrozenCoreClientError(
            "text content part must carry non-empty text"
        )
    evidence_id = part.get("evidence_id")
    if evidence_id is not None and (
        not isinstance(evidence_id, str) or not evidence_id
    ):
        raise FrozenCoreClientError(
            "text content part evidence_id must be a non-empty string or absent"
        )
    source_uri = part.get("source_uri")
    if source_uri is not None and (
        not isinstance(source_uri, str) or not source_uri
    ):
        raise FrozenCoreClientError(
            "text content part source_uri must be a non-empty string or absent"
        )
    knowledge_role = part.get("knowledge_role")
    if knowledge_role is not None and knowledge_role not in {"key", "value"}:
        raise FrozenCoreClientError(
            "text content part knowledge_role must be 'key', 'value', or absent"
        )
    return {"text": text, "evidence_id": evidence_id, "source_uri": source_uri,
            "knowledge_role": knowledge_role}


#: Item E21 (the knowledge INDEX, not the Earnings-21 carrier), 2026-09-19:
#: the ``source_uri`` scheme a pointer or expansion block carries
#: (``rails.knowledge_index.IndexAssembly.evidence_items``). A part whose
#: source is the released view gets its provenance from the VIEW rather
#: than from the rails message that rendered it; every other part keeps
#: exactly the ``rails-supply`` provenance it has always had, so an episode
#: that does not arm the key composes byte-identical provenance.
KNOWLEDGE_INDEX_SOURCE_SCHEME = "knowledge-index://"


def _supply_provenance(
    part: Mapping[str, object] | None, text: str, *, request_id: str, index: int,
) -> dict[str, str]:
    """One ``evidence_provenance`` row for one rendered supply part."""

    source_uri = None if part is None else part.get("source_uri")
    if isinstance(source_uri, str) and source_uri.startswith(
        KNOWLEDGE_INDEX_SOURCE_SCHEME
    ):
        return {
            "lock_key": "knowledge-index",
            "relpath": source_uri[len(KNOWLEDGE_INDEX_SOURCE_SCHEME):],
            "sha256": _content_sha256(text),
        }
    return {
        "lock_key": "rails-supply",
        "relpath": f"rails-message/{request_id}/{index}",
        "sha256": _content_sha256(text),
    }


def _parse_speech_feature_messages(
    messages: Sequence[Mapping[str, object]],
) -> tuple[str, list[dict[str, str | None]], list[dict[str, str]]]:
    """Parse the formal packet-reference content extension.

    Exactly one query packet is mandatory. Any additional packet is an
    explicitly marked key. Raw audio and caller-supplied arrays are refused;
    the descriptor vocabulary is the exact id/hash/role triple.
    """

    if len(messages) != 2:
        raise FrozenCoreClientError(
            f"FrozenCoreClient expects exactly 2 messages (system, user), got {len(messages)}"
        )
    system_message, user_message = messages
    if (
        not isinstance(system_message, Mapping)
        or system_message.get("role") != "system"
    ):
        raise FrozenCoreClientError("messages[0] must be a mapping with role 'system'")
    task_instruction = system_message.get("content")
    if not isinstance(task_instruction, str) or not task_instruction:
        raise FrozenCoreClientError("system message content must be a non-empty string")
    if not isinstance(user_message, Mapping) or user_message.get("role") != "user":
        raise FrozenCoreClientError("messages[1] must be a mapping with role 'user'")
    content = user_message.get("content")
    if not isinstance(content, Sequence) or isinstance(content, (str, bytes)):
        raise FrozenCoreClientError(
            "user message content must be a list of content parts"
        )
    supply_parts: list[dict[str, str | None]] = []
    descriptors: list[dict[str, str]] = []
    for index, part in enumerate(content):
        if not isinstance(part, Mapping) or "type" not in part:
            raise FrozenCoreClientError(
                f"user content[{index}] must be a mapping with a 'type' key"
            )
        part_type = part["type"]
        if part_type == "input_audio":
            raise FrozenCoreClientError(
                "speech-feature request must not carry input_audio; preprocessing must "
                "materialize every packet before inference"
            )
        if part_type == "text":
            supply_parts.append(_typed_supply_part(part))
            continue
        if part_type != "input_speech_features":
            raise FrozenCoreClientError(f"unsupported content part type {part_type!r}")
        speech_features = part.get("speech_features")
        required = {"packet_id", "sha256", "role"}
        if not isinstance(speech_features, Mapping) or set(speech_features) != required:
            raise FrozenCoreClientError(
                f"input_speech_features must carry exact keys {sorted(required)}"
            )
        if speech_features["role"] not in {"query", "key"}:
            raise FrozenCoreClientError("speech feature role must be 'query' or 'key'")
        if not all(
            isinstance(speech_features[field], str) and speech_features[field]
            for field in required
        ):
            raise FrozenCoreClientError(
                "speech feature descriptor values must be non-empty strings"
            )
        descriptors.append(dict(speech_features))
    if sum(part["role"] == "query" for part in descriptors) != 1:
        raise FrozenCoreClientError(
            "speech-feature request must carry exactly one query packet"
        )
    return task_instruction, supply_parts, descriptors


def _agent_history(
    *,
    agent_state: Sequence[Mapping[str, object]] | None,
    agent_contact_id: str | None,
    contact_instruction: str | None,
) -> list[dict[str, object]]:
    """Build the D2-visible ORG/CONTROL history for one Agent contact."""

    if agent_state is None and agent_contact_id is None and contact_instruction is None:
        return []
    if not isinstance(agent_state, Sequence) or isinstance(agent_state, (str, bytes)):
        raise FrozenCoreClientError(
            "agent_state must be a sequence of AgentStateArtifact documents"
        )
    if not isinstance(agent_contact_id, str) or not agent_contact_id:
        raise FrozenCoreClientError(
            "agent_contact_id must be a non-empty string for an Agent contact"
        )
    if not isinstance(contact_instruction, str) or not contact_instruction:
        raise FrozenCoreClientError(
            "contact_instruction must be a non-empty string for an Agent contact"
        )
    try:
        from .prepared_feedback import PreparedFeedbackStateArtifact

        artifacts = tuple(
            PreparedFeedbackStateArtifact.from_json(document)
            if isinstance(document, Mapping)
            and "prepared_feedback_state_version" in document
            else AgentStateArtifact.from_json(document)
            for document in agent_state
        )
    except (KeyError, RailsError, TypeError, ValueError) as error:
        raise FrozenCoreClientError(
            f"malformed Agent state artifact: {error}"
        ) from error
    ids = [artifact.state_id for artifact in artifacts]
    if len(set(ids)) != len(ids):
        raise FrozenCoreClientError("agent_state contains duplicate state ids")
    history: list[dict[str, object]] = []
    for index, artifact in enumerate(artifacts, start=1):
        state = {
            "turn": index,
            "role": "agent_state",
            "state_id": artifact.state_id,
            "state_kind": artifact.state_kind,
            "content": artifact.content,
            "content_sha256": _content_sha256(artifact.content),
            "cited_value_ids": list(artifact.cited_value_ids),
        }
        if isinstance(artifact, PreparedFeedbackStateArtifact):
            state.update({
                "prepared_feedback_state_version": artifact.prepared_feedback_state_version,
                "prepared_artifact_sha256": artifact.prepared_artifact_sha256,
                "source_feedback_sha256": artifact.source_feedback_sha256,
                "construction_roster_sha256": artifact.construction_roster_sha256,
                "model_context_sha256": artifact.model_context_sha256,
            })
        else:
            state.update({
                "source_query_state_sha256": artifact.source_query_state_sha256,
                "source_response_sha256": artifact.source_response_sha256,
                "producer_policy_id": artifact.producer_policy_id,
            })
        history.append(state)
    history.append(
        {
            "turn": len(history) + 1,
            "role": "control",
            "contact_id": agent_contact_id,
            "content": contact_instruction,
            "content_sha256": _content_sha256(contact_instruction),
        }
    )
    return history


class FrozenCoreClient:
    """The REAL ``CoreClient``: delegates every :meth:`complete` call to a
    ``core.model.FrozenCoreAdapter`` it owns (module docstring).

    Construction mirrors what ``core.driver.run_experiment``/
    ``core.driver.smoke.run_smoke`` already do for the non-rails path --
    build a ``PayloadBindingContext`` (:func:`build_payload_binding`), open a
    ``TraceSink`` under ``run_dir``, then construct exactly ONE
    ``FrozenCoreAdapter`` bound to ``plan``/``gate``/``transport``/``arm`` for
    this client's whole life. Every model-touching argument (``gate``,
    ``transport``) is accepted, never constructed here: building a REAL
    ``contracts.FrozenCoreGate``/spawning a REAL session is the flying
    mission's job (module docstring), not this bridge's.

    Enforcement carried through, explicitly, at construction (defense in
    depth -- ``FrozenCoreAdapter``'s own gate check is the authoritative one;
    this mirrors ``rails.runner.run_rails_experiment``'s own "explicitly, so
    the enforcement point is named directly in this function's own body"
    idiom for ``assert_execution_scope``):

    - ``plan.validate()`` then ``assert_execution_scope(plan.execution_profile)``.
    - The E0' flight lock (``core.flight_lock.read_flight_lock`` -- best-effort/
      advisory by that module's own design, never fail-closed here either) is
      read once and carried through ``flight_lock``/``close()``, exactly as
      advisory as the module that produces it.
    """

    def __init__(
        self,
        *,
        plan: ExecutionPlan,
        gate: object,
        transport: Callable[[bytes], bytes],
        run_dir: Path,
        binding: PayloadBindingContext,
        arm: str = DEFAULT_RAILS_ARM,
        slice_registry: SliceRegistry | None = None,
        request_id_prefix: str = "rails",
        now: Callable[[], float] = time.time,
        speech_feature_root: Path | None = None,
        speech_packet_bindings: Mapping[str, Mapping[str, str]] | None = None,
        validated_packet_set: ValidatedSpeechPacketSet | None = None,
        execution_units: ExecutionUnitRoster | None = None,
        tool_schemas: Sequence[Mapping[str, object]] | None = None,
        construction_targets: Sequence[Mapping[str, object]] | None = None,
    ) -> None:
        plan.validate()
        assert_execution_scope(plan.execution_profile)
        if arm not in ARM_VISIBLE_FIELDS:
            raise FrozenCoreClientError(
                f"unknown D2 arm {arm!r}; D2-frozen arms are {sorted(ARM_VISIBLE_FIELDS)}"
            )
        arm_fields = frozenset(ARM_VISIBLE_FIELDS[arm])
        if arm_fields not in _ACCEPTED_ARM_FIELD_SETS:
            raise FrozenCoreClientError(
                f"FrozenCoreClient only builds payloads for the field set "
                f"{sorted(_SUPPORTED_ARM_FIELDS)} (D2 arm {DEFAULT_RAILS_ARM!r}), that "
                f"field set plus {_NATIVE_TOOLS_FIELD!r}, the speech-feature-query field "
                f"set, or that field set plus {_NATIVE_TOOLS_FIELD!r}; arm {arm!r} "
                f"declares a different field set {sorted(ARM_VISIBLE_FIELDS[arm])}"
            )
        self._is_speech_feature_arm = arm_fields in _SPEECH_FEATURE_FAMILY_ARM_FIELDS
        self._is_native_tools_arm = _NATIVE_TOOLS_FIELD in arm_fields
        self._is_prepared_text_arm = arm_fields == _PREPARED_TEXT_ARM_FIELDS
        self._is_construction_proposer_arm = _CONSTRUCTION_TARGETS_FIELD in arm_fields
        # Read off the arm's OWN declared fields, never a hardcoded arm-name
        # list -- the same discipline core.policies.FixedPolicy.run_sample
        # documents for its own evidence branch.
        self._carries_evidence = bool(_EVIDENCE_FIELDS & arm_fields)
        # Construction targets are bound ONCE, here, BEFORE the adapter opens
        # its durable attempt: the gold this arm may show is a property of the
        # client's whole life, never a per-request argument a caller could
        # widen mid-run, and a misconfigured proposer client must not burn an
        # attempt id before it is refused.
        self._construction_targets: tuple[dict[str, str], ...] | None = None
        if self._is_construction_proposer_arm:
            self._construction_targets = _validate_construction_targets(
                construction_targets
            )
        elif construction_targets is not None:
            raise FrozenCoreClientError(
                f"arm {arm!r} is not a construction-proposer arm; construction_targets "
                "must be omitted"
            )
        if not isinstance(request_id_prefix, str) or not request_id_prefix:
            raise FrozenCoreClientError("request_id_prefix must be a non-empty string")
        self._plan = plan
        self._arm = arm
        self._binding = binding
        self._request_id_prefix = request_id_prefix
        self._now = now
        # Advisory read (module docstring): never fail-closed, threaded
        # through unchanged like rails.runner.run_rails_experiment's own
        # RunSummary.flight_lock.
        self._flight_lock = read_flight_lock(Path(binding.data_root))
        self._sink = TraceSink(Path(run_dir), plan.run_id)
        self._dispatching_sink = DispatchingSink(self._sink)
        self._slice_registry = slice_registry
        self._adapter = FrozenCoreAdapter(
            gate=gate,
            plan=plan,
            arm=arm,
            transport=transport,
            sink=self._dispatching_sink,
            binding=binding,
            slice_registry=slice_registry,
        )
        self._reverse_media_index: dict[str, str] = {
            relpath: sample_id for sample_id, relpath in binding.media_relpaths.items()
        }
        # A registered slice's own (audio_seconds, sample_rate_hz) -- NOT
        # necessarily equal to its parent sample's (a silence-swap control is
        # duration-MATCHED by convention, but this client must stay correct
        # for a slice of any other duration too): populated only by
        # register_slice, consulted by complete() before falling back to
        # self._binding.sample_facts.
        self._slice_facts: dict[str, tuple[float, int]] = {}
        self._request_counter = 0
        self._prepared_requests: dict[object, bytes] = {}
        self._last_attempted_request_id: str | None = None
        self._timings: list[RequestTiming] = []
        self._state_lock = threading.Lock()
        self._closed = False
        self._speech_feature_root: Path | None = None
        self._speech_packet_bindings: dict[str, dict[str, str]] = {}
        self._speech_decoder_gguf_sha256: str | None = None
        self._speech_n_embd: int | None = None
        self._execution_units_by_scope: dict[str, ExecutionUnit] = {}
        if self._is_speech_feature_arm and execution_units is not None:
            if speech_packet_bindings is not None or validated_packet_set is not None:
                raise FrozenCoreClientError(
                    "execution-unit speech packets replace parent speech_packet_bindings"
                )
            if speech_feature_root is None or slice_registry is None:
                raise FrozenCoreClientError(
                    "feature execution units require speech_feature_root and slice_registry"
                )
            if not isinstance(execution_units, ExecutionUnitRoster):
                raise FrozenCoreClientError(
                    "execution_units must be an ExecutionUnitRoster"
                )
            try:
                execution_units.validate(
                    parent_sample_ids=tuple(binding.allowed_sample_ids),
                    max_contacts=1,
                )
            except RailsError as error:
                raise FrozenCoreClientError(str(error)) from error
            descriptors = []
            for unit in execution_units.units:
                try:
                    descriptor = unit.query_descriptor("speech_features")
                except RailsError as error:
                    raise FrozenCoreClientError(str(error)) from error
                descriptors.append(
                    {"packet_id": descriptor["packet_id"], "sha256": descriptor["sha256"]}
                )
                record = slice_registry.lookup(
                    unit.parent_sample_id, unit.slice_record.media_relpath
                )
                if record != unit.slice_record:
                    raise FrozenCoreClientError(
                        "execution unit slice differs from the registered source"
                    )
                try:
                    slice_registry.verify_slice_bytes(record)
                except FrozenCoreError as error:
                    raise FrozenCoreClientError(str(error)) from error
            try:
                root = Path(speech_feature_root).resolve(strict=True)
                packets = load_speech_feature_packets(root, tuple(descriptors), workers=8)
            except (OSError, FrozenCoreError) as error:
                raise FrozenCoreClientError(
                    "cannot validate execution-unit speech packets: " + str(error)
                ) from error
            for unit, packet in zip(execution_units.units, packets, strict=True):
                if packet.audio_sha256 != unit.slice_record.sha256:
                    raise FrozenCoreClientError(
                        "execution-unit packet does not match its source slice"
                    )
                scope = execution_unit_scope(unit.request_key)
                if scope in self._execution_units_by_scope:
                    raise FrozenCoreClientError("execution unit scope collision")
                self._execution_units_by_scope[scope] = unit
                self.admit_registered_slice(unit.slice_record)
            decoders = {packet.decoder_gguf_sha256 for packet in packets}
            dimensions = {chunk.n_embd for packet in packets for chunk in packet.chunks}
            if len(decoders) != 1 or len(dimensions) != 1:
                raise FrozenCoreClientError(
                    "execution-unit packets must share one decoder identity and dimension"
                )
            self._speech_feature_root = root
            self._speech_decoder_gguf_sha256 = next(iter(decoders))
            self._speech_n_embd = next(iter(dimensions))
        elif self._is_speech_feature_arm and validated_packet_set is not None:
            if (
                speech_feature_root is None
                or speech_packet_bindings is None
                or not isinstance(validated_packet_set, ValidatedSpeechPacketSet)
                or not validated_packet_set.matches(
                    speech_feature_root, speech_packet_bindings, binding
                )
            ):
                raise FrozenCoreClientError(
                    "validated speech packet set does not match this client binding"
                )
            self._speech_feature_root = validated_packet_set.feature_root
            self._speech_packet_bindings = {
                sample_id: {"packet_id": packet_id, "sha256": sha256}
                for sample_id, packet_id, sha256 in validated_packet_set.bindings
            }
            self._speech_decoder_gguf_sha256 = validated_packet_set.decoder_gguf_sha256
            self._speech_n_embd = validated_packet_set.n_embd
        elif self._is_speech_feature_arm:
            if speech_feature_root is None or speech_packet_bindings is None:
                raise FrozenCoreClientError(
                    "speech-feature-query requires speech_feature_root and complete "
                    "speech_packet_bindings"
                )
            prepared = validate_speech_packet_set(
                speech_feature_root, speech_packet_bindings, binding, workers=8
            )
            self._speech_feature_root = prepared.feature_root
            self._speech_packet_bindings = {
                sample_id: {"packet_id": packet_id, "sha256": sha256}
                for sample_id, packet_id, sha256 in prepared.bindings
            }
            self._speech_decoder_gguf_sha256 = prepared.decoder_gguf_sha256
            self._speech_n_embd = prepared.n_embd
        elif (
            speech_feature_root is not None
            or speech_packet_bindings is not None
            or validated_packet_set is not None
            or execution_units is not None
        ):
            raise FrozenCoreClientError(
                "speech feature bindings and execution units are only valid for the speech-feature-query arm"
            )
        self._tool_schemas: tuple[dict[str, object], ...] | None = None
        self._tool_schemas_sha256: str | None = None
        self._tool_schemas_by_name: dict[str, dict[str, object]] = {}
        if self._is_native_tools_arm and tool_free_native_schemas(tool_schemas):
            # Item E23b (2026-09-20, repair form 0-B of owner decision 55): a
            # native-tools arm whose baseline declares NO phase_tools hands the
            # client an EMPTY tuple on purpose -- no role holds tool authority,
            # so every request goes out with tool_choice none and no tools
            # array. The invariant below (a non-empty schema sequence) stays
            # for every arm that names a tool.
            self._tool_schemas = ()
            self._tool_schemas_sha256 = _tool_schemas_sha256(())
            self._tool_schemas_by_name = {}
        elif self._is_native_tools_arm:
            self._tool_schemas = _validate_tool_schemas(tool_schemas)
            self._tool_schemas_sha256 = _tool_schemas_sha256(self._tool_schemas)
            self._tool_schemas_by_name = {
                schema["function"]["name"]: schema for schema in self._tool_schemas
            }
        elif tool_schemas is not None:
            raise FrozenCoreClientError(
                f"arm {arm!r} is not a native tool-calling arm; tool_schemas must be omitted"
            )

    @property
    def arm(self) -> str:
        return self._arm

    @property
    def flight_lock(self) -> Mapping[str, object] | None:
        return self._flight_lock

    @property
    def timings(self) -> tuple[RequestTiming, ...]:
        with self._state_lock:
            return tuple(self._timings)

    @property
    def last_attempted_request_id(self) -> str | None:
        """The ID handed to transport most recently, if any.

        It identifies an attempted request only; sealed cost remains the
        authority for charged model contacts.
        """
        with self._state_lock:
            return self._last_attempted_request_id

    def flush_trace_buffer(self, buffer: TraceBuffer) -> None:
        """Flush one completed parallel task into the owned trace sink.

        The caller chooses flush order after worker completion. Adapter
        emissions are routed into the task-local buffer by
        :class:`DispatchingSink`, so no worker writes the shared file.
        """

        if not isinstance(buffer, TraceBuffer) or buffer.run_id != self._plan.run_id:
            raise FrozenCoreClientError(
                "trace buffer must be a TraceBuffer bound to this client's run_id"
            )
        with self._state_lock:
            if self._closed:
                raise FrozenCoreClientError(
                    "trace buffer cannot be flushed after close()"
                )
            buffer.flush_into(self._sink)

    def registered_slice(self, sample_id: str, media_relpath: str):
        """Return an immutable existing slice after revalidating its bytes."""
        if self._slice_registry is None:
            return None
        record = self._slice_registry.lookup(sample_id, media_relpath)
        if record is not None:
            self._slice_registry.verify_slice_bytes(record)
        return record

    def admit_registered_slice(self, record: SliceRecord) -> None:
        """Bind an already registered, byte-verified slice to this client."""
        if self.registered_slice(record.sample_id, record.media_relpath) != record:
            raise FrozenCoreClientError("slice differs from its registered source")
        self._index_registered_slice(record)

    def _index_registered_slice(self, record: SliceRecord) -> None:
        existing_parent = self._reverse_media_index.get(record.media_relpath)
        if existing_parent not in (None, record.sample_id):
            raise FrozenCoreClientError("slice path is already bound to another parent")
        self._reverse_media_index[record.media_relpath] = record.sample_id
        self._slice_facts[record.media_relpath] = (
            record.audio_seconds, record.sample_rate_hz,
        )

    def register_slice(self, record: SliceRecord) -> None:
        """Register a runtime-derived media variant (e.g. a silence-swap
        control) BEFORE any :meth:`complete` call names it. Delegates to the
        ``slice_registry`` given at construction (the existing I3/I4
        derivation-chain rail, ``core.model.slices`` -- this method adds no
        new admission logic of its own) and extends this client's own
        ``media_relpath -> sample_id`` reverse index so a slice request
        resolves exactly the way an ordinary whole-file one does."""

        if self._slice_registry is None:
            raise FrozenCoreClientError(
                "register_slice requires a slice_registry to have been given at construction"
            )
        self._slice_registry.register(record)
        self._index_registered_slice(record)

    def _selected_construction_targets(
        self, construction_target_ids: Sequence[str] | None
    ) -> list[dict[str, str]]:
        """The ``construction_targets`` entries ONE request carries: either
        every target this client was constructed with (``None``, the
        historical behaviour, byte-identical), or the ORDERED SUBSET the
        caller names.

        A subset can only ever NARROW what the core sees. The bound tuple is
        still the whole of the gold this client may ever show -- it is
        validated once, at construction, from a committed roster (see
        ``_validate_construction_targets``) -- and a request naming an id
        that tuple does not carry is refused rather than resolved. So the
        module's invariant is intact: "the gold this arm may show is a
        property of the client's whole life, never a per-request argument a
        caller could WIDEN mid-run".

        ORDER is the caller's, deliberately. The EVO-A1 exemplar draw is a
        seeded ORDERED sample (preregistration section 4: the seed "in every
        case fixes their ORDER"), and the rendered proposer instruction
        preserves that order within a tool's group, so the audited payload
        must record the same order the prompt showed -- not the order the
        client happened to bind.
        """

        bound = self._construction_targets or ()
        if construction_target_ids is None:
            return [dict(entry) for entry in bound]
        if isinstance(construction_target_ids, (str, bytes)):
            raise FrozenCoreClientError(
                "construction_target_ids must be a sequence of bound sample ids"
            )
        wanted = tuple(construction_target_ids)
        if not wanted:
            raise FrozenCoreClientError(
                "construction_target_ids must name at least one bound target; an "
                "empty target list would silently degrade the proposer contact into "
                "an ungrounded free-writing request"
            )
        by_id = {entry["sample_id"]: entry for entry in bound}
        selected: list[dict[str, str]] = []
        seen: set[str] = set()
        for sample_id in wanted:
            if not isinstance(sample_id, str) or not sample_id:
                raise FrozenCoreClientError(
                    "every construction_target_ids entry must be a non-empty string"
                )
            if sample_id in seen:
                raise FrozenCoreClientError(
                    f"construction_target_ids repeats {sample_id!r}"
                )
            seen.add(sample_id)
            entry = by_id.get(sample_id)
            if entry is None:
                raise FrozenCoreClientError(
                    f"construction target {sample_id!r} was not bound at construction; "
                    "a request can narrow the bound targets, never widen them"
                )
            selected.append(dict(entry))
        return selected

    def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        decoding_params: Mapping[str, object] | None = None,
        text_only_sample_id: str | None = None,
        speech_feature_sample_id: str | None = None,
        raw_agent_sample_id: str | None = None,
        key_representation_id: str | None = None,
        matcher_policy_id: str | None = None,
        agent_state: Sequence[Mapping[str, object]] | None = None,
        agent_contact_id: str | None = None,
        contact_instruction: str | None = None,
        construction_target_ids: Sequence[str] | None = None,
        tool_names: Sequence[str] | None = None,
    ) -> str:
        """Construct and send through the same audited adapter as prepared calls."""
        payload = self._build_request_payload(
            messages, decoding_params=decoding_params,
            text_only_sample_id=text_only_sample_id,
            speech_feature_sample_id=speech_feature_sample_id,
            raw_agent_sample_id=raw_agent_sample_id,
            key_representation_id=key_representation_id,
            matcher_policy_id=matcher_policy_id, agent_state=agent_state,
            agent_contact_id=agent_contact_id, contact_instruction=contact_instruction,
            construction_target_ids=construction_target_ids,
            tool_names=tool_names,
        )
        return self._complete_payload(payload)

    def complete_with_metadata(
        self, messages: Sequence[Mapping[str, object]], **kwargs: object,
    ) -> CoreCompletion:
        """Send once through the ordinary builder and preserve response metadata."""
        if "prepare_only" in kwargs:
            raise FrozenCoreClientError("prepare_only is internal")
        payload = self._build_request_payload(messages, **kwargs)
        return self._completion_metadata(payload, self._dispatch_payload(payload))

    def prepare_request(
        self, messages: Sequence[Mapping[str, object]], **kwargs: object,
    ) -> PreparedCoreRequest:
        """Build actual immutable payload bytes without allocating a request ID.

        This only validates and reads bound local material. It performs no
        tokenizer, adapter, gate, review or model contact. The owning client
        accepts the template at most once, including a failed send. Raw
        supplied-evidence templates with legacy request-derived IDs are
        refused. The explicit raw native arm preserves registered stable
        evidence IDs and binds the actual raw speech bytes.
        """
        if "prepare_only" in kwargs:
            raise FrozenCoreClientError("prepare_only is internal")
        payload = self._build_request_payload(messages, prepare_only=True, **kwargs)
        if (payload.get("supplied_evidence") and "speech_feature_parts" not in payload
                and self._arm != _RAW_NATIVE_ARM):
            # Legacy raw supply IDs enter the prompt and include the dispatch
            # request ID. They cannot be normalized away as mere trace routing.
            raise FrozenCoreClientError(
                "prepared raw supplied evidence is unsupported; use the ordinary client"
            )
        raw = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        token = object()
        with self._state_lock:
            if self._closed:
                raise FrozenCoreClientError("prepare_request() called after close()")
            self._prepared_requests[token] = raw
        return PreparedCoreRequest(raw, token)

    def complete_prepared(
        self, request: PreparedCoreRequest, *, id_slot: int | None = None,
    ) -> str:
        """Send the same one-use prepared payload and return historical text."""
        return self._complete_payload(
            self._consume_prepared_payload(request, id_slot=id_slot),
        )

    def complete_prepared_with_metadata(
        self, request: PreparedCoreRequest, *, id_slot: int | None = None,
    ) -> CoreCompletion:
        """Preserve native metadata while consuming the same prepared request."""
        payload = self._consume_prepared_payload(request, id_slot=id_slot)
        return self._completion_metadata(payload, self._dispatch_payload(payload))

    def _consume_prepared_payload(
        self, request: PreparedCoreRequest, *, id_slot: int | None,
    ) -> dict[str, object]:
        """Send an owned template once, changing only request routing and slot.

        Packet bytes are checked again at dispatch because they can change
        after full-roster preparation. Failed attempts cannot reuse a template.
        """
        if not isinstance(request, PreparedCoreRequest):
            raise FrozenCoreClientError("expected a prepared core request")
        if id_slot is not None and (
            isinstance(id_slot, bool) or not isinstance(id_slot, int) or id_slot < 0
        ):
            raise FrozenCoreClientError("id_slot must be a non-negative integer")
        with self._state_lock:
            if self._closed:
                raise FrozenCoreClientError("complete_prepared() called after close()")
            if self._prepared_requests.get(request.token) != request.payload_bytes:
                raise FrozenCoreClientError("prepared request is foreign, changed or consumed")
            del self._prepared_requests[request.token]
        payload = request.as_payload()
        if self._arm == _RAW_NATIVE_ARM:
            if payload["raw_speech_query"] != self._raw_speech_identity(
                payload["sample_id"], payload["media_relpath"]
            ):
                raise FrozenCoreClientError("raw query bytes changed after preparation")
        descriptors = payload.get("speech_feature_parts")
        if descriptors is not None:
            self._validate_feature_execution_unit_payload(payload)
            load_speech_feature_packets(
                self._speech_feature_root,
                tuple({"packet_id": d["packet_id"], "sha256": d["sha256"]}
                      for d in descriptors),
                workers=8,
                expected_decoder_gguf_sha256=self._speech_decoder_gguf_sha256,
                expected_n_embd=self._speech_n_embd,
            )
        with self._state_lock:
            self._request_counter += 1
            request_id = f"{self._request_id_prefix}-{self._request_counter:04d}"
        payload["request_id"] = request_id
        for index, source in enumerate(payload.get("evidence_provenance", [])):
            if source.get("lock_key") == "rails-supply":
                source["relpath"] = f"rails-message/{request_id}/{index}"
        if descriptors is None and self._arm != _RAW_NATIVE_ARM:
            for index, evidence in enumerate(payload.get("supplied_evidence", [])):
                evidence["evidence_id"] = f"{request_id}-supply-{index}"
        if id_slot is not None:
            payload["decoding_params"]["id_slot"] = id_slot
        return payload

    def _complete_payload(self, payload: Mapping[str, object]) -> str:
        return self._dispatch_payload(payload).text

    @staticmethod
    def _completion_metadata(
        payload: Mapping[str, object], response: CoreResponse,
    ) -> CoreCompletion:
        contacts = [
            item["contact_id"] for item in payload["history"]
            if item.get("role") == "control"
        ]
        schemas = payload.get("tool_schemas")
        tool_names = (
            tuple(schema["function"]["name"] for schema in schemas)
            if isinstance(schemas, list) else None
        )
        return CoreCompletion(
            text=response.text,
            request_id=payload["request_id"],
            sample_id=payload["sample_id"],
            agent_contact_id=contacts[-1] if contacts else None,
            request_sha256=response.request_sha256,
            response_sha256=response.response_sha256,
            response_text_sha256=response.response_text_sha256,
            tool_calls_json=json.dumps(
                response.tool_calls, ensure_ascii=False,
                sort_keys=True, separators=(",", ":"),
            ).encode("utf-8"),
            tool_names=tool_names,
            tool_schemas_sha256=(
                _tool_schemas_sha256(schemas) if isinstance(schemas, list) else None
            ),
            wire_response_bytes=response.wire_response_bytes,
        )

    def _dispatch_payload(self, payload: Mapping[str, object]) -> CoreResponse:
        """Keep metering, exposure, transport and timing on the shared adapter."""
        request_id = payload["request_id"]
        sample_id = payload["sample_id"]
        started_at = _iso(self._now())
        with self._state_lock:
            self._last_attempted_request_id = request_id
        response = self._adapter.request(payload)
        contacts = [item["contact_id"] for item in payload["history"]
                    if item.get("role") == "control"]
        agent_contact_id = contacts[-1] if contacts else None
        saturated = False
        if agent_contact_id is not None and agent_contact_id.startswith("unit-"):
            from ..core.delivery import terminal_response_saturated

            saturated = (
                response.finish_reason == "length"
                or terminal_response_saturated(
                    response.usage, payload.get("decoding_params", {}).get("max_tokens"),
                )
            )
        with self._state_lock:
            schemas = payload.get("tool_schemas")
            tool_names = (
                tuple(schema["function"]["name"] for schema in schemas)
                if isinstance(schemas, list) else None
            )
            self._timings.append(
                RequestTiming(
                    request_id=request_id,
                    sample_id=sample_id,
                    started_at=started_at,
                    latency_seconds=response.latency_seconds,
                    agent_contact_id=agent_contact_id,
                    terminal_saturated=saturated,
                    tool_schemas_sha256=(
                        _tool_schemas_sha256(schemas)
                        if isinstance(schemas, list) else None
                    ),
                    tool_names=tool_names,
                    request_sha256=response.request_sha256,
                    response_sha256=response.response_sha256,
                    response_text_sha256=response.response_text_sha256,
                    native_tool_calls=(
                        len(response.tool_calls)
                        if isinstance(response.tool_calls, list)
                        else None
                    ),
                )
            )
        return response

    def _feature_execution_unit(self, agent_contact_id: str | None):
        """Resolve the immutable feature unit from its scoped contact ID."""
        if not self._execution_units_by_scope:
            return None
        if not isinstance(agent_contact_id, str) or not agent_contact_id:
            raise FrozenCoreClientError(
                "feature execution-unit request requires a scoped agent_contact_id"
            )
        scope, separator, _contact = agent_contact_id.partition("/")
        unit = self._execution_units_by_scope.get(scope)
        if separator != "/" or unit is None:
            raise FrozenCoreClientError(
                "feature request contact is outside the execution unit roster"
            )
        return unit

    def _validate_feature_execution_unit_payload(
        self, payload: Mapping[str, object]
    ) -> None:
        """Recheck unit source custody when a prepared request is consumed."""
        if not self._execution_units_by_scope:
            return
        controls = [
            item.get("contact_id")
            for item in payload.get("history", ())
            if isinstance(item, Mapping) and item.get("role") == "control"
        ]
        unit = self._feature_execution_unit(controls[-1] if controls else None)
        try:
            registered = self.registered_slice(
                unit.parent_sample_id, unit.slice_record.media_relpath
            )
        except FrozenCoreError as error:
            raise FrozenCoreClientError(
                "prepared feature execution unit source changed: " + str(error)
            ) from error
        if (
            unit.parent_sample_id != payload.get("sample_id")
            or unit.slice_record.media_relpath != payload.get("media_relpath")
            or unit.slice_record.audio_seconds != payload.get("audio_seconds")
            or unit.slice_record.sample_rate_hz != payload.get("sample_rate_hz")
            or registered != unit.slice_record
        ):
            raise FrozenCoreClientError(
                "prepared feature request differs from its execution unit source"
            )
        query = next(
            (
                descriptor
                for descriptor in payload.get("speech_feature_parts", ())
                if isinstance(descriptor, Mapping)
                and descriptor.get("role") == "query"
            ),
            None,
        )
        if query != unit.query_descriptor("speech_features"):
            raise FrozenCoreClientError(
                "prepared feature request differs from its execution unit packet"
            )

    def _raw_speech_identity(self, sample_id: str, media_relpath: str) -> dict[str, str]:
        """Hash only the bound original or a verified registered runtime slice."""
        try:
            relative = _normalized_relative_path(media_relpath, "raw native query")
            if self._reverse_media_index.get(relative) != sample_id:
                raise FrozenCoreClientError("raw native query is not bound to this sample")
            record = (
                self._slice_registry.lookup(sample_id, relative)
                if self._slice_registry is not None else None
            )
            if record is not None:
                self._slice_registry.verify_slice_bytes(record)
                digest = record.sha256
            else:
                if relative != self._binding.media_relpaths.get(sample_id):
                    raise FrozenCoreClientError("raw native query is not a registered source")
                path = _resolve_confined_any(
                    self._binding.data_root, relative,
                    (self._binding.carrier_root, *self._binding.derived_media_roots),
                    "raw native query", strict=True,
                )
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
        except (OSError, FrozenCoreError) as error:
            raise FrozenCoreClientError("raw native query identity failed: " + str(error)) from error
        return {"media_relpath": relative, "sha256": digest}

    def bound_raw_speech_identity(
        self, sample_id: str, media_relpath: str
    ) -> dict[str, str]:
        """Return a raw-native observation or prepared-text custody anchor identity."""

        if self._arm != _RAW_NATIVE_ARM and not self._is_prepared_text_arm:
            raise FrozenCoreClientError(
                "raw speech identity requires the raw native or prepared text arm"
            )
        return self._raw_speech_identity(sample_id, media_relpath)

    def _build_request_payload(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        decoding_params: Mapping[str, object] | None = None,
        text_only_sample_id: str | None = None,
        speech_feature_sample_id: str | None = None,
        raw_agent_sample_id: str | None = None,
        key_representation_id: str | None = None,
        matcher_policy_id: str | None = None,
        agent_state: Sequence[Mapping[str, object]] | None = None,
        agent_contact_id: str | None = None,
        contact_instruction: str | None = None,
        construction_target_ids: Sequence[str] | None = None,
        tool_names: Sequence[str] | None = None,
        prepare_only: bool = False,
    ) -> dict[str, object]:
        """The abort's own root cause, repaired (attempt-1 accounting,
        docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md section
        7): pre-2026-08-19, this method ALWAYS ran ``messages`` through the
        AUDIO invariant (``_parse_rails_messages``'s default), so the first
        registered TEXT-ONLY request (P-KEY's TXT-NOSUP) was refused with
        "user message must carry exactly one input_audio content part" --
        the client layer was never relaxed for registered text-only arms.

        ``text_only_sample_id`` (opt-in, default ``None`` -- every
        pre-existing caller is byte-identical) is that relaxation, GATED
        explicitly rather than inferred from ``messages`` shape alone (a
        text-only ``messages`` shape carries no ``media_relpath`` a reverse
        index could resolve on its own -- the caller must name the sample):
        when given, ``messages`` is parsed under the INVERSE (audio-free)
        invariant (:func:`_parse_rails_messages` ``text_only=True`` --
        refuses loud if an ``input_audio`` part is present), and this
        request's ``sample_id``/``media_relpath``/``audio_seconds``/
        ``sample_rate_hz`` payload fields are resolved from THIS client's own
        verified binding for ``text_only_sample_id`` directly (the SAME
        facts an audio request for that sample would carry -- I3/I4 payload-
        binding enforcement, ``core.model.binding._enforce_payload_binding``,
        is unchanged and untouched by this bridge: a text-only request is
        still, honestly, about that exact bound sample's speech_ref, even
        though no audio content part is ever sent). The DEFAULT AUDIO
        invariant is preserved byte-for-byte for every existing caller: a
        message carrying zero or two-or-more ``input_audio`` parts still
        refuses exactly as before.

        AgentLoop calls may additionally provide validated
        ``AgentStateArtifact`` documents and one contact id/instruction.
        Those records remain ORG/CONTROL history in the audited payload;
        only text parts carrying evidence ids become SUPPLY.
        """

        if self._closed:
            raise FrozenCoreClientError("complete() called after close()")
        raw_native = self._arm == _RAW_NATIVE_ARM
        if raw_native != (raw_agent_sample_id is not None):
            raise FrozenCoreClientError(
                "raw_agent_sample_id requires the explicit raw-speech-agent-native-tools arm"
            )
        if raw_native and (
            not isinstance(raw_agent_sample_id, str) or not raw_agent_sample_id
            or text_only_sample_id is not None or speech_feature_sample_id is not None
            or key_representation_id is not None or matcher_policy_id is not None
        ):
            raise FrozenCoreClientError("raw native query selectors are ambiguous")
        selected_tool_schemas = self._select_tool_schemas(tool_names)
        if selected_tool_schemas == () and (
            not isinstance(decoding_params, Mapping)
            or decoding_params.get("tool_choice") != "none"
        ):
            raise FrozenCoreClientError(
                "an empty per-contact tool_names scope requires tool_choice 'none'"
            )
        speech_feature_parts: list[dict[str, str]] | None = None
        speech_supply_parts: list[dict[str, str | None]] | None = None
        history = _agent_history(
            agent_state=agent_state,
            agent_contact_id=agent_contact_id,
            contact_instruction=contact_instruction,
        )
        if self._is_prepared_text_arm and (
            text_only_sample_id is None or speech_feature_sample_id is not None or raw_native
        ):
            raise FrozenCoreClientError("prepared text requires an explicit text-only anchor")
        if history and speech_feature_sample_id is None and not raw_native and not self._is_prepared_text_arm:
            raise FrozenCoreClientError(
                "Agent state/control requires an explicit feature or raw native decision call"
            )
        if speech_feature_sample_id is not None:
            if text_only_sample_id is not None:
                raise FrozenCoreClientError(
                    "speech_feature_sample_id and text_only_sample_id are mutually exclusive"
                )
            if not self._is_speech_feature_arm:
                raise FrozenCoreClientError(
                    "speech_feature_sample_id requires a speech-feature-query arm"
                )
            if (
                not isinstance(speech_feature_sample_id, str)
                or not speech_feature_sample_id
            ):
                raise FrozenCoreClientError(
                    "speech_feature_sample_id must be a non-empty string"
                )
            if not isinstance(key_representation_id, str) or not key_representation_id:
                raise FrozenCoreClientError(
                    "key_representation_id must be a non-empty string"
                )
            if not isinstance(matcher_policy_id, str) or not matcher_policy_id:
                raise FrozenCoreClientError(
                    "matcher_policy_id must be a non-empty string"
                )
            task_instruction, speech_supply_parts, speech_feature_parts = (
                _parse_speech_feature_messages(messages)
            )
            supply_texts = [part["text"] for part in speech_supply_parts]
            sample_id = speech_feature_sample_id
            unit = self._feature_execution_unit(agent_contact_id)
            if unit is None:
                expected_query = self._speech_packet_bindings.get(sample_id)
                if expected_query is None:
                    raise FrozenCoreClientError(
                        f"speech_feature_sample_id {sample_id!r} is not bound to this client"
                    )
                media_relpath = self._binding.media_relpaths[sample_id]
                audio_seconds, sample_rate_hz = self._binding.sample_facts[sample_id]
            else:
                if unit.parent_sample_id != sample_id:
                    raise FrozenCoreClientError(
                        "feature execution unit differs from its parent sample"
                    )
                descriptor = unit.query_descriptor("speech_features")
                expected_query = {
                    "packet_id": descriptor["packet_id"],
                    "sha256": descriptor["sha256"],
                }
                try:
                    registered = self.registered_slice(
                        sample_id, unit.slice_record.media_relpath
                    )
                except FrozenCoreError as error:
                    raise FrozenCoreClientError(
                        "feature execution unit source slice changed: " + str(error)
                    ) from error
                if registered != unit.slice_record:
                    raise FrozenCoreClientError(
                        "feature execution unit source slice changed"
                    )
                media_relpath = unit.slice_record.media_relpath
                audio_seconds = unit.slice_record.audio_seconds
                sample_rate_hz = unit.slice_record.sample_rate_hz
            actual_query = next(
                part for part in speech_feature_parts if part["role"] == "query"
            )
            if {
                "packet_id": actual_query["packet_id"],
                "sha256": actual_query["sha256"],
            } != expected_query:
                raise FrozenCoreClientError(
                    f"query packet does not match the bound packet for sample {sample_id!r}"
                )
            assert self._speech_feature_root is not None
            load_speech_feature_packets(
                self._speech_feature_root,
                tuple(
                    {
                        "packet_id": descriptor["packet_id"],
                        "sha256": descriptor["sha256"],
                    }
                    for descriptor in speech_feature_parts
                ),
                workers=8,
                expected_decoder_gguf_sha256=self._speech_decoder_gguf_sha256,
                expected_n_embd=self._speech_n_embd,
            )
        elif text_only_sample_id is not None:
            if not isinstance(text_only_sample_id, str) or not text_only_sample_id:
                raise FrozenCoreClientError(
                    "text_only_sample_id must be a non-empty string"
                )
            task_instruction, _, supply_texts = _parse_rails_messages(
                messages, text_only=True
            )
            sample_id = text_only_sample_id
            if sample_id not in self._binding.allowed_sample_ids:
                raise FrozenCoreClientError(
                    f"text_only_sample_id {sample_id!r} is not bound to any sample this client "
                    "was constructed with"
                )
            media_relpath = self._binding.media_relpaths[sample_id]
            audio_seconds, sample_rate_hz = self._binding.sample_facts[sample_id]
        else:
            if self._is_speech_feature_arm:
                raise FrozenCoreClientError(
                    "speech-feature-query requires speech_feature_sample_id and a query "
                    "packet on every decision call"
                )
            task_instruction, media_relpath, supply_texts = _parse_rails_messages(
                messages
            )
            sample_id = self._reverse_media_index.get(media_relpath)
            if sample_id is None:
                raise FrozenCoreClientError(
                    f"media_relpath {media_relpath!r} is not bound to any sample this client "
                    "was constructed with (and no matching slice was registered)"
                )
            if raw_native:
                if raw_agent_sample_id != sample_id:
                    raise FrozenCoreClientError("raw native sample differs from the bound audio")
                speech_supply_parts = [
                    _typed_supply_part(part) for part in messages[1]["content"]
                    if part["type"] == "text"
                ]
                if any(not part["evidence_id"] or not part["source_uri"]
                       for part in speech_supply_parts):
                    raise FrozenCoreClientError(
                        "raw native supply requires stable evidence_id and source_uri"
                    )
            # A registered slice's own facts take priority over the parent
            # sample's -- a slice is admitted precisely because its bytes (and
            # therefore its duration) may differ from the parent (comment at
            # self._slice_facts's own declaration).
            audio_seconds, sample_rate_hz = self._slice_facts.get(
                media_relpath, self._binding.sample_facts[sample_id]
            )
        if prepare_only:
            request_id = _PREPARED_REQUEST_ID
        else:
            with self._state_lock:
                self._request_counter += 1
                request_id = f"{self._request_id_prefix}-{self._request_counter:04d}"
        # Every rails "text" content part becomes one supplied-evidence item
        # (module docstring): rails flattens a SupplyPacket to prompt-level
        # text before assemble_prompt ever runs, so per-item EvidenceItem
        # provenance (data.lock_key/relpath/sha256) no longer exists by this
        # point -- the provenance record below names the rails message
        # itself as the source, honestly, rather than fabricating a carrier
        # file this text never came from.
        supplied_evidence = [
            {
                "evidence_id": (
                    (
                        speech_supply_parts[index]["evidence_id"]
                        or _speech_supply_evidence_id(index, text)
                    )
                    if speech_supply_parts is not None
                    else f"{request_id}-supply-{index}"
                ),
                "source_uri": (
                    speech_supply_parts[index]["source_uri"]
                    if speech_supply_parts is not None
                    and speech_supply_parts[index]["source_uri"] is not None
                    else f"rails-supply://{sample_id}"
                ),
                "content": text,
                **(
                    {"knowledge_role": speech_supply_parts[index]["knowledge_role"]}
                    if speech_supply_parts is not None
                    and speech_supply_parts[index].get("knowledge_role") is not None
                    else {}
                ),
            }
            for index, text in enumerate(supply_texts)
        ]
        evidence_provenance = [
            _supply_provenance(
                None if speech_supply_parts is None else speech_supply_parts[index],
                text, request_id=request_id, index=index,
            )
            for index, text in enumerate(supply_texts)
        ]
        payload: dict[str, object] = {
            "request_id": request_id,
            "carrier_lock_key": self._plan.carrier_lock_key,
            "sample_id": sample_id,
            "speech_ref": f"{self._plan.carrier_lock_key}/{sample_id}",
            "media_relpath": media_relpath,
            "audio_seconds": audio_seconds,
            "sample_rate_hz": sample_rate_hz,
            "task_instruction": task_instruction,
            "history": history,
            "decoding_params": dict(decoding_params) if decoding_params else {},
        }
        if self._is_prepared_text_arm:
            from .prepared_text import PREPARED_TEXT_SCHEMA, validate_prepared_text_payload
            payload["prepared_text"] = PREPARED_TEXT_SCHEMA
            try:
                validate_prepared_text_payload(payload)
            except ValueError as error:
                raise FrozenCoreClientError(str(error)) from error
        if raw_native:
            payload["raw_speech_query"] = self._raw_speech_identity(sample_id, media_relpath)
        if self._carries_evidence:
            payload["supplied_evidence"] = supplied_evidence
            payload["evidence_provenance"] = evidence_provenance
        elif supply_texts:
            # A zero-supply arm was handed prompt-level supply text. Dropping
            # it silently would send the model text the audited payload does
            # not record; refuse instead.
            raise FrozenCoreClientError(
                f"arm {self._arm!r} declares no evidence fields, so it cannot carry "
                f"the {len(supply_texts)} supply text part(s) these messages contain"
            )
        if speech_feature_parts is not None:
            query_part = next(
                part for part in speech_feature_parts if part["role"] == "query"
            )
            payload.update(
                {
                    "speech_feature_parts": speech_feature_parts,
                    "speech_packet_sha256": query_part["sha256"],
                    "query_source": "speech_features",
                    "key_representation_id": key_representation_id,
                    "matcher_policy_id": matcher_policy_id,
                    "mmproj_loaded": False,
                }
            )
        # Native tool-calling arm (D1b): the ONLY payload field this bridge
        # adds beyond what a non-native arm of the same base shape already
        # carries -- applies identically whether the base payload above came
        # from the raw-audio branch or the packet branch, so a native arm's
        # payload is otherwise byte-identical to its non-native counterpart
        # for the same messages (module docstring's own "for BOTH audio
        # paths" acceptance rule; core.model.transport.LlamaServerTransport.
        # __call__ forwards it verbatim as the request's `tools` key).
        if self._is_native_tools_arm:
            payload["tool_schemas"] = list(selected_tool_schemas)
        # Construction-proposer arm (E2.4): the one payload field that carries
        # gold, attached only for the arm whose D2-frozen field set declares
        # it and only on a text-only contact -- the proposer writes an
        # artifact from construction exemplars, so an audio part would be both
        # unnecessary and unaudited here.
        if self._is_construction_proposer_arm:
            if text_only_sample_id is None:
                raise FrozenCoreClientError(
                    f"arm {self._arm!r} is text-only; every request must name its "
                    "text_only_sample_id"
                )
            payload[_CONSTRUCTION_TARGETS_FIELD] = self._selected_construction_targets(
                construction_target_ids
            )
        elif construction_target_ids is not None:
            raise FrozenCoreClientError(
                f"arm {self._arm!r} is not a construction-proposer arm; "
                "construction_target_ids must be omitted"
            )
        return payload

    def _select_tool_schemas(
        self, tool_names: Sequence[str] | None,
    ) -> tuple[dict[str, object], ...] | None:
        """Select an ordered subset of this client's immutable tool registry."""
        if not self._is_native_tools_arm:
            if tool_names is not None:
                raise FrozenCoreClientError(
                    "tool_names is valid only for a native tool-calling arm"
                )
            return None
        assert self._tool_schemas is not None
        if tool_names is None:
            return self._tool_schemas
        if (
            not isinstance(tool_names, Sequence)
            or isinstance(tool_names, (str, bytes))
            or any(not isinstance(name, str) or not name for name in tool_names)
        ):
            raise FrozenCoreClientError(
                "tool_names must be an ordered sequence of non-empty strings"
            )
        names = tuple(tool_names)
        if len(set(names)) != len(names):
            raise FrozenCoreClientError("tool_names must not contain duplicates")
        unknown = [name for name in names if name not in self._tool_schemas_by_name]
        if unknown:
            raise FrozenCoreClientError(
                f"tool_names contains names outside the registered superset: {unknown}"
            )
        return tuple(self._tool_schemas_by_name[name] for name in names)

    def record_tool_call(self, count: int = 1) -> None:
        """Count a registered internal invocation without a model/audio debit."""
        with self._state_lock:
            if self._closed:
                raise FrozenCoreClientError("record_tool_call() called after close()")
            self._adapter.record_tool_call(count)

    def close(self) -> dict[str, object]:
        """Close the owned ``TraceSink`` (mirrors ``core.driver.run_experiment``'s
        own ``manifest_hash = sink.close()``) and return a JSON-safe summary
        -- "write run manifests/receipts through the existing machinery"
        (bridge mission instruction): the trace-manifest hash and the
        adapter's own ``cost_summary()`` (which itself carries the umbrella
        lock hash the gate returned, M-3) ARE that existing machinery: this
        method adds no parallel accounting of its own, only reports what
        ``TraceSink``/``FrozenCoreAdapter`` already recorded. Idempotent
        refusal: a second ``close()`` raises rather than silently re-closing
        (mirrors ``core.tracing.TraceSink``'s own closed-sink refusal on a
        second ``emit``)."""

        if self._closed:
            raise FrozenCoreClientError("close() called twice")
        with self._state_lock:
            self._closed = True
            self._prepared_requests.clear()
            manifest_hash = self._sink.close()
            request_count = self._request_counter
            timings = [timing.as_json() for timing in self._timings]
        return {
            "run_id": self._plan.run_id,
            "arm": self._arm,
            "tool_schemas_sha256": self._tool_schemas_sha256,
            "trace_manifest_hash": manifest_hash,
            "cost": self._adapter.cost_summary(),
            "flight_lock": self._flight_lock,
            "request_count": request_count,
            "timings": timings,
        }


def _content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _speech_supply_evidence_id(index: int, text: str) -> str:
    """Return the request-independent identifier used in speech wire prompts."""

    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise FrozenCoreClientError(
            "speech supply index must be a non-negative integer"
        )
    if not isinstance(text, str) or not text:
        raise FrozenCoreClientError("speech supply text must be a non-empty string")
    return f"speech-supply-{index:02d}-{_content_sha256(text)}"
