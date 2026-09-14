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


def test_finite_completion_policy_defaults_to_raise_and_can_deliver_or_abstain():
    parsed = load_native_episode_config(config(), program())
    assert parsed.finite_completion_policy == "raise"

    values = config()
    values["native_episode"]["finite_completion_policy"] = "deliver-latest-or-abstain"
    assert (
        load_native_episode_config(values, program()).finite_completion_policy
        == "deliver-latest-or-abstain"
    )


@pytest.mark.parametrize(
    "invalid",
    [True, False, None, 1, {}, [], "", "deliver-latest-solver", "unknown"],
)
def test_finite_completion_policy_rejects_invalid_types_and_values(invalid):
    values = config()
    values["native_episode"]["finite_completion_policy"] = invalid
    with pytest.raises(ValueError, match="finite completion policy"):
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


def test_candidate_refresh_opt_in_counts_extra_perception_without_changing_legacy():
    legacy = load_native_episode_config(config(), program())
    assert legacy.refresh_action is None
    assert legacy.max_candidate_refreshes == 0
    assert legacy.terminal_actions == ("REVISE", "ACQUIRE")
    values = config()
    values["native_episode"]["max_revisions"] = 2
    values["native_episode"]["roles"]["perception"]["max_iterations"] = 2
    values["native_episode"]["candidate_refresh"] = {
        "action": "REFRESH_CANDIDATES", "max_refreshes": 1,
    }
    # Initial Perception 2 + three rounds of 3 + one refreshed Perception 2.
    parsed = load_native_episode_config(values, program(ceiling=13))
    assert parsed.max_contacts == 13
    assert parsed.refresh_action == "REFRESH_CANDIDATES"
    assert parsed.max_candidate_refreshes == 1
    assert parsed.terminal_actions == ("REVISE", "ACQUIRE", "REFRESH_CANDIDATES")
    with pytest.raises(ValueError, match="ceiling"):
        load_native_episode_config(values, program(ceiling=11))


@pytest.mark.parametrize("refresh", [
    {}, {"action": "REFRESH", "max_refreshes": 0},
    {"action": "REFRESH", "max_refreshes": True},
    {"action": "REFRESH", "max_refreshes": 2},
    {"action": "REVISE", "max_refreshes": 1},
    {"action": " ", "max_refreshes": 1},
])
def test_invalid_candidate_refresh_is_rejected_before_runtime(refresh):
    values = config()
    values["native_episode"]["max_revisions"] = 1
    values["native_episode"]["candidate_refresh"] = refresh
    with pytest.raises(ValueError, match="candidate_refresh"):
        load_native_episode_config(values, program(ceiling=8))


def test_refresh_rejects_stale_candidate_supply_binding_before_any_contact():
    values = config()
    values["native_episode"]["max_revisions"] = 1
    values["native_episode"]["candidate_refresh"] = {
        "action": "REFRESH_CANDIDATES", "max_refreshes": 1,
    }
    supply = {"candidate_state_phase": "perception"}
    values["knowledge_stores"] = {"slot-contracts": {"candidate_supply": {"solver": supply}}}
    with pytest.raises(ValueError, match="latest candidate source selection"):
        load_native_episode_config(values, program(ceiling=8))
    supply["candidate_state_selection"] = "latest"
    assert load_native_episode_config(values, program(ceiling=8)).refresh_action


def test_held_refresh_tools_fragment_uses_distinct_program_and_reviewer_tools_only():
    import hashlib
    import json
    from pathlib import Path
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.phase_material import load_phase_material_specs
    from speech_aware_evidence_acquisition.rails.phase_tools import load_phase_tool_specs

    root = Path(__file__).resolve().parents[2]
    fragment = json.loads((
        root / "configs/baseline/slurp-native-candidate-refresh-tools-train-fold-a-held-v1.json"
    ).read_text())
    incumbent = default_phase_program("phase-native-candidates-review-revise-v1")
    successor = default_phase_program(fragment["policy"])
    assert successor.program_id != incumbent.program_id
    assert incumbent.max_contacts == 11
    assert successor.max_contacts == 12
    parsed = load_native_episode_config(fragment, successor)
    assert parsed.max_candidate_refreshes == 1
    assert parsed.max_contacts == 12
    assert set(load_phase_tool_specs(fragment, successor)) == {"reviewer"}
    assert parsed.role("perception").tool_names == parsed.role("solver").tool_names == ()
    assert "saea-tool-live-speech-observation-v1" in parsed.role("reviewer").tool_names
    assert parsed.role("reviewer").max_iterations == 3
    assert set(load_phase_material_specs(fragment, successor)) == set(successor.phase_names())
    templates = json.loads((root / "configs/probes/manifest.json").read_text())["templates"]
    for spec in fragment["phase_material"].values():
        template_path = root / "configs" / spec["instruction_template"]
        assert hashlib.sha256(template_path.read_bytes()).hexdigest() == templates[template_path.name]["sha256"]
    assert fragment["prospective_candidate_refresh_tools"]["new_model_contacts_authorized"] is False
    assert "native_contact_fit" not in fragment
    assert "live_speech_observations" not in fragment


def test_local_tool_execution_is_explicit_and_bounded():
    values = config()
    assert load_native_episode_config(values, program()).local_tool_workers == 0
    values["native_episode"]["local_tool_execution"] = {
        "mode": "yield-model-slot", "max_workers": 1,
    }
    assert load_native_episode_config(values, program()).local_tool_workers == 1


@pytest.mark.parametrize("bad", [
    None, {}, {"mode": "yield-model-slot"},
    {"mode": "fixed", "max_workers": 1},
    {"mode": "yield-model-slot", "max_workers": True},
    {"mode": "yield-model-slot", "max_workers": 0},
    {"mode": "yield-model-slot", "max_workers": 9},
    {"mode": "yield-model-slot", "max_workers": 1, "extra": 1},
])
def test_local_tool_execution_rejects_unbound_resource_policy(bad):
    values = config()
    values["native_episode"]["local_tool_execution"] = bad
    with pytest.raises(ValueError, match="local_tool_execution"):
        load_native_episode_config(values, program())


@pytest.mark.parametrize("invalid", [None, False, 1, "auto", {}, []])
def test_final_report_policy_rejects_unknown_explicit_value(invalid):
    values = config()
    values["native_episode"]["tool_iteration_policy"] = invalid
    with pytest.raises(ValueError, match="tool_iteration_policy"):
        load_native_episode_config(values, program())


def test_final_report_policy_is_opt_in_and_requires_a_report_turn():
    values = config()
    assert not load_native_episode_config(values, program()).reserve_final_report
    values["native_episode"]["tool_iteration_policy"] = "reserve-final-report"
    values["phase_tools"] = {"reviewer": {
        "mode": "native-tools", "source_authority_role": "reviewer", "allowed_tools": ["analyze"],
    }}
    with pytest.raises(ValueError, match="two tool-role iterations"):
        load_native_episode_config(values, program())
    values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 3
    assert load_native_episode_config(values, program(ceiling=6)).reserve_final_report
