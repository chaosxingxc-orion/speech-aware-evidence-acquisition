"""ObsPacket: the OBS-axis pipeline contract (typed, versioned, content-hashable).

Scope note (owner ruling, 2026-08-17): multi-view speech embeddings
(content/speaker/core-perception encoder views) are OUT of this study's
scope -- deferred whole to a future memory-focused study. ``ObsPacket``
therefore carries no ``views`` field and no encoder-view extension point;
this is a deliberate, clean absence, not a stub or a TODO. Nothing in this
module imports an encoder, embedding library, or vector type.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

from .errors import RailsError
from .hashing import content_hash

if TYPE_CHECKING:
    from .task_adapter import TaskSample

OBS_PACKET_VERSION = "obs-packet-v1"
FULL_SPAN_ID = "full"

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class AudioRef:
    """One audio file's identity: a repo/data-root-relative path plus its
    content sha256 -- the same ``(path, hash)`` shape every other identity
    record in this study uses (e.g. ``data.identity.FileFact``), kept
    independent here rather than importing that dataclass directly so the
    rails layer carries no hard dependency on the carrier-loader package."""

    path: str
    sha256: str

    def validate(self) -> "AudioRef":
        if not isinstance(self.path, str) or not self.path:
            raise RailsError("AudioRef.path must be a non-empty string")
        if not isinstance(self.sha256, str) or _SHA256_HEX.fullmatch(self.sha256) is None:
            raise RailsError(f"AudioRef.sha256 must be a 64-hex sha256, got {self.sha256!r}")
        return self

    def as_json(self) -> dict[str, object]:
        return {"path": self.path, "sha256": self.sha256}

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "AudioRef":
        return cls(path=document["path"], sha256=document["sha256"]).validate()


@dataclass(frozen=True)
class SpanRef:
    """One observed time span within an ``ObsPacket``'s audio, in seconds."""

    span_id: str
    start_seconds: float
    end_seconds: float

    def validate(self) -> "SpanRef":
        if not isinstance(self.span_id, str) or not self.span_id:
            raise RailsError("SpanRef.span_id must be a non-empty string")
        for label, value in (("start_seconds", self.start_seconds), ("end_seconds", self.end_seconds)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise RailsError(f"SpanRef.{label} must be a non-negative number, got {value!r}")
        if self.end_seconds <= self.start_seconds:
            raise RailsError(
                f"SpanRef {self.span_id!r} end_seconds ({self.end_seconds}) must be strictly "
                f"after start_seconds ({self.start_seconds})"
            )
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "span_id": self.span_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "SpanRef":
        return cls(
            span_id=document["span_id"],
            start_seconds=document["start_seconds"],
            end_seconds=document["end_seconds"],
        ).validate()


@dataclass(frozen=True)
class ObsPacket:
    """OBS-axis contract: what was observed of the audio, before any
    evidence is supplied. ``first_pass`` is the frozen core's own first-pass
    hypothesis text when one exists; every engineering-only construction in
    this mission (no model contact) leaves it ``None`` -- a real run fills
    it in post-request, this module never guesses it."""

    audio_ref: AudioRef
    spans: tuple[SpanRef, ...]
    first_pass: str | None
    obs_version: str = OBS_PACKET_VERSION

    def validate(self) -> "ObsPacket":
        self.audio_ref.validate()
        if not isinstance(self.spans, tuple):
            raise RailsError("ObsPacket.spans must be a tuple")
        seen_ids: set[str] = set()
        for span in self.spans:
            if not isinstance(span, SpanRef):
                raise RailsError("ObsPacket.spans entries must be SpanRef instances")
            span.validate()
            if span.span_id in seen_ids:
                raise RailsError(f"ObsPacket.spans has a duplicate span_id {span.span_id!r}")
            seen_ids.add(span.span_id)
        if self.first_pass is not None and not isinstance(self.first_pass, str):
            raise RailsError("ObsPacket.first_pass must be a string or None")
        if not isinstance(self.obs_version, str) or not self.obs_version:
            raise RailsError("ObsPacket.obs_version must be a non-empty string")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "audio_ref": self.audio_ref.as_json(),
            "spans": [span.as_json() for span in self.spans],
            "first_pass": self.first_pass,
            "obs_version": self.obs_version,
        }

    def content_hash(self) -> str:
        return content_hash(self.validate().as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "ObsPacket":
        return cls(
            audio_ref=AudioRef.from_json(document["audio_ref"]),
            spans=tuple(SpanRef.from_json(span) for span in document.get("spans", [])),
            first_pass=document.get("first_pass"),
            obs_version=document.get("obs_version", OBS_PACKET_VERSION),
        ).validate()


def default_obs_packet(sample: "TaskSample") -> ObsPacket:
    """The default, whole-file ``ObsPacket`` any ``TaskAdapter`` can reuse
    from its own ``build_task_contract``, or that the rails runner builds when an
    adapter has no reason to construct a custom one: one span covering the
    full sample duration, no first-pass hypothesis. ``sample`` is duck-typed
    against ``rails.task_adapter.TaskSample`` (``sample_id``/``audio_ref``/
    ``audio_seconds``) rather than imported at runtime, to avoid a circular
    import between this module and ``task_adapter`` (``TYPE_CHECKING``-only
    import above)."""

    return ObsPacket(
        audio_ref=sample.audio_ref,
        spans=(SpanRef(span_id=FULL_SPAN_ID, start_seconds=0.0, end_seconds=sample.audio_seconds),),
        first_pass=None,
    ).validate()
