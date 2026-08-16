#!/usr/bin/env bash
# Stream P2-resume arm-level milestones from the detached sequence log.
# Emits arm starts, arm exits (rc + elapsed), refusals, failure tails, and the
# terminal sequence line; exits when the sequence finishes.
set -uo pipefail
LOG=/home/chao/p2-rladder-detached-20260816T105824Z.log
tail -n +1 -F "$LOG" 2>/dev/null | awk '
  /^=====/            { print; fflush(); }
  /exit=/             { print; fflush(); }
  /arm failed/        { print; fflush(); }
  /TWO ARMS FAILED/   { print; fflush(); }
  /REFUSED|REFUSE:/   { print; fflush(); }
  /Traceback|Error|FAILED|Killed|OOM/ { print; fflush(); }
  /sequence done/     { exit; }
'
