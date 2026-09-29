# Shared helpers for every scripts/flights/*/*_read.sh driver. Source it -- never execute it
# directly -- after PY and MAIN are already set (every *_read.sh driver sets both near the top,
# before it sources this file):
#
#   PY=/home/chao/.venvs/speechrl/bin/python
#   MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
#   source "$MAIN/scripts/flights/batch/read_lib.sh"
#
# Both functions below only shell out to $PY over local files; neither makes a model, server, GPU
# or network contact.

# read_require_countersigned <ledger-relpath-or-abspath> <read-row-id>
#
# Loads scripts/checks/flight_registration_check.py BY FILE PATH (it sits under scripts/checks/,
# not the installed package, so nothing ever `import`s it by name) and refuses -- prints one
# REFUSED message on stderr and returns non-zero -- unless <read-row-id> has at least one row in
# the ledger and one of those rows is root countersigned. On success it prints one confirmation
# line on stdout and returns 0.
#
# Registers the loaded module in sys.modules BEFORE exec_module. The gate's @dataclass rows
# (Finding, CellReport) resolve their OWN module through sys.modules while their class bodies are
# evaluated during exec_module; skipping this step leaves sys.modules[spec.name] absent, so the
# dataclass machinery raises AttributeError ("'NoneType' object has no attribute '__dict__'")
# before the gate does any work at all -- the driver exits before anything is opened, with no
# ledger read and no REFUSED message: a false negative that looks like a crash, not a refusal.
# Fixed for scripts/flights/wsv1/wsv1_read.sh by commit e3799ad3; every other *_read.sh that
# loaded this gate the same way carried the identical one-line bug until this file replaced the
# inlined copies (2026-09-29 read-agent follow-up).
read_require_countersigned() {
  local ledger="$1" read_run="$2"
  "$PY" -B - "$MAIN" "$ledger" "$read_run" <<'PY'
import importlib.util
import sys
from pathlib import Path

repo, ledger, read_run = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
spec = importlib.util.spec_from_file_location("frc", repo / "scripts/checks/flight_registration_check.py")
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate  # dataclasses resolve the module through sys.modules
spec.loader.exec_module(gate)
rows = gate.parse_ledger(repo, ledger).get(read_run, [])
if not rows:
    sys.exit(f"REFUSED: the READ row {read_run} is not in the exposure ledger")
if not any(gate.is_countersigned(row) for row in rows):
    sys.exit(f"REFUSED: the READ row {read_run} is not root countersigned")
print(f"READ row {read_run} countersigned")
PY
}

# read_scoring_done <receipt-path> <expected-schema>
#
# True (exit 0) when <receipt-path> exists, parses as JSON, and its top-level "schema" field
# equals <expected-schema>; false (exit 1) on a missing, unreadable, malformed, or wrong-schema
# file (a receipt left by a different --mode, or a stale schema version, never counts as "already
# scored").
#
# A caller gates its (expensive -- one complete official scoring subprocess per rendered column)
# column-scoring step on:
#
#   if [ "$RESCORE" = 1 ] || ! read_scoring_done "$RECEIPT" "$SCHEMA"; then
#     ...run the scorer, writing $RECEIPT...
#   fi
#
# so a retry after a LATER stage fails (e.g. the paired read, run after the columns are already
# scored) does not re-score columns it already scored; a driver's own --rescore flag sets
# RESCORE=1 to force it anyway.
read_scoring_done() {
  local receipt="$1" schema="$2"
  [ -f "$receipt" ] || return 1
  "$PY" -B - "$receipt" "$schema" <<'PY'
import json
import sys
from pathlib import Path

receipt, schema = Path(sys.argv[1]), sys.argv[2]
try:
    payload = json.loads(receipt.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError):
    sys.exit(1)
sys.exit(0 if isinstance(payload, dict) and payload.get("schema") == schema else 1)
PY
}
