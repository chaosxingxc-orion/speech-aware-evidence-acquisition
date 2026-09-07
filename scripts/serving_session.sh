#!/usr/bin/env bash
#
# The coordinator's always-on serving session (owner rule, 2026-09-07: the
# model may stay always on provided monitoring numbers come back, so GPU time
# is reused across agents instead of being paid for again by every flight).
#
#   scripts/serving_session.sh start <model-fragment-id> [--session-id ID] \
#                                    [--host H] [--port N] [--runtime-root R]
#   scripts/serving_session.sh status [--session-id ID]
#   scripts/serving_session.sh stop   [--session-id ID]
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
# `start` refuses when a session.json without a session-stop.json is already
# recorded, or when anything is already listening on the port. Both refusals
# are enforced in core.session.serving, not here, so a caller that reaches the
# module directly gets them too.
#
# Agents never run `start` or `stop`. A flight attaches automatically:
# core.flight.FlightRuntime.serve finds the resident session, compares the
# identity fields session.json records, and refuses with the exact differing
# field rather than spawning a second 18.5 GB server.
#
# See docs/readiness/2026-09-07-always-on-serving-operating-note.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
    sed -n '2,39p' "${BASH_SOURCE[0]}" | sed 's/^#\{1,2\} \{0,1\}//'
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
    start|status|stop) ;;
    *)
        echo "serving_session.sh: unknown command '$1' (expected start|status|stop)" >&2
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
