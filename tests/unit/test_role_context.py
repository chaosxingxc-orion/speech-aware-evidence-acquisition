"""Typed role context keeps source custody while removing stale free-form history."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.role_context import (
    ROLE_CONTEXT_POLICY_ID,
    RoleContextError,
    SlurpRoleContextCompiler,
)
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    DEFAULT_FALLBACK_DISTINCTION,
    FALLBACK_CANDIDATE_SOURCE,
    MODEL_CANDIDATE_SOURCE,
)


QUERY_SHA = "1" * 64
PHASE_IDS = {
    "perception": "perception",
    "solver": "solver",
    "reviewer": "reviewer",
    "planner": "planner",
}
POLICY = CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
DRAFT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scenario", "action", "entities"],
    "properties": {
        "scenario": {"type": "string"},
        "action": {"type": "string"},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "filler"],
                "properties": {
                    "type": {"type": "string"},
                    "filler": {"type": "string"},
                },
            },
        },
    },
}


def artifact(state_id: str, kind: str, content: str) -> AgentStateArtifact:
    return AgentStateArtifact(
        state_id=state_id,
        state_kind=kind,
        content=content,
        source_query_state_sha256=QUERY_SHA,
        source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="source-policy",
        cited_value_ids=(),
    ).validate()


def phase(role: str, serial: int, content: str) -> AgentStateArtifact:
    return artifact(f"contact-{serial}:{role}:s1", f"phase:{PHASE_IDS[role]}", content)


def candidates(*intent_ids: str) -> str:
    return json.dumps({
        "candidates": [
            {
                "intent_id": intent_id,
                "distinction": f"Model interpretation {index}",
                "evidence_refs": [f"claim:{index}"],
                "unresolved_fields": ["entity span"],
            }
            for index, intent_id in enumerate(intent_ids, start=1)
        ]
    })


def draft(*fillers: str) -> str:
    return json.dumps({
        "scenario": "calendar",
        "action": "set_event",
        "entities": [{"type": "date", "filler": value} for value in fillers],
    })


def review(*evidence_ids: str) -> str:
    return json.dumps({
        "schema": "saea-review-findings-v1",
        "verdict": "supported-issue",
        "findings": [{
            "dimension": "slot-span",
            "rationale": "The proposed span may omit a spoken modifier.",
            "evidence_ids": list(evidence_ids),
        }],
        "recommendation": "reconsider",
        "remaining_uncertainty": "The exact boundary remains uncertain.",
    })


def native_pair(
    serial: int, *, source_role: str = "reviewer", evidence_id: str = "tool:e1",
) -> tuple[AgentStateArtifact, AgentStateArtifact]:
    source = phase(source_role, serial, json.dumps({"tool_call": serial}))
    document = {
        "schema": "saea-phase-tool-result-v2",
        "sample_id": "s1",
        "phase": PHASE_IDS[source_role],
        "native_source_state_id": source.state_id,
        "query_state_sha256": source.source_query_state_sha256,
        "source_response_sha256": source.source_response_sha256,
        "native_result_content": [{
            "type": "text",
            "evidence_id": evidence_id,
            "source_uri": f"test://{evidence_id}",
            "text": "A bounded synthetic observation.",
        }],
    }
    result = AgentStateArtifact(
        state_id=f"tool-result:{source_role}:s1:{serial}",
        state_kind="tool-result",
        content=json.dumps(document),
        source_query_state_sha256=source.source_query_state_sha256,
        source_response_sha256=source.source_response_sha256,
        producer_policy_id=source.producer_policy_id,
        cited_value_ids=(),
    ).validate()
    return source, result


def compiler(**changes) -> SlurpRoleContextCompiler:
    values = {
        "legal_intent_ids": ("calendar_set_event", "calendar_query"),
        "max_candidates": 2,
        "projection_policy": POLICY,
    }
    values.update(changes)
    return SlurpRoleContextCompiler(**values)


def compile_for(role_kind: str, states=(), *, local=(), available=()):
    return compiler().compile(
        role_kind=role_kind,
        phase_ids=PHASE_IDS,
        sample_id="s1",
        states=tuple(states),
        local_tool_result_ids=tuple(local),
        available_evidence_ids=tuple(available),
        draft_response_schema=DRAFT_SCHEMA,
    )


def views(result):
    return [
        json.loads(state.content)
        for state in result.states
        if state.state_kind.startswith("role-context:")
    ]


def by_class(result, semantic_class: str):
    return next(view for view in views(result) if view["semantic_class"] == semantic_class)


@pytest.mark.parametrize("changes", [
    {"legal_intent_ids": ()},
    {"legal_intent_ids": ("calendar_set_event", "calendar_set_event")},
    {"max_candidates": True},
    {"max_candidates": 0},
    {"max_candidates": 2, "projection_policy": "unknown"},
])
def test_factory_rejects_unbounded_or_ambiguous_parameters(changes):
    with pytest.raises((RoleContextError, ValueError)):
        compiler(**changes)


def test_first_perception_receives_no_old_candidate_or_draft_state():
    old = phase("perception", 1, candidates("calendar_set_event"))
    result = compile_for("perception", (old,))
    assert result.states == ()
    assert result.receipt["policy_id"] == ROLE_CONTEXT_POLICY_ID
    assert result.receipt["retained"] == []
    assert result.receipt["excluded"][0]["reason"] == "first-perception-has-no-prior-role-view"


def test_solver_gets_latest_distinct_candidate_projection_with_provenance():
    old = phase("perception", 1, candidates("calendar_query"))
    latest = phase(
        "perception", 2,
        candidates("calendar_set_event", "calendar_set_event"),
    )
    result = compile_for("solver", (old, latest))
    view = by_class(result, "candidate-hypothesis")
    assert [row["intent_id"] for row in view["view"]["candidates"]] == [
        "calendar_set_event",
    ]
    assert view["declaration_status"] == "unverified-model-hypotheses"
    retained = next(
        row for row in result.receipt["retained"]
        if row["state_kind"] == "role-context:candidate-hypothesis"
    )
    assert [row["raw_position"] for row in retained["projection"]["raw_positions"]] == [1, 2]
    assert view["source"]["state_id"] == latest.state_id
    assert view["source"] == {
        "state_id": latest.state_id, "state_kind": latest.state_kind,
    }
    assert retained["source"]["artifact_sha256"] == latest.content_hash()
    assert retained["source"]["producer_policy_id"] == latest.producer_policy_id
    derived = result.states[0]
    assert derived.source_response_sha256 == latest.source_response_sha256
    assert derived.source_response_sha256 != hashlib.sha256(derived.content.encode()).hexdigest()
    assert view["view"]["evidence_ref_availability"] == [{
        "intent_id": "calendar_set_event",
        "evidence_refs": [{"evidence_id": "claim:1", "available": False}],
    }]
    assert any(row["state_id"] == old.state_id and row["reason"] == "stale-perception" for row in result.receipt["excluded"])
    excluded = next(row for row in result.receipt["excluded"] if row["state_id"] == old.state_id)
    assert excluded["artifact_sha256"] == old.content_hash()
    assert excluded["producer_policy_id"] == old.producer_policy_id


# ---------------------------------------------------------------------------
# FIX-1 standing fallback candidate
# (docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md)
# ---------------------------------------------------------------------------

FALLBACK_ID = "calendar_remove_event"


def fallback_compiler(**changes) -> SlurpRoleContextCompiler:
    return compiler(
        legal_intent_ids=("calendar_set_event", "calendar_query", FALLBACK_ID),
        fallback_candidates=(FALLBACK_ID,),
        **changes,
    )


def compile_fallback_for(role_kind: str, states=(), *, local=(), available=(), **changes):
    return fallback_compiler(**changes).compile(
        role_kind=role_kind,
        phase_ids=PHASE_IDS,
        sample_id="s1",
        states=tuple(states),
        local_tool_result_ids=tuple(local),
        available_evidence_ids=tuple(available),
        draft_response_schema=DRAFT_SCHEMA,
    )


def test_candidate_view_appends_labelled_fallback_last_when_absent():
    perception = phase("perception", 1, candidates("calendar_query"))
    result = compile_fallback_for("solver", (perception,))
    view = by_class(result, "candidate-hypothesis")
    rows = view["view"]["candidates"]
    assert [row["intent_id"] for row in rows] == ["calendar_query", FALLBACK_ID]
    # The model's own candidate is unchanged and explicitly labelled model.
    assert rows[0]["source"] == MODEL_CANDIDATE_SOURCE
    assert rows[0]["distinction"] == "Model interpretation 1"
    assert rows[0]["evidence_refs"] == ["claim:1"]
    # The appended fallback is explicitly labelled -- not a model proposal.
    fallback_row = rows[1]
    assert fallback_row["source"] == FALLBACK_CANDIDATE_SOURCE
    assert fallback_row["distinction"] == DEFAULT_FALLBACK_DISTINCTION
    assert fallback_row["evidence_refs"] == []
    assert fallback_row["unresolved_fields"] == []
    assert view["declaration_status"] == "unverified-model-hypotheses"
    assert view["view"]["evidence_ref_availability"][-1] == {
        "intent_id": FALLBACK_ID, "evidence_refs": [],
    }
    # The projection audit (the sealed Perception response's own provenance)
    # is untouched by the fallback append -- it never claims the model named
    # a candidate it did not.
    retained = next(
        row for row in result.receipt["retained"]
        if row["state_kind"] == "role-context:candidate-hypothesis"
    )
    assert [item["intent_id"] for item in retained["projection"]["raw_positions"]] == (
        ["calendar_query"]
    )


def test_candidate_view_fallback_is_a_noop_when_already_present():
    perception = phase("perception", 1, candidates(FALLBACK_ID))
    result = compile_fallback_for("solver", (perception,))
    view = by_class(result, "candidate-hypothesis")
    rows = view["view"]["candidates"]
    # Already present: nothing is appended, but the option is configured, so
    # the model's own candidate is still explicitly labelled.
    assert [row["intent_id"] for row in rows] == [FALLBACK_ID]
    assert rows[0]["source"] == MODEL_CANDIDATE_SOURCE
    assert rows[0]["distinction"] == "Model interpretation 1"


def test_candidate_view_with_no_fallback_configured_carries_no_source_key():
    """Unconfigured (the default ``fallback_candidates=()``): the rendered
    candidate view must be byte-for-byte what this function rendered before
    the option existed -- in particular, no ``source`` key at all."""

    perception = phase("perception", 1, candidates("calendar_query"))
    result = compile_for("solver", (perception,))
    view = by_class(result, "candidate-hypothesis")
    rows = view["view"]["candidates"]
    assert rows == [{
        "intent_id": "calendar_query",
        "distinction": "Model interpretation 1",
        "evidence_refs": ["claim:1"],
        "unresolved_fields": ["entity span"],
    }]
    assert "source" not in rows[0]


def test_candidate_view_empty_fallback_list_is_byte_identical_to_absent():
    perception = phase("perception", 1, candidates("calendar_query"))
    absent = compile_for("solver", (perception,))
    empty = compiler(fallback_candidates=()).compile(
        role_kind="solver", phase_ids=PHASE_IDS, sample_id="s1",
        states=(perception,), local_tool_result_ids=(),
        available_evidence_ids=(), draft_response_schema=DRAFT_SCHEMA,
    )
    assert by_class(absent, "candidate-hypothesis") == by_class(empty, "candidate-hypothesis")
    assert absent.receipt == empty.receipt


def test_fallback_candidate_config_refuses_an_id_outside_the_legal_inventory():
    with pytest.raises(RoleContextError, match="outside the legal inventory"):
        compiler(fallback_candidates=("not_a_real_intent",))


def test_fallback_candidate_config_refuses_more_than_two_ids():
    with pytest.raises(RoleContextError, match="more than 2"):
        compiler(
            legal_intent_ids=("calendar_set_event", "calendar_query", "a", "b"),
            fallback_candidates=("calendar_set_event", "calendar_query", "a"),
        )


def test_reviewer_keeps_exact_repeated_draft_entities_and_marks_malformed_raw():
    perception = phase("perception", 1, candidates("calendar_set_event"))
    exact = phase("solver", 1, draft("next Friday", "next Friday"))
    parsed = compile_for("reviewer", (perception, exact))
    draft_view = by_class(parsed, "current-draft")
    assert draft_view["parse_status"] == "parsed"
    assert [row["filler"] for row in draft_view["view"]["parsed"]["entities"]] == [
        "next Friday", "next Friday",
    ]
    assert "raw_text" not in draft_view["view"]

    missing_entities = phase(
        "solver", 2, json.dumps({"scenario": "calendar", "action": "set_event"}),
    )
    malformed = compile_for("reviewer", (perception, missing_entities))
    malformed_view = by_class(malformed, "current-draft")
    assert malformed_view["parse_status"] == "malformed"
    assert malformed_view["view"] == {"raw_text": missing_entities.content}


def test_planner_gets_draft_identity_and_current_findings_with_visible_citations_only():
    perception = phase("perception", 1, candidates("calendar_set_event"))
    solver = phase("solver", 1, draft("Friday"))
    call, result = native_pair(1, evidence_id="tool:span")
    finding = phase("reviewer", 2, review("base:speech", "tool:span", "stale:hidden"))
    compiled = compile_for(
        "planner", (perception, solver, call, result, finding),
        local=(result.state_id,), available=("base:speech",),
    )
    assert any(state is call for state in compiled.states)
    assert any(state is result for state in compiled.states)
    planner_draft = by_class(compiled, "current-draft")
    assert planner_draft["view"] == {
        "source_state_id": solver.state_id, "parse_status": "parsed",
    }
    assert "Friday" not in json.dumps(planner_draft)
    report = by_class(compiled, "review-finding")
    assert report["declaration_status"] == "unverified-review-declaration"
    assert report["view"]["citation_availability"] == [
        {"evidence_id": "base:speech", "available": True},
        {"evidence_id": "tool:span", "available": True},
        {"evidence_id": "stale:hidden", "available": False},
    ]
    assert not any(view["semantic_class"] == "candidate-hypothesis" for view in views(compiled))


@pytest.mark.parametrize("role", ["solver", "planner", "perception"])
def test_post_draft_roles_keep_current_report_and_exact_relevant_native_pair(role):
    perception = phase("perception", 1, candidates("calendar_set_event"))
    solver = phase("solver", 1, draft("Friday"))
    call, result = native_pair(1)
    finding = phase("reviewer", 2, review("tool:e1"))
    compiled = compile_for(role, (perception, solver, call, result, finding))
    assert any(state is call for state in compiled.states)
    assert any(state is result for state in compiled.states)
    assert by_class(compiled, "review-finding")["parse_status"] == "parsed"


def test_malformed_review_is_unavailable_and_never_no_issue():
    solver = phase("solver", 1, draft())
    malformed = phase("reviewer", 1, "not JSON")
    result = compile_for("planner", (solver, malformed))
    report = by_class(result, "review-finding")
    assert report["parse_status"] == "unavailable"
    assert report["view"] == {"reason": "malformed-review-findings"}
    assert "no-supported-issue" not in json.dumps(report)


@pytest.mark.parametrize("change", ["missing", "foreign", "interleaved", "reordered"])
def test_invalid_native_pairs_fail_before_a_role_view_is_built(change):
    solver = phase("solver", 1, draft())
    call1, result1 = native_pair(1)
    call2, result2 = native_pair(2)
    states = [solver, call1, result1, call2, result2]
    local = [result1.state_id, result2.state_id]
    if change == "missing":
        local[1] = "missing"
    elif change == "foreign":
        document = json.loads(result1.content)
        document["native_source_state_id"] = "unknown"
        states[2] = artifact(result1.state_id, "tool-result", json.dumps(document))
    elif change == "interleaved":
        states = [solver, call1, call2, result1, result2]
    elif change == "reordered":
        local.reverse()
    with pytest.raises(RoleContextError):
        compile_for("planner", states, local=local)


def test_duplicate_nonfinite_draft_json_is_retained_as_malformed_without_input_mutation():
    raw = '{"scenario":"calendar","scenario":"other","action":"set_event","entities":[],"x":NaN}'
    source = phase("solver", 1, raw)
    states = (source,)
    schema_before = deepcopy(DRAFT_SCHEMA)
    result = compile_for("reviewer", states)
    assert by_class(result, "current-draft")["parse_status"] == "malformed"
    assert states == (source,)
    assert DRAFT_SCHEMA == schema_before
    json.dumps(result.receipt, sort_keys=True)


@pytest.mark.parametrize("source_role", ["solver", "reviewer"])
def test_selected_raw_phase_source_must_match_its_response_hash(source_role):
    perception = phase("perception", 1, candidates("calendar_set_event"))
    solver = phase("solver", 1, draft())
    if source_role == "solver":
        states = (perception, replace(solver, source_response_sha256="2" * 64))
        role = "reviewer"
    else:
        finding = phase("reviewer", 1, review())
        states = (solver, replace(finding, source_response_sha256="2" * 64))
        role = "planner"
    with pytest.raises(RoleContextError, match="response hash"):
        compile_for(role, states)


@pytest.mark.parametrize("defect", ["external_ref", "missing_entities"])
def test_direct_compiler_rejects_nonlocal_or_incomplete_draft_schema(defect):
    schema = deepcopy(DRAFT_SCHEMA)
    if defect == "external_ref":
        schema["properties"]["scenario"]["$ref"] = "https://example.invalid/schema"
    else:
        schema["required"].remove("entities")
    with pytest.raises(RoleContextError):
        compiler().compile(
            role_kind="reviewer", phase_ids=PHASE_IDS, sample_id="s1",
            states=(), local_tool_result_ids=(), available_evidence_ids=(),
            draft_response_schema=schema,
        )
