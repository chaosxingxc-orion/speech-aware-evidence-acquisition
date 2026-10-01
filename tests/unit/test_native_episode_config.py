"""Native graph configuration must determine role authority and contact bounds."""

from copy import deepcopy
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import RESPONSE_FORMATS
from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    load_native_episode_config,
)


def program(*, ceiling=4, rule="native-role-episode", planner_format=None):
    return PhaseProgram(
        program_id="phase-native-role-test",
        phases=tuple(PhaseSpec(
            name, name, "none",
            planner_format if name == "planner" else None,
            False,
        )
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


def test_json_planner_output_requires_registered_planner_phase_format():
    values = config()
    values["native_episode"]["planner_output_format"] = "json-action-v1"
    with pytest.raises(ValueError, match="registered Planner phase response format"):
        load_native_episode_config(values, program())

    parsed = load_native_episode_config(
        values,
        program(planner_format="saea-native-planner-action-v1"),
    )
    assert parsed.planner_output_format == "json-action-v1"

    values["native_episode"]["planner_output_format"] = "unregistered"
    with pytest.raises(ValueError, match="Planner output format"):
        load_native_episode_config(values, program())


def test_registered_json_planner_format_uses_configured_action_enum():
    builder = RESPONSE_FORMATS.resolve("saea-native-planner-action-v1")
    response_format = builder(
        {}, Path("."), actions=["ACCEPT", "REVISE", "ACQUIRE"]
    )
    assert response_format == {
        "type": "json_schema",
        "json_schema": {
            "name": "saea_native_planner_action_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["ACCEPT", "REVISE", "ACQUIRE"],
                    }
                },
            },
        },
    }


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


# ---------------------------------------------------------------------------
# E1: review loop off (M0). Reviewer and Planner may declare max_iterations 0
# only together and only with max_revisions 0; every other shape -- including
# either role alone at 0 -- stays refused exactly as before.
# ---------------------------------------------------------------------------


def test_review_loop_off_accepts_reviewer_planner_and_revisions_all_zero():
    values = config()
    values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 0
    values["native_episode"]["roles"]["planner"]["max_iterations"] = 0

    parsed = load_native_episode_config(values, program(ceiling=2))

    assert parsed.max_contacts == 2
    assert parsed.review_loop_enabled is False
    assert parsed.role("reviewer").max_iterations == 0
    assert parsed.role("planner").max_iterations == 0
    assert parsed.role("reviewer").tool_names == ()
    assert parsed.role("planner").tool_names == ()
    # Perception and Solver are untouched by the pairing.
    assert parsed.role("perception").max_iterations == 1
    assert parsed.role("solver").max_iterations == 1


def test_review_loop_enabled_defaults_true_for_the_ordinary_positive_shape():
    assert load_native_episode_config(config(), program()).review_loop_enabled is True


@pytest.mark.parametrize("mutation", [
    # Reviewer alone at 0, Planner stays positive.
    lambda v: v["native_episode"]["roles"]["reviewer"].update(max_iterations=0),
    # Planner alone at 0, Reviewer stays positive.
    lambda v: v["native_episode"]["roles"]["planner"].update(max_iterations=0),
    # Both roles at 0 but a nonzero revision allowance left with nothing to
    # spend it on.
    lambda v: (
        v["native_episode"]["roles"]["reviewer"].update(max_iterations=0),
        v["native_episode"]["roles"]["planner"].update(max_iterations=0),
        v["native_episode"].update(max_revisions=1),
    ),
])
def test_review_loop_off_refuses_every_partial_shape(mutation):
    values = config()
    mutation(values)
    with pytest.raises(
        ValueError,
        match="review loop off requires reviewer 0, planner 0 and max_revisions 0",
    ):
        load_native_episode_config(values, program(ceiling=2))


def test_review_loop_off_ceiling_is_exactly_two():
    values = config()
    values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 0
    values["native_episode"]["roles"]["planner"]["max_iterations"] = 0

    assert load_native_episode_config(values, program(ceiling=2)).max_contacts == 2
    with pytest.raises(ValueError, match="ceiling"):
        load_native_episode_config(values, program(ceiling=3))


# E2 (SLURP v2 base program M2): grouped Solver sampling
# (docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md
# section 4, item M2).
# ---------------------------------------------------------------------------

VALID_OVERRIDES = {"temperature": 0.7, "seed_offset": 0}
VALID_COMMIT = {
    "policy": "saea-commit-plurality-support-v1",
    "min_support": 3,
    "similarity_threshold": 0.8,
}


def test_solver_samples_defaults_to_one_and_carries_no_sampling_fields():
    parsed = load_native_episode_config(config(), program())
    solver = parsed.role("solver")
    assert solver.samples == 1
    assert solver.decoding_overrides is None
    assert solver.commit is None


def test_anchor_config_ceiling_is_unchanged_by_the_new_field():
    """The exact anchor config from ``config()`` must still validate at the
    historical ceiling -- samples 1 is byte-identical to today's behaviour."""

    values = config()
    values["native_episode"]["max_revisions"] = 2
    values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 3
    values["phase_tools"] = {"reviewer": {
        "mode": "native-tools", "source_authority_role": "reviewer",
        "allowed_tools": ["analyze"],
    }}
    parsed = load_native_episode_config(values, program(ceiling=16))
    assert parsed.max_contacts == 16


def test_grouped_solver_ceiling_multiplies_only_the_solver_contribution():
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = VALID_OVERRIDES
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    # perception 1 + (0 + 1) * (reviewer 1 + planner 1 + solver 1 * 5) = 8
    parsed = load_native_episode_config(values, program(ceiling=8))
    assert parsed.max_contacts == 8
    assert parsed.role("solver").samples == 5
    assert parsed.role("solver").decoding_overrides == VALID_OVERRIDES
    assert parsed.role("solver").commit == VALID_COMMIT
    with pytest.raises(ValueError, match="ceiling"):
        load_native_episode_config(values, program(ceiling=7))


def test_grouped_solver_ceiling_multiplies_across_every_revision():
    values = config()
    values["native_episode"]["max_revisions"] = 2
    values["native_episode"]["roles"]["solver"]["samples"] = 3
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = {
        "temperature": 1.0, "seed_offset": 7,
    }
    values["native_episode"]["roles"]["solver"]["commit"] = {
        "policy": "saea-commit-plurality-support-v1", "min_support": 2, "similarity_threshold": 0.8,
    }
    # perception 1 + (2 + 1) * (reviewer 1 + planner 1 + solver 1 * 3) = 1 + 15 = 16
    parsed = load_native_episode_config(values, program(ceiling=16))
    assert parsed.max_contacts == 16


def test_only_solver_role_may_declare_grouped_sampling_fields():
    values = config()
    values["native_episode"]["roles"]["reviewer"]["samples"] = 2
    with pytest.raises(ValueError, match="phase_id and max_iterations"):
        load_native_episode_config(values, program())


@pytest.mark.parametrize("samples", [0, -1, 9, True, 1.5, "5"])
def test_solver_samples_must_be_a_bounded_integer(samples):
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = samples
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = VALID_OVERRIDES
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    with pytest.raises(ValueError):
        load_native_episode_config(values, program(ceiling=100))


def test_decoding_overrides_requires_samples_at_least_two():
    values = config()
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = VALID_OVERRIDES
    with pytest.raises(ValueError, match="samples >= 2"):
        load_native_episode_config(values, program())


def test_commit_is_forbidden_when_samples_is_one():
    values = config()
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    with pytest.raises(ValueError, match="samples == 1"):
        load_native_episode_config(values, program())


def test_samples_at_least_two_requires_decoding_overrides_and_commit():
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    with pytest.raises(ValueError, match="decoding_overrides"):
        load_native_episode_config(values, program(ceiling=100))
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = VALID_OVERRIDES
    with pytest.raises(ValueError, match="commit"):
        load_native_episode_config(values, program(ceiling=100))


@pytest.mark.parametrize("overrides", [
    {"temperature": 0.7},
    {"seed_offset": 0},
    {"temperature": 0.7, "seed_offset": 0, "extra": 1},
    {"temperature": 0, "seed_offset": 0},
    {"temperature": 2.1, "seed_offset": 0},
    {"temperature": True, "seed_offset": 0},
    {"temperature": 0.7, "seed_offset": -1},
    {"temperature": 0.7, "seed_offset": True},
    {"temperature": 0.7, "seed_offset": 1.0},
])
def test_decoding_overrides_shape_and_ranges_are_enforced(overrides):
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = overrides
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    with pytest.raises(ValueError, match="decoding_overrides"):
        load_native_episode_config(values, program(ceiling=100))


@pytest.mark.parametrize("commit", [
    {"policy": "saea-commit-plurality-support-v1", "min_support": 3},
    {"policy": "saea-commit-plurality-support-v1", "min_support": 3, "similarity_threshold": 0.8, "extra": 1},
    {"policy": "", "min_support": 3, "similarity_threshold": 0.8},
    {"policy": "saea-commit-plurality-support-v1", "min_support": 0, "similarity_threshold": 0.8},
    {"policy": "saea-commit-plurality-support-v1", "min_support": 6, "similarity_threshold": 0.8},
    {"policy": "saea-commit-plurality-support-v1", "min_support": True, "similarity_threshold": 0.8},
    {"policy": "saea-commit-plurality-support-v1", "min_support": 3, "similarity_threshold": 0.0},
    {"policy": "saea-commit-plurality-support-v1", "min_support": 3, "similarity_threshold": 1.1},
    {"policy": "unknown-commit-policy", "min_support": 3, "similarity_threshold": 0.8},
])
def test_commit_shape_and_ranges_are_enforced(commit):
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = VALID_OVERRIDES
    values["native_episode"]["roles"]["solver"]["commit"] = commit
    with pytest.raises(ValueError):
        load_native_episode_config(values, program(ceiling=100))


# ---------------------------------------------------------------------------
# E2b (SLURP v2 base program M2 live wiring): the explicit greedy-repeat
# twin (docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md
# section 4, item E2: "N greedy repeats aggregated identically"). Every
# samples>=2 config above keeps E2's original temperature-in-(0, 2]
# requirement; only a role that ALSO declares twin: "greedy-repeat" may set
# temperature 0.
# ---------------------------------------------------------------------------


def test_temperature_zero_is_refused_without_a_declared_twin():
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = {
        "temperature": 0.0, "seed_offset": 0,
    }
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    with pytest.raises(ValueError, match="temperature"):
        load_native_episode_config(values, program(ceiling=8))


def test_temperature_zero_is_admitted_by_an_explicit_greedy_repeat_twin():
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = {
        "temperature": 0.0, "seed_offset": 0,
    }
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    values["native_episode"]["roles"]["solver"]["twin"] = "greedy-repeat"
    parsed = load_native_episode_config(values, program(ceiling=8))
    solver = parsed.role("solver")
    assert solver.twin == "greedy-repeat"
    assert solver.decoding_overrides["temperature"] == 0.0


def test_twin_still_enforces_the_upper_temperature_bound():
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = {
        "temperature": 2.5, "seed_offset": 0,
    }
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    values["native_episode"]["roles"]["solver"]["twin"] = "greedy-repeat"
    with pytest.raises(ValueError, match="temperature"):
        load_native_episode_config(values, program(ceiling=8))


def test_twin_requires_samples_at_least_two():
    values = config()
    values["native_episode"]["roles"]["solver"]["twin"] = "greedy-repeat"
    with pytest.raises(ValueError, match="samples >= 2"):
        load_native_episode_config(values, program())


@pytest.mark.parametrize("twin", ["", "bogus", "greedy_repeat", 1, True])
def test_twin_rejects_any_value_other_than_greedy_repeat(twin):
    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = VALID_OVERRIDES
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    values["native_episode"]["roles"]["solver"]["twin"] = twin
    with pytest.raises(ValueError, match="greedy-repeat"):
        load_native_episode_config(values, program(ceiling=8))


def test_twin_may_be_declared_alongside_a_positive_temperature():
    """twin is a custody label, not itself a temperature constraint: a
    samples>=2 role may declare twin: 'greedy-repeat' with T > 0 too (the
    field only ever RELAXES the lower bound, from > 0 to >= 0)."""

    values = config()
    values["native_episode"]["roles"]["solver"]["samples"] = 5
    values["native_episode"]["roles"]["solver"]["decoding_overrides"] = VALID_OVERRIDES
    values["native_episode"]["roles"]["solver"]["commit"] = VALID_COMMIT
    values["native_episode"]["roles"]["solver"]["twin"] = "greedy-repeat"
    parsed = load_native_episode_config(values, program(ceiling=8))
    assert parsed.role("solver").twin == "greedy-repeat"
    assert parsed.role("solver").decoding_overrides["temperature"] == 0.7


def test_only_solver_role_may_declare_a_twin():
    values = config()
    values["native_episode"]["roles"]["reviewer"]["twin"] = "greedy-repeat"
    with pytest.raises(ValueError, match="phase_id and max_iterations"):
        load_native_episode_config(values, program())


def test_slot_review_handoff_is_explicit_and_closed():
    values = config()
    assert load_native_episode_config(values, program()).review_handoff is None
    values["native_episode"]["review_handoff"] = "slot-issues-v1"
    assert load_native_episode_config(values, program()).review_handoff == "slot-issues-v1"
    values["native_episode"]["review_handoff"] = "infer-answer"
    with pytest.raises(ValueError, match="review_handoff"):
        load_native_episode_config(values, program())
