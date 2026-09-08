"""The Observer seam: the previous wave's REVIEW flags become the next wave's
observation.

Change 4 of the 2026-09-08 openJiuwen assessment's ordered list, and the
"SELECTIVE LISTENING" row of the agent-system design
(``docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md``):
the Observer re-listens only to the spans the Reviewer flagged, with more
context. ``obs-replay-loop`` has proved that mechanism end to end
(``reproduction.replay_loop``: SCORE -> LOCATE -> RETRIEVE -> REPLAY ->
ACCEPT, cutting each flagged span's neighbourhood window with
``core.span_surgery.cut_span`` and chaining it with
``core.model.slices.SliceRegistry``). This module does not reimplement any of
that -- it turns it into ONE optional step of the agent loop instead of a
second, separate policy.

What this module owns, and only this:

* the flag contract (``{sample_id, spans: [{start, end, reason}]}``) and one
  fixture reader for it, so the seam is exercisable model-free TODAY, before
  W1's ``REVIEW`` records exist. When they do exist, they arrive through the
  same ``FlagSource`` callable and nothing else moves;
* the fail-closed guards the change list names: a span outside its own media,
  a cutter that produced no derivation, a context margin that is not a finite
  non-negative number, and more re-listens for one sample than the config
  allows;
* the identity bridge: a :class:`~.knowledge.SpeechPacketDerivation` naming
  the trajectory's ORIGINAL packet as parent, the derived packet as output,
  and the canonical hash of the parameters that governed the cut.

What this module deliberately does NOT own: the loop. ``rails.runner`` calls
:meth:`ObserveStep.observe` between waves, builds the successor
``QueryState``, validates the ``relisten`` transition through
``assert_agent_step_binding``, and re-binds the controller's next contact.
Absent an ``ObserveStep`` the runner's graph is byte-identical to before this
module existed -- the default is no observer, and no observer is no step.

The byte chain stays where it already is. :class:`SliceReCutter` writes the
cut through ``core.span_surgery.cut_span`` and registers it through the
run's ``SliceRegistry``, which independently re-measures the parent media and
the written file; only then does the injected ``encode_packet`` turn the
chained slice into the speech-feature packet the agent loop actually sends.
Encoding a packet is the one step that needs the preprocessing encoder, so it
is injected rather than performed here: this module imports no model code and
runs model-free.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

from ..core.model import SliceRecord, SliceRegistry
from .errors import RailsError
from .hashing import content_hash
from .knowledge import SPEECH_PACKET_DERIVATION_KINDS, SpeechPacketDerivation

OBSERVE_STEP_VERSION = "agent-observe-step-v1"
RELISTEN_PARAMS_VERSION = "agent-relisten-params-v1"


class ObserveError(RailsError):
    """The Observer refused: an unusable flag, an out-of-media span, an
    over-budget sample, or a cutter that produced no registered derivation."""


def _finite(value: object, *, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ObserveError(f"{field} must be a finite number, got {value!r}")
    return float(value)


@dataclass(frozen=True)
class FlaggedSpan:
    """One span of one sample's media the Reviewer asked to hear again."""

    start_seconds: float
    end_seconds: float
    reason: str

    def validate(self) -> "FlaggedSpan":
        start = _finite(self.start_seconds, field="FlaggedSpan.start_seconds")
        end = _finite(self.end_seconds, field="FlaggedSpan.end_seconds")
        if start < 0:
            raise ObserveError(
                f"FlaggedSpan.start_seconds must be non-negative, got {start}"
            )
        if end <= start:
            raise ObserveError(
                f"FlaggedSpan span [{start}, {end}) is not a positive interval"
            )
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ObserveError("FlaggedSpan.reason must be a non-empty string")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "start": self.start_seconds,
            "end": self.end_seconds,
            "reason": self.reason,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "FlaggedSpan":
        if not isinstance(document, Mapping):
            raise ObserveError(
                f"a flagged span must be a mapping, got {type(document).__name__}"
            )
        missing = {"start", "end", "reason"} - set(document)
        if missing:
            raise ObserveError(
                f"a flagged span must carry start/end/reason; missing {sorted(missing)}"
            )
        return cls(
            start_seconds=document["start"],
            end_seconds=document["end"],
            reason=document["reason"],
        ).validate()


@dataclass(frozen=True)
class ReviewFlags:
    """One sample's flags from one wave, in the shape W1's ``REVIEW`` records
    will carry: ``{sample_id, spans: [{start, end, reason}]}``."""

    sample_id: str
    spans: tuple[FlaggedSpan, ...]
    wave_index: int | None = None

    def validate(self) -> "ReviewFlags":
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise ObserveError("ReviewFlags.sample_id must be a non-empty string")
        if not isinstance(self.spans, tuple):
            raise ObserveError("ReviewFlags.spans must be a tuple")
        for span in self.spans:
            if not isinstance(span, FlaggedSpan):
                raise ObserveError("ReviewFlags.spans entries must be FlaggedSpan")
            span.validate()
        if self.wave_index is not None and (
            isinstance(self.wave_index, bool)
            or not isinstance(self.wave_index, int)
            or self.wave_index < 0
        ):
            raise ObserveError(
                "ReviewFlags.wave_index must be a non-negative integer or None"
            )
        return self

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "ReviewFlags":
        if not isinstance(document, Mapping):
            raise ObserveError(
                f"review flags must be a mapping, got {type(document).__name__}"
            )
        unknown = set(document) - {"sample_id", "spans", "wave_index"}
        if unknown:
            raise ObserveError(
                f"review flags carry unknown keys {sorted(unknown)}; the contract is "
                "{sample_id, spans: [{start, end, reason}]} plus an optional wave_index"
            )
        spans = document.get("spans")
        if not isinstance(spans, Sequence) or isinstance(spans, (str, bytes)):
            raise ObserveError("review flags 'spans' must be a list")
        return cls(
            sample_id=document.get("sample_id"),
            spans=tuple(FlaggedSpan.from_json(span) for span in spans),
            wave_index=document.get("wave_index"),
        ).validate()


# (sample_id, wave_index) -> the flags raised on that sample by that wave, or
# None when the Reviewer raised none. W1's REVIEW records will be read through
# exactly this signature.
FlagSource = Callable[[str, int], "ReviewFlags | None"]


def fixture_flag_source(document: object) -> FlagSource:
    """A :data:`FlagSource` over a static fixture, for use until W1's
    ``REVIEW`` records land (and afterwards, in tests).

    ``document`` is a list of ``{sample_id, spans, wave_index?}`` mappings, or
    one such mapping. An entry with a ``wave_index`` answers only that wave; an
    entry without one answers every wave of its sample. Two entries that would
    answer the same (sample, wave) are refused rather than silently ordered.
    """

    entries = [document] if isinstance(document, Mapping) else document
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        raise ObserveError(
            "a flag fixture must be a review-flags mapping or a list of them"
        )
    keyed: dict[tuple[str, int | None], ReviewFlags] = {}
    for entry in entries:
        flags = ReviewFlags.from_json(entry)
        key = (flags.sample_id, flags.wave_index)
        if key in keyed:
            raise ObserveError(
                f"flag fixture declares {key!r} twice; one entry answers one "
                "(sample, wave)"
            )
        keyed[key] = flags

    def source(sample_id: str, wave_index: int) -> ReviewFlags | None:
        return keyed.get((sample_id, wave_index)) or keyed.get((sample_id, None))

    return source


@dataclass(frozen=True)
class ReListenRequest:
    """What the Observer asks a cutter for: one flagged span of one sample's
    own media, widened by the configured context margin and already clamped to
    the media's verified duration."""

    sample_id: str
    parent_media_relpath: str
    media_seconds: float
    span: FlaggedSpan
    start_seconds: float
    end_seconds: float
    context_margin_seconds: float
    derivation_kind: str
    relisten_index: int


@dataclass(frozen=True)
class ReListenResult:
    """The derived speech packet a cutter produced, plus whatever provenance
    it wants carried into the OBS trace record."""

    packet_id: str
    packet_sha256: str
    provenance: Mapping[str, object] = field(default_factory=dict)

    def validate(self) -> "ReListenResult":
        if not isinstance(self.packet_id, str) or not self.packet_id.strip():
            raise ObserveError("ReListenResult.packet_id must be a non-empty string")
        if (
            not isinstance(self.packet_sha256, str)
            or len(self.packet_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.packet_sha256)
        ):
            raise ObserveError("ReListenResult.packet_sha256 must be lowercase 64-hex")
        if not isinstance(self.provenance, Mapping):
            raise ObserveError("ReListenResult.provenance must be a mapping")
        return self


class ReListenCutter(Protocol):
    """Turn one :class:`ReListenRequest` into one registered derived packet."""

    def __call__(self, request: ReListenRequest) -> ReListenResult | None: ...


@dataclass(frozen=True)
class Observation:
    """One admitted re-listen: the span it answers, the identity chain that
    admits it, and the cutter's provenance for the trace."""

    span: FlaggedSpan
    derivation: SpeechPacketDerivation
    request: ReListenRequest
    provenance: Mapping[str, object]

    def trace_payload(self) -> dict[str, object]:
        return {
            "obs_relisten_index": self.request.relisten_index,
            "obs_flag_reason": self.span.reason,
            "obs_flagged_span_start_seconds": self.span.start_seconds,
            "obs_flagged_span_end_seconds": self.span.end_seconds,
            "obs_context_margin_seconds": self.request.context_margin_seconds,
            "obs_cut_start_seconds": self.request.start_seconds,
            "obs_cut_end_seconds": self.request.end_seconds,
            "obs_parent_media_relpath": self.request.parent_media_relpath,
            "obs_derivation_kind": self.derivation.derivation_kind,
            "obs_parent_packet_id": self.derivation.parent_packet_id,
            "obs_parent_packet_sha256": self.derivation.parent_packet_sha256,
            "obs_derived_packet_id": self.derivation.derived_packet_id,
            "obs_derived_packet_sha256": self.derivation.derived_packet_sha256,
            "obs_derivation_params_hash": self.derivation.derivation_params_hash,
            "obs_derivation_provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class ObserveConfig:
    """The ``observe`` config row, whose null arm is the absence of an
    :class:`ObserveStep` entirely (see the W4 note in
    ``docs/readiness/2026-09-08-ojw-wave-w2-observer-seam-v1.md``)."""

    context_margin_seconds: float
    max_relistens_per_sample: int
    derivation_kind: str = "recut-span"

    def validate(self) -> "ObserveConfig":
        margin = _finite(
            self.context_margin_seconds, field="ObserveConfig.context_margin_seconds"
        )
        if margin < 0:
            raise ObserveError(
                "ObserveConfig.context_margin_seconds must be non-negative, got "
                f"{margin}"
            )
        if (
            isinstance(self.max_relistens_per_sample, bool)
            or not isinstance(self.max_relistens_per_sample, int)
            or self.max_relistens_per_sample < 1
        ):
            raise ObserveError(
                "ObserveConfig.max_relistens_per_sample must be a positive integer"
            )
        if self.derivation_kind not in SPEECH_PACKET_DERIVATION_KINDS:
            raise ObserveError(
                "ObserveConfig.derivation_kind must be one of "
                f"{sorted(SPEECH_PACKET_DERIVATION_KINDS)}"
            )
        return self


class ObserveStep:
    """One optional step of the agent loop's wave preparation.

    Constructed by the driver from the ``observe`` config row and handed to
    ``rails.runner.run_speech_native_agent_loop``. ``media_facts`` is the SAME
    ``{sample_id: (media_relpath, seconds)}`` mapping
    ``core.model.slices.SliceRegistry`` is already built from, so the
    out-of-media guard reads the loader's own verified duration rather than a
    second, independently drifting copy of it.
    """

    def __init__(
        self,
        *,
        config: ObserveConfig,
        flag_source: FlagSource,
        cutter: ReListenCutter,
        media_facts: Mapping[str, tuple[str, float]],
    ) -> None:
        self._config = config.validate()
        if not callable(flag_source):
            raise ObserveError("ObserveStep flag_source must be callable")
        if not callable(cutter):
            raise ObserveError("ObserveStep cutter must be callable")
        if not isinstance(media_facts, Mapping):
            raise ObserveError("ObserveStep media_facts must be a mapping")
        self._flag_source = flag_source
        self._cutter = cutter
        self._media_facts = dict(media_facts)

    @property
    def config(self) -> ObserveConfig:
        return self._config

    def observe(
        self,
        *,
        sample_id: str,
        wave_index: int,
        origin_packet: tuple[str, str],
        relisten_index: int,
    ) -> Observation | None:
        """The next re-listen for this sample, or ``None`` for "keep going".

        ``None`` is returned exactly when the Reviewer raised no flag for this
        (sample, wave) or every flag it raised has already been re-listened to.
        Every other unusable input raises: a silently skipped re-listen would
        make two runs of the same config differ with nothing in the trace to
        say why.
        """

        flags = self._flag_source(sample_id, wave_index)
        if flags is None:
            return None
        flags.validate()
        if flags.sample_id != sample_id:
            raise ObserveError(
                f"flag source answered sample {flags.sample_id!r} for a query on "
                f"{sample_id!r}"
            )
        if not flags.spans:
            return None
        if len(flags.spans) > self._config.max_relistens_per_sample:
            raise ObserveError(
                f"sample {sample_id!r} carries {len(flags.spans)} flagged spans but "
                f"observe.max_relistens_per_sample is "
                f"{self._config.max_relistens_per_sample}; refusing rather than "
                "silently listening to some of them"
            )
        if relisten_index >= len(flags.spans):
            return None
        if relisten_index >= self._config.max_relistens_per_sample:
            raise ObserveError(
                f"sample {sample_id!r} asked for re-listen {relisten_index} beyond "
                f"its budget of {self._config.max_relistens_per_sample}"
            )

        fact = self._media_facts.get(sample_id)
        if fact is None:
            raise ObserveError(
                f"sample {sample_id!r} has no verified media in this run's loader "
                "facts; a span of unverified audio can never be cut"
            )
        parent_relpath, media_seconds = fact
        media_seconds = _finite(media_seconds, field="media duration")
        span = flags.spans[relisten_index]
        if span.end_seconds > media_seconds:
            raise ObserveError(
                f"flagged span [{span.start_seconds}, {span.end_seconds}) lies "
                f"outside sample {sample_id!r}'s own media (duration "
                f"{media_seconds}s); refusing"
            )
        margin = self._config.context_margin_seconds
        start_seconds = max(0.0, span.start_seconds - margin)
        end_seconds = min(media_seconds, span.end_seconds + margin)
        if end_seconds <= start_seconds:
            raise ObserveError(
                f"the context window for sample {sample_id!r}'s span "
                f"[{span.start_seconds}, {span.end_seconds}) collapsed to an empty "
                f"interval after clamping to [0, {media_seconds}]"
            )

        request = ReListenRequest(
            sample_id=sample_id,
            parent_media_relpath=parent_relpath,
            media_seconds=media_seconds,
            span=span,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            context_margin_seconds=margin,
            derivation_kind=self._config.derivation_kind,
            relisten_index=relisten_index,
        )
        result = self._cutter(request)
        if result is None:
            raise ObserveError(
                f"the re-listen cutter produced no derived packet for sample "
                f"{sample_id!r} span [{span.start_seconds}, {span.end_seconds}); a "
                "missing derivation is a refusal, never a skipped step"
            )
        if not isinstance(result, ReListenResult):
            raise ObserveError(
                "a re-listen cutter must return a ReListenResult, got "
                f"{type(result).__name__}"
            )
        result.validate()
        derivation = SpeechPacketDerivation(
            parent_packet_id=origin_packet[0],
            parent_packet_sha256=origin_packet[1],
            derived_packet_id=result.packet_id,
            derived_packet_sha256=result.packet_sha256,
            derivation_kind=self._config.derivation_kind,
            derivation_params_hash=relisten_params_hash(request),
        ).validate()
        return Observation(
            span=span,
            derivation=derivation,
            request=request,
            provenance=dict(result.provenance),
        )


def relisten_params_hash(request: ReListenRequest) -> str:
    """The canonical hash of everything that governed one cut.

    Two derivations that claim the same output from different spans, margins
    or kinds hash differently and therefore cannot both verify -- the same
    discipline ``core.evidence_derivation.canonical_params_hash`` applies to
    derived evidence text.
    """

    return content_hash(
        {
            "params_version": RELISTEN_PARAMS_VERSION,
            "sample_id": request.sample_id,
            "parent_media_relpath": request.parent_media_relpath,
            "flagged_start_seconds": request.span.start_seconds,
            "flagged_end_seconds": request.span.end_seconds,
            "flag_reason": request.span.reason,
            "context_margin_seconds": request.context_margin_seconds,
            "cut_start_seconds": request.start_seconds,
            "cut_end_seconds": request.end_seconds,
            "derivation_kind": request.derivation_kind,
            "relisten_index": request.relisten_index,
        }
    )


def _measure(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


class SliceReCutter:
    """The reference :class:`ReListenCutter`: ``obs-replay-loop``'s own re-cut.

    ``core.span_surgery.cut_span`` writes the widened span (the margin is
    already folded into the request's bounds, so ``pad_s`` is 0.0 here exactly
    as in ``reproduction.replay_loop._cut_replay_window``), the run's
    ``SliceRegistry`` chains the written file to the sample's registered parent
    media and re-measures both, and only then does ``encode_packet`` turn the
    chained :class:`~core.model.slices.SliceRecord` into the speech-feature
    packet the agent loop sends. Encoding needs the preprocessing encoder and
    is therefore injected, which is also what keeps this class runnable
    model-free.

    ``iteration_base`` offsets the slice iteration numbers so a run that also
    cut obs windows cannot collide with them; the agent loop cuts no obs
    windows, so 0 is correct there.
    """

    def __init__(
        self,
        *,
        registry: SliceRegistry,
        data_root: Path,
        encode_packet: Callable[[SliceRecord], tuple[str, str]],
        sample_rate_hz: int = 16000,
        iteration_base: int = 0,
    ) -> None:
        if not isinstance(registry, SliceRegistry):
            raise ObserveError(
                "SliceReCutter requires a core.model.SliceRegistry; refusing to cut "
                "unchained slices"
            )
        if not callable(encode_packet):
            raise ObserveError("SliceReCutter encode_packet must be callable")
        if (
            isinstance(iteration_base, bool)
            or not isinstance(iteration_base, int)
            or iteration_base < 0
        ):
            raise ObserveError("SliceReCutter iteration_base must be a non-negative int")
        self._registry = registry
        self._data_root = Path(data_root)
        self._encode_packet = encode_packet
        self._sample_rate_hz = sample_rate_hz
        self._iteration_base = iteration_base

    def __call__(self, request: ReListenRequest) -> ReListenResult:
        from ..core.span_surgery import SpanSurgeryError, cut_span  # noqa: PLC0415

        iteration = self._iteration_base + request.relisten_index
        relpath = self._registry.slice_relpath(request.sample_id, iteration)
        out_path = self._data_root / relpath
        out_path.parent.mkdir(parents=True, exist_ok=True)
        parent_path = self._data_root / request.parent_media_relpath
        try:
            cut_span(
                parent_path,
                request.start_seconds,
                request.end_seconds,
                0.0,
                out_path,
            )
        except SpanSurgeryError as error:
            raise ObserveError(
                f"re-listen cut failed for sample {request.sample_id!r}: {error}"
            ) from error
        cut_bytes, cut_sha256 = _measure(out_path)
        _, parent_sha256 = _measure(parent_path)
        # The cut's own rounding, mirrored from replay_loop._cut_replay_window
        # so the record's audio_seconds stays bit-exact with the file written.
        start_sample = int(round(request.start_seconds * self._sample_rate_hz))
        end_sample = int(round(request.end_seconds * self._sample_rate_hz))
        audio_seconds = (end_sample - start_sample) / self._sample_rate_hz
        record = SliceRecord(
            sample_id=request.sample_id,
            parent_media_relpath=request.parent_media_relpath,
            parent_sha256=parent_sha256,
            start_seconds=start_sample / self._sample_rate_hz,
            end_seconds=start_sample / self._sample_rate_hz + audio_seconds,
            audio_seconds=audio_seconds,
            sample_rate_hz=self._sample_rate_hz,
            media_relpath=relpath,
            sha256=cut_sha256,
            bytes=cut_bytes,
            iteration=iteration,
        )
        self._registry.register(record)
        packet = self._encode_packet(record)
        if (
            not isinstance(packet, tuple)
            or len(packet) != 2
        ):
            raise ObserveError(
                "SliceReCutter encode_packet must return a (packet_id, sha256) pair"
            )
        return ReListenResult(
            packet_id=packet[0],
            packet_sha256=packet[1],
            provenance={
                "media_relpath": record.media_relpath,
                "slice_sha256": record.sha256,
                "slice_bytes": record.bytes,
                "parent_media_relpath": record.parent_media_relpath,
                "parent_sha256": record.parent_sha256,
                "start_seconds": record.start_seconds,
                "end_seconds": record.end_seconds,
                "audio_seconds": record.audio_seconds,
                "iteration": record.iteration,
            },
        ).validate()


__all__ = [
    "OBSERVE_STEP_VERSION",
    "RELISTEN_PARAMS_VERSION",
    "FlagSource",
    "FlaggedSpan",
    "ObserveConfig",
    "ObserveError",
    "ObserveStep",
    "Observation",
    "ReListenCutter",
    "ReListenRequest",
    "ReListenResult",
    "ReviewFlags",
    "SliceReCutter",
    "fixture_flag_source",
    "relisten_params_hash",
]
