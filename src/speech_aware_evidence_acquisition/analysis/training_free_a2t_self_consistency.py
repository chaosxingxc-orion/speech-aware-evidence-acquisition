"""Training-free Audio2Tool routing from a prospective direct re-observation.

The module is intentionally model-free.  It defines the deployment-visible
state, deterministic values-stripped union renderer, grouped cross-fit reward
memory, and promotion artifact used by the registered 104-sample probe.  Gold
enters only through already-computed scorer-side ``ItemScore`` values supplied
to :class:`SelfConsistencyOutcome`; it is never accepted by the state or
renderer functions.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Literal, Mapping, Sequence

from ..data.audio2tool import render_registry_row
from ..reproduction.toolcall_scoring import (
    ItemScore,
    ToolCall,
    parse_tool_calls_text,
    score_item,
)
from .bootstrap import paired_cluster_bootstrap

STOP_M0 = "STOP_M0"
SUPPLY_UNION_STRIPPED = "SUPPLY_UNION_STRIPPED"
Action = Literal["STOP_M0", "SUPPLY_UNION_STRIPPED"]

COARSE_CANDIDATE = "coarse-v1"
HIERARCHICAL_CANDIDATE = "hierarchical-v1"
CANDIDATE_IDS = (COARSE_CANDIDATE, HIERARCHICAL_CANDIDATE)

POLICY_SCHEMA = "saea-a2t-training-free-self-consistency-policy-v1"
EXPERIMENT_ID = "SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1"
FOLD_SEED = 20260901
MIN_CELL_SUPPORT = 4
MIN_CELL_SAVES = 2
MAX_CELL_HARMS = 0
MIN_SUPPLIED = 5
MAX_SUPPLIED = 52
MIN_SAVED = 3
MAX_HARMED = 1
MIN_NET_GAIN = 2
MIN_POSITIVE_FOLDS = 2
MIN_HARM_AVOIDANCE = 0.80
MIN_SAVE_RETENTION = 0.50
MIN_NON_DOMINANT_STATE_SAMPLES = 10


class SelfConsistencyError(RuntimeError):
    """The registered state, reward surface, or artifact is invalid."""


def _normalise_value(value: object) -> object:
    """Mirror the frozen scorer's value equivalence for state comparison."""

    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("num", float(value))
    if isinstance(value, str):
        return ("str", value.strip().casefold())
    if isinstance(value, Mapping):
        return (
            "map",
            tuple(
                sorted(
                    (str(key), _normalise_value(item))
                    for key, item in value.items()
                )
            ),
        )
    if isinstance(value, (list, tuple)):
        return ("seq", tuple(_normalise_value(item) for item in value))
    if value is None:
        return ("null",)
    return ("other", repr(value))


def _canonical_call(call: ToolCall) -> object:
    return (call.name, _normalise_value(call.arguments))


def _deduplicate(calls: Sequence[ToolCall]) -> tuple[ToolCall, ...]:
    """Drop byte-equivalent duplicate calls without changing other content."""

    by_key: dict[object, ToolCall] = {}
    for call in calls:
        by_key.setdefault(_canonical_call(call), call)
    return tuple(by_key[key] for key in sorted(by_key, key=repr))


def _relation(left: Counter[object], right: Counter[object]) -> str:
    if left == right:
        return "exact"
    if set(left) & set(right):
        return "mixed"
    return "different"


@dataclass(frozen=True)
class SelfConsistencyState:
    """Gold-free relation between frozen M0 and a new direct observation."""

    parse_pair: str
    tool_relation: str
    call_count_relation: str
    key_signature_relation: str
    argument_value_relation: str

    def key(self, candidate_id: str) -> tuple[str, ...]:
        if candidate_id == COARSE_CANDIDATE:
            return (self.parse_pair, self.tool_relation)
        if candidate_id == HIERARCHICAL_CANDIDATE:
            return (
                self.parse_pair,
                self.tool_relation,
                self.call_count_relation,
                self.key_signature_relation,
                self.argument_value_relation,
            )
        raise SelfConsistencyError(f"unknown candidate_id {candidate_id!r}")

    @property
    def coarse_key(self) -> tuple[str, ...]:
        return self.key(COARSE_CANDIDATE)

    @property
    def detailed_key(self) -> tuple[str, ...]:
        return self.key(HIERARCHICAL_CANDIDATE)


@dataclass(frozen=True)
class SupplyRender:
    """Deterministic union-registry evidence derived from two responses."""

    text: str
    tool_names: tuple[str, ...]
    parsed_pair: tuple[bool, bool]

    @property
    def supply_available(self) -> bool:
        return bool(self.tool_names)


def extract_self_consistency_state(
    m0_response: str, observation_response: str
) -> SelfConsistencyState:
    """Extract only relation-valued state from two deployment responses."""

    m0_calls_raw, m0_parsed = parse_tool_calls_text(m0_response)
    observed_calls_raw, observed_parsed = parse_tool_calls_text(observation_response)
    if m0_parsed and observed_parsed:
        parse_pair = "both"
    elif m0_parsed or observed_parsed:
        parse_pair = "one"
    else:
        parse_pair = "neither"

    m0_calls = _deduplicate(m0_calls_raw)
    observed_calls = _deduplicate(observed_calls_raw)
    if not m0_parsed or not observed_parsed or not m0_calls or not observed_calls:
        return SelfConsistencyState(
            parse_pair=parse_pair,
            tool_relation="unresolved",
            call_count_relation="unresolved",
            key_signature_relation="unresolved",
            argument_value_relation="unresolved",
        )

    m0_names: Counter[object] = Counter(call.name for call in m0_calls)
    observed_names: Counter[object] = Counter(call.name for call in observed_calls)
    if m0_names == observed_names:
        tool_relation = "exact"
    elif set(m0_names) & set(observed_names):
        tool_relation = "overlap"
    else:
        tool_relation = "disjoint"
    call_count_relation = "equal" if len(m0_calls) == len(observed_calls) else "different"

    if tool_relation != "exact":
        key_relation = "unresolved"
        value_relation = "unresolved"
    else:
        m0_keys: Counter[object] = Counter(
            (call.name, tuple(sorted(str(key) for key in call.arguments)))
            for call in m0_calls
        )
        observed_keys: Counter[object] = Counter(
            (call.name, tuple(sorted(str(key) for key in call.arguments)))
            for call in observed_calls
        )
        key_relation = _relation(m0_keys, observed_keys)
        m0_values: Counter[object] = Counter(_canonical_call(call) for call in m0_calls)
        observed_values: Counter[object] = Counter(
            _canonical_call(call) for call in observed_calls
        )
        value_relation = _relation(m0_values, observed_values)

    return SelfConsistencyState(
        parse_pair=parse_pair,
        tool_relation=tool_relation,
        call_count_relation=call_count_relation,
        key_signature_relation=key_relation,
        argument_value_relation=value_relation,
    )


def render_union_stripped_registry(
    m0_response: str,
    observation_response: str,
    registry_rows: Sequence[Mapping[str, str]],
) -> SupplyRender:
    """Render the registry-resolved prediction union with defaults removed."""

    m0_calls, m0_parsed = parse_tool_calls_text(m0_response)
    observed_calls, observed_parsed = parse_tool_calls_text(observation_response)
    selected = {call.name for call in (*m0_calls, *observed_calls)}

    rows_by_name: dict[str, tuple[int, Mapping[str, str]]] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not isinstance(name, str) or not name:
            raise SelfConsistencyError("registry row lacks a non-empty tool_name")
        if name in rows_by_name:
            raise SelfConsistencyError(f"duplicate registry tool_name {name!r}")
        tool_id = row.get("tool_id")
        try:
            numeric_tool_id = int(tool_id)
        except (TypeError, ValueError):
            raise SelfConsistencyError(
                f"registry tool {name!r} lacks a numeric tool_id"
            ) from None
        rows_by_name[name] = (numeric_tool_id, row)
    names = tuple(
        name
        for name, (_tool_id, _row) in sorted(
            rows_by_name.items(), key=lambda item: (item[1][0], item[0])
        )
        if name in selected
    )
    text = "\n".join(
        render_registry_row(rows_by_name[name][1], strip_defaults=True)
        for name in names
    )
    return SupplyRender(text=text, tool_names=names, parsed_pair=(m0_parsed, observed_parsed))


@dataclass(frozen=True)
class SelfConsistencyOutcome:
    """Paired STOP/SUPPLY scorer-side return for one prospective sample."""

    sample_id: str
    group_id: str
    state: SelfConsistencyState
    supply_available: bool
    stop_score: ItemScore
    supply_score: ItemScore

    def __post_init__(self) -> None:
        if not self.sample_id or not self.group_id:
            raise ValueError("sample_id and group_id must be non-empty")
        if self.stop_score.exact_match not in (0.0, 1.0):
            raise ValueError("STOP exact match must be binary")
        if self.supply_score.exact_match not in (0.0, 1.0):
            raise ValueError("SUPPLY exact match must be binary")

    @property
    def delta(self) -> int:
        return int(self.supply_score.exact_match - self.stop_score.exact_match)

    @property
    def tool_accuracy_delta(self) -> int:
        return int(
            self.supply_score.tool_accuracy - self.stop_score.tool_accuracy
        )


def build_scored_outcomes(
    *,
    m0_response_by_id: Mapping[str, str],
    observation_response_by_id: Mapping[str, str],
    supply_response_by_id: Mapping[str, str],
    query_group_by_id: Mapping[str, str],
    registry_rows: Sequence[Mapping[str, str]],
    expected_by_id: Mapping[str, Sequence[ToolCall]],
) -> tuple[SelfConsistencyOutcome, ...]:
    """Build the registered scorer-side surface from three sealed arms.

    State and supply availability are computed before the corresponding gold
    row is read, keeping expected calls outside the runtime-information path.
    """

    sample_ids = set(m0_response_by_id)
    named_surfaces = {
        "observation": set(observation_response_by_id),
        "supply": set(supply_response_by_id),
        "query groups": set(query_group_by_id),
    }
    for label, values in named_surfaces.items():
        if values != sample_ids:
            raise SelfConsistencyError(
                f"{label} ids do not equal the frozen M0 sample identity"
            )
    missing_gold = sorted(sample_ids - set(expected_by_id))
    if missing_gold:
        raise SelfConsistencyError(
            f"scorer gold lacks registered sample ids: {missing_gold[:5]}"
        )

    outcomes: list[SelfConsistencyOutcome] = []
    for sample_id in sorted(sample_ids):
        m0_response = m0_response_by_id[sample_id]
        observation_response = observation_response_by_id[sample_id]
        state = extract_self_consistency_state(m0_response, observation_response)
        supply_available = render_union_stripped_registry(
            m0_response, observation_response, registry_rows
        ).supply_available

        expected = expected_by_id[sample_id]
        m0_calls, _m0_parsed = parse_tool_calls_text(m0_response)
        supply_calls, _supply_parsed = parse_tool_calls_text(
            supply_response_by_id[sample_id]
        )
        outcomes.append(
            SelfConsistencyOutcome(
                sample_id=sample_id,
                group_id=query_group_by_id[sample_id],
                state=state,
                supply_available=supply_available,
                stop_score=score_item(expected, m0_calls),
                supply_score=score_item(expected, supply_calls),
            )
        )
    return tuple(outcomes)


@dataclass(frozen=True)
class MemoryDecision:
    action: Action
    level: str
    support: int
    saves: int
    harms: int
    reason: str


def _cell_counts(
    state_key: tuple[str, ...],
    memory: Sequence[SelfConsistencyOutcome],
    *,
    candidate_id: str,
) -> tuple[int, int, int]:
    cell = tuple(
        item
        for item in memory
        if item.supply_available and item.state.key(candidate_id) == state_key
    )
    return (
        len(cell),
        sum(item.delta > 0 for item in cell),
        sum(item.delta < 0 for item in cell),
    )


def _decide_cell(
    support: int, saves: int, harms: int, *, level: str
) -> MemoryDecision:
    if support < MIN_CELL_SUPPORT:
        return MemoryDecision(
            STOP_M0, level, support, saves, harms, "insufficient-support"
        )
    if harms > MAX_CELL_HARMS:
        return MemoryDecision(STOP_M0, level, support, saves, harms, "observed-harm")
    if saves < MIN_CELL_SAVES:
        return MemoryDecision(
            STOP_M0, level, support, saves, harms, "insufficient-saves"
        )
    return MemoryDecision(
        SUPPLY_UNION_STRIPPED,
        level,
        support,
        saves,
        harms,
        "supported-positive-zero-harm-cell",
    )


def decide(
    state: SelfConsistencyState,
    memory: Sequence[SelfConsistencyOutcome],
    *,
    supply_available: bool,
    candidate_id: str,
) -> MemoryDecision:
    """Choose a registered action without fitting model parameters."""

    if not supply_available:
        return MemoryDecision(STOP_M0, "availability", 0, 0, 0, "supply-unavailable")
    if candidate_id == COARSE_CANDIDATE:
        counts = _cell_counts(
            state.coarse_key, memory, candidate_id=COARSE_CANDIDATE
        )
        return _decide_cell(*counts, level="coarse")
    if candidate_id != HIERARCHICAL_CANDIDATE:
        raise SelfConsistencyError(f"unknown candidate_id {candidate_id!r}")

    detailed_counts = _cell_counts(
        state.detailed_key, memory, candidate_id=HIERARCHICAL_CANDIDATE
    )
    detailed = _decide_cell(*detailed_counts, level="detailed")
    if detailed.support >= MIN_CELL_SUPPORT:
        return detailed
    coarse_counts = _cell_counts(
        state.coarse_key, memory, candidate_id=COARSE_CANDIDATE
    )
    return _decide_cell(*coarse_counts, level="coarse")


def _stable_rank(seed: int, group_id: str) -> str:
    return hashlib.sha256(f"{seed}\0{group_id}".encode()).hexdigest()


def assign_folds(
    outcomes: Sequence[SelfConsistencyOutcome], *, seed: int, n_folds: int = 5
) -> tuple[tuple[SelfConsistencyOutcome, ...], ...]:
    """Assign complete groups to deterministic sample-balanced folds."""

    if n_folds < 2:
        raise SelfConsistencyError("cross-fitting requires at least two folds")
    by_group: dict[str, list[SelfConsistencyOutcome]] = {}
    seen: set[str] = set()
    for item in outcomes:
        if item.sample_id in seen:
            raise SelfConsistencyError(f"duplicate sample_id {item.sample_id!r}")
        seen.add(item.sample_id)
        by_group.setdefault(item.group_id, []).append(item)
    if len(by_group) < n_folds:
        raise SelfConsistencyError("fewer independent groups than folds")
    ordered = sorted(
        by_group.items(),
        key=lambda pair: (-len(pair[1]), _stable_rank(seed, pair[0]), pair[0]),
    )
    folds: list[list[SelfConsistencyOutcome]] = [[] for _ in range(n_folds)]
    for _group, items in ordered:
        destination = min(range(n_folds), key=lambda index: (len(folds[index]), index))
        folds[destination].extend(items)
    return tuple(
        tuple(sorted(fold, key=lambda item: item.sample_id)) for fold in folds
    )


@dataclass(frozen=True)
class DecisionOutcome:
    outcome: SelfConsistencyOutcome
    action: Action

    @property
    def selected_exact(self) -> int:
        score = (
            self.outcome.supply_score
            if self.action == SUPPLY_UNION_STRIPPED
            else self.outcome.stop_score
        )
        return int(score.exact_match)

    @property
    def net_gain(self) -> int:
        return self.selected_exact - int(self.outcome.stop_score.exact_match)

    @property
    def tool_accuracy_net_gain(self) -> int:
        selected = (
            self.outcome.supply_score.tool_accuracy
            if self.action == SUPPLY_UNION_STRIPPED
            else self.outcome.stop_score.tool_accuracy
        )
        return int(selected - self.outcome.stop_score.tool_accuracy)


@dataclass(frozen=True)
class CandidateMetrics:
    n_samples: int
    supplied: int
    stopped: int
    saved: int
    harmed: int
    net_gain: int
    tool_accuracy_net_gain: int
    contact_rate: float
    fold_net_gains: tuple[int, ...]
    ci_low: float
    ci_high: float
    sigma_hat: float
    harm_avoidance: float
    save_retention: float


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


def _state_label(state: SelfConsistencyState, candidate_id: str) -> str:
    return json.dumps(state.key(candidate_id), separators=(",", ":"))


def _bootstrap(
    decisions: Sequence[DecisionOutcome], *, seed: int, n_replicates: int
):
    by_group: dict[str, list[int]] = {}
    for decision in decisions:
        by_group.setdefault(decision.outcome.group_id, []).append(decision.net_gain)
    group_ids = tuple(sorted(by_group))

    def statistic(groups: Sequence[str]) -> float:
        values = [value for group in groups for value in by_group[group]]
        return sum(values) / len(values)

    return paired_cluster_bootstrap(
        sample_ids=group_ids,
        statistic=statistic,
        n_replicates=n_replicates,
        seed=seed,
        ci_level=0.90,
    )


def evaluate_candidate(
    outcomes: Sequence[SelfConsistencyOutcome],
    *,
    candidate_id: str,
    seed: int = FOLD_SEED,
    n_folds: int = 5,
    n_replicates: int = 10_000,
) -> CandidateReport:
    """Cross-fit one frozen candidate and apply every registered gate."""

    ordered = tuple(sorted(outcomes, key=lambda item: item.sample_id))
    if not ordered:
        raise SelfConsistencyError("candidate evaluation requires outcomes")
    folds = assign_folds(ordered, seed=seed, n_folds=n_folds)
    decisions: list[DecisionOutcome] = []
    fold_net_gains: list[int] = []
    for fold_index, evaluation in enumerate(folds):
        memory = tuple(
            item
            for index, fold in enumerate(folds)
            if index != fold_index
            for item in fold
        )
        fold_decisions = tuple(
            DecisionOutcome(
                item,
                decide(
                    item.state,
                    memory,
                    supply_available=item.supply_available,
                    candidate_id=candidate_id,
                ).action,
            )
            for item in evaluation
        )
        decisions.extend(fold_decisions)
        fold_net_gains.append(sum(item.net_gain for item in fold_decisions))
    selected = tuple(sorted(decisions, key=lambda item: item.outcome.sample_id))

    supplied = sum(item.action == SUPPLY_UNION_STRIPPED for item in selected)
    saved = sum(
        item.action == SUPPLY_UNION_STRIPPED and item.outcome.delta > 0
        for item in selected
    )
    harmed = sum(
        item.action == SUPPLY_UNION_STRIPPED and item.outcome.delta < 0
        for item in selected
    )
    always_saves = sum(item.supply_available and item.delta > 0 for item in ordered)
    always_harms = sum(item.supply_available and item.delta < 0 for item in ordered)
    harm_avoidance = (
        (always_harms - harmed) / always_harms if always_harms else 1.0
    )
    save_retention = saved / always_saves if always_saves else 0.0
    class_counts = Counter(_state_label(item.state, candidate_id) for item in ordered)
    non_dominant = len(ordered) - max(class_counts.values(), default=0)
    bootstrap = _bootstrap(selected, seed=seed, n_replicates=n_replicates)
    net_gain = sum(item.net_gain for item in selected)
    tool_net = sum(item.tool_accuracy_net_gain for item in selected)
    gates = {
        "both_actions": supplied > 0 and supplied < len(ordered),
        "supply_range": MIN_SUPPLIED <= supplied <= MAX_SUPPLIED,
        "saved_minimum": saved >= MIN_SAVED,
        "harm_maximum": harmed <= MAX_HARMED,
        "net_gain": net_gain >= MIN_NET_GAIN,
        "positive_ci90_lower": bootstrap.ci_low > 0.0,
        "tool_accuracy_nonnegative": tool_net >= 0,
        "every_fold_nonnegative": all(value >= 0 for value in fold_net_gains),
        "positive_fold_count": sum(value > 0 for value in fold_net_gains)
        >= MIN_POSITIVE_FOLDS,
        "harm_avoidance": harm_avoidance >= MIN_HARM_AVOIDANCE,
        "save_retention": save_retention >= MIN_SAVE_RETENTION,
        "state_liveness": len(class_counts) >= 2
        and non_dominant >= MIN_NON_DOMINANT_STATE_SAMPLES,
    }
    metrics = CandidateMetrics(
        n_samples=len(ordered),
        supplied=supplied,
        stopped=len(ordered) - supplied,
        saved=saved,
        harmed=harmed,
        net_gain=net_gain,
        tool_accuracy_net_gain=tool_net,
        contact_rate=supplied / len(ordered),
        fold_net_gains=tuple(fold_net_gains),
        ci_low=bootstrap.ci_low,
        ci_high=bootstrap.ci_high,
        sigma_hat=bootstrap.sigma_hat,
        harm_avoidance=harm_avoidance,
        save_retention=save_retention,
    )
    return CandidateReport(
        candidate_id=candidate_id,
        state_class_counts=dict(sorted(class_counts.items())),
        metrics=metrics,
        gates=gates,
        promotion_passed=all(gates.values()),
        decisions=selected,
    )


def screen_candidates(
    outcomes: Sequence[SelfConsistencyOutcome],
    *,
    seed: int = FOLD_SEED,
    n_folds: int = 5,
    n_replicates: int = 10_000,
) -> ScreenResult:
    """Evaluate the two preregistered memory resolutions."""

    reports = {
        candidate_id: evaluate_candidate(
            outcomes,
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
    winner = sorted(
        eligible,
        key=lambda report: (
            -report.metrics.net_gain,
            -report.metrics.saved,
            report.metrics.supplied,
            report.candidate_id,
        ),
    )[0]
    return ScreenResult(reports, winner.candidate_id, True)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
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
        raise SelfConsistencyError(
            f"policy self hash mismatch: recorded={expected!r}, recomputed={actual!r}"
        )


def _decision_hash(decisions: Sequence[DecisionOutcome]) -> str:
    payload = "\n".join(
        f"{item.outcome.sample_id}\t{item.action}" for item in decisions
    ) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def _report_payload(report: CandidateReport) -> dict[str, object]:
    return {
        "candidate_id": report.candidate_id,
        "decision_identity_sha256": _decision_hash(report.decisions),
        "gates": dict(report.gates),
        "metrics": asdict(report.metrics),
        "promotion_passed": report.promotion_passed,
        "state_class_counts": dict(report.state_class_counts),
    }


def build_policy_artifact(
    outcomes: Sequence[SelfConsistencyOutcome],
    screen: ScreenResult,
    *,
    source_hashes: Mapping[str, str],
    offline_attempts: int,
) -> dict[str, object]:
    """Build a self-verifying discovery policy artifact."""

    if offline_attempts != 0:
        raise SelfConsistencyError("offline guard recorded an outbound attempt")
    if set(source_hashes) != {"m0", "repeat", "supply"}:
        raise SelfConsistencyError("source hashes must bind m0, repeat, and supply")
    if any(len(value) != 64 for value in source_hashes.values()):
        raise SelfConsistencyError("source hashes must be full SHA-256 values")
    reports = {
        key: _report_payload(value) for key, value in screen.reports.items()
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
            "execution_profile": "bounded-discovery-probe",
            "claim_status": "exposed-cohort secondary discovery only",
            "policy": {
                "default_action": STOP_M0,
                "minimum_cell_support": MIN_CELL_SUPPORT,
                "minimum_cell_saves": MIN_CELL_SAVES,
                "maximum_cell_harms": MAX_CELL_HARMS,
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
                "separately preregister the remaining exposed discovery support run"
                if screen.promotion_passed
                else "close direct self-consistency as this targeting signal"
            ),
        }
    )


def assert_policy_admits_support(document: Mapping[str, object]) -> None:
    """Fail closed before a support launcher can read this artifact."""

    assert_self_hash(document)
    if document.get("schema") != POLICY_SCHEMA:
        raise SelfConsistencyError("policy schema mismatch")
    if document.get("promotion_passed") is not True:
        raise SelfConsistencyError("discovery promotion screen did not pass")
    selected = document.get("selected")
    if not isinstance(selected, Mapping):
        raise SelfConsistencyError("policy lacks a selected candidate")
    metrics = selected.get("metrics")
    if not isinstance(metrics, Mapping):
        raise SelfConsistencyError("policy lacks selected metrics")
    if int(metrics.get("supplied", 0)) <= 0:
        raise SelfConsistencyError("selected policy does not exercise supply")
    if int(metrics.get("stopped", 0)) <= 0:
        raise SelfConsistencyError("selected policy does not exercise stop")
    counts = selected.get("state_class_counts")
    if not isinstance(counts, Mapping) or len(counts) < 2:
        raise SelfConsistencyError("selected policy state is not live")


__all__ = [
    "CANDIDATE_IDS",
    "COARSE_CANDIDATE",
    "EXPERIMENT_ID",
    "HIERARCHICAL_CANDIDATE",
    "POLICY_SCHEMA",
    "STOP_M0",
    "SUPPLY_UNION_STRIPPED",
    "CandidateMetrics",
    "CandidateReport",
    "DecisionOutcome",
    "MemoryDecision",
    "ScreenResult",
    "SelfConsistencyError",
    "SelfConsistencyOutcome",
    "SelfConsistencyState",
    "SupplyRender",
    "assert_policy_admits_support",
    "assert_self_hash",
    "assign_folds",
    "build_scored_outcomes",
    "build_policy_artifact",
    "decide",
    "evaluate_candidate",
    "extract_self_consistency_state",
    "render_union_stripped_registry",
    "screen_candidates",
    "with_self_hash",
]
