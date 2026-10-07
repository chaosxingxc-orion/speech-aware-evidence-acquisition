"""Finalize prospective natural4 bytes and validate in memory; countersign nothing."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.analysis.native_graph_rehearsal import require_prepared_graph_artifacts
from speech_aware_evidence_acquisition.rails.architecture_natural_registration import require_architecture_natural_registration

import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo-root',type=Path,required=True)
parser.add_argument('--data-root',type=Path,required=True)
parser.add_argument('--lock-path',type=Path,required=True)
parser.add_argument('--expected-source-commit',required=True)
parser.add_argument('--preparation-receipt',type=Path,required=True)
parser.add_argument('--preparation-receipt-sha256',required=True)
args=parser.parse_args()
R=args.repo_root.resolve();D=args.data_root.resolve();LOCK=args.lock_path.resolve()
from speech_aware_evidence_acquisition.core.bundle.git_commit import require_clean_study_repo
assert require_clean_study_repo(R)==args.expected_source_commit
assert args.preparation_receipt.resolve().is_relative_to(D)
assert hashlib.sha256(args.preparation_receipt.read_bytes()).hexdigest()==args.preparation_receipt_sha256
C4=D/'coordination/simple-consumption-prepared-graph-recovery2-v1'
P=R/'docs/readiness/2026-10-07-slurp-simple-consumption-natural4-instrumented-v4'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_bytes())
def save(p,v):
 with p.open('x',encoding='utf-8') as f: json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
def pin(p): return {'relpath':p.relative_to(D).as_posix(),'sha256':sha(p)}
def blocked(*a,**k): raise AssertionError('Prospective natural validation refuses transport contacts')
assert sha(C4/'registration-v1.json')=='975bb7c9fb4525082a3bc191d20736a7493df5328b4302a884fd0ba4712c302a'
assert sha(C4/'capacity-qualified-v1.json')=='47de73ed7217c042321abcc36ed027767fddc4bc8b77181f1b038477b8efff93'
reg=load(C4/'registration-v1.json');qualification=load(C4/'capacity-qualified-v1.json')
assert qualification['runtime_admission'] is False
prerequisite={key:pin(C4/name) for key,name in [('registration','registration-v1.json'),('qualification','capacity-qualified-v1.json')]}
records=[];queue=[];eligible=[];exposure=[]
with patch('socket.socket.connect',blocked),patch('socket.socket.connect_ex',blocked),patch('socket.create_connection',blocked):
 for i,m in enumerate(reg['members'],1):
  label=m['label'];stem='slurp-native-stage3-simple-consumption-'+label+'-engineering-smoke-4-v4'
  ep=R/'configs/experiment'/(stem+'.json');e=load(ep);cell=e['cells'][0]
  assert cell['readiness']['state']=='held'
  cell['readiness'].update(state='ready',reason='Root227 prospective natural4 preparation after adopted complete C4 capacity qualification; exact countersigned plans, exposure registration and frozen/live gates remain mandatory before contact.')
  ep.write_text(json.dumps(e,sort_keys=True,indent=2)+'\n',encoding='utf-8')
  rt=build_flight_runtime(R,D,model=cell['model_fragment'],dataset=cell['dataset_fragment'],baseline=cell['baseline_fragment'],experiment=stem,run_id=cell['run_id'],attempt_id=cell['attempt_id'],runtime_root=Path('/home/chao'),lock_path=LOCK,campaign_active=False)
  require_prepared_graph_artifacts(rt);ctx=rt.preparation_context();plan=ctx['execution_plan'];fit=ctx['values']['native_contact_fit']
  assert list(ctx['sample_ids'])==m['runtime_graph_sample_ids']
  plans=[]
  for role in ('generation','fit'):
   bound=plan if role=='generation' else replace(plan,run_id=fit['run_id'],attempt_id=fit['attempt_id'],planned_model_calls=fit['contact_cap'])
   document=load(P/(label+'-'+role+'-plan-draft-v1.json'))
   document.update(status='PROSPECTIVE UNSIGNED; root must countersign before contact',composed_config_hash=rt._composed.config_hash,execution_plan=asdict(bound),capacity_prerequisite=prerequisite)
   save(P/(label+'-'+role+'-plan-prospective-v1.json'),document);plans.append(document);eligible.append(bound.run_id)
   exposure.append({'label':label,'role':role,'plan_relpath':(P/(label+'-'+role+'-plan-registered-v1.json')).relative_to(R).as_posix(),'execution_plan':asdict(bound),'composed_config_hash':rt._composed.config_hash})
  in_memory=[{**p,'status':'ROOT COUNTERSIGNED BEFORE CONTACT; in-memory validator test only, not persisted authorization'} for p in plans]
  validated=require_architecture_natural_registration(ctx['values'],cell,in_memory,repo_root=R,data_root=D)
  records.append({'label':label,'experiment':stem,'config_hash':rt._composed.config_hash,'execution_plan':asdict(plan),'native_contact_fit':fit,'runtime_sample_ids':list(ctx['sample_ids']),'configured_sample_ids':e['populations'][0]['ids'],'prepared_phase_supply':ctx['values']['prepared_phase_supply'],'strict_prepared_artifacts':list(rt.verify_prepared_artifacts()),'existing_natural_api_validation':validated,'status':'PROSPECTIVE UNSIGNED','generation_contacts':0,'tokenizer_contacts':0,'scorer_contacts':0})
  queue.append({'order':i,'short':'simple-natural4-'+label+'-v4','kind':'engineering','experiment':stem,'cell':stem,'smoke_experiment':stem,'smoke_cell':stem,'campaign_plan':None,'run_id':plan.run_id,'fit_run_id':fit['run_id'],'gen_attempt_id':plan.attempt_id,'smoke_run_id':plan.run_id,'smoke_attempt_id':plan.attempt_id,'expected_rows':4,'contacts_per_row':m['model_per_trajectory'],'ceiling_per_row':m['model_per_trajectory'],'notool':False,'smoke_notool':False,'owner':'root-'+stem,'process_memory_diagnostics':True,'process_start_gib':4,'process_floor_gib':4,'process_start_wait_seconds':600,'process_start_stable_samples':3,'result_kind':'task-answer','smoke_result_kind':'task-answer'})
  print(label+': final prospective hashes, actual capacity prerequisite and existing natural validator pass; no countersign/contact',flush=True)
save(P/'natural4-prospective-members-v1.json',records)
save(P/'natural4-engineering-queue-v1.json',queue)
save(P/'exposure-preregistration-prospective-v1.json',exposure)
save(P/'root-admission-prospective-v1.json',{'schema':'saea-campaign-decision-v1','status':'DRAFT UNSIGNED','decision_id':'simple-consumption-natural4-instrumented-v4','owner_decisions':[227],'eligible_run_ids':eligible,'capacity_prerequisite':prerequisite,'scope':'Exactly four configured members times four natural structural trajectories; maximum124 generation contacts and496 actual FIT endpoints; no official scoring, quality read or scientific feedback.','failure_disposition':'Stop, preserve and obtain named root disposition; no automatic retry.','precontact_conditions':['Exact countersigned generation/FIT pairs and exposure ledger','Clean single frozen worker; strict supply/source/registration validation','Fresh resident-service identity and idle guard; no STOP or competing worker','Windows startup/running floors4GiB, stable600second/3sample startup wait'],'structural_read_scope':'Operational request/FIT/control/custody form only; no scientific scores or learner export. Natural absence of solver lookup is permitted; synthetic coverage stays separate.','next_panel_authorized':False,'learning':'HELD','resource_policy':{'start_gib':4,'floor_gib':4,'wait_seconds':600,'stable_samples':3},'role_division':{'engineering':'GPT-6.1 Sol','planning_optimization_independent_review_template_analysis':'GPT-6 Astra/Ultra','admission_launch':'root'}})
save(P/'natural4-prospective-validation-v1.json',{'status':'PASS PROSPECTIVE ONLY','at_utc':datetime.now(timezone.utc).isoformat(),'capacity_prerequisite':prerequisite,'members':records,'in_memory_root_status_for_validator_only':True,'persisted_root_countersignature':False,'runtime_admission':False,'generation_contacts':0,'tokenizer_contacts':0,'scorer_contacts':0})
