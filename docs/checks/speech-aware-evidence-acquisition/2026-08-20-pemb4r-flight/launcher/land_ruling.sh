#!/usr/bin/env bash
# Land the coordinator's pre-contact ruling into this attempt's flight state,
# VERBATIM and timestamped, BEFORE any C-DECODE generation contact exists.
# Run with NO launcher stage in flight, so nothing can overwrite it.
# Usage: land_ruling.sh <attempt_id>
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

if pgrep -f "python .*launch_pemb4r" >/dev/null; then
  echo "REFUSING: a launcher stage is in flight; it would overwrite flight-state.json"; exit 2
fi

python - "$1" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, ".")
import flight_identity as fid
import launch_pemb4r_flight as L
from speech_aware_evidence_acquisition.data.lock import data_root

attempt = sys.argv[1]
root = data_root()
run_dir = root / "runs" / fid.run_id() / attempt
state = L.FlightState(run_dir / "flight-state.json")

if "c_decode" in state.document:
    raise SystemExit("REFUSING: C-DECODE has already run for this attempt -- the ruling would not precede it")

existing = state.document.get(fid.COORDINATOR_PRE_CONTACT_RULING_KEY)
if existing:
    print("already recorded at", existing.get("recorded_at"))
else:
    state.put(
        fid.COORDINATOR_PRE_CONTACT_RULING_KEY,
        {
            "text": fid.COORDINATOR_PRE_CONTACT_RULING,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "issued_by": "coordinator",
            "issued_during_stage": "post-lco7, pre-qw -- ZERO C-DECODE generation contacts existed",
            "durable_spend_at_recording": None,
            "verbatim": True,
            "note": (
                "Recorded VERBATIM at the coordinator's instruction. The cdecode stage refuses "
                "fail-closed unless this block is present and matches verbatim, so its presence in "
                "the flight receipt is the flight-side record that the ruling preceded every "
                "generation contact. The coordinator lands the matching registration amendment "
                "pre-read if budget_forced fires."
            ),
        },
    )
    print("recorded")

block = state.document[fid.COORDINATOR_PRE_CONTACT_RULING_KEY]
print(json.dumps(block, indent=2, sort_keys=True))
print("verbatim match:", block["text"] == fid.COORDINATOR_PRE_CONTACT_RULING)
print("c_decode present in state:", "c_decode" in state.document)
PY
