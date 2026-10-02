"""Opt-in strict Reviewer output uses the existing material and native runner."""
import copy
import json
from dataclasses import replace
from pathlib import Path

import jsonschema
import pytest

from speech_aware_evidence_acquisition.core.base import RESPONSE_FORMATS
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks
from speech_aware_evidence_acquisition.rails.review_handoff import normalize_review_handoff
from speech_aware_evidence_acquisition.rails.phase_material import load_phase_material_specs, resolve_response_formats
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

FORMAT = "saea-slot-review-handoff-v1"
PROGRAM = "phase-native-slot-review-contract-v1"
REPO = Path(__file__).resolve().parents[2]


def block():
    value = json.loads((REPO / "configs/baseline/slurp-native-stage3-system-text-update2-l-parent-recovery1-v1.json").read_text())
    return copy.deepcopy(value["native_episode"]["consumption_module"])


def enable(value):
    component = next(c for c in value["components"] if c["component_id"] == "knowledge-consumption-opportunity")
    component["params"]["reviewer_response_format_id"] = FORMAT
    return component


def schema():
    return RESPONSE_FORMATS.resolve(FORMAT)({}, Path("."))["json_schema"]["schema"]


def test_strict_schema_accepts_empty_and_bounded_doubt():
    finding = {"kind": "boundary", "slot_types": ["date"], "draft_fragment": "tomorrow", "reason": "Uncertain boundary"}
    for response in [{"findings": [], "checked": []}, {"findings": [finding], "checked": ["current draft"]}]:
        jsonschema.validate(response, schema())
        assert json.loads(normalize_review_handoff(json.dumps(response)))["status"] == "valid"


@pytest.mark.parametrize("bad", [
    {"findings": [], "checked": [], "answer": "x"},
    {"findings": [{"kind": "boundary", "slot_types": ["date"], "draft_fragment": "", "reason": "x", "checked": []}], "checked": []},
    {"findings": [], "checked": ["x"] * 9},
    {"findings": [{"kind": "answer", "slot_types": ["date"], "draft_fragment": "", "reason": "x"}], "checked": []},
    {"findings": [{"kind": "existence", "slot_types": [], "draft_fragment": "", "reason": "x"}], "checked": []},
    {"findings": [{"kind": "existence", "slot_types": ["a", "b", "c"], "draft_fragment": "", "reason": "x"}], "checked": []},
    {"findings": [{"kind": "existence", "slot_types": ["date"], "draft_fragment": "", "reason": "x" * 513}], "checked": []},
    {"findings": [], "checked": ["x" * 257]},
    {"findings": [None], "checked": []},
])
def test_schema_refuses_observed_and_boundary_defects(bad):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema())


def test_compiler_opt_in_reaches_same_material_path_without_changing_old_requests():
    original = block()
    before = cm.compile_module(original, carrier_module_hooks()).values()
    updated = copy.deepcopy(original)
    enable(updated)
    values = cm.compile_module(updated, carrier_module_hooks()).values()
    program = rc.default_phase_program(values["policy"])
    assert values["policy"] == PROGRAM
    assert program.max_contacts == 13
    assert program.phase("reviewer").response_format_id == FORMAT
    assert values["phase_material"]["reviewer"]["response_format_id"] == FORMAT
    load_native_episode_config({**values, "carrier_lock_key": "slurp"}, program)
    specs = load_phase_material_specs(values, program)
    formats = resolve_response_formats({"reviewer": specs["reviewer"]}, {}, Path("."))
    assert formats["reviewer"]["json_schema"]["strict"] is True
    assert formats["reviewer"]["json_schema"]["schema"] == schema()
    for key in ["knowledge_stores", "phase_tools", "native_episode"]:
        assert values[key] == before[key]
    restored = copy.deepcopy(values)
    restored["policy"] = before["policy"]
    restored["phase_material"]["reviewer"]["response_format_id"] = None
    assert restored == before
    assert cm.compile_module(original, carrier_module_hooks()).values() == before


def test_unknown_contract_fails_closed():
    b = block()
    enable(b)["params"]["reviewer_response_format_id"] = "invented"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="Reviewer"):
        cm.compile_module(b, carrier_module_hooks())


def test_old_parser_remains_strict_and_raw_fences_are_not_salvaged():
    assert json.loads(normalize_review_handoff('```json\n{"findings":[],"checked":[]}\n```'))["status"] == "invalid"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_native_wire_carries_reviewer_contract(tmp_path):
    harness = _ActualEpisodeHarness(tmp_path, sample_count=2, max_revisions=0, max_contacts=4, planner_actions=("ACCEPT",), arm="speech-feature-query-native-tools")
    original_material = harness.material_for_phase
    original_output = harness._output
    contract = RESPONSE_FORMATS.resolve(FORMAT)({}, tmp_path)
    def material(phase, context, sealed):
        result = original_material(phase, context, sealed)
        return replace(result, response_format=contract) if phase == "reviewer" else result
    def output(key):
        return '{"findings":[],"checked":[]}' if key[1] == "reviewer" else original_output(key)
    harness.material_for_phase = material
    harness._output = output
    harness.config = replace(harness.config, review_handoff="slot-issues-v1")
    harness.program = replace(harness.program, phases=tuple(
        replace(phase, response_format_id=FORMAT) if phase.name == "reviewer" else phase
        for phase in harness.program.phases
    ))
    try:
        result = harness.run()
    finally:
        harness.close()
    reviews = [v["rendered"] for k, v in harness.prepared.items() if k[1] == "reviewer"]
    assert len(reviews) == 2 and all(v["response_format"] == contract for v in reviews)
    planners = [json.dumps(v["rendered"]) for k,v in harness.prepared.items() if k[1] == "planner"]
    assert len(planners) == 2 and all("model-criticism" in v and "valid" in v for v in planners)
    assert all(r.final_response_text.startswith("solver-answer:") for r in result.results)


@pytest.mark.parametrize("mutation", ["ceiling", "solver-contract"])
def test_review_contract_refuses_unregistered_phase_shape(mutation):
    b = block()
    enable(b)
    hooks = carrier_module_hooks()
    factory = hooks.lock_versions[b["lock"]]
    def layer():
        value = copy.deepcopy(factory())
        if mutation == "ceiling":
            value["policy"] = "phase-native-module-v1-c13"
        else:
            value["phase_material"]["solver"]["response_format_id"] = "unregistered-test"
        return value
    versions = dict(hooks.lock_versions)
    versions[b["lock"]] = layer
    with pytest.raises(cm.ConsumptionModuleConfigError, match="13-contact"):
        cm.compile_module(b, replace(hooks, lock_versions=versions))
