#!/usr/bin/env python3
"""CLI: price the EVO-S1 stage-one gate at each candidate fold size (MODEL-FREE).

Exposure row ``SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V2``. The re-draw from 30 to
60 utterances per scenario was ordered to buy stage-one power, and the number
of scenarios that power buys is the justification for about 3.35 extra planned
GPU-hours -- so it is computed here from a committed receipt rather than
asserted in prose. The only input is the KC-S1b DEV-1000 read
(``read.json``), already committed and already read; no new surface is opened
and no contact of any kind is made.

Run in WSL2 (no data root needed -- this reads one committed JSON receipt)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_evo_stage_one_power.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (  # noqa: E402
    ADMISSION_GATES,
    FOLD_QUOTA,
    FOLD_QUOTA_V2,
    KC_S1B_CONTRAST,
    KC_S1B_POPULATION,
    KC_S1B_READ_RECEIPT,
    REWARD_METRIC,
    exposure_row_id,
    stage_one_power,
    stage_one_power_summary,
)

CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power"
)
SCALING_RULE = (
    "A scenario's measured saves and harms become per-row rates on the "
    "population they were measured on, are multiplied by the fold size and "
    "are compared against the gate's own absolute constants without "
    "rounding. Stated because the answer is sensitive to it: rounding the "
    "expected counts admits datetime at 60, and scaling the harms bound with "
    "the fold admits transport, so a careless reading reports nine where the "
    "preregistered gate gives seven."
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rows", type=int, nargs="+", default=[FOLD_QUOTA, FOLD_QUOTA_V2]
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    read_path = REPO_ROOT / KC_S1B_READ_RECEIPT
    read_doc = json.loads(read_path.read_text(encoding="utf-8"))
    contrast = read_doc[KC_S1B_CONTRAST][KC_S1B_POPULATION][REWARD_METRIC]
    per_stratum = contrast["per_stratum"]

    sizes: dict[str, object] = {}
    for rows in args.rows:
        table = stage_one_power(per_stratum, rows)
        sizes[str(rows)] = {
            **stage_one_power_summary(table),
            "rows_per_scenario": rows,
            "per_scenario": table,
        }

    receipt = {
        "schema": "saea-slurp-evo-stage-one-power-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": exposure_row_id("V2"),
        "contacts": {
            "model": 0,
            "gpu": 0,
            "network": 0,
            "tokenizer": 0,
            "scorer": 0,
            "audio_decode": 0,
        },
        "source": {
            "relpath": KC_S1B_READ_RECEIPT,
            "file_sha256": _sha256_file(read_path),
            "contrast": KC_S1B_CONTRAST,
            "population": KC_S1B_POPULATION,
            "metric": REWARD_METRIC,
            "pooled_saves": contrast["saves"],
            "pooled_harms": contrast["harms"],
            "pooled_delta": contrast["delta"],
            "n": contrast["n"],
        },
        "gates": dict(ADMISSION_GATES),
        "scaling_rule": SCALING_RULE,
        "generator": "scripts/build_slurp_evo_stage_one_power.py",
        "fold_sizes": sizes,
    }

    payload = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        out = REPO_ROOT / CHECK_DIR / "power.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        print(f"wrote {CHECK_DIR}/power.json  sha256={_sha256_file(out)}")
    for rows in args.rows:
        entry = sizes[str(rows)]
        print(
            f"rows={rows}: {entry['clears']} of {entry['scenarios']} clear "
            f"-- {', '.join(entry['clearing_scenarios'])}"  # type: ignore[arg-type]
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
