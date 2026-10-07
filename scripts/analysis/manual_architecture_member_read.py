#!/usr/bin/env python3
"""Read one completed manual member under its own exact READ; never compare arms."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

from speech_aware_evidence_acquisition.analysis import system_architecture_read as architecture
from speech_aware_evidence_acquisition.analysis.native_episode_source import verify_native_episode_source
from speech_aware_evidence_acquisition.analysis.slurp_process_metrics import build_slurp_process_metrics
from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli import load_verified_slurp_reference_records
from speech_aware_evidence_acquisition.analysis.system_cache_cost import export_system_sample_timing, export_system_node_timing
from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1
from speech_aware_evidence_acquisition.analysis.native_intent_support import validate_initial_intent_support_spec
from speech_aware_evidence_acquisition.core.bundle.git_commit import require_clean_study_repo
from speech_aware_evidence_acquisition.analysis.system_text_update import FIELDS
from speech_aware_evidence_acquisition.core.scoring_receipt import write_complete_saved_score_receipt, verify_complete_score_receipt
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split, load_slurp_ontology
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.reward_links import RewardProjection, SLURP_NATIVE_FIELDS
from speech_aware_evidence_acquisition.rails.system_text_feedback import _row_cost_and_terminal
from speech_aware_evidence_acquisition.rails.system_text_policy import _read_pin, require

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('_manual_member_shared_reader', ROOT/'scripts/analysis/system_text_pilot_read.py')
reader = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reader
spec.loader.exec_module(reader)
SCHEMA = 'saea-manual-architecture-member-descriptive-recipe-v1'
VIEWS = ['business-descriptive', 'process-descriptive', 'timing-descriptive']


def pin(path):
    path=Path(path).resolve()
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':str(path),'sha256':digest}


def absolute(record):
    require(set(record)=={'path','sha256'} and Path(record['path']).is_absolute()
            and pin(record['path'])==record, 'exact absolute raw source pin differs')
    return json.loads(Path(record['path']).read_bytes())


def implementation_pins():
    functions=[verify_native_episode_source,build_slurp_process_metrics,
               load_verified_slurp_reference_records,export_system_sample_timing,
               export_system_node_timing,pooled_f1,_row_cost_and_terminal,
               verify_complete_score_receipt,load_slurp_split,load_slurp_ontology]
    paths={Path(inspect.getfile(f)).resolve() for f in functions}
    paths.update([Path(__file__).resolve(),Path(reader.__file__).resolve(),Path(architecture.__file__).resolve(),
                  ROOT/'src/speech_aware_evidence_acquisition/rails/reward_links.py'])
    for name in ('slurp_solver_stage_attribution','native_candidate_stage_projections',
                 'native_intent_support','review_findings','slurp_topn_diagnostics'):
        paths.add(ROOT/'src/speech_aware_evidence_acquisition/analysis'/(name+'.py'))
    return {p.relative_to(ROOT).as_posix():{'relpath':p.relative_to(ROOT).as_posix(),
                'sha256':pin(p)['sha256']} for p in sorted(paths)}


@contextmanager
def no_contacts():
    def refuse(*args,**kwargs):raise RuntimeError('Member analysis refuses every network endpoint')
    with patch('socket.socket.connect',refuse),patch('socket.socket.connect_ex',refuse):yield


def validate_member_recipe(recipe, family_recipe, registration, scope, prospective, authority):
    label=recipe.get('member_id')
    require(recipe.get('schema')==SCHEMA and label in scope['labels']
            and recipe.get('learner_export') is False and recipe.get('runtime_gold') is False
            and recipe.get('views')==VIEWS
            and not any(k in recipe for k in ('comparison_groups','optimizer_export','learning_amendment')),
            'explicit member descriptive scope; no contrasts or export')
    require(recipe.get('family_id')==family_recipe['family_id']
            and recipe.get('expected_members')==registration['expected_members']
            and recipe.get('member_binding')==registration['member_bindings'][label]
            and recipe.get('sample_ids')==family_recipe['sample_ids']
            and recipe.get('runtime_sample_ids')==scope['runtime_sample_ids'][label]
            and recipe.get('analysis_roster')==family_recipe['analysis_roster']
            and recipe.get('measurement_profile')==family_recipe.get('measurement_profile')
            ==registration.get('measurement_profile'), 'member differs from complete source registration')
    reads=prospective.get('member_read_ids',{})
    require(prospective.get('schema')=='saea-manual-member-read-prospective-scope-v1'
            and prospective.get('experiment_population')==family_recipe['experiment_population']
            and prospective.get('analysis_roster')==recipe['analysis_roster']
            and prospective.get('rows_per_member')==len(recipe['sample_ids'])
            and set(reads)==set(scope['labels']) and len(set(reads.values()))==len(reads)
            and all(isinstance(v,str) and v for v in reads.values())
            and reads[label]==recipe.get('run_ids',{}).get('read')==authority.get('read_run_id')
            and authority.get('ledger_row_sha256')
            and reads[label]!=registration['read_id'], 'exact distinct prospective member READ required')
    require(prospective.get('contacts_added')=={'model':0,'scorer':0,'tokenizer':0}
            and all(type(v) is int for v in prospective['contacts_added'].values()),
            'prospective zero-contact scope differs')
    return label


def validate_manifest(manifest, source, member, ids, runtime):
    require(source.bundle.attempt_state=='FINALIZED' and manifest.get('status')=='COMPLETED'
            and manifest.get('run_id')==member['run_id']
            and manifest.get('study_commit')==member['source_commit']
            and manifest['config']['config_hash']==member['config_hash']==source.composed.config_hash
            and manifest['attempt']['attempt_id']==member['attempt_id']
            and manifest['plan']['split_role']=='discovery'
            and manifest['split']['count']==len(ids)==len(set(ids))
            and len(manifest['split']['ids'])==len(ids)
            and set(manifest['split']['ids'])==set(ids)
            and list(source.sample_ids)==runtime
            and [r['sample_id'] for r in source.bundle.outputs_rows]==runtime,
            'completed sealed member identity/source/production order differs')


def describe_business(score, execution, roster, ids):
    rows=score['per_sample'];counts={r['sample_id']:r for r in rows}
    require(len(rows)==len(counts)==len(ids) and set(counts)==set(execution)==set(roster)==set(ids),
            'complete official/business/stratum join differs')
    require(all(all(k in r for k in SLURP_NATIVE_FIELDS) for r in rows)
            and all(type(r['scenario_action_exact']) in (int,float)
                    and r['scenario_action_exact'] in (0,1) for r in rows),
            'native official sufficient counts missing or invalid')
    require(all(roster[sid]['sample_id']==sid and isinstance(roster[sid]['utterance_id'],str)
                and roster[sid]['utterance_id'] and isinstance(roster[sid]['stratum'],str)
                and roster[sid]['stratum'] for sid in ids), 'stratum/utterance identity missing')
    def metrics(selected):
        return {'n':len(selected),'slu_f1':pooled_f1(counts,selected,FIELDS),
                'intent':math.fsum(counts[s]['scenario_action_exact'] for s in selected)/len(selected),
                'reliable_completion':sum(execution[s]['reliable_completion'] for s in selected)/len(selected)}
    natural=metrics(ids);aggregate=score['aggregate']
    require(aggregate['identity_check']['passed'] is True
            and math.isclose(natural['slu_f1'],aggregate['official']['slu_f1'],abs_tol=1e-6,rel_tol=0)
            and math.isclose(natural['intent'],aggregate['port_micro']['intent_accuracy'],abs_tol=1e-6,rel_tol=0),
            'pooled native counts differ from saved official aggregate')
    strata=[{'stratum':name,**metrics([s for s in ids if roster[s]['stratum']==name])}
            for name in sorted({roster[s]['stratum'] for s in ids})]
    return {'natural_mixture':natural,'strata':strata,
            'equal_stratum':{k:math.fsum(x[k] for x in strata)/len(strata)
                            for k in ('slu_f1','intent','reliable_completion')},
            'contacts':{k:sum(execution[s][k] for s in ids) for k in ('model_calls','tool_calls')},
            'tokens':{k:{'total':None if any(execution[s][k] is None for s in ids) else sum(execution[s][k] for s in ids),
                        'unknown_rows':sum(execution[s][k] is None for s in ids)} for k in ('prompt_tokens','completion_tokens')}}


def aggregate_only(process, timing, nodes):
    process={k:v for k,v in process.items() if k in {'schema','sample_count','metrics','transitions',
        'conditioning_unavailable','conditioning_not_applicable','by_scenario','claims_causal_node_credit',
        'claims_semantically_correct_criticism','statistical_scope','review_applicability','role_counts',
        'delivery_stages','recall_status','intent_support'}}
    process['delivery_stages']={k:v for k,v in process['delivery_stages'].items() if k!='rows'}
    if 'intent_support' in process:
        process['intent_support']={k:v for k,v in process['intent_support'].items() if k not in {'rows','samples','custody'}}
    process['authorization']='Exact completed-member root READ; no complete-family authority or export.'
    clock={k:v for k,v in timing.items() if k not in {'samples','content_sha256','source','timing_trace_records'}}
    clock['source_content_sha256']=timing['content_sha256']
    clock['first_admitted_sample']={k:v for k,v in clock['first_admitted_sample'].items() if k!='sample_id'}
    clock['by_role']=nodes['by_role']
    return process,clock


def source_support_configuration(recipe,registration,source,label,ontology,data_root):
    binding=recipe.get('intent_support_binding')
    if binding is None:return None
    receipt=json.loads(_read_pin(binding,data_root))
    support,proofs=receipt['intent_support'],receipt['proof']
    require(receipt.get('schema')=='saea-root-intent-support-configuration-binding-v1'
            and type(receipt.get('model_contacts_added')) is int and receipt['model_contacts_added']==0
            and receipt.get('task_outcomes_used') is False
            and set(support)==set(proofs)==set(registration['expected_members'])
            and all(proofs[k]['config_hash']==registration['member_bindings'][k]['config_hash'] for k in proofs),
            'prospective complete source-only intent support binding differs')
    configuration=support[label];proof=proofs[label]
    require(set(configuration)=={'max_candidates','projection_policy','specification'},'exact support mapping required')
    spec=validate_initial_intent_support_spec(configuration['specification'])
    stores=source.composed.values['knowledge_stores'];store=stores[spec['store_id']];supply=proof['candidate_supply']
    require(proof['config_hash']==source.composed.config_hash
            and proof['store_role']==store['store_role']=='intent-boundaries'
            and proof['snapshot']==store['snapshot'] and proof['release']==store['release']
            and type(configuration['max_candidates']) is int
            and configuration['max_candidates']==supply['max_candidates']>0
            and configuration['projection_policy']==supply['projection_policy']
            and any(supply==declared for entry in stores.values() for declared in entry.get('candidate_supply',{}).values()),
            'support mapping differs from actual frozen stores/supply')
    return {**configuration,'legal_candidate_ids':frozenset(ontology.intents)}


def run(*,recipe_pin,repo_root,data_root,operational_pin,output):
    repo_root,data_root,output=map(lambda p:Path(p).resolve(),(repo_root,data_root,output))
    require(output.is_relative_to(data_root/'analysis') and output!=data_root/'analysis'
            and not output.exists(),'fresh root-only descriptive analysis destination required')
    recipe=json.loads(_read_pin(recipe_pin,repo_root))
    spec={'family_id':recipe['family_id'],'expected_members':recipe['expected_members'],'read_registration':recipe_pin}
    authority=reader.CLI.require_read_registration(spec,repo_root=repo_root)
    family_recipe,registration,owner,supplement=reader.load_documents(recipe['family_recipe'],recipe['family_supplement'],repo_root)
    scope=architecture.validate_source_registration(family_recipe,registration,owner,repo_root=repo_root,data_root=data_root)
    prospective=json.loads(_read_pin(recipe['member_read_scope'],data_root))
    label=validate_member_recipe(recipe,family_recipe,registration,scope,prospective,authority)
    require(recipe['implementation']==implementation_pins(),'prospectively pinned executing member implementation differs')
    for record in recipe['implementation'].values():_read_pin(record,repo_root)
    original=absolute(operational_pin)
    require(set(original)=={'read_authority','recipe','member_id','runtime_gold','learner_export',
            'manifest','phase','job_metadata','original_score','reference_binding'},
            'exact operational custody fields required; no answer payloads')
    require(original.get('read_authority')==authority and original.get('recipe')==recipe_pin
            and original.get('member_id')==label and original.get('runtime_gold') is False
            and original.get('learner_export') is False,'exact member operational authority differs')
    member=registration['member_bindings'][label]
    require(member['source_commit']==scope['source_commit'],'selected member source differs')
    roster_path=repo_root/recipe['analysis_roster']['relpath']
    roster_doc=json.loads(_read_pin(recipe['analysis_roster'],repo_root))
    require([r['sample_id'] for r in roster_doc['items']]==recipe['sample_ids'],'exact ordered construction roster differs')
    binding,job_pins=reader.member_source_binding(label,member,pin(roster_path),data_root)
    require(original['manifest']==binding['config']['manifest'] and original['job_metadata']==job_pins,
            'original manifest or unique score job metadata differs')
    source=verify_native_episode_source(manifest_path=Path(original['manifest']['path']),
        expected_manifest_sha256=original['manifest']['sha256'],phase_artifact_path=Path(original['phase']['path']),
        expected_phase_sha256=original['phase']['sha256'],repo_root=Path(recipe['frozen_worker_root']),data_root=data_root)
    validate_manifest(source.bundle.manifest,source,member,recipe['sample_ids'],recipe['runtime_sample_ids'])
    custody=[pin(source.bundle.manifest['attempt']['state_path'])]+[source.bundle.manifest[k]
             for k in ('outputs','raw_trace','trace_manifest','scores') if source.bundle.manifest.get(k) is not None]
    require(pin(source.bundle.manifest['scores']['path'])==original['original_score'], 'original attached score differs')
    # Repackage the attached complete scores with the unchanged standard receipt API; no scorer runs.
    saved=write_complete_saved_score_receipt(output/'custody/saved-score',job_id=member['attempt_id'],verified_bundle=source.bundle)
    receipt=verify_complete_score_receipt(saved,source.bundle)
    payload=absolute(receipt['score_result'])
    require(payload['scores']==absolute(original['original_score']),'saved envelope differs from original official scores')
    projection=RewardProjection.from_json(supplement['projection'])
    require(projection.scorer=='slurp-slu-official-train' and set(projection.per_sample_fields)==set(SLURP_NATIVE_FIELDS),
            'exact native complete official score selector required')
    score=payload['scores'][projection.scorer];by_id={r['sample_id']:r for r in score['per_sample']}
    require(len(score['per_sample'])==len(by_id)==len(source.sample_ids) and set(by_id)==set(source.sample_ids),
            'official member rows partial or duplicate')
    require(recipe['reference_binding']==original['reference_binding'],'prospective reference binding differs')
    reference=recipe['reference_binding']
    require(Path(reference['data_root']).resolve()==data_root and pin(reference['lock']['path'])==reference['lock'],
            'original reference inventory root or raw lock differs before reference read')
    lock=load_lock(Path(reference['lock']['path']))
    ontology=load_slurp_ontology(lock,data_root)
    records=load_verified_slurp_reference_records(reference,source.sample_ids,loader=load_slurp_split)
    support=source_support_configuration(recipe,registration,source,label,ontology,data_root)
    clock=export_system_sample_timing(source);nodes=export_system_node_timing(source)
    require(clock.get('available') is True and [r['sample_id'] for r in clock['samples']]==list(source.sample_ids)
            and clock['first_admitted_sample']==clock['samples'][0]
            and all(clock[k]==recipe['measurement_profile'][k] for k in ('slot_count','queue_depth')),
            'original complete timing/order/profile differs')
    execution=_row_cost_and_terminal(source.bundle.manifest,include_sample_timing=True)
    metadata=json.loads(_read_pin(supplement['stratum_metadata'],repo_root))['items']
    require(len(metadata)==len({r['sample_id'] for r in metadata}),'duplicate stratum metadata')
    roster={r['sample_id']:r for r in metadata if r['sample_id'] in set(recipe['sample_ids'])}
    require(all(roster[r['sample_id']]['utterance_id']==r['utterance_id'] for r in roster_doc['items']),
            'official construction/stratum utterance join differs')
    business=describe_business(score,execution,roster,recipe['sample_ids'])
    process=build_slurp_process_metrics(source,reference_records=records,
        official_final_rows=tuple(by_id[s] for s in source.sample_ids),reference_binding_sha256=content_hash(reference),
        official_score_result_sha256=receipt['score_result']['sha256'],legal_slot_types=tuple(sorted(ontology.entity_types)),
        review_applicability=scope['review_applicability'][label],intent_support_configuration=support)
    # Support remains explicitly unknown without a prospectively source-bound projection.
    process,clock=aggregate_only(process,clock,nodes)
    require(reader.CLI.require_read_registration(spec,repo_root=repo_root)==authority,'member READ changed during joins')
    require(json.loads(_read_pin(recipe_pin,repo_root))==recipe and absolute(operational_pin)==original
            and json.loads(_read_pin(recipe['member_read_scope'],data_root))==prospective
            and recipe['implementation']==implementation_pins(),'prospective member bindings changed before persistence')
    again=reader.load_documents(recipe['family_recipe'],recipe['family_supplement'],repo_root)
    require(architecture.validate_source_registration(*again[:3],repo_root=repo_root,data_root=data_root)==scope,
            'complete source registration changed during member analysis')
    binding2,jobs2=reader.member_source_binding(label,member,pin(roster_path),data_root)
    require(binding2==binding and jobs2==job_pins,'original unique score metadata changed')
    for record in [original['manifest'],original['phase'],original['original_score'],reference['lock'],*job_pins,*custody]:
        require(pin(record['path'])==record,'original source changed before descriptive persistence')
    verify_complete_score_receipt(saved,source.bundle)
    require(require_clean_study_repo(Path(recipe['frozen_worker_root']))==scope['source_commit'],
            'original frozen source changed before persistence')
    source_support_configuration(recipe,registration,source,label,ontology,data_root)
    report={'schema':'saea-manual-member-descriptive-read-v1','status':'COMPLETE_MEMBER_DESCRIPTIVE_ONLY',
            'member_id':label,'read_authority':authority,'complete_family_registration':recipe['family_recipe'],
            'business':business,'process':process,'timing':clock,'comparisons':None,
            'learner_export':False,'runtime_gold':False,'contacts_added':{'model':0,'scorer':0,'tokenizer':0},
            'interpretation':'One completed member only. No contrasts, policy update, benefit, learning or complete-family verdict.'}
    provenance={'recipe':recipe_pin,'operational':operational_pin,'originals':original,
                'saved_score_receipt':{'cell_id':saved.cell_id,**pin(saved.path)},'implementation':recipe['implementation'],
                'timing_source':source.manifest_sha256 if hasattr(source,'manifest_sha256') else original['manifest']['sha256'],
                'runtime_sample_ids':list(source.sample_ids),'pending_policies_modified':False,'ledger_modified':False}
    reader.CLI.write_new(output/'report.json',report);reader.CLI.write_new(output/'custody/provenance.json',provenance)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--implementation-pins',action='store_true')
    for key in ('repo-root','data-root','recipe','recipe-sha256','operational','operational-sha256','output'):
        parser.add_argument('--'+key)
    args=parser.parse_args()
    if args.implementation_pins:print(json.dumps(implementation_pins(),sort_keys=True,indent=2));return
    require(all(getattr(args,k.replace('-','_')) for k in ('repo-root','data-root','recipe','recipe-sha256','operational','operational-sha256','output')),'complete explicit root inputs required')
    with no_contacts():run(recipe_pin={'relpath':args.recipe,'sha256':args.recipe_sha256},repo_root=args.repo_root,
        data_root=args.data_root,operational_pin={'path':args.operational,'sha256':args.operational_sha256},output=args.output)

if __name__=='__main__':main()
