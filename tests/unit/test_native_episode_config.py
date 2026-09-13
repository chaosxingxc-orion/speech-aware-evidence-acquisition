"""Native graph configuration must determine role authority and contact bounds."""

from copy import deepcopy

import pytest

from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    load_native_episode_config,
)


def program(*, ceiling=4, rule="native-role-episode"):
    return PhaseProgram(
        program_id="phase-native-role-test",
        phases=tuple(PhaseSpec(name, name, "none", None, False)
                     for name in ("perception", "reviewer", "planner", "solver")),
        max_contacts=ceiling, stop_rule=rule,
    ).validate()


def config():
    return {"native_episode": {
        "schema": "saea-native-episode-config-v1",
        "episode_id": "native-role-test",
        "max_revisions": 0,
        "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
        "roles": {name: {"phase_id": name, "max_iterations": 1}
                  for name in ("perception", "solver", "reviewer", "planner")},
    }}


def test_absent_default_remains_absent():
    assert load_native_episode_config({}, program(rule="always-run-full-program")) is None
    with pytest.raises(ValueError, match="requires native_episode"):
        load_native_episode_config({}, program())


def test_revision_and_inner_tool_iterations_determine_the_ceiling():
    values = config()
    values["native_episode"]["max_revisions"] = 2
    values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 3
    values["phase_tools"] = {"reviewer": {
        "mode": "native-tools", "source_authority_role": "reviewer",
        "allowed_tools": ["analyze"],
    }}
    # Perception once; each of three rounds has Solver 1 + Reviewer 3 + Planner 1.
    parsed = load_native_episode_config(values, program(ceiling=16))
    assert parsed.max_contacts == 16
    assert parsed.role("reviewer").tool_names == ("analyze",)
    assert parsed.role("solver").tool_names == ()
    with pytest.raises(ValueError, match="ceiling"):
        load_native_episode_config(values, program(ceiling=15))


def test_exhaustion_policy_defaults_to_raise_and_can_opt_in_to_delivery():
    parsed = load_native_episode_config(config(), program())
    assert parsed.exhaustion_policy == "raise"
    assert NativeEpisodeConfig(
        parsed.episode_id,
        parsed.max_revisions,
        parsed.actions,
        parsed.roles,
        parsed.max_contacts,
    ).exhaustion_policy == "raise"

    values = config()
    values["native_episode"]["exhaustion_policy"] = "deliver-latest-solver"
    assert (
        load_native_episode_config(values, program()).exhaustion_policy
        == "deliver-latest-solver"
    )

    values["native_episode"]["exhaustion_policy"] = "unknown"
    with pytest.raises(ValueError, match="exhaustion policy"):
        load_native_episode_config(values, program())


@pytest.mark.parametrize("kind", ["solver", "perception"])
def test_perception_and_solver_cannot_gain_analytical_tool_authority(kind):
    values = config()
    values["phase_tools"] = {kind: {
        "mode": "native-tools", "source_authority_role": kind, "allowed_tools": ["analyze"],
    }}
    with pytest.raises(ValueError, match="only Reviewer and Planner"):
        load_native_episode_config(values, program())


@pytest.mark.parametrize("mutation", [
    lambda v: v["native_episode"].update(max_revisions=True),
    lambda v: v["native_episode"]["actions"].update(revise="ACCEPT"),
    lambda v: v["native_episode"]["roles"]["reviewer"].update(phase_id="solver"),
    lambda v: v["native_episode"]["roles"]["reviewer"].update(max_iterations=0),
    lambda v: v["native_episode"].update(unregistered_mode=True),
    lambda v: v.update(phase_tools={"reviewer": {
        "mode": "native-tools", "source_authority_role": "planner", "allowed_tools": ["analyze"],
    }}),
])
def test_invalid_config_refuses_before_any_runtime_callback(mutation):
    values = deepcopy(config())
    mutation(values)
    with pytest.raises(ValueError):
        load_native_episode_config(values, program())
