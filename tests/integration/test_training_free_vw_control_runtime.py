"""Real-runtime check for the pinned optional Vowpal Wabbit boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

vowpalwabbit = pytest.importorskip(
    "vowpalwabbit", reason="the pinned optional tfrl-vw extra is not installed"
)

from speech_aware_evidence_acquisition.analysis.training_free_vw_control import (  # noqa: E402
    MacroAction,
    RuntimeState,
    create_workspace,
    learn_feedback,
    load_policy_artifact,
    predict_action,
    save_policy_artifact,
)


pytestmark = pytest.mark.requires_tfrl_vw


def _actions() -> tuple[MacroAction, MacroAction]:
    return (
        MacroAction("left"),
        MacroAction("right"),
    )


def _state(context: str) -> RuntimeState:
    return RuntimeState(categorical={"context": context})


def test_two_context_learn_save_load_predict_round_trip(tmp_path: Path) -> None:
    assert vowpalwabbit.__version__ == "9.11.2"
    actions = _actions()
    workspace = create_workspace()
    loaded = None
    try:
        for _ in range(80):
            for context, preferred in (("alpha", "left"), ("beta", "right")):
                for chosen in ("left", "right"):
                    learn_feedback(
                        workspace,
                        _state(context),
                        actions,
                        chosen_action_id=chosen,
                        terminal_reward=float(chosen == preferred),
                        propensity=0.5,
                    )

        artifact_path = tmp_path / "controller.vw"
        receipt = save_policy_artifact(workspace, artifact_path)
        loaded = load_policy_artifact(artifact_path, receipt)

        alpha = dict(
            predict_action(loaded, _state("alpha"), actions, draw=0.0).probabilities
        )
        beta = dict(
            predict_action(loaded, _state("beta"), actions, draw=0.0).probabilities
        )

        assert alpha["left"] > alpha["right"]
        assert beta["right"] > beta["left"]
    finally:
        if loaded is not None:
            loaded.finish()
        workspace.finish()
