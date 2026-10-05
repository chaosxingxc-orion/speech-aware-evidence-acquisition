"""Qualify the complete configured successor without pooling historical cohorts."""
from copy import deepcopy
import json
import pytest
from test_abstract_population_projection import setup, with_archive
from test_partitioned_context_learning import ready, prepare, response
from test_abstract_population_sources import pin
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails import system_context_partitioned_trial as subject
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture
def trial(ready, monkeypatch):
    s=ready
    for tag, family in s.joined['private_families'].items():
        _,recipe,reg,protocol,_,_,_=family
        recipe['run_ids']={'read':tag+'-old-read'}
        protocol.update(sampling=s.cfg['sampling'],frozen_reference={'sha256':'a'*64})
        for cid,b in reg['member_bindings'].items():
            b.update(run_id=tag+'-'+cid,attempt_id=tag+'-attempt-'+cid)
    s.packet=prepare(s)
    h=content_hash(s.packet['learner_view'])
    learning.reserve_context_population_update(s.archive,input_sha256=s.packet['input_sha256'],actor_input_sha256=h)
    s.result=learning.record_context_population_update(s.archive,input_sha256=s.packet['input_sha256'],response_document=response(s.packet,h))
    result_path=s.archive.root/'context-learning/populations/partitioned-next/result.json'
    s.result_pin=pin(s.data,str(result_path.relative_to(s.data)),s.result)
    packet_path=next((s.archive.root/'context-learning/inputs').glob('*.json'))
    s.packet_pin=pin(s.data,str(packet_path.relative_to(s.data)),s.packet)
    newcfg=deepcopy(s.cfg);newcfg['experiment_id']='successor'
    s.newcfg_pin=pin(s.root,'successor.json',newcfg)
    s.contract={'schema':'saea-partitioned-context-trial-contract-v1','status':'ROOT_REGISTERED',
        'algorithm':s.packet['algorithm'],'iteration':s.packet['iteration'],
        'source_packet':s.packet_pin,'original_update_record':s.result_pin,
        'trial_population':s.newcfg_pin,'no_change_candidates':list(s.packet['policies']),
        'criterion':'strict-population-utility-sum','runtime_admission':False}
    s.contract_pin=pin(s.root,'trial-contract.json',s.contract)
    s.after=deepcopy(s.joined);s.after['projection_config']=s.newcfg_pin
    bundles={r['candidate_id']:r['bundle_id'] for r in s.result['records']}
    for tag,family in s.after['private_families'].items():
        _,recipe,reg,protocol,_,_,_=family
        recipe['family_id']+='-next';recipe['run_ids']['read']+='-next'
        protocol.update(learning_trial_contract=s.contract_pin,iteration=s.packet['iteration'])
        for cid,b in reg['member_bindings'].items():
            b.update(run_id=b['run_id']+'-next',attempt_id=b['attempt_id']+'-next')
            b['bundle_id']=bundles.get(cid,b['bundle_id'])
    s.request={'source_registration_pin':pin(s.root,'trial-sources.json',{})}
    def joined(*,source_registration_pin,**kwargs):
        return deepcopy(s.after if source_registration_pin==s.request['source_registration_pin'] else s.joined)
    monkeypatch.setattr(subject,'read_registered_population_sources',joined)
    return s


def run(s):
    return subject.qualify_partitioned_context_trial(s.archive,input_sha256=s.packet['input_sha256'],
        contract_pin=s.contract_pin,request=s.request,repo_root=s.root,data_root=s.data)


def test_complete_trial_retains_nochange_positions_and_separate_controls(trial):
    s=trial; out=run(s)
    assert list(out['cohorts'])==['cohort-0','cohort-1']
    assert out['utility_before']==out['utility_after'] and not out['utility_increased']
    assert out['candidate_trajectories']==10
    assert out['formal_adoption'] is False and out['root_review_required']
    assert out['contacts_added']=={'model':0,'scorer':0}
    assert not (s.archive.root/'context-learning/iterations').exists()


@pytest.mark.parametrize('fault',['missing-last','wrong-child','changed-control','reused-attempt','reused-run',
    'reused-family','reused-read','roster','reference','sampling','measurement','contract','iteration'])
def test_refuse_incomplete_or_changed_successor(trial,fault):
    s=trial;tag='cohort-1';f=s.after['private_families'][tag];e,r,reg,p,cs,ct,ref=f
    if fault=='missing-last':s.after['private_families'].pop(tag)
    elif fault=='wrong-child':reg['member_bindings'][cs[-1]]['bundle_id']='f'*64
    elif fault=='changed-control':reg['member_bindings'][ct[-1]]['bundle_id']='f'*64
    elif fault=='reused-attempt':reg['member_bindings'][cs[-1]]['attempt_id']=s.joined['private_families'][tag][2]['member_bindings'][cs[-1]]['attempt_id']
    elif fault=='reused-run':reg['member_bindings'][cs[-1]]['run_id']=s.joined['private_families'][tag][2]['member_bindings'][cs[-1]]['run_id']
    elif fault=='reused-family':r['family_id']=s.joined['private_families'][tag][1]['family_id']
    elif fault=='reused-read':r['run_ids']['read']=s.joined['private_families'][tag][1]['run_ids']['read']
    elif fault=='roster':r['sample_ids'].reverse()
    elif fault=='reference':ref['f1']=.7
    elif fault=='sampling':p['sampling']['seed']+=1
    elif fault=='measurement':p['measurement_profile']={'different':True}
    elif fault=='contract':p['learning_trial_contract']={'relpath':'wrong','sha256':'f'*64}
    else:p['iteration']+=1
    with pytest.raises(PolicyError):run(s)


@pytest.mark.parametrize('fault',['draft','nochange','extra','config','criterion','record','packet'])
def test_prospective_contract_and_original_response_are_required(trial,fault):
    s=trial
    if fault=='draft':s.contract['status']='DRAFT'
    elif fault=='nochange':s.contract['no_change_candidates'].pop()
    elif fault=='extra':s.contract['automatic_adoption']=True
    elif fault=='config':
        cfg=deepcopy(s.cfg);cfg['cohorts'][-1]['sample_ids'].reverse()
        s.contract['trial_population']=pin(s.root,'badconfig.json',cfg)
    elif fault=='criterion':s.contract['criterion']='select-best-case'
    elif fault=='record':s.result['records'][-1]['status']='invalid';s.contract['original_update_record']=pin(s.data,s.result_pin['relpath'],s.result)
    else:s.packet['source_commitment']='f'*64;s.contract['source_packet']=pin(s.data,s.packet_pin['relpath'],s.packet)
    s.contract_pin=pin(s.root,'trial-contract.json',s.contract)
    with pytest.raises(PolicyError):run(s)


def test_incomplete_shared_join_cannot_return_a_partial_signal(trial,monkeypatch):
    original=subject.read_registered_population_sources
    def fail(**kwargs):
        if kwargs['source_registration_pin']==trial.request['source_registration_pin']:
            raise PolicyError('last seal missing')
        return original(**kwargs)
    monkeypatch.setattr(subject,'read_registered_population_sources',fail)
    with pytest.raises(PolicyError,match='last seal'):run(trial)


def test_strict_signal_uses_all_candidate_terminal_utilities(trial,monkeypatch):
    original=learning._candidate_groups
    def groups(e,r,*args):
        value=original(e,r,*args)
        if r['family_id'].endswith('-next'):
            value[-1]['members'][-1]['utility']+=.25
        return value
    monkeypatch.setattr(learning,'_candidate_groups',groups)
    out=run(trial)
    assert out['utility_after']-out['utility_before']==.5 and out['utility_increased']
    assert len(out['cohorts'])==2 and not out['formal_adoption']


@pytest.mark.parametrize('fault',['groups-order','groups-member','nonfinite','last-measurement'])
def test_incomplete_counts_or_costs_prevent_whole_result(trial,monkeypatch,fault):
    s=trial;original=learning._candidate_groups
    if fault=='last-measurement':
        measured=learning.measured_rows
        def fail(e,ids,*args,**kwargs):
            if ids[0]=='candidate-2':raise PolicyError('last measurement missing')
            return measured(e,ids,*args,**kwargs)
        monkeypatch.setattr(learning,'measured_rows',fail)
    else:
        def bad(e,r,*args):
            groups=original(e,r,*args)
            if r['family_id']=='family-cohort-1-next':
                if fault=='groups-order':groups.reverse()
                elif fault=='groups-member':groups[-1]['members'].pop()
                else:groups[-1]['members'][-1]['utility']=float('nan')
            return groups
        monkeypatch.setattr(learning,'_candidate_groups',bad)
    with pytest.raises(PolicyError,match='complete ordered|finite official|last measurement'):run(s)


def test_source_commitment_change_is_refused(trial,monkeypatch):
    original=subject.project_registered_population
    def bad(**kwargs):
        p=original(**kwargs);p['private_custody']['extra']='changed';return p
    monkeypatch.setattr(subject,'project_registered_population',bad)
    with pytest.raises(PolicyError,match='original complete feedback changed'):run(trial)


def test_contract_change_during_measurement_is_refused(trial,monkeypatch):
    original=learning.measured_rows
    def changed(*args,**kwargs):
        out=original(*args,**kwargs)
        (trial.root/trial.contract_pin['relpath']).write_text('{}')
        return out
    monkeypatch.setattr(learning,'measured_rows',changed)
    with pytest.raises(PolicyError):run(trial)


def test_caller_entered_reward_is_never_accepted(trial):
    trial.request['score']=1.
    with pytest.raises(PolicyError,match='never caller-entered'):run(trial)


def test_per_position_record_change_is_refused(trial):
    row=trial.result['records'][-1]
    p=trial.archive.root/'context-learning/updates'/f"{trial.packet['algorithm']}-{trial.packet['iteration']}-{row['update_id']}.json"
    d=json.loads(p.read_text());d['status']='invalid';p.write_text(json.dumps(d))
    with pytest.raises(PolicyError,match='per-position update'):run(trial)



def test_read_change_after_measurement_is_requalified(trial,monkeypatch):
    original=subject.read_registered_population_sources;counts={}
    def changed(**kwargs):
        key=kwargs['source_registration_pin']['relpath'];counts[key]=counts.get(key,0)+1
        result=original(**kwargs)
        if kwargs['source_registration_pin']==trial.request['source_registration_pin'] and counts[key]>1:
            result['qualifications']['cohort-1']['revoked']=True
        return result
    monkeypatch.setattr(subject,'read_registered_population_sources',changed)
    with pytest.raises(PolicyError,match='READ changed'):run(trial)


@pytest.mark.parametrize("changed_source", ["before", "after", "both"])
def test_fresh_operational_observation_time_does_not_change_trial_identity(trial, monkeypatch, changed_source):
    original = subject.read_registered_population_sources
    calls = {}
    def observed(**kwargs):
        key = kwargs["source_registration_pin"]["relpath"]
        calls[key] = calls.get(key, 0) + 1
        result = original(**kwargs)
        side = "after" if kwargs["source_registration_pin"] == trial.request["source_registration_pin"] else "before"
        for q in result["qualifications"].values():
            q["schema"] = "saea-configured-family-qualified-v1"
            tick = calls[key] if changed_source in (side, "both") else 1
            q["recorded_at_utc"] = f"2026-10-05T23:00:0{tick}+00:00"
        return result
    monkeypatch.setattr(subject, "read_registered_population_sources", observed)
    out = run(trial)
    assert out["utility_before"] == out["utility_after"]
    assert out["formal_adoption"] is False


@pytest.mark.parametrize("field", ["schema", "read_id", "recipe", "members", "attempt_metadata_pins",
    "job_metadata_pins", "frozen_commit", "status", "unknown_observation", "private_feedback"])
def test_requalification_still_refuses_every_non_observation_change(trial, monkeypatch, field):
    original = subject.read_registered_population_sources
    calls = {}
    def observed(**kwargs):
        key = kwargs["source_registration_pin"]["relpath"]
        calls[key] = calls.get(key, 0) + 1
        result = original(**kwargs)
        for q in result["qualifications"].values():
            q["schema"] = "saea-configured-family-qualified-v1"
            q["recorded_at_utc"] = f"2026-10-05T23:00:0{calls[key]}+00:00"
        if kwargs["source_registration_pin"] == trial.request["source_registration_pin"] and calls[key] > 1:
            if field == "private_feedback":
                result["private_families"]["cohort-1"][0]["recorded_at_utc"] = "changed-source-field"
            else:
                result["qualifications"]["cohort-1"][field] = "changed"
        return result
    monkeypatch.setattr(subject, "read_registered_population_sources", observed)
    with pytest.raises(PolicyError, match="source qualification or READ changed"):
        run(trial)


def test_unknown_qualification_schema_does_not_get_timestamp_exemption(trial, monkeypatch):
    original = subject.read_registered_population_sources
    calls = {}
    def observed(**kwargs):
        key = kwargs["source_registration_pin"]["relpath"]
        calls[key] = calls.get(key, 0) + 1
        result = original(**kwargs)
        for q in result["qualifications"].values():
            q.update(schema="unrecognized-qualification", recorded_at_utc=str(calls[key]))
        return result
    monkeypatch.setattr(subject, "read_registered_population_sources", observed)
    with pytest.raises(PolicyError, match="source qualification or READ changed"):
        run(trial)
