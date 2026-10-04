"""One semantic batch binds every prospectively registered full-system branch."""
import copy
import pytest
from speech_aware_evidence_acquisition.rails.template_population import validate_population_response

def fixture():
 parent='a'*64;profiles={k:{'context_layout':{'native_role_query_placement':None if k in 'AB' else 'before-speech-v1'},'node_context':{'tool_schema_rendering':'constant' if k in 'AD' else 'per-role','reviewer_history_scope':'full' if k in 'AC' else 'latest-solver-and-local-tools'}} for k in 'ABCD'}
 slots=[{'candidate_id':f'branch-{i*4+j+1:02d}','strategy_id':f'strategy-{i+1}','assembly_profile':a} for i in range(4) for j,a in enumerate('ABCD')]
 req={'input_sha256':'b'*64,'common_parent_bundle_id':parent,'common_parent_candidate':'parent','qualified_own_history':{'policies':{'parent':{'policy':{'role_text':{'perception':'Fixed perception'}}}}},'slots':slots,'assembly_profiles':profiles}
 branches=[]
 for s in slots:
  changes=copy.deepcopy(profiles[s['assembly_profile']]);changes['role_text']={'perception':'Fixed perception','solver':s['strategy_id']+' evidence method','reviewer':s['strategy_id']+' review method','planner':'Keep the legal Planner routing contract.'}
  p={'schema':'saea-context-policy-update-proposal-v1','algorithm':'tf-grpo-context-diversity','iteration':1,'candidate_id':s['candidate_id'],'component':'joint-system','parent_ids':[parent],'changes':changes,'rationale':'Untested complete-system template combination.','hypotheses':['Evaluate quality and cost jointly.'],'evidence':['b'*64]}
  branches.append({'strategy_id':s['strategy_id'],'assembly_profile':s['assembly_profile'],'proposal':p})
 hashes={'request.json':'c'*64,'instructions.md':'d'*64}
 out={'schema':'saea-template-population-response-v1','strategies':[{'strategy_id':f'strategy-{i+1}','mechanism':f'Evidence method {i+1}','tradeoff':'Measure, do not assume.'} for i in range(4)],'branches':branches,'provenance':{'input_hashes':copy.deepcopy(hashes),'model':'gpt-6.1-sol','reasoning_effort':'high'},'usage':{'provider_contacts':None,'input_tokens':None,'output_tokens':None}}
 return req,out,hashes

def test_all16_are_validated_in_original_order_without_activation():
 req,out,h=fixture();before=copy.deepcopy(out);ps=validate_population_response(out,req,input_hashes=h)
 assert len(ps)==16 and [p.as_json()['candidate_id'] for p in ps]==[s['candidate_id'] for s in req['slots']]
 assert out==before and out['usage']['provider_contacts'] is None

@pytest.mark.parametrize('change',['missing','extra','parent','evidence','perception','knowledge','profile','duplicate','provenance','usage','strategy','role','order','algorithm'])
def test_invalid_batch_cannot_be_silently_repaired_or_filtered(change):
 req,out,h=fixture();p=out['branches'][0]['proposal']
 if change=='missing':out['branches'].pop()
 elif change=='extra':out['branches'].append(copy.deepcopy(out['branches'][0]))
 elif change=='parent':p['parent_ids']=['e'*64]
 elif change=='evidence':p['evidence']=[]
 elif change=='perception':p['changes']['role_text']['perception']='Changed input'
 elif change=='knowledge':p['changes']['knowledge']={}
 elif change=='profile':p['changes']['context_layout']['native_role_query_placement']='before-speech-v1'
 elif change=='duplicate':out['branches'][4]['proposal']['changes']=copy.deepcopy(p['changes'])
 elif change=='provenance':out['provenance']['input_hashes']['request.json']='f'*64
 elif change=='usage':out['usage']['input_tokens']=-1
 elif change=='strategy':out['strategies'][1]['strategy_id']='strategy-1'
 elif change=='role':p['changes']['role_text'].pop('reviewer')
 elif change=='order':out['branches'][0],out['branches'][1]=out['branches'][1],out['branches'][0]
 elif change=='algorithm':p['algorithm']='gepa'
 with pytest.raises(ValueError):validate_population_response(out,req,input_hashes=h)

def test_four_strategy_rows_require_different_solver_reviewer_designs():
 req,out,h=fixture()
 for row in out['branches'][4:]:
  row['proposal']['changes']['role_text']['solver']='strategy-1 evidence method'
  row['proposal']['changes']['role_text']['reviewer']='strategy-1 review method'
 with pytest.raises(ValueError):validate_population_response(out,req,input_hashes=h)

def test_numeric_provider_metering_is_allowed_without_claiming_one_contact():
 req,out,h=fixture();out['usage']={'provider_contacts':2,'input_tokens':300,'output_tokens':500}
 assert len(validate_population_response(out,req,input_hashes=h))==16
