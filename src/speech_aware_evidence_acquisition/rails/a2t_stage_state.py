"""Canonical, hash-bound state carried between Audio2Tool workflows.

The envelope stores only canonical parsed state. It never stores a raw model
response, cumulative history, labels, references, or test annotations.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``build_select_stage_envelope`` is catalog id
``saea-tool-a2t-select-stage-envelope-v1`` on the ``ORG`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Mapping, Sequence


STAGE_STATE_SCHEMA = "a2t-stage-state-envelope-v2"
SELECT_STAGE = "SELECT"
JOINT_DRAFT_STAGE = "JOINT_DRAFT"
MIN_STAGE_CALLS = 1
MAX_STAGE_CALLS = 7
MAX_CANDIDATE_TOOLS = 32

_STAGES = frozenset({SELECT_STAGE, JOINT_DRAFT_STAGE})
_SHA256 = re.compile(r"[0-9a-f]{64}", flags=re.ASCII)
_TOOL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", flags=re.ASCII)
_OCCURRENCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", flags=re.ASCII)
_ENVELOPE_KEYS = frozenset(
    {
        "schema",
        "sample_identity_sha256",
        "split_identity_sha256",
        "speech_packet_sha256",
        "stage",
        "predecessor_envelope_sha256",
        "payload",
        "payload_sha256",
        "source_query_state_sha256",
        "source_response_sha256",
        "observation_state_sha256",
        "observation_source_response_sha256",
        "source_request_body_sha256",
        "candidate_set_sha256",
        "ground_sha256",
        "response_schema_sha256",
        "envelope_sha256",
    }
)
_FORBIDDEN_PAYLOAD_TOKENS = frozenset(
    {"gold", "reference", "test", "history"}
)


class StageStateError(ValueError):
    """Raised when a cross-workflow stage envelope is not exact and sealed."""


def _require_hash(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise StageStateError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_optional_hash(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    return _require_hash(value, field=field)


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise StageStateError("stage state must be canonical JSON data") from error


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _assert_ascii_json(value: object, *, path: str = "payload") -> None:
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StageStateError(f"{path} contains a non-finite number")
        return
    if isinstance(value, str):
        if not value.isascii():
            raise StageStateError(f"{path} must contain ASCII text only")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_ascii_json(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key.isascii():
                raise StageStateError(f"{path} object keys must be ASCII strings")
            _assert_ascii_json(item, path=f"{path}.{key}")
        return
    raise StageStateError(f"{path} contains a non-JSON value")


def _key_tokens(key: str) -> tuple[str, ...]:
    return tuple(token for token in re.split(r"[^a-z0-9]+", key.casefold()) if token)


def _is_forbidden_payload_key(key: str) -> bool:
    tokens = _key_tokens(key)
    if any(token in _FORBIDDEN_PAYLOAD_TOKENS for token in tokens):
        return True
    compact = "".join(tokens)
    return "rawresponse" in compact or (
        "raw" in tokens and "response" in tokens
    )


def _assert_no_forbidden_payload_keys(
    value: object, *, path: str = "payload"
) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_forbidden_payload_keys(item, path=f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            if _is_forbidden_payload_key(key):
                raise StageStateError(
                    f"{path}.{key} is a forbidden cross-workflow payload key"
                )
            _assert_no_forbidden_payload_keys(item, path=f"{path}.{key}")


def _require_exact_keys(
    value: object, expected: frozenset[str], *, field: str
) -> Mapping[str, object]:
    if not isinstance(value, dict) or frozenset(value) != expected:
        raise StageStateError(f"{field} has missing or extra keys")
    return value


def _candidate_binding(candidate_tool_names: Sequence[str]) -> tuple[tuple[str, ...], str]:
    if isinstance(candidate_tool_names, (str, bytes)):
        raise StageStateError("candidate tools must be a sequence")
    try:
        names = tuple(candidate_tool_names)
    except TypeError as error:
        raise StageStateError("candidate tools must be a sequence") from error
    if (
        not 1 <= len(names) <= MAX_CANDIDATE_TOOLS
        or len(names) != len(set(names))
        or any(not isinstance(name, str) or _TOOL_NAME.fullmatch(name) is None for name in names)
    ):
        raise StageStateError(
            "candidate tools must contain between 1 and 32 unique ASCII identifiers"
        )
    return names, _sha256(list(names))


def _validate_payload_candidates(
    payload: StagePayload, candidate_tool_names: Sequence[str]
) -> None:
    names, _binding = _candidate_binding(candidate_tool_names)
    if isinstance(payload, SelectPayload):
        payload_names = tuple(item.tool_name for item in payload.occurrences)
    else:
        payload_names = tuple(item.name for item in payload.calls)
    if not MIN_STAGE_CALLS <= len(payload_names) <= MAX_STAGE_CALLS:
        raise StageStateError("stage calls must contain between 1 and 7 occurrences")
    if not set(payload_names).issubset(names):
        raise StageStateError("stage call is outside the bound candidate set")


@dataclass(frozen=True)
class SelectOccurrence:
    """One ordered selector occurrence; tool names may repeat across occurrences."""

    occurrence_id: str
    tool_name: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.occurrence_id, str)
            or _OCCURRENCE_ID.fullmatch(self.occurrence_id) is None
        ):
            raise StageStateError("occurrence_id must be a non-empty ASCII identifier")
        if (
            not isinstance(self.tool_name, str)
            or _TOOL_NAME.fullmatch(self.tool_name) is None
        ):
            raise StageStateError("tool_name must be an exact ASCII identifier")

    def as_json(self) -> dict[str, str]:
        return {"occurrence_id": self.occurrence_id, "tool_name": self.tool_name}


@dataclass(frozen=True)
class SelectPayload:
    """The selector's canonical ordered occurrence sequence."""

    occurrences: tuple[SelectOccurrence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.occurrences, tuple) or any(
            not isinstance(item, SelectOccurrence) for item in self.occurrences
        ):
            raise StageStateError("SELECT occurrences must be an immutable tuple")
        occurrence_ids = tuple(item.occurrence_id for item in self.occurrences)
        if len(occurrence_ids) != len(set(occurrence_ids)):
            raise StageStateError("SELECT occurrence identifiers must be unique")

    def as_json(self) -> dict[str, object]:
        return {"occurrences": [item.as_json() for item in self.occurrences]}


@dataclass(frozen=True)
class JointDraftCall:
    """One exact draft call, storing arguments as immutable canonical JSON."""

    name: str
    arguments_json: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or _TOOL_NAME.fullmatch(self.name) is None:
            raise StageStateError("joint draft name must be an exact ASCII identifier")
        if not isinstance(self.arguments_json, str) or not self.arguments_json.isascii():
            raise StageStateError("joint draft arguments_json must be canonical ASCII JSON")
        arguments = _loads_strict(self.arguments_json)
        if not isinstance(arguments, dict):
            raise StageStateError("joint draft arguments must be one JSON object")
        _assert_ascii_json(arguments)
        _assert_no_forbidden_payload_keys(arguments)
        if self.arguments_json != _canonical_bytes(arguments).decode("ascii"):
            raise StageStateError("joint draft arguments_json must be canonical")

    @classmethod
    def from_arguments(
        cls, name: str, arguments: Mapping[str, object]
    ) -> "JointDraftCall":
        if not isinstance(arguments, Mapping):
            raise StageStateError("joint draft arguments must be one JSON object")
        copied = dict(arguments)
        _assert_ascii_json(copied)
        _assert_no_forbidden_payload_keys(copied)
        encoded = _canonical_bytes(copied).decode("ascii")
        return cls(name=name, arguments_json=encoded)

    @property
    def arguments(self) -> dict[str, object]:
        value = json.loads(self.arguments_json)
        if not isinstance(value, dict):  # pragma: no cover - constructor invariant
            raise AssertionError("sealed joint draft arguments must remain an object")
        return value

    def as_json(self) -> dict[str, object]:
        return {"name": self.name, "arguments": self.arguments}


@dataclass(frozen=True)
class JointDraftPayload:
    """The joint drafter's exact ordered call sequence."""

    calls: tuple[JointDraftCall, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.calls, tuple) or any(
            not isinstance(item, JointDraftCall) for item in self.calls
        ):
            raise StageStateError("JOINT_DRAFT calls must be an immutable tuple")

    def as_json(self) -> dict[str, object]:
        return {"calls": [item.as_json() for item in self.calls]}


StagePayload = SelectPayload | JointDraftPayload


@dataclass(frozen=True)
class StageStateEnvelope:
    """One self-verifying canonical state crossing a fresh workflow boundary."""

    sample_identity_sha256: str
    split_identity_sha256: str
    speech_packet_sha256: str
    stage: str
    predecessor_envelope_sha256: str | None
    payload: StagePayload
    payload_sha256: str
    source_query_state_sha256: str
    source_response_sha256: str
    observation_state_sha256: str
    observation_source_response_sha256: str
    source_request_body_sha256: str
    candidate_set_sha256: str
    ground_sha256: str
    response_schema_sha256: str
    envelope_sha256: str
    schema: str = STAGE_STATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != STAGE_STATE_SCHEMA:
            raise StageStateError("stage-state schema is unsupported")
        _require_hash(self.sample_identity_sha256, field="sample_identity_sha256")
        _require_hash(self.split_identity_sha256, field="split_identity_sha256")
        _require_hash(self.speech_packet_sha256, field="speech_packet_sha256")
        _require_hash(
            self.source_query_state_sha256,
            field="source_query_state_sha256",
        )
        _require_hash(self.source_response_sha256, field="source_response_sha256")
        _require_hash(self.observation_state_sha256, field="observation_state_sha256")
        _require_hash(
            self.observation_source_response_sha256,
            field="observation_source_response_sha256",
        )
        _require_hash(
            self.source_request_body_sha256,
            field="source_request_body_sha256",
        )
        _require_hash(self.candidate_set_sha256, field="candidate_set_sha256")
        _require_hash(self.ground_sha256, field="ground_sha256")
        _require_hash(self.response_schema_sha256, field="response_schema_sha256")
        _require_optional_hash(
            self.predecessor_envelope_sha256,
            field="predecessor_envelope_sha256",
        )
        _require_hash(self.payload_sha256, field="payload_sha256")
        _require_hash(self.envelope_sha256, field="envelope_sha256")
        if self.stage == SELECT_STAGE and not isinstance(self.payload, SelectPayload):
            raise StageStateError("SELECT stage requires a SelectPayload")
        if self.stage == JOINT_DRAFT_STAGE and not isinstance(
            self.payload, JointDraftPayload
        ):
            raise StageStateError("JOINT_DRAFT stage requires a JointDraftPayload")
        if self.stage not in _STAGES:
            raise StageStateError("stage must be SELECT or JOINT_DRAFT")
        if self.payload_sha256 != _sha256(self.payload.as_json()):
            raise StageStateError("payload hash does not match canonical payload")
        if self.envelope_sha256 != _sha256(self._body_json()):
            raise StageStateError("envelope hash does not match canonical envelope")

    def _body_json(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "sample_identity_sha256": self.sample_identity_sha256,
            "split_identity_sha256": self.split_identity_sha256,
            "speech_packet_sha256": self.speech_packet_sha256,
            "stage": self.stage,
            "predecessor_envelope_sha256": self.predecessor_envelope_sha256,
            "payload": self.payload.as_json(),
            "payload_sha256": self.payload_sha256,
            "source_query_state_sha256": self.source_query_state_sha256,
            "source_response_sha256": self.source_response_sha256,
            "observation_state_sha256": self.observation_state_sha256,
            "observation_source_response_sha256": (
                self.observation_source_response_sha256
            ),
            "source_request_body_sha256": self.source_request_body_sha256,
            "candidate_set_sha256": self.candidate_set_sha256,
            "ground_sha256": self.ground_sha256,
            "response_schema_sha256": self.response_schema_sha256,
        }

    def as_json(self) -> dict[str, object]:
        return {**self._body_json(), "envelope_sha256": self.envelope_sha256}

    def to_json(self) -> str:
        return _canonical_bytes(self.as_json()).decode("ascii")


def _build_envelope(
    *,
    sample_identity_sha256: str,
    split_identity_sha256: str,
    speech_packet_sha256: str,
    stage: str,
    predecessor_envelope_sha256: str | None,
    payload: StagePayload,
    source_query_state_sha256: str,
    source_response_sha256: str,
    observation_state_sha256: str,
    observation_source_response_sha256: str,
    source_request_body_sha256: str,
    candidate_tool_names: Sequence[str],
    ground_sha256: str,
    response_schema_sha256: str,
) -> StageStateEnvelope:
    _validate_payload_candidates(payload, candidate_tool_names)
    _candidate_names, candidate_set_sha256 = _candidate_binding(
        candidate_tool_names
    )
    payload_sha256 = _sha256(payload.as_json())
    body = {
        "schema": STAGE_STATE_SCHEMA,
        "sample_identity_sha256": sample_identity_sha256,
        "split_identity_sha256": split_identity_sha256,
        "speech_packet_sha256": speech_packet_sha256,
        "stage": stage,
        "predecessor_envelope_sha256": predecessor_envelope_sha256,
        "payload": payload.as_json(),
        "payload_sha256": payload_sha256,
        "source_query_state_sha256": source_query_state_sha256,
        "source_response_sha256": source_response_sha256,
        "observation_state_sha256": observation_state_sha256,
        "observation_source_response_sha256": observation_source_response_sha256,
        "source_request_body_sha256": source_request_body_sha256,
        "candidate_set_sha256": candidate_set_sha256,
        "ground_sha256": ground_sha256,
        "response_schema_sha256": response_schema_sha256,
    }
    return StageStateEnvelope(
        sample_identity_sha256=sample_identity_sha256,
        split_identity_sha256=split_identity_sha256,
        speech_packet_sha256=speech_packet_sha256,
        stage=stage,
        predecessor_envelope_sha256=predecessor_envelope_sha256,
        payload=payload,
        payload_sha256=payload_sha256,
        source_query_state_sha256=source_query_state_sha256,
        source_response_sha256=source_response_sha256,
        observation_state_sha256=observation_state_sha256,
        observation_source_response_sha256=observation_source_response_sha256,
        source_request_body_sha256=source_request_body_sha256,
        candidate_set_sha256=candidate_set_sha256,
        ground_sha256=ground_sha256,
        response_schema_sha256=response_schema_sha256,
        envelope_sha256=_sha256(body),
    )


def build_select_stage_envelope(
    *,
    sample_identity_sha256: str,
    split_identity_sha256: str,
    speech_packet_sha256: str,
    source_query_state_sha256: str,
    source_response_sha256: str,
    observation_state_sha256: str,
    observation_source_response_sha256: str,
    source_request_body_sha256: str,
    candidate_tool_names: Sequence[str],
    ground_sha256: str,
    response_schema_sha256: str,
    predecessor_envelope_sha256: str | None,
    occurrences: Sequence[SelectOccurrence],
) -> StageStateEnvelope:
    """Seal ordered SELECT occurrences while allowing repeated tool names."""

    if isinstance(occurrences, (str, bytes)):
        raise StageStateError("SELECT occurrences must be a sequence")
    try:
        payload = SelectPayload(tuple(occurrences))
    except TypeError as error:
        raise StageStateError("SELECT occurrences must be a sequence") from error
    return _build_envelope(
        sample_identity_sha256=sample_identity_sha256,
        split_identity_sha256=split_identity_sha256,
        speech_packet_sha256=speech_packet_sha256,
        stage=SELECT_STAGE,
        predecessor_envelope_sha256=predecessor_envelope_sha256,
        payload=payload,
        source_query_state_sha256=source_query_state_sha256,
        source_response_sha256=source_response_sha256,
        observation_state_sha256=observation_state_sha256,
        observation_source_response_sha256=observation_source_response_sha256,
        source_request_body_sha256=source_request_body_sha256,
        candidate_tool_names=candidate_tool_names,
        ground_sha256=ground_sha256,
        response_schema_sha256=response_schema_sha256,
    )


def build_joint_draft_stage_envelope(
    *,
    sample_identity_sha256: str,
    split_identity_sha256: str,
    speech_packet_sha256: str,
    source_query_state_sha256: str,
    source_response_sha256: str,
    observation_state_sha256: str,
    observation_source_response_sha256: str,
    source_request_body_sha256: str,
    candidate_tool_names: Sequence[str],
    ground_sha256: str,
    response_schema_sha256: str,
    predecessor_envelope_sha256: str | None,
    calls: Sequence[JointDraftCall],
) -> StageStateEnvelope:
    """Seal exact ordered JOINT_DRAFT calls without changing their arguments."""

    if isinstance(calls, (str, bytes)):
        raise StageStateError("JOINT_DRAFT calls must be a sequence")
    try:
        payload = JointDraftPayload(tuple(calls))
    except TypeError as error:
        raise StageStateError("JOINT_DRAFT calls must be a sequence") from error
    return _build_envelope(
        sample_identity_sha256=sample_identity_sha256,
        split_identity_sha256=split_identity_sha256,
        speech_packet_sha256=speech_packet_sha256,
        stage=JOINT_DRAFT_STAGE,
        predecessor_envelope_sha256=predecessor_envelope_sha256,
        payload=payload,
        source_query_state_sha256=source_query_state_sha256,
        source_response_sha256=source_response_sha256,
        observation_state_sha256=observation_state_sha256,
        observation_source_response_sha256=observation_source_response_sha256,
        source_request_body_sha256=source_request_body_sha256,
        candidate_tool_names=candidate_tool_names,
        ground_sha256=ground_sha256,
        response_schema_sha256=response_schema_sha256,
    )


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StageStateError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> object:
    raise StageStateError(f"non-finite JSON constant {value!r} is forbidden")


def _loads_strict(text: str) -> object:
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except StageStateError:
        raise
    except (TypeError, json.JSONDecodeError) as error:
        raise StageStateError("stage state must be one unfenced JSON object") from error


def _parse_select_payload(value: object) -> SelectPayload:
    _assert_no_forbidden_payload_keys(value)
    document = _require_exact_keys(value, frozenset({"occurrences"}), field="SELECT payload")
    occurrences = document["occurrences"]
    if not isinstance(occurrences, list):
        raise StageStateError("SELECT occurrences must be one JSON array")
    parsed: list[SelectOccurrence] = []
    for item in occurrences:
        row = _require_exact_keys(
            item,
            frozenset({"occurrence_id", "tool_name"}),
            field="SELECT occurrence",
        )
        parsed.append(
            SelectOccurrence(
                occurrence_id=row["occurrence_id"],  # type: ignore[arg-type]
                tool_name=row["tool_name"],  # type: ignore[arg-type]
            )
        )
    return SelectPayload(tuple(parsed))


def _parse_joint_draft_payload(value: object) -> JointDraftPayload:
    _assert_no_forbidden_payload_keys(value)
    document = _require_exact_keys(value, frozenset({"calls"}), field="JOINT_DRAFT payload")
    calls = document["calls"]
    if not isinstance(calls, list):
        raise StageStateError("JOINT_DRAFT calls must be one JSON array")
    parsed: list[JointDraftCall] = []
    for item in calls:
        row = _require_exact_keys(
            item,
            frozenset({"name", "arguments"}),
            field="JOINT_DRAFT call",
        )
        arguments = row["arguments"]
        if not isinstance(arguments, dict):
            raise StageStateError("joint draft arguments must be one JSON object")
        parsed.append(
            JointDraftCall.from_arguments(
                row["name"],  # type: ignore[arg-type]
                arguments,
            )
        )
    return JointDraftPayload(tuple(parsed))


def parse_stage_state_envelope(
    text: str,
    *,
    expected_sample_identity_sha256: str,
    expected_split_identity_sha256: str,
    expected_speech_packet_sha256: str,
    expected_stage: str,
    expected_predecessor_envelope_sha256: str | None,
    expected_source_query_state_sha256: str,
    expected_source_response_sha256: str,
    expected_observation_state_sha256: str,
    expected_observation_source_response_sha256: str,
    expected_source_request_body_sha256: str,
    expected_candidate_tool_names: Sequence[str],
    expected_ground_sha256: str,
    expected_response_schema_sha256: str,
) -> StageStateEnvelope:
    """Parse and verify one envelope against its expected workflow bindings."""

    if not isinstance(text, str) or not text or not text.isascii():
        raise StageStateError("stage envelope must be non-empty ASCII text")
    if "```" in text:
        raise StageStateError("stage envelope must not contain a JSON fence")
    value = _loads_strict(text)
    document = _require_exact_keys(value, _ENVELOPE_KEYS, field="stage envelope")
    _assert_ascii_json(document, path="envelope")

    schema = document["schema"]
    if schema != STAGE_STATE_SCHEMA:
        raise StageStateError("stage-state schema is unsupported")
    stage = document["stage"]
    if stage == SELECT_STAGE:
        payload = _parse_select_payload(document["payload"])
    elif stage == JOINT_DRAFT_STAGE:
        payload = _parse_joint_draft_payload(document["payload"])
    else:
        raise StageStateError("stage must be SELECT or JOINT_DRAFT")

    envelope = StageStateEnvelope(
        sample_identity_sha256=document["sample_identity_sha256"],  # type: ignore[arg-type]
        split_identity_sha256=document["split_identity_sha256"],  # type: ignore[arg-type]
        speech_packet_sha256=document["speech_packet_sha256"],  # type: ignore[arg-type]
        stage=stage,
        predecessor_envelope_sha256=document["predecessor_envelope_sha256"],  # type: ignore[arg-type]
        payload=payload,
        payload_sha256=document["payload_sha256"],  # type: ignore[arg-type]
        source_query_state_sha256=document["source_query_state_sha256"],  # type: ignore[arg-type]
        source_response_sha256=document["source_response_sha256"],  # type: ignore[arg-type]
        observation_state_sha256=document["observation_state_sha256"],  # type: ignore[arg-type]
        observation_source_response_sha256=document[
            "observation_source_response_sha256"
        ],  # type: ignore[arg-type]
        source_request_body_sha256=document["source_request_body_sha256"],  # type: ignore[arg-type]
        candidate_set_sha256=document["candidate_set_sha256"],  # type: ignore[arg-type]
        ground_sha256=document["ground_sha256"],  # type: ignore[arg-type]
        response_schema_sha256=document["response_schema_sha256"],  # type: ignore[arg-type]
        envelope_sha256=document["envelope_sha256"],  # type: ignore[arg-type]
        schema=schema,
    )
    if text != envelope.to_json():
        raise StageStateError("stage envelope bytes are not canonical")

    _require_hash(
        expected_sample_identity_sha256,
        field="expected_sample_identity_sha256",
    )
    _require_hash(
        expected_split_identity_sha256,
        field="expected_split_identity_sha256",
    )
    _require_hash(
        expected_speech_packet_sha256,
        field="expected_speech_packet_sha256",
    )
    _require_optional_hash(
        expected_predecessor_envelope_sha256,
        field="expected_predecessor_envelope_sha256",
    )
    _require_hash(
        expected_source_query_state_sha256,
        field="expected_source_query_state_sha256",
    )
    _require_hash(
        expected_source_response_sha256,
        field="expected_source_response_sha256",
    )
    _require_hash(
        expected_observation_state_sha256,
        field="expected_observation_state_sha256",
    )
    _require_hash(
        expected_observation_source_response_sha256,
        field="expected_observation_source_response_sha256",
    )
    _require_hash(
        expected_source_request_body_sha256,
        field="expected_source_request_body_sha256",
    )
    _candidate_names, expected_candidate_set_sha256 = _candidate_binding(
        expected_candidate_tool_names
    )
    _require_hash(expected_ground_sha256, field="expected_ground_sha256")
    _require_hash(
        expected_response_schema_sha256,
        field="expected_response_schema_sha256",
    )
    if expected_stage not in _STAGES:
        raise StageStateError("expected stage must be SELECT or JOINT_DRAFT")
    if envelope.sample_identity_sha256 != expected_sample_identity_sha256:
        raise StageStateError("sample identity binding does not match")
    if envelope.split_identity_sha256 != expected_split_identity_sha256:
        raise StageStateError("split identity binding does not match")
    if envelope.speech_packet_sha256 != expected_speech_packet_sha256:
        raise StageStateError("speech packet binding does not match")
    if envelope.stage != expected_stage:
        raise StageStateError("stage binding does not match")
    if (
        envelope.predecessor_envelope_sha256
        != expected_predecessor_envelope_sha256
    ):
        raise StageStateError("predecessor envelope binding does not match")
    if envelope.source_query_state_sha256 != expected_source_query_state_sha256:
        raise StageStateError("source query binding does not match")
    if envelope.source_response_sha256 != expected_source_response_sha256:
        raise StageStateError("source response binding does not match")
    if envelope.observation_state_sha256 != expected_observation_state_sha256:
        raise StageStateError("observation state binding does not match")
    if (
        envelope.observation_source_response_sha256
        != expected_observation_source_response_sha256
    ):
        raise StageStateError("observation source response binding does not match")
    if envelope.source_request_body_sha256 != expected_source_request_body_sha256:
        raise StageStateError("source request binding does not match")
    if envelope.candidate_set_sha256 != expected_candidate_set_sha256:
        raise StageStateError("candidate set binding does not match")
    if envelope.ground_sha256 != expected_ground_sha256:
        raise StageStateError("ground binding does not match")
    if envelope.response_schema_sha256 != expected_response_schema_sha256:
        raise StageStateError("response schema binding does not match")
    _validate_payload_candidates(envelope.payload, expected_candidate_tool_names)
    return envelope


__all__ = [
    "JOINT_DRAFT_STAGE",
    "SELECT_STAGE",
    "STAGE_STATE_SCHEMA",
    "JointDraftCall",
    "JointDraftPayload",
    "SelectOccurrence",
    "SelectPayload",
    "StageStateEnvelope",
    "StageStateError",
    "build_joint_draft_stage_envelope",
    "build_select_stage_envelope",
    "parse_stage_state_envelope",
]
