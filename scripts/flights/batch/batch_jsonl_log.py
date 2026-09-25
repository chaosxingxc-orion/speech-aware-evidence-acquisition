#!/usr/bin/env python3
"""Serialize one unattended batch event as one JSONL line."""

from datetime import datetime, timezone
import json
import sys


def event_line(event: str, raw_detail: str, *, force_text: bool = False) -> str:
    if force_text:
        detail = raw_detail
    else:
        try:
            detail = json.loads(raw_detail)
        except json.JSONDecodeError:
            detail = raw_detail
    return json.dumps({
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event,
        "detail": detail,
    }, ensure_ascii=True, separators=(",", ":"))


def main() -> int:
    if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != "--text"):
        print("usage: batch_jsonl_log.py EVENT DETAIL [--text]", file=sys.stderr)
        return 2
    print(event_line(sys.argv[1], sys.argv[2], force_text=len(sys.argv) == 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
