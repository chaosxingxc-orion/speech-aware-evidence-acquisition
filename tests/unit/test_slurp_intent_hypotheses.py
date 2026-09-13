from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.phase_material import (
    PHASE_STATE_FILLS,
    PhaseMaterialSpec,
    build_material_for_phase,
)
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    HYPOTHESIS_SEMANTICS,
    HYPOTHESIS_STATE_SCHEMA,
    SlurpIntentHypothesisError,
    SlurpIntentHypothesisStateFill,
    parse_slurp_intent_hypothesis_state,
)

LEGAL = frozenset({"weather_query", "transport_taxi", "calendar_set"})
SAMPLE_ID = "slurp:devel:0001"


def _payload(*, candidates=None, **overrides):
    document = {
        "schema": HYPOTHESIS_STATE_SCHEMA,
        "semantics": HYPOTHESIS_SEMANTICS,
        "sample_id": SAMPLE_ID,
        "candidates": candidates
        or [
            {
                "intent_id": "weather_query",
                "distinction": "Asks for weather at a location.",
                "evidence_refs": ["speech:full-utterance"],
                "unresolved_fields": ["location"],
            },
            {
                "intent_id": "transport_taxi",
                "distinction": "Requests a taxi to a destination.",
                "evidence_refs": ["speech:full-utterance"],
                "unresolved_fields": ["destination"],
            },
        ],
    }
    document.update(overrides)
    return document


def _state(payload=None):
    content = json.dumps(payload or _payload(), ensure_ascii=False, sort_keys=True)
    return AgentStateArtifact(
        state_id=f"hypotheses:{SAMPLE_ID}",
        state_kind="phase:hypotheses",
        content=content,
        source_query_state_sha256="1" * 64,
        source_response_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        producer_policy_id="phase-joint-intent-v1",
        cited_value_ids=(),
    ).validate()


def test_source_bound_ranked_alternatives_parse_and_render_in_order():
    parsed = parse_slurp_intent_hypothesis_state(
        _state(), expected_sample_id=SAMPLE_ID, legal_intent_ids=LEGAL, max_candidates=3
    )
    assert [candidate.intent_id for candidate in parsed.candidates] == [
        "weather_query", "transport_taxi"
    ]
    rendered = SlurpIntentHypothesisStateFill(
        legal_intent_ids=LEGAL, max_candidates=3
    ).render_state(_state(), sample_id=SAMPLE_ID)
    assert rendered.index("weather_query") < rendered.index("transport_taxi")
    assert "ranked alternatives" in rendered
    assert "not multiple task outputs" in rendered
    assert "Model-proposed and unverified" in rendered
    assert "confidence" not in rendered


def test_single_candidate_is_valid_for_n1_controls():
    payload = _payload(candidates=[_payload()["candidates"][0]])
    parsed = parse_slurp_intent_hypothesis_state(
        _state(payload),
        expected_sample_id=SAMPLE_ID,
        legal_intent_ids=LEGAL,
        max_candidates=1,
    )
    assert [candidate.intent_id for candidate in parsed.candidates] == [
        "weather_query"
    ]


@pytest.mark.parametrize(
    "content",
    [
        '{"schema":"saea-slurp-intent-hypotheses-v1",'
        '"schema":"saea-slurp-intent-hypotheses-v1",'
        '"semantics":"ranked-mutually-exclusive-intent-alternatives",'
        '"sample_id":"slurp:devel:0001","candidates":[]}',
        '{"schema":"saea-slurp-intent-hypotheses-v1",'
        '"semantics":"ranked-mutually-exclusive-intent-alternatives",'
        '"sample_id":"slurp:devel:0001","candidates":[{'
        '"intent_id":"weather_query","intent_id":"transport_taxi",'
        '"distinction":"x","evidence_refs":[],"unresolved_fields":[]}]}',
    ],
)
def test_duplicate_json_object_keys_are_rejected(content):
    state = AgentStateArtifact(
        state_id=f"hypotheses:{SAMPLE_ID}",
        state_kind="phase:hypotheses",
        content=content,
        source_query_state_sha256="1" * 64,
        source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="phase-joint-intent-v1",
        cited_value_ids=(),
    ).validate()
    with pytest.raises(SlurpIntentHypothesisError, match="duplicate JSON key"):
        parse_slurp_intent_hypothesis_state(
            state,
            expected_sample_id=SAMPLE_ID,
            legal_intent_ids=LEGAL,
            max_candidates=3,
        )


@pytest.mark.parametrize(
    "payload, match",
    [
        (_payload(semantics="requested-calls"), "semantics"),
        (_payload(candidates=[_payload()["candidates"][0]] * 2), "unique"),
        (_payload(candidates=[
            _payload()["candidates"][0],
            {"intent_id": "illegal_action", "distinction": "Not legal.",
             "evidence_refs": [], "unresolved_fields": []},
        ]), "legal"),
        (_payload(sample_id="slurp:devel:foreign"), "sample_id"),
    ],
)
def test_hypothesis_state_rejects_wrong_semantics_duplicates_illegal_or_foreign(payload, match):
    with pytest.raises(SlurpIntentHypothesisError, match=match):
        parse_slurp_intent_hypothesis_state(
            _state(payload), expected_sample_id=SAMPLE_ID,
            legal_intent_ids=LEGAL, max_candidates=3
        )


def test_hypothesis_state_enforces_supplied_max_and_response_binding():
    three = list(_payload()["candidates"]) + [{
        "intent_id": "calendar_set",
        "distinction": "Creates a calendar entry.",
        "evidence_refs": [],
        "unresolved_fields": ["date"],
    }]
    with pytest.raises(SlurpIntentHypothesisError, match="at most 2"):
        parse_slurp_intent_hypothesis_state(
            _state(_payload(candidates=three)), expected_sample_id=SAMPLE_ID,
            legal_intent_ids=LEGAL, max_candidates=2
        )
    tampered = replace(_state(), source_response_sha256="b" * 64)
    with pytest.raises(SlurpIntentHypothesisError, match="source response"):
        parse_slurp_intent_hypothesis_state(
            tampered, expected_sample_id=SAMPLE_ID,
            legal_intent_ids=LEGAL, max_candidates=3
        )


def test_phase_material_passes_full_artifact_only_to_registered_hypothesis_fill():
    specs = {
        "hypotheses": PhaseMaterialSpec(
            phase="hypotheses", purpose="retain alternatives",
            instruction_template="probes/unused.txt"
        ).validate(),
        "joint": PhaseMaterialSpec(
            phase="joint", purpose="jointly resolve",
            instruction_template="probes/unused.txt",
            predecessor_binding="append-sealed-state",
            state_fill="slurp-intent-hypotheses-for-joint-resolution-v1",
        ).validate(),
    }
    fill = SlurpIntentHypothesisStateFill(legal_intent_ids=LEGAL, max_candidates=3)
    material_for_phase = build_material_for_phase(
        specs, program_id="phase-joint-intent-v1",
        static_text_by_phase={"hypotheses": "Retain alternatives.", "joint": "Resolve."},
        response_format_by_phase={}, state_fill_by_phase={"joint": fill}
    )
    material = material_for_phase(
        "joint", SimpleNamespace(sample_id=SAMPLE_ID), {SAMPLE_ID: _state()}
    )
    assert "ranked alternatives" in material.instruction
    assert PHASE_STATE_FILLS.resolve("slurp-intent-hypotheses-for-joint-resolution-v1")
