"""Source-bound process metrics cross the actor boundary as aggregate numbers only."""
from copy import deepcopy
import json
import pytest
from test_slurp_process_metrics import row
from speech_aware_evidence_acquisition.analysis.slurp_process_metrics import aggregate_process_metrics, rate
from speech_aware_evidence_acquisition.analysis.abstract_process_feedback import project_process_feedback
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def fixture():
    ids=["slurp:train:PRIVATE_A", "slurp:train:PRIVATE_B"]
    c={"cohorts":[{"cohort_id":"part", "candidate_ids":["a","b"], "control_ids":["seed","aa"], "sample_ids":ids}]}
    family={}; bindings={}
    for mid in ["a","b","seed","aa"]:
        rows=[row(ids[0],alarm=True),row(ids[1],draft=True,final=False,alarm=True)]
        rows[0]["scenario"]="PRIVATE_SCENARIO"
        a=aggregate_process_metrics(rows); a['rows']=rows
        a['source']={'ordered_sample_ids_sha256':content_hash(ids),'official_score_result_sha256':'a'*64}
        a['custody']={'PRIVATE_TEXT':'not for export'}
        a['intent_support']={'metrics': {'gold_intent_card_in_initial_request':rate([True,True]),
            'gold_intent_in_initial_candidates':rate([False,True]),'candidate_coverage_given_card':rate([False,True])},
            'samples':[{'sample_id':sid,'gold_intent_value_supplied':True,'c0_gold_covered':v} for sid,v in zip(ids,[False,True])]}
        a['delivery_stages']={'rows':[{'sample_id':z['sample_id'],'model_revision_completed':z['revised'],
            'model':{k:z[k] for k in ('draft_entity_correct','final_entity_correct','draft_full_correct','final_full_correct')},
            'postprocessing':{'draft_entity_correct':z['final_entity_correct'],'final_entity_correct':z['final_entity_correct'],
                'draft_full_correct':z['final_full_correct'],'final_full_correct':z['final_full_correct']}} for z in rows]}
        family[mid]=a; bindings[mid]={'score_result':{'sha256':'a'*64}}
    return {'families':{'part':family}},c,{'part':bindings}


def test_process_projection_preserves_denominators_controls_and_private_boundary():
    report,config,bindings=fixture()
    out=project_process_feedback(report,config=config,bindings=bindings)
    assert list(out['cohorts']['part']['members'])==['a','b','seed','aa']
    member=out['cohorts']['part']['members']['a']
    assert member['rates']['review_false_alarm']['value']==1
    assert member['model_transitions']['entity']['correct_to_wrong']==1
    assert member['postprocessing_transitions']['entity']['correct_to_wrong']==0
    assert len(member['strata'])==2
    assert member['rates']['review_error_detection']['ci95_wilson'] is not None
    for secret in ['slurp:train:', 'PRIVATE_', 'weather','custody','sample_id']:
        assert secret not in json.dumps(out)


@pytest.mark.parametrize('fault',['member','order','sample','score','metric','extra-row','stage-link','stage-text','support-metric','support-bool'])
def test_process_projection_refuses_incomplete_or_inconsistent_evidence(fault):
    report,c,b=fixture(); family=report['families']['part']; a=family['a']
    if fault=='member': del family['aa']
    elif fault=='order': a['rows'].reverse()
    elif fault=='sample': a['source']['ordered_sample_ids_sha256']='b'*64
    elif fault=='score': a['source']['official_score_result_sha256']='b'*64
    elif fault=='metric': a['metrics']['review_error_detection']['value']=0
    elif fault=='extra-row': a['rows'][0]['gold_text']='PRIVATE'
    elif fault=='stage-link': a['delivery_stages']['rows'][0]['model']['draft_entity_correct']=True
    elif fault=='stage-text': a['delivery_stages']['rows'][0]['model']['gold']='PRIVATE'
    elif fault=='support-metric': a['intent_support']['metrics']['gold_intent_in_initial_candidates']['value']=0
    else: a['intent_support']['samples'][0]['c0_gold_covered']=1
    with pytest.raises(ValueError): project_process_feedback(report,config=c,bindings=b)
