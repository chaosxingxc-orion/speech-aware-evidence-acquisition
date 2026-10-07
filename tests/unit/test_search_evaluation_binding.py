"""New search labels require exact original slots and recorded child identities."""
from copy import deepcopy
import pytest
from test_system_context_learning import setup, pin, repin
from test_experiment_population_config import config
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.experiment_population import population_accounting
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def fixture(tmp_path, monkeypatch, algorithm='fixed-parent-aggregate-v1'):
    f = setup(tmp_path, monkeypatch)
    c = config((len(f.protocol['candidate_members']),), 20)
    cohort = c['cohorts'][0]
    cohort['candidate_ids'] = f.protocol['candidate_members']
    p = pin(tmp_path, 'population.json', c)
    for doc in (f.protocol, f.registration, f.recipe):
        doc.update(experiment_population=p, population_cohort=cohort['cohort_id'],
                   population_budget=population_accounting(c, cohort['cohort_id']))
    f.protocol['algorithms'] = [algorithm]
    slots = [{'candidate_id': cid, 'cohort_id': cohort['cohort_id'],
              'mode': 'fixed' if algorithm == 'fixed-parent-aggregate-v1' else 'local',
              'parent_bundle_ids': [content_hash('parent-' + cid)]}
             for cid in cohort['candidate_ids']]
    reservation = {'schema': 'saea-search-update-reservation-v1',
        'registration': {'relpath': 'private-registration.json', 'sha256': 'a'*64},
        'registration_sha256': 'b'*64, 'experiment_population': p,
        'qualified_input_sha256': 'c'*64, 'actor_input_sha256': 'd'*64,
        'algorithm': algorithm, 'iteration': 1, 'slots': slots,
        'proposal_slots': len(slots), 'proposer': c['proposer'],
        'population_budget': population_accounting(c), 'runtime_admission': False}
    result = {'schema': 'saea-search-update-result-v1',
        'registration': reservation['registration'], 'response_sha256': 'e'*64,
        'status': 'recorded', 'usage': None, 'runtime_admission': False,
        'experiment_population': p, 'algorithm': algorithm, 'iteration': 1,
        'population_budget': population_accounting(c), 'records': [
            {'candidate_id': s['candidate_id'], 'proposal_sha256': content_hash(s),
             'status': 'materialized-policy', 'parent_bundle_ids': s['parent_bundle_ids'],
             'bundle_id': f.registration['member_bindings'][s['candidate_id']]['bundle_id']}
            for s in slots]}
    f.reservation, f.result = reservation, result
    refresh(f)
    return f


def refresh(f):
    refs = {'reservation': pin(f.root, 'reserved.json', f.reservation),
            'result': pin(f.root, 'recorded.json', f.result)}
    for doc in (f.recipe, f.registration, f.protocol):
        doc['search_evaluation'] = deepcopy(refs)
    repin(f)


@pytest.mark.parametrize('algorithm', ['fixed-parent-aggregate-v1', 'bounded-multiparent-aggregate-v1'])
def test_search_scope_reuses_complete_family_and_reference_gates(tmp_path, monkeypatch, algorithm):
    f = fixture(tmp_path, monkeypatch, algorithm)
    f.result['records'][0]['status'] = 'no-change'
    refresh(f)
    evidence, *_ = learning._qualified_feedback(f.bindings, recipe_pin=f.recipe_pin, repo_root=f.root)
    assert evidence['read_authority']['read_run_id'] == f.registration['read_id']
    assert f.events.index('complete-family') < f.events.index('reference')


@pytest.mark.parametrize('fault', ['missing-pin', 'recipe-pin', 'changed-bytes', 'wrong-algorithm',
    'mixed-algorithms', 'old-label', 'iteration', 'population', 'budget', 'proposer',
    'slot-count', 'slot-order', 'slot-mode', 'slot-parent', 'result-parent', 'response-hash',
    'missing-result', 'invalid-slot', 'invalid-envelope', 'reordered-results', 'child-substitution',
    'registration-substitution', 'runtime-activation', 'partial-family', 'roster', 'read-authority'])
def test_search_refuses_drift_before_result_access(tmp_path, monkeypatch, fault):
    f = fixture(tmp_path, monkeypatch)
    r, q = f.reservation, f.result
    if fault == 'wrong-algorithm': q['algorithm'] = 'bounded-multiparent-aggregate-v1'
    elif fault == 'mixed-algorithms': f.protocol['algorithms'].append('gepa')
    elif fault == 'old-label': f.protocol['algorithms'] = ['gepa']
    elif fault == 'iteration': q['iteration'] = 2
    elif fault == 'population': q['experiment_population'] = {'relpath':'other', 'sha256':'f'*64}
    elif fault == 'budget': q['population_budget']['family_trajectories'] += 1
    elif fault == 'proposer': r['proposer']['model'] = 'another'
    elif fault == 'slot-count': r['proposal_slots'] += 1
    elif fault == 'slot-order': r['slots'].reverse()
    elif fault == 'slot-mode': r['slots'][0]['mode'] = 'explore'
    elif fault == 'slot-parent': r['slots'][0]['parent_bundle_ids'] = []
    elif fault == 'result-parent': q['records'][0]['parent_bundle_ids'] = ['f'*64]
    elif fault == 'response-hash': q['response_sha256'] = 'invalid'
    elif fault == 'missing-result': q['records'].pop()
    elif fault == 'invalid-slot': q['records'][0]['status'] = 'invalid'
    elif fault == 'invalid-envelope': q['status'] = 'invalid-envelope'
    elif fault == 'reordered-results': q['records'].reverse()
    elif fault == 'child-substitution': q['records'][0]['bundle_id'] = 'f'*64
    elif fault == 'registration-substitution': q['registration'] = {'relpath':'other','sha256':'f'*64}
    elif fault == 'runtime-activation': q['runtime_admission'] = True
    elif fault == 'partial-family': f.bindings.pop()
    elif fault == 'roster': f.recipe['sample_ids'].reverse()
    refresh(f)
    if fault == 'missing-pin':
        for d in (f.protocol, f.recipe, f.registration): d.pop('search_evaluation')
        repin(f)
    elif fault == 'recipe-pin':
        f.recipe['search_evaluation']['result']['sha256'] = 'f'*64
        repin(f)
    elif fault == 'changed-bytes': (f.root / 'recorded.json').write_text('{}')
    elif fault == 'read-authority':
        def refuse(*a, **kw): raise PolicyError('unsigned READ')
        f.cli.require_read_registration = refuse
    with pytest.raises((PolicyError, KeyError)):
        learning._qualified_feedback(f.bindings, recipe_pin=f.recipe_pin, repo_root=f.root)
    assert 'complete-family' not in f.events


def test_old_scope_cannot_gain_search_authority(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    assert learning._validate_scope(f.recipe, f.registration, f.protocol, root=f.root)
    f.protocol['algorithms'] = ['fixed-parent-aggregate-v1']
    repin(f)
    with pytest.raises(PolicyError):
        learning._validate_scope(f.recipe, f.registration, f.protocol, root=f.root)


@pytest.mark.parametrize('fault', [None, 'child', 'sampling', 'fit-cap'])
def test_prelaunch_uses_same_search_gate_and_runtime_bindings(tmp_path, monkeypatch, fault):
    from types import SimpleNamespace
    from test_flight_registration_check import gate
    from speech_aware_evidence_acquisition.core import config as runtime_config
    from speech_aware_evidence_acquisition.rails import system_text_policy
    f = fixture(tmp_path, monkeypatch)
    m = f.registration['member_bindings']['context-0']
    cell = dict(model_fragment='m', dataset_fragment='d', baseline_fragment='b',
        attempt_id=m['attempt_id'], system_text_policy_binding={'bundle_id': m['bundle_id']},
        experiment_population=f.protocol['experiment_population'], population_cohort=f.protocol['population_cohort'])
    effective = {'system_search_measurement': f.recipe['measurement_profile'],
        'serving_slots': 4, 'serving_slot_tokens': 24576, 'native_episode': {},
        'decoding_params': {'max_tokens': 512, **f.protocol['sampling']},
        'server_args': ['-np', '4', '-c', '98304'],
        'experiment_population': cell['experiment_population'], 'population_cohort': cell['population_cohort'],
        'native_contact_fit': {}}
    # Derive the per-member cap from the actual configured family, not a literal K.
    effective['native_contact_fit']['contact_cap'] = (
        f.protocol['population_budget']['fit_endpoints_cap'] // len(f.registration['member_bindings']))
    if fault == 'child': cell['system_text_policy_binding']['bundle_id'] = '1'*64
    elif fault == 'sampling': effective['decoding_params']['temperature'] = 1
    elif fault == 'fit-cap': effective['native_contact_fit']['contact_cap'] += 1
    monkeypatch.setattr(runtime_config, 'compose', lambda *a, **k: SimpleNamespace(values=effective, config_hash=m['config_hash']))
    seen = []
    monkeypatch.setattr(system_text_policy, 'verify_system_text_binding', lambda *a, **k: seen.append('role-bytes'))
    report = SimpleNamespace(run_id=m['run_id'], experiment='e', findings=[])
    gate._check_system_text_binding(report, cell, {}, f.recipe, f.root, f.root / 'data')
    assert bool(report.findings) == (fault is not None)
    assert seen == ([] if fault else ['role-bytes'])


def test_report_preserves_new_identity_without_initialization_claim(tmp_path):
    from test_context_learning_read import fixture as report_fixture
    from speech_aware_evidence_acquisition.analysis.system_context_read import analyze
    from speech_aware_evidence_acquisition.rails.system_text_feedback import CompleteSystemFeedback
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    d, recipe, registration, protocol, roster, supplement = report_fixture(tmp_path)
    protocol['experiment_population'] = {'relpath': 'config.json', 'sha256': 'a'*64}
    protocol['population_cohort'] = 'cohort'
    protocol['population_budget'] = {'K': len(protocol['candidate_members']), 'N': len(recipe['sample_ids'])}
    protocol['algorithms'] = ['bounded-multiparent-aggregate-v1']
    protocol['search_evaluation'] = {'reservation': {'relpath':'r.json','sha256':'b'*64},
                                     'result': {'relpath':'s.json','sha256':'c'*64}}
    for document in (recipe, registration):
        for key in ('experiment_population', 'population_cohort', 'population_budget', 'search_evaluation'):
            document[key] = deepcopy(protocol[key])
    report = analyze(CompleteSystemFeedback(canonical(d)), recipe=recipe, registration=registration,
        protocol=protocol, roster=roster, supplement=supplement)
    assert report['search_algorithms'] == protocol['algorithms']
    assert report['status'] == 'EXPLORATORY-SEARCH-EVALUATION-NO-ADOPTION'
    assert report['optimizer_feedback_allowed'] is False
    recipe['search_evaluation']['result']['sha256'] = 'd'*64
    with pytest.raises(PolicyError, match='provenance'):
        analyze(CompleteSystemFeedback(canonical(d)), recipe=recipe, registration=registration,
            protocol=protocol, roster=roster, supplement=supplement)
