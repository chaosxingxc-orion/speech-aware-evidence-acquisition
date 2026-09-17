"""Bind a registered pure role-context compiler to actual phase input contracts."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from ..core.base import CoreError, ROLE_CONTEXT_COMPILERS


def _bytes(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode()


_REQUIRED_PARAM_KEYS = {"max_candidates", "projection_policy", "draft_response_schema"}
#: FIX-1 standing fallback (docs/results/2026-09-17-slurp-a3-coverage-
#: confusion-audit-v1.md), declared here beside ``projection_policy`` --
#: role-context rendering already independently declares its own
#: ``max_candidates``/``projection_policy`` over the same Perception
#: contract, and this option follows that same established pattern rather
#: than threading through a single physical config key.
_OPTIONAL_PARAM_KEYS = {"fallback_candidates", "fallback_distinction"}


def _params(params):
    if (
        not isinstance(params, Mapping)
        or not _REQUIRED_PARAM_KEYS <= set(params)
        or set(params) - _REQUIRED_PARAM_KEYS - _OPTIONAL_PARAM_KEYS
    ):
        raise ValueError("role context parameters have unknown or missing fields")
    maximum = params["max_candidates"]
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        raise ValueError("role context candidate maximum must be positive")
    from .slurp_intent_hypotheses import (
        BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    )
    policies = {
        BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    }
    projection = params["projection_policy"]
    if not isinstance(projection, str) or projection not in policies or (
        maximum > 3 and projection != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
    ):
        raise ValueError("role context candidate projection is invalid")
    from .role_context import validate_role_context_draft_schema

    validate_role_context_draft_schema(params["draft_response_schema"])
    fallback_candidates = params.get("fallback_candidates", ())
    if (
        not isinstance(fallback_candidates, (list, tuple))
        or len(fallback_candidates) > 2
        or any(not isinstance(item, str) or not item for item in fallback_candidates)
        or len(set(fallback_candidates)) != len(fallback_candidates)
    ):
        raise ValueError(
            "role context fallback_candidates must be at most two unique non-empty strings"
        )
    if "fallback_distinction" in params:
        if not fallback_candidates:
            raise ValueError(
                "role context fallback_distinction requires a non-empty fallback_candidates"
            )
        text = params["fallback_distinction"]
        if not isinstance(text, str) or not text.strip() or len(text) > 128:
            raise ValueError("role context fallback_distinction is invalid")
    return params


def validate_role_context_config(document):
    """Return immutable canonical config text, with no source or model I/O."""
    from . import controllers  # noqa: F401 -- load canonical shared registrations

    if not isinstance(document, Mapping) or set(document) != {"policy_id", "params"}:
        raise ValueError("role context config requires policy_id and params")
    if not isinstance(document["policy_id"], str):
        raise ValueError("role context policy ID must be text")
    try:
        factory = ROLE_CONTEXT_COMPILERS.resolve(document["policy_id"])
    except CoreError as error:
        raise ValueError(str(error)) from error
    validator = getattr(factory, "validate_params", None)
    if not callable(factory) or not callable(validator):
        raise ValueError("role context compiler requires a registered parameter validator")
    validator(document["params"])
    return _bytes(document).decode()


@dataclass(frozen=True)
class RoleContextBinding:
    compiler: object
    draft_schema_json: str
    source_format_sha256: str
    config_sha256: str

    @property
    def draft_response_schema(self):
        return json.loads(self.draft_schema_json)


def build_slurp_role_context_compiler(*, perception_response_format, params):
    """Derive legal candidate IDs from the actual bound Perception response schema."""
    from .role_context import SlurpRoleContextCompiler

    params = _params(params)
    try:
        candidates = perception_response_format["json_schema"]["schema"]["properties"]["candidates"]
        legal = candidates["items"]["properties"]["intent_id"]["enum"]
    except (KeyError, TypeError):
        raise ValueError("role context requires the actual typed Perception schema") from None
    if (
        not isinstance(legal, list) or not legal
        or any(not isinstance(x, str) or not x for x in legal)
        or len(legal) != len(set(legal))
        or candidates.get("maxItems") != params["max_candidates"]
    ):
        raise ValueError("role context candidate inventory or maximum differs")
    from .slurp_intent_hypotheses import DEFAULT_FALLBACK_DISTINCTION

    return SlurpRoleContextCompiler(
        legal_intent_ids=tuple(legal), max_candidates=params["max_candidates"],
        projection_policy=params["projection_policy"],
        fallback_candidates=tuple(params.get("fallback_candidates", ())),
        fallback_distinction=params.get(
            "fallback_distinction", DEFAULT_FALLBACK_DISTINCTION
        ),
    )


build_slurp_role_context_compiler.validate_params = _params
build_slurp_role_context_compiler.perception_response_format_id = "slurp-intent-hypotheses-v1"


def role_context_source_format_id(config_json):
    spec = json.loads(config_json)
    factory = ROLE_CONTEXT_COMPILERS.resolve(spec["policy_id"])
    required = getattr(factory, "perception_response_format_id", None)
    if not isinstance(required, str) or not required:
        raise ValueError("role context compiler requires a source response format")
    return required


def build_role_context_binding(config_json, perception_response_format):
    spec = json.loads(config_json)
    if validate_role_context_config(spec) != config_json:
        raise ValueError("role context config is not its canonical bound representation")
    factory = ROLE_CONTEXT_COMPILERS.resolve(spec["policy_id"])
    compiler = factory(
        perception_response_format=perception_response_format, params=spec["params"],
    )
    return RoleContextBinding(
        compiler=compiler, draft_schema_json=_bytes(spec["params"]["draft_response_schema"]).decode(),
        source_format_sha256=hashlib.sha256(_bytes(perception_response_format)).hexdigest(),
        config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),
    )
