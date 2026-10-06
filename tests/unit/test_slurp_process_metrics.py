"""Process diagnostics preserve missingness, source custody and metric denominators."""
import copy
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_process_metrics import (
    aggregate_process_metrics, build_slurp_process_metrics, measure_support, rate,
)
from test_slurp_solver_stage_attribution import _source, _reference, _saved_row, _answer


def row(sid, draft=False, final=False, alarm=False, revised=True, **extra):
    return dict(sample_id=sid, scenario="weather", gold_empty=False,
                draft_entity_correct=draft, final_entity_correct=final,
                draft_full_correct=draft, final_full_correct=final,
                review_alarm=alarm, review_valid=True, handoff_visible=True,
                revised=revised, **extra)


def test_confusion_repair_and_harm_have_distinct_denominators():
    report=aggregate_process_metrics([
        row("tp", final=True, alarm=True), row("fn"),
        row("fp", draft=True, alarm=True), row("tn", draft=True, final=True),
    ])
    m=report["metrics"]
    assert (m["review_error_detection"]["numerator"],m["review_error_detection"]["denominator"]) == (1,2)
    assert m["review_alarm_precision"]["value"] == .5
    assert m["review_false_alarm"]["value"] == .5
    assert m["review_miss"]["value"] == .5
    assert m["entity_repair_given_revision"]["value"] == .5
    assert m["entity_harm_given_revision"]["value"] == .5
    assert m["entity_repair_after_alarm"]["value"] == 1
    assert report["sample_count"] == 4
    assert report["transitions"]["entity"] == {
        "wrong_to_correct":1,"correct_to_wrong":1,"stable_correct":1,
        "stable_wrong":1,"unknown":0,"net_repairs":0,
    }


def test_unknown_is_not_no_alarm_or_failure_and_strata_are_retained():
    rows=[row("x",alarm=None),row("y",draft=True,final=True)]
    rows[0]["review_valid"]=False
    rows[0]["scenario"]="calendar"
    result=aggregate_process_metrics(rows)
    rate_=result["metrics"]["review_error_detection"]
    assert rate_["value"] is None and rate_["unknown"] == 1
    assert rate_["eligible"] == 1 and rate_["denominator"] == 0
    assert result["metrics"]["review_valid"]["value"] == .5
    assert set(result["by_scenario"]) == {"calendar","weather"}


def test_invalid_review_in_error_sample_does_not_inflate_coverage():
    bad=row("bad",alarm=None)
    bad["review_valid"]=False
    m=aggregate_process_metrics([bad,row("good",alarm=True)])["metrics"]
    assert m["review_error_detection"]["value"] == 1
    assert m["review_error_detection"]["unknown"] == 1
    assert m["review_error_detection"]["lower_missing_bound"] == .5
    assert m["review_error_detection"]["upper_missing_bound"] == 1


def test_zero_denominator_and_wilson_interval():
    assert rate([])["ci95_wilson"] is None
    r=rate([True,False,None])
    assert r["value"] == .5 and r["eligible"] == 3
    assert r["ci95_wilson"][0] < .5 < r["ci95_wilson"][1]
    assert rate([True]*20)["ci95_wilson"][0] < 1


@pytest.mark.parametrize("bad",[1,0,"false",{},[]])
def test_nonboolean_observations_are_refused(bad):
    with pytest.raises(ValueError): rate([bad])


def test_duplicate_inputs_and_extra_content_refused():
    with pytest.raises(ValueError): aggregate_process_metrics([row("a"),row("a")])
    bad=row("a");bad["gold_text"]="secret"
    with pytest.raises(ValueError): aggregate_process_metrics([bad])


def test_support_separates_pool_from_context_and_missing_from_empty():
    support=measure_support({"city"},retrieved={"city"},delivered=set())
    assert support["retrieved_all"] is True and support["delivered_all"] is False
    assert support["lost_all_support"] is True
    missing=measure_support({"city"},retrieved=None,delivered=None)
    assert missing["delivered_all"] is None
    empty=measure_support(set(),retrieved=set(),delivered=set())
    assert empty["delivered_all"] is None and empty["gold_count"] == 0
    assert "city" not in json.dumps(support)


def test_support_entity_pair_does_not_match_value_under_another_type():
    m=measure_support({("city","paris")},retrieved={("country","paris")},delivered={("city","paris")})
    assert m["retrieved_all"] is False and m["delivered_all"] is True
    assert m["retrieved_hits"] == 0 and m["delivered_hits"] == 1


def test_source_wrapper_reuses_official_final_and_exports_no_content():
    sid="slurp:devel:one"
    correct=_answer("weather","query",("city","paris"))
    source=_source({sid:[_answer("calendar","remove"),correct]})
    reference=_reference(sid)
    result=build_slurp_process_metrics(source,reference_records=(reference,),
        official_final_rows=(_saved_row(reference,correct),),
        reference_binding_sha256="d"*64,official_score_result_sha256="e"*64,
        legal_slot_types=("city",))
    m=result["metrics"]
    assert m["entity_repair_given_revision"]["value"] == 1
    assert m["review_error_detection"]["unknown"] == 1
    assert result["source"]["official_score_result_sha256"] == "e"*64
    assert result["claims_causal_node_credit"] is False
    assert result["recall_status"] == "unavailable-until-actual-source-projection"
    assert "paris" not in json.dumps(result)
    assert correct not in json.dumps(result)
    assert result["contacts_added"] == {"model":0,"official_scorer":0}


def test_empty_gold_false_fill_and_exact_saved_score_verification():
    sid="slurp:devel:empty"
    answer=_answer("weather","query",("city","paris"))
    ref=replace(_reference(sid),entities=())
    source=_source({sid:[answer]})
    args=dict(reference_records=(ref,),official_final_rows=(_saved_row(ref,answer),),
        reference_binding_sha256="d"*64,official_score_result_sha256="e"*64,
        legal_slot_types=("city",))
    result=build_slurp_process_metrics(source,**args)
    assert result["metrics"]["empty_gold_false_fill"]["value"] == 1
    assert result["metrics"]["entity_repair_given_revision"]["value"] is None
    broken=copy.deepcopy(args);broken["official_final_rows"][0]["scenario_action_exact"]=9
    with pytest.raises(ValueError): build_slurp_process_metrics(source,**broken)


def _review_source(review_text, *, only_after_revision=False):
    sid="slurp:devel:review"
    wrong=_answer("weather","query")
    correct=_answer("weather","query",("city","paris"))
    texts=[wrong,correct,review_text,"ACCEPT",correct] if only_after_revision else [wrong,review_text,"REVISE",correct]
    source=_source({sid:texts})
    episode=source.phase_results[sid]["native_episode_receipt"]
    ri=2 if only_after_revision else 1
    for index,role in ((ri,"reviewer"),(ri+1,"planner")):
        visit=episode["role_visits"][index]
        visit["role_id"]=visit["stage"]=role
        for contact in visit["execution_receipt"]["contacts"]:
            source.bundle.trace_records[contact["request_id"]+"/native-role-contact"]["use_role_id"]=role
    episode["planner_routes"]=[{"role_visit_index":ri+1,"action":"REVISE"}]
    ref=_reference(sid)
    args=dict(reference_records=(ref,),official_final_rows=(_saved_row(ref,correct),),
              reference_binding_sha256="d"*64,official_score_result_sha256="e"*64,
              legal_slot_types=("city",))
    return source,args


def _review(slot="city"):
    return json.dumps({"findings":[{"kind":"existence","slot_types":[slot],
                       "draft_fragment":"","reason":"Check a possibly omitted entity."}],"checked":[]})


@pytest.mark.parametrize("text,valid,alarm",[
    (_review(),True,True),('{"findings":[],"checked":[]}',True,False),
    ('bad',False,None),(_review("illegal-slot"),False,None),
])
def test_bound_review_alarm_and_invalid_handoffs(text,valid,alarm):
    source,args=_review_source(text)
    result=build_slurp_process_metrics(source,**args)
    assert result["rows"][0]["review_valid"] is valid
    assert result["rows"][0]["review_alarm"] is alarm
    assert result["custody"][0]["first_draft_review"]["visit_index"] == 1


def test_later_review_is_never_evaluated_against_first_draft():
    source,args=_review_source(_review(),only_after_revision=True)
    result=build_slurp_process_metrics(source,**args)
    assert result["rows"][0]["review_alarm"] is None
    assert result["custody"][0]["first_draft_review"] is None


def test_unparsed_empty_prediction_is_not_a_successful_entity_revision():
    sid="slurp:devel:invalid"
    source=_source({sid:["invalid"]})
    ref=replace(_reference(sid),entities=())
    result=build_slurp_process_metrics(source,reference_records=(ref,),
        official_final_rows=(_saved_row(ref,"invalid"),),reference_binding_sha256="d"*64,
        official_score_result_sha256="e"*64,legal_slot_types=("city",))
    assert result["metrics"]["final_entity_correct"]["unknown"] == 1
    assert result["metrics"]["final_parsed"]["value"] == 0
    assert result["metrics"]["final_full_correct"]["value"] == 0
    assert result["metrics"]["empty_gold_false_fill"]["value"] is None


@pytest.mark.parametrize("change",[
    {"review_valid":False}, {"sample_id":""}, {"scenario":None},
    {"revised":1}, {"unknown_key":True},
])
def test_bad_abstract_rows_fail_closed(change):
    r=row("a");r.update(change)
    with pytest.raises(ValueError): aggregate_process_metrics([r])


@pytest.mark.parametrize("gold,retrieved,delivered",[(None,set(),set()),(set(),[],set()),(set(),set(),[])])
def test_unverified_support_shapes_refused(gold,retrieved,delivered):
    with pytest.raises(ValueError): measure_support(gold,retrieved=retrieved,delivered=delivered)


def test_optional_actual_intent_supply_keeps_missing_stage_unknown(monkeypatch):
    # Exercise the adapter after a validated missing-stage projection. The source
    # projection itself has its own strict trace/delivery tests.
    from speech_aware_evidence_acquisition.analysis import native_candidate_stage_projections as projections
    def projected(source, **kwargs):
        return tuple(projections.NativeCandidateStagePair(sid,None,None,False) for sid in source.sample_ids)
    monkeypatch.setattr(projections,"project_verified_native_candidate_stages",projected)
    from test_native_intent_support import SPEC
    sid="slurp:devel:support"
    answer=_answer("weather","query",("city","paris"))
    source=_source({sid:[answer]})
    source.composed.values["knowledge_stores"]={"intent-boundaries":{
        "store_role":"intent-boundaries","phase_supply":{"perception":{"expose_facets":False}},
        "snapshot":{"sha256":"a"*64},"release":{"sha256":"b"*64}}}
    ref=_reference(sid)
    report=build_slurp_process_metrics(source,reference_records=(ref,),
        official_final_rows=(_saved_row(ref,answer),),reference_binding_sha256="d"*64,
        official_score_result_sha256="e"*64,legal_slot_types=("city",),
        intent_support_configuration={"legal_candidate_ids":frozenset({"weather_query"}),
            "max_candidates":1,"specification":SPEC})
    support=report["intent_support"]
    assert support["metrics"]["gold_intent_card_in_initial_request"]["unknown"] == 1
    assert support["metrics"]["gold_intent_in_initial_candidates"]["value"] is None
    assert support["raw_retrieval_pool_status"] == "unavailable"
    assert "weather_query" not in json.dumps(support)


def test_support_adapter_refuses_undeclared_configuration():
    from speech_aware_evidence_acquisition.analysis.slurp_process_metrics import _intent_support
    with pytest.raises(ValueError): _intent_support(None, (), {})


def test_process_metrics_separates_model_revision_from_postprocessing(monkeypatch):
    from test_slurp_solver_stage_attribution import _normalised_source
    source, ref = _normalised_source(monkeypatch)
    report = build_slurp_process_metrics(source, reference_records=(ref,),
        official_final_rows=(_saved_row(ref, source.output_rows[ref.sample_id]["text"]),),
        reference_binding_sha256="d"*64, official_score_result_sha256="e"*64,
        legal_slot_types=("city",))
    stages = report["delivery_stages"]
    assert stages["model_revision"]["entity"]["wrong_to_correct"] == 0
    assert stages["postprocessing"]["entity"]["wrong_to_correct"] == 1
    assert stages["postprocessing_repair_rate"]["value"] == 1
    assert stages["postprocessing_harm_rate"]["value"] is None
    assert stages["rows"][0]["model_revision_completed"] is False
