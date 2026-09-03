"""Thin Vowpal Wabbit adapter for an external training-free control plane.

This module does not implement a reinforcement-learning algorithm.  It only
translates deployment-visible state and a variable macro-action set into the
upstream ``cb_explore_adf`` format, validates upstream probability output, and
produces content-addressed receipts.  Vowpal Wabbit is imported only when a
workspace is explicitly created, so importing the base package stays free of
the optional binary dependency.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

UPSTREAM_DISTRIBUTION = "vowpalwabbit"
UPSTREAM_VERSION = "9.11.2"
UPSTREAM_PROJECT_URL = "https://github.com/VowpalWabbit/vowpal_wabbit"
ADAPTER_SCHEMA = "saea-training-free-vw-control-adapter-v1"
DECISION_SCHEMA = "saea-training-free-vw-control-decision-v1"
POLICY_ARTIFACT_SCHEMA = "saea-training-free-vw-policy-artifact-v1"
_FORBIDDEN_INFORMATION_TOKENS = frozenset({"gold", "reference", "test"})
_PROBABILITY_SUM_TOLERANCE = 1e-6


class VwAdapterError(ValueError):
    """The caller supplied invalid state, actions, feedback, or VW output."""


class VwUnavailable(RuntimeError):
    """The pinned optional Vowpal Wabbit runtime is unavailable."""


@dataclass(frozen=True)
class RuntimeState:
    """Deployment-visible controller state, separated by feature type."""

    numeric: Mapping[str, float] = field(default_factory=dict)
    categorical: Mapping[str, str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class MacroAction:
    """One currently available macro-action and its deployment-visible data."""

    action_id: str
    numeric: Mapping[str, float] = field(default_factory=dict)
    categorical: Mapping[str, str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class VwConfig:
    """Exact upstream argument vector used to create a VW workspace."""

    arguments: tuple[str, ...]

    @property
    def argument_string(self) -> str:
        return " ".join(self.arguments)


DEFAULT_VW_CONFIG = VwConfig(
    arguments=(
        "--cb_explore_adf",
        "--cb_type",
        "dr",
        "--epsilon",
        "0.05",
        "--quadratic",
        "sa",
        "--random_seed",
        "20260903",
        "--quiet",
    )
)


@dataclass(frozen=True)
class AdfExample:
    """Canonical VW multiline example and the action order it binds."""

    text: str
    action_ids: tuple[str, ...]
    sha256: str


@dataclass(frozen=True)
class LoggedAdfExample(AdfExample):
    """ADF example carrying observed feedback for one chosen action."""

    chosen_action_id: str
    cost: float
    propensity: float


@dataclass(frozen=True)
class HashedReceipt:
    """Canonical JSON identity payload and its SHA-256 digest."""

    canonical_json: str
    sha256: str


@dataclass(frozen=True)
class ActionDecision:
    """Selected macro-action plus the complete validated exploration PDF."""

    action_id: str
    action_index: int
    propensity: float
    probabilities: tuple[tuple[str, float], ...]
    draw: float
    example: AdfExample

    @property
    def canonical_json(self) -> str:
        return _canonical_json(
            {
                "schema": DECISION_SCHEMA,
                "action_id": self.action_id,
                "action_index": self.action_index,
                "propensity": self.propensity,
                "probabilities": [
                    {"action_id": action_id, "probability": probability}
                    for action_id, probability in self.probabilities
                ],
                "external_draw": self.draw,
                "example_sha256": self.example.sha256,
            }
        )

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()


def _canonical_json(document: Mapping[str, object]) -> str:
    return json.dumps(
        document,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _feature_token(kind: str, *parts: str) -> str:
    payload = "\0".join((kind, *parts)).encode("utf-8")
    return f"{kind}_{hashlib.sha256(payload).hexdigest()}"


def _validate_key(key: object) -> str:
    if not isinstance(key, str) or not key:
        raise VwAdapterError("feature keys must be non-empty strings")
    tokens = set(filter(None, re.split(r"[^a-z0-9]+", key.casefold())))
    if tokens & _FORBIDDEN_INFORMATION_TOKENS:
        raise VwAdapterError(f"forbidden information key: {key!r}")
    return key


def _finite_number(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VwAdapterError(f"numeric feature {field_name!r} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise VwAdapterError(f"numeric feature {field_name!r} must be finite")
    return result


def _categorical_value(value: object, *, field_name: str) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if not isinstance(value, str):
        raise VwAdapterError(
            f"categorical feature {field_name!r} must be a string or boolean"
        )
    if not value:
        raise VwAdapterError(f"categorical feature {field_name!r} must not be empty")
    return value


def _format_number(value: float) -> str:
    if value == 0:
        return "0"
    return repr(value)


def _numeric_namespace(name: str, features: Mapping[str, float]) -> str | None:
    rendered: list[str] = []
    for raw_key in sorted(features):
        key = _validate_key(raw_key)
        value = _finite_number(features[raw_key], field_name=key)
        rendered.append(f"{_feature_token('n', key)}:{_format_number(value)}")
    return None if not rendered else f"|{name} " + " ".join(rendered)


def _categorical_namespace(
    name: str, features: Mapping[str, str | bool]
) -> str | None:
    rendered: list[str] = []
    for raw_key in sorted(features):
        key = _validate_key(raw_key)
        value = _categorical_value(features[raw_key], field_name=key)
        rendered.append(_feature_token("c", key, value))
    return None if not rendered else f"|{name} " + " ".join(rendered)


def _normalise_actions(actions: Sequence[MacroAction]) -> tuple[MacroAction, ...]:
    if len(actions) < 2:
        raise VwAdapterError("cb_explore_adf requires at least two macro-actions")
    ordered = sorted(actions, key=lambda action: action.action_id)
    for action in ordered:
        if not isinstance(action.action_id, str) or not action.action_id:
            raise VwAdapterError("action_id must be a non-empty string")
    duplicates = [
        ordered[index].action_id
        for index in range(1, len(ordered))
        if ordered[index - 1].action_id == ordered[index].action_id
    ]
    if duplicates:
        raise VwAdapterError(f"duplicate action_id: {duplicates[0]!r}")
    return tuple(ordered)


def _shared_line(state: RuntimeState) -> str:
    namespaces = [
        part
        for part in (
            _numeric_namespace("state_numeric", state.numeric),
            _categorical_namespace("state_categorical", state.categorical),
        )
        if part is not None
    ]
    if not namespaces:
        namespaces.append("|state_bias constant")
    return "shared " + " ".join(namespaces)


def _action_line(action: MacroAction) -> str:
    namespaces = [f"|action_identity {_feature_token('a', action.action_id)}"]
    numeric = _numeric_namespace("action_numeric", action.numeric)
    categorical = _categorical_namespace("action_categorical", action.categorical)
    if numeric is not None:
        namespaces.append(numeric)
    if categorical is not None:
        namespaces.append(categorical)
    return " ".join(namespaces)


def build_adf_example(
    state: RuntimeState, actions: Sequence[MacroAction]
) -> AdfExample:
    """Render a deterministic unlabeled ``cb_explore_adf`` example."""

    ordered = _normalise_actions(actions)
    text = "\n".join((_shared_line(state), *map(_action_line, ordered))) + "\n"
    return AdfExample(
        text=text,
        action_ids=tuple(action.action_id for action in ordered),
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def build_logged_adf_example(
    state: RuntimeState,
    actions: Sequence[MacroAction],
    *,
    chosen_action_id: str,
    terminal_reward: float,
    propensity: float,
) -> LoggedAdfExample:
    """Encode observed terminal reward as VW cost for one logged action."""

    ordered = _normalise_actions(actions)
    action_ids = tuple(action.action_id for action in ordered)
    if chosen_action_id not in action_ids:
        raise VwAdapterError(f"chosen action {chosen_action_id!r} is not available")
    reward = _finite_number(terminal_reward, field_name="terminal_reward")
    probability = _finite_number(propensity, field_name="propensity")
    if not 0 < probability <= 1:
        raise VwAdapterError("propensity must be in the interval (0, 1]")
    cost = -reward
    cost_text = _format_number(cost)
    propensity_text = _format_number(probability)
    action_lines = []
    for action in ordered:
        prefix = (
            f"0:{cost_text}:{propensity_text} "
            if action.action_id == chosen_action_id
            else ""
        )
        action_lines.append(prefix + _action_line(action))
    text = "\n".join((_shared_line(state), *action_lines)) + "\n"
    return LoggedAdfExample(
        text=text,
        action_ids=action_ids,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        chosen_action_id=chosen_action_id,
        cost=cost,
        propensity=probability,
    )


def learn_feedback(
    workspace: object,
    state: RuntimeState,
    actions: Sequence[MacroAction],
    *,
    chosen_action_id: str,
    terminal_reward: float,
    propensity: float,
) -> LoggedAdfExample:
    """Render one propensity-logged example and pass it to upstream VW."""

    example = build_logged_adf_example(
        state,
        actions,
        chosen_action_id=chosen_action_id,
        terminal_reward=terminal_reward,
        propensity=propensity,
    )
    try:
        workspace.learn(example.text)  # type: ignore[attr-defined]
    except AttributeError as error:
        raise VwAdapterError("workspace must expose learn(example)") from error
    return example


def _action_score(item: object) -> tuple[int, float]:
    if hasattr(item, "action") and hasattr(item, "score"):
        index = getattr(item, "action")
        probability = getattr(item, "score")
    elif isinstance(item, (tuple, list)) and len(item) == 2:
        index, probability = item
    else:
        raise VwAdapterError("VW output entries must carry action and score")
    if isinstance(index, bool) or not isinstance(index, int):
        raise VwAdapterError("VW action index must be an integer")
    value = _finite_number(probability, field_name="VW probability")
    return index, value


def validate_probabilities(
    actions: Sequence[MacroAction], raw_scores: object
) -> tuple[tuple[str, float], ...]:
    """Validate and bind VW action-score output to canonical action IDs."""

    ordered = _normalise_actions(actions)
    if not isinstance(raw_scores, Sequence) or isinstance(raw_scores, (str, bytes)):
        raise VwAdapterError("VW must return one probability for every action")
    if len(raw_scores) != len(ordered):
        raise VwAdapterError("VW must return exactly one probability for every action")
    by_index: dict[int, float] = {}
    for position, item in enumerate(raw_scores):
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            index = position
            probability = _finite_number(item, field_name="VW probability")
        else:
            index, probability = _action_score(item)
        if index in by_index:
            raise VwAdapterError(f"VW returned duplicate action index {index}")
        if index < 0 or index >= len(ordered):
            raise VwAdapterError(f"VW returned out-of-range action index {index}")
        if probability < 0:
            raise VwAdapterError("VW probabilities must be non-negative")
        by_index[index] = probability
    if len(by_index) != len(ordered):
        raise VwAdapterError("VW must return exactly one probability for every action")
    total = math.fsum(by_index.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=_PROBABILITY_SUM_TOLERANCE):
        raise VwAdapterError(f"VW probabilities must sum to 1; got {total!r}")
    return tuple(
        (action.action_id, by_index[index]) for index, action in enumerate(ordered)
    )


def predict_action(
    workspace: object,
    state: RuntimeState,
    actions: Sequence[MacroAction],
    *,
    draw: float,
) -> ActionDecision:
    """Predict a PDF and select from it using a caller-recorded external draw."""

    draw_value = _finite_number(draw, field_name="draw")
    if not 0 <= draw_value < 1:
        raise VwAdapterError("draw must be in the interval [0, 1)")
    example = build_adf_example(state, actions)
    try:
        raw_scores = workspace.predict(example.text)  # type: ignore[attr-defined]
    except AttributeError as error:
        raise VwAdapterError("workspace must expose predict(example)") from error
    probabilities = validate_probabilities(actions, raw_scores)
    cumulative = 0.0
    selected_index = -1
    for index, (_, probability) in enumerate(probabilities):
        cumulative += probability
        if draw_value < cumulative:
            selected_index = index
            break
    if selected_index < 0:
        # Validation allows only tiny floating-point error around one.  In that
        # case, a valid draw still belongs to the final non-zero action.
        selected_index = max(
            index for index, (_, probability) in enumerate(probabilities) if probability > 0
        )
    action_id, propensity = probabilities[selected_index]
    return ActionDecision(
        action_id=action_id,
        action_index=selected_index,
        propensity=propensity,
        probabilities=probabilities,
        draw=draw_value,
        example=example,
    )


def adapter_receipt(config: VwConfig = DEFAULT_VW_CONFIG) -> HashedReceipt:
    """Return the canonical identity receipt for upstream and adapter config."""

    payload: dict[str, object] = {
        "schema": ADAPTER_SCHEMA,
        "upstream": {
            "distribution": UPSTREAM_DISTRIBUTION,
            "version": UPSTREAM_VERSION,
            "project_url": UPSTREAM_PROJECT_URL,
        },
        "configuration": {
            "reduction": "cb_explore_adf",
            "arguments": list(config.arguments),
            "argument_string": config.argument_string,
        },
        "feature_encoding": "sha256-tokenized-names-and-categorical-values",
        "action_order": "ascending-action-id",
        "probability_selection": "caller-supplied-external-draw",
        "reward_to_cost": "cost=-terminal_reward",
    }
    canonical = _canonical_json(payload)
    return HashedReceipt(
        canonical_json=canonical,
        sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _file_identity(path: Path) -> tuple[int, str]:
    if not path.is_file():
        raise VwAdapterError(f"policy artifact was not written: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise VwAdapterError("policy artifact must not be empty")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return size, digest


def _policy_receipt_payload(
    *, config: VwConfig, artifact_bytes: int, artifact_sha256: str
) -> dict[str, object]:
    config_receipt = adapter_receipt(config)
    return {
        "schema": POLICY_ARTIFACT_SCHEMA,
        "upstream": {
            "distribution": UPSTREAM_DISTRIBUTION,
            "version": UPSTREAM_VERSION,
        },
        "configuration": {
            "arguments": list(config.arguments),
            "argument_string": config.argument_string,
            "adapter_receipt_sha256": config_receipt.sha256,
        },
        "artifact": {
            "bytes": artifact_bytes,
            "sha256": artifact_sha256,
        },
        "upstream_api": {
            "save": "Workspace.save(PATH)",
            "load": "Workspace(arg_list=[...,--initial_regressor,PATH])",
        },
    }


def save_policy_artifact(
    workspace: object,
    artifact_path: str | Path,
    *,
    config: VwConfig = DEFAULT_VW_CONFIG,
) -> HashedReceipt:
    """Save through upstream VW and return a version/config/byte-bound receipt."""

    path = Path(artifact_path)
    try:
        workspace.save(path)  # type: ignore[attr-defined]
    except AttributeError as error:
        raise VwAdapterError("workspace must expose save(path)") from error
    size, digest = _file_identity(path)
    canonical = _canonical_json(
        _policy_receipt_payload(
            config=config,
            artifact_bytes=size,
            artifact_sha256=digest,
        )
    )
    return HashedReceipt(
        canonical_json=canonical,
        sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _verify_policy_artifact(
    artifact_path: Path,
    receipt: HashedReceipt,
    config: VwConfig,
) -> None:
    measured_receipt_hash = hashlib.sha256(
        receipt.canonical_json.encode("utf-8")
    ).hexdigest()
    if measured_receipt_hash != receipt.sha256:
        raise VwAdapterError("policy receipt SHA-256 mismatch")
    try:
        payload = json.loads(receipt.canonical_json)
    except (json.JSONDecodeError, TypeError) as error:
        raise VwAdapterError("policy receipt is not valid canonical JSON") from error
    if not isinstance(payload, dict):
        raise VwAdapterError("policy receipt must contain a JSON object")
    if payload.get("schema") != POLICY_ARTIFACT_SCHEMA:
        raise VwAdapterError("policy receipt schema mismatch")
    if payload.get("upstream") != {
        "distribution": UPSTREAM_DISTRIBUTION,
        "version": UPSTREAM_VERSION,
    }:
        raise VwAdapterError("policy receipt upstream version mismatch")
    expected_config = _policy_receipt_payload(
        config=config,
        artifact_bytes=0,
        artifact_sha256="",
    )["configuration"]
    if payload.get("configuration") != expected_config:
        raise VwAdapterError("policy receipt configuration mismatch")
    size, digest = _file_identity(artifact_path)
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict):
        raise VwAdapterError("policy receipt lacks artifact identity")
    if artifact.get("bytes") != size:
        raise VwAdapterError("policy artifact byte count mismatch")
    if artifact.get("sha256") != digest:
        raise VwAdapterError("policy artifact SHA-256 mismatch")
    expected_payload = _policy_receipt_payload(
        config=config,
        artifact_bytes=size,
        artifact_sha256=digest,
    )
    if payload != expected_payload:
        raise VwAdapterError("policy receipt content mismatch")


def load_policy_artifact(
    artifact_path: str | Path,
    receipt: HashedReceipt,
    *,
    config: VwConfig = DEFAULT_VW_CONFIG,
) -> object:
    """Verify a saved policy receipt and load it through upstream VW."""

    path = Path(artifact_path)
    _verify_policy_artifact(path, receipt, config)
    workspace_type = _pinned_workspace_type()
    return workspace_type(
        arg_list=[*config.arguments, "--initial_regressor", str(path)]
    )


def _import_vowpalwabbit() -> object:
    import vowpalwabbit

    return vowpalwabbit


def _pinned_workspace_type() -> object:
    try:
        package = _import_vowpalwabbit()
    except ImportError as error:
        raise VwUnavailable(
            'Vowpal Wabbit is required for this controller: pip install -e ".[tfrl-vw]"'
        ) from error
    installed = getattr(package, "__version__", None)
    if installed != UPSTREAM_VERSION:
        raise VwUnavailable(
            f"Vowpal Wabbit {UPSTREAM_VERSION} is required; found {installed!r}"
        )
    try:
        return package.pyvw.Workspace  # type: ignore[attr-defined]
    except AttributeError as error:
        raise VwUnavailable("Vowpal Wabbit does not expose pyvw.Workspace") from error


def create_workspace(config: VwConfig = DEFAULT_VW_CONFIG) -> object:
    """Create the exactly pinned optional VW workspace, failing clearly."""

    workspace_type = _pinned_workspace_type()
    return workspace_type(config.argument_string)


__all__ = [
    "ADAPTER_SCHEMA",
    "POLICY_ARTIFACT_SCHEMA",
    "DEFAULT_VW_CONFIG",
    "ActionDecision",
    "AdfExample",
    "HashedReceipt",
    "LoggedAdfExample",
    "MacroAction",
    "RuntimeState",
    "UPSTREAM_DISTRIBUTION",
    "UPSTREAM_PROJECT_URL",
    "UPSTREAM_VERSION",
    "VwAdapterError",
    "VwConfig",
    "VwUnavailable",
    "adapter_receipt",
    "build_adf_example",
    "build_logged_adf_example",
    "create_workspace",
    "learn_feedback",
    "load_policy_artifact",
    "predict_action",
    "save_policy_artifact",
    "validate_probabilities",
]
