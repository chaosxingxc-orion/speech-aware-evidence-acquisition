#!/usr/bin/env python3
"""Two small, pure recovery rules the idle watchdog applies around ready-chain selection
(coordinator diagnosis, 2026-09-28 night: the resident llama-server died on a CUDA abort after
14.6 h resident, and the COMP-1 resume attempt then STOPped on a urllib3 ``RemoteDisconnected`` /
"Remote end closed connection" -- the SERVER was gone, not the experiment).

1. ``classify_stop`` -- a STOP is a SERVER-DEATH STOP only when its own text, or the log file its
   message references (``batch_driver.sh``'s own "...; see <path>" convention, e.g. "arm failed on
   step 1 ...; see /home/chao/batch-campaign-....log"), contains ``RemoteDisconnected`` or
   ``Remote end closed connection`` verbatim. No other STOP text ever qualifies: every other STOP
   is a real failure that needs a named root cause, never an automatic retry.
2. ``restart_needs_uptime`` -- true once a resident session's process has been up longer than
   ``max_uptime_seconds`` (default 12 h, the coordinator's bound: the server that died was up
   14.6 h). ``None`` elapsed time (no readable process) never forces a restart.

Both are side-effect free; ``idle_watchdog.sh`` resolves the STOP file, the referenced log file and
the resident process's elapsed time, and calls this module's CLI, which prints one plain
``true``/``false`` line (plus, for ``classify-stop``, the resolved log path on a second line) so the
shell need not parse JSON. Unit tests import the functions directly
(``tests/unit/test_idle_watchdog.py``).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

SERVER_DEATH_MARKERS = ("RemoteDisconnected", "Remote end closed connection")
DEFAULT_MAX_UPTIME_SECONDS = 12 * 3600.0

_SEE_LOG_RE = re.compile(r"see (\S+)")
_LOG_TAIL_LINES = 400


def extract_log_path(stop_text: str) -> Optional[str]:
    """``batch_driver.sh``'s STOP messages often end "...; see <path>" (its own log-pointer
    convention). Returns that path, with trailing punctuation stripped, or ``None`` when the STOP
    text names no log."""
    match = _SEE_LOG_RE.search(stop_text)
    if not match:
        return None
    return match.group(1).rstrip(").,;:")


def classify_stop(stop_text: str, log_text: str = "") -> bool:
    """True only when ``stop_text`` or ``log_text`` contains one of ``SERVER_DEATH_MARKERS``
    verbatim. An empty or unrelated STOP is never a server death."""
    haystack = f"{stop_text}\n{log_text}"
    return any(marker in haystack for marker in SERVER_DEATH_MARKERS)


def restart_needs_uptime(elapsed_seconds: Optional[float], max_uptime_seconds: float = DEFAULT_MAX_UPTIME_SECONDS) -> bool:
    """True once the resident geometry's server process has been up longer than
    ``max_uptime_seconds``. ``elapsed_seconds`` of ``None`` (no readable process, e.g. nothing is
    resident) never forces a restart: a missing fact is not evidence of an old server."""
    if elapsed_seconds is None:
        return False
    return elapsed_seconds > max_uptime_seconds


def _read_text(path: Optional[str]) -> str:
    if not path:
        return ""
    file_path = Path(path)
    if not file_path.is_file():
        return ""
    try:
        with file_path.open(encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return ""
    # The marker, when present, is near the traceback at the end of a (possibly large) campaign
    # log; only the tail is read.
    return "".join(lines[-_LOG_TAIL_LINES:])


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="mode", required=True)

    classify = sub.add_parser("classify-stop", help="is this STOP a SERVER-DEATH STOP?")
    classify.add_argument("--stop-file", required=True, help="path to batch-STOP")
    classify.add_argument("--log-file", default=None,
                           help="override the referenced log path instead of extracting it from the STOP text")

    uptime = sub.add_parser("uptime", help="has the resident geometry's server been up too long?")
    uptime.add_argument("--elapsed-seconds", type=float, default=None,
                         help="seconds the server process has been running (omit when nothing is readable)")
    uptime.add_argument("--max-uptime-seconds", type=float, default=DEFAULT_MAX_UPTIME_SECONDS)

    args = parser.parse_args(argv)

    if args.mode == "classify-stop":
        stop_path = Path(args.stop_file)
        stop_text = stop_path.read_text(encoding="utf-8", errors="replace") if stop_path.is_file() else ""
        log_path = args.log_file or extract_log_path(stop_text)
        log_text = _read_text(log_path)
        print("true" if classify_stop(stop_text, log_text) else "false")
        print(log_path or "")
        return 0

    if args.mode == "uptime":
        print("true" if restart_needs_uptime(args.elapsed_seconds, args.max_uptime_seconds) else "false")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
