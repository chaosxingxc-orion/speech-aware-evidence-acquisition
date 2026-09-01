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
import argparse
import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..rails.probes.a2t_pop_flight import (
    render_b1_tool_schemas as POP_SUPPLY_RENDERER,
)
from ..rails.probes.a2t_s2b_flight import (
    render_b1_tool_schemas as HEADROOM_SUPPLY_RENDERER,
)
from ..reproduction.toolcall_scoring import ToolCall, parse_tool_calls_text, score_item
from .bootstrap import BootstrapResult, paired_cluster_bootstrap

POLICY_SCHEMA = "saea-a2t-training-free-signed-supply-memory-policy-v1"
EXPERIMENT_ID = "SAEA-A2T-MF-TFRL-SIGNED-SUPPLY-MEMORY-V1"
SPLIT_IDENTITY_HASH = "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
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

REGISTRATION_PATHS: tuple[str, ...] = (
    "configs/experiment/a2t-training-free-signed-supply-memory-v1.json",
    "docs/readiness/2026-09-01-a2t-training-free-signed-supply-memory-v1-preregistration.md",
    "docs/exposure-ledger.md",
    "src/speech_aware_evidence_acquisition/analysis/training_free_a2t_supply_memory.py",
    "tests/unit/test_training_free_a2t_supply_memory.py",
)


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


@dataclass(frozen=True)
class SurfaceAudit:
    a0_rows: int
    headroom_rows: int
    population_rows: int
    eligible_rows: int
    distinct_query_groups: int
    repeated_query_groups: int
    supplied_tool_label_matches: int
    unresolved_registry_signatures: int


@dataclass(frozen=True)
class LoggedSurface:
    outcomes: tuple[SignedSupplyOutcome, ...]
    audit: SurfaceAudit


def load_query_groups_from_receipt(
    path: Path, *, expected_split_identity_hash: str
) -> dict[str, str]:
    """Load the frozen ``sample_id -> query_idx`` isolation mapping."""

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SupplyMemoryError(f"cannot read Audio2Tool receipt {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise SupplyMemoryError("Audio2Tool receipt must be a JSON object")
    if document.get("carrier") != "audio2tool":
        raise SupplyMemoryError("receipt carrier is not audio2tool")
    if document.get("split_identity_hash") != expected_split_identity_hash:
        raise SupplyMemoryError("receipt split identity does not match the registered hash")
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise SupplyMemoryError("Audio2Tool receipt has no items")
    groups: dict[str, str] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise SupplyMemoryError("Audio2Tool receipt item is not an object")
        tier = item.get("tier")
        item_id = item.get("id")
        query_idx = item.get("query_idx")
        if not isinstance(tier, str) or not tier:
            raise SupplyMemoryError("Audio2Tool receipt item lacks tier")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            raise SupplyMemoryError("Audio2Tool receipt item has an invalid id")
        if isinstance(query_idx, bool) or not isinstance(query_idx, int):
            raise SupplyMemoryError("Audio2Tool receipt item lacks an integer query_idx")
        sample_id = f"{tier}:{item_id:06d}"
        if sample_id in groups:
            raise SupplyMemoryError(f"Audio2Tool receipt has duplicate sample id {sample_id!r}")
        groups[sample_id] = str(query_idx)
    return groups


def _unique_index(rows: Sequence[object], *, label: str) -> dict[str, object]:
    indexed: dict[str, object] = {}
    for row in rows:
        sample_id = str(getattr(row, "sample_id"))
        if sample_id in indexed:
            raise SupplyMemoryError(f"{label} has duplicate sample_id {sample_id!r}")
        indexed[sample_id] = row
    return indexed


def _score_response(expected: Sequence[ToolCall], response: str):
    predicted, parsed = parse_tool_calls_text(response)
    return predicted, parsed, score_item(expected, predicted)


def build_logged_surface(
    *,
    a0_rows: Sequence[object],
    headroom_supply_rows: Sequence[object],
    population_supply_rows: Sequence[object],
    headroom_ids: Sequence[str],
    query_group_by_id: Mapping[str, str],
    registry_rows: Sequence[Mapping[str, str]],
    expected_by_id: Mapping[str, Sequence[ToolCall]],
    expected_a0_n: int = 400,
    expected_headroom_n: int = 120,
    expected_population_n: int = 97,
) -> LoggedSurface:
    """Build the paired 217-row surface with fail-closed fidelity checks.

    ``headroom_supply_rows`` and ``population_supply_rows`` may contain both
    arms from their source attempts.  Only B1 and R1 respectively are action
    outcomes; the sibling comparator arms are ignored after their source
    loaders have validated the attempts.
    """

    assert_supply_renderer_identity()
    if len(a0_rows) != expected_a0_n:
        raise SupplyMemoryError(
            f"A0 row count {len(a0_rows)} != expected {expected_a0_n}"
        )
    wrong_a0_arms = sorted(
        {str(getattr(row, "arm")) for row in a0_rows if getattr(row, "arm") != "zero-supply"}
    )
    if wrong_a0_arms:
        raise SupplyMemoryError(f"A0 contains unexpected arm(s): {wrong_a0_arms}")
    a0_by_id = _unique_index(a0_rows, label="A0")

    headroom_selected = tuple(
        row for row in headroom_supply_rows if getattr(row, "arm") == "B1"
    )
    population_selected = tuple(
        row for row in population_supply_rows if getattr(row, "arm") == "R1"
    )
    if len(headroom_selected) != expected_headroom_n:
        raise SupplyMemoryError(
            f"B1 row count {len(headroom_selected)} != expected {expected_headroom_n}"
        )
    if len(population_selected) != expected_population_n:
        raise SupplyMemoryError(
            f"R1 row count {len(population_selected)} != expected {expected_population_n}"
        )
    b1_by_id = _unique_index(headroom_selected, label="B1")
    r1_by_id = _unique_index(population_selected, label="R1")
    frozen_headroom = set(headroom_ids)
    if len(frozen_headroom) != len(tuple(headroom_ids)):
        raise SupplyMemoryError("headroom identity contains duplicate sample ids")
    if set(b1_by_id) != frozen_headroom:
        raise SupplyMemoryError("B1 ids do not equal the frozen headroom identity")
    if frozen_headroom & set(r1_by_id):
        raise SupplyMemoryError("headroom and population supply ids overlap")

    eligible_ids = tuple(sorted(frozen_headroom | set(r1_by_id)))
    if len(eligible_ids) != expected_headroom_n + expected_population_n:
        raise SupplyMemoryError("eligible signed-supply surface has the wrong cardinality")
    missing_a0 = sorted(set(eligible_ids) - set(a0_by_id))
    if missing_a0:
        raise SupplyMemoryError(f"eligible ids missing from A0: {missing_a0[:5]}")
    missing_gold = sorted(set(eligible_ids) - set(expected_by_id))
    if missing_gold:
        raise SupplyMemoryError(f"eligible ids missing scorer gold: {missing_gold[:5]}")
    missing_groups = sorted(set(eligible_ids) - set(query_group_by_id))
    if missing_groups:
        raise SupplyMemoryError(
            f"eligible ids missing a receipt query group: {missing_groups[:5]}"
        )

    outcomes: list[SignedSupplyOutcome] = []
    label_matches = 0
    for sample_id in eligible_ids:
        direct_row = a0_by_id[sample_id]
        direct_response = str(getattr(direct_row, "response_text"))
        # State is intentionally computed before scorer-side expected calls
        # are read in this loop.  Its function signature accepts no gold.
        state = extract_runtime_state(direct_response, registry_rows)
        expected = expected_by_id[sample_id]
        direct_calls, direct_parsed, direct_score = _score_response(expected, direct_response)
        if not direct_parsed:
            raise SupplyMemoryError(f"{sample_id}: tool-correct A0 response did not parse")
        direct_label = ",".join(sorted({call.name for call in direct_calls}))

        if sample_id in frozen_headroom:
            if direct_score.tool_accuracy != 1.0 or direct_score.exact_match != 0.0:
                raise SupplyMemoryError(
                    f"{sample_id}: headroom stratum is not A0 tool-correct/exact-wrong"
                )
            supply_row = b1_by_id[sample_id]
        else:
            if direct_score.tool_accuracy != 1.0 or direct_score.exact_match != 1.0:
                raise SupplyMemoryError(
                    f"{sample_id}: population stratum is not A0 tool-correct/exact-correct"
                )
            supply_row = r1_by_id[sample_id]

        supplied_label = getattr(supply_row, "supplied_tool")
        if supplied_label != direct_label:
            raise SupplyMemoryError(
                f"{sample_id}: supplied tool label {supplied_label!r} does not equal "
                f"the A0-selected label {direct_label!r}"
            )
        label_matches += 1
        _supply_calls, _supply_parsed, supply_score = _score_response(
            expected, str(getattr(supply_row, "response"))
        )
        outcomes.append(
            SignedSupplyOutcome(
                sample_id=sample_id,
                group_id=str(query_group_by_id[sample_id]),
                state=state,
                stop_exact=int(direct_score.exact_match),
                supply_exact=int(supply_score.exact_match),
                stop_tool_accuracy=direct_score.tool_accuracy,
                supply_tool_accuracy=supply_score.tool_accuracy,
                stop_slot_f1=direct_score.slot_f1,
                supply_slot_f1=supply_score.slot_f1,
            )
        )

    group_counts = Counter(item.group_id for item in outcomes)
    unresolved = sum(
        parse_signature_parameters(row.get("signature", "")) is None
        for row in registry_rows
    )
    return LoggedSurface(
        outcomes=tuple(outcomes),
        audit=SurfaceAudit(
            a0_rows=len(a0_rows),
            headroom_rows=len(headroom_selected),
            population_rows=len(population_selected),
            eligible_rows=len(outcomes),
            distinct_query_groups=len(group_counts),
            repeated_query_groups=sum(value > 1 for value in group_counts.values()),
            supplied_tool_label_matches=label_matches,
            unresolved_registry_signatures=unresolved,
        ),
    )


def _state_label(state: RuntimeState, candidate_id: str) -> str:
    return json.dumps(state.key(candidate_id), separators=(",", ":"))


def state_return_cells(
    outcomes: Sequence[SignedSupplyOutcome], *, candidate_id: str
) -> dict[str, dict[str, int]]:
    """Descriptive full-surface action-return counts for each frozen state."""

    cells: dict[str, dict[str, int]] = {}
    for item in outcomes:
        label = _state_label(item.state, candidate_id)
        cell = cells.setdefault(label, {"n": 0, "saves": 0, "harms": 0, "neutral": 0})
        cell["n"] += 1
        if item.delta > 0:
            cell["saves"] += 1
        elif item.delta < 0:
            cell["harms"] += 1
        else:
            cell["neutral"] += 1
    return dict(sorted(cells.items()))


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


def _identity_digest(lines: Sequence[str]) -> str:
    payload = "\n".join(sorted(lines)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _candidate_payload(
    report: CandidateReport, outcomes: Sequence[SignedSupplyOutcome]
) -> dict[str, object]:
    return {
        "candidate_id": report.candidate_id,
        "state_class_counts": dict(report.state_class_counts),
        "metrics": asdict(report.metrics),
        "gates": dict(report.gates),
        "promotion_passed": report.promotion_passed,
        "full_surface_return_cells": state_return_cells(
            outcomes, candidate_id=report.candidate_id
        ),
        "decision_identity_sha256": _identity_digest(
            [f"{item.outcome.sample_id}\t{item.action}" for item in report.decisions]
        ),
    }


def build_policy_artifact(
    surface: LoggedSurface,
    screen: ScreenResult,
    *,
    offline_attempts: int,
    source_hashes: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Create a response-free, self-hashed retrospective policy artifact."""

    reports = {
        candidate_id: _candidate_payload(report, surface.outcomes)
        for candidate_id, report in sorted(screen.reports.items())
    }
    selected = (
        None
        if screen.selected_candidate is None
        else reports[screen.selected_candidate]
    )
    outcomes = surface.outcomes
    memory_lines = [
        json.dumps(
            {
                "sample_id": item.sample_id,
                "group_id": item.group_id,
                "state": asdict(item.state),
                "stop_exact": item.stop_exact,
                "supply_exact": item.supply_exact,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        for item in outcomes
    ]
    payload: dict[str, object] = {
        "schema": POLICY_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "execution_profile": "model-free-check",
        "claim_status": "retrospective discovery feasibility only",
        "surface": {
            **asdict(surface.audit),
            "sample_identity_sha256": _identity_digest(
                [item.sample_id for item in outcomes]
            ),
            "query_group_identity_sha256": _identity_digest(
                [item.group_id for item in outcomes]
            ),
            "memory_sha256": _identity_digest(memory_lines),
            "always_stop_exact": sum(item.stop_exact for item in outcomes),
            "always_supply_exact": sum(item.supply_exact for item in outcomes),
            "always_supply_saves": sum(item.delta > 0 for item in outcomes),
            "always_supply_harms": sum(item.delta < 0 for item in outcomes),
        },
        "policy": {
            "type": "exact-cell non-parametric action-return memory",
            "default_action": STOP_DIRECT,
            "minimum_cell_support": MIN_CELL_SUPPORT,
            "minimum_cell_saves": MIN_CELL_SAVES,
            "maximum_cell_harms": MAX_CELL_HARMS,
            "parameter_training": "none",
        },
        "candidate_reports": reports,
        "selected_candidate": screen.selected_candidate,
        "selected": selected,
        "promotion_passed": screen.promotion_passed,
        "prospective_authorization": (
            "a pass may only propose a separately preregistered approximately-100-sample "
            "discovery experiment; this artifact authorizes no model contact"
        ),
        "offline_guard": {
            "outbound_connection_attempts": offline_attempts,
            "targets": [],
        },
        "source_hashes": dict(sorted((source_hashes or {}).items())),
    }
    return with_self_hash(payload)


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


def _assert_file_committed(*, repo_root: Path, relpath: str) -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relpath],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    clean = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relpath],
        cwd=repo_root,
        check=False,
    )
    if tracked.returncode != 0:
        raise SupplyMemoryError(f"{relpath} is not committed at HEAD")
    if clean.returncode != 0:
        raise SupplyMemoryError(f"{relpath} differs from its committed HEAD bytes")


def assert_registration_committed(repo_root: Path) -> None:
    for relpath in REGISTRATION_PATHS:
        _assert_file_committed(repo_root=repo_root, relpath=relpath)
    ledger = (repo_root / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    if ledger.count(f"Row `{EXPERIMENT_ID}`") != 1:
        raise SupplyMemoryError(
            "committed exposure ledger lacks exactly one signed-supply registration"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validated_a0_rows(
    a2t_reader,
    *,
    attempt_dir: Path,
    repo_root: Path,
) -> tuple[object, ...]:
    """Run A0's structural receipt checks without its per-row gold reload.

    ``build_a2t_report`` calls ``Audio2ToolAdapter.score`` once per row, and
    that adapter reloads the complete expected-call manifest on every call.
    This evaluator already performs one shared official-primitives scoring
    pass in :func:`build_logged_surface`, so repeating that reader's scoring
    would add 400 redundant manifest scans.  The receipt/row checks below are
    the exact helpers from the official reader; only the duplicate scoring
    pass is omitted.
    """

    rows, malformed = a2t_reader.load_attempt_rows(attempt_dir)
    flight_receipt = a2t_reader.load_flight_receipt(attempt_dir)
    split_receipt = a2t_reader._load_split_receipt(repo_root, "discovery")
    expected_ids = a2t_reader.expected_sample_ids(split_receipt)
    split_identity_hash = str(split_receipt["split_identity_hash"])
    reasons = a2t_reader._harness_defect_reasons(
        malformed_row_reasons=malformed,
        flight_receipt=flight_receipt,
        rows=rows,
        expected_ids=expected_ids,
        split_identity_hash=split_identity_hash,
    )
    if reasons:
        raise SupplyMemoryError(
            "A0 structural harness defect(s):\n  " + "\n  ".join(reasons)
        )
    return tuple(rows)


def load_registered_surface(
    *,
    repo_root: Path,
    data_root: Path,
    lock: Mapping[str, object],
    a0_attempt: Path,
    headroom_supply_attempt: Path,
    population_supply_attempt: Path,
    headroom_path: Path,
    stage2_arm_plan_path: Path,
    receipt_path: Path,
) -> LoggedSurface:
    """Validate the three consumed runs, then construct the frozen surface."""

    from ..data.audio2tool import load_expected_calls, load_tool_registry
    from . import a2t_pop_read, a2t_read, a2t_s2_read, a2t_s2b_read

    a0_rows = _validated_a0_rows(
        a2t_read, attempt_dir=a0_attempt, repo_root=repo_root
    )
    headroom_identity = a2t_s2_read.load_headroom_identity(headroom_path)
    a2t_s2b_read.build_a2t_s2b_report(
        headroom_supply_attempt,
        lock,
        data_root,
        repo_root=repo_root,
        headroom_path=headroom_path,
        stage2_arm_plan_path=stage2_arm_plan_path,
    )
    a2t_pop_read.build_a2t_pop_report(
        population_supply_attempt,
        lock,
        data_root,
        repo_root=repo_root,
    )

    b_rows, b_malformed = a2t_s2_read.load_attempt_rows(headroom_supply_attempt)
    pop_rows, pop_malformed = a2t_s2_read.load_attempt_rows(population_supply_attempt)
    malformed = (*b_malformed, *pop_malformed)
    if malformed:
        raise SupplyMemoryError(
            f"validated source loaders still reported {len(malformed)} malformed row(s)"
        )
    query_groups = load_query_groups_from_receipt(
        receipt_path, expected_split_identity_hash=SPLIT_IDENTITY_HASH
    )
    registry_rows = load_tool_registry(lock, data_root)
    expected_by_id = load_expected_calls(lock, data_root, repo_root=repo_root)
    surface = build_logged_surface(
        a0_rows=a0_rows,
        headroom_supply_rows=b_rows,
        population_supply_rows=pop_rows,
        headroom_ids=headroom_identity.sample_ids,
        query_group_by_id=query_groups,
        registry_rows=registry_rows,
        expected_by_id=expected_by_id,
    )
    saves = sum(item.delta > 0 for item in surface.outcomes)
    harms = sum(item.delta < 0 for item in surface.outcomes)
    if saves != 8 or harms != 36:
        raise SupplyMemoryError(
            f"signed-return aggregate drifted: saves={saves}, harms={harms}; expected 8/36"
        )
    return surface


def run_registered_replay(
    *,
    repo_root: Path,
    data_root: Path,
    lock: Mapping[str, object],
    a0_attempt: Path,
    headroom_supply_attempt: Path,
    population_supply_attempt: Path,
    headroom_path: Path,
    stage2_arm_plan_path: Path,
    receipt_path: Path,
) -> dict[str, object]:
    """Run the committed, zero-contact retrospective screen once."""

    from .dev100_reviewer_audit import arm_offline_guard

    assert_registration_committed(repo_root)
    attempts = arm_offline_guard()
    surface = load_registered_surface(
        repo_root=repo_root,
        data_root=data_root,
        lock=lock,
        a0_attempt=a0_attempt,
        headroom_supply_attempt=headroom_supply_attempt,
        population_supply_attempt=population_supply_attempt,
        headroom_path=headroom_path,
        stage2_arm_plan_path=stage2_arm_plan_path,
        receipt_path=receipt_path,
    )
    screen = screen_candidates(surface.outcomes)
    sources = {
        "a0_outputs": _sha256_file(a0_attempt / "outputs.jsonl"),
        "headroom_supply_outputs": _sha256_file(
            headroom_supply_attempt / "outputs.jsonl"
        ),
        "population_supply_outputs": _sha256_file(
            population_supply_attempt / "outputs.jsonl"
        ),
        "headroom_manifest": _sha256_file(headroom_path),
        "stage2_arm_plan": _sha256_file(stage2_arm_plan_path),
        "receipt": _sha256_file(receipt_path),
    }
    return build_policy_artifact(
        surface,
        screen,
        offline_attempts=attempts.count,
        source_hashes=sources,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m speech_aware_evidence_acquisition.analysis.training_free_a2t_supply_memory"
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--a0-attempt", type=Path, required=True)
    parser.add_argument("--headroom-supply-attempt", type=Path, required=True)
    parser.add_argument("--population-supply-attempt", type=Path, required=True)
    parser.add_argument("--headroom", type=Path, required=True)
    parser.add_argument("--stage2-arm-plan", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    from ..data.lock import load_lock

    args = _parser().parse_args(argv)
    artifact = run_registered_replay(
        repo_root=args.repo_root,
        data_root=args.data_root,
        lock=load_lock(args.lock),
        a0_attempt=args.a0_attempt,
        headroom_supply_attempt=args.headroom_supply_attempt,
        population_supply_attempt=args.population_supply_attempt,
        headroom_path=args.headroom,
        stage2_arm_plan_path=args.stage2_arm_plan,
        receipt_path=args.receipt,
    )
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0


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
    "SurfaceAudit",
    "LoggedSurface",
    "SupplyMemoryError",
    "assert_policy_admits_prospective",
    "assert_registration_committed",
    "assert_self_hash",
    "assert_supply_renderer_identity",
    "assign_folds",
    "build_logged_surface",
    "build_policy_artifact",
    "decide",
    "extract_runtime_state",
    "grouped_net_gain_bootstrap",
    "load_query_groups_from_receipt",
    "load_registered_surface",
    "main",
    "parse_signature_parameters",
    "run_registered_replay",
    "screen_candidates",
    "state_return_cells",
    "with_self_hash",
]


if __name__ == "__main__":  # pragma: no cover - exercised by the registered CLI run
    raise SystemExit(main())
