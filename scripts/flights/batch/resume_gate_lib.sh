#!/bin/bash
# Resume-replay prelaunch gate scoping (coordinator, after the COMP-1 resume attempt 3 seal
# abort): EVERY resume launch must first pass scripts/flights/batch/resume_prelaunch_gate.sh, and
# an ORDINARY cell must never pay for or invoke it. Sourced by batch_driver.sh so the driver's
# prelaunch and the comp1 resume chain (which calls the gate directly, right before the driver)
# share one scoping rule instead of two copies drifting apart. Pure functions only -- sourcing
# this file has no side effect, so it is safe to source in tests with fake stand-ins for
# PY/stop/log.

# resume_gate_declared REPO EXPERIMENT CELL
# Prints "yes"/"no" on stdout: whether configs/experiment/<EXPERIMENT>.json declares resume_from
# for cell_id CELL. Prints "no" (never an error, never a non-zero exit) on any missing or
# malformed input, so this scoping check itself can never block or divert an ordinary chain.
resume_gate_declared() {
  local repo=$1 exp=$2 cell=$3
  "${PY:-python3}" -c '
import json, sys
try:
    doc = json.load(open(sys.argv[1]))
    for c in doc.get("cells") or []:
        if isinstance(c, dict) and c.get("cell_id") == sys.argv[2]:
            print("yes" if c.get("resume_from") else "no")
            sys.exit(0)
except Exception:
    pass
print("no")
' "$repo/configs/experiment/$exp.json" "$cell" 2>/dev/null
}

# resume_gate_run ORDER REPO DATA EXPERIMENT CELL GATE_SCRIPT REPORT_PATH
# A no-op (return 0, GATE_SCRIPT never invoked) unless EXPERIMENT:CELL declares resume_from. When
# it does, runs GATE_SCRIPT and calls the caller's own `stop` on a non-zero exit (naming the
# failing row / sealed-twice counts already printed by the gate) and the caller's own `log` on
# success. Must be sourced into a shell that already defines both `stop` and `log`
# (scripts/flights/batch/batch_driver.sh does, exactly like registration_gate).
resume_gate_run() {
  local order=$1 repo=$2 data=$3 exp=$4 cell=$5 gate=$6 report=$7
  local declared; declared=$(resume_gate_declared "$repo" "$exp" "$cell")
  [ "$declared" = "yes" ] || return 0
  [ -f "$gate" ] || stop "resume prelaunch gate missing: $gate"
  local out rc
  out=$(bash "$gate" --repo-root "$repo" --data-root "$data" --experiment "$exp" --cell "$cell" 2>&1)
  rc=$?
  printf '%s\n' "$out" > "$report"
  [ $rc -eq 0 ] || stop "resume replay gate REFUSED step $order (exit $rc): $(printf '%s\n' "$out" | tail -8 | tr '\n' ';' | cut -c1-800); full report $report"
  log "resume-replay-gate-ok" "{\"step\":$order}"
}
