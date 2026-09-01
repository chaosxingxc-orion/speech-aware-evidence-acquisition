"""Route-conditioned state/action/return memory for evidence acquisition.

V3 retains query-vector cosine memory but restricts neighbors to the same
runtime-visible relation between the direct answer and the proposed evidence
route.  DEV-100 is adaptive discovery; grouped cross-fitting is a stability
screen, not independent support.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import training_free_query_memory as qmem


POLICY_SCHEMA = "saea-training-free-route-memory-policy-v3"
HOLDOUT_REPORT_SCHEMA = "saea-training-free-route-memory-holdout-v3"
POLICY_ID = "conservative-route-conditioned-query-memory-v3"
EXPERIMENT_ID = "SAEA-SN-MF-TFRL-ROUTE-MEMORY-V3"
DISCOVERY_SEED = 20260902
N_FOLDS = 5
ROUTE_CLASSES = (
    "direct-unresolved",
    "direct-absent",
    "direct-rank-1-dispatched",
    "direct-runner-up",
    "direct-rank-3plus",
)
REGISTRATION_PATHS = (
    "configs/experiment/slurp-training-free-route-memory-v3.json",
    "docs/readiness/2026-09-01-training-free-route-memory-v3-preregistration.md",
    "docs/exposure-ledger.md",
    "src/speech_aware_evidence_acquisition/analysis/training_free_route_memory.py",
)

Hyperparameters = qmem.Hyperparameters
Decision = qmem.Decision
Evaluation = qmem.Evaluation
DEFAULT_GRID = qmem.DEFAULT_GRID


class RoutePolicyError(RuntimeError):
    """A fail-closed identity, state, or policy-boundary violation."""


@dataclass(frozen=True)
class RouteOutcome:
    sample_id: str
    group_id: str
    query_vector: tuple[float, ...]
    route_class: str
    direct_match: int
    evidence_match: int

    def __post_init__(self) -> None:
        if not self.sample_id or not self.group_id:
            raise ValueError("sample_id and group_id must be non-empty")
        if self.route_class not in ROUTE_CLASSES:
            raise ValueError(f"unknown route class: {self.route_class}")
        if not self.query_vector:
            raise ValueError("query vector must be non-empty")
        if any(not math.isfinite(value) for value in self.query_vector):
            raise ValueError("query vector must be finite")
        if sum(value * value for value in self.query_vector) <= 0.0:
            raise ValueError("query vector must have non-zero norm")
        if self.direct_match not in (0, 1) or self.evidence_match not in (0, 1):
            raise ValueError("matching rewards must be binary")

    @property
    def acquisition_advantage(self) -> int:
        return self.evidence_match - self.direct_match


@dataclass(frozen=True)
class CrossFitResult:
    selected: Hyperparameters | None
    crossfit_metrics: Evaluation
    fold_metrics: tuple[Evaluation, ...]
    fold_ids: tuple[tuple[str, ...], ...]
    active_stop_folds: int
    minimum_stops: int
    minimum_active_folds: int
    stability_screen_passed: bool
    candidate_table: tuple[Mapping[str, object], ...]


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def with_self_hash(payload: Mapping[str, object]) -> dict[str, object]:
    if "self_sha256" in payload:
        raise RoutePolicyError("payload already carries self_sha256")
    out = dict(payload)
    out["self_sha256"] = hashlib.sha256(_canonical_bytes(out)).hexdigest()
    return out


def assert_self_hash(payload: Mapping[str, object]) -> str:
    expected = payload.get("self_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise RoutePolicyError("policy artifact lacks a valid self hash")
    unhashed = {key: value for key, value in payload.items() if key != "self_sha256"}
    measured = hashlib.sha256(_canonical_bytes(unhashed)).hexdigest()
    if measured != expected:
        raise RoutePolicyError(f"policy artifact self hash mismatch: {measured} != {expected}")
    return measured


def assert_policy_admits_holdout(payload: Mapping[str, object]) -> None:
    if payload.get("schema") != POLICY_SCHEMA:
        raise RoutePolicyError("holdout policy has the wrong schema")
    if payload.get("stability_screen_passed") is not True:
        raise RoutePolicyError("exploratory stability screen did not pass; holdout rewards stay unread")
    discovery = payload.get("discovery")
    if not isinstance(discovery, Mapping):
        raise RoutePolicyError("policy artifact lacks discovery state diagnostics")
    route_counts = discovery.get("route_class_counts")
    if not isinstance(route_counts, Mapping):
        raise RoutePolicyError("policy artifact lacks route-class counts")
    live_routes = [key for key, value in route_counts.items() if int(value) > 0]
    if len(live_routes) < 2:
        raise RoutePolicyError("route state is degenerate; holdout rewards stay unread")
    crossfit = payload.get("crossfit")
    comparator = payload.get("fixed_v2_comparator")
    if not isinstance(crossfit, Mapping) or not isinstance(comparator, Mapping):
        raise RoutePolicyError("policy artifact lacks the decision-attribution comparison")
    comparator_crossfit = comparator.get("crossfit")
    if not isinstance(comparator_crossfit, Mapping):
        raise RoutePolicyError("policy artifact lacks comparator cross-fitted decisions")
    stopped = tuple(sorted(str(value) for value in crossfit.get("stopped_ids", ())))
    comparator_stopped = tuple(
        sorted(str(value) for value in comparator_crossfit.get("stopped_ids", ()))
    )
    if stopped == comparator_stopped:
        raise RoutePolicyError(
            "route conditioning does not change cross-fitted decisions; holdout rewards stay unread"
        )


def classify_route(*, direct_target: str | None, fused_targets: Sequence[str]) -> str:
    """Classify only the pre-contact relation between direct and fused targets."""

    if direct_target is None:
        return "direct-unresolved"
    try:
        position = tuple(fused_targets).index(direct_target)
    except ValueError:
        return "direct-absent"
    if position == 0:
        return "direct-rank-1-dispatched"
    if position == 1:
        return "direct-runner-up"
    return "direct-rank-3plus"


def decide(
    *,
    query_vector: Sequence[float],
    route_class: str,
    memory: Sequence[RouteOutcome],
    k: int,
    minimum_cosine: float,
    exclude_group_id: str | None = None,
) -> Decision:
    params = Hyperparameters(k=k, minimum_cosine=minimum_cosine)
    if route_class not in ROUTE_CLASSES:
        raise RoutePolicyError(f"unknown route class: {route_class}")
    ranked = sorted(
        (
            (qmem._cosine(query_vector, item.query_vector), item)
            for item in memory
            if item.group_id != exclude_group_id and item.route_class == route_class
        ),
        key=lambda pair: (-pair[0], pair[1].sample_id),
    )
    local = [(similarity, item) for similarity, item in ranked if similarity >= params.minimum_cosine]
    if len(local) < params.k:
        return Decision("ACQUIRE", "insufficient-route-query-support", (), (), ())
    selected = local[: params.k]
    ids = tuple(item.sample_id for _similarity, item in selected)
    similarities = tuple(similarity for similarity, _item in selected)
    advantages = tuple(item.acquisition_advantage for _similarity, item in selected)
    if any(value > 0 for value in advantages):
        return Decision("ACQUIRE", "positive-return-route-neighbor", ids, similarities, advantages)
    return Decision("STOP", "unanimous-nonpositive-route-return", ids, similarities, advantages)


def evaluate(
    items: Sequence[RouteOutcome],
    *,
    memory: Sequence[RouteOutcome],
    params: Hyperparameters,
    exclude_own_group: bool = False,
) -> Evaluation:
    stopped: list[str] = []
    harmful: list[str] = []
    helpful: list[str] = []
    baseline_correct = 0
    policy_correct = 0
    for item in sorted(items, key=lambda value: value.sample_id):
        decision = decide(
            query_vector=item.query_vector,
            route_class=item.route_class,
            memory=memory,
            k=params.k,
            minimum_cosine=params.minimum_cosine,
            exclude_group_id=item.group_id if exclude_own_group else None,
        )
        baseline_correct += item.evidence_match
        if decision.action == "STOP":
            stopped.append(item.sample_id)
            policy_correct += item.direct_match
            if item.direct_match > item.evidence_match:
                helpful.append(item.sample_id)
            elif item.direct_match < item.evidence_match:
                harmful.append(item.sample_id)
        else:
            policy_correct += item.evidence_match
    neutral = len(set(stopped) - set(harmful) - set(helpful))
    return Evaluation(
        n=len(items),
        stopped=len(stopped),
        acquired=len(items) - len(stopped),
        contacts_saved=len(stopped),
        baseline_correct=baseline_correct,
        policy_correct=policy_correct,
        helpful_stops=len(helpful),
        harmful_stops=len(harmful),
        neutral_stops=neutral,
        stopped_ids=tuple(stopped),
        harmful_stop_ids=tuple(harmful),
        helpful_stop_ids=tuple(helpful),
    )


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def assign_folds(
    items: Sequence[RouteOutcome], *, seed: int, n_folds: int
) -> tuple[tuple[RouteOutcome, ...], ...]:
    if n_folds < 2:
        raise RoutePolicyError("cross-fitting requires at least two folds")
    by_group: dict[str, list[RouteOutcome]] = {}
    for item in sorted(items, key=lambda value: value.sample_id):
        by_group.setdefault(item.group_id, []).append(item)
    if len(by_group) < n_folds:
        raise RoutePolicyError("cross-fitting has fewer independent groups than folds")
    ordered_groups = sorted(
        by_group.items(),
        key=lambda pair: (-len(pair[1]), _hash_text(f"{seed}:{pair[0]}"), pair[0]),
    )
    folds: list[list[RouteOutcome]] = [[] for _ in range(n_folds)]
    for _group_id, group_items in ordered_groups:
        destination = min(range(n_folds), key=lambda index: (len(folds[index]), index))
        folds[destination].extend(group_items)
    return tuple(
        tuple(sorted(fold, key=lambda value: value.sample_id)) for fold in folds
    )


def _empty_evaluation(n: int = 0) -> Evaluation:
    return Evaluation(n, 0, n, 0, 0, 0, 0, 0, 0, (), (), ())


def _merge_evaluations(parts: Sequence[Evaluation]) -> Evaluation:
    stopped_ids = tuple(sorted(sample_id for part in parts for sample_id in part.stopped_ids))
    harmful_ids = tuple(
        sorted(sample_id for part in parts for sample_id in part.harmful_stop_ids)
    )
    helpful_ids = tuple(
        sorted(sample_id for part in parts for sample_id in part.helpful_stop_ids)
    )
    return Evaluation(
        n=sum(part.n for part in parts),
        stopped=sum(part.stopped for part in parts),
        acquired=sum(part.acquired for part in parts),
        contacts_saved=sum(part.contacts_saved for part in parts),
        baseline_correct=sum(part.baseline_correct for part in parts),
        policy_correct=sum(part.policy_correct for part in parts),
        helpful_stops=sum(part.helpful_stops for part in parts),
        harmful_stops=sum(part.harmful_stops for part in parts),
        neutral_stops=sum(part.neutral_stops for part in parts),
        stopped_ids=stopped_ids,
        harmful_stop_ids=harmful_ids,
        helpful_stop_ids=helpful_ids,
    )


def _evaluation_payload(metrics: Evaluation, *, include_ids: bool) -> dict[str, object]:
    payload = asdict(metrics)
    payload["delta_correct"] = metrics.delta_correct
    payload["contact_reduction_rate"] = metrics.contacts_saved / metrics.n if metrics.n else 0.0
    if not include_ids:
        for key in ("stopped_ids", "harmful_stop_ids", "helpful_stop_ids"):
            payload.pop(key)
    return payload


def _crossfit_evaluate(
    folds: Sequence[Sequence[RouteOutcome]], *, params: Hyperparameters
) -> tuple[Evaluation, tuple[Evaluation, ...]]:
    fold_metrics: list[Evaluation] = []
    for held_index, heldout in enumerate(folds):
        memory = tuple(
            item
            for memory_index, fold in enumerate(folds)
            if memory_index != held_index
            for item in fold
        )
        fold_metrics.append(evaluate(heldout, memory=memory, params=params))
    return _merge_evaluations(fold_metrics), tuple(fold_metrics)


def fit_crossfitted(
    items: Sequence[RouteOutcome],
    *,
    grid: Sequence[Hyperparameters] = DEFAULT_GRID,
    seed: int = DISCOVERY_SEED,
    n_folds: int = N_FOLDS,
) -> CrossFitResult:
    ordered = tuple(sorted(items, key=lambda item: item.sample_id))
    if len({item.sample_id for item in ordered}) != len(ordered):
        raise RoutePolicyError("discovery contains duplicate sample ids")
    if not grid:
        raise RoutePolicyError("candidate grid is empty")
    folds = assign_folds(ordered, seed=seed, n_folds=n_folds)
    minimum_stops = math.ceil(0.10 * len(ordered))
    minimum_active_folds = min(3, n_folds)
    rows: list[dict[str, object]] = []
    candidates: list[tuple[Hyperparameters, Evaluation, tuple[Evaluation, ...], int]] = []
    for params in sorted(set(grid)):
        aggregate, fold_metrics = _crossfit_evaluate(folds, params=params)
        active_folds = sum(metrics.stopped > 0 for metrics in fold_metrics)
        admissible = (
            aggregate.harmful_stops == 0
            and aggregate.stopped >= minimum_stops
            and active_folds >= minimum_active_folds
        )
        rows.append(
            {
                **asdict(params),
                "admissible": admissible,
                "active_stop_folds": active_folds,
                "metrics": _evaluation_payload(aggregate, include_ids=False),
                "per_fold": [
                    _evaluation_payload(metrics, include_ids=False) for metrics in fold_metrics
                ],
            }
        )
        if admissible:
            candidates.append((params, aggregate, fold_metrics, active_folds))
    fold_ids = tuple(tuple(item.sample_id for item in fold) for fold in folds)
    if not candidates:
        return CrossFitResult(
            selected=None,
            crossfit_metrics=_empty_evaluation(len(ordered)),
            fold_metrics=(),
            fold_ids=fold_ids,
            active_stop_folds=0,
            minimum_stops=minimum_stops,
            minimum_active_folds=minimum_active_folds,
            stability_screen_passed=False,
            candidate_table=tuple(rows),
        )
    selected, metrics, selected_folds, active_folds = sorted(
        candidates,
        key=lambda row: (-row[1].contacts_saved, -row[0].k, -row[0].minimum_cosine),
    )[0]
    return CrossFitResult(
        selected=selected,
        crossfit_metrics=metrics,
        fold_metrics=selected_folds,
        fold_ids=fold_ids,
        active_stop_folds=active_folds,
        minimum_stops=minimum_stops,
        minimum_active_folds=minimum_active_folds,
        stability_screen_passed=True,
        candidate_table=tuple(rows),
    )


def memory_digest(items: Sequence[RouteOutcome]) -> str:
    rows = [
        {
            "sample_id": item.sample_id,
            "group_id_sha256": _hash_text(item.group_id),
            "query_vector_sha256": hashlib.sha256(
                json.dumps(item.query_vector, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "route_class": item.route_class,
            "direct_match": item.direct_match,
            "evidence_match": item.evidence_match,
        }
        for item in sorted(items, key=lambda value: value.sample_id)
    ]
    return hashlib.sha256(
        (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()


def _repo_relpath(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as error:
        raise RoutePolicyError(f"artifact is outside the registered repository: {path}") from error


def _assert_file_committed(*, repo_root: Path, path: Path, label: str) -> None:
    relpath = _repo_relpath(repo_root=repo_root, path=path)
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
        raise RoutePolicyError(f"{label} is not committed at HEAD")
    if clean.returncode != 0:
        raise RoutePolicyError(f"{label} differs from its committed HEAD bytes")


def _assert_registration_committed(repo_root: Path) -> None:
    for relpath in REGISTRATION_PATHS:
        _assert_file_committed(repo_root=repo_root, path=repo_root / relpath, label=relpath)
    ledger = (repo_root / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    if ledger.count(f"| 2026-09-01 | {EXPERIMENT_ID} |") != 1:
        raise RoutePolicyError("committed exposure ledger lacks exactly one v3 experiment row")


def _load_cell(*, population_id: str, repo_root: Path, data_root: Path):
    return qmem._load_cell(population_id=population_id, repo_root=repo_root, data_root=data_root)


def _outcomes_from_cell(cell, replays: Mapping[str, object]) -> tuple[RouteOutcome, ...]:
    from . import dev100_damage_channel_analysis as dc

    items: list[RouteOutcome] = []
    dimensions: set[int] = set()
    for sample_id in cell.sample_ids:
        replay = replays[sample_id]
        if not replay.dispatched:
            continue
        evidence_text = cell.inputs.evidence_texts.get(sample_id)
        if evidence_text is None or cell.final_texts[sample_id] != evidence_text:
            raise RoutePolicyError(
                f"{sample_id}: dispatched final response is not its evidence response"
            )
        gold = cell.inputs.gold_by_sample[sample_id]
        direct = dc.score_response(gold, cell.inputs.direct_texts[sample_id])
        evidence = dc.score_response(gold, evidence_text)
        vector = tuple(float(value) for value in cell.inputs.query_vectors[sample_id])
        dimensions.add(len(vector))
        items.append(
            RouteOutcome(
                sample_id=sample_id,
                group_id=str(gold.utterance_id),
                query_vector=vector,
                route_class=classify_route(
                    direct_target=replay.direct_target,
                    fused_targets=tuple(target for target, _score in replay.fused_ranked),
                ),
                direct_match=1 if direct["correct"] else 0,
                evidence_match=1 if evidence["correct"] else 0,
            )
        )
    if len(dimensions) != 1:
        raise RoutePolicyError(f"route memory carries inconsistent dimensions: {dimensions}")
    return tuple(sorted(items, key=lambda item: item.sample_id))


def _as_query(item: RouteOutcome) -> qmem.QueryOutcome:
    return qmem.QueryOutcome(
        sample_id=item.sample_id,
        group_id=item.group_id,
        query_vector=item.query_vector,
        direct_match=item.direct_match,
        evidence_match=item.evidence_match,
    )


def _fixed_v2_comparator(
    folds: Sequence[Sequence[RouteOutcome]],
) -> tuple[Evaluation, tuple[Evaluation, ...]]:
    params = Hyperparameters(k=1, minimum_cosine=0.95)
    parts: list[Evaluation] = []
    for held_index, heldout in enumerate(folds):
        memory = tuple(
            _as_query(item)
            for memory_index, fold in enumerate(folds)
            if memory_index != held_index
            for item in fold
        )
        parts.append(qmem.evaluate(tuple(_as_query(item) for item in heldout), memory=memory, params=params))
    return _merge_evaluations(parts), tuple(parts)


def fit(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    from .dev100_reviewer_audit import arm_offline_guard

    _assert_registration_committed(repo_root)
    attempts = arm_offline_guard()
    cell, replays, replay_gate = _load_cell(
        population_id="DEV-100-ROUND4", repo_root=repo_root, data_root=data_root
    )
    items = _outcomes_from_cell(cell, replays)
    result = fit_crossfitted(items)
    folds = assign_folds(items, seed=DISCOVERY_SEED, n_folds=N_FOLDS)
    comparator, comparator_folds = _fixed_v2_comparator(folds)
    payload: dict[str, object] = {
        "schema": POLICY_SCHEMA,
        "policy_id": POLICY_ID,
        "state_contract": "direct-answer-route-class-plus-query-vector-v3",
        "route_classes": list(ROUTE_CLASSES),
        "scope": {
            "default_action": "ACQUIRE",
            "may_widen_dispatch": False,
            "eligible_population": "locked-v1 baseline-dispatched trajectories only",
            "counterfactual_imputation": "forbidden; both logged responses are required",
        },
        "discovery": {
            "population": "DEV-100-ROUND4",
            "exposure_status": "adaptive discovery; no fold is fresh support",
            "seed": DISCOVERY_SEED,
            "folds": N_FOLDS,
            "eligible_dispatched_n": len(items),
            "query_dimension": len(items[0].query_vector),
            "route_class_counts": dict(sorted(Counter(item.route_class for item in items).items())),
            "sample_identity_sha256": _hash_text(
                "\n".join(item.sample_id for item in items) + "\n"
            ),
            "source_hashes": dict(sorted(cell.artifact_hashes.items())),
            "replay_gate": replay_gate,
        },
        "candidate_grid": [asdict(params) for params in DEFAULT_GRID],
        "selection_rule": (
            "five-fold whole-group cross-fitting; candidate requires zero harmful STOP, "
            "ceil(10% of eligible) STOP, and STOP in at least three folds; maximize contacts "
            "saved, then larger k, then larger minimum cosine"
        ),
        "selected": None if result.selected is None else asdict(result.selected),
        "stability_screen_passed": result.stability_screen_passed,
        "minimum_stops": result.minimum_stops,
        "minimum_active_folds": result.minimum_active_folds,
        "active_stop_folds": result.active_stop_folds,
        "crossfit": _evaluation_payload(result.crossfit_metrics, include_ids=True),
        "selected_per_fold": [
            _evaluation_payload(metrics, include_ids=True) for metrics in result.fold_metrics
        ],
        "fold_identity_sha256": [
            _hash_text("\n".join(sample_ids) + "\n") for sample_ids in result.fold_ids
        ],
        "candidate_table": list(result.candidate_table),
        "fixed_v2_comparator": {
            "k": 1,
            "minimum_cosine": 0.95,
            "selection_eligible": False,
            "crossfit": _evaluation_payload(comparator, include_ids=True),
            "per_fold": [
                _evaluation_payload(metrics, include_ids=True) for metrics in comparator_folds
            ],
        },
        "memory_digest": memory_digest(items),
        "holdout_authorization": (
            "DEV-500-NEW400 may be read only when stability_screen_passed is true and this "
            "artifact is committed before evaluate starts"
        ),
        "claim_scope": (
            "adaptive discovery stability only; no independent support, baseline revision, "
            "test, confirmatory, generality, or Stage-3 claim"
        ),
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "targets": attempts.targets,
        },
    }
    return with_self_hash(payload)


def _policy_params(policy: Mapping[str, object]) -> Hyperparameters:
    selected = policy.get("selected")
    if not isinstance(selected, Mapping):
        raise RoutePolicyError("passed policy has no selected hyperparameters")
    return Hyperparameters(
        k=int(selected["k"]), minimum_cosine=float(selected["minimum_cosine"])
    )


def evaluate_holdout(
    *, policy: Mapping[str, object], repo_root: Path, data_root: Path
) -> dict[str, object]:
    from . import matching_vs_extraction_read as mve
    from . import training_free_acquisition_memory as v1
    from .dev100_reviewer_audit import arm_offline_guard

    assert_self_hash(policy)
    assert_policy_admits_holdout(policy)
    params = _policy_params(policy)
    attempts = arm_offline_guard()

    memory_cell, memory_replays, memory_gate = _load_cell(
        population_id="DEV-100-ROUND4", repo_root=repo_root, data_root=data_root
    )
    memory = _outcomes_from_cell(memory_cell, memory_replays)
    if memory_digest(memory) != policy.get("memory_digest"):
        raise RoutePolicyError("reloaded memory does not match the frozen policy artifact")
    if dict(sorted(memory_cell.artifact_hashes.items())) != policy["discovery"]["source_hashes"]:
        raise RoutePolicyError("discovery source hashes moved after policy freeze")

    holdout_cell, holdout_replays, holdout_gate = _load_cell(
        population_id="DEV-500-NEW400", repo_root=repo_root, data_root=data_root
    )
    holdout_all = _outcomes_from_cell(holdout_cell, holdout_replays)
    memory_groups = {item.group_id for item in memory}
    overlap = tuple(item for item in holdout_all if item.group_id in memory_groups)
    eligible = tuple(item for item in holdout_all if item.group_id not in memory_groups)
    metrics = evaluate(eligible, memory=memory, params=params)
    decisions = {
        item.sample_id: decide(
            query_vector=item.query_vector,
            route_class=item.route_class,
            memory=memory,
            k=params.k,
            minimum_cosine=params.minimum_cosine,
        )
        for item in eligible
    }
    baseline_responses = dict(holdout_cell.final_texts)
    policy_responses = dict(holdout_cell.final_texts)
    for item in eligible:
        if decisions[item.sample_id].action == "STOP":
            policy_responses[item.sample_id] = holdout_cell.inputs.direct_texts[item.sample_id]

    baseline_scored = v1._score_response_map(holdout_cell, baseline_responses)
    policy_scored = v1._score_response_map(holdout_cell, policy_responses)
    population_ids = tuple(holdout_cell.sample_ids)
    baseline_profile = mve.slurp_extraction_block(scored=baseline_scored, sample_ids=population_ids)
    policy_profile = mve.slurp_extraction_block(scored=policy_scored, sample_ids=population_ids)
    primary_bootstrap = v1._bootstrap_primary(
        population_ids, baseline_scored.match, policy_scored.match
    )
    extraction_bootstrap = mve._mean_gain_block(
        sample_ids=population_ids,
        m0=baseline_scored.slot_f1,
        blend=policy_scored.slot_f1,
        resampling_universe="DEV-500-NEW400 full 400-sample population",
        units="macro slot-F1 points",
    )
    minimum_savings = math.ceil(0.10 * len(eligible))
    promotion_gate = {
        "eligible_dispatched_at_least_100": len(eligible) >= 100,
        "zero_harmful_stops": metrics.harmful_stops == 0,
        "primary_score_non_decreasing": metrics.delta_correct >= 0,
        "primary_ci90_lower_nonnegative": primary_bootstrap["ci90_low_pp"] >= 0.0,
        "contact_savings_at_least_10_percent": metrics.contacts_saved >= minimum_savings,
    }
    promotion_gate["passed"] = all(promotion_gate.values())
    payload: dict[str, object] = {
        "schema": HOLDOUT_REPORT_SCHEMA,
        "policy_id": POLICY_ID,
        "selected": asdict(params),
        "policy_self_sha256": policy["self_sha256"],
        "memory_digest": policy["memory_digest"],
        "discovery_replay_gate": memory_gate,
        "holdout_replay_gate": holdout_gate,
        "holdout": {
            "population": "DEV-500-NEW400",
            "all_baseline_dispatched": len(holdout_all),
            "overlapping_utterance_groups_excluded": len(overlap),
            "eligible_dispatched": len(eligible),
            "route_class_counts": dict(
                sorted(Counter(item.route_class for item in eligible).items())
            ),
            "minimum_contacts_saved": minimum_savings,
            "metrics": _evaluation_payload(metrics, include_ids=True),
            "baseline_extraction": baseline_profile,
            "policy_extraction": policy_profile,
            "primary_delta_samples": sum(policy_scored.match.values())
            - sum(baseline_scored.match.values()),
            "primary_delta_pp": 100.0
            * (sum(policy_scored.match.values()) - sum(baseline_scored.match.values()))
            / len(population_ids),
            "primary_bootstrap": primary_bootstrap,
            "macro_slot_f1_bootstrap": extraction_bootstrap,
            "baseline_core_contacts": len(population_ids) + len(holdout_all),
            "policy_core_contacts": len(population_ids) + len(holdout_all)
            - metrics.contacts_saved,
            "evidence_contacts_saved": metrics.contacts_saved,
        },
        "promotion_gate": promotion_gate,
        "claim_scope": (
            "retrospective held-out replication on already-exposed devel data; no baseline "
            "revision, test, confirmatory, generality, or Stage-3 claim"
        ),
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "targets": attempts.targets,
        },
    }
    return with_self_hash(payload)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("fit", "evaluate"):
        child = sub.add_parser(name)
        child.add_argument("--repo-root", type=Path, required=True)
        child.add_argument("--data-root", type=Path, required=True)
        child.add_argument("--output", type=Path, required=True)
        if name == "evaluate":
            child.add_argument("--policy", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    if args.command == "fit":
        payload = fit(repo_root=repo_root, data_root=data_root)
    else:
        _assert_file_committed(
            repo_root=repo_root,
            path=args.policy.resolve(),
            label="v3 holdout policy artifact",
        )
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        payload = evaluate_holdout(policy=policy, repo_root=repo_root, data_root=data_root)
    _write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "DEFAULT_GRID",
    "HOLDOUT_REPORT_SCHEMA",
    "POLICY_SCHEMA",
    "CrossFitResult",
    "Decision",
    "Evaluation",
    "Hyperparameters",
    "RouteOutcome",
    "RoutePolicyError",
    "assert_policy_admits_holdout",
    "assert_self_hash",
    "assign_folds",
    "classify_route",
    "decide",
    "evaluate",
    "evaluate_holdout",
    "fit",
    "fit_crossfitted",
    "memory_digest",
    "with_self_hash",
]
