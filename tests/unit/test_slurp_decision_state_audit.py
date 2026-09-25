"""Prefix-only state and descriptive full-outcome joins, with synthetic inputs."""
import copy
import hashlib
import json
import pytest
from speech_aware_evidence_acquisition.analysis.slurp_decision_state_audit import (
    project_prefix, summarize_audit,
)
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
)

def inputs():
    candidates=[{"intent_id":label,"distinction":"Distinguish the requested task.",
                 "evidence_refs":["speech:full-utterance"],"unresolved_fields":[]}
                for label in ("weather_query","weather_query","transport_taxi")]
    content=json.dumps({"candidates":candidates})
    state=AgentStateArtifact("perception:s1","phase:perception",content,
        "1"*64,hashlib.sha256(content.encode()).hexdigest(),"shared-native",()).as_json()
    return dict(sample_id="s1",perception_state=state,
        solver_payload={"sample_id":"s1","supplied_evidence":[
            {"evidence_id":"train-exemplars::e1"},
            {"evidence_id":"train-exemplars::e2"},
            {"evidence_id":"slot-contracts::place"}]},
        legal_ids=("weather_query","transport_taxi","calendar_set"),
        labels={"e1":"weather_query","e2":"transport_taxi","future":"weather_query"},
        candidate_reader={"compact_source_phase":"perception","max_candidates":3,
            "projection_policy":BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID})

def test_prefix_uses_shared_distinct_projection_and_only_supplied_ids():
    args=inputs()
    actual=project_prefix(**args)
    assert actual["candidate_count"]==2 and actual["raw_candidate_count"]==3
    assert actual["exemplar_top_agreement"]=="agree-0.50-0.75"
    assert actual["exemplar_ids"]==["e1","e2"]
    changed=copy.deepcopy(args)
    changed["labels"]["future"]="transport_taxi"
    assert project_prefix(**changed)==actual

@pytest.mark.parametrize("mutation",["cross-sample","duplicate","unknown","altered-state"])
def test_unbound_inputs_are_refused(mutation):
    args=inputs()
    if mutation=="cross-sample":args["solver_payload"]["sample_id"]="s2"
    elif mutation=="duplicate":args["solver_payload"]["supplied_evidence"].append({"evidence_id":"train-exemplars::e1"})
    elif mutation=="unknown":args["solver_payload"]["supplied_evidence"].append({"evidence_id":"train-exemplars::missing"})
    else:args["perception_state"]["content"]+=" "
    with pytest.raises(ValueError):project_prefix(**args)

def test_no_exemplars_is_explicit_not_high_agreement():
    args=inputs();args["solver_payload"]["supplied_evidence"]=[]
    assert project_prefix(**args)["exemplar_top_agreement"]=="no-exemplars"

def test_terminal_labels_do_not_change_actor_state_and_unreached_is_retained():
    row={"sample_id":"s1",**project_prefix(**inputs()),"whole_episode_union_matches_prefix":True}
    other={"sample_id":"s2","status":"not_reached"}
    complete={"ordered_sample_ids":["s1","s2"],"rows":[
        {"sample_id":sid,"tp":0,"fp":1,"fn":0,"intent_exact":1,
         "fallback_flags":[],"revision_reached":False} for sid in ("s1","s2")]}
    source={"label":"plan","rows":[row,other],"complete":complete}
    repeat=copy.deepcopy(source);repeat["label"]="planr"
    before=summarize_audit([source,repeat],scenario_of={"s1":"weather","s2":"weather"},f0=.58)
    repeat["complete"]["rows"][0].update(tp=2,fp=0,intent_exact=0)
    after=summarize_audit([source,repeat],scenario_of={"s1":"weather","s2":"weather"},f0=.58)
    assert before["actor_states"]==after["actor_states"]
    assert before["state_rows"]==after["state_rows"]
    assert before["terminal_diagnostics"]!=after["terminal_diagnostics"]
    assert after["actor_states"]["plan"]["not_reached"]==1
    assert after["repeat_stability"]["candidate_count"]["comparable_rows"]==1
    assert after["policy_updated"] is False
    assert after["terminal_diagnostics"]["plan"]["all_rows"]["rows"]==2
    assert after["terminal_diagnostics"]["plan"]["boundary_not_reached"]["rows"]==1
