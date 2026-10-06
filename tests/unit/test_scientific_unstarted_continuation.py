"""Reject unsafe continuation without running any model or scorer."""
import copy
import importlib.util
from pathlib import Path
import pytest

MODULE = Path(__file__).parents[2] / "scripts/flights/batch/scientific_continuation.py"
spec = importlib.util.spec_from_file_location("scientific_continuation", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(count=4, completed=2):
    reg = {"members": [{"label": f"m{i}", "run_id": f"run{i}", "attempt_id": f"attempt{i}"} for i in range(count)]}
    observation = {"task_state": "Ready", "task_result": 2147943467,
                   "original_owner_live": False, "bound_windows_processes": [],
                   "bound_wsl_processes": [], "stop_present": False,
                   "flight_lock_present": False, "observed_at": "2026-10-06T20:00:00Z"}
    members = {}
    for i, expected in enumerate(reg["members"]):
        members[expected["label"]] = {**expected, "attempt_present": i < completed,
            "run_present": i < completed, "unit_present": i < completed,
            "attempt_state": "FINALIZED" if i < completed else None,
            "started": i < completed, "finished_exit": 0 if i < completed else None,
            "campaign_exit": 0 if i < completed else None,
            "inspection_exit": 0 if i < completed else None,
            "successful_scores": 1 if i < completed else 0,
            "failed_scores": 0, "prepared_scores": 1 if i < completed else 0,
            "failure_present": False}
    return reg, observation, members


def decide(reg, observation, members):
    return module.plan_unstarted_continuation(registration=reg, observation=observation,
        members=members, now="2026-10-06T20:00:20Z", max_age_seconds=60)


@pytest.mark.parametrize("count,complete", [(3,1),(7,5),(10,5)])
def test_derive_remaining_without_replaying_completed(count, complete):
    reg, obs, members = fixture(count, complete)
    before = copy.deepcopy((reg,obs,members))
    result = decide(reg,obs,members)
    assert result["preserved_members"] == [f"m{i}" for i in range(complete)]
    assert result["unstarted_members"] == [f"m{i}" for i in range(complete,count)]
    assert result["read_authorized"] is False
    assert (reg,obs,members) == before


@pytest.mark.parametrize("field,value", [
    ("task_state","Running"),("task_result",0),("original_owner_live",True),
    ("bound_windows_processes",[1]),("bound_wsl_processes",[2]),
    ("stop_present",True),("flight_lock_present",True),
    ("observed_at","2026-10-06T19:50:00Z"),
    ("observed_at","2026-10-06T20:01:00Z"),
    ("observed_at","2026-10-06T20:00:00")])
def test_refuse_live_unsettled_or_stale_observation(field,value):
    reg,obs,members=fixture();obs[field]=value
    with pytest.raises(ValueError):decide(reg,obs,members)


@pytest.mark.parametrize("field,value", [
    ("attempt_state","OPENED"),("finished_exit",1),("campaign_exit",None),
    ("inspection_exit",1),("successful_scores",2),("failed_scores",1),
    ("prepared_scores",2),("failure_present",True),("started",False),
    ("run_id","foreign"),("attempt_id","foreign"),("run_present",False)])
def test_refuse_unfinished_failed_or_mismatched_preserved_member(field,value):
    reg,obs,members=fixture();members['m0'][field]=value
    with pytest.raises(ValueError):decide(reg,obs,members)


@pytest.mark.parametrize("field,value", [
    ("unit_present",True),("run_present",True),("started",True),
    ("successful_scores",1),("failed_scores",1),("attempt_state","OPENED"),
    ("finished_exit",0),("prepared_scores",1),("failure_present",True)])
def test_refuse_any_trace_on_unstarted_member(field,value):
    reg,obs,members=fixture();members['m2'][field]=value
    with pytest.raises(ValueError):decide(reg,obs,members)


def test_refuse_nonprefix_completion():
    reg,obs,members=fixture()
    for key in list(members['m0']):
        if key not in ('label','run_id','attempt_id'):
            members['m0'][key],members['m2'][key]=members['m2'][key],members['m0'][key]
    with pytest.raises(ValueError):decide(reg,obs,members)


@pytest.mark.parametrize("fault", ['missing','extra','duplicate','empty','all_done','none_done'])
def test_refuse_invalid_member_partition(fault):
    reg,obs,members=fixture()
    if fault=='missing':members.pop('m0')
    if fault=='extra':members['extra']=members['m0']
    if fault=='duplicate':reg['members'].append(reg['members'][0])
    if fault=='empty':reg['members']=[];members={}
    if fault=='all_done':reg,obs,members=fixture(4,4)
    if fault=='none_done':reg,obs,members=fixture(4,0)
    with pytest.raises(ValueError):decide(reg,obs,members)


@pytest.mark.parametrize("key", ["run_id", "attempt_id"])
def test_refuse_duplicate_execution_identity(key):
    reg,obs,members=fixture();reg['members'][1][key]=reg['members'][0][key]
    with pytest.raises(ValueError):decide(reg,obs,members)


@pytest.mark.parametrize("value", [0,-1])
def test_refuse_disabled_freshness(value):
    reg,obs,members=fixture()
    with pytest.raises(ValueError):
        module.plan_unstarted_continuation(registration=reg,observation=obs,
            members=members,now="2026-10-06T20:00:20Z",max_age_seconds=value)


def test_refuse_task_running_code_even_with_ready_snapshot():
    reg,obs,members=fixture();obs['task_result']=267009
    with pytest.raises(ValueError):decide(reg,obs,members)


@pytest.mark.parametrize("field,value", [("successful_scores",True),("campaign_exit",False)])
def test_refuse_boolean_numeric_evidence(field,value):
    reg,obs,members=fixture();members['m0'][field]=value
    with pytest.raises(ValueError):decide(reg,obs,members)



def terminal_fixture():
    reg, obs, members = fixture(4,2)
    partition = decide(reg,obs,members)
    snapshot = {"result": partition, "observation": obs, "members": copy.deepcopy(members),
                "at_utc": "2026-10-06T20:00:20Z"}
    plan = {"status":"ROOT-ADMITTED", "authority":"owner227",
            "preserved_members":partition["preserved_members"],
            "unstarted_members":partition["unstarted_members"],
            "missing_native_exit_members":["m1"], "original_task_result":2147943467}
    current = copy.deepcopy(members)
    native = {"task_state":"Ready", "task_result":2147943467,
              "original_owner_live":False, "bound_windows_processes":[],
              "bound_wsl_processes":[], "observed_at":"2026-10-06T20:10:00Z"}
    suffix = {"status":"EXACT_SCIENTIFIC_JOB_TERMINAL", "member_count":2,
              "launch_epoch":"2026-10-06T20:01:00Z", "terminal_epoch":"2026-10-06T20:09:00Z"}
    return reg, snapshot, plan, current, native, suffix


def terminal_decide(values):
    reg,snapshot,plan,current,native,suffix=values
    return module.qualify_continued_terminal(registration=reg, settlement=snapshot,
        plan=plan,current_members=current,original_windows=native,suffix_terminal=suffix,
        actual_missing_native_exit_members=["m1"],now="2026-10-06T20:10:20Z",
        max_age_seconds=60)


def test_terminal_preserves_failed_owner_and_requires_separate_read():
    result=terminal_decide(terminal_fixture())
    assert result['status']=='CONTINUED_SCIENTIFIC_OWNER_CHAIN_VERIFIED'
    assert result['original_task_result']==2147943467
    assert result['member_count']==4
    assert result['read_authorized'] is False


@pytest.mark.parametrize('fault', ['unapproved','wrong_authority','changed_partition',
    'changed_prefix','changed_owner_result','live_original','stale_native',
    'bad_suffix','wrong_count','overlap_epochs','bad_missing_native_exit','unknown_missing_member'])
def test_terminal_rejects_changed_or_incomplete_provenance(fault):
    values=terminal_fixture();reg,snapshot,plan,current,native,suffix=values
    if fault=='unapproved':plan['status']='DRAFT'
    if fault=='wrong_authority':plan['authority']='monitor'
    if fault=='changed_partition':plan['unstarted_members']=['m2']
    if fault=='changed_prefix':current['m0']['successful_scores']=2
    if fault=='changed_owner_result':native['task_result']=0
    if fault=='live_original':native['bound_windows_processes']=[123]
    if fault=='stale_native':native['observed_at']='2026-10-06T19:00:00Z'
    if fault=='bad_suffix':suffix['status']='WAIT'
    if fault=='wrong_count':suffix['member_count']=1
    if fault=='overlap_epochs':suffix['launch_epoch']='2026-10-06T20:00:00Z'
    if fault=='bad_missing_native_exit':plan['missing_native_exit_members']=[]
    if fault=='unknown_missing_member':plan['missing_native_exit_members']=['m9']
    with pytest.raises(ValueError):terminal_decide(values)



def test_observe_actual_operational_files_and_refuse_tampering(tmp_path):
    import hashlib,json
    reg,_,_=fixture(3,1)
    job=tmp_path/'job';job.mkdir();data=tmp_path/'data';data.mkdir()
    m=reg['members'][0];unit=job/m['label'];unit.mkdir()
    ap=data/'attempts'/m['run_id']/(m['attempt_id']+'.json');ap.parent.mkdir(parents=True)
    ap.write_text(json.dumps({'state':'FINALIZED'}))
    run=data/'runs'/m['run_id']/m['attempt_id'];(run/'score-batch').mkdir(parents=True)
    summary=run/'score-batch/batch-summary.json';summary.write_text(json.dumps({'succeeded':1,'failed':0}))
    (run/'score-jobs.jsonl').write_text(json.dumps({'job_id':m['attempt_id']})+'\n')
    op={'state':'FINALIZED','successful_score_jobs':1,'failed_score_jobs':0,'prepared_score_jobs':1,
        'attempt_sha256':hashlib.sha256(ap.read_bytes()).hexdigest(),
        'score_batch_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'quality_read':False}
    (unit/'operational-complete.json').write_text(json.dumps(op))
    (unit/'scientific-started.json').write_text('{}')
    for name in ['scientific-finished.json','campaign-exit.json','inspect-exit.json']:
        (unit/name).write_text(json.dumps({'exit_code':0}))
    observed,pins=module.observe_members(registration=reg,data_root=data,job_root=job)
    assert observed['m0']['attempt_state']=='FINALIZED'
    assert observed['m1']['attempt_present'] is False
    assert pins and all(len(p['sha256'])==64 for p in pins)
    ap.write_text(json.dumps({'state':'OPENED'}))
    with pytest.raises(ValueError):module.observe_members(registration=reg,data_root=data,job_root=job)


def test_observe_rejects_path_escape(tmp_path):
    reg,_,_=fixture();reg['members'][0]['run_id']='../escape'
    with pytest.raises(ValueError):
        module.observe_members(registration=reg,data_root=tmp_path/'data',job_root=tmp_path/'job')


def test_full_owner_capture_is_additional_evidence_not_read_authority():
    receipt = {"schema": "saea-scientific-owner-native-exit-v1", "exit_code": 0,
               "registration_sha256": "a" * 64}
    result = module.verify_full_owner_capture(receipt=receipt, registration_sha="a" * 64)
    assert result["status"] == "NATIVE_OWNER_SUCCESS_BOUND"
    assert result["read_authorized"] is False
    assert result["registration_sha256"] == "a" * 64


@pytest.mark.parametrize("fault", ["missing", "failed", "boolean", "string", "float",
                                    "wrong_registration", "wrong_schema", "missing_exit"])
def test_full_owner_capture_refuses_missing_failed_or_unbound_receipt(fault):
    receipt = {"schema": "saea-scientific-owner-native-exit-v1", "exit_code": 0,
               "registration_sha256": "a" * 64}
    if fault == "missing": receipt = None
    if fault == "failed": receipt["exit_code"] = 23
    if fault == "boolean": receipt["exit_code"] = False
    if fault == "string": receipt["exit_code"] = "0"
    if fault == "float": receipt["exit_code"] = 0.0
    if fault == "wrong_registration": receipt["registration_sha256"] = "b" * 64
    if fault == "wrong_schema": receipt["schema"] = "other"
    if fault == "missing_exit": del receipt["exit_code"]
    with pytest.raises(ValueError):
        module.verify_full_owner_capture(receipt=receipt, registration_sha="a" * 64)
