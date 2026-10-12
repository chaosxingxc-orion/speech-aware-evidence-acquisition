#!/usr/bin/env python3
"""Section 6 falsifier for the OBS-E1 speaker-turn-unit flight, run BEFORE any score.

The seam is a media change, so it has a byte-level oracle
(``docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-preregistration.md``
section 6): concatenating a call's delivered unit slices with the 2.0-second
tails removed must reproduce that call's sealed concatenated ``audio_sha256``
from ``saea-diarization-v1``, because the units tile ``[0, duration)`` and the
tails are appended to the delivered bytes only.  If any call disagrees, the cut
moved and the cell is stopped before it is scored.

Checked per unit, on the run's own ``obs-derivation.<call>.json`` SliceRecord
dumps and on the delivered WAV bytes themselves:

* the emitted span reproduces the pinned plan's ``start_seconds`` /
  ``end_seconds`` / ``duration_seconds`` for that ``unit_index``;
* ``audio_seconds`` still equals the CUT span, so the tail moved no boundary;
* ``iteration == unit_index - 1``;
* ``preprocess`` declares exactly one ``tail-silence-2s`` transform;
* the delivered byte count is the untailed cut plus exactly 2.0 s of samples,
  and those samples are digital silence;
* ``pre_sha256`` chains to the untailed cut and ``sha256`` to the delivered bytes.

Per call it also records the derivation's ``boundary_mode`` (must be
``unit-plan``) and its ``unit_plan_sha256`` (must be the pinned plan's), and the
per-unit prompt/completion token distribution and decode-cap saturation read off
the run's own trace.  No score file, reference transcript or ``wer_tags`` sidecar
is opened.

usage: e21_obs_e1_falsifier.py <attempt_dir> <run_id> [out.json]
"""

from __future__ import annotations
import os

import hashlib
import io
import json
import statistics
import sys
import wave
from array import array
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/"
    "speech-aware-evidence-acquisition"
)
DATA_ROOT = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
PLAN = REPO / "docs/receipts/obs/e21-speaker-turn-units-v2.json"
PLAN_SHA256 = "0f5f013959b89fa0acc3bb366324e701cbe3a022f7b29ef3e364d621d98eb03b"
DIARIZATION_INPUTS = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-diarization-obs/inputs.json"
)
RATE = 16000
TAIL_SECONDS = 2.0
TAIL_SAMPLES = int(TAIL_SECONDS * RATE)
EXPECTED_UNITS = 5122
EXPECTED_CALLS = 44
EXPECTED_CUT_SECONDS = 141345.852687
EXPECTED_DELIVERED_SECONDS = 151589.852688


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wav_bytes(samples: array) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(samples.tobytes())
    return buffer.getvalue()


def trace_units(trace_path: Path) -> dict[str, dict]:
    """``<sample_id>:<iteration>`` -> {prompt_tokens, completion_tokens,
    saturated, skipped, unit_id, ...} off the run's own trace."""

    slice_sample: dict[str, str] = {}
    obs: dict[str, dict] = {}
    usage: dict[str, dict] = {}
    for line in Path(trace_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        payload = record.get("payload") or {}
        base = str(record.get("record_id", "")).split("/", 1)[0]
        channel = record.get("channel")
        if channel == "MODEL_REQUEST" and not payload.get("stitch"):
            inner = payload.get("payload")
            if isinstance(inner, dict) and "sample_id" in inner:
                slice_sample[base] = str(inner["sample_id"])
        elif channel == "MODEL_RESPONSE" and not payload.get("stitch"):
            usage[base] = dict(payload.get("usage") or {})
        elif channel == "OBS" and "obs_iteration" in payload:
            obs[base] = payload

    out: dict[str, dict] = {}
    for base, payload in obs.items():
        sample_id = slice_sample.get(base)
        if sample_id is None:
            continue
        row = {
            "request_id": base,
            "sample_id": sample_id,
            "iteration": int(payload["obs_iteration"]),
            "unit_id": payload.get("obs_unit_id"),
            "unit_speaker": payload.get("obs_unit_speaker"),
            "unit_end_cut": payload.get("obs_unit_end_cut"),
            "saturated": bool(payload.get("obs_saturated")),
            "skipped": bool(payload.get("obs_skipped")),
            "final": bool(payload.get("obs_final_window")),
            "window_start_seconds": payload.get("obs_window_start_seconds"),
            "window_end_seconds": payload.get("obs_window_end_seconds"),
        }
        row.update(
            {
                "prompt_tokens": int((usage.get(base) or {}).get("prompt_tokens") or 0),
                "completion_tokens": int(
                    (usage.get(base) or {}).get("completion_tokens") or 0
                ),
            }
        )
        out[f"{sample_id}:{row['iteration']}"] = row
    return out


def check(attempt_dir: Path, run_id: str) -> dict:
    plan_sha = sha256_file(PLAN)
    plan = load_json(PLAN)
    units_by_call = {
        str(block["sample_id"]): {int(u["unit_index"]): u for u in block["units"]}
        for block in plan["calls"]
    }
    diarization = {
        str(call["sample_id"]): dict(call)
        for call in load_json(DIARIZATION_INPUTS)["calls"]
    }
    trace = trace_units(attempt_dir / f"{run_id}.trace.jsonl")

    failures: list[str] = []
    per_call: list[dict] = []
    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    saturated_units: list[str] = []
    skipped_units: list[str] = []
    total_units = 0
    total_cut = 0.0
    total_delivered = 0.0
    total_bytes = 0

    if plan_sha != PLAN_SHA256:
        failures.append(f"pinned plan hashes {plan_sha}, expected {PLAN_SHA256}")

    for path in sorted(attempt_dir.glob(f"{run_id}.obs-derivation.*.json")):
        doc = load_json(path)
        sample_id = str(doc["sample_id"])
        call_failures: list[str] = []
        planned = units_by_call.get(sample_id)
        if planned is None:
            failures.append(f"{sample_id}: the pinned plan carries no block for it")
            continue
        if doc.get("boundary_mode") != "unit-plan":
            call_failures.append(f"boundary_mode {doc.get('boundary_mode')!r}")
        if doc.get("unit_plan_sha256") != PLAN_SHA256:
            call_failures.append("derivation does not name the pinned plan")
        if len(doc["slices"]) != len(planned):
            call_failures.append(
                f"{len(doc['slices'])} slices against {len(planned)} planned units"
            )

        rebuilt = array("h")
        cut_seconds = 0.0
        delivered_seconds = 0.0
        call_bytes = 0
        for position, record in enumerate(doc["slices"], start=1):
            unit = planned.get(position)
            where = f"unit {sample_id}#u{position:04d}"
            if unit is None:
                call_failures.append(f"{where} has no planned unit")
                continue
            media = DATA_ROOT / str(record["media_relpath"])
            delivered = media.read_bytes()
            samples = array("h", delivered[44:])
            untailed = samples[:-TAIL_SAMPLES]
            rebuilt.extend(untailed)
            cut_seconds += float(record["audio_seconds"])
            delivered_seconds += float(record["audio_seconds"]) + TAIL_SECONDS
            call_bytes += len(delivered)

            if abs(float(record["start_seconds"]) - float(unit["start_seconds"])) > 1e-6:
                call_failures.append(f"{where} start {record['start_seconds']}")
            if abs(float(record["end_seconds"]) - float(unit["end_seconds"])) > 1e-6:
                call_failures.append(f"{where} end {record['end_seconds']}")
            span = float(record["end_seconds"]) - float(record["start_seconds"])
            if abs(float(record["audio_seconds"]) - span) > 1e-9:
                call_failures.append(f"{where} audio_seconds moved off the span")
            if abs(span - float(unit["duration_seconds"])) > 1e-6:
                call_failures.append(f"{where} duration {span}")
            if int(record["iteration"]) != int(unit["unit_index"]) - 1:
                call_failures.append(f"{where} iteration {record['iteration']}")
            if list(record["preprocess"]) != ["tail-silence-2s"]:
                call_failures.append(f"{where} preprocess {record['preprocess']}")
            if int(record["sample_rate_hz"]) != RATE:
                call_failures.append(f"{where} sample rate {record['sample_rate_hz']}")
            if len(delivered) != 44 + 2 * (len(untailed) + TAIL_SAMPLES):
                call_failures.append(f"{where} delivered byte count {len(delivered)}")
            if int(record["bytes"]) != len(delivered):
                call_failures.append(f"{where} recorded byte count {record['bytes']}")
            if any(samples[len(samples) - TAIL_SAMPLES :]):
                call_failures.append(f"{where} tail is not digital silence")
            if hashlib.sha256(delivered).hexdigest() != record["sha256"]:
                call_failures.append(f"{where} delivered sha256 does not match")
            if record["pre_sha256"] != hashlib.sha256(wav_bytes(untailed)).hexdigest():
                call_failures.append(f"{where} pre_sha256 does not chain")

            row = trace.get(f"{sample_id}:{int(record['iteration'])}")
            if row is None:
                call_failures.append(f"{where} has no OBS trace record")
            else:
                if row["unit_id"] != unit["unit_id"]:
                    call_failures.append(f"{where} trace unit id {row['unit_id']}")
                if row["unit_speaker"] != unit["speaker"]:
                    call_failures.append(f"{where} trace speaker {row['unit_speaker']}")
                if row["unit_end_cut"] != unit["end_cut"]:
                    call_failures.append(f"{where} trace end cut {row['unit_end_cut']}")
                prompt_tokens.append(row["prompt_tokens"])
                completion_tokens.append(row["completion_tokens"])
                if row["saturated"]:
                    saturated_units.append(str(unit["unit_id"]))
                if row["skipped"]:
                    skipped_units.append(str(unit["unit_id"]))

        sealed_sha256 = str(diarization[sample_id]["audio_sha256"])
        rebuilt_sha256 = hashlib.sha256(wav_bytes(rebuilt)).hexdigest()
        if rebuilt_sha256 != sealed_sha256:
            call_failures.append(
                "the untailed unit concatenation does not reproduce the sealed "
                f"audio_sha256 ({rebuilt_sha256} vs {sealed_sha256})"
            )
        total_units += len(doc["slices"])
        total_cut += cut_seconds
        total_delivered += delivered_seconds
        total_bytes += call_bytes
        per_call.append(
            {
                "sample_id": sample_id,
                "units": len(doc["slices"]),
                "planned_units": len(planned),
                "cut_seconds": round(cut_seconds, 6),
                "delivered_seconds": round(delivered_seconds, 6),
                "delivered_bytes": call_bytes,
                "decoded_duration_seconds": doc["decoded_duration_seconds"],
                "sealed_audio_sha256": sealed_sha256,
                "rebuilt_audio_sha256": rebuilt_sha256,
                "falsifier": "PASS" if rebuilt_sha256 == sealed_sha256 else "FAIL",
                "failures": call_failures,
            }
        )
        failures.extend(f"{sample_id}: {message}" for message in call_failures)
        print(
            f"  {sample_id}: {len(doc['slices'])} units, falsifier "
            f"{'PASS' if rebuilt_sha256 == sealed_sha256 else 'FAIL'}"
            f"{'' if not call_failures else '  (%d failures)' % len(call_failures)}",
            flush=True,
        )

    if len(per_call) != EXPECTED_CALLS:
        failures.append(f"{len(per_call)} calls carry derivations, expected {EXPECTED_CALLS}")
    if total_units != EXPECTED_UNITS:
        failures.append(f"{total_units} units flown, expected {EXPECTED_UNITS}")
    if abs(total_cut - EXPECTED_CUT_SECONDS) > 1e-3:
        failures.append(f"cut seconds {total_cut} against {EXPECTED_CUT_SECONDS}")
    if abs(total_delivered - EXPECTED_DELIVERED_SECONDS) > 1e-3:
        failures.append(
            f"delivered seconds {total_delivered} against {EXPECTED_DELIVERED_SECONDS}"
        )

    def dist(values: list[int]) -> dict:
        ordered = sorted(values)
        if not ordered:
            return {}
        return {
            "n": len(ordered),
            "min": ordered[0],
            "p25": ordered[len(ordered) // 4],
            "median": statistics.median(ordered),
            "p75": ordered[(3 * len(ordered)) // 4],
            "p99": ordered[min(len(ordered) - 1, int(0.99 * len(ordered)))],
            "max": ordered[-1],
            "mean": round(statistics.fmean(ordered), 3),
            "total": sum(ordered),
        }

    return {
        "schema": "saea-e21-obs-e1-flight-falsifier-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_dir": str(attempt_dir),
        "exposure_row": "SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1",
        "preregistration": (
            "docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-preregistration.md"
        ),
        "oracle": (
            "concatenating each call's delivered unit slices with the 2.0-second tails "
            "removed must reproduce that call's committed saea-diarization-v1 "
            "audio_sha256 (docs/checks/speech-aware-evidence-acquisition/"
            "2026-09-06-e21-diarization-obs/inputs.json)"
        ),
        "unit_plan": {
            "relpath": "docs/receipts/obs/e21-speaker-turn-units-v2.json",
            "sha256": plan_sha,
            "schema": plan["schema"],
        },
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
        "calls": len(per_call),
        "units": total_units,
        "cut_seconds": round(total_cut, 6),
        "delivered_seconds": round(total_delivered, 6),
        "delivered_bytes": total_bytes,
        "prompt_tokens_per_unit": dist(prompt_tokens),
        "completion_tokens_per_unit": dist(completion_tokens),
        "saturated_units": sorted(saturated_units),
        "saturated_unit_count": len(saturated_units),
        "skipped_units": sorted(skipped_units),
        "skipped_unit_count": len(skipped_units),
        "per_call": per_call,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    attempt_dir = Path(argv[1])
    run_id = argv[2]
    document = check(attempt_dir, run_id)
    if len(argv) > 3:
        out = Path(argv[3])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(document, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("wrote", out)
    print(
        json.dumps(
            {
                key: document[key]
                for key in (
                    "result",
                    "calls",
                    "units",
                    "cut_seconds",
                    "delivered_seconds",
                    "prompt_tokens_per_unit",
                    "completion_tokens_per_unit",
                    "saturated_unit_count",
                    "skipped_unit_count",
                )
            },
            indent=1,
        )
    )
    if document["failures"]:
        print("FAILURES:")
        for message in document["failures"][:40]:
            print("  -", message)
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
