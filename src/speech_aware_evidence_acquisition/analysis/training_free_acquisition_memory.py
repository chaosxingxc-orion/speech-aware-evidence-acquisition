"""Training-free acquisition memory for the locked BLEND control plane.

The policy is deliberately conservative.  It operates only on trajectories
that the locked policy already dispatches, defaults to ``ACQUIRE``, and may
veto the second contact only when a local non-parametric memory contains
unanimously non-positive acquisition returns.  It never widens dispatch and
never imputes a response for an action that was not logged.

The executable experiment is split into two commands.  ``fit`` reads only the
already-exposed DEV-100 round-4 cell and writes a self-hashed policy artifact.
``evaluate`` refuses to open DEV-500-NEW400 unless that artifact records a
passed discovery support gate.  This makes the holdout boundary structural,
not a convention inside one combined analysis process.
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


POLICY_SCHEMA = "saea-training-free-acquisition-memory-policy-v1"
FIT_REPORT_SCHEMA = "saea-training-free-acquisition-memory-fit-v1"
HOLDOUT_REPORT_SCHEMA = "saea-training-free-acquisition-memory-holdout-v1"
POLICY_ID = "conservative-local-acquisition-return-memory-v1"
FEATURE_CONTRACT = "pre-acquisition-blend-telemetry-v1"
DISCOVERY_SEED = 20260901
EXPERIMENT_ID = "SAEA-SN-MF-TFRL-ACQUISITION-MEMORY-V1"
REGISTRATION_PATHS = (
    "configs/experiment/slurp-training-free-acquisition-memory-v1.json",
    "docs/readiness/2026-09-01-training-free-acquisition-memory-preregistration.md",
    "docs/exposure-ledger.md",
)

# Every feature is available after recall/rank/fuse and before the optional
# evidence contact.  No gold, future response, reference transcript, sample
# identity, speaker identity, or future-turn field appears here.
FEATURE_NAMES = (
    "cosine_top1_unit",
    "cosine_top2_unit",
    "cosine_margin_unit",
    "fused_top1_score",
    "fused_margin_top2",
    "admitted_facet_fraction",
    "selected_value_fraction",
    "selected_target_fraction",
    "direct_response_parsed",
)

class PolicyError(RuntimeError):
    """A fail-closed policy, identity, or experiment-boundary violation."""


@dataclass(frozen=True, order=True)
class Hyperparameters:
    """The two transparent non-parametric policy knobs."""

    k: int
    radius: float

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError("k must be positive")
        if not (0.0 <= self.radius <= 1.0):
            raise ValueError("radius must lie in [0, 1]")


DEFAULT_GRID = tuple(
    # Radius is mean absolute distance in the fixed [0, 1]^d state space.
    # The finite grid is frozen before discovery rewards are read.  Candidate
    # selection below resolves ties toward larger k and smaller radius.
    Hyperparameters(k=k, radius=radius)
    for k in (1, 3, 5, 7)
    for radius in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
)


@dataclass(frozen=True)
class Outcome:
    """One fully observed logged decision point.

    Both responses must exist because the baseline dispatched this sample.
    Consequently both actions are observed: ``STOP`` selects the trajectory's
    own direct response and ``ACQUIRE`` selects its own evidence response.
    """

    sample_id: str
    group_id: str
    state: tuple[float, ...]
    direct_match: int
    evidence_match: int

    def __post_init__(self) -> None:
        if not self.sample_id or not self.group_id:
            raise ValueError("sample_id and group_id must be non-empty")
        if len(self.state) != len(FEATURE_NAMES):
            raise ValueError("state does not match the frozen feature contract")
        if any(not math.isfinite(value) or not (0.0 <= value <= 1.0) for value in self.state):
            raise ValueError("every state feature must be finite and lie in [0, 1]")
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
    neighbor_distances: tuple[float, ...]
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
    """Return a canonical mapping carrying a SHA-256 over all other fields."""

    if "self_sha256" in payload:
        raise PolicyError("payload already carries self_sha256")
    out = dict(payload)
    out["self_sha256"] = hashlib.sha256(_canonical_bytes(out)).hexdigest()
    return out


def assert_self_hash(payload: Mapping[str, object]) -> str:
    expected = payload.get("self_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise PolicyError("policy artifact lacks a valid self hash")
    unhashed = {key: value for key, value in payload.items() if key != "self_sha256"}
    measured = hashlib.sha256(_canonical_bytes(unhashed)).hexdigest()
    if measured != expected:
        raise PolicyError(f"policy artifact self hash mismatch: {measured} != {expected}")
    return measured


def assert_policy_admits_holdout(payload: Mapping[str, object]) -> None:
    if payload.get("schema") != POLICY_SCHEMA:
        raise PolicyError("holdout policy has the wrong schema")
    if payload.get("support_gate_passed") is not True:
        raise PolicyError("discovery support gate did not pass; holdout rewards stay unread")


def _repo_relpath(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as error:
        raise PolicyError(f"artifact is outside the registered repository: {path}") from error


def _assert_file_committed(*, repo_root: Path, path: Path, label: str) -> None:
    relpath = _repo_relpath(repo_root=repo_root, path=path)
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relpath],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    worktree_clean = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relpath],
        cwd=repo_root,
        check=False,
    )
    index_clean = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "HEAD", "--", relpath],
        cwd=repo_root,
        check=False,
    )
    if tracked.returncode != 0:
        raise PolicyError(f"{label} is not committed at HEAD")
    if worktree_clean.returncode != 0 or index_clean.returncode != 0:
        raise PolicyError(f"{label} differs from its committed HEAD bytes")


def _assert_registration_committed(repo_root: Path) -> None:
    for relpath in REGISTRATION_PATHS:
        path = repo_root / relpath
        _assert_file_committed(repo_root=repo_root, path=path, label=relpath)
    ledger = (repo_root / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    if ledger.count(f"| 2026-09-01 | {EXPERIMENT_ID} |") != 1:
        raise PolicyError("the committed exposure ledger does not contain exactly one experiment row")


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _state_distance(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(FEATURE_NAMES) or len(right) != len(FEATURE_NAMES):
        raise PolicyError("state distance received a vector outside the frozen feature contract")
    return sum(abs(a - b) for a, b in zip(left, right, strict=True)) / len(FEATURE_NAMES)


def decide(
    *,
    state: Sequence[float],
    memory: Sequence[Outcome],
    k: int,
    radius: float,
    exclude_group_id: str | None = None,
) -> Decision:
    """Choose ``STOP`` only under unanimous local non-positive support."""

    params = Hyperparameters(k=k, radius=radius)
    ranked = sorted(
        (
            (_state_distance(state, item.state), item)
            for item in memory
            if item.group_id != exclude_group_id
        ),
        key=lambda pair: (pair[0], pair[1].sample_id),
    )
    local = [(distance, item) for distance, item in ranked if distance <= params.radius]
    if len(local) < params.k:
        return Decision("ACQUIRE", "insufficient-local-support", (), (), ())
    selected = local[: params.k]
    ids = tuple(item.sample_id for _distance, item in selected)
    distances = tuple(distance for distance, _item in selected)
    advantages = tuple(item.acquisition_advantage for _distance, item in selected)
    if any(value > 0 for value in advantages):
        return Decision("ACQUIRE", "positive-return-neighbor", ids, distances, advantages)
    return Decision("STOP", "unanimous-nonpositive-local-return", ids, distances, advantages)


def evaluate(
    items: Sequence[Outcome],
    *,
    memory: Sequence[Outcome],
    params: Hyperparameters,
    exclude_own_group: bool = False,
) -> Evaluation:
    """Evaluate a policy using only the two responses logged for each item."""

    stopped: list[str] = []
    harmful: list[str] = []
    helpful: list[str] = []
    baseline_correct = 0
    policy_correct = 0
    for item in sorted(items, key=lambda value: value.sample_id):
        decision = decide(
            state=item.state,
            memory=memory,
            k=params.k,
            radius=params.radius,
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
    stopped_set = set(stopped)
    neutral = len(stopped_set - set(harmful) - set(helpful))
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


def _split_groups(
    items: Sequence[Outcome], *, seed: int
) -> tuple[tuple[Outcome, ...], tuple[Outcome, ...]]:
    """Deterministically assign whole utterance groups 70/30."""

    by_group: dict[str, list[Outcome]] = {}
    for item in items:
        by_group.setdefault(item.group_id, []).append(item)
    ordered_groups = sorted(
        by_group,
        key=lambda group: (_hash_text(f"{seed}:{group}"), group),
    )
    if len(ordered_groups) < 4:
        raise PolicyError("discovery needs at least four independent utterance groups")
    tune_group_count = max(1, min(len(ordered_groups) - 1, math.ceil(0.70 * len(ordered_groups))))
    tune_groups = set(ordered_groups[:tune_group_count])
    tune = tuple(sorted((x for x in items if x.group_id in tune_groups), key=lambda x: x.sample_id))
    gate = tuple(sorted((x for x in items if x.group_id not in tune_groups), key=lambda x: x.sample_id))
    return tune, gate


def _empty_evaluation(n: int = 0) -> Evaluation:
    return Evaluation(n, 0, n, 0, 0, 0, 0, 0, 0, (), (), ())


def fit_discovery(
    items: Sequence[Outcome],
    *,
    grid: Sequence[Hyperparameters] = DEFAULT_GRID,
    seed: int = DISCOVERY_SEED,
) -> FitResult:
    """Select on grouped discovery and pass a separate grouped support gate."""

    ordered = tuple(sorted(items, key=lambda item: item.sample_id))
    if len({item.sample_id for item in ordered}) != len(ordered):
        raise PolicyError("discovery contains duplicate sample ids")
    if not grid:
        raise PolicyError("the frozen candidate grid is empty")
    tune, gate = _split_groups(ordered, seed=seed)
    rows: list[dict[str, object]] = []
    candidates: list[tuple[Hyperparameters, Evaluation]] = []
    for params in sorted(set(grid)):
        metrics = evaluate(tune, memory=tune, params=params, exclude_own_group=True)
        admissible = metrics.harmful_stops == 0 and metrics.stopped >= 2
        rows.append(
            {
                "k": params.k,
                "radius": params.radius,
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

    # First maximize contacts saved with no discovery harm, then prefer the
    # more supported and tighter local rule.  The exact order is frozen.
    selected, tune_metrics = sorted(
        candidates,
        key=lambda pair: (
            -pair[1].contacts_saved,
            -pair[0].k,
            pair[0].radius,
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


def _evaluation_payload(metrics: Evaluation, *, include_ids: bool) -> dict[str, object]:
    payload = asdict(metrics)
    payload["delta_correct"] = metrics.delta_correct
    payload["contact_reduction_rate"] = metrics.contacts_saved / metrics.n if metrics.n else 0.0
    if not include_ids:
        for key in ("stopped_ids", "harmful_stop_ids", "helpful_stop_ids"):
            payload.pop(key)
    return payload


def memory_digest(items: Sequence[Outcome]) -> str:
    rows = [
        {
            "sample_id": item.sample_id,
            "group_id_sha256": _hash_text(item.group_id),
            "state": list(item.state),
            "direct_match": item.direct_match,
            "evidence_match": item.evidence_match,
        }
        for item in sorted(items, key=lambda value: value.sample_id)
    ]
    return hashlib.sha256(
        (json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()


def _unit(value: float) -> float:
    return min(1.0, max(0.0, value))


def pre_acquisition_state(*, replay, direct_parsed: bool) -> tuple[float, ...]:
    """Map frozen blend telemetry into the fixed task-agnostic state space."""

    cos1 = -1.0 if replay.cos_top1 is None else float(replay.cos_top1)
    cos2 = -1.0 if replay.cos_top2 is None else float(replay.cos_top2)
    fused_top1 = float(replay.fused_ranked[0][1]) if replay.fused_ranked else 0.0
    return (
        _unit((cos1 + 1.0) / 2.0),
        _unit((cos2 + 1.0) / 2.0),
        _unit((float(replay.cos_margin) + 2.0) / 4.0),
        _unit(fused_top1),
        _unit(float(replay.margin_top2)),
        _unit(float(replay.admitted_count) / 5.0),
        _unit(float(len(replay.selected_value_ids)) / 6.0),
        _unit(float(len(replay.supplied_per_target)) / 3.0),
        1.0 if direct_parsed else 0.0,
    )


# The functions below import the landed readers lazily.  Unit tests therefore
# exercise the entire policy without opening any experiment artifact.


def _load_cell(*, population_id: str, repo_root: Path, data_root: Path):
    from . import contrast_fewshot_preanalysis as cf
    from . import dev500_confirmatory_read as d5

    bundle = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    populations = d5.load_populations(repo_root)
    pin = next(item for item in cf.CELL_PINS if item.population_id == population_id)
    cell = cf.load_cell_population(
        pin=pin,
        bundle=bundle,
        populations=populations,
        data_root=data_root,
        repo_root=repo_root,
    )
    replays, gate = cf.replay_population(cell, bundle)
    if not gate["retain_dispatch_gate_passed"] or not gate["supply_gate_passed"]:
        raise PolicyError(f"{population_id}: frozen-cell replay fidelity gate failed")
    return cell, replays, gate


def _outcomes_from_cell(cell, replays: Mapping[str, object]) -> tuple[Outcome, ...]:
    from . import dev100_damage_channel_analysis as dc

    items: list[Outcome] = []
    for sample_id in cell.sample_ids:
        replay = replays[sample_id]
        if not replay.dispatched:
            continue
        direct_text = cell.inputs.direct_texts[sample_id]
        evidence_text = cell.inputs.evidence_texts.get(sample_id)
        if evidence_text is None or cell.final_texts[sample_id] != evidence_text:
            raise PolicyError(f"{sample_id}: dispatched final response is not its evidence response")
        gold = cell.inputs.gold_by_sample[sample_id]
        direct = dc.score_response(gold, direct_text)
        evidence = dc.score_response(gold, evidence_text)
        items.append(
            Outcome(
                sample_id=sample_id,
                group_id=str(gold.utterance_id),
                state=pre_acquisition_state(
                    replay=replay, direct_parsed=bool(direct["parsed"])
                ),
                direct_match=1 if direct["correct"] else 0,
                evidence_match=1 if evidence["correct"] else 0,
            )
        )
    return tuple(sorted(items, key=lambda item: item.sample_id))


def _fit_payload(
    *,
    items: Sequence[Outcome],
    result: FitResult,
    source_hashes: Mapping[str, str],
    replay_gate: Mapping[str, object],
) -> dict[str, object]:
    selected = None if result.selected is None else asdict(result.selected)
    return {
        "schema": POLICY_SCHEMA,
        "fit_report_schema": FIT_REPORT_SCHEMA,
        "policy_id": POLICY_ID,
        "feature_contract": FEATURE_CONTRACT,
        "feature_names": list(FEATURE_NAMES),
        "scope": {
            "action_space": ["ACQUIRE", "STOP"],
            "default_action": "ACQUIRE",
            "may_widen_dispatch": False,
            "eligible_population": "locked-v1 baseline-dispatched trajectories only",
            "counterfactual_imputation": "forbidden; both logged responses are required",
        },
        "discovery": {
            "population": "DEV-100-ROUND4",
            "seed": DISCOVERY_SEED,
            "eligible_dispatched_n": len(items),
            "sample_identity_sha256": _hash_text("\n".join(item.sample_id for item in items) + "\n"),
            "utterance_group_identity_sha256": _hash_text(
                "\n".join(sorted({item.group_id for item in items})) + "\n"
            ),
            "source_hashes": dict(sorted(source_hashes.items())),
            "replay_gate": dict(replay_gate),
        },
        "candidate_grid": [asdict(params) for params in DEFAULT_GRID],
        "selection_rule": (
            "grouped 70/30 discovery; tune candidates require >=2 STOP and zero harmful STOP; "
            "maximize contacts saved, then larger k, then smaller radius; the separate 30% "
            "support gate requires zero harmful STOP and max(2, ceil(10% of gate n)) STOP"
        ),
        "selected": selected,
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
            "is committed before the evaluate command starts"
        ),
        "claim_scope": (
            "iteration-tier retrospective discovery artifact; no baseline revision, no test claim, "
            "no confirmatory or generalization claim"
        ),
    }


def fit(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    from .dev100_reviewer_audit import arm_offline_guard

    _assert_registration_committed(repo_root)
    attempts = arm_offline_guard()
    cell, replays, replay_gate = _load_cell(
        population_id="DEV-100-ROUND4", repo_root=repo_root, data_root=data_root
    )
    items = _outcomes_from_cell(cell, replays)
    result = fit_discovery(items)
    payload = _fit_payload(
        items=items,
        result=result,
        source_hashes=cell.artifact_hashes,
        replay_gate=replay_gate,
    )
    payload["offline_guard"] = {
        "outbound_connection_attempts": attempts.count,
        "targets": attempts.targets,
    }
    return with_self_hash(payload)


def _policy_params(policy: Mapping[str, object]) -> Hyperparameters:
    selected = policy.get("selected")
    if not isinstance(selected, Mapping):
        raise PolicyError("passed policy has no selected hyperparameters")
    return Hyperparameters(k=int(selected["k"]), radius=float(selected["radius"]))


def _score_response_map(cell, responses: Mapping[str, str]):
    from ..reproduction.slurp_scoring import parse_slu_response, score_slu

    from .matching_vs_extraction_read import SlurpScored

    match: dict[str, int] = {}
    slot_f1: dict[str, float] = {}
    parsed_map: dict[str, bool] = {}
    scores: dict[str, object] = {}
    for sample_id, text in responses.items():
        gold = cell.inputs.gold_by_sample[sample_id]
        scenario, action, entities, parsed = parse_slu_response(text)
        score = score_slu(
            gold_scenario=gold.scenario,
            gold_action=gold.action,
            gold_entities=gold.entities,
            predicted_scenario=scenario,
            predicted_action=action,
            predicted_entities=tuple(entities),
        )
        match[sample_id] = 1 if score.scenario_action_exact == 1.0 else 0
        slot_f1[sample_id] = float(score.slot_f1_exact[2])
        parsed_map[sample_id] = bool(parsed)
        scores[sample_id] = score
    return SlurpScored(match=match, slot_f1=slot_f1, parsed=parsed_map, scores=scores)


def _bootstrap_primary(
    ids: Sequence[str], baseline: Mapping[str, int], policy: Mapping[str, int]
) -> dict[str, object]:
    from .dev100_reviewer_audit import bootstrap_gain

    return dict(
        bootstrap_gain(
            sample_ids=ids,
            m0=baseline,
            blend=policy,
            n_replicates=10_000,
            seed=20260807,
        )
    )


def evaluate_holdout(
    *,
    policy: Mapping[str, object],
    repo_root: Path,
    data_root: Path,
) -> dict[str, object]:
    """Read NEW400 only after a committed, passed discovery policy exists."""

    from . import matching_vs_extraction_read as mve
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
        raise PolicyError("reloaded discovery memory does not match the frozen policy artifact")
    if dict(sorted(memory_cell.artifact_hashes.items())) != policy["discovery"]["source_hashes"]:
        raise PolicyError("discovery source hashes moved after policy freeze")

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
            state=item.state,
            memory=memory,
            k=params.k,
            radius=params.radius,
        )
        for item in eligible
    }
    baseline_responses = dict(holdout_cell.final_texts)
    policy_responses = dict(holdout_cell.final_texts)
    for item in eligible:
        if decisions[item.sample_id].action == "STOP":
            policy_responses[item.sample_id] = holdout_cell.inputs.direct_texts[item.sample_id]

    baseline_scored = _score_response_map(holdout_cell, baseline_responses)
    policy_scored = _score_response_map(holdout_cell, policy_responses)
    population_ids = tuple(holdout_cell.sample_ids)
    baseline_profile = mve.slurp_extraction_block(
        scored=baseline_scored, sample_ids=population_ids
    )
    policy_profile = mve.slurp_extraction_block(
        scored=policy_scored, sample_ids=population_ids
    )
    primary_bootstrap = _bootstrap_primary(
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
            "retrospective held-out replication on already-exposed devel data; a pass is a "
            "Stage-2 training-free control-plane contribution, not a test, confirmatory, "
            "generality, or Stage-3 claim"
        ),
    }
    payload["offline_guard"] = {
        "outbound_connection_attempts": attempts.count,
        "targets": attempts.targets,
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
            label="holdout policy artifact",
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
    "FEATURE_NAMES",
    "FIT_REPORT_SCHEMA",
    "HOLDOUT_REPORT_SCHEMA",
    "POLICY_SCHEMA",
    "Decision",
    "Evaluation",
    "FitResult",
    "Hyperparameters",
    "Outcome",
    "PolicyError",
    "assert_policy_admits_holdout",
    "assert_self_hash",
    "decide",
    "evaluate",
    "evaluate_holdout",
    "fit",
    "fit_discovery",
    "memory_digest",
    "pre_acquisition_state",
    "with_self_hash",
]
