"""An actor draft keeps aggregate history private from exposure and next-K choices."""
from copy import deepcopy
import json
import pytest
from test_abstract_population_projection import setup, with_archive
from test_partitioned_context_learning import ready, prepare
from test_partitioned_context_continuation import continuation
from test_aggregate_search_feedback import sources, prepare_feedback
from test_abstract_population_sources import pin
from test_experiment_population_config import config
from speech_aware_evidence_acquisition.rails import system_search_learning as subject
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture
def draft(sources):
    s=sources;s.feedback=prepare_feedback(s)
    s.pop=config((2,),n=3)
    ids=list(s.parent['policies'])
    s.options={'batch_id':'search-input-test','algorithm':'fixed-parent-aggregate-v1','iteration':1,
        'experiment_population':pin(s.root,'next-population.json',s.pop),
        'slots':[{'cohort_id':'cohort-0','candidate_id':cid,'mode':'fixed',
                  'parent_bundle_ids':[s.parent['policies'][cid]['bundle_id']]} for cid in ids[:2]],
        'parent_plan_sha256':'e'*64,'instructions':'Use aggregate outcomes to improve complete node templates.',
        'max_actor_input_bytes':2000000}
    return s


def build(s):
    return subject.assemble_search_actor_input(s.archive,feedback_record=s.feedback,
                                              configuration=s.options,repo_root=s.root)


def test_smaller_next_population_keeps_every_record_and_has_no_contact_authority(draft):
    s=draft;r=build(s);a=r['actor_view'];reg=r['registration_draft']
    assert len(a['slots'])==2 and len(a['feedback']['records'])==15
    assert a['population_budget']['candidate_trajectories']==6
    assert reg['actor_input_sha256']==content_hash(a) and reg['status']=='DRAFT'
    assert len(reg['evidence_record_ids'])==15
    assert 'slurp:train:PRIVATE_HISTORY' in {i for source in reg['cumulative_sources'] for i in source['sample_ids']}
    for secret in ['PRIVATE_','slurp:train:','cumulative_sources','private_custody','"knowledge":','"construction_instruction":']:
        assert secret not in json.dumps(a)
    assert r['source_qualification_required'] and not r['learner_exported']
    ref=pin(s.root,'draft-registration.json',reg)
    with pytest.raises(PolicyError):subject.reserve_search_update(s.archive,registration_pin=ref,repo_root=s.root)
    assert not (s.archive.root/'context-learning/search-updates').exists()


def test_both_algorithms_get_identical_feedback_and_recombination_parents(draft):
    s=draft;fixed=build(s)
    s.options['algorithm']='bounded-multiparent-aggregate-v1'
    s.options['slots'][0]['mode']='recombine'
    s.options['slots'][0]['parent_bundle_ids'].append(s.options['slots'][1]['parent_bundle_ids'][0])
    s.options['slots'][1]['mode']='explore'
    multi=build(s)
    assert multi['actor_view']['feedback']==fixed['actor_view']['feedback']
    assert len(multi['actor_view']['slots'][0]['parent_bundle_ids'])==2
    assert multi['registration_draft']['actor_input_sha256']!=fixed['registration_draft']['actor_input_sha256']


@pytest.mark.parametrize('fault',['feedback-hash','configuration-extra','budget','non-english','mode','count','parent','population-pin','records','private-view','plan-hash'])
def test_bad_input_never_produces_actor_draft(draft,fault):
    s=draft
    if fault=='feedback-hash':s.feedback['feedback_sha256']='a'*64
    elif fault=='configuration-extra':s.options['raw_cases']=[]
    elif fault=='budget':s.options['max_actor_input_bytes']=1
    elif fault=='non-english':s.options['instructions']='\u4e2d\u6587'
    elif fault=='mode':s.options['slots'][0]['mode']='explore'
    elif fault=='count':s.options['slots'].pop()
    elif fault=='parent':s.options['slots'][0]['parent_bundle_ids']=['a'*64]
    elif fault=='population-pin':(s.root/'next-population.json').write_text('{}')
    elif fault=='plan-hash':s.options['parent_plan_sha256']='invalid'
    else:
        if fault=='records':s.feedback['aggregate_feedback']['records'][0]['business']['slu_f1']=0
        else:s.feedback['aggregate_feedback']['raw_cases']=['private']
        s.feedback['feedback_sha256']=content_hash({k:v for k,v in s.feedback.items() if k!='feedback_sha256'})
    with pytest.raises((PolicyError,FileNotFoundError)):build(s)
    assert not (s.archive.root/'context-learning/search-updates').exists()
