"""Continuation keeps rejected attempts as evidence and never replaces active parents."""
from copy import deepcopy
import json
import pytest
from test_abstract_population_projection import setup, with_archive
from test_partitioned_context_learning import ready, prepare, response
from test_abstract_population_sources import pin
from test_abstract_process_feedback import fixture
from speech_aware_evidence_acquisition.analysis.slurp_process_metrics import aggregate_process_metrics
from speech_aware_evidence_acquisition.rails import system_context_continuation as subject
from speech_aware_evidence_acquisition.rails import system_context_partitioned_learning as partitioned
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture
def continuation(ready):
    s=ready
    for tag, family in s.joined['private_families'].items():
        _, recipe, reg, protocol, _, _, _ = family
        recipe['run_ids'] = {'read': tag+'-old-read'}
        protocol.update(sampling=s.cfg['sampling'], frozen_reference={'sha256':'a'*64})
        for cid, binding in reg['member_bindings'].items():
            binding.update(run_id=tag+'-'+cid, attempt_id=tag+'-attempt-'+cid)
    s.parent=prepare(s)
    source_pin=pin(s.root,"history-sources.json",{"projection_config":s.parent["source_population"]})
    s.history={'schema':'saea-rejected-context-learning-history-v1',
        'active_parent_bundle_ids':{cid:p['bundle_id'] for cid,p in s.parent['policies'].items()},
        'learner_history':{'disposition':'rejected-retain-before-population','criterion':'strict-population-utility-sum',
            'utility_before':10.,'utility_after':9.,'observation':deepcopy(s.parent['learner_view']),'instructions':'History only.'},
        'private_custody':{'source_projection':{'source_join':source_pin},'parent_input_sha256':s.parent['input_sha256'],
            'feedback_sample_ids':sorted(s.parent['feedback_sample_ids']+['slurp:train:PRIVATE_HISTORY'])},
        'runtime_admission':False,'learner_exported':False,'contacts_added':{'model':0,'scorer':0}}
    template=fixture()[0]['families']['part']['a']
    s.process={'schema':'saea-complete-slurp-process-backfill-v1','families':{},'registration_sha256':'placeholder',
               'contacts_added':{'model':0,'official_scorer':0},'learner_exported':False,'runtime_admission':False}
    cohorts=[]
    for c in s.cfg['cohorts']:
        family={};members=[]
        for mid in c['candidate_ids']+c['control_ids']:
            a=deepcopy(template)
            for name in ('rows',):
                for row,sid in zip(a[name],c['sample_ids'],strict=True):row['sample_id']=sid
            for row,sid in zip(a['intent_support']['samples'],c['sample_ids'],strict=True):row['sample_id']=sid
            for row,sid in zip(a['delivery_stages']['rows'],c['sample_ids'],strict=True):row['sample_id']=sid
            a.update(aggregate_process_metrics(a['rows']))
            a['source']['ordered_sample_ids_sha256']=content_hash(c['sample_ids'])
            family[mid]=a;members.append({'member_id':mid,'score_result':{'sha256':'a'*64}})
        s.process['families'][c['cohort_id']]=family
        cohorts.append({'cohort_id':c['cohort_id'],'members':members})
    s.process_reg={'schema':'saea-slurp-process-backfill-v1','status':'ROOT_REGISTERED','cohorts':cohorts,'source_registration':source_pin}
    s.process_reg_pin=pin(s.root,'process-reg.json',s.process_reg)
    s.process['registration_sha256']=s.process_reg_pin['sha256']
    hpin=pin(s.data,'history-private.json',s.history,True)
    ppin=pin(s.data,'process-private.json',s.process,True)
    s.hreceipt={'schema':'saea-rejected-history-preparation-complete-v1','status':'COMPLETE','output':hpin,
                'runtime_admission':False,'learner_exported':False}
    s.preceipt={'schema':'saea-complete-process-backfill-reviewed-v1','status':'COMPLETE_ROOT_REVIEWED','result':ppin,
                'runtime_admission':False,'learner_exported':False}
    s.reg={'schema':'saea-partitioned-context-continuation-registration-v1','status':'ROOT_REGISTERED',
        'parent_input_sha256':s.parent['input_sha256'],'iteration':s.parent['iteration']+1,
        'population_update_plan':dict(s.parent['population_update_plan'],batch_id='next-with-process'),
        'history_completion':pin(s.root,'history-complete.json',s.hreceipt),
        'process_completion':pin(s.root,'process-complete.json',s.preceipt),
        'process_registration':s.process_reg_pin,'max_actor_input_bytes':2000000,'runtime_admission':False}
    s.regpin=pin(s.root,'continuation.json',s.reg)
    return s


def run(s):
    return subject.prepare_context_continuation(s.archive,registration_pin=s.regpin,repo_root=s.root,data_root=s.data)


def test_registered_continuation_reuses_shared_compiler_and_retains_history_exposure(continuation):
    s=continuation;p=run(s)
    view=partitioned.partitioned_context_actor_view(s.archive,input_sha256=p['input_sha256'])
    assert p['policies']==s.parent['policies']
    assert view['rejected_history']['disposition']=='rejected-retain-before-population'
    assert set(view['process_feedback']['cohorts'])=={'cohort-0','cohort-1'}
    assert 'slurp:train:PRIVATE_HISTORY' in p['feedback_sample_ids']
    for secret in ['PRIVATE_','slurp:train:',str(s.data),'source_pins','private_custody']:
        assert secret not in json.dumps(view)
    h=content_hash(view)
    learning.reserve_context_population_update(s.archive,input_sha256=p['input_sha256'],actor_input_sha256=h)
    out=learning.record_context_population_update(s.archive,input_sha256=p['input_sha256'],response_document=response(p,h))
    assert len(out['records'])==len(p['policies'])
    child=s.archive.load_policy(out['records'][0]['bundle_id']).as_json()
    assert 'slurp:train:PRIVATE_HISTORY' in {sid for src in child['cumulative_sources'] for sid in src['sample_ids']}
    with pytest.raises(PolicyError): run(s)


@pytest.mark.parametrize('fault',['history-pin','process-pin','unreviewed','promote','parent','budget','iteration','membership','source-join'])
def test_bad_continuation_never_reserves_proposals(continuation,fault):
    s=continuation
    if fault=='history-pin':(s.data/'history-private.json').write_text('{}')
    elif fault=='process-pin':(s.data/'process-private.json').write_text('{}')
    elif fault=='unreviewed':
        s.preceipt['status']='RUNNING';s.reg['process_completion']=pin(s.root,'process-complete.json',s.preceipt)
    elif fault in ('promote','parent','membership'):
        if fault=='promote':s.history['learner_history']['disposition']='adopt'
        elif fault=='parent':s.history['active_parent_bundle_ids']['candidate-0']='other'
        else:s.history['learner_history']['observation']['templates'].pop('cohort-1')
        s.hreceipt['output']=pin(s.data,'history-private.json',s.history,True)
        s.reg['history_completion']=pin(s.root,'history-complete.json',s.hreceipt)
    elif fault=='source-join':
        s.process_reg['source_registration']['sha256']='c'*64
        s.reg['process_registration']=pin(s.root,'process-reg.json',s.process_reg)
        s.process['registration_sha256']=s.reg['process_registration']['sha256']
        s.preceipt['result']=pin(s.data,'process-private.json',s.process,True)
        s.reg['process_completion']=pin(s.root,'process-complete.json',s.preceipt)
    elif fault=='budget':s.reg['max_actor_input_bytes']=1
    else:s.reg['iteration']+=2
    s.regpin=pin(s.root,'continuation.json',s.reg)
    with pytest.raises((PolicyError,ValueError)):run(s)
    assert not (s.archive.root/'context-learning/populations').exists()


def test_modified_feedback_cannot_be_rehashed_into_actor_input(continuation):
    s=continuation;p=run(s)
    ep=s.archive.root/p['continuation_evidence']['relpath']
    ev=json.loads(ep.read_text());ev['process_feedback']['cohorts']['cohort-0']['members']['candidate-0']['rates'][0][4]=0
    ep.write_text(json.dumps(ev))
    with pytest.raises(PolicyError):partitioned.partitioned_context_actor_view(s.archive,input_sha256=p['input_sha256'])


def test_history_validates_its_own_configuration_identity(continuation):
    s=continuation
    cfg=deepcopy(s.cfg);cfg['experiment_id']='different-evaluated-successor'
    cfgpin=pin(s.root,'successor-config.json',cfg)
    joinpin=pin(s.root,'history-sources.json',{'projection_config':cfgpin})
    s.history['private_custody']['source_projection']['source_join']=joinpin
    s.history['learner_history']['observation']['population']['population_config_sha256']=content_hash(cfg)
    s.hreceipt['output']=pin(s.data,'history-private.json',s.history,True)
    s.reg['history_completion']=pin(s.root,'history-complete.json',s.hreceipt)
    s.process_reg['source_registration']=joinpin
    s.reg['process_registration']=pin(s.root,'process-reg.json',s.process_reg)
    s.process['registration_sha256']=s.reg['process_registration']['sha256']
    s.preceipt['result']=pin(s.data,'process-private.json',s.process,True)
    s.reg['process_completion']=pin(s.root,'process-complete.json',s.preceipt)
    s.regpin=pin(s.root,'continuation.json',s.reg)
    packet=run(s)
    assert packet['source_population']==s.parent['source_population']
    view=partitioned.partitioned_context_actor_view(s.archive,input_sha256=packet['input_sha256'])
    assert view['rejected_history']['observation']['population']['population_config_sha256']==content_hash(cfg)


def advance_registration(s, parent, ordinal):
    """Create fresh immutable source identities for a further rejected update."""
    s.parent = parent
    history = deepcopy(s.history)
    history['private_custody']['parent_input_sha256'] = parent['input_sha256']
    history['private_custody']['feedback_sample_ids'] = sorted(
        set(parent['feedback_sample_ids']) | {f'slurp:train:PRIVATE_HISTORY_{ordinal}'})
    history['learner_history']['utility_after'] = 9. - ordinal
    receipt = dict(s.hreceipt, output=pin(s.data, f'history-{ordinal}.json', history, True))
    s.reg = dict(s.reg, parent_input_sha256=parent['input_sha256'],
        iteration=parent['iteration'] + 1,
        population_update_plan=dict(parent['population_update_plan'], batch_id=f'next-process-{ordinal}'),
        history_completion=pin(s.root, f'history-complete-{ordinal}.json', receipt))
    s.regpin = pin(s.root, f'continuation-{ordinal}.json', s.reg)


def test_repeated_continuation_preserves_all_history_process_and_exposure(continuation):
    s = continuation
    original = s.parent
    first = run(s)
    first_view = partitioned.partitioned_context_actor_view(s.archive, input_sha256=first['input_sha256'])
    assert 'prior_continuations' not in first_view
    advance_registration(s, first, 2)
    second = run(s)
    advance_registration(s, second, 3)
    third = run(s)
    view = partitioned.partitioned_context_actor_view(s.archive, input_sha256=third['input_sha256'])
    assert third['policies'] == original['policies']
    assert [row['iteration'] for row in view['prior_continuations']] == [first['iteration'], second['iteration']]
    assert view['prior_continuations'][0]['rejected_history'] == first_view['rejected_history']
    assert view['prior_continuations'][0]['process_feedback'] == first_view['process_feedback']
    assert [row['rejected_history']['utility_after'] for row in view['prior_continuations']] == [9., 7.]
    assert view['rejected_history']['utility_after'] == 6.
    assert set(first['feedback_sample_ids']) <= set(second['feedback_sample_ids']) <= set(third['feedback_sample_ids'])
    assert 'slurp:train:PRIVATE_HISTORY_3' in third['feedback_sample_ids']
    for secret in ['PRIVATE_', 'slurp:train:', str(s.data), 'source_pins', 'private_custody']:
        assert secret not in json.dumps(view)
    h = content_hash(view)
    learning.reserve_context_population_update(s.archive, input_sha256=third['input_sha256'], actor_input_sha256=h)
    out = learning.record_context_population_update(s.archive, input_sha256=third['input_sha256'], response_document=response(third, h))
    child = s.archive.load_policy(out['records'][0]['bundle_id']).as_json()
    assert set(third['feedback_sample_ids']) <= {sid for src in child['cumulative_sources'] for sid in src['sample_ids']}


def test_repeated_continuation_rejects_modified_ancestor(continuation):
    s = continuation
    first = run(s)
    advance_registration(s, first, 2)
    second = run(s)
    (s.archive.root / first['continuation_evidence']['relpath']).write_text('{}')
    with pytest.raises(PolicyError):
        partitioned.partitioned_context_actor_view(s.archive, input_sha256=second['input_sha256'])


def test_repeated_continuation_budget_includes_prior_history(continuation):
    s = continuation
    first = run(s)
    first_view = partitioned.partitioned_context_actor_view(s.archive, input_sha256=first['input_sha256'])
    advance_registration(s, first, 2)
    s.reg['max_actor_input_bytes'] = len(json.dumps(first_view, ensure_ascii=True).encode()) + 100
    s.regpin = pin(s.root, 'bounded-second.json', s.reg)
    with pytest.raises(PolicyError, match='byte budget'):
        run(s)
    assert not (s.archive.root / 'context-learning/inputs/partitioned-next-process-2.json').exists()
    assert not (s.archive.root / 'context-learning/populations').exists()
