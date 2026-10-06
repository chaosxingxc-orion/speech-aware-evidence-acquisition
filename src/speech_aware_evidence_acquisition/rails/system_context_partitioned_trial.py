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


def _source_identity(source):
    """Compare evidence exactly, excluding only a fresh verifier's wall-clock stamp.

    The complete source reader has already rechecked all READ authority, pins,
    seals and official jobs. Its known operational receipt records a new time
    on each read; that observation time is not an experiment source identity.
    Unknown schemas and every other field remain part of strict equality.
    """
    qualifications = {
        tag: {key: value for key, value in receipt.items()
              if not (receipt.get("schema") == "saea-configured-family-qualified-v1"
                      and key == "recorded_at_utc")}
        for tag, receipt in source["qualifications"].items()
    }
    return {**source, "qualifications": qualifications}


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
    require(packet['schema'] in (SCHEMA, 'saea-partitioned-context-optimizer-input-v2'),'partitioned input required')
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
    # A continuation binds additional rejected history/process evidence. Its
    # active-parent observation still belongs to the original registered projection.
    from .system_context_continuation import context_packet_lineage
    lineage = context_packet_lineage(archive, packet)
    lineage_registrations = [json.loads(_read_pin(p['registration'], root)) for p in lineage]
    parent_packet = lineage[-1]
    initial=json.loads(_read_pin(parent_packet['registration'],root))
    projected=project_registered_population(projection_pin=initial['projection'],repo_root=root,
                                          data_root=data,policy_archive=archive)
    require(content_hash(projected['private_custody'])==parent_packet['source_commitment']
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
        require(_source_identity(fresh)==_source_identity(original_join),
                'source qualification or READ changed during measurement')
    require(all(json.loads(_read_pin(p['registration'], root)) == registered
                for p, registered in zip(lineage, lineage_registrations, strict=True)),
            'continuation lineage registration changed')
    current, _, _ = learning._population_update_input(archive, input_sha256)
    require(current == packet, 'optimizer continuation or active-parent evidence changed')
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


def prepare_rejected_context_history(archive, *, registration_pin, repo_root, data_root):
    """Requalify an entire rejected trial as history while retaining original parents.

    Return an in-memory abstract observation and private exposure custody. Never
    activate children, persist optimizer state, reserve a proposal, or export to an
    actor. A future update must separately bind both this history and its parents.
    """
    from copy import deepcopy
    from ..analysis.abstract_population_sources import _external

    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    registration = json.loads(_read_pin(registration_pin, root))
    require(set(registration) == {'schema', 'status', 'input_sha256', 'trial_contract',
            'root_decision', 'successor_projection', 'runtime_admission'}
            and registration['schema'] == 'saea-rejected-context-history-registration-v1'
            and registration['status'] == 'ROOT_REGISTERED'
            and registration['runtime_admission'] is False,
            'registered history-only preparation required')
    decision = json.loads(_read_pin(registration['root_decision'], root))
    require(decision.get('schema') == 'saea-partitioned-context-root-retention-v1'
            and decision.get('decision') == 'REJECT_WHOLE_UPDATE_RETAIN_BEFORE_POPULATION'
            and decision.get('preserve_all_candidates') is True
            and decision.get('new_runtime_admission') is False
            and decision.get('new_learner_export') is False,
            'explicit root rejection with no activation required')
    saved = _external(decision['qualification'], data)
    qualified = qualify_partitioned_context_trial(archive,
        input_sha256=registration['input_sha256'], contract_pin=registration['trial_contract'],
        request={'source_registration_pin': saved['trial_sources']}, repo_root=root, data_root=data)
    require(qualified == saved and qualified['utility_increased'] is False
            and all(decision.get(k) == qualified[k] for k in
                    ('criterion', 'utility_before', 'utility_after')),
            'complete rejected trial and original root decision must agree')
    packet, _, ids = learning._population_update_input(archive, registration['input_sha256'])
    config = load_population_config(packet['source_population'], repo_root=root)
    contract = json.loads(_read_pin(registration['trial_contract'], root))
    original = json.loads(_read_pin(contract['original_update_record'], data))
    expected = {r['candidate_id']: r['bundle_id'] for r in original['records']}
    projected = project_registered_population(projection_pin=registration['successor_projection'],
        repo_root=root, data_root=data, policy_archive=archive)
    custody, view = projected['private_custody'], projected['learner_view']
    require(custody['source_join'] == qualified['trial_sources']
            and custody['projection_registration'] == registration['successor_projection'],
            'history must project the exact complete rejected successor sources')
    require(list(view['templates']) == [c['cohort_id'] for c in config['cohorts']],
            'every rejected source cohort required')
    exposures = set(packet['feedback_sample_ids'])
    documents = {}
    for cohort in config['cohorts']:
        templates = view['templates'][cohort['cohort_id']]
        require(list(templates) == cohort['candidate_ids'], 'every rejected candidate required')
        for cid, template in templates.items():
            document = archive.load_policy(expected[cid]).as_json()
            require(template == {'bundle_id': expected[cid], **{k: document[k]
                    for k in ('role_text', 'context_layout', 'node_context')}},
                    'history templates must match the evaluated rejected policies')
            documents[expected[cid]] = document
            for source in document['cumulative_sources']:
                exposures.update(source['sample_ids'])
    # Repeat immutable bindings after potentially long native-source projection.
    for key, value in ((registration_pin, registration), (registration['root_decision'], decision),
                       (registration['trial_contract'], contract)):
        require(json.loads(_read_pin(key, root)) == value, 'history authority changed during preparation')
    require(_external(decision['qualification'], data) == saved
            and json.loads(_read_pin(contract['original_update_record'], data)) == original,
            'history qualification or original proposal changed')
    for bundle, document in documents.items():
        require(archive.load_policy(bundle).as_json() == document, 'history policy changed')
    current, _, _ = learning._population_update_input(archive, registration['input_sha256'])
    require(current == packet, 'active parents changed during history preparation')
    return {'schema': 'saea-rejected-context-learning-history-v1',
        'active_parent_bundle_ids': {cid: packet['policies'][cid]['bundle_id'] for cid in ids},
        'learner_history': {'disposition': 'rejected-retain-before-population',
            'criterion': qualified['criterion'], 'utility_before': qualified['utility_before'],
            'utility_after': qualified['utility_after'], 'observation': deepcopy(view),
            'instructions': 'These evaluated policies are rejected historical attempts, not active parents. '
                'Use every adverse, favorable and no-change observation without retroactive selection. '
                'Keep source cohorts and their control pairs separate; node causal credit is unmeasured.'},
        'private_custody': {'registration': registration_pin,
            'qualification': decision['qualification'], 'source_projection': deepcopy(custody),
            'feedback_sample_ids': sorted(exposures), 'parent_input_sha256': packet['input_sha256']},
        'runtime_admission': False, 'learner_exported': False,
        'contacts_added': {'model': 0, 'scorer': 0}}
