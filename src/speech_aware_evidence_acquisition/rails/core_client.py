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
from ..core.model import FrozenCoreAdapter, SliceRegistry, load_speech_feature_packets
from ..core.model.slices import SliceRecord
from ..core.tracing import DispatchingSink, TraceBuffer, TraceSink
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .errors import RailsError
from .knowledge import AgentStateArtifact


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
    on a formal speech-feature request. They populate D2's separate
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
        key_representation_id: str | None = None,
        matcher_policy_id: str | None = None,
        agent_state: Sequence[Mapping[str, object]] | None = None,
        agent_contact_id: str | None = None,
        contact_instruction: str | None = None,
        construction_target_ids: Sequence[str] | None = None,
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
# docstring). Only "speech-feature-query-native-tools" is a real,
# D2-registered arm as of this slice (e0.d2_leakage.ARM_VISIBLE_FIELDS); the
# raw-audio member of this pair is accepted here too so this acceptance logic
# never has to change again the day a raw-audio native-tools D2 arm is
# registered -- constructing this client for an arm name that is not in
# ARM_VISIBLE_FIELDS still fails closed ("unknown D2 arm") exactly as it
# always has, regardless of this field-set shape ever being reachable.
_NATIVE_TOOLS_FIELD = "tool_schemas"
_NATIVE_TOOLS_SUPPORTED_ARM_FIELDS = _SUPPORTED_ARM_FIELDS | frozenset(
    {_NATIVE_TOOLS_FIELD}
)
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
_ACCEPTED_ARM_FIELD_SETS = frozenset(
    {
        _SUPPORTED_ARM_FIELDS,
        _SPEECH_FEATURE_ARM_FIELDS,
        _NATIVE_TOOLS_SUPPORTED_ARM_FIELDS,
        _NATIVE_TOOLS_SPEECH_FEATURE_ARM_FIELDS,
        _ZERO_SUPPLY_ARM_FIELDS,
        _NATIVE_TOOLS_ZERO_SUPPLY_ARM_FIELDS,
        _CONSTRUCTION_PROPOSER_ARM_FIELDS,
    }
)
_SPEECH_FEATURE_FAMILY_ARM_FIELDS = frozenset(
    {_SPEECH_FEATURE_ARM_FIELDS, _NATIVE_TOOLS_SPEECH_FEATURE_ARM_FIELDS}
)

DEFAULT_RAILS_ARM = "fixed-legal-context"


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


def _validate_tool_schemas(
    tool_schemas: Sequence[Mapping[str, object]] | None,
) -> tuple[dict[str, object], ...]:
    """A native tool-calling arm's own ``tool_schemas`` invariant: a
    non-empty sequence of OpenAI-format ``{"type": "function", "function":
    {"name": ..., ...}}`` entries -- the exact shape
    ``data.audio2tool_tools.render_openai_tools`` produces (never imported
    here; module docstring -- this bridge's own dependency surface stays
    light). Every entry is copied into a plain ``dict`` so the client's own
    stored tuple never aliases a caller-owned mutable object."""

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
    for index, entry in enumerate(tool_schemas):
        if not isinstance(entry, Mapping):
            raise FrozenCoreClientError(
                f"tool_schemas[{index}] must be a mapping, got {type(entry).__name__}"
            )
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
        validated.append(dict(entry))
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
    # D1b, 2026-09-03: ``None`` for every non-native-tools client (every
    # pre-existing caller, byte-identical); the client's own
    # ``tool_schemas_sha256`` (constant for the client's whole life) on a
    # native-tools client, so a per-request trace record names the exact
    # tool registry that request was made under without re-hashing it.
    tool_schemas_sha256: str | None = None
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

    def as_json(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "sample_id": self.sample_id,
            "started_at": self.started_at,
            "latency_seconds": self.latency_seconds,
            "tool_schemas_sha256": self.tool_schemas_sha256,
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
            supply_parts.append(
                {
                    "text": text,
                    "evidence_id": evidence_id,
                    "source_uri": source_uri,
                    "knowledge_role": knowledge_role,
                }
            )
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
        artifacts = tuple(
            AgentStateArtifact.from_json(document) for document in agent_state
        )
    except (KeyError, RailsError, TypeError) as error:
        raise FrozenCoreClientError(
            f"malformed Agent state artifact: {error}"
        ) from error
    ids = [artifact.state_id for artifact in artifacts]
    if len(set(ids)) != len(ids):
        raise FrozenCoreClientError("agent_state contains duplicate state ids")
    history: list[dict[str, object]] = [
        {
            "turn": index,
            "role": "agent_state",
            "state_id": artifact.state_id,
            "state_kind": artifact.state_kind,
            "content": artifact.content,
            "content_sha256": _content_sha256(artifact.content),
            "source_query_state_sha256": artifact.source_query_state_sha256,
            "source_response_sha256": artifact.source_response_sha256,
            "producer_policy_id": artifact.producer_policy_id,
            "cited_value_ids": list(artifact.cited_value_ids),
        }
        for index, artifact in enumerate(artifacts, start=1)
    ]
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
        self._timings: list[RequestTiming] = []
        self._state_lock = threading.Lock()
        self._closed = False
        self._speech_feature_root: Path | None = None
        self._speech_packet_bindings: dict[str, dict[str, str]] = {}
        self._speech_decoder_gguf_sha256: str | None = None
        self._speech_n_embd: int | None = None
        if self._is_speech_feature_arm:
            if speech_feature_root is None or speech_packet_bindings is None:
                raise FrozenCoreClientError(
                    "speech-feature-query requires speech_feature_root and complete "
                    "speech_packet_bindings"
                )
            try:
                root = Path(speech_feature_root).resolve(strict=True)
            except OSError as error:
                raise FrozenCoreClientError(
                    f"speech_feature_root is unavailable: {error}"
                ) from error
            if not root.is_dir():
                raise FrozenCoreClientError("speech_feature_root must be a directory")
            if set(speech_packet_bindings) != set(binding.allowed_sample_ids):
                raise FrozenCoreClientError(
                    "speech_packet_bindings must materialize every target sample before inference"
                )
            verified: dict[str, dict[str, str]] = {}
            ordered_sample_ids = tuple(sorted(speech_packet_bindings))
            ordered_descriptors: list[dict[str, object]] = []
            for sample_id in ordered_sample_ids:
                descriptor = speech_packet_bindings[sample_id]
                if not isinstance(descriptor, Mapping) or set(descriptor) != {
                    "packet_id",
                    "sha256",
                }:
                    raise FrozenCoreClientError(
                        f"speech packet binding for {sample_id!r} must have exact "
                        "packet_id/sha256 keys"
                    )
                ordered_descriptors.append(dict(descriptor))
            packets = load_speech_feature_packets(
                root,
                tuple(ordered_descriptors),
                workers=8,
            )

            def audio_sha256(sample_id: str) -> str:
                audio_path = Path(binding.data_root) / binding.media_relpaths[sample_id]
                return hashlib.sha256(audio_path.read_bytes()).hexdigest()

            with ThreadPoolExecutor(
                max_workers=min(8, len(ordered_sample_ids)),
                thread_name_prefix="saea-speech-audio",
            ) as pool:
                audio_sha256s = tuple(pool.map(audio_sha256, ordered_sample_ids))
            for sample_id, packet, audio_digest in zip(
                ordered_sample_ids, packets, audio_sha256s, strict=True
            ):
                if packet.audio_sha256 != audio_digest:
                    raise FrozenCoreClientError(
                        f"speech packet bound to {sample_id!r} does not match its audio bytes"
                    )
                verified[sample_id] = {
                    "packet_id": packet.packet_id,
                    "sha256": packet.packet_sha256,
                }
            decoder_hashes = {packet.decoder_gguf_sha256 for packet in packets}
            dimensions = {chunk.n_embd for packet in packets for chunk in packet.chunks}
            if len(decoder_hashes) != 1 or len(dimensions) != 1:
                raise FrozenCoreClientError(
                    "speech packet bindings must share one decoder identity and dimension"
                )
            self._speech_feature_root = root
            self._speech_packet_bindings = verified
            self._speech_decoder_gguf_sha256 = next(iter(decoder_hashes))
            self._speech_n_embd = next(iter(dimensions))
        elif speech_feature_root is not None or speech_packet_bindings is not None:
            raise FrozenCoreClientError(
                "speech feature bindings are only valid for the speech-feature-query arm"
            )
        self._tool_schemas: tuple[dict[str, object], ...] | None = None
        self._tool_schemas_sha256: str | None = None
        if self._is_native_tools_arm:
            self._tool_schemas = _validate_tool_schemas(tool_schemas)
            self._tool_schemas_sha256 = _tool_schemas_sha256(self._tool_schemas)
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
        self._reverse_media_index[record.media_relpath] = record.sample_id
        self._slice_facts[record.media_relpath] = (
            record.audio_seconds,
            record.sample_rate_hz,
        )

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
        key_representation_id: str | None = None,
        matcher_policy_id: str | None = None,
        agent_state: Sequence[Mapping[str, object]] | None = None,
        agent_contact_id: str | None = None,
        contact_instruction: str | None = None,
        construction_target_ids: Sequence[str] | None = None,
    ) -> str:
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
        speech_feature_parts: list[dict[str, str]] | None = None
        speech_supply_parts: list[dict[str, str | None]] | None = None
        history = _agent_history(
            agent_state=agent_state,
            agent_contact_id=agent_contact_id,
            contact_instruction=contact_instruction,
        )
        if history and speech_feature_sample_id is None:
            raise FrozenCoreClientError(
                "Agent state/control is only valid on a speech-feature decision call"
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
            expected_query = self._speech_packet_bindings.get(sample_id)
            if expected_query is None:
                raise FrozenCoreClientError(
                    f"speech_feature_sample_id {sample_id!r} is not bound to this client"
                )
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
            media_relpath = self._binding.media_relpaths[sample_id]
            audio_seconds, sample_rate_hz = self._binding.sample_facts[sample_id]
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
            # A registered slice's own facts take priority over the parent
            # sample's -- a slice is admitted precisely because its bytes (and
            # therefore its duration) may differ from the parent (comment at
            # self._slice_facts's own declaration).
            audio_seconds, sample_rate_hz = self._slice_facts.get(
                media_relpath, self._binding.sample_facts[sample_id]
            )
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
            {
                "lock_key": "rails-supply",
                "relpath": f"rails-message/{request_id}/{index}",
                "sha256": _content_sha256(text),
            }
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
            payload["tool_schemas"] = list(self._tool_schemas)
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
        started_at = _iso(self._now())
        response = self._adapter.request(payload)
        with self._state_lock:
            self._timings.append(
                RequestTiming(
                    request_id=request_id,
                    sample_id=sample_id,
                    started_at=started_at,
                    latency_seconds=response.latency_seconds,
                    tool_schemas_sha256=self._tool_schemas_sha256,
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
        return response.text

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
