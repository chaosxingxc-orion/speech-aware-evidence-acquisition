"""Section 4.4 falsifier for the Earnings-21 silence-tail cells.

Every flown window's emitted slice must equal the committed ``@ts2`` entry for
that window -- SHA-256, byte count, sample rate -- and every delivered clip must
be its sealed twin plus exactly 2.0 s.  The authoritative surface is the run's
own ``obs-derivation.<call>.json`` SliceRecord dumps, which are what
``core.model.SliceRegistry`` sealed; the trace supplies the decode-cap
saturation covariate beside it.  No score file is opened.

usage: falsifier.py <attempt_dir> <run_id> <expected_windows> [out.json]
"""

from __future__ import annotations
import os

import json
import sys
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/"
    "speech-aware-evidence-acquisition"
)
TS2 = REPO / "docs/receipts/artifacts/d1-e21-buf90-1593-tail2s.json"
SEALED_ATTEMPT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET") + "/runs/"
    "SAEA-E21-FULL44-DIRECT-BASELINE-V2/attempt-20260904T233816Z-bcd338"
)
TAIL_SECONDS = 2.0


def ts2_index() -> dict[str, dict]:
    doc = json.loads(TS2.read_text(encoding="utf-8"))
    return {entry["id"].split("@")[0]: entry for entry in doc["manifest"]}


def sealed_cut_index() -> dict[str, dict]:
    """window id -> the SEALED comparator's own SliceRecord for that window."""
    out: dict[str, dict] = {}
    for path in sorted(SEALED_ATTEMPT.glob("*.obs-derivation.*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for position, slice_record in enumerate(doc["slices"], start=1):
            out[f"{doc['sample_id']}#w{position:04d}"] = slice_record
    return out


def trace_obs(trace_path: Path) -> dict[str, dict]:
    """(sample_id, iteration) -> OBS payload, for the saturation covariate."""
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
    out: dict[str, dict] = {}
    for base, payload in obs.items():
        sample_id = slice_sample.get(base)
        if sample_id is None:
            continue
        out[f"{sample_id}:{payload['obs_iteration']}"] = payload
    return out


def check(attempt_dir: Path, run_id: str, expected_windows: int) -> dict:
    index = ts2_index()
    sealed = sealed_cut_index()
    obs = trace_obs(attempt_dir / f"{run_id}.trace.jsonl")

    checked: list[dict] = []
    disagreements: list[dict] = []
    chain_bad: list[dict] = []
    derivations = sorted(attempt_dir.glob(f"{run_id}.obs-derivation.*.json"))
    for path in derivations:
        doc = json.loads(path.read_text(encoding="utf-8"))
        sample_id = doc["sample_id"]
        for position, record in enumerate(doc["slices"], start=1):
            wid = f"{sample_id}#w{position:04d}"
            entry = index.get(wid)
            problem = None
            if entry is None:
                problem = "no committed @ts2 entry for this window id"
            elif record["sha256"] != entry["sha256"]:
                problem = f"sha256 {record['sha256']} != committed {entry['sha256']}"
            elif record["bytes"] != entry["bytes"]:
                problem = f"bytes {record['bytes']} != committed {entry['bytes']}"
            elif record["sample_rate_hz"] != entry["sample_rate_hz"]:
                problem = "sample rate moved"
            # The committed supplement stores seconds rounded to 6 decimals, so
            # the comparison is made at the receipt's OWN precision. The exact
            # identity is carried by the two lines above: a matching SHA-256 and
            # a matching byte count pin the delivered sample count exactly
            # (bytes = 44 + 2 * samples for 16-bit mono PCM), and therefore the
            # delivered duration, to the sample.
            elif round(record["audio_seconds"] + TAIL_SECONDS, 6) != round(
                entry["audio_seconds"], 6
            ):
                problem = (
                    f"delivered {record['audio_seconds'] + TAIL_SECONDS} != committed "
                    f"{entry['audio_seconds']}"
                )
            elif record["bytes"] != 44 + 2 * round(
                (record["audio_seconds"] + TAIL_SECONDS) * record["sample_rate_hz"]
            ):
                problem = (
                    f"byte count {record['bytes']} is not 44 + 2 * "
                    f"{round((record['audio_seconds'] + TAIL_SECONDS) * record['sample_rate_hz'])} "
                    "samples: the delivered duration is not the cut plus exactly 2.0 s"
                )
            elif list(record.get("preprocess") or []) != ["tail-silence-2s"]:
                problem = f"preprocess declares {record.get('preprocess')!r}"
            elif abs(record["audio_seconds"] - (record["end_seconds"] - record["start_seconds"])) > 1e-9:
                problem = "audio_seconds is not the cut span: the tail moved the window"

            sealed_record = sealed.get(wid)
            if problem is None and sealed_record is not None:
                if record["pre_sha256"] != sealed_record["sha256"]:
                    chain_bad.append(
                        {
                            "window_id": wid,
                            "pre_sha256": record["pre_sha256"],
                            "sealed_cut_sha256": sealed_record["sha256"],
                        }
                    )
                elif (
                    record["start_seconds"] != sealed_record["start_seconds"]
                    or record["end_seconds"] != sealed_record["end_seconds"]
                ):
                    chain_bad.append(
                        {
                            "window_id": wid,
                            "span": [record["start_seconds"], record["end_seconds"]],
                            "sealed_span": [
                                sealed_record["start_seconds"],
                                sealed_record["end_seconds"],
                            ],
                        }
                    )

            payload = obs.get(f"{sample_id}:{record['iteration']}") or {}
            row = {
                "window_id": wid,
                "sample_id": sample_id,
                "window_index": position,
                "start_seconds": record["start_seconds"],
                "end_seconds": record["end_seconds"],
                "cut_seconds": record["audio_seconds"],
                "delivered_seconds": record["audio_seconds"] + TAIL_SECONDS,
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "pre_sha256": record["pre_sha256"],
                "saturated": bool(payload.get("obs_saturated")),
                "skipped": bool(payload.get("obs_skipped")),
                "accepted_chars": payload.get("obs_accepted_chars"),
                "ok": problem is None,
                "problem": problem,
            }
            checked.append(row)
            if problem is not None:
                disagreements.append(row)

    saturated = [row for row in checked if row["saturated"]]
    result = {
        "schema": "saea-e21-tail2s-falsifier-v1",
        "attempt_dir": str(attempt_dir),
        "run_id": run_id,
        "calls_checked": len(derivations),
        "windows_checked": len(checked),
        "windows_expected": expected_windows,
        "disagreeing_rows": len(disagreements),
        "disagreements": disagreements[:20],
        "pre_sha256_chain_checked": sum(1 for row in checked if row["window_id"] in sealed),
        "chain_disagreements": len(chain_bad),
        "chain_examples": chain_bad[:10],
        "saturated_slice_count": len(saturated),
        "saturated_windows": [
            {
                "window_id": row["window_id"],
                "sample_id": row["sample_id"],
                "window_index": row["window_index"],
                "window_seconds": [row["start_seconds"], row["end_seconds"]],
                "accepted_chars": row["accepted_chars"],
            }
            for row in saturated
        ],
        "skipped_slice_count": sum(1 for row in checked if row["skipped"]),
        "cut_seconds_total": round(sum(row["cut_seconds"] for row in checked), 6),
        "delivered_seconds_total": round(sum(row["delivered_seconds"] for row in checked), 6),
        "delivered_bytes_total": sum(row["bytes"] for row in checked),
    }
    ok = (
        not disagreements
        and not chain_bad
        and len(checked) == expected_windows
    )
    if len(checked) != expected_windows:
        result["window_count_problem"] = (
            f"{len(checked)} windows flown, {expected_windows} expected"
        )
    result["verdict"] = "PASS" if ok else "FAIL"
    return result


if __name__ == "__main__":
    attempt_dir = Path(sys.argv[1])
    run_id = sys.argv[2]
    expected = int(sys.argv[3])
    out = check(attempt_dir, run_id, expected)
    printable = dict(out)
    printable["disagreements"] = out["disagreements"][:3]
    print(json.dumps(printable, indent=2))
    if len(sys.argv) > 4:
        Path(sys.argv[4]).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if out["verdict"] == "PASS" else 1)
