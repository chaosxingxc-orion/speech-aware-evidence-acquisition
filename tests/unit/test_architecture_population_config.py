"""Prospective architecture accounting preserves graph identities and spent proposals."""
from copy import deepcopy

import pytest

from speech_aware_evidence_acquisition.rails.experiment_population import (
    load_population_config, population_accounting, population_stage_spec, validate_population_config,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_experiment_population_config import boundary_config
from test_system_context_learning import pin


def architecture(tmp_path, n=20):
    d = boundary_config()
    d['schema'] = 'saea-experiment-population-config-v4'
    d['boundary_maintenance']['mode'] = 'observe-only'
    d['proposer'] = None
    d['cohorts'] = [dict(cohort_id='comparison', candidate_ids=['off', 'tool'],
                         control_ids=['seed', 'seed-aa'],
                         sample_ids=[f'slurp:train:{i}' for i in range(n)])]
    members = []
    for name, cap, roles in [('seed', 13, d['nodes']), ('seed-aa', 13, d['nodes']),
                             ('off', 2, ['perception', 'solver']),
                             ('tool', 3, ['perception', 'solver'])]:
        # These fixtures attest file custody only, not runtime readiness.
        configuration = pin(tmp_path, name+'.json', {'synthetic_member': name})
        members.append(dict(cohort_id='comparison', member_id=name,
                            base_bundle_id='a'*64, execution_config=configuration,
                            active_roles=list(roles), model_per_trajectory=cap))
    d['architecture'] = dict(profile='manually-specified-architecture-v1',
                             semantic_proposals=0, learner_export=False, members=members)
    return d


@pytest.mark.parametrize('n', [7, 20, 50])
def test_heterogeneous_systems_account_from_config_without_proposer(tmp_path, n):
    d = architecture(tmp_path, n)
    saved = deepcopy(d)
    assert validate_population_config(d, allow_architecture=True) == saved
    budget = population_accounting(d, 'comparison')
    assert budget['family_trajectories'] == 4*n
    assert budget['generation_contacts_cap'] == 31*n
    assert budget['fit_endpoints_cap'] == 31*n*4
    assert budget['K'] == 2 and budget['N'] == n
    assert 'M' not in budget
    assert budget['active_node_counts'] == {'seed': 4, 'seed-aa': 4, 'off': 2, 'tool': 2}
    p = pin(tmp_path, 'population.json', d)
    stage = population_stage_spec(p, repo_root=tmp_path, cohort_id='comparison', allow_architecture=True)
    assert stage['member_generation_contacts_caps'] == {'seed': 13*n, 'seed-aa': 13*n, 'off': 2*n, 'tool': 3*n}
    assert stage['member_fit_endpoints_caps']['tool'] == 3*n*4
    assert stage['semantic_proposals'] == 0 and stage['proposer'] is None
    assert stage['learner_export'] is False and stage['runtime_admission'] is False
    assert stage['role_universe'] == d['nodes'] and 'M' not in stage
    assert stage['architecture_members'] == d['architecture']['members']
    assert stage['execution_identity_sha256']['off'] != stage['execution_identity_sha256']['tool']
    assert stage['execution_identity_sha256']['off'] == content_hash(d['architecture']['members'][2])
    assert d == saved


@pytest.mark.parametrize('fault', [
    'missing_architecture', 'unknown_profile', 'proposal_spend', 'bool_spend',
    'learner_export', 'fake_proposer', 'missing_member', 'duplicate_member',
    'unknown_member', 'wrong_cohort', 'reordered_members', 'blank_bundle',
    'bad_pin', 'pin_extra', 'unknown_role', 'duplicate_role', 'wrong_role_order',
    'missing_solver', 'zero_cap', 'bool_cap', 'over_cap', 'extra_member_field',
])
def test_reject_ambiguous_architecture_identity(tmp_path, fault):
    d = architecture(tmp_path)
    a = d['architecture']
    m = a['members'][2]
    if fault == 'missing_architecture': d.pop('architecture')
    elif fault == 'unknown_profile': a['profile'] = 'text-learning'
    elif fault == 'proposal_spend': a['semantic_proposals'] = 1
    elif fault == 'bool_spend': a['semantic_proposals'] = False
    elif fault == 'learner_export': a['learner_export'] = True
    elif fault == 'fake_proposer': d['proposer'] = {'model': 'gpt-6-astra', 'reasoning_effort': 'ultra', 'semantic_batches': 1}
    elif fault == 'missing_member': a['members'].pop()
    elif fault == 'duplicate_member': a['members'][3] = deepcopy(m)
    elif fault == 'unknown_member': m['member_id'] = 'absent'
    elif fault == 'wrong_cohort': m['cohort_id'] = 'other'
    elif fault == 'reordered_members': a['members'].reverse()
    elif fault == 'blank_bundle': m['base_bundle_id'] = ''
    elif fault == 'bad_pin': m['execution_config']['sha256'] = 'bad'
    elif fault == 'pin_extra': m['execution_config']['allow_missing'] = True
    elif fault == 'unknown_role': m['active_roles'] = ['perception', 'unknown']
    elif fault == 'duplicate_role': m['active_roles'] = ['solver', 'solver']
    elif fault == 'wrong_role_order': m['active_roles'] = ['solver', 'perception']
    elif fault == 'missing_solver': m['active_roles'] = ['perception']
    elif fault == 'zero_cap': m['model_per_trajectory'] = 0
    elif fault == 'bool_cap': m['model_per_trajectory'] = True
    elif fault == 'over_cap': m['model_per_trajectory'] = 14
    else: m['permission'] = 'dispatch'
    with pytest.raises(PolicyError): validate_population_config(d, allow_architecture=True)


def test_stage_refuses_changed_member_file_and_population_pin(tmp_path):
    d = architecture(tmp_path)
    p = pin(tmp_path, 'population.json', d)
    (tmp_path/'off.json').write_text('{}')
    with pytest.raises(PolicyError): population_stage_spec(p, repo_root=tmp_path, cohort_id='comparison', allow_architecture=True)


def test_architecture_cannot_leak_into_historical_config(tmp_path):
    d = architecture(tmp_path)
    d['schema'] = 'saea-experiment-population-config-v3'
    with pytest.raises(PolicyError): validate_population_config(d)


def test_generic_loaders_require_explicit_architecture_opt_in(tmp_path):
    d = architecture(tmp_path)
    p = pin(tmp_path, 'population.json', d)
    with pytest.raises(PolicyError, match='explicit architecture opt-in'):
        validate_population_config(d)
    with pytest.raises(PolicyError, match='explicit architecture opt-in'):
        load_population_config(p, repo_root=tmp_path)
    with pytest.raises(PolicyError, match='explicit architecture opt-in'):
        population_stage_spec(p, repo_root=tmp_path, cohort_id='comparison')


def test_search_reservation_rejects_manual_profile_before_archive_write(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
    from speech_aware_evidence_acquisition.rails.system_search_learning import reserve_search_update
    from speech_aware_evidence_acquisition.rails.system_text_policy import SEARCH_ALGORITHMS
    d = architecture(tmp_path)
    p = pin(tmp_path, 'population.json', d)
    archive = SystemSearchArchive(tmp_path/'archive')
    writes = []
    monkeypatch.setattr(archive, '_write', lambda *args: writes.append(args))
    registration = dict(schema='saea-search-update-registration-v1', status='ROOT_REGISTERED',
                        batch_id='manual-no-reservation', algorithm=SEARCH_ALGORITHMS[0], iteration=1,
                        experiment_population=p, qualified_input_sha256='a'*64, actor_input_sha256='b'*64,
                        slots=[], evidence_record_ids=[], cumulative_sources=[])
    r = pin(tmp_path, 'registration.json', registration)
    with pytest.raises(PolicyError, match='explicit architecture opt-in'):
        reserve_search_update(archive, registration_pin=r, repo_root=tmp_path)
    assert writes == []
