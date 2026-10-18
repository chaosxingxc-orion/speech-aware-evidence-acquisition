#!/usr/bin/env bash
# One-command launcher of the registered Solver reasoning diagnostic (owner ruling 330 A; package
# docs/readiness/2026-10-18-slurp-solver-reasoning-diagnostic-v1/). Run it from the study master AFTER the package is merged, its two ledger rows are
# countersigned by root, the R2 rec2 flight has sealed and the resident serving session is think-budget-np4.
#
#   bash scripts/flights/diag/solver_reasoning_diag.sh                 # re-issue the roster: 40 budget-3072 contacts, then the 16 budget-6144 contacts
#                                                                      # of the forced-both rows (per-slot sequential workers; ceiling 56 calls, < 1 GPU-h)
#   bash scripts/flights/diag/solver_reasoning_diag.sh --check-only    # every refusal below, no contact, exit 0 when the launch would proceed
#   bash scripts/flights/diag/solver_reasoning_diag.sh --render-only   # also build the transport and render every wire body, never POST
#
# REFUSES (exit 70) when:
#   * a generation flight process is alive or $DATA/locks/flight.lock exists (serving_lib.sh saea_flight_alive -- the precise detector of decision 163);
#   * a serving swap is pending;
#   * the ONE resident serving session is not the think-budget-np4 session (serving_lib.sh geometry table), or two sessions are resident;
#   * the diagnostic directory already holds an attempt (one attempt; supersede, never overwrite).
# It never starts, stops or swaps a server and never registers a scheduled task. The Python driver adds its own checks (ExecutionPlan, the exposure gate that
# demands the countersigned ledger row, the sealed-request hash proof) and writes statistics rows only; the reasoning bytes go to the data root.

set -euo pipefail

HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
# shellcheck source=../batch/serving_lib.sh
source "$REPO/scripts/flights/batch/serving_lib.sh"

RUN_ID=SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-V1
TARGET=think-budget-np4
MODE=run
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --check-only) MODE=check ;;
    *) ARGS+=("$arg") ;;
  esac
done

refuse() { echo "REFUSED (solver reasoning diagnostic): $*" >&2; exit 70; }

if reasons=$(saea_flight_alive); then
  refuse "a flight is in flight -- $(echo "$reasons" | tr '\n' ' ' | cut -c1-300)"
fi
if pending=$(saea_swap_pending); then
  refuse "a serving swap is pending -- $(echo "$pending" | tr '\n' ' ' | cut -c1-200)"
fi

saea_geometry "$TARGET" || refuse "unknown serving target $TARGET"
resident=()
if [ -d "$SAEA_DATA/serving" ]; then
  for dir in "$SAEA_DATA"/serving/*/; do
    [ -f "${dir}session.json" ] || continue
    [ -f "${dir}session-stop.json" ] && continue
    resident+=("$(basename "$dir")")
  done
fi
[ "${#resident[@]}" -eq 1 ] || refuse "expected exactly one resident serving session, found ${#resident[@]} (${resident[*]:-none})"
[ "${resident[0]}" = "$G_SID" ] || refuse "the resident serving session is ${resident[0]}, not $G_SID ($TARGET)"

if [ -e "$SAEA_DATA/diagnostics/$RUN_ID/results.jsonl" ] || [ -d "$SAEA_DATA/diagnostics/$RUN_ID/reasoning" ]; then
  refuse "the diagnostic directory $SAEA_DATA/diagnostics/$RUN_ID already holds an attempt"
fi

if [ "$MODE" = check ]; then
  echo "OK: no flight, no pending swap, resident session $G_SID, no previous attempt -- the launch would proceed"
  exit 0
fi

if [ -f "$HOME/.venvs/speechrl/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.venvs/speechrl/bin/activate"
fi
cd "$REPO"
exec python -B scripts/flights/diag/solver_reasoning_diag.py run \
  --data-root "$SAEA_DATA" --repo-root "$REPO" --runtime-root "$SAEA_RUNTIME_ROOT" "${ARGS[@]}"
