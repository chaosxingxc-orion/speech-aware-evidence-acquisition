#!/usr/bin/env python3
"""Snapshot the sealed comparator's PER-WINDOW hypotheses, and bind them.

KC-E1f's pass 1 is not re-flown: the sealed comparator
``SAEA-E21-FULL44-DIRECT-BASELINE-V2`` supplies each 90-second window's pass-1
hypothesis, so the cell costs ONE contact per window and the deletion profile
it is paired against is the comparator's own bytes. This script builds that
predecessor snapshot and the content-free receipt a config fragment pins.

MODEL-FREE. Zero model, GPU, server, tokenizer, tool, embedder, network and
audio-decode contacts; no reference transcript, no ``wer_tags``, no gold label
and no scorer is opened. It reads three sealed files -- the run manifest, its
``outputs.jsonl`` and its ``trace.jsonl`` -- and nothing else.

What it writes
--------------
* ``<data_root>/derived/e21-predecessor/<run>/<attempt>/window-hypotheses.json``
  -- 1,593 rows carrying each window's identity, bounds, sealed hypothesis text
  and that text's SHA-256, plus the per-window ``prompt_tokens`` /
  ``completion_tokens`` the sealed COST records recorded. It carries model
  output, so it lives under ``SPEECHRL_DATA_DIR`` where sealed outputs live and
  NEVER in Git.
* ``docs/receipts/<name>.json`` -- the committed, CONTENT-FREE binding: the
  artifact's path, size and SHA-256, the three source hashes, the window and
  call counts, a chain hash over ``(window_id, text_sha256)``, and the
  distributions the KC-E1f prompt fit needs to project a worst request. No
  hypothesis text of any kind.

How the recovery is proved rather than assumed
----------------------------------------------
``analysis.e21_window_pairing.stitched_windows_from_trace`` recovers the spans
and ``assert_stitch_reproduces_outputs`` refuses to continue unless every
recovered call rebuilds its sealed ``outputs.jsonl`` hypothesis BYTE FOR BYTE.
That is the same proof obligation the window-pairing receipt discharges, run
again here on the same sealed bytes, because a snapshot that cannot rebuild the
seal is not a snapshot of it.

Usage::

    python scripts/build_e21_predecessor_snapshot.py [--out <receipt path>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_window_pairing as wp,
)
from speech_aware_evidence_acquisition.core.predecessor_snapshot import (  # noqa: E402
    BINDING_SCHEMA,
    SNAPSHOT_SCHEMA,
    window_text_chain_sha256,
)

RUN_ID = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
ATTEMPT_ID = "attempt-20260904T233816Z-bcd338"
CARRIER = "earnings21-original"
SPLIT_IDENTITY_HASH = "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
EXPOSURE_ROW = "SAEA-E21-MF-PREDECESSOR-SNAPSHOT-V1"

DEFAULT_RECEIPT = (
    REPO_ROOT / "docs/receipts/e21-predecessor-full44-direct-baseline-v2.json"
)

#: What the sealed run is expected to contain, quoted from its own committed
#: readings (``scripts/e21_window_pairing_read.py``'s sealed profile and the
#: KC-E1 verdict's identity anchor) so this build is checked against a claim
#: rather than against whatever it happens to find.
EXPECTED_WINDOWS = 1593
EXPECTED_CALLS = 44
EXPECTED_SATURATED = 0
EXPECTED_COMPLETION_TOKENS_TOTAL = 439532
EXPECTED_PROMPT_TOKENS_TOTAL = 1935965


def log(message: str) -> None:
    print(
        "[%s] %s" % (datetime.now(tz=timezone.utc).strftime("%H:%M:%SZ"), message),
        flush=True,
    )


def git(*argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def distribution(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0}

    def percentile(fraction: float) -> float:
        index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
        return ordered[index]

    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": float(statistics.median(ordered)),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "max": ordered[-1],
        "total": sum(ordered),
    }


def read_outputs_text(path: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        sample_id = str(row["sample_id"])
        if sample_id in texts:
            raise SystemExit(f"outputs line {number}: duplicate sample {sample_id!r}")
        texts[sample_id] = str(row["text"])
    return texts


def read_cost_records(path: Path) -> dict[str, dict[str, int]]:
    """``request_id -> {prompt_tokens, completion_tokens}`` from the sealed COST
    channel. These are the SERVER's own counts on the flight tokenizer, which
    is why the KC-E1f prompt fit can project a pass-1 text cost exactly instead
    of estimating one from characters."""

    costs: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("channel") != "COST":
                continue
            record_id = str(record.get("record_id", ""))
            payload = record.get("payload")
            if not isinstance(payload, Mapping) or "/" not in record_id:
                continue
            costs[record_id.split("/", 1)[0]] = {
                "prompt_tokens": int(payload["prompt_tokens"]),
                "completion_tokens": int(payload["completion_tokens"]),
            }
    return costs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--attempt-id", default=ATTEMPT_ID)
    parser.add_argument("--out", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "TEST-ONLY. A binding receipt records the study commit it was built "
            "at; without this the build refuses a dirty tree rather than naming a "
            "commit that describes different bytes"
        ),
    )
    args = parser.parse_args()

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")

    from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: PLC0415

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit("the working tree is dirty; a binding names a commit:\n" + dirty)
    study_commit = git("rev-parse", "HEAD")

    root = data_root()
    attempt_dir = root / "runs" / args.run_id / args.attempt_id
    if not attempt_dir.is_dir():
        # KU-E1c's own placement deviation: some attempts sit at the run root.
        alternative = root / "runs" / args.run_id
        if (alternative / f"{args.run_id}.run-manifest.json").is_file():
            attempt_dir = alternative
        else:
            raise SystemExit(f"no sealed attempt directory at {attempt_dir}")
    manifest_path = attempt_dir / f"{args.run_id}.run-manifest.json"
    outputs_path = attempt_dir / f"{args.run_id}.outputs.jsonl"
    trace_path = attempt_dir / f"{args.run_id}.trace.jsonl"
    for path in (manifest_path, outputs_path, trace_path):
        if not path.is_file():
            raise SystemExit(f"sealed file missing: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest["run_id"]) != args.run_id:
        raise SystemExit("the manifest names a different run")
    if str(manifest["attempt"]["attempt_id"]) != args.attempt_id:
        raise SystemExit("the manifest names a different attempt")
    manifest_sha256 = sha256_file(manifest_path)
    outputs_sha256 = sha256_file(outputs_path)
    trace_sha256 = sha256_file(trace_path)
    if outputs_sha256 != str(manifest["outputs"]["sha256"]):
        raise SystemExit("outputs.jsonl does not hash to the manifest's own digest")
    if trace_sha256 != str(manifest["raw_trace"]["sha256"]):
        raise SystemExit("trace.jsonl does not hash to the manifest's own digest")
    log("sealed manifest, outputs and trace verified against the manifest's digests")

    windows_by_sample = wp.stitched_windows_from_trace(trace_path)
    outputs_text = read_outputs_text(outputs_path)
    wp.assert_stitch_reproduces_outputs(windows_by_sample, outputs_text)
    log(
        "the recovered windows rebuild all %d sealed hypotheses byte for byte"
        % len(outputs_text)
    )

    costs = read_cost_records(trace_path)
    rows: list[dict[str, Any]] = []
    per_call: list[dict[str, Any]] = []
    saturated_total = 0
    for sample_id in sorted(windows_by_sample):
        spans = windows_by_sample[sample_id]
        call_chars = 0
        call_completion = 0
        call_saturated = 0
        for span in spans:
            cost = costs.get(span.request_id, {})
            row = {
                "window_id": span.identifier,
                "sample_id": span.sample_id,
                "window_index": span.window_index,
                "request_id": span.request_id,
                "start_seconds": span.start_seconds,
                "end_seconds": span.end_seconds,
                "audio_seconds": span.audio_seconds,
                "saturated": span.saturated,
                "text": span.text,
                "text_sha256": sha256_text(span.text),
                "text_chars": len(span.text),
                "text_whitespace_tokens": len(span.text.split()),
                "prompt_tokens": cost.get("prompt_tokens"),
                "completion_tokens": cost.get("completion_tokens"),
            }
            rows.append(row)
            call_chars += len(span.text)
            call_completion += int(cost.get("completion_tokens") or 0)
            call_saturated += int(span.saturated)
        saturated_total += call_saturated
        per_call.append(
            {
                "sample_id": sample_id,
                "windows": len(spans),
                "saturated_windows": call_saturated,
                "text_chars": call_chars,
                "completion_tokens": call_completion,
                "max_window_completion_tokens": max(
                    (int(costs.get(span.request_id, {}).get("completion_tokens") or 0))
                    for span in spans
                ),
            }
        )

    if len(rows) != EXPECTED_WINDOWS:
        raise SystemExit(f"recovered {len(rows)} windows, expected {EXPECTED_WINDOWS}")
    if len(per_call) != EXPECTED_CALLS:
        raise SystemExit(f"recovered {len(per_call)} calls, expected {EXPECTED_CALLS}")
    if saturated_total != EXPECTED_SATURATED:
        raise SystemExit(
            f"recovered {saturated_total} saturated windows, the sealed run records "
            f"{EXPECTED_SATURATED}"
        )
    completion_total = sum(int(row["completion_tokens"] or 0) for row in rows)
    prompt_total = sum(int(row["prompt_tokens"] or 0) for row in rows)
    if completion_total != EXPECTED_COMPLETION_TOKENS_TOTAL:
        raise SystemExit(
            f"per-window completion tokens sum to {completion_total}, the manifest "
            f"records {EXPECTED_COMPLETION_TOKENS_TOTAL}"
        )
    if prompt_total != EXPECTED_PROMPT_TOKENS_TOTAL:
        raise SystemExit(
            f"per-window prompt tokens sum to {prompt_total}, the manifest records "
            f"{EXPECTED_PROMPT_TOKENS_TOTAL}"
        )
    log(
        "identity anchors PASS: %d windows / %d calls / %d saturated / %d completion "
        "tokens / %d prompt tokens"
        % (len(rows), len(per_call), saturated_total, completion_total, prompt_total)
    )

    artifact_relpath = "derived/e21-predecessor/%s/%s/window-hypotheses.json" % (
        args.run_id,
        args.attempt_id,
    )
    artifact_path = root / artifact_relpath
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "attempt_id": args.attempt_id,
        "carrier_lock_key": CARRIER,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": study_commit,
        "source": {
            "manifest_sha256": manifest_sha256,
            "outputs_sha256": outputs_sha256,
            "trace_sha256": trace_sha256,
        },
        "recovery": (
            "analysis.e21_window_pairing.stitched_windows_from_trace, proved by "
            "assert_stitch_reproduces_outputs to rebuild every sealed hypothesis byte "
            "for byte before a single row was written"
        ),
        "windows": len(rows),
        "calls": len(per_call),
        "rows": rows,
    }
    artifact_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact_sha256 = sha256_file(artifact_path)
    artifact_bytes = artifact_path.stat().st_size
    log("wrote %s (%d bytes, sha256 %s)" % (artifact_path, artifact_bytes, artifact_sha256[:12]))

    receipt = {
        "schema": BINDING_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "attempt_id": args.attempt_id,
        "carrier_lock_key": CARRIER,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "exposure_row": EXPOSURE_ROW,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": study_commit,
        "built_by": "scripts/build_e21_predecessor_snapshot.py",
        "zero_contact": (
            "no model, GPU, server, tokenizer, tool, embedder, network or audio-decode "
            "contact; three sealed files read (run manifest, outputs.jsonl, "
            "trace.jsonl) and no reference transcript, wer_tags, gold label or scorer "
            "opened"
        ),
        "content_free": (
            "this receipt carries hashes, counts and distributions only. Not one "
            "hypothesis character is committed: the per-window text is model output "
            "and lives with the sealed outputs under SPEECHRL_DATA_DIR"
        ),
        "source": {
            "manifest_sha256": manifest_sha256,
            "outputs_sha256": outputs_sha256,
            "trace_sha256": trace_sha256,
        },
        "artifact": {
            "relpath": artifact_relpath,
            "sha256": artifact_sha256,
            "bytes": artifact_bytes,
            "root": "SPEECHRL_DATA_DIR",
        },
        "windows": len(rows),
        "calls": len(per_call),
        "saturated_windows": saturated_total,
        "window_text_sha256_chain": window_text_chain_sha256(rows),
        "identity_anchors": {
            "windows": {"measured": len(rows), "sealed": EXPECTED_WINDOWS, "check": "PASS"},
            "calls": {"measured": len(per_call), "sealed": EXPECTED_CALLS, "check": "PASS"},
            "saturated_windows": {
                "measured": saturated_total,
                "sealed": EXPECTED_SATURATED,
                "check": "PASS",
            },
            "completion_tokens_total": {
                "measured": completion_total,
                "sealed": EXPECTED_COMPLETION_TOKENS_TOTAL,
                "check": "PASS",
            },
            "prompt_tokens_total": {
                "measured": prompt_total,
                "sealed": EXPECTED_PROMPT_TOKENS_TOTAL,
                "check": "PASS",
            },
            "stitch_rebuilds_sealed_outputs_byte_for_byte": "PASS",
        },
        "distributions": {
            "window_text_chars": distribution([int(row["text_chars"]) for row in rows]),
            "window_text_whitespace_tokens": distribution(
                [int(row["text_whitespace_tokens"]) for row in rows]
            ),
            "window_completion_tokens": distribution(
                [int(row["completion_tokens"] or 0) for row in rows]
            ),
            "window_prompt_tokens": distribution(
                [int(row["prompt_tokens"] or 0) for row in rows]
            ),
            "windows_per_call": distribution([int(row["windows"]) for row in per_call]),
        },
        "why_completion_tokens_matter": (
            "the pass-1 hypothesis rides in a KC-E1f pass-2 request, so its own "
            "completion-token count IS that request's added text cost, measured by the "
            "flight server on the flight tokenizer. The prompt fit projects the worst "
            "request from this distribution rather than from a characters-per-token "
            "guess"
        ),
        "per_call": per_call,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    log(
        "completion tokens per window: min %d median %.1f p95 %d max %d"
        % (
            receipt["distributions"]["window_completion_tokens"]["min"],
            receipt["distributions"]["window_completion_tokens"]["median"],
            receipt["distributions"]["window_completion_tokens"]["p95"],
            receipt["distributions"]["window_completion_tokens"]["max"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
