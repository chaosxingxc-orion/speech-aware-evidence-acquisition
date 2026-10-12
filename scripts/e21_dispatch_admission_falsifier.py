#!/usr/bin/env python3
"""Section 2 falsifier for the cross-call dispatcher admission cell.

The dispatcher claims that **nothing about the request moved** -- it moves WHEN a
call is cut and WHICH requests share a decode batch, never what is cut.  This proves it
against the sealed comparator's own bytes, before any score file is opened:
every one of the 1,593 emitted ``SliceRecord``s must equal
``SAEA-E21-FULL44-DIRECT-BASELINE-V2``'s record for the same window id on
``sha256``, ``bytes``, ``audio_seconds``, ``start_seconds``, ``end_seconds``,
``sample_rate_hz``, ``parent_sha256`` and ``preprocess`` -- and the run's own
``prompt_tokens_total`` must equal the comparator's 1,935,965 exactly.

``media_relpath`` is deliberately NOT compared: it carries the run id, so it
differs by construction and says nothing about the bytes.  The SHA-256 is what
pins the bytes.

The decode-cap saturation covariate is read off the trace beside it, exactly as
the tail cell's falsifier does, because a saturated window is 90 s of audio
contributing the empty string and must be a named, countable exclusion rather
than a silent one.

usage: e21_null_replicate_falsifier.py <attempt_dir> <run_id> <expected_windows> [out.json]
"""

from __future__ import annotations
import os

import json
import sys
from pathlib import Path

SEALED_ATTEMPT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET") + "/runs/"
    "SAEA-E21-FULL44-DIRECT-BASELINE-V2/attempt-20260904T233816Z-bcd338"
)
SEALED_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
SEALED_PROMPT_TOKENS = 1935965
SEALED_CUT_SECONDS = 141345.8526875
SEALED_WINDOWS = 1593

#: The fields that MUST agree.  `media_relpath` is excluded on purpose (it
#: carries the run id); `iteration` is excluded because it is the position the
#: window id already encodes.
COMPARED = (
    "sha256",
    "bytes",
    "audio_seconds",
    "start_seconds",
    "end_seconds",
    "sample_rate_hz",
    "parent_sha256",
    "preprocess",
)


def slice_index(attempt_dir: Path, run_id: str) -> dict[str, dict]:
    """window id -> that run's own SliceRecord."""

    out: dict[str, dict] = {}
    for path in sorted(attempt_dir.glob(f"{run_id}.obs-derivation.*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for position, record in enumerate(doc["slices"], start=1):
            out[f"{doc['sample_id']}#w{position:04d}"] = record
    return out


def saturation(trace_path: Path) -> dict[str, list]:
    """Window ids whose OBS record says the decode saturated or was skipped."""

    slice_sample: dict[str, str] = {}
    obs: dict[str, dict] = {}
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        payload = record.get("payload") or {}
        base = str(record.get("record_id", "")).split("/", 1)[0]
        if record.get("channel") == "MODEL_REQUEST" and not payload.get("stitch"):
            inner = payload.get("payload")
            if isinstance(inner, dict):
                slice_sample[base] = str(inner["sample_id"])
        elif record.get("channel") == "OBS" and "obs_iteration" in payload:
            obs[base] = payload
    saturated: list[dict] = []
    skipped: list[dict] = []
    for base, payload in obs.items():
        sample_id = slice_sample.get(base)
        if sample_id is None:
            continue
        entry = {
            "window_id": f"{sample_id}#w{int(payload['obs_iteration']) + 1:04d}",
            "sample_id": sample_id,
            "start_seconds": payload.get("obs_window_start_seconds"),
            "end_seconds": payload.get("obs_window_end_seconds"),
        }
        if payload.get("obs_saturated"):
            saturated.append(entry)
        if payload.get("obs_skipped"):
            skipped.append(entry)
    saturated.sort(key=lambda row: row["window_id"])
    skipped.sort(key=lambda row: row["window_id"])
    return {"saturated": saturated, "skipped": skipped}


def check(attempt_dir: Path, run_id: str, expected_windows: int) -> dict:
    sealed = slice_index(SEALED_ATTEMPT, SEALED_RUN)
    flown = slice_index(attempt_dir, run_id)
    manifest = json.loads(
        (attempt_dir / f"{run_id}.run-manifest.json").read_text(encoding="utf-8")
    )
    cost = manifest.get("cost") or {}

    disagreements: list[dict] = []
    for window_id in sorted(flown):
        record = flown[window_id]
        twin = sealed.get(window_id)
        if twin is None:
            disagreements.append(
                {"window_id": window_id, "problem": "no sealed comparator window with this id"}
            )
            continue
        for field in COMPARED:
            if record.get(field) != twin.get(field):
                disagreements.append(
                    {
                        "window_id": window_id,
                        "field": field,
                        "flown": record.get(field),
                        "sealed": twin.get(field),
                    }
                )
    for window_id in sorted(set(sealed) - set(flown)):
        disagreements.append(
            {"window_id": window_id, "problem": "sealed window not flown by the cell"}
        )

    wire = {
        "prompt_tokens_total": cost.get("prompt_tokens_total"),
        "sealed_prompt_tokens_total": SEALED_PROMPT_TOKENS,
        "prompt_tokens_identical": cost.get("prompt_tokens_total") == SEALED_PROMPT_TOKENS,
        "completion_tokens_total": cost.get("completion_tokens_total"),
        "sealed_completion_tokens_total": 439532,
        "calls_used": cost.get("calls_used"),
        "audio_seconds_used": cost.get("audio_seconds_used"),
        "sealed_audio_seconds_used": SEALED_CUT_SECONDS,
        "audio_seconds_identical": cost.get("audio_seconds_used") == SEALED_CUT_SECONDS,
    }

    covariate = saturation(attempt_dir / f"{run_id}.trace.jsonl")
    passed = (
        not disagreements
        and len(flown) == expected_windows
        and len(sealed) == SEALED_WINDOWS
        and wire["prompt_tokens_identical"]
        and wire["audio_seconds_identical"]
    )
    return {
        "schema": "saea-e21-dispatcher-admission-falsifier-v1",
        "run_id": run_id,
        "attempt_dir": str(attempt_dir),
        "comparator": {"run_id": SEALED_RUN, "attempt_dir": str(SEALED_ATTEMPT)},
        "windows_expected": expected_windows,
        "windows_checked": len(flown),
        "sealed_windows": len(sealed),
        "calls_checked": len({record["sample_id"] for record in flown.values()}),
        "compared_fields": list(COMPARED),
        "fields_not_compared": ["media_relpath (carries the run id)", "iteration"],
        "disagreeing_rows": len(disagreements),
        "disagreements": disagreements[:50],
        "wire": wire,
        "saturated_slice_count": len(covariate["saturated"]),
        "saturated_windows": covariate["saturated"],
        "skipped_slice_count": len(covariate["skipped"]),
        "skipped_windows": covariate["skipped"],
        "verdict": "PASS" if passed else "FAIL",
        "rule": (
            "Section 2 of docs/readiness/2026-09-08-e21-dispatcher-admission-v1-preregistration.md: "
            "every emitted SliceRecord equals the sealed comparator's own for that window id on "
            "every compared field, and prompt_tokens_total equals the comparator's 1,935,965 "
            "exactly. Zero disagreeing rows, or the cell is void and no score is read."
        ),
    }


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print(__doc__)
        return 2
    attempt_dir, run_id, expected = Path(argv[1]), argv[2], int(argv[3])
    result = check(attempt_dir, run_id, expected)
    if len(argv) > 4:
        Path(argv[4]).write_text(
            json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n"
        )
    summary = {key: result[key] for key in (
        "verdict", "windows_checked", "sealed_windows", "calls_checked",
        "disagreeing_rows", "saturated_slice_count", "skipped_slice_count",
    )}
    summary["wire"] = result["wire"]
    summary["saturated_windows"] = [row["window_id"] for row in result["saturated_windows"]]
    print(json.dumps(summary, indent=1))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
