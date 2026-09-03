"""Tests for the thin Vowpal Wabbit training-free control-plane adapter."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import tomllib

import pytest

from speech_aware_evidence_acquisition.analysis.training_free_vw_control import (
    DEFAULT_VW_CONFIG,
    MacroAction,
    RuntimeState,
    VwAdapterError,
    VwUnavailable,
    adapter_receipt,
    build_adf_example,
    build_logged_adf_example,
    create_workspace,
    learn_feedback,
    load_policy_artifact,
    predict_action,
    save_policy_artifact,
    validate_probabilities,
)


def _state() -> RuntimeState:
    return RuntimeState(
        numeric={"uncertainty": 0.25, "step": 2},
        categorical={"parse_status": "valid", "speech_mode": "audio"},
    )


def _actions() -> tuple[MacroAction, ...]:
    return (
        MacroAction(
            action_id="resolve",
            numeric={"expected_cost": 1.5},
            categorical={"phase": "use"},
        ),
        MacroAction(
            action_id="query-family:calendar",
            numeric={"expected_cost": 1.0},
            categorical={"phase": "supply"},
        ),
        MacroAction(
            action_id="stop-direct",
            numeric={"expected_cost": 0.0},
            categorical={"phase": "stop"},
        ),
    )


def test_vowpal_wabbit_is_an_exactly_pinned_optional_extra() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["dependencies"] == []
    assert pyproject["project"]["optional-dependencies"]["tfrl-vw"] == [
        "vowpalwabbit==9.11.2"
    ]


def test_build_adf_example_is_canonical_across_input_order() -> None:
    first = build_adf_example(_state(), _actions())
    second = build_adf_example(
        RuntimeState(
            numeric={"step": 2.0, "uncertainty": 0.25},
            categorical={"speech_mode": "audio", "parse_status": "valid"},
        ),
        tuple(reversed(_actions())),
    )

    assert first == second
    assert first.action_ids == (
        "query-family:calendar",
        "resolve",
        "stop-direct",
    )
    assert first.text.startswith("shared |state_numeric ")
    assert first.text.endswith("\n")
    assert len(first.text.splitlines()) == 4
    assert first.sha256 == hashlib.sha256(first.text.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    "field_name",
    ["gold", "gold_score", "reference-transcript", "heldout.test.annotation"],
)
def test_runtime_state_rejects_forbidden_information_keys(field_name: str) -> None:
    state = RuntimeState(numeric={field_name: 1.0})

    with pytest.raises(VwAdapterError, match="forbidden information key"):
        build_adf_example(state, _actions())


def test_feature_values_must_be_finite_and_categorical_values_scalar() -> None:
    with pytest.raises(VwAdapterError, match="finite"):
        build_adf_example(RuntimeState(numeric={"confidence": math.inf}), _actions())
    with pytest.raises(VwAdapterError, match="categorical"):
        build_adf_example(
            RuntimeState(categorical={"status": ["valid"]}),  # type: ignore[dict-item]
            _actions(),
        )


def test_actions_must_be_nonempty_and_uniquely_identified() -> None:
    with pytest.raises(VwAdapterError, match="at least two"):
        build_adf_example(_state(), (_actions()[0],))
    with pytest.raises(VwAdapterError, match="duplicate action_id"):
        build_adf_example(_state(), (_actions()[0], _actions()[0]))


def test_logged_example_encodes_negative_terminal_reward_and_propensity() -> None:
    logged = build_logged_adf_example(
        _state(),
        _actions(),
        chosen_action_id="resolve",
        terminal_reward=0.75,
        propensity=0.2,
    )

    lines = logged.text.splitlines()
    labelled = [line for line in lines if line.startswith("0:-0.75:0.2 ")]
    assert len(labelled) == 1
    assert logged.action_ids[1] == "resolve"
    assert logged.chosen_action_id == "resolve"
    assert logged.cost == -0.75
    assert logged.propensity == 0.2


@pytest.mark.parametrize(
    ("chosen_action_id", "reward", "propensity", "message"),
    [
        ("unknown", 1.0, 0.5, "not available"),
        ("resolve", math.nan, 0.5, "terminal_reward"),
        ("resolve", 1.0, 0.0, "propensity"),
        ("resolve", 1.0, 1.01, "propensity"),
    ],
)
def test_logged_example_refuses_invalid_feedback(
    chosen_action_id: str, reward: float, propensity: float, message: str
) -> None:
    with pytest.raises(VwAdapterError, match=message):
        build_logged_adf_example(
            _state(),
            _actions(),
            chosen_action_id=chosen_action_id,
            terminal_reward=reward,
            propensity=propensity,
        )


def test_probability_validation_normalizes_by_action_index() -> None:
    distribution = validate_probabilities(
        _actions(),
        [
            SimpleNamespace(action=2, score=0.2),
            SimpleNamespace(action=0, score=0.5),
            SimpleNamespace(action=1, score=0.3),
        ],
    )

    assert distribution == (
        ("query-family:calendar", 0.5),
        ("resolve", 0.3),
        ("stop-direct", 0.2),
    )


def test_probability_validation_accepts_upstream_positional_float_vector() -> None:
    distribution = validate_probabilities(_actions(), [0.5, 0.3, 0.2])

    assert distribution == (
        ("query-family:calendar", 0.5),
        ("resolve", 0.3),
        ("stop-direct", 0.2),
    )


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ([(0, 0.5), (1, 0.5)], "exactly one probability"),
        ([(0, 0.5), (1, 0.3), (1, 0.2)], "duplicate action index"),
        ([(0, 0.5), (1, -0.1), (2, 0.6)], "non-negative"),
        ([(0, 0.4), (1, 0.3), (2, 0.2)], "sum to 1"),
        ([(0, 0.5), (1, float("nan")), (2, 0.5)], "finite"),
    ],
)
def test_probability_validation_refuses_malformed_vw_output(
    raw: list[tuple[int, float]], message: str
) -> None:
    with pytest.raises(VwAdapterError, match=message):
        validate_probabilities(_actions(), raw)


class _FakeWorkspace:
    def __init__(self, result: object) -> None:
        self.result = result
        self.examples: list[str] = []

    def predict(self, example: str) -> object:
        self.examples.append(example)
        return self.result


class _FakeLearningWorkspace:
    def __init__(self) -> None:
        self.examples: list[str] = []

    def learn(self, example: str) -> None:
        self.examples.append(example)


def test_learn_feedback_builds_one_logged_example_and_delegates_to_upstream() -> None:
    workspace = _FakeLearningWorkspace()

    logged = learn_feedback(
        workspace,
        _state(),
        _actions(),
        chosen_action_id="resolve",
        terminal_reward=1.0,
        propensity=0.3,
    )

    assert workspace.examples == [logged.text]
    assert logged.chosen_action_id == "resolve"
    assert logged.cost == -1.0
    assert logged.propensity == 0.3


def test_learn_feedback_requires_the_upstream_learn_api() -> None:
    with pytest.raises(VwAdapterError, match="learn"):
        learn_feedback(
            object(),
            _state(),
            _actions(),
            chosen_action_id="resolve",
            terminal_reward=1.0,
            propensity=0.3,
        )


def test_predict_action_returns_full_distribution_and_logged_propensity() -> None:
    workspace = _FakeWorkspace([(0, 0.1), (1, 0.7), (2, 0.2)])

    decision = predict_action(workspace, _state(), _actions(), draw=0.65)

    assert decision.action_id == "resolve"
    assert decision.action_index == 1
    assert decision.propensity == 0.7
    assert decision.probabilities == (
        ("query-family:calendar", 0.1),
        ("resolve", 0.7),
        ("stop-direct", 0.2),
    )
    assert workspace.examples == [decision.example.text]
    payload = json.loads(decision.canonical_json)
    assert payload["action_id"] == "resolve"
    assert payload["example_sha256"] == decision.example.sha256
    assert decision.sha256 == hashlib.sha256(
        decision.canonical_json.encode("utf-8")
    ).hexdigest()


@pytest.mark.parametrize("draw", [-0.1, 1.0, math.nan])
def test_predict_action_refuses_invalid_external_draw(draw: float) -> None:
    workspace = _FakeWorkspace([(0, 0.1), (1, 0.7), (2, 0.2)])
    with pytest.raises(VwAdapterError, match="draw"):
        predict_action(workspace, _state(), _actions(), draw=draw)


def test_adapter_receipt_pins_upstream_and_exact_configuration() -> None:
    receipt = adapter_receipt()
    payload = json.loads(receipt.canonical_json)

    assert payload["schema"] == "saea-training-free-vw-control-adapter-v1"
    assert payload["upstream"] == {
        "distribution": "vowpalwabbit",
        "project_url": "https://github.com/VowpalWabbit/vowpal_wabbit",
        "version": "9.11.2",
    }
    assert payload["configuration"]["arguments"] == list(DEFAULT_VW_CONFIG.arguments)
    assert payload["configuration"]["reduction"] == "cb_explore_adf"
    assert payload["reward_to_cost"] == "cost=-terminal_reward"
    assert receipt.sha256 == hashlib.sha256(receipt.canonical_json.encode()).hexdigest()


def test_default_config_makes_contextual_learning_explicit() -> None:
    arguments = DEFAULT_VW_CONFIG.arguments

    assert arguments[arguments.index("--cb_type") + 1] == "dr"
    assert arguments[arguments.index("--quadratic") + 1] == "sa"


def test_create_workspace_has_clear_missing_extra_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import speech_aware_evidence_acquisition.analysis.training_free_vw_control as module

    def missing() -> object:
        raise ImportError("not installed")

    monkeypatch.setattr(module, "_import_vowpalwabbit", missing)

    with pytest.raises(VwUnavailable, match=r"\[tfrl-vw\]"):
        create_workspace()


def test_create_workspace_refuses_unpinned_runtime_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import speech_aware_evidence_acquisition.analysis.training_free_vw_control as module

    fake = SimpleNamespace(
        __version__="9.10.0",
        pyvw=SimpleNamespace(Workspace=lambda arguments: arguments),
    )
    monkeypatch.setattr(module, "_import_vowpalwabbit", lambda: fake)

    with pytest.raises(VwUnavailable, match="9.11.2"):
        create_workspace()


def test_create_workspace_passes_the_exact_pinned_argument_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import speech_aware_evidence_acquisition.analysis.training_free_vw_control as module

    received: list[str] = []
    fake = SimpleNamespace(
        __version__="9.11.2",
        pyvw=SimpleNamespace(Workspace=lambda arguments: received.append(arguments) or object()),
    )
    monkeypatch.setattr(module, "_import_vowpalwabbit", lambda: fake)

    workspace = create_workspace()

    assert workspace is not None
    assert received == [DEFAULT_VW_CONFIG.argument_string]


class _FakeSavingWorkspace:
    def __init__(self, policy_bytes: bytes) -> None:
        self.policy_bytes = policy_bytes
        self.saved_paths: list[Path] = []

    def save(self, filename: str | Path) -> None:
        path = Path(filename)
        self.saved_paths.append(path)
        path.write_bytes(self.policy_bytes)


def test_save_policy_artifact_uses_upstream_save_and_binds_bytes_version_and_config(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "controller.vw"
    workspace = _FakeSavingWorkspace(b"pinned-vw-policy")

    receipt = save_policy_artifact(workspace, artifact_path)
    payload = json.loads(receipt.canonical_json)

    assert workspace.saved_paths == [artifact_path]
    assert payload["schema"] == "saea-training-free-vw-policy-artifact-v1"
    assert payload["upstream"] == {
        "distribution": "vowpalwabbit",
        "version": "9.11.2",
    }
    assert payload["configuration"]["arguments"] == list(DEFAULT_VW_CONFIG.arguments)
    assert payload["configuration"]["adapter_receipt_sha256"] == adapter_receipt().sha256
    assert payload["artifact"] == {
        "bytes": len(b"pinned-vw-policy"),
        "sha256": hashlib.sha256(b"pinned-vw-policy").hexdigest(),
    }
    assert payload["upstream_api"] == {
        "load": "Workspace(arg_list=[...,--initial_regressor,PATH])",
        "save": "Workspace.save(PATH)",
    }
    assert receipt.sha256 == hashlib.sha256(receipt.canonical_json.encode()).hexdigest()


def test_save_policy_artifact_requires_upstream_save(tmp_path: Path) -> None:
    with pytest.raises(VwAdapterError, match="save"):
        save_policy_artifact(object(), tmp_path / "controller.vw")


def test_load_policy_artifact_verifies_receipt_then_uses_initial_regressor_arg_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import speech_aware_evidence_acquisition.analysis.training_free_vw_control as module

    artifact_path = tmp_path / "controller.vw"
    receipt = save_policy_artifact(
        _FakeSavingWorkspace(b"verified-policy"), artifact_path
    )
    received: list[list[str]] = []
    loaded_workspace = object()

    def workspace_type(*, arg_list: list[str]) -> object:
        received.append(arg_list)
        return loaded_workspace

    fake = SimpleNamespace(
        __version__="9.11.2",
        pyvw=SimpleNamespace(Workspace=workspace_type),
    )
    monkeypatch.setattr(module, "_import_vowpalwabbit", lambda: fake)

    loaded = load_policy_artifact(artifact_path, receipt)

    assert loaded is loaded_workspace
    assert received == [
        [
            *DEFAULT_VW_CONFIG.arguments,
            "--initial_regressor",
            str(artifact_path),
        ]
    ]


def test_load_policy_artifact_refuses_byte_drift_before_importing_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import speech_aware_evidence_acquisition.analysis.training_free_vw_control as module

    artifact_path = tmp_path / "controller.vw"
    receipt = save_policy_artifact(_FakeSavingWorkspace(b"original"), artifact_path)
    artifact_path.write_bytes(b"tampered")
    imported = False

    def unexpected_import() -> object:
        nonlocal imported
        imported = True
        raise AssertionError("runtime import must follow artifact verification")

    monkeypatch.setattr(module, "_import_vowpalwabbit", unexpected_import)

    with pytest.raises(VwAdapterError, match="artifact SHA-256 mismatch"):
        load_policy_artifact(artifact_path, receipt)

    assert imported is False


def test_load_policy_artifact_refuses_configuration_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import speech_aware_evidence_acquisition.analysis.training_free_vw_control as module

    artifact_path = tmp_path / "controller.vw"
    receipt = save_policy_artifact(_FakeSavingWorkspace(b"original"), artifact_path)
    imported = False

    def unexpected_import() -> object:
        nonlocal imported
        imported = True
        raise AssertionError("runtime import must follow receipt verification")

    monkeypatch.setattr(module, "_import_vowpalwabbit", unexpected_import)
    drifted = type(DEFAULT_VW_CONFIG)(
        arguments=(*DEFAULT_VW_CONFIG.arguments[:-2], "20260904", "--quiet")
    )

    with pytest.raises(VwAdapterError, match="configuration mismatch"):
        load_policy_artifact(artifact_path, receipt, config=drifted)

    assert imported is False


def test_load_policy_artifact_refuses_receipt_self_hash_drift(tmp_path: Path) -> None:
    artifact_path = tmp_path / "controller.vw"
    receipt = save_policy_artifact(_FakeSavingWorkspace(b"original"), artifact_path)
    drifted = type(receipt)(receipt.canonical_json, "0" * 64)

    with pytest.raises(VwAdapterError, match="receipt SHA-256 mismatch"):
        load_policy_artifact(artifact_path, drifted)


def test_load_policy_artifact_refuses_rehashed_receipt_content_drift(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "controller.vw"
    receipt = save_policy_artifact(_FakeSavingWorkspace(b"original"), artifact_path)
    payload = json.loads(receipt.canonical_json)
    payload["upstream_api"]["load"] = "local-loader"
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    drifted = type(receipt)(
        canonical,
        hashlib.sha256(canonical.encode()).hexdigest(),
    )

    with pytest.raises(VwAdapterError, match="receipt content mismatch"):
        load_policy_artifact(artifact_path, drifted)
