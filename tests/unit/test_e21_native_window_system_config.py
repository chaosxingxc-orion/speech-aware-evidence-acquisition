"""Resolve held E21 configurations through shared admission and role loaders."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import (
    CampaignError, load_campaign_cells,
)
from speech_aware_evidence_acquisition.core.preparation_fit import (
    validate_native_contact_fit_config,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.phase_material import (
    load_phase_material_specs, render_static_instruction, resolve_response_formats,
)

ROOT = Path(__file__).resolve().parents[2]
DIRECT = "e21-native-window-direct-full44-v1"
SYSTEM = "e21-native-window-context-tools-full44-v1"


def _resolved(name):
    cell, = load_campaign_cells(ROOT, name)
    document = cell.document
    config = compose(
        ROOT, document["model_fragment"], document["dataset_fragment"],
        document["baseline_fragment"], name,
    )
    program = default_phase_program(config.values["policy"])
    return cell, config.values, program


@pytest.mark.parametrize("name", (DIRECT, SYSTEM))
def test_held_cells_refuse_actual_contact_stages(name):
    cell, values, _ = _resolved(name)
    cell.assert_mode("check")
    for stage in ("worker", "campaign", "prompt-fit", "prepare-window-features",
                  "prepare-speech-observation-sources"):
        with pytest.raises(CampaignError, match="does not permit"):
            cell.assert_mode(stage)
    assert cell.document["readiness"]["state"] == "held"
    assert values["execution_plan"]["planned_model_calls"] == values["generation_budget"]["cap"]
    assert values["generation_budget"]["ceilings_are_not_targets"] is True


def test_matched_pair_resolves_one_source_and_model_geometry():
    _, direct, _ = _resolved(DIRECT)
    _, system, _ = _resolved(SYSTEM)
    for key in (
        "prepared_execution_units", "prepared_window_feature_packets", "population",
        "decoding_params", "server_args", "server_env", "serving_geometry",
        "runtime_receipt", "feature_encoder_runtime_receipt", "speech_feature_root",
        "task_instruction", "task_contract_source", "scorers", "prompt_fit_multiple",
        "analysis_plan",
    ):
        assert direct[key] == system[key], key
    assert direct["population"]["count"] == 44
    assert direct["prepared_execution_units"]["unit_count"] == 1593
    assert direct["prepared_execution_units"]["split_identity_hash"] == direct["population"]["split_identity_hash"]
    assert direct["decoding_params"]["max_tokens"] == 1024
    assert direct["serving_geometry"] == {"slots": 4, "slot_tokens": 24576, "max_tokens": 1024}
    args = direct["server_args"]
    assert args[args.index("-c") + 1] == "98304"
    assert args[args.index("-np") + 1] == "4"
    assert not any("mmproj" in value for value in args)


def test_direct_program_exposes_no_context_or_tool_route():
    _, values, program = _resolved(DIRECT)
    assert program.phase_names() == ("direct",)
    assert program.max_contacts == 1
    assert program.phases[0].knowledge == "none"
    assert load_native_episode_config(values, program) is None
    assert validate_native_contact_fit_config(values, program) is None
    assert not values.get("phase_tools")
    assert not values.get("knowledge_stores")
    assert not values.get("live_speech_observations")
    assert values["execution_plan"]["planned_model_calls"] == 1593


def test_native_roles_json_planner_and_contact_bounds_are_effective():
    _, values, program = _resolved(SYSTEM)
    native = load_native_episode_config(values, program)
    assert native.max_contacts == 11
    assert native.max_revisions == 1
    assert native.planner_output_format == "json-action-v1"
    assert native.role("reviewer").tool_names == ("saea-tool-live-speech-span-v1",)
    for role in ("solver", "perception", "planner"):
        assert native.role(role).tool_names == ()
    for role in ("perception", "solver"):
        invalid = deepcopy(values)
        invalid["phase_tools"][role] = {
            **invalid["phase_tools"]["reviewer"], "source_authority_role": role,
        }
        with pytest.raises(ValueError, match="only Reviewer and Planner"):
            load_native_episode_config(invalid, program)
    assert values["execution_plan"]["planned_model_calls"] == 1593 * native.max_contacts
    fit = validate_native_contact_fit_config(values, program)
    assert fit["contact_cap"] == 1593 * native.max_contacts * (fit["max_speech_packets"] + 3)
    assert set(values["knowledge_stores"]) == {"participant-roster", "document-lexicon"}
    for store in values["knowledge_stores"].values():
        assert set(store["context_supply"]) == {"solver"}


@pytest.mark.parametrize("name", (DIRECT, SYSTEM))
def test_every_role_renders_and_planner_has_only_implemented_actions(name, tmp_path):
    _, values, program = _resolved(name)
    specs = load_phase_material_specs(values, program)
    for spec in specs.values():
        text = render_static_instruction(spec, ROOT, {}, tmp_path)
        assert text.strip()
        assert text.isascii()
    formats = resolve_response_formats(specs, {}, tmp_path)
    if name == DIRECT:
        assert formats == {}
    else:
        assert set(formats) == {"planner"}
        schema = formats["planner"]["json_schema"]["schema"]
        assert schema["properties"]["action"]["enum"] == ["ACCEPT", "REVISE"]
        assert schema["additionalProperties"] is False


def test_analysis_and_local_tool_plan_are_pinned_without_external_data_reads():
    _, values, _ = _resolved(SYSTEM)
    for binding in (values["analysis_plan"], values["live_speech_observations"]["execution_plan"]):
        path = ROOT / binding["relpath"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["sha256"]
    plan = json.loads((ROOT / values["analysis_plan"]["relpath"]).read_text(encoding="utf-8"))
    budgets = plan["contact_budgets"]
    assert budgets["direct"]["static_fit_endpoint_cap"] == 1 + 3 * 1593
    assert budgets["system"]["live_fit_endpoint_cap"] == values["native_contact_fit"]["contact_cap"]
    assert budgets["local_asr"]["family_call_cap"] == 1593 * 4
