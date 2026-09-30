"""The policy-space document (design spec task 4): the closed knob list of
``docs/superpowers/specs/2026-09-29-sealed-credit-inner-loop-run-1-design.md``
section 2c, one JSON record per knob, each value naming its estimator and its
conversion source.

Validation:

* a knob whose ``route`` is one of ``rails.supply_variants.SUPPLY_VARIANT_KNOB_TAILS``
  (``phase_supply`` / ``candidate_supply``) must carry a ``tail`` admitted under that
  route -- the SAME closed set the runtime itself enforces on a supply-variant arm,
  imported, not copied;
* every other knob (the phase-2 / relisten / review-loop / delivery / commit-rule
  knobs, none of which are a ``knowledge_stores`` selection) validates structurally
  only, and says so (``"path_validated": false``);
* every value names an ``estimator`` (:data:`ESTIMATORS`) and a ``conversion_source``
  whose ``type`` is one of :data:`SOURCE_TYPES`; a ``"pool"``/``"credit_table_*"``
  source must name a pool label the pool manifest actually declares as ``tuning``
  (refused otherwise -- "non-tuning-source" refusal) or the row_states.py wrote in
  the manifest passed to :func:`validate_policy_space`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ESTIMATORS = ("conversion_estimate", "exact_offline", "excluded")
SOURCE_TYPES = (
    "pool_pair_delta", "credit_table_perception_rank", "credit_table_block_position",
    "credit_table_reviewer_toggle", "credit_table_normaliser_toggle", "credit_table_relisten_reach",
    "cited", "unobserved", "excluded",
)
REQUIRED_KNOB_KEYS = frozenset({"id", "node", "estimator", "flown_value", "values"})
OPTIONAL_KNOB_KEYS = frozenset({"route", "tail", "note", "excluded_reason"})
REQUIRED_VALUE_KEYS = frozenset({"value", "conversion_source"})
# Run 3: an optional value-level ``status`` records the coordinator's disposition of a line.
# ``open`` (the default when absent) may be nominated; ``admitted`` (already dev-admitted, kept
# so compositions can build on it) and ``closed`` (a closed line, kept as an observation) are
# ranked and composed but never nominated. ``status_note`` states the ruling.
VALUE_STATUSES = ("open", "admitted", "closed")


class PolicySpaceError(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise PolicySpaceError(message)


def load_policy_space(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PolicySpaceError(f"cannot read policy space {path}: {error}") from error
    if not isinstance(document, Mapping) or document.get("schema") != "saea-sealed-credit-policy-space-v1":
        _fail(f"{path}: must be a JSON object with schema 'saea-sealed-credit-policy-space-v1'")
    knobs = document.get("knobs")
    if not isinstance(knobs, list) or not knobs:
        _fail(f"{path}: knobs must be a non-empty list")
    seen_ids = set()
    for knob in knobs:
        if not isinstance(knob, Mapping):
            _fail(f"{path}: every knob must be an object")
        missing = sorted(REQUIRED_KNOB_KEYS - set(knob))
        if missing:
            _fail(f"{path}: knob {knob.get('id')!r} is missing key(s) {missing}")
        unknown = sorted(set(knob) - REQUIRED_KNOB_KEYS - OPTIONAL_KNOB_KEYS)
        if unknown:
            _fail(f"{path}: knob {knob['id']!r} carries unknown key(s) {unknown}")
        if knob["id"] in seen_ids:
            _fail(f"{path}: duplicate knob id {knob['id']!r}")
        seen_ids.add(knob["id"])
        if knob["estimator"] not in ESTIMATORS:
            _fail(f"{path}: knob {knob['id']!r}: estimator {knob['estimator']!r} not in {ESTIMATORS}")
        if not isinstance(knob["values"], list):
            _fail(f"{path}: knob {knob['id']!r}: values must be a list")
        if knob["estimator"] == "excluded":
            if knob["values"]:
                _fail(f"{path}: knob {knob['id']!r}: an excluded knob carries no candidate values")
            if not knob.get("excluded_reason"):
                _fail(f"{path}: knob {knob['id']!r}: an excluded knob must state excluded_reason")
            continue
        for value in knob["values"]:
            if not isinstance(value, Mapping):
                _fail(f"{path}: knob {knob['id']!r}: every value entry must be an object")
            vmissing = sorted(REQUIRED_VALUE_KEYS - set(value))
            if vmissing:
                _fail(f"{path}: knob {knob['id']!r}: value entry missing key(s) {vmissing}")
            if "status" in value and value["status"] not in VALUE_STATUSES:
                _fail(
                    f"{path}: knob {knob['id']!r} value {value.get('value')!r}: "
                    f"status must be one of {VALUE_STATUSES}"
                )
            source = value["conversion_source"]
            if not isinstance(source, Mapping) or source.get("type") not in SOURCE_TYPES:
                _fail(
                    f"{path}: knob {knob['id']!r} value {value.get('value')!r}: "
                    f"conversion_source.type must be one of {SOURCE_TYPES}"
                )
    return dict(document)


def validate_supply_variant_routes(document: Mapping[str, Any]) -> list[str]:
    """Every knob whose ``route`` is a ``SUPPLY_VARIANT_KNOB_TAILS`` key must carry
    an admitted ``tail``. Returns the ids validated this way (for a report line);
    raises :class:`PolicySpaceError` on an inadmissible tail."""

    from speech_aware_evidence_acquisition.rails.supply_variants import SUPPLY_VARIANT_KNOB_TAILS

    validated = []
    for knob in document["knobs"]:
        route = knob.get("route")
        if route not in SUPPLY_VARIANT_KNOB_TAILS:
            continue
        tail = knob.get("tail")
        if not isinstance(tail, list) or tuple(tail) not in SUPPLY_VARIANT_KNOB_TAILS[route]:
            admitted = [".".join(t) for t in SUPPLY_VARIANT_KNOB_TAILS[route]]
            _fail(
                f"knob {knob['id']!r}: route {route!r} admits only tail(s) {admitted}, got {tail!r}"
            )
        validated.append(knob["id"])
    return sorted(validated)


def validate_tuning_sources(document: Mapping[str, Any], tuning_pool_labels: set[str]) -> None:
    """Every ``pool_pair_delta`` / ``credit_table_*`` conversion source must name a
    pool label in ``tuning_pool_labels`` (the manifest's own ``use: tuning`` pools) --
    the "non-tuning-source" refusal."""

    for knob in document["knobs"]:
        for value in knob.get("values", []):
            source = value["conversion_source"]
            names = (
                source.get("pools")
                or ([source["pool"]] if "pool" in source else [])
                or ([source["primary_pool"]] if "primary_pool" in source else [])
            )
            for label in names:
                if label not in tuning_pool_labels:
                    _fail(
                        f"knob {knob['id']!r} value {value['value']!r}: conversion_source names pool "
                        f"{label!r}, which is not a tuning pool in this manifest"
                    )


def knob_by_id(document: Mapping[str, Any], knob_id: str) -> dict[str, Any]:
    for knob in document["knobs"]:
        if knob["id"] == knob_id:
            return dict(knob)
    raise PolicySpaceError(f"no knob {knob_id!r} in this policy space")


__all__ = [
    "ESTIMATORS", "SOURCE_TYPES", "VALUE_STATUSES", "PolicySpaceError",
    "load_policy_space", "validate_supply_variant_routes", "validate_tuning_sources", "knob_by_id",
]
