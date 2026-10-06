"""Prospective parent selection preserves history and grants no runtime authority."""
import copy
import json

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_search_parent_selection import (
    select_search_parents, record_parent_selection,
)
from test_system_search_measurement import profile, measured_fixture
from speech_aware_evidence_acquisition.rails.system_search_measurement import measured_rows


def config(**changes):
    return {"schema": "saea-search-parent-selection-config-v1",
            "frontier_capacity": 3, "exploration_capacity": 1,
            "selection_seed": 17, "iteration": 1, **changes}


def rows():
    specs = [("quality", .9, .9, 30), ("balanced", .8, .8, 20),
             ("cheap", .7, .7, 10), ("dominated", .6, .6, 40)]
    return [dict(candidate_id=name, bundle_id=content_hash(name),
                 cohort_id="a" * 64, measurement_id="b" * 64,
                 measurement_profile_sha256=content_hash(profile()),
                 slu_f1=f, intent=i, reliable_completion_rate=1.,
                 mean_sample_seconds=t, non_first_mean_seconds=t,
                 model_calls=20, tool_calls=0, eligible=True)
            for name, f, i, t in specs]


def select(data=None, cfg=None, uses=None):
    data = rows() if data is None else data
    return select_search_parents(data, profile=profile(), selection_config=cfg or config(),
                                 usage_counts=uses or {r["bundle_id"]: 0 for r in data})


def test_balanced_nonwinner_survives_frontier_and_dominated_parent_can_explore():
    result = select()
    assert set(result["frontier_ids"]) == {content_hash(x) for x in ["quality", "balanced", "cheap"]}
    assert set(result["frontier_parent_ids"]) == set(result["frontier_ids"])
    assert result["exploration_parent_ids"] == [content_hash("dominated")]
    assert result["formal_adoption"] is False and result["runtime_admission"] is False
    assert result["learner_exported"] is False


def test_capacity_retirement_is_explicit_and_does_not_modify_input():
    data = rows(); original = copy.deepcopy(data)
    result = select(data, config(frontier_capacity=1, exploration_capacity=1))
    assert result["frontier_parent_ids"] == [content_hash("quality")]
    assert len(result["exploration_parent_ids"]) == 1
    assert len(result["dispositions"]) == len(data)
    assert set(result["dispositions"]) == {r["bundle_id"] for r in data}
    assert data == original
    assert result["history_deleted"] is False


def test_usage_rotation_and_input_order_are_deterministic():
    data = rows(); uses = {r["bundle_id"]: 10 for r in data}
    uses[content_hash("balanced")] = 0
    a = select(data, config(frontier_capacity=2, exploration_capacity=0), uses)
    b = select(list(reversed(data)), config(frontier_capacity=2, exploration_capacity=0), uses)
    assert a == b
    assert a["frontier_parent_ids"] == [content_hash("quality"), content_hash("balanced")]
    assert a["usage_counts_after"][content_hash("balanced")] == 1
    assert a["usage_counts_after"][content_hash("dominated")] == 10


def test_no_duplicate_or_ineligible_exploration():
    data = rows(); data[-1]["eligible"] = False
    result = select(data, config(frontier_capacity=1, exploration_capacity=9))
    assert set(result["frontier_parent_ids"]).isdisjoint(result["exploration_parent_ids"])
    assert content_hash("dominated") not in result["exploration_parent_ids"]
    assert result["dispositions"][content_hash("dominated")] == "ineligible"
    assert result["unfilled_capacity"] == {"frontier": 0, "exploration": 7}


@pytest.mark.parametrize("field,value", [("frontier_capacity", 0), ("frontier_capacity", True),
    ("exploration_capacity", -1), ("selection_seed", True), ("iteration", 0),
    ("schema", "unknown")])
def test_invalid_configuration_refused(field, value):
    with pytest.raises(PolicyError): select(cfg=config(**{field: value}))


def test_unknown_configuration_field_refused():
    with pytest.raises(PolicyError): select(cfg=config(temperature=1))


@pytest.mark.parametrize("field,value", [("measurement_id", "c" * 64),
    ("cohort_id", "d" * 64), ("measurement_profile_sha256", "e" * 64),
    ("slu_f1", float("nan")), ("mean_sample_seconds", -1), ("eligible", 1)])
def test_invalid_or_mixed_measurements_refused(field, value):
    data = rows(); data[-1][field] = value
    with pytest.raises(PolicyError): select(data)


def test_identity_usage_and_empty_validation():
    data = rows()
    for malformed in [[], data + [copy.deepcopy(data[0])]]:
        with pytest.raises(PolicyError): select(malformed)
    bad = copy.deepcopy(data); bad[-1]["candidate_id"] = bad[0]["candidate_id"]
    with pytest.raises(PolicyError): select(bad)
    for uses in [{"foreign": 0}, {r["bundle_id"]: -1 for r in data},
                 {r["bundle_id"]: True for r in data}]:
        with pytest.raises(PolicyError): select(data, uses=uses)
    for r in data: r["eligible"] = False
    with pytest.raises(PolicyError): select(data)


def test_single_parent_and_tied_frontier_remain_valid():
    data = rows()[:1]
    result = select(data, config(frontier_capacity=1, exploration_capacity=2))
    assert len(result["frontier_parent_ids"]) == 1 and not result["exploration_parent_ids"]
    data = rows()[:2]
    for k in ["slu_f1", "intent", "mean_sample_seconds", "non_first_mean_seconds"]:
        data[1][k] = data[0][k]
    assert len(select(data)["frontier_ids"]) == 2


def test_archive_roundtrip_preserves_input_and_refuses_rewrite(tmp_path):
    archive = SystemSearchArchive(tmp_path / "archive")
    data = rows(); uses = {r["bundle_id"]: 0 for r in data}
    result = record_parent_selection(archive, rows=data, profile=profile(),
        selection_config=config(), usage_counts=uses, source_feedback_sha256="f" * 64)
    path = archive.root / "context-learning/parent-selection/iteration-1.json"
    document = json.loads(path.read_text()); before = path.read_bytes()
    assert document["selection"] == result
    assert document["inputs"]["rows"] == data
    assert document["source_feedback_sha256"] == "f" * 64
    with pytest.raises(PolicyError):
        record_parent_selection(archive, rows=data, profile=profile(),
            selection_config=config(), usage_counts=uses, source_feedback_sha256="f" * 64)
    assert path.read_bytes() == before


def test_existing_complete_feedback_measurement_adapter(tmp_path):
    archive, protocol, feedback, evaluation = measured_fixture(tmp_path)
    doc = feedback.as_json(); bindings = {k: {"bundle_id": content_hash(k)} for k in doc["summaries"]}
    measured = measured_rows(doc, list(bindings), bindings, profile=protocol["measurement_profile"])
    result = select_search_parents(measured, profile=protocol["measurement_profile"],
        selection_config=config(), usage_counts={r["bundle_id"]: 0 for r in measured})
    assert result["frontier_parent_ids"]
    assert result["runtime_admission"] is False


def test_raw_content_and_unknown_measurement_fields_are_refused():
    data = rows(); data[0]["task_answer"] = "Task content must remain outside the selector."
    with pytest.raises(PolicyError): select(data)


def test_all_capacity_dispositions_are_saved():
    result = select(cfg=config(frontier_capacity=1, exploration_capacity=0))
    assert result["dispositions"][content_hash("balanced")] == "frontier-capacity"
    assert result["dispositions"][content_hash("dominated")] == "dominated-not-explored"


@pytest.mark.parametrize("frontier_cap,exploration_cap", [(1, 0), (1, 1), (2, 1), (8, 16)])
def test_configured_capacities_do_not_allocate_proposals(frontier_cap, exploration_cap):
    result = select(cfg=config(frontier_capacity=frontier_cap, exploration_capacity=exploration_cap))
    assert len(result["frontier_parent_ids"]) <= frontier_cap
    assert len(result["exploration_parent_ids"]) <= exploration_cap
    assert result["proposal_allocation_granted"] is False


def test_reliability_floor_is_reapplied_even_when_eligible_flag_is_true():
    data = rows(); data[0]["reliable_completion_rate"] = .9
    result = select(data)
    assert result["dispositions"][content_hash("quality")] == "ineligible"


def proposal_config(selection, modes):
    from test_experiment_population_config import config as population_config
    population = population_config((len(modes),), n=3)
    return {"schema": "saea-parent-proposal-plan-config-v1",
            "experiment_population": population,
            "parent_selection_sha256": selection["selection_sha256"],
            "modes": dict(zip(population["cohorts"][0]["candidate_ids"], modes))}


def test_proposal_plan_covers_configured_population_without_extra_slots():
    from speech_aware_evidence_acquisition.rails.system_search_parent_selection import plan_parent_proposals
    selection = select()
    cfg = proposal_config(selection, ["local", "recombine", "explore", "local"])
    original = copy.deepcopy(cfg)
    plan = plan_parent_proposals(cfg, selection=selection)
    assert len(plan["slots"]) == 4
    assert [s["candidate_id"] for s in plan["slots"]] == list(cfg["modes"])
    assert [len(s["parent_bundle_ids"]) for s in plan["slots"]] == [1, 2, 1, 1]
    assert plan["slots"][2]["parent_bundle_ids"] == selection["exploration_parent_ids"]
    assert plan["population_budget"]["candidate_trajectories"] == 12
    assert plan["configuration_sha256"] == content_hash(cfg)
    assert plan["proposal_allocation_granted"] is False
    assert plan["runtime_admission"] is False and cfg == original


@pytest.mark.parametrize("k", [2, 4, 8, 16])
def test_proposal_plan_sizes_and_determinism_follow_config(k):
    from speech_aware_evidence_acquisition.rails.system_search_parent_selection import plan_parent_proposals
    selection = select(); cfg = proposal_config(selection, ["local"] * (k-1) + ["explore"])
    a = plan_parent_proposals(cfg, selection=selection)
    cfg["modes"] = dict(reversed(list(cfg["modes"].items())))
    assert plan_parent_proposals(cfg, selection=selection) == a
    assert len(a["slots"]) == k


@pytest.mark.parametrize("fault", ["missing_slot", "extra_slot", "unknown_mode", "selection_pin",
                                    "altered_selection", "extra_config", "no_exploration"])
def test_proposal_plan_refuses_drift_and_silent_budget_changes(fault):
    from speech_aware_evidence_acquisition.rails.system_search_parent_selection import plan_parent_proposals
    selection = select(); cfg = proposal_config(selection, ["local", "explore"])
    if fault == "missing_slot": cfg["modes"].pop("candidate-0")
    elif fault == "extra_slot": cfg["modes"]["replacement"] = "local"
    elif fault == "unknown_mode": cfg["modes"]["candidate-0"] = "retry"
    elif fault == "selection_pin": cfg["parent_selection_sha256"] = "a" * 64
    elif fault == "altered_selection": selection["frontier_parent_ids"] = ["f" * 64]
    elif fault == "extra_config": cfg["K"] = 999
    else: cfg["modes"]["candidate-1"] = "local"
    with pytest.raises(PolicyError): plan_parent_proposals(cfg, selection=selection)


@pytest.mark.parametrize("mode,frontier,exploration", [("recombine", 1, 1), ("explore", 1, 0)])
def test_proposal_plan_refuses_missing_parent_capacity_without_fallback(mode, frontier, exploration):
    from speech_aware_evidence_acquisition.rails.system_search_parent_selection import plan_parent_proposals
    selection = select(cfg=config(frontier_capacity=frontier, exploration_capacity=exploration))
    cfg = proposal_config(selection, [mode, "explore"])
    with pytest.raises(PolicyError): plan_parent_proposals(cfg, selection=selection)



def test_proposal_plan_preserves_multiple_cohort_order_and_budget():
    from test_experiment_population_config import config as population_config
    from speech_aware_evidence_acquisition.rails.system_search_parent_selection import plan_parent_proposals
    selection = select(); cfg = proposal_config(selection, ["local", "explore"])
    cfg["experiment_population"] = population_config((3, 2), n=7)
    cfg["modes"] = {f"candidate-{i}": "explore" if i == 4 else "local" for i in range(5)}
    plan = plan_parent_proposals(cfg, selection=selection)
    assert [s["cohort_id"] for s in plan["slots"]] == ["cohort-0"] * 3 + ["cohort-1"] * 2
    assert plan["population_budget"]["family_trajectories"] == 63
    assert plan["population_budget"]["generation_contacts_cap"] == 63 * 13
    parents = [s["parent_bundle_ids"][0] for s in plan["slots"][:4]]
    assert parents == selection["frontier_parent_ids"] + [selection["frontier_parent_ids"][0]]


@pytest.mark.parametrize("fault", ["duplicate", "disposition", "empty", "bad_sha", "malformed_mode"])
def test_proposal_plan_refuses_inconsistent_rehashed_selection(fault):
    from speech_aware_evidence_acquisition.rails.system_search_parent_selection import plan_parent_proposals
    selection = select()
    if fault == "duplicate": selection["exploration_parent_ids"] = selection["frontier_parent_ids"][:1]
    elif fault == "disposition": selection["dispositions"][selection["frontier_parent_ids"][0]] = "ineligible"
    elif fault == "empty": selection["frontier_parent_ids"] = []
    elif fault == "bad_sha":
        selection["frontier_parent_ids"][0] = "invalid"
        selection["dispositions"]["invalid"] = "frontier-parent"
    selection["selection_sha256"] = content_hash({k: v for k, v in selection.items() if k != "selection_sha256"})
    cfg = proposal_config(selection, ["local", "explore"])
    if fault == "malformed_mode": cfg["modes"]["candidate-0"] = []
    with pytest.raises(PolicyError): plan_parent_proposals(cfg, selection=selection)
