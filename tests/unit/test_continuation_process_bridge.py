"""Complete process reports enter the existing continuation through checked custody."""
from copy import deepcopy
import json
import pytest
from test_complete_process_feedback import sources
from test_abstract_population_projection import setup, with_archive
from test_partitioned_context_learning import ready
from test_partitioned_context_continuation import continuation, run
from test_abstract_population_sources import pin
from speech_aware_evidence_acquisition.analysis.continuation_process_bridge import build_continuation_process_backfill
from speech_aware_evidence_acquisition.analysis.abstract_process_feedback import project_process_feedback, compact_process_feedback
from speech_aware_evidence_acquisition.rails.system_context_partitioned_learning import partitioned_context_actor_view


def registered(a):
    source = {'relpath':'whole-trial-sources.json','sha256':'b'*64}
    reg = {'schema':'saea-slurp-process-backfill-v1','status':'ROOT_REGISTERED',
        'source_registration':source,'cohorts':[
            {'cohort_id':c['cohort_id'],'members':[{'member_id':mid,**value} for mid,value in a['score_bindings'][c['cohort_id']].items()]}
            for c in a['config']['cohorts']]}
    trial = {'schema':'saea-partitioned-context-qualified-trial-v1','trial_sources':source,
        'cohorts':{c['cohort_id']:{} for c in a['config']['cohorts']},
        'candidate_trajectories':sum(len(c['candidate_ids'])*len(c['sample_ids']) for c in a['config']['cohorts']),
        'root_review_required':True,'formal_adoption':False,'runtime_admission':False,
        'contacts_added':{'model':0,'scorer':0}}
    return reg,trial


def build(a, reg, trial):
    return build_continuation_process_backfill(config=a['config'], reports=a['reports'],
        qualifications=a['qualifications'], read_ids=a['read_ids'],
        process_registration=reg, registration_sha256='c'*64, trial_qualification=trial)


def test_bridge_preserves_private_sources_and_existing_numeric_projection():
    a=sources();reg,trial=registered(a);out=build(a,reg,trial)
    assert out['schema']=='saea-complete-slurp-process-backfill-v1'
    assert out['families']=={tag:r['members'] for tag,r in a['reports'].items()}
    assert not out['learner_exported'] and not out['runtime_admission']
    view=project_process_feedback(out,config=a['config'],bindings=a['score_bindings'])
    assert view['cohorts']['part']['members']['a']['model_transitions']['entity']['correct_to_wrong']==1
    assert 'PRIVATE' not in json.dumps(view)
    a['reports']['part']['members'].clear()
    assert out['families']['part']


@pytest.mark.parametrize('fault',['missing-cohort','duplicate-cohort','missing-control','duplicate-member',
    'unregistered','wrong-source','wrong-trial','partial-trial','wrong-budget','runtime','new-contact',
    'unsealed','wrong-score','metric'])
def test_bridge_refuses_partial_or_unbound_statistics(fault):
    a=sources();reg,trial=registered(a)
    if fault=='missing-cohort':reg['cohorts'].pop()
    elif fault=='duplicate-cohort':reg['cohorts'].append(deepcopy(reg['cohorts'][0]))
    elif fault=='missing-control':reg['cohorts'][0]['members'].pop()
    elif fault=='duplicate-member':reg['cohorts'][0]['members'].append(deepcopy(reg['cohorts'][0]['members'][0]))
    elif fault=='unregistered':reg['status']='DRAFT'
    elif fault=='wrong-source':trial['trial_sources']['sha256']='d'*64;reg['source_registration']={'relpath':'other','sha256':'b'*64}
    elif fault=='wrong-trial':trial['schema']='other'
    elif fault=='partial-trial':trial['cohorts'].pop('part')
    elif fault=='wrong-budget':trial['candidate_trajectories']+=1
    elif fault=='runtime':trial['runtime_admission']=True
    elif fault=='new-contact':trial['contacts_added']['model']=1
    elif fault=='unsealed':a['qualifications']['part']['members'][0]['verified_seal']=False
    elif fault=='wrong-score':reg['cohorts'][0]['members'][0]['score_result']['sha256']='d'*64
    else:a['reports']['part']['members']['a']['metrics']['review_false_alarm']['value']=0
    with pytest.raises(ValueError):build(a,reg,trial)


def test_bridge_flows_through_actual_registered_continuation(continuation):
    s=continuation;a={'config':s.cfg,'reports':{},'qualifications':{},'read_ids':{},'score_bindings':{}}
    for c in s.cfg['cohorts']:
        tag=c['cohort_id'];members=deepcopy(s.process['families'][tag]);qualified=[]
        for mid,report in members.items():
            report['source'].update(run_id=tag+'-'+mid,attempt_id=tag+'-'+mid+'-attempt')
            qualified.append({'member':mid,'run_id':tag+'-'+mid,'attempt_id':tag+'-'+mid+'-attempt',
                'rows':len(c['sample_ids']),'state':'FINALIZED','verified_seal':True,'official_successful_jobs':1,'failed_jobs':0})
        a['read_ids'][tag]=tag+'-READ'
        a['reports'][tag]={'schema':'saea-complete-cohort-process-metrics-v1','cohort':tag,'read_id':tag+'-READ',
            'members':members,'contacts_added':{'model':0,'official_scorer':0},'learner_exported':False,'runtime_changed':False}
        a['qualifications'][tag]={'status':'ALL_MEMBERS_OPERATIONALLY_QUALIFIED','read_id':tag+'-READ','members':qualified}
        a['score_bindings'][tag]={mid:{'score_result':{'sha256':'a'*64}} for mid in members}
    _,trial=registered(a);trial['trial_sources']=s.process_reg['source_registration']
    out=build_continuation_process_backfill(config=s.cfg,reports=a['reports'],qualifications=a['qualifications'],
        read_ids=a['read_ids'],process_registration=s.process_reg,
        registration_sha256=s.process_reg_pin['sha256'],trial_qualification=trial)
    s.preceipt['result']=pin(s.data,'bridged-process-private.json',out,True)
    s.reg['process_completion']=pin(s.root,'bridged-process-complete.json',s.preceipt)
    s.regpin=pin(s.root,'bridged-continuation.json',s.reg)
    packet=run(s)
    actor=partitioned_context_actor_view(s.archive,input_sha256=packet['input_sha256'])
    expected=compact_process_feedback(project_process_feedback(out,config=s.cfg,bindings=a['score_bindings']))
    assert actor['process_feedback']==expected
    assert 'PRIVATE' not in json.dumps(actor)
