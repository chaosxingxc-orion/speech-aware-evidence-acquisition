#!/usr/bin/env python3
"""Window-fit receipt for SAEA-E21-FULL44-DIRECT-BASELINE-V1.

Zero contact and zero generated tokens -- and, unlike the Audio2Tool prompt-fit
receipts, zero model contact of any kind: no llama-server is spawned, because
this protocol's request envelope was already MEASURED, request by request, by a
sealed run of the identical protocol.

The measurement source is the per-request ``COST`` channel of
``SAEA-E-005B-N10-zero``'s sealed trace (attempt-20260814T235515Z-044ccc, 342
fixed 90-second windows, hash-bound by that attempt's own run manifest). Its 342
records give, per window, the audio seconds actually sent and the prompt tokens
the server actually counted. Two facts fall straight out and they are all a fit
certificate needs:

* ``prompt_tokens - 13 * ceil(audio_seconds)`` is the CONSTANT 62 on all 332
  full 90-second windows and 49 on the 10 short tail windows (the tail is not a
  different envelope: ``ceil`` rounds a fractional tail second up, so the
  encoder rule over-counts a tail by exactly one second = 13 tokens, and
  62 - 13 = 49). The text envelope of this arm is therefore 62 tokens, exactly,
  for every request it will ever send.
* The largest prompt the protocol can produce is a full window:
  13 * 90 + 62 = 1,232 tokens, which is precisely the sealed maximum.

The completion side is measured too: the sealed arm's completions ran 25 to 392
tokens with ZERO requests reaching the 1,024-token ``max_tokens`` ceiling, so
the ceiling is charged in full here as a worst case that never actually binds.

Fit rule for this flight (see the model fragment's ``serving_geometry_basis``):
declared slot tokens must be at least twice the worst required request. It is
deliberately NOT the Audio2Tool 8,192-token reserve, which was derived for
13k-token tool registries and is unreachable at any slot count on a carrier
whose whole request is 2.3k tokens.

The receipt also states plainly what it does NOT certify: that this geometry
fits in VRAM with the bf16 mmproj resident on the GPU. That is a live fact about
the machine, not about the protocol, and it is proven by the smoke's own session
receipt and server log before the flight is launched.

Usage:
    python scripts/build_e21_full44_window_fit_receipt.py --output <path.json>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SEALED_RUN_ID = "SAEA-E-005B-N10-zero"
SEALED_ATTEMPT = "attempt-20260814T235515Z-044ccc"
SPEECH_TOKENS_PER_SECOND = 13
BUFFER_SECONDS = 90
SPECIAL_TOKEN_RESERVE = 2
MAX_TOKENS = 1024
DECLARED_SLOTS = 8
DECLARED_CONTEXT = 49152
FIT_MARGIN_FACTOR = 2.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build(output: Path) -> dict[str, object]:
    data_root = Path(os.environ.get("SPEECHRL_DATA_DIR", ""))
    if not data_root.is_dir():
        raise SystemExit("SPEECHRL_DATA_DIR is unset or not a directory")
    attempt_dir = data_root / "runs" / SEALED_RUN_ID / SEALED_ATTEMPT
    trace_path = attempt_dir / f"{SEALED_RUN_ID}.trace.jsonl"
    manifest_path = attempt_dir / f"{SEALED_RUN_ID}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trace_sha256 = _sha256(trace_path)
    if trace_sha256 != manifest["raw_trace"]["sha256"]:
        raise SystemExit(
            "sealed trace sha256 does not match the sealed run manifest; refusing "
            "to certify a fit from unbound bytes"
        )

    records: list[dict[str, object]] = []
    with trace_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("channel") != "COST":
                continue
            payload = row.get("payload")
            if isinstance(payload, dict) and "prompt_tokens" in payload:
                records.append(payload)
    if not records:
        raise SystemExit("sealed trace carries no COST records")

    overhead = collections.Counter(
        int(record["prompt_tokens"])
        - SPEECH_TOKENS_PER_SECOND * math.ceil(float(record["audio_seconds"]))
        for record in records
    )
    prompt_tokens = [int(record["prompt_tokens"]) for record in records]
    completion_tokens = [int(record["completion_tokens"]) for record in records]
    latency = [float(record["latency_seconds"]) for record in records]
    audio_seconds = [float(record["audio_seconds"]) for record in records]

    full_window_overhead = 62
    if overhead[full_window_overhead] != sum(
        1 for value in audio_seconds if value >= BUFFER_SECONDS
    ):
        raise SystemExit(
            "the 62-token text envelope does not hold on every full window; "
            f"observed overheads {dict(overhead)}"
        )

    worst_prompt = SPEECH_TOKENS_PER_SECOND * BUFFER_SECONDS + full_window_overhead
    if worst_prompt != max(prompt_tokens):
        raise SystemExit(
            f"derived worst prompt {worst_prompt} disagrees with the sealed maximum "
            f"{max(prompt_tokens)}"
        )
    worst_required = worst_prompt + MAX_TOKENS + SPECIAL_TOKEN_RESERVE
    slot_tokens = DECLARED_CONTEXT // DECLARED_SLOTS
    fits = slot_tokens >= FIT_MARGIN_FACTOR * worst_required

    receipt: dict[str, object] = {
        "schema": "saea-e21-full44-window-fit-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": "SAEA-E21-FULL44-DIRECT-BASELINE-V1",
        "zero_contact": (
            "no llama-server spawned, no model, GPU, tool, embedding, network or "
            "audio-decode contact, zero generated tokens; every number below is read "
            "out of an already-sealed, hash-bound trace of the identical protocol"
        ),
        "measurement_source": {
            "run_id": SEALED_RUN_ID,
            "attempt_id": SEALED_ATTEMPT,
            "trace_relpath": str(trace_path.relative_to(data_root)),
            "trace_sha256": trace_sha256,
            "trace_sha256_matches_sealed_manifest": True,
            "manifest_protocol_hash": manifest["protocol_hash"],
            "cost_records": len(records),
            "why_this_run": (
                "its baseline fragment fixed-batch-zero-locked-buf90 is byte-identical "
                "to this flight's e21-buf90-zero-locked-scored4 apart from the scorers "
                "list, so its request envelope IS this flight's request envelope"
            ),
        },
        "encoder_rule": {
            "rule": "n_speech_tokens = 13 * ceil(audio_seconds)",
            "provenance": (
                "the mmproj encoder's one-second window rule already pinned by this "
                "repository's Audio2Tool promotion receipt, where it reproduced all 400 "
                "per-packet n_tokens without an exception"
            ),
            "residual_prompt_tokens_after_the_rule": {
                str(key): value for key, value in sorted(overhead.items())
            },
            "text_envelope_tokens": full_window_overhead,
            "tail_window_note": (
                "the 10 short tail windows show 49 rather than 62 because ceil rounds "
                "their fractional tail second up: the rule over-counts a tail by one "
                "second = 13 tokens, and 62 - 13 = 49. The envelope itself is constant"
            ),
        },
        "measured_request_envelope": {
            "prompt_tokens_min": min(prompt_tokens),
            "prompt_tokens_max": max(prompt_tokens),
            "prompt_tokens_mean": round(sum(prompt_tokens) / len(prompt_tokens), 3),
            "completion_tokens_min": min(completion_tokens),
            "completion_tokens_max": max(completion_tokens),
            "completion_tokens_mean": round(
                sum(completion_tokens) / len(completion_tokens), 3
            ),
            "completions_reaching_max_tokens": sum(
                1 for value in completion_tokens if value >= MAX_TOKENS
            ),
            "audio_seconds_min": min(audio_seconds),
            "audio_seconds_max": max(audio_seconds),
            "latency_seconds_min": round(min(latency), 3),
            "latency_seconds_max": round(max(latency), 3),
            "latency_seconds_mean": round(sum(latency) / len(latency), 3),
            "latency_basis": (
                "measured with the mmproj on the CPU (--no-mmproj-offload) at -np 8 on "
                "build 5d9dfcb58; this flight moves the encoder onto the GPU, so these "
                "latencies are the pessimistic anchor the smoke re-measures, never a "
                "prediction"
            ),
        },
        "declared_geometry": {
            "server_args_context": DECLARED_CONTEXT,
            "slots": DECLARED_SLOTS,
            "slot_tokens": slot_tokens,
            "slot_tokens_is_multiple_of_512": slot_tokens % 512 == 0,
            "max_tokens": MAX_TOKENS,
            "model_fragment": "q4km-e21-buf90-mmproj-gpu-04ccc72a",
        },
        "fit": {
            "worst_prompt_tokens": worst_prompt,
            "worst_required_tokens": worst_required,
            "worst_required_basis": (
                f"{SPEECH_TOKENS_PER_SECOND} * {BUFFER_SECONDS} speech + "
                f"{full_window_overhead} text + {MAX_TOKENS} completion ceiling + "
                f"{SPECIAL_TOKEN_RESERVE} special"
            ),
            "slot_tokens": slot_tokens,
            "margin_tokens": slot_tokens - worst_required,
            "margin_factor": round(slot_tokens / worst_required, 3),
            "rule": f"slot_tokens >= {FIT_MARGIN_FACTOR} x worst_required",
            "verdict": "FITS" if fits else "DOES NOT FIT",
        },
        "not_certified_here": (
            "VRAM. This receipt certifies only that the protocol's largest request fits "
            "the declared slot. Whether -c 49152 with the 2.2 GB bf16 mmproj resident on "
            "the GPU fits this machine's 24 GB is a live fact, proven by the smoke's own "
            "session receipt and server log before the flight is launched, and by the "
            "flight manifest's peak_vram_mib afterwards."
        ),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    receipt = build(Path(args.output))
    fit = receipt["fit"]  # type: ignore[index]
    print(
        f"worst required {fit['worst_required_tokens']} tokens vs slot "
        f"{fit['slot_tokens']} (margin {fit['margin_tokens']}, "
        f"x{fit['margin_factor']}): {fit['verdict']}"
    )
    return 0 if fit["verdict"] == "FITS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
