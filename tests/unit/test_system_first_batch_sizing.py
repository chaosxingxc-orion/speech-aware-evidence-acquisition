"""Keep resource sizing consistent across the first complete-system replicas."""
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, effective_request_values
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.roster import verify_roster
from speech_aware_evidence_acquisition.rails.context_budget import serving_bound_reserve_tokens
from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "slurp-native-stage3-system-batch001-r01c"
MODEL = "q4km-mmproj-free-system-np2-ctx24k-resource-guard-v1"


def read(path):
    return json.loads((ROOT / path).read_text())


def test_first_batch_is_exact_parent_prefix_and_has_no_execution_authority():
    parent = read("docs/receipts/rosters/slurp-stage3-construction-r01c.json")
    roster = read("docs/receipts/rosters/slurp-system-batch001-r01c-v1.json")
    view = read("configs/dataset/slurp-speech-system-batch001-r01c-v1.json")
    assert roster["items"] == parent["items"][:4]
    assert verify_roster(roster) == view["split_identity_hash"]
    assert view["count"] == len(view["items"]) == 4
    original = read("configs/dataset/slurp-speech-native-stage3-construction-r01c.json")
    assert view["items"] == original["items"][:4]
    assert view["audio_seconds_total"] == sum(x["audio_seconds"] for x in view["items"])
    unsigned = {k: v for k, v in view.items() if k != "runtime_view_sha256"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == view["runtime_view_sha256"]


def test_all_replicas_resolve_two_slots_and_role_caps_through_shared_loader():
    signatures, seeds = [], []
    for replica in range(1, 5):
        name = f"{PREFIX}-s{replica}-v1"
        (cell,) = load_campaign_cells(ROOT, name)
        d = cell.document
        values = effective_request_values(compose(
            ROOT, d["model_fragment"], d["dataset_fragment"], d["baseline_fragment"], name
        ).values)
        assert d["model_fragment"] == MODEL
        assert values["profile_slot_count"] == values["serving_slots"] == 2
        assert values["serving_slot_tokens"] == 24576
        args = values["server_args"]
        assert int(args[args.index("-c") + 1]) == 2 * 24576
        for mode in ("campaign", "worker", "prompt-fit"):
            with pytest.raises(ValueError, match="does not permit"):
                cell.assert_mode(mode)
        assert "execution_plan" not in values
        program = PhaseProgram(
            program_id="phase-test-resource-sizing",
            phases=tuple(PhaseSpec(p, p, "none", None, False)
                         for p in ("perception", "solver", "reviewer", "planner")),
            max_contacts=11, stop_rule="native-role-episode",
        ).validate()
        native = load_native_episode_config(values, program)
        assert native.role("reviewer").max_completion_tokens == 1024
        assert {native.role(p).max_completion_tokens
                for p in ("perception", "solver", "planner")} == {512}
        assert native.max_contacts == 11
        seeds.append(values["decoding_params"]["seed"])
        signatures.append({key: values.get(key) for key in
                           ("native_episode", "phase_material", "knowledge_stores",
                            "task_instruction_template", "prompt_order")})
    assert len(set(seeds)) == 4
    assert all(s == signatures[0] for s in signatures)


def test_stage_envelopes_reserve_output_and_shared_headroom_without_claiming_fit():
    design = read("configs/analysis/slurp-system-first-batch-sizing-v1.json")
    assert design["launch_authority"] is False
    assert design["batch"]["inputs"] == 4
    assert design["batch"]["replicas_per_input"] == 4
    assert design["batch"]["maximum_concurrent_episodes"] == 2
    slot = design["capacity"]["slot_tokens"]
    reserve = serving_bound_reserve_tokens(slot)
    assert reserve == design["capacity"]["operational_reserve_tokens"]
    for stage in design["capacity"]["stages"]:
        assert stage["maximum_rendered_input_and_speech_tokens"] + stage["output_tokens"] + reserve + 2 == slot
        assert stage["actual_fit_status"] == "PENDING"
    assert design["memory_proposal"]["max_memory_records"] == 8
    assert design["workload"]["maximum_generation_contacts"] == 201
