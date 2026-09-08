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

`--schema-version v2` (default `v1`, unchanged in every other respect) builds the
coordinator's 2026-09-08 plan instead: same sealed diarization and window-row
inputs, `analysis.e21_speaker_turn_units.plan_units_v2` in place of `plan_units`,
exposure row `SAEA-E21-MF-SPEAKER-TURN-UNITS-V2`, and
`docs/receipts/obs/e21-speaker-turn-units-v2.json` as the default plan path. The
v1 code path (the default) is untouched by this flag.

`--schema-version v3` (OBS-E1b, exposure row `SAEA-E21-MF-SPEAKER-TURN-UNITS-V3`)
takes a DIFFERENT input and no audio at all: `--from-plan` names an already
committed v2 plan, `--from-plan-sha256` pins its bytes, and this build re-reads
that file, keeps every TURN byte for byte, and adds each unit's delivered-context
bounds through `analysis.e21_speaker_turn_units.add_context`. No diarization
artifact, no window rows and no sealed slice is opened on this path -- the turns
were cut from them once, and v3 does not re-cut them.
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


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def _uniform_units(sample_id: str, duration: float, seconds: float) -> list[dict]:
    """``ceil(duration / seconds)`` equal clock units, in the shape a plan
    block carries. The last one absorbs the remainder, exactly as the fixed
    window cutter's last window does."""

    import math

    count = max(1, math.ceil(duration / seconds))
    units: list[dict] = []
    for index in range(1, count + 1):
        start = min(duration, (index - 1) * seconds)
        end = duration if index == count else min(duration, index * seconds)
        units.append(
            {
                "unit_id": stu.unit_id(sample_id, index),
                "sample_id": sample_id,
                "unit_index": index,
                "start_seconds": round(start, 6),
                "end_seconds": round(end, 6),
                "duration_seconds": round(end - start, 6),
                "speaker": None,
                "speaker_share": 0.0,
                "speaker_count": 0,
                "start_cut": stu.CUT_CALL_START if index == 1 else "clock",
                "end_cut": stu.CUT_CALL_END if index == count else "clock",
                "ends_on_active_frame": False,
                "flags": ["uniform-clock-unit"],
                "absorbed_units": [],
            }
        )
    return units


def _build_v3(args, plan_out: Path) -> int:
    """v3: the committed v2 plan, re-read at its pin, with context bounds."""

    source = Path(args.from_plan)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if args.from_plan_sha256 and digest != args.from_plan_sha256:
        raise SystemExit(
            f"{source} hashes to {digest}, not the pinned {args.from_plan_sha256}"
        )
    document = json.loads(raw.decode("utf-8"))
    if document.get("schema") != stu.PLAN_SCHEMA_V2:
        raise SystemExit(
            f"--from-plan must be a {stu.PLAN_SCHEMA_V2} plan, got {document.get('schema')!r}"
        )
    started = time.time()
    calls: list[dict] = []
    summaries: list[dict] = []
    for block in document["calls"]:
        sample_id = str(block["sample_id"])
        duration = float(block["decoded_duration_seconds"])
        inherited = [dict(entry) for entry in block["units"]]
        if args.uniform_seconds:
            # The OBS-E1b FORM TWIN. Same call, same context rule, same
            # ownership stitch, same delivered seconds -- the ONE thing that
            # moves is where the boundaries are: the clock instead of the
            # diarized speaker turns. The turns it inherits are replaced by
            # equal clock units of ``--uniform-seconds``, so nothing about
            # this call's audio, duration or identity changes.
            inherited = _uniform_units(sample_id, duration, float(args.uniform_seconds))
        units = stu.add_context(
            [
                stu.UnitV2(
                    sample_id=sample_id,
                    unit_index=int(entry["unit_index"]),
                    start_seconds=float(entry["start_seconds"]),
                    end_seconds=float(entry["end_seconds"]),
                    speaker=entry["speaker"],
                    speaker_share=float(entry["speaker_share"]),
                    speaker_count=int(entry["speaker_count"]),
                    start_cut=str(entry["start_cut"]),
                    end_cut=str(entry["end_cut"]),
                    ends_active=bool(entry["ends_on_active_frame"]),
                    flags=tuple(entry.get("flags") or ()),
                    absorbed_units=tuple(
                        dict(item) for item in entry.get("absorbed_units") or ()
                    ),
                )
                for entry in inherited
            ],
            duration,
            margin=float(args.context_margin_seconds),
            min_delivered=float(args.min_delivered_seconds),
        )
        # The twin's units are new, so they carry no reference-word range: the
        # sealed per-window counts were partitioned over the SPEAKER turns and
        # re-interpolating them onto clock units would invent an attribution
        # nothing measured. The plan loader never reads the field, and the
        # twin's own verdict reads reference words from the scorer.
        ranges = (
            None
            if args.uniform_seconds
            else [tuple(entry["reference_word_range"]) for entry in inherited]
        )
        summary = stu.call_summary(
            sample_id, units, duration, int(block["windows"]), ranges
        )
        summaries.append(summary)
        emitted = (
            [unit.as_dict() for unit in units]
            if ranges is None
            else [
                dict(unit.as_dict(), reference_word_range=[low, high])
                for unit, (low, high) in zip(units, ranges)
            ]
        )
        identity_keys = (
            "speaker",
            "speaker_count",
            "start_cut",
            "end_cut",
            "ends_on_active_frame",
            "unit_id",
            "unit_index",
            "flags",
            "absorbed_units",
        ) + (() if ranges is None else ("reference_word_range",))
        for before, after in zip(inherited, emitted):
            # Exact for identity and structure; 1e-6 for the seconds, because
            # a v2 file stores each field rounded to six places and
            # ``end - start`` recomputed from those rounded ends can land one
            # unit in the last place away from the stored duration.
            for key in ("start_seconds", "end_seconds", "duration_seconds"):
                if abs(float(before[key]) - float(after[key])) > 2e-6:
                    raise SystemExit(
                        f"call {sample_id}: v3 moved {key} on {before['unit_id']}"
                    )
            for key in identity_keys:
                if before[key] != after[key]:
                    raise SystemExit(
                        f"call {sample_id}: v3 moved {key} on {before['unit_id']}"
                    )
        calls.append(
            {
                "sample_id": sample_id,
                "decoded_duration_seconds": round(duration, 6),
                "windows": int(block["windows"]),
                "units": emitted,
            }
        )
        print(f"{sample_id}: {len(units)} units with context", flush=True)

    pooled = stu.corpus_summary(summaries)
    shared = dict(
        schema=stu.PLAN_SCHEMA_V3,
        exposure_row=stu.EXPOSURE_ROW_V3,
        rules=stu.rules_block_v3(),
    )
    _write(
        plan_out,
        stu.plan_document(
            carrier_lock_key=str(document["carrier_lock_key"]),
            split_identity_hash=str(document["split_identity_hash"]),
            source_run_id=str(document["source_run_id"]),
            source_attempt_id=str(document["source_attempt_id"]),
            diarization_run_id=str(document["diarization_run_id"]),
            window_rows_sha256=str(document["window_rows_sha256"]),
            calls=calls,
            corpus=pooled,
            source_plan={
                "path": str(source.resolve().relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": digest,
                "schema": str(document["schema"]),
                "exposure_row": str(document["exposure_row"]),
                **(
                    {
                        "uniform_seconds": float(args.uniform_seconds),
                        "turns_are_replaced": (
                            "the OBS-E1b FORM TWIN: this plan inherits only the "
                            "call roster and each call's decoded duration from the "
                            "source plan; its units are equal clock units, so the "
                            "one thing that differs from the arm is where the "
                            "boundaries are"
                        ),
                    }
                    if args.uniform_seconds
                    else {
                        "turns_are_unchanged": (
                            "every unit's span, speaker facts, cut kinds, flags, "
                            "absorbed slivers and reference-word range are this "
                            "file's, asserted field by field by the builder before "
                            "the plan was written"
                        )
                    }
                ),
            },
            **shared,
        ),
    )
    _write(
        args.out_dir / "unit-plan-summary.json",
        stu.summary_document(
            plan_path=str(plan_out.resolve().relative_to(REPO_ROOT)).replace("\\", "/"),
            plan_sha256=hashlib.sha256(plan_out.read_bytes()).hexdigest(),
            elapsed_seconds=time.time() - started,
            corpus=pooled,
            per_call=summaries,
            schema=stu.SUMMARY_SCHEMA_V3,
            exposure_row=stu.EXPOSURE_ROW_V3,
            rules=stu.rules_block_v3(),
        ),
    )
    print(json.dumps(pooled, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", ""), type=Path)
    parser.add_argument("--diarization", type=Path)
    parser.add_argument("--window-rows", type=Path)
    parser.add_argument("--schema-version", choices=("v1", "v2", "v3"), default="v1")
    parser.add_argument("--from-plan", type=Path, default=None)
    parser.add_argument("--from-plan-sha256", default="")
    parser.add_argument(
        "--context-margin-seconds", type=float, default=stu.CONTEXT_MARGIN_SECONDS
    )
    parser.add_argument(
        "--min-delivered-seconds", type=float, default=stu.MIN_DELIVERED_CUT_SECONDS
    )
    parser.add_argument(
        "--uniform-seconds",
        type=float,
        default=0.0,
        help=(
            "OBS-E1b FORM TWIN (v3 only): replace the inherited speaker turns "
            "with equal clock units of this length before adding context, so "
            "the twin differs from the arm in boundary placement and nothing else"
        ),
    )
    parser.add_argument("--plan-out", type=Path, default=None)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    plan_out = args.plan_out or (
        REPO_ROOT / f"docs/receipts/obs/e21-speaker-turn-units-{args.schema_version}.json"
    )
    if args.schema_version == "v3":
        if args.from_plan is None:
            raise SystemExit("--schema-version v3 requires --from-plan")
        return _build_v3(args, plan_out)
    if args.diarization is None or args.window_rows is None:
        raise SystemExit("v1 and v2 require --diarization and --window-rows")
    if not args.data_root or not Path(args.data_root).is_dir():
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) must name the data root")
    build_units = stu.plan_units if args.schema_version == "v1" else stu.plan_units_v2
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
        units = build_units(
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
    plan_kwargs: dict[str, object] = dict(
        carrier_lock_key=artifact.carrier_lock_key,
        split_identity_hash=rows_document["split_identity_hash"],
        source_run_id=BASELINE_RUN,
        source_attempt_id=BASELINE_ATTEMPT,
        diarization_run_id=artifact.run_id,
        window_rows_sha256=hashlib.sha256(Path(args.window_rows).read_bytes()).hexdigest(),
        calls=calls,
        corpus=pooled,
    )
    summary_kwargs: dict[str, object] = dict(
        plan_path=str(plan_out.resolve().relative_to(REPO_ROOT)).replace("\\", "/"),
        elapsed_seconds=time.time() - started,
        corpus=pooled,
        per_call=summaries,
    )
    if args.schema_version == "v2":
        plan_kwargs.update(
            schema=stu.PLAN_SCHEMA_V2, exposure_row=stu.EXPOSURE_ROW_V2, rules=stu.rules_block_v2()
        )
        summary_kwargs.update(
            schema=stu.SUMMARY_SCHEMA_V2,
            exposure_row=stu.EXPOSURE_ROW_V2,
            rules=stu.rules_block_v2(),
        )
    _write(plan_out, stu.plan_document(**plan_kwargs))
    summary_kwargs["plan_sha256"] = hashlib.sha256(plan_out.read_bytes()).hexdigest()
    _write(args.out_dir / "unit-plan-summary.json", stu.summary_document(**summary_kwargs))
    print(json.dumps(pooled, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
