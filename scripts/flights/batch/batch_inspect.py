"""Structural inspector for the unattended batch driver. Zero model contact; reads sealed run/attempt files only.

Usage: python batch_inspect.py <data-root> <run_id> <attempt_id> <mode> <expected_rows> <ceiling_per_row> <notool 0|1> <flight_commit>
  mode = smoke | arm
Exit 0 = PASS, 2 = FAIL (reasons printed), 3 = files missing. Never prints utterance text or gold.
"""
import glob
import hashlib
import json
import os
import sys

DATA, RUN, ATT, MODE, EXP_ROWS, CEIL, NOTOOL, COMMIT = sys.argv[1:9]
EXP_ROWS, CEIL, NOTOOL = int(EXP_ROWS), int(CEIL), NOTOOL == "1"
fails = []
info = {}

att_path = f"{DATA}/attempts/{RUN}/{ATT}.json"
if not os.path.exists(att_path):
    print(f"FAIL: attempt record missing: {att_path}"); sys.exit(3)
att = json.load(open(att_path, encoding="utf-8"))
info["attempt_state"] = att.get("state"); info["actual"] = att.get("actual")
if att.get("state") == "ABORTED":
    fails.append(f"attempt ABORTED: {str(att.get('failure_reason') or att.get('failure') or '')[:200]}")
if MODE == "arm" and att.get("state") != "FINALIZED":
    fails.append(f"arm attempt state {att.get('state')} (expected FINALIZED)")

D = f"{DATA}/runs/{RUN}/{ATT}"
mans = glob.glob(f"{D}/*.run-manifest.json")
if not mans:
    print(f"FAIL: no run manifest under {D}"); print(json.dumps(info)); sys.exit(3)
m = json.load(open(mans[0], encoding="utf-8"))
info["manifest_status"] = m.get("status"); info["study_commit"] = m.get("study_commit"); info["dirt"] = m.get("study_repo_dirt")
if m.get("status") != "COMPLETED":
    fails.append(f"manifest status {m.get('status')}")
if MODE == "arm":
    if str(m.get("study_commit")) != COMMIT:
        fails.append(f"manifest study_commit {str(m.get('study_commit'))[:8]} != flight commit {COMMIT[:8]}")
    if m.get("study_repo_dirt"):
        fails.append(f"manifest dirt {m.get('study_repo_dirt')}")

outs = glob.glob(f"{D}/*.outputs.jsonl")
rows = [json.loads(l) for l in open(outs[0], encoding="utf-8")] if outs else []
info["rows"] = len(rows); info["distinct"] = len({r.get("sample_id") for r in rows})
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
    for k in ("finite_completion", "react_exhaustion", "planner_action_illegal", "context_compaction"):
        v = rec.get(k) or (rec.get("dispositions") or {}).get(k)
        if v:
            disp[k] = disp.get(k, 0) + (len(v) if isinstance(v, list) else 1)
    contacts = rec.get("contact_count") or rec.get("contacts") or len(rec.get("contact_ids") or []) or None
    if isinstance(contacts, int):
        contacts_hist[contacts] = contacts_hist.get(contacts, 0) + 1
        if contacts > CEIL:
            over += 1
info["dispositions"] = disp; info["contacts_per_row_hist"] = dict(sorted(contacts_hist.items()))
if over:
    fails.append(f"{over} rows above the contact ceiling {CEIL}")

# cost and score job
gens = glob.glob(f"{D}/*.generation-manifest.json")
if gens:
    c = json.load(open(gens[0], encoding="utf-8")).get("cost") or {}
    info["cost"] = {k: c.get(k) for k in ("calls_used", "audio_seconds_used", "prompt_tokens_total", "completion_tokens_total", "tool_calls")}
    tool_calls_total = c.get("tool_calls") or 0
    if NOTOOL and tool_calls_total:
        fails.append(f"notool form recorded {tool_calls_total} tool calls")
sj = f"{D}/score-jobs.jsonl"
info["score_jobs"] = sum(1 for _ in open(sj, encoding="utf-8")) if os.path.exists(sj) else 0
if MODE == "arm" and info["score_jobs"] != 1:
    fails.append(f"score jobs {info['score_jobs']} (expected 1)")

# requests: tools key presence (notool must be absent/empty everywhere), fits
traces = glob.glob(f"{D}/*.trace.jsonl")
tools_present = 0; req_n = 0
if traces:
    with open(traces[0], encoding="utf-8") as fh:
        for line in fh:
            e = json.loads(line)
            if e.get("channel") != "MODEL_REQUEST":
                continue
            req_n += 1
            p = e.get("payload") or {}; inner = p.get("payload") if isinstance(p.get("payload"), dict) else p
            ts = inner.get("tool_schemas")
            if ts:
                tools_present += 1
info["requests"] = req_n; info["requests_with_tool_schemas"] = tools_present
if NOTOOL and tools_present:
    fails.append(f"notool form: {tools_present} requests carry tool_schemas")

for f in ("run-manifest", "scores", "outputs"):
    ps = glob.glob(f"{D}/*.{f}.json*")
    if ps:
        info[f"sha256_{f}"] = hashlib.sha256(open(ps[0], "rb").read()).hexdigest()

print(json.dumps({"mode": MODE, "run_id": RUN, "attempt_id": ATT, "pass": not fails, "fails": fails, **info}, default=str))
sys.exit(0 if not fails else 2)
