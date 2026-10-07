"""Prepare held natural four-row successors through the existing model-free repin seam."""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.core.flight.repin import compute_cell_identity, ensure_artifact_pinned
from speech_aware_evidence_acquisition.analysis.native_graph_rehearsal import require_prepared_graph_artifacts
from speech_aware_evidence_acquisition.rails.experiment_population import load_population_config
from speech_aware_evidence_acquisition.rails.system_text_policy import verify_system_text_binding

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


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_bytes())
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2); stream.write('\n')


def blocked(*args, **kwargs): raise AssertionError('Natural preparation refuses network/model/scorer contacts')


def runtime(cell, stem):
    return build_flight_runtime(R, D, model=cell['model_fragment'], dataset=cell['dataset_fragment'],
        baseline=cell['baseline_fragment'], experiment=stem, run_id=cell['run_id'], attempt_id=cell['attempt_id'],
        runtime_root=Path('/home/chao'), lock_path=LOCK, campaign_active=False)


def prepare_supply(**kwargs):
    cell, = load_campaign_cells(R, kwargs['experiment'])
    return runtime(cell.document, kwargs['experiment']).prepare_phase_supply(kwargs['output_path'], max_workers=4)


reg = read(C4 / 'registration-v1.json')
assert sha(C4 / 'registration-v1.json') == '975bb7c9fb4525082a3bc191d20736a7493df5328b4302a884fd0ba4712c302a'
assert sha(C4 / 'capacity-qualified-v1.json') == '47de73ed7217c042321abcc36ed027767fddc4bc8b77181f1b038477b8efff93'
pop = load_population_config(reg['experiment_population'], repo_root=R, allow_architecture=True)
assert [m['label'] for m in reg['members']] == [m['member_id'] for m in pop['architecture']['members']]
assert P.is_dir()
assert not (P / "prepared-natural4-drafts-v1.json").exists()
reports = []
with patch('socket.socket.connect', blocked), patch('socket.socket.connect_ex', blocked), patch('socket.create_connection', blocked):
    for identity, capacity_member in zip(pop['architecture']['members'], reg['members'], strict=True):
        label = identity['member_id']
        old_stem = 'slurp-native-stage3-simple-consumption-' + label + '-engineering-smoke-4-v3'
        stem = old_stem[:-3] + '-v4'
        old_exp = R / 'configs/experiment' / (old_stem + '.json')
        old_baseline = R / 'configs/baseline' / (old_stem + '.json')
        e, baseline = read(old_exp), read(old_baseline)
        original_baseline = deepcopy(baseline)
        old_pin = deepcopy(baseline['prepared_phase_supply'])
        old_artifact = D / old_pin['relpath']; assert sha(old_artifact) == old_pin['sha256']
        old_output = read(old_artifact)['output']
        cell = e['cells'][0]
        run = cell['run_id'][:-3] + '-V4'
        attempt = cell['attempt_id'][:-3] + '-v4'
        e['experiment_id'] = run
        cell.update(cell_id=stem, baseline_fragment=stem, run_id=run, attempt_id=attempt)
        cell['readiness'] = {'state': 'held', 'reason': 'PREPARATION ONLY; final merged source, strict output-equal envelope repin, root incident disposition and countersignature, frozen and live gates required.', 'requirements': []}
        e['stage3_measurement']['note']='Same immutable UPDATE2 registered four-row subset; structural form proof only. No task-quality or learning feedback.'
        for key in ('run_id', 'attempt_id'):
            baseline['native_contact_fit'][key] = baseline['native_contact_fit'][key][:-3] + ('-V4' if key == 'run_id' else '-v4')
        assert e['populations'][0]['ids'] == capacity_member['graph_sample_ids']
        assert e['population']['count'] == 4 and e['stage3_measurement']['claims_benefit'] is False
        assert e['family_budget']['generation_calls_cap'] == 4 * identity['model_per_trajectory']
        assert e['family_budget']['actual_request_fit_endpoint_cap'] == 4 * e['family_budget']['generation_calls_cap']
        for path in (D / 'runs' / run, D / 'attempts' / run, D / 'runs' / baseline['native_contact_fit']['run_id'], D / 'attempts' / baseline['native_contact_fit']['run_id']):
            assert not path.exists(), str(path)
        ep, bp = R / 'configs/experiment' / (stem + '.json'), R / 'configs/baseline' / (stem + '.json')
        assert read(ep) == e and read(bp) == baseline, "Draft identities changed before final-source preparation"
        cell_object, = load_campaign_cells(R, stem)
        repin = ensure_artifact_pinned(repo_root=R, data_root=D, runtime_root=Path('/home/chao'), lock_path=LOCK,
            experiment=stem, identity=compute_cell_identity(R, stem, cell_object), prepare_supply_fn=prepare_supply, allow_output_change=False)
        baseline = read(bp); new_pin = baseline['prepared_phase_supply']; assert sha(D / new_pin['relpath']) == new_pin['sha256']
        assert read(D / new_pin['relpath'])['output'] == old_output
        comparable = deepcopy(baseline)
        comparable['prepared_phase_supply'] = old_pin
        comparable['native_contact_fit'] = original_baseline['native_contact_fit']
        assert comparable == original_baseline
        rt = runtime(cell, stem); require_prepared_graph_artifacts(rt)
        ctx = rt.preparation_context()
        assert list(ctx['sample_ids']) == capacity_member['runtime_graph_sample_ids']
        verify_system_text_binding(ctx['values'], cell['system_text_policy_binding'], repo_root=R, data_root=D)
        plan = ctx['execution_plan']
        prerequisite = {'registration': {'relpath': (C4 / 'registration-v1.json').relative_to(D).as_posix(), 'sha256': sha(C4 / 'registration-v1.json')},
                        'qualification': {'relpath': (C4 / 'capacity-qualified-v1.json').relative_to(D).as_posix(), 'sha256': sha(C4 / 'capacity-qualified-v1.json')}}
        for role in ('generation', 'fit'):
            fit = ctx['values']['native_contact_fit']
            bound = plan if role == 'generation' else replace(plan, run_id=fit['run_id'], attempt_id=fit['attempt_id'], planned_model_calls=fit['contact_cap'])
            draft = {'schema': 'saea-registered-' + role + '-plan-v1', 'plan_role': role,
                'architecture_proof': 'natural-four-row-v1', 'status': 'DRAFT HELD; complete capacity qualification and root countersignature required before contact',
                'experiment': stem, 'cell': stem, 'experiment_population': reg['experiment_population'],
                'population_cohort': identity['cohort_id'], 'architecture_member': label,
                'sample_ids': e['populations'][0]['ids'], 'composed_config_hash': rt._composed.config_hash,
                'execution_plan': asdict(bound), 'policy_binding': cell['system_text_policy_binding'],
                'prepared_phase_supply': new_pin, 'official_score_jobs': 0, 'scientific_feedback': False,
                'learner_export': False, 'capacity_prerequisite': prerequisite}
            save(P / (label + '-' + role + '-plan-draft-v1.json'), draft)
        report = {'label': label, 'experiment': stem, 'original_experiment': old_stem,
                  'old_prepared_pin': old_pin, 'new_prepared_pin': new_pin, 'output_equal': True,
                  'non_envelope_policy_equal': True, 'configured_sample_ids': e['populations'][0]['ids'],
                  'runtime_sample_ids': list(ctx['sample_ids']), 'capacity_graph': capacity_member['graph'],
                  'capacity_graph_config_hash': capacity_member['graph_config_hash'], 'config_hash': rt._composed.config_hash,
                  'generation_cap': plan.planned_model_calls, 'fit_cap': ctx['values']['native_contact_fit']['contact_cap'],
                  'repin': repin, 'strict_prepared_artifacts': list(rt.verify_prepared_artifacts()),
                  'generation_contacts': 0, 'tokenizer_contacts': 0, 'scorer_contacts': 0, 'status': 'HELD'}
        save(P / (label + '-prepared-natural4-v1.json'), report); reports.append(report)
        print(label + ': held successor prepared, exact output equal, strict artifacts valid, contacts0', flush=True)
save(P / 'prepared-natural4-drafts-v1.json', {'status': 'HELD', 'at_utc': datetime.now(timezone.utc).isoformat(),
    'preparation_source_commit': args.expected_source_commit, 'members': reports,
    'capacity_qualification_pending': False, 'runtime_admission': False,
    'generation_contacts': 0, 'tokenizer_contacts': 0, 'scorer_contacts': 0})
