"""Preserve failed precontact epochs while qualifying exact completed members."""
import copy
import pytest
from test_configured_capacity_family import example
from speech_aware_evidence_acquisition.rails import system_context_structural_entry as entry


def fixture():
    cfg,pin,reg,done,windows,receipts=example(3)
    reg.update(worker="frozen",resource_policy={"start_gib":20,"floor_gib":8})
    def epoch(name,begin,end,exit_code):
        r=copy.deepcopy(reg);r["members"]=r["members"][begin:]
        r["budget"]={"generation_contacts":0,"scorer_contacts":0,"tokenizer_endpoint_caps":{m["label"]:m["contact_cap"] for m in r["members"]},"tokenizer_endpoints_total":sum(m["contact_cap"] for m in r["members"])}
        f=copy.deepcopy(done);f.update(exit_code=exit_code,members=f["members"][begin:end])
        e={"epoch_id":name,"registration":r,"finished":f,"windows_exit":{"exit_code":exit_code}}
        if exit_code:
            e["precontact_failure"]={"candidate_id":reg["members"][end]["label"],"status":"observation-failed","exit_code":125,"worker_started":False}
        if begin:
            e["root_disposition"]={"status":"decided","completed_candidate_ids":[m["label"] for m in reg["members"][:begin]],"eligible_candidate_ids":[m["label"] for m in r["members"]],"eligible_run_ids":[m["run_id"] for m in r["members"]]}
        return e
    return [cfg,pin,[epoch("first",0,1,1),epoch("precontact",1,1,1),epoch("remaining",1,3,0)],receipts]


def qualify(args):
    return entry.qualify_precontact_capacity_epochs(*args,output_reserve=512,structural_reserve=2048,slot_tokens=24576,graph_config_hashes={label:"graph-"+label for label in args[3]})


def test_complete_join_preserves_failures_and_unique_member_sources():
    args=fixture();before=copy.deepcopy(args);result=qualify(args)
    assert args==before
    assert [e["exit_code"] for e in result["epochs"]]==[1,1,0]
    assert result["tokenizer_endpoints"]==9
    assert result["member_source_epochs"]=={"candidate-0":"first","candidate-1":"remaining","candidate-2":"remaining"}
    assert result["runtime_admission"] is False
    assert result["root_review_required"] is True
    assert all(e["evidence_sha256"] for e in result["epochs"])


@pytest.mark.parametrize("mutation",[
    lambda a:a[2].pop(),
    lambda a:a[2][1].update(epoch_id="first"),
    lambda a:a[2][0]["windows_exit"].update(exit_code=0),
    lambda a:a[2][0].pop("precontact_failure"),
    lambda a:a[2][0]["precontact_failure"].update(worker_started=True),
    lambda a:a[2][0]["precontact_failure"].update(candidate_id="candidate-2"),
    lambda a:a[2][0]["precontact_failure"].update(status="ready"),
    lambda a:a[2][0]["precontact_failure"].update(exit_code=0),
    lambda a:a[2][1]["root_disposition"].update(status="PENDING"),
    lambda a:a[2][1]["root_disposition"].update(completed_candidate_ids=[]),
    lambda a:a[2][1]["root_disposition"].update(eligible_candidate_ids=[]),
    lambda a:a[2][1]["root_disposition"].update(eligible_run_ids=[]),
    lambda a:a[2][1]["registration"]["members"].reverse(),
    lambda a:a[2][1]["registration"].update(worker_commit="other"),
    lambda a:a[2][1]["registration"].update(worker="other"),
    lambda a:a[2][1]["registration"]["resource_policy"].update(start_gib=1),
    lambda a:a[2][1]["registration"]["budget"].update(tokenizer_endpoints_total=3),
    lambda a:a[2][1]["registration"].update(status="HELD"),
    lambda a:a[2][1]["finished"].update(generation_contacts=1),
    lambda a:a[2][2]["finished"]["members"].pop(),
    lambda a:a[2][2]["finished"]["members"].reverse(),
    lambda a:a[2][2]["finished"]["members"][0].update(lease_exit_code=1),
    lambda a:a[2][2]["finished"]["members"][0].update(attempt_id="other"),
    lambda a:a[2][2]["finished"].update(exit_code=False),
    lambda a:a[2][2]["windows_exit"].update(exit_code=1),
    lambda a:a[3].pop("candidate-0"),
])
def test_reject_changed_or_incomplete_epoch_join(mutation):
    args=copy.deepcopy(fixture());mutation(args)
    with pytest.raises(ValueError):qualify(args)


def test_single_epoch_uses_existing_qualifier():
    args=fixture();args[2]=[]
    with pytest.raises(ValueError):qualify(args)


@pytest.mark.parametrize("mutation",[
    lambda a:a[2][0]["finished"].update(exit_code=0),
    lambda a:a[2][1].pop("root_disposition"),
    lambda a:a[2][0].update(finished=None),
    lambda a:a[2][2]["finished"].update(members=None),
    lambda a:a[2][1]["registration"].update(experiment_population={}),
    lambda a:a[2][1]["registration"].update(sampling={}),
])
def test_reject_missing_or_invalid_terminal_structure(mutation):
    args=fixture();mutation(args)
    with pytest.raises(ValueError):qualify(args)


def amended_fixture():
    args = fixture()
    args[2].pop(1)
    first, successor = args[2]
    first["precontact_failure"]["status"] = "wait-expired"
    successor["registration"]["resource_policy"]["start_gib"] = 18
    successor["root_disposition"]["resource_policy_amendment"] = {
        "scope": "nongenerative-capacity-only",
        "previous": copy.deepcopy(first["registration"]["resource_policy"]),
        "next": copy.deepcopy(successor["registration"]["resource_policy"]),
        "reason": "Measured capacity headroom; preserve the running floor.",
    }
    return args


def test_explicit_capacity_startup_amendment_preserves_failed_epoch():
    args = amended_fixture()
    before = copy.deepcopy(args)
    result = qualify(args)
    assert args == before
    assert [e["exit_code"] for e in result["epochs"]] == [1, 0]
    assert result["tokenizer_endpoints"] == 9
    assert result["runtime_admission"] is False


@pytest.mark.parametrize("mutation", [
    lambda a: a[2][1]["root_disposition"].pop("resource_policy_amendment"),
    lambda a: a[2][1]["root_disposition"]["resource_policy_amendment"].update(scope="generation"),
    lambda a: a[2][1]["root_disposition"]["resource_policy_amendment"].update(previous={}),
    lambda a: a[2][1]["root_disposition"]["resource_policy_amendment"].update(next={}),
    lambda a: a[2][1]["root_disposition"]["resource_policy_amendment"].update(reason=""),
    lambda a: a[2][1]["registration"]["resource_policy"].update(floor_gib=4),
    lambda a: a[2][1]["registration"]["resource_policy"].update(wait_seconds=900),
    lambda a: a[2][0]["precontact_failure"].update(worker_started=True),
])
def test_reject_unbound_capacity_resource_amendment(mutation):
    args = amended_fixture()
    mutation(args)
    with pytest.raises(ValueError):
        qualify(args)


@pytest.mark.parametrize("field,value", [
    ("start_gib", 7), ("start_gib", float("nan")), ("start_gib", True),
    ("floor_gib", 4), ("wait_seconds", 900),
])
def test_reject_bound_but_invalid_capacity_resource_amendment(field, value):
    args = amended_fixture()
    args[2][1]["registration"]["resource_policy"][field] = value
    args[2][1]["root_disposition"]["resource_policy_amendment"]["next"][field] = value
    with pytest.raises(ValueError):
        qualify(args)
