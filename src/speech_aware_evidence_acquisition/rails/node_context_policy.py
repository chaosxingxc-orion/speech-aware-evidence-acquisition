"""E8a/E8b: the Node Context Policy (NCP) -- one declared handling policy per
node boundary, levels L0 (``raw``), L1 (``structured``) and L2 (``cleaned``).

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
(sections 3-5, 9, 10). Evidence base:
``docs/results/2026-09-17-slurp-node-context-audit-v1.md``.

A **boundary** is the pair ``(consumer_role_kind, semantic_class)``: the same
producer output means different things to different consumers, which is why the
axis is the consumer's reading of the material and not the producer's contact.

The policy is a pure, deterministic, zero-contact TRANSFORM OVER THE ALREADY
SELECTED history. It never adds, drops, merges or reorders a state. That is
what makes L0 byte identity a checkable statement rather than an intention: at
``raw`` the transform is the identity function on every state, so the request
bytes are the pre-policy bytes by construction, and every ``raw`` receipt row
carries a ``rendered_sha256`` equal to its source's ``content_sha256``.

L1 is parse -> normalise -> render through a committed, hash-pinned template
file under ``configs/probes/``. Normalisation may only select, order and label
what the parse already found; it never reads gold, never retrieves, never
judges and never truncates a field's value. On a parse failure the boundary's
declared rule fires: ``FALLBACK-RAW`` (the default and the only rule this
module's SLURP defaults use), ``FALLBACK-OMIT`` (implemented, never a default)
or ``FALLBACK-REFUSE`` (``plan-action`` only, where the harness already
refuses).

L2 (``cleaned``, E8b) is L1 first and then ONE additional contact to the same
frozen core in the same resident session and geometry, composed by the same
``role_input`` / ``speech_binding`` path as every other contact, so it is
metered, budget-gated, exposure-bound, traced and costed identically and is
refused past ``config.max_contacts``. That contact's phase declares
``knowledge: "none"`` (no evidence blocks) and its own ``response_format_id``;
its instruction is a committed, hash-pinned template file carrying the cleaning
contract and the L1 material; its output is validated against the closed schema
:data:`CLEANING_SCHEMA` and against the rule that a cleaning contact MAY NOT
INTRODUCE CONTENT (every content token of an accepted output, outside the
schema's own fixed words, occurs in the L1 material it was handed). On ANY
validation failure the boundary falls back to its L1 rendering and the receipt
records ``validation: "rejected"`` with the reason: one attempt, one fallback,
no retry.

At most ONE cleaning contact is made per consumer contact per boundary. A
contact whose exposed history carries several states of one boundary (the
Planner at revision 2 sees both Reviewer outputs) cleans the LAST of them --
the one the design names "the review the Planner reads" -- and renders the
earlier ones at L1 with ``validation: "skipped"``. That is what makes the
contact-ceiling arithmetic of design section 7 exact.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from ..reproduction.slurp_scoring import parse_slu_response
from .knowledge import AgentStateArtifact, RailsError
from .review_findings import ReviewFindingsError, parse_review_findings
from .role_context import validate_role_context_draft_schema
from .scenario_hints import (
    NO_CUES,
    NO_NEIGHBOUR,
    SCENARIO_HINTS_RECEIPT_SCHEMA,
    ScenarioHintsBounds,
    ScenarioHintsTable,
    hint_counts,
    render_cues,
    render_leakage,
    scenario_hints,
)
from .slot_audit import (
    SLOT_AUDIT_RECEIPT_SCHEMA,
    SlotAuditFlag,
    SlotAuditTable,
    SlotAuditThresholds,
    flag_counts,
    profile_rows,
    render_share,
    slot_audit_flags,
)
from .slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS,
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    SlurpIntentHypothesisError,
    project_bounded_slurp_intent_hypotheses,
)

#: The registered id of the SLURP node-context policy (the value a fragment's
#: ``native_episode.context_policy.policy_id`` carries).
NODE_CONTEXT_POLICY_ID = "typed-slurp-node-context-v1"
#: The per-boundary, per-contact receipt row schema (design section 9).
NODE_CONTEXT_RECEIPT_SCHEMA = "saea-node-context-policy-v1"
#: The per-contact record that carries those rows.
NODE_CONTEXT_COMPILATION_SCHEMA = "saea-node-context-policy-compilation-v1"
#: Marker every committed template file's first line carries.
NODE_CONTEXT_TEMPLATE_SCHEMA = "saea-node-context-template-v1"

#: The three levels. ``raw`` is L0 and the OFF arm; ``structured`` is L1;
#: ``cleaned`` is L2.
LEVELS = ("raw", "structured", "cleaned")
#: The ``cleaning`` block's declared fields (design section 5), exactly.
CLEANING_KEYS = frozenset({
    "phase_id", "instruction_template", "response_format_id", "on_invalid",
})
#: The only admitted ``on_invalid`` rule: fall back to the L1 rendering.
CLEANING_FALLBACK_L1 = "fallback-l1"
CLEANING_INVALID_RULES = (CLEANING_FALLBACK_L1,)
#: Every validation status a ``cleaning_contact`` receipt block may carry.
CLEANING_ACCEPTED = "accepted"
CLEANING_REJECTED = "rejected"
CLEANING_SKIPPED = "skipped"
#: The reason a boundary state that is not the contact's LAST at that boundary
#: carries: it takes its L1 rendering and spends no contact.
CLEANING_SUPERSEDED_REASON = "superseded by a later source at this boundary"

#: The cleaning contact's closed output vocabulary (design section 4).
CLEANING_VERDICTS = ("draft_is_supported", "draft_has_issues")
CLEANING_ISSUE_FIELDS = (
    "scenario", "action", "entity_type", "entity_filler", "none",
)
CLEANING_MAX_ISSUES = 5
CLEANING_PROBLEM_MAX_CHARS = 140

#: The closed JSON schema a cleaning response is validated against, verbatim
#: from design section 4. The additional rules the schema cannot state (a
#: ``problem`` that is blank, and the "introduces no content" property) live in
#: :func:`validate_cleaning_document`, the same division
#: ``rails.review_findings.parse_review_findings`` already uses.
CLEANING_SCHEMA: Mapping[str, object] = {
    "type": "object", "additionalProperties": False,
    "required": ["verdict", "issues"],
    "properties": {
        "verdict": {"enum": list(CLEANING_VERDICTS)},
        "issues": {
            "type": "array", "maxItems": CLEANING_MAX_ISSUES,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["field", "problem"],
                "properties": {
                    "field": {"enum": list(CLEANING_ISSUE_FIELDS)},
                    "problem": {
                        "type": "string", "maxLength": CLEANING_PROBLEM_MAX_CHARS,
                    },
                },
            },
        },
    },
}
#: The registered ``core.base.RESPONSE_FORMATS`` id the cleaning phase declares.
CLEANING_RESPONSE_FORMAT_ID = "ncp-review-issues-v1"
#: The words the closed schema itself fixes. Everything else an accepted
#: cleaning output carries must occur in the L1 material it was handed.
CLEANING_FIXED_WORDS: tuple[str, ...] = (
    *CLEANING_VERDICTS, *CLEANING_ISSUE_FIELDS, "verdict", "issues", "field",
    "problem",
)

#: Declared malformed rules (design section 3, L1 step 4).
FALLBACK_RAW = "raw"
FALLBACK_OMIT = "omit"
FALLBACK_REFUSE = "refuse"
PARSE_FAILURE_RULES = (FALLBACK_RAW, FALLBACK_OMIT, FALLBACK_REFUSE)

ROLE_KINDS = ("perception", "solver", "reviewer", "planner")

#: E18 (2026-09-19, owner decisions 43-44): the sixth node's own role kind.
#: It is NOT in :data:`ROLE_KINDS` because that tuple is the set of CONSUMER
#: role kinds a boundary policy may be declared for, and no node consumes
#: context from the Acquisition node's seat -- the Acquisition node is a
#: PRODUCER only. Its phase id reaches :meth:`SlurpNodeContextPolicy.compile`
#: through the optional ``"acquisition"`` entry of ``phase_ids``.
ACQUISITION_ROLE_KIND = "acquisition"

SEMANTIC_CLASSES = (
    "candidate-hypothesis",
    "current-draft",
    "review-finding",
    "plan-action",
    "tool-observation",
    # E18: what the Acquisition node puts into the trajectory. It is a
    # semantic class of its own rather than a second spelling of
    # ``supplied-evidence`` because the consumer must be able to tell
    # pre-contact supply (chosen before the row's first contact, by the
    # supply policy) from evidence acquired ON DEMAND mid-episode, by a node,
    # after a draft was reviewed -- those are different SUPPLY decisions and
    # a cell that moves one must stay distinguishable from a cell that moves
    # the other.
    "acquired-evidence",
)

#: The SLURP native episode's boundaries, with the design's own ids: the eight
#: model-text boundaries plus the tool-observation boundary, whose id is
#: ``B-TOOL-<ROLE>`` because the design writes it ``B-TOOL-*``.
SLURP_BOUNDARY_IDS: Mapping[tuple[str, str], str] = {
    ("solver", "candidate-hypothesis"): "B-CAND-SOL",
    ("reviewer", "candidate-hypothesis"): "B-CAND-REV",
    ("reviewer", "current-draft"): "B-DRAFT-REV",
    ("planner", "current-draft"): "B-DRAFT-PLAN",
    ("solver", "current-draft"): "B-DRAFT-SOL",
    ("planner", "review-finding"): "B-REVIEW-PLAN",
    ("solver", "review-finding"): "B-REVIEW-SOL",
    ("solver", "plan-action"): "B-PLAN-SOL",
    ("perception", "tool-observation"): "B-TOOL-PERCEPTION",
    ("solver", "tool-observation"): "B-TOOL-SOLVER",
    ("reviewer", "tool-observation"): "B-TOOL-REVIEWER",
    ("planner", "tool-observation"): "B-TOOL-PLANNER",
}

#: Each boundary's default committed template (design section 4).
SLURP_BOUNDARY_TEMPLATES: Mapping[tuple[str, str], str] = {
    ("solver", "candidate-hypothesis"): "probes/ncp_slurp_candidate_hypothesis_v1.txt",
    ("reviewer", "candidate-hypothesis"): "probes/ncp_slurp_candidate_hypothesis_v1.txt",
    ("reviewer", "current-draft"): "probes/ncp_slurp_current_draft_reviewer_v1.txt",
    ("planner", "current-draft"): "probes/ncp_slurp_planner_brief_v1.txt",
    ("solver", "current-draft"): "probes/ncp_slurp_current_draft_solver_v1.txt",
    ("planner", "review-finding"): "probes/ncp_slurp_review_finding_v1.txt",
    ("solver", "review-finding"): "probes/ncp_slurp_review_finding_v1.txt",
    ("solver", "plan-action"): "probes/ncp_slurp_plan_action_v1.txt",
    ("perception", "tool-observation"): "probes/ncp_slurp_tool_observation_v1.txt",
    ("solver", "tool-observation"): "probes/ncp_slurp_tool_observation_v1.txt",
    ("reviewer", "tool-observation"): "probes/ncp_slurp_tool_observation_v1.txt",
    ("planner", "tool-observation"): "probes/ncp_slurp_tool_observation_v1.txt",
}

#: E8b: the committed template each cleaning-capable SEMANTIC CLASS renders an
#: ACCEPTED cleaning output through. The key is the semantic class, not the
#: boundary, so both ``review-finding`` consumers (Planner and revising Solver)
#: clean identically; a class with no entry may not be declared ``cleaned``.
CLEANING_RENDER_TEMPLATES: Mapping[str, str] = {
    "review-finding": "probes/ncp_slurp_cleaned_review_v1.txt",
}

#: E8b: the committed instruction template each cleaning-capable semantic class
#: defaults to. A boundary's ``cleaning.instruction_template`` may name it
#: explicitly; it may not name a template written for another class, because
#: the renderer key is checked when the template is loaded.
CLEANING_INSTRUCTION_TEMPLATES: Mapping[str, str] = {
    "review-finding": "probes/ncp_slurp_cleaning_review_v1.txt",
}

#: E12 (2026-09-19, owner directive 26, cell B8b): the ONE boundary the
#: Reviewer slot-audit block is appended at, and the committed template it is
#: rendered through. The block is an ADDITION to that boundary's own L1
#: rendering, never a replacement: the draft block above it is produced by the
#: same code and the same template as on the base, which is what keeps the
#: cell one factor and makes "everything outside this boundary is byte
#: identical" a checkable statement.
SLOT_AUDIT_BOUNDARY: tuple[str, str] = ("reviewer", "current-draft")

#: E19 (2026-09-19): the two ways an armed audit block attaches to that
#: boundary. It is an ADDITION either way -- what differs is the ONE thing
#: it is added to. ``l1-rendering`` is E12's own: the block follows the
#: boundary's structured rendering. ``sealed-draft`` is E19's: the boundary
#: stays at ``raw``, the sealed Solver bytes go out exactly as they are, and
#: the block follows them -- which is what lets a cell move the audit ALONE
#: on a base that declares no node-context policy at all.
SLOT_AUDIT_ATTACHMENT_L1 = "l1-rendering"
SLOT_AUDIT_ATTACHMENT_RAW = "sealed-draft"
SLOT_AUDIT_ATTACHMENTS: tuple[str, ...] = (
    SLOT_AUDIT_ATTACHMENT_L1, SLOT_AUDIT_ATTACHMENT_RAW,
)
SLOT_AUDIT_TEMPLATE = "probes/ncp_slurp_slot_audit_reviewer_v1.txt"
SLOT_AUDIT_RENDERER = "slot-audit"

#: E14 (2026-09-19, owner directive 26, cell B8c): the ONE boundary the
#: Solver scenario-hints block is appended at, and the committed template it
#: is rendered through. Like the E12 audit block it is an ADDITION to that
#: boundary's own L1 rendering, never a replacement: the candidate list above
#: it is produced by the same code and the same template as on the base,
#: which is what keeps the cell one factor and makes "everything outside this
#: boundary is byte identical" a checkable statement. The REVIEWER's own
#: candidate-hypothesis boundary is deliberately NOT this one: the hints are
#: for the node that CHOOSES between the candidates.
SOLVER_HINTS_BOUNDARY: tuple[str, str] = ("solver", "candidate-hypothesis")
SOLVER_HINTS_TEMPLATE = "probes/ncp_slurp_scenario_hints_solver_v1.txt"
SOLVER_HINTS_RENDERER = "scenario-hints"

#: E18 (2026-09-19, owner decisions 43-44): the NEW boundary the Acquisition
#: node produces at, ``acquisition -> solver``, carrying the semantic class
#: ``acquired-evidence``. It is declared here, beside the twelve boundaries of
#: :data:`SLURP_BOUNDARY_IDS`, and deliberately NOT added to that mapping: the
#: boundaries of that map are the pairs a declared ``native_episode.
#: context_policy`` resolves an entry for on EVERY episode, and an unarmed
#: episode has no acquisition node at all, so a thirteenth always-resolved
#: entry would put a boundary into every policy object that no state can ever
#: reach. The Acquisition node renders its own block through this committed
#: template instead, exactly as the E12 audit and the E14 hints render theirs,
#: and the rendered state is then classified ``acquired-evidence`` for any
#: consumer whose ``phase_ids`` names the acquisition phase.
ACQUIRED_EVIDENCE_BOUNDARY: tuple[str, str] = ("solver", "acquired-evidence")
ACQUIRED_EVIDENCE_BOUNDARY_ID = "B-ACQ-SOL"
ACQUIRED_EVIDENCE_TEMPLATE = "probes/ncp_acquired_evidence_solver_v1.txt"
ACQUIRED_EVIDENCE_RENDERER = "acquired-evidence"

#: The closed phrase an acquisition that returned nothing renders instead of
#: an item list. Part of the block's closed vocabulary.
NO_ACQUIRED_EVIDENCE = "nothing new was acquired for this row"

#: The default malformed rule per boundary. ``FALLBACK-RAW`` everywhere the
#: design proposes to fly; ``plan-action`` refuses, because the harness already
#: fails a row whose Planner emitted an unregistered action token.
SLURP_BOUNDARY_PARSE_FAILURE: Mapping[tuple[str, str], str] = {
    boundary: (FALLBACK_REFUSE if boundary[1] == "plan-action" else FALLBACK_RAW)
    for boundary in SLURP_BOUNDARY_IDS
}

#: Registered parser ids, recorded per receipt row so a row names the exact
#: rule that judged its source.
PARSER_IDS: Mapping[str, str] = {
    "candidate-hypothesis": (
        "rails.slurp_intent_hypotheses.project_bounded_slurp_intent_hypotheses"
    ),
    "current-draft": "reproduction.slurp_scoring.parse_slu_response",
    "review-finding": "rails.review_findings.parse_review_findings",
    "plan-action": "rails.node_context_policy.parse_plan_action",
    "tool-observation": "rails.node_context_policy.parse_tool_observation",
    # E37 (owner decision 84, 2026-09-22): the primitive-verdict parser
    # alongside the declared-but-unreachable JSON one above. Registered here
    # so a later NCP arm can render the token structurally; no boundary of
    # SLURP_BOUNDARY_IDS names "review-primitive" today, so the locked plan
    # (NCP off) and every existing boundary's FALLBACK-RAW default are
    # untouched by this entry.
    "review-primitive": "rails.review_primitives.parse_review_primitive",
}

#: The renderer key each boundary expects of its template.
RENDERER_KEYS: Mapping[tuple[str, str], str] = {
    ("solver", "candidate-hypothesis"): "candidate-hypothesis",
    ("reviewer", "candidate-hypothesis"): "candidate-hypothesis",
    ("reviewer", "current-draft"): "current-draft-reviewer",
    ("solver", "current-draft"): "current-draft-solver",
    ("planner", "current-draft"): "planner-brief",
    ("planner", "review-finding"): "review-finding",
    ("solver", "review-finding"): "review-finding",
    ("solver", "plan-action"): "plan-action",
    ("perception", "tool-observation"): "tool-observation",
    ("solver", "tool-observation"): "tool-observation",
    ("reviewer", "tool-observation"): "tool-observation",
    ("planner", "tool-observation"): "tool-observation",
}

#: Sections each renderer requires of its template, and the placeholders each
#: section may carry. A template with an unknown section, a missing section or
#: an unknown placeholder is refused when it is loaded -- never half-rendered.
RENDERER_SECTIONS: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "candidate-hypothesis": {
        "header": ("count", "max_candidates"),
        "item": ("position", "intent_id", "distinction"),
        "items_empty": (),
        "footer": (),
        "header_unparsed": (),
        "unparsed": ("source_content",),
        "omitted": ("reason",),
    },
    "current-draft-reviewer": {
        "header": (),
        "body": ("scenario", "action", "intent_id", "candidate_membership"),
        "item": ("entity_type", "entity_filler"),
        "items_empty": (),
        "footer": (),
        "header_unparsed": (),
        "unparsed": ("source_content",),
        "omitted": ("reason",),
    },
    "current-draft-solver": {
        "header": ("revision_index", "max_revisions"),
        "body": ("scenario", "action"),
        "item": ("entity_type", "entity_filler"),
        "items_empty": (),
        "footer": (),
        "header_unparsed": ("revision_index", "max_revisions"),
        "unparsed": ("source_content",),
        "omitted": ("reason",),
    },
    "planner-brief": {
        "header": ("revision_index", "max_revisions", "available_actions"),
        "body": ("scenario", "action", "intent_id"),
        "item": ("entity_type", "entity_filler"),
        "items_empty": (),
        "checks": ("check_parses", "check_candidate_member", "check_entity_types"),
        "footer": (),
        "header_unparsed": ("revision_index", "max_revisions", "available_actions"),
        "unparsed": ("source_content",),
        "omitted": ("reason",),
    },
    "review-finding": {
        "header": (),
        "body": ("verdict", "recommendation", "remaining_uncertainty"),
        "item": ("dimension", "rationale"),
        "items_empty": (),
        "citation": ("evidence_id", "availability"),
        "citations_empty": (),
        "footer": (),
        "header_unparsed": (),
        "unparsed": ("source_content",),
        "omitted": ("reason",),
    },
    "plan-action": {
        "header": ("action",),
        "footer": ("revisions_remaining", "available_actions"),
    },
    "tool-observation": {"reference": ("tool_id",)},
    # E37 (owner decision 84, 2026-09-22): the primitive-verdict renderer
    # section, declared so a later NCP arm has a template contract to render
    # against -- no boundary of SLURP_BOUNDARY_IDS/RENDERER_KEYS names
    # "review-primitive" today, so no template is loaded through it and this
    # entry changes nothing reachable by the locked plan. ``body`` carries
    # the parsed token; the rationale beside it is free text and is never a
    # placeholder (rails.review_primitives.parse_review_primitive never
    # parses it either).
    "review-primitive": {
        "header": (),
        "body": ("token",),
        "footer": (),
        "header_unparsed": (),
        "unparsed": ("source_content",),
        "omitted": ("reason",),
    },
    # E8b. ``cleaning-review`` is the INSTRUCTION the cleaning contact reads;
    # ``cleaned-review-finding`` is how an ACCEPTED cleaning output is rendered
    # into the consumer's context. Both are ordinary committed templates, so
    # both are hash-pinned in the receipt and both are refused at load time
    # when a section or a placeholder is missing.
    "cleaning-review": {"instruction": (), "material": ("structured_material",)},
    "cleaned-review-finding": {
        "header": (),
        "body": ("verdict",),
        "item": ("field", "problem"),
        "items_empty": (),
        "footer": (),
    },
    # E12. The Reviewer slot-audit block: the intent's construction profile
    # and the deterministic flags, appended after the draft block at
    # ``reviewer:current-draft``.
    SLOT_AUDIT_RENDERER: {
        "header": ("view_id", "intent_id"),
        "profile_header": ("intent_rows", "empty_share"),
        "profile_item": ("entity_type", "type_share"),
        "profile_empty": (),
        "flag": ("flag", "detail"),
        "flags_empty": (),
        "footer": (),
    },
    # E14. The Solver scenario-hints block: each Perception candidate's
    # construction confusion neighbours and the construction cue words that
    # discriminate the candidate from each neighbour, appended after the
    # candidate list at ``solver:candidate-hypothesis``.
    SOLVER_HINTS_RENDERER: {
        "header": ("view_id",),
        "candidate": ("intent_id", "intent_rows"),
        "neighbour": ("intent_id", "neighbour_id", "leakage", "cues"),
        "neighbour_empty": ("reason",),
        "candidate_empty": (),
        "footer": (),
    },
    # E18. The Acquisition node's own block: what the ``acquire`` primitive
    # brought into the trajectory, rendered once at the ``acquisition ->
    # solver`` boundary. ``content`` is the acquired item's own typed text
    # (a knowledge value, or one re-observation's candidate hypotheses);
    # ``evidence_id``/``source_id`` are its provenance.
    ACQUIRED_EVIDENCE_RENDERER: {
        "header": ("count", "kind", "policy_id"),
        "item": ("position", "evidence_id", "source_id", "content"),
        "items_empty": ("reason",),
        "footer": (),
    },
}

# -- the closed vocabulary a rendering may introduce ------------------------
#
# Everything a rendering emits is a template literal, a value the parse found
# in the source, a legal id of the bound inventory, a decimal count, an episode
# limit the consumer's own instruction already carries -- or one of these fixed
# English phrases. The "adds no information" property test (design section 10)
# reads exactly this set.
AMONG_CANDIDATES = "among the Perception candidates"
NOT_AMONG_CANDIDATES = "NOT among the Perception candidates"
CANDIDATES_UNAVAILABLE = "Perception candidates unavailable"
EVIDENCE_AVAILABLE = "available"
EVIDENCE_UNAVAILABLE = "not available in this context"
CHECK_YES = "yes"
CHECK_NO = "NO"
CHECK_NA = "n/a"
CHECK_NO_INVENTORY = "n/a (no inventory declared)"
CLOSED_VOCABULARY: tuple[str, ...] = (
    AMONG_CANDIDATES,
    NOT_AMONG_CANDIDATES,
    CANDIDATES_UNAVAILABLE,
    EVIDENCE_AVAILABLE,
    EVIDENCE_UNAVAILABLE,
    CHECK_YES,
    CHECK_NO,
    CHECK_NA,
    CHECK_NO_INVENTORY,
    # E14: the scenario-hints block's own two closed phrases, declared in
    # ``rails.scenario_hints`` beside the rule that emits them.
    NO_CUES,
    NO_NEIGHBOUR,
)

#: The tool whose result the ``tool-observation`` boundary may reference rather
#: than repeat, and the result field it references.
TASK_CONTRACT_TOOL_ID = "saea-tool-task-contract-v1"
TASK_CONTRACT_RESULT_FIELD = "task_contract"

_SECTION_PATTERN = re.compile(r"^\[([a-z_]+)\]$")
_PLACEHOLDER_PATTERN = re.compile(r"\{([a-z_]+)\}")
_TEMPLATE_RELPATH_PATTERN = re.compile(r"^probes/[A-Za-z0-9_.\-]+\.txt$")


class NodeContextPolicyError(ValueError):
    """A node-context policy, template or rendering is invalid."""


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=True, allow_nan=False, sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise NodeContextPolicyError("node context values must be finite JSON") from error


def _unique_object(pairs):
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise NodeContextPolicyError("node context source JSON repeats a key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise NodeContextPolicyError("node context source JSON has a nonfinite constant")


def _strict_json(text: str) -> object:
    """The same strictness ``rails.role_context`` applies: no duplicate keys,
    no NaN/Infinity, no text repair."""

    try:
        return json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as error:
        raise NodeContextPolicyError("node context source is not strict JSON") from error


# ---------------------------------------------------------------------------
# Committed templates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeContextTemplate:
    """One committed, hash-pinned template file under ``configs/probes/``.

    The file is a marker line plus ``[section]`` blocks. A section body is its
    lines verbatim; a placeholder is ``{name}`` and every name is declared by
    the renderer, so an unknown placeholder or a missing section is refused at
    load time rather than reaching a model half-rendered.
    """

    template_id: str
    renderer: str
    sha256: str
    sections: Mapping[str, tuple[str, ...]]

    def section(self, name: str) -> tuple[str, ...]:
        try:
            return self.sections[name]
        except KeyError:
            raise NodeContextPolicyError(
                f"template {self.template_id!r} has no section {name!r}"
            ) from None

    def literal_tokens(self) -> frozenset[str]:
        """Every whitespace-separated token of the template's own text, with
        placeholders removed. The "adds no information" test's allowed token
        set starts here."""

        tokens: set[str] = set()
        for lines in self.sections.values():
            for line in lines:
                tokens.update(_PLACEHOLDER_PATTERN.sub(" ", line).split())
        return frozenset(tokens)


def parse_node_context_template(text: str, *, template_id: str) -> NodeContextTemplate:
    """Parse one template's bytes into its sections, or refuse."""

    if not isinstance(text, str) or not text.strip():
        raise NodeContextPolicyError(f"node context template {template_id!r} is empty")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    marker = lines[0].split()
    if (
        len(marker) != 3
        or marker[0] != "#"
        or marker[1] != NODE_CONTEXT_TEMPLATE_SCHEMA
        or not marker[2].startswith("renderer=")
    ):
        raise NodeContextPolicyError(
            f"node context template {template_id!r} must open with "
            f"'# {NODE_CONTEXT_TEMPLATE_SCHEMA} renderer=<key>'"
        )
    renderer = marker[2].removeprefix("renderer=")
    if renderer not in RENDERER_SECTIONS:
        raise NodeContextPolicyError(
            f"node context template {template_id!r} names unknown renderer {renderer!r}"
        )
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[1:]:
        match = _SECTION_PATTERN.fullmatch(line)
        if match is not None:
            current = match.group(1)
            if current in sections:
                raise NodeContextPolicyError(
                    f"node context template {template_id!r} repeats section {current!r}"
                )
            sections[current] = []
            continue
        if current is None:
            raise NodeContextPolicyError(
                f"node context template {template_id!r} has text before its first section"
            )
        sections[current].append(line)
    declared = RENDERER_SECTIONS[renderer]
    if set(sections) != set(declared):
        raise NodeContextPolicyError(
            f"node context template {template_id!r} declares sections "
            f"{sorted(sections)}; renderer {renderer!r} requires {sorted(declared)}"
        )
    for name, body in sections.items():
        if not any(line.strip() for line in body):
            raise NodeContextPolicyError(
                f"node context template {template_id!r} section {name!r} is empty"
            )
        placeholders = {
            found for line in body for found in _PLACEHOLDER_PATTERN.findall(line)
        }
        unknown = sorted(placeholders - set(declared[name]))
        if unknown:
            raise NodeContextPolicyError(
                f"node context template {template_id!r} section {name!r} carries "
                f"unknown placeholders {unknown}"
            )
        for line in body:
            stripped = _PLACEHOLDER_PATTERN.sub("", line)
            if "{" in stripped or "}" in stripped:
                raise NodeContextPolicyError(
                    f"node context template {template_id!r} section {name!r} carries "
                    "an unrecognised brace"
                )
    return NodeContextTemplate(
        template_id=template_id,
        renderer=renderer,
        sha256=_sha256_text(text),
        sections={name: tuple(body) for name, body in sorted(sections.items())},
    )


_TEMPLATE_CACHE: dict[tuple[str, str], NodeContextTemplate] = {}


def load_node_context_template(repo_root: Path, relpath: str) -> NodeContextTemplate:
    """Read, validate and cache one committed template under ``configs/``."""

    if not isinstance(relpath, str) or not _TEMPLATE_RELPATH_PATTERN.fullmatch(relpath):
        raise NodeContextPolicyError(
            f"node context template {relpath!r} must be a plain 'probes/<name>.txt' "
            "path under configs/ (no absolute path, no '..', no backslash)"
        )
    root = Path(repo_root).resolve()
    key = (str(root), relpath)
    cached = _TEMPLATE_CACHE.get(key)
    if cached is not None:
        return cached
    path = root / "configs" / relpath
    if not path.is_file():
        raise NodeContextPolicyError(f"node context template missing: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise NodeContextPolicyError(
            f"cannot read node context template {path}: {error}"
        ) from error
    template = parse_node_context_template(text, template_id=relpath)
    _TEMPLATE_CACHE[key] = template
    return template


# ---------------------------------------------------------------------------
# Rendering with provenance
# ---------------------------------------------------------------------------

#: Where one substituted value came from. Every substitution carries one, and
#: no rendering may introduce a value without one.
PROVENANCE_SOURCE = "source-content"
PROVENANCE_COMPOSED = "source-composition"
PROVENANCE_INVENTORY = "legal-inventory"
PROVENANCE_VOCABULARY = "closed-vocabulary"
PROVENANCE_COUNT = "count"
PROVENANCE_LIMIT = "episode-limit"
#: E8b: a value one accepted cleaning contact produced. It is not a free value:
#: :func:`validate_cleaning_document` has already proved that every one of its
#: content tokens occurs in the L1 material that contact was handed, or is one
#: of the closed schema's own fixed words.
PROVENANCE_CLEANED = "cleaning-contact"
#: E12: a value read off the PINNED slot-audit table -- a construction count,
#: a construction share, or a released representation sentence. It is not a
#: free value either: the table is two hash-pinned committed files, mined from
#: the construction pool alone and carrying no filler, no sentence and no gold
#: of any evaluated row (``rails.slot_audit``).
PROVENANCE_AUDIT = "slot-audit-table"
#: E14: a value read off the PINNED scenario-hints table -- a construction
#: row count, a construction k-NN leakage rate, or a construction cue word.
#: It is not a free value either: the table is two hash-pinned released
#: files, mined from the construction pool alone and carrying no utterance
#: id, no recording and no gold of any evaluated row
#: (``rails.scenario_hints``).
PROVENANCE_HINTS = "scenario-hints-table"
#: E18: a value the Acquisition node's registered policy acquired -- one
#: frozen-store knowledge value's own content, or one re-observation's own
#: model bytes -- carried with the provenance id the acquisition receipt
#: names. It is not a free value either: a policy may only return material a
#: bound acquisition callback handed it, and the receipt binds that material
#: by hash (``rails.acquisition``).
PROVENANCE_ACQUIRED = "acquired-evidence"
PROVENANCES = (
    PROVENANCE_SOURCE,
    PROVENANCE_COMPOSED,
    PROVENANCE_INVENTORY,
    PROVENANCE_VOCABULARY,
    PROVENANCE_COUNT,
    PROVENANCE_LIMIT,
    PROVENANCE_CLEANED,
    PROVENANCE_AUDIT,
    PROVENANCE_HINTS,
    PROVENANCE_ACQUIRED,
)


@dataclass(frozen=True)
class Substitution:
    """One ``{field}`` the renderer replaced, and where its value came from."""

    field_name: str
    value: str
    provenance: str

    def __post_init__(self) -> None:
        if self.provenance not in PROVENANCES:
            raise NodeContextPolicyError(
                f"unknown substitution provenance {self.provenance!r}"
            )


@dataclass(frozen=True)
class RenderedBlock:
    """One boundary's rendered text, with every substitution it made."""

    text: str
    substitutions: tuple[Substitution, ...] = ()
    derived_fields: Mapping[str, object] = field(default_factory=dict)


class _Block:
    """Accumulate rendered lines and the substitutions actually used."""

    def __init__(self, template: NodeContextTemplate) -> None:
        self._template = template
        self._lines: list[str] = []
        self._substitutions: list[Substitution] = []

    def add(self, section: str, values: Mapping[str, Substitution] | None = None) -> None:
        available = dict(values or {})
        used: list[str] = []

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            try:
                substitution = available[name]
            except KeyError:
                raise NodeContextPolicyError(
                    f"node context rendering has no value for {name!r}"
                ) from None
            used.append(name)
            return substitution.value

        for line in self._template.section(section):
            self._lines.append(_PLACEHOLDER_PATTERN.sub(replace, line))
        for name in used:
            self._substitutions.append(available[name])

    def finish(self, derived_fields: Mapping[str, object]) -> RenderedBlock:
        return RenderedBlock(
            text="\n".join(self._lines),
            substitutions=tuple(self._substitutions),
            derived_fields=dict(derived_fields),
        )


def _text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise NodeContextPolicyError(f"node context {field_name} must be text")
    return value


def render_acquired_evidence(
    template: NodeContextTemplate,
    *,
    kind: str,
    policy_id: str,
    items: Sequence[Mapping[str, str]],
    reason: str = NO_ACQUIRED_EVIDENCE,
) -> RenderedBlock:
    """Render the ``acquisition -> solver`` block (E18).

    The block is produced by the Acquisition node itself rather than by a
    boundary policy, because there is no upstream MODEL TEXT to re-render: the
    node's output is already typed, and this template is what turns the typed
    record into the one text form every consumer reads. Zero contacts; every
    substituted value is either the acquisition's own record (kind, policy id,
    item count), one acquired item's provenance ids and content, or the
    module's one closed phrase.

    ``items`` entries carry exactly ``evidence_id``, ``source_id`` and
    ``content``; the position is the renderer's own 1-based counter.
    """

    if template.renderer != ACQUIRED_EVIDENCE_RENDERER:
        raise NodeContextPolicyError(
            f"the acquired-evidence block requires a {ACQUIRED_EVIDENCE_RENDERER!r} "
            f"template; {template.template_id!r} declares {template.renderer!r}"
        )
    rows = list(items)
    block = _Block(template)
    block.add("header", {
        "count": Substitution("count", str(len(rows)), PROVENANCE_COUNT),
        "kind": Substitution("kind", kind, PROVENANCE_VOCABULARY),
        "policy_id": Substitution("policy_id", policy_id, PROVENANCE_VOCABULARY),
    })
    if not rows:
        block.add("items_empty", {
            "reason": Substitution("reason", reason, PROVENANCE_VOCABULARY),
        })
    for position, row in enumerate(rows, start=1):
        missing = {"evidence_id", "source_id", "content"} - set(row)
        if missing or set(row) - {"evidence_id", "source_id", "content"}:
            raise NodeContextPolicyError(
                "an acquired-evidence item must carry exactly evidence_id, "
                "source_id and content"
            )
        block.add("item", {
            "position": Substitution("position", str(position), PROVENANCE_COUNT),
            "evidence_id": Substitution(
                "evidence_id",
                _text(row["evidence_id"], field_name="acquired evidence_id"),
                PROVENANCE_ACQUIRED,
            ),
            "source_id": Substitution(
                "source_id",
                _text(row["source_id"], field_name="acquired source_id"),
                PROVENANCE_ACQUIRED,
            ),
            "content": Substitution(
                "content",
                _text(row["content"], field_name="acquired content"),
                PROVENANCE_ACQUIRED,
            ),
        })
    block.add("footer")
    return block.finish({})


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_plan_action(text: str, *, actions: Sequence[str]) -> str:
    """The Planner's action token, by exact text match against the registered
    action set -- the only admission the harness itself already applies."""

    if not isinstance(text, str):
        raise NodeContextPolicyError("plan action must be text")
    candidate = text.strip()
    if candidate not in tuple(actions):
        raise NodeContextPolicyError("plan action is not a registered episode action")
    return candidate


def parse_tool_observation(
    content: str, *, task_instruction: str,
) -> tuple[Mapping[str, object], str]:
    """One tool-result envelope whose ``result`` is exactly the task contract
    already carried by this request's system message.

    Returns ``(document, contract)``. Refuses unless the contract really is a
    substring of ``task_instruction``: that substring test is what makes the
    reference rendering provably information-free rather than a compression the
    consumer has to take on trust.
    """

    document = _strict_json(content)
    if not isinstance(document, Mapping):
        raise NodeContextPolicyError("tool observation is not an object")
    result = document.get("result")
    if (
        document.get("tool_id") != TASK_CONTRACT_TOOL_ID
        or not isinstance(result, Mapping)
        or set(result) != {TASK_CONTRACT_RESULT_FIELD}
        or not isinstance(result[TASK_CONTRACT_RESULT_FIELD], str)
        or not result[TASK_CONTRACT_RESULT_FIELD]
    ):
        raise NodeContextPolicyError(
            "tool observation is not a task-contract result this policy may reference"
        )
    contract = result[TASK_CONTRACT_RESULT_FIELD]
    if not isinstance(task_instruction, str) or contract not in task_instruction:
        raise NodeContextPolicyError(
            "tool observation contract is not a substring of the system message"
        )
    return document, contract


@dataclass(frozen=True)
class ParsedDraft:
    """One Solver draft, exactly as the closed draft contract found it."""

    scenario: str
    action: str
    entities: tuple[tuple[str, str], ...]

    @property
    def intent_id(self) -> str:
        return f"{self.scenario}_{self.action}"


#: E19: the carrier's own closed draft contract, exactly as
#: ``rails.role_context.validate_role_context_draft_schema`` requires it --
#: an object, closed, with exactly ``scenario`` / ``action`` / ``entities``,
#: each entity exactly ``type`` / ``filler``. Every structured config
#: declares these same bytes in
#: ``context_policy.params.draft_response_schema``; this constant is what an
#: audit attached to the SEALED draft binds instead, so the two attachments
#: read a draft under one contract rather than two.
#: ``tests/unit/test_reviewer_slot_audit_block.py`` proves that equality
#: against the committed L1 fragment.
SLURP_CLOSED_DRAFT_SCHEMA: Mapping[str, object] = {
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


def parse_draft(text: str, *, validator: Draft202012Validator) -> ParsedDraft:
    """The Solver draft under the same closed contract the typed role context
    already applies (``rails.role_context._draft_view``): strict JSON, the
    closed draft schema, and the carrier's own ``parse_slu_response``."""

    document = _strict_json(text)
    if not isinstance(document, Mapping) or "entities" not in document:
        raise NodeContextPolicyError("a SLURP draft must explicitly declare entities")
    try:
        validator.validate(document)
    except ValidationError as error:
        raise NodeContextPolicyError(
            "draft does not match the closed draft schema"
        ) from error
    scenario, action, entities, parsed = parse_slu_response(text)
    if not parsed:
        raise NodeContextPolicyError("a schema-valid SLURP draft must parse")
    return ParsedDraft(
        scenario=scenario,
        action=action,
        entities=tuple((entity.type, entity.filler) for entity in entities),
    )


# ---------------------------------------------------------------------------
# E8b: the cleaning contact
# ---------------------------------------------------------------------------


_CONTENT_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")

_CLEANING_VALIDATOR = Draft202012Validator(CLEANING_SCHEMA)
#: The hash of the closed schema itself, pinned in every cleaning receipt.
CLEANING_SCHEMA_SHA256 = _sha256_text(_canonical_json(CLEANING_SCHEMA))


class NodeContextCleaningRejected(NodeContextPolicyError):
    """One cleaning response failed validation, so its boundary falls back to
    its L1 rendering. Carries a bounded, content-free machine reason: a reason
    never quotes the response, because a receipt is not a place for model text
    the run has not otherwise sealed."""


def ncp_review_issues_response_format(
    _lock: object = None, _root: object = None, **params: object,
) -> dict[str, object]:
    """The ``core.base.RESPONSE_FORMATS`` entry
    :data:`CLEANING_RESPONSE_FORMAT_ID`.

    It renders :data:`CLEANING_SCHEMA` itself, so a response generated under
    this format satisfies the schema half of
    :func:`validate_cleaning_document` by construction and the validator stays
    the authority on what the schema cannot say (a blank ``problem``, and the
    "introduces no content" property).
    """

    if params:
        raise NodeContextPolicyError(
            "the node-context cleaning response format takes no parameters"
        )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ncp_review_issues_v1",
            "strict": True,
            "schema": json.loads(_canonical_json(CLEANING_SCHEMA)),
        },
    }


def content_tokens(text: str) -> frozenset[str]:
    """The case-folded content tokens of one text. Case is not content, so the
    containment rule below folds it; everything else is compared literally."""

    return frozenset(
        token.casefold() for token in _CONTENT_TOKEN_PATTERN.findall(text)
    )


@dataclass(frozen=True)
class CleanedReview:
    """One accepted cleaning output: a closed verdict and at most five issues,
    each naming a closed field and a bounded problem statement."""

    verdict: str
    issues: tuple[tuple[str, str], ...]


def validate_cleaning_document(text: str, *, source_material: str) -> CleanedReview:
    """Validate one cleaning response, or refuse it with a bounded reason.

    Three gates, in order, each fail-closed: strict JSON (no duplicate keys, no
    nonfinite constants, no text repair); the closed schema
    :data:`CLEANING_SCHEMA`; and the rule that a cleaning contact MAY NOT
    INTRODUCE CONTENT -- every content token the response carries is either one
    of the schema's own fixed words (:data:`CLEANING_FIXED_WORDS`) or occurs in
    ``source_material``, the exact L1 rendering that contact was handed.
    """

    if not isinstance(text, str) or not text.strip():
        raise NodeContextCleaningRejected("cleaning response is empty")
    if len(text) > 16384:
        raise NodeContextCleaningRejected("cleaning response is unbounded")
    try:
        document = _strict_json(text)
    except NodeContextPolicyError:
        raise NodeContextCleaningRejected(
            "cleaning response is not strict JSON"
        ) from None
    try:
        _CLEANING_VALIDATOR.validate(document)
    except ValidationError:
        raise NodeContextCleaningRejected(
            "cleaning response does not match the closed cleaning schema"
        ) from None
    issues = tuple(
        (issue["field"], issue["problem"]) for issue in document["issues"]
    )
    for _field_name, problem in issues:
        if not problem.strip():
            raise NodeContextCleaningRejected("cleaning response states a blank problem")
    allowed = content_tokens(source_material) | content_tokens(
        " ".join(CLEANING_FIXED_WORDS)
    )
    for field_name, problem in issues:
        if not content_tokens(f"{field_name} {problem}") <= allowed:
            raise NodeContextCleaningRejected(
                "cleaning response introduces content the L1 material does not carry"
            )
    if document["verdict"] not in CLEANING_VERDICTS:  # pragma: no cover -- schema
        raise NodeContextCleaningRejected("cleaning response states no closed verdict")
    return CleanedReview(verdict=document["verdict"], issues=issues)


@dataclass(frozen=True)
class CleaningContactRequest:
    """What the policy asks the runner to contact the frozen core with.

    The policy composes the instruction and validates the answer; the runner
    owns metering, budget, exposure, tracing and cost. Neither reaches into the
    other, which is what lets every rule in
    :func:`validate_cleaning_document` be proved with a fake invoker and no
    model.
    """

    boundary_id: str
    consumer_role_kind: str
    semantic_class: str
    phase_id: str
    response_format_id: str
    knowledge: str
    instruction: str
    instruction_sha256: str
    source_state_id: str


@dataclass(frozen=True)
class CleaningContactOutcome:
    """The runner's answer: one ordinary contact's identity, digests and text."""

    agent_contact_id: str
    request_id: str
    request_sha256: str
    response_sha256: str
    response_text_sha256: str
    text: str

    def __post_init__(self) -> None:
        for name in (
            "agent_contact_id", "request_id", "request_sha256", "response_sha256",
            "response_text_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise NodeContextPolicyError(
                    f"a cleaning contact outcome requires {name}"
                )
        if not isinstance(self.text, str):
            raise NodeContextPolicyError("a cleaning contact outcome requires text")


@dataclass(frozen=True)
class NodeContextCleaningPolicy:
    """One boundary's declared cleaning contact (design section 5)."""

    phase_id: str
    instruction_template: NodeContextTemplate
    render_template: NodeContextTemplate
    response_format_id: str
    on_invalid: str

    #: The cleaning contact's phase declares no knowledge: its request carries
    #: the system contract, the speech packet and its own instruction, and no
    #: evidence block at all.
    knowledge: str = "none"

    def as_json(self) -> dict[str, object]:
        return {
            "phase_id": self.phase_id,
            "knowledge": self.knowledge,
            "response_format_id": self.response_format_id,
            "on_invalid": self.on_invalid,
            "instruction_template_id": self.instruction_template.template_id,
            "instruction_template_sha256": self.instruction_template.sha256,
            "render_template_id": self.render_template.template_id,
            "render_template_sha256": self.render_template.sha256,
            "schema_sha256": CLEANING_SCHEMA_SHA256,
        }

    def instruction(self, l1_material: str) -> str:
        """The exact bytes the cleaning contact reads: the committed contract,
        then the L1 material, and nothing else -- never the task, never the
        answer schema, never a request for a new judgment."""

        block = _Block(self.instruction_template)
        block.add("instruction")
        block.add("material", {
            "structured_material": Substitution(
                "structured_material", l1_material, PROVENANCE_SOURCE,
            ),
        })
        return block.finish({}).text


# ---------------------------------------------------------------------------
# The policy object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeContextBoundaryPolicy:
    """One boundary's declared handling: its level, its template and its rule
    for a malformed upstream output."""

    consumer_role_kind: str
    semantic_class: str
    level: str
    template: NodeContextTemplate | None
    on_parse_failure: str
    #: E8b: the declared cleaning contact, present exactly when the level is
    #: ``cleaned`` and ``None`` at every other level.
    cleaning: NodeContextCleaningPolicy | None = None

    @property
    def boundary_id(self) -> str:
        return SLURP_BOUNDARY_IDS.get(
            (self.consumer_role_kind, self.semantic_class), "B-UNDECLARED"
        )

    def as_json(self) -> dict[str, object]:
        return {
            "boundary": f"{self.consumer_role_kind}:{self.semantic_class}",
            "boundary_id": self.boundary_id,
            "level": self.level,
            "template_id": None if self.template is None else self.template.template_id,
            "template_sha256": None if self.template is None else self.template.sha256,
            "on_parse_failure": self.on_parse_failure,
            "cleaning": None if self.cleaning is None else self.cleaning.as_json(),
        }


@dataclass(frozen=True)
class SlotAuditBinding:
    """E12: the armed Reviewer slot-audit block -- table, thresholds, template.

    Present exactly when ``native_episode.reviewer_audit`` is armed; ``None``
    on every other flight, where the boundary renders the pre-E12 bytes.
    """

    table: SlotAuditTable
    thresholds: SlotAuditThresholds
    template: NodeContextTemplate

    def receipt(
        self,
        *,
        applied: bool,
        intent_id: str | None = None,
        flags: Sequence[object] = (),
        block_text: str | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        """The per-contact audit receipt block, the same shape whether the
        block was rendered or not."""

        document: dict[str, object] = {
            "schema": SLOT_AUDIT_RECEIPT_SCHEMA,
            "view_id": self.table.view_id,
            "release_sha256": self.table.release_sha256,
            "snapshot_sha256": self.table.snapshot_sha256,
            "table_content_hash": self.table.content_hash(),
            "template_id": self.template.template_id,
            "template_sha256": self.template.sha256,
            "thresholds": self.thresholds.as_json(),
            "applied": applied,
            "reason": reason,
            "intent_id": intent_id,
            "intent_in_table": (
                None if intent_id is None else intent_id in self.table.intents
            ),
            "block_sha256": None if block_text is None else _sha256_text(block_text),
            "block_chars": None if block_text is None else len(block_text),
            "flag_counts": flag_counts(list(flags)),
            "flags": [flag.as_json() for flag in flags],
        }
        return document


@dataclass(frozen=True)
class SolverHintsBinding:
    """E14: the armed Solver scenario-hints block -- table, bounds, template.

    Present exactly when ``native_episode.solver_hints`` is armed; ``None``
    on every other flight, where the boundary renders the pre-E14 bytes.
    """

    table: ScenarioHintsTable
    bounds: ScenarioHintsBounds
    template: NodeContextTemplate

    def receipt(
        self,
        *,
        applied: bool,
        candidate_ids: Sequence[str] = (),
        hints: Sequence[object] = (),
        block_text: str | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        """The per-contact hints receipt block, the same shape whether the
        block was rendered or not."""

        return {
            "schema": SCENARIO_HINTS_RECEIPT_SCHEMA,
            "view_id": self.table.view_id,
            "release_sha256": self.table.release_sha256,
            "snapshot_sha256": self.table.snapshot_sha256,
            "table_content_hash": self.table.content_hash(),
            "template_id": self.template.template_id,
            "template_sha256": self.template.sha256,
            "bounds": self.bounds.as_json(),
            "applied": applied,
            "reason": reason,
            "candidate_ids": [str(candidate) for candidate in candidate_ids],
            "covered_intent_ids": [hint.intent for hint in hints],
            "block_sha256": (
                None if block_text is None else _sha256_text(block_text)
            ),
            "block_chars": None if block_text is None else len(block_text),
            "counts": hint_counts(list(hints)),
            "hints": [hint.as_json() for hint in hints],
        }


@dataclass(frozen=True)
class NodeContextCompilation:
    """The exposed states one contact actually receives, and its receipt."""

    states: tuple[AgentStateArtifact, ...]
    receipt: Mapping[str, object]


def known_tool_call_sources(states: Sequence[AgentStateArtifact]) -> set[str]:
    """Every phase state that a tool-result envelope names as its source.

    Those states carry the model's own tool-calling turn and their bytes are
    verified against the framework's source authority
    (``core.model.native_history._bound_result`` requires
    ``content_sha256 == source_response_sha256``), so the policy never derives
    over them -- it records a ``raw`` row with that reason instead.
    """

    sources: set[str] = set()
    for state in states:
        if state.state_kind != "tool-result":
            continue
        try:
            document = json.loads(state.content)
        except (TypeError, ValueError):
            continue
        if isinstance(document, Mapping) and isinstance(
            document.get("native_source_state_id"), str
        ):
            sources.add(document["native_source_state_id"])
    return sources


class SlurpNodeContextPolicy:
    """The SLURP carrier's node-context policy: one entry per boundary, and a
    pure transform over one contact's exposed history."""

    def __init__(
        self,
        *,
        policy_id: str,
        boundaries: Mapping[tuple[str, str], NodeContextBoundaryPolicy],
        legal_intent_ids: Sequence[str] = (),
        max_candidates: int | None = None,
        projection_policy: str | None = None,
        draft_response_schema: Mapping[str, object] | None = None,
        legal_entity_types: Sequence[str] = (),
        slot_audit: SlotAuditBinding | None = None,
        solver_hints: SolverHintsBinding | None = None,
    ) -> None:
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise NodeContextPolicyError("node context policy_id must be text")
        self.slot_audit = slot_audit
        #: E19: which of :data:`SLOT_AUDIT_ATTACHMENTS` an armed audit takes,
        #: and ``None`` when none is armed.
        self.slot_audit_attachment: str | None = None
        if slot_audit is not None:
            entry = boundaries.get(SLOT_AUDIT_BOUNDARY)
            audit_level = "raw" if entry is None else entry.level
            if audit_level == "cleaned":
                raise NodeContextPolicyError(
                    "the reviewer slot-audit block cannot attach to the "
                    f"{SLOT_AUDIT_BOUNDARY[0]}:{SLOT_AUDIT_BOUNDARY[1]} boundary at "
                    "level 'cleaned'; a cleaning contact rewrites the rendering "
                    "the block is appended to, so the block would be cleaned away"
                )
            # E19 (owner decision 32): E12 required 'structured' here, because
            # the block was an addition to that boundary's L1 rendering and had
            # nothing to attach to at raw. Cell B7a v2 read the L1 policy
            # HARMFUL, so the block is re-based: at raw it is appended to the
            # SEALED draft bytes, which is an addition to exactly the one thing
            # the Reviewer would otherwise have received.
            self.slot_audit_attachment = (
                SLOT_AUDIT_ATTACHMENT_L1 if audit_level == "structured"
                else SLOT_AUDIT_ATTACHMENT_RAW
            )
        self.solver_hints = solver_hints
        if solver_hints is not None:
            entry = boundaries.get(SOLVER_HINTS_BOUNDARY)
            if entry is None or entry.level != "structured":
                raise NodeContextPolicyError(
                    "the solver scenario-hints block requires the "
                    f"{SOLVER_HINTS_BOUNDARY[0]}:{SOLVER_HINTS_BOUNDARY[1]} boundary "
                    "at level 'structured'; it is an addition to that boundary's own "
                    "L1 rendering, not a level of its own"
                )
        if not any(entry.level != "raw" for entry in boundaries.values()):
            # An ALL-RAW policy parses nothing and renders nothing, so it needs
            # no candidate inventory, no draft contract and no template. It
            # still compiles: every state passes through untouched and every
            # boundary emits its ``level: "raw"`` receipt row, which is what
            # makes L0's byte-identity claim a checked statement (design
            # section 9) rather than the absence of evidence.
            self.policy_id = policy_id
            self.boundaries = dict(boundaries)
            self.legal_intent_ids = ()
            self.max_candidates = 0
            self.projection_policy = None
            self.legal_entity_types = ()
            # E19: an all-raw policy parses nothing OF ITS OWN. An audit
            # attached to the sealed draft still has to read the draft it is
            # auditing, so the carrier's closed draft contract is bound HERE
            # and used for nothing else -- every other boundary still passes
            # its state through untouched.
            self._validator = (
                None if slot_audit is None
                else validate_role_context_draft_schema(
                    SLURP_CLOSED_DRAFT_SCHEMA if draft_response_schema is None
                    else draft_response_schema
                )
            )
            return
        legal = tuple(legal_intent_ids)
        if (
            not legal
            or any(not isinstance(item, str) or not item.strip() for item in legal)
            or len(legal) != len(set(legal))
        ):
            raise NodeContextPolicyError("legal_intent_ids must be non-empty and unique")
        if (
            isinstance(max_candidates, bool)
            or not isinstance(max_candidates, int)
            or not 1 <= max_candidates <= len(legal)
        ):
            raise NodeContextPolicyError("max_candidates must fit the legal inventory")
        if projection_policy not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS:
            raise NodeContextPolicyError("projection_policy is unsupported")
        if (
            max_candidates > 3
            and projection_policy
            != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        ):
            raise NodeContextPolicyError(
                "candidate bounds above three require the configurable policy"
            )
        entity_types = tuple(legal_entity_types)
        if any(
            not isinstance(item, str) or not item.strip() for item in entity_types
        ) or len(entity_types) != len(set(entity_types)):
            raise NodeContextPolicyError(
                "legal_entity_types must be unique non-empty strings"
            )
        self.policy_id = policy_id
        self.boundaries = dict(boundaries)
        self.legal_intent_ids = legal
        self.max_candidates = max_candidates
        self.projection_policy = projection_policy
        self.legal_entity_types = entity_types
        self._validator = validate_role_context_draft_schema(draft_response_schema)

    # -- boundary lookup ----------------------------------------------------

    def boundary_policy(
        self, role_kind: str, semantic_class: str,
    ) -> NodeContextBoundaryPolicy | None:
        return self.boundaries.get((role_kind, semantic_class))

    def declared_boundaries(self) -> list[dict[str, object]]:
        return [policy.as_json() for _key, policy in sorted(self.boundaries.items())]

    # -- compilation --------------------------------------------------------

    def compile(
        self,
        *,
        role_kind: str,
        phase_ids: Mapping[str, str],
        sample_id: str,
        states: Sequence[AgentStateArtifact],
        local_tool_result_ids: Sequence[str] = (),
        available_evidence_ids: Sequence[str] = (),
        task_instruction: str = "",
        episode_limits: Mapping[str, object] | None = None,
        actions: Sequence[str] = (),
        cleaning_invoker: object = None,
    ) -> NodeContextCompilation:
        """Return one contact's exposed states and its per-boundary receipt.

        The returned tuple has exactly the length and order of ``states``: this
        transform never adds, drops, merges or reorders a state.

        ``cleaning_invoker`` (E8b) is the runner's metered contact hook, a
        ``CleaningContactRequest -> CleaningContactOutcome`` callable. It is
        REQUIRED when any declared boundary is ``cleaned`` and unused
        otherwise: a policy that would clean but was handed no invoker fails
        the contact rather than silently degrading to L1.
        """

        if role_kind not in ROLE_KINDS:
            raise NodeContextPolicyError("role_kind is unsupported")
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise NodeContextPolicyError("sample_id must be a non-empty string")
        try:
            phases = {kind: phase_ids[kind] for kind in ROLE_KINDS}
        except (KeyError, TypeError) as error:
            raise NodeContextPolicyError(
                "phase_ids must map exactly the four native role kinds"
            ) from error
        # E18: one OPTIONAL fifth entry, the acquisition phase of an armed
        # episode. Absent -- every pre-E18 caller and every unarmed episode --
        # ``phases`` is exactly the four-entry mapping it always was and an
        # acquisition state could not exist to classify anyway.
        acquisition_phase = phase_ids.get(ACQUISITION_ROLE_KIND)
        if acquisition_phase is not None:
            if not isinstance(acquisition_phase, str) or not acquisition_phase.strip():
                raise NodeContextPolicyError(
                    "phase_ids acquisition entry must be a non-empty phase id"
                )
            phases[ACQUISITION_ROLE_KIND] = acquisition_phase
        state_list = list(states)
        for state in state_list:
            if not isinstance(state, AgentStateArtifact):
                raise NodeContextPolicyError(
                    "states must contain AgentStateArtifact values"
                )
            try:
                state.validate()
            except RailsError as error:
                raise NodeContextPolicyError(
                    "node context contains an invalid artifact"
                ) from error
        limits = dict(episode_limits or {})
        visible = set(available_evidence_ids)
        local = set(local_tool_result_ids)
        tool_sources = known_tool_call_sources(state_list)

        classes = [self._classify(state, phases=phases) for state in state_list]
        candidates = self._episode_candidates(state_list, classes, sample_id=sample_id)
        drafts = self._episode_drafts(state_list, classes)
        # E8b: at most ONE cleaning contact per consumer contact per boundary.
        # The LAST state of a cleaned boundary in this contact's exposed
        # history is the one that spends the contact -- for the Planner at
        # revision 2 that is the review it is actually deciding about -- and
        # every earlier one takes its L1 rendering. That bound is what makes
        # the contact-ceiling arithmetic of design section 7 exact.
        cleaning_targets: dict[str, int] = {}
        for position, (state, semantic_class) in enumerate(
            zip(state_list, classes, strict=True)
        ):
            if semantic_class is None or state.state_id in tool_sources:
                continue
            if semantic_class == "tool-observation" and state.state_id in local:
                continue
            entry = self.boundary_policy(role_kind, semantic_class)
            if entry is not None and entry.level == "cleaned":
                cleaning_targets[semantic_class] = position

        rendered_states: list[AgentStateArtifact] = []
        rows: list[Mapping[str, object]] = []
        for position, (state, semantic_class) in enumerate(
            zip(state_list, classes, strict=True)
        ):
            policy = None
            raw_reason: str | None = None
            if semantic_class is None:
                raw_reason = "not-a-role-state"
            elif state.state_id in tool_sources:
                raw_reason = "native-tool-call-source"
            elif semantic_class == "tool-observation" and state.state_id in local:
                raw_reason = "live-tool-chain"
            else:
                policy = self.boundary_policy(role_kind, semantic_class)
                if policy is None:
                    raw_reason = "boundary-not-declared"
            if policy is None or policy.level == "raw":
                if (
                    self.slot_audit is not None
                    and self.slot_audit_attachment == SLOT_AUDIT_ATTACHMENT_RAW
                    and (role_kind, semantic_class) == SLOT_AUDIT_BOUNDARY
                    and raw_reason in {None, "boundary-not-declared"}
                ):
                    # E19: the audited raw boundary, and the ONLY place this
                    # transform moves a byte under an all-raw policy. The
                    # sealed draft goes out exactly as it is and the block
                    # follows it. The two excluded raw reasons are the two the
                    # framework owns: a native tool-call source and a live tool
                    # chain both require the sealed bytes THEMSELVES.
                    audited_state, audited_row = self._audit_sealed_draft(
                        state, drafts=drafts, role_kind=role_kind,
                        semantic_class=semantic_class, sample_id=sample_id,
                        position=position, raw_reason=raw_reason,
                    )
                    rendered_states.append(audited_state)
                    rows.append(audited_row)
                    continue
                rendered_states.append(state)
                rows.append(self._raw_row(
                    state, position=position, role_kind=role_kind,
                    semantic_class=semantic_class, raw_reason=raw_reason,
                ))
                continue
            block, parse_status, fallback = self._render_boundary(
                policy,
                state=state,
                candidates=candidates,
                drafts=drafts,
                limits=limits,
                actions=actions,
                visible_evidence_ids=visible,
                task_instruction=task_instruction,
            )
            if block is None:
                # FALLBACK-RAW on a boundary whose template carries no
                # UNPARSED block: the consumer receives the sealed state
                # itself, and the row still names the boundary that decided so.
                rendered_states.append(state)
                rows.append(self._row(
                    state, position=position, role_kind=role_kind, policy=policy,
                    parse_status=parse_status, fallback=fallback, rendered=state,
                    derived_fields={},
                    slot_audit=self._slot_audit_row(
                        role_kind, policy, None, reason="boundary-rendered-raw",
                    ),
                    solver_hints=self._solver_hints_row(
                        role_kind, policy, None, reason="boundary-rendered-raw",
                    ),
                ))
                continue
            cleaning_contact = None
            if policy.level == "cleaned":
                block, cleaning_contact = self._clean_boundary(
                    policy,
                    l1_block=block,
                    state=state,
                    role_kind=role_kind,
                    is_target=cleaning_targets.get(policy.semantic_class) == position,
                    invoker=cleaning_invoker,
                )
            derived_fields = dict(block.derived_fields)
            audit_row = self._slot_audit_row(
                role_kind, policy, derived_fields.pop("slot_audit", None),
                reason="draft-unparsed",
            )
            hints_row = self._solver_hints_row(
                role_kind, policy, derived_fields.pop("solver_hints", None),
                reason="candidates-unparsed",
            )
            derived = self._derived_state(
                source=state, role_kind=role_kind,
                semantic_class=policy.semantic_class, sample_id=sample_id,
                rendered=block.text,
                preserve_identity=policy.semantic_class == "tool-observation",
            )
            rendered_states.append(derived)
            rows.append(self._row(
                state, position=position, role_kind=role_kind, policy=policy,
                parse_status=parse_status, fallback=fallback, rendered=derived,
                derived_fields=derived_fields,
                cleaning_contact=cleaning_contact,
                slot_audit=audit_row,
                solver_hints=hints_row,
            ))
        receipt = {
            "schema": NODE_CONTEXT_COMPILATION_SCHEMA,
            "policy_id": self.policy_id,
            "role_kind": role_kind,
            "sample_id": sample_id,
            "phase_ids": dict(phases),
            "declared_boundaries": self.declared_boundaries(),
            "boundaries": list(rows),
            "output_state_ids": [state.state_id for state in rendered_states],
        }
        receipt["receipt_sha256"] = _sha256_text(_canonical_json(receipt))
        return NodeContextCompilation(states=tuple(rendered_states), receipt=receipt)

    # -- classification and cross-state facts -------------------------------

    def _classify(
        self, state: AgentStateArtifact, *, phases: Mapping[str, str],
    ) -> str | None:
        if state.state_kind == "tool-result":
            return "tool-observation"
        for role_kind, semantic_class in (
            ("perception", "candidate-hypothesis"),
            ("solver", "current-draft"),
            ("reviewer", "review-finding"),
            ("planner", "plan-action"),
            # E18: present only when the caller's ``phase_ids`` names an
            # acquisition phase, which no pre-E18 caller does and no unarmed
            # episode has -- so on every other episode this loop iterates
            # exactly the four pairs it always did.
            (ACQUISITION_ROLE_KIND, "acquired-evidence"),
        ):
            if role_kind not in phases:
                continue
            if state.state_kind == f"phase:{phases[role_kind]}":
                return semantic_class
        return None

    def _episode_candidates(
        self,
        states: Sequence[AgentStateArtifact],
        classes: Sequence[str | None],
        *,
        sample_id: str,
    ) -> Mapping[str, object] | None:
        """The latest Perception output's projected candidates, parsed once per
        contact. ``None`` when there is none or it does not project."""

        if not self.legal_intent_ids:
            return None
        for state, semantic_class in reversed(list(zip(states, classes, strict=True))):
            if semantic_class != "candidate-hypothesis":
                continue
            try:
                projection = project_bounded_slurp_intent_hypotheses(
                    state.content,
                    sample_id=sample_id,
                    legal_intent_ids=self.legal_intent_ids,
                    max_candidates=self.max_candidates,
                    projection_policy=self.projection_policy,
                )
            except SlurpIntentHypothesisError:
                return None
            return json.loads(projection.content)
        return None

    def _episode_drafts(
        self, states: Sequence[AgentStateArtifact], classes: Sequence[str | None],
    ) -> dict[str, ParsedDraft | None]:
        drafts: dict[str, ParsedDraft | None] = {}
        if self._validator is None:
            return drafts
        for state, semantic_class in zip(states, classes, strict=True):
            if semantic_class != "current-draft":
                continue
            try:
                drafts[state.state_id] = parse_draft(
                    state.content, validator=self._validator
                )
            except NodeContextPolicyError:
                drafts[state.state_id] = None
        return drafts

    # -- rendering ----------------------------------------------------------

    def _render_boundary(
        self,
        policy: NodeContextBoundaryPolicy,
        *,
        state: AgentStateArtifact,
        candidates: Mapping[str, object] | None,
        drafts: Mapping[str, ParsedDraft | None],
        limits: Mapping[str, object],
        actions: Sequence[str],
        visible_evidence_ids: set[str],
        task_instruction: str,
    ) -> tuple[RenderedBlock | None, str, str | None]:
        semantic_class = policy.semantic_class
        try:
            if semantic_class == "candidate-hypothesis":
                block = self._render_candidates(policy, candidates=candidates)
            elif semantic_class == "current-draft":
                block = self._render_draft(
                    policy, state=state, drafts=drafts, candidates=candidates,
                    limits=limits,
                )
            elif semantic_class == "review-finding":
                block = self._render_review(
                    policy, state=state, visible_evidence_ids=visible_evidence_ids,
                )
            elif semantic_class == "plan-action":
                block = self._render_plan(
                    policy, state=state, limits=limits, actions=actions,
                )
            else:
                block = self._render_tool_observation(
                    policy, state=state, task_instruction=task_instruction,
                )
        except NodeContextPolicyError as error:
            return self._apply_parse_failure(
                policy, state=state, reason=str(error), limits=limits,
            )
        return block, "parsed", None

    def _apply_parse_failure(
        self,
        policy: NodeContextBoundaryPolicy,
        *,
        state: AgentStateArtifact,
        reason: str,
        limits: Mapping[str, object],
    ) -> tuple[RenderedBlock | None, str, str]:
        rule = policy.on_parse_failure
        if rule == FALLBACK_REFUSE:
            raise NodeContextPolicyError(
                f"{policy.boundary_id}: {reason}; the boundary declares "
                "FALLBACK-REFUSE, so the row fails rather than rendering"
            )
        template = policy.template
        if template is None:  # pragma: no cover -- structured always has one
            raise NodeContextPolicyError("a structured boundary requires a template")
        if "unparsed" not in template.sections:
            # A template with no UNPARSED block -- the tool-observation
            # boundary, whose source is a custody envelope and not prose --
            # falls back to the source state itself, verbatim. ``None`` is the
            # caller's instruction to keep it.
            if rule == FALLBACK_OMIT:
                raise NodeContextPolicyError(
                    f"{policy.boundary_id} declares FALLBACK-OMIT but its template "
                    "has no omitted block"
                )
            return None, "malformed", FALLBACK_RAW
        block = _Block(template)
        if rule == FALLBACK_OMIT:
            block.add("omitted", {
                "reason": Substitution("reason", reason, PROVENANCE_VOCABULARY),
            })
            return block.finish({"omitted_reason": reason}), "malformed", FALLBACK_OMIT
        values = self._limit_substitutions(template.renderer, limits)
        values["source_content"] = Substitution(
            "source_content", state.content, PROVENANCE_SOURCE,
        )
        block.add("header_unparsed", values)
        block.add("unparsed", values)
        return block.finish({"unparsed_reason": reason}), "malformed", FALLBACK_RAW

    def _limit_substitutions(
        self, renderer: str, limits: Mapping[str, object],
    ) -> dict[str, Substitution]:
        values = {
            "revision_index": Substitution(
                "revision_index", str(limits.get("revision_index", 0)), PROVENANCE_LIMIT
            ),
            "max_revisions": Substitution(
                "max_revisions", str(limits.get("max_revisions", 0)), PROVENANCE_LIMIT
            ),
        }
        if renderer in {"planner-brief", "plan-action"}:
            values["available_actions"] = Substitution(
                "available_actions",
                ", ".join(
                    str(action)
                    for action in limits.get("available_planner_actions", [])
                ),
                PROVENANCE_LIMIT,
            )
        return values

    def _render_candidates(
        self,
        policy: NodeContextBoundaryPolicy,
        *,
        candidates: Mapping[str, object] | None,
    ) -> RenderedBlock:
        if candidates is None:
            raise NodeContextPolicyError("Perception output does not project")
        template = policy.template
        block = _Block(template)
        rows = list(candidates["candidates"])
        block.add("header", {
            "count": Substitution("count", str(len(rows)), PROVENANCE_COUNT),
            "max_candidates": Substitution(
                "max_candidates", str(self.max_candidates), PROVENANCE_LIMIT
            ),
        })
        if not rows:
            block.add("items_empty")
        for position, row in enumerate(rows, start=1):
            block.add("item", {
                "position": Substitution("position", str(position), PROVENANCE_COUNT),
                "intent_id": Substitution(
                    "intent_id", _text(row["intent_id"], field_name="intent_id"),
                    PROVENANCE_INVENTORY,
                ),
                "distinction": Substitution(
                    "distinction",
                    _text(row["distinction"], field_name="distinction"),
                    PROVENANCE_SOURCE,
                ),
            })
        block.add("footer")
        rendered = block.finish({
            "candidate_count": len(rows),
            "intent_ids": [row["intent_id"] for row in rows],
        })
        if (
            self.solver_hints is None
            or (policy.consumer_role_kind, policy.semantic_class)
            != SOLVER_HINTS_BOUNDARY
        ):
            return rendered
        return self._append_solver_hints(
            rendered, candidate_ids=[row["intent_id"] for row in rows],
        )

    def _render_draft(
        self,
        policy: NodeContextBoundaryPolicy,
        *,
        state: AgentStateArtifact,
        drafts: Mapping[str, ParsedDraft | None],
        candidates: Mapping[str, object] | None,
        limits: Mapping[str, object],
    ) -> RenderedBlock:
        template = policy.template
        draft = drafts.get(state.state_id)
        if draft is None:
            raise NodeContextPolicyError(
                "draft does not parse as the task answer schema"
            )
        candidate_ids = (
            None if candidates is None
            else [row["intent_id"] for row in candidates["candidates"]]
        )
        membership = (
            CANDIDATES_UNAVAILABLE if candidate_ids is None
            else AMONG_CANDIDATES if draft.intent_id in candidate_ids
            else NOT_AMONG_CANDIDATES
        )
        values = self._limit_substitutions(template.renderer, limits)
        values.update({
            "scenario": Substitution("scenario", draft.scenario, PROVENANCE_SOURCE),
            "action": Substitution("action", draft.action, PROVENANCE_SOURCE),
            "intent_id": Substitution("intent_id", draft.intent_id, PROVENANCE_COMPOSED),
            "candidate_membership": Substitution(
                "candidate_membership", membership, PROVENANCE_VOCABULARY
            ),
        })
        block = _Block(template)
        block.add("header", values)
        block.add("body", values)
        if not draft.entities:
            block.add("items_empty")
        for entity_type, entity_filler in draft.entities:
            block.add("item", {
                "entity_type": Substitution(
                    "entity_type", entity_type, PROVENANCE_SOURCE
                ),
                "entity_filler": Substitution(
                    "entity_filler", entity_filler, PROVENANCE_SOURCE
                ),
            })
        derived: dict[str, object] = {
            "scenario": draft.scenario,
            "action": draft.action,
            "intent_id": draft.intent_id,
            "entity_count": len(draft.entities),
            "intent_among_candidates": (
                None if candidate_ids is None else draft.intent_id in candidate_ids
            ),
        }
        if template.renderer == "planner-brief":
            checks, check_values = self.harness_checks(
                draft=draft, candidate_ids=candidate_ids,
            )
            block.add("checks", check_values)
            derived["harness_checks"] = checks
        block.add("footer")
        rendered = block.finish(derived)
        if (
            self.slot_audit is None
            or (policy.consumer_role_kind, policy.semantic_class) != SLOT_AUDIT_BOUNDARY
        ):
            return rendered
        return self._append_slot_audit(rendered, draft=draft)

    # -- E12: the Reviewer slot-audit block ---------------------------------

    def _append_slot_audit(
        self, rendered: RenderedBlock, *, draft: ParsedDraft,
    ) -> RenderedBlock:
        """Append the slot-audit block to one Reviewer draft rendering.

        An ADDITION, never a rewrite: ``rendered.text`` is the same L1 block
        the base renders, byte for byte, and the audit follows it after one
        newline. Zero contacts; every substituted value is a construction
        count, a construction share, a released convention sentence, a closed
        flag name or an entity type the draft or the table already carries.
        """

        audit_block, flags = self._slot_audit_block(draft)
        derived = dict(rendered.derived_fields)
        derived["slot_audit"] = self.slot_audit.receipt(
            applied=True,
            intent_id=draft.intent_id,
            flags=flags,
            block_text=audit_block.text,
        )
        return RenderedBlock(
            text=f"{rendered.text}\n{audit_block.text}",
            substitutions=rendered.substitutions + audit_block.substitutions,
            derived_fields=derived,
        )

    def _slot_audit_block(
        self, draft: ParsedDraft,
    ) -> tuple[RenderedBlock, tuple[SlotAuditFlag, ...]]:
        """Render the audit block for one draft, and the flags it carries.

        The block ALONE: what it is appended to -- an L1 rendering (E12) or
        the sealed draft bytes (E19) -- is the caller's business, so the two
        attachments render one block through one template rather than two.
        """

        audit = self.slot_audit
        flags = slot_audit_flags(
            intent_id=draft.intent_id,
            entities=draft.entities,
            table=audit.table,
            thresholds=audit.thresholds,
        )
        profile = audit.table.profile(draft.intent_id)
        block = _Block(audit.template)
        block.add("header", {
            "view_id": Substitution(
                "view_id", audit.table.view_id, PROVENANCE_AUDIT
            ),
            "intent_id": Substitution(
                "intent_id", draft.intent_id, PROVENANCE_COMPOSED
            ),
        })
        listed = profile_rows(profile, audit.thresholds)
        if profile is None or profile.rows <= 0:
            block.add("profile_empty")
        else:
            block.add("profile_header", {
                "intent_rows": Substitution(
                    "intent_rows", str(profile.rows), PROVENANCE_AUDIT
                ),
                "empty_share": Substitution(
                    "empty_share",
                    render_share(profile.rows_without_entity, profile.rows),
                    PROVENANCE_AUDIT,
                ),
            })
            for entity_type, rows, of_rows in listed:
                block.add("profile_item", {
                    "entity_type": Substitution(
                        "entity_type", entity_type, PROVENANCE_AUDIT
                    ),
                    "type_share": Substitution(
                        "type_share", render_share(rows, of_rows), PROVENANCE_AUDIT
                    ),
                })
        if not flags:
            block.add("flags_empty")
        for flag in flags:
            block.add("flag", {
                "flag": Substitution("flag", flag.flag, PROVENANCE_VOCABULARY),
                "detail": Substitution("detail", flag.detail, PROVENANCE_AUDIT),
            })
        block.add("footer")
        return block.finish({}), tuple(flags)

    def _audit_sealed_draft(
        self,
        state: AgentStateArtifact,
        *,
        drafts: Mapping[str, ParsedDraft | None],
        role_kind: str,
        semantic_class: str,
        sample_id: str,
        position: int,
        raw_reason: str | None,
    ) -> tuple[AgentStateArtifact, Mapping[str, object]]:
        """E19: one raw Reviewer draft boundary with the audit appended.

        An ADDITION, never a rewrite: ``state.content`` is the sealed Solver
        response byte for byte and the audit follows it after one newline. A
        draft that does not parse under the closed contract takes the
        untouched state and an ``applied: false`` receipt, so a skip and a
        silent absence never look alike.
        """

        draft = drafts.get(state.state_id)
        if draft is None:
            return state, self._raw_row(
                state, position=position, role_kind=role_kind,
                semantic_class=semantic_class, raw_reason=raw_reason,
                slot_audit=self.slot_audit.receipt(
                    applied=False, reason="draft-unparsed",
                ),
            )
        audit_block, flags = self._slot_audit_block(draft)
        derived_state = self._derived_state(
            source=state, role_kind=role_kind, semantic_class=semantic_class,
            sample_id=sample_id,
            rendered=f"{state.content}\n{audit_block.text}",
            preserve_identity=False,
        )
        return derived_state, self._raw_row(
            state, position=position, role_kind=role_kind,
            semantic_class=semantic_class, raw_reason=raw_reason,
            rendered=derived_state,
            slot_audit=self.slot_audit.receipt(
                applied=True,
                intent_id=draft.intent_id,
                flags=flags,
                block_text=audit_block.text,
            ),
        )

    # -- E14: the Solver scenario-hints block -------------------------------

    def _append_solver_hints(
        self, rendered: RenderedBlock, *, candidate_ids: Sequence[str],
    ) -> RenderedBlock:
        """Append the scenario-hints block to one Solver candidate rendering.

        An ADDITION, never a rewrite: ``rendered.text`` is the same L1 block
        the base renders, byte for byte, and the hints follow it after one
        newline. Zero contacts; every substituted value is a construction row
        count, a construction leakage rate, a construction cue word, a legal
        intent id the consumer already holds in the list above, or one of the
        module's two closed phrases.
        """

        hints = self.solver_hints
        selected = scenario_hints(
            candidate_ids=candidate_ids, table=hints.table, bounds=hints.bounds,
        )
        block = _Block(hints.template)
        block.add("header", {
            "view_id": Substitution(
                "view_id", hints.table.view_id, PROVENANCE_HINTS
            ),
        })
        if not selected:
            block.add("candidate_empty")
        for hint in selected:
            block.add("candidate", {
                "intent_id": Substitution(
                    "intent_id", hint.intent, PROVENANCE_INVENTORY
                ),
                "intent_rows": Substitution(
                    "intent_rows", str(hint.rows), PROVENANCE_HINTS
                ),
            })
            if not hint.lines:
                block.add("neighbour_empty", {
                    "reason": Substitution(
                        "reason", NO_NEIGHBOUR, PROVENANCE_VOCABULARY
                    ),
                })
            for line in hint.lines:
                block.add("neighbour", {
                    "intent_id": Substitution(
                        "intent_id", line.intent, PROVENANCE_INVENTORY
                    ),
                    "neighbour_id": Substitution(
                        "neighbour_id", line.neighbour, PROVENANCE_INVENTORY
                    ),
                    "leakage": Substitution(
                        "leakage",
                        render_leakage(line.leaked, line.of_neighbours),
                        PROVENANCE_HINTS,
                    ),
                    "cues": Substitution(
                        "cues",
                        render_cues(line.cues),
                        PROVENANCE_HINTS if line.cues else PROVENANCE_VOCABULARY,
                    ),
                })
        block.add("footer")
        hints_block = block.finish({})
        derived = dict(rendered.derived_fields)
        derived["solver_hints"] = hints.receipt(
            applied=True,
            candidate_ids=candidate_ids,
            hints=selected,
            block_text=hints_block.text,
        )
        return RenderedBlock(
            text=f"{rendered.text}\n{hints_block.text}",
            substitutions=rendered.substitutions + hints_block.substitutions,
            derived_fields=derived,
        )

    def harness_checks(
        self, *, draft: ParsedDraft | None, candidate_ids: Sequence[str] | None,
    ) -> tuple[Mapping[str, object], dict[str, Substitution]]:
        """The deterministic HARNESS CHECKS block (design section 4; open
        question 2, answered by coordinator decision 2 of 2026-09-17).

        Computed ONLY from material the Planner already receives -- the draft
        it is deciding about, the Perception candidates it already holds, and
        the legal entity inventory its system contract already carries. No
        gold, no retrieval, no judgment; the harness states three facts and
        takes no position on what they mean.
        """

        parses = draft is not None
        member = (
            None if draft is None or candidate_ids is None
            else draft.intent_id in candidate_ids
        )
        illegal: list[str] = []
        if draft is None or not self.legal_entity_types:
            types_legal: bool | None = None
        else:
            illegal = [
                entity_type
                for entity_type, _filler in draft.entities
                if entity_type not in self.legal_entity_types
            ]
            types_legal = not illegal
        if types_legal is None:
            types_text = CHECK_NO_INVENTORY if not self.legal_entity_types else CHECK_NA
        elif types_legal:
            types_text = CHECK_YES
        else:
            types_text = f"{CHECK_NO} ({', '.join(illegal)})"
        values = {
            "check_parses": Substitution(
                "check_parses", CHECK_YES if parses else CHECK_NO, PROVENANCE_VOCABULARY
            ),
            "check_candidate_member": Substitution(
                "check_candidate_member",
                CHECK_NA if member is None else CHECK_YES if member else CHECK_NO,
                PROVENANCE_VOCABULARY,
            ),
            "check_entity_types": Substitution(
                "check_entity_types", types_text, PROVENANCE_VOCABULARY
            ),
        }
        checks = {
            "draft_parses": parses,
            "intent_among_candidates": member,
            "entity_types_legal": types_legal,
            "illegal_entity_types": illegal,
        }
        return checks, values

    def _render_review(
        self,
        policy: NodeContextBoundaryPolicy,
        *,
        state: AgentStateArtifact,
        visible_evidence_ids: set[str],
    ) -> RenderedBlock:
        template = policy.template
        try:
            report = parse_review_findings(state.content)
        except ReviewFindingsError as error:
            raise NodeContextPolicyError(
                "review report does not match its registered JSON contract"
            ) from error
        block = _Block(template)
        block.add("header")
        block.add("body", {
            "verdict": Substitution("verdict", report["verdict"], PROVENANCE_SOURCE),
            "recommendation": Substitution(
                "recommendation", report["recommendation"], PROVENANCE_SOURCE
            ),
            "remaining_uncertainty": Substitution(
                "remaining_uncertainty", report["remaining_uncertainty"],
                PROVENANCE_SOURCE,
            ),
        })
        findings = list(report["findings"])
        if not findings:
            block.add("items_empty")
        for finding in findings:
            block.add("item", {
                "dimension": Substitution(
                    "dimension", finding["dimension"], PROVENANCE_SOURCE
                ),
                "rationale": Substitution(
                    "rationale", finding["rationale"], PROVENANCE_SOURCE
                ),
            })
        evidence_ids = list(dict.fromkeys(
            evidence_id
            for finding in findings
            for evidence_id in finding["evidence_ids"]
        ))
        if not evidence_ids:
            block.add("citations_empty")
        availability = []
        for evidence_id in evidence_ids:
            present = evidence_id in visible_evidence_ids
            block.add("citation", {
                "evidence_id": Substitution(
                    "evidence_id", evidence_id, PROVENANCE_SOURCE
                ),
                "availability": Substitution(
                    "availability",
                    EVIDENCE_AVAILABLE if present else EVIDENCE_UNAVAILABLE,
                    PROVENANCE_VOCABULARY,
                ),
            })
            availability.append({"evidence_id": evidence_id, "available": present})
        block.add("footer")
        return block.finish({
            "verdict": report["verdict"],
            "issue_count": len(findings),
            "citation_availability": availability,
        })

    # -- E8b: the cleaning contact -----------------------------------------

    def _clean_boundary(
        self,
        policy: NodeContextBoundaryPolicy,
        *,
        l1_block: RenderedBlock,
        state: AgentStateArtifact,
        role_kind: str,
        is_target: bool,
        invoker: object,
    ) -> tuple[RenderedBlock, Mapping[str, object]]:
        """L1 first, then at most one cleaning contact, then the accepted
        rendering or the L1 fallback. Returns ``(block, cleaning_receipt)``."""

        cleaning = policy.cleaning
        if cleaning is None:  # pragma: no cover -- resolution refuses this
            raise NodeContextPolicyError(
                f"{policy.boundary_id} declares level 'cleaned' without a cleaning block"
            )
        if not is_target:
            return l1_block, self._cleaning_row(
                cleaning, validation=CLEANING_SKIPPED,
                reason=CLEANING_SUPERSEDED_REASON,
            )
        if not callable(invoker):
            raise NodeContextPolicyError(
                f"{policy.boundary_id} declares a cleaning contact, but this "
                "compilation was handed no metered cleaning invoker"
            )
        instruction = cleaning.instruction(l1_block.text)
        outcome = invoker(CleaningContactRequest(
            boundary_id=policy.boundary_id,
            consumer_role_kind=role_kind,
            semantic_class=policy.semantic_class,
            phase_id=cleaning.phase_id,
            response_format_id=cleaning.response_format_id,
            knowledge=cleaning.knowledge,
            instruction=instruction,
            instruction_sha256=_sha256_text(instruction),
            source_state_id=state.state_id,
        ))
        if not isinstance(outcome, CleaningContactOutcome):
            raise NodeContextPolicyError(
                "a cleaning invoker must return one CleaningContactOutcome"
            )
        try:
            cleaned = validate_cleaning_document(
                outcome.text, source_material=l1_block.text,
            )
        except NodeContextCleaningRejected as error:
            # One attempt, one fallback: the boundary renders exactly what L1
            # already produced and the receipt says why (design section 3, L2).
            return l1_block, self._cleaning_row(
                cleaning, validation=CLEANING_REJECTED, reason=str(error),
                outcome=outcome, instruction_sha256=_sha256_text(instruction),
            )
        return self._render_cleaned(policy, cleaned=cleaned), self._cleaning_row(
            cleaning, validation=CLEANING_ACCEPTED, reason=None, outcome=outcome,
            instruction_sha256=_sha256_text(instruction),
        )

    def _render_cleaned(
        self, policy: NodeContextBoundaryPolicy, *, cleaned: CleanedReview,
    ) -> RenderedBlock:
        template = policy.cleaning.render_template
        block = _Block(template)
        block.add("header")
        block.add("body", {
            "verdict": Substitution(
                "verdict", cleaned.verdict, PROVENANCE_CLEANED,
            ),
        })
        if not cleaned.issues:
            block.add("items_empty")
        for field_name, problem in cleaned.issues:
            block.add("item", {
                "field": Substitution("field", field_name, PROVENANCE_CLEANED),
                "problem": Substitution("problem", problem, PROVENANCE_CLEANED),
            })
        block.add("footer")
        return block.finish({
            "verdict": cleaned.verdict,
            "issue_count": len(cleaned.issues),
            "issue_fields": [field_name for field_name, _problem in cleaned.issues],
        })

    @staticmethod
    def _cleaning_row(
        cleaning: NodeContextCleaningPolicy,
        *,
        validation: str,
        reason: str | None,
        outcome: CleaningContactOutcome | None = None,
        instruction_sha256: str | None = None,
    ) -> Mapping[str, object]:
        """The ``cleaning_contact`` block of one receipt row (design section
        9), extended with the contact's phase, its declared knowledge and the
        two committed templates it is pinned to."""

        return {
            **cleaning.as_json(),
            "instruction_sha256": instruction_sha256,
            "agent_contact_id": None if outcome is None else outcome.agent_contact_id,
            "request_id": None if outcome is None else outcome.request_id,
            "request_sha256": None if outcome is None else outcome.request_sha256,
            "response_sha256": None if outcome is None else outcome.response_sha256,
            "response_text_sha256": (
                None if outcome is None else outcome.response_text_sha256
            ),
            "validation": validation,
            "rejected_reason": reason,
        }

    def _render_plan(
        self,
        policy: NodeContextBoundaryPolicy,
        *,
        state: AgentStateArtifact,
        limits: Mapping[str, object],
        actions: Sequence[str],
    ) -> RenderedBlock:
        template = policy.template
        action = parse_plan_action(state.content, actions=actions)
        try:
            remaining = max(
                int(limits.get("max_revisions", 0))
                - int(limits.get("revision_index", 0)),
                0,
            )
        except (TypeError, ValueError):
            remaining = 0
        values = self._limit_substitutions(template.renderer, limits)
        values.update({
            "action": Substitution("action", action, PROVENANCE_SOURCE),
            "revisions_remaining": Substitution(
                "revisions_remaining", str(remaining), PROVENANCE_LIMIT
            ),
        })
        block = _Block(template)
        block.add("header", values)
        block.add("footer", values)
        return block.finish({"action": action, "revisions_remaining": remaining})

    def _render_tool_observation(
        self,
        policy: NodeContextBoundaryPolicy,
        *,
        state: AgentStateArtifact,
        task_instruction: str,
    ) -> RenderedBlock:
        """Replace the duplicated task contract with a reference to the system
        message that already carries it, verbatim and in full.

        The audit measured 13,634,712 characters of this one duplication --
        about 7.4 % of the anchor's entire prompt budget, carrying nothing the
        receiving context did not already hold. The replacement runs only when
        the contract is provably a substring of this request's own system
        message, so it removes a repetition and never a fact.
        """

        from .hashing import content_hash  # noqa: PLC0415 (light package top level)

        template = policy.template
        document, contract = parse_tool_observation(
            state.content, task_instruction=task_instruction
        )
        block = _Block(template)
        block.add("reference", {
            "tool_id": Substitution("tool_id", document["tool_id"], PROVENANCE_SOURCE),
        })
        rendered = block.finish({})
        result = {TASK_CONTRACT_RESULT_FIELD: rendered.text}
        rewritten = dict(document)
        rewritten["result"] = result
        rewritten["result_sha256"] = content_hash(result)
        return RenderedBlock(
            text=json.dumps(rewritten, sort_keys=True),
            substitutions=rendered.substitutions,
            derived_fields={
                "replaced_result_field": TASK_CONTRACT_RESULT_FIELD,
                "source_contract_chars": len(contract),
                "reference_chars": len(rendered.text),
            },
        )

    # -- derived states and receipt rows ------------------------------------

    def _derived_state(
        self,
        *,
        source: AgentStateArtifact,
        role_kind: str,
        semantic_class: str,
        sample_id: str,
        rendered: str,
        preserve_identity: bool,
    ) -> AgentStateArtifact:
        """The state the consumer actually receives.

        It keeps the producer's ``source_response_sha256`` and
        ``source_query_state_sha256`` exactly as ``rails.role_context.
        _derived_state`` does, so a rendering can never obscure which model
        bytes it was derived from.

        ``preserve_identity`` is the tool-observation case: the framework binds
        a tool result to its call by STATE ID and requires the result's custody
        fields to equal its source phase state's
        (``core.model.native_history._bound_result``), so that boundary keeps
        the sealed identity and rewrites only the content.
        """

        if preserve_identity:
            return AgentStateArtifact(
                state_id=source.state_id,
                state_kind=source.state_kind,
                content=rendered,
                source_query_state_sha256=source.source_query_state_sha256,
                source_response_sha256=source.source_response_sha256,
                producer_policy_id=source.producer_policy_id,
                cited_value_ids=source.cited_value_ids,
            ).validate()
        content_sha256 = _sha256_text(rendered)
        # The SOURCE state id is part of the derived id, not just the sample:
        # this transform keeps every state, so two sources that happen to
        # render identically (two Reviewer visits emitting the same prose under
        # FALLBACK-RAW, say) must still be two distinct states on the wire.
        return AgentStateArtifact(
            state_id=(
                f"node-context:{role_kind}:{semantic_class}:{sample_id}:"
                f"{source.state_id}:{content_sha256}"
            ),
            state_kind=f"node-context:{semantic_class}",
            content=rendered,
            source_query_state_sha256=source.source_query_state_sha256,
            source_response_sha256=source.source_response_sha256,
            producer_policy_id=self.policy_id,
            cited_value_ids=source.cited_value_ids,
        ).validate()

    def _slot_audit_row(
        self,
        role_kind: str,
        policy: NodeContextBoundaryPolicy,
        rendered_row: Mapping[str, object] | None,
        *,
        reason: str,
    ) -> Mapping[str, object] | None:
        """The audit receipt block for one boundary row.

        ``None`` on every boundary but the armed one, and on every flight that
        arms no audit -- so a pre-E12 receipt keeps exactly its pre-E12 fields.
        On the armed boundary it is always present: rendered, or explicitly
        ``applied: false`` with the reason, because a silent absence and a
        deliberate skip must not look alike in the receipt.
        """

        if self.slot_audit is None:
            return None
        if (role_kind, policy.semantic_class) != SLOT_AUDIT_BOUNDARY:
            return None
        if rendered_row is not None:
            return rendered_row
        return self.slot_audit.receipt(applied=False, reason=reason)

    def _solver_hints_row(
        self,
        role_kind: str,
        policy: NodeContextBoundaryPolicy,
        rendered_row: Mapping[str, object] | None,
        *,
        reason: str,
    ) -> Mapping[str, object] | None:
        """E14: the hints receipt block for one boundary row.

        ``None`` on every boundary but the armed one, and on every flight
        that arms no hints -- so a pre-E14 receipt keeps exactly its pre-E14
        fields. On the armed boundary it is always present: rendered, or
        explicitly ``applied: false`` with the reason, because a silent
        absence and a deliberate skip must not look alike in the receipt.
        """

        if self.solver_hints is None:
            return None
        if (role_kind, policy.semantic_class) != SOLVER_HINTS_BOUNDARY:
            return None
        if rendered_row is not None:
            return rendered_row
        return self.solver_hints.receipt(applied=False, reason=reason)

    def _source_binding(
        self, source: AgentStateArtifact, position: int,
    ) -> dict[str, object]:
        return {
            "state_id": source.state_id,
            "state_kind": source.state_kind,
            "artifact_sha256": source.content_hash(),
            "content_sha256": _sha256_text(source.content),
            "source_response_sha256": source.source_response_sha256,
            "source_query_state_sha256": source.source_query_state_sha256,
            "producer_policy_id": source.producer_policy_id,
            "source_position": position,
        }

    def _finish_row(self, row: dict[str, object]) -> dict[str, object]:
        row["receipt_sha256"] = _sha256_text(_canonical_json(row))
        return row

    def _raw_row(
        self,
        state: AgentStateArtifact,
        *,
        position: int,
        role_kind: str,
        semantic_class: str | None,
        raw_reason: str | None,
        rendered: AgentStateArtifact | None = None,
        slot_audit: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        """A ``level: "raw"`` row. Its ``rendered_sha256`` equals the source's
        ``content_sha256`` -- that equality is what makes L0's claim of byte
        identity a checked statement rather than a comment.

        E19 opens exactly ONE exception: the audited draft boundary, where
        ``rendered`` is the sealed state followed by the appended audit
        block. That row always carries a ``slot_audit`` receipt naming the
        block, so the inequality can never be silent -- no ``slot_audit``,
        no inequality."""

        exposed = state if rendered is None else rendered
        row = self._finish_row({
            "schema": NODE_CONTEXT_RECEIPT_SCHEMA,
            "policy_id": self.policy_id,
            "boundary": {
                "consumer_role_kind": role_kind,
                "semantic_class": semantic_class,
                "boundary_id": (
                    "B-NONE" if semantic_class is None
                    # E18: the acquisition boundary is declared beside
                    # SLURP_BOUNDARY_IDS rather than in it, so name it
                    # explicitly instead of calling it undeclared.
                    else ACQUIRED_EVIDENCE_BOUNDARY_ID
                    if (role_kind, semantic_class) == ACQUIRED_EVIDENCE_BOUNDARY
                    else SLURP_BOUNDARY_IDS.get(
                        (role_kind, semantic_class), "B-UNDECLARED"
                    )
                ),
            },
            "level": "raw",
            "source": self._source_binding(state, position),
            "parse_status": "not-parsed",
            "parser_id": None,
            "fallback_applied": None,
            "raw_reason": raw_reason,
            "template_id": None,
            "template_sha256": None,
            "rendered_state_id": exposed.state_id,
            "rendered_sha256": _sha256_text(exposed.content),
            "rendered_chars": len(exposed.content),
            "derived_fields": {},
            "cleaning_contact": None,
        })
        if slot_audit is not None:
            # E12's discipline, on the raw row: added AFTER ``_finish_row``
            # computed the digest, then re-digested, so a pre-E19 raw row's
            # ``receipt_sha256`` is a function of exactly its pre-E19 fields.
            row["slot_audit"] = dict(slot_audit)
            row.pop("receipt_sha256")
            self._finish_row(row)
        return row

    def _row(
        self,
        state: AgentStateArtifact,
        *,
        position: int,
        role_kind: str,
        policy: NodeContextBoundaryPolicy,
        parse_status: str,
        fallback: str | None,
        rendered: AgentStateArtifact,
        derived_fields: Mapping[str, object],
        cleaning_contact: Mapping[str, object] | None = None,
        slot_audit: Mapping[str, object] | None = None,
        solver_hints: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        template = policy.template
        row = self._finish_row({
            "schema": NODE_CONTEXT_RECEIPT_SCHEMA,
            "policy_id": self.policy_id,
            "boundary": {
                "consumer_role_kind": role_kind,
                "semantic_class": policy.semantic_class,
                "boundary_id": policy.boundary_id,
            },
            "level": policy.level,
            "source": self._source_binding(state, position),
            "parse_status": parse_status,
            "parser_id": PARSER_IDS[policy.semantic_class],
            "fallback_applied": fallback,
            "raw_reason": None,
            "template_id": None if template is None else template.template_id,
            "template_sha256": None if template is None else template.sha256,
            "rendered_state_id": rendered.state_id,
            "rendered_sha256": _sha256_text(rendered.content),
            "rendered_chars": len(rendered.content),
            "derived_fields": dict(derived_fields),
            "cleaning_contact": (
                None if cleaning_contact is None else dict(cleaning_contact)
            ),
        })
        if slot_audit is not None:
            # E12. Added AFTER ``_finish_row`` computed the row digest, and
            # then re-digested, so a pre-E12 row's ``receipt_sha256`` is a
            # function of exactly its pre-E12 fields and only an ARMED audit
            # moves it.
            row["slot_audit"] = dict(slot_audit)
            row.pop("receipt_sha256")
            self._finish_row(row)
        if solver_hints is not None:
            # E14, the same discipline: added AFTER the row digest was
            # computed, then re-digested, so a pre-E14 row's
            # ``receipt_sha256`` is a function of exactly its pre-E14 fields
            # and only ARMED hints move it.
            row["solver_hints"] = dict(solver_hints)
            row.pop("receipt_sha256")
            self._finish_row(row)
        return row


def _resolve_cleaning(
    entry: object, *, key: tuple[str, str], spelling: str, repo_root: Path,
) -> NodeContextCleaningPolicy:
    """Resolve one boundary's declared ``cleaning`` block, or refuse it.

    Fail-closed on every axis: the block is required, its fields are exactly
    the design's four, the semantic class must have registered cleaning assets,
    and both committed templates must declare the renderer their position
    requires -- so a cleaning contact can never reach the model half-composed.
    """

    semantic_class = key[1]
    if semantic_class not in CLEANING_RENDER_TEMPLATES:
        raise NodeContextPolicyError(
            f"boundary {spelling!r} cannot be cleaned: this carrier registers a "
            f"cleaning renderer only for {sorted(CLEANING_RENDER_TEMPLATES)}"
        )
    if not isinstance(entry, Mapping) or set(entry) != CLEANING_KEYS:
        raise NodeContextPolicyError(
            f"boundary {spelling!r} at level 'cleaned' requires a cleaning block "
            f"declaring exactly {sorted(CLEANING_KEYS)}"
        )
    phase_id = entry["phase_id"]
    if not isinstance(phase_id, str) or not phase_id.strip():
        raise NodeContextPolicyError(
            f"boundary {spelling!r} cleaning phase_id must be text"
        )
    response_format_id = entry["response_format_id"]
    if not isinstance(response_format_id, str) or not response_format_id.strip():
        raise NodeContextPolicyError(
            f"boundary {spelling!r} cleaning response_format_id must be text"
        )
    on_invalid = entry["on_invalid"]
    if on_invalid not in CLEANING_INVALID_RULES:
        raise NodeContextPolicyError(
            f"boundary {spelling!r} cleaning on_invalid must be one of "
            f"{list(CLEANING_INVALID_RULES)}"
        )
    instruction = load_node_context_template(
        repo_root, entry["instruction_template"],
    )
    if instruction.renderer != "cleaning-review":
        raise NodeContextPolicyError(
            f"boundary {spelling!r} requires a 'cleaning-review' instruction "
            f"template; it declares {instruction.renderer!r}"
        )
    render = load_node_context_template(
        repo_root, CLEANING_RENDER_TEMPLATES[semantic_class],
    )
    if render.renderer != f"cleaned-{semantic_class}":
        raise NodeContextPolicyError(  # pragma: no cover -- committed asset
            f"boundary {spelling!r} cleaning renderer is {render.renderer!r}"
        )
    return NodeContextCleaningPolicy(
        phase_id=phase_id,
        instruction_template=instruction,
        render_template=render,
        response_format_id=response_format_id,
        on_invalid=on_invalid,
    )


def resolve_slot_audit_binding(
    repo_root: Path,
    *,
    table: SlotAuditTable,
    thresholds: SlotAuditThresholds,
    template: str | None = None,
) -> SlotAuditBinding:
    """E12: load and check the committed template the audit block renders
    through, and bind it to the pinned table and the declared thresholds."""

    relpath = SLOT_AUDIT_TEMPLATE if template is None else template
    resolved = load_node_context_template(repo_root, relpath)
    if resolved.renderer != SLOT_AUDIT_RENDERER:
        raise NodeContextPolicyError(
            f"the reviewer slot-audit block requires a {SLOT_AUDIT_RENDERER!r} "
            f"template; {relpath!r} declares {resolved.renderer!r}"
        )
    return SlotAuditBinding(table=table, thresholds=thresholds, template=resolved)


def resolve_solver_hints_binding(
    repo_root: Path,
    *,
    table: ScenarioHintsTable,
    bounds: ScenarioHintsBounds,
    template: str | None = None,
) -> SolverHintsBinding:
    """E14: load and check the committed template the scenario-hints block
    renders through, and bind it to the pinned table and declared bounds."""

    relpath = SOLVER_HINTS_TEMPLATE if template is None else template
    resolved = load_node_context_template(repo_root, relpath)
    if resolved.renderer != SOLVER_HINTS_RENDERER:
        raise NodeContextPolicyError(
            f"the solver scenario-hints block requires a {SOLVER_HINTS_RENDERER!r} "
            f"template; {relpath!r} declares {resolved.renderer!r}"
        )
    return SolverHintsBinding(table=table, bounds=bounds, template=resolved)


def build_slurp_node_context_policy(
    *,
    repo_root: Path,
    policy_id: str,
    level: str,
    boundaries: Mapping[str, Mapping[str, object]],
    legal_intent_ids: Iterable[str] = (),
    params: Mapping[str, object] | None = None,
    slot_audit: SlotAuditBinding | None = None,
    solver_hints: SolverHintsBinding | None = None,
) -> SlurpNodeContextPolicy:
    """Resolve one validated ``context_policy`` block into a live policy.

    ``level`` is the default every boundary of :data:`SLURP_BOUNDARY_IDS`
    takes; ``boundaries`` overrides named ones. Every ``structured`` boundary
    gets its declared template or, absent a declaration, the design's own
    default for that boundary.
    """

    if level not in LEVELS:
        raise NodeContextPolicyError(f"node context level must be one of {list(LEVELS)}")
    resolved: dict[tuple[str, str], NodeContextBoundaryPolicy] = {}
    for key in sorted(SLURP_BOUNDARY_IDS):
        spelling = f"{key[0]}:{key[1]}"
        entry = dict(boundaries.get(spelling, {}))
        entry_level = entry.get("level", level)
        if entry_level not in LEVELS:
            raise NodeContextPolicyError(
                f"boundary {spelling!r} level must be one of {list(LEVELS)}"
            )
        rule = entry.get("on_parse_failure", SLURP_BOUNDARY_PARSE_FAILURE[key])
        if rule not in PARSE_FAILURE_RULES:
            raise NodeContextPolicyError(
                f"boundary {spelling!r} on_parse_failure must be one of "
                f"{list(PARSE_FAILURE_RULES)}"
            )
        if entry_level == "cleaned" and key[1] not in CLEANING_RENDER_TEMPLATES:
            # Checked before the L1 template is loaded, so a boundary that may
            # not be cleaned says so rather than complaining about a template.
            raise NodeContextPolicyError(
                f"boundary {spelling!r} cannot be cleaned: this carrier registers a "
                f"cleaning renderer only for {sorted(CLEANING_RENDER_TEMPLATES)}"
            )
        template = None
        if entry_level in {"structured", "cleaned"}:
            # E8b: a cleaned boundary is L1 FIRST, so it resolves the same L1
            # template a structured one does -- that rendering is both what the
            # cleaning contact is handed and what the boundary falls back to.
            relpath = entry.get("template", SLURP_BOUNDARY_TEMPLATES[key])
            template = load_node_context_template(repo_root, relpath)
            if template.renderer != RENDERER_KEYS[key]:
                raise NodeContextPolicyError(
                    f"boundary {spelling!r} requires a {RENDERER_KEYS[key]!r} "
                    f"template; {relpath!r} declares {template.renderer!r}"
                )
        cleaning = None
        if entry_level == "cleaned":
            cleaning = _resolve_cleaning(
                entry.get("cleaning"), key=key, spelling=spelling,
                repo_root=repo_root,
            )
        elif "cleaning" in entry:
            raise NodeContextPolicyError(
                f"boundary {spelling!r} declares a cleaning contact at level "
                f"{entry_level!r}; only a 'cleaned' boundary may declare one"
            )
        resolved[key] = NodeContextBoundaryPolicy(
            consumer_role_kind=key[0], semantic_class=key[1], level=entry_level,
            template=template, on_parse_failure=rule, cleaning=cleaning,
        )
    if params is None:
        if any(entry.level != "raw" for entry in resolved.values()):
            raise NodeContextPolicyError(
                "a structured node context policy requires params"
            )
        return SlurpNodeContextPolicy(
            policy_id=policy_id, boundaries=resolved, slot_audit=slot_audit,
            solver_hints=solver_hints,
            # E19: an all-raw policy declares no params, so an audit attached
            # to the sealed draft binds the carrier's own closed contract.
            draft_response_schema=(
                None if slot_audit is None else SLURP_CLOSED_DRAFT_SCHEMA
            ),
        )
    return SlurpNodeContextPolicy(
        policy_id=policy_id,
        boundaries=resolved,
        legal_intent_ids=tuple(legal_intent_ids),
        max_candidates=params["max_candidates"],
        projection_policy=params["projection_policy"],
        draft_response_schema=params["draft_response_schema"],
        legal_entity_types=tuple(params.get("legal_entity_types", ())),
        slot_audit=slot_audit,
        solver_hints=solver_hints,
    )


__all__ = [
    "ACQUIRED_EVIDENCE_BOUNDARY",
    "ACQUIRED_EVIDENCE_BOUNDARY_ID",
    "ACQUIRED_EVIDENCE_RENDERER",
    "ACQUIRED_EVIDENCE_TEMPLATE",
    "ACQUISITION_ROLE_KIND",
    "AMONG_CANDIDATES",
    "CANDIDATES_UNAVAILABLE",
    "CHECK_NA",
    "CHECK_NO",
    "CHECK_NO_INVENTORY",
    "CHECK_YES",
    "CLEANING_ACCEPTED",
    "CLEANING_FALLBACK_L1",
    "CLEANING_FIXED_WORDS",
    "CLEANING_INSTRUCTION_TEMPLATES",
    "CLEANING_INVALID_RULES",
    "CLEANING_ISSUE_FIELDS",
    "CLEANING_KEYS",
    "CLEANING_MAX_ISSUES",
    "CLEANING_PROBLEM_MAX_CHARS",
    "CLEANING_REJECTED",
    "CLEANING_RENDER_TEMPLATES",
    "CLEANING_RESPONSE_FORMAT_ID",
    "CLEANING_SCHEMA",
    "CLEANING_SCHEMA_SHA256",
    "CLEANING_SKIPPED",
    "CLEANING_SUPERSEDED_REASON",
    "CLEANING_VERDICTS",
    "CLOSED_VOCABULARY",
    "EVIDENCE_AVAILABLE",
    "EVIDENCE_UNAVAILABLE",
    "FALLBACK_OMIT",
    "FALLBACK_RAW",
    "FALLBACK_REFUSE",
    "LEVELS",
    "NODE_CONTEXT_COMPILATION_SCHEMA",
    "NODE_CONTEXT_POLICY_ID",
    "NODE_CONTEXT_RECEIPT_SCHEMA",
    "NODE_CONTEXT_TEMPLATE_SCHEMA",
    "NOT_AMONG_CANDIDATES",
    "NO_ACQUIRED_EVIDENCE",
    "PARSER_IDS",
    "PARSE_FAILURE_RULES",
    "PROVENANCE_ACQUIRED",
    "RENDERER_KEYS",
    "RENDERER_SECTIONS",
    "ROLE_KINDS",
    "SEMANTIC_CLASSES",
    "SLOT_AUDIT_ATTACHMENTS",
    "SLOT_AUDIT_ATTACHMENT_L1",
    "SLOT_AUDIT_ATTACHMENT_RAW",
    "SLOT_AUDIT_BOUNDARY",
    "SLOT_AUDIT_RENDERER",
    "SLOT_AUDIT_TEMPLATE",
    "SLURP_CLOSED_DRAFT_SCHEMA",
    "SOLVER_HINTS_BOUNDARY",
    "SOLVER_HINTS_RENDERER",
    "SOLVER_HINTS_TEMPLATE",
    "SLURP_BOUNDARY_IDS",
    "SLURP_BOUNDARY_PARSE_FAILURE",
    "SLURP_BOUNDARY_TEMPLATES",
    "CleanedReview",
    "CleaningContactOutcome",
    "CleaningContactRequest",
    "NodeContextBoundaryPolicy",
    "NodeContextCleaningPolicy",
    "NodeContextCleaningRejected",
    "NodeContextCompilation",
    "NodeContextPolicyError",
    "NodeContextTemplate",
    "ParsedDraft",
    "RenderedBlock",
    "SlotAuditBinding",
    "SolverHintsBinding",
    "SlurpNodeContextPolicy",
    "Substitution",
    "build_slurp_node_context_policy",
    "content_tokens",
    "render_acquired_evidence",
    "known_tool_call_sources",
    "load_node_context_template",
    "ncp_review_issues_response_format",
    "parse_draft",
    "parse_node_context_template",
    "parse_plan_action",
    "parse_tool_observation",
    "resolve_slot_audit_binding",
    "resolve_solver_hints_binding",
    "validate_cleaning_document",
]
