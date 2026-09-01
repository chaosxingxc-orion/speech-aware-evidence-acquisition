"""Query-vector state/action/return memory for evidence acquisition.

This is the v2 successor to the scalar acquisition-memory policy.  It changes
only the state representation: the exact direct-answer query vector already
used by the locked retriever replaces the lossy nine-scalar state.  Dispatch
scope, default action, action semantics, group isolation, and the two-stage
discovery/holdout boundary remain unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence


POLICY_SCHEMA = "saea-training-free-query-memory-policy-v2"
HOLDOUT_REPORT_SCHEMA = "saea-training-free-query-memory-holdout-v2"
POLICY_ID = "conservative-query-cosine-acquisition-memory-v2"
EXPERIMENT_ID = "SAEA-SN-MF-TFRL-QUERY-MEMORY-V2"
DISCOVERY_SEED = 20260901
REGISTRATION_PATHS = (
    "configs/experiment/slurp-training-free-query-memory-v2.json",
    "docs/readiness/2026-09-01-training-free-query-memory-v2-preregistration.md",
    "docs/exposure-ledger.md",
)


class QueryPolicyError(RuntimeError):
    """A fail-closed identity, state, or policy-boundary violation."""


@dataclass(frozen=True, order=True)
class Hyperparameters:
    k: int
    minimum_cosine: float

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError("k must be positive")
        if not (-1.0 <= self.minimum_cosine <= 1.0):
            raise ValueError("minimum_cosine must lie in [-1, 1]")


DEFAULT_GRID = tuple(
    Hyperparameters(k=k, minimum_cosine=minimum)
    for k in (1, 3, 5, 7)
    for minimum in (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99, 0.999999)
)


@dataclass(frozen=True)
class QueryOutcome:
    sample_id: str
    group_id: str
    query_vector: tuple[float, ...]
    direct_match: int
    evidence_match: int

    def __post_init__(self) -> None:
        if not self.sample_id or not self.group_id:
            raise ValueError("sample_id and group_id must be non-empty")
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
class Decision:
    action: str
    reason: str
    neighbor_ids: tuple[str, ...]
    neighbor_cosines: tuple[float, ...]
    neighbor_advantages: tuple[int, ...]


@dataclass(frozen=True)
class Evaluation:
    n: int
    stopped: int
    acquired: int
    contacts_saved: int
    baseline_correct: int
    policy_correct: int
    helpful_stops: int
    harmful_stops: int
    neutral_stops: int
    stopped_ids: tuple[str, ...]
    harmful_stop_ids: tuple[str, ...]
    helpful_stop_ids: tuple[str, ...]

    @property
    def delta_correct(self) -> int:
        return self.policy_correct - self.baseline_correct


@dataclass(frozen=True)
class FitResult:
    selected: Hyperparameters | None
    tune_metrics: Evaluation
    gate_metrics: Evaluation
    tune_ids: tuple[str, ...]
    gate_ids: tuple[str, ...]
    support_gate_passed: bool
    support_gate_minimum_stops: int
    candidate_table: tuple[Mapping[str, object], ...]


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def with_self_hash(payload: Mapping[str, object]) -> dict[str, object]:
    if "self_sha256" in payload:
        raise QueryPolicyError("payload already carries self_sha256")
    out = dict(payload)
    out["self_sha256"] = hashlib.sha256(_canonical_bytes(out)).hexdigest()
    return out


def assert_self_hash(payload: Mapping[str, object]) -> str:
    expected = payload.get("self_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise QueryPolicyError("policy artifact lacks a valid self hash")
    unhashed = {key: value for key, value in payload.items() if key != "self_sha256"}
    measured = hashlib.sha256(_canonical_bytes(unhashed)).hexdigest()
    if measured != expected:
        raise QueryPolicyError(f"policy artifact self hash mismatch: {measured} != {expected}")
    return measured


def assert_policy_admits_holdout(payload: Mapping[str, object]) -> None:
    if payload.get("schema") != POLICY_SCHEMA:
        raise QueryPolicyError("holdout policy has the wrong schema")
    if payload.get("support_gate_passed") is not True:
        raise QueryPolicyError("discovery support gate did not pass; holdout rewards stay unread")


def _repo_relpath(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as error:
        raise QueryPolicyError(f"artifact is outside the registered repository: {path}") from error


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
        raise QueryPolicyError(f"{label} is not committed at HEAD")
    if clean.returncode != 0:
        raise QueryPolicyError(f"{label} differs from its committed HEAD bytes")


def _assert_registration_committed(repo_root: Path) -> None:
    for relpath in REGISTRATION_PATHS:
        _assert_file_committed(
            repo_root=repo_root,
            path=repo_root / relpath,
            label=relpath,
        )
    ledger = (repo_root / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    if ledger.count(f"| 2026-09-01 | {EXPERIMENT_ID} |") != 1:
        raise QueryPolicyError("committed exposure ledger lacks exactly one v2 experiment row")


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise QueryPolicyError("query-memory vector dimensions disagree")
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        raise QueryPolicyError("query-memory cosine received a zero vector")
    return max(-1.0, min(1.0, numerator / (left_norm * right_norm)))


def decide(
    *,
    query_vector: Sequence[float],
    memory: Sequence[QueryOutcome],
    k: int,
    minimum_cosine: float,
    exclude_group_id: str | None = None,
) -> Decision:
    params = Hyperparameters(k=k, minimum_cosine=minimum_cosine)
    ranked = sorted(
        (
            (_cosine(query_vector, item.query_vector), item)
            for item in memory
            if item.group_id != exclude_group_id
        ),
        key=lambda pair: (-pair[0], pair[1].sample_id),
    )
    local = [(similarity, item) for similarity, item in ranked if similarity >= params.minimum_cosine]
    if len(local) < params.k:
        return Decision("ACQUIRE", "insufficient-query-support", (), (), ())
    selected = local[: params.k]
    ids = tuple(item.sample_id for _similarity, item in selected)
    similarities = tuple(similarity for similarity, _item in selected)
    advantages = tuple(item.acquisition_advantage for _similarity, item in selected)
    if any(value > 0 for value in advantages):
        return Decision(
            "ACQUIRE", "positive-return-query-neighbor", ids, similarities, advantages
        )
    return Decision("STOP", "unanimous-nonpositive-query-return", ids, similarities, advantages)


def evaluate(
    items: Sequence[QueryOutcome],
    *,
    memory: Sequence[QueryOutcome],
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


def _split_groups(
    items: Sequence[QueryOutcome], *, seed: int
) -> tuple[tuple[QueryOutcome, ...], tuple[QueryOutcome, ...]]:
    groups = sorted(
        {item.group_id for item in items},
        key=lambda group: (_hash_text(f"{seed}:{group}"), group),
    )
    if len(groups) < 4:
        raise QueryPolicyError("discovery needs at least four independent utterance groups")
    count = max(1, min(len(groups) - 1, math.ceil(0.70 * len(groups))))
    tune_groups = set(groups[:count])
    tune = tuple(sorted((item for item in items if item.group_id in tune_groups), key=lambda x: x.sample_id))
    gate = tuple(sorted((item for item in items if item.group_id not in tune_groups), key=lambda x: x.sample_id))
    return tune, gate


def _empty_evaluation(n: int = 0) -> Evaluation:
    return Evaluation(n, 0, n, 0, 0, 0, 0, 0, 0, (), (), ())


def _evaluation_payload(metrics: Evaluation, *, include_ids: bool) -> dict[str, object]:
    payload = asdict(metrics)
    payload["delta_correct"] = metrics.delta_correct
    payload["contact_reduction_rate"] = metrics.contacts_saved / metrics.n if metrics.n else 0.0
    if not include_ids:
        for key in ("stopped_ids", "harmful_stop_ids", "helpful_stop_ids"):
            payload.pop(key)
    return payload


def fit_discovery(
    items: Sequence[QueryOutcome],
    *,
    grid: Sequence[Hyperparameters] = DEFAULT_GRID,
    seed: int = DISCOVERY_SEED,
) -> FitResult:
    ordered = tuple(sorted(items, key=lambda item: item.sample_id))
    if len({item.sample_id for item in ordered}) != len(ordered):
        raise QueryPolicyError("discovery contains duplicate sample ids")
    if not grid:
        raise QueryPolicyError("candidate grid is empty")
    tune, gate = _split_groups(ordered, seed=seed)
    rows: list[dict[str, object]] = []
    candidates: list[tuple[Hyperparameters, Evaluation]] = []
    for params in sorted(set(grid)):
        metrics = evaluate(tune, memory=tune, params=params, exclude_own_group=True)
        admissible = metrics.harmful_stops == 0 and metrics.stopped >= 2
        rows.append(
            {
                **asdict(params),
                "admissible": admissible,
                "metrics": _evaluation_payload(metrics, include_ids=False),
            }
        )
        if admissible:
            candidates.append((params, metrics))
    if not candidates:
        return FitResult(
            selected=None,
            tune_metrics=_empty_evaluation(len(tune)),
            gate_metrics=_empty_evaluation(len(gate)),
            tune_ids=tuple(item.sample_id for item in tune),
            gate_ids=tuple(item.sample_id for item in gate),
            support_gate_passed=False,
            support_gate_minimum_stops=max(2, math.ceil(0.10 * len(gate))),
            candidate_table=tuple(rows),
        )
    selected, tune_metrics = sorted(
        candidates,
        key=lambda pair: (
            -pair[1].contacts_saved,
            -pair[0].k,
            -pair[0].minimum_cosine,
        ),
    )[0]
    gate_metrics = evaluate(gate, memory=tune, params=selected)
    minimum_stops = max(2, math.ceil(0.10 * len(gate)))
    passed = gate_metrics.harmful_stops == 0 and gate_metrics.stopped >= minimum_stops
    return FitResult(
        selected=selected,
        tune_metrics=tune_metrics,
        gate_metrics=gate_metrics,
        tune_ids=tuple(item.sample_id for item in tune),
        gate_ids=tuple(item.sample_id for item in gate),
        support_gate_passed=passed,
        support_gate_minimum_stops=minimum_stops,
        candidate_table=tuple(rows),
    )


def memory_digest(items: Sequence[QueryOutcome]) -> str:
    rows = [
        {
            "sample_id": item.sample_id,
            "group_id_sha256": _hash_text(item.group_id),
            "query_vector_sha256": hashlib.sha256(
                json.dumps(item.query_vector, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "direct_match": item.direct_match,
            "evidence_match": item.evidence_match,
        }
        for item in sorted(items, key=lambda value: value.sample_id)
    ]
    return hashlib.sha256(
        (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()


def _load_cell(*, population_id: str, repo_root: Path, data_root: Path):
    from .training_free_acquisition_memory import _load_cell as load_v1_cell

    return load_v1_cell(population_id=population_id, repo_root=repo_root, data_root=data_root)


def _outcomes_from_cell(cell, replays: Mapping[str, object]) -> tuple[QueryOutcome, ...]:
    from . import dev100_damage_channel_analysis as dc

    items: list[QueryOutcome] = []
    dimensions: set[int] = set()
    for sample_id in cell.sample_ids:
        replay = replays[sample_id]
        if not replay.dispatched:
            continue
        evidence_text = cell.inputs.evidence_texts.get(sample_id)
        if evidence_text is None or cell.final_texts[sample_id] != evidence_text:
            raise QueryPolicyError(
                f"{sample_id}: dispatched final response is not its evidence response"
            )
        gold = cell.inputs.gold_by_sample[sample_id]
        direct = dc.score_response(gold, cell.inputs.direct_texts[sample_id])
        evidence = dc.score_response(gold, evidence_text)
        vector = tuple(float(value) for value in cell.inputs.query_vectors[sample_id])
        dimensions.add(len(vector))
        items.append(
            QueryOutcome(
                sample_id=sample_id,
                group_id=str(gold.utterance_id),
                query_vector=vector,
                direct_match=1 if direct["correct"] else 0,
                evidence_match=1 if evidence["correct"] else 0,
            )
        )
    if len(dimensions) != 1:
        raise QueryPolicyError(f"query memory carries inconsistent dimensions: {dimensions}")
    return tuple(sorted(items, key=lambda item: item.sample_id))


def fit(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    from .dev100_reviewer_audit import arm_offline_guard

    _assert_registration_committed(repo_root)
    attempts = arm_offline_guard()
    cell, replays, replay_gate = _load_cell(
        population_id="DEV-100-ROUND4", repo_root=repo_root, data_root=data_root
    )
    items = _outcomes_from_cell(cell, replays)
    result = fit_discovery(items)
    payload: dict[str, object] = {
        "schema": POLICY_SCHEMA,
        "policy_id": POLICY_ID,
        "state_contract": "direct-answer-query-vector-cosine-v2",
        "scope": {
            "default_action": "ACQUIRE",
            "may_widen_dispatch": False,
            "eligible_population": "locked-v1 baseline-dispatched trajectories only",
            "counterfactual_imputation": "forbidden; both logged responses are required",
        },
        "discovery": {
            "population": "DEV-100-ROUND4",
            "seed": DISCOVERY_SEED,
            "eligible_dispatched_n": len(items),
            "query_dimension": len(items[0].query_vector),
            "sample_identity_sha256": _hash_text(
                "\n".join(item.sample_id for item in items) + "\n"
            ),
            "source_hashes": dict(sorted(cell.artifact_hashes.items())),
            "replay_gate": replay_gate,
        },
        "candidate_grid": [asdict(params) for params in DEFAULT_GRID],
        "selection_rule": (
            "grouped 70/30 discovery; tune candidates require >=2 STOP and zero harmful STOP; "
            "maximize contacts saved, then larger k, then larger minimum cosine; support gate "
            "requires zero harmful STOP and max(2, ceil(10% of gate n)) STOP"
        ),
        "selected": None if result.selected is None else asdict(result.selected),
        "support_gate_passed": result.support_gate_passed,
        "support_gate_minimum_stops": result.support_gate_minimum_stops,
        "tune": _evaluation_payload(result.tune_metrics, include_ids=True),
        "gate": _evaluation_payload(result.gate_metrics, include_ids=True),
        "tune_identity_sha256": _hash_text("\n".join(result.tune_ids) + "\n"),
        "gate_identity_sha256": _hash_text("\n".join(result.gate_ids) + "\n"),
        "candidate_table": list(result.candidate_table),
        "memory_digest": memory_digest(items),
        "holdout_authorization": (
            "DEV-500-NEW400 may be read only when support_gate_passed is true and this artifact "
            "is committed before evaluate starts"
        ),
        "claim_scope": (
            "iteration-tier retrospective discovery; no baseline revision, test, confirmatory, "
            "generality, or Stage-3 claim"
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
        raise QueryPolicyError("passed policy has no selected hyperparameters")
    return Hyperparameters(
        k=int(selected["k"]),
        minimum_cosine=float(selected["minimum_cosine"]),
    )


def evaluate_holdout(
    *,
    policy: Mapping[str, object],
    repo_root: Path,
    data_root: Path,
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
        raise QueryPolicyError("reloaded memory does not match the frozen policy artifact")
    if dict(sorted(memory_cell.artifact_hashes.items())) != policy["discovery"]["source_hashes"]:
        raise QueryPolicyError("discovery source hashes moved after policy freeze")

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
    baseline_profile = mve.slurp_extraction_block(
        scored=baseline_scored, sample_ids=population_ids
    )
    policy_profile = mve.slurp_extraction_block(
        scored=policy_scored, sample_ids=population_ids
    )
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
        "primary_ci90_lower_nonnegative": float(primary_bootstrap["ci90_low_pp"]) >= 0.0,
        "contact_savings_at_least_10_percent": metrics.contacts_saved >= minimum_savings,
    }
    promotion_gate["passed"] = all(promotion_gate.values())
    payload: dict[str, object] = {
        "schema": HOLDOUT_REPORT_SCHEMA,
        "policy_id": POLICY_ID,
        "policy_self_sha256": policy["self_sha256"],
        "selected": asdict(params),
        "memory_digest": memory_digest(memory),
        "holdout": {
            "population": "DEV-500-NEW400",
            "parent_n": len(holdout_cell.sample_ids),
            "baseline_dispatched_n": len(holdout_all),
            "same_utterance_as_memory_excluded_n": len(overlap),
            "eligible_dispatched_n": len(eligible),
            "eligible_identity_sha256": _hash_text(
                "\n".join(item.sample_id for item in eligible) + "\n"
            ),
            "source_hashes": dict(sorted(holdout_cell.artifact_hashes.items())),
            "replay_gate": holdout_gate,
            "memory_replay_gate": memory_gate,
        },
        "policy_on_eligible_dispatched": _evaluation_payload(metrics, include_ids=True),
        "full_population": {
            "baseline": baseline_profile,
            "policy": policy_profile,
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
            label="v2 holdout policy artifact",
        )
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        payload = evaluate_holdout(
            policy=policy,
            repo_root=repo_root,
            data_root=data_root,
        )
    _write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "DEFAULT_GRID",
    "HOLDOUT_REPORT_SCHEMA",
    "POLICY_SCHEMA",
    "Decision",
    "Evaluation",
    "FitResult",
    "Hyperparameters",
    "QueryOutcome",
    "QueryPolicyError",
    "assert_policy_admits_holdout",
    "assert_self_hash",
    "decide",
    "evaluate",
    "evaluate_holdout",
    "fit",
    "fit_discovery",
    "memory_digest",
    "with_self_hash",
]
