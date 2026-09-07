#!/usr/bin/env python3
"""Cut the 44 Earnings-21 calls into SPEAKER-TURN UNITS and write the unit plan.

Exposure row `SAEA-E21-MF-SPEAKER-TURN-UNITS-V1` (`model-free-check`), registered
and committed before the first slice was read. Zero frozen-core, diarizer, GPU,
embedder, tokenizer, network and paid-API contacts; no MP3 decode and no resample,
so `ffmpeg` stays absent. The only audio touch is a local PCM read of already-sealed
slice WAVs whose samples become 20 ms frame energies and are then thrown away.
Reference TEXT is never opened: per-unit reference-word counts are interpolated
from the per-window reference-word COUNTS of the sealed window-pairing rows.

Writes `docs/receipts/obs/e21-speaker-turn-units-v1.json` (units, not audio) and
`<out-dir>/unit-plan-summary.json`; `README.md` is written by hand beside it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import e21_speaker_turn_units as stu  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.diarization import (  # noqa: E402
    load_diarization,
)

BASELINE_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
BASELINE_ATTEMPT = "attempt-20260904T233816Z-bcd338"
DEFAULT_PLAN = REPO_ROOT / "docs/receipts/obs/e21-speaker-turn-units-v1.json"


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", ""), type=Path)
    parser.add_argument("--diarization", required=True, type=Path)
    parser.add_argument("--window-rows", required=True, type=Path)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    if not args.data_root or not Path(args.data_root).is_dir():
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) must name the data root")
    data_root, started = Path(args.data_root), time.time()

    artifact = load_diarization(args.diarization)
    rows_document = json.loads(Path(args.window_rows).read_text(encoding="utf-8"))
    rows_by_call: dict[str, list[dict]] = {}
    for row in rows_document["rows"]:
        rows_by_call.setdefault(str(row["sample_id"]), []).append(row)

    calls: list[dict] = []
    summaries: list[dict] = []
    for sample_id in sorted(artifact.calls):
        derivation = json.loads(
            (
                data_root / "runs" / BASELINE_RUN / BASELINE_ATTEMPT
                / f"{BASELINE_RUN}.obs-derivation.{sample_id}.json"
            ).read_text(encoding="utf-8")
        )
        duration = float(derivation["decoded_duration_seconds"])
        window_count = len(derivation["slices"])
        active, frame_seconds = stu.activity_from_sealed_slices(data_root, derivation["slices"])
        pauses = stu.pauses_from_activity(active, frame_seconds)
        units = stu.plan_units(
            sample_id,
            artifact.calls[sample_id].segments,
            duration,
            pauses,
            active,
            frame_seconds,
        )
        window_rows = rows_by_call[sample_id]
        if len(window_rows) != window_count:
            raise SystemExit(
                f"call {sample_id}: {len(window_rows)} sealed rows, {window_count} slices"
            )
        ranges = stu.reference_word_partition(units, window_rows)
        summary = stu.call_summary(sample_id, units, duration, window_count, ranges)
        summary["pauses"] = len(pauses)
        summaries.append(summary)
        calls.append(
            {
                "sample_id": sample_id,
                "decoded_duration_seconds": round(duration, 6),
                "windows": window_count,
                "units": [
                    dict(unit.as_dict(), reference_word_range=[low, high])
                    for unit, (low, high) in zip(units, ranges)
                ],
            }
        )
        print(f"{sample_id}: {len(units)} units, {window_count} windows", flush=True)

    pooled = stu.corpus_summary(summaries)
    _write(
        args.plan_out,
        stu.plan_document(
            carrier_lock_key=artifact.carrier_lock_key,
            split_identity_hash=rows_document["split_identity_hash"],
            source_run_id=BASELINE_RUN,
            source_attempt_id=BASELINE_ATTEMPT,
            diarization_run_id=artifact.run_id,
            window_rows_sha256=hashlib.sha256(Path(args.window_rows).read_bytes()).hexdigest(),
            calls=calls,
            corpus=pooled,
        ),
    )
    _write(
        args.out_dir / "unit-plan-summary.json",
        stu.summary_document(
            plan_path=str(args.plan_out.relative_to(REPO_ROOT)).replace("\\", "/"),
            plan_sha256=hashlib.sha256(args.plan_out.read_bytes()).hexdigest(),
            elapsed_seconds=time.time() - started,
            corpus=pooled,
            per_call=summaries,
        ),
    )
    print(json.dumps(pooled, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
