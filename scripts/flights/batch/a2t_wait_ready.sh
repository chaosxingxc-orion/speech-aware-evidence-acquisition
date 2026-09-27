#!/bin/bash
# Readiness wait for the resident Audio2Tool np3 session: a thin caller of serving_wait_ready.sh (owner decision 163). Exit 0
# only when the session is READY (fresh session.json, no stop record, /health ok, /props geometry equal to the
# fragment, a fresh monitor sample); 2 timeout, 3 stopped early, 4 wrong geometry. Options pass through
# (--since EPOCH, --timeout SEC, --poll SEC).
exec bash "$(dirname "${BASH_SOURCE[0]}")/serving_wait_ready.sh" a2t-np3 "$@"
