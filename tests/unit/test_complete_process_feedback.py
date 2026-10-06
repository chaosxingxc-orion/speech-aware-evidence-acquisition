"""Complete cohort joins retain controls, exact source custody and abstract-only output."""
from copy import deepcopy
import json
import pytest
from test_abstract_process_feedback import fixture
from speech_aware_evidence_acquisition.analysis.complete_process_feedback import join_complete_process_feedback


def sources():
    raw, cfg, scores = fixture()
    cfg['cohorts'].append({**deepcopy(cfg['cohorts'][0]), 'cohort_id':'second'})
    reports, qualifications, read_ids = {}, {}, {}
    scores['second'] = deepcopy(scores['part'])
    for c in cfg['cohorts']:
        tag=c['cohort_id'];members=deepcopy(raw['families']['part']);observed=[]
        for mid,value in members.items():
            value['source'].update(run_id=tag+'-'+mid, attempt_id=tag+'-'+mid+'-attempt')
            observed.append({'member':mid,'run_id':tag+'-'+mid,'attempt_id':tag+'-'+mid+'-attempt','rows':2,'state':'FINALIZED','verified_seal':True,'official_successful_jobs':1,'failed_jobs':0})
        read_ids[tag]=tag+'-READ'
        qualifications[tag]={'status':'ALL_MEMBERS_OPERATIONALLY_QUALIFIED','read_id':read_ids[tag],'members':observed}
        reports[tag]={'schema':'saea-complete-cohort-process-metrics-v1','cohort':tag,'read_id':read_ids[tag],'members':members,'contacts_added':{'model':0,'official_scorer':0},'learner_exported':False,'runtime_changed':False}
    return dict(config=cfg,reports=reports,qualifications=qualifications,read_ids=read_ids,score_bindings=scores)


def test_every_cohort_controls_and_unknowns_are_preserved_without_private_rows():
    args=sources();out=join_complete_process_feedback(**args)
    assert list(out['cohorts'])==['part','second']
    assert list(out['cohorts']['second']['members'])==['a','b','seed','aa']
    assert out['cohorts']['part']['members']['a']['model_transitions']['entity']['correct_to_wrong']==1
    assert out['cohorts']['part']['members']['a']['rates']['review_error_detection']['ci95_wilson'] is not None
    for secret in ('PRIVATE','sample_id','attempt','-READ','custody'):
        assert secret not in json.dumps(out)


@pytest.mark.parametrize('fault',['missing-report','missing-qualification','missing-read','missing-score','wrong-schema','wrong-cohort','wrong-read','quality-unqualified','open','unsealed','duplicate-score','failed-score','wrong-count','duplicate-member','missing-control','wrong-run','wrong-attempt','metric','source-score','new-contact','exported','runtime-changed'])
def test_refuse_partial_mismatched_or_unqualified_process_feedback(fault):
    a=sources();r=a['reports']['second'];q=a['qualifications']['second'];m=q['members'][0]
    if fault=='missing-report':a['reports'].pop('second')
    elif fault=='missing-qualification':a['qualifications'].pop('second')
    elif fault=='missing-read':a['read_ids'].pop('second')
    elif fault=='missing-score':a['score_bindings'].pop('second')
    elif fault=='wrong-schema':r['schema']='unknown'
    elif fault=='wrong-cohort':r['cohort']='part'
    elif fault=='wrong-read':r['read_id']='foreign'
    elif fault=='quality-unqualified':q['status']='WAIT'
    elif fault=='open':m['state']='OPENED'
    elif fault=='unsealed':m['verified_seal']=False
    elif fault=='duplicate-score':m['official_successful_jobs']=2
    elif fault=='failed-score':m['failed_jobs']=1
    elif fault=='wrong-count':m['rows']=1
    elif fault=='duplicate-member':q['members'].append(deepcopy(m))
    elif fault=='missing-control':r['members'].pop('aa')
    elif fault=='wrong-run':r['members']['a']['source']['run_id']='other'
    elif fault=='wrong-attempt':r['members']['a']['source']['attempt_id']='other'
    elif fault=='metric':r['members']['a']['metrics']['review_false_alarm']['value']=0
    elif fault=='source-score':r['members']['a']['source']['official_score_result_sha256']='b'*64
    elif fault=='new-contact':r['contacts_added']['model']=1
    elif fault=='exported':r['learner_exported']=True
    else:r['runtime_changed']=True
    with pytest.raises(ValueError):join_complete_process_feedback(**a)


def test_independent_cohort_metrics_are_not_pooled_or_order_joined():
    a=sources();a['qualifications']['part']['members'].reverse()
    for r in a['reports']['second']['members'].values():
        r['rows'].reverse();r['intent_support']['samples'].reverse();r['delivery_stages']['rows'].reverse()
        from speech_aware_evidence_acquisition.rails.hashing import content_hash
        r['source']['ordered_sample_ids_sha256']=content_hash([x['sample_id'] for x in r['rows']])
    out=join_complete_process_feedback(**a)
    assert out['cohorts']['part']==out['cohorts']['second']
