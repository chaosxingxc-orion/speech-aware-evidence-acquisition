"""E8a: the Node Context Policy (NCP) -- one declared handling policy per node
boundary, levels L0 (``raw``) and L1 (``structured``).

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

L2 (``cleaned``) is E8b and is NOT implemented here. Its config surface, its
receipt fields and its value validation are: a ``cleaned`` boundary is refused
at load time with :data:`CLEANED_LEVEL_REFUSAL`.
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
#: ``cleaned`` is L2 and belongs to E8b.
LEVELS = ("raw", "structured", "cleaned")
#: The message every ``cleaned`` declaration is refused with until E8b lands.
CLEANED_LEVEL_REFUSAL = "E8b not implemented"

#: Declared malformed rules (design section 3, L1 step 4).
FALLBACK_RAW = "raw"
FALLBACK_OMIT = "omit"
FALLBACK_REFUSE = "refuse"
PARSE_FAILURE_RULES = (FALLBACK_RAW, FALLBACK_OMIT, FALLBACK_REFUSE)

ROLE_KINDS = ("perception", "solver", "reviewer", "planner")
SEMANTIC_CLASSES = (
    "candidate-hypothesis",
    "current-draft",
    "review-finding",
    "plan-action",
    "tool-observation",
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
PROVENANCES = (
    PROVENANCE_SOURCE,
    PROVENANCE_COMPOSED,
    PROVENANCE_INVENTORY,
    PROVENANCE_VOCABULARY,
    PROVENANCE_COUNT,
    PROVENANCE_LIMIT,
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
    ) -> None:
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise NodeContextPolicyError("node context policy_id must be text")
        if not any(entry.level == "structured" for entry in boundaries.values()):
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
            self._validator = None
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
    ) -> NodeContextCompilation:
        """Return one contact's exposed states and its per-boundary receipt.

        The returned tuple has exactly the length and order of ``states``: this
        transform never adds, drops, merges or reorders a state.
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
                ))
                continue
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
                derived_fields=block.derived_fields,
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
        ):
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
        return block.finish({
            "candidate_count": len(rows),
            "intent_ids": [row["intent_id"] for row in rows],
        })

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
        return block.finish(derived)

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
    ) -> Mapping[str, object]:
        """A ``level: "raw"`` row. Its ``rendered_sha256`` equals the source's
        ``content_sha256`` -- that equality is what makes L0's claim of byte
        identity a checked statement rather than a comment."""

        return self._finish_row({
            "schema": NODE_CONTEXT_RECEIPT_SCHEMA,
            "policy_id": self.policy_id,
            "boundary": {
                "consumer_role_kind": role_kind,
                "semantic_class": semantic_class,
                "boundary_id": (
                    "B-NONE" if semantic_class is None
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
            "rendered_state_id": state.state_id,
            "rendered_sha256": _sha256_text(state.content),
            "rendered_chars": len(state.content),
            "derived_fields": {},
            "cleaning_contact": None,
        })

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
    ) -> Mapping[str, object]:
        template = policy.template
        return self._finish_row({
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
            "cleaning_contact": None,
        })


def build_slurp_node_context_policy(
    *,
    repo_root: Path,
    policy_id: str,
    level: str,
    boundaries: Mapping[str, Mapping[str, object]],
    legal_intent_ids: Iterable[str] = (),
    params: Mapping[str, object] | None = None,
) -> SlurpNodeContextPolicy:
    """Resolve one validated ``context_policy`` block into a live policy.

    ``level`` is the default every boundary of :data:`SLURP_BOUNDARY_IDS`
    takes; ``boundaries`` overrides named ones. Every ``structured`` boundary
    gets its declared template or, absent a declaration, the design's own
    default for that boundary.
    """

    if level not in LEVELS:
        raise NodeContextPolicyError(f"node context level must be one of {list(LEVELS)}")
    if level == "cleaned":
        raise NodeContextPolicyError(CLEANED_LEVEL_REFUSAL)
    resolved: dict[tuple[str, str], NodeContextBoundaryPolicy] = {}
    for key in sorted(SLURP_BOUNDARY_IDS):
        spelling = f"{key[0]}:{key[1]}"
        entry = dict(boundaries.get(spelling, {}))
        entry_level = entry.get("level", level)
        if entry_level not in LEVELS:
            raise NodeContextPolicyError(
                f"boundary {spelling!r} level must be one of {list(LEVELS)}"
            )
        if entry_level == "cleaned":
            raise NodeContextPolicyError(
                f"boundary {spelling!r}: {CLEANED_LEVEL_REFUSAL}"
            )
        rule = entry.get("on_parse_failure", SLURP_BOUNDARY_PARSE_FAILURE[key])
        if rule not in PARSE_FAILURE_RULES:
            raise NodeContextPolicyError(
                f"boundary {spelling!r} on_parse_failure must be one of "
                f"{list(PARSE_FAILURE_RULES)}"
            )
        template = None
        if entry_level == "structured":
            relpath = entry.get("template", SLURP_BOUNDARY_TEMPLATES[key])
            template = load_node_context_template(repo_root, relpath)
            if template.renderer != RENDERER_KEYS[key]:
                raise NodeContextPolicyError(
                    f"boundary {spelling!r} requires a {RENDERER_KEYS[key]!r} "
                    f"template; {relpath!r} declares {template.renderer!r}"
                )
        resolved[key] = NodeContextBoundaryPolicy(
            consumer_role_kind=key[0], semantic_class=key[1], level=entry_level,
            template=template, on_parse_failure=rule,
        )
    if params is None:
        if any(entry.level == "structured" for entry in resolved.values()):
            raise NodeContextPolicyError(
                "a structured node context policy requires params"
            )
        return SlurpNodeContextPolicy(policy_id=policy_id, boundaries=resolved)
    return SlurpNodeContextPolicy(
        policy_id=policy_id,
        boundaries=resolved,
        legal_intent_ids=tuple(legal_intent_ids),
        max_candidates=params["max_candidates"],
        projection_policy=params["projection_policy"],
        draft_response_schema=params["draft_response_schema"],
        legal_entity_types=tuple(params.get("legal_entity_types", ())),
    )


__all__ = [
    "AMONG_CANDIDATES",
    "CANDIDATES_UNAVAILABLE",
    "CHECK_NA",
    "CHECK_NO",
    "CHECK_NO_INVENTORY",
    "CHECK_YES",
    "CLEANED_LEVEL_REFUSAL",
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
    "PARSER_IDS",
    "PARSE_FAILURE_RULES",
    "RENDERER_KEYS",
    "RENDERER_SECTIONS",
    "ROLE_KINDS",
    "SEMANTIC_CLASSES",
    "SLURP_BOUNDARY_IDS",
    "SLURP_BOUNDARY_PARSE_FAILURE",
    "SLURP_BOUNDARY_TEMPLATES",
    "NodeContextBoundaryPolicy",
    "NodeContextCompilation",
    "NodeContextPolicyError",
    "NodeContextTemplate",
    "ParsedDraft",
    "RenderedBlock",
    "SlurpNodeContextPolicy",
    "Substitution",
    "build_slurp_node_context_policy",
    "known_tool_call_sources",
    "load_node_context_template",
    "parse_draft",
    "parse_node_context_template",
    "parse_plan_action",
    "parse_tool_observation",
]
