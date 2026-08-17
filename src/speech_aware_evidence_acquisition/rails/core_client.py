"""CoreClient: the seam every rails runner call reaches "the model" through --
kept SEPARATE from ``core.model.FrozenCoreAdapter`` deliberately.

``FrozenCoreAdapter`` is the production, gate-enforced, budget-metered
request path (``PayloadBindingContext``, ``AttemptStore``, ``TraceSink``,
the D2 arm-field allowlist -- ``core.model.adapter``); wiring it in here
would mean this zero-model-contact engineering skeleton also has to
construct a live ``FrozenCoreGate``, an attempt store and a verified split,
none of which a rails-only test fixture has any business building, and B0's
mission is explicit: engineering only, ZERO model contact. ``CoreClient`` is
instead the MINIMAL request shape a ``TaskAdapter``'s assembled messages
need -- a future model-touching task can implement a ``CoreClient`` that
internally delegates to ``FrozenCoreAdapter`` without changing this
Protocol's shape or any caller of it.

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
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence, runtime_checkable

from ..contracts import ExecutionPlan, assert_execution_scope
from ..core.base import PayloadBindingContext
from ..core.flight_lock import read_flight_lock
from ..core.model import FrozenCoreAdapter, SliceRegistry
from ..core.model.slices import SliceRecord
from ..core.tracing import TraceSink
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .errors import RailsError


@runtime_checkable
class CoreClient(Protocol):
    """One completion call: chat-style ``messages`` in, response text out.
    No implementation in THIS module ever touches a real model -- see
    :class:`MockCoreClient` below, the only implementation this engineering
    mission constructs."""

    def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        decoding_params: Mapping[str, object] | None = None,
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
    ) -> str:
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

DEFAULT_RAILS_ARM = "fixed-legal-context"


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
        raise FrozenCoreClientError(f"cannot read audio header of {path}: {error}") from error
    rate = info.samplerate
    if isinstance(rate, bool) or not isinstance(rate, int) or rate <= 0:
        raise FrozenCoreClientError(f"audio header of {path} reports sample rate {rate!r}")
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
    rest of ``rails``) never needs its own lock coupling."""

    if not samples:
        raise FrozenCoreClientError("build_payload_binding requires at least one sample")
    allowed_sample_ids: set[str] = set()
    sample_facts: dict[str, tuple[float, int]] = {}
    media_relpaths: dict[str, str] = {}
    for sample in samples:
        sample_id = sample.sample_id
        if not isinstance(sample_id, str) or not sample_id:
            raise FrozenCoreClientError(f"sample_id must be a non-empty string, got {sample_id!r}")
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
    ).validate()


def build_slice_registry(*, data_root: Path, run_id: str, samples: Sequence[object]) -> SliceRegistry:
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
        sample.sample_id: (sample.audio_ref.path, float(sample.audio_seconds)) for sample in samples
    }
    return SliceRegistry(data_root=Path(data_root), run_id=run_id, parent_facts=parent_facts)


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

    def as_json(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "sample_id": self.sample_id,
            "started_at": self.started_at,
            "latency_seconds": self.latency_seconds,
        }


def _parse_rails_messages(
    messages: Sequence[Mapping[str, object]],
) -> tuple[str, str, list[str]]:
    """Extract ``(task_instruction, media_relpath, supply_texts)`` from a
    rails ``TaskAdapter.assemble_prompt`` output -- exactly the two-message
    ``[system, user]`` shape both ``SlurpAdapter`` and ``Audio2ToolAdapter``
    build (module docstring). Fail-closed on anything else: this bridge
    speaks exactly the shape those adapters produce, not an arbitrary chat
    transcript."""

    if len(messages) != 2:
        raise FrozenCoreClientError(
            f"FrozenCoreClient expects exactly 2 messages (system, user), got {len(messages)}"
        )
    system_message, user_message = messages
    if not isinstance(system_message, Mapping) or system_message.get("role") != "system":
        raise FrozenCoreClientError("messages[0] must be a mapping with role 'system'")
    task_instruction = system_message.get("content")
    if not isinstance(task_instruction, str) or not task_instruction:
        raise FrozenCoreClientError("system message content must be a non-empty string")
    if not isinstance(user_message, Mapping) or user_message.get("role") != "user":
        raise FrozenCoreClientError("messages[1] must be a mapping with role 'user'")
    content = user_message.get("content")
    if not isinstance(content, Sequence) or isinstance(content, (str, bytes)):
        raise FrozenCoreClientError("user message content must be a list of content parts")
    media_relpath: str | None = None
    supply_texts: list[str] = []
    for index, part in enumerate(content):
        if not isinstance(part, Mapping) or "type" not in part:
            raise FrozenCoreClientError(
                f"user content[{index}] must be a mapping with a 'type' key, got {part!r}"
            )
        part_type = part["type"]
        if part_type == "input_audio":
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
                raise FrozenCoreClientError("text content part must carry non-empty text")
            supply_texts.append(text)
        else:
            raise FrozenCoreClientError(f"unsupported content part type {part_type!r}")
    if media_relpath is None:
        raise FrozenCoreClientError(
            "user message must carry exactly one input_audio content part"
        )
    return task_instruction, media_relpath, supply_texts


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
    ) -> None:
        plan.validate()
        assert_execution_scope(plan.execution_profile)
        if arm not in ARM_VISIBLE_FIELDS:
            raise FrozenCoreClientError(
                f"unknown D2 arm {arm!r}; D2-frozen arms are {sorted(ARM_VISIBLE_FIELDS)}"
            )
        if set(ARM_VISIBLE_FIELDS[arm]) != _SUPPORTED_ARM_FIELDS:
            raise FrozenCoreClientError(
                f"FrozenCoreClient only builds payloads for the field set "
                f"{sorted(_SUPPORTED_ARM_FIELDS)} (D2 arm {DEFAULT_RAILS_ARM!r}); arm "
                f"{arm!r} declares a different field set {sorted(ARM_VISIBLE_FIELDS[arm])}"
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
        self._slice_registry = slice_registry
        self._adapter = FrozenCoreAdapter(
            gate=gate,
            plan=plan,
            arm=arm,
            transport=transport,
            sink=self._sink,
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
        self._closed = False

    @property
    def arm(self) -> str:
        return self._arm

    @property
    def flight_lock(self) -> Mapping[str, object] | None:
        return self._flight_lock

    @property
    def timings(self) -> tuple[RequestTiming, ...]:
        return tuple(self._timings)

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
        self._slice_facts[record.media_relpath] = (record.audio_seconds, record.sample_rate_hz)

    def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        decoding_params: Mapping[str, object] | None = None,
    ) -> str:
        if self._closed:
            raise FrozenCoreClientError("complete() called after close()")
        task_instruction, media_relpath, supply_texts = _parse_rails_messages(messages)
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
                "evidence_id": f"{request_id}-supply-{index}",
                "source_uri": f"rails-supply://{sample_id}",
                "content": text,
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
            "history": [],
            "decoding_params": dict(decoding_params) if decoding_params else {},
            "supplied_evidence": supplied_evidence,
            "evidence_provenance": evidence_provenance,
        }
        started_at = _iso(self._now())
        response = self._adapter.request(payload)
        self._timings.append(
            RequestTiming(
                request_id=request_id,
                sample_id=sample_id,
                started_at=started_at,
                latency_seconds=response.latency_seconds,
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
        self._closed = True
        manifest_hash = self._sink.close()
        return {
            "run_id": self._plan.run_id,
            "arm": self._arm,
            "trace_manifest_hash": manifest_hash,
            "cost": self._adapter.cost_summary(),
            "flight_lock": self._flight_lock,
            "request_count": self._request_counter,
            "timings": [timing.as_json() for timing in self._timings],
        }


def _content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
