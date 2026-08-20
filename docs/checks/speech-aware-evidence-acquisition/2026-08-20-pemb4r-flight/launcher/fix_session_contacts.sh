#!/usr/bin/env bash
# CORRECTION. stage_cdecode's teardown block recorded the q4km-core session's
# contact count from a HARDCODED expectation (QUERY_N + 1 = 61) instead of the
# proxy's own measured `flown`. C-DECODE never issued a single request, so 61 is
# false and directly contradicts every other zero-contact fact in this receipt.
# This script sets it to the measured truth (0), records the correction in the
# receipt itself, and leaves an explicit note. Model-free, zero contact.
# Usage: fix_session_contacts.sh <attempt_id>
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

if pgrep -f "python .*launch_pemb4r" >/dev/null; then
  echo "REFUSING: a launcher stage is in flight"; exit 2
fi

python - "$1" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, ".")
from speech_aware_evidence_acquisition.data.lock import data_root
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F

attempt = sys.argv[1]
root = data_root()
run_dir = root / "runs" / F.PROBE_ID / attempt

CORRECTION = {
    "field": "sessions[server_key='q4km-core'].contacts",
    "recorded_value": 61,
    "corrected_value": 0,
    "reason": (
        "The cdecode stage's teardown block passed extra={'contacts': QUERY_N + 1} -- a HARDCODED "
        "expectation of the full C-DECODE pass plus its determinism resend -- rather than the "
        "proxy's own measured `flown`, and that teardown runs in a `finally`, so the value was "
        "written even though the stage refused at FrozenCoreClient construction and issued ZERO "
        "requests. Corrected to the measured truth. Independently corroborated by "
        "session-q4km-core.server.log, which carries 0 'POST /v1/chat/completions' lines, and by "
        "the absence of c-decode-responses.jsonl / c-decode-outputs.jsonl."
    ),
    "corrected_at": datetime.now(timezone.utc).isoformat(),
    "scope": "recorded METADATA only -- no contact, vector, hash, budget total or durable spend is "
             "touched; the durable attempt store never counted these 61 (actual calls stay 4031).",
}

for name in ("flight-state.json", "flight-receipt.json"):
    path = run_dir / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for session in doc.get("sessions", []):
        if session.get("server_key") == "q4km-core" and session.get("contacts") != 0:
            session["contacts"] = 0
            session["contacts_note"] = (
                "ZERO requests were issued on this session: the stage refused at FrozenCoreClient "
                "construction, before any request could be built. See `corrections` and section 6 "
                "of the archived README."
            )
            changed += 1
    corrections = list(doc.get("corrections") or [])
    if not any(c.get("field") == CORRECTION["field"] for c in corrections):
        corrections.append(CORRECTION)
    doc["corrections"] = corrections
    path.write_text(json.dumps(doc, indent=2, sort_keys=True, default=str), encoding="utf-8", newline="\n")
    print(f"{name}: {changed} session record(s) corrected, corrections block carries {len(corrections)} entry(ies)")

doc = json.loads((run_dir / "flight-receipt.json").read_text(encoding="utf-8"))
print("sessions now:", [(s["server_key"], s["contacts"]) for s in doc["sessions"]])
print("sum of session contacts:", sum(s["contacts"] for s in doc["sessions"]), "vs durable calls:", doc["durable_actual"]["calls"])
PY
