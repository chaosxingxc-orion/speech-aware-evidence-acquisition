"""One complete template system is one learning record, independent of roster size."""
from copy import deepcopy
import json
import pytest
from test_abstract_population_projection import setup, with_archive
from test_partitioned_context_learning import ready, prepare, response
from test_partitioned_context_continuation import continuation, run
from test_abstract_population_sources import pin
from speech_aware_evidence_acquisition.rails import system_context_partitioned_learning as partitioned
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.analysis.aggregate_template_learning import aggregate_actor_view


def actor(s):
    packet = run(s)
    return packet, partitioned.partitioned_context_actor_view(s.archive, input_sha256=packet["input_sha256"])


def test_k_records_per_observation_no_sample_or_visit_records(continuation):
    _, original = actor(continuation)
    value = aggregate_actor_view(original)
    k = len(original["candidate_order"])
    assert value["population_size"] == k == 5
    assert value["observed_rounds"] == 2
    assert len(value["records"]) == 2 * k
    assert [r["candidate_id"] for r in value["records"][:k]] == original["candidate_order"]
    assert {r["evaluated_iteration"] for r in value["records"]} == {2, 3}
    forbidden = {"groups", "input_index", "nodes", "visit_index", "samples", "sample_ids", "observation"}
    def walk(x):
        if isinstance(x, dict):
            assert not forbidden.intersection(x)
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(value)
    assert value["runtime_admission"] is False
    assert value["records"][0]["process"] is None
    assert value["records"][k]["process"]["rates"]
    assert value["records"][k]["process"]["model_transitions"]
    assert "strata" not in value["records"][k]["process"]
    assert value["records"][0]["template"] == original["templates"]["cohort-0"]["candidate-0"]
    for marker in ("PRIVATE_", "slurp:train:", "source_pins", "private_custody"):
        assert marker not in json.dumps(value)


def test_numeric_summaries_preserve_denominators_and_categorical_actions(continuation):
    _, original = actor(continuation)
    cohort = original["feedback"]["cohorts"]["cohort-0"]
    members = [g["members"][0] for g in cohort["groups"]]
    value = aggregate_actor_view(original)["records"][0]
    assert value["sample_count"] == len(members)
    assert value["terminal"]["utility"][0] == len(members)
    assert value["terminal"]["utility"][2] == pytest.approx(sum(m["terminal"]["utility"] for m in members))
    assert value["terminal"]["relative_return"][2] == pytest.approx(sum(m["relative_return"] for m in members))
    role = value["node_statistics"]["solver"]
    visits = [n for m in members for n in m["nodes"] if n[0] == 1]
    assert role["visits"] == len(visits)
    assert role["performance"]["input_tokens"][0] + role["performance"]["input_tokens"][1] == len(visits)
    planner = value["node_statistics"]["planner"]
    assert sum(planner["actions"].values()) == planner["visits"]
    assert "action_index" not in planner["output_features"]
    assert value["business"]["slu_f1"] == original["business_measurements"]["cohort-0"][0]["slu_f1"]
    assert all(c["business"]["is_control"] for c in aggregate_actor_view(original)["comparators"])


def test_arbitrary_k_and_three_observations_keep_rejected_nochange(continuation):
    _, original = actor(continuation)
    original["iteration"] += 1
    original["prior_continuations"] = [{"iteration": 4,
        "rejected_history": deepcopy(original["rejected_history"]),
        "process_feedback": deepcopy(original["process_feedback"])}]
    view = aggregate_actor_view(original)
    assert len(view["records"]) == 3 * len(original["candidate_order"])
    assert [r["evaluated_iteration"] for r in view["records"]][::5] == [2, 3, 4]
    assert all(r["disposition"] == "rejected-retain-before-population" for r in view["records"][5:])


@pytest.mark.parametrize("fault", ["missing-candidate", "missing-sample", "extra-business", "bad-process", "nan", "nonsequential"])
def test_refuse_partial_or_misaligned_aggregate(continuation, fault):
    _, a = actor(continuation)
    if fault == "missing-candidate": a["templates"]["cohort-0"].pop("candidate-0")
    elif fault == "missing-sample": a["feedback"]["cohorts"]["cohort-0"]["groups"][0]["members"].pop()
    elif fault == "extra-business": a["business_measurements"]["cohort-0"][0]["answer"] = "PRIVATE"
    elif fault == "bad-process": a["process_feedback"]["cohorts"]["cohort-0"]["members"].pop("candidate-0")
    elif fault == "nan": a["feedback"]["cohorts"]["cohort-0"]["groups"][0]["members"][0]["terminal"]["utility"] = float("nan")
    else: a["prior_continuations"] = [{"iteration": 99, "rejected_history": a["rejected_history"], "process_feedback": a["process_feedback"]}]
    with pytest.raises(ValueError): aggregate_actor_view(a)


def test_optin_registered_profile_shared_reservation_and_compiler(continuation):
    s = continuation
    s.reg.update(schema="saea-partitioned-context-continuation-registration-v2", learner_profile="aggregate-template-records-v1")
    s.regpin = pin(s.root, "continuation.json", s.reg)
    p, view = actor(s)
    assert view["schema"] == "saea-aggregate-template-actor-view-v1"
    assert len(view["records"]) == 10
    h = content_hash(view)
    learning.reserve_context_population_update(s.archive, input_sha256=p["input_sha256"], actor_input_sha256=h)
    result = learning.record_context_population_update(s.archive, input_sha256=p["input_sha256"], response_document=response(p,h))
    assert len(result["records"]) == 5
    assert all(r["status"] == "no-change" for r in result["records"])


def test_all_missing_node_and_zero_variance_are_explicit(continuation):
    _, original = actor(continuation)
    for g in original["feedback"]["cohorts"]["cohort-0"]["groups"]:
        for m in g["members"]:
            m["nodes"] = [n for n in m["nodes"] if n[0] != 2]
            m["missing_roles"] = [2]
            m["relative_return"] = 0
    r = aggregate_actor_view(original)["records"][0]
    assert r["node_statistics"]["reviewer"]["visits"] == 0
    assert r["node_statistics"]["reviewer"]["samples_missing_role"] == r["sample_count"]
    assert r["node_statistics"]["reviewer"]["performance"]["input_tokens"] == [0,0,None,None,None,None,None]
    assert r["terminal"]["relative_return"][3] == 0


@pytest.mark.parametrize("fault", ["unknown-profile", "v1-extra", "budget"])
def test_profile_or_budget_refuses_before_reservation(continuation, fault):
    s = continuation
    s.reg.update(schema="saea-partitioned-context-continuation-registration-v2", learner_profile="aggregate-template-records-v1")
    if fault == "unknown-profile": s.reg["learner_profile"] = "cases"
    elif fault == "v1-extra": s.reg["schema"] = "saea-partitioned-context-continuation-registration-v1"
    else: s.reg["max_actor_input_bytes"] = 1
    s.regpin = pin(s.root, "continuation.json", s.reg)
    with pytest.raises(ValueError): run(s)
    assert not (s.archive.root / "context-learning/populations").exists()
    assert not (s.archive.root / "context-learning/inputs/partitioned-next-with-process.json").exists()


def test_new_profile_budget_is_actual_aggregate_not_private_source_size(continuation):
    s=continuation
    _, legacy=actor(s)
    compact=aggregate_actor_view(legacy)
    # Test the projection shape separately; fixture payloads can be too small for savings.
    assert len(compact["records"]) == 10
    original = deepcopy(legacy)
    for c in legacy["feedback"]["cohorts"].values():
        for i in range(3):
            c["groups"].extend(deepcopy(c["groups"]))
    # Cardinality is invariant with roster growth; unknown process was never measured for the base.
    expanded=aggregate_actor_view(legacy)
    assert len(expanded["records"]) == len(compact["records"])
    assert expanded["records"][0]["sample_count"] == 8*compact["records"][0]["sample_count"]
    assert aggregate_actor_view(original) == compact


def test_multiround_profile_preserves_selection_statistics_and_private_exposure(continuation):
    from test_partitioned_context_continuation import advance_registration
    s=continuation
    s.reg.update(schema="saea-partitioned-context-continuation-registration-v2", learner_profile="aggregate-template-records-v1")
    s.regpin=pin(s.root,"continuation.json",s.reg)
    first=run(s)
    advance_registration(s,first,2)
    second=run(s)
    view=partitioned.partitioned_context_actor_view(s.archive,input_sha256=second["input_sha256"])
    assert len(view["records"]) == 3*5
    assert [r["selection"]["utility_after"] for r in view["records"][5::5]] == [9.,7.]
    assert set(first["feedback_sample_ids"]) <= set(second["feedback_sample_ids"])
    assert "PRIVATE_HISTORY_2" not in json.dumps(view)
