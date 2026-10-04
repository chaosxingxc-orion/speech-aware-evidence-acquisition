"""A rejected complete trial informs templates without entering the parent pool."""
import copy
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails import system_context_exchange as exchange
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_context_iteration import iteration_fixture, run
from test_system_context_learning import pin, repin
from test_system_context_template_feedback import configure
from test_template_actor_capsule import prepare

ALGORITHM = 'tf-grpo-context-diversity'


def setup_history(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm=ALGORITHM, outcome='regress')
    plan = configure(f)
    plan['feedback_profile']['examples_per_template'] = 0
    f.protocol['iteration_plan'] = pin(f.root, 'iteration-plan.json', plan)
    repin(f)
    f.callbacks = replace(f.callbacks, update_experience=lambda task: {
        'value': [], 'provenance': {'kind': 'synthetic'},
        'usage': dict.fromkeys(('provider_contacts', 'input_tokens', 'output_tokens'), None)})
    original_input_pin = copy.deepcopy(f.recipe_pin)
    original_input = copy.deepcopy(learning._qualified_feedback(f.bindings, recipe_pin=f.recipe_pin, repo_root=f.root))
    first = run(f, ALGORITHM)
    assert first['status'] == 'rejected'
    old = copy.deepcopy(f.trial)
    fresh = copy.deepcopy(old)
    fresh[1]['run_ids']['read'] = 'NEXT-HISTORY-READ'
    fresh[3]['iteration'] = 2
    fresh[3]['rejected_trial_use'] = {'algorithm': ALGORITHM, 'iteration': 2,
        'previous_decision_sha256': first['decision_sha256']}
    original_qualified = learning._qualified_feedback
    calls = []
    def qualified(bindings, *, recipe_pin, repo_root):
        calls.append(recipe_pin['relpath'])
        if recipe_pin == original_input_pin: return original_input
        if recipe_pin['relpath'] == 'history-recipe.json': return fresh
        if recipe_pin['relpath'] == 'trial-recipe.json': return old
        return original_qualified(bindings, recipe_pin=recipe_pin, repo_root=repo_root)
    monkeypatch.setattr(learning, '_qualified_feedback', qualified)
    plan['iteration'] = f.protocol['iteration'] = 2
    plan['rejected_trial_feedback'] = {'mode': 'previous-rejected-trial-aggregate-v1',
        'previous_decision_sha256': first['decision_sha256'],
        'source': {'recipe_pin': {'relpath': 'history-recipe.json', 'sha256': 'd' * 64},
                   'bindings': first['events'][-1]['response']['value']['bindings']}}
    f.protocol['iteration_plan'] = pin(f.root, 'iteration-plan.json', plan)
    repin(f)
    f.calls.clear()
    return f, plan, first, old, fresh, calls


def second(f, previous, callbacks=None):
    return learning.run_context_learning_iteration(f.archive, bindings=f.bindings,
        recipe_pin=f.recipe_pin, repo_root=f.root, algorithm=ALGORITHM, iteration=2,
        policies=f.policies, callbacks=callbacks or f.callbacks,
        previous_decision_sha256=previous)


def test_rejected_trial_reaches_all_semantic_tasks_without_promoting_children(tmp_path, monkeypatch):
    f, plan, first, old, fresh, calls = setup_history(tmp_path, monkeypatch)
    original_decision = (f.archive.root/'context-learning/iterations/tf-grpo-context-diversity-1/decision.json').read_bytes()
    seen = []
    def check(stage, task):
        view = task if stage == 'update_experience' else task['qualified_input']
        history = view['rejected_trial_feedback']
        assert history['previous_decision_sha256'] == first['decision_sha256']
        assert history['status'] == 'rejected' and history['promoted_to_parent'] is False
        assert history['template_feedback']['rows_scored'] == 80
        assert all(t['examples'] == [] for t in history['template_feedback']['templates'])
        assert 'slurp:train:' not in json.dumps(task)
        assert 'unsampled_sample_ids' not in json.dumps(task)
        assert len(history['policies']) == 4
        for cid, p in history['policies'].items():
            assert p['bundle_id'] != f.policies[cid].bundle_id
            assert set(p['policy']) == {'schema', 'source_policy_sha256', 'role_text', 'context_layout', 'node_context'}
        directory=tmp_path/f'capsule-{len(seen)}'; directory.mkdir()
        path,args=prepare(directory,stage,task)
        assert len(exchange.prepare_template_actor_capsule(path,**args)['allowed_files'])==2
        seen.append(task)
    def experience(task):
        check('update_experience',task)
        return {'value': [], 'provenance': {'kind':'synthetic'},
                'usage':dict.fromkeys(('provider_contacts','input_tokens','output_tokens'),None)}
    original=f.callbacks.propose
    def propose(task):
        check('propose',task)
        assert task['parent_bundle_id']==f.policies[task['candidate_id']].bundle_id
        response=original(task); response['value']['changes']={}
        return response
    result=second(f,first['decision_sha256'],replace(f.callbacks,update_experience=experience,propose=propose))
    assert result['status']=='no-change',result['error']
    assert len(seen)==5 and 'history-recipe.json' in calls and 'trial-recipe.json' in calls
    assert result['state_after']['active_bundle_ids']==first['state_after']['active_bundle_ids']
    assert len(result['state_after']['programs'])==4
    assert result['fidelity']['rejected_trial_feedback']=='prospective-own-rejected-trial-aggregate-v1'
    assert (f.archive.root/'context-learning/iterations/tf-grpo-context-diversity-1/decision.json').read_bytes()==original_decision


@pytest.mark.parametrize('fault',['mode','profile','previous','scope','read-reuse','members','roster','sampling','reference','commitment','status','algorithm'])
def test_rejected_history_refuses_unqualified_or_foreign_source_before_callback(tmp_path,monkeypatch,fault):
    f,plan,first,old,fresh,calls=setup_history(tmp_path,monkeypatch)
    if fault=='mode': plan['rejected_trial_feedback']['mode']='any-history'
    elif fault=='profile': plan['feedback_profile']['examples_per_template']=1
    elif fault=='previous': plan['rejected_trial_feedback']['previous_decision_sha256']='e'*64
    elif fault=='scope': fresh[3]['rejected_trial_use']['algorithm']='gepa'
    elif fault=='read-reuse': fresh[1]['run_ids']['read']=old[1]['run_ids']['read']
    elif fault=='members': fresh[2]['member_bindings']['context-0']['bundle_id']='e'*64
    elif fault=='roster': fresh[1]['sample_ids']=fresh[1]['sample_ids'][::-1]
    elif fault=='sampling': fresh[3]['sampling']['seed']=99
    elif fault=='reference': fresh[6]['f1']=.99
    elif fault=='commitment': old[0]['family_id']='changed-source'
    else:
        path=f.archive.root/'context-learning/iterations/tf-grpo-context-diversity-1/decision.json'
        doc=json.loads(path.read_text())
        doc['status' if fault=='status' else 'algorithm']='retained-for-optimization' if fault=='status' else 'gepa'
        doc.pop('decision_sha256'); doc['decision_sha256']=content_hash(doc)
        path.write_text(json.dumps(doc)); first=doc
        plan['rejected_trial_feedback']['previous_decision_sha256']=doc['decision_sha256']
        fresh[3]['rejected_trial_use']['previous_decision_sha256']=doc['decision_sha256']
    f.protocol['iteration_plan']=pin(f.root,'iteration-plan.json',plan); repin(f)
    with pytest.raises(PolicyError): second(f,first['decision_sha256'])
    assert f.calls==[]
    assert not (f.archive.root/'context-learning/iterations/tf-grpo-context-diversity-2/reservation.json').exists()