from pathlib import Path
import json
REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
from speech_aware_evidence_acquisition.contracts.ledger import (
    _CARRIER_CELL_TOKEN_SPLIT, _EXPOSURE_CARRIER_COLUMN, _EXPOSURE_RUN_COLUMN, _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
rows = _parse_ledger_tables((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8"))
print("total ledger rows parsed:", len(rows))
m = [r for r in rows if r.get(_EXPOSURE_RUN_COLUMN) == "SAEA-BASE-a2t-a0-400"]
print("matched:", len(m))
row = m[0]
print("columns:", len(row))
for c in ("date","execution profile","split role","split identity hash","consumed","calls","speech audio seconds","gpu hours"):
    print(f"  {c!r} = {row.get(c)!r}")
lock = load_lock(umbrella_lock_path())
known = {e["name"] for k in ("datasets","asset_catalog") for e in lock.get(k, []) if isinstance(e, dict) and e.get("kind") == "dataset"}
cell = row[_EXPOSURE_CARRIER_COLUMN]
tokens = [t for t in _CARRIER_CELL_TOKEN_SPLIT.split(cell) if t]
named = [t for t in tokens if t in known]
print("carrier cell tokens matching known dataset keys:", named)
assert named == ["audio2tool"], named
print("CARRIER CELL OK")
