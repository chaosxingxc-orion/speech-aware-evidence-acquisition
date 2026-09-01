"""Training-free signed-supply reward memory for the Audio2Tool carrier.

This module contains the model-free controller and its retrospective grouped
cross-fit evaluator.  Runtime state is derived only from the original direct
tool-call response and the deployment registry.  Gold is represented only by
the two post-hoc action rewards carried by :class:`SignedSupplyOutcome`; no
reward field participates in :func:`extract_runtime_state` or a state key.

The experiment contract is frozen in
``configs/experiment/a2t-training-free-signed-supply-memory-v1.json``.  A
positive retrospective screen can propose, but never launch, a separately
registered prospective experiment.
"""

from __future__ import annotations

import ast
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from ..rails.probes.a2t_pop_flight import (
    render_b1_tool_schemas as POP_SUPPLY_RENDERER,
)
from ..rails.probes.a2t_s2b_flight import (
    render_b1_tool_schemas as HEADROOM_SUPPLY_RENDERER,
)
from ..reproduction.toolcall_scoring import parse_tool_calls_text
from .bootstrap import BootstrapResult, paired_cluster_bootstrap

POLICY_SCHEMA = "saea-a2t-training-free-signed-supply-memory-policy-v1"
CANDIDATE_IDS: tuple[str, ...] = ("coarse-v1", "detailed-v1")
STOP_DIRECT = "STOP_DIRECT"
SUPPLY_STRIPPED_REGISTRY = "SUPPLY_STRIPPED_REGISTRY"
Action = Literal["STOP_DIRECT", "SUPPLY_STRIPPED_REGISTRY"]

MIN_CELL_SUPPORT = 5
MIN_CELL_SAVES = 2
MAX_CELL_HARMS = 0

MIN_SAVED = 4
MAX_HARMED = 3
MIN_HARM_AVOIDANCE = 0.90
MIN_SAVE_RETENTION = 0.50
MIN_NET_GAIN = 3
MIN_POSITIVE_FOLDS = 3
MAX_DOMINANT_STATE_SHARE = 0.95


class SupplyMemoryError(RuntimeError):
    """A frozen controller, surface, or policy artifact is malformed."""


def parse_signature_parameters(signature: str) -> tuple[str, ...] | None:
    """Return declared Python-style parameter names, or ``None`` on doubt.

    Audio2Tool registry signatures are display strings.  Parsing them through
    Python's grammar avoids a comma-splitting heuristic that would misread
    annotations or default expressions.  Variable positional/keyword
    arguments are rejected because JSON call keys cannot be mapped to them
    without inventing a convention.
    """

    if not isinstance(signature, str) or not signature.strip():
        return None
    try:
        tree = ast.parse(f"def {signature.strip()}:\n    pass\n")
    except (SyntaxError, ValueError, TypeError):
        return None
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return None
    arguments = tree.body[0].args
    if arguments.vararg is not None or arguments.kwarg is not None:
        return None
    names = [
        item.arg
        for item in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
    ]
    if len(names) != len(set(names)):
        return None
    return tuple(names)


def _count_bucket(value: int) -> str:
    if value <= 0:
        return "zero"
    if value == 1:
        return "one"
    if value == 2:
        return "two"
    return "three-plus"


def _aggregate_bucket(values: Sequence[str], *, empty: str) -> str:
    if not values:
        return empty
    distinct = set(values)
    return values[0] if len(distinct) == 1 else "mixed"


@dataclass(frozen=True)
class RuntimeState:
    parse_class: str
    registry_resolution: str
    declared_key_relation: str
    schema_arity_bucket: str
    provided_key_bucket: str

    def key(self, candidate_id: str) -> tuple[str, ...]:
        coarse = (
            self.parse_class,
            self.registry_resolution,
            self.declared_key_relation,
        )
        if candidate_id == "coarse-v1":
            return coarse
        if candidate_id == "detailed-v1":
            return coarse + (self.schema_arity_bucket, self.provided_key_bucket)
        raise SupplyMemoryError(f"unknown candidate id {candidate_id!r}")


def extract_runtime_state(
    response_text: str, registry_rows: Sequence[Mapping[str, str]]
) -> RuntimeState:
    """Extract the frozen gold-free structural state from one direct output."""

    registry: dict[str, tuple[str, ...] | None] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not isinstance(name, str) or not name:
            raise SupplyMemoryError("registry row is missing a non-empty tool_name")
        if name in registry:
            raise SupplyMemoryError(f"registry has duplicate tool_name {name!r}")
        registry[name] = parse_signature_parameters(row.get("signature", ""))

    calls, parsed = parse_tool_calls_text(response_text)
    if not parsed:
        return RuntimeState("invalid", "no-call", "no-call", "unresolved", "zero")
    if not calls:
        return RuntimeState("empty", "no-call", "no-call", "unresolved", "zero")

    parse_class = "single" if len(calls) == 1 else "multiple"
    known = [call.name in registry for call in calls]
    if all(known):
        registry_resolution = "all-known"
    elif any(known):
        registry_resolution = "some-unknown"
    else:
        registry_resolution = "all-unknown"

    relations: list[str] = []
    arities: list[str] = []
    provided_counts: list[str] = []
    for call in calls:
        provided = set(call.arguments)
        provided_counts.append(_count_bucket(len(provided)))
        if call.name not in registry:
            relations.append("unresolved")
            continue
        declared_tuple = registry[call.name]
        if declared_tuple is None:
            relations.append("unresolved")
            continue
        declared = set(declared_tuple)
        arities.append(_count_bucket(len(declared)))
        if provided == declared:
            relations.append("exact")
        elif provided < declared:
            relations.append("subset")
        elif provided > declared:
            relations.append("superset")
        else:
            relations.append("mixed")

    return RuntimeState(
        parse_class=parse_class,
        registry_resolution=registry_resolution,
        declared_key_relation=_aggregate_bucket(relations, empty="unresolved"),
        schema_arity_bucket=_aggregate_bucket(arities, empty="unresolved"),
        provided_key_bucket=_aggregate_bucket(provided_counts, empty="zero"),
    )


@dataclass(frozen=True)
class SignedSupplyOutcome:
    sample_id: str
    group_id: str
    state: RuntimeState
    stop_exact: int
    supply_exact: int
    stop_tool_accuracy: float
    supply_tool_accuracy: float
    stop_slot_f1: float
    supply_slot_f1: float

    def __post_init__(self) -> None:
        if not self.sample_id or not self.group_id:
            raise ValueError("sample_id and group_id must be non-empty")
        if self.stop_exact not in (0, 1) or self.supply_exact not in (0, 1):
            raise ValueError("exact-match rewards must be binary")

    @property
    def delta(self) -> int:
        return self.supply_exact - self.stop_exact


@dataclass(frozen=True)
class MemoryDecision:
    action: Action
    support: int
    saves: int
    harms: int
    reason: str


def decide(
    state: RuntimeState,
    memory: Sequence[SignedSupplyOutcome],
    *,
    candidate_id: str,
    minimum_support: int = MIN_CELL_SUPPORT,
    minimum_saves: int = MIN_CELL_SAVES,
    maximum_harms: int = MAX_CELL_HARMS,
) -> MemoryDecision:
    """Choose supply only for a supported, positive, zero-harm memory cell."""

    key = state.key(candidate_id)
    cell = tuple(item for item in memory if item.state.key(candidate_id) == key)
    support = len(cell)
    saves = sum(item.delta > 0 for item in cell)
    harms = sum(item.delta < 0 for item in cell)
    if support < minimum_support:
        return MemoryDecision(STOP_DIRECT, support, saves, harms, "insufficient-support")
    if saves < minimum_saves:
        return MemoryDecision(STOP_DIRECT, support, saves, harms, "insufficient-saves")
    if harms > maximum_harms:
        return MemoryDecision(STOP_DIRECT, support, saves, harms, "observed-harm")
    return MemoryDecision(
        SUPPLY_STRIPPED_REGISTRY,
        support,
        saves,
        harms,
        "supported-positive-zero-harm-cell",
    )


def _stable_rank(seed: int, group_id: str) -> str:
    return hashlib.sha256(f"{seed}\0{group_id}".encode("utf-8")).hexdigest()


def assign_folds(
    outcomes: Sequence[SignedSupplyOutcome], *, seed: int, n_folds: int = 5
) -> tuple[tuple[SignedSupplyOutcome, ...], ...]:
    """Assign complete query groups to deterministic, sample-balanced folds."""

    if n_folds < 2:
        raise SupplyMemoryError("cross-fitting requires at least two folds")
    by_group: dict[str, list[SignedSupplyOutcome]] = {}
    seen_samples: set[str] = set()
    for item in outcomes:
        if item.sample_id in seen_samples:
            raise SupplyMemoryError(f"duplicate sample_id {item.sample_id!r}")
        seen_samples.add(item.sample_id)
        by_group.setdefault(item.group_id, []).append(item)
    if len(by_group) < n_folds:
        raise SupplyMemoryError("fewer independent query groups than folds")

    ordered_groups = sorted(
        by_group.items(), key=lambda pair: (-len(pair[1]), _stable_rank(seed, pair[0]), pair[0])
    )
    folds: list[list[SignedSupplyOutcome]] = [[] for _ in range(n_folds)]
    for _group_id, group_items in ordered_groups:
        destination = min(range(n_folds), key=lambda index: (len(folds[index]), index))
        folds[destination].extend(group_items)
    return tuple(
        tuple(sorted(fold, key=lambda item: item.sample_id)) for fold in folds
    )


@dataclass(frozen=True)
class DecisionOutcome:
    outcome: SignedSupplyOutcome
    action: Action
    selected_exact: int

    @property
    def net_gain(self) -> int:
        return self.selected_exact - self.outcome.stop_exact


def grouped_net_gain_bootstrap(
    decisions: Sequence[DecisionOutcome],
    *,
    seed: int,
    n_replicates: int = 10_000,
    ci_level: float = 0.90,
) -> BootstrapResult:
    """Bootstrap mean exact-match gain by complete ``query_idx`` groups."""

    by_group: dict[str, tuple[int, ...]] = {}
    mutable: dict[str, list[int]] = {}
    for decision in decisions:
        mutable.setdefault(decision.outcome.group_id, []).append(decision.net_gain)
    by_group = {key: tuple(values) for key, values in mutable.items()}
    group_ids = tuple(sorted(by_group))

    def statistic(groups: Sequence[str]) -> float:
        values = [value for group in groups for value in by_group[group]]
        return sum(values) / len(values)

    return paired_cluster_bootstrap(
        sample_ids=group_ids,
        statistic=statistic,
        n_replicates=n_replicates,
        seed=seed,
        ci_level=ci_level,
    )


@dataclass(frozen=True)
class CandidateMetrics:
    n_samples: int
    supplied: int
    stopped: int
    saved: int
    harmed: int
    net_gain: int
    second_contact_rate: float
    fold_net_gains: tuple[int, ...]
    ci_low: float
    ci_high: float
    sigma_hat: float


@dataclass(frozen=True)
class CandidateReport:
    candidate_id: str
    state_class_counts: Mapping[str, int]
    metrics: CandidateMetrics
    gates: Mapping[str, bool]
    promotion_passed: bool
    decisions: tuple[DecisionOutcome, ...]


@dataclass(frozen=True)
class ScreenResult:
    reports: Mapping[str, CandidateReport]
    selected_candidate: str | None
    promotion_passed: bool


def _state_label(state: RuntimeState, candidate_id: str) -> str:
    return json.dumps(state.key(candidate_id), separators=(",", ":"))


def _evaluate_candidate(
    outcomes: Sequence[SignedSupplyOutcome],
    *,
    candidate_id: str,
    seed: int,
    n_folds: int,
    n_replicates: int,
) -> CandidateReport:
    folds = assign_folds(outcomes, seed=seed, n_folds=n_folds)
    decisions: list[DecisionOutcome] = []
    fold_net_gains: list[int] = []
    for fold_index, evaluation in enumerate(folds):
        memory = tuple(
            item for index, fold in enumerate(folds) if index != fold_index for item in fold
        )
        fold_decisions: list[DecisionOutcome] = []
        for item in evaluation:
            choice = decide(item.state, memory, candidate_id=candidate_id)
            selected = item.supply_exact if choice.action == SUPPLY_STRIPPED_REGISTRY else item.stop_exact
            fold_decisions.append(DecisionOutcome(item, choice.action, selected))
        fold_net_gains.append(sum(item.net_gain for item in fold_decisions))
        decisions.extend(fold_decisions)
    ordered_decisions = tuple(sorted(decisions, key=lambda item: item.outcome.sample_id))

    supplied = sum(item.action == SUPPLY_STRIPPED_REGISTRY for item in ordered_decisions)
    stopped = len(ordered_decisions) - supplied
    saved = sum(
        item.action == SUPPLY_STRIPPED_REGISTRY and item.outcome.delta > 0
        for item in ordered_decisions
    )
    harmed = sum(
        item.action == SUPPLY_STRIPPED_REGISTRY and item.outcome.delta < 0
        for item in ordered_decisions
    )
    net_gain = sum(item.net_gain for item in ordered_decisions)
    bootstrap = grouped_net_gain_bootstrap(
        ordered_decisions, seed=seed, n_replicates=n_replicates
    )
    class_counts = Counter(_state_label(item.state, candidate_id) for item in outcomes)
    dominant_share = max(class_counts.values(), default=0) / len(outcomes)
    always_supply_saves = sum(item.delta > 0 for item in outcomes)
    always_supply_harms = sum(item.delta < 0 for item in outcomes)
    harm_avoidance = (
        (always_supply_harms - harmed) / always_supply_harms
        if always_supply_harms
        else 1.0
    )
    save_retention = saved / always_supply_saves if always_supply_saves else 0.0
    gates = {
        "state_liveness": len(class_counts) >= 2
        and dominant_share <= MAX_DOMINANT_STATE_SHARE,
        "both_actions": supplied > 0 and stopped > 0,
        "saved_minimum": saved >= MIN_SAVED,
        "harm_maximum": harmed <= MAX_HARMED,
        "harm_avoidance": harm_avoidance >= MIN_HARM_AVOIDANCE,
        "save_retention": save_retention >= MIN_SAVE_RETENTION,
        "net_gain": net_gain >= MIN_NET_GAIN,
        "positive_ci90_lower": bootstrap.ci_low > 0.0,
        "every_fold_nonnegative": all(value >= 0 for value in fold_net_gains),
        "positive_fold_count": sum(value > 0 for value in fold_net_gains)
        >= MIN_POSITIVE_FOLDS,
    }
    metrics = CandidateMetrics(
        n_samples=len(outcomes),
        supplied=supplied,
        stopped=stopped,
        saved=saved,
        harmed=harmed,
        net_gain=net_gain,
        second_contact_rate=supplied / len(outcomes),
        fold_net_gains=tuple(fold_net_gains),
        ci_low=bootstrap.ci_low,
        ci_high=bootstrap.ci_high,
        sigma_hat=bootstrap.sigma_hat,
    )
    return CandidateReport(
        candidate_id=candidate_id,
        state_class_counts=dict(sorted(class_counts.items())),
        metrics=metrics,
        gates=gates,
        promotion_passed=all(gates.values()),
        decisions=ordered_decisions,
    )


def screen_candidates(
    outcomes: Sequence[SignedSupplyOutcome],
    *,
    seed: int = 20260901,
    n_folds: int = 5,
    n_replicates: int = 10_000,
) -> ScreenResult:
    """Cross-fit both frozen candidates and apply the conjunctive gates."""

    ordered = tuple(sorted(outcomes, key=lambda item: item.sample_id))
    if not ordered:
        raise SupplyMemoryError("candidate screen requires at least one outcome")
    reports = {
        candidate_id: _evaluate_candidate(
            ordered,
            candidate_id=candidate_id,
            seed=seed,
            n_folds=n_folds,
            n_replicates=n_replicates,
        )
        for candidate_id in CANDIDATE_IDS
    }
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


def assert_supply_renderer_identity() -> None:
    """Prove both logged supply sources use the same renderer object."""

    if POP_SUPPLY_RENDERER is not HEADROOM_SUPPLY_RENDERER:
        raise SupplyMemoryError(
            "population and headroom supply renderer identities differ; refusing replay"
        )


def _canonical_json(document: Mapping[str, object]) -> bytes:
    return json.dumps(
        document, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


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
        raise SupplyMemoryError(
            f"policy self hash mismatch: recorded={expected!r}, recomputed={actual!r}"
        )


def assert_policy_admits_prospective(document: Mapping[str, object]) -> None:
    """Fail closed before a later prospective launcher reads a new sample."""

    if document.get("schema") != POLICY_SCHEMA:
        raise SupplyMemoryError("policy schema mismatch")
    if not document.get("promotion_passed"):
        raise SupplyMemoryError("retrospective promotion screen did not pass")
    selected = document.get("selected")
    if not isinstance(selected, Mapping):
        raise SupplyMemoryError("policy lacks selected candidate details")
    metrics = selected.get("metrics")
    if not isinstance(metrics, Mapping):
        raise SupplyMemoryError("policy lacks selected metrics")
    supplied = int(metrics.get("supplied", 0))
    stopped = int(metrics.get("stopped", 0))
    if supplied <= 0 or stopped <= 0:
        raise SupplyMemoryError("selected policy does not exercise both actions")
    counts = selected.get("state_class_counts")
    if not isinstance(counts, Mapping) or len(counts) < 2:
        raise SupplyMemoryError("selected policy state is not live")


__all__ = [
    "CANDIDATE_IDS",
    "HEADROOM_SUPPLY_RENDERER",
    "POLICY_SCHEMA",
    "POP_SUPPLY_RENDERER",
    "STOP_DIRECT",
    "SUPPLY_STRIPPED_REGISTRY",
    "CandidateMetrics",
    "CandidateReport",
    "DecisionOutcome",
    "MemoryDecision",
    "RuntimeState",
    "ScreenResult",
    "SignedSupplyOutcome",
    "SupplyMemoryError",
    "assert_policy_admits_prospective",
    "assert_self_hash",
    "assert_supply_renderer_identity",
    "assign_folds",
    "decide",
    "extract_runtime_state",
    "grouped_net_gain_bootstrap",
    "parse_signature_parameters",
    "screen_candidates",
    "with_self_hash",
]
