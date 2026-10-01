"""Prove owner-213 successor changes custody, not the scientific comparison."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAIRS = (("slurp-native-stage3-plan-testsample-milestone00-v1", "slurp-milestone-successor1-plan-v1"),
         ("slurp-native-stage3-comp1b-testsample-v1", "slurp-milestone-successor1-comp1b-v1"))


def load(name):
    return json.loads((ROOT / "configs/experiment" / (name + ".json")).read_text())


def test_successor_retains_the_entire_scientific_baseline():
    for old_name, new_name in PAIRS:
        old, new = load(old_name), load(new_name)
        oldcell, newcell = old["cells"][0], new["cells"][0]
        for field in ("model_fragment", "dataset_fragment", "allowed_execution_stages"):
            assert oldcell[field] == newcell[field]
        for field in ("execution_plan", "family_budget", "failure_policy", "preserve_wire_responses"):
            assert old[field] == new[field]
        a, b = [json.loads((ROOT / "configs/baseline" / (c["baseline_fragment"] + ".json")).read_text()) for c in (oldcell, newcell)]
        for doc in (a, b):
            doc.pop("prepared_phase_supply")
            doc["native_contact_fit"].pop("run_id")
            doc["native_contact_fit"].pop("attempt_id")
        assert a == b
        assert oldcell["run_id"] != newcell["run_id"]
        assert oldcell["attempt_id"] != newcell["attempt_id"]
        assert "resume_from" not in newcell


def test_successor_allowance_partitions_fresh_generation_and_fit_only():
    receipt = json.loads((ROOT / "docs/receipts/owner/2026-10-01-slurp-test-sample-successor1-allowance-v1.json").read_text())
    generation = {load(new)["cells"][0]["run_id"] for _, new in PAIRS}
    assert generation == set(receipt["read_run_ids"])
    assert len(receipt["permitted_run_ids"]) == 4
    assert set(receipt["permitted_run_ids"]) == generation | set(receipt["preparation_run_ids"])
    assert generation.isdisjoint(receipt["preparation_run_ids"])
    assert all("SUCCESSOR1" in run for run in receipt["permitted_run_ids"])
    assert receipt["budgets"]["official_score_jobs_total"] == 2


def test_all_registered_slurp_rosters_remain_compatible_with_final_report_isolation():
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.contracts.gate_exposure import _ExposureAndCarrierMixin
    receipts = _ExposureAndCarrierMixin._carrier_roster_receipts(SimpleNamespace(source_root=ROOT), "slurp")
    selected = [entry for entry in receipts if entry[1].get("roster_id") == "STAGE3-KNOWLEDGE-OPPORTUNITY-R01C400"]
    assert len(selected) == 1
    assert len(selected[0][2]) == 400
    assert selected[0][1]["split_role"] == "discovery"
