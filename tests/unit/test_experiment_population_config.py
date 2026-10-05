"""One pinned experiment configuration controls population and stage accounting."""
from copy import deepcopy
import json
import pytest
from speech_aware_evidence_acquisition.rails.experiment_population import (
    load_population_config, population_accounting, validate_population_config,
    require_population_binding,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_context_learning import pin


def config(sizes=(3, 5), n=7):
    offset = 0
    cohorts = []
    for index, size in enumerate(sizes):
        candidates = [f"candidate-{i}" for i in range(offset, offset+size)]
        offset += size
        cohorts.append({"cohort_id": f"cohort-{index}", "candidate_ids": candidates,
                        "control_ids": ["seed", "seed-aa"],
                        "sample_ids": [f"slurp:train:{i}" for i in range(n)]})
    return {"schema": "saea-experiment-population-config-v1", "experiment_id": "config-test",
            "nodes": ["perception", "solver", "reviewer", "planner"],
            "sampling": {"temperature": 0, "seed": 20260913},
            "execution": {"slot_count": 4, "queue_depth": 4, "schedule": "sequential-trajectory"},
            "proposer": {"model": "gpt-6.1-sol", "reasoning_effort": "high", "semantic_batches": 1},
            "contact_limits": {"model_per_trajectory": 13, "fit_endpoints_per_model_contact": 4},
            "cohorts": cohorts}


@pytest.mark.parametrize("sizes,n", [((3,5),7), ((8,),20), ((16,),20), ((4,4,4),50)])
def test_config_drives_all_counts_and_pins(tmp_path, sizes, n):
    document = config(sizes, n)
    ref = pin(tmp_path, "population.json", document)
    loaded = load_population_config(ref, repo_root=tmp_path)
    assert loaded == document
    accounting = population_accounting(loaded)
    assert accounting["candidate_trajectories"] == sum(sizes)*n
    assert accounting["control_trajectories"] == len(sizes)*2*n
    assert accounting["family_trajectories"] == (sum(sizes)+len(sizes)*2)*n
    assert accounting["generation_contacts_cap"] == accounting["family_trajectories"]*13
    assert accounting["fit_endpoints_cap"] == accounting["generation_contacts_cap"]*4
    # Different stages must carry the same configuration identity, never a new default.
    stages = [{"experiment_population": ref, "population_cohort": "cohort-0"}
              for _ in ("proposal", "compile", "fit", "generation", "score", "feedback")]
    selected = require_population_binding(loaded, ref, "cohort-0", *stages)
    assert len(selected["candidate_ids"]) == sizes[0]
    (tmp_path/"population.json").write_text(json.dumps(config((2,), n)))
    with pytest.raises(PolicyError): load_population_config(ref, repo_root=tmp_path)


@pytest.mark.parametrize("fault", ["duplicate_cohort", "duplicate_candidate", "candidate_control_collision",
    "duplicate_sample", "empty_candidates", "unknown_node", "duplicate_node", "bool_slots",
    "bad_queue", "bad_seed", "changed_temperature", "extra", "invalid_contact_cap"])
def test_refuse_ambiguous_configuration(fault):
    d = config()
    c = d["cohorts"][0]
    if fault == "duplicate_cohort": d["cohorts"][1]["cohort_id"] = c["cohort_id"]
    elif fault == "duplicate_candidate": d["cohorts"][1]["candidate_ids"][0] = c["candidate_ids"][0]
    elif fault == "candidate_control_collision": c["candidate_ids"][0] = "seed"
    elif fault == "duplicate_sample": c["sample_ids"][1] = c["sample_ids"][0]
    elif fault == "empty_candidates": c["candidate_ids"] = []
    elif fault == "unknown_node": d["nodes"][0] = "unimplemented"
    elif fault == "duplicate_node": d["nodes"][0] = "solver"
    elif fault == "bool_slots": d["execution"]["slot_count"] = True
    elif fault == "bad_queue": d["execution"]["queue_depth"] = 0
    elif fault == "bad_seed": d["sampling"]["seed"] = True
    elif fault == "changed_temperature": d["sampling"]["temperature"] = .5
    elif fault == "extra": d["K"] = 999
    else: d["contact_limits"]["model_per_trajectory"] = -1
    with pytest.raises(PolicyError): validate_population_config(d)


@pytest.mark.parametrize("fault", ["missing_pin", "changed_pin", "missing_cohort", "wrong_cohort", "unknown_cohort"])
def test_any_stage_drift_is_rejected(tmp_path, fault):
    d = config()
    ref = pin(tmp_path, "population.json", d)
    artifact = {"experiment_population": deepcopy(ref), "population_cohort": "cohort-0"}
    cohort = "cohort-0"
    if fault == "missing_pin": artifact.pop("experiment_population")
    elif fault == "changed_pin": artifact["experiment_population"]["sha256"] = content_hash("changed")
    elif fault == "missing_cohort": artifact.pop("population_cohort")
    elif fault == "wrong_cohort": artifact["population_cohort"] = "cohort-1"
    else: cohort = "absent"
    with pytest.raises(PolicyError): require_population_binding(d, ref, cohort, artifact)
