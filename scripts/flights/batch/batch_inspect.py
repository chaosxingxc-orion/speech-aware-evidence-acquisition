"""Structural inspector for the unattended batch driver. Zero model contact; reads sealed run/attempt files only.

Usage: python batch_inspect.py <data-root> <run_id> <attempt_id> <mode> <expected_rows> <ceiling_per_row> <notool 0|1> <flight_commit> [--result-kind task-answer|artifact]
  mode = smoke | arm | worker (complete generation, no official scoring)
  --text-only (arm mode, set by campaign inspection for a cell with no native episode config): the per-row native receipts do not
  exist, so the contact ceiling is checked on the sealed trace (MODEL_REQUEST count) and the cost block (calls_used) against
  expected_rows x ceiling_per_row; zero tool calls and zero tool schemas are required.
Exit 0 = PASS, 2 = FAIL (reasons printed), 3 = files missing. Never prints utterance text or gold.
"""

import argparse
import glob
import hashlib
import json
import os
import sys
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("data_root")
parser.add_argument("run_id")
parser.add_argument("attempt_id")
parser.add_argument("mode", choices=("smoke", "arm", "worker"))
parser.add_argument("expected_rows", type=int)
parser.add_argument("ceiling_per_row", type=int)
parser.add_argument("notool", choices=("0", "1"))
parser.add_argument("flight_commit")
parser.add_argument(
    "--result-kind", choices=("task-answer", "artifact"), default="task-answer"
)
parser.add_argument("--repo-root", type=Path)
parser.add_argument("--campaign-plan", type=Path)
parser.add_argument("--text-only", action="store_true")
args = parser.parse_args()
if args.campaign_plan is not None:
    if args.mode != "arm" or args.repo_root is None:
        parser.error("campaign inspection requires arm mode and exact repo-root")
    repo = args.repo_root.resolve()
    if repo != Path(__file__).resolve().parents[3]:
        parser.error("campaign inspector must run from the exact frozen repo-root")
    plan = args.campaign_plan.resolve()
    if not plan.is_relative_to(repo):
        parser.error("campaign inspection plan escapes repo-root")
    from speech_aware_evidence_acquisition.core.flight.cli import load_campaign_plan
    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
    results = []
    for experiment, cell in load_campaign_plan(repo, plan):
        c = cell.document
        values = compose(repo, c["model_fragment"], c["dataset_fragment"],
                         c["baseline_fragment"], experiment).values
        native = load_native_episode_config(values, default_phase_program(values["policy"]))
        rows = values["population"]["count"]
        text_only_args = []
        if type(rows) is int and rows >= 1 and native is None:
            # Text-only cell (no native episode, no audio, no tools). The authoritative ceiling is the run-cumulative call cap
            # execution_plan.planned_model_calls (= generation_budget.cap = family_budget.generation_calls_cap), which the
            # registration defines as rows x (1 + registered retries); the per-row ceiling is that cap divided by the rows.
            cap = (values.get("execution_plan") or {}).get("planned_model_calls")
            if (type(cap) is not int or cap < rows or cap % rows
                    or (values.get("generation_budget") or {}).get("cap") != cap
                    or (values.get("family_budget") or {}).get("generation_calls_cap") != cap
                    or default_phase_program(values["policy"]).max_contacts != 1):
                parser.error("text-only campaign inspection requires a consistent registered call cap and a one-contact program")
            ceiling, member_notool, text_only_args = cap // rows, "1", ["--text-only"]
        elif type(rows) is not int or rows < 1 or native is None:
            parser.error("campaign inspection requires registered positive rows and native contact ceiling")
        else:
            ceiling = native.max_contacts
            member_notool = "1" if args.notool == "1" or not any(
                role.tool_names for role in native.roles if role.max_iterations > 0) else "0"
        child = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), args.data_root,
            cell.run_id, cell.attempt_id, "arm", str(rows), str(ceiling), member_notool,
            args.flight_commit, "--result-kind", args.result_kind, *text_only_args], capture_output=True, text=True)
        try:
            report = json.loads(child.stdout)
        except (json.JSONDecodeError, TypeError):
            report = {"run_id": cell.run_id, "attempt_id": cell.attempt_id,
                      "pass": False, "fails": ["member inspection did not return structural JSON"]}
        results.append({"experiment": experiment, "cell": c["cell_id"], "exit_code": child.returncode,
                        "report": report})
    passed = all(row["exit_code"] == 0 and row["report"].get("pass") is True for row in results)
    print(json.dumps({"mode": "campaign", "pass": passed, "members": results}, sort_keys=True))
    sys.exit(0 if passed else 2)
if args.repo_root is not None:
    parser.error("repo-root is only used with an exact campaign plan")
DATA, RUN, ATT, MODE = args.data_root, args.run_id, args.attempt_id, args.mode
EXP_ROWS, CEIL, NOTOOL, COMMIT = (
    args.expected_rows,
    args.ceiling_per_row,
    args.notool == "1",
    args.flight_commit,
)
if EXP_ROWS <= 0 or CEIL <= 0:
    parser.error("expected rows and contact ceiling must be positive")
RESULT_KIND = args.result_kind
fails = []
info = {}
verified_outputs = None

att_path = f"{DATA}/attempts/{RUN}/{ATT}.json"
if not os.path.exists(att_path):
    print(f"FAIL: attempt record missing: {att_path}")
    sys.exit(3)
att = json.load(open(att_path, encoding="utf-8"))
info["attempt_state"] = att.get("state")
info["actual"] = att.get("actual")
if att.get("state") == "ABORTED":
    fails.append(
        f"attempt ABORTED: {str(att.get('failure_reason') or att.get('failure') or '')[:200]}"
    )
if MODE == "worker" and att.get("state") != "OPENED":
    fails.append(f"worker attempt state {att.get("state")} (expected OPENED)")
if MODE == "arm" and att.get("state") != "FINALIZED":
    fails.append(f"arm attempt state {att.get('state')} (expected FINALIZED)")

D = f"{DATA}/runs/{RUN}/{ATT}"
mans = glob.glob(f"{D}/*.run-manifest.json")
if not mans:
    print(f"FAIL: no run manifest under {D}")
    print(json.dumps(info))
    sys.exit(3)
m = json.load(open(mans[0], encoding="utf-8"))
info["result_kind"] = m.get("result_kind", "task-answer")
if info["result_kind"] != RESULT_KIND:
    fails.append(
        f"result kind {info['result_kind']} differs from expected {RESULT_KIND}"
    )
if RESULT_KIND == "artifact":
    info["bundle_verified"] = False
    if len(mans) != 1:
        fails.append("artifact run must have exactly one manifest")
    if (
        m.get("exposure_run_id") != RUN
        or (m.get("plan") or {}).get("attempt_id") != ATT
    ):
        fails.append("artifact run or attempt identity differs")
    if m.get("scorers") != [] or m.get("scores") is not None:
        fails.append("artifact must declare no scorers or score binding")
    if att.get("state") != "FINALIZED":
        fails.append("artifact attempt must be FINALIZED, including smoke")
    # Reuse the authoritative verifier; never invent task scores for an artifact.
    try:
        from speech_aware_evidence_acquisition.core.bundle import verify_bundle

        verified = verify_bundle(Path(mans[0]))
        if verified.manifest != m or verified.attempt_state != "FINALIZED":
            fails.append("verified artifact manifest or attempt state differs")
        else:
            info["bundle_verified"] = True
            verified_outputs = list(verified.outputs_rows)
    except (ValueError, RuntimeError, OSError) as error:
        # The inspector emits structural metadata, never raw model content from errors.
        fails.append(f"artifact bundle verification failed ({type(error).__name__})")
if MODE == "worker":
    info["bundle_verified"] = False
    try:
        from speech_aware_evidence_acquisition.core.bundle import verify_bundle
        from speech_aware_evidence_acquisition.core.flight.receipts import read_flight_receipts
        from speech_aware_evidence_acquisition.core.flight.scoring import load_sealed_score_jobs

        if RESULT_KIND != "task-answer" or len(mans) != 1:
            raise ValueError("worker requires one task generation manifest")
        if m.get("exposure_run_id") != RUN or (m.get("plan") or {}).get("attempt_id") != ATT:
            raise ValueError("worker identity mismatch")
        verified = verify_bundle(Path(mans[0]))
        receipt = read_flight_receipts(Path(D) / "flight-receipts.json")
        stages = receipt["stages"]
        if (verified.attempt_state != "OPENED" or m.get("scores") is not None
                or glob.glob(f"{D}/*.scores.json*") or "score" in stages
                or (receipt["run_id"], receipt["attempt_id"]) != (RUN, ATT)):
            raise ValueError("worker has finalized, scored, or foreign evidence")
        seal = stages["seal"]
        jobs = load_sealed_score_jobs(seal)
        if (len(jobs) != 1 or jobs[0].job_id != ATT
                or Path(seal["manifest_path"]).resolve() != Path(mans[0]).resolve()
                or jobs[0].manifest.resolve() != Path(mans[0]).resolve()
                or seal["finalize"]["status"] != "deferred-to-score-worker"):
            raise ValueError("worker prepared scoring identity mismatch")
        info["bundle_verified"] = True
        verified_outputs = list(verified.outputs_rows)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        fails.append(f"worker generation custody failed ({type(error).__name__})")
info["manifest_status"] = m.get("status")
info["study_commit"] = m.get("study_commit")
info["dirt"] = m.get("study_repo_dirt")
if m.get("status") != "COMPLETED":
    fails.append(f"manifest status {m.get('status')}")
if MODE in {"arm", "worker"}:
    if str(m.get("study_commit")) != COMMIT:
        fails.append(
            f"manifest study_commit {str(m.get('study_commit'))[:8]} != flight commit {COMMIT[:8]}"
        )
    if m.get("study_repo_dirt"):
        fails.append(f"manifest dirt {m.get('study_repo_dirt')}")

outs = glob.glob(f"{D}/*.outputs.jsonl")
rows = (
    verified_outputs
    if verified_outputs is not None
    else (
        [json.loads(line) for line in open(outs[0], encoding="utf-8")] if outs else []
    )
)
info["rows"] = len(rows)
info["distinct"] = len({r.get("sample_id") for r in rows})
if len(rows) != EXP_ROWS or info["distinct"] != EXP_ROWS:
    fails.append(f"rows {len(rows)} distinct {info['distinct']} (expected {EXP_ROWS})")

# dispositions and contacts per row from the episode receipts
disp = {}
over = 0
contacts_hist = {}
tool_calls_total = 0
for r in rows:
    rec = r.get("native_episode_receipt") or {}
    term = (rec.get("terminal_disposition") or {}).get("reason")
    if term:
        disp[term] = disp.get(term, 0) + 1
    for k in (
        "finite_completion",
        "react_exhaustion",
        "planner_action_illegal",
        "context_compaction",
    ):
        v = rec.get(k) or (rec.get("dispositions") or {}).get(k)
        if v:
            disp[k] = disp.get(k, 0) + (len(v) if isinstance(v, list) else 1)
    contacts = (
        rec.get("contact_count")
        or rec.get("contacts")
        or len(rec.get("contact_ids") or [])
        or None
    )
    if isinstance(contacts, int):
        contacts_hist[contacts] = contacts_hist.get(contacts, 0) + 1
        if contacts > CEIL:
            over += 1
info["dispositions"] = disp
info["contacts_per_row_hist"] = dict(sorted(contacts_hist.items()))
if over:
    fails.append(f"{over} rows above the contact ceiling {CEIL}")
if args.text_only and rows and any(r.get("native_episode_receipt") for r in rows):
    fails.append("text-only cell carries native episode receipts")

# cost and score job
gens = glob.glob(f"{D}/*.generation-manifest.json")
if gens:
    c = json.load(open(gens[0], encoding="utf-8")).get("cost") or {}
    info["cost"] = {
        k: c.get(k)
        for k in (
            "calls_used",
            "audio_seconds_used",
            "prompt_tokens_total",
            "completion_tokens_total",
            "tool_calls",
        )
    }
    tool_calls_total = c.get("tool_calls") or 0
    if NOTOOL and tool_calls_total:
        fails.append(f"notool form recorded {tool_calls_total} tool calls")
sj = f"{D}/score-jobs.jsonl"
info["score_jobs"] = (
    sum(1 for _ in open(sj, encoding="utf-8")) if os.path.exists(sj) else 0
)
info["expected_score_jobs"] = (
    0 if RESULT_KIND == "artifact" else (1 if MODE in {"arm", "worker"} else None)
)
if (MODE in {"arm", "worker"} or RESULT_KIND == "artifact") and info["score_jobs"] != info[
    "expected_score_jobs"
]:
    fails.append(
        f"score jobs {info['score_jobs']} (expected {info['expected_score_jobs']})"
    )

# requests: tools key presence (notool must be absent/empty everywhere), fits
traces = (
    [m["raw_trace"]["path"]]
    if info.get("bundle_verified")
    else glob.glob(f"{D}/*.trace.jsonl")
)
tools_present = 0
req_n = 0
if traces:
    with open(traces[0], encoding="utf-8") as fh:
        for line in fh:
            e = json.loads(line)
            if e.get("channel") != "MODEL_REQUEST":
                continue
            req_n += 1
            p = e.get("payload") or {}
            inner = p.get("payload") if isinstance(p.get("payload"), dict) else p
            ts = inner.get("tool_schemas")
            if ts:
                tools_present += 1
info["requests"] = req_n
if args.text_only:
    info["text_only"] = True
    if req_n > EXP_ROWS * CEIL:
        fails.append(f"text-only trace holds {req_n} model requests above rows x ceiling {EXP_ROWS * CEIL}")
    used = (info.get("cost") or {}).get("calls_used")
    if type(used) is not int or used > EXP_ROWS * CEIL:
        fails.append(f"text-only calls_used {used} not within rows x ceiling {EXP_ROWS * CEIL}")
    elif used != req_n:
        fails.append(f"text-only calls_used {used} differs from trace model requests {req_n}")
info["requests_with_tool_schemas"] = tools_present
if NOTOOL and tools_present:
    fails.append(f"notool form: {tools_present} requests carry tool_schemas")

for f in ("run-manifest", "scores", "outputs"):
    if info.get("bundle_verified") and f in {"outputs", "scores"}:
        ps = [m[f]["path"]] if m.get(f) else []
    else:
        ps = glob.glob(f"{D}/*.{f}.json*")
    if ps:
        info[f"sha256_{f}"] = hashlib.sha256(open(ps[0], "rb").read()).hexdigest()

print(
    json.dumps(
        {
            "mode": MODE,
            "run_id": RUN,
            "attempt_id": ATT,
            "pass": not fails,
            "fails": fails,
            **info,
        },
        default=str,
    )
)
sys.exit(0 if not fails else 2)
