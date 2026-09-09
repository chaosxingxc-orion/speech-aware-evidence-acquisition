#!/usr/bin/env python3
"""Section 2 of the SLURP own-null preregistration: the request-side falsifier.

Run BEFORE any score file is opened. **Zero model, GPU, tool, embedding and
network contacts** -- it reads two sealed attempt directories and nothing else.

The claim this cell makes is that *nothing* moved except batch composition under
greedy decoding. That claim is checkable on the request side, row by row, and
this script is the check:

* every one of the comparator's 1,000 published sample ids is flown exactly
  once, with zero missing and zero extra;
* each row's ``MODEL_REQUEST`` payload is byte-identical to the comparator's
  after removing the two fields that move between any two runs for scheduling
  reasons alone -- ``request_id``, a dispatch-order index, and
  ``decoding_params.id_slot``, the server slot the request landed on. That
  exclusion is not an invention here: it is the same pair
  ``docs/readiness/2026-09-06-slurp-evo-s1-round-1-verdict.md`` section 1 names
  when it compares two SLURP runs' payloads. Everything else -- the rendered
  task instruction, the speech packet sha256, the media relpath, the audio
  seconds, ``mmproj_loaded``, the history, the supplied evidence, temperature,
  seed and ``max_tokens`` -- is inside the compared bytes;
* each row's ``prompt_tokens`` equals the comparator's, so the encoder saw the
  same tokens on the same row and not merely the same total;
* the sealed manifests' own cost blocks agree on calls, metered speech seconds
  and ``prompt_tokens_total``.

**Zero disagreeing rows, or the cell is void and no score is read.**
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "saea-slurp-own-null-replicate-v1-falsifier-v1"
ROW_ID = "SAEA-SLURP-DEV1000-NULL-REPLICATE-V1"
COMPARATOR = ("SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1", "attempt-20260905T060424Z-2c5596")

#: The comparator's own sealed cost block, from its run manifest.
SEALED_COST = {
    "calls_used": 1000,
    "audio_seconds_used": 2884.793687499999,
    "prompt_tokens_total": 2190161,
}
SEALED_INSTRUCTION_SHA256 = "4073f79ef25c4796b0a46cb2ac7f5d4982c83084982b87ddd8a70504090d37db"

#: Excluded from the compared request bytes, and only these two.
SCHEDULING_FIELDS = ("request_id", "decoding_params.id_slot")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(document) -> str:
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def attempt_dir(root: Path, run_id: str, attempt_id: str) -> Path:
    return root / "runs" / run_id / attempt_id


def load_arm(root: Path, run_id: str, attempt_id: str) -> dict:
    """Per-sample request identity, prompt tokens and answer text for one arm."""

    base = attempt_dir(root, run_id, attempt_id)
    manifest = base / (run_id + ".run-manifest.json")
    outputs = base / (run_id + ".outputs.jsonl")
    trace = base / (run_id + ".trace.jsonl")
    for path in (manifest, outputs, trace):
        if not path.is_file():
            raise SystemExit("missing sealed artifact: %s" % path)

    manifest_doc = json.loads(manifest.read_text(encoding="utf-8"))

    text_by_sample: dict[str, str] = {}
    response_sha_by_sample: dict[str, str] = {}
    for line in outputs.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sample_id = str(row["sample_id"])
        if sample_id in text_by_sample:
            raise SystemExit("duplicate sample id in outputs: %s" % sample_id)
        text_by_sample[sample_id] = str(row["text"])
        response_sha_by_sample[sample_id] = str(row["response_text_sha256"])

    request_by_sample: dict[str, dict] = {}
    sample_of_request: dict[str, str] = {}
    tokens_by_request: dict[str, int] = {}
    for line in trace.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        channel = record.get("channel")
        payload = record.get("payload") or {}
        if channel == "MODEL_REQUEST":
            inner = dict(payload["payload"])
            sample_id = str(inner["sample_id"])
            request_id = str(inner["request_id"])
            sample_of_request[request_id] = sample_id
            comparable = dict(inner)
            comparable.pop("request_id", None)
            decoding = dict(comparable.get("decoding_params") or {})
            decoding.pop("id_slot", None)
            comparable["decoding_params"] = decoding
            if sample_id in request_by_sample:
                raise SystemExit("duplicate sample id in trace: %s" % sample_id)
            request_by_sample[sample_id] = {
                "request_identity_sha256": canonical(comparable),
                "speech_packet_sha256": inner.get("speech_packet_sha256"),
                "audio_seconds": inner.get("audio_seconds"),
                "mmproj_loaded": inner.get("mmproj_loaded"),
                "media_relpath": inner.get("media_relpath"),
                "task_instruction_sha256": hashlib.sha256(
                    str(inner.get("task_instruction", "")).encode("utf-8")
                ).hexdigest(),
                "arm": payload.get("arm"),
                "request_id": request_id,
                "id_slot": (inner.get("decoding_params") or {}).get("id_slot"),
            }
        elif channel == "MODEL_RESPONSE":
            record_id = str(record.get("record_id") or "")
            request_id = record_id.rsplit("/", 1)[0]
            tokens_by_request[request_id] = int(payload["usage"]["prompt_tokens"])

    tokens_by_sample = {
        sample_of_request[request_id]: value
        for request_id, value in tokens_by_request.items()
        if request_id in sample_of_request
    }

    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "manifest_path": str(manifest),
        "manifest_sha256": sha256_file(manifest),
        "outputs_path": str(outputs),
        "outputs_sha256": sha256_file(outputs),
        "status": manifest_doc.get("status"),
        "study_commit": manifest_doc.get("study_commit"),
        "protocol_hash": manifest_doc.get("protocol_hash"),
        "cost": manifest_doc.get("cost"),
        "text": text_by_sample,
        "response_text_sha256": response_sha_by_sample,
        "request": request_by_sample,
        "prompt_tokens": tokens_by_sample,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    if args.data_root:
        root = Path(args.data_root)
    else:
        sys.path.insert(0, str(Path.cwd() / "src"))
        from speech_aware_evidence_acquisition.data.lock import data_root

        root = Path(data_root())

    left = load_arm(root, COMPARATOR[0], COMPARATOR[1])
    right = load_arm(root, ROW_ID, args.attempt_id)

    left_ids = set(left["request"])
    right_ids = set(right["request"])
    missing = sorted(left_ids - right_ids)
    extra = sorted(right_ids - left_ids)
    paired = sorted(left_ids & right_ids)

    checks = Counter()
    disagreeing: list[dict] = []
    token_delta_histogram: Counter = Counter()
    for sample_id in paired:
        left_row = left["request"][sample_id]
        right_row = right["request"][sample_id]
        left_tokens = left["prompt_tokens"].get(sample_id)
        right_tokens = right["prompt_tokens"].get(sample_id)
        failures = []
        if left_row["request_identity_sha256"] != right_row["request_identity_sha256"]:
            failures.append("request_identity_sha256")
        else:
            checks["request_identity_sha256"] += 1
        if left_row["speech_packet_sha256"] != right_row["speech_packet_sha256"]:
            failures.append("speech_packet_sha256")
        else:
            checks["speech_packet_sha256"] += 1
        if left_row["audio_seconds"] != right_row["audio_seconds"]:
            failures.append("audio_seconds")
        else:
            checks["audio_seconds"] += 1
        if right_row["mmproj_loaded"] is not False or left_row["mmproj_loaded"] is not False:
            failures.append("mmproj_loaded")
        else:
            checks["mmproj_loaded_false"] += 1
        if right_row["task_instruction_sha256"] != SEALED_INSTRUCTION_SHA256:
            failures.append("task_instruction_sha256")
        else:
            checks["task_instruction_sha256"] += 1
        if left_tokens is None or right_tokens is None:
            failures.append("prompt_tokens_missing")
        else:
            token_delta_histogram[right_tokens - left_tokens] += 1
            if left_tokens != right_tokens:
                failures.append("prompt_tokens")
            else:
                checks["prompt_tokens"] += 1
        if "@" in sample_id:
            failures.append("variant_suffix")
        else:
            checks["no_variant_suffix"] += 1
        if failures:
            disagreeing.append(
                {
                    "sample_id": sample_id,
                    "failed": failures,
                    "comparator_prompt_tokens": left_tokens,
                    "replicate_prompt_tokens": right_tokens,
                }
            )

    cost_right = right["cost"] or {}
    cost_checks = {
        name: {
            "expected": expected,
            "actual": cost_right.get(name),
            "equal": cost_right.get(name) == expected,
        }
        for name, expected in SEALED_COST.items()
    }

    passed = (
        not missing
        and not extra
        and not disagreeing
        and len(paired) == 1000
        and all(entry["equal"] for entry in cost_checks.values())
    )

    document = {
        "schema": SCHEMA,
        "row": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration": (
            "docs/readiness/2026-09-09-slurp-own-null-replicate-v1-preregistration.md"
        ),
        "section": "2 -- the falsifier, before any score file is opened",
        "contacts": {
            "frozen_core": 0,
            "gpu_hours": 0,
            "servers_started": 0,
            "network": 0,
            "paid_api_spend": 0,
        },
        "excluded_scheduling_fields": list(SCHEDULING_FIELDS),
        "arms": {
            arm: {
                key: value
                for key, value in record.items()
                if key
                not in ("text", "response_text_sha256", "request", "prompt_tokens")
            }
            for arm, record in (("COMPARATOR", left), ("REPLICATE", right))
        },
        "rows_paired": len(paired),
        "rows_missing": missing,
        "rows_extra": extra,
        "checks_passed_per_row": dict(sorted(checks.items())),
        "prompt_token_delta_histogram": {
            str(key): value for key, value in sorted(token_delta_histogram.items())
        },
        "prompt_tokens_total": {
            "comparator": sum(left["prompt_tokens"].values()),
            "replicate": sum(right["prompt_tokens"].values()),
        },
        "manifest_cost_checks": cost_checks,
        "disagreeing_rows": disagreeing,
        "disagreeing_row_count": len(disagreeing),
        "passed": passed,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("paired %d, missing %d, extra %d" % (len(paired), len(missing), len(extra)))
    print("checks per row: %s" % json.dumps(dict(sorted(checks.items()))))
    print("prompt token delta histogram: %s" % dict(token_delta_histogram))
    print("manifest cost: %s" % json.dumps(cost_checks, sort_keys=True))
    print("FALSIFIER: %s" % ("PASS" if passed else "FAIL"))
    print("-> %s" % args.out)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
