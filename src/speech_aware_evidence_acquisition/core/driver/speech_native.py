"""Speech-native GPU-profile flight through the existing ``saea-driver``.

This is a driver module, not a standalone experiment script. It reuses the
repository's receipt-pinned session, frozen gate, attempt accounting,
speech-feature client, bounded matcher dispatcher, resource sampler, and
trace machinery. Profile flights are engineering-only: response text is
hashed in process and never copied into the profile receipt.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...contracts import ExecutionPlan
from ...data.lock import asset_dir, data_root, load_lock, umbrella_lock_path
from ...e0.artifacts import REPO_ROOT
from ...rails import FrozenCoreClient, build_payload_binding
from ...rails.probes.pslu_flight import (
    KeyCardV1,
    SpeechNativeMatchTask,
    load_speech_native_engineering_gate,
    parse_grounded_query_state,
    run_speech_native_match_tasks,
)
from ..attempts import AttemptStore
from ..base import TRANSPORTS
from ..config import (
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_lock_key,
    model_materialization_root,
    protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from ..resources import resolve_resource_sampler
from ..session import (
    SessionError,
    SessionReceipt,
    _model_file_argv,
    _pinned_model_files,
    attach_session,
    load_runtime_receipt,
    start_session,
    stop_session,
    write_session_receipt,
)
from .run import load_split
from .smoke import _server_args, _server_env, _write_inference_process_audit

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ORDER_BUILDERS = {
    "canonical": lambda cards: cards,
    "reverse": lambda cards: tuple(reversed(cards)),
    "rotate-1": lambda cards: cards[1:] + cards[:1],
    "rotate-7": lambda cards: cards[7:] + cards[:7],
}
_OOM_MARKERS = (
    "out of memory",
    "cuda error out of memory",
    "failed to allocate",
    "cuda_malloc failed",
)
_HOST_SPILL_MARKERS = (
    "offloaded to cpu",
    "offloading layer to cpu",
    "host buffer fallback",
)
_RUNAWAY_MARKERS = ("truncated = 1", "context shift", "slot context shift")
_SPEECH_NATIVE_KEY_IDS = frozenset(f"K{index:03d}" for index in range(1, 19))
_M6_SCHEMA_V2_POLICY_ID = "knowledge-grounded-semantic-refinement-schema-v2"
_M6_SCHEMA_V3_POLICY_ID = "knowledge-grounded-semantic-refinement-schema-v3"
_M6_AGGREGATOR_ID = "grounded-refined-primary-fallback-v1"
_M6_SUCCESS_ACTIONS = (
    "match:speech-only-primary",
    "retrieve:speech-only",
    "build:grounded-query-state",
    "retrieve:speech-plus-grounded-state",
    "verify:speech-plus-grounded-state",
    "select:refined-primary-fallback",
)
_SPEAKER_FOLD_POLICY_ID = "speaker-grouped-3fold-sha256-load-balanced-v1"
_CONTEXTUAL_ACTION_IDS = (
    "primary",
    "m3-unanimous-primary-fallback",
    "m3-majority-primary-fallback",
    "canonical-primary-fallback",
    "reverse-primary-fallback",
    "rotate-primary-fallback",
)


class SpeechNativeProfileError(RuntimeError):
    """A profile input, flight, or receipt failed closed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(document: object) -> str:
    raw = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_training_free_trajectories(
    trajectories: Sequence[Mapping[str, str | None]],
) -> tuple[Mapping[str, str | None], ...]:
    required = {
        "speaker_id",
        "gold_key_id",
        "primary_key_id",
        "canonical_key_id",
        "reverse_key_id",
        "rotate_key_id",
    }
    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError(
            "training-free policy search requires at least one trajectory"
        )
    for trajectory in frozen:
        if (
            set(trajectory) != required
            or not isinstance(trajectory.get("speaker_id"), str)
            or not trajectory.get("speaker_id")
            or not isinstance(trajectory.get("gold_key_id"), str)
        ):
            raise SpeechNativeProfileError(
                "training-free policy trajectory is malformed"
            )
        if any(
            value is not None and not isinstance(value, str)
            for key, value in trajectory.items()
            if key != "speaker_id"
        ):
            raise SpeechNativeProfileError(
                "training-free policy trajectory contains a malformed key id"
            )
    if len({str(item["speaker_id"]) for item in frozen}) < 3:
        raise SpeechNativeProfileError(
            "training-free policy search requires at least three speakers"
        )
    return frozen


def _speaker_grouped_fold_assignments(
    trajectories: Sequence[Mapping[str, str | None]],
) -> dict[str, str]:
    """Assign intact speaker groups to three deterministic balanced folds."""

    counts = Counter(str(item["speaker_id"]) for item in trajectories)
    ranked = sorted(
        counts,
        key=lambda speaker_id: (
            -counts[speaker_id],
            hashlib.sha256(speaker_id.encode("utf-8")).hexdigest(),
            speaker_id,
        ),
    )
    sizes = [0, 0, 0]
    assignments: dict[str, str] = {}
    for speaker_id in ranked:
        fold_index = min(range(3), key=lambda index: (sizes[index], index))
        assignments[speaker_id] = f"fold-{fold_index}"
        sizes[fold_index] += counts[speaker_id]
    return assignments


def _speaker_fold_metrics(
    trajectories: Sequence[Mapping[str, str | None]],
    *,
    assignments: Mapping[str, str],
    predictions: Sequence[str | None],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for fold_index in range(3):
        fold_id = f"fold-{fold_index}"
        indices = [
            index
            for index, trajectory in enumerate(trajectories)
            if assignments[str(trajectory["speaker_id"])] == fold_id
        ]
        if not indices:
            raise SpeechNativeProfileError(
                "speaker-grouped policy analysis produced an empty fold"
            )
        correct = sum(
            predictions[index] == trajectories[index]["gold_key_id"]
            for index in indices
        )
        primary_correct = sum(
            trajectories[index]["primary_key_id"]
            == trajectories[index]["gold_key_id"]
            for index in indices
        )
        rows.append(
            {
                "fold_id": fold_id,
                "speaker_count": len(
                    {str(trajectories[index]["speaker_id"]) for index in indices}
                ),
                "count": len(indices),
                "correct": correct,
                "accuracy": correct / len(indices),
                "primary_correct": primary_correct,
                "primary_accuracy": primary_correct / len(indices),
                "correct_delta_vs_primary": correct - primary_correct,
            }
        )
    return rows


def _m3_aggregate(
    trajectory: Mapping[str, str | None], mode: str
) -> str | None:
    primary = trajectory["primary_key_id"]
    votes = [
        trajectory["canonical_key_id"],
        trajectory["reverse_key_id"],
        trajectory["rotate_key_id"],
    ]
    valid = [vote for vote in votes if vote is not None]
    if mode == "majority":
        counts = Counter(valid)
        return next((vote for vote, count in counts.items() if count >= 2), primary)
    if mode == "unanimous":
        return valid[0] if len(valid) == 3 and len(set(valid)) == 1 else primary
    raise SpeechNativeProfileError(f"unknown training-free aggregate mode {mode!r}")


def _evaluate_training_free_agent_policies(
    trajectories: Sequence[Mapping[str, str | None]],
) -> list[dict[str, object]]:
    """Enumerate preregistered controller rules over full action logs.

    This is an offline, model-free policy evaluator. Gold is used only as the
    reward after every frozen-core action has already been recorded. The
    returned rules update no model, prompt, retriever, or verifier parameter.
    """

    frozen = _validate_training_free_trajectories(trajectories)
    assignments = _speaker_grouped_fold_assignments(frozen)

    def aggregate(trajectory: Mapping[str, str | None], mode: str) -> str | None:
        return _m3_aggregate(trajectory, mode)

    policy_specs = (
        ("trigger-never__primary-v1", "never", "primary"),
        (
            "trigger-disagreement__m3-majority-primary-v1",
            "disagreement",
            "majority",
        ),
        (
            "trigger-disagreement__m3-unanimous-primary-v1",
            "disagreement",
            "unanimous",
        ),
        ("trigger-always__m3-majority-primary-v1", "always", "majority"),
        ("trigger-always__m3-unanimous-primary-v1", "always", "unanimous"),
    )
    rows: list[dict[str, object]] = []
    for policy_id, trigger, mode in policy_specs:
        correct = 0
        wrong_to_correct = 0
        correct_to_wrong = 0
        branch_actions = 0
        predictions: list[str | None] = []
        for trajectory in frozen:
            primary = trajectory["primary_key_id"]
            gold = trajectory["gold_key_id"]
            run_branch = trigger == "always" or (
                trigger == "disagreement"
                and primary != trajectory["canonical_key_id"]
            )
            branch_actions += int(run_branch)
            prediction = (
                primary
                if mode == "primary" or not run_branch
                else aggregate(trajectory, mode)
            )
            predictions.append(prediction)
            primary_correct = primary == gold
            final_correct = prediction == gold
            correct += int(final_correct)
            wrong_to_correct += int(not primary_correct and final_correct)
            correct_to_wrong += int(primary_correct and not final_correct)
        speaker_folds = _speaker_fold_metrics(
            frozen,
            assignments=assignments,
            predictions=predictions,
        )
        rows.append(
            {
                "policy_id": policy_id,
                "correct": correct,
                "count": len(frozen),
                "accuracy": correct / len(frozen),
                "wrong_to_correct_vs_primary": wrong_to_correct,
                "correct_to_wrong_vs_primary": correct_to_wrong,
                "branch_action_count": branch_actions,
                "branch_action_rate": branch_actions / len(frozen),
                "speaker_fold_policy_id": _SPEAKER_FOLD_POLICY_ID,
                "speaker_folds": speaker_folds,
                "positive_delta_fold_count": sum(
                    int(fold["correct_delta_vs_primary"] > 0)
                    for fold in speaker_folds
                ),
                "nonnegative_delta_fold_count": sum(
                    int(fold["correct_delta_vs_primary"] >= 0)
                    for fold in speaker_folds
                ),
                "worst_fold_accuracy": min(
                    float(fold["accuracy"]) for fold in speaker_folds
                ),
                "worst_fold_delta_vs_primary": min(
                    int(fold["correct_delta_vs_primary"])
                    for fold in speaker_folds
                ),
            }
        )
    return rows


def _contextual_state_id(trajectory: Mapping[str, str | None]) -> str:
    primary = trajectory["primary_key_id"]
    canonical = trajectory["canonical_key_id"]
    votes = [
        canonical,
        trajectory["reverse_key_id"],
        trajectory["rotate_key_id"],
    ]
    valid = [vote for vote in votes if vote is not None]
    counts = Counter(valid)
    majority = next((vote for vote, count in counts.items() if count >= 2), None)
    if len(valid) == 3 and len(set(valid)) == 1:
        consensus = "unanimous"
    elif majority is not None:
        consensus = "majority"
    elif valid:
        consensus = "split"
    else:
        consensus = "missing"
    primary_canonical = (
        "missing"
        if canonical is None
        else "same"
        if canonical == primary
        else "different"
    )
    primary_majority = (
        "none" if majority is None else "same" if majority == primary else "different"
    )
    return (
        f"primary-canonical-{primary_canonical}__m3-{consensus}__"
        f"primary-majority-{primary_majority}__valid-{len(valid)}"
    )


def _contextual_action_predictions(
    trajectory: Mapping[str, str | None],
) -> dict[str, str | None]:
    primary = trajectory["primary_key_id"]
    return {
        "primary": primary,
        "m3-unanimous-primary-fallback": _m3_aggregate(trajectory, "unanimous"),
        "m3-majority-primary-fallback": _m3_aggregate(trajectory, "majority"),
        "canonical-primary-fallback": trajectory["canonical_key_id"] or primary,
        "reverse-primary-fallback": trajectory["reverse_key_id"] or primary,
        "rotate-primary-fallback": trajectory["rotate_key_id"] or primary,
    }


def _evaluate_training_free_contextual_policy(
    trajectories: Sequence[Mapping[str, str | None]],
) -> dict[str, object]:
    """Cross-fit a finite observable-state action policy without model updates.

    Speaker groups define three folds. For each held-out fold, state-to-action
    choices are learned only from the other two folds. A non-primary action
    requires at least three training examples in the state and a strict reward
    gain over the primary action; otherwise the conservative primary action is
    used. The per-query action oracle is diagnostic headroom, never a policy.
    """

    frozen = _validate_training_free_trajectories(trajectories)
    assignments = _speaker_grouped_fold_assignments(frozen)
    states = [_contextual_state_id(item) for item in frozen]
    action_predictions = [_contextual_action_predictions(item) for item in frozen]
    oof_predictions: list[str | None] = [None] * len(frozen)
    fold_rules: dict[str, list[dict[str, object]]] = {}
    oof_action_counts: Counter[str] = Counter()

    for fold_index in range(3):
        fold_id = f"fold-{fold_index}"
        train_indices = [
            index
            for index, item in enumerate(frozen)
            if assignments[str(item["speaker_id"])] != fold_id
        ]
        test_indices = [
            index
            for index, item in enumerate(frozen)
            if assignments[str(item["speaker_id"])] == fold_id
        ]
        rules: dict[str, str] = {}
        audit_rules: list[dict[str, object]] = []
        for state_id in sorted(set(states[index] for index in train_indices)):
            state_indices = [index for index in train_indices if states[index] == state_id]
            correct_by_action = {
                action_id: sum(
                    action_predictions[index][action_id]
                    == frozen[index]["gold_key_id"]
                    for index in state_indices
                )
                for action_id in _CONTEXTUAL_ACTION_IDS
            }
            primary_correct = correct_by_action["primary"]
            best_correct = max(correct_by_action.values())
            action_id = "primary"
            if len(state_indices) >= 3 and best_correct > primary_correct:
                action_id = next(
                    candidate
                    for candidate in _CONTEXTUAL_ACTION_IDS
                    if correct_by_action[candidate] == best_correct
                )
            rules[state_id] = action_id
            audit_rules.append(
                {
                    "state_id": state_id,
                    "train_count": len(state_indices),
                    "selected_action_id": action_id,
                    "selected_action_correct": correct_by_action[action_id],
                    "primary_correct": primary_correct,
                }
            )
        fold_rules[fold_id] = audit_rules
        for index in test_indices:
            action_id = rules.get(states[index], "primary")
            oof_action_counts[action_id] += 1
            oof_predictions[index] = action_predictions[index][action_id]

    speaker_folds = _speaker_fold_metrics(
        frozen,
        assignments=assignments,
        predictions=oof_predictions,
    )
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )
    correct = sum(
        prediction == item["gold_key_id"]
        for prediction, item in zip(oof_predictions, frozen, strict=True)
    )
    wrong_to_correct = sum(
        item["primary_key_id"] != item["gold_key_id"]
        and prediction == item["gold_key_id"]
        for prediction, item in zip(oof_predictions, frozen, strict=True)
    )
    correct_to_wrong = sum(
        item["primary_key_id"] == item["gold_key_id"]
        and prediction != item["gold_key_id"]
        for prediction, item in zip(oof_predictions, frozen, strict=True)
    )
    state_action_support: list[dict[str, object]] = []
    reward_spread_state_count = 0
    prediction_variable_state_count = 0
    for state_id in sorted(set(states)):
        indices = [index for index, state in enumerate(states) if state == state_id]
        correct_by_action = {
            action_id: sum(
                action_predictions[index][action_id] == frozen[index]["gold_key_id"]
                for index in indices
            )
            for action_id in _CONTEXTUAL_ACTION_IDS
        }
        reward_spread = max(correct_by_action.values()) - min(correct_by_action.values())
        reward_spread_state_count += int(reward_spread > 0)
        prediction_variable_state_count += int(
            any(
                len(
                    {
                        action_predictions[index][action_id]
                        for action_id in _CONTEXTUAL_ACTION_IDS
                    }
                )
                > 1
                for index in indices
            )
        )
        state_action_support.append(
            {
                "state_id": state_id,
                "count": len(indices),
                "correct_by_action": correct_by_action,
                "reward_spread": reward_spread,
            }
        )
    action_oracle_correct = sum(
        any(
            prediction == item["gold_key_id"]
            for prediction in action_predictions[index].values()
        )
        for index, item in enumerate(frozen)
    )
    return {
        "policy_id": "speaker-grouped-oof-observable-state-action-v1",
        "speaker_fold_policy_id": _SPEAKER_FOLD_POLICY_ID,
        "count": len(frozen),
        "correct": correct,
        "accuracy": correct / len(frozen),
        "primary_correct": primary_correct,
        "primary_accuracy": primary_correct / len(frozen),
        "wrong_to_correct_vs_primary": wrong_to_correct,
        "correct_to_wrong_vs_primary": correct_to_wrong,
        "positive_delta_fold_count": sum(
            int(fold["correct_delta_vs_primary"] > 0) for fold in speaker_folds
        ),
        "nonnegative_delta_fold_count": sum(
            int(fold["correct_delta_vs_primary"] >= 0) for fold in speaker_folds
        ),
        "worst_fold_accuracy": min(float(fold["accuracy"]) for fold in speaker_folds),
        "worst_fold_delta_vs_primary": min(
            int(fold["correct_delta_vs_primary"]) for fold in speaker_folds
        ),
        "oof_action_counts": dict(sorted(oof_action_counts.items())),
        "speaker_folds": [
            {**fold, "learned_state_actions": fold_rules[str(fold["fold_id"])]}
            for fold in speaker_folds
        ],
        "speaker_fold_assignments": [
            {"speaker_id": speaker_id, "fold_id": assignments[speaker_id]}
            for speaker_id in sorted(assignments)
        ],
        "state_action_support": state_action_support,
        "prediction_variable_state_count": prediction_variable_state_count,
        "reward_spread_state_count": reward_spread_state_count,
        "action_oracle_correct": action_oracle_correct,
        "action_oracle_headroom_vs_primary": action_oracle_correct - primary_correct,
        "action_oracle_status": "diagnostic-only-not-an-admissible-controller",
    }


_EPISODIC_REQUIRED_FIELDS = {
    "sample_id",
    "speaker_id",
    "gold_key_id",
    "primary_key_id",
    "canonical_key_id",
    "reverse_key_id",
    "rotate_key_id",
    "canonical_top_key_ids",
    "canonical_verifier_scores",
    "primary_calls",
    "canonical_calls",
    "reverse_calls",
    "rotate_calls",
}
_EPISODIC_STATE_WEIGHTS = (2, 2, 1, 1, 1, 1, 1)
_EPISODIC_NEIGHBOR_COUNT = 9
_EPISODIC_MIN_SUPPORT = 5
_EPISODIC_MAX_DISTANCE = 3
_EPISODIC_MIN_NET_GAIN = 2
_EPISODIC_MAX_HARM = 0


def _validate_episodic_trajectories(
    trajectories: Sequence[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError(
            "episodic policy search requires at least one trajectory"
        )
    for trajectory in frozen:
        if set(trajectory) != _EPISODIC_REQUIRED_FIELDS:
            raise SpeechNativeProfileError("episodic policy trajectory is malformed")
        if any(
            not isinstance(trajectory.get(field), str) or not trajectory.get(field)
            for field in ("sample_id", "speaker_id", "gold_key_id")
        ):
            raise SpeechNativeProfileError(
                "episodic policy trajectory identity is malformed"
            )
        if any(
            value is not None and not isinstance(value, str)
            for value in (
                trajectory.get("primary_key_id"),
                trajectory.get("canonical_key_id"),
                trajectory.get("reverse_key_id"),
                trajectory.get("rotate_key_id"),
            )
        ):
            raise SpeechNativeProfileError(
                "episodic policy trajectory action prediction is malformed"
            )
        top_ids = trajectory.get("canonical_top_key_ids")
        if (
            not isinstance(top_ids, (list, tuple))
            or not all(isinstance(key_id, str) and key_id for key_id in top_ids)
            or len(set(top_ids)) != len(top_ids)
        ):
            raise SpeechNativeProfileError(
                "episodic policy trajectory top-key list is malformed"
            )
        scores = trajectory.get("canonical_verifier_scores")
        if not isinstance(scores, Mapping):
            raise SpeechNativeProfileError(
                "episodic policy trajectory verifier scores are malformed"
            )
        for key_id, raw_score in scores.items():
            if (
                not isinstance(key_id, str)
                or not isinstance(raw_score, (list, tuple))
                or len(raw_score) != 2
                or not isinstance(raw_score[0], bool)
                or isinstance(raw_score[1], bool)
                or not isinstance(raw_score[1], (int, float))
                or not -1.0 <= float(raw_score[1]) <= 100.0
            ):
                raise SpeechNativeProfileError(
                    "episodic policy trajectory verifier score is malformed"
                )
        for field in (
            "primary_calls",
            "canonical_calls",
            "reverse_calls",
            "rotate_calls",
        ):
            value = trajectory.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise SpeechNativeProfileError(
                    "episodic policy trajectory contact cost is malformed"
                )
    return frozen


def _episodic_state(trajectory: Mapping[str, object]) -> tuple[str, ...]:
    primary = trajectory["primary_key_id"]
    canonical = trajectory["canonical_key_id"]
    top_ids = tuple(trajectory["canonical_top_key_ids"])
    scores = trajectory["canonical_verifier_scores"]
    assert isinstance(scores, Mapping)
    primary_rank = (
        str(top_ids.index(primary) + 1) if primary is not None and primary in top_ids else "0"
    )
    parsed_scores = {
        str(key_id): (bool(raw[0]), float(raw[1]))
        for key_id, raw in scores.items()
    }
    compatible_count = sum(int(value[0]) for value in parsed_scores.values())
    selected = parsed_scores.get(str(canonical)) if canonical is not None else None
    selected_compatible = (
        "missing" if selected is None else "yes" if selected[0] else "no"
    )
    if selected is None:
        margin_bucket = "missing"
    else:
        comparison = [
            value[1]
            for key_id, value in parsed_scores.items()
            if key_id != canonical and value[0] == selected[0]
        ]
        margin = selected[1] - max(comparison) if comparison else 100.0
        margin_bucket = "tie" if margin <= 0 else "narrow" if margin <= 10 else "wide"
    return (
        str(primary),
        str(canonical),
        "same" if primary == canonical else "different",
        primary_rank,
        str(min(compatible_count, 3)),
        selected_compatible,
        margin_bucket,
    )


def _episodic_distance(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    return sum(
        weight * int(left_value != right_value)
        for weight, left_value, right_value in zip(
            _EPISODIC_STATE_WEIGHTS, left, right, strict=True
        )
    )


def _episodic_action_contacts(
    trajectory: Mapping[str, object], action_id: str
) -> int:
    initial = int(trajectory["primary_calls"]) + int(trajectory["canonical_calls"])
    if action_id in {"primary", "canonical-primary-fallback"}:
        return initial
    return initial + int(trajectory["reverse_calls"]) + int(
        trajectory["rotate_calls"]
    )


def _evaluate_training_free_episodic_policy(
    trajectories: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Cross-fit a conservative non-parametric external action policy.

    The memory contains only structured runtime telemetry and complete
    discovery action outcomes. For each held-out speaker fold, the policy
    retrieves nearby training states, estimates every recorded action's paired
    advantage over the primary action, and permits a non-primary action only
    with at least five neighbors, net gain of two, and zero observed harm. It
    never modifies model logits, weights, prompts, or speech features.
    """

    frozen = _validate_episodic_trajectories(trajectories)
    assignments = _speaker_grouped_fold_assignments(frozen)
    states = [_episodic_state(item) for item in frozen]
    action_predictions = [_contextual_action_predictions(item) for item in frozen]
    oof_predictions: list[str | None] = [None] * len(frozen)
    oof_contacts = [0] * len(frozen)
    oof_action_counts: Counter[str] = Counter()
    memory_audit: list[dict[str, object]] = []

    for fold_index in range(3):
        fold_id = f"fold-{fold_index}"
        train_indices = [
            index
            for index, item in enumerate(frozen)
            if assignments[str(item["speaker_id"])] != fold_id
        ]
        test_indices = [
            index
            for index, item in enumerate(frozen)
            if assignments[str(item["speaker_id"])] == fold_id
        ]
        for index in test_indices:
            ranked = sorted(
                (
                    (_episodic_distance(states[index], states[train_index]), train_index)
                    for train_index in train_indices
                ),
                key=lambda item: (
                    item[0],
                    str(frozen[item[1]]["sample_id"]),
                ),
            )
            neighbors = [
                train_index
                for distance, train_index in ranked
                if distance <= _EPISODIC_MAX_DISTANCE
            ][:_EPISODIC_NEIGHBOR_COUNT]
            selected_action = "primary"
            selected_rank = (-1, -1, float("-inf"))
            action_audit: list[dict[str, object]] = []
            for action_id in _CONTEXTUAL_ACTION_IDS:
                helpful = sum(
                    action_predictions[neighbor]["primary"]
                    != frozen[neighbor]["gold_key_id"]
                    and action_predictions[neighbor][action_id]
                    == frozen[neighbor]["gold_key_id"]
                    for neighbor in neighbors
                )
                harmful = sum(
                    action_predictions[neighbor]["primary"]
                    == frozen[neighbor]["gold_key_id"]
                    and action_predictions[neighbor][action_id]
                    != frozen[neighbor]["gold_key_id"]
                    for neighbor in neighbors
                )
                net_gain = helpful - harmful
                mean_contacts = (
                    sum(
                        _episodic_action_contacts(frozen[neighbor], action_id)
                        for neighbor in neighbors
                    )
                    / len(neighbors)
                    if neighbors
                    else math.inf
                )
                action_audit.append(
                    {
                        "action_id": action_id,
                        "support": len(neighbors),
                        "helpful": helpful,
                        "harmful": harmful,
                        "net_gain": net_gain,
                        "mean_contacts": mean_contacts,
                    }
                )
                admissible = (
                    action_id != "primary"
                    and len(neighbors) >= _EPISODIC_MIN_SUPPORT
                    and net_gain >= _EPISODIC_MIN_NET_GAIN
                    and harmful <= _EPISODIC_MAX_HARM
                )
                candidate_rank = (net_gain, -harmful, -mean_contacts)
                if admissible and candidate_rank > selected_rank:
                    selected_action = action_id
                    selected_rank = candidate_rank
            oof_action_counts[selected_action] += 1
            oof_predictions[index] = action_predictions[index][selected_action]
            oof_contacts[index] = _episodic_action_contacts(
                frozen[index], selected_action
            )
            memory_audit.append(
                {
                    "sample_id": frozen[index]["sample_id"],
                    "fold_id": fold_id,
                    "selected_action_id": selected_action,
                    "neighbor_count": len(neighbors),
                    "nearest_distance": ranked[0][0] if ranked else None,
                    "action_estimates": action_audit,
                }
            )

    speaker_folds = _speaker_fold_metrics(
        frozen,
        assignments=assignments,
        predictions=oof_predictions,
    )
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )
    correct = sum(
        prediction == item["gold_key_id"]
        for prediction, item in zip(oof_predictions, frozen, strict=True)
    )
    wrong_to_correct = sum(
        item["primary_key_id"] != item["gold_key_id"]
        and prediction == item["gold_key_id"]
        for prediction, item in zip(oof_predictions, frozen, strict=True)
    )
    correct_to_wrong = sum(
        item["primary_key_id"] == item["gold_key_id"]
        and prediction != item["gold_key_id"]
        for prediction, item in zip(oof_predictions, frozen, strict=True)
    )
    return {
        "policy_id": "speaker-grouped-oof-episodic-action-advantage-v2",
        "speaker_fold_policy_id": _SPEAKER_FOLD_POLICY_ID,
        "count": len(frozen),
        "correct": correct,
        "accuracy": correct / len(frozen),
        "primary_correct": primary_correct,
        "primary_accuracy": primary_correct / len(frozen),
        "wrong_to_correct_vs_primary": wrong_to_correct,
        "correct_to_wrong_vs_primary": correct_to_wrong,
        "positive_delta_fold_count": sum(
            int(fold["correct_delta_vs_primary"] > 0) for fold in speaker_folds
        ),
        "nonnegative_delta_fold_count": sum(
            int(fold["correct_delta_vs_primary"] >= 0) for fold in speaker_folds
        ),
        "worst_fold_delta_vs_primary": min(
            int(fold["correct_delta_vs_primary"]) for fold in speaker_folds
        ),
        "oof_action_counts": dict(sorted(oof_action_counts.items())),
        "mean_contacts": sum(oof_contacts) / len(frozen),
        "speaker_folds": speaker_folds,
        "memory_policy": {
            "neighbor_count": _EPISODIC_NEIGHBOR_COUNT,
            "minimum_support": _EPISODIC_MIN_SUPPORT,
            "maximum_state_distance": _EPISODIC_MAX_DISTANCE,
            "minimum_net_gain": _EPISODIC_MIN_NET_GAIN,
            "maximum_observed_harm": _EPISODIC_MAX_HARM,
            "state_weights": list(_EPISODIC_STATE_WEIGHTS),
        },
        "memory_audit": sorted(memory_audit, key=lambda item: str(item["sample_id"])),
    }


def _require_string(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise SpeechNativeProfileError(f"profile config {key} must be a non-empty string")
    return value


def _require_positive_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SpeechNativeProfileError(f"profile config {key} must be a positive integer")
    return value


def _load_binding_document(path: Path, expected_sha256: str) -> dict[str, object]:
    if _SHA256.fullmatch(expected_sha256) is None:
        raise SpeechNativeProfileError("speech-native binding SHA-256 is malformed")
    if _sha256_file(path) != expected_sha256:
        raise SpeechNativeProfileError("speech-native binding file SHA-256 mismatch")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(f"cannot read speech-native binding: {error}") from error
    if not isinstance(document, dict):
        raise SpeechNativeProfileError("speech-native binding must be a JSON object")
    claimed = document.get("binding_sha256")
    unsigned = dict(document)
    unsigned.pop("binding_sha256", None)
    if claimed != _canonical_sha256(unsigned):
        raise SpeechNativeProfileError("speech-native binding self-hash mismatch")
    return document


def _load_key_cards(path: Path, expected_sha256: str) -> tuple[KeyCardV1, ...]:
    document = _load_binding_document(path, expected_sha256)
    raw_cards = document.get("key_cards")
    if not isinstance(raw_cards, list) or len(raw_cards) != 18:
        raise SpeechNativeProfileError("profile requires exactly 18 frozen key cards")
    cards: list[KeyCardV1] = []
    for raw in raw_cards:
        if not isinstance(raw, dict) or set(raw) != {
            "key_id",
            "definition",
            "positive_examples",
            "contrastive_boundary",
            "value_label",
        }:
            raise SpeechNativeProfileError("speech-native key card has unexpected fields")
        examples = raw["positive_examples"]
        if not isinstance(examples, list) or not all(
            isinstance(item, str) for item in examples
        ):
            raise SpeechNativeProfileError("speech-native key examples must be strings")
        cards.append(
            KeyCardV1(
                key_id=str(raw["key_id"]),
                definition=str(raw["definition"]),
                positive_examples=tuple(examples),
                contrastive_boundary=(
                    str(raw["contrastive_boundary"])
                    if raw["contrastive_boundary"] is not None
                    else None
                ),
                value_label=str(raw["value_label"]),
            ).validate()
        )
    return tuple(cards)


def read_speech_native_predictions(
    *,
    attempt_dirs: Sequence[Path],
    binding_path: Path,
    binding_sha256: str,
    split_name: str,
) -> dict[str, object]:
    """Score prediction-only flight artifacts after every server has stopped.

    Gold labels enter only this model-free reader. Flight receipts and
    decision rows are hash-verified before scoring; no runtime prompt or
    trace is modified.
    """

    if not attempt_dirs:
        raise SpeechNativeProfileError("speech-native read requires at least one attempt")
    binding = _load_binding_document(binding_path, binding_sha256)
    splits = binding.get("splits")
    split = splits.get(split_name) if isinstance(splits, Mapping) else None
    raw_items = split.get("items") if isinstance(split, Mapping) else None
    if not isinstance(raw_items, list) or not raw_items:
        raise SpeechNativeProfileError(f"binding lacks split {split_name!r}")
    gold: dict[str, str] = {}
    speaker_by_sample: dict[str, str] = {}
    for item in raw_items:
        if not isinstance(item, Mapping):
            raise SpeechNativeProfileError("binding split item must be an object")
        sample_id = item.get("sample_id")
        value_label = item.get("value_label")
        speaker_id = item.get("speaker_id")
        if (
            not isinstance(sample_id, str)
            or not isinstance(value_label, str)
            or not isinstance(speaker_id, str)
            or not speaker_id
            or sample_id in gold
        ):
            raise SpeechNativeProfileError(
                "binding split labels/speakers are malformed or duplicate"
            )
        gold[sample_id] = value_label
        speaker_by_sample[sample_id] = speaker_id

    cards = _load_key_cards(binding_path, binding_sha256)
    card_by_key = {card.key_id: card for card in cards}
    label_by_key = {card.key_id: card.value_label for card in cards}
    key_by_label = {card.value_label: card.key_id for card in cards}
    aggregates: list[dict[str, object]] = []
    correctness_by_cell: dict[str, dict[str, bool]] = {}
    predictions_by_cell: dict[str, dict[str, str | None]] = {}
    calls_by_cell: dict[str, dict[str, int | None]] = {}
    source_receipts: list[dict[str, str]] = []
    for attempt_dir_value in attempt_dirs:
        attempt_dir = Path(attempt_dir_value)
        receipt_path = attempt_dir / "flight-receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SpeechNativeProfileError(f"cannot read flight receipt: {error}") from error
        if (
            not isinstance(receipt, dict)
            or receipt.get("status") != "COMPLETED"
            or receipt.get("request_failures") != []
            or receipt.get("split_identity_hash") is None
        ):
            raise SpeechNativeProfileError("flight receipt is not a completed readable result")
        profile = receipt.get("profile")
        decisions_ref = receipt.get("decisions")
        if not isinstance(profile, Mapping) or not isinstance(decisions_ref, Mapping):
            raise SpeechNativeProfileError("flight receipt lacks prediction metadata")
        key_representation_id = profile.get("key_representation_id")
        matcher_policy_id = profile.get("matcher_policy_id")
        if not isinstance(key_representation_id, str) or not isinstance(
            matcher_policy_id, str
        ):
            raise SpeechNativeProfileError("flight cell identity is malformed")
        cell_id = f"{key_representation_id}-{matcher_policy_id}"
        if matcher_policy_id in {"M3", "M5", "M6"}:
            top_k = profile.get("top_k")
            if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
                raise SpeechNativeProfileError(
                    f"{matcher_policy_id} flight receipt lacks a valid top_k"
                )
            cell_id = f"{cell_id}-k{top_k}"
            prompt_policy_id = profile.get(
                "matcher_prompt_policy_id", "speech-native-json-copy-v2"
            )
            prompt_suffix = {
                "speech-native-json-copy-v2": "",
                "speech-native-json-copy-v3": "-v3",
            }.get(prompt_policy_id)
            if prompt_suffix is None:
                raise SpeechNativeProfileError(
                    f"{matcher_policy_id} flight receipt has an unknown matcher prompt policy"
                )
            cell_id += prompt_suffix
            verifier_policy_id = profile.get(
                "matcher_verifier_policy_id", "speech-native-compatibility-v1"
            )
            verifier_suffix = {
                "speech-native-compatibility-v1": "",
                "speech-native-contrastive-verifier-v2": "-verify-contrastive-v2",
            }.get(verifier_policy_id)
            if verifier_suffix is None:
                raise SpeechNativeProfileError(
                    f"{matcher_policy_id} flight receipt has an unknown verifier policy"
                )
            cell_id += verifier_suffix
        agent_aggregator_id = profile.get(
            "agent_aggregator_id", "m3-majority-canonical-tie-v1"
        )
        profile_agent_policy_id = profile.get(
            "agent_policy_id", "m1-m3-disagreement-escalation-v1"
        )
        if matcher_policy_id == "M5":
            if profile_agent_policy_id not in {
                "m1-m3-disagreement-escalation-v1",
                "m1-m3-full-branch-explorer-v1",
            }:
                raise SpeechNativeProfileError(
                    "M5 flight receipt has an unknown agent policy"
                )
            aggregator_suffix = {
                "m3-majority-canonical-tie-v1": "",
                "m3-majority-primary-tie-v2": "-aggregate-primary-v2",
                "m3-unanimous-primary-fallback-v3": "-aggregate-unanimous-v3",
            }.get(agent_aggregator_id)
            if aggregator_suffix is None:
                raise SpeechNativeProfileError(
                    "M5 flight receipt has an unknown agent aggregator"
                )
            cell_id += aggregator_suffix
            if profile_agent_policy_id == "m1-m3-full-branch-explorer-v1":
                cell_id += "-agent-full-branch-v1"
        elif matcher_policy_id == "M6":
            grounded_policy_suffix = {
                "knowledge-grounded-semantic-refinement-full-action-v1": "-grounded-v1",
                _M6_SCHEMA_V2_POLICY_ID: "-grounded-schema-v2",
                _M6_SCHEMA_V3_POLICY_ID: "-grounded-schema-v3",
            }.get(profile_agent_policy_id)
            if (
                grounded_policy_suffix is None
                or agent_aggregator_id != "grounded-refined-primary-fallback-v1"
            ):
                raise SpeechNativeProfileError(
                    "M6 flight receipt has an unknown grounded policy identity"
                )
            cell_id += grounded_policy_suffix
        order_ids = profile.get("key_order_ids", ["canonical"])
        if (
            not isinstance(order_ids, list)
            or len(order_ids) != 1
            or not isinstance(order_ids[0], str)
        ):
            raise SpeechNativeProfileError(
                "prediction flight must carry exactly one key order"
            )
        if order_ids[0] != "canonical":
            cell_id += f"-order-{order_ids[0]}"
        mechanism_control_id = profile.get("mechanism_control_id", "matched")
        control_suffix = {
            "matched": "",
            "speech-swap-v1": "-control-speech-swap-v1",
            "key-text-shuffle-v1": "-control-key-text-shuffle-v1",
        }.get(mechanism_control_id)
        if control_suffix is None:
            raise SpeechNativeProfileError(
                "flight receipt has an unknown mechanism control"
            )
        cell_id += control_suffix
        if cell_id in correctness_by_cell:
            raise SpeechNativeProfileError(f"duplicate flight cell {cell_id!r}")
        decisions_name = decisions_ref.get("path")
        decisions_sha256 = decisions_ref.get("sha256")
        if (
            not isinstance(decisions_name, str)
            or Path(decisions_name).name != decisions_name
            or not isinstance(decisions_sha256, str)
            or _SHA256.fullmatch(decisions_sha256) is None
        ):
            raise SpeechNativeProfileError("flight decisions reference is malformed")
        decisions_path = attempt_dir / decisions_name
        if _sha256_file(decisions_path) != decisions_sha256:
            raise SpeechNativeProfileError("flight decisions SHA-256 mismatch")
        rows: list[Mapping[str, object]] = []
        try:
            with decisions_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    if not isinstance(row, Mapping):
                        raise SpeechNativeProfileError("decision row must be an object")
                    rows.append(row)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SpeechNativeProfileError(f"cannot read decisions: {error}") from error
        if len(rows) != decisions_ref.get("count") or len(rows) != len(gold):
            raise SpeechNativeProfileError("decision count does not match receipt or split")
        seen: set[str] = set()
        correctness: dict[str, bool] = {}
        predictions: dict[str, str | None] = {}
        query_by_target: dict[str, str] = {}
        calls_by_sample: dict[str, int | None] = {}
        parse_failures = 0
        top_k_reachable_count = 0
        agent_escalation_count = 0
        agent_helpful_escalation_count = 0
        agent_harmful_escalation_count = 0
        agent_neutral_escalation_count = 0
        agent_recoverable_error_count = 0
        agent_missed_stop_error_count = 0
        agent_action_sensitive_count = 0
        agent_action_counts: Counter[str] = Counter()
        agent_primary_correct_count = 0
        agent_primary_fallback_correct_count = 0
        agent_primary_fallback_wrong_to_correct = 0
        agent_primary_fallback_correct_to_wrong = 0
        agent_unanimous_fallback_correct_count = 0
        agent_unanimous_fallback_wrong_to_correct = 0
        agent_unanimous_fallback_correct_to_wrong = 0
        agent_full_branch_count = 0
        agent_wrong_agreement_count = 0
        agent_branch_helpful_count = 0
        agent_branch_harmful_count = 0
        agent_branch_neutral_count = 0
        agent_full_trajectories: list[dict[str, str | None]] = []
        agent_full_episodic_trajectories: list[dict[str, object]] = []
        grounded_state_valid_count = 0
        grounded_backtrack_count = 0
        grounded_refined_change_count = 0
        grounded_fold_trajectories: list[dict[str, str | None]] = []
        grounded_final_predictions: list[str | None] = []
        for row in rows:
            if row.get("schema") != "saea-speech-native-decision-v1":
                raise SpeechNativeProfileError("decision schema mismatch")
            sample_id = row.get("sample_id")
            if not isinstance(sample_id, str) or sample_id not in gold or sample_id in seen:
                raise SpeechNativeProfileError("decision sample set is malformed")
            seen.add(sample_id)
            key_id = row.get("key_id")
            predicted = row.get("predicted_value_label")
            parse_failure = row.get("parse_failure")
            if not isinstance(parse_failure, bool):
                raise SpeechNativeProfileError("decision parse_failure must be boolean")
            if key_id is None:
                if predicted is not None or not parse_failure:
                    raise SpeechNativeProfileError("empty decision mapping is inconsistent")
            elif (
                not isinstance(key_id, str)
                or key_id not in label_by_key
                or predicted != label_by_key[key_id]
                or parse_failure
            ):
                raise SpeechNativeProfileError("decision key-to-label mapping is inconsistent")
            parse_failures += int(parse_failure)
            correctness[sample_id] = predicted == gold[sample_id]
            predictions[sample_id] = predicted if isinstance(predicted, str) else None
            raw_calls = row.get("calls")
            if raw_calls is not None and (
                isinstance(raw_calls, bool)
                or not isinstance(raw_calls, int)
                or raw_calls <= 0
            ):
                raise SpeechNativeProfileError(
                    "decision calls must be a positive integer when present"
                )
            calls_by_sample[sample_id] = raw_calls
            query_sample_id = row.get("query_sample_id", sample_id)
            row_control_id = row.get(
                "mechanism_control_id", mechanism_control_id
            )
            if (
                not isinstance(query_sample_id, str)
                or query_sample_id not in gold
                or row_control_id != mechanism_control_id
            ):
                raise SpeechNativeProfileError(
                    "decision query/control binding is malformed"
                )
            if mechanism_control_id == "speech-swap-v1":
                if query_sample_id == sample_id:
                    raise SpeechNativeProfileError(
                        "speech-swap decision contains a fixed point"
                    )
            elif query_sample_id != sample_id:
                raise SpeechNativeProfileError(
                    "matched decision does not use its target speech query"
                )
            query_by_target[sample_id] = query_sample_id
            raw_top_key_ids = row.get("top_key_ids", [])
            if (
                not isinstance(raw_top_key_ids, list)
                or not all(
                    isinstance(top_key_id, str) and top_key_id in label_by_key
                    for top_key_id in raw_top_key_ids
                )
                or len(set(raw_top_key_ids)) != len(raw_top_key_ids)
            ):
                raise SpeechNativeProfileError("decision top_key_ids are malformed")
            if matcher_policy_id in {"M3", "M5", "M6"}:
                assert isinstance(top_k, int)
                if len(raw_top_key_ids) > top_k:
                    raise SpeechNativeProfileError(
                        "decision top_key_ids exceed the registered top_k"
                    )
                top_k_reachable_count += int(
                    key_by_label[gold[sample_id]] in raw_top_key_ids
                )
            if matcher_policy_id == "M5":
                row_agent_policy_id = row.get("agent_policy_id")
                agent_actions = row.get("agent_actions")
                agent_escalated = row.get("agent_escalated")
                agent_votes = row.get("agent_vote_key_ids")
                agent_steps = row.get("agent_steps")
                row_aggregator_id = row.get(
                    "agent_aggregator_id", "m3-majority-canonical-tie-v1"
                )
                if (
                    row_agent_policy_id != profile_agent_policy_id
                    or row_aggregator_id != agent_aggregator_id
                    or not isinstance(agent_actions, list)
                    or not agent_actions
                    or not all(
                        isinstance(action_id, str) and action_id
                        for action_id in agent_actions
                    )
                    or not isinstance(agent_escalated, bool)
                    or not isinstance(agent_votes, list)
                    or len(agent_votes)
                    != (
                        4
                        if profile_agent_policy_id
                        == "m1-m3-full-branch-explorer-v1"
                        or agent_escalated
                        else 2
                    )
                    or not all(
                        vote is None
                        or isinstance(vote, str) and vote in label_by_key
                        for vote in agent_votes
                    )
                    or not isinstance(agent_steps, list)
                    or len(agent_steps) != len(agent_votes)
                ):
                    raise SpeechNativeProfileError("M5 agent trajectory is malformed")
                expected_step_fields = {
                    "action_id",
                    "key_id",
                    "top_key_ids",
                    "calls",
                    "parse_failure",
                }
                for step_index, step in enumerate(agent_steps):
                    if (
                        not isinstance(step, Mapping)
                        or set(step) != expected_step_fields
                        or step.get("key_id") != agent_votes[step_index]
                        or not isinstance(step.get("action_id"), str)
                        or isinstance(step.get("calls"), bool)
                        or not isinstance(step.get("calls"), int)
                        or int(step["calls"]) <= 0
                        or not isinstance(step.get("parse_failure"), bool)
                        or not isinstance(step.get("top_key_ids"), list)
                        or not all(
                            isinstance(top_key_id, str)
                            and top_key_id in label_by_key
                            for top_key_id in step.get("top_key_ids", [])
                        )
                        or len(set(step.get("top_key_ids", [])))
                        != len(step.get("top_key_ids", []))
                    ):
                        raise SpeechNativeProfileError(
                            "M5 agent step summary is malformed"
                        )
                raw_verifier_scores = row.get("verifier_scores", {})
                if not isinstance(raw_verifier_scores, Mapping):
                    raise SpeechNativeProfileError(
                        "M5 canonical verifier scores are malformed"
                    )
                canonical_verifier_scores: dict[str, tuple[bool, float]] = {}
                for score_key_id, score_document in raw_verifier_scores.items():
                    if (
                        not isinstance(score_key_id, str)
                        or score_key_id not in label_by_key
                        or not isinstance(score_document, Mapping)
                        or set(score_document) != {"compatible", "confidence"}
                        or not isinstance(score_document.get("compatible"), bool)
                        or isinstance(score_document.get("confidence"), bool)
                        or not isinstance(score_document.get("confidence"), (int, float))
                        or not -1.0
                        <= float(score_document["confidence"])
                        <= 100.0
                    ):
                        raise SpeechNativeProfileError(
                            "M5 canonical verifier score is malformed"
                        )
                    canonical_verifier_scores[score_key_id] = (
                        bool(score_document["compatible"]),
                        float(score_document["confidence"]),
                    )
                primary_vote = agent_votes[0]
                primary_correct = (
                    isinstance(primary_vote, str)
                    and label_by_key[primary_vote] == gold[sample_id]
                )
                final_correct = correctness[sample_id]
                candidate_correct = any(
                    isinstance(vote, str)
                    and label_by_key[vote] == gold[sample_id]
                    for vote in agent_votes[1:]
                )
                m3_votes = [vote for vote in agent_votes[1:] if vote is not None]
                m3_counts = Counter(m3_votes)
                m3_majority = next(
                    (vote for vote, count in m3_counts.items() if count >= 2),
                    None,
                )
                primary_fallback_key = (
                    m3_majority if m3_majority is not None else primary_vote
                )
                primary_fallback_correct = (
                    isinstance(primary_fallback_key, str)
                    and label_by_key[primary_fallback_key] == gold[sample_id]
                )
                unanimous_key = (
                    m3_votes[0]
                    if len(m3_votes) == 3 and len(set(m3_votes)) == 1
                    else primary_vote
                )
                unanimous_fallback_correct = (
                    isinstance(unanimous_key, str)
                    and label_by_key[unanimous_key] == gold[sample_id]
                )
                agent_action_counts.update(agent_actions)
                agent_primary_correct_count += int(primary_correct)
                agent_escalation_count += int(agent_escalated)
                branch_executed = len(agent_votes) == 4
                agent_full_branch_count += int(branch_executed)
                agent_wrong_agreement_count += int(
                    primary_vote == agent_votes[1] and not primary_correct
                )
                agent_recoverable_error_count += int(
                    not primary_correct and candidate_correct
                )
                agent_missed_stop_error_count += int(
                    not agent_escalated and not final_correct
                )
                agent_primary_fallback_correct_count += int(
                    primary_fallback_correct
                )
                agent_primary_fallback_wrong_to_correct += int(
                    not final_correct and primary_fallback_correct
                )
                agent_primary_fallback_correct_to_wrong += int(
                    final_correct and not primary_fallback_correct
                )
                agent_unanimous_fallback_correct_count += int(
                    unanimous_fallback_correct
                )
                agent_unanimous_fallback_wrong_to_correct += int(
                    not final_correct and unanimous_fallback_correct
                )
                agent_unanimous_fallback_correct_to_wrong += int(
                    final_correct and not unanimous_fallback_correct
                )
                if branch_executed:
                    agent_branch_helpful_count += int(
                        not primary_correct and final_correct
                    )
                    agent_branch_harmful_count += int(
                        primary_correct and not final_correct
                    )
                    agent_branch_neutral_count += int(
                        primary_correct == final_correct
                    )
                    agent_action_sensitive_count += int(
                        len({vote for vote in agent_votes[1:] if vote is not None}) > 1
                    )
                    agent_full_trajectories.append(
                        {
                            "speaker_id": speaker_by_sample[sample_id],
                            "gold_key_id": key_by_label[gold[sample_id]],
                            "primary_key_id": agent_votes[0],
                            "canonical_key_id": agent_votes[1],
                            "reverse_key_id": agent_votes[2],
                            "rotate_key_id": agent_votes[3],
                        }
                    )
                    agent_full_episodic_trajectories.append(
                        {
                            "sample_id": sample_id,
                            "speaker_id": speaker_by_sample[sample_id],
                            "gold_key_id": key_by_label[gold[sample_id]],
                            "primary_key_id": agent_votes[0],
                            "canonical_key_id": agent_votes[1],
                            "reverse_key_id": agent_votes[2],
                            "rotate_key_id": agent_votes[3],
                            "canonical_top_key_ids": tuple(
                                agent_steps[1]["top_key_ids"]
                            ),
                            "canonical_verifier_scores": canonical_verifier_scores,
                            "primary_calls": int(agent_steps[0]["calls"]),
                            "canonical_calls": int(agent_steps[1]["calls"]),
                            "reverse_calls": int(agent_steps[2]["calls"]),
                            "rotate_calls": int(agent_steps[3]["calls"]),
                        }
                    )
                if agent_escalated:
                    agent_helpful_escalation_count += int(
                        not primary_correct and final_correct
                    )
                    agent_harmful_escalation_count += int(
                        primary_correct and not final_correct
                    )
                    agent_neutral_escalation_count += int(
                        primary_correct == final_correct
                    )
            elif matcher_policy_id == "M6":
                row_agent_policy_id = row.get("agent_policy_id")
                row_aggregator_id = row.get("agent_aggregator_id")
                agent_actions = row.get("agent_actions")
                agent_escalated = row.get("agent_escalated")
                agent_votes = row.get("agent_vote_key_ids")
                agent_steps = row.get("agent_steps")
                if (
                    row_agent_policy_id != profile_agent_policy_id
                    or row_aggregator_id != agent_aggregator_id
                    or not isinstance(agent_actions, list)
                    or len(agent_actions) < 3
                    or not all(
                        isinstance(action_id, str) and action_id
                        for action_id in agent_actions
                    )
                    or agent_escalated is not True
                    or not isinstance(agent_votes, list)
                    or len(agent_votes) != 2
                    or not all(
                        vote is None
                        or isinstance(vote, str) and vote in label_by_key
                        for vote in agent_votes
                    )
                    or not isinstance(agent_steps, list)
                    or not 2 <= len(agent_steps) <= 4
                ):
                    raise SpeechNativeProfileError(
                        "M6 grounded agent trajectory is malformed"
                    )
                base_step_fields = {
                    "action_id",
                    "key_id",
                    "top_key_ids",
                    "calls",
                    "parse_failure",
                }
                for step in agent_steps:
                    if (
                        not isinstance(step, Mapping)
                        or not base_step_fields.issubset(step)
                        or step.get("key_id") is not None
                        and step.get("key_id") not in label_by_key
                        or not isinstance(step.get("action_id"), str)
                        or isinstance(step.get("calls"), bool)
                        or not isinstance(step.get("calls"), int)
                        or int(step["calls"]) <= 0
                        or not isinstance(step.get("parse_failure"), bool)
                        or not isinstance(step.get("top_key_ids"), list)
                        or not all(
                            isinstance(top_key_id, str)
                            and top_key_id in label_by_key
                            for top_key_id in step.get("top_key_ids", [])
                        )
                        or len(set(step.get("top_key_ids", [])))
                        != len(step.get("top_key_ids", []))
                    ):
                        raise SpeechNativeProfileError(
                            "M6 grounded agent step is malformed"
                        )
                if (
                    set(agent_steps[0]) != base_step_fields
                    or agent_steps[0].get("action_id")
                    != "match:speech-only-primary"
                    or agent_steps[0].get("key_id") != agent_votes[0]
                    or set(agent_steps[1]) != base_step_fields
                    or agent_steps[1].get("action_id") != "retrieve:speech-only"
                ):
                    raise SpeechNativeProfileError(
                        "M6 primary or initial retrieval step is malformed"
                    )
                initial_top_ids = tuple(agent_steps[1]["top_key_ids"])
                if len(initial_top_ids) > int(top_k):
                    raise SpeechNativeProfileError(
                        "M6 initial retrieval exceeds registered top_k"
                    )
                state_valid = False
                if len(agent_steps) >= 3:
                    state_step = agent_steps[2]
                    if state_step.get("action_id") != "build:grounded-query-state":
                        raise SpeechNativeProfileError(
                            "M6 grounded state step identity is malformed"
                        )
                    state_document = state_step.get("grounded_query_state")
                    if state_document is not None:
                        if set(state_step) != base_step_fields | {
                            "grounded_query_state"
                        }:
                            raise SpeechNativeProfileError(
                                "M6 grounded state step has unexpected fields"
                            )
                        parsed_state = parse_grounded_query_state(
                            json.dumps(
                                state_document,
                                ensure_ascii=False,
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                            candidate_key_ids=initial_top_ids,
                            cards_by_key=card_by_key,
                            key_representation_id="K2",
                        )
                        if parsed_state is None or state_step.get("parse_failure"):
                            raise SpeechNativeProfileError(
                                "M6 grounded query state fails citation validation"
                            )
                        state_valid = True
                    elif (
                        set(state_step) != base_step_fields
                        or state_step.get("parse_failure") is not True
                    ):
                        raise SpeechNativeProfileError(
                            "M6 invalid state step does not fail closed"
                        )
                success_actions = [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "build:grounded-query-state",
                    "retrieve:speech-plus-grounded-state",
                    "verify:speech-plus-grounded-state",
                    "select:refined-primary-fallback",
                ]
                backtracked = agent_actions[-1].startswith("backtrack:")
                if backtracked:
                    if (
                        agent_votes[1] is not None
                        or key_id != agent_votes[0]
                        or len(agent_steps) not in {2, 3}
                    ):
                        raise SpeechNativeProfileError(
                            "M6 backtrack does not preserve the speech primary"
                        )
                else:
                    if (
                        agent_actions != success_actions
                        or len(agent_steps) != 4
                        or not state_valid
                        or set(agent_steps[3])
                        != base_step_fields | {"verifier_scores"}
                        or agent_steps[3].get("action_id")
                        != "retrieve-and-verify:speech-plus-grounded-state"
                        or agent_steps[3].get("key_id") != agent_votes[1]
                        or tuple(agent_steps[3].get("top_key_ids", []))
                        != tuple(raw_top_key_ids)
                    ):
                        raise SpeechNativeProfileError(
                            "M6 refined retrieval step is malformed"
                        )
                    step_scores = agent_steps[3].get("verifier_scores")
                    if step_scores != row.get("verifier_scores") or not isinstance(
                        step_scores, Mapping
                    ):
                        raise SpeechNativeProfileError(
                            "M6 verifier score copies are inconsistent"
                        )
                    for score_key_id, score_document in step_scores.items():
                        if (
                            score_key_id not in raw_top_key_ids
                            or not isinstance(score_document, Mapping)
                            or set(score_document) != {"compatible", "confidence"}
                            or not isinstance(score_document.get("compatible"), bool)
                            or isinstance(score_document.get("confidence"), bool)
                            or not isinstance(
                                score_document.get("confidence"), (int, float)
                            )
                            or not -1.0
                            <= float(score_document["confidence"])
                            <= 100.0
                        ):
                            raise SpeechNativeProfileError(
                                "M6 verifier score is malformed"
                            )
                primary_vote = agent_votes[0]
                refined_vote = agent_votes[1]
                primary_correct = (
                    isinstance(primary_vote, str)
                    and label_by_key[primary_vote] == gold[sample_id]
                )
                refined_correct = (
                    isinstance(refined_vote, str)
                    and label_by_key[refined_vote] == gold[sample_id]
                )
                final_correct = correctness[sample_id]
                agent_action_counts.update(agent_actions)
                agent_primary_correct_count += int(primary_correct)
                agent_escalation_count += 1
                agent_helpful_escalation_count += int(
                    not primary_correct and final_correct
                )
                agent_harmful_escalation_count += int(
                    primary_correct and not final_correct
                )
                agent_neutral_escalation_count += int(
                    primary_correct == final_correct
                )
                agent_recoverable_error_count += int(
                    not primary_correct and refined_correct
                )
                changed = refined_vote is not None and refined_vote != primary_vote
                agent_action_sensitive_count += int(changed)
                grounded_refined_change_count += int(changed)
                grounded_state_valid_count += int(state_valid)
                grounded_backtrack_count += int(backtracked)
                grounded_fold_trajectories.append(
                    {
                        "speaker_id": speaker_by_sample[sample_id],
                        "gold_key_id": key_by_label[gold[sample_id]],
                        "primary_key_id": (
                            primary_vote if isinstance(primary_vote, str) else None
                        ),
                        "canonical_key_id": None,
                        "reverse_key_id": None,
                        "rotate_key_id": None,
                    }
                )
                grounded_final_predictions.append(
                    key_id if isinstance(key_id, str) else None
                )
        if seen != set(gold):
            raise SpeechNativeProfileError("decision sample set does not equal the frozen split")
        if (
            mechanism_control_id == "speech-swap-v1"
            and set(query_by_target.values()) != set(gold)
        ):
            raise SpeechNativeProfileError(
                "speech-swap decisions do not form a split permutation"
            )
        correct = sum(correctness.values())
        grounded_speaker_folds: list[dict[str, object]] = []
        if matcher_policy_id == "M6":
            frozen_grounded_folds = _validate_training_free_trajectories(
                grounded_fold_trajectories
            )
            grounded_speaker_folds = _speaker_fold_metrics(
                frozen_grounded_folds,
                assignments=_speaker_grouped_fold_assignments(
                    frozen_grounded_folds
                ),
                predictions=grounded_final_predictions,
            )
        aggregates.append(
            {
                "cell_id": cell_id,
                "correct": correct,
                "count": len(gold),
                "accuracy": correct / len(gold),
                "parse_failure_count": parse_failures,
                "top_k_reachable_count": (
                    top_k_reachable_count
                    if matcher_policy_id in {"M3", "M5", "M6"}
                    else None
                ),
                "top_k_reachability": (
                    top_k_reachable_count / len(gold)
                    if matcher_policy_id in {"M3", "M5", "M6"}
                    else None
                ),
                "agent_loop_metrics": (
                    {
                        "policy_id": profile_agent_policy_id,
                        "aggregator_id": agent_aggregator_id,
                        "primary_correct": agent_primary_correct_count,
                        "primary_accuracy": agent_primary_correct_count / len(gold),
                        "final_minus_primary_correct": (
                            correct - agent_primary_correct_count
                        ),
                        "stop_count": len(gold) - agent_escalation_count,
                        "escalation_count": agent_escalation_count,
                        "escalation_rate": agent_escalation_count / len(gold),
                        "helpful_escalation_count": agent_helpful_escalation_count,
                        "harmful_escalation_count": agent_harmful_escalation_count,
                        "neutral_escalation_count": agent_neutral_escalation_count,
                        "recoverable_error_count": agent_recoverable_error_count,
                        "missed_stop_error_count": agent_missed_stop_error_count,
                        "action_sensitive_escalation_count": agent_action_sensitive_count,
                        "action_counts": dict(sorted(agent_action_counts.items())),
                        "counterfactual_aggregators": [
                            {
                                "aggregator_id": "m3-majority-primary-tie-v2",
                                "discovery_status": "post-read-policy-discovery",
                                "correct": agent_primary_fallback_correct_count,
                                "count": len(gold),
                                "accuracy": (
                                    agent_primary_fallback_correct_count / len(gold)
                                ),
                                "wrong_to_correct_vs_observed": (
                                    agent_primary_fallback_wrong_to_correct
                                ),
                                "correct_to_wrong_vs_observed": (
                                    agent_primary_fallback_correct_to_wrong
                                ),
                            },
                            {
                                "aggregator_id": "m3-unanimous-primary-fallback-v3",
                                "discovery_status": "post-read-policy-discovery",
                                "correct": agent_unanimous_fallback_correct_count,
                                "count": len(gold),
                                "accuracy": (
                                    agent_unanimous_fallback_correct_count / len(gold)
                                ),
                                "wrong_to_correct_vs_observed": (
                                    agent_unanimous_fallback_wrong_to_correct
                                ),
                                "correct_to_wrong_vs_observed": (
                                    agent_unanimous_fallback_correct_to_wrong
                                ),
                            },
                        ],
                        **(
                            {
                                "full_branch_count": agent_full_branch_count,
                                "wrong_agreement_count": agent_wrong_agreement_count,
                                "branch_helpful_count": agent_branch_helpful_count,
                                "branch_harmful_count": agent_branch_harmful_count,
                                "branch_neutral_count": agent_branch_neutral_count,
                                "action_support_complete": (
                                    agent_full_branch_count == len(gold)
                                ),
                                "training_free_policy_frontier": (
                                    _evaluate_training_free_agent_policies(
                                        agent_full_trajectories
                                    )
                                    if agent_full_branch_count == len(gold)
                                    else None
                                ),
                                "training_free_contextual_policy": (
                                    _evaluate_training_free_contextual_policy(
                                        agent_full_trajectories
                                    )
                                    if agent_full_branch_count == len(gold)
                                    else None
                                ),
                                "training_free_episodic_policy": (
                                    _evaluate_training_free_episodic_policy(
                                        agent_full_episodic_trajectories
                                    )
                                    if agent_full_branch_count == len(gold)
                                    else None
                                ),
                            }
                            if profile_agent_policy_id
                            == "m1-m3-full-branch-explorer-v1"
                            else {}
                        ),
                    }
                    if matcher_policy_id == "M5"
                    else (
                        {
                            "policy_id": profile_agent_policy_id,
                            "aggregator_id": agent_aggregator_id,
                            "primary_correct": agent_primary_correct_count,
                            "primary_accuracy": (
                                agent_primary_correct_count / len(gold)
                            ),
                            "final_minus_primary_correct": (
                                correct - agent_primary_correct_count
                            ),
                            "speaker_fold_policy_id": _SPEAKER_FOLD_POLICY_ID,
                            "speaker_folds_vs_primary": grounded_speaker_folds,
                            "positive_delta_fold_count": sum(
                                int(fold["correct_delta_vs_primary"] > 0)
                                for fold in grounded_speaker_folds
                            ),
                            "nonnegative_delta_fold_count": sum(
                                int(fold["correct_delta_vs_primary"] >= 0)
                                for fold in grounded_speaker_folds
                            ),
                            "worst_fold_delta_vs_primary": min(
                                int(fold["correct_delta_vs_primary"])
                                for fold in grounded_speaker_folds
                            ),
                            "grounded_state_valid_count": (
                                grounded_state_valid_count
                            ),
                            "grounded_state_valid_rate": (
                                grounded_state_valid_count / len(gold)
                            ),
                            "backtrack_count": grounded_backtrack_count,
                            "refined_change_count": (
                                grounded_refined_change_count
                            ),
                            "helpful_refinement_count": (
                                agent_helpful_escalation_count
                            ),
                            "harmful_refinement_count": (
                                agent_harmful_escalation_count
                            ),
                            "neutral_refinement_count": (
                                agent_neutral_escalation_count
                            ),
                            "recoverable_error_count": (
                                agent_recoverable_error_count
                            ),
                            "action_sensitive_count": (
                                agent_action_sensitive_count
                            ),
                            "action_counts": dict(
                                sorted(agent_action_counts.items())
                            ),
                        }
                        if matcher_policy_id == "M6"
                        else None
                    )
                ),
                "actual_contact_count": profile.get("actual_contact_count"),
                "aggregate_tokens_per_second": (
                    receipt.get("timing", {}).get("aggregate_tokens_per_second")
                    if isinstance(receipt.get("timing"), Mapping)
                    else None
                ),
            }
        )
        correctness_by_cell[cell_id] = correctness
        predictions_by_cell[cell_id] = predictions
        calls_by_cell[cell_id] = calls_by_sample
        source_receipts.append(
            {
                "run_id": str(receipt.get("run_id")),
                "flight_receipt_sha256": _sha256_file(receipt_path),
                "decisions_sha256": decisions_sha256,
            }
        )

    aggregate_by_cell = {str(item["cell_id"]): item for item in aggregates}
    canonical_cells = tuple(predictions_by_cell)
    for base_cell_id in canonical_cells:
        if "-order-" in base_cell_id or "-control-" in base_cell_id:
            continue
        ordered_source_ids = (
            base_cell_id,
            f"{base_cell_id}-order-reverse",
            f"{base_cell_id}-order-rotate-7",
        )
        if not all(source_id in predictions_by_cell for source_id in ordered_source_ids):
            continue
        ensemble_prefix = re.sub(r"-M(?:1|3)", "-M4", base_cell_id, count=1)
        ensemble_cell_id = f"{ensemble_prefix}-order-ensemble-v1"
        if ensemble_cell_id in predictions_by_cell:
            raise SpeechNativeProfileError(
                f"duplicate order-ensemble cell {ensemble_cell_id!r}"
            )
        ensemble_predictions: dict[str, str | None] = {}
        ensemble_calls: dict[str, int | None] = {}
        tie_break_count = 0
        order_disagreement_count = 0
        for sample_id in gold:
            votes = tuple(
                predictions_by_cell[source_id][sample_id]
                for source_id in ordered_source_ids
            )
            order_disagreement_count += int(len(set(votes)) > 1)
            counts = Counter(vote for vote in votes if vote is not None)
            majority = next(
                (label for label, count in counts.items() if count >= 2),
                None,
            )
            if majority is None:
                tie_break_count += 1
                majority = votes[0]
            ensemble_predictions[sample_id] = majority
            source_calls = tuple(
                calls_by_cell[source_id][sample_id]
                for source_id in ordered_source_ids
            )
            ensemble_calls[sample_id] = (
                sum(int(value) for value in source_calls)
                if all(
                    isinstance(value, int) and not isinstance(value, bool)
                    for value in source_calls
                )
                else None
            )
        ensemble_correctness = {
            sample_id: prediction == gold[sample_id]
            for sample_id, prediction in ensemble_predictions.items()
        }
        source_contact_counts = tuple(
            aggregate_by_cell[source_id].get("actual_contact_count")
            for source_id in ordered_source_ids
        )
        actual_contact_count = (
            sum(int(value) for value in source_contact_counts)
            if all(isinstance(value, int) and not isinstance(value, bool) for value in source_contact_counts)
            else None
        )
        for source_id in ordered_source_ids:
            aggregate_by_cell[source_id]["order_disagreement_count"] = (
                order_disagreement_count
            )
        ensemble_aggregate: dict[str, object] = {
            "cell_id": ensemble_cell_id,
            "correct": sum(ensemble_correctness.values()),
            "count": len(gold),
            "accuracy": sum(ensemble_correctness.values()) / len(gold),
            "parse_failure_count": sum(
                prediction is None for prediction in ensemble_predictions.values()
            ),
            "top_k_reachable_count": None,
            "top_k_reachability": None,
            "actual_contact_count": actual_contact_count,
            "aggregate_tokens_per_second": None,
            "source_cell_ids": list(ordered_source_ids),
            "order_disagreement_count": order_disagreement_count,
            "tie_break_count": tie_break_count,
            "tie_break_policy_id": "canonical-on-no-majority-v1",
        }
        aggregates.append(ensemble_aggregate)
        aggregate_by_cell[ensemble_cell_id] = ensemble_aggregate
        correctness_by_cell[ensemble_cell_id] = ensemble_correctness
        predictions_by_cell[ensemble_cell_id] = ensemble_predictions
        calls_by_cell[ensemble_cell_id] = ensemble_calls

    adaptive_policies: list[dict[str, object]] = []
    adaptive_source_ids = (
        "K1-M1",
        "K1-M3-k3-v3",
        "K1-M3-k3-v3-order-reverse",
        "K1-M3-k3-v3-order-rotate-7",
    )
    adaptive_ensemble_id = "K1-M4-k3-v3-order-ensemble-v1"
    if all(source_id in predictions_by_cell for source_id in adaptive_source_ids) and (
        adaptive_ensemble_id in predictions_by_cell
    ):
        adaptive_predictions: dict[str, str | None] = {}
        actual_contact_count = 0
        stop_agree_count = 0
        escalation_count = 0
        calls_complete = True
        primary_id, critic_id, reverse_id, rotate_id = adaptive_source_ids
        for sample_id in gold:
            primary_prediction = predictions_by_cell[primary_id][sample_id]
            critic_prediction = predictions_by_cell[critic_id][sample_id]
            escalated = (
                primary_prediction is None
                or critic_prediction is None
                or primary_prediction != critic_prediction
            )
            if escalated:
                escalation_count += 1
                prediction = predictions_by_cell[adaptive_ensemble_id][sample_id]
            else:
                stop_agree_count += 1
                prediction = primary_prediction
            adaptive_predictions[sample_id] = prediction
            required_ids = (
                adaptive_source_ids
                if escalated
                else (primary_id, critic_id)
            )
            sample_calls = tuple(
                calls_by_cell[source_id][sample_id] for source_id in required_ids
            )
            if all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in sample_calls
            ):
                actual_contact_count += sum(int(value) for value in sample_calls)
            else:
                calls_complete = False
        primary_correctness = correctness_by_cell[primary_id]
        adaptive_correctness = {
            sample_id: prediction == gold[sample_id]
            for sample_id, prediction in adaptive_predictions.items()
        }
        adaptive_policies.append(
            {
                "policy_id": "K1-M5-disagreement-escalation-v1",
                "discovery_status": "post-read-policy-discovery",
                "correct": sum(adaptive_correctness.values()),
                "count": len(gold),
                "accuracy": sum(adaptive_correctness.values()) / len(gold),
                "actual_contact_count": actual_contact_count if calls_complete else None,
                "stop_agree_count": stop_agree_count,
                "escalation_count": escalation_count,
                "wrong_to_correct_vs_primary": sum(
                    not primary_correctness[sample_id]
                    and adaptive_correctness[sample_id]
                    for sample_id in gold
                ),
                "correct_to_wrong_vs_primary": sum(
                    primary_correctness[sample_id]
                    and not adaptive_correctness[sample_id]
                    for sample_id in gold
                ),
                "parse_failure_count": sum(
                    prediction is None for prediction in adaptive_predictions.values()
                ),
                "source_cell_ids": list(adaptive_source_ids),
                "escalation_policy_id": "m1-m3-disagree-v1",
                "escalation_aggregator_id": "m3-majority-canonical-tie-v1",
            }
        )

    baseline_id = str(aggregates[0]["cell_id"])
    baseline = correctness_by_cell[baseline_id]
    pairwise: list[dict[str, object]] = []
    for aggregate in aggregates:
        cell_id = str(aggregate["cell_id"])
        current = correctness_by_cell[cell_id]
        current_predictions = predictions_by_cell[cell_id]
        wrong_to_correct = sum(
            1 for sample_id in gold if not baseline[sample_id] and current[sample_id]
        )
        correct_to_wrong = sum(
            1 for sample_id in gold if baseline[sample_id] and not current[sample_id]
        )
        aggregate["wrong_to_correct_vs_baseline"] = wrong_to_correct
        aggregate["correct_to_wrong_vs_baseline"] = correct_to_wrong
        pairwise.append(
            {
                "baseline_cell_id": baseline_id,
                "cell_id": cell_id,
                "wrong_to_correct": wrong_to_correct,
                "correct_to_wrong": correct_to_wrong,
                "net_change": wrong_to_correct - correct_to_wrong,
                "prediction_disagreement_count": sum(
                    1
                    for sample_id in gold
                    if current_predictions[sample_id]
                    != predictions_by_cell[baseline_id][sample_id]
                ),
            }
        )
    cell_ids = tuple(predictions_by_cell)
    cell_pairwise = [
        {
            "left_cell_id": left_cell_id,
            "right_cell_id": right_cell_id,
            "prediction_disagreement_count": sum(
                predictions_by_cell[left_cell_id][sample_id]
                != predictions_by_cell[right_cell_id][sample_id]
                for sample_id in gold
            ),
        }
        for left_index, left_cell_id in enumerate(cell_ids)
        for right_cell_id in cell_ids[left_index + 1 :]
    ]
    mechanism_controls: list[dict[str, object]] = []
    for control_cell_id in cell_ids:
        marker = "-control-"
        if marker not in control_cell_id:
            continue
        base_cell_id, control_id = control_cell_id.split(marker, 1)
        if base_cell_id not in correctness_by_cell:
            raise SpeechNativeProfileError(
                f"mechanism control {control_cell_id!r} lacks matched base cell"
            )
        base_correct = sum(correctness_by_cell[base_cell_id].values())
        control_correct = sum(correctness_by_cell[control_cell_id].values())
        mechanism_controls.append(
            {
                "base_cell_id": base_cell_id,
                "control_cell_id": control_cell_id,
                "control_id": control_id,
                "correct_drop": base_correct - control_correct,
                "accuracy_drop": (base_correct - control_correct) / len(gold),
                "prediction_disagreement_count": sum(
                    predictions_by_cell[base_cell_id][sample_id]
                    != predictions_by_cell[control_cell_id][sample_id]
                    for sample_id in gold
                ),
            }
        )

    selectable = [item for item in aggregates if "-control-" not in str(item["cell_id"])]
    winner = min(
        selectable,
        key=lambda item: (
            -int(item["correct"]),
            int(item["correct_to_wrong_vs_baseline"]),
            int(item["parse_failure_count"]),
            int(item.get("order_disagreement_count", len(gold) + 1)),
            (
                int(item["actual_contact_count"])
                if isinstance(item.get("actual_contact_count"), int)
                and not isinstance(item.get("actual_contact_count"), bool)
                else math.inf
            ),
            str(item["cell_id"]),
        ),
    )
    accuracy_cost_candidates: list[dict[str, object]] = []
    for cell_id in ("K1-M1", "K1-M3-k3-v3", adaptive_ensemble_id):
        item = aggregate_by_cell.get(cell_id)
        if item is not None:
            accuracy_cost_candidates.append(
                {
                    "policy_id": cell_id,
                    "correct": item["correct"],
                    "count": item["count"],
                    "accuracy": item["accuracy"],
                    "actual_contact_count": item["actual_contact_count"],
                    "parse_failure_count": item["parse_failure_count"],
                    "discovery_status": "observed-cell",
                }
            )
    accuracy_cost_candidates.extend(adaptive_policies)

    def dominates(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
        left_calls = left.get("actual_contact_count")
        right_calls = right.get("actual_contact_count")
        if not isinstance(left_calls, int) or not isinstance(right_calls, int):
            return False
        left_correct = int(left["correct"])
        right_correct = int(right["correct"])
        left_failures = int(left["parse_failure_count"])
        right_failures = int(right["parse_failure_count"])
        return (
            left_correct >= right_correct
            and left_calls <= right_calls
            and left_failures <= right_failures
            and (
                left_correct > right_correct
                or left_calls < right_calls
                or left_failures < right_failures
            )
        )

    accuracy_cost_frontier = sorted(
        (
            candidate
            for candidate in accuracy_cost_candidates
            if not any(
                dominates(other, candidate)
                for other in accuracy_cost_candidates
                if other is not candidate
            )
        ),
        key=lambda item: (
            int(item["actual_contact_count"])
            if isinstance(item.get("actual_contact_count"), int)
            else math.inf,
            -int(item["correct"]),
            str(item["policy_id"]),
        ),
    )
    return {
        "schema": "saea-speech-native-read-v1",
        "study": "speech-aware-evidence-acquisition",
        "split_name": split_name,
        "binding_file_sha256": binding_sha256,
        "baseline_cell_id": baseline_id,
        "aggregates": aggregates,
        "pairwise": pairwise,
        "cell_pairwise": cell_pairwise,
        "mechanism_controls": mechanism_controls,
        "adaptive_policies": adaptive_policies,
        "accuracy_cost_candidates": accuracy_cost_candidates,
        "accuracy_cost_frontier": accuracy_cost_frontier,
        "selection_policy_id": "accuracy-regression-parse-order-cost-v1",
        "selected_cell_id": winner["cell_id"],
        "source_receipts": source_receipts,
    }


def _load_packet_index(
    receipt_path: Path,
    expected_sha256: str,
) -> dict[str, dict[str, str]]:
    if _SHA256.fullmatch(expected_sha256) is None:
        raise SpeechNativeProfileError("packet promotion receipt SHA-256 is malformed")
    if _sha256_file(receipt_path) != expected_sha256:
        raise SpeechNativeProfileError("packet promotion receipt SHA-256 mismatch")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(f"cannot read packet promotion receipt: {error}") from error
    if not isinstance(receipt, dict) or receipt.get("schema") != (
        "saea-speech-packet-promotion-receipt-v1"
    ):
        raise SpeechNativeProfileError("packet promotion receipt schema mismatch")
    packets = receipt.get("packets")
    if not isinstance(packets, list):
        raise SpeechNativeProfileError("packet promotion receipt lacks packets")
    by_packet_id: dict[str, dict[str, str]] = {}
    for packet in packets:
        if not isinstance(packet, dict):
            raise SpeechNativeProfileError("packet receipt entry must be an object")
        packet_id = packet.get("packet_id")
        packet_sha256 = packet.get("packet_sha256")
        if (
            not isinstance(packet_id, str)
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
            or packet_id in by_packet_id
        ):
            raise SpeechNativeProfileError("packet receipt contains malformed or duplicate ids")
        by_packet_id[packet_id] = {"packet_id": packet_id, "sha256": packet_sha256}
    return by_packet_id


def _load_packet_bindings(
    receipt_path: Path,
    expected_sha256: str,
    samples: Sequence[object],
) -> dict[str, dict[str, str]]:
    by_packet_id = _load_packet_index(receipt_path, expected_sha256)
    bindings: dict[str, dict[str, str]] = {}
    for sample in samples:
        descriptor = by_packet_id.get(sample.packet_id)
        if descriptor is None:
            raise SpeechNativeProfileError(
                f"packet promotion receipt does not materialize {sample.sample_id!r}"
            )
        bindings[sample.sample_id] = descriptor
    return bindings


def _packet_id_from_sample_id(sample_id: object) -> str:
    if not isinstance(sample_id, str):
        raise SpeechNativeProfileError("audio-key source sample id must be a string")
    parts = sample_id.split(":")
    if len(parts) != 4 or parts[0] != "slurp" or parts[1] != "train":
        raise SpeechNativeProfileError("audio-key source sample id is malformed")
    return "/".join(parts)


def _build_audio_key_bindings(
    binding: Mapping[str, object],
    packet_index: Mapping[str, Mapping[str, str]],
    key_cards: Sequence[KeyCardV1],
) -> dict[str, dict[str, str]]:
    raw_material = binding.get("key_material")
    if not isinstance(raw_material, list):
        raise SpeechNativeProfileError("speech-native binding lacks key material")
    source_by_key: dict[str, str] = {}
    for item in raw_material:
        if not isinstance(item, Mapping):
            raise SpeechNativeProfileError("speech-native key material must be objects")
        key_id = item.get("key_id")
        if not isinstance(key_id, str) or key_id in source_by_key:
            raise SpeechNativeProfileError("speech-native key material ids are malformed")
        source_by_key[key_id] = _packet_id_from_sample_id(
            item.get("audio_key_source_sample_id")
        )
    expected_keys = {card.key_id for card in key_cards}
    if set(source_by_key) != expected_keys:
        raise SpeechNativeProfileError("audio-key material does not match frozen key cards")
    bindings: dict[str, dict[str, str]] = {}
    for key_id in sorted(expected_keys):
        descriptor = packet_index.get(source_by_key[key_id])
        if (
            not isinstance(descriptor, Mapping)
            or set(descriptor) != {"packet_id", "sha256"}
        ):
            raise SpeechNativeProfileError(
                f"audio-key packet is not materialized for {key_id!r}"
            )
        bindings[key_id] = {
            "packet_id": str(descriptor["packet_id"]),
            "sha256": str(descriptor["sha256"]),
        }
    return bindings


def _shuffle_key_text(key_cards: tuple[KeyCardV1, ...]) -> tuple[KeyCardV1, ...]:
    donors = key_cards[1:] + key_cards[:1]
    return tuple(
        KeyCardV1(
            key_id=target.key_id,
            definition=donor.definition,
            positive_examples=donor.positive_examples,
            contrastive_boundary=donor.contrastive_boundary,
            value_label=target.value_label,
        ).validate()
        for target, donor in zip(key_cards, donors, strict=True)
    )


def build_profile_tasks(
    *,
    samples: Sequence[object],
    packet_bindings: Mapping[str, Mapping[str, str]],
    key_cards: tuple[KeyCardV1, ...],
    order_ids: Sequence[str],
    decoding_params: Mapping[str, object],
    key_representation_id: str,
    matcher_policy_id: str,
    top_k: int = 3,
    prompt_policy_id: str = "speech-native-json-copy-v2",
    verifier_policy_id: str = "speech-native-compatibility-v1",
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None = None,
    mechanism_control_id: str = "matched",
    agent_policy_id: str = "m1-m3-disagreement-escalation-v1",
    agent_aggregator_id: str = "m3-majority-canonical-tie-v1",
) -> tuple[SpeechNativeMatchTask, ...]:
    """Build the registered maximum-card prompt tasks without reading labels."""

    if mechanism_control_id not in {
        "matched",
        "speech-swap-v1",
        "key-text-shuffle-v1",
    }:
        raise SpeechNativeProfileError("unknown speech-native mechanism control")
    frozen_samples = tuple(samples)
    if mechanism_control_id == "speech-swap-v1" and len(frozen_samples) < 2:
        raise SpeechNativeProfileError("speech-swap control requires at least two samples")
    controlled_cards = key_cards
    if mechanism_control_id == "key-text-shuffle-v1":
        if key_representation_id not in {"K1", "K2", "K4"}:
            raise SpeechNativeProfileError(
                "key-text shuffle requires a text-bearing key representation"
            )
        controlled_cards = _shuffle_key_text(key_cards)
    source_samples = (
        frozen_samples[1:] + frozen_samples[:1]
        if mechanism_control_id == "speech-swap-v1"
        else frozen_samples
    )
    tasks: list[SpeechNativeMatchTask] = []
    for order_id in order_ids:
        builder = _ORDER_BUILDERS.get(order_id)
        if builder is None:
            raise SpeechNativeProfileError(f"unknown profile key order {order_id!r}")
        ordered_cards = builder(controlled_cards)
        for target_sample, source_sample in zip(
            frozen_samples, source_samples, strict=True
        ):
            descriptor = packet_bindings.get(source_sample.sample_id)
            if descriptor is None:
                raise SpeechNativeProfileError(
                    f"profile sample {source_sample.sample_id!r} lacks a packet binding"
                )
            tasks.append(
                SpeechNativeMatchTask(
                    task_id=f"{order_id}:{target_sample.sample_id}",
                    sample=source_sample,
                    scoring_sample_id=target_sample.sample_id,
                    mechanism_control_id=mechanism_control_id,
                    query_descriptor={**descriptor, "role": "query"},
                    key_cards=ordered_cards,
                    key_representation_id=key_representation_id,
                    matcher_policy_id=matcher_policy_id,
                    prompt_policy_id=prompt_policy_id,
                    verifier_policy_id=verifier_policy_id,
                    decoding_params=dict(decoding_params),
                    top_k=top_k,
                    audio_key_bindings=audio_key_bindings,
                    agent_policy_id=agent_policy_id,
                    agent_aggregator_id=agent_aggregator_id,
                )
            )
    return tuple(tasks)


def profile_timing_metrics(
    timings: Sequence[Mapping[str, object]],
    *,
    slot_count: int,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, float]:
    """Derive request-window throughput and mean slot occupancy."""

    if not timings:
        raise SpeechNativeProfileError("profile produced no request timings")
    starts: list[float] = []
    ends: list[float] = []
    latency_sum = 0.0
    for timing in timings:
        started_at = timing.get("started_at")
        latency = timing.get("latency_seconds")
        if (
            not isinstance(started_at, str)
            or isinstance(latency, bool)
            or not isinstance(latency, (int, float))
            or not math.isfinite(float(latency))
            or float(latency) < 0
        ):
            raise SpeechNativeProfileError("profile timing row is malformed")
        start = datetime.fromisoformat(started_at).timestamp()
        starts.append(start)
        ends.append(start + float(latency))
        latency_sum += float(latency)
    wall = max(ends) - min(starts)
    if wall <= 0:
        raise SpeechNativeProfileError("profile request window is not positive")
    return {
        "request_window_seconds": wall,
        "slot_occupancy_pct": min(100.0, 100.0 * latency_sum / (slot_count * wall)),
        "aggregate_tokens_per_second": (prompt_tokens + completion_tokens) / wall,
    }


def _trace_usage_summary(path: Path) -> dict[str, int]:
    request_count = 0
    response_count = 0
    cost_count = 0
    max_prompt_tokens = 0
    max_completion_tokens = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                channel = record.get("channel")
                if channel == "MODEL_REQUEST":
                    request_count += 1
                elif channel == "MODEL_RESPONSE":
                    response_count += 1
                    usage = record.get("payload", {}).get("usage", {})
                    if isinstance(usage, dict):
                        max_prompt_tokens = max(
                            max_prompt_tokens, int(usage.get("prompt_tokens", 0))
                        )
                        max_completion_tokens = max(
                            max_completion_tokens, int(usage.get("completion_tokens", 0))
                        )
                elif channel == "COST":
                    cost_count += 1
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise SpeechNativeProfileError(f"cannot verify profile trace usage: {error}") from error
    return {
        "model_request_count": request_count,
        "model_response_count": response_count,
        "cost_record_count": cost_count,
        "max_prompt_tokens": max_prompt_tokens,
        "max_completion_tokens": max_completion_tokens,
    }


def _trace_speech_query_summary(
    path: Path,
    *,
    expected_queries: Mapping[str, Mapping[str, str]],
) -> dict[str, int]:
    """Verify that every traced model request carries its bound speech query."""

    frozen_expected: dict[str, dict[str, str]] = {}
    for sample_id, descriptor in expected_queries.items():
        expected = dict(descriptor)
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or set(expected) != {"packet_id", "sha256", "role"}
            or expected.get("role") != "query"
            or not isinstance(expected.get("packet_id"), str)
            or not expected["packet_id"]
            or not isinstance(expected.get("sha256"), str)
            or _SHA256.fullmatch(expected["sha256"]) is None
        ):
            raise SpeechNativeProfileError(
                "cannot verify trace against a malformed expected speech query"
            )
        frozen_expected[sample_id] = expected

    counts = Counter(
        {
            "model_request_count": 0,
            "valid_speech_query_count": 0,
            "invalid_speech_query_count": 0,
            "unknown_sample_id_count": 0,
            "query_source_failure_count": 0,
            "mmproj_flag_failure_count": 0,
            "packet_binding_failure_count": 0,
        }
    )
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("channel") != "MODEL_REQUEST":
                    continue
                counts["model_request_count"] += 1
                envelope = record.get("payload", {})
                payload = (
                    envelope.get("payload", {})
                    if isinstance(envelope, Mapping)
                    else {}
                )
                if not isinstance(payload, Mapping):
                    payload = {}
                sample_id = payload.get("sample_id")
                expected = (
                    frozen_expected.get(sample_id)
                    if isinstance(sample_id, str)
                    else None
                )
                source_valid = payload.get("query_source") == "speech_features"
                mmproj_valid = payload.get("mmproj_loaded") is False
                if not source_valid:
                    counts["query_source_failure_count"] += 1
                if not mmproj_valid:
                    counts["mmproj_flag_failure_count"] += 1
                if expected is None:
                    counts["unknown_sample_id_count"] += 1

                parts = payload.get("speech_feature_parts")
                query_parts = (
                    [
                        dict(part)
                        for part in parts
                        if isinstance(part, Mapping) and part.get("role") == "query"
                    ]
                    if isinstance(parts, list)
                    else []
                )
                binding_valid = (
                    expected is not None
                    and payload.get("speech_packet_sha256") == expected["sha256"]
                    and query_parts == [expected]
                )
                if not binding_valid:
                    counts["packet_binding_failure_count"] += 1
                if source_valid and mmproj_valid and binding_valid:
                    counts["valid_speech_query_count"] += 1
                else:
                    counts["invalid_speech_query_count"] += 1
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise SpeechNativeProfileError(
            f"cannot verify profile trace speech-query carriage: {error}"
        ) from error
    return dict(counts)


def _profile_completion_issues(
    *,
    calls_used: int,
    actual_contact_count: int,
    task_count: int,
    planned_contact_ceiling: int,
    request_failure_count: int,
    server_scan: Mapping[str, object],
    trace_usage: Mapping[str, object],
    trace_speech_query: Mapping[str, object],
) -> tuple[str, ...]:
    """Return fail-closed completion defects using trace carriage as primary proof."""

    issues: list[str] = []
    if calls_used != actual_contact_count:
        issues.append("cost calls do not equal decision contacts")
    if actual_contact_count < task_count:
        issues.append("actual contacts are fewer than matcher tasks")
    if actual_contact_count > planned_contact_ceiling:
        issues.append("actual contacts exceed the registered ceiling")
    if request_failure_count:
        issues.append("request failures were recorded")
    for field, message in (
        ("oom_marker_hits", "server log contains OOM markers"),
        ("host_spill_marker_hits", "server log contains host-spill markers"),
        ("runaway_marker_hits", "server log contains runaway markers"),
    ):
        if server_scan.get(field):
            issues.append(message)
    if any(
        int(trace_usage.get(field, -1)) != actual_contact_count
        for field in (
            "model_request_count",
            "model_response_count",
            "cost_record_count",
        )
    ):
        issues.append("trace request, response, and cost counts are incomplete")
    if (
        int(trace_speech_query.get("model_request_count", -1))
        != actual_contact_count
        or int(trace_speech_query.get("valid_speech_query_count", -1))
        != actual_contact_count
        or int(trace_speech_query.get("invalid_speech_query_count", -1)) != 0
    ):
        issues.append("trace speech-query carriage is incomplete")
    return tuple(issues)


def _load_pinned_json_object(
    path: Path, *, expected_sha256: str, artifact_name: str
) -> dict[str, object]:
    if _SHA256.fullmatch(expected_sha256) is None:
        raise SpeechNativeProfileError(f"{artifact_name} expected SHA-256 is malformed")
    if not Path(path).is_file() or _sha256_file(Path(path)) != expected_sha256:
        raise SpeechNativeProfileError(f"{artifact_name} SHA-256 mismatch")
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(f"cannot read {artifact_name}: {error}") from error
    if not isinstance(document, dict):
        raise SpeechNativeProfileError(f"{artifact_name} must be a JSON object")
    return document


def audit_speech_native_action_support(
    *,
    attempt_dir: Path,
    attempt_record_path: Path,
    attempt_record_sha256: str,
    flight_receipt_sha256: str,
    decisions_sha256: str,
    trace_sha256: str,
) -> dict[str, object]:
    """Read only M6 action structure from one narrowly admitted aborted attempt.

    This audit never opens a split binding and never interprets value labels or
    correctness. It exists to decide whether the frozen grounded loop creates a
    non-degenerate action space worth testing on a fresh, unread train gate.
    """

    attempt_dir = Path(attempt_dir)
    flight = _load_pinned_json_object(
        attempt_dir / "flight-receipt.json",
        expected_sha256=flight_receipt_sha256,
        artifact_name="action-audit flight receipt",
    )
    run_id = flight.get("run_id")
    attempt_id = flight.get("attempt_id")
    if (
        not isinstance(run_id, str)
        or not run_id
        or not isinstance(attempt_id, str)
        or not attempt_id
        or flight.get("status") != "COMPLETED"
        or flight.get("request_failures") != []
    ):
        raise SpeechNativeProfileError(
            "action-audit flight is not a mechanically completed source"
        )
    attempt_record = _load_pinned_json_object(
        Path(attempt_record_path),
        expected_sha256=attempt_record_sha256,
        artifact_name="action-audit durable attempt record",
    )
    if (
        attempt_record.get("run_id") != run_id
        or attempt_record.get("attempt_id") != attempt_id
        or attempt_record.get("state") != "ABORTED"
        or attempt_record.get("failure_reason")
        != "speech-native profile completion checks failed"
    ):
        raise SpeechNativeProfileError(
            "action audit admits only the legacy completion-gate abort state"
        )

    profile = flight.get("profile")
    decisions_ref = flight.get("decisions")
    if (
        not isinstance(profile, Mapping)
        or profile.get("matcher_policy_id") != "M6"
        or profile.get("agent_policy_id") != _M6_SCHEMA_V2_POLICY_ID
        or profile.get("agent_aggregator_id") != _M6_AGGREGATOR_ID
        or profile.get("mechanism_control_id") != "matched"
        or profile.get("top_k") != 3
        or not isinstance(decisions_ref, Mapping)
        or decisions_ref.get("contains_gold_labels") is not False
    ):
        raise SpeechNativeProfileError(
            "action audit requires the matched M6 schema-v2 prediction-only cell"
        )
    decisions_name = decisions_ref.get("path")
    if (
        not isinstance(decisions_name, str)
        or not decisions_name
        or Path(decisions_name).name != decisions_name
    ):
        raise SpeechNativeProfileError("action-audit decision path is unsafe")
    decisions_path = attempt_dir / decisions_name
    if (
        _SHA256.fullmatch(decisions_sha256) is None
        or decisions_ref.get("sha256") != decisions_sha256
        or not decisions_path.is_file()
        or _sha256_file(decisions_path) != decisions_sha256
    ):
        raise SpeechNativeProfileError("action-audit decisions SHA-256 mismatch")
    try:
        decision_rows = tuple(
            json.loads(line)
            for line in decisions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read action-audit decisions: {error}"
        ) from error
    task_count = profile.get("task_count")
    if (
        isinstance(task_count, bool)
        or not isinstance(task_count, int)
        or task_count <= 0
        or len(decision_rows) != task_count
        or decisions_ref.get("count") != task_count
    ):
        raise SpeechNativeProfileError("action-audit decision count is inconsistent")

    expected_packet_sha256: dict[str, str] = {}
    calls_distribution: Counter[int] = Counter()
    action_sensitive_count = 0
    ranked_retrieval_change_count = 0
    candidate_set_change_count = 0
    top1_change_count = 0
    seen_samples: set[str] = set()
    contact_count = 0
    for row in decision_rows:
        if not isinstance(row, Mapping):
            raise SpeechNativeProfileError("action-audit decision row is not an object")
        sample_id = row.get("sample_id")
        query_sample_id = row.get("query_sample_id")
        packet_sha256 = row.get("speech_packet_sha256")
        calls = row.get("calls")
        votes = row.get("agent_vote_key_ids")
        steps = row.get("agent_steps")
        actions = row.get("agent_actions")
        if (
            row.get("schema") != "saea-speech-native-decision-v1"
            or not isinstance(sample_id, str)
            or not sample_id
            or sample_id in seen_samples
            or query_sample_id != sample_id
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
            or row.get("mechanism_control_id") != "matched"
            or row.get("key_representation_id") != "K1"
            or row.get("matcher_policy_id") != "M6"
            or row.get("parse_failure") is not False
            or row.get("agent_policy_id") != _M6_SCHEMA_V2_POLICY_ID
            or row.get("agent_aggregator_id") != _M6_AGGREGATOR_ID
            or row.get("agent_escalated") is not True
            or not isinstance(actions, list)
            or tuple(actions) != _M6_SUCCESS_ACTIONS
        ):
            raise SpeechNativeProfileError("action-audit M6 decision identity is malformed")
        if (
            isinstance(calls, bool)
            or not isinstance(calls, int)
            or calls not in {7, 8}
            or not isinstance(votes, list)
            or len(votes) != 2
            or not all(vote in _SPEECH_NATIVE_KEY_IDS for vote in votes)
            or row.get("key_id") != votes[1]
            or not isinstance(steps, list)
            or len(steps) != 4
        ):
            raise SpeechNativeProfileError("action-audit M6 action trajectory is malformed")
        expected_step_actions = (
            "match:speech-only-primary",
            "retrieve:speech-only",
            "build:grounded-query-state",
            "retrieve-and-verify:speech-plus-grounded-state",
        )
        for step, expected_action in zip(steps, expected_step_actions, strict=True):
            if (
                not isinstance(step, Mapping)
                or step.get("action_id") != expected_action
                or step.get("parse_failure") is not False
                or isinstance(step.get("calls"), bool)
                or not isinstance(step.get("calls"), int)
                or int(step["calls"]) <= 0
                or not isinstance(step.get("top_key_ids"), list)
                or not all(
                    key_id in _SPEECH_NATIVE_KEY_IDS
                    for key_id in step.get("top_key_ids", [])
                )
            ):
                raise SpeechNativeProfileError("action-audit M6 step is malformed")
        initial_ids = tuple(steps[1]["top_key_ids"])
        refined_ids = tuple(steps[3]["top_key_ids"])
        state_document = steps[2].get("grounded_query_state")
        if (
            len(initial_ids) != 3
            or len(set(initial_ids)) != 3
            or len(refined_ids) != 3
            or len(set(refined_ids)) != 3
            or not isinstance(state_document, Mapping)
            or state_document.get("candidate_key_ids") != list(initial_ids)
            or steps[0].get("key_id") != votes[0]
            or steps[1].get("key_id") != initial_ids[0]
            or steps[2].get("key_id") is not None
            or steps[3].get("key_id") != votes[1]
            or row.get("top_key_ids") != list(refined_ids)
            or steps[3].get("verifier_scores") != row.get("verifier_scores")
            or tuple(int(step["calls"]) for step in steps) != (1, 1, 1, 4)
        ):
            raise SpeechNativeProfileError(
                "action-audit grounded retrieval transition is malformed"
            )
        response_hashes = row.get("response_text_sha256")
        if (
            not isinstance(response_hashes, list)
            or len(response_hashes) != calls
            or not all(
                isinstance(value, str) and _SHA256.fullmatch(value) is not None
                for value in response_hashes
            )
        ):
            raise SpeechNativeProfileError("action-audit response hashes are malformed")
        seen_samples.add(sample_id)
        expected_packet_sha256[query_sample_id] = packet_sha256
        contact_count += calls
        calls_distribution[calls] += 1
        action_sensitive_count += int(votes[0] != votes[1])
        ranked_retrieval_change_count += int(initial_ids != refined_ids)
        candidate_set_change_count += int(set(initial_ids) != set(refined_ids))
        top1_change_count += int(initial_ids[0] != refined_ids[0])

    actual_contact_count = profile.get("actual_contact_count")
    planned_contact_ceiling = profile.get("planned_contact_ceiling")
    actual_usage = attempt_record.get("actual")
    close = flight.get("close")
    cost = close.get("cost") if isinstance(close, Mapping) else None
    if (
        actual_contact_count != contact_count
        or not isinstance(actual_usage, Mapping)
        or actual_usage.get("calls") != contact_count
        or not isinstance(cost, Mapping)
        or cost.get("calls_used") != contact_count
        or isinstance(planned_contact_ceiling, bool)
        or not isinstance(planned_contact_ceiling, int)
    ):
        raise SpeechNativeProfileError("action-audit contact accounting is inconsistent")

    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    if (
        _SHA256.fullmatch(trace_sha256) is None
        or not trace_path.is_file()
        or _sha256_file(trace_path) != trace_sha256
    ):
        raise SpeechNativeProfileError("action-audit trace SHA-256 mismatch")
    expected_queries: dict[str, Mapping[str, str]] = {}
    try:
        with trace_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("channel") != "MODEL_REQUEST":
                    continue
                envelope = record.get("payload")
                payload = envelope.get("payload") if isinstance(envelope, Mapping) else None
                if not isinstance(payload, Mapping):
                    continue
                sample_id = payload.get("sample_id")
                parts = payload.get("speech_feature_parts")
                query_parts = (
                    [
                        dict(part)
                        for part in parts
                        if isinstance(part, Mapping) and part.get("role") == "query"
                    ]
                    if isinstance(parts, list)
                    else []
                )
                if (
                    not isinstance(sample_id, str)
                    or sample_id not in expected_packet_sha256
                    or len(query_parts) != 1
                    or query_parts[0].get("sha256")
                    != expected_packet_sha256[sample_id]
                ):
                    continue
                previous = expected_queries.get(sample_id)
                if previous is not None and dict(previous) != query_parts[0]:
                    raise SpeechNativeProfileError(
                        "action-audit trace has conflicting speech-query carriage"
                    )
                expected_queries[sample_id] = query_parts[0]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot inspect action-audit speech-query carriage: {error}"
        ) from error
    if set(expected_queries) != set(expected_packet_sha256):
        raise SpeechNativeProfileError("action-audit trace speech-query carriage is incomplete")
    trace_usage = _trace_usage_summary(trace_path)
    trace_speech_query = _trace_speech_query_summary(
        trace_path, expected_queries=expected_queries
    )

    process_audit_sha256 = flight.get("process_audit_sha256")
    if not isinstance(process_audit_sha256, str):
        raise SpeechNativeProfileError("action-audit process receipt SHA-256 is missing")
    process_audit = _load_pinned_json_object(
        attempt_dir / f"{run_id}.mmproj-audit.json",
        expected_sha256=process_audit_sha256,
        artifact_name="action-audit mmproj process audit",
    )
    if (
        process_audit.get("mmproj_loaded") is not False
        or process_audit.get("mmproj_hit_count") != 0
    ):
        raise SpeechNativeProfileError("action-audit source loaded mmproj")
    server_scan = flight.get("server_log_scan")
    if not isinstance(server_scan, Mapping):
        raise SpeechNativeProfileError("action-audit server log scan is missing")
    completion_issues = _profile_completion_issues(
        calls_used=contact_count,
        actual_contact_count=contact_count,
        task_count=task_count,
        planned_contact_ceiling=planned_contact_ceiling,
        request_failure_count=0,
        server_scan=server_scan,
        trace_usage=trace_usage,
        trace_speech_query=trace_speech_query,
    )
    if completion_issues:
        raise SpeechNativeProfileError(
            "action-audit source has nonlegacy completion defects: "
            + "; ".join(completion_issues)
        )
    marker_count = server_scan.get("mmproj_free_chunk_count")
    if isinstance(marker_count, bool) or not isinstance(marker_count, int):
        raise SpeechNativeProfileError("action-audit feature-log count is malformed")
    return {
        "schema": "saea-speech-native-action-support-audit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "source_attempt_state": "ABORTED",
        "source_terminal_reason": "legacy-resident-prompt-cache-log-count-gate",
        "effectiveness_eligible": False,
        "gold_read": False,
        "decision_count": task_count,
        "contact_count": contact_count,
        "valid_speech_query_contact_count": trace_speech_query[
            "valid_speech_query_count"
        ],
        "grounded_state_valid_count": task_count,
        "backtrack_count": 0,
        "action_sensitive_count": action_sensitive_count,
        "action_sensitive_rate": action_sensitive_count / task_count,
        "action_support_threshold": 3,
        "action_support_threshold_met": action_sensitive_count >= 3,
        "initial_to_refined_ranked_change_count": ranked_retrieval_change_count,
        "initial_to_refined_candidate_set_change_count": candidate_set_change_count,
        "initial_to_refined_top1_change_count": top1_change_count,
        "calls_distribution": {
            str(calls): count for calls, count in sorted(calls_distribution.items())
        },
        "legacy_feature_log_marker_count": marker_count,
        "legacy_feature_log_marker_deficit": contact_count - marker_count,
        "source_sha256": {
            "attempt_record": attempt_record_sha256,
            "flight_receipt": flight_receipt_sha256,
            "decisions": decisions_sha256,
            "trace": trace_sha256,
            "process_audit": process_audit_sha256,
        },
    }


def _read_live_process_environment(
    pid: int, *, proc_root: Path = Path("/proc")
) -> dict[str, str]:
    path = Path(proc_root) / str(pid) / "environ"
    try:
        raw_entries = path.read_bytes().split(b"\0")
    except OSError as error:
        raise SessionError(
            f"cannot read resident session environment through {path}: {error}"
        ) from error
    environment: dict[str, str] = {}
    try:
        for raw in raw_entries:
            if not raw:
                continue
            key, separator, value = raw.partition(b"=")
            if not separator or not key:
                raise UnicodeError("environment entry lacks a non-empty key")
            decoded_key = key.decode("utf-8", "strict")
            if decoded_key in environment:
                raise UnicodeError(f"duplicate environment key {decoded_key!r}")
            environment[decoded_key] = value.decode("utf-8", "strict")
    except UnicodeError as error:
        raise SessionError(
            f"cannot decode resident session environment through {path}: {error}"
        ) from error
    return environment


def _assert_reusable_session_profile(
    session: SessionReceipt,
    *,
    host: str,
    port: int,
    model_argv: Sequence[str],
    server_args: Sequence[str],
    server_env: Mapping[str, str],
    live_environment: Mapping[str, str] | None = None,
) -> SessionReceipt:
    """Fail closed unless a resident inference service has this exact profile."""

    session.validate()
    if session.role != "inference":
        raise SessionError("speech-native reuse requires an inference session")
    expected_argv = (
        session.argv[0],
        "--host",
        host,
        "--port",
        str(port),
        *tuple(model_argv),
        *tuple(server_args),
    )
    if session.argv != expected_argv:
        raise SessionError(
            "resident session launch argv differs from the composed speech-native "
            "serving profile; model reload is required"
        )
    expected_env_keys = tuple(sorted(server_env))
    if session.server_env_keys != expected_env_keys:
        raise SessionError(
            "resident session environment keys differ from the composed speech-native "
            "serving profile; model reload is required"
        )
    observed_environment = (
        dict(live_environment)
        if live_environment is not None
        else _read_live_process_environment(session.pid)
    )
    mismatches = {
        key: {
            "expected": expected,
            "observed": observed_environment.get(key),
        }
        for key, expected in server_env.items()
        if observed_environment.get(key) != expected
    }
    if mismatches:
        raise SessionError(
            "resident session server environment differs from the composed "
            f"speech-native serving profile: {mismatches!r}"
        )
    return session


def _release_speech_native_session(
    session: SessionReceipt,
    *,
    owns_process: bool,
    runtime_receipt: Mapping[str, object],
    runtime_root: Path,
    receipt_path: Path,
    stop: Callable[..., Mapping[str, object]] = stop_session,
) -> Mapping[str, object] | None:
    """Stop only an attempt-owned server; attached resident services survive."""

    if not owns_process:
        return None
    return stop(
        session,
        runtime_receipt=runtime_receipt,
        runtime_root=Path(runtime_root),
        force_after_timeout=True,
        receipt_path=Path(receipt_path),
    )


def _scan_server_log(path: Path, *, start_offset: int = 0) -> dict[str, object]:
    if isinstance(start_offset, bool) or not isinstance(start_offset, int) or start_offset < 0:
        raise SpeechNativeProfileError("server log start_offset must be a non-negative integer")
    try:
        with path.open("rb") as handle:
            handle.seek(start_offset)
            text = handle.read().decode("utf-8", "replace").casefold()
    except OSError as error:
        raise SpeechNativeProfileError(f"cannot read profile server log: {error}") from error

    def hits(markers: Sequence[str]) -> list[str]:
        return [marker for marker in markers if marker in text]

    return {
        "oom_marker_hits": hits(_OOM_MARKERS),
        "host_spill_marker_hits": hits(_HOST_SPILL_MARKERS),
        "runaway_marker_hits": hits(_RUNAWAY_MARKERS),
        "mmproj_free_chunk_count": text.count("decoded mmproj-free speech feature chunk"),
    }


def _profile_geometry(values: Mapping[str, object], slot_count: int) -> dict[str, int]:
    args = _server_args(values)
    try:
        np_index = args.index("-np")
        context_index = args.index("-c")
        configured_slots = int(args[np_index + 1])
        context_tokens = int(args[context_index + 1])
    except (ValueError, IndexError) as error:
        raise SpeechNativeProfileError(
            "profile server_args must carry integer -np and -c values"
        ) from error
    if configured_slots != slot_count or context_tokens <= 0:
        raise SpeechNativeProfileError(
            "profile_slot_count must equal server_args -np and context must be positive"
        )
    return {
        "context_tokens_total": context_tokens,
        "context_tokens_per_slot": context_tokens // configured_slots,
    }


def _write_exclusive_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    except FileExistsError as error:
        raise SpeechNativeProfileError(f"profile artifact already exists: {path}") from error


def _write_exclusive_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
    except FileExistsError as error:
        raise SpeechNativeProfileError(f"profile artifact already exists: {path}") from error


def _cli_speech_native_profile(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    root = data_root()
    lock = load_lock(umbrella_lock_path())
    composed = compose(repo_root, args.model, args.dataset, args.baseline, args.experiment)
    values = composed.values
    plan = ExecutionPlan(**json.loads(Path(args.plan).read_text(encoding="utf-8"))).validate()
    split_ids, split_hash, split_role = load_split(
        repo_root, _require_string(values, "split_name"), lock, root
    )
    expected_protocol = protocol_hash(composed.config_hash, str(values["arm"]), split_hash)
    if (
        plan.split_identity_hash != split_hash
        or plan.split_role != split_role
        or plan.protocol_hash != expected_protocol
        or plan.carrier_lock_key != values.get("carrier_lock_key")
    ):
        raise SpeechNativeProfileError("execution plan does not match the composed profile")
    run_dir = Path(args.run_dir).resolve()
    if run_dir.name != plan.attempt_id:
        raise SpeechNativeProfileError("profile run_dir basename must equal plan.attempt_id")
    run_dir.mkdir(parents=True, exist_ok=False)
    plan_copy_path = run_dir / f"{plan.run_id}.plan.json"
    _write_exclusive_json(plan_copy_path, asdict(plan))

    dataset_path = repo_root / "configs" / "dataset" / f"{args.dataset}.json"
    gate_view = load_speech_native_engineering_gate(
        dataset_path,
        data_root=root,
        expected_count=_require_positive_int(values, "count"),
        expected_split_name=_require_string(values, "split_name"),
        workers=_require_positive_int(values, "profile_validation_workers"),
    )
    if {sample.sample_id for sample in gate_view.samples} != split_ids:
        raise SpeechNativeProfileError("runtime view ids do not match the verified split")
    binding_relpath = _require_string(values, "speech_native_binding")
    binding_path = repo_root / binding_relpath
    if binding_path.resolve() == repo_root.resolve() or not binding_path.resolve().is_relative_to(
        repo_root.resolve()
    ):
        raise SpeechNativeProfileError("speech-native binding must stay under the repository")
    binding_sha256 = _require_string(values, "speech_native_binding_file_sha256")
    binding_document = _load_binding_document(binding_path, binding_sha256)
    key_cards = _load_key_cards(
        binding_path, binding_sha256
    )
    packet_receipt_path = Path(_require_string(values, "speech_packet_promotion_receipt"))
    packet_bindings = _load_packet_bindings(
        packet_receipt_path,
        _require_string(values, "speech_packet_promotion_receipt_sha256"),
        gate_view.samples,
    )
    key_representation_id = _require_string(values, "key_representation_id")
    audio_key_bindings = None
    if key_representation_id in {"K3", "K4"}:
        audio_key_bindings = _build_audio_key_bindings(
            binding_document,
            _load_packet_index(
                packet_receipt_path,
                _require_string(values, "speech_packet_promotion_receipt_sha256"),
            ),
            key_cards,
        )
    feature_root = Path(_require_string(values, "speech_feature_root"))
    if packet_receipt_path.parent.resolve() != feature_root.resolve():
        raise SpeechNativeProfileError("packet promotion receipt must live at speech_feature_root")
    raw_order_ids = values.get("profile_key_order_ids")
    if not isinstance(raw_order_ids, list) or not raw_order_ids or not all(
        isinstance(item, str) for item in raw_order_ids
    ):
        raise SpeechNativeProfileError("profile_key_order_ids must be a non-empty string list")
    slot_count = _require_positive_int(values, "profile_slot_count")
    geometry = _profile_geometry(values, slot_count)
    queue_multiplier = _require_positive_int(values, "profile_queue_depth_multiplier")
    result_mode = values.get("speech_native_result_mode", "hash-only")
    if result_mode not in {"hash-only", "predictions"}:
        raise SpeechNativeProfileError(
            "speech_native_result_mode must be 'hash-only' or 'predictions'"
        )
    contact_ceiling = values.get("speech_native_contact_ceiling_per_task", 1)
    if (
        isinstance(contact_ceiling, bool)
        or not isinstance(contact_ceiling, int)
        or contact_ceiling <= 0
    ):
        raise SpeechNativeProfileError(
            "speech_native_contact_ceiling_per_task must be a positive integer"
        )
    top_k = values.get("speech_native_top_k", 3)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise SpeechNativeProfileError("speech_native_top_k must be a positive integer")
    prompt_policy_id = values.get(
        "matcher_prompt_policy_id", "speech-native-json-copy-v2"
    )
    if not isinstance(prompt_policy_id, str) or not prompt_policy_id:
        raise SpeechNativeProfileError(
            "matcher_prompt_policy_id must be a non-empty string"
        )
    verifier_policy_id = values.get(
        "matcher_verifier_policy_id", "speech-native-compatibility-v1"
    )
    if not isinstance(verifier_policy_id, str) or not verifier_policy_id:
        raise SpeechNativeProfileError(
            "matcher_verifier_policy_id must be a non-empty string"
        )
    agent_aggregator_id = values.get(
        "speech_native_agent_aggregator_id",
        "m3-majority-canonical-tie-v1",
    )
    if not isinstance(agent_aggregator_id, str) or not agent_aggregator_id:
        raise SpeechNativeProfileError(
            "speech_native_agent_aggregator_id must be a non-empty string"
        )
    agent_policy_id = values.get(
        "speech_native_agent_policy_id",
        "m1-m3-disagreement-escalation-v1",
    )
    if not isinstance(agent_policy_id, str) or not agent_policy_id:
        raise SpeechNativeProfileError(
            "speech_native_agent_policy_id must be a non-empty string"
        )
    dispatch_granularity = values.get("speech_native_dispatch_granularity", "task")
    if dispatch_granularity not in {"task", "contact"}:
        raise SpeechNativeProfileError(
            "speech_native_dispatch_granularity must be 'task' or 'contact'"
        )
    mechanism_control_id = values.get("speech_native_mechanism_control_id", "matched")
    if mechanism_control_id not in {
        "matched",
        "speech-swap-v1",
        "key-text-shuffle-v1",
    }:
        raise SpeechNativeProfileError("unknown speech-native mechanism control")
    tasks = build_profile_tasks(
        samples=gate_view.samples,
        packet_bindings=packet_bindings,
        key_cards=key_cards,
        order_ids=raw_order_ids,
        decoding_params=values.get("decoding_params", {}),
        key_representation_id=key_representation_id,
        matcher_policy_id=_require_string(values, "matcher_policy_id"),
        top_k=top_k,
        prompt_policy_id=prompt_policy_id,
        verifier_policy_id=verifier_policy_id,
        audio_key_bindings=audio_key_bindings,
        mechanism_control_id=mechanism_control_id,
        agent_policy_id=agent_policy_id,
        agent_aggregator_id=agent_aggregator_id,
    )
    planned_contact_ceiling = len(tasks) * contact_ceiling
    if planned_contact_ceiling != plan.planned_model_calls:
        raise SpeechNativeProfileError(
            f"profile expands to a {planned_contact_ceiling}-contact ceiling but plan registers "
            f"{plan.planned_model_calls}"
        )

    runtime_receipt = load_runtime_receipt(resolve_runtime_receipt_path(repo_root, values))
    model_root_value = model_materialization_root(values)
    model_root = Path(model_root_value) if model_root_value is not None else None
    from ...contracts import FrozenCoreGate

    frozen_gate = FrozenCoreGate.for_study_repo(
        repo_root,
        root,
        Path(args.runtime_root),
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
        model_root=model_root,
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values),
    )
    session_receipt_path = run_dir / f"{plan.run_id}.session-receipt.json"
    stop_receipt_path = run_dir / f"{plan.run_id}.session-stop-receipt.json"
    audit_path = run_dir / f"{plan.run_id}.mmproj-audit.json"
    attempt_server_log_path = run_dir / f"{plan.run_id}.server.log"
    flight_receipt_path = run_dir / "flight-receipt.json"
    decisions_path = run_dir / "decisions.jsonl"
    runtime_root = Path(args.runtime_root)
    server_args = _server_args(values)
    server_env = _server_env(values)
    role = runtime_receipt.get("role", "legacy")
    source_session_receipt = getattr(args, "session_receipt", None)
    source_session_receipt_sha256: str | None = None
    owns_session_process = source_session_receipt is None
    if source_session_receipt is None:
        session = start_session(
            runtime_root=runtime_root,
            data_root=root,
            runtime_receipt=runtime_receipt,
            host=args.host,
            port=args.port,
            session_id=f"{plan.run_id}-{plan.attempt_id}",
            extra_argv=server_args,
            extra_env=server_env,
            receipt_path=session_receipt_path,
            server_log_path=attempt_server_log_path,
            role=role,
            model_root=model_root,
        )
        active_server_log_path = attempt_server_log_path
        server_log_start_offset = 0
    else:
        source_path = Path(source_session_receipt).resolve()
        source_hash_before = _sha256_file(source_path)
        session = attach_session(
            source_path,
            runtime_receipt=runtime_receipt,
            runtime_root=runtime_root,
        )
        source_hash_after = _sha256_file(source_path)
        if source_hash_after != source_hash_before:
            raise SpeechNativeProfileError(
                "resident session receipt changed while it was being attached"
            )
        model_argv = _model_file_argv(
            root,
            _pinned_model_files(runtime_receipt),
            role=str(role),
            model_root=model_root,
        )
        _assert_reusable_session_profile(
            session,
            host=args.host,
            port=args.port,
            model_argv=model_argv,
            server_args=server_args,
            server_env=server_env,
        )
        if session.server_log_path is None:
            raise SpeechNativeProfileError(
                "resident speech-native service must persist a server log"
            )
        active_server_log_path = Path(session.server_log_path)
        prior_server_scan = _scan_server_log(active_server_log_path)
        if any(
            prior_server_scan[field]
            for field in (
                "oom_marker_hits",
                "host_spill_marker_hits",
                "runaway_marker_hits",
            )
        ):
            raise SpeechNativeProfileError(
                "resident speech-native service log contains a prior fatal marker; "
                "restart the service before reuse"
            )
        try:
            server_log_start_offset = active_server_log_path.stat().st_size
        except OSError as error:
            raise SpeechNativeProfileError(
                f"cannot stat resident speech-native server log: {error}"
            ) from error
        write_session_receipt(session_receipt_path, session)
        source_session_receipt_sha256 = source_hash_before
    client: FrozenCoreClient | None = None
    close_summary: dict[str, object] | None = None
    sampler = resolve_resource_sampler()
    resource_summary: Mapping[str, object] = {}
    outcomes = ()
    failure: BaseException | None = None
    request_started = False
    try:
        _write_inference_process_audit(session, audit_path)
        transport_factory = TRANSPORTS.resolve(str(values["transport"]))
        transport = transport_factory(
            values,
            root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=Path(args.runtime_root),
        )
        binding = build_payload_binding(
            carrier_lock_key=plan.carrier_lock_key,
            samples=gate_view.samples,
            data_root=root,
            carrier_root=asset_dir(lock, plan.carrier_lock_key, root),
        )
        client = FrozenCoreClient(
            plan=plan,
            gate=frozen_gate,
            transport=transport,
            run_dir=run_dir,
            binding=binding,
            arm="speech-feature-query",
            request_id_prefix="speech-native-profile",
            speech_feature_root=feature_root,
            speech_packet_bindings=packet_bindings,
        )
        sampler.start()
        sampler.begin_request_window()
        request_started = True
        outcomes = run_speech_native_match_tasks(
            core_client=client,
            tasks=tasks,
            slot_count=slot_count,
            queue_depth=slot_count * queue_multiplier,
            dispatch_granularity=dispatch_granularity,
            trace_run_id=plan.run_id,
            trace_flusher=client.flush_trace_buffer,
        )
    except BaseException as error:  # one-shot: record, stop, abort, re-raise
        failure = error
    finally:
        if request_started:
            sampler.end_request_window()
        sampler.stop()
        resource_summary = sampler.summary()
        if client is not None:
            try:
                close_summary = client.close()
            except BaseException as close_error:
                if failure is None:
                    failure = close_error
        _release_speech_native_session(
            session,
            owns_process=owns_session_process,
            runtime_receipt=runtime_receipt,
            runtime_root=runtime_root,
            receipt_path=stop_receipt_path,
        )

    attempt = AttemptStore(Path(root) / "attempts").handle(plan.run_id, str(plan.attempt_id))
    attempt_exists = attempt.path.is_file()
    gpu_seconds = resource_summary.get("gpu_seconds")
    if (
        attempt_exists
        and isinstance(gpu_seconds, (int, float))
        and not isinstance(gpu_seconds, bool)
    ):
        attempt.record_gpu_seconds(float(gpu_seconds))
    server_scan = _scan_server_log(
        active_server_log_path, start_offset=server_log_start_offset
    )
    actual_contact_count = sum(outcome.decision.calls for outcome in outcomes)
    if result_mode == "predictions" and failure is None:
        task_by_id = {task.task_id: task for task in tasks}
        _write_exclusive_jsonl(
            decisions_path,
            tuple(
                {
                    "schema": "saea-speech-native-decision-v1",
                    "task_id": outcome.task_id,
                    "sample_id": (
                        task_by_id[outcome.task_id].scoring_sample_id
                        or task_by_id[outcome.task_id].sample.sample_id
                    ),
                    "query_sample_id": task_by_id[outcome.task_id].sample.sample_id,
                    "mechanism_control_id": task_by_id[
                        outcome.task_id
                    ].mechanism_control_id,
                    "speech_packet_sha256": task_by_id[outcome.task_id].query_descriptor[
                        "sha256"
                    ],
                    "key_representation_id": outcome.decision.key_representation_id,
                    "matcher_policy_id": outcome.decision.matcher_policy_id,
                    "key_id": outcome.decision.key_id,
                    "predicted_value_label": outcome.decision.value_label,
                    "top_key_ids": list(outcome.decision.top_key_ids),
                    "calls": outcome.decision.calls,
                    "parse_failure": outcome.decision.parse_failure,
                    "agent_policy_id": outcome.decision.agent_policy_id,
                    "agent_actions": list(outcome.decision.agent_actions),
                    "agent_escalated": outcome.decision.agent_escalated,
                    "agent_vote_key_ids": list(
                        outcome.decision.agent_vote_key_ids
                    ),
                    "agent_steps": list(outcome.decision.agent_steps),
                    "agent_aggregator_id": outcome.decision.agent_aggregator_id,
                    "verifier_scores": {
                        key_id: {
                            "compatible": compatible,
                            "confidence": confidence,
                        }
                        for key_id, (
                            compatible,
                            confidence,
                        ) in outcome.decision.verifier_scores.items()
                    },
                    "response_text_sha256": [
                        hashlib.sha256(text.encode("utf-8")).hexdigest()
                        for text in outcome.decision.raw_responses
                    ],
                }
                for outcome in outcomes
            ),
        )
    receipt: dict[str, object] = {
        "schema": "saea-speech-native-profile-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "FAILED" if failure is not None else "COMPLETED",
        "run_id": plan.run_id,
        "attempt_id": plan.attempt_id,
        "config_hash": composed.config_hash,
        "protocol_hash": plan.protocol_hash,
        "split_identity_hash": plan.split_identity_hash,
        "profile": {
            "slot_count": slot_count,
            "queue_depth": slot_count * queue_multiplier,
            "task_count": len(tasks),
            "key_card_count": len(key_cards),
            "key_order_ids": list(raw_order_ids),
            "key_representation_id": values["key_representation_id"],
            "matcher_policy_id": values["matcher_policy_id"],
            "matcher_prompt_policy_id": prompt_policy_id,
            "matcher_verifier_policy_id": verifier_policy_id,
            "agent_policy_id": agent_policy_id,
            "agent_aggregator_id": agent_aggregator_id,
            "dispatch_granularity": dispatch_granularity,
            "mechanism_control_id": mechanism_control_id,
            "query_mapping_sha256": _canonical_sha256(
                {
                    (task.scoring_sample_id or task.sample.sample_id): task.sample.sample_id
                    for task in tasks
                }
            ),
            "key_text_mapping_sha256": (
                _canonical_sha256(
                    {
                        card.key_id: key_cards[(index + 1) % len(key_cards)].key_id
                        for index, card in enumerate(key_cards)
                    }
                )
                if mechanism_control_id == "key-text-shuffle-v1"
                else None
            ),
            "semantic_result_read": False,
            "result_mode": result_mode,
            "contact_ceiling_per_task": contact_ceiling,
            "planned_contact_ceiling": planned_contact_ceiling,
            "actual_contact_count": actual_contact_count,
            "top_k": top_k,
            **geometry,
        },
        "resource": dict(resource_summary),
        "server_log_scan": server_scan,
        "process_audit_sha256": _sha256_file(audit_path),
        "session_receipt_sha256": _sha256_file(session_receipt_path),
        "session_stop_receipt_sha256": (
            _sha256_file(stop_receipt_path) if stop_receipt_path.is_file() else None
        ),
        "session_lifecycle": {
            "mode": "attempt-owned" if owns_session_process else "resident-attached",
            "resident_reused": not owns_session_process,
            "source_session_receipt_sha256": source_session_receipt_sha256,
            "server_log_path": str(active_server_log_path),
            "server_log_start_offset": server_log_start_offset,
        },
        "packet_promotion_receipt_sha256": _sha256_file(packet_receipt_path),
        "binding_file_sha256": _sha256_file(binding_path),
        "response_text_sha256": [
            hashlib.sha256(text.encode("utf-8")).hexdigest()
            for outcome in outcomes
            for text in outcome.decision.raw_responses
        ],
        "parse_failure_count": sum(
            1 for outcome in outcomes if outcome.decision.parse_failure
        ),
        "request_failures": [] if failure is None else [f"{type(failure).__name__}: {failure}"],
        "close": close_summary,
    }
    if decisions_path.is_file():
        receipt["decisions"] = {
            "path": decisions_path.name,
            "sha256": _sha256_file(decisions_path),
            "count": len(outcomes),
            "contains_gold_labels": False,
        }
    trace_usage: Mapping[str, object] = {}
    trace_speech_query: Mapping[str, object] = {}
    completion_issues: tuple[str, ...] = ()
    if close_summary is not None:
        cost = close_summary.get("cost", {})
        if not isinstance(cost, Mapping):
            raise SpeechNativeProfileError("profile close summary cost is malformed")
        trace_path = run_dir / f"{plan.run_id}.trace.jsonl"
        timing_rows = close_summary.get("timings", [])
        if trace_path.is_file():
            trace_usage = _trace_usage_summary(trace_path)
            receipt["trace_usage"] = trace_usage
            expected_queries: dict[str, Mapping[str, str]] = {}
            for task in tasks:
                sample_id = task.sample.sample_id
                descriptor = dict(task.query_descriptor)
                previous = expected_queries.get(sample_id)
                if previous is not None and dict(previous) != descriptor:
                    raise SpeechNativeProfileError(
                        "one query sample is bound to conflicting speech packets"
                    )
                expected_queries[sample_id] = descriptor
            trace_speech_query = _trace_speech_query_summary(
                trace_path,
                expected_queries=expected_queries,
            )
            receipt["trace_speech_query"] = trace_speech_query
            receipt["trace_sha256"] = _sha256_file(trace_path)
        receipt["trace_manifest_sha256"] = _sha256_file(
            run_dir / f"{plan.run_id}.trace-manifest.json"
        )
        if timing_rows and trace_path.is_file():
            timing = profile_timing_metrics(
                timing_rows,
                slot_count=slot_count,
                prompt_tokens=int(cost.get("prompt_tokens_total", 0)),
                completion_tokens=int(cost.get("completion_tokens_total", 0)),
            )
            receipt["timing"] = timing
            median_util = resource_summary.get("request_gpu_utilization_median_pct")
            p10_util = resource_summary.get("request_gpu_utilization_p10_pct")
            receipt["eligibility"] = {
                "maximum_prompt_fits_one_slot": (
                    trace_usage["max_prompt_tokens"]
                    + trace_usage["max_completion_tokens"]
                    <= geometry["context_tokens_per_slot"]
                ),
                "zero_request_failures": failure is None,
                "zero_oom_markers": not server_scan["oom_marker_hits"],
                "zero_host_spill_markers": not server_scan["host_spill_marker_hits"],
                "zero_runaway_markers": not server_scan["runaway_marker_hits"],
                "gpu_median_at_least_95": (
                    isinstance(median_util, (int, float))
                    and not isinstance(median_util, bool)
                    and float(median_util) >= 95.0
                ),
                "gpu_p10_at_least_90": (
                    isinstance(p10_util, (int, float))
                    and not isinstance(p10_util, bool)
                    and float(p10_util) >= 90.0
                ),
                "slot_occupancy_at_least_90": timing["slot_occupancy_pct"] >= 90.0,
            }
            eligibility = receipt["eligibility"]
            assert isinstance(eligibility, Mapping)
            receipt["eligible"] = all(bool(value) for value in eligibility.values())
        if failure is None:
            completion_issues = _profile_completion_issues(
                calls_used=int(cost.get("calls_used", -1)),
                actual_contact_count=actual_contact_count,
                task_count=len(tasks),
                planned_contact_ceiling=planned_contact_ceiling,
                request_failure_count=len(receipt["request_failures"]),
                server_scan=server_scan,
                trace_usage=trace_usage,
                trace_speech_query=trace_speech_query,
            )
            receipt["completion_issues"] = list(completion_issues)
    elif failure is None:
        completion_issues = ("profile close summary is missing",)
        receipt["completion_issues"] = list(completion_issues)
    _write_exclusive_json(flight_receipt_path, receipt)

    if failure is not None:
        if attempt_exists:
            attempt.mark_aborted(
                f"speech-native profile failed: {type(failure).__name__}: {failure}"
            )
        raise failure
    if not attempt_exists:
        raise SpeechNativeProfileError(
            "profile completed without opening its durable attempt accounting record"
        )
    if completion_issues:
        attempt.mark_aborted("speech-native profile completion checks failed")
        raise SpeechNativeProfileError("profile completion checks failed; see flight receipt")
    attempt.mark_finalized()
    print(
        json.dumps(
            {
                "run_id": plan.run_id,
                "attempt_id": plan.attempt_id,
                "flight_receipt": str(flight_receipt_path),
                "status": "FINALIZED",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cli_speech_native_read(args: argparse.Namespace) -> int:
    report = read_speech_native_predictions(
        attempt_dirs=tuple(Path(path) for path in args.attempt_dir),
        binding_path=Path(args.binding),
        binding_sha256=args.binding_sha256,
        split_name=args.split_name,
    )
    output = Path(args.output)
    _write_exclusive_json(output, report)
    print(
        json.dumps(
            {
                "output": str(output),
                "selected_cell_id": report["selected_cell_id"],
                "aggregates": report["aggregates"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cli_speech_native_action_audit(args: argparse.Namespace) -> int:
    report = audit_speech_native_action_support(
        attempt_dir=Path(args.attempt_dir),
        attempt_record_path=Path(args.attempt_record),
        attempt_record_sha256=args.attempt_record_sha256,
        flight_receipt_sha256=args.flight_receipt_sha256,
        decisions_sha256=args.decisions_sha256,
        trace_sha256=args.trace_sha256,
    )
    output = Path(args.output)
    _write_exclusive_json(output, report)
    print(
        json.dumps(
            {
                "output": str(output),
                "action_sensitive_count": report["action_sensitive_count"],
                "action_support_threshold_met": report[
                    "action_support_threshold_met"
                ],
                "gold_read": False,
                "effectiveness_eligible": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


__all__ = [
    "SpeechNativeProfileError",
    "_cli_speech_native_profile",
    "_cli_speech_native_read",
    "build_profile_tasks",
    "profile_timing_metrics",
    "read_speech_native_predictions",
]
