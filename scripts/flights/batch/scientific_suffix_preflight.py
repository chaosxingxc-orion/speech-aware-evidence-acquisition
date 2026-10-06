"""Read-only start-time verification for an explicitly admitted untouched suffix."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
from scientific_continuation import observe_members, plan_unstarted_continuation, require


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--observation")
    parser.add_argument("--output")
    args=parser.parse_args()
    plan_path=Path(args.plan)
    require(digest(plan_path)==args.sha256,"Continuation plan changed")
    plan=json.loads(plan_path.read_text())
    require(plan["status"]=="ROOT-ADMITTED" and plan["authority"]=="owner227","Root continuation admission absent")
    for pin in plan["source_pins"] + plan["preserved_pins"]:
        require(digest(pin["path"])==pin["sha256"],"Pinned evidence or source changed")
    registration_path=Path(plan["registration_path"])
    require(digest(registration_path)==plan["registration_sha256"],"Original registration changed")
    registration=json.loads(registration_path.read_text())
    for pin in registration["pinned_files"]:
        require(digest(pin["path"])==pin["sha256"],"Original frozen registration source changed")
    worker=Path(registration["worker"])
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=worker,text=True).strip()==registration["worker_commit"],"Frozen worker commit differs")
    require(not subprocess.check_output(["git","status","--porcelain"],cwd=worker,text=True).strip(),"Frozen worker is dirty")
    original=Path(registration["new_receipt_root"])
    require(not (original/"scientific-finished.json").exists() and not (original/"scientific-windows-failure.json").exists(),"Original missing outer receipts changed")
    observation=json.loads(Path(args.observation or plan["native_observation_path"]).read_text())
    require(observation["task_name"]==plan["original_task_name"] and observation["registration_sha256"]==plan["registration_sha256"],"Native observation binding differs")
    require(observation["task_result"]==plan["original_task_result"],"Original task result changed")
    processes=[]
    tokens={b"speech_aware_evidence_acquisition.core.flight.cli",b"speech_aware_evidence_acquisition.core.scoring_batch",b"speech_aware_evidence_acquisition.core.driver",b"speech_aware_evidence_acquisition.core.flight.lease_cli"}
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        if int(path.parent.name)==os.getpid():continue
        try:raw=path.read_bytes()
        except OSError:continue
        if tokens.intersection(raw.split(b"\0")) or str(original).encode() in raw:
            processes.append({"pid":int(path.parent.name),"command":raw.replace(b"\0",b" ").decode()})
    data=Path(registration["data_root"])
    observation.update(bound_wsl_processes=processes,stop_present=Path(registration["stop_marker"]).exists(),flight_lock_present=(data/"locks/flight.lock").exists())
    members,pins=observe_members(registration=registration,data_root=data,job_root=original)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (data/"locks/generation.guard").open("a") as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        partition=plan_unstarted_continuation(registration=registration,observation=observation,members=members,now=now,max_age_seconds=plan["observation_max_age_seconds"])
        for key in ("preserved_members","unstarted_members","original_task_result"):
            require(partition[key]==plan[key],"Continuation member partition changed")
        require(sum(m["generation_cap"] for m in registration["members"] if m["label"] in partition["unstarted_members"])==plan["remaining_generation_cap"],"Remaining generation budget differs")
        require(sum(m["fit_endpoint_cap"] for m in registration["members"] if m["label"] in partition["unstarted_members"])==plan["remaining_fit_endpoint_cap"],"Remaining FIT budget differs")
        require(digest(plan_path)==args.sha256,"Plan changed during preflight")
        result={"schema":"saea-scientific-suffix-live-preflight-v1","at_utc":now,"status":"PASS","partition":partition,"observation":observation,"operational_pins":pins,"plan_sha256":args.sha256,"model_contacts":0,"scorer_contacts":0}
        with Path(args.output or plan["preflight_output"]).open("x") as stream:
            json.dump(result,stream,indent=2);stream.write("\n")
    print(json.dumps({"status":"PASS","unstarted_members":partition["unstarted_members"],"quality_read":False}))


if __name__=="__main__":main()
