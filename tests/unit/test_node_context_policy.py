"""E8a: the Node Context Policy object, its templates and its malformed rules.

Model-free, tokenizer-free, server-free: every test here renders through the
production policy object over synthetic ``AgentStateArtifact`` values.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
sections 3-5, 9 and 10.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.node_context_binding import (
    REVIEW_FINDINGS_RESPONSE_FORMAT_ID,
    is_node_context_null_arm,
    validate_node_context_policy_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import (
    CHECK_NA,
    CHECK_NO,
    CHECK_NO_INVENTORY,
    CHECK_YES,
    CLOSED_VOCABULARY,
    FALLBACK_OMIT,
    FALLBACK_RAW,
    NODE_CONTEXT_RECEIPT_SCHEMA,
    SLURP_BOUNDARY_IDS,
    SLURP_BOUNDARY_PARSE_FAILURE,
    SLURP_BOUNDARY_TEMPLATES,
    NodeContextPolicyError,
    ParsedDraft,
    build_slurp_node_context_policy,
    load_node_context_template,
    parse_node_context_template,
)
from speech_aware_evidence_acquisition.rails.review_findings import (
    parse_review_findings,
    review_findings_response_format,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

PHASE_IDS = {
    "perception": "perception",
    "solver": "solver",
    "reviewer": "reviewer",
    "planner": "planner",
}
ACTIONS = ("ACCEPT", "REVISE", "ACQUIRE")
LEGAL_INTENTS = ("alarm_set", "alarm_remove", "calendar_query")
LEGAL_ENTITY_TYPES = ("time", "date", "event_name")
LIMITS = {
    "revision_index": 0,
    "max_revisions": 1,
    "available_planner_actions": ["ACCEPT", "REVISE"],
}

DRAFT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["scenario", "action", "entities"],
    "properties": {
        "scenario": {"type": "string"}, "action": {"type": "string"},
        "entities": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["type", "filler"],
            "properties": {"type": {"type": "string"}, "filler": {"type": "string"}},
        }},
    },
}

PARAMS = {
    "max_candidates": 3,
    "projection_policy": (
        "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
    ),
    "draft_response_schema": deepcopy(DRAFT_SCHEMA),
    "legal_entity_types": list(LEGAL_ENTITY_TYPES),
}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _state(state_id: str, kind: str, content: str) -> AgentStateArtifact:
    return AgentStateArtifact(
        state_id=state_id,
        state_kind=kind,
        content=content,
        source_query_state_sha256="a" * 64,
        source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="native-role-runner-proof-v1",
        cited_value_ids=(),
    ).validate()


CANDIDATES = _json({"candidates": [
    {"intent_id": "alarm_set", "distinction": "The command may create an alarm.",
     "evidence_refs": [], "unresolved_fields": []},
    {"intent_id": "alarm_remove", "distinction": "The command may remove an alarm.",
     "evidence_refs": [], "unresolved_fields": []},
]})
DRAFT = _json({"scenario": "alarm", "action": "set",
               "entities": [{"type": "time", "filler": "seven"}]})
OFF_LIST_DRAFT = _json({"scenario": "calendar", "action": "set",
                        "entities": [{"type": "guest", "filler": "ana"}]})
REVIEW = _json({
    "schema": "saea-review-findings-v1",
    "verdict": "supported-issue",
    "findings": [{
        "dimension": "intent",
        "rationale": "Removal remains plausible on the spoken cue.",
        "evidence_ids": ["evidence-one", "evidence-absent"],
    }],
    "recommendation": "reconsider",
    "remaining_uncertainty": "The speech remains the authority.",
})
PROSE_REVIEW = "The draft looks plausible; the time reading is ambiguous."


def _policy(*, level: str = "structured", boundaries=None, params=None):
    return build_slurp_node_context_policy(
        repo_root=REPO_ROOT,
        policy_id="typed-slurp-node-context-v1",
        level=level,
        boundaries=boundaries or {},
        legal_intent_ids=LEGAL_INTENTS,
        params=params or PARAMS,
    )


def _compile(policy, role_kind, states, **kwargs):
    return policy.compile(
        role_kind=role_kind,
        phase_ids=PHASE_IDS,
        sample_id="s1",
        states=tuple(states),
        available_evidence_ids=kwargs.pop("available_evidence_ids", ("evidence-one",)),
        episode_limits=kwargs.pop("episode_limits", LIMITS),
        actions=ACTIONS,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def test_every_declared_slurp_template_is_committed_and_matches_its_renderer():
    """The design's section 4 drafts exist as committed files, each one
    declaring the renderer its boundary needs."""

    policy = _policy()
    declared = policy.declared_boundaries()
    assert len(declared) == len(SLURP_BOUNDARY_IDS) == 12
    for entry in declared:
        assert entry["level"] == "structured"
        assert entry["template_id"] in set(SLURP_BOUNDARY_TEMPLATES.values())
        assert re.fullmatch(r"[0-9a-f]{64}", entry["template_sha256"])
        assert (REPO_ROOT / "configs" / entry["template_id"]).is_file()
    assert {entry["on_parse_failure"] for entry in declared} == {"raw", "refuse"}
    for (role, semantic), rule in SLURP_BOUNDARY_PARSE_FAILURE.items():
        assert rule == ("refuse" if semantic == "plan-action" else "raw"), (role, semantic)


@pytest.mark.parametrize(
    "text,match",
    [
        ("[header]\nx\n", "must open with"),
        ("# saea-node-context-template-v1 renderer=nope\n[header]\nx\n", "unknown renderer"),
        ("# saea-node-context-template-v1 renderer=plan-action\n[header]\nx\n", "requires"),
        (
            "# saea-node-context-template-v1 renderer=plan-action\n"
            "[header]\n{nope}\n[footer]\n{revisions_remaining} {available_actions}\n",
            "unknown placeholders",
        ),
        (
            "# saea-node-context-template-v1 renderer=plan-action\n"
            "[header]\n{action} }\n[footer]\n{revisions_remaining} {available_actions}\n",
            "unrecognised brace",
        ),
        (
            "# saea-node-context-template-v1 renderer=plan-action\n"
            "[header]\n{action}\n[header]\nx\n[footer]\n"
            "{revisions_remaining} {available_actions}\n",
            "repeats section",
        ),
    ],
)
def test_a_malformed_template_is_refused_at_load_time(text, match):
    """An unfilled or unknown template never reaches a model: the refusal is
    at load, not at render."""

    with pytest.raises(NodeContextPolicyError, match=match):
        parse_node_context_template(text, template_id="probes/synthetic.txt")


def test_a_template_outside_configs_probes_is_refused(tmp_path):
    for relpath in ("../secrets.txt", "/etc/passwd", "probes\\win.txt", "other/x.txt"):
        with pytest.raises(NodeContextPolicyError, match="probes/"):
            load_node_context_template(tmp_path, relpath)


# ---------------------------------------------------------------------------
# L1 determinism, malformed rules and receipts
# ---------------------------------------------------------------------------


def _reviewer_states():
    return [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
    ]


def test_l1_rendering_is_byte_stable_across_repetitions():
    """(b) determinism: the same states render to the same bytes, every time
    and in any process -- no dict iteration, no float formatting."""

    policy = _policy()
    first = _compile(policy, "reviewer", _reviewer_states())
    texts = [state.content for state in first.states]
    for _ in range(50):
        again = _compile(_policy(), "reviewer", _reviewer_states())
        assert [state.content for state in again.states] == texts
        assert again.receipt["receipt_sha256"] == first.receipt["receipt_sha256"]


def test_structured_rendering_keeps_source_hashes_and_never_changes_state_count():
    policy = _policy()
    states = _reviewer_states()
    compiled = _compile(policy, "reviewer", states)
    assert len(compiled.states) == len(states)
    for source, rendered in zip(states, compiled.states, strict=True):
        assert rendered.source_response_sha256 == source.source_response_sha256
        assert rendered.source_query_state_sha256 == source.source_query_state_sha256
        assert rendered.state_kind.startswith("node-context:")
        assert rendered.content != source.content
    rows = compiled.receipt["boundaries"]
    assert [row["boundary"]["boundary_id"] for row in rows] == [
        "B-CAND-REV", "B-DRAFT-REV",
    ]
    for row in rows:
        assert row["schema"] == NODE_CONTEXT_RECEIPT_SCHEMA
        assert row["level"] == "structured"
        assert row["parse_status"] == "parsed"
        assert row["fallback_applied"] is None
        assert row["cleaning_contact"] is None
        assert len(row["receipt_sha256"]) == 64
        assert row["template_sha256"] == hashlib.sha256(
            (REPO_ROOT / "configs" / row["template_id"]).read_bytes()
        ).hexdigest()


def test_raw_rows_carry_a_rendered_hash_equal_to_their_source_content_hash():
    """Design section 9: every boundary emits a row on every contact, and a
    ``level: "raw"`` row's ``rendered_sha256`` equals its source's
    ``content_sha256``. That equality is what makes L0's byte-identity claim a
    checked statement rather than a comment."""

    policy = _policy(level="raw")
    states = _reviewer_states()
    compiled = _compile(policy, "reviewer", states)
    assert compiled.states == tuple(states)
    rows = compiled.receipt["boundaries"]
    assert len(rows) == len(states)
    for row, source in zip(rows, states, strict=True):
        assert row["level"] == "raw"
        assert row["rendered_sha256"] == row["source"]["content_sha256"]
        assert row["rendered_sha256"] == hashlib.sha256(
            source.content.encode()
        ).hexdigest()
        assert row["template_id"] is None and row["parser_id"] is None


def test_fallback_raw_keeps_the_source_content_in_a_labelled_unparsed_block():
    policy = _policy()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", "not a draft at all"),
    ]
    compiled = _compile(policy, "reviewer", states)
    rendered = compiled.states[1].content
    assert "UNPARSED" in rendered
    assert "not a draft at all" in rendered
    row = compiled.receipt["boundaries"][1]
    assert row["parse_status"] == "malformed"
    assert row["fallback_applied"] == FALLBACK_RAW


def test_fallback_omit_is_implementable_and_never_a_default():
    """FALLBACK-OMIT is what ``rails.role_context._review_view`` does today,
    and on the anchor's prose Reviewer it would delete the review from the
    Planner's context on 100 % of rows. It stays implementable and is never a
    default: only a config that names it explicitly gets it."""

    assert FALLBACK_OMIT not in set(SLURP_BOUNDARY_PARSE_FAILURE.values())
    policy = _policy(boundaries={
        "planner:review-finding": {"level": "structured", "on_parse_failure": "omit"},
    })
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
        _state("reviewer:s1", "phase:reviewer", PROSE_REVIEW),
    ]
    compiled = _compile(policy, "planner", states)
    rendered = compiled.states[2].content
    assert PROSE_REVIEW not in rendered
    assert len(rendered.splitlines()) == 1
    assert compiled.receipt["boundaries"][2]["fallback_applied"] == FALLBACK_OMIT


def test_fallback_refuse_fails_the_row_on_an_unregistered_plan_action():
    policy = _policy()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
        _state("planner:s1", "phase:planner", "MAYBE"),
    ]
    with pytest.raises(NodeContextPolicyError, match="FALLBACK-REFUSE"):
        _compile(policy, "solver", states)
    good = list(states[:2]) + [_state("planner:s1", "phase:planner", "REVISE")]
    compiled = _compile(policy, "solver", good)
    assert "PLANNER DECISION: REVISE" in compiled.states[2].content


def test_the_prose_reviewer_of_the_anchor_renders_its_verbatim_block_for_the_planner():
    """The audit's sharpest number: 2,167 of 2,167 anchor Reviewer outputs fail
    the registered findings parser. Under FALLBACK-RAW that is exactly what the
    Planner is told it is getting."""

    policy = _policy()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
        _state("reviewer:s1", "phase:reviewer", PROSE_REVIEW),
    ]
    compiled = _compile(policy, "planner", states)
    review = compiled.states[2].content
    assert review.startswith("REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)")
    assert PROSE_REVIEW in review
    structured = _compile(policy, "planner", states[:2] + [
        _state("reviewer:s1", "phase:reviewer", REVIEW),
    ])
    row = structured.receipt["boundaries"][2]
    assert row["parse_status"] == "parsed"
    assert row["derived_fields"]["verdict"] == "supported-issue"
    assert row["derived_fields"]["citation_availability"] == [
        {"evidence_id": "evidence-one", "available": True},
        {"evidence_id": "evidence-absent", "available": False},
    ]


# ---------------------------------------------------------------------------
# HARNESS CHECKS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "draft,candidate_ids,expected",
    [
        (None, ["alarm_set"], (CHECK_NO, CHECK_NA, CHECK_NA)),
        (
            ParsedDraft("alarm", "set", (("time", "seven"),)),
            ["alarm_set", "alarm_remove"],
            (CHECK_YES, CHECK_YES, CHECK_YES),
        ),
        (
            ParsedDraft("calendar", "query", (("date", "friday"),)),
            ["alarm_set", "alarm_remove"],
            (CHECK_YES, CHECK_NO, CHECK_YES),
        ),
        (
            ParsedDraft("alarm", "set", (("guest", "ana"), ("time", "seven"))),
            ["alarm_set"],
            (CHECK_YES, CHECK_YES, f"{CHECK_NO} (guest)"),
        ),
        (
            ParsedDraft("alarm", "set", ()),
            None,
            (CHECK_YES, CHECK_NA, CHECK_YES),
        ),
    ],
)
def test_harness_checks_state_three_facts_and_take_no_position(
    draft, candidate_ids, expected
):
    """(d) the three deterministic checks -- draft parses / selected intent is
    a Perception candidate / every entity type is legal -- on synthetic drafts,
    each in both directions."""

    policy = _policy()
    _checks, values = policy.harness_checks(draft=draft, candidate_ids=candidate_ids)
    assert (
        values["check_parses"].value,
        values["check_candidate_member"].value,
        values["check_entity_types"].value,
    ) == expected


def test_without_a_declared_entity_inventory_the_type_check_says_so():
    policy = _policy(params={
        key: value for key, value in PARAMS.items() if key != "legal_entity_types"
    })
    _checks, values = policy.harness_checks(
        draft=ParsedDraft("alarm", "set", (("guest", "ana"),)),
        candidate_ids=["alarm_set"],
    )
    assert values["check_entity_types"].value == CHECK_NO_INVENTORY


def test_the_planner_brief_carries_the_checks_and_reads_no_gold():
    policy = _policy()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", OFF_LIST_DRAFT),
    ]
    compiled = _compile(policy, "planner", states)
    brief = compiled.states[1].content
    assert "DECISION BRIEF (revision 0 of 1; you may answer ACCEPT, REVISE)" in brief
    assert "HARNESS CHECKS" in brief
    assert "selected intent is one of the Perception candidates: NO" in brief
    assert "every entity type is in the legal inventory: NO (guest)" in brief
    checks = compiled.receipt["boundaries"][1]["derived_fields"]["harness_checks"]
    assert checks == {
        "draft_parses": True,
        "intent_among_candidates": False,
        "entity_types_legal": False,
        "illegal_entity_types": ["guest"],
    }


# ---------------------------------------------------------------------------
# "Adds no information"
# ---------------------------------------------------------------------------

_TOKEN = re.compile(r"[A-Za-z0-9_]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text))


def _allowed_tokens(policy, sources) -> set[str]:
    allowed: set[str] = set()
    for entry in policy.declared_boundaries():
        if entry["template_id"] is None:
            continue
        allowed |= _tokens(
            (REPO_ROOT / "configs" / entry["template_id"]).read_text(encoding="utf-8")
        )
    for source in sources:
        allowed |= _tokens(source)
        # The ONE composed value the design's templates introduce:
        # ``intent: {scenario}_{action}`` over two fields the same source
        # already carries (``rails.node_context_policy.PROVENANCE_COMPOSED``).
        try:
            document = json.loads(source)
        except ValueError:
            continue
        if isinstance(document, dict) and {"scenario", "action"} <= set(document):
            allowed.add(f"{document['scenario']}_{document['action']}")
    allowed |= set(LEGAL_INTENTS) | set(LEGAL_ENTITY_TYPES)
    for phrase in CLOSED_VOCABULARY:
        allowed |= _tokens(phrase)
    allowed |= _tokens(" ".join(str(value) for value in LIMITS.values()))
    allowed |= _tokens(" ".join(ACTIONS))
    return allowed


@pytest.mark.parametrize("role_kind", ["solver", "reviewer", "planner"])
def test_l1_adds_no_information(role_kind):
    """(c) every token of an L1 rendering that is not one of the template's own
    literal words occurs in the parsed upstream material, in the legal
    inventory the system contract already carries, in the closed vocabulary, or
    as a decimal count/limit the consumer's instruction already states."""

    policy = _policy()
    contents = [
        CANDIDATES, DRAFT, OFF_LIST_DRAFT, REVIEW, "REVISE", PROSE_REVIEW,
        "not a draft at all",
    ]
    for review_text in (REVIEW, PROSE_REVIEW):
        for draft_text in (DRAFT, OFF_LIST_DRAFT, "not a draft at all"):
            states = [
                _state("perception:s1", "phase:perception", CANDIDATES),
                _state("solver:s1", "phase:solver", draft_text),
                _state("reviewer:s1", "phase:reviewer", review_text),
                _state("planner:s1", "phase:planner", "REVISE"),
            ]
            compiled = _compile(policy, role_kind, states)
            allowed = _allowed_tokens(policy, contents)
            for rendered in compiled.states:
                leaked = {
                    token
                    for token in _tokens(rendered.content)
                    if token not in allowed and not token.isdigit()
                }
                assert not leaked, (role_kind, draft_text[:20], sorted(leaked))
            for row in compiled.receipt["boundaries"]:
                assert row["derived_fields"].get("gold") is None


def test_every_substitution_declares_where_its_value_came_from():
    policy = _policy()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
    ]
    block = policy._render_draft(
        policy.boundary_policy("reviewer", "current-draft"),
        state=states[1],
        drafts=policy._episode_drafts(states, ["candidate-hypothesis", "current-draft"]),
        candidates=policy._episode_candidates(
            states, ["candidate-hypothesis", "current-draft"], sample_id="s1",
        ),
        limits=LIMITS,
    )
    assert block.substitutions
    for substitution in block.substitutions:
        if substitution.provenance == "source-content":
            assert substitution.value in DRAFT or substitution.value in CANDIDATES
        elif substitution.provenance == "closed-vocabulary":
            assert substitution.value in CLOSED_VOCABULARY
        elif substitution.provenance == "source-composition":
            assert substitution.value in LEGAL_INTENTS


# ---------------------------------------------------------------------------
# The tool-observation boundary
# ---------------------------------------------------------------------------

_CONTRACT = "Task contract: " + ("answer the SLURP intent and slots. " * 40)
_SYSTEM_MESSAGE = "You are a speech agent.\n" + _CONTRACT + "\nEnd of contract."


def _tool_result_state() -> AgentStateArtifact:
    document = {
        "schema": "saea-phase-tool-result-v2",
        "tool_id": "saea-tool-task-contract-v1",
        "native_source_state_id": "reviewer:s1",
        "result": {"task_contract": _CONTRACT},
        "result_sha256": "b" * 64,
    }
    return _state("tool-result:reviewer:s1", "tool-result", json.dumps(document, sort_keys=True))


def test_the_tool_observation_references_the_contract_instead_of_repeating_it():
    """(e) the rendered observation never contains the system-prompt substring
    the audit measured at 13,634,712 characters over the run."""

    policy = _policy()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
        _state("reviewer:s1", "phase:reviewer", PROSE_REVIEW),
        _tool_result_state(),
    ]
    compiled = _compile(policy, "planner", states, task_instruction=_SYSTEM_MESSAGE)
    rendered = compiled.states[3].content
    assert _CONTRACT not in rendered
    assert "saea-tool-task-contract-v1" in rendered
    assert len(rendered) < len(states[3].content) - 1000
    document = json.loads(rendered)
    assert set(document) == set(json.loads(states[3].content))
    assert document["native_source_state_id"] == "reviewer:s1"
    row = compiled.receipt["boundaries"][3]
    assert row["boundary"]["boundary_id"] == "B-TOOL-PLANNER"
    assert row["derived_fields"]["source_contract_chars"] == len(_CONTRACT)
    # The state IDENTITY is preserved: the framework binds a tool result to its
    # call by state id and requires its custody fields to equal the source
    # phase state's.
    assert compiled.states[3].state_id == states[3].state_id
    assert compiled.states[3].producer_policy_id == states[3].producer_policy_id


def test_a_contract_that_is_not_in_the_system_message_is_left_verbatim():
    policy = _policy()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
        _state("reviewer:s1", "phase:reviewer", PROSE_REVIEW),
        _tool_result_state(),
    ]
    compiled = _compile(policy, "planner", states, task_instruction="something else")
    assert compiled.states[3].content == states[3].content
    assert compiled.receipt["boundaries"][3]["fallback_applied"] == FALLBACK_RAW


def test_the_producing_roles_own_live_tool_chain_is_never_rewritten():
    """The Reviewer's own second iteration replays its call and result inside
    its framework contract, whose bytes ``core.model.native_framework_history``
    verifies against the sealed observation. That chain stays verbatim; only a
    later role's REPLAY is referenced."""

    policy = _policy()
    tool_state = _tool_result_state()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
        _state("reviewer:s1", "phase:reviewer", PROSE_REVIEW),
        tool_state,
    ]
    compiled = _compile(
        policy, "reviewer", states, task_instruction=_SYSTEM_MESSAGE,
        local_tool_result_ids=(tool_state.state_id,),
    )
    assert compiled.states[3].content == tool_state.content
    assert compiled.receipt["boundaries"][3]["raw_reason"] == "live-tool-chain"
    # And the phase state the call was made from stays verbatim too.
    assert compiled.states[2].content == PROSE_REVIEW
    assert compiled.receipt["boundaries"][2]["raw_reason"] == "native-tool-call-source"


# ---------------------------------------------------------------------------
# Config surface
# ---------------------------------------------------------------------------


def test_raw_and_absent_are_the_same_off_arm():
    assert is_node_context_null_arm(None) is True
    assert is_node_context_null_arm("raw") is True
    assert is_node_context_null_arm({"level": "raw"}) is True
    assert is_node_context_null_arm(
        {"level": "raw", "boundaries": {"solver:current-draft": {"level": "raw"}}}
    ) is True
    assert is_node_context_null_arm({"level": "structured"}) is False
    assert is_node_context_null_arm(
        {"level": "raw", "boundaries": {"solver:current-draft": {"level": "structured"}}}
    ) is False


def test_cleaned_is_a_per_boundary_declaration_with_its_own_cleaning_block():
    """E8b supersedes E8a's ``E8b not implemented`` refusal. ``cleaned`` is now
    a real level, and every way of declaring it that does NOT name one bounded
    cleaning contact is still refused."""

    with pytest.raises(ValueError, match="bare 'cleaned'"):
        validate_node_context_policy_config("cleaned")
    with pytest.raises(ValueError, match="cannot default to 'cleaned'"):
        validate_node_context_policy_config({"level": "cleaned"})
    with pytest.raises(ValueError, match="requires a cleaning block"):
        validate_node_context_policy_config({
            "level": "structured",
            "policy_id": "typed-slurp-node-context-v1",
            "params": deepcopy(PARAMS),
            "boundaries": {"planner:review-finding": {"level": "cleaned"}},
        })
    with pytest.raises(ValueError, match="only a 'cleaned' boundary"):
        validate_node_context_policy_config({
            "level": "structured",
            "policy_id": "typed-slurp-node-context-v1",
            "params": deepcopy(PARAMS),
            "boundaries": {"planner:review-finding": {
                "cleaning": {"phase_id": "context_clean_review"},
            }},
        })


@pytest.mark.parametrize(
    "document,match",
    [
        ("structured", "bare 'structured'"),
        ("sideways", "must be one of"),
        ({"level": "structured"}, "policy_id"),
        (
            {"level": "structured", "policy_id": "unregistered", "params": PARAMS},
            "unregistered",
        ),
        (
            {"level": "structured", "policy_id": "typed-slurp-node-context-v1"},
            "requires params",
        ),
        (
            {"level": "structured", "policy_id": "typed-slurp-node-context-v1",
             "params": PARAMS, "boundaries": {"solver:nonsense": {}}},
            "not one of this carrier",
        ),
        (
            {"level": "structured", "policy_id": "typed-slurp-node-context-v1",
             "params": PARAMS, "producers": {"current-draft": {
                 "response_format_id": "saea-review-findings-v1"}}},
            "may not declare a response format",
        ),
        (
            {"level": "structured", "policy_id": "typed-slurp-node-context-v1",
             "params": PARAMS, "producers": {"review-finding": {
                 "response_format_id": "unregistered-format"}}},
            "unregistered-format",
        ),
        ({"level": "raw", "params": PARAMS}, "all-raw"),
    ],
)
def test_an_invalid_context_policy_is_refused(document, match):
    with pytest.raises(ValueError, match=match):
        validate_node_context_policy_config(deepcopy(document))


def test_the_review_findings_response_format_produces_what_its_parser_expects():
    """Coordinator decision 1: the Reviewer's registered ``response_format_id``
    produces exactly the document ``parse_review_findings`` accepts."""

    document = review_findings_response_format()
    assert document["type"] == "json_schema"
    assert document["json_schema"]["strict"] is True
    schema = document["json_schema"]["schema"]
    assert schema["required"] == [
        "schema", "verdict", "findings", "recommendation", "remaining_uncertainty",
    ]
    assert "uniqueItems" not in json.dumps(schema)
    assert parse_review_findings(REVIEW)["verdict"] == "supported-issue"
    assert REVIEW_FINDINGS_RESPONSE_FORMAT_ID == "saea-review-findings-v1"


# ---------------------------------------------------------------------------
# E2c composition
# ---------------------------------------------------------------------------


def test_the_committed_grouped_solver_draft_parses_under_l1_by_construction():
    """(g) E2c and E8a compose without a special case.

    E2c (``reproduction.ojw.native_group_solver``) is a PRODUCER-side seam: a
    grouped Solver visit registers ONE ``phase:<solver>`` state, the commit
    policy's aggregated answer re-rendered through ``_default_render_answer``.
    E8a is a CONSUMER-side seam: what each downstream node reads at the
    ``current-draft`` boundary. They stay separate because they answer
    different questions -- and they compose because the committed state has
    exactly the wire form a samples-1 Solver state has, so L1 parses it under
    the same closed contract and renders it through the same template.
    """

    from speech_aware_evidence_acquisition.reproduction.ojw.native_group_solver import (
        _default_render_answer,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        SlotEntity,
    )

    class _Answer:
        scenario = "alarm"
        action = "set"
        entities = (SlotEntity(type="time", filler="seven"),)

    committed = _default_render_answer(_Answer())
    policy = _policy()
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", committed),
    ]
    compiled = _compile(policy, "reviewer", states)
    row = compiled.receipt["boundaries"][1]
    assert row["parse_status"] == "parsed"
    assert row["fallback_applied"] is None
    assert row["derived_fields"]["intent_id"] == "alarm_set"
    assert "DRAFT UNDER REVIEW (Solver, parsed)" in compiled.states[1].content
    assert "entity:   time=seven" in compiled.states[1].content
