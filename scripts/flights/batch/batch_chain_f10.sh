#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# F10 successor: the shared batch driver runs only after VAR-2 recovery scoring closes.
set -euo pipefail
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
H=/home/chao
PY=/home/chao/.venvs/speechrl/bin/python
SP=$MAIN/scripts/flights/batch
F10_PROTOCOL=docs/readiness/2026-09-25-slurp-stage3-f10-v1/protocol-registered-v1.json
VAR2_PROTOCOL=docs/readiness/2026-09-25-slurp-stage3-var2-recovery-v1/protocol-registered-v1.json
READ_ID=SAEA-SLURP-STAGE3-VAR2-RECOVERY-SUPPLY-READ-V1
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=$DATA
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1

boundary_check() {
  local home=$H data=$DATA repo=$REPO fixture="" commit=""
  if [ "${1:-}" = "--fixture" ]; then
    home=${F10_TEST_HOME:?}; data=${F10_TEST_DATA:?}
    fixture=${F10_TEST_VAR2_PROTOCOL:?}; commit=${F10_TEST_VAR2_COMMIT:?}
  fi
  "$PY" -B - "$home" "$data" "$repo" "$fixture" "$commit" "$VAR2_PROTOCOL" "$READ_ID" <<'PYCODE'
import hashlib, json, subprocess, sys
from pathlib import Path
home, data, repo = map(Path, sys.argv[1:4])
fixture, commit, protocol_rel, read_id = sys.argv[4:]
def stop(message):
    print("REFUSED: " + message, file=sys.stderr); raise SystemExit(20)
def wait(message):
    print("WAIT: " + message); raise SystemExit(10)
def obj(path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error: stop(f"cannot read {path.name}: {error}")
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
if (home / "batch-STOP").exists(): stop("predecessor STOP marker exists")
if fixture:
    protocol = obj(Path(fixture))
else:
    try:
        commit = (home / "var2-recovery-flight-commit.txt").read_text().strip()
        head = subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
        if head != commit: stop("predecessor checkout moved")
        protocol = json.loads(subprocess.check_output(
            ["git","-C",str(repo),"show",f"{commit}:{protocol_rel}"],text=True))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        stop(f"cannot bind predecessor protocol: {error}")
if len(commit)!=40 or any(c not in "0123456789abcdef" for c in commit):
    stop("predecessor commit pin invalid")
if protocol.get("schema")!="saea-var2-recovery-protocol-v1": stop("protocol schema mismatch")
full, smoke = protocol["cells"]["full"], protocol["cells"]["smoke"]
if (full.get("rows"),smoke.get("rows"))!=(625,4): stop("registered roster size mismatch")
qp, sp = home/"batch-queue.json", home/"batch-status.jsonl"
if not qp.exists() or not sp.exists(): wait("predecessor queue/status not yet present")
queue=obj(qp)
if not isinstance(queue,list) or len(queue)!=1: stop("predecessor queue is not one recovery step")
step=queue[0]
fields={"short":"var2-recovery","experiment":full["experiment"],"cell":full["cell_id"],
        "run_id":full["run_id"],"fit_run_id":full["fit_run_id"],
        "gen_attempt_id":full["attempt_id"],"smoke_experiment":smoke["experiment"],
        "smoke_cell":smoke["cell_id"],"smoke_run_id":smoke["run_id"],
        "smoke_attempt_id":smoke["attempt_id"],"expected_rows":625,"ceiling_per_row":17}
if any(step.get(k)!=v for k,v in fields.items()): stop("queue identities or bounds differ")
try: events=[json.loads(line) for line in sp.read_text().splitlines() if line]
except (OSError,ValueError) as error: stop(f"status malformed: {error}")
if any(e.get("event")=="STOP" for e in events): stop("predecessor status STOP")
if not (home/"batch-done").exists(): wait("predecessor driver not done")
if not events or events[-1].get("event")!="driver-done": stop("done marker lacks driver-done")
done=[e.get("detail",{}).get("short") for e in events if e.get("event")=="step-done"]
if done!=["var2-recovery"]: stop("recovery step not completed exactly once")
for event_name,cell in (("smoke-inspect",smoke),("arm-inspect",full)):
    found=[e.get("detail") for e in events if e.get("event")==event_name]
    if len(found)!=1 or not isinstance(found[0],dict) or (
        found[0].get("pass") is not True or found[0].get("run_id")!=cell["run_id"]
        or found[0].get("attempt_id")!=cell["attempt_id"]):
        stop(f"{event_name} acceptance missing")
for cell, event_name in ((smoke,"smoke-inspect"), (full,"arm-inspect")):
    receipt=data/"attempts"/cell["run_id"]/(cell["attempt_id"]+".json")
    if not receipt.exists(): stop("predecessor attempt receipt missing")
    state=obj(receipt).get("state")
    inspected=next(e["detail"] for e in events if e.get("event")==event_name)
    if state!=inspected.get("attempt_state"): stop(f"{event_name} attempt state drifted")
    if cell is full:
        if state!="FINALIZED": stop("full predecessor attempt not FINALIZED")
    elif state not in {"OPENED","FINALIZED"}:
        stop("smoke predecessor attempt state is invalid")
    smoke_manifest=data/"runs"/cell["run_id"]/cell["attempt_id"]/(cell["run_id"]+".run-manifest.json")
    if not smoke_manifest.exists() or inspected.get("sha256_run-manifest")!=digest(smoke_manifest):
        stop(f"{event_name} manifest receipt hash differs")
    sealed=obj(smoke_manifest)
    if (sealed.get("status")!="COMPLETED" or sealed.get("study_commit")!=commit
        or sealed.get("study_repo_dirt")
        or sealed.get("config",{}).get("config_hash")!=cell["composed_config_hash"]
        or inspected.get("manifest_status")!="COMPLETED"
        or inspected.get("rows")!=cell["rows"]
        or inspected.get("distinct")!=cell["rows"]):
        stop(f"{event_name} sealed custody differs")
summary_path=data/"analysis"/read_id/"score-summary.json"
if not summary_path.exists(): wait("derived official scoring not sealed")
summary=obj(summary_path)
arms=["exk10","exk30","exdiv","plan"]
if (summary.get("schema")!="saea-stage3-supply-variant-first-visit-v1"
    or summary.get("stage")!="score" or summary.get("scorer_id")!="slurp-slu-official-train"
    or summary.get("arm_order")!=arms or set(summary.get("arms",{}))!=set(arms)
    or summary.get("sealed_delivered_rows")!=625
    or summary.get("contacts",{}).get("scorer")!=4):
    stop("derived official score summary incomplete")
source=summary.get("source",{})
manifest_path=data/"runs"/full["run_id"]/full["attempt_id"]/(full["run_id"]+".run-manifest.json")
if (source.get("run_id")!=full["run_id"] or source.get("attempt_id")!=full["attempt_id"]
    or source.get("config_hash")!=full["composed_config_hash"]
    or source.get("manifest_path")!=str(manifest_path) or not manifest_path.exists()
    or source.get("manifest_sha256")!=digest(manifest_path)):
    stop("derived score source manifest binding differs")
manifest=obj(manifest_path)
if (manifest.get("status")!="COMPLETED" or manifest.get("study_commit")!=commit
    or manifest.get("study_repo_dirt")
    or manifest.get("config",{}).get("config_hash")!=full["composed_config_hash"]
    or manifest.get("scores",{}).get("sha256")!=source.get("sealed_scores_sha256")
    or summary.get("sealed_delivered_scores_sha256")!=source.get("sealed_scores_sha256")):
    stop("manifest/custody or delivered score binding differs")
for arm,item in summary["arms"].items():
    score=summary_path.parent/f"arm-{arm}-slurp-slu-official-train-scores.json"
    if item.get("rows")!=625 or not score.exists() or item.get("scores_sha256")!=digest(score):
        stop(f"derived official score receipt for {arm} mismatched")
print("READY: complete recovery and four derived official scores verified")
PYCODE
}
if [ "${1:-}" = "--check-boundary" ]; then boundary_check --fixture; exit $?; fi
closed_check() {
  local closure=$1 expected_sha=$2 home=$H data=$DATA repo=$REPO var2="" f10="" predecessor="" target=""
  if [ "${3:-}" = "--fixture" ]; then
    home=${F10_TEST_HOME:?}; data=${F10_TEST_DATA:?}; repo=${F10_TEST_REPO:?}
    var2=${F10_TEST_VAR2_PROTOCOL:?}; f10=${F10_TEST_F10_PROTOCOL:?}
    predecessor=${F10_TEST_VAR2_COMMIT:?}; target=${F10_TEST_F10_COMMIT:?}
  fi
  "$PY" -B - "$closure" "$expected_sha" "$home" "$data" "$repo" "$var2" "$f10" "$predecessor" "$target" "$VAR2_PROTOCOL" "$F10_PROTOCOL" <<'PYCODE'
import hashlib, json, re, subprocess, sys
from pathlib import Path
closure_path=Path(sys.argv[1])
expected_sha=sys.argv[2]
home,data,repo=map(Path,sys.argv[3:6])
var2_fixture,f10_fixture,predecessor,target,var2_rel,f10_rel=sys.argv[6:]
def stop(message):
    print("REFUSED: "+message,file=sys.stderr); raise SystemExit(20)
def obj(path):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError) as error: stop(f"cannot read {path.name}: {error}")
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def pinned(commit,relpath,fixture=""):
    if fixture: return obj(Path(fixture))
    try: return json.loads(subprocess.check_output(
        ["git","-C",str(repo),"show",f"{commit}:{relpath}"],text=True))
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        stop(f"cannot read pinned {relpath}: {error}")
if not re.fullmatch(r"[0-9a-f]{64}",expected_sha): stop("closure SHA invalid")
if not closure_path.is_absolute() or not closure_path.resolve().is_relative_to(
        (data/"coordination").resolve()):
    stop("closure path must be under DATA/coordination")
if not closure_path.is_file() or digest(closure_path)!=expected_sha:
    stop("closure receipt SHA differs")
closure=obj(closure_path)
required={"schema":"saea-closed-predecessor-continuation-v1","status":"decided",
          "owner":"root","predecessor_state":"ABORTED",
          "no_complete_manifest":True,"disposition":"closed-no-further-recovery",
          "next_family":"F10"}
if any(closure.get(k)!=v for k,v in required.items()):
    stop("closure decision schema or disposition differs")
if not isinstance(closure.get("decision_id"),str) or not closure["decision_id"].strip():
    stop("closure decision id absent")
if not isinstance(closure.get("reason"),str) or not closure["reason"].strip():
    stop("closure reason absent")
if var2_fixture:
    predecessor=predecessor
else:
    try:
        predecessor=(home/"var2-recovery-flight-commit.txt").read_text().strip()
        target=(home/"f10-flight-commit.txt").read_text().strip()
        head=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
        if head!=predecessor: stop("predecessor checkout moved before closure")
    except (OSError,subprocess.CalledProcessError) as error:
        stop(f"cannot bind flight commits: {error}")
for label,value in (("predecessor",predecessor),("F10",target)):
    if not re.fullmatch(r"[0-9a-f]{40}",value): stop(f"{label} commit invalid")
var2=pinned(predecessor,var2_rel,var2_fixture)
f10=pinned(target,f10_rel,f10_fixture)
if var2.get("schema")!="saea-var2-recovery-protocol-v1" or f10.get("schema")!="saea-f10-protocol-v1":
    stop("pinned protocol schema mismatch")
full=var2["cells"]["full"]
if (closure.get("predecessor_run_id")!=full["run_id"]
    or closure.get("predecessor_attempt_id")!=full["attempt_id"]
    or closure.get("predecessor_commit")!=predecessor):
    stop("closure predecessor identity differs")
attempt=data/"attempts"/full["run_id"]/(full["attempt_id"]+".json")
if not attempt.is_file() or closure.get("predecessor_attempt_sha256")!=digest(attempt):
    stop("aborted attempt receipt hash differs")
if obj(attempt).get("state")!="ABORTED": stop("predecessor attempt is not ABORTED")
run_dir=data/"runs"/full["run_id"]/full["attempt_id"]
if list(run_dir.glob("*.run-manifest.json")) or (run_dir/"score-jobs.jsonl").exists():
    stop("aborted predecessor has a manifest or official score job")
if (data/"analysis"/"SAEA-SLURP-STAGE3-VAR2-RECOVERY-SUPPLY-READ-V1"/"score-summary.json").exists():
    stop("aborted predecessor has a derived score summary")
if (home/"batch-STOP").exists() or (home/"f10-chain-STOP").exists():
    stop("STOP marker remains outside root archive")
archive_rel=closure.get("archive_relpath")
if (not isinstance(archive_rel,str) or archive_rel!="var2-recovery-closed-before-f10-20260925"
    or Path(archive_rel).is_absolute() or "\\" in archive_rel
    or any(x in ("",".","..") for x in archive_rel.split("/"))):
    stop("closure archive_relpath invalid")
archive=(home/archive_rel).resolve()
if not archive.is_relative_to(home.resolve()):
    stop("closure archive escapes /home/chao")
if not (archive/"batch-STOP").is_file() or not (archive/"root-reconciliation.json").is_file():
    stop("root STOP/reconciliation archive missing")
if (home/"batch-done").exists(): stop("closed predecessor unexpectedly has batch-done")
queue=obj(home/"batch-queue.json")
if not isinstance(queue,list) or len(queue)!=1: stop("closed predecessor queue differs")
step=queue[0]
fields={"short":"var2-recovery","experiment":full["experiment"],"cell":full["cell_id"],
        "run_id":full["run_id"],"gen_attempt_id":full["attempt_id"],
        "fit_run_id":full["fit_run_id"],
        "smoke_experiment":var2["cells"]["smoke"]["experiment"],
        "smoke_cell":var2["cells"]["smoke"]["cell_id"],
        "smoke_run_id":var2["cells"]["smoke"]["run_id"],
        "smoke_attempt_id":var2["cells"]["smoke"]["attempt_id"],
        "expected_rows":625,"ceiling_per_row":17}
if any(step.get(k)!=v for k,v in fields.items()): stop("closed predecessor queue identity differs")
try: events=[json.loads(x) for x in (home/"batch-status.jsonl").read_text().splitlines() if x]
except (OSError,ValueError) as error: stop(f"closed predecessor status malformed: {error}")
if not any(e.get("event")=="STOP" for e in events):
    stop("closed predecessor has no STOP event")
if any(e.get("event")=="driver-done" for e in events):
    stop("closed predecessor status claims completion")
if f10.get("execution_order")!=["smoke","control","empty"]:
    stop("F10 order differs")
cells=f10["cells"]
ids=[cells[key][field] for key in ("smoke","control","empty")
     for field in ("run_id","fit_run_id")]
auth=closure.get("authorized_next_run_ids")
if not isinstance(auth,list) or len(auth)!=6 or len(set(auth))!=6 or set(auth)!=set(ids):
    stop("closure does not authorize exact F10 generation/fit identities")
admission_sha=closure.get("root_admission_sha256")
if not isinstance(admission_sha,str) or not re.fullmatch(r"[0-9a-f]{64}",admission_sha):
    stop("closure root admission SHA invalid")
for key in ("smoke","control","empty"):
    exp=pinned(target,"configs/experiment/"+cells[key]["experiment"]+".json",
               str(repo/"configs/experiment"/(cells[key]["experiment"]+".json")) if f10_fixture else "")
    req=[x for x in exp["cells"][0]["readiness"]["requirements"] if x.get("kind")=="decision"]
    if len(req)!=1 or req[0].get("sha256")!=admission_sha:
        stop("F10 cell root admission pin differs")
    admission=(data/req[0]["relpath"]).resolve()
    if not admission.is_relative_to((data/"coordination").resolve()) or not admission.is_file():
        stop("F10 root admission receipt missing")
    if digest(admission)!=admission_sha: stop("F10 root admission bytes differ")
print("READY: explicit root closure permits F10 without predecessor scoring")
PYCODE
}
if [ "${1:-}" = "--check-closed-boundary" ]; then
  [ "$#" -eq 3 ] || exit 2
  if [ -n "${F10_TEST_HOME:-}" ]; then closed_check "$2" "$3" --fixture
  else closed_check "$2" "$3"; fi
  exit $?
fi
CLOSED=0
CLOSURE=""
CLOSURE_SHA=""
if [ "${1:-}" = "--closed-predecessor" ]; then
  [ "$#" -eq 4 ] && [ "$3" = "--closure-sha256" ] || {
    echo "usage: batch_chain_f10.sh --closed-predecessor PATH --closure-sha256 HASH" >&2; exit 2;
  }
  CLOSED=1; CLOSURE=$2; CLOSURE_SHA=$4
fi

[ "$#" -eq 0 ] || [ "$CLOSED" -eq 1 ] || { echo "usage: batch_chain_f10.sh [--check-boundary|--closed-predecessor PATH --closure-sha256 HASH]" >&2; exit 2; }
[ ! -e "$H/f10-chain-STOP" ] || { echo "F10 STOP marker exists; refuse replay" >&2; exit 8; }
STATUS=$H/f10-chain-status.jsonl
( set -o noclobber; : > "$STATUS" ) || { echo "F10 chain already started; refuse replay" >&2; exit 9; }
exec >> "$H/batch-chain-f10.out" 2>&1
log() {
  "$PY" -B "$SP/batch_jsonl_log.py" "$1" "${2:-null}" --text >> "$STATUS"
  echo "$(date -u +%FT%TZ) $1 ${2:-}"
}
fail() {
  trap - ERR
  log STOP "$1" || true
  printf '%s\n' "$1" > "$H/f10-chain-STOP"
  echo "$1" >&2; exit 9
}
trap 'fail "unexpected shell failure; preserve state"' ERR
if [ "$CLOSED" -eq 1 ]; then
  log closure-check "explicit root decision for closed VAR-2 recovery"
  closed_check "$CLOSURE" "$CLOSURE_SHA" || fail "closed-predecessor receipt rejected"
  if pgrep -f '[b]atch_chain_var2.sh recovery|[b]atch_chain_var2_recovery.sh' >/dev/null; then
    fail "closed predecessor chain still alive"
  fi
  log predecessor-closed "root-closed VAR-2 recovery; no manifest or score"
else
  log waiting "VAR-2 recovery generation and all derived scoring"
  last_wait=""
  while true; do
    [ ! -e "$H/f10-chain-STOP" ] || fail "F10 STOP marker exists"
    [ ! -e "$H/batch-STOP" ] || fail "predecessor batch-STOP exists"
    if boundary_output=$(boundary_check 2>&1); then
      if pgrep -f '[b]atch_chain_var2.sh recovery|[b]atch_chain_var2_recovery.sh' >/dev/null; then
        sleep 10; continue
      fi
      break
    else
      rc=$?
      [ "$rc" -eq 10 ] || fail "predecessor boundary rejected: $boundary_output"
      if [ "$boundary_output" != "$last_wait" ]; then
        log wait-state "$boundary_output"
        last_wait=$boundary_output
      fi
      pgrep -f '[b]atch_chain_var2.sh recovery|[b]atch_chain_var2_recovery.sh' >/dev/null ||
        fail "predecessor chain exited before derived scoring closed"
      sleep 10
    fi
  done
  log predecessor-closed "complete manifest and four derived scores"
fi
[ ! -e "$DATA/locks/flight.lock" ] || fail "flight lock remains"
[ ! -e "$H/batch-STOP" ] || fail "batch STOP remains"
[ ! -e "$H/f10-chain-STOP" ] || fail "F10 STOP remains"
if pgrep -f '[c]ore.flight.cli|[l]ease_cli|[b]atch_driver.sh|[s]tage3_rollout_score.py|[e]valuate.py|[s]lurp_scoring' >/dev/null; then
  fail "flight, lease, driver or scorer process remains"
fi
[ -z "$(git -C "$REPO" status --porcelain)" ] || fail "flight checkout dirty"
COMMIT=$(cat "$H/f10-flight-commit.txt")
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || fail "F10 commit pin invalid"
git -C "$REPO" cat-file -e "$COMMIT^{commit}" || fail "F10 commit absent"
"$PY" -B - "$REPO" "$COMMIT" "$F10_PROTOCOL" "$DATA" <<'PYCODE' || fail "F10 protocol or unopened attempt check failed"
import json,subprocess,sys
from pathlib import Path
repo,commit,relpath,data=Path(sys.argv[1]),sys.argv[2],sys.argv[3],Path(sys.argv[4])
p=json.loads(subprocess.check_output(["git","-C",str(repo),"show",f"{commit}:{relpath}"],text=True))
assert p["schema"]=="saea-f10-protocol-v1" and p["status"]=="registered-before-contact"
assert p["execution_order"]==["smoke","control","empty"]
assert p["limits"]["official_full_scoring_jobs"]==2
cells=p["cells"]
assert cells["smoke"]["rows"]==4 and cells["control"]["rows"]==cells["empty"]["rows"]==625
for cell in cells.values():
    for key in ("run_id","fit_run_id"):
        assert not (data/"attempts"/cell[key]).exists()
        assert not (data/"runs"/cell[key]).exists()
PYCODE
ARCHIVE=$H/var2-recovery-before-f10
if [ "$CLOSED" -eq 1 ]; then
  archive_rel=$("$PY" -B -c 'import json,sys;print(json.load(open(sys.argv[1]))["archive_relpath"])' "$CLOSURE")
  ARCHIVE=$H/$archive_rel/launcher-snapshot
fi
"$PY" -B - "$H" "$ARCHIVE" "$DATA" "$READ_ID" "$CLOSED" "$CLOSURE_SHA" <<'PYCODE' || fail "predecessor archive failed"
import hashlib,json,shutil,sys
from pathlib import Path
home,archive,data=map(Path,sys.argv[1:4]); read_id,closed,closure_sha=sys.argv[4:]
archive.mkdir()  # Exclusive child under the root-owned closure archive in closed mode.
names=["batch-queue.json","batch-status.jsonl","batch-flight-commit.txt",
       "batch-chain-var2-recovery.out","var2-recovery-flight-commit.txt",
       "batch-smoke-1-worker.log","batch-smoke-1-lease.out"]
if closed=="0": names.append("batch-done")
logs=sorted(home.glob("batch-campaign-1-var2-recovery-*.log"))
if not logs: raise RuntimeError("campaign log missing")
files=[home/name for name in names]+logs
if any(not p.is_file() for p in files): raise RuntimeError("archive input missing")
for path in files: shutil.copy2(path,archive/path.name)
receipt={"schema":"saea-f10-predecessor-archive-v1",
         "files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
if closed=="1":
    receipt["closed_predecessor_sha256"]=closure_sha
    receipt["predecessor_disposition"]="closed-no-further-recovery"
else:
    summary=data/"analysis"/read_id/"score-summary.json"
    receipt["derived_score_summary_sha256"]=hashlib.sha256(summary.read_bytes()).hexdigest()
(archive/"archive-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
PYCODE
git -C "$REPO" checkout -q --detach "$COMMIT" || fail "F10 checkout failed"
[ "$(git -C "$REPO" rev-parse HEAD)" = "$COMMIT" ] || fail "F10 HEAD mismatch"
log checkout "$COMMIT"
"$PY" -B - "$H" "$REPO" "$COMMIT" "$F10_PROTOCOL" <<'PYCODE' || fail "F10 queue creation failed"
import json,os,sys
from pathlib import Path
home,repo=map(Path,sys.argv[1:3]);commit,relpath=sys.argv[3:5]
p=json.loads((repo/relpath).read_text())
control,empty,smoke=(p["cells"][x] for x in ("control","empty","smoke"))
def step(order,short,cell,smoke_cell=None):
    return {"order":order,"short":short,"kind":"cell","experiment":cell["experiment"],
      "cell":cell["cell_id"],"smoke_experiment":smoke_cell["experiment"] if smoke_cell else None,
      "smoke_cell":smoke_cell["cell_id"] if smoke_cell else None,
      "campaign_plan":"configs/campaign/"+cell["experiment"]+".json",
      "run_id":cell["run_id"],"fit_run_id":cell["fit_run_id"],
      "gen_attempt_id":cell["attempt_id"],"smoke_run_id":smoke_cell["run_id"] if smoke_cell else None,
      "smoke_attempt_id":smoke_cell["attempt_id"] if smoke_cell else None,
      "expected_rows":625,"contacts_per_row":4,"ceiling_per_row":11,"notool":True,
      "owner":"root-"+cell["cell_id"]}
queue=[step(1,"f10-control",control,smoke),step(2,"f10-empty",empty)]
def replace(name,raw):
    path=home/name;temp=home/(name+".f10-tmp")
    with temp.open("xb") as out: out.write(raw)
    os.replace(temp,path)
replace("batch-queue.json",(json.dumps(queue,indent=2)+"\n").encode())
replace("batch-status.jsonl",b"")
if (home/"batch-done").exists(): (home/"batch-done").unlink()
replace("batch-flight-commit.txt",(commit+"\n").encode())
PYCODE
log driver-start "smoke then control625 then empty625"
set +e
bash "$REPO/scripts/flights/batch/batch_driver.sh"
rc=$?
set -e
[ "$rc" -eq 0 ] || fail "shared F10 driver failed; preserve attempts"
"$PY" -B - "$H" "$DATA" "$REPO" "$F10_PROTOCOL" <<'PYCODE' || fail "terminal F10 scoring verification failed"
import json,sys
from pathlib import Path
home,data,repo=map(Path,sys.argv[1:4]); p=json.loads((repo/sys.argv[4]).read_text())
events=[json.loads(line) for line in (home/"batch-status.jsonl").read_text().splitlines()]
assert events[-1]["event"]=="driver-done"
assert [e["detail"]["short"] for e in events if e["event"]=="step-done"]==["f10-control","f10-empty"]
for key in ("control","empty"):
    cell=p["cells"][key]
    run=data/"runs"/cell["run_id"]/cell["attempt_id"]
    assert (data/"attempts"/cell["run_id"]/(cell["attempt_id"]+".json")).exists()
    assert len((run/"score-jobs.jsonl").read_text().splitlines())==1
    assert json.loads((run/(cell["run_id"]+".run-manifest.json")).read_text())["status"]=="COMPLETED"
PYCODE
log complete "two complete terminal official scoring jobs"
