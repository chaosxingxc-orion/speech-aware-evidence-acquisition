"""Content-free node outcomes retain numeric evidence without case text."""
import json
import pytest
from speech_aware_evidence_acquisition.analysis.abstract_node_feedback import abstract_output, abstract_episode, FEEDBACK_SCHEMA

SECRET="PRIVATE_CASE_VALUE"
def answer(items=None):
 return json.dumps({"scenario":SECRET,"action":SECRET,"entities":items if items is not None else [{"type":SECRET,"filler":SECRET}]})
def counts():
 return {**{f"slu_f1_{a}_{k}":v for a in ["word","char"] for k,v in [("tp",1),("fp",0),("fn",0)]},"scenario_action_exact":1}
def contact(role,text,visit=0):return {"role":role,"text":text,"visit":visit,"interrupted":False,"measurements":{"client_transport_ms":12.5,"input_tokens":20}}
def test_solver_retains_structure_and_revision_counts_not_values():
 out=abstract_output("solver",answer(),previous_solver=answer([]));assert out==[True,1,1,1,0,0,False]
 assert SECRET not in json.dumps(out)
def test_perception_and_review_output_are_allowlisted_counts():
 text=json.dumps({"candidates":[{"intent_id":SECRET,"distinction":SECRET,"evidence_refs":[],"unresolved_fields":[]}]})
 assert abstract_output("perception",text)==[True,1,0,1]
 review=json.dumps({"findings":[{"kind":"boundary","slot_types":[SECRET],"draft_fragment":SECRET,"reason":SECRET}],"checked":[SECRET]})
 assert abstract_output("reviewer",review,previous_solver=answer())==[True,1,0,1,0,0,1,1]
 assert SECRET not in json.dumps(abstract_output("reviewer",review))
@pytest.mark.parametrize("role",["perception","solver","reviewer"])
def test_malformed_extra_fields_and_text_do_not_leak(role):
 for text in [SECRET,'[]','null','{"private":"PRIVATE_CASE_VALUE"}',answer()+" extra"]:
  result=abstract_output(role,text);assert result[0] is False and SECRET not in json.dumps(result)
def test_planner_actions_are_literal_and_unknown_is_not_exposed():
 assert abstract_output("planner","ACCEPT")==[True,0]
 assert abstract_output("planner","REVISE")==[True,1]
 assert abstract_output("planner",SECRET)==[False,2]
def test_complete_episode_preserves_every_contact_and_terminal_utility():
 cs=[contact("perception",'{"candidates":[]}'),contact("solver",answer(),1),contact("reviewer",'{"findings":[],"checked":[]}',2),contact("planner","REVISE",3),contact("solver",answer([]),4)]
 out=abstract_episode(cs,counts=counts(),reference_f1=.5,reliable=True,abstained=False,elapsed_seconds=1.5)
 assert len(out['nodes'])==5 and out['terminal']['utility']==2
 assert out['nodes'][-1][3][3:6]==[0,1,0]
 assert out['nodes'][0][4][-1] is None
 assert SECRET not in json.dumps(out)
 assert out['terminal']['official_aggregate_f1'] is None
 assert FEEDBACK_SCHEMA['node_performance_columns'][-1]=='independent_quality_score'
@pytest.mark.parametrize("change",[{'role':'unexpected'},{'visit':-1},{'interrupted':'yes'},{'measurements':{'client_transport_ms':float('nan')}},{'measurements':{'input_tokens':-1}},{'text':None}])
def test_invalid_operational_measurements_fail(change):
 c=contact('solver',answer());c.update(change)
 with pytest.raises(ValueError):abstract_episode([c],counts=counts(),reference_f1=.5,reliable=True,abstained=False,elapsed_seconds=1)
def test_zero_entities_false_positive_and_abstention_are_explicit():
 c=counts()
 for k in c:c[k]=0
 c['slu_f1_word_fp']=1;c['slu_f1_char_fp']=1
 out=abstract_episode([contact('solver',answer([]))],counts=c,reference_f1=.5,reliable=False,abstained=True,elapsed_seconds=1)
 assert out['terminal']['utility']==-1 and out['terminal']['abstained']
 assert out['missing_roles']==[0,2,3]
@pytest.mark.parametrize('kwargs',[{'elapsed_seconds':-1},{'reference_f1':2},{'reliable':1},{'abstained':None}])
def test_invalid_terminal_measurements_fail(kwargs):
 args=dict(counts=counts(),reference_f1=.5,reliable=True,abstained=False,elapsed_seconds=1);args.update(kwargs)
 with pytest.raises(ValueError):abstract_episode([contact('solver',answer())],**args)
def test_unknown_score_fields_cannot_carry_content():
 c=counts();c['private']=SECRET
 with pytest.raises(ValueError):abstract_episode([contact('solver',answer())],counts=c,reference_f1=.5,reliable=True,abstained=False,elapsed_seconds=1)
def test_missing_unknown_node_scores_are_not_invented():
 out=abstract_episode([contact('planner','ACCEPT')],counts=counts(),reference_f1=.5,reliable=True,abstained=False,elapsed_seconds=1)
 assert all(v is None for v in out['nodes'][0][4][2:])
 assert out['terminal']['intent_correct']==1

@pytest.mark.parametrize('role,text',[('perception','{"candidates":[{}]}'),('reviewer','{"findings":[{}],"checked":[]}')])
def test_malformed_nested_objects_return_only_unavailable_features(role,text):
 out=abstract_output(role,text)
 assert out[0] is False and all(v is None for v in out[1:])
