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
    SLURP_BOUNDARY_IDS,
    NodeContextPolicyError,
    build_slurp_node_context_policy,
)

#: The policy id an OFF-arm declaration that names none carries in its
#: receipts, so a ``level: "raw"`` row still says which policy decided it.
RAW_NODE_CONTEXT_POLICY_ID = "raw-node-context-v1"

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
    policy_id: str,
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


def build_node_context_policy_binding(
    config_json: str, perception_response_format: Mapping[str, object],
    repo_root: Path,
) -> NodeContextPolicyBinding:
    """Resolve the canonical config text into a live, template-bound policy."""

    spec = json.loads(config_json)
    if validate_node_context_policy_config(spec) != config_json:
        raise ValueError("node context config is not its canonical bound representation")
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
        )
        return NodeContextPolicyBinding(
            policy=policy,
            producers={},
            source_format_sha256=hashlib.sha256(
                _bytes(perception_response_format)
            ).hexdigest(),
            config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),
            template_sha256s={},
        )
    factory = ROLE_CONTEXT_COMPILERS.resolve(spec["policy_id"])
    policy = factory(
        perception_response_format=perception_response_format,
        params=spec["params"],
        repo_root=repo_root,
        level=spec["level"],
        boundaries=spec.get("boundaries", {}),
        policy_id=spec["policy_id"],
    )
    templates: dict[str, str] = {}
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
    "RAW_NODE_CONTEXT_POLICY_ID",
    "PRODUCER_ROLE_KINDS",
    "REVIEW_FINDINGS_RESPONSE_FORMAT_ID",
    "NodeContextPolicyBinding",
    "build_node_context_policy_binding",
    "build_slurp_node_context_policy_compiler",
    "is_node_context_null_arm",
    "node_context_cleaning_boundaries",
    "node_context_producer_formats",
    "node_context_source_format_id",
    "validate_node_context_policy_config",
]
