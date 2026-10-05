"""Complete-population retention evidence over separate registered source cohorts.

Reuse the shared all-source READ/seal/score gate. Never pool standardized returns,
mutate the optimizer, adopt a policy, or dispatch an experiment from this reader.
"""
import json
import math
from pathlib import Path

from ..analysis.abstract_population_projection import project_registered_population
from ..analysis.abstract_population_sources import read_registered_population_sources
from . import system_context_learning as learning
from .experiment_population import load_population_config, population_accounting
from .hashing import content_hash
from .system_context_partitioned_learning import SCHEMA
from .system_text_policy import _read_pin, require


def qualify_partitioned_context_trial(archive, *, input_sha256, contract_pin, request,
                                     repo_root, data_root):
    """Return a root-review signal only for the exact complete prospective trial.

    No-change positions require explicit registration and remain in the evaluation.
    Invalid positions are held; this interface does not invent replacement policies.
    Raw terminal utility sums are a learning criterion, not a common Pareto frontier
    or a scientific efficacy claim. All source cohorts must share the frozen F1.
    """
    root,data=Path(repo_root).resolve(),Path(data_root).resolve()
    packet,plan,ids=learning._population_update_input(archive,input_sha256)
    require(packet['schema']==SCHEMA,'partitioned input required')
    contract=json.loads(_read_pin(contract_pin,root))
    require(set(contract)=={'schema','status','algorithm','iteration','source_packet',
            'original_update_record','trial_population','no_change_candidates','criterion','runtime_admission'}
            and contract['schema']=='saea-partitioned-context-trial-contract-v1'
            and contract['status']=='ROOT_REGISTERED'
            and contract['algorithm']==packet['algorithm'] and contract['iteration']==packet['iteration']
            and contract['criterion']=='strict-population-utility-sum' and contract['runtime_admission'] is False,
            'exact prospective partitioned trial contract required')
    require(isinstance(request,dict) and set(request)=={'source_registration_pin'},
            'evaluation requires a complete source join, never caller-entered scores')
    require(json.loads(_read_pin(contract['source_packet'],data))==packet,'trial source packet differs')
    base=archive.root/'context-learning/populations'/plan['batch_id']
    raw=json.loads((base/'response.json').read_text())
    result=json.loads((base/'result.json').read_text())
    require(json.loads(_read_pin(contract['original_update_record'],data))==result
            and result.get('status')=='recorded' and result.get('input_sha256')==input_sha256
            and result.get('response_sha256')==raw.get('response_sha256')==content_hash(raw.get('response_document'))
            and [r.get('candidate_id') for r in result.get('records',[])]==ids
            and all(r.get('status') in {'provisional','no-change'} for r in result['records']),
            'all original configured valid dispositions required')
    require(contract['no_change_candidates']==[r['candidate_id'] for r in result['records'] if r['status']=='no-change'],
            'explicit unchanged-position disposition required')
    expected={r['candidate_id']:r['bundle_id'] for r in result['records']}
    for row in result['records']:
        path=archive.root/'context-learning/updates'/f"{packet['algorithm']}-{packet['iteration']}-{row['update_id']}.json"
        require({'candidate_id':row['candidate_id'],**json.loads(path.read_text())}==row,
                'original per-position update record differs')
        archive.load_policy(row['bundle_id'])
    oldcfg=load_population_config(packet['source_population'],repo_root=root)
    cfg=load_population_config(contract['trial_population'],repo_root=root)
    require(cfg['cohorts']==oldcfg['cohorts'] and cfg['sampling']==oldcfg['sampling']
            and cfg['nodes']==oldcfg['nodes'] and cfg['execution']==oldcfg['execution'],
            'successor must retain every configured input, position and execution envelope')
    initial=json.loads(_read_pin(packet['registration'],root))
    projected=project_registered_population(projection_pin=initial['projection'],repo_root=root,
                                          data_root=data,policy_archive=archive)
    require(content_hash(projected['private_custody'])==packet['source_commitment']
            and projected['learner_view']==packet['learner_view'],'original complete feedback changed')
    before=read_registered_population_sources(source_registration_pin=projected['private_custody']['source_join'],
                                              repo_root=root,data_root=data)
    after=read_registered_population_sources(source_registration_pin=request['source_registration_pin'],
                                             repo_root=root,data_root=data)
    tags=[c['cohort_id'] for c in cfg['cohorts']]
    require(before['projection_config']==packet['source_population']
            and after['projection_config']==contract['trial_population']
            and list(before['private_families'])==list(after['private_families'])==tags,
            'all original and successor cohorts required')
    cohorts={};totals=[[],[]];common_reference=None
    for c in cfg['cohorts']:
        tag=c['cohort_id'];old=before['private_families'][tag];new=after['private_families'][tag]
        oe,orr,oreg,op,ocs,oct,oref=old
        ne,nr,nreg,np,ncs,nct,nref=new
        require(ocs==ncs==c['candidate_ids'] and oct==nct==c['control_ids']
                and orr['sample_ids']==nr['sample_ids']==c['sample_ids']
                and nr['family_id']!=orr['family_id'] and nr['run_ids']['read']!=orr['run_ids']['read']
                and nref==oref and all(np[k]==op[k] for k in ('sampling','measurement_profile','frozen_reference'))
                and np.get('learning_trial_contract')==contract_pin and np.get('iteration')==packet['iteration'],
                'successor source roster, reference, READ or protocol differs')
        if common_reference is None:common_reference=oref['f1']
        require(oref['f1']==common_reference,'population utility requires one frozen reference F1')
        require(set(oreg['member_bindings'])==set(nreg['member_bindings'])==set(ncs+nct),
                'complete candidate and control bindings required')
        for cid,b in nreg['member_bindings'].items():
            prior=oreg['member_bindings'][cid]
            require(b['bundle_id']==expected.get(cid,prior['bundle_id'])
                    and b['run_id']!=prior['run_id'] and b['attempt_id']!=prior['attempt_id'],
                    'exact children, unchanged controls and fresh attempts required')
            if cid in ncs:
                require(prior['bundle_id']==packet['policies'][cid]['bundle_id'],'source policy ancestry differs')
        groups=[];business=[]
        for index,family in enumerate((old,new)):
            e,r,reg,p,cs,ct,ref=family
            gs=learning._candidate_groups(e,r,reg,cs,ref)
            require([g['sample_id'] for g in gs]==c['sample_ids']
                    and all([m['candidate_id'] for m in g['members']]==cs for g in gs),
                    'complete ordered candidate trajectories required')
            values=[m['utility'] for g in gs for m in g['members']]
            require(all(type(v) in (int,float) and math.isfinite(v) for v in values),'finite official utilities required')
            totals[index].extend(values);groups.append(gs)
            business.append(learning.measured_rows(e,cs+ct,reg['member_bindings'],profile=p['measurement_profile']))
        cohorts[tag]={'before_groups':groups[0],'after_groups':groups[1],
                      'business_before':business[0],'business_after':business[1],
                      'before_commitment':content_hash(old),'after_commitment':content_hash(new)}
    for pin in (contract_pin,packet['registration'],packet['source_population'],contract['trial_population'],request['source_registration_pin']):
        _read_pin(pin,root)
    require(json.loads(_read_pin(contract['source_packet'],data))==packet
            and json.loads(_read_pin(contract['original_update_record'],data))==result
            and json.loads((base/'response.json').read_text())==raw,'inputs changed during qualification')
    for original_join,source_pin in ((before,projected['private_custody']['source_join']),
                                     (after,request['source_registration_pin'])):
        fresh=read_registered_population_sources(source_registration_pin=source_pin,repo_root=root,data_root=data)
        require(fresh==original_join,'source qualification or READ changed during measurement')
    total_before,total_after=map(math.fsum,totals)
    return {'schema':'saea-partitioned-context-qualified-trial-v1','contract':contract_pin,
        'trial_sources':request['source_registration_pin'],'input_sha256':input_sha256,
        'response_sha256':result['response_sha256'],'cohorts':cohorts,
        'candidate_trajectories':population_accounting(cfg)['candidate_trajectories'],
        'utility_before':total_before,'utility_after':total_after,'utility_increased':total_after>total_before,
        'criterion':contract['criterion'],'root_review_required':True,'formal_adoption':False,
        'runtime_admission':False,'automatic_next_iteration':False,'contacts_added':{'model':0,'scorer':0},
        'interpretation':'Complete reused-input optimization signal, not efficacy, causal node credit, '
                         'a pooled scientific frontier or formal policy adoption.'}
