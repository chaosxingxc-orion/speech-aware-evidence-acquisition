"""E8b: the Node Context Policy at level L2 (``cleaned``), model-free.

Every test here drives the production policy object over synthetic
``AgentStateArtifact`` values and a FAKE cleaning invoker: no model, no
tokenizer, no server, no run directory. The production render path proof is
``tests/unit/test_node_context_policy_l2_runner.py``.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
sections 3 (L2), 4 (the cleaning template and its closed schema), 5, 7 (the
ceiling arithmetic), 9 (receipts) and 10 (the test plan).
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import RESPONSE_FORMATS
from speech_aware_evidence_acquisition.rails import controllers  # noqa: F401
from speech_aware_evidence_acquisition.rails.node_context_binding import (
    is_node_context_null_arm,
    node_context_cleaning_boundaries,
    validate_node_context_policy_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import (
    CLEANING_ACCEPTED,
    CLEANING_ISSUE_FIELDS,
    CLEANING_MAX_ISSUES,
    CLEANING_PROBLEM_MAX_CHARS,
    CLEANING_REJECTED,
    CLEANING_RESPONSE_FORMAT_ID,
    CLEANING_SCHEMA,
    CLEANING_SCHEMA_SHA256,
    CLEANING_SKIPPED,
    CLEANING_SUPERSEDED_REASON,
    CLEANING_VERDICTS,
    CleaningContactOutcome,
    NodeContextCleaningRejected,
    NodeContextPolicyError,
    build_slurp_node_context_policy,
    load_node_context_template,
    ncp_review_issues_response_format,
    validate_cleaning_document,
)

from test_node_context_policy import (
    ACTIONS,
    CANDIDATES,
    DRAFT,
    LEGAL_INTENTS,
    LIMITS,
    PARAMS,
    PHASE_IDS,
    PROSE_REVIEW,
    REPO_ROOT,
    _state,
)

# ---------------------------------------------------------------------------
# The committed cleaning assets, pinned.
#
# The cleaning contact's INSTRUCTION is these exact bytes plus the boundary's
# own L1 rendering -- never the task, never the answer schema, never a request
# for a new judgment. If either hash moves, the contract the cleaner reads
# moved with it and the cell that flew under the old one no longer describes
# this code.
# ---------------------------------------------------------------------------

CLEANING_INSTRUCTION_TEMPLATE = "probes/ncp_slurp_cleaning_review_v1.txt"
CLEANING_RENDER_TEMPLATE = "probes/ncp_slurp_cleaned_review_v1.txt"
CLEANING_INSTRUCTION_TEMPLATE_SHA256 = (
    "8231061e0a01e3a5d8fde0e1a4e153c2b731d0c2f90aac9beda585d066f4d96a"
)
CLEANING_RENDER_TEMPLATE_SHA256 = (
    "b901628473e405b7ef823b68c00e4d39b38d08783d9c9db93f5da969acdbd5ee"
)
PINNED_CLEANING_SCHEMA_SHA256 = (
    "c1ac021597e96f07c8740e71a7b058c99e3e5503c2220b950a82b98034ed8f7b"
)

CLEANING_BLOCK = {
    "phase_id": "context_clean_review",
    "instruction_template": CLEANING_INSTRUCTION_TEMPLATE,
    "response_format_id": CLEANING_RESPONSE_FORMAT_ID,
    "on_invalid": "fallback-l1",
}
CLEANED_BOUNDARY = {
    "level": "cleaned",
    "template": "probes/ncp_slurp_review_finding_v1.txt",
    "on_parse_failure": "raw",
    "cleaning": dict(CLEANING_BLOCK),
}

#: A cleaning output every one of whose content tokens occurs in the L1 block
#: the cleaner is handed (the FALLBACK-RAW rendering of ``PROSE_REVIEW``).
VALID_CLEANED = json.dumps({
    "verdict": "draft_has_issues",
    "issues": [{"field": "entity_filler", "problem": "the time reading is ambiguous"}],
})


def _policy(*, boundaries=None, level="structured"):
    return build_slurp_node_context_policy(
        repo_root=REPO_ROOT,
        policy_id="typed-slurp-node-context-v1",
        level=level,
        boundaries=boundaries if boundaries is not None else {
            "planner:review-finding": deepcopy(CLEANED_BOUNDARY),
        },
        legal_intent_ids=LEGAL_INTENTS,
        params=deepcopy(PARAMS),
    )


class _FakeCleaner:
    """One scripted cleaning contact. Records every request it was handed, so
    a test can prove there was exactly ONE attempt and no retry."""

    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        text = self.texts.pop(0) if self.texts else ""
        index = len(self.requests)
        return CleaningContactOutcome(
            agent_contact_id=f"fake-cleaning-contact-{index}",
            request_id=f"fake-request-{index}",
            request_sha256=hashlib.sha256(
                request.instruction.encode()
            ).hexdigest(),
            response_sha256=hashlib.sha256(f"response-{index}".encode()).hexdigest(),
            response_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
            text=text,
        )


def _planner_states(reviews=(PROSE_REVIEW,)):
    states = [
        _state("perception:s1", "phase:perception", CANDIDATES),
        _state("solver:s1", "phase:solver", DRAFT),
    ]
    for index, review in enumerate(reviews, start=1):
        states.append(_state(f"reviewer:s{index}", "phase:reviewer", review))
    return states


def _compile(policy, states, cleaner=None):
    return policy.compile(
        role_kind="planner",
        phase_ids=PHASE_IDS,
        sample_id="s1",
        states=states,
        available_evidence_ids=(),
        task_instruction="task contract",
        episode_limits=LIMITS,
        actions=ACTIONS,
        cleaning_invoker=cleaner,
    )


def _review_row(compiled):
    rows = [
        row for row in compiled.receipt["boundaries"]
        if row["boundary"]["boundary_id"] == "B-REVIEW-PLAN"
    ]
    assert rows
    return rows[-1]


def _rendered_review(compiled, states):
    index = len(states) - 1
    return compiled.states[index].content


# ---------------------------------------------------------------------------
# The committed assets
# ---------------------------------------------------------------------------


def test_the_cleaning_templates_are_committed_and_hash_pinned():
    """(c) the instruction the cleaner reads is a committed file, and these are
    its bytes."""

    instruction = load_node_context_template(REPO_ROOT, CLEANING_INSTRUCTION_TEMPLATE)
    render = load_node_context_template(REPO_ROOT, CLEANING_RENDER_TEMPLATE)
    assert instruction.renderer == "cleaning-review"
    assert render.renderer == "cleaned-review-finding"
    assert instruction.sha256 == CLEANING_INSTRUCTION_TEMPLATE_SHA256
    assert render.sha256 == CLEANING_RENDER_TEMPLATE_SHA256
    for relpath, template in (
        (CLEANING_INSTRUCTION_TEMPLATE, instruction),
        (CLEANING_RENDER_TEMPLATE, render),
    ):
        assert template.sha256 == hashlib.sha256(
            (REPO_ROOT / "configs" / relpath).read_bytes()
        ).hexdigest()
    text = (REPO_ROOT / "configs" / CLEANING_INSTRUCTION_TEMPLATE).read_text(
        encoding="utf-8"
    )
    # The four prohibitions design section 4 states, verbatim in substance.
    for clause in (
        "Do not add an issue the commentary does not state",
        "Do not judge the draft yourself",
        "Do not propose a replacement answer",
        "Do not mention the speech",
    ):
        assert clause in text
    # It never carries the task, the answer schema or a request for a verdict
    # about the speech.
    assert "scenario" in text and "entity_filler" in text
    assert "speech" in text


def test_the_cleaning_instruction_is_the_template_plus_the_l1_material_only():
    policy = _policy()
    entry = policy.boundary_policy("planner", "review-finding")
    instruction = entry.cleaning.instruction("L1 MATERIAL BLOCK")
    template = load_node_context_template(REPO_ROOT, CLEANING_INSTRUCTION_TEMPLATE)
    expected = "\n".join([
        *template.section("instruction"),
        *[
            line.replace("{structured_material}", "L1 MATERIAL BLOCK")
            for line in template.section("material")
        ],
    ])
    assert instruction == expected
    assert instruction.endswith("L1 MATERIAL BLOCK")


def test_the_cleaning_response_format_renders_the_closed_schema():
    document = RESPONSE_FORMATS.resolve(CLEANING_RESPONSE_FORMAT_ID)()
    assert document == ncp_review_issues_response_format()
    assert document["type"] == "json_schema"
    assert document["json_schema"]["strict"] is True
    schema = document["json_schema"]["schema"]
    assert schema == json.loads(json.dumps(CLEANING_SCHEMA))
    assert schema["properties"]["verdict"]["enum"] == list(CLEANING_VERDICTS)
    issues = schema["properties"]["issues"]
    assert issues["maxItems"] == CLEANING_MAX_ISSUES
    item = issues["items"]["properties"]
    assert item["field"]["enum"] == list(CLEANING_ISSUE_FIELDS)
    assert item["problem"]["maxLength"] == CLEANING_PROBLEM_MAX_CHARS
    assert CLEANING_SCHEMA_SHA256 == PINNED_CLEANING_SCHEMA_SHA256
    with pytest.raises(NodeContextPolicyError, match="no parameters"):
        ncp_review_issues_response_format(width=3)


# ---------------------------------------------------------------------------
# (a) accept, and the five ways to be refused
# ---------------------------------------------------------------------------


def test_an_accepted_cleaning_output_replaces_the_l1_block():
    """L1 first, then ONE contact, then the cleaned block -- and the receipt
    binds that contact by id and by request/response digest."""

    policy = _policy()
    states = _planner_states()
    cleaner = _FakeCleaner(VALID_CLEANED)
    compiled = _compile(policy, states, cleaner)

    assert len(cleaner.requests) == 1
    request = cleaner.requests[0]
    assert request.boundary_id == "B-REVIEW-PLAN"
    assert request.phase_id == "context_clean_review"
    assert request.knowledge == "none"
    assert request.response_format_id == CLEANING_RESPONSE_FORMAT_ID
    assert request.source_state_id == "reviewer:s1"
    # The cleaner was handed the L1 rendering and nothing else.
    assert PROSE_REVIEW in request.instruction
    assert "REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)" in request.instruction

    rendered = _rendered_review(compiled, states)
    assert "restated as structured issues by one cleaning contact" in rendered
    assert "verdict: draft_has_issues" in rendered
    assert "- entity_filler: the time reading is ambiguous" in rendered
    assert "UNPARSED REVIEW, VERBATIM" not in rendered

    row = _review_row(compiled)
    assert row["level"] == "cleaned"
    assert row["parse_status"] == "malformed"
    assert row["fallback_applied"] == "raw"
    assert row["derived_fields"] == {
        "verdict": "draft_has_issues",
        "issue_count": 1,
        "issue_fields": ["entity_filler"],
    }
    contact = row["cleaning_contact"]
    assert contact["validation"] == CLEANING_ACCEPTED
    assert contact["rejected_reason"] is None
    assert contact["agent_contact_id"] == "fake-cleaning-contact-1"
    assert contact["request_id"] == "fake-request-1"
    assert contact["request_sha256"] == hashlib.sha256(
        request.instruction.encode()
    ).hexdigest()
    assert len(contact["response_sha256"]) == 64
    assert len(contact["response_text_sha256"]) == 64
    assert contact["instruction_sha256"] == hashlib.sha256(
        request.instruction.encode()
    ).hexdigest()
    assert contact["phase_id"] == "context_clean_review"
    assert contact["knowledge"] == "none"
    assert contact["response_format_id"] == CLEANING_RESPONSE_FORMAT_ID
    assert contact["schema_sha256"] == CLEANING_SCHEMA_SHA256
    assert contact["instruction_template_sha256"] == CLEANING_INSTRUCTION_TEMPLATE_SHA256
    assert contact["render_template_sha256"] == CLEANING_RENDER_TEMPLATE_SHA256
    assert contact["on_invalid"] == "fallback-l1"


_INVALID_CLEANINGS = {
    "malformed-json": "{\"verdict\": \"draft_has_issues\", \"issues\": [",
    "enum-violation": json.dumps({
        "verdict": "looks-fine",
        "issues": [{"field": "entity_filler", "problem": "the time is ambiguous"}],
    }),
    "too-many-issues": json.dumps({
        "verdict": "draft_has_issues",
        "issues": [
            {"field": "entity_filler", "problem": "the time is ambiguous"}
        ] * (CLEANING_MAX_ISSUES + 1),
    }),
    "over-long-problem": json.dumps({
        "verdict": "draft_has_issues",
        "issues": [{"field": "entity_filler", "problem": "the " * 40}],
    }),
    "introduced-content": json.dumps({
        "verdict": "draft_has_issues",
        "issues": [{"field": "scenario", "problem": "the alarm scenario is wrong"}],
    }),
}


@pytest.mark.parametrize("case", sorted(_INVALID_CLEANINGS))
def test_an_invalid_cleaning_output_falls_back_to_the_l1_rendering(case):
    """(a) five invalid answers, one rule: the boundary renders exactly what L1
    already produced, the receipt says why, and there is no second attempt."""

    policy = _policy()
    states = _planner_states()
    cleaner = _FakeCleaner(_INVALID_CLEANINGS[case])
    compiled = _compile(policy, states, cleaner)

    assert len(cleaner.requests) == 1, "one attempt, one fallback, no retry"
    rendered = _rendered_review(compiled, states)
    assert "REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)" in rendered
    assert PROSE_REVIEW in rendered
    assert "restated as structured issues" not in rendered

    row = _review_row(compiled)
    assert row["level"] == "cleaned"
    contact = row["cleaning_contact"]
    assert contact["validation"] == CLEANING_REJECTED
    assert isinstance(contact["rejected_reason"], str) and contact["rejected_reason"]
    assert contact["agent_contact_id"] == "fake-cleaning-contact-1"
    # A rejection reason is a bounded machine phrase; it never quotes the
    # response text back into the receipt.
    assert _INVALID_CLEANINGS[case][:20] not in contact["rejected_reason"]


def test_an_empty_cleaning_answer_is_refused_like_any_other():
    policy = _policy()
    states = _planner_states()
    compiled = _compile(policy, states, _FakeCleaner(""))
    row = _review_row(compiled)
    assert row["cleaning_contact"]["validation"] == CLEANING_REJECTED
    assert "empty" in row["cleaning_contact"]["rejected_reason"]


# ---------------------------------------------------------------------------
# A cleaning contact may not introduce content
# ---------------------------------------------------------------------------


def test_a_cleaning_contact_may_not_introduce_content():
    material = "REVIEW (UNPARSED)\nthe time slot reading is ambiguous"
    accepted = validate_cleaning_document(
        json.dumps({
            "verdict": "draft_has_issues",
            "issues": [{"field": "entity_filler", "problem": "time slot ambiguous"}],
        }),
        source_material=material,
    )
    assert accepted.verdict == "draft_has_issues"
    assert accepted.issues == (("entity_filler", "time slot ambiguous"),)
    # Case is not content.
    assert validate_cleaning_document(
        json.dumps({
            "verdict": "draft_is_supported",
            "issues": [{"field": "none", "problem": "The TIME slot"}],
        }),
        source_material=material,
    ).issues == (("none", "The TIME slot"),)
    # A word the material does not carry is content, however plausible.
    with pytest.raises(NodeContextCleaningRejected, match="introduces content"):
        validate_cleaning_document(
            json.dumps({
                "verdict": "draft_has_issues",
                "issues": [{"field": "entity_filler", "problem": "the alarm is wrong"}],
            }),
            source_material=material,
        )
    # A blank problem restates nothing.
    with pytest.raises(NodeContextCleaningRejected, match="blank problem"):
        validate_cleaning_document(
            json.dumps({
                "verdict": "draft_has_issues",
                "issues": [{"field": "none", "problem": "   "}],
            }),
            source_material=material,
        )
    # An empty issue list is legal: it is the "nothing to restate" answer.
    assert validate_cleaning_document(
        json.dumps({"verdict": "draft_is_supported", "issues": []}),
        source_material=material,
    ).issues == ()


def test_an_accepted_cleaning_output_renders_only_cleaned_provenance():
    policy = _policy()
    entry = policy.boundary_policy("planner", "review-finding")
    cleaned = validate_cleaning_document(
        VALID_CLEANED,
        source_material="the time reading is ambiguous",
    )
    block = policy._render_cleaned(entry, cleaned=cleaned)
    assert block.substitutions
    assert {item.provenance for item in block.substitutions} == {"cleaning-contact"}


# ---------------------------------------------------------------------------
# One contact per consumer contact per boundary
# ---------------------------------------------------------------------------


def test_only_the_latest_source_at_a_cleaned_boundary_spends_a_contact():
    """The Planner at revision 2 holds both Reviewer outputs. One contact is
    spent, on the review it is deciding about; the earlier state takes its L1
    rendering and says so."""

    policy = _policy()
    earlier = "An earlier review with different words entirely."
    states = _planner_states(reviews=(earlier, PROSE_REVIEW))
    cleaner = _FakeCleaner(VALID_CLEANED)
    compiled = _compile(policy, states, cleaner)

    assert len(cleaner.requests) == 1
    assert cleaner.requests[0].source_state_id == "reviewer:s2"
    rows = [
        row for row in compiled.receipt["boundaries"]
        if row["boundary"]["boundary_id"] == "B-REVIEW-PLAN"
    ]
    assert [row["cleaning_contact"]["validation"] for row in rows] == [
        CLEANING_SKIPPED, CLEANING_ACCEPTED,
    ]
    assert rows[0]["cleaning_contact"]["rejected_reason"] == CLEANING_SUPERSEDED_REASON
    assert rows[0]["cleaning_contact"]["agent_contact_id"] is None
    assert earlier in compiled.states[2].content
    assert "restated as structured issues" in compiled.states[3].content


def test_a_cleaned_boundary_without_an_invoker_fails_the_contact():
    """Fail-closed: a policy that would clean but was handed no metered
    invoker never silently degrades to L1."""

    policy = _policy()
    with pytest.raises(NodeContextPolicyError, match="no metered cleaning invoker"):
        _compile(policy, _planner_states(), None)


def test_a_consumer_with_no_cleaned_boundary_spends_nothing():
    policy = _policy()
    states = _planner_states()
    cleaner = _FakeCleaner(VALID_CLEANED)
    compiled = policy.compile(
        role_kind="solver", phase_ids=PHASE_IDS, sample_id="s1", states=states,
        available_evidence_ids=(), task_instruction="task contract",
        episode_limits=LIMITS, actions=ACTIONS, cleaning_invoker=cleaner,
    )
    assert cleaner.requests == []
    assert all(
        row["cleaning_contact"] is None for row in compiled.receipt["boundaries"]
    )


def test_l1_and_l0_rows_carry_no_cleaning_block():
    """(d) E8b adds a field to a row only where a boundary is cleaned; L0 and
    L1 rows are what E8a pinned."""

    structured = build_slurp_node_context_policy(
        repo_root=REPO_ROOT, policy_id="typed-slurp-node-context-v1",
        level="structured", boundaries={}, legal_intent_ids=LEGAL_INTENTS,
        params=deepcopy(PARAMS),
    )
    compiled = _compile(structured, _planner_states(), None)
    assert all(
        row["cleaning_contact"] is None for row in compiled.receipt["boundaries"]
    )


# ---------------------------------------------------------------------------
# (b) the ceiling arithmetic
# ---------------------------------------------------------------------------


def _anchor_values(*, cleaned: bool):
    from test_native_episode_config import config

    values = config()
    values["native_episode"]["max_revisions"] = 1
    values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 3
    boundaries = {
        "planner:review-finding": deepcopy(CLEANED_BOUNDARY) if cleaned else {
            "level": "structured",
            "template": "probes/ncp_slurp_review_finding_v1.txt",
            "on_parse_failure": "raw",
        },
    }
    values["native_episode"]["context_policy"] = {
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": deepcopy(PARAMS),
        "boundaries": boundaries,
    }
    return values


def test_the_ceiling_arithmetic_takes_the_anchor_from_eleven_to_thirteen():
    """Design section 7: the anchor's shape (perception 1, solver 1, reviewer
    3, planner 1, max_revisions 1) has ceiling 11, and one cleaning boundary
    takes it to 13."""

    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )
    from test_role_context_binding import context_program

    program = context_program()
    assert load_native_episode_config(
        _anchor_values(cleaned=False), replace_ceiling(program, 11),
    ).max_contacts == 11
    cleaned = load_native_episode_config(
        _anchor_values(cleaned=True), replace_ceiling(program, 13),
    )
    assert cleaned.max_contacts == 13
    assert node_context_cleaning_boundaries(cleaned.context_policy_json) == (
        "planner:review-finding",
    )
    with pytest.raises(ValueError, match="ceiling"):
        load_native_episode_config(
            _anchor_values(cleaned=True), replace_ceiling(program, 11),
        )


def replace_ceiling(program, ceiling):
    from dataclasses import replace

    return replace(program, max_contacts=ceiling).validate()


def test_the_cleaning_phase_id_cannot_be_one_of_the_episode_phases():
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )
    from test_role_context_binding import context_program

    values = _anchor_values(cleaned=True)
    values["native_episode"]["context_policy"]["boundaries"][
        "planner:review-finding"
    ]["cleaning"]["phase_id"] = "planner"
    with pytest.raises(ValueError, match="cannot be one of the"):
        load_native_episode_config(values, replace_ceiling(context_program(), 13))


# ---------------------------------------------------------------------------
# (e) the config surface
# ---------------------------------------------------------------------------


def test_the_switch_key_accepts_cleaned_and_the_null_arm_is_unchanged():
    document = {
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": deepcopy(PARAMS),
        "boundaries": {"planner:review-finding": deepcopy(CLEANED_BOUNDARY)},
    }
    text = validate_node_context_policy_config(deepcopy(document))
    assert json.loads(text)["boundaries"]["planner:review-finding"]["level"] == "cleaned"
    assert node_context_cleaning_boundaries(text) == ("planner:review-finding",)
    # ``is_episode_null_arm`` semantics are exactly E8a's: a cleaned boundary
    # is not OFF, and every OFF shape still is.
    from speech_aware_evidence_acquisition.rails.config_tables import (
        is_episode_null_arm,
    )

    key = "native_episode.context_policy"
    assert is_episode_null_arm(key, document) is False
    assert is_node_context_null_arm(document) is False
    assert is_episode_null_arm(key, None) is True
    assert is_episode_null_arm(key, "raw") is True
    assert is_episode_null_arm(key, {"level": "raw"}) is True
    assert is_episode_null_arm(
        key, {"level": "raw", "boundaries": {"planner:review-finding": {"level": "raw"}}}
    ) is True
    assert node_context_cleaning_boundaries('"raw"') == ()


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda block: block.pop("on_invalid"), "exactly"),
        (lambda block: block.update(retry=True), "exactly"),
        (lambda block: block.update(on_invalid="retry-once"), "on_invalid must be"),
        (lambda block: block.update(phase_id=""), "phase_id must be text"),
        (
            lambda block: block.update(response_format_id="unregistered-format"),
            "unregistered-format",
        ),
        (
            lambda block: block.update(instruction_template="/etc/passwd"),
            "instruction_template must",
        ),
    ],
)
def test_an_invalid_cleaning_block_is_refused(mutate, match):
    document = {
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": deepcopy(PARAMS),
        "boundaries": {"planner:review-finding": deepcopy(CLEANED_BOUNDARY)},
    }
    mutate(document["boundaries"]["planner:review-finding"]["cleaning"])
    with pytest.raises(ValueError, match=match):
        validate_node_context_policy_config(document)


def test_only_a_class_with_a_registered_cleaning_renderer_may_be_cleaned():
    document = {
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": deepcopy(PARAMS),
        "boundaries": {"planner:current-draft": deepcopy(CLEANED_BOUNDARY)},
    }
    with pytest.raises(ValueError, match="cannot be cleaned"):
        validate_node_context_policy_config(document)
    with pytest.raises(NodeContextPolicyError, match="cannot be cleaned"):
        _policy(boundaries={"planner:current-draft": deepcopy(CLEANED_BOUNDARY)})


def test_the_declared_boundary_json_pins_all_three_committed_assets():
    policy = _policy()
    entry = [
        item for item in policy.declared_boundaries()
        if item["boundary"] == "planner:review-finding"
    ][0]
    assert entry["level"] == "cleaned"
    assert entry["template_id"] == "probes/ncp_slurp_review_finding_v1.txt"
    assert entry["cleaning"]["instruction_template_id"] == CLEANING_INSTRUCTION_TEMPLATE
    assert entry["cleaning"]["render_template_id"] == CLEANING_RENDER_TEMPLATE
    assert entry["cleaning"]["schema_sha256"] == CLEANING_SCHEMA_SHA256
    assert all(
        item["cleaning"] is None
        for item in policy.declared_boundaries()
        if item["boundary"] != "planner:review-finding"
    )


def test_the_cleaning_binding_pins_every_committed_template_hash(tmp_path):
    from speech_aware_evidence_acquisition.rails.node_context_binding import (
        build_node_context_policy_binding,
    )
    from test_role_context_binding import perception_format

    document = {
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": deepcopy(PARAMS),
        "boundaries": {"planner:review-finding": deepcopy(CLEANED_BOUNDARY)},
    }
    text = validate_node_context_policy_config(deepcopy(document))
    bound = build_node_context_policy_binding(
        text, perception_format(), Path(REPO_ROOT),
    )
    assert bound.template_sha256s[
        "planner:review-finding:cleaning-instruction"
    ] == CLEANING_INSTRUCTION_TEMPLATE_SHA256
    assert bound.template_sha256s[
        "planner:review-finding:cleaning-render"
    ] == CLEANING_RENDER_TEMPLATE_SHA256
