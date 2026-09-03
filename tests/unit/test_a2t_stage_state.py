"""Model-free tests for canonical Audio2Tool cross-workflow stage state."""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.a2t_stage_state import (
    JOINT_DRAFT_STAGE,
    SELECT_STAGE,
    STAGE_STATE_SCHEMA,
    JointDraftCall,
    JointDraftPayload,
    SelectOccurrence,
    SelectPayload,
    StageStateError,
    build_joint_draft_stage_envelope,
    build_select_stage_envelope,
    parse_stage_state_envelope,
)


SAMPLE = hashlib.sha256(b"dev:sample-001").hexdigest()
SPLIT = "1" * 64
SPEECH = "2" * 64
QUERY = "3" * 64
RESPONSE = "4" * 64
PREDECESSOR = "5" * 64
CANDIDATES = ("set_timer", "send_message", "get_weather")
GROUND = "6" * 64
SCHEMA = "7" * 64
OBS_STATE = "8" * 64
OBS_RESPONSE = "9" * 64
REQUEST_BODY = "a" * 64


def _select_envelope():
    return build_select_stage_envelope(
        sample_identity_sha256=SAMPLE,
        split_identity_sha256=SPLIT,
        speech_packet_sha256=SPEECH,
        source_query_state_sha256=QUERY,
        source_response_sha256=RESPONSE,
        observation_state_sha256=OBS_STATE,
        observation_source_response_sha256=OBS_RESPONSE,
        source_request_body_sha256=REQUEST_BODY,
        candidate_tool_names=CANDIDATES,
        ground_sha256=GROUND,
        response_schema_sha256=SCHEMA,
        predecessor_envelope_sha256=None,
        occurrences=(
            SelectOccurrence("occurrence-000", "set_timer"),
            SelectOccurrence("occurrence-001", "set_timer"),
            SelectOccurrence("occurrence-002", "send_message"),
        ),
    )


def _parse_select(text: str, **overrides: object):
    expected = {
        "expected_sample_identity_sha256": SAMPLE,
        "expected_split_identity_sha256": SPLIT,
        "expected_speech_packet_sha256": SPEECH,
        "expected_stage": SELECT_STAGE,
        "expected_predecessor_envelope_sha256": None,
        "expected_source_query_state_sha256": QUERY,
        "expected_source_response_sha256": RESPONSE,
        "expected_observation_state_sha256": OBS_STATE,
        "expected_observation_source_response_sha256": OBS_RESPONSE,
        "expected_source_request_body_sha256": REQUEST_BODY,
        "expected_candidate_tool_names": CANDIDATES,
        "expected_ground_sha256": GROUND,
        "expected_response_schema_sha256": SCHEMA,
    }
    expected.update(overrides)
    return parse_stage_state_envelope(text, **expected)


def test_select_round_trip_is_canonical_hash_bound_and_preserves_repeats() -> None:
    envelope = _select_envelope()
    encoded = envelope.to_json()
    parsed = _parse_select(encoded)

    assert encoded.isascii()
    assert encoded == parsed.to_json()
    assert parsed.payload_sha256 == hashlib.sha256(
        json.dumps(
            {
                "occurrences": [
                    {"occurrence_id": "occurrence-000", "tool_name": "set_timer"},
                    {"occurrence_id": "occurrence-001", "tool_name": "set_timer"},
                    {"occurrence_id": "occurrence-002", "tool_name": "send_message"},
                ]
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()
    assert isinstance(parsed.payload, SelectPayload)
    assert tuple(item.occurrence_id for item in parsed.payload.occurrences) == (
        "occurrence-000",
        "occurrence-001",
        "occurrence-002",
    )
    assert tuple(item.tool_name for item in parsed.payload.occurrences) == (
        "set_timer",
        "set_timer",
        "send_message",
    )


def test_joint_draft_round_trip_preserves_call_order_repeats_and_argument_values() -> None:
    envelope = build_joint_draft_stage_envelope(
        sample_identity_sha256=SAMPLE,
        split_identity_sha256=SPLIT,
        speech_packet_sha256=SPEECH,
        source_query_state_sha256=QUERY,
        source_response_sha256=RESPONSE,
        observation_state_sha256=OBS_STATE,
        observation_source_response_sha256=OBS_RESPONSE,
        source_request_body_sha256=REQUEST_BODY,
        candidate_tool_names=CANDIDATES,
        ground_sha256=GROUND,
        response_schema_sha256=SCHEMA,
        predecessor_envelope_sha256=PREDECESSOR,
        calls=(
            JointDraftCall.from_arguments(
                "set_timer",
                {"duration": "01", "enabled": True, "labels": ["b", "a"]},
            ),
            JointDraftCall.from_arguments(
                "set_timer",
                {"duration": 2.5, "metadata": {"z": 1, "a": None}},
            ),
        ),
    )

    parsed = parse_stage_state_envelope(
        envelope.to_json(),
        expected_sample_identity_sha256=SAMPLE,
        expected_split_identity_sha256=SPLIT,
        expected_speech_packet_sha256=SPEECH,
        expected_stage=JOINT_DRAFT_STAGE,
        expected_predecessor_envelope_sha256=PREDECESSOR,
        expected_source_query_state_sha256=QUERY,
        expected_source_response_sha256=RESPONSE,
        expected_observation_state_sha256=OBS_STATE,
        expected_observation_source_response_sha256=OBS_RESPONSE,
        expected_source_request_body_sha256=REQUEST_BODY,
        expected_candidate_tool_names=CANDIDATES,
        expected_ground_sha256=GROUND,
        expected_response_schema_sha256=SCHEMA,
    )

    assert isinstance(parsed.payload, JointDraftPayload)
    assert tuple(call.name for call in parsed.payload.calls) == (
        "set_timer",
        "set_timer",
    )
    assert parsed.payload.calls[0].arguments == {
        "duration": "01",
        "enabled": True,
        "labels": ["b", "a"],
    }
    assert parsed.payload.calls[1].arguments == {
        "duration": 2.5,
        "metadata": {"a": None, "z": 1},
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update({"extra": 1}), "keys"),
        (lambda value: value.pop("source_response_sha256"), "keys"),
        (lambda value: value.__setitem__("payload_sha256", "f" * 64), "payload hash"),
        (lambda value: value.__setitem__("envelope_sha256", "f" * 64), "envelope hash"),
    ],
)
def test_parser_rejects_extra_missing_and_hash_drift(mutation, message: str) -> None:
    document = json.loads(_select_envelope().to_json())
    mutation(document)
    tampered = json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    with pytest.raises(StageStateError, match=message):
        _parse_select(tampered)


def test_parser_rejects_duplicate_json_keys_at_every_depth() -> None:
    encoded = _select_envelope().to_json()
    duplicate_top = encoded.replace(
        f'"schema":"{STAGE_STATE_SCHEMA}"',
        f'"schema":"{STAGE_STATE_SCHEMA}","schema":"{STAGE_STATE_SCHEMA}"',
    )
    duplicate_nested = encoded.replace(
        '"occurrence_id":"occurrence-000"',
        '"occurrence_id":"occurrence-000","occurrence_id":"occurrence-000"',
    )

    for candidate in (duplicate_top, duplicate_nested):
        with pytest.raises(StageStateError, match="duplicate"):
            _parse_select(candidate)


@pytest.mark.parametrize(
    "candidate",
    [
        lambda text: f"```json\n{text}\n```",
        lambda text: text + " ",
        lambda text: text.replace("set_timer", "set_tim\u00e9r"),
    ],
)
def test_parser_rejects_fences_noncanonical_bytes_and_non_ascii(candidate) -> None:
    with pytest.raises(StageStateError):
        _parse_select(candidate(_select_envelope().to_json()))


@pytest.mark.parametrize(
    ("override", "value", "message"),
    [
        ("expected_sample_identity_sha256", "6" * 64, "sample"),
        ("expected_split_identity_sha256", "6" * 64, "split"),
        ("expected_speech_packet_sha256", "6" * 64, "speech"),
        ("expected_stage", JOINT_DRAFT_STAGE, "stage"),
        ("expected_predecessor_envelope_sha256", "6" * 64, "predecessor"),
        ("expected_source_query_state_sha256", "8" * 64, "source query"),
        ("expected_source_response_sha256", "8" * 64, "source response"),
        ("expected_observation_state_sha256", "b" * 64, "observation state"),
        (
            "expected_observation_source_response_sha256",
            "b" * 64,
            "observation source response",
        ),
        ("expected_source_request_body_sha256", "b" * 64, "source request"),
        ("expected_candidate_tool_names", ("other_tool",), "candidate"),
        ("expected_ground_sha256", "8" * 64, "ground"),
        ("expected_response_schema_sha256", "8" * 64, "response schema"),
    ],
)
def test_parser_rejects_wrong_expected_bindings(
    override: str, value: object, message: str
) -> None:
    with pytest.raises(StageStateError, match=message):
        _parse_select(_select_envelope().to_json(), **{override: value})


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "gold_label",
        "reference_transcript",
        "test_annotation",
        "raw_response_text",
        "chat_history",
    ],
)
def test_builder_and_parser_reject_forbidden_payload_keys(forbidden_key: str) -> None:
    with pytest.raises(StageStateError, match="forbidden"):
        JointDraftCall.from_arguments("set_timer", {forbidden_key: "leak"})

    document = json.loads(_select_envelope().to_json())
    document["payload"][forbidden_key] = "leak"
    payload_bytes = json.dumps(
        document["payload"], ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    document["payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    body = {key: value for key, value in document.items() if key != "envelope_sha256"}
    document["envelope_sha256"] = hashlib.sha256(
        json.dumps(body, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
            "ascii"
        )
    ).hexdigest()
    encoded = json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    with pytest.raises(StageStateError, match="forbidden"):
        _parse_select(encoded)


def test_builders_reject_invalid_hashes_occurrence_ids_and_mutable_arguments() -> None:
    with pytest.raises(StageStateError, match="sample_identity_sha256"):
        build_select_stage_envelope(
            sample_identity_sha256="BAD",
            split_identity_sha256=SPLIT,
            speech_packet_sha256=SPEECH,
            source_query_state_sha256=QUERY,
            source_response_sha256=RESPONSE,
            observation_state_sha256=OBS_STATE,
            observation_source_response_sha256=OBS_RESPONSE,
            source_request_body_sha256=REQUEST_BODY,
            candidate_tool_names=CANDIDATES,
            ground_sha256=GROUND,
            response_schema_sha256=SCHEMA,
            predecessor_envelope_sha256=None,
            occurrences=(SelectOccurrence("occurrence-000", "set_timer"),),
        )
    with pytest.raises(StageStateError, match="occurrence"):
        build_select_stage_envelope(
            sample_identity_sha256=SAMPLE,
            split_identity_sha256=SPLIT,
            speech_packet_sha256=SPEECH,
            source_query_state_sha256=QUERY,
            source_response_sha256=RESPONSE,
            observation_state_sha256=OBS_STATE,
            observation_source_response_sha256=OBS_RESPONSE,
            source_request_body_sha256=REQUEST_BODY,
            candidate_tool_names=CANDIDATES,
            ground_sha256=GROUND,
            response_schema_sha256=SCHEMA,
            predecessor_envelope_sha256=None,
            occurrences=(
                SelectOccurrence("occurrence-000", "set_timer"),
                SelectOccurrence("occurrence-000", "set_timer"),
            ),
        )
    source = {"value": [1, 2]}
    call = JointDraftCall.from_arguments("set_timer", source)
    source["value"].append(3)
    assert call.arguments == {"value": [1, 2]}


def test_stage_boundary_rejects_empty_too_many_and_out_of_candidate_calls() -> None:
    for occurrences, message in (
        ((), "between 1 and 7"),
        (
            tuple(SelectOccurrence(f"occurrence-{index:03d}", "set_timer") for index in range(8)),
            "between 1 and 7",
        ),
        ((SelectOccurrence("occurrence-000", "outside_tool"),), "candidate"),
    ):
        with pytest.raises(StageStateError, match=message):
            build_select_stage_envelope(
                sample_identity_sha256=SAMPLE,
                split_identity_sha256=SPLIT,
                speech_packet_sha256=SPEECH,
                source_query_state_sha256=QUERY,
                source_response_sha256=RESPONSE,
                observation_state_sha256=OBS_STATE,
                observation_source_response_sha256=OBS_RESPONSE,
                source_request_body_sha256=REQUEST_BODY,
                candidate_tool_names=CANDIDATES,
                ground_sha256=GROUND,
                response_schema_sha256=SCHEMA,
                predecessor_envelope_sha256=None,
                occurrences=occurrences,
            )


def test_parsed_argument_views_cannot_mutate_the_sealed_envelope() -> None:
    call = JointDraftCall.from_arguments("set_timer", {"nested": {"value": 1}})
    first = call.arguments
    first["nested"]["value"] = 2

    assert call.arguments == {"nested": {"value": 1}}
