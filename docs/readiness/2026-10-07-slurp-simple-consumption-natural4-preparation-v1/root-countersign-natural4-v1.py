"""Root-only document authoring against an already decided raw pin; never launch or touch controls."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2); stream.write('\n')


def prepare_outputs(repo, data, package, decision_pin):
    decision_path=(data/decision_pin['relpath']).resolve()
    assert decision_path.is_relative_to(data.resolve()) and sha(decision_path)==decision_pin['sha256']
    decision=read(decision_path)
    assert decision['schema']=='saea-campaign-decision-v1' and decision['status']=='decided'
    template=read(package/'root-admission-prospective-v1.json')
    for key in ('decision_id','eligible_run_ids','capacity_prerequisite','resource_policy'):
        assert decision[key]==template[key], key
    assert decision['next_panel_authorized'] is False and decision['learning']=='HELD'
    from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.rails.architecture_natural_registration import require_architecture_natural_registration
    members=read(package/'natural4-prospective-members-v1.json')
    exposure=read(package/'exposure-preregistration-prospective-v1.json')
    rows=[];outputs=[];all_ids=[]
    for member in members:
        cell,=load_campaign_cells(repo,member['experiment']);c=cell.document
        config=compose(repo,c['model_fragment'],c['dataset_fragment'],c['baseline_fragment'],member['experiment'])
        assert config.config_hash==member['config_hash'] and c['readiness']['state']=='ready'
        documents=[]
        for role in ('generation','fit'):
            path=package/(member['label']+'-'+role+'-plan-prospective-v1.json')
            document=read(path)
            assert document['status'].startswith('PROSPECTIVE UNSIGNED')
            assert document['composed_config_hash']==config.config_hash
            assert document['capacity_prerequisite']==decision['capacity_prerequisite']
            document.update(status='ROOT COUNTERSIGNED BEFORE CONTACT under owner227',at_utc=datetime.now(timezone.utc).isoformat(),decision_receipt=decision_pin)
            target=package/(member['label']+'-'+role+'-plan-registered-v1.json')
            assert not target.exists(), 'Existing registration is immutable'
            documents.append(document);outputs.append((target,document))
            plan=document['execution_plan'];all_ids.append(plan['run_id'])
            expected,=[row for row in exposure if row['label']==member['label'] and row['role']==role]
            assert expected['execution_plan']==plan and expected['composed_config_hash']==config.config_hash
            notes=('ROOT COUNTERSIGNED BEFORE CONTACT under owner227; decision '+decision_pin['relpath']+' SHA256 '+decision_pin['sha256']+'. Protocol '+plan['protocol_hash']+'; composed config '+config.config_hash+'. Exact natural-four-row structural proof; C4capacity qualification '+decision['capacity_prerequisite']['qualification']['sha256']+'. No official scoring, quality feedback or learner export; no automatic retry.')
            rows.append(['2026-10-07',plan['run_id'],plan['execution_profile'],'Natural four-row '+role+' structural proof','Frozen core' if role=='generation' else 'Existing guarded tokenizer','slurp same immutable UPDATE2 registered four-row subset',plan['split_role'],plan['split_identity_hash'],'no',str(plan['planned_model_calls']),str(plan['planned_speech_audio_seconds']),str(plan['planned_gpu_hours']),'Retained TRAIN optimization lineage; structural-only no quality read',target.relative_to(repo).as_posix(),notes])
        require_architecture_natural_registration(config.values,c,documents,repo_root=repo,data_root=data)
        recipe_path=package/(member['label']+'-analysis-recipe-v1.json')
        recipe=read(recipe_path)
        assert recipe['schema']=='saea-system-text-engineering-analysis-v1' and recipe['status'].startswith('DRAFT UNSIGNED READ')
        assert recipe['run_ids']['generation']==member['execution_plan']['run_id'] and recipe['run_ids']['fit']==member['native_contact_fit']['run_id']
        assert recipe['official_score_jobs']==0 and recipe['scientific_feedback'] is False and recipe['learner_export'] is False
        read_id=recipe['run_ids']['read']
        rows.append(['2026-10-07',read_id,'model-free-check','Natural four-row structural read after complete proof','Saved operational receipts','slurp same immutable UPDATE2 registered four-row subset','discovery',member['execution_plan']['split_identity_hash'],'no','0','0','0','No quality feedback or learner export',recipe_path.relative_to(repo).as_posix(),'DRAFT UNSIGNED READ; exact complete proof and root structural READ countersignature remain required. Decision '+decision_pin['relpath']+' SHA256 '+decision_pin['sha256']+'. No official scoring or scientific feedback.'])
    assert all_ids==decision['eligible_run_ids']
    ledger=repo/'docs/exposure-ledger.md';text=ledger.read_text(encoding='utf-8')
    assert not any('| '+row[1]+' |' in text for row in rows),'Exposure already registered'
    header='| Date | Run/experiment ID | Execution profile | Scope | Model/tool | Speech carrier + split | Split role | Split identity hash | Consumed | Calls | Speech audio seconds | GPU hours | Inherited exposure | Artifacts | Notes |'
    addition='\n\n## Natural four-row configured architecture structural proof, 2026-10-07\n\n'+header+'\n| '+' | '.join(['---']*15)+' |\n'+'\n'.join('| '+' | '.join(row)+' |' for row in rows)+'\n'
    return outputs,ledger,text+addition


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,required=True)
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--decision-relpath',required=True)
    parser.add_argument('--decision-sha256',required=True)
    parser.add_argument('--root-countersign',action='store_true',required=True)
    args=parser.parse_args()
    repo=args.repo_root.resolve();data=args.data_root.resolve()
    import sys
    sys.path.insert(0,str(repo/'src'))
    package=repo/'docs/readiness/2026-10-07-slurp-simple-consumption-natural4-preparation-v1'
    outputs,ledger,text=prepare_outputs(repo,data,package,{'relpath':args.decision_relpath,'sha256':args.decision_sha256})
    # Refuse every existing target before the first authoring write. No runtime/control operation follows.
    assert all(not path.exists() for path,_ in outputs)
    for path,document in outputs: save(path,document)
    ledger.write_text(text,encoding='utf-8')
    print(json.dumps({'registered_plans':len(outputs),'generation_contacts':0,'tokenizer_contacts':0,'scorer_contacts':0,'launches':0}))


if __name__=='__main__': main()
