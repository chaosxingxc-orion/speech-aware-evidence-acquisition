#!/usr/bin/env bash
#
# The coordinator's always-on serving session (owner rule, 2026-09-07: the
# model may stay always on provided monitoring numbers come back, so GPU time
# is reused across agents instead of being paid for again by every flight).
#
#   scripts/serving_session.sh start <model-fragment-id> [--session-id ID] \
#                                    [--host H] [--port N] [--runtime-root R] \
#                                    [--min-host-free-gb 12.0]
#   scripts/serving_session.sh status [--session-id ID]
#   scripts/serving_session.sh resident            (exit 0 = one is resident,
#                                                   3 = none, 2 = cannot tell)
#   scripts/serving_session.sh stop   [--session-id ID] [--stale]
#   scripts/serving_session.sh host-memory [--min-host-free-gb 12.0] \
#                                    [--margin-gb 0.0]  (exit 0 = start would
#                                                   pass its host guard, or the
#                                                   reading is unavailable;
#                                                   4 = the reading proves it
#                                                   would refuse)
#
# `start` launches ONE llama-server for that fragment's geometry, built by
# exactly the argument builder a flight uses (core.session.build_server_command
# over core.session.serving.merge_server_args -- never a second dialect),
# records $SPEECHRL_DATA_DIR/serving/<session-id>/session.json (fragment id and
# hash, runtime receipt, binary/model/mmproj sha256, full command line, host,
# port, pid, started_at, GET /props snapshot), and then STAYS IN THE
# FOREGROUND. That is not a convenience: a detached WSL job dies with the shell
# that spawned it, so the resident server must be owned by a live wrapper THE
# COORDINATOR runs, never by an agent's transient session. Run it as a
# background live wrapper:
#
#   bash scripts/serving_session.sh start q4km-hbmfree-np16 > serving.log 2>&1 &
#
# and stop it with `scripts/serving_session.sh stop` (or by signalling the
# wrapper; either path writes session-stop.json).
#
# The wrapper OWNS the server process, so it reaps it: when llama-server exits
# on its own, `start` writes session-stop.json with the reaped exit status,
# prints one line to stderr and exits 1 (0 only when the operator asked it to
# stop). There is deliberately no --restart-on-exit: an unrequested exit is a
# fact the coordinator has to see.
#
# `start` refuses when a session.json without a session-stop.json is already
# recorded, or when anything is already listening on the port. Both refusals
# are enforced in core.session.serving, not here, so a caller that reaches the
# module directly gets them too. A session whose server is already gone or
# <defunct> is recorded stopped with `stop --stale` (taken automatically by a
# plain `stop`), which refuses unless the pid, the port and the card all agree
# there is nothing left.
#
# Agents never run `start` or `stop`. A flight attaches automatically:
# core.flight.FlightRuntime.serve finds the resident session, compares the
# identity fields session.json records, and refuses with the exact differing
# field rather than spawning a second 18.5 GB server.
#
# `start` also refuses when the WINDOWS host's free memory is below
# --min-host-free-gb (default 12.0), printing the reading in the refusal (E7c,
# 2026-09-07: the VM's mmap plus page cache filled the host's headroom and the
# Claude Code host watchdog killed the serving wrapper and its llama-server
# child mid-flight -- a serving wrapper is a host-watchdog target, so the
# running cap must always leave that much for Windows). `status` prints the
# CURRENT host reading (Windows total/free GB, the vmmemWSL working set, and
# the VM's own MemTotal/MemAvailable) beside the session document. Both are
# enforced in core.session.serving (core.session.serving.read_host_memory),
# not here.
#
# See docs/readiness/2026-09-07-always-on-serving-operating-note.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
    sed -n '2,67p' "${BASH_SOURCE[0]}" | sed 's/^#\{1,2\} \{0,1\}//'
}

if [[ $# -lt 1 ]]; then
    usage >&2
    exit 2
fi

case "$1" in
    -h|--help|help)
        usage
        exit 0
        ;;
    start|status|stop|resident|host-memory) ;;
    *)
        echo "serving_session.sh: unknown command '$1' (expected start|status|stop|resident|host-memory)" >&2
        exit 2
        ;;
esac

if [[ -z "${SPEECHRL_DATA_DIR:-}" ]]; then
    echo "serving_session.sh: SPEECHRL_DATA_DIR is not set; the serving session record" \
         "lives under \$SPEECHRL_DATA_DIR/serving/" >&2
    exit 2
fi

# The shared WSL environment, never a per-clone install: an editable install
# from a worktree repoints the shared venv for every other agent. PYTHONPATH is
# the armour that makes THIS checkout the one that is imported regardless.
VENV="${SAEA_VENV:-${HOME}/.venvs/speechrl}"
if [[ -f "${VENV}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${VENV}/bin/activate"
fi

# __pycache__ under the frozen scoring package closes the D3 gate; never let
# this process be the one that plants it.
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export SAEA_REPO_ROOT="${REPO_ROOT}"

exec python -m speech_aware_evidence_acquisition.core.session.serving "$@"
