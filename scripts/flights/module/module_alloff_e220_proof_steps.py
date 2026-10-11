#!/usr/bin/env python3
"""Model-free proof steps for the HELD Earnings-22 all-off cells (``module_alloff_e220_proof.sh`` drives them).

Each step builds the cell's ``FlightRuntime`` (compose + adapter + gate construction; no process start) and runs ONE
read-only action; a refusal is the expected answer where packets or a snapshot are missing, and is printed with the
code location that raised it (the first contact-requiring step). It writes nothing itself; the wire-check step writes only
under ``$SPEECHRL_DATA_DIR/wire-check`` and ``attempts``, which is why the shell wrapper runs it on an overlay.

    python -B scripts/flights/module/module_alloff_e220_proof_steps.py <cell> units|snapshot|wire
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime  # noqa: E402

LOCK = Path(os.environ.get("SAEA_DATASETS_LOCK", "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"))


def main(argv: list[str]) -> int:
    cell, step = argv[0], (argv[1] if len(argv) > 1 else "wire")
    data = Path(os.environ["SPEECHRL_DATA_DIR"])
    doc = json.loads((REPO_ROOT / "configs" / "experiment" / f"{cell}.json").read_text(encoding="utf-8"))["cells"][0]
    runtime = build_flight_runtime(
        REPO_ROOT, data, model=doc["model_fragment"], dataset=doc["dataset_fragment"], baseline=doc["baseline_fragment"],
        experiment=cell, run_id=doc["run_id"], attempt_id=doc["attempt_id"], runtime_root=Path("/home/chao"), lock_path=LOCK,
    )
    print("COMPOSE+BUILD ok", cell)
    try:
        if step == "snapshot":
            runtime._prepare()
            runtime._load_knowledge_snapshot()
            print("SNAPSHOT ok")
        elif step == "units":
            runtime._prepare()
            roster = runtime._source_execution_unit_roster()
            print("UNITS ok", len(roster.units))
        elif step == "wire":
            result = runtime.wire_check(seal_and_score=False)
            print("WIRE ok", json.dumps({k: result[k] for k in ("model_contacts", "attempt_aborted") if k in result}))
        else:
            raise SystemExit(f"unknown step {step!r}")
    except Exception as error:  # noqa: BLE001 - the refusal IS the report
        frames = traceback.extract_tb(error.__traceback__)
        print("REFUSED", type(error).__name__, str(error).splitlines()[0][:300])
        print("AT", [f"{Path(f.filename).name}:{f.lineno}:{f.name}" for f in frames[-3:]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
