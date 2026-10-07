"""Member-only reads retain full source custody and separate real ledger authority."""
import copy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_system_architecture_read import scope_fixture
from test_slurp_solver_stage_attribution import _source, _answer, _reference, _saved_row
from speech_aware_evidence_acquisition.analysis import native_episode_source as native
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError

ROOT=Path(__file__).parents[2]
spec=importlib.util.spec_from_file_location('_test_manual_member_read',ROOT/'scripts/analysis/manual_architecture_member_read.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    return m.pin(path)


def member_fixture(tmp_path,monkeypatch):
    d,family,reg,owner,authority,roster,supplement,stage=scope_fixture(tmp_path,monkeypatch)
    family['analysis_roster']={'relpath':'roster.json','sha256':'r'*64}
    scope=m.architecture.validate_source_registration(family,reg,owner,repo_root=tmp_path,data_root=tmp_path/'data')
    reads={label:'MEMBER-'+label.upper()+'-READ' for label in scope['labels']}
    label=scope['labels'][0]
    recipe={'schema':m.SCHEMA,'family_id':family['family_id'],'expected_members':reg['expected_members'],
            'member_id':label,'member_binding':reg['member_bindings'][label],'sample_ids':family['sample_ids'],
            'runtime_sample_ids':scope['runtime_sample_ids'][label],'analysis_roster':family['analysis_roster'],
            'measurement_profile':family.get('measurement_profile'),'run_ids':{'read':reads[label]},
            'learner_export':False,'runtime_gold':False,'views':m.VIEWS}
    prospective={'schema':'saea-manual-member-read-prospective-scope-v1','member_read_ids':reads,
                 'experiment_population':family['experiment_population'],'analysis_roster':family['analysis_roster'],
                 'rows_per_member':len(family['sample_ids']),'contacts_added':{'model':0,'scorer':0,'tokenizer':0}}
    return recipe,family,reg,owner,scope,prospective


def signed(tmp_path,recipe,notes='ROOT COUNTERSIGNED after complete member qualification.'):
    path=tmp_path/'docs/readiness/member/recipe.json';record=save(path,recipe)
    relative={'relpath':path.relative_to(tmp_path).as_posix(),'sha256':record['sha256']}
    ledger=tmp_path/'docs/exposure-ledger.md'
    ledger.write_text('| run/experiment id | execution profile | split role | calls | artifacts | notes |\n|---|---|---|---|---|---|\n| '+
        ' | '.join([recipe['run_ids']['read'],'model-free-check','discovery','0',relative['relpath'],notes])+' |\n')
    spec={'family_id':recipe['family_id'],'expected_members':recipe['expected_members'],'read_registration':relative}
    return relative,spec,ledger


def test_actual_member_read_never_substitutes_for_family_read(tmp_path,monkeypatch):
    recipe,family,reg,owner,scope,prospective=member_fixture(tmp_path,monkeypatch)
    record,spec,ledger=signed(tmp_path,recipe)
    authority=m.reader.CLI.require_read_registration(spec,repo_root=tmp_path)
    assert m.validate_member_recipe(recipe,family,reg,scope,prospective,authority)==recipe['member_id']
    assert len(spec['expected_members'])==4
    # The existing full-family public gate stays unchanged even with real signed member authority.
    with pytest.raises(PolicyError,match='exact root manual READ'):
        m.architecture.validate_registration(family,reg,owner,authority,repo_root=tmp_path,data_root=tmp_path/'data')
    with pytest.raises(PolicyError,match='exact root manual READ'):
        m.architecture.validate_registration(family,reg,owner,{},repo_root=tmp_path,data_root=tmp_path/'data')


@pytest.mark.parametrize('fault',['unsigned','pending','duplicate','wrong-artifact','wrong-read'])
def test_real_member_ledger_refuses_before_source_or_metrics(tmp_path,monkeypatch,fault):
    recipe,*_=member_fixture(tmp_path,monkeypatch);record,spec,ledger=signed(tmp_path,recipe)
    text=ledger.read_text()
    if fault=='unsigned':text=text.replace('ROOT COUNTERSIGNED','DRAFT')
    elif fault=='pending':text=text.replace('complete member qualification.','countersignature pending.')
    elif fault=='duplicate':text+=text.splitlines()[-1]+'\n'
    elif fault=='wrong-artifact':text=text.replace(record['relpath'],'another.json')
    elif fault=='wrong-read':text=text.replace(recipe['run_ids']['read'],'WRONG-READ')
    ledger.write_text(text)
    reader=Mock();metrics=Mock();monkeypatch.setattr(m,'verify_native_episode_source',reader);monkeypatch.setattr(m,'build_slurp_process_metrics',metrics)
    with pytest.raises(PolicyError):m.run(recipe_pin=record,repo_root=tmp_path,data_root=tmp_path/'data',operational_pin={},output=tmp_path/'data/analysis/member')
    reader.assert_not_called();metrics.assert_not_called()
    assert not (tmp_path/'data/analysis/member').exists()


@pytest.mark.parametrize('fault',['singleton','wrong-member','member-binding','configured-order','runtime-order','duplicate-read','same-family-read','export','contrast','runtime-gold'])
def test_member_scope_preserves_every_original_source_identity(tmp_path,monkeypatch,fault):
    recipe,family,reg,owner,scope,prospective=member_fixture(tmp_path,monkeypatch)
    authority={'read_run_id':recipe['run_ids']['read'],'ledger_row_sha256':'a'*64}
    recipe=copy.deepcopy(recipe);prospective=copy.deepcopy(prospective)
    if fault=='singleton':recipe['expected_members']={recipe['member_id']:reg['expected_members'][recipe['member_id']]}
    elif fault=='wrong-member':recipe['member_id']='unknown'
    elif fault=='member-binding':recipe['member_binding']['attempt_id']='wrong'
    elif fault=='configured-order':recipe['sample_ids'].reverse()
    elif fault=='runtime-order':recipe['runtime_sample_ids'].reverse()
    elif fault=='duplicate-read':prospective['member_read_ids']['seed-aa']=prospective['member_read_ids']['seed']
    elif fault=='same-family-read':prospective['member_read_ids']['seed']=reg['read_id'];recipe['run_ids']['read']=reg['read_id'];authority['read_run_id']=reg['read_id']
    elif fault=='export':recipe['learner_export']=True
    elif fault=='contrast':recipe['comparison_groups']={}
    elif fault=='runtime-gold':recipe['runtime_gold']=True
    with pytest.raises(PolicyError):m.validate_member_recipe(recipe,family,reg,scope,prospective,authority)


@pytest.mark.parametrize('fault',[None,'duplicate-job','failed-job','partial-score','wrong-job','wrong-manifest'])
def test_unique_complete_original_score_metadata_with_absent_siblings(tmp_path,fault):
    data=tmp_path/'data';member={'run_id':'selected-run','attempt_id':'selected-attempt'}
    directory=data/'runs'/member['run_id']/member['attempt_id'];manifest=directory/'manifest.json';save(manifest,{'operational':True})
    job={'job_id':member['attempt_id'],'manifest':str(manifest),'returncode':0,'status':'succeeded','operation':'finalize'}
    jobs=[{'job_id':member['attempt_id'],'manifest':str(manifest)}]
    summary={'job_count':1,'succeeded':1,'failed':0,'include_per_sample':True,'jobs':[job]}
    if fault=='duplicate-job':jobs*=2
    elif fault=='failed-job':summary['failed']=1
    elif fault=='partial-score':summary['include_per_sample']=False
    elif fault=='wrong-job':job['job_id']='wrong'
    elif fault=='wrong-manifest':job['manifest']=str(tmp_path/'elsewhere.json')
    save(directory/'score-batch/batch-summary.json',summary);(directory/'score-jobs.jsonl').write_text(''.join(json.dumps(j)+'\n' for j in jobs))
    if fault is None:
        binding,pins=m.reader.member_source_binding('selected',member,{'path':'roster','sha256':'a'*64},data)
        assert binding['candidate_id']=='selected' and len(pins)==2
    else:
        with pytest.raises(PolicyError):m.reader.member_source_binding('selected',member,{},data)
    assert list((data/'runs').iterdir())==[directory.parent]


@pytest.mark.parametrize('fault',[None,'not-finalized','wrong-source','wrong-config','wrong-attempt','partial','duplicate','wrong-order'])
def test_verified_native_source_shape_then_exact_member_identity(tmp_path,fault):
    ids=['slurp:train:synthetic-'+str(i) for i in range(100)];runtime=list(reversed(ids))
    answer=_answer('weather','query',('city','paris'))
    source=_source({sid:[answer] for sid in runtime})
    member={'run_id':source.plan.run_id,'attempt_id':source.plan.attempt_id,'config_hash':source.composed.config_hash,'source_commit':'f'*40}
    manifest={'status':'COMPLETED','study_commit':member['source_commit'],'run_id':member['run_id'],
              'attempt':{'attempt_id':member['attempt_id']},'split':{'count':len(ids),'ids':ids},
              'config':{'config_hash':member['config_hash']},'plan':{'split_role':'discovery'}}
    bundle=VerifiedBundle(tmp_path/'manifest.json',manifest,None,tuple(source.output_rows[sid] for sid in runtime),
                          source.bundle.trace_records,frozenset(ids),'FINALIZED')
    source=replace(source,bundle=bundle)
    if fault=='not-finalized':source=replace(source,bundle=replace(bundle,attempt_state='OPENED'))
    elif fault=='wrong-source':manifest['study_commit']='0'*40
    elif fault=='wrong-config':manifest['config']['config_hash']='0'*64
    elif fault=='wrong-attempt':manifest['attempt']['attempt_id']='wrong'
    elif fault=='partial':manifest['split']['count']-=1
    elif fault=='duplicate':manifest['split']['ids']=[ids[0]]*len(ids)
    elif fault=='wrong-order':runtime.reverse()
    if fault is None:m.validate_manifest(manifest,source,member,ids,runtime)
    else:
        with pytest.raises(PolicyError):m.validate_manifest(manifest,source,member,ids,runtime)


def test_aggregate_business_is_pooled_and_keeps_unknown_tokens():
    ids=['slurp:train:synthetic-'+str(i) for i in range(100)];answer=_answer('weather','query',('city','paris'))
    rows=[_saved_row(_reference(s),answer) for s in ids]
    score={'per_sample':rows,'aggregate':{'identity_check':{'passed':True},'official':{'slu_f1':1.0},'port_micro':{'intent_accuracy':1.0}}}
    execution={s:{'reliable_completion':True,'model_calls':2,'tool_calls':0,'prompt_tokens':None,'completion_tokens':8} for s in ids}
    roster={s:{'sample_id':s,'utterance_id':s,'stratum':'a' if i<60 else 'b'} for i,s in enumerate(ids)}
    report=m.describe_business(score,execution,roster,ids)
    assert report['natural_mixture']=={'n':100,'slu_f1':1.0,'intent':1.0,'reliable_completion':1.0}
    assert [s['n'] for s in report['strata']]==[60,40]
    assert report['tokens']['prompt_tokens']=={'total':None,'unknown_rows':100}
    assert 'comparisons' not in report
    rows[-1]['sample_id']=rows[0]['sample_id']
    with pytest.raises(PolicyError):m.describe_business(score,execution,roster,ids)


def test_report_is_aggregate_only_and_retains_explicit_unknown_and_na():
    process={'schema':'saea-slurp-process-metrics-v2','metrics':{'support':{'unknown':100}},
        'conditioning_not_applicable':{'review_alarm':100},'rows':[{'text':'Synthetic answer must remain in custody'}],
        'custody':[{'example':'Do not expose'}],'delivery_stages':{'rows':[{}],'postprocessing':{'entity':{'unavailable':2}}}}
    clock={'samples':[{}],'content_sha256':'a'*64,'first_admitted_sample':{'admission_index':0},'excluding_first':{'n':99}}
    p,t=m.aggregate_only(process,clock,{'by_role':{'solver':{'contacts':100}}})
    assert 'rows' not in p and 'custody' not in p and 'rows' not in p['delivery_stages'] and 'samples' not in t
    assert p['metrics']['support']['unknown']==100 and p['conditioning_not_applicable']['review_alarm']==100
    assert 'Synthetic answer' not in json.dumps({'process':p,'timing':t})


def test_network_is_fenced_and_implementation_pins_are_source_only():
    import socket
    with m.no_contacts(),pytest.raises(RuntimeError):socket.socket().connect(('127.0.0.1',9))
    pins=m.implementation_pins()
    assert 'scripts/analysis/manual_architecture_member_read.py' in pins
    assert len(pins)>10



def completed100(tmp_path,monkeypatch):
    """Real saved-score/reference/process/timing APIs over a typed native source seam.

    Native seal acquisition and whole registration are fixture boundaries, tested
    separately. No fixture creates or opens any sibling result directory.
    """
    from speech_aware_evidence_acquisition.analysis import slurp_topn_diagnostics_cli as refs
    from speech_aware_evidence_acquisition.data.splits import prefixed,split_identity_hash
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    repo,data=tmp_path/'repo',tmp_path/'data';repo.mkdir();data.mkdir()
    ids=['slurp:train:fixture-'+str(i) for i in range(100)];runtime=ids[::-1]
    label='review-off';labels=['seed','seed-aa','review-off','solver-lookup']
    answer=_answer('weather','query',('city','paris'))
    source=_source({sid:[answer] for sid in runtime});values={'policy':'phase-native-review-revise-v1',
        'native_episode':{'review_loop':'off','roles':{'reviewer':{'max_iterations':0},'planner':{'max_iterations':0}},'max_revisions':0}}
    source=replace(source,composed=SimpleNamespace(config_hash='a'*64,values=values))
    run,attempt='RUN-REVIEW-OFF','ATTEMPT-REVIEW-OFF'
    source=replace(source,plan=SimpleNamespace(**{**vars(source.plan),'run_id':run,'attempt_id':attempt}))
    directory=data/'runs'/run/attempt;directory.mkdir(parents=True)
    trace=dict(source.bundle.trace_records)
    program=default_phase_program(values['policy']).program_id
    for i,sid in enumerate(runtime):
        trace[f'{sid}/{program}/sample-execution-timing']={'use_sample_execution_timing':{
            'schema':'saea-sample-execution-timing-v1','sample_id':sid,'execution_unit_id':None,'admission_index':i,
            'expected_samples':len(ids),'slot_count':4,'queue_depth':4,'batch_started_ns':1000,
            'admitted_ns':1000+i*1000,'finished_ns':2001000+i*1000,'status':'completed','error_type':None}}
    outputs=tuple(source.output_rows[s] for s in runtime)
    outputs_path=directory/'outputs.jsonl';outputs_path.write_text(''.join(json.dumps(x)+'\n' for x in outputs))
    formal=[]
    for rid,payload in trace.items():
        channel='MODEL_REQUEST' if rid.endswith('/request') else 'MODEL_RESPONSE' if rid.endswith('/response') else 'USE'
        formal.append({'record_id':rid,'channel':channel,'payload':payload})
    trace_path=directory/'trace.jsonl';trace_path.write_text(''.join(json.dumps(x)+'\n' for x in formal))
    official={'per_sample':[_saved_row(_reference(s),answer) for s in runtime],
        'aggregate':{'identity_check':{'passed':True},'official':{'slu_f1':1.0},'port_micro':{'intent_accuracy':1.0}}}
    scores=save(directory/'scores.json',{'slurp-slu-official-train':official})
    state=save(directory/'state.json',{'state':'FINALIZED','run_id':run,'attempt_id':attempt})
    manifest={'status':'COMPLETED','run_id':run,'study_commit':'f'*40,'config':{'config_hash':'a'*64},
        'attempt':{'attempt_id':attempt,'state_path':state['path']},'split':{'count':len(ids),'ids':ids,'identity_hash':'b'*64},
        'plan':{'split_role':'discovery'},'outputs':m.pin(outputs_path),'raw_trace':m.pin(trace_path),
        'scores':scores,'scorers':['slurp-slu-official-train']}
    manifest_pin=save(directory/'manifest.json',manifest);phase=save(directory/'phase.json',{'fixture_phase':True})
    bundle=VerifiedBundle(Path(manifest_pin['path']),manifest,outputs_path,outputs,trace,frozenset(ids),'FINALIZED')
    source=replace(source,bundle=bundle,phase_artifact_sha256=phase['sha256'])
    job={'job_id':attempt,'manifest':manifest_pin['path'],'status':'succeeded','returncode':0,'operation':'finalize'}
    jobs=directory/'score-jobs.jsonl';jobs.write_text(json.dumps({'job_id':attempt,'manifest':manifest_pin['path']})+'\n')
    summary=save(directory/'score-batch/batch-summary.json',{'job_count':1,'succeeded':1,'failed':0,'include_per_sample':True,'jobs':[job]})
    roster_rows=[{'sample_id':s,'utterance_id':s,'stratum':'weather'} for s in ids]
    rp=save(repo/'roster.json',{'items':roster_rows});roster={'relpath':'roster.json','sha256':rp['sha256']}
    member={'run_id':run,'attempt_id':attempt,'config_hash':'a'*64,'source_commit':'f'*40}
    expected={x:run if x==label else 'UNSTARTED-'+x for x in labels}
    registration={'expected_members':expected,'member_bindings':{x:member if x==label else {'run_id':expected[x]} for x in labels},'read_id':'FAMILY-READ','measurement_profile':{'slot_count':4,'queue_depth':4}}
    family={'family_id':'manual-fixture-family','expected_members':expected,'sample_ids':ids,'analysis_roster':roster,
            'experiment_population':{'relpath':'population.json','sha256':'b'*64},'measurement_profile':registration['measurement_profile']}
    scope={'labels':labels,'source_commit':'f'*40,'runtime_sample_ids':{x:runtime for x in labels},
           'review_applicability':{x:{'schema':'saea-review-applicability-v1','config_sha256':'a'*64,'review_loop':'off'} for x in labels}}
    family_abs=save(repo/'family.json',family);family_pin={'relpath':'family.json','sha256':family_abs['sha256']}
    supplement={'projection':m.RewardProjection('native-counts','slurp-slu-official-train',('port_micro.slu_f1',),m.SLURP_NATIVE_FIELDS).as_json(),
                'stratum_metadata':roster}
    supp=save(repo/'supplement.json',supplement);supp_pin={'relpath':'supplement.json','sha256':supp['sha256']}
    read_ids={x:'MEMBER-'+x.upper()+'-READ' for x in labels}
    prospective={'schema':'saea-manual-member-read-prospective-scope-v1','member_read_ids':read_ids,
        'experiment_population':family['experiment_population'],'analysis_roster':roster,'rows_per_member':len(ids),
        'contacts_added':{'model':0,'scorer':0,'tokenizer':0}}
    prospect=save(data/'scope.json',prospective);prospect_pin={'relpath':'scope.json','sha256':prospect['sha256']}
    lock=save(repo/'lock.json',{});reference={'kind':'slurp-split','split_id':'train',
        'split_identity_hash':split_identity_hash(prefixed('slurp',runtime)),'lock':lock,'data_root':str(data),
        'allow_heldout':False,'allow_synthetic':False}
    for record in m.implementation_pins().values():
        target=repo/record['relpath'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/record['relpath']).read_bytes())
    recipe={'schema':m.SCHEMA,'family_id':family['family_id'],'expected_members':expected,'member_id':label,
        'member_binding':member,'sample_ids':ids,'runtime_sample_ids':runtime,'analysis_roster':roster,
        'measurement_profile':family['measurement_profile'],'run_ids':{'read':read_ids[label]},'learner_export':False,
        'runtime_gold':False,'views':m.VIEWS,'family_recipe':family_pin,'family_supplement':supp_pin,
        'member_read_scope':prospect_pin,'implementation':m.implementation_pins(),'frozen_worker_root':str(repo),'reference_binding':reference}
    recipe_pin,spec,ledger=signed(repo,recipe);authority=m.reader.CLI.require_read_registration(spec,repo_root=repo)
    operational={'read_authority':authority,'recipe':recipe_pin,'member_id':label,'runtime_gold':False,'learner_export':False,
        'manifest':manifest_pin,'phase':phase,'job_metadata':[m.pin(jobs),summary],'original_score':scores,'reference_binding':reference}
    operational_pin=save(data/'operational.json',operational)
    monkeypatch.setattr(m.reader,'load_documents',lambda *a:(family,registration,{},supplement))
    monkeypatch.setattr(m.architecture,'validate_source_registration',lambda *a,**k:scope)
    fixed_implementation=recipe['implementation']
    monkeypatch.setattr(m,'implementation_pins',lambda:fixed_implementation)
    calls=[]
    def verify(**kwargs):
        assert str(kwargs['manifest_path'])==manifest_pin['path'] and kwargs['expected_manifest_sha256']==manifest_pin['sha256']
        assert str(kwargs['phase_artifact_path'])==phase['path'] and kwargs['expected_phase_sha256']==phase['sha256']
        assert kwargs['repo_root']==repo;calls.append('native-source');return source
    monkeypatch.setattr(m,'verify_native_episode_source',verify)
    monkeypatch.setattr(m,'require_clean_study_repo',lambda p:'f'*40)
    monkeypatch.setattr(m,'load_lock',lambda *a:{})
    monkeypatch.setattr(refs,'load_lock',lambda *a:{})
    monkeypatch.setattr(m,'load_slurp_ontology',lambda *a:SimpleNamespace(entity_types={'city':()},intents=('weather_query',)))
    references=[replace(_reference(s),split='train') for s in ids]
    monkeypatch.setattr(m,'load_slurp_split',lambda *a,**k:references)
    return SimpleNamespace(args={'recipe_pin':recipe_pin,'repo_root':repo,'data_root':data,'operational_pin':operational_pin,
                'output':data/'analysis/member'},source=source,calls=calls,operational=operational,ledger=ledger,jobs=jobs,
                summary_path=Path(summary['path']),metadata=operational,recipe=recipe,manifest=manifest)


def test_completed100_uses_real_score_reference_process_and_timing_joins_with_siblings_absent(tmp_path,monkeypatch):
    f=completed100(tmp_path,monkeypatch)
    with m.no_contacts():report=m.run(**f.args)
    assert f.calls==['native-source']
    assert report['business']['natural_mixture']['n']==100
    assert report['business']['natural_mixture']['slu_f1']==1.0
    assert report['timing']['excluding_first']['count']==99
    assert report['process']['sample_count']==100
    assert report['process']['conditioning_not_applicable']['review_alarm']==100
    assert not report['learner_export'] and report['comparisons'] is None
    assert '"paris"' not in json.dumps(report)
    assert '"per_sample":' not in json.dumps(report)
    assert 'samples' not in report['timing'] and 'timing_trace_records' not in report['timing']
    assert len(list((f.args['data_root']/'runs').iterdir()))==1
    assert (f.args['output']/'custody/saved-score/complete-score-receipt.json').exists()


@pytest.mark.parametrize('defect',['read','seal','source','order','failed-score','duplicate-job','late-score'])
def test_completed_member_refuses_custody_defect_without_descriptive_report(tmp_path,monkeypatch,defect):
    from dataclasses import replace
    f=completed100(tmp_path,monkeypatch)
    if defect=='read':
        f.ledger.write_text(f.ledger.read_text().replace('ROOT COUNTERSIGNED','UNSIGNED'))
    elif defect=='seal':
        bad=replace(f.source,bundle=replace(f.source.bundle,attempt_state='OPENED'))
        monkeypatch.setattr(m,'verify_native_episode_source',lambda **k:bad)
    elif defect=='source':
        f.manifest['study_commit']='e'*40
    elif defect=='order':
        bad=replace(f.source,sample_ids=tuple(reversed(f.source.sample_ids)))
        monkeypatch.setattr(m,'verify_native_episode_source',lambda **k:bad)
    elif defect in ('failed-score','duplicate-job'):
        summary=json.loads(f.summary_path.read_text())
        if defect=='failed-score':summary['failed']=1
        else:summary['jobs']*=2;summary['job_count']=2;summary['succeeded']=2
        f.summary_path.write_text(json.dumps(summary))
    else:
        original=m.describe_business
        def changed(*a,**k):
            result=original(*a,**k)
            Path(f.operational['original_score']['path']).write_text('{}')
            return result
        monkeypatch.setattr(m,'describe_business',changed)
    with m.no_contacts(),pytest.raises((ValueError,RuntimeError,AssertionError)):
        m.run(**f.args)
    assert not (f.args['output']/'report.json').exists()
