"""Rejected trials remain abstract evidence without replacing active parents."""
from copy import deepcopy
import json
import pytest
from test_abstract_population_projection import setup, with_archive
from test_partitioned_context_learning import ready
from test_partitioned_context_trial import trial, run
from test_abstract_population_sources import pin
from speech_aware_evidence_acquisition.rails import system_context_partitioned_trial as subject
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture
def history(trial, monkeypatch):
    s = trial
    s.qualified = run(s)
    s.qualified_pin = pin(s.data, 'qualified.json', s.qualified, True)
    s.decision = {'schema': 'saea-partitioned-context-root-retention-v1',
        'qualification': s.qualified_pin,
        'decision': 'REJECT_WHOLE_UPDATE_RETAIN_BEFORE_POPULATION',
        'criterion': s.qualified['criterion'],
        'utility_before': s.qualified['utility_before'],
        'utility_after': s.qualified['utility_after'],
        'new_learner_export': False, 'new_runtime_admission': False,
        'preserve_all_candidates': True}
    s.decision_pin = pin(s.root, 'decision.json', s.decision)
    s.history_projection_pin = pin(s.root, 'history-projection.json', {})
    original = subject.project_registered_population
    s.projected = deepcopy(original(projection_pin=s.pin, repo_root=s.root,
                                     data_root=s.data, policy_archive=s.archive))
    s.projected['private_custody']['source_join'] = s.request['source_registration_pin']
    s.projected['private_custody']['projection_registration'] = s.history_projection_pin
    records = {r['candidate_id']: r for r in s.result['records']}
    for tag, templates in s.projected['learner_view']['templates'].items():
        for cid in templates:
            doc = s.archive.load_policy(records[cid]['bundle_id']).as_json()
            templates[cid] = {'bundle_id': records[cid]['bundle_id'],
                **{k: doc[k] for k in ('role_text', 'context_layout', 'node_context')}}
    def projected(**kw):
        if kw['projection_pin'] == s.history_projection_pin:
            return deepcopy(s.projected)
        return original(**kw)
    monkeypatch.setattr(subject, 'project_registered_population', projected)
    s.history_registration = {'schema': 'saea-rejected-context-history-registration-v1',
        'status': 'ROOT_REGISTERED', 'input_sha256': s.packet['input_sha256'],
        'trial_contract': s.contract_pin, 'root_decision': s.decision_pin,
        'successor_projection': s.history_projection_pin, 'runtime_admission': False}
    s.history_pin = pin(s.root, 'history.json', s.history_registration)
    return s


def history_view(s):
    return subject.prepare_rejected_context_history(s.archive,
        registration_pin=s.history_pin, repo_root=s.root, data_root=s.data)


def test_history_does_not_activate_children_or_expose_private_content(history):
    s = history
    before = {str(p): p.read_bytes() for p in s.archive.root.rglob('*') if p.is_file()}
    out = history_view(s)
    assert out['active_parent_bundle_ids'] == {k:v['bundle_id'] for k,v in s.packet['policies'].items()}
    assert out['learner_history']['disposition'] == 'rejected-retain-before-population'
    assert list(out['learner_history']['observation']['templates']) == ['cohort-0', 'cohort-1']
    assert out['runtime_admission'] is False and out['learner_exported'] is False
    assert out['contacts_added'] == {'model': 0, 'scorer': 0}
    assert 'slurp:train:PRIVATE_REFERENCE' in out['private_custody']['feedback_sample_ids']
    for secret in ('PRIVATE_VALUE', 'PRIVATE_REFERENCE', 'PRIVATE_EXPOSURE', 'slurp:train:', str(s.data)):
        assert secret not in json.dumps(out['learner_history'])
    assert before == {str(p):p.read_bytes() for p in s.archive.root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('fault', ['draft','dispatch','decision','utility','qualification','join','projection', 'template','missing'])
def test_wrong_decision_or_unbound_history_fails_closed(history, fault):
    s=history
    if fault=='draft': s.history_registration['status']='DRAFT'
    elif fault=='dispatch': s.history_registration['runtime_admission']=True
    elif fault=='decision': s.decision['decision']='ADOPT_CHILDREN'
    elif fault=='utility': s.decision['utility_after'] += 1
    elif fault=='qualification': (s.data/'qualified.json').write_text('{}')
    elif fault=='join': s.projected['private_custody']['source_join']={'relpath':'other','sha256':'a'*64}
    elif fault=='projection': s.projected['private_custody']['projection_registration']={}
    elif fault=='missing': s.projected['learner_view']['templates'].pop('cohort-1')
    else: s.projected['learner_view']['templates']['cohort-1']['candidate-4']['role_text']['solver']='Unregistered change.'
    s.history_registration['root_decision']=pin(s.root,'decision.json',s.decision)
    s.history_pin=pin(s.root,'history.json',s.history_registration)
    with pytest.raises(PolicyError): history_view(s)


def test_revoked_last_source_refuses_history(history, monkeypatch):
    def fail(*args, **kwargs): raise PolicyError('last seal revoked')
    monkeypatch.setattr(subject,'qualify_partitioned_context_trial',fail)
    with pytest.raises(PolicyError,match='last seal revoked'):history_view(history)


def test_changed_decision_during_projection_refuses_history(history, monkeypatch):
    s=history; original=subject.project_registered_population
    def changed(**kw):
        value=original(**kw)
        if kw['projection_pin']==s.history_projection_pin:(s.root/'decision.json').write_text('{}')
        return value
    monkeypatch.setattr(subject,'project_registered_population',changed)
    with pytest.raises(PolicyError):history_view(s)
