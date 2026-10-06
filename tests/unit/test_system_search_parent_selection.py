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
