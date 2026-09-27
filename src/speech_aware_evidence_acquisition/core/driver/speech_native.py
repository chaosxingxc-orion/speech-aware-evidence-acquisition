"""Speech-native GPU-profile flight through the existing ``saea-driver``.

This is a driver module, not a standalone experiment script. It reuses the
repository's receipt-pinned session, frozen gate, attempt accounting,
speech-feature client, bounded matcher dispatcher, resource sampler, and
trace machinery. Profile flights are engineering-only: response text is
hashed in process and never copied into the profile receipt.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import io
from itertools import permutations
import json
import math
import re
import statistics
import subprocess
import threading
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping, Sequence

from ...contracts import ExecutionPlan
from ...core.model.transport import _ordered_speech_feature_content
from ...core.model.speech_features import load_speech_feature_packets
from ...data.lock import asset_dir, data_root, load_lock, umbrella_lock_path
from ...data.slurp import load_slurp_train_material
from ...e0.artifacts import REPO_ROOT
from ...rails import FrozenCoreClient, build_payload_binding
from ...rails.core_client import _speech_supply_evidence_id
from ...rails.probes.pslu_flight import (
    DecisionBoundaryV1,
    DecisionFactorV1,
    DecisionGraphV1,
    FactorLinkStateV1,
    KeyCardV1,
    PsluFlightError,
    SPEECH_NATIVE_KNOWLEDGE_POLICY_ID,
    SPEECH_NATIVE_REQUEST_LAYOUTS,
    SpeechNativeMatchTask,
    build_speech_native_knowledge_snapshot,
    load_speech_native_engineering_gate,
    decision_boundary_path,
    expand_decision_graph_candidates,
    expand_decision_graph_neighborhood,
    parse_grounded_query_state,
    partition_speech_native_train_knowledge,
    run_openjiuwen_speech_native_match_tasks,
    run_speech_native_match_tasks,
    validate_openjiuwen_speech_native_match_tasks,
)
from ..attempts import AttemptStore
from ..base import declared_derived_media_roots
from ..configured_transport import build_configured_transport
from ..config import (
    compose,
    d1_evidence_supplement_relpath,
    d1_evidence_supplement_sha256,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_lock_key,
    model_materialization_root,
    protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from ..resources import NOT_AVAILABLE, resolve_resource_sampler
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
_PROMPT_EVAL_TIMING = re.compile(
    r"prompt eval time\s*=\s*[0-9.]+\s*ms\s*/\s*(\d+)\s+tokens"
)
_SPEECH_FEATURE_BATCH = re.compile(
    r"decoded cross-slot speech feature batch,\s*"
    r"n_slots\s*=\s*(\d+),\s*n_tokens\s*=\s*(\d+)"
)
_SPECULATIVE_DRAFT_TIMING = re.compile(
    r"draft acceptance\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*"
    r"\(\s*(\d+)\s+accepted\s*/\s*(\d+)\s+generated\s*\),\s*"
    r"mean acceptance length\s*=\s*([0-9]+(?:\.[0-9]+)?)"
)
_SERVER_LOG_CLOCK = re.compile(rb"^(\d+)\.(\d+)\.(\d+)\.(\d+) ")
_SERVER_SLOT_LAUNCH = re.compile(
    rb"\bslot\s+launch_slot_: id\s+(\d+) \| task\s+(-?\d+)"
)
_SERVER_SLOT_RELEASE = re.compile(rb"\bslot\s+release: id\s+(\d+) \| task\s+(-?\d+)")
_PREFIX_REUSE_PROMPT_ORDERS = frozenset(
    {"speech-query-prefix-v2", "knowledge-speech-state-v2"}
)
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
_M7_POLICY_ID = "knowledge-grounded-multistate-action-support-v1"
_M7_AGGREGATOR_ID = "action-support-primary-control-v1"
_M7_STATE_POLICY_IDS = (
    "balanced-evidence-v1",
    "primary-challenge-v1",
    "retrieval-gap-v1",
)
_M7_SUCCESS_ACTIONS = (
    "match:speech-only-primary",
    "retrieve:speech-only",
    *tuple(f"explore:{policy_id}" for policy_id in _M7_STATE_POLICY_IDS),
    "select:retain-primary-for-support",
)
_M8_POLICY_ID = "speech-conditioned-pairwise-boundary-support-v1"
_M8_AGGREGATOR_ID = "pairwise-boundary-primary-control-v1"
_M9_POLICY_ID = "speech-conditioned-factor-graph-action-support-v1"
_M9_AGGREGATOR_ID = "factor-graph-primary-control-v1"
_M9_COMMON_ACTIONS = (
    "match:speech-only-primary",
    "retrieve:speech-only",
    "link:knowledge-factors",
    "tool:expand-factor-graph",
    "rerank:speech-plus-factor-state",
)
_M10_POLICY_ID = "speech-conditioned-candidate-evidence-action-support-v1"
_M10_AGGREGATOR_ID = "candidate-evidence-primary-control-v1"
_M11_POLICY_ID = "speech-conditioned-adaptive-evidence-gap-v1"
_M11_KEY_CONDITIONED_POLICY_ID = "speech-conditioned-adaptive-evidence-gap-v2"
_M11_POLICY_IDS = frozenset({_M11_POLICY_ID, _M11_KEY_CONDITIONED_POLICY_ID})
_M11_AGGREGATOR_ID = "adaptive-evidence-gap-primary-control-v1"
_M11_DECISION_GRAPH_IDS = frozenset(
    {
        "slurp-data-derived-decision-graph-v2",
        "slurp-shared-action-entity-decision-graph-v3",
        "slurp-signature-lexical-decision-graph-v4",
        "slurp-signature-complete-decision-graph-v5",
    }
)
_M11_OOF_POLICY_ID = "speaker-grouped-oof-information-advantage-v1"
_M11_MEMORY_HOLDOUT_EVALUATION_ID = "discovery-memory-to-speaker-unseen-holdout-v1"
_M11_INFORMATION_FLOW_SCHEMA = "m11-information-flow-v1"
_M11_OOF_ACTION_IDS = (
    "select-retrieval-top1",
    "select-candidate-action-state",
    "acquire-boundary-stable",
)
_M11_OOF_ACTION_CALLS = {
    "retain-primary": 3,
    "select-retrieval-top1": 3,
    "select-candidate-action-state": 3,
    "acquire-boundary-stable": 5,
}
_M11_READER_CONTRACT_V1 = {
    "support_minimum_query_count": 100,
    "support_minimum_top_k_reachable": 100,
    "support_minimum_action_variable_queries": 24,
    "support_minimum_adaptive_boundary_queries": 18,
    "support_minimum_boundary_non_primary_actions": 12,
    "support_minimum_incremental_boundary_repairs": 3,
    "support_minimum_oracle_gain": 6,
    "support_maximum_mechanism_failures": 0,
    "oof_fold_count": 3,
    "oof_minimum_state_support": 5,
    "oof_minimum_changed_prediction_support": 3,
    "oof_minimum_helpful_transitions": 2,
    "oof_minimum_estimated_net_gain": 2,
    "oof_maximum_harmful_transitions": 0,
    "promotion_minimum_net_gain": 3,
    "promotion_minimum_positive_folds": 2,
    "promotion_minimum_worst_fold_delta": 0,
    "promotion_maximum_harmful_transitions": 1,
    "promotion_minimum_action_rate": 0.05,
    "promotion_maximum_action_rate": 0.5,
    "promotion_requires_lower_mean_calls": True,
}
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


#: The two speech-native agent executors, in the ONE spelling each has. The
#: 2026-09-08 openJiuwen assessment, section 5.4 item 3: "name the executor
#: explicitly, in one spelling" -- a cell that does not name its executor
#: cannot state which harness produced its number.
SPEECH_NATIVE_AGENT_EXECUTOR_IDS = frozenset(
    {"legacy-contact-dag-v1", "openjiuwen-workflow-v1"}
)
SPEECH_NATIVE_AGENT_EXECUTOR_KEY = "speech_native_agent_executor_id"


def resolve_speech_native_agent_executor_id(values: Mapping[str, object]) -> str:
    """This cell's speech-native agent executor, named or refused.

    **Executor retirement (owner Decision 12-F item #9, 2026-09-08).** The
    silent default to ``legacy-contact-dag-v1`` is GONE. Thirty-two
    speech-native baselines reached that executor by declaring nothing at
    all, so no cell among them could say which harness produced its number;
    every one of them now names it, and a fragment that does not is refused
    here -- before any packet is promoted and before any contact is spent.

    ``legacy-contact-dag-v1`` remains ADMITTED, and that is not a
    half-measure. The openJiuwen speech-native executor is an M1/M2
    one-or-two-contact vertical slice; none of those 32 baselines composes
    into it (M0/M3/M5-M11, ceilings 1-20), so re-pointing them would refuse
    them rather than port them. What RETIRES the legacy path is that it can
    no longer be reached by accident: its remaining users are exactly the
    fragments that spell it, and shrinking that list is the per-carrier
    phase-program work ``configs/baseline/slurp-phase-direct-only-v1.json``
    already demonstrates for the simplest of them.

    One resolver for both call sites -- the profile flight and
    finalize-from-disk -- so the two can never disagree about what a cell
    declared.
    """

    if SPEECH_NATIVE_AGENT_EXECUTOR_KEY not in values:
        raise SpeechNativeProfileError(
            f"{SPEECH_NATIVE_AGENT_EXECUTOR_KEY} is required: the silent default "
            "to 'legacy-contact-dag-v1' was retired on 2026-09-08 (owner Decision "
            "12-F), because a cell that does not name its executor cannot state "
            "which harness produced its number. Declare 'openjiuwen-workflow-v1' "
            "(the M1/M2 speech-native agent graph) or 'legacy-contact-dag-v1' "
            "(the retiring contact DAG) in the baseline fragment"
        )
    executor_id = values[SPEECH_NATIVE_AGENT_EXECUTOR_KEY]
    if executor_id not in SPEECH_NATIVE_AGENT_EXECUTOR_IDS:
        raise SpeechNativeProfileError(
            f"{SPEECH_NATIVE_AGENT_EXECUTOR_KEY} must be 'legacy-contact-dag-v1' "
            "or 'openjiuwen-workflow-v1'"
        )
    return str(executor_id)


def _m11_reader_contract_from_values(
    values: Mapping[str, object], matcher_policy_id: object
) -> tuple[str | None, dict[str, object] | None]:
    """Validate the optional preregistered M11 model-free reader contract."""

    policy_id = values.get("speech_native_training_free_reader_policy_id")
    contract = values.get("speech_native_training_free_reader_contract")
    if policy_id is None and contract is None:
        return None, None
    if (
        matcher_policy_id != "M11"
        or policy_id != _M11_OOF_POLICY_ID
        or contract != _M11_READER_CONTRACT_V1
    ):
        raise SpeechNativeProfileError(
            "speech-native training-free reader contract is unknown or has drifted"
        )
    return _M11_OOF_POLICY_ID, dict(_M11_READER_CONTRACT_V1)


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
            trajectories[index]["primary_key_id"] == trajectories[index]["gold_key_id"]
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


def _m3_aggregate(trajectory: Mapping[str, str | None], mode: str) -> str | None:
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
                trigger == "disagreement" and primary != trajectory["canonical_key_id"]
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
                    int(fold["correct_delta_vs_primary"] > 0) for fold in speaker_folds
                ),
                "nonnegative_delta_fold_count": sum(
                    int(fold["correct_delta_vs_primary"] >= 0) for fold in speaker_folds
                ),
                "worst_fold_accuracy": min(
                    float(fold["accuracy"]) for fold in speaker_folds
                ),
                "worst_fold_delta_vs_primary": min(
                    int(fold["correct_delta_vs_primary"]) for fold in speaker_folds
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
            state_indices = [
                index for index in train_indices if states[index] == state_id
            ]
            correct_by_action = {
                action_id: sum(
                    action_predictions[index][action_id] == frozen[index]["gold_key_id"]
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
        reward_spread = max(correct_by_action.values()) - min(
            correct_by_action.values()
        )
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
        str(top_ids.index(primary) + 1)
        if primary is not None and primary in top_ids
        else "0"
    )
    parsed_scores = {
        str(key_id): (bool(raw[0]), float(raw[1])) for key_id, raw in scores.items()
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


def _episodic_action_contacts(trajectory: Mapping[str, object], action_id: str) -> int:
    initial = int(trajectory["primary_calls"]) + int(trajectory["canonical_calls"])
    if action_id in {"primary", "canonical-primary-fallback"}:
        return initial
    return initial + int(trajectory["reverse_calls"]) + int(trajectory["rotate_calls"])


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
                    (
                        _episodic_distance(states[index], states[train_index]),
                        train_index,
                    )
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


_GROUNDED_SEMANTIC_REQUIRED_FIELDS = {
    "sample_id",
    "speaker_id",
    "gold_key_id",
    "primary_key_id",
    "refined_key_id",
    "initial_top_key_ids",
    "refined_top_key_ids",
    "verifier_scores",
    "grounded_query_state",
    "total_calls",
}
_GROUNDED_SEMANTIC_STATE_FIELDS = {
    "domain",
    "operation",
    "target",
    "constraints",
    "exclusions",
    "unresolved_ambiguity",
}
_GROUNDED_SEMANTIC_STATE_WEIGHTS = (2, 2, 1, 1, 1, 1, 1, 1, 1)
_GROUNDED_SEMANTIC_NEIGHBOR_COUNT = 5
_GROUNDED_SEMANTIC_MIN_SUPPORT = 3
_GROUNDED_SEMANTIC_MIN_NET_GAIN = 1
_GROUNDED_SEMANTIC_MAX_HARM = 0
_GROUNDED_SEMANTIC_LEXICAL_WEIGHT = 4.0
_GROUNDED_SEMANTIC_TOKEN = re.compile(r"[a-z0-9]+")


def _validate_grounded_semantic_trajectories(
    trajectories: Sequence[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError(
            "grounded semantic policy requires at least one trajectory"
        )
    for trajectory in frozen:
        if set(trajectory) != _GROUNDED_SEMANTIC_REQUIRED_FIELDS:
            raise SpeechNativeProfileError(
                "grounded semantic policy trajectory is malformed"
            )
        if any(
            not isinstance(trajectory.get(field), str) or not trajectory.get(field)
            for field in (
                "sample_id",
                "speaker_id",
                "gold_key_id",
                "primary_key_id",
                "refined_key_id",
            )
        ):
            raise SpeechNativeProfileError(
                "grounded semantic policy identity is malformed"
            )
        for field in ("initial_top_key_ids", "refined_top_key_ids"):
            value = trajectory.get(field)
            if (
                not isinstance(value, (list, tuple))
                or not value
                or not all(isinstance(key_id, str) and key_id for key_id in value)
                or len(set(value)) != len(value)
            ):
                raise SpeechNativeProfileError(
                    "grounded semantic policy top-key list is malformed"
                )
        scores = trajectory.get("verifier_scores")
        if not isinstance(scores, Mapping):
            raise SpeechNativeProfileError(
                "grounded semantic policy verifier scores are malformed"
            )
        for key_id, raw_score in scores.items():
            if (
                not isinstance(key_id, str)
                or not isinstance(raw_score, (list, tuple))
                or len(raw_score) != 2
                or not isinstance(raw_score[0], bool)
                or isinstance(raw_score[1], bool)
                or not isinstance(raw_score[1], (int, float))
                or not 0.0 <= float(raw_score[1]) <= 100.0
            ):
                raise SpeechNativeProfileError(
                    "grounded semantic policy verifier score is malformed"
                )
        state = trajectory.get("grounded_query_state")
        if (
            not isinstance(state, Mapping)
            or set(state) != _GROUNDED_SEMANTIC_STATE_FIELDS
        ):
            raise SpeechNativeProfileError("grounded semantic query state is malformed")
        if any(
            not isinstance(state.get(field), str) or not state.get(field)
            for field in (
                "domain",
                "operation",
                "target",
                "unresolved_ambiguity",
            )
        ):
            raise SpeechNativeProfileError(
                "grounded semantic query scalar is malformed"
            )
        for field in ("constraints", "exclusions"):
            value = state.get(field)
            if not isinstance(value, (list, tuple)) or not all(
                isinstance(item, str) and item for item in value
            ):
                raise SpeechNativeProfileError(
                    "grounded semantic query list is malformed"
                )
        total_calls = trajectory.get("total_calls")
        if (
            isinstance(total_calls, bool)
            or not isinstance(total_calls, int)
            or total_calls <= 0
        ):
            raise SpeechNativeProfileError(
                "grounded semantic policy contact cost is malformed"
            )
    if len({str(item["speaker_id"]) for item in frozen}) < 3:
        raise SpeechNativeProfileError(
            "grounded semantic policy requires at least three speakers"
        )
    return frozen


def _grounded_semantic_tokens(trajectory: Mapping[str, object]) -> frozenset[str]:
    state = trajectory["grounded_query_state"]
    assert isinstance(state, Mapping)
    values: list[str] = [
        str(state[field])
        for field in ("domain", "operation", "target", "unresolved_ambiguity")
    ]
    for field in ("constraints", "exclusions"):
        raw_values = state[field]
        assert isinstance(raw_values, (list, tuple))
        values.extend(str(value) for value in raw_values)
    return frozenset(_GROUNDED_SEMANTIC_TOKEN.findall(" ".join(values).lower()))


def _grounded_semantic_state(trajectory: Mapping[str, object]) -> tuple[str, ...]:
    primary = str(trajectory["primary_key_id"])
    refined = str(trajectory["refined_key_id"])
    initial_top = tuple(str(value) for value in trajectory["initial_top_key_ids"])
    refined_top = tuple(str(value) for value in trajectory["refined_top_key_ids"])
    raw_scores = trajectory["verifier_scores"]
    assert isinstance(raw_scores, Mapping)
    scores = {
        str(key_id): (bool(raw[0]), float(raw[1])) for key_id, raw in raw_scores.items()
    }

    def compatibility(key_id: str) -> str:
        score = scores.get(key_id)
        if score is None:
            return "missing"
        return "yes" if score[0] else "no"

    selected = scores.get(refined)
    if selected is None:
        margin_bucket = "missing"
    else:
        alternatives = [
            score[1] for key_id, score in scores.items() if key_id != refined
        ]
        margin = selected[1] - max(alternatives) if alternatives else 100.0
        if margin < 0:
            margin_bucket = "negative"
        elif margin == 0:
            margin_bucket = "tie"
        elif margin <= 10:
            margin_bucket = "narrow"
        elif margin <= 30:
            margin_bucket = "medium"
        else:
            margin_bucket = "wide"
    primary_rank = (
        str(refined_top.index(primary) + 1) if primary in refined_top else "0"
    )
    overlap = str(min(len(set(initial_top) & set(refined_top)), 3))
    compatible_count = str(min(sum(int(score[0]) for score in scores.values()), 3))
    return (
        primary,
        refined,
        "same" if primary == refined else "different",
        primary_rank,
        overlap,
        compatible_count,
        compatibility(refined),
        compatibility(primary),
        margin_bucket,
    )


def _grounded_semantic_jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _grounded_semantic_distance(
    left_state: tuple[str, ...],
    left_tokens: frozenset[str],
    right_state: tuple[str, ...],
    right_tokens: frozenset[str],
) -> float:
    discrete = sum(
        weight * int(left_value != right_value)
        for weight, left_value, right_value in zip(
            _GROUNDED_SEMANTIC_STATE_WEIGHTS,
            left_state,
            right_state,
            strict=True,
        )
    )
    return discrete + _GROUNDED_SEMANTIC_LEXICAL_WEIGHT * (
        1.0 - _grounded_semantic_jaccard(left_tokens, right_tokens)
    )


def _evaluate_training_free_grounded_semantic_policy(
    trajectories: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Cross-fit a late grounded-refinement action policy without model updates."""

    frozen = _validate_grounded_semantic_trajectories(trajectories)
    assignments = _speaker_grouped_fold_assignments(frozen)
    states = [_grounded_semantic_state(item) for item in frozen]
    tokens = [_grounded_semantic_tokens(item) for item in frozen]
    predictions: list[str | None] = [None] * len(frozen)
    actions: list[str | None] = [None] * len(frozen)
    memory_audit: list[dict[str, object]] = []

    for fold_index in range(3):
        fold_id = f"fold-{fold_index}"
        train_indices = [
            index
            for index, item in enumerate(frozen)
            if assignments[str(item["speaker_id"])] != fold_id
            and item["primary_key_id"] != item["refined_key_id"]
        ]
        test_indices = [
            index
            for index, item in enumerate(frozen)
            if assignments[str(item["speaker_id"])] == fold_id
        ]
        for index in test_indices:
            primary = str(frozen[index]["primary_key_id"])
            refined = str(frozen[index]["refined_key_id"])
            ranked: list[tuple[float, str, int]] = []
            if primary != refined:
                ranked = sorted(
                    (
                        (
                            _grounded_semantic_distance(
                                states[index],
                                tokens[index],
                                states[train_index],
                                tokens[train_index],
                            ),
                            str(frozen[train_index]["sample_id"]),
                            train_index,
                        )
                        for train_index in train_indices
                    ),
                    key=lambda item: (item[0], item[1]),
                )[:_GROUNDED_SEMANTIC_NEIGHBOR_COUNT]
            neighbors = [item[2] for item in ranked]
            helpful = sum(
                frozen[neighbor]["primary_key_id"] != frozen[neighbor]["gold_key_id"]
                and frozen[neighbor]["refined_key_id"]
                == frozen[neighbor]["gold_key_id"]
                for neighbor in neighbors
            )
            harmful = sum(
                frozen[neighbor]["primary_key_id"] == frozen[neighbor]["gold_key_id"]
                and frozen[neighbor]["refined_key_id"]
                != frozen[neighbor]["gold_key_id"]
                for neighbor in neighbors
            )
            net_gain = helpful - harmful
            accept = (
                primary != refined
                and len(neighbors) >= _GROUNDED_SEMANTIC_MIN_SUPPORT
                and net_gain >= _GROUNDED_SEMANTIC_MIN_NET_GAIN
                and harmful <= _GROUNDED_SEMANTIC_MAX_HARM
            )
            action_id = "accept_refined" if accept else "retain_primary"
            actions[index] = action_id
            predictions[index] = refined if accept else primary
            memory_audit.append(
                {
                    "sample_id": str(frozen[index]["sample_id"]),
                    "fold_id": fold_id,
                    "state_sha256": _canonical_sha256(
                        {
                            "discrete": states[index],
                            "semantic_tokens": sorted(tokens[index]),
                        }
                    ),
                    "action_id": action_id,
                    "neighbor_count": len(neighbors),
                    "helpful_neighbor_count": helpful,
                    "harmful_neighbor_count": harmful,
                    "estimated_net_gain": net_gain,
                    "neighbors": [
                        {
                            "sample_id": sample_id,
                            "distance": distance,
                            "semantic_jaccard": _grounded_semantic_jaccard(
                                tokens[index], tokens[neighbor]
                            ),
                        }
                        for distance, sample_id, neighbor in ranked
                    ],
                }
            )

    if any(prediction is None for prediction in predictions) or any(
        action is None for action in actions
    ):
        raise SpeechNativeProfileError(
            "grounded semantic policy left a held-out trajectory unevaluated"
        )
    assignments_by_speaker = {
        speaker_id: assignments[speaker_id] for speaker_id in sorted(assignments)
    }
    speaker_folds = _speaker_fold_metrics(
        frozen,
        assignments=assignments_by_speaker,
        predictions=predictions,
    )
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )
    correct = sum(
        prediction == item["gold_key_id"]
        for prediction, item in zip(predictions, frozen, strict=True)
    )
    wrong_to_correct = sum(
        item["primary_key_id"] != item["gold_key_id"]
        and prediction == item["gold_key_id"]
        for prediction, item in zip(predictions, frozen, strict=True)
    )
    correct_to_wrong = sum(
        item["primary_key_id"] == item["gold_key_id"]
        and prediction != item["gold_key_id"]
        for prediction, item in zip(predictions, frozen, strict=True)
    )
    action_counts = Counter(str(action) for action in actions)
    accept_count = action_counts["accept_refined"]
    positive_fold_count = sum(
        int(fold["correct_delta_vs_primary"] > 0) for fold in speaker_folds
    )
    worst_fold_delta = min(
        int(fold["correct_delta_vs_primary"]) for fold in speaker_folds
    )
    accept_rate = accept_count / len(frozen)
    promotion_checks = {
        "net_gain_at_least_3": correct - primary_correct >= 3,
        "positive_fold_count_at_least_2": positive_fold_count >= 2,
        "worst_fold_delta_nonnegative": worst_fold_delta >= 0,
        "correct_to_wrong_zero": correct_to_wrong == 0,
        "action_rate_between_0_05_and_0_50": 0.05 <= accept_rate <= 0.50,
    }
    action_oracle_correct = sum(
        item["primary_key_id"] == item["gold_key_id"]
        or item["refined_key_id"] == item["gold_key_id"]
        for item in frozen
    )
    return {
        "policy_id": "speaker-grouped-oof-grounded-semantic-action-advantage-v1",
        "speaker_fold_policy_id": _SPEAKER_FOLD_POLICY_ID,
        "count": len(frozen),
        "correct": correct,
        "accuracy": correct / len(frozen),
        "primary_correct": primary_correct,
        "primary_accuracy": primary_correct / len(frozen),
        "wrong_to_correct_vs_primary": wrong_to_correct,
        "correct_to_wrong_vs_primary": correct_to_wrong,
        "oof_action_counts": dict(sorted(action_counts.items())),
        "non_primary_action_rate": accept_rate,
        "positive_delta_fold_count": positive_fold_count,
        "nonnegative_delta_fold_count": sum(
            int(fold["correct_delta_vs_primary"] >= 0) for fold in speaker_folds
        ),
        "worst_fold_delta_vs_primary": worst_fold_delta,
        "speaker_folds": speaker_folds,
        "mean_realized_contacts": sum(int(item["total_calls"]) for item in frozen)
        / len(frozen),
        "action_variable_count": sum(
            item["primary_key_id"] != item["refined_key_id"] for item in frozen
        ),
        "action_oracle_correct": action_oracle_correct,
        "action_oracle_headroom_vs_primary": action_oracle_correct - primary_correct,
        "action_oracle_status": "diagnostic-only-not-an-admissible-controller",
        "memory_policy": {
            "neighbor_count": _GROUNDED_SEMANTIC_NEIGHBOR_COUNT,
            "minimum_support": _GROUNDED_SEMANTIC_MIN_SUPPORT,
            "minimum_net_gain": _GROUNDED_SEMANTIC_MIN_NET_GAIN,
            "maximum_observed_harm": _GROUNDED_SEMANTIC_MAX_HARM,
            "discrete_state_weights": list(_GROUNDED_SEMANTIC_STATE_WEIGHTS),
            "semantic_jaccard_weight": _GROUNDED_SEMANTIC_LEXICAL_WEIGHT,
            "late_action_only": True,
        },
        "promotion_checks": promotion_checks,
        "promotion_gate_passed": all(promotion_checks.values()),
        "memory_audit": sorted(memory_audit, key=lambda item: str(item["sample_id"])),
    }


def _m7_state_tokens(state: Mapping[str, object]) -> frozenset[str]:
    return frozenset(
        re.findall(
            r"[a-z0-9]+",
            f"{state['domain']} {state['operation']}".lower(),
        )
    )


def _parse_m7_trajectory(
    *,
    row: Mapping[str, object],
    sample_id: str,
    speaker_id: str,
    gold_key_id: str,
    initial_top_ids: tuple[str, ...],
    top_k: int,
    visible_card_by_key: Mapping[str, KeyCardV1],
) -> dict[str, object]:
    """Validate one complete M7 trajectory before any reward is summarized."""

    votes = row.get("agent_vote_key_ids")
    steps = row.get("agent_steps")
    actions = row.get("agent_actions")
    if (
        row.get("agent_policy_id") != _M7_POLICY_ID
        or row.get("agent_aggregator_id") != _M7_AGGREGATOR_ID
        or row.get("agent_escalated") is not True
        or tuple(actions) != _M7_SUCCESS_ACTIONS
        if isinstance(actions, list)
        else True
    ):
        raise SpeechNativeProfileError("M7 action-support identity is malformed")
    if (
        not isinstance(votes, list)
        or len(votes) != 4
        or not all(
            isinstance(vote, str) and vote in visible_card_by_key for vote in votes
        )
        or not isinstance(steps, list)
        or len(steps) != 5
        or row.get("key_id") != votes[0]
        or row.get("verifier_scores") != {}
    ):
        raise SpeechNativeProfileError("M7 action-support trajectory is malformed")
    base_fields = {
        "action_id",
        "key_id",
        "top_key_ids",
        "calls",
        "parse_failure",
    }
    if (
        not isinstance(steps[0], Mapping)
        or set(steps[0]) != base_fields
        or steps[0].get("action_id") != "match:speech-only-primary"
        or steps[0].get("key_id") != votes[0]
        or steps[0].get("top_key_ids") != []
        or steps[0].get("calls") != 1
        or steps[0].get("parse_failure") is not False
        or not isinstance(steps[1], Mapping)
        or set(steps[1]) != base_fields
        or steps[1].get("action_id") != "retrieve:speech-only"
        or steps[1].get("key_id") != initial_top_ids[0]
        or tuple(steps[1].get("top_key_ids", [])) != initial_top_ids
        or steps[1].get("calls") != 1
        or steps[1].get("parse_failure") is not False
    ):
        raise SpeechNativeProfileError("M7 initial action-support stages are malformed")

    branch_fields = base_fields | {
        "state_policy_id",
        "grounded_query_state",
        "verifier_scores",
        "causal_parent_ids",
    }
    branches: list[dict[str, object]] = []
    for branch_index, state_policy_id in enumerate(_M7_STATE_POLICY_IDS, start=2):
        step = steps[branch_index]
        if (
            not isinstance(step, Mapping)
            or set(step) != branch_fields
            or step.get("action_id") != f"explore:{state_policy_id}"
            or step.get("state_policy_id") != state_policy_id
            or step.get("parse_failure") is not False
            or step.get("causal_parent_ids")
            != ["match:speech-only-primary", "retrieve:speech-only"]
            or step.get("key_id") != votes[branch_index - 1]
        ):
            raise SpeechNativeProfileError("M7 grounded branch identity is malformed")
        branch_top_ids = step.get("top_key_ids")
        state_document = step.get("grounded_query_state")
        scores = step.get("verifier_scores")
        if (
            not isinstance(branch_top_ids, list)
            or len(branch_top_ids) != top_k
            or len(set(branch_top_ids)) != top_k
            or not all(key_id in visible_card_by_key for key_id in branch_top_ids)
            or not isinstance(state_document, Mapping)
            or not isinstance(scores, Mapping)
            or set(scores) != set(branch_top_ids)
        ):
            raise SpeechNativeProfileError("M7 grounded branch payload is malformed")
        parsed_state = parse_grounded_query_state(
            json.dumps(
                state_document,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            candidate_key_ids=initial_top_ids,
            cards_by_key=visible_card_by_key,
            key_representation_id="K2",
        )
        if parsed_state is None:
            raise SpeechNativeProfileError(
                "M7 grounded branch citation validation failed"
            )
        normalized_scores: dict[str, tuple[bool, float]] = {}
        for key_id, score_document in scores.items():
            if (
                not isinstance(score_document, Mapping)
                or set(score_document) != {"compatible", "confidence"}
                or not isinstance(score_document.get("compatible"), bool)
                or isinstance(score_document.get("confidence"), bool)
                or not isinstance(score_document.get("confidence"), (int, float))
                or not 0.0 <= float(score_document["confidence"]) <= 100.0
            ):
                raise SpeechNativeProfileError("M7 verifier score is malformed")
            normalized_scores[str(key_id)] = (
                bool(score_document["compatible"]),
                float(score_document["confidence"]),
            )
        compatible_ids = [
            key_id for key_id in branch_top_ids if normalized_scores[key_id][0]
        ]
        selection_pool = compatible_ids or branch_top_ids
        best_confidence = max(normalized_scores[key_id][1] for key_id in selection_pool)
        tied_ids = tuple(
            key_id
            for key_id in selection_pool
            if normalized_scores[key_id][1] == best_confidence
        )
        selected_key_id = str(step["key_id"])
        expected_calls = 2 + top_k + int(len(tied_ids) > 1)
        if (
            selected_key_id not in tied_ids
            or isinstance(step.get("calls"), bool)
            or step.get("calls") != expected_calls
        ):
            raise SpeechNativeProfileError(
                "M7 grounded branch selection is inconsistent"
            )
        branches.append(
            {
                "state_policy_id": state_policy_id,
                "key_id": selected_key_id,
                "top_key_ids": tuple(branch_top_ids),
                "verifier_scores": normalized_scores,
                "state_tokens": _m7_state_tokens(state_document),
            }
        )
    raw_calls = row.get("calls")
    expected_total_calls = sum(int(step["calls"]) for step in steps)
    if (
        isinstance(raw_calls, bool)
        or not isinstance(raw_calls, int)
        or raw_calls != expected_total_calls
        or not 17 <= raw_calls <= 20
    ):
        raise SpeechNativeProfileError("M7 contact accounting is malformed")
    return {
        "sample_id": sample_id,
        "speaker_id": speaker_id,
        "gold_key_id": gold_key_id,
        "primary_key_id": str(votes[0]),
        "initial_top_key_ids": initial_top_ids,
        "branches": tuple(branches),
        "total_calls": raw_calls,
    }


def _evaluate_m7_multistate_action_support(
    trajectories: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Read M7 action support and apply the preregistered label-blind controller."""

    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError("M7 action-support read requires trajectories")
    fold_trajectories = tuple(
        {
            "speaker_id": str(item["speaker_id"]),
            "gold_key_id": str(item["gold_key_id"]),
            "primary_key_id": str(item["primary_key_id"]),
            "canonical_key_id": None,
            "reverse_key_id": None,
            "rotate_key_id": None,
        }
        for item in frozen
    )
    validated_folds = _validate_training_free_trajectories(fold_trajectories)
    assignments = _speaker_grouped_fold_assignments(validated_folds)
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )
    branch_metrics: list[dict[str, object]] = []
    for branch_index, state_policy_id in enumerate(_M7_STATE_POLICY_IDS):
        selected_correct = helpful = harmful = unique_helpful = 0
        changed = top_k_reachable = 0
        for item in frozen:
            branches = item["branches"]
            assert isinstance(branches, tuple)
            branch = branches[branch_index]
            assert isinstance(branch, Mapping)
            selected = branch["key_id"]
            primary = item["primary_key_id"]
            gold = item["gold_key_id"]
            selected_correct += int(selected == gold)
            changed += int(selected != primary)
            helpful += int(primary != gold and selected == gold)
            harmful += int(primary == gold and selected != gold)
            top_k_reachable += int(gold in branch["top_key_ids"])
            unique_helpful += int(
                primary != gold
                and selected == gold
                and all(
                    other_index == branch_index
                    or branches[other_index]["key_id"] != gold
                    for other_index in range(len(_M7_STATE_POLICY_IDS))
                )
            )
        branch_metrics.append(
            {
                "state_policy_id": state_policy_id,
                "selected_correct": selected_correct,
                "selected_accuracy": selected_correct / len(frozen),
                "non_primary_action_count": changed,
                "helpful_action_count": helpful,
                "harmful_action_count": harmful,
                "unique_helpful_action_count": unique_helpful,
                "top_k_reachable_count": top_k_reachable,
            }
        )

    action_variable_count = 0
    oracle_correct = 0
    controller_predictions: list[str | None] = []
    controller_reasons: Counter[str] = Counter()
    for item in frozen:
        primary = str(item["primary_key_id"])
        gold = str(item["gold_key_id"])
        branches = item["branches"]
        assert isinstance(branches, tuple)
        branch_keys = [str(branch["key_id"]) for branch in branches]
        action_variable_count += int(any(key_id != primary for key_id in branch_keys))
        oracle_correct += int(primary == gold or gold in branch_keys)
        counts = Counter(key_id for key_id in branch_keys if key_id != primary)
        supported = [key_id for key_id, count in counts.items() if count >= 2]
        selected = primary
        reason = "retain:no-two-branch-non-primary-agreement"
        if len(supported) == 1:
            candidate = supported[0]
            agreeing = [branch for branch in branches if branch["key_id"] == candidate]
            confidence_pass = True
            for branch in agreeing:
                scores = branch["verifier_scores"]
                assert isinstance(scores, Mapping)
                compatible, selected_confidence = scores[candidate]
                alternative_confidence = max(
                    (
                        score[1]
                        for key_id, score in scores.items()
                        if key_id != candidate
                    ),
                    default=0.0,
                )
                confidence_pass = (
                    confidence_pass
                    and compatible
                    and (selected_confidence - alternative_confidence >= 20.0)
                )
            semantic_pass = all(
                _grounded_semantic_jaccard(
                    agreeing[left]["state_tokens"],
                    agreeing[right]["state_tokens"],
                )
                >= 0.5
                for left in range(len(agreeing))
                for right in range(left + 1, len(agreeing))
            )
            if confidence_pass and semantic_pass:
                selected = candidate
                reason = "select:two-branch-grounded-consensus"
            elif not confidence_pass:
                reason = "retain:verifier-margin"
            else:
                reason = "retain:state-semantic-disagreement"
        controller_predictions.append(selected)
        controller_reasons[reason] += 1

    controller_correct = sum(
        prediction == item["gold_key_id"]
        for prediction, item in zip(controller_predictions, frozen, strict=True)
    )
    wrong_to_correct = sum(
        item["primary_key_id"] != item["gold_key_id"]
        and prediction == item["gold_key_id"]
        for prediction, item in zip(controller_predictions, frozen, strict=True)
    )
    correct_to_wrong = sum(
        item["primary_key_id"] == item["gold_key_id"]
        and prediction != item["gold_key_id"]
        for prediction, item in zip(controller_predictions, frozen, strict=True)
    )
    action_count = sum(
        prediction != item["primary_key_id"]
        for prediction, item in zip(controller_predictions, frozen, strict=True)
    )
    folds = _speaker_fold_metrics(
        validated_folds,
        assignments=assignments,
        predictions=controller_predictions,
    )
    positive_folds = sum(int(fold["correct_delta_vs_primary"] > 0) for fold in folds)
    worst_fold = min(int(fold["correct_delta_vs_primary"]) for fold in folds)
    action_rate = action_count / len(frozen)
    promotion_checks = {
        "net_gain_at_least_3": controller_correct - primary_correct >= 3,
        "positive_fold_count_at_least_2": positive_folds >= 2,
        "worst_fold_delta_nonnegative": worst_fold >= 0,
        "correct_to_wrong_zero": correct_to_wrong == 0,
        "action_rate_between_0_05_and_0_50": 0.05 <= action_rate <= 0.50,
    }
    support_checks = {
        "action_variable_query_count_at_least_24": action_variable_count >= 24,
        "oracle_gain_vs_primary_at_least_8": oracle_correct - primary_correct >= 8,
        "two_branch_policies_have_two_unique_helpful_actions": sum(
            branch["unique_helpful_action_count"] >= 2 for branch in branch_metrics
        )
        >= 2,
    }
    return {
        "policy_id": _M7_POLICY_ID,
        "aggregator_id": _M7_AGGREGATOR_ID,
        "primary_correct": primary_correct,
        "primary_accuracy": primary_correct / len(frozen),
        "final_minus_primary_correct": 0,
        "action_variable_query_count": action_variable_count,
        "oracle_correct": oracle_correct,
        "oracle_gain_vs_primary": oracle_correct - primary_correct,
        "oracle_status": "diagnostic-only-not-an-admissible-controller",
        "branch_policies": branch_metrics,
        "support_checks": support_checks,
        "support_gate_passed": all(support_checks.values()),
        "consistency_controller": {
            "policy_id": "two-branch-grounded-consensus-v1",
            "label_blind_at_action_time": True,
            "correct": controller_correct,
            "accuracy": controller_correct / len(frozen),
            "correct_delta_vs_primary": controller_correct - primary_correct,
            "wrong_to_correct_vs_primary": wrong_to_correct,
            "correct_to_wrong_vs_primary": correct_to_wrong,
            "action_count": action_count,
            "action_rate": action_rate,
            "action_reasons": dict(sorted(controller_reasons.items())),
            "speaker_fold_policy_id": _SPEAKER_FOLD_POLICY_ID,
            "speaker_folds_vs_primary": folds,
            "positive_delta_fold_count": positive_folds,
            "worst_fold_delta_vs_primary": worst_fold,
            "promotion_checks": promotion_checks,
            "qualified": all(promotion_checks.values()),
        },
    }


def _m8_success_actions(challenger_count: int) -> tuple[str, ...]:
    return (
        "match:speech-only-primary",
        "retrieve:speech-only",
        *tuple(
            f"compare:pairwise-boundary-rank-{rank}"
            for rank in range(1, challenger_count + 1)
        ),
        "select:retain-primary-for-support",
    )


def _parse_m8_pairwise_trajectory(
    *,
    row: Mapping[str, object],
    sample_id: str,
    speaker_id: str,
    gold_key_id: str,
    initial_top_ids: tuple[str, ...],
    top_k: int,
    visible_card_by_key: Mapping[str, KeyCardV1],
) -> dict[str, object]:
    """Validate one complete order-controlled K1/K2 pairwise trajectory."""

    primary_key_id = row.get("key_id")
    challengers = tuple(
        key_id for key_id in initial_top_ids if key_id != primary_key_id
    )
    votes = row.get("agent_vote_key_ids")
    steps = row.get("agent_steps")
    actions = row.get("agent_actions")
    if (
        row.get("agent_policy_id") != _M8_POLICY_ID
        or row.get("agent_aggregator_id") != _M8_AGGREGATOR_ID
        or row.get("agent_escalated") is not True
        or not isinstance(actions, list)
        or tuple(actions) != _m8_success_actions(len(challengers))
    ):
        raise SpeechNativeProfileError("M8 pairwise-support identity is malformed")
    if (
        not isinstance(primary_key_id, str)
        or primary_key_id not in visible_card_by_key
        or not 1 <= len(challengers) <= top_k
        or not isinstance(votes, list)
        or len(votes) != 1 + 2 * len(challengers)
        or votes[0] != primary_key_id
        or not all(
            vote is None or isinstance(vote, str) and vote in visible_card_by_key
            for vote in votes
        )
        or not isinstance(steps, list)
        or len(steps) != 2 + len(challengers)
        or row.get("verifier_scores") != {}
    ):
        raise SpeechNativeProfileError("M8 pairwise-support trajectory is malformed")
    base_fields = {
        "action_id",
        "key_id",
        "top_key_ids",
        "calls",
        "parse_failure",
    }
    if (
        not isinstance(steps[0], Mapping)
        or set(steps[0]) != base_fields
        or steps[0].get("action_id") != "match:speech-only-primary"
        or steps[0].get("key_id") != primary_key_id
        or steps[0].get("top_key_ids") != []
        or steps[0].get("calls") != 1
        or steps[0].get("parse_failure") is not False
        or not isinstance(steps[1], Mapping)
        or set(steps[1]) != base_fields
        or steps[1].get("action_id") != "retrieve:speech-only"
        or steps[1].get("key_id") != initial_top_ids[0]
        or tuple(steps[1].get("top_key_ids", [])) != initial_top_ids
        or steps[1].get("calls") != 1
        or steps[1].get("parse_failure") is not False
    ):
        raise SpeechNativeProfileError("M8 initial action-support stages are malformed")

    comparison_fields = {
        "action_id",
        "rank",
        "primary_key_id",
        "challenger_key_id",
        "k1_ab_key_id",
        "k1_ba_key_id",
        "k1_stable_key_id",
        "k2_ab_key_id",
        "k2_ba_key_id",
        "k2_stable_key_id",
        "calls",
        "parse_failure",
        "causal_parent_ids",
    }
    comparisons: list[dict[str, object]] = []
    for rank, challenger_key_id in enumerate(challengers, start=1):
        step = steps[rank + 1]
        pair = {primary_key_id, challenger_key_id}
        if (
            not isinstance(step, Mapping)
            or set(step) != comparison_fields
            or step.get("action_id") != f"compare:pairwise-boundary-rank-{rank}"
            or step.get("rank") != rank
            or step.get("primary_key_id") != primary_key_id
            or step.get("challenger_key_id") != challenger_key_id
            or step.get("calls") != 4
            or step.get("parse_failure") is not False
            or step.get("causal_parent_ids")
            != ["match:speech-only-primary", "retrieve:speech-only"]
        ):
            raise SpeechNativeProfileError(
                "M8 pairwise comparison identity is malformed"
            )
        raw_pair_votes = tuple(
            step.get(field)
            for field in (
                "k1_ab_key_id",
                "k1_ba_key_id",
                "k2_ab_key_id",
                "k2_ba_key_id",
            )
        )
        if not all(vote in pair for vote in raw_pair_votes):
            raise SpeechNativeProfileError("M8 pairwise vote is outside its key pair")
        k1_stable = (
            challenger_key_id
            if raw_pair_votes[0] == raw_pair_votes[1] == challenger_key_id
            else None
        )
        k2_stable = (
            challenger_key_id
            if raw_pair_votes[2] == raw_pair_votes[3] == challenger_key_id
            else None
        )
        if (
            step.get("k1_stable_key_id") != k1_stable
            or step.get("k2_stable_key_id") != k2_stable
            or votes[1 + 2 * (rank - 1)] != k1_stable
            or votes[2 + 2 * (rank - 1)] != k2_stable
        ):
            raise SpeechNativeProfileError(
                "M8 stable challenger support is inconsistent"
            )
        comparisons.append(
            {
                "rank": rank,
                "challenger_key_id": challenger_key_id,
                "k1_ab_key_id": raw_pair_votes[0],
                "k1_ba_key_id": raw_pair_votes[1],
                "k1_stable_key_id": k1_stable,
                "k2_ab_key_id": raw_pair_votes[2],
                "k2_ba_key_id": raw_pair_votes[3],
                "k2_stable_key_id": k2_stable,
            }
        )
    expected_calls = 2 + 4 * len(challengers)
    if row.get("calls") != expected_calls or expected_calls not in {10, 14}:
        raise SpeechNativeProfileError("M8 contact accounting is malformed")
    return {
        "sample_id": sample_id,
        "speaker_id": speaker_id,
        "gold_key_id": gold_key_id,
        "primary_key_id": primary_key_id,
        "initial_top_key_ids": initial_top_ids,
        "comparisons": tuple(comparisons),
        "total_calls": expected_calls,
    }


def _evaluate_m8_pairwise_action_support(
    trajectories: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Read M8 support and apply the preregistered label-blind controller."""

    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError("M8 pairwise-support read requires trajectories")
    fold_trajectories = tuple(
        {
            "speaker_id": str(item["speaker_id"]),
            "gold_key_id": str(item["gold_key_id"]),
            "primary_key_id": str(item["primary_key_id"]),
            "canonical_key_id": None,
            "reverse_key_id": None,
            "rotate_key_id": None,
        }
        for item in frozen
    )
    validated_folds = _validate_training_free_trajectories(fold_trajectories)
    assignments = _speaker_grouped_fold_assignments(validated_folds)
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )

    representation_metrics: dict[str, dict[str, object]] = {}
    representation_predictions: dict[str, list[str]] = {}
    for representation_id in ("K1", "K2"):
        field = f"{representation_id.casefold()}_stable_key_id"
        predictions: list[str] = []
        action_query_count = 0
        helpful = harmful = 0
        for item in frozen:
            primary = str(item["primary_key_id"])
            gold = str(item["gold_key_id"])
            comparisons = item["comparisons"]
            assert isinstance(comparisons, tuple)
            selected = next(
                (
                    str(comparison[field])
                    for comparison in comparisons
                    if comparison[field] is not None
                ),
                primary,
            )
            predictions.append(selected)
            action_query_count += int(selected != primary)
            helpful += int(primary != gold and selected == gold)
            harmful += int(primary == gold and selected != gold)
        representation_predictions[representation_id] = predictions
        correct = sum(
            prediction == item["gold_key_id"]
            for prediction, item in zip(predictions, frozen, strict=True)
        )
        representation_metrics[representation_id] = {
            "selector_policy_id": "first-ranked-stable-challenger-v1",
            "correct": correct,
            "accuracy": correct / len(frozen),
            "stable_non_primary_query_count": action_query_count,
            "helpful_action_count": helpful,
            "harmful_action_count": harmful,
        }

    oracle_correct = 0
    controller_predictions: list[str] = []
    controller_reasons: Counter[str] = Counter()
    for item in frozen:
        primary = str(item["primary_key_id"])
        gold = str(item["gold_key_id"])
        comparisons = item["comparisons"]
        assert isinstance(comparisons, tuple)
        supported = {
            str(comparison[field])
            for comparison in comparisons
            for field in ("k1_stable_key_id", "k2_stable_key_id")
            if comparison[field] is not None
        }
        oracle_correct += int(primary == gold or gold in supported)
        rank_one = comparisons[0]
        challenger = str(rank_one["challenger_key_id"])
        all_four = all(
            rank_one[field] == challenger
            for field in (
                "k1_ab_key_id",
                "k1_ba_key_id",
                "k2_ab_key_id",
                "k2_ba_key_id",
            )
        )
        selected = challenger if all_four else primary
        controller_predictions.append(selected)
        controller_reasons[
            "select:rank-one-four-way-consensus"
            if all_four
            else "retain:no-rank-one-four-way-consensus"
        ] += 1

    controller_correct = sum(
        prediction == item["gold_key_id"]
        for prediction, item in zip(controller_predictions, frozen, strict=True)
    )
    wrong_to_correct = sum(
        item["primary_key_id"] != item["gold_key_id"]
        and prediction == item["gold_key_id"]
        for prediction, item in zip(controller_predictions, frozen, strict=True)
    )
    correct_to_wrong = sum(
        item["primary_key_id"] == item["gold_key_id"]
        and prediction != item["gold_key_id"]
        for prediction, item in zip(controller_predictions, frozen, strict=True)
    )
    action_count = sum(
        prediction != item["primary_key_id"]
        for prediction, item in zip(controller_predictions, frozen, strict=True)
    )
    folds = _speaker_fold_metrics(
        validated_folds,
        assignments=assignments,
        predictions=controller_predictions,
    )
    positive_folds = sum(int(fold["correct_delta_vs_primary"] > 0) for fold in folds)
    worst_fold = min(int(fold["correct_delta_vs_primary"]) for fold in folds)
    action_rate = action_count / len(frozen)
    k1 = representation_metrics["K1"]
    k2 = representation_metrics["K2"]
    support_checks = {
        "k2_stable_non_primary_query_count_at_least_24": (
            int(k2["stable_non_primary_query_count"]) >= 24
        ),
        "oracle_gain_vs_primary_at_least_7": oracle_correct - primary_correct >= 7,
        "k2_helpful_at_least_k1_plus_2": (
            int(k2["helpful_action_count"]) >= int(k1["helpful_action_count"]) + 2
        ),
        "k2_harmful_no_more_than_k1": (
            int(k2["harmful_action_count"]) <= int(k1["harmful_action_count"])
        ),
    }
    promotion_checks = {
        "net_gain_at_least_3": controller_correct - primary_correct >= 3,
        "positive_fold_count_at_least_2": positive_folds >= 2,
        "worst_fold_delta_nonnegative": worst_fold >= 0,
        "correct_to_wrong_zero": correct_to_wrong == 0,
        "action_rate_between_0_05_and_0_50": 0.05 <= action_rate <= 0.50,
    }
    return {
        "policy_id": _M8_POLICY_ID,
        "aggregator_id": _M8_AGGREGATOR_ID,
        "primary_correct": primary_correct,
        "primary_accuracy": primary_correct / len(frozen),
        "final_minus_primary_correct": 0,
        "representations": representation_metrics,
        "oracle_correct": oracle_correct,
        "oracle_gain_vs_primary": oracle_correct - primary_correct,
        "oracle_status": "diagnostic-only-not-an-admissible-controller",
        "support_checks": support_checks,
        "support_gate_passed": all(support_checks.values()),
        "consistency_controller": {
            "policy_id": "rank-one-k1-k2-ab-ba-consensus-v1",
            "label_blind_at_action_time": True,
            "correct": controller_correct,
            "accuracy": controller_correct / len(frozen),
            "correct_delta_vs_primary": controller_correct - primary_correct,
            "wrong_to_correct_vs_primary": wrong_to_correct,
            "correct_to_wrong_vs_primary": correct_to_wrong,
            "action_count": action_count,
            "action_rate": action_rate,
            "action_reasons": dict(sorted(controller_reasons.items())),
            "speaker_fold_policy_id": _SPEAKER_FOLD_POLICY_ID,
            "speaker_folds_vs_primary": folds,
            "positive_delta_fold_count": positive_folds,
            "worst_fold_delta_vs_primary": worst_fold,
            "promotion_checks": promotion_checks,
            "qualified": all(promotion_checks.values()),
        },
    }


def _parse_m9_factor_graph_trajectory(
    *,
    row: Mapping[str, object],
    sample_id: str,
    speaker_id: str,
    gold_key_id: str,
    top_k: int,
    visible_card_by_key: Mapping[str, KeyCardV1],
    decision_graph: DecisionGraphV1,
) -> dict[str, object]:
    """Reconstruct one graph traversal without trusting derived row fields."""

    primary_key_id = row.get("key_id")
    actions = row.get("agent_actions")
    votes = row.get("agent_vote_key_ids")
    steps = row.get("agent_steps")
    if (
        row.get("agent_policy_id") != _M9_POLICY_ID
        or row.get("agent_aggregator_id") != _M9_AGGREGATOR_ID
        or row.get("agent_escalated") is not True
        or not isinstance(primary_key_id, str)
        or primary_key_id not in visible_card_by_key
        or not isinstance(actions, list)
        or not isinstance(votes, list)
        or not isinstance(steps, list)
        or row.get("verifier_scores") != {}
    ):
        raise SpeechNativeProfileError(
            "M9 factor-graph trajectory identity is malformed"
        )
    decision_graph.validate(tuple(visible_card_by_key.values()))
    base_fields = {
        "action_id",
        "key_id",
        "top_key_ids",
        "calls",
        "parse_failure",
    }
    if (
        len(steps) < 3
        or not isinstance(steps[0], Mapping)
        or set(steps[0]) != base_fields
        or steps[0].get("action_id") != "match:speech-only-primary"
        or steps[0].get("key_id") != primary_key_id
        or steps[0].get("top_key_ids") != []
        or steps[0].get("calls") != 1
        or steps[0].get("parse_failure") is not False
        or not isinstance(steps[1], Mapping)
        or set(steps[1]) != base_fields
        or steps[1].get("action_id") != "retrieve:speech-only"
        or steps[1].get("calls") != 1
        or steps[1].get("parse_failure") is not False
    ):
        raise SpeechNativeProfileError("M9 initial graph stages are malformed")
    initial_top_raw = steps[1].get("top_key_ids")
    if (
        not isinstance(initial_top_raw, list)
        or len(initial_top_raw) != top_k
        or len(set(initial_top_raw)) != top_k
        or not all(
            isinstance(key_id, str) and key_id in visible_card_by_key
            for key_id in initial_top_raw
        )
        or steps[1].get("key_id") != initial_top_raw[0]
    ):
        raise SpeechNativeProfileError("M9 initial retrieval is malformed")
    initial_top_ids = tuple(initial_top_raw)

    factor_step = steps[2]
    factor_fields = base_fields | {"factor_link_state"}
    invalid_factor_actions = (
        "match:speech-only-primary",
        "retrieve:speech-only",
        "link:knowledge-factors",
        "backtrack:invalid-factor-link-state",
    )
    if (
        isinstance(factor_step, Mapping)
        and set(factor_step) == base_fields
        and factor_step.get("action_id") == "link:knowledge-factors"
        and factor_step.get("key_id") is None
        and tuple(factor_step.get("top_key_ids", [])) == initial_top_ids
        and factor_step.get("calls") == 1
        and factor_step.get("parse_failure") is True
    ):
        if (
            tuple(actions) != invalid_factor_actions
            or len(steps) != 3
            or votes != [primary_key_id]
            or row.get("top_key_ids") != list(initial_top_ids)
            or row.get("calls") != 3
        ):
            raise SpeechNativeProfileError(
                "M9 invalid factor-link termination is malformed"
            )
        return {
            "sample_id": sample_id,
            "speaker_id": speaker_id,
            "gold_key_id": gold_key_id,
            "primary_key_id": primary_key_id,
            "initial_top_key_ids": initial_top_ids,
            "factor_ids": (),
            "selected_boundary_id": None,
            "expanded_key_ids": initial_top_ids,
            "reranked_key_ids": (primary_key_id,),
            "boundary_path_ids": (),
            "boundary_ab_key_id": None,
            "boundary_ba_key_id": None,
            "boundary_stable_key_id": None,
            "termination": "invalid-factor-link-state",
            "mechanism_failure": True,
            "total_calls": 3,
        }
    if (
        not isinstance(factor_step, Mapping)
        or set(factor_step) != factor_fields
        or factor_step.get("action_id") != "link:knowledge-factors"
        or factor_step.get("key_id") is not None
        or tuple(factor_step.get("top_key_ids", [])) != initial_top_ids
        or factor_step.get("calls") != 1
        or factor_step.get("parse_failure") is not False
    ):
        raise SpeechNativeProfileError("M9 factor-link stage is malformed")
    raw_factor_state = factor_step.get("factor_link_state")
    if not isinstance(raw_factor_state, Mapping) or set(raw_factor_state) != {
        "factor_ids",
        "boundary_id",
    }:
        raise SpeechNativeProfileError("M9 factor-link state is malformed")
    raw_factor_ids = raw_factor_state.get("factor_ids")
    boundary_id = raw_factor_state.get("boundary_id")
    neighborhood = decision_graph.neighborhood(initial_top_ids)
    if (
        not isinstance(raw_factor_ids, list)
        or not 2 <= len(raw_factor_ids) <= 5
        or len(set(raw_factor_ids)) != len(raw_factor_ids)
        or not all(
            isinstance(factor_id, str) and factor_id in set(neighborhood.factor_ids)
            for factor_id in raw_factor_ids
        )
        or (
            boundary_id is not None
            and (
                not isinstance(boundary_id, str)
                or boundary_id not in set(neighborhood.boundary_ids)
            )
        )
    ):
        raise SpeechNativeProfileError(
            "M9 factor-link state is outside its neighborhood"
        )
    factor_state = FactorLinkStateV1(
        factor_ids=tuple(raw_factor_ids), boundary_id=boundary_id
    )
    expected_expansion = expand_decision_graph_candidates(
        graph=decision_graph,
        initial_key_ids=initial_top_ids,
        state=factor_state,
        cap=min(6, len(visible_card_by_key)),
    )
    expansion_step = steps[3]
    expansion_fields = base_fields | {"expanded_key_ids", "distance_by_key"}
    if (
        not isinstance(expansion_step, Mapping)
        or set(expansion_step) != expansion_fields
        or expansion_step.get("action_id") != "tool:expand-factor-graph"
        or expansion_step.get("key_id") is not None
        or tuple(expansion_step.get("top_key_ids", [])) != initial_top_ids
        or expansion_step.get("calls") != 0
        or expansion_step.get("parse_failure") is not False
        or tuple(expansion_step.get("expanded_key_ids", []))
        != expected_expansion.key_ids
        or expansion_step.get("distance_by_key")
        != dict(expected_expansion.distance_by_key)
    ):
        raise SpeechNativeProfileError("M9 deterministic graph expansion is malformed")

    rerank_step = steps[4]
    reranked_raw = row.get("top_key_ids")
    expected_rerank_count = min(3, len(expected_expansion.key_ids))
    common_actions = tuple(actions[: len(_M9_COMMON_ACTIONS)])
    if common_actions != _M9_COMMON_ACTIONS:
        raise SpeechNativeProfileError("M9 graph action prefix is malformed")
    invalid_rerank = (
        isinstance(rerank_step, Mapping)
        and set(rerank_step) == base_fields
        and rerank_step.get("action_id") == "rerank:speech-plus-factor-state"
        and rerank_step.get("calls") == 1
        and isinstance(rerank_step.get("parse_failure"), bool)
        and isinstance(reranked_raw, list)
        and len(reranked_raw) < expected_rerank_count
        and len(set(reranked_raw)) == len(reranked_raw)
        and all(key_id in expected_expansion.key_ids for key_id in reranked_raw)
        and tuple(rerank_step.get("top_key_ids", [])) == tuple(reranked_raw)
        and rerank_step.get("key_id") == (reranked_raw[0] if reranked_raw else None)
    )
    if invalid_rerank:
        expected_actions = (*_M9_COMMON_ACTIONS, "backtrack:invalid-factor-rerank")
        if (
            tuple(actions) != expected_actions
            or len(steps) != 5
            or votes != [primary_key_id]
            or row.get("calls") != 4
        ):
            raise SpeechNativeProfileError(
                "M9 invalid factor-rerank termination is malformed"
            )
        return {
            "sample_id": sample_id,
            "speaker_id": speaker_id,
            "gold_key_id": gold_key_id,
            "primary_key_id": primary_key_id,
            "initial_top_key_ids": initial_top_ids,
            "factor_ids": factor_state.factor_ids,
            "selected_boundary_id": factor_state.boundary_id,
            "expanded_key_ids": expected_expansion.key_ids,
            "reranked_key_ids": (primary_key_id,),
            "boundary_path_ids": (),
            "boundary_ab_key_id": None,
            "boundary_ba_key_id": None,
            "boundary_stable_key_id": None,
            "termination": "invalid-factor-rerank",
            "mechanism_failure": True,
            "total_calls": 4,
        }
    if (
        not isinstance(rerank_step, Mapping)
        or set(rerank_step) != base_fields
        or rerank_step.get("action_id") != "rerank:speech-plus-factor-state"
        or rerank_step.get("calls") != 1
        or rerank_step.get("parse_failure") is not False
        or not isinstance(reranked_raw, list)
        or len(reranked_raw) != expected_rerank_count
        or len(set(reranked_raw)) != expected_rerank_count
        or not all(key_id in expected_expansion.key_ids for key_id in reranked_raw)
        or tuple(rerank_step.get("top_key_ids", [])) != tuple(reranked_raw)
        or rerank_step.get("key_id") != reranked_raw[0]
    ):
        raise SpeechNativeProfileError("M9 factor rerank stage is malformed")
    reranked_ids = tuple(reranked_raw)
    rerank_key_id = reranked_ids[0]

    boundary_ab: str | None = None
    boundary_ba: str | None = None
    boundary_path: tuple[str, ...] = ()
    termination = ""
    mechanism_failure = False
    if rerank_key_id == primary_key_id:
        expected_actions = (
            *_M9_COMMON_ACTIONS,
            "stop:primary-rerank-agree",
            "select:retain-primary-for-support",
        )
        if (
            tuple(actions) != expected_actions
            or len(steps) != 5
            or votes
            != [
                primary_key_id,
                rerank_key_id,
            ]
        ):
            raise SpeechNativeProfileError("M9 agreement termination is malformed")
        termination = "primary-rerank-agree"
    else:
        expected_path = decision_boundary_path(
            graph=decision_graph,
            source_key_id=primary_key_id,
            target_key_id=rerank_key_id,
            max_edges=2,
        )
        if expected_path:
            expected_actions = (
                *_M9_COMMON_ACTIONS,
                "compare:boundary-ab",
                "compare:boundary-ba",
                "select:retain-primary-for-support",
            )
            comparison_fields = base_fields | {
                "boundary_path_ids",
                "ab_key_id",
                "ba_key_id",
                "causal_parent_ids",
            }
            if (
                tuple(actions) != expected_actions
                or len(steps) != 6
                or row.get("calls") != 6
                or len(votes) != 4
                or votes[0] != primary_key_id
                or votes[1] != rerank_key_id
                or not isinstance(steps[5], Mapping)
                or set(steps[5]) != comparison_fields
                or steps[5].get("action_id") != "compare:factor-boundary"
                or steps[5].get("key_id") is not None
                or steps[5].get("top_key_ids") != [primary_key_id, rerank_key_id]
                or steps[5].get("calls") != 2
                or steps[5].get("parse_failure") is not False
                or tuple(steps[5].get("boundary_path_ids", [])) != expected_path
                or steps[5].get("causal_parent_ids")
                != [
                    "link:knowledge-factors",
                    "tool:expand-factor-graph",
                    "rerank:speech-plus-factor-state",
                ]
            ):
                raise SpeechNativeProfileError("M9 boundary comparison is malformed")
            pair = {primary_key_id, rerank_key_id}
            boundary_ab = steps[5].get("ab_key_id")  # type: ignore[assignment]
            boundary_ba = steps[5].get("ba_key_id")  # type: ignore[assignment]
            if (
                boundary_ab not in pair
                or boundary_ba not in pair
                or votes[2:] != [boundary_ab, boundary_ba]
            ):
                raise SpeechNativeProfileError("M9 boundary votes are unbound")
            boundary_path = expected_path
            termination = "boundary-compared"
        else:
            expected_actions = (
                *_M9_COMMON_ACTIONS,
                "backtrack:no-boundary-path",
                "select:retain-primary-for-support",
            )
            if (
                tuple(actions) != expected_actions
                or len(steps) != 5
                or votes != [primary_key_id, rerank_key_id]
            ):
                raise SpeechNativeProfileError("M9 no-path backtrack is malformed")
            termination = "no-boundary-path"
            mechanism_failure = True
    expected_calls = 6 if termination == "boundary-compared" else 4
    if row.get("calls") != expected_calls:
        raise SpeechNativeProfileError("M9 contact accounting is malformed")
    boundary_stable = boundary_ab if boundary_ab == boundary_ba else None
    return {
        "sample_id": sample_id,
        "speaker_id": speaker_id,
        "gold_key_id": gold_key_id,
        "primary_key_id": primary_key_id,
        "initial_top_key_ids": initial_top_ids,
        "factor_ids": factor_state.factor_ids,
        "selected_boundary_id": factor_state.boundary_id,
        "expanded_key_ids": expected_expansion.key_ids,
        "reranked_key_ids": reranked_ids,
        "boundary_path_ids": boundary_path,
        "boundary_ab_key_id": boundary_ab,
        "boundary_ba_key_id": boundary_ba,
        "boundary_stable_key_id": boundary_stable,
        "termination": termination,
        "mechanism_failure": mechanism_failure,
        "total_calls": expected_calls,
    }


def _evaluate_m9_factor_graph_action_support(
    trajectories: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Measure action support; do not optimize a controller before the gate."""

    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError("M9 factor-graph read requires trajectories")
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )
    initial_reachable = sum(
        item["gold_key_id"] in item["initial_top_key_ids"] for item in frozen
    )
    expanded_reachable = sum(
        item["gold_key_id"] in item["expanded_key_ids"] for item in frozen
    )
    rerank_reachable = sum(
        item["gold_key_id"] in item["reranked_key_ids"] for item in frozen
    )
    family_predictions: dict[str, list[str]] = {
        "factor-rerank": [str(item["reranked_key_ids"][0]) for item in frozen],
        "boundary-stable": [
            str(item["boundary_stable_key_id"])
            if item["boundary_stable_key_id"] is not None
            else str(item["primary_key_id"])
            for item in frozen
        ],
    }
    family_metrics: dict[str, dict[str, object]] = {}
    for family_id, predictions in family_predictions.items():
        helpful_sample_ids = [
            str(item["sample_id"])
            for prediction, item in zip(predictions, frozen, strict=True)
            if item["primary_key_id"] != item["gold_key_id"]
            and prediction == item["gold_key_id"]
        ]
        harmful_sample_ids = [
            str(item["sample_id"])
            for prediction, item in zip(predictions, frozen, strict=True)
            if item["primary_key_id"] == item["gold_key_id"]
            and prediction != item["gold_key_id"]
        ]
        family_metrics[family_id] = {
            "correct": sum(
                prediction == item["gold_key_id"]
                for prediction, item in zip(predictions, frozen, strict=True)
            ),
            "action_query_count": sum(
                prediction != item["primary_key_id"]
                for prediction, item in zip(predictions, frozen, strict=True)
            ),
            "helpful_action_count": len(helpful_sample_ids),
            "harmful_action_count": len(harmful_sample_ids),
            "helpful_sample_ids": helpful_sample_ids,
            "harmful_sample_ids": harmful_sample_ids,
        }
    action_variable_count = sum(
        any(
            predictions[index] != item["primary_key_id"]
            for predictions in family_predictions.values()
        )
        for index, item in enumerate(frozen)
    )
    oracle_correct = sum(
        item["gold_key_id"]
        in {
            item["primary_key_id"],
            family_predictions["factor-rerank"][index],
            family_predictions["boundary-stable"][index],
        }
        for index, item in enumerate(frozen)
    )
    mechanism_failure_count = sum(bool(item["mechanism_failure"]) for item in frozen)
    support_checks = {
        "query_count_at_least_100": len(frozen) >= 100,
        "action_variable_query_count_at_least_27": action_variable_count >= 27,
        "oracle_gain_vs_primary_at_least_8": oracle_correct - primary_correct >= 8,
        "two_non_primary_families_have_three_helpful_actions": sum(
            int(metrics["helpful_action_count"]) >= 3
            for metrics in family_metrics.values()
        )
        >= 2,
        "expanded_reachability_not_below_initial_top_k": (
            expanded_reachable >= initial_reachable
        ),
        "mechanism_failure_count_zero": mechanism_failure_count == 0,
    }
    return {
        "policy_id": _M9_POLICY_ID,
        "aggregator_id": _M9_AGGREGATOR_ID,
        "query_count": len(frozen),
        "primary_correct": primary_correct,
        "primary_accuracy": primary_correct / len(frozen),
        "final_minus_primary_correct": 0,
        "initial_top_k_reachable_count": initial_reachable,
        "expanded_reachable_count": expanded_reachable,
        "rerank_reachable_count": rerank_reachable,
        "action_variable_query_count": action_variable_count,
        "oracle_correct": oracle_correct,
        "oracle_gain_vs_primary": oracle_correct - primary_correct,
        "oracle_status": "diagnostic-only-not-an-admissible-controller",
        "mechanism_failure_count": mechanism_failure_count,
        "action_families": family_metrics,
        "support_checks": support_checks,
        "support_gate_passed": all(support_checks.values()),
        "training_free_controller": {
            "status": "deferred-until-support-gate-passes",
            "candidate_policy_family": "out-of-fold-nonparametric-trajectory-control",
        },
    }


def _parse_m10_candidate_evidence_trajectory(
    *,
    row: Mapping[str, object],
    sample_id: str,
    speaker_id: str,
    gold_key_id: str,
    top_k: int,
    visible_card_by_key: Mapping[str, KeyCardV1],
    decision_graph: DecisionGraphV1,
) -> dict[str, object]:
    """Reconstruct one candidate-evidence loop from exact graph-bound fields."""

    primary_key_id = row.get("key_id")
    actions = row.get("agent_actions")
    votes = row.get("agent_vote_key_ids")
    steps = row.get("agent_steps")
    if (
        row.get("agent_policy_id") != _M10_POLICY_ID
        or row.get("agent_aggregator_id") != _M10_AGGREGATOR_ID
        or row.get("agent_escalated") is not True
        or not isinstance(primary_key_id, str)
        or primary_key_id not in visible_card_by_key
        or not isinstance(actions, list)
        or not isinstance(votes, list)
        or not isinstance(steps, list)
        or row.get("verifier_scores") != {}
        or len(steps) < 3
    ):
        raise SpeechNativeProfileError(
            "M10 candidate-evidence trajectory identity is malformed"
        )
    decision_graph.validate(tuple(visible_card_by_key.values()))
    base_fields = {
        "action_id",
        "key_id",
        "top_key_ids",
        "calls",
        "parse_failure",
    }
    if (
        not isinstance(steps[0], Mapping)
        or set(steps[0]) != base_fields
        or steps[0].get("action_id") != "match:speech-only-primary"
        or steps[0].get("key_id") != primary_key_id
        or steps[0].get("top_key_ids") != []
        or steps[0].get("calls") != 1
        or steps[0].get("parse_failure") is not False
        or not isinstance(steps[1], Mapping)
        or set(steps[1]) != base_fields
        or steps[1].get("action_id") != "retrieve:speech-only"
        or steps[1].get("calls") != 1
        or steps[1].get("parse_failure") is not False
    ):
        raise SpeechNativeProfileError("M10 initial stages are malformed")
    initial_top_raw = steps[1].get("top_key_ids")
    if (
        not isinstance(initial_top_raw, list)
        or len(initial_top_raw) != top_k
        or len(set(initial_top_raw)) != top_k
        or not all(
            isinstance(key_id, str) and key_id in visible_card_by_key
            for key_id in initial_top_raw
        )
        or steps[1].get("key_id") != initial_top_raw[0]
    ):
        raise SpeechNativeProfileError("M10 initial retrieval is malformed")
    initial_top_ids = tuple(initial_top_raw)
    expected_expansion = expand_decision_graph_neighborhood(
        graph=decision_graph,
        initial_key_ids=initial_top_ids,
        cap=min(6, len(visible_card_by_key)),
    )
    expansion_step = steps[2]
    expansion_fields = base_fields | {"expanded_key_ids", "distance_by_key"}
    if (
        not isinstance(expansion_step, Mapping)
        or set(expansion_step) != expansion_fields
        or expansion_step.get("action_id") != "tool:expand-candidate-neighborhood"
        or expansion_step.get("key_id") is not None
        or tuple(expansion_step.get("top_key_ids", [])) != initial_top_ids
        or expansion_step.get("calls") != 0
        or expansion_step.get("parse_failure") is not False
        or tuple(expansion_step.get("expanded_key_ids", []))
        != expected_expansion.key_ids
        or expansion_step.get("distance_by_key")
        != dict(expected_expansion.distance_by_key)
        or row.get("top_key_ids") != list(expected_expansion.key_ids)
    ):
        raise SpeechNativeProfileError(
            "M10 deterministic candidate expansion is malformed"
        )

    factor_ids_by_key = {
        key_id: {
            factor.factor_id
            for factor in decision_graph.factors
            if key_id in factor.key_ids
        }
        for key_id in expected_expansion.key_ids
    }
    boundary_ids_by_key = {
        key_id: {
            boundary.boundary_id
            for boundary in decision_graph.boundaries
            if key_id in {boundary.left_key_id, boundary.right_key_id}
        }
        for key_id in expected_expansion.key_ids
    }
    evidence_fields = {
        "action_id",
        "candidate_key_id",
        "support_compatible",
        "support_confidence",
        "support_factor_ids",
        "counterevidence_contradicted",
        "counterevidence_confidence",
        "counterevidence_boundary_ids",
        "calls",
        "parse_failure",
        "causal_parent_ids",
    }
    evidence_states: list[dict[str, object]] = []
    mechanism_failure = False
    evidence_start = 3
    evidence_stop = evidence_start + len(expected_expansion.key_ids)
    if len(steps) < evidence_stop:
        raise SpeechNativeProfileError("M10 candidate evidence is incomplete")
    for offset, candidate_key_id in enumerate(expected_expansion.key_ids):
        step = steps[evidence_start + offset]
        if (
            not isinstance(step, Mapping)
            or set(step) != evidence_fields
            or step.get("action_id") != f"acquire:candidate-evidence:{candidate_key_id}"
            or step.get("candidate_key_id") != candidate_key_id
            or step.get("calls") != 2
            or step.get("causal_parent_ids")
            != [
                "retrieve:speech-only",
                "tool:expand-candidate-neighborhood",
            ]
            or not isinstance(step.get("parse_failure"), bool)
        ):
            raise SpeechNativeProfileError("M10 candidate evidence step is malformed")
        parse_failure = bool(step["parse_failure"])
        support_compatible = step.get("support_compatible")
        support_confidence = step.get("support_confidence")
        support_factor_ids = step.get("support_factor_ids")
        contradicted = step.get("counterevidence_contradicted")
        counter_confidence = step.get("counterevidence_confidence")
        boundary_ids = step.get("counterevidence_boundary_ids")
        valid_support = (
            isinstance(support_compatible, bool)
            and isinstance(support_confidence, int)
            and not isinstance(support_confidence, bool)
            and 0 <= support_confidence <= 100
            and isinstance(support_factor_ids, list)
            and 1 <= len(support_factor_ids) <= 3
            and len(set(support_factor_ids)) == len(support_factor_ids)
            and all(
                isinstance(factor_id, str)
                and factor_id in factor_ids_by_key[candidate_key_id]
                for factor_id in support_factor_ids
            )
        )
        valid_counter = (
            isinstance(contradicted, bool)
            and isinstance(counter_confidence, int)
            and not isinstance(counter_confidence, bool)
            and 0 <= counter_confidence <= 100
            and isinstance(boundary_ids, list)
            and len(boundary_ids) <= 2
            and len(set(boundary_ids)) == len(boundary_ids)
            and all(
                isinstance(boundary_id, str)
                and boundary_id in boundary_ids_by_key[candidate_key_id]
                for boundary_id in boundary_ids
            )
        )
        if parse_failure:
            mechanism_failure = True
        elif not valid_support or not valid_counter:
            raise SpeechNativeProfileError(
                "M10 parse-complete candidate evidence is invalid"
            )
        evidence_states.append(
            {
                "candidate_key_id": candidate_key_id,
                "support_compatible": (support_compatible if valid_support else False),
                "support_confidence": support_confidence if valid_support else -1,
                "support_factor_ids": (
                    tuple(support_factor_ids) if valid_support else ()
                ),
                "counterevidence_contradicted": (
                    contradicted if valid_counter else True
                ),
                "counterevidence_confidence": (
                    counter_confidence if valid_counter else -1
                ),
                "counterevidence_boundary_ids": (
                    tuple(boundary_ids) if valid_counter else ()
                ),
                "parse_failure": parse_failure,
            }
        )

    base_actions = (
        "match:speech-only-primary",
        "retrieve:speech-only",
        "tool:expand-candidate-neighborhood",
        *tuple(
            action
            for key_id in expected_expansion.key_ids
            for action in (
                f"acquire:support:{key_id}",
                f"seek:counterevidence:{key_id}",
            )
        ),
    )
    challenger_ids = tuple(
        key_id for key_id in expected_expansion.key_ids if key_id != primary_key_id
    )
    reconciliation_states: list[dict[str, object]] = []
    if mechanism_failure:
        if (
            tuple(actions) != (*base_actions, "backtrack:invalid-candidate-evidence")
            or len(steps) != evidence_stop
            or votes != [primary_key_id]
        ):
            raise SpeechNativeProfileError(
                "M10 invalid evidence backtrack is malformed"
            )
    else:
        reconciliation_fields = {
            "action_id",
            "candidate_key_id",
            "selected_action",
            "key_id",
            "selected_factor_ids",
            "selected_boundary_ids",
            "calls",
            "parse_failure",
            "causal_parent_ids",
        }
        if len(steps) != evidence_stop + len(challenger_ids):
            raise SpeechNativeProfileError("M10 reconciliation count is malformed")
        for offset, candidate_key_id in enumerate(challenger_ids):
            step = steps[evidence_stop + offset]
            evidence = evidence_states[
                expected_expansion.key_ids.index(candidate_key_id)
            ]
            if (
                not isinstance(step, Mapping)
                or set(step) != reconciliation_fields
                or step.get("action_id") != f"reconcile:candidate:{candidate_key_id}"
                or step.get("candidate_key_id") != candidate_key_id
                or step.get("selected_factor_ids")
                != list(evidence["support_factor_ids"])
                or step.get("selected_boundary_ids")
                != list(evidence["counterevidence_boundary_ids"])
                or step.get("calls") != 1
                or step.get("causal_parent_ids")
                != [f"acquire:candidate-evidence:{candidate_key_id}"]
                or not isinstance(step.get("parse_failure"), bool)
            ):
                raise SpeechNativeProfileError(
                    "M10 candidate reconciliation is malformed"
                )
            selected_action = step.get("selected_action")
            parse_failure = bool(step["parse_failure"])
            selected_key_id = step.get("key_id")
            if parse_failure:
                if selected_action is not None or selected_key_id is not None:
                    raise SpeechNativeProfileError(
                        "M10 failed reconciliation exposes an action"
                    )
                mechanism_failure = True
            elif selected_action not in {
                "retain_primary",
                "accept_candidate",
            } or selected_key_id != (
                candidate_key_id
                if selected_action == "accept_candidate"
                else primary_key_id
            ):
                raise SpeechNativeProfileError(
                    "M10 reconciliation selection is invalid"
                )
            reconciliation_states.append(
                {
                    "candidate_key_id": candidate_key_id,
                    "selected_action": selected_action,
                    "selected_key_id": selected_key_id,
                    "parse_failure": parse_failure,
                }
            )
        terminal_action = (
            "backtrack:invalid-candidate-reconciliation"
            if mechanism_failure
            else "select:retain-primary-for-support"
        )
        expected_actions = (
            *base_actions,
            *tuple(f"reconcile:{key_id}" for key_id in challenger_ids),
            terminal_action,
        )
        expected_votes = [
            primary_key_id,
            *(item["selected_key_id"] for item in reconciliation_states),
        ]
        if tuple(actions) != expected_actions or votes != expected_votes:
            raise SpeechNativeProfileError("M10 action or vote sequence is malformed")

    expected_calls = 2 + 2 * len(expected_expansion.key_ids)
    if not any(item["parse_failure"] for item in evidence_states):
        expected_calls += len(challenger_ids)
    if row.get("calls") != expected_calls:
        raise SpeechNativeProfileError("M10 contact accounting is malformed")
    supported = tuple(
        str(item["candidate_key_id"])
        for item in evidence_states
        if item["support_compatible"]
    )
    dual_evidence = tuple(
        str(item["candidate_key_id"])
        for item in evidence_states
        if item["support_compatible"] and not item["counterevidence_contradicted"]
    )
    reconciled = tuple(
        str(item["candidate_key_id"])
        for item in reconciliation_states
        if item["selected_action"] == "accept_candidate"
    )
    return {
        "sample_id": sample_id,
        "speaker_id": speaker_id,
        "gold_key_id": gold_key_id,
        "primary_key_id": primary_key_id,
        "initial_top_key_ids": initial_top_ids,
        "expanded_key_ids": expected_expansion.key_ids,
        "distance_by_key": dict(expected_expansion.distance_by_key),
        "evidence_states": tuple(evidence_states),
        "reconciliation_states": tuple(reconciliation_states),
        "supported_action_key_ids": supported,
        "dual_evidence_action_key_ids": dual_evidence,
        "reconciled_action_key_ids": reconciled,
        "mechanism_failure": mechanism_failure,
        "total_calls": expected_calls,
    }


def _evaluate_m10_candidate_evidence_action_support(
    trajectories: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Measure candidate-level action support before policy optimization."""

    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError(
            "M10 candidate-evidence read requires trajectories"
        )
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )
    initial_reachable = sum(
        item["gold_key_id"] in item["initial_top_key_ids"] for item in frozen
    )
    expanded_reachable = sum(
        item["gold_key_id"] in item["expanded_key_ids"] for item in frozen
    )
    family_fields = {
        "support-only": "supported_action_key_ids",
        "dual-evidence": "dual_evidence_action_key_ids",
        "reconciled": "reconciled_action_key_ids",
    }
    family_predictions: dict[str, list[str]] = {}
    for family_id, field in family_fields.items():
        predictions: list[str] = []
        for item in frozen:
            primary = str(item["primary_key_id"])
            candidates = tuple(
                str(key_id) for key_id in item[field] if key_id != primary
            )
            predictions.append(candidates[0] if candidates else primary)
        family_predictions[family_id] = predictions
    family_metrics: dict[str, dict[str, object]] = {}
    for family_id, predictions in family_predictions.items():
        helpful_sample_ids = [
            str(item["sample_id"])
            for prediction, item in zip(predictions, frozen, strict=True)
            if item["primary_key_id"] != item["gold_key_id"]
            and prediction == item["gold_key_id"]
        ]
        harmful_sample_ids = [
            str(item["sample_id"])
            for prediction, item in zip(predictions, frozen, strict=True)
            if item["primary_key_id"] == item["gold_key_id"]
            and prediction != item["gold_key_id"]
        ]
        family_metrics[family_id] = {
            "correct": sum(
                prediction == item["gold_key_id"]
                for prediction, item in zip(predictions, frozen, strict=True)
            ),
            "action_query_count": sum(
                prediction != item["primary_key_id"]
                for prediction, item in zip(predictions, frozen, strict=True)
            ),
            "helpful_action_count": len(helpful_sample_ids),
            "harmful_action_count": len(harmful_sample_ids),
            "helpful_sample_ids": helpful_sample_ids,
            "harmful_sample_ids": harmful_sample_ids,
        }
    action_sets = []
    for item in frozen:
        primary = str(item["primary_key_id"])
        action_sets.append(
            {
                str(key_id)
                for field in family_fields.values()
                for key_id in item[field]
                if key_id != primary
            }
        )
    action_variable_count = sum(bool(action_set) for action_set in action_sets)
    oracle_correct = sum(
        item["primary_key_id"] == item["gold_key_id"]
        or item["gold_key_id"] in action_set
        for item, action_set in zip(frozen, action_sets, strict=True)
    )
    supported_primary_error_count = sum(
        item["primary_key_id"] != item["gold_key_id"]
        and item["gold_key_id"] in action_set
        for item, action_set in zip(frozen, action_sets, strict=True)
    )
    mechanism_failure_count = sum(bool(item["mechanism_failure"]) for item in frozen)
    support_checks = {
        "query_count_at_least_100": len(frozen) >= 100,
        "expanded_reachability_not_below_initial_top_k": (
            expanded_reachable >= initial_reachable
        ),
        "expanded_reachable_count_at_least_100": expanded_reachable >= 100,
        "action_variable_query_count_at_least_24": action_variable_count >= 24,
        "oracle_gain_vs_primary_at_least_6": oracle_correct - primary_correct >= 6,
        "model_supported_primary_error_count_at_least_6": (
            supported_primary_error_count >= 6
        ),
        "support_only_helpful_actions_at_least_3": (
            int(family_metrics["support-only"]["helpful_action_count"]) >= 3
        ),
        "dual_or_reconciled_helpful_actions_at_least_3": max(
            int(family_metrics["dual-evidence"]["helpful_action_count"]),
            int(family_metrics["reconciled"]["helpful_action_count"]),
        )
        >= 3,
        "mechanism_failure_count_zero": mechanism_failure_count == 0,
    }
    return {
        "policy_id": _M10_POLICY_ID,
        "aggregator_id": _M10_AGGREGATOR_ID,
        "query_count": len(frozen),
        "primary_correct": primary_correct,
        "primary_accuracy": primary_correct / len(frozen),
        "final_minus_primary_correct": 0,
        "initial_top_k_reachable_count": initial_reachable,
        "expanded_reachable_count": expanded_reachable,
        "action_variable_query_count": action_variable_count,
        "model_supported_primary_error_count": supported_primary_error_count,
        "oracle_correct": oracle_correct,
        "oracle_gain_vs_primary": oracle_correct - primary_correct,
        "oracle_status": "diagnostic-only-not-an-admissible-controller",
        "mechanism_failure_count": mechanism_failure_count,
        "action_families": family_metrics,
        "support_checks": support_checks,
        "support_gate_passed": all(support_checks.values()),
        "training_free_controller": {
            "status": "deferred-until-support-gate-passes",
            "candidate_policy_family": "out-of-fold-nonparametric-trajectory-control",
        },
    }


def _parse_m11_adaptive_evidence_gap_trajectory(
    *,
    row: Mapping[str, object],
    sample_id: str,
    speaker_id: str,
    gold_key_id: str,
    top_k: int,
    visible_card_by_key: Mapping[str, KeyCardV1],
    decision_graph: DecisionGraphV1,
) -> dict[str, object]:
    """Reconstruct one M11 trajectory from exact graph-bound state transitions."""

    primary_key_id = row.get("key_id")
    policy_id = row.get("agent_policy_id")
    actions = row.get("agent_actions")
    votes = row.get("agent_vote_key_ids")
    steps = row.get("agent_steps")
    if (
        policy_id not in _M11_POLICY_IDS
        or row.get("agent_aggregator_id") != _M11_AGGREGATOR_ID
        or not isinstance(primary_key_id, str)
        or primary_key_id not in visible_card_by_key
        or not isinstance(actions, list)
        or not isinstance(votes, list)
        or not isinstance(steps, list)
        or row.get("verifier_scores") != {}
        or len(steps) < 2
    ):
        raise SpeechNativeProfileError(
            "M11 adaptive evidence-gap trajectory identity is malformed"
        )
    decision_graph.validate(tuple(visible_card_by_key.values()))
    initial_fields = {
        "action_id",
        "key_id",
        "top_key_ids",
        "calls",
        "parse_failure",
        "new_knowledge_ids",
    }
    if (
        not isinstance(steps[0], Mapping)
        or set(steps[0]) != initial_fields
        or steps[0].get("action_id") != "match:speech-only-primary"
        or steps[0].get("key_id") != primary_key_id
        or steps[0].get("top_key_ids") != []
        or steps[0].get("calls") != 1
        or steps[0].get("parse_failure") is not False
        or steps[0].get("new_knowledge_ids") != []
        or not isinstance(steps[1], Mapping)
        or set(steps[1]) != initial_fields
        or steps[1].get("action_id") != "retrieve:speech-only"
        or steps[1].get("calls") != 1
        or steps[1].get("new_knowledge_ids") != []
    ):
        raise SpeechNativeProfileError("M11 initial stages are malformed")
    initial_top_raw = steps[1].get("top_key_ids")
    if (
        not isinstance(initial_top_raw, list)
        or len(initial_top_raw) != top_k
        or len(set(initial_top_raw)) != top_k
        or not all(
            isinstance(key_id, str) and key_id in visible_card_by_key
            for key_id in initial_top_raw
        )
        or steps[1].get("key_id") != initial_top_raw[0]
        or steps[1].get("parse_failure") is not False
        or row.get("top_key_ids") != initial_top_raw
    ):
        raise SpeechNativeProfileError("M11 initial retrieval is malformed")
    initial_top_ids = tuple(initial_top_raw)
    candidate_factor_supply_ids = tuple(
        factor.factor_id
        for factor in decision_graph.factors
        if any(key_id in initial_top_ids for key_id in factor.key_ids)
    )

    def information_flow(
        *,
        selected_factor_ids: Sequence[str] = (),
        boundary_id: str | None = None,
    ) -> dict[str, object]:
        selected = tuple(selected_factor_ids)
        if not set(selected).issubset(candidate_factor_supply_ids):
            raise SpeechNativeProfileError(
                "M11 selected factor state was not supplied to the candidate action"
            )
        return {
            "schema": _M11_INFORMATION_FLOW_SCHEMA,
            "observation_source": "speech_features",
            "candidate_factor_supply_ids": candidate_factor_supply_ids,
            "model_selected_factor_ids": selected,
            "model_selected_state_is_external_supply": False,
            "incremental_boundary_supply_ids": (
                (boundary_id,) if boundary_id is not None else ()
            ),
        }

    base_actions = (
        "match:speech-only-primary",
        "retrieve:speech-only",
        "link:candidate-action-state",
    )
    action_fields = initial_fields | {"factor_ids", "causal_parent_ids"}
    if not isinstance(steps[2], Mapping) or set(steps[2]) != action_fields:
        raise SpeechNativeProfileError("M11 candidate-action stage is malformed")
    action_step = steps[2]
    raw_factor_ids = action_step.get("factor_ids")
    action_key_id = action_step.get("key_id")
    factors_by_id = {factor.factor_id: factor for factor in decision_graph.factors}
    valid_action_state = (
        action_step.get("action_id") == "link:candidate-action-state"
        and action_step.get("top_key_ids") == list(initial_top_ids)
        and action_step.get("calls") == 1
        and action_step.get("parse_failure") is False
        and action_step.get("causal_parent_ids") == ["retrieve:speech-only"]
        and isinstance(action_key_id, str)
        and action_key_id in initial_top_ids
        and isinstance(raw_factor_ids, list)
        and 1 <= len(raw_factor_ids) <= 3
        and len(set(raw_factor_ids)) == len(raw_factor_ids)
        and all(
            isinstance(factor_id, str)
            and factor_id in factors_by_id
            and action_key_id in factors_by_id[factor_id].key_ids
            for factor_id in raw_factor_ids
        )
        and any(
            factors_by_id[factor_id].kind == "operation" for factor_id in raw_factor_ids
        )
        and action_step.get("new_knowledge_ids") == raw_factor_ids
    )
    if not valid_action_state:
        if (
            tuple(actions)
            != (*base_actions, "backtrack:invalid-candidate-action-state")
            or row.get("agent_escalated") is not True
            or votes != [primary_key_id, initial_top_ids[0]]
            or len(steps) != 3
            or row.get("calls") != 3
        ):
            raise SpeechNativeProfileError(
                "M11 invalid candidate-action termination is malformed"
            )
        return {
            "policy_id": policy_id,
            "sample_id": sample_id,
            "speaker_id": speaker_id,
            "gold_key_id": gold_key_id,
            "primary_key_id": primary_key_id,
            "initial_top_key_ids": initial_top_ids,
            "retrieval_key_id": initial_top_ids[0],
            "action_key_id": None,
            "new_factor_ids": (),
            "new_factor_kinds": (),
            "new_boundary_id": None,
            "boundary_ab_key_id": None,
            "boundary_ba_key_id": None,
            "boundary_stable_key_id": None,
            "termination": "invalid-candidate-action-state",
            "mechanism_failure": True,
            "total_calls": 3,
            "information_flow": information_flow(),
        }
    assert isinstance(action_key_id, str)
    assert isinstance(raw_factor_ids, list)
    factor_ids = tuple(raw_factor_ids)
    factor_kinds = tuple(factors_by_id[factor_id].kind for factor_id in factor_ids)
    base_votes = (primary_key_id, initial_top_ids[0], action_key_id)
    if len(set(base_votes)) == 1:
        if (
            tuple(actions) != (*base_actions, "stop:complete-consistent-state")
            or row.get("agent_escalated") is not False
            or tuple(votes) != base_votes
            or len(steps) != 3
            or row.get("calls") != 3
        ):
            raise SpeechNativeProfileError("M11 consistent stop is malformed")
        return {
            "policy_id": policy_id,
            "sample_id": sample_id,
            "speaker_id": speaker_id,
            "gold_key_id": gold_key_id,
            "primary_key_id": primary_key_id,
            "initial_top_key_ids": initial_top_ids,
            "retrieval_key_id": initial_top_ids[0],
            "action_key_id": action_key_id,
            "new_factor_ids": factor_ids,
            "new_factor_kinds": factor_kinds,
            "new_boundary_id": None,
            "boundary_ab_key_id": None,
            "boundary_ba_key_id": None,
            "boundary_stable_key_id": None,
            "termination": "complete-consistent-state",
            "mechanism_failure": False,
            "total_calls": 3,
            "information_flow": information_flow(selected_factor_ids=factor_ids),
        }

    challenger_key_id = (
        action_key_id if action_key_id != primary_key_id else initial_top_ids[0]
    )
    boundary = next(
        (
            item
            for item in decision_graph.boundaries
            if {item.left_key_id, item.right_key_id}
            == {primary_key_id, challenger_key_id}
        ),
        None,
    )
    if boundary is None:
        if (
            tuple(actions) != (*base_actions, "stop:no-registered-pair-boundary")
            or row.get("agent_escalated") is not False
            or tuple(votes) != base_votes
            or len(steps) != 3
            or row.get("calls") != 3
        ):
            raise SpeechNativeProfileError("M11 no-boundary stop is malformed")
        return {
            "policy_id": policy_id,
            "sample_id": sample_id,
            "speaker_id": speaker_id,
            "gold_key_id": gold_key_id,
            "primary_key_id": primary_key_id,
            "initial_top_key_ids": initial_top_ids,
            "retrieval_key_id": initial_top_ids[0],
            "action_key_id": action_key_id,
            "new_factor_ids": factor_ids,
            "new_factor_kinds": factor_kinds,
            "new_boundary_id": None,
            "boundary_ab_key_id": None,
            "boundary_ba_key_id": None,
            "boundary_stable_key_id": None,
            "termination": "no-registered-pair-boundary",
            "mechanism_failure": False,
            "total_calls": 3,
            "information_flow": information_flow(selected_factor_ids=factor_ids),
        }

    boundary_fields = {
        "action_id",
        "boundary_id",
        "primary_key_id",
        "challenger_key_id",
        "information_gap",
        "ab_key_id",
        "ba_key_id",
        "calls",
        "parse_failure",
        "new_knowledge_ids",
        "causal_parent_ids",
    }
    if not isinstance(steps[3], Mapping) or set(steps[3]) != boundary_fields:
        raise SpeechNativeProfileError("M11 pair-boundary stage is malformed")
    boundary_step = steps[3]
    ab_key_id = boundary_step.get("ab_key_id")
    ba_key_id = boundary_step.get("ba_key_id")
    pair = {primary_key_id, challenger_key_id}
    comparison_failed = ab_key_id not in pair or ba_key_id not in pair
    terminal_action = (
        "backtrack:invalid-pair-boundary-comparison"
        if comparison_failed
        else "select:retain-primary-for-support"
    )
    expected_actions = (
        *base_actions,
        f"retrieve:pair-boundary:{boundary.boundary_id}",
        "compare:boundary-ab",
        "compare:boundary-ba",
        terminal_action,
    )
    if (
        tuple(actions) != expected_actions
        or row.get("agent_escalated") is not True
        or len(steps) != 4
        or row.get("calls") != 5
        or tuple(votes) != (*base_votes, ab_key_id, ba_key_id)
        or boundary_step.get("action_id")
        != f"retrieve:pair-boundary:{boundary.boundary_id}"
        or boundary_step.get("boundary_id") != boundary.boundary_id
        or boundary_step.get("primary_key_id") != primary_key_id
        or boundary_step.get("challenger_key_id") != challenger_key_id
        or boundary_step.get("information_gap") != "candidate-disagreement"
        or boundary_step.get("calls") != 2
        or boundary_step.get("parse_failure") is not comparison_failed
        or boundary_step.get("new_knowledge_ids") != [boundary.boundary_id]
        or boundary_step.get("causal_parent_ids") != ["link:candidate-action-state"]
    ):
        raise SpeechNativeProfileError("M11 pair-boundary comparison is malformed")
    boundary_stable = (
        ab_key_id if not comparison_failed and ab_key_id == ba_key_id else None
    )
    return {
        "policy_id": policy_id,
        "sample_id": sample_id,
        "speaker_id": speaker_id,
        "gold_key_id": gold_key_id,
        "primary_key_id": primary_key_id,
        "initial_top_key_ids": initial_top_ids,
        "retrieval_key_id": initial_top_ids[0],
        "action_key_id": action_key_id,
        "new_factor_ids": factor_ids,
        "new_factor_kinds": factor_kinds,
        "new_boundary_id": boundary.boundary_id,
        "boundary_ab_key_id": ab_key_id,
        "boundary_ba_key_id": ba_key_id,
        "boundary_stable_key_id": boundary_stable,
        "termination": (
            "invalid-pair-boundary-comparison"
            if comparison_failed
            else "pair-boundary-compared"
        ),
        "mechanism_failure": comparison_failed,
        "total_calls": 5,
        "information_flow": information_flow(
            selected_factor_ids=factor_ids,
            boundary_id=boundary.boundary_id,
        ),
    }


def _m11_action_prediction(trajectory: Mapping[str, object], action_id: str) -> str:
    primary = str(trajectory["primary_key_id"])
    field_by_action = {
        "retain-primary": "primary_key_id",
        "select-retrieval-top1": "retrieval_key_id",
        "select-candidate-action-state": "action_key_id",
        "acquire-boundary-stable": "boundary_stable_key_id",
    }
    try:
        value = trajectory[field_by_action[action_id]]
    except KeyError as exc:
        raise SpeechNativeProfileError(
            f"unknown M11 training-free action {action_id!r}"
        ) from exc
    return str(value) if value is not None else primary


def _m11_action_available(trajectory: Mapping[str, object], action_id: str) -> bool:
    if bool(trajectory["mechanism_failure"]):
        return action_id == "retain-primary"
    if action_id == "acquire-boundary-stable":
        return (
            trajectory["new_boundary_id"] is not None
            and trajectory["boundary_stable_key_id"] is not None
        )
    if action_id == "select-candidate-action-state":
        return trajectory["action_key_id"] is not None
    return action_id in {"retain-primary", "select-retrieval-top1"}


def _m11_preboundary_state(
    trajectory: Mapping[str, object], *, exact: bool
) -> tuple[str, ...]:
    primary = str(trajectory["primary_key_id"])
    retrieval = str(trajectory["retrieval_key_id"])
    action = (
        str(trajectory["action_key_id"])
        if trajectory["action_key_id"] is not None
        else "missing"
    )
    initial_top = tuple(str(key_id) for key_id in trajectory["initial_top_key_ids"])
    try:
        primary_rank = str(initial_top.index(primary) + 1)
    except ValueError:
        primary_rank = "outside"
    factor_kinds = tuple(sorted(str(kind) for kind in trajectory["new_factor_kinds"]))
    state = (
        f"primary-retrieval:{'same' if primary == retrieval else 'different'}",
        f"primary-action:{'same' if primary == action else 'different'}",
        f"retrieval-action:{'same' if retrieval == action else 'different'}",
        f"primary-rank:{primary_rank}",
        f"factor-kinds:{','.join(factor_kinds) or 'none'}",
        f"boundary-available:{trajectory['new_boundary_id'] is not None}",
    )
    if not exact:
        return state
    factor_ids = tuple(
        sorted(str(factor_id) for factor_id in trajectory["new_factor_ids"])
    )
    return (
        *state,
        f"factor-ids:{','.join(factor_ids) or 'none'}",
        f"boundary-id:{trajectory['new_boundary_id'] or 'none'}",
    )


def _select_m11_action_from_reward_memory(
    trajectory: Mapping[str, object],
    reward_memory: Sequence[Mapping[str, object]],
    *,
    insufficient_support_reason: str,
) -> dict[str, object]:
    """Select one M11 action without reading the evaluated trajectory reward."""

    exact_state = _m11_preboundary_state(trajectory, exact=True)
    coarse_state = _m11_preboundary_state(trajectory, exact=False)
    exact_matches = tuple(
        row
        for row in reward_memory
        if _m11_preboundary_state(row, exact=True) == exact_state
    )
    if len(exact_matches) >= _M11_READER_CONTRACT_V1["oof_minimum_state_support"]:
        memory = exact_matches
        state_tier = "exact"
    else:
        memory = tuple(
            row
            for row in reward_memory
            if _m11_preboundary_state(row, exact=False) == coarse_state
        )
        state_tier = "coarse"

    candidate_statistics: list[dict[str, object]] = []
    qualified: list[dict[str, object]] = []
    if len(memory) >= _M11_READER_CONTRACT_V1["oof_minimum_state_support"] and not bool(
        trajectory["mechanism_failure"]
    ):
        for action_rank, action_id in enumerate(_M11_OOF_ACTION_IDS):
            if not _m11_action_available(trajectory, action_id):
                continue
            support = tuple(
                row for row in memory if _m11_action_available(row, action_id)
            )
            changed = sum(
                _m11_action_prediction(row, action_id) != row["primary_key_id"]
                for row in support
            )
            helpful = sum(
                row["primary_key_id"] != row["gold_key_id"]
                and _m11_action_prediction(row, action_id) == row["gold_key_id"]
                for row in support
            )
            harmful = sum(
                row["primary_key_id"] == row["gold_key_id"]
                and _m11_action_prediction(row, action_id) != row["gold_key_id"]
                for row in support
            )
            net_gain = helpful - harmful
            qualifies = (
                len(support) >= _M11_READER_CONTRACT_V1["oof_minimum_state_support"]
                and changed
                >= _M11_READER_CONTRACT_V1["oof_minimum_changed_prediction_support"]
                and helpful
                >= _M11_READER_CONTRACT_V1["oof_minimum_helpful_transitions"]
                and net_gain
                >= _M11_READER_CONTRACT_V1["oof_minimum_estimated_net_gain"]
                and harmful
                <= _M11_READER_CONTRACT_V1["oof_maximum_harmful_transitions"]
            )
            statistics = {
                "action_id": action_id,
                "support_count": len(support),
                "changed_prediction_count": changed,
                "helpful_transition_count": helpful,
                "harmful_transition_count": harmful,
                "estimated_net_gain": net_gain,
                "estimated_calls": _M11_OOF_ACTION_CALLS[action_id],
                "qualified": qualifies,
                "action_rank": action_rank,
            }
            candidate_statistics.append(statistics)
            if qualifies:
                qualified.append(statistics)

    selected_action = "retain-primary"
    selection_reason = "retain:no-zero-harm-positive-advantage-action"
    if len(memory) < _M11_READER_CONTRACT_V1["oof_minimum_state_support"]:
        selection_reason = insufficient_support_reason
    elif bool(trajectory["mechanism_failure"]):
        selection_reason = "retain:mechanism-failure"
    elif qualified:
        best = min(
            qualified,
            key=lambda row: (
                -int(row["estimated_net_gain"]),
                -int(row["helpful_transition_count"]),
                int(row["estimated_calls"]),
                int(row["action_rank"]),
            ),
        )
        selected_action = str(best["action_id"])
        selection_reason = f"select:{state_tier}-zero-harm-positive-advantage"
    selected_prediction = _m11_action_prediction(trajectory, selected_action)
    return {
        "sample_id": str(trajectory["sample_id"]),
        "state_schema": "m11-preboundary-relative-state-v1",
        "state_tier": state_tier,
        "training_state_match_count": len(memory),
        "selected_action_id": selected_action,
        "selected_key_id": selected_prediction,
        "selection_reason": selection_reason,
        "estimated_calls": _M11_OOF_ACTION_CALLS[selected_action],
        "candidate_statistics": candidate_statistics,
    }


def _score_m11_action_selections(
    trajectories: Sequence[Mapping[str, object]],
    selections: Sequence[Mapping[str, object]],
    *,
    status: str,
    reward_scope: str,
    speaker_fold_role: str,
    assignments: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Score already-frozen M11 actions after action-time inputs are closed."""

    frozen = tuple(trajectories)
    selected = tuple(selections)
    if not frozen or len(frozen) != len(selected):
        raise SpeechNativeProfileError(
            "M11 action scoring requires one selection per trajectory"
        )
    fold_trajectories = tuple(
        {
            "speaker_id": str(item["speaker_id"]),
            "gold_key_id": str(item["gold_key_id"]),
            "primary_key_id": str(item["primary_key_id"]),
            "canonical_key_id": None,
            "reverse_key_id": None,
            "rotate_key_id": None,
        }
        for item in frozen
    )
    validated_folds = _validate_training_free_trajectories(fold_trajectories)
    fold_assignments = (
        dict(assignments)
        if assignments is not None
        else _speaker_grouped_fold_assignments(validated_folds)
    )
    if set(fold_assignments) != {str(item["speaker_id"]) for item in frozen}:
        raise SpeechNativeProfileError("M11 speaker-fold assignments are incomplete")

    selected_predictions = [str(row["selected_key_id"]) for row in selected]
    selected_actions = [str(row["selected_action_id"]) for row in selected]
    selected_calls = [int(row["estimated_calls"]) for row in selected]
    action_audit = [
        {
            **dict(row),
            "fold_id": fold_assignments[str(item["speaker_id"])],
        }
        for row, item in zip(selected, frozen, strict=True)
    ]
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )
    selected_correct = sum(
        prediction == item["gold_key_id"]
        for prediction, item in zip(selected_predictions, frozen, strict=True)
    )
    wrong_to_correct = sum(
        item["primary_key_id"] != item["gold_key_id"]
        and prediction == item["gold_key_id"]
        for prediction, item in zip(selected_predictions, frozen, strict=True)
    )
    correct_to_wrong = sum(
        item["primary_key_id"] == item["gold_key_id"]
        and prediction != item["gold_key_id"]
        for prediction, item in zip(selected_predictions, frozen, strict=True)
    )
    action_count = sum(
        prediction != item["primary_key_id"]
        for prediction, item in zip(selected_predictions, frozen, strict=True)
    )
    action_rate = action_count / len(frozen)
    folds = _speaker_fold_metrics(
        validated_folds,
        assignments=fold_assignments,
        predictions=selected_predictions,
    )
    positive_folds = sum(int(fold["correct_delta_vs_primary"] > 0) for fold in folds)
    worst_fold = min(int(fold["correct_delta_vs_primary"]) for fold in folds)
    mean_estimated_calls = sum(selected_calls) / len(selected_calls)
    full_acquisition_mean_calls = sum(
        int(item["total_calls"]) for item in frozen
    ) / len(frozen)
    promotion_checks = {
        "net_gain_at_least_3": (
            selected_correct - primary_correct
            >= _M11_READER_CONTRACT_V1["promotion_minimum_net_gain"]
        ),
        "positive_fold_count_at_least_2": (
            positive_folds
            >= _M11_READER_CONTRACT_V1["promotion_minimum_positive_folds"]
        ),
        "worst_fold_delta_nonnegative": (
            worst_fold >= _M11_READER_CONTRACT_V1["promotion_minimum_worst_fold_delta"]
        ),
        "correct_to_wrong_at_most_1": (
            correct_to_wrong
            <= _M11_READER_CONTRACT_V1["promotion_maximum_harmful_transitions"]
        ),
        "action_rate_between_0_05_and_0_50": (
            _M11_READER_CONTRACT_V1["promotion_minimum_action_rate"]
            <= action_rate
            <= _M11_READER_CONTRACT_V1["promotion_maximum_action_rate"]
        ),
        "mean_calls_below_full_acquisition": (
            mean_estimated_calls < full_acquisition_mean_calls
        ),
    }
    return {
        "status": status,
        "policy_id": _M11_OOF_POLICY_ID,
        "state_schema": "m11-preboundary-relative-state-v1",
        "speaker_fold_policy_id": _SPEAKER_FOLD_POLICY_ID,
        "speaker_fold_role": speaker_fold_role,
        "label_blind_at_action_time": True,
        "reward_scope": reward_scope,
        "reader_contract": dict(_M11_READER_CONTRACT_V1),
        "minimum_state_support": _M11_READER_CONTRACT_V1["oof_minimum_state_support"],
        "minimum_changed_prediction_support": _M11_READER_CONTRACT_V1[
            "oof_minimum_changed_prediction_support"
        ],
        "minimum_helpful_transitions": _M11_READER_CONTRACT_V1[
            "oof_minimum_helpful_transitions"
        ],
        "minimum_estimated_net_gain": _M11_READER_CONTRACT_V1[
            "oof_minimum_estimated_net_gain"
        ],
        "maximum_harmful_transitions": _M11_READER_CONTRACT_V1[
            "oof_maximum_harmful_transitions"
        ],
        "correct": selected_correct,
        "accuracy": selected_correct / len(frozen),
        "correct_delta_vs_primary": selected_correct - primary_correct,
        "wrong_to_correct_vs_primary": wrong_to_correct,
        "correct_to_wrong_vs_primary": correct_to_wrong,
        "action_count": action_count,
        "action_rate": action_rate,
        "mean_estimated_calls": mean_estimated_calls,
        "full_acquisition_mean_calls": full_acquisition_mean_calls,
        "selected_action_counts": dict(sorted(Counter(selected_actions).items())),
        "speaker_folds_vs_primary": folds,
        "positive_delta_fold_count": positive_folds,
        "worst_fold_delta_vs_primary": worst_fold,
        "promotion_checks": promotion_checks,
        "promotion_gate_passed": all(promotion_checks.values()),
        "action_audit": action_audit,
    }


def _evaluate_m11_oof_action_advantage_policy(
    trajectories: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Cross-fit a conservative external action policy over frozen M11 traces.

    State and available action predictions are fixed before reward is read.  For
    each held-out speaker fold, only the other two folds may contribute reward
    memory.  A non-primary action requires five matching training states, three
    observed changed predictions, two helpful transitions, net gain of two, and
    zero harmful transitions.  Exact graph state backs off once to a relative
    state; thresholds never back off.
    """

    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError("M11 OOF policy requires trajectories")
    fold_trajectories = tuple(
        {
            "speaker_id": str(item["speaker_id"]),
            "gold_key_id": str(item["gold_key_id"]),
            "primary_key_id": str(item["primary_key_id"]),
            "canonical_key_id": None,
            "reverse_key_id": None,
            "rotate_key_id": None,
        }
        for item in frozen
    )
    validated_folds = _validate_training_free_trajectories(fold_trajectories)
    assignments = _speaker_grouped_fold_assignments(validated_folds)
    selections: list[dict[str, object]] = []
    for item in frozen:
        fold_id = assignments[str(item["speaker_id"])]
        train = tuple(
            other
            for other in frozen
            if assignments[str(other["speaker_id"])] != fold_id
        )
        selections.append(
            _select_m11_action_from_reward_memory(
                item,
                train,
                insufficient_support_reason=("retain:insufficient-oof-state-support"),
            )
        )
    return _score_m11_action_selections(
        frozen,
        selections,
        status="evaluated-after-support-gate",
        reward_scope="other-two-speaker-folds-only",
        speaker_fold_role="reward-exclusion-and-evaluation",
        assignments=assignments,
    )


def _evaluate_m11_memory_holdout_action_advantage_policy(
    discovery_memory: Sequence[Mapping[str, object]],
    holdout_trajectories: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Apply a discovery-qualified M11 reader to a speaker-unseen holdout.

    Discovery labels may define action advantage. Holdout labels are read only
    after every action and selected key are frozen from discovery rewards plus
    the holdout trajectory's pre-boundary state.
    """

    memory = tuple(discovery_memory)
    holdout = tuple(holdout_trajectories)
    if not memory or not holdout:
        raise SpeechNativeProfileError(
            "M11 memory-holdout evaluation requires both trajectory sets"
        )
    for role, rows in (("discovery memory", memory), ("holdout", holdout)):
        policy_ids = {row.get("policy_id") for row in rows}
        if len(policy_ids) != 1 or next(iter(policy_ids)) not in _M11_POLICY_IDS:
            raise SpeechNativeProfileError(
                f"M11 {role} trajectories mix policy identities"
            )
    if memory[0].get("policy_id") != holdout[0].get("policy_id"):
        raise SpeechNativeProfileError(
            "M11 memory and holdout policy identities differ"
        )

    memory_samples = tuple(str(row["sample_id"]) for row in memory)
    holdout_samples = tuple(str(row["sample_id"]) for row in holdout)
    if len(set(memory_samples)) != len(memory_samples) or len(
        set(holdout_samples)
    ) != len(holdout_samples):
        raise SpeechNativeProfileError(
            "M11 memory-holdout sample identity is duplicated"
        )
    sample_overlap = set(memory_samples) & set(holdout_samples)
    if sample_overlap:
        raise SpeechNativeProfileError(
            "M11 memory-holdout sample identity overlap is forbidden"
        )
    memory_speakers = {str(row["speaker_id"]) for row in memory}
    holdout_speakers = {str(row["speaker_id"]) for row in holdout}
    speaker_overlap = memory_speakers & holdout_speakers
    if speaker_overlap:
        raise SpeechNativeProfileError(
            "M11 memory-holdout speaker identity overlap is forbidden"
        )

    memory_information = _evaluate_m11_adaptive_evidence_gap(
        memory,
        enable_training_free_controller=True,
    )
    memory_controller = memory_information["training_free_controller"]
    if not isinstance(memory_controller, Mapping):
        raise SpeechNativeProfileError("M11 discovery controller is malformed")
    memory_support_passed = bool(memory_information["support_gate_passed"])
    memory_promotion_passed = bool(memory_controller.get("promotion_gate_passed"))
    common = {
        "evaluation_policy_id": _M11_MEMORY_HOLDOUT_EVALUATION_ID,
        "memory_query_count": len(memory),
        "holdout_query_count": len(holdout),
        "sample_identity_overlap_count": 0,
        "speaker_identity_overlap_count": 0,
        "memory_support_gate_passed": memory_support_passed,
        "memory_promotion_gate_passed": memory_promotion_passed,
    }
    if not memory_support_passed or not memory_promotion_passed:
        return {
            "status": "deferred-discovery-memory-gate-failed",
            "policy_id": _M11_OOF_POLICY_ID,
            "reward_scope": "discovery-memory-only",
            "label_blind_at_action_time": True,
            "holdout_rewards_read": False,
            "action_audit": [],
            **common,
        }

    selections = tuple(
        _select_m11_action_from_reward_memory(
            item,
            memory,
            insufficient_support_reason=(
                "retain:insufficient-discovery-memory-state-support"
            ),
        )
        for item in holdout
    )
    result = _score_m11_action_selections(
        holdout,
        selections,
        status="evaluated-discovery-memory-to-unread-holdout",
        reward_scope="discovery-memory-only",
        speaker_fold_role="evaluation-only",
    )
    result.update(
        {
            "holdout_rewards_read": True,
            "holdout_rewards_read_after_action_freeze": True,
            **common,
        }
    )
    return result


def _validated_m11_information_flow(
    trajectory: Mapping[str, object],
) -> dict[str, tuple[str, ...] | str | bool]:
    """Validate the canonical OBS/ORG/SUPPLY split reconstructed for one row."""

    flow = trajectory.get("information_flow")
    expected_fields = {
        "schema",
        "observation_source",
        "candidate_factor_supply_ids",
        "model_selected_factor_ids",
        "model_selected_state_is_external_supply",
        "incremental_boundary_supply_ids",
    }
    if not isinstance(flow, Mapping) or set(flow) != expected_fields:
        raise SpeechNativeProfileError("M11 information-flow ledger is malformed")

    def identifiers(field: str, *, allow_empty: bool) -> tuple[str, ...]:
        raw = flow.get(field)
        if (
            not isinstance(raw, (list, tuple))
            or (not allow_empty and not raw)
            or not all(isinstance(value, str) and value for value in raw)
            or len(set(raw)) != len(raw)
        ):
            raise SpeechNativeProfileError(f"M11 information-flow {field} is malformed")
        return tuple(raw)

    supplied = identifiers("candidate_factor_supply_ids", allow_empty=False)
    selected = identifiers("model_selected_factor_ids", allow_empty=True)
    boundaries = identifiers("incremental_boundary_supply_ids", allow_empty=True)
    expected_selected = tuple(str(value) for value in trajectory["new_factor_ids"])
    expected_boundary = (
        (str(trajectory["new_boundary_id"]),)
        if trajectory["new_boundary_id"] is not None
        else ()
    )
    if (
        flow.get("schema") != _M11_INFORMATION_FLOW_SCHEMA
        or flow.get("observation_source") != "speech_features"
        or flow.get("model_selected_state_is_external_supply") is not False
        or not set(selected).issubset(supplied)
        or selected != expected_selected
        or boundaries != expected_boundary
    ):
        raise SpeechNativeProfileError(
            "M11 information-flow ledger contradicts the recorded trajectory"
        )
    return {
        "schema": _M11_INFORMATION_FLOW_SCHEMA,
        "observation_source": "speech_features",
        "candidate_factor_supply_ids": supplied,
        "model_selected_factor_ids": selected,
        "model_selected_state_is_external_supply": False,
        "incremental_boundary_supply_ids": boundaries,
    }


def _m11_marginal_transition_metrics(
    trajectories: Sequence[Mapping[str, object]],
    flows: Sequence[Mapping[str, object]],
    *,
    supply_field: str,
    before_field: str,
    after_field: str,
    attribution_scope: str,
) -> dict[str, object]:
    """Describe observed state transitions without claiming isolated causality."""

    eligible: list[tuple[Mapping[str, object], str, str]] = []
    unresolved_count = 0
    for trajectory, flow in zip(trajectories, flows, strict=True):
        if not flow[supply_field]:
            continue
        before = trajectory.get(before_field)
        after = trajectory.get(after_field)
        if not isinstance(before, str) or not isinstance(after, str):
            unresolved_count += 1
            continue
        eligible.append((trajectory, before, after))
    helpful = [
        str(trajectory["sample_id"])
        for trajectory, before, after in eligible
        if before != trajectory["gold_key_id"] and after == trajectory["gold_key_id"]
    ]
    harmful = [
        str(trajectory["sample_id"])
        for trajectory, before, after in eligible
        if before == trajectory["gold_key_id"] and after != trajectory["gold_key_id"]
    ]
    return {
        "attribution_scope": attribution_scope,
        "eligible_count": len(eligible),
        "unresolved_count": unresolved_count,
        "changed_prediction_count": sum(
            before != after for _, before, after in eligible
        ),
        "helpful_transition_count": len(helpful),
        "harmful_transition_count": len(harmful),
        "neutral_transition_count": len(eligible) - len(helpful) - len(harmful),
        "estimated_net_gain": len(helpful) - len(harmful),
        "helpful_sample_ids": helpful,
        "harmful_sample_ids": harmful,
    }


def _evaluate_m11_adaptive_evidence_gap(
    trajectories: Sequence[Mapping[str, object]],
    *,
    enable_training_free_controller: bool = False,
) -> dict[str, object]:
    """Measure information-bearing M11 actions without selecting a controller."""

    frozen = tuple(trajectories)
    if not frozen:
        raise SpeechNativeProfileError(
            "M11 adaptive evidence-gap read requires trajectories"
        )
    policy_ids = {item.get("policy_id") for item in frozen}
    if len(policy_ids) != 1 or next(iter(policy_ids)) not in _M11_POLICY_IDS:
        raise SpeechNativeProfileError(
            "M11 adaptive evidence-gap read mixes policy identities"
        )
    policy_id = next(iter(policy_ids))
    information_flows = tuple(_validated_m11_information_flow(item) for item in frozen)
    primary_correct = sum(
        item["primary_key_id"] == item["gold_key_id"] for item in frozen
    )
    family_fields = {
        "retrieval-top1": "retrieval_key_id",
        "candidate-action-state": "action_key_id",
        "boundary-stable": "boundary_stable_key_id",
    }
    family_metrics: dict[str, dict[str, object]] = {}
    family_predictions: dict[str, list[str]] = {}
    for family_id, field in family_fields.items():
        predictions = [
            str(item[field]) if item[field] is not None else str(item["primary_key_id"])
            for item in frozen
        ]
        family_predictions[family_id] = predictions
        helpful = [
            str(item["sample_id"])
            for prediction, item in zip(predictions, frozen, strict=True)
            if item["primary_key_id"] != item["gold_key_id"]
            and prediction == item["gold_key_id"]
        ]
        harmful = [
            str(item["sample_id"])
            for prediction, item in zip(predictions, frozen, strict=True)
            if item["primary_key_id"] == item["gold_key_id"]
            and prediction != item["gold_key_id"]
        ]
        family_metrics[family_id] = {
            "correct": sum(
                prediction == item["gold_key_id"]
                for prediction, item in zip(predictions, frozen, strict=True)
            ),
            "action_query_count": sum(
                prediction != item["primary_key_id"]
                for prediction, item in zip(predictions, frozen, strict=True)
            ),
            "helpful_action_count": len(helpful),
            "harmful_action_count": len(harmful),
            "helpful_sample_ids": helpful,
            "harmful_sample_ids": harmful,
        }
    oracle_correct = sum(
        item["gold_key_id"]
        in {
            item["primary_key_id"],
            *(predictions[index] for predictions in family_predictions.values()),
        }
        for index, item in enumerate(frozen)
    )
    action_variable_count = sum(
        any(
            predictions[index] != item["primary_key_id"]
            for predictions in family_predictions.values()
        )
        for index, item in enumerate(frozen)
    )
    new_knowledge_query_count = sum(
        bool(item["new_factor_ids"]) or item["new_boundary_id"] is not None
        for item in frozen
    )
    adaptive_boundary_query_count = sum(
        item["new_boundary_id"] is not None for item in frozen
    )
    mechanism_failure_count = sum(bool(item["mechanism_failure"]) for item in frozen)
    calls_distribution = Counter(int(item["total_calls"]) for item in frozen)
    initial_top_k_reachable_count = sum(
        item["gold_key_id"] in item["initial_top_key_ids"] for item in frozen
    )
    boundary_stable_non_primary_action_count = sum(
        item["boundary_stable_key_id"] is not None
        and item["boundary_stable_key_id"] != item["primary_key_id"]
        for item in frozen
    )
    boundary_incremental_helpful_action_count = sum(
        item["primary_key_id"] != item["gold_key_id"]
        and item["retrieval_key_id"] != item["gold_key_id"]
        and item["action_key_id"] != item["gold_key_id"]
        and item["boundary_stable_key_id"] == item["gold_key_id"]
        for item in frozen
    )
    information_flow = {
        "schema": _M11_INFORMATION_FLOW_SCHEMA,
        "factor_supply_query_count": sum(
            bool(flow["candidate_factor_supply_ids"]) for flow in information_flows
        ),
        "factor_supply_id_reference_count": sum(
            len(flow["candidate_factor_supply_ids"]) for flow in information_flows
        ),
        "factor_selection_query_count": sum(
            bool(flow["model_selected_factor_ids"]) for flow in information_flows
        ),
        "factor_selection_id_reference_count": sum(
            len(flow["model_selected_factor_ids"]) for flow in information_flows
        ),
        "boundary_supply_query_count": sum(
            bool(flow["incremental_boundary_supply_ids"]) for flow in information_flows
        ),
        "boundary_supply_id_reference_count": sum(
            len(flow["incremental_boundary_supply_ids"]) for flow in information_flows
        ),
        "generated_state_external_supply_count": sum(
            bool(flow["model_selected_state_is_external_supply"])
            for flow in information_flows
        ),
        "factor_supply_transition": _m11_marginal_transition_metrics(
            frozen,
            information_flows,
            supply_field="candidate_factor_supply_ids",
            before_field="retrieval_key_id",
            after_field="action_key_id",
            attribution_scope="factor-supply-plus-speech-reobservation",
        ),
        "boundary_supply_transition": _m11_marginal_transition_metrics(
            frozen,
            information_flows,
            supply_field="incremental_boundary_supply_ids",
            before_field="action_key_id",
            after_field="boundary_stable_key_id",
            attribution_scope="boundary-supply-plus-pairwise-comparison",
        ),
    }
    support_checks = {
        "query_count_at_least_100": (
            len(frozen) >= _M11_READER_CONTRACT_V1["support_minimum_query_count"]
        ),
        "initial_top_k_reachable_count_at_least_100": (
            initial_top_k_reachable_count
            >= _M11_READER_CONTRACT_V1["support_minimum_top_k_reachable"]
        ),
        "action_variable_query_count_at_least_24": (
            action_variable_count
            >= _M11_READER_CONTRACT_V1["support_minimum_action_variable_queries"]
        ),
        "adaptive_boundary_query_count_at_least_18": (
            adaptive_boundary_query_count
            >= _M11_READER_CONTRACT_V1["support_minimum_adaptive_boundary_queries"]
        ),
        "boundary_stable_non_primary_action_count_at_least_12": (
            boundary_stable_non_primary_action_count
            >= _M11_READER_CONTRACT_V1["support_minimum_boundary_non_primary_actions"]
        ),
        "boundary_incremental_helpful_action_count_at_least_3": (
            boundary_incremental_helpful_action_count
            >= _M11_READER_CONTRACT_V1["support_minimum_incremental_boundary_repairs"]
        ),
        "oracle_gain_vs_primary_at_least_6": (
            oracle_correct - primary_correct
            >= _M11_READER_CONTRACT_V1["support_minimum_oracle_gain"]
        ),
        "mechanism_failure_count_zero": (
            mechanism_failure_count
            <= _M11_READER_CONTRACT_V1["support_maximum_mechanism_failures"]
        ),
    }
    support_gate_passed = all(support_checks.values())
    if not support_gate_passed:
        training_free_controller = {
            "status": "deferred-support-gate-failed",
            "policy_id": _M11_OOF_POLICY_ID,
        }
    elif not enable_training_free_controller:
        training_free_controller = {
            "status": "deferred-reader-contract-not-preregistered",
            "policy_id": _M11_OOF_POLICY_ID,
        }
    else:
        training_free_controller = _evaluate_m11_oof_action_advantage_policy(frozen)
    return {
        "policy_id": policy_id,
        "aggregator_id": _M11_AGGREGATOR_ID,
        "query_count": len(frozen),
        "primary_correct": primary_correct,
        "primary_accuracy": primary_correct / len(frozen),
        "final_minus_primary_correct": 0,
        "retrieval_top1_correct": family_metrics["retrieval-top1"]["correct"],
        "action_state_correct": family_metrics["candidate-action-state"]["correct"],
        "boundary_stable_correct": family_metrics["boundary-stable"]["correct"],
        "initial_top_k_reachable_count": initial_top_k_reachable_count,
        "new_knowledge_query_count": new_knowledge_query_count,
        "adaptive_boundary_query_count": adaptive_boundary_query_count,
        "unique_boundary_id_count": len(
            {
                str(item["new_boundary_id"])
                for item in frozen
                if item["new_boundary_id"] is not None
            }
        ),
        "boundary_stable_non_primary_action_count": (
            boundary_stable_non_primary_action_count
        ),
        "boundary_incremental_helpful_action_count": (
            boundary_incremental_helpful_action_count
        ),
        "action_variable_query_count": action_variable_count,
        "oracle_correct": oracle_correct,
        "oracle_gain_vs_primary": oracle_correct - primary_correct,
        "oracle_status": "diagnostic-only-not-an-admissible-controller",
        "mechanism_failure_count": mechanism_failure_count,
        "calls_distribution": {
            str(calls): count for calls, count in sorted(calls_distribution.items())
        },
        "action_families": family_metrics,
        "information_flow": information_flow,
        "support_gate_id": "m11-information-support-gate-v1",
        "reader_contract": dict(_M11_READER_CONTRACT_V1),
        "support_checks": support_checks,
        "support_gate_passed": support_gate_passed,
        "training_free_controller": training_free_controller,
    }


def _require_string(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise SpeechNativeProfileError(
            f"profile config {key} must be a non-empty string"
        )
    return value


def _require_positive_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SpeechNativeProfileError(
            f"profile config {key} must be a positive integer"
        )
    return value


def _load_binding_document(path: Path, expected_sha256: str) -> dict[str, object]:
    if _SHA256.fullmatch(expected_sha256) is None:
        raise SpeechNativeProfileError("speech-native binding SHA-256 is malformed")
    if _sha256_file(path) != expected_sha256:
        raise SpeechNativeProfileError("speech-native binding file SHA-256 mismatch")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read speech-native binding: {error}"
        ) from error
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
            raise SpeechNativeProfileError(
                "speech-native key card has unexpected fields"
            )
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


def _load_decision_graph(
    path: Path,
    *,
    expected_sha256: str,
    key_cards: Sequence[KeyCardV1],
) -> DecisionGraphV1:
    """Load one strict, file-hash-pinned knowledge graph artifact."""

    artifact_path = Path(path)
    if _SHA256.fullmatch(expected_sha256) is None:
        raise SpeechNativeProfileError("decision graph SHA-256 is malformed")
    if not artifact_path.is_file() or _sha256_file(artifact_path) != expected_sha256:
        raise SpeechNativeProfileError("decision graph file SHA-256 mismatch")
    try:
        document = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read decision graph: {error}"
        ) from error
    if not isinstance(document, dict) or set(document) != {
        "schema",
        "graph_id",
        "factors",
        "boundaries",
    }:
        raise SpeechNativeProfileError("decision graph has unexpected top-level fields")
    if document.get("schema") != "saea-decision-graph-v1":
        raise SpeechNativeProfileError("decision graph schema is unsupported")
    raw_factors = document.get("factors")
    raw_boundaries = document.get("boundaries")
    if not isinstance(raw_factors, list) or not isinstance(raw_boundaries, list):
        raise SpeechNativeProfileError("decision graph nodes and edges must be arrays")

    def string_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise SpeechNativeProfileError(
                f"decision graph {field_name} must be a string array"
            )
        return tuple(value)

    factors: list[DecisionFactorV1] = []
    for raw in raw_factors:
        if not isinstance(raw, dict) or set(raw) != {
            "factor_id",
            "kind",
            "statement",
            "key_ids",
            "provenance_ids",
        }:
            raise SpeechNativeProfileError(
                "decision graph factor has unexpected fields"
            )
        factors.append(
            DecisionFactorV1(
                factor_id=str(raw["factor_id"]),
                kind=str(raw["kind"]),
                statement=str(raw["statement"]),
                key_ids=string_tuple(raw["key_ids"], field_name="factor key_ids"),
                provenance_ids=string_tuple(
                    raw["provenance_ids"], field_name="factor provenance_ids"
                ),
            )
        )
    boundaries: list[DecisionBoundaryV1] = []
    for raw in raw_boundaries:
        if not isinstance(raw, dict) or set(raw) != {
            "boundary_id",
            "left_key_id",
            "right_key_id",
            "left_factor_ids",
            "right_factor_ids",
            "left_exclusion",
            "right_exclusion",
            "provenance_ids",
        }:
            raise SpeechNativeProfileError(
                "decision graph boundary has unexpected fields"
            )
        boundaries.append(
            DecisionBoundaryV1(
                boundary_id=str(raw["boundary_id"]),
                left_key_id=str(raw["left_key_id"]),
                right_key_id=str(raw["right_key_id"]),
                left_factor_ids=string_tuple(
                    raw["left_factor_ids"], field_name="boundary left_factor_ids"
                ),
                right_factor_ids=string_tuple(
                    raw["right_factor_ids"], field_name="boundary right_factor_ids"
                ),
                left_exclusion=str(raw["left_exclusion"]),
                right_exclusion=str(raw["right_exclusion"]),
                provenance_ids=string_tuple(
                    raw["provenance_ids"], field_name="boundary provenance_ids"
                ),
            )
        )
    try:
        return DecisionGraphV1(
            graph_id=str(document["graph_id"]),
            factors=tuple(factors),
            boundaries=tuple(boundaries),
        ).validate(key_cards)
    except PsluFlightError as error:
        raise SpeechNativeProfileError(f"decision graph is invalid: {error}") from error


def read_speech_native_predictions(
    *,
    attempt_dirs: Sequence[Path],
    binding_path: Path,
    binding_sha256: str,
    split_name: str,
) -> dict[str, object]:
    """Score prediction-only flights after each attempt is finalized.

    Gold labels enter only this model-free reader. Flight receipts and
    decision rows are hash-verified before scoring; the resident frozen-core
    service may remain online and is neither contacted nor modified.
    """

    if not attempt_dirs:
        raise SpeechNativeProfileError(
            "speech-native read requires at least one attempt"
        )
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
            raise SpeechNativeProfileError(
                f"cannot read flight receipt: {error}"
            ) from error
        if (
            not isinstance(receipt, dict)
            or receipt.get("status") != "COMPLETED"
            or receipt.get("request_failures") != []
            or receipt.get("split_identity_hash") is None
        ):
            raise SpeechNativeProfileError(
                "flight receipt is not a completed readable result"
            )
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
        profile_reader_policy_id, _profile_reader_contract = (
            _m11_reader_contract_from_values(profile, matcher_policy_id)
        )
        cell_id = f"{key_representation_id}-{matcher_policy_id}"
        if matcher_policy_id in {
            "M3",
            "M5",
            "M6",
            "M7",
            "M8",
            "M9",
            "M10",
            "M11",
        }:
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
                "speech-native-json-copy-v4": "-v4",
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
        elif matcher_policy_id == "M7":
            if (
                profile_agent_policy_id != _M7_POLICY_ID
                or agent_aggregator_id != _M7_AGGREGATOR_ID
                or key_representation_id not in {"K1", "K2"}
            ):
                raise SpeechNativeProfileError(
                    "M7 flight receipt has an unknown multistate identity"
                )
            cell_id += "-multistate-support-v1"
        elif matcher_policy_id == "M8":
            if (
                profile_agent_policy_id != _M8_POLICY_ID
                or agent_aggregator_id != _M8_AGGREGATOR_ID
                or key_representation_id != "K1"
            ):
                raise SpeechNativeProfileError(
                    "M8 flight receipt has an unknown pairwise identity"
                )
            cell_id += "-pairwise-boundary-support-v1"
        elif matcher_policy_id == "M9":
            if (
                profile_agent_policy_id != _M9_POLICY_ID
                or agent_aggregator_id != _M9_AGGREGATOR_ID
                or key_representation_id != "K1"
                or profile.get("decision_graph_id") != "slurp-scenario-factor-graph-v1"
            ):
                raise SpeechNativeProfileError(
                    "M9 flight receipt has an unknown factor-graph identity"
                )
            cell_id += "-factor-graph-support-v1"
        elif matcher_policy_id == "M10":
            if (
                profile_agent_policy_id != _M10_POLICY_ID
                or agent_aggregator_id != _M10_AGGREGATOR_ID
                or key_representation_id != "K1"
                or profile.get("decision_graph_id") != "slurp-scenario-factor-graph-v1"
            ):
                raise SpeechNativeProfileError(
                    "M10 flight receipt has an unknown candidate-evidence identity"
                )
            cell_id += "-candidate-evidence-support-v1"
        elif matcher_policy_id == "M11":
            if (
                profile_agent_policy_id not in _M11_POLICY_IDS
                or agent_aggregator_id != _M11_AGGREGATOR_ID
                or key_representation_id != "K1"
                or profile.get("decision_graph_id") not in _M11_DECISION_GRAPH_IDS
            ):
                raise SpeechNativeProfileError(
                    "M11 flight receipt has an unknown adaptive evidence-gap identity"
                )
            cell_id += (
                "-adaptive-evidence-gap-v2"
                if profile_agent_policy_id == _M11_KEY_CONDITIONED_POLICY_ID
                else "-adaptive-evidence-gap-v1"
            )
        profile_decision_graph: DecisionGraphV1 | None = None
        if matcher_policy_id in {"M9", "M10", "M11"}:
            graph_relpath = profile.get("decision_graph_path")
            graph_sha256 = profile.get("decision_graph_file_sha256")
            if (
                not isinstance(graph_relpath, str)
                or not graph_relpath
                or not isinstance(graph_sha256, str)
            ):
                raise SpeechNativeProfileError(
                    f"{matcher_policy_id} flight receipt lacks its pinned decision graph"
                )
            graph_path = (REPO_ROOT / graph_relpath).resolve()
            if graph_path == REPO_ROOT.resolve() or not graph_path.is_relative_to(
                REPO_ROOT.resolve()
            ):
                raise SpeechNativeProfileError(
                    f"{matcher_policy_id} decision graph path escapes the repository"
                )
            profile_decision_graph = _load_decision_graph(
                graph_path,
                expected_sha256=graph_sha256,
                key_cards=cards,
            )
            if profile_decision_graph.graph_id != profile.get("decision_graph_id"):
                raise SpeechNativeProfileError(
                    f"{matcher_policy_id} decision graph identity does not match its artifact"
                )
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
        visible_card_by_key = card_by_key
        if mechanism_control_id == "key-text-shuffle-v1":
            visible_card_by_key = {
                card.key_id: card for card in _shuffle_key_text(cards)
            }
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
            raise SpeechNativeProfileError(
                "decision count does not match receipt or split"
            )
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
        grounded_semantic_trajectories: list[dict[str, object]] = []
        multistate_trajectories: list[dict[str, object]] = []
        pairwise_trajectories: list[dict[str, object]] = []
        factor_graph_trajectories: list[dict[str, object]] = []
        candidate_evidence_trajectories: list[dict[str, object]] = []
        adaptive_evidence_gap_trajectories: list[dict[str, object]] = []
        for row in rows:
            if row.get("schema") != "saea-speech-native-decision-v1":
                raise SpeechNativeProfileError("decision schema mismatch")
            sample_id = row.get("sample_id")
            if (
                not isinstance(sample_id, str)
                or sample_id not in gold
                or sample_id in seen
            ):
                raise SpeechNativeProfileError("decision sample set is malformed")
            seen.add(sample_id)
            key_id = row.get("key_id")
            predicted = row.get("predicted_value_label")
            parse_failure = row.get("parse_failure")
            if not isinstance(parse_failure, bool):
                raise SpeechNativeProfileError("decision parse_failure must be boolean")
            if key_id is None:
                if predicted is not None or not parse_failure:
                    raise SpeechNativeProfileError(
                        "empty decision mapping is inconsistent"
                    )
            elif (
                not isinstance(key_id, str)
                or key_id not in label_by_key
                or predicted != label_by_key[key_id]
                or parse_failure
            ):
                raise SpeechNativeProfileError(
                    "decision key-to-label mapping is inconsistent"
                )
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
            row_control_id = row.get("mechanism_control_id", mechanism_control_id)
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
            if matcher_policy_id in {
                "M3",
                "M5",
                "M6",
                "M7",
                "M8",
                "M9",
                "M10",
                "M11",
            }:
                assert isinstance(top_k, int)
                maximum_returned_keys = 6 if matcher_policy_id == "M10" else top_k
                if len(raw_top_key_ids) > maximum_returned_keys:
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
                        if profile_agent_policy_id == "m1-m3-full-branch-explorer-v1"
                        or agent_escalated
                        else 2
                    )
                    or not all(
                        vote is None or isinstance(vote, str) and vote in label_by_key
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
                            isinstance(top_key_id, str) and top_key_id in label_by_key
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
                        or not isinstance(
                            score_document.get("confidence"), (int, float)
                        )
                        or not -1.0 <= float(score_document["confidence"]) <= 100.0
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
                    isinstance(vote, str) and label_by_key[vote] == gold[sample_id]
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
                agent_primary_fallback_correct_count += int(primary_fallback_correct)
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
                    agent_branch_neutral_count += int(primary_correct == final_correct)
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
                        vote is None or isinstance(vote, str) and vote in label_by_key
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
                            isinstance(top_key_id, str) and top_key_id in label_by_key
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
                    or agent_steps[0].get("action_id") != "match:speech-only-primary"
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
                            cards_by_key=visible_card_by_key,
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
                        or set(agent_steps[3]) != base_step_fields | {"verifier_scores"}
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
                            or not -1.0 <= float(score_document["confidence"]) <= 100.0
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
                agent_neutral_escalation_count += int(primary_correct == final_correct)
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
                if (
                    profile_agent_policy_id == _M6_SCHEMA_V3_POLICY_ID
                    and mechanism_control_id == "matched"
                    and not backtracked
                    and isinstance(primary_vote, str)
                    and isinstance(refined_vote, str)
                    and isinstance(state_document, Mapping)
                    and isinstance(step_scores, Mapping)
                    and isinstance(raw_calls, int)
                ):
                    grounded_semantic_trajectories.append(
                        {
                            "sample_id": sample_id,
                            "speaker_id": speaker_by_sample[sample_id],
                            "gold_key_id": key_by_label[gold[sample_id]],
                            "primary_key_id": primary_vote,
                            "refined_key_id": refined_vote,
                            "initial_top_key_ids": initial_top_ids,
                            "refined_top_key_ids": tuple(raw_top_key_ids),
                            "verifier_scores": {
                                score_key_id: (
                                    bool(score_document["compatible"]),
                                    float(score_document["confidence"]),
                                )
                                for score_key_id, score_document in step_scores.items()
                            },
                            "grounded_query_state": {
                                field: state_document[field]
                                for field in _GROUNDED_SEMANTIC_STATE_FIELDS
                            },
                            "total_calls": raw_calls,
                        }
                    )
            elif matcher_policy_id == "M7":
                assert isinstance(top_k, int)
                trajectory = _parse_m7_trajectory(
                    row=row,
                    sample_id=sample_id,
                    speaker_id=speaker_by_sample[sample_id],
                    gold_key_id=key_by_label[gold[sample_id]],
                    initial_top_ids=tuple(raw_top_key_ids),
                    top_k=top_k,
                    visible_card_by_key=visible_card_by_key,
                )
                multistate_trajectories.append(trajectory)
                agent_primary_correct_count += int(
                    trajectory["primary_key_id"] == trajectory["gold_key_id"]
                )
                branches = trajectory["branches"]
                assert isinstance(branches, tuple)
                agent_action_sensitive_count += int(
                    any(
                        branch["key_id"] != trajectory["primary_key_id"]
                        for branch in branches
                    )
                )
                raw_actions = row.get("agent_actions")
                assert isinstance(raw_actions, list)
                agent_action_counts.update(raw_actions)
            elif matcher_policy_id == "M10":
                assert isinstance(top_k, int)
                assert profile_decision_graph is not None
                trajectory = _parse_m10_candidate_evidence_trajectory(
                    row=row,
                    sample_id=sample_id,
                    speaker_id=speaker_by_sample[sample_id],
                    gold_key_id=key_by_label[gold[sample_id]],
                    top_k=top_k,
                    visible_card_by_key=visible_card_by_key,
                    decision_graph=profile_decision_graph,
                )
                candidate_evidence_trajectories.append(trajectory)
                agent_primary_correct_count += int(
                    trajectory["primary_key_id"] == trajectory["gold_key_id"]
                )
                primary = trajectory["primary_key_id"]
                agent_action_sensitive_count += int(
                    any(
                        key_id != primary
                        for field in (
                            "supported_action_key_ids",
                            "dual_evidence_action_key_ids",
                            "reconciled_action_key_ids",
                        )
                        for key_id in trajectory[field]
                    )
                )
                raw_actions = row.get("agent_actions")
                assert isinstance(raw_actions, list)
                agent_action_counts.update(raw_actions)
            elif matcher_policy_id == "M11":
                assert isinstance(top_k, int)
                assert profile_decision_graph is not None
                trajectory = _parse_m11_adaptive_evidence_gap_trajectory(
                    row=row,
                    sample_id=sample_id,
                    speaker_id=speaker_by_sample[sample_id],
                    gold_key_id=key_by_label[gold[sample_id]],
                    top_k=top_k,
                    visible_card_by_key=visible_card_by_key,
                    decision_graph=profile_decision_graph,
                )
                adaptive_evidence_gap_trajectories.append(trajectory)
                agent_primary_correct_count += int(
                    trajectory["primary_key_id"] == trajectory["gold_key_id"]
                )
                agent_action_sensitive_count += int(
                    trajectory["retrieval_key_id"] != trajectory["primary_key_id"]
                    or trajectory["action_key_id"]
                    not in {None, trajectory["primary_key_id"]}
                    or trajectory["boundary_stable_key_id"]
                    not in {None, trajectory["primary_key_id"]}
                )
                raw_actions = row.get("agent_actions")
                assert isinstance(raw_actions, list)
                agent_action_counts.update(raw_actions)
            elif matcher_policy_id == "M8":
                assert isinstance(top_k, int)
                trajectory = _parse_m8_pairwise_trajectory(
                    row=row,
                    sample_id=sample_id,
                    speaker_id=speaker_by_sample[sample_id],
                    gold_key_id=key_by_label[gold[sample_id]],
                    initial_top_ids=tuple(raw_top_key_ids),
                    top_k=top_k,
                    visible_card_by_key=visible_card_by_key,
                )
                pairwise_trajectories.append(trajectory)
                agent_primary_correct_count += int(
                    trajectory["primary_key_id"] == trajectory["gold_key_id"]
                )
                comparisons = trajectory["comparisons"]
                assert isinstance(comparisons, tuple)
                agent_action_sensitive_count += int(
                    any(
                        comparison["k1_stable_key_id"] is not None
                        or comparison["k2_stable_key_id"] is not None
                        for comparison in comparisons
                    )
                )
                raw_actions = row.get("agent_actions")
                assert isinstance(raw_actions, list)
                agent_action_counts.update(raw_actions)
            elif matcher_policy_id == "M9":
                assert isinstance(top_k, int)
                assert profile_decision_graph is not None
                trajectory = _parse_m9_factor_graph_trajectory(
                    row=row,
                    sample_id=sample_id,
                    speaker_id=speaker_by_sample[sample_id],
                    gold_key_id=key_by_label[gold[sample_id]],
                    top_k=top_k,
                    visible_card_by_key=visible_card_by_key,
                    decision_graph=profile_decision_graph,
                )
                factor_graph_trajectories.append(trajectory)
                agent_primary_correct_count += int(
                    trajectory["primary_key_id"] == trajectory["gold_key_id"]
                )
                agent_action_sensitive_count += int(
                    trajectory["reranked_key_ids"][0] != trajectory["primary_key_id"]
                    or (
                        trajectory["boundary_stable_key_id"] is not None
                        and trajectory["boundary_stable_key_id"]
                        != trajectory["primary_key_id"]
                    )
                )
                raw_actions = row.get("agent_actions")
                assert isinstance(raw_actions, list)
                agent_action_counts.update(raw_actions)
        if seen != set(gold):
            raise SpeechNativeProfileError(
                "decision sample set does not equal the frozen split"
            )
        if mechanism_control_id == "speech-swap-v1" and set(
            query_by_target.values()
        ) != set(gold):
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
                assignments=_speaker_grouped_fold_assignments(frozen_grounded_folds),
                predictions=grounded_final_predictions,
            )
        multistate_metrics: dict[str, object] | None = None
        if matcher_policy_id == "M7":
            if len(multistate_trajectories) != len(gold):
                raise SpeechNativeProfileError(
                    "M7 action-support trajectory count is incomplete"
                )
            multistate_metrics = _evaluate_m7_multistate_action_support(
                multistate_trajectories
            )
        pairwise_metrics: dict[str, object] | None = None
        if matcher_policy_id == "M8":
            if len(pairwise_trajectories) != len(gold):
                raise SpeechNativeProfileError(
                    "M8 pairwise-support trajectory count is incomplete"
                )
            pairwise_metrics = _evaluate_m8_pairwise_action_support(
                pairwise_trajectories
            )
        factor_graph_metrics: dict[str, object] | None = None
        if matcher_policy_id == "M9":
            if len(factor_graph_trajectories) != len(gold):
                raise SpeechNativeProfileError(
                    "M9 factor-graph trajectory count is incomplete"
                )
            factor_graph_metrics = _evaluate_m9_factor_graph_action_support(
                factor_graph_trajectories
            )
        candidate_evidence_metrics: dict[str, object] | None = None
        if matcher_policy_id == "M10":
            if len(candidate_evidence_trajectories) != len(gold):
                raise SpeechNativeProfileError(
                    "M10 candidate-evidence trajectory count is incomplete"
                )
            candidate_evidence_metrics = (
                _evaluate_m10_candidate_evidence_action_support(
                    candidate_evidence_trajectories
                )
            )
        adaptive_evidence_gap_metrics: dict[str, object] | None = None
        if matcher_policy_id == "M11":
            if len(adaptive_evidence_gap_trajectories) != len(gold):
                raise SpeechNativeProfileError(
                    "M11 adaptive evidence-gap trajectory count is incomplete"
                )
            adaptive_evidence_gap_metrics = _evaluate_m11_adaptive_evidence_gap(
                adaptive_evidence_gap_trajectories,
                enable_training_free_controller=(
                    profile_reader_policy_id == _M11_OOF_POLICY_ID
                ),
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
                    if matcher_policy_id
                    in {"M3", "M5", "M6", "M7", "M8", "M9", "M10", "M11"}
                    else None
                ),
                "top_k_reachability": (
                    top_k_reachable_count / len(gold)
                    if matcher_policy_id
                    in {"M3", "M5", "M6", "M7", "M8", "M9", "M10", "M11"}
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
                            "grounded_state_valid_count": (grounded_state_valid_count),
                            "grounded_state_valid_rate": (
                                grounded_state_valid_count / len(gold)
                            ),
                            "backtrack_count": grounded_backtrack_count,
                            "refined_change_count": (grounded_refined_change_count),
                            "helpful_refinement_count": (
                                agent_helpful_escalation_count
                            ),
                            "harmful_refinement_count": (
                                agent_harmful_escalation_count
                            ),
                            "neutral_refinement_count": (
                                agent_neutral_escalation_count
                            ),
                            "recoverable_error_count": (agent_recoverable_error_count),
                            "action_sensitive_count": (agent_action_sensitive_count),
                            "action_counts": dict(sorted(agent_action_counts.items())),
                            **(
                                {
                                    "training_free_grounded_semantic_policy": (
                                        _evaluate_training_free_grounded_semantic_policy(
                                            grounded_semantic_trajectories
                                        )
                                        if len(grounded_semantic_trajectories)
                                        == len(gold)
                                        else None
                                    )
                                }
                                if profile_agent_policy_id == _M6_SCHEMA_V3_POLICY_ID
                                and mechanism_control_id == "matched"
                                else {}
                            ),
                        }
                        if matcher_policy_id == "M6"
                        else (
                            multistate_metrics
                            if matcher_policy_id == "M7"
                            else (
                                pairwise_metrics
                                if matcher_policy_id == "M8"
                                else (
                                    factor_graph_metrics
                                    if matcher_policy_id == "M9"
                                    else (
                                        candidate_evidence_metrics
                                        if matcher_policy_id == "M10"
                                        else (
                                            adaptive_evidence_gap_metrics
                                            if matcher_policy_id == "M11"
                                            else None
                                        )
                                    )
                                )
                            )
                        )
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
        if not all(
            source_id in predictions_by_cell for source_id in ordered_source_ids
        ):
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
                calls_by_cell[source_id][sample_id] for source_id in ordered_source_ids
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
            if all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in source_contact_counts
            )
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
            required_ids = adaptive_source_ids if escalated else (primary_id, critic_id)
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
                "actual_contact_count": actual_contact_count
                if calls_complete
                else None,
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

    selectable = [
        item for item in aggregates if "-control-" not in str(item["cell_id"])
    ]
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
        raise SpeechNativeProfileError(
            f"cannot read packet promotion receipt: {error}"
        ) from error
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
            raise SpeechNativeProfileError(
                "packet receipt contains malformed or duplicate ids"
            )
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
            raise SpeechNativeProfileError(
                "speech-native key material ids are malformed"
            )
        source_by_key[key_id] = _packet_id_from_sample_id(
            item.get("audio_key_source_sample_id")
        )
    expected_keys = {card.key_id for card in key_cards}
    if set(source_by_key) != expected_keys:
        raise SpeechNativeProfileError(
            "audio-key material does not match frozen key cards"
        )
    bindings: dict[str, dict[str, str]] = {}
    for key_id in sorted(expected_keys):
        descriptor = packet_index.get(source_by_key[key_id])
        if not isinstance(descriptor, Mapping) or set(descriptor) != {
            "packet_id",
            "sha256",
        }:
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
    request_layout_id: str = "legacy-key-speech-v1",
    verifier_policy_id: str = "speech-native-compatibility-v1",
    audio_key_bindings: Mapping[str, Mapping[str, str]] | None = None,
    decision_graph: DecisionGraphV1 | None = None,
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
    if request_layout_id not in SPEECH_NATIVE_REQUEST_LAYOUTS:
        raise SpeechNativeProfileError(
            f"unknown speech-native request layout {request_layout_id!r}"
        )
    if matcher_policy_id in {"M9", "M10", "M11"} and decision_graph is None:
        raise SpeechNativeProfileError(
            f"{matcher_policy_id} profile tasks require a decision graph"
        )
    if matcher_policy_id not in {"M9", "M10", "M11"} and decision_graph is not None:
        raise SpeechNativeProfileError(
            "decision graph may only enter M9/M10/M11 profile tasks"
        )
    frozen_samples = tuple(samples)
    if mechanism_control_id == "speech-swap-v1" and len(frozen_samples) < 2:
        raise SpeechNativeProfileError(
            "speech-swap control requires at least two samples"
        )
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
                    request_layout_id=request_layout_id,
                    verifier_policy_id=verifier_policy_id,
                    decoding_params=dict(decoding_params),
                    top_k=top_k,
                    audio_key_bindings=audio_key_bindings,
                    decision_graph=decision_graph,
                    agent_policy_id=agent_policy_id,
                    agent_aggregator_id=agent_aggregator_id,
                )
            )
    return tuple(tasks)


def _enumerate_m11_prompt_envelopes(
    *,
    key_cards: Sequence[KeyCardV1],
    decision_graph: DecisionGraphV1,
    top_k: int,
    key_order_ids: Sequence[str],
    request_layout_id: str = "legacy-key-speech-v1",
) -> tuple[dict[str, object], ...]:
    """Exercise the real contact-batched M11 constructor without a model.

    The audit enumerates every possible ranked candidate tuple for the bounded
    top-k action contact and both endpoint orientations of every registered
    pair boundary.  It deliberately drives :func:`run_speech_native_match_tasks`
    instead of reimplementing prompt strings, so prompt-fit evidence cannot
    silently drift away from the inference path it is meant to admit.
    """

    cards = tuple(card.validate() for card in key_cards)
    if not cards or len({card.key_id for card in cards}) != len(cards):
        raise SpeechNativeProfileError(
            "M11 prompt enumeration requires unique validated key cards"
        )
    if (
        isinstance(top_k, bool)
        or not isinstance(top_k, int)
        or not 2 <= top_k <= min(3, len(cards))
    ):
        raise SpeechNativeProfileError(
            "M11 prompt enumeration requires top_k in [2, min(3, key count)]"
        )
    orders = tuple(key_order_ids)
    if not orders or len(set(orders)) != len(orders):
        raise SpeechNativeProfileError(
            "M11 prompt enumeration requires unique key order ids"
        )
    for order_id in orders:
        if order_id not in _ORDER_BUILDERS:
            raise SpeechNativeProfileError(f"unknown profile key order {order_id!r}")
    try:
        decision_graph.validate(cards)
    except PsluFlightError as error:
        raise SpeechNativeProfileError(
            f"M11 prompt enumeration decision graph is invalid: {error}"
        ) from error

    factors_by_key = {
        card.key_id: tuple(
            factor for factor in decision_graph.factors if card.key_id in factor.key_ids
        )
        for card in cards
    }

    def selected_factor_ids(key_id: str) -> tuple[str, ...]:
        factors = factors_by_key[key_id]
        operation = next(
            (factor for factor in factors if factor.kind == "operation"), None
        )
        if operation is None:
            raise SpeechNativeProfileError(
                f"M11 prompt enumeration key {key_id!r} lacks an operation factor"
            )
        return (
            operation.factor_id,
            *tuple(
                factor.factor_id
                for factor in factors
                if factor.factor_id != operation.factor_id
            )[:2],
        )

    key_ids = tuple(card.key_id for card in cards)
    plans: dict[str, dict[str, object]] = {}
    tasks: list[SpeechNativeMatchTask] = []
    query_descriptor = {
        "packet_id": "audit/prompt-fit/query",
        "sha256": "0" * 64,
        "role": "query",
    }

    def add_task(
        *,
        task_id: str,
        ordered_cards: tuple[KeyCardV1, ...],
        family: str,
        primary_key_id: str,
        top_key_ids: tuple[str, ...],
        action_key_id: str,
        factor_ids: tuple[str, ...],
        boundary_id: str | None = None,
    ) -> None:
        sample = type("M11PromptAuditSample", (), {"sample_id": task_id})()
        plans[task_id] = {
            "family": family,
            "primary_key_id": primary_key_id,
            "top_key_ids": top_key_ids,
            "action_key_id": action_key_id,
            "factor_ids": factor_ids,
            "boundary_id": boundary_id,
        }
        tasks.append(
            SpeechNativeMatchTask(
                task_id=task_id,
                sample=sample,
                query_descriptor=query_descriptor,
                key_cards=ordered_cards,
                key_representation_id="K1",
                matcher_policy_id="M11",
                prompt_policy_id="speech-native-json-copy-v4",
                request_layout_id=request_layout_id,
                top_k=top_k,
                decision_graph=decision_graph,
                agent_policy_id="speech-conditioned-adaptive-evidence-gap-v2",
                agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
            )
        )

    for order_id in orders:
        ordered_cards = _ORDER_BUILDERS[order_id](cards)
        ordered_ids = tuple(card.key_id for card in ordered_cards)
        add_task(
            task_id=f"initial:{order_id}",
            ordered_cards=ordered_cards,
            family="initial",
            primary_key_id=ordered_ids[0],
            top_key_ids=ordered_ids[:top_k],
            action_key_id=ordered_ids[0],
            factor_ids=selected_factor_ids(ordered_ids[0]),
        )

    for index, ranked_ids in enumerate(permutations(key_ids, top_k)):
        add_task(
            task_id=f"action:{index:06d}",
            ordered_cards=cards,
            family="action",
            primary_key_id=ranked_ids[0],
            top_key_ids=ranked_ids,
            action_key_id=ranked_ids[0],
            factor_ids=selected_factor_ids(ranked_ids[0]),
        )

    for boundary in decision_graph.boundaries:
        endpoints = (boundary.left_key_id, boundary.right_key_id)
        filler_ids = tuple(key_id for key_id in key_ids if key_id not in endpoints)
        for orientation, (primary_key_id, action_key_id) in enumerate(
            (endpoints, tuple(reversed(endpoints)))
        ):
            ranked_ids = (action_key_id, primary_key_id, *filler_ids)[:top_k]
            add_task(
                task_id=f"boundary:{boundary.boundary_id}:{orientation}",
                ordered_cards=cards,
                family="boundary",
                primary_key_id=primary_key_id,
                top_key_ids=ranked_ids,
                action_key_id=action_key_id,
                factor_ids=selected_factor_ids(action_key_id),
                boundary_id=boundary.boundary_id,
            )

    class PromptCaptureClient:
        def __init__(self) -> None:
            self.lock = threading.Lock()
            self.envelopes: list[dict[str, object]] = []

        def complete(self, messages, **kwargs):
            sample_id = kwargs["speech_feature_sample_id"]
            plan = plans[sample_id]
            stage_id = kwargs["matcher_policy_id"]
            family = plan["family"]
            capture = (
                (
                    family == "initial"
                    and (
                        stage_id.endswith(":primary-listwise")
                        or ":speech-retrieve-top-" in stage_id
                    )
                )
                or (family == "action" and stage_id.endswith(":candidate-action-state"))
                or (family == "boundary" and ":boundary-" in stage_id)
            )
            if capture:
                if family == "initial":
                    order_id = sample_id.split(":", 1)[1]
                    suffix = (
                        "primary"
                        if stage_id.endswith(":primary-listwise")
                        else "retrieval"
                    )
                    envelope_id = f"initial:{order_id}:{suffix}"
                    stage_kind = suffix
                elif family == "action":
                    ranked = "-".join(plan["top_key_ids"])
                    envelope_id = f"action:{ranked}"
                    stage_kind = "action"
                else:
                    suffix = "ab" if stage_id.endswith(":boundary-ab") else "ba"
                    envelope_id = (
                        f"boundary:{plan['boundary_id']}:"
                        f"{plan['primary_key_id']}:{suffix}"
                    )
                    stage_kind = "boundary"
                response_format = kwargs.get("decoding_params", {}).get(
                    "response_format"
                )
                if not isinstance(response_format, Mapping):
                    raise SpeechNativeProfileError(
                        "M11 prompt enumeration contact lacks response_format"
                    )
                with self.lock:
                    self.envelopes.append(
                        {
                            "envelope_id": envelope_id,
                            "stage_kind": stage_kind,
                            "stage_id": stage_id,
                            "candidate_key_ids": tuple(plan["top_key_ids"]),
                            "boundary_id": plan["boundary_id"],
                            "messages": tuple(messages),
                            "response_format": dict(response_format),
                        }
                    )
            if stage_id.endswith(":primary-listwise"):
                return json.dumps({"key_id": plan["primary_key_id"]})
            if ":speech-retrieve-top-" in stage_id:
                return json.dumps({"key_ids": plan["top_key_ids"]})
            if stage_id.endswith(":candidate-action-state"):
                return json.dumps(
                    {
                        "key_id": plan["action_key_id"],
                        "factor_ids": plan["factor_ids"],
                    }
                )
            if ":boundary-" in stage_id:
                return json.dumps({"key_id": plan["action_key_id"]})
            raise SpeechNativeProfileError(
                f"unexpected M11 prompt enumeration stage {stage_id!r}"
            )

        def complete_many(self, requests, *, trace_parent=None):
            del trace_parent
            return tuple(
                self.complete(messages, **kwargs) for messages, kwargs in requests
            )

    client = PromptCaptureClient()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tuple(tasks),
        slot_count=min(16, len(tasks)),
        queue_depth=max(2, min(64, len(tasks) * 2)),
        dispatch_granularity="contact",
    )
    if len(outcomes) != len(tasks):
        raise SpeechNativeProfileError(
            "M11 prompt enumeration did not complete every synthetic task"
        )
    ordered = tuple(sorted(client.envelopes, key=lambda item: item["envelope_id"]))
    if len({item["envelope_id"] for item in ordered}) != len(ordered):
        raise SpeechNativeProfileError(
            "M11 prompt enumeration produced duplicate envelope ids"
        )
    expected_count = (
        2 * len(orders)
        + math.perm(len(cards), top_k)
        + (4 * len(decision_graph.boundaries))
    )
    if len(ordered) != expected_count:
        raise SpeechNativeProfileError(
            f"M11 prompt enumeration produced {len(ordered)} envelopes; "
            f"expected {expected_count}"
        )
    return ordered


def _wire_m11_prompt_envelope(
    envelope: Mapping[str, object], *, prompt_order: str
) -> dict[str, object]:
    """Render one enumerated M11 envelope at the real transport boundary."""

    if prompt_order == "speech-features-text-keys-v1":
        # Historical prompt-fit receipts hashed matcher messages before the
        # transport rebuilt them. Preserve that replay contract exactly.
        return dict(envelope)
    messages = envelope.get("messages")
    if (
        not isinstance(messages, (list, tuple))
        or len(messages) != 2
        or not isinstance(messages[0], Mapping)
        or messages[0].get("role") != "system"
        or not isinstance(messages[0].get("content"), str)
        or not isinstance(messages[1], Mapping)
        or messages[1].get("role") != "user"
        or not isinstance(messages[1].get("content"), (list, tuple))
    ):
        raise SpeechNativeProfileError(
            "M11 wire prompt envelope messages are malformed"
        )
    text_values: list[str] = []
    feature_parts: list[dict[str, object]] = []
    for part in messages[1]["content"]:
        if not isinstance(part, Mapping):
            raise SpeechNativeProfileError("M11 wire prompt content part is malformed")
        if part.get("type") == "text":
            value = part.get("text")
            if not isinstance(value, str) or not value:
                raise SpeechNativeProfileError("M11 wire prompt text part is malformed")
            text_values.append(value)
            continue
        descriptor = part.get("speech_features")
        if part.get("type") != "input_speech_features" or not isinstance(
            descriptor, Mapping
        ):
            raise SpeechNativeProfileError(
                "M11 wire prompt contains an unsupported content part"
            )
        feature_parts.append(
            {
                "type": "input_speech_features",
                "speech_features": dict(descriptor),
            }
        )
    evidence_texts = [
        f"[evidence {_speech_supply_evidence_id(index, value)}] {value}"
        for index, value in enumerate(text_values)
    ]
    wire_content = _ordered_speech_feature_content(
        prompt_order=prompt_order,
        evidence_texts=evidence_texts,
        feature_parts=feature_parts,
    )
    return {
        **envelope,
        "messages": (
            {"role": "system", "content": messages[0]["content"]},
            {"role": "user", "content": wire_content},
        ),
    }


def _audit_m11_prompt_fit(
    *,
    envelopes: Sequence[Mapping[str, object]],
    token_count: Callable[[Mapping[str, object]], int],
    maximum_speech_feature_tokens: int,
    maximum_completion_tokens: int,
    context_tokens_per_slot: int,
    special_token_reserve: int = 2,
) -> dict[str, object]:
    """Bind exact M11 prompt construction to a conservative slot-fit result."""

    for name, value in (
        ("maximum_speech_feature_tokens", maximum_speech_feature_tokens),
        ("maximum_completion_tokens", maximum_completion_tokens),
        ("context_tokens_per_slot", context_tokens_per_slot),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise SpeechNativeProfileError(f"{name} must be a positive integer")
    if (
        isinstance(special_token_reserve, bool)
        or not isinstance(special_token_reserve, int)
        or not 0 <= special_token_reserve <= 2
    ):
        raise SpeechNativeProfileError(
            "special_token_reserve must be an integer in [0, 2]"
        )
    frozen = tuple(envelopes)
    if not frozen:
        raise SpeechNativeProfileError("M11 prompt fit requires prompt envelopes")
    rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for envelope in frozen:
        envelope_id = envelope.get("envelope_id")
        stage_kind = envelope.get("stage_kind")
        messages = envelope.get("messages")
        response_format = envelope.get("response_format")
        if (
            not isinstance(envelope_id, str)
            or not envelope_id
            or envelope_id in seen_ids
            or stage_kind not in {"primary", "retrieval", "action", "boundary"}
            or not isinstance(messages, (list, tuple))
            or not isinstance(response_format, Mapping)
        ):
            raise SpeechNativeProfileError("M11 prompt envelope is malformed")
        seen_ids.add(envelope_id)
        query_parts = [
            part.get("speech_features")
            for message in messages
            if isinstance(message, Mapping)
            for part in (
                message.get("content")
                if isinstance(message.get("content"), list)
                else []
            )
            if isinstance(part, Mapping)
            and part.get("type") == "input_speech_features"
            and isinstance(part.get("speech_features"), Mapping)
            and part["speech_features"].get("role") == "query"
        ]
        if len(query_parts) != 1:
            raise SpeechNativeProfileError(
                "M11 prompt envelope must carry exactly one query speech packet"
            )
        text_tokens = token_count(envelope)
        if (
            isinstance(text_tokens, bool)
            or not isinstance(text_tokens, int)
            or text_tokens <= 0
        ):
            raise SpeechNativeProfileError(
                "M11 prompt tokenizer returned a non-positive count"
            )
        prompt_upper_bound = (
            text_tokens + maximum_speech_feature_tokens + special_token_reserve
        )
        rows.append(
            {
                "envelope_id": envelope_id,
                "stage_kind": stage_kind,
                "messages_sha256": _canonical_sha256(messages),
                "response_format_sha256": _canonical_sha256(response_format),
                "text_prompt_tokens": text_tokens,
                "prompt_tokens_upper_bound": prompt_upper_bound,
            }
        )
    worst = max(
        rows,
        key=lambda row: (
            int(row["prompt_tokens_upper_bound"]),
            str(row["envelope_id"]),
        ),
    )
    maximum_text = max(int(row["text_prompt_tokens"]) for row in rows)
    maximum_prompt = int(worst["prompt_tokens_upper_bound"])
    margin = context_tokens_per_slot - maximum_prompt - maximum_completion_tokens
    stage_counts = Counter(str(row["stage_kind"]) for row in rows)
    return {
        "schema": "saea-speech-native-m11-prompt-fit-v1",
        "model_contact": False,
        "envelope_count": len(rows),
        "stage_counts": dict(sorted(stage_counts.items())),
        "maximum_text_prompt_tokens": maximum_text,
        "maximum_speech_feature_tokens": maximum_speech_feature_tokens,
        "special_token_reserve": special_token_reserve,
        "maximum_prompt_tokens_upper_bound": maximum_prompt,
        "maximum_completion_tokens": maximum_completion_tokens,
        "context_tokens_per_slot": context_tokens_per_slot,
        "context_margin_tokens": margin,
        "maximum_prompt_fits_one_slot": margin >= 0,
        "worst_envelope_id": worst["envelope_id"],
        "worst_envelope_messages_sha256": worst["messages_sha256"],
        "envelopes": rows,
    }


def _load_m11_prompt_fit_receipt(
    *,
    path: Path,
    expected_sha256: str,
    binding_sha256: str,
    graph_id: str,
    graph_sha256: str,
    packet_promotion_sha256: str,
    session_receipt_sha256: str,
    decoder_sha256: str,
    key_count: int,
    boundary_count: int,
    key_order_count: int,
    top_k: int,
    packet_count: int,
    context_tokens_per_slot: int,
    maximum_completion_tokens: int,
    expected_envelopes: Sequence[Mapping[str, object]],
    transport_prompt_order: str = "speech-features-text-keys-v1",
) -> Mapping[str, object]:
    """Verify that one tokenizer-only receipt admits this exact M11 profile."""

    for value, name in (
        (expected_sha256, "prompt-fit receipt"),
        (binding_sha256, "prompt-fit binding"),
        (graph_sha256, "prompt-fit graph"),
        (packet_promotion_sha256, "prompt-fit packet promotion"),
        (session_receipt_sha256, "prompt-fit session receipt"),
        (decoder_sha256, "prompt-fit decoder"),
    ):
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise SpeechNativeProfileError(f"{name} SHA-256 is malformed")
    for value, name in (
        (key_count, "key_count"),
        (boundary_count, "boundary_count"),
        (key_order_count, "key_order_count"),
        (top_k, "top_k"),
        (packet_count, "packet_count"),
        (context_tokens_per_slot, "context_tokens_per_slot"),
        (maximum_completion_tokens, "maximum_completion_tokens"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise SpeechNativeProfileError(f"prompt-fit {name} must be positive")
    if top_k > key_count:
        raise SpeechNativeProfileError("prompt-fit top_k exceeds key count")
    if not isinstance(transport_prompt_order, str) or not transport_prompt_order:
        raise SpeechNativeProfileError("prompt-fit transport_prompt_order is malformed")
    if _sha256_file(path) != expected_sha256:
        raise SpeechNativeProfileError("prompt-fit receipt SHA-256 mismatch")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read prompt-fit receipt: {error}"
        ) from error
    if not isinstance(document, Mapping) or document.get("schema") != (
        "saea-speech-native-m11-prompt-fit-v1"
    ):
        raise SpeechNativeProfileError("prompt-fit receipt schema mismatch")
    expected_identity = {
        "binding_file_sha256": binding_sha256,
        "decision_graph_id": graph_id,
        "decision_graph_file_sha256": graph_sha256,
        "packet_promotion_receipt_sha256": packet_promotion_sha256,
        "validated_packet_count": packet_count,
        "context_tokens_per_slot": context_tokens_per_slot,
        "maximum_completion_tokens": maximum_completion_tokens,
        "model_contact": False,
        "scope": "model-free-check",
        "new_model_contact_authorized": False,
    }
    if transport_prompt_order != "speech-features-text-keys-v1":
        expected_identity["transport_prompt_order"] = transport_prompt_order
    mismatches = {
        key: {"expected": expected, "observed": document.get(key)}
        for key, expected in expected_identity.items()
        if document.get(key) != expected
    }
    if mismatches:
        raise SpeechNativeProfileError(
            f"prompt-fit receipt identity mismatch: {mismatches!r}"
        )
    expected_stage_counts = {
        "action": math.perm(key_count, top_k),
        "boundary": 4 * boundary_count,
        "primary": key_order_count,
        "retrieval": key_order_count,
    }
    expected_envelope_count = sum(expected_stage_counts.values())
    expected_prompt_rows: dict[str, Mapping[str, object]] = {}
    for envelope in expected_envelopes:
        envelope_id = envelope.get("envelope_id")
        stage_kind = envelope.get("stage_kind")
        messages = envelope.get("messages")
        response_format = envelope.get("response_format")
        if (
            not isinstance(envelope_id, str)
            or not envelope_id
            or envelope_id in expected_prompt_rows
            or stage_kind not in expected_stage_counts
            or not isinstance(messages, Sequence)
            or isinstance(messages, (str, bytes))
            or not isinstance(response_format, Mapping)
        ):
            raise SpeechNativeProfileError("expected M11 prompt envelope is malformed")
        expected_prompt_rows[envelope_id] = {
            "stage_kind": stage_kind,
            "messages_sha256": _canonical_sha256(messages),
            "response_format_sha256": _canonical_sha256(response_format),
        }
    if len(expected_prompt_rows) != expected_envelope_count:
        raise SpeechNativeProfileError(
            "expected M11 prompt envelopes do not cover the action space"
        )
    if (
        document.get("stage_counts") != expected_stage_counts
        or document.get("envelope_count") != expected_envelope_count
    ):
        raise SpeechNativeProfileError(
            "prompt-fit receipt stage coverage does not match the M11 action space"
        )
    special_reserve = document.get("special_token_reserve")
    maximum_speech_tokens = document.get("maximum_speech_feature_tokens")
    if (
        isinstance(special_reserve, bool)
        or not isinstance(special_reserve, int)
        or special_reserve != 2
        or isinstance(maximum_speech_tokens, bool)
        or not isinstance(maximum_speech_tokens, int)
        or maximum_speech_tokens <= 0
    ):
        raise SpeechNativeProfileError(
            "prompt-fit receipt speech/special token reserves are malformed"
        )
    raw_rows = document.get("envelopes")
    if not isinstance(raw_rows, list) or len(raw_rows) != expected_envelope_count:
        raise SpeechNativeProfileError(
            "prompt-fit receipt envelope rows are incomplete"
        )
    rows: list[Mapping[str, object]] = []
    seen_ids: set[str] = set()
    expected_row_keys = {
        "envelope_id",
        "stage_kind",
        "messages_sha256",
        "response_format_sha256",
        "text_prompt_tokens",
        "prompt_tokens_upper_bound",
    }
    for raw in raw_rows:
        if not isinstance(raw, Mapping) or set(raw) != expected_row_keys:
            raise SpeechNativeProfileError(
                "prompt-fit receipt envelope row is malformed"
            )
        envelope_id = raw.get("envelope_id")
        stage_kind = raw.get("stage_kind")
        text_tokens = raw.get("text_prompt_tokens")
        prompt_tokens = raw.get("prompt_tokens_upper_bound")
        expected_prompt_row = expected_prompt_rows.get(str(envelope_id))
        if (
            not isinstance(envelope_id, str)
            or not envelope_id
            or envelope_id in seen_ids
            or stage_kind not in expected_stage_counts
            or not isinstance(raw.get("messages_sha256"), str)
            or _SHA256.fullmatch(str(raw.get("messages_sha256"))) is None
            or not isinstance(raw.get("response_format_sha256"), str)
            or _SHA256.fullmatch(str(raw.get("response_format_sha256"))) is None
            or isinstance(text_tokens, bool)
            or not isinstance(text_tokens, int)
            or text_tokens <= 0
            or isinstance(prompt_tokens, bool)
            or not isinstance(prompt_tokens, int)
            or prompt_tokens != text_tokens + maximum_speech_tokens + special_reserve
            or expected_prompt_row is None
            or stage_kind != expected_prompt_row["stage_kind"]
            or raw.get("messages_sha256") != expected_prompt_row["messages_sha256"]
            or raw.get("response_format_sha256")
            != expected_prompt_row["response_format_sha256"]
        ):
            raise SpeechNativeProfileError(
                "prompt-fit receipt envelope token accounting is malformed"
            )
        seen_ids.add(envelope_id)
        rows.append(raw)
    observed_stage_counts = Counter(str(row["stage_kind"]) for row in rows)
    if dict(sorted(observed_stage_counts.items())) != expected_stage_counts:
        raise SpeechNativeProfileError(
            "prompt-fit receipt envelope rows disagree with stage coverage"
        )
    worst = max(
        rows,
        key=lambda row: (
            int(row["prompt_tokens_upper_bound"]),
            str(row["envelope_id"]),
        ),
    )
    maximum_prompt = int(worst["prompt_tokens_upper_bound"])
    margin = context_tokens_per_slot - maximum_prompt - maximum_completion_tokens
    if (
        document.get("maximum_text_prompt_tokens")
        != max(int(row["text_prompt_tokens"]) for row in rows)
        or document.get("maximum_prompt_tokens_upper_bound") != maximum_prompt
        or document.get("worst_envelope_id") != worst["envelope_id"]
        or document.get("worst_envelope_messages_sha256") != worst["messages_sha256"]
        or document.get("context_margin_tokens") != margin
        or document.get("maximum_prompt_fits_one_slot") is not True
        or margin < 0
    ):
        raise SpeechNativeProfileError(
            "prompt-fit receipt maximum or slot margin is inconsistent"
        )
    runtime = document.get("runtime")
    if (
        not isinstance(runtime, Mapping)
        or runtime.get("session_receipt_sha256") != session_receipt_sha256
        or runtime.get("decoder_sha256") != decoder_sha256
        or runtime.get("mmproj_loaded") is not False
    ):
        raise SpeechNativeProfileError("prompt-fit receipt runtime identity mismatch")
    tokenizer = document.get("tokenizer")
    expected_request_counts = {
        "GET /props": 1,
        "POST /apply-template": expected_envelope_count,
        "POST /tokenize": 2 * expected_envelope_count,
    }
    if (
        not isinstance(tokenizer, Mapping)
        or tokenizer.get("request_counts") != expected_request_counts
        or tokenizer.get("decoder_evaluations") != 0
        or tokenizer.get("generated_tokens") != 0
        or not isinstance(tokenizer.get("media_marker"), str)
        or not tokenizer.get("media_marker")
        or not isinstance(tokenizer.get("chat_template_sha256"), str)
        or _SHA256.fullmatch(str(tokenizer.get("chat_template_sha256"))) is None
    ):
        raise SpeechNativeProfileError(
            "prompt-fit receipt tokenizer accounting is malformed"
        )
    return document


def _validate_m11_prompt_fit_for_profile(
    *,
    path: Path,
    expected_sha256: str,
    binding_sha256: str,
    decision_graph: DecisionGraphV1,
    graph_sha256: str,
    packet_promotion_sha256: str,
    session_receipt_sha256: str,
    server_env: Mapping[str, str],
    key_cards: Sequence[KeyCardV1],
    key_order_ids: Sequence[str],
    top_k: int,
    packet_count: int,
    context_tokens_per_slot: int,
    maximum_completion_tokens: int,
    request_layout_id: str = "legacy-key-speech-v1",
    transport_prompt_order: str = "speech-features-text-keys-v1",
) -> Mapping[str, object]:
    """Bind an M11 prompt-fit receipt to one formal resident profile."""

    decoder_sha256 = server_env.get("LLAMA_SPEECH_DECODER_SHA256")
    if not isinstance(decoder_sha256, str) or _SHA256.fullmatch(decoder_sha256) is None:
        raise SpeechNativeProfileError(
            "M11 prompt-fit gate lacks a decoder SHA-256 binding"
        )
    expected_envelopes = tuple(
        _wire_m11_prompt_envelope(
            envelope,
            prompt_order=transport_prompt_order,
        )
        for envelope in _enumerate_m11_prompt_envelopes(
            key_cards=key_cards,
            decision_graph=decision_graph,
            top_k=top_k,
            key_order_ids=key_order_ids,
            request_layout_id=request_layout_id,
        )
    )
    return _load_m11_prompt_fit_receipt(
        path=path,
        expected_sha256=expected_sha256,
        binding_sha256=binding_sha256,
        graph_id=decision_graph.graph_id,
        graph_sha256=graph_sha256,
        packet_promotion_sha256=packet_promotion_sha256,
        session_receipt_sha256=session_receipt_sha256,
        decoder_sha256=decoder_sha256,
        key_count=len(key_cards),
        boundary_count=len(decision_graph.boundaries),
        key_order_count=len(key_order_ids),
        top_k=top_k,
        packet_count=packet_count,
        context_tokens_per_slot=context_tokens_per_slot,
        maximum_completion_tokens=maximum_completion_tokens,
        expected_envelopes=expected_envelopes,
        transport_prompt_order=transport_prompt_order,
    )


def _resolve_m11_prompt_fit_config(
    *,
    repo_root: Path,
    values: Mapping[str, object],
    matcher_policy_id: str,
    session_receipt: object,
) -> tuple[Path | None, str | None, int | None]:
    """Resolve the formal M11 gate before creating per-attempt artifacts."""

    if matcher_policy_id != "M11":
        return None, None, None
    if session_receipt is None:
        raise SpeechNativeProfileError(
            "M11 requires a receipt-bound resident session; starting a per-attempt "
            "server is prohibited"
        )
    prompt_fit_relpath = _require_string(values, "speech_native_prompt_fit_receipt")
    prompt_fit_path = (repo_root / prompt_fit_relpath).resolve()
    if prompt_fit_path == repo_root.resolve() or not prompt_fit_path.is_relative_to(
        repo_root.resolve()
    ):
        raise SpeechNativeProfileError(
            "M11 prompt-fit receipt must stay under the repository"
        )
    expected_sha256 = _require_string(values, "speech_native_prompt_fit_receipt_sha256")
    decoding_params = values.get("decoding_params")
    if not isinstance(decoding_params, Mapping):
        raise SpeechNativeProfileError("M11 decoding_params are malformed")
    maximum_completion_tokens = decoding_params.get("max_tokens")
    if (
        isinstance(maximum_completion_tokens, bool)
        or not isinstance(maximum_completion_tokens, int)
        or maximum_completion_tokens <= 0
    ):
        raise SpeechNativeProfileError(
            "M11 prompt-fit gate requires a positive max_tokens ceiling"
        )
    return prompt_fit_path, expected_sha256, maximum_completion_tokens


def _m11_prompt_text_token_count(
    *,
    envelope: Mapping[str, object],
    media_marker: str,
    post_json: Callable[[str, Mapping[str, object]], Mapping[str, object]],
) -> int:
    """Count the exact text segments used by speech-feature prompt assembly.

    The pinned server replaces its media marker with precomputed embedding
    tokens and tokenizes the text on each side independently.  This helper
    mirrors that boundary through the server's non-generative template and
    tokenizer endpoints; speech-feature and possible BOS/EOS tokens are added
    separately by :func:`_audit_m11_prompt_fit`.
    """

    messages = envelope.get("messages")
    response_format = envelope.get("response_format")
    if (
        not isinstance(messages, (list, tuple))
        or not isinstance(response_format, Mapping)
        or not isinstance(media_marker, str)
        or not media_marker
    ):
        raise SpeechNativeProfileError("M11 prompt tokenizer inputs are malformed")
    rendered = post_json(
        "/apply-template",
        {
            "messages": list(messages),
            "response_format": response_format,
        },
    )
    prompt = rendered.get("prompt") if isinstance(rendered, Mapping) else None
    if not isinstance(prompt, str):
        raise SpeechNativeProfileError(
            "llama.cpp apply-template response lacks a string prompt"
        )
    if prompt.count(media_marker) != 1:
        raise SpeechNativeProfileError(
            "rendered M11 prompt must contain exactly one media marker"
        )
    total = 0
    for segment in prompt.split(media_marker):
        if not segment:
            continue
        response = post_json(
            "/tokenize",
            {
                "content": segment,
                "add_special": False,
                "parse_special": True,
            },
        )
        tokens = response.get("tokens") if isinstance(response, Mapping) else None
        if not isinstance(tokens, list) or any(
            isinstance(token, bool) or not isinstance(token, int) for token in tokens
        ):
            raise SpeechNativeProfileError(
                "llama.cpp tokenize response contains malformed tokens"
            )
        total += len(tokens)
    if total <= 0:
        raise SpeechNativeProfileError(
            "llama.cpp rendered M11 prompt token count is not positive"
        )
    return total


class _LoopbackPromptAuditClient:
    """Thread-local keep-alive client for non-generative llama.cpp routes."""

    def __init__(self, *, host: str, port: int, timeout_seconds: float) -> None:
        if (
            not isinstance(host, str)
            or not host
            or isinstance(port, bool)
            or not isinstance(port, int)
            or not 0 < port < 65536
            or isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(float(timeout_seconds))
            or float(timeout_seconds) <= 0
        ):
            raise SpeechNativeProfileError(
                "prompt-audit HTTP client configuration is malformed"
            )
        self.host = host
        self.port = port
        self.timeout_seconds = float(timeout_seconds)
        self.local = threading.local()
        self.lock = threading.Lock()
        self.request_counts: Counter[str] = Counter()

    def _connection(self) -> http.client.HTTPConnection:
        connection = getattr(self.local, "connection", None)
        if connection is None:
            connection = http.client.HTTPConnection(
                self.host, self.port, timeout=self.timeout_seconds
            )
            self.local.connection = connection
        return connection

    def request_json(
        self, method: str, path: str, payload: Mapping[str, object] | None = None
    ) -> Mapping[str, object]:
        if method not in {"GET", "POST"} or not path.startswith("/"):
            raise SpeechNativeProfileError("prompt-audit HTTP request is malformed")
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            connection = self._connection()
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read()
        except (OSError, http.client.HTTPException) as error:
            raise SpeechNativeProfileError(
                f"llama.cpp prompt-audit request failed: {error}"
            ) from error
        with self.lock:
            self.request_counts[f"{method} {path}"] += 1
        if response.status != 200:
            raise SpeechNativeProfileError(
                f"llama.cpp prompt-audit endpoint {path!r} returned HTTP "
                f"{response.status}: {raw[:500].decode('utf-8', 'replace')}"
            )
        try:
            document = json.loads(raw)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise SpeechNativeProfileError(
                f"llama.cpp prompt-audit endpoint {path!r} returned invalid JSON"
            ) from error
        if not isinstance(document, Mapping):
            raise SpeechNativeProfileError(
                f"llama.cpp prompt-audit endpoint {path!r} returned a non-object"
            )
        return document

    def get_json(self, path: str) -> Mapping[str, object]:
        return self.request_json("GET", path)

    def post_json(
        self, path: str, payload: Mapping[str, object]
    ) -> Mapping[str, object]:
        return self.request_json("POST", path, payload)


def profile_timing_metrics(
    timings: Sequence[Mapping[str, object]],
    *,
    slot_count: int,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, float]:
    """Derive throughput and a client-side request-concurrency proxy."""

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


def profile_saturated_gpu_metrics(
    *,
    timing_rows: Sequence[Mapping[str, object]],
    resource_summary: Mapping[str, object],
    slot_count: int,
) -> dict[str, int | float | str]:
    """Measure GPU utilization while llama-server slots are truly busy.

    New profiles use receipt-bound ``/slots`` snapshots captured beside each
    GPU sample. Historical receipts lack those fields, so their former HTTP
    interval reconstruction remains readable under an explicit legacy source;
    :func:`profile_gpu_eligibility` never admits that proxy for a new run.
    """

    if (
        isinstance(slot_count, bool)
        or not isinstance(slot_count, int)
        or slot_count <= 0
    ):
        raise SpeechNativeProfileError("slot_count must be a positive integer")
    raw_samples = resource_summary.get("request_gpu_samples")
    if not isinstance(raw_samples, list):
        raise SpeechNativeProfileError("request GPU sample timeline is unavailable")
    minimum_active = max(1, math.ceil(slot_count * 0.90))
    saturated_utilization: list[float] = []
    exact_configured = resource_summary.get("server_slot_sampling_configured") is True
    exact_fields = {
        "server_busy_slots",
        "server_total_slots",
        "server_slot_sampled_at_unix_seconds",
        "server_slot_gpu_skew_milliseconds",
    }
    exact_present = any(
        isinstance(sample, Mapping) and any(field in sample for field in exact_fields)
        for sample in raw_samples
    )
    use_server_slots = exact_configured or exact_present
    slot_occupancy: list[float] = []
    slot_skews: list[float] = []

    intervals: list[tuple[float, float]] = []
    if not use_server_slots:
        for timing in timing_rows:
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
            intervals.append((start, start + float(latency)))

    for sample in raw_samples:
        if not isinstance(sample, Mapping):
            raise SpeechNativeProfileError("request GPU sample is malformed")
        sampled_at = sample.get("sampled_at_unix_seconds")
        utilization = sample.get("utilization_pct")
        if (
            isinstance(sampled_at, bool)
            or not isinstance(sampled_at, (int, float))
            or not math.isfinite(float(sampled_at))
            or isinstance(utilization, bool)
            or not isinstance(utilization, (int, float))
            or not math.isfinite(float(utilization))
        ):
            raise SpeechNativeProfileError("request GPU sample is malformed")
        if use_server_slots:
            present_fields = exact_fields.intersection(sample)
            if not present_fields:
                continue
            if present_fields != exact_fields:
                raise SpeechNativeProfileError("server slot sample is incomplete")
            busy_slots = sample.get("server_busy_slots")
            total_slots = sample.get("server_total_slots")
            slot_sampled_at = sample.get("server_slot_sampled_at_unix_seconds")
            skew = sample.get("server_slot_gpu_skew_milliseconds")
            if (
                isinstance(busy_slots, bool)
                or not isinstance(busy_slots, int)
                or isinstance(total_slots, bool)
                or not isinstance(total_slots, int)
                or total_slots <= 0
                or busy_slots < 0
                or busy_slots > total_slots
                or isinstance(slot_sampled_at, bool)
                or not isinstance(slot_sampled_at, (int, float))
                or not math.isfinite(float(slot_sampled_at))
                or isinstance(skew, bool)
                or not isinstance(skew, (int, float))
                or not math.isfinite(float(skew))
                or float(skew) < 0
            ):
                raise SpeechNativeProfileError("server slot sample is malformed")
            reconstructed_skew = (
                abs(float(slot_sampled_at) - float(sampled_at)) * 1000.0
            )
            if not math.isclose(
                reconstructed_skew,
                float(skew),
                rel_tol=0.0,
                abs_tol=0.001,
            ):
                raise SpeechNativeProfileError(
                    "server slot sample timestamp and GPU skew disagree"
                )
            if total_slots != slot_count:
                raise SpeechNativeProfileError(
                    "server slot count does not match the profile slot count"
                )
            slot_occupancy.append(100.0 * busy_slots / total_slots)
            slot_skews.append(float(skew))
            if busy_slots >= minimum_active:
                saturated_utilization.append(float(utilization))
        else:
            active = sum(start <= float(sampled_at) < end for start, end in intervals)
            if active >= minimum_active:
                saturated_utilization.append(float(utilization))
    sample_count = len(saturated_utilization)
    sample_fraction = 100.0 * sample_count / len(raw_samples) if raw_samples else 0.0
    if not saturated_utilization:
        median: float | str = NOT_AVAILABLE
        p10: float | str = NOT_AVAILABLE
    else:
        ordered = sorted(saturated_utilization)
        median = float(statistics.median(ordered))
        p10 = float(ordered[max(0, math.ceil(0.10 * len(ordered)) - 1)])
    result: dict[str, int | float | str] = {
        "saturation_source": (
            "llama-server-slots-v1" if use_server_slots else "client-http-intervals-v1"
        ),
        "minimum_active_requests": minimum_active,
        "sample_count": sample_count,
        "sample_fraction_pct": sample_fraction,
        "utilization_median_pct": median,
        "utilization_p10_pct": p10,
    }
    if use_server_slots:
        raw_failures = resource_summary.get("server_slot_probe_failure_count", 0)
        if (
            isinstance(raw_failures, bool)
            or not isinstance(raw_failures, int)
            or raw_failures < 0
        ):
            raise SpeechNativeProfileError("server slot failure count is malformed")
        slot_sample_count = len(slot_occupancy)
        result.update(
            {
                "server_slot_sample_count": slot_sample_count,
                "server_slot_sample_coverage_pct": (
                    100.0 * slot_sample_count / len(raw_samples) if raw_samples else 0.0
                ),
                "server_slot_probe_failure_count": raw_failures,
                "server_slot_gpu_skew_max_milliseconds": (
                    max(slot_skews) if slot_skews else NOT_AVAILABLE
                ),
                "server_slot_occupancy_mean_pct": (
                    statistics.fmean(slot_occupancy)
                    if slot_occupancy
                    else NOT_AVAILABLE
                ),
            }
        )
    return result


def profile_gpu_eligibility(
    saturated_gpu: Mapping[str, object],
) -> dict[str, bool]:
    """Apply the prospective, exact-slot GPU admission gate.

    Every threshold below reads a missing/``NOT_AVAILABLE`` field as
    ``False`` -- fail-closed, so a GPU sampler outage never silently passes
    an ENGINEERING-baseline admission threshold (owner ruling
    ``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md`` S2.1
    keeps the 95/90 saturated-median/P10 requirement for engineering
    acceptance). A plain ``False`` cannot by itself distinguish "measured and
    below threshold" from "no telemetry to measure", so
    ``gpu_telemetry_available`` is reported explicitly alongside the
    thresholds: when it is ``False`` the other GPU booleans here are "not
    evaluable: telemetry unavailable", not a measured failure.
    """

    def at_least(field: str, threshold: float) -> bool:
        value = saturated_gpu.get(field)
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            and float(value) >= threshold
        )

    source = saturated_gpu.get("saturation_source")
    if source == "llama-server-slot-events-v1":
        failure_count = saturated_gpu.get("server_slot_measurement_failure_count")
        maximum_clock_error = saturated_gpu.get(
            "server_slot_clock_alignment_upper_bound_milliseconds"
        )
    else:
        failure_count = saturated_gpu.get("server_slot_probe_failure_count")
        maximum_clock_error = saturated_gpu.get("server_slot_gpu_skew_max_milliseconds")
    return {
        "gpu_telemetry_available": saturated_gpu.get("gpu_telemetry_defect") is None,
        "saturation_source_is_server_slots": (
            source in {"llama-server-slots-v1", "llama-server-slot-events-v1"}
        ),
        "server_slot_sample_coverage_is_complete": at_least(
            "server_slot_sample_coverage_pct", 100.0
        ),
        "server_slot_measurement_failures_are_zero": (
            isinstance(failure_count, int)
            and not isinstance(failure_count, bool)
            and failure_count == 0
        ),
        "server_slot_clock_binding_at_most_500_ms": (
            isinstance(maximum_clock_error, (int, float))
            and not isinstance(maximum_clock_error, bool)
            and math.isfinite(float(maximum_clock_error))
            and float(maximum_clock_error) <= 500.0
        ),
        "saturated_gpu_sample_count_at_least_30": at_least("sample_count", 30),
        "saturated_gpu_sample_fraction_at_least_60": at_least(
            "sample_fraction_pct", 60.0
        ),
        "saturated_gpu_median_at_least_95": at_least("utilization_median_pct", 95.0),
        "saturated_gpu_p10_at_least_90": at_least("utilization_p10_pct", 90.0),
        "server_slot_occupancy_at_least_90": at_least(
            "server_slot_occupancy_mean_pct", 90.0
        ),
    }


def profile_prompt_work_policy(prompt_order: str) -> str:
    """Name the prompt-work gate without changing historical cold profiles."""

    if not isinstance(prompt_order, str) or not prompt_order:
        raise SpeechNativeProfileError("prompt_order must be a non-empty string")
    if prompt_order in _PREFIX_REUSE_PROMPT_ORDERS:
        return "prefix-reuse-v1"
    return "cold-evaluation-v1"


def profile_agent_kv_policy(
    server_args: Sequence[str],
    *,
    prompt_order: str,
) -> dict[str, object]:
    """Bind prefix probes to the only currently safe AgentLoop KV policy."""

    policy = profile_prompt_work_policy(prompt_order)
    if not isinstance(server_args, Sequence) or isinstance(server_args, (str, bytes)):
        raise SpeechNativeProfileError("server_args must be a string sequence")
    args = list(server_args)
    if not all(isinstance(item, str) for item in args):
        raise SpeechNativeProfileError("server_args must contain only strings")
    if policy != "prefix-reuse-v1":
        return {
            "policy_id": "legacy-server-defined-v1",
            "active_kv_residency": "server-defined",
            "cpu_cold_tier_enabled": "server-defined",
            "host_prompt_state_serialization": "server-defined",
            "per_slot_hbm_cpu_migration_supported": False,
        }

    cache_ram_values: list[str] = []
    for index, item in enumerate(args):
        if item == "--cache-ram":
            if index + 1 >= len(args):
                raise SpeechNativeProfileError(
                    "active-hbm-only prefix policy requires --cache-ram 0"
                )
            cache_ram_values.append(args[index + 1])
        elif item.startswith("--cache-ram="):
            cache_ram_values.append(item.split("=", 1)[1])
    active_hbm_only = (
        "--cache-prompt" in args
        and cache_ram_values == ["0"]
        and "--no-cache-idle-slots" in args
        and "--no-kv-offload" not in args
        and "-nkvo" not in args
    )
    if not active_hbm_only:
        raise SpeechNativeProfileError(
            "active-hbm-only prefix policy requires GPU KV offload, "
            "--cache-prompt, --cache-ram 0, and --no-cache-idle-slots"
        )
    return {
        "policy_id": "active-hbm-only-v1",
        "active_kv_residency": "gpu-hbm",
        "cpu_cold_tier_enabled": False,
        "host_prompt_state_serialization": False,
        "per_slot_hbm_cpu_migration_supported": False,
    }


def profile_prompt_work_eligibility(
    evaluated_work: Mapping[str, object],
    *,
    prompt_order: str,
) -> dict[str, bool]:
    """Apply the ratio direction that matches the registered cache policy."""

    policy = profile_prompt_work_policy(prompt_order)
    ratio = evaluated_work.get("prompt_evaluation_ratio_pct")
    one_token_fraction = evaluated_work.get("one_token_prompt_eval_fraction_pct")
    ratio_is_number = (
        isinstance(ratio, (int, float))
        and not isinstance(ratio, bool)
        and math.isfinite(float(ratio))
    )
    one_token_is_number = (
        isinstance(one_token_fraction, (int, float))
        and not isinstance(one_token_fraction, bool)
        and math.isfinite(float(one_token_fraction))
    )
    result = {
        "prompt_eval_records_match_contacts": (
            evaluated_work.get("prompt_eval_record_count_matches_contacts") is True
        )
    }
    if policy == "prefix-reuse-v1":
        result["prompt_evaluation_ratio_below_90"] = (
            ratio_is_number and float(ratio) < 90.0
        )
    else:
        result["prompt_evaluation_ratio_at_least_90"] = (
            ratio_is_number and float(ratio) >= 90.0
        )
    result["one_token_prompt_eval_fraction_at_most_5"] = (
        one_token_is_number and float(one_token_fraction) <= 5.0
    )
    return result


def _scan_server_slot_events(
    *,
    server_log_path: Path,
    server_log_start_offset: int,
    session_started_at: str,
    slot_count: int,
    expected_contact_count: int,
    server_log_end_offset: int | None = None,
) -> dict[str, object]:
    """Replay llama-server's native slot launch/release events over one window.

    Extracted verbatim from :func:`profile_server_slot_event_gpu_metrics`
    (pure move, no behaviour change) so the same fail-closed lifecycle proof
    can be replayed by a caller that needs the raw event timeline rather than
    the GPU pairing -- notably the model-free finalize-from-disk path, which
    has no GPU sample timeline to pair against but must still prove the run's
    own soundness.

    Every check here fails closed and is entirely independent of the GPU
    sampler: log clock format, monotonicity, per-slot launch/release balance,
    no task straddling the window boundary, and launch/release counts equal to
    ``expected_contact_count``.
    """

    for name, value in (
        ("server_log_start_offset", server_log_start_offset),
        ("slot_count", slot_count),
        ("expected_contact_count", expected_contact_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SpeechNativeProfileError(f"{name} must be a non-negative integer")
    if slot_count <= 0:
        raise SpeechNativeProfileError("slot_count must be a positive integer")
    try:
        session_epoch = datetime.fromisoformat(session_started_at).timestamp()
    except (TypeError, ValueError) as error:
        raise SpeechNativeProfileError(
            "session_started_at is not an ISO-8601 timestamp"
        ) from error
    try:
        log_bytes = Path(server_log_path).read_bytes()
    except OSError as error:
        raise SpeechNativeProfileError(
            f"cannot read profile server log: {error}"
        ) from error
    if server_log_end_offset is None:
        server_log_end_offset = len(log_bytes)
    if (
        isinstance(server_log_end_offset, bool)
        or not isinstance(server_log_end_offset, int)
        or server_log_end_offset < server_log_start_offset
        or server_log_end_offset > len(log_bytes)
    ):
        raise SpeechNativeProfileError("server log end offset is outside the log")
    log_bytes = log_bytes[:server_log_end_offset]
    if server_log_start_offset > len(log_bytes):
        raise SpeechNativeProfileError("server log start offset exceeds the log size")

    active_tasks: dict[int, int] = {}
    start_active_tasks: dict[int, int] | None = None
    event_times: list[float] = []
    event_active_counts: list[int] = []
    launch_count = 0
    release_count = 0
    first_elapsed_seconds: float | None = None
    previous_elapsed_seconds = -1.0
    byte_offset = 0
    for raw_line in log_bytes.splitlines(keepends=True):
        line_end = byte_offset + len(raw_line)
        if byte_offset < server_log_start_offset < line_end:
            raise SpeechNativeProfileError(
                "server log start offset falls inside a log line"
            )
        in_attempt = byte_offset >= server_log_start_offset
        if in_attempt and start_active_tasks is None:
            start_active_tasks = dict(active_tasks)
        clock_match = _SERVER_LOG_CLOCK.match(raw_line)
        launch_match = _SERVER_SLOT_LAUNCH.search(raw_line)
        release_match = _SERVER_SLOT_RELEASE.search(raw_line)
        if launch_match is not None or release_match is not None:
            if clock_match is None:
                raise SpeechNativeProfileError("server slot event lacks a log clock")
            minute, second, millisecond, microsecond = (
                int(part) for part in clock_match.groups()
            )
            if second >= 60 or millisecond >= 1000 or microsecond >= 1000:
                raise SpeechNativeProfileError("server log clock is malformed")
            elapsed_seconds = (
                minute * 60.0
                + second
                + millisecond / 1000.0
                + microsecond / 1_000_000.0
            )
            if elapsed_seconds < previous_elapsed_seconds:
                raise SpeechNativeProfileError("server log clock moved backwards")
            previous_elapsed_seconds = elapsed_seconds
            if first_elapsed_seconds is None:
                first_elapsed_seconds = elapsed_seconds
            if launch_match is not None:
                slot_id, task_id = (int(part) for part in launch_match.groups())
                if slot_id >= slot_count or slot_id in active_tasks:
                    raise SpeechNativeProfileError(
                        "server slot launch lifecycle is unbalanced"
                    )
                active_tasks[slot_id] = task_id
                if in_attempt:
                    launch_count += 1
            else:
                assert release_match is not None
                slot_id, task_id = (int(part) for part in release_match.groups())
                if active_tasks.get(slot_id) != task_id:
                    raise SpeechNativeProfileError(
                        "server slot release lifecycle is unbalanced"
                    )
                del active_tasks[slot_id]
                if in_attempt:
                    release_count += 1
            if in_attempt:
                event_times.append(session_epoch + elapsed_seconds)
                event_active_counts.append(len(active_tasks))
        elif clock_match is not None and first_elapsed_seconds is None:
            minute, second, millisecond, microsecond = (
                int(part) for part in clock_match.groups()
            )
            first_elapsed_seconds = (
                minute * 60.0
                + second
                + millisecond / 1000.0
                + microsecond / 1_000_000.0
            )
        byte_offset = line_end
    if start_active_tasks is None:
        start_active_tasks = dict(active_tasks)
    if (
        start_active_tasks
        or active_tasks
        or launch_count != expected_contact_count
        or release_count != expected_contact_count
    ):
        raise SpeechNativeProfileError(
            "server slot event lifecycle is unbalanced or contact-incomplete"
        )
    if first_elapsed_seconds is None:
        raise SpeechNativeProfileError("server log has no timestamped record")
    return {
        "event_times": event_times,
        "event_active_counts": event_active_counts,
        "launch_count": launch_count,
        "release_count": release_count,
        "first_elapsed_seconds": first_elapsed_seconds,
    }


def profile_server_slot_event_gpu_metrics(
    *,
    server_log_path: Path,
    server_log_start_offset: int,
    session_started_at: str,
    resource_summary: Mapping[str, object],
    slot_count: int,
    expected_contact_count: int,
    server_log_end_offset: int | None = None,
    gpu_timeline_required: bool = False,
) -> dict[str, int | float | str | None]:
    """Pair GPU samples with llama-server's native slot lifecycle events.

    The server writes launch/release events on its own timeline while the GPU
    sampler runs independently. Replaying those events removes the blocking
    ``nvidia-smi -> GET /slots`` dependency and its load-dependent HTTP skew.
    The session receipt's pre-spawn wall timestamp anchors the server's elapsed
    log clock; the first log timestamp is a conservative upper bound on that
    clock-alignment error.

    The slot-event lifecycle checks below (log format, launch/release
    balance, contact-completeness) always run and always fail closed --
    they prove, independently of the GPU sampler, whether the run itself was
    sound.

    GPU *utilization* numbers are a different story. Owner ruling
    ``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md`` S2.1
    demoted them from a scientific-admission criterion to DESCRIPTIVE
    reporting, so by default (``gpu_timeline_required=False``) a GPU sampler
    outage (missing ``nvidia-smi``, a failed first poll, a crashed polling
    thread -- see ``core.resources.NvidiaSmiSampler``, which already degrades
    to ``NOT_AVAILABLE`` plus a reason and never raises) degrades this
    function's GPU-derived fields to ``NOT_AVAILABLE`` plus a
    ``gpu_telemetry_defect`` reason instead of raising -- an otherwise-complete
    run's finalization must never be destroyed by missing GPU telemetry (the
    2026-08-23 E108 incident; ``docs/readiness/
    2026-08-23-e108-attempt-finalization-adjudication.md`` S3).
    ``gpu_timeline_required=True`` restores the previous fail-closed behaviour
    for a caller that treats GPU saturation as a hard ENGINEERING admission
    gate (owner ruling S2.1 keeps the 95/90 median/P10 requirement for
    engineering-baseline acceptance) rather than a scientific descriptive
    receipt field.
    """

    lifecycle = _scan_server_slot_events(
        server_log_path=server_log_path,
        server_log_start_offset=server_log_start_offset,
        session_started_at=session_started_at,
        slot_count=slot_count,
        expected_contact_count=expected_contact_count,
        server_log_end_offset=server_log_end_offset,
    )
    event_times = lifecycle["event_times"]
    event_active_counts = lifecycle["event_active_counts"]
    launch_count = lifecycle["launch_count"]
    release_count = lifecycle["release_count"]
    first_elapsed_seconds = lifecycle["first_elapsed_seconds"]
    assert isinstance(event_times, list)
    assert isinstance(event_active_counts, list)
    assert isinstance(first_elapsed_seconds, float)

    raw_samples = resource_summary.get("request_gpu_samples")
    if raw_samples is not None and not isinstance(raw_samples, list):
        raise SpeechNativeProfileError("request GPU sample timeline is malformed")
    gpu_telemetry_defect: str | None = None
    if not raw_samples:
        if gpu_timeline_required:
            raise SpeechNativeProfileError(
                "GPU telemetry unavailable for the engineering admission gate"
            )
        reason = resource_summary.get("gpu_sampling_reason")
        gpu_telemetry_defect = (
            reason
            if isinstance(reason, str) and reason.strip()
            else "request GPU sample timeline is unavailable"
        )
        raw_samples = []
    minimum_active = max(1, math.ceil(slot_count * 0.90))
    saturated_utilization: list[float] = []
    slot_occupancy: list[float] = []
    for sample in raw_samples:
        if not isinstance(sample, Mapping):
            raise SpeechNativeProfileError("request GPU sample is malformed")
        sampled_at = sample.get("sampled_at_unix_seconds")
        utilization = sample.get("utilization_pct")
        if (
            isinstance(sampled_at, bool)
            or not isinstance(sampled_at, (int, float))
            or not math.isfinite(float(sampled_at))
            or isinstance(utilization, bool)
            or not isinstance(utilization, (int, float))
            or not math.isfinite(float(utilization))
        ):
            raise SpeechNativeProfileError("request GPU sample is malformed")
        event_index = bisect_right(event_times, float(sampled_at)) - 1
        busy_slots = event_active_counts[event_index] if event_index >= 0 else 0
        slot_occupancy.append(100.0 * busy_slots / slot_count)
        if busy_slots >= minimum_active:
            saturated_utilization.append(float(utilization))

    sample_count = len(saturated_utilization)
    if saturated_utilization:
        ordered = sorted(saturated_utilization)
        median: float | str = float(statistics.median(ordered))
        p10: float | str = float(ordered[max(0, math.ceil(0.10 * len(ordered)) - 1)])
    else:
        median = NOT_AVAILABLE
        p10 = NOT_AVAILABLE
    result: dict[str, int | float | str | None] = {
        "saturation_source": "llama-server-slot-events-v1",
        "minimum_active_requests": minimum_active,
        "sample_count": sample_count,
        "sample_fraction_pct": (
            100.0 * sample_count / len(raw_samples) if raw_samples else NOT_AVAILABLE
        ),
        "utilization_median_pct": median,
        "utilization_p10_pct": p10,
        "server_slot_sample_count": len(raw_samples),
        "server_slot_sample_coverage_pct": 100.0 if raw_samples else NOT_AVAILABLE,
        "server_slot_measurement_failure_count": 0,
        "server_slot_clock_alignment_upper_bound_milliseconds": (
            first_elapsed_seconds * 1000.0
        ),
        "server_slot_occupancy_mean_pct": (
            statistics.fmean(slot_occupancy) if slot_occupancy else NOT_AVAILABLE
        ),
        "server_slot_event_count": len(event_times),
        "server_slot_launch_count": launch_count,
        "server_slot_release_count": release_count,
    }
    if gpu_telemetry_defect is not None:
        result["gpu_telemetry_defect"] = gpu_telemetry_defect
    return result


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
                            max_completion_tokens,
                            int(usage.get("completion_tokens", 0)),
                        )
                elif channel == "COST":
                    cost_count += 1
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        raise SpeechNativeProfileError(
            f"cannot verify profile trace usage: {error}"
        ) from error
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
                    envelope.get("payload", {}) if isinstance(envelope, Mapping) else {}
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
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
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
        int(trace_speech_query.get("model_request_count", -1)) != actual_contact_count
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
        raise SpeechNativeProfileError(
            f"cannot read {artifact_name}: {error}"
        ) from error
    if not isinstance(document, dict):
        raise SpeechNativeProfileError(f"{artifact_name} must be a JSON object")
    return document


def _audit_m7_multistate_action_support(
    *,
    attempt_dir: Path,
    flight: Mapping[str, object],
    attempt_record: Mapping[str, object],
    attempt_record_sha256: str,
    flight_receipt_sha256: str,
    decisions_sha256: str,
    trace_sha256: str,
) -> dict[str, object]:
    """Mechanically admit a complete C108 M7 flight before any label read."""

    run_id = str(flight["run_id"])
    attempt_id = str(flight["attempt_id"])
    profile = flight.get("profile")
    decisions_ref = flight.get("decisions")
    if (
        attempt_record.get("run_id") != run_id
        or attempt_record.get("attempt_id") != attempt_id
        or attempt_record.get("state") != "FINALIZED"
        or not isinstance(profile, Mapping)
        or profile.get("matcher_policy_id") != "M7"
        or profile.get("agent_policy_id") != _M7_POLICY_ID
        or profile.get("agent_aggregator_id") != _M7_AGGREGATOR_ID
        or profile.get("mechanism_control_id") != "matched"
        or profile.get("key_representation_id") not in {"K1", "K2"}
        or profile.get("top_k") != 3
        or profile.get("task_count") != 108
        or not isinstance(decisions_ref, Mapping)
        or decisions_ref.get("contains_gold_labels") is not False
    ):
        raise SpeechNativeProfileError(
            "M7 action audit requires the finalized matched C108 multistate cell"
        )
    decisions_name = decisions_ref.get("path")
    if (
        not isinstance(decisions_name, str)
        or Path(decisions_name).name != decisions_name
        or _SHA256.fullmatch(decisions_sha256) is None
        or decisions_ref.get("sha256") != decisions_sha256
    ):
        raise SpeechNativeProfileError(
            "M7 action-audit decisions reference is malformed"
        )
    decisions_path = attempt_dir / decisions_name
    if not decisions_path.is_file() or _sha256_file(decisions_path) != decisions_sha256:
        raise SpeechNativeProfileError("M7 action-audit decisions SHA-256 mismatch")
    try:
        rows = tuple(
            json.loads(line)
            for line in decisions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read M7 action-audit decisions: {error}"
        ) from error
    if len(rows) != 108 or decisions_ref.get("count") != 108:
        raise SpeechNativeProfileError("M7 action-audit decision count is inconsistent")

    expected_packet_sha256: dict[str, str] = {}
    calls_distribution: Counter[int] = Counter()
    action_sensitive_count = 0
    grounded_state_count = 0
    refined_retrieval_count = 0
    verifier_score_count = 0
    tie_contact_count = 0
    contact_count = 0
    branch_action_counts: Counter[str] = Counter()
    for row in rows:
        if not isinstance(row, Mapping):
            raise SpeechNativeProfileError(
                "M7 action-audit decision row is not an object"
            )
        sample_id = row.get("sample_id")
        query_sample_id = row.get("query_sample_id")
        packet_sha256 = row.get("speech_packet_sha256")
        actions = row.get("agent_actions")
        votes = row.get("agent_vote_key_ids")
        steps = row.get("agent_steps")
        calls = row.get("calls")
        if (
            row.get("schema") != "saea-speech-native-decision-v1"
            or not isinstance(sample_id, str)
            or not sample_id
            or sample_id in expected_packet_sha256
            or query_sample_id != sample_id
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
            or row.get("mechanism_control_id") != "matched"
            or row.get("matcher_policy_id") != "M7"
            or row.get("key_representation_id") not in {"K1", "K2"}
            or row.get("parse_failure") is not False
            or row.get("agent_policy_id") != _M7_POLICY_ID
            or row.get("agent_aggregator_id") != _M7_AGGREGATOR_ID
            or row.get("agent_escalated") is not True
            or not isinstance(actions, list)
            or tuple(actions) != _M7_SUCCESS_ACTIONS
            or not isinstance(votes, list)
            or len(votes) != 4
            or not all(vote in _SPEECH_NATIVE_KEY_IDS for vote in votes)
            or row.get("key_id") != votes[0]
            or row.get("verifier_scores") != {}
            or not isinstance(steps, list)
            or len(steps) != 5
        ):
            raise SpeechNativeProfileError(
                "M7 action-audit decision identity is malformed"
            )
        base_fields = {
            "action_id",
            "key_id",
            "top_key_ids",
            "calls",
            "parse_failure",
        }
        if (
            not isinstance(steps[0], Mapping)
            or set(steps[0]) != base_fields
            or steps[0].get("action_id") != "match:speech-only-primary"
            or steps[0].get("key_id") != votes[0]
            or steps[0].get("top_key_ids") != []
            or steps[0].get("calls") != 1
            or steps[0].get("parse_failure") is not False
            or not isinstance(steps[1], Mapping)
            or set(steps[1]) != base_fields
            or steps[1].get("action_id") != "retrieve:speech-only"
            or steps[1].get("calls") != 1
            or steps[1].get("parse_failure") is not False
        ):
            raise SpeechNativeProfileError(
                "M7 action-audit initial stages are malformed"
            )
        initial_top_ids = steps[1].get("top_key_ids")
        if (
            not isinstance(initial_top_ids, list)
            or len(initial_top_ids) != 3
            or len(set(initial_top_ids)) != 3
            or not all(key_id in _SPEECH_NATIVE_KEY_IDS for key_id in initial_top_ids)
            or steps[1].get("key_id") != initial_top_ids[0]
            or row.get("top_key_ids") != initial_top_ids
        ):
            raise SpeechNativeProfileError(
                "M7 action-audit initial retrieval is malformed"
            )
        branch_fields = base_fields | {
            "state_policy_id",
            "grounded_query_state",
            "verifier_scores",
            "causal_parent_ids",
        }
        for branch_offset, state_policy_id in enumerate(_M7_STATE_POLICY_IDS):
            step = steps[branch_offset + 2]
            if (
                not isinstance(step, Mapping)
                or set(step) != branch_fields
                or step.get("action_id") != f"explore:{state_policy_id}"
                or step.get("state_policy_id") != state_policy_id
                or step.get("key_id") != votes[branch_offset + 1]
                or step.get("parse_failure") is not False
                or step.get("causal_parent_ids")
                != ["match:speech-only-primary", "retrieve:speech-only"]
                or step.get("calls") not in {5, 6}
            ):
                raise SpeechNativeProfileError(
                    "M7 action-audit branch identity is malformed"
                )
            branch_top_ids = step.get("top_key_ids")
            state = step.get("grounded_query_state")
            scores = step.get("verifier_scores")
            if (
                not isinstance(branch_top_ids, list)
                or len(branch_top_ids) != 3
                or len(set(branch_top_ids)) != 3
                or not all(
                    key_id in _SPEECH_NATIVE_KEY_IDS for key_id in branch_top_ids
                )
                or step.get("key_id") not in branch_top_ids
                or not isinstance(state, Mapping)
                or set(state)
                != _GROUNDED_SEMANTIC_STATE_FIELDS | {"candidate_key_ids", "evidence"}
                or state.get("candidate_key_ids") != initial_top_ids
                or not isinstance(state.get("evidence"), list)
                or len(state["evidence"]) != 3
                or not isinstance(scores, Mapping)
                or set(scores) != set(branch_top_ids)
            ):
                raise SpeechNativeProfileError(
                    "M7 action-audit branch payload is malformed"
                )
            for key_id, score in scores.items():
                if (
                    not isinstance(score, Mapping)
                    or set(score) != {"compatible", "confidence"}
                    or not isinstance(score.get("compatible"), bool)
                    or isinstance(score.get("confidence"), bool)
                    or not isinstance(score.get("confidence"), (int, float))
                    or not 0.0 <= float(score["confidence"]) <= 100.0
                ):
                    raise SpeechNativeProfileError(
                        "M7 action-audit verifier score is malformed"
                    )
                if key_id not in branch_top_ids:
                    raise SpeechNativeProfileError(
                        "M7 action-audit verifier score key is unbound"
                    )
            grounded_state_count += 1
            refined_retrieval_count += 1
            verifier_score_count += len(scores)
            tie_contact_count += int(step["calls"] == 6)
            branch_action_counts[state_policy_id] += int(step["key_id"] != votes[0])
        expected_calls = sum(int(step["calls"]) for step in steps)
        response_hashes = row.get("response_text_sha256")
        if (
            isinstance(calls, bool)
            or not isinstance(calls, int)
            or calls != expected_calls
            or not 17 <= calls <= 20
            or not isinstance(response_hashes, list)
            or len(response_hashes) != calls
            or not all(
                isinstance(value, str) and _SHA256.fullmatch(value) is not None
                for value in response_hashes
            )
        ):
            raise SpeechNativeProfileError(
                "M7 action-audit contact accounting is malformed"
            )
        expected_packet_sha256[sample_id] = packet_sha256
        action_sensitive_count += int(any(vote != votes[0] for vote in votes[1:]))
        calls_distribution[calls] += 1
        contact_count += calls
    if (
        grounded_state_count != 324
        or refined_retrieval_count != 324
        or verifier_score_count != 972
    ):
        raise SpeechNativeProfileError(
            "M7 action-audit ready-stage counts are incomplete"
        )

    planned_contact_ceiling = profile.get("planned_contact_ceiling")
    actual_usage = attempt_record.get("actual")
    close = flight.get("close")
    cost = close.get("cost") if isinstance(close, Mapping) else None
    if (
        profile.get("actual_contact_count") != contact_count
        or planned_contact_ceiling != 2160
        or not isinstance(actual_usage, Mapping)
        or actual_usage.get("calls") != contact_count
        or not isinstance(cost, Mapping)
        or cost.get("calls_used") != contact_count
    ):
        raise SpeechNativeProfileError(
            "M7 action-audit durable accounting is inconsistent"
        )

    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    if (
        _SHA256.fullmatch(trace_sha256) is None
        or not trace_path.is_file()
        or _sha256_file(trace_path) != trace_sha256
    ):
        raise SpeechNativeProfileError("M7 action-audit trace SHA-256 mismatch")
    expected_queries: dict[str, Mapping[str, str]] = {}
    try:
        with trace_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("channel") != "MODEL_REQUEST":
                    continue
                envelope = record.get("payload")
                payload = (
                    envelope.get("payload") if isinstance(envelope, Mapping) else None
                )
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
                    or query_parts[0].get("sha256") != expected_packet_sha256[sample_id]
                ):
                    continue
                previous = expected_queries.get(sample_id)
                if previous is not None and dict(previous) != query_parts[0]:
                    raise SpeechNativeProfileError(
                        "M7 action-audit trace has conflicting speech-query carriage"
                    )
                expected_queries[sample_id] = query_parts[0]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot inspect M7 action-audit speech-query carriage: {error}"
        ) from error
    if set(expected_queries) != set(expected_packet_sha256):
        raise SpeechNativeProfileError(
            "M7 action-audit trace speech-query carriage is incomplete"
        )
    trace_usage = _trace_usage_summary(trace_path)
    trace_speech_query = _trace_speech_query_summary(
        trace_path, expected_queries=expected_queries
    )
    process_audit_sha256 = flight.get("process_audit_sha256")
    if not isinstance(process_audit_sha256, str):
        raise SpeechNativeProfileError("M7 action-audit process receipt is missing")
    process_audit = _load_pinned_json_object(
        attempt_dir / f"{run_id}.mmproj-audit.json",
        expected_sha256=process_audit_sha256,
        artifact_name="M7 action-audit mmproj process audit",
    )
    if (
        process_audit.get("mmproj_loaded") is not False
        or process_audit.get("mmproj_hit_count") != 0
    ):
        raise SpeechNativeProfileError("M7 action-audit source loaded mmproj")
    server_scan = flight.get("server_log_scan")
    if not isinstance(server_scan, Mapping):
        raise SpeechNativeProfileError("M7 action-audit server scan is missing")
    completion_issues = _profile_completion_issues(
        calls_used=contact_count,
        actual_contact_count=contact_count,
        task_count=108,
        planned_contact_ceiling=2160,
        request_failure_count=0,
        server_scan=server_scan,
        trace_usage=trace_usage,
        trace_speech_query=trace_speech_query,
    )
    if completion_issues:
        raise SpeechNativeProfileError(
            "M7 action-audit completion defects: " + "; ".join(completion_issues)
        )
    return {
        "schema": "saea-speech-native-action-support-audit-v2",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "source_attempt_state": "FINALIZED",
        "effectiveness_read_authorized": True,
        "gold_read": False,
        "decision_count": 108,
        "contact_count": contact_count,
        "valid_speech_query_contact_count": trace_speech_query[
            "valid_speech_query_count"
        ],
        "grounded_state_valid_count": grounded_state_count,
        "refined_retrieval_count": refined_retrieval_count,
        "verifier_score_count": verifier_score_count,
        "tie_contact_count": tie_contact_count,
        "action_sensitive_count": action_sensitive_count,
        "action_sensitive_rate": action_sensitive_count / 108,
        "action_support_threshold": 24,
        "action_support_threshold_met": action_sensitive_count >= 24,
        "branch_non_primary_action_counts": dict(sorted(branch_action_counts.items())),
        "calls_distribution": {
            str(calls): count for calls, count in sorted(calls_distribution.items())
        },
        "source_sha256": {
            "attempt_record": attempt_record_sha256,
            "flight_receipt": flight_receipt_sha256,
            "decisions": decisions_sha256,
            "trace": trace_sha256,
            "process_audit": process_audit_sha256,
        },
    }


def _audit_m8_pairwise_action_support(
    *,
    attempt_dir: Path,
    flight: Mapping[str, object],
    attempt_record: Mapping[str, object],
    attempt_record_sha256: str,
    flight_receipt_sha256: str,
    decisions_sha256: str,
    trace_sha256: str,
) -> dict[str, object]:
    """Admit a complete C108 M8 trajectory without opening split labels."""

    run_id = str(flight["run_id"])
    attempt_id = str(flight["attempt_id"])
    profile = flight.get("profile")
    decisions_ref = flight.get("decisions")
    if (
        attempt_record.get("run_id") != run_id
        or attempt_record.get("attempt_id") != attempt_id
        or attempt_record.get("state") != "FINALIZED"
    ):
        raise SpeechNativeProfileError(
            "M8 action audit requires a finalized durable attempt"
        )
    if (
        not isinstance(profile, Mapping)
        or profile.get("matcher_policy_id") != "M8"
        or profile.get("key_representation_id") != "K1"
        or profile.get("agent_policy_id") != _M8_POLICY_ID
        or profile.get("agent_aggregator_id") != _M8_AGGREGATOR_ID
        or profile.get("mechanism_control_id") != "matched"
        or profile.get("top_k") != 3
        or profile.get("task_count") != 108
        or not isinstance(decisions_ref, Mapping)
        or decisions_ref.get("contains_gold_labels") is not False
    ):
        raise SpeechNativeProfileError(
            "M8 action audit requires the finalized matched C108 pairwise cell"
        )
    decisions_name = decisions_ref.get("path")
    if (
        not isinstance(decisions_name, str)
        or Path(decisions_name).name != decisions_name
        or _SHA256.fullmatch(decisions_sha256) is None
        or decisions_ref.get("sha256") != decisions_sha256
    ):
        raise SpeechNativeProfileError(
            "M8 action-audit decisions reference is malformed"
        )
    decisions_path = attempt_dir / decisions_name
    if not decisions_path.is_file() or _sha256_file(decisions_path) != decisions_sha256:
        raise SpeechNativeProfileError("M8 action-audit decisions SHA-256 mismatch")
    try:
        rows = tuple(
            json.loads(line)
            for line in decisions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read M8 action-audit decisions: {error}"
        ) from error
    if len(rows) != 108 or decisions_ref.get("count") != 108:
        raise SpeechNativeProfileError("M8 action-audit decision count is inconsistent")

    expected_packet_sha256: dict[str, str] = {}
    calls_distribution: Counter[int] = Counter()
    contact_count = 0
    action_sensitive_count = 0
    k1_stable_query_count = 0
    k2_stable_query_count = 0
    four_way_consensus_count = 0
    k1_order_disagreement_count = 0
    k2_order_disagreement_count = 0
    comparison_count = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise SpeechNativeProfileError(
                "M8 action-audit decision row is not an object"
            )
        sample_id = row.get("sample_id")
        query_sample_id = row.get("query_sample_id")
        packet_sha256 = row.get("speech_packet_sha256")
        primary_key_id = row.get("key_id")
        initial_top_ids = row.get("top_key_ids")
        steps = row.get("agent_steps")
        votes = row.get("agent_vote_key_ids")
        actions = row.get("agent_actions")
        if (
            row.get("schema") != "saea-speech-native-decision-v1"
            or not isinstance(sample_id, str)
            or not sample_id
            or sample_id in expected_packet_sha256
            or query_sample_id != sample_id
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
            or row.get("mechanism_control_id") != "matched"
            or row.get("matcher_policy_id") != "M8"
            or row.get("key_representation_id") != "K1"
            or row.get("parse_failure") is not False
            or row.get("agent_policy_id") != _M8_POLICY_ID
            or row.get("agent_aggregator_id") != _M8_AGGREGATOR_ID
            or row.get("agent_escalated") is not True
            or primary_key_id not in _SPEECH_NATIVE_KEY_IDS
            or row.get("verifier_scores") != {}
            or not isinstance(initial_top_ids, list)
            or len(initial_top_ids) != 3
            or len(set(initial_top_ids)) != 3
            or not all(key_id in _SPEECH_NATIVE_KEY_IDS for key_id in initial_top_ids)
            or not isinstance(steps, list)
            or not isinstance(votes, list)
            or not isinstance(actions, list)
        ):
            raise SpeechNativeProfileError(
                "M8 action-audit decision identity is malformed"
            )
        challengers = tuple(
            key_id for key_id in initial_top_ids if key_id != primary_key_id
        )
        if (
            not 2 <= len(challengers) <= 3
            or tuple(actions) != _m8_success_actions(len(challengers))
            or len(steps) != 2 + len(challengers)
            or len(votes) != 1 + 2 * len(challengers)
            or votes[0] != primary_key_id
            or row.get("predicted_value_label") is None
        ):
            raise SpeechNativeProfileError("M8 action-audit trajectory is malformed")
        base_fields = {
            "action_id",
            "key_id",
            "top_key_ids",
            "calls",
            "parse_failure",
        }
        if (
            not isinstance(steps[0], Mapping)
            or set(steps[0]) != base_fields
            or steps[0].get("action_id") != "match:speech-only-primary"
            or steps[0].get("key_id") != primary_key_id
            or steps[0].get("top_key_ids") != []
            or steps[0].get("calls") != 1
            or steps[0].get("parse_failure") is not False
            or not isinstance(steps[1], Mapping)
            or set(steps[1]) != base_fields
            or steps[1].get("action_id") != "retrieve:speech-only"
            or steps[1].get("key_id") != initial_top_ids[0]
            or steps[1].get("top_key_ids") != initial_top_ids
            or steps[1].get("calls") != 1
            or steps[1].get("parse_failure") is not False
        ):
            raise SpeechNativeProfileError(
                "M8 action-audit initial stages are malformed"
            )
        comparison_fields = {
            "action_id",
            "rank",
            "primary_key_id",
            "challenger_key_id",
            "k1_ab_key_id",
            "k1_ba_key_id",
            "k1_stable_key_id",
            "k2_ab_key_id",
            "k2_ba_key_id",
            "k2_stable_key_id",
            "calls",
            "parse_failure",
            "causal_parent_ids",
        }
        row_has_action = False
        row_has_k1 = False
        row_has_k2 = False
        for rank, challenger_key_id in enumerate(challengers, start=1):
            step = steps[rank + 1]
            pair = {primary_key_id, challenger_key_id}
            if (
                not isinstance(step, Mapping)
                or set(step) != comparison_fields
                or step.get("action_id") != f"compare:pairwise-boundary-rank-{rank}"
                or step.get("rank") != rank
                or step.get("primary_key_id") != primary_key_id
                or step.get("challenger_key_id") != challenger_key_id
                or step.get("calls") != 4
                or step.get("parse_failure") is not False
                or step.get("causal_parent_ids")
                != ["match:speech-only-primary", "retrieve:speech-only"]
            ):
                raise SpeechNativeProfileError(
                    "M8 action-audit pairwise identity is malformed"
                )
            pair_votes = tuple(
                step.get(field)
                for field in (
                    "k1_ab_key_id",
                    "k1_ba_key_id",
                    "k2_ab_key_id",
                    "k2_ba_key_id",
                )
            )
            if not all(vote in pair for vote in pair_votes):
                raise SpeechNativeProfileError(
                    "M8 action-audit pairwise vote is unbound"
                )
            k1_stable = (
                challenger_key_id
                if pair_votes[0] == pair_votes[1] == challenger_key_id
                else None
            )
            k2_stable = (
                challenger_key_id
                if pair_votes[2] == pair_votes[3] == challenger_key_id
                else None
            )
            if (
                step.get("k1_stable_key_id") != k1_stable
                or step.get("k2_stable_key_id") != k2_stable
                or votes[1 + 2 * (rank - 1)] != k1_stable
                or votes[2 + 2 * (rank - 1)] != k2_stable
            ):
                raise SpeechNativeProfileError(
                    "M8 action-audit stable support is inconsistent"
                )
            row_has_k1 = row_has_k1 or k1_stable is not None
            row_has_k2 = row_has_k2 or k2_stable is not None
            row_has_action = (
                row_has_action or k1_stable is not None or k2_stable is not None
            )
            if rank == 1:
                four_way_consensus_count += int(
                    all(vote == challenger_key_id for vote in pair_votes)
                )
            k1_order_disagreement_count += int(pair_votes[0] != pair_votes[1])
            k2_order_disagreement_count += int(pair_votes[2] != pair_votes[3])
            comparison_count += 1
        calls = row.get("calls")
        expected_calls = 2 + 4 * len(challengers)
        response_hashes = row.get("response_text_sha256")
        if (
            calls != expected_calls
            or expected_calls not in {10, 14}
            or not isinstance(response_hashes, list)
            or len(response_hashes) != expected_calls
            or not all(
                isinstance(value, str) and _SHA256.fullmatch(value) is not None
                for value in response_hashes
            )
        ):
            raise SpeechNativeProfileError(
                "M8 action-audit contact accounting is malformed"
            )
        expected_packet_sha256[sample_id] = packet_sha256
        calls_distribution[expected_calls] += 1
        contact_count += expected_calls
        action_sensitive_count += int(row_has_action)
        k1_stable_query_count += int(row_has_k1)
        k2_stable_query_count += int(row_has_k2)

    actual_usage = attempt_record.get("actual")
    close = flight.get("close")
    cost = close.get("cost") if isinstance(close, Mapping) else None
    if (
        profile.get("actual_contact_count") != contact_count
        or profile.get("planned_contact_ceiling") != 1512
        or not isinstance(actual_usage, Mapping)
        or actual_usage.get("calls") != contact_count
        or not isinstance(cost, Mapping)
        or cost.get("calls_used") != contact_count
    ):
        raise SpeechNativeProfileError(
            "M8 action-audit durable accounting is inconsistent"
        )

    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    if (
        _SHA256.fullmatch(trace_sha256) is None
        or not trace_path.is_file()
        or _sha256_file(trace_path) != trace_sha256
    ):
        raise SpeechNativeProfileError("M8 action-audit trace SHA-256 mismatch")
    expected_queries: dict[str, Mapping[str, str]] = {}
    try:
        with trace_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("channel") != "MODEL_REQUEST":
                    continue
                envelope = record.get("payload")
                payload = (
                    envelope.get("payload") if isinstance(envelope, Mapping) else None
                )
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
                    or query_parts[0].get("sha256") != expected_packet_sha256[sample_id]
                ):
                    continue
                previous = expected_queries.get(sample_id)
                if previous is not None and dict(previous) != query_parts[0]:
                    raise SpeechNativeProfileError(
                        "M8 action-audit trace has conflicting speech-query carriage"
                    )
                expected_queries[sample_id] = query_parts[0]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot inspect M8 action-audit speech-query carriage: {error}"
        ) from error
    if set(expected_queries) != set(expected_packet_sha256):
        raise SpeechNativeProfileError(
            "M8 action-audit trace speech-query carriage is incomplete"
        )
    trace_usage = _trace_usage_summary(trace_path)
    trace_speech_query = _trace_speech_query_summary(
        trace_path, expected_queries=expected_queries
    )
    process_audit_sha256 = flight.get("process_audit_sha256")
    if not isinstance(process_audit_sha256, str):
        raise SpeechNativeProfileError("M8 action-audit process receipt is missing")
    process_audit = _load_pinned_json_object(
        attempt_dir / f"{run_id}.mmproj-audit.json",
        expected_sha256=process_audit_sha256,
        artifact_name="M8 action-audit mmproj process audit",
    )
    if (
        process_audit.get("mmproj_loaded") is not False
        or process_audit.get("mmproj_hit_count") != 0
    ):
        raise SpeechNativeProfileError("M8 action-audit source loaded mmproj")
    server_scan = flight.get("server_log_scan")
    if not isinstance(server_scan, Mapping):
        raise SpeechNativeProfileError("M8 action-audit server scan is missing")
    completion_issues = _profile_completion_issues(
        calls_used=contact_count,
        actual_contact_count=contact_count,
        task_count=108,
        planned_contact_ceiling=1512,
        request_failure_count=0,
        server_scan=server_scan,
        trace_usage=trace_usage,
        trace_speech_query=trace_speech_query,
    )
    if completion_issues:
        raise SpeechNativeProfileError(
            "M8 action-audit completion defects: " + "; ".join(completion_issues)
        )
    return {
        "schema": "saea-speech-native-pairwise-action-support-audit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "source_attempt_state": "FINALIZED",
        "effectiveness_read_authorized": True,
        "gold_read": False,
        "decision_count": 108,
        "contact_count": contact_count,
        "valid_speech_query_contact_count": trace_speech_query[
            "valid_speech_query_count"
        ],
        "pairwise_comparison_count": comparison_count,
        "action_sensitive_count": action_sensitive_count,
        "k1_stable_non_primary_query_count": k1_stable_query_count,
        "k2_stable_non_primary_query_count": k2_stable_query_count,
        "four_way_consensus_query_count": four_way_consensus_count,
        "k1_order_disagreement_count": k1_order_disagreement_count,
        "k2_order_disagreement_count": k2_order_disagreement_count,
        "action_support_threshold": 24,
        "action_support_threshold_met": k2_stable_query_count >= 24,
        "calls_distribution": {
            str(calls): count for calls, count in sorted(calls_distribution.items())
        },
        "source_sha256": {
            "attempt_record": attempt_record_sha256,
            "flight_receipt": flight_receipt_sha256,
            "decisions": decisions_sha256,
            "trace": trace_sha256,
            "process_audit": process_audit_sha256,
        },
    }


def _audit_m9_factor_graph_action_support(
    *,
    attempt_dir: Path,
    flight: Mapping[str, object],
    attempt_record: Mapping[str, object],
    attempt_record_sha256: str,
    flight_receipt_sha256: str,
    decisions_sha256: str,
    trace_sha256: str,
) -> dict[str, object]:
    """Admit a complete D108 M9 graph trajectory without opening its binding."""

    run_id = str(flight["run_id"])
    attempt_id = str(flight["attempt_id"])
    profile = flight.get("profile")
    decisions_ref = flight.get("decisions")
    if (
        attempt_record.get("run_id") != run_id
        or attempt_record.get("attempt_id") != attempt_id
        or attempt_record.get("state") != "FINALIZED"
    ):
        raise SpeechNativeProfileError(
            "M9 action audit requires a finalized durable attempt"
        )
    if (
        not isinstance(profile, Mapping)
        or profile.get("matcher_policy_id") != "M9"
        or profile.get("key_representation_id") != "K1"
        or profile.get("agent_policy_id") != _M9_POLICY_ID
        or profile.get("agent_aggregator_id") != _M9_AGGREGATOR_ID
        or profile.get("mechanism_control_id") != "matched"
        or profile.get("top_k") != 4
        or profile.get("task_count") != 108
        or not isinstance(decisions_ref, Mapping)
        or decisions_ref.get("contains_gold_labels") is not False
    ):
        raise SpeechNativeProfileError(
            "M9 action audit requires the finalized matched D108 factor-graph cell"
        )

    graph_relpath = profile.get("decision_graph_path")
    graph_sha256 = profile.get("decision_graph_file_sha256")
    graph_id = profile.get("decision_graph_id")
    if (
        not isinstance(graph_relpath, str)
        or not graph_relpath
        or "\\" in graph_relpath
        or Path(graph_relpath).is_absolute()
        or any(part in {"", ".", ".."} for part in Path(graph_relpath).parts)
        or not isinstance(graph_sha256, str)
        or _SHA256.fullmatch(graph_sha256) is None
        or not isinstance(graph_id, str)
        or not graph_id
    ):
        raise SpeechNativeProfileError("M9 action-audit graph reference is malformed")
    graph_path = (REPO_ROOT / graph_relpath).resolve()
    if graph_path == REPO_ROOT.resolve() or not graph_path.is_relative_to(
        REPO_ROOT.resolve()
    ):
        raise SpeechNativeProfileError("M9 action-audit graph escapes the repository")
    audit_cards = tuple(
        KeyCardV1(
            key_id=key_id,
            definition="Gold-free audit placeholder definition.",
            positive_examples=("Gold-free audit placeholder example.",),
            contrastive_boundary=None,
            value_label=f"audit-only-{key_id}",
        ).validate()
        for key_id in _SPEECH_NATIVE_KEY_IDS
    )
    decision_graph = _load_decision_graph(
        graph_path,
        expected_sha256=graph_sha256,
        key_cards=audit_cards,
    )
    if decision_graph.graph_id != graph_id:
        raise SpeechNativeProfileError("M9 action-audit graph id is inconsistent")
    visible_card_by_key = {card.key_id: card for card in audit_cards}

    decisions_name = decisions_ref.get("path")
    if (
        not isinstance(decisions_name, str)
        or Path(decisions_name).name != decisions_name
        or _SHA256.fullmatch(decisions_sha256) is None
        or decisions_ref.get("sha256") != decisions_sha256
    ):
        raise SpeechNativeProfileError(
            "M9 action-audit decisions reference is malformed"
        )
    decisions_path = attempt_dir / decisions_name
    if not decisions_path.is_file() or _sha256_file(decisions_path) != decisions_sha256:
        raise SpeechNativeProfileError("M9 action-audit decisions SHA-256 mismatch")
    try:
        rows = tuple(
            json.loads(line)
            for line in decisions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read M9 action-audit decisions: {error}"
        ) from error
    if len(rows) != 108 or decisions_ref.get("count") != 108:
        raise SpeechNativeProfileError("M9 action-audit decision count is inconsistent")

    expected_packet_sha256: dict[str, str] = {}
    calls_distribution: Counter[int] = Counter()
    contact_count = 0
    factor_rerank_non_primary_count = 0
    boundary_stable_non_primary_count = 0
    action_variable_count = 0
    candidate_expansion_count = 0
    selected_boundary_count = 0
    boundary_order_disagreement_count = 0
    mechanism_failure_count = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise SpeechNativeProfileError(
                "M9 action-audit decision row is not an object"
            )
        sample_id = row.get("sample_id")
        query_sample_id = row.get("query_sample_id")
        packet_sha256 = row.get("speech_packet_sha256")
        response_hashes = row.get("response_text_sha256")
        if (
            row.get("schema") != "saea-speech-native-decision-v1"
            or not isinstance(sample_id, str)
            or not sample_id
            or sample_id in expected_packet_sha256
            or query_sample_id != sample_id
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
            or row.get("mechanism_control_id") != "matched"
            or row.get("key_representation_id") != "K1"
            or row.get("matcher_policy_id") != "M9"
            or row.get("parse_failure") is not False
            or not isinstance(row.get("predicted_value_label"), str)
            or not row.get("predicted_value_label")
            or not isinstance(response_hashes, list)
        ):
            raise SpeechNativeProfileError(
                "M9 action-audit decision identity is malformed"
            )
        trajectory = _parse_m9_factor_graph_trajectory(
            row=row,
            sample_id=sample_id,
            speaker_id="gold-free-audit",
            gold_key_id="gold-not-opened",
            top_k=4,
            visible_card_by_key=visible_card_by_key,
            decision_graph=decision_graph,
        )
        calls = trajectory["total_calls"]
        if (
            row.get("calls") != calls
            or calls not in {3, 4, 6}
            or len(response_hashes) != calls
            or not all(
                isinstance(value, str) and _SHA256.fullmatch(value) is not None
                for value in response_hashes
            )
        ):
            raise SpeechNativeProfileError(
                "M9 action-audit contact accounting is malformed"
            )
        primary = trajectory["primary_key_id"]
        rerank = trajectory["reranked_key_ids"][0]
        boundary = trajectory["boundary_stable_key_id"]
        rerank_changed = rerank != primary
        boundary_changed = boundary is not None and boundary != primary
        expected_packet_sha256[sample_id] = packet_sha256
        calls_distribution[int(calls)] += 1
        contact_count += int(calls)
        factor_rerank_non_primary_count += int(rerank_changed)
        boundary_stable_non_primary_count += int(boundary_changed)
        action_variable_count += int(rerank_changed or boundary_changed)
        candidate_expansion_count += int(
            set(trajectory["expanded_key_ids"])
            != set(trajectory["initial_top_key_ids"])
        )
        selected_boundary_count += int(trajectory["selected_boundary_id"] is not None)
        boundary_order_disagreement_count += int(
            trajectory["boundary_ab_key_id"] is not None
            and trajectory["boundary_ba_key_id"] is not None
            and trajectory["boundary_ab_key_id"] != trajectory["boundary_ba_key_id"]
        )
        mechanism_failure_count += int(bool(trajectory["mechanism_failure"]))

    actual_usage = attempt_record.get("actual")
    close = flight.get("close")
    cost = close.get("cost") if isinstance(close, Mapping) else None
    if (
        profile.get("actual_contact_count") != contact_count
        or profile.get("planned_contact_ceiling") != 648
        or not isinstance(actual_usage, Mapping)
        or actual_usage.get("calls") != contact_count
        or not isinstance(cost, Mapping)
        or cost.get("calls_used") != contact_count
    ):
        raise SpeechNativeProfileError(
            "M9 action-audit durable accounting is inconsistent"
        )

    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    if (
        _SHA256.fullmatch(trace_sha256) is None
        or not trace_path.is_file()
        or _sha256_file(trace_path) != trace_sha256
    ):
        raise SpeechNativeProfileError("M9 action-audit trace SHA-256 mismatch")
    expected_queries: dict[str, Mapping[str, str]] = {}
    try:
        with trace_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("channel") != "MODEL_REQUEST":
                    continue
                envelope = record.get("payload")
                payload = (
                    envelope.get("payload") if isinstance(envelope, Mapping) else None
                )
                if not isinstance(payload, Mapping):
                    continue
                trace_sample_id = payload.get("sample_id")
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
                    not isinstance(trace_sample_id, str)
                    or trace_sample_id not in expected_packet_sha256
                    or len(query_parts) != 1
                    or query_parts[0].get("sha256")
                    != expected_packet_sha256[trace_sample_id]
                ):
                    continue
                previous = expected_queries.get(trace_sample_id)
                if previous is not None and dict(previous) != query_parts[0]:
                    raise SpeechNativeProfileError(
                        "M9 action-audit trace has conflicting speech-query carriage"
                    )
                expected_queries[trace_sample_id] = query_parts[0]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot inspect M9 action-audit speech-query carriage: {error}"
        ) from error
    if set(expected_queries) != set(expected_packet_sha256):
        raise SpeechNativeProfileError(
            "M9 action-audit trace speech-query carriage is incomplete"
        )
    trace_usage = _trace_usage_summary(trace_path)
    trace_speech_query = _trace_speech_query_summary(
        trace_path, expected_queries=expected_queries
    )
    process_audit_sha256 = flight.get("process_audit_sha256")
    if not isinstance(process_audit_sha256, str):
        raise SpeechNativeProfileError("M9 action-audit process receipt is missing")
    process_audit = _load_pinned_json_object(
        attempt_dir / f"{run_id}.mmproj-audit.json",
        expected_sha256=process_audit_sha256,
        artifact_name="M9 action-audit mmproj process audit",
    )
    if (
        process_audit.get("mmproj_loaded") is not False
        or process_audit.get("mmproj_hit_count") != 0
    ):
        raise SpeechNativeProfileError("M9 action-audit source loaded mmproj")
    server_scan = flight.get("server_log_scan")
    if not isinstance(server_scan, Mapping):
        raise SpeechNativeProfileError("M9 action-audit server scan is missing")
    completion_issues = _profile_completion_issues(
        calls_used=contact_count,
        actual_contact_count=contact_count,
        task_count=108,
        planned_contact_ceiling=648,
        request_failure_count=0,
        server_scan=server_scan,
        trace_usage=trace_usage,
        trace_speech_query=trace_speech_query,
    )
    if completion_issues:
        raise SpeechNativeProfileError(
            "M9 action-audit completion defects: " + "; ".join(completion_issues)
        )
    return {
        "schema": "saea-speech-native-factor-graph-action-audit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "source_attempt_state": "FINALIZED",
        "effectiveness_read_authorized": True,
        "gold_read": False,
        "decision_count": 108,
        "contact_count": contact_count,
        "valid_speech_query_contact_count": trace_speech_query[
            "valid_speech_query_count"
        ],
        "decision_graph_id": decision_graph.graph_id,
        "decision_graph_file_sha256": graph_sha256,
        "candidate_expansion_query_count": candidate_expansion_count,
        "selected_boundary_query_count": selected_boundary_count,
        "factor_rerank_non_primary_query_count": factor_rerank_non_primary_count,
        "boundary_stable_non_primary_query_count": boundary_stable_non_primary_count,
        "boundary_order_disagreement_count": boundary_order_disagreement_count,
        "action_variable_query_count": action_variable_count,
        "action_variable_threshold": 27,
        "action_variable_threshold_met": action_variable_count >= 27,
        "mechanism_failure_count": mechanism_failure_count,
        "calls_distribution": {
            str(calls): count for calls, count in sorted(calls_distribution.items())
        },
        "source_sha256": {
            "attempt_record": attempt_record_sha256,
            "flight_receipt": flight_receipt_sha256,
            "decisions": decisions_sha256,
            "trace": trace_sha256,
            "process_audit": process_audit_sha256,
        },
    }


def _audit_m10_candidate_evidence_action_support(
    *,
    attempt_dir: Path,
    flight: Mapping[str, object],
    attempt_record: Mapping[str, object],
    attempt_record_sha256: str,
    flight_receipt_sha256: str,
    decisions_sha256: str,
    trace_sha256: str,
) -> dict[str, object]:
    """Admit a complete M10 trajectory without opening its split binding."""

    run_id = str(flight["run_id"])
    attempt_id = str(flight["attempt_id"])
    profile = flight.get("profile")
    decisions_ref = flight.get("decisions")
    if (
        attempt_record.get("run_id") != run_id
        or attempt_record.get("attempt_id") != attempt_id
        or attempt_record.get("state") != "FINALIZED"
    ):
        raise SpeechNativeProfileError(
            "M10 action audit requires a finalized durable attempt"
        )
    if (
        not isinstance(profile, Mapping)
        or profile.get("matcher_policy_id") != "M10"
        or profile.get("key_representation_id") != "K1"
        or profile.get("agent_policy_id") != _M10_POLICY_ID
        or profile.get("agent_aggregator_id") != _M10_AGGREGATOR_ID
        or profile.get("mechanism_control_id") != "matched"
        or profile.get("top_k") != 4
        or profile.get("task_count") != 108
        or profile.get("planned_contact_ceiling") != 2160
        or not isinstance(decisions_ref, Mapping)
        or decisions_ref.get("contains_gold_labels") is not False
    ):
        raise SpeechNativeProfileError(
            "M10 action audit requires the finalized matched D108 candidate-evidence cell"
        )

    graph_relpath = profile.get("decision_graph_path")
    graph_sha256 = profile.get("decision_graph_file_sha256")
    graph_id = profile.get("decision_graph_id")
    if (
        not isinstance(graph_relpath, str)
        or not graph_relpath
        or "\\" in graph_relpath
        or Path(graph_relpath).is_absolute()
        or any(part in {"", ".", ".."} for part in Path(graph_relpath).parts)
        or not isinstance(graph_sha256, str)
        or _SHA256.fullmatch(graph_sha256) is None
        or not isinstance(graph_id, str)
        or not graph_id
    ):
        raise SpeechNativeProfileError("M10 action-audit graph reference is malformed")
    graph_path = (REPO_ROOT / graph_relpath).resolve()
    if graph_path == REPO_ROOT.resolve() or not graph_path.is_relative_to(
        REPO_ROOT.resolve()
    ):
        raise SpeechNativeProfileError("M10 action-audit graph escapes the repository")
    audit_cards = tuple(
        KeyCardV1(
            key_id=key_id,
            definition="Gold-free audit placeholder definition.",
            positive_examples=("Gold-free audit placeholder example.",),
            contrastive_boundary=None,
            value_label=f"audit-only-{key_id}",
        ).validate()
        for key_id in _SPEECH_NATIVE_KEY_IDS
    )
    decision_graph = _load_decision_graph(
        graph_path,
        expected_sha256=graph_sha256,
        key_cards=audit_cards,
    )
    if decision_graph.graph_id != graph_id:
        raise SpeechNativeProfileError("M10 action-audit graph id is inconsistent")
    visible_card_by_key = {card.key_id: card for card in audit_cards}

    decisions_name = decisions_ref.get("path")
    if (
        not isinstance(decisions_name, str)
        or Path(decisions_name).name != decisions_name
        or _SHA256.fullmatch(decisions_sha256) is None
        or decisions_ref.get("sha256") != decisions_sha256
    ):
        raise SpeechNativeProfileError(
            "M10 action-audit decisions reference is malformed"
        )
    decisions_path = attempt_dir / decisions_name
    if not decisions_path.is_file() or _sha256_file(decisions_path) != decisions_sha256:
        raise SpeechNativeProfileError("M10 action-audit decisions SHA-256 mismatch")
    try:
        rows = tuple(
            json.loads(line)
            for line in decisions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read M10 action-audit decisions: {error}"
        ) from error
    if len(rows) != 108 or decisions_ref.get("count") != 108:
        raise SpeechNativeProfileError(
            "M10 action-audit decision count is inconsistent"
        )

    expected_packet_sha256: dict[str, str] = {}
    calls_distribution: Counter[int] = Counter()
    expanded_size_distribution: Counter[int] = Counter()
    contact_count = 0
    evidence_contact_count = 0
    reconciliation_contact_count = 0
    support_non_primary_count = 0
    dual_non_primary_count = 0
    reconciled_non_primary_count = 0
    action_variable_count = 0
    mechanism_failure_count = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise SpeechNativeProfileError(
                "M10 action-audit decision row is not an object"
            )
        sample_id = row.get("sample_id")
        query_sample_id = row.get("query_sample_id")
        packet_sha256 = row.get("speech_packet_sha256")
        response_hashes = row.get("response_text_sha256")
        if (
            row.get("schema") != "saea-speech-native-decision-v1"
            or not isinstance(sample_id, str)
            or not sample_id
            or sample_id in expected_packet_sha256
            or query_sample_id != sample_id
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
            or row.get("mechanism_control_id") != "matched"
            or row.get("key_representation_id") != "K1"
            or row.get("matcher_policy_id") != "M10"
            or row.get("parse_failure") is not False
            or not isinstance(row.get("predicted_value_label"), str)
            or not row.get("predicted_value_label")
            or not isinstance(response_hashes, list)
        ):
            raise SpeechNativeProfileError(
                "M10 action-audit decision identity is malformed"
            )
        trajectory = _parse_m10_candidate_evidence_trajectory(
            row=row,
            sample_id=sample_id,
            speaker_id="gold-free-audit",
            gold_key_id="gold-not-opened",
            top_k=4,
            visible_card_by_key=visible_card_by_key,
            decision_graph=decision_graph,
        )
        calls = int(trajectory["total_calls"])
        if (
            row.get("calls") != calls
            or not 10 <= calls <= 20
            or len(response_hashes) != calls
            or not all(
                isinstance(value, str) and _SHA256.fullmatch(value) is not None
                for value in response_hashes
            )
        ):
            raise SpeechNativeProfileError(
                "M10 action-audit contact accounting is malformed"
            )
        primary = trajectory["primary_key_id"]
        family_fields = (
            "supported_action_key_ids",
            "dual_evidence_action_key_ids",
            "reconciled_action_key_ids",
        )
        non_primary_sets = [
            {key_id for key_id in trajectory[field] if key_id != primary}
            for field in family_fields
        ]
        expanded_size = len(trajectory["expanded_key_ids"])
        challenger_count = len(
            [key_id for key_id in trajectory["expanded_key_ids"] if key_id != primary]
        )
        expected_packet_sha256[sample_id] = packet_sha256
        calls_distribution[calls] += 1
        expanded_size_distribution[expanded_size] += 1
        contact_count += calls
        evidence_contact_count += 2 * expanded_size
        reconciliation_contact_count += challenger_count
        support_non_primary_count += int(bool(non_primary_sets[0]))
        dual_non_primary_count += int(bool(non_primary_sets[1]))
        reconciled_non_primary_count += int(bool(non_primary_sets[2]))
        action_variable_count += int(any(non_primary_sets))
        mechanism_failure_count += int(bool(trajectory["mechanism_failure"]))

    actual_usage = attempt_record.get("actual")
    close = flight.get("close")
    cost = close.get("cost") if isinstance(close, Mapping) else None
    if (
        profile.get("actual_contact_count") != contact_count
        or not isinstance(actual_usage, Mapping)
        or actual_usage.get("calls") != contact_count
        or not isinstance(cost, Mapping)
        or cost.get("calls_used") != contact_count
    ):
        raise SpeechNativeProfileError(
            "M10 action-audit durable accounting is inconsistent"
        )

    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    if (
        _SHA256.fullmatch(trace_sha256) is None
        or not trace_path.is_file()
        or _sha256_file(trace_path) != trace_sha256
    ):
        raise SpeechNativeProfileError("M10 action-audit trace SHA-256 mismatch")
    expected_queries: dict[str, Mapping[str, str]] = {}
    try:
        with trace_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("channel") != "MODEL_REQUEST":
                    continue
                envelope = record.get("payload")
                payload = (
                    envelope.get("payload") if isinstance(envelope, Mapping) else None
                )
                if not isinstance(payload, Mapping):
                    continue
                trace_sample_id = payload.get("sample_id")
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
                    not isinstance(trace_sample_id, str)
                    or trace_sample_id not in expected_packet_sha256
                    or len(query_parts) != 1
                    or query_parts[0].get("sha256")
                    != expected_packet_sha256[trace_sample_id]
                ):
                    continue
                previous = expected_queries.get(trace_sample_id)
                if previous is not None and dict(previous) != query_parts[0]:
                    raise SpeechNativeProfileError(
                        "M10 action-audit trace has conflicting speech-query carriage"
                    )
                expected_queries[trace_sample_id] = query_parts[0]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot inspect M10 action-audit speech-query carriage: {error}"
        ) from error
    if set(expected_queries) != set(expected_packet_sha256):
        raise SpeechNativeProfileError(
            "M10 action-audit trace speech-query carriage is incomplete"
        )
    trace_usage = _trace_usage_summary(trace_path)
    trace_speech_query = _trace_speech_query_summary(
        trace_path, expected_queries=expected_queries
    )
    process_audit_sha256 = flight.get("process_audit_sha256")
    if not isinstance(process_audit_sha256, str):
        raise SpeechNativeProfileError("M10 action-audit process receipt is missing")
    process_audit = _load_pinned_json_object(
        attempt_dir / f"{run_id}.mmproj-audit.json",
        expected_sha256=process_audit_sha256,
        artifact_name="M10 action-audit mmproj process audit",
    )
    if (
        process_audit.get("mmproj_loaded") is not False
        or process_audit.get("mmproj_hit_count") != 0
    ):
        raise SpeechNativeProfileError("M10 action-audit source loaded mmproj")
    server_scan = flight.get("server_log_scan")
    if not isinstance(server_scan, Mapping):
        raise SpeechNativeProfileError("M10 action-audit server scan is missing")
    completion_issues = _profile_completion_issues(
        calls_used=contact_count,
        actual_contact_count=contact_count,
        task_count=108,
        planned_contact_ceiling=2160,
        request_failure_count=0,
        server_scan=server_scan,
        trace_usage=trace_usage,
        trace_speech_query=trace_speech_query,
    )
    if completion_issues:
        raise SpeechNativeProfileError(
            "M10 action-audit completion defects: " + "; ".join(completion_issues)
        )
    return {
        "schema": "saea-speech-native-candidate-evidence-action-audit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "source_attempt_state": "FINALIZED",
        "effectiveness_read_authorized": True,
        "gold_read": False,
        "decision_count": 108,
        "contact_count": contact_count,
        "valid_speech_query_contact_count": trace_speech_query[
            "valid_speech_query_count"
        ],
        "decision_graph_id": decision_graph.graph_id,
        "decision_graph_file_sha256": graph_sha256,
        "evidence_contact_count": evidence_contact_count,
        "reconciliation_contact_count": reconciliation_contact_count,
        "support_non_primary_query_count": support_non_primary_count,
        "dual_non_primary_query_count": dual_non_primary_count,
        "reconciled_non_primary_query_count": reconciled_non_primary_count,
        "action_variable_query_count": action_variable_count,
        "action_variable_threshold": 24,
        "action_variable_threshold_met": action_variable_count >= 24,
        "mechanism_failure_count": mechanism_failure_count,
        "calls_distribution": {
            str(calls): count for calls, count in sorted(calls_distribution.items())
        },
        "expanded_size_distribution": {
            str(size): count
            for size, count in sorted(expanded_size_distribution.items())
        },
        "source_sha256": {
            "attempt_record": attempt_record_sha256,
            "flight_receipt": flight_receipt_sha256,
            "decisions": decisions_sha256,
            "trace": trace_sha256,
            "process_audit": process_audit_sha256,
        },
    }


def _audit_m11_adaptive_evidence_gap(
    *,
    attempt_dir: Path,
    flight: Mapping[str, object],
    attempt_record: Mapping[str, object],
    attempt_record_sha256: str,
    flight_receipt_sha256: str,
    decisions_sha256: str,
    trace_sha256: str,
) -> dict[str, object]:
    """Admit a batched M11 engineering trajectory without opening labels."""

    run_id = str(flight["run_id"])
    attempt_id = str(flight["attempt_id"])
    profile = flight.get("profile")
    decisions_ref = flight.get("decisions")
    if (
        attempt_record.get("run_id") != run_id
        or attempt_record.get("attempt_id") != attempt_id
        or attempt_record.get("state") != "FINALIZED"
    ):
        raise SpeechNativeProfileError(
            "M11 action audit requires a finalized durable attempt"
        )
    if not isinstance(profile, Mapping):
        raise SpeechNativeProfileError("M11 action-audit profile is missing")
    task_count = profile.get("task_count")
    top_k = profile.get("top_k")
    order_ids = profile.get("key_order_ids")
    if (
        profile.get("matcher_policy_id") != "M11"
        or profile.get("key_representation_id") != "K1"
        or profile.get("agent_policy_id") not in _M11_POLICY_IDS
        or profile.get("agent_aggregator_id") != _M11_AGGREGATOR_ID
        or profile.get("mechanism_control_id") != "matched"
        or isinstance(task_count, bool)
        or not isinstance(task_count, int)
        or task_count <= 0
        or isinstance(top_k, bool)
        or not isinstance(top_k, int)
        or top_k <= 0
        or not isinstance(order_ids, list)
        or not order_ids
        or len(set(order_ids)) != len(order_ids)
        or not all(
            isinstance(order_id, str) and order_id in _ORDER_BUILDERS
            for order_id in order_ids
        )
        or profile.get("contact_ceiling_per_task") != 5
        or profile.get("planned_contact_ceiling") != task_count * 5
        or not isinstance(decisions_ref, Mapping)
        or decisions_ref.get("contains_gold_labels") is not False
    ):
        raise SpeechNativeProfileError(
            "M11 action audit requires one bounded matched adaptive-evidence profile"
        )

    graph_relpath = profile.get("decision_graph_path")
    graph_sha256 = profile.get("decision_graph_file_sha256")
    graph_id = profile.get("decision_graph_id")
    if (
        not isinstance(graph_relpath, str)
        or not graph_relpath
        or "\\" in graph_relpath
        or Path(graph_relpath).is_absolute()
        or any(part in {"", ".", ".."} for part in Path(graph_relpath).parts)
        or not isinstance(graph_sha256, str)
        or _SHA256.fullmatch(graph_sha256) is None
        or not isinstance(graph_id, str)
        or not graph_id
    ):
        raise SpeechNativeProfileError("M11 action-audit graph reference is malformed")
    graph_path = (REPO_ROOT / graph_relpath).resolve()
    if graph_path == REPO_ROOT.resolve() or not graph_path.is_relative_to(
        REPO_ROOT.resolve()
    ):
        raise SpeechNativeProfileError("M11 action-audit graph escapes the repository")
    audit_cards = tuple(
        KeyCardV1(
            key_id=key_id,
            definition="Gold-free audit placeholder definition.",
            positive_examples=("Gold-free audit placeholder example.",),
            contrastive_boundary=None,
            value_label=f"audit-only-{key_id}",
        ).validate()
        for key_id in sorted(_SPEECH_NATIVE_KEY_IDS)
    )
    decision_graph = _load_decision_graph(
        graph_path,
        expected_sha256=graph_sha256,
        key_cards=audit_cards,
    )
    if decision_graph.graph_id != graph_id:
        raise SpeechNativeProfileError("M11 action-audit graph id is inconsistent")
    visible_card_by_key = {card.key_id: card for card in audit_cards}

    decisions_name = decisions_ref.get("path")
    if (
        not isinstance(decisions_name, str)
        or Path(decisions_name).name != decisions_name
        or decisions_ref.get("sha256") != decisions_sha256
        or _SHA256.fullmatch(decisions_sha256) is None
    ):
        raise SpeechNativeProfileError(
            "M11 action-audit decisions reference is malformed"
        )
    decisions_path = attempt_dir / decisions_name
    if not decisions_path.is_file() or _sha256_file(decisions_path) != decisions_sha256:
        raise SpeechNativeProfileError("M11 action-audit decisions SHA-256 mismatch")
    try:
        rows = tuple(
            json.loads(line)
            for line in decisions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read M11 action-audit decisions: {error}"
        ) from error
    if len(rows) != task_count or decisions_ref.get("count") != task_count:
        raise SpeechNativeProfileError(
            "M11 action-audit decision count is inconsistent"
        )

    expected_packet_sha256: dict[str, str] = {}
    sample_ids_by_order: dict[str, set[str]] = {
        str(order_id): set() for order_id in order_ids
    }
    state_by_sample: dict[str, list[tuple[str, str, str | None, str | None]]] = {}
    seen_task_ids: set[str] = set()
    calls_distribution: Counter[int] = Counter()
    contact_count = 0
    action_variable_count = 0
    adaptive_boundary_count = 0
    mechanism_failure_count = 0
    factor_knowledge_event_count = 0
    factor_supply_query_count = 0
    factor_supply_id_reference_count = 0
    factor_selection_query_count = 0
    factor_selection_id_reference_count = 0
    boundary_supply_query_count = 0
    boundary_supply_id_reference_count = 0
    generated_state_external_supply_count = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise SpeechNativeProfileError(
                "M11 action-audit decision row is not an object"
            )
        task_id = row.get("task_id")
        sample_id = row.get("sample_id")
        query_sample_id = row.get("query_sample_id")
        packet_sha256 = row.get("speech_packet_sha256")
        response_hashes = row.get("response_text_sha256")
        if (
            row.get("schema") != "saea-speech-native-decision-v1"
            or not isinstance(task_id, str)
            or task_id in seen_task_ids
            or not isinstance(sample_id, str)
            or not sample_id
            or query_sample_id != sample_id
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
            or row.get("mechanism_control_id") != "matched"
            or row.get("key_representation_id") != "K1"
            or row.get("matcher_policy_id") != "M11"
            or row.get("parse_failure") is not False
            or not isinstance(row.get("predicted_value_label"), str)
            or not row.get("predicted_value_label")
            or not isinstance(response_hashes, list)
        ):
            raise SpeechNativeProfileError(
                "M11 action-audit decision identity is malformed"
            )
        order_id, separator, task_sample_id = task_id.partition(":")
        if (
            separator != ":"
            or order_id not in sample_ids_by_order
            or task_sample_id != sample_id
            or sample_id in sample_ids_by_order[order_id]
        ):
            raise SpeechNativeProfileError(
                "M11 action-audit task/order binding is malformed"
            )
        previous_packet = expected_packet_sha256.get(sample_id)
        if previous_packet is not None and previous_packet != packet_sha256:
            raise SpeechNativeProfileError(
                "M11 action-audit sample has conflicting speech packets"
            )
        trajectory = _parse_m11_adaptive_evidence_gap_trajectory(
            row=row,
            sample_id=task_id,
            speaker_id="gold-free-audit",
            gold_key_id="gold-not-opened",
            top_k=top_k,
            visible_card_by_key=visible_card_by_key,
            decision_graph=decision_graph,
        )
        information_flow = _validated_m11_information_flow(trajectory)
        calls = int(trajectory["total_calls"])
        if (
            row.get("calls") != calls
            or calls not in {3, 5}
            or len(response_hashes) != calls
            or not all(
                isinstance(value, str) and _SHA256.fullmatch(value) is not None
                for value in response_hashes
            )
        ):
            raise SpeechNativeProfileError(
                "M11 action-audit contact accounting is malformed"
            )
        seen_task_ids.add(task_id)
        sample_ids_by_order[order_id].add(sample_id)
        expected_packet_sha256[sample_id] = packet_sha256
        calls_distribution[calls] += 1
        contact_count += calls
        adaptive_boundary_count += int(trajectory["new_boundary_id"] is not None)
        factor_knowledge_event_count += int(bool(trajectory["new_factor_ids"]))
        factor_supply_query_count += int(
            bool(information_flow["candidate_factor_supply_ids"])
        )
        factor_supply_id_reference_count += len(
            information_flow["candidate_factor_supply_ids"]
        )
        factor_selection_query_count += int(
            bool(information_flow["model_selected_factor_ids"])
        )
        factor_selection_id_reference_count += len(
            information_flow["model_selected_factor_ids"]
        )
        boundary_supply_query_count += int(
            bool(information_flow["incremental_boundary_supply_ids"])
        )
        boundary_supply_id_reference_count += len(
            information_flow["incremental_boundary_supply_ids"]
        )
        generated_state_external_supply_count += int(
            bool(information_flow["model_selected_state_is_external_supply"])
        )
        action_variable_count += int(
            trajectory["retrieval_key_id"] != trajectory["primary_key_id"]
            or trajectory["action_key_id"] not in {None, trajectory["primary_key_id"]}
            or trajectory["boundary_stable_key_id"]
            not in {None, trajectory["primary_key_id"]}
        )
        mechanism_failure_count += int(bool(trajectory["mechanism_failure"]))
        state_by_sample.setdefault(sample_id, []).append(
            (
                str(trajectory["primary_key_id"]),
                str(trajectory["retrieval_key_id"]),
                (
                    str(trajectory["action_key_id"])
                    if trajectory["action_key_id"] is not None
                    else None
                ),
                (
                    str(trajectory["boundary_stable_key_id"])
                    if trajectory["boundary_stable_key_id"] is not None
                    else None
                ),
            )
        )
    reference_samples = next(iter(sample_ids_by_order.values()))
    if not reference_samples or any(
        sample_ids != reference_samples for sample_ids in sample_ids_by_order.values()
    ):
        raise SpeechNativeProfileError(
            "M11 action-audit key orders do not cover one sample set"
        )
    order_disagreement_count = sum(
        len(set(states)) > 1 for states in state_by_sample.values()
    )

    actual_usage = attempt_record.get("actual")
    close = flight.get("close")
    cost = close.get("cost") if isinstance(close, Mapping) else None
    if (
        profile.get("actual_contact_count") != contact_count
        or not isinstance(actual_usage, Mapping)
        or actual_usage.get("calls") != contact_count
        or not isinstance(cost, Mapping)
        or cost.get("calls_used") != contact_count
    ):
        raise SpeechNativeProfileError(
            "M11 action-audit durable accounting is inconsistent"
        )

    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    if (
        _SHA256.fullmatch(trace_sha256) is None
        or not trace_path.is_file()
        or _sha256_file(trace_path) != trace_sha256
    ):
        raise SpeechNativeProfileError("M11 action-audit trace SHA-256 mismatch")
    expected_queries: dict[str, Mapping[str, str]] = {}
    try:
        with trace_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("channel") != "MODEL_REQUEST":
                    continue
                envelope = record.get("payload")
                payload = (
                    envelope.get("payload") if isinstance(envelope, Mapping) else None
                )
                if not isinstance(payload, Mapping):
                    continue
                trace_sample_id = payload.get("sample_id")
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
                    not isinstance(trace_sample_id, str)
                    or trace_sample_id not in expected_packet_sha256
                    or len(query_parts) != 1
                    or query_parts[0].get("sha256")
                    != expected_packet_sha256[trace_sample_id]
                ):
                    continue
                previous = expected_queries.get(trace_sample_id)
                if previous is not None and dict(previous) != query_parts[0]:
                    raise SpeechNativeProfileError(
                        "M11 action-audit trace has conflicting speech-query carriage"
                    )
                expected_queries[trace_sample_id] = query_parts[0]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot inspect M11 action-audit speech-query carriage: {error}"
        ) from error
    if set(expected_queries) != set(expected_packet_sha256):
        raise SpeechNativeProfileError(
            "M11 action-audit trace speech-query carriage is incomplete"
        )
    trace_usage = _trace_usage_summary(trace_path)
    trace_speech_query = _trace_speech_query_summary(
        trace_path, expected_queries=expected_queries
    )
    process_audit_sha256 = flight.get("process_audit_sha256")
    if not isinstance(process_audit_sha256, str):
        raise SpeechNativeProfileError("M11 action-audit process receipt is missing")
    process_audit = _load_pinned_json_object(
        attempt_dir / f"{run_id}.mmproj-audit.json",
        expected_sha256=process_audit_sha256,
        artifact_name="M11 action-audit mmproj process audit",
    )
    if (
        process_audit.get("mmproj_loaded") is not False
        or process_audit.get("mmproj_hit_count") != 0
    ):
        raise SpeechNativeProfileError("M11 action-audit source loaded mmproj")
    server_scan = flight.get("server_log_scan")
    if not isinstance(server_scan, Mapping):
        raise SpeechNativeProfileError("M11 action-audit server scan is missing")
    planned_contact_ceiling = task_count * 5
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
            "M11 action-audit completion defects: " + "; ".join(completion_issues)
        )
    engineering_gate_passed = (
        mechanism_failure_count == 0 and generated_state_external_supply_count == 0
    )
    return {
        "schema": "saea-speech-native-adaptive-evidence-gap-audit-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "source_attempt_state": "FINALIZED",
        "effectiveness_read_authorized": engineering_gate_passed,
        "gold_read": False,
        "decision_count": task_count,
        "unique_query_count": len(reference_samples),
        "key_order_count": len(order_ids),
        "key_order_ids": list(order_ids),
        "contact_count": contact_count,
        "valid_speech_query_contact_count": trace_speech_query[
            "valid_speech_query_count"
        ],
        "decision_graph_id": decision_graph.graph_id,
        "decision_graph_file_sha256": graph_sha256,
        "factor_knowledge_query_count": factor_knowledge_event_count,
        "adaptive_boundary_query_count": adaptive_boundary_count,
        "action_variable_query_count": action_variable_count,
        "key_order_disagreement_query_count": order_disagreement_count,
        "mechanism_failure_count": mechanism_failure_count,
        "engineering_gate_passed": engineering_gate_passed,
        "calls_distribution": {
            str(calls): count for calls, count in sorted(calls_distribution.items())
        },
        "information_flow": {
            "schema": _M11_INFORMATION_FLOW_SCHEMA,
            "factor_supply_query_count": factor_supply_query_count,
            "factor_supply_id_reference_count": factor_supply_id_reference_count,
            "factor_selection_query_count": factor_selection_query_count,
            "factor_selection_id_reference_count": (
                factor_selection_id_reference_count
            ),
            "boundary_supply_query_count": boundary_supply_query_count,
            "boundary_supply_id_reference_count": boundary_supply_id_reference_count,
            "generated_state_external_supply_count": (
                generated_state_external_supply_count
            ),
        },
        "source_sha256": {
            "attempt_record": attempt_record_sha256,
            "flight_receipt": flight_receipt_sha256,
            "decisions": decisions_sha256,
            "trace": trace_sha256,
            "process_audit": process_audit_sha256,
        },
    }


def audit_speech_native_action_support(
    *,
    attempt_dir: Path,
    attempt_record_path: Path,
    attempt_record_sha256: str,
    flight_receipt_sha256: str,
    decisions_sha256: str,
    trace_sha256: str,
) -> dict[str, object]:
    """Read action structure without opening a split binding or interpreting gold.

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
    profile = flight.get("profile")
    if isinstance(profile, Mapping) and profile.get("matcher_policy_id") == "M7":
        return _audit_m7_multistate_action_support(
            attempt_dir=attempt_dir,
            flight=flight,
            attempt_record=attempt_record,
            attempt_record_sha256=attempt_record_sha256,
            flight_receipt_sha256=flight_receipt_sha256,
            decisions_sha256=decisions_sha256,
            trace_sha256=trace_sha256,
        )
    if isinstance(profile, Mapping) and profile.get("matcher_policy_id") == "M8":
        return _audit_m8_pairwise_action_support(
            attempt_dir=attempt_dir,
            flight=flight,
            attempt_record=attempt_record,
            attempt_record_sha256=attempt_record_sha256,
            flight_receipt_sha256=flight_receipt_sha256,
            decisions_sha256=decisions_sha256,
            trace_sha256=trace_sha256,
        )
    if isinstance(profile, Mapping) and profile.get("matcher_policy_id") == "M9":
        return _audit_m9_factor_graph_action_support(
            attempt_dir=attempt_dir,
            flight=flight,
            attempt_record=attempt_record,
            attempt_record_sha256=attempt_record_sha256,
            flight_receipt_sha256=flight_receipt_sha256,
            decisions_sha256=decisions_sha256,
            trace_sha256=trace_sha256,
        )
    if isinstance(profile, Mapping) and profile.get("matcher_policy_id") == "M10":
        return _audit_m10_candidate_evidence_action_support(
            attempt_dir=attempt_dir,
            flight=flight,
            attempt_record=attempt_record,
            attempt_record_sha256=attempt_record_sha256,
            flight_receipt_sha256=flight_receipt_sha256,
            decisions_sha256=decisions_sha256,
            trace_sha256=trace_sha256,
        )
    if isinstance(profile, Mapping) and profile.get("matcher_policy_id") == "M11":
        return _audit_m11_adaptive_evidence_gap(
            attempt_dir=attempt_dir,
            flight=flight,
            attempt_record=attempt_record,
            attempt_record_sha256=attempt_record_sha256,
            flight_receipt_sha256=flight_receipt_sha256,
            decisions_sha256=decisions_sha256,
            trace_sha256=trace_sha256,
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
            raise SpeechNativeProfileError(
                "action-audit M6 decision identity is malformed"
            )
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
            raise SpeechNativeProfileError(
                "action-audit M6 action trajectory is malformed"
            )
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
        raise SpeechNativeProfileError(
            "action-audit contact accounting is inconsistent"
        )

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
                payload = (
                    envelope.get("payload") if isinstance(envelope, Mapping) else None
                )
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
                    or query_parts[0].get("sha256") != expected_packet_sha256[sample_id]
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
        raise SpeechNativeProfileError(
            "action-audit trace speech-query carriage is incomplete"
        )
    trace_usage = _trace_usage_summary(trace_path)
    trace_speech_query = _trace_speech_query_summary(
        trace_path, expected_queries=expected_queries
    )

    process_audit_sha256 = flight.get("process_audit_sha256")
    if not isinstance(process_audit_sha256, str):
        raise SpeechNativeProfileError(
            "action-audit process receipt SHA-256 is missing"
        )
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


def _scan_server_log(
    path: Path,
    *,
    start_offset: int = 0,
    end_offset: int | None = None,
) -> dict[str, object]:
    if (
        isinstance(start_offset, bool)
        or not isinstance(start_offset, int)
        or start_offset < 0
    ):
        raise SpeechNativeProfileError(
            "server log start_offset must be a non-negative integer"
        )
    if end_offset is not None and (
        isinstance(end_offset, bool)
        or not isinstance(end_offset, int)
        or end_offset < start_offset
    ):
        raise SpeechNativeProfileError(
            "server log end_offset must be at least start_offset"
        )
    try:
        with path.open("rb") as handle:
            handle.seek(start_offset)
            read_size = None if end_offset is None else end_offset - start_offset
            text = handle.read(read_size).decode("utf-8", "replace").casefold()
    except OSError as error:
        raise SpeechNativeProfileError(
            f"cannot read profile server log: {error}"
        ) from error

    def hits(markers: Sequence[str]) -> list[str]:
        return [marker for marker in markers if marker in text]

    prompt_eval_tokens = [
        int(match.group(1)) for match in _PROMPT_EVAL_TIMING.finditer(text)
    ]
    speech_feature_batches = list(_SPEECH_FEATURE_BATCH.finditer(text))
    if text.count("decoded cross-slot speech feature batch") != len(
        speech_feature_batches
    ):
        raise SpeechNativeProfileError(
            "server log speech feature batch statistics are incomplete"
        )
    speech_feature_batch_slots = [
        int(match.group(1)) for match in speech_feature_batches
    ]
    speech_feature_batch_tokens = [
        int(match.group(2)) for match in speech_feature_batches
    ]
    if any(value <= 0 for value in speech_feature_batch_slots) or any(
        value <= 0 for value in speech_feature_batch_tokens
    ):
        raise SpeechNativeProfileError(
            "server log speech feature batch statistics must be positive"
        )
    draft_matches = list(_SPECULATIVE_DRAFT_TIMING.finditer(text))
    if text.count("draft acceptance") != len(draft_matches):
        raise SpeechNativeProfileError(
            "server log speculative draft statistics are incomplete"
        )
    draft_generated: list[int] = []
    draft_accepted: list[int] = []
    draft_mean_acceptance_lengths: list[float] = []
    for match in draft_matches:
        reported_ratio = float(match.group(1))
        accepted = int(match.group(2))
        generated = int(match.group(3))
        mean_acceptance_length = float(match.group(4))
        if (
            generated <= 0
            or accepted > generated
            or reported_ratio > 1.0
            or mean_acceptance_length < 1.0
            or not math.isclose(
                reported_ratio,
                accepted / generated,
                rel_tol=0.0,
                abs_tol=5.1e-6,
            )
        ):
            raise SpeechNativeProfileError(
                "server log speculative draft statistics are inconsistent"
            )
        draft_generated.append(generated)
        draft_accepted.append(accepted)
        draft_mean_acceptance_lengths.append(mean_acceptance_length)

    draft_generated_total = sum(draft_generated)
    draft_accepted_total = sum(draft_accepted)

    return {
        "oom_marker_hits": hits(_OOM_MARKERS),
        "host_spill_marker_hits": hits(_HOST_SPILL_MARKERS),
        "runaway_marker_hits": hits(_RUNAWAY_MARKERS),
        "mmproj_free_chunk_count": text.count(
            "decoded mmproj-free speech feature chunk"
        ),
        "speech_feature_batch_count": len(speech_feature_batches),
        "speech_feature_batch_slot_count_total": sum(speech_feature_batch_slots),
        "speech_feature_batch_token_count_total": sum(speech_feature_batch_tokens),
        "speech_feature_batch_mean_slots": (
            statistics.fmean(speech_feature_batch_slots)
            if speech_feature_batch_slots
            else NOT_AVAILABLE
        ),
        "prompt_eval_record_count": len(prompt_eval_tokens),
        "prompt_eval_tokens_total": sum(prompt_eval_tokens),
        "prompt_eval_tokens_median": (
            float(statistics.median(prompt_eval_tokens))
            if prompt_eval_tokens
            else NOT_AVAILABLE
        ),
        "one_token_prompt_eval_count": sum(
            token_count == 1 for token_count in prompt_eval_tokens
        ),
        "prompt_cache_skip_count": text.count(
            "prompt is already in the cache, skipping"
        ),
        "speculative_draft_record_count": len(draft_matches),
        "speculative_draft_generated_tokens_total": draft_generated_total,
        "speculative_draft_accepted_tokens_total": draft_accepted_total,
        "speculative_draft_acceptance_ratio_pct": (
            100.0 * draft_accepted_total / draft_generated_total
            if draft_generated_total
            else NOT_AVAILABLE
        ),
        "speculative_mean_acceptance_length_median": (
            float(statistics.median(draft_mean_acceptance_lengths))
            if draft_mean_acceptance_lengths
            else NOT_AVAILABLE
        ),
    }


def profile_evaluated_work_metrics(
    *,
    server_scan: Mapping[str, object],
    declared_prompt_tokens: int,
    completion_tokens: int,
    wall_seconds: float,
    contact_count: int,
) -> dict[str, object]:
    """Report actual llama.cpp prompt work instead of cache-inflated input work."""

    for name, value in (
        ("declared_prompt_tokens", declared_prompt_tokens),
        ("completion_tokens", completion_tokens),
        ("contact_count", contact_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SpeechNativeProfileError(f"{name} must be a non-negative integer")
    if (
        isinstance(wall_seconds, bool)
        or not isinstance(wall_seconds, (int, float))
        or wall_seconds <= 0
    ):
        raise SpeechNativeProfileError("wall_seconds must be a positive number")

    def non_negative_scan_integer(field: str) -> int:
        value = server_scan.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SpeechNativeProfileError(
                f"server log scan {field} must be a non-negative integer"
            )
        return value

    record_count = non_negative_scan_integer("prompt_eval_record_count")
    evaluated_prompt_tokens = non_negative_scan_integer("prompt_eval_tokens_total")
    one_token_count = non_negative_scan_integer("one_token_prompt_eval_count")
    cache_skip_count = non_negative_scan_integer("prompt_cache_skip_count")
    prompt_ratio: float | str = (
        100.0 * evaluated_prompt_tokens / declared_prompt_tokens
        if declared_prompt_tokens
        else NOT_AVAILABLE
    )
    one_token_fraction: float | str = (
        100.0 * one_token_count / contact_count if contact_count else NOT_AVAILABLE
    )
    return {
        "declared_prompt_tokens": declared_prompt_tokens,
        "evaluated_prompt_tokens": evaluated_prompt_tokens,
        "prompt_evaluation_ratio_pct": prompt_ratio,
        "prompt_eval_record_count": record_count,
        "prompt_eval_record_count_matches_contacts": record_count == contact_count,
        "one_token_prompt_eval_count": one_token_count,
        "one_token_prompt_eval_fraction_pct": one_token_fraction,
        "prompt_cache_skip_count": cache_skip_count,
        "actual_evaluated_tokens_per_second": (
            evaluated_prompt_tokens + completion_tokens
        )
        / float(wall_seconds),
    }


def _audit_cuda_graph_moe_compatibility(
    *,
    runtime_receipt: Mapping[str, object],
    session_receipt: Mapping[str, object],
    checkout_commit: str,
    server_log_text: str,
    gguf_metadata: Mapping[str, object],
    expert_tensor_types: Sequence[str],
    mmvq_header_text: str,
    mmvq_source_text: str,
    mmq_source_text: str,
    cmake_cache_text: str,
    cuda_source_text: str,
    server_context_text: str,
    server_common_header_text: str,
    server_common_source_text: str,
) -> dict[str, object]:
    """Bind the current MoE decode width to llama.cpp's CUDA-graph guard.

    This is a static, model-free audit. It deliberately does not infer that a
    live workload used a particular batch width; native slot events remain the
    authority for that dynamic fact. The audit only proves whether a full-slot
    decode batch can use the pinned source's quantized MoE CUDA-graph path and
    whether decoder-ready speech chunks enter that path as a cross-slot batch.
    """

    if runtime_receipt.get("schema") != "saea-runtime-receipt-v3":
        raise SpeechNativeProfileError("engine audit requires runtime receipt v3")
    if runtime_receipt.get("role") != "inference":
        raise SpeechNativeProfileError(
            "engine audit requires an inference runtime receipt"
        )
    if session_receipt.get("schema") != "saea-session-receipt-v2":
        raise SpeechNativeProfileError("engine audit requires session receipt v2")
    if session_receipt.get("role") != "inference":
        raise SpeechNativeProfileError(
            "engine audit requires an inference session receipt"
        )

    llama_cpp = runtime_receipt.get("llama_cpp")
    if not isinstance(llama_cpp, Mapping):
        raise SpeechNativeProfileError("runtime receipt llama_cpp binding is malformed")
    runtime_commit = llama_cpp.get("build_commit")
    if (
        not isinstance(runtime_commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", runtime_commit) is None
    ):
        raise SpeechNativeProfileError("runtime receipt build commit is malformed")
    if checkout_commit != runtime_commit:
        raise SpeechNativeProfileError(
            "llama.cpp checkout commit differs from runtime receipt"
        )
    runtime_binary_sha256 = llama_cpp.get("binary_sha256")
    if (
        not isinstance(runtime_binary_sha256, str)
        or _SHA256.fullmatch(runtime_binary_sha256) is None
        or session_receipt.get("binary_sha256") != runtime_binary_sha256
    ):
        raise SpeechNativeProfileError("session binary differs from runtime receipt")

    def model_bindings(
        document: Mapping[str, object], field: str
    ) -> set[tuple[str, str]]:
        rows = document.get(field)
        if not isinstance(rows, list) or not rows:
            raise SpeechNativeProfileError(f"engine audit {field} is malformed")
        bindings: set[tuple[str, str]] = set()
        for row in rows:
            if not isinstance(row, Mapping):
                raise SpeechNativeProfileError(f"engine audit {field} row is malformed")
            path = row.get("path")
            sha256 = row.get("sha256")
            if (
                not isinstance(path, str)
                or not path
                or not isinstance(sha256, str)
                or _SHA256.fullmatch(sha256) is None
            ):
                raise SpeechNativeProfileError(f"engine audit {field} row is malformed")
            bindings.add((Path(path).name, sha256))
        return bindings

    if model_bindings(runtime_receipt, "gguf_files") != model_bindings(
        session_receipt, "model_files"
    ):
        raise SpeechNativeProfileError(
            "session model files differ from runtime receipt"
        )

    argv = session_receipt.get("argv")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        raise SpeechNativeProfileError("session argv is malformed")
    if "--no-mmproj" not in argv or "--mmproj" in argv:
        raise SpeechNativeProfileError("engine audit session is not mmproj-free")
    slot_count: int | None = None
    for option in ("-np", "--parallel"):
        if option in argv:
            try:
                slot_count = int(argv[argv.index(option) + 1])
            except (ValueError, IndexError) as error:
                raise SpeechNativeProfileError(
                    "session slot count is malformed"
                ) from error
            break
    if slot_count is None or slot_count <= 0:
        raise SpeechNativeProfileError("session argv has no positive slot count")

    arch_match = re.search(r"\bARCHS\s*=\s*(\d+)\b", server_log_text)
    graph_match = re.search(r"\bUSE_GRAPHS\s*=\s*([01])\b", server_log_text)
    gpu_match = re.search(r"CUDA0\s*:\s*([^\n|(]+)", server_log_text)
    if arch_match is None or graph_match is None or gpu_match is None:
        raise SpeechNativeProfileError("server log lacks CUDA architecture evidence")
    cuda_arch = int(arch_match.group(1))
    if cuda_arch < 890:
        raise SpeechNativeProfileError(
            "engine audit currently supports only Ada-or-newer NVIDIA GPUs"
        )
    if graph_match.group(1) != "1":
        raise SpeechNativeProfileError(
            "receipt-bound build does not enable CUDA graphs"
        )

    architecture = gguf_metadata.get("general.architecture")
    if not isinstance(architecture, str) or not architecture.endswith("moe"):
        raise SpeechNativeProfileError("GGUF architecture is not a receipt-bound MoE")
    expert_count = gguf_metadata.get(f"{architecture}.expert_count")
    expert_used_count = gguf_metadata.get(f"{architecture}.expert_used_count")
    if (
        isinstance(expert_count, bool)
        or not isinstance(expert_count, int)
        or expert_count <= 0
        or isinstance(expert_used_count, bool)
        or not isinstance(expert_used_count, int)
        or expert_used_count <= 0
        or expert_used_count > expert_count
    ):
        raise SpeechNativeProfileError("GGUF MoE expert metadata is malformed")

    normalized_types = tuple(sorted(set(expert_tensor_types)))
    if not normalized_types or not all(
        isinstance(tensor_type, str) and tensor_type for tensor_type in normalized_types
    ):
        raise SpeechNativeProfileError("GGUF expert tensor types are malformed")
    quantized_prefixes = ("Q", "IQ", "TQ", "MXFP", "NVFP")
    unquantized_types = tuple(
        tensor_type
        for tensor_type in normalized_types
        if not tensor_type.startswith(quantized_prefixes)
    )

    max_batch_match = re.search(
        r"#define\s+MMVQ_MAX_BATCH_SIZE\s+(\d+)", mmvq_header_text
    )
    if max_batch_match is None:
        raise SpeechNativeProfileError("MMVQ maximum batch size is not source-bound")
    mmvq_max_batch = int(max_batch_match.group(1))
    if mmvq_max_batch <= 0:
        raise SpeechNativeProfileError("MMVQ maximum batch size must be positive")
    if (
        "cc >= GGML_CUDA_CC_ADA_LOVELACE" not in mmvq_source_text
        or "return MMVQ_MAX_BATCH_SIZE" not in mmvq_source_text
    ):
        raise SpeechNativeProfileError("Ada/Blackwell MMVQ source branch is missing")
    legacy_guard_patterns = (
        r"node->op\s*==\s*GGML_OP_MUL_MAT_ID",
        r"!\s*ggml_is_quantized\(node->src\[0\]->type\)",
        r"node->ne\[2\]\s*>\s*mmvq_mmid_max",
        r"use_cuda_graph\s*=\s*false",
    )
    sync_aware_guard_patterns = (
        r"static\s+bool\s+ggml_cuda_mul_mat_id_needs_sync\s*\(",
        r"ggml_cuda_should_use_mmq\s*\(src0->type,\s*cc,\s*src1->ne\[2\],\s*/\*n_experts=\*/src0->ne\[2\]\)",
        r"ggml_cuda_should_use_mmf\s*\(src0->type,\s*cc,\s*WARP_SIZE,\s*src0->ne,\s*src0->nb,\s*src1->ne\[2\],\s*/\*mul_mat_id=\*/true\)",
        r"if\s*\(ggml_cuda_mul_mat_id_needs_sync\(node,\s*cc\)\)",
        r"GGML_ASSERT\s*\(ggml_cuda_mul_mat_id_needs_sync\(dst,\s*cc\)\)",
        r"use_cuda_graph\s*=\s*false",
    )
    legacy_guard = all(
        re.search(pattern, cuda_source_text) for pattern in legacy_guard_patterns
    )
    sync_aware_guard = all(
        re.search(pattern, cuda_source_text) for pattern in sync_aware_guard_patterns
    )
    if not legacy_guard and not sync_aware_guard:
        raise SpeechNativeProfileError(
            "MUL_MAT_ID CUDA graph guard is missing or changed"
        )

    def cmake_bool(name: str) -> bool:
        match = re.search(
            rf"^{re.escape(name)}:[^=\n]+=([^\n]+)$",
            cmake_cache_text,
            flags=re.MULTILINE,
        )
        if match is None or match.group(1) not in {"ON", "OFF"}:
            raise SpeechNativeProfileError(
                f"engine audit CMake binding {name} is missing or malformed"
            )
        return match.group(1) == "ON"

    if not cmake_bool("GGML_CUDA") or not cmake_bool("GGML_CUDA_GRAPHS"):
        raise SpeechNativeProfileError(
            "engine audit build does not enable CUDA and CUDA graphs"
        )
    mmq_forced_off = cmake_bool("GGML_CUDA_FORCE_CUBLAS")
    mmq_types = tuple(
        tensor_type
        for tensor_type in normalized_types
        if re.search(
            rf"case\s+GGML_TYPE_{re.escape(tensor_type)}\s*:",
            mmq_source_text,
        )
    )
    blackwell_mmq_dispatch = (
        "bool ggml_cuda_should_use_mmq" in mmq_source_text
        and re.search(
            r"if\s*\(turing_mma_available\(cc\)\)\s*\{\s*return\s+true\s*;\s*\}",
            mmq_source_text,
        )
        is not None
    )
    sync_free_mmq = (
        sync_aware_guard
        and not unquantized_types
        and not mmq_forced_off
        and tuple(mmq_types) == normalized_types
        and blackwell_mmq_dispatch
    )
    legacy_effective_limit = 0 if unquantized_types else mmvq_max_batch
    full_slot_graph_eligible = (
        sync_free_mmq if sync_aware_guard else slot_count <= legacy_effective_limit
    )
    effective_limit = slot_count if sync_free_mmq else legacy_effective_limit
    exceeds_limit = not full_slot_graph_eligible

    cross_slot_context_contract = all(
        marker in server_context_text
        for marker in (
            "std::vector<pending_speech_feature> pending_speech_features",
            "pack_server_speech_feature_batch(batch_items)",
            "llama_decode(ctx_tgt, speech_batch_view)",
            "decoded cross-slot speech feature batch",
        )
    )
    cross_slot_header_contract = all(
        marker in server_common_header_text
        for marker in (
            "struct server_speech_feature_batch_item",
            "struct server_speech_feature_batch",
            "pack_server_speech_feature_batch",
        )
    )
    cross_slot_packer_patterns = (
        r"packed\.positions\[static_cast<size_t>\(axis\)\s*\*\s*"
        r"packed\.n_tokens\s*\+\s*token_offset\s*\+\s*i\]",
        r"packed\.seq_id_values\[token_offset\s*\+\s*i\]\s*=\s*"
        r"item\.id_slot",
        r"packed\.seq_ids\[i\]\s*=\s*&packed\.seq_id_values\[i\]",
    )
    cross_slot_packer_contract = all(
        re.search(pattern, server_common_source_text)
        for pattern in cross_slot_packer_patterns
    )
    cross_slot_speech_batch = (
        cross_slot_context_contract
        and cross_slot_header_contract
        and cross_slot_packer_contract
    )
    per_slot_immediate_decode = (
        "llama_decode(ctx_tgt, batch)" in server_context_text
        and "decoded mmproj-free speech feature chunk" in server_context_text
    )
    if not cross_slot_speech_batch and not per_slot_immediate_decode:
        raise SpeechNativeProfileError(
            "speech feature decode transport is missing or changed"
        )

    engine_candidate_static_admissible = (
        sync_aware_guard and full_slot_graph_eligible and cross_slot_speech_batch
    )
    batch_event_matches = tuple(
        re.finditer(
            r"decoded cross-slot speech feature batch,\s*"
            r"n_slots\s*=\s*(\d+),\s*n_tokens\s*=\s*(\d+)",
            server_log_text,
        )
    )
    chunk_success_matches = tuple(
        re.finditer(
            r"decoded mmproj-free speech feature chunk in cross-slot batch,\s*"
            r"n_tokens\s*=\s*(\d+)",
            server_log_text,
        )
    )
    if server_log_text.count("decoded cross-slot speech feature batch") != len(
        batch_event_matches
    ):
        raise SpeechNativeProfileError(
            "server log contains malformed cross-slot speech batch evidence"
        )
    if server_log_text.count(
        "decoded mmproj-free speech feature chunk in cross-slot batch"
    ) != len(chunk_success_matches):
        raise SpeechNativeProfileError(
            "server log contains malformed cross-slot speech chunk evidence"
        )
    batch_slot_counts = tuple(int(match.group(1)) for match in batch_event_matches)
    batch_token_counts = tuple(int(match.group(2)) for match in batch_event_matches)
    chunk_token_counts = tuple(int(match.group(1)) for match in chunk_success_matches)
    if any(value <= 0 for value in (*batch_slot_counts, *batch_token_counts)):
        raise SpeechNativeProfileError(
            "server log cross-slot speech batch counts must be positive"
        )
    if any(value <= 0 for value in chunk_token_counts):
        raise SpeechNativeProfileError(
            "server log cross-slot speech chunk token counts must be positive"
        )
    batch_slot_total = sum(batch_slot_counts)
    batch_token_total = sum(batch_token_counts)
    chunk_token_total = sum(chunk_token_counts)
    runtime_evidence = {
        "speech_feature_batch_event_count": len(batch_event_matches),
        "speech_feature_batch_slot_total": batch_slot_total,
        "speech_feature_batch_token_total": batch_token_total,
        "speech_feature_batch_max_slots": max(batch_slot_counts, default=0),
        "speech_feature_chunk_success_count": len(chunk_success_matches),
        "speech_feature_chunk_token_total": chunk_token_total,
        "batch_chunk_count_matches": batch_slot_total == len(chunk_success_matches),
        "batch_chunk_tokens_match": batch_token_total == chunk_token_total,
        "cross_slot_batch_observed": any(count >= 2 for count in batch_slot_counts),
    }
    return {
        "schema": "saea-speech-native-engine-compatibility-audit-v3",
        "runtime": {
            "build_commit": runtime_commit,
            "binary_sha256": runtime_binary_sha256,
            "mmproj_free": True,
        },
        "hardware": {
            "gpu_name": gpu_match.group(1).strip(),
            "cuda_compute_arch": cuda_arch,
            "cuda_graphs_compiled": True,
        },
        "model": {
            "architecture": architecture,
            "expert_count": expert_count,
            "expert_used_count": expert_used_count,
            "expert_weight_tensor_types": list(normalized_types),
            "unquantized_expert_weight_tensor_types": list(unquantized_types),
        },
        "engine": {
            "mmvq_moe_max_batch_size": mmvq_max_batch,
            "effective_moe_graph_batch_limit": effective_limit,
            "audited_graph_decode_width_lower_bound": (
                slot_count if sync_free_mmq else effective_limit
            ),
            "mul_mat_id_graph_guard_present": True,
            "graph_guard_policy": (
                "sync-aware-dispatch-mirror-v2"
                if sync_aware_guard
                else "legacy-mmvq-only-v1"
            ),
            "ada_blackwell_mmvq_branch_present": True,
            "mmq_forced_off": mmq_forced_off,
            "blackwell_mmq_dispatch_present": blackwell_mmq_dispatch,
            "sync_free_mmq_expert_tensor_types": list(mmq_types),
            "speech_feature_transport_policy": (
                "cross-slot-embedding-batch-v1"
                if cross_slot_speech_batch
                else "per-slot-immediate-decode-v1"
            ),
            "speech_feature_axis_major_mrope_pack_present": (
                cross_slot_packer_contract
            ),
            "speech_feature_sequence_ownership_pack_present": (
                cross_slot_packer_contract
            ),
        },
        "profile": {
            "slot_count": slot_count,
            "full_slot_decode_exceeds_graph_limit": exceeds_limit,
            "full_slot_decode_graph_eligible_static": full_slot_graph_eligible,
            "speech_feature_cross_slot_batch_static": cross_slot_speech_batch,
        },
        "runtime_evidence": runtime_evidence,
        "decision": {
            "current_binary_profile_search_closed": (
                exceeds_limit or not cross_slot_speech_batch
            ),
            "engine_candidate_static_admissible": (engine_candidate_static_admissible),
            "live_contact_authorized": False,
            "required_change": (
                "cross-slot speech-feature embedding batch"
                if not cross_slot_speech_batch
                else (
                    "dynamic shape-stability and live GPU admission evidence"
                    if sync_aware_guard and full_slot_graph_eligible
                    else (
                        "receipt-bound engine equivalence improvement"
                        if exceeds_limit
                        else "dynamic shape-stability evidence"
                    )
                )
            ),
        },
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
            handle.write(
                json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            )
    except FileExistsError as error:
        raise SpeechNativeProfileError(
            f"profile artifact already exists: {path}"
        ) from error


def _write_exclusive_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(
                    json.dumps(
                        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    )
                    + "\n"
                )
    except FileExistsError as error:
        raise SpeechNativeProfileError(
            f"profile artifact already exists: {path}"
        ) from error


def _inspect_gguf_moe_metadata(
    path: Path,
) -> tuple[dict[str, object], tuple[str, ...]]:
    """Read only GGUF metadata and expert tensor descriptors, never tensor bytes."""

    try:
        from gguf import GGMLQuantizationType, GGUFReader
    except ImportError as error:
        raise SpeechNativeProfileError(
            "engine audit requires the receipt-pinned llama.cpp gguf Python package"
        ) from error
    try:
        reader = GGUFReader(str(path), "r")
    except Exception as error:
        raise SpeechNativeProfileError(
            f"cannot inspect receipt-bound GGUF: {path}"
        ) from error
    metadata: dict[str, object] = {}
    for key, field in reader.fields.items():
        if key == "general.architecture" or key.endswith(
            (".expert_count", ".expert_used_count")
        ):
            metadata[key] = field.contents()
    expert_types: list[str] = []
    for tensor in reader.tensors:
        if tensor.name.endswith("_exps.weight"):
            try:
                expert_types.append(GGMLQuantizationType(tensor.tensor_type).name)
            except ValueError as error:
                raise SpeechNativeProfileError(
                    f"unknown GGUF expert tensor type: {tensor.tensor_type}"
                ) from error
    return metadata, tuple(expert_types)


def _cli_speech_native_engine_audit(args: argparse.Namespace) -> int:
    """Produce a model-free, receipt-bound MoE/CUDA-graph compatibility audit."""

    runtime_path = Path(args.runtime_receipt)
    session_path = Path(args.session_receipt)
    source_root = Path(args.llama_cpp_root)
    try:
        runtime_receipt = json.loads(runtime_path.read_text(encoding="utf-8"))
        session_receipt = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError("cannot read engine-audit receipts") from error
    if not isinstance(runtime_receipt, Mapping) or not isinstance(
        session_receipt, Mapping
    ):
        raise SpeechNativeProfileError("engine-audit receipts must be JSON objects")

    server_log_value = session_receipt.get("server_log_path")
    argv = session_receipt.get("argv")
    if not isinstance(server_log_value, str) or not isinstance(argv, list):
        raise SpeechNativeProfileError("session receipt lacks engine-audit paths")
    try:
        model_index = argv.index("-m")
        model_path = Path(argv[model_index + 1])
    except (ValueError, IndexError, TypeError) as error:
        raise SpeechNativeProfileError(
            "session receipt has no decoder model path"
        ) from error

    source_paths = {
        "cuda_source": source_root / "ggml/src/ggml-cuda/ggml-cuda.cu",
        "mmq_source": source_root / "ggml/src/ggml-cuda/mmq.cu",
        "mmvq_source": source_root / "ggml/src/ggml-cuda/mmvq.cu",
        "mmvq_header": source_root / "ggml/src/ggml-cuda/mmvq.cuh",
        "server_context": source_root / "tools/server/server-context.cpp",
        "server_common_header": source_root / "tools/server/server-common.h",
        "server_common_source": source_root / "tools/server/server-common.cpp",
    }
    build_paths = {
        "cmake_cache": source_root / "build/CMakeCache.txt",
    }
    try:
        source_text = {
            key: path.read_text(encoding="utf-8") for key, path in source_paths.items()
        }
        build_text = {
            key: path.read_text(encoding="utf-8") for key, path in build_paths.items()
        }
        server_log_text = Path(server_log_value).read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError as error:
        raise SpeechNativeProfileError(
            "cannot read engine-audit source evidence"
        ) from error
    try:
        checkout = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise SpeechNativeProfileError(
            "cannot bind llama.cpp checkout commit"
        ) from error

    gguf_metadata, expert_types = _inspect_gguf_moe_metadata(model_path)
    report = _audit_cuda_graph_moe_compatibility(
        runtime_receipt=runtime_receipt,
        session_receipt=session_receipt,
        checkout_commit=checkout,
        server_log_text=server_log_text,
        gguf_metadata=gguf_metadata,
        expert_tensor_types=expert_types,
        mmvq_header_text=source_text["mmvq_header"],
        mmvq_source_text=source_text["mmvq_source"],
        mmq_source_text=source_text["mmq_source"],
        cmake_cache_text=build_text["cmake_cache"],
        cuda_source_text=source_text["cuda_source"],
        server_context_text=source_text["server_context"],
        server_common_header_text=source_text["server_common_header"],
        server_common_source_text=source_text["server_common_source"],
    )
    report["inputs"] = {
        "runtime_receipt_path": str(runtime_path),
        "runtime_receipt_sha256": _sha256_file(runtime_path),
        "session_receipt_path": str(session_path),
        "session_receipt_sha256": _sha256_file(session_path),
        "server_log_path": server_log_value,
        "server_log_sha256": _sha256_file(Path(server_log_value)),
        "model_path": str(model_path),
        "source_files": {
            key: {"path": str(path), "sha256": _sha256_file(path)}
            for key, path in source_paths.items()
        },
        "build_files": {
            key: {"path": str(path), "sha256": _sha256_file(path)}
            for key, path in build_paths.items()
        },
    }
    output = Path(args.output)
    _write_exclusive_json(output, report)
    print(
        json.dumps(
            {
                "output": str(output),
                "profile": report["profile"],
                "decision": report["decision"],
                "model_contact": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cli_speech_native_prompt_audit(args: argparse.Namespace) -> int:
    """Tokenize every reachable M11 prompt without evaluating the decoder."""

    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    composed = compose(
        repo_root, args.model, args.dataset, args.baseline, args.experiment
    )
    values = composed.values
    if (
        values.get("matcher_policy_id") != "M11"
        or values.get("key_representation_id") != "K1"
        or values.get("matcher_prompt_policy_id") != "speech-native-json-copy-v4"
        or values.get("speech_native_agent_policy_id")
        != "speech-conditioned-adaptive-evidence-gap-v2"
        or values.get("speech_native_agent_aggregator_id")
        != "adaptive-evidence-gap-primary-control-v1"
    ):
        raise SpeechNativeProfileError(
            "prompt audit requires the frozen K1/M11-v2 adaptive evidence profile"
        )
    workers = args.workers
    if (
        isinstance(workers, bool)
        or not isinstance(workers, int)
        or not 1 <= workers <= 64
    ):
        raise SpeechNativeProfileError(
            "prompt-audit workers must be an integer in [1, 64]"
        )
    slot_count = _require_positive_int(values, "profile_slot_count")
    geometry = _profile_geometry(values, slot_count)
    top_k = _require_positive_int(values, "speech_native_top_k")
    request_layout_id = values.get(
        "speech_native_request_layout_id", "legacy-key-speech-v1"
    )
    if request_layout_id not in SPEECH_NATIVE_REQUEST_LAYOUTS:
        raise SpeechNativeProfileError(
            f"unknown speech-native request layout {request_layout_id!r}"
        )
    transport_prompt_order = values.get("prompt_order")
    if not isinstance(transport_prompt_order, str) or not transport_prompt_order:
        raise SpeechNativeProfileError(
            "prompt audit requires a non-empty transport prompt_order"
        )
    raw_order_ids = values.get("profile_key_order_ids")
    if (
        not isinstance(raw_order_ids, list)
        or not raw_order_ids
        or not all(isinstance(order_id, str) for order_id in raw_order_ids)
    ):
        raise SpeechNativeProfileError("prompt audit requires registered key order ids")
    decoding_params = values.get("decoding_params")
    if not isinstance(decoding_params, Mapping):
        raise SpeechNativeProfileError("prompt audit decoding_params are malformed")
    maximum_completion_tokens = decoding_params.get("max_tokens")
    if (
        isinstance(maximum_completion_tokens, bool)
        or not isinstance(maximum_completion_tokens, int)
        or maximum_completion_tokens <= 0
    ):
        raise SpeechNativeProfileError(
            "prompt audit requires a positive max_tokens ceiling"
        )

    dataset_path = repo_root / "configs" / "dataset" / f"{args.dataset}.json"
    gate_view = load_speech_native_engineering_gate(
        dataset_path,
        data_root=data_root(),
        expected_count=_require_positive_int(values, "count"),
        expected_split_name=_require_string(values, "split_name"),
        workers=workers,
    )
    binding_relpath = _require_string(values, "speech_native_binding")
    binding_path = (repo_root / binding_relpath).resolve()
    if binding_path == repo_root.resolve() or not binding_path.is_relative_to(
        repo_root.resolve()
    ):
        raise SpeechNativeProfileError(
            "prompt-audit binding must stay under the repository"
        )
    binding_sha256 = _require_string(values, "speech_native_binding_file_sha256")
    key_cards = _load_key_cards(binding_path, binding_sha256)
    graph_relpath = _require_string(values, "speech_native_decision_graph")
    graph_path = (repo_root / graph_relpath).resolve()
    if graph_path == repo_root.resolve() or not graph_path.is_relative_to(
        repo_root.resolve()
    ):
        raise SpeechNativeProfileError(
            "prompt-audit decision graph must stay under the repository"
        )
    graph_sha256 = _require_string(values, "speech_native_decision_graph_file_sha256")
    decision_graph = _load_decision_graph(
        graph_path, expected_sha256=graph_sha256, key_cards=key_cards
    )

    feature_root = Path(_require_string(values, "speech_feature_root"))
    promotion_path = Path(_require_string(values, "speech_packet_promotion_receipt"))
    promotion_sha256 = _require_string(values, "speech_packet_promotion_receipt_sha256")
    if promotion_path.parent.resolve() != feature_root.resolve():
        raise SpeechNativeProfileError(
            "prompt-audit packet promotion receipt must live at feature root"
        )
    packet_bindings = _load_packet_bindings(
        promotion_path, promotion_sha256, gate_view.samples
    )
    server_env = _server_env(values)
    decoder_sha256 = server_env.get("LLAMA_SPEECH_DECODER_SHA256")
    if not isinstance(decoder_sha256, str) or _SHA256.fullmatch(decoder_sha256) is None:
        raise SpeechNativeProfileError(
            "prompt-audit server profile lacks a decoder SHA-256 binding"
        )
    packets = load_speech_feature_packets(
        feature_root,
        tuple(packet_bindings.values()),
        workers=workers,
        expected_decoder_gguf_sha256=decoder_sha256,
    )
    if len(packets) != len(gate_view.samples):
        raise SpeechNativeProfileError(
            "prompt-audit packet validation count disagrees with runtime view"
        )
    packet_token_counts = {
        packet.packet_id: sum(chunk.n_tokens for chunk in packet.chunks)
        for packet in packets
    }
    maximum_packet_id, maximum_speech_feature_tokens = max(
        packet_token_counts.items(), key=lambda item: (item[1], item[0])
    )
    maximum_packet = next(
        packet for packet in packets if packet.packet_id == maximum_packet_id
    )

    runtime_receipt = load_runtime_receipt(
        resolve_runtime_receipt_path(repo_root, values)
    )
    runtime_root = Path(args.runtime_root)
    session_path = Path(args.session_receipt).resolve()
    session_hash_before = _sha256_file(session_path)
    session = attach_session(
        session_path,
        runtime_receipt=runtime_receipt,
        runtime_root=runtime_root,
    )
    model_root_value = model_materialization_root(values)
    model_root = Path(model_root_value) if model_root_value is not None else None
    model_argv = _model_file_argv(
        data_root(),
        _pinned_model_files(runtime_receipt),
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=model_root,
    )
    _assert_reusable_session_profile(
        session,
        host=args.host,
        port=args.port,
        model_argv=model_argv,
        server_args=_server_args(values),
        server_env=server_env,
    )
    if _sha256_file(session_path) != session_hash_before:
        raise SpeechNativeProfileError(
            "resident session receipt changed during prompt-audit attachment"
        )
    client = _LoopbackPromptAuditClient(
        host=session.host,
        port=session.port,
        timeout_seconds=args.timeout_seconds,
    )
    props = client.get_json("/props")
    media_marker = props.get("media_marker")
    chat_template = props.get("chat_template")
    if (
        not isinstance(media_marker, str)
        or not media_marker
        or not isinstance(chat_template, str)
        or not chat_template
    ):
        raise SpeechNativeProfileError(
            "resident llama.cpp props lack media marker or chat template identity"
        )

    envelopes = tuple(
        _wire_m11_prompt_envelope(
            envelope,
            prompt_order=transport_prompt_order,
        )
        for envelope in _enumerate_m11_prompt_envelopes(
            key_cards=key_cards,
            decision_graph=decision_graph,
            top_k=top_k,
            key_order_ids=tuple(raw_order_ids),
            request_layout_id=request_layout_id,
        )
    )

    def count_one(envelope: Mapping[str, object]) -> tuple[str, int]:
        envelope_id = envelope.get("envelope_id")
        if not isinstance(envelope_id, str):
            raise SpeechNativeProfileError("prompt-audit envelope id is malformed")
        return (
            envelope_id,
            _m11_prompt_text_token_count(
                envelope=envelope,
                media_marker=media_marker,
                post_json=client.post_json,
            ),
        )

    with ThreadPoolExecutor(
        max_workers=min(workers, len(envelopes)),
        thread_name_prefix="saea-m11-prompt-tokenizer",
    ) as pool:
        counts = dict(pool.map(count_one, envelopes))
    if len(counts) != len(envelopes):
        raise SpeechNativeProfileError(
            "prompt-audit tokenizer did not cover every envelope"
        )
    report = _audit_m11_prompt_fit(
        envelopes=envelopes,
        token_count=lambda envelope: counts[str(envelope["envelope_id"])],
        maximum_speech_feature_tokens=maximum_speech_feature_tokens,
        maximum_completion_tokens=maximum_completion_tokens,
        context_tokens_per_slot=geometry["context_tokens_per_slot"],
        special_token_reserve=2,
    )
    report.update(
        {
            "study": "speech-aware-evidence-acquisition",
            "scope": "model-free-check",
            "config_hash": composed.config_hash,
            "binding_path": binding_path.relative_to(repo_root).as_posix(),
            "binding_file_sha256": binding_sha256,
            "decision_graph_id": decision_graph.graph_id,
            "decision_graph_path": graph_path.relative_to(repo_root).as_posix(),
            "decision_graph_file_sha256": graph_sha256,
            "request_layout_id": request_layout_id,
            "transport_prompt_order": transport_prompt_order,
            "packet_promotion_receipt_sha256": promotion_sha256,
            "validated_packet_count": len(packets),
            "maximum_speech_packet": {
                "packet_id": maximum_packet.packet_id,
                "packet_sha256": maximum_packet.packet_sha256,
                "feature_tokens": maximum_speech_feature_tokens,
            },
            "runtime": {
                "session_receipt_path": str(session_path),
                "session_receipt_sha256": session_hash_before,
                "server_pid": session.pid,
                "server_argv_sha256": _canonical_sha256(session.argv),
                "mmproj_loaded": False,
                "decoder_sha256": decoder_sha256,
            },
            "tokenizer": {
                "media_marker": media_marker,
                "chat_template_sha256": hashlib.sha256(
                    chat_template.encode("utf-8")
                ).hexdigest(),
                "request_counts": dict(sorted(client.request_counts.items())),
                "parallel_workers": workers,
                "decoder_evaluations": 0,
                "generated_tokens": 0,
            },
            "new_model_contact_authorized": False,
        }
    )
    output = Path(args.output)
    _write_exclusive_json(output, report)
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": _sha256_file(output),
                "envelope_count": report["envelope_count"],
                "maximum_prompt_tokens_upper_bound": report[
                    "maximum_prompt_tokens_upper_bound"
                ],
                "context_margin_tokens": report["context_margin_tokens"],
                "maximum_prompt_fits_one_slot": report["maximum_prompt_fits_one_slot"],
                "model_contact": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cli_speech_native_profile(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    root = data_root()
    lock = load_lock(umbrella_lock_path())
    composed = compose(
        repo_root, args.model, args.dataset, args.baseline, args.experiment
    )
    values = composed.values
    matcher_policy_id = _require_string(values, "matcher_policy_id")
    transport_prompt_order = _require_string(values, "prompt_order")
    source_session_receipt = getattr(args, "session_receipt", None)
    (
        prompt_fit_path,
        prompt_fit_expected_sha256,
        prompt_fit_maximum_completion_tokens,
    ) = _resolve_m11_prompt_fit_config(
        repo_root=repo_root,
        values=values,
        matcher_policy_id=matcher_policy_id,
        session_receipt=source_session_receipt,
    )
    plan = ExecutionPlan(
        **json.loads(Path(args.plan).read_text(encoding="utf-8"))
    ).validate()
    split_ids, split_hash, split_role = load_split(
        repo_root, _require_string(values, "split_name"), lock, root
    )
    expected_protocol = protocol_hash(
        composed.config_hash, str(values["arm"]), split_hash
    )
    if (
        plan.split_identity_hash != split_hash
        or plan.split_role != split_role
        or plan.protocol_hash != expected_protocol
        or plan.carrier_lock_key != values.get("carrier_lock_key")
    ):
        raise SpeechNativeProfileError(
            "execution plan does not match the composed profile"
        )
    run_dir = Path(args.run_dir).resolve()
    if run_dir.name != plan.attempt_id:
        raise SpeechNativeProfileError(
            "profile run_dir basename must equal plan.attempt_id"
        )
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
        raise SpeechNativeProfileError(
            "runtime view ids do not match the verified split"
        )
    binding_relpath = _require_string(values, "speech_native_binding")
    binding_path = repo_root / binding_relpath
    if (
        binding_path.resolve() == repo_root.resolve()
        or not binding_path.resolve().is_relative_to(repo_root.resolve())
    ):
        raise SpeechNativeProfileError(
            "speech-native binding must stay under the repository"
        )
    binding_sha256 = _require_string(values, "speech_native_binding_file_sha256")
    binding_document = _load_binding_document(binding_path, binding_sha256)
    key_cards = _load_key_cards(binding_path, binding_sha256)
    packet_receipt_path = Path(
        _require_string(values, "speech_packet_promotion_receipt")
    )
    packet_receipt_sha256 = _require_string(
        values, "speech_packet_promotion_receipt_sha256"
    )
    packet_bindings = _load_packet_bindings(
        packet_receipt_path,
        packet_receipt_sha256,
        gate_view.samples,
    )
    key_representation_id = _require_string(values, "key_representation_id")
    audio_key_bindings = None
    if key_representation_id in {"K3", "K4"}:
        audio_key_bindings = _build_audio_key_bindings(
            binding_document,
            _load_packet_index(
                packet_receipt_path,
                packet_receipt_sha256,
            ),
            key_cards,
        )
    feature_root = Path(_require_string(values, "speech_feature_root"))
    if packet_receipt_path.parent.resolve() != feature_root.resolve():
        raise SpeechNativeProfileError(
            "packet promotion receipt must live at speech_feature_root"
        )
    raw_order_ids = values.get("profile_key_order_ids")
    if (
        not isinstance(raw_order_ids, list)
        or not raw_order_ids
        or not all(isinstance(item, str) for item in raw_order_ids)
    ):
        raise SpeechNativeProfileError(
            "profile_key_order_ids must be a non-empty string list"
        )
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
    request_layout_id = values.get(
        "speech_native_request_layout_id", "legacy-key-speech-v1"
    )
    if request_layout_id not in SPEECH_NATIVE_REQUEST_LAYOUTS:
        raise SpeechNativeProfileError(
            f"unknown speech-native request layout {request_layout_id!r}"
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
    matcher_policy_id = _require_string(values, "matcher_policy_id")
    reader_policy_id, reader_contract = _m11_reader_contract_from_values(
        values, matcher_policy_id
    )
    decision_graph = None
    decision_graph_path: Path | None = None
    decision_graph_file_sha256: str | None = None
    if matcher_policy_id in {"M9", "M10", "M11"}:
        graph_relpath = _require_string(values, "speech_native_decision_graph")
        decision_graph_path = (repo_root / graph_relpath).resolve()
        if (
            decision_graph_path == repo_root.resolve()
            or not decision_graph_path.is_relative_to(repo_root.resolve())
        ):
            raise SpeechNativeProfileError(
                "speech-native decision graph must stay under the repository"
            )
        decision_graph_file_sha256 = _require_string(
            values, "speech_native_decision_graph_file_sha256"
        )
        decision_graph = _load_decision_graph(
            decision_graph_path,
            expected_sha256=decision_graph_file_sha256,
            key_cards=key_cards,
        )
    elif any(
        key in values
        for key in (
            "speech_native_decision_graph",
            "speech_native_decision_graph_file_sha256",
        )
    ):
        raise SpeechNativeProfileError(
            "decision graph configuration may only enter an M9/M10/M11 profile"
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
    agent_executor_id = resolve_speech_native_agent_executor_id(values)
    tasks = build_profile_tasks(
        samples=gate_view.samples,
        packet_bindings=packet_bindings,
        key_cards=key_cards,
        order_ids=raw_order_ids,
        decoding_params=values.get("decoding_params", {}),
        key_representation_id=key_representation_id,
        matcher_policy_id=matcher_policy_id,
        top_k=top_k,
        prompt_policy_id=prompt_policy_id,
        request_layout_id=request_layout_id,
        verifier_policy_id=verifier_policy_id,
        audio_key_bindings=audio_key_bindings,
        decision_graph=decision_graph,
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

    knowledge_snapshot = None
    if agent_executor_id == "openjiuwen-workflow-v1":
        if result_mode != "predictions":
            raise SpeechNativeProfileError(
                "openJiuwen speech-native matching requires predictions result mode"
            )
        openjiuwen_contact_ceiling = {"M1": 1, "M2": 2}.get(matcher_policy_id)
        if openjiuwen_contact_ceiling is None or (
            contact_ceiling != openjiuwen_contact_ceiling
        ):
            raise SpeechNativeProfileError(
                "the current openJiuwen M1/M2 vertical slice requires its registered "
                "one/two-contact ceiling"
            )
        knowledge_revision = binding_document.get("knowledge_revision")
        if knowledge_revision is not None and not isinstance(
            knowledge_revision, Mapping
        ):
            raise SpeechNativeProfileError(
                "speech-native binding knowledge_revision must be an object"
            )
        knowledge_seed = (
            knowledge_revision.get("seed")
            if isinstance(knowledge_revision, Mapping)
            else binding_document.get("seed")
        )
        knowledge_policy_id = (
            knowledge_revision.get("policy_id")
            if isinstance(knowledge_revision, Mapping)
            else SPEECH_NATIVE_KNOWLEDGE_POLICY_ID
        )
        if isinstance(knowledge_seed, bool) or not isinstance(knowledge_seed, int):
            raise SpeechNativeProfileError(
                "speech-native binding must provide an integer TRAIN knowledge seed"
            )
        if not isinstance(knowledge_policy_id, str) or not knowledge_policy_id:
            raise SpeechNativeProfileError(
                "speech-native binding must provide a TRAIN knowledge policy id"
            )
        query_sample_ids = tuple(task.sample.sample_id for task in tasks)
        if len(set(query_sample_ids)) != len(query_sample_ids):
            raise SpeechNativeProfileError(
                "the current openJiuwen M1 vertical slice requires one key order per query"
            )
        train_material = load_slurp_train_material(
            lock,
            root,
            media_validation_workers=_require_positive_int(
                values, "profile_validation_workers"
            ),
        )
        construction_material = partition_speech_native_train_knowledge(
            train_material,
            use_sample_ids=query_sample_ids,
        )
        knowledge_snapshot = build_speech_native_knowledge_snapshot(
            construction_material,
            seed=knowledge_seed,
            policy_id=knowledge_policy_id,
            expected_scenarios=tuple(card.value_label for card in key_cards),
        )
        validate_openjiuwen_speech_native_match_tasks(tasks, knowledge_snapshot)

    runtime_receipt = load_runtime_receipt(
        resolve_runtime_receipt_path(repo_root, values)
    )
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
        d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(values),
        d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(values),
    )
    session_receipt_path = run_dir / f"{plan.run_id}.session-receipt.json"
    stop_receipt_path = run_dir / f"{plan.run_id}.session-stop-receipt.json"
    audit_path = run_dir / f"{plan.run_id}.mmproj-audit.json"
    attempt_server_log_path = run_dir / f"{plan.run_id}.server.log"
    flight_receipt_path = run_dir / "flight-receipt.json"
    decisions_path = run_dir / "decisions.jsonl"
    runtime_root = Path(args.runtime_root)
    server_args = _server_args(values)
    agent_kv_policy = profile_agent_kv_policy(
        server_args,
        prompt_order=transport_prompt_order,
    )
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
    prompt_fit_document: Mapping[str, object] | None = None
    if matcher_policy_id == "M11":
        if (
            prompt_fit_path is None
            or prompt_fit_expected_sha256 is None
            or prompt_fit_maximum_completion_tokens is None
            or decision_graph is None
            or decision_graph_file_sha256 is None
            or source_session_receipt_sha256 is None
        ):
            raise SpeechNativeProfileError(
                "M11 prompt-fit gate lacks a required runtime binding"
            )
        prompt_fit_document = _validate_m11_prompt_fit_for_profile(
            path=prompt_fit_path,
            expected_sha256=prompt_fit_expected_sha256,
            binding_sha256=binding_sha256,
            decision_graph=decision_graph,
            graph_sha256=decision_graph_file_sha256,
            packet_promotion_sha256=packet_receipt_sha256,
            session_receipt_sha256=source_session_receipt_sha256,
            server_env=server_env,
            key_cards=key_cards,
            key_order_ids=tuple(raw_order_ids),
            top_k=top_k,
            packet_count=len(gate_view.samples),
            context_tokens_per_slot=geometry["context_tokens_per_slot"],
            maximum_completion_tokens=prompt_fit_maximum_completion_tokens,
            request_layout_id=request_layout_id,
            transport_prompt_order=transport_prompt_order,
        )
    client: FrozenCoreClient | None = None
    close_summary: dict[str, object] | None = None
    sampler = resolve_resource_sampler()
    resource_summary: Mapping[str, object] = {}
    outcomes = ()
    failure: BaseException | None = None
    request_started = False
    try:
        _write_inference_process_audit(session, audit_path)
        transport = build_configured_transport(
            values,
            root,
            repo_root=repo_root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=Path(args.runtime_root),
        )
        binding = build_payload_binding(
            carrier_lock_key=plan.carrier_lock_key,
            samples=gate_view.samples,
            data_root=root,
            carrier_root=asset_dir(lock, plan.carrier_lock_key, root),
            # DERIVED-MEDIA CONFINEMENT: this profile is what packet
            # preprocessing runs through, and a derived media population (the
            # ``@ts2`` runtime views) names its files under its own
            # ``derived/<variant>/`` root rather than under the carrier's. The
            # fragment declares that root; without it here every such row was
            # refused at payload time with no request ever reaching the wire.
            derived_media_roots=declared_derived_media_roots(values, root),
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
        if agent_executor_id == "openjiuwen-workflow-v1":
            assert knowledge_snapshot is not None
            outcomes = run_openjiuwen_speech_native_match_tasks(
                data_root=root,
                plan=plan,
                core_client=client,
                tasks=tasks,
                knowledge_snapshot=knowledge_snapshot,
                slot_count=slot_count,
                queue_depth=slot_count * queue_multiplier,
                trace_flusher=client.flush_trace_buffer,
            )
        else:
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

    attempt = AttemptStore(Path(root) / "attempts").handle(
        plan.run_id, str(plan.attempt_id)
    )
    attempt_exists = attempt.path.is_file()
    gpu_seconds = resource_summary.get("gpu_seconds")
    if (
        attempt_exists
        and isinstance(gpu_seconds, (int, float))
        and not isinstance(gpu_seconds, bool)
    ):
        attempt.record_gpu_seconds(float(gpu_seconds))
    try:
        server_log_end_offset = active_server_log_path.stat().st_size
    except OSError as error:
        raise SpeechNativeProfileError(
            f"cannot stat completed speech-native server log: {error}"
        ) from error
    server_scan = _scan_server_log(
        active_server_log_path,
        start_offset=server_log_start_offset,
        end_offset=server_log_end_offset,
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
                    "speech_packet_sha256": task_by_id[
                        outcome.task_id
                    ].query_descriptor["sha256"],
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
                    "agent_vote_key_ids": list(outcome.decision.agent_vote_key_ids),
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
            "decision_graph_id": (
                decision_graph.graph_id if decision_graph is not None else None
            ),
            "decision_graph_path": (
                decision_graph_path.relative_to(repo_root.resolve()).as_posix()
                if decision_graph_path is not None
                else None
            ),
            "decision_graph_file_sha256": decision_graph_file_sha256,
            "prompt_fit_receipt_path": (
                prompt_fit_path.relative_to(repo_root.resolve()).as_posix()
                if prompt_fit_path is not None
                else None
            ),
            "prompt_fit_receipt_sha256": prompt_fit_expected_sha256,
            "prompt_fit_maximum_prompt_tokens_upper_bound": (
                prompt_fit_document.get("maximum_prompt_tokens_upper_bound")
                if prompt_fit_document is not None
                else None
            ),
            "prompt_fit_context_margin_tokens": (
                prompt_fit_document.get("context_margin_tokens")
                if prompt_fit_document is not None
                else None
            ),
            "matcher_prompt_policy_id": prompt_policy_id,
            "transport_prompt_order": transport_prompt_order,
            "prompt_work_policy": profile_prompt_work_policy(transport_prompt_order),
            "agent_kv_policy": agent_kv_policy,
            "request_layout_id": request_layout_id,
            "matcher_verifier_policy_id": verifier_policy_id,
            "agent_policy_id": agent_policy_id,
            "agent_aggregator_id": agent_aggregator_id,
            "agent_executor_id": agent_executor_id,
            "knowledge_snapshot_sha256": (
                knowledge_snapshot.content_hash()
                if knowledge_snapshot is not None
                else None
            ),
            "knowledge_source_sample_count": (
                len(knowledge_snapshot.source_sample_ids)
                if knowledge_snapshot is not None
                else None
            ),
            "speech_native_training_free_reader_policy_id": reader_policy_id,
            "speech_native_training_free_reader_contract": reader_contract,
            "dispatch_granularity": dispatch_granularity,
            "mechanism_control_id": mechanism_control_id,
            "query_mapping_sha256": _canonical_sha256(
                {
                    (
                        task.scoring_sample_id or task.sample.sample_id
                    ): task.sample.sample_id
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
            "server_log_end_offset": server_log_end_offset,
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
        "request_failures": []
        if failure is None
        else [f"{type(failure).__name__}: {failure}"],
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
            evaluated_work = profile_evaluated_work_metrics(
                server_scan=server_scan,
                declared_prompt_tokens=int(cost.get("prompt_tokens_total", 0)),
                completion_tokens=int(cost.get("completion_tokens_total", 0)),
                wall_seconds=float(timing["request_window_seconds"]),
                contact_count=actual_contact_count,
            )
            receipt["evaluated_work"] = evaluated_work
            saturated_gpu = profile_server_slot_event_gpu_metrics(
                server_log_path=active_server_log_path,
                server_log_start_offset=server_log_start_offset,
                server_log_end_offset=server_log_end_offset,
                session_started_at=session.started_at,
                resource_summary=resource_summary,
                slot_count=slot_count,
                expected_contact_count=actual_contact_count,
            )
            receipt["saturated_gpu"] = saturated_gpu
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
                **profile_gpu_eligibility(saturated_gpu),
                **profile_prompt_work_eligibility(
                    evaluated_work,
                    prompt_order=transport_prompt_order,
                ),
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
        raise SpeechNativeProfileError(
            "profile completion checks failed; see flight receipt"
        )
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


FINALIZE_FROM_DISK_MODE_ID = "rebuilt-from-disk-v1"
_FINALIZE_FROM_DISK_UNREAD_CHANNELS = ("MODEL_RESPONSE", "decisions.jsonl rows")
_FINALIZE_FROM_DISK_PROFILE_IDENTITY_KEYS = (
    "agent_aggregator_id",
    "agent_policy_id",
    "context_tokens_per_slot",
    "context_tokens_total",
    "key_order_ids",
    "key_representation_id",
    "matcher_policy_id",
    "mechanism_control_id",
    "queue_depth",
    "slot_count",
    "top_k",
)


def _count_jsonl_lines(path: Path) -> int:
    """Count rows of a JSONL file WITHOUT decoding or parsing any row.

    Label blindness is structural here, not a convention: the bytes of each
    line are never decoded to text and never handed to ``json.loads``, so no
    prediction, label, correctness, reward, or response meaning can leak into
    the caller through this function.
    """

    count = 0
    try:
        with Path(path).open("rb") as handle:
            for raw_line in handle:
                if raw_line.strip():
                    count += 1
    except OSError as error:
        raise SpeechNativeProfileError(
            f"cannot count decision rows: {error}"
        ) from error
    return count


def derive_server_log_window_for_contacts(
    *,
    server_log_path: Path,
    expected_contact_count: int,
    server_log_end_offset: int | None = None,
) -> tuple[int, int]:
    """Locate the trailing log window holding exactly N slot launches.

    A live flight records its own ``[start, end)`` byte window while it runs.
    An attempt that died before minting its receipt never persisted those
    offsets, so a from-disk rebuild has to re-derive them. The derivation is
    deliberately a *hypothesis*: take the byte offset of the line carrying the
    ``expected_contact_count``-th launch counted back from the window end. It
    is then handed to :func:`_scan_server_slot_events`, whose independent
    fail-closed checks -- no task straddling the start boundary, no slot left
    active at the end, and launch/release counts both equal to
    ``expected_contact_count`` -- are what actually admit or reject it. A
    window that does not correspond to exactly one quiescent flight cannot
    survive those checks.
    """

    if (
        isinstance(expected_contact_count, bool)
        or not isinstance(expected_contact_count, int)
        or expected_contact_count <= 0
    ):
        raise SpeechNativeProfileError(
            "expected_contact_count must be a positive integer"
        )
    try:
        log_bytes = Path(server_log_path).read_bytes()
    except OSError as error:
        raise SpeechNativeProfileError(
            f"cannot read profile server log: {error}"
        ) from error
    if server_log_end_offset is None:
        server_log_end_offset = len(log_bytes)
    if (
        isinstance(server_log_end_offset, bool)
        or not isinstance(server_log_end_offset, int)
        or server_log_end_offset < 0
        or server_log_end_offset > len(log_bytes)
    ):
        raise SpeechNativeProfileError("server log end offset is outside the log")
    launch_offsets: list[int] = []
    byte_offset = 0
    for raw_line in log_bytes[:server_log_end_offset].splitlines(keepends=True):
        if _SERVER_SLOT_LAUNCH.search(raw_line) is not None:
            launch_offsets.append(byte_offset)
        byte_offset += len(raw_line)
    if len(launch_offsets) < expected_contact_count:
        raise SpeechNativeProfileError(
            f"server log holds {len(launch_offsets)} slot launches before the window "
            f"end but {expected_contact_count} contacts were recorded"
        )
    return launch_offsets[-expected_contact_count], server_log_end_offset


#: Block size of the trace reader's raw reads. The trace is read through a
#: handful of large ``read(2)`` calls instead of ``TextIOWrapper``'s 8 KiB
#: chunks: over the drvfs/9p run root the line iteration cost 14.6 s of a
#: 37.9 s seal on ROLL-2's 719 MiB trace (about 92,000 small reads) while
#: ``read_bytes`` on the same file took about 4 s
#: (docs/results/2026-09-26-slurp-seal-path-profile.md, section 6). 64 MiB
#: keeps the reader's peak memory at one buffer plus one line rather than the
#: whole trace, so the host reserve (owner decision 119) is untouched.
_TRACE_READ_BLOCK_BYTES = 64 * 1024 * 1024


def _iter_trace_lines(
    path: Path, *, block_bytes: int = _TRACE_READ_BLOCK_BYTES
) -> Iterator[str]:
    """Yield a trace file's lines, decoded as UTF-8, through large raw reads.

    Line discipline is ``core.tracing.TraceSink.emit``'s: every record is one
    ``json.dumps`` line terminated by ``"\n"``, so the file is split on
    ``b"\n"`` alone. Each yielded line excludes its terminator (``json.loads``
    never saw it as anything but whitespace); a final unterminated line is
    yielded as it stands; an empty line between two records is yielded empty,
    so it fails ``json.loads`` exactly as it did under text-mode iteration.
    Decoding per line is exact because the newline byte never occurs inside
    a UTF-8 multi-byte sequence, and a byte sequence that is not UTF-8 raises
    ``UnicodeDecodeError`` (a ``UnicodeError``) as the text reader's did.
    """

    if isinstance(block_bytes, bool) or not isinstance(block_bytes, int) or block_bytes <= 0:
        raise ValueError("block_bytes must be a positive integer")
    # io.BufferedReader's C-level readline over a ``block_bytes`` buffer: the
    # raw file is read ``block_bytes`` at a time (13 reads for a 719 MiB
    # trace) while one line at a time is resident. Measured on an ext4 copy
    # of ROLL-2's trace it is also faster than the text-mode iteration
    # (1.32 s against 1.45 s), which a Python-level block splitter was not.
    with io.BufferedReader(io.FileIO(str(path), "rb"), buffer_size=block_bytes) as handle:
        for raw in handle:
            if raw.endswith(b"\n"):
                raw = raw[:-1]
            yield raw.decode("utf-8")


def read_attempt_trace_facts(path: Path) -> dict[str, object]:
    """Summarise one attempt trace without ever opening ``MODEL_RESPONSE``.

    The live receipt takes its token maxima from each response record's
    ``usage`` block. This function refuses to touch a response record's
    payload at all -- it counts the record and moves on -- and takes the same
    per-contact token accounting from the ``COST`` channel, which carries the
    identical metered figures. Only structural carriage fields are read from
    ``MODEL_REQUEST``: never the prompt, the messages, or any generated text.

    The file is read by :func:`_iter_trace_lines` (a few large raw reads,
    bounded memory) and summarised by :func:`_trace_facts_from_lines`; the
    facts are identical to those of the former text-mode line iteration, which
    the unit tests hold against a reference iteration on fixtures.
    """

    try:
        return _trace_facts_from_lines(_iter_trace_lines(path))
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        raise SpeechNativeProfileError(
            f"cannot verify profile trace from disk: {error}"
        ) from error


def _trace_facts_from_lines(lines: Iterable[str]) -> dict[str, object]:
    """The per-record accounting of :func:`read_attempt_trace_facts`.

    ``lines`` is any iterable of JSON lines (terminator optional). Kept
    separate from the file reader so that two line sources can be proven to
    yield one facts object; the exceptions the file reader and ``json`` raise
    propagate unchanged and are mapped by the caller.
    """

    request_count = 0
    response_count = 0
    cost_count = 0
    calls_total = 0
    prompt_tokens_total = 0
    completion_tokens_total = 0
    audio_seconds_total = 0.0
    latency_seconds_total = 0.0
    max_prompt_tokens = 0
    max_completion_tokens = 0
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
    sample_ids: set[str] = set()
    packet_ids: set[str] = set()
    for line in lines:
        record = json.loads(line)
        channel = record.get("channel")
        if channel == "MODEL_RESPONSE":
            # Counted, never opened: the payload is not touched here.
            response_count += 1
            continue
        if channel == "COST":
            cost_count += 1
            payload = record.get("payload")
            if not isinstance(payload, Mapping):
                raise SpeechNativeProfileError("trace cost record is malformed")
            calls = payload.get("calls")
            prompt_tokens = payload.get("prompt_tokens")
            completion_tokens = payload.get("completion_tokens")
            audio_seconds = payload.get("audio_seconds")
            latency_seconds = payload.get("latency_seconds")
            for name, value in (
                ("calls", calls),
                ("prompt_tokens", prompt_tokens),
                ("completion_tokens", completion_tokens),
            ):
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0
                ):
                    raise SpeechNativeProfileError(
                        f"trace cost record {name} is malformed"
                    )
            for name, value in (
                ("audio_seconds", audio_seconds),
                ("latency_seconds", latency_seconds),
            ):
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or float(value) < 0
                ):
                    raise SpeechNativeProfileError(
                        f"trace cost record {name} is malformed"
                    )
            assert isinstance(calls, int)
            assert isinstance(prompt_tokens, int)
            assert isinstance(completion_tokens, int)
            calls_total += calls
            prompt_tokens_total += prompt_tokens
            completion_tokens_total += completion_tokens
            audio_seconds_total += float(audio_seconds)  # type: ignore[arg-type]
            latency_seconds_total += float(latency_seconds)  # type: ignore[arg-type]
            max_prompt_tokens = max(max_prompt_tokens, prompt_tokens)
            max_completion_tokens = max(
                max_completion_tokens, completion_tokens
            )
            continue
        if channel != "MODEL_REQUEST":
            continue
        request_count += 1
        counts["model_request_count"] += 1
        envelope = record.get("payload")
        payload = (
            envelope.get("payload") if isinstance(envelope, Mapping) else None
        )
        if not isinstance(payload, Mapping):
            payload = {}
        sample_id = payload.get("sample_id")
        if isinstance(sample_id, str) and sample_id:
            sample_ids.add(sample_id)
        else:
            counts["unknown_sample_id_count"] += 1
        source_valid = payload.get("query_source") == "speech_features"
        mmproj_valid = payload.get("mmproj_loaded") is False
        if not source_valid:
            counts["query_source_failure_count"] += 1
        if not mmproj_valid:
            counts["mmproj_flag_failure_count"] += 1
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
        packet_sha256 = payload.get("speech_packet_sha256")
        binding_valid = (
            len(query_parts) == 1
            and isinstance(packet_sha256, str)
            and _SHA256.fullmatch(packet_sha256) is not None
            and query_parts[0].get("sha256") == packet_sha256
            and isinstance(query_parts[0].get("packet_id"), str)
            and bool(query_parts[0].get("packet_id"))
        )
        if binding_valid:
            packet_ids.add(str(query_parts[0]["packet_id"]))
        else:
            counts["packet_binding_failure_count"] += 1
        if source_valid and mmproj_valid and binding_valid:
            counts["valid_speech_query_count"] += 1
        else:
            counts["invalid_speech_query_count"] += 1
    return {
        "trace_usage": {
            "model_request_count": request_count,
            "model_response_count": response_count,
            "cost_record_count": cost_count,
            "max_prompt_tokens": max_prompt_tokens,
            "max_completion_tokens": max_completion_tokens,
        },
        "trace_usage_source": "cost-channel-token-accounting-v1",
        "cost": {
            "calls_used": calls_total,
            "prompt_tokens_total": prompt_tokens_total,
            "completion_tokens_total": completion_tokens_total,
            "audio_seconds_used": audio_seconds_total,
            "latency_seconds_total": latency_seconds_total,
        },
        "speech_query": dict(counts),
        "distinct_query_sample_id_count": len(sample_ids),
        "distinct_query_packet_id_count": len(packet_ids),
    }


def build_flight_receipt_from_disk(
    *,
    attempt_dir: Path,
    plan: ExecutionPlan,
    config_hash: str,
    profile_identity: Mapping[str, object],
    contact_ceiling_per_task: int,
    expected_task_count: int,
    result_mode: str,
    transport_prompt_order: str,
    binding_path: Path,
    packet_receipt_path: Path,
    server_log_path: Path,
    server_log_start_offset: int,
    server_log_end_offset: int,
    session_started_at: str,
    source_session_receipt_sha256: str,
    authorization: str,
    exposure_row: str,
    rebuilt_at: str,
) -> dict[str, object]:
    """Rebuild one interrupted attempt's flight receipt from durable records.

    A pure function of its inputs: every value it returns is derived from the
    bytes named by its arguments, so two rebuilds of the same attempt produce
    byte-identical data-derived fields. ``rebuilt_at`` is the single
    wall-clock input; it is carried in ``finalization.rebuilt_at`` and is
    excluded from ``finalization.content_sha256`` (as is the content hash
    itself), which is the receipt schema's convention -- no other receipt
    field has ever recorded a timestamp.

    It contacts nothing. It constructs no transport, no client, and no socket:
    the resident service's session receipt and log are read as bytes, and the
    frozen core is not spoken to in any form. It is also label blind:
    ``decisions.jsonl`` is line-counted through :func:`_count_jsonl_lines`
    without decoding a row, and the trace's ``MODEL_RESPONSE`` channel is
    counted but never opened (:func:`read_attempt_trace_facts`).

    GPU-derived fields degrade to ``NOT_AVAILABLE`` with a
    ``gpu_telemetry_defect`` reason (the repaired mode of
    :func:`profile_server_slot_event_gpu_metrics`), while the slot-event
    lifecycle checks re-run on their own merits and still fail closed.
    """

    attempt_dir = Path(attempt_dir)
    flight_receipt_path = attempt_dir / "flight-receipt.json"
    if flight_receipt_path.exists():
        raise SpeechNativeProfileError(
            f"attempt is already finalized: {flight_receipt_path} exists; "
            "a rebuilt receipt must never overwrite a minted one"
        )
    for name in _FINALIZE_FROM_DISK_PROFILE_IDENTITY_KEYS:
        if name not in profile_identity:
            raise SpeechNativeProfileError(
                f"finalize-from-disk profile identity lacks {name!r}"
            )
    if (
        isinstance(contact_ceiling_per_task, bool)
        or not isinstance(contact_ceiling_per_task, int)
        or contact_ceiling_per_task <= 0
    ):
        raise SpeechNativeProfileError(
            "contact_ceiling_per_task must be a positive integer"
        )
    if result_mode != "predictions":
        raise SpeechNativeProfileError(
            "finalize-from-disk applies only to a predictions-mode attempt"
        )
    slot_count = profile_identity["slot_count"]
    context_tokens_per_slot = profile_identity["context_tokens_per_slot"]
    if (
        isinstance(slot_count, bool)
        or not isinstance(slot_count, int)
        or slot_count <= 0
        or isinstance(context_tokens_per_slot, bool)
        or not isinstance(context_tokens_per_slot, int)
        or context_tokens_per_slot <= 0
    ):
        raise SpeechNativeProfileError(
            "finalize-from-disk profile geometry is malformed"
        )

    plan_copy_path = attempt_dir / f"{plan.run_id}.plan.json"
    session_receipt_path = attempt_dir / f"{plan.run_id}.session-receipt.json"
    stop_receipt_path = attempt_dir / f"{plan.run_id}.session-stop-receipt.json"
    audit_path = attempt_dir / f"{plan.run_id}.mmproj-audit.json"
    trace_path = attempt_dir / f"{plan.run_id}.trace.jsonl"
    trace_manifest_path = attempt_dir / f"{plan.run_id}.trace-manifest.json"
    decisions_path = attempt_dir / "decisions.jsonl"
    for required in (
        plan_copy_path,
        session_receipt_path,
        audit_path,
        trace_path,
        trace_manifest_path,
        decisions_path,
    ):
        if not required.is_file():
            raise SpeechNativeProfileError(
                f"finalize-from-disk requires a durable {required.name}; it is missing"
            )
    try:
        plan_copy = json.loads(plan_copy_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read the attempt-local plan copy: {error}"
        ) from error
    if plan_copy != asdict(plan):
        raise SpeechNativeProfileError(
            "the attempt-local plan copy does not match the supplied execution plan"
        )

    # decisions.jsonl exists only when the flight's own try/except recorded no
    # failure (``result_mode == "predictions" and failure is None``), so its
    # presence is the on-disk proof that no request failed.
    task_count = _count_jsonl_lines(decisions_path)
    if task_count <= 0 or task_count != expected_task_count:
        raise SpeechNativeProfileError(
            f"decision rows ({task_count}) do not match the registered task count "
            f"({expected_task_count})"
        )
    planned_contact_ceiling = task_count * contact_ceiling_per_task
    if planned_contact_ceiling != plan.planned_model_calls:
        raise SpeechNativeProfileError(
            f"attempt expands to a {planned_contact_ceiling}-contact ceiling but the "
            f"plan registers {plan.planned_model_calls}"
        )

    trace_facts = read_attempt_trace_facts(trace_path)
    trace_usage = trace_facts["trace_usage"]
    cost = trace_facts["cost"]
    trace_speech_query = trace_facts["speech_query"]
    assert isinstance(trace_usage, Mapping)
    assert isinstance(cost, Mapping)
    assert isinstance(trace_speech_query, Mapping)
    actual_contact_count = int(cost["calls_used"])
    if actual_contact_count <= 0:
        raise SpeechNativeProfileError("the attempt trace records no contact")
    if trace_facts["distinct_query_sample_id_count"] != task_count:
        raise SpeechNativeProfileError(
            "traced query sample identities do not cover the decision rows"
        )

    audit_document = _load_json_object(audit_path, artifact_name="mmproj process audit")
    if (
        audit_document.get("mmproj_loaded") is not False
        or audit_document.get("mmproj_hit_count") != 0
    ):
        raise SpeechNativeProfileError(
            "the attempt's process audit does not prove an mmproj-free service"
        )
    session_document = _load_json_object(
        session_receipt_path, artifact_name="attempt session receipt"
    )
    if session_document.get("started_at") != session_started_at:
        raise SpeechNativeProfileError(
            "session_started_at does not match the attempt's own session receipt"
        )

    resource_summary: dict[str, object] = {
        "source": FINALIZE_FROM_DISK_MODE_ID,
        "request_gpu_samples": [],
        "gpu_seconds": NOT_AVAILABLE,
        "gpu_sampling_reason": (
            "the flown attempt's GPU sampler never started, and a from-disk "
            "rebuild samples nothing"
        ),
    }
    lifecycle = _scan_server_slot_events(
        server_log_path=server_log_path,
        server_log_start_offset=server_log_start_offset,
        server_log_end_offset=server_log_end_offset,
        session_started_at=session_started_at,
        slot_count=slot_count,
        expected_contact_count=actual_contact_count,
    )
    saturated_gpu = profile_server_slot_event_gpu_metrics(
        server_log_path=server_log_path,
        server_log_start_offset=server_log_start_offset,
        server_log_end_offset=server_log_end_offset,
        session_started_at=session_started_at,
        resource_summary=resource_summary,
        slot_count=slot_count,
        expected_contact_count=actual_contact_count,
    )
    if saturated_gpu.get("gpu_telemetry_defect") is None:
        raise SpeechNativeProfileError(
            "finalize-from-disk must record an explicit GPU telemetry defect"
        )
    server_scan = _scan_server_log(
        Path(server_log_path),
        start_offset=server_log_start_offset,
        end_offset=server_log_end_offset,
    )

    event_times = lifecycle["event_times"]
    assert isinstance(event_times, list)
    request_window_seconds = float(event_times[-1]) - float(event_times[0])
    if request_window_seconds <= 0:
        raise SpeechNativeProfileError("the rebuilt request window is not positive")
    prompt_tokens_total = int(cost["prompt_tokens_total"])
    completion_tokens_total = int(cost["completion_tokens_total"])
    timing = {
        "request_window_seconds": request_window_seconds,
        "slot_occupancy_pct": min(
            100.0,
            100.0
            * float(cost["latency_seconds_total"])
            / (slot_count * request_window_seconds),
        ),
        "aggregate_tokens_per_second": (
            (prompt_tokens_total + completion_tokens_total) / request_window_seconds
        ),
        "source": "server-slot-event-window-v1",
    }
    evaluated_work = profile_evaluated_work_metrics(
        server_scan=server_scan,
        declared_prompt_tokens=prompt_tokens_total,
        completion_tokens=completion_tokens_total,
        wall_seconds=request_window_seconds,
        contact_count=actual_contact_count,
    )

    profile: dict[str, object] = dict(profile_identity)
    profile.update(
        {
            "task_count": task_count,
            "semantic_result_read": False,
            "result_mode": result_mode,
            "contact_ceiling_per_task": contact_ceiling_per_task,
            "planned_contact_ceiling": planned_contact_ceiling,
            "actual_contact_count": actual_contact_count,
            "transport_prompt_order": transport_prompt_order,
            "prompt_work_policy": profile_prompt_work_policy(transport_prompt_order),
        }
    )
    receipt: dict[str, object] = {
        "schema": "saea-speech-native-profile-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "COMPLETED",
        "run_id": plan.run_id,
        "attempt_id": plan.attempt_id,
        "config_hash": config_hash,
        "protocol_hash": plan.protocol_hash,
        "split_identity_hash": plan.split_identity_hash,
        "profile": profile,
        "resource": dict(resource_summary),
        "server_log_scan": server_scan,
        "process_audit_sha256": _sha256_file(audit_path),
        "session_receipt_sha256": _sha256_file(session_receipt_path),
        "session_stop_receipt_sha256": (
            _sha256_file(stop_receipt_path) if stop_receipt_path.is_file() else None
        ),
        "session_lifecycle": {
            "mode": "resident-attached",
            "resident_reused": True,
            "source_session_receipt_sha256": source_session_receipt_sha256,
            "server_log_path": str(server_log_path),
            "server_log_start_offset": server_log_start_offset,
            "server_log_end_offset": server_log_end_offset,
        },
        "packet_promotion_receipt_sha256": _sha256_file(packet_receipt_path),
        "binding_file_sha256": _sha256_file(binding_path),
        "response_text_sha256": NOT_AVAILABLE,
        "parse_failure_count": NOT_AVAILABLE,
        "request_failures": [],
        "close": {"cost": dict(cost), "source": FINALIZE_FROM_DISK_MODE_ID},
        "decisions": {
            "path": decisions_path.name,
            "sha256": _sha256_file(decisions_path),
            "count": task_count,
            "contains_gold_labels": False,
        },
        "trace_usage": dict(trace_usage),
        "trace_usage_source": trace_facts["trace_usage_source"],
        "trace_speech_query": dict(trace_speech_query),
        "trace_sha256": _sha256_file(trace_path),
        "trace_manifest_sha256": _sha256_file(trace_manifest_path),
        "timing": timing,
        "evaluated_work": evaluated_work,
        "saturated_gpu": saturated_gpu,
    }
    receipt["eligibility"] = {
        "maximum_prompt_fits_one_slot": (
            int(trace_usage["max_prompt_tokens"])
            + int(trace_usage["max_completion_tokens"])
            <= context_tokens_per_slot
        ),
        "zero_request_failures": True,
        "zero_oom_markers": not server_scan["oom_marker_hits"],
        "zero_host_spill_markers": not server_scan["host_spill_marker_hits"],
        "zero_runaway_markers": not server_scan["runaway_marker_hits"],
        **profile_gpu_eligibility(saturated_gpu),
        **profile_prompt_work_eligibility(
            evaluated_work, prompt_order=transport_prompt_order
        ),
    }
    eligibility = receipt["eligibility"]
    assert isinstance(eligibility, Mapping)
    receipt["eligible"] = all(bool(value) for value in eligibility.values())
    receipt["completion_issues"] = list(
        _profile_completion_issues(
            calls_used=actual_contact_count,
            actual_contact_count=actual_contact_count,
            task_count=task_count,
            planned_contact_ceiling=planned_contact_ceiling,
            request_failure_count=0,
            server_scan=server_scan,
            trace_usage=trace_usage,
            trace_speech_query=trace_speech_query,
        )
    )
    finalization: dict[str, object] = {
        "mode": FINALIZE_FROM_DISK_MODE_ID,
        "authorization": authorization,
        "exposure_row": exposure_row,
        "service_contact_count": 0,
        "unread_channels": list(_FINALIZE_FROM_DISK_UNREAD_CHANNELS),
        "unrecoverable_fields": [
            "profile.query_mapping_sha256",
            "parse_failure_count",
            "response_text_sha256",
        ],
        "unrecoverable_fields_note": (
            "These live-flight fields are derived from in-memory decision "
            "outcomes. Recovering them would require parsing decision rows or "
            "opening the MODEL_RESPONSE channel, which this label-blind rebuild "
            "refuses. The per-row hashes they summarise remain inside "
            "decisions.jsonl and the trace, both pinned here by SHA-256."
        ),
        "rebuilt_at": rebuilt_at,
    }
    hashed = dict(receipt)
    hashed["finalization"] = {
        key: value
        for key, value in finalization.items()
        if key not in {"rebuilt_at", "content_sha256"}
    }
    finalization["content_sha256"] = _canonical_sha256(hashed)
    receipt["finalization"] = finalization
    return receipt


def _load_json_object(path: Path, *, artifact_name: str) -> dict[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechNativeProfileError(
            f"cannot read {artifact_name}: {error}"
        ) from error
    if not isinstance(document, dict):
        raise SpeechNativeProfileError(f"{artifact_name} must be a JSON object")
    return document


def _finalize_from_disk_profile_identity(
    *,
    repo_root: Path,
    values: Mapping[str, object],
) -> dict[str, object]:
    """Rebuild the receipt's config-derived profile identity, file reads only."""

    matcher_policy_id = _require_string(values, "matcher_policy_id")
    key_representation_id = _require_string(values, "key_representation_id")
    slot_count = _require_positive_int(values, "profile_slot_count")
    geometry = _profile_geometry(values, slot_count)
    queue_multiplier = _require_positive_int(values, "profile_queue_depth_multiplier")
    transport_prompt_order = _require_string(values, "prompt_order")
    raw_order_ids = values.get("profile_key_order_ids")
    if (
        not isinstance(raw_order_ids, list)
        or not raw_order_ids
        or not all(isinstance(item, str) for item in raw_order_ids)
    ):
        raise SpeechNativeProfileError(
            "profile_key_order_ids must be a non-empty string list"
        )
    top_k = values.get("speech_native_top_k", 3)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise SpeechNativeProfileError("speech_native_top_k must be a positive integer")
    mechanism_control_id = values.get("speech_native_mechanism_control_id", "matched")
    if mechanism_control_id != "matched":
        raise SpeechNativeProfileError(
            "finalize-from-disk supports only the matched mechanism control; a "
            "swap or shuffle control's task mapping cannot be rebuilt label-blind"
        )
    # Executor retirement (owner Decision 12-F item #9, 2026-09-08): the
    # silent default is gone here too, for the same reason -- a rebuilt
    # manifest must say which harness produced the outputs it is rebuilding
    # from. This function contacts nothing (it re-derives a finalized manifest
    # from an attempt's own on-disk artifacts), so it accepts the same two
    # spellings the profile path does rather than pinning the legacy one:
    # refusing a fragment that has since named its executor explicitly would
    # strand exactly the attempts this retirement moves.
    agent_executor_id = resolve_speech_native_agent_executor_id(values)
    binding_relpath = _require_string(values, "speech_native_binding")
    binding_path = (repo_root / binding_relpath).resolve()
    binding_sha256 = _require_string(values, "speech_native_binding_file_sha256")
    key_cards = _load_key_cards(binding_path, binding_sha256)
    decision_graph_id: str | None = None
    decision_graph_relpath: str | None = None
    decision_graph_file_sha256: str | None = None
    if matcher_policy_id in {"M9", "M10", "M11"}:
        graph_relpath = _require_string(values, "speech_native_decision_graph")
        graph_path = (repo_root / graph_relpath).resolve()
        decision_graph_file_sha256 = _require_string(
            values, "speech_native_decision_graph_file_sha256"
        )
        decision_graph_id = _load_decision_graph(
            graph_path,
            expected_sha256=decision_graph_file_sha256,
            key_cards=key_cards,
        ).graph_id
        decision_graph_relpath = graph_path.relative_to(repo_root.resolve()).as_posix()
    prompt_fit_relpath: str | None = None
    prompt_fit_sha256: str | None = None
    prompt_fit_upper_bound: object = None
    prompt_fit_margin: object = None
    if matcher_policy_id == "M11":
        prompt_fit_relpath = _require_string(values, "speech_native_prompt_fit_receipt")
        prompt_fit_sha256 = _require_string(
            values, "speech_native_prompt_fit_receipt_sha256"
        )
        prompt_fit_document = _load_pinned_json_object(
            (repo_root / prompt_fit_relpath).resolve(),
            expected_sha256=prompt_fit_sha256,
            artifact_name="M11 prompt-fit receipt",
        )
        prompt_fit_upper_bound = prompt_fit_document.get(
            "maximum_prompt_tokens_upper_bound"
        )
        prompt_fit_margin = prompt_fit_document.get("context_margin_tokens")
    reader_policy_id, reader_contract = _m11_reader_contract_from_values(
        values, matcher_policy_id
    )
    return {
        "slot_count": slot_count,
        "queue_depth": slot_count * queue_multiplier,
        "key_card_count": len(key_cards),
        "key_order_ids": list(raw_order_ids),
        "key_representation_id": key_representation_id,
        "matcher_policy_id": matcher_policy_id,
        "decision_graph_id": decision_graph_id,
        "decision_graph_path": decision_graph_relpath,
        "decision_graph_file_sha256": decision_graph_file_sha256,
        "prompt_fit_receipt_path": prompt_fit_relpath,
        "prompt_fit_receipt_sha256": prompt_fit_sha256,
        "prompt_fit_maximum_prompt_tokens_upper_bound": prompt_fit_upper_bound,
        "prompt_fit_context_margin_tokens": prompt_fit_margin,
        "matcher_prompt_policy_id": values.get(
            "matcher_prompt_policy_id", "speech-native-json-copy-v2"
        ),
        "agent_kv_policy": profile_agent_kv_policy(
            _server_args(values), prompt_order=transport_prompt_order
        ),
        "request_layout_id": values.get(
            "speech_native_request_layout_id", "legacy-key-speech-v1"
        ),
        "matcher_verifier_policy_id": values.get(
            "matcher_verifier_policy_id", "speech-native-compatibility-v1"
        ),
        "agent_policy_id": values.get(
            "speech_native_agent_policy_id", "m1-m3-disagreement-escalation-v1"
        ),
        "agent_aggregator_id": values.get(
            "speech_native_agent_aggregator_id", "m3-majority-canonical-tie-v1"
        ),
        "agent_executor_id": agent_executor_id,
        "knowledge_snapshot_sha256": None,
        "knowledge_source_sample_count": None,
        "speech_native_training_free_reader_policy_id": reader_policy_id,
        "speech_native_training_free_reader_contract": reader_contract,
        "dispatch_granularity": values.get(
            "speech_native_dispatch_granularity", "task"
        ),
        "mechanism_control_id": mechanism_control_id,
        "query_mapping_sha256": NOT_AVAILABLE,
        "key_text_mapping_sha256": None,
        "top_k": top_k,
        **geometry,
    }


def _cli_speech_native_finalize_from_disk(args: argparse.Namespace) -> int:
    """Finalize an already-flown attempt from its durable records alone.

    This entry point is physically incapable of contacting the frozen core: it
    never constructs a transport, a ``FrozenCoreClient``, an HTTP connection,
    or a session handle, and it never starts, stops, attaches to, or probes a
    server. Its only inputs are the repository's frozen configuration and the
    attempt's own bytes; the resident service's session receipt and log are
    read as files.

    It exists for the failure mode the 2026-08-23 E108 flight hit: every model
    contact completed, every durable record landed, and post-run metrics
    assembly then raised, so no receipt was minted and the attempt could not
    be finalized. Re-flying would re-spend the split on byte-identical inputs;
    rebuilding costs nothing and reads nothing new.
    """

    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    root = data_root()
    lock = load_lock(umbrella_lock_path())
    composed = compose(
        repo_root, args.model, args.dataset, args.baseline, args.experiment
    )
    values = composed.values
    plan = ExecutionPlan(
        **json.loads(Path(args.plan).read_text(encoding="utf-8"))
    ).validate()
    split_ids, split_hash, split_role = load_split(
        repo_root, _require_string(values, "split_name"), lock, root
    )
    expected_protocol = protocol_hash(
        composed.config_hash, str(values["arm"]), split_hash
    )
    if (
        plan.split_identity_hash != split_hash
        or plan.split_role != split_role
        or plan.protocol_hash != expected_protocol
        or plan.carrier_lock_key != values.get("carrier_lock_key")
    ):
        raise SpeechNativeProfileError(
            "execution plan does not match the composed profile"
        )
    attempt_dir = Path(args.attempt_dir).resolve()
    if attempt_dir.name != plan.attempt_id or not attempt_dir.is_dir():
        raise SpeechNativeProfileError(
            "attempt-dir basename must equal plan.attempt_id and must exist"
        )
    session_receipt_path = Path(args.session_receipt).resolve()
    source_session_receipt_sha256 = _sha256_file(session_receipt_path)
    if source_session_receipt_sha256 != args.session_receipt_sha256:
        raise SpeechNativeProfileError(
            "the resident session receipt changed since the attempt was flown; "
            f"expected {args.session_receipt_sha256}, found "
            f"{source_session_receipt_sha256}"
        )
    session_document = _load_json_object(
        session_receipt_path, artifact_name="resident session receipt"
    )
    server_log_value = session_document.get("server_log_path")
    if not isinstance(server_log_value, str) or not server_log_value:
        raise SpeechNativeProfileError(
            "the resident session receipt does not name a server log"
        )
    server_log_path = Path(server_log_value)
    session_started_at = session_document.get("started_at")
    if not isinstance(session_started_at, str) or not session_started_at:
        raise SpeechNativeProfileError(
            "the resident session receipt does not carry a start timestamp"
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
    profile_identity = _finalize_from_disk_profile_identity(
        repo_root=repo_root, values=values
    )
    trace_facts = read_attempt_trace_facts(attempt_dir / f"{plan.run_id}.trace.jsonl")
    cost = trace_facts["cost"]
    assert isinstance(cost, Mapping)
    actual_contact_count = int(cost["calls_used"])
    if args.server_log_start_offset is None or args.server_log_end_offset is None:
        server_log_start_offset, server_log_end_offset = (
            derive_server_log_window_for_contacts(
                server_log_path=server_log_path,
                expected_contact_count=actual_contact_count,
            )
        )
    else:
        server_log_start_offset = int(args.server_log_start_offset)
        server_log_end_offset = int(args.server_log_end_offset)

    receipt = build_flight_receipt_from_disk(
        attempt_dir=attempt_dir,
        plan=plan,
        config_hash=composed.config_hash,
        profile_identity=profile_identity,
        contact_ceiling_per_task=contact_ceiling,
        expected_task_count=len(split_ids),
        result_mode=str(values.get("speech_native_result_mode", "hash-only")),
        transport_prompt_order=_require_string(values, "prompt_order"),
        binding_path=(
            repo_root / _require_string(values, "speech_native_binding")
        ).resolve(),
        packet_receipt_path=Path(
            _require_string(values, "speech_packet_promotion_receipt")
        ),
        server_log_path=server_log_path,
        server_log_start_offset=server_log_start_offset,
        server_log_end_offset=server_log_end_offset,
        session_started_at=session_started_at,
        source_session_receipt_sha256=source_session_receipt_sha256,
        authorization=args.authorization,
        exposure_row=args.exposure_row,
        rebuilt_at=datetime.now().astimezone().isoformat(),
    )
    completion_issues = receipt["completion_issues"]
    assert isinstance(completion_issues, list)
    if completion_issues:
        raise SpeechNativeProfileError(
            f"rebuilt attempt fails its completion checks: {completion_issues}"
        )
    flight_receipt_path = attempt_dir / "flight-receipt.json"
    _write_exclusive_json(flight_receipt_path, receipt)
    attempt = AttemptStore(Path(root) / "attempts").handle(
        plan.run_id, str(plan.attempt_id)
    )
    if not attempt.path.is_file():
        raise SpeechNativeProfileError(
            "the attempt has no durable accounting record to finalize"
        )
    attempt.mark_finalized()
    finalization = receipt["finalization"]
    assert isinstance(finalization, Mapping)
    profile = receipt["profile"]
    assert isinstance(profile, Mapping)
    print(
        json.dumps(
            {
                "run_id": plan.run_id,
                "attempt_id": plan.attempt_id,
                "flight_receipt": str(flight_receipt_path),
                "flight_receipt_sha256": _sha256_file(flight_receipt_path),
                "content_sha256": finalization["content_sha256"],
                "rebuilt_at": finalization["rebuilt_at"],
                "decision_count": profile["task_count"],
                "actual_contact_count": profile["actual_contact_count"],
                "server_log_start_offset": server_log_start_offset,
                "server_log_end_offset": server_log_end_offset,
                "service_contact_count": 0,
                "status": "FINALIZED_FROM_DISK",
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
    action_sensitive_count = report.get("action_sensitive_count")
    if action_sensitive_count is None:
        action_sensitive_count = report["action_variable_query_count"]
    action_support_threshold_met = report.get("action_support_threshold_met")
    if action_support_threshold_met is None:
        action_support_threshold_met = report.get("action_variable_threshold_met")
    if action_support_threshold_met is None:
        action_support_threshold_met = report["engineering_gate_passed"]
    print(
        json.dumps(
            {
                "output": str(output),
                "action_sensitive_count": action_sensitive_count,
                "action_support_threshold_met": action_support_threshold_met,
                "gold_read": False,
                "effectiveness_eligible": report.get("effectiveness_eligible", False),
                "effectiveness_read_authorized": report.get(
                    "effectiveness_read_authorized", False
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


__all__ = [
    "SpeechNativeProfileError",
    "_cli_speech_native_engine_audit",
    "_cli_speech_native_prompt_audit",
    "_cli_speech_native_profile",
    "_cli_speech_native_read",
    "build_profile_tasks",
    "profile_timing_metrics",
    "read_speech_native_predictions",
]
