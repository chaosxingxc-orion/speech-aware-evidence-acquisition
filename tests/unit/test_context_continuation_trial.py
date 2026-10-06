"""Exercise a real v2 continuation through the shared full-trial qualifier."""
from copy import deepcopy
import json
import pytest
from test_abstract_population_projection import setup, with_archive
from test_partitioned_context_learning import ready, response
from test_partitioned_context_continuation import continuation, advance_registration, run as prepare_continuation
from test_abstract_population_sources import pin
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails import system_context_partitioned_trial as subject
from speech_aware_evidence_acquisition.rails.system_context_partitioned_learning import partitioned_context_actor_view
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture(params=[1, 2, 3])
def continuation_trial(continuation, monkeypatch, request):
    s=continuation
    s.packet=prepare_continuation(s)
    for ordinal in range(2, request.param + 1):
        advance_registration(s, s.packet, ordinal)
        s.packet = prepare_continuation(s)
    h=content_hash(partitioned_context_actor_view(s.archive,input_sha256=s.packet['input_sha256']))
    learning.reserve_context_population_update(s.archive,input_sha256=s.packet['input_sha256'],actor_input_sha256=h)
    result=learning.record_context_population_update(s.archive,input_sha256=s.packet['input_sha256'],response_document=response(s.packet,h))
    batch=s.packet['population_update_plan']['batch_id']
    result_path=s.archive.root/f'context-learning/populations/{batch}/result.json'
    result_pin=pin(s.data,str(result_path.relative_to(s.data)),result)
    packet_path=s.archive.root/f'context-learning/inputs/partitioned-{batch}.json'
    packet_pin=pin(s.data,str(packet_path.relative_to(s.data)),s.packet)
    cfg=deepcopy(s.cfg);cfg['experiment_id']='process-aware-successor'
    cfgpin=pin(s.root,'next-config.json',cfg)
    contract={'schema':'saea-partitioned-context-trial-contract-v1','status':'ROOT_REGISTERED',
        'algorithm':s.packet['algorithm'],'iteration':s.packet['iteration'],
        'source_packet':packet_pin,'original_update_record':result_pin,'trial_population':cfgpin,
        'no_change_candidates':list(s.packet['policies']),'criterion':'strict-population-utility-sum',
        'runtime_admission':False}
    s.contract_pin=pin(s.root,'trial-contract.json',contract)
    s.after=deepcopy(s.joined);s.after['projection_config']=cfgpin
    bundles={r['candidate_id']:r['bundle_id'] for r in result['records']}
    for tag, family in s.after['private_families'].items():
        _,recipe,reg,protocol,_,_,_=family
        recipe['family_id']+='-next';recipe['run_ids']['read']+='-next'
        protocol.update(learning_trial_contract=s.contract_pin,iteration=s.packet['iteration'])
        for cid,binding in reg['member_bindings'].items():
            binding.update(run_id=binding['run_id']+'-next',attempt_id=binding['attempt_id']+'-next',
                bundle_id=bundles.get(cid,binding['bundle_id']))
    s.source_pin=pin(s.root,'successor-source.json',{})
    s.in_comparison = False
    def joined(*,source_registration_pin,**kwargs):
        if source_registration_pin == s.source_pin:
            s.in_comparison = True
        return deepcopy(s.after if source_registration_pin==s.source_pin else s.joined)
    monkeypatch.setattr(subject,'read_registered_population_sources',joined)
    return s


def qualify(s):
    return subject.qualify_partitioned_context_trial(s.archive,input_sha256=s.packet['input_sha256'],
        contract_pin=s.contract_pin,request={'source_registration_pin':s.source_pin},
        repo_root=s.root,data_root=s.data)


def test_v2_trial_requalifies_actual_active_parent_projection(continuation_trial):
    s=continuation_trial
    assert s.packet['source_commitment'] != s.parent['source_commitment']
    out=qualify(s)
    assert out['utility_before']==out['utility_after']
    assert set(out['cohorts'])==set(s.joined['private_families'])
    assert not out['formal_adoption'] and out['contacts_added']=={'model':0,'scorer':0}


@pytest.mark.parametrize('fault',['parent-projection','continuation-evidence','parent-registration'])
def test_v2_trial_rejects_changed_source_during_measurement(continuation_trial,monkeypatch,fault):
    s=continuation_trial
    original=learning.measured_rows
    def changed(*args,**kwargs):
        out=original(*args,**kwargs)
        if not s.in_comparison:
            return out
        if fault=='parent-projection':
            s.joined['qualifications']['cohort-1']['changed']=True
        else:
            key=s.packet['continuation_evidence'] if fault=='continuation-evidence' else s.parent['registration']
            ((s.archive.root if fault=='continuation-evidence' else s.root)/key['relpath']).write_text('{}')
        return out
    monkeypatch.setattr(learning,'measured_rows',changed)
    with pytest.raises(PolicyError):
        qualify(s)
