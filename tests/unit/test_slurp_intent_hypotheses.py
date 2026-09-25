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
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
    DEFAULT_FALLBACK_DISTINCTION,
    FALLBACK_CANDIDATE_SOURCE,
    FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
    HYPOTHESIS_SEMANTICS,
    HYPOTHESIS_STATE_SCHEMA,
    MAX_FALLBACK_CANDIDATES,
    MODEL_CANDIDATE_SOURCE,
    SlurpIntentHypothesisCandidate,
    SlurpIntentHypothesisError,
    SlurpIntentHypothesisStateFill,
    append_fallback_slurp_intent_hypothesis_candidates,
    parse_slurp_intent_hypothesis_state,
    project_fixed_three_slurp_intent_hypotheses,
    project_bounded_slurp_intent_hypotheses,
    validate_fallback_candidate_ids,
    validate_fallback_distinction,
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


def _compact_response(*candidates):
    return json.dumps({"candidates": list(candidates)}, ensure_ascii=False)


@pytest.mark.parametrize(
    "raw_ids,expected_ids,projected_positions",
    [
        (("weather_query",) * 3, ("weather_query",), (1, 1, 1)),
        (
            ("weather_query", "transport_taxi", "weather_query"),
            ("weather_query", "transport_taxi"),
            (1, 2, 1),
        ),
        (
            ("weather_query", "transport_taxi", "calendar_set"),
            ("weather_query", "transport_taxi", "calendar_set"),
            (1, 2, 3),
        ),
    ],
)
def test_fixed_three_first_occurrence_projection_supports_widths_one_to_three(
    raw_ids, expected_ids, projected_positions
):
    by_id = {
        candidate["intent_id"]: candidate for candidate in _payload()["candidates"]
    }
    by_id["calendar_set"] = {
        "intent_id": "calendar_set",
        "distinction": "Creates a calendar entry.",
        "evidence_refs": [],
        "unresolved_fields": ["date"],
    }
    raw = _compact_response(*(by_id[intent_id] for intent_id in raw_ids))

    result = project_fixed_three_slurp_intent_hypotheses(
        raw, sample_id=SAMPLE_ID, legal_intent_ids=LEGAL
    )

    projected = json.loads(result.content)
    assert tuple(row["intent_id"] for row in projected["candidates"]) == expected_ids
    assert tuple(row.raw_position for row in result.raw_positions) == (1, 2, 3)
    assert tuple(row.projected_position for row in result.raw_positions) == projected_positions
    assert result.projection_policy_id == FIRST_OCCURRENCE_PROJECTION_POLICY_ID
    assert result.projection_policy_sha256 == FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256
    assert len(result.projection_policy_sha256) == 64
    assert result.original_text_sha256 == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert result.projected_content_sha256 == hashlib.sha256(
        result.content.encode("utf-8")
    ).hexdigest()


def test_projection_retains_the_exact_first_object_and_binds_every_raw_position():
    first = _payload()["candidates"][0]
    later_duplicate = {
        **first,
        "distinction": "A later duplicate that must not replace the first.",
        "evidence_refs": ["speech:later"],
    }
    taxi = _payload()["candidates"][1]
    raw = _compact_response(first, later_duplicate, taxi)

    result = project_fixed_three_slurp_intent_hypotheses(
        raw, sample_id=SAMPLE_ID, legal_intent_ids=LEGAL
    )

    candidates = json.loads(result.content)["candidates"]
    assert candidates == [first, taxi]
    assert result.raw_positions[0].candidate_sha256 == result.raw_positions[0].retained_sha256
    assert result.raw_positions[1].candidate_sha256 != result.raw_positions[1].retained_sha256
    assert result.raw_positions[1].first_raw_position == 1
    assert result.raw_positions[2].first_raw_position == 3


@pytest.mark.parametrize(
    "raw,match",
    [
        ('{"candidates":[],"candidates":[]}', "duplicate JSON key"),
        (
            '{"candidates":[{"intent_id":"weather_query",'
            '"intent_id":"transport_taxi","distinction":"x",'
            '"evidence_refs":[],"unresolved_fields":[]},{},{}]}',
            "duplicate JSON key",
        ),
        (_compact_response(*_payload()["candidates"]), "exactly three"),
        (
            _compact_response(
                _payload()["candidates"][0],
                {**_payload()["candidates"][1], "intent_id": "illegal"},
                _payload()["candidates"][0],
            ),
            "not legal",
        ),
        (
            _compact_response(
                _payload()["candidates"][0],
                {**_payload()["candidates"][1], "distinction": "x" * 513},
                _payload()["candidates"][0],
            ),
            "512-character bound",
        ),
    ],
)
def test_projection_refuses_malformed_illegal_or_non_fixed_three_input(raw, match):
    with pytest.raises(SlurpIntentHypothesisError, match=match):
        project_fixed_three_slurp_intent_hypotheses(
            raw, sample_id=SAMPLE_ID, legal_intent_ids=LEGAL
        )


def test_projection_does_not_relax_historical_duplicate_rejection():
    duplicate = _payload()["candidates"][0]
    raw = _compact_response(duplicate, duplicate, duplicate)
    projected = project_fixed_three_slurp_intent_hypotheses(
        raw, sample_id=SAMPLE_ID, legal_intent_ids=LEGAL
    )
    assert len(json.loads(projected.content)["candidates"]) == 1

    from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
        canonicalize_slurp_intent_hypothesis_response,
    )

    with pytest.raises(SlurpIntentHypothesisError, match="unique"):
        canonicalize_slurp_intent_hypothesis_response(
            raw,
            sample_id=SAMPLE_ID,
            legal_intent_ids=LEGAL,
            max_candidates=3,
        )


@pytest.mark.parametrize("namespace", [None, "native:request-7"])
def test_compact_state_consumption_is_explicit_and_preserves_raw_custody(namespace):
    from speech_aware_evidence_acquisition.rails.controllers import seal_phase_response_state

    raw = _compact_response(*_payload()["candidates"])
    artifact = seal_phase_response_state(
        phase_name="hypotheses", sample_id=SAMPLE_ID,
        state_content=raw, raw_response_text=raw,
        source_query_state_sha256="1" * 64,
        producer_policy_id="phase-joint-intent-v1", state_namespace=namespace,
    )
    original_hash = artifact.content_hash()
    with pytest.raises(SlurpIntentHypothesisError, match="exactly"):
        parse_slurp_intent_hypothesis_state(
            artifact, expected_sample_id=SAMPLE_ID,
            legal_intent_ids=LEGAL, max_candidates=3,
        )
    parsed = parse_slurp_intent_hypothesis_state(
        artifact, expected_sample_id=SAMPLE_ID,
        legal_intent_ids=LEGAL, max_candidates=3,
        compact_source_phase="hypotheses",
    )
    assert parsed.sample_id == SAMPLE_ID
    assert [item.intent_id for item in parsed.candidates] == [
        "weather_query", "transport_taxi",
    ]
    rendered = SlurpIntentHypothesisStateFill(
        legal_intent_ids=LEGAL, max_candidates=3,
        compact_source_phase="hypotheses",
    ).render_state(artifact, sample_id=SAMPLE_ID)
    assert "weather_query" in rendered and "transport_taxi" in rendered
    assert artifact.content == raw
    assert artifact.content_hash() == original_hash
    assert artifact.source_response_sha256 == hashlib.sha256(raw.encode()).hexdigest()


@pytest.mark.parametrize(
    "overrides,source_phase,match",
    [
        ({"state_id": "hypotheses:another-sample"}, "hypotheses", "sample_id"),
        ({"state_kind": "phase:solver"}, "hypotheses", "phase"),
        ({"source_response_sha256": "b" * 64}, "hypotheses", "source response"),
        ({}, "other-phase", "phase"),
        ({}, "hypotheses:slurp", "phase name"),
        ({}, "", "phase name"),
        ({}, True, "phase name"),
    ],
)
def test_compact_consumption_rejects_wrong_sample_phase_and_raw_hash(
    overrides, source_phase, match
):
    raw = _compact_response(*_payload()["candidates"])
    artifact = replace(
        _state(), content=raw,
        source_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
    )
    artifact = replace(artifact, **overrides)
    with pytest.raises(SlurpIntentHypothesisError, match=match):
        parse_slurp_intent_hypothesis_state(
            artifact, expected_sample_id=SAMPLE_ID,
            legal_intent_ids=LEGAL, max_candidates=3,
            compact_source_phase=source_phase,
        )


@pytest.mark.parametrize(
    "candidates,match",
    [
        ([{**_payload()["candidates"][0], "intent_id": "query"}], "not legal"),
        ([_payload()["candidates"][0]] * 2, "unique"),
    ],
)
def test_compact_consumption_never_repairs_candidate_ids_or_duplicates(candidates, match):
    raw = _compact_response(*candidates)
    artifact = replace(
        _state(), content=raw,
        source_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
    )
    with pytest.raises(SlurpIntentHypothesisError, match=match):
        parse_slurp_intent_hypothesis_state(
            artifact, expected_sample_id=SAMPLE_ID,
            legal_intent_ids=LEGAL, max_candidates=3,
            compact_source_phase="hypotheses",
        )


@pytest.mark.parametrize("positions", [(0,), (0, 0), (0, 1), (0, 1, 0)])
def test_bounded_projection_preserves_source_and_first_occurrence(positions):
    rows = [_payload()["candidates"][i] for i in positions]
    source = json.dumps({"candidates": rows})
    artifact = _state({"candidates": rows})
    result = parse_slurp_intent_hypothesis_state(
        artifact, expected_sample_id=SAMPLE_ID, legal_intent_ids=LEGAL,
        max_candidates=3, compact_source_phase="hypotheses",
        projection_policy=BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    )
    assert [c.intent_id for c in result.candidates] == list(dict.fromkeys(
        row["intent_id"] for row in rows
    ))
    projection = result.projection
    assert projection is not None
    assert projection.original_text_sha256 == artifact.source_response_sha256
    assert artifact.content == json.dumps({"candidates": rows}, sort_keys=True)
    assert len(projection.raw_positions) == len(rows)
    assert projection.projection_policy_id == BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
    assert projection.projection_policy_sha256 == BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256
    direct = project_bounded_slurp_intent_hypotheses(
        source, sample_id=SAMPLE_ID, legal_intent_ids=LEGAL,
    )
    assert direct.content == projection.content
    if len(set(positions)) != len(positions):
        with pytest.raises(SlurpIntentHypothesisError, match="unique"):
            parse_slurp_intent_hypothesis_state(
                artifact, expected_sample_id=SAMPLE_ID, legal_intent_ids=LEGAL,
                max_candidates=3, compact_source_phase="hypotheses",
            )


@pytest.mark.parametrize("rows", [
    [], [_payload()["candidates"][0]] * 4,
    [_payload()["candidates"][0], {
        **_payload()["candidates"][0], "evidence_refs": ["duplicate", "duplicate"],
    }],
    [_payload()["candidates"][0], {
        **_payload()["candidates"][0], "intent_id": "illegal",
    }],
])
def test_bounded_projection_validates_all_raw_objects(rows):
    with pytest.raises(SlurpIntentHypothesisError):
        project_bounded_slurp_intent_hypotheses(
            json.dumps({"candidates": rows}), sample_id=SAMPLE_ID, legal_intent_ids=LEGAL,
        )


@pytest.mark.parametrize("mutation", [
    {"state_id": "hypotheses:foreign"},
    {"state_kind": "phase:foreign"},
    {"source_response_sha256": "a" * 64},
])
def test_projection_cannot_bypass_source_custody(mutation):
    artifact = replace(_state({"candidates": _payload()["candidates"]}), **mutation)
    with pytest.raises(SlurpIntentHypothesisError):
        parse_slurp_intent_hypothesis_state(
            artifact, expected_sample_id=SAMPLE_ID, legal_intent_ids=LEGAL,
            max_candidates=3, compact_source_phase="hypotheses",
            projection_policy=BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        )


def test_bounded_and_fixed_three_projections_have_distinct_policy_identity():
    raw = json.dumps({"candidates": [_payload()["candidates"][0]] * 3})
    args = {"sample_id": SAMPLE_ID, "legal_intent_ids": LEGAL}
    old = project_fixed_three_slurp_intent_hypotheses(raw, **args)
    new = project_bounded_slurp_intent_hypotheses(raw, **args)
    assert old.content == new.content
    assert old.raw_positions == new.raw_positions
    assert old.projection_policy_id != new.projection_policy_id
    assert old.projection_policy_sha256 != new.projection_policy_sha256
    with pytest.raises(SlurpIntentHypothesisError, match="exactly three"):
        project_fixed_three_slurp_intent_hypotheses(
            json.dumps({"candidates": [_payload()["candidates"][0]]}), **args,
        )


def test_configurable_projection_accepts_five_without_changing_default_identity():
    candidates = [
        {
            "intent_id": intent_id,
            "distinction": f"Alternative {intent_id}.",
            "evidence_refs": ["speech:current-query"],
            "unresolved_fields": [],
        }
        for intent_id in (
            "weather_query",
            "transport_taxi",
            "alarm_set",
            "music_play",
            "calendar_set",
        )
    ]
    legal = frozenset(row["intent_id"] for row in candidates)
    raw = json.dumps({"candidates": candidates})

    projected = project_bounded_slurp_intent_hypotheses(
        raw,
        sample_id=SAMPLE_ID,
        legal_intent_ids=legal,
        max_candidates=5,
        projection_policy=(
            CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        ),
    )
    assert len(json.loads(projected.content)["candidates"]) == 5
    assert projected.projection_policy_id == (
        CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
    )
    assert projected.projection_policy_sha256 == (
        CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256
    )
    assert BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256 == (
        "a4ef54c1b0d1ee4853528fcd667fd0fd6f5b91a3b485c85dd75bd7f33f4c5096"
    )

    with pytest.raises(SlurpIntentHypothesisError, match="configurable"):
        project_bounded_slurp_intent_hypotheses(
            raw,
            sample_id=SAMPLE_ID,
            legal_intent_ids=legal,
            max_candidates=5,
        )
    with pytest.raises(SlurpIntentHypothesisError, match="one through 4"):
        project_bounded_slurp_intent_hypotheses(
            raw,
            sample_id=SAMPLE_ID,
            legal_intent_ids=legal,
            max_candidates=4,
            projection_policy=(
                CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
            ),
        )


# ---------------------------------------------------------------------------
# FIX-1 standing fallback candidate
# (docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md)
# ---------------------------------------------------------------------------

FALLBACK_LEGAL = LEGAL | {"general_quirky", "qa_factoid"}


def _model_candidate(intent_id, *, distinction="A model-proposed alternative."):
    return SlurpIntentHypothesisCandidate(
        intent_id=intent_id,
        distinction=distinction,
        evidence_refs=(),
        unresolved_fields=(),
    )


def test_fallback_candidate_ids_absent_or_empty_is_a_noop():
    assert validate_fallback_candidate_ids(None, legal_intent_ids=FALLBACK_LEGAL) == ()
    assert validate_fallback_candidate_ids((), legal_intent_ids=FALLBACK_LEGAL) == ()
    assert validate_fallback_candidate_ids([], legal_intent_ids=FALLBACK_LEGAL) == ()


def test_fallback_candidate_ids_refuse_unknown_id():
    with pytest.raises(SlurpIntentHypothesisError, match="outside the legal inventory"):
        validate_fallback_candidate_ids(
            ["not_a_real_intent"], legal_intent_ids=FALLBACK_LEGAL
        )


def test_fallback_candidate_ids_refuse_too_many():
    assert MAX_FALLBACK_CANDIDATES == 2
    with pytest.raises(SlurpIntentHypothesisError, match="more than 2"):
        validate_fallback_candidate_ids(
            ["general_quirky", "qa_factoid", "weather_query"],
            legal_intent_ids=FALLBACK_LEGAL,
        )


def test_fallback_candidate_ids_refuse_duplicates_and_non_strings():
    with pytest.raises(SlurpIntentHypothesisError, match="unique"):
        validate_fallback_candidate_ids(
            ["general_quirky", "general_quirky"], legal_intent_ids=FALLBACK_LEGAL
        )
    with pytest.raises(SlurpIntentHypothesisError, match="non-empty strings"):
        validate_fallback_candidate_ids([""], legal_intent_ids=FALLBACK_LEGAL)
    with pytest.raises(SlurpIntentHypothesisError, match="list of legal intent ids"):
        validate_fallback_candidate_ids("general_quirky", legal_intent_ids=FALLBACK_LEGAL)


def test_fallback_distinction_validation():
    assert validate_fallback_distinction(DEFAULT_FALLBACK_DISTINCTION) == (
        DEFAULT_FALLBACK_DISTINCTION
    )
    with pytest.raises(SlurpIntentHypothesisError, match="non-empty string"):
        validate_fallback_distinction("")
    with pytest.raises(SlurpIntentHypothesisError, match="exceeds 128"):
        validate_fallback_distinction("x" * 129)


def test_append_fallback_candidate_appends_at_end_when_absent():
    candidates = (_model_candidate("weather_query"), _model_candidate("transport_taxi"))
    result = append_fallback_slurp_intent_hypothesis_candidates(
        candidates,
        fallback_candidates=["general_quirky"],
        legal_intent_ids=FALLBACK_LEGAL,
    )
    assert [c.intent_id for c in result] == [
        "weather_query", "transport_taxi", "general_quirky",
    ]
    # Model candidates are returned unchanged, in their original order, and
    # keep their model source; only the appended entry is labelled fallback.
    assert result[0] == candidates[0]
    assert result[1] == candidates[1]
    assert result[0].source == MODEL_CANDIDATE_SOURCE
    assert result[1].source == MODEL_CANDIDATE_SOURCE
    fallback = result[2]
    assert fallback.source == FALLBACK_CANDIDATE_SOURCE
    assert fallback.distinction == DEFAULT_FALLBACK_DISTINCTION
    assert fallback.evidence_refs == ()
    assert fallback.unresolved_fields == ()


def test_append_fallback_candidate_is_a_noop_when_already_present():
    candidates = (
        _model_candidate("general_quirky"), _model_candidate("transport_taxi"),
    )
    result = append_fallback_slurp_intent_hypothesis_candidates(
        candidates,
        fallback_candidates=["general_quirky"],
        legal_intent_ids=FALLBACK_LEGAL,
    )
    assert result == candidates
    assert [c.intent_id for c in result] == ["general_quirky", "transport_taxi"]
    assert all(c.source == MODEL_CANDIDATE_SOURCE for c in result)


def test_append_fallback_candidate_empty_list_is_a_noop_and_preserves_order():
    candidates = (_model_candidate("transport_taxi"), _model_candidate("weather_query"))
    result = append_fallback_slurp_intent_hypothesis_candidates(
        candidates, fallback_candidates=[], legal_intent_ids=FALLBACK_LEGAL,
    )
    assert result == candidates
    result_absent = append_fallback_slurp_intent_hypothesis_candidates(
        candidates, legal_intent_ids=FALLBACK_LEGAL,
    )
    assert result_absent == candidates


def test_append_fallback_candidate_preserves_configured_order_of_multiple_ids():
    candidates = (_model_candidate("transport_taxi"),)
    result = append_fallback_slurp_intent_hypothesis_candidates(
        candidates,
        fallback_candidates=["general_quirky", "qa_factoid"],
        legal_intent_ids=FALLBACK_LEGAL,
    )
    assert [c.intent_id for c in result] == [
        "transport_taxi", "general_quirky", "qa_factoid",
    ]
    assert all(c.source == FALLBACK_CANDIDATE_SOURCE for c in result[1:])


def test_append_fallback_candidate_uses_a_configured_distinction_text():
    candidates = (_model_candidate("transport_taxi"),)
    result = append_fallback_slurp_intent_hypothesis_candidates(
        candidates,
        fallback_candidates=["general_quirky"],
        fallback_distinction="A shorter override distinction.",
        legal_intent_ids=FALLBACK_LEGAL,
    )
    assert result[-1].distinction == "A shorter override distinction."


def test_append_fallback_candidate_refuses_an_id_outside_the_legal_inventory():
    candidates = (_model_candidate("transport_taxi"),)
    with pytest.raises(SlurpIntentHypothesisError, match="outside the legal inventory"):
        append_fallback_slurp_intent_hypothesis_candidates(
            candidates,
            fallback_candidates=["not_a_real_intent"],
            legal_intent_ids=FALLBACK_LEGAL,
        )


def test_bounded_seal_projection_separates_raw_positions_from_distinct_authority():
    from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
        project_bounded_slurp_intent_hypotheses, SlurpIntentHypothesisError,
    )
    raw = json.dumps({"candidates": [
        {"intent_id": "one", "distinction": "A speech cue",
         "evidence_refs": [], "unresolved_fields": []} for _ in range(3)
    ]})
    with pytest.raises(SlurpIntentHypothesisError, match="one through 1"):
        project_bounded_slurp_intent_hypotheses(
            raw, sample_id="s1", legal_intent_ids=("one",), max_candidates=1)
    projected = project_bounded_slurp_intent_hypotheses(
        raw, sample_id="s1", legal_intent_ids=("one",), max_candidates=1,
        raw_max_candidates=3)
    assert len(json.loads(projected.content)["candidates"]) == 1
    assert len(projected.raw_positions) == 3
    ordinary = project_bounded_slurp_intent_hypotheses(
        raw, sample_id="s1", legal_intent_ids=("one", "two", "three"), max_candidates=3)
    assert projected == ordinary


@pytest.mark.parametrize("raw_limit", [True, 0, -1, 4, 1.5, "3"])
def test_invalid_explicit_raw_projection_bounds_are_rejected(raw_limit):
    from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
        project_bounded_slurp_intent_hypotheses, SlurpIntentHypothesisError,
    )
    raw = json.dumps({"candidates": [
        {"intent_id": "one", "distinction": "A speech cue",
         "evidence_refs": [], "unresolved_fields": []}
    ]})
    with pytest.raises(SlurpIntentHypothesisError):
        project_bounded_slurp_intent_hypotheses(
            raw, sample_id="s1", legal_intent_ids=("one",), max_candidates=1,
            raw_max_candidates=raw_limit)


@pytest.mark.parametrize("labels", [
    ("one", "one", "one", "one"), ("one", "unknown", "one"),
])
def test_explicit_raw_bound_preserves_length_and_label_validation(labels):
    from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
        project_bounded_slurp_intent_hypotheses, SlurpIntentHypothesisError,
    )
    raw = json.dumps({"candidates": [
        {"intent_id": label, "distinction": "A speech cue",
         "evidence_refs": [], "unresolved_fields": []} for label in labels
    ]})
    with pytest.raises(SlurpIntentHypothesisError):
        project_bounded_slurp_intent_hypotheses(
            raw, sample_id="s1", legal_intent_ids=("one",), max_candidates=1,
            raw_max_candidates=3)
