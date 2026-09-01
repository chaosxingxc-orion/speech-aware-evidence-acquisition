"""Training-free schema-risk memory over the Audio2Tool 104 action surface.

The state is derived only from two deployment-visible direct responses and
the frozen tool registry.  Gold remains inside the predecessor's scorer-side
``ItemScore`` objects and never enters schema parsing or state extraction.
The module reuses the predecessor's exact folds, cross-fit evaluator, reward
thresholds, bootstrap, and promotion gates.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from typing import Literal, Mapping, Sequence

from ..reproduction.toolcall_scoring import ItemScore, ToolCall, parse_tool_calls_text
from . import training_free_a2t_self_consistency as selfcon

POLICY_SCHEMA = "saea-a2t-training-free-schema-risk-memory-policy-v1"
EXPERIMENT_ID = "SAEA-A2T-MF-TFRL-SCHEMA-RISK-MEMORY-V1"
COARSE_CANDIDATE = "schema-risk-coarse-v1"
DETAILED_CANDIDATE = "schema-risk-detailed-v1"
CANDIDATE_IDS = (COARSE_CANDIDATE, DETAILED_CANDIDATE)

_INTERNAL_CANDIDATES = {
    COARSE_CANDIDATE: selfcon.COARSE_CANDIDATE,
    DETAILED_CANDIDATE: selfcon.HIERARCHICAL_CANDIDATE,
}
_SIGNATURE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$")
_PARAMETER = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*"
    r"([A-Za-z_][A-Za-z0-9_]*(?:<[A-Za-z_][A-Za-z0-9_]*>)?)(\?)?$"
)
_CONSTRAINT_CLAUSE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\[([^\]]*)\]"
)
_NUMBER = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
_RANGE = re.compile(rf"^\s*({_NUMBER})\s*-\s*({_NUMBER})\s*$")


class SchemaRiskError(RuntimeError):
    """A registry schema, signed-return surface, or artifact is invalid."""


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    type_name: str
    optional: bool


@dataclass(frozen=True)
class PseudoSignature:
    tool_name: str
    parameters: tuple[ParameterSpec, ...]


@dataclass(frozen=True)
class ConstraintSpec:
    kind: Literal["enum", "numeric-range", "uncheckable"]
    enum_values: tuple[str, ...] = ()
    numeric_range: tuple[float, float] | None = None


@dataclass(frozen=True)
class ToolSchema:
    signature: PseudoSignature | None
    constraints: Mapping[str, ConstraintSpec]


def parse_pseudo_signature(value: str) -> PseudoSignature | None:
    """Parse the registry's bounded pseudo-signature grammar fail-closed."""

    if not isinstance(value, str):
        return None
    match = _SIGNATURE.fullmatch(value.strip())
    if match is None:
        return None
    tool_name, body = match.groups()
    if not body.strip():
        return PseudoSignature(tool_name, ())
    parameters: list[ParameterSpec] = []
    seen: set[str] = set()
    for raw in body.split(","):
        parsed = _PARAMETER.fullmatch(raw.strip())
        if parsed is None:
            return None
        name, type_name, optional = parsed.groups()
        if name in seen:
            return None
        seen.add(name)
        parameters.append(ParameterSpec(name, type_name, optional == "?"))
    return PseudoSignature(tool_name, tuple(parameters))


def parse_argument_constraints(value: str) -> dict[str, ConstraintSpec]:
    """Parse exact enum and scalar numeric-range constraints.

    A compound body such as the HSB color mini-language stays explicitly
    uncheckable.  Malformed outer syntax returns no constraints rather than
    guessing where clauses begin or end.
    """

    if not isinstance(value, str) or not value.strip():
        return {}
    matches = list(_CONSTRAINT_CLAUSE.finditer(value))
    if not matches:
        return {}
    cursor = 0
    for index, match in enumerate(matches):
        separator = value[cursor : match.start()]
        if separator.strip(" ,"):
            return {}
        cursor = match.end()
        if index + 1 < len(matches) and value[cursor : matches[index + 1].start()].strip(
            " ,"
        ):
            return {}
    if value[cursor:].strip(" ,"):
        return {}

    parsed: dict[str, ConstraintSpec] = {}
    for match in matches:
        name, raw_body = match.groups()
        if name in parsed:
            return {}
        body = raw_body.strip()
        range_match = _RANGE.fullmatch(body)
        if range_match is not None:
            low, high = (float(item) for item in range_match.groups())
            if low <= high:
                parsed[name] = ConstraintSpec(
                    "numeric-range", numeric_range=(low, high)
                )
            else:
                parsed[name] = ConstraintSpec("uncheckable")
        elif ":" in body or not body:
            parsed[name] = ConstraintSpec("uncheckable")
        else:
            choices = tuple(item.strip() for item in body.split(","))
            if any(not item for item in choices):
                parsed[name] = ConstraintSpec("uncheckable")
            else:
                parsed[name] = ConstraintSpec("enum", enum_values=choices)
    return parsed


def _registry_index(
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, ToolSchema]:
    indexed: dict[str, ToolSchema] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not isinstance(name, str) or not name:
            raise SchemaRiskError("registry row lacks a non-empty tool_name")
        if name in indexed:
            raise SchemaRiskError(f"registry has duplicate tool_name {name!r}")
        signature = parse_pseudo_signature(row.get("signature", ""))
        if signature is not None and signature.tool_name != name:
            signature = None
        indexed[name] = ToolSchema(
            signature=signature,
            constraints=parse_argument_constraints(row.get("argument_constraints", "")),
        )
    return indexed


def _canonical_call(call: ToolCall) -> str:
    return json.dumps(
        {"arguments": call.arguments, "name": call.name},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _deduplicate(calls: Sequence[ToolCall]) -> tuple[ToolCall, ...]:
    by_key: dict[str, ToolCall] = {}
    for call in calls:
        by_key.setdefault(_canonical_call(call), call)
    return tuple(by_key[key] for key in sorted(by_key))


def _aggregate(values: Sequence[str], *, empty: str = "unresolved") -> str:
    if not values:
        return empty
    distinct = set(values)
    return values[0] if len(distinct) == 1 else "mixed"


def _type_valid(type_name: str, value: object) -> bool:
    base = type_name.split("<", 1)[0]
    if base == "Boolean":
        return isinstance(value, bool)
    if base == "Int":
        return isinstance(value, int) and not isinstance(value, bool)
    if base == "Float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if base == "List":
        return isinstance(value, list)
    if base == "Map":
        return isinstance(value, Mapping)
    return isinstance(value, str)


def _enum_value(value: object) -> str | None:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _constraint_status(spec: ConstraintSpec, value: object) -> str:
    if spec.kind == "uncheckable":
        return "unresolved"
    if spec.kind == "enum":
        rendered = _enum_value(value)
        return "valid" if rendered in spec.enum_values else "invalid"
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "unresolved"
    assert spec.numeric_range is not None
    low, high = spec.numeric_range
    return "valid" if low <= float(value) <= high else "invalid"


@dataclass(frozen=True)
class ResponseRisk:
    parse_class: str
    registry_resolution: str
    required_key_coverage: str
    unknown_key_status: str
    type_status: str
    constraint_status: str
    violation_count: int
    risk_class: str


def _known_call_risk(
    call: ToolCall, schema: ToolSchema
) -> tuple[str, str, str, str, int, set[str]]:
    signature = schema.signature
    if signature is None:
        return "unresolved", "unresolved", "unresolved", "unresolved", 0, set()
    parameters = {item.name: item for item in signature.parameters}
    required = {item.name for item in signature.parameters if not item.optional}
    provided = set(call.arguments)
    missing = required - provided
    extra = provided - set(parameters)
    required_status = "missing" if missing else "complete"
    unknown_status = "present" if extra else "none"

    type_results: list[str] = []
    constraint_results: list[str] = []
    invalid_types = 0
    invalid_constraints = 0
    for name in sorted(provided & set(parameters)):
        value = call.arguments[name]
        valid_type = _type_valid(parameters[name].type_name, value)
        type_results.append("valid" if valid_type else "invalid")
        invalid_types += not valid_type
        constraint = schema.constraints.get(name)
        if constraint is None:
            continue
        status = _constraint_status(constraint, value) if valid_type else "unresolved"
        constraint_results.append(status)
        invalid_constraints += status == "invalid"
    type_status = _aggregate(type_results)
    constraint_status = _aggregate(constraint_results, empty="unconstrained")
    violation_count = (
        len(missing) + len(extra) + invalid_types + invalid_constraints
    )
    channels: set[str] = set()
    if missing:
        channels.add("missing-required")
    if extra:
        channels.add("extra-key")
    if invalid_types:
        channels.add("type-invalid")
    if invalid_constraints:
        channels.add("constraint-invalid")
    return (
        required_status,
        unknown_status,
        type_status,
        constraint_status,
        violation_count,
        channels,
    )


def extract_response_risk(
    response_text: str, registry_rows: Sequence[Mapping[str, str]]
) -> ResponseRisk:
    """Extract an order- and duplicate-invariant schema-risk summary."""

    registry = _registry_index(registry_rows)
    raw_calls, parsed = parse_tool_calls_text(response_text)
    if not parsed:
        return ResponseRisk(
            "invalid",
            "no-call",
            "unresolved",
            "unresolved",
            "unresolved",
            "unresolved",
            0,
            "invalid-json",
        )
    calls = _deduplicate(raw_calls)
    if not calls:
        return ResponseRisk(
            "empty",
            "no-call",
            "unresolved",
            "unresolved",
            "unresolved",
            "unresolved",
            0,
            "empty",
        )

    known = [call.name in registry for call in calls]
    resolution = "all-known" if all(known) else "some-unknown" if any(known) else "all-unknown"
    required_statuses: list[str] = []
    unknown_statuses: list[str] = []
    type_statuses: list[str] = []
    constraint_statuses: list[str] = []
    violations = 0
    channels: set[str] = set()
    unresolved_schema = False
    for call in calls:
        schema = registry.get(call.name)
        if schema is None:
            unresolved_schema = True
            continue
        required, unknown, types, constraints, count, call_channels = _known_call_risk(
            call, schema
        )
        required_statuses.append(required)
        unknown_statuses.append(unknown)
        type_statuses.append(types)
        constraint_statuses.append(constraints)
        violations += count
        channels.update(call_channels)
        unresolved_schema |= schema.signature is None

    if unresolved_schema or not required_statuses:
        risk_class = "unresolved"
    elif not channels:
        risk_class = "schema-clean"
    elif len(channels) == 1:
        risk_class = next(iter(channels))
    else:
        risk_class = "mixed-risk"
    return ResponseRisk(
        parse_class="single" if len(calls) == 1 else "multiple",
        registry_resolution=resolution,
        required_key_coverage=_aggregate(required_statuses),
        unknown_key_status=_aggregate(unknown_statuses),
        type_status=_aggregate(type_statuses),
        constraint_status=_aggregate(constraint_statuses),
        violation_count=violations,
        risk_class=risk_class,
    )


def _risk_vector(value: ResponseRisk) -> tuple[int, int, int, int] | None:
    if value.risk_class in {"invalid-json", "empty", "unresolved"}:
        return None

    def flagged(status: str, bad: str) -> int:
        return int(status in {bad, "mixed"})

    return (
        flagged(value.required_key_coverage, "missing"),
        flagged(value.unknown_key_status, "present"),
        flagged(value.type_status, "invalid"),
        flagged(value.constraint_status, "invalid"),
    )


def _risk_relation(left: ResponseRisk, right: ResponseRisk) -> str:
    left_vector = _risk_vector(left)
    right_vector = _risk_vector(right)
    if left_vector is None or right_vector is None:
        return "unresolved"
    if left_vector == right_vector:
        return "exact"
    if all(a <= b for a, b in zip(left_vector, right_vector, strict=True)):
        return "m0-lower"
    if all(b <= a for a, b in zip(left_vector, right_vector, strict=True)):
        return "observation-lower"
    return "incomparable"


def _violation_bucket(value: int) -> str:
    if value <= 0:
        return "zero"
    if value == 1:
        return "one"
    if value == 2:
        return "two"
    return "three-plus"


@dataclass(frozen=True)
class SchemaRiskState:
    m0: ResponseRisk
    observation: ResponseRisk
    risk_relation: str

    @property
    def coarse_key(self) -> tuple[str, ...]:
        return self.key(COARSE_CANDIDATE)

    @property
    def detailed_key(self) -> tuple[str, ...]:
        return self.key(DETAILED_CANDIDATE)

    def key(self, candidate_id: str) -> tuple[str, ...]:
        if candidate_id in {COARSE_CANDIDATE, selfcon.COARSE_CANDIDATE}:
            return (self.m0.risk_class, self.risk_relation)
        if candidate_id in {DETAILED_CANDIDATE, selfcon.HIERARCHICAL_CANDIDATE}:
            return (
                self.m0.risk_class,
                self.observation.risk_class,
                self.risk_relation,
                _violation_bucket(self.m0.violation_count),
                _violation_bucket(self.observation.violation_count),
            )
        raise SchemaRiskError(f"unknown candidate_id {candidate_id!r}")


def extract_schema_risk_state(
    m0_response: str,
    observation_response: str,
    registry_rows: Sequence[Mapping[str, str]],
) -> SchemaRiskState:
    """Extract the preregistered paired schema-risk state."""

    m0 = extract_response_risk(m0_response, registry_rows)
    observation = extract_response_risk(observation_response, registry_rows)
    return SchemaRiskState(m0, observation, _risk_relation(m0, observation))


@dataclass(frozen=True)
class SchemaRiskOutcome:
    sample_id: str
    group_id: str
    state: SchemaRiskState
    supply_available: bool
    stop_score: ItemScore
    supply_score: ItemScore

    @property
    def delta(self) -> int:
        return int(self.supply_score.exact_match - self.stop_score.exact_match)

    @property
    def tool_accuracy_delta(self) -> int:
        return int(self.supply_score.tool_accuracy - self.stop_score.tool_accuracy)


def augment_outcomes(
    outcomes: Sequence[selfcon.SelfConsistencyOutcome],
    m0_response_by_id: Mapping[str, str],
    observation_response_by_id: Mapping[str, str],
    registry_rows: Sequence[Mapping[str, str]],
) -> tuple[SchemaRiskOutcome, ...]:
    """Replace only state while preserving the signed action surface."""

    expected_ids = {item.sample_id for item in outcomes}
    if set(m0_response_by_id) != expected_ids or set(observation_response_by_id) != expected_ids:
        raise SchemaRiskError("response ids do not equal predecessor outcome ids")
    return tuple(
        SchemaRiskOutcome(
            sample_id=item.sample_id,
            group_id=item.group_id,
            state=extract_schema_risk_state(
                m0_response_by_id[item.sample_id],
                observation_response_by_id[item.sample_id],
                registry_rows,
            ),
            supply_available=item.supply_available,
            stop_score=item.stop_score,
            supply_score=item.supply_score,
        )
        for item in sorted(outcomes, key=lambda row: row.sample_id)
    )


@dataclass(frozen=True)
class ScreenResult:
    reports: Mapping[str, selfcon.CandidateReport]
    selected_candidate: str | None
    promotion_passed: bool


def screen_candidates(
    outcomes: Sequence[SchemaRiskOutcome],
    *,
    seed: int = selfcon.FOLD_SEED,
    n_folds: int = 5,
    n_replicates: int = 10_000,
) -> ScreenResult:
    """Run the predecessor evaluator unchanged over two new state keys."""

    ordered = tuple(sorted(outcomes, key=lambda item: item.sample_id))
    if not ordered:
        raise SchemaRiskError("schema-risk screen requires outcomes")
    reports: dict[str, selfcon.CandidateReport] = {}
    for external, internal in _INTERNAL_CANDIDATES.items():
        report = selfcon.evaluate_candidate(
            ordered,  # type: ignore[arg-type] - structural outcome protocol is exact
            candidate_id=internal,
            seed=seed,
            n_folds=n_folds,
            n_replicates=n_replicates,
        )
        reports[external] = replace(report, candidate_id=external)
    eligible = [report for report in reports.values() if report.promotion_passed]
    if not eligible:
        return ScreenResult(reports, None, False)
    selected = sorted(
        eligible,
        key=lambda report: (
            -report.metrics.net_gain,
            -report.metrics.saved,
            report.metrics.supplied,
            report.candidate_id,
        ),
    )[0]
    return ScreenResult(reports, selected.candidate_id, True)


def state_return_cells(
    outcomes: Sequence[SchemaRiskOutcome], *, candidate_id: str
) -> dict[str, dict[str, int]]:
    cells: dict[str, dict[str, int]] = {}
    for item in outcomes:
        label = json.dumps(item.state.key(candidate_id), separators=(",", ":"))
        cell = cells.setdefault(
            label,
            {"n": 0, "available": 0, "saves": 0, "harms": 0, "neutral": 0},
        )
        cell["n"] += 1
        if not item.supply_available:
            continue
        cell["available"] += 1
        if item.delta > 0:
            cell["saves"] += 1
        elif item.delta < 0:
            cell["harms"] += 1
        else:
            cell["neutral"] += 1
    return dict(sorted(cells.items()))


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()


def with_self_hash(document: Mapping[str, object]) -> dict[str, object]:
    payload = dict(document)
    payload.pop("self_sha256", None)
    payload["self_sha256"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
    return payload


def assert_self_hash(document: Mapping[str, object]) -> None:
    expected = document.get("self_sha256")
    payload = dict(document)
    payload.pop("self_sha256", None)
    actual = hashlib.sha256(_canonical_json(payload)).hexdigest()
    if expected != actual:
        raise SchemaRiskError(
            f"policy self hash mismatch: recorded={expected!r}, recomputed={actual!r}"
        )


def _decision_hash(report: selfcon.CandidateReport) -> str:
    payload = "\n".join(
        f"{item.outcome.sample_id}\t{item.action}" for item in report.decisions
    ) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def _candidate_payload(
    report: selfcon.CandidateReport, outcomes: Sequence[SchemaRiskOutcome]
) -> dict[str, object]:
    return {
        "candidate_id": report.candidate_id,
        "decision_identity_sha256": _decision_hash(report),
        "gates": dict(report.gates),
        "metrics": asdict(report.metrics),
        "promotion_passed": report.promotion_passed,
        "state_class_counts": dict(report.state_class_counts),
        "full_surface_return_cells": state_return_cells(
            outcomes, candidate_id=report.candidate_id
        ),
    }


def build_policy_artifact(
    outcomes: Sequence[SchemaRiskOutcome],
    screen: ScreenResult,
    *,
    source_hashes: Mapping[str, str],
    offline_attempts: int,
) -> dict[str, object]:
    """Build the self-hashed model-free feasibility artifact."""

    if offline_attempts != 0:
        raise SchemaRiskError("offline guard recorded an outbound attempt")
    if set(source_hashes) != {"m0", "repeat", "supply"} or any(
        len(value) != 64 for value in source_hashes.values()
    ):
        raise SchemaRiskError("source hashes must bind full m0/repeat/supply SHA-256 values")
    reports = {
        key: _candidate_payload(report, outcomes)
        for key, report in sorted(screen.reports.items())
    }
    selected = reports.get(screen.selected_candidate) if screen.selected_candidate else None
    state_identity = hashlib.sha256(
        _canonical_json(
            [
                {
                    "sample_id": item.sample_id,
                    "group_id": item.group_id,
                    "state": asdict(item.state),
                    "supply_available": item.supply_available,
                }
                for item in sorted(outcomes, key=lambda row: row.sample_id)
            ]
        )
    ).hexdigest()
    return with_self_hash(
        {
            "schema": POLICY_SCHEMA,
            "experiment_id": EXPERIMENT_ID,
            "execution_profile": "model-free-check",
            "claim_status": "exposed-cohort retrospective feasibility only",
            "predecessor": {
                "experiment_id": selfcon.EXPERIMENT_ID,
                "state_identity_sha256": "890538474a7fcbc0ab981f54e2168358096be66145f306c9e6f7ba063808b246",
                "decision_identity_sha256": "07afc9c6e51b8b61f5ce8c1cf1c705a2e727e7a82c1f9a556247f252f386c31c",
            },
            "policy": {
                "default_action": selfcon.STOP_M0,
                "minimum_cell_support": selfcon.MIN_CELL_SUPPORT,
                "minimum_cell_saves": selfcon.MIN_CELL_SAVES,
                "maximum_cell_harms": selfcon.MAX_CELL_HARMS,
                "parameter_training": "none",
            },
            "candidate_reports": reports,
            "selected_candidate": screen.selected_candidate,
            "selected": selected,
            "promotion_passed": screen.promotion_passed,
            "state_identity_sha256": state_identity,
            "source_hashes": dict(sorted(source_hashes.items())),
            "offline_guard": {
                "outbound_connection_attempts": offline_attempts,
                "targets": [],
            },
            "next_scale": (
                "separately preregister a fresh approximately-100-sample exposed-discovery support flight"
                if screen.promotion_passed
                else "close schema-risk targeting for the current supply action"
            ),
        }
    )


def assert_policy_admits_support(document: Mapping[str, object]) -> None:
    assert_self_hash(document)
    if document.get("schema") != POLICY_SCHEMA:
        raise SchemaRiskError("policy schema mismatch")
    if document.get("promotion_passed") is not True:
        raise SchemaRiskError("schema-risk promotion screen did not pass")
    selected = document.get("selected")
    if not isinstance(selected, Mapping):
        raise SchemaRiskError("policy lacks a selected candidate")
    metrics = selected.get("metrics")
    if not isinstance(metrics, Mapping):
        raise SchemaRiskError("policy lacks selected metrics")
    if int(metrics.get("supplied", 0)) <= 0 or int(metrics.get("stopped", 0)) <= 0:
        raise SchemaRiskError("selected policy does not exercise both actions")
    counts = selected.get("state_class_counts")
    if not isinstance(counts, Mapping) or len(counts) < 2:
        raise SchemaRiskError("selected schema-risk state is not live")


__all__ = [
    "CANDIDATE_IDS",
    "COARSE_CANDIDATE",
    "DETAILED_CANDIDATE",
    "EXPERIMENT_ID",
    "POLICY_SCHEMA",
    "ConstraintSpec",
    "ParameterSpec",
    "PseudoSignature",
    "ResponseRisk",
    "SchemaRiskError",
    "SchemaRiskOutcome",
    "SchemaRiskState",
    "ScreenResult",
    "assert_policy_admits_support",
    "assert_self_hash",
    "augment_outcomes",
    "build_policy_artifact",
    "extract_response_risk",
    "extract_schema_risk_state",
    "parse_argument_constraints",
    "parse_pseudo_signature",
    "screen_candidates",
    "state_return_cells",
    "with_self_hash",
]
