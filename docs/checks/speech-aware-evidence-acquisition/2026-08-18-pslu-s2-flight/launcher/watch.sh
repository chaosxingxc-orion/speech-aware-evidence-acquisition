#!/usr/bin/env bash
# Operational-health watch for the Stage-2 flight log.
# Emits: phase markers, every 30th request, ALL failure signatures, terminal lines.
# Never emits response content (the launcher only logs char counts anyway).
LOG=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslus2fly/flight.log

while [ ! -f "$LOG" ]; do sleep 2; done

tail -n +1 -f "$LOG" | awk '
  /FLIGHT START/                    { print; fflush(); next }
  /FLIGHT ABORTED/                  { print; fflush(); next }
  /FAILED after/                    { print; fflush(); next }
  /Traceback|Error:|error:|refus|escape|divergence|Killed|OOM|Cannot|denied|closed|timeout|Timeout/ { print; fflush(); next }
  /session up|silence-swap registered|FrozenCoreClient constructed|model file:/ { print; fflush(); next }
  /outputs.jsonl written|trace_manifest_hash|^\[.*\] cost:|^\[.*\] requests:|^\[.*\] wall:|flight receipt/ { print; fflush(); next }
  /^exit:/                          { print; fflush(); exit }
  / req 0*([0-9]*[0369]0) ok /      { print; fflush(); next }
'
