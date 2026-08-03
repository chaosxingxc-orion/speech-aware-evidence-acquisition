"""Fail-closed E0 engineering contracts.

Model-free contracts frozen by the owner execution contract
(``AAEA-OWNER-GO-EXECUTION-CONTRACT-2026-08-03``): the runtime information boundary,
OBS/SUPPLY trace separation, exposure-claim schema, and the frozen-core entry gate.
Everything here is standard-library only so the contracts are testable before any ML
stack is installed and before any model is touched.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


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

TRACE_CHANNELS = ("OBS", "SUPPLY", "MODEL_REQUEST", "MODEL_RESPONSE", "TOOL", "COST")
_CHANNEL_PREFIX = {"OBS": "obs_", "SUPPLY": "supply_"}
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_BUILD_COMMIT = re.compile(r"[0-9a-f]{7,40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class BoundaryViolation(ValueError):
    """A payload tries to move gold/reference/test/future information across the runtime boundary."""


class TraceContractError(ValueError):
    """A trace record violates the OBS/SUPPLY separation or serializability contract."""


class ExposureSchemaError(ValueError):
    """An exposure claim does not carry the four required fields in the required shapes."""


class GateClosed(RuntimeError):
    """The frozen-core entry gate refuses: E0 closure or the runtime receipt is missing/invalid."""


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
    """One versioned trace event; payload keys are namespaced per channel."""

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
        for key in self.payload:
            if not isinstance(key, str):
                raise TraceContractError(f"non-string payload key {key!r}")
            if prefix is not None and not key.startswith(prefix):
                raise TraceContractError(
                    f"{self.channel} payload key {key!r} must start with {prefix!r} "
                    "(OBS and SUPPLY namespaces are disjoint by contract)"
                )
            other = "supply_" if prefix == "obs_" else "obs_"
            if prefix is not None and key.startswith(other):
                raise TraceContractError(f"{self.channel} payload smuggles {other}* field {key!r}")
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


@dataclass(frozen=True)
class FrozenCoreGate:
    """Fail-closed entry gate in front of every frozen-core (model) touch.

    The gate opens only when the E0 closure receipt (D1-D4 all CLOSED) and the runtime
    receipt (llama.cpp build commit + per-file GGUF sha256) both exist and validate.
    Any missing file, malformed JSON, or incomplete field refuses the touch.
    """

    e0_receipt: Path
    runtime_receipt: Path

    E0_DELIVERABLES = ("d1_identity", "d2_leakage", "d3_scoring", "d4_trace")

    def _load(self, path: Path, label: str) -> Mapping[str, object]:
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise GateClosed(f"{label} missing or unreadable ({path}): {error}") from error
        if not isinstance(document, Mapping):
            raise GateClosed(f"{label} must be a JSON object ({path})")
        return document

    def assert_model_touch_allowed(self) -> None:
        e0 = self._load(self.e0_receipt, "E0 closure receipt")
        for deliverable in self.E0_DELIVERABLES:
            if e0.get(deliverable) != "CLOSED":
                raise GateClosed(
                    f"E0 deliverable {deliverable} is not CLOSED "
                    f"(found {e0.get(deliverable)!r}); model touch refused"
                )
        runtime = self._load(self.runtime_receipt, "runtime receipt")
        commit = runtime.get("llama_cpp_build_commit")
        if not isinstance(commit, str) or _BUILD_COMMIT.fullmatch(commit) is None:
            raise GateClosed("runtime receipt lacks a valid llama_cpp_build_commit")
        files = runtime.get("gguf_files")
        if not isinstance(files, list) or not files:
            raise GateClosed("runtime receipt lacks a non-empty gguf_files list")
        for index, entry in enumerate(files):
            if (
                not isinstance(entry, Mapping)
                or not isinstance(entry.get("path"), str)
                or not entry.get("path")
                or not isinstance(entry.get("sha256"), str)
                or _SHA256.fullmatch(entry["sha256"]) is None
            ):
                raise GateClosed(f"runtime receipt gguf_files[{index}] lacks path/sha256")
