"""Runtime information boundary, OBS/ORG/SUPPLY/USE trace separation and the
exposure-claim schema.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Mapping

from .errors import BoundaryViolation, ExposureSchemaError, TraceContractError

FORBIDDEN_RUNTIME_FIELDS = frozenset(
    {
        "gold",
        "gold_answer",
        "gold_label",
        "gold_transcript",
        "reference",
        "reference_transcript",
        "reference_answer",
        "test_annotation",
        "test_label",
        "answer_key",
        "future_turn",
        "future_turns",
    }
)

TRACE_CHANNELS = (
    "OBS",
    "ORG",
    "SUPPLY",
    "USE",
    "MODEL_REQUEST",
    "MODEL_RESPONSE",
    # Decode-confidence channel (2026-09-08 logprob-as-judge probe): the raw
    # per-token distribution the frozen core returned for ONE request, hashed
    # like every other record and emitted only when that request actually
    # asked for it (``decoding_params.logprobs``). It is deliberately its own
    # channel rather than a MODEL_RESPONSE field: every sealed run that never
    # asked for logprobs keeps a byte-identical MODEL_RESPONSE record and a
    # byte-identical trace manifest. Like MODEL_REQUEST/MODEL_RESPONSE/TOOL/
    # COST it carries no research-axis prefix (_CHANNEL_PREFIX below), because
    # a decode-confidence signal is core provenance, not an OBS/ORG/SUPPLY/USE
    # observation -- what a Reviewer judge later DERIVES from it is.
    "MODEL_LOGPROBS",
    # Opt-in exact HTTP response provenance; absent from historical runs.
    "MODEL_WIRE_RESPONSE",
    "TOOL",
    "COST",
    # obs-replay-loop policy (reproduction.replay_loop): a fifth research-axis
    # channel for the listen-score-replay splice decision -- span/candidate
    # provenance and the accept/reject verdict. "Mirror OBS record
    # conventions" (the policy's own design brief): namespaced exactly like
    # OBS/ORG/SUPPLY/USE below, never sharing their prefix.
    "REPLAY",
    # The Reviewer seat of the four-agent loop (owner Decision 11-B/11-C,
    # 2026-09-08; ``rails.phase_review``): one record per reviewed row
    # carrying the judges' typed verdicts -- score, flags with their span and
    # field references, reasons. A sixth research-axis channel for the same
    # reason REPLAY is a fifth: a review verdict is neither an observation,
    # an organization, a supply nor a use, and folding it into one of those
    # namespaces would make two authorities for one decision. Criticism only
    # by construction: ``core.base.JudgeVerdict`` cannot carry replacement
    # text, so a REVIEW record cannot either.
    "REVIEW",
)
_CHANNEL_PREFIX = {
    "OBS": "obs_",
    "ORG": "org_",
    "SUPPLY": "supply_",
    "USE": "use_",
    "REPLAY": "replay_",
    "REVIEW": "review_",
}
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def assert_information_boundary(payload: object, _path: str = "$") -> None:
    """Recursively reject any forbidden field name anywhere in a runtime-bound payload.

    Fail-closed: the top-level payload must be a mapping, and unknown container types
    are rejected rather than skipped.
    """

    if _path == "$" and not isinstance(payload, Mapping):
        raise BoundaryViolation(f"runtime payload must be a mapping, got {type(payload).__name__}")
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if not isinstance(key, str):
                raise BoundaryViolation(f"{_path}: non-string key {key!r}")
            if key.lower() in FORBIDDEN_RUNTIME_FIELDS:
                raise BoundaryViolation(f"{_path}.{key}: forbidden field crosses the boundary")
            assert_information_boundary(value, f"{_path}.{key}")
    elif isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            assert_information_boundary(item, f"{_path}[{index}]")
    elif payload is not None and not isinstance(payload, (str, int, float, bool)):
        raise BoundaryViolation(f"{_path}: unserializable value type {type(payload).__name__}")


@dataclass(frozen=True)
class TraceRecord:
    """One versioned trace event; research-axis payload keys are namespaced per channel."""

    channel: str
    record_id: str
    payload: Mapping[str, object]

    def validate(self) -> "TraceRecord":
        if self.channel not in TRACE_CHANNELS:
            raise TraceContractError(f"unknown trace channel {self.channel!r}")
        if not self.record_id or not isinstance(self.record_id, str):
            raise TraceContractError("record_id must be a non-empty string")
        if not isinstance(self.payload, Mapping):
            raise TraceContractError("payload must be a mapping")
        prefix = _CHANNEL_PREFIX.get(self.channel)
        axis_prefixes = tuple(_CHANNEL_PREFIX.values())
        for key in self.payload:
            if not isinstance(key, str):
                raise TraceContractError(f"non-string payload key {key!r}")
            if prefix is not None and not key.startswith(prefix):
                raise TraceContractError(
                    f"{self.channel} payload key {key!r} must start with {prefix!r} "
                    "(OBS, ORG, SUPPLY and USE namespaces are disjoint by contract)"
                )
            other_prefixes = tuple(candidate for candidate in axis_prefixes if candidate != prefix)
            if prefix is not None and key.startswith(other_prefixes):
                raise TraceContractError(
                    f"{self.channel} payload smuggles another research-axis field {key!r}"
                )
        assert_information_boundary(dict(self.payload))
        return self

    def serialize(self) -> str:
        self.validate()
        try:
            return json.dumps(
                {
                    "channel": self.channel,
                    "record_id": self.record_id,
                    "payload": self.payload,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=_reject_unserializable,
            )
        except TypeError as error:
            raise TraceContractError(f"payload is not JSON-serializable: {error}") from error

    def content_hash(self) -> str:
        return hashlib.sha256(self.serialize().encode("utf-8")).hexdigest()


def _reject_unserializable(value: object) -> object:
    raise TypeError(f"unserializable trace value of type {type(value).__name__}")


EXPOSURE_FIELDS = ("scope", "date", "counts", "inherited")


def validate_exposure_claim(claim: Mapping[str, object]) -> Mapping[str, object]:
    """Validate the four-field exposure claim contract (scope/date/counts/inherited)."""

    if not isinstance(claim, Mapping):
        raise ExposureSchemaError("exposure claim must be a mapping")
    if set(claim) != set(EXPOSURE_FIELDS):
        raise ExposureSchemaError(
            f"exposure claim must have exactly the fields {EXPOSURE_FIELDS}, got {sorted(claim)}"
        )
    if not isinstance(claim["scope"], str) or not claim["scope"].strip():
        raise ExposureSchemaError("scope must be a non-empty string")
    if not isinstance(claim["date"], str) or _DATE.fullmatch(claim["date"]) is None:
        raise ExposureSchemaError("date must be YYYY-MM-DD")
    counts = claim["counts"]
    if not isinstance(counts, Mapping) or not counts:
        raise ExposureSchemaError("counts must be a non-empty mapping")
    for key, value in counts.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int):
            raise ExposureSchemaError(f"counts[{key!r}] must be an integer")
        if value < 0:
            raise ExposureSchemaError(f"counts[{key!r}] must be >= 0")
    if not isinstance(claim["inherited"], str) or not claim["inherited"].strip():
        raise ExposureSchemaError(
            "inherited must be a non-empty statement of inherited prior exposure"
        )
    return claim
