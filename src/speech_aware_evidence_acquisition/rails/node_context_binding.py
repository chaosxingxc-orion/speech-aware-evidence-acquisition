"""Bind a registered node-context policy to the actual phase input contracts.

The config surface is ONE key, ``native_episode.context_policy``
(``rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS``). Its value is either the
string level that applies to every boundary, or an object whose ``level`` is
that default and whose ``boundaries`` overrides named ones -- design
``docs/superpowers/specs/2026-09-17-node-context-policy-design.md`` section 5.

``native_episode.role_context`` is FOLDED under this key: its ``policy_id`` /
``params`` pair is the ``structured`` level's implementation, not a second
switch, so a fragment carrying both is refused
(``rails.native_episode_config.load_native_episode_config``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ..core.base import ROLE_CONTEXT_COMPILERS, CoreError
from .node_context_policy import (
    CLEANING_INVALID_RULES,
    CLEANING_KEYS,
    CLEANING_RENDER_TEMPLATES,
    LEVELS,
    PARSE_FAILURE_RULES,
    SLOT_AUDIT_ATTACHMENT_L1,
    SLOT_AUDIT_ATTACHMENT_RAW,
    SLOT_AUDIT_BOUNDARY,
    SLURP_BOUNDARY_IDS,
    SOLVER_HINTS_BOUNDARY,
    NodeContextPolicyError,
    build_slurp_node_context_policy,
    resolve_slot_audit_binding,
    resolve_solver_hints_binding,
)
from .scenario_hints import (
    SCENARIO_HINTS_BOUND_KEYS,
    SCENARIO_HINTS_VIEW_ID,
    ScenarioHintsError,
    load_scenario_hints_table,
    scenario_hints_bounds,
    validate_scenario_hints_pin,
)
from .slot_audit import (
    SLOT_AUDIT_VIEW_ID,
    SlotAuditError,
    load_slot_audit_table,
    slot_audit_thresholds,
)

#: The policy id an OFF-arm declaration that names none carries in its
#: receipts, so a ``level: "raw"`` row still says which policy decided it.
RAW_NODE_CONTEXT_POLICY_ID = "raw-node-context-v1"

#: E19 (2026-09-19, owner decision 32): the ``context_policy`` value an
#: armed ``native_episode.reviewer_audit`` composes when the fragment
#: declares NO policy at all -- the key's own bare OFF arm. It renders
#: every state untouched and still emits one ``level: "raw"`` receipt row
#: per boundary per contact, which is what turns "only the Reviewer's
#: draft boundary moved" from a claim into a checked statement.
IMPLICIT_RAW_CONTEXT_POLICY = "raw"

#: The producing role of each semantic class, for the ``producers`` block.
PRODUCER_ROLE_KINDS: Mapping[str, str] = {
    "candidate-hypothesis": "perception",
    "current-draft": "solver",
    "review-finding": "reviewer",
    "plan-action": "planner",
}

#: Semantic classes whose producer may declare a response format at E8a. Only
#: the Reviewer's: the audit measured 0 of 2,167 anchor Reviewer outputs
#: parsing under the repository's own registered findings parser, because the
#: Reviewer prompt asks for prose and its phase declares no response format
#: (audit section 6). Coordinator decision 1 of 2026-09-17 closes that gap
#: HERE, in the boundary policy, so B7a's L1 is the whole boundary policy:
#: producer format, parser and consumer template.
PRODUCER_FORMAT_CLASSES = ("review-finding",)

#: The response format the ``review-finding`` producer may declare. It renders
#: exactly ``rails.review_findings``'s own registered contract, so a Reviewer
#: generated under it parses under ``parse_review_findings`` by construction.
REVIEW_FINDINGS_RESPONSE_FORMAT_ID = "saea-review-findings-v1"

#: E12 (2026-09-19, owner directive 26, cell B8b): the fields
#: ``native_episode.reviewer_audit`` declares. ``view``, ``release`` and
#: ``snapshot`` are required -- a view with no pinned bytes is not a view --
#: and ``thresholds`` / ``template`` fall back to the module's registered
#: defaults.
_REVIEWER_AUDIT_REQUIRED_KEYS = frozenset({"view", "release", "snapshot"})
_REVIEWER_AUDIT_OPTIONAL_KEYS = frozenset({"thresholds", "template"})

#: E14 (2026-09-19, owner directive 26, cell B8c): the fields
#: ``native_episode.solver_hints`` declares. ``view``, ``release`` and
#: ``snapshot`` are required -- a view with no pinned bytes is not a view --
#: and the two render bounds plus ``template`` fall back to the registered
#: defaults of ``rails.scenario_hints``.
_SOLVER_HINTS_REQUIRED_KEYS = frozenset({"view", "release", "snapshot"})
_SOLVER_HINTS_OPTIONAL_KEYS = frozenset(
    {"template", *SCENARIO_HINTS_BOUND_KEYS}
)

_TOP_LEVEL_KEYS = frozenset({"level", "policy_id", "params", "boundaries", "producers"})
_BOUNDARY_KEYS = frozenset({"level", "template", "on_parse_failure", "cleaning"})
_REQUIRED_PARAM_KEYS = frozenset({"max_candidates", "projection_policy",
                                  "draft_response_schema"})
_OPTIONAL_PARAM_KEYS = frozenset({"legal_entity_types"})


def _bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _params(params: object) -> Mapping[str, object]:
    """The policy's carrier-local parameters: the same closed Perception and
    draft contract ``rails.role_context_binding`` already validates, plus the
    optional legal entity inventory the HARNESS CHECKS block reads."""

    if (
        not isinstance(params, Mapping)
        or not _REQUIRED_PARAM_KEYS <= set(params)
        or set(params) - _REQUIRED_PARAM_KEYS - _OPTIONAL_PARAM_KEYS
    ):
        raise ValueError("node context params have unknown or missing fields")
    maximum = params["max_candidates"]
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        raise ValueError("node context candidate maximum must be positive")
    from .slurp_intent_hypotheses import (  # noqa: PLC0415 (light package top level)
        BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    )

    policies = {
        BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    }
    projection = params["projection_policy"]
    if not isinstance(projection, str) or projection not in policies or (
        maximum > 3
        and projection != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
    ):
        raise ValueError("node context candidate projection is invalid")
    from .role_context import (  # noqa: PLC0415 (light package top level)
        validate_role_context_draft_schema,
    )

    validate_role_context_draft_schema(params["draft_response_schema"])
    types = params.get("legal_entity_types", [])
    if (
        not isinstance(types, (list, tuple))
        or any(not isinstance(item, str) or not item.strip() for item in types)
        or len(set(types)) != len(types)
    ):
        raise ValueError(
            "node context legal_entity_types must be unique non-empty strings"
        )
    return params


def _cleaning(entry: object, *, spelling: str, semantic: str) -> Mapping[str, object]:
    """E8b: validate one boundary's declared cleaning contact.

    The block's fields are exactly the design's four. The response format id
    must be registered AND must render with no lock and no root, because the
    runner resolves it at request-composition time from the frozen registry
    alone -- there is no flight-side resolution path for a contact that is not
    a program phase.
    """

    if semantic not in CLEANING_RENDER_TEMPLATES:
        raise ValueError(
            f"node context boundary {spelling!r} cannot be cleaned: this carrier "
            f"registers a cleaning renderer only for "
            f"{sorted(CLEANING_RENDER_TEMPLATES)}"
        )
    if not isinstance(entry, Mapping) or set(entry) != CLEANING_KEYS:
        raise ValueError(
            f"node context boundary {spelling!r} at level 'cleaned' requires a "
            f"cleaning block declaring exactly {sorted(CLEANING_KEYS)}"
        )
    phase_id = entry["phase_id"]
    if not isinstance(phase_id, str) or not phase_id.strip():
        raise ValueError(
            f"node context boundary {spelling!r} cleaning phase_id must be text"
        )
    template = entry["instruction_template"]
    if not isinstance(template, str) or not template.startswith("probes/"):
        raise ValueError(
            f"node context boundary {spelling!r} cleaning instruction_template must "
            "be a 'probes/<name>.txt' path under configs/"
        )
    if entry["on_invalid"] not in CLEANING_INVALID_RULES:
        raise ValueError(
            f"node context boundary {spelling!r} cleaning on_invalid must be one of "
            f"{list(CLEANING_INVALID_RULES)}"
        )
    format_id = entry["response_format_id"]
    if not isinstance(format_id, str) or not format_id.strip():
        raise ValueError(
            f"node context boundary {spelling!r} cleaning response_format_id must "
            "be text"
        )
    from ..core.base import RESPONSE_FORMATS  # noqa: PLC0415
    from . import controllers  # noqa: F401, PLC0415 (canonical registrations)

    try:
        builder = RESPONSE_FORMATS.resolve(format_id)
    except CoreError as error:
        raise ValueError(str(error)) from error
    try:
        document = builder()
    except TypeError as error:
        raise ValueError(
            f"node context cleaning response format {format_id!r} requires a lock or "
            "a root; a cleaning contact resolves its format from the registry alone"
        ) from error
    if not isinstance(document, Mapping) or not document:
        raise ValueError(
            f"node context cleaning response format {format_id!r} renders nothing"
        )
    return entry


def _boundaries(
    boundaries: object, *, default_level: str | None = None,
) -> Mapping[str, Mapping[str, object]]:
    if not isinstance(boundaries, Mapping):
        raise ValueError("node context boundaries must be an object")
    legal = {f"{role}:{semantic}" for role, semantic in SLURP_BOUNDARY_IDS}
    for spelling, entry in boundaries.items():
        if spelling not in legal:
            raise ValueError(
                f"node context boundary {spelling!r} is not one of this carrier's "
                f"boundaries {sorted(legal)}"
            )
        if not isinstance(entry, Mapping) or set(entry) - _BOUNDARY_KEYS:
            raise ValueError(
                f"node context boundary {spelling!r} has unknown fields; a boundary "
                f"declares {sorted(_BOUNDARY_KEYS)}"
            )
        level = entry.get("level", default_level)
        if level is not None and level not in LEVELS:
            raise ValueError(
                f"node context boundary {spelling!r} level must be one of {list(LEVELS)}"
            )
        if level == "cleaned":
            _cleaning(entry.get("cleaning"), spelling=spelling, semantic=spelling.split(":", 1)[1])
        elif "cleaning" in entry:
            raise ValueError(
                f"node context boundary {spelling!r} declares a cleaning contact at "
                f"level {level!r}; only a 'cleaned' boundary may declare one"
            )
        rule = entry.get("on_parse_failure")
        if rule is not None and rule not in PARSE_FAILURE_RULES:
            raise ValueError(
                f"node context boundary {spelling!r} on_parse_failure must be one of "
                f"{list(PARSE_FAILURE_RULES)}"
            )
        template = entry.get("template")
        if template is not None and (
            not isinstance(template, str) or not template.startswith("probes/")
        ):
            raise ValueError(
                f"node context boundary {spelling!r} template must be a "
                "'probes/<name>.txt' path under configs/"
            )
    return boundaries


def _producers(producers: object) -> Mapping[str, Mapping[str, object]]:
    if not isinstance(producers, Mapping):
        raise ValueError("node context producers must be an object")
    for semantic_class, entry in producers.items():
        if semantic_class not in PRODUCER_FORMAT_CLASSES:
            raise ValueError(
                f"node context producer {semantic_class!r} may not declare a response "
                f"format; the classes that may are {list(PRODUCER_FORMAT_CLASSES)}"
            )
        if not isinstance(entry, Mapping) or set(entry) != {"response_format_id"}:
            raise ValueError(
                f"node context producer {semantic_class!r} declares exactly "
                "response_format_id"
            )
        format_id = entry["response_format_id"]
        if not isinstance(format_id, str) or not format_id.strip():
            raise ValueError(
                f"node context producer {semantic_class!r} response_format_id must be text"
            )
        from ..core.base import RESPONSE_FORMATS  # noqa: PLC0415
        from . import controllers  # noqa: F401, PLC0415 (canonical registrations)

        try:
            RESPONSE_FORMATS.resolve(format_id)
        except CoreError as error:
            raise ValueError(str(error)) from error
    return producers


def is_node_context_null_arm(document: object) -> bool:
    """Whether a ``context_policy`` value is the key's own OFF form: absent,
    the literal ``"raw"``, or an object whose effective level is ``raw`` at
    every boundary.

    This is the semantics ``rails.config_tables.is_episode_null_arm`` exposes
    to the harness-admission gate, and the one
    ``load_native_episode_config`` applies when it decides whether the policy
    reaches the runtime at all: an all-raw declaration composes to a policy
    that is byte-identical to no policy, so the loader keeps none.
    """

    if document is None or document == "raw":
        return True
    if isinstance(document, str):
        return False
    if not isinstance(document, Mapping):
        return False
    level = document.get("level", "raw")
    boundaries = document.get("boundaries") or {}
    if not isinstance(boundaries, Mapping):
        return False
    declared = {f"{role}:{semantic}" for role, semantic in SLURP_BOUNDARY_IDS}
    if level != "raw":
        # A non-raw default is OFF only if EVERY boundary overrides it to raw.
        return all(
            isinstance(boundaries.get(spelling), Mapping)
            and boundaries[spelling].get("level") == "raw"
            for spelling in declared
        )
    return all(
        not isinstance(entry, Mapping) or entry.get("level", "raw") == "raw"
        for entry in boundaries.values()
    )


def validate_node_context_policy_config(document: object) -> str:
    """Return the immutable canonical config text, with no source or model I/O."""

    from . import controllers  # noqa: F401, PLC0415 (canonical registrations)

    if isinstance(document, str):
        if document not in LEVELS:
            raise ValueError(
                f"native_episode.context_policy must be one of {list(LEVELS)} or an object"
            )
        if document != "raw":
            raise ValueError(
                f"a bare {document!r} level declares no policy_id and no params; "
                "every level above raw needs both, so it is declared as an object"
            )
        return _bytes(document).decode()
    if not isinstance(document, Mapping) or set(document) - _TOP_LEVEL_KEYS:
        raise ValueError(
            f"native_episode.context_policy declares {sorted(_TOP_LEVEL_KEYS)}"
        )
    level = document.get("level")
    if level not in LEVELS:
        raise ValueError(
            f"native_episode.context_policy.level must be one of {list(LEVELS)}"
        )
    if level == "cleaned":
        # E8b: the DEFAULT level applies to every boundary of the carrier, and
        # no carrier registers cleaning assets for every boundary -- cleaning
        # is declared per boundary, one contact at a time, exactly as design
        # section 5's fragment does.
        raise ValueError(
            "native_episode.context_policy.level cannot default to 'cleaned'; a "
            "cleaning contact is declared on the boundary it cleans"
        )
    _boundaries(document.get("boundaries", {}), default_level=level)
    _producers(document.get("producers", {}))
    if is_node_context_null_arm(document):
        if "params" in document:
            raise ValueError(
                "an all-raw native_episode.context_policy declares no params; raw is "
                "the OFF arm and parses nothing"
            )
        return _bytes(dict(document)).decode()
    policy_id = document.get("policy_id")
    if not isinstance(policy_id, str) or not policy_id.strip():
        raise ValueError(
            "a structured native_episode.context_policy requires a registered policy_id"
        )
    try:
        factory = ROLE_CONTEXT_COMPILERS.resolve(policy_id)
    except CoreError as error:
        raise ValueError(str(error)) from error
    validator = getattr(factory, "validate_params", None)
    if not callable(factory) or not callable(validator):
        raise ValueError(
            "node context policy requires a registered parameter validator"
        )
    if "params" not in document:
        raise ValueError(
            "a structured native_episode.context_policy requires params"
        )
    validator(document["params"])
    return _bytes(dict(document)).decode()


def is_reviewer_audit_null_arm(document: object) -> bool:
    """E12: whether a ``native_episode.reviewer_audit`` value is the key's own
    OFF form. The node is ABSENT or it is armed -- there is no third shape,
    exactly as ``native_episode.deliver_normaliser``'s is."""

    return document is None


def validate_reviewer_audit_config(document: object) -> str:
    """Return the immutable canonical config text for the armed audit block.

    SHAPE ONLY, and deliberately: no file is opened here, exactly as
    :func:`validate_node_context_policy_config` opens no template. The pinned
    bytes are read, hashed and cross-checked once, in
    :func:`build_node_context_policy_binding`, at the same point the templates
    are loaded -- so a config can be validated (and its hash composed) on a
    machine that carries no repository checkout of the released view.
    """

    if not isinstance(document, Mapping):
        raise ValueError(
            "native_episode.reviewer_audit must be an object declaring "
            f"{sorted(_REVIEWER_AUDIT_REQUIRED_KEYS)}"
        )
    unknown = sorted(
        set(document) - _REVIEWER_AUDIT_REQUIRED_KEYS - _REVIEWER_AUDIT_OPTIONAL_KEYS
    )
    if unknown or not _REVIEWER_AUDIT_REQUIRED_KEYS <= set(document):
        raise ValueError(
            "native_episode.reviewer_audit has unknown or missing fields; it "
            f"declares {sorted(_REVIEWER_AUDIT_REQUIRED_KEYS)} and may add "
            f"{sorted(_REVIEWER_AUDIT_OPTIONAL_KEYS)}"
        )
    if document["view"] != SLOT_AUDIT_VIEW_ID:
        raise ValueError(
            f"native_episode.reviewer_audit.view must be {SLOT_AUDIT_VIEW_ID!r}; this "
            "carrier registers no other slot-audit view"
        )
    for field_name in ("release", "snapshot"):
        pin = document[field_name]
        if (
            not isinstance(pin, Mapping)
            or set(pin) != {"relpath", "sha256"}
            or not isinstance(pin["relpath"], str)
            or not pin["relpath"].startswith("knowledge/slurp/semantic/")
            or not isinstance(pin["sha256"], str)
            or len(pin["sha256"]) != 64
        ):
            raise ValueError(
                f"native_episode.reviewer_audit.{field_name} must pin a committed "
                "knowledge/slurp/semantic/... file by relpath and sha256"
            )
    template = document.get("template")
    if template is not None and (
        not isinstance(template, str) or not template.startswith("probes/")
    ):
        raise ValueError(
            "native_episode.reviewer_audit.template must be a 'probes/<name>.txt' "
            "path under configs/"
        )
    try:
        slot_audit_thresholds(document.get("thresholds"))
    except SlotAuditError as error:
        raise ValueError(str(error)) from error
    return _bytes(dict(document)).decode()


def _declared_boundary_level(
    context_policy_json: str | None, *, boundary: tuple[str, str],
) -> str:
    """The effective level one boundary takes under a declared policy.

    ``raw`` for a config that declares no ``context_policy`` at all and for
    the key's bare ``"raw"`` arm: both put exactly the sealed bytes on the
    wire, which is what an E19 attachment adds to.
    """

    if context_policy_json is None:
        return "raw"
    spec = json.loads(context_policy_json)
    if isinstance(spec, str):
        return spec
    if not isinstance(spec, Mapping):
        return "raw"
    spelling = f"{boundary[0]}:{boundary[1]}"
    default_level = spec.get("level", "raw")
    entry = (spec.get("boundaries") or {}).get(spelling)
    return (
        entry.get("level", default_level)
        if isinstance(entry, Mapping)
        else default_level
    )


def _requires_structured_boundary(
    context_policy_json: str | None, *, key: str, boundary: tuple[str, str],
) -> None:
    """Refuse an armed context block whose boundary is not at L1.

    E14's Solver scenario hints: the block is an ADDITION to that
    boundary's own L1 rendering, so it has nothing to attach to at ``raw``
    and would be cleaned away at ``cleaned``. Checked before contact, by
    name. (E12's Reviewer audit shared this rule until E19 re-based it on
    the sealed draft -- see :func:`reviewer_audit_boundary_attachment`.)
    """

    spelling = f"{boundary[0]}:{boundary[1]}"
    if context_policy_json is None:
        raise ValueError(
            f"{key} requires a declared "
            f"native_episode.context_policy with {spelling} at level 'structured'"
        )
    spec = json.loads(context_policy_json)
    if isinstance(spec, str) or not isinstance(spec, Mapping):
        raise ValueError(
            f"{key} requires {spelling} at level 'structured'"
        )
    level = _declared_boundary_level(context_policy_json, boundary=boundary)
    if level != "structured":
        raise ValueError(
            f"{key} requires the {spelling} boundary at level "
            f"'structured'; the declared policy puts it at {level!r}"
        )


def reviewer_audit_boundary_attachment(context_policy_json: str | None) -> str:
    """E19: which attachment an armed audit takes, or refuse it by name.

    E12 required the boundary at ``structured``, because the block was an
    addition to that boundary's L1 rendering and had nothing to attach to
    at raw. Cell B7a v2 read the L1 policy HARMFUL
    (``docs/results/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-verdict.md``) and
    owner decision 32 closed every cell registered on it, so the block is
    re-based rather than retired: at ``raw`` -- including the case of no
    declared policy at all -- it is appended to the SEALED draft bytes,
    which is an addition to exactly the one thing the Reviewer would
    otherwise have received at this boundary.

    ``cleaned`` stays refused by name: a cleaning contact REWRITES the
    rendering the block is appended to, so the block would be cleaned away.
    """

    spelling = f"{SLOT_AUDIT_BOUNDARY[0]}:{SLOT_AUDIT_BOUNDARY[1]}"
    level = _declared_boundary_level(context_policy_json, boundary=SLOT_AUDIT_BOUNDARY)
    if level == "cleaned":
        raise ValueError(
            f"native_episode.reviewer_audit cannot attach to the {spelling} "
            "boundary at level 'cleaned'; a cleaning contact rewrites the "
            "rendering the block is appended to"
        )
    return (
        SLOT_AUDIT_ATTACHMENT_L1 if level == "structured"
        else SLOT_AUDIT_ATTACHMENT_RAW
    )


def solver_hints_requires_structured_boundary(
    context_policy_json: str | None,
) -> None:
    """Refuse an armed scenario-hints block whose boundary is not at L1 (E14)."""

    _requires_structured_boundary(
        context_policy_json,
        key="native_episode.solver_hints",
        boundary=SOLVER_HINTS_BOUNDARY,
    )


def is_solver_hints_null_arm(document: object) -> bool:
    """E14: whether a ``native_episode.solver_hints`` value is the key's own
    OFF form. The node is ABSENT or it is armed -- there is no third shape,
    exactly as ``native_episode.reviewer_audit``'s is."""

    return document is None


def validate_solver_hints_config(document: object) -> str:
    """Return the immutable canonical config text for the armed hints block.

    SHAPE ONLY, and deliberately: no file is opened here, exactly as
    :func:`validate_reviewer_audit_config` opens none. The released bytes are
    read, hashed and cross-checked once, in
    :func:`build_node_context_policy_binding`, so a config can be validated
    (and its hash composed) on a machine that carries no materialised data
    root.
    """

    if not isinstance(document, Mapping):
        raise ValueError(
            "native_episode.solver_hints must be an object declaring "
            f"{sorted(_SOLVER_HINTS_REQUIRED_KEYS)}"
        )
    unknown = sorted(
        set(document) - _SOLVER_HINTS_REQUIRED_KEYS - _SOLVER_HINTS_OPTIONAL_KEYS
    )
    if unknown or not _SOLVER_HINTS_REQUIRED_KEYS <= set(document):
        raise ValueError(
            "native_episode.solver_hints has unknown or missing fields; it "
            f"declares {sorted(_SOLVER_HINTS_REQUIRED_KEYS)} and may add "
            f"{sorted(_SOLVER_HINTS_OPTIONAL_KEYS)}"
        )
    if document["view"] != SCENARIO_HINTS_VIEW_ID:
        raise ValueError(
            f"native_episode.solver_hints.view must be {SCENARIO_HINTS_VIEW_ID!r}; "
            "this carrier registers no other scenario-hints view"
        )
    for field_name in ("release", "snapshot"):
        try:
            validate_scenario_hints_pin(
                document[field_name], field_name=f"solver_hints.{field_name}",
            )
        except ScenarioHintsError as error:
            raise ValueError(str(error)) from error
    template = document.get("template")
    if template is not None and (
        not isinstance(template, str) or not template.startswith("probes/")
    ):
        raise ValueError(
            "native_episode.solver_hints.template must be a 'probes/<name>.txt' "
            "path under configs/"
        )
    try:
        scenario_hints_bounds({
            name: document[name]
            for name in SCENARIO_HINTS_BOUND_KEYS
            if name in document
        })
    except ScenarioHintsError as error:
        raise ValueError(str(error)) from error
    return _bytes(dict(document)).decode()


@dataclass(frozen=True)
class NodeContextPolicyBinding:
    """One flight's live policy, bound to the actual Perception contract."""

    policy: object
    producers: Mapping[str, Mapping[str, object]]
    source_format_sha256: str
    config_sha256: str
    template_sha256s: Mapping[str, str]


def build_slurp_node_context_policy_compiler(
    *, perception_response_format: Mapping[str, object], params: Mapping[str, object],
    repo_root: Path, level: str, boundaries: Mapping[str, Mapping[str, object]],
    policy_id: str, slot_audit: object = None, solver_hints: object = None,
):
    """Derive legal candidate IDs from the actual bound Perception schema.

    Same shape and same reason as ``rails.role_context_binding.
    build_slurp_role_context_compiler``: the candidate inventory the policy
    renders is the inventory the Perception phase was actually generated under,
    never a second copy in a config fragment.
    """

    params = _params(params)
    try:
        candidates = perception_response_format["json_schema"]["schema"]["properties"][
            "candidates"
        ]
        legal = candidates["items"]["properties"]["intent_id"]["enum"]
    except (KeyError, TypeError):
        raise ValueError(
            "node context requires the actual typed Perception schema"
        ) from None
    if (
        not isinstance(legal, list)
        or not legal
        or any(not isinstance(item, str) or not item for item in legal)
        or len(legal) != len(set(legal))
        or candidates.get("maxItems") != params["max_candidates"]
    ):
        raise ValueError("node context candidate inventory or maximum differs")
    try:
        return build_slurp_node_context_policy(
            repo_root=repo_root, policy_id=policy_id, level=level,
            boundaries=boundaries, legal_intent_ids=tuple(legal), params=params,
            slot_audit=slot_audit, solver_hints=solver_hints,
        )
    except NodeContextPolicyError as error:
        raise ValueError(str(error)) from error


build_slurp_node_context_policy_compiler.validate_params = _params
build_slurp_node_context_policy_compiler.perception_response_format_id = (
    "slurp-intent-hypotheses-v1"
)


def node_context_source_format_id(config_json: str) -> str:
    """The Perception response format id the declared policy requires."""

    spec = json.loads(config_json)
    factory = ROLE_CONTEXT_COMPILERS.resolve(spec["policy_id"])
    required = getattr(factory, "perception_response_format_id", None)
    if not isinstance(required, str) or not required:
        raise ValueError("node context policy requires a source response format")
    return required


def node_context_cleaning_boundaries(config_json: str) -> tuple[str, ...]:
    """E8b: the boundary spellings this policy declares a cleaning contact on.

    ``rails.native_episode_config.load_native_episode_config`` reads this to
    raise the bounded contact ceiling: one cleaning contact per consumer
    contact at that boundary, so the ceiling gains
    ``(max_revisions + 1) * consumer_role.max_iterations`` per entry -- which
    for the only boundary this program proposes, ``planner:review-finding``
    with a one-iteration Planner, is exactly the ``(max_revisions + 1)`` design
    section 7 states, taking the anchor's 11 to 13.
    """

    spec = json.loads(config_json)
    if not isinstance(spec, Mapping):
        return ()
    boundaries = spec.get("boundaries") or {}
    if not isinstance(boundaries, Mapping):
        return ()
    default_level = spec.get("level", "raw")
    return tuple(sorted(
        spelling
        for spelling, entry in boundaries.items()
        if isinstance(entry, Mapping)
        and entry.get("level", default_level) == "cleaned"
    ))


def node_context_producer_formats(config_json: str) -> Mapping[str, str]:
    """``{role_kind: response_format_id}`` the declared policy requires of the
    producing phases -- the coupling ``load_native_episode_config`` checks the
    program against."""

    spec = json.loads(config_json)
    if not isinstance(spec, Mapping):
        return {}
    return {
        PRODUCER_ROLE_KINDS[semantic_class]: entry["response_format_id"]
        for semantic_class, entry in sorted(spec.get("producers", {}).items())
    }


def build_slot_audit_binding(reviewer_audit_json: str, repo_root: Path):
    """E12: resolve the canonical ``reviewer_audit`` text into a live binding.

    This is where the two pinned committed files are read, hashed against
    their declared pins and cross-checked, and where the committed audit
    template is loaded -- one place, fail-closed, before any contact.
    """

    spec = json.loads(reviewer_audit_json)
    if validate_reviewer_audit_config(spec) != reviewer_audit_json:
        raise ValueError(
            "reviewer audit config is not its canonical bound representation"
        )
    try:
        table = load_slot_audit_table(
            repo_root,
            release=spec["release"],
            snapshot=spec["snapshot"],
            view_id=spec["view"],
        )
        thresholds = slot_audit_thresholds(spec.get("thresholds"))
    except SlotAuditError as error:
        raise ValueError(str(error)) from error
    try:
        return resolve_slot_audit_binding(
            repo_root, table=table, thresholds=thresholds,
            template=spec.get("template"),
        )
    except NodeContextPolicyError as error:
        raise ValueError(str(error)) from error


def build_solver_hints_binding(
    solver_hints_json: str, repo_root: Path, data_root: Path,
):
    """E14: resolve the canonical ``solver_hints`` text into a live binding.

    This is where the two released files under the controlled data root are
    read, hashed against their declared pins and cross-checked, and where
    the committed hints template is loaded -- one place, fail-closed, before
    any contact.
    """

    spec = json.loads(solver_hints_json)
    if validate_solver_hints_config(spec) != solver_hints_json:
        raise ValueError(
            "solver hints config is not its canonical bound representation"
        )
    try:
        table = load_scenario_hints_table(
            data_root,
            release=spec["release"],
            snapshot=spec["snapshot"],
            view_id=spec["view"],
        )
        bounds = scenario_hints_bounds({
            name: spec[name] for name in SCENARIO_HINTS_BOUND_KEYS if name in spec
        })
    except ScenarioHintsError as error:
        raise ValueError(str(error)) from error
    try:
        return resolve_solver_hints_binding(
            repo_root, table=table, bounds=bounds, template=spec.get("template"),
        )
    except NodeContextPolicyError as error:
        raise ValueError(str(error)) from error


def _slot_audit_template_sha256s(slot_audit: object) -> dict[str, str]:
    """E12: the THREE assets the audit pins beside the boundary's own L1
    template -- its rendering template and the two released files of the
    construction table -- so a receipt names every byte the block was
    composed from. Empty when no audit is armed."""

    if slot_audit is None:
        return {}
    spelling = f"{SLOT_AUDIT_BOUNDARY[0]}:{SLOT_AUDIT_BOUNDARY[1]}"
    return {
        f"{spelling}:slot-audit": slot_audit.template.sha256,
        f"{spelling}:slot-audit-release": slot_audit.table.release_sha256,
        f"{spelling}:slot-audit-snapshot": slot_audit.table.snapshot_sha256,
    }


def build_node_context_policy_binding(
    config_json: str | None, perception_response_format: Mapping[str, object],
    repo_root: Path, reviewer_audit_json: str | None = None,
    solver_hints_json: str | None = None, data_root: Path | None = None,
) -> NodeContextPolicyBinding:
    """Resolve the canonical config text into a live, template-bound policy.

    ``reviewer_audit_json`` (E12) is the canonical text of an armed
    ``native_episode.reviewer_audit``; ``None`` -- every flight before E12 and
    every OFF arm -- leaves the policy exactly as it was and the
    ``reviewer:current-draft`` boundary renders the pre-E12 bytes.

    ``config_json`` is ``None`` when the fragment declares no
    ``context_policy`` at all. That is legal only with an armed audit (E19),
    and it composes the key's own bare ``"raw"`` arm: nothing is rendered,
    every boundary emits its ``level: "raw"`` row, and the audited draft
    boundary is the single place a byte moves.
    """

    if config_json is None:
        if reviewer_audit_json is None:
            raise ValueError(
                "a node context binding with no declared "
                "native_episode.context_policy requires an armed "
                "native_episode.reviewer_audit"
            )
        config_json = validate_node_context_policy_config(
            IMPLICIT_RAW_CONTEXT_POLICY
        )
    spec = json.loads(config_json)
    if validate_node_context_policy_config(spec) != config_json:
        raise ValueError("node context config is not its canonical bound representation")
    slot_audit = None
    if reviewer_audit_json is not None:
        reviewer_audit_boundary_attachment(config_json)
        slot_audit = build_slot_audit_binding(reviewer_audit_json, repo_root)
    solver_hints = None
    if solver_hints_json is not None:
        solver_hints_requires_structured_boundary(config_json)
        if data_root is None:
            raise ValueError(
                "native_episode.solver_hints requires the controlled data root "
                "its released scenario-hints view is read from"
            )
        solver_hints = build_solver_hints_binding(
            solver_hints_json, repo_root, Path(data_root),
        )
    if is_node_context_null_arm(spec):
        # The DECLARED OFF arm. It parses nothing and renders nothing, so it
        # needs neither the Perception schema nor a template -- but it still
        # compiles, so every boundary emits its ``level: "raw"`` receipt row
        # and L0's byte identity is a checked statement rather than the absence
        # of evidence (design section 9).
        level = "raw" if isinstance(spec, str) else spec.get("level", "raw")
        boundaries = {} if isinstance(spec, str) else spec.get("boundaries", {})
        policy = build_slurp_node_context_policy(
            repo_root=repo_root,
            policy_id=(
                RAW_NODE_CONTEXT_POLICY_ID if isinstance(spec, str)
                else spec.get("policy_id", RAW_NODE_CONTEXT_POLICY_ID)
            ),
            level=level if level == "raw" else "raw",
            boundaries={
                spelling: dict(entry, level="raw")
                for spelling, entry in boundaries.items()
            },
            # E19: an armed audit attaches to the SEALED draft bytes here.
            # The OFF arm stays exactly what it was -- ``slot_audit`` is
            # None on every flight that arms none.
            slot_audit=slot_audit,
        )
        return NodeContextPolicyBinding(
            policy=policy,
            producers={},
            source_format_sha256=hashlib.sha256(
                _bytes(perception_response_format)
            ).hexdigest(),
            config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),
            template_sha256s=_slot_audit_template_sha256s(slot_audit),
        )
    factory = ROLE_CONTEXT_COMPILERS.resolve(spec["policy_id"])
    policy = factory(
        perception_response_format=perception_response_format,
        params=spec["params"],
        repo_root=repo_root,
        level=spec["level"],
        boundaries=spec.get("boundaries", {}),
        policy_id=spec["policy_id"],
        slot_audit=slot_audit,
        solver_hints=solver_hints,
    )
    templates: dict[str, str] = dict(_slot_audit_template_sha256s(slot_audit))
    if solver_hints is not None:
        # E14: the hints block pins THREE assets beside the boundary's own L1
        # template -- its rendering template and the two released files of
        # the construction table -- so a receipt names every byte the block
        # was composed from.
        spelling = f"{SOLVER_HINTS_BOUNDARY[0]}:{SOLVER_HINTS_BOUNDARY[1]}"
        templates[f"{spelling}:scenario-hints"] = solver_hints.template.sha256
        templates[f"{spelling}:scenario-hints-release"] = (
            solver_hints.table.release_sha256
        )
        templates[f"{spelling}:scenario-hints-snapshot"] = (
            solver_hints.table.snapshot_sha256
        )
    for entry in policy.declared_boundaries():
        if entry["template_sha256"] is not None:
            templates[entry["boundary"]] = entry["template_sha256"]
        cleaning = entry.get("cleaning")
        if cleaning is None:
            continue
        # E8b: a cleaned boundary pins THREE committed assets -- its L1
        # template, the instruction the cleaning contact reads, and the
        # template an accepted cleaning output is rendered through.
        templates[f"{entry['boundary']}:cleaning-instruction"] = cleaning[
            "instruction_template_sha256"
        ]
        templates[f"{entry['boundary']}:cleaning-render"] = cleaning[
            "render_template_sha256"
        ]
    return NodeContextPolicyBinding(
        policy=policy,
        producers=dict(spec.get("producers", {})),
        source_format_sha256=hashlib.sha256(
            _bytes(perception_response_format)
        ).hexdigest(),
        config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),
        template_sha256s=templates,
    )


__all__ = [
    "PRODUCER_FORMAT_CLASSES",
    "IMPLICIT_RAW_CONTEXT_POLICY",
    "RAW_NODE_CONTEXT_POLICY_ID",
    "PRODUCER_ROLE_KINDS",
    "REVIEW_FINDINGS_RESPONSE_FORMAT_ID",
    "NodeContextPolicyBinding",
    "build_node_context_policy_binding",
    "build_slot_audit_binding",
    "build_slurp_node_context_policy_compiler",
    "build_solver_hints_binding",
    "is_node_context_null_arm",
    "is_reviewer_audit_null_arm",
    "is_solver_hints_null_arm",
    "node_context_cleaning_boundaries",
    "node_context_producer_formats",
    "node_context_source_format_id",
    "reviewer_audit_boundary_attachment",
    "solver_hints_requires_structured_boundary",
    "validate_node_context_policy_config",
    "validate_reviewer_audit_config",
    "validate_solver_hints_config",
]
